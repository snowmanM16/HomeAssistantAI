import os
import logging
import aiohttp
import json
import asyncio
from typing import Dict, Any, List, Optional

logger = logging.getLogger("nexus.ha_api")

class HomeAssistantAPI:
    """Interface for communicating with Home Assistant API."""
    
    def __init__(self):
        """Initialize the Home Assistant API client."""
        self.token = os.environ.get("SUPERVISOR_TOKEN", "")
        if not self.token:
            logger.warning("No Home Assistant API token found in environment.")
        
        # API endpoints
        self.base_url = "http://supervisor/core/api"
        self.websocket_url = "ws://supervisor/core/websocket"
        
        # Session for HTTP requests
        self.session = None
        
        # WebSocket connection
        self.ws = None
        self.ws_id = 0
        self.ws_authenticated = False
        self.ws_tasks = []
    
    async def _get_session(self):
        """Get or create the HTTP session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            })
        return self.session
    
    async def call_service(self, domain: str, service: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Call a Home Assistant service."""
        session = await self._get_session()
        url = f"{self.base_url}/services/{domain}/{service}"
        
        try:
            async with session.post(url, json=data) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            logger.error(f"Error calling service {domain}.{service}: {e}")
            raise
    
    async def get_states(self) -> Dict[str, Any]:
        """Get all entity states from Home Assistant."""
        session = await self._get_session()
        url = f"{self.base_url}/states"
        
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                states = await response.json()
                
                # Convert to a dictionary with entity_id as key
                states_dict = {state["entity_id"]: state for state in states}
                return states_dict
        except aiohttp.ClientResponseError as e:
            logger.error(f"Error getting states: {e}")
            raise
    
    async def get_state(self, entity_id: str) -> Dict[str, Any]:
        """Get the state of a specific entity."""
        session = await self._get_session()
        url = f"{self.base_url}/states/{entity_id}"
        
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            logger.error(f"Error getting state for {entity_id}: {e}")
            raise
    
    async def start_websocket(self):
        """Start a WebSocket connection to Home Assistant."""
        if self.ws is not None:
            return
        
        try:
            self.ws = await aiohttp.ClientSession().ws_connect(self.websocket_url)
            
            # Authenticate
            await self._authenticate_websocket()
            
            # Start listening for events
            task = asyncio.create_task(self._listen_for_events())
            self.ws_tasks.append(task)
            
            logger.info("WebSocket connection established")
        except Exception as e:
            logger.error(f"Failed to establish WebSocket connection: {e}")
            self.ws = None
    
    async def _authenticate_websocket(self):
        """Authenticate the WebSocket connection."""
        if not self.ws:
            return
        
        # Receive auth required message
        auth_message = await self.ws.receive_json()
        if auth_message["type"] != "auth_required":
            logger.error("Unexpected first message from WebSocket")
            return
        
        # Send auth message
        await self.ws.send_json({
            "type": "auth",
            "access_token": self.token
        })
        
        # Receive auth response
        auth_response = await self.ws.receive_json()
        if auth_response["type"] != "auth_ok":
            logger.error(f"Authentication failed: {auth_response}")
            await self.ws.close()
            self.ws = None
            return
        
        self.ws_authenticated = True
        logger.info("WebSocket authenticated")
    
    async def _listen_for_events(self):
        """Listen for events from the WebSocket connection."""
        if not self.ws or not self.ws_authenticated:
            return
        
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if data["type"] == "event":
                        # Process event
                        event = data["event"]
                        logger.debug(f"Received event: {event['event_type']}")
                        # Process event here
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {msg.data}")
                    break
        except Exception as e:
            logger.error(f"WebSocket listener error: {e}")
        finally:
            # Connection closed
            self.ws_authenticated = False
            self.ws = None
            logger.info("WebSocket connection closed")
    
    async def subscribe_to_events(self, event_type: str):
        """Subscribe to specific event types."""
        if not self.ws or not self.ws_authenticated:
            await self.start_websocket()
        
        self.ws_id += 1
        message = {
            "id": self.ws_id,
            "type": "subscribe_events",
            "event_type": event_type
        }
        
        await self.ws.send_json(message)
        response = await self.ws.receive_json()
        
        if response.get("success"):
            logger.info(f"Successfully subscribed to {event_type} events")
        else:
            logger.error(f"Failed to subscribe to {event_type} events: {response}")
    
    async def close(self):
        """Close all connections."""
        # Cancel WebSocket tasks
        for task in self.ws_tasks:
            task.cancel()
        
        # Close WebSocket
        if self.ws:
            await self.ws.close()
            self.ws = None
        
        # Close HTTP session
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
