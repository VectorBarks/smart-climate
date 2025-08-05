"""
ABOUTME: Comprehensive end-to-end integration tests for complete climate entity outlier integration
ABOUTME: Tests complete outlier detection flow from coordinator to entity with multiple scenarios
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant

from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.coordinator import SmartClimateCoordinator
from custom_components.smart_climate.models import SmartClimateData, ModeAdjustments, OffsetResult
from custom_components.smart_climate.outlier_detector import OutlierDetector
from tests.fixtures.mock_entities import (
    create_mock_hass,
    create_mock_offset_engine,
    create_mock_sensor_manager,
    create_mock_mode_manager,
    create_mock_temperature_controller,
    create_mock_coordinator,
)


@pytest.fixture
def mock_outlier_detector():
    """Create mock OutlierDetector with complete functionality."""
    detector = Mock(spec=OutlierDetector)
    detector.is_temperature_outlier.return_value = False
    detector.is_power_outlier.return_value = False
    detector.add_temperature_sample = Mock()
    detector.add_power_sample = Mock()
    detector.get_history_size.return_value = 25
    detector.has_sufficient_data.return_value = True
    detector.get_outlier_statistics.return_value = {
        "enabled": True,
        "detected_outliers": 2,
        "filtered_samples": 48,
        "outlier_rate": 0.04,
        "temperature_history_size": 25,
        "power_history_size": 20,
        "has_sufficient_data": True
    }
    return detector


@pytest.fixture
def mock_coordinator_with_outlier_data():
    """Create coordinator with comprehensive outlier detection data."""
    coordinator = create_mock_coordinator()
    coordinator.outlier_detection_enabled = True
    coordinator._outlier_detector = Mock(spec=OutlierDetector)
    coordinator.data = SmartClimateData(
        room_temp=22.5,
        outdoor_temp=28.0,
        power=1200.0,
        calculated_offset=1.5,
        mode_adjustments=ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        ),
        outliers={"climate.smart_test": False, "climate.smart_test_2": True},
        outlier_count=1,
        outlier_statistics={
            "enabled": True,
            "temperature_outliers": 0,
            "power_outliers": 1,
            "total_samples": 50,
            "outlier_rate": 0.02
        }
    )
    return coordinator


@pytest.fixture
def integration_entities_config():
    """Configuration for multiple entity integration testing."""
    return [
        {
            "entity_id": "climate.smart_test",
            "config": {"name": "Test Smart Climate 1"},
            "wrapped_entity_id": "climate.test_ac_1",
            "room_sensor_id": "sensor.room_temp_1"
        },
        {
            "entity_id": "climate.smart_test_2", 
            "config": {"name": "Test Smart Climate 2"},
            "wrapped_entity_id": "climate.test_ac_2",
            "room_sensor_id": "sensor.room_temp_2"
        }
    ]


class TestEndToEndOutlierDetectionFlow:
    """Test complete outlier detection flow from coordinator to entity."""
    
    def setup_method(self):
        """Set up test fixtures for each test."""
        self.mock_hass = create_mock_hass()
    
    def test_end_to_end_outlier_detection_flow(self, mock_coordinator_with_outlier_data):
        """Test complete coordinator → entity data flow with outlier detection."""
        # Arrange - Create entity with coordinator containing outlier data
        coordinator = mock_coordinator_with_outlier_data
        
        entity = SmartClimateEntity(
            hass=self.mock_hass,
            config={"name": "Test Smart Climate"},
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=create_mock_offset_engine(),
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=coordinator,
        )
        entity.entity_id = "climate.smart_test"
        
        # Act - Verify complete data flow from coordinator to entity
        outlier_active = entity.outlier_detection_active
        outlier_detected = entity.outlier_detected
        attributes = entity.extra_state_attributes
        
        # Assert - Complete outlier detection flow is working
        assert outlier_active is True, "Outlier detection should be active"
        assert outlier_detected is False, "This entity should not have outliers detected"
        assert "is_outlier" in attributes, "Entity attributes should include outlier status"
        assert attributes["is_outlier"] is False, "Entity should not be flagged as outlier"
        assert "outlier_statistics" in attributes, "Entity should expose outlier statistics"
        assert attributes["outlier_statistics"]["enabled"] is True, "Statistics should show detection enabled"
        assert attributes["outlier_statistics"]["total_samples"] == 50, "Statistics should match coordinator data"
        
        # Verify coordinator data is properly consumed by entity
        assert coordinator.data.outlier_count == 1, "Coordinator should track outlier count"
        assert len(coordinator.data.outliers) == 2, "Coordinator should track multiple entities"
        assert coordinator.data.outliers["climate.smart_test"] is False, "Entity 1 should be normal"
        assert coordinator.data.outliers["climate.smart_test_2"] is True, "Entity 2 should be outlier"


class TestEntityPropertiesReflectCoordinatorData:
    """Test entity properties match coordinator state."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_hass = create_mock_hass()
    
    def test_entity_properties_reflect_coordinator_data(self, mock_coordinator_with_outlier_data):
        """Test entity properties accurately reflect coordinator data."""
        # Arrange - Create entity with comprehensive coordinator data
        coordinator = mock_coordinator_with_outlier_data
        
        entity = SmartClimateEntity(
            hass=self.mock_hass,
            config={"name": "Test Smart Climate"},
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=create_mock_offset_engine(),
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=coordinator,
        )
        entity.entity_id = "climate.smart_test"
        
        # Act - Check all entity properties match coordinator state
        
        # Assert - Entity properties reflect coordinator data exactly
        assert entity.outlier_detection_active == coordinator.outlier_detection_enabled
        assert entity.outlier_detected == coordinator.data.outliers.get(entity.entity_id, False)
        
        # Test with different coordinator states
        coordinator.outlier_detection_enabled = False
        assert entity.outlier_detection_active is False
        
        coordinator.data.outliers[entity.entity_id] = True
        assert entity.outlier_detected is True
        
        # Test outlier statistics match exactly
        attributes = entity.extra_state_attributes
        expected_stats = coordinator.data.outlier_statistics
        assert attributes["outlier_statistics"] == expected_stats
        
        # Test edge case: entity not in outliers dict
        del coordinator.data.outliers[entity.entity_id]
        assert entity.outlier_detected is False
        
        # Test edge case: coordinator has no outlier data
        coordinator.data.outliers = {}
        coordinator.data.outlier_statistics = {}
        attributes = entity.extra_state_attributes
        assert attributes["is_outlier"] is False
        assert attributes["outlier_statistics"] == {}


