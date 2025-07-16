"""System Health sensors for Smart Climate integration.

This module provides 5 diagnostic sensors for monitoring Smart Climate system health
and performance metrics. These sensors are categorized as diagnostic entities and
provide insights into the integration's operational status.

Sensors included:
1. MemoryUsageSensor - Memory consumption in KiB
2. PersistenceLatencySensor - Database write latency in milliseconds
3. SamplesPerDaySensor - Learning sample collection rate
4. ConvergenceTrendSensor - ML model convergence status with caching
5. OutlierDetectionSensor - Outlier detection system status

Race Condition Protection:
ConvergenceTrendSensor implements the same caching mechanism as other sensors
to handle coordinator data unavailability during startup, preventing "unknown"
states in dashboard templates.

Key Features:
- Diagnostic entity categorization for advanced users
- Robust error handling with graceful fallbacks
- Performance metrics for system optimization
- Cached values for critical sensors to prevent "unknown" states
"""

import logging
from typing import Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfInformation,
    EntityCategory,
)
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .entity import SmartClimateSensorEntity

_LOGGER = logging.getLogger(__name__)


class SmartClimateDashboardSensor(SmartClimateSensorEntity):
    """Base class for Smart Climate dashboard sensors."""
    pass


class MemoryUsageSensor(SmartClimateDashboardSensor):
    """Sensor for memory usage in KB."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize memory usage sensor."""
        super().__init__(coordinator, base_entity_id, "memory_usage", config_entry)
        self._attr_name = "Memory Usage"
        self._attr_native_unit_of_measurement = UnitOfInformation.KIBIBYTES
        self._attr_device_class = SensorDeviceClass.DATA_SIZE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:memory"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the memory usage value."""
        if not self.coordinator.data:
            return None
        
        try:
            system_health = self.coordinator.data.get("system_health", {})
            return system_health.get("memory_usage_kb")
        except (AttributeError, TypeError):
            return None


class PersistenceLatencySensor(SmartClimateDashboardSensor):
    """Sensor for persistence latency in milliseconds."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize persistence latency sensor."""
        super().__init__(coordinator, base_entity_id, "persistence_latency", config_entry)
        self._attr_name = "Persistence Latency"
        self._attr_native_unit_of_measurement = "ms"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:database-clock"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the persistence latency value."""
        if not self.coordinator.data:
            return None
        
        try:
            system_health = self.coordinator.data.get("system_health", {})
            return system_health.get("persistence_latency_ms")
        except (AttributeError, TypeError):
            return None


class OutlierDetectionSensor(SmartClimateDashboardSensor):
    """Sensor for outlier detection status (binary sensor showing on/off text)."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize outlier detection sensor."""
        super().__init__(coordinator, base_entity_id, "outlier_detection", config_entry)
        self._attr_name = "Outlier Detection"
        self._attr_icon = "mdi:filter-variant-remove"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> str:
        """Return the outlier detection status as text."""
        if not self.coordinator.data:
            return "off"
        
        try:
            system_health = self.coordinator.data.get("system_health", {})
            is_active = system_health.get("outlier_detection_active", False)
            return "on" if is_active else "off"
        except (AttributeError, TypeError):
            return "off"


class SamplesPerDaySensor(SmartClimateDashboardSensor):
    """Sensor for samples per day."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize samples per day sensor."""
        super().__init__(coordinator, base_entity_id, "samples_per_day", config_entry)
        self._attr_name = "Samples per Day"
        self._attr_native_unit_of_measurement = "samples/d"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1
        self._attr_icon = "mdi:chart-bar"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the samples per day value."""
        if not self.coordinator.data:
            return None
        
        try:
            system_health = self.coordinator.data.get("system_health", {})
            return system_health.get("samples_per_day")
        except (AttributeError, TypeError):
            return None


class ConvergenceTrendSensor(SmartClimateDashboardSensor):
    """Sensor for convergence trend analysis.
    
    This sensor displays the ML model's convergence trend to help users understand
    learning progress and stability. Implements comprehensive caching to handle
    coordinator data unavailability during startup.
    
    Valid States:
    - "improving": Model accuracy is increasing over time
    - "stable": Model accuracy has stabilized at current level
    - "unstable": Model accuracy is fluctuating or decreasing
    - "unknown": Insufficient data or sensor not available
    
    Features:
    - Race condition protection with _last_known_value caching
    - Comprehensive data validation with type checking
    - Graceful fallback to cached values on coordinator errors
    - Input validation against valid trend set
    - Diagnostic entity category for advanced users
    
    Race Condition Fix:
    This sensor was one of the primary sensors affected by the race condition
    issue where it would return "unknown" indefinitely if coordinator data
    wasn't available during initialization. The fix implements:
    1. Caching of last known valid trend value
    2. Comprehensive validation of data structure and types
    3. Validation against valid trend set
    4. Error handling that preserves cached state
    
    Data Path:
    coordinator.data["system_health"]["convergence_trend"] -> string
    """
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize convergence trend sensor.
        
        Args:
            coordinator: DataUpdateCoordinator instance
            base_entity_id: Base entity ID for the climate entity
            config_entry: Home Assistant configuration entry
        """
        super().__init__(coordinator, base_entity_id, "convergence_trend", config_entry)
        self._attr_name = "Convergence Trend"
        self._attr_icon = "mdi:chart-gantt"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._last_known_value = "unknown"
    
    @property
    def native_value(self) -> str:
        """Return the convergence trend value.
        
        This method implements comprehensive validation to ensure only valid
        trend values are returned. It provides multi-layer caching to handle
        coordinator data unavailability during startup and runtime errors.
        
        Returns:
            str: One of ["improving", "stable", "unstable", "unknown"]
            
        Caching Behavior:
        - Stores last known valid trend value in self._last_known_value
        - Returns cached value when coordinator data is unavailable
        - Updates cache only with validated trend values from valid set
        - Handles nested data structure validation gracefully
        
        Validation Layers:
        1. Checks coordinator.data is available and is a dictionary
        2. Validates system_health is a dictionary
        3. Ensures convergence_trend is a non-empty string
        4. Validates trend value is in valid set ["improving", "stable", "unstable", "unknown"]
        5. Falls back to cached value at any validation failure
        
        Race Condition Protection:
        This method was designed to fix the race condition where the sensor would
        return "unknown" indefinitely if coordinator data wasn't available during
        initialization, causing dashboard templates to display persistent "unknown" states.
        """
        # Define valid trend values
        valid_trends = ["improving", "stable", "unstable", "unknown"]
        
        try:
            # Check if coordinator data is available
            if not self.coordinator.data:
                return self._last_known_value
            
            # Check if coordinator data is a dictionary
            if not isinstance(self.coordinator.data, dict):
                return self._last_known_value
            
            # Get system_health data with validation
            system_health = self.coordinator.data.get("system_health")
            if not system_health or not isinstance(system_health, dict):
                return self._last_known_value
            
            # Get convergence_trend value with validation
            trend = system_health.get("convergence_trend")
            if not trend or not isinstance(trend, str) or not trend.strip():
                return self._last_known_value
            
            # Validate trend value is in valid set
            if trend not in valid_trends:
                return self._last_known_value
            
            # Cache the valid value and return it
            self._last_known_value = trend
            return trend
            
        except (AttributeError, TypeError, KeyError):
            # Return cached value on any error
            return self._last_known_value


# Export all sensor classes for easy import
__all__ = [
    "MemoryUsageSensor",
    "PersistenceLatencySensor",
    "OutlierDetectionSensor",
    "SamplesPerDaySensor",
    "ConvergenceTrendSensor",
]