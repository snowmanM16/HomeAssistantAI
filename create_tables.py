import os
import sys
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime

# Get the DATABASE_URL from environment variables
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is not set.")
    sys.exit(1)

print(f"Initializing database connection to PostgreSQL with URL: {DATABASE_URL}")

# Create base class for declarative models
Base = declarative_base()

# Define models directly
class Setting(Base):
    """Store application settings."""
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Setting {self.key}>"

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
        return f"<Entity {self.entity_id}>"

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
        return f"<EntityState {self.entity_id} {self.state} at {self.timestamp}>"

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

# Create engine and session
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def init_db():
    """Create all tables in the database."""
    print("Creating database tables...")
    Base.metadata.create_all(engine)
    print("Database tables created successfully.")

def test_db():
    """Test database connection by adding and querying a setting."""
    session = Session()
    try:
        # Add a test setting
        test_setting = Setting(key="db_test", value="Database connection successful")
        session.add(test_setting)
        session.commit()
        
        # Query the setting back
        result = session.query(Setting).filter_by(key="db_test").first()
        print(f"Test setting retrieved: {result.key} = {result.value}")
        
        return True
    except Exception as e:
        print(f"Error testing database: {e}")
        return False
    finally:
        session.close()

if __name__ == "__main__":
    try:
        init_db()
        if test_db():
            print("Database setup and test completed successfully.")
        else:
            print("Database test failed.")
    except Exception as e:
        print(f"Error setting up database: {e}")