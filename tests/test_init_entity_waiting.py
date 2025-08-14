"""ABOUTME: Comprehensive tests for entity availability waiting in async_setup_entry.
Tests required vs optional entity waiting, timeout handling, and ConfigEntryNotReady patterns."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN


class TestAsyncSetupEntryEntityWaiting:
    """Test entity availability waiting in async_setup_entry."""

    @pytest.fixture
    def mock_hass(self):
        """Mock Home Assistant core."""
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
            "climate_entity": "climate.living_room",
            "room_sensor": "sensor.room_temperature"
        }
        entry.options = {}
        return entry

    @pytest.fixture
    def mock_config_entry_with_optional(self):
        """Mock config entry with required and optional entities."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        entry.data = {
            "climate_entity": "climate.living_room",
            "room_sensor": "sensor.room_temperature"
        }
        entry.options = {
            "outdoor_sensor": "sensor.outdoor_temperature",
            "power_sensor": "sensor.power_consumption",
            "indoor_humidity_sensor": "sensor.indoor_humidity"
        }
        return entry

    @pytest.fixture
    def mock_config_entry_custom_timeout(self):
        """Mock config entry with custom startup timeout."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        entry.data = {
            "climate_entity": "climate.living_room",
            "room_sensor": "sensor.room_temperature"
        }
        entry.options = {
            "startup_timeout": 120  # Custom 2-minute timeout
        }
        return entry

    def setup_entity_states(self, mock_hass, entity_states):
        """Helper to set up entity states."""
        def get_state_side_effect(entity_id):
            if entity_id in entity_states:
                state_obj = Mock()
                state_obj.state = entity_states[entity_id]
                return state_obj
            return None
        
        mock_hass.states.get.side_effect = get_state_side_effect

    @pytest.mark.asyncio
    @patch('custom_components.smart_climate.async_wait_for_entities')
    @patch('custom_components.smart_climate.SeasonalHysteresisLearner')
    @patch('custom_components.smart_climate._async_setup_entity_persistence')
    @patch('custom_components.smart_climate._async_register_services')
    async def test_setup_success_all_entities_available_immediately(
        self, mock_register_services, mock_setup_persistence, 
        mock_seasonal, mock_wait_for_entities, 
        mock_hass, mock_config_entry_with_optional
    ):
        """Test successful setup when all entities are immediately available."""
        # Setup: All entities are available immediately
        mock_wait_for_entities.return_value = True
        mock_setup_persistence.return_value = None
        mock_register_services.return_value = None

        # Import here to allow patching
        from custom_components.smart_climate import async_setup_entry

        # Test
        result = await async_setup_entry(mock_hass, mock_config_entry_with_optional)

        # Assert
        assert result is True, "Setup should succeed when all entities are available"
        
        # Verify required entities checked with 90s timeout (default)
        required_call = mock_wait_for_entities.call_args_list[0]
        assert required_call[0][1] == ["climate.living_room", "sensor.room_temperature"]
        assert required_call[0][2] == 90  # Default timeout
        
        # Verify optional entities checked with 15s timeout
        optional_call = mock_wait_for_entities.call_args_list[1]
        assert "sensor.outdoor_temperature" in optional_call[0][1]
        assert "sensor.power_consumption" in optional_call[0][1]
        assert "sensor.indoor_humidity" in optional_call[0][1]
        assert optional_call[0][2] == 15  # Fixed optional timeout

        # Verify platforms were set up
        mock_hass.config_entries.async_forward_entry_setups.assert_called_once()

    @pytest.mark.asyncio
    @patch('custom_components.smart_climate.async_wait_for_entities')
    async def test_setup_success_entities_become_available_within_timeout(
        self, mock_wait_for_entities, mock_hass, mock_config_entry_required_only
    ):
        """Test successful setup when entities become available within timeout."""
        # Setup: Entities become available after waiting
        mock_wait_for_entities.return_value = True

        with patch('custom_components.smart_climate.SeasonalHysteresisLearner'), \
             patch('custom_components.smart_climate._async_setup_entity_persistence') as mock_setup_persistence, \
             patch('custom_components.smart_climate._async_register_services') as mock_register_services:
            
            mock_setup_persistence.return_value = None
            mock_register_services.return_value = None

            from custom_components.smart_climate import async_setup_entry

            # Test
            result = await async_setup_entry(mock_hass, mock_config_entry_required_only)

            # Assert
            assert result is True, "Setup should succeed when entities become available within timeout"
            
            # Verify required entities were waited for
            required_call = mock_wait_for_entities.call_args_list[0]
            assert required_call[0][1] == ["climate.living_room", "sensor.room_temperature"]
            assert required_call[0][2] == 90

    @pytest.mark.asyncio
    @patch('custom_components.smart_climate.async_wait_for_entities')
    async def test_setup_fails_required_entities_timeout_raises_config_entry_not_ready(
        self, mock_wait_for_entities, mock_hass, mock_config_entry_required_only
    ):
        """Test that ConfigEntryNotReady is raised when required entities timeout."""
        # Setup: Required entities timeout
        mock_wait_for_entities.return_value = False

        from custom_components.smart_climate import async_setup_entry

        # Test & Assert
        with pytest.raises(ConfigEntryNotReady) as exc_info:
            await async_setup_entry(mock_hass, mock_config_entry_required_only)

        # Verify the exception message mentions required entities and timeout
        error_msg = str(exc_info.value)
        assert "Required entities not available after 90s" in error_msg
        assert "Integration setup will be retried" in error_msg

        # Verify required entities were checked
        mock_wait_for_entities.assert_called_once()
        call_args = mock_wait_for_entities.call_args
        assert call_args[0][1] == ["climate.living_room", "sensor.room_temperature"]
        assert call_args[0][2] == 90

    @pytest.mark.asyncio
    @patch('custom_components.smart_climate.async_wait_for_entities')
    @patch('custom_components.smart_climate.SeasonalHysteresisLearner')
    @patch('custom_components.smart_climate._async_setup_entity_persistence')
    @patch('custom_components.smart_climate._async_register_services')
    async def test_setup_continues_optional_entities_timeout_with_warning(
        self, mock_register_services, mock_setup_persistence,
        mock_seasonal, mock_wait_for_entities,
        mock_hass, mock_config_entry_with_optional
    ):
        """Test setup continues with warning when optional entities timeout."""
        # Setup: Required entities succeed, optional entities timeout
        mock_wait_for_entities.side_effect = [True, False]  # Required succeed, optional timeout
        mock_setup_persistence.return_value = None
        mock_register_services.return_value = None

        from custom_components.smart_climate import async_setup_entry

        with patch('custom_components.smart_climate._LOGGER') as mock_logger:
            # Test
            result = await async_setup_entry(mock_hass, mock_config_entry_with_optional)

            # Assert
            assert result is True, "Setup should succeed even when optional entities timeout"

            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "Optional entities not available after 15s" in warning_call
            assert "Integration will start without them" in warning_call

            # Verify both required and optional entity calls were made
            assert mock_wait_for_entities.call_count == 2
            
            # Required entities call
            required_call = mock_wait_for_entities.call_args_list[0]
            assert required_call[0][2] == 90
            
            # Optional entities call
            optional_call = mock_wait_for_entities.call_args_list[1]
            assert optional_call[0][2] == 15

    @pytest.mark.asyncio
    @patch('custom_components.smart_climate.async_wait_for_entities')
    async def test_setup_handles_mixed_entity_availability(
        self, mock_wait_for_entities, mock_hass, mock_config_entry_with_optional
    ):
        """Test setup with mixed entity availability scenarios."""
        # Test Case 1: Required available, optional timeout
        mock_wait_for_entities.side_effect = [True, False]

        with patch('custom_components.smart_climate.SeasonalHysteresisLearner'), \
             patch('custom_components.smart_climate._async_setup_entity_persistence') as mock_setup_persistence, \
             patch('custom_components.smart_climate._async_register_services') as mock_register_services, \
             patch('custom_components.smart_climate._LOGGER'):
            
            mock_setup_persistence.return_value = None
            mock_register_services.return_value = None

            from custom_components.smart_climate import async_setup_entry

            result = await async_setup_entry(mock_hass, mock_config_entry_with_optional)
            assert result is True, "Should succeed when required entities available"

        # Reset mocks
        mock_wait_for_entities.reset_mock()
        
        # Test Case 2: Required timeout (should fail)
        mock_wait_for_entities.return_value = False

        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(mock_hass, mock_config_entry_with_optional)

    @pytest.mark.asyncio
    @patch('custom_components.smart_climate.async_wait_for_entities')
    async def test_setup_uses_custom_timeout_from_options(
        self, mock_wait_for_entities, mock_hass, mock_config_entry_custom_timeout
    ):
        """Test setup uses custom timeout from options."""
        # Setup
        mock_wait_for_entities.return_value = True

        with patch('custom_components.smart_climate.SeasonalHysteresisLearner'), \
             patch('custom_components.smart_climate._async_setup_entity_persistence') as mock_setup_persistence, \
             patch('custom_components.smart_climate._async_register_services') as mock_register_services:
            
            mock_setup_persistence.return_value = None
            mock_register_services.return_value = None

            from custom_components.smart_climate import async_setup_entry

            # Test
            result = await async_setup_entry(mock_hass, mock_config_entry_custom_timeout)

            # Assert
            assert result is True, "Setup should succeed with custom timeout"
            
            # Verify custom timeout was used (120s instead of default 90s)
            required_call = mock_wait_for_entities.call_args_list[0]
            assert required_call[0][2] == 120, "Should use custom timeout from options"

    @pytest.mark.asyncio
    @patch('custom_components.smart_climate.async_wait_for_entities')
    async def test_setup_handles_cancelled_entity_waiting(
        self, mock_wait_for_entities, mock_hass, mock_config_entry_required_only
    ):
        """Test setup handles cancelled entity waiting gracefully."""
        # Setup: Simulate task cancellation during entity waiting
        async def cancelled_wait(*args, **kwargs):
            raise asyncio.CancelledError("Task was cancelled")
        
        mock_wait_for_entities.side_effect = cancelled_wait

        from custom_components.smart_climate import async_setup_entry

        # Test & Assert
        with pytest.raises(asyncio.CancelledError):
            await async_setup_entry(mock_hass, mock_config_entry_required_only)

        # Verify entity waiting was attempted
        mock_wait_for_entities.assert_called_once()

    @pytest.mark.asyncio
    @patch('custom_components.smart_climate.async_wait_for_entities')
    async def test_setup_entity_classification_correct(
        self, mock_wait_for_entities, mock_hass, mock_config_entry_with_optional
    ):
        """Test that entities are correctly classified as required vs optional."""
        # Setup
        mock_wait_for_entities.return_value = True

        with patch('custom_components.smart_climate.SeasonalHysteresisLearner'), \
             patch('custom_components.smart_climate._async_setup_entity_persistence') as mock_setup_persistence, \
             patch('custom_components.smart_climate._async_register_services') as mock_register_services:
            
            mock_setup_persistence.return_value = None
            mock_register_services.return_value = None

            from custom_components.smart_climate import async_setup_entry

            # Test
            await async_setup_entry(mock_hass, mock_config_entry_with_optional)

            # Assert entity classification
            assert mock_wait_for_entities.call_count == 2

            # Required entities (from entry.data)
            required_call = mock_wait_for_entities.call_args_list[0]
            required_entities = required_call[0][1]
            assert "climate.living_room" in required_entities
            assert "sensor.room_temperature" in required_entities
            assert len(required_entities) == 2

            # Optional entities (from entry.options)
            optional_call = mock_wait_for_entities.call_args_list[1]
            optional_entities = optional_call[0][1]
            assert "sensor.outdoor_temperature" in optional_entities
            assert "sensor.power_consumption" in optional_entities
            assert "sensor.indoor_humidity" in optional_entities
            # Note: None values should be filtered out in implementation
            assert None not in optional_entities

    @pytest.mark.asyncio
    @patch('custom_components.smart_climate.async_wait_for_entities')
    async def test_setup_no_optional_entities_skips_optional_wait(
        self, mock_wait_for_entities, mock_hass, mock_config_entry_required_only
    ):
        """Test setup skips optional entity waiting when no optional entities configured."""
        # Setup
        mock_wait_for_entities.return_value = True

        with patch('custom_components.smart_climate.SeasonalHysteresisLearner'), \
             patch('custom_components.smart_climate._async_setup_entity_persistence') as mock_setup_persistence, \
             patch('custom_components.smart_climate._async_register_services') as mock_register_services:
            
            mock_setup_persistence.return_value = None
            mock_register_services.return_value = None

            from custom_components.smart_climate import async_setup_entry

            # Test
            result = await async_setup_entry(mock_hass, mock_config_entry_required_only)

            # Assert
            assert result is True
            
            # Should only call wait_for_entities once for required entities
            assert mock_wait_for_entities.call_count == 1
            required_call = mock_wait_for_entities.call_args_list[0]
            assert required_call[0][2] == 90  # Required timeout

    @pytest.mark.asyncio
    @patch('custom_components.smart_climate.async_wait_for_entities')
    async def test_setup_error_handling_during_entity_setup(
        self, mock_wait_for_entities, mock_hass, mock_config_entry_required_only
    ):
        """Test error handling during entity setup after successful entity waiting."""
        # Setup: Entity waiting succeeds but component setup fails
        mock_wait_for_entities.return_value = True

        with patch('custom_components.smart_climate.SeasonalHysteresisLearner'), \
             patch('custom_components.smart_climate._async_setup_entity_persistence') as mock_setup_persistence, \
             patch('custom_components.smart_climate._async_register_services') as mock_register_services:
            
            # Simulate setup failure
            mock_setup_persistence.side_effect = Exception("Setup failed")
            mock_register_services.return_value = None

            from custom_components.smart_climate import async_setup_entry

            # Test & Assert - should propagate the setup error
            with pytest.raises(Exception, match="Setup failed"):
                await async_setup_entry(mock_hass, mock_config_entry_required_only)

            # Verify entity waiting succeeded before the error
            mock_wait_for_entities.assert_called_once()

    @pytest.mark.asyncio
    @patch('custom_components.smart_climate.async_wait_for_entities')
    async def test_setup_logging_during_entity_waiting(
        self, mock_wait_for_entities, mock_hass, mock_config_entry_with_optional
    ):
        """Test appropriate logging occurs during entity waiting."""
        # Setup
        mock_wait_for_entities.side_effect = [True, False]  # Required succeed, optional timeout

        with patch('custom_components.smart_climate.SeasonalHysteresisLearner'), \
             patch('custom_components.smart_climate._async_setup_entity_persistence') as mock_setup_persistence, \
             patch('custom_components.smart_climate._async_register_services') as mock_register_services, \
             patch('custom_components.smart_climate._LOGGER') as mock_logger:
            
            mock_setup_persistence.return_value = None
            mock_register_services.return_value = None

            from custom_components.smart_climate import async_setup_entry

            # Test
            result = await async_setup_entry(mock_hass, mock_config_entry_with_optional)

            # Assert
            assert result is True

            # Verify appropriate logging occurred
            # Should log info about waiting for required entities
            info_calls = [call for call in mock_logger.info.call_args_list 
                         if "Waiting for required entities" in str(call)]
            assert len(info_calls) > 0, "Should log info about waiting for required entities"

            # Should log warning about optional entity timeout  
            warning_calls = mock_logger.warning.call_args_list
            assert len(warning_calls) == 1, "Should log warning for optional entity timeout"
            warning_msg = warning_calls[0][0][0]
            assert "Optional entities not available after 15s" in warning_msg

    def test_entity_waiting_integration_constants_available(self):
        """Test that required constants for entity waiting are available."""
        from custom_components.smart_climate.const import (
            CONF_CLIMATE_ENTITY,
            CONF_ROOM_SENSOR,
            CONF_OUTDOOR_SENSOR,
            CONF_POWER_SENSOR,
            CONF_INDOOR_HUMIDITY_SENSOR,
            CONF_STARTUP_TIMEOUT,
            STARTUP_TIMEOUT_SEC
        )

        # Verify constants are properly defined
        assert CONF_CLIMATE_ENTITY == "climate_entity"
        assert CONF_ROOM_SENSOR == "room_sensor"
        assert CONF_OUTDOOR_SENSOR == "outdoor_sensor"
        assert CONF_POWER_SENSOR == "power_sensor"
        assert CONF_INDOOR_HUMIDITY_SENSOR == "indoor_humidity_sensor"
        assert CONF_STARTUP_TIMEOUT == "startup_timeout"
        assert STARTUP_TIMEOUT_SEC == 90
        assert isinstance(STARTUP_TIMEOUT_SEC, int)