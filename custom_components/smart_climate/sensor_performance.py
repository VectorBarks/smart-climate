"""Performance analytics sensors for Smart Climate."""

from typing import Optional
from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTime,
    EntityCategory,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .entity import SmartClimateSensorEntity


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
    
    def get_coordinator_value(self, key_path: tuple, value_processor=None):
        """Helper method to get value from coordinator data with key path and optional processing."""
        if self.coordinator.data is None:
            return None
        
        # Safely traverse the nested dictionary
        value = self.coordinator.data
        try:
            for key in key_path:
                value = value[key]
        except (TypeError, KeyError):
            return None
        
        if value is None:
            return None
        
        # Apply optional value processing
        if value_processor:
            try:
                return value_processor(value)
            except (TypeError, ValueError):
                return None
        
        return value


class PredictionLatencySensor(SmartClimateDashboardSensor):
    """Sensor for prediction latency in milliseconds."""
    
    def __init__(self, coordinator, base_entity_id: str, config_entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator, base_entity_id, "prediction_latency", config_entry)
        self._attr_name = "Prediction Latency"
        self._attr_native_unit_of_measurement = "ms"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:timer-sand"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the prediction latency value."""
        value = self.get_coordinator_value(
            ("performance", "prediction_latency_ms"),
            lambda x: round(float(x), 1) if x is not None else None
        )
        return value


class EnergyEfficiencySensor(SmartClimateDashboardSensor):
    """Sensor for energy efficiency score."""
    
    def __init__(self, coordinator, base_entity_id: str, config_entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator, base_entity_id, "energy_efficiency_score", config_entry)
        self._attr_name = "Energy Efficiency Score"
        self._attr_native_unit_of_measurement = "/100"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:leaf-circle"
        self._attr_entity_category = None  # Visible by default - key metric
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the energy efficiency score value."""
        return self.get_coordinator_value(("performance", "energy_efficiency_score"))


class TemperatureStabilitySensor(SmartClimateDashboardSensor):
    """Sensor for temperature stability detection (displayed as on/off text)."""
    
    def __init__(self, coordinator, base_entity_id: str, config_entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator, base_entity_id, "temperature_stability_detected", config_entry)
        self._attr_name = "Temperature Stability Detected"
        self._attr_icon = "mdi:waves-arrow-up"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[str]:
        """Return 'on' or 'off' string based on boolean value."""
        # Get the boolean value from coordinator
        boolean_value = self.get_coordinator_value(("delay_data", "temperature_stability_detected"))
        
        if boolean_value is None:
            return None
        
        # Convert boolean to on/off string for sensor display
        return "on" if boolean_value else "off"


class LearnedDelaySensor(SmartClimateDashboardSensor):
    """Sensor for learned delay in seconds."""
    
    def __init__(self, coordinator, base_entity_id: str, config_entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator, base_entity_id, "learned_delay", config_entry)
        self._attr_name = "Learned Delay"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:timer-sync-outline"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the learned delay value."""
        value = self.get_coordinator_value(
            ("delay_data", "learned_delay_seconds"),
            lambda x: round(float(x), 1) if x is not None else None
        )
        return value


class EMACoeffficientSensor(SmartClimateDashboardSensor):
    """Sensor for EMA coefficient value."""
    
    def __init__(self, coordinator, base_entity_id: str, config_entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator, base_entity_id, "ema_coefficient", config_entry)
        self._attr_name = "EMA Coefficient"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:chart-bell-curve"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the EMA coefficient value."""
        value = self.get_coordinator_value(
            ("performance", "ema_coefficient"),
            lambda x: round(float(x), 3) if x is not None else None
        )
        return value


class SensorAvailabilitySensor(SmartClimateDashboardSensor):
    """Sensor for sensor availability score."""
    
    def __init__(self, coordinator, base_entity_id: str, config_entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator, base_entity_id, "sensor_availability", config_entry)
        self._attr_name = "Sensor Availability"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:access-point-check"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the sensor availability score value."""
        value = self.get_coordinator_value(
            ("performance", "sensor_availability_score"),
            lambda x: round(float(x), 1) if x is not None else None
        )
        return value


# Export all sensor classes for import
__all__ = [
    "PredictionLatencySensor",
    "EnergyEfficiencySensor",
    "TemperatureStabilitySensor",
    "LearnedDelaySensor",
    "EMACoeffficientSensor",
    "SensorAvailabilitySensor",
]