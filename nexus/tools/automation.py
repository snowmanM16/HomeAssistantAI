"""
Automation tools for Nexus AI
"""
import logging
from typing import Dict, List, Any, Optional
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AutomationTool:
    """Tool for creating and managing Home Assistant automations."""
    
    def __init__(self, database, ha_api):
        """Initialize the automation tool."""
        self.db = database
        self.ha_api = ha_api
    
    async def create_automation(self, name: str, triggers: List[Dict[str, Any]], 
                             actions: List[Dict[str, Any]], conditions: Optional[List[Dict[str, Any]]] = None,
                             description: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new automation in Home Assistant.
        
        Args:
            name: Name of the automation
            triggers: List of trigger configurations
            actions: List of action configurations
            conditions: Optional list of condition configurations
            description: Optional description of the automation
            
        Returns:
            Dictionary with status and result information
        """
        # Create automation configuration
        automation_config = {
            "id": f"nexus_ai.{name.lower().replace(' ', '_')}",
            "alias": name,
            "description": description or f"Automation created by Nexus AI on {datetime.now().strftime('%Y-%m-%d')}",
            "trigger": triggers,
            "action": actions,
        }
        
        if conditions:
            automation_config["condition"] = conditions
        
        # Add to Home Assistant
        try:
            # First, save to database
            automation_id = self.db.save_automation(
                name=name,
                triggers=triggers,
                actions=actions,
                conditions=conditions,
                description=description
            )
            
            if not automation_id:
                return {"success": False, "message": "Failed to save automation to database"}
            
            # Then, add to Home Assistant
            result = await self.ha_api.call_service("automation", "reload", {})
            if not result.get("success", False):
                return {"success": False, "message": "Failed to reload automations in Home Assistant"}
            
            return {"success": True, "automation_id": automation_id, "message": f"Automation '{name}' created successfully"}
            
        except Exception as e:
            logger.error(f"Error creating automation: {e}")
            return {"success": False, "message": f"Error creating automation: {str(e)}"}
    
    async def suggest_automations(self) -> List[Dict[str, Any]]:
        """
        Generate automation suggestions based on patterns.
        
        Returns:
            List of suggested automations
        """
        # Get patterns from database
        patterns = self.db.get_patterns(min_confidence=0.6)
        
        suggestions = []
        
        for pattern in patterns:
            # Skip patterns that already have automations
            automation_exists = False
            # TODO: Check if automation exists for this pattern
            
            if automation_exists:
                continue
            
            # Generate suggestion based on pattern type
            if pattern["pattern_type"] == "time-based":
                suggestion = self._suggest_time_based_automation(pattern)
            elif pattern["pattern_type"] == "correlation":
                suggestion = self._suggest_correlation_automation(pattern)
            elif pattern["pattern_type"] == "presence":
                suggestion = self._suggest_presence_automation(pattern)
            else:
                continue
            
            if suggestion:
                suggestions.append(suggestion)
        
        return suggestions
    
    def _suggest_time_based_automation(self, pattern: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate a time-based automation suggestion."""
        try:
            # Extract pattern data
            time_data = pattern["data"].get("time", {})
            entity_id = pattern["entities"][0] if pattern["entities"] else None
            
            if not entity_id or not time_data:
                return None
            
            # Get entity info
            entity = self.db.get_entity(entity_id)
            if not entity:
                return None
            
            # Create suggestion
            triggers = [{
                "platform": "time",
                "at": time_data.get("time", "17:00:00")
            }]
            
            actions = [{
                "service": f"{entity['domain']}.turn_on",
                "target": {
                    "entity_id": entity_id
                }
            }]
            
            return {
                "name": f"Turn on {entity['friendly_name']} at {time_data.get('time', '17:00')}",
                "description": f"Based on your usage pattern of {entity['friendly_name']}",
                "triggers": triggers,
                "actions": actions,
                "confidence": pattern["confidence"],
                "pattern_id": pattern["id"]
            }
        
        except Exception as e:
            logger.error(f"Error suggesting time-based automation: {e}")
            return None
    
    def _suggest_correlation_automation(self, pattern: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate a correlation-based automation suggestion."""
        try:
            # Extract pattern data
            if len(pattern["entities"]) < 2:
                return None
            
            trigger_entity = pattern["entities"][0]
            action_entity = pattern["entities"][1]
            
            # Get entity info
            trigger_entity_info = self.db.get_entity(trigger_entity)
            action_entity_info = self.db.get_entity(action_entity)
            
            if not trigger_entity_info or not action_entity_info:
                return None
            
            # Create suggestion
            triggers = [{
                "platform": "state",
                "entity_id": trigger_entity,
                "to": pattern["data"].get("trigger_state", "on")
            }]
            
            actions = [{
                "service": f"{action_entity_info['domain']}.turn_on",
                "target": {
                    "entity_id": action_entity
                }
            }]
            
            return {
                "name": f"Turn on {action_entity_info['friendly_name']} when {trigger_entity_info['friendly_name']} is {pattern['data'].get('trigger_state', 'on')}",
                "description": f"Based on correlation between {trigger_entity_info['friendly_name']} and {action_entity_info['friendly_name']}",
                "triggers": triggers,
                "actions": actions,
                "confidence": pattern["confidence"],
                "pattern_id": pattern["id"]
            }
        
        except Exception as e:
            logger.error(f"Error suggesting correlation automation: {e}")
            return None
    
    def _suggest_presence_automation(self, pattern: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate a presence-based automation suggestion."""
        try:
            # Extract pattern data
            presence_entity = None
            for entity in pattern["entities"]:
                if entity.startswith("person.") or entity.startswith("device_tracker."):
                    presence_entity = entity
                    break
            
            if not presence_entity:
                return None
            
            # Get action entities (lights, etc.)
            action_entities = [e for e in pattern["entities"] if e != presence_entity]
            if not action_entities:
                return None
            
            # Get entity info
            presence_entity_info = self.db.get_entity(presence_entity)
            if not presence_entity_info:
                return None
            
            # Create suggestion
            triggers = [{
                "platform": "state",
                "entity_id": presence_entity,
                "to": "home"
            }]
            
            actions = []
            for entity_id in action_entities:
                entity_info = self.db.get_entity(entity_id)
                if entity_info:
                    actions.append({
                        "service": f"{entity_info['domain']}.turn_on",
                        "target": {
                            "entity_id": entity_id
                        }
                    })
            
            if not actions:
                return None
            
            return {
                "name": f"Turn on lights when {presence_entity_info['friendly_name']} arrives home",
                "description": f"Based on presence pattern of {presence_entity_info['friendly_name']}",
                "triggers": triggers,
                "actions": actions,
                "confidence": pattern["confidence"],
                "pattern_id": pattern["id"]
            }
        
        except Exception as e:
            logger.error(f"Error suggesting presence automation: {e}")
            return None
