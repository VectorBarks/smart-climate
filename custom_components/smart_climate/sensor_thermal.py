"""Thermal sensors for Smart Climate integration.

This module provides 12 thermal sensors across 3 categories for comprehensive thermal efficiency monitoring:

1. Dashboard Sensors (5): Core thermal status display for end users
2. Performance Sensors (5): System efficiency metrics for advanced users  
3. Debug Sensors (3): Detailed diagnostics (disabled by default)

Key Features:
- Thermal state machine monitoring
- Operating window boundary tracking
- Model confidence and learning progress
- HVAC cycle health monitoring
- Probing status and results tracking

Data Access:
Thermal data is accessed from coordinator via thermal_components stored in
hass.data[DOMAIN][entry_id]["thermal_components"][entity_id]
"""

import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .entity import SmartClimateSensorEntity
from .thermal_models import ThermalState, PreferenceLevel

_LOGGER = logging.getLogger(__name__)


class SmartClimateThermalSensor(SmartClimateSensorEntity):
    """Base class for Smart Climate thermal sensors."""
    
    def _get_thermal_components(self) -> Optional[Dict[str, Any]]:
        """Get thermal components for this entity from hass.data."""
        try:
            entry_data = self.hass.data[DOMAIN][self._config_entry.entry_id]
            thermal_components = entry_data.get("thermal_components", {})
            
            # Debug logging
            _LOGGER.debug(
                "Looking for thermal components: base_entity_id=%s, available_keys=%s", 
                self._base_entity_id, 
                list(thermal_components.keys()) if thermal_components else "none"
            )
            
            components = thermal_components.get(self._base_entity_id, {})
            if not components:
                _LOGGER.debug("No thermal components found for %s", self._base_entity_id)
                return None
            return components
        except (KeyError, AttributeError) as e:
            _LOGGER.debug("Error getting thermal components for %s: %s", self._base_entity_id, e)
            return None


# === DASHBOARD SENSORS (5) ===

class ThermalStateSensor(SmartClimateThermalSensor):
    """Sensor for current thermal state from ThermalManager."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize thermal state sensor."""
        super().__init__(coordinator, base_entity_id, "thermal_state", config_entry)
        self._attr_name = "Thermal State"
        self._attr_icon = "mdi:state-machine"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[str]:
        """Return the current thermal state."""
        thermal_components = self._get_thermal_components()
        if not thermal_components:
            return None
        
        try:
            thermal_manager = thermal_components.get("thermal_manager")
            if thermal_manager:
                return thermal_manager.current_state.value
            return None
        except (AttributeError, TypeError):
            return None


class OperatingWindowLowerSensor(SmartClimateThermalSensor):
    """Sensor for operating window lower boundary."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize operating window lower sensor."""
        super().__init__(coordinator, base_entity_id, "operating_window_lower", config_entry)
        self._attr_name = "Operating Window Lower"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:thermometer-low"
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the operating window lower bound."""
        thermal_components = self._get_thermal_components()
        if not thermal_components:
            return None
        
        try:
            thermal_manager = thermal_components.get("thermal_manager")
            if not thermal_manager:
                return None
            
            # Get current setpoint and outdoor temp from coordinator if available
            coordinator_data = self.coordinator.data
            if not coordinator_data:
                return None
            
            setpoint = coordinator_data.get("setpoint", 24.0)  # Default fallback
            outdoor_temp = coordinator_data.get("outdoor_temp", 25.0)  # Default fallback
            hvac_mode = coordinator_data.get("hvac_mode", "cool")  # Default fallback
            
            lower_bound, _ = thermal_manager.get_operating_window(setpoint, outdoor_temp, hvac_mode)
            return lower_bound
        except (AttributeError, TypeError, ValueError):
            return None


class OperatingWindowUpperSensor(SmartClimateThermalSensor):
    """Sensor for operating window upper boundary."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize operating window upper sensor."""
        super().__init__(coordinator, base_entity_id, "operating_window_upper", config_entry)
        self._attr_name = "Operating Window Upper"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:thermometer-high"
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the operating window upper bound."""
        thermal_components = self._get_thermal_components()
        if not thermal_components:
            return None
        
        try:
            thermal_manager = thermal_components.get("thermal_manager")
            if not thermal_manager:
                return None
            
            # Get current setpoint and outdoor temp from coordinator if available
            coordinator_data = self.coordinator.data
            if not coordinator_data:
                return None
            
            setpoint = coordinator_data.get("setpoint", 24.0)  # Default fallback
            outdoor_temp = coordinator_data.get("outdoor_temp", 25.0)  # Default fallback
            hvac_mode = coordinator_data.get("hvac_mode", "cool")  # Default fallback
            
            _, upper_bound = thermal_manager.get_operating_window(setpoint, outdoor_temp, hvac_mode)
            return upper_bound
        except (AttributeError, TypeError, ValueError):
            return None


class ComfortPreferenceSensor(SmartClimateThermalSensor):
    """Sensor for user's comfort preference level."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize comfort preference sensor."""
        super().__init__(coordinator, base_entity_id, "comfort_preference", config_entry)
        self._attr_name = "Comfort Preference"
        self._attr_icon = "mdi:account-tune"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[str]:
        """Return the current comfort preference level."""
        thermal_components = self._get_thermal_components()
        if not thermal_components:
            return None
        
        try:
            user_preferences = thermal_components.get("user_preferences")
            if user_preferences and hasattr(user_preferences, 'level'):
                # Convert enum to human-readable format
                level = user_preferences.level
                if isinstance(level, PreferenceLevel):
                    return level.value.replace('_', ' ').title()
                return str(level)
            return None
        except (AttributeError, TypeError):
            return None


