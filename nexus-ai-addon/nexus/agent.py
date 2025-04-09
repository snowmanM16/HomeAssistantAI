"""
AI agent for Nexus
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional
import asyncio
import openai

logger = logging.getLogger(__name__)

class NexusAgent:
    """Core AI agent that processes queries and integrates with all components."""
    
    def __init__(self, database, ha_api):
        """Initialize the AI agent with components."""
        self.db = database
        self.ha_api = ha_api
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        
        # Initialize OpenAI client if API key is available
        if self.api_key:
            openai.api_key = self.api_key
        
        # System prompt for the AI
        self.system_prompt = """
        You are Nexus AI, an intelligent assistant for Home Assistant. 
        You have access to the user's smart home devices and can control them, 
        check their status, and suggest automations based on patterns.
        
        When responding to user queries:
        1. Be helpful, concise, and friendly
        2. If the user asks about the status of a device, check the most recent state
        3. If the user wants to control a device, execute the command using the Home Assistant API
        4. When appropriate, suggest automations that might be helpful based on the user's patterns
        5. Remember the user's preferences and past interactions
        
        You can use these special commands in your responses if needed:
        - [EXECUTE_SERVICE domain.service {data}] - Execute a Home Assistant service
        - [SAVE_MEMORY key:value] - Remember information for future use
        
        Respond in a conversational manner as if you're a helpful home assistant.
        """
    
    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Process a user query with context and memory."""
        logger.info(f"Processing query: {query}")
        
        if not self.api_key:
            return "Sorry, I'm not fully configured yet. Please set your OpenAI API key in the settings."
        
        # Get relevant Home Assistant states for context
        ha_states = await self.ha_api.get_states()
        
        # Process HA states to extract relevant information for this query
        ha_context = ""
        if ha_states.get("success", False):
            ha_context = self._extract_relevant_ha_states(ha_states["result"], query)
        
        # Get relevant memories
        memories = []
        # TODO: Implement memory retrieval
        
        # Build conversation context
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": f"Current Home Assistant state:\n{ha_context}"}
        ]
        
        # Add memories as system messages
        for memory in memories:
            messages.append({"role": "system", "content": f"Memory: {memory['key']} = {memory['value']}"})
        
        # Add user query
        messages.append({"role": "user", "content": query})
        
        try:
            # Call OpenAI API for response
            response = openai.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
                messages=messages,
                max_tokens=800,
                temperature=0.7
            )
            
            response_text = response.choices[0].message.content
            
            # Process any actions in the response
            await self._process_actions(response_text)
            
            # Remove action commands from the final response
            final_response = self._clean_response(response_text)
            
            return final_response
        
        except Exception as e:
            logger.error(f"Error calling OpenAI: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"
    
    def _extract_relevant_ha_states(self, ha_state: List[Dict[str, Any]], query: str) -> str:
        """Extract relevant Home Assistant states based on the query."""
        # For now, just return a summary of states
        # In a full implementation, this would analyze the query and filter for relevant states
        
        domains = set()
        entity_summary = []
        
        for entity in ha_state:
            entity_id = entity.get("entity_id", "")
            if "." in entity_id:
                domain = entity_id.split(".")[0]
                domains.add(domain)
            
            # Only include certain domains in the summary
            important_domains = {"light", "switch", "binary_sensor", "sensor", "climate", "person", "media_player"}
            if domain in important_domains:
                name = entity.get("attributes", {}).get("friendly_name", entity_id)
                state = entity.get("state", "unknown")
                entity_summary.append(f"{name}: {state}")
        
        # Limit the number of entities to avoid token limits
        if len(entity_summary) > 20:
            entity_summary = entity_summary[:20]
            entity_summary.append(f"... and {len(ha_state) - 20} more entities")
        
        return f"Available domains: {', '.join(sorted(domains))}\n\nEntity states:\n" + "\n".join(entity_summary)
    
    async def _process_actions(self, response: str) -> None:
        """Process any actions indicated in the AI response."""
        # Look for EXECUTE_SERVICE commands
        if "[EXECUTE_SERVICE" in response:
            for line in response.split("\n"):
                if "[EXECUTE_SERVICE" in line:
                    try:
                        # Extract command parts
                        command = line.split("[EXECUTE_SERVICE ")[1].split("]")[0]
                        domain_service, data_str = command.split(" ", 1)
                        domain, service = domain_service.split(".")
                        data = json.loads(data_str)
                        
                        # Execute the service
                        logger.info(f"Executing service {domain}.{service} with data {data}")
                        await self.ha_api.call_service(domain, service, data)
                    except Exception as e:
                        logger.error(f"Error executing service: {e}")
        
        # Look for SAVE_MEMORY commands
        if "[SAVE_MEMORY" in response:
            for line in response.split("\n"):
                if "[SAVE_MEMORY" in line:
                    try:
                        # Extract memory parts
                        memory = line.split("[SAVE_MEMORY ")[1].split("]")[0]
                        key, value = memory.split(":", 1)
                        
                        # Save to memory
                        logger.info(f"Saving memory {key}:{value}")
                        self.db.save_memory(key.strip(), value.strip())
                    except Exception as e:
                        logger.error(f"Error saving memory: {e}")
    
    def _clean_response(self, response: str) -> str:
        """Remove action commands from the response."""
        lines = []
        for line in response.split("\n"):
            if not any(command in line for command in ["[EXECUTE_SERVICE", "[SAVE_MEMORY"]):
                lines.append(line)
        return "\n".join(lines)
