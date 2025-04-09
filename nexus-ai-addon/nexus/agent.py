import os
import json
import logging
import datetime
import asyncio
import re
from typing import Dict, Any, List, Optional, Tuple
from .memory import MemoryManager
from .openai_helper import ask_gpt, extract_actions

logger = logging.getLogger("nexus.agent")

class NexusAgent:
    """Core AI agent that processes queries and integrates with all components."""
    
    def __init__(self, memory, ha_api, calendar=None, stt=None, tts=None):
        """Initialize the AI agent with components."""
        self.memory = memory
        self.ha_api = ha_api
        self.calendar = calendar
        self.stt = stt
        self.tts = tts
        
        # Get OpenAI API key from environment
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        if not self.openai_api_key:
            logger.warning("OpenAI API key not set. AI functionality will be limited.")
    
    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Process a user query with context and memory."""
        # Skip AI processing if API key is not set
        if not self.openai_api_key:
            return "OpenAI API key not configured. Please set it in the add-on configuration."
        
        # Get current time for context
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Retrieve relevant memories
        memories = self.memory.search(query)
        memory_context = "\n".join([f"- {item['value']}" for item in memories[:5]])
        
        # Get calendar events if available
        calendar_events = []
        if self.calendar:
            try:
                calendar_events = await self.calendar.get_today_events()
            except Exception as e:
                logger.error(f"Failed to get calendar events: {e}")
        
        calendar_context = "\n".join([f"- {event['time']}: {event['event']}" for event in calendar_events[:5]])
        
        # Get Home Assistant state
        ha_state = {}
        try:
            ha_state = await self.ha_api.get_states()
        except Exception as e:
            logger.error(f"Failed to get Home Assistant state: {e}")
        
        # Prepare the system message
        system_message = f"""
        You are Nexus AI, an intelligent assistant integrated with Home Assistant, a smart home platform.
        Current time: {current_time}
        
        Your capabilities:
        1. Answer questions and provide information
        2. Control smart home devices via Home Assistant
        3. Access calendar information
        4. Remember information shared with you
        
        When a user asks you to control devices or perform actions in their home, you should:
        - Identify the domain (light, switch, climate, etc.) and service (turn_on, turn_off, etc.)
        - If specific entity IDs are mentioned, use them
        - If details are unclear, ask for clarification
        
        When responding:
        - Be helpful, friendly, and concise
        - Acknowledge when you're taking actions
        - If you need to control a device, indicate which command you would use
        - Don't fabricate information or capabilities
        
        Remember these user preferences and information from previous conversations:
        {memory_context if memory_context else "No specific preferences recorded yet."}
        
        Today's calendar events:
        {calendar_context if calendar_context else "No calendar events found for today."}
        """
        
        # Use the most relevant Home Assistant states in the context
        ha_context = self._extract_relevant_ha_states(ha_state, query)
        
        # Add additional context if provided
        additional_context = ""
        if context:
            additional_context = f"\nAdditional context: {json.dumps(context)}"
            
        # Build messages for OpenAI
        messages = [
            {"role": "system", "content": system_message},
            {"role": "system", "content": f"Home Assistant state: {ha_context}{additional_context}"},
            {"role": "user", "content": query}
        ]
        
        # Log the request for debugging
        logger.debug(f"Sending request to OpenAI with messages: {messages}")
        
        try:
            # Use our OpenAI helper to get a response
            ai_response = await ask_gpt(
                prompt=query,
                system_prompt=system_message,
                context=f"Home Assistant state: {ha_context}{additional_context}"
            )
            
            # Save the interaction to memory
            current_date = datetime.datetime.now().strftime("%Y-%m-%d")
            self.memory.save_memory(
                f"interaction_{current_date}_{hash(query) % 10000}", 
                f"Q: {query}\nA: {ai_response}"
            )
            
            # Check for action commands in the response
            await self._process_actions(ai_response)
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"I encountered an error processing your request: {str(e)}"
    
    def _extract_relevant_ha_states(self, ha_state: Dict[str, Any], query: str) -> str:
        """Extract relevant Home Assistant states based on the query."""
        # This is a simple implementation that could be improved with better filtering
        relevant_states = {}
        
        # Define keywords to match with entities
        keywords = {
            "light": ["light", "lamp", "lights", "brightness", "dim", "bright", "color"],
            "switch": ["switch", "plug", "outlet", "turn on", "turn off", "toggle"],
            "climate": ["temperature", "climate", "heat", "cool", "thermostat", "ac", "heating"],
            "sensor": ["sensor", "temperature", "humidity", "motion", "door", "window", "battery"],
            "weather": ["weather", "forecast", "rain", "snow", "temperature", "wind"],
            "media_player": ["tv", "music", "play", "pause", "volume", "media", "song", "movie"]
        }
        
        # Extract entities that might be relevant to the query
        query_lower = query.lower()
        for entity_id, state in ha_state.items():
            entity_type = entity_id.split('.')[0]
            
            # Check if entity type is in our keywords list
            if entity_type in keywords:
                # Check if any keyword for this entity type appears in the query
                if any(keyword in query_lower for keyword in keywords[entity_type]):
                    relevant_states[entity_id] = state
            
            # Also include entities explicitly mentioned by name
            entity_name = state.get('attributes', {}).get('friendly_name', '').lower()
            if entity_name and entity_name in query_lower:
                relevant_states[entity_id] = state
        
        # Limit the number of states to avoid too much context
        relevant_states_list = list(relevant_states.items())[:15]
        
        # Convert to a readable format
        formatted_states = []
        for entity_id, state in relevant_states_list:
            friendly_name = state.get('attributes', {}).get('friendly_name', entity_id)
            state_str = state.get('state', 'unknown')
            formatted_states.append(f"{friendly_name} ({entity_id}): {state_str}")
        
        return "\n".join(formatted_states)
    
    async def _process_actions(self, response: str) -> None:
        """Process any actions indicated in the AI response."""
        try:
            # First check for actions in the old format pattern: [ACTION:domain.service:{"entity_id":"light.living_room"}]
            action_pattern = r'\[ACTION:([\w\.]+):({.*?})\]'
            matches = re.findall(action_pattern, response)
            
            for match in matches:
                try:
                    service_call, data_str = match
                    domain, service = service_call.split('.')
                    data = json.loads(data_str)
                    
                    logger.info(f"Executing action: {domain}.{service} with data: {data}")
                    await self.ha_api.call_service(domain, service, data)
                except Exception as e:
                    logger.error(f"Failed to execute action from response: {e}")
            
            # Then use the new structured extraction method
            actions = await extract_actions(response)
            for action in actions:
                try:
                    domain = action.get('domain')
                    service = action.get('service')
                    data = action.get('data', {})
                    
                    if domain and service:
                        logger.info(f"Executing extracted action: {domain}.{service} with data: {data}")
                        await self.ha_api.call_service(domain, service, data)
                except Exception as e:
                    logger.error(f"Failed to execute extracted action: {e}")
        except Exception as e:
            logger.error(f"Error in action processing: {e}")
