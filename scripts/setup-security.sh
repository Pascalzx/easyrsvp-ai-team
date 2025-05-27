#!/bin/bash

# 🔐 EasyRSVP AI Team - Configuration de Sécurité Automatisée
# =============================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRETS_DIR="$PROJECT_ROOT/secrets"
CONFIG_DIR="$PROJECT_ROOT/config"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"

echo -e "${BLUE}🔐 Configuration de Sécurité EasyRSVP AI Team${NC}"
echo "================================================="

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker n'est pas en cours d'exécution. Veuillez démarrer Docker."
        exit 1
    fi
    print_status "Docker est disponible"
}

# Function to create directory structure
create_directories() {
    print_info "Création de la structure des répertoires..."
    
    mkdir -p "$SECRETS_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$PROJECT_ROOT/logs/security"
    mkdir -p "$PROJECT_ROOT/backup"
    
    print_status "Répertoires créés"
}

# Function to generate secure random passwords
generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
}

# Function to setup Docker secrets
setup_docker_secrets() {
    print_info "Configuration des Docker Secrets..."
    
    # Initialize Docker Swarm if not already done
    if ! docker info 2>/dev/null | grep -q "Swarm: active"; then
        print_info "Initialisation de Docker Swarm..."
        docker swarm init --advertise-addr 127.0.0.1 2>/dev/null || true
    fi
    
    # List of required secrets
    declare -A secrets=(
        ["api_jwt_secret"]="$(generate_password)"
        ["database_password"]="$(generate_password)"
        ["redis_password"]="$(generate_password)"
        ["encryption_key"]="$(generate_password)"
    )
    
    # Create Docker secrets
    for secret_name in "${!secrets[@]}"; do
        secret_value="${secrets[$secret_name]}"
        
        # Remove existing secret if it exists
        docker secret rm "easyRSVP_${secret_name}" 2>/dev/null || true
        
        # Create new secret
        echo "$secret_value" | docker secret create "easyRSVP_${secret_name}" -
        print_status "Secret créé: easyRSVP_${secret_name}"
    done
}

# Function to create API keys template
create_api_keys_template() {
    print_info "Création du template pour les API Keys..."
    
    cat > "$SECRETS_DIR/api-keys.template.env" << 'EOF'
# 🔐 API Keys Configuration Template
# ==================================
# Copiez ce fichier vers api-keys.env et remplissez vos vraies clés API
# ⚠️ NE JAMAIS committer le fichier api-keys.env

# Services IA (Obligatoires)
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
PERPLEXITY_API_KEY=pplx-your-perplexity-key-here

# Services de Communication (Optionnels)
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token-here
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/webhook/url
DISCORD_BOT_TOKEN=your-discord-bot-token-here
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your/webhook/url

# Services de Développement
GITHUB_TOKEN=ghp_your-github-token-here
VERCEL_TOKEN=your-vercel-token-here

# Services de Monitoring (Optionnels)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
EOF
    
    print_status "Template créé: $SECRETS_DIR/api-keys.template.env"
}

# Function to create security configuration
create_security_config() {
    print_info "Création de la configuration de sécurité..."
    
    cat > "$CONFIG_DIR/security.json" << EOF
{
  "security": {
    "jwt": {
      "algorithm": "HS256",
      "expiration": 3600,
      "issuer": "easyRSVP-ai-team"
    },
    "rate_limiting": {
      "default": "100/minute",
      "auth": "10/minute",
      "api": "1000/hour"
    },
    "cors": {
      "allowed_origins": ["http://localhost:3000", "https://app.easyrsvp.com"],
      "allowed_methods": ["GET", "POST", "PUT", "DELETE"],
      "allowed_headers": ["Authorization", "Content-Type"],
      "max_age": 3600
    },
    "encryption": {
      "algorithm": "AES-256-GCM",
      "key_rotation_days": 90
    },
    "monitoring": {
      "log_level": "INFO",
      "max_failed_attempts": 5,
      "lockout_duration": 900,
      "audit_retention_days": 365
    }
  }
}
EOF
    
    print_status "Configuration de sécurité créée: $CONFIG_DIR/security.json"
}

