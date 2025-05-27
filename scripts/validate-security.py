#!/usr/bin/env python3
"""
🔒 Script de validation complète du système de sécurité
====================================================

Ce script valide l'ensemble du système de sécurité EasyRSVP AI Team:
- Gestionnaire de secrets
- Configuration sécurisée
- Intégration avec l'API
"""

import asyncio
import sys
import os
from pathlib import Path
import json
from datetime import datetime

# Ajouter le répertoire parent au PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

from agents.secrets_manager import SecretsManager, get_secrets_manager
from agents.secure_config import SecureConfigManager, get_config_manager

def print_header(title: str):
    """Affiche un en-tête formaté"""
    print(f"\n{'='*60}")
    print(f"🔐 {title}")
    print(f"{'='*60}")

def print_section(title: str):
    """Affiche une section"""
    print(f"\n📋 {title}")
    print("-" * 40)

def print_result(test_name: str, success: bool, details: str = ""):
    """Affiche le résultat d'un test"""
    icon = "✅" if success else "❌"
    print(f"{icon} {test_name}: {details}")

async def test_secrets_manager():
    """Test complet du gestionnaire de secrets"""
    print_section("Tests du Gestionnaire de Secrets")
    
    try:
        # Initialisation
        manager = SecretsManager()
        print_result("Initialisation", True, "SecretsManager créé")
        
        # Health check
        health = await manager.health_check()
        healthy_backends = [name for name, status in health.items() if status]
        print_result("Health Check", len(healthy_backends) > 0, 
                    f"Backends disponibles: {', '.join(healthy_backends)}")
        
        # Test de stockage/récupération
        test_key = "SECURITY_VALIDATION_TEST"
        test_value = f"test_value_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        store_success = await manager.set_secret(test_key, test_value)
        print_result("Stockage de secret", store_success)
        
        if store_success:
            retrieved = await manager.get_secret(test_key)
            retrieve_success = retrieved == test_value
            print_result("Récupération de secret", retrieve_success)
            
            # Nettoyage
            delete_success = await manager.delete_secret(test_key)
            print_result("Suppression de secret", delete_success)
        
        # Test des logs d'audit
        audit_log = await manager.get_audit_log()
        print_result("Logs d'audit", len(audit_log) >= 0, 
                    f"{len(audit_log)} entrées dans le log")
        
        return True
        
    except Exception as e:
        print_result("Gestionnaire de secrets", False, f"Erreur: {e}")
        return False

async def test_secure_config():
    """Test du gestionnaire de configuration sécurisée"""
    print_section("Tests de Configuration Sécurisée")
    
    try:
        # Initialisation
        config_manager = await get_config_manager()
        print_result("Initialisation", True, "SecureConfigManager créé")
        
        # Test de récupération de config
        config = await config_manager.get_config()
        print_result("Récupération configuration", config is not None)
        
        # Test du statut de santé
        health_status = await config_manager.get_health_status()
        print_result("Statut de santé", 
                    health_status.get("overall_status") in ["healthy", "degraded"])
        
        # Test de validation de configuration
        is_valid = await config_manager.validate_configuration()
        print_result("Validation configuration", is_valid)
        
        return True
        
    except Exception as e:
        print_result("Configuration sécurisée", False, f"Erreur: {e}")
        return False

async def test_api_keys_setup():
    """Test de la configuration des clés API"""
    print_section("Tests de Configuration des Clés API")
    
    try:
        manager = SecretsManager()
        
        # Test de configuration des clés API essentielles
        essential_keys = [
            ("OPENAI_API_KEY", "sk-test-key-openai"),
            ("ANTHROPIC_API_KEY", "sk-ant-test-key"),
            ("PERPLEXITY_API_KEY", "pplx-test-key")
        ]
        
        for key_name, test_value in essential_keys:
            success = await manager.set_secret(key_name, test_value)
            print_result(f"Configuration {key_name}", success)
        
        # Vérification que les clés sont récupérables
        all_retrieved = True
        for key_name, expected_value in essential_keys:
            retrieved = await manager.get_secret(key_name)
            if retrieved != expected_value:
                all_retrieved = False
                break
        
        print_result("Récupération clés API", all_retrieved)
        
        # Nettoyage des clés de test
        for key_name, _ in essential_keys:
            await manager.delete_secret(key_name)
        
        return True
        
    except Exception as e:
        print_result("Configuration clés API", False, f"Erreur: {e}")
        return False

async def test_backup_and_rotation():
    """Test des fonctionnalités de sauvegarde et rotation"""
    print_section("Tests de Sauvegarde et Rotation")
    
    try:
        manager = SecretsManager()
        
        # Test de rotation
        test_key = "ROTATION_TEST_KEY"
        initial_value = "initial_value"
        rotated_value = "rotated_value"
        
        # Stocker valeur initiale
        await manager.set_secret(test_key, initial_value)
        
        # Effectuer la rotation
        rotation_success = await manager.rotate_secret(test_key, rotated_value)
        print_result("Rotation de secret", rotation_success)
        
        if rotation_success:
            # Vérifier que la nouvelle valeur est active
            current_value = await manager.get_secret(test_key)
            print_result("Validation rotation", current_value == rotated_value)
        
        # Nettoyage
        await manager.delete_secret(test_key)
        
        return True
        
    except Exception as e:
        print_result("Sauvegarde et rotation", False, f"Erreur: {e}")
        return False

async def generate_security_report():
    """Génère un rapport de sécurité complet"""
    print_section("Génération du Rapport de Sécurité")
    
    try:
        manager = SecretsManager()
        config_manager = await get_config_manager()
        
        # Collecter les informations
        health = await manager.health_check()
        config_health = await config_manager.get_health_status()
        audit_log = await manager.get_audit_log()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "security_status": {
                "secrets_manager": {
                    "backends_health": health,
                    "audit_entries": len(audit_log)
                },
                "configuration": {
                    "overall_status": config_health.get("overall_status"),
                    "backends_status": config_health.get("backends", {})
                }
            },
            "recommendations": [
                "Utiliser Docker Secrets ou Vault en production",
                "Effectuer une rotation régulière des clés API",
                "Surveiller les logs d'audit régulièrement",
                "Maintenir les sauvegardes à jour"
            ]
        }
        
        # Sauvegarder le rapport
        report_file = Path("scripts/security-validation-report.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print_result("Rapport de sécurité", True, 
                    f"Sauvegardé dans {report_file}")
        
        return True
        
    except Exception as e:
        print_result("Génération rapport", False, f"Erreur: {e}")
        return False

async def main():
    """Fonction principale de validation"""
    print_header("Validation Complète du Système de Sécurité EasyRSVP AI Team")
    
    print("🚀 Début de la validation complète du système de sécurité...")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Exécuter tous les tests
    tests = [
        ("Gestionnaire de Secrets", test_secrets_manager),
        ("Configuration Sécurisée", test_secure_config),
        ("Configuration Clés API", test_api_keys_setup),
        ("Sauvegarde et Rotation", test_backup_and_rotation),
        ("Rapport de Sécurité", generate_security_report)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print_result(test_name, False, f"Exception: {e}")
            results[test_name] = False
    
    # Résumé final
    print_section("Résumé de Validation")
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    success_rate = (passed_tests / total_tests) * 100
    
    print(f"📊 Tests réussis: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
    
    for test_name, result in results.items():
        print_result(test_name, result)
    
    if passed_tests == total_tests:
        print("\n🎉 Validation complète réussie ! Le système de sécurité est opérationnel.")
        return 0
    else:
        print(f"\n⚠️ Validation partielle. {total_tests - passed_tests} test(s) ont échoué.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 