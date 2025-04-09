import os
import sys
import hashlib
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Get the DATABASE_URL from environment variables
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is not set.")
    sys.exit(1)

print(f"Connecting to PostgreSQL database with URL: {DATABASE_URL}")

# Import our models
sys.path.append(os.path.abspath('.'))
from create_tables import (
    Base, Setting, HomeAssistantConfig, Entity, EntityState, 
    Automation, Memory, Pattern
)

# Create engine and session
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def hash_token(token):
    """Create a secure hash of a token."""
    return hashlib.sha256(token.encode()).hexdigest()

def add_demo_settings():
    """Add demo settings to the database."""
    print("Adding demo settings...")
    
    # Add some basic settings
    settings = [
        {"key": "nexus_version", "value": "0.1.0"},
        {"key": "setup_completed", "value": "true"},
        {"key": "ai_model", "value": "gpt-4o"},
        {"key": "voice_enabled", "value": "false"},
        {"key": "welcome_message", "value": "Welcome to Nexus AI, your intelligent home assistant!"}
    ]
    
    for setting_data in settings:
        # Check if setting exists
        existing = session.query(Setting).filter_by(key=setting_data["key"]).first()
        if existing:
            # Update existing
            existing.value = setting_data["value"]
        else:
            # Create new
            setting = Setting(
                key=setting_data["key"],
                value=setting_data["value"]
            )
            session.add(setting)
    
    session.commit()
    print("Demo settings added successfully.")
    
def add_demo_ha_config():
    """Add a demo Home Assistant configuration."""
    print("Adding demo Home Assistant configuration...")
    
    # Demo Home Assistant config
    ha_config = HomeAssistantConfig(
        url="http://homeassistant.local:8123",
        token_hash=hash_token("DEMO_TOKEN_NOT_REAL"),
        is_active=True,
        last_connected_at=datetime.utcnow(),
        version="2023.12.3",
        location_name="Demo Home"
    )
    
    session.add(ha_config)
    session.commit()
    print("Demo Home Assistant configuration added successfully.")
    
def add_demo_entities():
    """Add demo entities and entity states."""
    print("Adding demo entities and states...")
    
    # Demo entities
    entities = [
        {
            "entity_id": "light.living_room",
            "friendly_name": "Living Room Lights",
            "domain": "light",
            "is_important": True,
            "attributes": {"brightness": 255, "color_temp": 370, "supported_features": 63},
            "state": "on"
        },
        {
            "entity_id": "light.kitchen",
            "friendly_name": "Kitchen Lights",
            "domain": "light",
            "is_important": True,
            "attributes": {"brightness": 200, "color_temp": 400, "supported_features": 63},
            "state": "off"
        },
        {
            "entity_id": "switch.coffee_maker",
            "friendly_name": "Coffee Maker",
            "domain": "switch",
            "is_important": True,
            "attributes": {"friendly_name": "Coffee Maker", "icon": "mdi:coffee"},
            "state": "off"
        },
        {
            "entity_id": "sensor.temperature",
            "friendly_name": "Living Room Temperature",
            "domain": "sensor",
            "is_important": True,
            "attributes": {"unit_of_measurement": "°C", "device_class": "temperature"},
            "state": "21.5"
        },
        {
            "entity_id": "sensor.humidity",
            "friendly_name": "Living Room Humidity",
            "domain": "sensor",
            "is_important": False,
            "attributes": {"unit_of_measurement": "%", "device_class": "humidity"},
            "state": "45"
        },
        {
            "entity_id": "binary_sensor.motion",
            "friendly_name": "Living Room Motion",
            "domain": "binary_sensor",
            "is_important": True,
            "attributes": {"device_class": "motion"},
            "state": "off"
        },
        {
            "entity_id": "sensor.energy_consumption",
            "friendly_name": "Home Energy Consumption",
            "domain": "sensor",
            "is_important": True,
            "attributes": {"unit_of_measurement": "kWh", "device_class": "energy"},
            "state": "3.2"
        }
    ]
    
    # Current time for reference
    now = datetime.utcnow()
    
    for entity_data in entities:
        # Check if entity exists
        existing = session.query(Entity).filter_by(entity_id=entity_data["entity_id"]).first()
        
        if not existing:
            # Create entity
            entity = Entity(
                entity_id=entity_data["entity_id"],
                friendly_name=entity_data["friendly_name"],
                domain=entity_data["domain"],
                is_important=entity_data["is_important"],
                attributes=entity_data["attributes"],
                last_state=entity_data["state"],
                last_updated=now
            )
            session.add(entity)
            session.flush()  # Get the ID
            
            # Add some historical states (for the past 24 hours, every 2 hours)
            for i in range(12):
                time_offset = now - timedelta(hours=i*2)
                
                # Slight variations in state for sensors
                state = entity_data["state"]
                attributes = entity_data["attributes"].copy()
                
                if entity_data["domain"] == "sensor" and "unit_of_measurement" in attributes:
                    if attributes["unit_of_measurement"] == "°C":
                        # Temperature variations
                        state_val = float(entity_data["state"]) + (i % 3 - 1)
                        state = str(state_val)
                    elif attributes["unit_of_measurement"] == "%":
                        # Humidity variations
                        state_val = float(entity_data["state"]) + (i % 5 - 2)
                        state = str(state_val)
                    elif attributes["unit_of_measurement"] == "kWh":
                        # Energy variations
                        state_val = float(entity_data["state"]) + (i * 0.2)
                        state = str(state_val)
                
                # Binary sensor and switch/light states
                elif entity_data["domain"] in ["binary_sensor", "switch", "light"]:
                    # Alternate states
                    state = "on" if i % 2 == 0 else "off"
                    
                    if entity_data["domain"] == "light" and state == "on":
                        attributes["brightness"] = max(100, attributes.get("brightness", 255) - i * 10)
                
                state_record = EntityState(
                    entity_id=entity.id,
                    state=state,
                    attributes=attributes,
                    timestamp=time_offset
                )
                session.add(state_record)
        
    session.commit()
    print("Demo entities and states added successfully.")
    