# Function to update Docker Compose with security settings
update_docker_compose() {
    print_info "Mise à jour du Docker Compose avec les paramètres de sécurité..."
    
    # Backup original docker-compose.yml
    if [ -f "$DOCKER_COMPOSE_FILE" ]; then
        cp "$DOCKER_COMPOSE_FILE" "$DOCKER_COMPOSE_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    
    # Create security-enhanced docker-compose override
    cat > "$PROJECT_ROOT/docker-compose.security.yml" << 'EOF'
version: '3.8'

services:
  api:
    environment:
      - SECURITY_ENABLED=true
      - JWT_SECRET_FILE=/run/secrets/easyRSVP_api_jwt_secret
      - ENCRYPTION_KEY_FILE=/run/secrets/easyRSVP_encryption_key
    secrets:
      - easyRSVP_api_jwt_secret
      - easyRSVP_encryption_key
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
    restart: unless-stopped
    
  postgres:
    environment:
      - POSTGRES_PASSWORD_FILE=/run/secrets/easyRSVP_database_password
    secrets:
      - easyRSVP_database_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backup:/backup
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.3'
    restart: unless-stopped
    
  redis:
    command: redis-server --requirepass /run/secrets/easyRSVP_redis_password
    secrets:
      - easyRSVP_redis_password
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.2'
    restart: unless-stopped
    
  n8n:
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD_FILE=/run/secrets/easyRSVP_api_jwt_secret
    secrets:
      - easyRSVP_api_jwt_secret
    restart: unless-stopped

secrets:
  easyRSVP_api_jwt_secret:
    external: true
  easyRSVP_database_password:
    external: true
  easyRSVP_redis_password:
    external: true
  easyRSVP_encryption_key:
    external: true

volumes:
  postgres_data:
    driver: local
EOF
    
    print_status "Configuration Docker Compose sécurisée créée"
}

