"""Mode management for Smart Climate Control integration."""

from typing import Callable, List, Optional
from datetime import datetime, timedelta

from homeassistant.util import dt as dt_util

from .models import ModeAdjustments


class ModeManager:
    """Manages operating modes and their effects."""
    
    def __init__(self, config: dict):
        """Initialize mode manager with configuration."""
        self._config = config
        self._current_mode = "none"
        self._mode_change_callbacks: List[Callable] = []
        
        # Mode change tracking for smart sleep wake-up
        self._last_mode_change_time: Optional[datetime] = None
        self._previous_mode = "none"
    
    @property
    def current_mode(self) -> str:
        """Get current operating mode."""
        return self._current_mode
    
    def set_mode(self, mode: str) -> None:
        """Set operating mode."""
        if mode not in ["none", "away", "sleep", "boost"]:
            raise ValueError(f"Invalid mode: {mode}")
        
        # Track mode change
        if mode != self._current_mode:
            self._previous_mode = self._current_mode
            self._current_mode = mode
            self._last_mode_change_time = dt_util.utcnow()
            
        self._notify_callbacks()
    
    def get_adjustments(self) -> ModeAdjustments:
        """Get adjustments for current mode."""
        if self._current_mode == "none":
            return ModeAdjustments(
                temperature_override=None,
                offset_adjustment=0.0,
                update_interval_override=None,
                boost_offset=0.0,
                force_operation=False
            )
        elif self._current_mode == "away":
            return ModeAdjustments(
                temperature_override=self._config.get("away_temperature", 19.0),
                offset_adjustment=0.0,
                update_interval_override=None,
                boost_offset=0.0,
                force_operation=False
            )
        elif self._current_mode == "sleep":
            return ModeAdjustments(
                temperature_override=None,
                offset_adjustment=self._config.get("sleep_offset", 1.0),
                update_interval_override=None,
                boost_offset=0.0,
                force_operation=False
            )
        elif self._current_mode == "boost":
            return ModeAdjustments(
                temperature_override=None,
                offset_adjustment=0.0,
                update_interval_override=None,
                boost_offset=self._config.get("boost_offset", -2.0),
                force_operation=True
            )
        else:
            # Fallback to none mode
            return ModeAdjustments(
                temperature_override=None,
                offset_adjustment=0.0,
                update_interval_override=None,
                boost_offset=0.0,
                force_operation=False
            )
    
    def register_mode_change_callback(self, callback: Callable) -> None:
        """Register callback for mode changes."""
        self._mode_change_callbacks.append(callback)
    
    def _notify_callbacks(self) -> None:
        """Notify all registered callbacks of mode change."""
        for callback in self._mode_change_callbacks:
            callback()
    
    def get_time_since_mode_change(self) -> Optional[timedelta]:
        """Get time since last mode change.
        
        Returns:
            timedelta since last mode change, or None if no changes recorded
        """
        if self._last_mode_change_time is None:
            return None
        
        return dt_util.utcnow() - self._last_mode_change_time
    
    def was_recently_in_sleep_or_away(self, threshold_minutes: int = 30) -> bool:
        """Check if recently changed from sleep or away mode.
        
        Args:
            threshold_minutes: Maximum minutes to consider "recent"
            
        Returns:
            True if recently changed from sleep or away mode
        """
        # Check if we changed from sleep or away mode recently
        if self._previous_mode not in ["sleep", "away"]:
            return False
        
        time_since_change = self.get_time_since_mode_change()
        if time_since_change is None:
            return False
        
        return time_since_change <= timedelta(minutes=threshold_minutes)