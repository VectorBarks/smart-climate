"""ABOUTME: Comprehensive tests for temperature adjustment logic fix.
Tests verify correct behavior when room temperature differs from target."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from custom_components.smart_climate.temperature_controller import (
    TemperatureController,
    TemperatureLimits
)
from custom_components.smart_climate.models import ModeAdjustments


class TestTemperatureAdjustmentLogic:
    """Test temperature adjustment logic for correct cooling behavior."""

    @pytest.fixture
    def mock_hass(self):
        """Mock HomeAssistant instance."""
        hass = Mock()
        hass.services = Mock()
        hass.services.async_call = AsyncMock()
        return hass

    @pytest.fixture
    def limits(self):
        """Temperature limits fixture."""
        return TemperatureLimits(min_temperature=16.0, max_temperature=30.0)

    @pytest.fixture
    def controller(self, mock_hass, limits):
        """TemperatureController fixture with default gradual adjustment."""
        return TemperatureController(mock_hass, limits, gradual_adjustment_rate=0.5)

    @pytest.fixture
    def mode_adjustments(self):
        """ModeAdjustments fixture with no adjustments."""
        return ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        )

    def test_room_warmer_than_target_positive_offset(self, controller, mode_adjustments):
        """Test: Room 24.8°C, Target 24.5°C, AC internal 25.0°C → AC should be set lower than 24.5°C.
        
        Scenario: Room is 0.3°C warmer than target, AC internal sensor reads 0.2°C warmer than room.
        Expected: AC should be set LOWER than target to provide MORE cooling.
        """
        room_temp = 24.8
        target_temp = 24.5
        ac_internal_temp = 25.0
        
        # Base offset = AC internal - Room = 25.0 - 24.8 = +0.2°C
        base_offset = ac_internal_temp - room_temp
        
        # Room is warmer than target, so we need MORE cooling
        # The adjusted temperature should be LOWER than target
        result = controller.apply_offset_and_limits(
            target_temp=target_temp,
            offset=base_offset,
            mode_adjustments=mode_adjustments,
            room_temp=room_temp
        )
        
        # With current implementation: 24.5 + 0.2 = 24.7°C (WRONG - less cooling)
        # This test should FAIL with current implementation
        assert result < target_temp, f"AC should be set lower than {target_temp}°C for more cooling, but got {result}°C"

    def test_room_cooler_than_target_positive_offset(self, controller, mode_adjustments):
        """Test: Room 24.2°C, Target 24.5°C, AC internal 25.0°C → AC should be set higher than 24.5°C.
        
        Scenario: Room is 0.3°C cooler than target, AC internal sensor reads 0.8°C warmer than room.
        Expected: AC should be set HIGHER than target to provide LESS cooling.
        """
        room_temp = 24.2
        target_temp = 24.5
        ac_internal_temp = 25.0
        
        # Base offset = AC internal - Room = 25.0 - 24.2 = +0.8°C
        base_offset = ac_internal_temp - room_temp
        
        # Room is cooler than target, so we need LESS cooling
        # The adjusted temperature should be HIGHER than target
        result = controller.apply_offset_and_limits(
            target_temp=target_temp,
            offset=base_offset,
            mode_adjustments=mode_adjustments,
            room_temp=room_temp
        )
        
        # With current implementation: 24.5 + 0.8 = 25.3°C (happens to be correct direction)
        # But this is only correct by coincidence, not by design
        assert result > target_temp, f"AC should be set higher than {target_temp}°C for less cooling, but got {result}°C"

    def test_room_equals_target_with_offset(self, controller, mode_adjustments):
        """Test: Room 24.5°C, Target 24.5°C, AC internal 25.0°C → AC should compensate for sensor difference.
        
        Scenario: Room equals target, but AC sensor reads warmer.
        Expected: AC should be set to target + base offset to maintain temperature.
        """
        room_temp = 24.5
        target_temp = 24.5
        ac_internal_temp = 25.0
        
        # Base offset = AC internal - Room = 25.0 - 24.5 = +0.5°C
        base_offset = ac_internal_temp - room_temp
        
        # Room equals target, just compensate for sensor difference
        result = controller.apply_offset_and_limits(
            target_temp=target_temp,
            offset=base_offset,
            mode_adjustments=mode_adjustments,
            room_temp=room_temp
        )
        
        # Should be target + base offset = 24.5 + 0.5 = 25.0°C
        expected = target_temp + base_offset
        assert result == expected, f"AC should be set to {expected}°C to compensate sensor, but got {result}°C"

    def test_room_warmer_than_target_negative_offset(self, controller, mode_adjustments):
        """Test: Room 25.0°C, Target 24.0°C, AC internal 24.5°C → AC should be set much lower.
        
        Scenario: Room is 1°C warmer than target, AC sensor reads 0.5°C cooler than room.
        Expected: AC should be set significantly LOWER for aggressive cooling.
        """
        room_temp = 25.0
        target_temp = 24.0
        ac_internal_temp = 24.5
        
        # Base offset = AC internal - Room = 24.5 - 25.0 = -0.5°C
        base_offset = ac_internal_temp - room_temp
        
        # Room is 1°C warmer than target, need aggressive cooling
        result = controller.apply_offset_and_limits(
            target_temp=target_temp,
            offset=base_offset,
            mode_adjustments=mode_adjustments,
            room_temp=room_temp
        )
        
        # With current implementation: 24.0 + (-0.5) = 23.5°C
        # This happens to cool more, but not considering room deviation
        assert result < target_temp, f"AC should be set lower than {target_temp}°C for cooling, but got {result}°C"

    def test_gradual_adjustment_interaction(self, controller, mode_adjustments):
        """Test that gradual adjustment still works with corrected logic."""
        # Set up a scenario where we need significant cooling
        room_temp = 26.0
        target_temp = 24.0
        ac_internal_temp = 26.5
        
        # Base offset = AC internal - Room = 26.5 - 26.0 = +0.5°C
        base_offset = ac_internal_temp - room_temp
        
        # First adjustment
        result1 = controller.apply_offset_and_limits(
            target_temp=target_temp,
            offset=base_offset,
            mode_adjustments=mode_adjustments,
            room_temp=room_temp
        )
        
        # Should be moving towards more cooling
        assert result1 < target_temp + base_offset

    def test_mode_adjustments_still_apply(self, controller):
        """Test that mode adjustments (night, boost) still work correctly."""
        room_temp = 24.5
        target_temp = 24.0
        ac_internal_temp = 25.0
        base_offset = ac_internal_temp - room_temp  # +0.5°C
        
        # Test with night mode adjustment
        night_adjustments = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=1.0,  # Night mode adds 1°C
            update_interval_override=None,
            boost_offset=0.0
        )
        
        result = controller.apply_offset_and_limits(
            target_temp=target_temp,
            offset=base_offset,
            mode_adjustments=night_adjustments
        )
        
        # Result should include both base offset and mode adjustment
        # Current: 24.0 + 0.5 + 1.0 = 25.5°C
        assert result > target_temp  # Night mode should reduce cooling

    def test_safety_limits_respected(self, controller, mode_adjustments):
        """Test that safety limits are still enforced with new logic."""
        # Test minimum limit
        room_temp = 30.0
        target_temp = 20.0
        ac_internal_temp = 30.5
        base_offset = ac_internal_temp - room_temp  # +0.5°C
        
        result = controller.apply_offset_and_limits(
            target_temp=target_temp,
            offset=base_offset,
            mode_adjustments=mode_adjustments,
            room_temp=room_temp
        )
        
        # Even with aggressive cooling needed, should not go below 16°C
        assert result >= 16.0
        
        # Test maximum limit
        room_temp = 15.0
        target_temp = 25.0
        ac_internal_temp = 16.0
        base_offset = ac_internal_temp - room_temp  # +1.0°C
        
        result = controller.apply_offset_and_limits(
            target_temp=target_temp,
            offset=base_offset,
            mode_adjustments=mode_adjustments,
            room_temp=room_temp
        )
        
        # Should not exceed 30°C
        assert result <= 30.0

    def test_real_world_scenario_hot_day(self, controller, mode_adjustments):
        """Test real-world scenario: Hot day, room warming up."""
        # Room is getting warm despite AC running
        room_temp = 26.2
        target_temp = 24.0
        ac_internal_temp = 15.8  # Evaporator coil temperature during cooling
        
        # Base offset = 15.8 - 26.2 = -10.4°C (typical for evaporator sensor)
        base_offset = ac_internal_temp - room_temp
        
        result = controller.apply_offset_and_limits(
            target_temp=target_temp,
            offset=base_offset,
            mode_adjustments=mode_adjustments,
            room_temp=room_temp
        )
        
        # With current logic: 24.0 + (-10.4) = 13.6°C → clamped to 16.0°C
        # This is actually providing maximum cooling, which is correct
        assert result == 16.0  # Should hit minimum limit for maximum cooling

    def test_real_world_scenario_mild_day(self, controller, mode_adjustments):
        """Test real-world scenario: Mild day, slight cooling needed."""
        # Room is slightly warm
        room_temp = 24.8
        target_temp = 24.5
        ac_internal_temp = 25.2  # AC sensor slightly warmer
        
        # Base offset = 25.2 - 24.8 = +0.4°C
        base_offset = ac_internal_temp - room_temp
        
        result = controller.apply_offset_and_limits(
            target_temp=target_temp,
            offset=base_offset,
            mode_adjustments=mode_adjustments,
            room_temp=room_temp
        )
        
        # Room is 0.3°C above target, needs more cooling
        # Without room adjustment: 24.5 + 0.4 = 24.9°C (reduces cooling - WRONG)
        # With room adjustment: 24.5 + 0.4 - 0.3 = 24.6°C (better but still not enough)
        # Since offset (0.4) > room deviation (0.3), result will be slightly above target
        # This is expected behavior - the test should check that we're cooling more than without adjustment
        assert abs(result - 24.6) < 0.01, f"Expected ~24.6°C but got {result}°C"

    @pytest.mark.parametrize("room_temp,target_temp,ac_temp,expected_direction", [
        (25.0, 24.0, 25.5, "lower"),    # Room 1°C warmer → cool more
        (23.0, 24.0, 23.5, "higher"),   # Room 1°C cooler → cool less
        (24.0, 24.0, 24.5, "equal"),    # Room at target → maintain
        (26.0, 24.0, 26.2, "lower"),    # Room 2°C warmer → cool much more
        (22.0, 24.0, 22.3, "higher"),   # Room 2°C cooler → cool much less
    ])
    def test_various_temperature_scenarios(self, controller, mode_adjustments, 
                                         room_temp, target_temp, ac_temp, expected_direction):
        """Test various temperature scenarios for correct adjustment direction."""
        base_offset = ac_temp - room_temp
        
        result = controller.apply_offset_and_limits(
            target_temp=target_temp,
            offset=base_offset,
            mode_adjustments=mode_adjustments,
            room_temp=room_temp
        )
        
        if expected_direction == "lower":
            assert result < target_temp + base_offset, \
                f"Room {room_temp}°C vs target {target_temp}°C should cool more"
        elif expected_direction == "higher":
            assert result > target_temp + base_offset, \
                f"Room {room_temp}°C vs target {target_temp}°C should cool less"
        else:  # equal
            expected = target_temp + base_offset
            assert abs(result - expected) < 0.1, \
                f"Room at target should just compensate sensor offset"