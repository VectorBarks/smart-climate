"""Sensor platform for the Smart Climate integration.

This module provides up to 47 sensors across 7 categories for comprehensive Smart Climate monitoring:

1. Legacy Dashboard Sensors (5): Core functionality display
2. Advanced Feature Sensors (4): v1.3.0+ features status
3. Algorithm Metrics (9): ML learning performance
4. Performance Sensors (6): System efficiency metrics
5. AC Learning Sensors (5): HVAC behavior tracking
6. System Health Sensors (5): Resource monitoring and diagnostics
7. Thermal Efficiency Sensors (12): v1.4.0+ thermal state machine monitoring
8. Outlier Detection Sensors (1): Outlier monitoring and statistics

Key Features:
- Sensor caching with race condition protection
- Comprehensive error handling and validation
- Type-safe data access with fallback values
- DataUpdateCoordinator integration for real-time updates
- Diagnostic entity categorization for advanced sensors

Race Condition Protection:
Several sensors implement _last_known_value caching to handle coordinator data
unavailability during startup, preventing "unknown" states in dashboard templates.
"""

import logging
from typing import Any, Dict, Optional
from datetime import datetime

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .entity import SmartClimateSensorEntity
from .sensor_algorithm import (
    CorrelationCoefficientSensor,
    PredictionVarianceSensor,
    ModelEntropySensor,
    LearningRateSensor,
    MomentumFactorSensor,
    RegularizationStrengthSensor,
    MeanSquaredErrorSensor,
    MeanAbsoluteErrorSensor,
    RSquaredSensor,
)
from .sensor_performance import (
    EMACoeffficientSensor,
    PredictionLatencySensor,
    EnergyEfficiencySensor,
    SensorAvailabilitySensor,
    TemperatureStabilitySensor as PerformanceTemperatureStabilitySensor,
    LearnedDelaySensor as PerformanceLearnedDelaySensor,
)
from .sensor_ac_learning import (
    TemperatureWindowSensor,
    PowerCorrelationSensor,
    HysteresisCyclesSensor,
    ReactiveOffsetSensor,
    PredictiveOffsetSensor,
)
from .sensor_system_health import (
    MemoryUsageSensor,
    PersistenceLatencySensor,
    SamplesPerDaySensor,
    ConvergenceTrendSensor,
    OutlierDetectionSensor,
)
from .sensor_thermal import (
    ThermalStateSensor,
    OperatingWindowLowerSensor,
    OperatingWindowUpperSensor,
    ComfortPreferenceSensor,
    ShadowModeSensor,
    ModelConfidenceSensor,
    TauCoolingSensor,
    TauWarmingSensor,
    AverageOnCycleSensor,
    AverageOffCycleSensor,
    CycleHealthSensor,
    AdjustedComfortBandSensor,
    LastProbeResultSensor,
    ProbingActiveSensor,
)
from .humidity_sensors import (
    IndoorHumiditySensor,
    OutdoorHumiditySensor,
    HumidityDifferentialSensor,
    HeatIndexSensor,
    IndoorDewPointSensor,
    OutdoorDewPointSensor,
    AbsoluteHumiditySensor,
    MLHumidityOffsetSensor,
    MLHumidityConfidenceSensor,
    MLHumidityWeightSensor,
)

_LOGGER = logging.getLogger(__name__)

