"""
Google Calendar integration using OAuth2 authentication.
Provides secure access to Google Calendar for viewing, creating, and managing events.
"""

from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pytz
from googleapiclient.errors import HttpError
import logging
import re
from dateutil.parser import parse as date_parse

from auth.google_auth import google_auth
from db.memory import memory_system

class CalendarCheckInput(BaseModel):
    days_ahead: int = Field(default=7, description="Number of days ahead to check for events")
    calendar_id: str = Field(default="primary", description="Calendar ID ('primary' for main calendar)")

class CalendarCreateInput(BaseModel):
    title: str = Field(..., description="Event title")
    start_datetime: str = Field(..., description="Start date/time (YYYY-MM-DD HH:MM or natural language)")
    end_datetime: Optional[str] = Field(default="", description="End date/time (auto-calculated if empty)")
    description: str = Field(default="", description="Event description")
    location: str = Field(default="", description="Event location")
    attendees: str = Field(default="", description="Attendee emails (comma-separated)")
    calendar_id: str = Field(default="primary", description="Calendar ID")

class CalendarSearchInput(BaseModel):
    query: str = Field(..., description="Search query for calendar events")
    days_back: int = Field(default=30, description="How many days back to search")
    days_ahead: int = Field(default=30, description="How many days ahead to search")
    calendar_id: str = Field(default="primary", description="Calendar ID")

def check_calendar_oauth(days_ahead: int = 7, calendar_id: str = "primary") -> str:
    """Check upcoming Google Calendar events using OAuth2."""
    try:
        if not google_auth.is_authenticated():
            if not google_auth.authenticate():
                return "❌ Google authentication failed. Run 'python setup_google_auth.py' to authenticate."
        
        calendar_service = google_auth.get_calendar_service()
        if not calendar_service:
            return "❌ Failed to initialize Google Calendar service"
        
        # Calculate time range
        now = datetime.utcnow()
        end_time = now + timedelta(days=days_ahead)
        
        # Get events
        events_result = calendar_service.events().list(
            calendarId=calendar_id,
            timeMin=now.isoformat() + 'Z',
            timeMax=end_time.isoformat() + 'Z',
            maxResults=20,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return f"📅 No upcoming events found for the next {days_ahead} days."
        
        # Format response
        response_parts = [f"📅 **Upcoming events for next {days_ahead} days:**\n"]
        
        for i, event in enumerate(events, 1):
            title = event.get('summary', 'No Title')
            
            # Parse start time
            start = event['start'].get('dateTime', event['start'].get('date'))
            if 'T' in start:  # DateTime
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                time_str = start_dt.strftime('%a, %b %d at %I:%M %p')
            else:  # All-day event
                start_dt = datetime.fromisoformat(start)
                time_str = start_dt.strftime('%a, %b %d (All day)')
            
            response_parts.append(f"{i}. **{title}**")
            response_parts.append(f"   📅 {time_str}")
            
            # Add location if available
            location = event.get('location')
            if location:
                response_parts.append(f"   📍 {location}")
            
            # Add description preview if available
            description = event.get('description', '')
            if description:
                desc_preview = description[:100].replace('\n', ' ')
                response_parts.append(f"   📝 {desc_preview}...")
            
            response_parts.append("")
        
        result_text = "\n".join(response_parts)
        
        # Store calendar summary in memory
        memory_system.store_knowledge(
            content=f"Calendar check on {datetime.now().strftime('%Y-%m-%d')}: Found {len(events)} upcoming events. " + 
                   " | ".join([e.get('summary', 'No Title')[:30] for e in events[:3]]),
            source="calendar_oauth",
            category="calendar"
        )
        
        return result_text
        
    except HttpError as e:
        error_msg = f"Google Calendar API error: {e}"
        logging.error(error_msg)
        return f"❌ {error_msg}"
    except Exception as e:
        error_msg = f"Error checking calendar: {str(e)}"
        logging.error(error_msg)
        return f"❌ {error_msg}"

def create_calendar_event_oauth(
    title: str, 
    start_datetime: str, 
    end_datetime: str = "", 
    description: str = "", 
    location: str = "",
    attendees: str = "",
    calendar_id: str = "primary"
) -> str:
    """Create a Google Calendar event using OAuth2."""
    try:
        if not google_auth.is_authenticated():
            if not google_auth.authenticate():
                return "❌ Google authentication failed. Run 'python setup_google_auth.py' to authenticate."
        
        calendar_service = google_auth.get_calendar_service()
        if not calendar_service:
            return "❌ Failed to initialize Google Calendar service"
        
        # Parse start datetime
        try:
            start_dt = parse_natural_datetime(start_datetime)
        except ValueError as e:
            return f"❌ Invalid start date/time: {e}"
        
        # Parse or calculate end datetime
        if end_datetime:
            try:
                end_dt = parse_natural_datetime(end_datetime)
            except ValueError as e:
                return f"❌ Invalid end date/time: {e}"
        else:
            # Default to 1 hour duration
            end_dt = start_dt + timedelta(hours=1)
        
        # Build event object
        event = {
            'summary': title,
            'description': description,
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'America/New_York',  # TODO: Use user's timezone
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'America/New_York',
            }
        }
        
        if location:
            event['location'] = location
        
        if attendees:
            attendee_list = [{'email': email.strip()} for email in attendees.split(',')]
            event['attendees'] = attendee_list
        
        # Create the event
        created_event = calendar_service.events().insert(
            calendarId=calendar_id, 
            body=event
        ).execute()
        
        # Format response
        start_str = start_dt.strftime('%A, %B %d, %Y at %I:%M %p')
        end_str = end_dt.strftime('%I:%M %p')
        
        response_parts = [
            f"✅ **Calendar event created:** {title}",
            f"📅 **Time:** {start_str} - {end_str}",
        ]
        
        if location:
            response_parts.append(f"📍 **Location:** {location}")
        
        if attendees:
            response_parts.append(f"👥 **Attendees:** {attendees}")
        
        if description:
            response_parts.append(f"📝 **Description:** {description}")
        
        # Add event link
        event_link = created_event.get('htmlLink', '')
        if event_link:
            response_parts.append(f"🔗 **Event Link:** {event_link}")
        
        result_text = "\n".join(response_parts)
        
        # Store in memory
        memory_system.store_knowledge(
            content=f"Created calendar event '{title}' on {start_dt.strftime('%Y-%m-%d %H:%M')} via Google Calendar OAuth",
            source="calendar_oauth_create",
            category="calendar"
        )
        
        return result_text
        
    except HttpError as e:
        error_msg = f"Google Calendar API error: {e}"
        logging.error(error_msg)
        return f"❌ {error_msg}"
    except Exception as e:
        error_msg = f"Error creating calendar event: {str(e)}"
        logging.error(error_msg)
        return f"❌ {error_msg}"

