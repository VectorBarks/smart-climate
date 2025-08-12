"""ABOUTME: Special thermal state handlers for Smart Climate Control.
Implements PrimingState, RecoveryState, ProbeState, and CalibratingState handlers."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple, TYPE_CHECKING, Literal

from .thermal_models import ThermalState, ProbeResult, ThermalConstants
from .thermal_states import StateHandler
from . import thermal_utils

if TYPE_CHECKING:
    from .thermal_manager import ThermalManager

_LOGGER = logging.getLogger(__name__)

# Phase types for PRIMING state
PrimingPhase = Literal['passive', 'active']

# Controlled drift states
ControlledDriftState = Literal['inactive', 'requested', 'monitoring', 'analyzing']


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
    
    Enhanced two-phase learning approach for new users with tiered passive/active learning.
    Runs for 24-48 hours (configurable) with phase-specific behaviors.
    
    THERMAL STATE FLOW: PRIMING → PROBING → CALIBRATING → DRIFTING
    
    Phase 1 (0-24h): Enhanced passive learning
    - Conservative comfort bands (±1.2°C from setpoint)
    - Aggressive passive learning with micro-drift analysis (5+ minutes)
    - Lower confidence threshold (0.25) for passive learning acceptance
    
    Phase 2 (24-48h): Controlled drift if needed
    - Controlled drift requests only if no tau learned yet
    - Safety checks: avoid sleep hours, monitor temperature deviation
    - Abort controlled drift if temperature changes >0.5°C for comfort
    """
    
    def __init__(self):
        """Initialize PrimingState handler."""
        self._start_time: Optional[datetime] = None
        self._current_phase: PrimingPhase = 'passive'
        self._controlled_drift_state: ControlledDriftState = 'inactive'
        self._controlled_drift_attempted: bool = False
        self._controlled_drift_start_time: Optional[datetime] = None
        self._controlled_drift_start_temp: Optional[float] = None
        self._temperature_history: List[Tuple[float, float]] = []  # (timestamp, temperature)

    def execute(self, context: "ThermalManager", current_temp: float, operating_window: tuple[float, float]) -> Optional[ThermalState]:
        """Execute enhanced priming state logic with two-phase learning.
        
        Args:
            context: ThermalManager instance providing system state
            current_temp: Current room temperature in Celsius
            operating_window: Tuple of (lower_bound, upper_bound) temperatures
            
        Returns:
            PROBING if stable conditions detected, DRIFTING if priming duration complete, None to stay in PRIMING
        """
        try:
            current_time = datetime.now()
            
            # Handle missing start time (should be set in on_enter or restored from persistence)
            if self._start_time is None:
                _LOGGER.warning("Missing start time in PrimingState, initializing to current time")
                self._start_time = current_time
                # Also trigger persistence to save this start time
                if hasattr(context, '_persistence_callback') and context._persistence_callback:
                    try:
                        context._persistence_callback()
                    except Exception as e:
                        _LOGGER.debug("Could not trigger persistence callback: %s", e)
            
            # Handle missing thermal constants
            if not hasattr(context, 'thermal_constants') or context.thermal_constants is None:
                _LOGGER.warning("Missing thermal constants in PrimingState")
                return None
            
            # Handle system clock changes gracefully
            elapsed_time = (current_time - self._start_time).total_seconds()
            if elapsed_time < 0:
                _LOGGER.warning("System clock moved backward during priming, resetting start time")
                self._start_time = current_time
                return None
            
            priming_duration = context.thermal_constants.priming_duration
            elapsed_hours = elapsed_time / 3600.0
            
            # Collect temperature history continuously
            if current_temp is not None:
                timestamp = current_time.timestamp()
                self._temperature_history.append((timestamp, current_temp))
                # Keep only last 4 hours of data
                cutoff_time = timestamp - (4 * 3600)
                self._temperature_history = [(t, temp) for t, temp in self._temperature_history if t >= cutoff_time]
            
            # Update stability detector if available
            if hasattr(context, 'stability_detector') and context.stability_detector and current_temp is not None:
                ac_state = self._get_current_hvac_state(context)
                context.stability_detector.add_reading(timestamp, current_temp, ac_state)
                
                # Update regular stability detector as well
                context.stability_detector.update(ac_state, current_temp)
            
            # Determine current phase based on elapsed time and learning progress
            self._update_current_phase(elapsed_hours, context)
            
            # Check for opportunistic probing during stable conditions
            if hasattr(context, 'stability_detector') and context.stability_detector:
                if context.stability_detector.is_stable_for_calibration():
                    _LOGGER.info("Stable conditions detected during PRIMING phase %s, transitioning to PROBING", 
                               self._current_phase)
                    return ThermalState.PROBING
            
            # Phase-specific behavior
            if self._current_phase == 'passive':
                # Phase 1: Enhanced passive learning with shorter drift requirements
                self._handle_passive_phase(context)
            elif self._current_phase == 'active':
                # Phase 2: Controlled drift if tau not learned yet
                result = self._handle_active_phase(context, current_temp)
                if result is not None:
                    return result
            
            # Check if priming duration is complete
            if elapsed_time >= priming_duration:
                _LOGGER.info("Priming duration %.1f hours complete (phase: %s), transitioning to DRIFTING",
                           elapsed_hours, self._current_phase)
                return ThermalState.DRIFTING
            
            # Log progress
            remaining_hours = (priming_duration - elapsed_time) / 3600.0
            _LOGGER.debug("Priming phase %s continuing, %.1f hours remaining, %d temp readings", 
                         self._current_phase, remaining_hours, len(self._temperature_history))
            
            return None
            
        except (AttributeError, TypeError, ValueError) as e:
            _LOGGER.error("Error in PrimingState execute: %s", e)
            return None
    
    def _get_current_hvac_state(self, context: "ThermalManager") -> str:
        """Get current HVAC state for stability tracking.
        
        Args:
            context: ThermalManager instance
            
        Returns:
            HVAC state string ("cooling", "heating", "idle", "off")
        """
        try:
            # Try to get actual HVAC state from context
            # This is a placeholder - actual implementation would read from HA climate entity
            if hasattr(context, '_last_hvac_mode'):
                mode = getattr(context, '_last_hvac_mode', 'off')
                if mode in ['cool', 'heat', 'auto']:
                    # For now, assume idle if mode is set but not actively running
                    return 'idle'
            return 'off'
        except Exception:
            return 'off'
    
    def _update_current_phase(self, elapsed_hours: float, context: "ThermalManager") -> None:
        """Update current phase based on elapsed time and learning progress.
        
        Args:
            elapsed_hours: Hours elapsed since priming started
            context: ThermalManager instance
        """
        if elapsed_hours < 24:
            if self._current_phase != 'passive':
                self._current_phase = 'passive'
                _LOGGER.info("Entering PRIMING passive phase (0-24h): enhanced passive learning")
        else:
            if self._current_phase != 'active':
                self._current_phase = 'active'
                _LOGGER.info("Entering PRIMING active phase (24-48h): controlled drift if needed")
    
    def _handle_passive_phase(self, context: "ThermalManager") -> None:
        """Handle passive learning phase with enhanced micro-drift analysis.
        
        Args:
            context: ThermalManager instance
        """
        # Enable aggressive passive learning with shorter minimum drift time
        passive_learning_enabled = getattr(context, 'passive_learning_enabled', True)
        
        if passive_learning_enabled:
            # Set enhanced parameters for PRIMING passive phase
            if hasattr(context, 'stability_detector') and context.stability_detector:
                # Look for natural drift events with shorter duration requirement for PRIMING
                drift_data = context.stability_detector.find_natural_drift_event_priming(min_duration_minutes=5)
                if drift_data:
                    _LOGGER.info("Found micro-drift event during PRIMING passive phase: %d points, %.1f minutes",
                               len(drift_data), (drift_data[-1][0] - drift_data[0][0]) / 60.0)
                    
                    # Analyze with lower confidence threshold for passive learning
                    probe_result = thermal_utils.analyze_drift_data(drift_data, is_passive=True)
                    if probe_result and probe_result.confidence >= 0.25:  # Lower threshold during PRIMING
                        _LOGGER.info("Passive learning successful in PRIMING: tau=%.1f, confidence=%.3f",
                                   probe_result.tau_value, probe_result.confidence)
                        
                        # Update thermal model
                        if hasattr(context, '_model') and context._model:
                            is_cooling = getattr(context, '_last_hvac_mode', 'cool') == 'cool'
                            context._model.update_tau(probe_result, is_cooling)
                            _trigger_persistence(context)
                else:
                    # Fallback to regular drift detection as well
                    drift_data = context.stability_detector.find_natural_drift_event()
                    if drift_data:
                        _LOGGER.debug("Found regular drift event during PRIMING passive phase: %d points, %.1f minutes",
                                    len(drift_data), (drift_data[-1][0] - drift_data[0][0]) / 60.0)
                        
                        # Analyze with lower confidence threshold for passive learning
                        probe_result = thermal_utils.analyze_drift_data(drift_data, is_passive=True)
                        if probe_result and probe_result.confidence >= 0.25:  # Lower threshold during PRIMING
                            _LOGGER.info("Regular passive learning successful in PRIMING: tau=%.1f, confidence=%.3f",
                                       probe_result.tau_value, probe_result.confidence)
                            
                            # Update thermal model
                            if hasattr(context, '_model') and context._model:
                                is_cooling = getattr(context, '_last_hvac_mode', 'cool') == 'cool'
                                context._model.update_tau(probe_result, is_cooling)
                                _trigger_persistence(context)
            
            # Trigger any existing passive learning handler
            if hasattr(context, '_handle_passive_learning'):
                try:
                    context._handle_passive_learning()
                except Exception as e:
                    _LOGGER.warning("Error in passive learning during priming: %s", e)
    
    def _handle_active_phase(self, context: "ThermalManager", current_temp: Optional[float]) -> Optional[ThermalState]:
        """Handle active phase with controlled drift capability.
        
        Args:
            context: ThermalManager instance
            current_temp: Current room temperature
            
        Returns:
            ThermalState to transition to, or None to continue
        """
        # Check if we already have sufficient tau learning
        if hasattr(context, '_model') and context._model:
            confidence = getattr(context._model, 'get_confidence', lambda: 0.0)()
            if confidence > 0.3:
                _LOGGER.debug("Sufficient tau learned (confidence=%.3f), staying passive", confidence)
                return None
        
        # Only attempt controlled drift if not already attempted
        if self._controlled_drift_attempted:
            _LOGGER.debug("Controlled drift already attempted, continuing passive learning")
            return None
        
        # Handle controlled drift state machine
        if self._controlled_drift_state == 'inactive':
            # Check if conditions are safe for controlled drift
            if self._is_safe_for_controlled_drift():
                _LOGGER.info("Initiating controlled drift during active phase")
                self._controlled_drift_state = 'requested'
                self._controlled_drift_start_time = datetime.now()
                self._controlled_drift_start_temp = current_temp
                
                # Request HVAC to turn off for controlled drift
                self._request_hvac_off(context)
                
        elif self._controlled_drift_state == 'requested':
            # Wait for HVAC to actually turn off, then start monitoring
            if self._is_hvac_off(context):
                self._controlled_drift_state = 'monitoring'
                _LOGGER.info("HVAC off confirmed, starting controlled drift monitoring")
            
        elif self._controlled_drift_state == 'monitoring':
            # Monitor temperature during controlled drift
            if current_temp is not None and self._controlled_drift_start_temp is not None:
                temp_change = abs(current_temp - self._controlled_drift_start_temp)
                
                # Abort if temperature change is too large for comfort
                if temp_change > 0.5:
                    _LOGGER.warning("Aborting controlled drift: temperature change %.2f°C > 0.5°C limit",
                                  temp_change)
                    self._abort_controlled_drift(context)
                    return None
                
                # Check if we have enough data for analysis (20 minutes or more)
                if self._controlled_drift_start_time:
                    elapsed_minutes = (datetime.now() - self._controlled_drift_start_time).total_seconds() / 60.0
                    if elapsed_minutes >= 20:
                        self._controlled_drift_state = 'analyzing'
                        _LOGGER.info("Controlled drift complete after %.1f minutes, analyzing data", elapsed_minutes)
        
        elif self._controlled_drift_state == 'analyzing':
            # Analyze collected controlled drift data
            self._analyze_controlled_drift(context)
            self._controlled_drift_attempted = True  # Mark as attempted regardless of result
            self._controlled_drift_state = 'inactive'
            
            # Trigger persistence to save state
            if hasattr(context, '_persistence_callback') and context._persistence_callback:
                try:
                    context._persistence_callback()
                except Exception as e:
                    _LOGGER.debug("Could not trigger persistence after controlled drift: %s", e)
        
        return None
    
    def _is_safe_for_controlled_drift(self) -> bool:
        """Check if conditions are safe for controlled drift.
        
        Returns:
            True if safe to initiate controlled drift
        """
        current_time = datetime.now()
        current_hour = current_time.hour
        
        # Avoid sleep hours (22:00-06:00)
        if current_hour >= 22 or current_hour <= 6:
            _LOGGER.debug("Controlled drift not safe during sleep hours (%02d:00)", current_hour)
            return False
        
        # Additional safety checks could be added here:
        # - Check outdoor temperature if available
        # - Check for recent temperature changes
        # - Check HVAC cycle timing
        
        return True
    
    def _request_hvac_off(self, context: "ThermalManager") -> None:
        """Request HVAC to turn off for controlled drift.
        
        Args:
            context: ThermalManager instance
        """
        try:
            # This would integrate with the climate entity to request AC off
            # For now, just log the request
            _LOGGER.info("Requesting HVAC off for controlled drift learning")
            
            # In a real implementation, this would:
            # 1. Set a flag that the AC control logic can read
            # 2. Or directly interface with the climate entity
            # 3. Have a timeout mechanism to resume normal operation
            
        except Exception as e:
            _LOGGER.error("Error requesting HVAC off: %s", e)
    
    def _is_hvac_off(self, context: "ThermalManager") -> bool:
        """Check if HVAC is actually off.
        
        Args:
            context: ThermalManager instance
            
        Returns:
            True if HVAC is confirmed off
        """
        # Placeholder implementation - would check actual HVAC state
        return True
    
    def _abort_controlled_drift(self, context: "ThermalManager") -> None:
        """Abort controlled drift and resume normal operation.
        
        Args:
            context: ThermalManager instance
        """
        _LOGGER.warning("Aborting controlled drift - safety limit exceeded")
        self._controlled_drift_state = 'inactive'
        self._controlled_drift_attempted = True
        
        # Resume normal HVAC operation
        # This would integrate with the climate control logic
    
    def _analyze_controlled_drift(self, context: "ThermalManager") -> None:
        """Analyze controlled drift data and update thermal model.
        
        Args:
            context: ThermalManager instance
        """
        if not self._controlled_drift_start_time or len(self._temperature_history) < 10:
            _LOGGER.warning("Insufficient data for controlled drift analysis")
            return
        
        # Extract temperature data from the controlled drift period
        start_timestamp = self._controlled_drift_start_time.timestamp()
        drift_data = [(t, temp) for t, temp in self._temperature_history if t >= start_timestamp]
        
        if len(drift_data) < 10:
            _LOGGER.warning("Insufficient controlled drift data points: %d", len(drift_data))
            return
        
        # Analyze with standard confidence (not passive scaling)
        probe_result = thermal_utils.analyze_drift_data(drift_data, is_passive=False)
        
        if probe_result and probe_result.confidence > 0.3:
            _LOGGER.info("Controlled drift analysis successful: tau=%.1f, confidence=%.3f",
                       probe_result.tau_value, probe_result.confidence)
            
            # Update thermal model
            if hasattr(context, '_model') and context._model:
                is_cooling = getattr(context, '_last_hvac_mode', 'cool') == 'cool'
                context._model.update_tau(probe_result, is_cooling)
                _trigger_persistence(context)
        else:
            _LOGGER.info("Controlled drift analysis failed or low confidence (%.3f)",
                       probe_result.confidence if probe_result else 0.0)

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
        self._current_phase = 'passive'  # Always start in passive phase
        self._controlled_drift_state = 'inactive'
        self._controlled_drift_attempted = False
        self._controlled_drift_start_time = None
        self._controlled_drift_start_temp = None
        self._temperature_history = []  # Reset temperature history
        
        duration_hours = 24  # Default duration
        
        try:
            if hasattr(context, 'thermal_constants') and context.thermal_constants:
                duration_hours = context.thermal_constants.priming_duration / 3600.0
        except (AttributeError, TypeError):
            pass
        
        _LOGGER.info("Entering PRIMING state - enhanced two-phase learning for %.1f hours", duration_hours)

    def on_exit(self, context: "ThermalManager") -> None:
        """Called when exiting PRIMING state.
        
        Args:
            context: ThermalManager instance
        """
        _LOGGER.info("Exiting PRIMING state - completed %s phase, transitioning to normal operation", 
                   self._current_phase)
        
        # Clean up any ongoing controlled drift
        if self._controlled_drift_state != 'inactive':
            _LOGGER.info("Cleaning up ongoing controlled drift state: %s", self._controlled_drift_state)
            self._controlled_drift_state = 'inactive'


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