"""Test thermal data migration from v1.5.2 (5 probes) to v1.5.3 (75 probes)."""

import pytest
from datetime import datetime, timezone, timedelta
from collections import deque
from unittest.mock import Mock, patch
import json
import tempfile
import os

from custom_components.smart_climate.thermal_model import (
    ProbeResult, 
    PassiveThermalModel
)
from custom_components.smart_climate.thermal_models import (
    ThermalState,
    ThermalConstants
)
from custom_components.smart_climate.thermal_preferences import (
    UserPreferences,
    PreferenceLevel
)
from custom_components.smart_climate.thermal_manager import ThermalManager
from custom_components.smart_climate.const import MAX_PROBE_HISTORY_SIZE
from custom_components.smart_climate.migrations.thermal_v153 import migrate_probe_data


class TestThermalMigrationV153:
    """Test suite for v1.5.3 thermal data migration."""

    @pytest.fixture
    def mock_hass(self):
        """Mock Home Assistant instance."""
        hass = Mock()
        hass.data = {}
        return hass

    @pytest.fixture
    def thermal_config(self):
        """Standard thermal configuration dictionary."""
        return {
            'tau_cooling': 90.0,
            'tau_warming': 150.0,
            'min_off_time': 600,
            'min_on_time': 300,
            'priming_duration': 86400,
            'recovery_duration': 1800,
            'calibration_idle_minutes': 30,
            'calibration_drift_threshold': 0.3,
            'passive_min_drift_minutes': 15
        }

    @pytest.fixture
    def preferences(self):
        """Standard user preferences."""
        from custom_components.smart_climate.thermal_preferences import UserPreferences
        return UserPreferences(
            level=PreferenceLevel.BALANCED,
            comfort_band=1.5,
            confidence_threshold=0.7,
            probe_drift=2.0
        )

    @pytest.fixture
    def thermal_model_v152(self):
        """Thermal model with v1.5.2 characteristics (5 probes)."""
        model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        # Simulate v1.5.2 with 5 probes (no outdoor_temp)
        return model

    @pytest.fixture
    def legacy_probe_data(self):
        """Sample legacy probe data from v1.5.2 (5 probes, no outdoor_temp)."""
        base_time = datetime(2025, 8, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        return [
            {
                "tau_value": 85.5,
                "confidence": 0.85,
                "duration": 3600,
                "fit_quality": 0.92,
                "aborted": False,
                "timestamp": (base_time - timedelta(days=10)).isoformat()
                # Note: No outdoor_temp field (legacy data)
            },
            {
                "tau_value": 92.3,
                "confidence": 0.78,
                "duration": 2800,
                "fit_quality": 0.88,
                "aborted": False,
                "timestamp": (base_time - timedelta(days=8)).isoformat()
            },
            {
                "tau_value": 88.7,
                "confidence": 0.82,
                "duration": 3200,
                "fit_quality": 0.90,
                "aborted": False,
                "timestamp": (base_time - timedelta(days=5)).isoformat()
            },
            {
                "tau_value": 94.1,
                "confidence": 0.75,
                "duration": 2600,
                "fit_quality": 0.86,
                "aborted": False,
                "timestamp": (base_time - timedelta(days=3)).isoformat()
            },
            {
                "tau_value": 90.8,
                "confidence": 0.89,
                "duration": 3400,
                "fit_quality": 0.94,
                "aborted": False,
                "timestamp": (base_time - timedelta(days=1)).isoformat()
            }
        ]

    @pytest.fixture
    def v153_probe_data(self):
        """Sample v1.5.3 probe data with outdoor_temp."""
        base_time = datetime(2025, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
        
        return [
            {
                "tau_value": 87.2,
                "confidence": 0.91,
                "duration": 3100,
                "fit_quality": 0.93,
                "aborted": False,
                "timestamp": (base_time - timedelta(hours=6)).isoformat(),
                "outdoor_temp": 24.5
            },
            {
                "tau_value": 89.5,
                "confidence": 0.88,
                "duration": 2900,
                "fit_quality": 0.89,
                "aborted": False,
                "timestamp": (base_time - timedelta(hours=2)).isoformat(),
                "outdoor_temp": 26.8
            }
        ]

    def test_legacy_data_loading(self, mock_hass, thermal_config, preferences, legacy_probe_data):
        """Test loading v1.5.2 data (5 probes) into v1.5.3 model."""
        # Arrange
        model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        manager = ThermalManager(mock_hass, model, preferences, thermal_config)
        
        # Create legacy thermal data structure
        legacy_data = {
            "version": "1.0",
            "state": {
                "current_state": "PRIMING",
                "last_transition": datetime.now(timezone.utc).isoformat(),
                "last_probe_time": None
            },
            "model": {
                "tau_cooling": 90.0,
                "tau_warming": 150.0,
                "last_modified": datetime.now(timezone.utc).isoformat()
            },
            "probe_history": legacy_probe_data,
            "confidence": 0.8,
            "metadata": {
                "saves_count": 12,
                "corruption_recoveries": 0,
                "schema_version": "1.0"
            }
        }
        
        # Act
        manager.restore(legacy_data)
        
        # Assert - All legacy probes should be loaded
        assert len(manager._model._probe_history) == 5
        
        # Check that legacy probes get outdoor_temp=None
        for probe in manager._model._probe_history:
            assert probe.outdoor_temp is None
            
        # Verify probe data integrity
        first_probe = manager._model._probe_history[0]
        assert first_probe.tau_value == 85.5
        assert first_probe.confidence == 0.85
        assert first_probe.duration == 3600
        assert first_probe.fit_quality == 0.92
        assert first_probe.aborted is False

    def test_preserve_existing_probe_timestamps(self, mock_hass, thermal_config, preferences, legacy_probe_data):
        """Test that existing probe timestamps are preserved accurately."""
        # Arrange
        model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        manager = ThermalManager(mock_hass, model, preferences, thermal_config)
        
        legacy_data = {
            "version": "1.0",
            "state": {"current_state": "PRIMING", "last_transition": datetime.now(timezone.utc).isoformat()},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0},
            "probe_history": legacy_probe_data,
            "confidence": 0.8,
            "metadata": {"saves_count": 5, "corruption_recoveries": 0}
        }
        
        # Get expected timestamps
        expected_timestamps = [
            datetime.fromisoformat(probe["timestamp"]) for probe in legacy_probe_data
        ]
        
        # Act
        manager.restore(legacy_data)
        
        # Assert - Timestamps should be preserved exactly
        actual_timestamps = [probe.timestamp for probe in manager._model._probe_history]
        assert len(actual_timestamps) == len(expected_timestamps)
        
        for actual, expected in zip(actual_timestamps, expected_timestamps):
            assert actual == expected

    def test_add_outdoor_temp_none_to_legacy_probes(self, mock_hass, thermal_config, preferences):
        """Test that legacy probes get outdoor_temp=None for backward compatibility."""
        # Arrange
        model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        manager = ThermalManager(mock_hass, model, preferences, thermal_config)
        
        # Legacy probe without outdoor_temp field
        legacy_probe_data = [{
            "tau_value": 88.0,
            "confidence": 0.85,
            "duration": 3000,
            "fit_quality": 0.90,
            "aborted": False,
            "timestamp": datetime.now(timezone.utc).isoformat()
            # No outdoor_temp field
        }]
        
        legacy_data = {
            "version": "1.0",
            "state": {"current_state": "PRIMING", "last_transition": datetime.now(timezone.utc).isoformat()},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0},
            "probe_history": legacy_probe_data,
            "confidence": 0.8,
            "metadata": {"saves_count": 1, "corruption_recoveries": 0}
        }
        
        # Act
        manager.restore(legacy_data)
        
        # Assert
        assert len(manager._model._probe_history) == 1
        probe = manager._model._probe_history[0]
        assert probe.outdoor_temp is None

    def test_save_v153_data_with_full_structure(self, mock_hass, thermal_config, preferences, v153_probe_data):
        """Test saving v1.5.3 data with full 75-probe structure."""
        # Arrange
        model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        manager = ThermalManager(mock_hass, model, preferences, thermal_config)
        
        # Add v1.5.3 probes with outdoor_temp
        for probe_data in v153_probe_data:
            probe = ProbeResult(
                tau_value=probe_data["tau_value"],
                confidence=probe_data["confidence"],
                duration=probe_data["duration"],
                fit_quality=probe_data["fit_quality"],
                aborted=probe_data["aborted"],
                timestamp=datetime.fromisoformat(probe_data["timestamp"]),
                outdoor_temp=probe_data["outdoor_temp"]
            )
            manager._model._probe_history.append(probe)
        
        # Act
        serialized_data = manager.serialize()
        
        # Assert - Data should include outdoor_temp
        probe_history = serialized_data["probe_history"]
        assert len(probe_history) == 2
        
        for probe_data in probe_history:
            assert "outdoor_temp" in probe_data or probe_data.get("outdoor_temp") is not None

    def test_round_trip_save_load_data_integrity(self, mock_hass, thermal_config, preferences, legacy_probe_data, v153_probe_data):
        """Test round-trip save/load maintains data integrity."""
        # Arrange
        model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        manager1 = ThermalManager(mock_hass, model, preferences, thermal_config)
        
        # Load legacy data
        legacy_data = {
            "version": "1.0",
            "state": {"current_state": "PRIMING", "last_transition": datetime.now(timezone.utc).isoformat()},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0},
            "probe_history": legacy_probe_data,
            "confidence": 0.8,
            "metadata": {"saves_count": 5, "corruption_recoveries": 0}
        }
        manager1.restore(legacy_data)
        
        # Add some v1.5.3 probes
        for probe_data in v153_probe_data:
            probe = ProbeResult(
                tau_value=probe_data["tau_value"],
                confidence=probe_data["confidence"],
                duration=probe_data["duration"],
                fit_quality=probe_data["fit_quality"],
                aborted=probe_data["aborted"],
                timestamp=datetime.fromisoformat(probe_data["timestamp"]),
                outdoor_temp=probe_data["outdoor_temp"]
            )
            manager1._model._probe_history.append(probe)
        
        # Act - Save and reload
        saved_data = manager1.serialize()
        
        model2 = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        manager2 = ThermalManager(mock_hass, model2, preferences, thermal_config)
        manager2.restore(saved_data)
        
        # Assert - All data should be preserved
        assert len(manager2._model._probe_history) == 7  # 5 legacy + 2 new
        
        # Check legacy probes (outdoor_temp=None)
        legacy_probes = [p for p in manager2._model._probe_history if p.outdoor_temp is None]
        assert len(legacy_probes) == 5
        
        # Check new probes (outdoor_temp not None)
        new_probes = [p for p in manager2._model._probe_history if p.outdoor_temp is not None]
        assert len(new_probes) == 2

    def test_handle_corrupted_data_gracefully(self, mock_hass, thermal_config, preferences):
        """Test handling corrupted data gracefully."""
        # Arrange
        model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        manager = ThermalManager(mock_hass, model, preferences, thermal_config)
        
        # Corrupted probe data
        corrupted_data = {
            "version": "1.0",
            "state": {"current_state": "PRIMING", "last_transition": datetime.now(timezone.utc).isoformat()},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0},
            "probe_history": [
                {
                    "tau_value": 88.0,
                    "confidence": 0.85,
                    "duration": 3000,
                    "fit_quality": 0.90,
                    "aborted": False,
                    "timestamp": "invalid-timestamp"  # Corrupted timestamp
                },
                {
                    "tau_value": "invalid",  # Corrupted tau_value
                    "confidence": 0.82,
                    "duration": 2800,
                    "fit_quality": 0.88,
                    "aborted": False,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            ],
            "confidence": 0.8,
            "metadata": {"saves_count": 2, "corruption_recoveries": 0}
        }
        
        # Act
        manager.restore(corrupted_data)
        
        # Assert - Should handle gracefully
        # First probe should be recovered with current timestamp
        # Second probe should be discarded
        assert manager._corruption_recovery_count > 0

    def test_version_detection_works_correctly(self, mock_hass, thermal_config, preferences):
        """Test version detection works correctly."""
        # Arrange
        model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        manager = ThermalManager(mock_hass, model, preferences, thermal_config)
        
        # v1.5.2 data (no outdoor_temp in probes)
        v152_data = {
            "version": "1.0",
            "state": {"current_state": "PRIMING", "last_transition": datetime.now(timezone.utc).isoformat()},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0},
            "probe_history": [{
                "tau_value": 88.0,
                "confidence": 0.85,
                "duration": 3000,
                "fit_quality": 0.90,
                "aborted": False,
                "timestamp": datetime.now(timezone.utc).isoformat()
                # No outdoor_temp - indicates v1.5.2
            }],
            "confidence": 0.8,
            "metadata": {"saves_count": 1, "corruption_recoveries": 0}
        }
        
        # Act
        manager.restore(v152_data)
        
        # Assert - Should be detected as legacy format
        probe = manager._model._probe_history[0]
        assert probe.outdoor_temp is None

    def test_migration_is_idempotent(self, mock_hass, thermal_config, preferences, legacy_probe_data):
        """Test migration is idempotent (can be run multiple times safely)."""
        # Arrange
        model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        manager = ThermalManager(mock_hass, model, preferences, thermal_config)
        
        legacy_data = {
            "version": "1.0",
            "state": {"current_state": "PRIMING", "last_transition": datetime.now(timezone.utc).isoformat()},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0},
            "probe_history": legacy_probe_data,
            "confidence": 0.8,
            "metadata": {"saves_count": 5, "corruption_recoveries": 0}
        }
        
        # Act - Run migration twice
        manager.restore(legacy_data)
        first_probe_count = len(manager._model._probe_history)
        
        # Save and reload (second migration)
        saved_data = manager.serialize()
        manager.restore(saved_data)
        second_probe_count = len(manager._model._probe_history)
        
        # Assert - Should not duplicate data
        assert first_probe_count == second_probe_count == 5

    def test_migrate_probe_data_function(self):
        """Test the migrate_probe_data utility function."""
        # Arrange
        legacy_probes = [
            {
                "tau_value": 88.0,
                "confidence": 0.85,
                "duration": 3000,
                "fit_quality": 0.90,
                "aborted": False,
                "timestamp": datetime.now(timezone.utc).isoformat()
                # No outdoor_temp
            }
        ]
        
        # Act
        migrated_probes = migrate_probe_data(legacy_probes)
        
        # Assert
        assert len(migrated_probes) == 1
        probe = migrated_probes[0]
        assert isinstance(probe, ProbeResult)
        assert probe.outdoor_temp is None
        assert probe.tau_value == 88.0

    def test_75_probe_history_capacity(self, mock_hass, thermal_config, preferences):
        """Test that system supports full 75-probe history capacity."""
        # Arrange
        model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        manager = ThermalManager(mock_hass, model, preferences, thermal_config)
        
        # Generate 75 probes
        base_time = datetime.now(timezone.utc)
        probe_data = []
        for i in range(75):
            probe_data.append({
                "tau_value": 85.0 + (i % 10),
                "confidence": 0.8 + (i % 20) * 0.01,
                "duration": 3000 + (i % 500),
                "fit_quality": 0.85 + (i % 15) * 0.01,
                "aborted": False,
                "timestamp": (base_time - timedelta(days=i)).isoformat(),
                "outdoor_temp": 20.0 + (i % 15)
            })
        
        thermal_data = {
            "version": "1.0",
            "state": {"current_state": "PRIMING", "last_transition": base_time.isoformat()},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0},
            "probe_history": probe_data,
            "confidence": 0.9,
            "metadata": {"saves_count": 50, "corruption_recoveries": 0}
        }
        
        # Act
        manager.restore(thermal_data)
        
        # Assert
        assert len(manager._model._probe_history) == 75
        assert manager._model._probe_history.maxlen == MAX_PROBE_HISTORY_SIZE

    def test_mixed_legacy_and_new_data_handling(self, mock_hass, thermal_config, preferences):
        """Test handling mixed legacy (no outdoor_temp) and new (with outdoor_temp) data."""
        # Arrange
        model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        manager = ThermalManager(mock_hass, model, preferences, thermal_config)
        
        base_time = datetime.now(timezone.utc)
        mixed_probe_data = [
            # Legacy probe (no outdoor_temp)
            {
                "tau_value": 88.0,
                "confidence": 0.85,
                "duration": 3000,
                "fit_quality": 0.90,
                "aborted": False,
                "timestamp": (base_time - timedelta(days=5)).isoformat()
                # No outdoor_temp field
            },
            # New probe (with outdoor_temp)
            {
                "tau_value": 92.0,
                "confidence": 0.88,
                "duration": 3200,
                "fit_quality": 0.92,
                "aborted": False,
                "timestamp": (base_time - timedelta(days=2)).isoformat(),
                "outdoor_temp": 24.5
            }
        ]
        
        thermal_data = {
            "version": "1.0",
            "state": {"current_state": "PRIMING", "last_transition": base_time.isoformat()},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0},
            "probe_history": mixed_probe_data,
            "confidence": 0.85,
            "metadata": {"saves_count": 2, "corruption_recoveries": 0}
        }
        
        # Act
        manager.restore(thermal_data)
        
        # Assert
        assert len(manager._model._probe_history) == 2
        
        # Check legacy probe
        legacy_probe = manager._model._probe_history[0]
        assert legacy_probe.outdoor_temp is None
        
        # Check new probe
        new_probe = manager._model._probe_history[1]
        assert new_probe.outdoor_temp == 24.5


