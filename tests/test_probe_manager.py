"""Tests for ProbeManager - Thermal efficiency probe orchestration system.

The ProbeManager handles both active (user-triggered) and passive (opportunistic)
thermal probing for learning thermal constants and improving HVAC efficiency.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, call
from dataclasses import dataclass
from typing import Dict, Optional

from custom_components.smart_climate.thermal_models import ProbeResult, ThermalConstants
from custom_components.smart_climate.thermal_preferences import UserPreferences, PreferenceLevel
from custom_components.smart_climate.thermal_model import PassiveThermalModel


class TestProbeManagerInitialization:
    """Test ProbeManager initialization and basic functionality."""
    
    def test_probe_manager_init(self):
        """Test ProbeManager initializes correctly."""
        from custom_components.smart_climate.probe_manager import ProbeManager
        
        # Mock dependencies
        mock_hass = Mock()
        mock_thermal_model = Mock(spec=PassiveThermalModel)
        mock_preferences = Mock(spec=UserPreferences)
        
        manager = ProbeManager(mock_hass, mock_thermal_model, mock_preferences)
        
        assert manager._hass is mock_hass
        assert manager._thermal_model is mock_thermal_model  
        assert manager._preferences is mock_preferences
        assert manager._active_probes == {}
        assert manager._passive_detection_enabled is True
        assert manager._max_concurrent_probes == 1
    
    def test_probe_manager_init_with_options(self):
        """Test ProbeManager initialization with custom options."""
        from custom_components.smart_climate.probe_manager import ProbeManager
        
        mock_hass = Mock()
        mock_thermal_model = Mock(spec=PassiveThermalModel)
        mock_preferences = Mock(spec=UserPreferences)
        
        manager = ProbeManager(
            mock_hass, 
            mock_thermal_model, 
            mock_preferences,
            max_concurrent_probes=2,
            passive_detection_enabled=False
        )
        
        assert manager._max_concurrent_probes == 2
        assert manager._passive_detection_enabled is False


class TestProbeInitiationConditions:
    """Test probe initiation condition checking."""
    
    def setup_method(self):
        """Set up test fixtures."""
        from custom_components.smart_climate.probe_manager import ProbeManager
        
        self.mock_hass = Mock()
        self.mock_thermal_model = Mock(spec=PassiveThermalModel)
        self.mock_preferences = Mock(spec=UserPreferences)
        self.mock_preferences.probe_drift = 2.0
        
        self.manager = ProbeManager(self.mock_hass, self.mock_thermal_model, self.mock_preferences)
    
    def test_can_start_probe_basic_conditions(self):
        """Test can_start_probe with basic valid conditions."""
        current_conditions = {
            'hvac_mode': 'off',
            'indoor_temp': 22.0,
            'outdoor_temp': 25.0,
            'target_temp': 21.0,
            'ac_stable_duration': 900,  # 15 minutes
            'thermal_state': 'drifting'
        }
        
        result = self.manager.can_start_probe(current_conditions)
        assert result is True
    
    def test_can_start_probe_hvac_on_blocks(self):
        """Test can_start_probe blocks when HVAC is running."""
        current_conditions = {
            'hvac_mode': 'cool',
            'indoor_temp': 22.0,
            'outdoor_temp': 25.0,
            'target_temp': 21.0,
            'ac_stable_duration': 900,
            'thermal_state': 'correcting'
        }
        
        result = self.manager.can_start_probe(current_conditions)
        assert result is False
    
    def test_can_start_probe_insufficient_stability(self):
        """Test can_start_probe blocks with insufficient AC stability duration."""
        current_conditions = {
            'hvac_mode': 'off',
            'indoor_temp': 22.0,
            'outdoor_temp': 25.0,
            'target_temp': 21.0,
            'ac_stable_duration': 300,  # Only 5 minutes
            'thermal_state': 'drifting'
        }
        
        result = self.manager.can_start_probe(current_conditions)
        assert result is False
    
    def test_can_start_probe_missing_conditions(self):
        """Test can_start_probe handles missing condition data."""
        incomplete_conditions = {
            'hvac_mode': 'off',
            'indoor_temp': 22.0
            # Missing outdoor_temp, target_temp, etc.
        }
        
        result = self.manager.can_start_probe(incomplete_conditions)
        assert result is False
    
    def test_can_start_probe_concurrent_limit(self):
        """Test can_start_probe respects concurrent probe limit."""
        # Setup active probe
        self.manager._active_probes['test_probe'] = Mock()
        
        current_conditions = {
            'hvac_mode': 'off',
            'indoor_temp': 22.0,
            'outdoor_temp': 25.0,
            'target_temp': 21.0,
            'ac_stable_duration': 900,
            'thermal_state': 'drifting'
        }
        
        result = self.manager.can_start_probe(current_conditions)
        assert result is False
    
    def test_can_start_probe_wrong_thermal_state(self):
        """Test can_start_probe blocks in wrong thermal state."""
        current_conditions = {
            'hvac_mode': 'off',
            'indoor_temp': 22.0,
            'outdoor_temp': 25.0,
            'target_temp': 21.0,
            'ac_stable_duration': 900,
            'thermal_state': 'priming'  # Wrong state for probing
        }
        
        result = self.manager.can_start_probe(current_conditions)
        assert result is False


class TestActiveProbeOrchestration:
    """Test active probe lifecycle and orchestration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        from custom_components.smart_climate.probe_manager import ProbeManager
        
        self.mock_hass = Mock()
        self.mock_thermal_model = Mock(spec=PassiveThermalModel)
        self.mock_preferences = Mock(spec=UserPreferences)
        self.mock_preferences.probe_drift = 2.0
        
        self.manager = ProbeManager(self.mock_hass, self.mock_thermal_model, self.mock_preferences)
        
    def test_start_active_probe_success(self):
        """Test successful active probe initiation."""
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = 'test_probe_id'
            with patch('custom_components.smart_climate.probe_manager.datetime') as mock_datetime:
                mock_now = datetime(2025, 1, 6, 14, 30)
                mock_datetime.now.return_value = mock_now
                
                probe_id = self.manager.start_active_probe(max_drift=2.5)
                
                assert probe_id == 'test_probe_id'
                assert 'test_probe_id' in self.manager._active_probes
                
                probe_data = self.manager._active_probes['test_probe_id']
                assert probe_data['start_time'] == mock_now
                assert probe_data['max_drift'] == 2.5
                assert probe_data['probe_type'] == 'active'
                assert probe_data['temperatures'] == []
                assert probe_data['start_temp'] is None
    
    def test_start_active_probe_creates_notification(self):
        """Test active probe creates Home Assistant notification."""
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = 'test_probe'
            
            probe_id = self.manager.start_active_probe()
            
            # Should create notification via Home Assistant service call
            self.mock_hass.services.call.assert_called_once_with(
                'persistent_notification',
                'create',
                service_data={
                    'notification_id': f'smart_climate_probe_{probe_id}',
                    'title': 'Smart Climate Thermal Probe Active',
                    'message': 'Temperature drift learning in progress. Allow temperature to drift up to 2.0°C for accurate thermal modeling.',
                    'data': {
                        'actions': [
                            {
                                'action': f'smart_climate_abort_probe_{probe_id}',
                                'title': 'Abort Probe'
                            }
                        ]
                    }
                }
            )
    
    def test_start_active_probe_custom_drift(self):
        """Test active probe with custom max drift."""
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = 'custom_probe'
            
            probe_id = self.manager.start_active_probe(max_drift=3.0)
            
            assert self.manager._active_probes[probe_id]['max_drift'] == 3.0
    
    def test_start_active_probe_concurrent_limit_exceeded(self):
        """Test active probe fails when concurrent limit exceeded."""
        # Add existing probe
        self.manager._active_probes['existing'] = Mock()
        
        with pytest.raises(RuntimeError, match="Maximum concurrent probes exceeded"):
            self.manager.start_active_probe()
    
    def test_get_probe_status_active_probe(self):
        """Test getting status of active probe."""
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = 'status_probe'
            with patch('custom_components.smart_climate.probe_manager.datetime') as mock_datetime:
                start_time = datetime(2025, 1, 6, 14, 0)
                current_time = datetime(2025, 1, 6, 14, 15)  # 15 minutes later
                mock_datetime.now.side_effect = [start_time, current_time]
                
                probe_id = self.manager.start_active_probe()
                
                # Simulate temperature recording
                probe_data = self.manager._active_probes[probe_id]
                probe_data['start_temp'] = 22.0
                probe_data['temperatures'] = [
                    (datetime(2025, 1, 6, 14, 5), 22.3),
                    (datetime(2025, 1, 6, 14, 10), 22.7),
                    (datetime(2025, 1, 6, 14, 15), 23.1)
                ]
                
                status = self.manager.get_probe_status(probe_id)
                
                assert status['probe_id'] == probe_id
                assert status['status'] == 'active'
                assert status['duration_seconds'] == 900  # 15 minutes
                assert status['current_drift'] == 1.1  # 23.1 - 22.0
                assert status['max_drift'] == 2.0
                assert status['completion_percentage'] == 55  # 1.1/2.0 * 100
    
    def test_get_probe_status_nonexistent_probe(self):
        """Test getting status of nonexistent probe."""
        status = self.manager.get_probe_status('nonexistent')
        assert status is None


