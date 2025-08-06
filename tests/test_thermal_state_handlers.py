"""Tests for thermal state handlers - DriftingState and CorrectingState.

Tests the concrete state handler implementations following TDD.
Covers state-specific behavior, transitions, and learning flag management.
"""

import pytest
import logging
from unittest.mock import Mock, MagicMock
from typing import Optional

from custom_components.smart_climate.thermal_models import ThermalState
from custom_components.smart_climate.thermal_states import StateHandler


class TestDriftingState:
    """Test DriftingState handler behavior and transitions."""

    def test_drifting_state_can_be_imported(self):
        """Test DriftingState can be imported from thermal_state_handlers."""
        # This will fail initially until we implement the file
        from custom_components.smart_climate.thermal_state_handlers import DriftingState
        assert issubclass(DriftingState, StateHandler)

    def test_drifting_state_instantiation(self):
        """Test DriftingState can be instantiated."""
        from custom_components.smart_climate.thermal_state_handlers import DriftingState
        handler = DriftingState()
        assert isinstance(handler, StateHandler)

    def test_drifting_state_temperature_within_bands_no_transition(self):
        """Test DriftingState stays in DRIFTING when temperature within bands."""
        from custom_components.smart_climate.thermal_state_handlers import DriftingState
        
        handler = DriftingState()
        mock_context = Mock()
        mock_context.current_temp = 22.5
        mock_context.operating_window = (20.0, 24.0)
        
        result = handler.execute(mock_context)
        
        assert result is None  # No state transition

    def test_drifting_state_temperature_above_upper_band_transitions_to_correcting(self):
        """Test DriftingState transitions to CORRECTING when temp exceeds upper band."""
        from custom_components.smart_climate.thermal_state_handlers import DriftingState
        
        handler = DriftingState()
        mock_context = Mock()
        mock_context.current_temp = 24.5  # Above upper bound
        mock_context.operating_window = (20.0, 24.0)
        
        result = handler.execute(mock_context)
        
        assert result == ThermalState.CORRECTING

    def test_drifting_state_temperature_below_lower_band_transitions_to_correcting(self):
        """Test DriftingState transitions to CORRECTING when temp below lower band."""
        from custom_components.smart_climate.thermal_state_handlers import DriftingState
        
        handler = DriftingState()
        mock_context = Mock()
        mock_context.current_temp = 19.5  # Below lower bound
        mock_context.operating_window = (20.0, 24.0)
        
        result = handler.execute(mock_context)
        
        assert result == ThermalState.CORRECTING

    def test_drifting_state_temperature_exactly_at_upper_bound_transitions(self):
        """Test DriftingState transitions when temp exactly at upper bound."""
        from custom_components.smart_climate.thermal_state_handlers import DriftingState
        
        handler = DriftingState()
        mock_context = Mock()
        mock_context.current_temp = 24.0  # Exactly at upper bound
        mock_context.operating_window = (20.0, 24.0)
        
        result = handler.execute(mock_context)
        
        assert result == ThermalState.CORRECTING

    def test_drifting_state_temperature_exactly_at_lower_bound_transitions(self):
        """Test DriftingState transitions when temp exactly at lower bound."""
        from custom_components.smart_climate.thermal_state_handlers import DriftingState
        
        handler = DriftingState()
        mock_context = Mock()
        mock_context.current_temp = 20.0  # Exactly at lower bound
        mock_context.operating_window = (20.0, 24.0)
        
        result = handler.execute(mock_context)
        
        assert result == ThermalState.CORRECTING

    def test_drifting_state_pauses_offset_learning_on_execute(self):
        """Test DriftingState pauses offset learning during execute."""
        from custom_components.smart_climate.thermal_state_handlers import DriftingState
        
        handler = DriftingState()
        mock_context = Mock()
        mock_context.current_temp = 22.0
        mock_context.operating_window = (20.0, 24.0)
        mock_context.offset_learning_paused = False
        
        handler.execute(mock_context)
        
        assert mock_context.offset_learning_paused is True

    def test_drifting_state_on_enter_logs_state_entry(self):
        """Test DriftingState logs state entry on_enter."""
        from custom_components.smart_climate.thermal_state_handlers import DriftingState
        
        handler = DriftingState()
        mock_context = Mock()
        
        # Should not raise exception - logging is implemented
        handler.on_enter(mock_context)

    def test_drifting_state_on_exit_called(self):
        """Test DriftingState on_exit can be called."""
        from custom_components.smart_climate.thermal_state_handlers import DriftingState
        
        handler = DriftingState()
        mock_context = Mock()
        
        # Should not raise exception
        handler.on_exit(mock_context)

    def test_drifting_state_with_missing_context_attributes_handles_gracefully(self):
        """Test DriftingState handles missing context attributes gracefully."""
        from custom_components.smart_climate.thermal_state_handlers import DriftingState
        
        handler = DriftingState()
        mock_context = Mock()
        # Missing current_temp and operating_window
        
        # Should not crash, might return None or raise appropriate exception
        try:
            result = handler.execute(mock_context)
            # Either returns None or raises AttributeError/ValueError
            assert result is None or isinstance(result, ThermalState)
        except (AttributeError, ValueError):
            # Expected behavior for missing attributes
            pass


