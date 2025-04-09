import os
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import asyncio
import json
from typing import Dict, Any, List, Optional

# Import Nexus modules
from nexus.agent import NexusAgent
from nexus.memory import MemoryManager
from nexus.ha_api import HomeAssistantAPI
from nexus.calendar import GoogleCalendar
from nexus.voice.stt import SpeechToText
from nexus.voice.tts import TextToSpeech
from nexus.tools.automation import AutomationTool

# Configure logging
log_level = os.getenv("LOG_LEVEL", "info").upper()
numeric_level = getattr(logging, log_level, logging.INFO)

# Create logs directory if it doesn't exist
logs_dir = os.getenv("LOGS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'logs'))
os.makedirs(logs_dir, exist_ok=True)
log_file = os.path.join(logs_dir, 'nexus.log')

logging.basicConfig(
    level=numeric_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Add file handler if we can write to the log file
try:
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)
except Exception as e:
    print(f"Warning: Unable to write to log file {log_file}: {e}")

logger = logging.getLogger("nexus")

# Define API request/response models
class AskRequest(BaseModel):
    prompt: str
    context: Optional[Dict[str, Any]] = None

class ActionRequest(BaseModel):
    domain: str
    service: str
    data: Optional[Dict[str, Any]] = None

class MemoryRequest(BaseModel):
    key: str
    value: str

# Initialize components with development-friendly paths
# Create data directories if they don't exist
data_dir = os.getenv("DATA_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data'))
os.makedirs(os.path.join(data_dir, 'db'), exist_ok=True)
os.makedirs(os.path.join(data_dir, 'chromadb'), exist_ok=True)

memory_manager = MemoryManager(
    db_path=os.path.join(data_dir, 'db', 'memory.db'),
    chroma_path=os.path.join(data_dir, 'chromadb')
)
ha_api = HomeAssistantAPI()

# Initialize optional components based on configuration
voice_enabled = os.getenv("VOICE_ENABLED", "false").lower() == "true"
if voice_enabled:
    stt = SpeechToText()
    tts = TextToSpeech()
    logger.info("Voice processing enabled")
else:
    stt = None
    tts = None
    logger.info("Voice processing disabled")

google_calendar_enabled = os.getenv("GOOGLE_CALENDAR_ENABLED", "false").lower() == "true"
if google_calendar_enabled:
    try:
        calendar = GoogleCalendar()
        logger.info("Google Calendar integration enabled")
    except Exception as e:
        logger.error(f"Failed to initialize Google Calendar: {e}")
        calendar = None
else:
    calendar = None
    logger.info("Google Calendar integration disabled")

# Initialize the AI agent with all components
agent = NexusAgent(
    memory=memory_manager,
    ha_api=ha_api,
    calendar=calendar,
    stt=stt,
    tts=tts
)

# Initialize the automation tool
automation_tool = AutomationTool(ha_api)

# Create FastAPI app
app = FastAPI(
    title="Nexus AI",
    description="Autonomous AI assistant with memory and smart control for Home Assistant",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the static directory path in a development-friendly way
static_dir = os.getenv("STATIC_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'))
logger.info(f"Using static directory: {static_dir}")

# Mount static files for the web interface
try:
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
except Exception as e:
    logger.error(f"Failed to mount static directory: {e}")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the web interface."""
    try:
        # Try to serve the modern UI first
        modern_ui_path = os.path.join(static_dir, 'modern-ui.html')
        if os.path.exists(modern_ui_path):
            logger.info(f"Serving modern UI from: {modern_ui_path}")
            with open(modern_ui_path, "r") as f:
                return f.read()
        
        # Fall back to legacy UI if modern UI is not available
        index_path = os.path.join(static_dir, 'index.html')
        logger.info(f"Serving legacy UI from: {index_path}")
        with open(index_path, "r") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to serve UI: {e}")
        return HTMLResponse("<html><body><h1>Nexus AI</h1><p>Error: Failed to load web interface</p></body></html>")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}

@app.post("/ask")
async def ask(request: AskRequest):
    """Process a natural language request through the AI agent."""
    try:
        logger.info(f"Processing request: {request.prompt[:50]}...")
        response = await agent.process_query(request.prompt, request.context)
        return {"response": response}
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/action")
async def action(request: ActionRequest):
    """Execute a Home Assistant service."""
    try:
        logger.info(f"Calling service: {request.domain}.{request.service}")
        result = await ha_api.call_service(
            domain=request.domain, 
            service=request.service, 
            data=request.data or {}
        )
        return {"result": result}
    except Exception as e:
        logger.error(f"Error calling service: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/calendar")
async def get_calendar():
    """Get events from Google Calendar."""
    if not calendar:
        raise HTTPException(status_code=503, detail="Google Calendar integration not enabled")
    
    try:
        events = await calendar.get_today_events()
        return {"events": events}
    except Exception as e:
        logger.error(f"Error getting calendar events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory")
async def save_to_memory(request: MemoryRequest):
    """Save a key-value pair to memory."""
    try:
        memory_manager.save_memory(request.key, request.value)
        return {"status": "saved", "key": request.key}
    except Exception as e:
        logger.error(f"Error saving to memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memory/{key}")
async def get_from_memory(key: str):
    """Retrieve a value from memory by key."""
    try:
        value = memory_manager.recall(key)
        if value is None:
            raise HTTPException(status_code=404, detail=f"Key '{key}' not found in memory")
        return {"key": key, "value": value}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving from memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memory/search")
async def search_memory(query: str):
    """Search memory for similar content."""
    try:
        results = memory_manager.search(query)
        return {"results": results}
    except Exception as e:
        logger.error(f"Error searching memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/voice/transcribe")
async def transcribe_audio(request: Request):
    """Transcribe audio to text."""
    if not voice_enabled:
        raise HTTPException(status_code=503, detail="Voice processing not enabled")
    
    try:
        data = await request.body()
        text = await stt.transcribe(data)
        return {"text": text}
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/voice/synthesize")
async def synthesize_speech(request: Request):
    """Convert text to speech."""
    if not voice_enabled:
        raise HTTPException(status_code=503, detail="Voice processing not enabled")
    
    try:
        data = await request.json()
        text = data.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="No text provided")
        
        audio_data = await tts.synthesize(text)
        return JSONResponse(content={"audio": audio_data})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error synthesizing speech: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Define model for HA configuration
class HAConfigRequest(BaseModel):
    url: str
    token: str

# Define model for creating automations
class AutomationRequest(BaseModel):
    name: str
    triggers: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    conditions: Optional[List[Dict[str, Any]]] = None

@app.post("/ha/configure")
async def configure_home_assistant(request: HAConfigRequest):
    """Configure the Home Assistant API connection."""
    try:
        logger.info(f"Configuring Home Assistant API with URL: {request.url}")
        ha_api.configure(url=request.url, token=request.token)
        
        # Test the connection
        connection_status = await ha_api.check_connection()
        
        if connection_status.get("connected", False):
            # Save the configuration to memory for persistence
            memory_manager.save_preference("ha_url", request.url)
            # Don't save the token directly for security; use a hash or other mechanism if needed
            memory_manager.save_preference("ha_configured", "true")
            
            return {"status": "configured", "connection": connection_status}
        else:
            return {"status": "error", "connection": connection_status}
    except Exception as e:
        logger.error(f"Error configuring Home Assistant: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ha/status")
async def check_home_assistant_status():
    """Check the status of the Home Assistant connection."""
    try:
        connection_status = await ha_api.check_connection()
        token_info = await ha_api.get_token_info()
        
        configured = memory_manager.get_preference("ha_configured", "false") == "true"
        
        return {
            "configured": configured,
            "connection": connection_status,
            "token": token_info
        }
    except Exception as e:
        logger.error(f"Error checking Home Assistant status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ha/entities")
async def get_home_assistant_entities(entity_type: Optional[str] = None):
    """Get all entities from Home Assistant with optional filtering."""
    try:
        states = await ha_api.get_states()
        
        # Filter by entity type if specified
        if entity_type:
            filtered_states = {
                entity_id: state for entity_id, state in states.items()
                if entity_id.startswith(f"{entity_type}.")
            }
            return {"entities": filtered_states}
        
        return {"entities": states}
    except Exception as e:
        logger.error(f"Error getting Home Assistant entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/automations")
async def get_automations():
    """Get all automations from Home Assistant."""
    try:
        automations = await automation_tool.get_automations()
        return {"automations": automations}
    except Exception as e:
        logger.error(f"Error getting automations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/automations/trigger/{entity_id}")
async def trigger_automation(entity_id: str):
    """Trigger a specific automation."""
    try:
        result = await automation_tool.trigger_automation(entity_id)
        return result
    except Exception as e:
        logger.error(f"Error triggering automation {entity_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/automations/toggle/{entity_id}")
async def toggle_automation(entity_id: str, enable: bool = True):
    """Enable or disable an automation."""
    try:
        result = await automation_tool.toggle_automation(entity_id, enable)
        return result
    except Exception as e:
        logger.error(f"Error toggling automation {entity_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/automations/create")
async def create_automation(request: AutomationRequest):
    """Create a new automation in Home Assistant."""
    try:
        result = await automation_tool.create_routine(
            name=request.name,
            triggers=request.triggers,
            actions=request.actions,
            conditions=request.conditions
        )
        return result
    except Exception as e:
        logger.error(f"Error creating automation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/automations/suggestions")
async def get_automation_suggestions():
    """Get AI-generated automation suggestions based on patterns."""
    try:
        suggestions = await automation_tool.suggest_automations(memory_manager)
        return {"suggestions": suggestions}
    except Exception as e:
        logger.error(f"Error generating automation suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Run the app if executed directly
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=False)
