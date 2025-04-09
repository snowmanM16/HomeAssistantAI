import os
import json
import logging
from typing import Dict, List, Any, Optional
import openai
from openai import OpenAI

# Configure logging
logger = logging.getLogger("nexus.openai")

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

async def ask_gpt(prompt: str, system_prompt: Optional[str] = None, context: Optional[str] = None) -> str:
    """
    Send a prompt to OpenAI and get a response.
    
    Args:
        prompt: The user query or prompt
        system_prompt: Optional system instructions to guide the AI
        context: Optional additional context to include
        
    Returns:
        The AI response as a string
    """
    try:
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add context if provided
        if context:
            messages.append({"role": "system", "content": f"Additional context: {context}"})
        
        # Add user prompt
        messages.append({"role": "user", "content": prompt})
        
        # Log the request (truncated for privacy)
        logger.debug(f"Sending request to OpenAI: {prompt[:50]}...")
        
        # Make the API call
        # The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
        )
        
        # Extract and return the response
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error in OpenAI API call: {e}")
        return f"I encountered an error while processing your request: {str(e)}"

async def extract_actions(text: str) -> List[Dict[str, Any]]:
    """
    Extract Home Assistant actions from text.
    
    Args:
        text: The text to parse for actions
        
    Returns:
        A list of action dictionaries with domain, service, and data
    """
    try:
        # Create a structured prompt to extract actions
        system_prompt = """
        Extract Home Assistant service calls from the text.
        If there are no actions to perform, return an empty list.
        For each action, include:
        1. domain (e.g., light, switch, climate)
        2. service (e.g., turn_on, turn_off, set_temperature)
        3. data (any parameters needed, like entity_id)
        
        Format your response as a valid JSON list of actions.
        Example: [{"domain": "light", "service": "turn_on", "data": {"entity_id": "light.living_room"}}]
        """
        
        user_prompt = f"Extract Home Assistant actions from this text: {text}"
        
        # Make the API call with response_format={"type": "json_object"}
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        # Parse the JSON response
        try:
            result = json.loads(response.choices[0].message.content)
            # Ensure we got a list of actions (could be an empty list)
            if not isinstance(result, dict) or "actions" not in result:
                return []
            return result["actions"]
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON response from OpenAI")
            return []
            
    except Exception as e:
        logger.error(f"Error extracting actions: {e}")
        return []