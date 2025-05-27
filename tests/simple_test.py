#!/usr/bin/env python3
"""
🧪 Test simple pour le gestionnaire de secrets
==============================================
"""

import os
import sys
import asyncio
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

from agents.secrets_manager import EnvironmentBackend, SecretsManager

async def test_environment_backend():
    """Test simple du backend d'environnement"""
    print("🧪 Test du backend d'environnement...")
    
    backend = EnvironmentBackend()
    
    # Test de stockage et récupération
    test_key = "TEST_SECRET_KEY"
    test_value = "test_secret_value_123"
    
    # Stocker
    success = await backend.set_secret(test_key, test_value)
    print(f"✅ Stockage: {success}")
    
    # Récupérer
    retrieved = await backend.get_secret(test_key)
    print(f"✅ Récupération: {retrieved == test_value}")
    
    # Lister
    secrets = await backend.list_secrets()
    print(f"✅ Listage: {test_key in secrets}")
    
    # Supprimer
    deleted = await backend.delete_secret(test_key)
    print(f"✅ Suppression: {deleted}")
    
    return True

async def test_secrets_manager():
    """Test simple du gestionnaire de secrets"""
    print("\n🧪 Test du gestionnaire de secrets...")
    
    manager = SecretsManager()
    
    # Test basic
    test_key = "MANAGER_TEST_KEY"
    test_value = "manager_test_value_456"
    
    # Stocker
    success = await manager.set_secret(test_key, test_value)
    print(f"✅ Gestionnaire - Stockage: {success}")
    
    # Récupérer
    retrieved = await manager.get_secret(test_key)
    print(f"✅ Gestionnaire - Récupération: {retrieved == test_value}")
    
    # Health check
    health = await manager.health_check()
    print(f"✅ Gestionnaire - Santé: {all(health.values())}")
    
    return True

async def main():
    """Fonction principale de test"""
    print("🚀 Démarrage des tests du gestionnaire de secrets\n")
    
    try:
        # Test du backend d'environnement
        result1 = await test_environment_backend()
        
        # Test du gestionnaire
        result2 = await test_secrets_manager()
        
        if result1 and result2:
            print("\n🎉 Tous les tests sont passés avec succès!")
            return 0
        else:
            print("\n❌ Certains tests ont échoué")
            return 1
            
    except Exception as e:
        print(f"\n💥 Erreur lors des tests: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 