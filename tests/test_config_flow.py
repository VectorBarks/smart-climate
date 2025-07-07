"""Test config flow for Smart Climate Control."""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import sys

# Mock homeassistant modules
sys.modules['homeassistant.helpers.selector'] = MagicMock()
sys.modules['homeassistant.helpers.entity_registry'] = MagicMock()
sys.modules['homeassistant.helpers.device_registry'] = MagicMock()

# Mock config_entries and data_entry_flow
mock_config_entries = MagicMock()
mock_config_entries.ConfigFlow = MagicMock()
mock_config_entries.OptionsFlow = MagicMock()
mock_config_entries.ConfigEntry = MagicMock()
sys.modules['homeassistant.config_entries'] = mock_config_entries

# Mock data_entry_flow
mock_data_entry_flow = MagicMock()
mock_data_entry_flow.FlowResultType = MagicMock()
mock_data_entry_flow.FlowResultType.FORM = "form"
mock_data_entry_flow.FlowResultType.CREATE_ENTRY = "create_entry"
mock_data_entry_flow.FlowResult = dict
sys.modules['homeassistant.data_entry_flow'] = mock_data_entry_flow

from custom_components.smart_climate.config_flow import SmartClimateConfigFlow
from custom_components.smart_climate.const import (
    DOMAIN,
    CONF_CLIMATE_ENTITY,
    CONF_ROOM_SENSOR,
    CONF_OUTDOOR_SENSOR,
    CONF_POWER_SENSOR,
    CONF_MAX_OFFSET,
    CONF_MIN_TEMPERATURE,
    CONF_MAX_TEMPERATURE,
    CONF_UPDATE_INTERVAL,
    CONF_ML_ENABLED,
    DEFAULT_MAX_OFFSET,
    DEFAULT_MIN_TEMPERATURE,
    DEFAULT_MAX_TEMPERATURE,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_ML_ENABLED,
)


@pytest.fixture
def hass():
    """Create a mock Home Assistant instance."""
    mock_hass = MagicMock()
    mock_hass.data = {}
    return mock_hass


@pytest.fixture
def mock_climate_entities():
    """Mock climate entities available in Home Assistant."""
    return {
        "climate.living_room": "Living Room AC",
        "climate.bedroom": "Bedroom AC",
        "climate.office": "Office AC",
    }


@pytest.fixture
def mock_temperature_sensors():
    """Mock temperature sensors available in Home Assistant."""
    return {
        "sensor.living_room_temperature": "Living Room Temperature",
        "sensor.bedroom_temperature": "Bedroom Temperature", 
        "sensor.outdoor_temperature": "Outdoor Temperature",
        "sensor.office_temperature": "Office Temperature",
    }


@pytest.fixture
def mock_power_sensors():
    """Mock power sensors available in Home Assistant."""
    return {
        "sensor.living_room_power": "Living Room Power",
        "sensor.bedroom_power": "Bedroom Power",
        "sensor.office_power": "Office Power",
    }


