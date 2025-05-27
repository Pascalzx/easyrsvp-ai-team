#!/usr/bin/env python3
"""
🔐 EasyRSVP AI Team - Secrets Manager
====================================

Gestionnaire de secrets pour l'équipe IA avec support pour:
- Docker Secrets
- HashiCorp Vault
- Variables d'environnement (développement uniquement)
"""

import os
import json
import logging
from typing import Dict, Optional, Union, Any
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
import aiofiles
import hvac
import docker
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

# Logger setup
logger = logging.getLogger(__name__)

@dataclass
class SecretMetadata:
    """Métadonnées pour un secret"""
    name: str
    created_at: datetime
    last_accessed: datetime
    expires_at: Optional[datetime] = None
    rotation_needed: bool = False
    source: str = "unknown"

class SecretsBackend(ABC):
    """Interface abstraite pour les backends de secrets"""
    
    @abstractmethod
    async def get_secret(self, name: str) -> Optional[str]:
        """Récupère un secret"""
        pass
    
    @abstractmethod
    async def set_secret(self, name: str, value: str, metadata: Optional[SecretMetadata] = None) -> bool:
        """Stocke un secret"""
        pass
    
    @abstractmethod
    async def delete_secret(self, name: str) -> bool:
        """Supprime un secret"""
        pass
    
    @abstractmethod
    async def list_secrets(self) -> Dict[str, SecretMetadata]:
        """Liste tous les secrets"""
        pass
    
    @abstractmethod
    async def rotate_secret(self, name: str, new_value: str) -> bool:
        """Effectue la rotation d'un secret"""
        pass

class DockerSecretsBackend(SecretsBackend):
    """Backend utilisant Docker Secrets"""
    
    def __init__(self, prefix: str = "easyRSVP_"):
        self.prefix = prefix
        self.client = docker.from_env()
        
    async def get_secret(self, name: str) -> Optional[str]:
        """Récupère un secret depuis Docker Secrets"""
        try:
            secret_path = f"/run/secrets/{self.prefix}{name}"
            if os.path.exists(secret_path):
                async with aiofiles.open(secret_path, 'r') as f:
                    value = await f.read()
                    return value.strip()
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du secret Docker {name}: {e}")
            return None
    
    async def set_secret(self, name: str, value: str, metadata: Optional[SecretMetadata] = None) -> bool:
        """Stocke un secret dans Docker Secrets"""
        try:
            secret_name = f"{self.prefix}{name}"
            
            # Supprimer le secret existant s'il existe
            try:
                existing_secret = self.client.secrets.get(secret_name)
                existing_secret.remove()
            except docker.errors.NotFound:
                pass
            
            # Créer le nouveau secret
            self.client.secrets.create(
                name=secret_name,
                data=value.encode('utf-8'),
                labels={
                    "created_at": datetime.now().isoformat(),
                    "managed_by": "easyRSVP_secrets_manager"
                }
            )
            
            logger.info(f"Secret Docker créé: {secret_name}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du secret Docker {name}: {e}")
            return False
    
    async def delete_secret(self, name: str) -> bool:
        """Supprime un secret Docker"""
        try:
            secret_name = f"{self.prefix}{name}"
            secret = self.client.secrets.get(secret_name)
            secret.remove()
            logger.info(f"Secret Docker supprimé: {secret_name}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du secret Docker {name}: {e}")
            return False
    
    async def list_secrets(self) -> Dict[str, SecretMetadata]:
        """Liste tous les secrets Docker"""
        secrets = {}
        try:
            for secret in self.client.secrets.list():
                if secret.name.startswith(self.prefix):
                    clean_name = secret.name[len(self.prefix):]
                    created_at = datetime.fromisoformat(
                        secret.attrs.get("CreatedAt", datetime.now().isoformat())
                    )
                    
                    secrets[clean_name] = SecretMetadata(
                        name=clean_name,
                        created_at=created_at,
                        last_accessed=datetime.now(),
                        source="docker_secrets"
                    )
        except Exception as e:
            logger.error(f"Erreur lors du listage des secrets Docker: {e}")
        
        return secrets
    
    async def rotate_secret(self, name: str, new_value: str) -> bool:
        """Effectue la rotation d'un secret Docker"""
        return await self.set_secret(name, new_value)

