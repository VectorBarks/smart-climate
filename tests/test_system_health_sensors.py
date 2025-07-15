"""Tests for System Health sensors."""

import pytest
from unittest.mock import Mock, MagicMock
from homeassistant.const import (
    UnitOfInformation,
    UnitOfTime,
    EntityCategory,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)

from custom_components.smart_climate.sensor_system_health import (
    MemoryUsageSensor,
    PersistenceLatencySensor,
    OutlierDetectionSensor,
    SamplesPerDaySensor,
    ConvergenceTrendSensor,
)


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator with test data."""
    coordinator = Mock()
    coordinator.last_update_success = True
    coordinator.data = {
        "system_health": {
            "memory_usage_kb": 2048.5,
            "persistence_latency_ms": 15.3,
            "outlier_detection_active": True,
            "samples_per_day": 144.7,
            "convergence_trend": "improving",
        }
    }
    coordinator.async_add_listener = Mock(return_value=lambda: None)
    return coordinator


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = Mock()
    entry.unique_id = "test_unique_id"
    entry.title = "Test Climate"
    return entry


class TestMemoryUsageSensor:
    """Test MemoryUsageSensor class."""
    
    def test_sensor_properties(self, mock_coordinator, mock_config_entry):
        """Test sensor has correct properties."""
        sensor = MemoryUsageSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.name == "Memory Usage"
        assert sensor.native_unit_of_measurement == UnitOfInformation.KIBIBYTES
        assert sensor.device_class == SensorDeviceClass.DATA_SIZE
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.icon == "mdi:memory"
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC
        
    def test_valid_data(self, mock_coordinator, mock_config_entry):
        """Test sensor returns correct value with valid data."""
        sensor = MemoryUsageSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value == 2048.5
        
    def test_missing_system_health(self, mock_coordinator, mock_config_entry):
        """Test sensor handles missing system_health data."""
        mock_coordinator.data = {}
        sensor = MemoryUsageSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value is None
        
    def test_missing_memory_usage(self, mock_coordinator, mock_config_entry):
        """Test sensor handles missing memory_usage_kb."""
        mock_coordinator.data = {"system_health": {}}
        sensor = MemoryUsageSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value is None
        
    def test_none_data(self, mock_coordinator, mock_config_entry):
        """Test sensor handles None coordinator data."""
        mock_coordinator.data = None
        sensor = MemoryUsageSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value is None


class TestPersistenceLatencySensor:
    """Test PersistenceLatencySensor class."""
    
    def test_sensor_properties(self, mock_coordinator, mock_config_entry):
        """Test sensor has correct properties."""
        sensor = PersistenceLatencySensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.name == "Persistence Latency"
        assert sensor.native_unit_of_measurement == "ms"
        assert sensor.device_class == SensorDeviceClass.DURATION
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.icon == "mdi:database-clock"
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC
        
    def test_valid_data(self, mock_coordinator, mock_config_entry):
        """Test sensor returns correct value with valid data."""
        sensor = PersistenceLatencySensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value == 15.3
        
    def test_missing_data(self, mock_coordinator, mock_config_entry):
        """Test sensor handles missing data gracefully."""
        mock_coordinator.data = {"system_health": {}}
        sensor = PersistenceLatencySensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value is None


class TestOutlierDetectionSensor:
    """Test OutlierDetectionSensor class."""
    
    def test_sensor_properties(self, mock_coordinator, mock_config_entry):
        """Test sensor has correct properties."""
        sensor = OutlierDetectionSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.name == "Outlier Detection"
        assert sensor.icon == "mdi:filter-variant-remove"
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC
        
    def test_valid_data_active(self, mock_coordinator, mock_config_entry):
        """Test sensor returns 'on' when outlier detection is active."""
        sensor = OutlierDetectionSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value == "on"
        
    def test_valid_data_inactive(self, mock_coordinator, mock_config_entry):
        """Test sensor returns 'off' when outlier detection is inactive."""
        mock_coordinator.data["system_health"]["outlier_detection_active"] = False
        sensor = OutlierDetectionSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value == "off"
        
    def test_missing_data(self, mock_coordinator, mock_config_entry):
        """Test sensor handles missing data gracefully."""
        mock_coordinator.data = {"system_health": {}}
        sensor = OutlierDetectionSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value == "off"
        
    def test_none_data(self, mock_coordinator, mock_config_entry):
        """Test sensor handles None coordinator data."""
        mock_coordinator.data = None
        sensor = OutlierDetectionSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value == "off"


class TestSamplesPerDaySensor:
    """Test SamplesPerDaySensor class."""
    
    def test_sensor_properties(self, mock_coordinator, mock_config_entry):
        """Test sensor has correct properties."""
        sensor = SamplesPerDaySensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.name == "Samples per Day"
        assert sensor.native_unit_of_measurement == "samples/d"
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.icon == "mdi:chart-bar"
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC
        
    def test_valid_data(self, mock_coordinator, mock_config_entry):
        """Test sensor returns correct value with valid data."""
        sensor = SamplesPerDaySensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value == 144.7
        
    def test_missing_data(self, mock_coordinator, mock_config_entry):
        """Test sensor handles missing data gracefully."""
        mock_coordinator.data = {"system_health": {}}
        sensor = SamplesPerDaySensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value is None


class TestConvergenceTrendSensor:
    """Test ConvergenceTrendSensor class."""
    
    def test_sensor_properties(self, mock_coordinator, mock_config_entry):
        """Test sensor has correct properties."""
        sensor = ConvergenceTrendSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.name == "Convergence Trend"
        assert sensor.icon == "mdi:chart-gantt"
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC
        
    def test_valid_data_improving(self, mock_coordinator, mock_config_entry):
        """Test sensor returns correct value for improving trend."""
        sensor = ConvergenceTrendSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value == "improving"
        
    def test_valid_data_stable(self, mock_coordinator, mock_config_entry):
        """Test sensor returns correct value for stable trend."""
        mock_coordinator.data["system_health"]["convergence_trend"] = "stable"
        sensor = ConvergenceTrendSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value == "stable"
        
    def test_valid_data_unstable(self, mock_coordinator, mock_config_entry):
        """Test sensor returns correct value for unstable trend."""
        mock_coordinator.data["system_health"]["convergence_trend"] = "unstable"
        sensor = ConvergenceTrendSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value == "unstable"
        
    def test_valid_data_unknown(self, mock_coordinator, mock_config_entry):
        """Test sensor returns correct value for unknown trend."""
        mock_coordinator.data["system_health"]["convergence_trend"] = "unknown"
        sensor = ConvergenceTrendSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value == "unknown"
        
    def test_missing_data(self, mock_coordinator, mock_config_entry):
        """Test sensor handles missing data gracefully."""
        mock_coordinator.data = {"system_health": {}}
        sensor = ConvergenceTrendSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value == "unknown"
        
    def test_none_data(self, mock_coordinator, mock_config_entry):
        """Test sensor handles None coordinator data."""
        mock_coordinator.data = None
        sensor = ConvergenceTrendSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value == "unknown"