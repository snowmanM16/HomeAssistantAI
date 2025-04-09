"""
Weather tools for Nexus AI
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class WeatherTool:
    """Tool for getting weather information from Home Assistant."""
    
    def __init__(self, ha_api):
        """Initialize the weather tool."""
        self.ha_api = ha_api
    
    async def get_current_weather(self) -> Dict[str, Any]:
        """
        Get current weather from Home Assistant.
        
        Returns:
            Dictionary with weather information
        """
        try:
            # Try to find weather entities
            states = await self.ha_api.get_states()
            
            if not states.get("success", False):
                return {"success": False, "message": "Failed to get states from Home Assistant"}
            
            # Look for weather entities
            weather_entities = []
            for entity in states["result"]:
                entity_id = entity.get("entity_id", "")
                if entity_id.startswith("weather."):
                    weather_entities.append(entity)
            
            if not weather_entities:
                return {"success": False, "message": "No weather entities found in Home Assistant"}
            
            # Use the first weather entity
            weather = weather_entities[0]
            
            # Extract weather data
            weather_data = {
                "entity_id": weather.get("entity_id"),
                "state": weather.get("state"),
                "friendly_name": weather.get("attributes", {}).get("friendly_name", "Weather"),
                "temperature": weather.get("attributes", {}).get("temperature"),
                "humidity": weather.get("attributes", {}).get("humidity"),
                "pressure": weather.get("attributes", {}).get("pressure"),
                "wind_speed": weather.get("attributes", {}).get("wind_speed"),
                "wind_bearing": weather.get("attributes", {}).get("wind_bearing"),
                "precipitation": weather.get("attributes", {}).get("precipitation"),
                "forecast": weather.get("attributes", {}).get("forecast", [])
            }
            
            return {"success": True, "weather": weather_data}
        
        except Exception as e:
            logger.error(f"Error getting weather: {e}")
            return {"success": False, "message": f"Error getting weather: {str(e)}"}
    
    async def get_forecast(self, days: int = 5) -> Dict[str, Any]:
        """
        Get weather forecast from Home Assistant.
        
        Args:
            days: Number of days for forecast
            
        Returns:
            Dictionary with forecast information
        """
        try:
            # Get current weather (which includes forecast)
            result = await self.get_current_weather()
            
            if not result.get("success", False):
                return result
            
            # Extract forecast
            forecast = result["weather"].get("forecast", [])
            
            # Limit to requested days
            forecast = forecast[:days] if days < len(forecast) else forecast
            
            return {"success": True, "forecast": forecast}
        
        except Exception as e:
            logger.error(f"Error getting forecast: {e}")
            return {"success": False, "message": f"Error getting forecast: {str(e)}"}
