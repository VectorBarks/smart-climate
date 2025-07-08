"""Test hysteresis information display in OffsetEngine get_learning_info."""

import pytest
from unittest.mock import Mock
from custom_components.smart_climate.offset_engine import OffsetEngine, HysteresisLearner
from custom_components.smart_climate.const import (
    DEFAULT_POWER_IDLE_THRESHOLD,
    DEFAULT_POWER_MIN_THRESHOLD,
    DEFAULT_POWER_MAX_THRESHOLD,
)


class TestOffsetEngineHysteresisInfo:
    """Test hysteresis data inclusion in get_learning_info method."""

    def test_get_learning_info_includes_hysteresis_when_enabled(self):
        """Test that get_learning_info returns hysteresis data when power sensor configured."""
        # GIVEN: OffsetEngine with power sensor configured (hysteresis enabled)
        config = {
            "power_sensor": "sensor.ac_power",
            "enable_learning": True,
            "power_idle_threshold": DEFAULT_POWER_IDLE_THRESHOLD,
            "power_min_threshold": DEFAULT_POWER_MIN_THRESHOLD,
            "power_max_threshold": DEFAULT_POWER_MAX_THRESHOLD,
        }
        engine = OffsetEngine(config)
        
        # Mock the hysteresis learner with some test data
        engine._hysteresis_learner._start_temps.extend([25.5, 26.0, 25.8])
        engine._hysteresis_learner._stop_temps.extend([23.0, 22.8, 23.2])
        engine._hysteresis_learner._update_thresholds()
        
        # WHEN: get_learning_info is called
        info = engine.get_learning_info()
        
        # THEN: Hysteresis data should be included
        assert "hysteresis_enabled" in info
        assert info["hysteresis_enabled"] is True
        assert "hysteresis_state" in info
        assert info["hysteresis_state"] == "learning_hysteresis"  # Not enough samples yet
        assert "learned_start_threshold" in info
        assert info["learned_start_threshold"] is None  # Not enough samples
        assert "learned_stop_threshold" in info
        assert info["learned_stop_threshold"] is None  # Not enough samples
        assert "temperature_window" in info
        assert info["temperature_window"] is None  # Can't calculate without thresholds
        assert "start_samples_collected" in info
        assert info["start_samples_collected"] == 3
        assert "stop_samples_collected" in info
        assert info["stop_samples_collected"] == 3
        assert "hysteresis_ready" in info
        assert info["hysteresis_ready"] is False  # Not enough samples

    def test_get_learning_info_hysteresis_disabled_without_power_sensor(self):
        """Test that hysteresis data shows disabled when no power sensor configured."""
        # GIVEN: OffsetEngine without power sensor (hysteresis disabled)
        config = {
            "enable_learning": True,
        }
        engine = OffsetEngine(config)
        
        # WHEN: get_learning_info is called
        info = engine.get_learning_info()
        
        # THEN: Hysteresis should be marked as disabled
        assert info["hysteresis_enabled"] is False
        assert info["hysteresis_state"] == "disabled"
        assert info["learned_start_threshold"] is None
        assert info["learned_stop_threshold"] is None
        assert info["temperature_window"] is None
        assert info["start_samples_collected"] == 0
        assert info["stop_samples_collected"] == 0
        assert info["hysteresis_ready"] is False

    def test_get_learning_info_with_sufficient_hysteresis_data(self):
        """Test hysteresis info when sufficient samples collected."""
        # GIVEN: OffsetEngine with power sensor and sufficient data
        config = {
            "power_sensor": "sensor.ac_power",
            "enable_learning": True,
        }
        engine = OffsetEngine(config)
        
        # Add sufficient samples (min_samples = 5 by default)
        start_temps = [25.5, 26.0, 25.8, 25.9, 26.1]
        stop_temps = [23.0, 22.8, 23.2, 23.1, 22.9]
        engine._hysteresis_learner._start_temps.extend(start_temps)
        engine._hysteresis_learner._stop_temps.extend(stop_temps)
        engine._hysteresis_learner._update_thresholds()
        
        # WHEN: get_learning_info is called
        info = engine.get_learning_info()
        
        # THEN: Full hysteresis data should be available
        assert info["hysteresis_enabled"] is True
        assert info["hysteresis_state"] == "ready"  # Sufficient data
        assert info["learned_start_threshold"] == 25.9  # Median of start temps
        assert info["learned_stop_threshold"] == 23.0  # Median of stop temps
        assert info["temperature_window"] == 2.9  # 25.9 - 23.0
        assert info["start_samples_collected"] == 5
        assert info["stop_samples_collected"] == 5
        assert info["hysteresis_ready"] is True

    def test_get_learning_info_formats_thresholds_to_two_decimals(self):
        """Test that temperature thresholds are formatted to 2 decimal places."""
        # GIVEN: OffsetEngine with precise threshold values
        config = {
            "power_sensor": "sensor.ac_power",
            "enable_learning": True,
        }
        engine = OffsetEngine(config)
        
        # Set up learner with values that would have many decimals
        engine._hysteresis_learner._start_temps.extend([25.333, 25.666, 25.999, 25.111, 25.555])
        engine._hysteresis_learner._stop_temps.extend([22.777, 22.888, 22.999, 22.111, 22.222])
        engine._hysteresis_learner._update_thresholds()
        
        # WHEN: get_learning_info is called
        info = engine.get_learning_info()
        
        # THEN: Thresholds should be formatted to 2 decimals
        assert isinstance(info["learned_start_threshold"], float)
        assert isinstance(info["learned_stop_threshold"], float)
        # Check formatting by converting back to string
        assert f"{info['learned_start_threshold']:.2f}" == str(info["learned_start_threshold"])
        assert f"{info['learned_stop_threshold']:.2f}" == str(info["learned_stop_threshold"])
        assert isinstance(info["temperature_window"], float)

    def test_get_learning_info_handles_edge_case_no_samples(self):
        """Test hysteresis info with no samples collected."""
        # GIVEN: OffsetEngine with power sensor but no data
        config = {
            "power_sensor": "sensor.ac_power",
            "enable_learning": True,
        }
        engine = OffsetEngine(config)
        
        # WHEN: get_learning_info is called (no samples added)
        info = engine.get_learning_info()
        
        # THEN: Should handle gracefully
        assert info["hysteresis_enabled"] is True
        assert info["hysteresis_state"] == "learning_hysteresis"
        assert info["learned_start_threshold"] is None
        assert info["learned_stop_threshold"] is None
        assert info["temperature_window"] is None
        assert info["start_samples_collected"] == 0
        assert info["stop_samples_collected"] == 0
        assert info["hysteresis_ready"] is False

    def test_get_learning_info_handles_partial_data(self):
        """Test hysteresis info when only one type of transition recorded."""
        # GIVEN: OffsetEngine with only start transitions recorded
        config = {
            "power_sensor": "sensor.ac_power",
            "enable_learning": True,
        }
        engine = OffsetEngine(config)
        
        # Add only start temps (no stop temps)
        engine._hysteresis_learner._start_temps.extend([25.5, 26.0, 25.8, 25.9, 26.1])
        engine._hysteresis_learner._update_thresholds()
        
        # WHEN: get_learning_info is called
        info = engine.get_learning_info()
        
        # THEN: Should show partial data state
        assert info["hysteresis_enabled"] is True
        assert info["hysteresis_state"] == "learning_hysteresis"  # Not ready
        assert info["learned_start_threshold"] is None  # Need both types
        assert info["learned_stop_threshold"] is None
        assert info["temperature_window"] is None
        assert info["start_samples_collected"] == 5
        assert info["stop_samples_collected"] == 0
        assert info["hysteresis_ready"] is False

    def test_get_learning_info_without_learning_enabled(self):
        """Test that hysteresis info is still included even if learning is disabled."""
        # GIVEN: OffsetEngine with power sensor but learning disabled
        config = {
            "power_sensor": "sensor.ac_power",
            "enable_learning": False,
        }
        engine = OffsetEngine(config)
        
        # WHEN: get_learning_info is called
        info = engine.get_learning_info()
        
        # THEN: Basic info should show learning disabled, but hysteresis info included
        assert info["enabled"] is False
        assert info["samples"] == 0
        # Hysteresis info should still be present
        assert "hysteresis_enabled" in info
        assert info["hysteresis_enabled"] is True
        assert "hysteresis_state" in info

    def test_get_learning_info_exception_handling(self):
        """Test that get_learning_info handles exceptions gracefully."""
        # GIVEN: OffsetEngine with mocked hysteresis learner that throws
        config = {
            "power_sensor": "sensor.ac_power",
            "enable_learning": True,
        }
        engine = OffsetEngine(config)
        
        # Mock the hysteresis learner to raise an exception
        engine._hysteresis_learner = Mock()
        engine._hysteresis_learner.has_sufficient_data = property(lambda self: True)
        engine._hysteresis_learner.learned_start_threshold = property(
            lambda self: (_ for _ in ()).throw(ValueError("Test exception"))
        )
        
        # WHEN: get_learning_info is called
        info = engine.get_learning_info()
        
        # THEN: Should return safe defaults
        assert "error" in info
        assert "hysteresis_enabled" in info  # Should still try to include what it can
        # Basic learning info should be present
        assert info["enabled"] is True
        assert info["samples"] == 0