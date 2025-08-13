"""ABOUTME: Tests for update_listener registration in Smart Climate integration.
Validates update listener registration pattern for HACS reload support."""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch, call
from custom_components.smart_climate import update_listener


class TestUpdateListenerRegistration:
    """Test update listener registration in async_setup_entry."""

    def test_update_listener_function_exists(self):
        """Test that update_listener function exists and is callable."""
        # Import the function that should be implemented by Agent A1
        assert hasattr(update_listener, '__call__'), "update_listener should be callable"
        assert callable(update_listener), "update_listener should be a callable function"

    @pytest.mark.asyncio
    async def test_update_listener_registration_in_setup_entry(self):
        """Test that update_listener is properly registered in async_setup_entry."""
        from custom_components.smart_climate import async_setup_entry
        
        # Create mock HomeAssistant instance
        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
        mock_hass.config_entries.async_reload = AsyncMock(return_value=True)
        mock_hass.async_add_executor_job = AsyncMock()
        mock_hass.services.async_register = Mock()
        
        # Create mock ConfigEntry
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_123"
        mock_entry.data = {
            "name": "Test Climate",
            "room_sensor": "sensor.room_temperature",
            "climate_entity": "climate.test"
        }
        mock_entry.options = {}
        mock_entry.runtime_data = {}
        
        # Mock the registration methods
        mock_unsubscribe_function = Mock()
        mock_entry.add_update_listener = Mock(return_value=mock_unsubscribe_function)
        mock_entry.async_on_unload = Mock()
        
        # Mock entity waiter to avoid entity lookup
        with patch('custom_components.smart_climate.EntityWaiter') as mock_waiter:
            mock_waiter_instance = AsyncMock()
            mock_waiter_instance.wait_for_entities = AsyncMock(return_value=["climate.test"])
            mock_waiter.return_value = mock_waiter_instance
            
            # Mock data store initialization
            with patch('custom_components.smart_climate.SmartClimateDataStore'):
                # Mock all the component creation that happens in setup
                with patch('custom_components.smart_climate.OffsetEngine'), \
                     patch('custom_components.smart_climate.SeasonalHysteresisLearner'), \
                     patch('custom_components.smart_climate.FeatureEngineering'), \
                     patch('custom_components.smart_climate.SensorManager'), \
                     patch('custom_components.smart_climate.ThermalManager'), \
                     patch('custom_components.smart_climate.ProbeManager'):
                    
                    # Call async_setup_entry
                    result = await async_setup_entry(mock_hass, mock_entry)
                    
                    # Verify setup succeeded
                    assert result is True, "async_setup_entry should return True"
                    
                    # Verify update_listener was registered
                    mock_entry.add_update_listener.assert_called_once()
                    
                    # Verify the function passed to add_update_listener is our update_listener
                    call_args = mock_entry.add_update_listener.call_args[0]
                    registered_listener = call_args[0]
                    assert registered_listener is update_listener, "Should register the update_listener function"
                    
                    # Verify the unsubscribe function is registered for cleanup
                    mock_entry.async_on_unload.assert_called()
                    cleanup_calls = mock_entry.async_on_unload.call_args_list
                    
                    # Check that the unsubscribe function from add_update_listener was passed to async_on_unload
                    found_listener_cleanup = False
                    for cleanup_call in cleanup_calls:
                        if cleanup_call[0][0] == mock_unsubscribe_function:
                            found_listener_cleanup = True
                            break
                    
                    assert found_listener_cleanup, "Should register update_listener unsubscribe for cleanup"

    @pytest.mark.asyncio
    async def test_update_listener_registration_stores_in_runtime_data(self):
        """Test that update listener registration is tracked in entry runtime data."""
        from custom_components.smart_climate import async_setup_entry
        
        # Create mock HomeAssistant instance
        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
        mock_hass.async_add_executor_job = AsyncMock()
        mock_hass.services.async_register = Mock()
        
        # Create mock ConfigEntry
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_456"
        mock_entry.data = {
            "name": "Test Climate",
            "room_sensor": "sensor.room_temperature", 
            "climate_entity": "climate.test"
        }
        mock_entry.options = {}
        
        # Mock the registration methods
        mock_unsubscribe_function = Mock()
        mock_entry.add_update_listener = Mock(return_value=mock_unsubscribe_function)
        mock_entry.async_on_unload = Mock()
        
        # Mock entity waiter
        with patch('custom_components.smart_climate.EntityWaiter') as mock_waiter:
            mock_waiter_instance = AsyncMock()
            mock_waiter_instance.wait_for_entities = AsyncMock(return_value=["climate.test"])
            mock_waiter.return_value = mock_waiter_instance
            
            # Mock data store and components
            with patch('custom_components.smart_climate.SmartClimateDataStore'), \
                 patch('custom_components.smart_climate.OffsetEngine'), \
                 patch('custom_components.smart_climate.SeasonalHysteresisLearner'), \
                 patch('custom_components.smart_climate.FeatureEngineering'), \
                 patch('custom_components.smart_climate.SensorManager'), \
                 patch('custom_components.smart_climate.ThermalManager'), \
                 patch('custom_components.smart_climate.ProbeManager'):
                
                # Call async_setup_entry
                result = await async_setup_entry(mock_hass, mock_entry)
                
                # Verify setup succeeded
                assert result is True, "async_setup_entry should return True"
                
                # Check that the entry data structure exists in hass.data
                assert "smart_climate" in mock_hass.data, "Domain data should be created"
                assert mock_entry.entry_id in mock_hass.data["smart_climate"], "Entry data should be created"
                
                entry_data = mock_hass.data["smart_climate"][mock_entry.entry_id]
                assert isinstance(entry_data, dict), "Entry data should be a dictionary"

    @pytest.mark.asyncio 
    async def test_update_listener_registration_no_exceptions(self):
        """Test that update_listener registration doesn't raise exceptions."""
        from custom_components.smart_climate import async_setup_entry
        
        # Create mock HomeAssistant instance
        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
        mock_hass.async_add_executor_job = AsyncMock()
        mock_hass.services.async_register = Mock()
        
        # Create mock ConfigEntry
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_789"
        mock_entry.data = {
            "name": "Test Climate",
            "room_sensor": "sensor.room_temperature",
            "climate_entity": "climate.test"
        }
        mock_entry.options = {}
        
        # Mock successful registration
        mock_entry.add_update_listener = Mock(return_value=Mock())
        mock_entry.async_on_unload = Mock()
        
        # Mock entity waiter
        with patch('custom_components.smart_climate.EntityWaiter') as mock_waiter:
            mock_waiter_instance = AsyncMock()
            mock_waiter_instance.wait_for_entities = AsyncMock(return_value=["climate.test"])
            mock_waiter.return_value = mock_waiter_instance
            
            # Mock all components
            with patch('custom_components.smart_climate.SmartClimateDataStore'), \
                 patch('custom_components.smart_climate.OffsetEngine'), \
                 patch('custom_components.smart_climate.SeasonalHysteresisLearner'), \
                 patch('custom_components.smart_climate.FeatureEngineering'), \
                 patch('custom_components.smart_climate.SensorManager'), \
                 patch('custom_components.smart_climate.ThermalManager'), \
                 patch('custom_components.smart_climate.ProbeManager'):
                
                # This should not raise any exceptions
                try:
                    result = await async_setup_entry(mock_hass, mock_entry)
                    assert result is True, "Setup should succeed"
                except Exception as e:
                    pytest.fail(f"update_listener registration should not raise exceptions: {e}")

    @pytest.mark.asyncio
    async def test_update_listener_registration_with_existing_listeners(self):
        """Test update_listener registration when other listeners already exist."""
        from custom_components.smart_climate import async_setup_entry
        
        # Create mock HomeAssistant instance
        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
        mock_hass.async_add_executor_job = AsyncMock()
        mock_hass.services.async_register = Mock()
        
        # Create mock ConfigEntry with existing unload listeners
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_existing"
        mock_entry.data = {
            "name": "Test Climate", 
            "room_sensor": "sensor.room_temperature",
            "climate_entity": "climate.test"
        }
        mock_entry.options = {}
        
        # Track calls to async_on_unload to verify multiple registrations
        unload_calls = []
        def track_unload_calls(func):
            unload_calls.append(func)
            
        mock_entry.add_update_listener = Mock(return_value=Mock())
        mock_entry.async_on_unload = Mock(side_effect=track_unload_calls)
        
        # Mock entity waiter
        with patch('custom_components.smart_climate.EntityWaiter') as mock_waiter:
            mock_waiter_instance = AsyncMock()
            mock_waiter_instance.wait_for_entities = AsyncMock(return_value=["climate.test"])
            mock_waiter.return_value = mock_waiter_instance
            
            # Mock all components
            with patch('custom_components.smart_climate.SmartClimateDataStore'), \
                 patch('custom_components.smart_climate.OffsetEngine'), \
                 patch('custom_components.smart_climate.SeasonalHysteresisLearner'), \
                 patch('custom_components.smart_climate.FeatureEngineering'), \
                 patch('custom_components.smart_climate.SensorManager'), \
                 patch('custom_components.smart_climate.ThermalManager'), \
                 patch('custom_components.smart_climate.ProbeManager'):
                
                # Call async_setup_entry
                result = await async_setup_entry(mock_hass, mock_entry)
                
                # Verify setup succeeded
                assert result is True, "async_setup_entry should return True"
                
                # Verify update_listener was registered
                mock_entry.add_update_listener.assert_called_once_with(update_listener)
                
                # Verify cleanup functions were registered
                # Note: Currently only update_listener cleanup is registered
                assert len(unload_calls) >= 1, "Should register at least one cleanup function (update_listener)"
                print(f"DEBUG: Registered {len(unload_calls)} cleanup functions")
                
                # Verify at least one cleanup is for the update_listener
                assert mock_entry.add_update_listener.return_value in unload_calls, \
                    "Update listener unsubscribe function should be registered for cleanup"

    def test_update_listener_import_availability(self):
        """Test that update_listener can be imported from the main module."""
        # This test verifies that Agent A1 has implemented the update_listener function
        # and made it importable from the main __init__.py module
        
        try:
            from custom_components.smart_climate import update_listener
            assert callable(update_listener), "update_listener should be callable"
        except ImportError:
            pytest.fail("update_listener function should be importable from main module")
        except AttributeError:
            pytest.fail("update_listener function should exist in main module")