"""ABOUTME: Tests for SmartClimateEntity outlier detection properties.
Tests outlier detection integration with coordinator data."""

import pytest
from unittest.mock import Mock, AsyncMock

from custom_components.smart_climate.climate import SmartClimateEntity
from tests.fixtures.mock_entities import (
    create_mock_hass,
    create_mock_offset_engine,
    create_mock_sensor_manager,
    create_mock_mode_manager,
    create_mock_temperature_controller,
    create_mock_coordinator,
)


class TestSmartClimateEntityOutlierDetection:
    """Test SmartClimateEntity outlier detection properties."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_hass = create_mock_hass()
        self.config = {"name": "Test Smart Climate"}
        self.entity_id = "climate.smart_test"
        
        # Create standard mocks
        self.mock_offset_engine = create_mock_offset_engine()
        self.mock_sensor_manager = create_mock_sensor_manager()
        self.mock_mode_manager = create_mock_mode_manager()
        self.mock_temperature_controller = create_mock_temperature_controller()
        self.mock_coordinator = create_mock_coordinator()
        
        # Create entity instance
        self.entity = SmartClimateEntity(
            hass=self.mock_hass,
            config=self.config,
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room_temp",
            offset_engine=self.mock_offset_engine,
            sensor_manager=self.mock_sensor_manager,
            mode_manager=self.mock_mode_manager,
            temperature_controller=self.mock_temperature_controller,
            coordinator=self.mock_coordinator,
        )
        # Set entity_id after creation
        self.entity.entity_id = self.entity_id

    def test_outlier_detection_active_property(self):
        """Test outlier_detection_active returns coordinator status."""
        # Test when outlier detection is enabled
        self.mock_coordinator.outlier_detection_enabled = True
        assert self.entity.outlier_detection_active is True
        
        # Test when outlier detection is disabled
        self.mock_coordinator.outlier_detection_enabled = False
        assert self.entity.outlier_detection_active is False
        
        # Test when coordinator has no outlier_detection_enabled attribute
        delattr(self.mock_coordinator, 'outlier_detection_enabled')
        assert self.entity.outlier_detection_active is False

    def test_outlier_detected_property(self):
        """Test outlier_detected returns entity outlier status."""
        # Test when entity has outlier detected
        self.mock_coordinator.data.outliers = {self.entity_id: True}
        assert self.entity.outlier_detected is True
        
        # Test when entity has no outlier detected
        self.mock_coordinator.data.outliers = {self.entity_id: False}
        assert self.entity.outlier_detected is False
        
        # Test when entity is not in outliers dict
        self.mock_coordinator.data.outliers = {}
        assert self.entity.outlier_detected is False
        
        # Test when coordinator data has no outliers attribute
        delattr(self.mock_coordinator.data, 'outliers')
        assert self.entity.outlier_detected is False

    def test_extra_state_attributes_include_outlier_data(self):
        """Test attributes include is_outlier and outlier_statistics."""
        # Set up outlier data
        self.mock_coordinator.data.outliers = {self.entity_id: True}
        self.mock_coordinator.data.outlier_statistics = {
            "enabled": True,
            "detected_outliers": 5,
            "filtered_samples": 123,
            "outlier_rate": 4.1,
            "temperature_history_size": 50,
            "power_history_size": 30,
            "has_sufficient_data": True
        }
        
        # Get attributes
        attributes = self.entity.extra_state_attributes
        
        # Verify outlier data is included
        assert attributes["is_outlier"] is True
        assert attributes["outlier_statistics"] == {
            "enabled": True,
            "detected_outliers": 5,
            "filtered_samples": 123,
            "outlier_rate": 4.1,
            "temperature_history_size": 50,
            "power_history_size": 30,
            "has_sufficient_data": True
        }

    def test_outlier_properties_with_no_coordinator(self):
        """Test graceful handling when coordinator unavailable."""
        # Create entity with None coordinator
        entity = SmartClimateEntity(
            hass=self.mock_hass,
            config=self.config,
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room_temp",
            offset_engine=self.mock_offset_engine,
            sensor_manager=self.mock_sensor_manager,
            mode_manager=self.mock_mode_manager,
            temperature_controller=self.mock_temperature_controller,
            coordinator=None,
        )
        entity.entity_id = self.entity_id
        
        # Test properties return safe defaults
        assert entity.outlier_detection_active is False
        assert entity.outlier_detected is False
        
        # Test attributes include safe defaults
        attributes = entity.extra_state_attributes
        assert attributes["is_outlier"] is False
        assert attributes["outlier_statistics"] == {}

    def test_outlier_properties_with_disabled_detection(self):
        """Test behavior when outlier detection disabled."""
        # Disable outlier detection
        self.mock_coordinator.outlier_detection_enabled = False
        self.mock_coordinator.data.outliers = {}
        self.mock_coordinator.data.outlier_statistics = {}
        
        # Test properties
        assert self.entity.outlier_detection_active is False
        assert self.entity.outlier_detected is False
        
        # Test attributes
        attributes = self.entity.extra_state_attributes
        assert attributes["is_outlier"] is False
        assert attributes["outlier_statistics"] == {}