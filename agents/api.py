"""
🤖 EasyRSVP AI Team - FastAPI Application
==========================================

API REST pour exposer les agents CrewAI aux workflows n8n.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import uvicorn
import logging
import json
from datetime import datetime
import os
import asyncio

from .crew_ai_agents import (
    EasyRSVPDevelopmentCrew,
    ProductOwnerAgent,
    TechLeadAgent,
    FrontendAgent,
    BackendAgent,
    QAAgent,
    DevOpsAgent
)
from .taskmaster_integration import taskmaster
from .secure_config import get_config_manager, initialize_config_sync, get_security_config
from .secrets_manager import get_secrets_manager

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sécurité
security = HTTPBearer()

# Initialisation de l'application FastAPI
app = FastAPI(
    title="🤖 EasyRSVP AI Team API",
    description="API REST pour l'équipe d'agents IA CrewAI - EasyRSVP",
    version="1.0.0",
    contact={
        "name": "EasyRSVP Team",
        "email": "team@easyrsvp.com",
    },
    license_info={
        "name": "MIT",
    },
)

# Variables globales pour la configuration
_config_manager = None
_dev_crew = None

# Configuration CORS (sera mise à jour au démarrage avec la config sécurisée)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Sera mis à jour avec la vraie config
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# INITIALISATION SÉCURISÉE
# =============================================================================

async def get_dev_crew():
    """Retourne l'équipe de développement avec configuration sécurisée"""
    global _dev_crew
    if not _dev_crew:
        # Initialiser avec la configuration sécurisée
        config_manager = await get_config_manager()
        config = await config_manager.get_config()
        _dev_crew = EasyRSVPDevelopmentCrew()
    return _dev_crew

async def verify_auth_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Vérifie le token d'authentification JWT"""
    try:
        # Pour l'instant, on accepte tous les tokens valides
        # En production, vérifier la signature JWT
        if not credentials.credentials:
            raise HTTPException(status_code=401, detail="Token manquant")
        return credentials.credentials
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token invalide")

@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage de l'application"""
    try:
        logger.info("🚀 Démarrage de l'API EasyRSVP AI Team...")
        
        # Initialiser la configuration sécurisée
        await initialize_config_sync()
        
        # Obtenir le gestionnaire de configuration
        global _config_manager
        _config_manager = await get_config_manager()
        config = await _config_manager.get_config()
        
        # Mettre à jour la configuration CORS avec les vrais paramètres
        app.user_middleware = []  # Réinitialiser les middlewares
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.security.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
        )
        
        # Initialiser l'équipe de développement
        global _dev_crew
        _dev_crew = EasyRSVPDevelopmentCrew()
        
        logger.info("✅ API initialisée avec succès")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation: {e}")
        raise

# =============================================================================
# MODÈLES PYDANTIC
# =============================================================================

class HealthResponse(BaseModel):
    """Modèle pour la réponse du health check"""
    status: str = "healthy"
    timestamp: str
    version: str = "1.0.0"
    agents_available: int
    services: Dict[str, str]

class UserStoryRequest(BaseModel):
    """Modèle pour les requêtes de développement de user story"""
    user_story: str = Field(..., description="User story à développer")
    prd_context: str = Field("", description="Contexte du PRD")
    mockups: str = Field("", description="Références aux maquettes")
    priority: str = Field("medium", description="Priorité (low/medium/high/critical)")
    environment: str = Field("staging", description="Environnement de déploiement")

class AgentTaskRequest(BaseModel):
    """Modèle pour les tâches individuelles d'agents"""
    agent_type: str = Field(..., description="Type d'agent (product_owner, tech_lead, etc.)")
    task_type: str = Field(..., description="Type de tâche")
    inputs: Dict[str, Any] = Field(..., description="Paramètres d'entrée pour la tâche")
    
