import os
import logging
import time
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

from openai_helper import OpenAIHelper

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI helper
openai_helper = OpenAIHelper()

# Define base model class
class Base(DeclarativeBase):
    pass

# Create SQLAlchemy extension instance
db = SQLAlchemy(model_class=Base)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "nexus-ai-secret-key")

# Configure database connection
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize SQLAlchemy with the Flask app
db.init_app(app)

# Models
class Setting(db.Model):
    """Store application settings."""
    __tablename__ = "settings"
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(255), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Setting {self.key}={self.value}>"

class HomeAssistantConfig(db.Model):
    """Store Home Assistant configuration."""
    __tablename__ = "ha_config"
    
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(255), nullable=False)
    token_hash = db.Column(db.String(255), nullable=False)  # Store hash of token, never the token itself
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_connected_at = db.Column(db.DateTime, nullable=True)
    version = db.Column(db.String(50), nullable=True)
    location_name = db.Column(db.String(255), nullable=True)
    
    def __repr__(self):
        return f"<HomeAssistantConfig {self.url}>"

class Entity(db.Model):
    """Store Home Assistant entity information."""
    __tablename__ = "entities"
    
    id = db.Column(db.Integer, primary_key=True)
    entity_id = db.Column(db.String(255), unique=True, nullable=False)
    friendly_name = db.Column(db.String(255), nullable=True)
    domain = db.Column(db.String(50), nullable=False)  # light, switch, sensor, etc.
    is_important = db.Column(db.Boolean, default=False)
    attributes = db.Column(db.JSON, nullable=True)
    last_state = db.Column(db.String(255), nullable=True)
    last_updated = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    state_history = db.relationship("EntityState", back_populates="entity", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Entity {self.entity_id}={self.last_state}>"

class EntityState(db.Model):
    """Store historical states of entities for pattern analysis."""
    __tablename__ = "entity_states"
    
    id = db.Column(db.Integer, primary_key=True)
    entity_id = db.Column(db.Integer, db.ForeignKey("entities.id"), nullable=False)
    state = db.Column(db.String(255), nullable=False)
    attributes = db.Column(db.JSON, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    entity = db.relationship("Entity", back_populates="state_history")
    
    def __repr__(self):
        return f"<EntityState {self.entity_id}={self.state} @ {self.timestamp}>"

class Automation(db.Model):
    """Store automation configurations."""
    __tablename__ = "automations"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    entity_id = db.Column(db.String(255), nullable=True)  # Link to Home Assistant entity ID if available
    description = db.Column(db.Text, nullable=True)
    triggers = db.Column(db.JSON, nullable=False)
    conditions = db.Column(db.JSON, nullable=True)
    actions = db.Column(db.JSON, nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    is_suggested = db.Column(db.Boolean, default=False)
    confidence = db.Column(db.Float, default=0.0)  # For AI-suggested automations
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_triggered = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Automation {self.name}>"

class Memory(db.Model):
    """Store memory items with support for semantic search."""
    __tablename__ = "memories"
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(255), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    embedding_id = db.Column(db.String(255), nullable=True)  # ID in vector store
    is_preference = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Memory {self.key}>"

class Pattern(db.Model):
    """Store detected usage patterns for smart suggestions."""
    __tablename__ = "patterns"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    pattern_type = db.Column(db.String(50), nullable=False)  # time-based, correlation, presence, etc.
    entities = db.Column(db.JSON, nullable=False)  # List of entity IDs involved in the pattern
    data = db.Column(db.JSON, nullable=False)  # Pattern specific data
    confidence = db.Column(db.Float, default=0.0)
    times_detected = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Pattern {self.name}>"

# Set static folder
app.static_folder = 'static'

# Routes
@app.route('/')
def index():
    """Serve the dashboard."""
    return render_template('dashboard.html')

@app.route('/dashboard')
def dashboard():
    """Serve the dashboard."""
    return render_template('dashboard.html')

@app.route('/automations')
def automations():
    """Serve the automations page."""
    return render_template('dashboard.html')  # We'll create a proper template later

@app.route('/entities')
def entities():
    """Serve the entities page."""
    return render_template('dashboard.html')  # We'll create a proper template later

@app.route('/settings')
def settings():
    """Serve the settings page."""
    return render_template('dashboard.html')  # We'll create a proper template later

@app.route('/static/<path:path>')
def serve_static(path):
    """Serve static files from the static directory."""
    return app.send_static_file(path)

@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "online"})

@app.route('/api/settings')
def get_settings():
    """Get all settings."""
    settings = Setting.query.all()
    result = {}
    for s in settings:
        result[s.key] = s.value
    return jsonify({"settings": result})

@app.route('/api/settings/<key>', methods=['GET'])
def get_setting(key):
    """Get a specific setting by key."""
    setting = Setting.query.filter_by(key=key).first()
    if setting:
        return jsonify({"key": setting.key, "value": setting.value})
    return jsonify({"error": "Setting not found"}), 404

@app.route('/api/settings', methods=['POST'])
def save_setting():
    """Save a setting."""
    data = request.json
    if not data or 'key' not in data or 'value' not in data:
        return jsonify({"error": "Invalid request"}), 400
    
    key = data['key']
    value = data['value']
    
    setting = Setting.query.filter_by(key=key).first()
    if setting:
        setting.value = value
    else:
        setting = Setting(key=key, value=value)
        db.session.add(setting)
    
    db.session.commit()
    return jsonify({"success": True, "key": key, "value": value})

@app.route('/api/entities')
def get_entities():
    """Get all entities with optional filtering."""
    domain = request.args.get('domain')
    important_only = request.args.get('important_only', 'false').lower() == 'true'
    
    query = Entity.query
    
    if domain:
        query = query.filter_by(domain=domain)
    
    if important_only:
        query = query.filter_by(is_important=True)
    
    entities = query.all()
    result = []
    
    for entity in entities:
        result.append({
            "id": entity.id,
            "entity_id": entity.entity_id,
            "friendly_name": entity.friendly_name,
            "domain": entity.domain,
            "is_important": entity.is_important,
            "attributes": entity.attributes,
            "last_state": entity.last_state,
            "last_updated": entity.last_updated.isoformat() if entity.last_updated else None
        })
    
    return jsonify({"entities": result})

@app.route('/api/entities/<entity_id>')
def get_entity(entity_id):
    """Get a specific entity by ID."""
    entity = Entity.query.filter_by(entity_id=entity_id).first()
    if not entity:
        return jsonify({"error": "Entity not found"}), 404
    
    result = {
        "id": entity.id,
        "entity_id": entity.entity_id,
        "friendly_name": entity.friendly_name,
        "domain": entity.domain,
        "is_important": entity.is_important,
        "attributes": entity.attributes,
        "last_state": entity.last_state,
        "last_updated": entity.last_updated.isoformat() if entity.last_updated else None
    }
    
    return jsonify(result)

@app.route('/api/entities/<entity_id>/history')
def get_entity_history(entity_id):
    """Get the history for a specific entity."""
    limit = request.args.get('limit', 100, type=int)
    
    entity = Entity.query.filter_by(entity_id=entity_id).first()
    if not entity:
        return jsonify({"error": "Entity not found"}), 404
    
    states = EntityState.query.filter_by(entity_id=entity.id).order_by(
        EntityState.timestamp.desc()).limit(limit).all()
    
    result = []
    for state in states:
        result.append({
            "state": state.state,
            "attributes": state.attributes,
            "timestamp": state.timestamp.isoformat()
        })
    
    return jsonify({"entity_id": entity_id, "history": result})

@app.route('/api/automations')
def get_automations():
    """Get all automations with optional filtering."""
    suggested_only = request.args.get('suggested_only', 'false').lower() == 'true'
    
    query = Automation.query
    
    if suggested_only:
        query = query.filter_by(is_suggested=True)
    
    automations = query.all()
    result = []
    
    for automation in automations:
        result.append({
            "id": automation.id,
            "name": automation.name,
            "entity_id": automation.entity_id,
            "description": automation.description,
            "triggers": automation.triggers,
            "conditions": automation.conditions,
            "actions": automation.actions,
            "is_enabled": automation.is_enabled,
            "is_suggested": automation.is_suggested,
            "confidence": automation.confidence,
            "created_at": automation.created_at.isoformat(),
            "last_triggered": automation.last_triggered.isoformat() if automation.last_triggered else None
        })
    
    return jsonify({"automations": result})

@app.route('/api/memories')
def get_memories():
    """Get all memories with optional filtering."""
    preferences_only = request.args.get('preferences_only', 'false').lower() == 'true'
    
    query = Memory.query
    
    if preferences_only:
        query = query.filter_by(is_preference=True)
    
    memories = query.all()
    result = []
    
    for memory in memories:
        result.append({
            "id": memory.id,
            "key": memory.key,
            "value": memory.value,
            "is_preference": memory.is_preference,
            "created_at": memory.created_at.isoformat(),
            "updated_at": memory.updated_at.isoformat()
        })
    
    return jsonify({"memories": result})

@app.route('/api/patterns')
def get_patterns():
    """Get all detected patterns with optional filtering."""
    pattern_type = request.args.get('pattern_type')
    min_confidence = request.args.get('min_confidence', 0.0, type=float)
    
    query = Pattern.query.filter(Pattern.confidence >= min_confidence)
    
    if pattern_type:
        query = query.filter_by(pattern_type=pattern_type)
    
    patterns = query.all()
    result = []
    
    for pattern in patterns:
        result.append({
            "id": pattern.id,
            "name": pattern.name,
            "pattern_type": pattern.pattern_type,
            "entities": pattern.entities,
            "data": pattern.data,
            "confidence": pattern.confidence,
            "times_detected": pattern.times_detected,
            "created_at": pattern.created_at.isoformat(),
            "updated_at": pattern.updated_at.isoformat()
        })
    
    return jsonify({"patterns": result})

@app.route('/api/ask', methods=['POST'])
def ask():
    """Process a natural language request through the OpenAI agent."""
    try:
        data = request.json
        if not data or 'prompt' not in data:
            return jsonify({"error": "Invalid request. 'prompt' is required."}), 400
        
        prompt = data['prompt']
        context = data.get('context', {})
        
        # Prepare context with relevant data from the database
        if not context:
            context = {}
            
            # Add important entities
            important_entities = Entity.query.filter_by(is_important=True).all()
            if important_entities:
                context['entities'] = [
                    {
                        "entity_id": entity.entity_id,
                        "friendly_name": entity.friendly_name,
                        "domain": entity.domain,
                        "last_state": entity.last_state
                    }
                    for entity in important_entities
                ]
            
            # Add relevant memories
            preference_memories = Memory.query.filter_by(is_preference=True).all()
            if preference_memories:
                context['memories'] = [
                    {
                        "key": memory.key,
                        "value": memory.value
                    }
                    for memory in preference_memories
                ]
            
            # Add patterns with high confidence
            high_confidence_patterns = Pattern.query.filter(Pattern.confidence >= 0.7).all()
            if high_confidence_patterns:
                context['patterns'] = [
                    {
                        "name": pattern.name,
                        "pattern_type": pattern.pattern_type,
                        "confidence": pattern.confidence
                    }
                    for pattern in high_confidence_patterns
                ]
        
        # Process the query
        response = openai_helper.process_query(prompt, context)
        
        # Save the query as a memory
        memory_key = f"query_{int(time.time())}"
        memory = Memory(key=memory_key, value=prompt, is_preference=False)
        db.session.add(memory)
        db.session.commit()
        
        return jsonify({"response": response})
    
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return jsonify({"error": f"Failed to process query: {str(e)}"}), 500

# Create all tables in the database
with app.app_context():
    db.create_all()
    
    # Add default settings if they don't exist
    default_settings = {
        "version": "0.1.0",
        "initialized_at": datetime.utcnow().isoformat(),
        "theme": "dark",
        "log_level": "info",
        "max_history_items": "100",
        "pattern_detection_enabled": "true",
        "suggestion_threshold": "0.7"
    }
    
    for key, value in default_settings.items():
        if not Setting.query.filter_by(key=key).first():
            db.session.add(Setting(key=key, value=value))
    
    db.session.commit()

# This is used by Gunicorn to find the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)