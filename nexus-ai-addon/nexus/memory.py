import os
import sqlite3
import json
import logging
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import datetime

logger = logging.getLogger("nexus.memory")

class MemoryManager:
    """Manages storage and retrieval of memory with vector search capabilities."""
    
    def __init__(self, db_path: str, chroma_path: str):
        """Initialize the memory manager with SQLite and ChromaDB."""
        self.db_path = db_path
        self.chroma_path = chroma_path
        
        # Ensure directories exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        os.makedirs(chroma_path, exist_ok=True)
        
        # Initialize SQLite
        self._init_sqlite()
        
        # Initialize ChromaDB
        self._init_chromadb()
    
    def _init_sqlite(self):
        """Initialize the SQLite database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create memory table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memory (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    timestamp TEXT
                )
            ''')
            
            # Create preferences table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS preferences (
                    name TEXT PRIMARY KEY,
                    value TEXT,
                    timestamp TEXT
                )
            ''')
            
            # Create entities table for tracking Home Assistant entities of interest
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS entities (
                    entity_id TEXT PRIMARY KEY,
                    last_state TEXT,
                    last_changed TEXT,
                    important INTEGER
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("SQLite database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SQLite database: {e}")
    
    def _init_chromadb(self):
        """Initialize ChromaDB for vector embeddings."""
        try:
            self.chroma_client = chromadb.Client(Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=self.chroma_path
            ))
            
            # Create a collection for memory
            self.memory_collection = self.chroma_client.get_or_create_collection(
                name="memory",
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info("ChromaDB initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.chroma_client = None
            self.memory_collection = None
    
    def save_memory(self, key: str, value: str) -> bool:
        """Save a memory item to both SQLite and ChromaDB."""
        timestamp = datetime.datetime.now().isoformat()
        
        try:
            # Save to SQLite
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO memory (key, value, timestamp) VALUES (?, ?, ?)",
                (key, value, timestamp)
            )
            conn.commit()
            conn.close()
            
            # Save to ChromaDB for vector search
            if self.memory_collection:
                try:
                    # Check if document already exists
                    existing = self.memory_collection.get(ids=[key])
                    
                    if existing and existing['ids'] and key in existing['ids']:
                        # Update existing document
                        self.memory_collection.update(
                            ids=[key],
                            documents=[value],
                            metadatas=[{"timestamp": timestamp}]
                        )
                    else:
                        # Add new document
                        self.memory_collection.add(
                            ids=[key],
                            documents=[value],
                            metadatas=[{"timestamp": timestamp}]
                        )
                except Exception as e:
                    logger.error(f"Failed to save to ChromaDB: {e}")
            
            logger.debug(f"Saved memory: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
            return False
    
    def recall(self, key: str) -> Optional[str]:
        """Recall a specific memory by key."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM memory WHERE key = ?", (key,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0]
            return None
        except Exception as e:
            logger.error(f"Failed to recall memory: {e}")
            return None
    
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for memories semantically similar to the query."""
        results = []
        
        # Try vector search first
        if self.memory_collection:
            try:
                vector_results = self.memory_collection.query(
                    query_texts=[query],
                    n_results=limit
                )
                
                if vector_results and vector_results['documents'] and vector_results['documents'][0]:
                    for i, doc in enumerate(vector_results['documents'][0]):
                        results.append({
                            "key": vector_results['ids'][0][i],
                            "value": doc,
                            "score": vector_results.get('distances', [[]])[0][i] if vector_results.get('distances') else None
                        })
            except Exception as e:
                logger.error(f"Vector search failed: {e}")
        
        # Fall back to simple text search if vector search failed or returned no results
        if not results:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Split query into words for simple search
                words = query.strip().lower().split()
                if not words:
                    return []
                
                # Build SQL query with multiple LIKE conditions
                sql_conditions = " OR ".join([f"LOWER(value) LIKE ?" for _ in words])
                sql_params = [f"%{word}%" for word in words]
                
                cursor.execute(
                    f"SELECT key, value FROM memory WHERE {sql_conditions} ORDER BY timestamp DESC LIMIT ?",
                    sql_params + [limit]
                )
                
                for key, value in cursor.fetchall():
                    results.append({
                        "key": key,
                        "value": value,
                        "score": None  # No score for text search
                    })
                
                conn.close()
            except Exception as e:
                logger.error(f"Text search failed: {e}")
        
        return results
    
    def save_preference(self, name: str, value: str) -> bool:
        """Save a user preference."""
        timestamp = datetime.datetime.now().isoformat()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO preferences (name, value, timestamp) VALUES (?, ?, ?)",
                (name, value, timestamp)
            )
            conn.commit()
            conn.close()
            
            logger.debug(f"Saved preference: {name} = {value}")
            return True
        except Exception as e:
            logger.error(f"Failed to save preference: {e}")
            return False
    
    def get_preference(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get a user preference."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM preferences WHERE name = ?", (name,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0]
            return default
        except Exception as e:
            logger.error(f"Failed to get preference: {e}")
            return default
    
    def get_all_preferences(self) -> Dict[str, str]:
        """Get all user preferences."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name, value FROM preferences")
            results = cursor.fetchall()
            conn.close()
            
            return {name: value for name, value in results}
        except Exception as e:
            logger.error(f"Failed to get all preferences: {e}")
            return {}
    
    def track_entity(self, entity_id: str, state: str, important: bool = False) -> bool:
        """Track a Home Assistant entity state change."""
        timestamp = datetime.datetime.now().isoformat()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO entities (entity_id, last_state, last_changed, important) VALUES (?, ?, ?, ?)",
                (entity_id, state, timestamp, 1 if important else 0)
            )
            conn.commit()
            conn.close()
            
            logger.debug(f"Tracked entity: {entity_id} = {state}")
            return True
        except Exception as e:
            logger.error(f"Failed to track entity: {e}")
            return False
    
    def get_important_entities(self) -> List[Dict[str, Any]]:
        """Get all important entities and their states."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT entity_id, last_state, last_changed FROM entities WHERE important = 1"
            )
            results = cursor.fetchall()
            conn.close()
            
            return [
                {
                    "entity_id": entity_id,
                    "state": state,
                    "last_changed": last_changed
                }
                for entity_id, state, last_changed in results
            ]
        except Exception as e:
            logger.error(f"Failed to get important entities: {e}")
            return []
    
    def clear_all(self) -> bool:
        """Clear all memory data (for testing/reset purposes)."""
        try:
            # Clear SQLite
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memory")
            cursor.execute("DELETE FROM preferences")
            cursor.execute("DELETE FROM entities")
            conn.commit()
            conn.close()
            
            # Clear ChromaDB
            if self.memory_collection:
                try:
                    self.memory_collection.delete(where={})
                except Exception as e:
                    logger.error(f"Failed to clear ChromaDB: {e}")
            
            logger.info("All memory data cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear memory data: {e}")
            return False