# Minimum samples required for calibration completion
MIN_SAMPLES_FOR_CALIBRATION = 10


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Smart Climate sensor platform from a config entry."""
    # Retrieve the coordinators created in __init__.py
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators = entry_data.get("coordinators", {})
    
    if not coordinators:
        _LOGGER.warning("No coordinators found for sensor setup in entry: %s", config_entry.entry_id)
        return
    
    # Create sensors for each climate entity
    sensors = []
    for entity_id, coordinator in coordinators.items():
        # Create all sensor types for each climate entity
        sensors.extend([
            # === LEGACY SENSORS (5) ===
            OffsetCurrentSensor(coordinator, entity_id, config_entry),
            LearningProgressSensor(coordinator, entity_id, config_entry),
            AccuracyCurrentSensor(coordinator, entity_id, config_entry),
            CalibrationStatusSensor(coordinator, entity_id, config_entry),
            HysteresisStateSensor(coordinator, entity_id, config_entry),
            
            # === EXISTING SENSORS (4) ===
            AdaptiveDelaySensor(coordinator, entity_id, config_entry),
            WeatherForecastSensor(coordinator, entity_id, config_entry),
            SeasonalAdaptationSensor(coordinator, entity_id, config_entry),
            SeasonalContributionSensor(coordinator, entity_id, config_entry),
            
            # === ALGORITHM METRICS (9) ===
            CorrelationCoefficientSensor(coordinator, entity_id, config_entry),
            PredictionVarianceSensor(coordinator, entity_id, config_entry),
            ModelEntropySensor(coordinator, entity_id, config_entry),
            LearningRateSensor(coordinator, entity_id, config_entry),
            MomentumFactorSensor(coordinator, entity_id, config_entry),
            RegularizationStrengthSensor(coordinator, entity_id, config_entry),
            MeanSquaredErrorSensor(coordinator, entity_id, config_entry),
            MeanAbsoluteErrorSensor(coordinator, entity_id, config_entry),
            RSquaredSensor(coordinator, entity_id, config_entry),
            
            # === PERFORMANCE SENSORS (6) ===
            EMACoeffficientSensor(coordinator, entity_id, config_entry),
            PredictionLatencySensor(coordinator, entity_id, config_entry),
            EnergyEfficiencySensor(coordinator, entity_id, config_entry),
            SensorAvailabilitySensor(coordinator, entity_id, config_entry),
            PerformanceTemperatureStabilitySensor(coordinator, entity_id, config_entry),
            PerformanceLearnedDelaySensor(coordinator, entity_id, config_entry),
            
            # === AC LEARNING SENSORS (5) ===
            TemperatureWindowSensor(coordinator, entity_id, config_entry),
            PowerCorrelationSensor(coordinator, entity_id, config_entry),
            HysteresisCyclesSensor(coordinator, entity_id, config_entry),
            ReactiveOffsetSensor(coordinator, entity_id, config_entry),
            PredictiveOffsetSensor(coordinator, entity_id, config_entry),
            
            # === SYSTEM HEALTH SENSORS (5) ===
            MemoryUsageSensor(coordinator, entity_id, config_entry),
            PersistenceLatencySensor(coordinator, entity_id, config_entry),
            SamplesPerDaySensor(coordinator, entity_id, config_entry),
            ConvergenceTrendSensor(coordinator, entity_id, config_entry),
            OutlierDetectionSensor(coordinator, entity_id, config_entry),
        ])
        
        # === THERMAL EFFICIENCY SENSORS (12) ===
        # Only add thermal sensors when thermal efficiency is enabled
        thermal_efficiency_enabled = config_entry.options.get("thermal_efficiency_enabled", False)
        if thermal_efficiency_enabled:
            sensors.extend([
                # Dashboard Sensors (5)
                ThermalStateSensor(coordinator, entity_id, config_entry),
                OperatingWindowLowerSensor(coordinator, entity_id, config_entry),
                OperatingWindowUpperSensor(coordinator, entity_id, config_entry),
                ComfortPreferenceSensor(coordinator, entity_id, config_entry),
                ShadowModeSensor(coordinator, entity_id, config_entry),
                
                # Performance Sensors (5)
                ModelConfidenceSensor(coordinator, entity_id, config_entry),
                TauCoolingSensor(coordinator, entity_id, config_entry),
                TauWarmingSensor(coordinator, entity_id, config_entry),
                AverageOnCycleSensor(coordinator, entity_id, config_entry),
                AverageOffCycleSensor(coordinator, entity_id, config_entry),
                CycleHealthSensor(coordinator, entity_id, config_entry),
                
                # Debug Sensors (3) - Disabled by default via entity_registry_enabled_default=False
                AdjustedComfortBandSensor(coordinator, entity_id, config_entry),
                LastProbeResultSensor(coordinator, entity_id, config_entry),
                ProbingActiveSensor(coordinator, entity_id, config_entry),
            ])
        
        # === OUTLIER DETECTION SENSORS (1) ===
        # Only add OutlierCountSensor when outlier detection is enabled
        outlier_detection_enabled = config_entry.options.get("outlier_detection_enabled", True)
        if outlier_detection_enabled:
            sensors.append(OutlierCountSensor(coordinator, entity_id, config_entry))
        
        # === HUMIDITY MONITORING SENSORS (12) ===
        # Get HumidityMonitor from entry_data (where it was stored in __init__.py)
        humidity_monitor = entry_data.get("humidity_monitor")
        _LOGGER.info("HumidityMonitor check: %s", "Found" if humidity_monitor is not None else "Not found")
        if humidity_monitor is not None:
            _LOGGER.info("Creating 10 humidity sensors for entity %s", entity_id)
            sensors.extend([
                # Core Humidity Sensors (4)
                IndoorHumiditySensor(humidity_monitor),
                OutdoorHumiditySensor(humidity_monitor),
                HumidityDifferentialSensor(humidity_monitor),
                HeatIndexSensor(humidity_monitor),
                
                # Dew Point Sensors (2)  
                IndoorDewPointSensor(humidity_monitor),
                OutdoorDewPointSensor(humidity_monitor),
                
                # Advanced Humidity Metrics (3)
                AbsoluteHumiditySensor(humidity_monitor),
                MLHumidityOffsetSensor(humidity_monitor),
                MLHumidityConfidenceSensor(humidity_monitor),
                
                # System & Status Sensors (1)
                MLHumidityWeightSensor(humidity_monitor),
            ])
        else:
            _LOGGER.debug("HumidityMonitor not available for entity %s, skipping humidity sensors", entity_id)
    
    async_add_entities(sensors)


class SmartClimateDashboardSensor(SmartClimateSensorEntity):
    """Base class for Smart Climate dashboard sensors."""
    
    def _get_thermal_persistence_diagnostics(self) -> Dict[str, Any]:
        """Get thermal persistence diagnostic attributes per §10.8.1.
        
        Accesses thermal components via hass.data pattern:
        hass.data[DOMAIN][entry_id]["thermal_components"][entity_id]
        
        Returns:
            Dict with thermal persistence diagnostic data or defaults
        """
        # Default thermal persistence diagnostic values
        default_attrs = {
            # Health Metrics per §10.8.1
            "thermal_data_last_saved": None,
            "thermal_data_age_hours": None,
            "thermal_state_restored": False,
            "corruption_recovery_count": 0,
            "probe_history_count": 0,
            "tau_values_modified": None,
            "thermal_persistence_version": "unknown"
        }
        
        try:
            # Access thermal components via coordinator's hass.data
            if not hasattr(self, 'coordinator') or not hasattr(self.coordinator, 'hass'):
                return default_attrs
                
            hass = self.coordinator.hass
            entity_id = self._base_entity_id
            
            # Look up thermal components via hass.data pattern (§10.2.2)
            # Note: We need to find the correct entry_id for this entity
            for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
                thermal_components = entry_data.get("thermal_components", {})
                if entity_id in thermal_components:
                    thermal_manager = thermal_components[entity_id].get("thermal_manager")
                    
                    if thermal_manager:
                        # Extract diagnostic data from ThermalManager
                        attrs = default_attrs.copy()
                        
                        # thermal_data_last_saved (timestamp)
                        if hasattr(thermal_manager, 'thermal_data_last_saved'):
                            last_saved = thermal_manager.thermal_data_last_saved
                            attrs["thermal_data_last_saved"] = last_saved.isoformat() if last_saved else None
                            
                            # thermal_data_age_hours (calculated age)
                            if last_saved:
                                age_delta = datetime.now() - last_saved
                                attrs["thermal_data_age_hours"] = round(age_delta.total_seconds() / 3600, 1)
                        
                        # thermal_state_restored (bool)
                        if hasattr(thermal_manager, 'thermal_state_restored'):
                            attrs["thermal_state_restored"] = thermal_manager.thermal_state_restored
                        
                        # corruption_recovery_count (int)
                        if hasattr(thermal_manager, 'corruption_recovery_count'):
                            attrs["corruption_recovery_count"] = thermal_manager.corruption_recovery_count
                        
                        # probe_history_count (0-5)
                        if hasattr(thermal_manager, '_model') and hasattr(thermal_manager._model, '_probe_history'):
                            attrs["probe_history_count"] = len(thermal_manager._model._probe_history)
                        
                        # tau_values_modified (timestamp) - use actual modification time
                        if hasattr(thermal_manager, '_model'):
                            model = thermal_manager._model
                            if hasattr(model, 'tau_last_modified') and model.tau_last_modified:
                                attrs["tau_values_modified"] = model.tau_last_modified.isoformat()
                            else:
                                attrs["tau_values_modified"] = None  # Never modified
                        
                        # thermal_persistence_version (schema version)
                        attrs["thermal_persistence_version"] = "1.0"  # From §10.3.1
                        
                        _LOGGER.debug("Thermal persistence diagnostics for %s: %s", entity_id, attrs)
                        return attrs
                    break
            
            # No thermal manager found - return defaults
            _LOGGER.debug("No thermal manager found for entity %s, using defaults", entity_id)
            return default_attrs
            
        except Exception as exc:
            _LOGGER.warning("Error getting thermal persistence diagnostics for entity %s: %s", 
                          getattr(self, '_base_entity_id', 'unknown'), exc)
            return default_attrs


class OffsetCurrentSensor(SmartClimateDashboardSensor):
    """Sensor for current temperature offset."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize offset sensor."""
        super().__init__(coordinator, base_entity_id, "offset_current", config_entry)
        self._attr_name = "Current Offset"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:thermometer-lines"
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the current offset value."""
        if not self.coordinator.data:
            return None
        
        try:
            return self.coordinator.data.get("calculated_offset")
        except (AttributeError, TypeError):
            return None


class LearningProgressSensor(SmartClimateDashboardSensor):
    """Sensor for learning progress percentage."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize learning progress sensor."""
        super().__init__(coordinator, base_entity_id, "learning_progress", config_entry)
        self._attr_name = "Learning Progress"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:brain"
    
    @property
    def native_value(self) -> int:
        """Return the learning progress percentage."""
        if not self.coordinator.data:
            return 0
            
        try:
            learning_info = self.coordinator.data.get("learning_info", {})
            
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
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize accuracy sensor."""
        super().__init__(coordinator, base_entity_id, "accuracy_current", config_entry)
        self._attr_name = "Current Accuracy"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:target"
    
    @property
    def native_value(self) -> int:
        """Return the current accuracy percentage."""
        if not self.coordinator.data:
            return 0
            
        try:
            learning_info = self.coordinator.data.get("learning_info", {})
            accuracy = learning_info.get("accuracy", 0.0)
            # Convert to percentage
            return int(accuracy * 100)
        except Exception:
            return 0


class CalibrationStatusSensor(SmartClimateDashboardSensor):
    """Sensor for calibration phase status."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize calibration status sensor."""
        super().__init__(coordinator, base_entity_id, "calibration_status", config_entry)
        self._attr_name = "Calibration Status"
        self._attr_icon = "mdi:progress-check"
    
    @property
    def native_value(self) -> str:
        """Return the calibration status text."""
        if not self.coordinator.data:
            return "Unknown"
            
        try:
            learning_info = self.coordinator.data.get("learning_info", {})
            
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
        """Return additional attributes including thermal persistence diagnostics."""
        base_attrs = {
            "samples_collected": 0,
            "minimum_required": MIN_SAMPLES_FOR_CALIBRATION,
            "learning_enabled": False,
            "last_sample": None,
        }
        
        # Add thermal persistence diagnostic attributes per §10.8.1
        thermal_attrs = self._get_thermal_persistence_diagnostics()
        base_attrs.update(thermal_attrs)
        
        if not self.coordinator.data:
            return base_attrs
            
        try:
            learning_info = self.coordinator.data.get("learning_info", {})
            base_attrs.update({
                "samples_collected": learning_info.get("samples", 0),
                "minimum_required": MIN_SAMPLES_FOR_CALIBRATION,
                "learning_enabled": learning_info.get("enabled", False),
                "last_sample": learning_info.get("last_sample_time"),
            })
            return base_attrs
        except Exception:
            return base_attrs


