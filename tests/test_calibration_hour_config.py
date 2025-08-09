"""Tests for calibration hour configuration functionality.
Tests that CalibrationState uses configured calibration_hour instead of hardcoded 2-3 AM."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from custom_components.smart_climate.thermal_special_states import CalibratingState
from custom_components.smart_climate.thermal_models import ThermalState
from custom_components.smart_climate.thermal_states import StateHandler


class TestCalibrationHourConfiguration:
    """Test calibration hour configuration functionality."""

    def test_calibrating_state_uses_configured_hour_1am(self):
        """Test CalibrationState uses calibration_hour=1 (1-2 AM window)."""
        handler = CalibratingState()
        context = Mock()
        
        # Mock context to return calibration_hour = 1
        context.calibration_hour = 1
        
        # Test that 1 AM is within the configured window
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_datetime:
            mock_now = Mock()
            mock_now.hour = 1
            mock_datetime.now.return_value = mock_now
            
            result = handler.is_optimal_calibration_time(context)
            assert result is True

    def test_calibrating_state_uses_configured_hour_22pm(self):
        """Test CalibrationState uses calibration_hour=22 (10-11 PM window)."""
        handler = CalibratingState()
        context = Mock()
        
        # Mock context to return calibration_hour = 22
        context.calibration_hour = 22
        
        # Test that 10 PM is within the configured window
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_datetime:
            mock_now = Mock()
            mock_now.hour = 22
            mock_datetime.now.return_value = mock_now
            
            result = handler.is_optimal_calibration_time(context)
            assert result is True

    def test_calibrating_state_uses_configured_hour_14pm(self):
        """Test CalibrationState uses calibration_hour=14 (2-3 PM window)."""
        handler = CalibratingState()
        context = Mock()
        
        # Mock context to return calibration_hour = 14
        context.calibration_hour = 14
        
        # Test that 2 PM is within the configured window
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_datetime:
            mock_now = Mock()
            mock_now.hour = 14
            mock_datetime.now.return_value = mock_now
            
            result = handler.is_optimal_calibration_time(context)
            assert result is True

    def test_calibrating_state_hour_outside_window(self):
        """Test CalibrationState returns False outside configured window."""
        handler = CalibratingState()
        context = Mock()
        
        # Mock context to return calibration_hour = 1 (1-2 AM window)
        context.calibration_hour = 1
        
        # Test that 3 AM is outside the 1-2 AM window
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_datetime:
            mock_now = Mock()
            mock_now.hour = 3
            mock_datetime.now.return_value = mock_now
            
            result = handler.is_optimal_calibration_time(context)
            assert result is False

    def test_calibrating_state_hour_edge_case_0(self):
        """Test CalibrationState with calibration_hour=0 (midnight-1 AM)."""
        handler = CalibratingState()
        context = Mock()
        
        # Mock context to return calibration_hour = 0
        context.calibration_hour = 0
        
        # Test that midnight (0) is within the configured window
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_datetime:
            mock_now = Mock()
            mock_now.hour = 0
            mock_datetime.now.return_value = mock_now
            
            result = handler.is_optimal_calibration_time(context)
            assert result is True

    def test_calibrating_state_hour_edge_case_23(self):
        """Test CalibrationState with calibration_hour=23 (11 PM-midnight)."""
        handler = CalibratingState()
        context = Mock()
        
        # Mock context to return calibration_hour = 23
        context.calibration_hour = 23
        
        # Test that 11 PM (23) is within the configured window
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_datetime:
            mock_now = Mock()
            mock_now.hour = 23
            mock_datetime.now.return_value = mock_now
            
            result = handler.is_optimal_calibration_time(context)
            assert result is True

    def test_calibrating_state_fallback_when_no_config(self):
        """Test CalibrationState falls back to hardcoded 2-3 AM when no config available."""
        handler = CalibratingState()
        context = Mock()
        
        # Mock context with no calibration_hour attribute
        del context.calibration_hour  # Remove attribute to simulate missing config
        
        # Test that 2 AM uses fallback behavior
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_datetime:
            mock_now = Mock()
            mock_now.hour = 2
            mock_datetime.now.return_value = mock_now
            
            result = handler.is_optimal_calibration_time(context)
            assert result is True

    def test_calibrating_state_window_spans_hour(self):
        """Test calibration window is exactly 1 hour starting from configured hour."""
        handler = CalibratingState()
        context = Mock()
        
        # Test calibration_hour=5 should create 5-6 AM window
        context.calibration_hour = 5
        
        test_cases = [
            (4, False),  # Before window
            (5, True),   # Start of window
            (6, False),  # Just after window ends
            (7, False),  # Well after window
        ]
        
        for test_hour, expected in test_cases:
            with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_datetime:
                mock_now = Mock()
                mock_now.hour = test_hour
                mock_datetime.now.return_value = mock_now
                
                result = handler.is_optimal_calibration_time(context)
                assert result is expected, f"Hour {test_hour} should return {expected}"

    def test_calibrating_state_error_handling(self):
        """Test CalibrationState handles errors gracefully."""
        handler = CalibratingState()
        context = Mock()
        
        # Mock context to raise exception when accessing calibration_hour
        context.calibration_hour = property(lambda self: (_ for _ in ()).throw(AttributeError()))
        
        # Should return False on error
        result = handler.is_optimal_calibration_time(context)
        assert result is False