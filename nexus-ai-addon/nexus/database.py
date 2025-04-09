"""
Database service for Nexus AI
"""
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import json

from sqlalchemy.orm import Session
from .models import (
    Setting, HomeAssistantConfig, Entity, EntityState,
    Automation, Memory, Pattern, init_db
)

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for interacting with the database."""
    
    def __init__(self):
        """Initialize the database service."""
        self.session = init_db()
    
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a setting value by key."""
        setting = self.session.query(Setting).filter(Setting.key == key).first()
        return setting.value if setting else default
    
    def set_setting(self, key: str, value: str) -> bool:
        """Set a setting value."""
        try:
            setting = self.session.query(Setting).filter(Setting.key == key).first()
            if setting:
                setting.value = value
                setting.updated_at = datetime.utcnow()
            else:
                setting = Setting(key=key, value=value)
                self.session.add(setting)
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting {key}: {e}")
            self.session.rollback()
            return False
    
    def get_all_settings(self) -> Dict[str, str]:
        """Get all settings as a dictionary."""
        settings = self.session.query(Setting).all()
        return {s.key: s.value for s in settings}
    
    def save_ha_config(self, url: str, token: str) -> bool:
        """Save Home Assistant configuration with token hash."""
        try:
            # Deactivate any existing configs
            self.session.query(HomeAssistantConfig).update({"is_active": False})
            
            # Create new config
            token_hash = self._hash_token(token)
            config = HomeAssistantConfig(
                url=url,
                token_hash=token_hash,
                is_active=True
            )
            self.session.add(config)
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving HA config: {e}")
            self.session.rollback()
            return False
    
    def get_active_ha_config(self) -> Optional[Dict[str, Any]]:
        """Get the active Home Assistant configuration."""
        config = self.session.query(HomeAssistantConfig).filter(HomeAssistantConfig.is_active == True).first()
        if not config:
            return None
        
        return {
            "id": config.id,
            "url": config.url,
            "is_active": config.is_active,
            "last_connected_at": config.last_connected_at,
            "version": config.version,
            "location_name": config.location_name,
            "created_at": config.created_at
        }
    
    def update_ha_connection_status(self, version: Optional[str] = None, location_name: Optional[str] = None) -> bool:
        """Update Home Assistant connection status."""
        try:
            config = self.session.query(HomeAssistantConfig).filter(HomeAssistantConfig.is_active == True).first()
            if not config:
                return False
            
            config.last_connected_at = datetime.utcnow()
            if version:
                config.version = version
            if location_name:
                config.location_name = location_name
            
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating HA connection status: {e}")
            self.session.rollback()
            return False
    
    def verify_ha_token(self, token: str) -> bool:
        """Verify if a token matches the stored hash."""
        config = self.session.query(HomeAssistantConfig).filter(HomeAssistantConfig.is_active == True).first()
        if not config:
            return False
        
        token_hash = self._hash_token(token)
        return token_hash == config.token_hash
    
    def save_entity(self, entity_id: str, friendly_name: Optional[str], domain: str, 
                    state: str, attributes: Dict[str, Any], is_important: bool = False) -> bool:
        """Save or update an entity and its state."""
        try:
            entity = self.session.query(Entity).filter(Entity.entity_id == entity_id).first()
            
            # Update or create entity
            if entity:
                entity.friendly_name = friendly_name
                entity.domain = domain
                entity.last_state = state
                entity.attributes = attributes
                entity.last_updated = datetime.utcnow()
                entity.is_important = is_important
            else:
                entity = Entity(
                    entity_id=entity_id,
                    friendly_name=friendly_name,
                    domain=domain,
                    last_state=state,
                    attributes=attributes,
                    is_important=is_important
                )
                self.session.add(entity)
                self.session.flush()  # Flush to get the entity ID
            
            # Add state history
            entity_state = EntityState(
                entity_id=entity.id,
                state=state,
                attributes=attributes
            )
            self.session.add(entity_state)
            
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving entity {entity_id}: {e}")
            self.session.rollback()
            return False
    
    def get_entities(self, domain: Optional[str] = None, important_only: bool = False) -> List[Dict[str, Any]]:
        """Get entities with optional filtering."""
        query = self.session.query(Entity)
        
        if domain:
            query = query.filter(Entity.domain == domain)
        
        if important_only:
            query = query.filter(Entity.is_important == True)
        
        entities = query.all()
        return [
            {
                "id": e.id,
                "entity_id": e.entity_id,
                "friendly_name": e.friendly_name,
                "domain": e.domain,
                "last_state": e.last_state,
                "attributes": e.attributes,
                "is_important": e.is_important,
                "last_updated": e.last_updated
            }
            for e in entities
        ]
    
    def get_entity_history(self, entity_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get history for a specific entity."""
        entity = self.session.query(Entity).filter(Entity.entity_id == entity_id).first()
        if not entity:
            return []
        
        states = (
            self.session.query(EntityState)
            .filter(EntityState.entity_id == entity.id)
            .order_by(EntityState.timestamp.desc())
            .limit(limit)
            .all()
        )
        
        return [
            {
                "state": s.state,
                "attributes": s.attributes,
                "timestamp": s.timestamp
            }
            for s in states
        ]
    
    def save_automation(self, name: str, triggers: List[Dict[str, Any]], 
                      actions: List[Dict[str, Any]], entity_id: Optional[str] = None,
                      description: Optional[str] = None, conditions: Optional[List[Dict[str, Any]]] = None,
                      is_suggested: bool = False, confidence: float = 0.0) -> Optional[int]:
        """Save a new automation."""
        try:
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
            self.session.add(automation)
            self.session.commit()
            return automation.id
        except Exception as e:
            logger.error(f"Error saving automation {name}: {e}")
            self.session.rollback()
            return None
    
    def get_automations(self, suggested_only: bool = False) -> List[Dict[str, Any]]:
        """Get all automations with optional filtering."""
        query = self.session.query(Automation)
        
        if suggested_only:
            query = query.filter(Automation.is_suggested == True)
        
        automations = query.all()
        return [
            {
                "id": a.id,
                "name": a.name,
                "entity_id": a.entity_id,
                "description": a.description,
                "triggers": a.triggers,
                "conditions": a.conditions,
                "actions": a.actions,
                "is_enabled": a.is_enabled,
                "is_suggested": a.is_suggested,
                "confidence": a.confidence,
                "last_triggered": a.last_triggered
            }
            for a in automations
        ]
    
    def update_automation_status(self, automation_id: int, is_enabled: bool) -> bool:
        """Enable or disable an automation."""
        try:
            automation = self.session.query(Automation).get(automation_id)
            if not automation:
                return False
            
            automation.is_enabled = is_enabled
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating automation status: {e}")
            self.session.rollback()
            return False
    
    def record_automation_trigger(self, automation_id: int) -> bool:
        """Record that an automation was triggered."""
        try:
            automation = self.session.query(Automation).get(automation_id)
            if not automation:
                return False
            
            automation.last_triggered = datetime.utcnow()
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error recording automation trigger: {e}")
            self.session.rollback()
            return False
    
    def save_memory(self, key: str, value: str, embedding_id: Optional[str] = None, is_preference: bool = False) -> bool:
        """Save a memory item."""
        try:
            memory = self.session.query(Memory).filter(Memory.key == key).first()
            
            if memory:
                memory.value = value
                memory.embedding_id = embedding_id if embedding_id else memory.embedding_id
                memory.is_preference = is_preference
                memory.updated_at = datetime.utcnow()
            else:
                memory = Memory(
                    key=key,
                    value=value,
                    embedding_id=embedding_id,
                    is_preference=is_preference
                )
                self.session.add(memory)
            
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving memory {key}: {e}")
            self.session.rollback()
            return False
    
    def get_memory(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a memory item by key."""
        memory = self.session.query(Memory).filter(Memory.key == key).first()
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
    
    def get_all_memories(self, preferences_only: bool = False) -> List[Dict[str, Any]]:
        """Get all memory items."""
        query = self.session.query(Memory)
        
        if preferences_only:
            query = query.filter(Memory.is_preference == True)
        
        memories = query.all()
        return [
            {
                "id": m.id,
                "key": m.key,
                "value": m.value,
                "embedding_id": m.embedding_id,
                "is_preference": m.is_preference,
                "created_at": m.created_at,
                "updated_at": m.updated_at
            }
            for m in memories
        ]
    
    def delete_memory(self, key: str) -> bool:
        """Delete a memory item."""
        try:
            memory = self.session.query(Memory).filter(Memory.key == key).first()
            if not memory:
                return False
            
            self.session.delete(memory)
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting memory {key}: {e}")
            self.session.rollback()
            return False
    
    def save_pattern(self, name: str, pattern_type: str, entities: List[str], 
                    data: Dict[str, Any], confidence: float = 0.0) -> Optional[int]:
        """Save a detected pattern."""
        try:
            pattern = self.session.query(Pattern).filter(Pattern.name == name).first()
            
            if pattern:
                pattern.pattern_type = pattern_type
                pattern.entities = entities
                pattern.data = data
                pattern.confidence = max(pattern.confidence, confidence)
                pattern.times_detected += 1
                pattern.updated_at = datetime.utcnow()
            else:
                pattern = Pattern(
                    name=name,
                    pattern_type=pattern_type,
                    entities=entities,
                    data=data,
                    confidence=confidence
                )
                self.session.add(pattern)
            
            self.session.commit()
            return pattern.id
        except Exception as e:
            logger.error(f"Error saving pattern {name}: {e}")
            self.session.rollback()
            return None
    
    def get_patterns(self, pattern_type: Optional[str] = None, min_confidence: float = 0.0) -> List[Dict[str, Any]]:
        """Get patterns with optional filtering."""
        query = self.session.query(Pattern).filter(Pattern.confidence >= min_confidence)
        
        if pattern_type:
            query = query.filter(Pattern.pattern_type == pattern_type)
        
        patterns = query.all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "pattern_type": p.pattern_type,
                "entities": p.entities,
                "data": p.data,
                "confidence": p.confidence,
                "times_detected": p.times_detected,
                "created_at": p.created_at,
                "updated_at": p.updated_at
            }
            for p in patterns
        ]
    
    def _hash_token(self, token: str) -> str:
        """Create a secure hash of a token."""
        return hashlib.sha256(token.encode()).hexdigest()
