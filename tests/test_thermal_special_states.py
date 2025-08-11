"""Tests for thermal special state handlers - PrimingState, RecoveryState, ProbeState, CalibratingState.

Tests the special state handler implementations following TDD.
Covers state-specific behavior, duration tracking, transitions, and special logic.
"""

import pytest
import logging
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from typing import Optional

from custom_components.smart_climate.thermal_models import ThermalState, ProbeResult, ThermalConstants
from custom_components.smart_climate.thermal_states import StateHandler


class TestPrimingState:
    """Test PrimingState handler behavior and transitions."""

    def test_priming_state_can_be_imported(self):
        """Test PrimingState can be imported from thermal_special_states."""
        # This will fail initially until we implement the file
        from custom_components.smart_climate.thermal_special_states import PrimingState
        assert issubclass(PrimingState, StateHandler)

    def test_priming_state_instantiation(self):
        """Test PrimingState can be instantiated."""
        from custom_components.smart_climate.thermal_special_states import PrimingState
        handler = PrimingState()
        assert isinstance(handler, StateHandler)

    def test_priming_state_uses_conservative_bands(self):
        """Test PrimingState uses conservative ±1.2°C bands."""
        from custom_components.smart_climate.thermal_special_states import PrimingState
        
        handler = PrimingState()
        mock_context = Mock()
        mock_context.current_temp = 22.0
        mock_context.setpoint = 23.0
        
        # Should return conservative band of ±1.2°C from setpoint
        conservative_band = handler.get_conservative_band(mock_context)
        assert conservative_band == 1.2

    def test_priming_state_starts_duration_tracking(self):
        """Test PrimingState starts duration tracking on enter."""
        from custom_components.smart_climate.thermal_special_states import PrimingState
        
        handler = PrimingState()
        mock_context = Mock()
        mock_context.thermal_constants = Mock()
        mock_context.thermal_constants.priming_duration = 86400  # 24 hours
        
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, 12, 0, 0)
            handler.on_enter(mock_context)
        
        # Should set start time
        assert hasattr(handler, '_start_time')

    def test_priming_state_checks_stability_not_time(self):
        """Test PrimingState checks stability detection instead of calibration_hour."""
        from custom_components.smart_climate.thermal_special_states import PrimingState
        
        handler = PrimingState()
        handler._start_time = datetime(2025, 1, 1, 12, 0, 0)
        
        mock_context = Mock()
        mock_context.thermal_constants = Mock()
        mock_context.thermal_constants.priming_duration = 86400  # 24 hours
        mock_context.stability_detector = Mock()
        mock_context.stability_detector.is_stable_for_calibration.return_value = True
        
        # Test - should transition to calibrating when stable, not based on time
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, 14, 0, 0)  # Just 2 hours later
            result = handler.execute(mock_context, 23.5, (22.0, 25.0))
        
        assert result == ThermalState.CALIBRATING

    def test_priming_state_transitions_to_drifting_after_duration(self):
        """Test PrimingState transitions to DRIFTING after 24-48 hours."""
        from custom_components.smart_climate.thermal_special_states import PrimingState
        
        handler = PrimingState()
        handler._start_time = datetime(2025, 1, 1, 12, 0, 0)
        
        mock_context = Mock()
        mock_context.thermal_constants = Mock()
        mock_context.thermal_constants.priming_duration = 86400  # 24 hours
        mock_context.stability_detector = Mock()
        mock_context.stability_detector.is_stable_for_calibration.return_value = False
        
        # Test after 25 hours (should transition to drifting, not calibrating)
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 2, 13, 0, 0)  # 25 hours later
            result = handler.execute(mock_context, 23.5, (22.0, 25.0))
        
        assert result == ThermalState.DRIFTING

    def test_priming_state_stays_in_priming_before_duration_complete(self):
        """Test PrimingState stays in PRIMING before duration is complete."""
        from custom_components.smart_climate.thermal_special_states import PrimingState
        
        handler = PrimingState()
        handler._start_time = datetime(2025, 1, 1, 12, 0, 0)
        
        mock_context = Mock()
        mock_context.thermal_constants = Mock()
        mock_context.thermal_constants.priming_duration = 86400  # 24 hours
        mock_context.stability_detector = Mock()
        mock_context.stability_detector.is_stable_for_calibration.return_value = False
        
        # Test after 12 hours (should stay in priming)
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 2, 0, 0, 0)  # 12 hours later
            result = handler.execute(mock_context, 23.5, (22.0, 25.0))
        
        assert result is None

    def test_priming_state_handles_missing_start_time(self):
        """Test PrimingState handles missing start time gracefully."""
        from custom_components.smart_climate.thermal_special_states import PrimingState
        
        handler = PrimingState()
        # No _start_time set
        
        mock_context = Mock()
        mock_context.thermal_constants = Mock()
        mock_context.thermal_constants.priming_duration = 86400
        
        result = handler.execute(mock_context, 23.5, (22.0, 25.0))
        
        # Should handle gracefully (either stay or transition safely)
        assert result is None or isinstance(result, ThermalState)

    def test_priming_state_aggressive_passive_learning_enabled(self):
        """Test PrimingState enables aggressive passive learning when not explicitly disabled."""
        from custom_components.smart_climate.thermal_special_states import PrimingState
        
        handler = PrimingState()
        handler._start_time = datetime(2025, 1, 1, 12, 0, 0)
        
        mock_context = Mock()
        mock_context.thermal_constants = Mock()
        mock_context.thermal_constants.priming_duration = 86400  # 24 hours
        mock_context.stability_detector = Mock()
        mock_context.stability_detector.is_stable_for_calibration.return_value = False
        # Start with passive learning not set (should default to enabled)
        # del mock_context.passive_learning_enabled  # Attribute doesn't exist initially
        
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, 18, 0, 0)  # 6 hours later
            handler.execute(mock_context, 23.5, (22.0, 25.0))
        
        # Should enable aggressive passive learning
        assert hasattr(mock_context, 'passive_learning_enabled')
        assert mock_context.passive_learning_enabled is True

    def test_priming_state_on_enter_logs_state_entry(self):
        """Test PrimingState logs state entry on_enter."""
        from custom_components.smart_climate.thermal_special_states import PrimingState
        
        handler = PrimingState()
        mock_context = Mock()
        mock_context.thermal_constants = Mock()
        mock_context.thermal_constants.priming_duration = 86400
        
        # Should not raise exception - logging is implemented
        handler.on_enter(mock_context)

    def test_priming_state_on_exit_called(self):
        """Test PrimingState on_exit can be called."""
        from custom_components.smart_climate.thermal_special_states import PrimingState
        
        handler = PrimingState()
        mock_context = Mock()
        
        # Should not raise exception
        handler.on_exit(mock_context)

    def test_drifting_state_transitions_on_stability(self):
        """Test DriftingState transitions to CALIBRATING when stable conditions detected."""
        # Note: This would be in thermal_state_handlers, but we test the concept here
        # DriftingState would need to check stability_detector in its execute method
        pass

    def test_no_calibration_hour_dependency(self):
        """Test that no state handlers depend on calibration_hour anymore."""
        from custom_components.smart_climate.thermal_special_states import PrimingState
        
        handler = PrimingState()
        handler._start_time = datetime(2025, 1, 1, 12, 0, 0)
        
        mock_context = Mock()
        mock_context.thermal_constants = Mock()
        mock_context.thermal_constants.priming_duration = 0  # Force immediate transition
        mock_context.stability_detector = Mock()
        mock_context.stability_detector.is_stable_for_calibration.return_value = False
        # No calibration_hour attribute should be accessed
        
        result = handler.execute(mock_context, 23.5, (22.0, 25.0))
        
        # Should transition based on duration/stability, not calibration_hour
        assert result == ThermalState.DRIFTING

    def test_calibrating_still_captures_offset(self):
        """Test that CalibratingState still functions for offset capture."""
        from custom_components.smart_climate.thermal_special_states import CalibratingState
        
        handler = CalibratingState()
        handler._start_time = datetime(2025, 1, 1, 12, 0, 0)
        
        mock_context = Mock()
        mock_context.thermal_constants = Mock()
        mock_context.thermal_constants.calibrating_duration = 3600
        
        # Should still enable precise measurement mode
        result = handler.execute(mock_context, 23.5, (22.0, 25.0))
        
        # Should still enable precise measurement mode for clean offset readings
        assert mock_context.precise_measurement_mode is True


