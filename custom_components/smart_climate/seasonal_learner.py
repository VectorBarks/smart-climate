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
from homeassistant.helpers.storage import Store

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
        
        # Initialize storage
        self._store = Store(
            hass,
            version=1,
            key=f"smart_climate_seasonal_patterns",
            encoder=None
        )
        
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
    
    def get_relevant_hysteresis_delta(self, current_outdoor_temp: Optional[float] = None) -> Optional[float]:
        """Calculates the most relevant hysteresis delta based on current outdoor temp.
        
        Args:
            current_outdoor_temp: Outdoor temperature to match against (optional)
            
        Returns:
            Most relevant hysteresis delta or None if no patterns available
        """
        if not self._patterns:
            _LOGGER.debug("No patterns available for hysteresis delta calculation")
            return None
        
        # Get current outdoor temperature if not provided
        if current_outdoor_temp is None:
            current_outdoor_temp = self._get_current_outdoor_temp()
        
        if current_outdoor_temp is None:
            _LOGGER.debug("No outdoor temperature available for pattern matching")
            return None
        
        # Try to find patterns within initial tolerance (±2.5°C)
        relevant_patterns = self._find_patterns_by_outdoor_temp(current_outdoor_temp, 2.5)
        
        # If insufficient patterns in bucket, try wider tolerance (±5°C)
        if len(relevant_patterns) < self._min_samples_for_bucket:
            _LOGGER.debug(
                "Insufficient patterns in bucket (±2.5°C): %d < %d, trying wider tolerance",
                len(relevant_patterns), self._min_samples_for_bucket
            )
            relevant_patterns = self._find_patterns_by_outdoor_temp(current_outdoor_temp, 5.0)
        
        # If still insufficient, use all patterns as graceful degradation
        if len(relevant_patterns) < self._min_samples_for_bucket:
            _LOGGER.debug(
                "Insufficient patterns in wider bucket (±5°C): %d < %d, using all patterns",
                len(relevant_patterns), self._min_samples_for_bucket
            )
            relevant_patterns = self._patterns
        
        if not relevant_patterns:
            _LOGGER.warning("No relevant patterns found for hysteresis delta calculation")
            return None
        
        # Calculate median delta for robust estimation
        deltas = [pattern.hysteresis_delta for pattern in relevant_patterns]
        median_delta = statistics.median(deltas)
        
        _LOGGER.debug(
            "Calculated hysteresis delta: outdoor_temp=%.1f, patterns_used=%d/%d, delta=%.1f",
            current_outdoor_temp, len(relevant_patterns), len(self._patterns), median_delta
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
    
    async def async_load(self) -> None:
        """Load learned patterns from storage."""
        try:
            stored_data = await self._store.async_load()
            
            if stored_data is None:
                _LOGGER.debug("No stored seasonal patterns found")
                return
            
            if not isinstance(stored_data, dict) or "patterns" not in stored_data:
                _LOGGER.warning("Invalid stored seasonal pattern data structure")
                return
            
            # Load patterns from storage
            self._patterns = []
            pattern_data = stored_data["patterns"]
            
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
            
            _LOGGER.info(
                "Loaded %d seasonal patterns from storage",
                len(self._patterns)
            )
            
        except Exception as exc:
            _LOGGER.error(
                "Error loading seasonal patterns from storage: %s",
                exc
            )
    
    async def async_save(self) -> None:
        """Save learned patterns to storage."""
        try:
            # Prepare data for storage
            pattern_data = []
            for pattern in self._patterns:
                pattern_data.append({
                    "timestamp": pattern.timestamp,
                    "start_temp": pattern.start_temp,
                    "stop_temp": pattern.stop_temp,
                    "outdoor_temp": pattern.outdoor_temp
                })
            
            stored_data = {
                "patterns": pattern_data
            }
            
            await self._store.async_save(stored_data)
            
            _LOGGER.debug(
                "Saved %d seasonal patterns to storage",
                len(self._patterns)
            )
            
        except Exception as exc:
            _LOGGER.error(
                "Error saving seasonal patterns to storage: %s",
                exc
            )
    
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
                return 0.0
            
            accuracy = self.get_seasonal_accuracy()
            
            # Scale contribution based on pattern count
            # Full contribution at 20+ patterns
            pattern_factor = min(1.0, pattern_count / 20.0)
            
            # Contribution is accuracy scaled by pattern factor
            contribution = accuracy * pattern_factor
            
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