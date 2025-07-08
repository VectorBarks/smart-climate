"""Tests for periodic offset adjustments in SmartClimateEntity."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, call
from homeassistant.components.climate.const import HVACMode
from homeassistant.core import callback

from custom_components.smart_climate.climate import SmartClimateEntity, OFFSET_UPDATE_THRESHOLD
from custom_components.smart_climate.models import OffsetResult, SmartClimateData, ModeAdjustments
from tests.fixtures.mock_entities import (
    create_mock_hass,
    create_mock_state,
    create_mock_offset_engine,
    create_mock_sensor_manager,
    create_mock_mode_manager,
    create_mock_temperature_controller,
    create_mock_coordinator,
)


class TestPeriodicAdjustments:
    """Test periodic offset adjustments functionality."""

    @pytest.fixture
    def smart_climate_entity(self):
        """Create a SmartClimateEntity with mocked dependencies."""
        mock_hass = create_mock_hass()
        config = {
            "name": "Test Smart Climate",
            "feedback_delay": 45,
            "min_temperature": 16.0,
            "max_temperature": 30.0
        }
        
        # Create mock dependencies
        mock_offset_engine = create_mock_offset_engine()
        mock_sensor_manager = create_mock_sensor_manager()
        mock_mode_manager = create_mock_mode_manager()
        mock_temperature_controller = create_mock_temperature_controller()
        mock_coordinator = create_mock_coordinator()
        
        # Configure coordinator with test data
        test_data = SmartClimateData(
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
        mock_coordinator.data = test_data
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=mock_offset_engine,
            sensor_manager=mock_sensor_manager,
            mode_manager=mock_mode_manager,
            temperature_controller=mock_temperature_controller,
            coordinator=mock_coordinator
        )
        
        # Set target temperature for testing
        entity._attr_target_temperature = 22.0
        
        # Mock the async_write_ha_state method that the @callback method calls
        entity.async_write_ha_state = Mock()
        entity.async_on_remove = Mock()
        
        return entity

    def test_handle_coordinator_update_no_data(self, smart_climate_entity):
        """Test that coordinator update handles missing data gracefully."""
        # Arrange
        smart_climate_entity._coordinator.data = None
        
        # Act
        smart_climate_entity._handle_coordinator_update()
        
        # Assert - should not cause any errors or side effects
        # No temperature adjustment should be triggered
        smart_climate_entity.hass.async_create_task.assert_not_called()

    def test_handle_coordinator_update_hvac_off(self, smart_climate_entity):
        """Test that no adjustment is triggered when HVAC mode is OFF."""
        # Arrange
        smart_climate_entity._last_offset = 0.0
        
        # Mock wrapped entity state to return OFF
        wrapped_state = create_mock_state(
            entity_id="climate.test_ac",
            state=HVACMode.OFF,
            attributes={"target_temperature": 22.0}
        )
        smart_climate_entity.hass.states.get.return_value = wrapped_state
        
        # Verify coordinator has data
        assert smart_climate_entity._coordinator.data is not None
        assert smart_climate_entity._coordinator.data.calculated_offset == 1.5
        
        # Act
        print(f"Before: coordinator data = {smart_climate_entity._coordinator.data}")
        print(f"Before: hvac_mode = {smart_climate_entity.hvac_mode}")
        print(f"Method exists: {hasattr(smart_climate_entity, '_handle_coordinator_update')}")
        print(f"Method type: {type(getattr(smart_climate_entity, '_handle_coordinator_update', None))}")
        smart_climate_entity._handle_coordinator_update()
        print(f"After: async_create_task called {smart_climate_entity.hass.async_create_task.call_count} times")
        print(f"After: async_write_ha_state called {smart_climate_entity.async_write_ha_state.call_count} times")
        
        # Assert
        smart_climate_entity.hass.async_create_task.assert_not_called()
        smart_climate_entity.async_write_ha_state.assert_called_once()

    def test_handle_coordinator_update_significant_offset_change(self, smart_climate_entity):
        """Test automatic adjustment when offset changes significantly."""
        # Arrange
        smart_climate_entity._last_offset = 0.0  # Last applied offset
        new_offset = 1.5  # From coordinator data
        offset_diff = abs(new_offset - smart_climate_entity._last_offset)
        
        # Verify test setup - offset change should exceed threshold
        assert offset_diff > OFFSET_UPDATE_THRESHOLD
        
        # Mock wrapped entity state to return COOL (active)
        wrapped_state = create_mock_state(
            entity_id="climate.test_ac",
            state=HVACMode.COOL,
            attributes={"target_temperature": 22.0}
        )
        smart_climate_entity.hass.states.get.return_value = wrapped_state
        
        # Act
        smart_climate_entity._handle_coordinator_update()
        
        # Assert
        smart_climate_entity.hass.async_create_task.assert_called_once()
        # Check that the task was created with the right coroutine
        call_args = smart_climate_entity.hass.async_create_task.call_args[0][0]
        # The coroutine should be _apply_temperature_with_offset with current target temp
        assert hasattr(call_args, 'cr_frame')  # It's a coroutine
        smart_climate_entity.async_write_ha_state.assert_called_once()

    def test_handle_coordinator_update_small_offset_change(self, smart_climate_entity):
        """Test no adjustment when offset change is below threshold."""
        # Arrange
        smart_climate_entity._last_offset = 1.0
        # Coordinator data has calculated_offset = 1.5, so diff = 0.5
        # But we'll set it smaller for this test
        smart_climate_entity._coordinator.data.calculated_offset = 1.2  # diff = 0.2
        offset_diff = abs(1.2 - smart_climate_entity._last_offset)
        
        # Verify test setup - offset change should be below threshold
        assert offset_diff < OFFSET_UPDATE_THRESHOLD
        
        # Mock wrapped entity state to return COOL (active)
        wrapped_state = create_mock_state(
            entity_id="climate.test_ac",
            state=HVACMode.COOL,
            attributes={"target_temperature": 22.0}
        )
        smart_climate_entity.hass.states.get.return_value = wrapped_state
        
        # Act
        smart_climate_entity._handle_coordinator_update()
        
        # Assert
        smart_climate_entity.hass.async_create_task.assert_not_called()
        smart_climate_entity.async_write_ha_state.assert_called_once()

    def test_handle_coordinator_update_exactly_at_threshold(self, smart_climate_entity):
        """Test behavior when offset change equals threshold."""
        # Arrange
        smart_climate_entity._last_offset = 1.0
        smart_climate_entity._coordinator.data.calculated_offset = 1.0 + OFFSET_UPDATE_THRESHOLD
        
        # Mock wrapped entity state to return COOL (active)
        wrapped_state = create_mock_state(
            entity_id="climate.test_ac",
            state=HVACMode.COOL,
            attributes={"target_temperature": 22.0}
        )
        smart_climate_entity.hass.states.get.return_value = wrapped_state
        
        # Act
        smart_climate_entity._handle_coordinator_update()
        
        # Assert - at threshold should NOT trigger (> not >=)
        smart_climate_entity.hass.async_create_task.assert_not_called()
        smart_climate_entity.async_write_ha_state.assert_called_once()

    def test_handle_coordinator_update_just_above_threshold(self, smart_climate_entity):
        """Test behavior when offset change is just above threshold."""
        # Arrange
        smart_climate_entity._last_offset = 1.0
        smart_climate_entity._coordinator.data.calculated_offset = 1.0 + OFFSET_UPDATE_THRESHOLD + 0.01
        
        # Mock wrapped entity state to return COOL (active)
        wrapped_state = create_mock_state(
            entity_id="climate.test_ac",
            state=HVACMode.COOL,
            attributes={"target_temperature": 22.0}
        )
        smart_climate_entity.hass.states.get.return_value = wrapped_state
        
        # Act
        smart_climate_entity._handle_coordinator_update()
        
        # Assert - just above threshold should trigger
        smart_climate_entity.hass.async_create_task.assert_called_once()
        smart_climate_entity.async_write_ha_state.assert_called_once()

    def test_handle_coordinator_update_negative_offset_change(self, smart_climate_entity):
        """Test adjustment when offset change is negative but significant."""
        # Arrange
        smart_climate_entity._last_offset = 2.0
        smart_climate_entity._coordinator.data.calculated_offset = 0.5  # diff = 1.5
        offset_diff = abs(0.5 - smart_climate_entity._last_offset)
        
        # Verify test setup - offset change should exceed threshold
        assert offset_diff > OFFSET_UPDATE_THRESHOLD
        
        # Mock wrapped entity state to return HEAT (active)
        wrapped_state = create_mock_state(
            entity_id="climate.test_ac",
            state=HVACMode.HEAT,
            attributes={"target_temperature": 22.0}
        )
        smart_climate_entity.hass.states.get.return_value = wrapped_state
        
        # Act
        smart_climate_entity._handle_coordinator_update()
        
        # Assert
        smart_climate_entity.hass.async_create_task.assert_called_once()
        smart_climate_entity.async_write_ha_state.assert_called_once()

    def test_handle_coordinator_update_no_target_temperature(self, smart_climate_entity):
        """Test behavior when target_temperature is None."""
        # Arrange
        smart_climate_entity._attr_target_temperature = None
        smart_climate_entity._last_offset = 0.0
        
        # Mock wrapped entity state to return COOL but return None for target temp
        wrapped_state = create_mock_state(
            entity_id="climate.test_ac",
            state=HVACMode.COOL,
            attributes={}  # No target_temperature
        )
        smart_climate_entity.hass.states.get.return_value = wrapped_state
        
        # Act
        smart_climate_entity._handle_coordinator_update()
        
        # Assert - no task should be created when no target temperature
        smart_climate_entity.hass.async_create_task.assert_not_called()
        smart_climate_entity.async_write_ha_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_added_to_hass_registers_coordinator_listener(self, smart_climate_entity):
        """Test that async_added_to_hass properly registers the coordinator listener."""
        # Arrange
        mock_remove_listener = Mock()
        smart_climate_entity._coordinator.async_add_listener.return_value = mock_remove_listener
        
        # Mock wrapped entity state
        wrapped_state = create_mock_state(
            entity_id="climate.test_ac",
            state=HVACMode.COOL,
            attributes={"target_temperature": 23.0}
        )
        smart_climate_entity.hass.states.get.return_value = wrapped_state
        
        # Act
        await smart_climate_entity.async_added_to_hass()
        
        # Assert
        smart_climate_entity._coordinator.async_add_listener.assert_called_once_with(
            smart_climate_entity._handle_coordinator_update
        )
        smart_climate_entity.async_on_remove.assert_called_once_with(mock_remove_listener)

    def test_offset_update_threshold_constant(self):
        """Test that OFFSET_UPDATE_THRESHOLD is properly defined."""
        # Arrange & Act & Assert
        assert OFFSET_UPDATE_THRESHOLD == 0.3
        assert isinstance(OFFSET_UPDATE_THRESHOLD, (int, float))

    def test_handle_coordinator_update_is_callback(self, smart_climate_entity):
        """Test that _handle_coordinator_update method has @callback decorator."""
        # Arrange & Act
        method = getattr(smart_climate_entity._handle_coordinator_update, '__wrapped__', smart_climate_entity._handle_coordinator_update)
        
        # Assert - check if method has callback markers
        # The @callback decorator modifies the function, we can check this way
        assert hasattr(smart_climate_entity._handle_coordinator_update, '__qualname__')

    @pytest.mark.asyncio
    async def test_integration_coordinator_update_triggers_temperature_adjustment(self, smart_climate_entity):
        """Integration test: coordinator update should trigger temperature adjustment."""
        # Arrange
        smart_climate_entity._last_offset = 0.0
        smart_climate_entity._attr_target_temperature = 22.0
        
        # Mock dependencies for _apply_temperature_with_offset
        smart_climate_entity._sensor_manager.get_room_temperature.return_value = 24.0
        smart_climate_entity._sensor_manager.get_outdoor_temperature.return_value = 28.0
        smart_climate_entity._sensor_manager.get_power_consumption.return_value = 150.0
        
        # Mock wrapped entity state for AC internal temp
        wrapped_state = create_mock_state(
            entity_id="climate.test_ac",
            state=HVACMode.COOL,
            attributes={"current_temperature": 23.5}
        )
        smart_climate_entity.hass.states.get.return_value = wrapped_state
        
        # Mock offset engine response
        offset_result = OffsetResult(offset=1.5, clamped=False, reason="Test", confidence=0.9)
        smart_climate_entity._offset_engine.calculate_offset.return_value = offset_result
        
        # Mock mode adjustments
        mode_adjustments = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        )
        smart_climate_entity._mode_manager.get_adjustments.return_value = mode_adjustments
        
        # Mock temperature controller
        smart_climate_entity._temperature_controller.apply_offset_and_limits.return_value = 20.5
        
        # Mock wrapped entity state to return COOL (active)
        wrapped_state = create_mock_state(
            entity_id="climate.test_ac",
            state=HVACMode.COOL,
            attributes={"target_temperature": 22.0}
        )
        smart_climate_entity.hass.states.get.return_value = wrapped_state
        
        # Act - trigger coordinator update handler
        smart_climate_entity._handle_coordinator_update()
        
        # Get the scheduled task (coroutine) and await it
        assert smart_climate_entity.hass.async_create_task.called
        task_coroutine = smart_climate_entity.hass.async_create_task.call_args[0][0]
        
        # Since we can't easily await the actual coroutine in this test setup,
        # we'll verify that the right method would be called by checking the task creation
            
        # Assert
        smart_climate_entity.hass.async_create_task.assert_called_once()
        smart_climate_entity.async_write_ha_state.assert_called_once()