def add_demo_automations():
    """Add demo automations."""
    print("Adding demo automations...")
    
    # Demo automations
    automations = [
        {
            "name": "Morning Routine",
            "description": "Turn on lights and start coffee maker in the morning",
            "triggers": [
                {"platform": "time", "at": "06:30:00"}
            ],
            "conditions": [
                {"condition": "time", "weekday": ["mon", "tue", "wed", "thu", "fri"]}
            ],
            "actions": [
                {"service": "light.turn_on", "target": {"entity_id": "light.kitchen"}},
                {"service": "switch.turn_on", "target": {"entity_id": "switch.coffee_maker"}}
            ],
            "is_suggested": False,
            "confidence": 1.0
        },
        {
            "name": "Evening Lights",
            "description": "Turn on living room lights at sunset",
            "triggers": [
                {"platform": "sun", "event": "sunset", "offset": "-00:30:00"}
            ],
            "conditions": [],
            "actions": [
                {"service": "light.turn_on", "target": {"entity_id": "light.living_room"}, 
                 "data": {"brightness": 200, "color_temp": 400}}
            ],
            "is_suggested": False,
            "confidence": 1.0
        },
        {
            "name": "Motion-Activated Lights",
            "description": "Turn on living room lights when motion is detected",
            "triggers": [
                {"platform": "state", "entity_id": "binary_sensor.motion", "to": "on"}
            ],
            "conditions": [
                {"condition": "sun", "after": "sunset", "before": "sunrise"}
            ],
            "actions": [
                {"service": "light.turn_on", "target": {"entity_id": "light.living_room"}}
            ],
            "is_suggested": False,
            "confidence": 1.0
        }
    ]
    
    # AI-suggested automations
    suggested_automations = [
        {
            "name": "Auto-Off Coffee Maker",
            "description": "Turn off coffee maker after 30 minutes",
            "triggers": [
                {"platform": "state", "entity_id": "switch.coffee_maker", "to": "on", "for": {"minutes": 30}}
            ],
            "conditions": [],
            "actions": [
                {"service": "switch.turn_off", "target": {"entity_id": "switch.coffee_maker"}}
            ],
            "is_suggested": True,
            "confidence": 0.87
        },
        {
            "name": "Energy-Saving Mode",
            "description": "Reduce brightness of lights when energy consumption is high",
            "triggers": [
                {"platform": "numeric_state", "entity_id": "sensor.energy_consumption", "above": 5}
            ],
            "conditions": [
                {"condition": "state", "entity_id": "light.living_room", "state": "on"}
            ],
            "actions": [
                {"service": "light.turn_on", "target": {"entity_id": "light.living_room"}, 
                 "data": {"brightness": 150}}
            ],
            "is_suggested": True,
            "confidence": 0.75
        }
    ]
    
    # Combine all automations
    all_automations = automations + suggested_automations
    
    for automation_data in all_automations:
        # Check if automation exists by name
        existing = session.query(Automation).filter_by(name=automation_data["name"]).first()
        
        if not existing:
            # Create automation
            automation = Automation(
                name=automation_data["name"],
                description=automation_data["description"],
                triggers=automation_data["triggers"],
                conditions=automation_data["conditions"],
                actions=automation_data["actions"],
                is_suggested=automation_data["is_suggested"],
                confidence=automation_data["confidence"],
                is_enabled=True,
                last_triggered=None if automation_data["is_suggested"] else datetime.utcnow() - timedelta(days=1)
            )
            session.add(automation)
    
    session.commit()
    print("Demo automations added successfully.")
    
