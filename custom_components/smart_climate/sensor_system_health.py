"""System Health sensors for Smart Climate integration."""

import logging
from typing import Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfInformation,
    EntityCategory,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SmartClimateDashboardSensor(SensorEntity):
    """Base class for Smart Climate dashboard sensors."""
    
    _attr_has_entity_name = True
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        sensor_type: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize dashboard sensor."""
        super().__init__()
        self.coordinator = coordinator
        self._base_entity_id = base_entity_id
        self._sensor_type = sensor_type
        
        # Generate unique ID
        safe_entity_id = base_entity_id.replace(".", "_")
        self._attr_unique_id = f"{config_entry.unique_id}_{safe_entity_id}_{sensor_type}"
        
        # Link to the same device as the climate entity
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
                self._handle_coordinator_update, self.entity_id
            )
        )
    
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class MemoryUsageSensor(SmartClimateDashboardSensor):
    """Sensor for memory usage in KB."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize memory usage sensor."""
        super().__init__(coordinator, base_entity_id, "memory_usage", config_entry)
        self._attr_name = "Memory Usage"
        self._attr_native_unit_of_measurement = UnitOfInformation.KIBIBYTES
        self._attr_device_class = SensorDeviceClass.DATA_SIZE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:memory"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the memory usage value."""
        if not self.coordinator.data:
            return None
        
        try:
            system_health = self.coordinator.data.get("system_health", {})
            return system_health.get("memory_usage_kb")
        except (AttributeError, TypeError):
            return None


class PersistenceLatencySensor(SmartClimateDashboardSensor):
    """Sensor for persistence latency in milliseconds."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize persistence latency sensor."""
        super().__init__(coordinator, base_entity_id, "persistence_latency", config_entry)
        self._attr_name = "Persistence Latency"
        self._attr_native_unit_of_measurement = "ms"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:database-clock"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the persistence latency value."""
        if not self.coordinator.data:
            return None
        
        try:
            system_health = self.coordinator.data.get("system_health", {})
            return system_health.get("persistence_latency_ms")
        except (AttributeError, TypeError):
            return None


class OutlierDetectionSensor(SmartClimateDashboardSensor):
    """Sensor for outlier detection status (binary sensor showing on/off text)."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize outlier detection sensor."""
        super().__init__(coordinator, base_entity_id, "outlier_detection", config_entry)
        self._attr_name = "Outlier Detection"
        self._attr_icon = "mdi:filter-variant-remove"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> str:
        """Return the outlier detection status as text."""
        if not self.coordinator.data:
            return "off"
        
        try:
            system_health = self.coordinator.data.get("system_health", {})
            is_active = system_health.get("outlier_detection_active", False)
            return "on" if is_active else "off"
        except (AttributeError, TypeError):
            return "off"


class SamplesPerDaySensor(SmartClimateDashboardSensor):
    """Sensor for samples per day."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize samples per day sensor."""
        super().__init__(coordinator, base_entity_id, "samples_per_day", config_entry)
        self._attr_name = "Samples per Day"
        self._attr_native_unit_of_measurement = "samples/d"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:chart-bar"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the samples per day value."""
        if not self.coordinator.data:
            return None
        
        try:
            system_health = self.coordinator.data.get("system_health", {})
            return system_health.get("samples_per_day")
        except (AttributeError, TypeError):
            return None


class ConvergenceTrendSensor(SmartClimateDashboardSensor):
    """Sensor for convergence trend (text values: improving, stable, unstable, unknown)."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize convergence trend sensor."""
        super().__init__(coordinator, base_entity_id, "convergence_trend", config_entry)
        self._attr_name = "Convergence Trend"
        self._attr_icon = "mdi:chart-gantt"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> str:
        """Return the convergence trend value."""
        if not self.coordinator.data:
            return "unknown"
        
        try:
            system_health = self.coordinator.data.get("system_health", {})
            trend = system_health.get("convergence_trend", "unknown")
            # Ensure we return a valid trend value
            if trend in ["improving", "stable", "unstable", "unknown"]:
                return trend
            return "unknown"
        except (AttributeError, TypeError):
            return "unknown"


# Export all sensor classes for easy import
__all__ = [
    "MemoryUsageSensor",
    "PersistenceLatencySensor",
    "OutlierDetectionSensor",
    "SamplesPerDaySensor",
    "ConvergenceTrendSensor",
]