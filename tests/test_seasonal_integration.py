"""Test seasonal adaptation integration into Smart Climate setup."""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError

from custom_components.smart_climate import async_setup_entry, _async_setup_entity_persistence
from custom_components.smart_climate.seasonal_learner import SeasonalHysteresisLearner
from custom_components.smart_climate.const import DOMAIN


@pytest.fixture
def mock_config_entry_with_outdoor():
    """Create a mock config entry with outdoor sensor."""
    config_data = {
        "climate_entity": "climate.test_ac",
        "room_sensor": "sensor.room_temp",
        "outdoor_sensor": "sensor.outdoor_temp",  # Outdoor sensor present
        "max_offset": 5.0,
        "update_interval": 180,
        "enable_retry": True,
        "max_retry_attempts": 4,
        "initial_timeout": 60
    }
    
    entry = Mock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = config_data
    entry.title = "Test Smart Climate"
    return entry


@pytest.fixture
def mock_config_entry_without_outdoor():
    """Create a mock config entry without outdoor sensor."""
    config_data = {
        "climate_entity": "climate.test_ac",
        "room_sensor": "sensor.room_temp",
        # No outdoor_sensor key
        "max_offset": 5.0,
        "update_interval": 180,
        "enable_retry": True,
        "max_retry_attempts": 4,
        "initial_timeout": 60
    }
    
    entry = Mock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = config_data
    entry.title = "Test Smart Climate"
    return entry


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.data = {DOMAIN: {}}
    hass.config_entries = Mock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    return hass


class TestSeasonalLearnerCreation:
    """Test seasonal learner creation during setup."""

    @patch('custom_components.smart_climate.EntityWaiter')
    @patch('custom_components.smart_climate._async_register_services')
    @patch('custom_components.smart_climate.SeasonalHysteresisLearner')
    @pytest.mark.asyncio
    async def test_seasonal_learner_created_with_outdoor_sensor(self, mock_seasonal_class, mock_register_services, mock_entity_waiter, mock_hass, mock_config_entry_with_outdoor):
        """Test that SeasonalHysteresisLearner is created when outdoor sensor is configured."""
        # Setup mocks
        mock_entity_waiter_instance = Mock()
        mock_entity_waiter_instance.wait_for_required_entities = AsyncMock()
        mock_entity_waiter.return_value = mock_entity_waiter_instance
        mock_register_services.return_value = AsyncMock()
        
        # Mock seasonal learner instance
        mock_seasonal_instance = Mock(spec=SeasonalHysteresisLearner)
        mock_seasonal_instance.async_load = AsyncMock()
        mock_seasonal_class.return_value = mock_seasonal_instance
        
        # Execute setup
        result = await async_setup_entry(mock_hass, mock_config_entry_with_outdoor)
        
        # Verify setup succeeded
        assert result is True
        
        # Verify SeasonalHysteresisLearner was created with correct parameters
        mock_seasonal_class.assert_called_once_with(
            mock_hass,
            "sensor.outdoor_temp"  # outdoor_sensor_id should be passed
        )
        
        # Verify seasonal learner is stored in hass.data
        entry_data = mock_hass.data[DOMAIN]["test_entry_id"]
        assert "seasonal_learners" in entry_data
        assert entry_data["seasonal_learners"]["climate.test_ac"] == mock_seasonal_instance

    @patch('custom_components.smart_climate.EntityWaiter')
    @patch('custom_components.smart_climate._async_register_services')
    @patch('custom_components.smart_climate.seasonal_learner.SeasonalHysteresisLearner')
    @pytest.mark.asyncio
    async def test_seasonal_learner_not_created_without_outdoor_sensor(self, mock_seasonal_class, mock_register_services, mock_entity_waiter, mock_hass, mock_config_entry_without_outdoor):
        """Test that SeasonalHysteresisLearner is not created when outdoor sensor is not configured."""
        # Setup mocks
        mock_entity_waiter_instance = Mock()
        mock_entity_waiter_instance.wait_for_required_entities = AsyncMock()
        mock_entity_waiter.return_value = mock_entity_waiter_instance
        mock_register_services.return_value = AsyncMock()
        
        # Execute setup
        result = await async_setup_entry(mock_hass, mock_config_entry_without_outdoor)
        
        # Verify setup succeeded
        assert result is True
        
        # Verify SeasonalHysteresisLearner was NOT created
        mock_seasonal_class.assert_not_called()
        
        # Verify no seasonal learner is stored in hass.data
        entry_data = mock_hass.data[DOMAIN]["test_entry_id"]
        seasonal_learners = entry_data.get("seasonal_learners", {})
        assert "climate.test_ac" not in seasonal_learners


