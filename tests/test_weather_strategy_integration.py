"""Integration test for weather strategy configuration through the full pipeline."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant

from custom_components.smart_climate.config_helpers import build_predictive_config
from custom_components.smart_climate.forecast_engine import ForecastEngine, Forecast
from custom_components.smart_climate import const


@pytest.mark.asyncio
async def test_full_pipeline_heat_wave_strategy():
    """Test the full pipeline from config to strategy activation."""
    # Create a config as it would come from the UI
    config = {
        const.CONF_FORECAST_ENABLED: True,
        const.CONF_WEATHER_ENTITY: "weather.test_entity",
        const.CONF_HEAT_WAVE_TEMP_THRESHOLD: 28.0,
        const.CONF_HEAT_WAVE_MIN_DURATION_HOURS: 4,
        const.CONF_HEAT_WAVE_LOOKAHEAD_HOURS: 24,
        const.CONF_HEAT_WAVE_PRE_ACTION_HOURS: 2,
        const.CONF_HEAT_WAVE_ADJUSTMENT: -1.5,
        const.CONF_CLEAR_SKY_CONDITION: "sunny",
        const.CONF_CLEAR_SKY_MIN_DURATION_HOURS: 3,
        const.CONF_CLEAR_SKY_LOOKAHEAD_HOURS: 12,
        const.CONF_CLEAR_SKY_PRE_ACTION_HOURS: 1,
        const.CONF_CLEAR_SKY_ADJUSTMENT: -1.0,
    }
    
    # Build predictive config
    predictive_config = build_predictive_config(config)
    assert predictive_config is not None
    
    # Create mock HomeAssistant
    hass = Mock()
    
    # Create ForecastEngine with the config
    engine = ForecastEngine(hass, predictive_config)
    
    # Verify strategies were loaded correctly
    assert len(engine._strategies) == 2
    
    # Set up forecast data that should trigger heat wave
    now = datetime.now()
    engine._forecast_data = [
        Forecast(datetime=now + timedelta(hours=i), temperature=29.0, condition="sunny")
        for i in range(1, 6)  # 5 hours of 29°C (above 28°C threshold for 4+ hours)
    ]
    
    # Evaluate strategies - heat wave should activate
    engine._evaluate_strategies(now)
    
    # Verify heat wave strategy was activated
    assert engine._active_strategy is not None
    assert engine._active_strategy.name == "heat_wave"
    assert engine._active_strategy.adjustment == -1.5
    assert engine.predictive_offset == -1.5


@pytest.mark.asyncio
async def test_full_pipeline_clear_sky_strategy():
    """Test the full pipeline for clear sky strategy activation."""
    # Create a config as it would come from the UI
    config = {
        const.CONF_FORECAST_ENABLED: True,
        const.CONF_WEATHER_ENTITY: "weather.test_entity",
        const.CONF_HEAT_WAVE_TEMP_THRESHOLD: 35.0,  # High threshold so it won't trigger
        const.CONF_HEAT_WAVE_MIN_DURATION_HOURS: 10,
        const.CONF_HEAT_WAVE_LOOKAHEAD_HOURS: 24,
        const.CONF_HEAT_WAVE_PRE_ACTION_HOURS: 2,
        const.CONF_HEAT_WAVE_ADJUSTMENT: -2.0,
        const.CONF_CLEAR_SKY_CONDITION: "clear-night",
        const.CONF_CLEAR_SKY_MIN_DURATION_HOURS: 3,
        const.CONF_CLEAR_SKY_LOOKAHEAD_HOURS: 12,
        const.CONF_CLEAR_SKY_PRE_ACTION_HOURS: 0,  # Immediate activation
        const.CONF_CLEAR_SKY_ADJUSTMENT: -0.5,
    }
    
    # Build predictive config
    predictive_config = build_predictive_config(config)
    assert predictive_config is not None
    
    # Create mock HomeAssistant
    hass = Mock()
    
    # Create ForecastEngine with the config
    engine = ForecastEngine(hass, predictive_config)
    
    # Set up forecast data that should trigger clear sky (but not heat wave)
    now = datetime.now()
    engine._forecast_data = [
        Forecast(datetime=now + timedelta(hours=i), temperature=22.0, condition="clear-night")
        for i in range(1, 5)  # 4 hours of clear-night (3+ hours required)
    ]
    
    # Evaluate strategies - clear sky should activate
    engine._evaluate_strategies(now)
    
    # Verify clear sky strategy was activated
    assert engine._active_strategy is not None
    assert engine._active_strategy.name == "clear_sky"
    assert engine._active_strategy.adjustment == -0.5
    assert engine.predictive_offset == -0.5


@pytest.mark.asyncio
async def test_no_strategy_activation_with_config():
    """Test that strategies don't activate when conditions aren't met."""
    # Create a config with high thresholds
    config = {
        const.CONF_FORECAST_ENABLED: True,
        const.CONF_WEATHER_ENTITY: "weather.test_entity",
        const.CONF_HEAT_WAVE_TEMP_THRESHOLD: 40.0,  # Very high threshold
        const.CONF_HEAT_WAVE_MIN_DURATION_HOURS: 10,
        const.CONF_HEAT_WAVE_LOOKAHEAD_HOURS: 24,
        const.CONF_HEAT_WAVE_PRE_ACTION_HOURS: 2,
        const.CONF_HEAT_WAVE_ADJUSTMENT: -2.0,
        const.CONF_CLEAR_SKY_CONDITION: "rainy",  # Look for rain
        const.CONF_CLEAR_SKY_MIN_DURATION_HOURS: 6,
        const.CONF_CLEAR_SKY_LOOKAHEAD_HOURS: 12,
        const.CONF_CLEAR_SKY_PRE_ACTION_HOURS: 1,
        const.CONF_CLEAR_SKY_ADJUSTMENT: -1.0,
    }
    
    # Build predictive config
    predictive_config = build_predictive_config(config)
    assert predictive_config is not None
    
    # Create mock HomeAssistant
    hass = Mock()
    
    # Create ForecastEngine with the config
    engine = ForecastEngine(hass, predictive_config)
    
    # Set up forecast data that won't trigger either strategy
    now = datetime.now()
    engine._forecast_data = [
        Forecast(datetime=now + timedelta(hours=i), temperature=25.0, condition="sunny")
        for i in range(1, 10)  # Sunny and mild - won't trigger either strategy
    ]
    
    # Evaluate strategies - nothing should activate
    engine._evaluate_strategies(now)
    
    # Verify no strategy was activated
    assert engine._active_strategy is None
    assert engine.predictive_offset == 0.0


def test_config_helper_handles_missing_weather_entity():
    """Test that config helper returns None when weather entity is missing."""
    config = {
        const.CONF_FORECAST_ENABLED: True,
        # No CONF_WEATHER_ENTITY
    }
    
    with patch('custom_components.smart_climate.config_helpers._LOGGER') as mock_logger:
        result = build_predictive_config(config)
        assert result is None
        mock_logger.warning.assert_called_with("Weather forecast enabled but no weather entity configured")


def test_config_helper_handles_disabled_forecast():
    """Test that config helper returns None when forecast is disabled."""
    config = {
        const.CONF_FORECAST_ENABLED: False,
        const.CONF_WEATHER_ENTITY: "weather.test",
    }
    
    result = build_predictive_config(config)
    assert result is None