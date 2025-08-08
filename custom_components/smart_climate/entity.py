"""Base entity for Smart Climate integration."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorEntity

from .const import DOMAIN


class SmartClimateBaseEntity(CoordinatorEntity):
    """Base class for all Smart Climate entities using coordinator."""

    def __init__(self, coordinator, base_entity_id: str, config_entry) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)
        self._base_entity_id = base_entity_id
        
        # Generate safe entity ID for device info
        safe_entity_id = base_entity_id.replace(".", "_")
        
        # Device info shared by all entities
        climate_name = f"{config_entry.title} ({base_entity_id})"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{config_entry.unique_id}_{safe_entity_id}")},
            name=climate_name,
        )


def create_sensor_entity(base_cls=SensorEntity):
    """Create a sensor entity class that inherits from the proper base.
    
    This factory function avoids metaclass conflicts by creating the class
    dynamically with the correct method resolution order.
    """
    
    class SmartClimateSensorEntity(base_cls):
        """Base class for Smart Climate sensor entities."""
        
        _attr_has_entity_name = True
        
        def __init__(
            self,
            coordinator,
            base_entity_id: str,
            sensor_type: str,
            config_entry,
        ) -> None:
            """Initialize dashboard sensor."""
            # Initialize the SensorEntity
            super().__init__()
            
            # Set up coordinator attributes
            self.coordinator = coordinator
            self._base_entity_id = base_entity_id
            self._sensor_type = sensor_type
            self._config_entry = config_entry
            
            # Generate unique ID
            safe_entity_id = base_entity_id.replace(".", "_")
            self._attr_unique_id = f"{config_entry.unique_id}_{safe_entity_id}_{sensor_type}"
            
            # Set up device info
            climate_name = f"{config_entry.title} ({base_entity_id})"
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{config_entry.unique_id}_{safe_entity_id}")},
                name=climate_name,
            )
        
        @property
        def should_poll(self) -> bool:
            """No need to poll. Coordinator notifies entity of updates."""
            return False
        
        @property
        def available(self) -> bool:
            """Return if entity is available."""
            return self.coordinator.last_update_success
        
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
    
    return SmartClimateSensorEntity


# Create the sensor entity class
SmartClimateSensorEntity = create_sensor_entity()