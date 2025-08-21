import chromadb
from chromadb.config import Settings
import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from .models import get_session, Conversation, User, SearchHistory, TaskHistory
import hashlib

# Suppress ChromaDB warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
logging.getLogger("chromadb").setLevel(logging.WARNING)

class MemorySystem:
    """Hybrid memory system using Chroma and SQL."""
    
    def __init__(self, user_id: int = 1):
        self.user_id = user_id
        
        # Initialize Chroma
        chroma_path = os.path.join(os.path.dirname(__file__), "chroma_db")
        os.makedirs(chroma_path, exist_ok=True)
        
        try:
            # Configure ChromaDB settings
            chroma_settings = Settings(
                allow_reset=True,
                anonymized_telemetry=False
            )
            
            self.chroma_client = chromadb.PersistentClient(
                path=chroma_path,
                settings=chroma_settings
            )
            
            # Create collections with error handling
            self.conversations_collection = self.chroma_client.get_or_create_collection(
                name="conversations",
                metadata={"hnsw:space": "cosine"}
            )
            
            self.knowledge_collection = self.chroma_client.get_or_create_collection(
                name="knowledge", 
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            logging.warning(f"ChromaDB initialization warning: {e}")
            # Create minimal fallback
            self.chroma_client = None
            self.conversations_collection = None
            self.knowledge_collection = None
    
    def store_conversation(self, session_id: str, user_message: str, assistant_response: str, tools_used: List[str] = None):
        """Store a conversation in both PostgreSQL and Chroma for vector search."""
        db_session = get_session()
        
        try:
            # Store in PostgreSQL
            conversation = Conversation(
                user_id=self.user_id,
                session_id=session_id,
                user_message=user_message,
                assistant_response=assistant_response,
                tools_used=json.dumps(tools_used) if tools_used else None
            )
            db_session.add(conversation)
            db_session.commit()
            
            # Store in Chroma for vector search
            conversation_text = f"User: {user_message}\nAssistant: {assistant_response}"
            document_id = f"conv_{conversation.id}"
            
            self.conversations_collection.add(
                documents=[conversation_text],
                metadatas=[{
                    "user_id": str(self.user_id),
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "tools_used": json.dumps(tools_used) if tools_used else "[]",
                    "conversation_id": conversation.id
                }],
                ids=[document_id]
            )
            
        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()
    
    def store_knowledge(self, content: str, source: str, category: str = "general"):
        """Store knowledge from web searches, emails, etc."""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        document_id = f"knowledge_{content_hash}"
        
        try:
            self.knowledge_collection.add(
                documents=[content],
                metadatas=[{
                    "user_id": str(self.user_id),
                    "source": source,
                    "category": category,
                    "timestamp": datetime.utcnow().isoformat()
                }],
                ids=[document_id]
            )
        except Exception as e:
            # Document might already exist, update metadata
            try:
                self.knowledge_collection.update(
                    ids=[document_id],
                    metadatas=[{
                        "user_id": str(self.user_id),
                        "source": source,
                        "category": category,
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                )
            except:
                pass  # Ignore if can't update
    
    def search_conversations(self, query: str, limit: int = 5) -> List[Dict]:
        """Search past conversations for relevant context."""
        if not self.conversations_collection:
            return []
            
        try:
            results = self.conversations_collection.query(
                query_texts=[query],
                n_results=limit,
                where={"user_id": str(self.user_id)}
            )
            
            formatted_results = []
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )):
                formatted_results.append({
                    "content": doc,
                    "timestamp": metadata.get("timestamp"),
                    "session_id": metadata.get("session_id"),
                    "tools_used": json.loads(metadata.get("tools_used", "[]")),
                    "relevance_score": 1 - distance  # Convert distance to similarity
                })
            
            return formatted_results
        except Exception as e:
            print(f"Error searching conversations: {e}")
            return []
    
    def search_knowledge(self, query: str, category: str = None, limit: int = 3) -> List[Dict]:
        """Search stored knowledge for relevant information."""
        if not self.knowledge_collection:
            return []
            
        try:
            where_clause = {"user_id": str(self.user_id)}
            if category:
                where_clause["category"] = category
            
            results = self.knowledge_collection.query(
                query_texts=[query],
                n_results=limit,
                where=where_clause
            )
            
            formatted_results = []
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )):
                formatted_results.append({
                    "content": doc,
                    "source": metadata.get("source"),
                    "category": metadata.get("category"),
                    "timestamp": metadata.get("timestamp"),
                    "relevance_score": 1 - distance
                })
            
            return formatted_results
        except Exception as e:
            print(f"Error searching knowledge: {e}")
            return []
    
    def get_recent_conversations(self, session_id: str = None, limit: int = 10) -> List[Dict]:
        """Get recent conversations from PostgreSQL."""
        db_session = get_session()
        
        try:
            query = db_session.query(Conversation).filter(
                Conversation.user_id == self.user_id
            )
            
            if session_id:
                query = query.filter(Conversation.session_id == session_id)
            
            conversations = query.order_by(
                Conversation.created_at.desc()
            ).limit(limit).all()
            
            result = []
            for conv in conversations:
                result.append({
                    "user_message": conv.user_message,
                    "assistant_response": conv.assistant_response,
                    "tools_used": json.loads(conv.tools_used) if conv.tools_used else [],
                    "timestamp": conv.created_at.isoformat(),
                    "session_id": conv.session_id
                })
            
            return result
        except Exception as e:
            print(f"Error getting recent conversations: {e}")
            return []
        finally:
            db_session.close()
    
    def store_search_history(self, query: str, results_summary: str):
        """Store web search history."""
        db_session = get_session()
        
        try:
            search_record = SearchHistory(
                user_id=self.user_id,
                query=query,
                results_summary=results_summary
            )
            db_session.add(search_record)
            db_session.commit()
            
            # Also store in knowledge base
            self.store_knowledge(
                content=f"Search query: {query}\n\nResults: {results_summary}",
                source="web_search",
                category="search"
            )
        except Exception as e:
            db_session.rollback()
            print(f"Error storing search history: {e}")
        finally:
            db_session.close()
    
    def store_task_history(self, task_type: str, command: str, result: str, success: bool):
        """Store task execution history."""
        db_session = get_session()
        
        try:
            task_record = TaskHistory(
                user_id=self.user_id,
                task_type=task_type,
                command=command,
                result=result,
                success=success
            )
            db_session.add(task_record)
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            print(f"Error storing task history: {e}")
        finally:
            db_session.close()
    
    def get_context_for_query(self, query: str) -> str:
        """Get relevant context from memory for a query."""
        context_parts = []
        
        # Search conversations
        conv_results = self.search_conversations(query, limit=3)
        if conv_results:
            context_parts.append("## Relevant Past Conversations:")
            for result in conv_results:
                if result["relevance_score"] > 0.7:  # Only include highly relevant results
                    context_parts.append(f"- {result['content'][:200]}...")
        
        # Search knowledge
        knowledge_results = self.search_knowledge(query, limit=2)
        if knowledge_results:
            context_parts.append("## Relevant Knowledge:")
            for result in knowledge_results:
                if result["relevance_score"] > 0.7:
                    context_parts.append(f"- From {result['source']}: {result['content'][:200]}...")
        
        return "\n".join(context_parts) if context_parts else ""

# Global memory instance
memory_system = MemorySystem()