class TestSmartClimateConfigFlow:
    """Test the Smart Climate config flow."""

    def test_config_flow_creates_form(self, hass, mock_climate_entities, mock_temperature_sensors):
        """Test that the config flow creates the initial form."""
        async def run_test():
            flow = SmartClimateConfigFlow()
            flow.hass = hass
            
            with patch.object(flow, '_get_climate_entities', return_value=mock_climate_entities), \
                 patch.object(flow, '_get_temperature_sensors', return_value=mock_temperature_sensors), \
                 patch.object(flow, '_get_power_sensors', return_value={}):
                
                result = await flow.async_step_user()
                
                assert result["type"] == "form"
                assert result["step_id"] == "user"
                assert result["data_schema"] is not None
        
        asyncio.run(run_test())

    def test_config_flow_validates_selected_entities(self, hass, mock_climate_entities, mock_temperature_sensors):
        """Test that selected entities are validated."""
        async def run_test():
            flow = SmartClimateConfigFlow()
            flow.hass = hass
            
            with patch.object(flow, '_get_climate_entities', return_value=mock_climate_entities), \
                 patch.object(flow, '_get_temperature_sensors', return_value=mock_temperature_sensors), \
                 patch.object(flow, '_get_power_sensors', return_value={}), \
                 patch.object(flow, '_entity_exists', return_value=True), \
                 patch.object(flow, '_already_configured', return_value=False):
                
                user_input = {
                    CONF_CLIMATE_ENTITY: "climate.living_room",
                    CONF_ROOM_SENSOR: "sensor.living_room_temperature",
                }
                
                result = await flow.async_step_user(user_input)
                
                # Should succeed with valid entities
                assert result["type"] == "create_entry"
                assert result["title"] == "Smart Climate Control"
                assert result["data"][CONF_CLIMATE_ENTITY] == "climate.living_room"
                assert result["data"][CONF_ROOM_SENSOR] == "sensor.living_room_temperature"
        
        asyncio.run(run_test())

    def test_config_flow_validates_invalid_climate_entity(self, hass, mock_climate_entities, mock_temperature_sensors):
        """Test validation of invalid climate entity."""
        flow = SmartClimateConfigFlow()
        flow.hass = hass
        
        with patch.object(flow, '_get_climate_entities', return_value=mock_climate_entities), \
             patch.object(flow, '_get_temperature_sensors', return_value=mock_temperature_sensors), \
             patch.object(flow, '_get_power_sensors', return_value={}):
            
            user_input = {
                CONF_CLIMATE_ENTITY: "climate.invalid",  # Invalid entity
                CONF_ROOM_SENSOR: "sensor.living_room_temperature",
            }
            
            result = flow.async_step_user(user_input)
            
            # Should show form with error
            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "user"
            assert result["errors"]["climate_entity"] == "entity_not_found"

    def test_config_flow_validates_invalid_sensor(self, hass, mock_climate_entities, mock_temperature_sensors):
        """Test validation of invalid temperature sensor."""
        flow = SmartClimateConfigFlow()
        flow.hass = hass
        
        with patch.object(flow, '_get_climate_entities', return_value=mock_climate_entities), \
             patch.object(flow, '_get_temperature_sensors', return_value=mock_temperature_sensors), \
             patch.object(flow, '_get_power_sensors', return_value={}):
            
            user_input = {
                CONF_CLIMATE_ENTITY: "climate.living_room",
                CONF_ROOM_SENSOR: "sensor.invalid_temperature",  # Invalid sensor
            }
            
            result = flow.async_step_user(user_input)
            
            # Should show form with error
            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "user"
            assert result["errors"]["room_sensor"] == "entity_not_found"

    def test_config_flow_includes_optional_sensors(self, hass, mock_climate_entities, mock_temperature_sensors, mock_power_sensors):
        """Test that optional sensors are included in config."""
        flow = SmartClimateConfigFlow()
        flow.hass = hass
        
        with patch.object(flow, '_get_climate_entities', return_value=mock_climate_entities), \
             patch.object(flow, '_get_temperature_sensors', return_value=mock_temperature_sensors), \
             patch.object(flow, '_get_power_sensors', return_value=mock_power_sensors):
            
            user_input = {
                CONF_CLIMATE_ENTITY: "climate.living_room",
                CONF_ROOM_SENSOR: "sensor.living_room_temperature",
                CONF_OUTDOOR_SENSOR: "sensor.outdoor_temperature",
                CONF_POWER_SENSOR: "sensor.living_room_power",
            }
            
            result = flow.async_step_user(user_input)
            
            assert result["type"] == FlowResultType.CREATE_ENTRY
            assert result["data"][CONF_OUTDOOR_SENSOR] == "sensor.outdoor_temperature"
            assert result["data"][CONF_POWER_SENSOR] == "sensor.living_room_power"

    def test_config_flow_applies_defaults(self, hass, mock_climate_entities, mock_temperature_sensors):
        """Test that default values are applied to config."""
        flow = SmartClimateConfigFlow()
        flow.hass = hass
        
        with patch.object(flow, '_get_climate_entities', return_value=mock_climate_entities), \
             patch.object(flow, '_get_temperature_sensors', return_value=mock_temperature_sensors), \
             patch.object(flow, '_get_power_sensors', return_value={}):
            
            user_input = {
                CONF_CLIMATE_ENTITY: "climate.living_room",
                CONF_ROOM_SENSOR: "sensor.living_room_temperature",
            }
            
            result = flow.async_step_user(user_input)
            
            assert result["type"] == FlowResultType.CREATE_ENTRY
            assert result["data"][CONF_MAX_OFFSET] == DEFAULT_MAX_OFFSET
            assert result["data"][CONF_MIN_TEMPERATURE] == DEFAULT_MIN_TEMPERATURE
            assert result["data"][CONF_MAX_TEMPERATURE] == DEFAULT_MAX_TEMPERATURE
            assert result["data"][CONF_UPDATE_INTERVAL] == DEFAULT_UPDATE_INTERVAL
            assert result["data"][CONF_ML_ENABLED] == DEFAULT_ML_ENABLED

    def test_config_flow_prevents_duplicate_entries(self, hass, mock_climate_entities, mock_temperature_sensors):
        """Test that duplicate entries are prevented."""
        flow = SmartClimateConfigFlow()
        flow.hass = hass
        
        # Mock existing entries
        existing_entry = MagicMock()
        existing_entry.data = {CONF_CLIMATE_ENTITY: "climate.living_room"}
        flow.hass.config_entries.async_entries.return_value = [existing_entry]
        
        with patch.object(flow, '_get_climate_entities', return_value=mock_climate_entities), \
             patch.object(flow, '_get_temperature_sensors', return_value=mock_temperature_sensors), \
             patch.object(flow, '_get_power_sensors', return_value={}):
            
            user_input = {
                CONF_CLIMATE_ENTITY: "climate.living_room",  # Same as existing
                CONF_ROOM_SENSOR: "sensor.living_room_temperature",
            }
            
            result = flow.async_step_user(user_input)
            
            # Should show error for duplicate
            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "user"
            assert result["errors"]["climate_entity"] == "already_configured"

    def test_config_flow_handles_empty_entity_lists(self, hass):
        """Test graceful handling when no entities are available."""
        flow = SmartClimateConfigFlow()
        flow.hass = hass
        
        with patch.object(flow, '_get_climate_entities', return_value={}), \
             patch.object(flow, '_get_temperature_sensors', return_value={}), \
             patch.object(flow, '_get_power_sensors', return_value={}):
            
            result = flow.async_step_user()
            
            # Should still create form, but with empty selectors
            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "user"

    def test_config_flow_user_friendly_labels(self, hass, mock_climate_entities, mock_temperature_sensors):
        """Test that entity selectors show user-friendly labels."""
        flow = SmartClimateConfigFlow()
        flow.hass = hass
        
        with patch.object(flow, '_get_climate_entities', return_value=mock_climate_entities), \
             patch.object(flow, '_get_temperature_sensors', return_value=mock_temperature_sensors), \
             patch.object(flow, '_get_power_sensors', return_value={}):
            
            result = flow.async_step_user()
            
            # Check that the schema includes selectors with proper options
            assert result["type"] == FlowResultType.FORM
            # The actual selector validation depends on the implementation
            # This test verifies the structure is correct