class TestOffsetEngineIntegration:
    """Test integration of seasonal learner with OffsetEngine."""

    @patch('custom_components.smart_climate.OffsetEngine')
    @patch('custom_components.smart_climate.SmartClimateDataStore')
    @patch('custom_components.smart_climate.DataUpdateCoordinator')
    @patch('custom_components.smart_climate.seasonal_learner.SeasonalHysteresisLearner')
    @pytest.mark.asyncio
    async def test_offset_engine_receives_seasonal_learner(self, mock_seasonal_class, mock_coordinator_class, mock_data_store_class, mock_offset_engine_class, mock_hass):
        """Test that OffsetEngine receives seasonal_learner during entity persistence setup."""
        # Setup config with outdoor sensor
        config_data = {
            "climate_entity": "climate.test_ac",
            "room_sensor": "sensor.room_temp",
            "outdoor_sensor": "sensor.outdoor_temp",
            "max_offset": 5.0,
        }
        
        entry = Mock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.data = config_data
        
        # Initialize hass.data structure
        mock_hass.data[DOMAIN] = {
            "test_entry_id": {
                "seasonal_learners": {},
                "offset_engines": {},
                "data_stores": {},
                "coordinators": {},
                "unload_listeners": []
            }
        }
        
        # Mock seasonal learner instance
        mock_seasonal_instance = Mock(spec=SeasonalHysteresisLearner)
        mock_seasonal_class.return_value = mock_seasonal_instance
        mock_hass.data[DOMAIN]["test_entry_id"]["seasonal_learners"]["climate.test_ac"] = mock_seasonal_instance
        
        # Mock OffsetEngine instance
        mock_offset_engine = Mock()
        mock_offset_engine.async_get_dashboard_data = AsyncMock(return_value={})
        mock_offset_engine.set_data_store = Mock()
        mock_offset_engine.async_load_learning_data = AsyncMock(return_value=True)
        mock_offset_engine.async_setup_periodic_save = AsyncMock(return_value=Mock())
        mock_offset_engine_class.return_value = mock_offset_engine
        
        # Mock other components
        mock_data_store = Mock()
        mock_data_store_class.return_value = mock_data_store
        
        mock_coordinator = Mock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator
        
        # Execute entity persistence setup
        await _async_setup_entity_persistence(mock_hass, entry, "climate.test_ac")
        
        # Verify OffsetEngine was created with seasonal_learner parameter
        mock_offset_engine_class.assert_called_once()
        call_args = mock_offset_engine_class.call_args
        
        # Check if seasonal_learner was passed (could be positional or keyword)
        seasonal_learner_passed = False
        if len(call_args[0]) > 1:  # Positional argument
            seasonal_learner_passed = call_args[0][1] == mock_seasonal_instance
        elif 'seasonal_learner' in call_args[1]:  # Keyword argument
            seasonal_learner_passed = call_args[1]['seasonal_learner'] == mock_seasonal_instance
        
        assert seasonal_learner_passed, f"seasonal_learner not passed to OffsetEngine. Args: {call_args}"

    @patch('custom_components.smart_climate.OffsetEngine')
    @patch('custom_components.smart_climate.SmartClimateDataStore')
    @patch('custom_components.smart_climate.DataUpdateCoordinator')
    @pytest.mark.asyncio
    async def test_offset_engine_receives_none_without_outdoor_sensor(self, mock_coordinator_class, mock_data_store_class, mock_offset_engine_class, mock_hass):
        """Test that OffsetEngine receives seasonal_learner=None when no outdoor sensor configured."""
        # Setup config without outdoor sensor
        config_data = {
            "climate_entity": "climate.test_ac",
            "room_sensor": "sensor.room_temp",
            # No outdoor_sensor
            "max_offset": 5.0,
        }
        
        entry = Mock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.data = config_data
        
        # Initialize hass.data structure (no seasonal learners)
        mock_hass.data[DOMAIN] = {
            "test_entry_id": {
                "seasonal_learners": {},  # Empty - no outdoor sensor
                "offset_engines": {},
                "data_stores": {},
                "coordinators": {},
                "unload_listeners": []
            }
        }
        
        # Mock OffsetEngine instance
        mock_offset_engine = Mock()
        mock_offset_engine.async_get_dashboard_data = AsyncMock(return_value={})
        mock_offset_engine.set_data_store = Mock()
        mock_offset_engine.async_load_learning_data = AsyncMock(return_value=True)
        mock_offset_engine.async_setup_periodic_save = AsyncMock(return_value=Mock())
        mock_offset_engine_class.return_value = mock_offset_engine
        
        # Mock other components
        mock_data_store = Mock()
        mock_data_store_class.return_value = mock_data_store
        
        mock_coordinator = Mock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator
        
        # Execute entity persistence setup
        await _async_setup_entity_persistence(mock_hass, entry, "climate.test_ac")
        
        # Verify OffsetEngine was created with seasonal_learner=None
        mock_offset_engine_class.assert_called_once()
        call_args = mock_offset_engine_class.call_args
        
        # Check that seasonal_learner was passed as None
        seasonal_learner_none = False
        if len(call_args[0]) > 1:  # Positional argument
            seasonal_learner_none = call_args[0][1] is None
        elif 'seasonal_learner' in call_args[1]:  # Keyword argument
            seasonal_learner_none = call_args[1]['seasonal_learner'] is None
        
        assert seasonal_learner_none, f"seasonal_learner should be None. Args: {call_args}"


