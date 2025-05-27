#!/usr/bin/env python3
"""
🧪 EasyRSVP AI Team - Tests pour le Gestionnaire de Secrets
==========================================================

Tests complets pour vérifier le bon fonctionnement du système
de gestion des secrets avec tous les backends.
"""

import pytest
import asyncio
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from agents.secrets_manager import (
    SecretsManager,
    EnvironmentBackend,
    DockerSecretsBackend,
    VaultBackend,
    SecretMetadata,
    get_secrets_manager
)
from agents.secure_config import SecureConfigManager, get_config_manager

class TestEnvironmentBackend:
    """Tests pour le backend des variables d'environnement"""
    
    def setup_method(self):
        """Configuration avant chaque test"""
        self.backend = EnvironmentBackend()
        # Nettoyer les variables d'environnement de test
        for key in list(os.environ.keys()):
            if key.startswith("TEST_"):
                del os.environ[key]
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_secret(self):
        """Test de stockage et récupération d'un secret"""
        secret_name = "TEST_API_KEY"
        secret_value = "test_secret_value_123"
        
        # Stocker le secret
        success = await self.backend.store_secret(secret_name, secret_value)
        assert success
        
        # Récupérer le secret
        retrieved_value = await self.backend.get_secret(secret_name)
        assert retrieved_value == secret_value
    
    @pytest.mark.asyncio
    async def test_delete_secret(self):
        """Test de suppression d'un secret"""
        secret_name = "TEST_DELETE_KEY"
        secret_value = "to_be_deleted"
        
        # Stocker puis supprimer
        await self.backend.store_secret(secret_name, secret_value)
        success = await self.backend.delete_secret(secret_name)
        assert success
        
        # Vérifier que le secret n'existe plus
        retrieved_value = await self.backend.get_secret(secret_name)
        assert retrieved_value is None
    
    @pytest.mark.asyncio
    async def test_list_secrets(self):
        """Test de listage des secrets"""
        # Stocker quelques secrets de test
        test_secrets = {
            "TEST_SECRET_1": "value1",
            "TEST_SECRET_2": "value2",
            "TEST_SECRET_3": "value3"
        }
        
        for name, value in test_secrets.items():
            await self.backend.store_secret(name, value)
        
        # Lister les secrets
        secrets_list = await self.backend.list_secrets()
        
        # Vérifier que nos secrets de test sont présents
        for secret_name in test_secrets.keys():
            assert secret_name in secrets_list
            assert isinstance(secrets_list[secret_name], SecretMetadata)
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test du contrôle de santé"""
        health = await self.backend.health_check()
        assert health["status"] == "healthy"
        assert health["backend_type"] == "environment"

class TestDockerSecretsBackend:
    """Tests pour le backend Docker Secrets"""
    
    def setup_method(self):
        """Configuration avant chaque test"""
        self.temp_dir = tempfile.mkdtemp()
        self.backend = DockerSecretsBackend(secrets_path=self.temp_dir)
    
    def teardown_method(self):
        """Nettoyage après chaque test"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_secret(self):
        """Test de stockage et récupération avec Docker Secrets"""
        secret_name = "test_docker_secret"
        secret_value = "docker_secret_value_456"
        
        # Stocker le secret
        success = await self.backend.store_secret(secret_name, secret_value)
        assert success
        
        # Vérifier que le fichier existe
        secret_file = Path(self.temp_dir) / secret_name
        assert secret_file.exists()
        
        # Récupérer le secret
        retrieved_value = await self.backend.get_secret(secret_name)
        assert retrieved_value == secret_value
    
    @pytest.mark.asyncio
    async def test_delete_secret(self):
        """Test de suppression avec Docker Secrets"""
        secret_name = "test_delete_docker"
        secret_value = "to_be_deleted_docker"
        
        # Stocker puis supprimer
        await self.backend.store_secret(secret_name, secret_value)
        success = await self.backend.delete_secret(secret_name)
        assert success
        
        # Vérifier que le fichier n'existe plus
        secret_file = Path(self.temp_dir) / secret_name
        assert not secret_file.exists()
    
    @pytest.mark.asyncio
    async def test_encrypted_storage(self):
        """Test du chiffrement des secrets"""
        secret_name = "test_encrypted"
        secret_value = "encrypted_value_789"
        
        # Stocker le secret avec chiffrement
        encrypted_backend = DockerSecretsBackend(
            secrets_path=self.temp_dir,
            encrypt=True,
            encryption_key=b"test_encryption_key_32_bytes_long"
        )
        
        success = await encrypted_backend.store_secret(secret_name, secret_value)
        assert success
        
        # Vérifier que le fichier contient des données chiffrées
        secret_file = Path(self.temp_dir) / secret_name
        with open(secret_file, 'rb') as f:
            encrypted_content = f.read()
        
        # Le contenu chiffré ne doit pas contenir la valeur en clair
        assert secret_value.encode() not in encrypted_content
        
        # Récupérer et vérifier le déchiffrement
        retrieved_value = await encrypted_backend.get_secret(secret_name)
        assert retrieved_value == secret_value