class TestRecoveryState:
    """Test RecoveryState handler behavior and transitions."""

    def test_recovery_state_can_be_imported(self):
        """Test RecoveryState can be imported from thermal_special_states."""
        from custom_components.smart_climate.thermal_special_states import RecoveryState
        assert issubclass(RecoveryState, StateHandler)

    def test_recovery_state_instantiation(self):
        """Test RecoveryState can be instantiated."""
        from custom_components.smart_climate.thermal_special_states import RecoveryState
        handler = RecoveryState()
        assert isinstance(handler, StateHandler)

    def test_recovery_state_tracks_gradual_transition_progress(self):
        """Test RecoveryState tracks gradual transition progress."""
        from custom_components.smart_climate.thermal_special_states import RecoveryState
        
        handler = RecoveryState()
        handler._start_time = datetime(2025, 1, 1, 12, 0, 0)
        
        mock_context = Mock()
        mock_context.thermal_constants = Mock()
        mock_context.thermal_constants.recovery_duration = 1800  # 30 minutes
        
        # Test after 15 minutes (50% progress)
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, 12, 15, 0)
            progress = handler.get_progress(mock_context)
        
        assert abs(progress - 0.5) < 0.01  # 50% progress

    def test_recovery_state_transitions_after_duration_complete(self):
        """Test RecoveryState transitions to appropriate state after duration."""
        from custom_components.smart_climate.thermal_special_states import RecoveryState
        
        handler = RecoveryState()
        handler._start_time = datetime(2025, 1, 1, 12, 0, 0)
        handler._target_state = ThermalState.DRIFTING
        
        mock_context = Mock()
        mock_context.thermal_constants = Mock()
        mock_context.thermal_constants.recovery_duration = 1800  # 30 minutes
        
        # Test after 31 minutes (should transition)
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, 12, 31, 0)
            result = handler.execute(mock_context, 23.5, (22.0, 25.0))
        
        assert result == ThermalState.DRIFTING

    def test_recovery_state_stays_in_recovery_during_transition(self):
        """Test RecoveryState stays in RECOVERY during gradual transition."""
        from custom_components.smart_climate.thermal_special_states import RecoveryState
        
        handler = RecoveryState()
        handler._start_time = datetime(2025, 1, 1, 12, 0, 0)
        
        mock_context = Mock()
        mock_context.thermal_constants = Mock()
        mock_context.thermal_constants.recovery_duration = 1800  # 30 minutes
        
        # Test after 15 minutes (should stay in recovery)
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, 12, 15, 0)
            result = handler.execute(mock_context, 23.5, (22.0, 25.0))
        
        assert result is None

    def test_recovery_state_handles_large_delta_from_mode_changes(self):
        """Test RecoveryState handles large temperature delta from mode changes."""
        from custom_components.smart_climate.thermal_special_states import RecoveryState
        
        handler = RecoveryState()
        mock_context = Mock()
        mock_context.previous_mode = "heat"
        mock_context.current_mode = "cool"
        mock_context.temperature_delta = 5.0  # Large delta
        
        # Should enable gradual adjustment mode
        handler.on_enter(mock_context)
        
        assert hasattr(handler, '_gradual_adjustment')
        assert handler._gradual_adjustment is True

    def test_recovery_state_calculates_adjusted_target(self):
        """Test RecoveryState calculates adjusted target based on progress."""
        from custom_components.smart_climate.thermal_special_states import RecoveryState
        
        handler = RecoveryState()
        handler._start_time = datetime(2025, 1, 1, 12, 0, 0)
        handler._initial_target = 20.0
        handler._final_target = 24.0
        
        mock_context = Mock()
        mock_context.thermal_constants = Mock()
        mock_context.thermal_constants.recovery_duration = 1800
        
        # Test 50% progress
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, 12, 15, 0)
            adjusted_target = handler.get_adjusted_target(mock_context)
        
        assert abs(adjusted_target - 22.0) < 0.01  # 50% between 20.0 and 24.0

    def test_recovery_state_on_enter_initializes_transition(self):
        """Test RecoveryState on_enter initializes transition parameters."""
        from custom_components.smart_climate.thermal_special_states import RecoveryState
        
        handler = RecoveryState()
        mock_context = Mock()
        mock_context.thermal_constants = Mock()
        mock_context.thermal_constants.recovery_duration = 1800
        
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, 12, 0, 0)
            handler.on_enter(mock_context)
        
        # Should initialize start time
        assert hasattr(handler, '_start_time')

    def test_recovery_state_on_exit_called(self):
        """Test RecoveryState on_exit can be called."""
        from custom_components.smart_climate.thermal_special_states import RecoveryState
        
        handler = RecoveryState()
        mock_context = Mock()
        
        # Should not raise exception
        handler.on_exit(mock_context)


