"""Tests for thermal efficiency initialization bug fix."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from homeassistant.config_entries import ConfigEntry

from custom_components.smart_climate.const import DOMAIN
from custom_components.smart_climate.climate import async_setup_entry
from tests.fixtures.mock_entities import create_mock_hass


class TestThermalInitializationBug:
    """Test that thermal components are properly passed to coordinator."""

    @pytest.mark.asyncio
    async def test_coordinator_receives_thermal_components_when_enabled(self):
        """Test that SmartClimateCoordinator gets thermal components when thermal efficiency is enabled.
        
        This test verifies the bug fix where thermal components stored in hass.data
        were not being retrieved and passed to the coordinator constructor.
        """
        # Arrange - Create mock hass with data structure
        mock_hass = create_mock_hass()
        mock_hass.data = {
            DOMAIN: {
                "test_entry_id": {
                    "offset_engines": {"climate.test": Mock()},
                    "thermal_components": {
                        "climate.test": {
                            "thermal_model": Mock(),
                            "user_preferences": Mock(),
                            "thermal_manager": Mock(),
                            "probe_manager": Mock(),
                            "status_sensor": Mock(),
                            "shadow_mode": "enabled"
                        }
                    }
                }
            }
        }
        
        # Mock config entry with thermal efficiency enabled
        mock_config_entry = Mock(spec=ConfigEntry)
        mock_config_entry.entry_id = "test_entry_id"
        mock_config_entry.data = {
            "climate_entity": "climate.test",
            "room_sensor": "sensor.room_temp",
            "thermal_efficiency_enabled": True
        }
        mock_config_entry.options = {}
        
        # Mock async_add_entities
        mock_async_add_entities = AsyncMock()
        
        # Mock all the dependencies by patching their import paths
        with patch('custom_components.smart_climate.sensor_manager.SensorManager') as mock_sensor_manager_class, \
             patch('custom_components.smart_climate.offset_engine.OffsetEngine') as mock_offset_engine_class, \
             patch('custom_components.smart_climate.mode_manager.ModeManager') as mock_mode_manager_class, \
             patch('custom_components.smart_climate.temperature_controller.TemperatureController') as mock_temp_controller_class, \
             patch('custom_components.smart_climate.temperature_controller.TemperatureLimits') as mock_temp_limits_class, \
             patch('custom_components.smart_climate.coordinator.SmartClimateCoordinator') as mock_coordinator_class, \
             patch('custom_components.smart_climate.climate.SmartClimateEntity') as mock_entity_class, \
             patch('custom_components.smart_climate.integration.validate_configuration', return_value=True), \
             patch('custom_components.smart_climate.integration.get_unique_id', return_value="test_unique_id"), \
             patch('custom_components.smart_climate.integration.get_entity_name', return_value="Test Climate"), \
             patch('custom_components.smart_climate.forecast_engine.ForecastEngine') as mock_forecast_engine_class:
            
            # Make sure coordinator mock can be called and returns a mock instance
            mock_coordinator_instance = Mock()
            mock_coordinator_class.return_value = mock_coordinator_instance
            mock_coordinator_instance.async_config_entry_first_refresh = AsyncMock()
            
            # Make sensor manager instance
            mock_sensor_manager = Mock()
            mock_sensor_manager.start_listening = AsyncMock()
            mock_sensor_manager_class.return_value = mock_sensor_manager
            
            # Act - Call async_setup_entry
            await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
            
            # Assert - Verify coordinator was created with thermal components
            mock_coordinator_class.assert_called_once()
            call_args = mock_coordinator_class.call_args
            
            # Check that thermal efficiency related arguments were passed
            assert 'thermal_efficiency_enabled' in call_args.kwargs
            assert call_args.kwargs['thermal_efficiency_enabled'] is True
            
            # Check that thermal components were passed
            assert 'thermal_model' in call_args.kwargs
            assert 'user_preferences' in call_args.kwargs
            
            # Verify thermal components are the ones from hass.data
            expected_thermal_components = mock_hass.data[DOMAIN]["test_entry_id"]["thermal_components"]["climate.test"]
            assert call_args.kwargs['thermal_model'] is expected_thermal_components['thermal_model']
            assert call_args.kwargs['user_preferences'] is expected_thermal_components['user_preferences']

    @pytest.mark.asyncio
    async def test_coordinator_without_thermal_components_when_disabled(self):
        """Test that SmartClimateCoordinator doesn't get thermal components when thermal efficiency is disabled."""
        # Arrange - Create mock hass without thermal components
        mock_hass = create_mock_hass()
        mock_hass.data = {
            DOMAIN: {
                "test_entry_id": {
                    "offset_engines": {"climate.test": Mock()}
                    # No thermal_components key
                }
            }
        }
        
        # Mock config entry with thermal efficiency disabled
        mock_config_entry = Mock(spec=ConfigEntry)
        mock_config_entry.entry_id = "test_entry_id"
        mock_config_entry.data = {
            "climate_entity": "climate.test",
            "room_sensor": "sensor.room_temp",
            "thermal_efficiency_enabled": False
        }
        mock_config_entry.options = {}
        
        # Mock async_add_entities
        mock_async_add_entities = AsyncMock()
        
        # Mock all the dependencies by patching their import paths
        with patch('custom_components.smart_climate.sensor_manager.SensorManager') as mock_sensor_manager_class, \
             patch('custom_components.smart_climate.offset_engine.OffsetEngine') as mock_offset_engine_class, \
             patch('custom_components.smart_climate.mode_manager.ModeManager') as mock_mode_manager_class, \
             patch('custom_components.smart_climate.temperature_controller.TemperatureController') as mock_temp_controller_class, \
             patch('custom_components.smart_climate.temperature_controller.TemperatureLimits') as mock_temp_limits_class, \
             patch('custom_components.smart_climate.coordinator.SmartClimateCoordinator') as mock_coordinator_class, \
             patch('custom_components.smart_climate.climate.SmartClimateEntity') as mock_entity_class, \
             patch('custom_components.smart_climate.integration.validate_configuration', return_value=True), \
             patch('custom_components.smart_climate.integration.get_unique_id', return_value="test_unique_id"), \
             patch('custom_components.smart_climate.integration.get_entity_name', return_value="Test Climate"), \
             patch('custom_components.smart_climate.forecast_engine.ForecastEngine') as mock_forecast_engine_class:
            
            # Make sure coordinator mock can be called and returns a mock instance
            mock_coordinator_instance = Mock()
            mock_coordinator_class.return_value = mock_coordinator_instance
            mock_coordinator_instance.async_config_entry_first_refresh = AsyncMock()
            
            # Make sensor manager instance
            mock_sensor_manager = Mock()
            mock_sensor_manager.start_listening = AsyncMock()
            mock_sensor_manager_class.return_value = mock_sensor_manager
            
            # Act
            await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
            
            # Assert - Verify coordinator was created without thermal components
            mock_coordinator_class.assert_called_once()
            call_args = mock_coordinator_class.call_args
            
            # Check that thermal efficiency is disabled
            assert 'thermal_efficiency_enabled' in call_args.kwargs
            assert call_args.kwargs['thermal_efficiency_enabled'] is False
            
            # Check that thermal components are None/empty
            assert call_args.kwargs.get('thermal_model') is None
            assert call_args.kwargs.get('user_preferences') is None

    @pytest.mark.asyncio  
    async def test_coordinator_handles_missing_thermal_components_gracefully(self):
        """Test that coordinator handles the case where thermal efficiency is enabled but components are missing."""
        # Arrange - Create mock hass with thermal efficiency enabled but no thermal components
        mock_hass = create_mock_hass()
        mock_hass.data = {
            DOMAIN: {
                "test_entry_id": {
                    "offset_engines": {"climate.test": Mock()}
                    # thermal_components key missing despite thermal_efficiency_enabled=True
                }
            }
        }
        
        # Mock config entry with thermal efficiency enabled but no components
        mock_config_entry = Mock(spec=ConfigEntry)
        mock_config_entry.entry_id = "test_entry_id" 
        mock_config_entry.data = {
            "climate_entity": "climate.test",
            "room_sensor": "sensor.room_temp", 
            "thermal_efficiency_enabled": True  # Enabled but components missing
        }
        mock_config_entry.options = {}
        
        # Mock async_add_entities
        mock_async_add_entities = AsyncMock()
        
        # Mock all the dependencies by patching their import paths
        with patch('custom_components.smart_climate.sensor_manager.SensorManager') as mock_sensor_manager_class, \
             patch('custom_components.smart_climate.offset_engine.OffsetEngine') as mock_offset_engine_class, \
             patch('custom_components.smart_climate.mode_manager.ModeManager') as mock_mode_manager_class, \
             patch('custom_components.smart_climate.temperature_controller.TemperatureController') as mock_temp_controller_class, \
             patch('custom_components.smart_climate.temperature_controller.TemperatureLimits') as mock_temp_limits_class, \
             patch('custom_components.smart_climate.coordinator.SmartClimateCoordinator') as mock_coordinator_class, \
             patch('custom_components.smart_climate.climate.SmartClimateEntity') as mock_entity_class, \
             patch('custom_components.smart_climate.integration.validate_configuration', return_value=True), \
             patch('custom_components.smart_climate.integration.get_unique_id', return_value="test_unique_id"), \
             patch('custom_components.smart_climate.integration.get_entity_name', return_value="Test Climate"), \
             patch('custom_components.smart_climate.forecast_engine.ForecastEngine') as mock_forecast_engine_class:
            
            # Make sure coordinator mock can be called and returns a mock instance
            mock_coordinator_instance = Mock()
            mock_coordinator_class.return_value = mock_coordinator_instance
            mock_coordinator_instance.async_config_entry_first_refresh = AsyncMock()
            
            # Make sensor manager instance
            mock_sensor_manager = Mock()
            mock_sensor_manager.start_listening = AsyncMock()
            mock_sensor_manager_class.return_value = mock_sensor_manager
            
            # Act
            await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
            
            # Assert - Should handle gracefully and create coordinator with None thermal components
            mock_coordinator_class.assert_called_once()
            call_args = mock_coordinator_class.call_args
            
            # Should still pass thermal_efficiency_enabled=True  
            assert call_args.kwargs['thermal_efficiency_enabled'] is True
            
            # But thermal components should be None since they're missing
            assert call_args.kwargs.get('thermal_model') is None
            assert call_args.kwargs.get('user_preferences') is None