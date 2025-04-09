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
        # Try to get token from different sources (in order of priority)
        self.token = os.environ.get("SUPERVISOR_TOKEN") or os.environ.get("HASS_TOKEN") or os.environ.get("HA_LONG_LIVED_TOKEN", "")
        
        if not self.token:
            logger.warning("No Home Assistant API token found in environment. You will need to configure a long-lived access token.")
        
        # Get base URL from environment or use default
        ha_host = os.environ.get("HASS_URL", "http://supervisor/core")
        
        # Remove trailing slash if present
        if ha_host.endswith('/'):
            ha_host = ha_host[:-1]
            
        # API endpoints
        self.base_url = f"{ha_host}/api"
        self.websocket_url = ha_host.replace('http', 'ws') + "/api/websocket"
        
        logger.info(f"Home Assistant API configured with base URL: {self.base_url}")
        
        # Session for HTTP requests
        self.session = None
        
        # WebSocket connection
        self.ws = None
        self.ws_id = 0
        self.ws_authenticated = False
        self.ws_tasks = []
        
        # Track connection status
        self.connected = False
        self.last_error = None
    
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
    
    def configure(self, url: Optional[str] = None, token: Optional[str] = None) -> None:
        """
        Configure the Home Assistant API with a custom URL and token.
        This allows setting up the connection after initialization.
        
        Args:
            url: The Home Assistant URL (e.g., http://homeassistant.local:8123)
            token: The long-lived access token
        """
        if token:
            self.token = token
            logger.info("Home Assistant API token configured")
            
        if url:
            # Remove trailing slash if present
            if url.endswith('/'):
                url = url[:-1]
                
            # API endpoints
            self.base_url = f"{url}/api"
            self.websocket_url = url.replace('http', 'ws') + "/api/websocket"
            logger.info(f"Home Assistant API URL configured: {self.base_url}")
        
        # Reset session to use new token if it was changed
        if token and self.session and not self.session.closed:
            asyncio.create_task(self.session.close())
            self.session = None
    
    async def check_connection(self) -> Dict[str, Any]:
        """
        Check the connection to Home Assistant.
        
        Returns:
            Dictionary with connection status information
        """
        if not self.token:
            return {
                "connected": False,
                "error": "No API token configured"
            }
            
        try:
            # Try to get API status
            session = await self._get_session()
            url = f"{self.base_url}/config"
            
            async with session.get(url) as response:
                response.raise_for_status()
                config = await response.json()
                
                self.connected = True
                self.last_error = None
                
                return {
                    "connected": True,
                    "version": config.get("version", "unknown"),
                    "location_name": config.get("location_name", "unknown")
                }
                
        except Exception as e:
            self.connected = False
            self.last_error = str(e)
            logger.error(f"Error connecting to Home Assistant: {e}")
            
            return {
                "connected": False,
                "error": str(e)
            }
    
    async def get_token_info(self) -> Dict[str, Any]:
        """
        Get information about the current access token.
        
        Returns:
            Dictionary with token information
        """
        if not self.token:
            return {
                "valid": False,
                "error": "No token configured"
            }
            
        try:
            session = await self._get_session()
            
            # We'll use the config endpoint to test authentication
            url = f"{self.base_url}/config"
            
            async with session.get(url) as response:
                if response.status == 200:
                    return {
                        "valid": True,
                        "scopes": ["*"],  # Long-lived tokens typically have full access
                        "expires": None  # Long-lived tokens don't expire
                    }
                elif response.status == 401:
                    return {
                        "valid": False,
                        "error": "Invalid token"
                    }
                else:
                    return {
                        "valid": False,
                        "error": f"Unexpected status code: {response.status}"
                    }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
    
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
