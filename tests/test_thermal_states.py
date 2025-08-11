"""Tests for thermal state handler base classes and state machine infrastructure.

Tests the StateHandler abstract base class and state transition validation
following the thermal efficiency state machine architecture.
"""

import pytest
from abc import ABC, abstractmethod
from unittest.mock import Mock, MagicMock
from typing import Optional

from custom_components.smart_climate.thermal_models import ThermalState
from custom_components.smart_climate.thermal_states import StateHandler


class TestStateHandler:
    """Test StateHandler abstract base class functionality."""

    def test_state_handler_is_abstract(self):
        """Test that StateHandler cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            StateHandler()

    def test_state_handler_abstract_methods_defined(self):
        """Test that StateHandler defines required abstract methods."""
        # Check that abstract methods are defined
        assert hasattr(StateHandler, 'execute')
        assert hasattr(StateHandler, 'on_enter')
        assert hasattr(StateHandler, 'on_exit')
        
        # Verify they are abstract
        assert getattr(StateHandler.execute, '__isabstractmethod__', False)
        assert getattr(StateHandler.on_enter, '__isabstractmethod__', False)
        assert getattr(StateHandler.on_exit, '__isabstractmethod__', False)


class MockStateHandler(StateHandler):
    """Mock concrete implementation of StateHandler for testing."""
    
    def __init__(self, next_state: Optional[ThermalState] = None):
        self.next_state = next_state
        self.execute_called = False
        self.on_enter_called = False
        self.on_exit_called = False
        self.context_received = None
    
    def execute(self, context, current_temp: float, operating_window: tuple[float, float]) -> Optional[ThermalState]:
        """Mock execute method."""
        self.execute_called = True
        self.context_received = context
        self.current_temp = current_temp
        self.operating_window = operating_window
        return self.next_state
    
    def on_enter(self, context) -> None:
        """Mock on_enter callback."""
        self.on_enter_called = True
        self.context_received = context
    
    def on_exit(self, context) -> None:
        """Mock on_exit callback."""
        self.on_exit_called = True
        self.context_received = context


class TestStateHandlerImplementation:
    """Test concrete StateHandler implementations."""

    def test_concrete_state_handler_can_be_instantiated(self):
        """Test that concrete StateHandler can be created."""
        handler = MockStateHandler()
        assert isinstance(handler, StateHandler)

    def test_execute_method_signature(self):
        """Test execute method accepts context and returns Optional[ThermalState]."""
        handler = MockStateHandler(ThermalState.CORRECTING)
        mock_context = Mock()
        
        result = handler.execute(mock_context, 23.0, (22.0, 24.0))
        
        assert handler.execute_called
        assert handler.context_received is mock_context
        assert result == ThermalState.CORRECTING

    def test_execute_can_return_none(self):
        """Test execute method can return None (no state change)."""
        handler = MockStateHandler(None)
        mock_context = Mock()
        
        result = handler.execute(mock_context, 23.0, (22.0, 24.0))
        
        assert result is None

    def test_on_enter_callback(self):
        """Test on_enter callback receives context."""
        handler = MockStateHandler()
        mock_context = Mock()
        
        handler.on_enter(mock_context)
        
        assert handler.on_enter_called
        assert handler.context_received is mock_context

    def test_on_exit_callback(self):
        """Test on_exit callback receives context."""
        handler = MockStateHandler()
        mock_context = Mock()
        
        handler.on_exit(mock_context)
        
        assert handler.on_exit_called
        assert handler.context_received is mock_context

    def test_state_lifecycle_methods_return_none(self):
        """Test on_enter and on_exit return None."""
        handler = MockStateHandler()
        mock_context = Mock()
        
        enter_result = handler.on_enter(mock_context)
        exit_result = handler.on_exit(mock_context)
        
        assert enter_result is None
        assert exit_result is None


class TestThermalManagerIntegration:
    """Test StateHandler integration with ThermalManager context."""

    def test_state_handler_context_type_hint(self):
        """Test that StateHandler methods expect ThermalManager context."""
        # This test verifies the type hint in the abstract method
        # The actual implementation should accept ThermalManager
        handler = MockStateHandler()
        
        # Create a mock ThermalManager
        mock_thermal_manager = Mock(spec=['current_state', 'get_operating_window'])
        mock_thermal_manager.current_state = ThermalState.PRIMING
        
        # Should accept ThermalManager without error
        result = handler.execute(mock_thermal_manager, 23.0, (22.0, 24.0))
        handler.on_enter(mock_thermal_manager)
        handler.on_exit(mock_thermal_manager)
        
        assert handler.context_received is mock_thermal_manager

    def test_state_transition_return_validation(self):
        """Test state transition returns are valid ThermalState values."""
        # Test all valid states can be returned
        for state in ThermalState:
            handler = MockStateHandler(state)
            result = handler.execute(Mock(), 23.0, (22.0, 24.0))
            assert result in ThermalState or result is None

    def test_execute_method_accepts_thermal_manager_interface(self):
        """Test execute method works with ThermalManager interface."""
        handler = MockStateHandler(ThermalState.DRIFTING)
        
        # Mock ThermalManager with expected interface
        mock_manager = Mock()
        mock_manager.current_state = ThermalState.PRIMING
        mock_manager.get_operating_window.return_value = (20.0, 24.0)
        
        result = handler.execute(mock_manager, 23.0, (22.0, 24.0))
        
        assert result == ThermalState.DRIFTING
        assert handler.context_received is mock_manager


class TestStateTransitionValidation:
    """Test state transition validation logic."""

    def test_valid_state_transitions(self):
        """Test that valid state transitions are accepted."""
        # These should be valid transitions based on the state machine
        valid_transitions = [
            (ThermalState.PRIMING, ThermalState.DRIFTING),
            (ThermalState.DRIFTING, ThermalState.CORRECTING),
            (ThermalState.CORRECTING, ThermalState.DRIFTING),
            (ThermalState.RECOVERY, ThermalState.DRIFTING),
            (ThermalState.PROBING, ThermalState.DRIFTING),
            (ThermalState.CALIBRATING, ThermalState.DRIFTING),
        ]
        
        for from_state, to_state in valid_transitions:
            handler = MockStateHandler(to_state)
            mock_context = Mock()
            mock_context.current_state = from_state
            
            result = handler.execute(mock_context, 23.0, (22.0, 24.0))
            assert result == to_state

    def test_state_handler_base_provides_no_validation(self):
        """Test that base StateHandler doesn't enforce transition rules."""
        # The base StateHandler should allow any transition
        # Validation should be in ThermalManager or specific handlers
        handler = MockStateHandler(ThermalState.PROBING)
        result = handler.execute(Mock(), 23.0, (22.0, 24.0))
        assert result == ThermalState.PROBING

    def test_none_return_means_no_state_change(self):
        """Test that returning None from execute means no state transition."""
        handler = MockStateHandler(None)
        result = handler.execute(Mock(), 23.0, (22.0, 24.0))
        assert result is None