"""Test the feedback offset calculation in Smart Climate."""

import pytest
from unittest.mock import Mock
from datetime import datetime

from homeassistant.components.climate.const import HVACMode

from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.models import OffsetInput
from tests.fixtures.mock_entities import (
    create_mock_hass,
    create_mock_offset_engine,
    create_mock_sensor_manager,
    create_mock_mode_manager,
    create_mock_temperature_controller,
    create_mock_coordinator
)


class TestFeedbackOffsetCalculation:
    """Test the feedback offset calculation in Smart Climate."""

    @pytest.mark.asyncio
    async def test_feedback_offset_calculation_cooling_scenario(self):
        """Test that feedback calculates the correct offset when AC is cooling.
        
        Scenario: Room is warmer than desired, AC is cooling
        - Room temp: 25.0°C (warmer)
        - AC internal temp: 22.0°C (cooler because it's actively cooling)
        - Expected actual offset: -3.0°C (negative offset needed to cool more)
        """
        # Create mocks
        hass = create_mock_hass()
        offset_engine = create_mock_offset_engine()
        offset_engine._enable_learning = True
        offset_engine.record_actual_performance = Mock()
        
        sensor_manager = create_mock_sensor_manager()
        sensor_manager.get_room_temperature = Mock(return_value=25.0)
        
        mode_manager = create_mock_mode_manager()
        temperature_controller = create_mock_temperature_controller()
        coordinator = create_mock_coordinator()
        
        # Create entity
        config = {
            "climate_entity": "climate.test_ac",
            "room_sensor": "sensor.room_temp",
            "feedback_delay": 1  # Short delay for testing
        }
        
        entity = SmartClimateEntity(
            hass,
            config,
            "climate.test_ac",
            "sensor.room_temp",
            offset_engine,
            sensor_manager,
            mode_manager,
            temperature_controller,
            coordinator
        )
        
        # Set up the wrapped entity state with AC internal temperature
        mock_state = Mock()
        mock_state.attributes = {
            "current_temperature": 22.0,  # AC thinks it's cooler
            "target_temperature": 24.0
        }
        hass.states.get.return_value = mock_state
        
        # Set room temperature
        sensor_manager.get_room_temperature.return_value = 25.0
        
        # Store prediction data (simulating a previous offset calculation)
        entity._last_predicted_offset = -2.5  # We predicted -2.5°C offset
        entity._last_offset_input = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=25.0,
            outdoor_temp=None,
            mode="none",
            power_consumption=None,
            time_of_day=datetime.now().time(),
            day_of_week=datetime.now().weekday()
        )
        
        # Call the feedback collection method
        await entity._collect_learning_feedback(None)
        
        # Verify the offset was calculated correctly
        # The actual offset should be: AC temp (22) - Room temp (25) = -3.0
        # This negative offset means we need to cool MORE
        offset_engine.record_actual_performance.assert_called_once()
        
        call_args = offset_engine.record_actual_performance.call_args
        assert call_args[1]["predicted_offset"] == -2.5
        assert call_args[1]["actual_offset"] == -3.0  # Should be negative for cooling
        assert call_args[1]["input_data"] == entity._last_offset_input

    @pytest.mark.asyncio
    async def test_feedback_offset_calculation_heating_scenario(self):
        """Test that feedback calculates the correct offset when room is cooler than AC sensor.
        
        Scenario: Room is cooler than AC sensor (AC overcooled)
        - Room temp: 22.0°C (cooler)
        - AC internal temp: 25.0°C (warmer)
        - Expected actual offset: 3.0°C (positive offset needed to cool less)
        """
        # Create mocks
        hass = create_mock_hass()
        offset_engine = create_mock_offset_engine()
        offset_engine._enable_learning = True
        offset_engine.record_actual_performance = Mock()
        
        sensor_manager = create_mock_sensor_manager()
        sensor_manager.get_room_temperature = Mock(return_value=22.0)
        
        mode_manager = create_mock_mode_manager()
        temperature_controller = create_mock_temperature_controller()
        coordinator = create_mock_coordinator()
        
        # Create entity
        config = {
            "climate_entity": "climate.test_ac",
            "room_sensor": "sensor.room_temp",
            "feedback_delay": 1
        }
        
        entity = SmartClimateEntity(
            hass,
            config,
            "climate.test_ac",
            "sensor.room_temp",
            offset_engine,
            sensor_manager,
            mode_manager,
            temperature_controller,
            coordinator
        )
        
        # Set up the wrapped entity state
        mock_state = Mock()
        mock_state.attributes = {
            "current_temperature": 25.0,  # AC thinks it's warmer
            "target_temperature": 24.0
        }
        hass.states.get.return_value = mock_state
        
        # Set room temperature
        sensor_manager.get_room_temperature.return_value = 22.0
        
        # Store prediction data
        entity._last_predicted_offset = 2.5
        entity._last_offset_input = OffsetInput(
            ac_internal_temp=25.0,
            room_temp=22.0,
            outdoor_temp=None,
            mode="none",
            power_consumption=None,
            time_of_day=datetime.now().time(),
            day_of_week=datetime.now().weekday()
        )
        
        # Call the feedback collection method
        await entity._collect_learning_feedback(None)
        
        # Verify the offset was calculated correctly
        # The actual offset should be: AC temp (25) - Room temp (22) = 3.0
        # This positive offset means we need to cool LESS
        offset_engine.record_actual_performance.assert_called_once()
        
        call_args = offset_engine.record_actual_performance.call_args
        assert call_args[1]["predicted_offset"] == 2.5
        assert call_args[1]["actual_offset"] == 3.0  # Should be positive when room is cooler

    @pytest.mark.asyncio
    async def test_feedback_not_collected_when_learning_disabled(self):
        """Test that feedback is not collected when learning is disabled."""
        # Create mocks
        hass = create_mock_hass()
        offset_engine = create_mock_offset_engine()
        offset_engine._enable_learning = False  # Disable learning
        offset_engine.record_actual_performance = Mock()
        
        sensor_manager = create_mock_sensor_manager()
        mode_manager = create_mock_mode_manager()
        temperature_controller = create_mock_temperature_controller()
        coordinator = create_mock_coordinator()
        
        config = {
            "climate_entity": "climate.test_ac",
            "room_sensor": "sensor.room_temp",
            "feedback_delay": 1
        }
        
        entity = SmartClimateEntity(
            hass,
            config,
            "climate.test_ac",
            "sensor.room_temp",
            offset_engine,
            sensor_manager,
            mode_manager,
            temperature_controller,
            coordinator
        )
        
        # Set up state
        hass.states.async_set("climate.test_ac", HVACMode.COOL, {
            "current_temperature": 22.0,
            "target_temperature": 24.0
        })
        
        # Store prediction data
        entity._last_predicted_offset = -2.5
        entity._last_offset_input = Mock()
        
        # Call the feedback collection method
        await entity._collect_learning_feedback(None)
        
        # Verify record_actual_performance was NOT called
        offset_engine.record_actual_performance.assert_not_called()

    @pytest.mark.asyncio
    async def test_feedback_handles_missing_data_gracefully(self):
        """Test that feedback collection handles missing data gracefully."""
        # Create mocks
        hass = create_mock_hass()
        offset_engine = create_mock_offset_engine()
        offset_engine._enable_learning = True
        offset_engine.record_actual_performance = Mock()
        
        sensor_manager = create_mock_sensor_manager()
        mode_manager = create_mock_mode_manager()
        temperature_controller = create_mock_temperature_controller()
        coordinator = create_mock_coordinator()
        
        config = {
            "climate_entity": "climate.test_ac",
            "room_sensor": "sensor.room_temp",
            "feedback_delay": 1
        }
        
        entity = SmartClimateEntity(
            hass,
            config,
            "climate.test_ac",
            "sensor.room_temp",
            offset_engine,
            sensor_manager,
            mode_manager,
            temperature_controller,
            coordinator
        )
        
        # Test with no prediction data
        await entity._collect_learning_feedback(None)
        offset_engine.record_actual_performance.assert_not_called()
        
        # Test with missing room temperature
        entity._last_predicted_offset = -2.5
        entity._last_offset_input = Mock()
        sensor_manager.get_room_temperature.return_value = None
        
        await entity._collect_learning_feedback(None)
        offset_engine.record_actual_performance.assert_not_called()
        
        # Test with missing wrapped entity
        sensor_manager.get_room_temperature.return_value = 25.0
        hass.states.async_remove("climate.test_ac")
        
        await entity._collect_learning_feedback(None)
        offset_engine.record_actual_performance.assert_not_called()