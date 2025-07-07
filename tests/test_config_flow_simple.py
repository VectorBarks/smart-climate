"""Simple test config flow for Smart Climate Control."""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import sys

# Mock Home Assistant modules before imports
mock_selector = MagicMock()
mock_selector.SelectSelector = MagicMock
mock_selector.SelectSelectorConfig = MagicMock
mock_selector.SelectSelectorMode = MagicMock()
mock_selector.SelectSelectorMode.DROPDOWN = "dropdown"
mock_selector.SelectOptionDict = dict
mock_selector.NumberSelector = MagicMock
mock_selector.NumberSelectorConfig = MagicMock
mock_selector.NumberSelectorMode = MagicMock()
mock_selector.NumberSelectorMode.BOX = "box"
mock_selector.BooleanSelector = MagicMock
sys.modules['homeassistant.helpers.selector'] = mock_selector

# Mock other HA modules
sys.modules['homeassistant.helpers.entity_registry'] = MagicMock()
sys.modules['homeassistant.helpers.device_registry'] = MagicMock()

# Mock config_entries
mock_config_entries = MagicMock()
mock_config_entries.ConfigFlow = MagicMock
mock_config_entries.OptionsFlow = MagicMock
mock_config_entries.ConfigEntry = MagicMock
sys.modules['homeassistant.config_entries'] = mock_config_entries

# Mock data_entry_flow
mock_data_entry_flow = MagicMock()
mock_data_entry_flow.FlowResult = dict
sys.modules['homeassistant.data_entry_flow'] = mock_data_entry_flow

from custom_components.smart_climate.config_flow import SmartClimateConfigFlow
from custom_components.smart_climate.const import (
    DOMAIN,
    CONF_CLIMATE_ENTITY,
    CONF_ROOM_SENSOR,
    CONF_OUTDOOR_SENSOR,
    CONF_POWER_SENSOR,
    DEFAULT_MAX_OFFSET,
    DEFAULT_MIN_TEMPERATURE,
    DEFAULT_MAX_TEMPERATURE,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_ML_ENABLED,
)


