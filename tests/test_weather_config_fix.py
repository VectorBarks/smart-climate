"""ABOUTME: Test suite for weather configuration fix.
Tests that flat config structure is properly converted to predictive format."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.helpers import entity_registry as er
from homeassistant.config_entries import ConfigEntry

from custom_components.smart_climate import async_setup_entry
from custom_components.smart_climate.const import (
    DOMAIN,
    CONF_CLIMATE_ENTITY,
    CONF_ROOM_SENSOR,
    CONF_FORECAST_ENABLED,
    CONF_WEATHER_ENTITY,
    CONF_PREDICTIVE,
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
from custom_components.smart_climate.forecast_engine import ForecastEngine

from .fixtures.weather_config_fixtures import *


class TestWeatherConfigConversion:
    """Test weather configuration conversion from flat to predictive format."""
    
    async def test_flat_config_converts_to_predictive_structure(
        self, hass: HomeAssistant, flat_weather_config
    ):
        """Test that flat config from config_flow converts to CONF_PREDICTIVE structure."""
        # This test should verify that when climate.py receives flat config,
        # it builds the proper CONF_PREDICTIVE dictionary for ForecastEngine
        
        # Create a mock config entry with flat weather config
        config_data = {
            CONF_CLIMATE_ENTITY: "climate.test",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            **flat_weather_config
        }
        
        config_entry = ConfigEntry(
            version=1,
            minor_version=1,
            domain=DOMAIN,
            title="Test Climate",
            data=config_data,
            source="user",
            entry_id="test_entry_id",
            unique_id="test_unique_id",
        )
        
        # Mock the entity setup
        with patch('custom_components.smart_climate.async_setup_entry') as mock_setup:
            mock_setup.return_value = True
            
            # The actual function should convert flat config to predictive structure
            # This should currently FAIL because the conversion isn't implemented
            result = await async_setup_entry(hass, config_entry)
            
            # Verify setup was called
            assert result is True
            
            # Check that the config was transformed to include CONF_PREDICTIVE
            # This assertion will fail until the fix is implemented
            assert CONF_PREDICTIVE in config_entry.data
            assert "weather_entity" in config_entry.data[CONF_PREDICTIVE]
            assert "strategies" in config_entry.data[CONF_PREDICTIVE]
    
    async def test_strategies_array_built_from_parameters(
        self, hass: HomeAssistant, flat_weather_config
    ):
        """Test that strategy parameters are converted to strategies array."""
        # This test verifies the detailed conversion of strategy parameters
        
        # Mock the conversion function that should be implemented
        from custom_components.smart_climate.climate import _build_predictive_config
        
        # This function doesn't exist yet, so this test will fail
        predictive_config = _build_predictive_config(flat_weather_config)
        
        assert predictive_config is not None
        assert "weather_entity" in predictive_config
        assert predictive_config["weather_entity"] == "weather.home"
        
        strategies = predictive_config.get("strategies", [])
        assert len(strategies) == 2
        
        # Check heat wave strategy
        heat_wave = next((s for s in strategies if s["type"] == "heat_wave"), None)
        assert heat_wave is not None
        assert heat_wave["temp_threshold"] == 29.0
        assert heat_wave["min_duration_hours"] == 5
        assert heat_wave["lookahead_hours"] == 24
        assert heat_wave["pre_action_hours"] == 2
        assert heat_wave["adjustment"] == -2.0
        
        # Check clear sky strategy
        clear_sky = next((s for s in strategies if s["type"] == "clear_sky"), None)
        assert clear_sky is not None
        assert clear_sky["condition"] == "sunny"
        assert clear_sky["min_duration_hours"] == 6
        assert clear_sky["lookahead_hours"] == 12
        assert clear_sky["pre_action_hours"] == 1
        assert clear_sky["adjustment"] == -1.0
    
    async def test_backward_compatibility_with_predictive_format(
        self, hass: HomeAssistant, legacy_predictive_config
    ):
        """Test that existing CONF_PREDICTIVE format still works."""
        # If there are existing users with CONF_PREDICTIVE format, it should still work
        
        config_data = {
            CONF_CLIMATE_ENTITY: "climate.test",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            **legacy_predictive_config
        }
        
        # Mock ForecastEngine initialization
        with patch('custom_components.smart_climate.climate.ForecastEngine') as mock_fe:
            mock_fe.return_value = Mock(spec=ForecastEngine)
            
            # This should work without conversion
            forecast_engine = ForecastEngine(hass, config_data[CONF_PREDICTIVE])
            
            # Verify ForecastEngine was created with correct config
            mock_fe.assert_called_once_with(hass, config_data[CONF_PREDICTIVE])
    
    async def test_weather_disabled_config_handling(
        self, hass: HomeAssistant, weather_disabled_config
    ):
        """Test that weather disabled config doesn't create ForecastEngine."""
        config_data = {
            CONF_CLIMATE_ENTITY: "climate.test",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            **weather_disabled_config
        }
        
        # When forecast_enabled is False, no CONF_PREDICTIVE should be created
        from custom_components.smart_climate.climate import _should_enable_forecast
        
        # This function doesn't exist yet, so will fail
        should_enable = _should_enable_forecast(config_data)
        assert should_enable is False
        
        # No predictive config should be built
        from custom_components.smart_climate.climate import _build_predictive_config
        predictive_config = _build_predictive_config(config_data)
        assert predictive_config is None
    
    async def test_weather_entity_missing_handling(
        self, hass: HomeAssistant, weather_no_entity_config
    ):
        """Test that missing weather entity is handled gracefully."""
        config_data = {
            CONF_CLIMATE_ENTITY: "climate.test",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            **weather_no_entity_config
        }
        
        # Even with forecast_enabled=True, missing entity should prevent ForecastEngine
        from custom_components.smart_climate.climate import _build_predictive_config
        
        # Should return None or handle gracefully
        predictive_config = _build_predictive_config(config_data)
        assert predictive_config is None
    
    async def test_default_values_applied_when_missing(
        self, hass: HomeAssistant
    ):
        """Test that default values are applied for missing strategy parameters."""
        # Minimal config with only required fields
        config_data = {
            CONF_FORECAST_ENABLED: True,
            CONF_WEATHER_ENTITY: "weather.home",
            # Missing all strategy parameters
        }
        
        from custom_components.smart_climate.climate import _build_predictive_config
        predictive_config = _build_predictive_config(config_data)
        
        assert predictive_config is not None
        strategies = predictive_config.get("strategies", [])
        assert len(strategies) == 2
        
        # Check defaults are applied
        heat_wave = next((s for s in strategies if s["type"] == "heat_wave"), None)
        assert heat_wave["temp_threshold"] == DEFAULT_HEAT_WAVE_TEMP_THRESHOLD
        assert heat_wave["min_duration_hours"] == DEFAULT_HEAT_WAVE_MIN_DURATION_HOURS
        
        clear_sky = next((s for s in strategies if s["type"] == "clear_sky"), None)
        assert clear_sky["condition"] == DEFAULT_CLEAR_SKY_CONDITION
        assert clear_sky["min_duration_hours"] == DEFAULT_CLEAR_SKY_MIN_DURATION_HOURS