class TaskProgressRequest(BaseModel):
    """Modèle pour la mise à jour du progrès des tâches"""
    task_id: str = Field(..., description="ID de la tâche Task Master")
    status: str = Field(..., description="Nouveau statut")
    details: Optional[str] = Field(None, description="Détails supplémentaires")

class DevelopmentResponse(BaseModel):
    """Modèle pour les réponses de développement"""
    status: str
    session_id: str
    phases: Dict[str, Any]
    quality_score: Optional[float] = None
    deployment_url: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class SecretRequest(BaseModel):
    """Modèle pour les requêtes de gestion des secrets"""
    key: str = Field(..., description="Nom du secret")
    value: str = Field(..., description="Valeur du secret")
    backend: Optional[str] = Field(None, description="Backend de stockage")

class SecretResponse(BaseModel):
    """Modèle pour les réponses des secrets"""
    key: str
    exists: bool
    backend: Optional[str] = None
    last_updated: Optional[str] = None

class SecurityStatusResponse(BaseModel):
    """Modèle pour le statut de sécurité"""
    status: str
    secrets_backends: Dict[str, bool]
    api_keys_configured: int
    security_keys_configured: bool
    environment: str

# =============================================================================
# ENDPOINTS DE SANTÉ ET INFORMATION
# =============================================================================

@app.get("/", summary="Page d'accueil de l'API")
async def root():
    """Point d'entrée principal de l'API"""
    return {
        "message": "🤖 EasyRSVP AI Team API",
        "description": "API REST pour l'équipe d'agents IA CrewAI",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "agents": len(dev_crew.agents),
    }

@app.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check():
    """Endpoint de vérification de santé pour monitoring"""
    try:
        # Obtenir l'équipe de développement
        dev_crew = await get_dev_crew()
        
        # Vérification de l'état des agents
        agents_status = {
            agent_name: "healthy" for agent_name in dev_crew.agents.keys()
        }
        
        # Vérification des services externes avec le gestionnaire de secrets
        services = {}
        try:
            config_manager = await get_config_manager()
            config = await config_manager.get_config()
            
            services = {
                "openai": "available" if config.api.openai_key else "missing_key",
                "anthropic": "available" if config.api.anthropic_key else "missing_key",
                "perplexity": "available" if config.api.perplexity_key else "missing_key",
                "secrets_manager": "available",
                "database": "available" if config.database.password else "missing_password",
                "redis": "available" if config.redis.password else "no_password",
            }
        except Exception as e:
            logger.warning(f"Cannot check secure config: {e}")
            services = {
                "openai": "available" if os.getenv("OPENAI_API_KEY") else "missing_key",
                "database": "unknown",
                "redis": "unknown",
            }
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            agents_available=len(dev_crew.agents),
            services=services
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.get("/agents", summary="Liste des agents disponibles")
async def list_agents():
    """Retourne la liste des agents disponibles et leurs capacités"""
    return {
        "agents": {
            "product_owner": {
                "name": "Product Owner Agent",
                "description": "Analyse les user stories et génère les spécifications",
                "capabilities": ["analyze_user_story", "define_acceptance_criteria", "estimate_complexity"]
            },
            "tech_lead": {
                "name": "Tech Lead Agent", 
                "description": "Conçoit l'architecture technique",
                "capabilities": ["design_architecture", "create_component_breakdown", "define_api_structure"]
            },
            "frontend": {
                "name": "Frontend Developer Agent",
                "description": "Développe les composants React/Next.js",
                "capabilities": ["develop_components", "implement_ui", "create_tests"]
            },
            "backend": {
                "name": "Backend Developer Agent",
                "description": "Développe les APIs et la logique métier",
                "capabilities": ["develop_apis", "implement_business_logic", "create_database_schema"]
            },
            "qa": {
                "name": "QA Engineer Agent",
                "description": "Effectue les tests et validation qualité",
                "capabilities": ["run_tests", "validate_quality", "generate_reports"]
            },
            "devops": {
                "name": "DevOps Engineer Agent",
                "description": "Gère le déploiement et le monitoring",
                "capabilities": ["deploy_application", "setup_monitoring", "manage_infrastructure"]
            }
        }
    }