class ShadowModeSensor(SmartClimateThermalSensor, BinarySensorEntity):
    """Binary sensor for thermal efficiency shadow mode status."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize shadow mode sensor."""
        super().__init__(coordinator, base_entity_id, "shadow_mode", config_entry)
        self._attr_name = "Shadow Mode"
        self._attr_device_class = BinarySensorDeviceClass.SAFETY
        self._attr_icon = "mdi:eye-outline"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def is_on(self) -> Optional[bool]:
        """Return true if thermal efficiency is in shadow mode."""
        thermal_components = self._get_thermal_components()
        if not thermal_components:
            return None
        
        try:
            # Check if shadow mode is enabled from thermal components or config
            shadow_mode = thermal_components.get("shadow_mode")
            if shadow_mode is not None:
                return bool(shadow_mode)
            
            # Fallback: check config entry options
            return self._config_entry.options.get("thermal_shadow_mode", False)
        except (AttributeError, TypeError):
            return None
    
    @property
    def native_value(self) -> None:
        """Binary sensors don't have native_value."""
        return None


# === PERFORMANCE SENSORS (5) ===

class ModelConfidenceSensor(SmartClimateThermalSensor):
    """Sensor for thermal model confidence percentage."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize model confidence sensor."""
        super().__init__(coordinator, base_entity_id, "model_confidence", config_entry)
        self._attr_name = "Model Confidence"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:chart-line-variant"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the thermal model confidence percentage."""
        thermal_components = self._get_thermal_components()
        if not thermal_components:
            return None
        
        try:
            thermal_model = thermal_components.get("thermal_model")
            if thermal_model and hasattr(thermal_model, 'get_confidence'):
                confidence = thermal_model.get_confidence()
                return confidence * 100  # Convert to percentage
            return None
        except (AttributeError, TypeError):
            return None


class TauCoolingSensor(SmartClimateThermalSensor):
    """Sensor for thermal cooling time constant."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize tau cooling sensor."""
        super().__init__(coordinator, base_entity_id, "tau_cooling", config_entry)
        self._attr_name = "Tau Cooling"
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:arrow-down-bold-box-outline"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the thermal cooling time constant in minutes."""
        thermal_components = self._get_thermal_components()
        if not thermal_components:
            return None
        
        try:
            thermal_model = thermal_components.get("thermal_model")
            if thermal_model and hasattr(thermal_model, '_tau_cooling'):
                # Convert from seconds to minutes
                return thermal_model._tau_cooling / 60.0
            return None
        except (AttributeError, TypeError):
            return None


