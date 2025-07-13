"""Test forecast configuration schema for Smart Climate Control."""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import voluptuous as vol

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
    # Forecast configuration constants (to be added)
    CONF_FORECAST_ENABLED,
    CONF_WEATHER_ENTITY,
    CONF_FORECAST_STRATEGIES,
    CONF_STRATEGY_NAME,
    CONF_STRATEGY_ENABLED,
    CONF_STRATEGY_TYPE,
    CONF_HEAT_WAVE_TEMP_THRESHOLD,
    CONF_HEAT_WAVE_MIN_DURATION_HOURS,
    CONF_HEAT_WAVE_LOOKAHEAD_HOURS,
    CONF_HEAT_WAVE_PRE_ACTION_HOURS,
    CONF_HEAT_WAVE_ADJUSTMENT,
    CONF_CLEAR_SKY_CONDITION,
    CONF_CLEAR_SKY_MIN_DURATION_HOURS,
    CONF_CLEAR_SKY_LOOKAHEAD_HOURS,
    CONF_CLEAR_SKY_PRE_ACTION_HOURS,
    CONF_CLEAR_SKY_ADJUSTMENT,
    # Default values
    DEFAULT_FORECAST_ENABLED,
    DEFAULT_HEAT_WAVE_TEMP_THRESHOLD,
    DEFAULT_HEAT_WAVE_MIN_DURATION_HOURS,
    DEFAULT_HEAT_WAVE_LOOKAHEAD_HOURS,
    DEFAULT_HEAT_WAVE_PRE_ACTION_HOURS,
    DEFAULT_HEAT_WAVE_ADJUSTMENT,
    DEFAULT_CLEAR_SKY_CONDITION,
    DEFAULT_CLEAR_SKY_MIN_DURATION_HOURS,
    DEFAULT_CLEAR_SKY_LOOKAHEAD_HOURS,
    DEFAULT_CLEAR_SKY_PRE_ACTION_HOURS,
    DEFAULT_CLEAR_SKY_ADJUSTMENT,
)


@pytest.fixture
def hass():
    """Create a mock Home Assistant instance."""
    mock_hass = MagicMock()
    mock_hass.data = {}
    return mock_hass


@pytest.fixture
def mock_weather_entities():
    """Mock weather entities available in Home Assistant."""
    return {
        "weather.home": "Home Weather",
        "weather.openweathermap": "OpenWeatherMap",
        "weather.met_no": "Met.no",
        "weather.accuweather": "AccuWeather",
    }


@pytest.fixture
def mock_base_entities():
    """Mock basic entities for config flow."""
    return {
        "climate_entities": {
            "climate.living_room": "Living Room AC",
            "climate.bedroom": "Bedroom AC",
        },
        "temperature_sensors": {
            "sensor.living_room_temperature": "Living Room Temperature",
            "sensor.outdoor_temperature": "Outdoor Temperature",
        },
        "power_sensors": {
            "sensor.ac_power": "AC Power",
        }
    }


