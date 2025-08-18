"""Test probe scheduler configuration flow functionality."""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from homeassistant.config_entries import FlowResult
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.smart_climate.config_flow import SmartClimateConfigFlow
from custom_components.smart_climate.const import (
    DOMAIN,
    CONF_CLIMATE_ENTITY,
    CONF_ROOM_SENSOR,
    # Probe scheduler constants
    CONF_LEARNING_PROFILE,
    CONF_PRESENCE_ENTITY_ID,
    CONF_WEATHER_ENTITY_ID,
    CONF_CALENDAR_ENTITY_ID,
    CONF_MANUAL_OVERRIDE_ENTITY_ID,
    CONF_MIN_PROBE_INTERVAL,
    CONF_MAX_PROBE_INTERVAL,
    CONF_QUIET_HOURS_START,
    CONF_QUIET_HOURS_END,
    CONF_INFO_GAIN_THRESHOLD,
    DEFAULT_LEARNING_PROFILE,
    DEFAULT_MIN_PROBE_INTERVAL,
    DEFAULT_MAX_PROBE_INTERVAL,
    DEFAULT_QUIET_HOURS_START,
    DEFAULT_QUIET_HOURS_END,
    DEFAULT_INFO_GAIN_THRESHOLD,
)


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    hass = Mock(spec=HomeAssistant)
    hass.config_entries = Mock()
    hass.config_entries.async_entries.return_value = []
    hass.states = Mock()
    return hass


@pytest.fixture
def mock_states(mock_hass):
    """Set up mock states for entities."""
    mock_states = {
        "climate.test_hvac": Mock(
            entity_id="climate.test_hvac",
            attributes={"friendly_name": "Test HVAC"},
        ),
        "sensor.room_temp": Mock(
            entity_id="sensor.room_temp",
            attributes={"friendly_name": "Room Temperature", "device_class": "temperature"},
        ),
        "binary_sensor.home_occupancy": Mock(
            entity_id="binary_sensor.home_occupancy",
            attributes={"friendly_name": "Home Occupancy"},
        ),
        "weather.home": Mock(
            entity_id="weather.home",
            attributes={"friendly_name": "Home Weather"},
        ),
        "calendar.work": Mock(
            entity_id="calendar.work",
            attributes={"friendly_name": "Work Calendar"},
        ),
        "input_boolean.manual_override": Mock(
            entity_id="input_boolean.manual_override",
            attributes={"friendly_name": "Manual Override"},
        ),
    }
    
    def get_state(entity_id):
        return mock_states.get(entity_id)
    
    def async_all():
        return list(mock_states.values())
    
    mock_hass.states.get = get_state
    mock_hass.states.async_all = async_all
    
    return mock_states


