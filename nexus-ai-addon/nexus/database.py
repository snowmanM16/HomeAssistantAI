import os
import logging
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from sqlalchemy import create_engine, func, desc
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError

from nexus.models import (
    Base, Setting, HomeAssistantConfig, Entity, EntityState, 
    Automation, Memory, Pattern, get_db, init_db, close_db
)

logger = logging.getLogger("nexus.database")

class DatabaseService:
    """Service for interacting with the database."""
    
    def __init__(self):
        """Initialize the database service."""
        try:
            # Initialize the database
            init_db()
            logger.info("Database initialized with PostgreSQL")
            
            # Try to create a test setting to ensure tables exist
            self.set_setting("db_initialized", "true")
            logger.info("Successfully created tables and test setting")
        except Exception as e:
            logger.error(f"Error initializing database: {e}", exc_info=True)
    
    # Settings methods
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a setting value by key."""
        db = None
        try:
            db = get_db()
            setting = db.query(Setting).filter(Setting.key == key).first()
            return setting.value if setting else default
        except Exception as e:
            logger.error(f"Error getting setting {key}: {e}")
            return default
        finally:
            close_db()
    
    def set_setting(self, key: str, value: str) -> bool:
        """Set a setting value."""
        db = None
        try:
            db = get_db()
            setting = db.query(Setting).filter(Setting.key == key).first()
            
            if setting:
                setting.value = value
                setting.updated_at = datetime.utcnow()
            else:
                setting = Setting(key=key, value=value)
                db.add(setting)
                
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting setting {key}: {e}")
            if db is not None:
                db.rollback()
            return False
        finally:
            close_db()
    
    def get_all_settings(self) -> Dict[str, str]:
        """Get all settings as a dictionary."""
        try:
            db = get_db()
            settings = db.query(Setting).all()
            return {setting.key: setting.value for setting in settings}
        except Exception as e:
            logger.error(f"Error getting all settings: {e}")
            return {}
        finally:
            close_db()
    
    # Home Assistant configuration methods
    def save_ha_config(self, url: str, token: str) -> bool:
        """Save Home Assistant configuration with token hash."""
        try:
            # Create token hash for storage - never store the actual token
            token_hash = self._hash_token(token)
            
            db = get_db()
            
            # First deactivate any existing configurations
            db.query(HomeAssistantConfig).update({
                "is_active": False,
                "updated_at": datetime.utcnow()
            })
            
            # Check if a config with this URL already exists
            existing = db.query(HomeAssistantConfig).filter(
                HomeAssistantConfig.url == url
            ).first()
            
            if existing:
                # Update existing
                existing.token_hash = token_hash
                existing.is_active = True
                existing.updated_at = datetime.utcnow()
            else:
                # Create new
                config = HomeAssistantConfig(
                    url=url,
                    token_hash=token_hash,
                    is_active=True
                )
                db.add(config)
            
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving HA config: {e}")
            db.rollback()
            return False
        finally:
            close_db()
    
    def get_active_ha_config(self) -> Optional[Dict[str, Any]]:
        """Get the active Home Assistant configuration."""
        try:
            db = get_db()
            config = db.query(HomeAssistantConfig).filter(
                HomeAssistantConfig.is_active == True
            ).first()
            
            if not config:
                return None
                
            return {
                "id": config.id,
                "url": config.url,
                "is_active": config.is_active,
                "last_connected_at": config.last_connected_at,
                "version": config.version,
                "location_name": config.location_name
            }
        except Exception as e:
            logger.error(f"Error getting active HA config: {e}")
            return None
        finally:
            close_db()
    
    def update_ha_connection_status(self, version: Optional[str] = None, location_name: Optional[str] = None) -> bool:
        """Update Home Assistant connection status."""
        try:
            db = get_db()
            config = db.query(HomeAssistantConfig).filter(
                HomeAssistantConfig.is_active == True
            ).first()
            
            if not config:
                return False
                
            config.last_connected_at = datetime.utcnow()
            
            if version:
                config.version = version
                
            if location_name:
                config.location_name = location_name
                
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating HA connection status: {e}")
            db.rollback()
            return False
        finally:
            close_db()
    
    def verify_ha_token(self, token: str) -> bool:
        """Verify if a token matches the stored hash."""
        try:
            token_hash = self._hash_token(token)
            
            db = get_db()
            config = db.query(HomeAssistantConfig).filter(
                HomeAssistantConfig.is_active == True
            ).first()
            
            if not config:
                return False
                
            return config.token_hash == token_hash
        except Exception as e:
            logger.error(f"Error verifying HA token: {e}")
            return False
        finally:
            close_db()
    
    # Entity methods
    def save_entity(self, entity_id: str, friendly_name: Optional[str], domain: str, 
                    state: str, attributes: Dict[str, Any], is_important: bool = False) -> bool:
        """Save or update an entity and its state."""
        try:
            db = get_db()
            
            # Check if entity exists
            entity = db.query(Entity).filter(Entity.entity_id == entity_id).first()
            
            now = datetime.utcnow()
            
            if not entity:
                # Create new entity
                entity = Entity(
                    entity_id=entity_id,
                    friendly_name=friendly_name,
                    domain=domain,
                    last_state=state,
                    last_updated=now,
                    attributes=attributes,
                    is_important=is_important
                )
                db.add(entity)
                db.flush()  # Get the ID before using it in a relationship
            else:
                # Update existing entity
                entity.friendly_name = friendly_name
                entity.last_state = state
                entity.last_updated = now
                entity.attributes = attributes
                
                if is_important:
                    entity.is_important = True
            
            # Add state history
            state_record = EntityState(
                entity_id=entity.id,
                state=state,
                attributes=attributes,
                timestamp=now
            )
            db.add(state_record)
            
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving entity {entity_id}: {e}")
            db.rollback()
            return False
        finally:
            close_db()
    
    def get_entities(self, domain: Optional[str] = None, important_only: bool = False) -> List[Dict[str, Any]]:
        """Get entities with optional filtering."""
        try:
            db = get_db()
            query = db.query(Entity)
            
            if domain:
                query = query.filter(Entity.domain == domain)
                
            if important_only:
                query = query.filter(Entity.is_important == True)
                
            entities = query.all()
            
            return [{
                "id": entity.id,
                "entity_id": entity.entity_id,
                "friendly_name": entity.friendly_name,
                "domain": entity.domain,
                "state": entity.last_state,
                "attributes": entity.attributes,
                "is_important": entity.is_important,
                "last_updated": entity.last_updated
            } for entity in entities]
        except Exception as e:
            logger.error(f"Error getting entities: {e}")
            return []
        finally:
            close_db()
    
    def get_entity_history(self, entity_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get history for a specific entity."""
        try:
            db = get_db()
            
            entity = db.query(Entity).filter(Entity.entity_id == entity_id).first()
            
            if not entity:
                return []
                
            states = db.query(EntityState).filter(
                EntityState.entity_id == entity.id
            ).order_by(desc(EntityState.timestamp)).limit(limit).all()
            
            return [{
                "state": state.state,
                "attributes": state.attributes,
                "timestamp": state.timestamp
            } for state in states]
        except Exception as e:
            logger.error(f"Error getting entity history for {entity_id}: {e}")
            return []
        finally:
            close_db()
    
    # Automation methods
    def save_automation(self, name: str, triggers: List[Dict[str, Any]], 
                      actions: List[Dict[str, Any]], entity_id: Optional[str] = None,
                      description: Optional[str] = None, conditions: Optional[List[Dict[str, Any]]] = None,
                      is_suggested: bool = False, confidence: float = 0.0) -> Optional[int]:
        """Save a new automation."""
        try:
            db = get_db()
            
            automation = Automation(
                name=name,
                entity_id=entity_id,
                description=description,
                triggers=triggers,
                conditions=conditions,
                actions=actions,
                is_suggested=is_suggested,
                confidence=confidence
            )
            
            db.add(automation)
            db.commit()
            
            return automation.id
        except Exception as e:
            logger.error(f"Error saving automation {name}: {e}")
            db.rollback()
            return None
        finally:
            close_db()
    
    def get_automations(self, suggested_only: bool = False) -> List[Dict[str, Any]]:
        """Get all automations with optional filtering."""
        try:
            db = get_db()
            query = db.query(Automation)
            
            if suggested_only:
                query = query.filter(Automation.is_suggested == True)
                
            automations = query.all()
            
            return [{
                "id": auto.id,
                "name": auto.name,
                "entity_id": auto.entity_id,
                "description": auto.description,
                "triggers": auto.triggers,
                "conditions": auto.conditions,
                "actions": auto.actions,
                "is_enabled": auto.is_enabled,
                "is_suggested": auto.is_suggested,
                "confidence": auto.confidence,
                "last_triggered": auto.last_triggered
            } for auto in automations]
        except Exception as e:
            logger.error(f"Error getting automations: {e}")
            return []
        finally:
            close_db()
    
    def update_automation_status(self, automation_id: int, is_enabled: bool) -> bool:
        """Enable or disable an automation."""
        try:
            db = get_db()
            
            automation = db.query(Automation).filter(Automation.id == automation_id).first()
            
            if not automation:
                return False
                
            automation.is_enabled = is_enabled
            automation.updated_at = datetime.utcnow()
            
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating automation status for ID {automation_id}: {e}")
            db.rollback()
            return False
        finally:
            close_db()
    
    def record_automation_trigger(self, automation_id: int) -> bool:
        """Record that an automation was triggered."""
        try:
            db = get_db()
            
            automation = db.query(Automation).filter(Automation.id == automation_id).first()
            
            if not automation:
                return False
                
            automation.last_triggered = datetime.utcnow()
            
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error recording automation trigger for ID {automation_id}: {e}")
            db.rollback()
            return False
        finally:
            close_db()
    
    # Memory methods
    def save_memory(self, key: str, value: str, embedding_id: Optional[str] = None, is_preference: bool = False) -> bool:
        """Save a memory item."""
        try:
            db = get_db()
            
            # Check if memory exists
            memory = db.query(Memory).filter(Memory.key == key).first()
            
            if memory:
                # Update existing
                memory.value = value
                memory.updated_at = datetime.utcnow()
                
                if embedding_id:
                    memory.embedding_id = embedding_id
                    
                memory.is_preference = is_preference
            else:
                # Create new
                memory = Memory(
                    key=key,
                    value=value,
                    embedding_id=embedding_id,
                    is_preference=is_preference
                )
                db.add(memory)
                
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving memory {key}: {e}")
            db.rollback()
            return False
        finally:
            close_db()
    
    def get_memory(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a memory item by key."""
        try:
            db = get_db()
            
            memory = db.query(Memory).filter(Memory.key == key).first()
            
            if not memory:
                return None
                
            return {
                "id": memory.id,
                "key": memory.key,
                "value": memory.value,
                "embedding_id": memory.embedding_id,
                "is_preference": memory.is_preference,
                "created_at": memory.created_at,
                "updated_at": memory.updated_at
            }
        except Exception as e:
            logger.error(f"Error getting memory {key}: {e}")
            return None
        finally:
            close_db()
    
    def get_all_memories(self, preferences_only: bool = False) -> List[Dict[str, Any]]:
        """Get all memory items."""
        try:
            db = get_db()
            query = db.query(Memory)
            
            if preferences_only:
                query = query.filter(Memory.is_preference == True)
                
            memories = query.all()
            
            return [{
                "id": memory.id,
                "key": memory.key,
                "value": memory.value,
                "embedding_id": memory.embedding_id,
                "is_preference": memory.is_preference,
                "created_at": memory.created_at,
                "updated_at": memory.updated_at
            } for memory in memories]
        except Exception as e:
            logger.error(f"Error getting all memories: {e}")
            return []
        finally:
            close_db()
    
    def delete_memory(self, key: str) -> bool:
        """Delete a memory item."""
        try:
            db = get_db()
            
            result = db.query(Memory).filter(Memory.key == key).delete()
            
            db.commit()
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting memory {key}: {e}")
            db.rollback()
            return False
        finally:
            close_db()
    
    # Pattern methods
    def save_pattern(self, name: str, pattern_type: str, entities: List[str], 
                    data: Dict[str, Any], confidence: float = 0.0) -> Optional[int]:
        """Save a detected pattern."""
        try:
            db = get_db()
            
            # Check if a similar pattern exists
            existing = db.query(Pattern).filter(
                Pattern.name == name,
                Pattern.pattern_type == pattern_type
            ).first()
            
            if existing:
                # Update existing pattern
                existing.entities = entities
                existing.data = data
                existing.confidence = max(existing.confidence, confidence)
                existing.times_detected += 1
                existing.updated_at = datetime.utcnow()
                
                db.commit()
                return existing.id
            else:
                # Create new pattern
                pattern = Pattern(
                    name=name,
                    pattern_type=pattern_type,
                    entities=entities,
                    data=data,
                    confidence=confidence
                )
                
                db.add(pattern)
                db.commit()
                
                return pattern.id
        except Exception as e:
            logger.error(f"Error saving pattern {name}: {e}")
            db.rollback()
            return None
        finally:
            close_db()
    
    def get_patterns(self, pattern_type: Optional[str] = None, min_confidence: float = 0.0) -> List[Dict[str, Any]]:
        """Get patterns with optional filtering."""
        try:
            db = get_db()
            query = db.query(Pattern).filter(Pattern.confidence >= min_confidence)
            
            if pattern_type:
                query = query.filter(Pattern.pattern_type == pattern_type)
                
            patterns = query.all()
            
            return [{
                "id": pattern.id,
                "name": pattern.name,
                "pattern_type": pattern.pattern_type,
                "entities": pattern.entities,
                "data": pattern.data,
                "confidence": pattern.confidence,
                "times_detected": pattern.times_detected,
                "created_at": pattern.created_at,
                "updated_at": pattern.updated_at
            } for pattern in patterns]
        except Exception as e:
            logger.error(f"Error getting patterns: {e}")
            return []
        finally:
            close_db()
    
    # Helper methods
    def _hash_token(self, token: str) -> str:
        """Create a secure hash of a token."""
        return hashlib.sha256(token.encode()).hexdigest()