class VaultBackend(SecretsBackend):
    """Backend utilisant HashiCorp Vault"""
    
    def __init__(self, vault_url: str = "http://localhost:8200", vault_token: Optional[str] = None):
        self.vault_url = vault_url
        self.vault_token = vault_token or os.getenv("VAULT_TOKEN")
        self.mount_point = "easyRSVP"
        self.client = None
        
    async def _get_client(self):
        """Initialise le client Vault si nécessaire"""
        if not self.client:
            self.client = hvac.Client(url=self.vault_url, token=self.vault_token)
            
            # Vérifier la connexion
            if not self.client.is_authenticated():
                raise Exception("Authentification Vault échouée")
            
            # Activer le moteur KV v2 si nécessaire
            try:
                self.client.sys.enable_secrets_engine(
                    backend_type='kv',
                    path=self.mount_point,
                    options={'version': '2'}
                )
            except hvac.exceptions.InvalidRequest:
                # Le moteur existe déjà
                pass
        
        return self.client
    
    async def get_secret(self, name: str) -> Optional[str]:
        """Récupère un secret depuis Vault"""
        try:
            client = await self._get_client()
            response = client.secrets.kv.v2.read_secret_version(
                mount_point=self.mount_point,
                path=name
            )
            return response['data']['data'].get('value')
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du secret Vault {name}: {e}")
            return None
    
    async def set_secret(self, name: str, value: str, metadata: Optional[SecretMetadata] = None) -> bool:
        """Stocke un secret dans Vault"""
        try:
            client = await self._get_client()
            
            secret_data = {
                'value': value,
                'created_at': datetime.now().isoformat(),
                'managed_by': 'easyRSVP_secrets_manager'
            }
            
            if metadata:
                secret_data['metadata'] = {
                    'expires_at': metadata.expires_at.isoformat() if metadata.expires_at else None,
                    'rotation_needed': metadata.rotation_needed
                }
            
            client.secrets.kv.v2.create_or_update_secret(
                mount_point=self.mount_point,
                path=name,
                secret=secret_data
            )
            
            logger.info(f"Secret Vault créé: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du secret Vault {name}: {e}")
            return False
    
    async def delete_secret(self, name: str) -> bool:
        """Supprime un secret Vault"""
        try:
            client = await self._get_client()
            client.secrets.kv.v2.delete_metadata_and_all_versions(
                mount_point=self.mount_point,
                path=name
            )
            logger.info(f"Secret Vault supprimé: {name}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du secret Vault {name}: {e}")
            return False
    
    async def list_secrets(self) -> Dict[str, SecretMetadata]:
        """Liste tous les secrets Vault"""
        secrets = {}
        try:
            client = await self._get_client()
            # Lister les secrets à la racine du mount point
            response = client.secrets.kv.v2.list_secrets(mount_point=self.mount_point, path="")
            
            if response and 'data' in response and 'keys' in response['data']:
                for secret_name in response['data']['keys']:
                    try:
                        # Récupérer les métadonnées
                        secret_data = client.secrets.kv.v2.read_secret_version(
                            mount_point=self.mount_point,
                            path=secret_name
                        )
                        
                        created_at = datetime.fromisoformat(
                            secret_data['data']['data'].get('created_at', datetime.now().isoformat())
                        )
                        
                        secrets[secret_name] = SecretMetadata(
                            name=secret_name,
                            created_at=created_at,
                            last_accessed=datetime.now(),
                            source="vault"
                        )
                    except Exception as secret_e:
                        logger.warning(f"Impossible de lire le secret Vault {secret_name}: {secret_e}")
                        # Créer une entrée basique sans métadonnées détaillées
                        secrets[secret_name] = SecretMetadata(
                            name=secret_name,
                            created_at=datetime.now(),
                            last_accessed=datetime.now(),
                            source="vault"
                        )
                
        except Exception as e:
            logger.error(f"Erreur lors du listage des secrets Vault: {e}")
        
        return secrets
    
    async def rotate_secret(self, name: str, new_value: str) -> bool:
        """Effectue la rotation d'un secret Vault"""
        return await self.set_secret(name, new_value)

