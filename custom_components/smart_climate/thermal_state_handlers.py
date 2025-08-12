"""ABOUTME: Concrete thermal state handlers for Smart Climate Control.
Implements DriftingState and CorrectingState handlers for the thermal efficiency state machine."""

import logging
from typing import Optional, TYPE_CHECKING

from .thermal_models import ThermalState
from .thermal_states import StateHandler

if TYPE_CHECKING:
    from .thermal_manager import ThermalManager

_LOGGER = logging.getLogger(__name__)


class DriftingState(StateHandler):
    """Handler for DRIFTING thermal state.
    
    AC is off, temperature is drifting passively within the operating window.
    OffsetEngine learning is paused during this phase as no corrective action is taken.
    
    Transitions to CORRECTING when temperature exceeds operating window bounds.
    """

    def execute(self, context: "ThermalManager", current_temp: float, operating_window: tuple[float, float]) -> Optional[ThermalState]:
        """Execute drifting state logic and check for transitions.
        
        Args:
            context: ThermalManager instance providing system state
            current_temp: Current room temperature in Celsius
            operating_window: Tuple of (lower_bound, upper_bound) temperatures
            
        Returns:
            CALIBRATING if stable conditions detected, PROBING if low confidence and sufficient time passed,
            CORRECTING if temperature exceeds bounds, None to stay in DRIFTING
        """
        try:
            # Pause offset learning during drift phase (per architecture)
            context.offset_learning_paused = True
            
            # Check if stable conditions detected for opportunistic calibration
            if hasattr(context, 'stability_detector') and context.stability_detector:
                if context.stability_detector.is_stable_for_calibration():
                    _LOGGER.info("Stable conditions detected during DRIFTING, transitioning to CALIBRATING")
                    return ThermalState.CALIBRATING
            
            # Check for automatic probing trigger based on low thermal model confidence
            if hasattr(context, '_model') and context._model:
                try:
                    confidence = context._model.get_confidence()
                    if confidence < 0.3 and hasattr(context, 'can_auto_probe') and context.can_auto_probe():
                        _LOGGER.info("Low thermal model confidence (%.2f < 0.3) detected during DRIFTING, triggering automatic PROBING",
                                   confidence)
                        return ThermalState.PROBING
                    elif confidence < 0.3:
                        _LOGGER.debug("Low thermal model confidence (%.2f) but minimum probe interval not met", confidence)
                except (AttributeError, Exception) as e:
                    _LOGGER.debug("Could not check thermal model confidence: %s", e)
            
            # Use parameters instead of trying to access context attributes
            # current_temp and operating_window are now passed as parameters
            
            # Validate required parameters
            if operating_window is None or len(operating_window) != 2:
                _LOGGER.warning("Invalid operating_window in DriftingState: %s", operating_window)
                return None
            
            lower_bound, upper_bound = operating_window
            
            # Validate operating window
            if upper_bound < lower_bound:
                _LOGGER.warning("Invalid operating window in DriftingState: [%.1f, %.1f]", 
                               lower_bound, upper_bound)
                return None
            
            # Check if temperature has exceeded operating window bounds
            if current_temp >= upper_bound or current_temp <= lower_bound:
                _LOGGER.info("Temperature %.1f°C outside operating window [%.1f, %.1f], transitioning to CORRECTING",
                            current_temp, lower_bound, upper_bound)
                return ThermalState.CORRECTING
            
            # Stay in DRIFTING state
            _LOGGER.debug("Temperature %.1f°C within operating window [%.1f, %.1f], staying in DRIFTING",
                         current_temp, lower_bound, upper_bound)
            return None
            
        except (AttributeError, TypeError, ValueError) as e:
            _LOGGER.error("Error in DriftingState execute: %s", e)
            return None

    def on_enter(self, context: "ThermalManager") -> None:
        """Called when entering DRIFTING state.
        
        Args:
            context: ThermalManager instance
        """
        _LOGGER.info("Entering DRIFTING state - AC off, temperature drifting passively")

    def on_exit(self, context: "ThermalManager") -> None:
        """Called when exiting DRIFTING state.
        
        Args:
            context: ThermalManager instance
        """
        _LOGGER.info("Exiting DRIFTING state")


