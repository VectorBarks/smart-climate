"""Mode management for Smart Climate Control integration."""

from typing import Callable, List

from .models import ModeAdjustments


class ModeManager:
    """Manages operating modes and their effects."""
    
    def __init__(self, config: dict):
        """Initialize mode manager with configuration."""
        self._config = config
        self._current_mode = "none"
        self._mode_change_callbacks: List[Callable] = []
    
    @property
    def current_mode(self) -> str:
        """Get current operating mode."""
        return self._current_mode
    
    def set_mode(self, mode: str) -> None:
        """Set operating mode."""
        if mode not in ["none", "away", "sleep", "boost"]:
            raise ValueError(f"Invalid mode: {mode}")
        self._current_mode = mode
        self._notify_callbacks()
    
    def get_adjustments(self) -> ModeAdjustments:
        """Get adjustments for current mode."""
        if self._current_mode == "none":
            return ModeAdjustments(
                temperature_override=None,
                offset_adjustment=0.0,
                update_interval_override=None,
                boost_offset=0.0
            )
        elif self._current_mode == "away":
            return ModeAdjustments(
                temperature_override=self._config.get("away_temperature", 19.0),
                offset_adjustment=0.0,
                update_interval_override=None,
                boost_offset=0.0
            )
        elif self._current_mode == "sleep":
            return ModeAdjustments(
                temperature_override=None,
                offset_adjustment=self._config.get("sleep_offset", 1.0),
                update_interval_override=None,
                boost_offset=0.0
            )
        elif self._current_mode == "boost":
            return ModeAdjustments(
                temperature_override=None,
                offset_adjustment=0.0,
                update_interval_override=None,
                boost_offset=self._config.get("boost_offset", -2.0)
            )
        else:
            # Fallback to none mode
            return ModeAdjustments(
                temperature_override=None,
                offset_adjustment=0.0,
                update_interval_override=None,
                boost_offset=0.0
            )
    
    def register_mode_change_callback(self, callback: Callable) -> None:
        """Register callback for mode changes."""
        self._mode_change_callbacks.append(callback)
    
    def _notify_callbacks(self) -> None:
        """Notify all registered callbacks of mode change."""
        for callback in self._mode_change_callbacks:
            callback()