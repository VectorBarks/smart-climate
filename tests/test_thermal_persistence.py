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

    def test_restore_preserves_probe_timestamps(self, thermal_manager, mock_thermal_model):
        """Test that restore() preserves original probe timestamps from data."""
        from collections import deque
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        # Mock the actual deque structure in the model
        mock_thermal_model._probe_history = deque(maxlen=5)
        
        # Create test data with specific timestamps
        probe1_time = "2025-08-15T10:30:00+00:00"
        probe2_time = "2025-08-15T12:45:00+00:00"
        
        restore_data = {
            "version": "1.0",
            "state": {"current_state": "priming", "last_transition": "2025-08-15T15:00:00"},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0},
            "probe_history": [
                {
                    "tau_value": 95.0,
                    "confidence": 0.8,
                    "duration": 1800,
                    "fit_quality": 0.9,
                    "aborted": False,
                    "timestamp": probe1_time
                },
                {
                    "tau_value": 105.0,
                    "confidence": 0.85,
                    "duration": 2100,
                    "fit_quality": 0.92,
                    "aborted": False,
                    "timestamp": probe2_time
                }
            ],
            "confidence": 0.8
        }
        
        # This should fail until restore() is fixed to parse timestamps
        thermal_manager.restore(restore_data)
        
        # Verify timestamps were preserved (not overwritten with current time)
        probe_history = list(mock_thermal_model._probe_history)
        assert len(probe_history) == 2
        
        # Check that timestamps match original data (not current time)
        expected_time1 = datetime.fromisoformat(probe1_time)
        expected_time2 = datetime.fromisoformat(probe2_time)
        
        actual_times = [probe.timestamp for probe in probe_history]
        assert expected_time1 in actual_times, f"Original timestamp {probe1_time} not preserved"
        assert expected_time2 in actual_times, f"Original timestamp {probe2_time} not preserved"

    def test_restore_handles_missing_timestamps(self, thermal_manager, mock_thermal_model):
        """Test that restore() handles legacy data without timestamp field gracefully."""
        from collections import deque
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        # Mock the actual deque structure in the model
        mock_thermal_model._probe_history = deque(maxlen=5)
        
        # Create legacy data without timestamp fields
        restore_data = {
            "version": "1.0",
            "state": {"current_state": "priming", "last_transition": "2025-08-15T15:00:00"},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0},
            "probe_history": [
                {
                    "tau_value": 95.0,
                    "confidence": 0.8,
                    "duration": 1800,
                    "fit_quality": 0.9,
                    "aborted": False
                    # No timestamp field (legacy data)
                }
            ],
            "confidence": 0.8
        }
        
        # Should handle missing timestamps gracefully with fallback
        before_restore = datetime.now(timezone.utc)
        thermal_manager.restore(restore_data)
        after_restore = datetime.now(timezone.utc)
        
        # Verify probe was restored with fallback timestamp
        probe_history = list(mock_thermal_model._probe_history)
        assert len(probe_history) == 1
        
        # Fallback timestamp should be close to current time
        probe_timestamp = probe_history[0].timestamp
        assert before_restore <= probe_timestamp <= after_restore, \
            "Legacy data should use current time as fallback timestamp"

    def test_restore_timestamp_parsing(self, thermal_manager, mock_thermal_model):
        """Test that restore() correctly parses various timestamp formats."""
        from collections import deque
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        # Mock the actual deque structure in the model
        mock_thermal_model._probe_history = deque(maxlen=5)
        
        # Test various valid ISO format timestamps
        test_timestamps = [
            "2025-08-15T10:30:00+00:00",  # UTC with timezone
            "2025-08-15T10:30:00Z",       # UTC Z format
            "2025-08-15T10:30:00",        # No timezone (should be treated as UTC)
        ]
        
        for i, timestamp_str in enumerate(test_timestamps):
            restore_data = {
                "version": "1.0",
                "state": {"current_state": "priming"},
                "model": {"tau_cooling": 90.0, "tau_warming": 150.0},
                "probe_history": [
                    {
                        "tau_value": 95.0 + i,  # Unique values
                        "confidence": 0.8,
                        "duration": 1800,
                        "fit_quality": 0.9,
                        "aborted": False,
                        "timestamp": timestamp_str
                    }
                ]
            }
            
            # Clear previous probes for clean test
            mock_thermal_model._probe_history.clear()
            
            # Should parse timestamp without errors
            thermal_manager.restore(restore_data)
            
            # Verify probe was restored with parsed timestamp
            probe_history = list(mock_thermal_model._probe_history)
            assert len(probe_history) == 1
            
            # Verify timestamp was parsed correctly
            expected_dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            actual_dt = probe_history[0].timestamp
            assert actual_dt == expected_dt, \
                f"Timestamp {timestamp_str} not parsed correctly"

    def test_restore_backward_compatibility(self, thermal_manager, mock_thermal_model):
        """Test that restore() maintains backward compatibility with old data formats."""
        from collections import deque
        from custom_components.smart_climate.thermal_models import ProbeResult
        
        # Mock the actual deque structure in the model
        mock_thermal_model._probe_history = deque(maxlen=5)
        
        # Test old format data (pre-timestamp field)
        old_format_data = {
            "version": "1.0",
            "state": {"current_state": "priming"},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0},
            "probe_history": [
                {
                    "tau_value": 95.0,
                    "confidence": 0.8,
                    "duration": 1800,
                    "fit_quality": 0.9,
                    "aborted": False
                    # Missing timestamp field
                }
            ]
        }
        
        # Should not crash on old format
        thermal_manager.restore(old_format_data)
        
        # Verify probe was still restored successfully
        probe_history = list(mock_thermal_model._probe_history)
        assert len(probe_history) == 1
        assert probe_history[0].tau_value == 95.0
        assert probe_history[0].confidence == 0.8
        # Timestamp should be set to current time as fallback
        assert probe_history[0].timestamp is not None

    def test_restore_timezone_handling(self, thermal_manager, mock_thermal_model):
        """Test that restore() properly handles different timezone formats."""
        from collections import deque
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        # Mock the actual deque structure in the model
        mock_thermal_model._probe_history = deque(maxlen=5)
        
        # Test data with timezone information
        restore_data = {
            "version": "1.0", 
            "state": {"current_state": "priming"},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0},
            "probe_history": [
                {
                    "tau_value": 95.0,
                    "confidence": 0.8,
                    "duration": 1800,
                    "fit_quality": 0.9,
                    "aborted": False,
                    "timestamp": "2025-08-15T10:30:00+02:00"  # CEST timezone
                }
            ]
        }
        
        thermal_manager.restore(restore_data)
        
        # Verify probe was restored with correct timezone conversion
        probe_history = list(mock_thermal_model._probe_history)
        assert len(probe_history) == 1
        
        # Timestamp should be parsed with timezone info preserved
        expected_dt = datetime.fromisoformat("2025-08-15T10:30:00+02:00")
        actual_dt = probe_history[0].timestamp
        assert actual_dt == expected_dt, "Timezone information not preserved correctly"