# =============================================================================
# ENDPOINTS PRINCIPAUX DE DÉVELOPPEMENT
# =============================================================================

@app.post("/develop-feature", response_model=DevelopmentResponse, summary="Développer une fonctionnalité complète")
async def develop_feature(request: UserStoryRequest, background_tasks: BackgroundTasks):
    """
    Endpoint principal pour développer une fonctionnalité complète
    de la user story au déploiement via l'équipe d'agents IA.
    """
    try:
        logger.info(f"Starting feature development: {request.user_story[:50]}...")
        
        # Lancement du développement avec l'équipe complète
        result = dev_crew.develop_feature(
            user_story=request.user_story,
            prd_context=request.prd_context,
            mockups=request.mockups,
            priority=request.priority,
            environment=request.environment
        )
        
        logger.info(f"Feature development completed with status: {result.get('status')}")
        
        return DevelopmentResponse(**result)
        
    except Exception as e:
        logger.error(f"Feature development failed: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to develop feature: {str(e)}"
        )

@app.post("/execute-agent-task", summary="Exécuter une tâche spécifique d'agent")
async def execute_agent_task(request: AgentTaskRequest):
    """
    Exécute une tâche spécifique sur un agent individuel.
    Utilisé par les workflows n8n pour des étapes spécialisées.
    """
    try:
        agent_type = request.agent_type
        task_type = request.task_type
        inputs = request.inputs
        
        logger.info(f"Executing {task_type} on {agent_type} agent")
        
        # Mapping des agents
        agent_map = {
            "product_owner": ProductOwnerAgent,
            "tech_lead": TechLeadAgent, 
            "frontend": FrontendAgent,
            "backend": BackendAgent,
            "qa": QAAgent,
            "devops": DevOpsAgent
        }
        
        if agent_type not in agent_map:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown agent type: {agent_type}"
            )
        
        # Exécution de la tâche selon le type d'agent
        agent_class = agent_map[agent_type]
        
        if agent_type == "product_owner" and task_type == "analyze_user_story":
            agent = agent_class.create_agent()
            task = agent_class.create_task(
                user_story=inputs.get("user_story", ""),
                prd_context=inputs.get("prd_context", ""),
                priority=inputs.get("priority", "medium")
            )
        elif agent_type == "tech_lead" and task_type == "design_architecture":
            agent = agent_class.create_agent()
            task = agent_class.create_task(
                requirements=inputs.get("requirements", ""),
                existing_architecture=inputs.get("existing_architecture", "")
            )
        elif agent_type == "frontend" and task_type == "develop_components":
            agent = agent_class.create_agent()
            task = agent_class.create_task(
                component_specs=inputs.get("component_specs", ""),
                mockups=inputs.get("mockups", "")
            )
        elif agent_type == "backend" and task_type == "develop_apis":
            agent = agent_class.create_agent()
            task = agent_class.create_task(
                api_specs=inputs.get("api_specs", ""),
                database_schema=inputs.get("database_schema", ""),
                business_logic=inputs.get("business_logic", "")
            )
        elif agent_type == "qa" and task_type == "validate_quality":
            agent = agent_class.create_agent()
            task = agent_class.create_task(
                code=inputs.get("code", ""),
                acceptance_criteria=inputs.get("acceptance_criteria", "")
            )
        elif agent_type == "devops" and task_type == "deploy":
            agent = agent_class.create_agent()
            task = agent_class.create_task(
                validated_code=inputs.get("validated_code", ""),
                environment=inputs.get("environment", "staging")
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown task type: {task_type} for agent: {agent_type}"
            )
        
        # Exécution avec CrewAI
        from crewai import Crew, Process
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential)
        result = crew.kickoff()
        
        return {
            "status": "success",
            "agent_type": agent_type,
            "task_type": task_type,
            "result": str(result),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Agent task execution failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute agent task: {str(e)}"
        )

