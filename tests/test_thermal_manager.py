"""ABOUTME: Test suite for ThermalManager state machine orchestrator.
Tests state transitions, operating window calculations, and AC control decisions."""

import pytest
from unittest.mock import Mock, MagicMock
from typing import Dict, Tuple, Optional

from custom_components.smart_climate.thermal_models import ThermalState, ThermalConstants
from custom_components.smart_climate.thermal_preferences import UserPreferences, PreferenceLevel
from custom_components.smart_climate.thermal_model import PassiveThermalModel
from custom_components.smart_climate.thermal_manager import ThermalManager, StateHandler


class TestThermalManager:
    """Test ThermalManager state machine orchestrator."""

    @pytest.fixture
    def mock_hass(self):
        """Mock Home Assistant instance."""
        return Mock()

    @pytest.fixture
    def mock_thermal_model(self):
        """Mock PassiveThermalModel."""
        model = Mock(spec=PassiveThermalModel)
        model.predict_drift.return_value = 22.0
        model.get_confidence.return_value = 0.8
        return model

    @pytest.fixture
    def mock_preferences(self):
        """Mock UserPreferences."""
        prefs = Mock(spec=UserPreferences)
        prefs.level = PreferenceLevel.BALANCED
        prefs.get_adjusted_band.return_value = 1.5
        return prefs

    @pytest.fixture
    def thermal_manager(self, mock_hass, mock_thermal_model, mock_preferences):
        """Create ThermalManager instance for testing."""
        return ThermalManager(mock_hass, mock_thermal_model, mock_preferences)

    def test_initial_state_priming_for_new_users(self, thermal_manager):
        """Test that ThermalManager initializes in PRIMING state for new users."""
        assert thermal_manager.current_state == ThermalState.PRIMING
        assert thermal_manager._current_state == ThermalState.PRIMING

    def test_state_handlers_registry_created(self, thermal_manager):
        """Test that state handlers registry is properly initialized."""
        assert hasattr(thermal_manager, '_state_handlers')

    def test_thermal_constants_initialization(self, mock_hass, mock_thermal_model, mock_preferences):
        """Test that thermal_constants attribute is properly initialized."""
        # Test with default configuration
        manager = ThermalManager(mock_hass, mock_thermal_model, mock_preferences)
        
        assert hasattr(manager, 'thermal_constants')
        assert isinstance(manager.thermal_constants, ThermalConstants)
        
        # Test default values
        assert manager.thermal_constants.tau_cooling == 90.0
        assert manager.thermal_constants.tau_warming == 150.0
        assert manager.thermal_constants.min_off_time == 600
        assert manager.thermal_constants.min_on_time == 300
        assert manager.thermal_constants.priming_duration == 86400
        assert manager.thermal_constants.recovery_duration == 1800

    def test_thermal_constants_from_config(self, mock_hass, mock_thermal_model, mock_preferences):
        """Test that thermal_constants uses config values when provided."""
        config = {
            'tau_cooling': 120.0,
            'tau_warming': 180.0,
            'min_off_time': 900,
            'min_on_time': 450,
            'priming_duration': 172800,  # 48 hours
            'recovery_duration': 2700
        }
        
        manager = ThermalManager(mock_hass, mock_thermal_model, mock_preferences, config)
        
        assert manager.thermal_constants.tau_cooling == 120.0
        assert manager.thermal_constants.tau_warming == 180.0
        assert manager.thermal_constants.min_off_time == 900
        assert manager.thermal_constants.min_on_time == 450
        assert manager.thermal_constants.priming_duration == 172800
        assert manager.thermal_constants.recovery_duration == 2700

    def test_transition_to_valid_state(self, thermal_manager):
        """Test successful state transition."""
        thermal_manager.transition_to(ThermalState.DRIFTING)
        assert thermal_manager.current_state == ThermalState.DRIFTING

    def test_transition_to_invalid_state_raises_error(self, thermal_manager):
        """Test that invalid state transition raises ValueError."""
        with pytest.raises(ValueError, match="Invalid thermal state"):
            thermal_manager.transition_to("invalid_state")

    def test_transition_calls_state_handlers(self, thermal_manager):
        """Test that state transitions call appropriate handler methods."""
        # Mock the state handlers
        old_handler = Mock()
        new_handler = Mock()
        thermal_manager._state_handlers[ThermalState.PRIMING] = old_handler
        thermal_manager._state_handlers[ThermalState.DRIFTING] = new_handler
        
        thermal_manager.transition_to(ThermalState.DRIFTING)
        
        old_handler.on_exit.assert_called_once_with(thermal_manager)
        new_handler.on_enter.assert_called_once_with(thermal_manager)

    def test_get_operating_window_cooling_mode(self, thermal_manager, mock_preferences):
        """Test operating window calculation for cooling mode."""
        mock_preferences.get_adjusted_band.return_value = 1.5
        setpoint = 24.0
        outdoor_temp = 30.0
        
        lower, upper = thermal_manager.get_operating_window(setpoint, outdoor_temp, "cool")
        
        # Window should be centered around setpoint with preference-adjusted band
        expected_lower = setpoint - 1.5
        expected_upper = setpoint + 1.5
        assert lower == expected_lower
        assert upper == expected_upper
        mock_preferences.get_adjusted_band.assert_called_once_with(outdoor_temp, "cool")

    def test_get_operating_window_heating_mode(self, thermal_manager, mock_preferences):
        """Test operating window calculation for heating mode."""
        mock_preferences.get_adjusted_band.return_value = 1.2
        setpoint = 20.0
        outdoor_temp = 5.0
        
        lower, upper = thermal_manager.get_operating_window(setpoint, outdoor_temp, "heat")
        
        expected_lower = setpoint - 1.2
        expected_upper = setpoint + 1.2
        assert lower == expected_lower
        assert upper == expected_upper
        mock_preferences.get_adjusted_band.assert_called_once_with(outdoor_temp, "heat")

    def test_should_ac_run_cooling_above_upper_bound(self, thermal_manager):
        """Test AC should run when cooling and temperature above upper bound."""
        current = 25.5
        setpoint = 24.0
        window = (22.5, 25.5)
        
        should_run = thermal_manager.should_ac_run(current, setpoint, window)
        assert should_run is True

    def test_should_ac_run_cooling_below_lower_bound(self, thermal_manager):
        """Test AC should not run when cooling and temperature below lower bound."""
        current = 22.0
        setpoint = 24.0
        window = (22.5, 25.5)
        
        should_run = thermal_manager.should_ac_run(current, setpoint, window)
        assert should_run is False

    def test_should_ac_run_heating_below_lower_bound(self, thermal_manager):
        """Test AC should run when heating and temperature below lower bound."""
        current = 18.0
        setpoint = 20.0
        window = (18.5, 21.5)
        
        # Mock HVAC mode detection - in practice this would be passed or detected
        thermal_manager._last_hvac_mode = "heat"
        should_run = thermal_manager.should_ac_run(current, setpoint, window)
        assert should_run is True

    def test_should_ac_run_heating_above_upper_bound(self, thermal_manager):
        """Test AC should not run when heating and temperature above upper bound."""
        current = 22.0
        setpoint = 20.0
        window = (18.5, 21.5)
        
        thermal_manager._last_hvac_mode = "heat"
        should_run = thermal_manager.should_ac_run(current, setpoint, window)
        assert should_run is False

    def test_should_ac_run_within_comfort_window(self, thermal_manager):
        """Test AC should not run when temperature is within comfort window."""
        current = 24.0
        setpoint = 24.0
        window = (22.5, 25.5)
        
        should_run = thermal_manager.should_ac_run(current, setpoint, window)
        assert should_run is False

    def test_get_learning_target_returns_boundary_cooling(self, thermal_manager):
        """Test that get_learning_target returns appropriate boundary for cooling."""
        current = 26.0  # Above setpoint, cooling needed
        window = (22.5, 25.5)
        
        target = thermal_manager.get_learning_target(current, window)
        # Should return upper boundary for cooling
        assert target == 25.5

    def test_get_learning_target_returns_boundary_heating(self, thermal_manager):
        """Test that get_learning_target returns appropriate boundary for heating."""
        current = 18.0  # Below setpoint, heating needed
        window = (18.5, 21.5)
        
        thermal_manager._last_hvac_mode = "heat"
        target = thermal_manager.get_learning_target(current, window)
        # Should return lower boundary for heating
        assert target == 18.5

    def test_get_learning_target_within_window_returns_setpoint(self, thermal_manager):
        """Test that get_learning_target returns setpoint when within window."""
        current = 24.0  # Within window
        window = (22.5, 25.5)
        setpoint = 24.0
        
        thermal_manager._setpoint = setpoint
        target = thermal_manager.get_learning_target(current, window)
        # Should return setpoint when within comfort window
        assert target == setpoint

    def test_state_persistence_across_updates(self, thermal_manager):
        """Test that state persists across multiple updates."""
        initial_state = thermal_manager.current_state
        assert initial_state == ThermalState.PRIMING
        
        # Simulate some operations
        thermal_manager.get_operating_window(24.0, 30.0, "cool")
        thermal_manager.should_ac_run(25.0, 24.0, (22.5, 25.5))
        
        # State should remain unchanged unless explicitly transitioned
        assert thermal_manager.current_state == initial_state

    def test_state_aware_window_calculation(self, thermal_manager, mock_preferences):
        """Test that operating window calculation is state-aware."""
        mock_preferences.get_adjusted_band.return_value = 1.5
        
        # PRIMING state should have conservative bands
        thermal_manager._current_state = ThermalState.PRIMING
        lower1, upper1 = thermal_manager.get_operating_window(24.0, 30.0, "cool")
        
        # CORRECTING state should have different behavior
        thermal_manager._current_state = ThermalState.CORRECTING
        lower2, upper2 = thermal_manager.get_operating_window(24.0, 30.0, "cool")
        
        # Both should use preferences but state handlers might modify
        assert isinstance(lower1, float)
        assert isinstance(upper1, float)
        assert isinstance(lower2, float)
        assert isinstance(upper2, float)

    def test_current_state_property(self, thermal_manager):
        """Test current_state property getter."""
        assert thermal_manager.current_state == ThermalState.PRIMING
        
        thermal_manager.transition_to(ThermalState.DRIFTING)
        assert thermal_manager.current_state == ThermalState.DRIFTING

    def test_state_machine_context_passing(self, thermal_manager):
        """Test that ThermalManager passes self as context to state handlers."""
        mock_handler = Mock()
        thermal_manager._state_handlers[ThermalState.CORRECTING] = mock_handler
        
        thermal_manager.transition_to(ThermalState.CORRECTING)
        
        # Handler should receive ThermalManager instance as context
        mock_handler.on_enter.assert_called_once_with(thermal_manager)

    def test_error_handling_in_state_transitions(self, thermal_manager):
        """Test error handling during state transitions."""
        mock_handler = Mock()
        mock_handler.on_enter.side_effect = Exception("Handler error")
        thermal_manager._state_handlers[ThermalState.CORRECTING] = mock_handler
        
        # Should handle errors gracefully and not crash
        with pytest.raises(Exception, match="Handler error"):
            thermal_manager.transition_to(ThermalState.CORRECTING)

    def test_multiple_rapid_transitions(self, thermal_manager):
        """Test multiple rapid state transitions work correctly."""
        states = [ThermalState.DRIFTING, ThermalState.CORRECTING, ThermalState.RECOVERY]
        
        for state in states:
            thermal_manager.transition_to(state)
            assert thermal_manager.current_state == state

    def test_hvac_mode_inference_from_temperature_and_window(self, thermal_manager):
        """Test HVAC mode inference for learning target calculation."""
        # Test cooling scenario
        current = 26.0
        window = (22.5, 25.5)
        setpoint = 24.0
        
        # Temperature above window suggests cooling needed
        target = thermal_manager.get_learning_target(current, window)
        assert target == window[1]  # Upper boundary for cooling
        
        # Test heating scenario
        current = 18.0
        window = (18.5, 21.5)
        
        # Temperature below window suggests heating needed
        target = thermal_manager.get_learning_target(current, window)
        assert target == window[0]  # Lower boundary for heating

    def test_operating_window_with_extreme_outdoor_temperatures(self, thermal_manager, mock_preferences):
        """Test operating window calculation with extreme outdoor temperatures."""
        # Test extreme heat
        mock_preferences.get_adjusted_band.return_value = 2.0
        lower, upper = thermal_manager.get_operating_window(24.0, 45.0, "cool")
        assert lower == 22.0
        assert upper == 26.0
        
        # Test extreme cold
        mock_preferences.get_adjusted_band.return_value = 1.0
        lower, upper = thermal_manager.get_operating_window(20.0, -10.0, "heat")
        assert lower == 19.0
        assert upper == 21.0

    def test_should_ac_run_edge_case_temperatures(self, thermal_manager):
        """Test should_ac_run with edge case temperatures at exact boundaries."""
        setpoint = 24.0
        window = (22.5, 25.5)
        
        # Test exactly at lower bound with cooling
        assert thermal_manager.should_ac_run(22.5, setpoint, window) is False
        
        # Test exactly at upper bound with cooling  
        assert thermal_manager.should_ac_run(25.5, setpoint, window) is True
        
        # Test heating mode at boundaries
        thermal_manager._last_hvac_mode = "heat"
        assert thermal_manager.should_ac_run(22.5, setpoint, window) is True
        assert thermal_manager.should_ac_run(25.5, setpoint, window) is False

    def test_learning_target_with_very_large_deviations(self, thermal_manager):
        """Test learning target calculation with very large temperature deviations."""
        window = (20.0, 26.0)
        thermal_manager._setpoint = 23.0
        
        # Very hot temperature should still target upper bound
        target = thermal_manager.get_learning_target(35.0, window)
        assert target == 26.0
        
        # Very cold temperature should still target lower bound
        thermal_manager._last_hvac_mode = "heat"
        target = thermal_manager.get_learning_target(5.0, window)
        assert target == 20.0