class TestEntityAttributesUpdateWithOutlierChanges:
    """Test attributes update when outliers detected."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_hass = create_mock_hass()
    
    def test_entity_attributes_update_with_outlier_changes(self, mock_coordinator_with_outlier_data):
        """Test attributes update dynamically when outlier status changes."""
        # Arrange - Create entity with initial normal state
        coordinator = mock_coordinator_with_outlier_data
        coordinator.data.outliers = {"climate.smart_test": False}
        coordinator.data.outlier_count = 0
        
        entity = SmartClimateEntity(
            hass=self.mock_hass,
            config={"name": "Test Smart Climate"},
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=create_mock_offset_engine(),
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=coordinator,
        )
        entity.entity_id = "climate.smart_test"
        
        # Act & Assert - Test initial normal state
        initial_attributes = entity.extra_state_attributes
        assert initial_attributes["is_outlier"] is False
        assert entity.outlier_detected is False
        
        # Act - Simulate outlier detection for this entity
        coordinator.data.outliers["climate.smart_test"] = True
        coordinator.data.outlier_count = 1
        coordinator.data.outlier_statistics.update({
            "temperature_outliers": 1,
            "power_outliers": 0,
            "total_samples": 51,
            "outlier_rate": 0.02
        })
        
        # Assert - Attributes should reflect outlier detection
        updated_attributes = entity.extra_state_attributes
        assert updated_attributes["is_outlier"] is True
        assert entity.outlier_detected is True
        assert updated_attributes["outlier_statistics"]["temperature_outliers"] == 1
        assert updated_attributes["outlier_statistics"]["total_samples"] == 51
        
        # Act - Simulate outlier resolution
        coordinator.data.outliers["climate.smart_test"] = False
        coordinator.data.outlier_count = 0
        coordinator.data.outlier_statistics.update({
            "temperature_outliers": 0,
            "power_outliers": 0,
            "total_samples": 52,
            "outlier_rate": 0.0
        })
        
        # Assert - Attributes should reflect outlier resolution
        resolved_attributes = entity.extra_state_attributes
        assert resolved_attributes["is_outlier"] is False
        assert entity.outlier_detected is False
        assert resolved_attributes["outlier_statistics"]["outlier_rate"] == 0.0
        assert resolved_attributes["outlier_statistics"]["total_samples"] == 52


class TestOutlierDetectionEnableDisableCycle:
    """Test enabling/disabling outlier detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_hass = create_mock_hass()
    
    def test_outlier_detection_enable_disable_cycle(self, mock_coordinator_with_outlier_data):
        """Test enabling/disabling outlier detection affects entity behavior."""
        # Arrange - Create entity with outlier detection initially enabled
        coordinator = mock_coordinator_with_outlier_data
        coordinator.outlier_detection_enabled = True
        
        entity = SmartClimateEntity(
            hass=self.mock_hass,
            config={"name": "Test Smart Climate"},
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=create_mock_offset_engine(),
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=coordinator,
        )
        entity.entity_id = "climate.smart_test"
        
        # Act & Assert - Test enabled state
        assert entity.outlier_detection_active is True
        enabled_attributes = entity.extra_state_attributes
        assert enabled_attributes["outlier_statistics"]["enabled"] is True
        
        # Act - Disable outlier detection
        coordinator.outlier_detection_enabled = False
        coordinator.data.outliers = {}
        coordinator.data.outlier_count = 0
        coordinator.data.outlier_statistics = {
            "enabled": False,
            "temperature_outliers": 0,
            "power_outliers": 0,
            "total_samples": 0,
            "outlier_rate": 0.0
        }
        
        # Assert - Entity should reflect disabled state
        assert entity.outlier_detection_active is False
        assert entity.outlier_detected is False
        disabled_attributes = entity.extra_state_attributes
        assert disabled_attributes["is_outlier"] is False
        assert disabled_attributes["outlier_statistics"]["enabled"] is False
        assert disabled_attributes["outlier_statistics"]["total_samples"] == 0
        
        # Act - Re-enable outlier detection
        coordinator.outlier_detection_enabled = True
        coordinator.data.outliers = {"climate.smart_test": False}
        coordinator.data.outlier_count = 0
        coordinator.data.outlier_statistics = {
            "enabled": True,
            "temperature_outliers": 0,
            "power_outliers": 0,
            "total_samples": 10,
            "outlier_rate": 0.0
        }
        
        # Assert - Entity should reflect re-enabled state
        assert entity.outlier_detection_active is True
        reenabled_attributes = entity.extra_state_attributes
        assert reenabled_attributes["outlier_statistics"]["enabled"] is True
        assert reenabled_attributes["outlier_statistics"]["total_samples"] == 10


