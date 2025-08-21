from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging

@dataclass
class TaskState:
    task_type: str
    status: str = "pending"  # pending, in_progress, completed, failed
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def update(self, **kwargs):
        """Update task data and timestamp."""
        self.data.update(kwargs)
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_type": self.task_type,
            "status": self.status,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

class StateManager:
    def __init__(self):
        self.active_tasks: Dict[str, TaskState] = {}
        self.session_context: Dict[str, Any] = {}
    
    def create_task(self, task_id: str, task_type: str, initial_data: Dict[str, Any] = None) -> TaskState:
        """Create new task."""
        task = TaskState(
            task_type=task_type,
            data=initial_data or {}
        )
        self.active_tasks[task_id] = task
        logging.info(f"Created task {task_id} of type {task_type}")
        return task
    
    def get_task(self, task_id: str) -> Optional[TaskState]:
        """Get task by ID."""
        return self.active_tasks.get(task_id)
    
    def update_task(self, task_id: str, status: str = None, **data) -> bool:
        """Update task status and data."""
        if task_id not in self.active_tasks:
            return False
        
        task = self.active_tasks[task_id]
        if status:
            task.status = status
        task.update(**data)
        
        logging.info(f"Updated task {task_id}: status={status}, data={data}")
        return True
    
    def complete_task(self, task_id: str, result: Any = None) -> bool:
        """Mark task as completed."""
        if task_id not in self.active_tasks:
            return False
        
        task = self.active_tasks[task_id]
        task.status = "completed"
        if result is not None:
            task.update(result=result)
        
        logging.info(f"Completed task {task_id}")
        return True
    
    def get_active_tasks(self, task_type: str = None) -> Dict[str, TaskState]:
        """Get active tasks, optionally by type."""
        if task_type:
            return {k: v for k, v in self.active_tasks.items() 
                   if v.task_type == task_type and v.status in ["pending", "in_progress"]}
        return {k: v for k, v in self.active_tasks.items() 
               if v.status in ["pending", "in_progress"]}
    
    def set_context(self, key: str, value: Any):
        """Set session context."""
        self.session_context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get session context."""
        return self.session_context.get(key, default)
    
    def clear_completed_tasks(self):
        """Remove completed/failed tasks."""
        to_remove = [k for k, v in self.active_tasks.items() 
                    if v.status in ["completed", "failed"]]
        for task_id in to_remove:
            del self.active_tasks[task_id]
        logging.info(f"Cleared {len(to_remove)} completed/failed tasks")
    
    def get_state_summary(self) -> str:
        """Get current state summary."""
        active = self.get_active_tasks()
        if not active:
            return "No active tasks."
        
        summary_parts = ["Active tasks:"]
        for task_id, task in active.items():
            summary_parts.append(f"- {task.task_type} ({task.status}): {task.data}")
        
        return "\n".join(summary_parts)

# Global instance
state_manager = StateManager()