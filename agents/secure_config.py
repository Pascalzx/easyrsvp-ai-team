#!/usr/bin/env python3
"""
⚙️ EasyRSVP AI Team - Secure Configuration
==========================================

Module de configuration sécurisée qui intègre le gestionnaire de secrets
pour fournir une configuration sécurisée à toute l'application.
"""

import os
import json
import logging
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from pathlib import Path
import asyncio
from functools import lru_cache

from .secrets_manager import get_secrets_manager, API_KEYS_CONFIG

# Logger setup
logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Configuration de la base de données"""
    host: str = "localhost"
    port: int = 5432
    database: str = "easyRSVP"
    username: str = "postgres"
    password: Optional[str] = None
    ssl_mode: str = "prefer"
    pool_size: int = 10
    max_overflow: int = 20

@dataclass
class RedisConfig:
    """Configuration Redis"""
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    ssl: bool = False
    connection_pool_size: int = 10

@dataclass
class APIConfig:
    """Configuration des API externes"""
    openai_key: Optional[str] = None
    anthropic_key: Optional[str] = None
    perplexity_key: Optional[str] = None
    github_token: Optional[str] = None
    vercel_token: Optional[str] = None
    slack_bot_token: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    discord_bot_token: Optional[str] = None
    discord_webhook_url: Optional[str] = None
    sentry_dsn: Optional[str] = None

@dataclass
class SecurityConfig:
    """Configuration de sécurité"""
    jwt_secret: Optional[str] = None
    encryption_key: Optional[str] = None
    cors_origins: List[str] = field(default_factory=lambda: ["http://localhost:3000"])
    allowed_hosts: List[str] = field(default_factory=lambda: ["localhost", "127.0.0.1"])
    rate_limit_per_minute: int = 100
    auth_rate_limit_per_minute: int = 10
    session_timeout_hours: int = 24
    max_failed_login_attempts: int = 5
    account_lockout_duration_minutes: int = 15

@dataclass
class MonitoringConfig:
    """Configuration du monitoring"""
    log_level: str = "INFO"
    enable_metrics: bool = True
    metrics_port: int = 9090
    health_check_interval: int = 30
    audit_log_retention_days: int = 365
    error_reporting_enabled: bool = True

@dataclass
class AppConfig:
    """Configuration principale de l'application"""
    environment: str = "development"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    api: APIConfig = field(default_factory=APIConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)

