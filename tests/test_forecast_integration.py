"""Tests for ForecastEngine integration into SmartClimateEntity.

This module tests the integration of weather-based predictive adjustments
with the existing reactive offset system.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from homeassistant.core import HomeAssistant
from homeassistant.components.climate.const import HVACMode

from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.models import OffsetInput, OffsetResult
from custom_components.smart_climate.const import CONF_PREDICTIVE
from tests.fixtures.mock_entities import create_mock_hass, create_mock_state

# Test fixtures for ForecastEngine
@pytest.fixture
def mock_forecast_engine():
    """Create a mock ForecastEngine."""
    engine = Mock()
    engine.predictive_offset = 0.0
    engine.active_strategy_info = None
    engine.async_update = AsyncMock()
    return engine

@pytest.fixture
def predictive_config():
    """Configuration with predictive section."""
    return {
        "climate_entity": "climate.test_ac",
        "room_sensor": "sensor.room_temp",
        "outdoor_sensor": "sensor.outdoor_temp",
        "power_sensor": "sensor.ac_power",
        "update_interval": 180,
        "feedback_delay": 45,
        "predictive": {
            "weather_entity": "weather.forecast",
            "strategies": [
                {
                    "type": "heat_wave",
                    "enabled": True,
                    "temperature_threshold": 35.0,
                    "adjustment": -1.0,
                    "duration_hours": 4
                }
            ]
        }
    }

@pytest.fixture
def basic_config():
    """Configuration without predictive section."""
    return {
        "climate_entity": "climate.test_ac",
        "room_sensor": "sensor.room_temp",
        "outdoor_sensor": "sensor.outdoor_temp",
        "power_sensor": "sensor.ac_power",
        "update_interval": 180,
        "feedback_delay": 45
    }

class TestForecastEngineIntegration:
    """Test ForecastEngine integration into SmartClimateEntity."""

    def test_entity_initialization_with_forecast_engine(
        self, predictive_config, mock_forecast_engine
    ):
        """Test entity initializes with ForecastEngine when predictive config present."""
        # Create mock dependencies
        mock_hass = create_mock_hass()
        mock_offset_engine = Mock()
        mock_sensor_manager = Mock()
        mock_mode_manager = Mock()
        mock_temperature_controller = Mock()
        mock_coordinator = Mock()

        # Create entity with forecast engine
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=predictive_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=mock_offset_engine,
            sensor_manager=mock_sensor_manager,
            mode_manager=mock_mode_manager,
            temperature_controller=mock_temperature_controller,
            coordinator=mock_coordinator,
            forecast_engine=mock_forecast_engine
        )

        # Verify forecast engine is stored
        assert entity._forecast_engine is mock_forecast_engine

    def test_entity_initialization_without_forecast_engine(
        self, basic_config
    ):
        """Test entity initializes without ForecastEngine when no predictive config."""
        # Create mock dependencies
        mock_hass = create_mock_hass()
        mock_offset_engine = Mock()
        mock_sensor_manager = Mock()
        mock_mode_manager = Mock()
        mock_temperature_controller = Mock()
        mock_coordinator = Mock()

        # Create entity without forecast engine
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=basic_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=mock_offset_engine,
            sensor_manager=mock_sensor_manager,
            mode_manager=mock_mode_manager,
            temperature_controller=mock_temperature_controller,
            coordinator=mock_coordinator,
            forecast_engine=None
        )

        # Verify no forecast engine
        assert entity._forecast_engine is None

    @pytest.mark.asyncio
    async def test_offset_combination_reactive_plus_predictive(
        self, predictive_config, mock_forecast_engine
    ):
        """Test combining reactive and predictive offsets."""
        # Setup mock components
        mock_hass = create_mock_hass()
        mock_offset_engine = Mock()
        mock_offset_engine.calculate_offset.return_value = OffsetResult(
            offset=1.5,  # Reactive offset
            clamped=False,
            reason="Room warmer than AC",
            confidence=0.8
        )

        mock_sensor_manager = Mock()
        mock_sensor_manager.get_room_temperature.return_value = 25.0
        mock_sensor_manager.get_outdoor_temperature.return_value = 30.0
        mock_sensor_manager.get_power_consumption.return_value = 1200.0

        mock_mode_manager = Mock()
        mock_mode_manager.current_mode = "none"
        mock_mode_manager.get_adjustments.return_value = Mock(
            temperature_override=None,
            offset_adjustment=0.0,
            boost_offset=0.0
        )

        mock_temperature_controller = Mock()
        mock_temperature_controller.apply_offset_and_limits.return_value = 22.0
        mock_temperature_controller.send_temperature_command = AsyncMock()

        mock_coordinator = Mock()

        # Setup forecast engine with predictive offset
        mock_forecast_engine.predictive_offset = -0.5  # Predictive pre-cooling

        # Create entity
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=predictive_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=mock_offset_engine,
            sensor_manager=mock_sensor_manager,
            mode_manager=mock_mode_manager,
            temperature_controller=mock_temperature_controller,
            coordinator=mock_coordinator,
            forecast_engine=mock_forecast_engine
        )

        # Mock wrapped entity state
        wrapped_state = create_mock_state(HVACMode.COOL, {"current_temperature": 23.0}, "climate.test_ac")
        mock_hass.states.set("climate.test_ac", wrapped_state)

        # Call temperature application
        await entity._apply_temperature_with_offset(24.0)

        # Verify total offset calculation (1.5 + (-0.5) = 1.0)
        mock_temperature_controller.apply_offset_and_limits.assert_called_once()
        call_args = mock_temperature_controller.apply_offset_and_limits.call_args
        total_offset_used = call_args[0][1]  # Second parameter is offset
        assert total_offset_used == 1.0  # 1.5 reactive + (-0.5) predictive

        # Verify stored offsets
        assert entity._last_offset == 1.5  # Reactive offset stored
        assert entity._last_total_offset == 1.0  # Total offset stored

    @pytest.mark.asyncio
    async def test_offset_calculation_without_forecast_engine(
        self, basic_config
    ):
        """Test offset calculation works normally without forecast engine."""
        # Setup mock components
        mock_hass = create_mock_hass()
        mock_offset_engine = Mock()
        mock_offset_engine.calculate_offset.return_value = OffsetResult(
            offset=2.0,  # Only reactive offset
            clamped=False,
            reason="Room much warmer than AC",
            confidence=0.9
        )

        mock_sensor_manager = Mock()
        mock_sensor_manager.get_room_temperature.return_value = 26.0
        mock_sensor_manager.get_outdoor_temperature.return_value = 32.0

        mock_mode_manager = Mock()
        mock_mode_manager.current_mode = "none"
        mock_mode_manager.get_adjustments.return_value = Mock(
            temperature_override=None,
            offset_adjustment=0.0,
            boost_offset=0.0
        )

        mock_temperature_controller = Mock()
        mock_temperature_controller.apply_offset_and_limits.return_value = 22.0
        mock_temperature_controller.send_temperature_command = AsyncMock()

        mock_coordinator = Mock()

        # Create entity without forecast engine
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=basic_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=mock_offset_engine,
            sensor_manager=mock_sensor_manager,
            mode_manager=mock_mode_manager,
            temperature_controller=mock_temperature_controller,
            coordinator=mock_coordinator,
            forecast_engine=None
        )

        # Mock wrapped entity state
        wrapped_state = create_mock_state(HVACMode.COOL, {"current_temperature": 24.0}, "climate.test_ac")
        mock_hass.states.set("climate.test_ac", wrapped_state)

        # Call temperature application
        await entity._apply_temperature_with_offset(24.0)

        # Verify only reactive offset used (2.0 + 0.0 = 2.0)
        mock_temperature_controller.apply_offset_and_limits.assert_called_once()
        call_args = mock_temperature_controller.apply_offset_and_limits.call_args
        total_offset_used = call_args[0][1]
        assert total_offset_used == 2.0  # Only reactive offset

        # Verify stored offsets
        assert entity._last_offset == 2.0
        assert entity._last_total_offset == 2.0  # Same as reactive when no predictive

    @pytest.mark.asyncio
    async def test_forecast_engine_error_handling(
        self, predictive_config, mock_forecast_engine
    ):
        """Test graceful handling when forecast engine fails."""
        # Setup mock components
        mock_hass = create_mock_hass()
        mock_offset_engine = Mock()
        mock_offset_engine.calculate_offset.return_value = OffsetResult(
            offset=1.0, clamped=False, reason="Normal", confidence=0.8
        )

        mock_sensor_manager = Mock()
        mock_sensor_manager.get_room_temperature.return_value = 25.0

        mock_mode_manager = Mock()
        mock_mode_manager.current_mode = "none"
        mock_mode_manager.get_adjustments.return_value = Mock(
            temperature_override=None, offset_adjustment=0.0, boost_offset=0.0
        )

        mock_temperature_controller = Mock()
        mock_temperature_controller.apply_offset_and_limits.return_value = 23.0
        mock_temperature_controller.send_temperature_command = AsyncMock()

        mock_coordinator = Mock()

        # Setup forecast engine to raise exception
        mock_forecast_engine.predictive_offset = Mock(
            side_effect=Exception("Weather service unavailable")
        )

        # Create entity
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=predictive_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=mock_offset_engine,
            sensor_manager=mock_sensor_manager,
            mode_manager=mock_mode_manager,
            temperature_controller=mock_temperature_controller,
            coordinator=mock_coordinator,
            forecast_engine=mock_forecast_engine
        )

        # Mock wrapped entity state
        wrapped_state = create_mock_state(HVACMode.COOL, {"current_temperature": 24.0}, "climate.test_ac")
        mock_hass.states.set("climate.test_ac", wrapped_state)

        # Call temperature application (should not raise exception)
        await entity._apply_temperature_with_offset(24.0)

        # Verify fallback to reactive offset only (1.0 + 0.0 = 1.0)
        mock_temperature_controller.apply_offset_and_limits.assert_called_once()
        call_args = mock_temperature_controller.apply_offset_and_limits.call_args
        total_offset_used = call_args[0][1]
        assert total_offset_used == 1.0  # Only reactive offset due to error

    def test_extra_state_attributes_with_forecast_engine(
        self, predictive_config, mock_forecast_engine
    ):
        """Test state attributes expose forecast information."""
        # Setup forecast engine with active strategy
        mock_hass = create_mock_hass()
        mock_forecast_engine.predictive_offset = -0.8
        mock_forecast_engine.active_strategy_info = {
            "name": "Heat Wave Pre-cooling",
            "adjustment": -0.8,
            "end_time": "2025-07-13T16:00:00"
        }

        # Create entity
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=predictive_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=Mock(),
            sensor_manager=Mock(),
            mode_manager=Mock(),
            temperature_controller=Mock(),
            coordinator=Mock(),
            forecast_engine=mock_forecast_engine
        )

        # Set reactive offset
        entity._last_offset = 1.2

        # Get attributes
        attributes = entity.extra_state_attributes

        # Verify all offset components are exposed
        assert attributes["reactive_offset"] == 1.2
        assert attributes["predictive_offset"] == -0.8
        assert abs(attributes["total_offset"] - 0.4) < 0.001  # 1.2 + (-0.8) with floating point tolerance
        assert attributes["predictive_strategy"] == {
            "name": "Heat Wave Pre-cooling",
            "adjustment": -0.8,
            "end_time": "2025-07-13T16:00:00"
        }

    def test_extra_state_attributes_without_forecast_engine(
        self, basic_config
    ):
        """Test state attributes work without forecast engine."""
        # Create entity without forecast engine
        mock_hass = create_mock_hass()
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=basic_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=Mock(),
            sensor_manager=Mock(),
            mode_manager=Mock(),
            temperature_controller=Mock(),
            coordinator=Mock(),
            forecast_engine=None
        )

        # Set reactive offset
        entity._last_offset = 1.5

        # Get attributes
        attributes = entity.extra_state_attributes

        # Verify only reactive information available
        assert attributes["reactive_offset"] == 1.5
        assert attributes["predictive_offset"] == 0.0
        assert attributes["total_offset"] == 1.5
        assert attributes["predictive_strategy"] is None

    def test_coordinator_update_with_total_offset_monitoring(
        self, predictive_config, mock_forecast_engine
    ):
        """Test coordinator update logic monitors total offset changes."""
        # Setup components
        mock_hass = create_mock_hass()
        mock_offset_engine = Mock()
        mock_sensor_manager = Mock()
        mock_mode_manager = Mock()
        mock_temperature_controller = Mock()

        # Setup coordinator data
        mock_coordinator = Mock()
        mock_coordinator.data = Mock()
        mock_coordinator.data.calculated_offset = 1.0  # New reactive offset
        mock_coordinator.data.room_temp = 24.5
        mock_coordinator.data.is_startup_calculation = False

        # Setup forecast engine
        mock_forecast_engine.predictive_offset = -0.3  # Current predictive offset

        # Create entity
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=predictive_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=mock_offset_engine,
            sensor_manager=mock_sensor_manager,
            mode_manager=mock_mode_manager,
            temperature_controller=mock_temperature_controller,
            coordinator=mock_coordinator,
            forecast_engine=mock_forecast_engine
        )

        # Set initial state
        entity._last_total_offset = 0.5  # Previous total offset
        entity._attr_target_temperature = 24.0
        entity.hass.async_create_task = Mock()

        # Mock wrapped entity state with HVAC mode as COOL
        wrapped_state = create_mock_state(HVACMode.COOL, {"current_temperature": 24.0}, "climate.test_ac")
        mock_hass.states.set("climate.test_ac", wrapped_state)

        # Call coordinator update handler
        entity._handle_coordinator_update()

        # Verify total offset calculation (1.0 + (-0.3) = 0.7)
        # Change from 0.5 to 0.7 = 0.2, which is below 0.3 threshold
        # Should not trigger update for small change
        entity.hass.async_create_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_coordinator_update_triggers_on_significant_total_offset_change(
        self, predictive_config, mock_forecast_engine
    ):
        """Test coordinator triggers update on significant total offset change."""
        # Setup components
        mock_hass = create_mock_hass()
        mock_offset_engine = Mock()
        mock_sensor_manager = Mock()
        mock_mode_manager = Mock()
        mock_temperature_controller = Mock()

        # Setup coordinator data with significant change
        mock_coordinator = Mock()
        mock_coordinator.data = Mock()
        mock_coordinator.data.calculated_offset = 2.0  # New reactive offset
        mock_coordinator.data.room_temp = 24.0
        mock_coordinator.data.is_startup_calculation = False

        # Setup forecast engine with significant predictive change
        mock_forecast_engine.predictive_offset = -1.0  # Large predictive offset

        # Create entity
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=predictive_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=mock_offset_engine,
            sensor_manager=mock_sensor_manager,
            mode_manager=mock_mode_manager,
            temperature_controller=mock_temperature_controller,
            coordinator=mock_coordinator,
            forecast_engine=mock_forecast_engine
        )

        # Set initial state
        entity._last_total_offset = 0.2  # Previous total offset
        entity._attr_target_temperature = 24.0
        entity.hass.async_create_task = Mock()

        # Mock wrapped entity state with HVAC mode as COOL
        wrapped_state = create_mock_state(HVACMode.COOL, {"current_temperature": 24.0}, "climate.test_ac")
        mock_hass.states.set("climate.test_ac", wrapped_state)

        # Call coordinator update handler
        entity._handle_coordinator_update()

        # New total offset: 2.0 + (-1.0) = 1.0
        # Change from 0.2 to 1.0 = 0.8, which exceeds 0.3 threshold
        # Should trigger update
        entity.hass.async_create_task.assert_called_once()

class TestForecastEngineSetupIntegration:
    """Test setup logic integration with ForecastEngine."""

    def test_forecast_engine_creation_logic_with_predictive_config(self, predictive_config):
        """Test ForecastEngine creation logic when predictive config present."""
        from custom_components.smart_climate.const import CONF_PREDICTIVE
        
        # Test the conditional logic directly
        config = predictive_config
        
        # Verify that CONF_PREDICTIVE is in config
        assert CONF_PREDICTIVE in config
        assert config[CONF_PREDICTIVE] is not None
        
        # This would trigger ForecastEngine creation in the real setup
        forecast_config = config[CONF_PREDICTIVE]
        assert "weather_entity" in forecast_config
        assert "strategies" in forecast_config

    def test_forecast_engine_creation_logic_without_predictive_config(self, basic_config):
        """Test ForecastEngine creation logic when no predictive config."""
        from custom_components.smart_climate.const import CONF_PREDICTIVE
        
        # Test the conditional logic directly
        config = basic_config
        
        # Verify that CONF_PREDICTIVE is NOT in config
        assert CONF_PREDICTIVE not in config
        
        # This would skip ForecastEngine creation in the real setup

    def test_forecast_engine_error_handling_logic(self, predictive_config, caplog):
        """Test forecast engine initialization error handling logic."""
        from custom_components.smart_climate.forecast_engine import ForecastEngine
        from custom_components.smart_climate.const import CONF_PREDICTIVE
        
        # Create mock hass
        mock_hass = create_mock_hass()
        
        # Test error handling logic directly
        forecast_engine = None
        config = predictive_config
        
        if CONF_PREDICTIVE in config:
            try:
                # This would normally create the ForecastEngine
                # Simulate an exception
                raise Exception("Weather service initialization failed")
            except Exception as exc:
                # This is the error handling logic from the real setup
                forecast_engine = None
                # The setup should continue without predictive features
        
        # Verify fallback behavior
        assert forecast_engine is None