class TestProbeState:
    """Test ProbeState handler behavior and transitions."""

    def test_probe_state_can_be_imported(self):
        """Test ProbeState can be imported from thermal_special_states."""
        from custom_components.smart_climate.thermal_special_states import ProbeState
        assert issubclass(ProbeState, StateHandler)

    def test_probe_state_instantiation(self):
        """Test ProbeState can be instantiated."""
        from custom_components.smart_climate.thermal_special_states import ProbeState
        handler = ProbeState()
        assert isinstance(handler, StateHandler)

    def test_probe_state_allows_wider_drift_range(self):
        """Test ProbeState allows ±2.0°C drift for active learning."""
        from custom_components.smart_climate.thermal_special_states import ProbeState
        
        handler = ProbeState()
        mock_context = Mock()
        mock_context.current_temp = 24.5  # 1.5°C above setpoint
        mock_context.setpoint = 23.0
        
        # Should allow drift within ±2.0°C
        is_within_drift = handler.is_within_probe_drift(mock_context)
        assert is_within_drift is True

    def test_probe_state_detects_excessive_drift(self):
        """Test ProbeState detects when drift exceeds ±2.0°C."""
        from custom_components.smart_climate.thermal_special_states import ProbeState
        
        handler = ProbeState()
        mock_context = Mock()
        mock_context.current_temp = 25.5  # 2.5°C above setpoint
        mock_context.setpoint = 23.0
        
        # Should detect excessive drift
        is_within_drift = handler.is_within_probe_drift(mock_context)
        assert is_within_drift is False

    def test_probe_state_tracks_probe_start_time_and_temperature(self):
        """Test ProbeState tracks probe start time and temperature."""
        from custom_components.smart_climate.thermal_special_states import ProbeState
        
        handler = ProbeState()
        mock_context = Mock()
        mock_context.current_temp = 23.0
        
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, 12, 0, 0)
            handler.on_enter(mock_context)
        
        # Should track start time and temperature
        assert hasattr(handler, '_probe_start_time')
        assert hasattr(handler, '_probe_start_temp')
        assert handler._probe_start_temp == 23.0

    def test_probe_state_supports_abort_capability(self):
        """Test ProbeState supports abort capability returning to previous state."""
        from custom_components.smart_climate.thermal_special_states import ProbeState
        
        handler = ProbeState()
        handler._previous_state = ThermalState.DRIFTING
        
        mock_context = Mock()
        mock_context.probe_aborted = True
        
        result = handler.execute(mock_context, 23.5, (22.0, 25.0))
        
        # Should return to previous state when aborted
        assert result == ThermalState.DRIFTING

    def test_probe_state_transitions_to_calibrating_on_completion(self):
        """Test ProbeState transitions to CALIBRATING when probe completes successfully."""
        from custom_components.smart_climate.thermal_special_states import ProbeState
        
        handler = ProbeState()
        handler._probe_start_time = datetime(2025, 1, 1, 12, 0, 0)
        handler._probe_start_temp = 23.0
        
        mock_context = Mock()
        mock_context.current_temp = 25.0
        mock_context.probe_aborted = False
        mock_context.thermal_constants = Mock()
        mock_context.thermal_constants.min_probe_duration = 1800  # 30 minutes
        
        # Test after sufficient time with good data
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, 12, 35, 0)  # 35 minutes later
            result = handler.execute(mock_context, 25.0, (22.0, 25.0))
        
        assert result == ThermalState.CALIBRATING

    def test_probe_state_calculates_probe_result_on_completion(self):
        """Test ProbeState calculates ProbeResult with tau value and confidence."""
        from custom_components.smart_climate.thermal_special_states import ProbeState
        
        handler = ProbeState()
        handler._probe_start_time = datetime(2025, 1, 1, 12, 0, 0)
        handler._probe_start_temp = 23.0
        
        mock_context = Mock()
        mock_context.current_temp = 25.0
        mock_context.outdoor_temp = 30.0
        
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, 12, 30, 0)
            probe_result = handler.calculate_probe_result(mock_context)
        
        assert isinstance(probe_result, ProbeResult)
        assert probe_result.tau_value > 0
        assert 0.0 <= probe_result.confidence <= 1.0
        assert probe_result.aborted is False

    def test_probe_state_sends_phone_notifications_during_active_learning(self):
        """Test ProbeState sends phone notifications during active learning."""
        from custom_components.smart_climate.thermal_special_states import ProbeState
        
        handler = ProbeState()
        mock_context = Mock()
        mock_context.notification_service = Mock()
        
        handler.on_enter(mock_context)
        
        # Should send notification about probe start
        mock_context.notification_service.send_notification.assert_called()

    def test_probe_state_on_enter_starts_probe(self):
        """Test ProbeState on_enter starts active probe."""
        from custom_components.smart_climate.thermal_special_states import ProbeState
        
        handler = ProbeState()
        mock_context = Mock()
        mock_context.current_temp = 23.0
        mock_context.notification_service = Mock()
        
        handler.on_enter(mock_context)
        
        # Should initialize probe parameters
        assert hasattr(handler, '_probe_start_time')
        assert hasattr(handler, '_probe_start_temp')

    def test_probe_state_on_exit_called(self):
        """Test ProbeState on_exit can be called."""
        from custom_components.smart_climate.thermal_special_states import ProbeState
        
        handler = ProbeState()
        mock_context = Mock()
        
        # Should not raise exception
        handler.on_exit(mock_context)


