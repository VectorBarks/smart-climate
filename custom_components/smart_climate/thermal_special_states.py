"""ABOUTME: Special thermal state handlers for Smart Climate Control.
Implements PrimingState, RecoveryState, ProbeState, and CalibratingState handlers."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, TYPE_CHECKING

from .thermal_models import ThermalState, ProbeResult, ThermalConstants
from .thermal_states import StateHandler

if TYPE_CHECKING:
    from .thermal_manager import ThermalManager

_LOGGER = logging.getLogger(__name__)


class PrimingState(StateHandler):
    """Handler for PRIMING thermal state.
    
    Conservative learning phase for new users with ±1.2°C bands and aggressive passive learning.
    Runs for 24-48 hours (configurable) before transitioning to normal operation.
    
    Key behaviors:
    - Uses conservative comfort bands (±1.2°C from setpoint)
    - Enables aggressive passive learning to quickly gather thermal data
    - Tracks duration and transitions to DRIFTING when complete
    """
    
    def __init__(self):
        """Initialize PrimingState handler."""
        self._start_time: Optional[datetime] = None

    def execute(self, context: "ThermalManager") -> Optional[ThermalState]:
        """Execute priming state logic and check for transitions.
        
        Args:
            context: ThermalManager instance providing system state
            
        Returns:
            CALIBRATING if calibration hour reached, DRIFTING if priming duration complete, None to stay in PRIMING
        """
        try:
            # Enable aggressive passive learning during priming phase
            if hasattr(context, 'passive_learning_enabled'):
                context.passive_learning_enabled = True
            
            # Handle missing thermal constants
            if not hasattr(context, 'thermal_constants') or context.thermal_constants is None:
                _LOGGER.warning("Missing thermal constants in PrimingState")
                return None
            
            # Handle missing start time (should be set in on_enter)
            if self._start_time is None:
                _LOGGER.warning("Missing start time in PrimingState, staying in priming")
                return None
            
            current_time = datetime.now()
            
            # CRITICAL FIX: Check if it's calibration hour - this takes priority
            # This allows calibration to happen even during priming phase
            calibration_hour = getattr(context, 'calibration_hour', 2)  # Default to 2 AM
            if current_time.hour == calibration_hour:
                _LOGGER.info("Calibration hour (%d AM) reached during PRIMING, transitioning to CALIBRATING",
                           calibration_hour)
                return ThermalState.CALIBRATING
            
            # Check if priming duration is complete
            elapsed_time = (current_time - self._start_time).total_seconds()
            priming_duration = context.thermal_constants.priming_duration
            
            # Log detailed priming check for debugging
            _LOGGER.debug("PrimingState check - elapsed: %.1fh of %.1fh, calibration_hour: %d, current_hour: %d",
                          elapsed_time / 3600.0, priming_duration / 3600.0, 
                          calibration_hour, current_time.hour)
            
            # Handle system clock changes gracefully
            if elapsed_time < 0:
                _LOGGER.warning("System clock moved backward during priming, resetting start time")
                self._start_time = current_time
                return None
            
            if elapsed_time >= priming_duration:
                _LOGGER.info("Priming duration %.1f hours complete, transitioning to DRIFTING",
                           elapsed_time / 3600.0)
                return ThermalState.DRIFTING
            
            # Stay in priming phase
            remaining_hours = (priming_duration - elapsed_time) / 3600.0
            _LOGGER.debug("Priming phase continuing, %.1f hours remaining (need %.1f total)", 
                         remaining_hours, priming_duration / 3600.0)
            return None
            
        except (AttributeError, TypeError, ValueError) as e:
            _LOGGER.error("Error in PrimingState execute: %s", e)
            return None

    def get_conservative_band(self, context: "ThermalManager") -> float:
        """Get conservative comfort band for priming phase.
        
        Args:
            context: ThermalManager instance
            
        Returns:
            Conservative band size (±1.2°C)
        """
        return 1.2  # Conservative ±1.2°C bands per architecture

    def on_enter(self, context: "ThermalManager") -> None:
        """Called when entering PRIMING state.
        
        Args:
            context: ThermalManager instance
        """
        self._start_time = datetime.now()
        duration_hours = 24  # Default duration
        
        try:
            if hasattr(context, 'thermal_constants') and context.thermal_constants:
                duration_hours = context.thermal_constants.priming_duration / 3600.0
        except (AttributeError, TypeError):
            pass
        
        _LOGGER.info("Entering PRIMING state - conservative learning for %.1f hours", duration_hours)

    def on_exit(self, context: "ThermalManager") -> None:
        """Called when exiting PRIMING state.
        
        Args:
            context: ThermalManager instance
        """
        _LOGGER.info("Exiting PRIMING state - transitioning to normal operation")


class RecoveryState(StateHandler):
    """Handler for RECOVERY thermal state.
    
    Provides gradual transition over 30-60 minutes when mode changes cause large temperature deltas.
    Prevents sudden changes that could cause discomfort or system instability.
    
    Key behaviors:
    - Gradual adjustment from initial to final target over recovery duration
    - Tracks transition progress percentage
    - Transitions to appropriate target state when recovery complete
    """
    
    def __init__(self):
        """Initialize RecoveryState handler."""
        self._start_time: Optional[datetime] = None
        self._target_state: ThermalState = ThermalState.DRIFTING
        self._initial_target: Optional[float] = None
        self._final_target: Optional[float] = None
        self._gradual_adjustment: bool = False

    def execute(self, context: "ThermalManager") -> Optional[ThermalState]:
        """Execute recovery state logic and check for transitions.
        
        Args:
            context: ThermalManager instance providing system state
            
        Returns:
            Target state if recovery complete, None to stay in RECOVERY
        """
        try:
            # Handle missing thermal constants
            if not hasattr(context, 'thermal_constants') or context.thermal_constants is None:
                _LOGGER.warning("Missing thermal constants in RecoveryState")
                return None
            
            # Handle missing start time
            if self._start_time is None:
                _LOGGER.warning("Missing start time in RecoveryState, transitioning immediately")
                return self._target_state
            
            # Check if recovery duration is complete
            current_time = datetime.now()
            elapsed_time = (current_time - self._start_time).total_seconds()
            recovery_duration = context.thermal_constants.recovery_duration
            
            # Handle zero duration or system clock changes
            if recovery_duration <= 0 or elapsed_time < 0:
                _LOGGER.info("Recovery duration invalid or clock changed, transitioning immediately")
                return self._target_state
            
            if elapsed_time >= recovery_duration:
                _LOGGER.info("Recovery duration %.1f minutes complete, transitioning to %s",
                           elapsed_time / 60.0, self._target_state.value)
                return self._target_state
            
            # Stay in recovery phase
            progress = elapsed_time / recovery_duration
            _LOGGER.debug("Recovery phase continuing, %.1f%% complete", progress * 100)
            return None
            
        except (AttributeError, TypeError, ValueError) as e:
            _LOGGER.error("Error in RecoveryState execute: %s", e)
            return self._target_state  # Fail safe to target state

    def get_progress(self, context: "ThermalManager") -> float:
        """Get recovery transition progress.
        
        Args:
            context: ThermalManager instance
            
        Returns:
            Progress percentage (0.0-1.0)
        """
        try:
            if self._start_time is None or not hasattr(context, 'thermal_constants'):
                return 1.0  # Complete if no timing info
            
            current_time = datetime.now()
            elapsed_time = (current_time - self._start_time).total_seconds()
            recovery_duration = context.thermal_constants.recovery_duration
            
            if recovery_duration <= 0:
                return 1.0
            
            return min(1.0, max(0.0, elapsed_time / recovery_duration))
            
        except (AttributeError, TypeError, ValueError):
            return 1.0  # Default to complete on error

    def get_adjusted_target(self, context: "ThermalManager") -> Optional[float]:
        """Get adjusted target temperature based on recovery progress.
        
        Args:
            context: ThermalManager instance
            
        Returns:
            Adjusted target temperature or None if not configured
        """
        try:
            if self._initial_target is None or self._final_target is None:
                return None
            
            progress = self.get_progress(context)
            # Linear interpolation between initial and final targets
            adjusted = self._initial_target + (self._final_target - self._initial_target) * progress
            return adjusted
            
        except (AttributeError, TypeError, ValueError):
            return None

    def on_enter(self, context: "ThermalManager") -> None:
        """Called when entering RECOVERY state.
        
        Args:
            context: ThermalManager instance
        """
        self._start_time = datetime.now()
        duration_minutes = 30  # Default duration
        
        try:
            if hasattr(context, 'thermal_constants') and context.thermal_constants:
                duration_minutes = context.thermal_constants.recovery_duration / 60.0
        except (AttributeError, TypeError):
            pass
        
        # Check for large temperature delta from mode changes
        try:
            if (hasattr(context, 'temperature_delta') and 
                hasattr(context, 'previous_mode') and 
                hasattr(context, 'current_mode')):
                if abs(context.temperature_delta) > 3.0:  # Large delta threshold
                    self._gradual_adjustment = True
                    _LOGGER.info("Large temperature delta detected (%.1f°C), enabling gradual adjustment",
                               context.temperature_delta)
        except (AttributeError, TypeError):
            pass
        
        _LOGGER.info("Entering RECOVERY state - gradual transition over %.1f minutes", duration_minutes)

    def on_exit(self, context: "ThermalManager") -> None:
        """Called when exiting RECOVERY state.
        
        Args:
            context: ThermalManager instance
        """
        _LOGGER.info("Exiting RECOVERY state - gradual transition complete")


class ProbeState(StateHandler):
    """Handler for PROBING thermal state.
    
    Active learning with wider drift allowance (±2.0°C) and user notifications.
    Supports abort capability to return to previous state if user is uncomfortable.
    
    Key behaviors:
    - Allows ±2.0°C drift for active thermal time constant measurement
    - Tracks probe start time and temperature for tau calculation
    - Sends phone notifications during active learning
    - Supports abort capability returning to previous state
    - Calculates ProbeResult on completion
    """
    
    def __init__(self):
        """Initialize ProbeState handler."""
        self._probe_start_time: Optional[datetime] = None
        self._probe_start_temp: Optional[float] = None
        self._previous_state: ThermalState = ThermalState.DRIFTING

    def execute(self, context: "ThermalManager") -> Optional[ThermalState]:
        """Execute probing state logic and check for transitions.
        
        Args:
            context: ThermalManager instance providing system state
            
        Returns:
            CALIBRATING on completion, previous state on abort, None to continue probing
        """
        try:
            # Check for abort condition
            if hasattr(context, 'probe_aborted') and context.probe_aborted:
                _LOGGER.info("Probe aborted by user, returning to %s", self._previous_state.value)
                return self._previous_state
            
            # Handle missing start time or temperature
            if self._probe_start_time is None or self._probe_start_temp is None:
                _LOGGER.warning("Missing probe start data, aborting probe")
                return self._previous_state
            
            # Handle invalid current temperature
            current_temp = getattr(context, 'current_temp', None)
            if current_temp is None:
                _LOGGER.warning("Missing current temperature during probe")
                return None  # Continue probing until valid data
            
            # Check if probe has run for minimum duration
            current_time = datetime.now()
            elapsed_time = (current_time - self._probe_start_time).total_seconds()
            min_probe_duration = 1800  # 30 minutes default
            
            try:
                if hasattr(context, 'thermal_constants') and context.thermal_constants:
                    min_probe_duration = getattr(context.thermal_constants, 'min_probe_duration', 1800)
            except (AttributeError, TypeError):
                pass
            
            # Check if sufficient time has elapsed for meaningful data
            if elapsed_time >= min_probe_duration:
                # Calculate probe result
                probe_result = self.calculate_probe_result(context)
                
                if probe_result and not probe_result.aborted:
                    _LOGGER.info("Probe completed successfully after %.1f minutes, transitioning to CALIBRATING",
                               elapsed_time / 60.0)
                    
                    # Store probe result in context if possible
                    if hasattr(context, 'last_probe_result'):
                        context.last_probe_result = probe_result
                    
                    return ThermalState.CALIBRATING
            
            # Continue probing
            _LOGGER.debug("Probe continuing, %.1f minutes elapsed", elapsed_time / 60.0)
            return None
            
        except (AttributeError, TypeError, ValueError) as e:
            _LOGGER.error("Error in ProbeState execute: %s", e)
            return self._previous_state  # Fail safe to previous state

    def is_within_probe_drift(self, context: "ThermalManager") -> bool:
        """Check if current temperature is within allowed probe drift.
        
        Args:
            context: ThermalManager instance
            
        Returns:
            True if within ±2.0°C drift allowance, False otherwise
        """
        try:
            current_temp = getattr(context, 'current_temp', None)
            setpoint = getattr(context, 'setpoint', None)
            
            if current_temp is None or setpoint is None:
                return True  # Assume within drift if data unavailable
            
            drift = abs(current_temp - setpoint)
            return drift <= 2.0  # ±2.0°C drift allowance per architecture
            
        except (AttributeError, TypeError, ValueError):
            return True  # Fail safe to within drift

    def calculate_probe_result(self, context: "ThermalManager") -> Optional[ProbeResult]:
        """Calculate probe result with tau value and confidence.
        
        Args:
            context: ThermalManager instance
            
        Returns:
            ProbeResult with tau value, confidence, and quality metrics
        """
        try:
            if self._probe_start_time is None or self._probe_start_temp is None:
                return None
            
            current_time = datetime.now()
            current_temp = getattr(context, 'current_temp', None)
            outdoor_temp = getattr(context, 'outdoor_temp', None)
            
            if current_temp is None:
                return None
            
            # Calculate probe duration and temperature change
            duration = (current_time - self._probe_start_time).total_seconds()
            temp_change = current_temp - self._probe_start_temp
            
            # Simple tau calculation (could be enhanced with exponential fitting)
            if abs(temp_change) > 0.1:  # Minimum meaningful change
                # Simplified tau estimation based on temperature change rate
                tau_value = duration / (abs(temp_change) * 60.0)  # Convert to minutes
                tau_value = max(1.0, min(600.0, tau_value))  # Clamp to reasonable range
            else:
                tau_value = 90.0  # Default if no significant change
            
            # Calculate confidence based on temperature change magnitude and duration
            confidence = min(1.0, abs(temp_change) * duration / 3600.0)  # Higher for larger change over time
            confidence = max(0.1, min(0.9, confidence))  # Clamp to reasonable range
            
            # Calculate fit quality (simplified metric)
            fit_quality = min(1.0, duration / 1800.0)  # Better with longer duration
            
            return ProbeResult(
                tau_value=tau_value,
                confidence=confidence,
                duration=int(duration),
                fit_quality=fit_quality,
                aborted=False
            )
            
        except (AttributeError, TypeError, ValueError) as e:
            _LOGGER.error("Error calculating probe result: %s", e)
            return None

    def on_enter(self, context: "ThermalManager") -> None:
        """Called when entering PROBING state.
        
        Args:
            context: ThermalManager instance
        """
        self._probe_start_time = datetime.now()
        self._probe_start_temp = getattr(context, 'current_temp', None)
        
        # Send notification about probe start if service available
        try:
            if hasattr(context, 'notification_service') and context.notification_service:
                context.notification_service.send_notification(
                    title="Smart Climate Probe Started",
                    message="Active thermal learning in progress. Temperature may drift ±2°C for better efficiency.",
                    data={"actions": [{"action": "abort_probe", "title": "Abort if Uncomfortable"}]}
                )
        except (AttributeError, TypeError) as e:
            _LOGGER.debug("Could not send probe notification: %s", e)
        
        _LOGGER.info("Entering PROBING state - active learning with ±2.0°C drift allowance")

    def on_exit(self, context: "ThermalManager") -> None:
        """Called when exiting PROBING state.
        
        Args:
            context: ThermalManager instance
        """
        _LOGGER.info("Exiting PROBING state")


class CalibratingState(StateHandler):
    """Handler for CALIBRATING thermal state.
    
    Daily 1-hour window with very tight bands (±0.1°C) for clean offset readings.
    Provides precise measurements for offset engine calibration.
    
    Key behaviors:
    - Uses very tight ±0.1°C bands for precise control
    - Runs for 1-hour duration during optimal daily window
    - Tracks calibration quality metrics
    - Enables precise measurement mode for clean offset readings
    - Transitions to DRIFTING when complete
    """
    
    def __init__(self):
        """Initialize CalibratingState handler."""
        self._start_time: Optional[datetime] = None

    def execute(self, context: "ThermalManager") -> Optional[ThermalState]:
        """Execute calibrating state logic and check for transitions.
        
        Args:
            context: ThermalManager instance providing system state
            
        Returns:
            DRIFTING if calibration window complete, None to stay in CALIBRATING
        """
        try:
            # Enable precise measurement mode for clean offset readings
            if hasattr(context, 'precise_measurement_mode'):
                context.precise_measurement_mode = True
            
            # Handle missing thermal constants
            if not hasattr(context, 'thermal_constants') or context.thermal_constants is None:
                _LOGGER.warning("Missing thermal constants in CalibratingState")
                return ThermalState.DRIFTING  # Exit if no config
            
            # Handle missing start time
            if self._start_time is None:
                _LOGGER.warning("Missing start time in CalibratingState, transitioning immediately")
                return ThermalState.DRIFTING
            
            # Check if calibration duration is complete
            current_time = datetime.now()
            elapsed_time = (current_time - self._start_time).total_seconds()
            calibrating_duration = getattr(context.thermal_constants, 'calibrating_duration', 3600)  # 1 hour default
            
            # Handle zero duration or system clock changes
            if calibrating_duration <= 0 or elapsed_time < 0:
                _LOGGER.info("Calibration duration invalid or clock changed, transitioning to DRIFTING")
                return ThermalState.DRIFTING
            
            if elapsed_time >= calibrating_duration:
                _LOGGER.info("Calibration duration %.1f minutes complete, transitioning to DRIFTING",
                           elapsed_time / 60.0)
                return ThermalState.DRIFTING
            
            # Stay in calibrating phase
            remaining_minutes = (calibrating_duration - elapsed_time) / 60.0
            _LOGGER.debug("Calibration phase continuing, %.1f minutes remaining", remaining_minutes)
            return None
            
        except (AttributeError, TypeError, ValueError) as e:
            _LOGGER.error("Error in CalibratingState execute: %s", e)
            return ThermalState.DRIFTING  # Fail safe to drifting

    def get_calibration_band(self, context: "ThermalManager") -> float:
        """Get very tight calibration band.
        
        Args:
            context: ThermalManager instance
            
        Returns:
            Tight calibration band (±0.1°C)
        """
        return 0.1  # Very tight ±0.1°C bands per architecture

    def get_calibration_quality(self, context: "ThermalManager") -> Dict[str, float]:
        """Get calibration quality metrics.
        
        Args:
            context: ThermalManager instance
            
        Returns:
            Dictionary with stability, precision, and duration metrics
        """
        try:
            current_temp = getattr(context, 'current_temp', None)
            setpoint = getattr(context, 'setpoint', None)
            temperature_stability = getattr(context, 'temperature_stability', 0.5)
            
            metrics = {
                'stability': temperature_stability,
                'precision': 0.0,
                'duration': 0.0
            }
            
            # Calculate precision based on temperature deviation from setpoint
            if current_temp is not None and setpoint is not None:
                deviation = abs(current_temp - setpoint)
                # Higher precision score for smaller deviations
                metrics['precision'] = max(0.0, 1.0 - deviation / 1.0)  # Scale by 1°C
            
            # Calculate duration metric
            if self._start_time is not None:
                elapsed_time = (datetime.now() - self._start_time).total_seconds()
                # Higher score for longer stable calibration
                metrics['duration'] = min(1.0, elapsed_time / 3600.0)  # Scale by 1 hour
            
            return metrics
            
        except (AttributeError, TypeError, ValueError):
            return {'stability': 0.0, 'precision': 0.0, 'duration': 0.0}

    def is_optimal_calibration_time(self, context: "ThermalManager") -> bool:
        """Check if current time is within optimal calibration window.
        
        Args:
            context: ThermalManager instance
            
        Returns:
            True if within configured calibration window (calibration_hour to calibration_hour+1), False otherwise
        """
        try:
            current_time = datetime.now()
            hour = current_time.hour
            
            # Get configured calibration hour from context, fallback to 2 AM default
            calibration_hour = getattr(context, 'calibration_hour', 2)
            
            # Calibration window: configured hour to configured hour + 1
            # e.g., calibration_hour=2 means 2-3 AM window
            return calibration_hour <= hour < calibration_hour + 1
            
        except (AttributeError, TypeError, ValueError):
            return False  # Not optimal if we can't determine time

    def on_enter(self, context: "ThermalManager") -> None:
        """Called when entering CALIBRATING state.
        
        Args:
            context: ThermalManager instance
        """
        self._start_time = datetime.now()
        duration_minutes = 60  # Default 1 hour
        
        try:
            if hasattr(context, 'thermal_constants') and context.thermal_constants:
                duration_minutes = getattr(context.thermal_constants, 'calibrating_duration', 3600) / 60.0
        except (AttributeError, TypeError):
            pass
        
        _LOGGER.info("Entering CALIBRATING state - precise offset measurement for %.1f minutes", duration_minutes)

    def on_exit(self, context: "ThermalManager") -> None:
        """Called when exiting CALIBRATING state.
        
        Args:
            context: ThermalManager instance
        """
        # Disable precise measurement mode
        if hasattr(context, 'precise_measurement_mode'):
            context.precise_measurement_mode = False
        
        _LOGGER.info("Exiting CALIBRATING state - calibration window complete")