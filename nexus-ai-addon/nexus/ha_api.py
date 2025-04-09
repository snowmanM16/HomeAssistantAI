"""
Home Assistant API client for Nexus AI
"""
import os
import logging
import json
import asyncio
from typing import Dict, Any, Optional, List

import aiohttp
from aiohttp import ClientSession, WSMsgType

logger = logging.getLogger("nexus.ha_api")

class HomeAssistantAPI:
    """Interface for communicating with Home Assistant API."""
    
    def __init__(self):
        """Initialize the Home Assistant API client."""
        # Configure from environment or use defaults that work inside the add-on
        self.base_url = os.environ.get("HA_URL", "http://supervisor/core/api")
        self.token = os.environ.get("HA_TOKEN", os.environ.get("SUPERVISOR_TOKEN"))
        
        # Track session and websocket
        self._session = None
        self._ws = None
        self._ws_task = None
        self._ws_authenticated = False
        self._ws_handlers = {}
        self._ws_id = 1
    
    async def _get_session(self):
        """Get or create the HTTP session."""
        if self._session is None or self._session.closed:
            self._session = ClientSession(headers=self._get_headers())
        return self._session
    
    def _get_headers(self):
        """Get the HTTP headers for API requests."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
    
    async def call_service(self, domain: str, service: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Call a Home Assistant service."""
        if not self.token:
            raise ValueError("Home Assistant token not configured")
        
        session = await self._get_session()
        url = f"{self.base_url}/services/{domain}/{service}"
        
        logger.debug(f"Calling service: {url} with data: {data}")
        
        try:
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Error calling service: {response.status} - {error_text}")
                    return {"error": f"HTTP {response.status}", "message": error_text}
        except Exception as e:
            logger.error(f"Exception calling service: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def get_states(self) -> List[Dict[str, Any]]:
        """Get all entity states from Home Assistant."""
        if not self.token:
            raise ValueError("Home Assistant token not configured")
        
        session = await self._get_session()
        url = f"{self.base_url}/states"
        
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Error getting states: {response.status} - {error_text}")
                    return []
        except Exception as e:
            logger.error(f"Exception getting states: {e}", exc_info=True)
            return []
    
    async def get_state(self, entity_id: str) -> Dict[str, Any]:
        """Get the state of a specific entity."""
        if not self.token:
            raise ValueError("Home Assistant token not configured")
        
        session = await self._get_session()
        url = f"{self.base_url}/states/{entity_id}"
        
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Error getting state: {response.status} - {error_text}")
                    return {"error": f"HTTP {response.status}", "message": error_text}
        except Exception as e:
            logger.error(f"Exception getting state: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def start_websocket(self):
        """Start a WebSocket connection to Home Assistant."""
        if self._ws_task and not self._ws_task.done():
            logger.debug("WebSocket already running")
            return
        
        self._ws_task = asyncio.create_task(self._websocket_loop())
    
    async def _websocket_loop(self):
        """Handle the WebSocket connection loop."""
        ws_url = self.base_url.replace("http", "ws").replace("https", "wss")
        ws_url = f"{ws_url}/websocket"
        
        logger.info(f"Connecting to WebSocket: {ws_url}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(ws_url) as ws:
                    self._ws = ws
                    
                    # Handle auth required message
                    msg = await ws.receive()
                    if msg.type == WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        if data.get("type") == "auth_required":
                            await self._authenticate_websocket()
                        else:
                            logger.error(f"Unexpected initial message: {data}")
                            return
                    
                    # Start listening for events
                    await self._listen_for_events()
        except Exception as e:
            logger.error(f"WebSocket error: {e}", exc_info=True)
        finally:
            self._ws = None
            self._ws_authenticated = False
    
    async def _authenticate_websocket(self):
        """Authenticate the WebSocket connection."""
        if not self._ws:
            logger.error("No active WebSocket connection")
            return
        
        try:
            await self._ws.send_str(json.dumps({
                "type": "auth",
                "access_token": self.token
            }))
            
            msg = await self._ws.receive()
            if msg.type == WSMsgType.TEXT:
                data = json.loads(msg.data)
                if data.get("type") == "auth_ok":
                    logger.info("WebSocket authenticated successfully")
                    self._ws_authenticated = True
                else:
                    logger.error(f"Authentication failed: {data}")
            else:
                logger.error(f"Unexpected message type: {msg.type}")
        except Exception as e:
            logger.error(f"Error authenticating WebSocket: {e}", exc_info=True)
    
    async def _listen_for_events(self):
        """Listen for events from the WebSocket connection."""
        if not self._ws or not self._ws_authenticated:
            logger.error("WebSocket not ready")
            return
        
        try:
            async for msg in self._ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    
                    # Handle event responses
                    if data.get("type") == "event" and data.get("event"):
                        event_type = data["event"].get("event_type")
                        if event_type in self._ws_handlers:
                            for handler in self._ws_handlers[event_type]:
                                try:
                                    handler(data["event"])
                                except Exception as e:
                                    logger.error(f"Error in event handler: {e}", exc_info=True)
                    
                    # Handle result responses
                    elif data.get("type") == "result":
                        logger.debug(f"Received result: {data}")
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {msg.data}")
                    break
        except Exception as e:
            logger.error(f"Error listening for events: {e}", exc_info=True)
    
    async def subscribe_to_events(self, event_type: str):
        """Subscribe to specific event types."""
        if not self._ws or not self._ws_authenticated:
            logger.warning("WebSocket not ready, can't subscribe")
            return
        
        try:
            self._ws_id += 1
            await self._ws.send_str(json.dumps({
                "id": self._ws_id,
                "type": "subscribe_events",
                "event_type": event_type
            }))
            logger.info(f"Subscribed to event type: {event_type}")
        except Exception as e:
            logger.error(f"Error subscribing to events: {e}", exc_info=True)
    
    def configure(self, url: Optional[str] = None, token: Optional[str] = None) -> None:
        """
        Configure the Home Assistant API with a custom URL and token.
        This allows setting up the connection after initialization.
        
        Args:
            url: The Home Assistant URL (e.g., http://homeassistant.local:8123)
            token: The long-lived access token
        """
        if url:
            # Make sure the URL doesn't end with a slash
            self.base_url = url.rstrip("/") + "/api"
        
        if token:
            self.token = token
        
        logger.info(f"Home Assistant API configured: {self.base_url}")
    
    async def check_connection(self) -> Dict[str, Any]:
        """
        Check the connection to Home Assistant.
        
        Returns:
            Dictionary with connection status information
        """
        if not self.token:
            return {"status": "error", "message": "No token configured"}
        
        try:
            # Try to get basic info from the API
            session = await self._get_session()
            url = f"{self.base_url}/config"
            
            async with session.get(url) as response:
                if response.status == 200:
                    config = await response.json()
                    return {
                        "status": "connected",
                        "version": config.get("version"),
                        "location_name": config.get("location_name"),
                        "time_zone": config.get("time_zone"),
                        "config": config
                    }
                else:
                    error_text = await response.text()
                    return {"status": "error", "message": f"HTTP {response.status}: {error_text}"}
        except Exception as e:
            logger.error(f"Error checking connection: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}
    
    async def get_token_info(self) -> Dict[str, Any]:
        """
        Get information about the current access token.
        
        Returns:
            Dictionary with token information
        """
        if not self.token:
            return {"valid": False, "message": "No token configured"}
            
        try:
            session = await self._get_session()
            url = f"{self.base_url}/"
            
            async with session.get(url) as response:
                if response.status == 200:
                    return {"valid": True, "message": "Token is valid"}
                else:
                    return {"valid": False, "message": f"HTTP {response.status}"}
        except Exception as e:
            logger.error(f"Error checking token: {e}", exc_info=True)
            return {"valid": False, "message": str(e)}
    
    async def close(self):
        """Close all connections."""
        if self._ws:
            await self._ws.close()
            self._ws = None
        
        if self._session:
            await self._session.close()
            self._session = None
        
        if self._ws_task and not self._ws_task.done():
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
