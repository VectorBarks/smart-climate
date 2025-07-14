"""ABOUTME: Weather configuration test fixtures for Smart Climate Control.
Provides mock weather entities and configuration builders for testing weather feature fixes."""

import pytest
from typing import Dict, Any, Optional
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone, timedelta

from homeassistant.components.weather import (
    WeatherEntity,
    Forecast,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_CONDITION,
)
from homeassistant.core import State
from homeassistant.const import (
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    ATTR_TEMPERATURE,
    ATTR_UNIT_OF_MEASUREMENT,
    TEMP_CELSIUS,
)

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
    CONF_PREDICTIVE,
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
def mock_weather_entity():
    """Create a mock weather entity with forecast data."""
    entity = Mock(spec=WeatherEntity)
    entity.entity_id = "weather.home"
    
    # Current conditions
    entity.temperature = 25.0
    entity.condition = "sunny"
    entity.humidity = 60
    entity.pressure = 1013
    entity.wind_speed = 5.0
    
    # Forecast data - 24 hours of hourly forecasts
    now = datetime.now(timezone.utc)
    forecasts = []
    for i in range(24):
        forecast_time = now + timedelta(hours=i)
        temp = 20.0 + (5.0 * (1 + i/6))  # Temperature rises during day
        condition = "sunny" if i < 18 else "clear-night"
        
        forecasts.append({
            ATTR_FORECAST_TIME: forecast_time.isoformat(),
            ATTR_FORECAST_TEMP: temp,
            ATTR_FORECAST_CONDITION: condition,
        })
    
    # Make forecast property return the list
    type(entity).forecast = property(lambda self: forecasts)
    
    return entity


@pytest.fixture
def weather_entity_state():
    """Create a weather entity state with attributes."""
    return State(
        "weather.home",
        "sunny",
        {
            ATTR_TEMPERATURE: 25.0,
            "humidity": 60,
            "pressure": 1013,
            "wind_speed": 5.0,
            "wind_bearing": 180,
            "forecast": [
                {
                    ATTR_FORECAST_TIME: "2025-07-14T10:00:00+00:00",
                    ATTR_FORECAST_TEMP: 25.0,
                    ATTR_FORECAST_CONDITION: "sunny",
                },
                {
                    ATTR_FORECAST_TIME: "2025-07-14T11:00:00+00:00",
                    ATTR_FORECAST_TEMP: 27.0,
                    ATTR_FORECAST_CONDITION: "sunny",
                },
                {
                    ATTR_FORECAST_TIME: "2025-07-14T12:00:00+00:00",
                    ATTR_FORECAST_TEMP: 30.0,
                    ATTR_FORECAST_CONDITION: "sunny",
                },
            ]
        }
    )