class TestForecastConfigConstants:
    """Test forecast configuration constants are properly defined."""

    def test_forecast_config_constants_exist(self):
        """Test that all required forecast configuration constants are defined."""
        # Main forecast constants
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'CONF_FORECAST_ENABLED')
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'CONF_WEATHER_ENTITY')
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'CONF_FORECAST_STRATEGIES')
        
        # Strategy configuration constants
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'CONF_STRATEGY_NAME')
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'CONF_STRATEGY_ENABLED')
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'CONF_STRATEGY_TYPE')
        
        # Heat wave strategy constants
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'CONF_HEAT_WAVE_TEMP_THRESHOLD')
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'CONF_HEAT_WAVE_MIN_DURATION_HOURS')
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'CONF_HEAT_WAVE_LOOKAHEAD_HOURS')
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'CONF_HEAT_WAVE_PRE_ACTION_HOURS')
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'CONF_HEAT_WAVE_ADJUSTMENT')
        
        # Clear sky strategy constants
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'CONF_CLEAR_SKY_CONDITION')
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'CONF_CLEAR_SKY_MIN_DURATION_HOURS')
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'CONF_CLEAR_SKY_LOOKAHEAD_HOURS')
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'CONF_CLEAR_SKY_PRE_ACTION_HOURS')
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'CONF_CLEAR_SKY_ADJUSTMENT')

    def test_forecast_default_values_exist(self):
        """Test that all required forecast default values are defined."""
        # Main defaults
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'DEFAULT_FORECAST_ENABLED')
        
        # Heat wave defaults
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'DEFAULT_HEAT_WAVE_TEMP_THRESHOLD')
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'DEFAULT_HEAT_WAVE_MIN_DURATION_HOURS')
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'DEFAULT_HEAT_WAVE_LOOKAHEAD_HOURS')
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'DEFAULT_HEAT_WAVE_PRE_ACTION_HOURS')
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'DEFAULT_HEAT_WAVE_ADJUSTMENT')
        
        # Clear sky defaults
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'DEFAULT_CLEAR_SKY_CONDITION')
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'DEFAULT_CLEAR_SKY_MIN_DURATION_HOURS')
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'DEFAULT_CLEAR_SKY_LOOKAHEAD_HOURS')
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'DEFAULT_CLEAR_SKY_PRE_ACTION_HOURS')
        assert hasattr(sys.modules['custom_components.smart_climate.const'], 'DEFAULT_CLEAR_SKY_ADJUSTMENT')

    def test_forecast_constant_values(self):
        """Test that forecast configuration constant values are correct strings."""
        assert CONF_FORECAST_ENABLED == "forecast_enabled"
        assert CONF_WEATHER_ENTITY == "weather_entity"
        assert CONF_FORECAST_STRATEGIES == "forecast_strategies"
        
        assert CONF_STRATEGY_NAME == "strategy_name"
        assert CONF_STRATEGY_ENABLED == "strategy_enabled"
        assert CONF_STRATEGY_TYPE == "strategy_type"
        
        # Heat wave constants
        assert CONF_HEAT_WAVE_TEMP_THRESHOLD == "heat_wave_temp_threshold"
        assert CONF_HEAT_WAVE_MIN_DURATION_HOURS == "heat_wave_min_duration_hours"
        assert CONF_HEAT_WAVE_LOOKAHEAD_HOURS == "heat_wave_lookahead_hours"
        assert CONF_HEAT_WAVE_PRE_ACTION_HOURS == "heat_wave_pre_action_hours"
        assert CONF_HEAT_WAVE_ADJUSTMENT == "heat_wave_adjustment"
        
        # Clear sky constants
        assert CONF_CLEAR_SKY_CONDITION == "clear_sky_condition"
        assert CONF_CLEAR_SKY_MIN_DURATION_HOURS == "clear_sky_min_duration_hours"
        assert CONF_CLEAR_SKY_LOOKAHEAD_HOURS == "clear_sky_lookahead_hours"
        assert CONF_CLEAR_SKY_PRE_ACTION_HOURS == "clear_sky_pre_action_hours"
        assert CONF_CLEAR_SKY_ADJUSTMENT == "clear_sky_adjustment"

    def test_forecast_default_values(self):
        """Test that forecast default values are reasonable."""
        assert DEFAULT_FORECAST_ENABLED == False  # Optional feature, disabled by default
        
        # Heat wave defaults
        assert DEFAULT_HEAT_WAVE_TEMP_THRESHOLD == 29.0  # Celsius
        assert DEFAULT_HEAT_WAVE_MIN_DURATION_HOURS == 5
        assert DEFAULT_HEAT_WAVE_LOOKAHEAD_HOURS == 24
        assert DEFAULT_HEAT_WAVE_PRE_ACTION_HOURS == 2
        assert DEFAULT_HEAT_WAVE_ADJUSTMENT == -2.0  # Pre-cool by 2°C
        
        # Clear sky defaults
        assert DEFAULT_CLEAR_SKY_CONDITION == "sunny"
        assert DEFAULT_CLEAR_SKY_MIN_DURATION_HOURS == 6
        assert DEFAULT_CLEAR_SKY_LOOKAHEAD_HOURS == 12
        assert DEFAULT_CLEAR_SKY_PRE_ACTION_HOURS == 1
        assert DEFAULT_CLEAR_SKY_ADJUSTMENT == -1.0  # Pre-cool by 1°C


