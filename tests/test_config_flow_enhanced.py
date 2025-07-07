"""ABOUTME: Enhanced configuration flow tests for Smart Climate Control.
Tests the expanded UI configuration options including mode-specific settings."""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_NAME

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
    CONF_AWAY_TEMPERATURE,
    CONF_SLEEP_OFFSET,
    CONF_BOOST_OFFSET,
    CONF_GRADUAL_ADJUSTMENT_RATE,
    CONF_FEEDBACK_DELAY,
    CONF_ENABLE_LEARNING,
    DEFAULT_AWAY_TEMPERATURE,
    DEFAULT_SLEEP_OFFSET,
    DEFAULT_BOOST_OFFSET,
    DEFAULT_GRADUAL_ADJUSTMENT_RATE,
    DEFAULT_FEEDBACK_DELAY,
    DEFAULT_ENABLE_LEARNING,
)
from custom_components.smart_climate.config_flow import SmartClimateConfigFlow


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock(spec=HomeAssistant)
    hass.data = {}
    hass.config_entries = Mock(spec=config_entries.ConfigEntries)
    hass.config_entries.async_entries.return_value = []
    
    # Mock states for entity selection
    states = []
    
    # Add climate entities
    climate1 = Mock()
    climate1.entity_id = "climate.living_room"
    climate1.attributes = {"friendly_name": "Living Room AC"}
    states.append(climate1)
    
    climate2 = Mock()
    climate2.entity_id = "climate.bedroom"
    climate2.attributes = {"friendly_name": "Bedroom AC"}
    states.append(climate2)
    
    # Add temperature sensors
    temp1 = Mock()
    temp1.entity_id = "sensor.room_temp"
    temp1.attributes = {"friendly_name": "Room Temperature", "device_class": "temperature"}
    states.append(temp1)
    
    temp2 = Mock()
    temp2.entity_id = "sensor.outdoor_temp"
    temp2.attributes = {"friendly_name": "Outdoor Temperature", "device_class": "temperature"}
    states.append(temp2)
    
    # Add power sensor
    power1 = Mock()
    power1.entity_id = "sensor.ac_power"
    power1.attributes = {"friendly_name": "AC Power", "device_class": "power"}
    states.append(power1)
    
    hass.states = Mock()
    hass.states.async_all.return_value = states
    hass.states.get.side_effect = lambda entity_id: next(
        (state for state in states if state.entity_id == entity_id), None
    )
    
    return hass


