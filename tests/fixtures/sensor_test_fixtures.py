"""Test fixtures for sensor availability testing."""

from unittest.mock import Mock, AsyncMock
from datetime import datetime
from typing import Dict, Any, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)

from custom_components.smart_climate.const import DOMAIN


def create_mock_offset_engine_with_coordinator():
    """Create a mock OffsetEngine with coordinator reference."""
    mock_engine = Mock()
    mock_engine.is_learning_enabled = True
    
    # Mock coordinator with data
    mock_coordinator = Mock()
    mock_coordinator.data = Mock()
    mock_coordinator.data.calculated_offset = 1.5
    mock_coordinator.data.room_temp = 22.5
    mock_coordinator.data.outdoor_temp = 28.0
    mock_coordinator.data.power = 150.0
    
    # Set coordinator reference
    mock_engine._coordinator = mock_coordinator
    
    # Mock learning info
    mock_engine.get_learning_info = Mock(return_value={
        "enabled": True,
        "samples": 8,
        "accuracy": 0.75,
        "confidence": 0.85,
        "has_sufficient_data": False,
        "last_sample_time": "2025-07-09T16:45:00",
        "hysteresis_enabled": True,
        "hysteresis_state": "learning_hysteresis",
        "learned_start_threshold": 25.5,
        "learned_stop_threshold": 23.0,
        "temperature_window": 2.5,
        "start_samples_collected": 4,
        "stop_samples_collected": 4,
        "hysteresis_ready": False
    })
    
    return mock_engine


def create_mock_offset_engine_without_coordinator():
    """Create a mock OffsetEngine without coordinator reference."""
    mock_engine = Mock()
    mock_engine.is_learning_enabled = True
    
    # No coordinator reference (this is the bug scenario)
    # Either hasattr returns False or _coordinator is None
    
    # Mock learning info
    mock_engine.get_learning_info = Mock(return_value={
        "enabled": True,
        "samples": 5,
        "accuracy": 0.0,
        "confidence": 0.0,
        "has_sufficient_data": False,
        "last_sample_time": None,
        "hysteresis_enabled": False,
        "hysteresis_state": "disabled",
        "learned_start_threshold": None,
        "learned_stop_threshold": None,
        "temperature_window": None,
        "start_samples_collected": 0,
        "stop_samples_collected": 0,
        "hysteresis_ready": False
    })
    
    return mock_engine


def create_mock_offset_engine_coordinator_no_data():
    """Create a mock OffsetEngine with coordinator but no data."""
    mock_engine = Mock()
    mock_engine.is_learning_enabled = True
    
    # Mock coordinator without data
    mock_coordinator = Mock()
    mock_coordinator.data = None
    
    # Set coordinator reference
    mock_engine._coordinator = mock_coordinator
    
    # Mock learning info
    mock_engine.get_learning_info = Mock(return_value={
        "enabled": False,
        "samples": 0,
        "accuracy": 0.0,
        "confidence": 0.0,
        "has_sufficient_data": False,
        "last_sample_time": None,
        "hysteresis_enabled": False,
        "hysteresis_state": "disabled",
        "learned_start_threshold": None,
        "learned_stop_threshold": None,
        "temperature_window": None,
        "start_samples_collected": 0,
        "stop_samples_collected": 0,
        "hysteresis_ready": False
    })
    
    return mock_engine


def create_mock_config_entry():
    """Create a mock config entry for testing."""
    entry = Mock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.unique_id = "test_unique_id"
    entry.title = "Test Smart Climate"
    entry.data = {
        "climate_entity": "climate.test_ac",
        "room_sensor": "sensor.test_room",
        "power_sensor": "sensor.test_power",
        "max_offset": 5.0,
        "enable_learning": True,
    }
    return entry


