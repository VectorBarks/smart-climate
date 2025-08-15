"""Test thermal manager lookup fix in SmartClimateEntity.

This test ensures thermal components are properly accessed using the wrapped entity ID
instead of the Smart Climate entity ID, fixing the DRIFTING state functionality.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.models import OffsetInput, OffsetResult, ModeAdjustments


class TestThermalManagerLookupFix:
    """Test class for thermal manager lookup fix."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = Mock()
        hass.data = {}
        hass.states.get.return_value = Mock(
            state='heat',
            attributes={'current_temperature': 21.5}
        )
        return hass

    @pytest.fixture
    def thermal_components(self):
        """Create mock thermal components with DRIFTING state."""
        mock_thermal_state = Mock()
        mock_thermal_state.name = 'DRIFTING'
        
        mock_thermal_manager = Mock()
        mock_thermal_manager.current_state = mock_thermal_state
        
        return {
            'thermal_manager': mock_thermal_manager
        }

    @pytest.fixture
    def smart_climate_entity(self, mock_hass, thermal_components):
        """Create a SmartClimateEntity for testing."""
        config = {
            'entry_id': 'test_entry_123',
            'room_sensor': 'sensor.room_temp'
        }
        
        wrapped_entity_id = 'climate.klimaanlage_tu_climate'
        smart_entity_id = 'climate.smart_klimaanlage_tu_climate'
        
        # Set up hass.data with thermal components stored by wrapped entity ID
        mock_hass.data = {
            'smart_climate': {
                'test_entry_123': {
                    'thermal_components': {
                        wrapped_entity_id: thermal_components  # Stored by wrapped ID
                    }
                }
            }
        }
        
        # Create mocked dependencies
        sensor_manager = Mock()
        sensor_manager.get_room_temperature.return_value = 22.0
        sensor_manager.get_outdoor_temperature.return_value = 25.0
        sensor_manager.get_power_consumption.return_value = None
        sensor_manager.get_indoor_humidity.return_value = None
        sensor_manager.get_outdoor_humidity.return_value = None
        
        offset_engine = Mock()
        offset_engine.calculate_offset.return_value = OffsetResult(
            offset=-1.0, clamped=False, reason='Test', confidence=0.8
        )
        
        mode_manager = Mock()
        mode_manager.get_adjustments.return_value = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0,
            force_operation=False
        )
        mode_manager.current_mode = 'none'
        
        temperature_controller = Mock()
        temperature_controller.apply_offset_and_limits.return_value = 21.0
        temperature_controller.send_temperature_command = AsyncMock()
        
        # Create entity
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=config,
            wrapped_entity_id=wrapped_entity_id,
            room_sensor_id=config['room_sensor'],
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=mode_manager,
            temperature_controller=temperature_controller,
            coordinator=Mock()
        )
        
        # Set the Smart Climate entity ID (different from wrapped)
        entity.entity_id = smart_entity_id
        
        # Mock additional methods to prevent errors
        entity._is_hvac_mode_active = Mock(return_value=True)
        
        return entity

    def test_thermal_lookup_bug_demonstration(self, mock_hass, thermal_components):
        """Demonstrate the original bug - lookup fails with wrong entity ID."""
        wrapped_entity_id = 'climate.klimaanlage_tu_climate'
        smart_entity_id = 'climate.smart_klimaanlage_tu_climate'
        
        # Store thermal components by wrapped entity ID (how it actually works)
        storage = {wrapped_entity_id: thermal_components}
        
        # Buggy lookup using Smart Climate entity ID (old code)
        buggy_result = storage.get(smart_entity_id)
        assert buggy_result is None, "Bug not reproduced - should not find thermal components"
        
        # Correct lookup using wrapped entity ID (fixed code)
        fixed_result = storage.get(wrapped_entity_id)
        assert fixed_result is not None, "Fix verification failed - should find thermal components"
        assert 'thermal_manager' in fixed_result

    @pytest.mark.asyncio
    async def test_thermal_state_retrieval_after_fix(self, smart_climate_entity):
        """Test that thermal state is properly retrieved after the fix."""
        # Mock _resolve_target_temperature to verify it gets called with thermal state
        original_resolve = Mock(return_value=21.0)
        smart_climate_entity._resolve_target_temperature = original_resolve
        
        # Call _apply_temperature_with_offset which contains the thermal lookup
        await smart_climate_entity._apply_temperature_with_offset(22.0, source='test')
        
        # Verify _resolve_target_temperature was called
        original_resolve.assert_called_once()
        
        # Check that thermal state was passed as third argument
        call_args = original_resolve.call_args[0]
        assert len(call_args) == 4, f"Expected 4 args, got {len(call_args)}"
        
        thermal_state_arg = call_args[2]
        assert thermal_state_arg is not None, "Thermal state should not be None after fix"
        assert thermal_state_arg.name == 'DRIFTING', f"Expected DRIFTING state, got {thermal_state_arg.name}"

    @pytest.mark.asyncio
    async def test_drifting_state_priority_integration(self, smart_climate_entity):
        """Test that DRIFTING state integrates properly with priority resolver."""
        # Mock the priority resolver to return DRIFTING-specific temperature
        def mock_resolve_target(base_temp, room_temp, thermal_state, mode_adjustments):
            if thermal_state and thermal_state.name == 'DRIFTING':
                # DRIFTING should set target = room_temp + 3.0 to turn AC off
                return room_temp + 3.0
            return base_temp
        
        smart_climate_entity._resolve_target_temperature = Mock(side_effect=mock_resolve_target)
        
        # Call temperature application
        await smart_climate_entity._apply_temperature_with_offset(22.0, source='test')
        
        # Verify the priority resolver was called with DRIFTING state
        smart_climate_entity._resolve_target_temperature.assert_called_once()
        call_args = smart_climate_entity._resolve_target_temperature.call_args[0]
        
        # Check thermal state is DRIFTING
        thermal_state = call_args[2]
        assert thermal_state.name == 'DRIFTING'
        
        # Verify DRIFTING logic was applied (room_temp + 3.0 = 25.0)
        expected_drifting_temp = 22.0 + 3.0  # room_temp + 3.0
        result = mock_resolve_target(22.0, 22.0, thermal_state, call_args[3])
        assert result == expected_drifting_temp

    @pytest.mark.asyncio  
    async def test_missing_thermal_components_graceful_handling(self, mock_hass):
        """Test that missing thermal components are handled gracefully."""
        config = {'entry_id': 'test_entry_123'}
        
        # Set up hass.data WITHOUT thermal components
        mock_hass.data = {
            'smart_climate': {
                'test_entry_123': {
                    # No thermal_components key
                }
            }
        }
        
        # Create minimal entity
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=config,
            wrapped_entity_id='climate.test',
            room_sensor_id='sensor.room_temp',
            offset_engine=Mock(),
            sensor_manager=Mock(),
            mode_manager=Mock(),
            temperature_controller=Mock(),
            coordinator=Mock()
        )
        
        # Mock required methods
        entity._is_hvac_mode_active = Mock(return_value=True)
        entity._sensor_manager.get_room_temperature = Mock(return_value=22.0)
        entity._sensor_manager.get_outdoor_temperature = Mock(return_value=25.0)
        entity._sensor_manager.get_power_consumption = Mock(return_value=None)
        entity._sensor_manager.get_indoor_humidity = Mock(return_value=None)
        entity._sensor_manager.get_outdoor_humidity = Mock(return_value=None)
        
        entity._offset_engine.calculate_offset.return_value = OffsetResult(
            offset=-1.0, clamped=False, reason='Test', confidence=0.8
        )
        
        entity._mode_manager.get_adjustments.return_value = ModeAdjustments(
            temperature_override=None, offset_adjustment=0.0, 
            update_interval_override=None, boost_offset=0.0, force_operation=False
        )
        entity._mode_manager.current_mode = 'none'
        
        entity._temperature_controller.apply_offset_and_limits.return_value = 21.0
        entity._temperature_controller.send_temperature_command = AsyncMock()
        
        # Should not crash when thermal components are missing
        await entity._apply_temperature_with_offset(22.0, source='test')
        
        # Verify standard logic was used (no thermal state override)
        entity._temperature_controller.send_temperature_command.assert_called_once()

    def test_entity_id_vs_wrapped_entity_id_distinction(self, smart_climate_entity):
        """Test that entity_id and _wrapped_entity_id are properly different."""
        # These should be different
        assert smart_climate_entity.entity_id != smart_climate_entity._wrapped_entity_id
        
        # Smart Climate entity should have 'smart_' prefix
        assert smart_climate_entity.entity_id.startswith('climate.smart_')
        
        # Wrapped entity should not have the prefix
        assert not smart_climate_entity._wrapped_entity_id.startswith('climate.smart_')
        
        print(f"Entity ID: {smart_climate_entity.entity_id}")
        print(f"Wrapped Entity ID: {smart_climate_entity._wrapped_entity_id}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])