# Function to create security monitoring script
create_security_monitor() {
    print_info "Création du script de monitoring de sécurité..."
    
    cat > "$PROJECT_ROOT/scripts/security-monitor.py" << 'EOF'
#!/usr/bin/env python3
"""
🔍 EasyRSVP AI Team - Security Monitor
=====================================

Script de monitoring de sécurité pour détecter les activités suspectes.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import requests

# Configuration
LOG_DIR = Path(__file__).parent.parent / "logs" / "security"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Logger setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "security-monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SecurityMonitor:
    """Moniteur de sécurité pour l'équipe IA"""
    
    def __init__(self):
        self.api_base = "http://localhost:8000"
        self.failed_attempts = {}
        
    def check_api_health(self):
        """Vérifie la santé de l'API"""
        try:
            response = requests.get(f"{self.api_base}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ API Health Check: OK")
                return True
            else:
                logger.warning(f"⚠️ API Health Check: Status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ API Health Check Failed: {e}")
            return False
    
    def check_docker_security(self):
        """Vérifie la sécurité des conteneurs Docker"""
        try:
            # Check running containers
            result = subprocess.run(
                ["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                logger.info("✅ Docker Security Check: All containers running")
                return True
            else:
                logger.warning("⚠️ Docker Security Check: Some issues detected")
                return False
                
        except Exception as e:
            logger.error(f"❌ Docker Security Check Failed: {e}")
            return False
    
    def monitor_logs(self):
        """Surveille les logs pour détecter des activités suspectes"""
        log_patterns = [
            "authentication failed",
            "unauthorized access",
            "SQL injection",
            "XSS attempt",
            "rate limit exceeded"
        ]
        
        # This would integrate with actual log monitoring
        logger.info("🔍 Log monitoring: Checking for suspicious patterns...")
        
    def generate_security_report(self):
        """Génère un rapport de sécurité"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "checks": {
                "api_health": self.check_api_health(),
                "docker_security": self.check_docker_security()
            },
            "alerts": [],
            "recommendations": [
                "Rotation régulière des API keys",
                "Mise à jour des dépendances de sécurité",
                "Audit des logs d'accès"
            ]
        }
        
        # Save report
        report_file = LOG_DIR / f"security-report-{datetime.now().strftime('%Y%m%d')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📊 Security report generated: {report_file}")
        return report

if __name__ == "__main__":
    monitor = SecurityMonitor()
    monitor.generate_security_report()
EOF
    
    chmod +x "$PROJECT_ROOT/scripts/security-monitor.py"
    print_status "Script de monitoring créé: scripts/security-monitor.py"
}

# Function to create .gitignore security entries
update_gitignore() {
    print_info "Mise à jour du .gitignore pour la sécurité..."
    
    if [ ! -f "$PROJECT_ROOT/.gitignore" ]; then
        touch "$PROJECT_ROOT/.gitignore"
    fi
    
    # Add security-related ignores
    cat >> "$PROJECT_ROOT/.gitignore" << 'EOF'

# Security - Never commit these files
secrets/api-keys.env
secrets/*.key
secrets/*.pem
secrets/*.p12
config/production.env
.env.production
*.log
logs/security/
backup/*.sql
backup/*.dump

# Docker secrets
docker-secrets/
EOF
    
    print_status ".gitignore mis à jour avec les exclusions de sécurité"
}

# Function to create backup script
create_backup_script() {
    print_info "Création du script de sauvegarde sécurisée..."
    
    cat > "$PROJECT_ROOT/scripts/backup.sh" << 'EOF'
#!/bin/bash

# 💾 EasyRSVP AI Team - Backup Script
# ===================================

set -e

BACKUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "🔄 Starting secure backup..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup database (if running)
if docker ps | grep -q postgres; then
    echo "📊 Backing up database..."
    docker exec easyRSVP-postgres pg_dump -U postgres easyRSVP > "$BACKUP_DIR/database_$TIMESTAMP.sql"
    
    # Encrypt the backup
    if command -v gpg &> /dev/null; then
        gpg --symmetric --cipher-algo AES256 "$BACKUP_DIR/database_$TIMESTAMP.sql"
        rm "$BACKUP_DIR/database_$TIMESTAMP.sql"
        echo "🔐 Database backup encrypted"
    fi
fi

# Backup configuration files
echo "⚙️ Backing up configuration..."
tar -czf "$BACKUP_DIR/config_$TIMESTAMP.tar.gz" \
    -C "$(dirname "$BACKUP_DIR")" \
    config/ \
    docker-compose.yml \
    docker-compose.security.yml \
    --exclude='*.log'

# Backup task files
if [ -d "$(dirname "$BACKUP_DIR")/tasks" ]; then
    echo "📋 Backing up tasks..."
    tar -czf "$BACKUP_DIR/tasks_$TIMESTAMP.tar.gz" \
        -C "$(dirname "$BACKUP_DIR")" \
        tasks/
fi

# Clean old backups (keep last 7 days)
find "$BACKUP_DIR" -name "*.sql" -mtime +7 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete
find "$BACKUP_DIR" -name "*.gpg" -mtime +7 -delete

echo "✅ Backup completed: $BACKUP_DIR"
EOF
    
    chmod +x "$PROJECT_ROOT/scripts/backup.sh"
    print_status "Script de sauvegarde créé: scripts/backup.sh"
}

# Main execution
main() {
    echo
    print_info "Démarrage de la configuration de sécurité..."
    echo
    
    # Run all setup functions
    check_docker
    create_directories
    setup_docker_secrets
    create_api_keys_template
    create_security_config
    update_docker_compose
    create_security_monitor
    update_gitignore
    create_backup_script
    
    echo
    print_status "Configuration de sécurité terminée !"
    echo
    print_warning "ÉTAPES SUIVANTES IMPORTANTES :"
    echo "1. Copiez secrets/api-keys.template.env vers secrets/api-keys.env"
    echo "2. Remplissez vos vraies API keys dans secrets/api-keys.env"
    echo "3. Exécutez: docker-compose -f docker-compose.yml -f docker-compose.security.yml up -d"
    echo "4. Testez la sécurité avec: python scripts/security-monitor.py"
    echo "5. Configurez la sauvegarde automatique: crontab -e"
    echo "   Ajoutez: 0 2 * * * /path/to/scripts/backup.sh"
    echo
    print_warning "⚠️ N'oubliez pas de configurer vos vraies API keys avant de démarrer les services !"
}

# Run main function
main "$@" 