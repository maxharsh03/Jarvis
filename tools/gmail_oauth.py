"""
Gmail integration using OAuth2 authentication.
Provides secure access to Gmail for reading, sending, and searching emails.
"""

from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import base64
import email
import re
from datetime import datetime, timedelta
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

from auth.google_auth import google_auth
from db.memory import memory_system

class GmailCheckInput(BaseModel):
    limit: int = Field(default=5, description="Number of recent emails to check")
    unread_only: bool = Field(default=True, description="Whether to check only unread emails")
    label: str = Field(default="INBOX", description="Gmail label to check (INBOX, SENT, etc.)")

class GmailSendInput(BaseModel):
    to: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body content")
    cc: Optional[str] = Field(default="", description="CC recipients (comma-separated)")
    bcc: Optional[str] = Field(default="", description="BCC recipients (comma-separated)")

class GmailSearchInput(BaseModel):
    query: str = Field(..., description="Gmail search query (sender, subject, keywords, etc.)")
    limit: int = Field(default=10, description="Maximum number of results")
    label: str = Field(default="INBOX", description="Gmail label to search in")

def check_gmail_oauth(limit: int = 5, unread_only: bool = True, label: str = "INBOX") -> str:
    """Check Gmail messages using OAuth2 authentication."""
    try:
        if not google_auth.is_authenticated():
            if not google_auth.authenticate():
                return "❌ Google authentication failed. Run 'python setup_google_auth.py' to authenticate."
        
        gmail_service = google_auth.get_gmail_service()
        if not gmail_service:
            return "❌ Failed to initialize Gmail service"
        
        # Build query
        query = f'label:{label}'
        if unread_only:
            query += ' is:unread'
        
        # Get message IDs
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=limit
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"📬 No {'unread ' if unread_only else ''}emails found in {label}."
        
        emails_info = []
        
        for message in messages:
            try:
                # Get message details
                msg = gmail_service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()
                
                # Extract headers
                headers = msg['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                
                # Clean sender name
                sender_match = re.match(r'^(.*?)<(.+)>$', sender)
                if sender_match:
                    sender_name = sender_match.group(1).strip().strip('"')
                    sender_email = sender_match.group(2)
                    sender_clean = sender_name if sender_name else sender_email
                else:
                    sender_clean = sender
                
                # Extract message body preview
                body_preview = extract_message_body(msg['payload'])[:200]
                
                emails_info.append({
                    'sender': sender_clean,
                    'subject': subject,
                    'date': date_str,
                    'preview': body_preview.replace('\n', ' ').strip() if body_preview else '',
                    'message_id': message['id']
                })
                
            except HttpError as e:
                logging.error(f"Error fetching message {message['id']}: {e}")
                continue
        
        # Format response
        email_type = "unread" if unread_only else "recent"
        response = [f"📧 **{len(emails_info)} {email_type} email(s) in {label}:**\n"]
        
        for i, email_info in enumerate(emails_info, 1):
            response.append(f"{i}. **From:** {email_info['sender']}")
            response.append(f"   **Subject:** {email_info['subject']}")
            if email_info['preview']:
                response.append(f"   **Preview:** {email_info['preview']}...")
            if email_info['date']:
                try:
                    # Parse and format date
                    parsed_date = email.utils.parsedate_to_datetime(email_info['date'])
                    formatted_date = parsed_date.strftime('%b %d, %Y at %I:%M %p')
                    response.append(f"   **Date:** {formatted_date}")
                except:
                    response.append(f"   **Date:** {email_info['date'][:50]}")
            response.append("")
        
        result_text = "\n".join(response)
        
        # Store email summary in memory
        memory_system.store_knowledge(
            content=f"Gmail check on {datetime.now().strftime('%Y-%m-%d')}: Found {len(emails_info)} {email_type} emails in {label}. " + 
                   " | ".join([f"{e['sender']}: {e['subject']}" for e in emails_info[:3]]),
            source="gmail_oauth",
            category="email"
        )
        
        return result_text
        
    except HttpError as e:
        error_msg = f"Gmail API error: {e}"
        logging.error(error_msg)
        return f"❌ {error_msg}"
    except Exception as e:
        error_msg = f"Error checking Gmail: {str(e)}"
        logging.error(error_msg)
        return f"❌ {error_msg}"

def send_gmail_oauth(to: str, subject: str, body: str, cc: str = "", bcc: str = "") -> str:
    """Send email via Gmail using OAuth2 authentication."""
    try:
        if not google_auth.is_authenticated():
            if not google_auth.authenticate():
                return "❌ Google authentication failed. Run 'python setup_google_auth.py' to authenticate."
        
        gmail_service = google_auth.get_gmail_service()
        if not gmail_service:
            return "❌ Failed to initialize Gmail service"
        
        # Create message
        message = MIMEMultipart()
        message['To'] = to
        message['Subject'] = subject
        
        if cc:
            message['Cc'] = cc
        if bcc:
            message['Bcc'] = bcc
        
        # Add body
        message.attach(MIMEText(body, 'plain'))
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Send message
        gmail_service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        # Store in memory
        recipients = [to]
        if cc:
            recipients.extend(cc.split(','))
        
        memory_system.store_knowledge(
            content=f"Sent email via Gmail OAuth to {', '.join(recipients)} with subject '{subject}' on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            source="gmail_oauth_send",
            category="email"
        )
        
        return f"✅ Email sent successfully via Gmail to {to}"
        
    except HttpError as e:
        error_msg = f"Gmail API error: {e}"
        logging.error(error_msg)
        return f"❌ {error_msg}"
    except Exception as e:
        error_msg = f"Error sending email: {str(e)}"
        logging.error(error_msg)
        return f"❌ {error_msg}"

def search_gmail_oauth(query: str, limit: int = 10, label: str = "INBOX") -> str:
    """Search Gmail messages using OAuth2 authentication."""
    try:
        if not google_auth.is_authenticated():
            if not google_auth.authenticate():
                return "❌ Google authentication failed. Run 'python setup_google_auth.py' to authenticate."
        
        gmail_service = google_auth.get_gmail_service()
        if not gmail_service:
            return "❌ Failed to initialize Gmail service"
        
        # Build search query
        search_query = f'label:{label} {query}'
        
        # Search messages
        results = gmail_service.users().messages().list(
            userId='me',
            q=search_query,
            maxResults=limit
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return f"🔍 No emails found matching '{query}' in {label}"
        
        search_results = []
        
        for message in messages[:limit]:
            try:
                # Get message details
                msg = gmail_service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='metadata',
                    metadataHeaders=['Subject', 'From', 'Date']
                ).execute()
                
                # Extract headers
                headers = msg['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                
                # Clean sender
                sender_match = re.match(r'^(.*?)<(.+)>$', sender)
                if sender_match:
                    sender_name = sender_match.group(1).strip().strip('"')
                    sender_clean = sender_name if sender_name else sender_match.group(2)
                else:
                    sender_clean = sender
                
                search_results.append({
                    'sender': sender_clean,
                    'subject': subject,
                    'date': date_str,
                    'message_id': message['id']
                })
                
            except HttpError as e:
                logging.error(f"Error fetching search result {message['id']}: {e}")
                continue
        
        # Format response
        response = [f"🔍 **Found {len(search_results)} email(s) matching '{query}' in {label}:**\n"]
        
        for i, email_info in enumerate(search_results, 1):
            response.append(f"{i}. **From:** {email_info['sender']}")
            response.append(f"   **Subject:** {email_info['subject']}")
            if email_info['date']:
                try:
                    parsed_date = email.utils.parsedate_to_datetime(email_info['date'])
                    formatted_date = parsed_date.strftime('%b %d, %Y at %I:%M %p')
                    response.append(f"   **Date:** {formatted_date}")
                except:
                    response.append(f"   **Date:** {email_info['date'][:50]}")
            response.append("")
        
        return "\n".join(response)
        
    except HttpError as e:
        error_msg = f"Gmail API error: {e}"
        logging.error(error_msg)
        return f"❌ {error_msg}"
    except Exception as e:
        error_msg = f"Error searching Gmail: {str(e)}"
        logging.error(error_msg)
        return f"❌ {error_msg}"

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

# Create LangChain tools
gmail_check_oauth_tool = StructuredTool.from_function(
    name="check_gmail_oauth",
    description="Check Gmail emails using secure OAuth2 authentication. Superior to IMAP method.",
    func=check_gmail_oauth,
    args_schema=GmailCheckInput
)

gmail_send_oauth_tool = StructuredTool.from_function(
    name="send_gmail_oauth", 
    description="Send emails via Gmail using secure OAuth2 authentication.",
    func=send_gmail_oauth,
    args_schema=GmailSendInput
)

gmail_search_oauth_tool = StructuredTool.from_function(
    name="search_gmail_oauth",
    description="Search Gmail messages using secure OAuth2 authentication.",
    func=search_gmail_oauth,
    args_schema=GmailSearchInput
)

# Combined Gmail OAuth tool
class GmailOAuthActionInput(BaseModel):
    action: str = Field(..., description="Gmail action: 'check', 'send', or 'search'")
    limit: int = Field(default=5, description="For check/search: number of results")
    unread_only: bool = Field(default=True, description="For check: only unread emails")
    label: str = Field(default="INBOX", description="Gmail label (INBOX, SENT, etc.)")
    to: str = Field(default="", description="For send: recipient email")
    subject: str = Field(default="", description="For send: email subject")
    body: str = Field(default="", description="For send: email body")
    cc: str = Field(default="", description="For send: CC recipients")
    bcc: str = Field(default="", description="For send: BCC recipients")
    query: str = Field(default="", description="For search: search query")

def gmail_oauth_main(action: str, **kwargs) -> str:
    """Main Gmail OAuth tool that handles check, send, and search actions."""
    if action == "check":
        return check_gmail_oauth(
            kwargs.get('limit', 5), 
            kwargs.get('unread_only', True),
            kwargs.get('label', 'INBOX')
        )
    elif action == "send":
        return send_gmail_oauth(
            kwargs['to'], 
            kwargs['subject'], 
            kwargs['body'],
            kwargs.get('cc', ''),
            kwargs.get('bcc', '')
        )
    elif action == "search":
        return search_gmail_oauth(
            kwargs['query'], 
            kwargs.get('limit', 10),
            kwargs.get('label', 'INBOX')
        )
    else:
        return "❌ Invalid Gmail action. Use 'check', 'send', or 'search'."

gmail_oauth_tool = StructuredTool.from_function(
    name="gmail_oauth",
    description="Secure Gmail management using OAuth2: check emails, send emails, or search through Gmail history.",
    func=gmail_oauth_main,
    args_schema=GmailOAuthActionInput
)