class TestSetupValidation:
    """Test setup validation and error handling."""

    @patch('custom_components.smart_climate.EntityWaiter')
    @patch('custom_components.smart_climate._async_register_services')
    @patch('custom_components.smart_climate.SeasonalHysteresisLearner')
    @pytest.mark.asyncio
    async def test_setup_continues_with_seasonal_learner_creation_failure(self, mock_seasonal_class, mock_register_services, mock_entity_waiter, mock_hass, mock_config_entry_with_outdoor):
        """Test that setup continues if seasonal learner creation fails."""
        # Setup mocks
        mock_entity_waiter_instance = Mock()
        mock_entity_waiter_instance.wait_for_required_entities = AsyncMock()
        mock_entity_waiter.return_value = mock_entity_waiter_instance
        mock_register_services.return_value = AsyncMock()
        
        # Make seasonal learner creation fail
        mock_seasonal_class.side_effect = Exception("Seasonal learner creation failed")
        
        # Execute setup
        result = await async_setup_entry(mock_hass, mock_config_entry_with_outdoor)
        
        # Verify setup still succeeded (graceful degradation)
        assert result is True
        
        # Verify seasonal learner creation was attempted
        mock_seasonal_class.assert_called_once_with(
            mock_hass,
            "sensor.outdoor_temp"
        )
        
        # Verify no seasonal learner is stored due to failure
        entry_data = mock_hass.data[DOMAIN]["test_entry_id"]
        seasonal_learners = entry_data.get("seasonal_learners", {})
        assert "climate.test_ac" not in seasonal_learners

    @pytest.mark.asyncio
    async def test_setup_with_invalid_outdoor_sensor_config(self, mock_hass):
        """Test setup behavior with invalid outdoor sensor configuration."""
        # Setup config with invalid outdoor sensor (empty string)
        config_data = {
            "climate_entity": "climate.test_ac",
            "room_sensor": "sensor.room_temp",
            "outdoor_sensor": "",  # Invalid empty string
            "max_offset": 5.0,
        }
        
        entry = Mock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.data = config_data
        
        with patch('custom_components.smart_climate.EntityWaiter') as mock_entity_waiter, \
             patch('custom_components.smart_climate._async_register_services') as mock_register_services, \
             patch('custom_components.smart_climate.seasonal_learner.SeasonalHysteresisLearner') as mock_seasonal_class:
            
            # Setup mocks
            mock_entity_waiter_instance = Mock()
            mock_entity_waiter_instance.wait_for_required_entities = AsyncMock()
            mock_entity_waiter.return_value = mock_entity_waiter_instance
            mock_register_services.return_value = AsyncMock()
            
            # Execute setup
            result = await async_setup_entry(mock_hass, entry)
            
            # Verify setup succeeded
            assert result is True
            
            # Verify seasonal learner was NOT created (empty string should be treated as None)
            mock_seasonal_class.assert_not_called()


