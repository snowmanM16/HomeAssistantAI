import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Get the DATABASE_URL from environment variables
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is not set.")
    sys.exit(1)

print(f"Initializing database connection to PostgreSQL with URL: {DATABASE_URL}")

# Create base class for declarative models
Base = declarative_base()

# Import models - these will be added to the Base.metadata
sys.path.append(os.path.abspath('.'))
from nexus-ai-addon.nexus.models import (
    Setting, HomeAssistantConfig, Entity, EntityState, 
    Automation, Memory, Pattern
)

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