"""Tests for TemperatureController component."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from custom_components.smart_climate.temperature_controller import (
    TemperatureController,
    TemperatureLimits
)
from custom_components.smart_climate.models import ModeAdjustments


class TestTemperatureLimits:
    """Test TemperatureLimits dataclass."""
    
    def test_default_limits(self):
        """Test default temperature limits."""
        limits = TemperatureLimits()
        assert limits.min_temperature == 16.0
        assert limits.max_temperature == 30.0
    
    def test_custom_limits(self):
        """Test custom temperature limits."""
        limits = TemperatureLimits(min_temperature=18.0, max_temperature=28.0)
        assert limits.min_temperature == 18.0
        assert limits.max_temperature == 28.0


class TestTemperatureController:
    """Test TemperatureController class."""

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
        """TemperatureController fixture."""
        return TemperatureController(mock_hass, limits)

    @pytest.fixture
    def mode_adjustments(self):
        """ModeAdjustments fixture."""
        return ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        )

    def test_init(self, mock_hass, limits):
        """Test TemperatureController initialization."""
        controller = TemperatureController(mock_hass, limits)
        
        assert controller._hass == mock_hass
        assert controller._limits == limits
        assert controller._gradual_adjustment_rate == 0.5
        assert controller._last_adjustment == 0.0

    def test_apply_offset_and_limits_normal(self, controller, mode_adjustments):
        """Test apply_offset_and_limits with normal values."""
        result = controller.apply_offset_and_limits(
            target_temp=22.0,
            offset=2.0,
            mode_adjustments=mode_adjustments
        )
        
        # 22.0 + 2.0 = 24.0 (within limits)
        assert result == 24.0

    def test_apply_offset_and_limits_clamp_min(self, controller, mode_adjustments):
        """Test apply_offset_and_limits clamps to minimum."""
        result = controller.apply_offset_and_limits(
            target_temp=18.0,
            offset=-5.0,
            mode_adjustments=mode_adjustments
        )
        
        # 18.0 - 5.0 = 13.0, clamped to 16.0
        assert result == 16.0

    def test_apply_offset_and_limits_clamp_max(self, controller, mode_adjustments):
        """Test apply_offset_and_limits clamps to maximum."""
        result = controller.apply_offset_and_limits(
            target_temp=28.0,
            offset=5.0,
            mode_adjustments=mode_adjustments
        )
        
        # 28.0 + 5.0 = 33.0, clamped to 30.0
        assert result == 30.0

    def test_apply_offset_and_limits_with_boost(self, controller):
        """Test apply_offset_and_limits with boost mode."""
        mode_adjustments = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=2.0
        )
        
        result = controller.apply_offset_and_limits(
            target_temp=22.0,
            offset=1.0,
            mode_adjustments=mode_adjustments
        )
        
        # 22.0 + 1.0 + 2.0 = 25.0
        assert result == 25.0

    def test_apply_offset_and_limits_with_override(self, controller):
        """Test apply_offset_and_limits with temperature override."""
        mode_adjustments = ModeAdjustments(
            temperature_override=20.0,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        )
        
        result = controller.apply_offset_and_limits(
            target_temp=22.0,
            offset=1.0,
            mode_adjustments=mode_adjustments
        )
        
        # Override temperature used instead: 20.0 + 1.0 = 21.0
        assert result == 21.0

    def test_apply_gradual_adjustment_no_change(self, controller):
        """Test apply_gradual_adjustment with no change needed."""
        result = controller.apply_gradual_adjustment(
            current_adjustment=2.0,
            target_adjustment=2.0
        )
        
        assert result == 2.0

    def test_apply_gradual_adjustment_increase(self, controller):
        """Test apply_gradual_adjustment with increase."""
        result = controller.apply_gradual_adjustment(
            current_adjustment=1.0,
            target_adjustment=3.0
        )
        
        # 1.0 + 0.5 = 1.5 (limited by rate)
        assert result == 1.5

    def test_apply_gradual_adjustment_decrease(self, controller):
        """Test apply_gradual_adjustment with decrease."""
        result = controller.apply_gradual_adjustment(
            current_adjustment=3.0,
            target_adjustment=1.0
        )
        
        # 3.0 - 0.5 = 2.5 (limited by rate)
        assert result == 2.5

    def test_apply_gradual_adjustment_large_change(self, controller):
        """Test apply_gradual_adjustment with large change."""
        result = controller.apply_gradual_adjustment(
            current_adjustment=0.0,
            target_adjustment=0.3
        )
        
        # Small change: 0.0 + 0.3 = 0.3 (not limited)
        assert result == 0.3

    def test_send_temperature_command_success(self, controller, mock_hass):
        """Test send_temperature_command successful call."""
        import asyncio
        
        async def run_test():
            await controller.send_temperature_command(
                entity_id="climate.test",
                temperature=22.5
            )
        
        asyncio.run(run_test())
        
        mock_hass.services.async_call.assert_called_once_with(
            "climate",
            "set_temperature",
            {
                "entity_id": "climate.test",
                "temperature": 22.5
            },
            blocking=False
        )

    def test_send_temperature_command_failure(self, controller, mock_hass):
        """Test send_temperature_command handles failures gracefully."""
        import asyncio
        
        mock_hass.services.async_call.side_effect = Exception("Service call failed")
        
        async def run_test():
            # Should not raise exception
            await controller.send_temperature_command(
                entity_id="climate.test",
                temperature=22.5
            )
        
        asyncio.run(run_test())
        
        mock_hass.services.async_call.assert_called_once()

    def test_integration_with_mode_adjustments(self, controller):
        """Test integration with all mode adjustments."""
        mode_adjustments = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=1.0,
            update_interval_override=None,
            boost_offset=0.5
        )
        
        result = controller.apply_offset_and_limits(
            target_temp=22.0,
            offset=1.5,
            mode_adjustments=mode_adjustments
        )
        
        # 22.0 + 1.5 + 1.0 + 0.5 = 25.0
        assert result == 25.0

    def test_edge_case_zero_offset(self, controller, mode_adjustments):
        """Test edge case with zero offset."""
        result = controller.apply_offset_and_limits(
            target_temp=22.0,
            offset=0.0,
            mode_adjustments=mode_adjustments
        )
        
        assert result == 22.0

    def test_edge_case_negative_offset(self, controller, mode_adjustments):
        """Test edge case with negative offset."""
        result = controller.apply_offset_and_limits(
            target_temp=22.0,
            offset=-1.5,
            mode_adjustments=mode_adjustments
        )
        
        assert result == 20.5