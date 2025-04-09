"""
Home Assistant API client for Nexus AI
"""
import os
import logging
import json
import asyncio
from typing import Dict, Any, Optional, List, Callable
import aiohttp
import websockets

logger = logging.getLogger(__name__)

class HomeAssistantAPI:
    """Interface for communicating with Home Assistant API."""
    
    def __init__(self):
        """Initialize the Home Assistant API client."""
        self.url = os.environ.get('HOME_ASSISTANT_URL', '')
        self.token = os.environ.get('SUPERVISOR_TOKEN', '')
        self.websocket_url = None
        self.session = None
        self.ws_client = None
        self.ws_id = 1
        self.ws_handlers = {}
        self.ws_authenticated = False
        self.ws_task = None

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
        
        url = f"{self.url}/api/services/{domain}/{service}"
        try:
            async with session.post(url, json=data) as response:
                if response.status != 200:
                    logger.error(f"Error calling service {domain}.{service}: {response.status}")
                    text = await response.text()
                    return {"success": False, "error": text}
                
                return {"success": True, "result": await response.json()}
        except Exception as e:
            logger.error(f"Exception calling service {domain}.{service}: {e}")
            return {"success": False, "error": str(e)}

    async def get_states(self) -> Dict[str, Any]:
        """Get all entity states from Home Assistant."""
        session = await self._get_session()
        
        url = f"{self.url}/api/states"
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Error getting states: {response.status}")
                    text = await response.text()
                    return {"success": False, "error": text}
                
                data = await response.json()
                return {"success": True, "result": data}
        except Exception as e:
            logger.error(f"Exception getting states: {e}")
            return {"success": False, "error": str(e)}

    async def get_state(self, entity_id: str) -> Dict[str, Any]:
        """Get the state of a specific entity."""
        session = await self._get_session()
        
        url = f"{self.url}/api/states/{entity_id}"
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Error getting state for {entity_id}: {response.status}")
                    text = await response.text()
                    return {"success": False, "error": text}
                
                data = await response.json()
                return {"success": True, "result": data}
        except Exception as e:
            logger.error(f"Exception getting state for {entity_id}: {e}")
            return {"success": False, "error": str(e)}

    async def start_websocket(self):
        """Start a WebSocket connection to Home Assistant."""
        if self.ws_task and not self.ws_task.done():
            logger.info("WebSocket connection already running")
            return
        
        self.websocket_url = f"{self.url.replace('http', 'ws')}/api/websocket"
        self.ws_authenticated = False
        self.ws_task = asyncio.create_task(self._listen_for_events())

    async def _authenticate_websocket(self):
        """Authenticate the WebSocket connection."""
        auth_message = {"type": "auth", "access_token": self.token}
        await self.ws_client.send(json.dumps(auth_message))
        self.ws_authenticated = True
        logger.info("WebSocket authenticated")

    async def _listen_for_events(self):
        """Listen for events from the WebSocket connection."""
        try:
            async with websockets.connect(self.websocket_url) as websocket:
                self.ws_client = websocket
                self.ws_id = 1
                
                # Receive auth required message
                auth_message = await websocket.recv()
                auth_data = json.loads(auth_message)
                
                if auth_data["type"] == "auth_required":
                    await self._authenticate_websocket()
                
                # Main event loop
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    # Handle different message types
                    if data["type"] == "event":
                        event_type = data["event"]["event_type"]
                        if event_type in self.ws_handlers:
                            for handler in self.ws_handlers[event_type]:
                                asyncio.create_task(handler(data["event"]))
                    
                    # Handle command responses
                    elif "id" in data and data["id"] in self.ws_handlers:
                        for handler in self.ws_handlers[data["id"]]:
                            asyncio.create_task(handler(data))
                            # Remove one-time handlers for command responses
                            self.ws_handlers[data["id"]].remove(handler)
                            if not self.ws_handlers[data["id"]]:
                                del self.ws_handlers[data["id"]]
        
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            # Schedule reconnection
            await asyncio.sleep(10)
            self.ws_task = asyncio.create_task(self._listen_for_events())

    async def subscribe_to_events(self, event_type: str):
        """Subscribe to specific event types."""
        if not self.ws_client or not self.ws_authenticated:
            logger.warning("WebSocket not connected or authenticated")
            return
        
        message = {
            "id": self.ws_id,
            "type": "subscribe_events",
            "event_type": event_type
        }
        await self.ws_client.send(json.dumps(message))
        self.ws_id += 1

    def configure(self, url: Optional[str] = None, token: Optional[str] = None) -> None:
        """
        Configure the Home Assistant API with a custom URL and token.
        This allows setting up the connection after initialization.
        
        Args:
            url: The Home Assistant URL (e.g., http://homeassistant.local:8123)
            token: The long-lived access token
        """
        if url:
            self.url = url
        if token:
            self.token = token
        
        # Reset session to apply new token
        if self.session and not self.session.closed:
            asyncio.create_task(self.session.close())
            self.session = None

    async def check_connection(self) -> Dict[str, Any]:
        """
        Check the connection to Home Assistant.
        
        Returns:
            Dictionary with connection status information
        """
        session = await self._get_session()
        
        url = f"{self.url}/api/"
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Error connecting to Home Assistant: {response.status}")
                    text = await response.text()
                    return {"success": False, "error": text}
                
                data = await response.json()
                return {
                    "success": True, 
                    "version": data.get("version", "unknown"),
                    "location_name": data.get("location_name", "unknown")
                }
        except Exception as e:
            logger.error(f"Exception connecting to Home Assistant: {e}")
            return {"success": False, "error": str(e)}

    async def get_token_info(self) -> Dict[str, Any]:
        """
        Get information about the current access token.
        
        Returns:
            Dictionary with token information
        """
        session = await self._get_session()
        
        url = f"{self.url}/api/auth/current_user"
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Error getting token info: {response.status}")
                    text = await response.text()
                    return {"success": False, "error": text}
                
                data = await response.json()
                return {"success": True, "result": data}
        except Exception as e:
            logger.error(f"Exception getting token info: {e}")
            return {"success": False, "error": str(e)}

    async def close(self):
        """Close all connections."""
        if self.ws_task and not self.ws_task.done():
            self.ws_task.cancel()
        
        if self.session and not self.session.closed:
            await self.session.close()