class HysteresisStateSensor(SmartClimateDashboardSensor):
    """Sensor for human-readable AC hysteresis state."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize hysteresis state sensor."""
        super().__init__(coordinator, base_entity_id, "hysteresis_state", config_entry)
        self._attr_name = "Hysteresis State"
        self._attr_icon = "mdi:sine-wave"
    
    @property
    def native_value(self) -> str:
        """Return the human-readable hysteresis state."""
        if not self.coordinator.data:
            return "Unknown"
            
        try:
            learning_info = self.coordinator.data.get("learning_info", {})
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
        """Return additional attributes including thermal persistence diagnostics."""
        base_attrs = {
            "power_sensor_configured": False,
            "start_threshold": "Not available",
            "stop_threshold": "Not available",
            "temperature_window": "Not available",
            "start_samples": 0,
            "stop_samples": 0,
            "ready": False,
        }
        
        # Add thermal persistence diagnostic attributes per §10.8.1
        thermal_attrs = self._get_thermal_persistence_diagnostics()
        base_attrs.update(thermal_attrs)
        
        if not self.coordinator.data:
            return base_attrs
            
        try:
            learning_info = self.coordinator.data.get("learning_info", {})
            
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
            
            base_attrs.update({
                "power_sensor_configured": power_configured,
                "start_threshold": start_display,
                "stop_threshold": stop_display,
                "temperature_window": window_display,
                "start_samples": learning_info.get("start_samples_collected", 0),
                "stop_samples": learning_info.get("stop_samples_collected", 0),
                "ready": learning_info.get("hysteresis_ready", False),
            })
            return base_attrs
        except Exception:
            return base_attrs

