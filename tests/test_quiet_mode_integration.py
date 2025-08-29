"""Tests for Quiet Mode integration with climate entity."""
import sys
import os
from unittest.mock import MagicMock, patch, AsyncMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_quiet_mode_initialization():
    """Test that quiet mode controller is created with proper config."""
    from custom_components.smart_climate.climate import SmartClimateEntity
    from custom_components.smart_climate.const import CONF_QUIET_MODE_ENABLED
    
    print("Testing quiet mode initialization...")
    
    # Mock Home Assistant instance
    hass = MagicMock()
    mock_wrapped_entity_state = MagicMock()
    mock_wrapped_entity_state.attributes = {"temperature": 24.0}
    hass.states.get.return_value = mock_wrapped_entity_state
    
    config = {
        CONF_QUIET_MODE_ENABLED: True,
        "wrapped_entity_id": "climate.test_ac",
        "sensor_configs": {}
    }
    
    # Mock the required components
    with patch('custom_components.smart_climate.climate.SensorManager'), \
         patch('custom_components.smart_climate.climate.ThermalManager'), \
         patch('custom_components.smart_climate.climate.OffsetEngine'), \
         patch('custom_components.smart_climate.climate.CompressorStateAnalyzer'), \
         patch('custom_components.smart_climate.climate.QuietModeController'):
        
        entity = SmartClimateEntity(
            hass, config, "climate.test_ac", "sensor.room_temp",
            MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()
        )
        
        # Test that quiet mode was enabled and controller created
        assert hasattr(entity, '_quiet_mode_enabled')
        assert entity._quiet_mode_enabled is True
        assert hasattr(entity, '_quiet_mode_controller')
        assert entity._quiet_mode_controller is not None
        
    print("✓ Quiet mode initialization test passed")


def test_quiet_mode_disabled_when_config_false():
    """Test that quiet mode controller is not created when disabled in config."""
    from custom_components.smart_climate.climate import SmartClimateEntity
    from custom_components.smart_climate.const import CONF_QUIET_MODE_ENABLED
    
    print("Testing quiet mode disabled configuration...")
    
    # Mock Home Assistant instance
    hass = MagicMock()
    mock_wrapped_entity_state = MagicMock()
    mock_wrapped_entity_state.attributes = {"temperature": 24.0}
    hass.states.get.return_value = mock_wrapped_entity_state
    
    config = {
        CONF_QUIET_MODE_ENABLED: False,
        "wrapped_entity_id": "climate.test_ac",
        "sensor_configs": {}
    }
    
    # Mock the required components
    with patch('custom_components.smart_climate.climate.SensorManager'), \
         patch('custom_components.smart_climate.climate.ThermalManager'), \
         patch('custom_components.smart_climate.climate.OffsetEngine'):
        
        entity = SmartClimateEntity(
            hass, config, "climate.test_ac", "sensor.room_temp",
            MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()
        )
        
        # Test that quiet mode was disabled and no controller created
        assert hasattr(entity, '_quiet_mode_enabled')
        assert entity._quiet_mode_enabled is False
        assert hasattr(entity, '_quiet_mode_controller')
        assert entity._quiet_mode_controller is None
        
    print("✓ Quiet mode disabled test passed")


def test_quiet_mode_adds_diagnostic_attributes():
    """Test that quiet mode diagnostic attributes are added to extra_state_attributes."""
    from custom_components.smart_climate.climate import SmartClimateEntity
    from custom_components.smart_climate.const import CONF_QUIET_MODE_ENABLED
    
    print("Testing quiet mode diagnostic attributes...")
    
    # Mock Home Assistant instance
    hass = MagicMock()
    mock_wrapped_entity_state = MagicMock()
    mock_wrapped_entity_state.attributes = {"temperature": 24.0}
    hass.states.get.return_value = mock_wrapped_entity_state
    
    config = {
        CONF_QUIET_MODE_ENABLED: True,
        "wrapped_entity_id": "climate.test_ac",
        "sensor_configs": {}
    }
    
    # Mock the required components
    with patch('custom_components.smart_climate.climate.SensorManager'), \
         patch('custom_components.smart_climate.climate.ThermalManager'), \
         patch('custom_components.smart_climate.climate.OffsetEngine'), \
         patch('custom_components.smart_climate.climate.CompressorStateAnalyzer'), \
         patch('custom_components.smart_climate.climate.QuietModeController') as mock_controller_cls:
        
        # Setup controller mock to return diagnostic data
        mock_controller = MagicMock()
        mock_controller.get_suppression_count.return_value = 3
        mock_controller_cls.return_value = mock_controller
        
        entity = SmartClimateEntity(
            hass, config, "climate.test_ac", "sensor.room_temp",
            MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()
        )
        
        # Mock the _last_offset attribute required by extra_state_attributes
        entity._last_offset = 1.5
        
        # Get the extra state attributes
        attributes = entity.extra_state_attributes
        
        # Verify quiet mode attributes are present
        assert "quiet_mode_enabled" in attributes
        assert attributes["quiet_mode_enabled"] is True
        assert "quiet_mode_suppressions" in attributes
        assert attributes["quiet_mode_suppressions"] == 3
        
    print("✓ Quiet mode diagnostic attributes test passed")


