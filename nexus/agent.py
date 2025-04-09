"""
AI agent for Nexus
"""
import os
import re
import logging
import json
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime

import openai
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NexusAgent:
    """Core AI agent that processes queries and integrates with all components."""
    
    def __init__(self, database, ha_api):
        """Initialize the AI agent with components."""
        self.db = database
        self.ha_api = ha_api
        self.client = None
        self.initialize_ai()
    
    def initialize_ai(self):
        """Initialize the AI backend based on configuration."""
        # Check if using OpenAI or local model
        use_local_model = os.environ.get("USE_LOCAL_MODEL", "false").lower() == "true"
        
        if use_local_model:
            local_model_path = os.environ.get("LOCAL_MODEL_PATH", "")
            logger.info(f"Using local model at {local_model_path}")
            # Implement local model initialization here
            # This would typically use a library like llama-cpp-python
            self.model_type = "local"
            self.model_name = os.path.basename(local_model_path)
        else:
            # Use OpenAI
            openai_api_key = os.environ.get("OPENAI_API_KEY")
            if not openai_api_key:
                logger.warning("OpenAI API key not provided. AI functionality will be limited.")
                self.client = None
                self.model_type = "none"
                self.model_name = "none"
            else:
                self.client = OpenAI(api_key=openai_api_key)
                self.model_type = "openai"
                self.model_name = "gpt-4o"  # The newest OpenAI model is "gpt-4o" which was released May 13, 2024
                logger.info("Using OpenAI API")
    
    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Process a user query with context and memory."""
        # Check if AI is available
        if not self.client and self.model_type != "local":
            return "AI is not available. Please configure an OpenAI API key or local model in the add-on settings."
        
        try:
            # Get current Home Assistant state
            ha_state = await self.ha_api.get_states()
            
            # Prepare context object
            if not context:
                context = {}
            
            # Extract relevant HA states based on the query
            relevant_states = self._extract_relevant_ha_states(ha_state, query)
            
            # Build system prompt
            system_prompt = self._build_system_prompt(context)
            
            # Build user prompt with context
            user_prompt = f"User question: {query}\n\n"
            user_prompt += "Current Home Assistant state:\n"
            user_prompt += relevant_states
            
            # Add any additional context from the request
            if context and context.get("additional_context"):
                user_prompt += f"\nAdditional context:\n{context.get('additional_context')}"
            
            # Call the AI
            if self.model_type == "openai":
                response = await self._call_openai(system_prompt, user_prompt)
            elif self.model_type == "local":
                response = self._call_local_model(system_prompt, user_prompt)
            else:
                return "AI is not available. Please configure an OpenAI API key or local model in the add-on settings."
            
            # Process any actions in the response
            await self._process_actions(response)
            
            # Clean the response (remove action commands)
            cleaned_response = self._clean_response(response)
            
            return cleaned_response
        
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return f"I'm sorry, I encountered an error processing your request: {str(e)}"
    
    def _extract_relevant_ha_states(self, ha_state: List[Dict[str, Any]], query: str) -> str:
        """Extract relevant Home Assistant states based on the query."""
        # This is a simple implementation - in a more advanced version,
        # we could use embeddings to find the most relevant entities
        
        # Convert query to lowercase for case-insensitive matching
        query_lower = query.lower()
        
        # Keywords to always include certain domains
        domain_keywords = {
            "light": ["light", "lights", "lamp", "lamps", "on", "off", "brightness"],
            "switch": ["switch", "switches", "outlet", "outlets", "on", "off"],
            "sensor": ["temperature", "humidity", "sensor", "reading", "motion", "presence"],
            "climate": ["thermostat", "heat", "ac", "temperature", "cool"],
            "media_player": ["tv", "music", "play", "pause", "volume", "media", "movie"],
            "cover": ["blinds", "shades", "curtains", "garage", "door", "cover"],
            "person": ["person", "people", "who", "home", "away", "present"],
            "weather": ["weather", "forecast", "temperature", "rain", "wind", "snow"],
            "automation": ["automation", "automatic", "trigger", "scene"],
        }
        
        # Determine which domains to include
        domains_to_include = []
        for domain, keywords in domain_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                domains_to_include.append(domain)
        
        # If no specific domains matched, include common important ones
        if not domains_to_include:
            domains_to_include = ["light", "switch", "sensor", "climate", "person"]
        
        # Filter entities by domain and prepare output
        relevant_entities = []
        for entity in ha_state:
            entity_id = entity.get("entity_id", "")
            domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
            
            if domain in domains_to_include:
                state = entity.get("state", "")
                attributes = entity.get("attributes", {})
                friendly_name = attributes.get("friendly_name", entity_id)
                
                relevant_entities.append({
                    "entity_id": entity_id,
                    "state": state,
                    "friendly_name": friendly_name,
                    "attributes": attributes
                })
        
        # Format entities as text
        if not relevant_entities:
            return "No relevant entities found."
        
        formatted_text = ""
        for entity in relevant_entities:
            formatted_text += f"- {entity['friendly_name']} ({entity['entity_id']}): {entity['state']}\n"
            
            # Add key attributes if present
            if entity['attributes']:
                for key, value in entity['attributes'].items():
                    if key in ['temperature', 'humidity', 'brightness', 'volume_level', 'current_position', 'mode']:
                        formatted_text += f"  - {key}: {value}\n"
        
        return formatted_text
    
    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """Build the system prompt with instructions for the AI."""
        system_prompt = """
