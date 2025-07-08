"""Test suite for HysteresisLearner class."""

import pytest
from collections import deque
from custom_components.smart_climate.offset_engine import HysteresisLearner


class TestHysteresisLearner:
    """Test the HysteresisLearner class functionality."""

    def test_initialization_with_defaults(self):
        """Test that HysteresisLearner initializes with correct default values."""
        learner = HysteresisLearner()
        
        # Check default parameters
        assert learner._min_samples == 5
        assert isinstance(learner._start_temps, deque)
        assert isinstance(learner._stop_temps, deque)
        assert learner._start_temps.maxlen == 50  # default max_samples
        assert learner._stop_temps.maxlen == 50
        
        # Check initial threshold values
        assert learner.learned_start_threshold is None
        assert learner.learned_stop_threshold is None

    def test_initialization_with_custom_params(self):
        """Test that HysteresisLearner accepts custom initialization parameters."""
        learner = HysteresisLearner(min_samples=10, max_samples=100)
        
        # Check custom parameters
        assert learner._min_samples == 10
        assert learner._start_temps.maxlen == 100
        assert learner._stop_temps.maxlen == 100
        
        # Check thresholds still None initially
        assert learner.learned_start_threshold is None
        assert learner.learned_stop_threshold is None

    def test_has_sufficient_data_false_initially(self):
        """Test that has_sufficient_data returns False when insufficient samples."""
        learner = HysteresisLearner(min_samples=5)
        
        # Initially should be False
        assert learner.has_sufficient_data is False
        
        # Add some start temps but not enough stop temps
        for i in range(5):
            learner._start_temps.append(24.0 + i * 0.1)
        # Still False - need both start AND stop samples
        assert learner.has_sufficient_data is False
        
        # Add some stop temps but still not enough
        for i in range(3):
            learner._stop_temps.append(23.0 + i * 0.1)
        # Still False - stop temps < min_samples
        assert learner.has_sufficient_data is False

    def test_has_sufficient_data_true_after_min_samples(self):
        """Test that has_sufficient_data returns True when both start and stop have sufficient samples."""
        learner = HysteresisLearner(min_samples=3)
        
        # Add sufficient start temps
        for i in range(3):
            learner._start_temps.append(24.0 + i * 0.1)
        
        # Add sufficient stop temps
        for i in range(3):
            learner._stop_temps.append(23.0 + i * 0.1)
        
        # Now should be True
        assert learner.has_sufficient_data is True

    def test_record_transition_start(self):
        """Test recording start transitions (idle/low -> moderate/high power)."""
        learner = HysteresisLearner()
        
        # Record start transition
        learner.record_transition('start', 24.5)
        
        # Check that start temp was recorded
        assert len(learner._start_temps) == 1
        assert learner._start_temps[0] == 24.5
        assert len(learner._stop_temps) == 0  # Stop temps unchanged

    def test_record_transition_stop(self):
        """Test recording stop transitions (moderate/high -> idle/low power)."""
        learner = HysteresisLearner()
        
        # Record stop transition
        learner.record_transition('stop', 23.5)
        
        # Check that stop temp was recorded
        assert len(learner._stop_temps) == 1
        assert learner._stop_temps[0] == 23.5
        assert len(learner._start_temps) == 0  # Start temps unchanged

    def test_learned_thresholds_none_initially(self):
        """Test that learned thresholds remain None until sufficient data and _update_thresholds is called."""
        learner = HysteresisLearner()
        
        # Initially None
        assert learner.learned_start_threshold is None
        assert learner.learned_stop_threshold is None
        
        # Add some data but insufficient for thresholds
        learner.record_transition('start', 24.5)
        learner.record_transition('stop', 23.5)
        
        # Should still be None (insufficient data)
        assert learner.learned_start_threshold is None
        assert learner.learned_stop_threshold is None

    def test_learned_thresholds_calculated_with_sufficient_data(self):
        """Test that thresholds are calculated as median when sufficient data is available."""
        learner = HysteresisLearner(min_samples=3)
        
        # Add sufficient start temperatures
        start_temps = [24.2, 24.4, 24.3, 24.1, 24.5]
        for temp in start_temps:
            learner.record_transition('start', temp)
        
        # Add sufficient stop temperatures  
        stop_temps = [23.6, 23.8, 23.7, 23.5, 23.9]
        for temp in stop_temps:
            learner.record_transition('stop', temp)
        
        # Thresholds should now be calculated as medians
        assert learner.learned_start_threshold == 24.3  # median of start temps
        assert learner.learned_stop_threshold == 23.7   # median of stop temps

    def test_serialize_for_persistence(self):
        """Test serialization of learner state for persistence."""
        learner = HysteresisLearner()
        
        # Add some data
        learner.record_transition('start', 24.5)
        learner.record_transition('start', 24.3)
        learner.record_transition('stop', 23.7)
        
        # Serialize
        data = learner.serialize_for_persistence()
        
        # Check structure
        assert isinstance(data, dict)
        assert "start_temps" in data
        assert "stop_temps" in data
        assert data["start_temps"] == [24.5, 24.3]
        assert data["stop_temps"] == [23.7]

    def test_restore_from_persistence(self):
        """Test restoration of learner state from persistence data."""
        learner = HysteresisLearner(min_samples=2)
        
        # Restore from persistence data
        data = {
            "start_temps": [24.2, 24.4],
            "stop_temps": [23.6, 23.8]
        }
        learner.restore_from_persistence(data)
        
        # Check that data was restored
        assert list(learner._start_temps) == [24.2, 24.4]
        assert list(learner._stop_temps) == [23.6, 23.8]
        
        # Check that thresholds were calculated
        assert learner.has_sufficient_data is True
        assert abs(learner.learned_start_threshold - 24.3) < 0.001  # median of [24.2, 24.4]
        assert abs(learner.learned_stop_threshold - 23.7) < 0.001   # median of [23.6, 23.8]