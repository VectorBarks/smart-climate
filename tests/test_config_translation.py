"""ABOUTME: Tests for build_predictive_config function in config_helpers module.
Validates configuration translation from flat format to nested predictive format."""

import pytest
from typing import Dict, Any
import logging

from custom_components.smart_climate.config_helpers import build_predictive_config
from custom_components.smart_climate.const import (
    CONF_FORECAST_ENABLED,
    CONF_WEATHER_ENTITY,
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


class TestBuildPredictiveConfig:
    """Test build_predictive_config function with various configurations."""

    def test_build_with_all_parameters(self):
        """Test building predictive config with all parameters specified."""
        config = {
            CONF_FORECAST_ENABLED: True,
            CONF_WEATHER_ENTITY: "weather.home",
            CONF_HEAT_WAVE_TEMP_THRESHOLD: 35.0,
            CONF_HEAT_WAVE_MIN_DURATION_HOURS: 4,
            CONF_HEAT_WAVE_LOOKAHEAD_HOURS: 48,
            CONF_HEAT_WAVE_PRE_ACTION_HOURS: 3,
            CONF_HEAT_WAVE_ADJUSTMENT: -3.0,
            CONF_CLEAR_SKY_CONDITION: "partlycloudy",
            CONF_CLEAR_SKY_MIN_DURATION_HOURS: 1,
            CONF_CLEAR_SKY_LOOKAHEAD_HOURS: 6,
            CONF_CLEAR_SKY_PRE_ACTION_HOURS: 0.5,
            CONF_CLEAR_SKY_ADJUSTMENT: -0.5,
        }
        
        result = build_predictive_config(config)
        
        assert result is not None
        assert result["weather_entity"] == "weather.home"
        assert len(result["strategies"]) == 2
        
        # Check heat wave strategy
        heat_wave = result["strategies"][0]
        assert heat_wave["name"] == "heat_wave"
        assert heat_wave["enabled"] is True
        assert heat_wave["type"] == "heat_wave"
        assert heat_wave["temp_threshold"] == 35.0
        assert heat_wave["min_duration_hours"] == 4
        assert heat_wave["lookahead_hours"] == 48
        assert heat_wave["pre_action_hours"] == 3
        assert heat_wave["adjustment"] == -3.0
        
        # Check clear sky strategy
        clear_sky = result["strategies"][1]
        assert clear_sky["name"] == "clear_sky"
        assert clear_sky["enabled"] is True
        assert clear_sky["type"] == "clear_sky"
        assert clear_sky["condition"] == "partlycloudy"
        assert clear_sky["min_duration_hours"] == 1
        assert clear_sky["lookahead_hours"] == 6
        assert clear_sky["pre_action_hours"] == 0.5
        assert clear_sky["adjustment"] == -0.5

    def test_build_with_defaults(self):
        """Test building predictive config with default values."""
        config = {
            CONF_FORECAST_ENABLED: True,
            CONF_WEATHER_ENTITY: "weather.home",
        }
        
        result = build_predictive_config(config)
        
        assert result is not None
        assert result["weather_entity"] == "weather.home"
        assert len(result["strategies"]) == 2
        
        # Check heat wave strategy defaults
        heat_wave = result["strategies"][0]
        assert heat_wave["temp_threshold"] == DEFAULT_HEAT_WAVE_TEMP_THRESHOLD
        assert heat_wave["min_duration_hours"] == DEFAULT_HEAT_WAVE_MIN_DURATION_HOURS
        assert heat_wave["lookahead_hours"] == DEFAULT_HEAT_WAVE_LOOKAHEAD_HOURS
        assert heat_wave["pre_action_hours"] == DEFAULT_HEAT_WAVE_PRE_ACTION_HOURS
        assert heat_wave["adjustment"] == DEFAULT_HEAT_WAVE_ADJUSTMENT
        
        # Check clear sky strategy defaults
        clear_sky = result["strategies"][1]
        assert clear_sky["condition"] == DEFAULT_CLEAR_SKY_CONDITION
        assert clear_sky["min_duration_hours"] == DEFAULT_CLEAR_SKY_MIN_DURATION_HOURS
        assert clear_sky["lookahead_hours"] == DEFAULT_CLEAR_SKY_LOOKAHEAD_HOURS
        assert clear_sky["pre_action_hours"] == DEFAULT_CLEAR_SKY_PRE_ACTION_HOURS
        assert clear_sky["adjustment"] == DEFAULT_CLEAR_SKY_ADJUSTMENT

    def test_build_with_forecast_disabled(self):
        """Test that None is returned when forecast is disabled."""
        config = {
            CONF_FORECAST_ENABLED: False,
            CONF_WEATHER_ENTITY: "weather.home",
        }
        
        result = build_predictive_config(config)
        
        assert result is None

    def test_build_with_missing_weather_entity(self):
        """Test that None is returned when weather entity is missing."""
        config = {
            CONF_FORECAST_ENABLED: True,
            # No weather entity
        }
        
        result = build_predictive_config(config)
        
        assert result is None

    def test_build_with_empty_weather_entity(self):
        """Test that None is returned when weather entity is empty string."""
        config = {
            CONF_FORECAST_ENABLED: True,
            CONF_WEATHER_ENTITY: "",
        }
        
        result = build_predictive_config(config)
        
        assert result is None

    def test_build_with_string_boolean_values(self):
        """Test handling of string boolean values from UI."""
        config = {
            CONF_FORECAST_ENABLED: "true",  # String instead of boolean
            CONF_WEATHER_ENTITY: "weather.home",
        }
        
        result = build_predictive_config(config)
        
        assert result is not None
        assert result["weather_entity"] == "weather.home"

    def test_build_with_false_string_boolean(self):
        """Test handling of 'false' string boolean value."""
        config = {
            CONF_FORECAST_ENABLED: "false",  # String false
            CONF_WEATHER_ENTITY: "weather.home",
        }
        
        result = build_predictive_config(config)
        
        assert result is None

    def test_build_with_mixed_case_boolean_string(self):
        """Test handling of mixed case boolean strings."""
        test_cases = [
            ("True", True),
            ("TRUE", True),
            ("tRuE", True),
            ("False", False),
            ("FALSE", False),
            ("fAlSe", False),
        ]
        
        for string_value, should_enable in test_cases:
            config = {
                CONF_FORECAST_ENABLED: string_value,
                CONF_WEATHER_ENTITY: "weather.home",
            }
            
            result = build_predictive_config(config)
            
            if should_enable:
                assert result is not None
            else:
                assert result is None

    def test_build_with_partial_heat_wave_config(self):
        """Test building with partial heat wave configuration."""
        config = {
            CONF_FORECAST_ENABLED: True,
            CONF_WEATHER_ENTITY: "weather.home",
            CONF_HEAT_WAVE_TEMP_THRESHOLD: 40.0,
            CONF_HEAT_WAVE_ADJUSTMENT: -4.0,
            # Other heat wave params use defaults
        }
        
        result = build_predictive_config(config)
        
        assert result is not None
        heat_wave = result["strategies"][0]
        assert heat_wave["temp_threshold"] == 40.0
        assert heat_wave["adjustment"] == -4.0
        assert heat_wave["min_duration_hours"] == DEFAULT_HEAT_WAVE_MIN_DURATION_HOURS
        assert heat_wave["lookahead_hours"] == DEFAULT_HEAT_WAVE_LOOKAHEAD_HOURS

    def test_build_with_partial_clear_sky_config(self):
        """Test building with partial clear sky configuration."""
        config = {
            CONF_FORECAST_ENABLED: True,
            CONF_WEATHER_ENTITY: "weather.home",
            CONF_CLEAR_SKY_CONDITION: "clear-night",
            CONF_CLEAR_SKY_PRE_ACTION_HOURS: 2,
            # Other clear sky params use defaults
        }
        
        result = build_predictive_config(config)
        
        assert result is not None
        clear_sky = result["strategies"][1]
        assert clear_sky["condition"] == "clear-night"
        assert clear_sky["pre_action_hours"] == 2
        assert clear_sky["min_duration_hours"] == DEFAULT_CLEAR_SKY_MIN_DURATION_HOURS
        assert clear_sky["adjustment"] == DEFAULT_CLEAR_SKY_ADJUSTMENT

    def test_strategy_structure_matches_forecast_engine(self):
        """Test that strategy structure matches ForecastEngine expectations."""
        config = {
            CONF_FORECAST_ENABLED: True,
            CONF_WEATHER_ENTITY: "weather.home",
        }
        
        result = build_predictive_config(config)
        
        assert result is not None
        
        # Both strategies should have required fields
        for strategy in result["strategies"]:
            assert "name" in strategy
            assert "enabled" in strategy
            assert "type" in strategy
            assert strategy["enabled"] is True

    def test_empty_config(self):
        """Test building with empty configuration."""
        config = {}
        
        result = build_predictive_config(config)
        
        assert result is None

    def test_build_with_numeric_types(self):
        """Test that numeric types are preserved correctly."""
        config = {
            CONF_FORECAST_ENABLED: True,
            CONF_WEATHER_ENTITY: "weather.home",
            CONF_HEAT_WAVE_TEMP_THRESHOLD: 30,  # int instead of float
            CONF_HEAT_WAVE_MIN_DURATION_HOURS: 3.5,  # float instead of int
            CONF_CLEAR_SKY_PRE_ACTION_HOURS: "1.5",  # string number
        }
        
        result = build_predictive_config(config)
        
        assert result is not None
        assert result["strategies"][0]["temp_threshold"] == 30
        assert result["strategies"][0]["min_duration_hours"] == 3.5
        # String numbers are not converted, passed as-is
        assert result["strategies"][1]["pre_action_hours"] == "1.5"

    def test_build_preserves_extra_fields(self):
        """Test that extra fields in config are not included in result."""
        config = {
            CONF_FORECAST_ENABLED: True,
            CONF_WEATHER_ENTITY: "weather.home",
            "extra_field": "should_not_appear",
            "climate_entity": "climate.ac",
            "room_sensor": "sensor.room",
        }
        
        result = build_predictive_config(config)
        
        assert result is not None
        assert "extra_field" not in result
        assert "climate_entity" not in result
        assert "room_sensor" not in result
        assert "weather_entity" in result
        assert "strategies" in result

    @pytest.mark.parametrize("weather_entity", [
        "weather.home",
        "weather.home_assistant",
        "weather.openweathermap",
        "weather.met_no",
        "weather.darksky",
    ])
    def test_various_weather_entities(self, weather_entity):
        """Test with various weather entity names."""
        config = {
            CONF_FORECAST_ENABLED: True,
            CONF_WEATHER_ENTITY: weather_entity,
        }
        
        result = build_predictive_config(config)
        
        assert result is not None
        assert result["weather_entity"] == weather_entity

    def test_logging_behavior(self, caplog):
        """Test that appropriate log messages are generated."""
        with caplog.at_level(logging.DEBUG):
            # Test disabled forecast
            config = {CONF_FORECAST_ENABLED: False}
            result = build_predictive_config(config)
            assert "Weather forecast is disabled in configuration" in caplog.text
            
            caplog.clear()
            
            # Test missing weather entity
            config = {CONF_FORECAST_ENABLED: True}
            result = build_predictive_config(config)
            assert "Weather forecast enabled but no weather entity configured" in caplog.text
            
            caplog.clear()
            
            # Test successful build
            config = {
                CONF_FORECAST_ENABLED: True,
                CONF_WEATHER_ENTITY: "weather.home"
            }
            result = build_predictive_config(config)
            assert "Built predictive config with weather entity" in caplog.text
            assert "2 strategies" in caplog.text


class TestConfigTranslationEdgeCases:
    """Test edge cases and invalid inputs for config translation."""

    def test_none_config(self):
        """Test that None config is handled gracefully."""
        # This should raise an AttributeError since None has no .get method
        with pytest.raises(AttributeError):
            build_predictive_config(None)

    def test_config_with_none_values(self):
        """Test handling of None values in config."""
        config = {
            CONF_FORECAST_ENABLED: None,  # None instead of boolean
            CONF_WEATHER_ENTITY: "weather.home",
        }
        
        result = build_predictive_config(config)
        
        # None is falsy, so should return None
        assert result is None

    def test_config_with_invalid_boolean_string(self):
        """Test handling of invalid boolean string values."""
        config = {
            CONF_FORECAST_ENABLED: "yes",  # Invalid boolean string
            CONF_WEATHER_ENTITY: "weather.home",
        }
        
        result = build_predictive_config(config)
        
        # "yes" != "true" so should be disabled
        assert result is None

    def test_strategy_order_preserved(self):
        """Test that strategies are always in the same order."""
        config = {
            CONF_FORECAST_ENABLED: True,
            CONF_WEATHER_ENTITY: "weather.home",
        }
        
        # Build multiple times
        results = []
        for _ in range(5):
            result = build_predictive_config(config)
            results.append(result)
        
        # All results should be identical
        for result in results:
            assert result["strategies"][0]["name"] == "heat_wave"
            assert result["strategies"][1]["name"] == "clear_sky"

    def test_unicode_weather_entity(self):
        """Test handling of unicode characters in weather entity name."""
        config = {
            CONF_FORECAST_ENABLED: True,
            CONF_WEATHER_ENTITY: "weather.домашняя_погода",  # Unicode characters
        }
        
        result = build_predictive_config(config)
        
        assert result is not None
        assert result["weather_entity"] == "weather.домашняя_погода"