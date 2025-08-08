"""Test for beta9 weather strategy configuration fix."""

import pytest
from unittest.mock import patch
from custom_components.smart_climate.config_helpers import build_predictive_config
from custom_components.smart_climate.forecast_engine import ForecastEngine
from custom_components.smart_climate import const


def test_config_helpers_creates_correct_keys():
    """Test that config_helpers creates the correct key names for ForecastEngine."""
    config = {
        const.CONF_FORECAST_ENABLED: True,
        const.CONF_WEATHER_ENTITY: "weather.forecast_sachsenheim_tu",
        const.CONF_HEAT_WAVE_TEMP_THRESHOLD: 30.0,
        const.CONF_HEAT_WAVE_MIN_DURATION_HOURS: 5,
        const.CONF_HEAT_WAVE_LOOKAHEAD_HOURS: 48,
        const.CONF_HEAT_WAVE_PRE_ACTION_HOURS: 4,
        const.CONF_HEAT_WAVE_ADJUSTMENT: -2.0,
        const.CONF_CLEAR_SKY_CONDITION: "sunny",
        const.CONF_CLEAR_SKY_MIN_DURATION_HOURS: 6,
        const.CONF_CLEAR_SKY_LOOKAHEAD_HOURS: 24,
        const.CONF_CLEAR_SKY_PRE_ACTION_HOURS: 1,
        const.CONF_CLEAR_SKY_ADJUSTMENT: -1.5,
    }
    
    result = build_predictive_config(config)
    
    # Verify structure is correct
    assert result is not None
    assert "weather_entity" in result
    assert "strategies" in result
    assert len(result["strategies"]) == 2
    
    # Check heat wave strategy has correct keys
    heat_wave = result["strategies"][0]
    assert heat_wave["strategy_type"] == "heat_wave"  # Not "type"
    assert heat_wave["temp_threshold_c"] == 30.0  # Not "temp_threshold"
    
    # Check clear sky strategy has correct keys
    clear_sky = result["strategies"][1]
    assert clear_sky["strategy_type"] == "clear_sky"  # Not "type"
    assert clear_sky["condition"] == "sunny"  # This was already correct


def test_forecast_engine_accepts_config_helper_format():
    """Test that ForecastEngine can process config from config_helpers without warnings."""
    config = {
        const.CONF_FORECAST_ENABLED: True,
        const.CONF_WEATHER_ENTITY: "weather.test",
        const.CONF_HEAT_WAVE_TEMP_THRESHOLD: 28.0,
        const.CONF_CLEAR_SKY_CONDITION: "sunny",
    }
    
    # Build config through config_helpers
    predictive_config = build_predictive_config(config)
    
    # Mock HomeAssistant
    hass = None  # ForecastEngine doesn't actually use it in __init__
    
    # Create ForecastEngine - should not produce warnings
    with patch('custom_components.smart_climate.forecast_engine._LOGGER') as mock_logger:
        engine = ForecastEngine(hass, predictive_config)
        
        # Verify strategies were loaded
        assert len(engine._strategies) == 2
        
        # No warnings about configuration
        for call in mock_logger.warning.call_args_list:
            assert "Unknown strategy type" not in str(call)


def test_forecast_engine_backward_compatible_with_legacy_format():
    """Test that ForecastEngine still works with legacy config format."""
    # Legacy format (what might be stored in existing configs)
    legacy_config = {
        "weather_entity": "weather.test",
        "strategies": [
            {
                "name": "heat_wave",
                "enabled": True,
                "type": "heat_wave",  # Legacy uses "type"
                "temp_threshold": 28.0,  # Legacy uses "temp_threshold"
                "min_duration_hours": 5,
                "lookahead_hours": 48,
                "pre_action_hours": 4,
                "adjustment_c": -2.0,  # Legacy uses "adjustment_c"
            },
            {
                "name": "clear_sky",
                "enabled": True,
                "type": "clear_sky",  # Legacy uses "type"
                "condition": "sunny",
                "min_duration_hours": 6,
                "lookahead_hours": 24,
                "pre_action_hours": 1,
                "adjustment_c": -1.5,  # Legacy uses "adjustment_c"
            }
        ]
    }
    
    # Create ForecastEngine with legacy config
    hass = None
    with patch('custom_components.smart_climate.forecast_engine._LOGGER') as mock_logger:
        engine = ForecastEngine(hass, legacy_config)
        
        # Verify strategies were loaded
        assert len(engine._strategies) == 2
        
        # No warnings about unknown strategy types
        warning_calls = [
            call for call in mock_logger.warning.call_args_list
            if "Unknown strategy type" in str(call)
        ]
        assert len(warning_calls) == 0


def test_forecast_engine_handles_mixed_format():
    """Test that ForecastEngine can handle mixed old and new format."""
    mixed_config = {
        "weather_entity": "weather.test",
        "strategies": [
            {
                "name": "heat_wave",
                "enabled": True,
                "strategy_type": "heat_wave",  # New format
                "temp_threshold_c": 28.0,  # New format
                "adjustment": -2.0,  # New format
            },
            {
                "name": "clear_sky",  
                "enabled": True,
                "type": "clear_sky",  # Old format
                "condition": "sunny",
                "adjustment_c": -1.5,  # Old format
            }
        ]
    }
    
    hass = None
    with patch('custom_components.smart_climate.forecast_engine._LOGGER') as mock_logger:
        engine = ForecastEngine(hass, mixed_config)
        
        # Both strategies should load
        assert len(engine._strategies) == 2
        
        # No warnings
        for call in mock_logger.warning.call_args_list:
            assert "Unknown strategy type" not in str(call)