def search_calendar_oauth(
    query: str, 
    days_back: int = 30, 
    days_ahead: int = 30,
    calendar_id: str = "primary"
) -> str:
    """Search Google Calendar events using OAuth2."""
    try:
        if not google_auth.is_authenticated():
            if not google_auth.authenticate():
                return "❌ Google authentication failed. Run 'python setup_google_auth.py' to authenticate."
        
        calendar_service = google_auth.get_calendar_service()
        if not calendar_service:
            return "❌ Failed to initialize Google Calendar service"
        
        # Calculate time range
        start_time = datetime.utcnow() - timedelta(days=days_back)
        end_time = datetime.utcnow() + timedelta(days=days_ahead)
        
        # Search events
        events_result = calendar_service.events().list(
            calendarId=calendar_id,
            timeMin=start_time.isoformat() + 'Z',
            timeMax=end_time.isoformat() + 'Z',
            q=query,
            maxResults=20,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return f"🔍 No calendar events found matching '{query}'"
        
        # Format response
        response_parts = [f"🔍 **Found {len(events)} calendar event(s) matching '{query}':**\n"]
        
        for i, event in enumerate(events, 1):
            title = event.get('summary', 'No Title')
            
            # Parse start time
            start = event['start'].get('dateTime', event['start'].get('date'))
            if 'T' in start:  # DateTime
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                time_str = start_dt.strftime('%a, %b %d at %I:%M %p')
            else:  # All-day event
                start_dt = datetime.fromisoformat(start)
                time_str = start_dt.strftime('%a, %b %d (All day)')
            
            response_parts.append(f"{i}. **{title}**")
            response_parts.append(f"   📅 {time_str}")
            
            location = event.get('location')
            if location:
                response_parts.append(f"   📍 {location}")
            
            response_parts.append("")
        
        return "\n".join(response_parts)
        
    except HttpError as e:
        error_msg = f"Google Calendar API error: {e}"
        logging.error(error_msg)
        return f"❌ {error_msg}"
    except Exception as e:
        error_msg = f"Error searching calendar: {str(e)}"
        logging.error(error_msg)
        return f"❌ {error_msg}"

def parse_natural_datetime(datetime_str: str) -> datetime:
    """Parse natural language datetime strings."""
    datetime_str = datetime_str.strip().lower()
    
    # Handle relative terms
    now = datetime.now()
    
    if datetime_str in ['now', 'right now']:
        return now
    elif datetime_str in ['today']:
        return now.replace(hour=9, minute=0, second=0, microsecond=0)
    elif datetime_str in ['tomorrow']:
        return (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    elif 'next week' in datetime_str:
        return (now + timedelta(days=7)).replace(hour=9, minute=0, second=0, microsecond=0)
    
    # Handle day names
    weekdays = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    
    for day_name, day_num in weekdays.items():
        if day_name in datetime_str:
            days_ahead = (day_num - now.weekday()) % 7
            if days_ahead == 0:  # Today, assume next week
                days_ahead = 7
            target_date = now + timedelta(days=days_ahead)
            
            # Extract time if present
            time_match = re.search(r'(\d{1,2}):?(\d{2})?\s*(am|pm)', datetime_str)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2)) if time_match.group(2) else 0
                am_pm = time_match.group(3)
                
                if am_pm == 'pm' and hour < 12:
                    hour += 12
                elif am_pm == 'am' and hour == 12:
                    hour = 0
                
                return target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            else:
                return target_date.replace(hour=9, minute=0, second=0, microsecond=0)
    
    # Try standard date parsing
    try:
        return date_parse(datetime_str)
    except:
        raise ValueError(f"Could not parse datetime: {datetime_str}")