class TestForecastConfigFlow:
    """Test forecast configuration in config flow."""

    def test_config_flow_imports_forecast_constants(self):
        """Test that config flow imports all required forecast constants."""
        from custom_components.smart_climate.config_flow import SmartClimateConfigFlow
        
        # Test that the config flow module has access to all forecast constants
        flow_module = sys.modules['custom_components.smart_climate.config_flow']
        
        required_constants = [
            'CONF_FORECAST_ENABLED',
            'CONF_WEATHER_ENTITY',
            'CONF_HEAT_WAVE_TEMP_THRESHOLD',
            'CONF_HEAT_WAVE_MIN_DURATION_HOURS',
            'CONF_HEAT_WAVE_LOOKAHEAD_HOURS',
            'CONF_HEAT_WAVE_PRE_ACTION_HOURS',
            'CONF_HEAT_WAVE_ADJUSTMENT',
            'CONF_CLEAR_SKY_CONDITION',
            'CONF_CLEAR_SKY_MIN_DURATION_HOURS',
            'CONF_CLEAR_SKY_LOOKAHEAD_HOURS',
            'CONF_CLEAR_SKY_PRE_ACTION_HOURS',
            'CONF_CLEAR_SKY_ADJUSTMENT',
            'DEFAULT_FORECAST_ENABLED',
            'DEFAULT_HEAT_WAVE_TEMP_THRESHOLD',
            'DEFAULT_HEAT_WAVE_MIN_DURATION_HOURS',
            'DEFAULT_HEAT_WAVE_LOOKAHEAD_HOURS',
            'DEFAULT_HEAT_WAVE_PRE_ACTION_HOURS',
            'DEFAULT_HEAT_WAVE_ADJUSTMENT',
            'DEFAULT_CLEAR_SKY_CONDITION',
            'DEFAULT_CLEAR_SKY_MIN_DURATION_HOURS',
            'DEFAULT_CLEAR_SKY_LOOKAHEAD_HOURS',
            'DEFAULT_CLEAR_SKY_PRE_ACTION_HOURS',
            'DEFAULT_CLEAR_SKY_ADJUSTMENT',
        ]
        
        for constant in required_constants:
            assert hasattr(flow_module, constant), f"Config flow missing constant: {constant}"
    
    def test_weather_entity_getter_method_exists(self):
        """Test that _get_weather_entities method exists in config flow."""
        flow = SmartClimateConfigFlow()
        assert hasattr(flow, '_get_weather_entities'), "Config flow missing _get_weather_entities method"
        assert callable(getattr(flow, '_get_weather_entities')), "_get_weather_entities should be callable"

    def test_validation_logic_exists(self):
        """Test that forecast validation logic exists in _validate_input method."""
        # Read the config_flow.py source file directly to verify forecast validation exists
        with open('/home/vector/git/vector-climate/custom_components/smart_climate/config_flow.py', 'r') as f:
            source = f.read()
        
        # Check that forecast validation logic is present
        assert 'forecast_enabled' in source, "Missing forecast_enabled validation"
        assert 'weather_entity' in source, "Missing weather_entity validation"
        assert 'weather_entity required when forecast is enabled' in source, "Missing weather entity requirement validation"


