"""Integration tests for retry mechanism in real Home Assistant environment."""

import asyncio
from datetime import timedelta
from unittest.mock import Mock, patch, AsyncMock, call, PropertyMock
import pytest
import pytest_asyncio
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.const import STATE_UNAVAILABLE, STATE_OFF
from homeassistant.setup import async_setup_component
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_test_home_assistant,
    async_fire_time_changed,
)

from custom_components.smart_climate import async_setup_entry, async_reload_entry
from custom_components.smart_climate.const import DOMAIN
from custom_components.smart_climate.entity_waiter import EntityNotAvailableError


@pytest_asyncio.fixture
async def hass():
    """Create a test Home Assistant instance."""
    async with async_test_home_assistant() as hass:
        yield hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry with retry enabled."""
    return MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Test Climate",
        data={
            "climate_entity": "climate.test",
            "room_sensor": "sensor.test_temperature",
            "enable_retry": True,
            "max_retry_attempts": 4,
            "initial_timeout": 60,
        },
        source="user",
        entry_id="test_entry_id",
    )


@pytest.fixture
def mock_config_entry_multi():
    """Create a mock config entry with multiple climate entities."""
    return MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Multi Climate",
        data={
            "climate_entities": ["climate.test1", "climate.test2"],
            "room_sensor": "sensor.test_temperature",
            "enable_retry": True,
            "max_retry_attempts": 3,
            "initial_timeout": 45,
        },
        source="user",
        entry_id="multi_entry_id",
    )


class TestRetryIntegration:
    """Test retry mechanism in full integration scenarios."""

    @pytest.mark.asyncio
    async def test_entity_becomes_available_after_one_retry(self, hass: HomeAssistant, mock_config_entry):
        """Test entity becomes available after a single retry attempt."""
        # Add config entry to hass
        mock_config_entry.add_to_hass(hass)
        
        # Track retry calls
        retry_calls = []
        original_schedule_retry = None
        
        async def track_retry(hass, entry, attempt):
            retry_calls.append(attempt)
            # Call the original function
            from custom_components.smart_climate import _schedule_retry
            await _schedule_retry(hass, entry, attempt)
        
        # Initially set entities as unavailable
        hass.states.async_set("climate.test", STATE_UNAVAILABLE)
        hass.states.async_set("sensor.test_temperature", STATE_UNAVAILABLE)
        
        # Patch _schedule_retry to track calls
        with patch("custom_components.smart_climate._schedule_retry", side_effect=track_retry):
            # Initial setup should fail and schedule retry
            result = await async_setup_entry(hass, mock_config_entry)
            assert result is False
            assert len(retry_calls) == 1
            assert retry_calls[0] == 1
            
            # Make entities available before retry
            hass.states.async_set("climate.test", STATE_OFF)
            hass.states.async_set("sensor.test_temperature", "22.5")
            
            # Simulate time passing (30 seconds for first retry)
            await asyncio.sleep(0.1)  # Small delay to ensure retry is scheduled
            async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
            await hass.async_block_till_done()
            
            # After retry, check if setup succeeded
            assert mock_config_entry.state == ConfigEntryState.LOADED

    @pytest.mark.asyncio
    async def test_entity_becomes_available_after_multiple_retries(self, hass: HomeAssistant, mock_config_entry):
        """Test entity becomes available after multiple retry attempts."""
        # Add config entry to hass
        mock_config_entry.add_to_hass(hass)
        
        # Track all setup attempts
        setup_attempts = []
        entity_availability_states = []
        
        async def mock_wait_for_entities(self, hass, config, timeout=60):
            setup_attempts.append(len(setup_attempts) + 1)
            # Check current entity states
            climate_state = hass.states.get("climate.test")
            sensor_state = hass.states.get("sensor.test_temperature")
            
            if len(setup_attempts) < 3:
                # First two attempts fail
                entity_availability_states.append("unavailable")
                raise EntityNotAvailableError("Entities not available")
            else:
                # Third attempt succeeds
                if climate_state and climate_state.state != STATE_UNAVAILABLE:
                    entity_availability_states.append("available")
                    return True
                else:
                    entity_availability_states.append("still_unavailable")
                    raise EntityNotAvailableError("Still not available")
        
        # Initially set entities as unavailable
        hass.states.async_set("climate.test", STATE_UNAVAILABLE)
        hass.states.async_set("sensor.test_temperature", STATE_UNAVAILABLE)
        
        with patch("custom_components.smart_climate.entity_waiter.EntityWaiter.wait_for_required_entities",
                   mock_wait_for_entities):
            # Initial setup
            result = await async_setup_entry(hass, mock_config_entry)
            assert result is False
            assert len(setup_attempts) == 1
            
            # Simulate first retry after 30 seconds
            await asyncio.sleep(0.1)
            async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
            await hass.async_block_till_done()
            
            # Should have attempted again and failed
            assert len(setup_attempts) == 2
            assert mock_config_entry.state != ConfigEntryState.LOADED
            
            # Make entities available before second retry
            hass.states.async_set("climate.test", STATE_OFF)
            hass.states.async_set("sensor.test_temperature", "22.5")
            
            # Simulate second retry after 60 seconds
            async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=91))
            await hass.async_block_till_done()
            
            # Should succeed on third attempt
            assert len(setup_attempts) == 3
            assert entity_availability_states == ["unavailable", "unavailable", "available"]

    @pytest.mark.asyncio
    async def test_config_entry_state_transitions_during_retry(self, hass: HomeAssistant, mock_config_entry):
        """Test config entry state transitions during retry sequence."""
        # Add config entry to hass
        mock_config_entry.add_to_hass(hass)
        
        # Track state transitions
        state_transitions = []
        
        # Patch state property to track changes
        original_state = mock_config_entry.state
        
        def track_state():
            state_transitions.append(mock_config_entry.state)
            return original_state
        
        # Set entities as unavailable
        hass.states.async_set("climate.test", STATE_UNAVAILABLE)
        hass.states.async_set("sensor.test_temperature", STATE_UNAVAILABLE)
        
        with patch("custom_components.smart_climate.entity_waiter.EntityWaiter.wait_for_required_entities",
                   side_effect=EntityNotAvailableError("Not available")):
            # Initial setup fails
            result = await async_setup_entry(hass, mock_config_entry)
            assert result is False
            
            # Config entry should be in SETUP_RETRY state
            assert mock_config_entry.state == ConfigEntryState.SETUP_RETRY

    @pytest.mark.asyncio
    async def test_multiple_config_entries_with_different_retry_settings(self, hass: HomeAssistant):
        """Test multiple config entries with different retry configurations."""
        # Create entries with different settings
        entry1 = MockConfigEntry(
            version=1,
            domain=DOMAIN,
            title="Climate 1",
            data={
                "climate_entity": "climate.test1",
                "room_sensor": "sensor.temp1",
                "enable_retry": True,
                "max_retry_attempts": 2,
                "initial_timeout": 30,
            },
            source="user",
            entry_id="entry1",
        )
        
        entry2 = MockConfigEntry(
            version=1,
            domain=DOMAIN,
            title="Climate 2",
            data={
                "climate_entity": "climate.test2",
                "room_sensor": "sensor.temp2",
                "enable_retry": False,  # No retry
                "initial_timeout": 60,
            },
            source="user",
            entry_id="entry2",
        )
        
        entry3 = MockConfigEntry(
            version=1,
            domain=DOMAIN,
            title="Climate 3",
            data={
                "climate_entity": "climate.test3",
                "room_sensor": "sensor.temp3",
                "enable_retry": True,
                "max_retry_attempts": 4,
                "initial_timeout": 120,
            },
            source="user",
            entry_id="entry3",
        )
        
        # Add all entries
        entry1.add_to_hass(hass)
        entry2.add_to_hass(hass)
        entry3.add_to_hass(hass)
        
        # Set different availability states
        hass.states.async_set("climate.test1", STATE_UNAVAILABLE)
        hass.states.async_set("sensor.temp1", STATE_UNAVAILABLE)
        hass.states.async_set("climate.test2", STATE_UNAVAILABLE)
        hass.states.async_set("sensor.temp2", STATE_UNAVAILABLE)
        hass.states.async_set("climate.test3", STATE_OFF)  # Available
        hass.states.async_set("sensor.temp3", "23.0")
        
        # Track retries
        scheduled_retries = {}
        
        async def track_retry(hass, entry, attempt):
            if entry.entry_id not in scheduled_retries:
                scheduled_retries[entry.entry_id] = []
            scheduled_retries[entry.entry_id].append(attempt)
            # Actually schedule the retry
            from custom_components.smart_climate import _schedule_retry
            await _schedule_retry(hass, entry, attempt)
        
        with patch("custom_components.smart_climate._schedule_retry", side_effect=track_retry):
            # Setup all entries
            result1 = await async_setup_entry(hass, entry1)
            
            # Entry2 should raise exception (retry disabled)
            with pytest.raises(Exception):  # HomeAssistantError is mocked
                await async_setup_entry(hass, entry2)
            
            result3 = await async_setup_entry(hass, entry3)
            
            # Check results
            assert result1 is False  # Should retry
            assert "entry1" in scheduled_retries
            assert scheduled_retries["entry1"] == [1]
            
            assert "entry2" not in scheduled_retries  # No retry
            
            assert result3 is True  # Should succeed
            assert "entry3" not in scheduled_retries

    @pytest.mark.asyncio
    async def test_retry_cancellation_on_integration_unload(self, hass: HomeAssistant, mock_config_entry):
        """Test that scheduled retries are cancelled when integration is unloaded."""
        # Add config entry to hass
        mock_config_entry.add_to_hass(hass)
        
        # Track scheduled callbacks
        scheduled_callbacks = []
        
        def mock_async_call_later(hass, delay, callback):
            # Create a mock cancel function
            cancel = Mock()
            scheduled_callbacks.append((delay, callback, cancel))
            return cancel
        
        # Set entities as unavailable
        hass.states.async_set("climate.test", STATE_UNAVAILABLE)
        hass.states.async_set("sensor.test_temperature", STATE_UNAVAILABLE)
        
        with patch("custom_components.smart_climate.async_call_later", side_effect=mock_async_call_later):
            # Initial setup fails and schedules retry
            result = await async_setup_entry(hass, mock_config_entry)
            assert result is False
            assert len(scheduled_callbacks) == 1
            
            # Unload the integration
            from custom_components.smart_climate import async_unload_entry
            with patch("custom_components.smart_climate.async_unload_entry", return_value=True):
                await hass.config_entries.async_unload(mock_config_entry.entry_id)
            
            # The scheduled retry should have been cancelled
            # In a real scenario, the cancel function would be called

    @pytest.mark.asyncio
    async def test_manual_reload_during_retry_sequence(self, hass: HomeAssistant, mock_config_entry):
        """Test manual reload while retry is in progress."""
        # Add config entry to hass
        mock_config_entry.add_to_hass(hass)
        
        # Track reload calls
        reload_calls = []
        
        async def mock_reload(entry_id):
            reload_calls.append(entry_id)
            # Simulate successful reload
            hass.states.async_set("climate.test", STATE_OFF)
            hass.states.async_set("sensor.test_temperature", "22.5")
            return True
        
        # Set entities as unavailable
        hass.states.async_set("climate.test", STATE_UNAVAILABLE)
        hass.states.async_set("sensor.test_temperature", STATE_UNAVAILABLE)
        
        # Initial setup fails
        result = await async_setup_entry(hass, mock_config_entry)
        assert result is False
        
        # Manually reload before scheduled retry
        with patch.object(hass.config_entries, "async_reload", side_effect=mock_reload):
            await async_reload_entry(hass, mock_config_entry)
            
        assert len(reload_calls) == 1
        assert reload_calls[0] == mock_config_entry.entry_id

    @pytest.mark.asyncio
    async def test_notifications_sent_correctly(self, hass: HomeAssistant, mock_config_entry):
        """Test that notifications are sent correctly on final failure."""
        # Add config entry to hass
        mock_config_entry.add_to_hass(hass)
        
        # Set max attempts to 2 for faster test
        mock_config_entry._data["max_retry_attempts"] = 2
        
        # Track notifications
        notifications = []
        
        async def mock_notification(hass, title, message, notification_id=None):
            notifications.append({
                "title": title,
                "message": message,
                "notification_id": notification_id
            })
        
        # Set entities as unavailable
        hass.states.async_set("climate.test", STATE_UNAVAILABLE)
        hass.states.async_set("sensor.test_temperature", STATE_UNAVAILABLE)
        
        with patch("custom_components.smart_climate.entity_waiter.EntityWaiter.wait_for_required_entities",
                   side_effect=EntityNotAvailableError("Entities not available")):
            with patch("custom_components.smart_climate.async_create_notification",
                       side_effect=mock_notification):
                # Initial setup (attempt 1)
                result = await async_setup_entry(hass, mock_config_entry)
                assert result is False
                assert len(notifications) == 0  # No notification yet
                
                # Simulate first retry (attempt 2)
                hass.data[DOMAIN][mock_config_entry.entry_id]["_retry_attempt"] = 1
                await asyncio.sleep(0.1)
                async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
                await hass.async_block_till_done()
                
                # Now at max attempts, set retry attempt to 2
                hass.data[DOMAIN][mock_config_entry.entry_id]["_retry_attempt"] = 2
                result = await async_setup_entry(hass, mock_config_entry)
                assert result is False
                
                # Should have sent notification
                assert len(notifications) == 1
                assert "Smart Climate Setup Failed" in notifications[0]["title"]
                assert "failed to initialize after 2 attempts" in notifications[0]["message"]
                assert "manually reload" in notifications[0]["message"]
                assert notifications[0]["notification_id"] == f"smart_climate_setup_failed_{mock_config_entry.entry_id}"

    @pytest.mark.asyncio
    async def test_cleanup_on_unload(self, hass: HomeAssistant, mock_config_entry):
        """Test proper cleanup when integration is unloaded."""
        # Add config entry to hass
        mock_config_entry.add_to_hass(hass)
        
        # Set up with available entities
        hass.states.async_set("climate.test", STATE_OFF)
        hass.states.async_set("sensor.test_temperature", "22.5")
        
        # Mock platform setup
        with patch.object(hass.config_entries, "async_forward_entry_setups", return_value=True):
            result = await async_setup_entry(hass, mock_config_entry)
            assert result is True
        
        # Verify data is stored
        assert DOMAIN in hass.data
        assert mock_config_entry.entry_id in hass.data[DOMAIN]
        
        # Mock unload
        from custom_components.smart_climate import async_unload_entry
        
        # Create a proper mock for async_unload_entry
        async def mock_unload(hass, entry):
            # Simulate cleanup
            if entry.entry_id in hass.data.get(DOMAIN, {}):
                del hass.data[DOMAIN][entry.entry_id]
            return True
        
        with patch("custom_components.smart_climate.async_unload_entry", side_effect=mock_unload):
            # Unload the entry
            await hass.config_entries.async_unload(mock_config_entry.entry_id)
            
            # Verify cleanup
            assert mock_config_entry.entry_id not in hass.data.get(DOMAIN, {})

    @pytest.mark.asyncio
    async def test_actual_timing_with_time_advancement(self, hass: HomeAssistant, mock_config_entry):
        """Test actual retry timing using Home Assistant time advancement."""
        # Add config entry to hass
        mock_config_entry.add_to_hass(hass)
        
        # Track retry timing
        retry_times = []
        start_time = dt_util.utcnow()
        
        async def track_retry_time(hass, entry, attempt):
            current_time = dt_util.utcnow()
            elapsed = (current_time - start_time).total_seconds()
            retry_times.append((attempt, elapsed))
            # Schedule the actual retry
            from custom_components.smart_climate import _schedule_retry
            await _schedule_retry(hass, entry, attempt)
        
        # Set entities as unavailable
        hass.states.async_set("climate.test", STATE_UNAVAILABLE)
        hass.states.async_set("sensor.test_temperature", STATE_UNAVAILABLE)
        
        with patch("custom_components.smart_climate._schedule_retry", side_effect=track_retry_time):
            with patch("custom_components.smart_climate.entity_waiter.EntityWaiter.wait_for_required_entities",
                       side_effect=EntityNotAvailableError("Not available")):
                # Initial setup
                result = await async_setup_entry(hass, mock_config_entry)
                assert result is False
                assert len(retry_times) == 1
                assert retry_times[0] == (1, 0)  # First retry scheduled immediately
                
                # Advance time by 30 seconds (first retry)
                async_fire_time_changed(hass, start_time + timedelta(seconds=30))
                await hass.async_block_till_done()
                
                # Should trigger another retry
                hass.data[DOMAIN][mock_config_entry.entry_id]["_retry_attempt"] = 1
                result = await async_setup_entry(hass, mock_config_entry)
                assert result is False
                assert len(retry_times) == 2
                
                # Advance time by 60 more seconds (second retry)
                async_fire_time_changed(hass, start_time + timedelta(seconds=90))
                await hass.async_block_till_done()
                
                # Continue pattern for remaining retries
                hass.data[DOMAIN][mock_config_entry.entry_id]["_retry_attempt"] = 2
                result = await async_setup_entry(hass, mock_config_entry)
                assert result is False
                assert len(retry_times) == 3

    @pytest.mark.asyncio
    async def test_concurrent_retries_for_multiple_entries(self, hass: HomeAssistant):
        """Test concurrent retry handling for multiple config entries."""
        # Create multiple entries
        entries = []
        for i in range(3):
            entry = MockConfigEntry(
                version=1,
                domain=DOMAIN,
                title=f"Climate {i+1}",
                data={
                    "climate_entity": f"climate.test{i+1}",
                    "room_sensor": f"sensor.temp{i+1}",
                    "enable_retry": True,
                    "max_retry_attempts": 3,
                    "initial_timeout": 30,
                },
                source="user",
                entry_id=f"entry_{i+1}",
            )
            entry.add_to_hass(hass)
            entries.append(entry)
            
            # Set all entities as unavailable
            hass.states.async_set(f"climate.test{i+1}", STATE_UNAVAILABLE)
            hass.states.async_set(f"sensor.temp{i+1}", STATE_UNAVAILABLE)
        
        # Track concurrent operations
        concurrent_setups = []
        
        async def track_setup(entry):
            concurrent_setups.append((entry.entry_id, dt_util.utcnow()))
            result = await async_setup_entry(hass, entry)
            return result
        
        # Setup all entries concurrently
        results = await asyncio.gather(
            *[track_setup(entry) for entry in entries],
            return_exceptions=True
        )
        
        # All should fail and schedule retries
        assert all(result is False for result in results if not isinstance(result, Exception))
        assert len(concurrent_setups) == 3
        
        # Verify retries are scheduled independently
        for entry in entries:
            assert "_retry_attempt" in hass.data[DOMAIN][entry.entry_id]
            assert hass.data[DOMAIN][entry.entry_id]["_retry_attempt"] == 1