class SecureConfigManager:
    """Gestionnaire de configuration sécurisée"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "config/app.json"
        self.config = AppConfig()
        self._secrets_manager = None
        self._config_loaded = False
    
    async def initialize(self):
        """Initialise le gestionnaire de configuration"""
        if self._config_loaded:
            return
        
        # Initialiser le gestionnaire de secrets
        self._secrets_manager = await get_secrets_manager()
        
        # Charger la configuration depuis le fichier
        await self._load_config_file()
        
        # Charger les secrets
        await self._load_secrets()
        
        # Valider la configuration
        await self._validate_config()
        
        self._config_loaded = True
        logger.info("✅ Configuration sécurisée initialisée")
    
    async def _load_config_file(self):
        """Charge la configuration depuis le fichier JSON"""
        config_path = Path(self.config_file)
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # Mise à jour de la configuration avec les données du fichier
                await self._update_config_from_dict(config_data)
                logger.info(f"Configuration chargée depuis {config_path}")
                
            except Exception as e:
                logger.error(f"Erreur lors du chargement de la configuration: {e}")
        else:
            logger.info("Aucun fichier de configuration trouvé, utilisation des valeurs par défaut")
    
    async def _update_config_from_dict(self, config_data: Dict[str, Any]):
        """Met à jour la configuration à partir d'un dictionnaire"""
        if "database" in config_data:
            db_config = config_data["database"]
            self.config.database = DatabaseConfig(**db_config)
        
        if "redis" in config_data:
            redis_config = config_data["redis"]
            self.config.redis = RedisConfig(**redis_config)
        
        if "security" in config_data:
            security_config = config_data["security"]
            self.config.security = SecurityConfig(**security_config)
        
        if "monitoring" in config_data:
            monitoring_config = config_data["monitoring"]
            self.config.monitoring = MonitoringConfig(**monitoring_config)
        
        # Configuration principale
        for key in ["environment", "debug", "host", "port", "workers"]:
            if key in config_data:
                setattr(self.config, key, config_data[key])
    
    async def _load_secrets(self):
        """Charge tous les secrets depuis le gestionnaire de secrets"""
        if not self._secrets_manager:
            logger.error("Gestionnaire de secrets non initialisé")
            return
        
        # Charger les API keys
        api_config = {}
        for key_name, config in API_KEYS_CONFIG.items():
            env_name = config["env_name"]
            secret_value = await self._secrets_manager.get_secret(env_name)
            
            if secret_value:
                # Mapper les noms d'environnement aux attributs de configuration
                attr_name = self._env_name_to_attr(env_name)
                api_config[attr_name] = secret_value
                logger.debug(f"Secret chargé: {key_name}")
            elif config["required"]:
                logger.warning(f"⚠️ Secret requis manquant: {key_name}")
        
        self.config.api = APIConfig(**api_config)
        
        # Charger les secrets de sécurité
        jwt_secret = await self._secrets_manager.get_secret("JWT_SECRET")
        if jwt_secret:
            self.config.security.jwt_secret = jwt_secret
        
        encryption_key = await self._secrets_manager.get_secret("ENCRYPTION_KEY")
        if encryption_key:
            self.config.security.encryption_key = encryption_key
        
        # Charger les secrets de base de données
        db_password = await self._secrets_manager.get_secret("DATABASE_PASSWORD")
        if db_password:
            self.config.database.password = db_password
        
        # Charger les secrets Redis
        redis_password = await self._secrets_manager.get_secret("REDIS_PASSWORD")
        if redis_password:
            self.config.redis.password = redis_password
    
    def _env_name_to_attr(self, env_name: str) -> str:
        """Convertit un nom de variable d'environnement en attribut de configuration"""
        mapping = {
            "OPENAI_API_KEY": "openai_key",
            "ANTHROPIC_API_KEY": "anthropic_key",
            "PERPLEXITY_API_KEY": "perplexity_key",
            "SLACK_BOT_TOKEN": "slack_bot_token",
            "SLACK_WEBHOOK_URL": "slack_webhook_url",
            "DISCORD_BOT_TOKEN": "discord_bot_token",
            "DISCORD_WEBHOOK_URL": "discord_webhook_url",
            "GITHUB_TOKEN": "github_token",
            "VERCEL_TOKEN": "vercel_token",
            "SENTRY_DSN": "sentry_dsn"
        }
        return mapping.get(env_name, env_name.lower())
    
    async def _validate_config(self):
        """Valide la configuration"""
        errors = []
        
        # Vérifier les API keys requises
        if not self.config.api.openai_key:
            errors.append("OpenAI API key manquante")
        
        if not self.config.api.anthropic_key:
            errors.append("Anthropic API key manquante")
        
        if not self.config.api.perplexity_key:
            errors.append("Perplexity API key manquante")
        
        # Vérifier la configuration de sécurité
        if not self.config.security.jwt_secret:
            logger.warning("⚠️ JWT secret non configuré, génération automatique")
            # Générer un secret JWT temporaire
            import secrets
            jwt_secret = secrets.token_urlsafe(32)
            self.config.security.jwt_secret = jwt_secret
            
            # Stocker le secret généré
            if self._secrets_manager:
                await self._secrets_manager.set_secret("JWT_SECRET", jwt_secret)
        
        if not self.config.security.encryption_key:
            logger.warning("⚠️ Clé de chiffrement non configurée, génération automatique")
            # Générer une clé de chiffrement
            from cryptography.fernet import Fernet
            encryption_key = Fernet.generate_key().decode()
            self.config.security.encryption_key = encryption_key
            
            # Stocker la clé générée
            if self._secrets_manager:
                await self._secrets_manager.set_secret("ENCRYPTION_KEY", encryption_key)
        
        # Vérifier la configuration de base de données
        if not self.config.database.password:
            logger.warning("⚠️ Mot de passe de base de données non configuré")
        
        if errors:
            error_msg = "Erreurs de configuration: " + ", ".join(errors)
            logger.error(error_msg)
            if self.config.environment == "production":
                raise ValueError(error_msg)
        else:
            logger.info("✅ Configuration validée")
    
    async def get_config(self) -> AppConfig:
        """Retourne la configuration de l'application"""
        if not self._config_loaded:
            await self.initialize()
        return self.config
    
    async def update_secret(self, key: str, value: str) -> bool:
        """Met à jour un secret"""
        if not self._secrets_manager:
            logger.error("Gestionnaire de secrets non initialisé")
            return False
        
        success = await self._secrets_manager.set_secret(key, value)
        if success:
            # Recharger la configuration
            await self._load_secrets()
        return success
    
    async def get_database_url(self) -> str:
        """Retourne l'URL de connexion à la base de données"""
        config = await self.get_config()
        db = config.database
        
        password_part = f":{db.password}" if db.password else ""
        return f"postgresql://{db.username}{password_part}@{db.host}:{db.port}/{db.database}"
    
    async def get_redis_url(self) -> str:
        """Retourne l'URL de connexion Redis"""
        config = await self.get_config()
        redis = config.redis
        
        protocol = "rediss" if redis.ssl else "redis"
        password_part = f":{redis.password}@" if redis.password else ""
        return f"{protocol}://{password_part}{redis.host}:{redis.port}/{redis.db}"
    
    async def validate_configuration(self) -> bool:
        """
        Valide que la configuration est correcte et que tous les secrets requis sont disponibles.
        """
        try:
            # Vérifier les secrets essentiels
            essential_keys = [
                self.config.security.jwt_secret,
                self.config.security.encryption_key
            ]
            
            # Au moins une clé API doit être configurée
            api_keys = [
                self.config.api.openai_key,
                self.config.api.anthropic_key,
                self.config.api.perplexity_key
            ]
            
            has_essential_keys = all(essential_keys)
            has_api_key = any(api_keys)
            
            return has_essential_keys and has_api_key
            
        except Exception as e:
            logger.error(f"Erreur lors de la validation de configuration: {e}")
            return False

    async def get_health_status(self) -> Dict[str, Any]:
        """Retourne l'état de santé de la configuration"""
        if not self._secrets_manager:
            return {"status": "error", "message": "Gestionnaire de secrets non initialisé"}
        
        # Vérifier la santé du gestionnaire de secrets
        secrets_health = await self._secrets_manager.health_check()
        
        # Compter les secrets configurés
        api_keys_count = sum(1 for key in [
            self.config.api.openai_key,
            self.config.api.anthropic_key,
            self.config.api.perplexity_key,
            self.config.api.github_token
        ] if key)
        
        # Valider la configuration
        config_valid = await self.validate_configuration()
        
        return {
            "overall_status": "healthy" if any(secrets_health.values()) and config_valid else "degraded",
            "secrets_backends": secrets_health,
            "api_keys_configured": api_keys_count,
            "security_keys_configured": bool(self.config.security.jwt_secret and self.config.security.encryption_key),
            "configuration_valid": config_valid,
            "environment": self.config.environment
        }
    
    async def save_config_template(self, output_file: str = "config/app.template.json"):
        """Sauvegarde un template de configuration"""
        template_config = {
            "environment": "development",
            "debug": True,
            "host": "0.0.0.0",
            "port": 8000,
            "workers": 1,
            "database": {
                "host": "localhost",
                "port": 5432,
                "database": "easyRSVP",
                "username": "postgres",
                "ssl_mode": "prefer",
                "pool_size": 10,
                "max_overflow": 20
            },
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 0,
                "ssl": False,
                "connection_pool_size": 10
            },
            "security": {
                "cors_origins": ["http://localhost:3000", "https://app.easyrsvp.com"],
                "allowed_hosts": ["localhost", "127.0.0.1", "app.easyrsvp.com"],
                "rate_limit_per_minute": 100,
                "auth_rate_limit_per_minute": 10,
                "session_timeout_hours": 24,
                "max_failed_login_attempts": 5,
                "account_lockout_duration_minutes": 15
            },
            "monitoring": {
                "log_level": "INFO",
                "enable_metrics": True,
                "metrics_port": 9090,
                "health_check_interval": 30,
                "audit_log_retention_days": 365,
                "error_reporting_enabled": True
            }
        }
        
        # Créer le répertoire si nécessaire
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(template_config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Template de configuration sauvegardé: {output_file}")

# Instance globale du gestionnaire de configuration
_config_manager = None

async def get_config_manager() -> SecureConfigManager:
    """Retourne l'instance globale du gestionnaire de configuration"""
    global _config_manager
    if not _config_manager:
        _config_manager = SecureConfigManager()
        await _config_manager.initialize()
    return _config_manager

@lru_cache()
def get_config_sync() -> AppConfig:
    """Retourne la configuration de manière synchrone (pour FastAPI)"""
    # Cette fonction sera initialisée au démarrage de l'application
    if not hasattr(get_config_sync, '_config'):
        raise RuntimeError("Configuration non initialisée. Appelez initialize_config_sync() au démarrage.")
    return get_config_sync._config

async def initialize_config_sync():
    """Initialise la configuration synchrone pour FastAPI"""
    config_manager = await get_config_manager()
    config = await config_manager.get_config()
    get_config_sync._config = config
    logger.info("✅ Configuration synchrone initialisée")

# Utilitaires pour FastAPI
def get_api_config() -> APIConfig:
    """Retourne la configuration des API"""
    return get_config_sync().api

def get_security_config() -> SecurityConfig:
    """Retourne la configuration de sécurité"""
    return get_config_sync().security

def get_database_config() -> DatabaseConfig:
    """Retourne la configuration de base de données"""
    return get_config_sync().database

if __name__ == "__main__":
    async def test_config():
        """Test du gestionnaire de configuration"""
        manager = await get_config_manager()
        config = await manager.get_config()
        
        print("🔧 Configuration EasyRSVP AI Team:")
        print(f"  Environment: {config.environment}")
        print(f"  Debug: {config.debug}")
        print(f"  Host: {config.host}:{config.port}")
        
        print("\n🔗 API Keys:")
        print(f"  OpenAI: {'✅' if config.api.openai_key else '❌'}")
        print(f"  Anthropic: {'✅' if config.api.anthropic_key else '❌'}")
        print(f"  Perplexity: {'✅' if config.api.perplexity_key else '❌'}")
        print(f"  GitHub: {'✅' if config.api.github_token else '❌'}")
        
        print("\n🔒 Sécurité:")
        print(f"  JWT Secret: {'✅' if config.security.jwt_secret else '❌'}")
        print(f"  Encryption Key: {'✅' if config.security.encryption_key else '❌'}")
        
        print("\n🏥 Health Status:")
        health = await manager.get_health_status()
        for key, value in health.items():
            print(f"  {key}: {value}")
        
        # Sauvegarder le template
        await manager.save_config_template()
        print("\n💾 Template de configuration sauvegardé")
    
    asyncio.run(test_config()) 