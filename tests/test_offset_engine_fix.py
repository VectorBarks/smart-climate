"""Test correct offset calculation logic after bug fix."""

import pytest
from datetime import time

from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.models import OffsetInput, OffsetResult


class TestOffsetEngineFix:
    """Test suite for correct offset calculation logic."""

    def test_room_warmer_than_ac_sensor_needs_negative_offset(self):
        """Test when room is warmer than AC sensor, we need negative offset to cool more.
        
        Example: Room is 25°C, AC sensor reads 24°C
        The AC thinks it's cooler than reality, so it won't cool enough.
        We need a negative offset to make the AC target lower and cool more.
        """
        config = {"max_offset": 5.0, "enable_learning": False}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=24.0,  # AC sensor reads 24°C
            room_temp=25.0,         # Room is actually 25°C (warmer)
            outdoor_temp=None,
            mode="none",
            power_consumption=None,
            time_of_day=time(12, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        # Room is warmer than AC sensor, so we need negative offset
        assert result.offset < 0, f"Expected negative offset, got {result.offset}"
        # Specifically, the offset should be -1.0 (24 - 25 = -1)
        assert abs(result.offset - (-1.0)) < 0.01, f"Expected offset of -1.0, got {result.offset}"
        assert not result.clamped
        assert "AC sensor cooler than room" in result.reason

    def test_room_cooler_than_ac_sensor_needs_positive_offset(self):
        """Test when room is cooler than AC sensor, we need positive offset to cool less.
        
        Example: Room is 23°C, AC sensor reads 24°C
        The AC thinks it's warmer than reality, so it will cool too much.
        We need a positive offset to make the AC target higher and cool less.
        """
        config = {"max_offset": 5.0, "enable_learning": False}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=24.0,  # AC sensor reads 24°C
            room_temp=23.0,         # Room is actually 23°C (cooler)
            outdoor_temp=None,
            mode="none",
            power_consumption=None,
            time_of_day=time(12, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        # Room is cooler than AC sensor, so we need positive offset
        assert result.offset > 0, f"Expected positive offset, got {result.offset}"
        # Specifically, the offset should be +1.0 (24 - 23 = 1)
        assert abs(result.offset - 1.0) < 0.01, f"Expected offset of +1.0, got {result.offset}"
        assert not result.clamped
        assert "AC sensor warmer than room" in result.reason

    def test_equal_temperatures_zero_offset(self):
        """Test when temperatures are equal, offset should be zero."""
        config = {"max_offset": 5.0, "enable_learning": False}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=24.0,  # AC sensor reads 24°C
            room_temp=24.0,         # Room is also 24°C
            outdoor_temp=None,
            mode="none",
            power_consumption=None,
            time_of_day=time(12, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        assert result.offset == 0.0, f"Expected zero offset, got {result.offset}"
        assert not result.clamped
        assert "no offset needed" in result.reason.lower()

    def test_large_temperature_difference_clamped(self):
        """Test that large temperature differences are clamped to max_offset."""
        config = {"max_offset": 3.0, "enable_learning": False}  # Lower limit for testing
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=20.0,  # AC sensor reads 20°C
            room_temp=30.0,         # Room is 30°C (10°C difference!)
            outdoor_temp=None,
            mode="none",
            power_consumption=None,
            time_of_day=time(12, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        # Should be clamped to -3.0 (max negative offset)
        assert result.offset == -3.0, f"Expected clamped offset of -3.0, got {result.offset}"
        assert result.clamped
        assert "clamped to limit" in result.reason

    def test_mode_adjustments_with_correct_base_offset(self):
        """Test that mode adjustments are applied to the correct base offset."""
        config = {"max_offset": 5.0, "enable_learning": False}
        engine = OffsetEngine(config)
        
        # Base scenario: room warmer than AC (needs negative offset)
        input_data_base = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=26.0,  # 2°C warmer
            outdoor_temp=None,
            mode="none",
            power_consumption=None,
            time_of_day=time(12, 0),
            day_of_week=2
        )
        
        result_base = engine.calculate_offset(input_data_base)
        base_offset = result_base.offset
        assert base_offset < 0, "Base offset should be negative"
        
        # Test away mode (less aggressive)
        input_data_away = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=26.0,
            outdoor_temp=None,
            mode="away",  # Changed mode
            power_consumption=None,
            time_of_day=time(12, 0),
            day_of_week=2
        )
        result_away = engine.calculate_offset(input_data_away)
        # Away mode should reduce the magnitude (make it less negative)
        assert result_away.offset > base_offset, "Away mode should reduce cooling"
        assert result_away.offset < 0, "But still should be negative"
        
        # Test boost mode (more aggressive)
        input_data_boost = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=26.0,
            outdoor_temp=None,
            mode="boost",  # Changed mode
            power_consumption=None,
            time_of_day=time(12, 0),
            day_of_week=2
        )
        result_boost = engine.calculate_offset(input_data_boost)
        # Boost mode should increase the magnitude (make it more negative)
        assert result_boost.offset < base_offset, "Boost mode should increase cooling"

    def test_practical_scenario_hot_room(self):
        """Test realistic scenario: Hot room needs more cooling.
        
        User sets AC to 24°C. Room is 26°C but AC sensor reads 25°C.
        Without correction, AC would target 24°C thinking it's at 25°C.
        We need offset of -1°C so AC targets 23°C to actually cool to 24°C.
        """
        config = {"max_offset": 5.0, "enable_learning": False}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=25.0,  # AC thinks it's 25°C
            room_temp=26.0,         # Room is actually 26°C
            outdoor_temp=35.0,      # Hot day
            mode="none",
            power_consumption=250.0,  # AC working hard
            time_of_day=time(14, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        # Should have negative offset to cool more
        assert result.offset < 0, f"Hot room should have negative offset, got {result.offset}"
        # Base offset should be -1.0, with some adjustments
        assert -2.0 < result.offset < 0, f"Offset out of expected range: {result.offset}"

    def test_practical_scenario_overcooling(self):
        """Test realistic scenario: AC overcooling the room.
        
        User sets AC to 24°C. Room is 22°C but AC sensor reads 24°C.
        AC thinks it's at target but room is too cold.
        We need offset of +2°C so AC targets 26°C to let room warm to 24°C.
        """
        config = {"max_offset": 5.0, "enable_learning": False}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=24.0,  # AC thinks it's 24°C
            room_temp=22.0,         # Room is actually 22°C (too cold)
            outdoor_temp=30.0,
            mode="none",
            power_consumption=100.0,  # AC not working hard
            time_of_day=time(14, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        # Should have positive offset to cool less
        assert result.offset > 0, f"Overcooled room should have positive offset, got {result.offset}"
        # Base offset should be +2.0, with some adjustments
        assert 0 < result.offset < 3.0, f"Offset out of expected range: {result.offset}"