class AdaptiveDelaySensor(SmartClimateDashboardSensor):
    """Sensor for adaptive delay value."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize adaptive delay sensor."""
        super().__init__(coordinator, base_entity_id, "adaptive_delay", config_entry)
        self._attr_name = "Adaptive Delay"
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:camera-timer"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the adaptive delay value."""
        if not self.coordinator.data:
            return None
        
        try:
            delay_data = self.coordinator.data.get("delay_data", {})
            return delay_data.get("adaptive_delay")
        except (AttributeError, TypeError):
            return None


class WeatherForecastSensor(SmartClimateDashboardSensor, BinarySensorEntity):
    """Binary sensor for weather forecast status.
    
    This sensor displays whether weather forecast integration is enabled and functioning.
    Implements robust caching to handle coordinator data unavailability during startup.
    
    Features:
    - Race condition protection with _last_known_value caching
    - Type validation to ensure boolean values
    - Graceful fallback to cached values on coordinator errors
    - Diagnostic entity category for advanced users
    
    State Values:
    - True: Weather forecast is enabled and configured
    - False: Weather forecast is disabled
    - None: Unknown state (only during initial startup)
    
    Race Condition Fix:
    This sensor was affected by a race condition where it would return None during
    startup when coordinator data wasn't available. The fix implements:
    1. Caching of last known valid boolean value
    2. Type validation to reject non-boolean values
    3. Error handling that preserves cached state
    4. Graceful degradation during initialization
    """
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize weather forecast sensor.
        
        Args:
            coordinator: DataUpdateCoordinator instance
            base_entity_id: Base entity ID for the climate entity
            config_entry: Home Assistant configuration entry
        """
        super().__init__(coordinator, base_entity_id, "weather_forecast", config_entry)
        self._attr_name = "Weather Forecast"
        self._attr_icon = "mdi:weather-partly-cloudy"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._last_known_value = None
    
    @property
    def is_on(self) -> Optional[bool]:
        """Return true if weather forecast is enabled.
        
        This method implements robust caching to handle coordinator data unavailability
        during startup and runtime errors. It validates data types and provides
        graceful fallback to cached values.
        
        Returns:
            bool: True if weather forecast is enabled, False if disabled
            None: Only returned during initial startup before any data is available
            
        Caching Behavior:
        - Stores last known valid boolean value in self._last_known_value
        - Returns cached value when coordinator data is unavailable
        - Updates cache only with validated boolean values
        - Logs warnings for invalid data types
        
        Race Condition Protection:
        This method was designed to fix the race condition where sensors would
        return None indefinitely if coordinator data wasn't available during
        initialization, causing dashboard templates to show "unknown" states.
        """
        try:
            # Check coordinator data with robust error handling
            if (hasattr(self, 'coordinator') and 
                self.coordinator is not None and 
                hasattr(self.coordinator, 'data') and 
                self.coordinator.data is not None):
                
                # Get weather forecast value with type validation
                weather_forecast_value = self.coordinator.data.get("weather_forecast")
                
                # Validate that the value is a boolean
                if isinstance(weather_forecast_value, bool):
                    # Cache the last known good value
                    self._last_known_value = weather_forecast_value
                    return weather_forecast_value
                
                # Handle non-boolean values
                if weather_forecast_value is not None:
                    _LOGGER.warning(
                        "Weather forecast value is not boolean: %s (type: %s)",
                        weather_forecast_value, type(weather_forecast_value)
                    )
            
            # If coordinator data is not available or invalid, return cached value
            if self._last_known_value is not None:
                return self._last_known_value
                
            # No coordinator data and no cache - return None
            return None
            
        except (AttributeError, TypeError, KeyError) as e:
            _LOGGER.warning("Error accessing weather forecast data: %s", e)
            
            # Return cached value if available
            if self._last_known_value is not None:
                return self._last_known_value
            
            return None
    
    @property
    def native_value(self) -> None:
        """Binary sensors don't have native_value."""
        return None


