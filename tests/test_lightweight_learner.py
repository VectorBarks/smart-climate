"""Tests for LightweightOffsetLearner component."""

import pytest
import json
from datetime import time
from unittest.mock import Mock, patch
from typing import Dict, Any

from custom_components.smart_climate.lightweight_learner import (
    LightweightOffsetLearner,
    OffsetPrediction,
    LearningStats
)


class TestOffsetPrediction:
    """Test suite for OffsetPrediction dataclass."""

    def test_offset_prediction_creation(self):
        """Test OffsetPrediction creation with all fields."""
        prediction = OffsetPrediction(
            predicted_offset=1.5,
            confidence=0.85,
            reason="Time-based learning pattern"
        )
        
        assert prediction.predicted_offset == 1.5
        assert prediction.confidence == 0.85
        assert prediction.reason == "Time-based learning pattern"

    def test_offset_prediction_types(self):
        """Test OffsetPrediction field types."""
        prediction = OffsetPrediction(
            predicted_offset=2.0,
            confidence=0.9,
            reason="Test reason"
        )
        
        assert isinstance(prediction.predicted_offset, float)
        assert isinstance(prediction.confidence, float)
        assert isinstance(prediction.reason, str)


class TestLearningStats:
    """Test suite for LearningStats dataclass."""

    def test_learning_stats_creation(self):
        """Test LearningStats creation with all fields."""
        stats = LearningStats(
            samples_collected=100,
            patterns_learned=24,
            avg_accuracy=0.82
        )
        
        assert stats.samples_collected == 100
        assert stats.patterns_learned == 24
        assert stats.avg_accuracy == 0.82

    def test_learning_stats_types(self):
        """Test LearningStats field types."""
        stats = LearningStats(
            samples_collected=50,
            patterns_learned=12,
            avg_accuracy=0.75
        )
        
        assert isinstance(stats.samples_collected, int)
        assert isinstance(stats.patterns_learned, int)
        assert isinstance(stats.avg_accuracy, float)