class EnvironmentBackend(SecretsBackend):
    """Backend utilisant les variables d'environnement (développement uniquement)"""
    
    def __init__(self, env_file: Optional[str] = None):
        self.env_file = env_file or ".env"
        self.secrets_cache = {}
        self._load_env_file()
    
    def _load_env_file(self):
        """Charge le fichier .env si disponible"""
        if os.path.exists(self.env_file):
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        self.secrets_cache[key] = value
    
    async def get_secret(self, name: str) -> Optional[str]:
        """Récupère un secret depuis les variables d'environnement"""
        # Essayer d'abord les variables d'environnement actuelles
        value = os.getenv(name)
        if value:
            return value
        
        # Puis le cache du fichier .env
        return self.secrets_cache.get(name)
    
    async def set_secret(self, name: str, value: str, metadata: Optional[SecretMetadata] = None) -> bool:
        """Stocke un secret (dans le cache uniquement)"""
        logger.warning("⚠️ Stockage en variable d'environnement - Usage développement uniquement!")
        self.secrets_cache[name] = value
        return True
    
    async def delete_secret(self, name: str) -> bool:
        """Supprime un secret du cache"""
        if name in self.secrets_cache:
            del self.secrets_cache[name]
            return True
        return False
    
    async def list_secrets(self) -> Dict[str, SecretMetadata]:
        """Liste tous les secrets disponibles"""
        secrets = {}
        for name in self.secrets_cache:
            secrets[name] = SecretMetadata(
                name=name,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                source="environment"
            )
        return secrets
    
    async def rotate_secret(self, name: str, new_value: str) -> bool:
        """Effectue la rotation d'un secret"""
        return await self.set_secret(name, new_value)

