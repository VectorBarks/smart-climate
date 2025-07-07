"""ABOUTME: Simple test for startup timing functionality.
Basic tests to verify EntityWaiter works correctly without complex HA dependencies."""

import asyncio
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Add the project directory to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Mock basic HA classes
class MockState:
    def __init__(self, state="on"):
        self.state = state

class MockStates:
    def __init__(self):
        self._states = {}
    
    def get(self, entity_id):
        return self._states.get(entity_id)
    
    def set_state(self, entity_id, state_obj):
        self._states[entity_id] = state_obj

class MockHass:
    def __init__(self):
        self.states = MockStates()

# Mock the homeassistant modules
sys.modules['homeassistant'] = Mock()
sys.modules['homeassistant.core'] = Mock()

from custom_components.smart_climate.entity_waiter import EntityWaiter, EntityNotAvailableError


class TestEntityWaiterBasic:
    """Basic tests for EntityWaiter functionality."""

    def test_init(self):
        """Test EntityWaiter can be created."""
        waiter = EntityWaiter()
        assert waiter is not None

    @pytest.mark.asyncio
    async def test_entity_available_immediately(self):
        """Test entity that is available immediately."""
        hass = MockHass()
        hass.states.set_state("sensor.test", MockState("on"))
        
        waiter = EntityWaiter()
        result = await waiter.wait_for_entity(hass, "sensor.test", timeout=1)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_entity_not_available(self):
        """Test entity that is never available."""
        hass = MockHass()
        # Don't set any state - entity will be None
        
        waiter = EntityWaiter()
        
        with patch('custom_components.smart_climate.entity_waiter.asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(EntityNotAvailableError):
                await waiter.wait_for_entity(hass, "sensor.missing", timeout=1)

    @pytest.mark.asyncio
    async def test_entity_unavailable_state(self):
        """Test entity with unavailable state."""
        hass = MockHass()
        hass.states.set_state("sensor.unavailable", MockState("unavailable"))
        
        waiter = EntityWaiter()
        
        with patch('custom_components.smart_climate.entity_waiter.asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(EntityNotAvailableError):
                await waiter.wait_for_entity(hass, "sensor.unavailable", timeout=1)

    @pytest.mark.asyncio
    async def test_entity_unknown_state(self):
        """Test entity with unknown state."""
        hass = MockHass()
        hass.states.set_state("sensor.unknown", MockState("unknown"))
        
        waiter = EntityWaiter()
        
        with patch('custom_components.smart_climate.entity_waiter.asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(EntityNotAvailableError):
                await waiter.wait_for_entity(hass, "sensor.unknown", timeout=1)

    @pytest.mark.asyncio 
    async def test_wait_for_multiple_entities_success(self):
        """Test waiting for multiple entities that are all available."""
        hass = MockHass()
        hass.states.set_state("sensor.temp", MockState("on"))
        hass.states.set_state("climate.ac", MockState("cool"))
        
        waiter = EntityWaiter()
        entity_ids = ["sensor.temp", "climate.ac"]
        
        result = await waiter.wait_for_entities(hass, entity_ids, timeout=5)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_multiple_entities_failure(self):
        """Test waiting for multiple entities where one is missing."""
        hass = MockHass()
        hass.states.set_state("sensor.temp", MockState("on"))
        # climate.missing is not set - will be None
        
        waiter = EntityWaiter()
        entity_ids = ["sensor.temp", "climate.missing"]
        
        with patch('custom_components.smart_climate.entity_waiter.asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(EntityNotAvailableError) as exc_info:
                await waiter.wait_for_entities(hass, entity_ids, timeout=1)
        
        assert "climate.missing" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_wait_for_required_entities_from_config(self):
        """Test waiting for required entities from config dictionary."""
        hass = MockHass()
        hass.states.set_state("climate.thermostat", MockState("heat"))
        hass.states.set_state("sensor.room_temp", MockState("20.5"))
        
        config = {
            "climate_entity": "climate.thermostat",
            "room_sensor": "sensor.room_temp",
            "outdoor_sensor": "sensor.outdoor",  # Optional - missing is OK
            "power_sensor": "sensor.power"       # Optional - missing is OK
        }
        
        waiter = EntityWaiter()
        result = await waiter.wait_for_required_entities(hass, config, timeout=5)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_required_entities_missing_required(self):
        """Test failure when required entity is missing."""
        hass = MockHass()
        hass.states.set_state("sensor.room_temp", MockState("20.5"))
        # climate.thermostat is missing
        
        config = {
            "climate_entity": "climate.thermostat",  # Required but missing
            "room_sensor": "sensor.room_temp",       # Required and available
        }
        
        waiter = EntityWaiter()
        
        with patch('custom_components.smart_climate.entity_waiter.asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(EntityNotAvailableError) as exc_info:
                await waiter.wait_for_required_entities(hass, config, timeout=1)
        
        assert "climate.thermostat" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_exponential_backoff_delays(self):
        """Test that exponential backoff works correctly."""
        hass = MockHass()
        # Entity becomes available after 3 attempts
        
        call_count = 0
        def mock_get_with_delay(entity_id):
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                return MockState("on")
            return None
        
        hass.states.get = mock_get_with_delay
        
        waiter = EntityWaiter()
        
        with patch('custom_components.smart_climate.entity_waiter.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await waiter.wait_for_entity(hass, "sensor.delayed", timeout=10)
        
        assert result is True
        assert call_count == 3
        
        # Check exponential backoff: should have 1s, 2s delays
        expected_delays = [1, 2]
        actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
        assert actual_delays == expected_delays


class TestStartupTimingIntegration:
    """Test integration with startup timing fixes."""

    @pytest.mark.asyncio
    async def test_entity_waiter_in_startup_flow(self):
        """Test that EntityWaiter can be used in startup flow."""
        hass = MockHass()
        hass.states.set_state("climate.test", MockState("heat"))
        hass.states.set_state("sensor.temp", MockState("21.0"))
        
        config = {
            "climate_entity": "climate.test",
            "room_sensor": "sensor.temp"
        }
        
        # Simulate the startup flow
        waiter = EntityWaiter()
        
        # This should succeed without exceptions
        result = await waiter.wait_for_required_entities(hass, config, timeout=5)
        assert result is True

    def test_import_works(self):
        """Test that the module can be imported successfully."""
        from custom_components.smart_climate.entity_waiter import EntityWaiter, EntityNotAvailableError
        
        # Should be able to create instance
        waiter = EntityWaiter()
        assert waiter is not None
        
        # Exception should be available
        assert EntityNotAvailableError is not None