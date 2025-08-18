"""ABOUTME: Configuration and data migration manager for Smart Climate Control.
ABOUTME: Handles v1.5.2→v1.5.3 upgrade migration, preserving thermal data and adding ProbeScheduler defaults."""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone, time
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import (
    # ProbeScheduler configuration keys - use actual constant names from const.py
    CONF_LEARNING_PROFILE,
    CONF_PRESENCE_ENTITY_ID,
    CONF_WEATHER_ENTITY_ID,
    CONF_CALENDAR_ENTITY_ID,
    CONF_MANUAL_OVERRIDE_ENTITY_ID,
    CONF_MIN_PROBE_INTERVAL,  # This is "min_probe_interval_hours"
    CONF_MAX_PROBE_INTERVAL,  # This is "max_probe_interval_days" 
    CONF_QUIET_HOURS_START,
    CONF_QUIET_HOURS_END,
    CONF_INFO_GAIN_THRESHOLD,  # This is "information_gain_threshold"
    # Default values
    DEFAULT_LEARNING_PROFILE,
    DEFAULT_MIN_PROBE_INTERVAL,
    DEFAULT_MAX_PROBE_INTERVAL,
    DEFAULT_QUIET_HOURS_START,
    DEFAULT_QUIET_HOURS_END,
    DEFAULT_INFO_GAIN_THRESHOLD,
)

# ProbeScheduler enabled key - define locally as it's not in const.py yet
CONF_PROBE_SCHEDULER_ENABLED = "probe_scheduler_enabled"

_LOGGER = logging.getLogger(__name__)