class TestMigrationUtilities:
    """Test migration utility functions."""

    def test_migrate_probe_data_with_empty_list(self):
        """Test migrate_probe_data with empty probe list."""
        # Act
        result = migrate_probe_data([])
        
        # Assert
        assert result == []

    def test_migrate_probe_data_with_invalid_data(self):
        """Test migrate_probe_data handles invalid data gracefully."""
        # Arrange
        invalid_probes = [
            {"invalid": "data"},
            {
                "tau_value": "not_a_number",
                "confidence": 0.85,
                "duration": 3000,
                "fit_quality": 0.90,
                "aborted": False,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        # Act & Assert - Should handle gracefully without crashing
        try:
            migrate_probe_data(invalid_probes)
        except Exception as e:
            pytest.fail(f"migrate_probe_data should handle invalid data gracefully, but raised: {e}")

    def test_migration_preserves_all_probe_fields(self):
        """Test that migration preserves all probe fields correctly."""
        # Arrange
        timestamp = datetime.now(timezone.utc)
        legacy_probe = {
            "tau_value": 88.5,
            "confidence": 0.85,
            "duration": 3000,
            "fit_quality": 0.90,
            "aborted": True,
            "timestamp": timestamp.isoformat()
            # No outdoor_temp
        }
        
        # Act
        migrated = migrate_probe_data([legacy_probe])
        
        # Assert
        assert len(migrated) == 1
        probe = migrated[0]
        assert probe.tau_value == 88.5
        assert probe.confidence == 0.85
        assert probe.duration == 3000
        assert probe.fit_quality == 0.90
        assert probe.aborted is True
        assert probe.timestamp == timestamp
        assert probe.outdoor_temp is None