class TestConfigFlowEnhanced:
    """Test the enhanced config flow."""
    
    async def test_user_form_with_all_fields(self, mock_hass):
        """Test the user form shows all configuration fields."""
        flow = SmartClimateConfigFlow()
        flow.hass = mock_hass
        
        result = await flow.async_step_user()
        
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "user"
        
        # Check that all fields are in the schema
        schema_keys = list(result["data_schema"].schema.keys())
        field_names = [str(key) for key in schema_keys]
        
        # Basic fields
        assert "climate_entity" in field_names
        assert "room_sensor" in field_names
        assert "outdoor_sensor" in field_names
        assert "power_sensor" in field_names
        assert "max_offset" in field_names
        assert "min_temperature" in field_names
        assert "max_temperature" in field_names
        assert "update_interval" in field_names
        assert "ml_enabled" in field_names
        
        # Enhanced fields
        assert "away_temperature" in field_names
        assert "sleep_offset" in field_names
        assert "boost_offset" in field_names
        assert "gradual_adjustment_rate" in field_names
        assert "feedback_delay" in field_names
        assert "enable_learning" in field_names
    
    async def test_user_form_default_values(self, mock_hass):
        """Test the form shows correct default values for new fields."""
        flow = SmartClimateConfigFlow()
        flow.hass = mock_hass
        
        result = await flow.async_step_user()
        
        # Get the schema and check defaults
        schema = result["data_schema"].schema
        
        # Find the field with away_temperature key
        away_temp_field = next((k for k in schema if str(k) == "away_temperature"), None)
        assert away_temp_field is not None
        assert schema[away_temp_field].default() == DEFAULT_AWAY_TEMPERATURE
        
        sleep_offset_field = next((k for k in schema if str(k) == "sleep_offset"), None)
        assert sleep_offset_field is not None
        assert schema[sleep_offset_field].default() == DEFAULT_SLEEP_OFFSET
        
        boost_offset_field = next((k for k in schema if str(k) == "boost_offset"), None)
        assert boost_offset_field is not None
        assert schema[boost_offset_field].default() == DEFAULT_BOOST_OFFSET
        
        gradual_rate_field = next((k for k in schema if str(k) == "gradual_adjustment_rate"), None)
        assert gradual_rate_field is not None
        assert schema[gradual_rate_field].default() == DEFAULT_GRADUAL_ADJUSTMENT_RATE
        
        feedback_delay_field = next((k for k in schema if str(k) == "feedback_delay"), None)
        assert feedback_delay_field is not None
        assert schema[feedback_delay_field].default() == DEFAULT_FEEDBACK_DELAY
        
        enable_learning_field = next((k for k in schema if str(k) == "enable_learning"), None)
        assert enable_learning_field is not None
        assert schema[enable_learning_field].default() == DEFAULT_ENABLE_LEARNING
    
    async def test_user_form_submission_with_enhanced_fields(self, mock_hass):
        """Test form submission with all enhanced fields."""
        flow = SmartClimateConfigFlow()
        flow.hass = mock_hass
        
        user_input = {
            CONF_CLIMATE_ENTITY: "climate.living_room",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            CONF_OUTDOOR_SENSOR: "sensor.outdoor_temp",
            CONF_POWER_SENSOR: "sensor.ac_power",
            CONF_MAX_OFFSET: 6.0,
            CONF_MIN_TEMPERATURE: 18.0,
            CONF_MAX_TEMPERATURE: 28.0,
            CONF_UPDATE_INTERVAL: 120,
            CONF_ML_ENABLED: True,
            CONF_AWAY_TEMPERATURE: 20.0,
            CONF_SLEEP_OFFSET: 1.5,
            CONF_BOOST_OFFSET: -3.0,
            CONF_GRADUAL_ADJUSTMENT_RATE: 0.3,
            CONF_FEEDBACK_DELAY: 60,
            CONF_ENABLE_LEARNING: True,
        }
        
        result = await flow.async_step_user(user_input)
        
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["title"] == "Smart Climate Control"
        assert result["data"] == user_input
    
    async def test_away_temperature_validation(self, mock_hass):
        """Test that away temperature must be within min/max range."""
        flow = SmartClimateConfigFlow()
        flow.hass = mock_hass
        
        # Away temperature outside the min/max range
        user_input = {
            CONF_CLIMATE_ENTITY: "climate.living_room",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            CONF_MAX_OFFSET: 5.0,
            CONF_MIN_TEMPERATURE: 18.0,
            CONF_MAX_TEMPERATURE: 28.0,
            CONF_UPDATE_INTERVAL: 180,
            CONF_ML_ENABLED: True,
            CONF_AWAY_TEMPERATURE: 35.0,  # Outside max temperature
            CONF_SLEEP_OFFSET: 1.0,
            CONF_BOOST_OFFSET: -2.0,
            CONF_GRADUAL_ADJUSTMENT_RATE: 0.5,
            CONF_FEEDBACK_DELAY: 45,
            CONF_ENABLE_LEARNING: False,
        }
        
        result = await flow.async_step_user(user_input)
        
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["errors"]["away_temperature"] == "away_temperature_out_of_range"
    
    async def test_options_flow_with_enhanced_fields(self, mock_hass):
        """Test the options flow includes all enhanced fields."""
        # Create a config entry
        config_entry = config_entries.ConfigEntry(
            version=1,
            domain=DOMAIN,
            title="Smart Climate Control",
            data={
                CONF_CLIMATE_ENTITY: "climate.living_room",
                CONF_ROOM_SENSOR: "sensor.room_temp",
                CONF_MAX_OFFSET: 5.0,
                CONF_MIN_TEMPERATURE: 16.0,
                CONF_MAX_TEMPERATURE: 30.0,
                CONF_UPDATE_INTERVAL: 180,
                CONF_ML_ENABLED: True,
                CONF_AWAY_TEMPERATURE: 19.0,
                CONF_SLEEP_OFFSET: 1.0,
                CONF_BOOST_OFFSET: -2.0,
                CONF_GRADUAL_ADJUSTMENT_RATE: 0.5,
                CONF_FEEDBACK_DELAY: 45,
                CONF_ENABLE_LEARNING: False,
            },
            source="user",
            entry_id="test_entry_id",
            unique_id="test_unique_id",
            options={},
        )
        
        flow = SmartClimateConfigFlow.async_get_options_flow(config_entry)
        flow.hass = mock_hass
        
        result = await flow.async_step_init()
        
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "init"
        
        # Check that all fields are in the options schema
        schema_keys = list(result["data_schema"].schema.keys())
        field_names = [str(key) for key in schema_keys]
        
        # All configurable fields should be in options
        assert "max_offset" in field_names
        assert "min_temperature" in field_names
        assert "max_temperature" in field_names
        assert "update_interval" in field_names
        assert "ml_enabled" in field_names
        assert "away_temperature" in field_names
        assert "sleep_offset" in field_names
        assert "boost_offset" in field_names
        assert "gradual_adjustment_rate" in field_names
        assert "feedback_delay" in field_names
        assert "enable_learning" in field_names
    
    async def test_options_flow_update_enhanced_fields(self, mock_hass):
        """Test updating configuration through options flow."""
        # Create a config entry
        config_entry = config_entries.ConfigEntry(
            version=1,
            domain=DOMAIN,
            title="Smart Climate Control",
            data={
                CONF_CLIMATE_ENTITY: "climate.living_room",
                CONF_ROOM_SENSOR: "sensor.room_temp",
                CONF_MAX_OFFSET: 5.0,
                CONF_MIN_TEMPERATURE: 16.0,
                CONF_MAX_TEMPERATURE: 30.0,
                CONF_UPDATE_INTERVAL: 180,
                CONF_ML_ENABLED: True,
                CONF_AWAY_TEMPERATURE: 19.0,
                CONF_SLEEP_OFFSET: 1.0,
                CONF_BOOST_OFFSET: -2.0,
                CONF_GRADUAL_ADJUSTMENT_RATE: 0.5,
                CONF_FEEDBACK_DELAY: 45,
                CONF_ENABLE_LEARNING: False,
            },
            source="user",
            entry_id="test_entry_id",
            unique_id="test_unique_id",
            options={},
        )
        
        flow = SmartClimateConfigFlow.async_get_options_flow(config_entry)
        flow.hass = mock_hass
        
        # Update some values
        user_input = {
            CONF_MAX_OFFSET: 7.0,
            CONF_MIN_TEMPERATURE: 17.0,
            CONF_MAX_TEMPERATURE: 29.0,
            CONF_UPDATE_INTERVAL: 90,
            CONF_ML_ENABLED: False,
            CONF_AWAY_TEMPERATURE: 21.0,
            CONF_SLEEP_OFFSET: 2.0,
            CONF_BOOST_OFFSET: -4.0,
            CONF_GRADUAL_ADJUSTMENT_RATE: 0.2,
            CONF_FEEDBACK_DELAY: 30,
            CONF_ENABLE_LEARNING: True,
        }
        
        result = await flow.async_step_init(user_input)
        
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["data"] == user_input
    
    async def test_gradual_adjustment_rate_limits(self, mock_hass):
        """Test gradual adjustment rate has sensible limits."""
        flow = SmartClimateConfigFlow()
        flow.hass = mock_hass
        
        result = await flow.async_step_user()
        
        # Find the gradual_adjustment_rate field in the schema
        schema = result["data_schema"].schema
        gradual_rate_field = next((k for k in schema if str(k) == "gradual_adjustment_rate"), None)
        
        # Check the selector configuration
        assert gradual_rate_field is not None
        selector = gradual_rate_field.description["selector"]["number"]
        assert selector["min"] == 0.1
        assert selector["max"] == 2.0
        assert selector["step"] == 0.1
        assert selector["unit_of_measurement"] == "°C"
    
    async def test_feedback_delay_limits(self, mock_hass):
        """Test feedback delay has appropriate limits."""
        flow = SmartClimateConfigFlow()
        flow.hass = mock_hass
        
        result = await flow.async_step_user()
        
        # Find the feedback_delay field in the schema
        schema = result["data_schema"].schema
        feedback_delay_field = next((k for k in schema if str(k) == "feedback_delay"), None)
        
        # Check the selector configuration
        assert feedback_delay_field is not None
        selector = feedback_delay_field.description["selector"]["number"]
        assert selector["min"] == 10
        assert selector["max"] == 300
        assert selector["step"] == 5
        assert selector["unit_of_measurement"] == "seconds"
    
    async def test_offset_fields_validation(self, mock_hass):
        """Test that sleep and boost offsets have appropriate limits."""
        flow = SmartClimateConfigFlow()
        flow.hass = mock_hass
        
        result = await flow.async_step_user()
        
        # Find the offset fields in the schema
        schema = result["data_schema"].schema
        
        sleep_offset_field = next((k for k in schema if str(k) == "sleep_offset"), None)
        assert sleep_offset_field is not None
        selector = sleep_offset_field.description["selector"]["number"]
        assert selector["min"] == -5.0
        assert selector["max"] == 5.0
        assert selector["step"] == 0.5
        assert selector["unit_of_measurement"] == "°C"
        
        boost_offset_field = next((k for k in schema if str(k) == "boost_offset"), None)
        assert boost_offset_field is not None
        selector = boost_offset_field.description["selector"]["number"]
        assert selector["min"] == -10.0
        assert selector["max"] == 0.0
        assert selector["step"] == 0.5
        assert selector["unit_of_measurement"] == "°C"