# =============================================================================
# ENDPOINTS D'INTÉGRATION TASK MASTER
# =============================================================================

@app.post("/update-task-progress", summary="Mettre à jour le progrès d'une tâche Task Master")
async def update_task_progress(request: TaskProgressRequest):
    """
    Met à jour le statut d'une tâche dans Task Master.
    Utilisé par les workflows n8n pour synchroniser l'avancement.
    """
    try:
        logger.info(f"Updating task {request.task_id} to status {request.status}")
        
        # Mise à jour via l'intégration Task Master
        success = taskmaster.update_task_status(
            task_id=request.task_id,
            status=request.status,
            details=request.details
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Task {request.task_id} not found"
            )
        
        return {
            "status": "success",
            "task_id": request.task_id,
            "new_status": request.status,
            "updated_at": datetime.now().isoformat(),
            "details": request.details
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Task progress update failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update task progress: {str(e)}"
        )

@app.get("/daily-standup", summary="Générer le rapport quotidien de l'équipe")
async def daily_standup():
    """
    Génère le rapport quotidien de l'équipe d'agents IA.
    Utilisé par le workflow de standup quotidien.
    """
    try:
        standup_report = dev_crew.daily_standup()
        
        return {
            "status": "success",
            "report": standup_report,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Daily standup generation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate daily standup: {str(e)}"
        )

@app.get("/next-task", summary="Obtenir la prochaine tâche à développer")
async def get_next_task():
    """
    Retourne la prochaine tâche à développer selon Task Master.
    """
    try:
        next_task = taskmaster.get_next_pending_task()
        
        if not next_task:
            return {
                "status": "success",
                "next_task": None,
                "message": "Aucune tâche en attente avec dépendances satisfaites",
                "retrieved_at": datetime.now().isoformat()
            }
        
        return {
            "status": "success",
            "next_task": next_task,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Next task retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get next task: {str(e)}"
        )

# =============================================================================
# ENDPOINTS TASK MASTER ADDITIONNELS
# =============================================================================

@app.get("/tasks", summary="Obtenir toutes les tâches")
async def get_all_tasks(status: Optional[str] = None):
    """
    Retourne toutes les tâches, optionnellement filtrées par statut.
    """
    try:
        tasks = taskmaster.get_tasks_by_status(status)
        progress = taskmaster.get_project_progress()
        
        return {
            "status": "success",
            "tasks": tasks,
            "progress": progress,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Tasks retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get tasks: {str(e)}"
        )

@app.get("/tasks/{task_id}", summary="Obtenir une tâche spécifique")
async def get_task_by_id(task_id: str):
    """
    Retourne les détails d'une tâche spécifique par son ID.
    Supporte les sous-tâches avec notation point (ex: "5.3").
    """
    try:
        task = taskmaster.find_task_by_id(task_id)
        
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found"
            )
        
        return {
            "status": "success",
            "task": task,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Task retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task: {str(e)}"
        )

@app.post("/tasks/{task_id}/details", summary="Ajouter des détails à une sous-tâche")
async def append_subtask_details(task_id: str, details: Dict[str, str]):
    """
    Ajoute des détails horodatés à une sous-tâche.
    Utilisé pour logger le progrès de développement.
    """
    try:
        if '.' not in task_id:
            raise HTTPException(
                status_code=400,
                detail="Cet endpoint est réservé aux sous-tâches (format ID: parent.subtask)"
            )
        
        success = taskmaster.append_subtask_details(
            task_id=task_id,
            details=details.get("details", "")
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Subtask {task_id} not found"
            )
        
        return {
            "status": "success",
            "task_id": task_id,
            "updated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Subtask details update failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update subtask details: {str(e)}"
        )

