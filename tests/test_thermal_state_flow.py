"""Tests for thermal state flow fixes in Smart Climate Control.

This module tests the complete thermal state flow implementation:
- Fixed state transitions: PRIMING → PROBING → CALIBRATING → DRIFTING
- ProbeState data collection and tau updates
- CalibratingState data collection and tau updates  
- Manual and automatic probing triggers
- Button availability and persistence callbacks

Tests follow TDD approach and comprehensive coverage of new functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, call
from homeassistant.core import HomeAssistant

from custom_components.smart_climate.thermal_manager import ThermalManager
from custom_components.smart_climate.thermal_special_states import PrimingState, CalibratingState, ProbeState
from custom_components.smart_climate.thermal_state_handlers import DriftingState
from custom_components.smart_climate.thermal_models import ThermalState, ThermalConstants, ProbeResult
from custom_components.smart_climate.thermal_preferences import UserPreferences, PreferenceLevel
from custom_components.smart_climate.thermal_model import PassiveThermalModel


@pytest.fixture
def mock_hass():
    """Mock Home Assistant instance."""
    return Mock(spec=HomeAssistant)


@pytest.fixture
def mock_thermal_model():
    """Mock PassiveThermalModel with update_tau method."""
    model = Mock(spec=PassiveThermalModel)
    model.update_tau = Mock()
    model.get_confidence.return_value = 0.8
    return model


@pytest.fixture
def mock_preferences():
    """Mock UserPreferences."""
    prefs = Mock(spec=UserPreferences)
    prefs.level = PreferenceLevel.BALANCED
    prefs.comfort_band = 1.5
    prefs.get_adjusted_band.return_value = 1.5
    return prefs


@pytest.fixture
def thermal_constants():
    """ThermalConstants for testing."""
    return ThermalConstants(
        tau_cooling=90.0,
        tau_warming=150.0,
        priming_duration=86400,  # 24 hours
        recovery_duration=1800,  # 30 minutes
        min_probe_duration=1800  # 30 minutes for probing
    )


@pytest.fixture
def mock_persistence_callback():
    """Mock persistence callback."""
    return Mock()


@pytest.fixture
def thermal_manager(mock_hass, mock_thermal_model, mock_preferences, thermal_constants, mock_persistence_callback):
    """ThermalManager instance with mocked dependencies."""
    config = {
        "calibration_hour": 2,
        "calibration_idle_minutes": 30,
        "calibration_drift_threshold": 0.3,
        "passive_min_drift_minutes": 15
    }
    
    manager = ThermalManager(
        hass=mock_hass,
        thermal_model=mock_thermal_model,
        preferences=mock_preferences,
        config=config,
        persistence_callback=mock_persistence_callback
    )
    manager.thermal_constants = thermal_constants
    manager._setpoint = 23.0
    manager._last_hvac_mode = "cool"
    manager.current_temp = 23.0
    return manager


@pytest.fixture
def mock_probe_result():
    """Mock ProbeResult for testing."""
    return ProbeResult(
        tau_value=95.5,
        confidence=0.85,
        duration=3600,
        fit_quality=0.92,
        aborted=False
    )


class TestStateTransitionFlow:
    """Test complete thermal state transition flow."""
    
    def test_state_transition_flow(self, thermal_manager):
        """Test complete state transition flow: PRIMING → PROBING → CALIBRATING → DRIFTING."""
        # Start in PRIMING state
        assert thermal_manager.current_state == ThermalState.PRIMING
        
        # Mock stability detector to trigger PRIMING → PROBING transition
        thermal_manager.stability_detector.is_stable_for_calibration.return_value = True
        
        # Execute PRIMING state logic - should transition to PROBING
        priming_handler = thermal_manager._state_handlers[ThermalState.PRIMING]
        result = priming_handler.execute(thermal_manager, 23.0, (22.0, 24.0))
        assert result == ThermalState.PROBING
        
        # Transition to PROBING
        thermal_manager.transition_to(ThermalState.PROBING)
        assert thermal_manager.current_state == ThermalState.PROBING
        
        # Mock probe completion in ProbeState
        probe_handler = thermal_manager._state_handlers[ThermalState.PROBING]
        with patch('custom_components.smart_climate.thermal_utils.analyze_drift_data') as mock_analyze:
            mock_analyze.return_value = ProbeResult(
                tau_value=95.0, confidence=0.8, duration=1800, fit_quality=0.9, aborted=False
            )
            
            # Set probe start time to 31 minutes ago to exceed minimum duration
            probe_handler._probe_start_time = datetime.now() - timedelta(minutes=31)
            probe_handler._probe_start_temp = 23.0
            probe_handler._temperature_history = [(datetime.now().timestamp() - i*60, 23.0 + i*0.1) for i in range(10)]
            
            result = probe_handler.execute(thermal_manager, 23.5, (22.0, 24.0))
            assert result == ThermalState.CALIBRATING
        
        # Transition to CALIBRATING
        thermal_manager.transition_to(ThermalState.CALIBRATING)
        assert thermal_manager.current_state == ThermalState.CALIBRATING
        
        # Mock calibration completion
        calibrating_handler = thermal_manager._state_handlers[ThermalState.CALIBRATING]
        calibrating_handler._start_time = datetime.now() - timedelta(hours=1, minutes=1)  # Exceed 1 hour
        
        result = calibrating_handler.execute(thermal_manager, 23.0, (22.0, 24.0))
        assert result == ThermalState.DRIFTING
        
        # Transition to DRIFTING (final state in flow)
        thermal_manager.transition_to(ThermalState.DRIFTING)
        assert thermal_manager.current_state == ThermalState.DRIFTING


class TestProbingDataCollection:
    """Test ProbeState data collection functionality."""
    
    def test_probing_data_collection(self, thermal_manager, mock_probe_result):
        """Test that ProbeState collects temperature data during probing."""
        # Get ProbeState handler
        probe_handler = thermal_manager._state_handlers[ThermalState.PROBING]
        
        # Initialize probe state
        probe_handler._probe_start_time = datetime.now()
        probe_handler._probe_start_temp = 23.0
        probe_handler._temperature_history = []
        
        # Execute multiple times to simulate data collection
        temperatures = [23.0, 23.1, 23.2, 23.3, 23.4]
        for temp in temperatures:
            thermal_manager.current_temp = temp
            probe_handler.execute(thermal_manager, temp, (22.0, 24.0))
        
        # Verify temperature history was collected
        assert len(probe_handler._temperature_history) == len(temperatures)
        
        # Verify data format: (timestamp, temperature)
        for i, (timestamp, temp) in enumerate(probe_handler._temperature_history):
            assert isinstance(timestamp, float)  # Unix timestamp
            assert temp == temperatures[i]
    
    def test_probing_minimum_duration_check(self, thermal_manager):
        """Test that ProbeState respects minimum duration before analysis."""
        probe_handler = thermal_manager._state_handlers[ThermalState.PROBING]
        
        # Set probe start time to just 10 minutes ago (below 30-minute minimum)
        probe_handler._probe_start_time = datetime.now() - timedelta(minutes=10)
        probe_handler._probe_start_temp = 23.0
        probe_handler._temperature_history = [(datetime.now().timestamp(), 23.0)]
        
        # Execute should continue probing (return None)
        result = probe_handler.execute(thermal_manager, 23.1, (22.0, 24.0))
        assert result is None  # Continue probing
    
    def test_probing_insufficient_data_handling(self, thermal_manager):
        """Test ProbeState handling when analysis fails due to insufficient data."""
        probe_handler = thermal_manager._state_handlers[ThermalState.PROBING]
        
        # Set conditions for analysis attempt (sufficient time)
        probe_handler._probe_start_time = datetime.now() - timedelta(minutes=35)
        probe_handler._probe_start_temp = 23.0
        probe_handler._temperature_history = [(datetime.now().timestamp(), 23.0)]  # Minimal data
        
        with patch('custom_components.smart_climate.thermal_utils.analyze_drift_data') as mock_analyze:
            mock_analyze.return_value = None  # Analysis failed
            
            result = probe_handler.execute(thermal_manager, 23.1, (22.0, 24.0))
            assert result is None  # Continue probing when analysis fails


class TestProbingTauUpdate:
    """Test ProbeState tau value updates after successful analysis."""
    
    def test_probing_tau_update(self, thermal_manager, mock_probe_result):
        """Test that ProbeState updates tau values after successful analysis."""
        probe_handler = thermal_manager._state_handlers[ThermalState.PROBING]
        
        # Setup for successful probe completion
        probe_handler._probe_start_time = datetime.now() - timedelta(minutes=35)
        probe_handler._probe_start_temp = 23.0
        probe_handler._temperature_history = [(datetime.now().timestamp() - i*60, 23.0 + i*0.1) for i in range(10)]
        
        with patch('custom_components.smart_climate.thermal_utils.analyze_drift_data') as mock_analyze:
            mock_analyze.return_value = mock_probe_result
            
            # Execute probe completion
            result = probe_handler.execute(thermal_manager, 23.5, (22.0, 24.0))
            
            # Verify transition to CALIBRATING
            assert result == ThermalState.CALIBRATING
            
            # Verify thermal model was updated with probe result
            thermal_manager._model.update_tau.assert_called_once_with(mock_probe_result, True)  # is_cooling=True
    
    def test_probing_persistence_trigger(self, thermal_manager, mock_probe_result, mock_persistence_callback):
        """Test that persistence callback is triggered after tau update."""
        probe_handler = thermal_manager._state_handlers[ThermalState.PROBING]
        
        # Setup for successful probe completion
        probe_handler._probe_start_time = datetime.now() - timedelta(minutes=35)
        probe_handler._probe_start_temp = 23.0
        probe_handler._temperature_history = [(datetime.now().timestamp() - i*60, 23.0 + i*0.1) for i in range(10)]
        
        with patch('custom_components.smart_climate.thermal_utils.analyze_drift_data') as mock_analyze:
            mock_analyze.return_value = mock_probe_result
            
            # Execute probe completion
            probe_handler.execute(thermal_manager, 23.5, (22.0, 24.0))
            
            # Verify persistence callback was triggered
            mock_persistence_callback.assert_called()
    
    def test_probing_heating_mode_detection(self, thermal_manager, mock_probe_result):
        """Test ProbeState correctly detects heating vs cooling mode for tau updates."""
        probe_handler = thermal_manager._state_handlers[ThermalState.PROBING]
        thermal_manager._last_hvac_mode = "heat"
        thermal_manager._setpoint = 23.0
        
        # Setup for successful probe completion
        probe_handler._probe_start_time = datetime.now() - timedelta(minutes=35)
        probe_handler._probe_start_temp = 23.0
        probe_handler._temperature_history = [(datetime.now().timestamp() - i*60, 23.0 - i*0.1) for i in range(10)]
        
        with patch('custom_components.smart_climate.thermal_utils.analyze_drift_data') as mock_analyze:
            mock_analyze.return_value = mock_probe_result
            
            # Execute probe completion
            probe_handler.execute(thermal_manager, 22.5, (22.0, 24.0))
            
            # Verify thermal model was updated with heating mode (is_cooling=False)
            thermal_manager._model.update_tau.assert_called_once_with(mock_probe_result, False)


class TestCalibratingDataCollection:
    """Test CalibratingState data collection functionality."""
    
    def test_calibrating_data_collection(self, thermal_manager):
        """Test that CalibratingState collects temperature data during calibration."""
        calibrating_handler = thermal_manager._state_handlers[ThermalState.CALIBRATING]
        calibrating_handler._start_time = datetime.now()
        calibrating_handler._temperature_history = []
        
        # Execute multiple times to simulate data collection
        temperatures = [22.9, 23.0, 23.1, 22.95, 23.05]
        for temp in temperatures:
            calibrating_handler.execute(thermal_manager, temp, (22.0, 24.0))
        
        # Verify temperature history was collected
        assert len(calibrating_handler._temperature_history) == len(temperatures)
        
        # Verify data format: (timestamp, temperature)
        for i, (timestamp, temp) in enumerate(calibrating_handler._temperature_history):
            assert isinstance(timestamp, float)  # Unix timestamp
            assert temp == temperatures[i]
    
    def test_calibrating_duration_completion(self, thermal_manager):
        """Test CalibratingState transitions after calibration duration complete."""
        calibrating_handler = thermal_manager._state_handlers[ThermalState.CALIBRATING]
        
        # Set start time to exceed calibration duration (1 hour default)
        calibrating_handler._start_time = datetime.now() - timedelta(hours=1, minutes=5)
        calibrating_handler._temperature_history = [(datetime.now().timestamp(), 23.0)]
        
        result = calibrating_handler.execute(thermal_manager, 23.0, (22.0, 24.0))
        assert result == ThermalState.DRIFTING
    
    def test_calibrating_tau_refinement(self, thermal_manager, mock_probe_result):
        """Test CalibratingState can update tau values from collected data."""
        calibrating_handler = thermal_manager._state_handlers[ThermalState.CALIBRATING]
        
        # Setup sufficient data for analysis
        calibrating_handler._start_time = datetime.now() - timedelta(hours=1, minutes=5)
        calibrating_handler._temperature_history = [(datetime.now().timestamp() - i*180, 23.0 + i*0.02) for i in range(15)]
        
        mock_probe_result.confidence = 0.4  # Above 0.3 threshold for calibration
        
        with patch('custom_components.smart_climate.thermal_utils.analyze_drift_data') as mock_analyze:
            mock_analyze.return_value = mock_probe_result
            
            result = calibrating_handler.execute(thermal_manager, 23.0, (22.0, 24.0))
            
            # Should transition to DRIFTING and update tau
            assert result == ThermalState.DRIFTING
            thermal_manager._model.update_tau.assert_called_once_with(mock_probe_result, True)


class TestManualProbeTriggering:
    """Test manual probing trigger functionality."""
    
    def test_manual_probe_trigger(self, thermal_manager):
        """Test force_probing() method works correctly."""
        # Start in DRIFTING state
        thermal_manager._current_state = ThermalState.DRIFTING
        
        # Mock transition_to method to verify it gets called
        with patch.object(thermal_manager, 'transition_to') as mock_transition:
            thermal_manager.force_probing()
            mock_transition.assert_called_once_with(ThermalState.PROBING)
    
    def test_manual_probe_from_different_states(self, thermal_manager):
        """Test force_probing() works from various starting states."""
        test_states = [ThermalState.PRIMING, ThermalState.DRIFTING, ThermalState.CORRECTING, ThermalState.CALIBRATING]
        
        for start_state in test_states:
            thermal_manager._current_state = start_state
            
            with patch.object(thermal_manager, 'transition_to') as mock_transition:
                thermal_manager.force_probing()
                mock_transition.assert_called_once_with(ThermalState.PROBING)
    
    def test_manual_probe_already_probing(self, thermal_manager):
        """Test force_probing() when already in PROBING state."""
        thermal_manager._current_state = ThermalState.PROBING
        
        with patch.object(thermal_manager, 'transition_to') as mock_transition:
            thermal_manager.force_probing()
            # Should not call transition_to when already probing
            mock_transition.assert_not_called()


class TestAutomaticProbeTriggering:
    """Test automatic probing trigger based on confidence."""
    
    @pytest.fixture
    def drifting_handler(self):
        """Get DriftingState handler for testing."""
        return DriftingState()
    
    def test_automatic_probe_trigger(self, thermal_manager, drifting_handler):
        """Test that low confidence triggers automatic probing after 24h interval."""
        thermal_manager._current_state = ThermalState.DRIFTING
        thermal_manager._last_probe_time = datetime.now() - timedelta(hours=25)  # Over 24h ago
        
        # Mock low confidence from thermal model
        thermal_manager._model.get_confidence.return_value = 0.2  # Below 0.3 threshold
        
        with patch.object(thermal_manager, 'can_auto_probe', return_value=True):
            result = drifting_handler.execute(thermal_manager, 23.0, (22.0, 24.0))
            assert result == ThermalState.PROBING
    
    def test_automatic_probe_confidence_threshold(self, thermal_manager, drifting_handler):
        """Test that automatic probe respects confidence threshold."""
        thermal_manager._current_state = ThermalState.DRIFTING
        thermal_manager._last_probe_time = datetime.now() - timedelta(hours=25)
        
        # Mock high confidence - should not trigger probing
        thermal_manager._model.get_confidence.return_value = 0.8  # Above 0.3 threshold
        
        with patch.object(thermal_manager, 'can_auto_probe', return_value=True):
            result = drifting_handler.execute(thermal_manager, 23.0, (22.0, 24.0))
            assert result is None  # Should not trigger probing
    
    def test_automatic_probe_minimum_interval(self, thermal_manager, drifting_handler):
        """Test that automatic probe respects 24-hour minimum interval."""
        thermal_manager._current_state = ThermalState.DRIFTING
        thermal_manager._last_probe_time = datetime.now() - timedelta(hours=12)  # Only 12h ago
        
        # Mock low confidence
        thermal_manager._model.get_confidence.return_value = 0.2
        
        with patch.object(thermal_manager, 'can_auto_probe', return_value=False):
            result = drifting_handler.execute(thermal_manager, 23.0, (22.0, 24.0))
            assert result is None  # Should not trigger probing due to interval


class TestProbeButtonAvailability:
    """Test probe button availability and state management."""
    
    def test_probe_button_disabled_during_probing(self, thermal_manager):
        """Test that probe button is disabled/unavailable during PROBING state."""
        # This would typically be tested in button.py tests, but we verify the logic here
        thermal_manager._current_state = ThermalState.PROBING
        
        # Button should check if already probing before calling force_probing
        with patch.object(thermal_manager, 'transition_to') as mock_transition:
            thermal_manager.force_probing()
            mock_transition.assert_not_called()  # Should not transition when already probing
    
    def test_probe_button_available_other_states(self, thermal_manager):
        """Test that probe button is available in non-probing states."""
        available_states = [ThermalState.PRIMING, ThermalState.DRIFTING, ThermalState.CORRECTING, ThermalState.CALIBRATING]
        
        for state in available_states:
            thermal_manager._current_state = state
            
            with patch.object(thermal_manager, 'transition_to') as mock_transition:
                thermal_manager.force_probing()
                mock_transition.assert_called_once_with(ThermalState.PROBING)
                mock_transition.reset_mock()


class TestPersistenceAfterTauUpdate:
    """Test persistence callback triggering after tau updates."""
    
    def test_persistence_after_probe_tau_update(self, thermal_manager, mock_probe_result, mock_persistence_callback):
        """Test persistence callback is triggered after ProbeState tau update."""
        probe_handler = thermal_manager._state_handlers[ThermalState.PROBING]
        probe_handler._probe_start_time = datetime.now() - timedelta(minutes=35)
        probe_handler._probe_start_temp = 23.0
        probe_handler._temperature_history = [(datetime.now().timestamp() - i*60, 23.0 + i*0.1) for i in range(10)]
        
        with patch('custom_components.smart_climate.thermal_utils.analyze_drift_data') as mock_analyze:
            mock_analyze.return_value = mock_probe_result
            
            probe_handler.execute(thermal_manager, 23.5, (22.0, 24.0))
            
            # Verify persistence was triggered after tau update
            mock_persistence_callback.assert_called()
    
    def test_persistence_after_calibration_tau_update(self, thermal_manager, mock_probe_result, mock_persistence_callback):
        """Test persistence callback is triggered after CalibratingState tau update."""
        calibrating_handler = thermal_manager._state_handlers[ThermalState.CALIBRATING]
        calibrating_handler._start_time = datetime.now() - timedelta(hours=1, minutes=5)
        calibrating_handler._temperature_history = [(datetime.now().timestamp() - i*180, 23.0 + i*0.02) for i in range(15)]
        
        mock_probe_result.confidence = 0.4  # Above threshold
        
        with patch('custom_components.smart_climate.thermal_utils.analyze_drift_data') as mock_analyze:
            mock_analyze.return_value = mock_probe_result
            
            calibrating_handler.execute(thermal_manager, 23.0, (22.0, 24.0))
            
            # Verify persistence was triggered after tau update
            mock_persistence_callback.assert_called()
    
    def test_persistence_not_triggered_without_tau_update(self, thermal_manager, mock_persistence_callback):
        """Test persistence callback not triggered when no tau update occurs."""
        # Test ProbeState with analysis failure
        probe_handler = thermal_manager._state_handlers[ThermalState.PROBING]
        probe_handler._probe_start_time = datetime.now() - timedelta(minutes=35)
        probe_handler._probe_start_temp = 23.0
        probe_handler._temperature_history = [(datetime.now().timestamp(), 23.0)]
        
        with patch('custom_components.smart_climate.thermal_utils.analyze_drift_data') as mock_analyze:
            mock_analyze.return_value = None  # Analysis failed
            
            # Reset mock to clear any previous calls
            mock_persistence_callback.reset_mock()
            
            probe_handler.execute(thermal_manager, 23.1, (22.0, 24.0))
            
            # Should not trigger persistence when no tau update
            mock_persistence_callback.assert_not_called()
    
    def test_persistence_error_handling(self, thermal_manager, mock_probe_result):
        """Test graceful handling of persistence callback errors."""
        # Setup persistence callback that raises exception
        def failing_callback():
            raise Exception("Persistence failed")
        
        thermal_manager._persistence_callback = failing_callback
        
        probe_handler = thermal_manager._state_handlers[ThermalState.PROBING]
        probe_handler._probe_start_time = datetime.now() - timedelta(minutes=35)
        probe_handler._probe_start_temp = 23.0
        probe_handler._temperature_history = [(datetime.now().timestamp() - i*60, 23.0 + i*0.1) for i in range(10)]
        
        with patch('custom_components.smart_climate.thermal_utils.analyze_drift_data') as mock_analyze:
            mock_analyze.return_value = mock_probe_result
            
            # Should not raise exception even if persistence fails
            result = probe_handler.execute(thermal_manager, 23.5, (22.0, 24.0))
            assert result == ThermalState.CALIBRATING  # Should still transition normally


# Integration test combining multiple features
class TestThermalStateFlowIntegration:
    """Integration tests for complete thermal state flow functionality."""
    
    def test_complete_probe_cycle_with_persistence(self, thermal_manager, mock_probe_result, mock_persistence_callback):
        """Test complete probe cycle from trigger to completion with persistence."""
        # Start in DRIFTING with low confidence to trigger automatic probe
        thermal_manager._current_state = ThermalState.DRIFTING
        thermal_manager._last_probe_time = datetime.now() - timedelta(hours=25)
        thermal_manager._model.get_confidence.return_value = 0.2
        
        # Get handlers
        drifting_handler = thermal_manager._state_handlers[ThermalState.DRIFTING]
        probe_handler = thermal_manager._state_handlers[ThermalState.PROBING]
        
        # 1. Trigger automatic probe from DRIFTING
        with patch.object(thermal_manager, 'can_auto_probe', return_value=True):
            result = drifting_handler.execute(thermal_manager, 23.0, (22.0, 24.0))
            assert result == ThermalState.PROBING
        
        # 2. Transition to PROBING
        thermal_manager.transition_to(ThermalState.PROBING)
        
        # 3. Simulate probe data collection and completion
        probe_handler._probe_start_time = datetime.now() - timedelta(minutes=35)
        probe_handler._probe_start_temp = 23.0
        probe_handler._temperature_history = [(datetime.now().timestamp() - i*60, 23.0 + i*0.1) for i in range(15)]
        
        with patch('custom_components.smart_climate.thermal_utils.analyze_drift_data') as mock_analyze:
            mock_analyze.return_value = mock_probe_result
            
            result = probe_handler.execute(thermal_manager, 23.8, (22.0, 24.0))
            
            # 4. Verify complete cycle
            assert result == ThermalState.CALIBRATING
            thermal_manager._model.update_tau.assert_called_once_with(mock_probe_result, True)
            mock_persistence_callback.assert_called()
            assert hasattr(thermal_manager, 'last_probe_result')
            assert thermal_manager.last_probe_result == mock_probe_result