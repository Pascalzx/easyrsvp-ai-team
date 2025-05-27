"""
🎯 Project Coordinator - Chef d'Orchestre EasyRSVP AI Team
===========================================================

Coordinateur de projet IA responsable de :
- Analyser les demandes utilisateur
- Décomposer en tâches spécifiques et détaillées
- Assigner les tâches aux agents appropriés
- Suivre l'avancement et coordonner le travail
- Valider la qualité finale

Version: 2.0.0
Date: 2024
"""

import os
import json
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# Imports CrewAI
from crewai import Agent, Task, Crew, Process
from langchain.llms import OpenAI

# Imports locaux
try:
    from .secrets_manager import get_secrets_manager
except ImportError:
    # Fallback pour développement
    async def get_secrets_manager():
        return None

# =============================================================================
# MODÈLES DE DONNÉES
# =============================================================================

class TaskStatus(Enum):
    """Statuts possibles pour les tâches"""
    CREATED = "created"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    """Niveaux de priorité"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AgentType(Enum):
    """Types d'agents disponibles"""
    PRODUCT_OWNER = "product_owner"
    TECH_LEAD = "tech_lead"
    FRONTEND_DEVELOPER = "frontend_developer"
    BACKEND_DEVELOPER = "backend_developer"
    QA_ENGINEER = "qa_engineer"
    DEVOPS_ENGINEER = "devops_engineer"

