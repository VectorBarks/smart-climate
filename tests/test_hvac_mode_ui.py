"""ABOUTME: Tests for HVAC mode UI responsiveness and state updates.
Tests to ensure HVAC mode changes trigger immediate UI feedback."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
from homeassistant.core import HomeAssistant
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.components.climate.const import (
    HVACMode, HVACAction, ClimateEntityFeature
)

# Test imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.models import OffsetResult


@pytest.fixture
def mock_hass():
    """Mock Home Assistant instance."""
    hass = Mock(spec=HomeAssistant)
    hass.services = Mock()
    hass.services.async_call = AsyncMock()
    hass.states = Mock()
    return hass


@pytest.fixture
def mock_dependencies():
    """Mock all dependencies."""
    offset_engine = Mock()
    offset_engine.calculate_offset.return_value = OffsetResult(
        offset=0.0, clamped=False, reason="Test", confidence=1.0
    )
    
    sensor_manager = Mock()
    sensor_manager.get_room_temperature.return_value = 22.0
    sensor_manager.get_outdoor_temperature.return_value = 25.0
    sensor_manager.get_power_consumption.return_value = 1200.0
    sensor_manager.start_listening = AsyncMock()
    sensor_manager.stop_listening = AsyncMock()
    
    mode_manager = Mock()
    mode_manager.current_mode = "none"
    mode_manager.set_mode = Mock()
    mode_manager.get_adjustments.return_value = Mock(
        temperature_override=None,
        offset_adjustment=0.0,
        update_interval_override=None,
        boost_offset=0.0
    )
    
    temperature_controller = Mock()
    temperature_controller.apply_offset_and_limits.return_value = 23.0
    temperature_controller.send_temperature_command = AsyncMock()
    
    coordinator = Mock()
    coordinator.async_add_listener = Mock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    
    return {
        'offset_engine': offset_engine,
        'sensor_manager': sensor_manager,
        'mode_manager': mode_manager,
        'temperature_controller': temperature_controller,
        'coordinator': coordinator
    }


@pytest.fixture
def mock_wrapped_entity_state():
    """Mock wrapped entity state."""
    state = Mock()
    state.state = HVACMode.OFF
    state.attributes = {
        'hvac_modes': [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.AUTO],
        'supported_features': int(ClimateEntityFeature.TARGET_TEMPERATURE),
        'current_temperature': 22.5,
        'target_temperature': 23.0,
        'temperature_unit': '°C',
        'min_temp': 16.0,
        'max_temp': 30.0,
        'target_temperature_step': 0.5
    }
    return state


@pytest.fixture
def smart_climate_entity(mock_hass, mock_dependencies, mock_wrapped_entity_state):
    """Create SmartClimateEntity with mocked dependencies."""
    config = {
        'name': 'Test Smart Climate',
        'room_sensor': 'sensor.room_temp',
        'outdoor_sensor': 'sensor.outdoor_temp',
        'power_sensor': 'sensor.power',
        'max_offset': 5.0,
        'min_temperature': 16.0,
        'max_temperature': 30.0,
        'update_interval': 180
    }
    
    # Mock the wrapped entity state
    mock_hass.states.get.return_value = mock_wrapped_entity_state
    
    entity = SmartClimateEntity(
        hass=mock_hass,
        config=config,
        wrapped_entity_id='climate.test_ac',
        room_sensor_id='sensor.room_temp',
        **mock_dependencies
    )
    
    return entity


class TestHVACModeUI:
    """Test HVAC mode UI responsiveness."""
    
    def test_hvac_mode_method_exists(self, smart_climate_entity):
        """Test that async_set_hvac_mode method exists."""
        assert hasattr(smart_climate_entity, 'async_set_hvac_mode')
        assert callable(smart_climate_entity.async_set_hvac_mode)
    
    @pytest.mark.asyncio
    async def test_hvac_mode_forwards_to_wrapped_entity(self, smart_climate_entity):
        """Test that HVAC mode change is forwarded to wrapped entity."""
        # Mock the async_write_ha_state method
        smart_climate_entity.async_write_ha_state = Mock()
        
        # Call set_hvac_mode
        await smart_climate_entity.async_set_hvac_mode(HVACMode.COOL)
        
        # Verify service call was made
        smart_climate_entity.hass.services.async_call.assert_called_once_with(
            "climate",
            "set_hvac_mode",
            {
                "entity_id": "climate.test_ac",
                "hvac_mode": HVACMode.COOL
            },
            blocking=False
        )
    
    @pytest.mark.asyncio
    async def test_hvac_mode_triggers_ui_update(self, smart_climate_entity):
        """Test that HVAC mode change triggers immediate UI update."""
        # Mock the async_write_ha_state method
        smart_climate_entity.async_write_ha_state = Mock()
        
        # Call set_hvac_mode
        await smart_climate_entity.async_set_hvac_mode(HVACMode.COOL)
        
        # Verify UI update was triggered
        smart_climate_entity.async_write_ha_state.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_hvac_mode_different_modes(self, smart_climate_entity):
        """Test HVAC mode changes with different modes."""
        # Mock the async_write_ha_state method
        smart_climate_entity.async_write_ha_state = Mock()
        
        test_modes = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.AUTO]
        
        for mode in test_modes:
            # Reset mocks
            smart_climate_entity.hass.services.async_call.reset_mock()
            smart_climate_entity.async_write_ha_state.reset_mock()
            
            # Call set_hvac_mode
            await smart_climate_entity.async_set_hvac_mode(mode)
            
            # Verify service call
            smart_climate_entity.hass.services.async_call.assert_called_once_with(
                "climate",
                "set_hvac_mode",
                {
                    "entity_id": "climate.test_ac",
                    "hvac_mode": mode
                },
                blocking=False
            )
            
            # Verify UI update
            smart_climate_entity.async_write_ha_state.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_hvac_mode_service_call_error_handling(self, smart_climate_entity):
        """Test error handling when service call fails."""
        # Mock the async_write_ha_state method
        smart_climate_entity.async_write_ha_state = Mock()
        
        # Mock service call to raise an exception
        smart_climate_entity.hass.services.async_call.side_effect = Exception("Service call failed")
        
        # Call set_hvac_mode - should not raise exception
        await smart_climate_entity.async_set_hvac_mode(HVACMode.COOL)
        
        # Verify service call was attempted
        smart_climate_entity.hass.services.async_call.assert_called_once()
        
        # UI update should still be called for consistency
        smart_climate_entity.async_write_ha_state.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_hvac_mode_responsiveness_timing(self, smart_climate_entity):
        """Test that HVAC mode changes are responsive (no artificial delays)."""
        # Mock the async_write_ha_state method
        smart_climate_entity.async_write_ha_state = Mock()
        
        import time
        start_time = time.time()
        
        # Call set_hvac_mode
        await smart_climate_entity.async_set_hvac_mode(HVACMode.COOL)
        
        end_time = time.time()
        
        # Should complete quickly (under 100ms for mocked calls)
        assert end_time - start_time < 0.1
        
        # Both service call and UI update should have been called
        smart_climate_entity.hass.services.async_call.assert_called_once()
        smart_climate_entity.async_write_ha_state.assert_called_once()
    
    def test_hvac_mode_property_reading(self, smart_climate_entity):
        """Test that HVAC mode property reads from wrapped entity."""
        # Test current hvac_mode property
        current_mode = smart_climate_entity.hvac_mode
        assert current_mode == HVACMode.OFF
        
        # Test hvac_modes property
        available_modes = smart_climate_entity.hvac_modes
        expected_modes = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.AUTO]
        assert available_modes == expected_modes
    
    def test_hvac_mode_property_error_handling(self, smart_climate_entity):
        """Test HVAC mode property error handling."""
        # Mock wrapped entity to return None (unavailable)
        smart_climate_entity.hass.states.get.return_value = None
        
        # Should return safe defaults
        assert smart_climate_entity.hvac_mode == HVACMode.OFF
        assert isinstance(smart_climate_entity.hvac_modes, list)
        assert HVACMode.OFF in smart_climate_entity.hvac_modes
    
    @pytest.mark.asyncio
    async def test_hvac_mode_integration_with_temperature_setting(self, smart_climate_entity):
        """Test that HVAC mode changes work alongside temperature setting."""
        # Mock the async_write_ha_state method
        smart_climate_entity.async_write_ha_state = Mock()
        
        # First set temperature
        await smart_climate_entity.async_set_temperature(temperature=24.0)
        
        # Then change HVAC mode
        await smart_climate_entity.async_set_hvac_mode(HVACMode.COOL)
        
        # Both operations should have completed
        assert smart_climate_entity.hass.services.async_call.call_count >= 2
        assert smart_climate_entity.async_write_ha_state.call_count >= 2
        
        # Last call should be for HVAC mode
        last_call = smart_climate_entity.hass.services.async_call.call_args_list[-1]
        assert last_call[0][1] == "set_hvac_mode"
        assert last_call[1]["hvac_mode"] == HVACMode.COOL


def test_hvac_mode_ui_responsiveness_integration():
    """Integration test for HVAC mode UI responsiveness."""
    # This test verifies that the fix addresses the reported issue
    # The key requirement is that UI updates happen immediately
    
    # Mock Home Assistant
    hass = Mock(spec=HomeAssistant)
    hass.services = Mock()
    hass.services.async_call = AsyncMock()
    hass.states = Mock()
    
    # Mock wrapped entity state
    wrapped_state = Mock()
    wrapped_state.state = HVACMode.OFF
    wrapped_state.attributes = {
        'hvac_modes': [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT],
        'supported_features': int(ClimateEntityFeature.TARGET_TEMPERATURE),
        'current_temperature': 22.0,
        'target_temperature': 23.0
    }
    hass.states.get.return_value = wrapped_state
    
    # Create minimal entity
    config = {'name': 'Test'}
    entity = SmartClimateEntity(
        hass=hass,
        config=config,
        wrapped_entity_id='climate.test',
        room_sensor_id='sensor.room',
        offset_engine=Mock(),
        sensor_manager=Mock(),
        mode_manager=Mock(),
        temperature_controller=Mock(),
        coordinator=Mock()
    )
    
    # Mock async_write_ha_state
    entity.async_write_ha_state = Mock()
    
    # The key test: HVAC mode change should trigger immediate UI update
    async def test_ui_update():
        await entity.async_set_hvac_mode(HVACMode.COOL)
        
        # Verify both service call and UI update occurred
        assert hass.services.async_call.called
        assert entity.async_write_ha_state.called
        
        # This is what fixes the slow UI update issue
        entity.async_write_ha_state.assert_called_once()
    
    # Run the test
    asyncio.run(test_ui_update())
    
    print("✓ HVAC mode UI responsiveness integration test passed")


if __name__ == "__main__":
    test_hvac_mode_ui_responsiveness_integration()
    print("\n✅ HVAC mode UI tests completed!")