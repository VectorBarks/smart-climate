"""Tests for LightweightOffsetLearner hysteresis enhancements."""

import pytest
from datetime import time
from unittest.mock import Mock, patch
from typing import Dict, Any

from custom_components.smart_climate.lightweight_learner import (
    LightweightOffsetLearner,
    OffsetPrediction,
    LearningStats
)


class TestLightweightLearnerHysteresisEnhancements:
    """Test suite for hysteresis-enhanced LightweightOffsetLearner methods."""

    def test_add_sample_with_hysteresis_state(self):
        """Test add_sample method with hysteresis_state parameter."""
        learner = LightweightOffsetLearner()
        
        # Test with hysteresis_state provided
        learner.add_sample(
            predicted=1.0,
            actual=1.2,
            ac_temp=24.0,
            room_temp=25.0,
            outdoor_temp=30.0,
            mode="cool",
            power=150.0,
            hysteresis_state="active_phase"
        )
        
        assert learner._sample_count == 1
        # Verify sample data includes hysteresis_state
        assert len(learner._enhanced_samples) == 1
        sample = learner._enhanced_samples[0]
        assert sample["hysteresis_state"] == "active_phase"
        assert sample["predicted"] == 1.0
        assert sample["actual"] == 1.2

    def test_add_sample_without_hysteresis_state_uses_default(self):
        """Test add_sample method without hysteresis_state uses default."""
        learner = LightweightOffsetLearner()
        
        # Test without hysteresis_state (should use default)
        learner.add_sample(
            predicted=1.0,
            actual=1.2,
            ac_temp=24.0,
            room_temp=25.0,
            outdoor_temp=30.0,
            mode="cool",
            power=150.0
        )
        
        assert learner._sample_count == 1
        sample = learner._enhanced_samples[0]
        assert sample["hysteresis_state"] == "no_power_sensor"

    def test_add_sample_with_different_hysteresis_states(self):
        """Test add_sample with various hysteresis states."""
        learner = LightweightOffsetLearner()
        
        hysteresis_states = [
            "learning_hysteresis",
            "active_phase", 
            "idle_above_start_threshold",
            "idle_below_stop_threshold",
            "idle_stable_zone",
            "no_power_sensor"
        ]
        
        for i, state in enumerate(hysteresis_states):
            learner.add_sample(
                predicted=1.0 + i * 0.1,
                actual=1.1 + i * 0.1,
                ac_temp=24.0,
                room_temp=25.0,
                hysteresis_state=state
            )
        
        assert learner._sample_count == len(hysteresis_states)
        
        # Verify all states are stored correctly
        stored_states = [sample["hysteresis_state"] for sample in learner._enhanced_samples]
        assert stored_states == hysteresis_states

    def test_predict_with_hysteresis_state(self):
        """Test predict method with hysteresis_state parameter."""
        learner = LightweightOffsetLearner()
        
        # Add training data with specific hysteresis state
        for i in range(5):
            learner.add_sample(
                predicted=1.0,
                actual=1.5,
                ac_temp=24.0 + i * 0.1,
                room_temp=25.0 + i * 0.1,
                outdoor_temp=30.0,
                mode="cool",
                power=150.0,
                hysteresis_state="active_phase"
            )
        
        # Predict with matching hysteresis state
        prediction = learner.predict(
            ac_temp=24.2,
            room_temp=25.2,
            outdoor_temp=30.0,
            mode="cool",
            power=150.0,
            hysteresis_state="active_phase"
        )
        
        assert isinstance(prediction, float)
        # Prediction should be influenced by matching hysteresis state
        assert prediction != 0.0

    def test_predict_without_hysteresis_state_uses_default(self):
        """Test predict method without hysteresis_state uses default."""
        learner = LightweightOffsetLearner()
        
        # Add training data
        learner.add_sample(
            predicted=1.0,
            actual=1.5,
            ac_temp=24.0,
            room_temp=25.0
        )
        
        # Predict without hysteresis_state (should use default)
        prediction = learner.predict(
            ac_temp=24.0,
            room_temp=25.0
        )
        
        assert isinstance(prediction, float)

    def test_enhanced_similarity_with_matching_hysteresis_state(self):
        """Test that samples with matching hysteresis_state have higher similarity."""
        learner = LightweightOffsetLearner()
        
        # Add samples with different hysteresis states
        learner.add_sample(
            predicted=1.0, actual=1.5, ac_temp=24.0, room_temp=25.0,
            hysteresis_state="active_phase"
        )
        learner.add_sample(
            predicted=1.0, actual=1.2, ac_temp=24.0, room_temp=25.0,
            hysteresis_state="idle_stable_zone"
        )
        learner.add_sample(
            predicted=1.0, actual=1.4, ac_temp=24.0, room_temp=25.0,
            hysteresis_state="active_phase"
        )
        
        # Predict with "active_phase" - should favor samples with matching state
        prediction_active = learner.predict(
            ac_temp=24.0,
            room_temp=25.0,
            hysteresis_state="active_phase"
        )
        
        # Predict with "idle_stable_zone"
        prediction_idle = learner.predict(
            ac_temp=24.0,
            room_temp=25.0,
            hysteresis_state="idle_stable_zone"
        )
        
        # Predictions should differ based on hysteresis state
        assert prediction_active != prediction_idle

    def test_backward_compatibility_with_existing_samples(self):
        """Test backward compatibility with samples that don't have hysteresis_state."""
        learner = LightweightOffsetLearner()
        
        # Simulate existing samples without hysteresis_state
        # This would happen when loading old persistence data
        learner._enhanced_samples = [
            {
                "predicted": 1.0,
                "actual": 1.2,
                "ac_temp": 24.0,
                "room_temp": 25.0,
                "outdoor_temp": 30.0,
                "mode": "cool",
                "power": 150.0,
                "timestamp": "2023-10-27T15:30:00.123456"
                # Note: no hysteresis_state field
            }
        ]
        learner._sample_count = 1
        
        # Should handle prediction without errors
        prediction = learner.predict(
            ac_temp=24.0,
            room_temp=25.0,
            hysteresis_state="active_phase"
        )
        
        assert isinstance(prediction, float)
        # Should not raise any errors

    def test_similarity_calculation_handles_missing_hysteresis_state(self):
        """Test similarity calculation gracefully handles missing hysteresis_state in old samples."""
        learner = LightweightOffsetLearner()
        
        # Add old sample without hysteresis_state
        learner._enhanced_samples = [
            {
                "predicted": 1.0,
                "actual": 1.3,
                "ac_temp": 24.0,
                "room_temp": 25.0,
                "outdoor_temp": 30.0,
                "mode": "cool",
                "power": 150.0
                # Missing hysteresis_state
            }
        ]
        learner._sample_count = 1
        
        # Add new sample with hysteresis_state
        learner.add_sample(
            predicted=1.0, actual=1.5, ac_temp=24.1, room_temp=25.1,
            hysteresis_state="active_phase"
        )
        
        # Should work without errors
        prediction = learner.predict(
            ac_temp=24.0, room_temp=25.0,
            hysteresis_state="active_phase"
        )
        
        assert isinstance(prediction, float)

    def test_hysteresis_state_similarity_weighting(self):
        """Test that hysteresis_state similarity affects prediction weighting."""
        learner = LightweightOffsetLearner()
        
        # Add samples with identical conditions but different hysteresis states
        # and different actual offsets
        learner.add_sample(
            predicted=1.0, actual=2.0, ac_temp=24.0, room_temp=25.0,
            outdoor_temp=30.0, mode="cool", power=150.0,
            hysteresis_state="active_phase"
        )
        learner.add_sample(
            predicted=1.0, actual=0.5, ac_temp=24.0, room_temp=25.0,
            outdoor_temp=30.0, mode="cool", power=150.0,
            hysteresis_state="idle_stable_zone"
        )
        
        # Predict for active_phase - should be closer to 2.0
        prediction_active = learner.predict(
            ac_temp=24.0, room_temp=25.0, outdoor_temp=30.0,
            mode="cool", power=150.0, hysteresis_state="active_phase"
        )
        
        # Predict for idle_stable_zone - should be closer to 0.5
        prediction_idle = learner.predict(
            ac_temp=24.0, room_temp=25.0, outdoor_temp=30.0,
            mode="cool", power=150.0, hysteresis_state="idle_stable_zone"
        )
        
        # Verify predictions favor matching hysteresis states
        assert abs(prediction_active - 2.0) < abs(prediction_active - 0.5)
        assert abs(prediction_idle - 0.5) < abs(prediction_idle - 2.0)

    def test_no_breaking_changes_to_existing_api(self):
        """Test that existing API methods still work unchanged."""
        learner = LightweightOffsetLearner()
        
        # Test existing update_pattern method still works
        learner.update_pattern(
            offset=1.5,
            outdoor_temp=25.0,
            hour=14,
            power_state="cooling"
        )
        
        # Test existing predict_offset method still works
        prediction = learner.predict_offset(
            outdoor_temp=25.0,
            hour=14,
            power_state="cooling"
        )
        
        assert isinstance(prediction, OffsetPrediction)
        assert learner._sample_count == 1

    def test_enhanced_sample_data_structure(self):
        """Test that enhanced sample data structure includes all required fields."""
        learner = LightweightOffsetLearner()
        
        learner.add_sample(
            predicted=1.0,
            actual=1.2,
            ac_temp=24.0,
            room_temp=25.0,
            outdoor_temp=30.0,
            mode="cool",
            power=150.0,
            hysteresis_state="active_phase"
        )
        
        sample = learner._enhanced_samples[0]
        
        # Verify all required fields are present
        required_fields = [
            "predicted", "actual", "ac_temp", "room_temp",
            "outdoor_temp", "mode", "power", "hysteresis_state", "timestamp"
        ]
        
        for field in required_fields:
            assert field in sample

    def test_serialization_compatibility_with_hysteresis_data(self):
        """Test that serialization includes hysteresis_state data."""
        learner = LightweightOffsetLearner()
        
        # Add samples with hysteresis states
        learner.add_sample(
            predicted=1.0, actual=1.2, ac_temp=24.0, room_temp=25.0,
            hysteresis_state="active_phase"
        )
        learner.add_sample(
            predicted=1.1, actual=1.3, ac_temp=24.1, room_temp=25.1,
            hysteresis_state="idle_stable_zone"
        )
        
        # Test serialization includes hysteresis data
        patterns = learner.save_patterns()
        
        # Should include enhanced samples with hysteresis_state
        assert "enhanced_samples" in patterns
        assert len(patterns["enhanced_samples"]) == 2
        
        for sample in patterns["enhanced_samples"]:
            assert "hysteresis_state" in sample

    def test_performance_with_hysteresis_enhancement(self):
        """Test that hysteresis enhancements don't degrade performance."""
        learner = LightweightOffsetLearner()
        
        # Add many samples with hysteresis states
        for i in range(100):
            learner.add_sample(
                predicted=1.0,
                actual=1.0 + (i % 10) * 0.01,
                ac_temp=24.0 + (i % 5) * 0.1,
                room_temp=25.0 + (i % 5) * 0.1,
                outdoor_temp=30.0,
                mode="cool",
                power=150.0,
                hysteresis_state=["active_phase", "idle_stable_zone"][i % 2]
            )
        
        # Test prediction performance
        import time
        start_time = time.time()
        
        for _ in range(50):  # 50 predictions
            learner.predict(
                ac_temp=24.2,
                room_temp=25.2,
                outdoor_temp=30.0,
                mode="cool",
                power=150.0,
                hysteresis_state="active_phase"
            )
        
        elapsed = time.time() - start_time
        avg_time = elapsed / 50
        
        # Should still be very fast
        assert avg_time < 0.01, f"Average prediction time {avg_time:.4f}s too slow"

    def test_edge_case_empty_samples_with_hysteresis_prediction(self):
        """Test prediction with hysteresis_state when no samples exist."""
        learner = LightweightOffsetLearner()
        
        # Predict with no training data
        prediction = learner.predict(
            ac_temp=24.0,
            room_temp=25.0,
            hysteresis_state="active_phase"
        )
        
        # Should return default prediction (0.0)
        assert prediction == 0.0

    def test_mixed_sample_types_compatibility(self):
        """Test compatibility when mixing old update_pattern and new add_sample calls."""
        learner = LightweightOffsetLearner()
        
        # Add sample via old method
        learner.update_pattern(
            offset=1.5,
            outdoor_temp=25.0,
            hour=14,
            power_state="cooling"
        )
        
        # Add sample via new method
        learner.add_sample(
            predicted=1.0, actual=1.3, ac_temp=24.0, room_temp=25.0,
            hysteresis_state="active_phase"
        )
        
        # Both prediction methods should work
        old_prediction = learner.predict_offset(
            outdoor_temp=25.0, hour=14, power_state="cooling"
        )
        new_prediction = learner.predict(
            ac_temp=24.0, room_temp=25.0, hysteresis_state="active_phase"
        )
        
        assert isinstance(old_prediction, OffsetPrediction)
        assert isinstance(new_prediction, float)