class TestPassiveProbeDetection:
    """Test passive probe detection logic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        from custom_components.smart_climate.probe_manager import ProbeManager
        
        self.mock_hass = Mock()
        self.mock_thermal_model = Mock(spec=PassiveThermalModel)
        self.mock_preferences = Mock(spec=UserPreferences)
        
        self.manager = ProbeManager(self.mock_hass, self.mock_thermal_model, self.mock_preferences)
    
    def test_detect_passive_probe_valid_conditions(self):
        """Test detecting valid passive probe conditions."""
        # AC off for >60 minutes with stable outdoor temp and significant drift
        ac_state_history = [
            ('off', datetime(2025, 1, 6, 13, 0), 22.0, 25.0),  # Start
            ('off', datetime(2025, 1, 6, 13, 30), 22.5, 25.2),
            ('off', datetime(2025, 1, 6, 14, 0), 23.2, 24.8),
            ('off', datetime(2025, 1, 6, 14, 30), 24.1, 25.1),  # 90 minutes total
        ]
        
        result = self.manager.detect_passive_probe(ac_state_history)
        assert result is True
    
    def test_detect_passive_probe_insufficient_duration(self):
        """Test passive probe detection with insufficient AC off duration."""
        ac_state_history = [
            ('off', datetime(2025, 1, 6, 14, 0), 22.0, 25.0),
            ('off', datetime(2025, 1, 6, 14, 30), 22.8, 25.1),  # Only 30 minutes
        ]
        
        result = self.manager.detect_passive_probe(ac_state_history)
        assert result is False
    
    def test_detect_passive_probe_unstable_outdoor_temp(self):
        """Test passive probe detection with unstable outdoor temperature."""
        ac_state_history = [
            ('off', datetime(2025, 1, 6, 13, 0), 22.0, 25.0),
            ('off', datetime(2025, 1, 6, 13, 30), 22.5, 27.5),  # +2.5°C outdoor change
            ('off', datetime(2025, 1, 6, 14, 0), 23.0, 23.0),   # -4.5°C outdoor change
            ('off', datetime(2025, 1, 6, 14, 30), 23.5, 30.0),  # +7°C outdoor change
        ]
        
        result = self.manager.detect_passive_probe(ac_state_history)
        assert result is False
    
    def test_detect_passive_probe_insufficient_drift(self):
        """Test passive probe detection with insufficient temperature drift."""
        ac_state_history = [
            ('off', datetime(2025, 1, 6, 13, 0), 22.0, 25.0),
            ('off', datetime(2025, 1, 6, 13, 30), 22.1, 25.1),
            ('off', datetime(2025, 1, 6, 14, 0), 22.2, 24.9),
            ('off', datetime(2025, 1, 6, 14, 30), 22.3, 25.0),  # Only 0.3°C drift
        ]
        
        result = self.manager.detect_passive_probe(ac_state_history)
        assert result is False
    
    def test_detect_passive_probe_ac_turned_on(self):
        """Test passive probe detection when AC turns on during period."""
        ac_state_history = [
            ('off', datetime(2025, 1, 6, 13, 0), 22.0, 25.0),
            ('off', datetime(2025, 1, 6, 13, 30), 22.5, 25.1),
            ('cool', datetime(2025, 1, 6, 14, 0), 23.0, 24.9),  # AC turned on
            ('off', datetime(2025, 1, 6, 14, 30), 22.5, 25.0),
        ]
        
        result = self.manager.detect_passive_probe(ac_state_history)
        assert result is False
    
    def test_detect_passive_probe_disabled(self):
        """Test passive probe detection when disabled."""
        self.manager._passive_detection_enabled = False
        
        ac_state_history = [
            ('off', datetime(2025, 1, 6, 13, 0), 22.0, 25.0),
            ('off', datetime(2025, 1, 6, 14, 30), 24.0, 25.0),  # Perfect conditions
        ]
        
        result = self.manager.detect_passive_probe(ac_state_history)
        assert result is False


class TestNotificationManagement:
    """Test probe notification creation and management."""
    
    def setup_method(self):
        """Set up test fixtures."""
        from custom_components.smart_climate.probe_manager import ProbeManager
        
        self.mock_hass = Mock()
        self.mock_thermal_model = Mock(spec=PassiveThermalModel)
        self.mock_preferences = Mock(spec=UserPreferences)
        
        self.manager = ProbeManager(self.mock_hass, self.mock_thermal_model, self.mock_preferences)
    
    def test_create_notification_basic(self):
        """Test basic notification creation."""
        self.manager.create_notification(
            'Test Title',
            'Test message content',
            'test_notification_id'
        )
        
        self.mock_hass.services.call.assert_called_once_with(
            'persistent_notification',
            'create',
            service_data={
                'notification_id': 'test_notification_id',
                'title': 'Test Title',
                'message': 'Test message content'
            }
        )
    
    def test_create_notification_with_actions(self):
        """Test notification creation with action buttons."""
        actions = [
            {'action': 'test_action', 'title': 'Test Action'}
        ]
        
        self.manager.create_notification(
            'Test Title',
            'Test message',
            'test_id',
            actions=actions
        )
        
        expected_call = call(
            'persistent_notification',
            'create',
            service_data={
                'notification_id': 'test_id',
                'title': 'Test Title',
                'message': 'Test message',
                'data': {
                    'actions': actions
                }
            }
        )
        
        self.mock_hass.services.call.assert_called_once_with(*expected_call.args, **expected_call.kwargs)
    
    def test_update_probe_notification_content(self):
        """Test updating probe notification with current status."""
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = 'update_test'
            with patch('custom_components.smart_climate.probe_manager.datetime') as mock_datetime:
                start_time = datetime(2025, 1, 6, 14, 0)
                current_time = datetime(2025, 1, 6, 14, 10)
                mock_datetime.now.side_effect = [start_time, current_time]
                
                probe_id = self.manager.start_active_probe()
                
                # Reset mock to test update call
                self.mock_hass.services.call.reset_mock()
                
                # Simulate probe progress
                probe_data = self.manager._active_probes[probe_id]
                probe_data['start_temp'] = 22.0
                probe_data['temperatures'] = [(current_time, 22.8)]
                
                # This would typically be called periodically
                self.manager._update_probe_notification(probe_id)
                
                # Verify notification was updated
                assert self.mock_hass.services.call.called
                call_args = self.mock_hass.services.call.call_args
                assert 'Current drift: 0.8°C' in call_args[1]['service_data']['message']
                assert 'Time remaining: ~' in call_args[1]['service_data']['message']


class TestProbeAbortHandling:
    """Test probe abort functionality and cleanup."""
    
    def setup_method(self):
        """Set up test fixtures."""
        from custom_components.smart_climate.probe_manager import ProbeManager
        
        self.mock_hass = Mock()
        self.mock_thermal_model = Mock(spec=PassiveThermalModel)
        self.mock_preferences = Mock(spec=UserPreferences)
        
        self.manager = ProbeManager(self.mock_hass, self.mock_thermal_model, self.mock_preferences)
    
    def test_abort_probe_success(self):
        """Test successful probe abort."""
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = 'abort_test'
            
            probe_id = self.manager.start_active_probe()
            
            # Reset mock to test abort cleanup
            self.mock_hass.services.call.reset_mock()
            
            result = self.manager.abort_probe(probe_id)
            
            assert result is True
            assert probe_id not in self.manager._active_probes
            
            # Should dismiss the notification
            self.mock_hass.services.call.assert_called_once_with(
                'persistent_notification',
                'dismiss',
                service_data={
                    'notification_id': f'smart_climate_probe_{probe_id}'
                }
            )
    
    def test_abort_nonexistent_probe(self):
        """Test aborting nonexistent probe."""
        result = self.manager.abort_probe('nonexistent')
        assert result is False
        
        # Should not call any services
        self.mock_hass.services.call.assert_not_called()
    
    def test_abort_probe_data_cleanup(self):
        """Test probe abort cleans up all associated data."""
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = 'cleanup_test'
            
            probe_id = self.manager.start_active_probe()
            
            # Add some probe data
            probe_data = self.manager._active_probes[probe_id]
            probe_data['temperatures'] = [
                (datetime.now(), 22.5),
                (datetime.now(), 23.0)
            ]
            probe_data['start_temp'] = 22.0
            
            self.manager.abort_probe(probe_id)
            
            # Verify complete cleanup
            assert probe_id not in self.manager._active_probes


class TestProbeResultCalculation:
    """Test probe completion and result calculation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        from custom_components.smart_climate.probe_manager import ProbeManager
        
        self.mock_hass = Mock()
        self.mock_thermal_model = Mock(spec=PassiveThermalModel)
        self.mock_preferences = Mock(spec=UserPreferences)
        
        self.manager = ProbeManager(self.mock_hass, self.mock_thermal_model, self.mock_preferences)
    
    def test_complete_probe_success(self):
        """Test successful probe completion with result calculation."""
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = 'complete_test'
            
            probe_id = self.manager.start_active_probe()
            
            # Simulate probe data collection
            start_time = datetime(2025, 1, 6, 14, 0)
            probe_data = self.manager._active_probes[probe_id]
            probe_data['start_time'] = start_time
            probe_data['start_temp'] = 22.0
            probe_data['temperatures'] = [
                (start_time + timedelta(minutes=5), 22.3),
                (start_time + timedelta(minutes=10), 22.7),
                (start_time + timedelta(minutes=15), 23.1),
                (start_time + timedelta(minutes=20), 23.4)
            ]
            
            with patch.object(self.manager, '_calculate_tau_from_temperatures') as mock_calc:
                mock_calc.return_value = (85.0, 0.92)  # tau_value, fit_quality
                
                result = self.manager.complete_probe(probe_id)
                
                assert isinstance(result, ProbeResult)
                assert result.tau_value == 85.0
                assert result.confidence > 0.0
                assert result.duration == 1200  # 20 minutes
                assert result.fit_quality == 0.92
                assert result.aborted is False
    
    def test_complete_probe_partial_data(self):
        """Test probe completion with insufficient data (reduced confidence)."""
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = 'partial_test'
            
            probe_id = self.manager.start_active_probe()
            
            # Simulate minimal probe data
            start_time = datetime(2025, 1, 6, 14, 0)
            probe_data = self.manager._active_probes[probe_id]
            probe_data['start_time'] = start_time
            probe_data['start_temp'] = 22.0
            probe_data['temperatures'] = [
                (start_time + timedelta(minutes=5), 22.2),
                (start_time + timedelta(minutes=10), 22.4)
            ]
            
            with patch.object(self.manager, '_calculate_tau_from_temperatures') as mock_calc:
                mock_calc.return_value = (75.0, 0.65)  # Lower quality due to less data
                
                result = self.manager.complete_probe(probe_id)
                
                assert result.confidence < 0.7  # Reduced confidence
                assert result.duration == 600  # 10 minutes
    
    def test_complete_nonexistent_probe(self):
        """Test completing nonexistent probe."""
        result = self.manager.complete_probe('nonexistent')
        assert result is None
    
    def test_complete_probe_updates_thermal_model(self):
        """Test probe completion updates the thermal model."""
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = 'update_model_test'
            
            probe_id = self.manager.start_active_probe()
            
            # Setup probe data
            probe_data = self.manager._active_probes[probe_id]
            probe_data['start_temp'] = 22.0
            probe_data['temperatures'] = [(datetime.now(), 23.0)]
            
            with patch.object(self.manager, '_calculate_tau_from_temperatures') as mock_calc:
                mock_calc.return_value = (88.0, 0.89)
                
                result = self.manager.complete_probe(probe_id)
                
                # Should update thermal model with probe result
                self.mock_thermal_model.update_tau.assert_called_once()
                call_args = self.mock_thermal_model.update_tau.call_args[0]
                probe_result = call_args[0]
                is_cooling = call_args[1]
                
                assert isinstance(probe_result, ProbeResult)
                assert probe_result.tau_value == 88.0
                assert isinstance(is_cooling, bool)