class TauWarmingSensor(SmartClimateThermalSensor):
    """Sensor for thermal warming time constant."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize tau warming sensor."""
        super().__init__(coordinator, base_entity_id, "tau_warming", config_entry)
        self._attr_name = "Tau Warming"
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:arrow-up-bold-box-outline"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the thermal warming time constant in minutes."""
        thermal_components = self._get_thermal_components()
        if not thermal_components:
            return None
        
        try:
            thermal_model = thermal_components.get("thermal_model")
            if thermal_model and hasattr(thermal_model, '_tau_warming'):
                # Convert from seconds to minutes
                return thermal_model._tau_warming / 60.0
            return None
        except (AttributeError, TypeError):
            return None


class AverageOnCycleSensor(SmartClimateThermalSensor):
    """Sensor for average HVAC on cycle duration."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize average on cycle sensor."""
        super().__init__(coordinator, base_entity_id, "avg_on_cycle", config_entry)
        self._attr_name = "Average On Cycle"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:timer-play-outline"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the average on cycle duration in seconds."""
        thermal_components = self._get_thermal_components()
        if not thermal_components:
            return None
        
        try:
            cycle_monitor = thermal_components.get("cycle_monitor")
            if cycle_monitor and hasattr(cycle_monitor, 'get_average_on_duration'):
                return cycle_monitor.get_average_on_duration()
            return None
        except (AttributeError, TypeError):
            return None


class AverageOffCycleSensor(SmartClimateThermalSensor):
    """Sensor for average HVAC off cycle duration."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize average off cycle sensor."""
        super().__init__(coordinator, base_entity_id, "avg_off_cycle", config_entry)
        self._attr_name = "Average Off Cycle"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_icon = "mdi:timer-stop-outline"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the average off cycle duration in seconds."""
        thermal_components = self._get_thermal_components()
        if not thermal_components:
            return None
        
        try:
            cycle_monitor = thermal_components.get("cycle_monitor")
            if cycle_monitor and hasattr(cycle_monitor, 'get_average_off_duration'):
                return cycle_monitor.get_average_off_duration()
            return None
        except (AttributeError, TypeError):
            return None


# === DEBUG SENSORS (3) - Disabled by default ===

class AdjustedComfortBandSensor(SmartClimateThermalSensor):
    """Sensor for adjusted comfort band size (disabled by default)."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize adjusted comfort band sensor."""
        super().__init__(coordinator, base_entity_id, "adjusted_comfort_band", config_entry)
        self._attr_name = "Adjusted Comfort Band"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 2
        self._attr_icon = "mdi:tune"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_entity_registry_enabled_default = False
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the adjusted comfort band size."""
        thermal_components = self._get_thermal_components()
        if not thermal_components:
            return None
        
        try:
            user_preferences = thermal_components.get("user_preferences")
            if not user_preferences or not hasattr(user_preferences, 'get_adjusted_band'):
                return None
            
            # Get current outdoor temp and hvac mode from coordinator if available
            coordinator_data = self.coordinator.data
            if coordinator_data:
                outdoor_temp = coordinator_data.get("outdoor_temp")
                hvac_mode = coordinator_data.get("hvac_mode")
            else:
                outdoor_temp = None
                hvac_mode = None
            
            return user_preferences.get_adjusted_band(outdoor_temp, hvac_mode)
        except (AttributeError, TypeError, ValueError):
            return None


class LastProbeResultSensor(SmartClimateThermalSensor):
    """Sensor for last probe result status (disabled by default)."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize last probe result sensor."""
        super().__init__(coordinator, base_entity_id, "last_probe_result", config_entry)
        self._attr_name = "Last Probe Result"
        self._attr_icon = "mdi:test-tube"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_entity_registry_enabled_default = False
    
    @property
    def native_value(self) -> Optional[str]:
        """Return the last probe result status."""
        thermal_components = self._get_thermal_components()
        if not thermal_components:
            return None
        
        try:
            probe_manager = thermal_components.get("probe_manager")
            if not probe_manager:
                return "No Probe Manager"
            
            # Get the most recent probe result
            # This would need to be implemented in probe_manager
            if hasattr(probe_manager, 'get_last_probe_result'):
                last_result = probe_manager.get_last_probe_result()
                if last_result:
                    if hasattr(last_result, 'aborted') and last_result.aborted:
                        return "Aborted"
                    elif hasattr(last_result, 'confidence'):
                        if last_result.confidence > 0.8:
                            return "Success"
                        elif last_result.confidence > 0.5:
                            return "Partial"
                        else:
                            return "Poor Quality"
                    else:
                        return "Unknown"
                else:
                    return "No Results"
            return "Not Available"
        except (AttributeError, TypeError):
            return "Error"
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional probe result details as attributes."""
        thermal_components = self._get_thermal_components()
        if not thermal_components:
            return {}
        
        try:
            probe_manager = thermal_components.get("probe_manager")
            if not probe_manager or not hasattr(probe_manager, 'get_last_probe_result'):
                return {}
            
            last_result = probe_manager.get_last_probe_result()
            if not last_result:
                return {}
            
            # Extract ProbeResult dataclass fields
            attributes = {}
            if hasattr(last_result, 'tau_value'):
                attributes['tau_value_minutes'] = last_result.tau_value
            if hasattr(last_result, 'confidence'):
                attributes['confidence'] = last_result.confidence
            if hasattr(last_result, 'duration'):
                attributes['duration_seconds'] = last_result.duration
            if hasattr(last_result, 'fit_quality'):
                attributes['fit_quality'] = last_result.fit_quality
            if hasattr(last_result, 'aborted'):
                attributes['aborted'] = last_result.aborted
            
            return attributes
        except (AttributeError, TypeError):
            return {}


class ProbingActiveSensor(SmartClimateThermalSensor, BinarySensorEntity):
    """Binary sensor for probing active status (disabled by default)."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize probing active sensor."""
        super().__init__(coordinator, base_entity_id, "probing_active", config_entry)
        self._attr_name = "Probing Active"
        self._attr_device_class = BinarySensorDeviceClass.RUNNING
        self._attr_icon = "mdi:magnify-scan"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_entity_registry_enabled_default = False
    
    @property
    def is_on(self) -> Optional[bool]:
        """Return true if thermal probing is currently active."""
        thermal_components = self._get_thermal_components()
        if not thermal_components:
            return None
        
        try:
            thermal_manager = thermal_components.get("thermal_manager")
            if thermal_manager and hasattr(thermal_manager, 'current_state'):
                return thermal_manager.current_state == ThermalState.PROBING
            return False
        except (AttributeError, TypeError):
            return None
    
    @property
    def native_value(self) -> None:
        """Binary sensors don't have native_value."""
        return None


