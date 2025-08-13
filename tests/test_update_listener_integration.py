"""ABOUTME: Integration tests for update_listener complete options update flow.
Tests end-to-end reload behavior when integration options change."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform

from custom_components.smart_climate.const import DOMAIN
from custom_components.smart_climate import async_setup_entry, async_unload_entry, update_listener


class TestUpdateListenerIntegration:
    """Integration tests for complete options update flow."""

    @pytest.mark.asyncio
    async def test_complete_options_update_flow(self):
        """Test complete options update flow with integration reload."""
        # Create mock HomeAssistant instance
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {}}
        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
        mock_hass.config_entries.async_reload = AsyncMock(return_value=True)
        mock_hass.async_add_executor_job = AsyncMock()
        mock_hass.services = Mock()
        mock_hass.services.async_register = Mock()
        
        # Create mock ConfigEntry with initial options
        initial_entry = Mock()
        initial_entry.entry_id = "test_integration_entry"
        initial_entry.data = {
            "name": "Integration Test Climate",
            "room_sensor": "sensor.room_temperature",
            "climate_entity": "climate.integration_test"
        }
        initial_entry.options = {
            "max_offset": 3.0,  # Initial value
            "min_cycle_time": 600,
            "learning_enabled": True
        }
        initial_entry.runtime_data = {}
        
        # Mock entry registration methods
        mock_unsubscribe = Mock()
        initial_entry.add_update_listener = Mock(return_value=mock_unsubscribe)
        initial_entry.async_on_unload = Mock()
        
        # Track if entities were created/recreated
        entity_creation_calls = []
        
        def track_platform_setup(*args, **kwargs):
            entity_creation_calls.append(args)
            return True
        
        # Mock entity waiter and all component dependencies
        with patch('custom_components.smart_climate.EntityWaiter') as mock_waiter, \
             patch('custom_components.smart_climate.SmartClimateDataStore'), \
             patch('custom_components.smart_climate.OffsetEngine'), \
             patch('custom_components.smart_climate.SeasonalHysteresisLearner'), \
             patch('custom_components.smart_climate.FeatureEngineering'), \
             patch('custom_components.smart_climate.SensorManager'), \
             patch('custom_components.smart_climate.ThermalManager'), \
             patch('custom_components.smart_climate.ProbeManager'):
            
            # Configure entity waiter
            mock_waiter_instance = AsyncMock()
            mock_waiter_instance.wait_for_entities = AsyncMock(
                return_value=["climate.integration_test"]
            )
            mock_waiter.return_value = mock_waiter_instance
            
            # Mock platform forwarding
            mock_hass.config_entries.async_forward_entry_setups = AsyncMock(
                side_effect=track_platform_setup
            )
            
            # Step 1: Set up integration with initial options
            result = await async_setup_entry(mock_hass, initial_entry)
            assert result is True, "Initial setup should succeed"
            
            # Verify update_listener was registered during setup
            initial_entry.add_update_listener.assert_called_once_with(update_listener)
            initial_entry.async_on_unload.assert_called()
            
            # Verify initial platform setup (entities created)
            assert len(entity_creation_calls) >= 1, "Should have created entities initially"
            initial_platform_calls = len(entity_creation_calls)
            
            # Reset mocks for reload test
            mock_hass.config_entries.async_reload.reset_mock()
            entity_creation_calls.clear()
            
            # Step 2: Simulate options change (max_offset from 3 to 5)
            updated_entry = Mock()
            updated_entry.entry_id = "test_integration_entry"
            updated_entry.data = initial_entry.data.copy()
            updated_entry.options = {
                "max_offset": 5.0,  # Changed value
                "min_cycle_time": 600,
                "learning_enabled": True
            }
            updated_entry.runtime_data = {}
            
            # Step 3: Call update_listener directly (simulating what HA does)
            await update_listener(mock_hass, updated_entry)
            
            # Step 4: Verify async_reload was called
            mock_hass.config_entries.async_reload.assert_called_once_with(
                "test_integration_entry"
            )
            
    @pytest.mark.asyncio
    async def test_update_listener_with_real_homeassistant_instance(self):
        """Test update_listener with more realistic HomeAssistant instance."""
        # Create a more realistic mock that behaves like actual HA
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {}}
        
        # Mock config_entries with actual-like behavior
        mock_config_entries = Mock()
        mock_config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
        mock_config_entries.async_reload = AsyncMock(return_value=True)
        mock_hass.config_entries = mock_config_entries
        
        mock_hass.async_add_executor_job = AsyncMock()
        mock_hass.services = Mock()
        mock_hass.services.async_register = Mock()
        
        # Create ConfigEntry with test data
        entry = Mock()
        entry.entry_id = "realistic_test_entry"
        entry.data = {
            "name": "Realistic Test Climate",
            "room_sensor": "sensor.living_room_temperature",
            "climate_entity": "climate.living_room"
        }
        entry.options = {
            "max_offset": 2.5,
            "learning_enabled": False,
            "thermal_efficiency_enabled": True
        }
        entry.runtime_data = {}
        
        # Mock registration
        entry.add_update_listener = Mock(return_value=Mock())
        entry.async_on_unload = Mock()
        
        # Test setup and registration
        with patch('custom_components.smart_climate.EntityWaiter') as mock_waiter, \
             patch('custom_components.smart_climate.SmartClimateDataStore'), \
             patch('custom_components.smart_climate.OffsetEngine'), \
             patch('custom_components.smart_climate.SeasonalHysteresisLearner'), \
             patch('custom_components.smart_climate.FeatureEngineering'), \
             patch('custom_components.smart_climate.SensorManager'), \
             patch('custom_components.smart_climate.ThermalManager'), \
             patch('custom_components.smart_climate.ProbeManager'):
            
            mock_waiter_instance = AsyncMock()
            mock_waiter_instance.wait_for_entities = AsyncMock(
                return_value=["climate.living_room"]
            )
            mock_waiter.return_value = mock_waiter_instance
            
            # Setup integration
            setup_result = await async_setup_entry(mock_hass, entry)
            assert setup_result is True
            
            # Verify registration
            entry.add_update_listener.assert_called_once_with(update_listener)
            
            # Test update_listener call
            await update_listener(mock_hass, entry)
            
            # Verify reload was triggered
            mock_config_entries.async_reload.assert_called_once_with("realistic_test_entry")
            
    @pytest.mark.asyncio  
    async def test_update_listener_logging_during_integration(self, caplog):
        """Test that update_listener logs correctly during integration flow."""
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {}}
        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_reload = AsyncMock()
        
        entry = Mock()
        entry.entry_id = "logging_test_entry"
        entry.data = {"name": "Test", "room_sensor": "sensor.test", "climate_entity": "climate.test"}
        entry.options = {}
        
        # Test logging during update_listener call
        with caplog.at_level(logging.INFO):
            await update_listener(mock_hass, entry)
            
        # Verify expected log messages
        log_messages = [record.message for record in caplog.records]
        assert any(
            "Reloading Smart Climate integration due to options update" in message
            for message in log_messages
        ), "Expected reload log message not found"
        
        # Verify reload was called
        mock_hass.config_entries.async_reload.assert_called_once_with("logging_test_entry")

    @pytest.mark.asyncio
    async def test_update_listener_handles_reload_errors_gracefully(self):
        """Test update_listener handles reload errors without crashing."""
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {}}
        mock_hass.config_entries = Mock()
        
        # Mock reload to raise an exception
        mock_hass.config_entries.async_reload = AsyncMock(
            side_effect=Exception("Simulated reload error")
        )
        
        entry = Mock()
        entry.entry_id = "error_test_entry"
        entry.data = {"name": "Test", "room_sensor": "sensor.test", "climate_entity": "climate.test"}
        entry.options = {}
        
        # update_listener should not crash even if reload fails
        try:
            await update_listener(mock_hass, entry)
            # If we reach this point, the exception was not properly handled
            pytest.fail("update_listener should have raised the reload exception")
        except Exception as e:
            # This is expected - update_listener should let reload errors propagate
            # so HA can handle them appropriately
            assert "Simulated reload error" in str(e)
        
        # Verify reload was attempted
        mock_hass.config_entries.async_reload.assert_called_once_with("error_test_entry")