#!/usr/bin/env python3
"""
Database initialization script for Jarvis.
Run this script to set up the database and create initial user data.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.models import create_engine_and_tables, get_session, User
from db.memory import MemorySystem

def init_database():
    """Initialize the database with tables and default data."""
    load_dotenv()
    
    print("🚀 Initializing Jarvis database...")
    
    try:
        # Create database engine and tables
        engine = create_engine_and_tables()
        print("✅ Database tables created successfully")
        
        # Create default user if it doesn't exist
        session = get_session()
        try:
            existing_user = session.query(User).filter_by(id=1).first()
            
            if not existing_user:
                default_user = User(
                    id=1,
                    name=os.getenv('USER_NAME', 'User'),
                    email=os.getenv('EMAIL_ADDRESS', 'user@example.com'),
                    preferred_location=os.getenv('DEFAULT_LOCATION', 'New York, NY'),
                    timezone=os.getenv('TIMEZONE', 'America/New_York')
                )
                session.add(default_user)
                session.commit()
                print(f"✅ Created default user: {default_user.name}")
            else:
                print(f"✅ Default user already exists: {existing_user.name}")
        
        finally:
            session.close()
        
        # Initialize Chroma vector database
        print("🧠 Initializing vector memory system...")
        memory_system = MemorySystem(user_id=1)
        
        # Store initial knowledge
        initial_knowledge = [
            {
                "content": "Jarvis is a voice-activated AI assistant with capabilities for weather, email, calendar, terminal commands, web search, and memory recall.",
                "source": "system_init",
                "category": "system"
            },
            {
                "content": "User preferences: Wake word is 'Jarvis', shutdown phrase is 'Jarvis shut down'",
                "source": "system_init", 
                "category": "preferences"
            }
        ]
        
        for knowledge in initial_knowledge:
            memory_system.store_knowledge(
                content=knowledge["content"],
                source=knowledge["source"],
                category=knowledge["category"]
            )
        
        print("✅ Vector memory system initialized")
        
        # Create directories for logs and temp files
        os.makedirs("logs", exist_ok=True)
        os.makedirs("temp", exist_ok=True)
        
        print("📁 Created necessary directories")
        
        print("""
🎉 Jarvis database initialization complete!

Next steps:
1. Update your .env file with necessary API keys:
   - WEATHER_API_KEY (from weatherapi.com)
   - EMAIL_ADDRESS and EMAIL_PASSWORD (Gmail app password)
   - SERPAPI_API_KEY (optional, for enhanced web search)
   - DATABASE_URL (optional, defaults to SQLite)

2. Install required dependencies:
   pip install -r requirements.txt

3. Make sure Ollama is running with llama3.2 model:
   ollama pull llama3.2
   ollama serve

4. Run Jarvis:
   python main.py

🎤 Say "Jarvis" to wake up the assistant!
""")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_database()