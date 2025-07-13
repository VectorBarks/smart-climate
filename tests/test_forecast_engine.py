"""Tests for ForecastEngine component."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass
from typing import List, Optional

# Import our modules
from custom_components.smart_climate.models import Forecast, ActiveStrategy
from custom_components.smart_climate.forecast_engine import ForecastEngine


class TestForecastDataClasses:
    """Test data classes used by ForecastEngine."""

    def test_forecast_dataclass(self):
        """Test Forecast dataclass creation."""
        test_datetime = datetime(2025, 7, 13, 15, 0, 0)
        forecast = Forecast(
            datetime=test_datetime,
            temperature=25.5,
            condition="sunny"
        )
        
        assert forecast.datetime == test_datetime
        assert forecast.temperature == 25.5
        assert forecast.condition == "sunny"

    def test_forecast_dataclass_optional_condition(self):
        """Test Forecast dataclass with optional condition."""
        test_datetime = datetime(2025, 7, 13, 15, 0, 0)
        forecast = Forecast(
            datetime=test_datetime,
            temperature=25.5
        )
        
        assert forecast.datetime == test_datetime
        assert forecast.temperature == 25.5
        assert forecast.condition is None

    def test_active_strategy_dataclass(self):
        """Test ActiveStrategy dataclass creation."""
        test_end_time = datetime(2025, 7, 13, 20, 0, 0)
        strategy = ActiveStrategy(
            name="Test Strategy",
            adjustment=-1.5,
            end_time=test_end_time
        )
        
        assert strategy.name == "Test Strategy"
        assert strategy.adjustment == -1.5
        assert strategy.end_time == test_end_time


class TestForecastEngineInitialization:
    """Test ForecastEngine initialization."""

    def test_init_basic_config(self):
        """Test ForecastEngine initialization with basic config."""
        mock_hass = Mock()
        config = {
            "weather_entity": "weather.test",
            "strategies": [
                {"name": "Test", "enabled": True, "strategy_type": "heat_wave"}
            ]
        }
        
        engine = ForecastEngine(mock_hass, config)
        
        assert engine._hass == mock_hass
        assert engine._weather_entity == "weather.test"
        assert len(engine._strategies) == 1
        assert engine._strategies[0]["name"] == "Test"
        assert engine._forecast_data == []
        assert engine._active_strategy is None
        assert engine._last_update is None

    def test_init_filters_disabled_strategies(self):
        """Test that disabled strategies are filtered out."""
        mock_hass = Mock()
        config = {
            "weather_entity": "weather.test",
            "strategies": [
                {"name": "Enabled", "enabled": True, "strategy_type": "heat_wave"},
                {"name": "Disabled", "enabled": False, "strategy_type": "clear_sky"},
                {"name": "Default", "strategy_type": "heat_wave"}  # enabled by default
            ]
        }
        
        engine = ForecastEngine(mock_hass, config)
        
        assert len(engine._strategies) == 2
        strategy_names = [s["name"] for s in engine._strategies]
        assert "Enabled" in strategy_names
        assert "Default" in strategy_names
        assert "Disabled" not in strategy_names

    def test_init_no_weather_entity(self):
        """Test initialization without weather entity."""
        mock_hass = Mock()
        config = {"strategies": []}
        
        engine = ForecastEngine(mock_hass, config)
        
        assert engine._weather_entity is None
        assert engine._strategies == []

    def test_init_empty_strategies(self):
        """Test initialization with empty strategies list."""
        mock_hass = Mock()
        config = {"weather_entity": "weather.test", "strategies": []}
        
        engine = ForecastEngine(mock_hass, config)
        
        assert engine._strategies == []


class TestPredictiveOffset:
    """Test predictive_offset property."""

    @patch('homeassistant.util.dt.utcnow')
    def test_no_active_strategy(self, mock_utcnow):
        """Test predictive_offset returns 0.0 when no strategy is active."""
        mock_hass = Mock()
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        assert engine.predictive_offset == 0.0

    def test_active_strategy_not_expired(self):
        """Test predictive_offset returns adjustment when strategy is active and not expired."""
        mock_hass = Mock()
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Set current time and strategy end time
        current_time = datetime(2025, 7, 13, 15, 0, 0)
        end_time = datetime(2025, 7, 13, 18, 0, 0)  # 3 hours in future
        
        # Set active strategy
        engine._active_strategy = ActiveStrategy(
            name="Test Strategy",
            adjustment=-1.5,
            end_time=end_time
        )
        
        with patch('homeassistant.util.dt.utcnow', return_value=current_time):
            assert engine.predictive_offset == -1.5

    def test_active_strategy_expired(self):
        """Test predictive_offset clears expired strategy and returns 0.0."""
        mock_hass = Mock()
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Set current time after strategy end time
        current_time = datetime(2025, 7, 13, 19, 0, 0)
        end_time = datetime(2025, 7, 13, 18, 0, 0)  # 1 hour in past
        
        # Set active strategy
        engine._active_strategy = ActiveStrategy(
            name="Test Strategy",
            adjustment=-1.5,
            end_time=end_time
        )
        
        with patch('homeassistant.util.dt.utcnow', return_value=current_time):
            result = engine.predictive_offset  # This should clear the expired strategy
            assert result == 0.0
            assert engine._active_strategy is None


class TestAsyncUpdate:
    """Test async_update method."""

    @pytest.mark.asyncio
    @patch('homeassistant.util.dt.utcnow')
    async def test_no_weather_entity_returns_early(self, mock_utcnow):
        """Test that async_update returns early when no weather entity configured."""
        mock_hass = Mock()
        config = {"strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Mock _async_fetch_forecast to track if it's called
        engine._async_fetch_forecast = AsyncMock()
        
        await engine.async_update()
        
        engine._async_fetch_forecast.assert_not_called()

    @pytest.mark.asyncio
    @patch('custom_components.smart_climate.forecast_engine.dt_util.utcnow')
    async def test_throttling_prevents_frequent_updates(self, mock_utcnow):
        """Test that async_update is throttled to prevent excessive API calls."""
        mock_hass = Mock()
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Set up time sequence
        first_call_time = datetime(2025, 7, 13, 15, 0, 0)
        second_call_time = datetime(2025, 7, 13, 15, 10, 0)  # 10 minutes later
        
        # Mock _async_fetch_forecast to track calls
        engine._async_fetch_forecast = AsyncMock(return_value=True)
        engine._evaluate_strategies = Mock()
        
        # First call - should fetch
        mock_utcnow.return_value = first_call_time
        await engine.async_update()
        
        assert engine._async_fetch_forecast.call_count == 1
        assert engine._last_update == first_call_time
        
        # Second call within throttle window - should not fetch
        mock_utcnow.return_value = second_call_time
        await engine.async_update()
        
        assert engine._async_fetch_forecast.call_count == 1  # Still 1, not called again
        assert engine._last_update == first_call_time  # Not updated

    @pytest.mark.asyncio
    @patch('custom_components.smart_climate.forecast_engine.dt_util.utcnow')
    async def test_update_after_throttle_period(self, mock_utcnow):
        """Test that async_update fetches after throttle period expires."""
        mock_hass = Mock()
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Set up time sequence
        first_call_time = datetime(2025, 7, 13, 15, 0, 0)
        second_call_time = datetime(2025, 7, 13, 15, 35, 0)  # 35 minutes later (> 30min throttle)
        
        # Mock methods
        engine._async_fetch_forecast = AsyncMock(return_value=True)
        engine._evaluate_strategies = Mock()
        
        # First call
        mock_utcnow.return_value = first_call_time
        await engine.async_update()
        
        # Second call after throttle period
        mock_utcnow.return_value = second_call_time
        await engine.async_update()
        
        assert engine._async_fetch_forecast.call_count == 2
        assert engine._last_update == second_call_time

    @pytest.mark.asyncio
    @patch('custom_components.smart_climate.forecast_engine.dt_util.utcnow')
    async def test_evaluate_strategies_called_on_successful_fetch(self, mock_utcnow):
        """Test that _evaluate_strategies is called when forecast fetch succeeds."""
        mock_hass = Mock()
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        current_time = datetime(2025, 7, 13, 15, 0, 0)
        mock_utcnow.return_value = current_time
        
        # Mock successful fetch
        engine._async_fetch_forecast = AsyncMock(return_value=True)
        engine._evaluate_strategies = Mock()
        
        await engine.async_update()
        
        engine._evaluate_strategies.assert_called_once_with(current_time)

    @pytest.mark.asyncio
    @patch('custom_components.smart_climate.forecast_engine.dt_util.utcnow')
    async def test_evaluate_strategies_not_called_on_failed_fetch(self, mock_utcnow):
        """Test that _evaluate_strategies is not called when forecast fetch fails."""
        mock_hass = Mock()
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        current_time = datetime(2025, 7, 13, 15, 0, 0)
        mock_utcnow.return_value = current_time
        
        # Mock failed fetch
        engine._async_fetch_forecast = AsyncMock(return_value=False)
        engine._evaluate_strategies = Mock()
        
        await engine.async_update()
        
        engine._evaluate_strategies.assert_not_called()


class TestAsyncFetchForecast:
    """Test _async_fetch_forecast method."""

    @pytest.mark.asyncio
    @patch('custom_components.smart_climate.forecast_engine.dt_util.parse_datetime')
    async def test_successful_fetch(self, mock_parse_datetime):
        """Test successful forecast fetch and parsing."""
        mock_hass = Mock()
        mock_hass.services.async_call = AsyncMock()
        
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Mock service response
        mock_response = {
            "weather.test": {
                "forecast": [
                    {
                        "datetime": "2025-07-13T15:00:00+00:00",
                        "temperature": 25.5,
                        "condition": "sunny"
                    },
                    {
                        "datetime": "2025-07-13T16:00:00+00:00", 
                        "temperature": 26.0,
                        "condition": "cloudy"
                    }
                ]
            }
        }
        mock_hass.services.async_call.return_value = mock_response
        
        # Mock datetime parsing
        expected_times = [
            datetime(2025, 7, 13, 15, 0, 0),
            datetime(2025, 7, 13, 16, 0, 0)
        ]
        mock_parse_datetime.side_effect = expected_times
        
        result = await engine._async_fetch_forecast()
        
        assert result is True
        assert len(engine._forecast_data) == 2
        
        # Check first forecast
        assert engine._forecast_data[0].datetime == expected_times[0]
        assert engine._forecast_data[0].temperature == 25.5
        assert engine._forecast_data[0].condition == "sunny"
        
        # Check second forecast
        assert engine._forecast_data[1].datetime == expected_times[1]
        assert engine._forecast_data[1].temperature == 26.0
        assert engine._forecast_data[1].condition == "cloudy"
        
        # Verify service call
        mock_hass.services.async_call.assert_called_once_with(
            "weather", "get_forecasts",
            {"entity_id": "weather.test", "type": "hourly"},
            blocking=True, return_response=True
        )

    @pytest.mark.asyncio
    async def test_fetch_handles_missing_condition(self):
        """Test forecast fetch handles missing condition field."""
        mock_hass = Mock()
        mock_hass.services.async_call = AsyncMock()
        
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Mock service response without condition
        mock_response = {
            "weather.test": {
                "forecast": [
                    {
                        "datetime": "2025-07-13T15:00:00+00:00",
                        "temperature": 25.5
                    }
                ]
            }
        }
        mock_hass.services.async_call.return_value = mock_response
        
        with patch('custom_components.smart_climate.forecast_engine.dt_util.parse_datetime') as mock_parse:
            mock_parse.return_value = datetime(2025, 7, 13, 15, 0, 0)
            
            result = await engine._async_fetch_forecast()
            
            assert result is True
            assert len(engine._forecast_data) == 1
            assert engine._forecast_data[0].condition is None

    @pytest.mark.asyncio
    async def test_fetch_handles_service_exception(self):
        """Test forecast fetch handles service call exceptions."""
        mock_hass = Mock()
        mock_hass.services.async_call = AsyncMock(side_effect=Exception("Service error"))
        
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        result = await engine._async_fetch_forecast()
        
        assert result is False
        assert engine._forecast_data == []

    @pytest.mark.asyncio
    async def test_fetch_handles_malformed_response(self):
        """Test forecast fetch handles malformed response."""
        mock_hass = Mock()
        mock_hass.services.async_call = AsyncMock()
        
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Mock malformed response
        mock_response = {"other_entity": {}}
        mock_hass.services.async_call.return_value = mock_response
        
        result = await engine._async_fetch_forecast()
        
        assert result is True
        assert engine._forecast_data == []


class TestFindConsecutiveEvent:
    """Test _find_consecutive_event helper method."""

    def test_event_found_and_long_enough(self):
        """Test finding a consecutive event that meets duration requirement."""
        mock_hass = Mock()
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Create test forecasts - 6 hours of high temperature
        base_time = datetime(2025, 7, 13, 10, 0, 0)
        forecasts = []
        for i in range(8):
            temp = 30.0 if 2 <= i <= 7 else 25.0  # Hours 2-7 are hot (6 hours)
            forecasts.append(Forecast(
                datetime=base_time + timedelta(hours=i),
                temperature=temp,
                condition="sunny"
            ))
        
        # Look for 5+ hours of temp >= 29°C
        min_duration = timedelta(hours=5)
        condition_checker = lambda f: f.temperature >= 29.0
        
        result = engine._find_consecutive_event(forecasts, min_duration, condition_checker)
        
        expected_start = base_time + timedelta(hours=2)
        assert result == expected_start

    def test_event_too_short(self):
        """Test that short events are not returned."""
        mock_hass = Mock()
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Create test forecasts - only 3 hours of high temperature
        base_time = datetime(2025, 7, 13, 10, 0, 0)
        forecasts = []
        for i in range(8):
            temp = 30.0 if 2 <= i <= 4 else 25.0  # Hours 2-4 are hot (3 hours)
            forecasts.append(Forecast(
                datetime=base_time + timedelta(hours=i),
                temperature=temp,
                condition="sunny"
            ))
        
        # Look for 5+ hours of temp >= 29°C
        min_duration = timedelta(hours=5)
        condition_checker = lambda f: f.temperature >= 29.0
        
        result = engine._find_consecutive_event(forecasts, min_duration, condition_checker)
        
        assert result is None

    def test_no_event_found(self):
        """Test when no event meets the condition."""
        mock_hass = Mock()
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Create test forecasts - no high temperatures
        base_time = datetime(2025, 7, 13, 10, 0, 0)
        forecasts = []
        for i in range(8):
            forecasts.append(Forecast(
                datetime=base_time + timedelta(hours=i),
                temperature=25.0,  # All temperatures are moderate
                condition="sunny"
            ))
        
        # Look for temp >= 29°C
        min_duration = timedelta(hours=5)
        condition_checker = lambda f: f.temperature >= 29.0
        
        result = engine._find_consecutive_event(forecasts, min_duration, condition_checker)
        
        assert result is None

    def test_multiple_short_events(self):
        """Test multiple short events that don't meet duration requirement."""
        mock_hass = Mock()
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Create test forecasts - two 2-hour events separated by a gap
        base_time = datetime(2025, 7, 13, 10, 0, 0)
        forecasts = []
        for i in range(10):
            # Hours 1-2 and 6-7 are hot, others are moderate
            temp = 30.0 if i in [1, 2, 6, 7] else 25.0
            forecasts.append(Forecast(
                datetime=base_time + timedelta(hours=i),
                temperature=temp,
                condition="sunny"
            ))
        
        # Look for 5+ hours of temp >= 29°C
        min_duration = timedelta(hours=5)
        condition_checker = lambda f: f.temperature >= 29.0
        
        result = engine._find_consecutive_event(forecasts, min_duration, condition_checker)
        
        assert result is None

    def test_event_at_end_of_forecast(self):
        """Test event that continues to the end of forecast list."""
        mock_hass = Mock()
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Create test forecasts - event starts at hour 3 and continues to end
        base_time = datetime(2025, 7, 13, 10, 0, 0)
        forecasts = []
        for i in range(8):
            temp = 30.0 if i >= 3 else 25.0  # Hours 3-7 are hot (5 hours)
            forecasts.append(Forecast(
                datetime=base_time + timedelta(hours=i),
                temperature=temp,
                condition="sunny"
            ))
        
        # Look for 5+ hours of temp >= 29°C
        min_duration = timedelta(hours=5)
        condition_checker = lambda f: f.temperature >= 29.0
        
        result = engine._find_consecutive_event(forecasts, min_duration, condition_checker)
        
        expected_start = base_time + timedelta(hours=3)
        assert result == expected_start