class TestSmartClimateConfigFlow:
    """Test the Smart Climate config flow."""

    def test_config_flow_initialization(self):
        """Test that the config flow can be initialized."""
        flow = SmartClimateConfigFlow()
        assert flow is not None
        assert flow.VERSION == 1
        assert flow.domain == DOMAIN

    def test_async_step_user_creates_form(self):
        """Test that async_step_user creates a form when called without input."""
        async def run_test():
            # Mock hass
            mock_hass = MagicMock()
            mock_hass.states.async_all.return_value = [
                MagicMock(entity_id="climate.test", attributes={"friendly_name": "Test Climate"}),
                MagicMock(entity_id="sensor.test_temp", attributes={"friendly_name": "Test Temp", "device_class": "temperature"}),
            ]
            mock_hass.config_entries.async_entries.return_value = []
            
            flow = SmartClimateConfigFlow()
            flow.hass = mock_hass
            
            # Mock the base class methods
            flow.async_show_form = MagicMock(return_value={"type": "form", "step_id": "user"})
            
            result = await flow.async_step_user()
            
            assert result["type"] == "form"
            assert result["step_id"] == "user"
            flow.async_show_form.assert_called_once()
        
        asyncio.run(run_test())

    def test_async_step_user_validates_input(self):
        """Test that async_step_user validates user input correctly."""
        async def run_test():
            # Mock hass with state
            mock_state = MagicMock()
            mock_hass = MagicMock()
            mock_hass.states.get.return_value = mock_state
            mock_hass.states.async_all.return_value = []
            mock_hass.config_entries.async_entries.return_value = []
            
            flow = SmartClimateConfigFlow()
            flow.hass = mock_hass
            
            # Mock the base class method
            flow.async_create_entry = MagicMock(return_value={"type": "create_entry", "title": "Smart Climate Control"})
            
            user_input = {
                CONF_CLIMATE_ENTITY: "climate.test",
                CONF_ROOM_SENSOR: "sensor.test_temp",
            }
            
            result = await flow.async_step_user(user_input)
            
            # Should create entry with validated input
            assert result["type"] == "create_entry"
            flow.async_create_entry.assert_called_once()
        
        asyncio.run(run_test())

    def test_validate_input_checks_entity_existence(self):
        """Test that _validate_input checks if entities exist."""
        async def run_test():
            mock_hass = MagicMock()
            mock_hass.states.get.return_value = MagicMock()  # Entity exists
            
            flow = SmartClimateConfigFlow()
            flow.hass = mock_hass
            
            user_input = {
                CONF_CLIMATE_ENTITY: "climate.test",
                CONF_ROOM_SENSOR: "sensor.test",
            }
            
            result = await flow._validate_input(user_input)
            
            # Should return validated data
            assert result[CONF_CLIMATE_ENTITY] == "climate.test"
            assert result[CONF_ROOM_SENSOR] == "sensor.test"
            
            # Should have defaults applied
            assert result[CONF_MAX_OFFSET] == DEFAULT_MAX_OFFSET
            assert result[CONF_MIN_TEMPERATURE] == DEFAULT_MIN_TEMPERATURE
            assert result[CONF_MAX_TEMPERATURE] == DEFAULT_MAX_TEMPERATURE
            assert result[CONF_UPDATE_INTERVAL] == DEFAULT_UPDATE_INTERVAL
            assert result[CONF_ML_ENABLED] == DEFAULT_ML_ENABLED
        
        asyncio.run(run_test())

    def test_entity_exists_validates_domain(self):
        """Test that _entity_exists validates entity domain correctly."""
        async def run_test():
            mock_hass = MagicMock()
            mock_state = MagicMock()
            mock_hass.states.get.return_value = mock_state
            
            flow = SmartClimateConfigFlow()
            flow.hass = mock_hass
            
            # Test climate entity
            result = await flow._entity_exists("climate.test", "climate")
            assert result is True
            
            # Test wrong domain
            result = await flow._entity_exists("sensor.test", "climate")
            assert result is False
            
            # Test non-existent entity
            mock_hass.states.get.return_value = None
            result = await flow._entity_exists("climate.nonexistent", "climate")
            assert result is False
        
        asyncio.run(run_test())

    def test_already_configured_prevents_duplicates(self):
        """Test that _already_configured prevents duplicate entries."""
        async def run_test():
            mock_entry = MagicMock()
            mock_entry.data = {CONF_CLIMATE_ENTITY: "climate.existing"}
            
            mock_hass = MagicMock()
            mock_hass.config_entries.async_entries.return_value = [mock_entry]
            
            flow = SmartClimateConfigFlow()
            flow.hass = mock_hass
            
            # Test existing entity
            result = await flow._already_configured("climate.existing")
            assert result is True
            
            # Test new entity
            result = await flow._already_configured("climate.new")
            assert result is False
        
        asyncio.run(run_test())

    def test_get_climate_entities(self):
        """Test that _get_climate_entities returns climate entities."""
        async def run_test():
            mock_state = MagicMock()
            mock_state.entity_id = "climate.test"
            mock_state.attributes = {"friendly_name": "Test Climate"}
            
            mock_hass = MagicMock()
            mock_hass.states.async_all.return_value = [mock_state]
            
            flow = SmartClimateConfigFlow()
            flow.hass = mock_hass
            
            result = await flow._get_climate_entities()
            
            assert "climate.test" in result
            assert result["climate.test"] == "Test Climate"
        
        asyncio.run(run_test())

    def test_get_temperature_sensors(self):
        """Test that _get_temperature_sensors returns temperature sensors."""
        async def run_test():
            mock_state = MagicMock()
            mock_state.entity_id = "sensor.temp"
            mock_state.attributes = {"friendly_name": "Temperature Sensor", "device_class": "temperature"}
            
            mock_hass = MagicMock()
            mock_hass.states.async_all.return_value = [mock_state]
            
            flow = SmartClimateConfigFlow()
            flow.hass = mock_hass
            
            result = await flow._get_temperature_sensors()
            
            assert "sensor.temp" in result
            assert result["sensor.temp"] == "Temperature Sensor"
        
        asyncio.run(run_test())

    def test_get_power_sensors(self):
        """Test that _get_power_sensors returns power sensors."""
        async def run_test():
            mock_state = MagicMock()
            mock_state.entity_id = "sensor.power"
            mock_state.attributes = {"friendly_name": "Power Sensor", "device_class": "power"}
            
            mock_hass = MagicMock()
            mock_hass.states.async_all.return_value = [mock_state]
            
            flow = SmartClimateConfigFlow()
            flow.hass = mock_hass
            
            result = await flow._get_power_sensors()
            
            assert "sensor.power" in result
            assert result["sensor.power"] == "Power Sensor"
        
        asyncio.run(run_test())