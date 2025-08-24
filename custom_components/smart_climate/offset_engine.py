"""Offset calculation engine for Smart Climate Control."""

import logging
import time
from typing import Optional, Dict, List, Tuple, Callable, TYPE_CHECKING, Literal, Any
import statistics
from datetime import datetime
from collections import deque
import sys
import numpy as np

from .models import OffsetInput, OffsetResult
from .lightweight_learner import LightweightOffsetLearner as EnhancedLightweightOffsetLearner
from .outlier_detector import OutlierDetector
from .dto import (
    DashboardData,
    SeasonalData,
    DelayData,
    ACBehaviorData,
    PerformanceData,
    SystemHealthData,
    DiagnosticsData,
    AlgorithmMetrics,
)
from .const import (
    DEFAULT_POWER_IDLE_THRESHOLD,
    DEFAULT_POWER_MIN_THRESHOLD,
    DEFAULT_POWER_MAX_THRESHOLD,
    DEFAULT_SAVE_INTERVAL,
    CONF_SAVE_INTERVAL,
    CONF_VALIDATION_OFFSET_MIN,
    CONF_VALIDATION_OFFSET_MAX,
    CONF_VALIDATION_TEMP_MIN,
    CONF_VALIDATION_TEMP_MAX,
    CONF_VALIDATION_RATE_LIMIT_SECONDS,
    DEFAULT_VALIDATION_OFFSET_MIN,
    DEFAULT_VALIDATION_OFFSET_MAX,
    DEFAULT_VALIDATION_TEMP_MIN,
    DEFAULT_VALIDATION_TEMP_MAX,
    DEFAULT_VALIDATION_RATE_LIMIT_SECONDS,
    CONF_FORECAST_ENABLED,
    CONF_OUTDOOR_SENSOR,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from .data_store import SmartClimateDataStore
    from .seasonal_learner import SeasonalHysteresisLearner
    from .delay_learner import DelayLearner
    from .forecast_engine import ForecastEngine
    from .feature_engineering import FeatureEngineering

# Type definitions for thermal persistence callbacks
GetThermalDataCallback = Callable[[], Optional[Dict[str, Any]]]
RestoreThermalDataCallback = Callable[[Dict[str, Any]], None]

_LOGGER = logging.getLogger(__name__)

# Calibration phase threshold - configurable in the future
MIN_SAMPLES_FOR_ACTIVE_CONTROL = 10  # Exit calibration after this many samples

# Cache duration constants for dashboard data
CACHE_DUR_MEMORY = 300      # 5 minutes for memory usage
CACHE_DUR_TRENDS = 1800     # 30 minutes for long-term trends  
CACHE_DUR_PERF = 60         # 1 minute for general performance
CACHE_DUR_PERSISTENCE = 3600 # 1 hour (relies on event invalidation)

# HysteresisState defines the possible states of the AC cycle.
HysteresisState = Literal[
    "learning_hysteresis",      # Not enough data to determine thresholds.
    "active_phase",             # AC is actively cooling/heating (high power).
    "idle_above_start_threshold", # AC is off, but room temp is above the point where it should start.
    "idle_below_stop_threshold",  # AC is off, and room temp is below the point where it just stopped.
    "idle_stable_zone"          # AC is off, room temp is between stop and start thresholds.
]


class HysteresisLearner:
    """Learns the operational temperature thresholds of an AC unit based on power transitions."""

    def __init__(self, min_samples: int = 5, max_samples: int = 50) -> None:
        """
        Initializes the HysteresisLearner.

        Args:
            min_samples: The minimum number of start and stop samples required before thresholds are considered reliable.
            max_samples: The maximum number of recent samples to keep for calculating thresholds.
        """
        # Internal state attributes
        self._min_samples: int = min_samples
        self._start_temps: deque[float] = deque(maxlen=max_samples)
        self._stop_temps: deque[float] = deque(maxlen=max_samples)

        # Publicly accessible learned thresholds
        self.learned_start_threshold: Optional[float] = None
        self.learned_stop_threshold: Optional[float] = None

    @property
    def has_sufficient_data(self) -> bool:
        """
        Checks if enough data has been collected to provide reliable thresholds.

        Returns:
            True if both start and stop sample counts meet the minimum requirement.
        """
        return len(self._start_temps) >= self._min_samples and len(self._stop_temps) >= self._min_samples

    def record_transition(self, transition_type: Literal['start', 'stop'], room_temp: float) -> None:
        """
        Records the room temperature during a power state transition. This is the primary data input method.

        Args:
            transition_type: 'start' for idle->high power, 'stop' for high->idle power.
            room_temp: The current room temperature at the moment of transition.
        """
        if transition_type == 'start':
            self._start_temps.append(room_temp)
        elif transition_type == 'stop':
            self._stop_temps.append(room_temp)
        
        # Update thresholds after recording new data
        self._update_thresholds()

    def get_hysteresis_state(self, power_state: str, room_temp: float) -> HysteresisState:
        """
        Determines the current position within the hysteresis cycle based on learned thresholds.

        Args:
            power_state: The current power state ("idle", "low", "moderate", "high").
            room_temp: The current room temperature.

        Returns:
            A HysteresisState string representing the current phase of the cycle.
        """
        # Check if we have sufficient data to determine thresholds
        if not self.has_sufficient_data:
            return "learning_hysteresis"
        
        # Handle edge case where thresholds are None despite sufficient data
        if self.learned_start_threshold is None or self.learned_stop_threshold is None:
            return "learning_hysteresis"
        
        # If power state indicates active operation (moderate or high), return active_phase
        if power_state in ("moderate", "high"):
            return "active_phase"
        
        # For idle/low power states, compare room temperature against learned thresholds
        # Default to idle behavior for any unknown power states (defensive programming)
        
        # Room temperature above start threshold - AC should be starting but isn't
        if room_temp > self.learned_start_threshold:
            return "idle_above_start_threshold"
        
        # Room temperature below stop threshold - AC has stopped and room is cooling down
        if room_temp < self.learned_stop_threshold:
            return "idle_below_stop_threshold"
        
        # Room temperature between stop and start thresholds (stable zone)
        # This includes the case where room_temp equals either threshold
        return "idle_stable_zone"

    def serialize_for_persistence(self) -> Dict[str, List[float]]:
        """
        Serializes the learner's state into a JSON-compatible dictionary.

        Returns:
            A dictionary containing the lists of start and stop temperatures.
        """
        return {
            "start_temps": list(self._start_temps),
            "stop_temps": list(self._stop_temps)
        }

    def restore_from_persistence(self, data: Dict) -> None:
        """
        Restores the learner's state from a dictionary.

        Args:
            data: A dictionary conforming to the persistence schema.
        """
        if isinstance(data, dict):
            start_temps = data.get("start_temps", [])
            stop_temps = data.get("stop_temps", [])
            
            if isinstance(start_temps, list):
                self._start_temps.clear()
                for temp in start_temps:
                    if isinstance(temp, (int, float)):
                        self._start_temps.append(float(temp))
            
            if isinstance(stop_temps, list):
                self._stop_temps.clear()
                for temp in stop_temps:
                    if isinstance(temp, (int, float)):
                        self._stop_temps.append(float(temp))
            
            # Update thresholds after restoring data
            self._update_thresholds()

    def _update_thresholds(self) -> None:
        """
        (Private) Recalculates the learned thresholds using the median of collected samples.
        The median is used for robustness against outlier temperature readings.
        """
        if self.has_sufficient_data:
            self.learned_start_threshold = statistics.median(self._start_temps)
            self.learned_stop_threshold = statistics.median(self._stop_temps)
        else:
            self.learned_start_threshold = None
            self.learned_stop_threshold = None



class OffsetEngine:
    """Calculates temperature offset for accurate climate control."""
    
    def __init__(
        self, 
        config: dict, 
        seasonal_learner: Optional["SeasonalHysteresisLearner"] = None,
        delay_learner: Optional["DelayLearner"] = None,
        outlier_detection_config: Optional[dict] = None,
        get_thermal_data_cb: Optional[GetThermalDataCallback] = None,
        restore_thermal_data_cb: Optional[RestoreThermalDataCallback] = None,
        feature_engineer: Optional["FeatureEngineering"] = None
    ):
        """Initialize the offset engine with configuration.
        
        Args:
            config: Configuration dictionary
            seasonal_learner: Optional seasonal learner for enhanced predictions
            delay_learner: Optional delay learner for adaptive timing
            outlier_detection_config: Optional configuration for outlier detection
            get_thermal_data_cb: Optional callback to get thermal data for persistence
            restore_thermal_data_cb: Optional callback to restore thermal data from persistence
            feature_engineer: Optional FeatureEngineering for enriching input features
        """
        self._max_offset = config.get("max_offset", 5.0)
        self._ml_enabled = config.get("ml_enabled", True)
        self._ml_model = None  # Loaded when available
        
        # Feature engineering for ML input enhancement
        self._feature_engineer = feature_engineer
        
        # Thermal persistence callbacks (v2.1 schema support)
        self._get_thermal_data_cb = get_thermal_data_cb
        self._restore_thermal_data_cb = restore_thermal_data_cb
        
        # ForecastEngine reference (set later via set_forecast_engine)
        self._forecast_engine = None
        
        # Power thresholds configuration
        self._power_idle_threshold = config.get("power_idle_threshold", DEFAULT_POWER_IDLE_THRESHOLD)
        self._power_min_threshold = config.get("power_min_threshold", DEFAULT_POWER_MIN_THRESHOLD)
        self._power_max_threshold = config.get("power_max_threshold", DEFAULT_POWER_MAX_THRESHOLD)
        
        # Learning configuration (disabled by default for backward compatibility)
        self._enable_learning = config.get("enable_learning", False)
        self._learner: Optional[EnhancedLightweightOffsetLearner] = None
        self._update_callbacks: List[Callable] = []  # For state update notifications
        
        # Hysteresis learning configuration
        power_sensor = config.get("power_sensor")
        self._hysteresis_enabled = power_sensor is not None and power_sensor != ""
        self._hysteresis_learner = HysteresisLearner()
        self._last_power_state: Optional[str] = None
        
        # Add state for the stable calibration offset
        self._stable_calibration_offset: Optional[float] = None
        
        # Add state for the last calculated offset (for dashboard data)
        self._last_offset: float = 0.0
        
        # Add state for humidity contribution (for feature contribution tracking)
        self._last_humidity_contribution: float = 0.0
        
        # ML feedback loop prevention - track adjustment sources
        self._prediction_active: bool = False
        self._adjustment_source: Optional[str] = None  # Track if adjustment from prediction vs user
        
        # Weather forecast configuration (from config, not existence)
        self._weather_forecast_enabled = config.get(CONF_FORECAST_ENABLED, False)
        
        # Seasonal learning integration
        self._seasonal_learner: Optional["SeasonalHysteresisLearner"] = seasonal_learner
        # Check config for outdoor sensor, not just learner existence
        outdoor_sensor = config.get(CONF_OUTDOOR_SENSOR)
        self._seasonal_features_enabled: bool = outdoor_sensor is not None and outdoor_sensor != ""
        
        # Delay learning integration
        self._delay_learner: Optional["DelayLearner"] = delay_learner
        
        # Outlier detection integration
        self._outlier_detector: Optional[OutlierDetector] = None
        if outlier_detection_config:
            self._outlier_detector = OutlierDetector(config=outlier_detection_config)
            _LOGGER.debug("OutlierDetector initialized with config: %s", outlier_detection_config)
        else:
            _LOGGER.debug("No outlier detection configured")
        
        # State-aware learning protocol (v1.4.0)
        self._learning_paused: bool = False
        
        # Dashboard cache for performance
        self._dashboard_cache: Dict[str, Any] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Save configuration and statistics
        self._save_interval = config.get(CONF_SAVE_INTERVAL, DEFAULT_SAVE_INTERVAL)
        self._save_count = 0
        self._failed_save_count = 0
        self._last_save_time: Optional[datetime] = None
        
        # ML input validation configuration
        self._validation_offset_min = config.get(CONF_VALIDATION_OFFSET_MIN, DEFAULT_VALIDATION_OFFSET_MIN)
        self._validation_offset_max = config.get(CONF_VALIDATION_OFFSET_MAX, DEFAULT_VALIDATION_OFFSET_MAX)
        self._validation_temp_min = config.get(CONF_VALIDATION_TEMP_MIN, DEFAULT_VALIDATION_TEMP_MIN)
        self._validation_temp_max = config.get(CONF_VALIDATION_TEMP_MAX, DEFAULT_VALIDATION_TEMP_MAX)
        self._validation_rate_limit_seconds = config.get(CONF_VALIDATION_RATE_LIMIT_SECONDS, DEFAULT_VALIDATION_RATE_LIMIT_SECONDS)
        self._last_sample_time: Optional[float] = None
        
        if self._enable_learning:
            self._learner = EnhancedLightweightOffsetLearner()
            _LOGGER.debug("Learning enabled - EnhancedLightweightOffsetLearner initialized")
        
        _LOGGER.debug(
            "OffsetEngine initialized with max_offset=%s, ml_enabled=%s, learning_enabled=%s, "
            "hysteresis_enabled=%s, seasonal_enabled=%s, delay_learning=%s, outlier_detection=%s, "
            "power_thresholds(idle=%s, min=%s, max=%s), save_interval=%s, "
            "validation_bounds(offset=%s to %s, temp=%s to %s, rate_limit=%ss)",
            self._max_offset,
            self._ml_enabled,
            self._enable_learning,
            self._hysteresis_enabled,
            self._seasonal_features_enabled,
            delay_learner is not None,
            self._outlier_detector is not None,
            self._power_idle_threshold,
            self._power_min_threshold,
            self._power_max_threshold,
            self._save_interval,
            self._validation_offset_min,
            self._validation_offset_max,
            self._validation_temp_min,
            self._validation_temp_max,
            self._validation_rate_limit_seconds
        )
    
    @property
    def is_learning_enabled(self) -> bool:
        """Return true if learning is enabled."""
        return self._enable_learning
    
    @property
    def save_count(self) -> int:
        """Return the number of successful saves."""
        return self._save_count
    
    @property
    def failed_save_count(self) -> int:
        """Return the number of failed saves."""
        return self._failed_save_count
    
    @property
    def last_save_time(self) -> Optional[datetime]:
        """Return the timestamp of the last successful save."""
        return self._last_save_time
    
    @property
    def is_in_calibration_phase(self) -> bool:
        """
        Determines if the system is in the initial calibration phase.
        During this phase, we use stable state offset caching.
        """
        if not self._enable_learning or not self._learner:
            return False
        
        try:
            stats = self._learner.get_statistics()
            return stats.samples_collected < MIN_SAMPLES_FOR_ACTIVE_CONTROL
        except Exception:
            return True
    
    def _get_power_state(self, power_consumption: float) -> str:
        """Determine power state based on consumption and thresholds.
        
        Args:
            power_consumption: Current power consumption in watts
            
        Returns:
            Power state: "idle", "low", "moderate", or "high"
        """
        if power_consumption < self._power_idle_threshold:
            return "idle"
        elif power_consumption < self._power_min_threshold:
            return "low"
        elif power_consumption < self._power_max_threshold:
            return "moderate"
        else:
            return "high"
    
    def _validate_feedback(self, offset: float, room_temp: float, timestamp: float) -> bool:
        """Validate feedback data before training to prevent data poisoning.
        
        Args:
            offset: Temperature offset value to validate
            room_temp: Room temperature to validate  
            timestamp: Timestamp to validate
            
        Returns:
            True if data is valid, False if it should be rejected
        """
        try:
            # Type validation - ensure all values are numeric but not boolean
            if not isinstance(offset, (int, float)) or offset is None or isinstance(offset, bool):
                _LOGGER.warning("Invalid offset type: %s", type(offset).__name__)
                return False
            
            if not isinstance(room_temp, (int, float)) or room_temp is None or isinstance(room_temp, bool):
                _LOGGER.warning("Invalid room temperature type: %s", type(room_temp).__name__)
                return False
                
            if not isinstance(timestamp, (int, float)) or timestamp is None or isinstance(timestamp, bool):
                _LOGGER.warning("Invalid timestamp type: %s", type(timestamp).__name__)
                return False
            
            # Offset bounds validation (-10°C to +10°C reasonable for any climate)
            if not self._validation_offset_min <= offset <= self._validation_offset_max:
                _LOGGER.warning("Invalid offset range: %s (bounds: %s to %s)", 
                              offset, self._validation_offset_min, self._validation_offset_max)
                return False
            
            # Timestamp validation (not in future)
            current_time = time.time()
            if timestamp > current_time:
                _LOGGER.warning("Future timestamp rejected: %s (current: %s)", timestamp, current_time)
                return False
            
            # Temperature bounds validation (configurable reasonable indoor range)
            if not self._validation_temp_min <= room_temp <= self._validation_temp_max:
                _LOGGER.warning("Invalid temperature: %s (bounds: %s to %s)", 
                              room_temp, self._validation_temp_min, self._validation_temp_max)
                return False
            
            # Rate limiting - max 1 sample per configured interval
            # Only apply rate limiting if the new timestamp is after the last sample
            if self._last_sample_time is not None and timestamp > self._last_sample_time:
                time_since_last = timestamp - self._last_sample_time
                if time_since_last < self._validation_rate_limit_seconds:
                    _LOGGER.debug("Rate limit: too frequent samples (%.1fs < %ds)", 
                                time_since_last, self._validation_rate_limit_seconds)
                    return False
            
            # Update last sample time on successful validation (only if timestamp is newer)
            if self._last_sample_time is None or timestamp > self._last_sample_time:
                self._last_sample_time = timestamp
            return True
            
        except Exception as exc:
            _LOGGER.warning("Error during feedback validation: %s", exc)
            return False
    
    def _sanitize_float(self, value: any, param_name: str) -> Optional[float]:
        """Sanitize a value to a float, handling non-numeric sensor values gracefully.
        
        Args:
            value: The value to sanitize (can be float, int, string, or None)
            param_name: Name of the parameter for logging purposes
            
        Returns:
            Float value if valid, None if invalid or out of range
        """
        if value is None:
            return None
        
        # Handle string values
        if isinstance(value, str):
            # Handle empty strings
            if not value.strip():
                return None
            
            # Handle common non-numeric states from Home Assistant sensors
            if value.lower() in ['unavailable', 'unknown', 'none', 'null', '']:
                return None
            
            # Try to convert numeric strings
            try:
                value = float(value)
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Failed to convert %s value '%s' to float - treating as unavailable",
                    param_name, value
                )
                return None
        
        # Convert to float if not already
        try:
            float_value = float(value)
        except (ValueError, TypeError):
            _LOGGER.warning(
                "Failed to convert %s value '%s' to float - treating as unavailable", 
                param_name, value
            )
            return None
        
        # Apply sanity checks for reasonable sensor ranges
        if float_value < -10000 or float_value > 10000:
            _LOGGER.warning(
                "Rejecting %s value %.2f - outside reasonable range (-10000 to 10000)",
                param_name, float_value
            )
            return None
        
        return float_value
    
    def _validate_learning_data(self, input_data: OffsetInput) -> bool:
        """Validate learning data using outlier detection to prevent ML model corruption.
        
        Args:
            input_data: The input data to validate
            
        Returns:
            True if data is valid for learning, False if outliers are detected
        """
        if not self._outlier_detector:
            # No outlier detection configured - all data is valid
            return True
        
        try:
            # Check room temperature for outliers
            if input_data.room_temp is not None:
                if self._outlier_detector.is_temperature_outlier(input_data.room_temp):
                    _LOGGER.debug(
                        "Outlier detected in room temperature: %.2f°C. Skipping learning.",
                        input_data.room_temp
                    )
                    return False
                # Add valid sample to history for future detection
                self._outlier_detector.add_temperature_sample(input_data.room_temp)
            
            # Check AC internal temperature for outliers
            if input_data.ac_internal_temp is not None:
                if self._outlier_detector.is_temperature_outlier(input_data.ac_internal_temp):
                    _LOGGER.debug(
                        "Outlier detected in AC internal temperature: %.2f°C. Skipping learning.",
                        input_data.ac_internal_temp
                    )
                    return False
                # Add valid sample to history for future detection
                self._outlier_detector.add_temperature_sample(input_data.ac_internal_temp)
            
            # Check power consumption for outliers
            if input_data.power_consumption is not None:
                if self._outlier_detector.is_power_outlier(input_data.power_consumption):
                    _LOGGER.debug(
                        "Outlier detected in power consumption: %.2fW. Skipping learning.",
                        input_data.power_consumption
                    )
                    return False
                # Add valid sample to history for future detection
                self._outlier_detector.add_power_sample(input_data.power_consumption)
            
            # Check outdoor temperature for outliers (if available)
            if input_data.outdoor_temp is not None:
                if self._outlier_detector.is_temperature_outlier(input_data.outdoor_temp):
                    _LOGGER.debug(
                        "Outlier detected in outdoor temperature: %.2f°C. Skipping learning.",
                        input_data.outdoor_temp
                    )
                    return False
                # Add valid sample to history for future detection
                self._outlier_detector.add_temperature_sample(input_data.outdoor_temp)
            
            # All data passed outlier detection
            _LOGGER.debug("All sensor data passed outlier detection - learning data is valid")
            return True
            
        except Exception as exc:
            _LOGGER.warning("Error during outlier detection validation: %s", exc)
            # On error, allow learning to continue (fail-safe behavior)
            return True
    
    async def apply_prediction(self, offset: float) -> float:
        """Apply prediction and mark as prediction-sourced adjustment.
        
        Args:
            offset: Temperature offset from prediction
            
        Returns:
            The applied offset value
        """
        self._prediction_active = True
        self._adjustment_source = "prediction"
        _LOGGER.debug("Applied prediction offset: %.2f°C (marked as prediction source)", offset)
        return offset
    
    def set_adjustment_source(self, source: str) -> None:
        """Set the source of the current adjustment.
        
        Args:
            source: Source of adjustment ("prediction", "manual", "external", etc.)
        """
        self._adjustment_source = source
        if source == "prediction":
            self._prediction_active = True
        else:
            self._prediction_active = False
        _LOGGER.debug("Adjustment source set to: %s", source)
    
    def clear_prediction_state(self) -> None:
        """Clear prediction state (called after non-prediction adjustments)."""
        self._prediction_active = False
        self._adjustment_source = None
        _LOGGER.debug("Prediction state cleared")
    
    def register_update_callback(self, callback: Callable) -> Callable:
        """Register a callback to be called when the learning state changes.
        
        Args:
            callback: Function to call when learning state changes
            
        Returns:
            Function to unregister the callback
        """
        self._update_callbacks.append(callback)
        # Return a function to unregister the callback
        return lambda: self._update_callbacks.remove(callback) if callback in self._update_callbacks else None
    
    def _notify_update_callbacks(self) -> None:
        """Notify all registered callbacks of a state change."""
        for callback in self._update_callbacks:
            try:
                callback()
            except Exception as exc:
                _LOGGER.warning("Error in update callback: %s", exc)
    
    def enable_learning(self) -> None:
        """Enable the learning system at runtime."""
        old_state = self._enable_learning
        if not self._enable_learning:
            if not self._learner:
                self._learner = EnhancedLightweightOffsetLearner()
                _LOGGER.info("EnhancedLightweightOffsetLearner initialized at runtime")
            self._enable_learning = True
            _LOGGER.info("Offset learning has been enabled")
            _LOGGER.debug("Learning state changed: %s -> %s", old_state, self._enable_learning)
            self._notify_update_callbacks()
            
            # Trigger save to persist the learning state change
            # Note: This is synchronous but will be handled in an async context
            # by the calling code that manages the enable/disable operations
        else:
            _LOGGER.debug("Learning enable requested but already enabled")
    
    def disable_learning(self) -> None:
        """Disable the learning system at runtime."""
        old_state = self._enable_learning
        if self._enable_learning:
            self._enable_learning = False
            _LOGGER.info("Offset learning has been disabled")
            _LOGGER.debug("Learning state changed: %s -> %s", old_state, self._enable_learning)
            self._notify_update_callbacks()
            
            # Trigger save to persist the learning state change
            # Note: This is synchronous but will be handled in an async context
            # by the calling code that manages the enable/disable operations
        else:
            _LOGGER.debug("Learning disable requested but already disabled")
    
    def reset_learning(self) -> None:
        """Reset all learning data and start fresh."""
        _LOGGER.info("Resetting all learning data for fresh start")
        
        # Create a fresh learner instance with current thresholds
        if self._enable_learning:
            self._learner = EnhancedLightweightOffsetLearner()
            _LOGGER.debug("Learner reset with fresh instance")
        
        # Reset hysteresis learner
        self._hysteresis_learner = HysteresisLearner()
        self._last_power_state = None
        _LOGGER.debug("Hysteresis learner reset with fresh instance")
        
        # Clear calibration phase cache
        self._stable_calibration_offset = None
        _LOGGER.debug("Calibration phase cache cleared")
        
        # Reset prediction tracking state
        self._prediction_active = False
        self._adjustment_source = None
        _LOGGER.debug("Prediction tracking state reset")
        
        # Clear any cached learning info
        if hasattr(self, '_last_learning_info'):
            self._last_learning_info = {}
        
        # Notify callbacks about the reset
        self._notify_update_callbacks()
        
        _LOGGER.info("Learning data reset completed")
    
    def pause_learning(self) -> None:
        """Pause learning updates (state-aware protocol for thermal efficiency)."""
        self._learning_paused = True
        _LOGGER.debug("Learning paused for state-aware thermal management")
    
    def resume_learning(self) -> None:
        """Resume learning updates (state-aware protocol for thermal efficiency)."""
        self._learning_paused = False
        _LOGGER.debug("Learning resumed for state-aware thermal management")
    
    def get_predicted_hysteresis_delta(self, outdoor_temp: Optional[float] = None) -> Optional[float]:
        """Get predicted hysteresis delta with seasonal context when available.
        
        Args:
            outdoor_temp: Outdoor temperature for seasonal context (optional)
            
        Returns:
            Predicted hysteresis delta or None if no prediction available
        """
        # Use seasonal learner if available
        if self._seasonal_features_enabled and self._seasonal_learner:
            try:
                return self._seasonal_learner.get_relevant_hysteresis_delta(outdoor_temp)
            except Exception as exc:
                _LOGGER.warning("Seasonal hysteresis prediction failed: %s", exc)
                # Fall through to traditional method
        
        # Fall back to traditional hysteresis learner
        if self._hysteresis_enabled and self._hysteresis_learner.has_sufficient_data:
            try:
                # Traditional hysteresis learner doesn't use outdoor temp
                start_threshold = self._hysteresis_learner.learned_start_threshold
                stop_threshold = self._hysteresis_learner.learned_stop_threshold
                
                if start_threshold is not None and stop_threshold is not None:
                    return start_threshold - stop_threshold
            except Exception as exc:
                _LOGGER.warning("Traditional hysteresis prediction failed: %s", exc)
        
        # No prediction available
        return None
    
    def calculate_seasonal_offset(self, room_temp: float, ac_temp: float, outdoor_temp: Optional[float]) -> float:
        """Calculate offset using seasonal context for improved accuracy.
        
        Args:
            room_temp: Current room temperature
            ac_temp: Current AC internal temperature
            outdoor_temp: Current outdoor temperature (optional)
            
        Returns:
            Seasonally-adjusted temperature offset
        """
        # Basic offset calculation
        base_offset = ac_temp - room_temp
        
        _LOGGER.debug(
            "Seasonal offset calculation: room_temp=%.1f°C, ac_temp=%.1f°C, outdoor_temp=%s, base_offset=%.2f°C",
            room_temp, ac_temp, f"{outdoor_temp:.1f}°C" if outdoor_temp is not None else "None", base_offset
        )
        
        # Try to enhance with seasonal context
        if self._seasonal_features_enabled and self._seasonal_learner and outdoor_temp is not None:
            try:
                _LOGGER.debug("Seasonal: Attempting to enhance offset with seasonal learning")
                
                # Get seasonal hysteresis prediction
                seasonal_delta = self._seasonal_learner.get_relevant_hysteresis_delta(outdoor_temp)
                
                if seasonal_delta is not None:
                    # Apply seasonal adjustment to the base offset
                    # This is a simplified implementation - more sophisticated logic could be added
                    seasonal_factor = seasonal_delta / 2.5  # Normalize around typical hysteresis delta
                    seasonal_adjustment = base_offset * (0.8 + 0.4 * seasonal_factor)
                    
                    contribution_pct = self._seasonal_learner.get_seasonal_contribution()
                    
                    _LOGGER.debug(
                        "Seasonal offset enhancement: base=%.2f°C, seasonal_delta=%.2f°C, "
                        "seasonal_factor=%.2f, adjusted=%.2f°C",
                        base_offset, seasonal_delta, seasonal_factor, seasonal_adjustment
                    )
                    
                    _LOGGER.info(
                        "Seasonal: Applying hysteresis delta %.1f°C to offset calculation (contribution: %.0f%%)",
                        seasonal_delta, contribution_pct
                    )
                    
                    return seasonal_adjustment
                else:
                    _LOGGER.debug("Seasonal: No relevant hysteresis delta available for outdoor temp %.1f°C", outdoor_temp)
            except Exception as exc:
                _LOGGER.warning("Seasonal offset calculation failed: %s", exc)
        elif self._seasonal_features_enabled and not self._seasonal_learner:
            _LOGGER.debug("Seasonal: Features enabled but no seasonal learner available")
        elif not self._seasonal_features_enabled:
            _LOGGER.debug("Seasonal: Features disabled in configuration")
        else:
            _LOGGER.debug("Seasonal: No outdoor temperature available for seasonal enhancement")
        
        # Fall back to basic calculation
        _LOGGER.debug("Seasonal: Using basic offset calculation: %.2f°C", base_offset)
        return base_offset
    
    def calculate_offset(self, input_data: OffsetInput, thermal_window: Optional[Tuple[float, float]] = None) -> OffsetResult:
        """Calculate temperature offset based on current conditions.
        
        Args:
            input_data: OffsetInput containing all sensor data and context
            thermal_window: Optional thermal window (lower, upper) for unclamped offset
            
        Returns:
            OffsetResult with calculated offset and metadata
        """
        # Enrich features if feature_engineer available
        if self._feature_engineer:
            input_data = self._feature_engineer.enrich_features(input_data)
        
        # Store the input data for confidence calculation
        self._last_input_data = input_data
        
        # Check for unavailable critical sensors
        if input_data.ac_internal_temp is None or input_data.room_temp is None:
            _LOGGER.debug(
                "Critical sensor unavailable: ac_temp=%s, room_temp=%s. Using safe fallback.",
                input_data.ac_internal_temp, input_data.room_temp
            )
            # Store the fallback offset
            self._last_offset = 0.0
            return OffsetResult(
                offset=0.0,
                clamped=False,
                reason="Critical sensor unavailable - using safe fallback",
                confidence=0.0
            )
        
        try:
            # Calculate basic rule-based offset from temperature difference
            # When room_temp > ac_internal_temp: AC thinks it's cooler than reality, needs negative offset to cool more
            # When room_temp < ac_internal_temp: AC thinks it's warmer than reality, needs positive offset to cool less
            
            # Use seasonal offset calculation if available, otherwise basic calculation
            if self._seasonal_features_enabled:
                _LOGGER.debug("Using seasonal-enhanced offset calculation")
                base_offset = self.calculate_seasonal_offset(
                    input_data.room_temp, 
                    input_data.ac_internal_temp, 
                    input_data.outdoor_temp
                )
            else:
                base_offset = input_data.ac_internal_temp - input_data.room_temp
                _LOGGER.debug("Using basic offset calculation: %.2f°C", base_offset)
            
            # Apply mode-specific adjustments
            mode_adjusted_offset = self._apply_mode_adjustments(base_offset, input_data)
            
            # Apply contextual adjustments
            rule_based_offset = self._apply_contextual_adjustments(
                mode_adjusted_offset, input_data
            )
            
            # Always run power transition detection
            self._detect_power_transitions(input_data)
            
            # Check if in calibration phase
            if self.is_in_calibration_phase:
                samples_collected = 0
                if self._learner:
                    try:
                        stats = self._learner.get_statistics()
                        samples_collected = stats.samples_collected
                    except Exception:
                        pass
                
                # Determine if AC is in stable state (idle and temps converged)
                # Note: At this point we've already verified temps are not None
                if input_data.power_consumption is not None:
                    # Power sensor available - use both power and temperature
                    is_stable_state = (
                        input_data.power_consumption < self._power_idle_threshold and
                        abs(input_data.ac_internal_temp - input_data.room_temp) < 2.0
                    )
                else:
                    # No power sensor - use temperature convergence only
                    is_stable_state = abs(input_data.ac_internal_temp - input_data.room_temp) < 2.0
                
                if is_stable_state:
                    # Calculate and cache the stable offset
                    self._stable_calibration_offset = input_data.ac_internal_temp - input_data.room_temp
                    final_offset, was_clamped = self._clamp_offset(self._stable_calibration_offset)
                    self._stable_calibration_offset = final_offset  # Store clamped value
                    
                    reason = (
                        f"Calibration (Stable): Updated offset to {final_offset:.1f}°C. "
                        f"({samples_collected}/{MIN_SAMPLES_FOR_ACTIVE_CONTROL} samples)"
                    )
                    _LOGGER.info(reason)
                    
                elif self._stable_calibration_offset is not None:
                    # AC is cooling - use cached stable offset
                    final_offset = self._stable_calibration_offset
                    reason = f"Calibration (Active): Using cached stable offset of {final_offset:.1f}°C."
                    _LOGGER.debug(reason)
                    
                else:
                    # First run with AC already cooling - temporary offset
                    final_offset = input_data.ac_internal_temp - input_data.room_temp
                    final_offset, was_clamped = self._clamp_offset(final_offset)
                    reason = f"Calibration (Initial): No cached offset. Using temporary offset of {final_offset:.1f}°C."
                    _LOGGER.info(reason)
                
                # Store the last offset for dashboard data
                self._last_offset = final_offset
                
                return OffsetResult(
                    offset=final_offset,
                    clamped=False,
                    reason=reason,
                    confidence=0.2  # Low confidence during calibration
                )
            
            # Get hysteresis state for enhanced learning
            if not self._hysteresis_enabled:
                # No power sensor configured
                hysteresis_state = "no_power_sensor"
            elif not self._hysteresis_learner.has_sufficient_data:
                # Power sensor configured but still learning
                hysteresis_state = "learning_hysteresis"
            else:
                # Power sensor configured with sufficient data
                try:
                    current_power_state = self._get_power_state(input_data.power_consumption or 0)
                    hysteresis_state = self._hysteresis_learner.get_hysteresis_state(
                        current_power_state, input_data.room_temp
                    )
                except Exception:
                    hysteresis_state = "learning_hysteresis"  # Graceful fallback
            
            # Try to use learning if enabled and sufficient data available
            final_offset = rule_based_offset
            learning_confidence = 0.0
            learning_used = False
            
            learning_error = None
            if self._enable_learning and self._learner and self._learner._enhanced_samples:
                try:
                    sample_count = len(self._learner._enhanced_samples)
                    _LOGGER.debug(
                        "Attempting learning prediction for offset calculation (%d samples available)",
                        sample_count
                    )
                    # Use enhanced predict method with hysteresis context and humidity data
                    learned_offset = self._learner.predict(
                        ac_temp=input_data.ac_internal_temp,
                        room_temp=input_data.room_temp,
                        outdoor_temp=input_data.outdoor_temp,
                        mode=input_data.mode,
                        power=input_data.power_consumption,
                        hysteresis_state=hysteresis_state,
                        indoor_humidity=input_data.indoor_humidity,
                        outdoor_humidity=input_data.outdoor_humidity
                    )
                    learning_confidence = 0.8  # High confidence for hysteresis-aware prediction
                    
                    # Calculate humidity contribution if humidity data is present
                    self._calculate_humidity_contribution(input_data, hysteresis_state)
                    
                    _LOGGER.debug(
                        "Learning prediction: rule_based=%.2f°C, learned=%.2f°C, confidence=%.1f",
                        rule_based_offset, learned_offset, learning_confidence
                    )
                    
                    if learning_confidence > 0.1:  # Only use if we have some confidence
                        # Weighted combination based on learning confidence
                        final_offset = (1 - learning_confidence) * rule_based_offset + learning_confidence * learned_offset
                        learning_used = True
                        _LOGGER.debug(
                            "Using learning-enhanced offset: %.2f°C (weight: %.1f, %d%% learning / %d%% rule-based)", 
                            final_offset, learning_confidence, 
                            int(learning_confidence * 100), int((1 - learning_confidence) * 100)
                        )
                    else:
                        _LOGGER.debug("Learning confidence too low (%.1f), using rule-based only", learning_confidence)
                        
                except Exception as exc:
                    _LOGGER.warning("Learning prediction failed, using rule-based fallback: %s", exc)
                    learning_error = str(exc)
            elif self._enable_learning and self._learner:
                _LOGGER.debug("Learning enabled but insufficient data for prediction (need >0 samples)")
            elif self._enable_learning:
                _LOGGER.debug("Learning enabled but no learner instance available")
            
            # Clamp to maximum limit
            clamped_offset, was_clamped = self._clamp_offset(final_offset)
            
            # Generate reason and confidence
            reason = self._generate_reason_with_learning(
                input_data, 
                clamped_offset, 
                was_clamped, 
                learning_used, 
                learning_confidence,
                learning_error
            )
            confidence = self._calculate_confidence_with_learning(
                input_data, 
                learning_used, 
                learning_confidence
            )
            
            _LOGGER.debug(
                "Offset calculation complete: final_offset=%.2f°C, clamped=%s, learning_used=%s, confidence=%.2f",
                clamped_offset, was_clamped, learning_used, confidence
            )
            _LOGGER.debug("Offset calculation reason: %s", reason)
            
            # Log summary of all contributing factors
            factors = []
            if self._seasonal_features_enabled and self._seasonal_learner and input_data.outdoor_temp is not None:
                contribution = self._seasonal_learner.get_seasonal_contribution()
                factors.append(f"seasonal({contribution:.0f}%)")
            if self._weather_forecast_enabled and self._forecast_engine:
                try:
                    forecast_offset = self._forecast_engine.predictive_offset
                    if abs(forecast_offset) > 0.01:
                        factors.append(f"forecast({forecast_offset:+.1f}°C)")
                except Exception:
                    pass
            if learning_used:
                factors.append(f"learning({learning_confidence:.1f})")
            
            # Add humidity contribution if present
            humidity_contributing = any([
                input_data.indoor_humidity is not None and input_data.indoor_humidity != 0,
                input_data.outdoor_humidity is not None and input_data.outdoor_humidity != 0,
                input_data.humidity_differential is not None and input_data.humidity_differential != 0
            ])
            if humidity_contributing:
                factors.append("humidity")
            
            if factors:
                _LOGGER.debug("Contributing factors: %s", ", ".join(factors))
            else:
                _LOGGER.debug("Contributing factors: rule-based only")
            
            # Store the last calculated offset for dashboard data
            self._last_offset = clamped_offset
            
            return OffsetResult(
                offset=clamped_offset,
                clamped=was_clamped,
                reason=reason,
                confidence=confidence
            )
            
        except Exception as exc:
            _LOGGER.error("Error calculating offset: %s", exc)
            # Store the fallback offset
            self._last_offset = 0.0
            # Return safe fallback
            return OffsetResult(
                offset=0.0,
                clamped=False,
                reason="Error in calculation, using safe fallback",
                confidence=0.0
            )
    
    def _apply_mode_adjustments(self, base_offset: float, input_data: OffsetInput) -> float:
        """Apply mode-specific adjustments to the base offset."""
        if input_data.mode == "away":
            # In away mode, we might want less aggressive offset
            return base_offset * 0.5
        elif input_data.mode == "sleep":
            # In sleep mode, slightly less aggressive for comfort
            return base_offset * 0.8
        elif input_data.mode == "boost":
            # In boost mode, more aggressive offset for faster response
            return base_offset * 1.2
        else:
            # Normal mode, no adjustment
            return base_offset
    
    def _apply_contextual_adjustments(self, offset: float, input_data: OffsetInput) -> float:
        """Apply contextual adjustments based on outdoor temp, power, etc."""
        adjusted_offset = offset
        
        # Consider outdoor temperature
        if input_data.outdoor_temp is not None:
            outdoor_diff = input_data.outdoor_temp - input_data.room_temp
            if outdoor_diff > 10:  # Very hot outside
                # Might need more aggressive cooling
                adjusted_offset *= 1.1
            elif outdoor_diff < -10:  # Very cold outside
                # Might need less aggressive heating
                adjusted_offset *= 0.9
        
        # Consider power consumption
        if input_data.power_consumption is not None:
            power_state = self._get_power_state(input_data.power_consumption)
            if power_state == "high":  # High power usage
                # AC is working hard, might need less offset
                adjusted_offset *= 0.9
            elif power_state == "low" or power_state == "idle":  # Low power usage
                # AC is not working much, might need more offset
                adjusted_offset *= 1.1
        
        return adjusted_offset
    
    def _clamp_offset(self, offset: float) -> tuple[float, bool]:
        """Clamp offset to maximum limits."""
        if abs(offset) <= self._max_offset:
            return offset, False
        
        # Clamp to maximum
        clamped_offset = max(-self._max_offset, min(self._max_offset, offset))
        return clamped_offset, True
    
    def _detect_power_transitions(self, input_data: OffsetInput) -> None:
        """Detect power state transitions and record them in hysteresis learner."""
        # Early return if hysteresis is disabled
        if not self._hysteresis_enabled:
            return
        
        # Early return if no power data available
        if input_data.power_consumption is None:
            return
        
        try:
            current_power_state = self._get_power_state(input_data.power_consumption)
            
            # Check for transitions if we have a previous state
            if self._last_power_state is not None and self._last_power_state != current_power_state:
                # Detect AC starting: any transition from idle to a higher power state
                if (self._last_power_state == "idle" and 
                    current_power_state in ("low", "moderate", "high")):
                    self._hysteresis_learner.record_transition('start', input_data.room_temp)
                    _LOGGER.debug(
                        "Hysteresis transition detected: %s -> %s (start at %.1f°C)",
                        self._last_power_state, current_power_state, input_data.room_temp
                    )
                
                # Detect AC stopping: any transition to idle from a higher power state
                elif (self._last_power_state in ("low", "moderate", "high") and 
                      current_power_state == "idle"):
                    self._hysteresis_learner.record_transition('stop', input_data.room_temp)
                    _LOGGER.debug(
                        "Hysteresis transition detected: %s -> %s (stop at %.1f°C)",
                        self._last_power_state, current_power_state, input_data.room_temp
                    )
            
            # Update the last power state
            self._last_power_state = current_power_state
            
        except Exception as exc:
            _LOGGER.warning("Error in hysteresis transition detection: %s", exc)
    
    def _generate_reason(self, input_data: OffsetInput, offset: float, clamped: bool) -> str:
        """Generate human-readable reason for the offset."""
        if offset == 0.0:
            return "No offset needed - AC and room temperatures match"
        
        reasons = []
        
        # Main temperature difference reason
        # Positive offset = cool less, negative offset = cool more
        if input_data.ac_internal_temp > input_data.room_temp:
            reasons.append("AC sensor warmer than room")
        elif input_data.ac_internal_temp < input_data.room_temp:
            reasons.append("AC sensor cooler than room")
        
        # Mode-specific reasons
        if input_data.mode == "away":
            reasons.append("away mode adjustment")
        elif input_data.mode == "sleep":
            reasons.append("sleep mode adjustment")
        elif input_data.mode == "boost":
            reasons.append("boost mode adjustment")
        
        # Contextual reasons
        if input_data.outdoor_temp is not None:
            outdoor_diff = input_data.outdoor_temp - input_data.room_temp
            if outdoor_diff > 10:
                reasons.append("hot outdoor conditions")
            elif outdoor_diff < -10:
                reasons.append("cold outdoor conditions")
        else:
            # Add explicit mention when outdoor temperature is unavailable
            reasons.append("outdoor temperature unavailable")
        
        if input_data.power_consumption is not None:
            power_state = self._get_power_state(input_data.power_consumption)
            if power_state == "high":
                reasons.append("high power usage")
            elif power_state == "low":
                reasons.append("low power usage")
            elif power_state == "idle":
                reasons.append("AC idle/off")
        else:
            # Add explicit mention when power consumption is unavailable
            reasons.append("power consumption unavailable")
        
        # Clamping reason
        if clamped:
            reasons.append(f"clamped to limit (±{self._max_offset}°C)")
        
        return ", ".join(reasons) if reasons else "Basic offset calculation"
    
    def _calculate_confidence(self, input_data: OffsetInput) -> float:
        """Calculate confidence level in the offset calculation."""
        confidence = 0.5  # Base confidence
        
        # More data points increase confidence
        if input_data.outdoor_temp is not None:
            confidence += 0.2
        if input_data.power_consumption is not None:
            confidence += 0.2
        
        # Mode-specific confidence adjustments
        if input_data.mode in ["away", "sleep", "boost"]:
            confidence += 0.1
        
        # Ensure confidence is within bounds
        return min(1.0, max(0.0, confidence))
    
    def update_ml_model(self, model_path: str) -> None:
        """Update the ML model used for predictions.
        
        Supports both old format (direct model object) and new format (model package).
        Model package format: {'model': ..., 'features': [...], 'version': '...'}
        
        Args:
            model_path: Path to the ML model file
        """
        _LOGGER.info("ML model update requested for path: %s", model_path)
        
        if not self._ml_enabled:
            _LOGGER.warning("ML is disabled, ignoring model update")
            return
        
        # TODO: Implement ML model loading when ML features are added
        # For now, this is a placeholder that supports both formats
        _LOGGER.debug("ML model update is not yet implemented")
        self._ml_model = None
    
    def _prepare_feature_vector(self, data: OffsetInput) -> List[float]:
        """Prepare feature vector from OffsetInput for ML model.
        
        Args:
            data: OffsetInput containing all sensor data and context
            
        Returns:
            List of float values with None converted to numpy.nan
        """
        # Convert OffsetInput to dictionary
        feature_dict = {
            'ac_internal_temp': data.ac_internal_temp,
            'room_temp': data.room_temp,
            'outdoor_temp': data.outdoor_temp,
            'power_consumption': data.power_consumption,
            'day_of_week': float(data.day_of_week),
            'time_of_day': data.time_of_day.hour + data.time_of_day.minute / 60.0,
            'indoor_humidity': data.indoor_humidity,
            'outdoor_humidity': data.outdoor_humidity,
            'humidity_differential': data.humidity_differential,
            'indoor_dew_point': data.indoor_dew_point,
            'outdoor_dew_point': data.outdoor_dew_point,
            'heat_index': data.heat_index,
        }
        
        # If we have a model package with features list, align with it
        if isinstance(self._ml_model, dict) and 'features' in self._ml_model:
            model_features = self._ml_model['features']
            feature_vector = []
            for feature_name in model_features:
                value = feature_dict.get(feature_name)
                # Convert None to numpy.nan
                if value is None:
                    feature_vector.append(np.nan)
                else:
                    feature_vector.append(float(value))
        else:
            # Use all features, convert None to numpy.nan
            feature_vector = []
            for value in feature_dict.values():
                if value is None:
                    feature_vector.append(np.nan)
                else:
                    feature_vector.append(float(value))
        
        # Log if humidity features are present in the feature vector
        humidity_indices = [6, 7, 8, 9, 10, 11]  # Indices for humidity features: indoor, outdoor, diff, dew_in, dew_out, heat_index
        humidity_values = [feature_vector[i] for i in humidity_indices if i < len(feature_vector)]
        if humidity_values and any(not np.isnan(v) and v != 0 for v in humidity_values):
            _LOGGER.debug(
                "ML feature vector includes humidity data: [indoor=%.1f, outdoor=%.1f, diff=%.1f, dew_in=%.1f, dew_out=%.1f, heat=%.1f]",
                *[v if not np.isnan(v) else 0.0 for v in humidity_values]
            )
        
        return feature_vector
    
    def record_feedback(
        self,
        predicted_offset: float,
        actual_offset: float,
        input_data: OffsetInput,
        outcome_quality: float = 0.8
    ) -> None:
        """Record feedback for learning (alias for record_actual_performance).
        
        Args:
            predicted_offset: The offset that was predicted/used
            actual_offset: The offset that actually worked best
            input_data: The input conditions for this sample
            outcome_quality: Quality metric (ignored, for compatibility)
        """
        self.record_actual_performance(predicted_offset, actual_offset, input_data)
    
    def record_actual_performance(
        self,
        predicted_offset: float,
        actual_offset: float,
        input_data: OffsetInput,
        learning_target_temp: Optional[float] = None
    ) -> None:
        """Record actual performance for learning feedback.
        
        Args:
            predicted_offset: The offset that was predicted/used
            actual_offset: The offset that actually worked best
            input_data: The input conditions for this sample
            learning_target_temp: Optional target temperature for state-aware learning
        """
        if not self._enable_learning or not self._learner:
            # Learning disabled, silently ignore
            return
        
        # Check if learning is paused (state-aware protocol)
        if self._learning_paused:
            _LOGGER.debug(
                "Learning paused - skipping sample recording "
                "(predicted=%.2f°C, actual=%.2f°C)",
                predicted_offset, actual_offset
            )
            return
        
        # CRITICAL: Prevent ML feedback loop by checking adjustment source
        if getattr(self, '_adjustment_source', None) == "prediction":
            _LOGGER.debug(
                "Skipping feedback recording from prediction to prevent feedback loop "
                "(predicted=%.2f°C, actual=%.2f°C, source=%s)",
                predicted_offset, actual_offset, getattr(self, '_adjustment_source', 'unknown')
            )
            return
        
        # Skip recording if critical sensors are unavailable
        if input_data.ac_internal_temp is None or input_data.room_temp is None:
            _LOGGER.debug(
                "Skipping learning sample due to unavailable sensors: ac_temp=%s, room_temp=%s",
                input_data.ac_internal_temp, input_data.room_temp
            )
            return
        
        # Skip recording if HVAC mode is not suitable for learning (only collect data when AC is actively heating/cooling)
        if hasattr(input_data, 'hvac_mode') and input_data.hvac_mode is not None:
            from .const import LEARNING_HVAC_MODES
            if input_data.hvac_mode not in LEARNING_HVAC_MODES:
                _LOGGER.debug(
                    "Skipping learning sample in %s mode (predicted=%.2f°C, actual=%.2f°C)",
                    input_data.hvac_mode, predicted_offset, actual_offset
                )
                return
        
        # Validate feedback data before training to prevent data poisoning
        current_timestamp = time.time()
        if not self._validate_feedback(actual_offset, input_data.room_temp, current_timestamp):
            _LOGGER.warning("Rejecting invalid feedback data for security: offset=%s, room_temp=%s", 
                          actual_offset, input_data.room_temp)
            return
        
        # Validate learning data for outliers to protect ML model
        if not self._validate_learning_data(input_data):
            _LOGGER.info(
                "Outlier detected in learning data - skipping ML model update to prevent corruption "
                "(predicted=%.2f°C, actual=%.2f°C, room_temp=%.2f°C, ac_temp=%.2f°C)",
                predicted_offset, actual_offset, 
                input_data.room_temp or 0.0, input_data.ac_internal_temp or 0.0
            )
            return
        
        # Sanitize humidity values to handle non-numeric sensor states gracefully
        sanitized_indoor_humidity = self._sanitize_float(input_data.indoor_humidity, "indoor_humidity")
        sanitized_outdoor_humidity = self._sanitize_float(input_data.outdoor_humidity, "outdoor_humidity")
        
        # Also sanitize other optional numeric values for robustness
        sanitized_outdoor_temp = self._sanitize_float(input_data.outdoor_temp, "outdoor_temp")
        sanitized_power = self._sanitize_float(input_data.power_consumption, "power_consumption")
        
        try:
            # Get hysteresis state for enhanced learning
            if not self._hysteresis_enabled:
                # No power sensor configured
                hysteresis_state = "no_power_sensor"
            elif not self._hysteresis_learner.has_sufficient_data:
                # Power sensor configured but still learning
                hysteresis_state = "learning_hysteresis"
            else:
                # Power sensor configured with sufficient data
                try:
                    current_power_state = self._get_power_state(sanitized_power or 0)
                    hysteresis_state = self._hysteresis_learner.get_hysteresis_state(
                        current_power_state, input_data.room_temp
                    )
                except Exception:
                    hysteresis_state = "learning_hysteresis"  # Graceful fallback
            
            # Create validated OffsetInput for outlier detection with sanitized values
            validated_input = OffsetInput(
                ac_internal_temp=input_data.ac_internal_temp,
                room_temp=input_data.room_temp,
                outdoor_temp=sanitized_outdoor_temp,
                mode=input_data.mode,
                power_consumption=sanitized_power,
                time_of_day=input_data.time_of_day,
                day_of_week=input_data.day_of_week,
                hvac_mode=getattr(input_data, 'hvac_mode', None),
                indoor_humidity=sanitized_indoor_humidity,
                outdoor_humidity=sanitized_outdoor_humidity
            )
            
            # Record sample with hysteresis context and sanitized humidity data
            self._learner.add_sample(
                predicted=predicted_offset,
                actual=actual_offset,
                ac_temp=input_data.ac_internal_temp,
                room_temp=input_data.room_temp,
                outdoor_temp=sanitized_outdoor_temp,
                mode=input_data.mode,
                power=sanitized_power,
                hysteresis_state=hysteresis_state,
                indoor_humidity=sanitized_indoor_humidity,
                outdoor_humidity=sanitized_outdoor_humidity
            )
            _LOGGER.debug(
                "Recorded enhanced learning sample: predicted=%.2f, actual=%.2f, hysteresis_state=%s, source=%s, "
                "indoor_humidity=%s, outdoor_humidity=%s",
                predicted_offset, actual_offset, hysteresis_state, getattr(self, '_adjustment_source', 'unknown'),
                sanitized_indoor_humidity, sanitized_outdoor_humidity
            )
        except Exception as exc:
            _LOGGER.error(
                "Failed to record learning sample: %s - Input data types: ac_temp=%s(%s), room_temp=%s(%s), "
                "outdoor_temp=%s(%s), indoor_humidity=%s(%s), outdoor_humidity=%s(%s), power=%s(%s)",
                exc,
                input_data.ac_internal_temp, type(input_data.ac_internal_temp).__name__,
                input_data.room_temp, type(input_data.room_temp).__name__,
                input_data.outdoor_temp, type(input_data.outdoor_temp).__name__,
                input_data.indoor_humidity, type(input_data.indoor_humidity).__name__,
                input_data.outdoor_humidity, type(input_data.outdoor_humidity).__name__,
                input_data.power_consumption, type(input_data.power_consumption).__name__,
                exc_info=True
            )
    
    def _calculate_enhanced_confidence(self, stats: "LearningStats") -> float:
        """Calculate enhanced confidence score based on multiple factors.
        
        Args:
            stats: Learning statistics from the learner
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Start with the learner's accuracy as the base
        # This reflects actual prediction performance
        base_confidence = stats.avg_accuracy
        
        # Factor 1: Sample count maturity
        # Confidence increases with more samples, plateauing at 100
        sample_factor = min(1.0, stats.samples_collected / 100.0)
        
        # Factor 2: Calibration phase penalty
        # Lower confidence during initial calibration
        calibration_factor = 1.0
        if self.is_in_calibration_phase:
            calibration_factor = 0.5  # 50% reduction during calibration
            _LOGGER.debug("In calibration phase, reducing confidence by 50%")
        
        # Factor 3: Hysteresis readiness (if applicable)
        hysteresis_factor = 1.0
        if self._hysteresis_enabled and hasattr(self, '_hysteresis_learner'):
            if self._hysteresis_learner.has_sufficient_data:
                hysteresis_factor = 1.1  # 10% boost when hysteresis is ready
            else:
                hysteresis_factor = 0.9  # 10% penalty when still learning
        
        # Factor 4: Sensor availability
        # Full sensor complement increases confidence
        sensor_factor = 1.0
        sensor_count = 2  # Base: AC temp + room temp (always present)
        
        # Check for optional sensors through recent input data
        if hasattr(self, '_last_input_data'):
            if self._last_input_data.outdoor_temp is not None:
                sensor_count += 1
            if self._last_input_data.power_consumption is not None:
                sensor_count += 1
        
        # 2 sensors = 0.8, 3 sensors = 0.9, 4 sensors = 1.0
        sensor_factor = 0.7 + (sensor_count - 2) * 0.1
        
        # Combine all factors with weights
        # Learning accuracy is the primary factor (40%)
        # Sample maturity is important (30%)
        # Other factors provide adjustments (30% combined)
        combined_confidence = (
            0.4 * base_confidence +
            0.3 * sample_factor +
            0.1 * calibration_factor +
            0.1 * hysteresis_factor +
            0.1 * sensor_factor
        )
        
        # Apply bounds and log the calculation
        final_confidence = max(0.0, min(1.0, combined_confidence))
        
        _LOGGER.debug(
            "Confidence calculation: base=%.2f, samples=%.2f, calibration=%.2f, "
            "hysteresis=%.2f, sensors=%.2f → final=%.2f",
            base_confidence, sample_factor, calibration_factor,
            hysteresis_factor, sensor_factor, final_confidence
        )
        
        return final_confidence
    
    def get_learning_info(self) -> Dict:
        """Get learning information and statistics.
        
        Returns:
            Dictionary containing learning status and statistics
        """
        # Build base learning info first
        base_info = {}
        
        if not self._enable_learning or not self._learner:
            base_info = {
                "enabled": False,
                "samples": 0,
                "accuracy": 0.0,
                "confidence": 0.0,
                "has_sufficient_data": False,
                "last_sample_time": None
            }
        else:
            try:
                stats = self._learner.get_statistics()
                
                # Calculate enhanced confidence based on multiple factors
                confidence = self._calculate_enhanced_confidence(stats)
                
                # Handle LearningStats dataclass from LightweightOffsetLearner
                base_info = {
                    "enabled": True,
                    "samples": stats.samples_collected,
                    "accuracy": stats.avg_accuracy,
                    "confidence": confidence,  # Use enhanced confidence calculation
                    "has_sufficient_data": stats.samples_collected >= 10,  # Consider 10+ samples sufficient
                    "last_sample_time": stats.last_sample_time,
                }
            except Exception as exc:
                _LOGGER.warning("Failed to get learning info: %s", exc)
                base_info = {
                    "enabled": True,
                    "samples": 0,
                    "accuracy": 0.0,
                    "confidence": 0.0,
                    "has_sufficient_data": False,
                    "last_sample_time": None,
                    "error": str(exc)
                }
        
        # Add hysteresis information
        try:
            if not self._hysteresis_enabled:
                # No power sensor configured
                base_info.update({
                    "hysteresis_enabled": False,
                    "hysteresis_state": "disabled",
                    "learned_start_threshold": None,
                    "learned_stop_threshold": None,
                    "temperature_window": None,
                    "start_samples_collected": 0,
                    "stop_samples_collected": 0,
                    "hysteresis_ready": False
                })
            else:
                # Power sensor configured - get hysteresis data
                start_samples = len(self._hysteresis_learner._start_temps)
                stop_samples = len(self._hysteresis_learner._stop_temps)
                has_sufficient = self._hysteresis_learner.has_sufficient_data
                
                # Determine hysteresis state
                if has_sufficient:
                    hysteresis_state = "ready"
                else:
                    hysteresis_state = "learning_hysteresis"
                
                # Get learned thresholds (may be None if insufficient data)
                start_threshold = self._hysteresis_learner.learned_start_threshold
                stop_threshold = self._hysteresis_learner.learned_stop_threshold
                
                # Format thresholds to 2 decimal places if they exist
                if start_threshold is not None:
                    start_threshold = round(start_threshold, 2)
                if stop_threshold is not None:
                    stop_threshold = round(stop_threshold, 2)
                
                # Calculate temperature window if both thresholds exist
                temperature_window = None
                if start_threshold is not None and stop_threshold is not None:
                    temperature_window = round(start_threshold - stop_threshold, 2)
                
                base_info.update({
                    "hysteresis_enabled": True,
                    "hysteresis_state": hysteresis_state,
                    "learned_start_threshold": start_threshold,
                    "learned_stop_threshold": stop_threshold,
                    "temperature_window": temperature_window,
                    "start_samples_collected": start_samples,
                    "stop_samples_collected": stop_samples,
                    "hysteresis_ready": has_sufficient
                })
                
        except Exception as exc:
            _LOGGER.warning("Failed to get hysteresis info: %s", exc)
            # Add safe defaults on error
            base_info.update({
                "hysteresis_enabled": self._hysteresis_enabled,
                "hysteresis_state": "error",
                "learned_start_threshold": None,
                "learned_stop_threshold": None,
                "temperature_window": None,
                "start_samples_collected": 0,
                "stop_samples_collected": 0,
                "hysteresis_ready": False,
                "hysteresis_error": str(exc)
            })
            # Also add to main error key if no other error exists
            if "error" not in base_info:
                base_info["error"] = f"Hysteresis: {exc}"
        
        return base_info
    
    def _calculate_humidity_contribution(self, input_data: OffsetInput, hysteresis_state: str) -> None:
        """Calculate the temperature contribution from humidity features.
        
        Makes two predictions: one with humidity data and one without, then calculates
        the difference to determine humidity's contribution to the offset.
        
        Args:
            input_data: Input data with humidity values
            hysteresis_state: Current hysteresis state
        """
        # Reset contribution to 0.0 by default
        self._last_humidity_contribution = 0.0
        
        # Only calculate if we have learner and humidity data
        if not (self._learner and self._has_humidity_data(input_data)):
            return
            
        try:
            # Make prediction without humidity data
            input_no_humidity = OffsetInput(
                ac_internal_temp=input_data.ac_internal_temp,
                room_temp=input_data.room_temp,
                outdoor_temp=input_data.outdoor_temp,
                mode=input_data.mode,
                power_consumption=input_data.power_consumption,
                time_of_day=input_data.time_of_day,
                day_of_week=input_data.day_of_week,
                hvac_mode=input_data.hvac_mode,
                # Set humidity values to None
                indoor_humidity=None,
                outdoor_humidity=None,
                humidity_differential=None,
                indoor_dew_point=None,
                outdoor_dew_point=None,
                heat_index=None
            )
            
            # Enrich the no-humidity input if feature_engineer available
            if self._feature_engineer:
                input_no_humidity = self._feature_engineer.enrich_features(input_no_humidity)
            
            # Make prediction without humidity
            offset_without_humidity = self._learner.predict(
                ac_temp=input_no_humidity.ac_internal_temp,
                room_temp=input_no_humidity.room_temp,
                outdoor_temp=input_no_humidity.outdoor_temp,
                mode=input_no_humidity.mode,
                power=input_no_humidity.power_consumption,
                hysteresis_state=hysteresis_state,
                indoor_humidity=None,
                outdoor_humidity=None
            )
            
            # The prediction with humidity was already made in calculate_offset
            # We need to make it again here to get the exact value
            offset_with_humidity = self._learner.predict(
                ac_temp=input_data.ac_internal_temp,
                room_temp=input_data.room_temp,
                outdoor_temp=input_data.outdoor_temp,
                mode=input_data.mode,
                power=input_data.power_consumption,
                hysteresis_state=hysteresis_state,
                indoor_humidity=input_data.indoor_humidity,
                outdoor_humidity=input_data.outdoor_humidity
            )
            
            # Calculate the contribution (difference between predictions)
            self._last_humidity_contribution = offset_with_humidity - offset_without_humidity
            
            _LOGGER.debug(
                "Humidity contribution calculated: with_humidity=%.2f°C, without_humidity=%.2f°C, contribution=%.2f°C",
                offset_with_humidity, offset_without_humidity, self._last_humidity_contribution
            )
            
        except Exception as exc:
            _LOGGER.debug("Error calculating humidity contribution: %s", exc)
            self._last_humidity_contribution = 0.0
    
    def _has_humidity_data(self, input_data: OffsetInput) -> bool:
        """Check if input data has any non-zero humidity values."""
        return any([
            input_data.indoor_humidity is not None and input_data.indoor_humidity != 0,
            input_data.outdoor_humidity is not None and input_data.outdoor_humidity != 0,
            input_data.humidity_differential is not None and input_data.humidity_differential != 0
        ])

    def _generate_reason_with_learning(
        self,
        input_data: OffsetInput,
        offset: float,
        clamped: bool,
        learning_used: bool,
        learning_confidence: float,
        learning_error: Optional[str] = None
    ) -> str:
        """Generate human-readable reason including learning information."""
        if offset == 0.0:
            return "No offset needed - AC and room temperatures match"
        
        reasons = []
        
        # Main temperature difference reason
        # Positive offset = cool less, negative offset = cool more
        if input_data.ac_internal_temp > input_data.room_temp:
            reasons.append("AC sensor warmer than room")
        elif input_data.ac_internal_temp < input_data.room_temp:
            reasons.append("AC sensor cooler than room")
        
        # Seasonal information
        if self._seasonal_features_enabled and input_data.outdoor_temp is not None:
            if self._seasonal_learner:
                contribution = self._seasonal_learner.get_seasonal_contribution()
                pattern_count = self._seasonal_learner.get_pattern_count()
                reasons.append(f"seasonal-enhanced ({pattern_count} patterns, {contribution:.0f}% contribution, outdoor: {input_data.outdoor_temp:.1f}°C)")
            else:
                reasons.append(f"seasonal-configured (outdoor: {input_data.outdoor_temp:.1f}°C, no learner)")
        elif self._seasonal_features_enabled:
            reasons.append("seasonal available but no outdoor temp")
        
        # Weather forecast information
        if self._weather_forecast_enabled and self._forecast_engine:
            try:
                forecast_offset = self._forecast_engine.predictive_offset
                active_strategy = self._forecast_engine.active_strategy_info
                if abs(forecast_offset) > 0.01:
                    strategy_name = active_strategy.get('name', 'unknown') if active_strategy else 'unknown'
                    reasons.append(f"weather-forecast ({strategy_name}: {forecast_offset:+.1f}°C)")
                else:
                    reasons.append("weather-forecast (no active strategy)")
            except Exception:
                reasons.append("weather-forecast (error getting status)")
        elif self._weather_forecast_enabled:
            reasons.append("weather-forecast (configured but no engine)")
        
        # Learning information
        if self._enable_learning and self._learner:
            if learning_error:
                reasons.append("learning error, fallback used")
            elif learning_used:
                reasons.append(f"learning-enhanced (confidence: {learning_confidence:.1f})")
            elif self._learner._enhanced_samples:
                reasons.append("learning available but low confidence")
            else:
                reasons.append("insufficient learning data")
        
        # Humidity information with contribution if significant
        humidity_parts = []
        if input_data.indoor_humidity is not None and input_data.indoor_humidity != 0:
            humidity_parts.append(f"indoor: {input_data.indoor_humidity:.1f}%")
        if input_data.outdoor_humidity is not None and input_data.outdoor_humidity != 0:
            humidity_parts.append(f"outdoor: {input_data.outdoor_humidity:.1f}%")
        if input_data.humidity_differential is not None and input_data.humidity_differential != 0:
            humidity_parts.append(f"diff: {input_data.humidity_differential:.1f}%")
        
        if humidity_parts:
            # Always show contribution in °C for transparency
            contribution_sign = "+" if self._last_humidity_contribution > 0 else ""
            contribution_text = f"humidity-adjusted ({contribution_sign}{self._last_humidity_contribution:.1f}°C from {', '.join(humidity_parts)})"
            reasons.append(contribution_text)
            
            # Add debug logging for humidity contribution visibility
            _LOGGER.debug(
                "Humidity contribution displayed: %s (raw contribution: %.3f°C)", 
                contribution_text, 
                self._last_humidity_contribution
            )
        elif (input_data.indoor_humidity is None and input_data.outdoor_humidity is None):
            # Mention when all humidity data is unavailable
            reasons.append("humidity data unavailable")
        
        # Mode-specific reasons
        if input_data.mode == "away":
            reasons.append("away mode adjustment")
        elif input_data.mode == "sleep":
            reasons.append("sleep mode adjustment")
        elif input_data.mode == "boost":
            reasons.append("boost mode adjustment")
        
        # Power state information
        if input_data.power_consumption is not None:
            power_state = self._get_power_state(input_data.power_consumption)
            if power_state == "high":
                reasons.append("high power usage")
            elif power_state == "low":
                reasons.append("low power usage")
            elif power_state == "idle":
                reasons.append("AC idle/off")
            else:
                reasons.append("moderate power usage")
        else:
            if self._enable_learning:
                reasons.append("power unavailable, temperature-only")
        
        # Contextual reasons
        if input_data.outdoor_temp is not None:
            outdoor_diff = input_data.outdoor_temp - input_data.room_temp
            if outdoor_diff > 10:
                reasons.append("hot outdoor conditions")
            elif outdoor_diff < -10:
                reasons.append("cold outdoor conditions")
        else:
            # Add explicit mention when outdoor temperature is unavailable
            reasons.append("outdoor temperature unavailable")
        
        # Clamping reason
        if clamped:
            reasons.append(f"clamped to limit (±{self._max_offset}°C)")
        
        return ", ".join(reasons) if reasons else "Basic offset calculation"
    
    def _calculate_confidence_with_learning(
        self,
        input_data: OffsetInput,
        learning_used: bool,
        learning_confidence: float
    ) -> float:
        """Calculate confidence level including learning factors."""
        # Start with base confidence from original method
        base_confidence = 0.5
        
        # More data points increase confidence
        if input_data.outdoor_temp is not None:
            base_confidence += 0.2
            # Additional boost if seasonal features are enabled and operational
            if self._seasonal_features_enabled and self._seasonal_learner:
                seasonal_contribution = self._seasonal_learner.get_seasonal_contribution()
                confidence_boost = 0.1 * (seasonal_contribution / 100.0)  # Scale by actual contribution
                base_confidence += confidence_boost
                _LOGGER.debug(
                    "Confidence boost from seasonal data: +%.2f (based on %.1f%% contribution)",
                    confidence_boost, seasonal_contribution
                )
            elif self._seasonal_features_enabled:
                base_confidence += 0.05  # Smaller boost if configured but not operational
                
        if input_data.power_consumption is not None:
            base_confidence += 0.2
            
        # Weather forecast confidence contribution
        if self._weather_forecast_enabled and self._forecast_engine:
            try:
                active_strategy = self._forecast_engine.active_strategy_info
                if active_strategy:
                    base_confidence += 0.15  # Boost for active weather strategy
                    _LOGGER.debug("Confidence boost from active weather strategy: +0.15")
                else:
                    base_confidence += 0.05  # Small boost for available but inactive forecast
            except Exception:
                pass
        
        # Mode-specific confidence adjustments
        if input_data.mode in ["away", "sleep", "boost"]:
            base_confidence += 0.1
        
        # Learning contribution
        if learning_used:
            # Weight learning confidence with base confidence
            final_confidence = 0.6 * base_confidence + 0.4 * learning_confidence
        else:
            final_confidence = base_confidence
        
        # Ensure confidence is within bounds
        return min(1.0, max(0.0, final_confidence))
    
    def set_data_store(self, data_store: "SmartClimateDataStore") -> None:
        """Set the data store for persistence operations.
        
        Args:
            data_store: SmartClimateDataStore instance for this entity
        """
        self._data_store = data_store
        _LOGGER.debug("Data store configured for OffsetEngine")
    
    def set_forecast_engine(self, forecast_engine: Optional["ForecastEngine"]) -> None:
        """Set the forecast engine for weather-based predictions.
        
        Args:
            forecast_engine: ForecastEngine instance or None
        """
        self._forecast_engine = forecast_engine
        _LOGGER.debug("ForecastEngine configured for OffsetEngine: %s", 
                     "enabled" if forecast_engine else "disabled")
    
    async def async_save_learning_data(self) -> None:
        """Save learning data and engine state to persistent storage.

        This method serializes the current engine state (including whether
        learning is enabled) and the learner's data, saving it to disk
        to survive Home Assistant restarts. Learning data is preserved
        even when learning is disabled to prevent data loss.
        """
        if not hasattr(self, "_data_store") or self._data_store is None:
            _LOGGER.warning("No data store configured, cannot save learning data")
            self._failed_save_count += 1
            return

        try:
            # Prepare learner data if learner exists (regardless of enable_learning state)
            learner_data = None
            sample_count = 0
            if self._learner:
                learner_data = self._learner.serialize_for_persistence()
                sample_count = learner_data.get("sample_count", 0)
                _LOGGER.debug("Serializing learner data: %s samples, learning_enabled=%s", sample_count, self._enable_learning)

            # Prepare hysteresis data only if hysteresis is enabled
            hysteresis_data = None
            hysteresis_sample_count = 0
            if self._hysteresis_enabled:
                hysteresis_data = self._hysteresis_learner.serialize_for_persistence()
                hysteresis_sample_count = (
                    len(hysteresis_data.get("start_temps", [])) + 
                    len(hysteresis_data.get("stop_temps", []))
                )
                _LOGGER.debug("Serializing hysteresis data: %s start samples, %s stop samples", 
                            len(hysteresis_data.get("start_temps", [])), 
                            len(hysteresis_data.get("stop_temps", [])))

            # Collect seasonal data if seasonal learner exists
            seasonal_data = None
            if self._seasonal_learner:
                try:
                    seasonal_data = self._seasonal_learner.serialize_for_persistence()
                    pattern_count = seasonal_data.get("pattern_count", 0)
                    _LOGGER.debug("Serializing seasonal data: %d patterns", pattern_count)
                except Exception as exc:
                    # Log error but continue - seasonal failure doesn't block offset data save
                    _LOGGER.debug("Failed to get seasonal data: %s", exc)

            # Collect thermal data if callback is provided
            thermal_data = None
            if self._get_thermal_data_cb:
                try:
                    thermal_data = self._get_thermal_data_cb()
                    if thermal_data:
                        _LOGGER.debug("Retrieved thermal data for persistence")
                    else:
                        _LOGGER.debug("Thermal data callback returned None")
                except Exception as exc:
                    # Log error but continue - thermal failure doesn't block offset data save
                    _LOGGER.debug("Failed to get thermal data: %s", exc)

            # Create a comprehensive state dictionary with v2.1 schema
            persistent_data = {
                "version": "2.1",  # Updated for v2.1 schema with thermal persistence support
                "learning_data": {
                    "engine_state": {
                        "enable_learning": self._enable_learning
                    },
                    "learner_data": learner_data,
                    "hysteresis_data": hysteresis_data if hysteresis_data is not None else None,
                    "seasonal_data": seasonal_data  # NEW: Added seasonal data to v2.1 schema
                },
                "thermal_data": thermal_data
            }

            _LOGGER.debug(
                "Saving learning data: samples=%s, learning_enabled=%s, has_learner_data=%s",
                sample_count, self._enable_learning, learner_data is not None
            )

            # Save to persistent storage
            await self._data_store.async_save_learning_data(persistent_data)
            
            # Update save statistics on success
            self._save_count += 1
            self._last_save_time = datetime.now()
            
            # Invalidate persistence latency cache after successful save
            self.invalidate_cache_key('persistence_latency')
            
            # Log successful save with sample count information
            total_samples = sample_count + hysteresis_sample_count
            if total_samples > 0:
                _LOGGER.info(
                    "Learning data save successful: %s learning samples, %s hysteresis samples (%s total)",
                    sample_count, hysteresis_sample_count, total_samples
                )
            else:
                _LOGGER.info("Learning data save successful: no samples collected yet")
            
            _LOGGER.debug("Learning data and engine state saved successfully")

        except Exception as exc:
            self._failed_save_count += 1
            _LOGGER.warning("Failed to save learning data: %s", exc)
    
    async def async_load_learning_data(self) -> bool:
        """Load engine state and learning data from persistent storage.

        This method loads the previously saved state from disk. It first
        restores the engine's configuration (like enable_learning) and then,
        if applicable, restores the learner's state.

        Returns:
            True if data was loaded and state was restored, False otherwise.
        """
        if not hasattr(self, "_data_store") or self._data_store is None:
            _LOGGER.warning("No data store configured, cannot load learning data")
            return False

        try:
            # Load from persistent storage
            _LOGGER.debug("Loading learning data from persistent storage")
            persistent_data = await self._data_store.async_load_learning_data()

            if persistent_data is None:
                _LOGGER.debug("No saved learning data found, using config defaults.")
                return False

            # Validate that persistent_data is a dictionary
            if not isinstance(persistent_data, dict):
                _LOGGER.warning("Invalid persistent data format: expected dict, got %s", type(persistent_data).__name__)
                return False
            
            _LOGGER.debug("Loaded persistent data with keys: %s", list(persistent_data.keys()))

            # Detect data format version and migrate if necessary
            data_version = persistent_data.get("version")
            
            if data_version == "2.1":
                # Native v2.1 format - extract sections
                _LOGGER.debug("Loading native v2.1 format data")
                learning_data = persistent_data.get("learning_data", {})
                thermal_data = persistent_data.get("thermal_data")
                
                # Extract learning components from v2.1 structure
                engine_state = learning_data.get("engine_state", {})
                learner_data = learning_data.get("learner_data")
                hysteresis_data = learning_data.get("hysteresis_data")
                seasonal_data = learning_data.get("seasonal_data")
                
            else:
                # v1.0 format (no version field) or v2 format - treat as learning data only
                _LOGGER.debug("Migrating from v1.0/v2 format to v2.1 structure")
                learning_data = persistent_data
                thermal_data = None
                
                # Extract learning components from old structure
                engine_state = persistent_data.get("engine_state", {})
                learner_data = persistent_data.get("learner_data")
                hysteresis_data = persistent_data.get("hysteresis_data")
                seasonal_data = None  # v1.0/v2 format doesn't have seasonal data


            # Restore engine state from persistence
            if isinstance(engine_state, dict):
                persisted_learning_enabled = engine_state.get("enable_learning")
                if persisted_learning_enabled is not None:
                    if self._enable_learning != persisted_learning_enabled:
                        _LOGGER.info(
                            "Restoring learning state from persistence: %s (was %s from config)",
                            persisted_learning_enabled, self._enable_learning
                        )
                        self._enable_learning = persisted_learning_enabled
                        # If learning is now enabled, ensure the learner instance exists
                        if self._enable_learning and not self._learner:
                            self._learner = EnhancedLightweightOffsetLearner()
                            _LOGGER.debug("EnhancedLightweightOffsetLearner initialized during data load.")

            # Load learner data if it exists, regardless of enable_learning state
            # This preserves accumulated data even when learning is temporarily disabled
            if learner_data:
                # Ensure learner exists before restoring data
                if not self._learner:
                    self._learner = EnhancedLightweightOffsetLearner()

                success = self._learner.restore_from_persistence(learner_data)
                if success:
                    _LOGGER.info("Learning data loaded successfully (learning currently %s).", 
                                "enabled" if self._enable_learning else "disabled")
                else:
                    _LOGGER.warning("Failed to restore learner state from loaded data.")
            else:
                _LOGGER.debug("No learner data found in persistence.")

            # Load hysteresis data if available and hysteresis is enabled
            if self._hysteresis_enabled and hysteresis_data:
                try:
                    self._hysteresis_learner.restore_from_persistence(hysteresis_data)
                    _LOGGER.info("Hysteresis data loaded successfully.")
                except Exception as exc:
                    _LOGGER.warning("Failed to restore hysteresis data: %s", exc)
            elif self._hysteresis_enabled:
                _LOGGER.debug("Hysteresis is enabled, but no hysteresis data found in persistence.")
            else:
                _LOGGER.debug("Hysteresis is disabled, skipping hysteresis data load.")

            # Load seasonal data if available and seasonal learner exists
            if self._seasonal_learner and seasonal_data:
                try:
                    self._seasonal_learner.restore_from_persistence(seasonal_data)
                    pattern_count = seasonal_data.get("pattern_count", 0)
                    _LOGGER.info("Seasonal data loaded successfully: %d patterns", pattern_count)
                except Exception as exc:
                    _LOGGER.warning("Failed to restore seasonal data: %s", exc)
            elif self._seasonal_learner:
                _LOGGER.debug("Seasonal learner exists, but no seasonal data found in persistence.")
            else:
                _LOGGER.debug("No seasonal learner configured, skipping seasonal data load.")

            # Restore thermal data if callback is provided and thermal data exists
            if self._restore_thermal_data_cb and thermal_data:
                try:
                    self._restore_thermal_data_cb(thermal_data)
                    _LOGGER.debug("Thermal data restored successfully")
                except Exception as exc:
                    # Log error but continue - thermal restore failure doesn't block load
                    _LOGGER.debug("Failed to restore thermal data: %s", exc)
            elif thermal_data:
                _LOGGER.debug("Thermal data found but no restore callback provided")
            else:
                _LOGGER.debug("No thermal data found in persistence")

            self._notify_update_callbacks()  # Notify listeners of the restored state
            return True

        except Exception as exc:
            _LOGGER.error("Failed to load learning data: %s", exc)
            return False
    
    async def async_setup_periodic_save(self, hass: "HomeAssistant", save_interval: Optional[int] = None) -> Callable:
        """Set up periodic saving of learning data.
        
        Args:
            hass: Home Assistant instance
            save_interval: Optional save interval in seconds. If not provided, uses configured interval.
            
        Returns:
            Function to cancel the periodic saving
        """
        from homeassistant.helpers.event import async_track_time_interval
        from datetime import timedelta
        
        if not self._enable_learning:
            _LOGGER.debug("Learning disabled, skipping periodic save setup")
            return lambda: None
        
        # Use provided save_interval or fall back to configured interval
        interval = save_interval if save_interval is not None else self._save_interval
        
        async def _periodic_save(_now=None):
            """Periodic save callback."""
            await self.async_save_learning_data()
        
        # Set up periodic save with configurable interval
        remove_listener = async_track_time_interval(
            hass, _periodic_save, timedelta(seconds=interval)
        )
        
        _LOGGER.info(
            "Periodic learning data save configured (every %s seconds / %s minutes)",
            interval, interval / 60
        )
        return remove_listener
    
    async def _trigger_save_callback(self) -> None:
        """Trigger a save operation (used for testing and state changes)."""
        await self.async_save_learning_data()
    
    def invalidate_cache_key(self, key: str) -> None:
        """Public method to invalidate a specific cache key."""
        if key in self._dashboard_cache:
            del self._dashboard_cache[key]
            _LOGGER.debug("Dashboard cache key '%s' invalidated.", key)
    
    def _get_cached_or_recompute(self, key: str, func: Callable, duration: int, default_value: Any = None) -> Any:
        """
        Cache helper with configurable duration and error handling.
        Duration of 0 means no caching.
        """
        now = time.monotonic()
        cached_item = self._dashboard_cache.get(key)
        
        if cached_item and (now - cached_item['timestamp']) < duration:
            self._cache_hits += 1
            return cached_item['data']
        
        self._cache_misses += 1
        
        try:
            new_data = func()
            if duration > 0:
                self._dashboard_cache[key] = {'data': new_data, 'timestamp': now}
            return new_data
        except Exception as e:
            _LOGGER.warning(
                "Failed to compute dashboard data for key '%s': %s. "
                "Returning stale or default data.", key, e
            )
            # Return last known good value if exists
            if cached_item:
                return cached_item['data']
            # Otherwise return safe default
            return default_value
    
    def _get_seasonal_data(self) -> SeasonalData:
        """Get seasonal learning data with graceful handling."""
        # Check both config AND component existence for operational status
        is_operationally_enabled = self._seasonal_features_enabled and self._seasonal_learner is not None
        
        if not is_operationally_enabled:
            return SeasonalData(enabled=False)
        
        try:
            return SeasonalData(
                enabled=True,
                contribution=self._seasonal_learner.get_seasonal_contribution(),
                pattern_count=self._seasonal_learner.get_pattern_count(),
                outdoor_temp_bucket=self._seasonal_learner.get_outdoor_temp_bucket(),
                accuracy=self._seasonal_learner.get_accuracy()
            )
        except Exception as e:
            _LOGGER.warning("Failed to get seasonal data: %s", e)
            return SeasonalData(enabled=False)
    
    def _get_delay_data(self) -> DelayData:
        """Get delay learning data with graceful handling."""
        if not self._delay_learner:
            return DelayData()
        
        try:
            return DelayData(
                adaptive_delay=self._delay_learner.get_adaptive_delay(),
                temperature_stability_detected=self._delay_learner.is_temperature_stable(),
                learned_delay_seconds=self._delay_learner.get_learned_delay()
            )
        except Exception as e:
            _LOGGER.warning("Failed to get delay data: %s", e)
            return DelayData()
    
    def _get_ac_behavior_data(self) -> ACBehaviorData:
        """Get AC behavior metrics."""
        try:
            return ACBehaviorData(
                temperature_window=self._get_temperature_window(),
                power_correlation_accuracy=self._calculate_power_correlation(),
                hysteresis_cycle_count=self._get_hysteresis_cycle_count()
            )
        except Exception as e:
            _LOGGER.warning("Failed to get AC behavior data: %s", e)
            return ACBehaviorData()
    
    def _compute_performance_data(self) -> PerformanceData:
        """Compute expensive performance metrics."""
        return PerformanceData(
            ema_coefficient=self._get_ema_coefficient(),
            prediction_latency_ms=self._measure_prediction_latency(),
            energy_efficiency_score=self._calculate_energy_efficiency_score(),
            sensor_availability_score=self._calculate_sensor_availability()
        )
    
    def _compute_system_health_data(self) -> SystemHealthData:
        """Compute expensive system health metrics."""
        # Memory usage (cached for 5 minutes)
        mem_usage = self._get_cached_or_recompute(
            'memory_usage', self._calculate_memory_usage_kb, CACHE_DUR_MEMORY, default_value=0.0
        )
        
        # Persistence latency (cached until invalidated by save operation)
        persistence_latency = self._get_cached_or_recompute(
            'persistence_latency', 
            lambda: self._data_store.get_last_write_latency() if hasattr(self, '_data_store') else 0.0,
            CACHE_DUR_PERSISTENCE, 
            default_value=0.0
        )
        
        # Trends (cached for 30 minutes)
        accuracy_rate = self._get_cached_or_recompute(
            'accuracy_rate', self._calculate_accuracy_improvement_rate, CACHE_DUR_TRENDS, default_value=0.0
        )
        
        convergence = self._get_cached_or_recompute(
            'convergence', self._analyze_convergence_trend, CACHE_DUR_TRENDS, default_value="unknown"
        )
        
        return SystemHealthData(
            memory_usage_kb=mem_usage,
            persistence_latency_ms=persistence_latency,
            outlier_detection_active=self._is_outlier_detection_active(),
            samples_per_day=self._calculate_samples_per_day(),
            accuracy_improvement_rate=accuracy_rate,
            convergence_trend=convergence,
            outliers_detected_today=self._get_outliers_detected_today(),
            outlier_detection_threshold=self._get_outlier_detection_threshold(),
            last_outlier_detection_time=self._get_last_outlier_detection_time()
        )
    
    def _compute_diagnostics(self, start_time: float) -> DiagnosticsData:
        """Compute diagnostic metrics."""
        end_time = time.monotonic()
        update_duration_ms = (end_time - start_time) * 1000
        
        total_calls = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_calls) if total_calls > 0 else 0.0
        
        return DiagnosticsData(
            last_update_duration_ms=round(update_duration_ms, 2),
            cache_hit_rate=round(hit_rate, 3),
            cached_keys=len(self._dashboard_cache)
        )
    
    # Helper methods for computing metrics
    def _get_temperature_window(self) -> Optional[str]:
        """Get the temperature window string."""
        if self._hysteresis_enabled and self._hysteresis_learner.has_sufficient_data:
            start = self._hysteresis_learner.learned_start_threshold
            stop = self._hysteresis_learner.learned_stop_threshold
            if start is not None and stop is not None:
                delta = abs(start - stop)
                return f"±{delta/2:.1f}°C"
        return None
    
    def _calculate_power_correlation(self) -> float:
        """Calculate power correlation accuracy."""
        # TODO: Implement actual power correlation calculation
        # For now, return a placeholder based on hysteresis readiness
        if self._hysteresis_enabled and self._hysteresis_learner.has_sufficient_data:
            return 85.0  # Placeholder value
        return 0.0
    
    def _get_hysteresis_cycle_count(self) -> int:
        """Get the number of completed hysteresis cycles."""
        if self._hysteresis_enabled:
            # Use the minimum of start and stop samples as completed cycles
            start_count = len(self._hysteresis_learner._start_temps)
            stop_count = len(self._hysteresis_learner._stop_temps)
            return min(start_count, stop_count)
        return 0
    
    def _get_ema_coefficient(self) -> float:
        """Get the exponential moving average coefficient."""
        # TODO: Get from learner if available
        return 0.2  # Default EMA coefficient
    
    def _measure_prediction_latency(self) -> float:
        """Measure the latency of ML predictions."""
        if not self._enable_learning or not self._learner:
            return 0.0
        
        # TODO: Implement actual latency measurement
        # For now, return a placeholder value
        return 1.0  # ms
    
    def _calculate_energy_efficiency_score(self) -> int:
        """Calculate energy efficiency score (0-100)."""
        # TODO: Implement actual energy efficiency calculation
        # For now, return a placeholder based on learning progress
        if self._enable_learning and self._learner:
            try:
                stats = self._learner.get_statistics()
                # Base score on accuracy and sample count
                base_score = int(stats.avg_accuracy * 50)
                sample_bonus = min(30, stats.samples_collected // 10)
                return base_score + sample_bonus + 20  # +20 base
            except:
                pass
        return 50  # Default middle score
    
    def _calculate_sensor_availability(self) -> float:
        """Calculate sensor availability score."""
        available_sensors = 2  # AC temp + room temp (always available)
        
        if hasattr(self, '_last_input_data') and self._last_input_data:
            if self._last_input_data.outdoor_temp is not None:
                available_sensors += 1
            if self._last_input_data.power_consumption is not None:
                available_sensors += 1
        
        # Maximum 4 sensors total
        return (available_sensors / 4.0) * 100.0
    
    def _calculate_memory_usage_kb(self) -> float:
        """Calculate memory usage of the offset engine."""
        try:
            # Calculate size of major data structures
            size = 0
            
            # Learner samples
            if self._learner and hasattr(self._learner, '_enhanced_samples'):
                size += len(self._learner._enhanced_samples) * 100  # Estimate bytes per sample
            
            # Hysteresis data
            if self._hysteresis_enabled:
                size += len(self._hysteresis_learner._start_temps) * 8
                size += len(self._hysteresis_learner._stop_temps) * 8
            
            # Dashboard cache
            size += sys.getsizeof(self._dashboard_cache)
            
            return size / 1024.0  # Convert to KB
        except:
            return 0.0
    
    def _is_outlier_detection_active(self) -> bool:
        """Check if outlier detection is active."""
        return self._outlier_detector is not None
    
    def has_outlier_detection(self) -> bool:
        """Check if outlier detection is available."""
        return self._outlier_detector is not None
    
    def get_outlier_statistics(self) -> Dict[str, Any]:
        """Get outlier detection statistics."""
        if not self._outlier_detector:
            return {
                "enabled": False,
                "detected_outliers": 0,
                "filtered_samples": 0,
                "outlier_rate": 0.0,
                "temperature_history_size": 0,
                "power_history_size": 0,
                "has_sufficient_data": False
            }
        
        try:
            temp_history_size = self._outlier_detector.get_history_size()
            power_history_size = len(self._outlier_detector._power_history)
            
            # TODO: Track actual outlier counts - for now use placeholder
            # In a real implementation, we'd track these stats as outliers are detected
            total_samples = temp_history_size + power_history_size
            detected_outliers = 0  # Placeholder
            filtered_samples = total_samples - detected_outliers
            outlier_rate = detected_outliers / total_samples if total_samples > 0 else 0.0
            
            return {
                "enabled": True,
                "detected_outliers": detected_outliers,
                "filtered_samples": filtered_samples,
                "outlier_rate": outlier_rate,
                "temperature_history_size": temp_history_size,
                "power_history_size": power_history_size,
                "has_sufficient_data": self._outlier_detector.has_sufficient_data()
            }
        except Exception as exc:
            _LOGGER.warning("Error getting outlier statistics: %s", exc)
            return {
                "enabled": True,
                "error": str(exc),
                "detected_outliers": 0,
                "filtered_samples": 0,
                "outlier_rate": 0.0,
                "temperature_history_size": 0,
                "power_history_size": 0,
                "has_sufficient_data": False
            }
    
    def get_feature_contribution(self, feature_name: str) -> float:
        """Get the temperature contribution of a specific feature in °C.
        
        Args:
            feature_name: Name of the feature ("humidity", etc.)
            
        Returns:
            Temperature contribution in °C. Returns 0.0 for unknown features
            or when no contribution has been calculated.
        """
        if feature_name == "humidity":
            return self._last_humidity_contribution
        else:
            return 0.0
    
    def _get_outliers_detected_today(self) -> int:
        """Get number of outliers detected today.
        
        This method provides outlier count for system health reporting
        as specified in c_architecture.md Section 9.6.
        """
        if not self._outlier_detector:
            return 0
            
        # TODO: Implement daily outlier tracking
        # For now, return placeholder - in full implementation this would
        # track outliers detected since midnight
        try:
            stats = self.get_outlier_statistics()
            return stats.get("detected_outliers", 0)
        except Exception as exc:
            _LOGGER.warning("Error getting outliers detected today: %s", exc)
            return 0
    
    def _get_outlier_detection_threshold(self) -> float:
        """Get current outlier detection threshold.
        
        This method provides threshold value for system health reporting
        as specified in c_architecture.md Section 9.6.
        """
        if not self._outlier_detector:
            return 2.5  # Default threshold
            
        try:
            return self._outlier_detector.zscore_threshold
        except Exception as exc:
            _LOGGER.warning("Error getting outlier detection threshold: %s", exc)
            return 2.5
    
    def _get_last_outlier_detection_time(self) -> Optional[datetime]:
        """Get timestamp of last outlier detection.
        
        This method provides last detection time for system health reporting
        as specified in c_architecture.md Section 9.6.
        """
        if not self._outlier_detector:
            return None
            
        # TODO: Implement last detection time tracking
        # For now, return None - in full implementation this would
        # track the timestamp of the most recent outlier detection
        try:
            stats = self.get_outlier_statistics()
            if stats.get("detected_outliers", 0) > 0:
                # Placeholder: return current time if outliers were detected
                # In real implementation, track actual detection timestamps
                return datetime.now()
            return None
        except Exception as exc:
            _LOGGER.warning("Error getting last outlier detection time: %s", exc)
            return None
    
    def _calculate_samples_per_day(self) -> float:
        """Calculate average samples collected per day."""
        if not self._enable_learning or not self._learner:
            return 0.0
        
        try:
            stats = self._learner.get_statistics()
            if stats.last_sample_time and stats.samples_collected > 0:
                # Estimate based on time since first sample
                # TODO: Track actual first sample time
                # For now, assume steady collection rate
                return 288.0  # Typical: every 5 minutes
        except:
            pass
        return 0.0
    
    def _calculate_accuracy_improvement_rate(self) -> float:
        """Calculate accuracy improvement rate per day."""
        # TODO: Track accuracy history over time
        # For now, return a placeholder
        if self._enable_learning and self._learner:
            try:
                stats = self._learner.get_statistics()
                if stats.samples_collected > 50:
                    return 2.0  # % per day placeholder
            except:
                pass
        return 0.0
    
    def _analyze_convergence_trend(self) -> str:
        """Analyze convergence trend of the learning system."""
        if not self._enable_learning or not self._learner:
            return "not_learning"
        
        try:
            stats = self._learner.get_statistics()
            if stats.samples_collected < 20:
                return "learning"
            elif stats.avg_accuracy > 0.8:
                return "stable"
            elif stats.avg_accuracy > 0.6:
                return "improving"
            else:
                return "unstable"
        except:
            return "unknown"
    
    def _compute_algorithm_metrics(self) -> AlgorithmMetrics:
        """Compute algorithm performance metrics."""
        metrics = AlgorithmMetrics()
        
        if not self._enable_learning or not self._learner:
            return metrics
        
        try:
            # Get basic statistics from learner
            stats = self._learner.get_statistics()
            
            # Correlation coefficient (placeholder based on accuracy)
            # In a real implementation, this would calculate actual correlation
            metrics.correlation_coefficient = (stats.avg_accuracy * 2.0) - 1.0  # Map 0-1 to -1 to 1
            
            # Prediction variance (placeholder)
            # In reality, would calculate variance of predictions
            if stats.samples_collected > 10:
                metrics.prediction_variance = 0.05 * (1.0 - stats.avg_accuracy)
            
            # Model entropy (placeholder)
            # Would represent uncertainty in the model
            metrics.model_entropy = -stats.avg_accuracy * 0.693 if stats.avg_accuracy > 0 else 0
            
            # Learning rate (placeholder)
            # Could be extracted from actual ML model
            metrics.learning_rate = 0.001
            
            # Momentum factor (placeholder)
            # Could be from optimizer settings
            metrics.momentum_factor = 0.9
            
            # Regularization strength (placeholder)
            metrics.regularization_strength = 0.001
            
            # Mean squared error (placeholder based on accuracy)
            # Would be actual MSE from predictions
            metrics.mean_squared_error = (1.0 - stats.avg_accuracy) * 0.1
            
            # Mean absolute error (placeholder)
            # Would be actual MAE from predictions
            metrics.mean_absolute_error = (1.0 - stats.avg_accuracy) * 0.2
            
            # R-squared (placeholder based on accuracy)
            # Would represent model fit quality
            metrics.r_squared = stats.avg_accuracy * 0.9
            
        except Exception as e:
            _LOGGER.warning("Failed to compute algorithm metrics: %s", e)
        
        return metrics
    
    async def async_get_dashboard_data(self) -> Dict[str, Any]:
        """Aggregates all data for the dashboard with performance tracking."""
        start_time = time.monotonic()
        
        # Existing fields (always computed fresh - assumed lightweight)
        calculated_offset = self._last_offset
        learning_info = self.get_learning_info()
        save_diagnostics = {
            "save_count": self._save_count,
            "failed_save_count": self._failed_save_count,
            "last_save_time": self._last_save_time.isoformat() if self._last_save_time else None,
        }
        calibration_info = {
            "in_calibration": self.is_in_calibration_phase,
            "cached_offset": self._stable_calibration_offset,
        }
        
        # Get weather forecast data (based on config AND engine existence)
        weather_forecast = self._weather_forecast_enabled and self._forecast_engine is not None
        predictive_offset = 0.0
        if self._forecast_engine:
            try:
                predictive_offset = self._forecast_engine.predictive_offset
            except Exception as exc:
                _LOGGER.warning("Failed to get predictive offset from ForecastEngine: %s", exc)
                predictive_offset = 0.0
        
        # Create the data object
        data_dto = DashboardData(
            # Backward compatibility fields
            calculated_offset=calculated_offset,
            learning_info=learning_info,
            save_diagnostics=save_diagnostics,
            calibration_info=calibration_info,
            
            # New structured fields
            seasonal_data=self._get_seasonal_data(),
            delay_data=self._get_delay_data(),
            ac_behavior=self._get_ac_behavior_data(),
            
            # Cached expensive calculations
            performance=self._get_cached_or_recompute(
                'performance', self._compute_performance_data, CACHE_DUR_PERF, PerformanceData()
            ),
            system_health=self._get_cached_or_recompute(
                'system_health', self._compute_system_health_data, CACHE_DUR_MEMORY, SystemHealthData()
            ),
            diagnostics=self._compute_diagnostics(start_time),
            
            # Algorithm metrics
            algorithm_metrics=self._get_cached_or_recompute(
                'algorithm_metrics', self._compute_algorithm_metrics, CACHE_DUR_PERF, AlgorithmMetrics()
            )
        )
        
        # Convert to dict and add the new root-level fields
        result = data_dto.to_dict()
        result["weather_forecast"] = weather_forecast
        result["predictive_offset"] = predictive_offset
        
        return result