class TestSeasonalFeatureStatusLogging:
    """Test logging of seasonal feature status during setup."""

    @patch('custom_components.smart_climate.EntityWaiter')
    @patch('custom_components.smart_climate._async_register_services')
    @patch('custom_components.smart_climate.SeasonalHysteresisLearner')
    @patch('custom_components.smart_climate._LOGGER')
    @pytest.mark.asyncio
    async def test_seasonal_features_enabled_logging(self, mock_logger, mock_seasonal_class, mock_register_services, mock_entity_waiter, mock_hass, mock_config_entry_with_outdoor):
        """Test that enabled seasonal features are logged appropriately."""
        # Setup mocks
        mock_entity_waiter_instance = Mock()
        mock_entity_waiter_instance.wait_for_required_entities = AsyncMock()
        mock_entity_waiter.return_value = mock_entity_waiter_instance
        mock_register_services.return_value = AsyncMock()
        
        mock_seasonal_instance = Mock(spec=SeasonalHysteresisLearner)
        mock_seasonal_class.return_value = mock_seasonal_instance
        
        # Execute setup
        await async_setup_entry(mock_hass, mock_config_entry_with_outdoor)
        
        # Verify seasonal features enabled log message
        mock_logger.info.assert_any_call(
            "Seasonal adaptation features enabled for entity %s with outdoor sensor %s",
            "climate.test_ac",
            "sensor.outdoor_temp"
        )

    @patch('custom_components.smart_climate.EntityWaiter')
    @patch('custom_components.smart_climate._async_register_services')
    @patch('custom_components.smart_climate._LOGGER')
    @pytest.mark.asyncio
    async def test_seasonal_features_disabled_logging(self, mock_logger, mock_register_services, mock_entity_waiter, mock_hass, mock_config_entry_without_outdoor):
        """Test that disabled seasonal features are logged appropriately."""
        # Setup mocks
        mock_entity_waiter_instance = Mock()
        mock_entity_waiter_instance.wait_for_required_entities = AsyncMock()
        mock_entity_waiter.return_value = mock_entity_waiter_instance
        mock_register_services.return_value = AsyncMock()
        
        # Execute setup
        await async_setup_entry(mock_hass, mock_config_entry_without_outdoor)
        
        # Verify seasonal features disabled log message
        mock_logger.info.assert_any_call(
            "Seasonal adaptation features disabled for entity %s (no outdoor sensor configured)",
            "climate.test_ac"
        )


