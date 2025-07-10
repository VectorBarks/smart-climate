"""Base entity for Smart Climate integration."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

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