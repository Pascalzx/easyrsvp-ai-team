# 📦 Guide d'Installation Détaillé

> **Instructions complètes pour installer et configurer EasyRSVP AI Team**

## 📋 Table des Matières

- [🔧 Prérequis Système](#-prérequis-système)
- [⚡ Installation Rapide](#-installation-rapide)
- [🐳 Installation avec Docker](#-installation-avec-docker)
- [🔧 Installation Manuelle](#-installation-manuelle)
- [🌐 Configuration n8n](#-configuration-n8n)
- [🔐 Configuration des Secrets](#-configuration-des-secrets)
- [✅ Vérification de l'Installation](#-vérification-de-linstallation)
- [🚀 Premier Déploiement](#-premier-déploiement)

---

## 🔧 Prérequis Système

### Minimum Requis

| Composant | Version Minimale | Recommandé |
|-----------|------------------|------------|
| **OS** | Ubuntu 20.04+ / macOS 11+ / Windows 10+ | Ubuntu 22.04 LTS |
| **RAM** | 8 GB | 16 GB |
| **Stockage** | 20 GB libre | 50 GB SSD |
| **CPU** | 4 cores | 8+ cores |
| **Network** | Accès Internet stable | Fibre optique |

### Logiciels Requis

```bash
# 1. Docker & Docker Compose
docker --version          # >= 24.0.0
docker-compose --version  # >= 2.20.0

# 2. Node.js & npm
node --version            # >= 18.17.0
npm --version             # >= 9.6.7

# 3. Python
python3 --version        # >= 3.11.0
pip3 --version           # >= 23.0.0

# 4. Git
git --version            # >= 2.30.0
```

### Installation des Prérequis

#### 🐧 Ubuntu/Debian

```bash
# Mise à jour du système
sudo apt update && sudo apt upgrade -y

# Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker $USER

# Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Node.js (via NodeSource)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Python 3.11
sudo apt install python3.11 python3.11-venv python3.11-pip -y

# Git
sudo apt install git -y
```

#### 🍎 macOS

```bash
# Homebrew (si pas installé)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Docker Desktop
brew install --cask docker

# Node.js
brew install node@18

# Python 3.11
brew install python@3.11

# Git
brew install git
```

#### 🪟 Windows

```powershell
# Chocolatey (si pas installé)
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Docker Desktop
choco install docker-desktop

# Node.js
choco install nodejs --version=18.17.1

# Python
choco install python --version=3.11.5

# Git
choco install git
```

---

## ⚡ Installation Rapide

### 🚀 Script d'Installation Automatique

```bash
# Télécharger et exécuter le script d'installation
curl -fsSL https://raw.githubusercontent.com/your-org/easyRSVP-ai-team/main/scripts/install.sh | bash

# Ou pour un contrôle manuel :
wget https://raw.githubusercontent.com/your-org/easyRSVP-ai-team/main/scripts/install.sh
chmod +x install.sh
./install.sh
```

### 📝 Installation Manuelle Rapide

```bash
# 1. Cloner le repository
git clone https://github.com/your-org/easyRSVP-ai-team.git
cd easyRSVP-ai-team

# 2. Configuration initiale
cp env.example .env
echo "🔧 Éditez le fichier .env avec vos API keys"

# 3. Installation des dépendances
npm install
pip3 install -r requirements.txt

# 4. Démarrage rapide
docker-compose up -d

# 5. Vérification
sleep 30  # Attendre que les services démarrent
curl http://localhost:3000/health
```

---

## 🐳 Installation avec Docker

### 📋 Configuration Docker Complète

#### 1. **Préparation de l'environnement**

```bash
# Créer les répertoires nécessaires
mkdir -p {data/postgres,data/redis,data/n8n,logs,secrets}

# Permissions appropriées
sudo chown -R $USER:$USER data/ logs/ secrets/
chmod 755 data/ logs/ secrets/
```

#### 2. **Configuration Docker Compose**

```yaml
# docker-compose.prod.yml - Configuration de production
version: '3.8'

services:
  # PostgreSQL pour n8n
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: n8n
      POSTGRES_USER: n8n
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U n8n"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis pour le cache
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - ./data/redis:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  # n8n - Orchestrateur principal
  n8n:
    image: n8nio/n8n:latest
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=${N8N_USER}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD}
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - DB_POSTGRESDB_USER=n8n
      - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
      - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
      - WEBHOOK_URL=https://your-domain.com/
    ports:
      - "5678:5678"
    volumes:
      - ./data/n8n:/home/node/.n8n
      - ./workflows:/home/node/workflows
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  # API des Agents IA
  agents-api:
    build:
      context: .
      dockerfile: Dockerfile.agents
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=${DATABASE_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    ports:
      - "3000:3000"
    volumes:
      - ./agents:/app/agents
      - ./logs:/app/logs
      - ./secrets:/run/secrets
    depends_on:
      - redis
      - postgres
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Traefik pour le reverse proxy (Production)
  traefik:
    image: traefik:v3.0
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.email=${ACME_EMAIL}"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"  # Dashboard Traefik
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./data/letsencrypt:/letsencrypt
    restart: unless-stopped

  # Monitoring avec Prometheus
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./data/prometheus:/prometheus
    restart: unless-stopped

  # Grafana pour les dashboards
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - ./data/grafana:/var/lib/grafana
      - ./config/grafana:/etc/grafana/provisioning
    restart: unless-stopped

networks:
  default:
    driver: bridge
```

#### 3. **Variables d'environnement pour Production**

```bash
# .env.production
# Base de données
POSTGRES_PASSWORD=your_secure_postgres_password
REDIS_PASSWORD=your_secure_redis_password

# n8n Configuration
N8N_USER=admin
N8N_PASSWORD=your_secure_n8n_password
N8N_ENCRYPTION_KEY=your_32_character_encryption_key

# API Keys
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
PERPLEXITY_API_KEY=pplx-your-perplexity-key
GITHUB_TOKEN=ghp_your-github-token

# Notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/slack/webhook
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your/discord/webhook

# Monitoring
SENTRY_DSN=https://your-sentry-dsn
GRAFANA_PASSWORD=your_grafana_password

# SSL & Domaine
ACME_EMAIL=your-email@domain.com
DOMAIN=your-domain.com

# Base de données application
DATABASE_URL=postgresql://user:password@localhost:5432/easyRSVP
```

#### 4. **Démarrage en Production**

```bash
# Démarrage avec le fichier de production
docker-compose -f docker-compose.prod.yml up -d

# Vérification des logs
docker-compose -f docker-compose.prod.yml logs -f

# Vérification du statut
docker-compose -f docker-compose.prod.yml ps
```

---

## 🔧 Installation Manuelle

### 📝 Installation Étape par Étape

#### 1. **Préparation de l'environnement Python**

```bash
# Créer un environnement virtuel
python3.11 -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate     # Windows

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Installation des dépendances Python
pip install -r requirements.txt

# Vérification des packages critiques
pip show crewai anthropic openai fastapi uvicorn
```

#### 2. **Installation des dépendances Node.js**

```bash
# Installation des packages
npm install

# Vérification des packages critiques
npm list @types/node typescript next tailwindcss

# Build du projet (si nécessaire)
npm run build
```

#### 3. **Configuration de la base de données**

```bash
# PostgreSQL local
sudo -u postgres createdb easyRSVP
sudo -u postgres createuser easyRSVP_user

# Configuration des permissions
sudo -u postgres psql -c "ALTER USER easyRSVP_user PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE easyRSVP TO easyRSVP_user;"

# Test de connexion
psql -h localhost -U easyRSVP_user -d easyRSVP -c "SELECT version();"
```

#### 4. **Configuration Redis**

```bash
# Installation Redis (Ubuntu)
sudo apt install redis-server

# Configuration sécurisée
sudo nano /etc/redis/redis.conf
# Décommenter et configurer :
# requirepass your_redis_password
# bind 127.0.0.1

# Redémarrage
sudo systemctl restart redis-server
sudo systemctl enable redis-server

# Test
redis-cli ping
# Réponse attendue : PONG
```

---

## 🌐 Configuration n8n

### 📋 Installation n8n

#### 1. **Installation via npm**

```bash
# Installation globale
npm install -g n8n

# Ou installation locale dans le projet
npm install n8n
```

#### 2. **Configuration initiale**

```bash
# Variables d'environnement n8n
export N8N_BASIC_AUTH_ACTIVE=true
export N8N_BASIC_AUTH_USER=admin
export N8N_BASIC_AUTH_PASSWORD=your_secure_password
export N8N_ENCRYPTION_KEY=your_32_character_encryption_key
export WEBHOOK_URL=https://your-domain.com/

# Démarrage
n8n start
```

#### 3. **Import des workflows**

```bash
# Copier les workflows dans n8n
cp workflows/*.json ~/.n8n/workflows/

# Ou via l'interface web n8n
# Accéder à http://localhost:5678
# Importer les fichiers JSON des workflows
```

### 🔗 Configuration des Webhooks

#### 1. **URLs de Webhooks**

```bash
# Feature Development Pipeline
https://your-domain.com/webhook/feature-development

# Daily Standup
https://your-domain.com/webhook/daily-standup

# Code Review
https://your-domain.com/webhook/code-review

# Bug Fix
https://your-domain.com/webhook/bug-fix
```

#### 2. **Test des Webhooks**

```bash
# Test Feature Development
curl -X POST https://your-domain.com/webhook/feature-development \
  -H "Content-Type: application/json" \
  -d '{
    "user_story": "Test user story",
    "priority": "medium"
  }'

# Vérifier les logs n8n pour confirmer la réception
```

---

## 🔐 Configuration des Secrets

### 🏗️ Choix du Backend de Secrets

#### Option 1 : Docker Secrets (Recommandé pour Production)

```bash
# Créer les secrets Docker
docker secret create easyRSVP_openai_key your_openai_key.txt
docker secret create easyRSVP_anthropic_key your_anthropic_key.txt
docker secret create easyRSVP_github_token your_github_token.txt

# Vérification
docker secret ls
```

#### Option 2 : HashiCorp Vault

```bash
# Installation Vault
wget https://releases.hashicorp.com/vault/1.15.0/vault_1.15.0_linux_amd64.zip
unzip vault_1.15.0_linux_amd64.zip
sudo mv vault /usr/local/bin/

# Démarrage en mode dev (pour test)
vault server -dev &

# Configuration
export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN="your-vault-token"

# Activation du moteur KV
vault secrets enable -path=easyRSVP kv-v2

# Stockage des secrets
vault kv put easyRSVP/openai value="your-openai-key"
vault kv put easyRSVP/anthropic value="your-anthropic-key"
```

#### Option 3 : Variables d'environnement (Développement uniquement)

```bash
# Fichier .env local
cp env.example .env

# Éditer avec vos vraies clés API
nano .env
```

### 🧪 Test du Gestionnaire de Secrets

```bash
# Test du gestionnaire
python3 -c "
import asyncio
from agents.secrets_manager import get_secrets_manager

async def test():
    manager = await get_secrets_manager()
    health = await manager.health_check()
    print('Health Check:', health)
    
    # Test d'une clé
    await manager.set_secret('test_key', 'test_value')
    value = await manager.get_secret('test_key')
    print('Test Secret:', value == 'test_value')

asyncio.run(test())
"
```

---

## ✅ Vérification de l'Installation

### 🏥 Health Checks

#### 1. **Services de Base**

```bash
# Docker containers
docker ps

# Services spécifiques
curl http://localhost:3000/health           # API Agents
curl http://localhost:5678/healthz          # n8n
curl http://localhost:6379/ping             # Redis (si exposé)

# PostgreSQL
pg_isready -h localhost -p 5432
```

#### 2. **API des Agents**

```bash
# Test de l'API principale
curl http://localhost:3000/api/agents/status

# Test d'un agent spécifique
curl http://localhost:3000/api/agents/product-owner/health

# Test du gestionnaire de secrets
curl http://localhost:3000/api/secrets/health
```

#### 3. **Workflows n8n**

```bash
# Liste des workflows actifs
curl -u admin:password http://localhost:5678/rest/workflows

# Test d'un webhook
curl -X POST http://localhost:5678/webhook/test \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

### 📊 Monitoring Initial

```bash
# Logs des containers
docker-compose logs -f agents-api
docker-compose logs -f n8n

# Métriques système
htop              # Usage CPU/RAM
df -h             # Espace disque
netstat -tulpn    # Ports ouverts
```

---

## 🚀 Premier Déploiement

### 🎯 Test de Fonctionnement Complet

#### 1. **Créer une User Story de Test**

```bash
curl -X POST http://localhost:3000/api/crew/feature-development \
  -H "Content-Type: application/json" \
  -d '{
    "user_story": "En tant qu'utilisateur, je veux voir une page d'accueil simple avec le message \"Hello EasyRSVP AI Team\"",
    "priority": "high",
    "deadline": "2024-01-20"
  }'
```

#### 2. **Suivre le Progression**

```bash
# Surveiller les logs des agents
docker-compose logs -f agents-api

# Vérifier le statut via l'API
curl http://localhost:3000/api/tasks/status

# Accéder à l'interface n8n
open http://localhost:5678
```

#### 3. **Vérifier les Résultats**

```bash
# Liste des tâches créées
curl http://localhost:3000/api/tasks | jq '.'

# Détails d'une tâche spécifique
curl http://localhost:3000/api/tasks/1 | jq '.'

# Statut de l'équipe
curl http://localhost:3000/api/metrics/team | jq '.'
```

### 🎉 Résultat Attendu

Après 5-10 minutes, vous devriez avoir :
- ✅ User story analysée par le Product Owner
- ✅ Architecture planifiée par le Tech Lead
- ✅ Code frontend/backend généré
- ✅ Tests créés par le QA Engineer
- ✅ Déploiement préparé par le DevOps Engineer

---

## 🔧 Troubleshooting

### ❗ Problèmes Courants

#### 1. **API Keys Non Reconnues**

```bash
# Vérifier les secrets
python3 -c "
import asyncio
from agents.secrets_manager import get_secrets_manager

async def check():
    manager = await get_secrets_manager()
    keys = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GITHUB_TOKEN']
    for key in keys:
        value = await manager.get_secret(key)
        print(f'{key}: {'✅' if value else '❌'}')

asyncio.run(check())
"
```

#### 2. **Containers qui ne Démarrent Pas**

```bash
# Vérifier les logs d'erreur
docker-compose logs agents-api
docker-compose logs n8n

# Vérifier les ressources
docker system df
docker system prune  # Si nécessaire
```

#### 3. **Base de Données Non Accessible**

```bash
# Test de connexion PostgreSQL
pg_isready -h localhost -p 5432 -U postgres

# Reset si nécessaire
docker-compose down -v
docker-compose up -d postgres
sleep 10
docker-compose up -d
```

### 📞 Support

Si vous rencontrez des problèmes :
1. 📋 Consultez les [logs détaillés](troubleshooting.md#logs)
2. 🔍 Vérifiez la [FAQ](troubleshooting.md#faq)
3. 💬 Contactez le support : support@easyRSVP.com

---

<div align="center">

**✅ Installation Terminée avec Succès !**

[🏠 Retour à la Documentation Principale](README.md) | [🎯 Créer votre Première Feature](feature-development-guide.md)

</div> 