class TestEvaluateStrategies:
    """Test _evaluate_strategies method."""

    def test_no_strategies_configured(self):
        """Test strategy evaluation with no strategies configured."""
        mock_hass = Mock()
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        current_time = datetime(2025, 7, 13, 15, 0, 0)
        
        engine._evaluate_strategies(current_time)
        
        assert engine._active_strategy is None

    def test_strategy_evaluator_called(self):
        """Test that correct strategy evaluator is called."""
        mock_hass = Mock()
        config = {
            "weather_entity": "weather.test",
            "strategies": [
                {"name": "Heat Wave", "strategy_type": "heat_wave", "enabled": True}
            ]
        }
        engine = ForecastEngine(mock_hass, config)
        
        # Mock the evaluator method
        engine._evaluate_heat_wave_strategy = Mock()
        
        current_time = datetime(2025, 7, 13, 15, 0, 0)
        engine._evaluate_strategies(current_time)
        
        engine._evaluate_heat_wave_strategy.assert_called_once_with(
            {"name": "Heat Wave", "strategy_type": "heat_wave", "enabled": True},
            current_time
        )

    def test_unknown_strategy_type_ignored(self):
        """Test that unknown strategy types are safely ignored."""
        mock_hass = Mock()
        config = {
            "weather_entity": "weather.test", 
            "strategies": [
                {"name": "Unknown", "strategy_type": "unknown_type", "enabled": True}
            ]
        }
        engine = ForecastEngine(mock_hass, config)
        
        current_time = datetime(2025, 7, 13, 15, 0, 0)
        # Should not raise an exception
        engine._evaluate_strategies(current_time)
        
        assert engine._active_strategy is None

    def test_first_matching_strategy_wins(self):
        """Test that only the first matching strategy is activated."""
        mock_hass = Mock()
        config = {
            "weather_entity": "weather.test",
            "strategies": [
                {"name": "Strategy 1", "strategy_type": "heat_wave", "enabled": True},
                {"name": "Strategy 2", "strategy_type": "clear_sky", "enabled": True}
            ]
        }
        engine = ForecastEngine(mock_hass, config)
        
        # Mock both evaluators to activate strategies
        def activate_strategy_1(config_dict, now):
            engine._active_strategy = ActiveStrategy("Strategy 1", -1.0, now + timedelta(hours=1))
        
        def activate_strategy_2(config_dict, now):
            engine._active_strategy = ActiveStrategy("Strategy 2", 0.5, now + timedelta(hours=2))
        
        engine._evaluate_heat_wave_strategy = Mock(side_effect=activate_strategy_1)
        engine._evaluate_clear_sky_strategy = Mock(side_effect=activate_strategy_2)
        
        current_time = datetime(2025, 7, 13, 15, 0, 0)
        engine._evaluate_strategies(current_time)
        
        # Only first strategy should be called
        engine._evaluate_heat_wave_strategy.assert_called_once()
        engine._evaluate_clear_sky_strategy.assert_not_called()
        
        # First strategy should be active
        assert engine._active_strategy.name == "Strategy 1"

    def test_active_strategy_reset_before_evaluation(self):
        """Test that active strategy is reset before evaluation."""
        mock_hass = Mock()
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Set a pre-existing active strategy
        engine._active_strategy = ActiveStrategy("Old Strategy", -2.0, datetime(2025, 7, 13, 20, 0, 0))
        
        current_time = datetime(2025, 7, 13, 15, 0, 0)
        engine._evaluate_strategies(current_time)
        
        # Should be reset to None since no strategies are configured
        assert engine._active_strategy is None


