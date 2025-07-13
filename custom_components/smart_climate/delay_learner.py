"""
ABOUTME: DelayLearner class for adaptive feedback delays in Smart Climate Control.
Learns optimal feedback delay timing based on AC temperature stabilization patterns.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

# Constants based on architectural specification and MCP guidance
STABILITY_THRESHOLD = 0.1  # Temperature change threshold for stability detection (°C)
CHECK_INTERVAL = timedelta(seconds=15)  # Temperature monitoring interval
LEARNING_TIMEOUT = timedelta(minutes=10)  # Maximum learning cycle duration
EMA_ALPHA = 0.3  # Exponential moving average smoothing factor


class DelayLearner:
    """Learns optimal feedback delay timing based on AC response patterns."""
    
    def __init__(
        self,
        hass: HomeAssistant,
        entity_id: str,
        room_sensor_entity_id: str,
        store: Store
    ):
        """Initialize the delay learner.
        
        Args:
            hass: Home Assistant instance
            entity_id: Climate entity ID for logging purposes
            room_sensor_entity_id: Room temperature sensor entity ID
            store: Home Assistant Store instance for persistence
        """
        self._hass = hass
        self._entity_id = entity_id
        self._room_sensor_entity_id = room_sensor_entity_id
        self._store = store
        
        # Learning state
        self._learned_delay_secs: Optional[int] = None
        self._cancel_listener: Optional[callable] = None
        self._learning_start_time: Optional[datetime] = None
        self._last_temp: Optional[float] = None
        self._temp_history: List[Tuple[datetime, float]] = []
    
    async def async_load(self) -> None:
        """Load learned delay from storage."""
        try:
            data = await self._store.async_load()
            if data and "learned_delay" in data:
                self._learned_delay_secs = data["learned_delay"]
                _LOGGER.info(
                    "[%s] Loaded learned delay from store: %s seconds",
                    self._entity_id, self._learned_delay_secs
                )
        except Exception as err:
            _LOGGER.warning(
                "[%s] Failed to load learned delay from store: %s",
                self._entity_id, err
            )
    
    async def async_save(self, new_delay: int) -> None:
        """Save learned delay using exponential moving average.
        
        Args:
            new_delay: New delay measurement in seconds
        """
        try:
            if self._learned_delay_secs is None:
                # First measurement - no smoothing
                self._learned_delay_secs = new_delay
            else:
                # Apply exponential moving average for smoothing
                self._learned_delay_secs = int(
                    (EMA_ALPHA * new_delay) + (1 - EMA_ALPHA) * self._learned_delay_secs
                )
            
            _LOGGER.info(
                "[%s] Updating learned delay to %s seconds (new measurement: %s)",
                self._entity_id, self._learned_delay_secs, new_delay
            )
            
            # Persist to storage
            await self._store.async_save({"learned_delay": self._learned_delay_secs})
            
        except Exception as err:
            _LOGGER.error(
                "[%s] Failed to save learned delay: %s",
                self._entity_id, err
            )
    
    def start_learning_cycle(self) -> None:
        """Start monitoring temperature to learn stabilization delay."""
        if self._cancel_listener:
            _LOGGER.debug(
                "[%s] Learning cycle already in progress. Ignoring.",
                self._entity_id
            )
            return
        
        # Get initial temperature reading
        self._last_temp = self._get_current_temp()
        
        if self._last_temp is None:
            _LOGGER.warning(
                "[%s] Cannot start learning cycle: temperature sensor '%s' is unavailable.",
                self._entity_id, self._room_sensor_entity_id
            )
            return
        
        _LOGGER.info("[%s] Starting new feedback delay learning cycle.", self._entity_id)
        self._learning_start_time = dt_util.utcnow()
        self._temp_history = [(self._learning_start_time, self._last_temp)]
        
        # Start periodic temperature monitoring
        self._cancel_listener = async_track_time_interval(
            self._hass, self._async_check_stability, CHECK_INTERVAL
        )
    
    def stop_learning_cycle(self) -> None:
        """Stop current learning cycle."""
        if self._cancel_listener:
            self._cancel_listener()
            self._cancel_listener = None
            self._learning_start_time = None
            self._temp_history = []
            _LOGGER.debug("[%s] Stopped feedback delay learning cycle.", self._entity_id)
    
    def get_adaptive_delay(self, fallback_delay: int = 45) -> int:
        """Get current adaptive delay or fallback.
        
        Args:
            fallback_delay: Default delay if no learned value exists
            
        Returns:
            Adaptive delay in seconds
        """
        return self._learned_delay_secs if self._learned_delay_secs else fallback_delay
    
    def _get_current_temp(self) -> Optional[float]:
        """Get current temperature from room sensor.
        
        Returns:
            Current temperature in Celsius, or None if unavailable
        """
        state = self._hass.states.get(self._room_sensor_entity_id)
        if state and state.state not in ("unknown", "unavailable"):
            try:
                return float(state.state)
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "[%s] Could not parse temperature sensor state: %s",
                    self._entity_id, state.state
                )
                return None
        return None
    
    @callback
    def _async_check_stability(self, now: datetime) -> None:
        """Check if temperature has stabilized.
        
        Called periodically during learning cycle to monitor temperature changes.
        Stops learning and saves delay when temperature stabilizes or timeout occurs.
        
        Args:
            now: Current datetime from the timer
        """
        # Timeout protection - stop if learning cycle exceeds maximum duration
        if now - self._learning_start_time > LEARNING_TIMEOUT:
            _LOGGER.warning(
                "[%s] Learning cycle timed out after %s. No new delay learned.",
                self._entity_id, LEARNING_TIMEOUT
            )
            self.stop_learning_cycle()
            return
        
        # Get current temperature reading
        current_temp = self._get_current_temp()
        if current_temp is None:
            _LOGGER.debug(
                "[%s] Skipping stability check, temp sensor unavailable.",
                self._entity_id
            )
            return
        
        # Calculate temperature change since last reading
        temp_delta = abs(current_temp - self._last_temp)
        self._last_temp = current_temp
        self._temp_history.append((now, current_temp))
        
        _LOGGER.debug(
            "[%s] Stability check: Temp delta is %.2f°C (Threshold: %.2f°C)",
            self._entity_id, temp_delta, STABILITY_THRESHOLD
        )
        
        # Check if temperature has stabilized (change below threshold)
        if temp_delta < STABILITY_THRESHOLD:
            # Calculate time elapsed since learning started
            stabilization_time = (now - self._learning_start_time).total_seconds()
            
            # Add buffer time for safety (5 seconds as per architecture notes)
            buffer_time = 5
            final_delay = int(stabilization_time + buffer_time)
            
            _LOGGER.info(
                "[%s] Temperature stabilized in %s seconds (+ %s buffer). Saving delay: %s seconds.",
                self._entity_id, int(stabilization_time), buffer_time, final_delay
            )
            
            # Save the learned delay with EMA smoothing
            self._hass.async_create_task(self.async_save(final_delay))
            
            # Stop the learning cycle
            self.stop_learning_cycle()