@app.post("/development-session", summary="Créer une session de développement")
async def create_development_session(request: Dict[str, str]):
    """
    Crée une nouvelle session de développement trackée dans Task Master.
    """
    try:
        user_story = request.get("user_story", "")
        task_id = request.get("task_id")
        
        if not user_story:
            raise HTTPException(
                status_code=400,
                detail="user_story is required"
            )
        
        session_id = taskmaster.create_development_session(
            user_story=user_story,
            task_id=task_id
        )
        
        return {
            "status": "success",
            "session_id": session_id,
            "user_story": user_story,
            "task_id": task_id,
            "created_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Development session creation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create development session: {str(e)}"
        )

# =============================================================================
# ENDPOINTS DE MONITORING ET MÉTRIQUES
# =============================================================================

@app.get("/metrics", summary="Métriques de performance de l'équipe")
async def get_metrics():
    """
    Retourne les métriques de performance de l'équipe d'agents.
    """
    try:
        # Simulation des métriques - à implémenter avec de vraies données
        metrics = {
            "team_performance": {
                "features_completed_today": 3,
                "average_quality_score": 8.7,
                "deployment_success_rate": 0.95,
                "average_development_time": "4.2 hours"
            },
            "agent_performance": {
                "product_owner": {"tasks_completed": 5, "avg_score": 9.1},
                "tech_lead": {"tasks_completed": 4, "avg_score": 8.8},
                "frontend": {"tasks_completed": 6, "avg_score": 8.5},
                "backend": {"tasks_completed": 5, "avg_score": 8.9},
                "qa": {"tasks_completed": 7, "avg_score": 9.2},
                "devops": {"tasks_completed": 3, "avg_score": 8.6}
            },
            "system_health": {
                "api_response_time": "245ms",
                "error_rate": 0.02,
                "uptime": "99.8%"
            }
        }
        
        return {
            "status": "success",
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Metrics retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics: {str(e)}"
        )

# =============================================================================
# ENDPOINTS DE SÉCURITÉ
# =============================================================================

@app.get("/security/status", response_model=SecurityStatusResponse, summary="Statut de sécurité")
async def security_status():
    """
    Retourne l'état de sécurité de l'application et la configuration des secrets.
    """
    try:
        config_manager = await get_config_manager()
        health = await config_manager.get_health_status()
        
        return SecurityStatusResponse(**health)
        
    except Exception as e:
        logger.error(f"Security status check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get security status: {str(e)}"
        )

@app.post("/security/secrets", summary="Stocker un secret")
async def store_secret(request: SecretRequest, token: str = Depends(verify_auth_token)):
    """
    Stocke un secret de manière sécurisée.
    Nécessite une authentification.
    """
    try:
        secrets_manager = await get_secrets_manager()
        
        success = await secrets_manager.set_secret(
            name=request.key,
            value=request.value,
            backend=request.backend
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to store secret: {request.key}"
            )
        
        return {
            "status": "success",
            "key": request.key,
            "backend": request.backend or "primary",
            "stored_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Secret storage failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store secret: {str(e)}"
        )

@app.get("/security/secrets/{key}", response_model=SecretResponse, summary="Vérifier l'existence d'un secret")
async def check_secret(key: str, token: str = Depends(verify_auth_token)):
    """
    Vérifie l'existence d'un secret sans révéler sa valeur.
    Nécessite une authentification.
    """
    try:
        secrets_manager = await get_secrets_manager()
        
        # Récupérer le secret pour vérifier son existence
        value = await secrets_manager.get_secret(key)
        exists = value is not None
        
        # Déterminer le backend où le secret a été trouvé
        backend = None
        if exists:
            all_secrets = await secrets_manager.list_all_secrets()
            for backend_name, secrets in all_secrets.items():
                if key in secrets:
                    backend = backend_name
                    break
        
        return SecretResponse(
            key=key,
            exists=exists,
            backend=backend,
            last_updated=datetime.now().isoformat() if exists else None
        )
        
    except Exception as e:
        logger.error(f"Secret check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check secret: {str(e)}"
        )

