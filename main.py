import sys
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the project directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Add nexus-ai-addon to the path
nexus_dir = os.path.join(current_dir, 'nexus-ai-addon')
if os.path.exists(nexus_dir):
    sys.path.insert(0, nexus_dir)
    logger.info(f"Added {nexus_dir} to Python path")
else:
    logger.warning(f"Directory not found: {nexus_dir}")

# Import the FastAPI app
try:
    from nexus.main import app
    logger.info("Successfully imported app from nexus.main")
except ImportError as e:
    logger.error(f"Failed to import app: {e}")
    
    # Try to diagnose the issue
    logger.info(f"Python path: {sys.path}")
    if os.path.exists(os.path.join(nexus_dir, 'nexus')):
        logger.info(f"Nexus directory exists at: {os.path.join(nexus_dir, 'nexus')}")
        if os.path.exists(os.path.join(nexus_dir, 'nexus', 'main.py')):
            logger.info(f"main.py exists at: {os.path.join(nexus_dir, 'nexus', 'main.py')}")
        else:
            logger.error(f"main.py not found in {os.path.join(nexus_dir, 'nexus')}")
    
    # Create a minimal app for diagnostics
    from fastapi import FastAPI
    app = FastAPI()
    
    @app.get("/")
    async def root():
        return {"message": "Diagnostic Mode - Failed to load Nexus AI application"}
    
    @app.get("/debug")
    async def debug():
        return {
            "python_path": sys.path,
            "current_dir": current_dir,
            "nexus_dir": nexus_dir,
            "nexus_exists": os.path.exists(nexus_dir),
            "nexus_main_exists": os.path.exists(os.path.join(nexus_dir, 'nexus', 'main.py')) if os.path.exists(os.path.join(nexus_dir, 'nexus')) else False
        }

# This variable is used by Gunicorn to access the FastAPI app
# The command: gunicorn main:app will look for this variable