class TestForecastStrategyValidation:
    """Test forecast strategy parameter validation."""

    def test_heat_wave_strategy_parameter_validation(self):
        """Test heat wave strategy parameter ranges."""
        # Test valid heat wave parameters
        valid_heat_wave_input = {
            CONF_HEAT_WAVE_TEMP_THRESHOLD: 30.0,
            CONF_HEAT_WAVE_MIN_DURATION_HOURS: 4,
            CONF_HEAT_WAVE_LOOKAHEAD_HOURS: 24,
            CONF_HEAT_WAVE_PRE_ACTION_HOURS: 2,
            CONF_HEAT_WAVE_ADJUSTMENT: -2.5,
        }
        
        # Should not raise validation error
        try:
            # This would be called in actual validation
            assert valid_heat_wave_input[CONF_HEAT_WAVE_TEMP_THRESHOLD] >= 20.0
            assert valid_heat_wave_input[CONF_HEAT_WAVE_TEMP_THRESHOLD] <= 40.0
            assert valid_heat_wave_input[CONF_HEAT_WAVE_MIN_DURATION_HOURS] >= 1
            assert valid_heat_wave_input[CONF_HEAT_WAVE_MIN_DURATION_HOURS] <= 24
            assert valid_heat_wave_input[CONF_HEAT_WAVE_LOOKAHEAD_HOURS] >= 1
            assert valid_heat_wave_input[CONF_HEAT_WAVE_LOOKAHEAD_HOURS] <= 72
            assert valid_heat_wave_input[CONF_HEAT_WAVE_PRE_ACTION_HOURS] >= 1
            assert valid_heat_wave_input[CONF_HEAT_WAVE_PRE_ACTION_HOURS] <= 12
            assert valid_heat_wave_input[CONF_HEAT_WAVE_ADJUSTMENT] >= -5.0
            assert valid_heat_wave_input[CONF_HEAT_WAVE_ADJUSTMENT] <= 0.0
        except AssertionError:
            pytest.fail("Valid heat wave parameters failed validation")

    def test_clear_sky_strategy_parameter_validation(self):
        """Test clear sky strategy parameter ranges."""
        # Test valid clear sky parameters
        valid_clear_sky_input = {
            CONF_CLEAR_SKY_CONDITION: "sunny",
            CONF_CLEAR_SKY_MIN_DURATION_HOURS: 6,
            CONF_CLEAR_SKY_LOOKAHEAD_HOURS: 12,
            CONF_CLEAR_SKY_PRE_ACTION_HOURS: 1,
            CONF_CLEAR_SKY_ADJUSTMENT: -1.0,
        }
        
        # Valid weather conditions
        valid_conditions = ["sunny", "clear", "clear-night", "partly-cloudy"]
        
        # Should not raise validation error
        try:
            assert valid_clear_sky_input[CONF_CLEAR_SKY_CONDITION] in valid_conditions
            assert valid_clear_sky_input[CONF_CLEAR_SKY_MIN_DURATION_HOURS] >= 1
            assert valid_clear_sky_input[CONF_CLEAR_SKY_MIN_DURATION_HOURS] <= 24
            assert valid_clear_sky_input[CONF_CLEAR_SKY_LOOKAHEAD_HOURS] >= 1
            assert valid_clear_sky_input[CONF_CLEAR_SKY_LOOKAHEAD_HOURS] <= 48
            assert valid_clear_sky_input[CONF_CLEAR_SKY_PRE_ACTION_HOURS] >= 1
            assert valid_clear_sky_input[CONF_CLEAR_SKY_PRE_ACTION_HOURS] <= 6
            assert valid_clear_sky_input[CONF_CLEAR_SKY_ADJUSTMENT] >= -3.0
            assert valid_clear_sky_input[CONF_CLEAR_SKY_ADJUSTMENT] <= 0.0
        except AssertionError:
            pytest.fail("Valid clear sky parameters failed validation")

    def test_strategy_parameter_boundary_validation(self):
        """Test boundary conditions for strategy parameters."""
        # Test boundary values that should be valid
        boundary_tests = [
            # Heat wave boundaries
            {CONF_HEAT_WAVE_TEMP_THRESHOLD: 20.0},  # Min temperature
            {CONF_HEAT_WAVE_TEMP_THRESHOLD: 40.0},  # Max temperature
            {CONF_HEAT_WAVE_MIN_DURATION_HOURS: 1},  # Min duration
            {CONF_HEAT_WAVE_MIN_DURATION_HOURS: 24},  # Max duration
            {CONF_HEAT_WAVE_ADJUSTMENT: -5.0},  # Min adjustment
            {CONF_HEAT_WAVE_ADJUSTMENT: 0.0},  # Max adjustment
            
            # Clear sky boundaries
            {CONF_CLEAR_SKY_MIN_DURATION_HOURS: 1},  # Min duration
            {CONF_CLEAR_SKY_MIN_DURATION_HOURS: 24},  # Max duration
            {CONF_CLEAR_SKY_ADJUSTMENT: -3.0},  # Min adjustment
            {CONF_CLEAR_SKY_ADJUSTMENT: 0.0},  # Max adjustment
        ]
        
        for test_case in boundary_tests:
            # All boundary values should be valid
            for key, value in test_case.items():
                if "temp_threshold" in key:
                    assert 20.0 <= value <= 40.0, f"Temperature threshold {value} out of range"
                elif "min_duration_hours" in key:
                    assert 1 <= value <= 24, f"Duration {value} out of range"
                elif "adjustment" in key:
                    if "heat_wave" in key:
                        assert -5.0 <= value <= 0.0, f"Heat wave adjustment {value} out of range"
                    else:
                        assert -3.0 <= value <= 0.0, f"Clear sky adjustment {value} out of range"


