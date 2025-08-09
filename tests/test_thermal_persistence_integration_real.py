"""ABOUTME: Real integration test for thermal data persistence Issue #67.
Tests the actual production flow from __init__.py to see the callback issue."""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, AsyncMock, patch, call
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

# Import the actual init function
from custom_components.smart_climate import setup_entity
from custom_components.smart_climate.const import DOMAIN


class TestThermalPersistenceIntegrationReal:
    """Test the real thermal persistence integration using actual setup."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = Mock()
        hass.data = {DOMAIN: {}}
        return hass

    @pytest.fixture 
    def mock_config_entry(self):
        """Create a mock config entry."""
        entry = Mock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.data = {
            "wrapped_entity_id": "climate.test_thermostat",
            "room_sensor": "sensor.room_temp",
            "name": "Test Smart Climate"
        }
        entry.options = {
            "thermal_efficiency_enabled": True,
            "shadow_mode": True
        }
        return entry

    @pytest.mark.asyncio
    async def test_debug_real_setup_entity_callback_issue(self, mock_hass, mock_config_entry):
        """Debug the real setup_entity to identify the callback issue."""
        entity_id = "climate.test_thermostat"
        config = {
            "max_offset": 5.0,
            "ml_enabled": True,
            "thermal_efficiency_enabled": True,
            "shadow_mode": True
        }
        
        # Mock the required external dependencies that setup_entity needs
        with patch('custom_components.smart_climate.SeasonalHysteresisLearner') as mock_seasonal_class, \
             patch('custom_components.smart_climate.OutlierDetector') as mock_outlier_class:
            
            # Mock the seasonal learner
            mock_seasonal = Mock()
            mock_seasonal_class.return_value = mock_seasonal
            
            # Mock the outlier detector  
            mock_outlier = Mock()
            mock_outlier_class.return_value = mock_outlier

            # Add debug logging
            with patch('custom_components.smart_climate._LOGGER') as mock_logger:
                try:
                    # Call the real setup_entity function
                    await setup_entity(mock_hass, mock_config_entry, entity_id, config)
                    
                    # Print all debug logs to see what happened
                    print("=== Setup Debug Logs ===")
                    for call_args in mock_logger.debug.call_args_list:
                        print(f"DEBUG: {call_args}")
                    
                    for call_args in mock_logger.info.call_args_list:
                        print(f"INFO: {call_args}")
                        
                    for call_args in mock_logger.warning.call_args_list:
                        print(f"WARNING: {call_args}")
                        
                    for call_args in mock_logger.error.call_args_list:
                        print(f"ERROR: {call_args}")
                    
                    # Check what was stored in hass.data
                    print("=== hass.data structure ===")
                    domain_data = mock_hass.data.get(DOMAIN, {})
                    print(f"Domain keys: {list(domain_data.keys())}")
                    
                    entry_data = domain_data.get(mock_config_entry.entry_id, {})
                    print(f"Entry data keys: {list(entry_data.keys())}")
                    
                    if "offset_engines" in entry_data:
                        print(f"offset_engines keys: {list(entry_data['offset_engines'].keys())}")
                        
                        # Check the OffsetEngine callbacks
                        offset_engine = entry_data['offset_engines'].get(entity_id)
                        if offset_engine:
                            print(f"OffsetEngine callbacks: get_thermal={offset_engine._get_thermal_data_cb}, restore_thermal={offset_engine._restore_thermal_data_cb}")
                            
                            # Try calling the callback to see what happens
                            if offset_engine._get_thermal_data_cb:
                                try:
                                    callback_result = offset_engine._get_thermal_data_cb()
                                    print(f"Callback result: {callback_result}")
                                    print(f"Callback result type: {type(callback_result)}")
                                except Exception as e:
                                    print(f"Callback failed: {e}")
                        
                    if "thermal_components" in entry_data:
                        print(f"thermal_components keys: {list(entry_data['thermal_components'].keys())}")
                        thermal_comp = entry_data['thermal_components'].get(entity_id)
                        if thermal_comp:
                            print(f"Thermal component keys: {list(thermal_comp.keys())}")
                            thermal_manager = thermal_comp.get("thermal_manager")
                            if thermal_manager:
                                # Test direct serialize
                                serialize_result = thermal_manager.serialize()
                                print(f"Direct serialize result type: {type(serialize_result)}")
                                print(f"Direct serialize keys: {list(serialize_result.keys()) if isinstance(serialize_result, dict) else 'NOT DICT'}")
                    
                except Exception as exc:
                    print(f"Setup failed with exception: {exc}")
                    # Print the exception details
                    import traceback
                    traceback.print_exc()
                    
                    # Also check debug logs for partial setup
                    print("=== Partial Setup Debug Logs ===")
                    for call_args in mock_logger.debug.call_args_list:
                        print(f"DEBUG: {call_args}")
                        
                    for call_args in mock_logger.error.call_args_list:
                        print(f"ERROR: {call_args}")

        # Just assert the test ran (we'll analyze the debug output)
        assert True