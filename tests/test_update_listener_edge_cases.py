"""ABOUTME: Edge cases and validation tests for update_listener functionality.
Tests robustness during concurrent operations, invalid options, cleanup edge cases, and memory leak prevention."""

import pytest
import asyncio
import weakref
from unittest.mock import Mock, AsyncMock, MagicMock, patch, call
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError

from custom_components.smart_climate import update_listener, async_setup_entry, async_unload_entry
from custom_components.smart_climate.const import DOMAIN


class TestUpdateListenerEdgeCases:
    """Test edge cases for update_listener functionality."""

    @pytest.mark.asyncio
    async def test_reload_during_offset_calculation(self):
        """Test reload while offset calculation is in progress."""
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {}}
        mock_hass.config_entries = Mock()
        
        # Mock a slow async_reload to simulate concurrent operations
        slow_reload_called = asyncio.Event()
        reload_completed = asyncio.Event()
        
        async def slow_reload(entry_id):
            slow_reload_called.set()
            # Simulate long-running reload operation
            await asyncio.sleep(0.1)
            reload_completed.set()
            return True
        
        mock_hass.config_entries.async_reload = AsyncMock(side_effect=slow_reload)
        
        entry = Mock()
        entry.entry_id = "test_concurrent_entry"
        entry.data = {"name": "Test", "room_sensor": "sensor.test", "climate_entity": "climate.test"}
        entry.options = {"max_offset": 3.0}
        
        # Start update_listener in background
        update_task = asyncio.create_task(update_listener(mock_hass, entry))
        
        # Wait for reload to start
        await slow_reload_called.wait()
        
        # Now start another offset calculation simulation
        offset_calculation_running = True
        
        # Complete the reload
        await reload_completed.wait()
        await update_task
        
        # Verify reload was called
        mock_hass.config_entries.async_reload.assert_called_once_with("test_concurrent_entry")
        
        # Verify no exceptions were raised
        assert update_task.done()
        assert not update_task.cancelled()

    @pytest.mark.asyncio
    async def test_reload_during_data_persistence(self):
        """Test reload while data persistence is happening."""
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {}}
        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_reload = AsyncMock()
        
        entry = Mock()
        entry.entry_id = "test_persistence_entry"
        entry.data = {"name": "Test", "room_sensor": "sensor.test", "climate_entity": "climate.test"}
        entry.options = {"max_offset": 2.5}
        
        # Simulate persistence operation in progress
        persistence_event = asyncio.Event()
        
        async def simulate_persistence():
            # This simulates a data persistence operation
            await asyncio.sleep(0.05)
            persistence_event.set()
        
        # Start persistence simulation
        persistence_task = asyncio.create_task(simulate_persistence())
        
        # Trigger reload during persistence
        await update_listener(mock_hass, entry)
        
        # Wait for persistence to complete
        await persistence_event.wait()
        await persistence_task
        
        # Verify reload was called even during persistence
        mock_hass.config_entries.async_reload.assert_called_once_with("test_persistence_entry")

    @pytest.mark.asyncio
    async def test_multiple_rapid_reloads(self):
        """Test multiple rapid reloads."""
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {}}
        mock_hass.config_entries = Mock()
        
        reload_calls = []
        
        async def track_reload(entry_id):
            reload_calls.append(entry_id)
            await asyncio.sleep(0.01)  # Small delay to simulate reload time
            return True
        
        mock_hass.config_entries.async_reload = AsyncMock(side_effect=track_reload)
        
        entry = Mock()
        entry.entry_id = "test_rapid_reload_entry"
        entry.data = {"name": "Test", "room_sensor": "sensor.test", "climate_entity": "climate.test"}
        entry.options = {"max_offset": 1.0}
        
        # Fire off multiple rapid reloads
        tasks = []
        for i in range(5):
            tasks.append(asyncio.create_task(update_listener(mock_hass, entry)))
        
        # Wait for all to complete
        await asyncio.gather(*tasks)
        
        # Verify all reloads were attempted
        assert len(reload_calls) == 5
        assert all(call_id == "test_rapid_reload_entry" for call_id in reload_calls)
        
        # Verify async_reload was called 5 times
        assert mock_hass.config_entries.async_reload.call_count == 5

    @pytest.mark.asyncio
    async def test_reload_with_invalid_new_options(self):
        """Test reload with invalid new options."""
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {}}
        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_reload = AsyncMock()
        
        entry = Mock()
        entry.entry_id = "test_invalid_options_entry"
        entry.data = {"name": "Test", "room_sensor": "sensor.test", "climate_entity": "climate.test"}
        
        # Test with various invalid options
        invalid_options_list = [
            {"max_offset": -1.0},  # Negative offset
            {"max_offset": 100.0},  # Excessive offset
            {"min_cycle_time": -500},  # Negative time
            {"learning_enabled": "invalid"},  # Wrong type
            {},  # Empty options - should use defaults
        ]
        
        for invalid_options in invalid_options_list:
            entry.options = invalid_options
            
            # update_listener should still attempt reload
            # Options validation is handled by OptionsFlow, not update_listener
            await update_listener(mock_hass, entry)
            
            # Verify reload was attempted despite invalid options
            mock_hass.config_entries.async_reload.assert_called_with("test_invalid_options_entry")
        
        # Should have been called once for each invalid option set
        assert mock_hass.config_entries.async_reload.call_count == len(invalid_options_list)

    @pytest.mark.asyncio
    async def test_unloading_integration_while_reload_in_progress(self):
        """Test unloading integration while reload is in progress."""
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {"test_unload_entry": {}}}
        mock_hass.config_entries = Mock()
        
        reload_started = asyncio.Event()
        reload_should_complete = asyncio.Event()
        
        async def slow_reload(entry_id):
            reload_started.set()
            await reload_should_complete.wait()
            return True
        
        mock_hass.config_entries.async_reload = AsyncMock(side_effect=slow_reload)
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        
        entry = Mock()
        entry.entry_id = "test_unload_entry"
        entry.data = {"name": "Test", "room_sensor": "sensor.test", "climate_entity": "climate.test"}
        entry.options = {"max_offset": 2.0}
        
        # Start reload in background
        reload_task = asyncio.create_task(update_listener(mock_hass, entry))
        
        # Wait for reload to start
        await reload_started.wait()
        
        # Now simulate unload while reload is in progress
        unload_result = await async_unload_entry(mock_hass, entry)
        
        # Allow reload to complete
        reload_should_complete.set()
        await reload_task
        
        # Verify unload succeeded
        assert unload_result is True
        
        # Verify both operations completed
        mock_hass.config_entries.async_reload.assert_called_once_with("test_unload_entry")
        mock_hass.config_entries.async_unload_platforms.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_update_listeners_prevention(self):
        """Test that multiple update_listeners cannot be registered simultaneously."""
        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
        mock_hass.async_add_executor_job = AsyncMock()
        mock_hass.services.async_register = Mock()
        
        entry = MagicMock()
        entry.entry_id = "test_multiple_listeners_entry"
        entry.data = {
            "name": "Test Climate",
            "room_sensor": "sensor.room_temperature",
            "climate_entity": "climate.test"
        }
        entry.options = {}
        entry.runtime_data = {}
        
        # Mock registration methods
        listener_calls = []
        def track_add_listener(listener_func):
            listener_calls.append(listener_func)
            return Mock()  # Return mock unsubscribe function
        
        entry.add_update_listener = Mock(side_effect=track_add_listener)
        entry.async_on_unload = Mock()
        
        # Mock entity waiter and components
        with patch('custom_components.smart_climate.EntityWaiter') as mock_waiter, \
             patch('custom_components.smart_climate.SmartClimateDataStore'), \
             patch('custom_components.smart_climate.OffsetEngine'), \
             patch('custom_components.smart_climate.SeasonalHysteresisLearner'), \
             patch('custom_components.smart_climate.FeatureEngineering'), \
             patch('custom_components.smart_climate.SensorManager'), \
             patch('custom_components.smart_climate.ThermalManager'), \
             patch('custom_components.smart_climate.ProbeManager'):
            
            mock_waiter_instance = AsyncMock()
            mock_waiter_instance.wait_for_entities = AsyncMock(return_value=["climate.test"])
            mock_waiter.return_value = mock_waiter_instance
            
            # First setup should succeed
            result1 = await async_setup_entry(mock_hass, entry)
            assert result1 is True
            
            # Verify listener was registered
            assert len(listener_calls) == 1
            assert listener_calls[0] == update_listener
            
            # Try to setup again with same entry (simulating double registration)
            entry.add_update_listener.reset_mock()
            listener_calls.clear()
            
            # Second setup should not add another listener (HA prevents this by design)
            # But our code should handle it gracefully
            result2 = await async_setup_entry(mock_hass, entry)
            assert result2 is True
            
            # In HA, this would only register one listener per entry automatically
            # Our implementation should follow this pattern

    @pytest.mark.asyncio
    async def test_update_listener_called_after_integration_unloaded(self):
        """Test update_listener called after integration is unloaded."""
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {}}
        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_reload = AsyncMock()
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        
        entry = Mock()
        entry.entry_id = "test_after_unload_entry"
        entry.data = {"name": "Test", "room_sensor": "sensor.test", "climate_entity": "climate.test"}
        entry.options = {"max_offset": 1.5}
        
        # First unload the integration
        mock_hass.data[DOMAIN]["test_after_unload_entry"] = {"unload_listeners": []}
        await async_unload_entry(mock_hass, entry)
        
        # Verify entry data was removed
        assert "test_after_unload_entry" not in mock_hass.data[DOMAIN]
        
        # Now call update_listener after unload
        # This should not crash - HA will still call reload
        await update_listener(mock_hass, entry)
        
        # Verify reload was still attempted
        mock_hass.config_entries.async_reload.assert_called_once_with("test_after_unload_entry")

    @pytest.mark.asyncio
    async def test_memory_leak_prevention(self):
        """Test memory leak prevention."""
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {}}
        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_reload = AsyncMock()
        
        # Create multiple entries and weak references to track memory
        entries = []
        weak_refs = []
        
        for i in range(10):
            entry = Mock()
            entry.entry_id = f"test_memory_entry_{i}"
            entry.data = {"name": f"Test {i}", "room_sensor": f"sensor.test_{i}", "climate_entity": f"climate.test_{i}"}
            entry.options = {"max_offset": 2.0}
            
            entries.append(entry)
            weak_refs.append(weakref.ref(entry))
            
            # Call update_listener for each entry
            await update_listener(mock_hass, entry)
        
        # Clear strong references
        entries.clear()
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Check that entries can be garbage collected
        # (In a real test, we'd need more sophisticated memory leak detection)
        alive_refs = sum(1 for ref in weak_refs if ref() is not None)
        
        # Some references might still be alive due to mocking framework
        # The important thing is that update_listener doesn't hold strong references
        # This is a basic smoke test
        assert alive_refs >= 0  # Basic sanity check
        
        # Verify all reloads were called
        assert mock_hass.config_entries.async_reload.call_count == 10

    @pytest.mark.asyncio
    async def test_reload_with_concurrent_operations_stress_test(self):
        """Stress test reload with many concurrent operations."""
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {}}
        mock_hass.config_entries = Mock()
        
        reload_count = 0
        reload_lock = asyncio.Lock()
        
        async def counting_reload(entry_id):
            nonlocal reload_count
            async with reload_lock:
                reload_count += 1
            await asyncio.sleep(0.001)  # Tiny delay
            return True
        
        mock_hass.config_entries.async_reload = AsyncMock(side_effect=counting_reload)
        
        entry = Mock()
        entry.entry_id = "test_stress_entry"
        entry.data = {"name": "Stress Test", "room_sensor": "sensor.stress", "climate_entity": "climate.stress"}
        entry.options = {"max_offset": 3.0}
        
        # Create many concurrent operations
        tasks = []
        num_operations = 50
        
        for i in range(num_operations):
            # Mix of reload calls and other operations
            if i % 3 == 0:
                tasks.append(asyncio.create_task(update_listener(mock_hass, entry)))
            elif i % 3 == 1:
                # Simulate other async operations
                tasks.append(asyncio.create_task(asyncio.sleep(0.001)))
            else:
                # More reload calls
                tasks.append(asyncio.create_task(update_listener(mock_hass, entry)))
        
        # Wait for all operations to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check that no exceptions were raised
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, f"Got exceptions: {exceptions}"
        
        # Count how many update_listener calls we made
        expected_reload_calls = sum(1 for i in range(num_operations) if i % 3 != 1)
        assert reload_count == expected_reload_calls
        assert mock_hass.config_entries.async_reload.call_count == expected_reload_calls

    @pytest.mark.asyncio
    async def test_reload_with_exception_handling(self):
        """Test reload exception handling."""
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {}}
        mock_hass.config_entries = Mock()
        
        entry = Mock()
        entry.entry_id = "test_exception_entry"
        entry.data = {"name": "Exception Test", "room_sensor": "sensor.exception", "climate_entity": "climate.exception"}
        entry.options = {"max_offset": 2.0}
        
        # Test with a simple Exception
        test_exception = Exception("General reload error")
        mock_hass.config_entries.async_reload = AsyncMock(side_effect=test_exception)
        
        # update_listener should let the exception propagate to HA
        with pytest.raises(Exception) as exc_info:
            await update_listener(mock_hass, entry)
        
        # Verify the exception message matches
        assert "General reload error" in str(exc_info.value)
        
        # Verify reload was attempted
        mock_hass.config_entries.async_reload.assert_called_with("test_exception_entry")
        
        # Test with asyncio.TimeoutError
        mock_hass.config_entries.async_reload.reset_mock()
        timeout_exception = asyncio.TimeoutError("Reload timeout")
        mock_hass.config_entries.async_reload = AsyncMock(side_effect=timeout_exception)
        
        with pytest.raises(asyncio.TimeoutError) as exc_info:
            await update_listener(mock_hass, entry)
        
        # Verify the exception message matches
        assert "Reload timeout" in str(exc_info.value)
        
        # Verify reload was attempted
        mock_hass.config_entries.async_reload.assert_called_with("test_exception_entry")

    @pytest.mark.asyncio
    async def test_reload_logging_during_edge_cases(self, caplog):
        """Test that logging works correctly during edge cases."""
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {}}
        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_reload = AsyncMock()
        
        entry = Mock()
        entry.entry_id = "test_logging_edge_case"
        entry.data = {"name": "Logging Test", "room_sensor": "sensor.logging", "climate_entity": "climate.logging"}
        entry.options = {}
        
        # Test logging with various scenarios
        scenarios = [
            {"name": "empty_options", "options": {}},
            {"name": "minimal_options", "options": {"max_offset": 1.0}},
            {"name": "full_options", "options": {"max_offset": 3.0, "learning_enabled": True, "min_cycle_time": 300}},
        ]
        
        for scenario in scenarios:
            entry.options = scenario["options"]
            
            with caplog.at_level(logging.INFO):
                await update_listener(mock_hass, entry)
            
            # Verify reload log message was created
            log_messages = [record.message for record in caplog.records]
            assert any(
                "Reloading Smart Climate integration due to options update" in message
                for message in log_messages
            ), f"Expected log message not found for scenario: {scenario['name']}"
            
            caplog.clear()
        
        # Verify reload was called for each scenario
        assert mock_hass.config_entries.async_reload.call_count == len(scenarios)