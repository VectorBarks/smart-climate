"""Offset calculation engine for Smart Climate Control."""

import logging
from typing import Optional, Dict, List, Tuple, Callable, TYPE_CHECKING
import statistics
from datetime import datetime

from .models import OffsetInput, OffsetResult

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from .data_store import SmartClimateDataStore

_LOGGER = logging.getLogger(__name__)


class LightweightOffsetLearner:
    """Lightweight learning component for offset prediction."""
    
    def __init__(self):
        """Initialize the learner."""
        self._training_samples: List[Dict] = []
        self._min_samples = 20  # Minimum samples for predictions
        self._max_samples = 1000  # Maximum samples to keep in memory
        self._has_sufficient_data = False
        
    def has_sufficient_data(self) -> bool:
        """Check if learner has sufficient training data."""
        return len(self._training_samples) >= self._min_samples
    
    def record_sample(
        self,
        predicted_offset: float,
        actual_offset: float,
        input_data: OffsetInput
    ) -> None:
        """Record a training sample."""
        try:
            sample = {
                "predicted": predicted_offset,
                "actual": actual_offset,
                "ac_temp": input_data.ac_internal_temp,
                "room_temp": input_data.room_temp,
                "outdoor_temp": input_data.outdoor_temp,
                "mode": input_data.mode,
                "power": input_data.power_consumption,
                "hour": input_data.time_of_day.hour,
                "day_of_week": input_data.day_of_week,
                "timestamp": datetime.now()
            }
            
            self._training_samples.append(sample)
            
            # Keep only recent samples to prevent memory bloat
            if len(self._training_samples) > self._max_samples:
                removed_count = len(self._training_samples) - self._max_samples
                self._training_samples = self._training_samples[-self._max_samples:]
                _LOGGER.debug("Pruned %s old training samples, keeping %s most recent", removed_count, self._max_samples)
            
            self._has_sufficient_data = self.has_sufficient_data()
            
            _LOGGER.debug(
                "Recording learning sample: predicted=%s, actual=%s, samples_count=%s, sufficient_data=%s",
                predicted_offset, actual_offset, len(self._training_samples), self._has_sufficient_data
            )
            
        except Exception as exc:
            _LOGGER.warning("Failed to record learning sample: %s", exc)
    
    def predict_offset(self, input_data: OffsetInput) -> Dict:
        """Predict offset based on learned patterns."""
        if not self._has_sufficient_data:
            _LOGGER.debug(
                "Prediction request with insufficient data: have %s samples, need %s",
                len(self._training_samples), self._min_samples
            )
            return {"predicted_offset": 0.0, "confidence": 0.0}
        
        try:
            # Find similar conditions
            similar_samples = self._find_similar_samples(input_data)
            
            if not similar_samples:
                _LOGGER.debug(
                    "No similar samples found for prediction: ac_temp=%s, room_temp=%s, mode=%s",
                    input_data.ac_internal_temp, input_data.room_temp, input_data.mode
                )
                return {"predicted_offset": 0.0, "confidence": 0.0}
            
            # Calculate weighted average of actual offsets
            actual_offsets = [sample["actual"] for sample in similar_samples]
            predicted_offset = statistics.mean(actual_offsets)
            
            # Calculate confidence based on sample size and consistency
            confidence = self._calculate_prediction_confidence(similar_samples)
            
            _LOGGER.debug(
                "Prediction generated: offset=%s, confidence=%s, similar_samples=%s, from_total=%s",
                predicted_offset, confidence, len(similar_samples), len(self._training_samples)
            )
            
            return {
                "predicted_offset": predicted_offset,
                "confidence": confidence
            }
            
        except Exception as exc:
            _LOGGER.warning("Failed to predict offset: %s", exc)
            return {"predicted_offset": 0.0, "confidence": 0.0}
    
    def _find_similar_samples(self, input_data: OffsetInput) -> List[Dict]:
        """Find samples with similar conditions."""
        similar = []
        
        for sample in self._training_samples:
            similarity_score = 0.0
            factors = 0
            
            # Temperature similarity (most important)
            temp_diff = abs(sample["ac_temp"] - input_data.ac_internal_temp)
            if temp_diff <= 2.0:  # Within 2°C
                similarity_score += 3.0 * (2.0 - temp_diff) / 2.0
            factors += 3.0
            
            room_temp_diff = abs(sample["room_temp"] - input_data.room_temp)
            if room_temp_diff <= 2.0:
                similarity_score += 2.0 * (2.0 - room_temp_diff) / 2.0
            factors += 2.0
            
            # Mode similarity
            if sample["mode"] == input_data.mode:
                similarity_score += 2.0
            factors += 2.0
            
            # Power consumption similarity (if available)
            if sample["power"] is not None and input_data.power_consumption is not None:
                power_diff = abs(sample["power"] - input_data.power_consumption)
                if power_diff <= 100:  # Within 100W
                    similarity_score += 1.0 * (100 - power_diff) / 100
                factors += 1.0
            
            # Time of day similarity
            hour_diff = abs(sample["hour"] - input_data.time_of_day.hour)
            if hour_diff <= 3:  # Within 3 hours
                similarity_score += 0.5 * (3 - hour_diff) / 3
            factors += 0.5
            
            # Outdoor temperature similarity (if available)
            if sample["outdoor_temp"] is not None and input_data.outdoor_temp is not None:
                outdoor_diff = abs(sample["outdoor_temp"] - input_data.outdoor_temp)
                if outdoor_diff <= 5.0:  # Within 5°C
                    similarity_score += 1.0 * (5.0 - outdoor_diff) / 5.0
                factors += 1.0
            
            # Accept samples with >60% similarity
            if similarity_score / factors > 0.6:
                similar.append(sample)
        
        # Return most recent similar samples (max 10)
        similar.sort(key=lambda x: x["timestamp"], reverse=True)
        return similar[:10]
    
    def _calculate_prediction_confidence(self, similar_samples: List[Dict]) -> float:
        """Calculate confidence in prediction based on sample quality."""
        if not similar_samples:
            return 0.0
        
        # Base confidence from sample size
        sample_confidence = min(len(similar_samples) / 10, 1.0)
        
        # Consistency confidence from variance in actual offsets
        actual_offsets = [sample["actual"] for sample in similar_samples]
        if len(actual_offsets) > 1:
            variance = statistics.variance(actual_offsets)
            consistency_confidence = max(0.0, 1.0 - variance / 2.0)
        else:
            consistency_confidence = 0.5
        
        # Overall confidence (weighted average)
        return 0.6 * sample_confidence + 0.4 * consistency_confidence
    
    def get_statistics(self) -> Dict:
        """Get learning statistics."""
        if not self._training_samples:
            return {
                "samples": 0,
                "accuracy": 0.0,
                "mean_error": 0.0,
                "has_sufficient_data": False
            }
        
        # Calculate prediction accuracy
        errors = []
        for sample in self._training_samples:
            error = abs(sample["predicted"] - sample["actual"])
            errors.append(error)
        
        mean_error = statistics.mean(errors) if errors else 0.0
        accuracy = max(0.0, 1.0 - mean_error / 2.0)  # Normalize to 0-1
        
        return {
            "samples": len(self._training_samples),
            "accuracy": accuracy,
            "mean_error": mean_error,
            "has_sufficient_data": self._has_sufficient_data
        }
    
    def serialize_for_persistence(self) -> Dict:
        """Serialize learner state for persistence.
        
        Returns:
            Dictionary containing all learner state that can be saved to JSON
        """
        # Convert datetime objects to ISO strings for JSON serialization
        serializable_samples = []
        for sample in self._training_samples:
            serializable_sample = sample.copy()
            if isinstance(serializable_sample.get("timestamp"), datetime):
                serializable_sample["timestamp"] = serializable_sample["timestamp"].isoformat()
            serializable_samples.append(serializable_sample)
        
        return {
            "samples": serializable_samples,
            "min_samples": self._min_samples,
            "max_samples": self._max_samples,
            "has_sufficient_data": self._has_sufficient_data,
            "statistics": self.get_statistics()
        }
    
    def restore_from_persistence(self, data: Dict) -> bool:
        """Restore learner state from persisted data.
        
        Args:
            data: Dictionary containing serialized learner state
            
        Returns:
            True if restoration was successful, False otherwise
        """
        try:
            # Validate data structure
            if not isinstance(data, dict):
                _LOGGER.warning("Invalid persistence data: not a dictionary")
                return False
            
            samples = data.get("samples", [])
            if not isinstance(samples, list):
                _LOGGER.warning("Invalid samples data in persistence: not a list")
                return False
            
            # Restore samples, converting timestamp strings back to datetime objects
            restored_samples = []
            for sample in samples:
                if not isinstance(sample, dict):
                    continue
                
                # Validate required fields exist
                required_fields = ["predicted", "actual", "ac_temp", "room_temp", "mode", "hour", "day_of_week"]
                if not all(field in sample for field in required_fields):
                    # Skip samples missing required fields
                    continue
                
                # Convert timestamp string back to datetime
                timestamp_str = sample.get("timestamp")
                if isinstance(timestamp_str, str):
                    try:
                        sample["timestamp"] = datetime.fromisoformat(timestamp_str)
                    except ValueError:
                        # Skip samples with invalid timestamps
                        continue
                elif not isinstance(timestamp_str, datetime):
                    # Skip samples with invalid timestamp types
                    continue
                
                restored_samples.append(sample)
            
            # Restore state
            self._training_samples = restored_samples[-self._max_samples:]  # Keep only recent samples
            self._has_sufficient_data = len(self._training_samples) >= self._min_samples
            
            _LOGGER.debug(
                "Restored %d learning samples, sufficient_data=%s",
                len(self._training_samples), self._has_sufficient_data
            )
            
            return True
            
        except Exception as exc:
            _LOGGER.warning("Failed to restore learner state from persistence: %s", exc)
            return False


