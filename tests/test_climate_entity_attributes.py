"""Tests for SmartClimateEntity attribute extensions.

ABOUTME: Tests comprehensive outlier statistics in entity attributes
Following TDD approach - tests written before implementation
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.models import SmartClimateData, ModeAdjustments
from tests.fixtures.mock_entities import (
    create_mock_hass,
    create_mock_offset_engine,
    create_mock_sensor_manager,
    create_mock_mode_manager,
    create_mock_temperature_controller,
    create_mock_coordinator
)


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    return {
        "climate_entity": "climate.test_ac",
        "room_sensor": "sensor.room_temp",
        "learning_enabled": True,
        "update_interval": 180,
        "feedback_delay": 45,
        "min_temperature": 16,
        "max_temperature": 30,
    }


@pytest.fixture
def mock_coordinator_with_outlier_data():
    """Create mock coordinator with outlier detection data."""
    coordinator = create_mock_coordinator()
    
    # Mock coordinator data with outlier statistics as per c_architecture.md Section 9.2
    coordinator.data = SmartClimateData(
        room_temp=25.5,
        outdoor_temp=30.2,
        power=1200.0,
        calculated_offset=2.1,
        mode_adjustments=ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        ),
        is_startup_calculation=False
    )
    
    # Add outlier detection data as per architecture specification
    coordinator.data.outliers = {"climate.test_ac": False}
    coordinator.data.outlier_count = 3
    coordinator.data.outlier_statistics = {
        "enabled": True,
        "detected_outliers": 3,
        "filtered_samples": 97,
        "outlier_rate": 3.0,
        "temperature_history_size": 50,
        "power_history_size": 50,
        "has_sufficient_data": True
    }
    
    return coordinator


@pytest.fixture
def smart_climate_entity(mock_config, mock_coordinator_with_outlier_data):
    """Create SmartClimateEntity instance with mocked dependencies."""
    mock_hass = create_mock_hass()
    mock_offset_engine = create_mock_offset_engine()
    mock_sensor_manager = create_mock_sensor_manager()
    mock_mode_manager = create_mock_mode_manager()
    mock_temperature_controller = create_mock_temperature_controller()
    
    entity = SmartClimateEntity(
        hass=mock_hass,
        config=mock_config,
        wrapped_entity_id="climate.test_ac",
        room_sensor_id="sensor.room_temp",
        offset_engine=mock_offset_engine,
        sensor_manager=mock_sensor_manager,
        mode_manager=mock_mode_manager,
        temperature_controller=mock_temperature_controller,
        coordinator=mock_coordinator_with_outlier_data,
        forecast_engine=None
    )
    
    # Set entity attributes
    entity._attr_unique_id = "smart_climate_test_ac"
    entity._attr_name = "Smart Climate Test AC"
    entity._last_offset = 2.1
    entity._feedback_delay = 45
    
    return entity


def test_attributes_include_outlier_statistics(smart_climate_entity):
    """Test that outlier statistics are included in entity attributes."""
    # This should fail initially - we haven't implemented the outlier statistics yet
    attributes = smart_climate_entity.extra_state_attributes
    
    # Verify outlier statistics are present
    assert "outlier_statistics" in attributes
    
    outlier_stats = attributes["outlier_statistics"]
    assert isinstance(outlier_stats, dict)
    
    # Verify all required statistics as per c_architecture.md Section 9.3
    expected_keys = [
        "detected_outliers",
        "filtered_samples", 
        "outlier_rate",
        "temperature_history_size",
        "power_history_size"
    ]
    
    for key in expected_keys:
        assert key in outlier_stats, f"Missing outlier statistic: {key}"


def test_attributes_structure_validation(smart_climate_entity):
    """Test that outlier statistics have correct data types."""
    attributes = smart_climate_entity.extra_state_attributes
    outlier_stats = attributes["outlier_statistics"]
    
    # Test data types are correct
    assert isinstance(outlier_stats["detected_outliers"], int)
    assert isinstance(outlier_stats["filtered_samples"], int)
    assert isinstance(outlier_stats["outlier_rate"], float)
    assert isinstance(outlier_stats["temperature_history_size"], int)
    assert isinstance(outlier_stats["power_history_size"], int)
    
    # Test reasonable value ranges
    assert outlier_stats["detected_outliers"] >= 0
    assert outlier_stats["filtered_samples"] >= 0
    assert 0.0 <= outlier_stats["outlier_rate"] <= 100.0
    assert outlier_stats["temperature_history_size"] >= 0
    assert outlier_stats["power_history_size"] >= 0


def test_attributes_update_with_coordinator(mock_config):
    """Test that attributes update when coordinator data changes."""
    # Create coordinator with initial data
    coordinator = create_mock_coordinator()
    coordinator.data = SmartClimateData(
        room_temp=24.0,
        outdoor_temp=28.0,
        power=1000.0,
        calculated_offset=1.5,
        mode_adjustments=ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        ),
        is_startup_calculation=False
    )
    
    # Add initial outlier statistics
    coordinator.data.outliers = {"climate.test_ac": False}
    coordinator.data.outlier_count = 2
    coordinator.data.outlier_statistics = {
        "enabled": True,
        "detected_outliers": 2,
        "filtered_samples": 48,
        "outlier_rate": 4.0,
        "temperature_history_size": 50,
        "power_history_size": 50,
        "has_sufficient_data": True
    }
    
    # Create entity
    mock_hass = create_mock_hass()
    mock_offset_engine = create_mock_offset_engine()
    mock_sensor_manager = create_mock_sensor_manager()
    mock_mode_manager = create_mock_mode_manager()
    mock_temperature_controller = create_mock_temperature_controller()
    
    entity = SmartClimateEntity(
        hass=mock_hass,
        config=mock_config,
        wrapped_entity_id="climate.test_ac",
        room_sensor_id="sensor.room_temp",
        offset_engine=mock_offset_engine,
        sensor_manager=mock_sensor_manager,
        mode_manager=mock_mode_manager,
        temperature_controller=mock_temperature_controller,
        coordinator=coordinator,
        forecast_engine=None
    )
    entity._attr_unique_id = "smart_climate_test_ac"
    entity._last_offset = 1.5
    
    # Get initial attributes
    initial_attributes = entity.extra_state_attributes
    initial_outlier_count = initial_attributes["outlier_statistics"]["detected_outliers"]
    assert initial_outlier_count == 2
    
    # Update coordinator data
    coordinator.data.outlier_count = 5
    coordinator.data.outlier_statistics["detected_outliers"] = 5
    coordinator.data.outlier_statistics["outlier_rate"] = 10.0
    
    # Get updated attributes
    updated_attributes = entity.extra_state_attributes
    updated_outlier_count = updated_attributes["outlier_statistics"]["detected_outliers"]
    updated_outlier_rate = updated_attributes["outlier_statistics"]["outlier_rate"]
    
    # Verify attributes updated with coordinator changes
    assert updated_outlier_count == 5
    assert updated_outlier_rate == 10.0


def test_attributes_handle_missing_statistics(mock_config):
    """Test graceful handling of missing outlier statistics data."""
    # Create coordinator without outlier detection data
    coordinator = create_mock_coordinator()
    coordinator.data = SmartClimateData(
        room_temp=22.5,
        outdoor_temp=26.8,
        power=800.0,
        calculated_offset=1.8,
        mode_adjustments=ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        ),
        is_startup_calculation=False
    )
    
    # Deliberately omit outlier detection attributes
    # coordinator.data has no outliers, outlier_count, or outlier_statistics
    
    # Create entity
    mock_hass = create_mock_hass()
    mock_offset_engine = create_mock_offset_engine()
    mock_sensor_manager = create_mock_sensor_manager()
    mock_mode_manager = create_mock_mode_manager()
    mock_temperature_controller = create_mock_temperature_controller()
    
    entity = SmartClimateEntity(
        hass=mock_hass,
        config=mock_config,
        wrapped_entity_id="climate.test_ac",
        room_sensor_id="sensor.room_temp",
        offset_engine=mock_offset_engine,
        sensor_manager=mock_sensor_manager,
        mode_manager=mock_mode_manager,
        temperature_controller=mock_temperature_controller,
        coordinator=coordinator,
        forecast_engine=None
    )
    entity._attr_unique_id = "smart_climate_test_ac"
    entity._last_offset = 1.8
    
    # Should not raise exception and provide safe defaults
    attributes = entity.extra_state_attributes
    
    # Should still have outlier_statistics but with safe defaults
    assert "outlier_statistics" in attributes
    outlier_stats = attributes["outlier_statistics"]
    
    # Verify safe defaults
    assert outlier_stats["detected_outliers"] == 0
    assert outlier_stats["filtered_samples"] == 0
    assert outlier_stats["outlier_rate"] == 0.0
    assert outlier_stats["temperature_history_size"] == 0
    assert outlier_stats["power_history_size"] == 0


def test_attributes_outlier_rate_calculation(smart_climate_entity):
    """Test that outlier rate is properly calculated and included."""
    attributes = smart_climate_entity.extra_state_attributes
    outlier_stats = attributes["outlier_statistics"]
    
    # Verify outlier rate calculation
    detected = outlier_stats["detected_outliers"]  # 3
    filtered = outlier_stats["filtered_samples"]   # 97
    total_samples = detected + filtered            # 100
    expected_rate = (detected / total_samples) * 100 if total_samples > 0 else 0.0
    
    assert abs(outlier_stats["outlier_rate"] - expected_rate) < 0.001
    assert outlier_stats["outlier_rate"] == 3.0  # 3/100 * 100 = 3.0%