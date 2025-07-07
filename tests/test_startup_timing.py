"""ABOUTME: Test startup timing and entity availability checking.
Tests for EntityWaiter utility and startup timing improvements."""

import asyncio
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Add the project directory to the path to import custom components
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Mock HomeAssistant imports since we don't have HA installed for testing
class MockHomeAssistant:
    def __init__(self):
        self.states = Mock()

class MockHomeAssistantError(Exception):
    pass

# Mock the imports before importing our code
sys.modules['homeassistant'] = Mock()
sys.modules['homeassistant.core'] = Mock()
sys.modules['homeassistant.exceptions'] = Mock()
sys.modules['homeassistant.core'].HomeAssistant = MockHomeAssistant
sys.modules['homeassistant.exceptions'].HomeAssistantError = MockHomeAssistantError

# Import types after mocking is set up
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.smart_climate.entity_waiter import EntityWaiter, EntityNotAvailableError


class TestEntityWaiter:
    """Test EntityWaiter utility class."""

    def test_init(self):
        """Test EntityWaiter initialization."""
        waiter = EntityWaiter()
        assert waiter is not None

    @pytest.mark.asyncio
    async def test_wait_for_entity_success_immediate(self):
        """Test waiting for entity that is immediately available."""
        # Mock Home Assistant instance
        hass = MockHomeAssistant()
        
        # Mock entity state
        mock_state = Mock()
        mock_state.state = "on"
        hass.states.get = Mock(return_value=mock_state)
        
        waiter = EntityWaiter()
        result = await waiter.wait_for_entity(hass, "sensor.temperature", timeout=5)
        
        assert result is True
        hass.states.get.assert_called_once_with("sensor.temperature")

    @pytest.mark.asyncio
    async def test_wait_for_entity_success_after_delay(self, hass: HomeAssistant):
        """Test waiting for entity that becomes available after delay."""
        # First call returns None, second call returns state
        mock_state = Mock()
        mock_state.state = "on"
        hass.states.get = Mock(side_effect=[None, mock_state])
        
        waiter = EntityWaiter()
        
        # Mock sleep to avoid actual delays in tests
        with patch('custom_components.smart_climate.entity_waiter.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await waiter.wait_for_entity(hass, "sensor.temperature", timeout=5)
        
        assert result is True
        assert hass.states.get.call_count == 2
        mock_sleep.assert_called_once_with(1)  # First retry delay

    @pytest.mark.asyncio
    async def test_wait_for_entity_timeout(self, hass: HomeAssistant):
        """Test waiting for entity that never becomes available."""
        # Always return None (entity not available)
        hass.states.get = Mock(return_value=None)
        
        waiter = EntityWaiter()
        
        with patch('custom_components.smart_climate.entity_waiter.asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(EntityNotAvailableError) as exc_info:
                await waiter.wait_for_entity(hass, "sensor.missing", timeout=2)
        
        assert "sensor.missing" in str(exc_info.value)
        assert "not available after" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_wait_for_entity_unavailable_state(self, hass: HomeAssistant):
        """Test waiting for entity that has 'unavailable' state."""
        # Mock entity with unavailable state
        mock_state = Mock()
        mock_state.state = "unavailable"
        hass.states.get = Mock(return_value=mock_state)
        
        waiter = EntityWaiter()
        
        with patch('custom_components.smart_climate.entity_waiter.asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(EntityNotAvailableError):
                await waiter.wait_for_entity(hass, "sensor.unavailable", timeout=2)

    @pytest.mark.asyncio
    async def test_wait_for_entity_unknown_state(self, hass: HomeAssistant):
        """Test waiting for entity that has 'unknown' state."""
        # Mock entity with unknown state
        mock_state = Mock()
        mock_state.state = "unknown"
        hass.states.get = Mock(return_value=mock_state)
        
        waiter = EntityWaiter()
        
        with patch('custom_components.smart_climate.entity_waiter.asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(EntityNotAvailableError):
                await waiter.wait_for_entity(hass, "sensor.unknown", timeout=2)

    @pytest.mark.asyncio
    async def test_wait_for_entity_exponential_backoff(self, hass: HomeAssistant):
        """Test exponential backoff delays."""
        # Entity becomes available after 3 attempts
        mock_state = Mock()
        mock_state.state = "on"
        hass.states.get = Mock(side_effect=[None, None, mock_state])
        
        waiter = EntityWaiter()
        
        with patch('custom_components.smart_climate.entity_waiter.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await waiter.wait_for_entity(hass, "sensor.temperature", timeout=10)
        
        assert result is True
        assert hass.states.get.call_count == 3
        # Check exponential backoff: 1s, 2s
        expected_delays = [1, 2]
        actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
        assert actual_delays == expected_delays

    @pytest.mark.asyncio
    async def test_wait_for_entity_max_delay_cap(self, hass: HomeAssistant):
        """Test that delay is capped at maximum value."""
        # Entity becomes available after many attempts
        mock_state = Mock()
        mock_state.state = "on"
        hass.states.get = Mock(side_effect=[None] * 10 + [mock_state])
        
        waiter = EntityWaiter()
        
        with patch('custom_components.smart_climate.entity_waiter.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await waiter.wait_for_entity(hass, "sensor.temperature", timeout=120)
        
        assert result is True
        # Check that delays are capped at 16s (1, 2, 4, 8, 16, 16, 16, ...)
        actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
        assert all(delay <= 16 for delay in actual_delays)
        assert 16 in actual_delays  # At least one delay hit the cap

    @pytest.mark.asyncio
    async def test_wait_for_entities_all_available(self, hass: HomeAssistant):
        """Test waiting for multiple entities that are all available."""
        # Mock multiple entities
        mock_state = Mock()
        mock_state.state = "on"
        hass.states.get = Mock(return_value=mock_state)
        
        waiter = EntityWaiter()
        entity_ids = ["sensor.temperature", "climate.thermostat", "sensor.humidity"]
        
        result = await waiter.wait_for_entities(hass, entity_ids, timeout=5)
        
        assert result is True
        assert hass.states.get.call_count == len(entity_ids)

    @pytest.mark.asyncio
    async def test_wait_for_entities_partial_availability(self, hass: HomeAssistant):
        """Test waiting for multiple entities where some are not available."""
        # Mock first entity available, second not available
        mock_state = Mock()
        mock_state.state = "on"
        hass.states.get = Mock(side_effect=[mock_state, None, mock_state])
        
        waiter = EntityWaiter()
        entity_ids = ["sensor.temperature", "climate.missing", "sensor.humidity"]
        
        with patch('custom_components.smart_climate.entity_waiter.asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(EntityNotAvailableError) as exc_info:
                await waiter.wait_for_entities(hass, entity_ids, timeout=2)
        
        assert "climate.missing" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_wait_for_entities_empty_list(self, hass: HomeAssistant):
        """Test waiting for empty list of entities."""
        waiter = EntityWaiter()
        
        result = await waiter.wait_for_entities(hass, [], timeout=5)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_entities_gradual_availability(self, hass: HomeAssistant):
        """Test entities becoming available at different times."""
        # First entity available immediately, second becomes available after delay
        mock_state = Mock()
        mock_state.state = "on"
        
        def mock_get_state(entity_id):
            if entity_id == "sensor.temperature":
                return mock_state
            elif entity_id == "climate.thermostat":
                # Return None first few times, then available
                if mock_get_state.call_count <= 3:
                    return None
                return mock_state
            return None
        
        mock_get_state.call_count = 0
        
        def side_effect(entity_id):
            mock_get_state.call_count += 1
            return mock_get_state(entity_id)
        
        hass.states.get = Mock(side_effect=side_effect)
        
        waiter = EntityWaiter()
        entity_ids = ["sensor.temperature", "climate.thermostat"]
        
        with patch('custom_components.smart_climate.entity_waiter.asyncio.sleep', new_callable=AsyncMock):
            result = await waiter.wait_for_entities(hass, entity_ids, timeout=10)
        
        assert result is True


class TestStartupTiming:
    """Test startup timing improvements in __init__.py."""

    @pytest.mark.asyncio
    async def test_setup_entry_waits_for_entities(self, hass: HomeAssistant):
        """Test that async_setup_entry waits for entities before proceeding."""
        # Mock config entry
        config_entry = Mock()
        config_entry.data = {
            "climate_entity": "climate.thermostat",
            "room_sensor": "sensor.temperature",
            "outdoor_sensor": "sensor.outdoor_temp",
            "power_sensor": "sensor.power"
        }
        
        # Mock entities as available
        mock_state = Mock()
        mock_state.state = "on"
        hass.states.get = Mock(return_value=mock_state)
        
        # Mock the climate platform setup
        with patch('custom_components.smart_climate.async_forward_entry_setups', new_callable=AsyncMock) as mock_forward:
            from custom_components.smart_climate import async_setup_entry
            
            result = await async_setup_entry(hass, config_entry)
        
        assert result is True
        # Should have checked for required entities
        expected_entities = ["climate.thermostat", "sensor.temperature"]
        assert hass.states.get.call_count >= len(expected_entities)
        mock_forward.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_entry_entity_wait_failure(self, hass: HomeAssistant):
        """Test setup failure when entities are not available."""
        # Mock config entry
        config_entry = Mock()
        config_entry.data = {
            "climate_entity": "climate.missing",
            "room_sensor": "sensor.temperature",
        }
        
        # Mock entities as not available
        hass.states.get = Mock(return_value=None)
        
        with patch('custom_components.smart_climate.entity_waiter.asyncio.sleep', new_callable=AsyncMock):
            from custom_components.smart_climate import async_setup_entry
            
            with pytest.raises(HomeAssistantError) as exc_info:
                await async_setup_entry(hass, config_entry)
        
        assert "Required entities not available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_setup_entry_optional_entities(self, hass: HomeAssistant):
        """Test setup succeeds with only required entities available."""
        # Mock config entry with optional entities
        config_entry = Mock()
        config_entry.data = {
            "climate_entity": "climate.thermostat",
            "room_sensor": "sensor.temperature",
            "outdoor_sensor": "sensor.missing_outdoor",  # Optional
            "power_sensor": "sensor.missing_power"       # Optional
        }
        
        # Mock only required entities as available
        def mock_get_state(entity_id):
            if entity_id in ["climate.thermostat", "sensor.temperature"]:
                mock_state = Mock()
                mock_state.state = "on"
                return mock_state
            return None  # Optional entities not available
        
        hass.states.get = Mock(side_effect=mock_get_state)
        
        # Mock the climate platform setup
        with patch('custom_components.smart_climate.async_forward_entry_setups', new_callable=AsyncMock) as mock_forward:
            from custom_components.smart_climate import async_setup_entry
            
            result = await async_setup_entry(hass, config_entry)
        
        assert result is True
        mock_forward.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_entry_with_retry_success(self, hass: HomeAssistant):
        """Test setup succeeds after entities become available with retry."""
        # Mock config entry
        config_entry = Mock()
        config_entry.data = {
            "climate_entity": "climate.thermostat",
            "room_sensor": "sensor.temperature",
        }
        
        # Mock entities becoming available after delay
        mock_state = Mock()
        mock_state.state = "on"
        hass.states.get = Mock(side_effect=[None, mock_state, mock_state])
        
        # Mock the climate platform setup
        with patch('custom_components.smart_climate.async_forward_entry_setups', new_callable=AsyncMock) as mock_forward:
            with patch('custom_components.smart_climate.entity_waiter.asyncio.sleep', new_callable=AsyncMock):
                from custom_components.smart_climate import async_setup_entry
                
                result = await async_setup_entry(hass, config_entry)
        
        assert result is True
        mock_forward.assert_called_once()