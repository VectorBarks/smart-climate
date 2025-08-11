"""ABOUTME: Test suite for passive learning orchestration in ThermalManager.
Tests integration between PrimingState, ThermalManager, StabilityDetector, and thermal_utils."""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from typing import List, Tuple, Optional
from datetime import datetime

from custom_components.smart_climate.thermal_models import ThermalState, ThermalConstants, ProbeResult
from custom_components.smart_climate.thermal_preferences import UserPreferences, PreferenceLevel
from custom_components.smart_climate.thermal_model import PassiveThermalModel
from custom_components.smart_climate.thermal_manager import ThermalManager
from custom_components.smart_climate.thermal_special_states import PrimingState


class TestThermalManagerPassiveLearning:
    """Test passive learning orchestration in ThermalManager."""

    @pytest.fixture
    def mock_hass(self):
        """Mock Home Assistant instance."""
        return Mock()

    @pytest.fixture
    def mock_thermal_model(self):
        """Mock PassiveThermalModel with update_tau method."""
        model = Mock(spec=PassiveThermalModel)
        model.predict_drift.return_value = 22.0
        model.get_confidence.return_value = 0.8
        model.update_tau = Mock()
        return model

    @pytest.fixture
    def mock_preferences(self):
        """Mock UserPreferences."""
        prefs = Mock(spec=UserPreferences)
        prefs.level = PreferenceLevel.BALANCED
        prefs.get_adjusted_band.return_value = 1.5
        return prefs

    @pytest.fixture
    def mock_config(self):
        """Mock configuration with passive learning settings."""
        return {
            'passive_learning_enabled': True,
            'passive_confidence_threshold': 0.3,
            'passive_min_drift_minutes': 15,
            'tau_cooling': 90.0,
            'tau_warming': 150.0,
            'calibration_idle_minutes': 30,
            'calibration_drift_threshold': 0.3
        }

    @pytest.fixture
    def thermal_manager(self, mock_hass, mock_thermal_model, mock_preferences, mock_config):
        """Create ThermalManager instance with passive learning configuration."""
        return ThermalManager(mock_hass, mock_thermal_model, mock_preferences, mock_config)

    def test_handle_passive_learning_method_exists(self, thermal_manager):
        """Test that _handle_passive_learning method exists."""
        assert hasattr(thermal_manager, '_handle_passive_learning')
        assert callable(thermal_manager._handle_passive_learning)

    def test_handle_passive_learning_no_drift_event(self, thermal_manager):
        """Test _handle_passive_learning when no drift event is found."""
        # Mock stability detector with no drift event
        thermal_manager.stability_detector.find_natural_drift_event = Mock(return_value=None)
        
        # Should not call analyze_drift_data
        with patch('custom_components.smart_climate.thermal_utils.analyze_drift_data') as mock_analyze:
            thermal_manager._handle_passive_learning()
            mock_analyze.assert_not_called()

    def test_handle_passive_learning_drift_event_found(self, thermal_manager):
        """Test _handle_passive_learning when drift event is found."""
        # Mock drift event data
        drift_data = [(1000.0, 24.0), (1060.0, 23.8), (1120.0, 23.5)]
        thermal_manager.stability_detector.find_natural_drift_event = Mock(return_value=drift_data)
        
        # Mock successful analysis
        probe_result = ProbeResult(
            tau_value=120.0,
            confidence=0.4,  # Above 0.3 threshold
            duration=900,
            fit_quality=0.8,
            aborted=False
        )
        
        with patch('custom_components.smart_climate.thermal_utils.analyze_drift_data') as mock_analyze:
            mock_analyze.return_value = probe_result
            
            thermal_manager._handle_passive_learning()
            
            # Verify analyze_drift_data was called with correct parameters
            mock_analyze.assert_called_once_with(drift_data, is_passive=True)
            
            # Verify model.update_tau was called (default _last_hvac_mode="cool" -> is_cooling=True)
            thermal_manager._model.update_tau.assert_called_once_with(probe_result, True)

    def test_handle_passive_learning_low_confidence_rejected(self, thermal_manager):
        """Test _handle_passive_learning rejects results with confidence below threshold."""
        # Mock drift event data
        drift_data = [(1000.0, 24.0), (1060.0, 23.8)]
        thermal_manager.stability_detector.find_natural_drift_event = Mock(return_value=drift_data)
        
        # Mock analysis with low confidence
        probe_result = ProbeResult(
            tau_value=120.0,
            confidence=0.2,  # Below 0.3 threshold
            duration=900,
            fit_quality=0.8,
            aborted=False
        )
        
        with patch('custom_components.smart_climate.thermal_utils.analyze_drift_data') as mock_analyze:
            mock_analyze.return_value = probe_result
            
            thermal_manager._handle_passive_learning()
            
            # Verify analyze_drift_data was called
            mock_analyze.assert_called_once_with(drift_data, is_passive=True)
            
            # Verify model.update_tau was NOT called due to low confidence
            thermal_manager._model.update_tau.assert_not_called()

    def test_handle_passive_learning_analysis_failed(self, thermal_manager):
        """Test _handle_passive_learning when analysis fails."""
        # Mock drift event data
        drift_data = [(1000.0, 24.0), (1060.0, 23.8)]
        thermal_manager.stability_detector.find_natural_drift_event = Mock(return_value=drift_data)
        
        # Mock failed analysis
        with patch('custom_components.smart_climate.thermal_utils.analyze_drift_data') as mock_analyze:
            mock_analyze.return_value = None
            
            thermal_manager._handle_passive_learning()
            
            # Verify analyze_drift_data was called
            mock_analyze.assert_called_once_with(drift_data, is_passive=True)
            
            # Verify model.update_tau was NOT called
            thermal_manager._model.update_tau.assert_not_called()

    def test_handle_passive_learning_cooling_mode_detection(self, thermal_manager):
        """Test _handle_passive_learning correctly determines is_cooling parameter."""
        # Test cooling mode
        thermal_manager._last_hvac_mode = "cool"
        drift_data = [(1000.0, 24.0), (1060.0, 23.8)]
        thermal_manager.stability_detector.find_natural_drift_event = Mock(return_value=drift_data)
        
        probe_result = ProbeResult(tau_value=120.0, confidence=0.4, duration=900, fit_quality=0.8, aborted=False)
        
        with patch('custom_components.smart_climate.thermal_utils.analyze_drift_data') as mock_analyze:
            mock_analyze.return_value = probe_result
            
            thermal_manager._handle_passive_learning()
            
            # Verify update_tau was called with is_cooling=True
            thermal_manager._model.update_tau.assert_called_once_with(probe_result, True)

    def test_handle_passive_learning_heating_mode_detection(self, thermal_manager):
        """Test _handle_passive_learning correctly determines is_cooling parameter."""
        # Test heating mode
        thermal_manager._last_hvac_mode = "heat"
        drift_data = [(1000.0, 22.0), (1060.0, 22.2)]
        thermal_manager.stability_detector.find_natural_drift_event = Mock(return_value=drift_data)
        
        probe_result = ProbeResult(tau_value=120.0, confidence=0.4, duration=900, fit_quality=0.8, aborted=False)
        
        with patch('custom_components.smart_climate.thermal_utils.analyze_drift_data') as mock_analyze:
            mock_analyze.return_value = probe_result
            
            thermal_manager._handle_passive_learning()
            
            # Verify update_tau was called with is_cooling=False
            thermal_manager._model.update_tau.assert_called_once_with(probe_result, False)

    def test_handle_passive_learning_config_threshold_respected(self, thermal_manager):
        """Test _handle_passive_learning respects passive_confidence_threshold from config."""
        # Set custom threshold
        thermal_manager._config['passive_confidence_threshold'] = 0.5
        
        drift_data = [(1000.0, 24.0), (1060.0, 23.8)]
        thermal_manager.stability_detector.find_natural_drift_event = Mock(return_value=drift_data)
        
        # Mock analysis with confidence below custom threshold
        probe_result = ProbeResult(tau_value=120.0, confidence=0.4, duration=900, fit_quality=0.8, aborted=False)
        
        with patch('custom_components.smart_climate.thermal_utils.analyze_drift_data') as mock_analyze:
            mock_analyze.return_value = probe_result
            
            thermal_manager._handle_passive_learning()
            
            # Should be rejected due to higher threshold
            thermal_manager._model.update_tau.assert_not_called()

    @patch('custom_components.smart_climate.thermal_manager._LOGGER')
    def test_handle_passive_learning_logging_success(self, mock_logger, thermal_manager):
        """Test _handle_passive_learning logs successful passive learning."""
        drift_data = [(1000.0, 24.0), (1060.0, 23.8)]
        thermal_manager.stability_detector.find_natural_drift_event = Mock(return_value=drift_data)
        
        probe_result = ProbeResult(tau_value=120.0, confidence=0.4, duration=900, fit_quality=0.8, aborted=False)
        
        with patch('custom_components.smart_climate.thermal_utils.analyze_drift_data') as mock_analyze:
            mock_analyze.return_value = probe_result
            
            thermal_manager._handle_passive_learning()
            
            # Verify success was logged
            mock_logger.info.assert_called()
            args = mock_logger.info.call_args[0][0]
            assert "Passive learning" in args and "tau" in args

    @patch('custom_components.smart_climate.thermal_manager._LOGGER')
    def test_handle_passive_learning_logging_failure(self, mock_logger, thermal_manager):
        """Test _handle_passive_learning logs when passive learning fails."""
        drift_data = [(1000.0, 24.0), (1060.0, 23.8)]
        thermal_manager.stability_detector.find_natural_drift_event = Mock(return_value=drift_data)
        
        probe_result = ProbeResult(tau_value=120.0, confidence=0.2, duration=900, fit_quality=0.8, aborted=False)
        
        with patch('custom_components.smart_climate.thermal_utils.analyze_drift_data') as mock_analyze:
            mock_analyze.return_value = probe_result
            
            thermal_manager._handle_passive_learning()
            
            # Verify rejection was logged
            mock_logger.debug.assert_called()
            args = mock_logger.debug.call_args[0][0]
            assert "confidence" in args and "threshold" in args


