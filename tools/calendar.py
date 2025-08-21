from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
import os
import logging
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv
from db.memory import memory_system
import json

load_dotenv()

class CalendarCheckInput(BaseModel):
    days_ahead: int = Field(default=7, description="Number of days ahead to check for events")

class CalendarCreateInput(BaseModel):
    title: str = Field(..., description="Event title")
    date: str = Field(..., description="Event date (YYYY-MM-DD)")
    time: str = Field(..., description="Event time (HH:MM)")
    duration: int = Field(default=60, description="Duration in minutes")
    description: str = Field(default="", description="Event description")

class CalendarSearchInput(BaseModel):
    query: str = Field(..., description="Search query for calendar events")
    days_back: int = Field(default=30, description="How many days back to search")

def check_calendar_events(days_ahead: int = 7) -> str:
    """Check upcoming calendar events."""
    try:
        # Try Google Calendar API
        from tools.google_api import get_calendar_events
        
        events = get_calendar_events(days_ahead)
        
        if events:
            response_parts = [f"📅 **Upcoming events for next {days_ahead} days via Google Calendar:**\n"]
            
            for i, event in enumerate(events, 1):
                title = event['title']
                start_time = event['start']
                
                # Format time
                try:
                    if 'T' in start_time:
                        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        time_str = dt.strftime('%a, %b %d at %I:%M %p')
                    else:
                        dt = datetime.fromisoformat(start_time)
                        time_str = dt.strftime('%a, %b %d (All day)')
                except:
                    time_str = start_time
                
                response_parts.append(f"{i}. **{title}**")
                response_parts.append(f"   📅 {time_str}")
                
                if event.get('location'):
                    response_parts.append(f"   📍 {event['location']}")
                
                if event.get('description'):
                    desc_preview = event['description'][:100].replace('\n', ' ')
                    response_parts.append(f"   📝 {desc_preview}...")
                
                response_parts.append("")
            
            result_text = "\n".join(response_parts)
            
            # Store in memory
            memory_system.store_knowledge(
                content=f"Google Calendar check on {datetime.now().strftime('%Y-%m-%d')}: Found {len(events)} upcoming events. " + 
                       " | ".join([e['title'][:30] for e in events[:3]]),
                source="google_calendar_api",
                category="calendar"
            )
            
            return result_text
        else:
            return f"📅 No upcoming events found for the next {days_ahead} days via Google Calendar."
    
    except Exception as e:
        # Fallback to memory-based calendar
        logging.warning(f"Google Calendar API failed, using memory: {e}")
        return check_calendar_events_memory(days_ahead)

def check_calendar_events_memory(days_ahead: int = 7) -> str:
    """Memory-based calendar checking."""
    try:
        # Check stored calendar info
        calendar_context = memory_system.search_knowledge("calendar events meeting appointment", category="calendar", limit=5)
        
        if calendar_context:
            response_parts = [f"📅 **Checking calendar for next {days_ahead} days:**\n"]
            response_parts.append("Based on recent calendar activity:")
            
            for event in calendar_context:
                if event["relevance_score"] > 0.5:
                    response_parts.append(f"• {event['content'][:100]}...")
            
            response_parts.append(f"\n💡 To set up full Google Calendar integration, configure GOOGLE_CALENDAR_API_KEY and credentials in your .env file.")
        else:
            response_parts = [
                f"📅 **Calendar check for next {days_ahead} days**",
                "",
                "🔧 Google Calendar integration not yet configured.",
                "To enable full calendar features:",
                "1. Set up Google Calendar API credentials",
                "2. Add GOOGLE_CALENDAR_API_KEY to .env file",
                "3. Complete OAuth2 authentication",
                "",
                "For now, I can help you track events using memory and reminders."
            ]
        
        # Store the calendar check in memory
        memory_system.store_knowledge(
            content=f"Calendar check performed on {datetime.now().strftime('%Y-%m-%d %H:%M')} for next {days_ahead} days",
            source="calendar_check",
            category="calendar"
        )
        
        return "\n".join(response_parts)
    
    except Exception as e:
        return f"❌ Error checking calendar: {str(e)}"