class TestCorrectingState:
    """Test CorrectingState handler behavior and transitions."""

    def test_correcting_state_can_be_imported(self):
        """Test CorrectingState can be imported from thermal_state_handlers."""
        from custom_components.smart_climate.thermal_state_handlers import CorrectingState
        assert issubclass(CorrectingState, StateHandler)

    def test_correcting_state_instantiation(self):
        """Test CorrectingState can be instantiated."""
        from custom_components.smart_climate.thermal_state_handlers import CorrectingState
        handler = CorrectingState()
        assert isinstance(handler, StateHandler)

    def test_correcting_state_temperature_within_bands_with_buffer_transitions_to_drifting(self):
        """Test CorrectingState transitions to DRIFTING when temp within bands + buffer."""
        from custom_components.smart_climate.thermal_state_handlers import CorrectingState
        
        handler = CorrectingState()
        mock_context = Mock()
        mock_context.current_temp = 22.0  # Well within bounds
        mock_context.operating_window = (20.0, 24.0)
        
        result = handler.execute(mock_context)
        
        assert result == ThermalState.DRIFTING

    def test_correcting_state_temperature_at_boundary_no_transition(self):
        """Test CorrectingState stays in CORRECTING when temp at boundary (within buffer)."""
        from custom_components.smart_climate.thermal_state_handlers import CorrectingState
        
        handler = CorrectingState()
        mock_context = Mock()
        mock_context.current_temp = 24.1  # Just outside upper bound (within 0.2°C buffer)
        mock_context.operating_window = (20.0, 24.0)
        
        result = handler.execute(mock_context)
        
        assert result is None  # Stay in correcting

    def test_correcting_state_hysteresis_buffer_upper_bound(self):
        """Test CorrectingState uses 0.2°C buffer for upper bound hysteresis."""
        from custom_components.smart_climate.thermal_state_handlers import CorrectingState
        
        handler = CorrectingState()
        mock_context = Mock()
        mock_context.current_temp = 23.8  # Upper bound (24.0) - buffer (0.2) = 23.8
        mock_context.operating_window = (20.0, 24.0)
        mock_context._setpoint = 22.0  # Set real number for setpoint
        
        result = handler.execute(mock_context)
        
        # Should transition to DRIFTING as it's within buffer zone
        assert result == ThermalState.DRIFTING

    def test_correcting_state_hysteresis_buffer_lower_bound(self):
        """Test CorrectingState uses 0.2°C buffer for lower bound hysteresis."""
        from custom_components.smart_climate.thermal_state_handlers import CorrectingState
        
        handler = CorrectingState()
        mock_context = Mock()
        mock_context.current_temp = 20.2  # Lower bound (20.0) + buffer (0.2) = 20.2
        mock_context.operating_window = (20.0, 24.0)
        mock_context._setpoint = 22.0  # Set real number for setpoint
        
        result = handler.execute(mock_context)
        
        # Should transition to DRIFTING as it's within buffer zone
        assert result == ThermalState.DRIFTING

    def test_correcting_state_resumes_offset_learning_on_execute(self):
        """Test CorrectingState resumes offset learning during execute."""
        from custom_components.smart_climate.thermal_state_handlers import CorrectingState
        
        handler = CorrectingState()
        mock_context = Mock()
        mock_context.current_temp = 22.0
        mock_context.operating_window = (20.0, 24.0)
        mock_context.offset_learning_paused = True
        
        handler.execute(mock_context)
        
        assert mock_context.offset_learning_paused is False

    def test_correcting_state_sets_learning_target_to_nearest_boundary(self):
        """Test CorrectingState sets learning target to nearest boundary."""
        from custom_components.smart_climate.thermal_state_handlers import CorrectingState
        
        handler = CorrectingState()
        mock_context = Mock()
        mock_context.current_temp = 25.0  # Above upper bound
        mock_context.operating_window = (20.0, 24.0)
        
        handler.execute(mock_context)
        
        # Should set learning target to upper boundary (24.0)
        assert mock_context.learning_target == 24.0

    def test_correcting_state_sets_learning_target_lower_boundary(self):
        """Test CorrectingState sets learning target to lower boundary when below."""
        from custom_components.smart_climate.thermal_state_handlers import CorrectingState
        
        handler = CorrectingState()
        mock_context = Mock()
        mock_context.current_temp = 19.0  # Below lower bound
        mock_context.operating_window = (20.0, 24.0)
        
        handler.execute(mock_context)
        
        # Should set learning target to lower boundary (20.0)
        assert mock_context.learning_target == 20.0

    def test_correcting_state_sets_learning_target_within_bands_uses_setpoint(self):
        """Test CorrectingState sets learning target to setpoint when within bands."""
        from custom_components.smart_climate.thermal_state_handlers import CorrectingState
        
        handler = CorrectingState()
        mock_context = Mock()
        mock_context.current_temp = 22.0  # Within bounds
        mock_context.operating_window = (20.0, 24.0)
        mock_context._setpoint = 22.0  # Mock setpoint
        
        handler.execute(mock_context)
        
        # Should set learning target to setpoint (22.0)
        assert mock_context.learning_target == 22.0

    def test_correcting_state_on_enter_logs_state_entry(self):
        """Test CorrectingState logs state entry on_enter."""
        from custom_components.smart_climate.thermal_state_handlers import CorrectingState
        
        handler = CorrectingState()
        mock_context = Mock()
        
        # For now, just verify on_enter can be called
        handler.on_enter(mock_context)

    def test_correcting_state_on_exit_called(self):
        """Test CorrectingState on_exit can be called."""
        from custom_components.smart_climate.thermal_state_handlers import CorrectingState
        
        handler = CorrectingState()
        mock_context = Mock()
        
        # Should not raise exception
        handler.on_exit(mock_context)


