"""Offset calculation engine for Smart Climate Control."""

import logging
import time
from typing import Optional, Dict, List, Tuple, Callable, TYPE_CHECKING, Literal
import statistics
from datetime import datetime
from collections import deque

from .models import OffsetInput, OffsetResult
from .lightweight_learner import LightweightOffsetLearner as EnhancedLightweightOffsetLearner
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
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from .data_store import SmartClimateDataStore
    from .seasonal_learner import SeasonalHysteresisLearner

_LOGGER = logging.getLogger(__name__)

# Calibration phase threshold - configurable in the future
MIN_SAMPLES_FOR_ACTIVE_CONTROL = 10  # Exit calibration after this many samples

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
    
    def __init__(self, config: dict, seasonal_learner: Optional["SeasonalHysteresisLearner"] = None):
        """Initialize the offset engine with configuration.
        
        Args:
            config: Configuration dictionary
            seasonal_learner: Optional seasonal learner for enhanced predictions
        """
        self._max_offset = config.get("max_offset", 5.0)
        self._ml_enabled = config.get("ml_enabled", True)
        self._ml_model = None  # Loaded when available
        
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
        
        # ML feedback loop prevention - track adjustment sources
        self._prediction_active: bool = False
        self._adjustment_source: Optional[str] = None  # Track if adjustment from prediction vs user
        
        # Seasonal learning integration
        self._seasonal_learner: Optional["SeasonalHysteresisLearner"] = seasonal_learner
        self._seasonal_features_enabled: bool = seasonal_learner is not None
        
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
            "hysteresis_enabled=%s, seasonal_enabled=%s, power_thresholds(idle=%s, min=%s, max=%s), save_interval=%s, "
            "validation_bounds(offset=%s to %s, temp=%s to %s, rate_limit=%ss)",
            self._max_offset,
            self._ml_enabled,
            self._enable_learning,
            self._hysteresis_enabled,
            self._seasonal_features_enabled,
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
        
        # Try to enhance with seasonal context
        if self._seasonal_features_enabled and self._seasonal_learner and outdoor_temp is not None:
            try:
                # Get seasonal hysteresis prediction
                seasonal_delta = self._seasonal_learner.get_relevant_hysteresis_delta(outdoor_temp)
                
                if seasonal_delta is not None:
                    # Apply seasonal adjustment to the base offset
                    # This is a simplified implementation - more sophisticated logic could be added
                    seasonal_factor = seasonal_delta / 2.5  # Normalize around typical hysteresis delta
                    seasonal_adjustment = base_offset * (0.8 + 0.4 * seasonal_factor)
                    
                    _LOGGER.debug(
                        "Seasonal offset calculation: base=%.2f, seasonal_delta=%.2f, "
                        "seasonal_factor=%.2f, adjusted=%.2f",
                        base_offset, seasonal_delta, seasonal_factor, seasonal_adjustment
                    )
                    
                    return seasonal_adjustment
            except Exception as exc:
                _LOGGER.warning("Seasonal offset calculation failed: %s", exc)
        
        # Fall back to basic calculation
        _LOGGER.debug("Using basic offset calculation: %.2f", base_offset)
        return base_offset
    
    def calculate_offset(self, input_data: OffsetInput) -> OffsetResult:
        """Calculate temperature offset based on current conditions.
        
        Args:
            input_data: OffsetInput containing all sensor data and context
            
        Returns:
            OffsetResult with calculated offset and metadata
        """
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
                base_offset = self.calculate_seasonal_offset(
                    input_data.room_temp, 
                    input_data.ac_internal_temp, 
                    input_data.outdoor_temp
                )
            else:
                base_offset = input_data.ac_internal_temp - input_data.room_temp
            
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
                    _LOGGER.debug("Attempting learning prediction for offset calculation")
                    # Use enhanced predict method with hysteresis context
                    learned_offset = self._learner.predict(
                        ac_temp=input_data.ac_internal_temp,
                        room_temp=input_data.room_temp,
                        outdoor_temp=input_data.outdoor_temp,
                        mode=input_data.mode,
                        power=input_data.power_consumption,
                        hysteresis_state=hysteresis_state
                    )
                    learning_confidence = 0.8  # High confidence for hysteresis-aware prediction
                    
                    _LOGGER.debug(
                        "Learning prediction: rule_based=%s, learned=%s, confidence=%s",
                        rule_based_offset, learned_offset, learning_confidence
                    )
                    
                    if learning_confidence > 0.1:  # Only use if we have some confidence
                        # Weighted combination based on learning confidence
                        final_offset = (1 - learning_confidence) * rule_based_offset + learning_confidence * learned_offset
                        learning_used = True
                        _LOGGER.debug("Using learning-enhanced offset: %s (weight: %s)", final_offset, learning_confidence)
                    else:
                        _LOGGER.debug("Learning confidence too low (%s), using rule-based only", learning_confidence)
                        
                except Exception as exc:
                    _LOGGER.warning("Learning prediction failed, using rule-based fallback: %s", exc)
                    learning_error = str(exc)
            elif self._enable_learning and self._learner:
                _LOGGER.debug("Learning enabled but insufficient data for prediction")
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
                "Offset calculation complete: final_offset=%s, clamped=%s, learning_used=%s, confidence=%s",
                clamped_offset, was_clamped, learning_used, confidence
            )
            _LOGGER.debug("Offset calculation reason: %s", reason)
            
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
                # Detect transitions from idle/low to moderate/high (AC starting)
                if (self._last_power_state in ("idle", "low") and 
                    current_power_state in ("moderate", "high")):
                    self._hysteresis_learner.record_transition('start', input_data.room_temp)
                    _LOGGER.debug(
                        "Hysteresis transition detected: %s -> %s (start at %.1f°C)",
                        self._last_power_state, current_power_state, input_data.room_temp
                    )
                
                # Detect transitions from moderate/high to idle/low (AC stopping)
                elif (self._last_power_state in ("moderate", "high") and 
                      current_power_state in ("idle", "low")):
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
        
        if input_data.power_consumption is not None:
            power_state = self._get_power_state(input_data.power_consumption)
            if power_state == "high":
                reasons.append("high power usage")
            elif power_state == "low":
                reasons.append("low power usage")
            elif power_state == "idle":
                reasons.append("AC idle/off")
        
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
        
        Args:
            model_path: Path to the ML model file
        """
        _LOGGER.info("ML model update requested for path: %s", model_path)
        
        if not self._ml_enabled:
            _LOGGER.warning("ML is disabled, ignoring model update")
            return
        
        # TODO: Implement ML model loading when ML features are added
        # For now, this is a placeholder
        _LOGGER.debug("ML model update is not yet implemented")
        self._ml_model = None
    
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
        input_data: OffsetInput
    ) -> None:
        """Record actual performance for learning feedback.
        
        Args:
            predicted_offset: The offset that was predicted/used
            actual_offset: The offset that actually worked best
            input_data: The input conditions for this sample
        """
        if not self._enable_learning or not self._learner:
            # Learning disabled, silently ignore
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
                    current_power_state = self._get_power_state(input_data.power_consumption or 0)
                    hysteresis_state = self._hysteresis_learner.get_hysteresis_state(
                        current_power_state, input_data.room_temp
                    )
                except Exception:
                    hysteresis_state = "learning_hysteresis"  # Graceful fallback
            
            # Record sample with hysteresis context
            self._learner.add_sample(
                predicted=predicted_offset,
                actual=actual_offset,
                ac_temp=input_data.ac_internal_temp,
                room_temp=input_data.room_temp,
                outdoor_temp=input_data.outdoor_temp,
                mode=input_data.mode,
                power=input_data.power_consumption,
                hysteresis_state=hysteresis_state
            )
            _LOGGER.debug(
                "Recorded enhanced learning sample: predicted=%.2f, actual=%.2f, hysteresis_state=%s, source=%s",
                predicted_offset, actual_offset, hysteresis_state, getattr(self, '_adjustment_source', 'unknown')
            )
        except Exception as exc:
            _LOGGER.warning("Failed to record learning sample: %s", exc)
    
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
            reasons.append(f"seasonal-enhanced (outdoor: {input_data.outdoor_temp:.1f}°C)")
        elif self._seasonal_features_enabled:
            reasons.append("seasonal available but no outdoor temp")
        
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
            # Additional boost if seasonal features are enabled
            if self._seasonal_features_enabled:
                base_confidence += 0.1
        if input_data.power_consumption is not None:
            base_confidence += 0.2
        
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

            # Create a comprehensive state dictionary including the engine's state
            persistent_data = {
                "version": 2,  # Updated for v2 schema with hysteresis support
                "engine_state": {
                    "enable_learning": self._enable_learning
                },
                "learner_data": learner_data
            }
            
            # Only include hysteresis_data if hysteresis is enabled
            if hysteresis_data is not None:
                persistent_data["hysteresis_data"] = hysteresis_data

            _LOGGER.debug(
                "Saving learning data: samples=%s, learning_enabled=%s, has_learner_data=%s",
                sample_count, self._enable_learning, learner_data is not None
            )

            # Save to persistent storage
            await self._data_store.async_save_learning_data(persistent_data)
            
            # Update save statistics on success
            self._save_count += 1
            self._last_save_time = datetime.now()
            
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

            # --- KEY FIX: Restore engine state from persistence ---
            engine_state = persistent_data.get("engine_state", {})
            
            # Validate engine_state is a dictionary before accessing
            if isinstance(engine_state, dict):
                persisted_learning_enabled = engine_state.get("enable_learning")
            else:
                _LOGGER.warning("Invalid engine_state format: expected dict, got %s", type(engine_state).__name__)
                persisted_learning_enabled = None

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
            # --- END OF KEY FIX ---

            # Load learner data if it exists, regardless of enable_learning state
            # This preserves accumulated data even when learning is temporarily disabled
            learner_data = persistent_data.get("learner_data")
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

            # Load hysteresis data if available (v2 schema) and hysteresis is enabled
            if self._hysteresis_enabled:
                hysteresis_data = persistent_data.get("hysteresis_data")
                if hysteresis_data:
                    try:
                        self._hysteresis_learner.restore_from_persistence(hysteresis_data)
                        _LOGGER.info("Hysteresis data loaded successfully.")
                    except Exception as exc:
                        _LOGGER.warning("Failed to restore hysteresis data: %s", exc)
                else:
                    _LOGGER.debug("Hysteresis is enabled, but no hysteresis data found in persistence (v1 data or fresh start).")
            else:
                _LOGGER.debug("Hysteresis is disabled, skipping hysteresis data load.")

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
    
    async def async_get_dashboard_data(self) -> dict:
        """Return all data needed by dashboard sensors.
        
        Returns a dictionary containing:
        - calculated_offset: Current offset value
        - learning_info: Full learning statistics
        - save_diagnostics: Save operation statistics
        - calibration_info: Calibration phase information
        """
        try:
            # Get the last calculated offset (default to 0.0 if not available)
            calculated_offset = getattr(self, '_last_offset', 0.0)
            
            # Get full learning info using existing method
            learning_info = self.get_learning_info()
            
            # Build save diagnostics
            save_diagnostics = {
                "save_count": self._save_count,
                "failed_save_count": self._failed_save_count,
                "last_save_time": self._last_save_time.isoformat() if self._last_save_time else None,
            }
            
            # Build calibration info
            calibration_info = {
                "in_calibration": self.is_in_calibration_phase,
                "cached_offset": self._stable_calibration_offset,
            }
            
            # Return the complete dashboard data
            return {
                "calculated_offset": calculated_offset,
                "learning_info": learning_info,
                "save_diagnostics": save_diagnostics,
                "calibration_info": calibration_info,
            }
            
        except Exception as exc:
            _LOGGER.error("Error getting dashboard data: %s", exc)
            # Return safe fallback data on error
            return {
                "calculated_offset": 0.0,
                "learning_info": {
                    "enabled": False,
                    "samples": 0,
                    "accuracy": 0.0,
                    "confidence": 0.0,
                    "has_sufficient_data": False,
                    "last_sample_time": None,
                    "hysteresis_enabled": False,
                    "hysteresis_state": "disabled",
                    "learned_start_threshold": None,
                    "learned_stop_threshold": None,
                    "temperature_window": None,
                    "start_samples_collected": 0,
                    "stop_samples_collected": 0,
                    "hysteresis_ready": False,
                },
                "save_diagnostics": {
                    "save_count": 0,
                    "failed_save_count": 0,
                    "last_save_time": None,
                },
                "calibration_info": {
                    "in_calibration": False,
                    "cached_offset": None,
                },
            }