@dataclass
class TaskAssignment:
    """Représente une tâche assignée par le coordinateur"""
    task_id: str
    title: str
    description: str
    assigned_to: AgentType
    priority: TaskPriority
    estimated_hours: float
    dependencies: List[str]
    acceptance_criteria: List[str]
    technical_details: Dict[str, Any]
    deadline: datetime
    status: TaskStatus = TaskStatus.CREATED
    created_at: datetime = None
    updated_at: datetime = None
    completion_notes: str = ""
    quality_score: float = 0.0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour sérialisation"""
        data = asdict(self)
        # Convertir les enums en strings
        data["assigned_to"] = self.assigned_to.value
        data["priority"] = self.priority.value
        data["status"] = self.status.value
        # Convertir les dates en ISO format
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        data["deadline"] = self.deadline.isoformat()
        return data

@dataclass
class ProjectPlan:
    """Plan de projet généré par le coordinateur"""
    project_id: str
    user_story: str
    analysis: Dict[str, Any]
    task_assignments: List[TaskAssignment]
    estimated_total_hours: float
    estimated_completion: datetime
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

# =============================================================================
# COORDINATEUR DE PROJET PRINCIPAL
# =============================================================================

class ProjectCoordinator:
    """
    Coordinateur de projet IA - Chef d'orchestre de l'équipe EasyRSVP
    
    Responsabilités:
    1. Analyser les demandes utilisateur
    2. Décomposer en tâches spécifiques par agent
    3. Gérer les assignations et dépendances
    4. Suivre l'avancement du projet
    5. Coordonner la livraison finale
    """
    
    def __init__(self):
        self.active_projects: Dict[str, ProjectPlan] = {}
        self.active_tasks: Dict[str, TaskAssignment] = {}
        self.agents_workload: Dict[AgentType, List[str]] = {
            agent: [] for agent in AgentType
        }
        
        # Configuration de l'agent IA coordinateur
        self.agent = Agent(
            role="Chef de Projet IA Senior",
            goal="Orchestrer efficacement l'équipe de développement EasyRSVP pour livrer des fonctionnalités de qualité optimale dans les délais impartis",
            backstory="""
            🎯 PROFIL EXPERT
            Je suis un Chef de Projet IA avec 12 ans d'expérience en gestion de projets SaaS complexes.
            
            💼 EXPERTISE:
            - Gestion d'équipes techniques multidisciplinaires  
            - Décomposition de fonctionnalités en tâches atomiques
            - Optimisation des workflows de développement
            - Coordination agile et livraison continue
            - Analyse de risques et mitigation proactive
            
            🏆 SPÉCIALISATIONS:
            - Développement SaaS événementiel (EasyRSVP)
            - Stack technique moderne (Next.js, TypeScript, Tailwind)
            - Méthodologies agiles (Scrum, Kanban)
            - Qualité et performance (WCAG, Core Web Vitals)
            - Architecture microservices et déploiement cloud
            
            🎪 CONTEXTE EASYRSV:
            Plateforme SaaS complète de gestion d'événements avec système RSVP avancé,
            targeting: organisateurs d'événements professionnels et particuliers.
            
            🚀 MISSION:
            Transformer chaque demande utilisateur en plan de développement structuré,
            avec tâches spécifiques, estimations précises et coordination optimale.
            """,
            verbose=True,
            allow_delegation=True,
            tools=[],
            llm=OpenAI(temperature=0.1, model="gpt-4")
        )
        
        # Templates de tâches par type d'agent
        self.task_templates = {
            AgentType.PRODUCT_OWNER: {
                "acceptance_criteria_base": [
                    "User stories détaillées avec personas",
                    "Critères d'acceptation en format Given/When/Then",
                    "Wireframes et mockups validés",
                    "Règles métier documentées",
                    "Cas d'usage et scénarios d'erreur"
                ],
                "estimated_hours_base": 6
            },
            AgentType.TECH_LEAD: {
                "acceptance_criteria_base": [
                    "Architecture technique documentée",
                    "Schémas de base de données optimisés",
                    "APIs REST/GraphQL spécifiées",
                    "Stratégie de tests définie",
                    "Plan de migration et rollback"
                ],
                "estimated_hours_base": 8
            },
            AgentType.FRONTEND_DEVELOPER: {
                "acceptance_criteria_base": [
                    "Composants React réutilisables",
                    "Responsive design mobile-first",
                    "Accessibilité WCAG 2.1 AA",
                    "Performance Lighthouse > 90",
                    "Tests unitaires 90%+ couverture"
                ],
                "estimated_hours_base": 12
            },
            AgentType.BACKEND_DEVELOPER: {
                "acceptance_criteria_base": [
                    "APIs documentées OpenAPI/Swagger",
                    "Validation des données avec Zod",
                    "Tests d'intégration complets",
                    "Gestion d'erreurs robuste",
                    "Monitoring et logging intégrés"
                ],
                "estimated_hours_base": 14
            },
            AgentType.QA_ENGINEER: {
                "acceptance_criteria_base": [
                    "Tests automatisés E2E avec Playwright",
                    "Tests de performance et charge",
                    "Tests d'accessibilité automatisés",
                    "Tests de sécurité OWASP",
                    "Rapport de qualité complet"
                ],
                "estimated_hours_base": 10
            },
            AgentType.DEVOPS_ENGINEER: {
                "acceptance_criteria_base": [
                    "Pipeline CI/CD configuré",
                    "Déploiement zero-downtime",
                    "Monitoring et alertes actifs",
                    "Backup et disaster recovery",
                    "Documentation d'exploitation"
                ],
                "estimated_hours_base": 8
            }
        }
    
    # =========================================================================
    # ANALYSE ET PLANIFICATION
    # =========================================================================
    
    async def analyze_user_request(self, user_story: str, context: Dict[str, Any] = None) -> ProjectPlan:
        """
        Analyse une demande utilisateur et crée un plan de projet complet
        """
        print(f"🎯 Début de l'analyse : {user_story[:100]}...")
        
        project_id = f"PROJ-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"
        
        # Création de la tâche d'analyse
        analysis_task = Task(
            description=f"""
            🎯 ANALYSE APPROFONDIE DE DEMANDE UTILISATEUR
            =============================================
            
            DEMANDE: {user_story}
            
            CONTEXTE: {json.dumps(context or {}, indent=2)}
            
            🔍 ANALYSE REQUISE:
            
            1. **COMPRÉHENSION MÉTIER**
               - Objectif principal et valeur ajoutée
               - Personas utilisateurs ciblés
               - Parcours utilisateur complet
               - Impact sur l'écosystème EasyRSVP
               - Métriques de succès attendues
            
            2. **DÉCOMPOSITION TECHNIQUE**
               - Composants frontend nécessaires
               - APIs backend et logique métier
               - Modifications/extensions de BDD
               - Intégrations tierces requises
               - Considérations de sécurité et performance
            
            3. **PLANIFICATION DÉTAILLÉE**
               Pour CHAQUE agent, définir:
               - Tâches spécifiques et atomiques
               - Estimations réalistes (heures)
               - Dépendances inter-tâches
               - Critères d'acceptation précis
               - Livrables attendus
               - Risques et points d'attention
            
            4. **STRATÉGIE QUALITÉ**
               - Tests requis par niveau
               - Points de validation critiques
               - Stratégie de déploiement
               - Plan de rollback
            
            5. **TIMELINE ET PRIORISATION**
               - Séquencement optimal des tâches
               - Jalons importants
               - Estimation globale
               - Stratégie de livraison (MVP vs complet)
            
            📋 FORMAT JSON ATTENDU:
            Structurer la réponse avec une planification complète pour les 6 agents.
            """,
            agent=self.agent,
            expected_output="""
            JSON détaillé avec structure:
            {
                "project_analysis": {
                    "business_understanding": {
                        "main_objective": "string",
                        "target_personas": ["array"],
                        "user_journey": "string",
                        "business_value": "string",
                        "success_metrics": ["array"]
                    },
                    "technical_breakdown": {
                        "frontend_components": ["array"],
                        "backend_apis": ["array"],
                        "database_changes": ["array"],
                        "integrations": ["array"],
                        "security_considerations": ["array"]
                    },
                    "quality_strategy": {
                        "testing_levels": ["array"],
                        "validation_points": ["array"],
                        "deployment_strategy": "string",
                        "rollback_plan": "string"
                    }
                },
                "task_assignments": {
                    "product_owner": [
                        {
                            "title": "string",
                            "description": "string",
                            "estimated_hours": number,
                            "priority": "string",
                            "dependencies": ["array"],
                            "acceptance_criteria": ["array"],
                            "deliverables": ["array"],
                            "risks": ["array"]
                        }
                    ],
                    "tech_lead": [...],
                    "frontend_developer": [...],
                    "backend_developer": [...],
                    "qa_engineer": [...],
                    "devops_engineer": [...]
                },
                "timeline": {
                    "total_estimated_hours": number,
                    "estimated_days": number,
                    "critical_path": ["array"],
                    "milestones": [
                        {
                            "name": "string",
                            "date": "string",
                            "deliverables": ["array"]
                        }
                    ]
                }
            }
            """
        )
        
        # Exécution de l'analyse
        crew = Crew(
            agents=[self.agent],
            tasks=[analysis_task],
            verbose=True,
            process=Process.sequential
        )
        
        print("🔄 Exécution de l'analyse par l'IA...")
        result = crew.kickoff()
        
        # Parse du résultat
        analysis_data = self._parse_analysis_result(result)
        
        # Création des tâches détaillées
        task_assignments = await self._create_detailed_tasks(analysis_data, project_id)
        
        # Calcul des estimations globales
        total_hours = sum(task.estimated_hours for task in task_assignments)
        estimated_completion = datetime.now() + timedelta(hours=total_hours * 1.2)  # Buffer 20%
        
        # Création du plan de projet
        project_plan = ProjectPlan(
            project_id=project_id,
            user_story=user_story,
            analysis=analysis_data,
            task_assignments=task_assignments,
            estimated_total_hours=total_hours,
            estimated_completion=estimated_completion
        )
        
        # Stockage du projet
        self.active_projects[project_id] = project_plan
        
        # Assignation des tâches aux agents
        for task in task_assignments:
            self.active_tasks[task.task_id] = task
            self.agents_workload[task.assigned_to].append(task.task_id)
        
        print(f"✅ Projet {project_id} créé avec {len(task_assignments)} tâches")
        
        return project_plan
    
    def _parse_analysis_result(self, result: Any) -> Dict[str, Any]:
        """Parse le résultat de l'analyse IA"""
        try:
            if isinstance(result, str):
                # Chercher du JSON dans la réponse
                import re
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            elif hasattr(result, 'content'):
                return json.loads(result.content)
            else:
                return {"raw_analysis": str(result)}
        except json.JSONDecodeError:
            return {"raw_analysis": str(result), "parse_error": True}
    
    async def _create_detailed_tasks(self, analysis_data: Dict[str, Any], project_id: str) -> List[TaskAssignment]:
        """Crée les tâches détaillées à partir de l'analyse"""
        tasks = []
        task_counter = 1
        
        task_assignments = analysis_data.get("task_assignments", {})
        
        for agent_type_str, agent_tasks in task_assignments.items():
            try:
                # Conversion string -> enum
                if agent_type_str in ["product_owner", "tech_lead", "frontend_developer", 
                                    "backend_developer", "qa_engineer", "devops_engineer"]:
                    agent_type = AgentType(agent_type_str)
                else:
                    continue
                
                for task_data in agent_tasks:
                    task_id = f"{project_id}-T{task_counter:03d}"
                    
                    # Parsing de la priorité
                    priority_str = task_data.get("priority", "medium").lower()
                    try:
                        priority = TaskPriority(priority_str)
                    except ValueError:
                        priority = TaskPriority.MEDIUM
                    
                    # Calcul de la deadline
                    estimated_hours = task_data.get("estimated_hours", 
                                                   self.task_templates[agent_type]["estimated_hours_base"])
                    deadline = datetime.now() + timedelta(hours=estimated_hours * 1.5)
                    
                    # Création de la tâche
                    task = TaskAssignment(
                        task_id=task_id,
                        title=task_data.get("title", f"Tâche {agent_type.value}"),
                        description=task_data.get("description", ""),
                        assigned_to=agent_type,
                        priority=priority,
                        estimated_hours=estimated_hours,
                        dependencies=task_data.get("dependencies", []),
                        acceptance_criteria=task_data.get("acceptance_criteria", 
                                                        self.task_templates[agent_type]["acceptance_criteria_base"]),
                        technical_details={
                            "deliverables": task_data.get("deliverables", []),
                            "risks": task_data.get("risks", []),
                            "tools_required": task_data.get("tools_required", []),
                            "references": task_data.get("references", [])
                        },
                        deadline=deadline
                    )
                    
                    tasks.append(task)
                    task_counter += 1
                    
            except Exception as e:
                print(f"⚠️  Erreur création tâche pour {agent_type_str}: {e}")
                continue
        
        # Si aucune tâche créée, générer des tâches par défaut
        if not tasks:
            tasks = self._create_default_tasks(project_id, analysis_data.get("project_analysis", {}))
        
        return tasks
    
    def _create_default_tasks(self, project_id: str, analysis: Dict[str, Any]) -> List[TaskAssignment]:
        """Crée des tâches par défaut si l'analyse n'en contient pas"""
        default_tasks = []
        task_counter = 1
        
        # Tâche Product Owner par défaut
        po_task = TaskAssignment(
            task_id=f"{project_id}-T{task_counter:03d}",
            title="Analyse et spécification fonctionnelle",
            description="Analyser la demande utilisateur et créer les spécifications détaillées",
            assigned_to=AgentType.PRODUCT_OWNER,
            priority=TaskPriority.HIGH,
            estimated_hours=6,
            dependencies=[],
            acceptance_criteria=self.task_templates[AgentType.PRODUCT_OWNER]["acceptance_criteria_base"],
            technical_details={"context": analysis},
            deadline=datetime.now() + timedelta(hours=9)
        )
        default_tasks.append(po_task)
        task_counter += 1
        
        # Tâche Tech Lead par défaut
        tl_task = TaskAssignment(
            task_id=f"{project_id}-T{task_counter:03d}",
            title="Architecture technique et planification",
            description="Concevoir l'architecture et créer le plan technique de développement",
            assigned_to=AgentType.TECH_LEAD,
            priority=TaskPriority.HIGH,
            estimated_hours=8,
            dependencies=[po_task.task_id],
            acceptance_criteria=self.task_templates[AgentType.TECH_LEAD]["acceptance_criteria_base"],
            technical_details={"depends_on_po": True},
            deadline=datetime.now() + timedelta(hours=17)
        )
        default_tasks.append(tl_task)
        
        return default_tasks
    
    # =========================================================================
    # GESTION DES TÂCHES
    # =========================================================================
    
    async def assign_task_to_agent(self, task_id: str, agent_type: AgentType) -> bool:
        """Réassigne une tâche à un autre agent"""
        if task_id not in self.active_tasks:
            return False
        
        task = self.active_tasks[task_id]
        old_agent = task.assigned_to
        
        # Retirer de l'ancien agent
        if task_id in self.agents_workload[old_agent]:
            self.agents_workload[old_agent].remove(task_id)
        
        # Assigner au nouvel agent
        task.assigned_to = agent_type
        task.updated_at = datetime.now()
        self.agents_workload[agent_type].append(task_id)
        
        print(f"📋 Tâche {task_id} réassignée : {old_agent.value} → {agent_type.value}")
        return True
    
    async def update_task_status(self, task_id: str, status: TaskStatus, notes: str = "") -> bool:
        """Met à jour le statut d'une tâche"""
        if task_id not in self.active_tasks:
            return False
        
        task = self.active_tasks[task_id]
        old_status = task.status
        task.status = status
        task.updated_at = datetime.now()
        
        if notes:
            task.completion_notes = notes
        
        print(f"📈 Tâche {task_id} : {old_status.value} → {status.value}")
        if notes:
            print(f"   📝 Notes : {notes}")
        
        return True
    
    async def add_task_dependency(self, task_id: str, dependency_id: str) -> bool:
        """Ajoute une dépendance à une tâche"""
        if task_id not in self.active_tasks or dependency_id not in self.active_tasks:
            return False
        
        task = self.active_tasks[task_id]
        if dependency_id not in task.dependencies:
            task.dependencies.append(dependency_id)
            task.updated_at = datetime.now()
            print(f"🔗 Dépendance ajoutée : {task_id} dépend de {dependency_id}")
            return True
        
        return False
    
    async def get_agent_current_task(self, agent_type: AgentType) -> Optional[TaskAssignment]:
        """Récupère la tâche actuelle d'un agent"""
        agent_tasks = self.agents_workload[agent_type]
        
        # Chercher une tâche en cours
        for task_id in agent_tasks:
            task = self.active_tasks[task_id]
            if task.status == TaskStatus.IN_PROGRESS:
                return task
        
        # Sinon, chercher la prochaine tâche assignée avec dépendances satisfaites
        for task_id in agent_tasks:
            task = self.active_tasks[task_id]
            if task.status == TaskStatus.ASSIGNED:
                # Vérifier les dépendances
                dependencies_ready = True
                for dep_id in task.dependencies:
                    if dep_id in self.active_tasks:
                        if self.active_tasks[dep_id].status != TaskStatus.COMPLETED:
                            dependencies_ready = False
                            break
                
                if dependencies_ready:
                    return task
        
        return None
    
    async def get_agent_workload(self, agent_type: AgentType) -> Dict[str, Any]:
        """Récupère la charge de travail d'un agent"""
        task_ids = self.agents_workload[agent_type]
        agent_tasks = [self.active_tasks[tid] for tid in task_ids if tid in self.active_tasks]
        
        status_counts = {}
        total_hours = 0
        completed_hours = 0
        
        for task in agent_tasks:
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            total_hours += task.estimated_hours
            
            if task.status == TaskStatus.COMPLETED:
                completed_hours += task.estimated_hours
        
        return {
            "agent": agent_type.value,
            "total_tasks": len(agent_tasks),
            "total_hours": total_hours,
            "completed_hours": completed_hours,
            "progress_percentage": (completed_hours / total_hours * 100) if total_hours > 0 else 0,
            "status_breakdown": status_counts,
            "current_task": (await self.get_agent_current_task(agent_type)).task_id if await self.get_agent_current_task(agent_type) else None
        }
    
    # =========================================================================
    # RAPPORTS ET MONITORING
    # =========================================================================
    
    async def generate_project_status_report(self, project_id: str) -> Dict[str, Any]:
        """Génère un rapport de statut complet du projet"""
        if project_id not in self.active_projects:
            return {"error": f"Projet {project_id} non trouvé"}
        
        project = self.active_projects[project_id]
        
        # Collecte des statistiques
        total_tasks = len(project.task_assignments)
        completed_tasks = len([t for t in project.task_assignments if t.status == TaskStatus.COMPLETED])
        in_progress_tasks = len([t for t in project.task_assignments if t.status == TaskStatus.IN_PROGRESS])
        blocked_tasks = len([t for t in project.task_assignments if t.status == TaskStatus.BLOCKED])
        
        # Calcul du progrès
        progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Charge de travail par agent
        agents_status = {}
        for agent_type in AgentType:
            agents_status[agent_type.value] = await self.get_agent_workload(agent_type)
        
        # Prochaines échéances
        upcoming_deadlines = []
        now = datetime.now()
        for task in project.task_assignments:
            if task.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
                hours_remaining = (task.deadline - now).total_seconds() / 3600
                if hours_remaining <= 72:  # Prochaines 72h
                    upcoming_deadlines.append({
                        "task_id": task.task_id,
                        "title": task.title,
                        "assigned_to": task.assigned_to.value,
                        "deadline": task.deadline.isoformat(),
                        "hours_remaining": round(hours_remaining, 1),
                        "status": task.status.value
                    })
        
        upcoming_deadlines.sort(key=lambda x: x["hours_remaining"])
        
        return {
            "project_id": project_id,
            "user_story": project.user_story,
            "created_at": project.created_at.isoformat(),
            "estimated_completion": project.estimated_completion.isoformat(),
            "status": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "in_progress_tasks": in_progress_tasks,
                "blocked_tasks": blocked_tasks,
                "progress_percentage": round(progress_percentage, 1)
            },
            "estimated_hours": {
                "total": project.estimated_total_hours,
                "completed": sum(t.estimated_hours for t in project.task_assignments if t.status == TaskStatus.COMPLETED),
                "remaining": sum(t.estimated_hours for t in project.task_assignments if t.status != TaskStatus.COMPLETED)
            },
            "agents_status": agents_status,
            "upcoming_deadlines": upcoming_deadlines[:5],  # Top 5
            "quality_metrics": await self._calculate_quality_metrics(project_id)
        }
    
    async def _calculate_quality_metrics(self, project_id: str) -> Dict[str, Any]:
        """Calcule les métriques de qualité du projet"""
        if project_id not in self.active_projects:
            return {}
        
        project = self.active_projects[project_id]
        completed_tasks = [t for t in project.task_assignments if t.status == TaskStatus.COMPLETED]
        
        if not completed_tasks:
            return {"status": "no_completed_tasks"}
        
        # Score de qualité moyen
        quality_scores = [t.quality_score for t in completed_tasks if t.quality_score > 0]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # Respect des délais
        on_time_tasks = 0
        for task in completed_tasks:
            if task.updated_at <= task.deadline:
                on_time_tasks += 1
        
        on_time_percentage = (on_time_tasks / len(completed_tasks) * 100) if completed_tasks else 0
        
        return {
            "average_quality_score": round(avg_quality, 2),
            "tasks_with_quality_score": len(quality_scores),
            "on_time_percentage": round(on_time_percentage, 1),
            "on_time_tasks": on_time_tasks,
            "total_completed": len(completed_tasks)
        }
    
    async def daily_standup_report(self) -> Dict[str, Any]:
        """Génère le rapport quotidien de standup"""
        report = {
            "date": datetime.now().isoformat(),
            "summary": {
                "active_projects": len(self.active_projects),
                "total_active_tasks": len(self.active_tasks),
                "completed_today": 0,
                "blocked_tasks": 0
            },
            "agents_status": {},
            "urgent_items": [],
            "achievements": []
        }
        
        # Collecte des données par agent
        today = datetime.now().date()
        
        for agent_type in AgentType:
            agent_tasks = [
                self.active_tasks[tid] 
                for tid in self.agents_workload[agent_type] 
                if tid in self.active_tasks
            ]
            
            # Tâches terminées aujourd'hui
            completed_today = [
                t for t in agent_tasks 
                if t.status == TaskStatus.COMPLETED and t.updated_at.date() == today
            ]
            
            # Tâche actuelle
            current_task = await self.get_agent_current_task(agent_type)
            
            report["agents_status"][agent_type.value] = {
                "current_task": current_task.title if current_task else "Aucune tâche active",
                "completed_today": len(completed_today),
                "total_assigned": len(agent_tasks),
                "status": "active" if current_task else "available"
            }
            
            report["summary"]["completed_today"] += len(completed_today)
            
            # Ajout des réalisations
            for task in completed_today:
                report["achievements"].append({
                    "agent": agent_type.value,
                    "task": task.title,
                    "quality_score": task.quality_score
                })
        
        # Identification des éléments urgents
        for task in self.active_tasks.values():
            if task.status == TaskStatus.BLOCKED:
                report["summary"]["blocked_tasks"] += 1
                report["urgent_items"].append({
                    "type": "blocked_task",
                    "task_id": task.task_id,
                    "title": task.title,
                    "assigned_to": task.assigned_to.value,
                    "notes": task.completion_notes
                })
            
            # Tâches en retard
            if task.deadline < datetime.now() and task.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
                hours_overdue = (datetime.now() - task.deadline).total_seconds() / 3600
                report["urgent_items"].append({
                    "type": "overdue_task",
                    "task_id": task.task_id,
                    "title": task.title,
                    "assigned_to": task.assigned_to.value,
                    "hours_overdue": round(hours_overdue, 1)
                })
        
        return report
    
    # =========================================================================
    # UTILITAIRES
    # =========================================================================
    
    def export_project_data(self, project_id: str) -> Dict[str, Any]:
        """Exporte toutes les données d'un projet"""
        if project_id not in self.active_projects:
            return {"error": f"Projet {project_id} non trouvé"}
        
        project = self.active_projects[project_id]
        
        return {
            "project": {
                "project_id": project.project_id,
                "user_story": project.user_story,
                "analysis": project.analysis,
                "estimated_total_hours": project.estimated_total_hours,
                "estimated_completion": project.estimated_completion.isoformat(),
                "created_at": project.created_at.isoformat()
            },
            "tasks": [task.to_dict() for task in project.task_assignments]
        }
    
    def save_to_file(self, project_id: str, filename: str = None) -> str:
        """Sauvegarde un projet dans un fichier JSON"""
        if filename is None:
            filename = f"project_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        data = self.export_project_data(project_id)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return filename