class SecretsManager:
    """Gestionnaire principal de secrets avec support multi-backend"""
    
    def __init__(self, primary_backend: str = "docker", fallback_backend: str = "environment"):
        self.backends = {}
        self.primary_backend = primary_backend
        self.fallback_backend = fallback_backend
        self.audit_log = []
        
        # Initialiser les backends disponibles
        self._initialize_backends()
    
    def _initialize_backends(self):
        """Initialise les backends disponibles"""
        try:
            # Docker Secrets
            self.backends["docker"] = DockerSecretsBackend()
            logger.info("✅ Backend Docker Secrets initialisé")
        except Exception as e:
            logger.warning(f"⚠️ Backend Docker Secrets non disponible: {e}")
        
        try:
            # HashiCorp Vault
            vault_url = os.getenv("VAULT_ADDR", "http://localhost:8200")
            self.backends["vault"] = VaultBackend(vault_url)
            logger.info("✅ Backend Vault initialisé")
        except Exception as e:
            logger.warning(f"⚠️ Backend Vault non disponible: {e}")
        
        # Variables d'environnement (toujours disponible)
        self.backends["environment"] = EnvironmentBackend()
        logger.info("✅ Backend Environment initialisé")
    
    async def get_secret(self, name: str, backend: Optional[str] = None) -> Optional[str]:
        """Récupère un secret avec fallback automatique"""
        backends_to_try = []
        
        if backend:
            backends_to_try = [backend]
        else:
            backends_to_try = [self.primary_backend, self.fallback_backend]
        
        for backend_name in backends_to_try:
            if backend_name in self.backends:
                try:
                    value = await self.backends[backend_name].get_secret(name)
                    if value:
                        self._log_access(name, backend_name, "read")
                        return value
                except Exception as e:
                    logger.error(f"Erreur backend {backend_name} pour {name}: {e}")
                    continue
        
        logger.warning(f"Secret {name} non trouvé dans tous les backends")
        return None
    
    async def set_secret(self, name: str, value: str, backend: Optional[str] = None) -> bool:
        """Stocke un secret"""
        backend_name = backend or self.primary_backend
        
        if backend_name not in self.backends:
            logger.error(f"Backend {backend_name} non disponible")
            return False
        
        try:
            metadata = SecretMetadata(
                name=name,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                source=backend_name
            )
            
            success = await self.backends[backend_name].set_secret(name, value, metadata)
            if success:
                self._log_access(name, backend_name, "write")
            return success
            
        except Exception as e:
            logger.error(f"Erreur lors du stockage du secret {name}: {e}")
            return False
    
    async def delete_secret(self, name: str, backend: Optional[str] = None) -> bool:
        """Supprime un secret"""
        backend_name = backend or self.primary_backend
        
        if backend_name not in self.backends:
            logger.error(f"Backend {backend_name} non disponible")
            return False
        
        try:
            success = await self.backends[backend_name].delete_secret(name)
            if success:
                self._log_access(name, backend_name, "delete")
            return success
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du secret {name}: {e}")
            return False
    
    async def list_all_secrets(self) -> Dict[str, Dict[str, SecretMetadata]]:
        """Liste tous les secrets de tous les backends"""
        all_secrets = {}
        
        for backend_name, backend in self.backends.items():
            try:
                secrets = await backend.list_secrets()
                all_secrets[backend_name] = secrets
            except Exception as e:
                logger.error(f"Erreur lors du listage des secrets {backend_name}: {e}")
                all_secrets[backend_name] = {}
        
        return all_secrets
    
    async def rotate_secret(self, name: str, new_value: str, backend: Optional[str] = None) -> bool:
        """Effectue la rotation d'un secret"""
        backend_name = backend or self.primary_backend
        
        if backend_name not in self.backends:
            logger.error(f"Backend {backend_name} non disponible")
            return False
        
        try:
            success = await self.backends[backend_name].rotate_secret(name, new_value)
            if success:
                self._log_access(name, backend_name, "rotate")
            return success
        except Exception as e:
            logger.error(f"Erreur lors de la rotation du secret {name}: {e}")
            return False
    
    def _log_access(self, secret_name: str, backend: str, operation: str):
        """Log des accès aux secrets pour audit"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "secret_name": secret_name,
            "backend": backend,
            "operation": operation
        }
        self.audit_log.append(log_entry)
        
        # Garder seulement les 1000 dernières entrées
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]
    
    async def get_audit_log(self) -> list:
        """Retourne le log d'audit"""
        return self.audit_log.copy()
    
    async def health_check(self) -> Dict[str, bool]:
        """Vérifie la santé de tous les backends"""
        health = {}
        
        for backend_name, backend in self.backends.items():
            try:
                # Test simple : lister les secrets
                await backend.list_secrets()
                health[backend_name] = True
            except Exception as e:
                logger.error(f"Health check échoué pour {backend_name}: {e}")
                health[backend_name] = False
        
        return health

