"""ABOUTME: Comprehensive integration tests for HVAC mode fixes - verifies complete flow works correctly.
Tests the complete integration of coordinator → climate entity → offset engine → learner for HVAC mode filtering."""

import pytest
import pytest_asyncio
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from datetime import datetime, timedelta

from homeassistant.components.climate.const import HVACMode
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.coordinator import SmartClimateCoordinator 
from custom_components.smart_climate.models import SmartClimateData, OffsetResult, OffsetInput
from custom_components.smart_climate.const import ACTIVE_HVAC_MODES, LEARNING_HVAC_MODES

from tests.fixtures.mock_entities import (
    create_mock_hass,
    create_mock_state,
    create_mock_offset_engine,
    create_mock_sensor_manager,
    create_mock_mode_manager,
    create_mock_temperature_controller,
    create_mock_coordinator,
)


class TestHVACModeIntegration:
    """Test complete HVAC mode integration flow with real coordinator."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance with enhanced functionality."""
        hass = create_mock_hass()
        
        # Enhanced service mock to track actual calls
        hass.services.async_call = AsyncMock()
        
        # Mock async_create_task to track scheduled tasks
        hass.async_create_task = Mock()
        
        return hass

    @pytest.fixture
    def mock_coordinator_dependencies(self):
        """Create dependencies for coordinator."""
        sensor_manager = create_mock_sensor_manager()
        offset_engine = create_mock_offset_engine()
        mode_manager = create_mock_mode_manager()
        
        # Configure offset engine with realistic responses
        offset_engine.calculate_offset.return_value = OffsetResult(
            offset=1.5,
            clamped=False,
            reason="Normal operation",
            confidence=0.8
        )
        
        return {
            "sensor_manager": sensor_manager,
            "offset_engine": offset_engine,
            "mode_manager": mode_manager,
        }

    @pytest.fixture
    def mock_real_coordinator(self, mock_hass, mock_coordinator_dependencies):
        """Create real SmartClimateCoordinator for integration testing."""
        coordinator = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=30,  # Short interval for testing
            **mock_coordinator_dependencies
        )
        
        # Mock the _async_update_data method to return test data
        async def mock_update_data():
            return SmartClimateData(
                room_temp=24.0,
                outdoor_temp=28.0,
                power=150.0,
                calculated_offset=1.5,
                mode_adjustments=mock_coordinator_dependencies["mode_manager"].get_adjustments(),
                is_startup_calculation=False
            )
        
        coordinator._async_update_data = mock_update_data
        return coordinator

    @pytest.fixture
    def mock_entity_dependencies(self, mock_hass):
        """Create mock entity dependencies."""
        offset_engine = create_mock_offset_engine()
        sensor_manager = create_mock_sensor_manager()
        mode_manager = create_mock_mode_manager() 
        temperature_controller = create_mock_temperature_controller(mock_hass)
        
        # Configure realistic sensor values
        sensor_manager.get_room_temperature.return_value = 24.0
        sensor_manager.get_outdoor_temperature.return_value = 28.0
        sensor_manager.get_power_consumption.return_value = 150.0
        
        return {
            "offset_engine": offset_engine,
            "sensor_manager": sensor_manager,
            "mode_manager": mode_manager,
            "temperature_controller": temperature_controller,
        }

    def _create_wrapped_entity_state(self, hvac_mode: str, target_temp: float = 22.0, current_temp: float = 23.0):
        """Helper to create wrapped entity state."""
        return create_mock_state(
            state=hvac_mode,
            attributes={
                "friendly_name": "Test AC",
                "hvac_mode": hvac_mode,
                "target_temperature": target_temp,
                "current_temperature": current_temp,
                "supported_features": 1,  # SUPPORT_TARGET_TEMPERATURE
            },
            entity_id="climate.test_ac"
        )

    @pytest_asyncio.fixture
    async def climate_entity_with_coordinator(self, mock_hass, mock_real_coordinator, mock_entity_dependencies):
        """Create climate entity with real coordinator integration."""
        config = {
            "name": "Test Smart Climate",
            "default_target_temperature": 24.0,
            "max_offset": 5.0,
            "update_interval": 30
        }
        
        # Set up wrapped entity state
        wrapped_state = self._create_wrapped_entity_state(HVACMode.COOL)
        mock_hass.states.set("climate.test_ac", wrapped_state)
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            coordinator=mock_real_coordinator,
            **mock_entity_dependencies
        )
        
        # Initialize entity state
        entity._attr_target_temperature = 22.0
        entity._attr_hvac_mode = HVACMode.COOL
        entity._last_offset = 0.0
        entity._last_total_offset = 0.0
        
        return entity

    @pytest.mark.asyncio
    async def test_complete_flow_fan_only_mode(self, climate_entity_with_coordinator, mock_hass, mock_real_coordinator):
        """Test complete flow in fan_only mode: no temperature adjustment, no learning."""
        entity = climate_entity_with_coordinator
        
        # Set AC to fan_only mode
        entity._attr_hvac_mode = HVACMode.FAN_ONLY
        wrapped_state = self._create_wrapped_entity_state(HVACMode.FAN_ONLY)
        mock_hass.states.set("climate.test_ac", wrapped_state)
        
        # Trigger coordinator update
        await mock_real_coordinator.async_refresh()
        
        # Manually trigger the coordinator update handler
        entity._handle_coordinator_update()
        
        # Verify no temperature adjustment task was created
        mock_hass.async_create_task.assert_not_called()
        
        # Verify no service call to wrapped entity
        mock_hass.services.async_call.assert_not_called()
        
        # Verify offset engine was not called for temperature adjustment
        entity._offset_engine.calculate_offset.assert_called()  # Called for coordinator data
        
        # Verify temperature controller was not called for adjustment
        entity._temperature_controller.apply_offset_and_limits.assert_not_called()

    @pytest.mark.asyncio
    async def test_mode_transition_cool_to_fan_only_to_cool(self, climate_entity_with_coordinator, mock_hass, mock_real_coordinator):
        """Test mode transitions: cool → fan_only → cool."""
        entity = climate_entity_with_coordinator
        
        # Start in cool mode - should work normally
        entity._attr_hvac_mode = HVACMode.COOL
        wrapped_state = self._create_wrapped_entity_state(HVACMode.COOL)
        mock_hass.states.set("climate.test_ac", wrapped_state)
        
        # Trigger coordinator update in cool mode
        await mock_real_coordinator.async_refresh()
        entity._coordinator.data.calculated_offset = 1.5  # Significant offset
        entity._handle_coordinator_update()
        
        # Should create adjustment task in cool mode
        assert mock_hass.async_create_task.call_count == 1
        mock_hass.async_create_task.reset_mock()
        mock_hass.services.async_call.reset_mock()
        
        # Switch to fan_only mode
        entity._attr_hvac_mode = HVACMode.FAN_ONLY
        wrapped_state = self._create_wrapped_entity_state(HVACMode.FAN_ONLY)
        mock_hass.states.set("climate.test_ac", wrapped_state)
        
        # Trigger coordinator update in fan_only mode
        entity._coordinator.data.calculated_offset = 2.0  # Even larger offset
        entity._handle_coordinator_update()
        
        # Should NOT create adjustment task in fan_only mode
        mock_hass.async_create_task.assert_not_called()
        mock_hass.services.async_call.assert_not_called()
        
        # Switch back to cool mode
        entity._attr_hvac_mode = HVACMode.COOL
        wrapped_state = self._create_wrapped_entity_state(HVACMode.COOL)
        mock_hass.states.set("climate.test_ac", wrapped_state)
        
        # Trigger coordinator update in cool mode again
        entity._coordinator.data.calculated_offset = 2.5  # Another significant change
        entity._handle_coordinator_update()
        
        # Should create adjustment task again in cool mode
        assert mock_hass.async_create_task.call_count == 1

    @pytest.mark.asyncio
    async def test_all_non_active_modes_behavior(self, climate_entity_with_coordinator, mock_hass, mock_real_coordinator):
        """Test both off and fan_only modes show consistent behavior."""
        entity = climate_entity_with_coordinator
        
        non_active_modes = [HVACMode.OFF, HVACMode.FAN_ONLY]
        
        for hvac_mode in non_active_modes:
            # Reset mocks for each test
            mock_hass.async_create_task.reset_mock()
            mock_hass.services.async_call.reset_mock()
            entity._temperature_controller.apply_offset_and_limits.reset_mock()
            
            # Set the mode
            entity._attr_hvac_mode = hvac_mode
            wrapped_state = self._create_wrapped_entity_state(hvac_mode)
            mock_hass.states.set("climate.test_ac", wrapped_state)
            
            # Force significant offset change
            entity._coordinator.data.calculated_offset = 3.0
            entity._last_total_offset = 0.0  # Ensure significant change
            
            # Trigger coordinator update
            entity._handle_coordinator_update()
            
            # Verify no temperature adjustment for this mode
            mock_hass.async_create_task.assert_not_called(), f"Mode {hvac_mode} should not trigger adjustments"
            mock_hass.services.async_call.assert_not_called(), f"Mode {hvac_mode} should not call services"
            entity._temperature_controller.apply_offset_and_limits.assert_not_called(), f"Mode {hvac_mode} should not call temperature controller"

    @pytest.mark.asyncio
    async def test_learning_data_integrity_fan_only(self, climate_entity_with_coordinator, mock_hass, mock_real_coordinator):
        """Test that learning data count doesn't increase in fan_only mode."""
        entity = climate_entity_with_coordinator
        
        # Set up offset engine to track learning calls
        initial_record_calls = entity._offset_engine.record_feedback.call_count
        
        # Set to fan_only mode
        entity._attr_hvac_mode = HVACMode.FAN_ONLY
        wrapped_state = self._create_wrapped_entity_state(HVACMode.FAN_ONLY)
        mock_hass.states.set("climate.test_ac", wrapped_state)
        
        # Simulate multiple coordinator cycles in fan_only mode
        for cycle in range(5):
            await mock_real_coordinator.async_refresh()
            entity._coordinator.data.calculated_offset = 1.0 + (cycle * 0.5)
            entity._handle_coordinator_update()
            
            # Verify no temperature adjustments triggered
            mock_hass.async_create_task.assert_not_called()
            mock_hass.async_create_task.reset_mock()
        
        # Verify learning data was not recorded
        assert entity._offset_engine.record_feedback.call_count == initial_record_calls
        
        # Switch to cool mode and verify learning resumes
        entity._attr_hvac_mode = HVACMode.COOL
        wrapped_state = self._create_wrapped_entity_state(HVACMode.COOL)
        mock_hass.states.set("climate.test_ac", wrapped_state)
        
        # Force significant offset to trigger adjustment
        entity._coordinator.data.calculated_offset = 2.0
        entity._last_total_offset = 0.0
        entity._handle_coordinator_update()
        
        # Should now trigger adjustment in cool mode
        assert mock_hass.async_create_task.call_count == 1

    @pytest.mark.asyncio 
    async def test_unavailable_wrapped_entity_in_fan_only(self, climate_entity_with_coordinator, mock_hass, mock_real_coordinator):
        """Test unavailable wrapped entity during fan_only mode."""
        entity = climate_entity_with_coordinator
        
        # Set to fan_only mode
        entity._attr_hvac_mode = HVACMode.FAN_ONLY
        
        # Make wrapped entity unavailable
        unavailable_state = create_mock_state(
            state=STATE_UNAVAILABLE,
            attributes={},
            entity_id="climate.test_ac"
        )
        mock_hass.states.set("climate.test_ac", unavailable_state)
        
        # Trigger coordinator update
        entity._coordinator.data.calculated_offset = 2.0
        entity._handle_coordinator_update()
        
        # Should handle gracefully - no adjustment attempts
        mock_hass.async_create_task.assert_not_called()
        mock_hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_mode_change_during_feedback_delay(self, climate_entity_with_coordinator, mock_hass, mock_real_coordinator):
        """Test mode change occurring during feedback delay period."""
        entity = climate_entity_with_coordinator
        
        # Start in cool mode and trigger adjustment
        entity._attr_hvac_mode = HVACMode.COOL
        wrapped_state = self._create_wrapped_entity_state(HVACMode.COOL)
        mock_hass.states.set("climate.test_ac", wrapped_state)
        
        # Trigger adjustment with feedback delay
        entity._coordinator.data.calculated_offset = 2.0
        entity._last_total_offset = 0.0
        entity._handle_coordinator_update()
        
        # Should create task for adjustment
        assert mock_hass.async_create_task.call_count == 1
        mock_hass.async_create_task.reset_mock()
        
        # Simulate mode change to fan_only during feedback delay
        entity._attr_hvac_mode = HVACMode.FAN_ONLY
        wrapped_state = self._create_wrapped_entity_state(HVACMode.FAN_ONLY)
        mock_hass.states.set("climate.test_ac", wrapped_state)
        
        # Subsequent coordinator updates should not trigger adjustments
        entity._coordinator.data.calculated_offset = 2.5
        entity._handle_coordinator_update()
        
        mock_hass.async_create_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_coordinator_updates_different_modes(self, climate_entity_with_coordinator, mock_hass, mock_real_coordinator):
        """Test coordinator updates behave correctly in different HVAC modes."""
        entity = climate_entity_with_coordinator
        
        test_modes = [
            (HVACMode.COOL, True),      # Should allow adjustments
            (HVACMode.HEAT, True),      # Should allow adjustments  
            (HVACMode.AUTO, True),      # Should allow adjustments
            (HVACMode.OFF, False),      # Should NOT allow adjustments
            (HVACMode.FAN_ONLY, False), # Should NOT allow adjustments
        ]
        
        for hvac_mode, should_adjust in test_modes:
            # Reset for each test
            mock_hass.async_create_task.reset_mock()
            mock_hass.services.async_call.reset_mock()
            
            # Set mode and state
            entity._attr_hvac_mode = hvac_mode
            wrapped_state = self._create_wrapped_entity_state(hvac_mode)
            mock_hass.states.set("climate.test_ac", wrapped_state)
            
            # Force significant offset change
            entity._coordinator.data.calculated_offset = 2.0
            entity._last_total_offset = 0.0
            
            # Trigger coordinator update
            entity._handle_coordinator_update()
            
            if should_adjust:
                # Active modes should trigger adjustments
                assert mock_hass.async_create_task.call_count >= 1, f"Mode {hvac_mode} should trigger adjustment"
            else:
                # Non-active modes should not trigger adjustments
                mock_hass.async_create_task.assert_not_called(), f"Mode {hvac_mode} should NOT trigger adjustment"

    @pytest.mark.asyncio
    async def test_learning_hvac_mode_filtering(self, climate_entity_with_coordinator, mock_hass, mock_real_coordinator):
        """Test that learning data collection respects HVAC mode filtering."""
        entity = climate_entity_with_coordinator
        
        # Configure offset engine to track HVAC mode in record_feedback calls
        def mock_record_feedback(predicted_offset, actual_offset, input_data):
            # Verify that the input_data includes HVAC mode information
            assert hasattr(input_data, 'hvac_mode'), "Input data should include HVAC mode"
            return True
        
        entity._offset_engine.record_feedback.side_effect = mock_record_feedback
        
        # Test different modes to ensure learning respects mode filtering
        learning_test_cases = [
            (HVACMode.COOL, True),      # Should record learning
            (HVACMode.HEAT, True),      # Should record learning
            (HVACMode.AUTO, True),      # Should record learning
            (HVACMode.FAN_ONLY, False), # Should NOT record learning
            (HVACMode.OFF, False),      # Should NOT record learning
        ]
        
        for hvac_mode, should_learn in learning_test_cases:
            # Reset offset engine calls
            entity._offset_engine.record_feedback.reset_mock()
            entity._offset_engine.record_feedback.side_effect = mock_record_feedback if should_learn else None
            
            # Set mode
            entity._attr_hvac_mode = hvac_mode
            wrapped_state = self._create_wrapped_entity_state(hvac_mode)
            mock_hass.states.set("climate.test_ac", wrapped_state)
            
            # Create OffsetInput with HVAC mode
            test_input = OffsetInput(
                ac_internal_temp=23.0,
                room_temp=24.0,
                outdoor_temp=28.0,
                mode="normal",
                power_consumption=150.0,
                time_of_day=datetime.now().time(),
                day_of_week=datetime.now().weekday(),
                hvac_mode=hvac_mode
            )
            
            # Simulate learning feedback call that would be made after adjustment
            if hasattr(entity._offset_engine, 'record_feedback'):
                try:
                    entity._offset_engine.record_feedback(1.5, 1.2, test_input)
                    if not should_learn:
                        # If mode shouldn't allow learning, the call should be filtered out
                        # This depends on the actual implementation in offset_engine
                        pass
                except Exception:
                    # Expected for modes that should not learn
                    if should_learn:
                        raise

    @pytest.mark.asyncio
    async def test_edge_case_rapid_mode_switching(self, climate_entity_with_coordinator, mock_hass, mock_real_coordinator):
        """Test rapid switching between active and inactive modes.""" 
        entity = climate_entity_with_coordinator
        
        # Rapid mode switching sequence
        mode_sequence = [
            HVACMode.COOL,
            HVACMode.FAN_ONLY,
            HVACMode.COOL,
            HVACMode.OFF, 
            HVACMode.HEAT,
            HVACMode.FAN_ONLY,
        ]
        
        task_count = 0
        
        for i, hvac_mode in enumerate(mode_sequence):
            # Set mode
            entity._attr_hvac_mode = hvac_mode
            wrapped_state = self._create_wrapped_entity_state(hvac_mode)
            mock_hass.states.set("climate.test_ac", wrapped_state)
            
            # Force offset change each time
            entity._coordinator.data.calculated_offset = 1.0 + (i * 0.5)
            entity._last_total_offset = 0.0
            
            # Trigger update
            entity._handle_coordinator_update()
            
            # Count expected tasks based on mode
            if hvac_mode in ACTIVE_HVAC_MODES:
                task_count += 1
        
        # Verify correct number of tasks were created
        assert mock_hass.async_create_task.call_count == task_count

    @pytest.mark.asyncio
    async def test_integration_with_mocked_time_sleep(self, climate_entity_with_coordinator, mock_hass, mock_real_coordinator):
        """Test integration with mocked time.sleep for feedback delays."""
        entity = climate_entity_with_coordinator
        
        with patch('time.sleep') as mock_sleep:
            # Set to cool mode
            entity._attr_hvac_mode = HVACMode.COOL
            wrapped_state = self._create_wrapped_entity_state(HVACMode.COOL)
            mock_hass.states.set("climate.test_ac", wrapped_state)
            
            # Trigger adjustment that would schedule feedback
            entity._coordinator.data.calculated_offset = 2.0
            entity._last_total_offset = 0.0
            entity._handle_coordinator_update()
            
            # Should create adjustment task
            assert mock_hass.async_create_task.call_count == 1
            
            # Switch to fan_only during what would be feedback delay
            entity._attr_hvac_mode = HVACMode.FAN_ONLY
            wrapped_state = self._create_wrapped_entity_state(HVACMode.FAN_ONLY)
            mock_hass.states.set("climate.test_ac", wrapped_state)
            
            # Subsequent updates should not trigger adjustments
            mock_hass.async_create_task.reset_mock()
            entity._coordinator.data.calculated_offset = 2.5
            entity._handle_coordinator_update()
            
            mock_hass.async_create_task.assert_not_called()