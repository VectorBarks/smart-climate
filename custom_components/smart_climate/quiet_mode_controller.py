"""
ABOUTME: Controls quiet mode behavior to suppress unnecessary temperature adjustments 
when AC compressor is idle, reducing beep noise pollution.
"""

from typing import Optional, Tuple
import logging

from .compressor_state_analyzer import CompressorStateAnalyzer
from .offset_engine import HysteresisLearner

_LOGGER = logging.getLogger(__name__)


class QuietModeController:
    """Controls quiet mode to suppress unnecessary AC adjustments when compressor idle."""
    
    def __init__(
        self,
        enabled: bool,
        analyzer: CompressorStateAnalyzer,
        logger: logging.Logger
    ):
        """Initialize the QuietModeController.
        
        Args:
            enabled: Whether quiet mode is enabled via configuration
            analyzer: CompressorStateAnalyzer instance for state detection
            logger: Logger instance for debugging/info messages
        """
        self._enabled = enabled
        self._analyzer = analyzer
        self._logger = logger
        self._suppression_count = 0
        self._last_learning_attempt = None
        
        _LOGGER.debug("QuietModeController initialized: enabled=%s", enabled)
    
    def should_suppress_adjustment(
        self,
        current_room_temp: float,
        current_setpoint: float,
        new_setpoint: float,
        power: Optional[float],
        hvac_mode: str,
        hysteresis_learner: HysteresisLearner
    ) -> Tuple[bool, Optional[str]]:
        """Determine if temperature adjustment should be suppressed.
        
        Args:
            current_room_temp: Current room temperature in celsius
            current_setpoint: Current AC setpoint temperature in celsius
            new_setpoint: Proposed new setpoint temperature in celsius
            power: Current power consumption in watts (or None if unavailable)
            hvac_mode: Current HVAC mode (cool, dry, auto, heat, heat_cool, off)
            hysteresis_learner: Learned hysteresis thresholds
            
        Returns:
            Tuple of (should_suppress, reason_string)
            - should_suppress: True if adjustment should be suppressed
            - reason_string: Human-readable reason for suppression (None if not suppressed)
        """
        # Quick exit if quiet mode is disabled
        if not self._enabled:
            return False, None
        
        # Only support cooling modes
        supported_modes = ["cool", "dry", "auto"]
        if hvac_mode.lower() not in supported_modes:
            return False, None
        
        # Don't suppress if compressor is already active (power above threshold)
        if not self._analyzer.is_compressor_idle(power):
            return False, None
        
        # Check if adjustment would activate the compressor
        would_activate = self._analyzer.would_adjustment_activate_compressor(
            current_room_temp, new_setpoint, hysteresis_learner, hvac_mode
        )
        
        # Allow adjustment if it would activate compressor (crosses threshold)
        if would_activate is True:
            return False, None
        
        # Suppress if compressor is idle and adjustment won't activate it
        if would_activate is False:
            self._suppression_count += 1
            reason = f"Compressor idle (power: {power}W), adjustment won't activate compressor"
            self._logger.debug(
                "Quiet Mode suppression #%d: %s -> %s (room: %.1f°C, power: %sW)",
                self._suppression_count, current_setpoint, new_setpoint, 
                current_room_temp, power
            )
            return True, reason
        
        # would_activate is None - thresholds unknown
        if would_activate is None:
            self._suppression_count += 1
            reason = "Compressor idle, hysteresis thresholds unknown (learning needed)"
            self._logger.debug(
                "Quiet Mode suppression #%d (thresholds unknown): %s -> %s",
                self._suppression_count, current_setpoint, new_setpoint
            )
            return True, reason
        
        # Fallback - should not reach here
        return False, None
    
    def get_progressive_adjustment(
        self,
        current_room_temp: float,
        current_setpoint: float,
        hysteresis_learner: HysteresisLearner,
        hvac_mode: str
    ) -> Optional[float]:
        """Get progressive learning setpoint when thresholds are unknown.
        
        This method returns a slightly more aggressive setpoint that can be used
        for learning hysteresis thresholds when they are not yet known.
        
        Args:
            current_room_temp: Current room temperature in celsius
            current_setpoint: Current AC setpoint temperature in celsius
            hysteresis_learner: Hysteresis learner (may have unknown thresholds)
            hvac_mode: Current HVAC mode
            
        Returns:
            Progressive setpoint for learning, or None if mode not supported
        """
        # Only support cooling modes
        supported_modes = ["cool", "dry", "auto"]
        if hvac_mode.lower() not in supported_modes:
            return None
        
        # Return setpoint 0.5°C lower for progressive learning
        progressive_setpoint = current_setpoint - 0.5
        
        self._logger.debug(
            "Progressive learning adjustment: current=%.1f°C -> progressive=%.1f°C",
            current_setpoint, progressive_setpoint
        )
        
        return progressive_setpoint
    
    def get_suppression_count(self) -> int:
        """Get the current count of suppressed adjustments.
        
        Returns:
            Number of adjustments suppressed since last reset
        """
        return self._suppression_count
    
    def reset_suppression_count(self) -> None:
        """Reset the suppression count to zero.
        
        This can be called daily or periodically to track suppressions over time.
        """
        previous_count = self._suppression_count
        self._suppression_count = 0
        
        self._logger.debug(
            "Quiet Mode suppression count reset: %d -> 0", 
            previous_count
        )