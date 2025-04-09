"""
Database models for Nexus AI
"""
import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, 
    Text, DateTime, ForeignKey, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()

class Setting(Base):
    """Store application settings."""
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Setting {self.key}={self.value}>"

class HomeAssistantConfig(Base):
    """Store Home Assistant configuration."""
    __tablename__ = "ha_config"
    
    id = Column(Integer, primary_key=True)
    url = Column(String(255), nullable=False)
    token_hash = Column(String(255), nullable=False)  # Store hash of token, never the token itself
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_connected_at = Column(DateTime, nullable=True)
    version = Column(String(50), nullable=True)
    location_name = Column(String(255), nullable=True)
    
    def __repr__(self):
        return f"<HomeAssistantConfig {self.url}>"

class Entity(Base):
    """Store Home Assistant entity information."""
    __tablename__ = "entities"
    
    id = Column(Integer, primary_key=True)
    entity_id = Column(String(255), unique=True, nullable=False)
    friendly_name = Column(String(255), nullable=True)
    domain = Column(String(50), nullable=False)  # light, switch, sensor, etc.
    is_important = Column(Boolean, default=False)
    attributes = Column(JSON, nullable=True)
    last_state = Column(String(255), nullable=True)
    last_updated = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    state_history = relationship("EntityState", back_populates="entity", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Entity {self.entity_id}={self.last_state}>"

class EntityState(Base):
    """Store historical states of entities for pattern analysis."""
    __tablename__ = "entity_states"
    
    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)
    state = Column(String(255), nullable=False)
    attributes = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    entity = relationship("Entity", back_populates="state_history")
    
    def __repr__(self):
        return f"<EntityState {self.entity_id}={self.state} @ {self.timestamp}>"

class Automation(Base):
    """Store automation configurations."""
    __tablename__ = "automations"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    entity_id = Column(String(255), nullable=True)  # Link to Home Assistant entity ID if available
    description = Column(Text, nullable=True)
    triggers = Column(JSON, nullable=False)
    conditions = Column(JSON, nullable=True)
    actions = Column(JSON, nullable=False)
    is_enabled = Column(Boolean, default=True)
    is_suggested = Column(Boolean, default=False)
    confidence = Column(Float, default=0.0)  # For AI-suggested automations
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_triggered = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Automation {self.name}>"

class Memory(Base):
    """Store memory items with support for semantic search."""
    __tablename__ = "memories"
    
    id = Column(Integer, primary_key=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    embedding_id = Column(String(255), nullable=True)  # ID in vector store
    is_preference = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Memory {self.key}>"

class Pattern(Base):
    """Store detected usage patterns for smart suggestions."""
    __tablename__ = "patterns"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    pattern_type = Column(String(50), nullable=False)  # time-based, correlation, presence, etc.
    entities = Column(JSON, nullable=False)  # List of entity IDs involved in the pattern
    data = Column(JSON, nullable=False)  # Pattern specific data
    confidence = Column(Float, default=0.0)
    times_detected = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Pattern {self.name}>"

# Database initialization function
def init_db():
    """Initialize the database engine and create tables if they don't exist."""
    db_url = os.environ.get("DATABASE_URL")
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()
