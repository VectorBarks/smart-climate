"""ABOUTME: Thermal efficiency state machine orchestrator for Smart Climate Control.
Coordinates thermal states, operating window calculations, and AC control decisions."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Tuple, Optional, Any, Callable
from datetime import datetime
from homeassistant.core import HomeAssistant

from .thermal_models import ThermalState, ThermalConstants
from .thermal_preferences import UserPreferences
from .thermal_model import PassiveThermalModel

_LOGGER = logging.getLogger(__name__)


class StateHandler(ABC):
    """Abstract base class for thermal state handlers.
    
    Each thermal state has a handler that implements state-specific behavior
    for operating window calculations and state transitions.
    """

    @abstractmethod
    def execute(self, context: 'ThermalManager', current_temp: Optional[float] = None, operating_window: Optional[tuple] = None) -> Optional[ThermalState]:
        """Execute state-specific logic and return next state if transition needed.
        
        Args:
            context: ThermalManager instance for access to models and data
            current_temp: Current room temperature
            operating_window: Operating window (lower_bound, upper_bound) tuple
            
        Returns:
            Next ThermalState to transition to, or None to stay in current state
        """
        pass

    def on_enter(self, context: 'ThermalManager') -> None:
        """Called when entering this state.
        
        Args:
            context: ThermalManager instance
        """
        pass

    def on_exit(self, context: 'ThermalManager') -> None:
        """Called when exiting this state.
        
        Args:
            context: ThermalManager instance
        """
        pass


class DefaultStateHandler(StateHandler):
    """Default state handler implementation for states without specific handlers."""

    def execute(self, context: 'ThermalManager', current_temp: Optional[float] = None, operating_window: Optional[tuple] = None) -> Optional[ThermalState]:
        """Default execute - no state transitions."""
        return None


class ThermalManager:
    """Thermal efficiency state machine orchestrator.
    
    Coordinates all thermal states and provides state-aware operating window
    calculations and AC control decisions. Central coordination point for
    thermal efficiency system.
    
    Args:
        hass: Home Assistant instance
        thermal_model: PassiveThermalModel for temperature predictions
        preferences: UserPreferences for comfort band calculations
    """

    def __init__(
        self,
        hass: HomeAssistant,
        thermal_model: PassiveThermalModel,
        preferences: UserPreferences,
        config: Optional[Dict[str, Any]] = None,
        persistence_callback: Optional[Callable[[], None]] = None
    ):
        """Initialize ThermalManager."""
        self._hass = hass
        self._model = thermal_model
        self._preferences = preferences
        self._config = config or {}
        self._persistence_callback = persistence_callback
        self._current_state = ThermalState.PRIMING  # Default to PRIMING for new users
        self._state_handlers: Dict[ThermalState, StateHandler] = {}
        self._last_hvac_mode = "cool"  # Default assumption
        self._setpoint = 24.0  # Default setpoint
        self._last_transition: Optional[datetime] = None
        
        # Diagnostic properties per §10.2.3
        self._thermal_data_last_saved: Optional[datetime] = None
        self._thermal_state_restored: bool = False
        self._corruption_recovery_count: int = 0
        self._saves_count: int = 0
        
        # Initialize thermal constants from config or defaults
        self.thermal_constants = ThermalConstants(
            tau_cooling=self._config.get('tau_cooling', 90.0),
            tau_warming=self._config.get('tau_warming', 150.0),
            min_off_time=self._config.get('min_off_time', 600),
            min_on_time=self._config.get('min_on_time', 300),
            priming_duration=self._config.get('priming_duration', 86400),
            recovery_duration=self._config.get('recovery_duration', 1800)
        )
        
        # Initialize state handlers registry
        self._initialize_state_handlers()
        
        _LOGGER.debug("ThermalManager initialized in %s state", self._current_state.value)

    def _initialize_state_handlers(self) -> None:
        """Initialize state handlers registry with actual implementations."""
        # Import and register actual state handlers
        try:
            from .thermal_special_states import PrimingState, CalibratingState, RecoveryState, ProbeState
            from .thermal_state_handlers import DriftingState, CorrectingState
            
            # Register concrete state handlers
            self._state_handlers[ThermalState.PRIMING] = PrimingState()
            self._state_handlers[ThermalState.DRIFTING] = DriftingState()
            self._state_handlers[ThermalState.CORRECTING] = CorrectingState()
            self._state_handlers[ThermalState.RECOVERY] = RecoveryState()
            self._state_handlers[ThermalState.PROBING] = ProbeState()
            self._state_handlers[ThermalState.CALIBRATING] = CalibratingState()
            
            _LOGGER.debug("Initialized concrete state handlers for all thermal states")
            
        except ImportError as e:
            _LOGGER.warning("Could not import state handlers, using defaults: %s", e)
            # Fallback to default handlers
            for state in ThermalState:
                self._state_handlers[state] = DefaultStateHandler()

    @property
    def current_state(self) -> ThermalState:
        """Get current thermal state."""
        return self._current_state

    @property
    def calibration_hour(self) -> int:
        """Get configured calibration hour."""
        from .const import CONF_CALIBRATION_HOUR, DEFAULT_CALIBRATION_HOUR
        return self._config.get(CONF_CALIBRATION_HOUR, DEFAULT_CALIBRATION_HOUR)

    def transition_to(self, new_state: ThermalState) -> None:
        """Transition to a new thermal state.
        
        Args:
            new_state: Target thermal state to transition to
            
        Raises:
            ValueError: If new_state is not a valid ThermalState
        """
        if not isinstance(new_state, ThermalState):
            raise ValueError(f"Invalid thermal state: {new_state}")
        
        if new_state == self._current_state:
            _LOGGER.debug("Already in state %s, no transition needed", new_state.value)
            return
        
        old_state = self._current_state
        _LOGGER.info("Transitioning thermal state: %s -> %s", old_state.value, new_state.value)
        
        # Call exit handler for current state
        try:
            self._state_handlers[old_state].on_exit(self)
        except Exception as e:
            _LOGGER.error("Error in exit handler for state %s: %s", old_state.value, e)
            raise
        
        # Update state and record timestamp
        self._current_state = new_state
        self._last_transition = datetime.now()
        
        # Call enter handler for new state
        try:
            self._state_handlers[new_state].on_enter(self)
        except Exception as e:
            _LOGGER.error("Error in enter handler for state %s: %s", new_state.value, e)
            raise
        
        # CRITICAL FIX: Trigger persistence after state change
        if self._persistence_callback:
            try:
                _LOGGER.debug("Triggering persistence after state transition to %s", new_state.value)
                self._persistence_callback()
            except Exception as e:
                _LOGGER.warning("Error triggering persistence after state transition: %s", e)
        
        _LOGGER.debug("Successfully transitioned to state %s", new_state.value)

    def get_operating_window(
        self,
        setpoint: float,
        outdoor_temp: float,
        hvac_mode: str
    ) -> Tuple[float, float]:
        """Calculate state-aware operating window for temperature control.
        
        Uses user preferences to calculate base comfort band, then applies
        state-specific adjustments through current state handler.
        
        Args:
            setpoint: Target temperature
            outdoor_temp: Current outdoor temperature
            hvac_mode: HVAC mode (cool/heat/auto)
            
        Returns:
            Tuple of (lower_bound, upper_bound) for operating window
        """
        # Store for other methods
        self._setpoint = setpoint
        self._last_hvac_mode = hvac_mode
        
        # Get base comfort band from preferences
        band_size = self._preferences.get_adjusted_band(outdoor_temp, hvac_mode)
        
        # Calculate base window centered on setpoint
        lower_bound = setpoint - band_size
        upper_bound = setpoint + band_size
        
        # State handlers could modify this window in the future
        # For now, return base calculation
        _LOGGER.debug(
            "Operating window for setpoint %.1f°C: [%.1f, %.1f] (band: %.1f)",
            setpoint, lower_bound, upper_bound, band_size
        )
        
        return (lower_bound, upper_bound)

    def should_ac_run(
        self,
        current: float,
        setpoint: float,
        window: Tuple[float, float]
    ) -> bool:
        """Determine if AC should run based on current temperature and operating window.
        
        Uses state-aware logic to determine if HVAC should activate based on
        current temperature relative to the operating window boundaries.
        
        Args:
            current: Current room temperature
            setpoint: Target temperature
            window: Operating window (lower_bound, upper_bound)
            
        Returns:
            True if AC should run, False otherwise
        """
        lower_bound, upper_bound = window
        
        # Determine if we're in cooling or heating mode based on hvac_mode first
        is_cooling = self._last_hvac_mode == "cool" or (
            self._last_hvac_mode == "auto" and current > setpoint
        )
        
        if is_cooling:
            # Cooling: run AC when temperature is at or above upper bound
            should_run = current >= upper_bound
            _LOGGER.debug(
                "Cooling decision: current=%.1f, upper_bound=%.1f, should_run=%s",
                current, upper_bound, should_run
            )
        else:
            # Heating: run AC when temperature is at or below lower bound
            should_run = current <= lower_bound
            _LOGGER.debug(
                "Heating decision: current=%.1f, lower_bound=%.1f, should_run=%s",
                current, lower_bound, should_run
            )
        
        return should_run

    def get_learning_target(
        self,
        current: float,
        window: Tuple[float, float]
    ) -> float:
        """Get learning target temperature for OffsetEngine training.
        
        Returns the appropriate boundary temperature that OffsetEngine should
        learn to correct towards, based on current thermal state and situation.
        
        Args:
            current: Current room temperature
            window: Operating window (lower_bound, upper_bound)
            
        Returns:
            Target temperature for learning (boundary or setpoint)
        """
        lower_bound, upper_bound = window
        
        # If within window, target is setpoint for maintenance
        if lower_bound <= current <= upper_bound:
            _LOGGER.debug(
                "Within window [%.1f, %.1f], targeting setpoint %.1f",
                lower_bound, upper_bound, self._setpoint
            )
            return self._setpoint
        
        # Determine which boundary to target based on temperature position
        if current > upper_bound:
            # Above window - cooling needed, target upper boundary
            target = upper_bound
            _LOGGER.debug(
                "Above window, current=%.1f, targeting upper boundary %.1f",
                current, target
            )
        else:
            # Below window - heating needed, target lower boundary
            target = lower_bound
            _LOGGER.debug(
                "Below window, current=%.1f, targeting lower boundary %.1f",
                current, target
            )
        
        return target

    # Diagnostic properties per §10.2.3
    @property
    def thermal_data_last_saved(self) -> Optional[datetime]:
        """Get timestamp of last thermal data save."""
        return self._thermal_data_last_saved

    @property
    def thermal_state_restored(self) -> bool:
        """Get whether thermal state was restored from disk."""
        return self._thermal_state_restored

    @property
    def corruption_recovery_count(self) -> int:
        """Get count of corrupted field recoveries."""
        return self._corruption_recovery_count

    # Persistence methods per §10.2.3
    def serialize(self) -> Dict[str, Any]:
        """Serialize thermal manager state for persistence.
        
        Returns complete thermal data structure per c_architecture.md §10.2.3
        including version, state, model, probe_history, confidence, and metadata.
        
        Returns:
            Dict containing serialized thermal data
        """
        # Increment saves counter each time we serialize
        self._saves_count += 1
        self._thermal_data_last_saved = datetime.now()
        
        # Get probe history from thermal model (max 5 entries)
        probe_history = []
        if hasattr(self._model, '_probe_history'):
            probes = list(self._model._probe_history)[-5:]  # Take most recent 5
            for probe in probes:
                probe_data = {
                    "tau_value": probe.tau_value,
                    "confidence": probe.confidence,
                    "duration": probe.duration,
                    "fit_quality": probe.fit_quality,
                    "aborted": probe.aborted,
                    "timestamp": datetime.now().isoformat()  # Current timestamp for serialization
                }
                probe_history.append(probe_data)

        return {
            "version": "1.0",
            "state": {
                "current_state": self._current_state.value,
                "last_transition": self._last_transition.isoformat() if self._last_transition else datetime.now().isoformat()
            },
            "model": {
                "tau_cooling": getattr(self._model, '_tau_cooling', 90.0),
                "tau_warming": getattr(self._model, '_tau_warming', 150.0), 
                "last_modified": (
                    self._model.tau_last_modified.isoformat() 
                    if hasattr(self._model, 'tau_last_modified') and self._model.tau_last_modified 
                    else datetime.now().isoformat()
                )
            },
            "probe_history": probe_history,
            "confidence": self._model.get_confidence() if hasattr(self._model, 'get_confidence') else 0.0,
            "metadata": {
                "saves_count": self._saves_count,
                "corruption_recoveries": self._corruption_recovery_count,
                "schema_version": "1.0"
            }
        }

    def restore(self, data: Dict[str, Any]) -> None:
        """Restore thermal manager state from persistence data.
        
        Performs field-level validation and recovery per c_architecture.md §10.4.1.
        Uses defaults for invalid fields and logs debug information for each recovery.
        
        Args:
            data: Dictionary containing thermal persistence data
        """
        self._thermal_state_restored = True
        recovery_count_start = self._corruption_recovery_count

        try:
            # Restore state section with validation
            if "state" in data:
                state_data = data["state"]
                
                # Validate and restore thermal state
                if "current_state" in state_data:
                    try:
                        state_value = state_data["current_state"]
                        # Try to find the enum by value
                        for state in ThermalState:
                            if state.value == state_value:
                                self._current_state = state
                                _LOGGER.debug("Restored thermal state: %s", state_value)
                                break
                        else:
                            # State value not found in enum
                            raise ValueError(f"Unknown thermal state: {state_value}")
                    except (ValueError, TypeError) as e:
                        _LOGGER.debug("Invalid thermal state '%s', using PRIMING: %s", 
                                    state_data.get("current_state"), e)
                        self._current_state = ThermalState.PRIMING
                        self._corruption_recovery_count += 1
                
                # Restore last transition timestamp
                if "last_transition" in state_data:
                    try:
                        timestamp_str = state_data["last_transition"]
                        self._last_transition = datetime.fromisoformat(timestamp_str)
                        _LOGGER.debug("Restored last transition: %s", timestamp_str)
                    except (ValueError, TypeError) as e:
                        _LOGGER.debug("Invalid last_transition timestamp, using current time: %s", e)
                        self._last_transition = datetime.now()
                        self._corruption_recovery_count += 1

            # Restore model section with validation
            if "model" in data:
                model_data = data["model"]
                
                # Validate and restore tau_cooling (1-1000 range)
                if "tau_cooling" in model_data:
                    tau_cooling = model_data["tau_cooling"]
                    if isinstance(tau_cooling, (int, float)) and 1 <= tau_cooling <= 1000:
                        if hasattr(self._model, '_tau_cooling'):
                            self._model._tau_cooling = float(tau_cooling)
                        _LOGGER.debug("Restored tau_cooling: %.1f", tau_cooling)
                    else:
                        _LOGGER.debug("Invalid tau_cooling %.1f, using default 90.0", tau_cooling)
                        if hasattr(self._model, '_tau_cooling'):
                            self._model._tau_cooling = 90.0
                        self._corruption_recovery_count += 1
                
                # Validate and restore tau_warming (1-1000 range)  
                if "tau_warming" in model_data:
                    tau_warming = model_data["tau_warming"]
                    if isinstance(tau_warming, (int, float)) and 1 <= tau_warming <= 1000:
                        if hasattr(self._model, '_tau_warming'):
                            self._model._tau_warming = float(tau_warming)
                        _LOGGER.debug("Restored tau_warming: %.1f", tau_warming)
                    else:
                        _LOGGER.debug("Invalid tau_warming %.1f, using default 150.0", tau_warming)
                        if hasattr(self._model, '_tau_warming'):
                            self._model._tau_warming = 150.0
                        self._corruption_recovery_count += 1
                
                # Restore tau_last_modified timestamp
                if "last_modified" in model_data:
                    try:
                        timestamp_str = model_data["last_modified"]
                        if hasattr(self._model, '_tau_last_modified'):
                            self._model._tau_last_modified = datetime.fromisoformat(timestamp_str)
                        _LOGGER.debug("Restored tau_last_modified: %s", timestamp_str)
                    except (ValueError, TypeError) as e:
                        _LOGGER.debug("Invalid tau_last_modified timestamp, using None: %s", e)
                        if hasattr(self._model, '_tau_last_modified'):
                            self._model._tau_last_modified = None
                        self._corruption_recovery_count += 1

            # Restore probe history with validation
            if "probe_history" in data and hasattr(self._model, '_probe_history'):
                probe_data = data["probe_history"]
                if isinstance(probe_data, list):
                    from collections import deque
                    from .thermal_models import ProbeResult
                    
                    restored_probes = deque(maxlen=5)
                    for probe_dict in probe_data[-5:]:  # Take most recent 5
                        try:
                            # Validate probe fields
                            if (isinstance(probe_dict, dict) and
                                "tau_value" in probe_dict and
                                "confidence" in probe_dict and
                                "duration" in probe_dict and
                                "fit_quality" in probe_dict and
                                "aborted" in probe_dict):
                                
                                # Validate ranges
                                duration = probe_dict["duration"]
                                confidence = probe_dict["confidence"] 
                                fit_quality = probe_dict["fit_quality"]
                                
                                if (isinstance(duration, (int, float)) and duration > 0 and
                                    isinstance(confidence, (int, float)) and 0.0 <= confidence <= 1.0 and
                                    isinstance(fit_quality, (int, float)) and 0.0 <= fit_quality <= 1.0):
                                    
                                    probe = ProbeResult(
                                        tau_value=float(probe_dict["tau_value"]),
                                        confidence=float(confidence),
                                        duration=int(duration),
                                        fit_quality=float(fit_quality),
                                        aborted=bool(probe_dict["aborted"])
                                    )
                                    restored_probes.append(probe)
                                    _LOGGER.debug("Restored probe: tau=%.1f, confidence=%.2f", 
                                                probe.tau_value, probe.confidence)
                                else:
                                    _LOGGER.debug("Invalid probe field ranges, discarding probe")
                                    self._corruption_recovery_count += 1
                            else:
                                _LOGGER.debug("Invalid probe structure, discarding probe")
                                self._corruption_recovery_count += 1
                        except Exception as e:
                            _LOGGER.debug("Error restoring probe, discarding: %s", e)
                            self._corruption_recovery_count += 1
                    
                    self._model._probe_history = restored_probes

            # Restore confidence (informational, validated by model)
            if "confidence" in data:
                confidence = data["confidence"]
                if not (isinstance(confidence, (int, float)) and 0.0 <= confidence <= 1.0):
                    _LOGGER.debug("Invalid confidence %.2f, model will calculate", confidence)
                    self._corruption_recovery_count += 1

            # Restore metadata
            if "metadata" in data:
                metadata = data["metadata"]
                if isinstance(metadata, dict):
                    # Restore saves count
                    if "saves_count" in metadata:
                        saves_count = metadata["saves_count"]
                        if isinstance(saves_count, int) and saves_count >= 0:
                            self._saves_count = saves_count
                        else:
                            _LOGGER.debug("Invalid saves_count, using 0")
                            self._corruption_recovery_count += 1
                    
                    # Restore historical corruption recoveries
                    if "corruption_recoveries" in metadata:
                        historical_recoveries = metadata["corruption_recoveries"]
                        if isinstance(historical_recoveries, int) and historical_recoveries >= 0:
                            # Add historical to current session recoveries
                            self._corruption_recovery_count += historical_recoveries
                        else:
                            _LOGGER.debug("Invalid corruption_recoveries, ignoring")

        except Exception as e:
            _LOGGER.error("Error during thermal data restoration: %s", e)
            # Reset to safe defaults on critical error
            self._current_state = ThermalState.PRIMING
            self._corruption_recovery_count += 1

        # Log summary if any recoveries occurred
        recoveries_this_session = self._corruption_recovery_count - recovery_count_start
        if recoveries_this_session > 0:
            _LOGGER.warning("Thermal data restoration completed with %d field recoveries", 
                          recoveries_this_session)

    def update_state(self, current_temp: Optional[float] = None, outdoor_temp: Optional[float] = None, hvac_mode: Optional[str] = None) -> None:
        """Update thermal state and check for transitions.
        
        This method should be called periodically by the coordinator to:
        1. Execute current state handler logic
        2. Check for calibration hour transitions regardless of current state
        3. Handle state transitions returned by handlers
        
        Args:
            current_temp: Current room temperature
            outdoor_temp: Current outdoor temperature 
            hvac_mode: Current HVAC mode (cool/heat/auto)
        
        Fixes the critical bug where thermal states never transition because
        no periodic check was happening.
        """
        _LOGGER.debug("ThermalManager.update_state() called - current state: %s", self._current_state.value)
        
        try:
            # Log current conditions for debugging
            current_time = datetime.now()
            calibration_hour = self.calibration_hour
            _LOGGER.debug("Thermal state check - hour: %d, calibration_hour: %d, state: %s, last_transition: %s",
                          current_time.hour, calibration_hour, self._current_state.value, 
                          self._last_transition.isoformat() if self._last_transition else "Never")
            
            # First check if it's calibration hour - this takes priority over other transitions
            if current_time.hour == calibration_hour:
                # Transition to CALIBRATING if we're in calibration hour
                # This allows calibration from any state
                if self._current_state != ThermalState.CALIBRATING:
                    _LOGGER.info("Calibration hour reached (%d AM), transitioning from %s to CALIBRATING",
                               calibration_hour, self._current_state.value)
                    self.transition_to(ThermalState.CALIBRATING)
                    return
                else:
                    _LOGGER.debug("Already in CALIBRATING state during calibration hour")
            else:
                _LOGGER.debug("Not calibration hour (current: %d, calibration: %d)", current_time.hour, calibration_hour)
            
            # Execute current state handler logic
            current_handler = self._state_handlers.get(self._current_state)
            if current_handler:
                try:
                    _LOGGER.debug("Executing state handler for %s", self._current_state.value)
                    
                    # Calculate operating window if we have the necessary parameters
                    operating_window = None
                    if current_temp is not None and outdoor_temp is not None and hvac_mode is not None:
                        # Use current room temperature as setpoint approximation
                        setpoint = current_temp
                        operating_window = self.get_operating_window(setpoint, outdoor_temp, hvac_mode)
                        _LOGGER.debug("Calculated operating window: %s for temp=%.1f", operating_window, current_temp)
                    else:
                        _LOGGER.debug("Missing parameters for operating window calculation: temp=%s, outdoor=%s, hvac_mode=%s",
                                    current_temp, outdoor_temp, hvac_mode)
                    
                    # Call state handler with temperature and operating window parameters
                    next_state = current_handler.execute(self, current_temp, operating_window)
                    if next_state is not None and next_state != self._current_state:
                        _LOGGER.info("Thermal state transition triggered: %s -> %s", 
                                     self._current_state.value, next_state.value)
                        self.transition_to(next_state)
                    else:
                        _LOGGER.debug("No thermal state transition needed, staying in %s", self._current_state.value)
                except Exception as e:
                    _LOGGER.error("Error executing state handler for %s: %s", 
                                self._current_state.value, e)
            else:
                _LOGGER.warning("No state handler found for state %s", self._current_state.value)
                
        except Exception as e:
            _LOGGER.error("Error in thermal state update: %s", e)

    def reset(self) -> None:
        """Reset thermal manager to default state.
        
        Resets to PRIMING state with default tau values and clears probe history
        per c_architecture.md §10.2.3. Used by thermal reset button.
        """
        _LOGGER.info("Resetting thermal manager to defaults")
        
        # Reset state to PRIMING (safest default)
        self._current_state = ThermalState.PRIMING
        self._last_transition = datetime.now()
        
        # Reset thermal model to defaults
        if hasattr(self._model, '_tau_cooling'):
            self._model._tau_cooling = 90.0
        if hasattr(self._model, '_tau_warming'):
            self._model._tau_warming = 150.0
        if hasattr(self._model, '_tau_last_modified'):
            self._model._tau_last_modified = None
        
        # Clear probe history
        if hasattr(self._model, '_probe_history'):
            from collections import deque
            self._model._probe_history = deque(maxlen=5)
        
        _LOGGER.debug("Thermal manager reset complete: state=%s, tau_cooling=90.0, tau_warming=150.0",
                     self._current_state.value)