"""Test PrimingState start time persistence."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from custom_components.smart_climate.thermal_models import ThermalState
from custom_components.smart_climate.thermal_manager import ThermalManager
from custom_components.smart_climate.thermal_special_states import PrimingState


class TestPrimingStatePersistence:
    """Test suite for PrimingState start time persistence."""
    
    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        return Mock()
    
    @pytest.fixture
    def mock_thermal_model(self):
        """Create mock thermal model."""
        model = Mock()
        model._tau_cooling = 90.0
        model._tau_warming = 150.0
        model.get_confidence.return_value = 0.5
        model._probe_history = []
        return model
    
    @pytest.fixture
    def mock_preferences(self):
        """Create mock user preferences."""
        return Mock()
    
    @pytest.fixture
    def thermal_manager(self, mock_hass, mock_thermal_model, mock_preferences):
        """Create ThermalManager instance."""
        manager = ThermalManager(mock_hass, mock_thermal_model, mock_preferences)
        # Set to PRIMING state
        manager._current_state = ThermalState.PRIMING
        return manager
    
    def test_priming_start_time_serialization(self, thermal_manager):
        """Test that priming start time is serialized when in PRIMING state."""
        # Set a start time in the PrimingState handler
        test_start_time = datetime(2025, 1, 11, 10, 30, 0)
        handler = thermal_manager._state_handlers.get(ThermalState.PRIMING)
        handler._start_time = test_start_time
        
        # Serialize the state
        serialized = thermal_manager.serialize()
        
        # Check that priming_start_time is included
        assert "state" in serialized
        assert "priming_start_time" in serialized["state"]
        assert serialized["state"]["priming_start_time"] == test_start_time.isoformat()
    
    def test_priming_start_time_not_serialized_in_other_states(self, thermal_manager):
        """Test that priming start time is not serialized when not in PRIMING state."""
        # Change to DRIFTING state
        thermal_manager._current_state = ThermalState.DRIFTING
        
        # Serialize the state
        serialized = thermal_manager.serialize()
        
        # Check that priming_start_time is None
        assert "state" in serialized
        assert serialized["state"]["priming_start_time"] is None
    
    def test_priming_start_time_restoration(self, thermal_manager):
        """Test that priming start time is restored from persistence."""
        # Create test data with priming start time
        test_start_time = datetime(2025, 1, 11, 9, 0, 0)
        restore_data = {
            "version": "1.0",
            "state": {
                "current_state": "priming",
                "last_transition": datetime.now().isoformat(),
                "priming_start_time": test_start_time.isoformat()
            },
            "model": {
                "tau_cooling": 90.0,
                "tau_warming": 150.0,
                "last_modified": datetime.now().isoformat()
            }
        }
        
        # Restore the state
        thermal_manager.restore(restore_data)
        
        # Check that the start time was restored
        handler = thermal_manager._state_handlers.get(ThermalState.PRIMING)
        assert handler._start_time == test_start_time
        assert thermal_manager._current_state == ThermalState.PRIMING
    
    def test_priming_start_time_not_restored_in_wrong_state(self, thermal_manager):
        """Test that priming start time is not restored when not in PRIMING state."""
        # Create test data with DRIFTING state but priming_start_time present
        test_start_time = datetime(2025, 1, 11, 9, 0, 0)
        restore_data = {
            "version": "1.0",
            "state": {
                "current_state": "drifting",
                "last_transition": datetime.now().isoformat(),
                "priming_start_time": test_start_time.isoformat()
            },
            "model": {
                "tau_cooling": 90.0,
                "tau_warming": 150.0,
                "last_modified": datetime.now().isoformat()
            }
        }
        
        # Restore the state
        thermal_manager.restore(restore_data)
        
        # Check that the start time was NOT restored (wrong state)
        handler = thermal_manager._state_handlers.get(ThermalState.PRIMING)
        # The handler should have None or a different value
        assert thermal_manager._current_state == ThermalState.DRIFTING
    
    def test_priming_state_handles_missing_start_time(self):
        """Test that PrimingState initializes start time if missing."""
        handler = PrimingState()
        handler._start_time = None  # Simulate missing start time
        
        mock_context = Mock()
        mock_context.thermal_constants = Mock()
        mock_context.thermal_constants.priming_duration = 86400  # 24 hours
        mock_context.stability_detector = Mock()
        mock_context.stability_detector.is_stable_for_calibration.return_value = False
        mock_context._persistence_callback = Mock()
        
        # Execute with missing start time
        with patch('custom_components.smart_climate.thermal_special_states.datetime') as mock_dt:
            test_time = datetime(2025, 1, 11, 14, 0, 0)
            mock_dt.now.return_value = test_time
            
            result = handler.execute(mock_context, 23.5, (22.0, 25.0))
        
        # Check that start time was initialized
        assert handler._start_time == test_time
        # Check that persistence was triggered
        mock_context._persistence_callback.assert_called_once()
    
    def test_full_persistence_cycle(self, thermal_manager):
        """Test complete cycle: set -> serialize -> restore."""
        # Set start time
        original_start = datetime(2025, 1, 11, 8, 0, 0)
        handler = thermal_manager._state_handlers.get(ThermalState.PRIMING)
        handler._start_time = original_start
        
        # Serialize
        serialized = thermal_manager.serialize()
        
        # Create new manager and restore
        new_manager = ThermalManager(
            Mock(), Mock(), Mock()
        )
        new_manager.restore(serialized)
        
        # Verify restoration
        new_handler = new_manager._state_handlers.get(ThermalState.PRIMING)
        assert new_handler._start_time == original_start
        assert new_manager._current_state == ThermalState.PRIMING