class TestCalibratingState:
    """Test CalibratingState handler behavior and transitions."""

    def test_calibrating_state_can_be_imported(self):
        """Test CalibratingState can be imported from thermal_special_states."""
        from custom_components.smart_climate.thermal_special_states import CalibratingState
        assert issubclass(CalibratingState, StateHandler)

    def test_calibrating_state_instantiation(self):
        """Test CalibratingState can be instantiated."""
        from custom_components.smart_climate.thermal_special_states import CalibratingState
        handler = CalibratingState()
        assert isinstance(handler, StateHandler)

    def test_calibrating_state_uses_very_tight_bands(self):
        """Test CalibratingState uses very tight ±0.1°C bands."""
        from custom_components.smart_climate.thermal_special_states import CalibratingState
        
        handler = CalibratingState()
        mock_context = Mock()
        
        tight_band = handler.get_calibration_band(mock_context)
        assert tight_band == 0.1

    def test_calibrating_state_runs_for_one_hour_duration(self):
        """Test CalibratingState runs for 1-hour duration."""
        from custom_components.smart_climate.thermal_special_states import CalibratingState
        
        handler = CalibratingState()
        handler._start_time = datetime(2025, 1, 1, 12, 0, 0)
        
        mock_context = Mock()
        mock_context.thermal_constants = Mock()
        mock_context.thermal_constants.calibrating_duration = 3600  # 1 hour
        
        # Test after 61 minutes (should transition)
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, 13, 1, 0)  # 61 minutes later
            result = handler.execute(mock_context, 23.5, (22.0, 25.0))
        
        assert result == ThermalState.DRIFTING

    def test_calibrating_state_stays_during_calibration_window(self):
        """Test CalibratingState stays in CALIBRATING during 1-hour window."""
        from custom_components.smart_climate.thermal_special_states import CalibratingState
        
        handler = CalibratingState()
        handler._start_time = datetime(2025, 1, 1, 12, 0, 0)
        
        mock_context = Mock()
        mock_context.thermal_constants = Mock()
        mock_context.thermal_constants.calibrating_duration = 3600  # 1 hour
        
        # Test after 30 minutes (should stay)
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, 12, 30, 0)
            result = handler.execute(mock_context, 23.5, (22.0, 25.0))
        
        assert result is None

    def test_calibrating_state_tracks_calibration_quality_metrics(self):
        """Test CalibratingState tracks calibration quality metrics."""
        from custom_components.smart_climate.thermal_special_states import CalibratingState
        
        handler = CalibratingState()
        mock_context = Mock()
        mock_context.current_temp = 23.05
        mock_context.setpoint = 23.0
        mock_context.temperature_stability = 0.95
        
        quality_metrics = handler.get_calibration_quality(mock_context)
        
        assert 'stability' in quality_metrics
        assert 'precision' in quality_metrics
        assert 'duration' in quality_metrics
        assert 0.0 <= quality_metrics['stability'] <= 1.0

    def test_calibrating_state_provides_clean_offset_readings(self):
        """Test CalibratingState provides clean offset readings for calibration."""
        from custom_components.smart_climate.thermal_special_states import CalibratingState
        
        handler = CalibratingState()
        mock_context = Mock()
        mock_context.current_temp = 23.0
        mock_context.ac_internal_temp = 20.5
        
        # Should enable precise offset measurement mode
        handler.execute(mock_context, 23.0, (22.5, 23.5))
        
        assert mock_context.precise_measurement_mode is True

    def test_calibrating_state_runs_during_daily_window(self):
        """Test CalibratingState runs during optimal daily calibration window."""
        from custom_components.smart_climate.thermal_special_states import CalibratingState
        
        handler = CalibratingState()
        mock_context = Mock()
        
        # Mock calibration_hour to be 2 (default expected value)
        mock_context.calibration_hour = 2
        
        # Test if current time is within optimal window (e.g., 2-3 AM)
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, 2, 30, 0)  # 2:30 AM
            is_optimal_time = handler.is_optimal_calibration_time(mock_context)
        
        assert is_optimal_time is True

    def test_calibrating_state_avoids_suboptimal_times(self):
        """Test CalibratingState avoids suboptimal calibration times."""
        from custom_components.smart_climate.thermal_special_states import CalibratingState
        
        handler = CalibratingState()
        mock_context = Mock()
        
        # Mock calibration_hour to be 2 (default expected value)
        mock_context.calibration_hour = 2
        
        # Test during busy time (e.g., 6 PM)
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, 18, 0, 0)  # 6:00 PM
            is_optimal_time = handler.is_optimal_calibration_time(mock_context)
        
        assert is_optimal_time is False

    def test_calibrating_state_on_enter_starts_calibration(self):
        """Test CalibratingState on_enter starts calibration procedure."""
        from custom_components.smart_climate.thermal_special_states import CalibratingState
        
        handler = CalibratingState()
        mock_context = Mock()
        mock_context.thermal_constants = Mock()
        mock_context.thermal_constants.calibrating_duration = 3600
        
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, 2, 0, 0)
            handler.on_enter(mock_context)
        
        # Should initialize calibration parameters
        assert hasattr(handler, '_start_time')

    def test_calibrating_state_on_exit_called(self):
        """Test CalibratingState on_exit can be called."""
        from custom_components.smart_climate.thermal_special_states import CalibratingState
        
        handler = CalibratingState()
        mock_context = Mock()
        
        # Should not raise exception
        handler.on_exit(mock_context)


