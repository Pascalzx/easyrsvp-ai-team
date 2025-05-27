"""
🤖 EasyRSVP AI Team - Task Master Integration
==============================================

Module d'intégration entre les agents CrewAI et Task Master
pour synchroniser l'avancement des tâches.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class TaskMasterIntegration:
    """Classe d'intégration avec Task Master"""
    
    def __init__(self, project_root: str = None):
        """Initialise l'intégration Task Master"""
        self.project_root = project_root or os.getcwd()
        self.tasks_file = os.path.join(self.project_root, "tasks", "tasks.json")
        self.ensure_tasks_file_exists()
    
    def ensure_tasks_file_exists(self):
        """S'assure que le fichier tasks.json existe"""
        if not os.path.exists(self.tasks_file):
            # Créer le répertoire tasks si nécessaire
            os.makedirs(os.path.dirname(self.tasks_file), exist_ok=True)
            
            # Créer un fichier tasks.json vide
            empty_tasks = {
                "version": "1.0.0",
                "project": "EasyRSVP AI Team",
                "description": "Système d'équipe IA automatisé",
                "created": datetime.now().isoformat(),
                "tasks": []
            }
            
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(empty_tasks, f, indent=2, ensure_ascii=False)
    
    def load_tasks(self) -> Dict[str, Any]:
        """Charge le fichier tasks.json"""
        try:
            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erreur lors du chargement des tâches: {e}")
            return {"tasks": []}
    
    def save_tasks(self, tasks_data: Dict[str, Any]):
        """Sauvegarde le fichier tasks.json"""
        try:
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(tasks_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des tâches: {e}")
            raise
    
    def find_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Trouve une tâche par son ID (supporte les sous-tâches avec notation point)"""
        tasks_data = self.load_tasks()
        
        # Gestion des sous-tâches (ex: "5.3")
        if '.' in task_id:
            parent_id, subtask_id = task_id.split('.', 1)
            parent_id = int(parent_id)
            subtask_id = int(subtask_id)
            
            # Trouver la tâche parent
            for task in tasks_data.get("tasks", []):
                if task["id"] == parent_id:
                    # Trouver la sous-tâche
                    for subtask in task.get("subtasks", []):
                        if subtask["id"] == subtask_id:
                            subtask["parent_id"] = parent_id
                            return subtask
        else:
            # Tâche principale
            task_id = int(task_id)
            for task in tasks_data.get("tasks", []):
                if task["id"] == task_id:
                    return task
        
        return None
    
    def update_task_status(self, task_id: str, status: str, details: str = None) -> bool:
        """Met à jour le statut d'une tâche"""
        try:
            tasks_data = self.load_tasks()
            
            # Gestion des sous-tâches
            if '.' in task_id:
                parent_id, subtask_id = task_id.split('.', 1)
                parent_id = int(parent_id)
                subtask_id = int(subtask_id)
                
                for task in tasks_data.get("tasks", []):
                    if task["id"] == parent_id:
                        for subtask in task.get("subtasks", []):
                            if subtask["id"] == subtask_id:
                                subtask["status"] = status
                                if details:
                                    if "details" not in subtask:
                                        subtask["details"] = ""
                                    subtask["details"] += f"\n[{datetime.now().isoformat()}] {details}"
                                
                                self.save_tasks(tasks_data)
                                logger.info(f"Sous-tâche {task_id} mise à jour: {status}")
                                return True
            else:
                # Tâche principale
                task_id = int(task_id)
                for task in tasks_data.get("tasks", []):
                    if task["id"] == task_id:
                        task["status"] = status
                        if details:
                            if "details" not in task:
                                task["details"] = ""
                            task["details"] += f"\n[{datetime.now().isoformat()}] {details}"
                        
                        self.save_tasks(tasks_data)
                        logger.info(f"Tâche {task_id} mise à jour: {status}")
                        return True
            
            logger.warning(f"Tâche {task_id} non trouvée")
            return False
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la tâche {task_id}: {e}")
            return False
    
    def append_subtask_details(self, task_id: str, details: str) -> bool:
        """Ajoute des détails horodatés à une sous-tâche"""
        try:
            if '.' not in task_id:
                logger.error(f"ID de sous-tâche invalide: {task_id}")
                return False
            
            tasks_data = self.load_tasks()
            parent_id, subtask_id = task_id.split('.', 1)
            parent_id = int(parent_id)
            subtask_id = int(subtask_id)
            
            for task in tasks_data.get("tasks", []):
                if task["id"] == parent_id:
                    for subtask in task.get("subtasks", []):
                        if subtask["id"] == subtask_id:
                            if "details" not in subtask:
                                subtask["details"] = ""
                            
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            subtask["details"] += f"\n\n[{timestamp}] {details}"
                            
                            self.save_tasks(tasks_data)
                            logger.info(f"Détails ajoutés à la sous-tâche {task_id}")
                            return True
            
            logger.warning(f"Sous-tâche {task_id} non trouvée")
            return False
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout de détails à {task_id}: {e}")
            return False
    
    def get_next_pending_task(self) -> Optional[Dict[str, Any]]:
        """Retourne la prochaine tâche en attente selon les dépendances"""
        tasks_data = self.load_tasks()
        
        # Collecte des IDs des tâches terminées
        completed_task_ids = set()
        for task in tasks_data.get("tasks", []):
            if task.get("status") == "done":
                completed_task_ids.add(task["id"])
        
        # Trouve la première tâche en attente sans dépendances non terminées
        for task in tasks_data.get("tasks", []):
            if task.get("status") == "pending":
                dependencies = set(task.get("dependencies", []))
                if dependencies.issubset(completed_task_ids):
                    return task
        
        return None
    
    def get_tasks_by_status(self, status: str = None) -> List[Dict[str, Any]]:
        """Retourne les tâches filtrées par statut"""
        tasks_data = self.load_tasks()
        tasks = tasks_data.get("tasks", [])
        
        if status:
            tasks = [task for task in tasks if task.get("status") == status]
        
        return tasks
    
    def get_project_progress(self) -> Dict[str, Any]:
        """Calcule et retourne les statistiques de progression du projet"""
        tasks_data = self.load_tasks()
        tasks = tasks_data.get("tasks", [])
        
        if not tasks:
            return {"total": 0, "completed": 0, "in_progress": 0, "pending": 0, "progress_percentage": 0}
        
        total = len(tasks)
        completed = len([t for t in tasks if t.get("status") == "done"])
        in_progress = len([t for t in tasks if t.get("status") == "in-progress"])
        pending = len([t for t in tasks if t.get("status") == "pending"])
        
        progress_percentage = (completed / total) * 100 if total > 0 else 0
        
        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "progress_percentage": round(progress_percentage, 2)
        }
    
    def create_development_session(self, user_story: str, task_id: str = None) -> str:
        """Crée une session de développement et retourne un ID unique"""
        session_id = f"dev_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Log de la session (à étendre selon les besoins)
        logger.info(f"Nouvelle session de développement créée: {session_id}")
        logger.info(f"User story: {user_story[:100]}...")
        
        if task_id:
            self.append_subtask_details(
                task_id, 
                f"Session de développement démarrée: {session_id}\nUser story: {user_story}"
            )
        
        return session_id
    
    def log_development_phase(self, session_id: str, phase: str, result: Dict[str, Any], task_id: str = None):
        """Log le résultat d'une phase de développement"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info(f"Session {session_id} - Phase {phase} terminée")
        
        if task_id and '.' in task_id:
            details = f"Phase {phase} terminée dans la session {session_id}:\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            self.append_subtask_details(task_id, details)


# Instance globale pour l'intégration
taskmaster = TaskMasterIntegration() 