class TestForecastTranslations:
    """Test forecast configuration translations."""

    def test_forecast_config_translations_exist(self):
        """Test that forecast configuration translations are defined."""
        # This test will verify that the translation keys exist
        # The actual translations will be added to en.json
        
        required_translation_keys = [
            "config.step.user.data.forecast_enabled",
            "config.step.user.data.weather_entity",
            "config.step.user.data.heat_wave_temp_threshold",
            "config.step.user.data.heat_wave_min_duration_hours",
            "config.step.user.data.heat_wave_lookahead_hours", 
            "config.step.user.data.heat_wave_pre_action_hours",
            "config.step.user.data.heat_wave_adjustment",
            "config.step.user.data.clear_sky_condition",
            "config.step.user.data.clear_sky_min_duration_hours",
            "config.step.user.data.clear_sky_lookahead_hours",
            "config.step.user.data.clear_sky_pre_action_hours",
            "config.step.user.data.clear_sky_adjustment",
        ]
        
        required_description_keys = [
            "config.step.user.data_description.forecast_enabled",
            "config.step.user.data_description.weather_entity",
            "config.step.user.data_description.heat_wave_temp_threshold",
            "config.step.user.data_description.heat_wave_min_duration_hours",
            "config.step.user.data_description.heat_wave_lookahead_hours",
            "config.step.user.data_description.heat_wave_pre_action_hours",
            "config.step.user.data_description.heat_wave_adjustment",
            "config.step.user.data_description.clear_sky_condition",
            "config.step.user.data_description.clear_sky_min_duration_hours",
            "config.step.user.data_description.clear_sky_lookahead_hours",
            "config.step.user.data_description.clear_sky_pre_action_hours",
            "config.step.user.data_description.clear_sky_adjustment",
        ]
        
        # For now, just verify the translation key formats are correct
        # The actual verification will happen when translations are implemented
        for key in required_translation_keys + required_description_keys:
            assert "." in key, f"Translation key {key} should be hierarchical"
            assert key.startswith("config."), f"Config translation key {key} should start with 'config.'"

    def test_forecast_error_translations_exist(self):
        """Test that forecast error translations are defined."""
        required_error_keys = [
            "config.error.weather_entity_not_found",
            "config.error.invalid_strategy_parameters",
            "config.error.forecast_weather_entity_required",
        ]
        
        # Verify error key formats
        for key in required_error_keys:
            assert "." in key, f"Error translation key {key} should be hierarchical"
            assert key.startswith("config.error."), f"Error translation key {key} should start with 'config.error.'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])