class TestVaultSecretBackend:
    """Tests pour le backend HashiCorp Vault"""
    
    def setup_method(self):
        """Configuration avant chaque test"""
        self.mock_client = Mock()
        self.backend = VaultSecretBackend(
            url="http://localhost:8200",
            token="test_token",
            mount_point="secret"
        )
        self.backend.client = self.mock_client
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_secret(self):
        """Test de stockage et récupération avec Vault"""
        secret_name = "test_vault_secret"
        secret_value = "vault_secret_value_abc"
        
        # Mock des réponses Vault
        self.mock_client.secrets.kv.v2.create_or_update_secret.return_value = None
        self.mock_client.secrets.kv.v2.read_secret_version.return_value = {
            'data': {'data': {'value': secret_value}}
        }
        
        # Stocker le secret
        success = await self.backend.store_secret(secret_name, secret_value)
        assert success
        
        # Récupérer le secret
        retrieved_value = await self.backend.get_secret(secret_name)
        assert retrieved_value == secret_value
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test du contrôle de santé pour Vault"""
        # Mock de la réponse de santé
        self.mock_client.sys.read_health_status.return_value = {
            'sealed': False,
            'initialized': True
        }
        
        health = await self.backend.health_check()
        assert health["status"] == "healthy"
        assert health["backend_type"] == "vault"

class TestSecretsManager:
    """Tests pour le gestionnaire principal des secrets"""
    
    def setup_method(self):
        """Configuration avant chaque test"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Créer un gestionnaire avec backends de test
        self.manager = SecretsManager()
        
        # Ajouter des backends de test
        self.manager.add_backend(
            "environment", 
            EnvironmentSecretBackend(),
            is_primary=True
        )
        self.manager.add_backend(
            "docker",
            DockerSecretsBackend(secrets_path=self.temp_dir)
        )
    
    def teardown_method(self):
        """Nettoyage après chaque test"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        # Nettoyer les variables d'environnement de test
        for key in list(os.environ.keys()):
            if key.startswith("TEST_"):
                del os.environ[key]
    
    @pytest.mark.asyncio
    async def test_fallback_mechanism(self):
        """Test du mécanisme de fallback entre backends"""
        secret_name = "test_fallback"
        secret_value = "fallback_value_xyz"
        
        # Stocker dans le backend secondaire seulement
        docker_backend = self.manager.backends["docker"]
        await docker_backend.store_secret(secret_name, secret_value)
        
        # Le gestionnaire doit trouver le secret dans le fallback
        retrieved_value = await self.manager.get_secret(secret_name)
        assert retrieved_value == secret_value
    
    @pytest.mark.asyncio
    async def test_secret_rotation(self):
        """Test de la rotation des secrets"""
        secret_name = "test_rotation"
        old_value = "old_secret_value"
        new_value = "new_secret_value"
        
        # Stocker la valeur initiale
        await self.manager.set_secret(secret_name, old_value)
        
        # Effectuer la rotation
        success = await self.manager.rotate_secret(secret_name, new_value)
        assert success
        
        # Vérifier la nouvelle valeur
        retrieved_value = await self.manager.get_secret(secret_name)
        assert retrieved_value == new_value
    
    @pytest.mark.asyncio
    async def test_audit_logging(self):
        """Test du logging d'audit"""
        secret_name = "test_audit"
        secret_value = "audit_test_value"
        
        # Effectuer plusieurs opérations
        await self.manager.set_secret(secret_name, secret_value)
        await self.manager.get_secret(secret_name)
        await self.manager.delete_secret(secret_name)
        
        # Vérifier les logs d'audit
        audit_log = await self.manager.get_audit_log()
        assert len(audit_log) >= 3  # Au moins 3 opérations
        
        # Vérifier que les opérations sont enregistrées
        operations = [entry["operation"] for entry in audit_log]
        assert "set_secret" in operations
        assert "get_secret" in operations
        assert "delete_secret" in operations
    
    @pytest.mark.asyncio
    async def test_health_check_all_backends(self):
        """Test du contrôle de santé de tous les backends"""
        health = await self.manager.health_check()
        
        assert "environment" in health
        assert "docker" in health
        assert health["environment"]["status"] == "healthy"
        assert health["docker"]["status"] == "healthy"

