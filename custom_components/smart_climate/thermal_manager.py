"""ABOUTME: Thermal efficiency state machine orchestrator for Smart Climate Control.
Coordinates thermal states, operating window calculations, and AC control decisions."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Tuple, Optional, Any, Callable
from datetime import datetime, timedelta, timezone, time
from homeassistant.core import HomeAssistant

from .thermal_models import ThermalState, ThermalConstants
from .thermal_preferences import UserPreferences
from .thermal_model import PassiveThermalModel

_LOGGER = logging.getLogger(__name__)

# Minimum time between automatic probing triggers (24 hours)
MIN_PROBE_INTERVAL = timedelta(hours=24)


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
        persistence_callback: Optional[Callable[[], None]] = None,
        probe_scheduler: Optional['ProbeScheduler'] = None
    ):
        """Initialize ThermalManager.
        
        Args:
            hass: Home Assistant instance
            thermal_model: PassiveThermalModel instance
            preferences: UserPreferences instance
            config: Optional configuration dictionary
            persistence_callback: Optional callback for data persistence
            probe_scheduler: Optional ProbeScheduler for intelligent probe scheduling
        """
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
        self._last_probe_time: Optional[datetime] = None  # Track when last probe occurred
        
        # ProbeScheduler integration for intelligent probe scheduling (v1.5.3-beta)
        self.probe_scheduler = probe_scheduler
        
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
        
        # Initialize stability detector for opportunistic calibration
        from .thermal_stability import StabilityDetector
        self.stability_detector = StabilityDetector(
            idle_threshold_minutes=self._config.get('calibration_idle_minutes', 30),
            drift_threshold=self._config.get('calibration_drift_threshold', 0.3),
            passive_min_drift_minutes=self._config.get('passive_min_drift_minutes', 15)
        )
        
        # Initialize state handlers registry
        self._initialize_state_handlers()
        
        _LOGGER.debug("ThermalManager initialized in %s state with probe_scheduler=%s", 
                     self._current_state.value, "enabled" if self.probe_scheduler else "disabled")

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


    def _get_current_conditions(self) -> tuple[str, Optional[float]]:
        """Get current AC state and temperature for stability detection.
        
        Returns:
            Tuple of (ac_state, temperature) where ac_state is one of:
            "cooling", "heating", "idle", "off"
        """
        try:
            # This would normally get the actual AC state from the climate entity
            # For now, return a simple idle state as fallback
            # TODO: Implement proper AC state detection from climate entity
            ac_state = "idle"  # Placeholder implementation
            temperature = None  # Will be provided by coordinator
            
            return ac_state, temperature
        except Exception as exc:
            _LOGGER.debug("Error getting current conditions: %s", exc)
            return "idle", None

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
        
        # Record when probing occurs for minimum interval tracking
        if new_state == ThermalState.PROBING:
            self._last_probe_time = self._last_transition
        
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

    def force_calibration(self) -> None:
        """Force immediate transition to CALIBRATING state.
        
        This method allows manual triggering of calibration regardless of
        normal transition conditions. Blocked during PROBING state to
        prevent conflicts.
        """
        if self._current_state == ThermalState.PROBING:
            _LOGGER.warning("Cannot force calibration during probing")
            return
        
        if self._current_state != ThermalState.CALIBRATING:
            _LOGGER.info("Manual calibration triggered from %s state", self._current_state.value)
            self.transition_to(ThermalState.CALIBRATING)
        else:
            _LOGGER.debug("Already in CALIBRATING state, no transition needed")

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
    def _serialize_probe_scheduler_config(self) -> Dict[str, Any]:
        """Serialize probe scheduler configuration.
        
        Returns probe scheduler configuration for persistence including
        learning profile and advanced settings per architecture Section 20.9.
        
        Returns:
            Dict containing probe scheduler configuration
        """
        if not hasattr(self, 'probe_scheduler') or not self.probe_scheduler:
            return {"enabled": False}
        
        try:
            # Get learning profile
            profile_value = self.probe_scheduler._learning_profile.value
        except (AttributeError, ValueError):
            profile_value = "balanced"  # Default fallback
        
        config = {
            "enabled": True,
            "learning_profile": profile_value
        }
        
        # Serialize advanced settings if available
        if hasattr(self.probe_scheduler, '_profile_config') and self.probe_scheduler._profile_config:
            try:
                advanced_config = self.probe_scheduler._profile_config
                config["advanced_settings"] = {
                    "min_probe_interval_hours": getattr(advanced_config, 'min_probe_interval_hours', 12),
                    "max_probe_interval_days": getattr(advanced_config, 'max_probe_interval_days', 7),
                    "information_gain_threshold": getattr(advanced_config, 'information_gain_threshold', 0.5),
                    "temperature_bins": getattr(advanced_config, 'temperature_bins', [-10, 0, 10, 20, 30]),
                    "presence_override_enabled": getattr(advanced_config, 'presence_override_enabled', False),
                    "outdoor_temp_change_threshold": getattr(advanced_config, 'outdoor_temp_change_threshold', 5.0),
                    "min_probe_duration_minutes": getattr(advanced_config, 'min_probe_duration_minutes', 15)
                }
            except Exception as e:
                _LOGGER.debug("Could not serialize advanced settings, using defaults: %s", e)
                # Include minimal advanced settings as fallback
                config["advanced_settings"] = {}
        
        return config

    def serialize(self) -> Dict[str, Any]:
        """Serialize thermal manager state for persistence.
        
        Returns complete thermal data structure per c_architecture.md §10.2.3
        including version, state, model, probe_history, confidence, metadata,
        and probe_scheduler_config (v2.1 enhancement).
        
        Returns:
            Dict containing serialized thermal data
        """
        # Increment saves counter each time we serialize
        self._saves_count += 1
        self._thermal_data_last_saved = datetime.now()
        
        # Get probe history from thermal model (v1.5.3: up to 75 entries)
        probe_history = []
        if hasattr(self._model, '_probe_history'):
            from .const import MAX_PROBE_HISTORY_SIZE
            probes = list(self._model._probe_history)[-MAX_PROBE_HISTORY_SIZE:]  # Take most recent
            for probe in probes:
                probe_data = {
                    "tau_value": probe.tau_value,
                    "confidence": probe.confidence,
                    "duration": probe.duration,
                    "fit_quality": probe.fit_quality,
                    "aborted": probe.aborted,
                    "timestamp": probe.timestamp.isoformat(),  # Read existing timestamp
                    "outdoor_temp": probe.outdoor_temp  # v1.5.3 enhancement - None for legacy probes
                }
                probe_history.append(probe_data)

        # Serialize stability detector state if available
        stability_data = None
        if hasattr(self, 'stability_detector') and self.stability_detector:
            stability_data = {
                "idle_threshold_minutes": int(self.stability_detector._idle_threshold.total_seconds() // 60),
                "drift_threshold": self.stability_detector._drift_threshold,
                "last_ac_state": getattr(self.stability_detector, '_last_ac_state', None),
                "temperature_history_count": len(self.stability_detector._temperature_history)
            }

        # Get enhanced priming state data if in PRIMING state
        priming_data = None
        if self._current_state == ThermalState.PRIMING:
            handler = self._state_handlers.get(ThermalState.PRIMING)
            if handler:
                priming_data = {
                    "start_time": handler._start_time.isoformat() if hasattr(handler, '_start_time') and handler._start_time else None,
                    "current_phase": getattr(handler, '_current_phase', 'passive'),
                    "controlled_drift_state": getattr(handler, '_controlled_drift_state', 'inactive'),
                    "controlled_drift_attempted": getattr(handler, '_controlled_drift_attempted', False),
                    "controlled_drift_start_time": (
                        handler._controlled_drift_start_time.isoformat() 
                        if hasattr(handler, '_controlled_drift_start_time') and handler._controlled_drift_start_time 
                        else None
                    ),
                    "controlled_drift_start_temp": getattr(handler, '_controlled_drift_start_temp', None)
                }
                _LOGGER.debug("Serializing enhanced priming data: phase=%s, drift_state=%s, drift_attempted=%s",
                            priming_data['current_phase'], priming_data['controlled_drift_state'], priming_data['controlled_drift_attempted'])

        return {
            "version": "2.1",  # Updated for probe scheduler support
            "state": {
                "current_state": self._current_state.value,
                "last_transition": self._last_transition.isoformat() if self._last_transition else datetime.now().isoformat(),
                "last_probe_time": self._last_probe_time.isoformat() if self._last_probe_time else None,
                "priming_data": priming_data  # Enhanced priming state data
            },
            "model": {
                "tau_cooling": getattr(self._model, '_tau_cooling', 90.0),
                "tau_warming": getattr(self._model, '_tau_warming', 150.0), 
                "last_modified": (
                    self._model.tau_last_modified.isoformat() 
                    if hasattr(self._model, 'tau_last_modified') and self._model.tau_last_modified and hasattr(self._model.tau_last_modified, 'isoformat')
                    else datetime.now().isoformat()
                )
            },
            "probe_history": probe_history,
            "confidence": self._model.get_confidence() if hasattr(self._model, 'get_confidence') else 0.0,
            "stability_detector": stability_data,
            "probe_scheduler_config": self._serialize_probe_scheduler_config(),  # NEW - v2.1
            "metadata": {
                "saves_count": self._saves_count,
                "corruption_recoveries": self._corruption_recovery_count,
                "schema_version": "2.1"  # Updated schema version
            }
        }

    def _restore_probe_scheduler_config(self, config_data: Dict[str, Any]) -> None:
        """Restore probe scheduler configuration.
        
        CRITICAL FIX: Prioritize live configuration over persistence data.
        When user changes ProbeScheduler settings via options flow,
        use current config_entry.options instead of stale persistence data.
        
        Args:
            config_data: Dictionary containing probe scheduler configuration
        """
        # CRITICAL: Check live configuration first (options flow takes priority)
        # The probe_scheduler should already be created if enabled in current config
        if not hasattr(self, 'probe_scheduler') or not self.probe_scheduler:
            _LOGGER.debug("No probe scheduler available - live config has it disabled or failed to create")
            return
            
        # If we have a probe_scheduler, it means live config enabled it
        # Don't let stale persistence data disable it
        _LOGGER.debug("Probe scheduler exists - applying stored configuration (not enabled/disabled state)")
            
        try:
            # Restore learning profile (if valid)
            profile_str = config_data.get("learning_profile", "balanced")
            try:
                from .probe_scheduler import LearningProfile
                profile = LearningProfile(profile_str)
                if hasattr(self.probe_scheduler, '_update_profile'):
                    self.probe_scheduler._update_profile(profile)
                    _LOGGER.debug("Restored probe scheduler learning profile: %s", profile_str)
                else:
                    # Fallback: set profile directly
                    self.probe_scheduler._learning_profile = profile
            except (ValueError, AttributeError) as e:
                _LOGGER.debug("Invalid learning profile '%s', keeping current: %s", profile_str, e)
                # Keep current profile - don't break on invalid stored profile
            
            # Restore advanced settings if present (but not enabled/disabled state)
            if "advanced_settings" in config_data:
                try:
                    settings_data = config_data["advanced_settings"]
                    if isinstance(settings_data, dict):
                        from .probe_scheduler import AdvancedSettings
                        
                        # Parse time strings safely
                        def parse_time(time_str, default_time):
                            try:
                                if isinstance(time_str, str):
                                    # Parse ISO time format (HH:MM:SS)
                                    time_parts = time_str.split(':')
                                    if len(time_parts) >= 2:
                                        hour = int(time_parts[0])
                                        minute = int(time_parts[1])
                                        second = int(time_parts[2]) if len(time_parts) > 2 else 0
                                        return time(hour, minute, second)
                                return default_time
                            except (ValueError, IndexError):
                                return default_time
                        
                        # Build advanced settings with validation
                        settings = AdvancedSettings(
                            min_probe_interval_hours=int(settings_data.get("min_probe_interval_hours", 12)),
                            max_probe_interval_days=int(settings_data.get("max_probe_interval_days", 7)),
                            information_gain_threshold=float(settings_data.get("information_gain_threshold", 0.5)),
                            temperature_bins=list(settings_data.get("temperature_bins", [-10, 0, 10, 20, 30])),
                            presence_override_enabled=bool(settings_data.get("presence_override_enabled", False)),
                            outdoor_temp_change_threshold=float(settings_data.get("outdoor_temp_change_threshold", 5.0)),
                            min_probe_duration_minutes=int(settings_data.get("min_probe_duration_minutes", 15))
                        )
                        
                        if hasattr(self.probe_scheduler, 'apply_advanced_settings'):
                            self.probe_scheduler.apply_advanced_settings(settings)
                            _LOGGER.debug("Restored probe scheduler advanced settings")
                        else:
                            # Fallback: set profile config directly
                            self.probe_scheduler._profile_config = settings
                        
                except (ValueError, TypeError, AttributeError) as e:
                    _LOGGER.debug("Could not restore advanced settings, keeping current: %s", e)
                    self._corruption_recovery_count += 1
                    
        except Exception as e:
            _LOGGER.debug("Error restoring probe scheduler configuration: %s", e)
            self._corruption_recovery_count += 1

    def restore(self, data: Dict[str, Any]) -> None:
        """Restore thermal manager state from persistence data.
        
        Performs field-level validation and recovery per c_architecture.md §10.4.1.
        Uses defaults for invalid fields and logs debug information for each recovery.
        Supports schema migration from v2.0 to v2.1 for probe scheduler support.
        
        Args:
            data: Dictionary containing thermal persistence data
        """
        self._thermal_state_restored = True
        recovery_count_start = self._corruption_recovery_count

        try:
            # Handle schema migration - detect data version
            data_version = data.get("version", "1.0")
            schema_version = data.get("metadata", {}).get("schema_version", data_version)
            _LOGGER.debug("Restoring thermal data from schema version: %s", schema_version)

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
                
                # Restore last probe time if present
                if "last_probe_time" in state_data:
                    try:
                        probe_time_str = state_data["last_probe_time"]
                        if probe_time_str:  # Check it's not None
                            self._last_probe_time = datetime.fromisoformat(probe_time_str)
                            _LOGGER.debug("Restored last probe time: %s", probe_time_str)
                        else:
                            self._last_probe_time = None
                            _LOGGER.debug("No previous probe time found")
                    except (ValueError, TypeError) as e:
                        _LOGGER.debug("Invalid last_probe_time timestamp, clearing probe history: %s", e)
                        self._last_probe_time = None
                        self._corruption_recovery_count += 1
                
                # Restore enhanced priming data if present and in PRIMING state
                if "priming_data" in state_data and self._current_state == ThermalState.PRIMING:
                    try:
                        priming_data = state_data["priming_data"]
                        if priming_data and isinstance(priming_data, dict):
                            handler = self._state_handlers.get(ThermalState.PRIMING)
                            if handler:
                                # Restore start time
                                if "start_time" in priming_data and priming_data["start_time"]:
                                    handler._start_time = datetime.fromisoformat(priming_data["start_time"])
                                    _LOGGER.debug("Restored priming start time: %s", priming_data["start_time"])
                                
                                # Restore current phase
                                phase = priming_data.get("current_phase", "passive")
                                if phase in ["passive", "active"]:
                                    handler._current_phase = phase
                                    _LOGGER.debug("Restored priming phase: %s", phase)
                                
                                # Restore controlled drift state
                                drift_state = priming_data.get("controlled_drift_state", "inactive")
                                if drift_state in ["inactive", "requested", "monitoring", "analyzing"]:
                                    handler._controlled_drift_state = drift_state
                                    _LOGGER.debug("Restored controlled drift state: %s", drift_state)
                                
                                # Restore controlled drift attempted flag
                                handler._controlled_drift_attempted = priming_data.get("controlled_drift_attempted", False)
                                _LOGGER.debug("Restored controlled drift attempted: %s", handler._controlled_drift_attempted)
                                
                                # Restore controlled drift start time
                                if "controlled_drift_start_time" in priming_data and priming_data["controlled_drift_start_time"]:
                                    handler._controlled_drift_start_time = datetime.fromisoformat(priming_data["controlled_drift_start_time"])
                                    _LOGGER.debug("Restored controlled drift start time: %s", priming_data["controlled_drift_start_time"])
                                
                                # Restore controlled drift start temperature
                                handler._controlled_drift_start_temp = priming_data.get("controlled_drift_start_temp")
                                if handler._controlled_drift_start_temp is not None:
                                    _LOGGER.debug("Restored controlled drift start temp: %.2f", handler._controlled_drift_start_temp)
                                
                                _LOGGER.info("Restored enhanced priming state: phase=%s, drift_state=%s", 
                                           handler._current_phase, handler._controlled_drift_state)
                    except (ValueError, TypeError, AttributeError) as e:
                        _LOGGER.debug("Could not restore enhanced priming data: %s", e)
                        self._corruption_recovery_count += 1
                
                # Fallback: restore legacy priming_start_time format
                elif "priming_start_time" in state_data and self._current_state == ThermalState.PRIMING:
                    try:
                        priming_time_str = state_data["priming_start_time"]
                        if priming_time_str:  # Check it's not None
                            priming_start = datetime.fromisoformat(priming_time_str)
                            # Set the start time in the PrimingState handler
                            handler = self._state_handlers.get(ThermalState.PRIMING)
                            if handler:
                                handler._start_time = priming_start
                                _LOGGER.info("Restored legacy priming start time: %s", priming_time_str)
                    except (ValueError, TypeError, AttributeError) as e:
                        _LOGGER.debug("Could not restore legacy priming start time: %s", e)
                        self._corruption_recovery_count += 1

            # Restore model section with validation
            if "model" in data:
                model_data = data["model"]
                
                # Validate and restore tau_cooling (60-86400 seconds range)
                if "tau_cooling" in model_data:
                    tau_cooling = model_data["tau_cooling"]
                    if isinstance(tau_cooling, (int, float)) and 60 <= tau_cooling <= 86400:
                        if hasattr(self._model, '_tau_cooling'):
                            self._model._tau_cooling = float(tau_cooling)
                        _LOGGER.debug("Restored tau_cooling: %.1f", tau_cooling)
                    else:
                        _LOGGER.debug("Invalid tau_cooling %.1f seconds (range: 60-86400s), using default 90.0", tau_cooling)
                        if hasattr(self._model, '_tau_cooling'):
                            self._model._tau_cooling = 90.0
                        self._corruption_recovery_count += 1
                
                # Validate and restore tau_warming (60-86400 seconds range)  
                if "tau_warming" in model_data:
                    tau_warming = model_data["tau_warming"]
                    if isinstance(tau_warming, (int, float)) and 60 <= tau_warming <= 86400:
                        if hasattr(self._model, '_tau_warming'):
                            self._model._tau_warming = float(tau_warming)
                        _LOGGER.debug("Restored tau_warming: %.1f", tau_warming)
                    else:
                        _LOGGER.debug("Invalid tau_warming %.1f seconds (range: 60-86400s), using default 150.0", tau_warming)
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

            # Restore probe history with validation (v1.5.3: up to 75 probes)
            if "probe_history" in data and hasattr(self._model, '_probe_history'):
                probe_data = data["probe_history"]
                if isinstance(probe_data, list):
                    from collections import deque
                    from .thermal_model import ProbeResult
                    from .const import MAX_PROBE_HISTORY_SIZE
                    
                    restored_probes = deque(maxlen=MAX_PROBE_HISTORY_SIZE)
                    for probe_dict in probe_data[-MAX_PROBE_HISTORY_SIZE:]:  # Take most recent based on constant
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
                                    
                                    # Parse timestamp or use fallback for legacy data
                                    timestamp_str = probe_dict.get("timestamp")
                                    if timestamp_str:
                                        try:
                                            timestamp = datetime.fromisoformat(timestamp_str)
                                        except (ValueError, TypeError) as e:
                                            _LOGGER.debug("Invalid timestamp '%s', using current time: %s", timestamp_str, e)
                                            timestamp = datetime.now(timezone.utc)
                                            self._corruption_recovery_count += 1
                                    else:
                                        timestamp = datetime.now(timezone.utc)  # Legacy fallback
                                    
                                    # Handle outdoor_temp - v1.5.3 enhancement
                                    outdoor_temp = None
                                    if "outdoor_temp" in probe_dict:
                                        outdoor_temp_value = probe_dict["outdoor_temp"]
                                        if isinstance(outdoor_temp_value, (int, float)):
                                            outdoor_temp = float(outdoor_temp_value)
                                        elif outdoor_temp_value is not None:
                                            _LOGGER.debug("Invalid outdoor_temp type: %s", type(outdoor_temp_value))
                                    # If no outdoor_temp field, leave as None (legacy v1.5.2 behavior)
                                    
                                    probe = ProbeResult(
                                        tau_value=float(probe_dict["tau_value"]),
                                        confidence=float(confidence),
                                        duration=int(duration),
                                        fit_quality=float(fit_quality),
                                        aborted=bool(probe_dict["aborted"]),
                                        timestamp=timestamp,  # Pass the restored timestamp
                                        outdoor_temp=outdoor_temp  # v1.5.3 enhancement
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
                    
                    # Replace probe history with restored probes (proper restoration behavior)
                    if restored_probes:
                        self._model._probe_history.clear()  # Clear existing history for proper restore
                        for probe in restored_probes:
                            self._model._probe_history.append(probe)
                        _LOGGER.debug("Restored probe history with %d probes", 
                                     len(restored_probes))
                    else:
                        # Clear history if no valid probes to restore
                        self._model._probe_history.clear()
                        _LOGGER.debug("No valid probes to restore, cleared history")

            # Restore confidence (informational, validated by model)
            if "confidence" in data:
                confidence = data["confidence"]
                if not (isinstance(confidence, (int, float)) and 0.0 <= confidence <= 1.0):
                    _LOGGER.debug("Invalid confidence %.2f, model will calculate", confidence)
                    self._corruption_recovery_count += 1

            # Restore probe scheduler configuration (v2.1+ feature)
            if "probe_scheduler_config" in data:
                self._restore_probe_scheduler_config(data["probe_scheduler_config"])
            elif schema_version in ["2.0", "1.0"]:
                # Backward compatibility: missing probe_scheduler_config is expected in older versions
                _LOGGER.debug("No probe scheduler config in schema version %s (expected)", schema_version)

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
        2. Check for probe scheduling from stable states (DRIFTING/CORRECTING)
        3. Handle state transitions returned by handlers
        4. Perform passive learning during PRIMING state
        
        Args:
            current_temp: Current room temperature
            outdoor_temp: Current outdoor temperature 
            hvac_mode: Current HVAC mode (cool/heat/auto)
        
        Enhanced with ProbeScheduler integration per architecture Section 20.11.
        """
        _LOGGER.debug("ThermalManager.update_state() called - current state: %s", self._current_state.value)
        
        try:
            # Log current conditions for debugging
            current_time = datetime.now()
            _LOGGER.debug("Thermal state check - state: %s, last_transition: %s",
                          self._current_state.value, 
                          self._last_transition.isoformat() if self._last_transition else "Never")
            
            # Update stability detector with current conditions
            if hasattr(self, 'stability_detector') and self.stability_detector:
                ac_state, temperature = self._get_current_conditions()
                if ac_state and temperature is not None:
                    self.stability_detector.update(ac_state, temperature)
                    _LOGGER.debug("Updated stability detector: ac_state=%s, temp=%.1f°C", ac_state, temperature)
            
            # Execute current state handler logic (for ALL states including PRIMING)
            current_handler = self._state_handlers.get(self._current_state)
            handler_next_state = None
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
                    handler_next_state = current_handler.execute(self, current_temp, operating_window)
                    if handler_next_state is not None and handler_next_state != self._current_state:
                        _LOGGER.info("State handler transition triggered: %s -> %s", 
                                     self._current_state.value, handler_next_state.value)
                        self.transition_to(handler_next_state)
                        return  # Handler transition takes priority, exit early
                    else:
                        _LOGGER.debug("State handler requires no transition, staying in %s", self._current_state.value)
                except Exception as e:
                    _LOGGER.error("Error executing state handler for %s: %s", 
                                self._current_state.value, e)
            else:
                _LOGGER.warning("No state handler found for state %s", self._current_state.value)
            
            # Phase 1: Passive learning during PRIMING (AFTER handler execution)
            if self._current_state == ThermalState.PRIMING:
                self._handle_passive_learning()
            

            
            # Phase 2: Opportunistic probing from stable states (only if handler didn't transition)
            if (handler_next_state is None and 
                self._current_state in [ThermalState.DRIFTING, ThermalState.CORRECTING] and
                self.probe_scheduler is not None):
                
                try:
                    _LOGGER.debug("Checking probe scheduler for opportunistic probing from %s state", 
                                 self._current_state.value)
                    
                    if self.probe_scheduler.should_probe_now():
                        _LOGGER.info("ProbeScheduler approved opportunistic probing from %s state", 
                                   self._current_state.value)
                        self.transition_to(ThermalState.PROBING)
                        return
                    else:
                        _LOGGER.debug("ProbeScheduler declined probing opportunity from %s state", 
                                    self._current_state.value)
                except Exception as e:
                    _LOGGER.error("Error checking probe scheduler: %s", e)
                    # Continue gracefully - probe scheduling failure should not break state machine
            elif self.probe_scheduler is None:
                _LOGGER.debug("No probe scheduler configured, skipping opportunistic probing")
                
        except Exception as e:
            _LOGGER.error("Error in thermal state update: %s", e)

    def reset(self) -> None:
        """Reset thermal manager to default state.
        
        Resets to PRIMING state with default tau values and clears probe history
        per c_architecture.md §10.2.3. Used by thermal reset button.
        """
        _LOGGER.info("Resetting thermal manager to defaults")
        
        # Reset state to PRIMING using proper transition to initialize handler
        self.transition_to(ThermalState.PRIMING)
        
        # Reset thermal model to defaults
        if hasattr(self._model, '_tau_cooling'):
            self._model._tau_cooling = 90.0
        if hasattr(self._model, '_tau_warming'):
            self._model._tau_warming = 150.0
        if hasattr(self._model, '_tau_last_modified'):
            self._model._tau_last_modified = None
        
        # Clear probe history (v1.5.3: 75-probe capacity)
        if hasattr(self._model, '_probe_history'):
            from collections import deque
            from .const import MAX_PROBE_HISTORY_SIZE
            self._model._probe_history = deque(maxlen=MAX_PROBE_HISTORY_SIZE)
        
        _LOGGER.debug("Thermal manager reset complete: state=%s, tau_cooling=90.0, tau_warming=150.0",
                     self._current_state.value)

    def _handle_passive_learning(self) -> None:
        """Handle passive learning during PRIMING state.
        
        Orchestrates passive learning by:
        1. Checking for natural drift events via stability detector
        2. Analyzing drift data using thermal_utils.analyze_drift_data
        3. Accepting results with confidence > configured threshold
        4. Updating thermal model via existing update_tau method
        
        Uses configuration parameters:
        - passive_confidence_threshold: Minimum confidence to accept results (default 0.3)
        - passive_min_drift_minutes: Minimum drift duration (default 15)
        """
        try:
            # Check for natural drift event
            if not hasattr(self, 'stability_detector') or not self.stability_detector:
                _LOGGER.debug("No stability detector available for passive learning")
                return
                
            drift_data = self.stability_detector.find_natural_drift_event()
            if not drift_data:
                _LOGGER.debug("No natural drift event found for passive learning")
                return
                
            _LOGGER.debug("Found drift event with %d data points for passive analysis", len(drift_data))
            
            # Analyze drift data using thermal_utils
            from .thermal_utils import analyze_drift_data
            probe_result = analyze_drift_data(drift_data, is_passive=True)
            
            if not probe_result:
                _LOGGER.debug("Passive learning analysis failed - insufficient data or curve fitting error")
                return
                
            # Check confidence threshold from config
            confidence_threshold = self._config.get('passive_confidence_threshold', 0.3)
            if probe_result.confidence < confidence_threshold:
                _LOGGER.debug("Passive learning rejected: confidence %.3f < threshold %.3f", 
                             probe_result.confidence, confidence_threshold)
                return
                
            # Determine cooling/heating mode for update_tau
            is_cooling = self._last_hvac_mode == "cool" or (
                self._last_hvac_mode == "auto" and hasattr(self, '_setpoint') and 
                hasattr(self, 'current_temp') and getattr(self, 'current_temp', 0) > self._setpoint
            )
            
            # Update thermal model with passive learning result
            self._model.update_tau(probe_result, is_cooling)
            
            _LOGGER.info("Passive learning successful: tau=%.1f, confidence=%.3f, duration=%ds, fit_quality=%.3f",
                        probe_result.tau_value, probe_result.confidence, 
                        probe_result.duration, probe_result.fit_quality)
                        
        except Exception as e:
            _LOGGER.error("Error in passive learning handler: %s", e)

    def update_temperature(self, temperature: float, ac_state: str) -> None:
        """Update stability detector with current temperature and AC state.
        
        Args:
            temperature: Current room temperature
            ac_state: Current AC state (cooling/heating/idle/off)
        """
        if hasattr(self, 'stability_detector') and self.stability_detector:
            self.stability_detector.update(ac_state, temperature)
            _LOGGER.debug("Updated stability detector: temp=%.1f°C, state=%s", temperature, ac_state)

    def force_calibration(self) -> None:
        """Force immediate transition to CALIBRATING state."""
        if self._current_state == ThermalState.PROBING:
            _LOGGER.warning("Cannot force calibration during probing")
            return
        if self._current_state != ThermalState.CALIBRATING:
            self.transition_to(ThermalState.CALIBRATING)
            _LOGGER.info("Manual calibration triggered from %s state", self._current_state)

    def force_probing(self) -> None:
        """Force immediate transition to PROBING state."""
        if self._current_state == ThermalState.PROBING:
            _LOGGER.info("Already in PROBING state")
            return
        self.transition_to(ThermalState.PROBING)
        _LOGGER.info("Manual probing triggered from %s state", self._current_state)

    def can_auto_probe(self) -> bool:
        """Check if sufficient time has passed since last probe for automatic probing.
        
        Returns:
            True if minimum probe interval has passed, False otherwise
        """
        if self._last_probe_time is None:
            # Never probed before, allow probing
            return True
        
        time_since_last_probe = datetime.now() - self._last_probe_time
        can_probe = time_since_last_probe >= MIN_PROBE_INTERVAL
        
        if not can_probe:
            remaining = MIN_PROBE_INTERVAL - time_since_last_probe
            hours_remaining = remaining.total_seconds() / 3600
            _LOGGER.debug("Cannot auto-probe yet, %.1f hours remaining until next probe allowed", hours_remaining)
        
        return can_probe