# Create LangChain tools
calendar_check_oauth_tool = StructuredTool.from_function(
    name="check_calendar_oauth",
    description="Check upcoming Google Calendar events using secure OAuth2 authentication.",
    func=check_calendar_oauth,
    args_schema=CalendarCheckInput
)

calendar_create_oauth_tool = StructuredTool.from_function(
    name="create_calendar_event_oauth",
    description="Create Google Calendar events using secure OAuth2 authentication.",
    func=create_calendar_event_oauth,
    args_schema=CalendarCreateInput
)

calendar_search_oauth_tool = StructuredTool.from_function(
    name="search_calendar_oauth",
    description="Search Google Calendar events using secure OAuth2 authentication.",
    func=search_calendar_oauth,
    args_schema=CalendarSearchInput
)

# Combined Calendar OAuth tool
class CalendarOAuthActionInput(BaseModel):
    action: str = Field(..., description="Calendar action: 'check', 'create', or 'search'")
    title: str = Field(default="", description="For create: event title")
    start_datetime: str = Field(default="", description="For create: start date/time")
    end_datetime: str = Field(default="", description="For create: end date/time (optional)")
    description: str = Field(default="", description="For create: event description")
    location: str = Field(default="", description="For create: event location")
    attendees: str = Field(default="", description="For create: attendee emails")
    query: str = Field(default="", description="For search: search query")
    days_ahead: int = Field(default=7, description="For check: days ahead to look")
    days_back: int = Field(default=30, description="For search: days back to search")
    calendar_id: str = Field(default="primary", description="Calendar ID")

def calendar_oauth_main(action: str, **kwargs) -> str:
    """Main Calendar OAuth tool that handles check, create, and search actions."""
    if action == "check":
        return check_calendar_oauth(
            kwargs.get('days_ahead', 7),
            kwargs.get('calendar_id', 'primary')
        )
    elif action == "create":
        if not kwargs.get('title') or not kwargs.get('start_datetime'):
            return "❌ Event title and start time are required for creating calendar events."
        return create_calendar_event_oauth(
            kwargs['title'],
            kwargs['start_datetime'],
            kwargs.get('end_datetime', ''),
            kwargs.get('description', ''),
            kwargs.get('location', ''),
            kwargs.get('attendees', ''),
            kwargs.get('calendar_id', 'primary')
        )
    elif action == "search":
        if not kwargs.get('query'):
            return "❌ Search query is required for searching calendar events."
        return search_calendar_oauth(
            kwargs['query'],
            kwargs.get('days_back', 30),
            kwargs.get('days_ahead', 30),
            kwargs.get('calendar_id', 'primary')
        )
    else:
        return "❌ Invalid calendar action. Use 'check', 'create', or 'search'."

calendar_oauth_tool = StructuredTool.from_function(
    name="google_calendar_oauth",
    description="Secure Google Calendar management using OAuth2: check upcoming events, create new events, or search through calendar history.",
    func=calendar_oauth_main,
    args_schema=CalendarOAuthActionInput
)