class TestStateHandlerEdgeCases:
    """Test edge cases and error handling for state handlers."""

    def test_drifting_state_with_none_current_temp_handles_gracefully(self):
        """Test DriftingState handles None current_temp gracefully."""
        from custom_components.smart_climate.thermal_state_handlers import DriftingState
        
        handler = DriftingState()
        mock_context = Mock()
        mock_context.current_temp = None
        mock_context.operating_window = (20.0, 24.0)
        
        try:
            result = handler.execute(mock_context)
            # Should either return None or raise appropriate exception
            assert result is None or isinstance(result, ThermalState)
        except (AttributeError, ValueError, TypeError):
            # Expected behavior for invalid input
            pass

    def test_correcting_state_with_none_operating_window_handles_gracefully(self):
        """Test CorrectingState handles None operating_window gracefully."""
        from custom_components.smart_climate.thermal_state_handlers import CorrectingState
        
        handler = CorrectingState()
        mock_context = Mock()
        mock_context.current_temp = 22.0
        mock_context.operating_window = None
        
        try:
            result = handler.execute(mock_context)
            # Should either return None or raise appropriate exception
            assert result is None or isinstance(result, ThermalState)
        except (AttributeError, ValueError, TypeError):
            # Expected behavior for invalid input
            pass

    def test_drifting_state_with_inverted_operating_window_handles_gracefully(self):
        """Test DriftingState handles inverted operating window gracefully."""
        from custom_components.smart_climate.thermal_state_handlers import DriftingState
        
        handler = DriftingState()
        mock_context = Mock()
        mock_context.current_temp = 22.0
        mock_context.operating_window = (24.0, 20.0)  # Inverted
        
        try:
            result = handler.execute(mock_context)
            # Should handle gracefully or raise appropriate exception
            assert result is None or isinstance(result, ThermalState)
        except (ValueError, TypeError):
            # Expected behavior for invalid window
            pass

    def test_correcting_state_with_very_small_operating_window(self):
        """Test CorrectingState with very small operating window."""
        from custom_components.smart_climate.thermal_state_handlers import CorrectingState
        
        handler = CorrectingState()
        mock_context = Mock()
        mock_context.current_temp = 22.0
        mock_context.operating_window = (21.9, 22.1)  # Very small window
        mock_context._setpoint = 22.0
        
        result = handler.execute(mock_context)
        
        # Should handle small windows without crashing
        assert result is None or isinstance(result, ThermalState)

    def test_state_handlers_handle_missing_setpoint_gracefully(self):
        """Test state handlers handle missing setpoint attribute gracefully."""
        from custom_components.smart_climate.thermal_state_handlers import CorrectingState
        
        handler = CorrectingState()
        mock_context = Mock()
        mock_context.current_temp = 22.0
        mock_context.operating_window = (20.0, 24.0)
        # Mock doesn't have _setpoint attribute
        
        try:
            handler.execute(mock_context)
            # Should either work with fallback or raise appropriate exception
        except AttributeError:
            # Expected behavior when setpoint is missing
            pass