@pytest.fixture
def weather_config_builder():
    """Builder for creating various weather configuration scenarios."""
    
    def build_config(
        enabled: bool = True,
        weather_entity: Optional[str] = "weather.home",
        include_strategies: bool = True,
        as_predictive_dict: bool = False,
        heat_wave_threshold: float = DEFAULT_HEAT_WAVE_TEMP_THRESHOLD,
        clear_sky_condition: str = DEFAULT_CLEAR_SKY_CONDITION,
    ) -> Dict[str, Any]:
        """Build a weather configuration.
        
        Args:
            enabled: Whether weather forecast is enabled
            weather_entity: Weather entity ID or None
            include_strategies: Whether to include strategy parameters
            as_predictive_dict: If True, returns config in CONF_PREDICTIVE format
            heat_wave_threshold: Temperature threshold for heat wave strategy
            clear_sky_condition: Condition string for clear sky strategy
            
        Returns:
            Configuration dictionary in either flat or nested format
        """
        # Build the base configuration
        config = {
            CONF_FORECAST_ENABLED: enabled,
        }
        
        if weather_entity:
            config[CONF_WEATHER_ENTITY] = weather_entity
            
        if include_strategies:
            # Heat wave strategy parameters
            config[CONF_HEAT_WAVE_TEMP_THRESHOLD] = heat_wave_threshold
            config[CONF_HEAT_WAVE_MIN_DURATION_HOURS] = DEFAULT_HEAT_WAVE_MIN_DURATION_HOURS
            config[CONF_HEAT_WAVE_LOOKAHEAD_HOURS] = DEFAULT_HEAT_WAVE_LOOKAHEAD_HOURS
            config[CONF_HEAT_WAVE_PRE_ACTION_HOURS] = DEFAULT_HEAT_WAVE_PRE_ACTION_HOURS
            config[CONF_HEAT_WAVE_ADJUSTMENT] = DEFAULT_HEAT_WAVE_ADJUSTMENT
            
            # Clear sky strategy parameters
            config[CONF_CLEAR_SKY_CONDITION] = clear_sky_condition
            config[CONF_CLEAR_SKY_MIN_DURATION_HOURS] = DEFAULT_CLEAR_SKY_MIN_DURATION_HOURS
            config[CONF_CLEAR_SKY_LOOKAHEAD_HOURS] = DEFAULT_CLEAR_SKY_LOOKAHEAD_HOURS
            config[CONF_CLEAR_SKY_PRE_ACTION_HOURS] = DEFAULT_CLEAR_SKY_PRE_ACTION_HOURS
            config[CONF_CLEAR_SKY_ADJUSTMENT] = DEFAULT_CLEAR_SKY_ADJUSTMENT
        
        if as_predictive_dict:
            # Return in nested CONF_PREDICTIVE format expected by ForecastEngine
            strategies = []
            
            if include_strategies and enabled and weather_entity:
                # Build heat wave strategy
                strategies.append({
                    "name": "heat_wave",
                    "enabled": True,
                    "type": "heat_wave",
                    "temp_threshold": heat_wave_threshold,
                    "min_duration_hours": DEFAULT_HEAT_WAVE_MIN_DURATION_HOURS,
                    "lookahead_hours": DEFAULT_HEAT_WAVE_LOOKAHEAD_HOURS,
                    "pre_action_hours": DEFAULT_HEAT_WAVE_PRE_ACTION_HOURS,
                    "adjustment": DEFAULT_HEAT_WAVE_ADJUSTMENT,
                })
                
                # Build clear sky strategy
                strategies.append({
                    "name": "clear_sky",
                    "enabled": True,
                    "type": "clear_sky",
                    "condition": clear_sky_condition,
                    "min_duration_hours": DEFAULT_CLEAR_SKY_MIN_DURATION_HOURS,
                    "lookahead_hours": DEFAULT_CLEAR_SKY_LOOKAHEAD_HOURS,
                    "pre_action_hours": DEFAULT_CLEAR_SKY_PRE_ACTION_HOURS,
                    "adjustment": DEFAULT_CLEAR_SKY_ADJUSTMENT,
                })
            
            return {
                CONF_PREDICTIVE: {
                    "weather_entity": weather_entity,
                    "strategies": strategies,
                }
            }
        
        return config
    
    return build_config


@pytest.fixture
def legacy_predictive_config():
    """Create a legacy CONF_PREDICTIVE configuration format if it exists."""
    # This represents how weather config might have been stored in older versions
    return {
        CONF_PREDICTIVE: {
            "enabled": True,
            "weather_entity": "weather.home",
            "strategies": [
                {
                    "name": "heat_wave",
                    "enabled": True,
                    "type": "heat_wave",
                    "temp_threshold": 30.0,
                    "min_duration_hours": 5,
                    "lookahead_hours": 24,
                    "pre_action_hours": 2,
                    "adjustment": -2.0,
                },
                {
                    "name": "clear_sky",
                    "enabled": True,
                    "type": "clear_sky",
                    "condition": "sunny",
                    "min_duration_hours": 6,
                    "lookahead_hours": 12,
                    "pre_action_hours": 1,
                    "adjustment": -1.0,
                }
            ]
        }
    }