class OffsetEngine:
    """Calculates temperature offset for accurate climate control."""
    
    def __init__(self, config: dict):
        """Initialize the offset engine with configuration."""
        self._max_offset = config.get("max_offset", 5.0)
        self._ml_enabled = config.get("ml_enabled", True)
        self._ml_model = None  # Loaded when available
        
        # Learning configuration (disabled by default for backward compatibility)
        self._enable_learning = config.get("enable_learning", False)
        self._learner: Optional[LightweightOffsetLearner] = None
        self._update_callbacks: List[Callable] = []  # For state update notifications
        
        if self._enable_learning:
            self._learner = LightweightOffsetLearner()
            _LOGGER.debug("Learning enabled - LightweightOffsetLearner initialized")
        
        _LOGGER.debug(
            "OffsetEngine initialized with max_offset=%s, ml_enabled=%s, learning_enabled=%s",
            self._max_offset,
            self._ml_enabled,
            self._enable_learning
        )
    
    @property
    def is_learning_enabled(self) -> bool:
        """Return true if learning is enabled."""
        return self._enable_learning
    
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
                self._learner = LightweightOffsetLearner()
                _LOGGER.info("LightweightOffsetLearner initialized at runtime")
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
    
    def calculate_offset(self, input_data: OffsetInput) -> OffsetResult:
        """Calculate temperature offset based on current conditions.
        
        Args:
            input_data: OffsetInput containing all sensor data and context
            
        Returns:
            OffsetResult with calculated offset and metadata
        """
        try:
            # Calculate basic rule-based offset from temperature difference
            temp_diff = input_data.ac_internal_temp - input_data.room_temp
            base_offset = -temp_diff  # Negative because we want to correct the difference
            
            # Apply mode-specific adjustments
            mode_adjusted_offset = self._apply_mode_adjustments(base_offset, input_data)
            
            # Apply contextual adjustments
            rule_based_offset = self._apply_contextual_adjustments(
                mode_adjusted_offset, input_data
            )
            
            # Try to use learning if enabled and sufficient data available
            final_offset = rule_based_offset
            learning_confidence = 0.0
            learning_used = False
            
            learning_error = None
            if self._enable_learning and self._learner and self._learner.has_sufficient_data():
                try:
                    _LOGGER.debug("Attempting learning prediction for offset calculation")
                    learning_result = self._learner.predict_offset(input_data)
                    learned_offset = learning_result["predicted_offset"]
                    learning_confidence = learning_result["confidence"]
                    
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
            
            return OffsetResult(
                offset=clamped_offset,
                clamped=was_clamped,
                reason=reason,
                confidence=confidence
            )
            
        except Exception as exc:
            _LOGGER.error("Error calculating offset: %s", exc)
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
            if input_data.power_consumption > 250:  # High power usage
                # AC is working hard, might need less offset
                adjusted_offset *= 0.9
            elif input_data.power_consumption < 100:  # Low power usage
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
    
    def _generate_reason(self, input_data: OffsetInput, offset: float, clamped: bool) -> str:
        """Generate human-readable reason for the offset."""
        if offset == 0.0:
            return "No offset needed - AC and room temperatures match"
        
        reasons = []
        
        # Main temperature difference reason
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
            if input_data.power_consumption > 250:
                reasons.append("high power usage")
            elif input_data.power_consumption < 100:
                reasons.append("low power usage")
        
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
        
        try:
            self._learner.record_sample(predicted_offset, actual_offset, input_data)
            _LOGGER.debug(
                "Recorded learning sample: predicted=%.2f, actual=%.2f",
                predicted_offset, actual_offset
            )
        except Exception as exc:
            _LOGGER.warning("Failed to record learning sample: %s", exc)
    
    def get_learning_info(self) -> Dict:
        """Get learning information and statistics.
        
        Returns:
            Dictionary containing learning status and statistics
        """
        if not self._enable_learning or not self._learner:
            return {
                "enabled": False,
                "samples": 0,
                "accuracy": 0.0,
                "confidence": 0.0,
                "has_sufficient_data": False
            }
        
        try:
            stats = self._learner.get_statistics()
            return {
                "enabled": True,
                "samples": stats["samples"],
                "accuracy": stats["accuracy"],
                "confidence": stats["accuracy"],  # Use accuracy as overall confidence
                "has_sufficient_data": stats["has_sufficient_data"],
                "mean_error": stats["mean_error"]
            }
        except Exception as exc:
            _LOGGER.warning("Failed to get learning info: %s", exc)
            return {
                "enabled": True,
                "samples": 0,
                "accuracy": 0.0,
                "confidence": 0.0,
                "has_sufficient_data": False,
                "error": str(exc)
            }
    
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
        if input_data.ac_internal_temp > input_data.room_temp:
            reasons.append("AC sensor warmer than room")
        elif input_data.ac_internal_temp < input_data.room_temp:
            reasons.append("AC sensor cooler than room")
        
        # Learning information
        if self._enable_learning and self._learner:
            if learning_error:
                reasons.append("learning error, fallback used")
            elif learning_used:
                reasons.append(f"learning-enhanced (confidence: {learning_confidence:.1f})")
            elif self._learner.has_sufficient_data():
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
            if input_data.power_consumption > 250:
                reasons.append("high power usage")
            elif input_data.power_consumption < 100:
                reasons.append("low power usage")
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
        to survive Home Assistant restarts.
        """
        if not hasattr(self, "_data_store") or self._data_store is None:
            _LOGGER.warning("No data store configured, cannot save learning data")
            return

        try:
            # Prepare learner data only if learning is enabled and learner exists
            learner_data = None
            sample_count = 0
            if self._enable_learning and self._learner:
                learner_data = self._learner.serialize_for_persistence()
                sample_count = learner_data.get("statistics", {}).get("samples", 0)
                _LOGGER.debug("Serializing learner data: %s samples, learning_enabled=%s", sample_count, self._enable_learning)

            # Create a comprehensive state dictionary including the engine's state
            persistent_data = {
                "version": 1,  # For future schema migrations
                "engine_state": {
                    "enable_learning": self._enable_learning
                },
                "learner_data": learner_data
            }

            _LOGGER.debug(
                "Saving learning data: samples=%s, enabled=%s, has_learner_data=%s",
                sample_count, self._enable_learning, learner_data is not None
            )

            # Save to persistent storage
            await self._data_store.async_save_learning_data(persistent_data)
            _LOGGER.debug("Learning data and engine state saved successfully")

        except Exception as exc:
            _LOGGER.error("Failed to save learning data: %s", exc)
    
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
                        self._learner = LightweightOffsetLearner()
                        _LOGGER.debug("LightweightOffsetLearner initialized during data load.")
            # --- END OF KEY FIX ---

            # If learning is enabled (either from config or restored from persistence), load learner data
            if self._enable_learning:
                learner_data = persistent_data.get("learner_data")
                if learner_data:
                    # Ensure learner exists before restoring data
                    if not self._learner:
                        self._learner = LightweightOffsetLearner()

                    success = self._learner.restore_from_persistence(learner_data)
                    if success:
                        _LOGGER.info("Learning data loaded successfully.")
                    else:
                        _LOGGER.warning("Failed to restore learner state from loaded data.")
                else:
                    _LOGGER.debug("Learning is enabled, but no learner data found in persistence.")
            else:
                _LOGGER.debug("Learning is disabled based on persisted state, skipping learner data load.")

            self._notify_update_callbacks()  # Notify listeners of the restored state
            return True

        except Exception as exc:
            _LOGGER.error("Failed to load learning data: %s", exc)
            return False
    
    async def async_setup_periodic_save(self, hass: "HomeAssistant") -> Callable:
        """Set up periodic saving of learning data.
        
        Args:
            hass: Home Assistant instance
            
        Returns:
            Function to cancel the periodic saving
        """
        from homeassistant.helpers.event import async_track_time_interval
        from datetime import timedelta
        
        if not self._enable_learning:
            _LOGGER.debug("Learning disabled, skipping periodic save setup")
            return lambda: None
        
        async def _periodic_save(_now=None):
            """Periodic save callback."""
            await self.async_save_learning_data()
        
        # Save every 10 minutes (600 seconds)
        remove_listener = async_track_time_interval(
            hass, _periodic_save, timedelta(seconds=600)
        )
        
        _LOGGER.debug("Periodic learning data save configured (every 10 minutes)")
        return remove_listener
    
    async def _trigger_save_callback(self) -> None:
        """Trigger a save operation (used for testing and state changes)."""
        await self.async_save_learning_data()