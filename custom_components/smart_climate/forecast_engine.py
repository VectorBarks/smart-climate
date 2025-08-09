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
            if dt_util.now() < self._active_strategy.end_time:
                _LOGGER.debug(
                    "Weather: Returning active predictive offset %.1f°C from '%s' strategy (expires at %s)",
                    self._active_strategy.adjustment, self._active_strategy.name, 
                    self._active_strategy.end_time.strftime('%H:%M')
                )
                return self._active_strategy.adjustment
            else:
                _LOGGER.info("Predictive strategy '%s' has ended.", self._active_strategy.name)
                _LOGGER.debug("Weather: Strategy expired, predictive offset now 0.0°C")
                self._active_strategy = None
        
        _LOGGER.debug("Weather: No active strategy, predictive offset 0.0°C")
        return 0.0

    @property
    def active_strategy_info(self) -> Optional[Dict[str, Any]]:
        """
        Return information about the currently active strategy.
        Returns None if no strategy is active or if the active strategy has expired.
        """
        if self._active_strategy:
            if dt_util.now() < self._active_strategy.end_time:
                return {
                    "name": self._active_strategy.name,
                    "adjustment": self._active_strategy.adjustment,
                    "end_time": self._active_strategy.end_time.isoformat(),
                    "reason": getattr(self._active_strategy, 'reason', 'strategy conditions met')
                }
            else:
                _LOGGER.info("Predictive strategy '%s' has ended.", self._active_strategy.name)
                self._active_strategy = None
        
        return None

    async def async_update(self) -> None:
        """
        Fetch latest forecast and re-evaluate strategies.
        This method is throttled to prevent excessive API calls.
        """
        if not self._weather_entity:
            _LOGGER.debug("Weather: No weather entity configured, skipping forecast update")
            return

        now = dt_util.now()
        if self._last_update and (now - self._last_update < self._update_interval):
            time_remaining = (self._update_interval - (now - self._last_update)).total_seconds()
            _LOGGER.debug(
                "Weather: Forecast update throttled - %.1f minutes remaining until next update",
                time_remaining / 60
            )
            return
            
        _LOGGER.debug("Weather: Fetching forecast and re-evaluating predictive strategies")
        if await self._async_fetch_forecast():
            self._evaluate_strategies(now)
        else:
            _LOGGER.warning("Weather: Failed to fetch forecast data - strategies not updated")
        self._last_update = now

    async def _async_fetch_forecast(self) -> bool:
        """Fetch hourly forecast data from Home Assistant. Returns True on success."""
        try:
            _LOGGER.debug("Weather forecast: Fetching data from entity %s", self._weather_entity)
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
            
            _LOGGER.debug("Weather forecast: Retrieved %d hourly forecast points from %s", 
                         len(self._forecast_data), self._weather_entity)
            
            # Log detailed forecast data for the next few hours
            if self._forecast_data:
                next_hours = self._forecast_data[:6]  # Next 6 hours
                forecast_summary = ", ".join([
                    f"{f.temperature:.1f}°C {f.condition or 'unknown'}" for f in next_hours
                ])
                _LOGGER.debug("Weather: Next 6 hours: [%s]", forecast_summary)
            
            return True
        except Exception as e:
            _LOGGER.error("Error fetching weather forecast for %s: %s", self._weather_entity, e)
            self._forecast_data = []
            return False

    def _evaluate_strategies(self, now: datetime) -> None:
        """Iterate through configured strategies and activate the first one that matches."""
        self._active_strategy = None  # Reset before evaluation
        _LOGGER.debug("Weather: Evaluating %d configured predictive strategies", len(self._strategies))

        for strategy_config in self._strategies:
            # Support both "strategy_type" (new) and "type" (legacy) for backward compatibility
            strategy_type = strategy_config.get("strategy_type") or strategy_config.get("type")
            strategy_name = strategy_config.get("name", strategy_type)
            
            _LOGGER.debug("Weather: Evaluating '%s' strategy (%s)", strategy_name, strategy_type)
            
            # Dynamically call the correct evaluator based on strategy_type
            evaluator = getattr(self, f"_evaluate_{strategy_type}_strategy", None)
            
            if evaluator:
                evaluator(strategy_config, now)
            else:
                _LOGGER.warning("Weather: Unknown strategy type '%s' for strategy '%s'", 
                               strategy_type, strategy_name)
            
            if self._active_strategy:
                _LOGGER.info(
                    "Weather: Activated '%s' strategy - applying %+.1f°C offset for next %.1f hours (reason: %s)",
                    self._active_strategy.name, self._active_strategy.adjustment, 
                    (self._active_strategy.end_time - now).total_seconds() / 3600,
                    getattr(self._active_strategy, 'reason', 'strategy conditions met')
                )
                break  # Stop after finding the first active strategy
            else:
                _LOGGER.debug("Weather: Strategy '%s' not activated - conditions not met", strategy_name)
        
        if not self._active_strategy:
            _LOGGER.debug("Weather: No strategies activated - all conditions not met")

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
        # Support both "temp_threshold_c" (new) and "temp_threshold" (legacy)
        temp_threshold = config.get("temp_threshold_c") or config.get("temp_threshold")
        min_duration = config.get("min_duration_hours", 5)
        pre_action_hours = config.get("pre_action_hours", 4)
        
        future_forecasts = [f for f in self._forecast_data if now < f.datetime <= now + lookahead]
        
        _LOGGER.debug(
            "Weather: Evaluating 'heat_wave' strategy - checking for temps >%.1f°C for %dh in next %dh",
            temp_threshold, min_duration, lookahead.total_seconds() / 3600
        )
        
        # Find the maximum temperature in the forecast period for logging
        if future_forecasts:
            max_temp = max(f.temperature for f in future_forecasts)
            _LOGGER.debug("Weather: Heat wave strategy - max forecast temp %.1f°C in next %.1fh", 
                         max_temp, lookahead.total_seconds() / 3600)
        
        event_start_time = self._find_consecutive_event(
            future_forecasts,
            timedelta(hours=min_duration),
            lambda f: f.temperature >= temp_threshold
        )
        
        if event_start_time:
            pre_action_start_time = event_start_time - timedelta(hours=pre_action_hours)
            hours_until_event = (event_start_time - now).total_seconds() / 3600
            
            _LOGGER.debug(
                "Weather: Heat wave detected starting at %s (%.1fh from now), pre-action time %s",
                event_start_time.strftime('%H:%M'), hours_until_event, 
                pre_action_start_time.strftime('%H:%M')
            )
            
            if now >= pre_action_start_time:
                # Support both adjustment and adjustment_c for backward compatibility
                adjustment = config.get("adjustment", config.get("adjustment_c", 0.0))
                self._active_strategy = ActiveStrategy(
                    name=config["name"],
                    adjustment=adjustment,
                    end_time=event_start_time,
                )
                # Add reason for logging
                self._active_strategy.reason = f"heat wave >={temp_threshold}°C detected in {hours_until_event:.1f}h"
                _LOGGER.debug(
                    "Weather: Heat wave strategy activated - pre-cooling with %+.1f°C until event starts",
                    adjustment
                )
            else:
                hours_until_preaction = (pre_action_start_time - now).total_seconds() / 3600
                _LOGGER.debug(
                    "Weather: Heat wave detected but pre-action not yet due (%.1fh remaining)",
                    hours_until_preaction
                )
        else:
            if future_forecasts:
                max_temp = max(f.temperature for f in future_forecasts)
                _LOGGER.debug(
                    "Weather: Heat wave strategy not activated - max temp %.1f°C < %.1f°C threshold",
                    max_temp, temp_threshold
                )
            else:
                _LOGGER.debug("Weather: Heat wave strategy not activated - no forecast data available")

    def _evaluate_clear_sky_strategy(self, config: Dict[str, Any], now: datetime) -> None:
        """Evaluator for the 'clear_sky' strategy type."""
        lookahead = timedelta(hours=config.get("lookahead_hours", 24))
        target_condition = config["condition"]
        min_duration = config.get("min_duration_hours", 6)
        pre_action_hours = config.get("pre_action_hours", 1)
        
        future_forecasts = [f for f in self._forecast_data if now < f.datetime <= now + lookahead]
        
        _LOGGER.debug(
            "Weather: Evaluating 'clear_sky' strategy - checking for '%s' conditions for %dh in next %dh",
            target_condition, min_duration, lookahead.total_seconds() / 3600
        )
        
        # Count matching conditions for logging
        if future_forecasts:
            matching_count = sum(1 for f in future_forecasts if f.condition == target_condition)
            total_count = len(future_forecasts)
            _LOGGER.debug(
                "Weather: Clear sky check - %d/%d forecast points match '%s' condition",
                matching_count, total_count, target_condition
            )

        event_start_time = self._find_consecutive_event(
            future_forecasts,
            timedelta(hours=min_duration),
            lambda f: f.condition == target_condition
        )

        if event_start_time:
            pre_action_start_time = event_start_time - timedelta(hours=pre_action_hours)
            hours_until_event = (event_start_time - now).total_seconds() / 3600
            consecutive_hours = min_duration  # Minimum hours found by _find_consecutive_event
            
            _LOGGER.debug(
                "Weather: Clear sky period detected starting at %s (%.1fh from now), %dh consecutive '%s'",
                event_start_time.strftime('%H:%M'), hours_until_event, consecutive_hours, target_condition
            )
            
            if now >= pre_action_start_time:
                # Support both adjustment and adjustment_c for backward compatibility
                adjustment = config.get("adjustment", config.get("adjustment_c", 0.0))
                self._active_strategy = ActiveStrategy(
                    name=config["name"],
                    adjustment=adjustment,
                    end_time=event_start_time,
                )
                # Add reason for logging
                self._active_strategy.reason = f"{consecutive_hours} consecutive {target_condition} hours"
                _LOGGER.debug(
                    "Weather: Clear sky strategy activated - applying %+.1f°C offset until clear period starts",
                    adjustment
                )
            else:
                hours_until_preaction = (pre_action_start_time - now).total_seconds() / 3600
                _LOGGER.debug(
                    "Weather: Clear sky period detected but pre-action not yet due (%.1fh remaining)",
                    hours_until_preaction
                )
        else:
            _LOGGER.debug(
                "Weather: Clear sky strategy not activated - insufficient consecutive '%s' conditions (%dh required)",
                target_condition, min_duration
            )