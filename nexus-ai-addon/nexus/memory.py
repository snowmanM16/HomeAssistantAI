"""
Memory manager for Nexus AI
"""
import os
import logging
from typing import Dict, List, Any, Optional
import json
from datetime import datetime
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

class MemoryManager:
    """Manages storage and retrieval of memory with vector search capabilities."""
    
    def __init__(self, db_service, embedding_path: str = None):
        """Initialize the memory manager with SQLite and ChromaDB."""
        self.db = db_service
        
        # Initialize ChromaDB
        self._init_chromadb(embedding_path)
    
    def _init_chromadb(self, path: str = None):
        """Initialize ChromaDB for vector embeddings."""
        if not path:
            path = os.environ.get("DATA_DIR", ".") + "/chromadb"
        
        try:
            os.makedirs(path, exist_ok=True)
            
            self.chroma_client = chromadb.PersistentClient(
                path=path, 
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Create or get collection for memories
            self.memory_collection = self.chroma_client.get_or_create_collection(
                name="memories",
                metadata={"description": "User memories and preferences"}
            )
            
            logger.info(f"ChromaDB initialized at {path}")
        
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {e}")
            # Fallback to dummy implementation if ChromaDB fails
            self.chroma_client = None
            self.memory_collection = None
    
    def save_memory(self, key: str, value: str) -> bool:
        """Save a memory item to both SQLite and ChromaDB."""
        try:
            # First save to database
            embedding_id = None
            
            # Then save to vector store if available
            if self.memory_collection:
                # Use key as the unique ID
                embedding_id = key
                
                # Upsert to ChromaDB
                self.memory_collection.upsert(
                    ids=[embedding_id],
                    documents=[value],
                    metadatas=[{"key": key, "timestamp": datetime.utcnow().isoformat()}]
                )
            
            # Save to database with embedding ID reference
            success = self.db.save_memory(key, value, embedding_id)
            return success
        
        except Exception as e:
            logger.error(f"Error saving memory {key}: {e}")
            return False
    
    def recall(self, key: str) -> Optional[str]:
        """Recall a specific memory by key."""
        memory = self.db.get_memory(key)
        return memory["value"] if memory else None
    
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for memories semantically similar to the query."""
        results = []
        
        if not self.memory_collection:
            logger.warning("ChromaDB not available for semantic search")
            # Fallback to basic keyword search in database
            # TODO: Implement basic search
            return results
        
        try:
            # Query the vector store
            chroma_results = self.memory_collection.query(
                query_texts=[query],
                n_results=limit
            )
            
            # Process results
            if chroma_results and "metadatas" in chroma_results and chroma_results["metadatas"]:
                for i, metadata in enumerate(chroma_results["metadatas"][0]):
                    if metadata and "key" in metadata:
                        key = metadata["key"]
                        memory = self.db.get_memory(key)
                        if memory:
                            memory["relevance"] = float(chroma_results["distances"][0][i]) if "distances" in chroma_results else 0.0
                            results.append(memory)
            
            return results
        
        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            return []
    
    def save_preference(self, name: str, value: str) -> bool:
        """Save a user preference."""
        return self.db.save_memory(f"preference:{name}", value, is_preference=True)
    
    def get_preference(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get a user preference."""
        memory = self.db.get_memory(f"preference:{name}")
        return memory["value"] if memory else default
    
    def get_all_preferences(self) -> Dict[str, str]:
        """Get all user preferences."""
        preferences = {}
        memories = self.db.get_all_memories(preferences_only=True)
        
        for memory in memories:
            if memory["key"].startswith("preference:"):
                name = memory["key"].replace("preference:", "", 1)
                preferences[name] = memory["value"]
        
        return preferences
    
    def track_entity(self, entity_id: str, state: str, important: bool = False) -> bool:
        """Track a Home Assistant entity state change."""
        # Save as a memory with timestamp
        timestamp = datetime.utcnow().isoformat()
        return self.save_memory(
            f"entity_state:{entity_id}:{timestamp}", 
            json.dumps({"entity_id": entity_id, "state": state, "timestamp": timestamp})
        )
    
    def get_important_entities(self) -> List[Dict[str, Any]]:
        """Get all important entities and their states."""
        return self.db.get_entities(important_only=True)
    
    def clear_all(self) -> bool:
        """Clear all memory data (for testing/reset purposes)."""
        try:
            # Clear ChromaDB
            if self.chroma_client:
                self.chroma_client.delete_collection("memories")
                self._init_chromadb()
            
            # TODO: Clear database memories
            
            return True
        except Exception as e:
            logger.error(f"Error clearing memories: {e}")
            return False
