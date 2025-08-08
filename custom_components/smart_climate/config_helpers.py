"""ABOUTME: Configuration helper functions for Smart Climate Control.
Provides utilities to convert between different configuration formats."""

from typing import Dict, Any, Optional, List
import logging

from .const import (
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

_LOGGER = logging.getLogger(__name__)


def build_predictive_config(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build predictive configuration from flat config structure.
    
    Converts flat configuration saved by config_flow into the nested
    CONF_PREDICTIVE format expected by ForecastEngine.
    
    Args:
        config: Flat configuration dictionary from config_flow
        
    Returns:
        Predictive configuration dictionary or None if not enabled
    """
    # Check if forecast is enabled
    forecast_enabled = config.get(CONF_FORECAST_ENABLED, DEFAULT_FORECAST_ENABLED)
    
    # Handle string values for boolean fields
    if isinstance(forecast_enabled, str):
        forecast_enabled = forecast_enabled.lower() == "true"
    
    if not forecast_enabled:
        _LOGGER.debug("Weather forecast is disabled in configuration")
        return None
    
    # Check if weather entity is configured
    weather_entity = config.get(CONF_WEATHER_ENTITY)
    if not weather_entity:
        _LOGGER.warning("Weather forecast enabled but no weather entity configured")
        return None
    
    # Build heat wave strategy
    heat_wave_strategy = {
        "name": "heat_wave",
        "enabled": True,
        "strategy_type": "heat_wave",
        "temp_threshold_c": config.get(
            CONF_HEAT_WAVE_TEMP_THRESHOLD, DEFAULT_HEAT_WAVE_TEMP_THRESHOLD
        ),
        "min_duration_hours": config.get(
            CONF_HEAT_WAVE_MIN_DURATION_HOURS, DEFAULT_HEAT_WAVE_MIN_DURATION_HOURS
        ),
        "lookahead_hours": config.get(
            CONF_HEAT_WAVE_LOOKAHEAD_HOURS, DEFAULT_HEAT_WAVE_LOOKAHEAD_HOURS
        ),
        "pre_action_hours": config.get(
            CONF_HEAT_WAVE_PRE_ACTION_HOURS, DEFAULT_HEAT_WAVE_PRE_ACTION_HOURS
        ),
        "adjustment": config.get(
            CONF_HEAT_WAVE_ADJUSTMENT, DEFAULT_HEAT_WAVE_ADJUSTMENT
        ),
    }
    
    # Build clear sky strategy
    clear_sky_strategy = {
        "name": "clear_sky",
        "enabled": True,
        "strategy_type": "clear_sky",
        "condition": config.get(
            CONF_CLEAR_SKY_CONDITION, DEFAULT_CLEAR_SKY_CONDITION
        ),
        "min_duration_hours": config.get(
            CONF_CLEAR_SKY_MIN_DURATION_HOURS, DEFAULT_CLEAR_SKY_MIN_DURATION_HOURS
        ),
        "lookahead_hours": config.get(
            CONF_CLEAR_SKY_LOOKAHEAD_HOURS, DEFAULT_CLEAR_SKY_LOOKAHEAD_HOURS
        ),
        "pre_action_hours": config.get(
            CONF_CLEAR_SKY_PRE_ACTION_HOURS, DEFAULT_CLEAR_SKY_PRE_ACTION_HOURS
        ),
        "adjustment": config.get(
            CONF_CLEAR_SKY_ADJUSTMENT, DEFAULT_CLEAR_SKY_ADJUSTMENT
        ),
    }
    
    # Build predictive configuration
    predictive_config = {
        "weather_entity": weather_entity,
        "strategies": [heat_wave_strategy, clear_sky_strategy]
    }
    
    _LOGGER.debug(
        "Built predictive config with weather entity '%s' and %d strategies",
        weather_entity,
        len(predictive_config["strategies"])
    )
    
    return predictive_config