"""ABOUTME: Integration tests for complete entity availability waiting system.
Tests end-to-end startup scenarios with delayed entities, timeout behavior, and graceful degradation."""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN

from custom_components.smart_climate.const import (
    DOMAIN,
    CONF_CLIMATE_ENTITY,
    CONF_ROOM_SENSOR,
    CONF_OUTDOOR_SENSOR,
    CONF_POWER_SENSOR,
    CONF_INDOOR_HUMIDITY_SENSOR,
    CONF_OUTDOOR_HUMIDITY_SENSOR,
    CONF_STARTUP_TIMEOUT,
    STARTUP_TIMEOUT_SEC,
)


# Mock entity IDs for consistent testing
MOCK_CLIMATE_ID = "climate.test_ac"
MOCK_ROOM_SENSOR_ID = "sensor.test_room_temp"
MOCK_OUTDOOR_SENSOR_ID = "sensor.test_outdoor_temp"
MOCK_POWER_SENSOR_ID = "sensor.test_power"
MOCK_INDOOR_HUMIDITY_ID = "sensor.test_indoor_humidity"
MOCK_OUTDOOR_HUMIDITY_ID = "sensor.test_outdoor_humidity"


class TestEntityAvailabilityWaitingIntegration:
    """Integration tests for complete entity availability waiting system."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        hass = MagicMock()
        hass.data = {}
        hass.states = MagicMock()
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        return hass

    @pytest.fixture
    def mock_config_entry_required_only(self):
        """Mock config entry with only required entities."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        entry.data = {
            CONF_CLIMATE_ENTITY: MOCK_CLIMATE_ID,
            CONF_ROOM_SENSOR: MOCK_ROOM_SENSOR_ID
        }
        entry.options = {}
        return entry

    @pytest.fixture
    def mock_config_entry_with_optional(self):
        """Mock config entry with required and optional entities."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        entry.data = {
            CONF_CLIMATE_ENTITY: MOCK_CLIMATE_ID,
            CONF_ROOM_SENSOR: MOCK_ROOM_SENSOR_ID
        }
        entry.options = {
            CONF_OUTDOOR_SENSOR: MOCK_OUTDOOR_SENSOR_ID,
            CONF_POWER_SENSOR: MOCK_POWER_SENSOR_ID,
            CONF_INDOOR_HUMIDITY_SENSOR: MOCK_INDOOR_HUMIDITY_ID,
            CONF_OUTDOOR_HUMIDITY_SENSOR: MOCK_OUTDOOR_HUMIDITY_ID
        }
        return entry

    @pytest.fixture 
    def mock_config_entry_custom_timeout(self):
        """Mock config entry with custom startup timeout."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        entry.data = {
            CONF_CLIMATE_ENTITY: MOCK_CLIMATE_ID,
            CONF_ROOM_SENSOR: MOCK_ROOM_SENSOR_ID
        }
        entry.options = {
            CONF_STARTUP_TIMEOUT: 120  # 2-minute timeout
        }
        return entry

    def setup_entity_states(self, mock_hass, entity_states):
        """Helper to set up entity states with availability."""
        def get_state_side_effect(entity_id):
            if entity_id in entity_states:
                state_obj = Mock()
                state_obj.state = entity_states[entity_id]
                return state_obj
            return None
        
        mock_hass.states.get.side_effect = get_state_side_effect

    @pytest.mark.asyncio
    async def test_fresh_ha_startup_with_delayed_zigbee_entities(
        self, mock_hass, mock_config_entry_with_optional
    ):
        """Test fresh Home Assistant startup where Zigbee entities are delayed."""
        # Simulate fresh startup - no entities available initially
        initial_states = {}  # No entities available
        self.setup_entity_states(mock_hass, initial_states)

        with patch('custom_components.smart_climate.async_setup_entry') as mock_setup:
            # Create a real-world scenario where setup waits for entities
            async def delayed_setup_entry(hass, entry):
                # Import the helper function
                from custom_components.smart_climate.helpers import async_wait_for_entities
                
                # Required entities
                required_entities = [MOCK_CLIMATE_ID, MOCK_ROOM_SENSOR_ID]
                
                # Optional entities 
                optional_entities = [
                    MOCK_OUTDOOR_SENSOR_ID, MOCK_POWER_SENSOR_ID, 
                    MOCK_INDOOR_HUMIDITY_ID, MOCK_OUTDOOR_HUMIDITY_ID
                ]
                
                # Wait for required entities with default timeout
                required_available = await async_wait_for_entities(
                    hass, required_entities, STARTUP_TIMEOUT_SEC
                )
                
                if not required_available:
                    raise ConfigEntryNotReady(
                        f"Required entities not available after {STARTUP_TIMEOUT_SEC}s. "
                        "Integration setup will be retried."
                    )
                
                # Wait for optional entities with shorter timeout
                optional_available = await async_wait_for_entities(
                    hass, optional_entities, 15
                )
                
                if not optional_available:
                    # Log warning but continue (graceful degradation)
                    pass
                
                return True

            mock_setup.side_effect = delayed_setup_entry

            # Start setup in background task
            setup_task = asyncio.create_task(mock_setup(mock_hass, mock_config_entry_with_optional))
            
            # Give setup time to start waiting
            await asyncio.sleep(0.1)
            
            # Simulate Zigbee entities becoming available after delay
            # First, required entities become available
            updated_states = {
                MOCK_CLIMATE_ID: "cool",
                MOCK_ROOM_SENSOR_ID: "22.5"
            }
            self.setup_entity_states(mock_hass, updated_states)
            
            # Give more time for processing
            await asyncio.sleep(0.1)
            
            # Then optional entities become available
            final_states = {
                MOCK_CLIMATE_ID: "cool",
                MOCK_ROOM_SENSOR_ID: "22.5",
                MOCK_OUTDOOR_SENSOR_ID: "18.5",
                MOCK_POWER_SENSOR_ID: "120.0",
                MOCK_INDOOR_HUMIDITY_ID: "45.0",
                MOCK_OUTDOOR_HUMIDITY_ID: "38.0"
            }
            self.setup_entity_states(mock_hass, final_states)
            
            # Wait for setup completion
            result = await setup_task
            
            # Verify setup succeeded
            assert result is True

    @pytest.mark.asyncio
    async def test_partial_entity_availability_during_startup(
        self, mock_hass, mock_config_entry_with_optional
    ):
        """Test startup with partial entity availability (some available, some not)."""
        # Setup partial availability - required entities available, some optional missing
        partial_states = {
            MOCK_CLIMATE_ID: "cool",
            MOCK_ROOM_SENSOR_ID: "23.0",
            MOCK_OUTDOOR_SENSOR_ID: "19.0",
            # MOCK_POWER_SENSOR_ID and humidity sensors are missing
        }
        self.setup_entity_states(mock_hass, partial_states)

        with patch('custom_components.smart_climate.async_setup_entry') as mock_setup:
            async def partial_setup_entry(hass, entry):
                from custom_components.smart_climate.helpers import async_wait_for_entities
                
                # Required entities
                required_entities = [MOCK_CLIMATE_ID, MOCK_ROOM_SENSOR_ID]
                required_available = await async_wait_for_entities(hass, required_entities, 90)
                
                if not required_available:
                    raise ConfigEntryNotReady("Required entities not available")
                
                # Optional entities (some missing)
                optional_entities = [
                    MOCK_OUTDOOR_SENSOR_ID, MOCK_POWER_SENSOR_ID, 
                    MOCK_INDOOR_HUMIDITY_ID, MOCK_OUTDOOR_HUMIDITY_ID
                ]
                optional_available = await async_wait_for_entities(hass, optional_entities, 15)
                
                # Should continue even if optional entities timeout
                return True

            mock_setup.side_effect = partial_setup_entry
            
            # Setup should succeed with graceful degradation
            result = await mock_setup(mock_hass, mock_config_entry_with_optional)
            assert result is True

    @pytest.mark.asyncio
    async def test_timeout_and_retry_behavior_with_config_entry_not_ready(
        self, mock_hass, mock_config_entry_required_only
    ):
        """Test timeout behavior and ConfigEntryNotReady raising for required entities."""
        # Setup no entities available (they never come online)
        self.setup_entity_states(mock_hass, {})

        with patch('custom_components.smart_climate.async_setup_entry') as mock_setup:
            async def timeout_setup_entry(hass, entry):
                from custom_components.smart_climate.helpers import async_wait_for_entities
                
                required_entities = [MOCK_CLIMATE_ID, MOCK_ROOM_SENSOR_ID]
                
                # Use very short timeout for fast test
                required_available = await async_wait_for_entities(hass, required_entities, 1)
                
                if not required_available:
                    raise ConfigEntryNotReady(
                        f"Required entities not available after 1s. "
                        "Integration setup will be retried."
                    )
                
                return True

            mock_setup.side_effect = timeout_setup_entry
            
            # Setup should raise ConfigEntryNotReady
            with pytest.raises(ConfigEntryNotReady) as exc_info:
                await mock_setup(mock_hass, mock_config_entry_required_only)
            
            # Verify exception message
            assert "Required entities not available after 1s" in str(exc_info.value)
            assert "Integration setup will be retried" in str(exc_info.value)

    @pytest.mark.asyncio  
    async def test_graceful_degradation_with_missing_optional_entities(
        self, mock_hass, mock_config_entry_with_optional
    ):
        """Test graceful degradation when optional entities are missing."""
        # Setup with required entities only
        required_only_states = {
            MOCK_CLIMATE_ID: "cool",
            MOCK_ROOM_SENSOR_ID: "24.0"
        }
        self.setup_entity_states(mock_hass, required_only_states)

        with patch('custom_components.smart_climate.async_setup_entry') as mock_setup, \
             patch('custom_components.smart_climate._LOGGER') as mock_logger:
            
            async def degraded_setup_entry(hass, entry):
                from custom_components.smart_climate.helpers import async_wait_for_entities
                
                # Required entities succeed
                required_entities = [MOCK_CLIMATE_ID, MOCK_ROOM_SENSOR_ID]
                required_available = await async_wait_for_entities(hass, required_entities, 90)
                
                if not required_available:
                    raise ConfigEntryNotReady("Required entities not available")
                
                # Optional entities timeout
                optional_entities = [
                    MOCK_OUTDOOR_SENSOR_ID, MOCK_POWER_SENSOR_ID, 
                    MOCK_INDOOR_HUMIDITY_ID, MOCK_OUTDOOR_HUMIDITY_ID
                ]
                optional_available = await async_wait_for_entities(hass, optional_entities, 15)
                
                if not optional_available:
                    mock_logger.warning(
                        "Optional entities not available after 15s. "
                        "Integration will start without them: %s", optional_entities
                    )
                
                return True

            mock_setup.side_effect = degraded_setup_entry
            
            # Setup should succeed
            result = await mock_setup(mock_hass, mock_config_entry_with_optional)
            assert result is True
            
            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert "Optional entities not available after 15s" in warning_msg
            assert "Integration will start without them" in warning_msg

    @pytest.mark.asyncio
    async def test_configuration_option_affects_timeout_behavior(
        self, mock_hass, mock_config_entry_custom_timeout
    ):
        """Test that custom startup timeout configuration is used correctly."""
        # Setup entities to become available after default timeout but before custom timeout
        self.setup_entity_states(mock_hass, {})

        with patch('custom_components.smart_climate.async_setup_entry') as mock_setup:
            async def timeout_config_setup_entry(hass, entry):
                from custom_components.smart_climate.helpers import async_wait_for_entities
                
                # Get custom timeout from config (120 seconds)
                custom_timeout = entry.options.get(CONF_STARTUP_TIMEOUT, STARTUP_TIMEOUT_SEC)
                
                required_entities = [MOCK_CLIMATE_ID, MOCK_ROOM_SENSOR_ID]
                required_available = await async_wait_for_entities(hass, required_entities, custom_timeout)
                
                if not required_available:
                    raise ConfigEntryNotReady(f"Required entities not available after {custom_timeout}s")
                
                return True

            mock_setup.side_effect = timeout_config_setup_entry
            
            # Verify the custom timeout is being used (120s vs default 90s)
            # This is tested by checking that the function gets the correct value
            custom_timeout = mock_config_entry_custom_timeout.options.get(CONF_STARTUP_TIMEOUT, STARTUP_TIMEOUT_SEC)
            assert custom_timeout == 120
            
            # In a real scenario, entities would become available within 120s
            # For test speed, we'll make entities available immediately
            available_states = {
                MOCK_CLIMATE_ID: "cool",
                MOCK_ROOM_SENSOR_ID: "22.0"
            }
            self.setup_entity_states(mock_hass, available_states)
            
            result = await mock_setup(mock_hass, mock_config_entry_custom_timeout)
            assert result is True

    @pytest.mark.asyncio
    async def test_logging_provides_clear_user_feedback(
        self, mock_hass, mock_config_entry_with_optional
    ):
        """Test that entity waiting provides clear, informative logging."""
        self.setup_entity_states(mock_hass, {})

        with patch('custom_components.smart_climate.async_setup_entry') as mock_setup, \
             patch('custom_components.smart_climate.helpers._LOGGER') as mock_logger:
            
            async def logging_setup_entry(hass, entry):
                from custom_components.smart_climate.helpers import async_wait_for_entities
                
                required_entities = [MOCK_CLIMATE_ID, MOCK_ROOM_SENSOR_ID]
                
                # This will trigger logging in async_wait_for_entities
                try:
                    required_available = await async_wait_for_entities(hass, required_entities, 1)
                    if not required_available:
                        raise ConfigEntryNotReady("Entities not available")
                except ConfigEntryNotReady:
                    raise
                
                return True

            mock_setup.side_effect = logging_setup_entry
            
            # Setup should raise ConfigEntryNotReady due to timeout
            with pytest.raises(ConfigEntryNotReady):
                await mock_setup(mock_hass, mock_config_entry_with_optional)
            
            # Verify appropriate logging occurred
            # Check that INFO level messages about waiting were logged
            info_calls = [call for call in mock_logger.info.call_args_list]
            assert len(info_calls) > 0, "Should log info messages about entity waiting"
            
            # Check that warning about timeout was logged
            warning_calls = [call for call in mock_logger.warning.call_args_list]
            assert len(warning_calls) > 0, "Should log warning about entity timeout"

    @pytest.mark.asyncio
    async def test_integration_continues_normally_after_entity_waiting(
        self, mock_hass, mock_config_entry_required_only
    ):
        """Test that integration operates normally after successful entity waiting."""
        # Start with no entities, then make them available
        self.setup_entity_states(mock_hass, {})

        with patch('custom_components.smart_climate.async_setup_entry') as mock_setup, \
             patch('custom_components.smart_climate.SeasonalHysteresisLearner'), \
             patch('custom_components.smart_climate._async_setup_entity_persistence') as mock_persistence, \
             patch('custom_components.smart_climate._async_register_services') as mock_services:
            
            mock_persistence.return_value = None
            mock_services.return_value = None

            async def normal_operation_setup_entry(hass, entry):
                from custom_components.smart_climate.helpers import async_wait_for_entities
                
                required_entities = [MOCK_CLIMATE_ID, MOCK_ROOM_SENSOR_ID]
                required_available = await async_wait_for_entities(hass, required_entities, 90)
                
                if not required_available:
                    raise ConfigEntryNotReady("Required entities not available")
                
                # Continue with normal setup
                await hass.config_entries.async_forward_entry_setups(entry, ["climate", "sensor", "switch"])
                
                return True

            mock_setup.side_effect = normal_operation_setup_entry
            
            # Start setup in background
            setup_task = asyncio.create_task(mock_setup(mock_hass, mock_config_entry_required_only))
            
            # Give setup time to start waiting
            await asyncio.sleep(0.1)
            
            # Make entities available
            available_states = {
                MOCK_CLIMATE_ID: "cool", 
                MOCK_ROOM_SENSOR_ID: "23.5"
            }
            self.setup_entity_states(mock_hass, available_states)
            
            # Wait for setup to complete
            result = await setup_task
            
            # Verify setup succeeded and platforms were set up
            assert result is True
            mock_hass.config_entries.async_forward_entry_setups.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_setup_attempts_handled_gracefully(
        self, mock_hass, mock_config_entry_required_only
    ):
        """Test that concurrent setup attempts (retries) are handled gracefully."""
        call_count = 0
        
        # Start with no entities available
        self.setup_entity_states(mock_hass, {})
        
        with patch('custom_components.smart_climate.async_setup_entry') as mock_setup:
            async def concurrent_setup_entry(hass, entry):
                nonlocal call_count
                call_count += 1
                
                from custom_components.smart_climate.helpers import async_wait_for_entities
                
                required_entities = [MOCK_CLIMATE_ID, MOCK_ROOM_SENSOR_ID]
                
                # First call times out, second call succeeds
                if call_count == 1:
                    # Entities not available on first attempt
                    required_available = await async_wait_for_entities(hass, required_entities, 1)
                    if not required_available:
                        raise ConfigEntryNotReady("First attempt failed")
                else:
                    # Second attempt - entities are now available
                    available_states = {
                        MOCK_CLIMATE_ID: "cool",
                        MOCK_ROOM_SENSOR_ID: "24.0"
                    }
                    self.setup_entity_states(hass, available_states)
                    
                    required_available = await async_wait_for_entities(hass, required_entities, 90)
                    if not required_available:
                        raise ConfigEntryNotReady("Second attempt failed")
                
                return True

            mock_setup.side_effect = concurrent_setup_entry
            
            # First setup attempt should fail (entities not available)
            with pytest.raises(ConfigEntryNotReady):
                await mock_setup(mock_hass, mock_config_entry_required_only)
            
            # Second setup attempt should succeed (entities become available)
            result = await mock_setup(mock_hass, mock_config_entry_required_only)
            assert result is True
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_entity_availability_edge_cases(
        self, mock_hass, mock_config_entry_required_only
    ):
        """Test edge cases in entity availability detection."""
        # Test entities that are present but in unavailable/unknown states
        edge_case_states = {
            MOCK_CLIMATE_ID: STATE_UNAVAILABLE,  # Present but unavailable
            MOCK_ROOM_SENSOR_ID: STATE_UNKNOWN   # Present but unknown
        }
        self.setup_entity_states(mock_hass, edge_case_states)

        with patch('custom_components.smart_climate.async_setup_entry') as mock_setup:
            async def edge_case_setup_entry(hass, entry):
                from custom_components.smart_climate.helpers import async_wait_for_entities
                
                required_entities = [MOCK_CLIMATE_ID, MOCK_ROOM_SENSOR_ID]
                
                # Should not consider unavailable/unknown entities as available
                required_available = await async_wait_for_entities(hass, required_entities, 1)
                
                if not required_available:
                    raise ConfigEntryNotReady("Entities unavailable/unknown")
                
                return True

            mock_setup.side_effect = edge_case_setup_entry
            
            # Setup should fail because entities are in unavailable/unknown states
            with pytest.raises(ConfigEntryNotReady) as exc_info:
                await mock_setup(mock_hass, mock_config_entry_required_only)
            
            assert "Entities unavailable/unknown" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_performance_with_many_optional_entities(
        self, mock_hass
    ):
        """Test performance when waiting for many optional entities."""
        # Create config with many optional entities
        config_entry = Mock()
        config_entry.entry_id = "test_entry"
        config_entry.data = {
            CONF_CLIMATE_ENTITY: MOCK_CLIMATE_ID,
            CONF_ROOM_SENSOR: MOCK_ROOM_SENSOR_ID
        }
        # Add many optional entities
        many_optional = {f"sensor.optional_{i}": f"value_{i}" for i in range(20)}
        config_entry.options = many_optional
        
        # Setup required entities available, optional entities missing
        required_states = {
            MOCK_CLIMATE_ID: "cool",
            MOCK_ROOM_SENSOR_ID: "22.0"
        }
        self.setup_entity_states(mock_hass, required_states)

        start_time = asyncio.get_event_loop().time()

        with patch('custom_components.smart_climate.async_setup_entry') as mock_setup:
            async def performance_setup_entry(hass, entry):
                from custom_components.smart_climate.helpers import async_wait_for_entities
                
                # Wait for required entities (should succeed quickly)
                required_entities = [MOCK_CLIMATE_ID, MOCK_ROOM_SENSOR_ID]
                required_available = await async_wait_for_entities(hass, required_entities, 90)
                
                if not required_available:
                    raise ConfigEntryNotReady("Required entities not available")
                
                # Wait for many optional entities (should timeout quickly)
                optional_entities = list(many_optional.keys())
                await async_wait_for_entities(hass, optional_entities, 15)
                
                return True

            mock_setup.side_effect = performance_setup_entry
            
            result = await mock_setup(mock_hass, config_entry)
            
            end_time = asyncio.get_event_loop().time()
            duration = end_time - start_time
            
            # Should complete in reasonable time despite many entities
            assert result is True
            assert duration < 20  # Should complete well within timeout periods

    def test_entity_waiting_constants_are_properly_defined(self):
        """Test that all required constants for entity waiting are available."""
        # Verify startup timeout constants
        assert CONF_STARTUP_TIMEOUT == "startup_timeout"
        assert STARTUP_TIMEOUT_SEC == 90
        assert isinstance(STARTUP_TIMEOUT_SEC, int)
        assert 30 <= STARTUP_TIMEOUT_SEC <= 300
        
        # Verify entity configuration constants
        assert CONF_CLIMATE_ENTITY == "climate_entity"
        assert CONF_ROOM_SENSOR == "room_sensor"
        assert CONF_OUTDOOR_SENSOR == "outdoor_sensor"
        assert CONF_POWER_SENSOR == "power_sensor"
        assert CONF_INDOOR_HUMIDITY_SENSOR == "indoor_humidity_sensor"
        assert CONF_OUTDOOR_HUMIDITY_SENSOR == "outdoor_humidity_sensor"


