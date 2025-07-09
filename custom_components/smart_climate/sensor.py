"""Sensor platform for the Smart Climate integration."""

import logging
from typing import Any, Dict, Optional
from datetime import datetime

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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .offset_engine import OffsetEngine

_LOGGER = logging.getLogger(__name__)

# Minimum samples required for calibration completion
MIN_SAMPLES_FOR_CALIBRATION = 10


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Smart Climate sensor platform from a config entry."""
    # Retrieve the OffsetEngine instances created in __init__.py
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    offset_engines = entry_data.get("offset_engines", {})
    
    if not offset_engines:
        _LOGGER.warning("No offset engines found for sensor setup in entry: %s", config_entry.entry_id)
        return
    
    # Create sensors for each climate entity
    sensors = []
    for entity_id, offset_engine in offset_engines.items():
        # Create all 5 sensor types for each climate entity
        sensors.extend([
            OffsetCurrentSensor(offset_engine, entity_id, config_entry),
            LearningProgressSensor(offset_engine, entity_id, config_entry),
            AccuracyCurrentSensor(offset_engine, entity_id, config_entry),
            CalibrationStatusSensor(offset_engine, entity_id, config_entry),
            HysteresisStateSensor(offset_engine, entity_id, config_entry),
        ])
    
    async_add_entities(sensors)


class SmartClimateDashboardSensor(SensorEntity):
    """Base class for Smart Climate dashboard sensors."""
    
    _attr_has_entity_name = True
    
    def __init__(
        self,
        offset_engine: OffsetEngine,
        base_entity_id: str,
        sensor_type: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize dashboard sensor."""
        self._offset_engine = offset_engine
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
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._offset_engine is not None  # Simple existence check