def test_quiet_mode_no_attributes_when_disabled():
    """Test that quiet mode attributes are not added when disabled."""
    from custom_components.smart_climate.climate import SmartClimateEntity
    from custom_components.smart_climate.const import CONF_QUIET_MODE_ENABLED
    
    print("Testing quiet mode attributes when disabled...")
    
    # Mock Home Assistant instance
    hass = MagicMock()
    mock_wrapped_entity_state = MagicMock()
    mock_wrapped_entity_state.attributes = {"temperature": 24.0}
    hass.states.get.return_value = mock_wrapped_entity_state
    
    config = {
        CONF_QUIET_MODE_ENABLED: False,
        "wrapped_entity_id": "climate.test_ac",
        "sensor_configs": {}
    }
    
    # Mock the required components
    with patch('custom_components.smart_climate.climate.SensorManager'), \
         patch('custom_components.smart_climate.climate.ThermalManager'), \
         patch('custom_components.smart_climate.climate.OffsetEngine'):
        
        entity = SmartClimateEntity(
            hass, config, "climate.test_ac", "sensor.room_temp",
            MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()
        )
        
        # Mock the _last_offset attribute required by extra_state_attributes
        entity._last_offset = 1.5
        
        # Get the extra state attributes
        attributes = entity.extra_state_attributes
        
        # Verify quiet mode attributes are NOT present
        assert "quiet_mode_enabled" not in attributes
        assert "quiet_mode_suppressions" not in attributes
        
    print("✓ Quiet mode disabled attributes test passed")

def run_all_tests():
    """Run all quiet mode integration tests."""
    print("Running Quiet Mode Integration Tests...")
    print("=" * 50)
    
    test_quiet_mode_initialization()
    test_quiet_mode_disabled_when_config_false()
    test_quiet_mode_adds_diagnostic_attributes()
    test_quiet_mode_no_attributes_when_disabled()
    
    print("=" * 50)
    print("✓ All Quiet Mode Integration Tests Passed!")


if __name__ == "__main__":
    run_all_tests()

    def test_quiet_mode_adds_diagnostic_attributes(self, climate_entity):
        """Test that quiet mode diagnostic attributes are added to extra_state_attributes."""
        # Setup controller to return diagnostic data
        climate_entity._quiet_mode_controller.get_suppression_count.return_value = 3
        
        # Get the extra state attributes
        attributes = climate_entity.extra_state_attributes
        
        # Verify quiet mode attributes are present
        assert "quiet_mode_enabled" in attributes
        assert attributes["quiet_mode_enabled"] is True
        assert "quiet_mode_suppressions" in attributes
        assert attributes["quiet_mode_suppressions"] == 3

    def test_quiet_mode_no_attributes_when_disabled(self, climate_entity_disabled):
        """Test that quiet mode attributes are not added when disabled."""
        attributes = climate_entity_disabled.extra_state_attributes
        
        # Verify quiet mode attributes are NOT present
        assert "quiet_mode_enabled" not in attributes
        assert "quiet_mode_suppressions" not in attributes

    async def test_quiet_mode_handles_missing_power_consumption(self, climate_entity):
        """Test that quiet mode handles missing power consumption gracefully."""
        climate_entity.hvac_mode = "cool"
        climate_entity._quiet_mode_controller.should_suppress_adjustment.return_value = (False, None)
        climate_entity._send_temperature_command = AsyncMock()
        
        # Call with None power consumption
        await climate_entity._apply_temperature_with_offset(25.0, 23.5, None)
        
        # Verify suppression logic was still called with None power
        climate_entity._quiet_mode_controller.should_suppress_adjustment.assert_called_once()
        call_args = climate_entity._quiet_mode_controller.should_suppress_adjustment.call_args[1]
        assert call_args["power"] is None

    async def test_quiet_mode_handles_missing_current_setpoint(self, climate_entity):
        """Test that quiet mode handles missing current setpoint gracefully."""
        # Setup wrapped entity state without temperature attribute
        climate_entity.hass.states.get.return_value.attributes = {}
        
        climate_entity.hvac_mode = "cool"
        climate_entity._send_temperature_command = AsyncMock()
        
        # Call the method
        await climate_entity._apply_temperature_with_offset(25.0, 23.5, 50.0)
        
        # Verify suppression logic was NOT called due to missing setpoint
        climate_entity._quiet_mode_controller.should_suppress_adjustment.assert_not_called()
        
        # Verify command WAS sent (no suppression without current setpoint)
        climate_entity._send_temperature_command.assert_called_once()