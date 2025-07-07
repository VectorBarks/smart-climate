"""Switch platform for the Smart Climate integration."""

import logging
from typing import Any, Dict

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .offset_engine import OffsetEngine

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Smart Climate switch platform from a config entry."""
    # Retrieve the OffsetEngine instances created in __init__.py
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    offset_engines = entry_data.get("offset_engines", {})
    
    # Create switches for each climate entity
    switches = []
    for entity_id, offset_engine in offset_engines.items():
        # Use config entry title plus entity ID for unique naming
        climate_name = f"{config_entry.title} ({entity_id})"
        switch = LearningSwitch(config_entry, offset_engine, climate_name, entity_id)
        switches.append(switch)
    
    if switches:
        async_add_entities(switches)
    else:
        _LOGGER.warning("No offset engines found for switch setup in entry: %s", config_entry.entry_id)


class LearningSwitch(SwitchEntity):
    """A switch to control the learning functionality of the Smart Climate system."""

    _attr_has_entity_name = True

    def __init__(
        self,
        config_entry: ConfigEntry,
        offset_engine: OffsetEngine,
        climate_name: str,
        entity_id: str,
    ) -> None:
        """Initialize the switch."""
        self._offset_engine = offset_engine
        self._entity_id = entity_id
        
        self._attr_name = "Learning"
        # Include entity ID in unique_id to ensure uniqueness across multiple entities
        safe_entity_id = entity_id.replace(".", "_")
        self._attr_unique_id = f"{config_entry.unique_id}_{safe_entity_id}_learning_switch"
        
        # This links the switch to the same device as the climate entity,
        # ensuring they are grouped together in the Home Assistant UI.
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{config_entry.unique_id}_{safe_entity_id}")},
            name=climate_name,
        )

    @property
    def icon(self) -> str:
        """Return the icon for the switch."""
        return "mdi:brain" if self.is_on else "mdi:brain-off"

    @property
    def is_on(self) -> bool:
        """Return true if the learning system is enabled."""
        return self._offset_engine.is_learning_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the learning system."""
        try:
            self._offset_engine.enable_learning()
            _LOGGER.debug("Learning enabled via switch for %s", self._entity_id)
            # Trigger save to persist the learning state change
            await self._trigger_save()
        except Exception as exc:
            _LOGGER.error("Failed to enable learning for %s: %s", self._entity_id, exc)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the learning system."""
        try:
            self._offset_engine.disable_learning()
            _LOGGER.debug("Learning disabled via switch for %s", self._entity_id)
            # Trigger save to persist the learning state change
            await self._trigger_save()
        except Exception as exc:
            _LOGGER.error("Failed to disable learning for %s: %s", self._entity_id, exc)

    async def _trigger_save(self) -> None:
        """Trigger save of learning data when switch state changes."""
        try:
            await self._offset_engine.async_save_learning_data()
            _LOGGER.debug("Learning data saved after switch state change for %s", self._entity_id)
        except Exception as exc:
            _LOGGER.warning("Failed to save learning data for %s: %s", self._entity_id, exc)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes of the learning system for diagnostics."""
        try:
            learning_info = self._offset_engine.get_learning_info()
            return {
                "samples_collected": learning_info.get("samples", 0),
                "learning_accuracy": learning_info.get("accuracy", 0.0),
                "confidence_level": learning_info.get("confidence", 0.0),
                "patterns_learned": learning_info.get("samples", 0),  # Use samples as patterns count
                "has_sufficient_data": learning_info.get("has_sufficient_data", False),
                "enabled": learning_info.get("enabled", False)
            }
        except Exception as exc:
            _LOGGER.warning("Failed to get learning info for switch attributes: %s", exc)
            return {
                "samples_collected": 0,
                "learning_accuracy": 0.0,
                "confidence_level": 0.0,
                "patterns_learned": 0,
                "has_sufficient_data": False,
                "enabled": False,
                "error": str(exc)
            }

    async def async_added_to_hass(self) -> None:
        """Register callbacks when the entity is added to Home Assistant."""
        # This ensures the switch state updates automatically when the
        # learning state changes from any source.
        try:
            unregister_callback = self._offset_engine.register_update_callback(self._handle_update)
            self.async_on_remove(unregister_callback)
            _LOGGER.debug("Registered update callback for learning switch")
        except Exception as exc:
            _LOGGER.warning("Failed to register update callback: %s", exc)

    @callback
    def _handle_update(self) -> None:
        """Handle updates from the OffsetEngine and schedule a state update."""
        try:
            self.async_write_ha_state()
            _LOGGER.debug("Learning switch state updated")
        except Exception as exc:
            _LOGGER.warning("Failed to update switch state: %s", exc)