class TestForecastEngineInitialization:
    """Test ForecastEngine initialization with converted config."""
    
    async def test_forecast_engine_created_with_converted_config(
        self, hass: HomeAssistant, flat_weather_config, mock_hass_with_weather
    ):
        """Test that ForecastEngine is properly initialized with converted config."""
        config_data = {
            CONF_CLIMATE_ENTITY: "climate.test",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            **flat_weather_config
        }
        
        # Mock the climate entity creation process
        with patch('custom_components.smart_climate.climate.ForecastEngine') as mock_fe_class:
            mock_fe = Mock(spec=ForecastEngine)
            mock_fe_class.return_value = mock_fe
            
            # Import and call the setup logic
            from custom_components.smart_climate.climate import SmartClimateEntity
            
            # This should convert flat config and create ForecastEngine
            # Currently will fail because conversion not implemented
            entity = SmartClimateEntity(
                hass=mock_hass_with_weather,
                config=config_data,
                wrapped_entity_id="climate.test",
                room_sensor_id="sensor.room_temp",
                # ... other required params
            )
            
            # Verify ForecastEngine was created
            mock_fe_class.assert_called_once()
            call_args = mock_fe_class.call_args[0]
            
            # Check the config passed to ForecastEngine
            fe_config = call_args[1]
            assert "weather_entity" in fe_config
            assert "strategies" in fe_config
            assert len(fe_config["strategies"]) == 2
    
    async def test_forecast_engine_not_created_when_disabled(
        self, hass: HomeAssistant, weather_disabled_config
    ):
        """Test that ForecastEngine is not created when forecast is disabled."""
        config_data = {
            CONF_CLIMATE_ENTITY: "climate.test",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            **weather_disabled_config
        }
        
        with patch('custom_components.smart_climate.climate.ForecastEngine') as mock_fe_class:
            # Setup should not create ForecastEngine
            from custom_components.smart_climate.climate import SmartClimateEntity
            
            # This test verifies no ForecastEngine is created
            # Will fail until proper checks are implemented
            entity = SmartClimateEntity(
                hass=hass,
                config=config_data,
                wrapped_entity_id="climate.test",
                room_sensor_id="sensor.room_temp",
                # ... other required params
            )
            
            # ForecastEngine should not be created
            mock_fe_class.assert_not_called()