You are Nexus AI, an intelligent assistant for Home Assistant smart homes. Your goal is to provide helpful, accurate, and concise responses to user queries about their smart home system.

Guidelines:
1. Be concise and friendly in your responses.
2. When the user asks to control devices, respond accordingly and use the ACTION commands below.
3. For complex multi-step operations, break them down into individual actions.
4. Be helpful and creative in suggesting automations and routines.
5. Always prioritize safety and security in your suggestions.

To control Home Assistant devices or create automations, use these special commands:
- To control a device: <ACTION:CALL_SERVICE domain="light" service="turn_on" data={"entity_id": "light.living_room"}>
- To create an automation: <ACTION:CREATE_AUTOMATION name="Evening Lights" trigger={"platform": "sun", "event": "sunset"} action={"service": "light.turn_on", "entity_id": "light.living_room"}>

Remember to include these ACTION commands within your response text where appropriate, and I'll execute them for you.
        """
        
        # Add any custom system instructions from context
        if context and context.get("system_instructions"):
            system_prompt += f"\n\n{context.get('system_instructions')}"
        
        return system_prompt
    
    async def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        """Call OpenAI's API to generate a response."""
        try:
            # Safety check
            if not self.client:
                logger.error("OpenAI client not initialized")
                return "AI service is not available. Please check your OpenAI API key."
            
            response = self.client.chat.completions.create(
                model=self.model_name,  # gpt-4o is the newest model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content
            else:
                logger.error("No response from OpenAI API")
                return "I'm sorry, I couldn't generate a response. Please try again."
        
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            return f"I encountered an error communicating with the AI service: {str(e)}"
    
    def _call_local_model(self, system_prompt: str, user_prompt: str) -> str:
        """Call a local LLM to generate a response."""
        # This is a placeholder for local model integration
        # Implement based on the specific local model library you're using
        return "Local model support is not fully implemented yet."
    
    async def _process_actions(self, response: str) -> None:
        """Process any actions indicated in the AI response."""
        # Find all ACTION commands in the response
        action_calls = re.findall(r'<ACTION:([A-Z_]+)\s+([^>]+)>', response)
        
        for action_type, action_params in action_calls:
            try:
                # Parse parameters from the action string
                params = {}
                # Simple parsing for key="value" pairs
                for match in re.finditer(r'(\w+)=(?:"([^"]*)"|\{([^}]*)\})', action_params):
                    key = match.group(1)
                    if match.group(2) is not None:
                        # String value
                        params[key] = match.group(2)
                    else:
                        # JSON value
                        try:
                            json_str = match.group(3)
                            # Ensure proper JSON format (convert single quotes, add quotes to keys)
                            json_str = json_str.replace("'", '"')
                            json_str = re.sub(r'(\w+):', r'"\1":', json_str)
                            params[key] = json.loads('{' + json_str + '}')
                        except json.JSONDecodeError:
                            logger.error(f"Invalid JSON in action parameters: {match.group(3)}")
                
                # Process the action based on its type
                if action_type == "CALL_SERVICE" and "domain" in params and "service" in params:
                    await self.ha_api.call_service(
                        params["domain"], 
                        params["service"], 
                        params.get("data", {})
                    )
                    logger.info(f"Called service {params['domain']}.{params['service']}")
                
                elif action_type == "CREATE_AUTOMATION" and "name" in params:
                    # Extract parameters for automation
                    name = params["name"]
                    trigger = params.get("trigger", {})
                    action = params.get("action", {})
                    condition = params.get("condition", None)
                    
                    # Convert to lists if needed
                    triggers = [trigger] if not isinstance(trigger, list) else trigger
                    actions = [action] if not isinstance(action, list) else action
                    conditions = [condition] if condition and not isinstance(condition, list) else condition
                    
                    # Save automation
                    self.db.save_automation(
                        name=name,
                        triggers=triggers,
                        actions=actions,
                        conditions=conditions,
                        is_suggested=True,
                        confidence=0.8
                    )
                    logger.info(f"Created automation: {name}")
            
            except Exception as e:
                logger.error(f"Error processing action {action_type}: {str(e)}")
    
    def _clean_response(self, response: str) -> str:
        """Remove action commands from the response."""
        def replace_action(match):
            # Replace with a simple confirmation of what was done
            action_type = match.group(1)
            if action_type == "CALL_SERVICE":
                return "(Action executed)"
            elif action_type == "CREATE_AUTOMATION":
                return "(Automation created)"
            return ""
        
        # Replace action patterns with descriptive text
        cleaned = re.sub(r'<ACTION:[A-Z_]+\s+[^>]+>', replace_action, response)
        return cleaned