class TestMultipleEntitiesOutlierIndependence:
    """Test outlier detection works independently for multiple entities."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_hass = create_mock_hass()
    
    def test_multiple_entities_outlier_independence(self, integration_entities_config, mock_coordinator_with_outlier_data):
        """Test outlier detection works independently for multiple entities."""
        # Arrange - Create multiple entities sharing same coordinator
        coordinator = mock_coordinator_with_outlier_data
        coordinator.data.outliers = {
            "climate.smart_test": False,  # Entity 1: Normal
            "climate.smart_test_2": True, # Entity 2: Outlier
            "climate.smart_test_3": False # Entity 3: Normal
        }
        coordinator.data.outlier_count = 1
        
        entities = []
        for config in integration_entities_config:
            entity = SmartClimateEntity(
                hass=self.mock_hass,
                config=config["config"],
                wrapped_entity_id=config["wrapped_entity_id"],
                room_sensor_id=config["room_sensor_id"],
                offset_engine=create_mock_offset_engine(),
                sensor_manager=create_mock_sensor_manager(),
                mode_manager=create_mock_mode_manager(),
                temperature_controller=create_mock_temperature_controller(),
                coordinator=coordinator,
            )
            entity.entity_id = config["entity_id"]
            entities.append(entity)
        
        # Add third entity for comprehensive testing
        entity3 = SmartClimateEntity(
            hass=self.mock_hass,
            config={"name": "Test Smart Climate 3"},
            wrapped_entity_id="climate.test_ac_3",
            room_sensor_id="sensor.room_temp_3",
            offset_engine=create_mock_offset_engine(),
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=coordinator,
        )
        entity3.entity_id = "climate.smart_test_3"
        entities.append(entity3)
        
        # Act & Assert - Verify independent outlier status for each entity
        
        # Entity 1: Normal (no outlier)
        assert entities[0].outlier_detection_active is True
        assert entities[0].outlier_detected is False
        entity1_attrs = entities[0].extra_state_attributes
        assert entity1_attrs["is_outlier"] is False
        
        # Entity 2: Outlier detected
        assert entities[1].outlier_detection_active is True
        assert entities[1].outlier_detected is True
        entity2_attrs = entities[1].extra_state_attributes
        assert entity2_attrs["is_outlier"] is True
        
        # Entity 3: Normal (no outlier)
        assert entities[2].outlier_detection_active is True
        assert entities[2].outlier_detected is False
        entity3_attrs = entities[2].extra_state_attributes
        assert entity3_attrs["is_outlier"] is False
        
        # All entities should share same outlier statistics from coordinator
        for entity in entities:
            attrs = entity.extra_state_attributes
            assert attrs["outlier_statistics"]["enabled"] is True
            assert attrs["outlier_statistics"]["total_samples"] == 50
            assert attrs["outlier_statistics"]["outlier_rate"] == 0.02
        
        # Act - Change outlier status for specific entity
        coordinator.data.outliers["climate.smart_test"] = True  # Entity 1 becomes outlier
        coordinator.data.outliers["climate.smart_test_2"] = False  # Entity 2 becomes normal
        coordinator.data.outlier_count = 1  # Still 1 outlier total
        
        # Assert - Only affected entities change status
        assert entities[0].outlier_detected is True  # Entity 1 now outlier
        assert entities[1].outlier_detected is False  # Entity 2 now normal
        assert entities[2].outlier_detected is False  # Entity 3 unchanged
        
        # All should still be active
        for entity in entities:
            assert entity.outlier_detection_active is True


class TestOutlierDetectionWithSensorFailures:
    """Test handling of sensor unavailability."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_hass = create_mock_hass()
    
    def test_outlier_detection_with_sensor_failures(self, mock_coordinator_with_outlier_data):
        """Test outlier detection handles sensor unavailability gracefully."""
        # Arrange - Create entity with coordinator
        coordinator = mock_coordinator_with_outlier_data
        
        entity = SmartClimateEntity(
            hass=self.mock_hass,
            config={"name": "Test Smart Climate"},
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=create_mock_offset_engine(),
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=coordinator,
        )
        entity.entity_id = "climate.smart_test"
        
        # Act & Assert - Test normal operation first
        assert entity.outlier_detection_active is True
        initial_attributes = entity.extra_state_attributes
        assert initial_attributes["outlier_statistics"]["enabled"] is True
        
        # Act - Simulate sensor failures (None values in coordinator data)
        coordinator.data.room_temp = None
        coordinator.data.outdoor_temp = None
        coordinator.data.power = None
        
        # Coordinator should still provide outlier data even with sensor failures
        coordinator.data.outliers = {"climate.smart_test": False}
        coordinator.data.outlier_count = 0
        coordinator.data.outlier_statistics = {
            "enabled": True,
            "temperature_outliers": 0,
            "power_outliers": 0,
            "total_samples": 25,  # Reduced due to missing data
            "outlier_rate": 0.0
        }
        
        # Assert - Entity should handle sensor failures gracefully
        assert entity.outlier_detection_active is True  # Still active
        assert entity.outlier_detected is False  # No outliers with missing data
        failure_attributes = entity.extra_state_attributes
        assert failure_attributes["is_outlier"] is False
        assert failure_attributes["outlier_statistics"]["enabled"] is True
        assert failure_attributes["outlier_statistics"]["total_samples"] == 25
        
        # Act - Simulate partial sensor recovery
        coordinator.data.room_temp = 22.0  # Room sensor recovers
        coordinator.data.outdoor_temp = None  # Outdoor still missing
        coordinator.data.power = 1100.0  # Power sensor recovers
        
        coordinator.data.outlier_statistics["total_samples"] = 35  # More data available
        
        # Assert - Entity should work with partial sensor recovery
        partial_recovery_attrs = entity.extra_state_attributes
        assert partial_recovery_attrs["outlier_statistics"]["total_samples"] == 35
        assert partial_recovery_attrs["outlier_statistics"]["enabled"] is True
        
        # Act - Simulate complete sensor recovery
        coordinator.data.room_temp = 22.5
        coordinator.data.outdoor_temp = 28.0
        coordinator.data.power = 1200.0
        coordinator.data.outlier_statistics["total_samples"] = 50  # Full data restored
        
        # Assert - Entity should return to normal operation
        recovery_attributes = entity.extra_state_attributes
        assert recovery_attributes["outlier_statistics"]["total_samples"] == 50
        assert entity.outlier_detection_active is True