def create_calendar_event(title: str, date: str, time: str, duration: int = 60, description: str = "") -> str:
    """Create calendar event."""
    try:
        # Try Google Calendar API
        from tools.google_api import create_calendar_event as api_create_event
        
        # Parse date and time
        try:
            event_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        except ValueError as ve:
            logging.error(f"Date/time parsing error: {ve}")
            return f"❌ Invalid date or time format. Expected YYYY-MM-DD for date and HH:MM for time. Got date='{date}', time='{time}'"
        
        end_time = event_datetime + timedelta(minutes=duration)
        
        # Create event via API
        success = api_create_event(title, event_datetime, end_time, description)
        
        if success:
            response_parts = [
                f"✅ **Calendar event created successfully:** {title}",
                f"📅 **Date:** {event_datetime.strftime('%A, %B %d, %Y')}",
                f"⏰ **Time:** {time} - {end_time.strftime('%H:%M')} ({duration} mins)",
            ]
            
            if description:
                response_parts.append(f"📝 **Description:** {description}")
            
            # Store in memory
            memory_system.store_knowledge(
                content=f"Successfully created calendar event '{title}' on {event_datetime.strftime('%Y-%m-%d %H:%M')} in Google Calendar",
                source="google_calendar_create",
                category="calendar"
            )
            
            return "\n".join(response_parts)
        else:
            # API failed, use fallback
            logging.warning("Google Calendar API call returned False, falling back to memory storage")
            return create_calendar_event_memory(title, date, time, duration, description)
    
    except ImportError:
        logging.warning("Google API module not available, using memory storage")
        return create_calendar_event_memory(title, date, time, duration, description)
    except Exception as e:
        # Fallback to memory storage
        logging.error(f"Google Calendar API failed with error: {e}")
        return create_calendar_event_memory(title, date, time, duration, description)

def create_calendar_event_memory(title: str, date: str, time: str, duration: int = 60, description: str = "") -> str:
    """Memory-based event creation."""
    try:
        # Parse date and time
        event_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        end_time = event_datetime + timedelta(minutes=duration)
        
        # Format event details
        event_details = {
            "title": title,
            "date": date,
            "time": time,
            "duration": duration,
            "description": description,
            "start_datetime": event_datetime.isoformat(),
            "end_datetime": end_time.isoformat()
        }
        
        # Store in memory as a reminder/event
        event_summary = f"Event: {title} on {date} at {time} ({duration} mins)"
        if description:
            event_summary += f" - {description}"
        
        memory_system.store_knowledge(
            content=event_summary,
            source="calendar_create",
            category="calendar"
        )
        
        # Store in memory for now
        response_parts = [
            f"✅ **Event created:** {title}",
            f"📅 **Date:** {event_datetime.strftime('%A, %B %d, %Y')}",
            f"⏰ **Time:** {time} - {end_time.strftime('%H:%M')} ({duration} mins)",
        ]
        
        if description:
            response_parts.append(f"📝 **Description:** {description}")
        
        response_parts.extend([
            "",
            "💡 Event stored in memory. For full Google Calendar integration, configure API credentials."
        ])
        
        return "\n".join(response_parts)
    
    except ValueError as e:
        return f"❌ Invalid date/time format. Use YYYY-MM-DD for date and HH:MM for time. Error: {str(e)}"
    except Exception as e:
        return f"❌ Error creating calendar event: {str(e)}"

def search_calendar_events(query: str, days_back: int = 30) -> str:
    """Search calendar events in memory."""
    try:
        # Search for calendar-related entries in memory
        results = memory_system.search_knowledge(query, category="calendar", limit=10)
        
        if not results:
            return f"🔍 No calendar events found matching '{query}'"
        
        response_parts = [f"🔍 **Calendar search results for '{query}':**\n"]
        
        for i, result in enumerate(results, 1):
            if result["relevance_score"] > 0.4:  # Include somewhat relevant results
                timestamp = result.get("timestamp", "Unknown time")[:10]  # Just the date part
                source = result.get("source", "calendar")
                
                response_parts.append(f"{i}. [{timestamp}] {result['content']}")
                response_parts.append("")
        
        if len(response_parts) == 1:  # Only header, no results
            return f"🔍 No relevant calendar events found matching '{query}'"
        
        return "\n".join(response_parts)
    
    except Exception as e:
        return f"❌ Error searching calendar: {str(e)}"

def parse_natural_event(text: str) -> dict:
    """Parse natural language into event components."""
    import re
    from dateutil.parser import parse as date_parse
    
    # Simplified parser
    result = {
        "title": text,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": "09:00",
        "duration": 60,
        "description": ""
    }
    
    # Try to extract time patterns
    time_pattern = r'(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)?'
    time_match = re.search(time_pattern, text)
    if time_match:
        hour, minute = time_match.groups()[:2]
        am_pm = time_match.group(3)
        
        if am_pm and am_pm.lower() == 'pm' and int(hour) < 12:
            hour = str(int(hour) + 12)
        elif am_pm and am_pm.lower() == 'am' and hour == '12':
            hour = '00'
        
        result["time"] = f"{hour.zfill(2)}:{minute}"
    
    # Try to extract date patterns
    date_patterns = [
        r'tomorrow',
        r'today',
        r'next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
        r'\d{4}-\d{2}-\d{2}',
        r'\d{1,2}/\d{1,2}/\d{4}',
    ]
    
    for pattern in date_patterns:
        date_match = re.search(pattern, text.lower())
        if date_match:
            date_text = date_match.group()
            
            if date_text == 'tomorrow':
                result["date"] = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            elif date_text == 'today':
                result["date"] = datetime.now().strftime("%Y-%m-%d")
            else:
                try:
                    parsed_date = date_parse(date_text)
                    result["date"] = parsed_date.strftime("%Y-%m-%d")
                except:
                    pass
            break
    
    return result