# API Keys définies pour l'équipe IA
API_KEYS_CONFIG = {
    "openai": {
        "env_name": "OPENAI_API_KEY",
        "required": True,
        "description": "Clé API OpenAI pour le modèle principal"
    },
    "anthropic": {
        "env_name": "ANTHROPIC_API_KEY", 
        "required": True,
        "description": "Clé API Anthropic Claude pour le fallback"
    },
    "perplexity": {
        "env_name": "PERPLEXITY_API_KEY",
        "required": True,
        "description": "Clé API Perplexity pour la recherche"
    },
    "slack_bot": {
        "env_name": "SLACK_BOT_TOKEN",
        "required": False,
        "description": "Token bot Slack pour les notifications"
    },
    "slack_webhook": {
        "env_name": "SLACK_WEBHOOK_URL",
        "required": False,
        "description": "URL webhook Slack"
    },
    "discord_bot": {
        "env_name": "DISCORD_BOT_TOKEN",
        "required": False,
        "description": "Token bot Discord"
    },
    "discord_webhook": {
        "env_name": "DISCORD_WEBHOOK_URL",
        "required": False,
        "description": "URL webhook Discord"
    },
    "github": {
        "env_name": "GITHUB_TOKEN",
        "required": True,
        "description": "Token GitHub pour l'intégration Git"
    },
    "vercel": {
        "env_name": "VERCEL_TOKEN",
        "required": False,
        "description": "Token Vercel pour le déploiement"
    },
    "sentry": {
        "env_name": "SENTRY_DSN",
        "required": False,
        "description": "DSN Sentry pour le monitoring"
    }
}

async def setup_api_keys(secrets_manager: SecretsManager) -> Dict[str, bool]:
    """Configure toutes les API keys nécessaires"""
    results = {}
    
    logger.info("🔧 Configuration des API keys...")
    
    for key_name, config in API_KEYS_CONFIG.items():
        env_name = config["env_name"]
        
        # Vérifier si la clé existe déjà
        existing_value = await secrets_manager.get_secret(env_name)
        
        if existing_value:
            logger.info(f"✅ {key_name}: Déjà configuré")
            results[key_name] = True
        else:
            # Essayer de récupérer depuis les variables d'environnement
            env_value = os.getenv(env_name)
            if env_value:
                success = await secrets_manager.set_secret(env_name, env_value)
                if success:
                    logger.info(f"✅ {key_name}: Migré depuis l'environnement")
                    results[key_name] = True
                else:
                    logger.error(f"❌ {key_name}: Erreur de migration")
                    results[key_name] = False
            else:
                if config["required"]:
                    logger.warning(f"⚠️ {key_name}: REQUIS mais non configuré")
                else:
                    logger.info(f"ℹ️ {key_name}: Optionnel, non configuré")
                results[key_name] = False
    
    return results

# Instance globale du gestionnaire de secrets
secrets_manager = None

async def get_secrets_manager() -> SecretsManager:
    """Retourne l'instance globale du gestionnaire de secrets"""
    global secrets_manager
    if not secrets_manager:
        # Déterminer le backend principal basé sur l'environnement
        if os.getenv("DOCKER_SECRETS", "false").lower() == "true":
            primary = "docker"
        elif os.getenv("VAULT_ADDR"):
            primary = "vault"
        else:
            primary = "environment"
        
        secrets_manager = SecretsManager(primary_backend=primary)
        
        # Configuration initiale des API keys
        await setup_api_keys(secrets_manager)
    
    return secrets_manager

if __name__ == "__main__":
    import asyncio
    
    async def test_secrets_manager():
        """Test du gestionnaire de secrets"""
        manager = await get_secrets_manager()
        
        # Test de santé
        health = await manager.health_check()
        print("🏥 Health Check:")
        for backend, status in health.items():
            print(f"  {backend}: {'✅' if status else '❌'}")
        
        # Test d'une clé
        test_key = "test_api_key"
        test_value = "test_value_123"
        
        print(f"\n🧪 Test du secret '{test_key}':")
        
        # Stockage
        success = await manager.set_secret(test_key, test_value)
        print(f"  Stockage: {'✅' if success else '❌'}")
        
        # Récupération
        retrieved = await manager.get_secret(test_key)
        print(f"  Récupération: {'✅' if retrieved == test_value else '❌'}")
        
        # Suppression
        success = await manager.delete_secret(test_key)
        print(f"  Suppression: {'✅' if success else '❌'}")
        
        # Audit log
        audit = await manager.get_audit_log()
        print(f"\n📋 Audit log: {len(audit)} entrées")
    
    asyncio.run(test_secrets_manager()) 