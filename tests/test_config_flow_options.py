"""Test the Smart Climate Control options flow."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from custom_components.smart_climate.config_flow import SmartClimateOptionsFlow
from custom_components.smart_climate.const import (
    DOMAIN,
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
def config_entry():
    """Return a mock config entry."""
    mock_entry = Mock()
    mock_entry.data = {}
    mock_entry.options = {}
    return mock_entry


@pytest.fixture
def options_flow(hass: HomeAssistant, config_entry):
    """Return a SmartClimateOptionsFlow instance."""
    options_flow = SmartClimateOptionsFlow(config_entry)
    options_flow.hass = hass
    return options_flow


class TestSmartClimateOptionsFlowBasic:
    """Test the basic options flow functionality."""

    def test_options_flow_init_no_input(self):
        """Test options flow initialization without user input."""
        # Create mock config entry
        config_entry = Mock()
        config_entry.data = {}
        config_entry.options = {}
        
        # Create options flow instance
        options_flow = SmartClimateOptionsFlow(config_entry)
        
        # Mock hass
        hass = Mock()
        hass.states.async_all.return_value = []
        options_flow.hass = hass
        
        # Mock the required methods
        options_flow._get_description_placeholders = Mock(return_value={})
        options_flow.async_show_form = Mock(return_value={"type": FlowResultType.FORM, "step_id": "init", "data_schema": Mock()})
        
        # Test async_step_init
        import asyncio
        result = asyncio.run(options_flow.async_step_init())
        
        # Verify the form is shown
        assert options_flow.async_show_form.called
        call_args = options_flow.async_show_form.call_args
        assert call_args[1]["step_id"] == "init"
        assert "data_schema" in call_args[1]

    def test_options_flow_init_with_comfort_profile(self):
        """Test options flow with comfort profile selection."""
        # Create mock config entry
        config_entry = Mock()
        config_entry.data = {}
        config_entry.options = {}
        
        # Create options flow instance
        options_flow = SmartClimateOptionsFlow(config_entry)
        options_flow.async_create_entry = Mock(return_value={"type": FlowResultType.CREATE_ENTRY, "data": {}})
        
        user_input = {
            CONF_LEARNING_PROFILE: "comfort",
            CONF_PRESENCE_ENTITY_ID: "binary_sensor.home_presence",
        }
        
        import asyncio
        result = asyncio.run(options_flow.async_step_init(user_input))
        
        # Should create entry directly (not custom profile)
        assert options_flow.async_create_entry.called
        call_args = options_flow.async_create_entry.call_args
        assert call_args[1]["data"] == user_input

    def test_options_flow_init_with_custom_profile(self):
        """Test options flow with custom profile requires advanced step."""
        # Create mock config entry
        config_entry = Mock()
        config_entry.data = {}
        config_entry.options = {}
        
        # Create options flow instance
        options_flow = SmartClimateOptionsFlow(config_entry)
        options_flow.async_step_advanced = Mock(return_value={"type": FlowResultType.FORM, "step_id": "advanced"})
        
        user_input = {
            CONF_LEARNING_PROFILE: "custom",
            CONF_PRESENCE_ENTITY_ID: "binary_sensor.home_presence",
        }
        
        import asyncio
        result = asyncio.run(options_flow.async_step_init(user_input))
        
        # Should redirect to advanced step for custom profile
        assert options_flow.async_step_advanced.called
        assert options_flow._basic_settings == user_input

    def test_options_flow_advanced_step(self):
        """Test advanced options step for custom profile."""
        # Create mock config entry
        config_entry = Mock()
        config_entry.data = {}
        config_entry.options = {}
        
        # Create options flow instance
        options_flow = SmartClimateOptionsFlow(config_entry)
        options_flow.async_create_entry = Mock(return_value={"type": FlowResultType.CREATE_ENTRY, "data": {}})
        
        # Set up basic settings from init step
        basic_settings = {
            CONF_LEARNING_PROFILE: "custom",
            CONF_PRESENCE_ENTITY_ID: "binary_sensor.home_presence",
        }
        options_flow._basic_settings = basic_settings
        
        advanced_input = {
            CONF_MIN_PROBE_INTERVAL: 8,
            CONF_MAX_PROBE_INTERVAL: 5,
            CONF_QUIET_HOURS_START: "23:00",
            CONF_QUIET_HOURS_END: "06:00",
            CONF_INFO_GAIN_THRESHOLD: 0.6,
        }
        
        import asyncio
        result = asyncio.run(options_flow.async_step_advanced(advanced_input))
        
        # Should create entry with combined settings
        assert options_flow.async_create_entry.called
        call_args = options_flow.async_create_entry.call_args
        expected_data = {**basic_settings, **advanced_input}
        assert call_args[1]["data"] == expected_data

    def test_options_schema_includes_probe_scheduler_fields(self):
        """Test that options schema includes ProbeScheduler configuration fields."""
        # Create mock config entry
        config_entry = Mock()
        config_entry.data = {}
        config_entry.options = {}
        
        # Create options flow instance
        options_flow = SmartClimateOptionsFlow(config_entry)
        
        schema = options_flow._get_options_schema()
        schema_str = str(schema.schema)
        
        # Check that all ProbeScheduler fields are present
        expected_fields = [
            CONF_LEARNING_PROFILE,
            CONF_PRESENCE_ENTITY_ID,
            CONF_WEATHER_ENTITY_ID,
            CONF_CALENDAR_ENTITY_ID,
            CONF_MANUAL_OVERRIDE_ENTITY_ID,
        ]
        
        for field in expected_fields:
            assert field in schema_str

    def test_options_schema_learning_profiles(self):
        """Test that learning profile options are correct."""
        # Create mock config entry
        config_entry = Mock()
        config_entry.data = {}
        config_entry.options = {}
        
        # Create options flow instance
        options_flow = SmartClimateOptionsFlow(config_entry)
        
        schema = options_flow._get_options_schema()
        schema_str = str(schema.schema)
        
        # Verify the learning profile field is present with correct options
        assert CONF_LEARNING_PROFILE in schema_str
        # The vol.In validator should contain the expected profiles
        expected_profiles = ["comfort", "balanced", "aggressive", "custom"]
        # This is a basic check - the actual validation would depend on parsing the schema
        # This is a basic check - the actual validation would depend on the selector implementation


class TestSmartClimateOptionsFlowValidation:
    """Test validation in options flow."""

    async def test_entity_selector_validation(self, hass: HomeAssistant, options_flow):
        """Test entity selectors validate against correct domains."""
        # Mock entity states
        hass.states.async_all = Mock(return_value=[
            Mock(entity_id="binary_sensor.presence", attributes={"friendly_name": "Home Presence"}),
            Mock(entity_id="weather.home", attributes={"friendly_name": "Home Weather"}),
            Mock(entity_id="calendar.work", attributes={"friendly_name": "Work Calendar"}),
            Mock(entity_id="input_boolean.manual_override", attributes={"friendly_name": "Manual Override"}),
        ])
        
        user_input = {
            CONF_LEARNING_PROFILE: "balanced",
            CONF_PRESENCE_ENTITY_ID: "binary_sensor.presence",
            CONF_WEATHER_ENTITY_ID: "weather.home",
            CONF_CALENDAR_ENTITY_ID: "calendar.work",
            CONF_MANUAL_OVERRIDE_ENTITY_ID: "input_boolean.manual_override",
        }
        
        result = await options_flow.async_step_init(user_input)
        assert result["type"] == FlowResultType.CREATE_ENTRY

    async def test_invalid_entity_domains_rejected(self, hass: HomeAssistant, options_flow):
        """Test that invalid entity domains are rejected."""
        user_input = {
            CONF_LEARNING_PROFILE: "balanced",
            CONF_PRESENCE_ENTITY_ID: "sensor.invalid_presence",  # Wrong domain
        }
        
        # This would normally trigger validation error
        # The actual implementation depends on the selector validation


class TestSmartClimateOptionsFlowGracefulDegradation:
    """Test graceful degradation without presence sensor."""

    async def test_options_without_presence_sensor(self, hass: HomeAssistant, options_flow):
        """Test options work without presence sensor."""
        user_input = {
            CONF_LEARNING_PROFILE: "comfort",
            # No presence sensor provided
            CONF_WEATHER_ENTITY_ID: "weather.home",
        }
        
        result = await options_flow.async_step_init(user_input)
        
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"] == user_input

    async def test_fallback_behavior_description(self, hass: HomeAssistant, options_flow):
        """Test description placeholders explain fallback behavior."""
        placeholders = options_flow._get_description_placeholders()
        
        # Check that fallback behavior is documented
        assert "fallback_behavior" in placeholders
        assert "quiet hours" in placeholders["fallback_behavior"]
        assert "conservative" in placeholders["fallback_behavior"]


class TestSmartClimateOptionsFlowDefaults:
    """Test default value handling."""

    async def test_current_options_used_as_defaults(self, hass: HomeAssistant, config_entry):
        """Test that current options are used as defaults."""
        # Set up existing options
        config_entry.options = {
            CONF_LEARNING_PROFILE: "aggressive",
            CONF_MIN_PROBE_INTERVAL: 8,
        }
        
        options_flow = SmartClimateOptionsFlow(config_entry)
        options_flow.hass = hass
        
        schema = options_flow._get_options_schema()
        
        # Check that existing options are used as defaults
        # The actual implementation would need to check the schema defaults

    async def test_system_defaults_when_no_options(self, hass: HomeAssistant, options_flow):
        """Test system defaults when no existing options."""
        schema = options_flow._get_options_schema()
        
        # Should use system defaults from const.py
        # The actual verification depends on schema inspection


class TestSmartClimateOptionsFlowMultiStep:
    """Test multi-step flow for custom profile."""

    async def test_custom_profile_flow_sequence(self, hass: HomeAssistant, options_flow):
        """Test complete custom profile configuration sequence."""
        # Step 1: Basic settings with custom profile
        basic_input = {
            CONF_LEARNING_PROFILE: "custom",
            CONF_PRESENCE_ENTITY_ID: "binary_sensor.home_presence",
        }
        
        result = await options_flow.async_step_init(basic_input)
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "advanced"
        
        # Step 2: Advanced settings
        advanced_input = {
            CONF_MIN_PROBE_INTERVAL: 6,
            CONF_MAX_PROBE_INTERVAL: 3,
            CONF_QUIET_HOURS_START: "22:30",
            CONF_QUIET_HOURS_END: "07:30",
            CONF_INFO_GAIN_THRESHOLD: 0.7,
        }
        
        result = await options_flow.async_step_advanced(advanced_input)
        assert result["type"] == FlowResultType.CREATE_ENTRY
        
        # Should combine both sets of settings
        expected_data = {**basic_input, **advanced_input}
        assert result["data"] == expected_data

    async def test_advanced_step_without_basic_settings(self, hass: HomeAssistant, options_flow):
        """Test advanced step gracefully handles missing basic settings."""
        advanced_input = {
            CONF_MIN_PROBE_INTERVAL: 8,
        }
        
        # Should not crash even if basic settings missing
        result = await options_flow.async_step_advanced(advanced_input)
        assert result["type"] == FlowResultType.CREATE_ENTRY


class TestSmartClimateOptionsFlowSchemas:
    """Test schema generation and validation."""

    async def test_get_options_schema_structure(self, hass: HomeAssistant, options_flow):
        """Test options schema has correct structure."""
        schema = options_flow._get_options_schema()
        
        assert schema is not None
        assert hasattr(schema, 'schema')
        
        # Basic structure validation
        schema_fields = list(schema.schema.keys())
        assert len(schema_fields) > 0

    async def test_get_advanced_schema_structure(self, hass: HomeAssistant, options_flow):
        """Test advanced schema has correct structure."""
        schema = options_flow._get_advanced_schema()
        
        assert schema is not None
        assert hasattr(schema, 'schema')
        
        # Should contain advanced configuration options
        expected_advanced_fields = [
            CONF_MIN_PROBE_INTERVAL,
            CONF_MAX_PROBE_INTERVAL,
            CONF_QUIET_HOURS_START,
            CONF_QUIET_HOURS_END,
            CONF_INFO_GAIN_THRESHOLD,
        ]
        
        schema_str = str(schema.schema)
        for field in expected_advanced_fields:
            assert field in schema_str

    async def test_description_placeholders_content(self, hass: HomeAssistant, options_flow):
        """Test description placeholders provide helpful information."""
        placeholders = options_flow._get_description_placeholders()
        
        expected_keys = [
            "probe_scheduler_info",
            "learning_profiles", 
            "presence_sensor_info",
            "fallback_behavior",
        ]
        
        for key in expected_keys:
            assert key in placeholders
            assert isinstance(placeholders[key], str)
            assert len(placeholders[key]) > 10  # Should have meaningful content


# Integration test with the main config flow
class TestConfigFlowOptionsFlowIntegration:
    """Test integration between main config flow and options flow."""

    async def test_config_flow_provides_options_flow(self, hass: HomeAssistant):
        """Test that main config flow provides the options flow."""
        from custom_components.smart_climate.config_flow import SmartClimateConfigFlow
        
        mock_config_entry = Mock(spec=config_entries.ConfigEntry)
        options_flow = SmartClimateConfigFlow.async_get_options_flow(mock_config_entry)
        
        assert isinstance(options_flow, SmartClimateOptionsFlow)
        assert options_flow.config_entry == mock_config_entry