class TestProbeManagerIntegration:
    """Test integration aspects and edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        from custom_components.smart_climate.probe_manager import ProbeManager
        
        self.mock_hass = Mock()
        self.mock_thermal_model = Mock(spec=PassiveThermalModel)
        self.mock_preferences = Mock(spec=UserPreferences)
        self.mock_preferences.probe_drift = 1.8
        
        self.manager = ProbeManager(self.mock_hass, self.mock_thermal_model, self.mock_preferences)
    
    def test_probe_manager_thermal_model_integration(self):
        """Test ProbeManager properly integrates with PassiveThermalModel."""
        # Test that probe results are passed to thermal model correctly
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = 'integration_test'
            
            probe_id = self.manager.start_active_probe()
            probe_data = self.manager._active_probes[probe_id]
            probe_data['start_temp'] = 21.0
            probe_data['temperatures'] = [(datetime.now(), 22.8)]  # 1.8°C drift (cooling scenario)
            
            with patch.object(self.manager, '_calculate_tau_from_temperatures') as mock_calc:
                mock_calc.return_value = (92.0, 0.88)
                
                result = self.manager.complete_probe(probe_id)
                
                # Verify thermal model update
                self.mock_thermal_model.update_tau.assert_called_once()
                update_args = self.mock_thermal_model.update_tau.call_args
                probe_result = update_args[0][0]
                is_cooling = update_args[0][1]
                
                assert probe_result.tau_value == 92.0
                assert is_cooling is True  # Indoor temp rose, so this is warming scenario
    
    def test_probe_manager_preferences_integration(self):
        """Test ProbeManager respects UserPreferences settings."""
        # Test that probe drift comes from preferences
        self.mock_preferences.probe_drift = 2.5
        
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = 'prefs_test'
            
            probe_id = self.manager.start_active_probe()
            probe_data = self.manager._active_probes[probe_id]
            
            assert probe_data['max_drift'] == 2.0  # Default override
            
            # Test custom drift override
            self.manager.abort_probe(probe_id)  # Clean up first probe
            probe_id2 = self.manager.start_active_probe(max_drift=3.0)
            probe_data2 = self.manager._active_probes[probe_id2]
            
            assert probe_data2['max_drift'] == 3.0  # Custom value
    
    def test_probe_manager_concurrent_prevention(self):
        """Test ProbeManager prevents concurrent probes properly."""
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = 'concurrent_test'
            
            # Start first probe
            probe_id1 = self.manager.start_active_probe()
            
            # Attempt second probe should fail
            with pytest.raises(RuntimeError, match="Maximum concurrent probes exceeded"):
                self.manager.start_active_probe()
            
            # After aborting first, second should succeed
            self.manager.abort_probe(probe_id1)
            probe_id2 = self.manager.start_active_probe()  # Should work now
            
            assert probe_id2 in self.manager._active_probes
    
    def test_probe_manager_cleanup_on_completion(self):
        """Test ProbeManager cleans up probe data after completion."""
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = 'cleanup_complete_test'
            
            probe_id = self.manager.start_active_probe()
            probe_data = self.manager._active_probes[probe_id]
            probe_data['temperatures'] = [(datetime.now(), 22.0)]
            
            with patch.object(self.manager, '_calculate_tau_from_temperatures') as mock_calc:
                mock_calc.return_value = (90.0, 0.85)
                
                result = self.manager.complete_probe(probe_id)
                
                # Probe should be removed from active probes
                assert probe_id not in self.manager._active_probes
                assert result is not None
                
                # Notification should be dismissed
                expected_calls = [
                    call('persistent_notification', 'create', service_data={
                        'notification_id': f'smart_climate_probe_{probe_id}',
                        'title': 'Smart Climate Thermal Probe Active',
                        'message': 'Temperature drift learning in progress. Allow temperature to drift up to 2.0°C for accurate thermal modeling.',
                        'data': {
                            'actions': [{'action': f'smart_climate_abort_probe_{probe_id}', 'title': 'Abort Probe'}]
                        }
                    }),
                    call('persistent_notification', 'dismiss', service_data={
                        'notification_id': f'smart_climate_probe_{probe_id}'
                    })
                ]
                
                self.mock_hass.services.call.assert_has_calls(expected_calls)