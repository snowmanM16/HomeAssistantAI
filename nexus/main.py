"""
Main application module for Nexus AI
"""
import os
import logging
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, Request, WebSocket, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .agent import NexusAgent
from .database import DatabaseService
from .ha_api import HomeAssistantAPI
from .memory import MemoryManager
from .calendar import GoogleCalendar

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize services
db_service = DatabaseService()
ha_api = HomeAssistantAPI()
agent = NexusAgent(db_service, ha_api)
memory_manager = MemoryManager(db_service)
calendar = GoogleCalendar()

# Create FastAPI app
app = FastAPI(
    title="Nexus AI",
    description="AI assistant for Home Assistant",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request/response models
class AskRequest(BaseModel):
    prompt: str
    context: Optional[Dict[str, Any]] = None

class ActionRequest(BaseModel):
    domain: str
    service: str
    data: Optional[Dict[str, Any]] = None

class HAConfigRequest(BaseModel):
    url: str
    token: str

class AutomationRequest(BaseModel):
    name: str
    triggers: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    conditions: Optional[List[Dict[str, Any]]] = None

class MemoryRequest(BaseModel):
    key: str
    value: str


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the web interface."""
    return FileResponse("nexus/static/index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "online"}


@app.post("/api/ask")
async def ask(request: AskRequest):
    """Process a natural language request through the AI agent."""
    try:
        response = await agent.process_query(request.prompt, request.context)
        return {"response": response}
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/action")
async def action(request: ActionRequest):
    """Execute a Home Assistant service."""
    try:
        result = await ha_api.call_service(request.domain, request.service, request.data or {})
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error executing action: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/homeassistant")
async def configure_home_assistant(request: HAConfigRequest):
    """Configure the Home Assistant API connection."""
    try:
        # Configure the API client
        ha_api.configure(request.url, request.token)
        
        # Test connection
        connection_info = await ha_api.check_connection()
        
        # Save configuration to database with token hash
        db_service.save_ha_config(request.url, request.token)
        
        # Update connection status
        db_service.update_ha_connection_status(
            version=connection_info.get("version"),
            location_name=connection_info.get("location_name")
        )
        
        # Subscribe to state changes via WebSocket
        await ha_api.start_websocket()
        
        return {"success": True, "connection": connection_info}
    except Exception as e:
        logger.error(f"Error configuring Home Assistant: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            response = await agent.process_query(data)
            await websocket.send_text(response)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        await websocket.close()


@app.post("/api/memory")
async def save_memory(request: MemoryRequest):
    """Save a memory item."""
    success = memory_manager.save(request.key, request.value)
    return {"success": success}


@app.get("/api/memory/{key}")
async def get_memory(key: str):
    """Get a specific memory by key."""
    memory = memory_manager.recall(key)
    if memory:
        return memory
    raise HTTPException(status_code=404, detail="Memory not found")


@app.get("/api/memories")
async def get_all_memories(preferences_only: bool = False):
    """Get all memories with optional filtering."""
    memories = memory_manager.get_all(preferences_only)
    return {"memories": memories}


@app.post("/api/automation")
async def create_automation(request: AutomationRequest):
    """Create a new automation."""
    automation_id = db_service.save_automation(
        name=request.name,
        triggers=request.triggers,
        actions=request.actions,
        conditions=request.conditions
    )
    if automation_id:
        return {"success": True, "automation_id": automation_id}
    raise HTTPException(status_code=500, detail="Failed to create automation")


@app.get("/api/automations")
async def get_automations(suggested_only: bool = False):
    """Get all automations with optional filtering."""
    automations = db_service.get_automations(suggested_only)
    return {"automations": automations}


@app.get("/api/entities")
async def get_entities(domain: Optional[str] = None, important_only: bool = False):
    """Get entities with optional filtering."""
    entities = db_service.get_entities(domain, important_only)
    return {"entities": entities}


@app.get("/api/entity/{entity_id}/history")
async def get_entity_history(entity_id: str, limit: int = 100):
    """Get historical states for an entity."""
    history = db_service.get_entity_history(entity_id, limit)
    return {"history": history}


@app.get("/api/patterns")
async def get_patterns(pattern_type: Optional[str] = None, min_confidence: float = 0.0):
    """Get detected patterns with optional filtering."""
    patterns = db_service.get_patterns(pattern_type, min_confidence)
    return {"patterns": patterns}


# Mount static files
try:
    app.mount("/static", StaticFiles(directory="nexus/static"), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {str(e)}")


# Main entry point
if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or use default
    port = int(os.environ.get("PORT", 5000))
    
    # Start the server
    uvicorn.run(
        "nexus.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=True
    )