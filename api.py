#!/usr/bin/env python3
"""
FastAPI backend for Jarvis - Optional REST API interface.
This provides HTTP endpoints for web/mobile clients to interact with Jarvis.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import sys
from datetime import datetime
import uuid
import asyncio
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.models import get_session, User, Conversation
from db.memory import MemorySystem
from tools.weather import get_current_weather
from tools.web_search import enhanced_web_search
from tools.email import check_emails, send_email, search_emails
from tools.calendar import check_calendar_events, create_calendar_event, search_calendar_events
from tools.terminal import run_terminal_command
from tools.app_launcher import launch_application

# Initialize FastAPI app
app = FastAPI(
    title="Jarvis API",
    description="REST API for Jarvis AI Assistant",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load environment variables
load_dotenv()

# Initialize memory system
memory_system = MemorySystem(user_id=1)

# Pydantic models for API requests/responses
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: datetime
    tools_used: List[str] = []

class ToolRequest(BaseModel):
    tool: str
    parameters: Dict[str, Any]

class MemorySearchRequest(BaseModel):
    query: str
    limit: int = 5
    search_type: str = "both"  # conversations, knowledge, both

class MemoryResponse(BaseModel):
    results: List[Dict[str, Any]]
    total_found: int

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Jarvis AI Assistant API",
        "version": "1.0.0",
        "endpoints": [
            "/chat - Chat with Jarvis",
            "/tools - Execute specific tools",
            "/memory/search - Search conversation history",
            "/health - Health check"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        session = get_session()
        session.query(User).first()
        session.close()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(),
            "database": "connected",
            "memory": "initialized"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(),
            "error": str(e)
        }

@app.post("/chat", response_model=ChatResponse)
async def chat_with_jarvis(request: ChatRequest):
    """
    Chat with Jarvis AI assistant.
    This is a simplified version - for full agent capabilities, use the voice interface.
    """
    try:
        session_id = request.session_id or str(uuid.uuid4())
        
        # Get context from memory
        context = memory_system.get_context_for_query(request.message)
        
        # For API simplicity, we'll route to specific tools based on message content
        # In the full voice interface, the LLM agent handles this routing
        response_text = ""
        tools_used = []
        
        message_lower = request.message.lower()
        
        if "weather" in message_lower:
            # Extract city from message or use default
            import re
            city_match = re.search(r'weather (?:in |for )?([\w\s]+)', message_lower)
            city = city_match.group(1).strip() if city_match else "New York"
            
            response_text = get_current_weather(city)
            tools_used.append("weather")
        
        elif "email" in message_lower:
            if "check" in message_lower or "read" in message_lower:
                response_text = check_emails()
                tools_used.append("email_check")
            else:
                response_text = "Email functionality available. Try: 'check my emails'"
        
        elif "calendar" in message_lower:
            response_text = check_calendar_events()
            tools_used.append("calendar")
        
        elif "search" in message_lower or "look up" in message_lower:
            # Extract search query
            query = request.message.replace("search for", "").replace("search", "").replace("look up", "").strip()
            if query:
                response_text = enhanced_web_search(query)
                tools_used.append("web_search")
            else:
                response_text = "What would you like me to search for?"
        
        elif "remember" in message_lower or "recall" in message_lower:
            # Memory search
            query = request.message.replace("remember", "").replace("recall", "").strip()
            if query:
                conv_results = memory_system.search_conversations(query, limit=3)
                if conv_results:
                    response_text = f"I found these relevant memories:\n\n"
                    for i, result in enumerate(conv_results, 1):
                        response_text += f"{i}. {result['content'][:200]}...\n"
                else:
                    response_text = f"I don't have any memories about '{query}'"
                tools_used.append("memory_search")
            else:
                response_text = "What would you like me to remember or recall?"
        
        else:
            # General response
            response_text = f"I received your message: '{request.message}'. For full AI capabilities, please use the voice interface with 'python main.py'."
        
        # Store conversation in memory
        memory_system.store_conversation(
            session_id=session_id,
            user_message=request.message,
            assistant_response=response_text,
            tools_used=tools_used
        )
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            timestamp=datetime.now(),
            tools_used=tools_used
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")

@app.post("/tools")
async def execute_tool(request: ToolRequest):
    """Execute a specific tool with parameters."""
    try:
        tool = request.tool.lower()
        params = request.parameters
        
        if tool == "weather":
            result = get_current_weather(params.get("city", "New York"))
        
        elif tool == "web_search":
            result = enhanced_web_search(params.get("query", ""), params.get("num_results", 3))
        
        elif tool == "email_check":
            result = check_emails(params.get("limit", 5), params.get("unread_only", True))
        
        elif tool == "calendar_check":
            result = check_calendar_events(params.get("days_ahead", 7))
        
        elif tool == "terminal":
            command = params.get("command", "")
            if command:
                result = run_terminal_command(command)
            else:
                result = "No command provided"
        
        elif tool == "app_launch":
            app_name = params.get("app_name", "")
            if app_name:
                result = launch_application(app_name)
            else:
                result = "No app name provided"
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {tool}")
        
        return {
            "tool": tool,
            "result": result,
            "timestamp": datetime.now(),
            "parameters": params
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing tool: {str(e)}")

@app.post("/memory/search", response_model=MemoryResponse)
async def search_memory(request: MemorySearchRequest):
    """Search through conversation history and stored knowledge."""
    try:
        results = []
        
        if request.search_type in ["conversations", "both"]:
            conv_results = memory_system.search_conversations(request.query, limit=request.limit)
            results.extend([{
                "type": "conversation",
                "content": r["content"],
                "timestamp": r.get("timestamp"),
                "relevance_score": r.get("relevance_score"),
                "session_id": r.get("session_id")
            } for r in conv_results])
        
        if request.search_type in ["knowledge", "both"]:
            knowledge_results = memory_system.search_knowledge(request.query, limit=request.limit)
            results.extend([{
                "type": "knowledge",
                "content": r["content"],
                "source": r.get("source"),
                "category": r.get("category"),
                "timestamp": r.get("timestamp"),
                "relevance_score": r.get("relevance_score")
            } for r in knowledge_results])
        
        # Sort by relevance score
        results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return MemoryResponse(
            results=results[:request.limit],
            total_found=len(results)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching memory: {str(e)}")

@app.get("/conversations/{session_id}")
async def get_conversation_history(session_id: str, limit: int = 50):
    """Get conversation history for a specific session."""
    try:
        conversations = memory_system.get_recent_conversations(session_id=session_id, limit=limit)
        
        return {
            "session_id": session_id,
            "conversations": conversations,
            "count": len(conversations)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation history: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "127.0.0.1")
    
    print(f"🚀 Starting Jarvis API server on {host}:{port}")
    print("📖 API docs available at: http://localhost:8000/docs")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=True
    )