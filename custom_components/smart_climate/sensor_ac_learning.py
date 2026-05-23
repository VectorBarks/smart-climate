"""AC learning sensor entities for Smart Climate integration."""

import logging
from typing import Any, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    EntityCategory,
)

from .const import DOMAIN
from .entity import SmartClimateSensorEntity

_LOGGER = logging.getLogger(__name__)


class SmartClimateDashboardSensor(SmartClimateSensorEntity):
    """Base class for Smart Climate dashboard sensors."""
    pass
    
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


class TemperatureWindowSensor(SmartClimateDashboardSensor):
    """Sensor for AC temperature window range."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the temperature window sensor."""
        super().__init__(coordinator, base_entity_id, "temperature_window", config_entry)
        self._attr_name = "Temperature Window"
        self._attr_icon = "mdi:arrow-expand-vertical"
        # Visible by default - useful metric
        self._attr_entity_category = None
        
    @property
    def native_value(self) -> str:
        """Return the temperature window string or an explicit learning state."""
        if self.coordinator.data is None:
            return "unknown"
            
        try:
            ac_behavior = self.coordinator.data.get("ac_behavior", {})
            value = ac_behavior.get("temperature_window")
            if value:
                return value

            learning_info = self.coordinator.data.get("learning_info", {})
            if not learning_info.get("hysteresis_enabled", False):
                return "disabled"
            return "learning"
        except (TypeError, KeyError, AttributeError):
            return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return context explaining why the window is not yet numeric."""
        attrs = {
            "status_detail": "Waiting for coordinator data",
            "source": "dashboard_coordinator.ac_behavior.temperature_window",
        }
        if self.coordinator.data is None:
            return attrs

        try:
            ac_behavior = self.coordinator.data.get("ac_behavior", {})
            learning_info = self.coordinator.data.get("learning_info", {})
            attrs.update({
                "hysteresis_enabled": learning_info.get("hysteresis_enabled", False),
                "hysteresis_ready": learning_info.get("hysteresis_ready", False),
                "hysteresis_state": learning_info.get("hysteresis_state", "unknown"),
                "start_samples": learning_info.get("start_samples_collected", 0),
                "stop_samples": learning_info.get("stop_samples_collected", 0),
                "hysteresis_cycle_count": ac_behavior.get("hysteresis_cycle_count", 0),
                "status_detail": (
                    "Temperature window learned" if ac_behavior.get("temperature_window")
                    else "Power sensor is disabled; hysteresis learning is unavailable" if not learning_info.get("hysteresis_enabled", False)
                    else "Collecting compressor start/stop samples before a window can be calculated"
                ),
            })
        except (TypeError, KeyError, AttributeError):
            attrs["status_detail"] = "Coordinator data shape is invalid"
        return attrs


class PowerCorrelationSensor(SmartClimateDashboardSensor):
    """Sensor for power correlation accuracy."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the power correlation sensor."""
        super().__init__(coordinator, base_entity_id, "power_correlation", config_entry)
        self._attr_name = "Power Correlation Accuracy"
        self._attr_icon = "mdi:lightning-bolt-circle"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        # Visible by default - important metric
        self._attr_entity_category = None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the power correlation accuracy percentage."""
        if self.coordinator.data is None:
            return None
            
        try:
            ac_behavior = self.coordinator.data.get("ac_behavior", {})
            value = ac_behavior.get("power_correlation_accuracy")
            return value if value is not None else None
        except (TypeError, KeyError, AttributeError):
            return None


class HysteresisCyclesSensor(SmartClimateDashboardSensor):
    """Sensor for hysteresis cycle count."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the hysteresis cycles sensor."""
        super().__init__(coordinator, base_entity_id, "hysteresis_cycles", config_entry)
        self._attr_name = "Hysteresis Cycles"
        self._attr_icon = "mdi:sync-circle"
        self._attr_native_unit_of_measurement = "cycles"
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        # Visible by default - shows learning progress
        self._attr_entity_category = None
        
    @property
    def native_value(self) -> Optional[int]:
        """Return the hysteresis cycle count."""
        if self.coordinator.data is None:
            return None
            
        try:
            ac_behavior = self.coordinator.data.get("ac_behavior", {})
            value = ac_behavior.get("hysteresis_cycle_count")
            return value if value is not None else None
        except (TypeError, KeyError, AttributeError):
            return None


class ReactiveOffsetSensor(SmartClimateDashboardSensor):
    """Sensor for reactive temperature offset (current calculated offset)."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the reactive offset sensor."""
        super().__init__(coordinator, base_entity_id, "reactive_offset", config_entry)
        self._attr_name = "Reactive Offset"
        self._attr_icon = "mdi:thermometer-chevron-up"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        # Visible by default - core metric
        self._attr_entity_category = None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the current reactive offset."""
        if self.coordinator.data is None:
            return None
            
        try:
            # This is at root level, not nested
            value = self.coordinator.data.get("calculated_offset")
            return value if value is not None else None
        except (TypeError, KeyError, AttributeError):
            return None


class PredictiveOffsetSensor(SmartClimateDashboardSensor):
    """Sensor for predictive temperature offset from weather/ML."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the predictive offset sensor."""
        super().__init__(coordinator, base_entity_id, "predictive_offset", config_entry)
        self._attr_name = "Predictive Offset"
        self._attr_icon = "mdi:thermometer-chevron-down"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        # Visible by default - core metric
        self._attr_entity_category = None
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the predictive offset.
        
        Note: This field needs to be added to dashboard data.
        Will show as unavailable until implemented.
        """
        if self.coordinator.data is None:
            return None
            
        try:
            # This is expected at root level like calculated_offset
            value = self.coordinator.data.get("predictive_offset")
            return value if value is not None else None
        except (TypeError, KeyError, AttributeError):
            return None