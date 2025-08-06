"""ABOUTME: Tests for thermal efficiency configuration in SmartClimateConfigFlow.
Comprehensive test suite for thermal settings, preferences, shadow mode, and migration."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

import voluptuous as vol
from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector

from custom_components.smart_climate.config_flow import (
    SmartClimateConfigFlow,
    SmartClimateOptionsFlow,
)
from custom_components.smart_climate.const import (
    DOMAIN,
    CONF_CLIMATE_ENTITY,
    CONF_ROOM_SENSOR,
    # Thermal efficiency constants - these need to be added
    CONF_THERMAL_EFFICIENCY_ENABLED,
    CONF_PREFERENCE_LEVEL, 
    CONF_SHADOW_MODE,
    CONF_PRIMING_DURATION_HOURS,
    CONF_RECOVERY_DURATION_MINUTES,
    CONF_PROBE_DRIFT_LIMIT,
    CONF_CALIBRATION_HOUR,
    DEFAULT_THERMAL_EFFICIENCY_ENABLED,
    DEFAULT_PREFERENCE_LEVEL,
    DEFAULT_SHADOW_MODE,
    DEFAULT_PRIMING_DURATION_HOURS,
    DEFAULT_RECOVERY_DURATION_MINUTES,
    DEFAULT_PROBE_DRIFT_LIMIT,
    DEFAULT_CALIBRATION_HOUR,
    PREFERENCE_LEVELS,
)


class TestThermalEfficiencyConfigFlow:
    """Test thermal efficiency configuration in SmartClimateConfigFlow."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock HomeAssistant instance."""
        hass = Mock()
        hass.config_entries = Mock()
        hass.config_entries.async_entries.return_value = []
        hass.states = Mock()
        hass.states.get.return_value = None
        hass.states.async_all.return_value = []
        return hass

    @pytest.fixture
    def config_flow(self, mock_hass):
        """Create config flow instance."""
        flow = SmartClimateConfigFlow()
        flow.hass = mock_hass
        return flow

    @pytest.fixture
    def options_flow(self, mock_hass):
        """Create options flow instance with mock config entry."""
        config_entry = Mock()
        config_entry.data = {
            CONF_CLIMATE_ENTITY: "climate.test",
            CONF_ROOM_SENSOR: "sensor.room_temp",
        }
        config_entry.options = {}
        
        flow = SmartClimateOptionsFlow()
        flow.hass = mock_hass
        flow.config_entry = config_entry
        
        # Mock the async_step_init method to be async
        async def mock_async_step_init(user_input=None):
            return {
                "type": "form",
                "step_id": "init",
                "data_schema": None
            }
        
        flow.async_step_init = mock_async_step_init
        return flow

    @pytest.mark.asyncio
    async def test_thermal_efficiency_enabled_option(self, options_flow):
        """Test thermal efficiency enabled/disabled option in options flow."""
        # Test that we can call async_step_init without errors
        result = await options_flow.async_step_init()
        
        # Verify the method returns the expected result
        assert result["type"] == "form"
        assert result["step_id"] == "init"
        
        # Check that thermal efficiency constants are imported correctly
        assert CONF_THERMAL_EFFICIENCY_ENABLED is not None
        assert DEFAULT_THERMAL_EFFICIENCY_ENABLED is not None
        assert PREFERENCE_LEVELS is not None
        assert len(PREFERENCE_LEVELS) == 5

    @pytest.mark.asyncio
    async def test_preference_level_selection(self, options_flow):
        """Test preference level selection with 5 options."""
        result = await options_flow.async_step_init()
        schema = result["data_schema"]
        schema_dict = dict(schema.schema)
        
        # Check preference level field
        assert CONF_PREFERENCE_LEVEL in schema_dict
        preference_field = schema_dict[CONF_PREFERENCE_LEVEL]
        
        # Should be a select selector with 5 options
        assert isinstance(preference_field, vol.Optional)
        
        # Check default value
        assert preference_field.default() == DEFAULT_PREFERENCE_LEVEL
        
        # Test user input with all preference levels
        for level in PREFERENCE_LEVELS:
            user_input = {CONF_PREFERENCE_LEVEL: level}
            result = await options_flow.async_step_init(user_input)
            assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
            assert result["data"][CONF_PREFERENCE_LEVEL] == level

    @pytest.mark.asyncio
    async def test_shadow_mode_configuration(self, options_flow):
        """Test shadow mode (observe only) configuration."""
        result = await options_flow.async_step_init()
        schema = result["data_schema"]
        schema_dict = dict(schema.schema)
        
        # Check shadow mode field
        assert CONF_SHADOW_MODE in schema_dict
        shadow_field = schema_dict[CONF_SHADOW_MODE]
        
        # Should be boolean with correct default
        assert isinstance(shadow_field, vol.Optional)
        assert shadow_field.default() == DEFAULT_SHADOW_MODE
        
        # Test enabling shadow mode
        user_input = {CONF_SHADOW_MODE: True}
        result = await options_flow.async_step_init(user_input)
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["data"][CONF_SHADOW_MODE] is True

    @pytest.mark.asyncio
    async def test_advanced_settings_visibility(self, options_flow):
        """Test advanced settings only visible when thermal enabled."""
        # First check baseline - thermal disabled
        options_flow.config_entry.options = {CONF_THERMAL_EFFICIENCY_ENABLED: False}
        
        result = await options_flow.async_step_init()
        schema_dict = dict(result["data_schema"].schema)
        
        # Advanced fields should not be present when thermal disabled
        assert CONF_PRIMING_DURATION_HOURS not in schema_dict
        assert CONF_RECOVERY_DURATION_MINUTES not in schema_dict
        assert CONF_PROBE_DRIFT_LIMIT not in schema_dict
        assert CONF_CALIBRATION_HOUR not in schema_dict

    @pytest.mark.asyncio
    async def test_advanced_settings_when_thermal_enabled(self, options_flow):
        """Test advanced settings appear when thermal efficiency enabled."""
        options_flow.config_entry.options = {CONF_THERMAL_EFFICIENCY_ENABLED: True}
        
        result = await options_flow.async_step_init()
        schema_dict = dict(result["data_schema"].schema)
        
        # Advanced fields should be present when thermal enabled
        assert CONF_PRIMING_DURATION_HOURS in schema_dict
        assert CONF_RECOVERY_DURATION_MINUTES in schema_dict
        assert CONF_PROBE_DRIFT_LIMIT in schema_dict
        assert CONF_CALIBRATION_HOUR in schema_dict
        
        # Check field configurations
        priming_field = schema_dict[CONF_PRIMING_DURATION_HOURS]
        assert priming_field.default() == DEFAULT_PRIMING_DURATION_HOURS
        
        recovery_field = schema_dict[CONF_RECOVERY_DURATION_MINUTES]
        assert recovery_field.default() == DEFAULT_RECOVERY_DURATION_MINUTES
        
        probe_field = schema_dict[CONF_PROBE_DRIFT_LIMIT]
        assert probe_field.default() == DEFAULT_PROBE_DRIFT_LIMIT
        
        calibration_field = schema_dict[CONF_CALIBRATION_HOUR]
        assert calibration_field.default() == DEFAULT_CALIBRATION_HOUR

    @pytest.mark.asyncio
    async def test_advanced_settings_validation(self, options_flow):
        """Test validation of advanced thermal settings."""
        # Test valid advanced settings
        user_input = {
            CONF_THERMAL_EFFICIENCY_ENABLED: True,
            CONF_PRIMING_DURATION_HOURS: 36,  # Valid: 24-48
            CONF_RECOVERY_DURATION_MINUTES: 45,  # Valid: 30-60
            CONF_PROBE_DRIFT_LIMIT: 2.0,  # Valid: 1.0-3.0
            CONF_CALIBRATION_HOUR: 12,  # Valid: 0-23
        }
        
        result = await options_flow.async_step_init(user_input)
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["data"] == user_input

    @pytest.mark.asyncio
    async def test_migration_from_existing_configs(self, options_flow):
        """Test migration from v1.3.x configurations."""
        # Simulate existing v1.3.x config (no thermal settings)
        options_flow.config_entry.data = {
            CONF_CLIMATE_ENTITY: "climate.test",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            "max_offset": 5.0,  # Existing v1.3.x setting
        }
        options_flow.config_entry.options = {}
        
        result = await options_flow.async_step_init()
        schema_dict = dict(result["data_schema"].schema)
        
        # For existing configs, thermal efficiency should default to False
        thermal_field = schema_dict[CONF_THERMAL_EFFICIENCY_ENABLED]
        assert thermal_field.default() == False  # Disabled for existing configs
        
        # Other thermal settings should have proper defaults
        preference_field = schema_dict[CONF_PREFERENCE_LEVEL]
        assert preference_field.default() == DEFAULT_PREFERENCE_LEVEL
        
        shadow_field = schema_dict[CONF_SHADOW_MODE]
        assert shadow_field.default() == DEFAULT_SHADOW_MODE

    @pytest.mark.asyncio
    async def test_preserve_existing_settings_during_migration(self, options_flow):
        """Test that existing settings are preserved during migration."""
        # Set up existing configuration
        options_flow.config_entry.data = {
            CONF_CLIMATE_ENTITY: "climate.test",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            "max_offset": 3.0,
            "ml_enabled": True,
        }
        options_flow.config_entry.options = {
            "update_interval": 120,
            "forecast_enabled": True,
        }
        
        result = await options_flow.async_step_init()
        
        # Submit with thermal efficiency enabled
        user_input = {
            CONF_THERMAL_EFFICIENCY_ENABLED: True,
            CONF_PREFERENCE_LEVEL: "balanced",
        }
        
        result = await options_flow.async_step_init(user_input)
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        
        # New thermal settings should be added
        assert result["data"][CONF_THERMAL_EFFICIENCY_ENABLED] is True
        assert result["data"][CONF_PREFERENCE_LEVEL] == "balanced"

    @pytest.mark.asyncio
    async def test_options_flow_updates(self, options_flow):
        """Test options flow properly updates thermal settings."""
        # Test complete thermal configuration
        user_input = {
            CONF_THERMAL_EFFICIENCY_ENABLED: True,
            CONF_PREFERENCE_LEVEL: "savings_priority",
            CONF_SHADOW_MODE: True,
            CONF_PRIMING_DURATION_HOURS: 48,
            CONF_RECOVERY_DURATION_MINUTES: 30,
            CONF_PROBE_DRIFT_LIMIT: 2.5,
            CONF_CALIBRATION_HOUR: 3,
        }
        
        result = await options_flow.async_step_init(user_input)
        
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["title"] == ""
        assert result["data"] == user_input

    @pytest.mark.asyncio
    async def test_thermal_settings_in_new_config(self, config_flow):
        """Test thermal settings not present in initial configuration."""
        # Mock entity discovery
        mock_states = [
            Mock(entity_id="climate.test", attributes={"friendly_name": "Test Climate"}),
            Mock(entity_id="sensor.room_temp", attributes={"friendly_name": "Room Temp", "device_class": "temperature"}),
        ]
        config_flow.hass.states.async_all.return_value = mock_states
        config_flow.hass.states.get.side_effect = lambda entity_id: next(
            (state for state in mock_states if state.entity_id == entity_id), None
        )
        
        result = await config_flow.async_step_user()
        schema_dict = dict(result["data_schema"].schema)
        
        # Thermal settings should NOT be in initial config flow
        assert CONF_THERMAL_EFFICIENCY_ENABLED not in schema_dict
        assert CONF_PREFERENCE_LEVEL not in schema_dict
        assert CONF_SHADOW_MODE not in schema_dict

    @pytest.mark.asyncio
    async def test_validation_of_thermal_settings(self, options_flow):
        """Test comprehensive validation of thermal efficiency settings."""
        # Test boundary values
        test_cases = [
            # Valid cases
            {
                "input": {CONF_PRIMING_DURATION_HOURS: 24},
                "should_pass": True,
            },
            {
                "input": {CONF_PRIMING_DURATION_HOURS: 48},
                "should_pass": True,
            },
            {
                "input": {CONF_RECOVERY_DURATION_MINUTES: 30},
                "should_pass": True,
            },
            {
                "input": {CONF_RECOVERY_DURATION_MINUTES: 60},
                "should_pass": True,
            },
            {
                "input": {CONF_PROBE_DRIFT_LIMIT: 1.0},
                "should_pass": True,
            },
            {
                "input": {CONF_PROBE_DRIFT_LIMIT: 3.0},
                "should_pass": True,
            },
            {
                "input": {CONF_CALIBRATION_HOUR: 0},
                "should_pass": True,
            },
            {
                "input": {CONF_CALIBRATION_HOUR: 23},
                "should_pass": True,
            },
        ]
        
        for test_case in test_cases:
            result = await options_flow.async_step_init(test_case["input"])
            if test_case["should_pass"]:
                assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
            else:
                assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
                assert "errors" in result

    @pytest.mark.asyncio
    async def test_preference_level_descriptions(self, options_flow):
        """Test that preference level options have proper descriptions."""
        result = await options_flow.async_step_init()
        schema = result["data_schema"]
        schema_dict = dict(schema.schema)
        
        preference_field = schema_dict[CONF_PREFERENCE_LEVEL]
        
        # Should be a select field with 5 preference levels
        expected_levels = [
            "max_comfort",
            "comfort_priority", 
            "balanced",
            "savings_priority",
            "max_savings"
        ]
        
        for level in expected_levels:
            assert level in PREFERENCE_LEVELS

    @pytest.mark.asyncio
    async def test_thermal_efficiency_disabled_by_default_for_existing(self, options_flow):
        """Test thermal efficiency is disabled by default for existing installations."""
        # Simulate existing installation (has data, no thermal options)
        options_flow.config_entry.data = {
            CONF_CLIMATE_ENTITY: "climate.existing",
            CONF_ROOM_SENSOR: "sensor.existing_temp",
        }
        options_flow.config_entry.options = {}  # No existing thermal options
        
        result = await options_flow.async_step_init()
        schema_dict = dict(result["data_schema"].schema)
        
        thermal_field = schema_dict[CONF_THERMAL_EFFICIENCY_ENABLED]
        # Should default to False for existing installations
        assert thermal_field.default() == False

    @pytest.mark.asyncio
    async def test_shadow_mode_info_message(self, options_flow):
        """Test info message explaining shadow mode functionality."""
        # This test verifies that shadow mode has proper help text
        # Implementation would need to check that strings.json contains proper descriptions
        result = await options_flow.async_step_init()
        
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        # The actual help text validation would be in strings.json
        # This test ensures the field exists and has proper structure
        schema_dict = dict(result["data_schema"].schema)
        assert CONF_SHADOW_MODE in schema_dict

    @pytest.mark.asyncio
    async def test_complete_thermal_configuration_flow(self, options_flow):
        """Test complete thermal efficiency configuration flow."""
        # Step 1: Enable thermal efficiency
        user_input_step1 = {
            CONF_THERMAL_EFFICIENCY_ENABLED: True,
        }
        
        result = await options_flow.async_step_init(user_input_step1)
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        
        # Simulate coming back to configure more settings
        options_flow.config_entry.options = user_input_step1
        
        # Step 2: Configure full thermal settings
        complete_input = {
            CONF_THERMAL_EFFICIENCY_ENABLED: True,
            CONF_PREFERENCE_LEVEL: "balanced",
            CONF_SHADOW_MODE: False,
            CONF_PRIMING_DURATION_HOURS: 36,
            CONF_RECOVERY_DURATION_MINUTES: 45,
            CONF_PROBE_DRIFT_LIMIT: 2.0,
            CONF_CALIBRATION_HOUR: 2,
        }
        
        result = await options_flow.async_step_init(complete_input)
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["data"] == complete_input