class TestPrimingStatePassiveIntegration:
    """Test PrimingState integration with passive learning."""

    @pytest.fixture
    def mock_context(self):
        """Mock ThermalManager context."""
        context = Mock(spec=ThermalManager)
        context.thermal_constants = ThermalConstants()
        context.stability_detector = Mock()
        context.stability_detector.is_stable_for_calibration.return_value = False
        context.passive_learning_enabled = True
        context._handle_passive_learning = Mock()
        return context

    @pytest.fixture
    def priming_state(self):
        """Create PrimingState instance for testing."""
        state = PrimingState()
        state._start_time = datetime.now()
        return state

    def test_priming_state_calls_handle_passive_learning(self, priming_state, mock_context):
        """Test that PrimingState.execute calls _handle_passive_learning when enabled."""
        # Mock current conditions
        current_temp = 23.0
        operating_window = (22.0, 24.0)
        
        # Execute should call passive learning handler
        priming_state.execute(mock_context, current_temp, operating_window)
        
        # Verify passive learning was triggered
        mock_context._handle_passive_learning.assert_called_once()

    def test_priming_state_passive_learning_before_duration_check(self, priming_state, mock_context):
        """Test that passive learning is called before priming duration check."""
        # Mock short priming duration (should complete immediately)
        mock_context.thermal_constants.priming_duration = 0
        current_temp = 23.0
        operating_window = (22.0, 24.0)
        
        result = priming_state.execute(mock_context, current_temp, operating_window)
        
        # Even though priming would complete, passive learning should still be called first
        mock_context._handle_passive_learning.assert_called_once()
        
        # Should transition to DRIFTING due to zero duration
        assert result == ThermalState.DRIFTING

    def test_priming_state_no_passive_learning_when_disabled(self, priming_state, mock_context):
        """Test that PrimingState does not call passive learning when disabled."""
        mock_context.passive_learning_enabled = False
        current_temp = 23.0
        operating_window = (22.0, 24.0)
        
        priming_state.execute(mock_context, current_temp, operating_window)
        
        # Should not call passive learning when disabled
        mock_context._handle_passive_learning.assert_not_called()

    def test_priming_state_passive_learning_enabled_set_in_execute(self, priming_state, mock_context):
        """Test that PrimingState.execute enables passive learning when missing."""
        # Remove passive_learning_enabled attribute to test defaulting
        del mock_context.passive_learning_enabled
        
        current_temp = 23.0
        operating_window = (22.0, 24.0)
        
        priming_state.execute(mock_context, current_temp, operating_window)
        
        # Should have set passive_learning_enabled to True during execute()
        assert hasattr(mock_context, 'passive_learning_enabled')
        assert mock_context.passive_learning_enabled is True
        
    def test_priming_state_passive_learning_context_missing(self, priming_state):
        """Test PrimingState handles missing _handle_passive_learning method gracefully."""
        # Mock context without _handle_passive_learning method
        context = Mock()
        context.thermal_constants = ThermalConstants()
        context.stability_detector = Mock()
        context.stability_detector.is_stable_for_calibration.return_value = False
        context.passive_learning_enabled = True
        # Don't add _handle_passive_learning method
        
        current_temp = 23.0
        operating_window = (22.0, 24.0)
        
        # Should not raise exception when method is missing
        result = priming_state.execute(context, current_temp, operating_window)
        
        # Should continue normal execution
        assert result is None  # Stay in priming

    def test_priming_state_passive_learning_exception_handling(self, priming_state, mock_context):
        """Test PrimingState handles passive learning exceptions gracefully."""
        # Make passive learning raise an exception
        mock_context._handle_passive_learning.side_effect = RuntimeError("Passive learning error")
        
        current_temp = 23.0
        operating_window = (22.0, 24.0)
        
        # Should not propagate exception
        result = priming_state.execute(mock_context, current_temp, operating_window)
        
        # Should continue normal operation
        assert result is None  # Stay in priming


class TestPassiveLearningConfiguration:
    """Test configuration reading for passive learning."""

    def test_config_defaults_when_missing(self):
        """Test that default values are used when configuration is missing."""
        thermal_manager = ThermalManager(Mock(), Mock(), Mock(), {})
        
        # Should have default values
        assert thermal_manager._config.get('passive_confidence_threshold', 0.3) == 0.3
        assert thermal_manager._config.get('passive_min_drift_minutes', 15) == 15

    def test_config_custom_values_respected(self):
        """Test that custom configuration values are used."""
        config = {
            'passive_confidence_threshold': 0.4,
            'passive_min_drift_minutes': 20
        }
        thermal_manager = ThermalManager(Mock(), Mock(), Mock(), config)
        
        # Should use custom values
        assert thermal_manager._config['passive_confidence_threshold'] == 0.4
        assert thermal_manager._config['passive_min_drift_minutes'] == 20