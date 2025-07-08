"""Simple functional tests for periodic offset adjustments."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from homeassistant.components.climate.const import HVACMode

from custom_components.smart_climate.climate import SmartClimateEntity, OFFSET_UPDATE_THRESHOLD
from custom_components.smart_climate.models import SmartClimateData, ModeAdjustments


def test_offset_update_threshold_constant():
    """Test that OFFSET_UPDATE_THRESHOLD is properly defined."""
    assert OFFSET_UPDATE_THRESHOLD == 0.3
    assert isinstance(OFFSET_UPDATE_THRESHOLD, (int, float))


def test_handle_coordinator_update_method_exists():
    """Test that the _handle_coordinator_update method exists and is callable."""
    # Create a minimal entity instance to test method existence
    mock_hass = Mock()
    mock_hass.states.get.return_value = None
    
    entity = SmartClimateEntity(
        hass=mock_hass,
        config={},
        wrapped_entity_id="climate.test",
        room_sensor_id="sensor.room",
        offset_engine=Mock(),
        sensor_manager=Mock(),
        mode_manager=Mock(),
        temperature_controller=Mock(),
        coordinator=Mock()
    )
    
    # Test method exists and is callable
    assert hasattr(entity, '_handle_coordinator_update')
    assert callable(getattr(entity, '_handle_coordinator_update'))


def test_handle_coordinator_update_logic_hvac_off():
    """Test the core logic when HVAC mode is OFF."""
    # Create entity with minimal mocking
    mock_hass = Mock()
    mock_coordinator = Mock()
    
    # Set up coordinator data
    mock_coordinator.data = SmartClimateData(
        room_temp=24.0,
        outdoor_temp=28.0,
        power=150.0,
        calculated_offset=1.5,
        mode_adjustments=ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        )
    )
    
    entity = SmartClimateEntity(
        hass=mock_hass,
        config={},
        wrapped_entity_id="climate.test",
        room_sensor_id="sensor.room",
        offset_engine=Mock(),
        sensor_manager=Mock(),
        mode_manager=Mock(),
        temperature_controller=Mock(),
        coordinator=mock_coordinator
    )
    
    # Mock the methods we expect to be called
    entity.async_write_ha_state = Mock()
    entity._last_offset = 0.0
    
    # Mock wrapped entity state to return OFF (this affects hvac_mode property)
    mock_wrapped_state = Mock()
    mock_wrapped_state.state = HVACMode.OFF
    mock_wrapped_state.attributes = {"target_temperature": 22.0}
    mock_hass.states.get.return_value = mock_wrapped_state
    
    # Call the method directly
    entity._handle_coordinator_update()
    
    # Assert async_write_ha_state was called (state update)
    entity.async_write_ha_state.assert_called_once()
    
    # Assert no task was created for temperature adjustment
    mock_hass.async_create_task.assert_not_called()


def test_handle_coordinator_update_logic_significant_change():
    """Test the core logic when offset changes significantly."""
    mock_hass = Mock()
    mock_coordinator = Mock()
    
    # Set up coordinator data with significant offset
    mock_coordinator.data = SmartClimateData(
        room_temp=24.0,
        outdoor_temp=28.0,
        power=150.0,
        calculated_offset=1.5,  # Significant change from 0.0
        mode_adjustments=ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        )
    )
    
    entity = SmartClimateEntity(
        hass=mock_hass,
        config={},
        wrapped_entity_id="climate.test",
        room_sensor_id="sensor.room",
        offset_engine=Mock(),
        sensor_manager=Mock(),
        mode_manager=Mock(),
        temperature_controller=Mock(),
        coordinator=mock_coordinator
    )
    
    # Mock the methods and properties
    entity.async_write_ha_state = Mock()
    entity._last_offset = 0.0  # Last offset significantly different from 1.5
    entity._attr_target_temperature = 22.0
    
    # Mock wrapped entity state to return COOL (active)
    mock_wrapped_state = Mock()
    mock_wrapped_state.state = HVACMode.COOL
    mock_wrapped_state.attributes = {"target_temperature": 22.0}
    mock_hass.states.get.return_value = mock_wrapped_state
    
    # Verify the offset difference exceeds threshold
    offset_diff = abs(1.5 - 0.0)
    assert offset_diff > OFFSET_UPDATE_THRESHOLD
    
    # Call the method directly
    entity._handle_coordinator_update()
    
    # Assert state update was called
    entity.async_write_ha_state.assert_called_once()
    
    # Assert a task was created for temperature adjustment
    mock_hass.async_create_task.assert_called_once()


def test_handle_coordinator_update_logic_small_change():
    """Test the core logic when offset change is below threshold."""
    mock_hass = Mock()
    mock_coordinator = Mock()
    
    # Set up coordinator data with small offset change
    mock_coordinator.data = SmartClimateData(
        room_temp=24.0,
        outdoor_temp=28.0,
        power=150.0,
        calculated_offset=0.2,  # Small change from 0.0
        mode_adjustments=ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        )
    )
    
    entity = SmartClimateEntity(
        hass=mock_hass,
        config={},
        wrapped_entity_id="climate.test",
        room_sensor_id="sensor.room",
        offset_engine=Mock(),
        sensor_manager=Mock(),
        mode_manager=Mock(),
        temperature_controller=Mock(),
        coordinator=mock_coordinator
    )
    
    # Mock the methods and properties
    entity.async_write_ha_state = Mock()
    entity._last_offset = 0.0  # Small difference from 0.2
    
    # Mock wrapped entity state to return COOL (active)
    mock_wrapped_state = Mock()
    mock_wrapped_state.state = HVACMode.COOL
    mock_wrapped_state.attributes = {"target_temperature": 22.0}
    mock_hass.states.get.return_value = mock_wrapped_state
    
    # Verify the offset difference is below threshold
    offset_diff = abs(0.2 - 0.0)
    assert offset_diff < OFFSET_UPDATE_THRESHOLD
    
    # Call the method directly
    entity._handle_coordinator_update()
    
    # Assert state update was called
    entity.async_write_ha_state.assert_called_once()
    
    # Assert no task was created for temperature adjustment
    mock_hass.async_create_task.assert_not_called()


def test_handle_coordinator_update_no_data():
    """Test behavior when coordinator has no data."""
    mock_hass = Mock()
    mock_coordinator = Mock()
    mock_coordinator.data = None  # No data
    
    entity = SmartClimateEntity(
        hass=mock_hass,
        config={},
        wrapped_entity_id="climate.test",
        room_sensor_id="sensor.room",
        offset_engine=Mock(),
        sensor_manager=Mock(),
        mode_manager=Mock(),
        temperature_controller=Mock(),
        coordinator=mock_coordinator
    )
    
    entity.async_write_ha_state = Mock()
    
    # Call the method directly
    entity._handle_coordinator_update()
    
    # Assert no methods were called - early return
    entity.async_write_ha_state.assert_not_called()
    mock_hass.async_create_task.assert_not_called()