class MigrationManager:
    """Manages data migration from v1.5.2 to v1.5.3 with ProbeScheduler support."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize migration manager.
        
        Args:
            hass: Home Assistant instance for accessing entities and configuration
        """
        self._hass = hass
        self._logger = logging.getLogger(__name__)
        
    async def migrate_v152_to_v153(self, config_entry: ConfigEntry) -> bool:
        """Migrate from v1.5.2 to v1.5.3 with ProbeScheduler support.
        
        Migration process:
        1. Detect v1.5.2 data format (schema version "2.0")
        2. Preserve all existing thermal data (probe history, tau values, preferences)
        3. Add default ProbeScheduler configuration with conservative settings
        4. Update schema version to "2.1"
        5. Verify migration success and data integrity
        
        Args:
            config_entry: Home Assistant config entry to migrate
            
        Returns:
            True if migration successful, False if failed or not needed
        """
        try:
            self._logger.info("Starting v1.5.2→v1.5.3 migration for config entry %s", config_entry.entry_id)
            
            # Check if migration is needed
            schema_version = self.detect_schema_version(config_entry.data)
            if schema_version == "2.1":
                self._logger.debug("Config entry already v1.5.3 format (schema 2.1), no migration needed")
                return True
            elif schema_version != "2.0":
                self._logger.warning("Unknown schema version '%s', cannot migrate", schema_version)
                return False
            
            # Get existing configuration data
            old_data = dict(config_entry.data)
            self._logger.debug("Migrating from v1.5.2 data with %d configuration keys", len(old_data))
            
            # Preserve all existing thermal data
            migrated_data = self.preserve_thermal_data(old_data)
            
            # Add default ProbeScheduler configuration
            self.add_default_probe_scheduler(migrated_data)
            
            # Update schema version to v1.5.3
            migrated_data["schema_version"] = "2.1"
            migrated_data["migration_timestamp"] = datetime.now(timezone.utc).isoformat()
            
            # Update the config entry with migrated data
            self._hass.config_entries.async_update_entry(
                config_entry,
                data=migrated_data
            )
            
            # Verify migration success
            success = self.verify_migration_success(migrated_data, old_data)
            if success:
                self._logger.info("Successfully migrated config entry to v1.5.3")
                return True
            else:
                self._logger.error("Migration verification failed")
                return False
                
        except Exception as e:
            self._logger.error("Error during v1.5.2→v1.5.3 migration: %s", e)
            return False
    
    def detect_schema_version(self, data: Dict[str, Any]) -> str:
        """Detect data schema version.
        
        Args:
            data: Configuration data to analyze
            
        Returns:
            Version string: "2.0" (v1.5.2) or "2.1" (v1.5.3) or "unknown"
        """
        # Check for explicit schema version first
        if "schema_version" in data:
            version = data["schema_version"]
            if version in ["2.0", "2.1"]:
                return version
            else:
                # Return the unknown version as-is
                return str(version)
        
        # Detect based on presence of ProbeScheduler configuration
        probe_scheduler_keys = [
            CONF_PROBE_SCHEDULER_ENABLED,
            CONF_LEARNING_PROFILE,
            CONF_PRESENCE_ENTITY_ID,
        ]
        
        if any(key in data for key in probe_scheduler_keys):
            return "2.1"  # v1.5.3 format
        else:
            return "2.0"  # v1.5.2 format (assume legacy)
    
    def preserve_thermal_data(self, old_data: Dict[str, Any]) -> Dict[str, Any]:
        """Preserve existing thermal model data during migration.
        
        Ensures that all critical thermal learning data is maintained:
        - Probe history (timestamps, tau values, confidence scores)
        - Thermal manager state (current state, tau cooling/warming values)
        - User preferences (comfort bands, temperature limits)
        - Configuration settings (sensor IDs, update intervals)
        - Custom advanced settings
        
        Args:
            old_data: Original v1.5.2 configuration data
            
        Returns:
            Migrated data with all thermal information preserved
        """
        migrated_data = old_data.copy()
        
        # Log what we're preserving
        preserved_keys = []
        thermal_keys = [
            # Core climate entity configuration
            "wrapped_entity_id", "room_sensor_id", "outdoor_sensor_id", "power_sensor_id",
            # Temperature control settings
            "target_temperature", "min_temperature", "max_temperature",
            # Learning and behavior settings
            "learning_enabled", "offset_clamp", "update_interval",
            # Comfort band and user preferences
            "comfort_band", "preference_level", "confidence_threshold",
            # Advanced thermal settings
            "tau_cooling", "tau_warming", "thermal_constants",
            # Probe and learning data (if stored in config entry)
            "probe_history", "thermal_state", "last_probe_time",
            # Seasonal learning data
            "seasonal_enabled", "seasonal_data",
            # Performance and debugging
            "debug_mode", "performance_mode",
        ]
        
        for key in thermal_keys:
            if key in old_data:
                preserved_keys.append(key)
                
        self._logger.debug("Preserved %d thermal configuration keys: %s", 
                          len(preserved_keys), ", ".join(preserved_keys))
        
        return migrated_data
    
    def add_default_probe_scheduler(self, migrated_data: Dict[str, Any]) -> None:
        """Add default ProbeScheduler configuration to migrated data.
        
        Conservative defaults for existing v1.5.2 users:
        - Enable ProbeScheduler (but with conservative settings)
        - Comfort learning profile (24h minimum interval vs 12h default)
        - Higher information gain threshold (0.6 vs 0.5 default)
        - Entity configurations left unconfigured (user must set up)
        
        Args:
            migrated_data: Configuration data to add ProbeScheduler defaults to
        """
        self._logger.debug("Adding default ProbeScheduler configuration for v1.5.2 users")
        
        # Core ProbeScheduler settings - conservative for existing users
        migrated_data[CONF_PROBE_SCHEDULER_ENABLED] = True
        migrated_data[CONF_LEARNING_PROFILE] = "comfort"  # Conservative profile
        
        # Entity configurations - None means user must configure
        # This ensures ProbeScheduler doesn't make assumptions about user's setup
        migrated_data[CONF_PRESENCE_ENTITY_ID] = None
        migrated_data[CONF_WEATHER_ENTITY_ID] = "weather.home"  # Common default
        migrated_data[CONF_CALENDAR_ENTITY_ID] = None
        migrated_data[CONF_MANUAL_OVERRIDE_ENTITY_ID] = None
        
        # Advanced settings - conservative for existing users
        migrated_data[CONF_MIN_PROBE_INTERVAL] = 24  # Less disruptive than 12h default
        migrated_data[CONF_MAX_PROBE_INTERVAL] = 7     # Standard maximum
        migrated_data[CONF_QUIET_HOURS_START] = "22:00"     # Conservative quiet hours
        migrated_data[CONF_QUIET_HOURS_END] = "07:00"
        migrated_data[CONF_INFO_GAIN_THRESHOLD] = 0.6  # Higher threshold for existing users
        
        # Add migration metadata
        migrated_data["probe_scheduler_migration_source"] = "v1.5.2_defaults"
        
        self._logger.info(
            "Added ProbeScheduler defaults: profile=comfort, min_interval=24h, "
            "gain_threshold=0.6, requires_user_configuration=presence/calendar/override"
        )
    
    def verify_migration_success(
        self, 
        migrated_data: Dict[str, Any], 
        original_data: Dict[str, Any]
    ) -> bool:
        """Verify that migration completed successfully.
        
        Validation checks:
        - Schema version updated to "2.1"
        - All original thermal configuration preserved
        - ProbeScheduler configuration added
        - No critical data lost
        - Configuration structure valid
        
        Args:
            migrated_data: Post-migration configuration data
            original_data: Pre-migration configuration data
            
        Returns:
            True if migration verification passes, False if issues found
        """
        try:
            # Check schema version updated
            if migrated_data.get("schema_version") != "2.1":
                self._logger.error("Schema version not updated to 2.1")
                return False
            
            # Check ProbeScheduler configuration added
            if not migrated_data.get(CONF_PROBE_SCHEDULER_ENABLED):
                self._logger.error("ProbeScheduler not enabled in migrated data")
                return False
            
            if CONF_LEARNING_PROFILE not in migrated_data:
                self._logger.error("Learning profile not set in migrated data")
                return False
            
            # Verify critical thermal data preserved
            critical_keys = ["wrapped_entity_id", "room_sensor_id"]
            for key in critical_keys:
                if key in original_data and migrated_data.get(key) != original_data.get(key):
                    self._logger.error("Critical key '%s' not preserved correctly", key)
                    return False
            
            # Check that we haven't lost any original keys (except schema updates)
            excluded_keys = {"schema_version", "migration_timestamp", "probe_scheduler_migration_source"}
            for key, value in original_data.items():
                if key not in excluded_keys and migrated_data.get(key) != value:
                    self._logger.error("Original data key '%s' not preserved", key)
                    return False
            
            # Verify ProbeScheduler defaults are reasonable
            profile = migrated_data.get(CONF_LEARNING_PROFILE)
            if profile not in ["comfort", "balanced", "aggressive", "custom"]:
                self._logger.error("Invalid learning profile: %s", profile)
                return False
            
            min_interval = migrated_data.get(CONF_MIN_PROBE_INTERVAL)
            if not isinstance(min_interval, int) or not 6 <= min_interval <= 24:
                self._logger.error("Invalid min probe interval: %s", min_interval)
                return False
            
            self._logger.debug("Migration verification passed all checks")
            return True
            
        except Exception as e:
            self._logger.error("Error during migration verification: %s", e)
            return False