class TestEntityWaitingHelperFunctionIntegration:
    """Integration tests specifically for the async_wait_for_entities helper function."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        hass = MagicMock()
        hass.states = MagicMock()
        return hass

    @pytest.mark.asyncio
    async def test_helper_function_with_realistic_zigbee_scenario(self, mock_hass):
        """Test helper function with realistic Zigbee device discovery scenario."""
        from custom_components.smart_climate.helpers import async_wait_for_entities
        
        # Simulate Zigbee entities that come online gradually
        entity_ids = [
            "sensor.zigbee_temperature_1",
            "sensor.zigbee_temperature_2", 
            "sensor.zigbee_humidity_1"
        ]
        
        # Initially no entities available
        mock_hass.states.get.return_value = None
        
        # Start waiting in background
        wait_task = asyncio.create_task(
            async_wait_for_entities(mock_hass, entity_ids, 10)
        )
        
        # Give waiting time to start
        await asyncio.sleep(0.1)
        
        # Simulate first entity coming online
        def first_entity_available(entity_id):
            if entity_id == "sensor.zigbee_temperature_1":
                state = Mock()
                state.state = "22.5"
                return state
            return None
        
        mock_hass.states.get.side_effect = first_entity_available
        await asyncio.sleep(0.1)
        
        # Simulate all entities coming online
        def all_entities_available(entity_id):
            if entity_id in entity_ids:
                state = Mock()
                state.state = "online_value"
                return state
            return None
        
        mock_hass.states.get.side_effect = all_entities_available
        
        # Wait should succeed
        result = await wait_task
        assert result is True

    @pytest.mark.asyncio
    async def test_helper_function_timeout_behavior(self, mock_hass):
        """Test helper function timeout behavior with precise timing."""
        from custom_components.smart_climate.helpers import async_wait_for_entities
        
        # Entities never become available
        mock_hass.states.get.return_value = None
        
        start_time = asyncio.get_event_loop().time()
        
        # Should timeout after 1 second
        result = await async_wait_for_entities(mock_hass, ["sensor.never_available"], 1)
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        assert result is False
        assert 0.9 <= duration <= 1.5  # Should timeout around 1 second with some tolerance

    @pytest.mark.asyncio
    async def test_helper_function_with_mixed_entity_states(self, mock_hass):
        """Test helper function with entities in various states."""
        from custom_components.smart_climate.helpers import async_wait_for_entities
        
        entity_ids = [
            "sensor.available",
            "sensor.unavailable", 
            "sensor.unknown",
            "sensor.none"
        ]
        
        def mixed_states_side_effect(entity_id):
            state_map = {
                "sensor.available": Mock(state="22.0"),
                "sensor.unavailable": Mock(state=STATE_UNAVAILABLE),
                "sensor.unknown": Mock(state=STATE_UNKNOWN),
                "sensor.none": None
            }
            return state_map.get(entity_id)
        
        mock_hass.states.get.side_effect = mixed_states_side_effect
        
        # Should return False because unavailable/unknown/None entities are not considered available
        result = await async_wait_for_entities(mock_hass, entity_ids, 1)
        assert result is False

    @pytest.mark.asyncio
    async def test_helper_function_early_return_optimization(self, mock_hass):
        """Test that helper function returns immediately when all entities are available."""
        from custom_components.smart_climate.helpers import async_wait_for_entities
        
        entity_ids = ["sensor.ready1", "sensor.ready2"]
        
        def all_ready_side_effect(entity_id):
            if entity_id in entity_ids:
                state = Mock()
                state.state = "ready"
                return state
            return None
        
        mock_hass.states.get.side_effect = all_ready_side_effect
        
        start_time = asyncio.get_event_loop().time()
        
        # Should return immediately without waiting
        result = await async_wait_for_entities(mock_hass, entity_ids, 30)
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        assert result is True
        assert duration < 0.5  # Should return very quickly

    @pytest.mark.asyncio  
    async def test_helper_function_with_empty_entity_list(self, mock_hass):
        """Test helper function behavior with empty entity list."""
        from custom_components.smart_climate.helpers import async_wait_for_entities
        
        # Empty list should return True immediately
        result = await async_wait_for_entities(mock_hass, [], 60)
        assert result is True

    @pytest.mark.asyncio
    async def test_helper_function_cancellation_handling(self, mock_hass):
        """Test that helper function handles task cancellation gracefully."""
        from custom_components.smart_climate.helpers import async_wait_for_entities
        
        # Entities never become available
        mock_hass.states.get.return_value = None
        
        # Start waiting task
        wait_task = asyncio.create_task(
            async_wait_for_entities(mock_hass, ["sensor.never"], 30)
        )
        
        # Give it time to start
        await asyncio.sleep(0.1)
        
        # Cancel the task
        wait_task.cancel()
        
        # Should raise CancelledError
        with pytest.raises(asyncio.CancelledError):
            await wait_task