class TestStateHandlerIntegration:
    """Test state handler integration with ThermalManager."""

    def test_state_handlers_work_with_thermal_manager_interface(self):
        """Test state handlers work with ThermalManager interface."""
        from custom_components.smart_climate.thermal_state_handlers import DriftingState, CorrectingState
        
        # Mock minimal ThermalManager interface
        mock_manager = Mock()
        mock_manager.current_state = ThermalState.DRIFTING
        mock_manager.current_temp = 22.0
        mock_manager.operating_window = (20.0, 24.0)
        mock_manager.offset_learning_paused = False
        
        drifting_handler = DriftingState()
        correcting_handler = CorrectingState()
        
        # Both should be able to execute with ThermalManager interface
        drifting_result = drifting_handler.execute(mock_manager)
        correcting_result = correcting_handler.execute(mock_manager)
        
        assert drifting_result is None or isinstance(drifting_result, ThermalState)
        assert correcting_result is None or isinstance(correcting_result, ThermalState)

    def test_state_lifecycle_methods_integration(self):
        """Test state lifecycle methods work with context."""
        from custom_components.smart_climate.thermal_state_handlers import DriftingState, CorrectingState
        
        mock_context = Mock()
        
        drifting_handler = DriftingState()
        correcting_handler = CorrectingState()
        
        # All lifecycle methods should be callable
        drifting_handler.on_enter(mock_context)
        drifting_handler.on_exit(mock_context)
        correcting_handler.on_enter(mock_context)
        correcting_handler.on_exit(mock_context)
        
        # Should not raise exceptions