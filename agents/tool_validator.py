from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, ValidationError
import logging
from .intent_classifier import Intent, intent_classifier
from .state_manager import state_manager

class ValidationResult:
    def __init__(self, is_valid: bool, missing_fields: List[str] = None, 
                 extracted_fields: Dict[str, Any] = None, clarification: str = None):
        self.is_valid = is_valid
        self.missing_fields = missing_fields or []
        self.extracted_fields = extracted_fields or {}
        self.clarification = clarification

class ToolValidator:
    def __init__(self):
        self.clarification_templates = {
            Intent.CALENDAR_CREATE: {
                "title": "What should I call this event?",
                "date": "What date is this for? (e.g., tomorrow, today, 2024-03-08)",
                "time": "What time should this be scheduled for? (e.g., 3:00 PM, 15:00)"
            },
            Intent.EMAIL_SEND: {
                "to": "Who should I send this email to?",
                "subject": "What should the subject line be?",
                "content": "What should the email say?"
            },
            Intent.WEB_SEARCH: {
                "query": "What would you like me to search for?"
            },
            Intent.APP_LAUNCH: {
                "app_name": "Which application would you like me to open?"
            },
            Intent.TERMINAL: {
                "command": "What command should I run?"
            }
        }
    
    def validate_and_extract(self, user_input: str, intent: Intent) -> ValidationResult:
        """Validate user input and extract fields."""
        # Extract fields from user input
        extracted_fields = intent_classifier.extract_fields(user_input, intent)
        required_fields = intent_classifier.get_required_fields(intent)
        
        # Check for missing required fields
        missing_fields = []
        for field in required_fields:
            if field not in extracted_fields or not extracted_fields[field]:
                missing_fields.append(field)
        
        # Check active tasks for missing context
        active_tasks = state_manager.get_active_tasks(intent.value)
        if active_tasks and missing_fields:
            # Get missing fields from active task context
            for task_id, task in active_tasks.items():
                for field in missing_fields[:]:
                    if field in task.data and task.data[field]:
                        extracted_fields[field] = task.data[field]
                        missing_fields.remove(field)
        
        if missing_fields:
            # Generate clarification request
            clarification = self._generate_clarification(intent, missing_fields, extracted_fields)
            
            # Create or update task state
            task_id = f"{intent.value}_{len(state_manager.active_tasks)}"
            if not active_tasks:
                state_manager.create_task(task_id, intent.value, extracted_fields)
            else:
                # Update existing
                task_id = list(active_tasks.keys())[0]
                state_manager.update_task(task_id, **extracted_fields)
            
            return ValidationResult(
                is_valid=False,
                missing_fields=missing_fields,
                extracted_fields=extracted_fields,
                clarification=clarification
            )
        
        # All fields present
        return ValidationResult(
            is_valid=True,
            extracted_fields=extracted_fields
        )
    
    def _generate_clarification(self, intent: Intent, missing_fields: List[str], 
                              extracted_fields: Dict[str, Any]) -> str:
        """Generate natural clarification request."""
        templates = self.clarification_templates.get(intent, {})
        
        if len(missing_fields) == 1:
            field = missing_fields[0]
            if field in templates:
                base_message = templates[field]
            else:
                base_message = f"I need to know the {field}."
            
            # Add context for what we have
            if extracted_fields:
                context_parts = []
                for key, value in extracted_fields.items():
                    context_parts.append(f"{key}: {value}")
                
                if context_parts:
                    context = "I have: " + ", ".join(context_parts)
                    return f"{base_message} {context}"
            
            return base_message
        
        else:
            # Multiple fields missing
            field_questions = []
            for field in missing_fields:
                if field in templates:
                    field_questions.append(templates[field])
                else:
                    field_questions.append(f"What is the {field}?")
            
            return "I need a bit more information: " + " And ".join(field_questions)
    
    def complete_task_with_response(self, user_response: str) -> Optional[ValidationResult]:
        """Process user response to complete pending task."""
        # Find the most recent pending task
        active_tasks = state_manager.get_active_tasks()
        if not active_tasks:
            return None
        
        # Get most recent task
        recent_task = max(active_tasks.values(), key=lambda t: t.created_at)
        task_id = None
        for tid, task in active_tasks.items():
            if task == recent_task:
                task_id = tid
                break
        
        if not task_id:
            return None
        
        # Extract missing fields from response
        intent = Intent(recent_task.task_type)
        new_fields = intent_classifier.extract_fields(user_response, intent)
        
        # Update task with new info
        combined_fields = {**recent_task.data, **new_fields}
        state_manager.update_task(task_id, **new_fields)
        
        # Re-validate with combined fields
        required_fields = intent_classifier.get_required_fields(intent)
        missing_fields = [f for f in required_fields if f not in combined_fields or not combined_fields[f]]
        
        if missing_fields:
            # Still missing fields
            clarification = self._generate_clarification(intent, missing_fields, combined_fields)
            return ValidationResult(
                is_valid=False,
                missing_fields=missing_fields,
                extracted_fields=combined_fields,
                clarification=clarification
            )
        else:
            # Task complete
            state_manager.complete_task(task_id)
            return ValidationResult(
                is_valid=True,
                extracted_fields=combined_fields
            )

# Global instance
tool_validator = ToolValidator()