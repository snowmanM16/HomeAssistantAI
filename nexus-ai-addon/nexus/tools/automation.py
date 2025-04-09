import logging
import asyncio
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
    
    async def create_routine(self, name: str, triggers: List[Dict[str, Any]], actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a new routine (automation) in Home Assistant.
        
        NOTE: This is a more advanced feature that requires the config entries integration.
        Home Assistant typically doesn't allow automations to be created via the API
        without configuration changes.
        """
        logger.warning("Creating automations via API is not fully supported in Home Assistant")
        return {
            "success": False, 
            "error": "Creating automations programmatically requires additional configuration. Please create automations through the Home Assistant UI."
        }
    
    async def suggest_automations(self, memory_manager) -> List[Dict[str, Any]]:
        """
        Analyze tracked entity data to suggest possible automations.
        This is a simplified implementation that would need to be expanded.
        """
        suggestions = []
        
        try:
            # Get important entities from memory
            important_entities = memory_manager.get_important_entities()
            
            # Get states of entities
            states = await self.ha_api.get_states()
            
            # Simple logic for suggestions - this would be expanded in a real implementation
            for entity in important_entities:
                entity_id = entity["entity_id"]
                
                # Example: Suggest automation for lights based on time patterns
                if entity_id.startswith("light."):
                    suggestions.append({
                        "type": "light_automation",
                        "description": f"Create a schedule for {entity_id}",
                        "entity_id": entity_id
                    })
                
                # Example: Suggest automation for climate based on presence
                if entity_id.startswith("climate."):
                    suggestions.append({
                        "type": "climate_automation",
                        "description": f"Adjust {entity_id} based on presence detection",
                        "entity_id": entity_id
                    })
            
            return suggestions
        except Exception as e:
            logger.error(f"Error suggesting automations: {e}")
            return []