class SeasonalAdaptationSensor(SmartClimateDashboardSensor, BinarySensorEntity):
    """Binary sensor for seasonal adaptation status.
    
    This sensor displays whether seasonal adaptation learning is enabled and active.
    Implements the same caching mechanism as WeatherForecastSensor to handle
    coordinator data unavailability during startup.
    
    Features:
    - Race condition protection with _last_known_value caching
    - Nested data validation for seasonal_data.enabled
    - Type validation to ensure boolean values
    - Graceful fallback to cached values on coordinator errors
    
    State Values:
    - True: Seasonal adaptation is enabled and learning patterns
    - False: Seasonal adaptation is disabled
    - None: Unknown state (only during initial startup)
    
    Data Path:
    coordinator.data["seasonal_data"]["enabled"] -> boolean
    """
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize seasonal adaptation sensor.
        
        Args:
            coordinator: DataUpdateCoordinator instance
            base_entity_id: Base entity ID for the climate entity
            config_entry: Home Assistant configuration entry
        """
        super().__init__(coordinator, base_entity_id, "seasonal_adaptation", config_entry)
        self._attr_name = "Seasonal Adaptation"
        self._attr_icon = "mdi:sun-snowflake"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._last_known_value = None
    
    @property
    def is_on(self) -> Optional[bool]:
        """Return true if seasonal adaptation is enabled.
        
        This method implements robust nested data validation to safely access
        the seasonal_data.enabled value from coordinator data. It provides
        comprehensive type checking and caching for race condition protection.
        
        Returns:
            bool: True if seasonal adaptation is enabled, False if disabled
            None: Only returned during initial startup before any data is available
            
        Caching Behavior:
        - Stores last known valid boolean value in self._last_known_value
        - Returns cached value when coordinator data is unavailable
        - Updates cache only with validated boolean values from nested data
        - Handles nested data structure validation gracefully
        
        Data Validation:
        1. Checks coordinator.data is available and is a dictionary
        2. Validates seasonal_data is a dictionary
        3. Ensures enabled value is a boolean
        4. Falls back to cached value at any validation failure
        """
        # Check if coordinator data exists
        if not self.coordinator.data:
            return self._last_known_value
        
        try:
            # Robust coordinator.data checking
            coordinator_data = self.coordinator.data
            if not isinstance(coordinator_data, dict):
                return self._last_known_value
            
            # Nested data access validation (seasonal_data.enabled)
            seasonal_data = coordinator_data.get("seasonal_data")
            if not isinstance(seasonal_data, dict):
                return self._last_known_value
            
            # Type validation for enabled value
            enabled_value = seasonal_data.get("enabled")
            if not isinstance(enabled_value, bool):
                return self._last_known_value
            
            # Caching of last known good values
            self._last_known_value = enabled_value
            return enabled_value
            
        except (AttributeError, TypeError, KeyError) as e:
            # Graceful handling of None/invalid data
            _LOGGER.debug("SeasonalAdaptationSensor data access error: %s", e)
            return self._last_known_value
    
    @property
    def native_value(self) -> None:
        """Binary sensors don't have native_value."""
        return None


