"""Comprehensive test suite for HysteresisLearner persistence methods."""

import pytest
from collections import deque
from custom_components.smart_climate.offset_engine import HysteresisLearner


class TestHysteresisLearnerPersistence:
    """Test the HysteresisLearner persistence functionality comprehensively."""

    def test_serialize_empty_learner(self):
        """Test serialization of an empty learner with no data."""
        learner = HysteresisLearner()
        
        data = learner.serialize_for_persistence()
        
        # Check structure and content
        assert isinstance(data, dict)
        assert set(data.keys()) == {"start_temps", "stop_temps"}
        assert data["start_temps"] == []
        assert data["stop_temps"] == []
        assert isinstance(data["start_temps"], list)
        assert isinstance(data["stop_temps"], list)

    def test_serialize_partially_filled_learner(self):
        """Test serialization with some data but not full."""
        learner = HysteresisLearner(max_samples=10)
        
        # Add some start transitions only
        learner.record_transition('start', 24.2)
        learner.record_transition('start', 24.4)
        learner.record_transition('start', 24.3)
        
        data = learner.serialize_for_persistence()
        
        # Check structure and content
        assert isinstance(data, dict)
        assert data["start_temps"] == [24.2, 24.4, 24.3]
        assert data["stop_temps"] == []

    def test_serialize_fully_filled_learner(self):
        """Test serialization with learner at maximum capacity."""
        learner = HysteresisLearner(max_samples=3)  # Small maxlen for easier testing
        
        # Fill beyond maximum capacity to test deque behavior
        start_temps = [24.1, 24.2, 24.3, 24.4, 24.5]  # 5 items, maxlen=3
        stop_temps = [23.5, 23.6, 23.7, 23.8, 23.9]   # 5 items, maxlen=3
        
        for temp in start_temps:
            learner.record_transition('start', temp)
        for temp in stop_temps:
            learner.record_transition('stop', temp)
        
        data = learner.serialize_for_persistence()
        
        # Should only contain the last 3 items due to maxlen
        assert data["start_temps"] == [24.3, 24.4, 24.5]
        assert data["stop_temps"] == [23.7, 23.8, 23.9]

    def test_serialize_data_types_are_json_compatible(self):
        """Test that serialized data contains only JSON-compatible types."""
        learner = HysteresisLearner()
        
        # Add some data with various float formats
        learner.record_transition('start', 24.0)
        learner.record_transition('start', 24.5)
        learner.record_transition('stop', 23.75)
        
        data = learner.serialize_for_persistence()
        
        # All values should be float or int (JSON compatible)
        for temp in data["start_temps"]:
            assert isinstance(temp, (int, float))
        for temp in data["stop_temps"]:
            assert isinstance(temp, (int, float))

    def test_restore_empty_data(self):
        """Test restoration from empty persistence data."""
        learner = HysteresisLearner(min_samples=2)
        
        # Initially has no data
        assert len(learner._start_temps) == 0
        assert len(learner._stop_temps) == 0
        
        # Restore from empty data
        data = {"start_temps": [], "stop_temps": []}
        learner.restore_from_persistence(data)
        
        # Should still be empty
        assert len(learner._start_temps) == 0
        assert len(learner._stop_temps) == 0
        assert learner.has_sufficient_data is False
        assert learner.learned_start_threshold is None
        assert learner.learned_stop_threshold is None

    def test_restore_partial_data(self):
        """Test restoration from partial persistence data."""
        learner = HysteresisLearner(min_samples=3)
        
        # Restore partial data (not enough for thresholds)
        data = {
            "start_temps": [24.2, 24.4],
            "stop_temps": [23.6]
        }
        learner.restore_from_persistence(data)
        
        # Data should be restored but insufficient for thresholds
        assert list(learner._start_temps) == [24.2, 24.4]
        assert list(learner._stop_temps) == [23.6]
        assert learner.has_sufficient_data is False
        assert learner.learned_start_threshold is None
        assert learner.learned_stop_threshold is None

    def test_restore_sufficient_data_calculates_thresholds(self):
        """Test that restoration triggers threshold calculation when sufficient data exists."""
        learner = HysteresisLearner(min_samples=3)
        
        # Restore sufficient data
        data = {
            "start_temps": [24.1, 24.3, 24.5, 24.2, 24.4],  # 5 samples
            "stop_temps": [23.5, 23.7, 23.9, 23.6, 23.8]   # 5 samples
        }
        learner.restore_from_persistence(data)
        
        # Data should be restored and thresholds calculated
        assert list(learner._start_temps) == [24.1, 24.3, 24.5, 24.2, 24.4]
        assert list(learner._stop_temps) == [23.5, 23.7, 23.9, 23.6, 23.8]
        assert learner.has_sufficient_data is True
        
        # Thresholds should be median values
        assert learner.learned_start_threshold == 24.3  # median of [24.1, 24.2, 24.3, 24.4, 24.5]
        assert learner.learned_stop_threshold == 23.7   # median of [23.5, 23.6, 23.7, 23.8, 23.9]

    def test_restore_preserves_deque_maxlen(self):
        """Test that restoration preserves the deque maxlen constraints."""
        learner = HysteresisLearner(min_samples=2, max_samples=3)
        
        # Restore more data than maxlen
        data = {
            "start_temps": [24.1, 24.2, 24.3, 24.4, 24.5],  # 5 items, maxlen=3
            "stop_temps": [23.5, 23.6, 23.7, 23.8, 23.9]   # 5 items, maxlen=3
        }
        learner.restore_from_persistence(data)
        
        # Should only keep the last max_samples items, in order
        assert len(learner._start_temps) == 3
        assert len(learner._stop_temps) == 3
        assert list(learner._start_temps) == [24.3, 24.4, 24.5]
        assert list(learner._stop_temps) == [23.7, 23.8, 23.9]
        
        # Deque should still respect maxlen for future additions
        learner.record_transition('start', 24.6)
        assert len(learner._start_temps) == 3
        assert list(learner._start_temps) == [24.4, 24.5, 24.6]

    def test_restore_malformed_data_missing_keys(self):
        """Test graceful handling of malformed data with missing keys."""
        learner = HysteresisLearner()
        
        # Add some initial data
        learner.record_transition('start', 25.0)
        initial_start_count = len(learner._start_temps)
        initial_stop_count = len(learner._stop_temps)
        
        # Try to restore malformed data (missing stop_temps key)
        malformed_data = {"start_temps": [24.2, 24.4]}
        learner.restore_from_persistence(malformed_data)
        
        # Should handle gracefully - start_temps restored, stop_temps cleared but not crashed
        assert list(learner._start_temps) == [24.2, 24.4]
        assert len(learner._stop_temps) == 0  # Should be cleared/empty due to missing key

    def test_restore_malformed_data_wrong_types(self):
        """Test graceful handling of malformed data with wrong types."""
        learner = HysteresisLearner()
        
        # Test various malformed inputs
        malformed_inputs = [
            {"start_temps": "not_a_list", "stop_temps": [23.5]},
            {"start_temps": [24.5], "stop_temps": "not_a_list"},
            {"start_temps": [24.5, "not_a_number"], "stop_temps": [23.5]},
            {"start_temps": [24.5], "stop_temps": [23.5, None]},
            {"start_temps": [24.5, []], "stop_temps": [23.5]},
        ]
        
        for malformed_data in malformed_inputs:
            # Should not crash, should handle gracefully
            learner.restore_from_persistence(malformed_data)
            
            # Verify learner is still functional after malformed data
            learner.record_transition('start', 24.0)
            learner.record_transition('stop', 23.0)
            assert isinstance(learner._start_temps, deque)
            assert isinstance(learner._stop_temps, deque)

    def test_restore_non_dict_input(self):
        """Test graceful handling of non-dictionary input."""
        learner = HysteresisLearner()
        
        # Add some initial data
        learner.record_transition('start', 25.0)
        
        # Test various non-dict inputs
        invalid_inputs = [None, "string", 123, [], True]
        
        for invalid_input in invalid_inputs:
            # Should handle gracefully without crashing
            learner.restore_from_persistence(invalid_input)
            
            # Learner should still be functional
            assert isinstance(learner._start_temps, deque)
            assert isinstance(learner._stop_temps, deque)

    def test_round_trip_persistence_equivalence(self):
        """Test that serialize -> restore produces equivalent state."""
        # Create and populate original learner
        original = HysteresisLearner(min_samples=3, max_samples=10)
        
        start_temps = [24.1, 24.3, 24.5, 24.2, 24.4]
        stop_temps = [23.5, 23.7, 23.9, 23.6, 23.8]
        
        for temp in start_temps:
            original.record_transition('start', temp)
        for temp in stop_temps:
            original.record_transition('stop', temp)
        
        # Serialize original state
        serialized_data = original.serialize_for_persistence()
        
        # Create new learner and restore from serialized data
        restored = HysteresisLearner(min_samples=3, max_samples=10)
        restored.restore_from_persistence(serialized_data)
        
        # Verify equivalence
        assert list(original._start_temps) == list(restored._start_temps)
        assert list(original._stop_temps) == list(restored._stop_temps)
        assert original.has_sufficient_data == restored.has_sufficient_data
        assert original.learned_start_threshold == restored.learned_start_threshold
        assert original.learned_stop_threshold == restored.learned_stop_threshold

    def test_round_trip_with_different_maxlen(self):
        """Test round-trip persistence with different maxlen constraints."""
        # Create original with large maxlen
        original = HysteresisLearner(min_samples=2, max_samples=10)
        
        # Add more data than the restore maxlen will allow
        for i in range(8):
            original.record_transition('start', 24.0 + i * 0.1)
            original.record_transition('stop', 23.0 + i * 0.1)
        
        # Serialize data
        serialized_data = original.serialize_for_persistence()
        
        # Restore into learner with smaller maxlen
        restored = HysteresisLearner(min_samples=2, max_samples=5)
        restored.restore_from_persistence(serialized_data)
        
        # Should only keep the first 5 items (deque handles truncation)
        assert len(restored._start_temps) == 5
        assert len(restored._stop_temps) == 5
        
        # Should still calculate thresholds correctly
        assert restored.has_sufficient_data is True
        assert restored.learned_start_threshold is not None
        assert restored.learned_stop_threshold is not None

    def test_threshold_recalculation_after_restore(self):
        """Test that thresholds are properly recalculated after restoration."""
        learner = HysteresisLearner(min_samples=3)
        
        # Add initial data manually (bypass record_transition to avoid auto-calculation)
        initial_data = {
            "start_temps": [24.0, 24.2, 24.4],
            "stop_temps": [23.0, 23.2, 23.4]
        }
        
        # Verify thresholds are None initially
        assert learner.learned_start_threshold is None
        assert learner.learned_stop_threshold is None
        
        # Restore data - should trigger threshold calculation
        learner.restore_from_persistence(initial_data)
        
        # Verify thresholds were calculated
        assert learner.learned_start_threshold == 24.2  # median of [24.0, 24.2, 24.4]
        assert learner.learned_stop_threshold == 23.2   # median of [23.0, 23.2, 23.4]
        assert learner.has_sufficient_data is True

    def test_state_consistency_after_restore(self):
        """Test that all learner state is consistent after restoration."""
        learner = HysteresisLearner(min_samples=2, max_samples=5)
        
        # Restore realistic data
        data = {
            "start_temps": [24.3, 24.1, 24.5, 24.2],
            "stop_temps": [23.7, 23.5, 23.9, 23.6]
        }
        learner.restore_from_persistence(data)
        
        # Verify all state is consistent
        assert len(learner._start_temps) == 4
        assert len(learner._stop_temps) == 4
        assert learner.has_sufficient_data is True  # Both >= min_samples (2)
        
        # Verify thresholds are calculated correctly
        expected_start_threshold = 24.25  # median of [24.1, 24.2, 24.3, 24.5]
        expected_stop_threshold = 23.65   # median of [23.5, 23.6, 23.7, 23.9]
        
        assert abs(learner.learned_start_threshold - expected_start_threshold) < 0.001
        assert abs(learner.learned_stop_threshold - expected_stop_threshold) < 0.001
        
        # Verify learner can still function normally after restore
        learner.record_transition('start', 24.6)
        assert len(learner._start_temps) == 5  # Should have added the new sample
        
        # Get hysteresis state (should work without errors)
        state = learner.get_hysteresis_state("idle", 24.0)
        assert state in ["learning_hysteresis", "active_phase", "idle_above_start_threshold", 
                        "idle_below_stop_threshold", "idle_stable_zone"]

    def test_data_integrity_with_various_float_precision(self):
        """Test that persistence handles various float precision correctly."""
        learner = HysteresisLearner()
        
        # Test data with various float precisions
        data = {
            "start_temps": [24.0, 24.123456789, 24.5, 24.1234567890123456],
            "stop_temps": [23.0, 23.987654321, 23.5, 23.9876543210987654]
        }
        
        # Restore and serialize
        learner.restore_from_persistence(data)
        serialized = learner.serialize_for_persistence()
        
        # Values should be preserved as floats
        for temp in serialized["start_temps"]:
            assert isinstance(temp, float)
        for temp in serialized["stop_temps"]:
            assert isinstance(temp, float)
        
        # Should handle the precision appropriately
        assert len(serialized["start_temps"]) == 4
        assert len(serialized["stop_temps"]) == 4