"""Weather forecast analysis engine for predictive temperature control."""

import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .models import Forecast, ActiveStrategy

_LOGGER = logging.getLogger(__name__)


class ForecastEngine:
    """Analyzes weather forecasts to calculate predictive temperature adjustments."""

    def __init__(self, hass: HomeAssistant, config: Dict[str, Any]):
        """Initialize the ForecastEngine."""
        self._hass = hass
        self._weather_entity = config.get("weather_entity")
        self._strategies = [s for s in config.get("strategies", []) if s.get("enabled", True)]
        
        self._forecast_data: List[Forecast] = []
        self._active_strategy: Optional[ActiveStrategy] = None
        self._last_update: Optional[datetime] = None
        self._update_interval = timedelta(minutes=30)

    @property
    def predictive_offset(self) -> float:
        """
        Return the current predictive temperature offset.
        Returns 0.0 if no strategy is active or if the active strategy has expired.
        """
        if self._active_strategy:
            if dt_util.utcnow() < self._active_strategy.end_time:
                return self._active_strategy.adjustment
            else:
                _LOGGER.info("Predictive strategy '%s' has ended.", self._active_strategy.name)
                self._active_strategy = None
        
        return 0.0

    async def async_update(self) -> None:
        """
        Fetch latest forecast and re-evaluate strategies.
        This method is throttled to prevent excessive API calls.
        """
        if not self._weather_entity:
            return

        now = dt_util.utcnow()
        if self._last_update and (now - self._last_update < self._update_interval):
            return
            
        _LOGGER.debug("Fetching forecast and re-evaluating predictive strategies.")
        if await self._async_fetch_forecast():
            self._evaluate_strategies(now)
        self._last_update = now

    async def _async_fetch_forecast(self) -> bool:
        """Fetch hourly forecast data from Home Assistant. Returns True on success."""
        try:
            response = await self._hass.services.async_call(
                "weather", "get_forecasts",
                {"entity_id": self._weather_entity, "type": "hourly"},
                blocking=True, return_response=True,
            )
            
            raw_forecasts = response.get(self._weather_entity, {}).get("forecast", [])
            self._forecast_data = [
                Forecast(
                    datetime=dt_util.parse_datetime(f["datetime"]),
                    temperature=f["temperature"],
                    condition=f.get("condition"),
                ) for f in raw_forecasts
            ]
            _LOGGER.debug("Fetched %d hourly forecast points.", len(self._forecast_data))
            return True
        except Exception as e:
            _LOGGER.error("Error fetching weather forecast for %s: %s", self._weather_entity, e)
            self._forecast_data = []
            return False

    def _evaluate_strategies(self, now: datetime) -> None:
        """Iterate through configured strategies and activate the first one that matches."""
        self._active_strategy = None  # Reset before evaluation

        for strategy_config in self._strategies:
            strategy_type = strategy_config.get("strategy_type")
            # Dynamically call the correct evaluator based on strategy_type
            evaluator = getattr(self, f"_evaluate_{strategy_type}_strategy", None)
            
            if evaluator:
                evaluator(strategy_config, now)
            
            if self._active_strategy:
                _LOGGER.info(
                    "Activating predictive strategy '%s' with offset %.2f until %s",
                    self._active_strategy.name, self._active_strategy.adjustment, self._active_strategy.end_time
                )
                break  # Stop after finding the first active strategy

    def _find_consecutive_event(
        self, 
        forecasts: List[Forecast], 
        min_duration: timedelta, 
        condition_checker: Callable[[Forecast], bool]
    ) -> Optional[datetime]:
        """Generic helper to find the start time of a consecutive weather event."""
        event_start_time = None
        consecutive_hours = 0
        
        for forecast in forecasts:
            if condition_checker(forecast):
                if not event_start_time:
                    event_start_time = forecast.datetime
                consecutive_hours += 1
            else:
                # Event ended, check if it was long enough
                if event_start_time and consecutive_hours >= min_duration.total_seconds() / 3600:
                    return event_start_time
                # Reset
                event_start_time = None
                consecutive_hours = 0
        
        # Check if the forecast ended during a valid event
        if event_start_time and consecutive_hours >= min_duration.total_seconds() / 3600:
            return event_start_time
        return None

    def _evaluate_heat_wave_strategy(self, config: Dict[str, Any], now: datetime) -> None:
        """Evaluator for the 'heat_wave' strategy type."""
        lookahead = timedelta(hours=config.get("lookahead_hours", 48))
        future_forecasts = [f for f in self._forecast_data if now < f.datetime <= now + lookahead]
        
        event_start_time = self._find_consecutive_event(
            future_forecasts,
            timedelta(hours=config.get("min_duration_hours", 5)),
            lambda f: f.temperature >= config["temp_threshold_c"]
        )
        
        if event_start_time:
            pre_action_start_time = event_start_time - timedelta(hours=config.get("pre_action_hours", 4))
            if now >= pre_action_start_time:
                self._active_strategy = ActiveStrategy(
                    name=config["name"],
                    adjustment=config["adjustment_c"],
                    end_time=event_start_time,
                )

    def _evaluate_clear_sky_strategy(self, config: Dict[str, Any], now: datetime) -> None:
        """Evaluator for the 'clear_sky' strategy type."""
        lookahead = timedelta(hours=config.get("lookahead_hours", 24))
        future_forecasts = [f for f in self._forecast_data if now < f.datetime <= now + lookahead]

        event_start_time = self._find_consecutive_event(
            future_forecasts,
            timedelta(hours=config.get("min_duration_hours", 6)),
            lambda f: f.condition == config["condition"]
        )

        if event_start_time:
            pre_action_start_time = event_start_time - timedelta(hours=config.get("pre_action_hours", 1))
            if now >= pre_action_start_time:
                self._active_strategy = ActiveStrategy(
                    name=config["name"],
                    adjustment=config["adjustment_c"],
                    end_time=event_start_time,
                )