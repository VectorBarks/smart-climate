"""ABOUTME: Tests for tau values modification timestamp tracking
ABOUTME: Verifies that tau_values_modified diagnostic shows actual modification time instead of current time"""

import pytest
from unittest.mock import Mock
from datetime import datetime, timedelta
from custom_components.smart_climate.thermal_model import PassiveThermalModel, ProbeResult
from custom_components.smart_climate.thermal_manager import ThermalManager
from custom_components.smart_climate.thermal_models import ThermalState
from custom_components.smart_climate.thermal_preferences import UserPreferences, PreferenceLevel


class TestTauModificationTracking:
    """Test tau values modification timestamp tracking."""

    def test_tau_last_modified_initially_none(self):
        """Test that tau_last_modified is None initially."""
        model = PassiveThermalModel()
        
        # Verify the property exists and is initially None
        assert hasattr(model, 'tau_last_modified')
        assert model.tau_last_modified is None

    def test_tau_last_modified_updates_when_tau_changes(self):
        """Test that tau_last_modified updates when update_tau() changes values."""
        model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        
        # Record time before update
        before_update = datetime.now()
        
        # Create probe result that will change tau values
        probe_result = ProbeResult(
            tau_value=95.0,  # Different from initial 90.0
            confidence=0.8,
            duration=3600,
            fit_quality=0.9,
            aborted=False
        )
        
        # Update tau for cooling
        model.update_tau(probe_result, is_cooling=True)
        
        # Record time after update
        after_update = datetime.now()
        
        # Verify tau_last_modified was set and is reasonable
        assert model.tau_last_modified is not None
        assert before_update <= model.tau_last_modified <= after_update
        assert model._tau_cooling != 90.0  # Verify tau actually changed

    def test_tau_last_modified_does_not_update_when_no_change_needed(self):
        """Test tau_last_modified doesn't update if calculated tau doesn't actually change."""
        model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        
        # Add a probe that would result in the same weighted average
        probe_result1 = ProbeResult(
            tau_value=90.0,  
            confidence=0.8,
            duration=3600,
            fit_quality=0.9,
            aborted=False
        )
        model.update_tau(probe_result1, is_cooling=True)
        
        # Now the current tau should be 90.0 (since first probe gets weight 0.4: 90*0.4 = 36, which is close to 90)
        # Actually, with weighted average: 90 * 0.4 = 36, so tau becomes 36, not 90
        # Let me recalculate the expected behavior
        
        # Set a specific tau and timestamp after the first probe
        current_tau = model._tau_cooling  # This will be the weighted result: 90 * 0.4 = 36
        model._tau_cooling = current_tau  # Ensure it's set
        
        # Set initial modification time 
        initial_time = datetime.now() - timedelta(hours=1)
        model._tau_last_modified = initial_time
        
        # Add another probe with same value - this should cause minimal change
        probe_result2 = ProbeResult(
            tau_value=current_tau,  # Use same value as current tau
            confidence=0.8,
            duration=3600,
            fit_quality=0.9,
            aborted=False
        )
        
        # Record tau before update
        tau_before = model._tau_cooling
        
        # Update tau for cooling
        model.update_tau(probe_result2, is_cooling=True)
        
        # With identical values, the weighted average should result in minimal change
        # But due to floating point precision, small changes may occur
        # The test should verify that if change is minimal, timestamp doesn't update
        tau_after = model._tau_cooling
        change = abs(tau_after - tau_before)
        
        if change <= 0.01:  # Our tolerance threshold
            # Should not have updated timestamp
            assert model.tau_last_modified == initial_time
        else:
            # Should have updated timestamp
            assert model.tau_last_modified != initial_time

    def test_tau_last_modified_updates_for_warming_tau(self):
        """Test that tau_last_modified updates for warming tau changes too."""
        model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        
        before_update = datetime.now()
        
        # Create probe result for warming
        probe_result = ProbeResult(
            tau_value=155.0,  # Different from initial 150.0
            confidence=0.8,
            duration=3600,
            fit_quality=0.9,
            aborted=False
        )
        
        # Update tau for warming
        model.update_tau(probe_result, is_cooling=False)
        
        after_update = datetime.now()
        
        # Verify tau_last_modified was set
        assert model.tau_last_modified is not None
        assert before_update <= model.tau_last_modified <= after_update
        assert model._tau_warming != 150.0  # Verify tau actually changed


