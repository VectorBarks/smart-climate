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
    
    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        
        # Safely traverse the nested dictionary
        value = self.coordinator.data
        try:
            for key in self._key_path:
                value = value[key]
        except (TypeError, KeyError):
            return None
        
        if value is None:
            return None
        
        # Apply optional value processing
        if self._value_processor:
            try:
                return self._value_processor(value)
            except (TypeError, ValueError):
                return None
        
        return value


class PredictionLatencySensor(SmartClimateDashboardSensor):
    """Sensor for prediction latency in milliseconds."""
    
    def __init__(self, coordinator, device_info: DeviceInfo, climate_entity_name: str):
        """Initialize the sensor."""
        description = SensorEntityDescription(
            key="prediction_latency",
            name="Prediction Latency",
            native_unit_of_measurement="ms",
            device_class=SensorDeviceClass.DURATION,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:timer-sand",
            entity_category=EntityCategory.DIAGNOSTIC,
        )
        super().__init__(
            coordinator,
            device_info,
            climate_entity_name,
            description,
            ("performance", "prediction_latency_ms"),
            value_processor=lambda x: round(float(x), 1) if x is not None else None,
        )


class EnergyEfficiencySensor(SmartClimateDashboardSensor):
    """Sensor for energy efficiency score."""
    
    def __init__(self, coordinator, device_info: DeviceInfo, climate_entity_name: str):
        """Initialize the sensor."""
        description = SensorEntityDescription(
            key="energy_efficiency_score",
            name="Energy Efficiency Score",
            native_unit_of_measurement="/100",
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:leaf-circle",
            entity_category=None,  # Visible by default - key metric
        )
        super().__init__(
            coordinator,
            device_info,
            climate_entity_name,
            description,
            ("performance", "energy_efficiency_score"),
        )


class TemperatureStabilitySensor(SmartClimateDashboardSensor):
    """Sensor for temperature stability detection (displayed as on/off text)."""
    
    def __init__(self, coordinator, device_info: DeviceInfo, climate_entity_name: str):
        """Initialize the sensor."""
        description = SensorEntityDescription(
            key="temperature_stability_detected",
            name="Temperature Stability Detected",
            icon="mdi:waves-arrow-up",
            entity_category=EntityCategory.DIAGNOSTIC,
        )
        super().__init__(
            coordinator,
            device_info,
            climate_entity_name,
            description,
            ("delay_data", "temperature_stability_detected"),
        )
    
    @property
    def native_value(self):
        """Return 'on' or 'off' string based on boolean value."""
        # Get the boolean value from parent
        boolean_value = super().native_value
        
        if boolean_value is None:
            return None
        
        # Convert boolean to on/off string for sensor display
        return "on" if boolean_value else "off"


class LearnedDelaySensor(SmartClimateDashboardSensor):
    """Sensor for learned delay in seconds."""
    
    def __init__(self, coordinator, device_info: DeviceInfo, climate_entity_name: str):
        """Initialize the sensor."""
        description = SensorEntityDescription(
            key="learned_delay",
            name="Learned Delay",
            native_unit_of_measurement=UnitOfTime.SECONDS,
            device_class=SensorDeviceClass.DURATION,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:timer-sync-outline",
            entity_category=EntityCategory.DIAGNOSTIC,
        )
        super().__init__(
            coordinator,
            device_info,
            climate_entity_name,
            description,
            ("delay_data", "learned_delay_seconds"),
            value_processor=lambda x: round(float(x), 1) if x is not None else None,
        )


class EMACoeffficientSensor(SmartClimateDashboardSensor):
    """Sensor for EMA coefficient value."""
    
    def __init__(self, coordinator, device_info: DeviceInfo, climate_entity_name: str):
        """Initialize the sensor."""
        description = SensorEntityDescription(
            key="ema_coefficient",
            name="EMA Coefficient",
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:chart-bell-curve",
            entity_category=EntityCategory.DIAGNOSTIC,
        )
        super().__init__(
            coordinator,
            device_info,
            climate_entity_name,
            description,
            ("performance", "ema_coefficient"),
            value_processor=lambda x: round(float(x), 3) if x is not None else None,
        )


class SensorAvailabilitySensor(SmartClimateDashboardSensor):
    """Sensor for sensor availability score."""
    
    def __init__(self, coordinator, device_info: DeviceInfo, climate_entity_name: str):
        """Initialize the sensor."""
        description = SensorEntityDescription(
            key="sensor_availability",
            name="Sensor Availability",
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:access-point-check",
            entity_category=EntityCategory.DIAGNOSTIC,
        )
        super().__init__(
            coordinator,
            device_info,
            climate_entity_name,
            description,
            ("performance", "sensor_availability_score"),
            value_processor=lambda x: round(float(x), 1) if x is not None else None,
        )


# Export all sensor classes for import
__all__ = [
    "PredictionLatencySensor",
    "EnergyEfficiencySensor",
    "TemperatureStabilitySensor",
    "LearnedDelaySensor",
    "EMACoeffficientSensor",
    "SensorAvailabilitySensor",
]