class TestOutlierStatisticsAccuracy:
    """Test statistics calculations are accurate."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_hass = create_mock_hass()
    
    def test_outlier_statistics_accuracy(self, mock_coordinator_with_outlier_data):
        """Test outlier statistics calculations are mathematically accurate."""
        # Arrange - Create entity with coordinator containing precise statistics
        coordinator = mock_coordinator_with_outlier_data
        
        # Set up precise test data for statistics validation
        coordinator.data.outliers = {
            "climate.smart_test": False,
            "climate.smart_test_2": True,
            "climate.smart_test_3": False
        }
        coordinator.data.outlier_count = 1
        coordinator.data.outlier_statistics = {
            "enabled": True,
            "temperature_outliers": 3,  # Temperature outliers detected
            "power_outliers": 2,        # Power outliers detected
            "total_samples": 100,       # Total samples processed
            "outlier_rate": 0.05        # (3+2)/100 = 5% outlier rate
        }
        
        entity = SmartClimateEntity(
            hass=self.mock_hass,
            config={"name": "Test Smart Climate"},
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=create_mock_offset_engine(),
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=coordinator,
        )
        entity.entity_id = "climate.smart_test"
        
        # Act - Get statistics from entity
        attributes = entity.extra_state_attributes
        stats = attributes["outlier_statistics"]
        
        # Assert - Verify mathematical accuracy of statistics
        assert stats["temperature_outliers"] == 3
        assert stats["power_outliers"] == 2
        assert stats["total_samples"] == 100
        
        # Verify outlier rate calculation: (temp_outliers + power_outliers) / total_samples
        expected_outlier_rate = (stats["temperature_outliers"] + stats["power_outliers"]) / stats["total_samples"]
        assert abs(stats["outlier_rate"] - expected_outlier_rate) < 0.001, f"Expected {expected_outlier_rate}, got {stats['outlier_rate']}"
        assert stats["outlier_rate"] == 0.05
        
        # Test with different numbers to verify calculation
        coordinator.data.outlier_statistics.update({
            "temperature_outliers": 7,
            "power_outliers": 3,
            "total_samples": 200,
            "outlier_rate": 0.05  # (7+3)/200 = 5%
        })
        
        updated_attributes = entity.extra_state_attributes
        updated_stats = updated_attributes["outlier_statistics"]
        expected_rate = (7 + 3) / 200
        assert abs(updated_stats["outlier_rate"] - expected_rate) < 0.001
        assert updated_stats["outlier_rate"] == 0.05
        
        # Test edge case: no outliers
        coordinator.data.outlier_statistics.update({
            "temperature_outliers": 0,
            "power_outliers": 0,
            "total_samples": 150,
            "outlier_rate": 0.0
        })
        
        zero_outliers_attrs = entity.extra_state_attributes
        zero_stats = zero_outliers_attrs["outlier_statistics"]
        assert zero_stats["outlier_rate"] == 0.0
        assert zero_stats["temperature_outliers"] == 0
        assert zero_stats["power_outliers"] == 0
        
        # Test edge case: all outliers (hypothetical stress test)
        coordinator.data.outlier_statistics.update({
            "temperature_outliers": 50,
            "power_outliers": 50,
            "total_samples": 100,
            "outlier_rate": 1.0  # 100% outlier rate
        })
        
        all_outliers_attrs = entity.extra_state_attributes
        all_stats = all_outliers_attrs["outlier_statistics"]
        assert all_stats["outlier_rate"] == 1.0
        assert all_stats["temperature_outliers"] == 50
        assert all_stats["power_outliers"] == 50


class TestOutlierDetectionErrorHandling:
    """Test robust error handling in outlier detection integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_hass = create_mock_hass()
    
    def test_entity_handles_missing_coordinator(self):
        """Test entity gracefully handles missing coordinator."""
        # Arrange - Create entity with None coordinator
        entity = SmartClimateEntity(
            hass=self.mock_hass,
            config={"name": "Test Smart Climate"},
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=create_mock_offset_engine(),
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=None,
        )
        entity.entity_id = "climate.smart_test"
        
        # Act & Assert - Entity should provide safe defaults
        assert entity.outlier_detection_active is False
        assert entity.outlier_detected is False
        
        attributes = entity.extra_state_attributes
        assert attributes["is_outlier"] is False
        assert attributes["outlier_statistics"] == {}
    
    def test_entity_handles_corrupted_coordinator_data(self, mock_coordinator_with_outlier_data):
        """Test entity handles corrupted or incomplete coordinator data."""
        # Arrange - Create entity with coordinator containing partial/corrupted data
        coordinator = mock_coordinator_with_outlier_data
        
        entity = SmartClimateEntity(
            hass=self.mock_hass,
            config={"name": "Test Smart Climate"},
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=create_mock_offset_engine(),
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=coordinator,
        )
        entity.entity_id = "climate.smart_test"
        
        # Act - Remove outlier detection attributes from coordinator
        delattr(coordinator, 'outlier_detection_enabled')
        delattr(coordinator.data, 'outliers')
        delattr(coordinator.data, 'outlier_statistics')
        
        # Assert - Entity should handle missing attributes gracefully
        assert entity.outlier_detection_active is False
        assert entity.outlier_detected is False
        
        attributes = entity.extra_state_attributes
        assert attributes["is_outlier"] is False
        assert attributes["outlier_statistics"] == {}
    
    def test_entity_handles_invalid_outlier_data_types(self, mock_coordinator_with_outlier_data):
        """Test entity handles invalid data types in outlier data."""
        # Arrange - Create entity with coordinator
        coordinator = mock_coordinator_with_outlier_data
        
        entity = SmartClimateEntity(
            hass=self.mock_hass,
            config={"name": "Test Smart Climate"},
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=create_mock_offset_engine(),
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=coordinator,
        )
        entity.entity_id = "climate.smart_test"
        
        # Act - Set invalid data types
        coordinator.data.outliers = "invalid_string"  # Should be dict
        coordinator.data.outlier_statistics = None   # Should be dict
        coordinator.outlier_detection_enabled = "yes"  # Should be bool
        
        # Assert - Entity should handle invalid types gracefully
        # outlier_detection_active should handle non-boolean values
        assert entity.outlier_detection_active is True  # "yes" is truthy
        
        # outlier_detected should handle non-dict outliers
        assert entity.outlier_detected is False  # Can't find entity in non-dict
        
        attributes = entity.extra_state_attributes
        assert attributes["is_outlier"] is False
        
        # Should provide empty dict for None outlier_statistics
        expected_stats = coordinator.data.outlier_statistics or {}
        assert attributes["outlier_statistics"] == expected_stats