@pytest.fixture 
def flat_weather_config():
    """Create a flat weather configuration as saved by config_flow."""
    return {
        CONF_FORECAST_ENABLED: True,
        CONF_WEATHER_ENTITY: "weather.home",
        CONF_HEAT_WAVE_TEMP_THRESHOLD: 29.0,
        CONF_HEAT_WAVE_MIN_DURATION_HOURS: 5,
        CONF_HEAT_WAVE_LOOKAHEAD_HOURS: 24,
        CONF_HEAT_WAVE_PRE_ACTION_HOURS: 2,
        CONF_HEAT_WAVE_ADJUSTMENT: -2.0,
        CONF_CLEAR_SKY_CONDITION: "sunny",
        CONF_CLEAR_SKY_MIN_DURATION_HOURS: 6,
        CONF_CLEAR_SKY_LOOKAHEAD_HOURS: 12,
        CONF_CLEAR_SKY_PRE_ACTION_HOURS: 1,
        CONF_CLEAR_SKY_ADJUSTMENT: -1.0,
    }


@pytest.fixture
def weather_disabled_config():
    """Create a configuration with weather forecast disabled."""
    return {
        CONF_FORECAST_ENABLED: False,
        # May still have weather entity and strategy params stored
        CONF_WEATHER_ENTITY: "weather.home",
        CONF_HEAT_WAVE_TEMP_THRESHOLD: 29.0,
        CONF_HEAT_WAVE_MIN_DURATION_HOURS: 5,
        CONF_HEAT_WAVE_LOOKAHEAD_HOURS: 24,
        CONF_HEAT_WAVE_PRE_ACTION_HOURS: 2,
        CONF_HEAT_WAVE_ADJUSTMENT: -2.0,
        CONF_CLEAR_SKY_CONDITION: "sunny",
        CONF_CLEAR_SKY_MIN_DURATION_HOURS: 6,
        CONF_CLEAR_SKY_LOOKAHEAD_HOURS: 12,
        CONF_CLEAR_SKY_PRE_ACTION_HOURS: 1,
        CONF_CLEAR_SKY_ADJUSTMENT: -1.0,
    }


@pytest.fixture
def weather_no_entity_config():
    """Create a configuration with weather enabled but no entity specified."""
    return {
        CONF_FORECAST_ENABLED: True,
        # Missing CONF_WEATHER_ENTITY
        CONF_HEAT_WAVE_TEMP_THRESHOLD: 29.0,
        CONF_HEAT_WAVE_MIN_DURATION_HOURS: 5,
        CONF_HEAT_WAVE_LOOKAHEAD_HOURS: 24,
        CONF_HEAT_WAVE_PRE_ACTION_HOURS: 2,
        CONF_HEAT_WAVE_ADJUSTMENT: -2.0,
        CONF_CLEAR_SKY_CONDITION: "sunny",
        CONF_CLEAR_SKY_MIN_DURATION_HOURS: 6,
        CONF_CLEAR_SKY_LOOKAHEAD_HOURS: 12,
        CONF_CLEAR_SKY_PRE_ACTION_HOURS: 1,
        CONF_CLEAR_SKY_ADJUSTMENT: -1.0,
    }


@pytest.fixture
def mock_hass_with_weather(hass, weather_entity_state):
    """Create a mock Home Assistant instance with weather entity."""
    # Add weather entity state
    hass.states.async_set(
        weather_entity_state.entity_id,
        weather_entity_state.state,
        weather_entity_state.attributes
    )
    
    # Mock the weather domain get_forecast service
    async def mock_get_forecast(call):
        """Mock weather.get_forecast service."""
        return {
            "forecast": weather_entity_state.attributes.get("forecast", [])
        }
    
    hass.services.async_register(
        "weather", "get_forecast", mock_get_forecast
    )
    
    return hass