class OffsetCurrentSensor(SmartClimateDashboardSensor):
    """Sensor for current temperature offset."""
    
    def __init__(
        self,
        offset_engine: OffsetEngine,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize offset sensor."""
        super().__init__(offset_engine, base_entity_id, "offset_current", config_entry)
        self._attr_name = "Current Offset"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:thermometer-lines"
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the current offset value."""
        if not self.available:
            return None
        
        try:
            return self._offset_engine._coordinator.data.calculated_offset
        except (AttributeError, TypeError):
            return None


class LearningProgressSensor(SmartClimateDashboardSensor):
    """Sensor for learning progress percentage."""
    
    def __init__(
        self,
        offset_engine: OffsetEngine,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize learning progress sensor."""
        super().__init__(offset_engine, base_entity_id, "learning_progress", config_entry)
        self._attr_name = "Learning Progress"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:brain"
    
    @property
    def native_value(self) -> int:
        """Return the learning progress percentage."""
        try:
            learning_info = self._offset_engine.get_learning_info()
            
            if not learning_info.get("enabled", False):
                return 0
            
            samples = learning_info.get("samples", 0)
            # Calculate progress as percentage of minimum required samples
            progress = min(100, int((samples / MIN_SAMPLES_FOR_CALIBRATION) * 100))
            
            return progress
        except Exception:
            return 0


class AccuracyCurrentSensor(SmartClimateDashboardSensor):
    """Sensor for current prediction accuracy."""
    
    def __init__(
        self,
        offset_engine: OffsetEngine,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize accuracy sensor."""
        super().__init__(offset_engine, base_entity_id, "accuracy_current", config_entry)
        self._attr_name = "Current Accuracy"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:target"
    
    @property
    def native_value(self) -> int:
        """Return the current accuracy percentage."""
        try:
            learning_info = self._offset_engine.get_learning_info()
            accuracy = learning_info.get("accuracy", 0.0)
            # Convert to percentage
            return int(accuracy * 100)
        except Exception:
            return 0


class CalibrationStatusSensor(SmartClimateDashboardSensor):
    """Sensor for calibration phase status."""
    
    def __init__(
        self,
        offset_engine: OffsetEngine,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize calibration status sensor."""
        super().__init__(offset_engine, base_entity_id, "calibration_status", config_entry)
        self._attr_name = "Calibration Status"
        self._attr_icon = "mdi:progress-check"
    
    @property
    def native_value(self) -> str:
        """Return the calibration status text."""
        try:
            learning_info = self._offset_engine.get_learning_info()
            
            if not learning_info.get("enabled", False):
                return "Waiting (Learning Disabled)"
            
            samples = learning_info.get("samples", 0)
            
            if samples >= MIN_SAMPLES_FOR_CALIBRATION:
                return "Complete"
            else:
                return f"In Progress ({samples}/{MIN_SAMPLES_FOR_CALIBRATION} samples)"
        except Exception:
            return "Unknown"
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        try:
            learning_info = self._offset_engine.get_learning_info()
            return {
                "samples_collected": learning_info.get("samples", 0),
                "minimum_required": MIN_SAMPLES_FOR_CALIBRATION,
                "learning_enabled": learning_info.get("enabled", False),
                "last_sample": learning_info.get("last_sample_time"),
            }
        except Exception:
            return {
                "samples_collected": 0,
                "minimum_required": MIN_SAMPLES_FOR_CALIBRATION,
                "learning_enabled": False,
                "last_sample": None,
            }


class HysteresisStateSensor(SmartClimateDashboardSensor):
    """Sensor for human-readable AC hysteresis state."""
    
    def __init__(
        self,
        offset_engine: OffsetEngine,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize hysteresis state sensor."""
        super().__init__(offset_engine, base_entity_id, "hysteresis_state", config_entry)
        self._attr_name = "Hysteresis State"
        self._attr_icon = "mdi:sine-wave"
    
    @property
    def native_value(self) -> str:
        """Return the human-readable hysteresis state."""
        try:
            learning_info = self._offset_engine.get_learning_info()
            state = learning_info.get("hysteresis_state", "unknown")
            
            # Map to human-readable descriptions
            state_mapping = {
                "learning_hysteresis": "Learning AC behavior",
                "active_phase": "AC actively cooling",
                "idle_above_start_threshold": "AC should start soon",
                "idle_below_stop_threshold": "AC recently stopped",
                "idle_stable_zone": "Temperature stable",
                "disabled": "No power sensor",
                "no_power_sensor": "No power sensor",
                "ready": "Ready",
                "error": "Error",
            }
            
            return state_mapping.get(state, "Unknown")
        except Exception:
            return "Unknown"
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        try:
            learning_info = self._offset_engine.get_learning_info()
            
            # Check if power sensor is configured
            power_configured = learning_info.get("hysteresis_enabled", False)
            
            # Format threshold values
            start_threshold = learning_info.get("learned_start_threshold")
            stop_threshold = learning_info.get("learned_stop_threshold")
            temperature_window = learning_info.get("temperature_window")
            
            # Determine display format based on state
            if not power_configured:
                start_display = "Not available"
                stop_display = "Not available"
                window_display = "Not available"
            elif learning_info.get("hysteresis_state") == "learning_hysteresis":
                start_display = f"{start_threshold:.1f}°C" if start_threshold is not None else "Learning..."
                stop_display = f"{stop_threshold:.1f}°C" if stop_threshold is not None else "Learning..."
                window_display = f"{temperature_window:.1f}°C" if temperature_window is not None else "Learning..."
            else:
                start_display = f"{start_threshold:.1f}°C" if start_threshold is not None else "Not available"
                stop_display = f"{stop_threshold:.1f}°C" if stop_threshold is not None else "Not available"
                window_display = f"{temperature_window:.1f}°C" if temperature_window is not None else "Not available"
            
            return {
                "power_sensor_configured": power_configured,
                "start_threshold": start_display,
                "stop_threshold": stop_display,
                "temperature_window": window_display,
                "start_samples": learning_info.get("start_samples_collected", 0),
                "stop_samples": learning_info.get("stop_samples_collected", 0),
                "ready": learning_info.get("hysteresis_ready", False),
            }
        except Exception:
            return {
                "power_sensor_configured": False,
                "start_threshold": "Not available",
                "stop_threshold": "Not available",
                "temperature_window": "Not available",
                "start_samples": 0,
                "stop_samples": 0,
                "ready": False,
            }