# =============================================================================
# EXEMPLE D'USAGE
# =============================================================================

async def main():
    """Exemple d'usage du coordinateur de projet"""
    
    # Initialisation du coordinateur
    coordinator = ProjectCoordinator()
    
    # Analyse d'une demande utilisateur
    user_story = """
    En tant qu'organisateur d'événement, je veux pouvoir créer un système de 
    billetterie avancé avec différents types de billets (gratuit, payant, VIP) 
    et des codes promo pour pouvoir gérer les ventes et la monétisation de mon événement.
    """
    
    context = {
        "event_type": "conference",
        "expected_attendees": 500,
        "budget": "medium",
        "timeline": "6_weeks"
    }
    
    print("🚀 Démarrage de l'analyse...")
    
    # Création du plan de projet
    project_plan = await coordinator.analyze_user_request(user_story, context)
    
    print(f"\n📊 Plan de projet créé : {project_plan.project_id}")
    print(f"📋 Nombre de tâches : {len(project_plan.task_assignments)}")
    print(f"⏱️  Estimation totale : {project_plan.estimated_total_hours}h")
    
    # Affichage des tâches par agent
    for agent_type in AgentType:
        agent_tasks = [t for t in project_plan.task_assignments if t.assigned_to == agent_type]
        if agent_tasks:
            print(f"\n👤 {agent_type.value.upper()} ({len(agent_tasks)} tâches)")
            for task in agent_tasks:
                print(f"  📌 {task.title} ({task.estimated_hours}h - {task.priority.value})")
    
    # Génération du rapport de statut
    status_report = await coordinator.generate_project_status_report(project_plan.project_id)
    print(f"\n📈 Progrès initial : {status_report['status']['progress_percentage']}%")
    
    # Simulation d'avancement des tâches
    print("\n🔄 Simulation d'avancement...")
    
    # Démarrage de quelques tâches
    for task in project_plan.task_assignments[:3]:
        await coordinator.update_task_status(task.task_id, TaskStatus.IN_PROGRESS)
    
    # Rapport de standup
    standup = await coordinator.daily_standup_report()
    print(f"\n📋 Standup : {standup['summary']['total_active_tasks']} tâches actives")
    
    # Sauvegarde du projet
    filename = coordinator.save_to_file(project_plan.project_id)
    print(f"\n💾 Projet sauvegardé : {filename}")

if __name__ == "__main__":
    asyncio.run(main()) 