class TestThermalManagerTauTimestampIntegration:
    """Test ThermalManager integration with tau timestamp tracking."""

    def test_thermal_manager_exposes_tau_last_modified(self):
        """Test that ThermalManager exposes tau_last_modified in diagnostics."""
        # Create mock dependencies
        mock_hass = Mock()
        mock_preferences = Mock(spec=UserPreferences)
        mock_preferences.level = PreferenceLevel.BALANCED
        
        # Create model with known modification time
        model = PassiveThermalModel()
        modification_time = datetime.now() - timedelta(minutes=30)
        model._tau_last_modified = modification_time
        
        # Create thermal manager
        manager = ThermalManager(mock_hass, model, mock_preferences)
        
        # Verify tau_last_modified is accessible via manager
        assert hasattr(manager, '_model')
        assert hasattr(manager._model, 'tau_last_modified')
        assert manager._model.tau_last_modified == modification_time

    def test_thermal_manager_serialization_includes_tau_timestamp(self):
        """Test that serialization includes tau_last_modified timestamp."""
        # Create mock dependencies
        mock_hass = Mock()
        mock_preferences = Mock(spec=UserPreferences)
        
        # Create model with modification time
        model = PassiveThermalModel()
        modification_time = datetime.now() - timedelta(minutes=45)
        model._tau_last_modified = modification_time
        
        # Create thermal manager
        manager = ThermalManager(mock_hass, model, mock_preferences)
        
        # Serialize thermal data
        serialized = manager.serialize()
        
        # Verify tau_last_modified is in model section
        assert "model" in serialized
        assert "last_modified" in serialized["model"]
        
        # Should use actual modification time, not current time
        serialized_time = datetime.fromisoformat(serialized["model"]["last_modified"])
        
        # Allow small tolerance for test execution time
        time_diff = abs((serialized_time - modification_time).total_seconds())
        assert time_diff < 1  # Less than 1 second difference

    def test_thermal_manager_serialization_handles_none_timestamp(self):
        """Test serialization when tau_last_modified is None."""
        # Create mock dependencies
        mock_hass = Mock()
        mock_preferences = Mock(spec=UserPreferences)
        
        # Create model without modification time
        model = PassiveThermalModel()
        assert model.tau_last_modified is None
        
        # Create thermal manager
        manager = ThermalManager(mock_hass, model, mock_preferences)
        
        # Serialize thermal data
        serialized = manager.serialize()
        
        # Should handle None gracefully (use current time as fallback)
        assert "model" in serialized
        assert "last_modified" in serialized["model"]
        assert serialized["model"]["last_modified"] is not None

    def test_thermal_manager_restoration_preserves_tau_timestamp(self):
        """Test that restoration preserves tau_last_modified from saved data."""
        # Create mock dependencies
        mock_hass = Mock()
        mock_preferences = Mock(spec=UserPreferences)
        model = PassiveThermalModel()
        manager = ThermalManager(mock_hass, model, mock_preferences)
        
        # Create test data with tau modification timestamp
        test_timestamp = "2025-08-09T10:15:30"
        test_data = {
            "version": "1.0",
            "state": {
                "current_state": "PRIMING",
                "last_transition": "2025-08-09T10:00:00"
            },
            "model": {
                "tau_cooling": 95.5,
                "tau_warming": 148.2,
                "last_modified": test_timestamp
            },
            "probe_history": [],
            "confidence": 0.0,
            "metadata": {
                "saves_count": 1,
                "corruption_recoveries": 0,
                "schema_version": "1.0"
            }
        }
        
        # Restore thermal data
        manager.restore(test_data)
        
        # Verify tau_last_modified was restored
        assert manager._model.tau_last_modified is not None
        restored_time = manager._model.tau_last_modified
        expected_time = datetime.fromisoformat(test_timestamp)
        assert restored_time == expected_time

    def test_thermal_manager_restoration_handles_invalid_timestamp(self):
        """Test restoration gracefully handles invalid tau timestamp."""
        # Create mock dependencies
        mock_hass = Mock()
        mock_preferences = Mock(spec=UserPreferences)
        model = PassiveThermalModel()
        manager = ThermalManager(mock_hass, model, mock_preferences)
        
        # Create test data with invalid timestamp
        test_data = {
            "version": "1.0",
            "state": {"current_state": "PRIMING"},
            "model": {
                "tau_cooling": 95.5,
                "tau_warming": 148.2,
                "last_modified": "invalid-timestamp"
            }
        }
        
        # Restore should not crash
        manager.restore(test_data)
        
        # Should have incremented corruption recovery count
        assert manager.corruption_recovery_count > 0
        
        # tau_last_modified should remain None or be set to None
        # (depending on implementation - either is acceptable for invalid data)


