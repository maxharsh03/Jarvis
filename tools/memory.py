from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from db.memory import memory_system
from typing import List, Dict

class MemorySearchInput(BaseModel):
    query: str = Field(..., description="What to search for in memory (past conversations, knowledge)")
    search_type: str = Field(default="both", description="Search type: 'conversations', 'knowledge', or 'both'")

def smart_memory_lookup(query: str, search_type: str = "both") -> str:
    """Search through past conversations and stored knowledge for relevant information."""
    try:
        results = []
        
        if search_type in ["conversations", "both"]:
            # Search past conversations
            conv_results = memory_system.search_conversations(query, limit=3)
            if conv_results:
                results.append("🧠 **Relevant Past Conversations:**")
                for i, result in enumerate(conv_results, 1):
                    if result["relevance_score"] > 0.6:  # Only include reasonably relevant results
                        timestamp = result.get("timestamp", "Unknown time")
                        tools = result.get("tools_used", [])
                        tools_str = f" (used: {', '.join(tools)})" if tools else ""
                        
                        results.append(f"{i}. From {timestamp[:10]}{tools_str}:")
                        results.append(f"   {result['content'][:300]}...")
                        results.append("")
        
        if search_type in ["knowledge", "both"]:
            # Search stored knowledge
            knowledge_results = memory_system.search_knowledge(query, limit=3)
            if knowledge_results:
                results.append("📚 **Relevant Knowledge:**")
                for i, result in enumerate(knowledge_results, 1):
                    if result["relevance_score"] > 0.6:
                        source = result.get("source", "Unknown source")
                        category = result.get("category", "general")
                        
                        results.append(f"{i}. From {source} ({category}):")
                        results.append(f"   {result['content'][:300]}...")
                        results.append("")
        
        if results:
            return "\n".join(results)
        else:
            return f"🤔 No relevant information found in memory for '{query}'. This might be a new topic."
    
    except Exception as e:
        return f"❌ Error searching memory: {str(e)}"

def get_recent_context(limit: int = 5) -> str:
    """Get recent conversation context for continuity."""
    try:
        recent_convs = memory_system.get_recent_conversations(limit=limit)
        
        if not recent_convs:
            return "No recent conversation history."
        
        context_parts = ["📝 **Recent Conversation Context:**"]
        
        for conv in recent_convs[-3:]:  # Last 3 conversations for context
            timestamp = conv.get("timestamp", "")[:16]  # YYYY-MM-DDTHH:MM
            context_parts.append(f"[{timestamp}] User: {conv['user_message'][:100]}...")
            context_parts.append(f"[{timestamp}] Jarvis: {conv['assistant_response'][:100]}...")
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    except Exception as e:
        return f"❌ Error getting recent context: {str(e)}"

class RecentContextInput(BaseModel):
    limit: int = Field(default=5, description="Number of recent conversations to retrieve")

# Create the Langchain tools
smart_lookup_tool = StructuredTool.from_function(
    name="search_memory",
    description="Search through past conversations and stored knowledge for relevant information. Always use this before web search to check if you already know something.",
    func=smart_memory_lookup,
    args_schema=MemorySearchInput
)

recent_context_tool = StructuredTool.from_function(
    name="get_recent_context",
    description="Get recent conversation history for context and continuity.",
    func=get_recent_context,
    args_schema=RecentContextInput
)