"""
OpenAI integration helper for Nexus AI
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List

# The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenAIHelper:
    """Helper class for OpenAI API interactions."""
    
    def __init__(self):
        """Initialize the OpenAI helper."""
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)
        
    def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Process a natural language query with context."""
        try:
            if not self.api_key:
                return "OpenAI API key not configured. Please set it in the settings."
            
            # Build messages with system prompt and user query
            messages = [
                {"role": "system", "content": self._build_system_prompt(context)},
                {"role": "user", "content": query}
            ]
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4o",  # Use the latest model
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error processing query with OpenAI: {str(e)}")
            return f"Error processing your request: {str(e)}"
    
    def _build_system_prompt(self, context: Optional[Dict[str, Any]] = None) -> str:
        """Build a system prompt with context information."""
        system_prompt = """
        You are Nexus AI, an intelligent assistant for home automation integrated with Home Assistant.
        
        Your capabilities include:
        1. Answering questions about the home state
        2. Controlling home automation devices (lights, switches, etc.)
        3. Creating and suggesting automations
        4. Detecting patterns in home usage
        5. Learning preferences and remembering important information
        
        Respond in a helpful, friendly, and concise manner. When asked to control devices or create
        automations, be specific about what actions you're taking.
        """
        
        # Add context information if available
        if context:
            if "entities" in context:
                system_prompt += "\n\nCurrent Home State:\n"
                for entity in context["entities"]:
                    system_prompt += f"- {entity['friendly_name'] or entity['entity_id']}: {entity['last_state']}\n"
            
            if "memories" in context:
                system_prompt += "\n\nRelevant Information I Remember:\n"
                for memory in context["memories"]:
                    system_prompt += f"- {memory['key']}: {memory['value']}\n"
            
            if "patterns" in context:
                system_prompt += "\n\nDetected Patterns:\n"
                for pattern in context["patterns"]:
                    system_prompt += f"- {pattern['name']}: {pattern['pattern_type']} pattern (confidence: {pattern['confidence']})\n"
        
        return system_prompt
    
    def generate_automation(self, 
                           trigger_description: str, 
                           entities: List[Dict[str, Any]],
                           patterns: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Generate an automation based on description and available entities."""
        try:
            if not self.api_key:
                return {"error": "OpenAI API key not configured"}
            
            # Build the prompt
            prompt = f"""
            Create a Home Assistant automation based on this description: "{trigger_description}"
            
            Available entities:
            """
            
            for entity in entities[:20]:  # Limit entities to avoid token limits
                prompt += f"- {entity['entity_id']} ({entity['friendly_name'] or 'No name'}): domain={entity['domain']}, current state={entity['last_state']}\n"
            
            if patterns:
                prompt += "\nRelevant detected patterns:\n"
                for pattern in patterns:
                    prompt += f"- {pattern['name']}: {pattern['pattern_type']} pattern\n"
            
            prompt += """
            Respond with a JSON object containing these fields:
            - name: A short, descriptive name for the automation
            - description: A longer explanation of what this automation does
            - triggers: Array of Home Assistant trigger configurations
            - conditions: Array of conditions (can be empty)
            - actions: Array of actions to perform
            - confidence: Number between 0 and 1 indicating how confident you are in this suggestion
            
            Only respond with the JSON object, no other text.
            """
            
            # Call OpenAI API with JSON response format
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            # Parse the response
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Error generating automation: {str(e)}")
            return {"error": str(e)}
            
    def analyze_pattern(self, 
                       entity_histories: Dict[str, List[Dict[str, Any]]],
                       existing_patterns: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Analyze entity histories to detect patterns."""
        try:
            if not self.api_key:
                return {"error": "OpenAI API key not configured"}
            
            # Build the prompt
            prompt = """
            Analyze these entity state histories to detect possible usage patterns:
            
            """
            
            for entity_id, history in entity_histories.items():
                prompt += f"\nEntity: {entity_id}\n"
                prompt += "Recent states:\n"
                for i, state in enumerate(history[:10]):  # Limit history items to avoid token limits
                    prompt += f"- {state['timestamp']}: {state['state']}\n"
            
            if existing_patterns:
                prompt += "\nPatterns already detected:\n"
                for pattern in existing_patterns:
                    prompt += f"- {pattern['name']}: {pattern['pattern_type']} pattern\n"
            
            prompt += """
            Respond with a JSON object containing these fields:
            - patterns: Array of pattern objects with these fields:
              - name: Descriptive name for the pattern
              - pattern_type: One of "time-based", "correlation", "presence", "usage", "periodic"
              - entities: Array of entity IDs involved in the pattern
              - data: Object with pattern-specific data
              - confidence: Number between 0 and 1 indicating confidence
            
            Only respond with the JSON object, no other text.
            """
            
            # Call OpenAI API with JSON response format
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            # Parse the response
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing patterns: {str(e)}")
            return {"error": str(e)}