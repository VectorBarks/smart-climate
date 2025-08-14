"""Tests for humidity contribution in OffsetEngine reason strings."""

import pytest
from datetime import time
from unittest.mock import Mock, patch

from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.models import OffsetInput


class TestOffsetEngineHumidityReason:
    """Test suite for humidity contribution in offset reason strings."""

    def test_reason_includes_humidity_when_present(self):
        """Test that reason string includes humidity information when humidity data is present."""
        config = {
            "max_offset": 5.0,
            "ml_enabled": False,
            "enable_learning": False
        }
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="auto",
            power_consumption=150.0,
            time_of_day=time(14, 0),
            day_of_week=2,
            indoor_humidity=65.0,
            outdoor_humidity=80.0,
            humidity_differential=15.0
        )
        
        result = engine.calculate_offset(input_data)
        
        # When humidity data is present and non-zero, it should appear in reason
        assert "humidity-adjusted" in result.reason
        assert "indoor: 65.0%" in result.reason
        assert "outdoor: 80.0%" in result.reason
        assert "diff: 15.0%" in result.reason

    def test_reason_excludes_humidity_when_none(self):
        """Test that reason string excludes humidity when humidity data is None."""
        config = {
            "max_offset": 5.0,
            "ml_enabled": False,
            "enable_learning": False
        }
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="auto",
            power_consumption=150.0,
            time_of_day=time(14, 0),
            day_of_week=2,
            indoor_humidity=None,
            outdoor_humidity=None,
            humidity_differential=None
        )
        
        result = engine.calculate_offset(input_data)
        
        # When humidity data is None, it should not appear in reason
        assert "humidity-adjusted" not in result.reason

    def test_reason_excludes_humidity_when_zero(self):
        """Test that reason string excludes humidity when humidity data is zero."""
        config = {
            "max_offset": 5.0,
            "ml_enabled": False,
            "enable_learning": False
        }
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="auto",
            power_consumption=150.0,
            time_of_day=time(14, 0),
            day_of_week=2,
            indoor_humidity=0.0,
            outdoor_humidity=0.0,
            humidity_differential=0.0
        )
        
        result = engine.calculate_offset(input_data)
        
        # When humidity data is zero, it should not appear in reason
        assert "humidity-adjusted" not in result.reason

    def test_reason_includes_partial_humidity(self):
        """Test that reason string includes humidity when only some values are present."""
        config = {
            "max_offset": 5.0,
            "ml_enabled": False,
            "enable_learning": False
        }
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="auto",
            power_consumption=150.0,
            time_of_day=time(14, 0),
            day_of_week=2,
            indoor_humidity=60.0,
            outdoor_humidity=None,  # Only indoor is present
            humidity_differential=None
        )
        
        result = engine.calculate_offset(input_data)
        
        # When at least one humidity value is present, it should appear in reason
        assert "humidity-adjusted" in result.reason
        assert "indoor: 60.0%" in result.reason

    def test_contributing_factors_includes_humidity(self):
        """Test that contributing factors debug log includes humidity when present."""
        config = {
            "max_offset": 5.0,
            "ml_enabled": False,
            "enable_learning": False
        }
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="auto",
            power_consumption=150.0,
            time_of_day=time(14, 0),
            day_of_week=2,
            indoor_humidity=65.0,
            outdoor_humidity=80.0,
            humidity_differential=15.0
        )
        
        with patch('custom_components.smart_climate.offset_engine._LOGGER') as mock_logger:
            result = engine.calculate_offset(input_data)
            
            # Check if any debug call mentions humidity in contributing factors
            debug_calls = [call.args for call in mock_logger.debug.call_args_list]
            humidity_factor_call = None
            for args in debug_calls:
                if len(args) >= 2 and "Contributing factors:" in args[0]:
                    humidity_factor_call = args
                    break
            
            # Should have humidity in contributing factors if humidity data impacts calculation
            assert humidity_factor_call is not None
            if any(h for h in [65.0, 80.0, 15.0] if h and h != 0):
                assert "humidity" in humidity_factor_call[1].lower()