"""
Test suite for ThermalManager persistence with ProbeScheduler support.

Tests for Step 5.3: Persistence Updates - Update ThermalManager persistence 
to support ProbeScheduler data with schema migration from v2.0 to v2.1.
"""
import pytest
from datetime import datetime, timezone, time, timedelta
from unittest.mock import Mock, patch
from custom_components.smart_climate.thermal_manager import ThermalManager
from custom_components.smart_climate.thermal_model import PassiveThermalModel, ProbeResult
from custom_components.smart_climate.thermal_states import ThermalState
from custom_components.smart_climate.thermal_preferences import UserPreferences, PreferenceLevel
from custom_components.smart_climate.probe_scheduler import ProbeScheduler, LearningProfile, AdvancedSettings


class TestThermalManagerProbeSchedulerPersistence:
    """Test probe scheduler persistence functionality in ThermalManager."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = Mock()
        hass.states = Mock()
        return hass

    @pytest.fixture
    def mock_thermal_model(self):
        """Create a mock thermal model."""
        model = Mock(spec=PassiveThermalModel)
        model.get_confidence.return_value = 0.75
        model._tau_cooling = 90.0
        model._tau_warming = 150.0
        model._probe_history = []
        return model

    @pytest.fixture
    def mock_preferences(self):
        """Create a mock user preferences."""
        preferences = Mock(spec=UserPreferences)
        preferences.level = PreferenceLevel.BALANCED
        return preferences

    @pytest.fixture
    def mock_probe_scheduler(self):
        """Create a mock ProbeScheduler instance."""
        scheduler = Mock(spec=ProbeScheduler)
        scheduler._learning_profile = LearningProfile.BALANCED
        scheduler._profile_config = AdvancedSettings(
            min_probe_interval_hours=12,
            max_probe_interval_days=7,
            quiet_hours_start=time(22, 0),
            quiet_hours_end=time(7, 0),
            information_gain_threshold=0.5,
            temperature_bins=[-10, 0, 10, 20, 30],
            presence_override_enabled=False,
            outdoor_temp_change_threshold=5.0,
            min_probe_duration_minutes=15
        )
        return scheduler

    @pytest.fixture
    def thermal_manager_with_probe_scheduler(self, mock_hass, mock_thermal_model, mock_preferences, mock_probe_scheduler):
        """Create ThermalManager instance with ProbeScheduler."""
        manager = ThermalManager(mock_hass, mock_thermal_model, mock_preferences)
        manager.probe_scheduler = mock_probe_scheduler
        return manager

    def test_serialize_includes_probe_scheduler_config(self, thermal_manager_with_probe_scheduler):
        """Test that serialize() includes probe scheduler configuration in v2.1 format."""
        # Arrange
        manager = thermal_manager_with_probe_scheduler
        
        # Act
        data = manager.serialize()
        
        # Assert
        assert "version" in data
        assert data["version"] == "2.1"  # Updated schema version
        assert "probe_scheduler_config" in data
        
        probe_config = data["probe_scheduler_config"]
        assert probe_config["enabled"] is True
        assert probe_config["learning_profile"] == "balanced"
        assert "advanced_settings" in probe_config
        
        advanced = probe_config["advanced_settings"]
        assert advanced["min_probe_interval_hours"] == 12
        assert advanced["max_probe_interval_days"] == 7
        assert advanced["quiet_hours_start"] == "22:00:00"
        assert advanced["quiet_hours_end"] == "07:00:00"
        assert advanced["information_gain_threshold"] == 0.5
        assert advanced["temperature_bins"] == [-10, 0, 10, 20, 30]
        assert advanced["presence_override_enabled"] is False
        assert advanced["outdoor_temp_change_threshold"] == 5.0
        assert advanced["min_probe_duration_minutes"] == 15

    def test_serialize_without_probe_scheduler(self, mock_hass, mock_thermal_model, mock_preferences):
        """Test serialize() handles missing probe scheduler gracefully."""
        # Arrange
        manager = ThermalManager(mock_hass, mock_thermal_model, mock_preferences)
        # Don't add probe_scheduler attribute
        
        # Act
        data = manager.serialize()
        
        # Assert
        assert "version" in data
        assert data["version"] == "2.1"  # Still updated schema version
        assert "probe_scheduler_config" in data
        
        probe_config = data["probe_scheduler_config"]
        assert probe_config["enabled"] is False

    def test_serialize_with_custom_learning_profile(self, thermal_manager_with_probe_scheduler):
        """Test serialize() with CUSTOM learning profile."""
        # Arrange
        manager = thermal_manager_with_probe_scheduler
        manager.probe_scheduler._learning_profile = LearningProfile.CUSTOM
        
        # Act
        data = manager.serialize()
        
        # Assert
        probe_config = data["probe_scheduler_config"]
        assert probe_config["learning_profile"] == "custom"

    def test_restore_with_probe_scheduler_config_v21(self, mock_hass, mock_thermal_model, mock_preferences):
        """Test restore() with v2.1 data including probe scheduler configuration."""
        # Arrange
        manager = ThermalManager(mock_hass, mock_thermal_model, mock_preferences)
        manager.probe_scheduler = Mock(spec=ProbeScheduler)
        manager.probe_scheduler._update_profile = Mock()
        manager.probe_scheduler.apply_advanced_settings = Mock()
        
        data = {
            "version": "2.1",
            "state": {"current_state": "DRIFTING"},
            "model": {"tau_cooling": 95.0, "tau_warming": 155.0},
            "probe_scheduler_config": {
                "enabled": True,
                "learning_profile": "aggressive",
                "advanced_settings": {
                    "min_probe_interval_hours": 8,
                    "max_probe_interval_days": 5,
                    "quiet_hours_start": "23:00:00",
                    "quiet_hours_end": "06:00:00",
                    "information_gain_threshold": 0.7,
                    "temperature_bins": [-5, 5, 15, 25, 35],
                    "presence_override_enabled": True,
                    "outdoor_temp_change_threshold": 3.0,
                    "min_probe_duration_minutes": 20
                }
            },
            "metadata": {"schema_version": "2.1"}
        }
        
        # Act
        manager.restore(data)
        
        # Assert
        manager.probe_scheduler._update_profile.assert_called_once_with(LearningProfile.AGGRESSIVE)
        manager.probe_scheduler.apply_advanced_settings.assert_called_once()
        
        # Verify advanced settings were applied correctly
        call_args = manager.probe_scheduler.apply_advanced_settings.call_args[0][0]
        assert call_args.min_probe_interval_hours == 8
        assert call_args.max_probe_interval_days == 5
        assert call_args.quiet_hours_start == time(23, 0)
        assert call_args.quiet_hours_end == time(6, 0)
        assert call_args.information_gain_threshold == 0.7
        assert call_args.temperature_bins == [-5, 5, 15, 25, 35]
        assert call_args.presence_override_enabled is True
        assert call_args.outdoor_temp_change_threshold == 3.0
        assert call_args.min_probe_duration_minutes == 20

    def test_restore_with_probe_scheduler_disabled(self, mock_hass, mock_thermal_model, mock_preferences):
        """Test restore() with probe scheduler disabled."""
        # Arrange
        manager = ThermalManager(mock_hass, mock_thermal_model, mock_preferences)
        
        data = {
            "version": "2.1",
            "state": {"current_state": "DRIFTING"},
            "probe_scheduler_config": {
                "enabled": False
            },
            "metadata": {"schema_version": "2.1"}
        }
        
        # Act
        manager.restore(data)
        
        # Assert - should complete without error
        # No probe scheduler methods should be called

    def test_restore_backward_compatibility_v20(self, mock_hass, mock_thermal_model, mock_preferences):
        """Test restore() handles v2.0 data without probe scheduler (backward compatibility)."""
        # Arrange
        manager = ThermalManager(mock_hass, mock_thermal_model, mock_preferences)
        manager.probe_scheduler = Mock(spec=ProbeScheduler)
        
        # v2.0 data without probe_scheduler_config
        data = {
            "version": "2.0",
            "state": {"current_state": "DRIFTING"},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0},
            "metadata": {"schema_version": "2.0"}
        }
        
        # Act
        manager.restore(data)
        
        # Assert - should complete without error, no probe scheduler config applied
        # This tests graceful handling of missing probe scheduler config

    def test_restore_backward_compatibility_v10(self, mock_hass, mock_thermal_model, mock_preferences):
        """Test restore() handles v1.0 data without probe scheduler (backward compatibility)."""
        # Arrange
        manager = ThermalManager(mock_hass, mock_thermal_model, mock_preferences)
        
        # v1.0 data (current format) without probe_scheduler_config
        data = {
            "version": "1.0",
            "state": {"current_state": "PRIMING"},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0},
            "metadata": {"schema_version": "1.0"}
        }
        
        # Act
        manager.restore(data)
        
        # Assert - should complete without error
        assert manager.current_state == ThermalState.PRIMING

    def test_restore_with_invalid_learning_profile(self, mock_hass, mock_thermal_model, mock_preferences):
        """Test restore() handles invalid learning profile gracefully."""
        # Arrange
        manager = ThermalManager(mock_hass, mock_thermal_model, mock_preferences)
        manager.probe_scheduler = Mock(spec=ProbeScheduler)
        
        data = {
            "version": "2.1",
            "state": {"current_state": "DRIFTING"},
            "probe_scheduler_config": {
                "enabled": True,
                "learning_profile": "invalid_profile",  # Invalid value
                "advanced_settings": {}
            }
        }
        
        # Act & Assert - should not raise exception
        manager.restore(data)
        # Should use default profile or handle gracefully

    def test_restore_with_malformed_advanced_settings(self, mock_hass, mock_thermal_model, mock_preferences):
        """Test restore() handles malformed advanced settings gracefully."""
        # Arrange
        manager = ThermalManager(mock_hass, mock_thermal_model, mock_preferences)
        manager.probe_scheduler = Mock(spec=ProbeScheduler)
        
        data = {
            "version": "2.1",
            "state": {"current_state": "DRIFTING"},
            "probe_scheduler_config": {
                "enabled": True,
                "learning_profile": "balanced",
                "advanced_settings": {
                    "min_probe_interval_hours": "invalid",  # Should be int
                    "quiet_hours_start": "invalid_time",   # Should be valid time
                    "temperature_bins": "not_a_list"       # Should be list
                }
            }
        }
        
        # Act & Assert - should not raise exception
        manager.restore(data)
        # Should use defaults for invalid settings

    def test_roundtrip_serialization_accuracy(self, thermal_manager_with_probe_scheduler):
        """Test that serialize/restore roundtrip maintains data accuracy."""
        # Arrange
        manager = thermal_manager_with_probe_scheduler
        
        # Set specific state
        manager._current_state = ThermalState.CORRECTING
        
        # Act - serialize then restore
        data = manager.serialize()
        
        # Create new manager for restoration
        new_manager = ThermalManager(manager._hass, manager._model, manager._preferences)
        new_manager.probe_scheduler = Mock(spec=ProbeScheduler)
        new_manager.probe_scheduler._update_profile = Mock()
        new_manager.probe_scheduler.apply_advanced_settings = Mock()
        
        new_manager.restore(data)
        
        # Assert
        assert new_manager.current_state == ThermalState.CORRECTING
        new_manager.probe_scheduler._update_profile.assert_called_once_with(LearningProfile.BALANCED)

    def test_schema_migration_metadata_updated(self, thermal_manager_with_probe_scheduler):
        """Test that schema version is properly updated in metadata."""
        # Arrange
        manager = thermal_manager_with_probe_scheduler
        
        # Act
        data = manager.serialize()
        
        # Assert
        assert data["version"] == "2.1"
        assert data["metadata"]["schema_version"] == "2.1"

    def test_serialize_probe_scheduler_without_advanced_settings(self, mock_hass, mock_thermal_model, mock_preferences):
        """Test serialize() when probe scheduler lacks advanced settings."""
        # Arrange
        manager = ThermalManager(mock_hass, mock_thermal_model, mock_preferences)
        scheduler = Mock(spec=ProbeScheduler)
        scheduler._learning_profile = LearningProfile.COMFORT
        scheduler._profile_config = None  # Missing advanced settings
        manager.probe_scheduler = scheduler
        
        # Act
        data = manager.serialize()
        
        # Assert
        probe_config = data["probe_scheduler_config"]
        assert probe_config["enabled"] is True
        assert probe_config["learning_profile"] == "comfort"
        # Should handle missing advanced settings gracefully

    def test_restore_time_parsing_edge_cases(self, mock_hass, mock_thermal_model, mock_preferences):
        """Test restore() handles edge cases in time parsing."""
        # Arrange
        manager = ThermalManager(mock_hass, mock_thermal_model, mock_preferences)
        manager.probe_scheduler = Mock(spec=ProbeScheduler)
        manager.probe_scheduler._update_profile = Mock()
        manager.probe_scheduler.apply_advanced_settings = Mock()
        
        data = {
            "version": "2.1",
            "state": {"current_state": "DRIFTING"},
            "probe_scheduler_config": {
                "enabled": True,
                "learning_profile": "balanced",
                "advanced_settings": {
                    "quiet_hours_start": "00:00:00",  # Midnight
                    "quiet_hours_end": "23:59:59",   # End of day
                    "min_probe_interval_hours": 24,  # Maximum value
                    "max_probe_interval_days": 1     # Minimum value
                }
            }
        }
        
        # Act
        manager.restore(data)
        
        # Assert
        call_args = manager.probe_scheduler.apply_advanced_settings.call_args[0][0]
        assert call_args.quiet_hours_start == time(0, 0)
        assert call_args.quiet_hours_end == time(23, 59, 59)
        assert call_args.min_probe_interval_hours == 24
        assert call_args.max_probe_interval_days == 1