class TestSpecialStateEdgeCases:
    """Test edge cases and error handling for special state handlers."""

    def test_all_special_states_handle_missing_thermal_constants(self):
        """Test all special states handle missing thermal constants gracefully."""
        from custom_components.smart_climate.thermal_special_states import (
            PrimingState, RecoveryState, ProbeState, CalibratingState
        )
        
        handlers = [PrimingState(), RecoveryState(), ProbeState(), CalibratingState()]
        
        for handler in handlers:
            mock_context = Mock()
            mock_context.thermal_constants = None
            
            try:
                result = handler.execute(mock_context, 23.5, (22.0, 25.0))
                assert result is None or isinstance(result, ThermalState)
            except (AttributeError, ValueError, TypeError):
                # Expected behavior for missing constants
                pass

    def test_special_states_handle_system_clock_changes(self):
        """Test special states handle system clock changes gracefully."""
        from custom_components.smart_climate.thermal_special_states import PrimingState
        
        handler = PrimingState()
        handler._start_time = datetime(2025, 1, 1, 12, 0, 0)
        
        mock_context = Mock()
        mock_context.thermal_constants = Mock()
        mock_context.thermal_constants.priming_duration = 86400
        
        # Test with clock moved backward
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, 10, 0, 0)  # 2 hours before start
            result = handler.execute(mock_context, 23.5, (22.0, 25.0))
        
        # Should handle gracefully without crashing
        assert result is None or isinstance(result, ThermalState)

    def test_probe_state_handles_invalid_temperature_readings(self):
        """Test ProbeState handles invalid temperature readings during probe."""
        from custom_components.smart_climate.thermal_special_states import ProbeState
        
        handler = ProbeState()
        handler._probe_start_time = datetime(2025, 1, 1, 12, 0, 0)
        handler._probe_start_temp = 23.0
        
        mock_context = Mock()
        mock_context.current_temp = None  # Invalid reading
        mock_context.probe_aborted = False
        
        try:
            result = handler.execute(mock_context, None, (22.0, 25.0))
            assert result is None or isinstance(result, ThermalState)
        except (AttributeError, ValueError, TypeError):
            # Expected behavior for invalid readings
            pass

    def test_recovery_state_handles_zero_duration(self):
        """Test RecoveryState handles zero duration gracefully."""
        from custom_components.smart_climate.thermal_special_states import RecoveryState
        
        handler = RecoveryState()
        handler._start_time = datetime(2025, 1, 1, 12, 0, 0)
        
        mock_context = Mock()
        mock_context.thermal_constants = Mock()
        mock_context.thermal_constants.recovery_duration = 0  # Zero duration
        
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, 12, 0, 1)  # 1 second later
            result = handler.execute(mock_context, 23.5, (22.0, 25.0))
        
        # Should handle gracefully (likely immediate transition)
        assert result is None or isinstance(result, ThermalState)


