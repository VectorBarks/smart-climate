"""ABOUTME: Thermal efficiency state machine orchestrator for Smart Climate Control.
Coordinates thermal states, operating window calculations, and AC control decisions."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Tuple, Optional
from homeassistant.core import HomeAssistant

from .thermal_models import ThermalState
from .thermal_preferences import UserPreferences
from .thermal_model import PassiveThermalModel

_LOGGER = logging.getLogger(__name__)


class StateHandler(ABC):
    """Abstract base class for thermal state handlers.
    
    Each thermal state has a handler that implements state-specific behavior
    for operating window calculations and state transitions.
    """

    @abstractmethod
    def execute(self, context: 'ThermalManager') -> Optional[ThermalState]:
        """Execute state-specific logic and return next state if transition needed.
        
        Args:
            context: ThermalManager instance for access to models and data
            
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

    def execute(self, context: 'ThermalManager') -> Optional[ThermalState]:
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
        preferences: UserPreferences
    ):
        """Initialize ThermalManager."""
        self._hass = hass
        self._model = thermal_model
        self._preferences = preferences
        self._current_state = ThermalState.PRIMING  # Default to PRIMING for new users
        self._state_handlers: Dict[ThermalState, StateHandler] = {}
        self._last_hvac_mode = "cool"  # Default assumption
        self._setpoint = 24.0  # Default setpoint
        
        # Initialize state handlers registry
        self._initialize_state_handlers()
        
        _LOGGER.debug("ThermalManager initialized in %s state", self._current_state.value)

    def _initialize_state_handlers(self) -> None:
        """Initialize state handlers registry with default handlers."""
        # Create default handlers for all states
        # Individual state handlers will be replaced when thermal_state_handlers.py is available
        for state in ThermalState:
            self._state_handlers[state] = DefaultStateHandler()

    @property
    def current_state(self) -> ThermalState:
        """Get current thermal state."""
        return self._current_state

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
        
        # Update state
        self._current_state = new_state
        
        # Call enter handler for new state
        try:
            self._state_handlers[new_state].on_enter(self)
        except Exception as e:
            _LOGGER.error("Error in enter handler for state %s: %s", new_state.value, e)
            raise
        
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