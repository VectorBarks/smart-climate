"""Test suite for HysteresisLearner.get_hysteresis_state() method."""

import pytest
from custom_components.smart_climate.offset_engine import HysteresisLearner


class TestHysteresisStateDetection:
    """Test the hysteresis state detection logic."""

    def test_learning_hysteresis_insufficient_data(self):
        """Test that learning_hysteresis is returned when insufficient data."""
        learner = HysteresisLearner(min_samples=5)
        
        # Add insufficient data (less than min_samples for either start or stop)
        for i in range(3):
            learner.record_transition('start', 24.0 + i * 0.1)
            learner.record_transition('stop', 23.0 + i * 0.1)
        
        # Should return learning_hysteresis for any power state
        assert learner.get_hysteresis_state("idle", 24.0) == "learning_hysteresis"
        assert learner.get_hysteresis_state("low", 24.0) == "learning_hysteresis" 
        assert learner.get_hysteresis_state("moderate", 24.0) == "learning_hysteresis"
        assert learner.get_hysteresis_state("high", 24.0) == "learning_hysteresis"

    def test_learning_hysteresis_no_data(self):
        """Test that learning_hysteresis is returned when no data at all."""
        learner = HysteresisLearner()
        
        # No data recorded
        assert learner.has_sufficient_data is False
        
        # Should return learning_hysteresis for any combination
        assert learner.get_hysteresis_state("idle", 23.5) == "learning_hysteresis"
        assert learner.get_hysteresis_state("high", 25.0) == "learning_hysteresis"

    def test_active_phase_moderate_power(self):
        """Test that active_phase is returned for moderate power state."""
        learner = HysteresisLearner(min_samples=3)
        
        # Add sufficient data to enable threshold detection
        for i in range(5):
            learner.record_transition('start', 24.3 + i * 0.1)
            learner.record_transition('stop', 23.7 + i * 0.1)
        
        # Verify we have sufficient data
        assert learner.has_sufficient_data is True
        
        # Moderate power should return active_phase regardless of temperature
        assert learner.get_hysteresis_state("moderate", 22.0) == "active_phase"
        assert learner.get_hysteresis_state("moderate", 24.0) == "active_phase"
        assert learner.get_hysteresis_state("moderate", 26.0) == "active_phase"

    def test_active_phase_high_power(self):
        """Test that active_phase is returned for high power state."""
        learner = HysteresisLearner(min_samples=3)
        
        # Add sufficient data
        for i in range(5):
            learner.record_transition('start', 24.3 + i * 0.1)
            learner.record_transition('stop', 23.7 + i * 0.1)
        
        # High power should return active_phase regardless of temperature
        assert learner.get_hysteresis_state("high", 22.0) == "active_phase"
        assert learner.get_hysteresis_state("high", 24.0) == "active_phase"
        assert learner.get_hysteresis_state("high", 26.0) == "active_phase"

    def test_idle_above_start_threshold(self):
        """Test detection when AC is idle but room temp is above start threshold."""
        learner = HysteresisLearner(min_samples=3)
        
        # Add data: start threshold will be median of [24.1, 24.2, 24.3, 24.4, 24.5] = 24.3
        # stop threshold will be median of [23.5, 23.6, 23.7, 23.8, 23.9] = 23.7
        start_temps = [24.1, 24.2, 24.3, 24.4, 24.5]
        stop_temps = [23.5, 23.6, 23.7, 23.8, 23.9]
        
        for temp in start_temps:
            learner.record_transition('start', temp)
        for temp in stop_temps:
            learner.record_transition('stop', temp)
        
        # Verify thresholds calculated correctly
        assert learner.learned_start_threshold == 24.3
        assert learner.learned_stop_threshold == 23.7
        
        # Room temperature above start threshold with idle/low power
        assert learner.get_hysteresis_state("idle", 24.5) == "idle_above_start_threshold"
        assert learner.get_hysteresis_state("low", 24.4) == "idle_above_start_threshold"
        assert learner.get_hysteresis_state("idle", 25.0) == "idle_above_start_threshold"

    def test_idle_below_stop_threshold(self):
        """Test detection when AC is idle and room temp is below stop threshold."""
        learner = HysteresisLearner(min_samples=3)
        
        # Same threshold setup: start=24.3, stop=23.7
        start_temps = [24.1, 24.2, 24.3, 24.4, 24.5]
        stop_temps = [23.5, 23.6, 23.7, 23.8, 23.9]
        
        for temp in start_temps:
            learner.record_transition('start', temp)
        for temp in stop_temps:
            learner.record_transition('stop', temp)
        
        # Room temperature below stop threshold with idle/low power
        assert learner.get_hysteresis_state("idle", 23.5) == "idle_below_stop_threshold"
        assert learner.get_hysteresis_state("low", 23.6) == "idle_below_stop_threshold"
        assert learner.get_hysteresis_state("idle", 23.0) == "idle_below_stop_threshold"

    def test_idle_stable_zone(self):
        """Test detection when AC is idle and room temp is in stable zone."""
        learner = HysteresisLearner(min_samples=3)
        
        # Same threshold setup: start=24.3, stop=23.7
        start_temps = [24.1, 24.2, 24.3, 24.4, 24.5]
        stop_temps = [23.5, 23.6, 23.7, 23.8, 23.9]
        
        for temp in start_temps:
            learner.record_transition('start', temp)
        for temp in stop_temps:
            learner.record_transition('stop', temp)
        
        # Room temperature between stop and start thresholds (23.7 < temp < 24.3)
        assert learner.get_hysteresis_state("idle", 23.8) == "idle_stable_zone"
        assert learner.get_hysteresis_state("low", 24.0) == "idle_stable_zone"
        assert learner.get_hysteresis_state("idle", 24.2) == "idle_stable_zone"
        
        # Boundary conditions (exactly at thresholds should be stable zone)
        assert learner.get_hysteresis_state("idle", 23.7) == "idle_stable_zone"
        assert learner.get_hysteresis_state("idle", 24.3) == "idle_stable_zone"

    def test_edge_case_none_thresholds(self):
        """Test edge case where thresholds are None despite sufficient data."""
        learner = HysteresisLearner(min_samples=3)
        
        # Manually set thresholds to None (edge case)
        learner._start_temps.extend([24.1, 24.2, 24.3])
        learner._stop_temps.extend([23.5, 23.6, 23.7])
        learner.learned_start_threshold = None
        learner.learned_stop_threshold = None
        
        # Should handle gracefully and return learning_hysteresis
        assert learner.get_hysteresis_state("idle", 24.0) == "learning_hysteresis"

    def test_edge_case_invalid_power_state(self):
        """Test behavior with invalid/unknown power states."""
        learner = HysteresisLearner(min_samples=3)
        
        # Add sufficient data
        for i in range(5):
            learner.record_transition('start', 24.3 + i * 0.1)
            learner.record_transition('stop', 23.7 + i * 0.1)
        
        # Invalid power states should be treated as idle (fallback)
        # Note: start_threshold=24.5, stop_threshold=23.9 for this data set
        assert learner.get_hysteresis_state("unknown", 24.6) == "idle_above_start_threshold"  # Above start
        assert learner.get_hysteresis_state("invalid", 23.8) == "idle_below_stop_threshold"   # Below stop  
        assert learner.get_hysteresis_state("", 24.0) == "idle_stable_zone"                   # In zone
        assert learner.get_hysteresis_state(None, 24.2) == "idle_stable_zone"                 # In zone

    def test_boundary_temperature_conditions(self):
        """Test behavior at exact boundary temperatures."""
        learner = HysteresisLearner(min_samples=3)
        
        # Set up precise thresholds: start=24.0, stop=23.0
        start_temps = [24.0, 24.0, 24.0]
        stop_temps = [23.0, 23.0, 23.0]
        
        for temp in start_temps:
            learner.record_transition('start', temp)
        for temp in stop_temps:
            learner.record_transition('stop', temp)
        
        assert learner.learned_start_threshold == 24.0
        assert learner.learned_stop_threshold == 23.0
        
        # Test exact boundary conditions
        assert learner.get_hysteresis_state("idle", 24.1) == "idle_above_start_threshold"  # Above start
        assert learner.get_hysteresis_state("idle", 24.0) == "idle_stable_zone"           # At start
        assert learner.get_hysteresis_state("idle", 23.5) == "idle_stable_zone"           # Between
        assert learner.get_hysteresis_state("idle", 23.0) == "idle_stable_zone"           # At stop
        assert learner.get_hysteresis_state("idle", 22.9) == "idle_below_stop_threshold"  # Below stop

    def test_comprehensive_state_matrix(self):
        """Test comprehensive matrix of power states and temperature ranges."""
        learner = HysteresisLearner(min_samples=2)
        
        # Simple threshold setup: start=25.0, stop=24.0
        learner.record_transition('start', 25.0)
        learner.record_transition('start', 25.0)
        learner.record_transition('stop', 24.0)
        learner.record_transition('stop', 24.0)
        
        assert learner.learned_start_threshold == 25.0
        assert learner.learned_stop_threshold == 24.0
        
        # Test matrix: [power_state, temperature, expected_result]
        test_cases = [
            # Active phase cases
            ("moderate", 23.0, "active_phase"),
            ("moderate", 24.5, "active_phase"),
            ("moderate", 26.0, "active_phase"),
            ("high", 23.0, "active_phase"),
            ("high", 24.5, "active_phase"),
            ("high", 26.0, "active_phase"),
            
            # Idle state cases  
            ("idle", 25.1, "idle_above_start_threshold"),    # Above start
            ("idle", 24.5, "idle_stable_zone"),              # Between thresholds
            ("idle", 23.9, "idle_below_stop_threshold"),     # Below stop
            ("low", 25.5, "idle_above_start_threshold"),     # Low power above start
            ("low", 24.2, "idle_stable_zone"),               # Low power in zone
            ("low", 23.5, "idle_below_stop_threshold"),      # Low power below stop
        ]
        
        for power_state, temp, expected in test_cases:
            result = learner.get_hysteresis_state(power_state, temp)
            assert result == expected, f"Failed for {power_state}, {temp}°C: got {result}, expected {expected}"