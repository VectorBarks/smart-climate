"""ABOUTME: Thermal state handler base classes for Smart Climate Control.
Abstract base classes and interfaces for the thermal efficiency state machine."""

from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

from .thermal_models import ThermalState

if TYPE_CHECKING:
    # Forward reference to avoid circular imports
    # ThermalManager will be implemented in a separate module
    from typing import Protocol
    
    class ThermalManager(Protocol):
        """Type hint protocol for ThermalManager context."""
        current_state: ThermalState
        
        def get_operating_window(self, setpoint: float, outdoor_temp: float, hvac_mode: str) -> tuple[float, float]:
            """Get the current operating window for the thermal system."""
            ...


class StateHandler(ABC):
    """Abstract base class for thermal efficiency state handlers.
    
    Each thermal state (PRIMING, DRIFTING, CORRECTING, etc.) implements
    this interface to define its behavior and transitions.
    
    The StateHandler receives a ThermalManager context and can:
    - Execute state-specific logic
    - Determine next state transitions
    - Handle state entry and exit callbacks
    """

    @abstractmethod
    def execute(self, context: "ThermalManager") -> Optional[ThermalState]:
        """Execute state-specific logic and determine next state.
        
        Args:
            context: ThermalManager instance providing system state and methods
            
        Returns:
            Next ThermalState to transition to, or None to stay in current state
        """
        pass

    @abstractmethod 
    def on_enter(self, context: "ThermalManager") -> None:
        """Called when entering this state.
        
        Performs any setup or initialization needed when transitioning
        into this state.
        
        Args:
            context: ThermalManager instance for system interaction
        """
        pass

    @abstractmethod
    def on_exit(self, context: "ThermalManager") -> None:
        """Called when exiting this state.
        
        Performs any cleanup needed when transitioning out of this state.
        
        Args:
            context: ThermalManager instance for system interaction
        """
        pass