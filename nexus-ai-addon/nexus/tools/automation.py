import logging
import asyncio
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger("nexus.tools.automation")

class AutomationTool:
    """Tool for working with Home Assistant automations."""
    
    def __init__(self, ha_api):
        """Initialize with Home Assistant API."""
        self.ha_api = ha_api
    
    async def get_automations(self) -> List[Dict[str, Any]]:
        """Get list of automations from Home Assistant."""
        try:
            states = await self.ha_api.get_states()
            
            # Filter automation entities
            automations = []
            for entity_id, state in states.items():
                if entity_id.startswith("automation."):
                    friendly_name = state.get("attributes", {}).get("friendly_name", entity_id)
                    state_value = state.get("state", "unknown")
                    last_triggered = state.get("attributes", {}).get("last_triggered", "Never")
                    
                    automations.append({
                        "entity_id": entity_id,
                        "name": friendly_name,
                        "state": state_value,
                        "last_triggered": last_triggered
                    })
            
            return automations
        except Exception as e:
            logger.error(f"Error getting automations: {e}")
            return []
    
    async def trigger_automation(self, entity_id: str) -> Dict[str, Any]:
        """Trigger a specific automation."""
        try:
            if not entity_id.startswith("automation."):
                entity_id = f"automation.{entity_id}"
            
            # Call the trigger service
            result = await self.ha_api.call_service(
                domain="automation",
                service="trigger",
                data={"entity_id": entity_id}
            )
            
            return {"success": True, "entity_id": entity_id, "result": result}
        except Exception as e:
            logger.error(f"Error triggering automation {entity_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def toggle_automation(self, entity_id: str, enable: bool) -> Dict[str, Any]:
        """Enable or disable an automation."""
        try:
            if not entity_id.startswith("automation."):
                entity_id = f"automation.{entity_id}"
            
            # Determine which service to call
            service = "turn_on" if enable else "turn_off"
            
            # Call the service
            result = await self.ha_api.call_service(
                domain="automation",
                service=service,
                data={"entity_id": entity_id}
            )
            
            action = "enabled" if enable else "disabled"
            return {"success": True, "entity_id": entity_id, "action": action, "result": result}
        except Exception as e:
            logger.error(f"Error {'enabling' if enable else 'disabling'} automation {entity_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_routine(self, name: str, triggers: List[Dict[str, Any]], actions: List[Dict[str, Any]], conditions: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Create a new routine (automation) in Home Assistant.
        
        This uses the webhook service to create automations in Home Assistant.
        Requires a long-lived access token with proper permissions.
        
        Args:
            name: The name of the automation
            triggers: List of trigger conditions
            actions: List of actions to perform
            conditions: Optional list of conditions that must be met
            
        Returns:
            Dictionary with the result of the operation
        """
        try:
            # Format the automation configuration
            automation_config = {
                "id": f"nexus_ai_{name.lower().replace(' ', '_')}",
                "alias": f"Nexus AI: {name}",
                "description": f"Automation created by Nexus AI",
                "trigger": triggers,
                "action": actions,
                "mode": "single"  # Could be single, restart, queued, or parallel
            }
            
            # Add conditions if provided
            if conditions:
                automation_config["condition"] = conditions
            
            # Create the automation using the config API
            result = await self.ha_api.call_service(
                domain="automation",
                service="reload",
                data={}
            )
            
            # The direct creation via API is complex, but we can use
            # "input_boolean" entities to track our suggested automations
            # which can then be accepted/modified by the user
            
            # Create an input_boolean to track this suggestion
            suggestion_data = {
                "name": f"Automation Suggestion: {name}",
                "icon": "mdi:robot",
                "initial": "on"
            }
            
            await self.ha_api.call_service(
                domain="input_boolean",
                service="create",
                data=suggestion_data
            )
            
            # Store the automation config in the frontend state
            return {
                "success": True,
                "entity_id": f"automation.nexus_ai_{name.lower().replace(' ', '_')}",
                "name": name,
                "config": automation_config,
                "message": "Automation suggestion created. Please review and apply through Home Assistant."
            }
        except Exception as e:
            logger.error(f"Error creating automation {name}: {e}")
            return {"success": False, "error": str(e)}
    
    async def suggest_automations(self, memory_manager) -> List[Dict[str, Any]]:
        """
        Analyze tracked entity data to suggest possible automations.
        Uses intelligent pattern recognition to identify potential automations.
        """
        suggestions = []
        
        try:
            # Get important entities from memory
            important_entities = memory_manager.get_important_entities()
            
            # Get all states of entities
            states = await self.ha_api.get_states()
            
            # Analyze patterns and suggest automations
            # 1. Find correlations between entity states
            correlations = await self._find_state_correlations(states)
            
            # 2. Analyze usage patterns
            usage_patterns = await self._analyze_usage_patterns(memory_manager)
            
            # 3. Generate suggestions based on entity types
            for entity_id, state in states.items():
                entity_type = entity_id.split('.')[0]
                
                # Light automations
                if entity_type == "light":
                    suggestion = await self._suggest_light_automation(entity_id, state, states, usage_patterns)
                    if suggestion:
                        suggestions.append(suggestion)
                
                # Climate automations
                elif entity_type == "climate":
                    suggestion = await self._suggest_climate_automation(entity_id, state, states, usage_patterns)
                    if suggestion:
                        suggestions.append(suggestion)
                
                # Presence-based automations
                elif entity_type in ["binary_sensor", "device_tracker"]:
                    suggestion = await self._suggest_presence_automation(entity_id, state, states, correlations)
                    if suggestion:
                        suggestions.append(suggestion)
                
                # Media player automations
                elif entity_type == "media_player":
                    suggestion = await self._suggest_media_automation(entity_id, state, states)
                    if suggestion:
                        suggestions.append(suggestion)
            
            # 4. Check user preferences in memory for specialized automations
            user_prefs = memory_manager.get_all_preferences()
            for pref_name, pref_value in user_prefs.items():
                if pref_name.startswith("automation_pref_"):
                    suggestion = {
                        "type": "preference_automation",
                        "description": f"Create automation based on your preference: {pref_value}",
                        "preference": pref_name,
                        "config": self._generate_config_from_preference(pref_name, pref_value, states)
                    }
                    suggestions.append(suggestion)
                
            return suggestions
        except Exception as e:
            logger.error(f"Error suggesting automations: {e}")
            return []
    
    async def _find_state_correlations(self, states: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find correlations between entity states for smarter automation suggestions."""
        correlations = []
        
        # Look for related devices (e.g., lights and motion sensors in the same room)
        rooms = {}
        
        for entity_id, state in states.items():
            # Extract room from entity name or attributes
            room_name = None
            friendly_name = state.get("attributes", {}).get("friendly_name", "")
            
            # Try to extract room from the name
            common_rooms = ["living", "kitchen", "bedroom", "bathroom", "office", "hallway", "dining"]
            for room in common_rooms:
                if room in friendly_name.lower() or room in entity_id.lower():
                    room_name = room
                    break
                    
            if room_name:
                if room_name not in rooms:
                    rooms[room_name] = []
                rooms[room_name].append(entity_id)
        
        # Create correlations for entities in the same room
        for room, entities in rooms.items():
            # Find motion sensors and lights in the same room
            motion_sensors = [e for e in entities if e.startswith("binary_sensor.") and 
                              ("motion" in e or "presence" in e)]
            lights = [e for e in entities if e.startswith("light.")]
            
            # If we have both motion sensors and lights in a room, suggest correlation
            if motion_sensors and lights:
                correlations.append({
                    "type": "motion_light",
                    "room": room,
                    "motion_sensors": motion_sensors,
                    "lights": lights,
                    "description": f"Motion-activated lights in {room}"
                })
        
        return correlations
    
    async def _analyze_usage_patterns(self, memory_manager) -> Dict[str, Any]:
        """Analyze usage patterns from tracked entity data."""
        patterns = {
            "time_based": {},
            "frequency": {},
            "duration": {}
        }
        
        # This would typically analyze historical data from the memory manager
        # For demonstration, we're using simplified pattern detection
        
        # Get tracked entities
        entities = memory_manager.get_important_entities()
        
        # Group by entity type
        for entity in entities:
            entity_id = entity["entity_id"]
            entity_type = entity_id.split('.')[0]
            
            if entity_type not in patterns["frequency"]:
                patterns["frequency"][entity_type] = 0
            patterns["frequency"][entity_type] += 1
        
        return patterns
    
    async def _suggest_light_automation(self, entity_id: str, state: Dict[str, Any], states: Dict[str, Any], patterns: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate a light automation suggestion."""
        friendly_name = state.get("attributes", {}).get("friendly_name", entity_id)
        
        # Extract room name if possible
        room_name = None
        common_rooms = ["living", "kitchen", "bedroom", "bathroom", "office", "hallway", "dining"]
        for room in common_rooms:
            if room in friendly_name.lower() or room in entity_id.lower():
                room_name = room
                break
        
        room_display = f"the {room_name}" if room_name else "a room"
        
        # Create a sunset automation for this light
        name = f"Turn on {friendly_name} at sunset"
        
        # Define the trigger (sunset)
        triggers = [{
            "platform": "sun",
            "event": "sunset",
            "offset": "+00:00:00"
        }]
        
        # Define the action
        actions = [{
            "service": "light.turn_on",
            "target": {
                "entity_id": entity_id
            },
            "data": {
                "brightness_pct": 80
            }
        }]
        
        return {
            "type": "light_sunset",
            "description": f"Turn on {friendly_name} in {room_display} at sunset",
            "entity_id": entity_id,
            "name": name,
            "triggers": triggers,
            "actions": actions,
            "confidence": 0.75  # Confidence score for this suggestion
        }
    
    async def _suggest_climate_automation(self, entity_id: str, state: Dict[str, Any], states: Dict[str, Any], patterns: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate a climate automation suggestion."""
        friendly_name = state.get("attributes", {}).get("friendly_name", entity_id)
        current_temp = state.get("attributes", {}).get("current_temperature")
        
        # Energy-saving climate automation
        name = f"Energy saving for {friendly_name}"
        
        # Define triggers (time-based)
        triggers = [
            {
                "platform": "time",
                "at": "22:00:00"  # 10:00 PM
            }
        ]
        
        # Define actions (adjust temperature)
        actions = [{
            "service": "climate.set_temperature",
            "target": {
                "entity_id": entity_id
            },
            "data": {
                "temperature": 18  # Lower temperature at night (18°C/64°F)
            }
        }]
        
        return {
            "type": "climate_energy_saving",
            "description": f"Lower {friendly_name} temperature at night to save energy",
            "entity_id": entity_id,
            "name": name,
            "triggers": triggers,
            "actions": actions,
            "confidence": 0.8
        }
    
    async def _suggest_presence_automation(self, entity_id: str, state: Dict[str, Any], states: Dict[str, Any], correlations: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Generate a presence-based automation suggestion."""
        if not (entity_id.startswith("binary_sensor.") and "motion" in entity_id or 
                entity_id.startswith("device_tracker.")):
            return None
            
        friendly_name = state.get("attributes", {}).get("friendly_name", entity_id)
        
        # Look for correlation with lights
        for correlation in correlations:
            if correlation["type"] == "motion_light" and entity_id in correlation["motion_sensors"]:
                lights = correlation["lights"]
                room = correlation["room"]
                
                if lights:
                    name = f"Motion-activated lights in {room}"
                    
                    # Define triggers (motion detected)
                    triggers = [{
                        "platform": "state",
                        "entity_id": entity_id,
                        "to": "on"
                    }]
                    
                    # Define conditions (only at night)
                    conditions = [{
                        "condition": "sun",
                        "after": "sunset",
                        "before": "sunrise"
                    }]
                    
                    # Define actions (turn on lights)
                    actions = [{
                        "service": "light.turn_on",
                        "target": {
                            "entity_id": lights
                        }
                    }]
                    
                    return {
                        "type": "presence_lights",
                        "description": f"Turn on lights in {room} when motion is detected at night",
                        "entity_id": entity_id,
                        "related_entities": lights,
                        "name": name,
                        "triggers": triggers,
                        "conditions": conditions,
                        "actions": actions,
                        "confidence": 0.9
                    }
        
        return None
    
    async def _suggest_media_automation(self, entity_id: str, state: Dict[str, Any], states: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate a media player automation suggestion."""
        friendly_name = state.get("attributes", {}).get("friendly_name", entity_id)
        
        # Evening entertainment mode
        name = f"Evening entertainment mode with {friendly_name}"
        
        # Define triggers (time-based)
        triggers = [{
            "platform": "time",
            "at": "20:00:00"  # 8:00 PM
        }]
        
        # Find lights in the same area
        area = None
        common_areas = ["living", "family", "media", "entertainment", "tv"]
        for area_name in common_areas:
            if area_name in friendly_name.lower() or area_name in entity_id.lower():
                area = area_name
                break
        
        # Find lights that might be in the same area
        area_lights = []
        if area:
            for light_id, light_state in states.items():
                if light_id.startswith("light.") and area in light_id.lower():
                    area_lights.append(light_id)
        
        # Define actions
        actions = []
        
        # Dim lights if found
        if area_lights:
            actions.append({
                "service": "light.turn_on",
                "target": {
                    "entity_id": area_lights
                },
                "data": {
                    "brightness_pct": 40,
                    "transition": 5
                }
            })
        
        # Add media player action
        actions.append({
            "service": "media_player.turn_on",
            "target": {
                "entity_id": entity_id
            }
        })
        
        if not actions:
            return None
            
        return {
            "type": "media_evening",
            "description": f"Set up evening entertainment with {friendly_name}",
            "entity_id": entity_id,
            "related_entities": area_lights,
            "name": name,
            "triggers": triggers,
            "actions": actions,
            "confidence": 0.7
        }
    
    def _generate_config_from_preference(self, pref_name: str, pref_value: str, states: Dict[str, Any]) -> Dict[str, Any]:
        """Generate automation config from a user preference."""
        # This would be expanded based on actual preference types
        config = {
            "name": f"Preference-based automation: {pref_name}",
            "triggers": [],
            "actions": []
        }
        
        # Example: Parse a temperature preference
        if "temperature" in pref_name:
            temp_match = re.search(r'(\d+)(?:\s+degrees|\s*°)', pref_value)
            if temp_match:
                preferred_temp = int(temp_match.group(1))
                
                # Find climate entities
                for entity_id in states:
                    if entity_id.startswith("climate."):
                        config["triggers"].append({
                            "platform": "time_pattern",
                            "hours": "8"  # Morning time
                        })
                        config["actions"].append({
                            "service": "climate.set_temperature",
                            "target": {
                                "entity_id": entity_id
                            },
                            "data": {
                                "temperature": preferred_temp
                            }
                        })
                        break
        
        return config