class TestHeatWaveStrategy:
    """Test _evaluate_heat_wave_strategy method."""

    def test_heat_wave_detected_and_pre_action_time_reached(self):
        """Test heat wave strategy activation when conditions are met."""
        mock_hass = Mock()
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Set up forecast data - heat wave starting at hour 8 lasting 6 hours
        base_time = datetime(2025, 7, 13, 10, 0, 0)
        engine._forecast_data = []
        for i in range(24):
            temp = 30.0 if 8 <= i <= 13 else 25.0  # Hours 8-13 are hot (6 hours)
            engine._forecast_data.append(Forecast(
                datetime=base_time + timedelta(hours=i),
                temperature=temp,
                condition="sunny"
            ))
        
        # Strategy config
        strategy_config = {
            "name": "Heat Wave Pre-Cool",
            "temp_threshold_c": 29.0,
            "min_duration_hours": 5,
            "lookahead_hours": 48,
            "pre_action_hours": 4,
            "adjustment_c": -1.5
        }
        
        # Current time is 5 hours before heat wave (1 hour into pre-action period)
        current_time = base_time + timedelta(hours=5)  # Heat wave starts at hour 8, pre-action at hour 4
        
        engine._evaluate_heat_wave_strategy(strategy_config, current_time)
        
        assert engine._active_strategy is not None
        assert engine._active_strategy.name == "Heat Wave Pre-Cool"
        assert engine._active_strategy.adjustment == -1.5
        assert engine._active_strategy.end_time == base_time + timedelta(hours=8)

    def test_heat_wave_detected_but_pre_action_not_reached(self):
        """Test heat wave strategy not activated when pre-action time not reached."""
        mock_hass = Mock()
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Set up forecast data - heat wave starting at hour 8 lasting 6 hours
        base_time = datetime(2025, 7, 13, 10, 0, 0)
        engine._forecast_data = []
        for i in range(24):
            temp = 30.0 if 8 <= i <= 13 else 25.0
            engine._forecast_data.append(Forecast(
                datetime=base_time + timedelta(hours=i),
                temperature=temp,
                condition="sunny"
            ))
        
        # Strategy config
        strategy_config = {
            "name": "Heat Wave Pre-Cool",
            "temp_threshold_c": 29.0,
            "min_duration_hours": 5,
            "lookahead_hours": 48,
            "pre_action_hours": 4,
            "adjustment_c": -1.5
        }
        
        # Current time is 6 hours before heat wave (2 hours before pre-action)
        current_time = base_time + timedelta(hours=2)
        
        engine._evaluate_heat_wave_strategy(strategy_config, current_time)
        
        assert engine._active_strategy is None

    def test_heat_wave_too_short(self):
        """Test heat wave strategy not activated when duration too short."""
        mock_hass = Mock()
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Set up forecast data - short heat wave lasting only 3 hours
        base_time = datetime(2025, 7, 13, 10, 0, 0)
        engine._forecast_data = []
        for i in range(24):
            temp = 30.0 if 8 <= i <= 10 else 25.0  # Only 3 hours hot
            engine._forecast_data.append(Forecast(
                datetime=base_time + timedelta(hours=i),
                temperature=temp,
                condition="sunny"
            ))
        
        # Strategy config requiring 5+ hours
        strategy_config = {
            "name": "Heat Wave Pre-Cool",
            "temp_threshold_c": 29.0,
            "min_duration_hours": 5,
            "lookahead_hours": 48,
            "pre_action_hours": 4,
            "adjustment_c": -1.5
        }
        
        current_time = base_time + timedelta(hours=5)
        
        engine._evaluate_heat_wave_strategy(strategy_config, current_time)
        
        assert engine._active_strategy is None

    def test_no_heat_wave_detected(self):
        """Test heat wave strategy not activated when no heat wave in forecast."""
        mock_hass = Mock()
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Set up forecast data - no high temperatures
        base_time = datetime(2025, 7, 13, 10, 0, 0)
        engine._forecast_data = []
        for i in range(24):
            engine._forecast_data.append(Forecast(
                datetime=base_time + timedelta(hours=i),
                temperature=25.0,  # All moderate temperatures
                condition="sunny"
            ))
        
        strategy_config = {
            "name": "Heat Wave Pre-Cool",
            "temp_threshold_c": 29.0,
            "min_duration_hours": 5,
            "lookahead_hours": 48,
            "pre_action_hours": 4,
            "adjustment_c": -1.5
        }
        
        current_time = base_time + timedelta(hours=5)
        
        engine._evaluate_heat_wave_strategy(strategy_config, current_time)
        
        assert engine._active_strategy is None

    def test_heat_wave_beyond_lookahead_window(self):
        """Test heat wave strategy not activated when event is beyond lookahead window."""
        mock_hass = Mock()
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Set up forecast data - heat wave starting at hour 50 (beyond 48h lookahead)
        base_time = datetime(2025, 7, 13, 10, 0, 0)
        engine._forecast_data = []
        for i in range(72):  # 3 days of forecast
            temp = 30.0 if 50 <= i <= 55 else 25.0
            engine._forecast_data.append(Forecast(
                datetime=base_time + timedelta(hours=i),
                temperature=temp,
                condition="sunny"
            ))
        
        strategy_config = {
            "name": "Heat Wave Pre-Cool",
            "temp_threshold_c": 29.0,
            "min_duration_hours": 5,
            "lookahead_hours": 48,  # Only look 48 hours ahead
            "pre_action_hours": 4,
            "adjustment_c": -1.5
        }
        
        current_time = base_time
        
        engine._evaluate_heat_wave_strategy(strategy_config, current_time)
        
        assert engine._active_strategy is None