def add_demo_memories():
    """Add demo memories."""
    print("Adding demo memories...")
    
    # Demo memories
    memories = [
        {
            "key": "user_preference.light_brightness",
            "value": "The user prefers their living room lights at 80% brightness in the evening.",
            "is_preference": True
        },
        {
            "key": "user_preference.temperature",
            "value": "The user prefers to keep their home at 21 degrees Celsius during the day.",
            "is_preference": True
        },
        {
            "key": "user_preference.coffee_time",
            "value": "The user typically makes coffee at 7:00 AM on weekdays.",
            "is_preference": True
        },
        {
            "key": "learned.daily_routine",
            "value": "The user typically leaves for work around 8:30 AM and returns around 6:00 PM on weekdays.",
            "is_preference": False
        },
        {
            "key": "learned.weekend_routine",
            "value": "The user typically sleeps in until 9:00 AM on weekends and spends more time in the living room.",
            "is_preference": False
        }
    ]
    
    for memory_data in memories:
        # Check if memory exists
        existing = session.query(Memory).filter_by(key=memory_data["key"]).first()
        
        if not existing:
            # Create memory
            memory = Memory(
                key=memory_data["key"],
                value=memory_data["value"],
                is_preference=memory_data["is_preference"],
                embedding_id=None  # We don't have actual embeddings for demo data
            )
            session.add(memory)
    
    session.commit()
    print("Demo memories added successfully.")
    
def add_demo_patterns():
    """Add demo patterns."""
    print("Adding demo patterns...")
    
    # Demo patterns
    patterns = [
        {
            "name": "Morning Light Pattern",
            "pattern_type": "time_based",
            "entities": ["light.kitchen"],
            "data": {
                "time": "07:00:00",
                "service": "light.turn_on",
                "repeat_days": ["mon", "tue", "wed", "thu", "fri"]
            },
            "confidence": 0.85,
            "times_detected": 15
        },
        {
            "name": "Coffee Consumption Pattern",
            "pattern_type": "time_based",
            "entities": ["switch.coffee_maker"],
            "data": {
                "time": "07:15:00",
                "service": "switch.turn_on",
                "repeat_days": ["mon", "tue", "wed", "thu", "fri"]
            },
            "confidence": 0.92,
            "times_detected": 20
        },
        {
            "name": "Evening Lighting Pattern",
            "pattern_type": "correlation",
            "entities": ["light.living_room", "binary_sensor.motion"],
            "data": {
                "trigger_entity": "binary_sensor.motion",
                "trigger_state": "on",
                "action_entity": "light.living_room",
                "action_service": "light.turn_on",
                "time_window": "18:00:00-23:00:00"
            },
            "confidence": 0.78,
            "times_detected": 12
        }
    ]
    
    for pattern_data in patterns:
        # Check if pattern exists
        existing = session.query(Pattern).filter_by(name=pattern_data["name"]).first()
        
        if not existing:
            # Create pattern
            pattern = Pattern(
                name=pattern_data["name"],
                pattern_type=pattern_data["pattern_type"],
                entities=pattern_data["entities"],
                data=pattern_data["data"],
                confidence=pattern_data["confidence"],
                times_detected=pattern_data["times_detected"]
            )
            session.add(pattern)
    
    session.commit()
    print("Demo patterns added successfully.")

def main():
    """Add all demo data."""
    try:
        add_demo_settings()
        add_demo_ha_config()
        add_demo_entities()
        add_demo_automations()
        add_demo_memories()
        add_demo_patterns()
        
        print("\nAll demo data has been added successfully!")
    except Exception as e:
        print(f"Error adding demo data: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main()