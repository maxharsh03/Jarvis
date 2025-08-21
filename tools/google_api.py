"""Google API integration for Gmail and Calendar."""

import os
import json
import pickle
from pathlib import Path
from typing import Optional, List, Dict
import base64
import email
from datetime import datetime, timedelta
from dotenv import load_dotenv

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

load_dotenv()

# OAuth2 scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send', 
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events'
]

class GoogleAPIManager:
    """Google API authentication and services."""
    
    def __init__(self):
        self.credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'auth/credentials.json')
        self.token_file = 'auth/token.pickle'
        self._credentials = None
        self._gmail_service = None
        self._calendar_service = None
        
        # Create auth directory
        Path('auth').mkdir(exist_ok=True)
    
    def authenticate(self) -> bool:
        """Authenticate with Google APIs."""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # Get credentials if needed
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logging.info("✅ Refreshed Google API token")
                except Exception as e:
                    logging.warning(f"⚠️ Token refresh failed: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_file):
                    logging.error(f"❌ Credentials file not found: {self.credentials_file}")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=8080)
                logging.info("✅ Completed Google API authentication")
            
            # Save creds
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        self._credentials = creds
        return True
    
    def get_gmail_service(self):
        """Get Gmail API service."""
        if not self._gmail_service and self._credentials:
            self._gmail_service = build('gmail', 'v1', credentials=self._credentials)
        return self._gmail_service
    
    def get_calendar_service(self):
        """Get Calendar API service."""
        if not self._calendar_service and self._credentials:
            self._calendar_service = build('calendar', 'v3', credentials=self._credentials)
        return self._calendar_service
    
    def is_ready(self) -> bool:
        """Check if APIs are ready."""
        return self._credentials is not None and self._credentials.valid

# Global instance
google_api = GoogleAPIManager()

def ensure_authenticated() -> bool:
    """Ensure authentication."""
    if not google_api.is_ready():
        return google_api.authenticate()
    return True

def get_gmail_messages(query: str = "", max_results: int = 10) -> List[Dict]:
    """Get Gmail messages."""
    if not ensure_authenticated():
        return []
    
    try:
        gmail_service = google_api.get_gmail_service()
        
        # Get message IDs
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        email_list = []
        
        for message in messages:
            # Get full message
            msg = gmail_service.users().messages().get(
                userId='me',
                id=message['id'],
                format='full'
            ).execute()
            
            # Extract headers
            headers = msg['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            # Get message body
            body = extract_message_body(msg['payload'])
            
            email_list.append({
                'id': message['id'],
                'subject': subject,
                'sender': sender,
                'date': date_str,
                'body': body[:300] + "..." if len(body) > 300 else body
            })
        
        return email_list
        
    except Exception as e:
        logging.error(f"Error getting Gmail messages: {e}")
        return []

def send_gmail_message(to: str, subject: str, body: str) -> bool:
    """Send Gmail message."""
    if not ensure_authenticated():
        return False
    
    try:
        gmail_service = google_api.get_gmail_service()
        
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        gmail_service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        logging.info(f"✅ Email sent to {to}")
        return True
        
    except Exception as e:
        logging.error(f"Error sending email: {e}")
        return False

def get_calendar_events(days_ahead: int = 7) -> List[Dict]:
    """Get upcoming calendar events."""
    if not ensure_authenticated():
        return []
    
    try:
        calendar_service = google_api.get_calendar_service()
        
        # Get time range
        now = datetime.utcnow()
        end_time = now + timedelta(days=days_ahead)
        
        events_result = calendar_service.events().list(
            calendarId='primary',
            timeMin=now.isoformat() + 'Z',
            timeMax=end_time.isoformat() + 'Z',
            maxResults=20,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        event_list = []
        
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            event_list.append({
                'id': event['id'],
                'title': event.get('summary', 'No Title'),
                'start': start,
                'location': event.get('location', ''),
                'description': event.get('description', '')
            })
        
        return event_list
        
    except Exception as e:
        logging.error(f"Error getting calendar events: {e}")
        return []

def create_calendar_event(title: str, start_time: datetime, end_time: datetime = None, description: str = "", location: str = "") -> bool:
    """Create a calendar event."""
    if not ensure_authenticated():
        return False
    
    try:
        calendar_service = google_api.get_calendar_service()
        
        if not end_time:
            end_time = start_time + timedelta(hours=1)
        
        event = {
            'summary': title,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'America/New_York',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'America/New_York',
            },
        }
        
        calendar_service.events().insert(calendarId='primary', body=event).execute()
        logging.info(f"✅ Calendar event created: {title}")
        return True
        
    except Exception as e:
        logging.error(f"Error creating calendar event: {e}")
        return False

def extract_message_body(payload) -> str:
    """Extract text body from Gmail message payload."""
    body = ""
    
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                if 'data' in part['body']:
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
    else:
        if payload['mimeType'] == 'text/plain' and 'data' in payload['body']:
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
    
    return body