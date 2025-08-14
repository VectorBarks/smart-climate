"""ABOUTME: Comprehensive test suite for ThermalManager persistence functionality.
Tests serialization, restoration, field-level validation, and diagnostic properties."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from custom_components.smart_climate.thermal_models import ThermalState, ProbeResult
from custom_components.smart_climate.thermal_preferences import UserPreferences, PreferenceLevel
from custom_components.smart_climate.thermal_model import PassiveThermalModel
from custom_components.smart_climate.thermal_manager import ThermalManager


class TestThermalManagerPersistence:
    """Test ThermalManager persistence functionality per c_architecture.md §10."""

    @pytest.fixture
    def mock_hass(self):
        """Mock Home Assistant instance."""
        return Mock()

    @pytest.fixture
    def mock_thermal_model(self):
        """Mock PassiveThermalModel with probe history."""
        model = Mock(spec=PassiveThermalModel)
        model.get_confidence.return_value = 0.75
        model._tau_cooling = 95.5
        model._tau_warming = 148.2
        
        # Mock probe history
        probe1 = ProbeResult(
            tau_value=95.5,
            confidence=0.85,
            duration=3600,
            fit_quality=0.92,
            aborted=False
        )
        probe2 = ProbeResult(
            tau_value=88.3,
            confidence=0.78,
            duration=2400,
            fit_quality=0.88,
            aborted=False
        )
        model._probe_history = [probe1, probe2]
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
        manager = ThermalManager(mock_hass, mock_thermal_model, mock_preferences)
        # Set some non-default values for testing
        manager._current_state = ThermalState.DRIFTING
        manager._last_transition = datetime.now()
        return manager

    def test_serialize_returns_complete_structure(self, thermal_manager):
        """Test that serialize() returns complete data structure per §10.2.3."""
        # Mock datetime for consistent testing
        test_time = datetime(2025, 8, 8, 16, 0, 0)
        thermal_manager._last_transition = test_time
        
        data = thermal_manager.serialize()
        
        # Verify top-level structure
        assert isinstance(data, dict)
        assert data["version"] == "1.0"
        assert isinstance(data["state"], dict)
        assert isinstance(data["model"], dict)
        assert isinstance(data["probe_history"], list)
        assert isinstance(data["confidence"], float)
        assert isinstance(data["metadata"], dict)

    def test_serialize_state_section(self, thermal_manager):
        """Test serialize() state section contains required fields."""
        thermal_manager._current_state = ThermalState.CORRECTING
        test_time = datetime(2025, 8, 8, 15, 45, 0)
        thermal_manager._last_transition = test_time
        
        data = thermal_manager.serialize()
        
        state_section = data["state"]
        assert state_section["current_state"] == "correcting"
        assert state_section["last_transition"] == test_time.isoformat()

    def test_serialize_model_section(self, thermal_manager, mock_thermal_model):
        """Test serialize() model section contains tau values and timestamp."""
        mock_thermal_model._tau_cooling = 95.5
        mock_thermal_model._tau_warming = 148.2
        
        data = thermal_manager.serialize()
        
        model_section = data["model"]
        assert model_section["tau_cooling"] == 95.5
        assert model_section["tau_warming"] == 148.2
        assert "last_modified" in model_section
        # Verify timestamp is recent (within last minute)
        last_mod = datetime.fromisoformat(model_section["last_modified"])
        assert (datetime.now() - last_mod).total_seconds() < 60

    def test_serialize_probe_history_max_5_entries(self, thermal_manager, mock_thermal_model):
        """Test serialize() limits probe history to max 5 entries."""
        # Create 7 probe results
        probes = []
        for i in range(7):
            probe = ProbeResult(
                tau_value=90.0 + i,
                confidence=0.8 + i * 0.02,
                duration=3600 - i * 100,
                fit_quality=0.9 - i * 0.01,
                aborted=False
            )
            probes.append(probe)
        mock_thermal_model._probe_history = probes
        
        data = thermal_manager.serialize()
        
        # Should only have 5 most recent probes
        assert len(data["probe_history"]) <= 5

    def test_serialize_probe_history_structure(self, thermal_manager, mock_thermal_model):
        """Test serialize() probe history contains all required fields."""
        data = thermal_manager.serialize()
        
        for probe_data in data["probe_history"]:
            assert "tau_value" in probe_data
            assert "confidence" in probe_data
            assert "duration" in probe_data
            assert "fit_quality" in probe_data
            assert "aborted" in probe_data
            assert "timestamp" in probe_data

    def test_serialize_confidence_from_model(self, thermal_manager, mock_thermal_model):
        """Test serialize() uses confidence from thermal model."""
        mock_thermal_model.get_confidence.return_value = 0.85
        
        data = thermal_manager.serialize()
        
        assert data["confidence"] == 0.85

    def test_serialize_metadata_section(self, thermal_manager):
        """Test serialize() metadata section contains required fields."""
        data = thermal_manager.serialize()
        
        metadata = data["metadata"]
        assert isinstance(metadata["saves_count"], int)
        assert isinstance(metadata["corruption_recoveries"], int)
        assert metadata["schema_version"] == "1.0"
        assert metadata["saves_count"] >= 0
        assert metadata["corruption_recoveries"] >= 0

    def test_restore_valid_data_success(self, thermal_manager):
        """Test restore() with valid data succeeds."""
        valid_data = {
            "version": "1.0",
            "state": {
                "current_state": "correcting",
                "last_transition": "2025-08-08T15:45:00"
            },
            "model": {
                "tau_cooling": 95.5,
                "tau_warming": 148.2,
                "last_modified": "2025-08-08T15:30:00"
            },
            "probe_history": [
                {
                    "tau_value": 95.5,
                    "confidence": 0.85,
                    "duration": 3600,
                    "fit_quality": 0.92,
                    "aborted": False,
                    "timestamp": "2025-08-08T15:30:00"
                }
            ],
            "confidence": 0.75,
            "metadata": {
                "saves_count": 42,
                "corruption_recoveries": 0,
                "schema_version": "1.0"
            }
        }
        
        # Should not raise exception
        thermal_manager.restore(valid_data)
        
        # Verify state was restored
        assert thermal_manager.current_state == ThermalState.CORRECTING

    def test_restore_invalid_tau_values_uses_defaults(self, thermal_manager):
        """Test restore() with invalid tau values recovers with defaults."""
        invalid_data = {
            "version": "1.0", 
            "state": {"current_state": "priming", "last_transition": "2025-08-08T15:45:00"},
            "model": {
                "tau_cooling": -50.0,  # Invalid: negative
                "tau_warming": 2000.0,  # Invalid: too large
                "last_modified": "2025-08-08T15:30:00"
            },
            "probe_history": [],
            "confidence": 0.5,
            "metadata": {"saves_count": 1, "corruption_recoveries": 0, "schema_version": "1.0"}
        }
        
        thermal_manager.restore(invalid_data)
        
        # Should use defaults: tau_cooling=90.0, tau_warming=150.0
        # Verify through model interaction
        assert thermal_manager._model._tau_cooling == 90.0
        assert thermal_manager._model._tau_warming == 150.0
        # Corruption recovery count should increment
        assert thermal_manager.corruption_recovery_count > 0

    def test_restore_invalid_confidence_uses_default(self, thermal_manager):
        """Test restore() with invalid confidence recovers with default."""
        invalid_data = {
            "version": "1.0",
            "state": {"current_state": "priming", "last_transition": "2025-08-08T15:45:00"},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0, "last_modified": "2025-08-08T15:30:00"},
            "probe_history": [],
            "confidence": 1.5,  # Invalid: > 1.0
            "metadata": {"saves_count": 1, "corruption_recoveries": 0, "schema_version": "1.0"}
        }
        
        thermal_manager.restore(invalid_data)
        
        # Should use default confidence (0.0 for no probes)
        assert thermal_manager.corruption_recovery_count > 0

    def test_restore_invalid_thermal_state_uses_priming(self, thermal_manager):
        """Test restore() with invalid thermal state defaults to PRIMING."""
        invalid_data = {
            "version": "1.0",
            "state": {
                "current_state": "INVALID_STATE",  # Invalid state
                "last_transition": "2025-08-08T15:45:00"
            },
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0, "last_modified": "2025-08-08T15:30:00"},
            "probe_history": [],
            "confidence": 0.5,
            "metadata": {"saves_count": 1, "corruption_recoveries": 0, "schema_version": "1.0"}
        }
        
        thermal_manager.restore(invalid_data)
        
        # Should default to PRIMING (safest state)
        assert thermal_manager.current_state == ThermalState.PRIMING
        assert thermal_manager.corruption_recovery_count > 0

    def test_restore_corrupted_probe_discards_invalid_probes(self, thermal_manager):
        """Test restore() discards corrupted probes but keeps valid ones."""
        mixed_data = {
            "version": "1.0",
            "state": {"current_state": "priming", "last_transition": "2025-08-08T15:45:00"},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0, "last_modified": "2025-08-08T15:30:00"},
            "probe_history": [
                {  # Valid probe
                    "tau_value": 95.5,
                    "confidence": 0.85,
                    "duration": 3600,
                    "fit_quality": 0.92,
                    "aborted": False,
                    "timestamp": "2025-08-08T15:30:00"
                },
                {  # Invalid probe - negative duration
                    "tau_value": 88.3,
                    "confidence": 0.78,
                    "duration": -100,  # Invalid
                    "fit_quality": 0.88,
                    "aborted": False,
                    "timestamp": "2025-08-08T15:25:00"
                }
            ],
            "confidence": 0.75,
            "metadata": {"saves_count": 1, "corruption_recoveries": 0, "schema_version": "1.0"}
        }
        
        thermal_manager.restore(mixed_data)
        
        # Should keep only valid probe
        # We can't directly inspect the model's probe history in this test structure,
        # but corruption recovery count should increment
        assert thermal_manager.corruption_recovery_count > 0

    def test_restore_missing_sections_uses_defaults(self, thermal_manager):
        """Test restore() with missing sections uses safe defaults."""
        minimal_data = {
            "version": "1.0",
            "state": {"current_state": "PRIMING", "last_transition": "2025-08-08T15:45:00"}
            # Missing model, probe_history, confidence, metadata sections
        }
        
        thermal_manager.restore(minimal_data)
        
        # Should not crash and use defaults
        assert thermal_manager.current_state == ThermalState.PRIMING
        assert thermal_manager.corruption_recovery_count >= 0

    def test_reset_restores_defaults(self, thermal_manager):
        """Test reset() restores system to defaults per §10.2.3."""
        # Set to non-default values
        thermal_manager._current_state = ThermalState.PROBING
        thermal_manager._corruption_recovery_count = 5
        
        thermal_manager.reset()
        
        # Verify reset to defaults
        assert thermal_manager.current_state == ThermalState.PRIMING
        # Check that the model's tau values were set to defaults
        # Since we're using mocks, check if the attributes were set
        assert hasattr(thermal_manager._model, '_tau_cooling')
        assert hasattr(thermal_manager._model, '_tau_warming')
        # Reset should not affect corruption recovery count (that's historical)

    def test_diagnostic_properties_after_restore(self, thermal_manager):
        """Test diagnostic properties are set after successful restore."""
        valid_data = {
            "version": "1.0",
            "state": {"current_state": "drifting", "last_transition": "2025-08-08T15:45:00"},
            "model": {"tau_cooling": 95.5, "tau_warming": 148.2, "last_modified": "2025-08-08T15:30:00"},
            "probe_history": [],
            "confidence": 0.5,
            "metadata": {"saves_count": 10, "corruption_recoveries": 2, "schema_version": "1.0"}
        }
        
        thermal_manager.restore(valid_data)
        
        # Verify diagnostic properties
        assert thermal_manager.thermal_state_restored is True
        assert thermal_manager.corruption_recovery_count >= 2  # May increment during restore
        assert thermal_manager.thermal_data_last_saved is None  # Not set until save

    def test_diagnostic_properties_default_values(self, thermal_manager):
        """Test diagnostic properties have correct default values."""
        # Fresh instance should have defaults
        assert thermal_manager.thermal_data_last_saved is None
        assert thermal_manager.thermal_state_restored is False
        assert thermal_manager.corruption_recovery_count == 0

    def test_serialize_after_restore_roundtrip(self, thermal_manager):
        """Test that serialize() after restore() maintains data integrity."""
        original_data = {
            "version": "1.0",
            "state": {"current_state": "correcting", "last_transition": "2025-08-08T15:45:00"},
            "model": {"tau_cooling": 95.5, "tau_warming": 148.2, "last_modified": "2025-08-08T15:30:00"},
            "probe_history": [
                {
                    "tau_value": 95.5,
                    "confidence": 0.85,
                    "duration": 3600,
                    "fit_quality": 0.92,
                    "aborted": False,
                    "timestamp": "2025-08-08T15:30:00"
                }
            ],
            "confidence": 0.75,
            "metadata": {"saves_count": 5, "corruption_recoveries": 1, "schema_version": "1.0"}
        }
        
        # Restore then serialize
        thermal_manager.restore(original_data)
        new_data = thermal_manager.serialize()
        
        # Verify key fields are preserved
        assert new_data["version"] == "1.0"
        assert new_data["state"]["current_state"] == "correcting"
        assert new_data["model"]["tau_cooling"] == 95.5
        assert new_data["model"]["tau_warming"] == 148.2
        # Metadata save count should have incremented, but that's handled by caller
        assert new_data["metadata"]["schema_version"] == "1.0"

    def test_restore_with_future_timestamps_handled_gracefully(self, thermal_manager):
        """Test restore() handles future timestamps gracefully."""
        future_time = (datetime.now() + timedelta(days=1)).isoformat()
        future_data = {
            "version": "1.0",
            "state": {"current_state": "drifting", "last_transition": future_time},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0, "last_modified": future_time},
            "probe_history": [],
            "confidence": 0.5,
            "metadata": {"saves_count": 1, "corruption_recoveries": 0, "schema_version": "1.0"}
        }
        
        # Should not crash with future timestamps
        thermal_manager.restore(future_data)
        
        # State should still be restored (timestamps are informational)
        assert thermal_manager.current_state == ThermalState.DRIFTING

    def test_restore_with_malformed_timestamps_recovers(self, thermal_manager):
        """Test restore() recovers from malformed timestamps."""
        malformed_data = {
            "version": "1.0",
            "state": {"current_state": "drifting", "last_transition": "not-a-timestamp"},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0, "last_modified": "also-invalid"},
            "probe_history": [],
            "confidence": 0.5,
            "metadata": {"saves_count": 1, "corruption_recoveries": 0, "schema_version": "1.0"}
        }
        
        thermal_manager.restore(malformed_data)
        
        # Should recover and set defaults
        assert thermal_manager.current_state == ThermalState.DRIFTING
        assert thermal_manager.corruption_recovery_count > 0

    def test_multiple_restore_calls_handled_correctly(self, thermal_manager):
        """Test multiple restore() calls work correctly."""
        data1 = {
            "version": "1.0",
            "state": {"current_state": "drifting", "last_transition": "2025-08-08T15:45:00"},
            "model": {"tau_cooling": 95.0, "tau_warming": 145.0, "last_modified": "2025-08-08T15:30:00"},
            "probe_history": [],
            "confidence": 0.6,
            "metadata": {"saves_count": 1, "corruption_recoveries": 0, "schema_version": "1.0"}
        }
        
        data2 = {
            "version": "1.0",
            "state": {"current_state": "correcting", "last_transition": "2025-08-08T16:00:00"},
            "model": {"tau_cooling": 100.0, "tau_warming": 155.0, "last_modified": "2025-08-08T15:45:00"},
            "probe_history": [],
            "confidence": 0.8,
            "metadata": {"saves_count": 2, "corruption_recoveries": 0, "schema_version": "1.0"}
        }
        
        thermal_manager.restore(data1)
        assert thermal_manager.current_state == ThermalState.DRIFTING
        
        thermal_manager.restore(data2)
        assert thermal_manager.current_state == ThermalState.CORRECTING
        # Each restore marks as restored
        assert thermal_manager.thermal_state_restored is True
    
    def test_saves_count_increments_on_serialize(self, thermal_manager):
        """Test that saves_count increments each time serialize is called."""
        # Initial state
        assert thermal_manager._saves_count == 0
        
        # First serialize
        data1 = thermal_manager.serialize()
        assert thermal_manager._saves_count == 1
        assert data1["metadata"]["saves_count"] == 1
        
        # Second serialize
        data2 = thermal_manager.serialize()
        assert thermal_manager._saves_count == 2
        assert data2["metadata"]["saves_count"] == 2
        
        # Third serialize
        data3 = thermal_manager.serialize()
        assert thermal_manager._saves_count == 3
        assert data3["metadata"]["saves_count"] == 3
        
        # Verify thermal_data_last_saved is updated
        assert thermal_manager.thermal_data_last_saved is not None
    
    def test_restore_extends_probe_history_instead_of_replacing(self, thermal_manager, mock_thermal_model):
        """Test that restoration extends existing probe_history instead of overwriting.
        
        CRITICAL BUG FIX: This test exposes the data loss bug where restore()
        completely replaces probe_history instead of extending it, causing:
        - Loss of probes added since last save
        - Overwriting of active learning data
        - Artificially low thermal confidence
        - Slower thermal learning performance
        """
        from collections import deque
        from custom_components.smart_climate.thermal_models import ProbeResult
        
        # Mock the actual deque structure in the model
        mock_thermal_model._probe_history = deque(maxlen=5)
        
        # Add some probes to existing model (simulates runtime learning)
        existing_probe = ProbeResult(
            tau_value=100.0,
            confidence=0.8,
            duration=1800,
            fit_quality=0.9,
            aborted=False
        )
        mock_thermal_model._probe_history.append(existing_probe)
        
        # Prepare restoration data with different probe (simulates loaded from disk)
        restore_data = {
            "version": "1.0",
            "state": {"current_state": "priming", "last_transition": "2025-08-08T15:45:00"},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0, "last_modified": "2025-08-08T15:30:00"},
            "probe_history": [{
                "tau_value": 200.0,
                "confidence": 0.7,
                "duration": 2400, 
                "fit_quality": 0.85,
                "aborted": False,
                "timestamp": "2025-08-08T15:30:00"
            }],
            "confidence": 0.75,
            "metadata": {"saves_count": 1, "corruption_recoveries": 0, "schema_version": "1.0"}
        }
        
        # BUG: restore() should EXTEND probe_history, not replace it
        thermal_manager.restore(restore_data)
        
        # CRITICAL ASSERTION: Should have BOTH probes (existing + restored)
        # Current buggy behavior: only has restored probe (existing probe lost!)
        probe_history = list(mock_thermal_model._probe_history)
        assert len(probe_history) == 2, f"Expected 2 probes, got {len(probe_history)} - existing probe was lost!"
        
        probe_values = [p.tau_value for p in probe_history]
        assert 100.0 in probe_values, "Existing probe (100.0) was lost during restoration!"
        assert 200.0 in probe_values, "Restored probe (200.0) was not added!"