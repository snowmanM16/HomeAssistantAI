"""
OpenAI helper functions for Nexus AI
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional
import openai

logger = logging.getLogger(__name__)

class OpenAIHelper:
    """Helper class for OpenAI API interactions"""
    
    def __init__(self):
        """Initialize OpenAI helper"""
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.model = "gpt-4o"  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
        
        # Set API key if available
        if self.api_key:
            openai.api_key = self.api_key
    
    async def chat_completion(self, 
                        messages: List[Dict[str, str]], 
                        temperature: float = 0.7,
                        max_tokens: int = 1000,
                        response_format: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Get a chat completion from OpenAI
        
        Args:
            messages: List of message objects with role and content
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response
            response_format: Optional response format specification
            
        Returns:
            Dictionary with response data
        """
        if not self.api_key:
            return {"success": False, "error": "OpenAI API key not configured"}
        
        try:
            # Build API request
            request_params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            # Add response format if specified
            if response_format:
                request_params["response_format"] = response_format
            
            # Call OpenAI API
            response = openai.chat.completions.create(**request_params)
            
            # Parse response
            content = response.choices[0].message.content
            
            # Handle JSON response format if requested
            if response_format and response_format.get("type") == "json_object":
                try:
                    content = json.loads(content)
                except json.JSONDecodeError as json_err:
                    logger.error(f"Failed to parse JSON response: {json_err}")
                    return {"success": False, "error": f"Failed to parse JSON response: {str(json_err)}"}
            
            return {
                "success": True,
                "content": content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
        
        except Exception as e:
            logger.error(f"Error in OpenAI API call: {e}")
            return {"success": False, "error": str(e)}
    
    async def analyze_home_assistant_data(self, 
                                    ha_data: Dict[str, Any], 
                                    query: str = "",
                                    memories: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Analyze Home Assistant data with OpenAI
        
        Args:
            ha_data: Home Assistant state data
            query: User query for context
            memories: Optional memory items to include
            
        Returns:
            Dictionary with analysis results
        """
        if not self.api_key:
            return {"success": False, "error": "OpenAI API key not configured"}
        
        try:
            # Build system message with HA data
            system_message = "You are an AI assistant for Home Assistant. "
            system_message += "Analyze the following Home Assistant state data to provide insights, answer questions, or suggest automations."
            
            # Prepare messages
            messages = [
                {"role": "system", "content": system_message},
                {"role": "system", "content": f"Home Assistant data: {json.dumps(ha_data)}"}
            ]
            
            # Add memories if available
            if memories:
                memory_content = "User memories and preferences:"
                for memory in memories:
                    memory_content += f"\n- {memory['key']}: {memory['value']}"
                messages.append({"role": "system", "content": memory_content})
            
            # Add user query if provided
            if query:
                messages.append({"role": "user", "content": query})
            else:
                messages.append({"role": "user", "content": "Analyze this Home Assistant data and provide useful insights or suggestions."})
            
            # Request JSON response format
            response_format = {"type": "json_object"}
            
            # Get completion
            result = await self.chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=1500,
                response_format=response_format
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Error analyzing Home Assistant data: {e}")
            return {"success": False, "error": str(e)}
    
    async def detect_patterns(self, entity_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect patterns in entity data using OpenAI
        
        Args:
            entity_data: List of entity state history entries
            
        Returns:
            Dictionary with detected patterns
        """
        if not self.api_key:
            return {"success": False, "error": "OpenAI API key not configured"}
        
        try:
            # Build system message
            system_message = "You are an AI assistant specialized in detecting patterns in smart home usage data. "
            system_message += "Analyze the following entity state history from Home Assistant to identify patterns like: "
            system_message += "time-based patterns (same action at similar times), correlations between entities, presence-based actions, etc."
            
            # Prepare user message with entity data
            user_message = f"Analyze this entity state history data and identify usage patterns:\n"
            user_message += json.dumps(entity_data)
            user_message += "\n\nRespond with a JSON object containing detected patterns with these fields: "
            user_message += "pattern_type, name, description, entities, confidence (0.0-1.0), data (pattern-specific details)"
            
            # Prepare messages
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
            
            # Request JSON response format
            response_format = {"type": "json_object"}
            
            # Get completion
            result = await self.chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=1500,
                response_format=response_format
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Error detecting patterns: {e}")
            return {"success": False, "error": str(e)}
