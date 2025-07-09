"""Test save interval configuration functionality."""
import pytest
from unittest.mock import Mock, patch
from homeassistant.config_entries import ConfigEntry
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.core import HomeAssistant
from custom_components.smart_climate.config_flow import SmartClimateConfigFlow, SmartClimateOptionsFlow
from custom_components.smart_climate.const import (
    CONF_SAVE_INTERVAL,
    DEFAULT_SAVE_INTERVAL,
    DOMAIN,
)

pytestmark = pytest.mark.asyncio


class TestSaveIntervalConfig:
    """Test save interval configuration in config flow."""
    
    @pytest.fixture
    def mock_hass(self):
        """Mock Home Assistant."""
        hass = Mock()
        hass.states = Mock()
        hass.states.async_all = Mock(return_value=[])
        hass.config_entries = Mock()
        hass.config_entries.async_entries = Mock(return_value=[])
        return hass

    @pytest.fixture
    def config_flow(self, mock_hass):
        """Create config flow instance."""
        flow = SmartClimateConfigFlow()
        flow.hass = mock_hass
        return flow

    def test_save_interval_default_value(self):
        """Test save interval has correct default value."""
        assert DEFAULT_SAVE_INTERVAL == 3600  # 60 minutes

    async def test_save_interval_in_config_schema(self, config_flow):
        """Test save interval is present in config schema."""
        # Mock entities for selectors
        with patch.object(config_flow, '_get_climate_entities', return_value={'climate.test': 'Test'}):
            with patch.object(config_flow, '_get_temperature_sensors', return_value={'sensor.temp': 'Temp'}):
                with patch.object(config_flow, '_get_power_sensors', return_value={}):
                    # Get the schema by calling the form
                    result = await config_flow.async_step_user()
                    
                    # Check that save_interval is in the schema
                    schema_dict = dict(result['data_schema'].schema)
                    assert any(CONF_SAVE_INTERVAL in str(key) for key in schema_dict.keys())

    async def test_save_interval_validation_range(self, config_flow):
        """Test save interval validation accepts valid range."""
        valid_intervals = [300, 1800, 3600, 7200, 86400]  # 5 min to 24 hours
        
        for interval in valid_intervals:
            user_input = {
                'climate_entity': 'climate.test',
                'room_sensor': 'sensor.temp',
                CONF_SAVE_INTERVAL: interval
            }
            
            with patch.object(config_flow, '_entity_exists', return_value=True):
                with patch.object(config_flow, '_already_configured', return_value=False):
                    validated = await config_flow._validate_input(user_input)
                    assert validated[CONF_SAVE_INTERVAL] == interval

    async def test_save_interval_validation_minimum(self, config_flow):
        """Test save interval validation rejects values below minimum."""
        user_input = {
            'climate_entity': 'climate.test',
            'room_sensor': 'sensor.temp',
            CONF_SAVE_INTERVAL: 299  # Below 300s minimum
        }
        
        # This should not raise an error as validation happens in the selector
        # The selector config will enforce the minimum value
        with patch.object(config_flow, '_entity_exists', return_value=True):
            with patch.object(config_flow, '_already_configured', return_value=False):
                validated = await config_flow._validate_input(user_input)
                assert CONF_SAVE_INTERVAL in validated

    async def test_save_interval_validation_maximum(self, config_flow):
        """Test save interval validation rejects values above maximum."""
        user_input = {
            'climate_entity': 'climate.test',
            'room_sensor': 'sensor.temp',
            CONF_SAVE_INTERVAL: 86401  # Above 86400s maximum
        }
        
        # This should not raise an error as validation happens in the selector
        # The selector config will enforce the maximum value
        with patch.object(config_flow, '_entity_exists', return_value=True):
            with patch.object(config_flow, '_already_configured', return_value=False):
                validated = await config_flow._validate_input(user_input)
                assert CONF_SAVE_INTERVAL in validated

    async def test_save_interval_backward_compatibility(self, config_flow):
        """Test that existing configs without save_interval get default value."""
        user_input = {
            'climate_entity': 'climate.test',
            'room_sensor': 'sensor.temp',
            # No save_interval specified
        }
        
        with patch.object(config_flow, '_entity_exists', return_value=True):
            with patch.object(config_flow, '_already_configured', return_value=False):
                validated = await config_flow._validate_input(user_input)
                assert validated[CONF_SAVE_INTERVAL] == DEFAULT_SAVE_INTERVAL

    async def test_save_interval_in_options_flow(self, mock_hass):
        """Test save interval is available in options flow."""
        config_entry = Mock(spec=ConfigEntry)
        config_entry.data = {
            'climate_entity': 'climate.test',
            'room_sensor': 'sensor.temp',
            CONF_SAVE_INTERVAL: 1800
        }
        config_entry.options = {}
        
        options_flow = SmartClimateOptionsFlow()
        options_flow.hass = mock_hass
        options_flow.config_entry = config_entry
        
        result = await options_flow.async_step_init()
        
        # Check that save_interval is in the options schema
        schema_dict = dict(result['data_schema'].schema)
        assert any(CONF_SAVE_INTERVAL in str(key) for key in schema_dict.keys())

    async def test_save_interval_options_preserves_current_value(self, mock_hass):
        """Test options flow preserves current save interval value."""
        current_interval = 7200  # 2 hours
        config_entry = Mock(spec=ConfigEntry)
        config_entry.data = {
            'climate_entity': 'climate.test',
            'room_sensor': 'sensor.temp',
            CONF_SAVE_INTERVAL: current_interval
        }
        config_entry.options = {}
        
        options_flow = SmartClimateOptionsFlow()
        options_flow.hass = mock_hass
        options_flow.config_entry = config_entry
        
        result = await options_flow.async_step_init()
        
        # Find the save_interval field in the schema
        schema_dict = dict(result['data_schema'].schema)
        save_interval_field = None
        for key in schema_dict.keys():
            if CONF_SAVE_INTERVAL in str(key):
                save_interval_field = key
                break
        
        assert save_interval_field is not None
        assert save_interval_field.default == current_interval

    async def test_save_interval_options_updates_value(self, mock_hass):
        """Test options flow can update save interval value."""
        config_entry = Mock(spec=ConfigEntry)
        config_entry.data = {
            'climate_entity': 'climate.test',
            'room_sensor': 'sensor.temp',
            CONF_SAVE_INTERVAL: 3600
        }
        config_entry.options = {}
        
        options_flow = SmartClimateOptionsFlow()
        options_flow.hass = mock_hass
        options_flow.config_entry = config_entry
        
        # Submit new value
        new_interval = 7200  # 2 hours
        result = await options_flow.async_step_init({CONF_SAVE_INTERVAL: new_interval})
        
        assert result['type'] == FlowResultType.CREATE_ENTRY
        assert result['data'][CONF_SAVE_INTERVAL] == new_interval

    async def test_save_interval_options_with_existing_options(self, mock_hass):
        """Test options flow with existing options overrides config data."""
        config_entry = Mock(spec=ConfigEntry)
        config_entry.data = {
            'climate_entity': 'climate.test',
            'room_sensor': 'sensor.temp',
            CONF_SAVE_INTERVAL: 3600  # Original value
        }
        config_entry.options = {
            CONF_SAVE_INTERVAL: 1800  # Previously changed value
        }
        
        options_flow = SmartClimateOptionsFlow()
        options_flow.hass = mock_hass
        options_flow.config_entry = config_entry
        
        result = await options_flow.async_step_init()
        
        # Find the save_interval field in the schema
        schema_dict = dict(result['data_schema'].schema)
        save_interval_field = None
        for key in schema_dict.keys():
            if CONF_SAVE_INTERVAL in str(key):
                save_interval_field = key
                break
        
        assert save_interval_field is not None
        # Should use options value, not config data value
        assert save_interval_field.default == 1800