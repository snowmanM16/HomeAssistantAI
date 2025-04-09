"""
Database service for Nexus AI
"""
import os
import logging
import json
import hashlib
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger("nexus.database")

class DatabaseService:
    """Service for interacting with the database."""
    
    def __init__(self):
        """Initialize the database service."""
        # Use SQLite by default, but support PostgreSQL if configured
        self.database_url = os.environ.get("DATABASE_URL", f"sqlite:///{os.environ.get('DATA_DIR', '/data/nexus')}/database.sqlite")
        
        if self.database_url.startswith("sqlite"):
            # SQLite implementation
            self.db_path = self.database_url.replace("sqlite:///", "")
            self._init_sqlite()
        else:
            # PostgreSQL or other database
            try:
                import sqlalchemy
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker
                
                self.engine = create_engine(self.database_url)
                self.Session = sessionmaker(bind=self.engine)
                logger.info(f"Using database: {self.database_url}")
            except ImportError:
                logger.error("SQLAlchemy not installed, falling back to SQLite")
                self.db_path = f"{os.environ.get('DATA_DIR', '/data/nexus')}/database.sqlite"
                self._init_sqlite()
    
    def _init_sqlite(self):
        """Initialize SQLite database."""
        logger.info(f"Using SQLite database: {self.db_path}")
        
        # Make sure the directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Create tables if they don't exist
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Settings table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            key TEXT UNIQUE NOT NULL,
            value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Home Assistant config table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ha_config (
            id INTEGER PRIMARY KEY,
            url TEXT NOT NULL,
            token_hash TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_connected_at TIMESTAMP,
            version TEXT,
            location_name TEXT
        )
        ''')
        
        # Entities table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY,
            entity_id TEXT UNIQUE NOT NULL,
            friendly_name TEXT,
            domain TEXT NOT NULL,
            is_important BOOLEAN DEFAULT 0,
            attributes TEXT,
            last_state TEXT,
            last_updated TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Entity states table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS entity_states (
            id INTEGER PRIMARY KEY,
            entity_id INTEGER NOT NULL,
            state TEXT NOT NULL,
            attributes TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entity_id) REFERENCES entities (id)
        )
        ''')
        
        # Automations table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS automations (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            entity_id TEXT,
            description TEXT,
            triggers TEXT NOT NULL,
            conditions TEXT,
            actions TEXT NOT NULL,
            is_enabled BOOLEAN DEFAULT 1,
            is_suggested BOOLEAN DEFAULT 0,
            confidence REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_triggered TIMESTAMP
        )
        ''')
        
        # Memories table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            embedding_id TEXT,
            is_preference BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Patterns table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS patterns (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            pattern_type TEXT NOT NULL,
            entities TEXT NOT NULL,
            data TEXT NOT NULL,
            confidence REAL DEFAULT 0.0,
            times_detected INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a setting value by key."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = cursor.fetchone()
        
        conn.close()
        
        return result[0] if result else default
    
    def set_setting(self, key: str, value: str) -> bool:
        """Set a setting value."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT INTO settings (key, value, updated_at) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET 
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            ''', (key, value))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error setting {key}: {e}")
            conn.close()
            return False
    
    def get_all_settings(self) -> Dict[str, str]:
        """Get all settings as a dictionary."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT key, value FROM settings")
        results = cursor.fetchall()
        
        conn.close()
        
        return {row[0]: row[1] for row in results}
    
    def save_ha_config(self, url: str, token: str) -> bool:
        """Save Home Assistant configuration with token hash."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Hash the token for security
        token_hash = self._hash_token(token)
        
        try:
            # Set all existing configs to inactive
            cursor.execute("UPDATE ha_config SET is_active = 0")
            
            # Insert new config
            cursor.execute('''
            INSERT INTO ha_config (url, token_hash, is_active, updated_at)
            VALUES (?, ?, 1, CURRENT_TIMESTAMP)
            ''', (url, token_hash))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error saving HA config: {e}")
            conn.close()
            return False
    
    def get_active_ha_config(self) -> Optional[Dict[str, Any]]:
        """Get the active Home Assistant configuration."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT id, url, is_active, created_at, updated_at, 
               last_connected_at, version, location_name
        FROM ha_config 
        WHERE is_active = 1 
        ORDER BY updated_at DESC 
        LIMIT 1
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return dict(result)
        return None
    
    def update_ha_connection_status(self, version: Optional[str] = None, location_name: Optional[str] = None) -> bool:
        """Update Home Assistant connection status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            UPDATE ha_config 
            SET last_connected_at = CURRENT_TIMESTAMP,
                version = COALESCE(?, version),
                location_name = COALESCE(?, location_name),
                updated_at = CURRENT_TIMESTAMP
            WHERE is_active = 1
            """, (version, location_name))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error updating HA connection: {e}")
            conn.close()
            return False
    
    def verify_ha_token(self, token: str) -> bool:
        """Verify if a token matches the stored hash."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        token_hash = self._hash_token(token)
        
        cursor.execute("SELECT id FROM ha_config WHERE token_hash = ? AND is_active = 1", (token_hash,))
        result = cursor.fetchone()
        
        conn.close()
        
        return result is not None
    
    def save_entity(self, entity_id: str, friendly_name: Optional[str], domain: str, 
                    state: str, attributes: Dict[str, Any], is_important: bool = False) -> bool:
        """Save or update an entity and its state."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Convert attributes to JSON string
            attributes_json = json.dumps(attributes)
            
            # Insert or update entity
            cursor.execute('''
            INSERT INTO entities (
                entity_id, friendly_name, domain, is_important, 
                attributes, last_state, last_updated, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(entity_id) DO UPDATE SET
                friendly_name = COALESCE(excluded.friendly_name, friendly_name),
                domain = excluded.domain,
                is_important = excluded.is_important,
                attributes = excluded.attributes,
                last_state = excluded.last_state,
                last_updated = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            ''', (entity_id, friendly_name, domain, is_important, attributes_json, state))
            
            # Get the entity ID for the state history
            cursor.execute("SELECT id FROM entities WHERE entity_id = ?", (entity_id,))
            entity_db_id = cursor.fetchone()[0]
            
            # Add to state history
            cursor.execute('''
            INSERT INTO entity_states (entity_id, state, attributes)
            VALUES (?, ?, ?)
            ''', (entity_db_id, state, attributes_json))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error saving entity {entity_id}: {e}")
            conn.close()
            return False
    
    def get_entities(self, domain: Optional[str] = None, important_only: bool = False) -> List[Dict[str, Any]]:
        """Get entities with optional filtering."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM entities WHERE 1=1"
        params = []
        
        if domain:
            query += " AND domain = ?"
            params.append(domain)
        
        if important_only:
            query += " AND is_important = 1"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        entities = []
        for row in results:
            entity = dict(row)
            # Parse JSON attributes
            if entity.get('attributes'):
                try:
                    entity['attributes'] = json.loads(entity['attributes'])
                except:
                    entity['attributes'] = {}
            entities.append(entity)
        
        conn.close()
        return entities
    
    def get_entity_history(self, entity_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get history for a specific entity."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT es.* FROM entity_states es
        JOIN entities e ON es.entity_id = e.id
        WHERE e.entity_id = ?
        ORDER BY es.timestamp DESC
        LIMIT ?
        ''', (entity_id, limit))
        
        results = cursor.fetchall()
        
        history = []
        for row in results:
            item = dict(row)
            # Parse JSON attributes
            if item.get('attributes'):
                try:
                    item['attributes'] = json.loads(item['attributes'])
                except:
                    item['attributes'] = {}
            history.append(item)
        
        conn.close()
        return history
    
    def save_automation(self, name: str, triggers: List[Dict[str, Any]], 
                      actions: List[Dict[str, Any]], entity_id: Optional[str] = None,
                      description: Optional[str] = None, conditions: Optional[List[Dict[str, Any]]] = None,
                      is_suggested: bool = False, confidence: float = 0.0) -> Optional[int]:
        """Save a new automation."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Convert to JSON strings
            triggers_json = json.dumps(triggers)
            actions_json = json.dumps(actions)
            conditions_json = json.dumps(conditions) if conditions else None
            
            cursor.execute('''
            INSERT INTO automations (
                name, entity_id, description, triggers, conditions, 
                actions, is_suggested, confidence, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (name, entity_id, description, triggers_json, conditions_json, 
                  actions_json, is_suggested, confidence))
            
            automation_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return automation_id
        except Exception as e:
            logger.error(f"Error saving automation: {e}")
            conn.close()
            return None
    
    def get_automations(self, suggested_only: bool = False) -> List[Dict[str, Any]]:
        """Get all automations with optional filtering."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM automations"
        if suggested_only:
            query += " WHERE is_suggested = 1"
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        automations = []
        for row in results:
            automation = dict(row)
            # Parse JSON fields
            for field in ['triggers', 'conditions', 'actions']:
                if automation.get(field):
                    try:
                        automation[field] = json.loads(automation[field])
                    except:
                        automation[field] = []
            automations.append(automation)
        
        conn.close()
        return automations
    
    def update_automation_status(self, automation_id: int, is_enabled: bool) -> bool:
        """Enable or disable an automation."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            UPDATE automations
            SET is_enabled = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            ''', (is_enabled, automation_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error updating automation status: {e}")
            conn.close()
            return False
    
    def record_automation_trigger(self, automation_id: int) -> bool:
        """Record that an automation was triggered."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            UPDATE automations
            SET last_triggered = CURRENT_TIMESTAMP
            WHERE id = ?
            ''', (automation_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error recording automation trigger: {e}")
            conn.close()
            return False
    
    def save_memory(self, key: str, value: str, embedding_id: Optional[str] = None, is_preference: bool = False) -> bool:
        """Save a memory item."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT INTO memories (key, value, embedding_id, is_preference, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                embedding_id = COALESCE(excluded.embedding_id, embedding_id),
                is_preference = excluded.is_preference,
                updated_at = CURRENT_TIMESTAMP
            ''', (key, value, embedding_id, is_preference))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error saving memory {key}: {e}")
            conn.close()
            return False
    
    def get_memory(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a memory item by key."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM memories WHERE key = ?", (key,))
        result = cursor.fetchone()
        
        conn.close()
        
        return dict(result) if result else None
    
    def get_all_memories(self, preferences_only: bool = False) -> List[Dict[str, Any]]:
        """Get all memory items."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM memories"
        if preferences_only:
            query += " WHERE is_preference = 1"
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        conn.close()
        
        return [dict(row) for row in results]
    
    def delete_memory(self, key: str) -> bool:
        """Delete a memory item."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM memories WHERE key = ?", (key,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error deleting memory {key}: {e}")
            conn.close()
            return False
    
    def save_pattern(self, name: str, pattern_type: str, entities: List[str], 
                    data: Dict[str, Any], confidence: float = 0.0) -> Optional[int]:
        """Save a detected pattern."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Convert to JSON strings
            entities_json = json.dumps(entities)
            data_json = json.dumps(data)
            
            # Check if a similar pattern already exists
            cursor.execute('''
            SELECT id, confidence, times_detected FROM patterns
            WHERE name = ? AND pattern_type = ?
            ''', (name, pattern_type))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing pattern
                existing_id, existing_confidence, times_detected = existing
                
                # Average confidence with existing
                new_confidence = (existing_confidence * times_detected + confidence) / (times_detected + 1)
                new_times_detected = times_detected + 1
                
                cursor.execute('''
                UPDATE patterns
                SET entities = ?, data = ?, confidence = ?, times_detected = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                ''', (entities_json, data_json, new_confidence, new_times_detected, existing_id))
                
                conn.commit()
                conn.close()
                return existing_id
            else:
                # Insert new pattern
                cursor.execute('''
                INSERT INTO patterns (name, pattern_type, entities, data, confidence, times_detected, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (name, pattern_type, entities_json, data_json, confidence))
                
                pattern_id = cursor.lastrowid
                conn.commit()
                conn.close()
                return pattern_id
        except Exception as e:
            logger.error(f"Error saving pattern: {e}")
            conn.close()
            return None
    
    def get_patterns(self, pattern_type: Optional[str] = None, min_confidence: float = 0.0) -> List[Dict[str, Any]]:
        """Get patterns with optional filtering."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM patterns WHERE confidence >= ?"
        params = [min_confidence]
        
        if pattern_type:
            query += " AND pattern_type = ?"
            params.append(pattern_type)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        patterns = []
        for row in results:
            pattern = dict(row)
            # Parse JSON fields
            for field in ['entities', 'data']:
                if pattern.get(field):
                    try:
                        pattern[field] = json.loads(pattern[field])
                    except:
                        if field == 'entities':
                            pattern[field] = []
                        else:
                            pattern[field] = {}
            patterns.append(pattern)
        
        conn.close()
        return patterns
    
    def _hash_token(self, token: str) -> str:
        """Create a secure hash of a token."""
        return hashlib.sha256(token.encode()).hexdigest()
