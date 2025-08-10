"""Integration tests for updated weather strategies with current state checking."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from dataclasses import dataclass
from typing import List, Optional

from custom_components.smart_climate.models import Forecast, ActiveStrategy
from custom_components.smart_climate.forecast_engine import ForecastEngine


class TestWeatherStrategyIntegration:
    """Integration tests for weather strategies with current state checking."""

    def test_heat_wave_already_active_with_weather_entity_should_not_precool(self):
        """Test that heat wave strategy doesn't activate when weather entity shows current hot conditions."""
        mock_hass = Mock()
        
        # Mock weather entity showing current hot conditions (above threshold)
        mock_weather_state = Mock()
        mock_weather_state.state = "sunny"
        mock_weather_state.attributes = {"temperature": 30.5}  # Above 29.0°C threshold
        mock_hass.states.get.return_value = mock_weather_state
        
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Set up future forecast data (shouldn't matter due to current state check)
        base_time = datetime(2025, 7, 13, 10, 0, 0)
        current_time = datetime(2025, 7, 13, 10, 39, 0)  # Currently 10:39
        
        engine._forecast_data = []
        for i in range(1, 25):  # Future hours only
            hour_time = base_time + timedelta(hours=i)
            temp = 25.0  # Cool forecast
            engine._forecast_data.append(Forecast(
                datetime=hour_time,
                temperature=temp,
                condition="cloudy"
            ))

        strategy_config = {
            "name": "Heat Wave Pre-Cool",
            "temp_threshold_c": 29.0,
            "min_duration_hours": 5,
            "lookahead_hours": 24,
            "pre_action_hours": 2,
            "adjustment_c": -1.5
        }

        # Strategy should NOT activate because we're currently hot (30.5°C > 29.0°C threshold)
        engine._evaluate_heat_wave_strategy(strategy_config, current_time)
        
        assert engine._active_strategy is None, "Strategy should not activate when currently above temperature threshold"

    def test_clear_sky_already_active_with_weather_entity_should_not_precool(self):
        """Test that clear sky strategy doesn't activate when weather entity shows current sunny conditions."""
        mock_hass = Mock()
        
        # Mock weather entity showing current sunny conditions
        mock_weather_state = Mock()
        mock_weather_state.state = "sunny"  # Current condition matches target
        mock_weather_state.attributes = {"temperature": 25.0}
        mock_hass.states.get.return_value = mock_weather_state
        
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Set up future forecast data (shouldn't matter due to current state check)
        base_time = datetime(2025, 7, 13, 10, 0, 0) 
        current_time = datetime(2025, 7, 13, 10, 39, 0)  # Currently 10:39
        
        engine._forecast_data = []
        for i in range(1, 25):  # Future hours only
            hour_time = base_time + timedelta(hours=i)
            condition = "cloudy"  # Cloudy forecast
            engine._forecast_data.append(Forecast(
                datetime=hour_time,
                temperature=25.0,
                condition=condition
            ))

        strategy_config = {
            "name": "Sunny Day Thermal Gain", 
            "condition": "sunny",
            "min_duration_hours": 6,
            "lookahead_hours": 24,
            "pre_action_hours": 1,
            "adjustment": -1.0
        }

        # Strategy should NOT activate because we're currently sunny
        engine._evaluate_clear_sky_strategy(strategy_config, current_time)
        
        assert engine._active_strategy is None, "Strategy should not activate when currently in target condition"