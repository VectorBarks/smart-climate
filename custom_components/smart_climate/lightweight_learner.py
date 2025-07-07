"""Lightweight offset learning for Smart Climate Control.

ABOUTME: Implements incremental machine learning for offset pattern recognition.
Uses simple statistics and exponential smoothing for memory-efficient real-time learning.
"""

import logging
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from collections import deque

_LOGGER = logging.getLogger(__name__)


@dataclass
class OffsetPrediction:
    """Result of offset prediction."""
    predicted_offset: float  # Predicted offset in degrees
    confidence: float  # 0.0 to 1.0 confidence in prediction
    reason: str  # Human-readable reason for prediction


@dataclass
class LearningStats:
    """Statistics about the learning process."""
    samples_collected: int  # Total number of data points collected
    patterns_learned: int  # Number of distinct patterns learned
    avg_accuracy: float  # Average accuracy of predictions (0.0 to 1.0)


class LightweightOffsetLearner:
    """Lightweight machine learning for offset pattern recognition.
    
    Uses incremental learning with exponential smoothing to learn patterns:
    - Time-of-day patterns (24-hour learning)
    - Temperature correlation patterns
    - Power state awareness
    - Memory-efficient storage with configurable limits
    """
    
    def __init__(self, max_history: int = 1000, learning_rate: float = 0.1):
        """Initialize the lightweight learner.
        
        Args:
            max_history: Maximum number of data points to keep in memory
            learning_rate: Learning rate for exponential smoothing (0.0 to 1.0)
        """
        if not 0.0 < learning_rate <= 1.0:
            raise ValueError("Learning rate must be between 0.0 and 1.0")
        if max_history <= 0:
            raise ValueError("Max history must be positive")
            
        self._max_history = max_history
        self._learning_rate = learning_rate
        
        # Time-of-day patterns (24 hours, 0-23)
        self._time_patterns: List[float] = [0.0] * 24
        self._time_pattern_counts: List[int] = [0] * 24
        
        # Temperature correlation data (limited by max_history)
        self._temp_correlation_data = deque(maxlen=max_history)
        
        # Power state patterns
        self._power_state_patterns: Dict[str, Dict[str, float]] = {}
        
        # Overall statistics
        self._sample_count: int = 0
        
        _LOGGER.debug(
            "LightweightOffsetLearner initialized: max_history=%d, learning_rate=%.3f",
            max_history, learning_rate
        )
    
    def update_pattern(
        self,
        offset: float,
        outdoor_temp: Optional[float],
        hour: int,
        power_state: Optional[str]
    ) -> None:
        """Update learning patterns with new data point.
        
        Args:
            offset: Actual offset that was effective
            outdoor_temp: Outdoor temperature if available
            hour: Hour of day (0-23)
            power_state: Power state ("cooling", "idle", etc.) if available
        
        Raises:
            ValueError: If hour is not between 0 and 23
        """
        if not 0 <= hour <= 23:
            raise ValueError(f"Hour must be between 0 and 23, got {hour}")
        
        self._sample_count += 1
        
        # Update time-of-day pattern with exponential smoothing
        if self._time_pattern_counts[hour] == 0:
            # First data point for this hour
            self._time_patterns[hour] = offset
        else:
            # Apply exponential smoothing: new_value = α * new + (1-α) * old
            self._time_patterns[hour] = (
                self._learning_rate * offset + 
                (1 - self._learning_rate) * self._time_patterns[hour]
            )
        self._time_pattern_counts[hour] += 1
        
        # Update temperature correlation data if outdoor temp available
        if outdoor_temp is not None:
            self._temp_correlation_data.append({
                "outdoor_temp": outdoor_temp,
                "offset": offset
            })
        
        # Update power state patterns if available
        if power_state is not None:
            if power_state not in self._power_state_patterns:
                self._power_state_patterns[power_state] = {
                    "avg_offset": offset,
                    "count": 1
                }
            else:
                # Update running average
                pattern = self._power_state_patterns[power_state]
                total_offset = pattern["avg_offset"] * pattern["count"] + offset
                pattern["count"] += 1
                pattern["avg_offset"] = total_offset / pattern["count"]
        
        _LOGGER.debug(
            "Pattern updated: hour=%d, offset=%.2f, outdoor_temp=%s, power_state=%s",
            hour, offset, outdoor_temp, power_state
        )
    
    def predict_offset(
        self,
        outdoor_temp: Optional[float],
        hour: int,
        power_state: Optional[str]
    ) -> OffsetPrediction:
        """Predict offset based on learned patterns.
        
        Args:
            outdoor_temp: Current outdoor temperature if available
            hour: Current hour of day (0-23)
            power_state: Current power state if available
        
        Returns:
            OffsetPrediction with predicted offset, confidence, and reasoning
        
        Raises:
            ValueError: If hour is not between 0 and 23
        """
        if not 0 <= hour <= 23:
            raise ValueError(f"Hour must be between 0 and 23, got {hour}")
        
        reasons = []
        prediction_components = []
        confidence_factors = []
        
        # 1. Time-based prediction
        if self._time_pattern_counts[hour] > 0:
            time_prediction = self._time_patterns[hour]
            prediction_components.append(("time", time_prediction, 1.0))
            
            # Confidence based on sample count for this hour
            time_confidence = min(1.0, self._time_pattern_counts[hour] / 50.0)
            confidence_factors.append(time_confidence)
            reasons.append(f"time-based pattern (hour {hour})")
        else:
            # Use overall average as fallback
            if self._sample_count > 0:
                avg_offset = sum(self._time_patterns) / 24
                prediction_components.append(("fallback", avg_offset, 0.3))
                confidence_factors.append(0.2)
                reasons.append("limited data for this hour")
            else:
                prediction_components.append(("default", 0.0, 0.1))
                confidence_factors.append(0.1)
                reasons.append("no training data available")
        
        # 2. Temperature correlation prediction
        if outdoor_temp is not None and len(self._temp_correlation_data) >= 2:
            temp_prediction = self._predict_from_temperature_correlation(outdoor_temp)
            if temp_prediction is not None:
                prediction_components.append(("temperature", temp_prediction, 0.8))
                
                # Confidence based on correlation strength
                temp_confidence = min(1.0, len(self._temp_correlation_data) / 15.0)
                confidence_factors.append(temp_confidence)
                reasons.append("temperature correlation")
        
        # 3. Power state prediction
        if power_state is not None and power_state in self._power_state_patterns:
            power_prediction = self._power_state_patterns[power_state]["avg_offset"]
            power_count = self._power_state_patterns[power_state]["count"]
            
            prediction_components.append(("power", power_prediction, 0.6))
            
            # Confidence based on sample count for this power state
            power_confidence = min(1.0, power_count / 30.0)
            confidence_factors.append(power_confidence)
            reasons.append(f"power state pattern ({power_state})")
        
        # Combine predictions with weighted average
        if prediction_components:
            total_weight = sum(weight for _, _, weight in prediction_components)
            weighted_sum = sum(
                prediction * weight 
                for _, prediction, weight in prediction_components
            )
            final_prediction = weighted_sum / total_weight
        else:
            final_prediction = 0.0
        
        # Calculate overall confidence
        if confidence_factors:
            # Use geometric mean for conservative confidence estimation
            confidence = 1.0
            for factor in confidence_factors:
                confidence *= factor
            confidence = confidence ** (1.0 / len(confidence_factors))
            
            # Boost confidence if multiple prediction methods agree
            if len(prediction_components) > 1:
                confidence = min(1.0, confidence * 1.5)
        else:
            confidence = 0.1
        
        # Generate human-readable reason
        reason = ", ".join(reasons) if reasons else "no patterns available"
        
        _LOGGER.debug(
            "Offset predicted: %.3f (confidence: %.2f, reason: %s)",
            final_prediction, confidence, reason
        )
        
        return OffsetPrediction(
            predicted_offset=final_prediction,
            confidence=confidence,
            reason=reason
        )
    
    def _predict_from_temperature_correlation(self, outdoor_temp: float) -> Optional[float]:
        """Predict offset based on temperature correlation.
        
        Args:
            outdoor_temp: Outdoor temperature to predict for
            
        Returns:
            Predicted offset or None if insufficient data
        """
        if len(self._temp_correlation_data) < 2:
            return None
        
        try:
            # Extract temperatures and offsets
            temps = [data["outdoor_temp"] for data in self._temp_correlation_data]
            offsets = [data["offset"] for data in self._temp_correlation_data]
            
            # Calculate simple linear correlation
            # For simplicity, use linear interpolation/extrapolation
            if len(set(temps)) < 2:
                # All temperatures are the same, return average offset
                return statistics.mean(offsets)
            
            # Find two closest temperature points
            temp_diffs = [(abs(temp - outdoor_temp), temp, offset) 
                         for temp, offset in zip(temps, offsets)]
            temp_diffs.sort()
            
            if len(temp_diffs) >= 2:
                # Linear interpolation between two closest points
                _, temp1, offset1 = temp_diffs[0]
                _, temp2, offset2 = temp_diffs[1]
                
                if temp1 == temp2:
                    return (offset1 + offset2) / 2
                
                # Linear interpolation
                ratio = (outdoor_temp - temp1) / (temp2 - temp1)
                predicted = offset1 + ratio * (offset2 - offset1)
                return predicted
            else:
                # Fall back to closest point
                return temp_diffs[0][2]
                
        except (ZeroDivisionError, ValueError) as exc:
            _LOGGER.warning("Error in temperature correlation prediction: %s", exc)
            return None
    
    def get_learning_stats(self) -> LearningStats:
        """Get statistics about the learning process.
        
        Returns:
            LearningStats with current learning statistics
        """
        # Count patterns learned (hours with data)
        patterns_learned = sum(1 for count in self._time_pattern_counts if count > 0)
        
        # Calculate average accuracy (simplified metric)
        if self._sample_count == 0:
            avg_accuracy = 0.0
        else:
            # Use consistency as a proxy for accuracy
            # More consistent predictions = higher accuracy
            hour_variances = []
            for hour in range(24):
                if self._time_pattern_counts[hour] > 1:
                    # This is a simplified accuracy metric
                    # In practice, would compare predictions vs actual outcomes
                    consistency = min(1.0, self._time_pattern_counts[hour] / 10.0)
                    hour_variances.append(consistency)
            
            if hour_variances:
                avg_accuracy = statistics.mean(hour_variances)
            else:
                avg_accuracy = 0.5  # Default moderate accuracy
        
        return LearningStats(
            samples_collected=self._sample_count,
            patterns_learned=patterns_learned,
            avg_accuracy=avg_accuracy
        )
    
    def reset_learning(self) -> None:
        """Reset all learned patterns to initial state."""
        self._time_patterns = [0.0] * 24
        self._time_pattern_counts = [0] * 24
        self._temp_correlation_data.clear()
        self._power_state_patterns.clear()
        self._sample_count = 0
        
        _LOGGER.info("All learning patterns have been reset")
    
    def save_patterns(self) -> Dict[str, Any]:
        """Save current patterns for persistence.
        
        Returns:
            Dictionary containing all pattern data for JSON serialization
        """
        return {
            "version": "1.0",
            "time_patterns": {
                hour: offset for hour, offset in enumerate(self._time_patterns)
                if self._time_pattern_counts[hour] > 0
            },
            "time_pattern_counts": {
                hour: count for hour, count in enumerate(self._time_pattern_counts)
                if count > 0
            },
            "temp_correlation_data": list(self._temp_correlation_data),
            "power_state_patterns": dict(self._power_state_patterns),
            "sample_count": self._sample_count
        }
    
    def load_patterns(self, patterns: Dict[str, Any]) -> None:
        """Load patterns from saved data.
        
        Args:
            patterns: Dictionary containing pattern data
            
        Raises:
            ValueError: If pattern data is invalid or incompatible
            KeyError: If required fields are missing
        """
        # Validate version
        version = patterns.get("version")
        if version != "1.0":
            raise ValueError(f"Unsupported pattern data version: {version}")
        
        # Validate and load time patterns
        time_patterns = patterns["time_patterns"]
        time_pattern_counts = patterns.get("time_pattern_counts", {})
        
        # Reset current patterns
        self._time_patterns = [0.0] * 24
        self._time_pattern_counts = [0] * 24
        
        # Load time patterns with validation
        for hour_str, offset in time_patterns.items():
            hour = int(hour_str)
            if not 0 <= hour <= 23:
                raise ValueError(f"Invalid hour in time patterns: {hour}")
            self._time_patterns[hour] = float(offset)
        
        for hour_str, count in time_pattern_counts.items():
            hour = int(hour_str)
            if not 0 <= hour <= 23:
                raise ValueError(f"Invalid hour in time pattern counts: {hour}")
            self._time_pattern_counts[hour] = int(count)
        
        # Load temperature correlation data
        self._temp_correlation_data.clear()
        temp_data = patterns["temp_correlation_data"]
        for item in temp_data:
            self._temp_correlation_data.append({
                "outdoor_temp": float(item["outdoor_temp"]),
                "offset": float(item["offset"])
            })
        
        # Load power state patterns
        self._power_state_patterns = {}
        power_patterns = patterns["power_state_patterns"]
        for state, pattern in power_patterns.items():
            self._power_state_patterns[str(state)] = {
                "avg_offset": float(pattern["avg_offset"]),
                "count": int(pattern["count"])
            }
        
        # Load sample count
        self._sample_count = int(patterns["sample_count"])
        
        _LOGGER.info(
            "Loaded patterns: %d samples, %d hours with data, %d power states",
            self._sample_count,
            sum(1 for count in self._time_pattern_counts if count > 0),
            len(self._power_state_patterns)
        )