class TestSecureConfigManager:
    """Tests pour le gestionnaire de configuration sécurisée"""
    
    def setup_method(self):
        """Configuration avant chaque test"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock du gestionnaire de secrets
        self.mock_secrets_manager = Mock()
        self.mock_secrets_manager.get_secret = AsyncMock()
        self.mock_secrets_manager.set_secret = AsyncMock(return_value=True)
        self.mock_secrets_manager.health_check = AsyncMock(return_value={
            "environment": {"status": "healthy"},
            "docker": {"status": "healthy"}
        })
        
        # Créer le gestionnaire de configuration
        self.config_manager = SecureConfigManager(self.mock_secrets_manager)
    
    def teardown_method(self):
        """Nettoyage après chaque test"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_get_api_key(self):
        """Test de récupération des clés API"""
        # Mock de la réponse du gestionnaire de secrets
        self.mock_secrets_manager.get_secret.return_value = "test_openai_key_123"
        
        # Récupérer la clé API
        api_key = await self.config_manager.get_api_key("openai")
        assert api_key == "test_openai_key_123"
        
        # Vérifier que le bon secret a été demandé
        self.mock_secrets_manager.get_secret.assert_called_with("OPENAI_API_KEY")
    
    @pytest.mark.asyncio
    async def test_validate_configuration(self):
        """Test de validation de la configuration"""
        # Mock des clés API valides
        self.mock_secrets_manager.get_secret.side_effect = lambda key: {
            "OPENAI_API_KEY": "valid_openai_key",
            "ANTHROPIC_API_KEY": "valid_anthropic_key",
            "SLACK_BOT_TOKEN": "valid_slack_token"
        }.get(key)
        
        # Valider la configuration
        result = await self.config_manager.validate_configuration()
        
        assert result["valid"] is True
        assert len(result["missing_keys"]) == 0
        assert len(result["available_services"]) > 0
    
    @pytest.mark.asyncio
    async def test_health_status(self):
        """Test du statut de santé de la configuration"""
        health = await self.config_manager.get_health_status()
        
        assert "secrets_backends" in health
        assert "configuration_valid" in health
        assert "last_check" in health

# Tests d'intégration
class TestIntegration:
    """Tests d'intégration du système complet"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test du workflow complet de gestion des secrets"""
        # Ce test nécessiterait un environnement Docker ou Vault réel
        # Pour l'instant, on teste avec le backend environment
        
        secrets_manager = await get_secrets_manager()
        config_manager = await get_config_manager()
        
        # Test de stockage d'une clé API
        test_key = "TEST_INTEGRATION_KEY"
        test_value = "integration_test_value_456"
        
        success = await secrets_manager.set_secret(test_key, test_value)
        assert success
        
        # Test de récupération via le gestionnaire de configuration
        retrieved_value = await secrets_manager.get_secret(test_key)
        assert retrieved_value == test_value
        
        # Nettoyage
        await secrets_manager.delete_secret(test_key)

def run_tests():
    """Fonction pour exécuter tous les tests"""
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ])

if __name__ == "__main__":
    run_tests() 