def _parse_date(date_str: str) -> str:
    """Parse various date formats into YYYY-MM-DD format."""
    date_str = date_str.lower().strip()
    
    if date_str == 'today':
        return datetime.now().strftime("%Y-%m-%d")
    elif date_str == 'tomorrow':
        return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    elif 'next week' in date_str:
        return (datetime.now() + timedelta(weeks=1)).strftime("%Y-%m-%d")
    elif 'next month' in date_str:
        return (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    else:
        # Try to parse standard formats
        try:
            from dateutil.parser import parse as date_parse
            parsed_date = date_parse(date_str)
            return parsed_date.strftime("%Y-%m-%d")
        except:
            # If parsing fails, default to tomorrow
            logging.warning(f"Could not parse date '{date_str}', defaulting to tomorrow")
            return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

def _parse_time(time_str: str) -> str:
    """Parse various time formats into HH:MM format."""
    time_str = time_str.lower().strip()
    
    # Handle AM/PM format
    import re
    am_pm_pattern = r'(\d{1,2}):?(\d{2})?\s*(am|pm)'
    match = re.search(am_pm_pattern, time_str)
    
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        am_pm = match.group(3)
        
        if am_pm == 'pm' and hour != 12:
            hour += 12
        elif am_pm == 'am' and hour == 12:
            hour = 0
            
        return f"{hour:02d}:{minute:02d}"
    
    # Handle 24-hour format
    hour_pattern = r'(\d{1,2}):(\d{2})'
    match = re.search(hour_pattern, time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
    
    # If parsing fails, return as-is or default
    logging.warning(f"Could not parse time '{time_str}', returning as-is")
    return time_str

def _validate_calendar_fields(title: str, date: str, time: str) -> bool:
    """Validate calendar event fields."""
    if not title or not title.strip():
        return False
    
    # Validate date format (YYYY-MM-DD)
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return False
    
    # Validate time format (HH:MM)
    try:
        datetime.strptime(time, "%H:%M")
    except ValueError:
        return False
    
    return True

# Combined calendar tool
class CalendarActionInput(BaseModel):
    action: str = Field(..., description="Calendar action: 'check', 'create', or 'search'")
    title: str = Field(default="", description="For create: event title")
    date: str = Field(default="", description="For create: event date (YYYY-MM-DD)")
    time: str = Field(default="", description="For create: event time (HH:MM)")
    duration: int = Field(default=60, description="For create: duration in minutes")
    description: str = Field(default="", description="For create: event description")
    query: str = Field(default="", description="For search: search query")
    days_ahead: int = Field(default=7, description="For check: days ahead to look")
    days_back: int = Field(default=30, description="For search: days back to search")

def calendar_tool_main(action: str, title: str = "", date: str = "", time: str = "", 
                      duration: int = 60, description: str = "", query: str = "", 
                      days_ahead: int = 7, days_back: int = 30) -> str:
    """Main calendar tool that handles check, create, and search actions."""
    try:
        # Ensure parameters are not None and have valid defaults
        title = title if title is not None else ""
        date = date if date is not None else ""
        time = time if time is not None else ""
        duration = duration if duration is not None and duration > 0 else 60
        description = description if description is not None else ""
        query = query if query is not None else ""
        days_ahead = days_ahead if days_ahead is not None and days_ahead > 0 else 7
        days_back = days_back if days_back is not None and days_back > 0 else 30
        
        if action == "check":
            return check_calendar_events(days_ahead)
        
        elif action == "create":
            title = title.strip()
            if not title:
                return "❌ Event title is required for creating calendar events. What should I call this event?"
            
            # Smart date resolution - fix hardcoded dates
            date = date.strip()
            if not date:
                # Default to tomorrow instead of hardcoded date
                date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                # Parse natural language dates
                date = _parse_date(date)
            
            time = time.strip()
            if not time:
                time = '09:00'  # Default to 9 AM
            else:
                # Validate and normalize time format
                time = _parse_time(time)
            
            # Validate that all required fields are present and properly formatted
            if not _validate_calendar_fields(title, date, time):
                return "❌ Invalid calendar event data. Please check the title, date, and time format."
            
            return create_calendar_event(title, date, time, duration, description)
        
        elif action == "search":
            query = query.strip()
            if not query:
                return "❌ Search query is required for searching calendar events."
                
            return search_calendar_events(query, days_back)
        
        else:
            return "❌ Invalid calendar action. Use 'check', 'create', or 'search'."
            
    except Exception as e:
        return f"❌ Calendar tool error: {str(e)}"

calendar_tool = StructuredTool.from_function(
    name="calendar_management",
    description="Manage calendar events: check upcoming events, create new events, or search through calendar history.",
    func=calendar_tool_main,
    args_schema=CalendarActionInput
)