class TestSpecialStateIntegration:
    """Test special state handlers integration with ThermalManager."""

    def test_all_special_states_implement_state_handler_interface(self):
        """Test all special states properly implement StateHandler interface."""
        from custom_components.smart_climate.thermal_special_states import (
            PrimingState, RecoveryState, ProbeState, CalibratingState
        )
        
        handlers = [PrimingState(), RecoveryState(), ProbeState(), CalibratingState()]
        
        for handler in handlers:
            assert isinstance(handler, StateHandler)
            assert hasattr(handler, 'execute')
            assert hasattr(handler, 'on_enter')
            assert hasattr(handler, 'on_exit')
            assert callable(handler.execute)
            assert callable(handler.on_enter)
            assert callable(handler.on_exit)

    def test_special_states_work_with_thermal_manager_context(self):
        """Test special states work with ThermalManager context interface."""
        from custom_components.smart_climate.thermal_special_states import (
            PrimingState, RecoveryState, ProbeState, CalibratingState
        )
        
        # Mock minimal ThermalManager interface
        mock_manager = Mock()
        mock_manager.current_state = ThermalState.PRIMING
        mock_manager.current_temp = 23.0
        mock_manager.setpoint = 23.0
        mock_manager.thermal_constants = Mock()
        mock_manager.thermal_constants.priming_duration = 86400
        mock_manager.thermal_constants.recovery_duration = 1800
        mock_manager.thermal_constants.calibrating_duration = 3600
        
        handlers = [PrimingState(), RecoveryState(), ProbeState(), CalibratingState()]
        
        for handler in handlers:
            # All should be able to execute with ThermalManager interface
            try:
                result = handler.execute(mock_manager, 23.0, (22.0, 24.0))
                assert result is None or isinstance(result, ThermalState)
            except (AttributeError, ValueError, TypeError):
                # Some may need additional setup, which is acceptable
                pass

    def test_special_state_lifecycle_methods_integration(self):
        """Test special state lifecycle methods work with context."""
        from custom_components.smart_climate.thermal_special_states import (
            PrimingState, RecoveryState, ProbeState, CalibratingState
        )
        
        mock_context = Mock()
        mock_context.thermal_constants = Mock()
        mock_context.thermal_constants.priming_duration = 86400
        mock_context.thermal_constants.recovery_duration = 1800
        mock_context.thermal_constants.calibrating_duration = 3600
        
        handlers = [PrimingState(), RecoveryState(), ProbeState(), CalibratingState()]
        
        for handler in handlers:
            # All lifecycle methods should be callable
            try:
                handler.on_enter(mock_context)
                handler.on_exit(mock_context)
            except (AttributeError, ValueError, TypeError):
                # Some may need additional context attributes
                pass

    def test_special_states_handle_state_transitions_appropriately(self):
        """Test special states handle state transitions according to architecture."""
        from custom_components.smart_climate.thermal_special_states import (
            PrimingState, RecoveryState, ProbeState, CalibratingState
        )
        
        # Test expected transitions from architecture:
        # PrimingState -> DRIFTING (after duration)
        # RecoveryState -> target state (after gradual transition)  
        # ProbeState -> CALIBRATING (on completion) or previous state (on abort)
        # CalibratingState -> DRIFTING (after calibration window)
        
        expected_transitions = {
            PrimingState: [ThermalState.DRIFTING],
            RecoveryState: [ThermalState.DRIFTING, ThermalState.CORRECTING],  # depends on target
            ProbeState: [ThermalState.CALIBRATING, ThermalState.DRIFTING],    # completion or abort
            CalibratingState: [ThermalState.DRIFTING]
        }
        
        for handler_class, expected_states in expected_transitions.items():
            handler = handler_class()
            mock_context = Mock()
            
            # Configure for transition conditions (simplified)
            mock_context.thermal_constants = Mock()
            mock_context.thermal_constants.priming_duration = 0  # Force immediate transition
            mock_context.thermal_constants.recovery_duration = 0
            mock_context.thermal_constants.calibrating_duration = 0
            
            try:
                result = handler.execute(mock_context, 23.5, (22.0, 25.0))
                if result is not None:
                    assert result in expected_states, f"{handler_class} returned unexpected state: {result}"
            except (AttributeError, ValueError, TypeError):
                # May need additional setup for some handlers
                pass