class TestClearSkyStrategy:
    """Test _evaluate_clear_sky_strategy method."""

    def test_clear_sky_detected_and_pre_action_time_reached(self):
        """Test clear sky strategy activation when conditions are met."""
        mock_hass = Mock()
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Set up forecast data - sunny period starting at hour 6 lasting 8 hours
        base_time = datetime(2025, 7, 13, 10, 0, 0)
        engine._forecast_data = []
        for i in range(24):
            condition = "sunny" if 6 <= i <= 13 else "cloudy"
            engine._forecast_data.append(Forecast(
                datetime=base_time + timedelta(hours=i),
                temperature=25.0,
                condition=condition
            ))
        
        # Strategy config
        strategy_config = {
            "name": "Sunny Day Thermal Gain",
            "condition": "sunny",
            "min_duration_hours": 6,
            "lookahead_hours": 24,
            "pre_action_hours": 1,
            "adjustment_c": 0.5
        }
        
        # Current time is at hour 5 (1 hour before sunny period, pre-action time reached)
        current_time = base_time + timedelta(hours=5)
        
        engine._evaluate_clear_sky_strategy(strategy_config, current_time)
        
        assert engine._active_strategy is not None
        assert engine._active_strategy.name == "Sunny Day Thermal Gain"
        assert engine._active_strategy.adjustment == 0.5
        assert engine._active_strategy.end_time == base_time + timedelta(hours=6)

    def test_clear_sky_detected_but_pre_action_not_reached(self):
        """Test clear sky strategy not activated when pre-action time not reached."""
        mock_hass = Mock()
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Set up forecast data - sunny period starting at hour 6
        base_time = datetime(2025, 7, 13, 10, 0, 0)
        engine._forecast_data = []
        for i in range(24):
            condition = "sunny" if 6 <= i <= 13 else "cloudy"
            engine._forecast_data.append(Forecast(
                datetime=base_time + timedelta(hours=i),
                temperature=25.0,
                condition=condition
            ))
        
        strategy_config = {
            "name": "Sunny Day Thermal Gain",
            "condition": "sunny",
            "min_duration_hours": 6,
            "lookahead_hours": 24,
            "pre_action_hours": 1,
            "adjustment_c": 0.5
        }
        
        # Current time is at hour 3 (3 hours before sunny period, before pre-action time)
        current_time = base_time + timedelta(hours=3)
        
        engine._evaluate_clear_sky_strategy(strategy_config, current_time)
        
        assert engine._active_strategy is None

    def test_clear_sky_period_too_short(self):
        """Test clear sky strategy not activated when duration too short."""
        mock_hass = Mock()
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Set up forecast data - short sunny period lasting only 4 hours
        base_time = datetime(2025, 7, 13, 10, 0, 0)
        engine._forecast_data = []
        for i in range(24):
            condition = "sunny" if 6 <= i <= 9 else "cloudy"  # Only 4 hours
            engine._forecast_data.append(Forecast(
                datetime=base_time + timedelta(hours=i),
                temperature=25.0,
                condition=condition
            ))
        
        strategy_config = {
            "name": "Sunny Day Thermal Gain",
            "condition": "sunny",
            "min_duration_hours": 6,  # Requires 6+ hours
            "lookahead_hours": 24,
            "pre_action_hours": 1,
            "adjustment_c": 0.5
        }
        
        current_time = base_time + timedelta(hours=5)
        
        engine._evaluate_clear_sky_strategy(strategy_config, current_time)
        
        assert engine._active_strategy is None

    def test_no_clear_sky_condition_found(self):
        """Test clear sky strategy not activated when condition not found."""
        mock_hass = Mock()
        config = {"weather_entity": "weather.test", "strategies": []}
        engine = ForecastEngine(mock_hass, config)
        
        # Set up forecast data - no sunny conditions
        base_time = datetime(2025, 7, 13, 10, 0, 0)
        engine._forecast_data = []
        for i in range(24):
            engine._forecast_data.append(Forecast(
                datetime=base_time + timedelta(hours=i),
                temperature=25.0,
                condition="cloudy"  # All cloudy
            ))
        
        strategy_config = {
            "name": "Sunny Day Thermal Gain",
            "condition": "sunny",
            "min_duration_hours": 6,
            "lookahead_hours": 24,
            "pre_action_hours": 1,
            "adjustment_c": 0.5
        }
        
        current_time = base_time + timedelta(hours=5)
        
        engine._evaluate_clear_sky_strategy(strategy_config, current_time)
        
        assert engine._active_strategy is None


