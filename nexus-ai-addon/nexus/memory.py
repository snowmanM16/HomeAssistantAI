"""
Memory manager for Nexus AI
"""
import os
import logging
import json
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("nexus.memory")

class MemoryManager:
    """Manages storage and retrieval of memory with vector search capabilities."""
    
    def __init__(self, db_service, embedding_path: str = None):
        """Initialize the memory manager with SQLite and ChromaDB."""
        self.db_service = db_service
        
        # Default embedding path is in the data directory
        if not embedding_path:
            data_dir = os.environ.get("DATA_DIR", "/data/nexus")
            embedding_path = os.path.join(data_dir, "embeddings")
        
        # Initialize ChromaDB for vector storage
        self.embeddings_available = False
        try:
            self._init_chromadb(embedding_path)
            self.embeddings_available = True
        except Exception as e:
            logger.warning(f"ChromaDB initialization failed: {e}. Vector search will be disabled.")
    
    def _init_chromadb(self, path: str = None):
        """Initialize ChromaDB for vector embeddings."""
        try:
            import chromadb
            from chromadb.config import Settings
            
            # Create directory if it doesn't exist
            if path:
                os.makedirs(path, exist_ok=True)
            
            # Initialize the client
            self.chroma_client = chromadb.PersistentClient(
                path=path, 
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Create or get the collection
            self.collection = self.chroma_client.get_or_create_collection(
                name="memories",
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info(f"ChromaDB initialized at {path}")
        except ImportError:
            logger.warning("ChromaDB not installed. Vector search will be disabled.")
            raise
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {e}")
            raise
    
    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding vector for text."""
        if not self.embeddings_available:
            return None
            
        try:
            import openai
            
            response = openai.embeddings.create(
                model="text-embedding-3-large",
                input=text,
                dimensions=1024
            )
            return response.data[0].embedding
        except ImportError:
            logger.warning("OpenAI module not available for embeddings")
            return None
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    def save_memory(self, key: str, value: str, is_preference: bool = False) -> bool:
        """Save a memory item to both SQLite and ChromaDB."""
        # Generate embedding for vector search
        embedding_id = None
        if self.embeddings_available:
            try:
                embedding = self._generate_embedding(value)
                if embedding:
                    # Store in ChromaDB
                    self.collection.upsert(
                        ids=[key],
                        embeddings=[embedding],
                        metadatas=[{"key": key, "is_preference": is_preference}],
                        documents=[value]
                    )
                    embedding_id = key
                    logger.debug(f"Stored embedding for memory: {key}")
            except Exception as e:
                logger.error(f"Error storing embedding: {e}")
        
        # Store in SQLite database
        return self.db_service.save_memory(key, value, embedding_id, is_preference)
    
    def recall(self, key: str) -> Optional[str]:
        """Recall a specific memory by key."""
        memory = self.db_service.get_memory(key)
        return memory.get("value") if memory else None
    
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for memories semantically similar to the query."""
        if not self.embeddings_available:
            logger.warning("Vector search not available")
            # Fallback to basic keyword search in SQLite
            memories = self.db_service.get_all_memories()
            results = []
            
            # Simple string matching
            query_lower = query.lower()
            for memory in memories:
                if query_lower in memory.get("key", "").lower() or query_lower in memory.get("value", "").lower():
                    results.append({
                        "key": memory.get("key"),
                        "value": memory.get("value"),
                        "score": 0.5  # Default score for text matching
                    })
            
            # Sort by simple relevance and limit
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:limit]
        
        try:
            # Generate embedding for the query
            query_embedding = self._generate_embedding(query)
            if not query_embedding:
                logger.warning("Could not generate embedding for query")
                return []
            
            # Search ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit
            )
            
            # Format results
            formatted_results = []
            for i, (doc_id, document, metadata, distance) in enumerate(zip(
                results.get("ids", [[]])[0],
                results.get("documents", [[]])[0],
                results.get("metadatas", [[]])[0],
                results.get("distances", [[]])[0]
            )):
                score = 1.0 - distance  # Convert distance to similarity score
                formatted_results.append({
                    "key": metadata.get("key", doc_id),
                    "value": document,
                    "score": score,
                    "is_preference": metadata.get("is_preference", False)
                })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            return []
    
    def save_preference(self, name: str, value: str) -> bool:
        """Save a user preference."""
        key = f"preference:{name}"
        return self.save_memory(key, value, is_preference=True)
    
    def get_preference(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get a user preference."""
        key = f"preference:{name}"
        value = self.recall(key)
        return value if value is not None else default
    
    def get_all_preferences(self) -> Dict[str, str]:
        """Get all user preferences."""
        preferences = {}
        memories = self.db_service.get_all_memories(preferences_only=True)
        
        for memory in memories:
            key = memory.get("key", "")
            if key.startswith("preference:"):
                name = key[11:]  # Remove the "preference:" prefix
                preferences[name] = memory.get("value")
        
        return preferences
    
    def track_entity(self, entity_id: str, state: str, attributes: Dict[str, Any], important: bool = False) -> bool:
        """Track a Home Assistant entity state change for pattern detection."""
        # Extract domain
        domain = entity_id.split('.')[0] if '.' in entity_id else ""
        
        # Extract friendly name
        friendly_name = attributes.get("friendly_name", entity_id)
        
        # Save to database
        return self.db_service.save_entity(
            entity_id=entity_id,
            friendly_name=friendly_name,
            domain=domain,
            state=state,
            attributes=attributes,
            is_important=important
        )
    
    def get_important_entities(self) -> List[Dict[str, Any]]:
        """Get all important entities and their states."""
        return self.db_service.get_entities(important_only=True)
    
    def clear_all(self) -> bool:
        """Clear all memory data (for testing/reset purposes)."""
        # Clear ChromaDB
        if self.embeddings_available:
            try:
                self.collection.delete()
                logger.info("Cleared ChromaDB collection")
            except Exception as e:
                logger.error(f"Error clearing ChromaDB: {e}")
                return False
        
        # Clear database memories
        # Note: This would require implementing this method in the database service
        # return self.db_service.clear_memories()
        
        # For now, we'll just log that we can't do this
        logger.warning("Database memory clearing not implemented")
        return False