class SeasonalContributionSensor(SmartClimateDashboardSensor):
    """Sensor for seasonal contribution percentage."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize seasonal contribution sensor."""
        super().__init__(coordinator, base_entity_id, "seasonal_contribution", config_entry)
        self._attr_name = "Seasonal Contribution"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:sun-snowflake"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the seasonal contribution percentage."""
        if not self.coordinator.data:
            return None
        
        try:
            seasonal_data = self.coordinator.data.get("seasonal_data", {})
            return seasonal_data.get("contribution")
        except (AttributeError, TypeError):
            return None


class OutlierCountSensor(SmartClimateDashboardSensor):
    """Sensor for total count of outliers detected."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize outlier count sensor."""
        super().__init__(coordinator, base_entity_id, "outlier_count", config_entry)
        self._attr_name = "Outlier Count"
        self._attr_icon = "mdi:alert-circle-check-outline"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> int:
        """Return the outlier count from coordinator."""
        if not self.coordinator.data:
            return 0
        
        try:
            return getattr(self.coordinator.data, "outlier_count", 0)
        except (AttributeError, TypeError):
            return 0
    
    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes including thermal persistence diagnostics."""
        base_attrs = {
            "total_sensors": 0,
            "outlier_rate": 0.0,
            "last_detection_time": None,
        }
        
        # Add thermal persistence diagnostic attributes per §10.8.1
        thermal_attrs = self._get_thermal_persistence_diagnostics()
        base_attrs.update(thermal_attrs)
        
        if not self.coordinator.data:
            return base_attrs
        
        try:
            outlier_stats = getattr(self.coordinator.data, "outlier_statistics", {})
            if not outlier_stats:
                return base_attrs
            
            base_attrs.update({
                "total_sensors": outlier_stats.get("total_samples", 0),
                "outlier_rate": outlier_stats.get("outlier_rate", 0.0),
                "last_detection_time": outlier_stats.get("last_detection_time"),
            })
            return base_attrs
        except (AttributeError, TypeError):
            return base_attrs