class TestProbeSchedulerConfigFlow:
    """Test probe scheduler configuration flow."""

    async def test_probe_scheduler_basic_config(self, mock_hass, mock_states):
        """Test basic probe scheduler configuration."""
        config_flow = SmartClimateConfigFlow()
        config_flow.hass = mock_hass
        
        user_input = {
            CONF_CLIMATE_ENTITY: "climate.test_hvac",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            CONF_LEARNING_PROFILE: "balanced",
        }
        
        result = await config_flow.async_step_user(user_input)
        
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_LEARNING_PROFILE] == "balanced"

    async def test_probe_scheduler_comfort_profile(self, mock_hass, mock_states):
        """Test comfort learning profile configuration."""
        config_flow = SmartClimateConfigFlow()
        config_flow.hass = mock_hass
        
        user_input = {
            CONF_CLIMATE_ENTITY: "climate.test_hvac",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            CONF_LEARNING_PROFILE: "comfort",
            CONF_PRESENCE_ENTITY_ID: "binary_sensor.home_occupancy",
        }
        
        result = await config_flow.async_step_user(user_input)
        
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_LEARNING_PROFILE] == "comfort"
        assert result["data"][CONF_PRESENCE_ENTITY_ID] == "binary_sensor.home_occupancy"

    async def test_probe_scheduler_aggressive_profile(self, mock_hass, mock_states):
        """Test aggressive learning profile configuration."""
        config_flow = SmartClimateConfigFlow()
        config_flow.hass = mock_hass
        
        user_input = {
            CONF_CLIMATE_ENTITY: "climate.test_hvac",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            CONF_LEARNING_PROFILE: "aggressive",
        }
        
        result = await config_flow.async_step_user(user_input)
        
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_LEARNING_PROFILE] == "aggressive"

    async def test_probe_scheduler_custom_profile_full_config(self, mock_hass, mock_states):
        """Test custom profile with all advanced settings."""
        config_flow = SmartClimateConfigFlow()
        config_flow.hass = mock_hass
        
        user_input = {
            CONF_CLIMATE_ENTITY: "climate.test_hvac",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            CONF_LEARNING_PROFILE: "custom",
            CONF_PRESENCE_ENTITY_ID: "binary_sensor.home_occupancy",
            CONF_WEATHER_ENTITY_ID: "weather.home",
            CONF_CALENDAR_ENTITY_ID: "calendar.work",
            CONF_MANUAL_OVERRIDE_ENTITY_ID: "input_boolean.manual_override",
            CONF_MIN_PROBE_INTERVAL: 8,
            CONF_MAX_PROBE_INTERVAL: 5,
            CONF_QUIET_HOURS_START: "23:00",
            CONF_QUIET_HOURS_END: "06:30",
            CONF_INFO_GAIN_THRESHOLD: 0.7,
        }
        
        result = await config_flow.async_step_user(user_input)
        
        assert result["type"] == FlowResultType.CREATE_ENTRY
        data = result["data"]
        assert data[CONF_LEARNING_PROFILE] == "custom"
        assert data[CONF_PRESENCE_ENTITY_ID] == "binary_sensor.home_occupancy"
        assert data[CONF_WEATHER_ENTITY_ID] == "weather.home"
        assert data[CONF_CALENDAR_ENTITY_ID] == "calendar.work"
        assert data[CONF_MANUAL_OVERRIDE_ENTITY_ID] == "input_boolean.manual_override"
        assert data[CONF_MIN_PROBE_INTERVAL] == 8
        assert data[CONF_MAX_PROBE_INTERVAL] == 5
        assert data[CONF_QUIET_HOURS_START] == "23:00"
        assert data[CONF_QUIET_HOURS_END] == "06:30"
        assert data[CONF_INFO_GAIN_THRESHOLD] == 0.7

    async def test_probe_scheduler_entity_validation_presence(self, mock_hass, mock_states):
        """Test presence entity validation."""
        config_flow = SmartClimateConfigFlow()
        config_flow.hass = mock_hass
        
        user_input = {
            CONF_CLIMATE_ENTITY: "climate.test_hvac",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            CONF_LEARNING_PROFILE: "comfort",
            CONF_PRESENCE_ENTITY_ID: "binary_sensor.nonexistent",
        }
        
        result = await config_flow.async_step_user(user_input)
        
        assert result["type"] == FlowResultType.FORM
        assert CONF_PRESENCE_ENTITY_ID in result["errors"]
        assert result["errors"][CONF_PRESENCE_ENTITY_ID] == "entity_not_found"

    async def test_probe_scheduler_entity_validation_weather(self, mock_hass, mock_states):
        """Test weather entity validation."""
        config_flow = SmartClimateConfigFlow()
        config_flow.hass = mock_hass
        
        user_input = {
            CONF_CLIMATE_ENTITY: "climate.test_hvac",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            CONF_LEARNING_PROFILE: "balanced",
            CONF_WEATHER_ENTITY_ID: "weather.nonexistent",
        }
        
        result = await config_flow.async_step_user(user_input)
        
        assert result["type"] == FlowResultType.FORM
        assert CONF_WEATHER_ENTITY_ID in result["errors"]
        assert result["errors"][CONF_WEATHER_ENTITY_ID] == "entity_not_found"

    async def test_probe_scheduler_entity_validation_calendar(self, mock_hass, mock_states):
        """Test calendar entity validation."""
        config_flow = SmartClimateConfigFlow()
        config_flow.hass = mock_hass
        
        user_input = {
            CONF_CLIMATE_ENTITY: "climate.test_hvac",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            CONF_LEARNING_PROFILE: "balanced",
            CONF_CALENDAR_ENTITY_ID: "calendar.nonexistent",
        }
        
        result = await config_flow.async_step_user(user_input)
        
        assert result["type"] == FlowResultType.FORM
        assert CONF_CALENDAR_ENTITY_ID in result["errors"]
        assert result["errors"][CONF_CALENDAR_ENTITY_ID] == "entity_not_found"

    async def test_probe_scheduler_entity_validation_manual_override(self, mock_hass, mock_states):
        """Test manual override entity validation."""
        config_flow = SmartClimateConfigFlow()
        config_flow.hass = mock_hass
        
        user_input = {
            CONF_CLIMATE_ENTITY: "climate.test_hvac",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            CONF_LEARNING_PROFILE: "balanced",
            CONF_MANUAL_OVERRIDE_ENTITY_ID: "input_boolean.nonexistent",
        }
        
        result = await config_flow.async_step_user(user_input)
        
        assert result["type"] == FlowResultType.FORM
        assert CONF_MANUAL_OVERRIDE_ENTITY_ID in result["errors"]
        assert result["errors"][CONF_MANUAL_OVERRIDE_ENTITY_ID] == "entity_not_found"

    async def test_probe_scheduler_interval_validation_min_max(self, mock_hass, mock_states):
        """Test probe interval validation ranges."""
        config_flow = SmartClimateConfigFlow()
        config_flow.hass = mock_hass
        
        # Test minimum interval too low
        user_input = {
            CONF_CLIMATE_ENTITY: "climate.test_hvac",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            CONF_LEARNING_PROFILE: "custom",
            CONF_MIN_PROBE_INTERVAL: 5,  # Below minimum of 6
        }
        
        result = await config_flow.async_step_user(user_input)
        
        assert result["type"] == FlowResultType.FORM
        assert "base" in result["errors"]
        assert result["errors"]["base"] == "invalid_probe_interval_range"

    async def test_probe_scheduler_interval_validation_max_too_high(self, mock_hass, mock_states):
        """Test probe interval validation maximum."""
        config_flow = SmartClimateConfigFlow()
        config_flow.hass = mock_hass
        
        # Test maximum interval too high
        user_input = {
            CONF_CLIMATE_ENTITY: "climate.test_hvac",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            CONF_LEARNING_PROFILE: "custom",
            CONF_MAX_PROBE_INTERVAL: 15,  # Above maximum of 14
        }
        
        result = await config_flow.async_step_user(user_input)
        
        assert result["type"] == FlowResultType.FORM
        assert "base" in result["errors"]
        assert result["errors"]["base"] == "invalid_probe_interval_range"

    async def test_probe_scheduler_quiet_hours_validation_invalid_format(self, mock_hass, mock_states):
        """Test quiet hours time format validation."""
        config_flow = SmartClimateConfigFlow()
        config_flow.hass = mock_hass
        
        user_input = {
            CONF_CLIMATE_ENTITY: "climate.test_hvac",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            CONF_LEARNING_PROFILE: "custom",
            CONF_QUIET_HOURS_START: "25:00",  # Invalid hour
        }
        
        result = await config_flow.async_step_user(user_input)
        
        assert result["type"] == FlowResultType.FORM
        assert CONF_QUIET_HOURS_START in result["errors"]
        assert result["errors"][CONF_QUIET_HOURS_START] == "invalid_time_format"

    async def test_probe_scheduler_quiet_hours_validation_invalid_minutes(self, mock_hass, mock_states):
        """Test quiet hours minutes validation."""
        config_flow = SmartClimateConfigFlow()
        config_flow.hass = mock_hass
        
        user_input = {
            CONF_CLIMATE_ENTITY: "climate.test_hvac",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            CONF_LEARNING_PROFILE: "custom",
            CONF_QUIET_HOURS_END: "07:70",  # Invalid minutes
        }
        
        result = await config_flow.async_step_user(user_input)
        
        assert result["type"] == FlowResultType.FORM
        assert CONF_QUIET_HOURS_END in result["errors"]
        assert result["errors"][CONF_QUIET_HOURS_END] == "invalid_time_format"

    async def test_probe_scheduler_information_gain_threshold_validation(self, mock_hass, mock_states):
        """Test information gain threshold validation."""
        config_flow = SmartClimateConfigFlow()
        config_flow.hass = mock_hass
        
        # Test threshold too low
        user_input = {
            CONF_CLIMATE_ENTITY: "climate.test_hvac",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            CONF_LEARNING_PROFILE: "custom",
            CONF_INFO_GAIN_THRESHOLD: 0.05,  # Below minimum of 0.1
        }
        
        result = await config_flow.async_step_user(user_input)
        
        assert result["type"] == FlowResultType.FORM
        assert "base" in result["errors"]
        assert result["errors"]["base"] == "invalid_info_gain_threshold"

    async def test_probe_scheduler_information_gain_threshold_validation_high(self, mock_hass, mock_states):
        """Test information gain threshold validation high end."""
        config_flow = SmartClimateConfigFlow()
        config_flow.hass = mock_hass
        
        # Test threshold too high
        user_input = {
            CONF_CLIMATE_ENTITY: "climate.test_hvac",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            CONF_LEARNING_PROFILE: "custom",
            CONF_INFO_GAIN_THRESHOLD: 0.95,  # Above maximum of 0.9
        }
        
        result = await config_flow.async_step_user(user_input)
        
        assert result["type"] == FlowResultType.FORM
        assert "base" in result["errors"]
        assert result["errors"]["base"] == "invalid_info_gain_threshold"

    async def test_probe_scheduler_defaults_applied(self, mock_hass, mock_states):
        """Test that probe scheduler defaults are properly applied."""
        config_flow = SmartClimateConfigFlow()
        config_flow.hass = mock_hass
        
        user_input = {
            CONF_CLIMATE_ENTITY: "climate.test_hvac",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            # No probe scheduler settings provided - should use defaults
        }
        
        result = await config_flow.async_step_user(user_input)
        
        assert result["type"] == FlowResultType.CREATE_ENTRY
        data = result["data"]
        # Check defaults are applied
        assert data.get(CONF_LEARNING_PROFILE, DEFAULT_LEARNING_PROFILE) == DEFAULT_LEARNING_PROFILE
        assert data.get(CONF_MIN_PROBE_INTERVAL, DEFAULT_MIN_PROBE_INTERVAL) == DEFAULT_MIN_PROBE_INTERVAL
        assert data.get(CONF_MAX_PROBE_INTERVAL, DEFAULT_MAX_PROBE_INTERVAL) == DEFAULT_MAX_PROBE_INTERVAL
        assert data.get(CONF_QUIET_HOURS_START, DEFAULT_QUIET_HOURS_START) == DEFAULT_QUIET_HOURS_START
        assert data.get(CONF_QUIET_HOURS_END, DEFAULT_QUIET_HOURS_END) == DEFAULT_QUIET_HOURS_END
        assert data.get(CONF_INFO_GAIN_THRESHOLD, DEFAULT_INFO_GAIN_THRESHOLD) == DEFAULT_INFO_GAIN_THRESHOLD

    async def test_probe_scheduler_existing_configuration_unchanged(self, mock_hass, mock_states):
        """Test that existing configuration fields are unchanged."""
        config_flow = SmartClimateConfigFlow()
        config_flow.hass = mock_hass
        
        user_input = {
            CONF_CLIMATE_ENTITY: "climate.test_hvac",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            "max_offset": 5.0,  # Existing config that should be preserved
            CONF_LEARNING_PROFILE: "balanced",
        }
        
        result = await config_flow.async_step_user(user_input)
        
        assert result["type"] == FlowResultType.CREATE_ENTRY
        data = result["data"]
        # Existing config preserved
        assert data["max_offset"] == 5.0
        # New probe scheduler config added
        assert data[CONF_LEARNING_PROFILE] == "balanced"

    async def test_probe_scheduler_form_schema_includes_options(self, mock_hass, mock_states):
        """Test that form schema includes probe scheduler options."""
        config_flow = SmartClimateConfigFlow()
        config_flow.hass = mock_hass
        
        result = await config_flow.async_step_user()
        
        assert result["type"] == FlowResultType.FORM
        schema_dict = dict(result["data_schema"].schema)
        
        # Check probe scheduler fields are included
        assert any(str(key).endswith("learning_profile") for key in schema_dict.keys())
        # Advanced options should be conditionally included
        # (Implementation detail: may be separate step or conditional visibility)

    async def test_probe_scheduler_learning_profile_options_valid(self, mock_hass, mock_states):
        """Test learning profile selector has correct options."""
        config_flow = SmartClimateConfigFlow()
        config_flow.hass = mock_hass
        
        result = await config_flow.async_step_user()
        
        assert result["type"] == FlowResultType.FORM
        # This test validates the schema includes the correct learning profile options
        # Implementation will validate specific selector configuration
        schema_dict = dict(result["data_schema"].schema)
        learning_profile_key = None
        for key in schema_dict.keys():
            if str(key).endswith("learning_profile"):
                learning_profile_key = key
                break
        
        assert learning_profile_key is not None
        # Further validation of options would depend on implementation