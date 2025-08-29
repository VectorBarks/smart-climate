"""Tests for CompressorStateAnalyzer component.

ABOUTME: Tests for the Quiet Mode CompressorStateAnalyzer that detects compressor states
and determines when adjustments would activate the compressor.
"""

import pytest
from unittest.mock import Mock
from custom_components.smart_climate.compressor_state_analyzer import CompressorStateAnalyzer
from custom_components.smart_climate.offset_engine import HysteresisLearner


class TestCompressorStateAnalyzer:
    """Test the CompressorStateAnalyzer class functionality."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.analyzer = CompressorStateAnalyzer()
        self.analyzer_custom_threshold = CompressorStateAnalyzer(power_threshold=75.0)
        
        # Create mock hysteresis learner with known thresholds
        self.mock_hysteresis_learner = Mock(spec=HysteresisLearner)
        self.mock_hysteresis_learner.learned_start_threshold = 22.0  # Compressor starts at 22°C
        self.mock_hysteresis_learner.learned_stop_threshold = 24.0   # Compressor stops at 24°C

    def test_analyzer_detects_compressor_idle_state(self):
        """Test that power consumption below threshold is detected as idle."""
        # Test default threshold (50W)
        assert self.analyzer.is_compressor_idle(0.0) is True
        assert self.analyzer.is_compressor_idle(25.0) is True
        assert self.analyzer.is_compressor_idle(49.9) is True
        
        # Test custom threshold (75W)
        assert self.analyzer_custom_threshold.is_compressor_idle(74.9) is True
        assert self.analyzer_custom_threshold.is_compressor_idle(50.0) is True

    def test_analyzer_detects_compressor_active_state(self):
        """Test that power consumption at or above threshold is detected as active."""
        # Test default threshold (50W)
        assert self.analyzer.is_compressor_idle(50.0) is False
        assert self.analyzer.is_compressor_idle(75.0) is False
        assert self.analyzer.is_compressor_idle(150.0) is False
        
        # Test custom threshold (75W)  
        assert self.analyzer_custom_threshold.is_compressor_idle(75.0) is False
        assert self.analyzer_custom_threshold.is_compressor_idle(100.0) is False

    def test_would_activate_compressor_when_below_start_threshold(self):
        """Test detection when adjustment would activate compressor (cooling modes)."""
        current_room_temp = 25.0  # Above start threshold
        new_setpoint = 21.0       # Below start threshold - should activate
        
        # Test COOL mode
        result = self.analyzer.would_adjustment_activate_compressor(
            current_room_temp, new_setpoint, self.mock_hysteresis_learner, "cool"
        )
        assert result is True
        
        # Test DRY mode
        result = self.analyzer.would_adjustment_activate_compressor(
            current_room_temp, new_setpoint, self.mock_hysteresis_learner, "dry"
        )
        assert result is True
        
        # Test AUTO mode
        result = self.analyzer.would_adjustment_activate_compressor(
            current_room_temp, new_setpoint, self.mock_hysteresis_learner, "auto"
        )
        assert result is True

    def test_would_not_activate_when_above_start_threshold(self):
        """Test that adjustment above start threshold won't activate compressor."""
        current_room_temp = 25.0  # Above start threshold
        new_setpoint = 23.0       # Above start threshold - should not activate
        
        result = self.analyzer.would_adjustment_activate_compressor(
            current_room_temp, new_setpoint, self.mock_hysteresis_learner, "cool"
        )
        assert result is False

    def test_handles_unknown_thresholds_gracefully(self):
        """Test behavior when hysteresis thresholds are not learned yet."""
        # Create learner without learned thresholds
        unknown_learner = Mock(spec=HysteresisLearner)
        unknown_learner.learned_start_threshold = None
        unknown_learner.learned_stop_threshold = None
        
        result = self.analyzer.would_adjustment_activate_compressor(
            25.0, 21.0, unknown_learner, "cool"
        )
        assert result is None
        
        # Test get_adjustment_needed_to_activate with unknown thresholds
        adjustment_needed = self.analyzer.get_adjustment_needed_to_activate(
            25.0, unknown_learner, "cool"
        )
        assert adjustment_needed is None

    def test_calculates_required_adjustment_to_activate(self):
        """Test calculation of setpoint needed to activate compressor."""
        current_room_temp = 25.0  # Above start threshold (22.0)
        
        # Should return the start threshold to activate compressor
        result = self.analyzer.get_adjustment_needed_to_activate(
            current_room_temp, self.mock_hysteresis_learner, "cool"
        )
        assert result == 22.0  # The learned start threshold
        
        # Test when room temp is already below start threshold
        current_room_temp = 21.0  # Below start threshold
        result = self.analyzer.get_adjustment_needed_to_activate(
            current_room_temp, self.mock_hysteresis_learner, "cool"
        )
        assert result == 22.0  # Still returns the start threshold

    def test_handles_none_power_input(self):
        """Test graceful handling of None power consumption."""
        # None power should be treated as idle (conservative approach)
        assert self.analyzer.is_compressor_idle(None) is True

    def test_unsupported_hvac_modes(self):
        """Test that unsupported HVAC modes return False for would_activate."""
        current_room_temp = 25.0
        new_setpoint = 21.0
        
        # Test HEAT mode (not supported)
        result = self.analyzer.would_adjustment_activate_compressor(
            current_room_temp, new_setpoint, self.mock_hysteresis_learner, "heat"
        )
        assert result is False
        
        # Test HEAT_COOL mode (not supported)  
        result = self.analyzer.would_adjustment_activate_compressor(
            current_room_temp, new_setpoint, self.mock_hysteresis_learner, "heat_cool"
        )
        assert result is False
        
        # Test OFF mode (not supported)
        result = self.analyzer.would_adjustment_activate_compressor(
            current_room_temp, new_setpoint, self.mock_hysteresis_learner, "off"
        )
        assert result is False
        
        # Test get_adjustment_needed_to_activate with unsupported mode
        adjustment_needed = self.analyzer.get_adjustment_needed_to_activate(
            current_room_temp, self.mock_hysteresis_learner, "heat"
        )
        assert adjustment_needed is None