# === CYCLE HEALTH BINARY SENSOR ===

class CycleHealthSensor(SmartClimateThermalSensor, BinarySensorEntity):
    """Binary sensor for HVAC cycle health monitoring."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize cycle health sensor."""
        super().__init__(coordinator, base_entity_id, "cycle_health", config_entry)
        self._attr_name = "Cycle Health"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_icon = "mdi:heart-pulse"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def is_on(self) -> Optional[bool]:
        """Return true if there are cycle health issues (short-cycling detected)."""
        thermal_components = self._get_thermal_components()
        if not thermal_components:
            return None
        
        try:
            cycle_monitor = thermal_components.get("cycle_monitor")
            if cycle_monitor and hasattr(cycle_monitor, 'needs_adjustment'):
                # Return True for problems (opposite of healthy)
                return cycle_monitor.needs_adjustment()
            return None
        except (AttributeError, TypeError):
            return None
    
    @property
    def native_value(self) -> None:
        """Binary sensors don't have native_value."""
        return None


# Export all thermal sensor classes for easy import
__all__ = [
    # Dashboard sensors
    "ThermalStateSensor",
    "OperatingWindowLowerSensor", 
    "OperatingWindowUpperSensor",
    "ComfortPreferenceSensor",
    "ShadowModeSensor",
    # Performance sensors
    "ModelConfidenceSensor",
    "TauCoolingSensor",
    "TauWarmingSensor", 
    "AverageOnCycleSensor",
    "AverageOffCycleSensor",
    "CycleHealthSensor",
    # Debug sensors (disabled by default)
    "AdjustedComfortBandSensor",
    "LastProbeResultSensor",
    "ProbingActiveSensor",
]