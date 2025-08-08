"""Test weather strategy configuration fix for beta9."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from custom_components.smart_climate.config_helpers import build_predictive_config
from custom_components.smart_climate.forecast_engine import ForecastEngine, Forecast
from custom_components.smart_climate import const


@pytest.fixture
def config_with_weather():
    """Create a configuration with weather forecast enabled."""
    return {
        const.CONF_FORECAST_ENABLED: True,
        const.CONF_WEATHER_ENTITY: "weather.test",
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


def test_build_predictive_config_creates_correct_strategy_keys(config_with_weather):
    """Test that build_predictive_config creates strategies with correct keys."""
    result = build_predictive_config(config_with_weather)
    
    assert result is not None
    assert "strategies" in result
    assert len(result["strategies"]) == 2
    
    # Check heat wave strategy
    heat_wave = result["strategies"][0]
    assert heat_wave["name"] == "heat_wave"
    assert heat_wave["strategy_type"] == "heat_wave"  # Fixed from "type"
    assert heat_wave["temp_threshold_c"] == 30.0  # Fixed from "temp_threshold"
    assert heat_wave["min_duration_hours"] == 5
    assert heat_wave["lookahead_hours"] == 48
    assert heat_wave["pre_action_hours"] == 4
    assert heat_wave["adjustment"] == -2.0
    
    # Check clear sky strategy
    clear_sky = result["strategies"][1]
    assert clear_sky["name"] == "clear_sky"
    assert clear_sky["strategy_type"] == "clear_sky"  # Fixed from "type"
    assert clear_sky["condition"] == "sunny"  # Correct key
    assert clear_sky["min_duration_hours"] == 6
    assert clear_sky["lookahead_hours"] == 24
    assert clear_sky["pre_action_hours"] == 1
    assert clear_sky["adjustment"] == -1.5


@pytest.mark.asyncio
async def test_forecast_engine_recognizes_strategy_types(hass, config_with_weather):
    """Test that ForecastEngine properly recognizes strategy types after fix."""
    predictive_config = build_predictive_config(config_with_weather)
    
    # Create ForecastEngine
    engine = ForecastEngine(hass, predictive_config)
    
    # Mock forecast data
    now = datetime.now()
    forecast_data = [
        Forecast(datetime=now + timedelta(hours=i), temperature=32.0, condition="sunny")
        for i in range(24)
    ]
    
    # Set forecast data directly
    engine._forecast_data = forecast_data
    
    # Evaluate strategies - should not produce warnings about unknown strategy types
    with patch('custom_components.smart_climate.forecast_engine._LOGGER') as mock_logger:
        engine._evaluate_strategies(now)
        
        # Check that no warnings about unknown strategy types were logged
        warning_calls = [
            call for call in mock_logger.warning.call_args_list
            if "Unknown strategy type" in str(call)
        ]
        assert len(warning_calls) == 0, "Should not warn about unknown strategy types"
        
        # Check that debug messages show correct strategy types
        debug_calls = [
            call for call in mock_logger.debug.call_args_list
            if "Evaluating" in str(call) and "strategy" in str(call)
        ]
        assert len(debug_calls) >= 2, "Should have debug messages for both strategies"


@pytest.mark.asyncio
async def test_heat_wave_strategy_evaluation_with_fixed_keys(hass, config_with_weather):
    """Test that heat wave strategy evaluates correctly with fixed key names."""
    predictive_config = build_predictive_config(config_with_weather)
    engine = ForecastEngine(hass, predictive_config)
    
    # Create forecast data that should trigger heat wave
    now = datetime.now()
    forecast_data = [
        Forecast(datetime=now + timedelta(hours=i), temperature=31.0, condition="sunny")
        for i in range(10)  # 10 hours above 30°C threshold
    ]
    
    engine._forecast_data = forecast_data
    
    # Evaluate strategies
    engine._evaluate_strategies(now)
    
    # Check if heat wave strategy was activated
    assert engine._active_strategy is not None
    assert engine._active_strategy.name == "heat_wave"
    assert engine._active_strategy.adjustment == -2.0


@pytest.mark.asyncio
async def test_clear_sky_strategy_evaluation_with_fixed_keys(hass, config_with_weather):
    """Test that clear sky strategy evaluates correctly with fixed key names."""
    predictive_config = build_predictive_config(config_with_weather)
    engine = ForecastEngine(hass, predictive_config)
    
    # Create forecast data that should trigger clear sky
    now = datetime.now()
    forecast_data = [
        Forecast(datetime=now + timedelta(hours=i), temperature=25.0, condition="sunny")
        for i in range(8)  # 8 hours of sunny conditions
    ]
    
    engine._forecast_data = forecast_data
    
    # Evaluate strategies
    engine._evaluate_strategies(now)
    
    # Check if clear sky strategy was activated
    assert engine._active_strategy is not None
    assert engine._active_strategy.name == "clear_sky"
    assert engine._active_strategy.adjustment == -1.5