"""
Memory management module for Nexus AI
"""
import os
import logging
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemoryManager:
    """
    Memory manager for Nexus AI.
    Handles both factual memories and semantic embeddings for retrieval.
    """
    
    def __init__(self, database_service):
        """Initialize the memory manager with database service."""
        self.db = database_service
        self.embedding_store = None
        self.initialize_embedding_store()
    
    def initialize_embedding_store(self):
        """Initialize the embedding store for semantic search."""
        try:
            import chromadb
            from chromadb.config import Settings
            
            # Get data directory from environment or use default
            data_dir = os.environ.get("DATA_DIR", "/data/nexus")
            
            # Create directory if it doesn't exist
            os.makedirs(f"{data_dir}/embeddings", exist_ok=True)
            
            # Initialize ChromaDB client
            self.embedding_store = chromadb.Client(
                Settings(
                    persist_directory=f"{data_dir}/embeddings",
                    anonymized_telemetry=False
                )
            )
            
            # Get or create collection
            self.collection = self.embedding_store.get_or_create_collection("memories")
            
            logger.info("Embedding store initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize embedding store: {str(e)}")
            logger.warning("Semantic search will not be available")
    
    def save(self, key: str, value: str, is_preference: bool = False) -> bool:
        """
        Save a memory item with optional embedding for semantic search.
        
        Args:
            key: Unique identifier for the memory
            value: Content of the memory
            is_preference: Whether this memory represents a user preference
            
        Returns:
            bool: Success status
        """
        try:
            # Store in database
            result = self.db.save_memory(key, value, is_preference=is_preference)
            
            # Add to vector store if available
            if self.embedding_store and result:
                try:
                    # Generate embedding using OpenAI
                    embedding_id = self._generate_embedding(key, value)
                    
                    # Update memory with embedding ID
                    if embedding_id:
                        self.db.save_memory(key, value, embedding_id=embedding_id, is_preference=is_preference)
                        
                except Exception as e:
                    logger.warning(f"Failed to generate embedding: {str(e)}")
            
            return result
        except Exception as e:
            logger.error(f"Error saving memory: {str(e)}")
            return False
    
    def _generate_embedding(self, key: str, value: str) -> Optional[str]:
        """
        Generate embedding for a memory item.
        
        Args:
            key: Memory key
            value: Memory content
            
        Returns:
            str: Embedding ID or None if failed
        """
        try:
            import openai
            
            # Check if OpenAI API key is available
            if not os.environ.get("OPENAI_API_KEY"):
                logger.warning("OpenAI API key not found, skipping embedding generation")
                return None
            
            # Generate embedding
            client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            embedding_response = client.embeddings.create(
                model="text-embedding-ada-002",
                input=value
            )
            
            if not embedding_response.data:
                logger.warning("No embedding data received from OpenAI")
                return None
                
            embedding = embedding_response.data[0].embedding
            
            # Store in ChromaDB
            embedding_id = f"mem_{int(time.time())}"
            
            self.collection.add(
                ids=[embedding_id],
                embeddings=[embedding],
                metadatas=[{"key": key, "created_at": datetime.utcnow().isoformat()}],
                documents=[value]
            )
            
            return embedding_id
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            return None
    
    def recall(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Recall a specific memory by key.
        
        Args:
            key: Memory key to retrieve
            
        Returns:
            dict: Memory data or None if not found
        """
        return self.db.get_memory(key)
    
    def semantic_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for memories semantically related to the query.
        
        Args:
            query: Natural language query
            limit: Maximum number of results
            
        Returns:
            list: Matching memories sorted by relevance
        """
        if not self.embedding_store:
            logger.warning("Semantic search not available - embedding store not initialized")
            return []
        
        try:
            # Generate query embedding
            import openai
            
            # Check if OpenAI API key is available
            if not os.environ.get("OPENAI_API_KEY"):
                logger.warning("OpenAI API key not found, skipping semantic search")
                return []
            
            # Generate embedding for query
            client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            embedding_response = client.embeddings.create(
                model="text-embedding-ada-002",
                input=query
            )
            
            if not embedding_response.data:
                logger.warning("No embedding data received from OpenAI")
                return []
                
            query_embedding = embedding_response.data[0].embedding
            
            # Query the collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit
            )
            
            # Process results
            memories = []
            if results["ids"]:
                for i, doc_id in enumerate(results["ids"][0]):
                    key = results["metadatas"][0][i]["key"]
                    memory = self.db.get_memory(key)
                    if memory:
                        # Add distance score
                        memory["relevance"] = 1.0 - results["distances"][0][i] if "distances" in results else 1.0
                        memories.append(memory)
            
            return memories
        except Exception as e:
            logger.error(f"Error performing semantic search: {str(e)}")
            return []
    
    def get_all(self, preferences_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get all memories with optional filtering.
        
        Args:
            preferences_only: Whether to return only preference memories
            
        Returns:
            list: All matching memories
        """
        return self.db.get_all_memories(preferences_only)
    
    def delete(self, key: str) -> bool:
        """
        Delete a memory by key.
        
        Args:
            key: Memory key to delete
            
        Returns:
            bool: Success status
        """
        memory = self.db.get_memory(key)
        if not memory:
            return False
        
        # Delete from embedding store if it has an embedding
        if memory.get("embedding_id") and self.embedding_store:
            try:
                self.collection.delete(ids=[memory["embedding_id"]])
            except Exception as e:
                logger.warning(f"Failed to delete embedding: {str(e)}")
        
        # Delete from database
        return self.db.delete_memory(key)