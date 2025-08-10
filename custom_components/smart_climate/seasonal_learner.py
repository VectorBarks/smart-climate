"""Seasonal Learning Infrastructure for Smart Climate Control.

ABOUTME: Implements seasonal adaptation using outdoor temperature context for hysteresis learning.
Provides temperature bucket matching with graceful degradation and robust median-based calculations.
"""

import logging
import statistics
import time
from dataclasses import dataclass
from typing import List, Optional

from homeassistant.core import HomeAssistant

from .models import HvacCycleData

_LOGGER = logging.getLogger(__name__)


@dataclass
class LearnedPattern:
    """Represents a single learned AC hysteresis cycle with outdoor temperature context."""
    timestamp: float
    start_temp: float
    stop_temp: float
    outdoor_temp: float
    
    @property
    def hysteresis_delta(self) -> float:
        """The temperature drop achieved during the cooling cycle."""
        return self.start_temp - self.stop_temp


class SeasonalHysteresisLearner:
    """Enhanced HysteresisLearner with seasonal adaptation using outdoor temperature context."""
    
    def __init__(self, hass: HomeAssistant, outdoor_sensor_id: Optional[str]):
        """Initialize the seasonal hysteresis learner.
        
        Args:
            hass: Home Assistant instance
            outdoor_sensor_id: Entity ID of outdoor temperature sensor (optional)
        """
        self._hass = hass
        self._outdoor_sensor_id = outdoor_sensor_id
        self._patterns: List[LearnedPattern] = []
        self._data_retention_days = 45
        self._outdoor_temp_bucket_size = 5.0  # degrees C/F for pattern matching
        self._min_samples_for_bucket = 3
        
        # Storage is now handled by OffsetEngine via callbacks
        # No longer using separate Store instance
        
        _LOGGER.debug(
            "SeasonalHysteresisLearner initialized: outdoor_sensor=%s, retention_days=%d, bucket_size=%.1f",
            outdoor_sensor_id, self._data_retention_days, self._outdoor_temp_bucket_size
        )
    
    def learn_new_cycle(self, start_temp: float, stop_temp: float) -> None:
        """Records a new completed AC cycle with current outdoor temperature context.
        
        Args:
            start_temp: Temperature when AC started cooling
            stop_temp: Temperature when AC stopped cooling
        """
        _LOGGER.debug("SeasonalLearner.learn_new_cycle() - start: %.1f, stop: %.1f, existing patterns: %d",
                      start_temp, stop_temp, len(self._patterns))
        
        outdoor_temp = self._get_current_outdoor_temp()
        
        if outdoor_temp is None:
            _LOGGER.debug(
                "Cannot learn cycle without outdoor temperature: start=%.1f, stop=%.1f",
                start_temp, stop_temp
            )
            return
        
        # Create new pattern
        pattern = LearnedPattern(
            timestamp=time.time(),
            start_temp=start_temp,
            stop_temp=stop_temp,
            outdoor_temp=outdoor_temp
        )
        
        self._patterns.append(pattern)
        
        # Prune old patterns
        self._prune_old_patterns()
        
        _LOGGER.debug(
            "Learned new cycle: start=%.1f, stop=%.1f, outdoor=%.1f, delta=%.1f, total_patterns=%d",
            start_temp, stop_temp, outdoor_temp, pattern.hysteresis_delta, len(self._patterns)
        )
        
        _LOGGER.info(
            "Seasonal pattern learned: New AC cycle recorded (delta=%.1f°C) at outdoor temp %.1f°C. Total patterns: %d",
            pattern.hysteresis_delta, outdoor_temp, len(self._patterns)
        )
    
    def learn_from_cycle_data(self, cycle_data: HvacCycleData) -> None:
        """Records a new completed AC cycle from structured cycle data.
        
        Args:
            cycle_data: Complete cycle data including temperatures and timing
        """
        if cycle_data.outdoor_temp_at_start is None:
            _LOGGER.debug(
                "Cannot learn cycle without outdoor temperature data"
            )
            return
        
        # Use the stabilized temp as the stop temp since that's more accurate
        # for hysteresis learning than the immediate stop temp
        stop_temp = cycle_data.stabilized_temp
        
        # Create new pattern
        pattern = LearnedPattern(
            timestamp=cycle_data.start_time.timestamp(),
            start_temp=cycle_data.start_temp,
            stop_temp=stop_temp,
            outdoor_temp=cycle_data.outdoor_temp_at_start
        )
        
        self._patterns.append(pattern)
        
        # Prune old patterns
        self._prune_old_patterns()
        
        _LOGGER.debug(
            "Learned cycle from structured data: start=%.1f, stabilized=%.1f, outdoor=%.1f, delta=%.1f, duration=%s, total_patterns=%d",
            cycle_data.start_temp, stop_temp, cycle_data.outdoor_temp_at_start, 
            pattern.hysteresis_delta, cycle_data.end_time - cycle_data.start_time, len(self._patterns)
        )
        
        _LOGGER.info(
            "Seasonal pattern learned from cycle: delta=%.1f°C at outdoor temp %.1f°C (duration: %s). Total patterns: %d",
            pattern.hysteresis_delta, cycle_data.outdoor_temp_at_start, 
            cycle_data.end_time - cycle_data.start_time, len(self._patterns)
        )
    
    def get_relevant_hysteresis_delta(self, current_outdoor_temp: Optional[float] = None) -> Optional[float]:
        """Calculates the most relevant hysteresis delta based on current outdoor temp.
        
        Args:
            current_outdoor_temp: Outdoor temperature to match against (optional)
            
        Returns:
            Most relevant hysteresis delta or None if no patterns available
        """
        _LOGGER.debug("SeasonalLearner.get_relevant_hysteresis_delta() - patterns: %d, outdoor_temp: %s",
                      len(self._patterns) if self._patterns else 0, 
                      current_outdoor_temp if current_outdoor_temp is not None else "not provided")
        
        if not self._patterns:
            _LOGGER.debug("No patterns available for hysteresis delta calculation")
            return None
        
        # Get current outdoor temperature if not provided
        if current_outdoor_temp is None:
            current_outdoor_temp = self._get_current_outdoor_temp()
        
        if current_outdoor_temp is None:
            _LOGGER.debug("No outdoor temperature available for pattern matching")
            return None
        
        _LOGGER.debug(
            "Seasonal adaptation: outdoor_temp=%.1f°C, found %d patterns total",
            current_outdoor_temp, len(self._patterns)
        )
        
        # Try to find patterns within initial tolerance (±2.5°C)
        relevant_patterns = self._find_patterns_by_outdoor_temp(current_outdoor_temp, 2.5)
        
        _LOGGER.debug(
            "Seasonal: Searching patterns within ±2.5°C of %.1f°C, found %d matches",
            current_outdoor_temp, len(relevant_patterns)
        )
        
        # If insufficient patterns in bucket, try wider tolerance (±5°C)
        if len(relevant_patterns) < self._min_samples_for_bucket:
            _LOGGER.debug(
                "Insufficient patterns in bucket (±2.5°C): %d < %d, trying wider tolerance",
                len(relevant_patterns), self._min_samples_for_bucket
            )
            relevant_patterns = self._find_patterns_by_outdoor_temp(current_outdoor_temp, 5.0)
            
            _LOGGER.debug(
                "Seasonal: Searching patterns within ±5.0°C of %.1f°C, found %d matches",
                current_outdoor_temp, len(relevant_patterns)
            )
        
        # If still insufficient, use all patterns as graceful degradation
        if len(relevant_patterns) < self._min_samples_for_bucket:
            _LOGGER.debug(
                "Insufficient patterns in wider bucket (±5°C): %d < %d, using all patterns",
                len(relevant_patterns), self._min_samples_for_bucket
            )
            relevant_patterns = self._patterns
            _LOGGER.debug(
                "Seasonal: Using all %d patterns as fallback (graceful degradation)",
                len(relevant_patterns)
            )
        
        if not relevant_patterns:
            _LOGGER.warning("No relevant patterns found for hysteresis delta calculation")
            return None
        
        # Calculate median delta for robust estimation
        deltas = [pattern.hysteresis_delta for pattern in relevant_patterns]
        median_delta = statistics.median(deltas)
        
        # Determine which bucket was used for the final calculation
        if len(relevant_patterns) < len(self._patterns):
            temp_range_lower = current_outdoor_temp - (5.0 if len(relevant_patterns) > len(self._find_patterns_by_outdoor_temp(current_outdoor_temp, 2.5)) else 2.5)
            temp_range_upper = current_outdoor_temp + (5.0 if len(relevant_patterns) > len(self._find_patterns_by_outdoor_temp(current_outdoor_temp, 2.5)) else 2.5)
            _LOGGER.debug(
                "Seasonal: Using %d patterns from bucket [%.1f-%.1f°C], median delta=%.1f°C",
                len(relevant_patterns), temp_range_lower, temp_range_upper, median_delta
            )
        else:
            _LOGGER.debug(
                "Seasonal: Using all %d patterns (fallback), median delta=%.1f°C",
                len(relevant_patterns), median_delta
            )
        
        return median_delta
    
    def _get_current_outdoor_temp(self) -> Optional[float]:
        """Safely retrieves the current outdoor temperature from Home Assistant.
        
        Returns:
            Current outdoor temperature or None if unavailable
        """
        if self._outdoor_sensor_id is None:
            return None
        
        state = self._hass.states.get(self._outdoor_sensor_id)
        if state is None:
            _LOGGER.debug("Outdoor temperature sensor not found: %s", self._outdoor_sensor_id)
            return None
        
        try:
            return float(state.state)
        except (ValueError, TypeError):
            _LOGGER.debug(
                "Cannot parse outdoor temperature from state: %s",
                state.state
            )
            return None
    
    def _prune_old_patterns(self) -> None:
        """Removes patterns older than the retention period."""
        if not self._patterns:
            return
        
        cutoff_time = time.time() - (self._data_retention_days * 24 * 3600)
        old_count = len(self._patterns)
        
        self._patterns = [
            pattern for pattern in self._patterns
            if pattern.timestamp >= cutoff_time
        ]
        
        pruned_count = old_count - len(self._patterns)
        if pruned_count > 0:
            _LOGGER.debug(
                "Pruned %d old patterns (older than %d days), %d patterns remaining",
                pruned_count, self._data_retention_days, len(self._patterns)
            )
    
    def _find_patterns_by_outdoor_temp(self, target_temp: float, tolerance: float) -> List[LearnedPattern]:
        """Find patterns within temperature tolerance of target outdoor temperature.
        
        Args:
            target_temp: Target outdoor temperature
            tolerance: Temperature tolerance (±degrees)
            
        Returns:
            List of patterns within tolerance
        """
        matching_patterns = []
        
        for pattern in self._patterns:
            temp_diff = abs(pattern.outdoor_temp - target_temp)
            if temp_diff <= tolerance:
                matching_patterns.append(pattern)
        
        _LOGGER.debug(
            "Found %d patterns within %.1f°C of %.1f°C",
            len(matching_patterns), tolerance, target_temp
        )
        
        return matching_patterns
    
    def serialize_for_persistence(self) -> dict:
        """Serialize patterns for storage.
        
        Returns:
            Dictionary with patterns data ready for persistence
        """
        return {
            "patterns": [
                {
                    "timestamp": p.timestamp,
                    "start_temp": p.start_temp,
                    "stop_temp": p.stop_temp,
                    "outdoor_temp": p.outdoor_temp
                }
                for p in self._patterns
            ],
            "pattern_count": len(self._patterns)
        }
    
    def restore_from_persistence(self, data: dict) -> None:
        """Restore patterns from storage.
        
        Args:
            data: Dictionary containing patterns data from persistence
        """
        if not data or "patterns" not in data:
            _LOGGER.debug("No pattern data to restore")
            return
        
        self._patterns = []
        pattern_data = data["patterns"]
        
        for pattern_dict in pattern_data:
            try:
                pattern = LearnedPattern(
                    timestamp=float(pattern_dict["timestamp"]),
                    start_temp=float(pattern_dict["start_temp"]),
                    stop_temp=float(pattern_dict["stop_temp"]),
                    outdoor_temp=float(pattern_dict["outdoor_temp"])
                )
                self._patterns.append(pattern)
            except (KeyError, ValueError, TypeError) as exc:
                _LOGGER.warning(
                    "Skipping invalid stored pattern: %s. Error: %s",
                    pattern_dict, exc
                )
        
        # Prune old patterns after loading
        self._prune_old_patterns()
        
        pattern_count = data.get("pattern_count", len(self._patterns))
        _LOGGER.info(
            "Restored %d seasonal patterns from persistence",
            len(self._patterns)
        )
    
    # Removed async_save() and async_load() methods
    # Storage is now handled by OffsetEngine via serialize_for_persistence() and restore_from_persistence()
    
    def get_pattern_count(self) -> int:
        """Get the number of learned patterns.
        
        Returns:
            Number of learned patterns (>= 0)
        """
        if not hasattr(self, '_patterns') or self._patterns is None:
            return 0
        return len(self._patterns)
    
    def get_outdoor_temp_bucket(self) -> Optional[str]:
        """Get the current outdoor temperature bucket.
        
        Returns:
            Bucket string in format "X-Y°C" or None if unavailable
        """
        try:
            current_temp = self._get_current_outdoor_temp()
            if current_temp is None:
                return None
            
            # Calculate bucket boundaries (5°C buckets)
            bucket_size = 5.0
            lower_bound = int(current_temp // bucket_size) * int(bucket_size)
            upper_bound = lower_bound + int(bucket_size)
            
            return f"{lower_bound}-{upper_bound}°C"
            
        except Exception as exc:
            _LOGGER.warning(
                "Error calculating outdoor temperature bucket: %s",
                exc
            )
            return None
    
    def get_seasonal_accuracy(self) -> float:
        """Calculate the accuracy of seasonal predictions.
        
        Returns:
            Accuracy percentage (0-100)
        """
        try:
            if not hasattr(self, '_patterns') or not self._patterns:
                return 0.0
            
            # Need at least minimum samples
            if len(self._patterns) < self._min_samples_for_bucket:
                return 0.0
            
            current_temp = self._get_current_outdoor_temp()
            if current_temp is None:
                return 0.0
            
            # Find relevant patterns
            relevant_patterns = self._find_patterns_by_outdoor_temp(current_temp, 2.5)
            if len(relevant_patterns) < self._min_samples_for_bucket:
                relevant_patterns = self._find_patterns_by_outdoor_temp(current_temp, 5.0)
            
            if len(relevant_patterns) < self._min_samples_for_bucket:
                # Not enough patterns for meaningful accuracy
                return 0.0
            
            # Calculate median and deviations
            deltas = [pattern.hysteresis_delta for pattern in relevant_patterns]
            if not deltas:
                return 0.0
            
            median_delta = statistics.median(deltas)
            
            # Calculate average deviation from median
            deviations = [abs(delta - median_delta) for delta in deltas]
            avg_deviation = sum(deviations) / len(deviations)
            
            # Convert to accuracy percentage (lower deviation = higher accuracy)
            # Assume 1°C deviation = 100% error
            accuracy = max(0.0, 100.0 - (avg_deviation * 100.0))
            
            return round(accuracy, 1)
            
        except Exception as exc:
            _LOGGER.warning(
                "Error calculating seasonal accuracy: %s",
                exc
            )
            return 0.0
    
    def get_seasonal_contribution(self) -> float:
        """Get the contribution percentage of seasonal learning.
        
        Returns:
            Contribution percentage (0-100)
        """
        try:
            # Base contribution on pattern count and accuracy
            pattern_count = self.get_pattern_count()
            if pattern_count == 0:
                _LOGGER.debug("Seasonal contribution: No patterns available, contribution=0%")
                return 0.0
            
            accuracy = self.get_seasonal_accuracy()
            
            # Scale contribution based on pattern count
            # Full contribution at 20+ patterns
            pattern_factor = min(1.0, pattern_count / 20.0)
            
            # Contribution is accuracy scaled by pattern factor
            contribution = accuracy * pattern_factor
            
            _LOGGER.debug(
                "Seasonal contribution calculation: patterns=%d, accuracy=%.1f%%, pattern_factor=%.2f, contribution=%.1f%%",
                pattern_count, accuracy, pattern_factor, contribution
            )
            
            return round(contribution, 1)
            
        except Exception as exc:
            _LOGGER.warning(
                "Error calculating seasonal contribution: %s",
                exc
            )
            return 0.0
    
    def get_accuracy(self) -> float:
        """Get the accuracy of seasonal predictions.
        
        This method provides compatibility with the dashboard system
        by wrapping the get_seasonal_accuracy method.
        
        Returns:
            Accuracy percentage (0-100)
        """
        try:
            return self.get_seasonal_accuracy()
        except Exception as exc:
            _LOGGER.warning(
                "Error getting seasonal accuracy: %s",
                exc
            )
            return 0.0
    
    def log_pattern_summary(self):
        """Log summary of learned patterns for debugging."""
        if not self._patterns:
            _LOGGER.info("SeasonalLearner: No patterns learned yet")
            return
        
        _LOGGER.info("SeasonalLearner: %d patterns learned", len(self._patterns))
        for i, pattern in enumerate(self._patterns):
            _LOGGER.debug("  Pattern %d: start=%.1f, stop=%.1f, outdoor=%.1f, delta=%.2f, age=%.1f days",
                          i, pattern.start_temp, pattern.stop_temp, pattern.outdoor_temp, 
                          pattern.hysteresis_delta, (time.time() - pattern.timestamp) / 86400.0)