class CorrectingState(StateHandler):
    """Handler for CORRECTING thermal state.
    
    AC is actively running to correct temperature back towards the operating window.
    OffsetEngine learning is active with learning target set to the boundary temperature.
    
    Transitions to DRIFTING when temperature returns within operating window (with hysteresis buffer).
    """

    def execute(self, context: "ThermalManager", current_temp: float, operating_window: tuple[float, float]) -> Optional[ThermalState]:
        """Execute correcting state logic and check for transitions.
        
        Args:
            context: ThermalManager instance providing system state
            current_temp: Current room temperature in Celsius
            operating_window: Tuple of (lower_bound, upper_bound) temperatures
            
        Returns:
            DRIFTING if temperature within bounds + buffer, None to stay in CORRECTING
        """
        try:
            # Resume offset learning during correction phase (per architecture)
            context.offset_learning_paused = False
            
            # Use parameters instead of trying to access context attributes
            # current_temp and operating_window are now passed as parameters
            
            # Validate required parameters
            if operating_window is None or len(operating_window) != 2:
                _LOGGER.warning("Invalid operating_window in CorrectingState: %s", operating_window)
                return None
            
            lower_bound, upper_bound = operating_window
            
            # Validate operating window
            if upper_bound < lower_bound:
                _LOGGER.warning("Invalid operating window in CorrectingState: [%.1f, %.1f]", 
                               lower_bound, upper_bound)
                return None
            
            # Set learning target to nearest boundary (per architecture)
            self._set_learning_target(context, current_temp, operating_window)
            
            # Apply hysteresis buffer (0.2°C) to prevent rapid switching
            hysteresis_buffer = 0.2
            
            # Check if temperature is within bounds + hysteresis buffer
            # Use <= and >= to include the exact buffer boundaries
            if (current_temp >= lower_bound + hysteresis_buffer and 
                current_temp <= upper_bound - hysteresis_buffer):
                _LOGGER.info("Temperature %.1f°C within operating window with buffer [%.1f, %.1f], transitioning to DRIFTING",
                            current_temp, lower_bound + hysteresis_buffer, upper_bound - hysteresis_buffer)
                return ThermalState.DRIFTING
            
            # Stay in CORRECTING state
            _LOGGER.debug("Temperature %.1f°C still outside safe zone, staying in CORRECTING",
                         current_temp)
            return None
            
        except (AttributeError, TypeError, ValueError) as e:
            _LOGGER.error("Error in CorrectingState execute: %s", e)
            return None

    def _set_learning_target(self, context: "ThermalManager", current_temp: float, operating_window: tuple) -> None:
        """Set learning target temperature for OffsetEngine.
        
        Sets the target to the appropriate boundary temperature that OffsetEngine
        should learn to correct towards.
        
        Args:
            context: ThermalManager instance
            current_temp: Current room temperature
            operating_window: (lower_bound, upper_bound) tuple
        """
        try:
            lower_bound, upper_bound = operating_window
            
            # If within window, target setpoint for maintenance
            if lower_bound <= current_temp <= upper_bound:
                # Try to get setpoint from context, fallback to window center
                try:
                    target = context._setpoint
                    # Validate that target is a real number (not Mock)
                    if not isinstance(target, (int, float)):
                        target = (lower_bound + upper_bound) / 2
                        _LOGGER.debug("Context _setpoint not numeric, using window center %.1f", target)
                except AttributeError:
                    target = (lower_bound + upper_bound) / 2
                    _LOGGER.debug("Context missing _setpoint, using window center %.1f", target)
            
            # If above window, target upper boundary
            elif current_temp > upper_bound:
                target = upper_bound
                
            # If below window, target lower boundary  
            else:
                target = lower_bound
            
            context.learning_target = target
            _LOGGER.debug("Set learning target to %.1f°C for current temp %.1f°C", target, current_temp)
            
        except (AttributeError, TypeError) as e:
            _LOGGER.error("Error setting learning target: %s", e)

    def on_enter(self, context: "ThermalManager") -> None:
        """Called when entering CORRECTING state.
        
        Args:
            context: ThermalManager instance
        """
        _LOGGER.info("Entering CORRECTING state - AC actively correcting temperature")

    def on_exit(self, context: "ThermalManager") -> None:
        """Called when exiting CORRECTING state.
        
        Args:
            context: ThermalManager instance
        """
        _LOGGER.info("Exiting CORRECTING state")