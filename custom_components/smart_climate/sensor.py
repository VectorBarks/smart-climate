"""Sensor platform for the Smart Climate integration.

This module provides 34 sensors across 5 categories for comprehensive Smart Climate monitoring:

1. Legacy Dashboard Sensors (5): Core functionality display
2. Advanced Feature Sensors (4): v1.3.0+ features status
3. Algorithm Metrics (9): ML learning performance
4. Performance Sensors (6): System efficiency metrics
5. AC Learning Sensors (5): HVAC behavior tracking
6. System Health Sensors (5): Resource monitoring and diagnostics

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
    
    async_add_entities(sensors)


class SmartClimateDashboardSensor(SmartClimateSensorEntity):
    """Base class for Smart Climate dashboard sensors."""
    pass


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
        """Return additional attributes."""
        if not self.coordinator.data:
            return {
                "samples_collected": 0,
                "minimum_required": MIN_SAMPLES_FOR_CALIBRATION,
                "learning_enabled": False,
                "last_sample": None,
            }
            
        try:
            learning_info = self.coordinator.data.get("learning_info", {})
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
        """Return additional attributes."""
        if not self.coordinator.data:
            return {
                "power_sensor_configured": False,
                "start_threshold": "Not available",
                "stop_threshold": "Not available",
                "temperature_window": "Not available",
                "start_samples": 0,
                "stop_samples": 0,
                "ready": False,
            }
            
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

