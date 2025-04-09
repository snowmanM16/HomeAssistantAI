"""
Database service for Nexus AI
"""
import os
import logging
import json
import sqlite3
import hashlib
import secrets
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
import time
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for interacting with the database."""
    
    def __init__(self):
        """Initialize the database service."""
        # Get data directory from environment or use default
        self.data_dir = os.environ.get("DATA_DIR", "/data/nexus")
        
        # Create data directory if it doesn't exist
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)
        
        # Configure SQLite database
        self.db_path = os.path.join(self.data_dir, "nexus.db")
        self.db_connection = None
        
        # Initialize database
        self._init_sqlite()
    
    def _init_sqlite(self):
        """Initialize SQLite database."""
        try:
            # Create connection
            self.db_connection = sqlite3.connect(self.db_path)
            self.db_connection.row_factory = sqlite3.Row
            
            # Enable foreign keys
            self.db_connection.execute("PRAGMA foreign_keys = ON")
            
            # Create tables if they don't exist
            self._create_tables()
            
            logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise
    
    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.db_connection.cursor()
        
        try:
            # Settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,
                    value TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Home Assistant configuration table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ha_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    token_hash TEXT NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_connected_at TIMESTAMP,
                    version TEXT,
                    location_name TEXT
                )
            """)
            
            # Entities table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id TEXT NOT NULL UNIQUE,
                    friendly_name TEXT,
                    domain TEXT NOT NULL,
                    is_important BOOLEAN NOT NULL DEFAULT 0,
                    attributes TEXT,
                    last_state TEXT,
                    last_updated TIMESTAMP,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Entity states table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entity_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    attributes TEXT,
                    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (entity_id) REFERENCES entities (id) ON DELETE CASCADE
                )
            """)
            
            # Automations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS automations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    entity_id TEXT,
                    description TEXT,
                    triggers TEXT NOT NULL,
                    conditions TEXT,
                    actions TEXT NOT NULL,
                    is_enabled BOOLEAN NOT NULL DEFAULT 1,
                    is_suggested BOOLEAN NOT NULL DEFAULT 0,
                    confidence REAL NOT NULL DEFAULT 0.0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_triggered TIMESTAMP
                )
            """)
            
            # Memories table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,
                    value TEXT NOT NULL,
                    embedding_id TEXT,
                    is_preference BOOLEAN NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Patterns table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    pattern_type TEXT NOT NULL,
                    entities TEXT NOT NULL,
                    data TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 0.0,
                    times_detected INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Commit changes
            self.db_connection.commit()
            logger.info("Database tables created/verified")
        
        except Exception as e:
            logger.error(f"Error creating tables: {str(e)}")
            self.db_connection.rollback()
            raise
        
        finally:
            cursor.close()
    
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a setting value by key."""
        cursor = self.db_connection.cursor()
        
        try:
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            
            if row:
                return row["value"]
            return default
        
        except Exception as e:
            logger.error(f"Error getting setting {key}: {str(e)}")
            return default
        
        finally:
            cursor.close()
    
    def set_setting(self, key: str, value: str) -> bool:
        """Set a setting value."""
        cursor = self.db_connection.cursor()
        
        try:
            # Use UPSERT (INSERT OR REPLACE)
            cursor.execute("""
                INSERT INTO settings (key, value, updated_at) 
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (key) 
                DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP
            """, (key, value, value))
            
            self.db_connection.commit()
            return True
        
        except Exception as e:
            logger.error(f"Error setting {key}: {str(e)}")
            self.db_connection.rollback()
            return False
        
        finally:
            cursor.close()
    
    def get_all_settings(self) -> Dict[str, str]:
        """Get all settings as a dictionary."""
        cursor = self.db_connection.cursor()
        
        try:
            cursor.execute("SELECT key, value FROM settings")
            return {row["key"]: row["value"] for row in cursor.fetchall()}
        
        except Exception as e:
            logger.error(f"Error getting all settings: {str(e)}")
            return {}
        
        finally:
            cursor.close()
    
    def save_ha_config(self, url: str, token: str) -> bool:
        """Save Home Assistant configuration with token hash."""
        cursor = self.db_connection.cursor()
        
        try:
            # Hash the token for secure storage
            token_hash = self._hash_token(token)
            
            # Deactivate all existing configurations
            cursor.execute("""
                UPDATE ha_config SET is_active = 0, updated_at = CURRENT_TIMESTAMP
            """)
            
            # Add new configuration
            cursor.execute("""
                INSERT INTO ha_config (url, token_hash, is_active, created_at, updated_at)
                VALUES (?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (url, token_hash))
            
            self.db_connection.commit()
            return True
        
        except Exception as e:
            logger.error(f"Error saving HA config: {str(e)}")
            self.db_connection.rollback()
            return False
        
        finally:
            cursor.close()
    
    def get_active_ha_config(self) -> Optional[Dict[str, Any]]:
        """Get the active Home Assistant configuration."""
        cursor = self.db_connection.cursor()
        
        try:
            cursor.execute("""
                SELECT id, url, token_hash, last_connected_at, version, location_name
                FROM ha_config WHERE is_active = 1
                ORDER BY id DESC LIMIT 1
            """)
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                "id": row["id"],
                "url": row["url"],
                "token_hash": row["token_hash"],
                "last_connected_at": row["last_connected_at"],
                "version": row["version"],
                "location_name": row["location_name"]
            }
        
        except Exception as e:
            logger.error(f"Error getting active HA config: {str(e)}")
            return None
        
        finally:
            cursor.close()
    
    def update_ha_connection_status(self, version: Optional[str] = None, location_name: Optional[str] = None) -> bool:
        """Update Home Assistant connection status."""
        cursor = self.db_connection.cursor()
        
        try:
            # Get active config
            config = self.get_active_ha_config()
            if not config:
                logger.warning("No active HA config to update")
                return False
            
            # Update connection status
            cursor.execute("""
                UPDATE ha_config 
                SET last_connected_at = CURRENT_TIMESTAMP,
                    version = COALESCE(?, version),
                    location_name = COALESCE(?, location_name),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (version, location_name, config["id"]))
            
            self.db_connection.commit()
            return True
        
        except Exception as e:
            logger.error(f"Error updating HA connection status: {str(e)}")
            self.db_connection.rollback()
            return False
        
        finally:
            cursor.close()
    
    def verify_ha_token(self, token: str) -> bool:
        """Verify if a token matches the stored hash."""
        config = self.get_active_ha_config()
        if not config:
            return False
        
        token_hash = self._hash_token(token)
        return token_hash == config["token_hash"]
    
    def save_entity(self, entity_id: str, friendly_name: Optional[str], domain: str, 
                    state: str, attributes: Dict[str, Any], is_important: bool = False) -> bool:
        """Save or update an entity and its state."""
        cursor = self.db_connection.cursor()
        
        try:
            # Check if entity exists
            cursor.execute("SELECT id FROM entities WHERE entity_id = ?", (entity_id,))
            row = cursor.fetchone()
            
            if row:
                # Update existing entity
                entity_db_id = row["id"]
                cursor.execute("""
                    UPDATE entities 
                    SET friendly_name = ?, last_state = ?, attributes = ?, 
                        is_important = ?, last_updated = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    friendly_name, 
                    state, 
                    json.dumps(attributes), 
                    1 if is_important else 0,
                    entity_db_id
                ))
            else:
                # Insert new entity
                cursor.execute("""
                    INSERT INTO entities 
                    (entity_id, friendly_name, domain, last_state, attributes, is_important, 
                     last_updated, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (
                    entity_id, 
                    friendly_name, 
                    domain, 
                    state, 
                    json.dumps(attributes), 
                    1 if is_important else 0
                ))
                cursor.execute("SELECT last_insert_rowid()")
                entity_db_id = cursor.fetchone()[0]
            
            # Save state history
            cursor.execute("""
                INSERT INTO entity_states (entity_id, state, attributes, timestamp)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (entity_db_id, state, json.dumps(attributes)))
            
            self.db_connection.commit()
            return True
        
        except Exception as e:
            logger.error(f"Error saving entity {entity_id}: {str(e)}")
            self.db_connection.rollback()
            return False
        
        finally:
            cursor.close()
    
    def get_entities(self, domain: Optional[str] = None, important_only: bool = False) -> List[Dict[str, Any]]:
        """Get entities with optional filtering."""
        cursor = self.db_connection.cursor()
        
        try:
            # Build query based on filters
            query = "SELECT * FROM entities WHERE 1=1"
            params = []
            
            if domain:
                query += " AND domain = ?"
                params.append(domain)
            
            if important_only:
                query += " AND is_important = 1"
            
            query += " ORDER BY domain, entity_id"
            
            # Execute query
            cursor.execute(query, params)
            
            # Process results
            entities = []
            for row in cursor.fetchall():
                try:
                    attributes = json.loads(row["attributes"]) if row["attributes"] else {}
                except json.JSONDecodeError:
                    attributes = {}
                
                entities.append({
                    "id": row["id"],
                    "entity_id": row["entity_id"],
                    "friendly_name": row["friendly_name"],
                    "domain": row["domain"],
                    "is_important": bool(row["is_important"]),
                    "attributes": attributes,
                    "last_state": row["last_state"],
                    "last_updated": row["last_updated"]
                })
            
            return entities
        
        except Exception as e:
            logger.error(f"Error getting entities: {str(e)}")
            return []
        
        finally:
            cursor.close()
    
    def get_entity_history(self, entity_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get history for a specific entity."""
        cursor = self.db_connection.cursor()
        
        try:
            # Get entity database ID
            cursor.execute("SELECT id FROM entities WHERE entity_id = ?", (entity_id,))
            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"Entity {entity_id} not found")
                return []
            
            entity_db_id = row["id"]
            
            # Get historical states
            cursor.execute("""
                SELECT state, attributes, timestamp
                FROM entity_states
                WHERE entity_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (entity_db_id, limit))
            
            # Process results
            history = []
            for row in cursor.fetchall():
                try:
                    attributes = json.loads(row["attributes"]) if row["attributes"] else {}
                except json.JSONDecodeError:
                    attributes = {}
                
                history.append({
                    "state": row["state"],
                    "attributes": attributes,
                    "timestamp": row["timestamp"]
                })
            
            return history
        
        except Exception as e:
            logger.error(f"Error getting history for {entity_id}: {str(e)}")
            return []
        
        finally:
            cursor.close()
    
    def save_automation(self, name: str, triggers: List[Dict[str, Any]], 
                      actions: List[Dict[str, Any]], entity_id: Optional[str] = None,
                      description: Optional[str] = None, conditions: Optional[List[Dict[str, Any]]] = None,
                      is_suggested: bool = False, confidence: float = 0.0) -> Optional[int]:
        """Save a new automation."""
        cursor = self.db_connection.cursor()
        
        try:
            # Convert lists to JSON strings
            triggers_json = json.dumps(triggers)
            actions_json = json.dumps(actions)
            conditions_json = json.dumps(conditions) if conditions else None
            
            # Insert automation
            cursor.execute("""
                INSERT INTO automations 
                (name, entity_id, description, triggers, conditions, actions, 
                 is_suggested, confidence, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                name, entity_id, description, triggers_json, conditions_json, actions_json,
                1 if is_suggested else 0, confidence
            ))
            
            # Get the ID of the inserted automation
            cursor.execute("SELECT last_insert_rowid()")
            automation_id = cursor.fetchone()[0]
            
            self.db_connection.commit()
            return automation_id
        
        except Exception as e:
            logger.error(f"Error saving automation {name}: {str(e)}")
            self.db_connection.rollback()
            return None
        
        finally:
            cursor.close()
    
    def get_automations(self, suggested_only: bool = False) -> List[Dict[str, Any]]:
        """Get all automations with optional filtering."""
        cursor = self.db_connection.cursor()
        
        try:
            # Build query based on filters
            query = "SELECT * FROM automations WHERE 1=1"
            params = []
            
            if suggested_only:
                query += " AND is_suggested = 1"
            
            query += " ORDER BY name"
            
            # Execute query
            cursor.execute(query, params)
            
            # Process results
            automations = []
            for row in cursor.fetchall():
                try:
                    triggers = json.loads(row["triggers"]) if row["triggers"] else []
                    conditions = json.loads(row["conditions"]) if row["conditions"] else []
                    actions = json.loads(row["actions"]) if row["actions"] else []
                except json.JSONDecodeError:
                    triggers, conditions, actions = [], [], []
                
                automations.append({
                    "id": row["id"],
                    "name": row["name"],
                    "entity_id": row["entity_id"],
                    "description": row["description"],
                    "triggers": triggers,
                    "conditions": conditions,
                    "actions": actions,
                    "is_enabled": bool(row["is_enabled"]),
                    "is_suggested": bool(row["is_suggested"]),
                    "confidence": float(row["confidence"]),
                    "created_at": row["created_at"],
                    "last_triggered": row["last_triggered"]
                })
            
            return automations
        
        except Exception as e:
            logger.error(f"Error getting automations: {str(e)}")
            return []
        
        finally:
            cursor.close()
    
    def update_automation_status(self, automation_id: int, is_enabled: bool) -> bool:
        """Enable or disable an automation."""
        cursor = self.db_connection.cursor()
        
        try:
            cursor.execute("""
                UPDATE automations
                SET is_enabled = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (1 if is_enabled else 0, automation_id))
            
            self.db_connection.commit()
            return True
        
        except Exception as e:
            logger.error(f"Error updating automation {automation_id}: {str(e)}")
            self.db_connection.rollback()
            return False
        
        finally:
            cursor.close()
    
    def record_automation_trigger(self, automation_id: int) -> bool:
        """Record that an automation was triggered."""
        cursor = self.db_connection.cursor()
        
        try:
            cursor.execute("""
                UPDATE automations
                SET last_triggered = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (automation_id,))
            
            self.db_connection.commit()
            return True
        
        except Exception as e:
            logger.error(f"Error recording trigger for automation {automation_id}: {str(e)}")
            self.db_connection.rollback()
            return False
        
        finally:
            cursor.close()
    
    def save_memory(self, key: str, value: str, embedding_id: Optional[str] = None, is_preference: bool = False) -> bool:
        """Save a memory item."""
        cursor = self.db_connection.cursor()
        
        try:
            # Use UPSERT (INSERT OR REPLACE)
            cursor.execute("""
                INSERT INTO memories (key, value, embedding_id, is_preference, updated_at) 
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (key) 
                DO UPDATE SET value = ?, embedding_id = ?, is_preference = ?, updated_at = CURRENT_TIMESTAMP
            """, (
                key, value, embedding_id, 1 if is_preference else 0,
                value, embedding_id, 1 if is_preference else 0
            ))
            
            self.db_connection.commit()
            return True
        
        except Exception as e:
            logger.error(f"Error saving memory {key}: {str(e)}")
            self.db_connection.rollback()
            return False
        
        finally:
            cursor.close()
    
    def get_memory(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a memory item by key."""
        cursor = self.db_connection.cursor()
        
        try:
            cursor.execute("SELECT * FROM memories WHERE key = ?", (key,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return {
                "id": row["id"],
                "key": row["key"],
                "value": row["value"],
                "embedding_id": row["embedding_id"],
                "is_preference": bool(row["is_preference"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }
        
        except Exception as e:
            logger.error(f"Error getting memory {key}: {str(e)}")
            return None
        
        finally:
            cursor.close()
    
    def get_all_memories(self, preferences_only: bool = False) -> List[Dict[str, Any]]:
        """Get all memory items."""
        cursor = self.db_connection.cursor()
        
        try:
            # Build query based on filters
            query = "SELECT * FROM memories WHERE 1=1"
            params = []
            
            if preferences_only:
                query += " AND is_preference = 1"
            
            query += " ORDER BY key"
            
            # Execute query
            cursor.execute(query, params)
            
            # Process results
            memories = []
            for row in cursor.fetchall():
                memories.append({
                    "id": row["id"],
                    "key": row["key"],
                    "value": row["value"],
                    "embedding_id": row["embedding_id"],
                    "is_preference": bool(row["is_preference"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                })
            
            return memories
        
        except Exception as e:
            logger.error(f"Error getting memories: {str(e)}")
            return []
        
        finally:
            cursor.close()
    
    def delete_memory(self, key: str) -> bool:
        """Delete a memory item."""
        cursor = self.db_connection.cursor()
        
        try:
            cursor.execute("DELETE FROM memories WHERE key = ?", (key,))
            self.db_connection.commit()
            return cursor.rowcount > 0
        
        except Exception as e:
            logger.error(f"Error deleting memory {key}: {str(e)}")
            self.db_connection.rollback()
            return False
        
        finally:
            cursor.close()
    
    def save_pattern(self, name: str, pattern_type: str, entities: List[str], 
                    data: Dict[str, Any], confidence: float = 0.0) -> Optional[int]:
        """Save a detected pattern."""
        cursor = self.db_connection.cursor()
        
        try:
            # Check if a similar pattern exists
            cursor.execute("""
                SELECT id, confidence, times_detected FROM patterns 
                WHERE name = ? AND pattern_type = ?
            """, (name, pattern_type))
            
            row = cursor.fetchone()
            
            if row:
                # Update existing pattern
                pattern_id = row["id"]
                old_confidence = float(row["confidence"])
                times_detected = int(row["times_detected"]) + 1
                
                # Adjust confidence (weighted average)
                new_confidence = (old_confidence * (times_detected - 1) + confidence) / times_detected
                
                cursor.execute("""
                    UPDATE patterns
                    SET entities = ?, data = ?, confidence = ?, times_detected = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    json.dumps(entities), 
                    json.dumps(data), 
                    new_confidence, 
                    times_detected,
                    pattern_id
                ))
            else:
                # Insert new pattern
                cursor.execute("""
                    INSERT INTO patterns
                    (name, pattern_type, entities, data, confidence, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (
                    name, 
                    pattern_type, 
                    json.dumps(entities), 
                    json.dumps(data), 
                    confidence
                ))
                
                # Get the ID of the inserted pattern
                cursor.execute("SELECT last_insert_rowid()")
                pattern_id = cursor.fetchone()[0]
            
            self.db_connection.commit()
            return pattern_id
        
        except Exception as e:
            logger.error(f"Error saving pattern {name}: {str(e)}")
            self.db_connection.rollback()
            return None
        
        finally:
            cursor.close()
    
    def get_patterns(self, pattern_type: Optional[str] = None, min_confidence: float = 0.0) -> List[Dict[str, Any]]:
        """Get patterns with optional filtering."""
        cursor = self.db_connection.cursor()
        
        try:
            # Build query based on filters
            query = "SELECT * FROM patterns WHERE confidence >= ?"
            params = [min_confidence]
            
            if pattern_type:
                query += " AND pattern_type = ?"
                params.append(pattern_type)
            
            query += " ORDER BY confidence DESC"
            
            # Execute query
            cursor.execute(query, params)
            
            # Process results
            patterns = []
            for row in cursor.fetchall():
                try:
                    entities = json.loads(row["entities"]) if row["entities"] else []
                    data = json.loads(row["data"]) if row["data"] else {}
                except json.JSONDecodeError:
                    entities, data = [], {}
                
                patterns.append({
                    "id": row["id"],
                    "name": row["name"],
                    "pattern_type": row["pattern_type"],
                    "entities": entities,
                    "data": data,
                    "confidence": float(row["confidence"]),
                    "times_detected": int(row["times_detected"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                })
            
            return patterns
        
        except Exception as e:
            logger.error(f"Error getting patterns: {str(e)}")
            return []
        
        finally:
            cursor.close()
    
    def _hash_token(self, token: str) -> str:
        """Create a secure hash of a token."""
        salt = secrets.token_hex(16)
        token_hash = hashlib.sha256((token + salt).encode()).hexdigest()
        return f"{salt}:{token_hash}"