def create_realistic_learning_info(samples: int = 8, enabled: bool = True) -> Dict[str, Any]:
    """Create realistic learning info for testing."""
    return {
        "enabled": enabled,
        "samples": samples,
        "accuracy": 0.75 if samples > 5 else 0.0,
        "confidence": 0.85 if samples > 5 else 0.0,
        "has_sufficient_data": samples >= 10,
        "last_sample_time": "2025-07-09T16:45:00" if samples > 0 else None,
        "hysteresis_enabled": True,
        "hysteresis_state": "learning_hysteresis" if samples < 10 else "idle_stable_zone",
        "learned_start_threshold": 25.5 if samples > 3 else None,
        "learned_stop_threshold": 23.0 if samples > 3 else None,
        "temperature_window": 2.5 if samples > 3 else None,
        "start_samples_collected": min(samples // 2, 5),
        "stop_samples_collected": min(samples // 2, 5),
        "hysteresis_ready": samples >= 10
    }


def create_sensor_test_data():
    """Create test data for all sensor types."""
    return {
        "offset_current": {
            "coordinator_value": 2.3,
            "expected_value": 2.3,
            "unit": UnitOfTemperature.CELSIUS,
            "device_class": SensorDeviceClass.TEMPERATURE,
            "state_class": SensorStateClass.MEASUREMENT
        },
        "learning_progress": {
            "samples": 8,
            "enabled": True,
            "expected_value": 80,  # 8/10 * 100
            "unit": PERCENTAGE,
            "device_class": None,
            "state_class": SensorStateClass.MEASUREMENT
        },
        "accuracy_current": {
            "accuracy": 0.75,
            "expected_value": 75,  # 0.75 * 100
            "unit": PERCENTAGE,
            "device_class": None,
            "state_class": SensorStateClass.MEASUREMENT
        },
        "calibration_status": {
            "samples": 8,
            "enabled": True,
            "expected_value": "In Progress (8/10 samples)",
            "unit": None,
            "device_class": None,
            "state_class": None
        },
        "hysteresis_state": {
            "hysteresis_state": "learning_hysteresis",
            "expected_value": "Learning AC behavior",
            "unit": None,
            "device_class": None,
            "state_class": None
        }
    }


def create_exception_scenario_offset_engine():
    """Create an OffsetEngine that raises exceptions for testing error handling."""
    mock_engine = Mock()
    mock_engine.is_learning_enabled = True
    
    # Mock coordinator with data
    mock_coordinator = Mock()
    mock_coordinator.data = Mock()
    mock_coordinator.data.calculated_offset = 1.5
    mock_engine._coordinator = mock_coordinator
    
    # Mock get_learning_info to raise exception
    mock_engine.get_learning_info = Mock(side_effect=Exception("Test exception"))
    
    return mock_engine


def create_missing_coordinator_attribute_engine():
    """Create an OffsetEngine that doesn't have _coordinator attribute at all."""
    mock_engine = Mock()
    mock_engine.is_learning_enabled = True
    
    # Don't set _coordinator attribute at all
    # This simulates hasattr(self._offset_engine, '_coordinator') returning False
    
    # Mock learning info
    mock_engine.get_learning_info = Mock(return_value={
        "enabled": True,
        "samples": 5,
        "accuracy": 0.0,
        "confidence": 0.0,
        "has_sufficient_data": False,
        "last_sample_time": None,
        "hysteresis_enabled": False,
        "hysteresis_state": "disabled",
        "learned_start_threshold": None,
        "learned_stop_threshold": None,
        "temperature_window": None,
        "start_samples_collected": 0,
        "stop_samples_collected": 0,
        "hysteresis_ready": False
    })
    
    return mock_engine


def create_sensor_availability_test_scenarios():
    """Create different test scenarios for sensor availability."""
    return {
        "available_with_coordinator_data": {
            "offset_engine": create_mock_offset_engine_with_coordinator(),
            "expected_available": True,
            "description": "Sensor should be available when coordinator has data"
        },
        "unavailable_no_coordinator": {
            "offset_engine": create_mock_offset_engine_without_coordinator(),
            "expected_available": False,
            "description": "Sensor should be unavailable when no coordinator"
        },
        "unavailable_coordinator_no_data": {
            "offset_engine": create_mock_offset_engine_coordinator_no_data(),
            "expected_available": False,
            "description": "Sensor should be unavailable when coordinator has no data"
        },
        "unavailable_missing_coordinator_attribute": {
            "offset_engine": create_missing_coordinator_attribute_engine(),
            "expected_available": False,
            "description": "Sensor should be unavailable when _coordinator attribute missing"
        },
        "exception_handling": {
            "offset_engine": create_exception_scenario_offset_engine(),
            "expected_available": True,  # Still available since coordinator.data exists
            "description": "Sensor availability not affected by get_learning_info exceptions"
        }
    }