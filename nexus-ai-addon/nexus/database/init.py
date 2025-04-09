"""
Database initialization module for Nexus AI
"""
import logging
import os
from pathlib import Path
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path so we can import from the parent package
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import after path setup
from database import DatabaseService

def init_database():
    """Initialize the database."""
    try:
        # Create database service instance (which initializes tables)
        db = DatabaseService()
        
        # Add default settings if they don't exist
        init_default_settings(db)
        
        logger.info("Database initialization complete")
        return db
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        sys.exit(1)

def init_default_settings(db):
    """Initialize default settings."""
    default_settings = {
        "version": "0.1.0",
        "initialized_at": "2024-04-01T00:00:00Z",
        "theme": "dark",
        "log_level": "info",
        "max_history_items": "100",
        "pattern_detection_enabled": "true",
        "suggestion_threshold": "0.7"
    }
    
    for key, value in default_settings.items():
        if db.get_setting(key) is None:
            db.set_setting(key, value)
            logger.info(f"Added default setting: {key}={value}")

if __name__ == "__main__":
    # Run database initialization when module is executed directly
    init_database()