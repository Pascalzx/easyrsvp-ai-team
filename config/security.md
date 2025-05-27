# 🔐 EasyRSVP AI Team - Configuration de Sécurité

## Vue d'ensemble

Ce document décrit la configuration de sécurité complète pour le système d'équipe IA EasyRSVP, incluant la gestion des API keys, le chiffrement, et les mesures de protection.

## 📋 API Keys Nécessaires

### Services IA (Obligatoires)
- **OpenAI** : `OPENAI_API_KEY`
  - Obtenir sur : https://platform.openai.com/api-keys
  - Permissions : Accès API complet
  - Usage : Agent principal pour génération de code

- **Anthropic (Claude)** : `ANTHROPIC_API_KEY`
  - Obtenir sur : https://console.anthropic.com/
  - Permissions : API Access
  - Usage : Agent de fallback et révision de code

- **Perplexity** : `PERPLEXITY_API_KEY`
  - Obtenir sur : https://www.perplexity.ai/settings/api
  - Permissions : API Access
  - Usage : Recherche et contexte pour les agents

### Services de Communication (Optionnels)
- **Slack** : `SLACK_BOT_TOKEN` & `SLACK_WEBHOOK_URL`
  - Bot Token : https://api.slack.com/apps → Your App → OAuth & Permissions
  - Webhook : https://api.slack.com/apps → Your App → Incoming Webhooks
  - Permissions : `chat:write`, `files:write`, `channels:read`
  - Usage : Notifications et rapports d'équipe

- **Discord** : `DISCORD_BOT_TOKEN` & `DISCORD_WEBHOOK_URL`
  - Bot Token : https://discord.com/developers/applications
  - Webhook : Channel Settings → Integrations → Webhooks
  - Permissions : Send Messages, Embed Links
  - Usage : Notifications alternatives

### Services de Développement
- **GitHub** : `GITHUB_TOKEN`
  - Obtenir sur : https://github.com/settings/tokens
  - Permissions : `repo`, `write:packages`, `workflow`
  - Usage : Gestion du code et déploiement

- **Vercel** : `VERCEL_TOKEN`
  - Obtenir sur : https://vercel.com/account/tokens
  - Permissions : Deploy
  - Usage : Déploiement automatisé

### Services Monitoring (Optionnels)
- **Sentry** : `SENTRY_DSN`
  - Obtenir sur : https://sentry.io/
  - Usage : Monitoring des erreurs

## 🔒 Configuration des Secrets

### Option 1 : Docker Secrets (Recommandé)

```bash
# Créer les secrets Docker
echo "your_openai_key" | docker secret create openai_api_key -
echo "your_anthropic_key" | docker secret create anthropic_api_key -
echo "your_slack_token" | docker secret create slack_bot_token -
```

### Option 2 : HashiCorp Vault

```bash
# Configuration Vault
vault secrets enable -path=easyRSVP kv-v2
vault kv put easyRSVP/api-keys \
  openai_key="your_openai_key" \
  anthropic_key="your_anthropic_key"
```

### Option 3 : Variables d'environnement (Développement uniquement)

```bash
# Fichier .env (Ne JAMAIS committer)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
PERPLEXITY_API_KEY=pplx-...
SLACK_BOT_TOKEN=xoxb-...
DISCORD_BOT_TOKEN=...
GITHUB_TOKEN=ghp_...
VERCEL_TOKEN=...
```

## 🛡️ Mesures de Sécurité

### 1. Chiffrement
- **TLS 1.3** pour toutes les communications
- **AES-256** pour le chiffrement au repos
- **Certificats SSL** automatiquement renouvelés

### 2. Authentification API
```python
# Exemple d'authentification JWT
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_token(token: str = Depends(security)):
    # Vérification du token JWT
    if not verify_jwt(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide"
        )
```

### 3. Limitation de Débit (Rate Limiting)
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/agents")
@limiter.limit("100/minute")  # 100 requêtes par minute max
async def get_agents():
    pass
```

### 4. Validation des Entrées
```python
from pydantic import BaseModel, validator

class UserStoryRequest(BaseModel):
    user_story: str
    
    @validator('user_story')
    def validate_user_story(cls, v):
        if len(v) > 1000:
            raise ValueError('User story trop longue')
        if any(char in v for char in ['<', '>', '&']):
            raise ValueError('Caractères non autorisés')
        return v
```

## 🔍 Monitoring de Sécurité

### Logs de Sécurité
```python
import logging
from datetime import datetime

security_logger = logging.getLogger('security')

def log_security_event(event_type: str, details: dict):
    security_logger.warning({
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "details": details,
        "severity": "HIGH" if event_type in ["auth_failure", "injection_attempt"] else "MEDIUM"
    })
```

### Alertes Automatiques
- Tentatives d'authentification échouées (> 5/minute)
- Requêtes suspectes (injection SQL, XSS)
- Usage anormal d'API (quota dépassé)
- Accès depuis IPs non autorisées

## 📊 Audit et Conformité

### Checklist de Sécurité
- [ ] Toutes les API keys sont stockées de manière sécurisée
- [ ] Aucune clé n'est exposée dans le code source
- [ ] TLS activé sur tous les endpoints
- [ ] Rate limiting configuré
- [ ] Logs de sécurité activés
- [ ] Monitoring d'intrusion en place
- [ ] Sauvegarde chiffrée configurée
- [ ] Plan de récupération testé

### Tests de Pénétration
```bash
# Tests automatisés avec OWASP ZAP
docker run -t owasp/zap2docker-stable zap-baseline.py \
  -t http://localhost:8000 \
  -J zap-report.json
```

## 🚨 Plan d'Incident

### En cas de compromission d'API Key
1. **Immédiat** : Révoquer la clé compromise
2. **Court terme** : Générer une nouvelle clé
3. **Audit** : Vérifier les logs d'accès
4. **Communication** : Notifier l'équipe
5. **Prévention** : Renforcer les mesures

### Contacts d'Urgence
- **Admin Sécurité** : security@easyrsvp.com
- **DevOps Lead** : devops@easyrsvp.com
- **Escalation** : +33 X XX XX XX XX

## 📚 Ressources

- [OWASP Top 10](https://owasp.org/Top10/)
- [Security Best Practices FastAPI](https://fastapi.tiangolo.com/tutorial/security/)
- [Docker Secrets](https://docs.docker.com/engine/swarm/secrets/)
- [HashiCorp Vault](https://www.vaultproject.io/docs)

---

**⚠️ Important** : Ce document contient des informations sensibles. Accès restreint aux membres autorisés de l'équipe. 