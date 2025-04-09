"""
Main application module for Nexus AI
"""

import os
import logging
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from nexus.agent import NexusAgent
from nexus.database import DatabaseService
from nexus.ha_api import HomeAssistantAPI
from nexus.memory import MemoryManager

# Configure logging
log_level = os.environ.get("LOG_LEVEL", "info").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("nexus")

# Initialize components
db_service = DatabaseService()
ha_api = HomeAssistantAPI()
memory_manager = MemoryManager(db_service)
agent = NexusAgent(db_service, ha_api)

# Create FastAPI app
app = FastAPI(
    title="Nexus AI",
    description="Intelligent AI Assistant for Home Assistant",
    version="0.1.0",
)

# Models for API requests
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

# Mount static files and templates
try:
    app.mount("/static", StaticFiles(directory="nexus/static"), name="static")
    templates = Jinja2Templates(directory="nexus/templates")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")
    templates = None

# Web interface
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the web interface."""
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    else:
        return HTMLResponse("<html><body><h1>Nexus AI is running</h1><p>Web interface not available</p></body></html>")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "online"}

# AI endpoint
@app.post("/api/ask")
async def ask(request: AskRequest):
    """Process a natural language request through the AI agent."""
    try:
        response = await agent.process_query(request.prompt, request.context)
        return {"response": response}
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Home Assistant actions
@app.post("/api/action")
async def action(request: ActionRequest):
    """Execute a Home Assistant service."""
    try:
        result = await ha_api.call_service(request.domain, request.service, request.data or {})
        return {"result": result}
    except Exception as e:
        logger.error(f"Error executing action: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Home Assistant configuration
@app.post("/api/ha/configure")
async def configure_home_assistant(request: HAConfigRequest):
    """Configure the Home Assistant API connection."""
    try:
        ha_api.configure(request.url, request.token)
        db_service.save_ha_config(request.url, request.token)
        
        # Test the connection
        result = await ha_api.check_connection()
        
        # Update connection status in the database
        db_service.update_ha_connection_status(
            version=result.get("version"),
            location_name=result.get("location_name")
        )
        
        return {"status": "connected", "info": result}
    except Exception as e:
        logger.error(f"Error configuring Home Assistant: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket for real-time communication
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            if "prompt" in data:
                response = await agent.process_query(data["prompt"], data.get("context"))
                await websocket.send_json({"response": response})
            else:
                await websocket.send_json({"error": "Invalid request"})
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({"error": str(e)})

# Memory endpoints
@app.post("/api/memory")
async def save_memory(request: MemoryRequest):
    """Save a memory item."""
    db_service.save_memory(request.key, request.value)
    return {"status": "saved"}

@app.get("/api/memory/{key}")
async def get_memory(key: str):
    """Get a specific memory by key."""
    memory = db_service.get_memory(key)
    if memory:
        return memory
    raise HTTPException(status_code=404, detail="Memory not found")

@app.get("/api/memories")
async def get_all_memories(preferences_only: bool = False):
    """Get all memories with optional filtering."""
    memories = db_service.get_all_memories(preferences_only)
    return {"memories": memories}

# Automations endpoints
@app.post("/api/automations")
async def create_automation(request: AutomationRequest):
    """Create a new automation."""
    automation_id = db_service.save_automation(
        name=request.name,
        triggers=request.triggers,
        actions=request.actions,
        conditions=request.conditions
    )
    if automation_id:
        return {"id": automation_id}
    raise HTTPException(status_code=500, detail="Failed to create automation")

@app.get("/api/automations")
async def get_automations(suggested_only: bool = False):
    """Get all automations with optional filtering."""
    automations = db_service.get_automations(suggested_only)
    return {"automations": automations}

# Entity information
@app.get("/api/entities")
async def get_entities(domain: Optional[str] = None, important_only: bool = False):
    """Get entities with optional filtering."""
    entities = db_service.get_entities(domain, important_only)
    return {"entities": entities}

@app.get("/api/entities/{entity_id}/history")
async def get_entity_history(entity_id: str, limit: int = 100):
    """Get historical states for an entity."""
    history = db_service.get_entity_history(entity_id, limit)
    return {"history": history}

# Patterns endpoints
@app.get("/api/patterns")
async def get_patterns(pattern_type: Optional[str] = None, min_confidence: float = 0.0):
    """Get detected patterns with optional filtering."""
    patterns = db_service.get_patterns(pattern_type, min_confidence)
    return {"patterns": patterns}

if __name__ == "__main__":
    import uvicorn
    import argparse
    
    parser = argparse.ArgumentParser(description="Nexus AI Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to listen on")
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on")
    
    args = parser.parse_args()
    
    uvicorn.run("nexus.main:app", host=args.host, port=args.port, reload=True)
