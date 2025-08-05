"""Tests for OutlierDetectionSensor binary sensor entity."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry

from custom_components.smart_climate.binary_sensor import OutlierDetectionSensor
from custom_components.smart_climate.const import DOMAIN


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator with outlier detection data."""
    coordinator = Mock()
    coordinator.last_update_success = True
    coordinator.name = "test_climate"
    coordinator.data = Mock()
    coordinator.data.outliers = {
        "climate.test_entity": True,
        "temperature": False,
        "power": True
    }
    coordinator.data.outlier_count = 2
    coordinator.data.outlier_statistics = {
        "enabled": True,
        "temperature_outliers": 0,
        "power_outliers": 1,
        "total_samples": 10,
        "outlier_rate": 0.1,
        "history_size": 50,
        "has_sufficient_data": True
    }
    return coordinator


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    config_entry = Mock(spec=ConfigEntry)
    config_entry.unique_id = "test_unique_id"
    config_entry.title = "Test Climate"
    config_entry.entry_id = "test_entry_id"
    return config_entry


def test_outlier_detection_sensor_initialization(mock_coordinator, mock_config_entry):
    """Test OutlierDetectionSensor initializes with coordinator and entity_id."""
    entity_id = "climate.test_entity"
    
    sensor = OutlierDetectionSensor(mock_coordinator, entity_id)
    
    # Should have coordinator set
    assert sensor.coordinator == mock_coordinator
    # Should store entity_id
    assert sensor._entity_id == entity_id
    # Should have proper BinarySensorEntity characteristics
    assert hasattr(sensor, 'is_on')
    assert hasattr(sensor, '_attr_device_class')


def test_sensor_device_class_is_problem(mock_coordinator, mock_config_entry):
    """Test device class is BinarySensorDeviceClass.PROBLEM."""
    entity_id = "climate.test_entity"
    
    sensor = OutlierDetectionSensor(mock_coordinator, entity_id)
    
    assert sensor._attr_device_class == BinarySensorDeviceClass.PROBLEM


def test_sensor_is_on_reflects_outlier_status(mock_coordinator, mock_config_entry):
    """Test is_on property returns outlier status from coordinator."""
    entity_id = "climate.test_entity"
    
    sensor = OutlierDetectionSensor(mock_coordinator, entity_id)
    
    # Should return True when entity has outliers
    assert sensor.is_on is True
    
    # Test False case
    entity_id_no_outlier = "climate.no_outlier_entity"
    sensor_no_outlier = OutlierDetectionSensor(mock_coordinator, entity_id_no_outlier)
    
    assert sensor_no_outlier.is_on is False


def test_sensor_attributes_include_statistics(mock_coordinator, mock_config_entry):
    """Test extra_state_attributes include outlier statistics."""
    entity_id = "climate.test_entity"
    
    sensor = OutlierDetectionSensor(mock_coordinator, entity_id)
    
    attributes = sensor.extra_state_attributes
    
    assert "outlier_count" in attributes
    assert "outlier_rate" in attributes
    assert "detection_enabled" in attributes
    
    assert attributes["outlier_count"] == 2
    assert attributes["outlier_rate"] == 0.1
    assert attributes["detection_enabled"] is True


def test_sensor_unique_id_format(mock_coordinator, mock_config_entry):
    """Test unique_id follows '{entity_id}_outlier_detection' format."""
    entity_id = "climate.test_entity"
    
    sensor = OutlierDetectionSensor(mock_coordinator, entity_id)
    
    expected_unique_id = f"{entity_id}_outlier_detection"
    assert sensor.unique_id == expected_unique_id


def test_sensor_updates_with_coordinator(mock_coordinator, mock_config_entry):
    """Test sensor updates when coordinator data changes."""
    entity_id = "climate.test_entity"
    
    sensor = OutlierDetectionSensor(mock_coordinator, entity_id)
    
    # Initial state
    assert sensor.is_on is True
    
    # Update coordinator data
    mock_coordinator.data.outliers[entity_id] = False
    mock_coordinator.data.outlier_count = 1
    
    # Sensor should reflect new state
    assert sensor.is_on is False
    assert sensor.extra_state_attributes["outlier_count"] == 1


def test_sensor_handles_missing_entity_data(mock_coordinator, mock_config_entry):
    """Test graceful handling when entity not in outlier data."""
    entity_id = "climate.missing_entity"
    
    sensor = OutlierDetectionSensor(mock_coordinator, entity_id)
    
    # Should return False when entity not in outliers dict
    assert sensor.is_on is False
    
    # Should still return valid attributes
    attributes = sensor.extra_state_attributes
    assert attributes["outlier_count"] == 2
    assert attributes["detection_enabled"] is True


def test_sensor_handles_coordinator_data_unavailable():
    """Test graceful handling when coordinator data is None."""
    coordinator = Mock()
    coordinator.last_update_success = True
    coordinator.data = None
    
    entity_id = "climate.test_entity"
    sensor = OutlierDetectionSensor(coordinator, entity_id)
    
    # Should handle None data gracefully
    assert sensor.is_on is False
    
    # Attributes should have default values
    attributes = sensor.extra_state_attributes
    assert attributes["outlier_count"] == 0
    assert attributes["outlier_rate"] == 0.0
    assert attributes["detection_enabled"] is False


def test_sensor_handles_missing_outlier_statistics():
    """Test graceful handling when outlier_statistics is missing."""
    coordinator = Mock()
    coordinator.last_update_success = True
    coordinator.data = Mock()
    coordinator.data.outliers = {"climate.test": False}
    coordinator.data.outlier_count = 0
    coordinator.data.outlier_statistics = None
    
    entity_id = "climate.test"
    sensor = OutlierDetectionSensor(coordinator, entity_id)
    
    # Should handle missing statistics
    attributes = sensor.extra_state_attributes
    assert attributes["outlier_count"] == 0
    assert attributes["outlier_rate"] == 0.0
    assert attributes["detection_enabled"] is False