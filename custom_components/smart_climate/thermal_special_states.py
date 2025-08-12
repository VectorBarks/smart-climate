"""ABOUTME: Special thermal state handlers for Smart Climate Control.
Implements PrimingState, RecoveryState, ProbeState, and CalibratingState handlers."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple, TYPE_CHECKING

from .thermal_models import ThermalState, ProbeResult, ThermalConstants
from .thermal_states import StateHandler
from . import thermal_utils

if TYPE_CHECKING:
    from .thermal_manager import ThermalManager

_LOGGER = logging.getLogger(__name__)


def _trigger_persistence(context: "ThermalManager") -> None:
    """Helper function to trigger persistence after tau updates.
    
    Args:
        context: ThermalManager instance
    """
    if hasattr(context, '_persistence_callback') and context._persistence_callback:
        try:
            context._persistence_callback()
            _LOGGER.debug("Triggered persistence callback after tau update")
        except Exception as e:
            _LOGGER.warning("Could not trigger persistence callback: %s", e)


class PrimingState(StateHandler):
    """Handler for PRIMING thermal state.
    
    Conservative learning phase for new users with ±1.2°C bands and aggressive passive learning.
    Runs for 24-48 hours (configurable) before transitioning to normal operation.
    
    THERMAL STATE FLOW: PRIMING → PROBING → CALIBRATING → DRIFTING
    
    Key behaviors:
    - Uses conservative comfort bands (±1.2°C from setpoint)
    - Enables aggressive passive learning to quickly gather thermal data
    - Transitions to PROBING when stable conditions detected
    - Transitions to DRIFTING when priming duration complete
    """
    
    def __init__(self):
        """Initialize PrimingState handler."""
        self._start_time: Optional[datetime] = None

    def execute(self, context: "ThermalManager", current_temp: float, operating_window: tuple[float, float]) -> Optional[ThermalState]:
        """Execute priming state logic and check for transitions.
        
        Args:
            context: ThermalManager instance providing system state
            current_temp: Current room temperature in Celsius
            operating_window: Tuple of (lower_bound, upper_bound) temperatures
            
        Returns:
            PROBING if stable conditions detected, DRIFTING if priming duration complete, None to stay in PRIMING
        """
        try:
            # Check if passive learning is enabled (default to True if not set)
            passive_learning_enabled = getattr(context, 'passive_learning_enabled', True)
            
            # Enable aggressive passive learning during priming phase (if not explicitly disabled)
            if passive_learning_enabled:
                # Set the attribute if it doesn't exist or enable if True
                context.passive_learning_enabled = True
                
                # Trigger passive learning if handler available
                if hasattr(context, '_handle_passive_learning'):
                    try:
                        context._handle_passive_learning()
                    except Exception as e:
                        _LOGGER.warning("Error in passive learning during priming: %s", e)
            
            # Handle missing thermal constants
            if not hasattr(context, 'thermal_constants') or context.thermal_constants is None:
                _LOGGER.warning("Missing thermal constants in PrimingState")
                return None
            
            # Handle missing start time (should be set in on_enter or restored from persistence)
            if self._start_time is None:
                _LOGGER.warning("Missing start time in PrimingState, initializing to current time")
                self._start_time = datetime.now()
                # Also trigger persistence to save this start time
                if hasattr(context, '_persistence_callback') and context._persistence_callback:
                    try:
                        context._persistence_callback()
                    except Exception as e:
                        _LOGGER.debug("Could not trigger persistence callback: %s", e)
            
            current_time = datetime.now()
            
            # Check if stable conditions detected for opportunistic probing
            if hasattr(context, 'stability_detector') and context.stability_detector:
                if context.stability_detector.is_stable_for_calibration():
                    _LOGGER.info("Stable conditions detected during PRIMING, transitioning to PROBING")
                    return ThermalState.PROBING
            
            # Check if priming duration is complete
            elapsed_time = (current_time - self._start_time).total_seconds()
            priming_duration = context.thermal_constants.priming_duration
            
            # Log detailed priming check for debugging  
            stability_ready = False
            if hasattr(context, 'stability_detector') and context.stability_detector:
                stability_ready = context.stability_detector.is_stable_for_calibration()
            _LOGGER.debug("PrimingState check - elapsed: %.1fh of %.1fh, stability_ready: %s",
                          elapsed_time / 3600.0, priming_duration / 3600.0, stability_ready)
            
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

    def execute(self, context: "ThermalManager", current_temp: float, operating_window: tuple[float, float]) -> Optional[ThermalState]:
        """Execute recovery state logic and check for transitions.
        
        Args:
            context: ThermalManager instance providing system state
            current_temp: Current room temperature in Celsius
            operating_window: Tuple of (lower_bound, upper_bound) temperatures
            
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
    
    THERMAL STATE FLOW: PRIMING → PROBING → CALIBRATING → DRIFTING
    
    Key behaviors:
    - Allows ±2.0°C drift for active thermal time constant measurement
    - Tracks probe start time and temperature for tau calculation
    - Sends phone notifications during active learning
    - Supports abort capability returning to previous state
    - Transitions to CALIBRATING when probe completes successfully
    """
    
    def __init__(self):
        """Initialize ProbeState handler."""
        self._probe_start_time: Optional[datetime] = None
        self._probe_start_temp: Optional[float] = None
        self._previous_state: ThermalState = ThermalState.DRIFTING
        self._temperature_history: List[Tuple[float, float]] = []  # (timestamp, temperature)

    def execute(self, context: "ThermalManager", current_temp: float, operating_window: tuple[float, float]) -> Optional[ThermalState]:
        """Execute probing state logic and check for transitions.
        
        Args:
            context: ThermalManager instance providing system state
            current_temp: Current room temperature in Celsius
            operating_window: Tuple of (lower_bound, upper_bound) temperatures
            
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
            
            # Collect temperature data for analysis
            current_time = datetime.now()
            timestamp = current_time.timestamp()
            self._temperature_history.append((timestamp, current_temp))
            
            # Check if probe has run for minimum duration
            elapsed_time = (current_time - self._probe_start_time).total_seconds()
            min_probe_duration = 1800  # 30 minutes default
            
            try:
                if hasattr(context, 'thermal_constants') and context.thermal_constants:
                    min_probe_duration = getattr(context.thermal_constants, 'min_probe_duration', 1800)
            except (AttributeError, TypeError):
                pass
            
            # Check if sufficient time has elapsed for meaningful data
            if elapsed_time >= min_probe_duration:
                # Analyze temperature data using thermal_utils
                probe_result = thermal_utils.analyze_drift_data(self._temperature_history)
                
                if probe_result:
                    _LOGGER.info("Probe analysis successful after %.1f minutes: tau=%.1f, confidence=%.3f",
                               elapsed_time / 60.0, probe_result.tau_value, probe_result.confidence)
                    
                    # Update thermal model with probe result
                    if hasattr(context, '_model') and context._model:
                        # Determine cooling vs warming mode
                        is_cooling = getattr(context, '_last_hvac_mode', 'cool') == "cool" or (
                            getattr(context, '_last_hvac_mode', 'cool') == "auto" and 
                            current_temp > getattr(context, '_setpoint', current_temp + 1)
                        )
                        
                        context._model.update_tau(probe_result, is_cooling)
                        _LOGGER.info("Updated thermal model with probe result: cooling=%s", is_cooling)
                        
                        # Trigger persistence after tau update
                        _trigger_persistence(context)
                    
                    # Store probe result in context if possible
                    if hasattr(context, 'last_probe_result'):
                        context.last_probe_result = probe_result
                    
                    return ThermalState.CALIBRATING
                else:
                    _LOGGER.warning("Probe analysis failed with %d data points, extending probe duration",
                                  len(self._temperature_history))
                    # Continue probing to gather more data
            
            # Continue probing
            _LOGGER.debug("Probe continuing, %.1f minutes elapsed, %d data points collected", 
                         elapsed_time / 60.0, len(self._temperature_history))
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
        self._temperature_history = []  # Reset temperature history for new probe
        
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
    
    THERMAL STATE FLOW: PRIMING → PROBING → CALIBRATING → DRIFTING
    
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
        self._temperature_history: List[Tuple[float, float]] = []  # (timestamp, temperature)

    def execute(self, context: "ThermalManager", current_temp: float, operating_window: tuple[float, float]) -> Optional[ThermalState]:
        """Execute calibrating state logic and check for transitions.
        
        Args:
            context: ThermalManager instance providing system state
            current_temp: Current room temperature in Celsius
            operating_window: Tuple of (lower_bound, upper_bound) temperatures
            
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
            
            # Collect temperature data for potential analysis
            current_time = datetime.now()
            if current_temp is not None:
                timestamp = current_time.timestamp()
                self._temperature_history.append((timestamp, current_temp))
            
            # Check if calibration duration is complete
            elapsed_time = (current_time - self._start_time).total_seconds()
            calibrating_duration = getattr(context.thermal_constants, 'calibrating_duration', 3600)  # 1 hour default
            
            # Handle zero duration or system clock changes
            if calibrating_duration <= 0 or elapsed_time < 0:
                _LOGGER.info("Calibration duration invalid or clock changed, transitioning to DRIFTING")
                return ThermalState.DRIFTING
            
            if elapsed_time >= calibrating_duration:
                _LOGGER.info("Calibration duration %.1f minutes complete with %d data points, analyzing data",
                           elapsed_time / 60.0, len(self._temperature_history))
                
                # Try to analyze collected data for potential tau refinement
                if len(self._temperature_history) >= 10:
                    probe_result = thermal_utils.analyze_drift_data(self._temperature_history)
                    
                    if probe_result and probe_result.confidence > 0.3:  # Higher threshold for calibration
                        _LOGGER.info("Calibration analysis successful: tau=%.1f, confidence=%.3f",
                                   probe_result.tau_value, probe_result.confidence)
                        
                        # Update thermal model with calibration result
                        if hasattr(context, '_model') and context._model:
                            # Determine cooling vs warming mode
                            is_cooling = getattr(context, '_last_hvac_mode', 'cool') == "cool" or (
                                getattr(context, '_last_hvac_mode', 'cool') == "auto" and 
                                current_temp > getattr(context, '_setpoint', current_temp + 1)
                            )
                            
                            context._model.update_tau(probe_result, is_cooling)
                            _LOGGER.info("Updated thermal model with calibration result: cooling=%s", is_cooling)
                            
                            # Trigger persistence after tau update
                            _trigger_persistence(context)
                    else:
                        _LOGGER.debug("Calibration data insufficient for tau update (confidence=%.3f)",
                                    probe_result.confidence if probe_result else 0.0)
                else:
                    _LOGGER.debug("Insufficient calibration data points (%d) for analysis",
                                len(self._temperature_history))
                
                return ThermalState.DRIFTING
            
            # Stay in calibrating phase
            remaining_minutes = (calibrating_duration - elapsed_time) / 60.0
            _LOGGER.debug("Calibration phase continuing, %.1f minutes remaining, %d data points collected", 
                         remaining_minutes, len(self._temperature_history))
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
        """Check if current time is optimal for calibration.
        
        Args:
            context: ThermalManager instance
            
        Returns:
            True if conditions are good for calibration (now uses stability detection)
        """
        try:
            # With opportunistic calibration, we rely on stability detection
            # rather than fixed time windows
            if hasattr(context, 'stability_detector') and context.stability_detector:
                return context.stability_detector.is_stable_for_calibration()
            
            # Fallback: assume any time is acceptable if no stability detector
            return True
            
        except (AttributeError, TypeError, ValueError):
            return False  # Not optimal if we can't determine stability

    def on_enter(self, context: "ThermalManager") -> None:
        """Called when entering CALIBRATING state.
        
        Args:
            context: ThermalManager instance
        """
        self._start_time = datetime.now()
        self._temperature_history = []  # Reset temperature history for new calibration
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