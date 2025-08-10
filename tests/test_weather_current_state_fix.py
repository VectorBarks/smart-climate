"""Tests for weather strategy current state checking fix."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass
from typing import List, Optional

# Import our modules
from custom_components.smart_climate.models import Forecast, ActiveStrategy
from custom_components.smart_climate.forecast_engine import ForecastEngine


class TestWeatherCurrentStateFix:
    """Test weather entity current state checking before forecast evaluation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_hass = Mock()
        self.mock_hass.states = Mock()
        
        self.config = {
            "weather_entity": "weather.local",
            "strategies": [
                {
                    "name": "Clear Sky Test",
                    "strategy_type": "clear_sky",
                    "enabled": True,
                    "condition": "sunny",
                    "lookahead_hours": 24,
                    "min_duration_hours": 6,
                    "pre_action_hours": 1,
                    "adjustment": -1.0
                },
                {
                    "name": "Heat Wave Test", 
                    "strategy_type": "heat_wave",
                    "enabled": True,
                    "temp_threshold_c": 30.0,
                    "lookahead_hours": 48,
                    "min_duration_hours": 5,
                    "pre_action_hours": 4,
                    "adjustment": -2.0
                }
            ]
        }
        
        self.engine = ForecastEngine(self.mock_hass, self.config)
        
        # Mock forecast data for future events
        base_time = datetime(2025, 8, 10, 10, 0, 0)  # 10:00 AM
        self.future_forecasts = [
            Forecast(datetime=base_time + timedelta(hours=i), temperature=25.0 + i, condition="cloudy") 
            for i in range(1, 25)  # Future hours 11:00-10:00 next day
        ]
        # Add a sunny period starting at 2 PM (4 hours from base_time)
        for i in range(4, 10):  # 2 PM - 8 PM = 6 hours of sun
            self.future_forecasts[i-1] = Forecast(
                datetime=base_time + timedelta(hours=i), 
                temperature=32.0,  # High temp during sunny period
                condition="sunny"
            )
        
        self.engine._forecast_data = self.future_forecasts

    def test_clear_sky_current_sunny_skips_precooling(self):
        """Test clear sky strategy skips pre-cooling when currently sunny."""
        # Mock weather entity showing current sunny conditions
        mock_weather_state = Mock()
        mock_weather_state.state = "sunny"
        self.mock_hass.states.get.return_value = mock_weather_state
        
        current_time = datetime(2025, 8, 10, 13, 0, 0)  # 1 PM - pre-action time for 2 PM event
        
        # This should NOT activate because we're already sunny
        self.engine._evaluate_clear_sky_strategy(self.config["strategies"][0], current_time)
        
        assert self.engine._active_strategy is None, "Should skip pre-cooling when currently sunny"

    def test_clear_sky_current_cloudy_checks_forecast(self):
        """Test clear sky strategy checks forecast when currently cloudy."""
        # Mock weather entity showing current cloudy conditions  
        mock_weather_state = Mock()
        mock_weather_state.state = "cloudy"
        self.mock_hass.states.get.return_value = mock_weather_state
        
        current_time = datetime(2025, 8, 10, 13, 0, 0)  # 1 PM - pre-action time for 2 PM sunny event
        
        # This SHOULD activate because we're cloudy now but sunny period coming
        self.engine._evaluate_clear_sky_strategy(self.config["strategies"][0], current_time)
        
        assert self.engine._active_strategy is not None, "Should activate when currently cloudy but sunny period coming"
        assert self.engine._active_strategy.adjustment == -1.0

    def test_clear_sky_no_weather_entity_checks_forecast(self):
        """Test clear sky strategy checks forecast when no weather entity configured."""
        # Test engine without weather entity
        config_no_weather = dict(self.config)
        config_no_weather["weather_entity"] = None
        engine_no_weather = ForecastEngine(self.mock_hass, config_no_weather)
        engine_no_weather._forecast_data = self.future_forecasts
        
        current_time = datetime(2025, 8, 10, 13, 0, 0)  # 1 PM - pre-action time
        
        # Should check forecast normally when no weather entity
        engine_no_weather._evaluate_clear_sky_strategy(self.config["strategies"][0], current_time)
        
        assert engine_no_weather._active_strategy is not None, "Should check forecast when no weather entity"

    def test_clear_sky_weather_entity_unavailable_checks_forecast(self):
        """Test clear sky strategy checks forecast when weather entity unavailable."""
        # Mock weather entity unavailable
        self.mock_hass.states.get.return_value = None
        
        current_time = datetime(2025, 8, 10, 13, 0, 0)  # 1 PM
        
        # Should continue to check forecast when weather entity unavailable
        self.engine._evaluate_clear_sky_strategy(self.config["strategies"][0], current_time)
        
        assert self.engine._active_strategy is not None, "Should check forecast when weather entity unavailable"

    def test_heat_wave_current_hot_skips_precooling(self):
        """Test heat wave strategy skips pre-cooling when currently hot enough."""
        # Mock weather entity with current temperature above threshold
        mock_weather_state = Mock()
        mock_weather_state.state = "sunny"
        mock_weather_state.attributes = {"temperature": 32.0}  # Above 30.0°C threshold
        self.mock_hass.states.get.return_value = mock_weather_state
        
        current_time = datetime(2025, 8, 10, 10, 0, 0)  # 10 AM - before pre-action time
        
        # This should NOT activate because we're already hot
        self.engine._evaluate_heat_wave_strategy(self.config["strategies"][1], current_time) 
        
        assert self.engine._active_strategy is None, "Should skip pre-cooling when currently hot"

    def test_heat_wave_current_cool_checks_forecast(self):
        """Test heat wave strategy checks forecast when currently cool."""
        # Mock weather entity with current temperature below threshold
        mock_weather_state = Mock()
        mock_weather_state.state = "cloudy"
        mock_weather_state.attributes = {"temperature": 25.0}  # Below 30.0°C threshold
        self.mock_hass.states.get.return_value = mock_weather_state
        
        current_time = datetime(2025, 8, 10, 10, 0, 0)  # 10 AM - before any hot periods
        
        # This should check forecast and potentially activate
        self.engine._evaluate_heat_wave_strategy(self.config["strategies"][1], current_time)
        
        # In our test data, there's a hot period at 2 PM (32°C), pre-action starts at 10 AM
        # Since current time (10 AM) is exactly when pre-action should start, strategy should activate
        assert self.engine._active_strategy is not None, "Should activate when currently cool but hot period coming"
        assert self.engine._active_strategy.adjustment == -2.0

    def test_heat_wave_no_temperature_attribute_checks_forecast(self):
        """Test heat wave strategy checks forecast when temperature attribute missing."""
        # Mock weather entity without temperature attribute
        mock_weather_state = Mock()
        mock_weather_state.state = "sunny"
        mock_weather_state.attributes = {}  # No temperature
        self.mock_hass.states.get.return_value = mock_weather_state
        
        current_time = datetime(2025, 8, 10, 10, 0, 0)  # 10 AM
        
        # Should continue to check forecast when no temperature attribute
        self.engine._evaluate_heat_wave_strategy(self.config["strategies"][1], current_time)
        
        assert self.engine._active_strategy is not None, "Should check forecast when no temperature attribute"

    def test_heat_wave_invalid_temperature_checks_forecast(self):
        """Test heat wave strategy checks forecast when temperature attribute is None."""
        # Mock weather entity with None temperature
        mock_weather_state = Mock()
        mock_weather_state.state = "sunny"
        mock_weather_state.attributes = {"temperature": None}
        self.mock_hass.states.get.return_value = mock_weather_state
        
        current_time = datetime(2025, 8, 10, 10, 0, 0)  # 10 AM
        
        # Should continue to check forecast when temperature is None
        self.engine._evaluate_heat_wave_strategy(self.config["strategies"][1], current_time)
        
        assert self.engine._active_strategy is not None, "Should check forecast when temperature is None"

    def test_both_strategies_current_conditions_present(self):
        """Test both strategies skip when current conditions match their triggers."""
        # Mock weather entity showing both sunny and hot conditions currently
        mock_weather_state = Mock()
        mock_weather_state.state = "sunny"
        mock_weather_state.attributes = {"temperature": 31.0}  # Above heat wave threshold
        self.mock_hass.states.get.return_value = mock_weather_state
        
        current_time = datetime(2025, 8, 10, 13, 0, 0)  # 1 PM
        
        # Neither strategy should activate
        self.engine._evaluate_clear_sky_strategy(self.config["strategies"][0], current_time)
        assert self.engine._active_strategy is None, "Clear sky should skip when currently sunny"
        
        self.engine._evaluate_heat_wave_strategy(self.config["strategies"][1], current_time)
        assert self.engine._active_strategy is None, "Heat wave should skip when currently hot"

    def test_logging_current_state_checks(self):
        """Test that current state checks are properly logged."""
        # Mock weather entity showing sunny conditions
        mock_weather_state = Mock()
        mock_weather_state.state = "sunny"
        mock_weather_state.attributes = {"temperature": 32.0}
        self.mock_hass.states.get.return_value = mock_weather_state
        
        current_time = datetime(2025, 8, 10, 13, 0, 0)
        
        with patch('custom_components.smart_climate.forecast_engine._LOGGER') as mock_logger:
            # Test clear sky strategy logging
            self.engine._evaluate_clear_sky_strategy(self.config["strategies"][0], current_time)
            
            # Should log that we're skipping because currently sunny
            mock_logger.info.assert_called_with("Weather: Currently %s - skipping pre-cooling", "sunny")
            
            # Test heat wave strategy logging
            self.engine._evaluate_heat_wave_strategy(self.config["strategies"][1], current_time)
            
            # Should log that we're skipping because currently hot
            mock_logger.info.assert_called_with(
                "Weather: Currently %.1f°C (>= %.1f°C threshold) - skipping pre-cooling", 
                32.0, 30.0
            )

    def test_weather_entity_error_fallback(self):
        """Test graceful handling when weather entity access fails."""
        # Mock weather entity access that raises exception
        self.mock_hass.states.get.side_effect = Exception("Entity access failed")
        
        current_time = datetime(2025, 8, 10, 13, 0, 0)  # 1 PM
        
        # Should continue to check forecast despite weather entity error
        self.engine._evaluate_clear_sky_strategy(self.config["strategies"][0], current_time)
        
        assert self.engine._active_strategy is not None, "Should fallback to forecast check on weather entity error"