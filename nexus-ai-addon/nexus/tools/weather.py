import logging
import asyncio
from typing import Dict, Any, Optional

logger = logging.getLogger("nexus.tools.weather")

class WeatherTool:
    """Tool for accessing weather data from Home Assistant."""
    
    def __init__(self, ha_api):
        """Initialize with Home Assistant API."""
        self.ha_api = ha_api
    
    async def get_current_weather(self) -> Dict[str, Any]:
        """Get current weather information from Home Assistant weather entities."""
        try:
            # Get states
            states = await self.ha_api.get_states()
            
            # Look for weather entities
            weather_entities = {
                entity_id: state for entity_id, state in states.items()
                if entity_id.startswith("weather.")
            }
            
            if not weather_entities:
                logger.warning("No weather entities found")
                return {"error": "No weather entities found in Home Assistant"}
            
            # Use the first weather entity
            weather_entity_id = list(weather_entities.keys())[0]
            weather_state = weather_entities[weather_entity_id]
            
            # Extract relevant data
            weather_data = {
                "entity_id": weather_entity_id,
                "state": weather_state.get("state", "unknown"),
                "temperature": self._get_attr(weather_state, "temperature"),
                "temperature_unit": self._get_attr(weather_state, "temperature_unit"),
                "humidity": self._get_attr(weather_state, "humidity"),
                "pressure": self._get_attr(weather_state, "pressure"),
                "wind_speed": self._get_attr(weather_state, "wind_speed"),
                "wind_bearing": self._get_attr(weather_state, "wind_bearing"),
                "forecast": self._get_attr(weather_state, "forecast", [])
            }
            
            return weather_data
        except Exception as e:
            logger.error(f"Error getting weather data: {e}")
            return {"error": str(e)}
    
    async def get_temperature_sensors(self) -> Dict[str, Any]:
        """Get data from temperature sensors in Home Assistant."""
        try:
            # Get states
            states = await self.ha_api.get_states()
            
            # Look for temperature sensor entities
            temp_sensors = {}
            for entity_id, state in states.items():
                if entity_id.startswith("sensor.") and "temperature" in entity_id.lower():
                    # Check if it has a unit_of_measurement attribute that is temperature related
                    unit = self._get_attr(state, "unit_of_measurement")
                    if unit in ["°C", "°F", "K", "C", "F"]:
                        friendly_name = self._get_attr(state, "friendly_name", entity_id)
                        temp_sensors[entity_id] = {
                            "name": friendly_name,
                            "temperature": state.get("state", "unknown"),
                            "unit": unit
                        }
            
            return {"sensors": temp_sensors}
        except Exception as e:
            logger.error(f"Error getting temperature sensors: {e}")
            return {"error": str(e)}
    
    def _get_attr(self, state: Dict[str, Any], attr_name: str, default=None) -> Any:
        """Helper to get attribute from state."""
        return state.get("attributes", {}).get(attr_name, default)