class TestIntegration:
    """Integration tests for complete ForecastEngine workflow."""

    @pytest.mark.asyncio
    @patch('custom_components.smart_climate.forecast_engine.dt_util.utcnow')
    @patch('custom_components.smart_climate.forecast_engine.dt_util.parse_datetime')
    async def test_complete_workflow_heat_wave_activation(self, mock_parse_datetime, mock_utcnow):
        """Test complete workflow from forecast fetch to strategy activation."""
        mock_hass = Mock()
        mock_hass.services.async_call = AsyncMock()
        
        config = {
            "weather_entity": "weather.test",
            "strategies": [
                {
                    "name": "Heat Wave Pre-Cool",
                    "enabled": True,
                    "strategy_type": "heat_wave",
                    "temp_threshold_c": 29.0,
                    "min_duration_hours": 5,
                    "lookahead_hours": 48,
                    "pre_action_hours": 4,
                    "adjustment_c": -1.5
                }
            ]
        }
        engine = ForecastEngine(mock_hass, config)
        
        # Set up current time and forecast response
        base_time = datetime(2025, 7, 13, 10, 0, 0)
        current_time = base_time + timedelta(hours=5)  # Pre-action time for hour 9 heat wave
        mock_utcnow.return_value = current_time
        
        # Create forecast response - heat wave starting at hour 9 lasting 6 hours
        forecast_response = {"weather.test": {"forecast": []}}
        for i in range(24):
            temp = 30.0 if 9 <= i <= 14 else 25.0
            forecast_response["weather.test"]["forecast"].append({
                "datetime": f"2025-07-13T{base_time.hour + i:02d}:00:00+00:00",
                "temperature": temp,
                "condition": "sunny"
            })
        
        mock_hass.services.async_call.return_value = forecast_response
        
        # Mock datetime parsing
        parse_times = [base_time + timedelta(hours=i) for i in range(24)]
        mock_parse_datetime.side_effect = parse_times
        
        # Run the complete update cycle
        await engine.async_update()
        
        # Verify strategy was activated
        assert engine._active_strategy is not None
        assert engine._active_strategy.name == "Heat Wave Pre-Cool"
        assert engine._active_strategy.adjustment == -1.5
        assert engine._active_strategy.end_time == base_time + timedelta(hours=9)
        
        # Verify predictive offset is returned
        assert engine.predictive_offset == -1.5

    @pytest.mark.asyncio
    @patch('custom_components.smart_climate.forecast_engine.dt_util.utcnow')
    @patch('custom_components.smart_climate.forecast_engine.dt_util.parse_datetime')
    async def test_complete_workflow_no_strategy_activation(self, mock_parse_datetime, mock_utcnow):
        """Test complete workflow when no strategy should be activated."""
        mock_hass = Mock()
        mock_hass.services.async_call = AsyncMock()
        
        config = {
            "weather_entity": "weather.test",
            "strategies": [
                {
                    "name": "Heat Wave Pre-Cool",
                    "enabled": True,
                    "strategy_type": "heat_wave",
                    "temp_threshold_c": 29.0,
                    "min_duration_hours": 5,
                    "lookahead_hours": 48,
                    "pre_action_hours": 4,
                    "adjustment_c": -1.5
                }
            ]
        }
        engine = ForecastEngine(mock_hass, config)
        
        # Set up current time and forecast response
        base_time = datetime(2025, 7, 13, 10, 0, 0)
        current_time = base_time
        mock_utcnow.return_value = current_time
        
        # Create forecast response - all moderate temperatures
        forecast_response = {"weather.test": {"forecast": []}}
        for i in range(24):
            forecast_response["weather.test"]["forecast"].append({
                "datetime": f"2025-07-13T{base_time.hour + i:02d}:00:00+00:00",
                "temperature": 25.0,  # All moderate
                "condition": "cloudy"
            })
        
        mock_hass.services.async_call.return_value = forecast_response
        
        # Mock datetime parsing
        parse_times = [base_time + timedelta(hours=i) for i in range(24)]
        mock_parse_datetime.side_effect = parse_times
        
        # Run the complete update cycle
        await engine.async_update()
        
        # Verify no strategy was activated
        assert engine._active_strategy is None
        assert engine.predictive_offset == 0.0

    @pytest.mark.asyncio
    @patch('custom_components.smart_climate.forecast_engine.dt_util.utcnow')
    async def test_multiple_strategies_first_wins(self, mock_utcnow):
        """Test that when multiple strategies match, the first one wins."""
        mock_hass = Mock()
        mock_hass.services.async_call = AsyncMock()
        
        config = {
            "weather_entity": "weather.test",
            "strategies": [
                {
                    "name": "Heat Wave Strategy",
                    "enabled": True,
                    "strategy_type": "heat_wave",
                    "temp_threshold_c": 28.0,
                    "min_duration_hours": 4,
                    "lookahead_hours": 48,
                    "pre_action_hours": 2,
                    "adjustment_c": -2.0
                },
                {
                    "name": "Clear Sky Strategy",
                    "enabled": True,
                    "strategy_type": "clear_sky",
                    "condition": "sunny",
                    "min_duration_hours": 6,
                    "lookahead_hours": 24,
                    "pre_action_hours": 1,
                    "adjustment_c": 1.0
                }
            ]
        }
        engine = ForecastEngine(mock_hass, config)
        
        # Set up forecast data that would match both strategies
        base_time = datetime(2025, 7, 13, 10, 0, 0)
        current_time = base_time + timedelta(hours=6)  # Pre-action time for hour 8 event
        mock_utcnow.return_value = current_time
        
        engine._forecast_data = []
        for i in range(24):
            # Hours 8-15 are hot and sunny (matches both strategies)
            temp = 29.0 if 8 <= i <= 15 else 25.0
            condition = "sunny" if 8 <= i <= 15 else "cloudy"
            engine._forecast_data.append(Forecast(
                datetime=base_time + timedelta(hours=i),
                temperature=temp,
                condition=condition
            ))
        
        # Manually call _evaluate_strategies (skipping fetch for this test)
        engine._evaluate_strategies(current_time)
        
        # First strategy (heat wave) should win
        assert engine._active_strategy is not None
        assert engine._active_strategy.name == "Heat Wave Strategy"
        assert engine._active_strategy.adjustment == -2.0