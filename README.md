# 🤖 Équipe IA - Workflow n8n pour EasyRSVP

## Vue d'ensemble

Système d'automatisation avancé utilisant n8n et CrewAI pour orchestrer une équipe complète d'agents IA spécialisés dans le développement de l'application EasyRSVP.

## 🏗️ Architecture

### Agents IA Spécialisés
- **Product Owner Agent** - Analyse des user stories et spécifications
- **Tech Lead Agent** - Architecture technique et conception
- **Frontend Developer Agent** - Développement React/Next.js
- **Backend Developer Agent** - APIs et logique métier
- **QA Agent** - Tests et validation qualité
- **DevOps Agent** - Déploiement et monitoring

### Stack Technique
- **Framework**: Next.js 15 avec App Router
- **Language**: TypeScript (strict mode)
- **Styling**: Tailwind CSS v4 + shadcn/ui
- **Database**: Turso (SQLite)
- **Deployment**: Vercel
- **Orchestration**: n8n + CrewAI
- **CI/CD**: GitHub Actions

## 🚀 Workflows Principaux

### 1. Feature Development Pipeline
Workflow complet du développement d'une fonctionnalité :
`Webhook → Product Owner → Tech Lead → [Frontend + Backend] → QA → DevOps`

### 2. Daily Standup Workflow
Rapport quotidien automatisé de l'avancement de tous les agents.

### 3. Code Review Workflow
Review automatique lors des pushs Git avec feedback des agents.

### 4. Bug Fixing Workflow
Détection, assignation et résolution automatique des bugs.

## 📊 Monitoring

### Métriques Trackées
- Vélocité de développement (features/semaine)
- Qualité du code (score QA moyen)
- Temps de cycle (user story → production)
- Couverture de tests

### Notifications
- Slack/Discord pour les déploiements
- Email pour les erreurs critiques
- Dashboard temps réel

## 🛠️ Installation

```bash
# 1. Installer les dépendances
npm install

# 2. Configurer n8n
docker-compose up -d n8n

# 3. Importer les workflows
npm run import-workflows

# 4. Configurer les variables d'environnement
cp .env.example .env
```

## 📝 Configuration

1. **API Keys requis** :
   - OpenAI API Key
   - Vercel API Token
   - GitHub Token
   - Slack/Discord Webhooks

2. **Variables d'environnement** :
   Voir `.env.example` pour la liste complète

## 🔄 Utilisation

### Démarrer un nouveau développement
```bash
# Via webhook n8n
curl -X POST https://n8n.example.com/webhook/feature-dev \
  -H "Content-Type: application/json" \
  -d '{"user_story": "US4.1.1", "priority": "high"}'
```

### Monitoring en temps réel
```bash
# Dashboard des métriques
npm run dashboard

# Logs des agents
npm run logs
```

## 📁 Structure du Projet

```
├── agents/               # Configuration des agents CrewAI
├── workflows/           # Workflows n8n (JSON exports)
├── scripts/            # Scripts d'automatisation
├── monitoring/         # Configuration monitoring
├── docs/              # Documentation détaillée
└── tests/             # Tests du système
```

## 🤝 Contribution

1. Créer une branche pour la nouvelle fonctionnalité
2. Les agents IA valideront automatiquement votre code
3. Merge automatique après validation QA

## 📄 License

MIT License - Voir LICENSE.md 