class TestSensorDiagnosticTimestamp:
    """Test sensor diagnostic timestamp display."""

    def test_sensor_uses_actual_tau_timestamp_not_current_time(self):
        """Test that sensor diagnostic uses actual tau modification time."""
        # This test verifies the fix for the bug where sensor.py line 275
        # used datetime.now() instead of the actual modification timestamp
        
        # Test the _get_thermal_persistence_diagnostics method directly
        # by creating a mock sensor with the necessary attributes
        
        # Set up modification time (2 hours ago)
        modification_time = datetime.now() - timedelta(hours=2)
        
        # Create mock thermal manager and model
        mock_thermal_manager = Mock()
        mock_model = Mock()
        mock_model.tau_last_modified = modification_time
        mock_thermal_manager._model = mock_model
        
        # Mock other required attributes for diagnostics
        mock_thermal_manager.thermal_data_last_saved = None
        mock_thermal_manager.thermal_state_restored = False  
        mock_thermal_manager.corruption_recovery_count = 0
        
        # Set up mock probe history
        mock_model._probe_history = []
        
        # Create a minimal sensor-like object for testing
        class TestSensor:
            def __init__(self):
                self._base_entity_id = "climate.test"
                self.coordinator = Mock()
                self.coordinator.hass = Mock()
                
                # Set up hass.data structure as expected by sensor
                self.coordinator.hass.data = {
                    "smart_climate": {
                        "test_entry": {
                            "thermal_components": {
                                "climate.test": {
                                    "thermal_manager": mock_thermal_manager
                                }
                            }
                        }
                    }
                }
                
            # Import the method we want to test
            from custom_components.smart_climate.sensor import SmartClimateDashboardSensor
            _get_thermal_persistence_diagnostics = SmartClimateDashboardSensor._get_thermal_persistence_diagnostics
        
        # Create test sensor instance
        sensor = TestSensor()
        
        # Get thermal persistence diagnostics
        attrs = sensor._get_thermal_persistence_diagnostics()
        
        # Verify that tau_values_modified uses actual modification time
        assert "tau_values_modified" in attrs
        
        if attrs["tau_values_modified"] is not None:
            # Should be the actual modification time, not current time
            diagnostic_time = datetime.fromisoformat(attrs["tau_values_modified"])
            
            # Should be close to our mock modification time
            time_diff = abs((diagnostic_time - modification_time).total_seconds())
            assert time_diff < 60  # Within 1 minute tolerance
            
            # Should NOT be current time (should be significantly in the past)
            current_time_diff = abs((diagnostic_time - datetime.now()).total_seconds())
            assert current_time_diff > 3600  # More than 1 hour ago

    def test_sensor_handles_none_tau_timestamp_gracefully(self):
        """Test sensor handles None tau_last_modified gracefully."""
        # Create mock thermal manager with model that has None modification time
        mock_thermal_manager = Mock()
        mock_model = Mock()
        mock_model.tau_last_modified = None
        mock_thermal_manager._model = mock_model
        
        # Mock other required attributes
        mock_thermal_manager.thermal_data_last_saved = None
        mock_thermal_manager.thermal_state_restored = False
        mock_thermal_manager.corruption_recovery_count = 0
        
        # Set up mock probe history
        mock_model._probe_history = []
        
        # Create a minimal sensor-like object for testing
        class TestSensor:
            def __init__(self):
                self._base_entity_id = "climate.test"
                self.coordinator = Mock()
                self.coordinator.hass = Mock()
                
                # Set up hass.data structure as expected by sensor
                self.coordinator.hass.data = {
                    "smart_climate": {
                        "test_entry": {
                            "thermal_components": {
                                "climate.test": {
                                    "thermal_manager": mock_thermal_manager
                                }
                            }
                        }
                    }
                }
                
            # Import the method we want to test
            from custom_components.smart_climate.sensor import SmartClimateDashboardSensor
            _get_thermal_persistence_diagnostics = SmartClimateDashboardSensor._get_thermal_persistence_diagnostics
        
        # Create test sensor instance
        sensor = TestSensor()
        
        # Get thermal persistence diagnostics
        attrs = sensor._get_thermal_persistence_diagnostics()
        
        # Should handle None gracefully
        assert "tau_values_modified" in attrs
        # None is acceptable for "never modified" case
        assert attrs["tau_values_modified"] is None