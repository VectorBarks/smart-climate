"""Test ThermalManager integration with ProbeScheduler.

Tests the integration patterns specified in architecture Section 20.11:
- Constructor integration with ProbeScheduler
- State transition logic with probe scheduling
- Opportunistic probing from stable states
- Passive learning during PRIMING
- Backward compatibility when probe scheduler not provided
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from custom_components.smart_climate.thermal_manager import ThermalManager
from custom_components.smart_climate.thermal_models import ThermalState, PassiveThermalModel
from custom_components.smart_climate.probe_scheduler import ProbeScheduler
from custom_components.smart_climate.user_preferences import UserPreferences, PreferenceLevel


class TestThermalManagerProbeIntegration:
    """Test ProbeScheduler integration with ThermalManager."""

    @pytest.fixture
    def mock_hass(self):
        """Mock Home Assistant instance."""
        return Mock()

    @pytest.fixture
    def mock_thermal_model(self):
        """Mock PassiveThermalModel."""
        model = Mock(spec=PassiveThermalModel)
        model.get_confidence.return_value = 0.7
        return model

    @pytest.fixture
    def mock_preferences(self):
        """Mock UserPreferences."""
        return Mock(spec=UserPreferences)

    @pytest.fixture
    def mock_probe_scheduler(self):
        """Mock ProbeScheduler."""
        scheduler = Mock(spec=ProbeScheduler)
        scheduler.should_probe_now.return_value = False  # Default to no probing
        return scheduler

    @pytest.fixture
    def thermal_manager_config(self):
        """Standard ThermalManager configuration."""
        return {
            'tau_cooling': 90.0,
            'tau_warming': 150.0,
            'min_off_time': 600,
            'min_on_time': 300,
            'priming_duration': 86400,
            'recovery_duration': 1800
        }

    def test_thermal_manager_init_with_probe_scheduler(self, mock_hass, mock_thermal_model, 
                                                     mock_preferences, mock_probe_scheduler,
                                                     thermal_manager_config):
        """Test ThermalManager initialization with ProbeScheduler."""
        # Act
        manager = ThermalManager(
            hass=mock_hass,
            thermal_model=mock_thermal_model,
            preferences=mock_preferences,
            config=thermal_manager_config,
            probe_scheduler=mock_probe_scheduler
        )

        # Assert
        assert hasattr(manager, 'probe_scheduler')
        assert manager.probe_scheduler is mock_probe_scheduler

    def test_thermal_manager_init_without_probe_scheduler(self, mock_hass, mock_thermal_model,
                                                        mock_preferences, thermal_manager_config):
        """Test ThermalManager backward compatibility without ProbeScheduler."""
        # Act - should not raise exception
        manager = ThermalManager(
            hass=mock_hass,
            thermal_model=mock_thermal_model,
            preferences=mock_preferences,
            config=thermal_manager_config
        )

        # Assert - probe_scheduler should be None
        assert hasattr(manager, 'probe_scheduler')
        assert manager.probe_scheduler is None

    def test_priming_state_passive_learning_only(self, mock_hass, mock_thermal_model,
                                                mock_preferences, mock_probe_scheduler,
                                                thermal_manager_config):
        """Test PRIMING state only does passive learning, no probing."""
        # Arrange
        mock_probe_scheduler.should_probe_now.return_value = True  # Scheduler wants to probe
        
        manager = ThermalManager(
            hass=mock_hass,
            thermal_model=mock_thermal_model,
            preferences=mock_preferences,
            config=thermal_manager_config,
            probe_scheduler=mock_probe_scheduler
        )
        
        # Force PRIMING state (this is the default, but make it explicit)
        manager._current_state = ThermalState.PRIMING
        
        with patch.object(manager, '_handle_passive_learning') as mock_passive_learning:
            # Act
            manager.update_state(current_temp=22.0, outdoor_temp=25.0, hvac_mode="cool")
            
            # Assert
            mock_passive_learning.assert_called_once()
            # Should never check probe scheduler during PRIMING
            mock_probe_scheduler.should_probe_now.assert_not_called()
            # Should remain in PRIMING state
            assert manager._current_state == ThermalState.PRIMING

    def test_drifting_state_opportunistic_probing(self, mock_hass, mock_thermal_model,
                                                 mock_preferences, mock_probe_scheduler,
                                                 thermal_manager_config):
        """Test DRIFTING state checks for opportunistic probing."""
        # Arrange
        mock_probe_scheduler.should_probe_now.return_value = True
        
        manager = ThermalManager(
            hass=mock_hass,
            thermal_model=mock_thermal_model,
            preferences=mock_preferences,
            config=thermal_manager_config,
            probe_scheduler=mock_probe_scheduler
        )
        
        # Set to DRIFTING state
        manager._current_state = ThermalState.DRIFTING
        
        with patch.object(manager, 'transition_to') as mock_transition:
            # Act
            manager.update_state(current_temp=22.0, outdoor_temp=25.0, hvac_mode="cool")
            
            # Assert
            mock_probe_scheduler.should_probe_now.assert_called_once()
            mock_transition.assert_called_with(ThermalState.PROBING)

    def test_correcting_state_opportunistic_probing(self, mock_hass, mock_thermal_model,
                                                   mock_preferences, mock_probe_scheduler,
                                                   thermal_manager_config):
        """Test CORRECTING state checks for opportunistic probing."""
        # Arrange
        mock_probe_scheduler.should_probe_now.return_value = True
        
        manager = ThermalManager(
            hass=mock_hass,
            thermal_model=mock_thermal_model,
            preferences=mock_preferences,
            config=thermal_manager_config,
            probe_scheduler=mock_probe_scheduler
        )
        
        # Set to CORRECTING state
        manager._current_state = ThermalState.CORRECTING
        
        with patch.object(manager, 'transition_to') as mock_transition:
            # Act
            manager.update_state(current_temp=22.0, outdoor_temp=25.0, hvac_mode="cool")
            
            # Assert
            mock_probe_scheduler.should_probe_now.assert_called_once()
            mock_transition.assert_called_with(ThermalState.PROBING)

    def test_probe_scheduling_blocked_in_other_states(self, mock_hass, mock_thermal_model,
                                                     mock_preferences, mock_probe_scheduler,
                                                     thermal_manager_config):
        """Test probe scheduling is blocked in RECOVERY, PROBING, CALIBRATING states."""
        # Test states where probing should be blocked
        blocked_states = [ThermalState.RECOVERY, ThermalState.PROBING, ThermalState.CALIBRATING]
        
        for state in blocked_states:
            # Arrange
            mock_probe_scheduler.should_probe_now.return_value = True  # Scheduler wants to probe
            mock_probe_scheduler.reset_mock()
            
            manager = ThermalManager(
                hass=mock_hass,
                thermal_model=mock_thermal_model,
                preferences=mock_preferences,
                config=thermal_manager_config,
                probe_scheduler=mock_probe_scheduler
            )
            
            # Set to test state
            manager._current_state = state
            
            with patch.object(manager, 'transition_to') as mock_transition:
                # Act
                manager.update_state(current_temp=22.0, outdoor_temp=25.0, hvac_mode="cool")
                
                # Assert - should not check probe scheduler in these states
                mock_probe_scheduler.should_probe_now.assert_not_called()
                # Should not transition to PROBING
                mock_transition.assert_not_called()

    def test_probe_scheduler_declines_probing(self, mock_hass, mock_thermal_model,
                                             mock_preferences, mock_probe_scheduler,
                                             thermal_manager_config):
        """Test when probe scheduler declines to probe from DRIFTING state."""
        # Arrange
        mock_probe_scheduler.should_probe_now.return_value = False  # Scheduler declines
        
        manager = ThermalManager(
            hass=mock_hass,
            thermal_model=mock_thermal_model,
            preferences=mock_preferences,
            config=thermal_manager_config,
            probe_scheduler=mock_probe_scheduler
        )
        
        # Set to DRIFTING state
        manager._current_state = ThermalState.DRIFTING
        
        with patch.object(manager, 'transition_to') as mock_transition:
            # Act
            manager.update_state(current_temp=22.0, outdoor_temp=25.0, hvac_mode="cool")
            
            # Assert
            mock_probe_scheduler.should_probe_now.assert_called_once()
            # Should not transition to PROBING
            mock_transition.assert_not_called()
            # Should remain in DRIFTING
            assert manager._current_state == ThermalState.DRIFTING

    def test_backward_compatibility_no_probe_scheduler(self, mock_hass, mock_thermal_model,
                                                      mock_preferences, thermal_manager_config):
        """Test backward compatibility when probe scheduler is None."""
        # Arrange - no probe scheduler provided
        manager = ThermalManager(
            hass=mock_hass,
            thermal_model=mock_thermal_model,
            preferences=mock_preferences,
            config=thermal_manager_config
            # probe_scheduler=None (not provided)
        )
        
        # Set to DRIFTING state (would normally check for probing)
        manager._current_state = ThermalState.DRIFTING
        
        with patch.object(manager, 'transition_to') as mock_transition:
            # Act - should not raise exception
            manager.update_state(current_temp=22.0, outdoor_temp=25.0, hvac_mode="cool")
            
            # Assert - should not crash, should not transition to PROBING
            mock_transition.assert_not_called()
            assert manager._current_state == ThermalState.DRIFTING

    def test_existing_state_transition_logic_preserved(self, mock_hass, mock_thermal_model,
                                                      mock_preferences, mock_probe_scheduler,
                                                      thermal_manager_config):
        """Test that existing state transition logic still works with probe scheduler integration."""
        # Arrange
        mock_probe_scheduler.should_probe_now.return_value = False  # Don't interfere
        
        manager = ThermalManager(
            hass=mock_hass,
            thermal_model=mock_thermal_model,
            preferences=mock_preferences,
            config=thermal_manager_config,
            probe_scheduler=mock_probe_scheduler
        )
        
        # Set to DRIFTING state
        manager._current_state = ThermalState.DRIFTING
        
        # Mock state handler to return a different state (simulating normal state transition)
        mock_handler = Mock()
        mock_handler.execute.return_value = ThermalState.CORRECTING
        manager._state_handlers[ThermalState.DRIFTING] = mock_handler
        
        with patch.object(manager, 'transition_to') as mock_transition:
            # Act
            manager.update_state(current_temp=22.0, outdoor_temp=25.0, hvac_mode="cool")
            
            # Assert
            # Probe scheduler should be checked but decline
            mock_probe_scheduler.should_probe_now.assert_called_once()
            # Normal state handler should still execute
            mock_handler.execute.assert_called_once()
            # Should transition to CORRECTING (from handler), not PROBING (from probe scheduler)
            mock_transition.assert_called_with(ThermalState.CORRECTING)

    def test_probe_scheduler_exception_handling(self, mock_hass, mock_thermal_model,
                                               mock_preferences, mock_probe_scheduler,
                                               thermal_manager_config):
        """Test graceful handling of probe scheduler exceptions."""
        # Arrange
        mock_probe_scheduler.should_probe_now.side_effect = Exception("Probe scheduler error")
        
        manager = ThermalManager(
            hass=mock_hass,
            thermal_model=mock_thermal_model,
            preferences=mock_preferences,
            config=thermal_manager_config,
            probe_scheduler=mock_probe_scheduler
        )
        
        # Set to DRIFTING state
        manager._current_state = ThermalState.DRIFTING
        
        with patch.object(manager, 'transition_to') as mock_transition:
            # Act - should not raise exception
            manager.update_state(current_temp=22.0, outdoor_temp=25.0, hvac_mode="cool")
            
            # Assert - should handle error gracefully and not transition to PROBING
            mock_probe_scheduler.should_probe_now.assert_called_once()
            mock_transition.assert_not_called()
            assert manager._current_state == ThermalState.DRIFTING

    def test_integration_with_mock_state_handlers(self, mock_hass, mock_thermal_model,
                                                 mock_preferences, mock_probe_scheduler,
                                                 thermal_manager_config):
        """Test integration works correctly with state handler system."""
        # Arrange
        mock_probe_scheduler.should_probe_now.return_value = True
        
        manager = ThermalManager(
            hass=mock_hass,
            thermal_model=mock_thermal_model,
            preferences=mock_preferences,
            config=thermal_manager_config,
            probe_scheduler=mock_probe_scheduler
        )
        
        # Set to DRIFTING state and mock its handler
        manager._current_state = ThermalState.DRIFTING
        mock_handler = Mock()
        mock_handler.execute.return_value = None  # Handler doesn't want to transition
        manager._state_handlers[ThermalState.DRIFTING] = mock_handler
        
        with patch.object(manager, 'transition_to') as mock_transition:
            # Act
            manager.update_state(current_temp=22.0, outdoor_temp=25.0, hvac_mode="cool")
            
            # Assert
            # Handler should execute first
            mock_handler.execute.assert_called_once()
            # Then probe scheduler should be checked
            mock_probe_scheduler.should_probe_now.assert_called_once()
            # Should transition to PROBING (probe scheduler wins when handler returns None)
            mock_transition.assert_called_with(ThermalState.PROBING)

    def test_probe_priority_over_no_handler_transition(self, mock_hass, mock_thermal_model,
                                                      mock_preferences, mock_probe_scheduler,
                                                      thermal_manager_config):
        """Test probe scheduling takes priority when handler returns None."""
        # Arrange
        mock_probe_scheduler.should_probe_now.return_value = True
        
        manager = ThermalManager(
            hass=mock_hass,
            thermal_model=mock_thermal_model,
            preferences=mock_preferences,
            config=thermal_manager_config,
            probe_scheduler=mock_probe_scheduler
        )
        
        # Set to CORRECTING state and mock its handler to return None
        manager._current_state = ThermalState.CORRECTING
        mock_handler = Mock()
        mock_handler.execute.return_value = None  # No state transition from handler
        manager._state_handlers[ThermalState.CORRECTING] = mock_handler
        
        with patch.object(manager, 'transition_to') as mock_transition:
            # Act
            manager.update_state(current_temp=22.0, outdoor_temp=25.0, hvac_mode="cool")
            
            # Assert
            mock_handler.execute.assert_called_once()
            mock_probe_scheduler.should_probe_now.assert_called_once()
            mock_transition.assert_called_with(ThermalState.PROBING)

    def test_handler_transition_takes_priority_over_probing(self, mock_hass, mock_thermal_model,
                                                           mock_preferences, mock_probe_scheduler,
                                                           thermal_manager_config):
        """Test state handler transition takes priority over probe scheduling."""
        # Arrange
        mock_probe_scheduler.should_probe_now.return_value = True  # Scheduler wants to probe
        
        manager = ThermalManager(
            hass=mock_hass,
            thermal_model=mock_thermal_model,
            preferences=mock_preferences,
            config=thermal_manager_config,
            probe_scheduler=mock_probe_scheduler
        )
        
        # Set to DRIFTING state and mock handler to return a different state
        manager._current_state = ThermalState.DRIFTING
        mock_handler = Mock()
        mock_handler.execute.return_value = ThermalState.RECOVERY  # Handler wants recovery
        manager._state_handlers[ThermalState.DRIFTING] = mock_handler
        
        with patch.object(manager, 'transition_to') as mock_transition:
            # Act
            manager.update_state(current_temp=22.0, outdoor_temp=25.0, hvac_mode="cool")
            
            # Assert
            mock_handler.execute.assert_called_once()
            # Handler transition should take priority, probe scheduler should not be called
            mock_probe_scheduler.should_probe_now.assert_not_called()
            mock_transition.assert_called_with(ThermalState.RECOVERY)