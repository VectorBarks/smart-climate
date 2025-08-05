"""Binary sensor platform for the Smart Climate integration.

ABOUTME: Binary sensors for Smart Climate outlier detection status.
This module provides binary sensors for outlier detection monitoring.
"""

import logging
from typing import Any, Dict, Optional

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Smart Climate binary sensor platform from a config entry.
    
    Creates OutlierDetectionSensor for each climate entity when outlier detection
    is enabled in the configuration.
    
    Args:
        hass: Home Assistant instance
        config_entry: Configuration entry for the integration
        async_add_entities: Callback to add entities to Home Assistant
    """
    # Check if outlier detection is enabled
    outlier_detection_enabled = config_entry.options.get("outlier_detection_enabled", True)
    if not outlier_detection_enabled:
        _LOGGER.debug("Outlier detection disabled, skipping binary sensor setup")
        return

    # Retrieve the coordinators created in __init__.py
    entry_data = hass.data[DOMAIN].get(config_entry.entry_id, {})
    coordinators = entry_data.get("coordinators", {})
    
    if not coordinators:
        _LOGGER.warning("No coordinators found for binary sensor setup in entry: %s", config_entry.entry_id)
        return

    # Create OutlierDetectionSensor for each climate entity
    sensors = []
    for entity_id, coordinator in coordinators.items():
        _LOGGER.debug("Creating OutlierDetectionSensor for entity: %s", entity_id)
        sensor_entity = OutlierDetectionSensor(coordinator, entity_id)
        sensors.append(sensor_entity)

    # Add sensors to Home Assistant
    if sensors:
        async_add_entities(sensors)
        _LOGGER.info("Created %d outlier detection binary sensors", len(sensors))


def create_binary_sensor_entity(base_cls=BinarySensorEntity):
    """Create a binary sensor entity class that inherits from the proper base.
    
    This factory function avoids metaclass conflicts by creating the class
    dynamically with the correct method resolution order.
    """
    
    class SmartClimateBinarySensorEntity(base_cls):
        """Base class for Smart Climate binary sensor entities."""
        
        _attr_has_entity_name = True
        
        def __init__(
            self,
            coordinator,
            entity_id: str,
        ) -> None:
            """Initialize binary sensor."""
            # Initialize the BinarySensorEntity
            super().__init__()
            
            # Set up coordinator attributes
            self.coordinator = coordinator
            self._entity_id = entity_id
        
        @property
        def should_poll(self) -> bool:
            """No need to poll. Coordinator notifies entity of updates."""
            return False
        
        @property
        def available(self) -> bool:
            """Return if entity is available."""
            return (hasattr(self.coordinator, 'last_update_success') and 
                    self.coordinator.last_update_success)
        
        async def async_added_to_hass(self) -> None:
            """When entity is added to hass."""
            await super().async_added_to_hass()
            self.async_on_remove(
                self.coordinator.async_add_listener(
                    self._handle_coordinator_update
                )
            )
        
        def _handle_coordinator_update(self) -> None:
            """Handle updated data from the coordinator."""
            self.async_write_ha_state()
    
    return SmartClimateBinarySensorEntity


# Create the binary sensor entity class
SmartClimateBinarySensorEntity = create_binary_sensor_entity()


class OutlierDetectionSensor(SmartClimateBinarySensorEntity):
    """Binary sensor for outlier detection status.
    
    This sensor indicates whether outliers have been detected for a specific
    climate entity. It extends CoordinatorEntity and BinarySensorEntity as
    specified in c_architecture.md Section 9.4.
    
    Features:
    - Reflects outlier status from coordinator data
    - Uses PROBLEM device class to indicate issues
    - Provides detailed outlier statistics in attributes
    - Handles missing/invalid data gracefully
    
    State Values:
    - True: Outliers detected for this entity
    - False: No outliers detected
    """
    
    def __init__(self, coordinator, entity_id: str) -> None:
        """Initialize outlier detection sensor.
        
        Args:
            coordinator: SmartClimateCoordinator instance
            entity_id: Climate entity ID to monitor for outliers
        """
        super().__init__(coordinator, entity_id)
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        
        # Generate unique ID following the specified format
        self._attr_unique_id = f"{entity_id}_outlier_detection"
        
        # Set sensor name and icon
        self._attr_name = f"{entity_id} Outlier Detection"
        self._attr_icon = "mdi:alert-circle-outline"
    
    @property
    def unique_id(self) -> str:
        """Return unique ID for the sensor."""
        return self._attr_unique_id
    
    @property
    def is_on(self) -> bool:
        """Return True if outliers are detected for this entity.
        
        Returns outlier status from coordinator.data.outliers for this entity.
        Defaults to False if data is unavailable or entity not found.
        
        Returns:
            bool: True if outliers detected, False otherwise
        """
        if (not hasattr(self.coordinator, 'data') or 
            self.coordinator.data is None or
            not hasattr(self.coordinator.data, 'outliers')):
            return False
        
        return self.coordinator.data.outliers.get(self._entity_id, False)
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes.
        
        Provides outlier detection statistics including:
        - outlier_count: Total number of outliers detected
        - outlier_rate: Rate of outlier detection
        - detection_enabled: Whether outlier detection is active
        
        Returns:
            Dict[str, Any]: Dictionary of additional attributes
        """
        attributes = {}
        
        # Default values when data is unavailable
        if (not hasattr(self.coordinator, 'data') or 
            self.coordinator.data is None):
            return {
                "outlier_count": 0,
                "outlier_rate": 0.0,
                "detection_enabled": False
            }
        
        # Get outlier count
        if hasattr(self.coordinator.data, 'outlier_count'):
            attributes["outlier_count"] = self.coordinator.data.outlier_count
        else:
            attributes["outlier_count"] = 0
        
        # Get statistics from coordinator data
        if (hasattr(self.coordinator.data, 'outlier_statistics') and 
            self.coordinator.data.outlier_statistics is not None):
            stats = self.coordinator.data.outlier_statistics
            attributes["outlier_rate"] = stats.get("outlier_rate", 0.0)
            attributes["detection_enabled"] = stats.get("enabled", False)
        else:
            attributes["outlier_rate"] = 0.0
            attributes["detection_enabled"] = False
        
        return attributes