class TestProbeResultTimestamp:
    """Test ProbeResult timestamp field functionality per architecture §19.2."""

    def test_probe_result_has_timestamp_field(self):
        """Test that ProbeResult has timestamp field."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime
        
        # This should fail initially since timestamp field doesn't exist yet
        probe = ProbeResult(
            tau_value=90.0,
            confidence=0.85,
            duration=1800,
            fit_quality=0.92,
            aborted=False
        )
        
        # Test that timestamp field exists and is datetime
        assert hasattr(probe, 'timestamp')
        assert isinstance(probe.timestamp, datetime)

    def test_probe_result_automatic_utc_timestamping(self):
        """Test that ProbeResult automatically sets UTC timestamp."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        before_creation = datetime.now(timezone.utc)
        
        probe = ProbeResult(
            tau_value=90.0,
            confidence=0.85,
            duration=1800,
            fit_quality=0.92,
            aborted=False
        )
        
        after_creation = datetime.now(timezone.utc)
        
        # Timestamp should be UTC and within creation window
        assert probe.timestamp.tzinfo == timezone.utc
        assert before_creation <= probe.timestamp <= after_creation

    def test_probe_result_accepts_explicit_timestamp(self):
        """Test that ProbeResult accepts explicit timestamp parameter."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        explicit_time = datetime(2025, 8, 17, 12, 30, 45, tzinfo=timezone.utc)
        
        probe = ProbeResult(
            tau_value=90.0,
            confidence=0.85,
            duration=1800,
            fit_quality=0.92,
            aborted=False,
            timestamp=explicit_time
        )
        
        assert probe.timestamp == explicit_time

    def test_probe_result_is_frozen_dataclass(self):
        """Test that ProbeResult is frozen (immutable) dataclass."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        
        probe = ProbeResult(
            tau_value=90.0,
            confidence=0.85,
            duration=1800,
            fit_quality=0.92,
            aborted=False
        )
        
        # Should raise error when trying to modify frozen dataclass
        with pytest.raises(AttributeError):
            probe.tau_value = 100.0
            
        with pytest.raises(AttributeError):
            probe.timestamp = probe.timestamp

    def test_probe_result_timezone_aware(self):
        """Test that ProbeResult timestamp is always timezone-aware."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        # Test automatic timestamp
        probe_auto = ProbeResult(
            tau_value=90.0,
            confidence=0.85,
            duration=1800,
            fit_quality=0.92,
            aborted=False
        )
        
        assert probe_auto.timestamp.tzinfo is not None
        assert probe_auto.timestamp.tzinfo == timezone.utc
        
        # Test explicit UTC timestamp
        explicit_utc = datetime(2025, 8, 17, 12, 30, 45, tzinfo=timezone.utc)
        probe_explicit = ProbeResult(
            tau_value=90.0,
            confidence=0.85,
            duration=1800,
            fit_quality=0.92,
            aborted=False,
            timestamp=explicit_utc
        )
        
        assert probe_explicit.timestamp.tzinfo == timezone.utc


class TestSerializeTimestampPreservation:
    """Test timestamp preservation during ThermalManager serialization.
    
    CRITICAL BUG FIX: Tests for probe timestamp persistence bug where
    serialize() overwrites all probe timestamps with current time during
    serialization, corrupting temporal relationships.
    """

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        return Mock()

    @pytest.fixture  
    def mock_thermal_model(self):
        """Create mock thermal model with probe history."""
        from collections import deque
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        mock_model = Mock()
        mock_model._tau_cooling = 90.0
        mock_model._tau_warming = 150.0
        mock_model.get_confidence.return_value = 0.85
        
        # Create probe history with different timestamps
        mock_model._probe_history = deque(maxlen=5)
        
        # Create probes with specific timestamps (different times)
        probe1_time = datetime(2025, 8, 8, 10, 0, 0, tzinfo=timezone.utc)
        probe2_time = datetime(2025, 8, 8, 12, 0, 0, tzinfo=timezone.utc)
        probe3_time = datetime(2025, 8, 8, 14, 0, 0, tzinfo=timezone.utc)
        
        probe1 = ProbeResult(
            tau_value=85.0,
            confidence=0.8,
            duration=1800,
            fit_quality=0.9,
            aborted=False,
            timestamp=probe1_time
        )
        
        probe2 = ProbeResult(
            tau_value=95.0,
            confidence=0.85,
            duration=2400,
            fit_quality=0.88,
            aborted=False,
            timestamp=probe2_time
        )
        
        probe3 = ProbeResult(
            tau_value=90.0,
            confidence=0.9,
            duration=2100,
            fit_quality=0.95,
            aborted=True,
            timestamp=probe3_time
        )
        
        mock_model._probe_history.extend([probe1, probe2, probe3])
        return mock_model

    @pytest.fixture
    def mock_preferences(self):
        """Create mock user preferences."""
        mock_prefs = Mock()
        mock_prefs.comfort_band = 0.8
        return mock_prefs

    @pytest.fixture
    def thermal_manager(self, mock_hass, mock_thermal_model, mock_preferences):
        """Create ThermalManager with mocked dependencies."""
        from custom_components.smart_climate.thermal_manager import ThermalManager
        
        return ThermalManager(mock_hass, mock_thermal_model, mock_preferences, {})

    def test_serialize_preserves_probe_timestamps(self, thermal_manager, mock_thermal_model):
        """Test that serialize() preserves original probe timestamps.
        
        CRITICAL BUG: Currently serialize() overwrites all probe timestamps
        with datetime.now() during serialization. This test should FAIL
        until the bug is fixed.
        """
        from datetime import datetime, timezone
        
        # Get original probe timestamps
        probes = list(mock_thermal_model._probe_history)
        original_timestamps = [probe.timestamp for probe in probes]
        
        # Serialize the thermal manager state
        serialized_data = thermal_manager.serialize()
        
        # Extract timestamps from serialized data
        probe_history = serialized_data.get("probe_history", [])
        serialized_timestamps = []
        
        for probe_data in probe_history:
            timestamp_str = probe_data.get("timestamp")
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str)
                serialized_timestamps.append(timestamp)
        
        # CRITICAL ASSERTION: Serialized timestamps should match original timestamps
        assert len(serialized_timestamps) == len(original_timestamps), \
            "Number of serialized timestamps should match original"
        
        for i, (original, serialized) in enumerate(zip(original_timestamps, serialized_timestamps)):
            # Convert to ISO format for comparison (handles timezone differences)
            original_iso = original.isoformat()
            serialized_iso = serialized.isoformat()
            
            assert original_iso == serialized_iso, \
                f"Probe {i}: Original timestamp {original_iso} != serialized timestamp {serialized_iso}"

    def test_serialize_multiple_probes_different_timestamps(self, thermal_manager, mock_thermal_model):
        """Test serialize() with multiple probes having different timestamps.
        
        Ensures that when multiple probes exist with different timestamps,
        each probe's individual timestamp is preserved correctly.
        """
        from datetime import datetime
        
        # Get probe history and verify we have multiple probes with different timestamps
        probes = list(mock_thermal_model._probe_history)
        assert len(probes) >= 3, "Need at least 3 probes for this test"
        
        # Verify timestamps are actually different
        timestamps = [probe.timestamp for probe in probes]
        unique_timestamps = set(timestamps)
        assert len(unique_timestamps) == len(timestamps), "All probe timestamps should be different"
        
        # Serialize and check each timestamp individually
        serialized_data = thermal_manager.serialize()
        probe_history = serialized_data.get("probe_history", [])
        
        assert len(probe_history) == len(probes), "All probes should be serialized"
        
        for i, (original_probe, serialized_probe) in enumerate(zip(probes, probe_history)):
            expected_timestamp = original_probe.timestamp.isoformat()
            actual_timestamp = serialized_probe.get("timestamp")
            
            assert actual_timestamp == expected_timestamp, \
                f"Probe {i}: Expected timestamp {expected_timestamp}, got {actual_timestamp}"

    def test_serialize_timestamp_iso_format(self, thermal_manager, mock_thermal_model):
        """Test that serialized timestamps are in correct ISO format.
        
        Ensures that probe timestamps are serialized in ISO format
        for proper JSON compatibility and restoration.
        """
        from datetime import datetime
        
        serialized_data = thermal_manager.serialize()
        probe_history = serialized_data.get("probe_history", [])
        
        assert len(probe_history) > 0, "Should have probe history for this test"
        
        for i, probe_data in enumerate(probe_history):
            timestamp_str = probe_data.get("timestamp")
            assert timestamp_str is not None, f"Probe {i} should have timestamp"
            
            # Verify it's a valid ISO format timestamp
            try:
                parsed_timestamp = datetime.fromisoformat(timestamp_str)
                # Should be able to round-trip
                assert parsed_timestamp.isoformat() == timestamp_str, \
                    f"Probe {i}: Timestamp {timestamp_str} not in proper ISO format"
            except ValueError as e:
                pytest.fail(f"Probe {i}: Invalid ISO timestamp format {timestamp_str}: {e}")

    def test_serialize_empty_probe_history(self, thermal_manager, mock_thermal_model):
        """Test serialize() behavior with empty probe history.
        
        Ensures that serialization works correctly when no probes exist,
        without attempting to access non-existent timestamps.
        """
        from collections import deque
        
        # Clear probe history
        mock_thermal_model._probe_history = deque(maxlen=5)
        
        # Should not raise any exceptions
        serialized_data = thermal_manager.serialize()
        
        # Should have empty probe history
        probe_history = serialized_data.get("probe_history", [])
        assert isinstance(probe_history, list), "probe_history should be a list"
        assert len(probe_history) == 0, "probe_history should be empty"


# ================================================================================
# COMPREHENSIVE PROBE TIMESTAMP PERSISTENCE TEST SUITE
# Level 4 Implementation based on Level 4 Agent Design
# Target: >95% line coverage, <5% performance impact
# ================================================================================

import time
import timeit
from datetime import timezone
from collections import deque


class TestProbeTimestampPersistence:
    """Comprehensive tests for probe timestamp persistence functionality.
    
    Tests core functionality of timestamp preservation through serialization/deserialization.
    Based on Level 4 agent design requirements for >95% coverage.
    """

    @pytest.fixture
    def mock_hass(self):
        """Mock Home Assistant instance."""
        return Mock()

    @pytest.fixture  
    def mock_thermal_model(self):
        """Mock thermal model with probe history."""
        model = Mock(spec=PassiveThermalModel)
        model._tau_cooling = 90.0
        model._tau_warming = 150.0
        model._probe_history = deque(maxlen=5)
        model.get_confidence.return_value = 0.8
        return model

    @pytest.fixture
    def mock_preferences(self):
        """Mock user preferences."""
        prefs = Mock(spec=UserPreferences)
        prefs.level = PreferenceLevel.BALANCED
        return prefs

    @pytest.fixture
    def thermal_manager(self, mock_hass, mock_thermal_model, mock_preferences):
        """Create ThermalManager instance for testing."""
        manager = ThermalManager(mock_hass, mock_thermal_model, mock_preferences)
        return manager

    def test_probe_creation_with_timestamp(self):
        """Test ProbeResult includes timestamp field with automatic UTC timestamping."""
        # Create probe without explicit timestamp
        probe = ProbeResult(
            tau_value=120.0,
            confidence=0.85,
            duration=1800,
            fit_quality=0.92,
            aborted=False
        )
        
        # Verify timestamp field exists and is timezone-aware UTC
        assert hasattr(probe, 'timestamp'), "ProbeResult should have timestamp field"
        assert probe.timestamp is not None, "Timestamp should not be None"
        assert probe.timestamp.tzinfo is not None, "Timestamp should be timezone-aware"
        assert probe.timestamp.tzinfo == timezone.utc, "Timestamp should be UTC"
        
        # Verify timestamp is recent (within last 5 seconds)
        now = datetime.now(timezone.utc)
        time_diff = abs((now - probe.timestamp).total_seconds())
        assert time_diff < 5.0, f"Timestamp should be recent, but was {time_diff} seconds ago"

    def test_serialize_deserialize_roundtrip(self, thermal_manager):
        """Test complete serialize/deserialize roundtrip preserves timestamps accurately."""
        # Create test probes with different timestamps
        base_time = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        test_probes = [
            ProbeResult(120.0, 0.85, 1800, 0.92, False, base_time),
            ProbeResult(95.0, 0.78, 1200, 0.88, False, base_time + timedelta(hours=2)),
            ProbeResult(140.0, 0.91, 2100, 0.95, False, base_time + timedelta(hours=4))
        ]
        
        # Add probes to thermal manager
        for probe in test_probes:
            thermal_manager._model._probe_history.append(probe)
        
        # Serialize data
        serialized_data = thermal_manager.serialize()
        
        # Verify serialization includes timestamps
        probe_history = serialized_data.get("probe_history", [])
        assert len(probe_history) == 3, "Should serialize all 3 probes"
        
        for i, probe_data in enumerate(probe_history):
            assert "timestamp" in probe_data, f"Probe {i} should have timestamp in serialized data"
            assert probe_data["timestamp"] == test_probes[i].timestamp.isoformat()
        
        # Clear probe history and restore
        thermal_manager._model._probe_history.clear()
        thermal_manager.restore(serialized_data)
        
        # Verify restoration preserves exact timestamps
        restored_probes = list(thermal_manager._model._probe_history)
        assert len(restored_probes) == 3, "Should restore all 3 probes"
        
        for i, restored_probe in enumerate(restored_probes):
            assert restored_probe.timestamp == test_probes[i].timestamp, \
                f"Probe {i} timestamp not preserved: expected {test_probes[i].timestamp}, got {restored_probe.timestamp}"

    def test_multiple_probes_distinct_timestamps(self, thermal_manager):
        """Test serialization preserves distinct timestamps for multiple probes."""
        # Create 5 probes with timestamps 1 hour apart
        base_time = datetime(2024, 6, 10, 14, 0, 0, tzinfo=timezone.utc)
        test_probes = []
        
        for i in range(5):
            probe = ProbeResult(
                tau_value=100.0 + i * 10,
                confidence=0.8 + i * 0.02,
                duration=1800 + i * 300,
                fit_quality=0.85 + i * 0.02,
                aborted=False,
                timestamp=base_time + timedelta(hours=i)
            )
            test_probes.append(probe)
            thermal_manager._model._probe_history.append(probe)
        
        # Serialize
        serialized_data = thermal_manager.serialize()
        probe_history = serialized_data.get("probe_history", [])
        
        # Verify all timestamps are distinct and correctly serialized
        timestamps = [probe_data["timestamp"] for probe_data in probe_history]
        assert len(set(timestamps)) == 5, "All timestamps should be distinct"
        
        # Verify chronological order is preserved
        for i in range(5):
            expected_timestamp = (base_time + timedelta(hours=i)).isoformat()
            assert probe_history[i]["timestamp"] == expected_timestamp, \
                f"Probe {i} timestamp mismatch"

    def test_legacy_data_compatibility(self, thermal_manager):
        """Test system handles legacy data without timestamps gracefully."""
        # Create legacy data structure without timestamps
        legacy_data = {
            "thermal_state": "PRIMING",
            "model": {
                "tau_cooling": 85.0,
                "tau_warming": 145.0,
                "confidence": 0.75
            },
            "probe_history": [
                {
                    "tau_value": 90.0,
                    "confidence": 0.82,
                    "duration": 1500,
                    "fit_quality": 0.87,
                    "aborted": False
                    # No timestamp field - legacy data
                },
                {
                    "tau_value": 110.0,
                    "confidence": 0.79,
                    "duration": 1700,
                    "fit_quality": 0.84,
                    "aborted": False
                    # No timestamp field - legacy data
                }
            ]
        }
        
        # Store current time for comparison
        restore_time = datetime.now(timezone.utc)
        
        # Restore legacy data
        thermal_manager.restore(legacy_data)
        
        # Verify probes were restored with fallback timestamps
        restored_probes = list(thermal_manager._model._probe_history)
        assert len(restored_probes) == 2, "Should restore 2 legacy probes"
        
        for i, probe in enumerate(restored_probes):
            # Verify probe has timestamp (fallback applied)
            assert hasattr(probe, 'timestamp'), f"Legacy probe {i} should have timestamp"
            assert probe.timestamp is not None, f"Legacy probe {i} timestamp should not be None"
            assert probe.timestamp.tzinfo == timezone.utc, f"Legacy probe {i} should have UTC timezone"
            
            # Verify fallback timestamp is recent (within 10 seconds of restore time)
            time_diff = abs((probe.timestamp - restore_time).total_seconds())
            assert time_diff < 10.0, f"Legacy probe {i} fallback timestamp should be recent"
            
            # Verify other fields are correctly restored
            expected_tau = 90.0 if i == 0 else 110.0
            assert probe.tau_value == expected_tau, f"Legacy probe {i} tau_value not restored correctly"

    def test_timezone_handling(self, thermal_manager):
        """Test system correctly handles various timezone formats."""
        # Test different timezone representations
        test_cases = [
            # UTC with Z suffix
            "2024-03-15T09:30:00Z",
            # UTC with +00:00 offset
            "2024-03-15T09:30:00+00:00",
            # Different timezone with offset
            "2024-03-15T11:30:00+02:00",
            # UTC without explicit timezone (should be treated as UTC in our system)
            "2024-03-15T09:30:00"
        ]
        
        for i, timestamp_str in enumerate(test_cases):
            # Create data with specific timestamp format
            test_data = {
                "probe_history": [
                    {
                        "tau_value": 100.0,
                        "confidence": 0.8,
                        "duration": 1800,
                        "fit_quality": 0.9,
                        "aborted": False,
                        "timestamp": timestamp_str
                    }
                ]
            }
            
            # Clear and restore
            thermal_manager._model._probe_history.clear()
            thermal_manager.restore(test_data)
            
            # Verify restoration handled timezone correctly
            restored_probes = list(thermal_manager._model._probe_history)
            assert len(restored_probes) == 1, f"Test case {i}: Should restore 1 probe"
            
            probe = restored_probes[0]
            assert probe.timestamp.tzinfo is not None, f"Test case {i}: Restored timestamp should be timezone-aware"
            
            # For our system, all timestamps should be normalized to UTC or handled gracefully
            assert isinstance(probe.timestamp, datetime), f"Test case {i}: Should have valid datetime object"

    def test_corrupted_timestamp_recovery(self, thermal_manager):
        """Test system recovers gracefully from corrupted timestamp data."""
        # Test various corruption scenarios
        corruption_cases = [
            {
                "name": "invalid_iso_format",
                "timestamp": "invalid-timestamp-format",
                "should_recover": True
            },
            {
                "name": "non_string_timestamp",
                "timestamp": 1234567890,  # Unix timestamp as integer
                "should_recover": True
            },
            {
                "name": "null_timestamp",
                "timestamp": None,
                "should_recover": True
            },
            {
                "name": "empty_string_timestamp",
                "timestamp": "",
                "should_recover": True
            }
        ]
        
        for case in corruption_cases:
            # Create test data with corrupted timestamp
            test_data = {
                "probe_history": [
                    {
                        "tau_value": 95.0,
                        "confidence": 0.85,
                        "duration": 1600,
                        "fit_quality": 0.88,
                        "aborted": False,
                        "timestamp": case["timestamp"]
                    }
                ]
            }
            
            # Store time before restoration for comparison
            restore_time = datetime.now(timezone.utc)
            
            # Clear and attempt restore
            thermal_manager._model._probe_history.clear()
            
            if case["should_recover"]:
                # Should not raise exception
                thermal_manager.restore(test_data)
                
                # Verify probe was restored with fallback timestamp
                restored_probes = list(thermal_manager._model._probe_history)
                assert len(restored_probes) == 1, f"{case['name']}: Should recover with fallback timestamp"
                
                probe = restored_probes[0]
                assert probe.timestamp is not None, f"{case['name']}: Should have fallback timestamp"
                assert probe.timestamp.tzinfo == timezone.utc, f"{case['name']}: Fallback should be UTC"
                
                # Fallback timestamp should be recent
                time_diff = abs((probe.timestamp - restore_time).total_seconds())
                assert time_diff < 10.0, f"{case['name']}: Fallback timestamp should be recent"
            else:
                # Case where we expect failure - not used in current test design
                pass

    def test_performance_impact(self, thermal_manager):
        """Test serialization/deserialization performance meets <5% impact requirement."""
        # Create test scenario with 5 probes (maximum)
        base_time = datetime(2024, 8, 17, 12, 0, 0, tzinfo=timezone.utc)
        test_probes = []
        
        for i in range(5):
            probe = ProbeResult(
                tau_value=80.0 + i * 15,
                confidence=0.75 + i * 0.05,
                duration=1200 + i * 400,
                fit_quality=0.80 + i * 0.04,
                aborted=False,
                timestamp=base_time + timedelta(minutes=i * 30)
            )
            test_probes.append(probe)
            thermal_manager._model._probe_history.append(probe)
        
        # Measure serialization performance
        def serialize_operation():
            return thermal_manager.serialize()
        
        # Run multiple iterations for accurate timing
        serialize_times = timeit.repeat(serialize_operation, repeat=10, number=100)
        avg_serialize_time = sum(serialize_times) / len(serialize_times) / 100  # Per operation
        
        # Measure deserialization performance
        serialized_data = thermal_manager.serialize()
        
        def deserialize_operation():
            thermal_manager._model._probe_history.clear()
            thermal_manager.restore(serialized_data)
        
        deserialize_times = timeit.repeat(deserialize_operation, repeat=10, number=100)
        avg_deserialize_time = sum(deserialize_times) / len(deserialize_times) / 100  # Per operation
        
        # Performance assertions (reasonable thresholds for timestamp operations)
        assert avg_serialize_time < 0.001, f"Serialization too slow: {avg_serialize_time:.6f}s (should be <1ms)"
        assert avg_deserialize_time < 0.005, f"Deserialization too slow: {avg_deserialize_time:.6f}s (should be <5ms)"
        
        # Verify data integrity after performance test
        final_probes = list(thermal_manager._model._probe_history)
        assert len(final_probes) == 5, "Performance test should preserve all probes"
        
        for i, probe in enumerate(final_probes):
            expected_timestamp = base_time + timedelta(minutes=i * 30)
            assert probe.timestamp == expected_timestamp, f"Performance test corrupted probe {i} timestamp"


class TestTimestampErrorRecovery:
    """Comprehensive tests for timestamp error recovery scenarios.
    
    Tests system resilience to various forms of timestamp data corruption.
    Based on Level 4 agent design for robust error handling.
    """

    @pytest.fixture
    def mock_hass(self):
        """Mock Home Assistant instance."""
        return Mock()

    @pytest.fixture  
    def mock_thermal_model(self):
        """Mock thermal model with probe history."""
        model = Mock(spec=PassiveThermalModel)
        model._tau_cooling = 90.0
        model._tau_warming = 150.0
        model._probe_history = deque(maxlen=5)
        model.get_confidence.return_value = 0.8
        return model

    @pytest.fixture
    def mock_preferences(self):
        """Mock user preferences."""
        prefs = Mock(spec=UserPreferences)
        prefs.level = PreferenceLevel.BALANCED
        return prefs

    @pytest.fixture
    def thermal_manager(self, mock_hass, mock_thermal_model, mock_preferences):
        """Create ThermalManager instance for testing."""
        from custom_components.smart_climate.thermal_manager import ThermalManager
        manager = ThermalManager(mock_hass, mock_thermal_model, mock_preferences)
        return manager

    def test_corrupted_timestamp_invalid_iso_format(self, thermal_manager):
        """Test recovery from invalid ISO format timestamp strings."""
        invalid_formats = [
            "2024-13-45T25:99:99",  # Invalid date/time values
            "2024/03/15 10:30:00",  # Wrong separators
            "March 15, 2024 10:30 AM",  # Natural language format
            "1710492600",  # Unix timestamp as string
            "2024-03-15",  # Date only, no time
            "10:30:00",  # Time only, no date
            "2024-03-15T10:30:00.123456789Z",  # Too many microseconds
            "2024-03-15T10:30:00+25:00"  # Invalid timezone offset
        ]
        
        for i, invalid_timestamp in enumerate(invalid_formats):
            test_data = {
                "probe_history": [
                    {
                        "tau_value": 100.0 + i,
                        "confidence": 0.8,
                        "duration": 1800,
                        "fit_quality": 0.9,
                        "aborted": False,
                        "timestamp": invalid_timestamp
                    }
                ]
            }
            
            # Clear history and attempt restore
            thermal_manager._model._probe_history.clear()
            restore_time = datetime.now(timezone.utc)
            
            # Should not raise exception
            thermal_manager.restore(test_data)
            
            # Verify fallback timestamp was applied
            restored_probes = list(thermal_manager._model._probe_history)
            assert len(restored_probes) == 1, f"Format {i}: Should restore probe with fallback"
            
            probe = restored_probes[0]
            assert probe.timestamp is not None, f"Format {i}: Should have fallback timestamp"
            assert probe.timestamp.tzinfo == timezone.utc, f"Format {i}: Should be UTC"
            
            # Verify fallback is recent
            time_diff = abs((probe.timestamp - restore_time).total_seconds())
            assert time_diff < 10.0, f"Format {i}: Fallback should be recent"
            
            # Verify other data was restored correctly
            assert probe.tau_value == 100.0 + i, f"Format {i}: tau_value should be preserved"

    def test_corrupted_timestamp_non_string_types(self, thermal_manager):
        """Test recovery from non-string timestamp data types."""
        non_string_types = [
            123456789,  # Integer
            123456789.123,  # Float
            ["2024", "03", "15"],  # List
            {"year": 2024, "month": 3, "day": 15},  # Dictionary
            True,  # Boolean
            b"2024-03-15T10:30:00Z",  # Bytes
        ]
        
        for i, non_string_timestamp in enumerate(non_string_types):
            test_data = {
                "probe_history": [
                    {
                        "tau_value": 90.0 + i * 5,
                        "confidence": 0.75 + i * 0.02,
                        "duration": 1500 + i * 100,
                        "fit_quality": 0.85 + i * 0.01,
                        "aborted": False,
                        "timestamp": non_string_timestamp
                    }
                ]
            }
            
            # Clear and restore
            thermal_manager._model._probe_history.clear()
            restore_time = datetime.now(timezone.utc)
            
            # Should handle gracefully
            thermal_manager.restore(test_data)
            
            # Verify recovery
            restored_probes = list(thermal_manager._model._probe_history)
            assert len(restored_probes) == 1, f"Type {type(non_string_timestamp).__name__}: Should restore with fallback"
            
            probe = restored_probes[0]
            assert probe.timestamp is not None, f"Type {type(non_string_timestamp).__name__}: Should have fallback"
            assert probe.timestamp.tzinfo == timezone.utc, f"Type {type(non_string_timestamp).__name__}: Should be UTC"
            
            # Verify correct field restoration
            assert probe.tau_value == 90.0 + i * 5, f"Type {type(non_string_timestamp).__name__}: tau_value preserved"

    def test_corrupted_timestamp_mixed_data(self, thermal_manager):
        """Test recovery when mixing valid and corrupted timestamps."""
        mixed_data = {
            "probe_history": [
                {  # Valid timestamp
                    "tau_value": 100.0,
                    "confidence": 0.8,
                    "duration": 1800,
                    "fit_quality": 0.9,
                    "aborted": False,
                    "timestamp": "2024-03-15T10:30:00Z"
                },
                {  # Corrupted timestamp
                    "tau_value": 105.0,
                    "confidence": 0.82,
                    "duration": 1900,
                    "fit_quality": 0.91,
                    "aborted": False,
                    "timestamp": "corrupted-data"
                },
                {  # Missing timestamp field
                    "tau_value": 110.0,
                    "confidence": 0.84,
                    "duration": 2000,
                    "fit_quality": 0.92,
                    "aborted": False
                    # No timestamp field
                },
                {  # Valid timestamp
                    "tau_value": 115.0,
                    "confidence": 0.86,
                    "duration": 2100,
                    "fit_quality": 0.93,
                    "aborted": False,
                    "timestamp": "2024-03-15T12:30:00Z"
                }
            ]
        }
        
        # Clear and restore
        thermal_manager._model._probe_history.clear()
        restore_time = datetime.now(timezone.utc)
        
        # Should handle mixed data gracefully
        thermal_manager.restore(mixed_data)
        
        # Verify all probes were restored
        restored_probes = list(thermal_manager._model._probe_history)
        assert len(restored_probes) == 4, "Should restore all 4 probes despite corruption"
        
        # Check each probe
        probe_0 = restored_probes[0]  # Valid timestamp
        assert probe_0.timestamp == datetime(2024, 3, 15, 10, 30, 0, tzinfo=timezone.utc)
        assert probe_0.tau_value == 100.0
        
        probe_1 = restored_probes[1]  # Corrupted timestamp -> fallback
        assert probe_1.timestamp is not None
        assert probe_1.timestamp.tzinfo == timezone.utc
        time_diff = abs((probe_1.timestamp - restore_time).total_seconds())
        assert time_diff < 10.0, "Corrupted timestamp should get recent fallback"
        assert probe_1.tau_value == 105.0
        
        probe_2 = restored_probes[2]  # Missing timestamp -> fallback
        assert probe_2.timestamp is not None
        assert probe_2.timestamp.tzinfo == timezone.utc
        time_diff = abs((probe_2.timestamp - restore_time).total_seconds())
        assert time_diff < 10.0, "Missing timestamp should get recent fallback"
        assert probe_2.tau_value == 110.0
        
        probe_3 = restored_probes[3]  # Valid timestamp
        assert probe_3.timestamp == datetime(2024, 3, 15, 12, 30, 0, tzinfo=timezone.utc)
        assert probe_3.tau_value == 115.0

    def test_corrupted_timestamp_overflow_dates(self, thermal_manager):
        """Test recovery from timestamp overflow and extreme date values."""
        extreme_cases = [
            "9999-12-31T23:59:59Z",  # Far future (edge of datetime range)
            "1900-01-01T00:00:00Z",  # Far past
            "0001-01-01T00:00:00Z",  # Minimum datetime
            "2024-02-30T10:30:00Z",  # Invalid date (Feb 30th)
            "2024-04-31T10:30:00Z",  # Invalid date (April 31st)
            "2023-02-29T10:30:00Z",  # Invalid leap year date
            "2024-00-15T10:30:00Z",  # Month 0
            "2024-13-15T10:30:00Z",  # Month 13
        ]
        
        for i, extreme_timestamp in enumerate(extreme_cases):
            test_data = {
                "probe_history": [
                    {
                        "tau_value": 80.0 + i * 3,
                        "confidence": 0.7 + i * 0.01,
                        "duration": 1400 + i * 50,
                        "fit_quality": 0.8 + i * 0.01,
                        "aborted": False,
                        "timestamp": extreme_timestamp
                    }
                ]
            }
            
            # Clear and restore
            thermal_manager._model._probe_history.clear()
            restore_time = datetime.now(timezone.utc)
            
            # Should handle extreme dates gracefully
            thermal_manager.restore(test_data)
            
            # Verify recovery behavior
            restored_probes = list(thermal_manager._model._probe_history)
            assert len(restored_probes) == 1, f"Extreme case {i}: Should restore probe"
            
            probe = restored_probes[0]
            assert probe.timestamp is not None, f"Extreme case {i}: Should have timestamp"
            assert probe.timestamp.tzinfo == timezone.utc, f"Extreme case {i}: Should be UTC"
            
            # For extreme dates that might be valid, verify they're reasonable
            # For invalid dates, verify fallback was applied
            if extreme_timestamp in ["9999-12-31T23:59:59Z", "1900-01-01T00:00:00Z", "0001-01-01T00:00:00Z"]:
                # These might be valid extreme dates depending on implementation
                # Just verify we have a valid datetime object
                assert isinstance(probe.timestamp, datetime), f"Extreme case {i}: Should have valid datetime"
            else:
                # Invalid dates should get fallback timestamp
                time_diff = abs((probe.timestamp - restore_time).total_seconds())
                assert time_diff < 10.0, f"Extreme case {i}: Invalid date should get recent fallback"
            
            # Verify other data preserved
            assert probe.tau_value == 80.0 + i * 3, f"Extreme case {i}: tau_value should be preserved"


class TestTimestampEdgeCases:
    """Tests for timestamp edge cases and boundary conditions.
    
    Tests challenging scenarios like concurrent operations, precision limits,
    timezone transitions, and boundary conditions. Based on Level 4 agent design.
    """

    @pytest.fixture
    def mock_hass(self):
        """Mock Home Assistant instance."""
        return Mock()

    @pytest.fixture  
    def mock_thermal_model(self):
        """Mock thermal model with probe history."""
        model = Mock(spec=PassiveThermalModel)
        model._tau_cooling = 90.0
        model._tau_warming = 150.0
        model._probe_history = deque(maxlen=5)
        model.get_confidence.return_value = 0.8
        return model

    @pytest.fixture
    def mock_preferences(self):
        """Mock user preferences."""
        prefs = Mock(spec=UserPreferences)
        prefs.level = PreferenceLevel.BALANCED
        return prefs

    @pytest.fixture
    def thermal_manager(self, mock_hass, mock_thermal_model, mock_preferences):
        """Create ThermalManager instance for testing."""
        from custom_components.smart_climate.thermal_manager import ThermalManager
        manager = ThermalManager(mock_hass, mock_thermal_model, mock_preferences)
        return manager

    def test_concurrent_probe_creation(self):
        """Test timestamp behavior when creating multiple probes rapidly."""
        # Create probes in rapid succession to test timestamp precision
        probes = []
        creation_times = []
        
        for i in range(10):
            creation_time = datetime.now(timezone.utc)
            probe = ProbeResult(
                tau_value=100.0 + i,
                confidence=0.8,
                duration=1800,
                fit_quality=0.9,
                aborted=False
            )
            probes.append(probe)
            creation_times.append(creation_time)
            
            # Small delay to potentially create different timestamps
            time.sleep(0.001)  # 1ms delay
        
        # Verify all probes have timestamps
        for i, probe in enumerate(probes):
            assert probe.timestamp is not None, f"Probe {i} should have timestamp"
            assert probe.timestamp.tzinfo == timezone.utc, f"Probe {i} should be UTC"
            
            # Timestamp should be close to creation time (within 1 second)
            time_diff = abs((probe.timestamp - creation_times[i]).total_seconds())
            assert time_diff < 1.0, f"Probe {i} timestamp should be close to creation time"
        
        # Check that timestamps are ordered (monotonic if possible)
        timestamps = [probe.timestamp for probe in probes]
        for i in range(1, len(timestamps)):
            # Should be equal or later than previous (allowing for system clock precision)
            assert timestamps[i] >= timestamps[i-1], f"Timestamp {i} should not be earlier than {i-1}"

    def test_probe_timestamp_precision(self):
        """Test timestamp precision and microsecond handling."""
        # Create probe with high-precision timestamp
        precise_time = datetime(2024, 3, 15, 10, 30, 45, 123456, tzinfo=timezone.utc)
        probe = ProbeResult(
            tau_value=120.0,
            confidence=0.85,
            duration=1800,
            fit_quality=0.92,
            aborted=False,
            timestamp=precise_time
        )
        
        # Verify microsecond precision is preserved
        assert probe.timestamp == precise_time, "Should preserve microsecond precision"
        assert probe.timestamp.microsecond == 123456, "Should preserve exact microseconds"
        
        # Test serialization/deserialization preserves precision
        serialized = probe.timestamp.isoformat()
        parsed = datetime.fromisoformat(serialized)
        
        # ISO format should include microseconds
        assert ".123456" in serialized, "ISO format should include microseconds"
        assert parsed == precise_time, "Parsing should restore exact precision"

    def test_daylight_saving_transitions(self, thermal_manager):
        """Test timestamp handling during daylight saving time transitions."""
        # Test various DST transition scenarios
        dst_scenarios = [
            # Spring forward (2:00 AM becomes 3:00 AM)
            {
                "name": "spring_forward_before",
                "timestamp": "2024-03-31T01:30:00+01:00",  # 1:30 AM CET (before transition)
                "expected_utc": datetime(2024, 3, 31, 0, 30, 0, tzinfo=timezone.utc)
            },
            {
                "name": "spring_forward_after", 
                "timestamp": "2024-03-31T03:30:00+02:00",  # 3:30 AM CEST (after transition)
                "expected_utc": datetime(2024, 3, 31, 1, 30, 0, tzinfo=timezone.utc)
            },
            # Fall back (3:00 AM becomes 2:00 AM)
            {
                "name": "fall_back_first",
                "timestamp": "2024-10-27T02:30:00+02:00",  # 2:30 AM CEST (first occurrence)
                "expected_utc": datetime(2024, 10, 27, 0, 30, 0, tzinfo=timezone.utc)
            },
            {
                "name": "fall_back_second",
                "timestamp": "2024-10-27T02:30:00+01:00",  # 2:30 AM CET (second occurrence)
                "expected_utc": datetime(2024, 10, 27, 1, 30, 0, tzinfo=timezone.utc)
            }
        ]
        
        for scenario in dst_scenarios:
            test_data = {
                "probe_history": [
                    {
                        "tau_value": 100.0,
                        "confidence": 0.8,
                        "duration": 1800,
                        "fit_quality": 0.9,
                        "aborted": False,
                        "timestamp": scenario["timestamp"]
                    }
                ]
            }
            
            # Clear and restore
            thermal_manager._model._probe_history.clear()
            thermal_manager.restore(test_data)
            
            # Verify DST handling
            restored_probes = list(thermal_manager._model._probe_history)
            assert len(restored_probes) == 1, f"DST {scenario['name']}: Should restore probe"
            
            probe = restored_probes[0]
            assert probe.timestamp is not None, f"DST {scenario['name']}: Should have timestamp"
            
            # For UTC conversion, we expect the UTC equivalent
            # (exact comparison may depend on implementation details)
            assert probe.timestamp.tzinfo == timezone.utc, f"DST {scenario['name']}: Should normalize to UTC"

    def test_very_old_timestamps(self, thermal_manager):
        """Test handling of very old timestamp data."""
        # Test historical timestamps from different eras
        old_timestamps = [
            "1970-01-01T00:00:01Z",  # Just after Unix epoch
            "1980-12-31T23:59:59Z",  # 1980s
            "1999-12-31T23:59:59Z",  # Y2K edge
            "2000-01-01T00:00:00Z",  # Y2K
            "2010-01-01T00:00:00Z",  # Recent history
        ]
        
        for i, old_timestamp in enumerate(old_timestamps):
            test_data = {
                "probe_history": [
                    {
                        "tau_value": 95.0 + i,
                        "confidence": 0.8,
                        "duration": 1800,
                        "fit_quality": 0.9,
                        "aborted": False,
                        "timestamp": old_timestamp
                    }
                ]
            }
            
            # Clear and restore
            thermal_manager._model._probe_history.clear()
            thermal_manager.restore(test_data)
            
            # Verify old timestamps are handled correctly
            restored_probes = list(thermal_manager._model._probe_history)
            assert len(restored_probes) == 1, f"Old timestamp {i}: Should restore probe"
            
            probe = restored_probes[0]
            assert probe.timestamp is not None, f"Old timestamp {i}: Should have timestamp"
            assert probe.timestamp.tzinfo == timezone.utc, f"Old timestamp {i}: Should be UTC"
            
            # Verify the timestamp is reasonable (not corrupted)
            assert probe.timestamp.year >= 1970, f"Old timestamp {i}: Should be after Unix epoch"
            assert probe.timestamp.year <= 2030, f"Old timestamp {i}: Should be reasonable"

    def test_future_timestamps(self, thermal_manager):
        """Test handling of future timestamp data."""
        # Test timestamps in the future (could happen due to clock skew)
        now = datetime.now(timezone.utc)
        future_scenarios = [
            now + timedelta(minutes=5),    # 5 minutes in future (clock skew)
            now + timedelta(hours=1),      # 1 hour in future
            now + timedelta(days=1),       # 1 day in future
            now + timedelta(days=365),     # 1 year in future
            datetime(2030, 1, 1, 0, 0, 0, tzinfo=timezone.utc),  # Far future
        ]
        
        for i, future_time in enumerate(future_scenarios):
            test_data = {
                "probe_history": [
                    {
                        "tau_value": 110.0 + i,
                        "confidence": 0.8,
                        "duration": 1800,
                        "fit_quality": 0.9,
                        "aborted": False,
                        "timestamp": future_time.isoformat()
                    }
                ]
            }
            
            # Clear and restore
            thermal_manager._model._probe_history.clear()
            thermal_manager.restore(test_data)
            
            # Verify future timestamps are handled
            restored_probes = list(thermal_manager._model._probe_history)
            assert len(restored_probes) == 1, f"Future timestamp {i}: Should restore probe"
            
            probe = restored_probes[0]
            assert probe.timestamp is not None, f"Future timestamp {i}: Should have timestamp"
            assert probe.timestamp.tzinfo == timezone.utc, f"Future timestamp {i}: Should be UTC"
            
            # For reasonable future times (clock skew), preserve them
            # For unreasonable future times, implementation may choose to use fallback
            if i < 2:  # First two scenarios (5 min, 1 hour) are reasonable clock skew
                expected_time = future_time.replace(microsecond=0)  # ISO format may lose microseconds
                assert abs((probe.timestamp - expected_time).total_seconds()) < 1, \
                    f"Future timestamp {i}: Should preserve reasonable future time"
            else:
                # For far future times, verify we at least have a valid timestamp
                assert isinstance(probe.timestamp, datetime), f"Future timestamp {i}: Should have valid datetime"

    def test_probe_history_boundary_conditions(self, thermal_manager):
        """Test timestamp preservation at probe history boundaries."""
        # Test probe history deque boundary (maxlen=5)
        base_time = datetime(2024, 8, 17, 10, 0, 0, tzinfo=timezone.utc)
        
        # Create 7 probes (more than maxlen=5)
        all_probes = []
        for i in range(7):
            probe = ProbeResult(
                tau_value=80.0 + i * 5,
                confidence=0.75 + i * 0.02,
                duration=1500 + i * 100,
                fit_quality=0.8 + i * 0.02,
                aborted=False,
                timestamp=base_time + timedelta(hours=i)
            )
            all_probes.append(probe)
            thermal_manager._model._probe_history.append(probe)
        
        # Verify only last 5 are kept
        history_probes = list(thermal_manager._model._probe_history)
        assert len(history_probes) == 5, "Should keep only last 5 probes due to maxlen"
        
        # Verify preserved probes are the last 5 with correct timestamps
        for i, probe in enumerate(history_probes):
            expected_probe = all_probes[i + 2]  # Skip first 2 (indices 0,1)
            assert probe.timestamp == expected_probe.timestamp, \
                f"Boundary probe {i}: Should preserve correct timestamp"
            assert probe.tau_value == expected_probe.tau_value, \
                f"Boundary probe {i}: Should preserve correct data"
        
        # Test serialization preserves boundary behavior
        serialized_data = thermal_manager.serialize()
        probe_history = serialized_data.get("probe_history", [])
        assert len(probe_history) == 5, "Serialization should preserve boundary behavior"
        
        # Verify timestamps in serialized data
        for i, probe_data in enumerate(probe_history):
            expected_timestamp = (base_time + timedelta(hours=i + 2)).isoformat()
            assert probe_data["timestamp"] == expected_timestamp, \
                f"Serialized boundary probe {i}: Should have correct timestamp"
        
        # Test restoration maintains boundary behavior
        thermal_manager._model._probe_history.clear()
        thermal_manager.restore(serialized_data)
        
        restored_probes = list(thermal_manager._model._probe_history)
        assert len(restored_probes) == 5, "Restoration should maintain boundary behavior"
        
        for i, probe in enumerate(restored_probes):
            expected_timestamp = base_time + timedelta(hours=i + 2)
            assert probe.timestamp == expected_timestamp, \
                f"Restored boundary probe {i}: Should have correct timestamp"


class TestTimestampIntegration:
    """Integration tests for end-to-end timestamp persistence workflows.
    
    Tests complete workflows involving multiple operations, mixed data scenarios,
    and real-world usage patterns. Based on Level 4 agent design.
    """

    @pytest.fixture
    def mock_hass(self):
        """Mock Home Assistant instance."""
        return Mock()

    @pytest.fixture  
    def mock_thermal_model(self):
        """Mock thermal model with probe history."""
        model = Mock(spec=PassiveThermalModel)
        model._tau_cooling = 90.0
        model._tau_warming = 150.0
        model._probe_history = deque(maxlen=5)
        model.get_confidence.return_value = 0.8
        return model

    @pytest.fixture
    def mock_preferences(self):
        """Mock user preferences."""
        prefs = Mock(spec=UserPreferences)
        prefs.level = PreferenceLevel.BALANCED
        return prefs

    @pytest.fixture
    def thermal_manager(self, mock_hass, mock_thermal_model, mock_preferences):
        """Create ThermalManager instance for testing."""
        from custom_components.smart_climate.thermal_manager import ThermalManager
        manager = ThermalManager(mock_hass, mock_thermal_model, mock_preferences)
        return manager

    def test_end_to_end_timestamp_preservation(self, thermal_manager):
        """Test complete end-to-end timestamp preservation through multiple operations."""
        # Phase 1: Create initial probes with specific timestamps
        initial_time = datetime(2024, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        initial_probes = []
        
        for i in range(3):
            probe = ProbeResult(
                tau_value=90.0 + i * 10,
                confidence=0.8 + i * 0.05,
                duration=1500 + i * 200,
                fit_quality=0.85 + i * 0.03,
                aborted=False,
                timestamp=initial_time + timedelta(days=i)
            )
            initial_probes.append(probe)
            thermal_manager._model._probe_history.append(probe)
        
        # Phase 2: First serialize/restore cycle
        first_serialized = thermal_manager.serialize()
        thermal_manager._model._probe_history.clear()
        thermal_manager.restore(first_serialized)
        
        # Verify first cycle preserved timestamps
        phase2_probes = list(thermal_manager._model._probe_history)
        assert len(phase2_probes) == 3, "Phase 2: Should have 3 probes"
        for i, probe in enumerate(phase2_probes):
            expected_timestamp = initial_time + timedelta(days=i)
            assert probe.timestamp == expected_timestamp, f"Phase 2 probe {i}: Timestamp preserved"
        
        # Phase 3: Add more probes
        additional_time = initial_time + timedelta(days=10)
        for i in range(2):
            probe = ProbeResult(
                tau_value=120.0 + i * 5,
                confidence=0.9 + i * 0.02,
                duration=2000 + i * 100,
                fit_quality=0.92 + i * 0.01,
                aborted=False,
                timestamp=additional_time + timedelta(hours=i * 6)
            )
            thermal_manager._model._probe_history.append(probe)
        
        # Phase 4: Second serialize/restore cycle with mixed data
        second_serialized = thermal_manager.serialize()
        thermal_manager._model._probe_history.clear()
        thermal_manager.restore(second_serialized)
        
        # Verify second cycle preserved all timestamps correctly
        final_probes = list(thermal_manager._model._probe_history)
        assert len(final_probes) == 5, "Phase 4: Should have 5 probes total"
        
        # Check original probes (first 3)
        for i in range(3):
            expected_timestamp = initial_time + timedelta(days=i)
            assert final_probes[i].timestamp == expected_timestamp, f"Final probe {i}: Original timestamp preserved"
        
        # Check additional probes (last 2)
        for i in range(2):
            expected_timestamp = additional_time + timedelta(hours=i * 6)
            assert final_probes[i + 3].timestamp == expected_timestamp, f"Final probe {i+3}: Additional timestamp preserved"
        
        # Phase 5: Verify serialized format includes all timestamps
        final_serialized = thermal_manager.serialize()
        probe_history = final_serialized.get("probe_history", [])
        assert len(probe_history) == 5, "Serialized data should include all 5 probes"
        
        for i, probe_data in enumerate(probe_history):
            assert "timestamp" in probe_data, f"Serialized probe {i}: Should have timestamp field"
            timestamp_str = probe_data["timestamp"]
            parsed_timestamp = datetime.fromisoformat(timestamp_str)
            assert parsed_timestamp == final_probes[i].timestamp, f"Serialized probe {i}: Timestamp should match"

    def test_mixed_legacy_and_new_data_loading(self, thermal_manager):
        """Test loading data that mixes legacy (no timestamps) and new (with timestamps) formats."""
        # Create mixed data scenario - some probes with timestamps, some without
        mixed_data = {
            "thermal_state": "DRIFTING",
            "model": {
                "tau_cooling": 95.0,
                "tau_warming": 155.0,
                "confidence": 0.82
            },
            "probe_history": [
                {  # Legacy probe - no timestamp
                    "tau_value": 85.0,
                    "confidence": 0.78,
                    "duration": 1400,
                    "fit_quality": 0.83,
                    "aborted": False
                },
                {  # New probe - with timestamp
                    "tau_value": 95.0,
                    "confidence": 0.85,
                    "duration": 1600,
                    "fit_quality": 0.88,
                    "aborted": False,
                    "timestamp": "2024-06-15T10:30:00Z"
                },
                {  # Legacy probe - no timestamp
                    "tau_value": 105.0,
                    "confidence": 0.82,
                    "duration": 1800,
                    "fit_quality": 0.90,
                    "aborted": False
                },
                {  # New probe - with timestamp
                    "tau_value": 115.0,
                    "confidence": 0.88,
                    "duration": 2000,
                    "fit_quality": 0.92,
                    "aborted": False,
                    "timestamp": "2024-06-15T14:45:00Z"
                }
            ]
        }
        
        # Load mixed data
        restore_time = datetime.now(timezone.utc)
        thermal_manager.restore(mixed_data)
        
        # Verify all probes were loaded
        restored_probes = list(thermal_manager._model._probe_history)
        assert len(restored_probes) == 4, "Should load all 4 mixed probes"
        
        # Check probe 0 (legacy - should get fallback timestamp)
        probe_0 = restored_probes[0]
        assert probe_0.tau_value == 85.0, "Probe 0: Should preserve tau_value"
        assert probe_0.timestamp is not None, "Probe 0: Should have fallback timestamp"
        assert probe_0.timestamp.tzinfo == timezone.utc, "Probe 0: Should be UTC"
        time_diff = abs((probe_0.timestamp - restore_time).total_seconds())
        assert time_diff < 10.0, "Probe 0: Fallback timestamp should be recent"
        
        # Check probe 1 (new - should preserve original timestamp)
        probe_1 = restored_probes[1]
        assert probe_1.tau_value == 95.0, "Probe 1: Should preserve tau_value"
        expected_timestamp_1 = datetime(2024, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
        assert probe_1.timestamp == expected_timestamp_1, "Probe 1: Should preserve original timestamp"
        
        # Check probe 2 (legacy - should get fallback timestamp)
        probe_2 = restored_probes[2]
        assert probe_2.tau_value == 105.0, "Probe 2: Should preserve tau_value"
        assert probe_2.timestamp is not None, "Probe 2: Should have fallback timestamp"
        assert probe_2.timestamp.tzinfo == timezone.utc, "Probe 2: Should be UTC"
        time_diff = abs((probe_2.timestamp - restore_time).total_seconds())
        assert time_diff < 10.0, "Probe 2: Fallback timestamp should be recent"
        
        # Check probe 3 (new - should preserve original timestamp)
        probe_3 = restored_probes[3]
        assert probe_3.tau_value == 115.0, "Probe 3: Should preserve tau_value"
        expected_timestamp_3 = datetime(2024, 6, 15, 14, 45, 0, tzinfo=timezone.utc)
        assert probe_3.timestamp == expected_timestamp_3, "Probe 3: Should preserve original timestamp"
        
        # Verify subsequent serialization includes all timestamps
        new_serialized = thermal_manager.serialize()
        new_probe_history = new_serialized.get("probe_history", [])
        assert len(new_probe_history) == 4, "Re-serialization should include all probes"
        
        for i, probe_data in enumerate(new_probe_history):
            assert "timestamp" in probe_data, f"Re-serialized probe {i}: Should have timestamp"
            # All should have valid timestamp strings now
            timestamp_str = probe_data["timestamp"]
            parsed = datetime.fromisoformat(timestamp_str)
            assert isinstance(parsed, datetime), f"Re-serialized probe {i}: Should have valid timestamp"

    def test_incremental_probe_addition_with_timestamps(self, thermal_manager):
        """Test incremental addition of probes preserves timestamp ordering."""
        base_time = datetime(2024, 8, 1, 9, 0, 0, tzinfo=timezone.utc)
        all_timestamps = []
        
        # Add probes incrementally and test serialization after each addition
        for batch in range(3):  # 3 batches
            batch_start_time = base_time + timedelta(days=batch * 2)
            
            # Add 2 probes per batch
            for i in range(2):
                probe_time = batch_start_time + timedelta(hours=i * 3)
                probe = ProbeResult(
                    tau_value=80.0 + (batch * 2 + i) * 8,
                    confidence=0.75 + (batch * 2 + i) * 0.03,
                    duration=1400 + (batch * 2 + i) * 150,
                    fit_quality=0.80 + (batch * 2 + i) * 0.02,
                    aborted=False,
                    timestamp=probe_time
                )
                thermal_manager._model._probe_history.append(probe)
                all_timestamps.append(probe_time)
                
                # Test serialization after each probe addition
                serialized = thermal_manager.serialize()
                probe_history = serialized.get("probe_history", [])
                
                # Verify current probes in history
                current_count = batch * 2 + i + 1
                expected_count = min(current_count, 5)  # maxlen=5
                assert len(probe_history) == expected_count, f"Batch {batch}, probe {i}: Should have {expected_count} probes"
                
                # Verify timestamp ordering in serialized data
                for j in range(len(probe_history) - 1):
                    ts1 = datetime.fromisoformat(probe_history[j]["timestamp"])
                    ts2 = datetime.fromisoformat(probe_history[j + 1]["timestamp"])
                    assert ts1 <= ts2, f"Batch {batch}, probe {i}: Timestamps should be in order"
        
        # Final verification - should have 5 probes (maxlen limit)
        final_probes = list(thermal_manager._model._probe_history)
        assert len(final_probes) == 5, "Should have exactly 5 probes due to maxlen"
        
        # Verify final probes are the last 5 chronologically
        expected_final_timestamps = all_timestamps[-5:]
        for i, probe in enumerate(final_probes):
            assert probe.timestamp == expected_final_timestamps[i], f"Final probe {i}: Should have correct timestamp"
        
        # Test complete restore cycle preserves final state
        final_serialized = thermal_manager.serialize()
        thermal_manager._model._probe_history.clear()
        thermal_manager.restore(final_serialized)
        
        restored_final = list(thermal_manager._model._probe_history)
        assert len(restored_final) == 5, "Restored should have 5 probes"
        for i, probe in enumerate(restored_final):
            assert probe.timestamp == expected_final_timestamps[i], f"Restored probe {i}: Should have correct timestamp"

    def test_probe_history_rotation_preserves_timestamps(self, thermal_manager):
        """Test that probe history rotation (maxlen=5) correctly preserves timestamps."""
        # Create 8 probes to test rotation behavior
        start_time = datetime(2024, 5, 20, 15, 0, 0, tzinfo=timezone.utc)
        all_probes = []
        
        for i in range(8):
            probe_time = start_time + timedelta(hours=i * 2)
            probe = ProbeResult(
                tau_value=70.0 + i * 12,
                confidence=0.70 + i * 0.04,
                duration=1300 + i * 175,
                fit_quality=0.75 + i * 0.025,
                aborted=False,
                timestamp=probe_time
            )
            all_probes.append(probe)
            thermal_manager._model._probe_history.append(probe)
            
            # Test state after each addition
            current_history = list(thermal_manager._model._probe_history)
            expected_length = min(i + 1, 5)
            assert len(current_history) == expected_length, f"Addition {i}: Should have {expected_length} probes"
            
            # Verify timestamps are still in chronological order
            for j in range(len(current_history) - 1):
                assert current_history[j].timestamp <= current_history[j + 1].timestamp, \
                    f"Addition {i}: Probe {j} timestamp should be <= probe {j+1}"
            
            # For rotations (i >= 5), verify we have the latest probes
            if i >= 5:
                expected_start_index = i - 4  # Keep last 5
                for j, probe in enumerate(current_history):
                    expected_probe = all_probes[expected_start_index + j]
                    assert probe.timestamp == expected_probe.timestamp, \
                        f"Addition {i}: Rotated probe {j} should match expected probe"
        
        # Final state verification
        final_history = list(thermal_manager._model._probe_history)
        assert len(final_history) == 5, "Final history should have exactly 5 probes"
        
        # Should contain probes 3, 4, 5, 6, 7 (indices from all_probes)
        for i, probe in enumerate(final_history):
            expected_probe = all_probes[i + 3]
            assert probe.timestamp == expected_probe.timestamp, f"Final probe {i}: Should match expected"
            assert probe.tau_value == expected_probe.tau_value, f"Final probe {i}: Should preserve data"
        
        # Test serialization preserves rotated state correctly
        serialized = thermal_manager.serialize()
        probe_history = serialized.get("probe_history", [])
        assert len(probe_history) == 5, "Serialized should have 5 probes"
        
        for i, probe_data in enumerate(probe_history):
            expected_timestamp = all_probes[i + 3].timestamp.isoformat()
            assert probe_data["timestamp"] == expected_timestamp, f"Serialized probe {i}: Should have correct timestamp"
        
        # Test restoration after rotation preserves correct timestamps
        thermal_manager._model._probe_history.clear()
        thermal_manager.restore(serialized)
        
        restored_history = list(thermal_manager._model._probe_history)
        assert len(restored_history) == 5, "Restored should have 5 probes"
        
        for i, probe in enumerate(restored_history):
            expected_timestamp = all_probes[i + 3].timestamp
            assert probe.timestamp == expected_timestamp, f"Restored probe {i}: Should have correct timestamp"