def is_migration_needed(config_entry: ConfigEntry) -> bool:
    """Check if config entry needs v1.5.2→v1.5.3 migration.
    
    Args:
        config_entry: Home Assistant config entry to check
        
    Returns:
        True if migration needed (schema version "2.0"), False otherwise
    """
    manager = MigrationManager(None)  # Don't need hass for version detection
    schema_version = manager.detect_schema_version(config_entry.data)
    return schema_version == "2.0"


def create_default_v153_config(base_config: Dict[str, Any]) -> Dict[str, Any]:
    """Create default v1.5.3 configuration for new installations.
    
    Args:
        base_config: Base configuration with core climate settings
        
    Returns:
        Complete v1.5.3 configuration with ProbeScheduler defaults
    """
    config = base_config.copy()
    
    # Set schema version for new installations
    config["schema_version"] = "2.1"
    
    # Add ProbeScheduler defaults for new users (less conservative than migration)
    config[CONF_PROBE_SCHEDULER_ENABLED] = True
    config[CONF_LEARNING_PROFILE] = DEFAULT_LEARNING_PROFILE  # "balanced" for new users
    config[CONF_PRESENCE_ENTITY_ID] = None
    config[CONF_WEATHER_ENTITY_ID] = "weather.home"
    config[CONF_CALENDAR_ENTITY_ID] = None
    config[CONF_MANUAL_OVERRIDE_ENTITY_ID] = None
    config[CONF_MIN_PROBE_INTERVAL] = DEFAULT_MIN_PROBE_INTERVAL  # 12h standard default
    config[CONF_MAX_PROBE_INTERVAL] = DEFAULT_MAX_PROBE_INTERVAL  # 7 days
    config[CONF_QUIET_HOURS_START] = DEFAULT_QUIET_HOURS_START
    config[CONF_QUIET_HOURS_END] = DEFAULT_QUIET_HOURS_END
    config[CONF_INFO_GAIN_THRESHOLD] = DEFAULT_INFO_GAIN_THRESHOLD  # 0.5 standard
    
    return config