class TestWeatherEntityValidation:
    """Test weather entity validation during config conversion."""
    
    async def test_invalid_weather_entity_handled(
        self, hass: HomeAssistant
    ):
        """Test that invalid weather entity IDs are handled gracefully."""
        config_data = {
            CONF_FORECAST_ENABLED: True,
            CONF_WEATHER_ENTITY: "sensor.not_a_weather_entity",  # Wrong domain
        }
        
        from custom_components.smart_climate.climate import _validate_weather_entity
        
        # This function doesn't exist yet
        is_valid = _validate_weather_entity(config_data[CONF_WEATHER_ENTITY])
        assert is_valid is False
    
    async def test_weather_entity_state_check(
        self, hass: HomeAssistant, mock_hass_with_weather
    ):
        """Test that weather entity availability is checked."""
        # Entity exists and is available
        config_data = {
            CONF_FORECAST_ENABLED: True,
            CONF_WEATHER_ENTITY: "weather.home",
        }
        
        # Check if entity is available
        state = mock_hass_with_weather.states.get(config_data[CONF_WEATHER_ENTITY])
        assert state is not None
        assert state.state != STATE_UNAVAILABLE
        assert state.state != STATE_UNKNOWN
        
        # Now test with unavailable entity
        mock_hass_with_weather.states.async_set(
            "weather.home", STATE_UNAVAILABLE
        )
        
        state = mock_hass_with_weather.states.get(config_data[CONF_WEATHER_ENTITY])
        assert state.state == STATE_UNAVAILABLE
        
        # ForecastEngine should not be created for unavailable entity
        from custom_components.smart_climate.climate import _should_create_forecast_engine
        should_create = _should_create_forecast_engine(mock_hass_with_weather, config_data)
        assert should_create is False


class TestEdgeCases:
    """Test edge cases in weather configuration."""
    
    async def test_partial_strategy_config(self, hass: HomeAssistant):
        """Test handling of partial strategy configuration."""
        # Has some but not all strategy parameters
        config_data = {
            CONF_FORECAST_ENABLED: True,
            CONF_WEATHER_ENTITY: "weather.home",
            CONF_HEAT_WAVE_TEMP_THRESHOLD: 35.0,  # Only this is set
            # All other strategy params missing
        }
        
        from custom_components.smart_climate.climate import _build_predictive_config
        predictive_config = _build_predictive_config(config_data)
        
        # Should still build valid config with defaults
        assert predictive_config is not None
        strategies = predictive_config["strategies"]
        
        heat_wave = next((s for s in strategies if s["type"] == "heat_wave"), None)
        assert heat_wave["temp_threshold"] == 35.0  # User value
        assert heat_wave["min_duration_hours"] == DEFAULT_HEAT_WAVE_MIN_DURATION_HOURS  # Default
    
    async def test_empty_config(self, hass: HomeAssistant):
        """Test handling of empty/minimal configuration."""
        config_data = {}
        
        from custom_components.smart_climate.climate import _build_predictive_config
        predictive_config = _build_predictive_config(config_data)
        
        # Should return None or empty config
        assert predictive_config is None
    
    async def test_forecast_enabled_string_value(self, hass: HomeAssistant):
        """Test handling of forecast_enabled as string instead of bool."""
        # Sometimes config values come as strings
        config_data = {
            CONF_FORECAST_ENABLED: "true",  # String instead of bool
            CONF_WEATHER_ENTITY: "weather.home",
        }
        
        from custom_components.smart_climate.climate import _build_predictive_config
        predictive_config = _build_predictive_config(config_data)
        
        # Should handle string "true" as True
        assert predictive_config is not None