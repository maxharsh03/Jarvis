from typing import Dict, List, Tuple
import re
from enum import Enum

class Intent(Enum):
    CALENDAR_CREATE = "calendar_create"
    CALENDAR_CHECK = "calendar_check" 
    CALENDAR_SEARCH = "calendar_search"
    EMAIL_SEND = "email_send"
    EMAIL_READ = "email_read"
    WEATHER = "weather"
    APP_LAUNCH = "app_launch"
    TERMINAL = "terminal"
    WEB_SEARCH = "web_search"
    MEMORY_LOOKUP = "memory_lookup"
    GENERAL = "general"

class IntentClassifier:
    def __init__(self):
        self.patterns = {
            Intent.CALENDAR_CREATE: [
                r'\b(schedule|create|add|plan|set up)\b.*\b(meeting|event|appointment|reminder)\b',
                r'\b(tomorrow|today|next week|next month)\b.*\b(at|@)\b.*\d+',
                r'\bremind me\b.*\b(about|to)\b',
                r'\b(gym|workout|dinner|lunch|meeting)\b.*\b(at|@)\b.*\d+',
                r'\bgoing to\b.*\b(gym|meeting|appointment)',
                r'\b(calendar|schedule)\b.*\b(for|at)\b'
            ],
            Intent.CALENDAR_CHECK: [
                r'\b(check|show|what\'s|whats)\b.*\b(calendar|schedule|events|meetings)\b',
                r'\b(what do i have|what\'s on my)\b.*\b(calendar|schedule)\b',
                r'\b(upcoming|next)\b.*\b(events|meetings|appointments)\b',
                r'\b(free|available|busy)\b.*\b(today|tomorrow|next week)\b'
            ],
            Intent.CALENDAR_SEARCH: [
                r'\b(find|search|look for)\b.*\b(event|meeting|appointment)\b',
                r'\b(when was|when is)\b.*\b(meeting|event|appointment)\b'
            ],
            Intent.EMAIL_SEND: [
                r'\b(send|write|compose)\b.*\b(email|message|mail)\b',
                r'\b(email|mail)\b.*\b(to|about)\b',
                r'\btell\b.*\b(via email|by email)\b'
            ],
            Intent.EMAIL_READ: [
                r'\b(check|read|show)\b.*\b(email|emails|mail|inbox)\b',
                r'\b(any new|latest)\b.*\b(email|mail|messages)\b'
            ],
            Intent.WEATHER: [
                r'\b(weather|temperature|forecast)\b',
                r'\b(how\'s|what\'s|whats)\b.*\b(weather|temperature)\b',
                r'\b(rain|sunny|cloudy|hot|cold)\b.*\b(today|tomorrow|outside)\b'
            ],
            Intent.APP_LAUNCH: [
                r'\b(open|launch|start|run)\b.*\b(app|application|program)\b',
                r'\b(open|launch|start)\b\s+\w+\.(app|exe|com)\b',
                r'\bopen\b\s+(chrome|firefox|safari|spotify|slack|discord|teams)\b'
            ],
            Intent.TERMINAL: [
                r'\b(run|execute|terminal|command)\b',
                r'\b(bash|shell|cmd)\b',
                r'\bgit\b.*\b(status|commit|push|pull)\b',
                r'\b(ls|cd|mkdir|rm|cp|mv)\b',
                r'\b(npm|pip|docker)\b',
                r'\brun\s+\w+',  # "run ellis", "run something"
                r'\bls\b.*\bon\b',  # "ls on desk"
                r'\bellis\b'  # "ellis" (common misinterpretation of "ls")
            ],
            Intent.WEB_SEARCH: [
                r'\b(search|google|look up|find)\b.*\b(for|about|on)\b',
                r'\b(what is|who is|how to)\b',
                r'\b(browse|web|internet)\b.*\b(search|for)\b'
            ],
            Intent.MEMORY_LOOKUP: [
                r'\b(remember|recall|what did)\b.*\b(say|tell|mention)\b',
                r'\b(previous|earlier|before)\b.*\b(conversation|discussion)\b',
                r'\b(context|history|past)\b'
            ]
        }
    
    def classify_intent(self, text: str) -> Tuple[Intent, float]:
        """Classify intent of input text."""
        text_lower = text.lower()
        scores = {}
        
        for intent, patterns in self.patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    score += 1
            
            if score > 0:
                # Normalize by number of patterns for this intent
                scores[intent] = score / len(patterns)
        
        if not scores:
            return Intent.GENERAL, 0.0
        
        # Return highest scoring intent
        best_intent = max(scores.keys(), key=lambda x: scores[x])
        return best_intent, scores[best_intent]
    
    def get_required_fields(self, intent: Intent) -> List[str]:
        """Get required fields for intent."""
        field_requirements = {
            Intent.CALENDAR_CREATE: ["title"],
            Intent.EMAIL_SEND: ["to", "subject"],
            Intent.WEATHER: [],
            Intent.APP_LAUNCH: ["app_name"],
            Intent.TERMINAL: ["command"],
            Intent.WEB_SEARCH: ["query"],
            Intent.MEMORY_LOOKUP: ["query"],
            Intent.CALENDAR_CHECK: [],
            Intent.CALENDAR_SEARCH: ["query"],
            Intent.EMAIL_READ: []
        }
        return field_requirements.get(intent, [])
    
    def extract_fields(self, text: str, intent: Intent) -> Dict[str, str]:
        """Extract fields from text by intent."""
        text_lower = text.lower()
        fields = {}
        
        if intent == Intent.CALENDAR_CREATE:
            # Extract activity title
            activity_patterns = [
                r'\b(gym|workout|meeting|lunch|dinner|appointment|call)\b',
                r'\bgoing to\s+(\w+)',
                r'\b(schedule|create|add)\s+([^at]+?)(?:\s+at|\s+for|\s+on|$)'
            ]
            for pattern in activity_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    if pattern == activity_patterns[1]:
                        fields["title"] = match.group(1)
                    elif pattern == activity_patterns[2]:
                        fields["title"] = match.group(2).strip()
                    else:
                        fields["title"] = match.group(0)
                    break
            
            # Extract time
            time_patterns = [
                r'\b(\d{1,2}):(\d{2})\s*(am|pm)?\b',
                r'\b(\d{1,2})\s*(am|pm)\b'
            ]
            for pattern in time_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    if pattern == time_patterns[0]:
                        hour, minute, ampm = match.groups()
                        if ampm and ampm == 'pm' and int(hour) < 12:
                            hour = str(int(hour) + 12)
                        elif ampm and ampm == 'am' and hour == '12':
                            hour = '00'
                        fields["time"] = f"{hour.zfill(2)}:{minute}"
                    else:
                        hour, ampm = match.groups()
                        if ampm == 'pm' and int(hour) < 12:
                            hour = str(int(hour) + 12)
                        elif ampm == 'am' and hour == '12':
                            hour = '00'
                        fields["time"] = f"{hour.zfill(2)}:00"
                    break
            
            # Extract date
            if 'tomorrow' in text_lower:
                from datetime import datetime, timedelta
                fields["date"] = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            elif 'today' in text_lower:
                from datetime import datetime
                fields["date"] = datetime.now().strftime("%Y-%m-%d")
        
        elif intent == Intent.EMAIL_SEND:
            # Extract recipient
            if '@' in text:
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
                if email_match:
                    fields["to"] = email_match.group(0)
        
        elif intent == Intent.TERMINAL:
            # For terminal commands, pass the full text to let the LLM interpret
            # The LLM will convert natural language like "list files on desktop" 
            # into actual commands like "ls ~/Desktop"
            fields["command"] = text  # Pass original text, not text_lower
        
        elif intent == Intent.WEB_SEARCH:
            # Extract search query
            search_patterns = [
                r'search for (.+?)(?:\.|$)',
                r'look up (.+?)(?:\.|$)',
                r'find (.+?)(?:\.|$)',
                r'google (.+?)(?:\.|$)'
            ]
            for pattern in search_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    fields["query"] = match.group(1).strip()
                    break
        
        return fields

# Global instance
intent_classifier = IntentClassifier()