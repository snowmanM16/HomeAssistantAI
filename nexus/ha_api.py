"""
Home Assistant API client for Nexus AI
"""
import os
import logging
import json
import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

import aiohttp
from aiohttp import ClientSession

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HomeAssistantAPI:
    """Interface for communicating with Home Assistant API."""
    
    def __init__(self):
        """Initialize the Home Assistant API client."""
        # Default to supervisor connection if running as add-on
        self.ha_url = os.environ.get("SUPERVISOR_URL", "http://supervisor/core")
        self.token = os.environ.get("SUPERVISOR_TOKEN", "")
        
        self._session = None
        self._ws_client = None
        self._ws_task = None
        self._event_listeners = {}
        self._entity_listeners = {}
        self._connection_state = "disconnected"
    
    async def _get_session(self):
        """Get or create the HTTP session."""
        if self._session is None or self._session.closed:
            self._session = ClientSession()
        return self._session
    
    def _get_headers(self):
        """Get the HTTP headers for API requests."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
    
    async def call_service(self, domain: str, service: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Call a Home Assistant service."""
        session = await self._get_session()
        url = f"{self.ha_url}/api/services/{domain}/{service}"
        
        try:
            async with session.post(url, json=data, headers=self._get_headers()) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    logger.error(f"Error calling service {domain}.{service}: {resp.status} - {error_text}")
                    raise Exception(f"Error calling service: {resp.status} - {error_text}")
        except Exception as e:
            logger.error(f"Exception calling service {domain}.{service}: {str(e)}")
            raise
    
    async def get_states(self) -> List[Dict[str, Any]]:
        """Get all entity states from Home Assistant."""
        session = await self._get_session()
        url = f"{self.ha_url}/api/states"
        
        try:
            async with session.get(url, headers=self._get_headers()) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    logger.error(f"Error getting states: {resp.status} - {error_text}")
                    raise Exception(f"Error getting states: {resp.status} - {error_text}")
        except Exception as e:
            logger.error(f"Exception getting states: {str(e)}")
            raise
    
    async def get_state(self, entity_id: str) -> Dict[str, Any]:
        """Get the state of a specific entity."""
        session = await self._get_session()
        url = f"{self.ha_url}/api/states/{entity_id}"
        
        try:
            async with session.get(url, headers=self._get_headers()) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    logger.error(f"Error getting state for {entity_id}: {resp.status} - {error_text}")
                    raise Exception(f"Error getting state: {resp.status} - {error_text}")
        except Exception as e:
            logger.error(f"Exception getting state for {entity_id}: {str(e)}")
            raise
    
    async def start_websocket(self):
        """Start a WebSocket connection to Home Assistant."""
        if self._ws_task and not self._ws_task.done():
            logger.info("WebSocket connection already running")
            return
        
        self._ws_task = asyncio.create_task(self._websocket_loop())
        logger.info("Started WebSocket connection task")
    
    async def _websocket_loop(self):
        """Handle the WebSocket connection loop."""
        retry_interval = 5  # seconds
        max_retries = 10
        retries = 0
        
        while retries < max_retries:
            try:
                logger.info("Connecting to Home Assistant WebSocket API...")
                self._connection_state = "connecting"
                
                async with aiohttp.ClientSession() as session:
                    ws_url = f"{self.ha_url.replace('http', 'ws')}/api/websocket"
                    
                    async with session.ws_connect(ws_url) as ws:
                        self._ws_client = ws
                        logger.info("Connected to Home Assistant WebSocket")
                        
                        # Handle authentication
                        auth_ok = await self._authenticate_websocket()
                        if not auth_ok:
                            logger.error("WebSocket authentication failed")
                            self._connection_state = "auth_failed"
                            break
                        
                        # Successfully connected and authenticated
                        self._connection_state = "connected"
                        retries = 0  # Reset retry counter on successful connection
                        
                        # Subscribe to state_changed events
                        await self.subscribe_to_events("state_changed")
                        
                        # Start listening for events
                        await self._listen_for_events()
            
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                retries += 1
                self._connection_state = "disconnected"
                logger.error(f"WebSocket connection error (attempt {retries}/{max_retries}): {str(e)}")
                await asyncio.sleep(retry_interval)
            
            except Exception as e:
                logger.error(f"Unexpected WebSocket error: {str(e)}")
                self._connection_state = "error"
                break
        
        self._ws_client = None
        if self._connection_state != "auth_failed":
            self._connection_state = "disconnected"
        
        logger.info("WebSocket connection closed")
    
    async def _authenticate_websocket(self):
        """Authenticate the WebSocket connection."""
        if not self._ws_client:
            return False
        
        # Wait for auth required message
        msg = await self._ws_client.receive_json()
        if msg.get("type") != "auth_required":
            logger.error(f"Expected auth_required message, got: {msg}")
            return False
        
        # Send authentication message
        await self._ws_client.send_json({
            "type": "auth",
            "access_token": self.token
        })
        
        # Wait for auth result
        msg = await self._ws_client.receive_json()
        if msg.get("type") == "auth_ok":
            logger.info("WebSocket authentication successful")
            return True
        else:
            logger.error(f"Authentication failed: {msg}")
            return False
    
    async def _listen_for_events(self):
        """Listen for events from the WebSocket connection."""
        if not self._ws_client:
            return
        
        msg_id = 1
        
        try:
            async for msg in self._ws_client:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if data.get("type") == "event":
                        event_data = data.get("event", {})
                        event_type = event_data.get("event_type")
                        
                        # Handle state changed events
                        if event_type == "state_changed":
                            entity_id = event_data.get("data", {}).get("entity_id")
                            new_state = event_data.get("data", {}).get("new_state", {})
                            old_state = event_data.get("data", {}).get("old_state", {})
                            
                            # Process entity callbacks
                            if entity_id in self._entity_listeners:
                                for callback in self._entity_listeners[entity_id]:
                                    try:
                                        callback(entity_id, new_state, old_state)
                                    except Exception as e:
                                        logger.error(f"Error in entity callback: {str(e)}")
                        
                        # Process event callbacks
                        if event_type in self._event_listeners:
                            for callback in self._event_listeners[event_type]:
                                try:
                                    callback(event_data)
                                except Exception as e:
                                    logger.error(f"Error in event callback: {str(e)}")
                    
                    msg_id += 1
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket connection closed with error: {self._ws_client.exception()}")
                    break
        except Exception as e:
            logger.error(f"Error in WebSocket event loop: {str(e)}")
    
    async def subscribe_to_events(self, event_type: str):
        """Subscribe to specific event types."""
        if not self._ws_client:
            logger.warning("Cannot subscribe to events - WebSocket not connected")
            return
        
        try:
            await self._ws_client.send_json({
                "id": 1,
                "type": "subscribe_events",
                "event_type": event_type
            })
            logger.info(f"Subscribed to {event_type} events")
        except Exception as e:
            logger.error(f"Error subscribing to {event_type} events: {str(e)}")
    
    def configure(self, url: Optional[str] = None, token: Optional[str] = None) -> None:
        """
        Configure the Home Assistant API with a custom URL and token.
        This allows setting up the connection after initialization.
        
        Args:
            url: The Home Assistant URL (e.g., http://homeassistant.local:8123)
            token: The long-lived access token
        """
        if url:
            self.ha_url = url
        if token:
            self.token = token
    
    async def check_connection(self) -> Dict[str, Any]:
        """
        Check the connection to Home Assistant.
        
        Returns:
            Dictionary with connection status information
        """
        try:
            session = await self._get_session()
            url = f"{self.ha_url}/api/"
            
            async with session.get(url, headers=self._get_headers()) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "connected": True,
                        "version": data.get("version"),
                        "location_name": data.get("location_name"),
                        "status": "connected"
                    }
                else:
                    error_text = await resp.text()
                    logger.error(f"Error connecting to HA: {resp.status} - {error_text}")
                    return {
                        "connected": False,
                        "status": f"Error: {resp.status}",
                        "message": error_text
                    }
        except Exception as e:
            logger.error(f"Exception checking connection: {str(e)}")
            return {
                "connected": False,
                "status": "error",
                "message": str(e)
            }
    
    async def get_token_info(self) -> Dict[str, Any]:
        """
        Get information about the current access token.
        
        Returns:
            Dictionary with token information
        """
        try:
            session = await self._get_session()
            url = f"{self.ha_url}/api/auth/token"
            
            async with session.get(url, headers=self._get_headers()) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    logger.error(f"Error getting token info: {resp.status} - {error_text}")
                    return {"error": f"Error: {resp.status}", "message": error_text}
        except Exception as e:
            logger.error(f"Exception getting token info: {str(e)}")
            return {"error": "Exception", "message": str(e)}
    
    def register_entity_callback(self, entity_id: str, callback: Callable[[str, Dict, Dict], None]) -> None:
        """
        Register a callback for changes to a specific entity.
        
        Args:
            entity_id: The entity to monitor
            callback: Function to call with (entity_id, new_state, old_state)
        """
        if entity_id not in self._entity_listeners:
            self._entity_listeners[entity_id] = []
        self._entity_listeners[entity_id].append(callback)
    
    def register_event_callback(self, event_type: str, callback: Callable[[Dict], None]) -> None:
        """
        Register a callback for a specific event type.
        
        Args:
            event_type: The event type to monitor
            callback: Function to call with event data
        """
        if event_type not in self._event_listeners:
            self._event_listeners[event_type] = []
        self._event_listeners[event_type].append(callback)
    
    async def close(self):
        """Close all connections."""
        if self._ws_task and not self._ws_task.done():
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
        
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None