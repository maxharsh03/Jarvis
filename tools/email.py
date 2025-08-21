from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
import os
import imaplib
import email
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from dotenv import load_dotenv
from db.memory import memory_system
import re

load_dotenv()

class EmailCheckInput(BaseModel):
    limit: int = Field(default=5, description="Number of recent emails to check")
    unread_only: bool = Field(default=True, description="Whether to check only unread emails")

class EmailSendInput(BaseModel):
    to: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body content")

class EmailSearchInput(BaseModel):
    query: str = Field(..., description="Search query for emails (sender, subject, or keywords)")
    limit: int = Field(default=10, description="Maximum number of results")

def check_emails(limit: int = 5, unread_only: bool = True) -> str:
    """Check recent emails using Google Gmail API."""
    try:
        # Try Google API first
        from tools.google_api import get_gmail_messages
        
        query = "is:unread" if unread_only else ""
        emails = get_gmail_messages(query=query, max_results=limit)
        
        if emails:
            email_type = "unread" if unread_only else "recent"
            response = [f"📧 **{len(emails)} {email_type} email(s) via Google API:**\n"]
            
            for i, email_info in enumerate(emails, 1):
                response.append(f"{i}. **From:** {email_info['sender']}")
                response.append(f"   **Subject:** {email_info['subject']}")
                if email_info.get('body'):
                    preview = email_info['body'][:200].replace('\n', ' ')
                    response.append(f"   **Preview:** {preview}...")
                response.append("")
            
            result_text = "\n".join(response)
            
            # Store in memory
            memory_system.store_knowledge(
                content=f"Gmail API check on {datetime.now().strftime('%Y-%m-%d')}: Found {len(emails)} {email_type} emails. " + 
                       " ".join([f"{e['sender']}: {e['subject']}" for e in emails]),
                source="gmail_api",
                category="email"
            )
            
            return result_text
        else:
            return f"📬 No {'unread ' if unread_only else ''}emails found via Google API."
    
    except Exception as e:
        # Fallback to IMAP if Google API fails
        logging.warning(f"Google API failed, trying IMAP: {e}")
        return check_emails_imap(limit, unread_only)

def check_emails_imap(limit: int = 5, unread_only: bool = True) -> str:
    """Fallback IMAP email checking."""
    try:
        # Gmail IMAP settings
        imap_server = os.getenv('IMAP_SERVER', 'imap.gmail.com')
        imap_port = int(os.getenv('IMAP_PORT', '993'))
        email_address = os.getenv('EMAIL_ADDRESS')
        email_password = os.getenv('EMAIL_PASSWORD')  # App password for Gmail
        
        if not email_address or not email_password:
            return "❌ Email credentials not configured. Please set EMAIL_ADDRESS and EMAIL_PASSWORD in your .env file."
        
        # Connect to IMAP server
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        mail.login(email_address, email_password)
        mail.select('INBOX')
        
        # Search for emails
        search_criteria = 'UNSEEN' if unread_only else 'ALL'
        result, messages = mail.search(None, search_criteria)
        
        if result != 'OK' or not messages[0]:
            mail.logout()
            return "📬 No new emails found." if unread_only else "📭 No emails found."
        
        # Get message IDs (most recent first)
        message_ids = messages[0].split()[-limit:]
        emails_info = []
        
        for msg_id in reversed(message_ids):  # Most recent first
            result, msg_data = mail.fetch(msg_id, '(RFC822)')
            if result == 'OK':
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                
                # Extract email info
                sender = email_message['From']
                subject = email_message['Subject'] or "No Subject"
                date = email_message['Date']
                
                # Clean sender (remove email address part if name is present)
                sender_clean = re.sub(r'<.*?>', '', sender).strip()
                if not sender_clean:
                    sender_clean = sender
                
                # Get email body preview
                body_preview = ""
                if email_message.is_multipart():
                    for part in email_message.walk():
                        if part.get_content_type() == "text/plain":
                            body_preview = part.get_payload(decode=True).decode('utf-8', errors='ignore')[:200]
                            break
                else:
                    body_preview = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')[:200]
                
                emails_info.append({
                    'sender': sender_clean,
                    'subject': subject,
                    'date': date,
                    'preview': body_preview.replace('\n', ' ').strip()
                })
        
        mail.logout()
        
        # Format response
        if not emails_info:
            return "📬 No new emails found." if unread_only else "📭 No emails found."
        
        email_type = "unread" if unread_only else "recent"
        response = [f"📧 **{len(emails_info)} {email_type} email(s):**\n"]
        
        for i, email_info in enumerate(emails_info, 1):
            response.append(f"{i}. **From:** {email_info['sender']}")
            response.append(f"   **Subject:** {email_info['subject']}")
            if email_info['preview']:
                response.append(f"   **Preview:** {email_info['preview']}...")
            response.append(f"   **Date:** {email_info['date']}")
            response.append("")
        
        result_text = "\n".join(response)
        
        # Store email summary in memory
        memory_system.store_knowledge(
            content=f"Email check on {datetime.now().strftime('%Y-%m-%d')}: Found {len(emails_info)} {email_type} emails. " + 
                   " ".join([f"{e['sender']}: {e['subject']}" for e in emails_info]),
            source="email_check",
            category="email"
        )
        
        return result_text
    
    except Exception as e:
        return f"❌ Error checking emails: {str(e)}"

