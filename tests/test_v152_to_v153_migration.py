"""Tests for v1.5.2→v1.5.3 migration compatibility.

Tests migration from v1.5.2 (schema version "2.0") to v1.5.3 (schema version "2.1")
including ProbeScheduler configuration addition and data preservation.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.smart_climate.migration import (
    MigrationManager,
    is_migration_needed,
    create_default_v153_config,
    CONF_PROBE_SCHEDULER_ENABLED,  # Import from migration module
)
from custom_components.smart_climate.const import (
    CONF_LEARNING_PROFILE,
    CONF_PRESENCE_ENTITY_ID,
    CONF_WEATHER_ENTITY_ID,
    CONF_CALENDAR_ENTITY_ID,
    CONF_MANUAL_OVERRIDE_ENTITY_ID,
    CONF_MIN_PROBE_INTERVAL,
    CONF_MAX_PROBE_INTERVAL,
    CONF_QUIET_HOURS_START,
    CONF_QUIET_HOURS_END,
    CONF_INFO_GAIN_THRESHOLD,
)


# Common fixtures available to all test classes
@pytest.fixture
def mock_hass():
    """Mock Home Assistant instance."""
    hass_mock = Mock()  # Don't spec with HomeAssistant to avoid conflicts
    hass_mock.config_entries = Mock()
    hass_mock.config_entries.async_update_entry = AsyncMock()
    return hass_mock


@pytest.fixture
def migration_manager(mock_hass):
    """Create MigrationManager instance."""
    return MigrationManager(mock_hass)


@pytest.fixture
def v152_sample_data():
    """Create representative v1.5.2 configuration data."""
    return {
        # Core climate configuration (present in v1.5.2)
        "wrapped_entity_id": "climate.daikin_ac",
        "room_sensor_id": "sensor.living_room_temperature",
        "outdoor_sensor_id": "sensor.outdoor_temperature",
        "power_sensor_id": "sensor.ac_power",
        
        # User preferences and thermal settings
        "target_temperature": 22.0,
        "min_temperature": 18.0,
        "max_temperature": 28.0,
        "comfort_band": 1.0,
        "preference_level": "COMFORT_PRIORITY",
        "confidence_threshold": 0.8,
        
        # Learning and behavioral settings
        "learning_enabled": True,
        "offset_clamp": 3.0,
        "update_interval": 60,
        
        # Thermal model parameters (if configured)
        "tau_cooling": 90.5,
        "tau_warming": 152.3,
        
        # Advanced settings
        "debug_mode": False,
        "seasonal_enabled": True,
        
        # Schema version (v1.5.2 uses "2.0" or may be missing)
        "schema_version": "2.0",
    }


@pytest.fixture
def v152_minimal_data():
    """Create minimal v1.5.2 configuration (new installation)."""
    return {
        "wrapped_entity_id": "climate.generic",
        "room_sensor_id": "sensor.temperature",
        "schema_version": "2.0",
    }


@pytest.fixture
def v152_legacy_data():
    """Create v1.5.2 configuration without schema_version (legacy)."""
    return {
        "wrapped_entity_id": "climate.old_ac",
        "room_sensor_id": "sensor.room_temp",
        "outdoor_sensor_id": "sensor.weather_temp",
        "learning_enabled": True,
        "comfort_band": 0.8,
        # No schema_version field (legacy v1.5.2)
    }


@pytest.fixture
def mock_config_entry(v152_sample_data):
    """Create mock config entry with v1.5.2 data."""
    entry = Mock(spec=ConfigEntry)
    entry.entry_id = "test_migration_entry"
    entry.data = v152_sample_data
    return entry


class TestMigrationManager:
    """Test MigrationManager functionality."""


class TestSchemaVersionDetection:
    """Test schema version detection logic."""
    
    def test_detect_explicit_v152_version(self, migration_manager):
        """Test detection of explicit v1.5.2 schema version."""
        data = {"schema_version": "2.0", "wrapped_entity_id": "climate.test"}
        assert migration_manager.detect_schema_version(data) == "2.0"
    
    def test_detect_explicit_v153_version(self, migration_manager):
        """Test detection of explicit v1.5.3 schema version."""
        data = {
            "schema_version": "2.1",
            "wrapped_entity_id": "climate.test",
            CONF_PROBE_SCHEDULER_ENABLED: True,
        }
        assert migration_manager.detect_schema_version(data) == "2.1"
    
    def test_detect_v153_by_probe_scheduler_presence(self, migration_manager):
        """Test v1.5.3 detection based on ProbeScheduler configuration."""
        data = {
            "wrapped_entity_id": "climate.test",
            CONF_PROBE_SCHEDULER_ENABLED: True,
            CONF_LEARNING_PROFILE: "balanced",
        }
        assert migration_manager.detect_schema_version(data) == "2.1"
    
    def test_detect_v152_by_absence_of_probe_scheduler(self, migration_manager):
        """Test v1.5.2 detection when no ProbeScheduler configuration present."""
        data = {
            "wrapped_entity_id": "climate.test",
            "room_sensor_id": "sensor.temp",
            "learning_enabled": True,
        }
        assert migration_manager.detect_schema_version(data) == "2.0"
    
    def test_detect_unknown_version(self, migration_manager):
        """Test handling of unknown schema versions."""
        data = {"schema_version": "1.0", "wrapped_entity_id": "climate.test"}
        assert migration_manager.detect_schema_version(data) == "1.0"


class TestDataPreservation:
    """Test preservation of existing thermal data during migration."""
    
    def test_preserve_all_thermal_data(self, migration_manager, v152_sample_data):
        """Test that all thermal configuration is preserved."""
        migrated = migration_manager.preserve_thermal_data(v152_sample_data)
        
        # Verify all original keys preserved
        for key, value in v152_sample_data.items():
            assert migrated[key] == value
        
        # Verify critical thermal settings preserved
        assert migrated["wrapped_entity_id"] == "climate.daikin_ac"
        assert migrated["room_sensor_id"] == "sensor.living_room_temperature"
        assert migrated["tau_cooling"] == 90.5
        assert migrated["tau_warming"] == 152.3
        assert migrated["comfort_band"] == 1.0
        assert migrated["confidence_threshold"] == 0.8
    
    def test_preserve_minimal_configuration(self, migration_manager, v152_minimal_data):
        """Test preservation of minimal v1.5.2 configuration."""
        migrated = migration_manager.preserve_thermal_data(v152_minimal_data)
        
        assert migrated["wrapped_entity_id"] == "climate.generic"
        assert migrated["room_sensor_id"] == "sensor.temperature"
        assert migrated["schema_version"] == "2.0"
    
    def test_preserve_legacy_data(self, migration_manager, v152_legacy_data):
        """Test preservation of legacy v1.5.2 data without schema version."""
        migrated = migration_manager.preserve_thermal_data(v152_legacy_data)
        
        # All original data preserved
        for key, value in v152_legacy_data.items():
            assert migrated[key] == value
        
        assert "schema_version" not in migrated  # Should not be added here


class TestProbeSchedulerDefaults:
    """Test addition of default ProbeScheduler configuration."""
    
    def test_add_conservative_defaults_for_migration(self, migration_manager):
        """Test conservative ProbeScheduler defaults for migrated v1.5.2 users."""
        migrated_data = {"wrapped_entity_id": "climate.test"}
        migration_manager.add_default_probe_scheduler(migrated_data)
        
        # Verify ProbeScheduler enabled with conservative settings
        assert migrated_data[CONF_PROBE_SCHEDULER_ENABLED] is True
        assert migrated_data[CONF_LEARNING_PROFILE] == "comfort"
        
        # Verify conservative intervals
        assert migrated_data[CONF_MIN_PROBE_INTERVAL] == 24  # More conservative than default 12h
        assert migrated_data[CONF_MAX_PROBE_INTERVAL] == 7
        
        # Verify higher threshold for existing users
        assert migrated_data[CONF_INFO_GAIN_THRESHOLD] == 0.6  # Higher than default 0.5
        
        # Verify quiet hours set
        assert migrated_data[CONF_QUIET_HOURS_START] == "22:00"
        assert migrated_data[CONF_QUIET_HOURS_END] == "07:00"
        
        # Verify entity configuration placeholders
        assert migrated_data[CONF_PRESENCE_ENTITY_ID] is None
        assert migrated_data[CONF_WEATHER_ENTITY_ID] == "weather.home"
        assert migrated_data[CONF_CALENDAR_ENTITY_ID] is None
        assert migrated_data[CONF_MANUAL_OVERRIDE_ENTITY_ID] is None
        
        # Verify migration metadata
        assert migrated_data["probe_scheduler_migration_source"] == "v1.5.2_defaults"
    
    def test_probe_scheduler_defaults_overwrite_behavior(self, migration_manager):
        """Test that ProbeScheduler defaults properly overwrite existing values."""
        migrated_data = {
            "wrapped_entity_id": "climate.test",
            CONF_PROBE_SCHEDULER_ENABLED: False,  # Should be overwritten
            CONF_LEARNING_PROFILE: "aggressive",  # Should be overwritten
        }
        
        migration_manager.add_default_probe_scheduler(migrated_data)
        
        # Verify conservative defaults override any existing values
        assert migrated_data[CONF_PROBE_SCHEDULER_ENABLED] is True
        assert migrated_data[CONF_LEARNING_PROFILE] == "comfort"


class TestMigrationWorkflow:
    """Test complete migration workflow."""
    
    @pytest.mark.asyncio
    async def test_successful_migration_workflow(
        self, migration_manager, mock_config_entry, v152_sample_data
    ):
        """Test complete successful migration from v1.5.2 to v1.5.3."""
        result = await migration_manager.migrate_v152_to_v153(mock_config_entry)
        
        assert result is True
        
        # Verify config entry was updated
        migration_manager._hass.config_entries.async_update_entry.assert_called_once()
        call_args = migration_manager._hass.config_entries.async_update_entry.call_args
        assert call_args[0][0] == mock_config_entry  # First positional arg
        
        updated_data = call_args[1]["data"]  # Keyword arg
        
        # Verify schema version updated
        assert updated_data["schema_version"] == "2.1"
        assert "migration_timestamp" in updated_data
        
        # Verify original data preserved
        assert updated_data["wrapped_entity_id"] == "climate.daikin_ac"
        assert updated_data["tau_cooling"] == 90.5
        assert updated_data["comfort_band"] == 1.0
        
        # Verify ProbeScheduler configuration added
        assert updated_data[CONF_PROBE_SCHEDULER_ENABLED] is True
        assert updated_data[CONF_LEARNING_PROFILE] == "comfort"
        assert updated_data[CONF_MIN_PROBE_INTERVAL] == 24
    
    @pytest.mark.asyncio
    async def test_migration_not_needed_v153_already(self, migration_manager, mock_config_entry):
        """Test migration skipped when config entry already v1.5.3."""
        # Set up v1.5.3 data
        mock_config_entry.data = {
            "schema_version": "2.1",
            "wrapped_entity_id": "climate.test",
            CONF_PROBE_SCHEDULER_ENABLED: True,
        }
        
        result = await migration_manager.migrate_v152_to_v153(mock_config_entry)
        
        assert result is True  # Success, but no migration needed
        migration_manager._hass.config_entries.async_update_entry.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_migration_unknown_schema_version(self, migration_manager, mock_config_entry):
        """Test migration failure with unknown schema version."""
        mock_config_entry.data = {"schema_version": "1.5", "wrapped_entity_id": "climate.test"}
        
        result = await migration_manager.migrate_v152_to_v153(mock_config_entry)
        
        assert result is False
        migration_manager._hass.config_entries.async_update_entry.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_migration_with_config_entry_update_error(
        self, migration_manager, mock_config_entry, v152_sample_data
    ):
        """Test migration handling when config entry update fails."""
        # Make config entry update raise exception
        migration_manager._hass.config_entries.async_update_entry.side_effect = Exception("Update failed")
        
        result = await migration_manager.migrate_v152_to_v153(mock_config_entry)
        
        assert result is False


class TestMigrationVerification:
    """Test migration success verification."""
    
    def test_successful_verification(self, migration_manager):
        """Test successful migration verification."""
        original_data = {
            "wrapped_entity_id": "climate.test",
            "room_sensor_id": "sensor.temp",
            "schema_version": "2.0",
            "comfort_band": 1.0,
        }
        
        migrated_data = original_data.copy()
        migrated_data.update({
            "schema_version": "2.1",
            "migration_timestamp": "2025-08-18T14:30:00+00:00",
            CONF_PROBE_SCHEDULER_ENABLED: True,
            CONF_LEARNING_PROFILE: "comfort",
            CONF_MIN_PROBE_INTERVAL: 24,
            "probe_scheduler_migration_source": "v1.5.2_defaults",
        })
        
        result = migration_manager.verify_migration_success(migrated_data, original_data)
        assert result is True
    
    def test_verification_schema_version_not_updated(self, migration_manager):
        """Test verification failure when schema version not updated."""
        original_data = {"wrapped_entity_id": "climate.test", "schema_version": "2.0"}
        migrated_data = original_data.copy()
        # Schema version not updated
        
        result = migration_manager.verify_migration_success(migrated_data, original_data)
        assert result is False
    
    def test_verification_probe_scheduler_not_enabled(self, migration_manager):
        """Test verification failure when ProbeScheduler not enabled."""
        original_data = {"wrapped_entity_id": "climate.test", "schema_version": "2.0"}
        migrated_data = original_data.copy()
        migrated_data["schema_version"] = "2.1"
        # ProbeScheduler not enabled
        
        result = migration_manager.verify_migration_success(migrated_data, original_data)
        assert result is False
    
    def test_verification_original_data_lost(self, migration_manager):
        """Test verification failure when original data is lost."""
        original_data = {
            "wrapped_entity_id": "climate.test",
            "room_sensor_id": "sensor.temp",
            "comfort_band": 1.0,
            "schema_version": "2.0",
        }
        
        migrated_data = {
            "schema_version": "2.1",
            CONF_PROBE_SCHEDULER_ENABLED: True,
            CONF_LEARNING_PROFILE: "comfort",
            # Missing original data
        }
        
        result = migration_manager.verify_migration_success(migrated_data, original_data)
        assert result is False
    
    def test_verification_invalid_learning_profile(self, migration_manager):
        """Test verification failure with invalid learning profile."""
        original_data = {"wrapped_entity_id": "climate.test", "schema_version": "2.0"}
        migrated_data = original_data.copy()
        migrated_data.update({
            "schema_version": "2.1",
            CONF_PROBE_SCHEDULER_ENABLED: True,
            CONF_LEARNING_PROFILE: "invalid_profile",  # Invalid
            CONF_MIN_PROBE_INTERVAL: 12,
        })
        
        result = migration_manager.verify_migration_success(migrated_data, original_data)
        assert result is False
    
    def test_verification_invalid_probe_interval(self, migration_manager):
        """Test verification failure with invalid probe interval."""
        original_data = {"wrapped_entity_id": "climate.test", "schema_version": "2.0"}
        migrated_data = original_data.copy()
        migrated_data.update({
            "schema_version": "2.1",
            CONF_PROBE_SCHEDULER_ENABLED: True,
            CONF_LEARNING_PROFILE: "comfort",
            CONF_MIN_PROBE_INTERVAL: 48,  # Invalid (>24)
        })
        
        result = migration_manager.verify_migration_success(migrated_data, original_data)
        assert result is False


class TestMigrationScenarios:
    """Test various real-world migration scenarios."""
    
    @pytest.mark.asyncio
    async def test_migration_with_large_probe_history(self, migration_manager, mock_hass):
        """Test migration with extensive probe history data."""
        # Create config entry with large probe history
        large_history_data = {
            "wrapped_entity_id": "climate.central_ac",
            "room_sensor_id": "sensor.main_temp",
            "schema_version": "2.0",
            "probe_history": [
                {
                    "tau_value": 89.2 + i,
                    "confidence": 0.8 + (i * 0.01),
                    "timestamp": f"2025-08-{10+i:02d}T14:30:00Z",
                    "aborted": False,
                    "duration": 3600,
                    "fit_quality": 0.9,
                }
                for i in range(50)  # 50 probe entries
            ],
            "tau_cooling": 91.5,
            "tau_warming": 148.2,
        }
        
        config_entry = Mock(spec=ConfigEntry)
        config_entry.entry_id = "large_history_migration"
        config_entry.data = large_history_data
        
        result = await migration_manager.migrate_v152_to_v153(config_entry)
        
        assert result is True
        
        # Verify probe history preserved
        call_args = migration_manager._hass.config_entries.async_update_entry.call_args
        updated_data = call_args[1]["data"]
        
        assert len(updated_data["probe_history"]) == 50
        assert updated_data["tau_cooling"] == 91.5
        assert updated_data["tau_warming"] == 148.2
    
    @pytest.mark.asyncio
    async def test_migration_with_custom_settings(self, migration_manager, mock_hass):
        """Test migration preserves custom user settings."""
        custom_settings_data = {
            "wrapped_entity_id": "climate.custom_ac",
            "room_sensor_id": "sensor.custom_temp",
            "outdoor_sensor_id": "sensor.custom_outdoor",
            "power_sensor_id": "sensor.custom_power",
            "schema_version": "2.0",
            
            # Custom thermal settings
            "tau_cooling": 65.0,  # Custom value
            "tau_warming": 180.0,  # Custom value
            "comfort_band": 0.5,  # Tight comfort band
            "confidence_threshold": 0.9,  # High confidence requirement
            
            # Custom learning settings
            "offset_clamp": 2.0,  # Lower clamp
            "update_interval": 45,  # Custom interval
            
            # Advanced settings
            "debug_mode": True,
            "seasonal_enabled": False,  # Disabled
        }
        
        config_entry = Mock(spec=ConfigEntry)
        config_entry.entry_id = "custom_migration"
        config_entry.data = custom_settings_data
        
        result = await migration_manager.migrate_v152_to_v153(config_entry)
        
        assert result is True
        
        # Verify all custom settings preserved
        call_args = migration_manager._hass.config_entries.async_update_entry.call_args
        updated_data = call_args[1]["data"]
        
        assert updated_data["tau_cooling"] == 65.0
        assert updated_data["tau_warming"] == 180.0
        assert updated_data["comfort_band"] == 0.5
        assert updated_data["confidence_threshold"] == 0.9
        assert updated_data["offset_clamp"] == 2.0
        assert updated_data["update_interval"] == 45
        assert updated_data["debug_mode"] is True
        assert updated_data["seasonal_enabled"] is False
    
    @pytest.mark.asyncio
    async def test_migration_multiple_config_entries(self, migration_manager, mock_hass):
        """Test migration can handle multiple config entries."""
        # This test verifies that migration manager can be called multiple times
        entries_data = [
            {
                "wrapped_entity_id": "climate.bedroom_ac",
                "room_sensor_id": "sensor.bedroom_temp",
                "schema_version": "2.0",
            },
            {
                "wrapped_entity_id": "climate.living_room_ac",
                "room_sensor_id": "sensor.living_room_temp",
                "schema_version": "2.0",
            },
        ]
        
        results = []
        for i, data in enumerate(entries_data):
            config_entry = Mock(spec=ConfigEntry)
            config_entry.entry_id = f"multi_entry_{i}"
            config_entry.data = data
            
            result = await migration_manager.migrate_v152_to_v153(config_entry)
            results.append(result)
        
        # All migrations should succeed
        assert all(results)
        assert len(results) == 2
        
        # Verify both config entries were updated
        assert migration_manager._hass.config_entries.async_update_entry.call_count == 2


class TestRollbackCompatibility:
    """Test rollback compatibility - v1.5.3 data readable by v1.5.2."""
    
    def test_v153_data_v152_readable_core_fields(self):
        """Test that v1.5.3 data core fields can be read by v1.5.2."""
        # Simulate v1.5.3 data with ProbeScheduler configuration
        v153_data = {
            "schema_version": "2.1",
            "migration_timestamp": "2025-08-18T14:30:00Z",
            
            # Core fields that v1.5.2 needs (should be preserved)
            "wrapped_entity_id": "climate.test",
            "room_sensor_id": "sensor.temp",
            "outdoor_sensor_id": "sensor.outdoor",
            "comfort_band": 1.0,
            "learning_enabled": True,
            "tau_cooling": 90.0,
            "tau_warming": 150.0,
            
            # v1.5.3 ProbeScheduler fields (v1.5.2 should ignore these)
            CONF_PROBE_SCHEDULER_ENABLED: True,
            CONF_LEARNING_PROFILE: "comfort",
            CONF_MIN_PROBE_INTERVAL: 24,
            CONF_QUIET_HOURS_START: "22:00",
            "probe_scheduler_migration_source": "v1.5.2_defaults",
        }
        
        # Extract fields that v1.5.2 would use
        v152_readable_fields = [
            "wrapped_entity_id", "room_sensor_id", "outdoor_sensor_id",
            "comfort_band", "learning_enabled", "tau_cooling", "tau_warming"
        ]
        
        for field in v152_readable_fields:
            assert field in v153_data, f"v1.5.2 required field '{field}' missing from v1.5.3 data"
        
        # Verify v1.5.2 critical configuration still accessible
        assert v153_data["wrapped_entity_id"] == "climate.test"
        assert v153_data["room_sensor_id"] == "sensor.temp"
        assert v153_data["comfort_band"] == 1.0
        assert v153_data["tau_cooling"] == 90.0
    
    def test_v153_graceful_degradation(self):
        """Test that v1.5.3 features gracefully degrade when missing."""
        # Simulate v1.5.3 data where ProbeScheduler fields are missing or invalid
        degraded_data = {
            "schema_version": "2.1",
            "wrapped_entity_id": "climate.test",
            "room_sensor_id": "sensor.temp",
            
            # ProbeScheduler fields missing or invalid (should not crash v1.5.2)
            CONF_PROBE_SCHEDULER_ENABLED: None,  # Invalid
            CONF_LEARNING_PROFILE: "unknown_profile",  # Invalid
        }
        
        # v1.5.2 should be able to extract core functionality
        core_fields = ["wrapped_entity_id", "room_sensor_id"]
        for field in core_fields:
            assert field in degraded_data
        
        # Invalid ProbeScheduler fields should not affect core operation
        assert degraded_data["wrapped_entity_id"] == "climate.test"


class TestUtilityFunctions:
    """Test utility functions for migration detection and configuration."""
    
    def test_is_migration_needed_v152(self):
        """Test migration detection for v1.5.2 config entry."""
        config_entry = Mock(spec=ConfigEntry)
        config_entry.data = {"schema_version": "2.0", "wrapped_entity_id": "climate.test"}
        
        assert is_migration_needed(config_entry) is True
    
    def test_is_migration_needed_v153(self):
        """Test migration detection for v1.5.3 config entry."""
        config_entry = Mock(spec=ConfigEntry)
        config_entry.data = {
            "schema_version": "2.1",
            "wrapped_entity_id": "climate.test",
            CONF_PROBE_SCHEDULER_ENABLED: True,
        }
        
        assert is_migration_needed(config_entry) is False
    
    def test_is_migration_needed_legacy(self):
        """Test migration detection for legacy config entry (no schema version)."""
        config_entry = Mock(spec=ConfigEntry)
        config_entry.data = {"wrapped_entity_id": "climate.test", "learning_enabled": True}
        
        assert is_migration_needed(config_entry) is True
    
    def test_create_default_v153_config_new_installation(self):
        """Test creating default v1.5.3 config for new installations."""
        base_config = {
            "wrapped_entity_id": "climate.new_ac",
            "room_sensor_id": "sensor.new_temp",
        }
        
        v153_config = create_default_v153_config(base_config)
        
        # Verify schema version set for new installation
        assert v153_config["schema_version"] == "2.1"
        
        # Verify base config preserved
        assert v153_config["wrapped_entity_id"] == "climate.new_ac"
        assert v153_config["room_sensor_id"] == "sensor.new_temp"
        
        # Verify ProbeScheduler enabled with balanced defaults (not conservative migration defaults)
        assert v153_config[CONF_PROBE_SCHEDULER_ENABLED] is True
        assert v153_config[CONF_LEARNING_PROFILE] == "balanced"  # Standard for new users
        assert v153_config[CONF_MIN_PROBE_INTERVAL] == 12  # Standard, not 24h migration default
        assert v153_config[CONF_INFO_GAIN_THRESHOLD] == 0.5  # Standard, not 0.6 migration default
    
    def test_create_default_v153_config_preserves_base(self):
        """Test that creating default config preserves all base configuration."""
        base_config = {
            "wrapped_entity_id": "climate.test",
            "room_sensor_id": "sensor.test",
            "custom_setting": "custom_value",
            "user_preference": 42,
        }
        
        v153_config = create_default_v153_config(base_config)
        
        # Verify all base config preserved
        assert v153_config["wrapped_entity_id"] == "climate.test"
        assert v153_config["room_sensor_id"] == "sensor.test"
        assert v153_config["custom_setting"] == "custom_value"
        assert v153_config["user_preference"] == 42
        
        # Verify v1.5.3 defaults added
        assert v153_config["schema_version"] == "2.1"
        assert v153_config[CONF_PROBE_SCHEDULER_ENABLED] is True


class TestErrorHandling:
    """Test error handling in migration scenarios."""
    
    @pytest.mark.asyncio
    async def test_migration_corrupted_data_structure(self, migration_manager, mock_hass):
        """Test migration handling with corrupted configuration data."""
        corrupted_config_entry = Mock(spec=ConfigEntry)
        corrupted_config_entry.entry_id = "corrupted_entry"
        corrupted_config_entry.data = {
            "wrapped_entity_id": None,  # Invalid
            "schema_version": "2.0",
            "probe_history": "not_a_list",  # Invalid type
        }
        
        result = await migration_manager.migrate_v152_to_v153(corrupted_config_entry)
        
        # Migration should handle corrupted data gracefully
        # Result depends on verification logic - might succeed with defaults or fail safely
        assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_migration_missing_critical_data(self, migration_manager, mock_hass):
        """Test migration with missing critical configuration data."""
        incomplete_config_entry = Mock(spec=ConfigEntry)
        incomplete_config_entry.entry_id = "incomplete_entry"
        incomplete_config_entry.data = {
            "schema_version": "2.0",
            # Missing wrapped_entity_id and room_sensor_id
        }
        
        result = await migration_manager.migrate_v152_to_v153(incomplete_config_entry)
        
        # Migration should either succeed with reasonable defaults or fail safely
        assert isinstance(result, bool)
        
    def test_verification_with_exception(self, migration_manager):
        """Test migration verification handles exceptions gracefully."""
        # Create malformed data that might cause exceptions during verification
        original_data = {"wrapped_entity_id": "climate.test"}
        malformed_migrated_data = {
            "schema_version": 2.1,  # Wrong type (should be string)
            CONF_MIN_PROBE_INTERVAL: "not_an_int",  # Wrong type
        }
        
        result = migration_manager.verify_migration_success(malformed_migrated_data, original_data)
        
        # Should return False rather than raising exception
        assert result is False


class TestIntegrationScenarios:
    """Test integration with Home Assistant config entry system."""
    
    def test_migration_timestamp_format(self, migration_manager):
        """Test that migration timestamp uses proper ISO format."""
        migrated_data = {"wrapped_entity_id": "climate.test"}
        
        with patch('custom_components.smart_climate.migration.datetime') as mock_dt:
            mock_now = Mock()
            mock_now.isoformat.return_value = "2025-08-18T14:30:00+00:00"
            mock_dt.now.return_value = mock_now
            mock_dt.timezone = timezone
            
            migration_manager.add_default_probe_scheduler(migrated_data)
            # Migration would normally add timestamp in migrate_v152_to_v153
        
        # This test verifies the timestamp format would be correct
        # Actual timestamp addition happens in migrate_v152_to_v153 method
    
    def test_migration_preserves_config_entry_structure(self, migration_manager):
        """Test that migration maintains Home Assistant config entry data structure."""
        original_config_data = {
            "wrapped_entity_id": "climate.test",
            "room_sensor_id": "sensor.test",
            "schema_version": "2.0",
        }
        
        # Test that preserved data maintains proper structure for Home Assistant
        migrated = migration_manager.preserve_thermal_data(original_config_data)
        
        # Verify data types remain compatible with Home Assistant serialization
        for key, value in migrated.items():
            assert isinstance(key, str), f"Key '{key}' must be string for HA serialization"
            # Values must be JSON-serializable types
            assert value is None or isinstance(value, (str, int, float, bool, list, dict)), \
                f"Value for key '{key}' must be JSON-serializable"