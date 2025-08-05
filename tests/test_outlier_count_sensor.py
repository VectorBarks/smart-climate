"""Tests for OutlierCountSensor."""

import pytest
from unittest.mock import Mock
from datetime import datetime

from homeassistant.components.sensor import (
    SensorStateClass,
)
from homeassistant.const import EntityCategory

from custom_components.smart_climate.sensor import OutlierCountSensor


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator with outlier test data."""
    coordinator = Mock()
    coordinator.last_update_success = True
    coordinator.data = Mock()
    coordinator.data.outlier_count = 3
    coordinator.data.outlier_statistics = {
        "enabled": True,
        "temperature_outliers": 2,
        "power_outliers": 1,
        "total_samples": 10,
        "outlier_rate": 0.3,
        "last_detection_time": datetime(2025, 8, 5, 20, 0, 0).isoformat(),
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


class TestOutlierCountSensor:
    """Test OutlierCountSensor class."""
    
    def test_outlier_count_sensor_initialization(self, mock_coordinator, mock_config_entry):
        """Test sensor initializes with coordinator."""
        sensor = OutlierCountSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.coordinator == mock_coordinator
        assert sensor.name == "Outlier Count"
        assert sensor.icon == "mdi:alert-circle-check-outline"
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC
        
    def test_sensor_native_value_returns_count(self, mock_coordinator, mock_config_entry):
        """Test native_value returns coordinator.data.outlier_count."""
        sensor = OutlierCountSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value == 3
    
    def test_sensor_attributes_include_details(self, mock_coordinator, mock_config_entry):
        """Test extra_state_attributes include total_sensors, outlier_rate."""
        sensor = OutlierCountSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        attributes = sensor.extra_state_attributes
        assert attributes["total_sensors"] == 10
        assert attributes["outlier_rate"] == 0.3
        assert attributes["last_detection_time"] == datetime(2025, 8, 5, 20, 0, 0).isoformat()
    
    def test_sensor_unique_id_format(self, mock_coordinator, mock_config_entry):
        """Test unique_id follows expected format."""
        sensor = OutlierCountSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        expected_unique_id = "test_unique_id_climate_test_outlier_count"
        assert sensor.unique_id == expected_unique_id
    
    def test_sensor_updates_with_count_changes(self, mock_coordinator, mock_config_entry):
        """Test sensor updates when outlier count changes."""
        sensor = OutlierCountSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        # Initial value
        assert sensor.native_value == 3
        
        # Update coordinator data  
        mock_coordinator.data.outlier_count = 5
        mock_coordinator.data.outlier_statistics["total_samples"] = 15
        mock_coordinator.data.outlier_statistics["outlier_rate"] = 0.33
        
        # Verify updated values
        assert sensor.native_value == 5
        attributes = sensor.extra_state_attributes
        assert attributes["total_sensors"] == 15
        assert attributes["outlier_rate"] == 0.33
    
    def test_sensor_handles_zero_outliers(self, mock_coordinator, mock_config_entry):
        """Test proper handling when no outliers detected."""
        mock_coordinator.data.outlier_count = 0
        mock_coordinator.data.outlier_statistics = {
            "enabled": True,
            "temperature_outliers": 0,
            "power_outliers": 0,
            "total_samples": 5,
            "outlier_rate": 0.0,
            "last_detection_time": None,
        }
        
        sensor = OutlierCountSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value == 0
        attributes = sensor.extra_state_attributes
        assert attributes["total_sensors"] == 5
        assert attributes["outlier_rate"] == 0.0
        assert attributes["last_detection_time"] is None
    
    def test_sensor_state_class_is_measurement(self, mock_coordinator, mock_config_entry):
        """Test state_class is SensorStateClass.MEASUREMENT."""
        sensor = OutlierCountSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.state_class == SensorStateClass.MEASUREMENT


class TestOutlierCountSensorErrorHandling:
    """Test OutlierCountSensor error handling."""
    
    def test_missing_coordinator_data(self, mock_config_entry):
        """Test sensor handles missing coordinator data gracefully."""
        coordinator = Mock()
        coordinator.data = None
        coordinator.async_add_listener = Mock(return_value=lambda: None)
        
        sensor = OutlierCountSensor(coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value == 0
        attributes = sensor.extra_state_attributes
        assert attributes["total_sensors"] == 0
        assert attributes["outlier_rate"] == 0.0
        assert attributes["last_detection_time"] is None
    
    def test_missing_outlier_statistics(self, mock_config_entry):
        """Test sensor handles missing outlier_statistics."""
        coordinator = Mock()
        coordinator.data = Mock()
        coordinator.data.outlier_count = 2
        coordinator.data.outlier_statistics = None
        coordinator.async_add_listener = Mock(return_value=lambda: None)
        
        sensor = OutlierCountSensor(coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value == 2
        attributes = sensor.extra_state_attributes
        assert attributes["total_sensors"] == 0
        assert attributes["outlier_rate"] == 0.0
        assert attributes["last_detection_time"] is None