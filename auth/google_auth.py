"""
Google OAuth2 Authentication for Jarvis.
Handles authentication flow for Gmail and Google Calendar APIs.
"""

import os
import json
import pickle
from pathlib import Path
from typing import Optional, List
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

# OAuth2 scopes for Gmail and Calendar
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events'
]

class GoogleAuthManager:
    """Manages Google OAuth2 authentication for Jarvis."""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.credentials_file = self.base_dir / 'credentials.json'
        self.token_file = self.base_dir / 'token.pickle'
        self._credentials = None
        self._gmail_service = None
        self._calendar_service = None
    
    def setup_credentials(self, credentials_path: str = None) -> bool:
        """
        Set up Google API credentials.
        
        Args:
            credentials_path: Path to credentials.json file downloaded from Google Cloud Console
            
        Returns:
            bool: True if credentials are set up successfully
        """
        if credentials_path:
            # Copy provided credentials file
            import shutil
            shutil.copy2(credentials_path, self.credentials_file)
        
        if not self.credentials_file.exists():
            logging.error("❌ credentials.json not found. Please download from Google Cloud Console")
            return False
        
        try:
            # Test if credentials file is valid JSON
            with open(self.credentials_file, 'r') as f:
                json.load(f)
            logging.info("✅ Google API credentials file found and valid")
            return True
        except json.JSONDecodeError:
            logging.error("❌ credentials.json is not valid JSON")
            return False
    
    def authenticate(self, force_reauth: bool = False) -> bool:
        """
        Authenticate with Google APIs using OAuth2 flow.
        
        Args:
            force_reauth: Force re-authentication even if token exists
            
        Returns:
            bool: True if authentication successful
        """
        creds = None
        
        # Load existing token
        if self.token_file.exists() and not force_reauth:
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logging.info("✅ Refreshed Google OAuth2 token")
                except Exception as e:
                    logging.warning(f"⚠️ Token refresh failed: {e}")
                    creds = None
            
            if not creds:
                if not self.credentials_file.exists():
                    logging.error("❌ credentials.json not found. Run setup_credentials() first")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file), SCOPES
                )
                # Use local server for OAuth flow
                creds = flow.run_local_server(port=8080)
                logging.info("✅ Completed Google OAuth2 authentication")
            
            # Save the credentials for the next run
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        self._credentials = creds
        return True
    
    def get_gmail_service(self):
        """Get authenticated Gmail API service."""
        if not self._gmail_service and self._credentials:
            try:
                self._gmail_service = build('gmail', 'v1', credentials=self._credentials)
                logging.info("✅ Gmail API service initialized")
            except Exception as e:
                logging.error(f"❌ Failed to initialize Gmail service: {e}")
        return self._gmail_service
    
    def get_calendar_service(self):
        """Get authenticated Google Calendar API service."""
        if not self._calendar_service and self._credentials:
            try:
                self._calendar_service = build('calendar', 'v3', credentials=self._credentials)
                logging.info("✅ Google Calendar API service initialized")
            except Exception as e:
                logging.error(f"❌ Failed to initialize Calendar service: {e}")
        return self._calendar_service
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated with Google APIs."""
        return self._credentials is not None and self._credentials.valid
    
    def revoke_access(self) -> bool:
        """Revoke access and remove stored tokens."""
        try:
            if self.token_file.exists():
                os.remove(self.token_file)
            
            if self._credentials:
                # Revoke the token
                self._credentials.revoke(Request())
            
            self._credentials = None
            self._gmail_service = None
            self._calendar_service = None
            
            logging.info("✅ Google API access revoked")
            return True
        except Exception as e:
            logging.error(f"❌ Error revoking access: {e}")
            return False
    
    def test_connection(self) -> dict:
        """Test connections to Gmail and Calendar APIs."""
        results = {
            'gmail': False,
            'calendar': False,
            'errors': []
        }
        
        if not self.is_authenticated():
            results['errors'].append("Not authenticated")
            return results
        
        # Test Gmail API
        try:
            gmail_service = self.get_gmail_service()
            if gmail_service:
                profile = gmail_service.users().getProfile(userId='me').execute()
                results['gmail'] = True
                logging.info(f"✅ Gmail API test successful for {profile.get('emailAddress')}")
        except Exception as e:
            results['errors'].append(f"Gmail API error: {e}")
            logging.error(f"❌ Gmail API test failed: {e}")
        
        # Test Calendar API
        try:
            calendar_service = self.get_calendar_service()
            if calendar_service:
                calendars = calendar_service.calendarList().list().execute()
                results['calendar'] = True
                logging.info(f"✅ Calendar API test successful, found {len(calendars.get('items', []))} calendars")
        except Exception as e:
            results['errors'].append(f"Calendar API error: {e}")
            logging.error(f"❌ Calendar API test failed: {e}")
        
        return results

# Global auth manager instance
google_auth = GoogleAuthManager()