class TestLightweightOffsetLearner:
    """Test suite for LightweightOffsetLearner class."""

    def test_init_with_defaults(self):
        """Test LightweightOffsetLearner initialization with default parameters."""
        learner = LightweightOffsetLearner()
        
        assert learner._max_history == 1000
        assert learner._learning_rate == 0.1
        assert len(learner._time_patterns) == 24
        assert learner._sample_count == 0
        assert len(learner._temp_correlation_data) == 0
        assert learner._power_state_patterns == {}

    def test_init_with_custom_params(self):
        """Test LightweightOffsetLearner initialization with custom parameters."""
        learner = LightweightOffsetLearner(max_history=500, learning_rate=0.05)
        
        assert learner._max_history == 500
        assert learner._learning_rate == 0.05
        assert len(learner._time_patterns) == 24
        assert learner._sample_count == 0

    def test_update_pattern_basic(self):
        """Test basic pattern update functionality."""
        learner = LightweightOffsetLearner()
        
        # Initial update
        learner.update_pattern(
            offset=1.5,
            outdoor_temp=25.0,
            hour=14,
            power_state="cooling"
        )
        
        assert learner._sample_count == 1
        assert learner._time_patterns[14] == 1.5
        assert len(learner._temp_correlation_data) == 1

    def test_update_pattern_multiple_same_hour(self):
        """Test pattern update with multiple data points for same hour."""
        learner = LightweightOffsetLearner(learning_rate=0.1)
        
        # First update
        learner.update_pattern(offset=1.0, outdoor_temp=25.0, hour=14, power_state="cooling")
        assert learner._time_patterns[14] == 1.0
        
        # Second update - should apply exponential smoothing
        learner.update_pattern(offset=2.0, outdoor_temp=26.0, hour=14, power_state="cooling")
        expected = 0.1 * 2.0 + 0.9 * 1.0  # α * new + (1-α) * old
        assert abs(learner._time_patterns[14] - expected) < 0.001

    def test_update_pattern_hour_validation(self):
        """Test hour validation in update_pattern."""
        learner = LightweightOffsetLearner()
        
        # Valid hours (0-23)
        learner.update_pattern(offset=1.0, outdoor_temp=25.0, hour=0, power_state="cooling")
        learner.update_pattern(offset=1.0, outdoor_temp=25.0, hour=23, power_state="cooling")
        
        # Invalid hours
        with pytest.raises(ValueError, match="Hour must be between 0 and 23"):
            learner.update_pattern(offset=1.0, outdoor_temp=25.0, hour=-1, power_state="cooling")
        
        with pytest.raises(ValueError, match="Hour must be between 0 and 23"):
            learner.update_pattern(offset=1.0, outdoor_temp=25.0, hour=24, power_state="cooling")

    def test_update_pattern_max_history_limit(self):
        """Test that update_pattern respects max_history limit."""
        learner = LightweightOffsetLearner(max_history=5)
        
        # Add more data than max_history
        for i in range(10):
            learner.update_pattern(
                offset=float(i),
                outdoor_temp=25.0 + i,
                hour=i % 24,
                power_state="cooling"
            )
        
        # Should only keep max_history samples
        assert len(learner._temp_correlation_data) == 5
        assert learner._sample_count == 10  # Total count still tracked

    def test_update_pattern_power_state_tracking(self):
        """Test power state pattern tracking."""
        learner = LightweightOffsetLearner()
        
        # Add data for different power states
        learner.update_pattern(offset=1.0, outdoor_temp=25.0, hour=14, power_state="cooling")
        learner.update_pattern(offset=0.5, outdoor_temp=25.0, hour=14, power_state="idle")
        learner.update_pattern(offset=1.2, outdoor_temp=25.0, hour=14, power_state="cooling")
        
        # Check power state patterns are tracked
        assert "cooling" in learner._power_state_patterns
        assert "idle" in learner._power_state_patterns
        assert learner._power_state_patterns["cooling"]["count"] == 2
        assert learner._power_state_patterns["idle"]["count"] == 1

    def test_update_pattern_none_outdoor_temp(self):
        """Test update_pattern with None outdoor temperature."""
        learner = LightweightOffsetLearner()
        
        learner.update_pattern(offset=1.5, outdoor_temp=None, hour=14, power_state="cooling")
        
        assert learner._sample_count == 1
        assert learner._time_patterns[14] == 1.5
        # Should not add to temp correlation data if outdoor_temp is None
        assert len(learner._temp_correlation_data) == 0

    def test_update_pattern_none_power_state(self):
        """Test update_pattern with None power state."""
        learner = LightweightOffsetLearner()
        
        learner.update_pattern(offset=1.5, outdoor_temp=25.0, hour=14, power_state=None)
        
        assert learner._sample_count == 1
        assert learner._time_patterns[14] == 1.5
        # Should not add to power state patterns if power_state is None
        assert len(learner._power_state_patterns) == 0

    def test_predict_offset_time_pattern_only(self):
        """Test prediction based on time patterns only."""
        learner = LightweightOffsetLearner()
        
        # Train with some time patterns
        learner.update_pattern(offset=1.5, outdoor_temp=None, hour=14, power_state=None)
        learner.update_pattern(offset=1.6, outdoor_temp=None, hour=14, power_state=None)
        
        # Predict for same hour
        prediction = learner.predict_offset(outdoor_temp=None, hour=14, power_state=None)
        
        assert isinstance(prediction, OffsetPrediction)
        assert prediction.predicted_offset != 0.0
        assert 0.0 <= prediction.confidence <= 1.0
        assert "time-based" in prediction.reason.lower()

    def test_predict_offset_with_temperature_correlation(self):
        """Test prediction with temperature correlation."""
        learner = LightweightOffsetLearner()
        
        # Train with correlated data
        for i in range(10):
            temp = 20.0 + i
            offset = 1.0 + (i * 0.1)  # Positive correlation
            learner.update_pattern(offset=offset, outdoor_temp=temp, hour=14, power_state="cooling")
        
        # Predict with temperature
        prediction = learner.predict_offset(outdoor_temp=25.0, hour=14, power_state="cooling")
        
        assert isinstance(prediction, OffsetPrediction)
        assert prediction.predicted_offset != 0.0
        assert prediction.confidence > 0.5  # Should be confident with good correlation
        assert "temperature correlation" in prediction.reason.lower()

    def test_predict_offset_with_power_state(self):
        """Test prediction with power state consideration."""
        learner = LightweightOffsetLearner()
        
        # Train with different power states
        for _ in range(5):
            learner.update_pattern(offset=1.0, outdoor_temp=25.0, hour=14, power_state="cooling")
        for _ in range(5):
            learner.update_pattern(offset=0.5, outdoor_temp=25.0, hour=14, power_state="idle")
        
        # Predict for different power states
        prediction_cooling = learner.predict_offset(outdoor_temp=25.0, hour=14, power_state="cooling")
        prediction_idle = learner.predict_offset(outdoor_temp=25.0, hour=14, power_state="idle")
        
        assert prediction_cooling.predicted_offset != prediction_idle.predicted_offset
        assert "power state" in prediction_cooling.reason.lower()

    def test_predict_offset_unknown_hour(self):
        """Test prediction for hour with no training data."""
        learner = LightweightOffsetLearner()
        
        # Train for hour 14
        learner.update_pattern(offset=1.5, outdoor_temp=25.0, hour=14, power_state="cooling")
        
        # Predict for hour 8 (no training data)
        prediction = learner.predict_offset(outdoor_temp=25.0, hour=8, power_state="cooling")
        
        assert isinstance(prediction, OffsetPrediction)
        assert prediction.confidence < 0.5  # Should have low confidence
        assert "limited data" in prediction.reason.lower()

    def test_predict_offset_hour_validation(self):
        """Test hour validation in predict_offset."""
        learner = LightweightOffsetLearner()
        
        # Invalid hours
        with pytest.raises(ValueError, match="Hour must be between 0 and 23"):
            learner.predict_offset(outdoor_temp=25.0, hour=-1, power_state="cooling")
        
        with pytest.raises(ValueError, match="Hour must be between 0 and 23"):
            learner.predict_offset(outdoor_temp=25.0, hour=24, power_state="cooling")

    def test_predict_offset_confidence_scoring(self):
        """Test confidence scoring logic."""
        learner = LightweightOffsetLearner()
        
        # Train with varying amounts of data
        for i in range(1):
            learner.update_pattern(offset=1.0, outdoor_temp=25.0, hour=14, power_state="cooling")
        prediction_low = learner.predict_offset(outdoor_temp=25.0, hour=14, power_state="cooling")
        
        for i in range(49):  # Total 50 samples
            learner.update_pattern(offset=1.0, outdoor_temp=25.0, hour=14, power_state="cooling")
        prediction_high = learner.predict_offset(outdoor_temp=25.0, hour=14, power_state="cooling")
        
        assert prediction_high.confidence > prediction_low.confidence

    def test_get_learning_stats_initial(self):
        """Test get_learning_stats with initial state."""
        learner = LightweightOffsetLearner()
        
        stats = learner.get_learning_stats()
        
        assert isinstance(stats, LearningStats)
        assert stats.samples_collected == 0
        assert stats.patterns_learned == 0
        assert stats.avg_accuracy == 0.0

    def test_get_learning_stats_after_training(self):
        """Test get_learning_stats after training."""
        learner = LightweightOffsetLearner()
        
        # Add training data
        for hour in range(12):
            learner.update_pattern(offset=1.0, outdoor_temp=25.0, hour=hour, power_state="cooling")
        
        stats = learner.get_learning_stats()
        
        assert stats.samples_collected == 12
        assert stats.patterns_learned == 12  # Each hour is a pattern
        assert stats.avg_accuracy > 0.0

    def test_reset_learning(self):
        """Test reset_learning functionality."""
        learner = LightweightOffsetLearner()
        
        # Add some training data
        for hour in range(5):
            learner.update_pattern(offset=1.0, outdoor_temp=25.0, hour=hour, power_state="cooling")
        
        # Verify data exists
        stats_before = learner.get_learning_stats()
        assert stats_before.samples_collected > 0
        
        # Reset
        learner.reset_learning()
        
        # Verify reset
        stats_after = learner.get_learning_stats()
        assert stats_after.samples_collected == 0
        assert stats_after.patterns_learned == 0
        assert stats_after.avg_accuracy == 0.0
        assert len(learner._temp_correlation_data) == 0
        assert len(learner._power_state_patterns) == 0

    def test_save_patterns(self):
        """Test save_patterns functionality."""
        learner = LightweightOffsetLearner()
        
        # Add some training data
        learner.update_pattern(offset=1.5, outdoor_temp=25.0, hour=14, power_state="cooling")
        learner.update_pattern(offset=0.8, outdoor_temp=20.0, hour=8, power_state="idle")
        
        # Save patterns
        patterns = learner.save_patterns()
        
        assert isinstance(patterns, dict)
        assert "time_patterns" in patterns
        assert "temp_correlation_data" in patterns
        assert "power_state_patterns" in patterns
        assert "sample_count" in patterns
        assert "version" in patterns
        
        # Verify data integrity
        assert patterns["sample_count"] == 2
        assert patterns["time_patterns"][14] == 1.5
        assert patterns["time_patterns"][8] == 0.8

    def test_load_patterns_valid_data(self):
        """Test load_patterns with valid data."""
        learner = LightweightOffsetLearner()
        
        # Create valid pattern data
        patterns = {
            "version": "1.0",
            "time_patterns": {14: 1.5, 8: 0.8},
            "temp_correlation_data": [
                {"outdoor_temp": 25.0, "offset": 1.5},
                {"outdoor_temp": 20.0, "offset": 0.8}
            ],
            "power_state_patterns": {
                "cooling": {"avg_offset": 1.5, "count": 1},
                "idle": {"avg_offset": 0.8, "count": 1}
            },
            "sample_count": 2
        }
        
        # Load patterns
        learner.load_patterns(patterns)
        
        # Verify loaded data
        assert learner._sample_count == 2
        assert learner._time_patterns[14] == 1.5
        assert learner._time_patterns[8] == 0.8
        assert len(learner._temp_correlation_data) == 2
        assert len(learner._power_state_patterns) == 2

    def test_load_patterns_invalid_data(self):
        """Test load_patterns with invalid data."""
        learner = LightweightOffsetLearner()
        
        # Test with invalid version
        with pytest.raises(ValueError, match="Unsupported pattern data version"):
            learner.load_patterns({"version": "2.0"})
        
        # Test with missing fields
        with pytest.raises(KeyError):
            learner.load_patterns({"version": "1.0"})  # Missing required fields

    def test_load_patterns_corrupted_data(self):
        """Test load_patterns with corrupted data."""
        learner = LightweightOffsetLearner()
        
        # Test with corrupted time patterns
        patterns = {
            "version": "1.0",
            "time_patterns": {"25": 1.5},  # Invalid hour
            "temp_correlation_data": [],
            "power_state_patterns": {},
            "sample_count": 1
        }
        
        with pytest.raises(ValueError, match="Invalid hour in time patterns"):
            learner.load_patterns(patterns)

    def test_json_serialization_roundtrip(self):
        """Test JSON serialization/deserialization roundtrip."""
        learner1 = LightweightOffsetLearner()
        
        # Add training data
        for hour in range(5):
            learner1.update_pattern(
                offset=1.0 + hour * 0.1,
                outdoor_temp=25.0 + hour,
                hour=hour,
                power_state="cooling"
            )
        
        # Save and serialize
        patterns = learner1.save_patterns()
        json_data = json.dumps(patterns)
        
        # Deserialize and load
        restored_patterns = json.loads(json_data)
        learner2 = LightweightOffsetLearner()
        learner2.load_patterns(restored_patterns)
        
        # Verify identical behavior
        prediction1 = learner1.predict_offset(outdoor_temp=25.0, hour=0, power_state="cooling")
        prediction2 = learner2.predict_offset(outdoor_temp=25.0, hour=0, power_state="cooling")
        
        assert abs(prediction1.predicted_offset - prediction2.predicted_offset) < 0.001
        assert abs(prediction1.confidence - prediction2.confidence) < 0.001

    def test_performance_requirements(self):
        """Test performance requirements (<1ms prediction, <1MB memory)."""
        learner = LightweightOffsetLearner(max_history=1000)
        
        # Fill with maximum data
        for i in range(1000):
            learner.update_pattern(
                offset=1.0 + (i % 100) * 0.01,
                outdoor_temp=20.0 + (i % 50),
                hour=i % 24,
                power_state="cooling" if i % 2 == 0 else "idle"
            )
        
        # Test prediction performance
        import time
        start_time = time.time()
        for _ in range(100):  # 100 predictions
            learner.predict_offset(outdoor_temp=25.0, hour=14, power_state="cooling")
        elapsed = time.time() - start_time
        
        # Should average <1ms per prediction
        avg_time = elapsed / 100
        assert avg_time < 0.001, f"Average prediction time {avg_time:.4f}s exceeds 1ms limit"
        
        # Test memory usage (approximate)
        import sys
        patterns_size = sys.getsizeof(learner.save_patterns())
        assert patterns_size < 1024 * 1024, f"Pattern data size {patterns_size} exceeds 1MB limit"

    def test_learning_accuracy_improvement(self):
        """Test that learning accuracy improves over time."""
        learner = LightweightOffsetLearner()
        
        # Train with consistent pattern
        for i in range(50):
            # Hour 14 always has offset 1.5
            learner.update_pattern(offset=1.5, outdoor_temp=25.0, hour=14, power_state="cooling")
        
        # Prediction should be close to training data
        prediction = learner.predict_offset(outdoor_temp=25.0, hour=14, power_state="cooling")
        assert abs(prediction.predicted_offset - 1.5) < 0.1
        assert prediction.confidence > 0.8

    def test_graceful_degradation_with_missing_data(self):
        """Test graceful degradation when data is missing."""
        learner = LightweightOffsetLearner()
        
        # Train with limited data
        learner.update_pattern(offset=1.0, outdoor_temp=25.0, hour=14, power_state="cooling")
        
        # Predict with different conditions
        prediction = learner.predict_offset(outdoor_temp=None, hour=8, power_state=None)
        
        # Should still provide reasonable prediction
        assert isinstance(prediction, OffsetPrediction)
        assert prediction.confidence >= 0.0
        assert prediction.predicted_offset is not None
        assert "limited data" in prediction.reason.lower()

    def test_memory_efficiency_with_large_dataset(self):
        """Test memory efficiency with large dataset."""
        learner = LightweightOffsetLearner(max_history=100)
        
        # Add way more data than max_history
        for i in range(500):
            learner.update_pattern(
                offset=1.0 + (i % 10) * 0.1,
                outdoor_temp=20.0 + (i % 20),
                hour=i % 24,
                power_state="cooling" if i % 2 == 0 else "idle"
            )
        
        # Should maintain memory limit
        assert len(learner._temp_correlation_data) <= 100
        assert learner._sample_count == 500  # But still track total samples
        
        # Should still make reasonable predictions
        prediction = learner.predict_offset(outdoor_temp=25.0, hour=14, power_state="cooling")
        assert isinstance(prediction, OffsetPrediction)
        assert prediction.confidence > 0.0

    def test_exponential_smoothing_behavior(self):
        """Test exponential smoothing behavior for recent data weighting."""
        learner = LightweightOffsetLearner(learning_rate=0.1)
        
        # Add old data
        for _ in range(10):
            learner.update_pattern(offset=1.0, outdoor_temp=25.0, hour=14, power_state="cooling")
        
        old_pattern = learner._time_patterns[14]
        
        # Add new data with different pattern
        for _ in range(3):
            learner.update_pattern(offset=2.0, outdoor_temp=25.0, hour=14, power_state="cooling")
        
        new_pattern = learner._time_patterns[14]
        
        # New pattern should be closer to recent data (2.0) than old (1.0)
        assert new_pattern > old_pattern
        assert new_pattern < 2.0  # But not exactly 2.0 due to smoothing
        assert new_pattern > 1.0  # But greater than original