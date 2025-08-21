from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class User(Base):
    """User profile and preferences."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True)
    preferred_location = Column(String(100))  # For weather queries
    timezone = Column(String(50), default='America/New_York')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="user")
    calendar_events = relationship("CalendarEvent", back_populates="user")
    email_summaries = relationship("EmailSummary", back_populates="user")

class Conversation(Base):
    """Store conversation history for context."""
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    session_id = Column(String(100), nullable=False)  # To group related messages
    user_message = Column(Text, nullable=False)
    assistant_response = Column(Text, nullable=False)
    tools_used = Column(Text)  # JSON string of tools used
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="conversations")

class CalendarEvent(Base):
    """Cache calendar events locally."""
    __tablename__ = 'calendar_events'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    external_id = Column(String(255))  # Google Calendar event ID
    title = Column(String(255), nullable=False)
    description = Column(Text)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    location = Column(String(255))
    attendees = Column(Text)  # JSON string of attendees
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="calendar_events")

class EmailSummary(Base):
    """Cache email summaries and important information."""
    __tablename__ = 'email_summaries'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    message_id = Column(String(255), unique=True)  # Gmail message ID
    sender = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    summary = Column(Text)
    importance_score = Column(Integer, default=1)  # 1-5 scale
    is_read = Column(Boolean, default=False)
    received_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="email_summaries")

class SearchHistory(Base):
    """Track web searches for learning user interests."""
    __tablename__ = 'search_history'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    query = Column(Text, nullable=False)
    results_summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class TaskHistory(Base):
    """Track completed tasks and commands."""
    __tablename__ = 'task_history'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    task_type = Column(String(50), nullable=False)  # 'terminal', 'app_launch', etc.
    command = Column(Text, nullable=False)
    result = Column(Text)
    success = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Database connection
def get_database_url():
    """Get database URL from environment or use SQLite fallback."""
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        return db_url
    else:
        # Fallback to SQLite for local development
        db_path = os.path.join(os.path.dirname(__file__), 'jarvis.db')
        return f'sqlite:///{db_path}'

def create_engine_and_tables():
    """Create database engine and tables."""
    engine = create_engine(get_database_url())
    Base.metadata.create_all(engine)
    return engine

def get_session():
    """Get database session."""
    engine = create_engine_and_tables()
    Session = sessionmaker(bind=engine)
    return Session()