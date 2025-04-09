"""
AI agent for Nexus
"""
import logging
import os
import json
import re
from typing import Dict, Any, List, Optional

import openai

logger = logging.getLogger("nexus.agent")

class NexusAgent:
    """Core AI agent that processes queries and integrates with all components."""
    
    def __init__(self, database, ha_api):
        """Initialize the AI agent with components."""
        self.database = database
        self.ha_api = ha_api
        
        # Configure OpenAI if API key is available
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if openai_api_key:
            openai.api_key = openai_api_key
            logger.info("OpenAI API configured")
        else:
            logger.warning("OpenAI API key not configured")
        
        # Check if we're using a local model
        self.use_local_model = os.environ.get("USE_LOCAL_MODEL", "false").lower() == "true"
        self.local_model_path = os.environ.get("LOCAL_MODEL_PATH")
        
        if self.use_local_model:
            if not self.local_model_path:
                logger.warning("Local model enabled but no model path specified")
            else:
                logger.info(f"Using local model: {self.local_model_path}")
    
    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Process a user query with context and memory."""
        logger.info(f"Processing query: {query}")
        
        try:
            # Get relevant information for context
            ha_state = await self.ha_api.get_states() if self.ha_api else None
            memories = self.database.get_all_memories() if self.database else []
            settings = self.database.get_all_settings() if self.database else {}
            
            # Extract relevant Home Assistant states based on the query
            relevant_entities = self._extract_relevant_ha_states(ha_state, query) if ha_state else ""
            
            # Construct the system prompt
            system_prompt = f"""You are Nexus AI, an intelligent assistant for Home Assistant.
            
Current time: {context.get('time', 'unknown')}
Current date: {context.get('date', 'unknown')}
Location: {settings.get('location', 'unknown')}

Your capabilities:
1. Control smart home devices through Home Assistant
2. Remember user preferences and important information
3. Suggest automations based on patterns
4. Answer questions about the home state

To execute actions on Home Assistant, use the format [ACTION:domain.service:{{data_json}}]
Example: [ACTION:light.turn_on:{{"entity_id":"light.living_room","brightness":255}}]

Guidelines:
- Be helpful, concise, and friendly
- Prioritize user preferences and safety
- Only include action commands when the user clearly wants to execute something
"""

            # User's query with context
            user_prompt = f"""
{query}

Relevant Home Assistant entities:
{relevant_entities}

{'Additional context: ' + json.dumps(context) if context else ''}
"""

            if not openai.api_key and not self.use_local_model:
                return "AI processing is not available. Please configure an OpenAI API key or local model."
            
            # Use the appropriate model
            if not self.use_local_model:
                # Use OpenAI
                completion = openai.chat.completions.create(
                    model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
                response = completion.choices[0].message.content
            else:
                # Use local model (placeholder - implement based on your local model)
                logger.warning("Local model processing not fully implemented")
                response = "Local model processing is not fully implemented yet."
            
            # Process any actions in the response
            await self._process_actions(response)
            
            # Clean response by removing action commands
            cleaned_response = self._clean_response(response)
            
            return cleaned_response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return f"I'm sorry, I encountered an error: {str(e)}"
    
    def _extract_relevant_ha_states(self, ha_state: List[Dict[str, Any]], query: str) -> str:
        """Extract relevant Home Assistant states based on the query."""
        if not ha_state:
            return "No Home Assistant state available"
        
        # Simple keyword matching - could be enhanced with embeddings/semantic search
        keywords = query.lower().split()
        relevant_entities = []
        
        for entity in ha_state:
            entity_id = entity.get("entity_id", "").lower()
            entity_name = entity.get("attributes", {}).get("friendly_name", "").lower()
            
            # Check if any keywords match this entity
            if any(keyword in entity_id or keyword in entity_name for keyword in keywords):
                attributes = entity.get("attributes", {})
                # Format only the most important attributes
                important_attrs = {k: v for k, v in attributes.items() 
                                 if k in ["friendly_name", "unit_of_measurement", "device_class", "temperature", 
                                          "humidity", "state_class", "brightness", "rgb_color"]}
                
                relevant_entities.append(
                    f"- {entity.get('entity_id')}: {entity.get('state')} " + 
                    (f"({', '.join([f'{k}: {v}' for k, v in important_attrs.items()])})" if important_attrs else "")
                )
        
        # Always include some important entities regardless of keywords
        important_domains = ["person", "binary_sensor.motion", "alarm_control_panel", 
                           "weather", "sensor.temperature", "climate"]
        
        for entity in ha_state:
            entity_id = entity.get("entity_id", "")
            if any(entity_id.startswith(domain) for domain in important_domains) and entity_id not in [e.split(":")[0].strip("- ") for e in relevant_entities]:
                relevant_entities.append(f"- {entity_id}: {entity.get('state')}")
        
        # Limit to a reasonable number
        if len(relevant_entities) > 15:
            relevant_entities = relevant_entities[:15]
            relevant_entities.append("... (more entities available)")
        
        return "\n".join(relevant_entities) if relevant_entities else "No relevant entities found"
    
    async def _process_actions(self, response: str) -> None:
        """Process any actions indicated in the AI response."""
        # Find action patterns: [ACTION:domain.service:{json_data}]
        action_pattern = r'\[ACTION:([a-zA-Z_]+)\.([a-zA-Z_]+):({.*?})\]'
        actions = re.findall(action_pattern, response)
        
        for domain, service, data_str in actions:
            try:
                # Parse the JSON data
                data = json.loads(data_str)
                logger.info(f"Executing action: {domain}.{service} with data: {data}")
                
                # Call the Home Assistant API
                if self.ha_api:
                    result = await self.ha_api.call_service(domain, service, data)
                    logger.info(f"Action result: {result}")
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in action data: {data_str}")
            except Exception as e:
                logger.error(f"Error executing action {domain}.{service}: {e}")
    
    def _clean_response(self, response: str) -> str:
        """Remove action commands from the response."""
        # Replace action patterns with a cleaner message
        action_pattern = r'\[ACTION:([a-zA-Z_]+)\.([a-zA-Z_]+):({.*?})\]'
        
        def replace_action(match):
            domain = match.group(1)
            service = match.group(2)
            data = json.loads(match.group(3))
            
            entity_id = data.get("entity_id", "unknown")
            
            # Customize message based on service
            if service == "turn_on":
                return f"I've turned on {entity_id}."
            elif service == "turn_off":
                return f"I've turned off {entity_id}."
            elif service == "set_temperature":
                return f"I've set {entity_id} to {data.get('temperature', 'a new')} degrees."
            else:
                return f"I've executed {domain}.{service} on {entity_id}."
        
        cleaned = re.sub(action_pattern, replace_action, response)
        return cleaned