def send_email(to: str, subject: str, body: str) -> str:
    """Send an email via Google Gmail API."""
    try:
        # Try Google API first
        from tools.google_api import send_gmail_message
        
        if send_gmail_message(to, subject, body):
            # Store in memory
            memory_system.store_knowledge(
                content=f"Sent email via Gmail API to {to} with subject '{subject}' on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                source="gmail_api_send",
                category="email"
            )
            return f"✅ Email sent successfully via Gmail API to {to}"
        else:
            return "❌ Failed to send email via Gmail API"
    
    except Exception as e:
        # Fallback to SMTP if Google API fails
        logging.warning(f"Gmail API failed, trying SMTP: {e}")
        return send_email_smtp(to, subject, body)

def send_email_smtp(to: str, subject: str, body: str) -> str:
    """Fallback SMTP email sending."""
    try:
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        email_address = os.getenv('EMAIL_ADDRESS')
        email_password = os.getenv('EMAIL_PASSWORD')
        
        if not email_address or not email_password:
            return "❌ Email credentials not configured. Please set EMAIL_ADDRESS and EMAIL_PASSWORD in your .env file."
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = email_address
        msg['To'] = to
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect and send
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_address, email_password)
        
        text = msg.as_string()
        server.sendmail(email_address, to, text)
        server.quit()
        
        # Store in memory
        memory_system.store_knowledge(
            content=f"Sent email to {to} with subject '{subject}' on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            source="email_send",
            category="email"
        )
        
        return f"✅ Email sent successfully to {to}"
    
    except Exception as e:
        return f"❌ Error sending email: {str(e)}"

def search_emails(query: str, limit: int = 10) -> str:
    """Search emails by sender, subject, or content."""
    try:
        imap_server = os.getenv('IMAP_SERVER', 'imap.gmail.com')
        imap_port = int(os.getenv('IMAP_PORT', '993'))
        email_address = os.getenv('EMAIL_ADDRESS')
        email_password = os.getenv('EMAIL_PASSWORD')
        
        if not email_address or not email_password:
            return "❌ Email credentials not configured."
        
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        mail.login(email_address, email_password)
        mail.select('INBOX')
        
        # Try different search criteria
        search_queries = [
            f'FROM "{query}"',      # Search by sender
            f'SUBJECT "{query}"',   # Search by subject
            f'BODY "{query}"'       # Search by body content
        ]
        
        all_messages = set()
        for search_query in search_queries:
            result, messages = mail.search(None, search_query)
            if result == 'OK' and messages[0]:
                all_messages.update(messages[0].split())
        
        if not all_messages:
            mail.logout()
            return f"🔍 No emails found matching '{query}'"
        
        # Get most recent matches
        message_ids = list(all_messages)[-limit:]
        results = []
        
        for msg_id in reversed(message_ids):
            result, msg_data = mail.fetch(msg_id, '(RFC822)')
            if result == 'OK':
                email_message = email.message_from_bytes(msg_data[0][1])
                
                sender = email_message['From']
                subject = email_message['Subject'] or "No Subject"
                date = email_message['Date']
                
                sender_clean = re.sub(r'<.*?>', '', sender).strip()
                if not sender_clean:
                    sender_clean = sender
                
                results.append({
                    'sender': sender_clean,
                    'subject': subject,
                    'date': date
                })
        
        mail.logout()
        
        if not results:
            return f"🔍 No emails found matching '{query}'"
        
        response = [f"🔍 **Found {len(results)} email(s) matching '{query}':**\n"]
        for i, email_info in enumerate(results, 1):
            response.append(f"{i}. **From:** {email_info['sender']}")
            response.append(f"   **Subject:** {email_info['subject']}")
            response.append(f"   **Date:** {email_info['date']}")
            response.append("")
        
        return "\n".join(response)
    
    except Exception as e:
        return f"❌ Error searching emails: {str(e)}"

# Create the Langchain tools
email_check_tool = StructuredTool.from_function(
    name="check_emails",
    description="Check recent or unread emails from your Gmail account. Use this to read your emails.",
    func=check_emails,
    args_schema=EmailCheckInput
)

email_send_tool = StructuredTool.from_function(
    name="send_email",
    description="Send an email to someone. Provide the recipient, subject, and body content.",
    func=send_email,
    args_schema=EmailSendInput
)

email_search_tool = StructuredTool.from_function(
    name="search_emails",
    description="Search through emails by sender, subject, or keywords.",
    func=search_emails,
    args_schema=EmailSearchInput
)

# Combine all email tools into one main tool
class EmailActionInput(BaseModel):
    action: str = Field(..., description="Email action: 'check', 'send', or 'search'")
    limit: int = Field(default=5, description="For check/search: number of results")
    unread_only: bool = Field(default=True, description="For check: only unread emails")
    to: str = Field(default="", description="For send: recipient email")
    subject: str = Field(default="", description="For send: email subject")
    body: str = Field(default="", description="For send: email body")
    query: str = Field(default="", description="For search: search query")

def email_tool_main(action: str, **kwargs) -> str:
    """Main email tool that handles check, send, and search actions."""
    if action == "check":
        return check_emails(kwargs.get('limit', 5), kwargs.get('unread_only', True))
    elif action == "send":
        return send_email(kwargs['to'], kwargs['subject'], kwargs['body'])
    elif action == "search":
        return search_emails(kwargs['query'], kwargs.get('limit', 10))
    else:
        return "❌ Invalid email action. Use 'check', 'send', or 'search'."

email_tool = StructuredTool.from_function(
    name="email_management",
    description="Manage emails: check unread emails, send emails, or search through your email history.",
    func=email_tool_main,
    args_schema=EmailActionInput
)