"""Tests for OffsetEngine component."""

import pytest
from datetime import time
from unittest.mock import Mock

from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.models import OffsetInput, OffsetResult


class TestOffsetEngine:
    """Test suite for OffsetEngine class."""

    def test_init_with_default_config(self):
        """Test OffsetEngine initialization with default config."""
        config = {}
        engine = OffsetEngine(config)
        
        assert engine._max_offset == 5.0
        assert engine._ml_enabled is True
        assert engine._ml_model is None

    def test_init_with_custom_config(self):
        """Test OffsetEngine initialization with custom config."""
        config = {
            "max_offset": 3.0,
            "ml_enabled": False
        }
        engine = OffsetEngine(config)
        
        assert engine._max_offset == 3.0
        assert engine._ml_enabled is False
        assert engine._ml_model is None

    def test_calculate_offset_basic_scenario(self):
        """Test basic offset calculation."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=1
        )
        
        result = engine.calculate_offset(input_data)
        
        assert isinstance(result, OffsetResult)
        assert isinstance(result.offset, float)
        assert isinstance(result.clamped, bool)
        assert isinstance(result.reason, str)
        assert 0.0 <= result.confidence <= 1.0
        assert -5.0 <= result.offset <= 5.0

    def test_calculate_offset_ac_warmer_than_room(self):
        """Test offset when AC internal sensor reads warmer than room."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=22.0,
            outdoor_temp=None,
            mode="none",
            power_consumption=None,
            time_of_day=time(12, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        # AC reads warmer, so we need negative offset to cool more
        assert result.offset < 0
        assert not result.clamped
        assert "AC sensor warmer than room" in result.reason

    def test_calculate_offset_ac_cooler_than_room(self):
        """Test offset when AC internal sensor reads cooler than room."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=20.0,
            room_temp=22.0,
            outdoor_temp=None,
            mode="none",
            power_consumption=None,
            time_of_day=time(12, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        # AC reads cooler, so we need positive offset to heat less
        assert result.offset > 0
        assert not result.clamped
        assert "AC sensor cooler than room" in result.reason

    def test_calculate_offset_max_limit_clamping(self):
        """Test offset clamping to maximum limit."""
        config = {"max_offset": 2.0}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=15.0,  # Very different from room
            room_temp=25.0,
            outdoor_temp=None,
            mode="none",
            power_consumption=None,
            time_of_day=time(12, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        assert abs(result.offset) <= 2.0
        assert result.clamped
        assert "clamped to limit" in result.reason

    def test_calculate_offset_zero_difference(self):
        """Test offset when AC and room temperatures are equal."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=22.0,
            outdoor_temp=None,
            mode="none",
            power_consumption=None,
            time_of_day=time(12, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        assert result.offset == 0.0
        assert not result.clamped
        assert "no offset needed" in result.reason.lower()

    def test_calculate_offset_away_mode(self):
        """Test offset calculation in away mode."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=25.0,
            mode="away",
            power_consumption=None,
            time_of_day=time(12, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        assert isinstance(result, OffsetResult)
        assert "away mode" in result.reason.lower()

    def test_calculate_offset_sleep_mode(self):
        """Test offset calculation in sleep mode."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=25.0,
            mode="sleep",
            power_consumption=None,
            time_of_day=time(23, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        assert isinstance(result, OffsetResult)
        assert "sleep mode" in result.reason.lower()

    def test_calculate_offset_boost_mode(self):
        """Test offset calculation in boost mode."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=30.0,
            mode="boost",
            power_consumption=200.0,
            time_of_day=time(15, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        assert isinstance(result, OffsetResult)
        assert "boost mode" in result.reason.lower()

    def test_calculate_offset_with_outdoor_temp(self):
        """Test offset calculation with outdoor temperature consideration."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=35.0,  # Very hot outside
            mode="none",
            power_consumption=None,
            time_of_day=time(15, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        assert isinstance(result, OffsetResult)
        # Should consider outdoor temperature in reasoning
        assert result.reason is not None

    def test_calculate_offset_with_power_consumption(self):
        """Test offset calculation with power consumption data."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=300.0,  # High power usage
            time_of_day=time(15, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        assert isinstance(result, OffsetResult)
        # Should consider power consumption in reasoning
        assert result.reason is not None

    def test_calculate_offset_confidence_levels(self):
        """Test that confidence levels are reasonable."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        # Test with complete data
        input_complete = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=150.0,
            time_of_day=time(15, 0),
            day_of_week=2
        )
        
        result_complete = engine.calculate_offset(input_complete)
        
        # Test with minimal data
        input_minimal = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=None,
            mode="none",
            power_consumption=None,
            time_of_day=time(15, 0),
            day_of_week=2
        )
        
        result_minimal = engine.calculate_offset(input_minimal)
        
        # Complete data should have higher confidence
        assert result_complete.confidence >= result_minimal.confidence

    def test_update_ml_model(self):
        """Test ML model update functionality."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        # Should not raise an exception
        engine.update_ml_model("/path/to/model.pkl")
        
        # For now, this is a placeholder implementation
        # In future, this would load and validate the model

    def test_calculate_offset_edge_cases(self):
        """Test edge cases and error conditions."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        # Test with extreme temperature differences
        input_extreme = OffsetInput(
            ac_internal_temp=10.0,
            room_temp=30.0,
            outdoor_temp=None,
            mode="none",
            power_consumption=None,
            time_of_day=time(12, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_extreme)
        
        assert isinstance(result, OffsetResult)
        assert abs(result.offset) <= 5.0
        assert result.clamped