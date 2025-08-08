"""Button platform for the Smart Climate integration."""

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .offset_engine import OffsetEngine
from .data_store import SmartClimateDataStore

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Smart Climate button platform from a config entry."""
    # Retrieve the OffsetEngine and DataStore instances created in __init__.py
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    offset_engines = entry_data.get("offset_engines", {})
    data_stores = entry_data.get("data_stores", {})
    thermal_components = entry_data.get("thermal_components", {})
    
    # Create buttons for each climate entity
    buttons = []
    
    # Create training data reset buttons
    for entity_id, offset_engine in offset_engines.items():
        # Use config entry title plus entity ID for unique naming
        climate_name = f"{config_entry.title} ({entity_id})"
        
        # Get the corresponding data store
        data_store = data_stores.get(entity_id)
        if data_store is None:
            _LOGGER.warning(
                "No data store found for entity %s, button will reset memory only",
                entity_id
            )
        
        button = ResetTrainingDataButton(
            config_entry, offset_engine, data_store, climate_name, entity_id
        )
        buttons.append(button)
    
    # Create thermal reset buttons for entities with thermal components
    for entity_id, components in thermal_components.items():
        if "thermal_manager" in components:
            thermal_button = SmartClimateThermalResetButton(
                hass, config_entry, entity_id
            )
            buttons.append(thermal_button)
            _LOGGER.debug("Created thermal reset button for %s", entity_id)
    
    if buttons:
        async_add_entities(buttons)
        _LOGGER.info("Created %d buttons for entry: %s", len(buttons), config_entry.entry_id)
    else:
        _LOGGER.warning("No offset engines found for button setup in entry: %s", config_entry.entry_id)


class ResetTrainingDataButton(ButtonEntity):
    """A button to reset/clear all learning training data."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        config_entry: ConfigEntry,
        offset_engine: OffsetEngine,
        data_store: SmartClimateDataStore,
        climate_name: str,
        entity_id: str,
    ) -> None:
        """Initialize the button."""
        self._offset_engine = offset_engine
        self._data_store = data_store
        self._entity_id = entity_id
        
        self._attr_name = "Reset Training Data"
        # Include entity ID in unique_id to ensure uniqueness across multiple entities
        safe_entity_id = entity_id.replace(".", "_")
        self._attr_unique_id = f"{config_entry.unique_id}_{safe_entity_id}_reset_training_data"
        
        # This links the button to the same device as the climate entity,
        # ensuring they are grouped together in the Home Assistant UI.
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{config_entry.unique_id}_{safe_entity_id}")},
            name=climate_name,
        )

    @property
    def icon(self) -> str:
        """Return the icon for the button."""
        return "mdi:database-remove"

    async def async_press(self) -> None:
        """Handle the button press."""
        try:
            _LOGGER.info("Reset training data button pressed for %s", self._entity_id)
            
            # Reset the learning data in the offset engine
            self._offset_engine.reset_learning()
            _LOGGER.debug("Learning data reset in offset engine for %s", self._entity_id)
            
            # Delete the persisted learning data file if data store exists
            if self._data_store:
                try:
                    await self._data_store.delete_learning_data()
                    _LOGGER.debug("Learning data file deleted for %s", self._entity_id)
                except Exception as exc:
                    _LOGGER.warning(
                        "Failed to delete learning data file for %s: %s",
                        self._entity_id, exc
                    )
            
            _LOGGER.info("Training data reset completed for %s", self._entity_id)
            
        except Exception as exc:
            _LOGGER.error(
                "Failed to reset training data for %s: %s",
                self._entity_id, exc, exc_info=True
            )


class SmartClimateThermalResetButton(ButtonEntity):
    """A button to reset thermal data (tau values, probe history, thermal state)."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        entity_id: str,
    ) -> None:
        """Initialize the thermal reset button."""
        self.hass = hass
        self._config_entry = config_entry
        self._entity_id = entity_id
        
        self._attr_name = "Reset Thermal Data"
        # Create unique_id per architecture spec: {entity_id}_thermal_reset
        safe_entity_id = entity_id.replace(".", "_")
        self._attr_unique_id = f"{safe_entity_id}_thermal_reset"
        
        # Link to parent climate entity device for proper grouping
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, safe_entity_id)},
        )

    @property
    def icon(self) -> str:
        """Return the icon for the button."""
        return "mdi:thermometer-off"

    def _get_thermal_manager(self):
        """Get thermal manager for this entity from hass.data."""
        try:
            entry_data = self.hass.data[DOMAIN][self._config_entry.entry_id]
            thermal_components = entry_data.get("thermal_components", {})
            components = thermal_components.get(self._entity_id, {})
            return components.get("thermal_manager")
        except (KeyError, AttributeError) as exc:
            _LOGGER.debug("Error getting thermal manager for %s: %s", self._entity_id, exc)
            return None

    def _get_offset_engine(self):
        """Get offset engine for this entity from hass.data."""
        try:
            entry_data = self.hass.data[DOMAIN][self._config_entry.entry_id]
            offset_engines = entry_data.get("offset_engines", {})
            return offset_engines.get(self._entity_id)
        except (KeyError, AttributeError) as exc:
            _LOGGER.debug("Error getting offset engine for %s: %s", self._entity_id, exc)
            return None

    async def async_press(self) -> None:
        """Handle the thermal reset button press."""
        try:
            _LOGGER.info("Thermal reset button pressed for %s", self._entity_id)
            
            # Get thermal manager and reset thermal data only
            thermal_manager = self._get_thermal_manager()
            if not thermal_manager:
                _LOGGER.warning("No thermal manager found for entity %s", self._entity_id)
                return
            
            # Reset thermal data (tau values, probe history, thermal state)
            thermal_manager.reset()
            _LOGGER.debug("Thermal data reset for %s", self._entity_id)
            
            # Persist reset state by saving learning data
            offset_engine = self._get_offset_engine()
            if offset_engine:
                try:
                    await offset_engine.save_learning_data()
                    _LOGGER.debug("Reset state persisted for %s", self._entity_id)
                except Exception as exc:
                    _LOGGER.warning(
                        "Failed to save reset state for %s: %s",
                        self._entity_id, exc
                    )
            else:
                _LOGGER.warning("No offset engine found for entity %s", self._entity_id)
            
            _LOGGER.info("Thermal data reset completed for %s", self._entity_id)
            
        except Exception as exc:
            _LOGGER.error(
                "Failed to reset thermal data for %s: %s",
                self._entity_id, exc, exc_info=True
            )