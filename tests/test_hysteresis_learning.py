"""Test suite for HysteresisLearner threshold calculation logic."""

import pytest
import statistics
from collections import deque
from custom_components.smart_climate.offset_engine import HysteresisLearner


class TestHysteresisLearnerThresholds:
    """Test HysteresisLearner threshold calculation functionality."""

    def test_start_threshold_median_calculation(self):
        """Test that start threshold is calculated as median of start temperatures."""
        learner = HysteresisLearner(min_samples=3, max_samples=10)
        
        # Record enough start samples to enable threshold calculation
        start_temps = [24.1, 24.3, 24.2, 24.0, 24.4]
        for temp in start_temps:
            learner.record_transition('start', temp)
        
        # Record sufficient stop samples too
        stop_temps = [23.7, 23.8, 23.6]
        for temp in stop_temps:
            learner.record_transition('stop', temp)
        
        # Verify start threshold equals median of start temperatures
        expected_start_threshold = statistics.median(start_temps)
        assert learner.learned_start_threshold == expected_start_threshold
        assert learner.learned_start_threshold == 24.2  # Median of [24.1, 24.3, 24.2, 24.0, 24.4]

    def test_stop_threshold_median_calculation(self):
        """Test that stop threshold is calculated as median of stop temperatures."""
        learner = HysteresisLearner(min_samples=3, max_samples=10)
        
        # Record sufficient start samples
        start_temps = [24.1, 24.3, 24.2]
        for temp in start_temps:
            learner.record_transition('start', temp)
        
        # Record enough stop samples to enable threshold calculation
        stop_temps = [23.7, 23.8, 23.6, 23.9, 23.5]
        for temp in stop_temps:
            learner.record_transition('stop', temp)
        
        # Verify stop threshold equals median of stop temperatures
        expected_stop_threshold = statistics.median(stop_temps)
        assert learner.learned_stop_threshold == expected_stop_threshold
        assert learner.learned_stop_threshold == 23.7  # Median of [23.7, 23.8, 23.6, 23.9, 23.5]

    def test_threshold_updates_on_new_samples(self):
        """Test that thresholds are recalculated when new samples are added."""
        learner = HysteresisLearner(min_samples=3, max_samples=10)
        
        # Add initial samples
        initial_start_temps = [24.0, 24.2, 24.1]
        initial_stop_temps = [23.5, 23.7, 23.6]
        
        for temp in initial_start_temps:
            learner.record_transition('start', temp)
        for temp in initial_stop_temps:
            learner.record_transition('stop', temp)
        
        # Verify initial thresholds
        initial_start_threshold = learner.learned_start_threshold
        initial_stop_threshold = learner.learned_stop_threshold
        assert initial_start_threshold == 24.1  # Median of [24.0, 24.2, 24.1]
        assert initial_stop_threshold == 23.6   # Median of [23.5, 23.7, 23.6]
        
        # Add new samples that should change the median
        learner.record_transition('start', 24.5)  # [24.0, 24.2, 24.1, 24.5] -> median = 24.15
        learner.record_transition('stop', 23.9)   # [23.5, 23.7, 23.6, 23.9] -> median = 23.65
        
        # Verify thresholds were updated
        assert learner.learned_start_threshold != initial_start_threshold
        assert learner.learned_stop_threshold != initial_stop_threshold
        assert learner.learned_start_threshold == 24.15  # Median of [24.0, 24.2, 24.1, 24.5]
        assert learner.learned_stop_threshold == 23.65   # Median of [23.5, 23.7, 23.6, 23.9]

    def test_deque_max_size_enforcement(self):
        """Test that deque enforces max_size and old samples are removed."""
        learner = HysteresisLearner(min_samples=3, max_samples=5)
        
        # Add more samples than max_size to start deque
        start_temps = [24.0, 24.1, 24.2, 24.3, 24.4, 24.5, 24.6]  # 7 samples, max is 5
        stop_temps = [23.5, 23.6, 23.7]  # Enough for has_sufficient_data
        
        for temp in start_temps:
            learner.record_transition('start', temp)
        for temp in stop_temps:
            learner.record_transition('stop', temp)
        
        # Verify only last 5 start samples are kept
        assert len(learner._start_temps) == 5
        expected_start_temps = start_temps[-5:]  # [24.2, 24.3, 24.4, 24.5, 24.6]
        assert list(learner._start_temps) == expected_start_temps
        
        # Verify threshold calculated from only the kept samples
        expected_threshold = statistics.median(expected_start_temps)
        assert learner.learned_start_threshold == expected_threshold
        assert learner.learned_start_threshold == 24.4  # Median of last 5 samples

    def test_invalid_transition_types_ignored(self):
        """Test that invalid transition types are ignored gracefully."""
        learner = HysteresisLearner(min_samples=3, max_samples=10)
        
        # Add valid samples first
        valid_start_temps = [24.0, 24.1, 24.2]
        valid_stop_temps = [23.5, 23.6, 23.7]
        
        for temp in valid_start_temps:
            learner.record_transition('start', temp)
        for temp in valid_stop_temps:
            learner.record_transition('stop', temp)
        
        initial_start_count = len(learner._start_temps)
        initial_stop_count = len(learner._stop_temps)
        initial_start_threshold = learner.learned_start_threshold
        initial_stop_threshold = learner.learned_stop_threshold
        
        # Try invalid transition types
        learner.record_transition('invalid_type', 25.0)
        learner.record_transition('', 25.0)
        learner.record_transition(None, 25.0)
        
        # Verify no samples were added and thresholds unchanged
        assert len(learner._start_temps) == initial_start_count
        assert len(learner._stop_temps) == initial_stop_count
        assert learner.learned_start_threshold == initial_start_threshold
        assert learner.learned_stop_threshold == initial_stop_threshold

    def test_threshold_stability_with_outliers(self):
        """Test that median-based thresholds are robust against outlier values."""
        learner = HysteresisLearner(min_samples=3, max_samples=10)
        
        # Add normal samples
        normal_start_temps = [24.0, 24.1, 24.2, 24.1, 24.0]
        normal_stop_temps = [23.5, 23.6, 23.7, 23.6, 23.5]
        
        for temp in normal_start_temps:
            learner.record_transition('start', temp)
        for temp in normal_stop_temps:
            learner.record_transition('stop', temp)
        
        # Verify normal thresholds
        normal_start_threshold = learner.learned_start_threshold
        normal_stop_threshold = learner.learned_stop_threshold
        assert normal_start_threshold == 24.1  # Median of normal values
        assert normal_stop_threshold == 23.6   # Median of normal values
        
        # Add extreme outliers
        learner.record_transition('start', 30.0)  # Extreme outlier
        learner.record_transition('start', 10.0)  # Extreme outlier  
        learner.record_transition('stop', 30.0)   # Extreme outlier
        learner.record_transition('stop', 10.0)   # Extreme outlier
        
        # Verify thresholds are still reasonable (median is robust to outliers)
        # With outliers, start temps are: [24.0, 24.1, 24.2, 24.1, 24.0, 30.0, 10.0]
        # Median should still be close to normal range
        assert abs(learner.learned_start_threshold - normal_start_threshold) < 1.0
        assert abs(learner.learned_stop_threshold - normal_stop_threshold) < 1.0

    def test_insufficient_data_thresholds_none(self):
        """Test that thresholds remain None when insufficient data is available."""
        learner = HysteresisLearner(min_samples=5, max_samples=10)
        
        # Add insufficient start samples
        learner.record_transition('start', 24.0)
        learner.record_transition('start', 24.1)
        # Only 2 start samples, need 5
        
        # Add insufficient stop samples  
        learner.record_transition('stop', 23.5)
        learner.record_transition('stop', 23.6)
        learner.record_transition('stop', 23.7)
        # Only 3 stop samples, need 5
        
        # Verify thresholds are None due to insufficient data
        assert learner.learned_start_threshold is None
        assert learner.learned_stop_threshold is None
        assert not learner.has_sufficient_data

    def test_sufficient_data_one_type_insufficient_other(self):
        """Test thresholds remain None if only one type has sufficient data."""
        learner = HysteresisLearner(min_samples=3, max_samples=10)
        
        # Add sufficient start samples
        start_temps = [24.0, 24.1, 24.2, 24.3]
        for temp in start_temps:
            learner.record_transition('start', temp)
        
        # Add insufficient stop samples
        learner.record_transition('stop', 23.5)
        learner.record_transition('stop', 23.6)
        # Only 2 stop samples, need 3
        
        # Verify thresholds are None because stop data is insufficient
        assert learner.learned_start_threshold is None
        assert learner.learned_stop_threshold is None
        assert not learner.has_sufficient_data

    def test_empty_deques_no_calculation(self):
        """Test behavior with empty deques."""
        learner = HysteresisLearner(min_samples=1, max_samples=10)
        
        # No samples added
        assert len(learner._start_temps) == 0
        assert len(learner._stop_temps) == 0
        assert learner.learned_start_threshold is None
        assert learner.learned_stop_threshold is None
        assert not learner.has_sufficient_data

    def test_single_value_median(self):
        """Test median calculation with single values in each deque."""
        learner = HysteresisLearner(min_samples=1, max_samples=10)
        
        # Add single samples
        learner.record_transition('start', 24.5)
        learner.record_transition('stop', 23.5)
        
        # With min_samples=1, thresholds should be calculated
        assert learner.learned_start_threshold == 24.5
        assert learner.learned_stop_threshold == 23.5
        assert learner.has_sufficient_data

    def test_record_transition_calls_update_thresholds(self):
        """Test that record_transition calls _update_thresholds after appending."""
        learner = HysteresisLearner(min_samples=2, max_samples=10)
        
        # Add first sample - should not trigger threshold calculation yet
        learner.record_transition('start', 24.0)
        learner.record_transition('stop', 23.0) 
        assert learner.learned_start_threshold is None
        assert learner.learned_stop_threshold is None
        
        # Add second samples - should trigger threshold calculation
        learner.record_transition('start', 24.1)
        learner.record_transition('stop', 23.1)
        
        # Now should have sufficient data and calculated thresholds
        assert learner.has_sufficient_data
        assert learner.learned_start_threshold is not None
        assert learner.learned_stop_threshold is not None
        assert learner.learned_start_threshold == 24.05  # Median of [24.0, 24.1]
        assert learner.learned_stop_threshold == 23.05   # Median of [23.0, 23.1]