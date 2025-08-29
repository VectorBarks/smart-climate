"""CompressorStateAnalyzer for Smart Climate Control Quiet Mode.

ABOUTME: Analyzes compressor state and determines when temperature adjustments 
would activate the compressor to reduce unnecessary AC beeps.
"""

from typing import Optional
import logging

from .offset_engine import HysteresisLearner

_LOGGER = logging.getLogger(__name__)


class CompressorStateAnalyzer:
    """Analyzes compressor state and activation conditions for Quiet Mode."""
    
    def __init__(self, power_threshold: float = 50.0):
        """Initialize the CompressorStateAnalyzer.
        
        Args:
            power_threshold: Power consumption threshold in watts to consider
                           compressor active (default: 50W)
        """
        self._power_threshold = power_threshold
        _LOGGER.debug("CompressorStateAnalyzer initialized with power_threshold=%.1fW", power_threshold)
    
    def is_compressor_idle(self, power: Optional[float]) -> bool:
        """Check if compressor is currently idle (below power threshold).
        
        Args:
            power: Current power consumption in watts, or None if unavailable
            
        Returns:
            True if compressor is idle (power < threshold), False if active
            None power is treated as idle (conservative approach)
        """
        if power is None:
            _LOGGER.debug("Power consumption unavailable, treating as idle")
            return True
        
        is_idle = power < self._power_threshold
        _LOGGER.debug("Power consumption: %.1fW, threshold: %.1fW, idle: %s", 
                     power, self._power_threshold, is_idle)
        return is_idle
    
    def would_adjustment_activate_compressor(
        self,
        current_room_temp: float,
        new_setpoint: float,
        hysteresis_learner: HysteresisLearner,
        hvac_mode: str
    ) -> Optional[bool]:
        """Determine if temperature adjustment would activate the compressor.
        
        Args:
            current_room_temp: Current room temperature in celsius
            new_setpoint: Proposed new setpoint temperature in celsius
            hysteresis_learner: Learned hysteresis thresholds
            hvac_mode: Current HVAC mode (cool, dry, auto, heat, heat_cool, off)
            
        Returns:
            True if adjustment would activate compressor
            False if adjustment would not activate compressor  
            None if thresholds unknown or mode unsupported
        """
        # Only support cooling modes (cool, dry, auto)
        supported_modes = ["cool", "dry", "auto"]
        if hvac_mode.lower() not in supported_modes:
            _LOGGER.debug("HVAC mode '%s' not supported for compressor activation analysis", hvac_mode)
            return False
        
        # Check if we have learned thresholds
        if hysteresis_learner.learned_start_threshold is None:
            _LOGGER.debug("No learned start threshold available, cannot determine activation")
            return None
        
        start_threshold = hysteresis_learner.learned_start_threshold
        
        # For cooling modes, compressor activates when setpoint goes below start threshold
        # and room temperature is above the setpoint
        would_activate = new_setpoint < start_threshold and current_room_temp > new_setpoint
        
        _LOGGER.debug(
            "Activation analysis: room_temp=%.1f°C, new_setpoint=%.1f°C, "
            "start_threshold=%.1f°C, hvac_mode=%s, would_activate=%s",
            current_room_temp, new_setpoint, start_threshold, hvac_mode, would_activate
        )
        
        return would_activate
    
    def get_adjustment_needed_to_activate(
        self,
        current_room_temp: float,
        hysteresis_learner: HysteresisLearner,
        hvac_mode: str
    ) -> Optional[float]:
        """Calculate the setpoint needed to activate the compressor.
        
        Args:
            current_room_temp: Current room temperature in celsius
            hysteresis_learner: Learned hysteresis thresholds
            hvac_mode: Current HVAC mode
            
        Returns:
            Setpoint temperature that would activate compressor
            None if thresholds unknown or mode unsupported
        """
        # Only support cooling modes
        supported_modes = ["cool", "dry", "auto"]
        if hvac_mode.lower() not in supported_modes:
            _LOGGER.debug("HVAC mode '%s' not supported for activation calculation", hvac_mode)
            return None
        
        # Check if we have learned thresholds
        if hysteresis_learner.learned_start_threshold is None:
            _LOGGER.debug("No learned start threshold available, cannot calculate activation setpoint")
            return None
        
        # Return the start threshold - this is the setpoint that would activate the compressor
        activation_setpoint = hysteresis_learner.learned_start_threshold
        
        _LOGGER.debug(
            "Activation setpoint calculation: room_temp=%.1f°C, hvac_mode=%s, "
            "activation_setpoint=%.1f°C",
            current_room_temp, hvac_mode, activation_setpoint
        )
        
        return activation_setpoint