@app.delete("/security/secrets/{key}", summary="Supprimer un secret")
async def delete_secret(key: str, backend: Optional[str] = None, token: str = Depends(verify_auth_token)):
    """
    Supprime un secret de manière sécurisée.
    Nécessite une authentification.
    """
    try:
        secrets_manager = await get_secrets_manager()
        
        success = await secrets_manager.delete_secret(key, backend=backend)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Secret not found: {key}"
            )
        
        return {
            "status": "success",
            "key": key,
            "backend": backend or "primary",
            "deleted_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Secret deletion failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete secret: {str(e)}"
        )

@app.get("/security/secrets", summary="Lister les secrets")
async def list_secrets(backend: Optional[str] = None, token: str = Depends(verify_auth_token)):
    """
    Liste tous les secrets disponibles (sans révéler leurs valeurs).
    Nécessite une authentification.
    """
    try:
        secrets_manager = await get_secrets_manager()
        
        if backend:
            # Lister les secrets d'un backend spécifique
            if backend not in secrets_manager.backends:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown backend: {backend}"
                )
            
            secrets = await secrets_manager.backends[backend].list_secrets()
            result = {backend: secrets}
        else:
            # Lister les secrets de tous les backends
            result = await secrets_manager.list_all_secrets()
        
        # Convertir les métadonnées en format JSON-friendly
        formatted_result = {}
        for backend_name, secrets in result.items():
            formatted_result[backend_name] = {
                secret_name: {
                    "name": metadata.name,
                    "created_at": metadata.created_at.isoformat(),
                    "last_accessed": metadata.last_accessed.isoformat(),
                    "expires_at": metadata.expires_at.isoformat() if metadata.expires_at else None,
                    "rotation_needed": metadata.rotation_needed,
                    "source": metadata.source
                }
                for secret_name, metadata in secrets.items()
            }
        
        return {
            "status": "success",
            "secrets": formatted_result,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Secrets listing failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list secrets: {str(e)}"
        )

@app.post("/security/secrets/{key}/rotate", summary="Effectuer la rotation d'un secret")
async def rotate_secret(key: str, new_value: str, backend: Optional[str] = None, token: str = Depends(verify_auth_token)):
    """
    Effectue la rotation d'un secret en le remplaçant par une nouvelle valeur.
    Nécessite une authentification.
    """
    try:
        secrets_manager = await get_secrets_manager()
        
        success = await secrets_manager.rotate_secret(
            name=key,
            new_value=new_value,
            backend=backend
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Secret not found or rotation failed: {key}"
            )
        
        return {
            "status": "success",
            "key": key,
            "backend": backend or "primary",
            "rotated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Secret rotation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to rotate secret: {str(e)}"
        )

@app.get("/security/audit", summary="Log d'audit des accès aux secrets")
async def get_security_audit(token: str = Depends(verify_auth_token)):
    """
    Retourne le log d'audit des accès aux secrets.
    Nécessite une authentification.
    """
    try:
        secrets_manager = await get_secrets_manager()
        audit_log = await secrets_manager.get_audit_log()
        
        return {
            "status": "success",
            "audit_log": audit_log,
            "total_entries": len(audit_log),
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Audit log retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get audit log: {str(e)}"
        )

@app.get("/security/backends", summary="Statut des backends de sécurité")
async def get_backends_status(token: str = Depends(verify_auth_token)):
    """
    Retourne l'état de santé de tous les backends de secrets.
    Nécessite une authentification.
    """
    try:
        secrets_manager = await get_secrets_manager()
        health = await secrets_manager.health_check()
        
        return {
            "status": "success",
            "backends": health,
            "primary_backend": secrets_manager.primary_backend,
            "fallback_backend": secrets_manager.fallback_backend,
            "checked_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Backends status check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check backends status: {str(e)}"
        )

# =============================================================================
# POINT D'ENTRÉE PRINCIPAL
# =============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 