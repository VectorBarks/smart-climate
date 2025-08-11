"""Tests for thermal state system bug fixes.

ABOUTME: Test cases that reproduce and verify fixes for AttributeError and persistence bugs.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from homeassistant.core import HomeAssistant

from custom_components.smart_climate.thermal_manager import ThermalManager
from custom_components.smart_climate.thermal_state_handlers import DriftingState, CorrectingState
from custom_components.smart_climate.thermal_model import PassiveThermalModel
from custom_components.smart_climate.thermal_preferences import UserPreferences, PreferenceLevel
from custom_components.smart_climate.thermal_models import ThermalState


class TestThermalStateBugs:
    """Test thermal state system bugs."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock Home Assistant
        self.hass = Mock()
        
        # Create real thermal model and preferences
        self.thermal_model = PassiveThermalModel()
        self.preferences = UserPreferences(
            level=PreferenceLevel.BALANCED,
            comfort_band=1.0,
            confidence_threshold=0.7,
            probe_drift=2.0
        )
        
        # Create ThermalManager with real components
        self.thermal_manager = ThermalManager(
            self.hass,
            self.thermal_model,
            self.preferences
        )
        
        # Create state handlers
        self.drifting_state = DriftingState()
        self.correcting_state = CorrectingState()

    def test_drifting_state_attribute_error_bug_fixed(self):
        """Test that DriftingState.execute() no longer raises AttributeError after fix."""
        # Set thermal manager to DRIFTING state
        self.thermal_manager._current_state = ThermalState.DRIFTING
        
        # FIXED: Now accepts parameters instead of accessing context attributes
        # Should handle missing parameters gracefully (return None, log warning)
        result = self.drifting_state.execute(self.thermal_manager, current_temp=None, operating_window=None)
        assert result is None  # Should return None for missing parameters
        
        # Test with valid parameters
        current_temp = 23.5
        operating_window = (22.0, 24.0)
        result = self.drifting_state.execute(self.thermal_manager, current_temp, operating_window)
        assert result is None  # Should stay in DRIFTING when temp is within window

    def test_correcting_state_attribute_error_bug_fixed(self):
        """Test that CorrectingState.execute() no longer raises AttributeError after fix."""
        # Set thermal manager to CORRECTING state
        self.thermal_manager._current_state = ThermalState.CORRECTING
        
        # FIXED: Now accepts parameters instead of accessing context attributes
        # Should handle missing parameters gracefully (return None, log warning)
        result = self.correcting_state.execute(self.thermal_manager, current_temp=None, operating_window=None)
        assert result is None  # Should return None for missing parameters
        
        # Test with valid parameters - temperature outside window should stay in CORRECTING
        current_temp = 25.5  # Above window
        operating_window = (22.0, 24.0)
        result = self.correcting_state.execute(self.thermal_manager, current_temp, operating_window)
        assert result is None  # Should stay in CORRECTING when temp is outside safe zone

    def test_thermal_state_persistence_bug_fixed(self):
        """Test that thermal state transitions now trigger persistence after fix."""
        # Mock persistence callback to track calls
        mock_persistence_callback = Mock()
        
        # Create ThermalManager with persistence callback (simulating fixed version)
        thermal_manager_with_persistence = ThermalManager(
            self.hass, 
            self.thermal_model, 
            self.preferences,
            persistence_callback=mock_persistence_callback
        )
        
        # Set up in PRIMING state
        thermal_manager_with_persistence._current_state = ThermalState.PRIMING
        
        # Transition to DRIFTING state
        thermal_manager_with_persistence.transition_to(ThermalState.DRIFTING)
        
        # Verify the state changed
        assert thermal_manager_with_persistence.current_state == ThermalState.DRIFTING
        
        # FIXED: The state change should now trigger persistence
        mock_persistence_callback.assert_called_once()
        
        # Reset mock and test another transition
        mock_persistence_callback.reset_mock()
        thermal_manager_with_persistence.transition_to(ThermalState.CORRECTING)
        assert thermal_manager_with_persistence.current_state == ThermalState.CORRECTING
        mock_persistence_callback.assert_called_once()  # Should be called again

    def test_state_handlers_work_with_parameters(self):
        """Test that state handlers work correctly with temperature and window parameters."""
        # Test DriftingState with temperature within operating window
        current_temp = 23.0  # Within window
        operating_window = (22.0, 24.0)
        
        # Should stay in DRIFTING when temperature is within window
        result = self.drifting_state.execute(self.thermal_manager, current_temp, operating_window)
        assert result is None
        
        # Test DriftingState with temperature outside operating window
        current_temp = 25.5  # Above window
        result = self.drifting_state.execute(self.thermal_manager, current_temp, operating_window)
        assert result == ThermalState.CORRECTING  # Should transition to CORRECTING
        
        # Test CorrectingState with temperature within safe zone (with hysteresis)
        self.thermal_manager._current_state = ThermalState.CORRECTING
        current_temp = 23.0  # Within hysteresis buffer
        result = self.correcting_state.execute(self.thermal_manager, current_temp, operating_window)
        assert result == ThermalState.DRIFTING  # Should transition back to DRIFTING

    @patch('custom_components.smart_climate.thermal_manager.datetime')
    def test_calibration_hour_transition_with_persistence_fixed(self, mock_datetime):
        """Test that calibration hour transitions now trigger persistence after fix."""
        # Mock datetime to simulate calibration hour (2 AM)
        mock_now = datetime(2025, 8, 11, 2, 0, 0)  # 2 AM
        mock_datetime.now.return_value = mock_now
        
        # Mock persistence callback
        mock_persistence_callback = Mock()
        
        # Create ThermalManager with persistence callback
        thermal_manager = ThermalManager(
            self.hass, 
            self.thermal_model, 
            self.preferences,
            config={'calibration_hour': 2},
            persistence_callback=mock_persistence_callback
        )
        
        # Start in DRIFTING state
        thermal_manager._current_state = ThermalState.DRIFTING
        
        # Call update_state during calibration hour
        thermal_manager.update_state()
        
        # Should transition to CALIBRATING
        assert thermal_manager.current_state == ThermalState.CALIBRATING
        
        # FIXED: Persistence should now be triggered for this state change
        mock_persistence_callback.assert_called_once()