class TestMultipleClimateEntities:
    """Test seasonal integration with multiple climate entities."""

    @patch('custom_components.smart_climate.EntityWaiter')
    @patch('custom_components.smart_climate._async_register_services')
    @patch('custom_components.smart_climate.SeasonalHysteresisLearner')
    @pytest.mark.asyncio
    async def test_seasonal_learner_created_for_multiple_entities(self, mock_seasonal_class, mock_register_services, mock_entity_waiter, mock_hass):
        """Test that seasonal learners are created for multiple climate entities."""
        # Setup config with multiple climate entities
        config_data = {
            "climate_entities": ["climate.ac_1", "climate.ac_2"],
            "room_sensor": "sensor.room_temp",
            "outdoor_sensor": "sensor.outdoor_temp",
            "max_offset": 5.0,
        }
        
        entry = Mock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.data = config_data
        entry.title = "Test Smart Climate"
        
        # Setup mocks
        mock_entity_waiter_instance = Mock()
        mock_entity_waiter_instance.wait_for_required_entities = AsyncMock()
        mock_entity_waiter.return_value = mock_entity_waiter_instance
        mock_register_services.return_value = AsyncMock()
        
        mock_seasonal_instance = Mock(spec=SeasonalHysteresisLearner)
        mock_seasonal_class.return_value = mock_seasonal_instance
        
        # Execute setup
        result = await async_setup_entry(mock_hass, entry)
        
        # Verify setup succeeded
        assert result is True
        
        # Verify SeasonalHysteresisLearner was created twice (once per entity)
        assert mock_seasonal_class.call_count == 2
        
        # Verify both calls had correct parameters
        expected_calls = [
            ((mock_hass, "sensor.outdoor_temp"),),
            ((mock_hass, "sensor.outdoor_temp"),)
        ]
        actual_calls = mock_seasonal_class.call_args_list
        assert actual_calls == expected_calls
        
        # Verify both seasonal learners are stored
        entry_data = mock_hass.data[DOMAIN]["test_entry_id"]
        assert "seasonal_learners" in entry_data
        assert "climate.ac_1" in entry_data["seasonal_learners"]
        assert "climate.ac_2" in entry_data["seasonal_learners"]
        assert entry_data["seasonal_learners"]["climate.ac_1"] == mock_seasonal_instance
        assert entry_data["seasonal_learners"]["climate.ac_2"] == mock_seasonal_instance


class TestSeasonalLearnerPersistence:
    """Test seasonal learner persistence during setup."""

    @patch('custom_components.smart_climate.EntityWaiter')
    @patch('custom_components.smart_climate._async_register_services')
    @patch('custom_components.smart_climate.SeasonalHysteresisLearner')
    @pytest.mark.asyncio
    async def test_seasonal_learner_loading_during_setup(self, mock_seasonal_class, mock_register_services, mock_entity_waiter, mock_hass, mock_config_entry_with_outdoor):
        """Test that seasonal learner data is loaded during setup."""
        # Setup mocks
        mock_entity_waiter_instance = Mock()
        mock_entity_waiter_instance.wait_for_required_entities = AsyncMock()
        mock_entity_waiter.return_value = mock_entity_waiter_instance
        mock_register_services.return_value = AsyncMock()
        
        mock_seasonal_instance = Mock(spec=SeasonalHysteresisLearner)
        mock_seasonal_instance.async_load = AsyncMock()
        mock_seasonal_class.return_value = mock_seasonal_instance
        
        # Execute setup
        result = await async_setup_entry(mock_hass, mock_config_entry_with_outdoor)
        
        # Verify setup succeeded
        assert result is True
        
        # Verify seasonal learner data was loaded
        mock_seasonal_instance.async_load.assert_called_once()

    @patch('custom_components.smart_climate.EntityWaiter')
    @patch('custom_components.smart_climate._async_register_services')
    @patch('custom_components.smart_climate.SeasonalHysteresisLearner')
    @patch('custom_components.smart_climate._LOGGER')
    @pytest.mark.asyncio
    async def test_seasonal_learner_loading_failure_handling(self, mock_logger, mock_seasonal_class, mock_register_services, mock_entity_waiter, mock_hass, mock_config_entry_with_outdoor):
        """Test graceful handling of seasonal learner loading failures."""
        # Setup mocks
        mock_entity_waiter_instance = Mock()
        mock_entity_waiter_instance.wait_for_required_entities = AsyncMock()
        mock_entity_waiter.return_value = mock_entity_waiter_instance
        mock_register_services.return_value = AsyncMock()
        
        mock_seasonal_instance = Mock(spec=SeasonalHysteresisLearner)
        mock_seasonal_instance.async_load = AsyncMock(side_effect=Exception("Loading failed"))
        mock_seasonal_class.return_value = mock_seasonal_instance
        
        # Execute setup
        result = await async_setup_entry(mock_hass, mock_config_entry_with_outdoor)
        
        # Verify setup still succeeded (graceful degradation)
        assert result is True
        
        # Verify loading was attempted
        mock_seasonal_instance.async_load.assert_called_once()
        
        # Verify error was logged
        mock_logger.warning.assert_any_call(
            "Failed to load seasonal patterns for entity %s: %s",
            "climate.test_ac",
            mock_seasonal_instance.async_load.side_effect
        )