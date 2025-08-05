"""Comprehensive end-to-end integration tests for dashboard sensor integration."""
# ABOUTME: Complete integration tests for dashboard sensor functionality including coordinator integration, entity creation, state updates, and UI discoverability
# Tests the entire dashboard sensor ecosystem from coordinator data through platform setup to entity registry

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any, List

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorStateClass
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, EntityCategory

from custom_components.smart_climate.const import DOMAIN
from custom_components.smart_climate.models import SmartClimateData, ModeAdjustments
from custom_components.smart_climate.outlier_detector import OutlierDetector


@pytest.fixture
def mock_hass():
    """Create a comprehensive mock Home Assistant instance."""
    hass = Mock(spec=HomeAssistant)
    hass.data = {}
    hass.states = Mock()
    hass.config_entries = Mock()
    return hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry with outlier detection enabled."""
    config_entry = Mock(spec=ConfigEntry)
    config_entry.entry_id = "test_config_entry_123"
    config_entry.unique_id = "test_unique_id"
    config_entry.title = "Test Smart Climate"
    config_entry.data = {
        "climate_entity": "climate.test_ac",
        "room_sensor": "sensor.room_temperature",
        "outdoor_sensor": "sensor.outdoor_temperature",
        "power_sensor": "sensor.ac_power",
    }
    config_entry.options = {
        "outlier_detection_enabled": True,
        "outlier_sensitivity": 2.5,
    }
    return config_entry


@pytest.fixture
def mock_outlier_detector():
    """Create a mock OutlierDetector for testing."""
    detector = Mock(spec=OutlierDetector)
    detector.is_temperature_outlier.return_value = False
    detector.is_power_outlier.return_value = False
    detector.add_temperature_sample = Mock()
    detector.add_power_sample = Mock()
    detector.get_history_size.return_value = 25
    detector.has_sufficient_data.return_value = True
    return detector


@pytest.fixture
def mock_coordinator(mock_outlier_detector):
    """Create a mock SmartClimateCoordinator with outlier detection data."""
    coordinator = Mock()
    coordinator.last_update_success = True
    coordinator.name = "test_climate"
    coordinator.async_add_listener = Mock(return_value=lambda: None)
    
    # Create realistic SmartClimateData with outlier fields
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
        outliers={"climate.test_ac": False, "temperature": False, "power": False},
        outlier_count=0,
        outlier_statistics={
            "enabled": True,
            "temperature_outliers": 0,
            "power_outliers": 0,
            "total_samples": 10,
            "outlier_rate": 0.0,
            "history_size": 25,
            "has_sufficient_data": True,
            "last_detection_time": datetime(2025, 8, 5, 20, 0, 0).isoformat(),
        }
    )
    
    # Add outlier detector
    coordinator._outlier_detector = mock_outlier_detector
    coordinator.outlier_detection_enabled = True
    
    return coordinator


@pytest.fixture
def mock_entity_registry():
    """Create a mock entity registry for device info testing."""
    registry = Mock()
    registry.entities = {}
    registry.async_get = Mock(return_value=None)
    return registry


@pytest.fixture
def mock_async_add_entities():
    """Create a mock async_add_entities callback."""
    return AsyncMock(spec=AddEntitiesCallback)


class TestCompleteSensorCreationFlow:
    """Test complete sensor creation flow from config entry to entities."""
    
    @pytest.mark.asyncio
    async def test_complete_sensor_creation_flow(
        self, mock_hass, mock_config_entry, mock_coordinator, mock_async_add_entities
    ):
        """Test full sensor creation from config entry to entities."""
        # Setup hass data with coordinator
        mock_hass.data[DOMAIN] = {
            mock_config_entry.entry_id: {
                "coordinators": {
                    "climate.test_ac": mock_coordinator
                }
            }
        }
        
        # Mock both platform setup functions
        with patch("custom_components.smart_climate.binary_sensor.async_setup_entry") as mock_binary_setup, \
             patch("custom_components.smart_climate.sensor.async_setup_entry") as mock_sensor_setup:
            
            # Import and setup binary sensor platform
            from custom_components.smart_climate.binary_sensor import async_setup_entry as binary_setup
            from custom_components.smart_climate.sensor import async_setup_entry as sensor_setup
            
            # Setup binary sensor platform (OutlierDetectionSensor)
            await binary_setup(mock_hass, mock_config_entry, mock_async_add_entities)
            
            # Setup sensor platform (OutlierCountSensor) 
            await sensor_setup(mock_hass, mock_config_entry, mock_async_add_entities)
            
            # Verify platforms were called
            assert mock_async_add_entities.call_count >= 2
            
            # Get created entities from both calls
            all_created_entities = []
            for call in mock_async_add_entities.call_args_list:
                entities = call[0][0]
                all_created_entities.extend(entities)
            
            # Should have both OutlierDetectionSensor and OutlierCountSensor
            assert len(all_created_entities) >= 2
            
            # Verify entity types
            entity_types = [type(entity).__name__ for entity in all_created_entities]
            assert "OutlierDetectionSensor" in entity_types
            assert "OutlierCountSensor" in entity_types
            
            # Verify entities have proper coordinators
            for entity in all_created_entities:
                assert hasattr(entity, 'coordinator')
                assert entity.coordinator == mock_coordinator
    
    @pytest.mark.asyncio
    async def test_sensor_creation_with_outlier_detection_disabled(
        self, mock_hass, mock_config_entry, mock_coordinator, mock_async_add_entities
    ):
        """Test sensor creation when outlier detection is disabled."""
        # Disable outlier detection
        mock_config_entry.options["outlier_detection_enabled"] = False
        mock_coordinator.outlier_detection_enabled = False
        
        # Setup hass data
        mock_hass.data[DOMAIN] = {
            mock_config_entry.entry_id: {
                "coordinators": {
                    "climate.test_ac": mock_coordinator
                }
            }
        }
        
        with patch("custom_components.smart_climate.binary_sensor.async_setup_entry") as mock_binary_setup, \
             patch("custom_components.smart_climate.sensor.async_setup_entry") as mock_sensor_setup:
            
            from custom_components.smart_climate.binary_sensor import async_setup_entry as binary_setup
            from custom_components.smart_climate.sensor import async_setup_entry as sensor_setup
            
            # Setup platforms
            await binary_setup(mock_hass, mock_config_entry, mock_async_add_entities)
            await sensor_setup(mock_hass, mock_config_entry, mock_async_add_entities)
            
            # Should not create any outlier-related sensors
            # (Other sensors may still be created)
            for call in mock_async_add_entities.call_args_list:
                entities = call[0][0] if call[0] else []
                outlier_entities = [e for e in entities if 'outlier' in type(e).__name__.lower()]
                assert len(outlier_entities) == 0


class TestSensorsReflectCoordinatorOutlierData:
    """Test sensors reflect coordinator outlier data changes."""
    
    def test_outlier_detection_sensor_reflects_coordinator_data(self, mock_coordinator):
        """Test OutlierDetectionSensor reflects coordinator outlier data."""
        from custom_components.smart_climate.binary_sensor import OutlierDetectionSensor
        
        entity_id = "climate.test_ac"
        sensor = OutlierDetectionSensor(mock_coordinator, entity_id)
        
        # Initially no outliers
        assert sensor.is_on is False
        
        # Update coordinator data to show outliers
        mock_coordinator.data.outliers["climate.test_ac"] = True
        mock_coordinator.data.outlier_count = 1
        
        # Sensor should reflect the change
        assert sensor.is_on is True
        
        # Verify attributes update
        attributes = sensor.extra_state_attributes
        assert attributes["outlier_count"] == 1
        assert attributes["detection_enabled"] is True
    
    def test_outlier_count_sensor_reflects_coordinator_data(self, mock_coordinator, mock_config_entry):
        """Test OutlierCountSensor reflects coordinator outlier statistics."""
        from custom_components.smart_climate.sensor import OutlierCountSensor
        
        sensor = OutlierCountSensor(mock_coordinator, "climate.test_ac", mock_config_entry)
        
        # Initially 0 outliers
        assert sensor.native_value == 0
        
        # Update coordinator data
        mock_coordinator.data.outlier_count = 3
        mock_coordinator.data.outlier_statistics.update({
            "total_samples": 15,
            "outlier_rate": 0.2,
            "temperature_outliers": 2,
            "power_outliers": 1,
        })
        
        # Sensor should reflect changes
        assert sensor.native_value == 3
        
        attributes = sensor.extra_state_attributes
        assert attributes["total_sensors"] == 15
        assert attributes["outlier_rate"] == 0.2
    
    def test_sensors_update_dynamically_with_coordinator_changes(self, mock_coordinator, mock_config_entry):
        """Test sensors update dynamically when coordinator data changes."""
        from custom_components.smart_climate.binary_sensor import OutlierDetectionSensor
        from custom_components.smart_climate.sensor import OutlierCountSensor
        
        # Create both sensor types
        binary_sensor = OutlierDetectionSensor(mock_coordinator, "climate.test_ac")
        count_sensor = OutlierCountSensor(mock_coordinator, "climate.test_ac", mock_config_entry)
        
        # Test multiple data updates
        test_scenarios = [
            {"outliers": {"climate.test_ac": True}, "count": 1, "rate": 0.1},
            {"outliers": {"climate.test_ac": False}, "count": 0, "rate": 0.0},
            {"outliers": {"climate.test_ac": True}, "count": 2, "rate": 0.15},
        ]
        
        for scenario in test_scenarios:
            # Update coordinator data
            mock_coordinator.data.outliers.update(scenario["outliers"])
            mock_coordinator.data.outlier_count = scenario["count"]
            mock_coordinator.data.outlier_statistics["outlier_rate"] = scenario["rate"]
            
            # Verify sensors reflect changes
            assert binary_sensor.is_on == scenario["outliers"]["climate.test_ac"]
            assert count_sensor.native_value == scenario["count"]
            assert count_sensor.extra_state_attributes["outlier_rate"] == scenario["rate"]


class TestSensorAvailabilityMatchesCoordinator:
    """Test sensor availability matches coordinator status."""
    
    def test_sensors_available_when_coordinator_successful(self, mock_coordinator, mock_config_entry):
        """Test sensors are available when coordinator is successful."""
        from custom_components.smart_climate.binary_sensor import OutlierDetectionSensor
        from custom_components.smart_climate.sensor import OutlierCountSensor
        
        # Coordinator successful with data
        mock_coordinator.last_update_success = True
        
        binary_sensor = OutlierDetectionSensor(mock_coordinator, "climate.test_ac")
        count_sensor = OutlierCountSensor(mock_coordinator, "climate.test_ac", mock_config_entry)
        
        # Both sensors should be available
        assert binary_sensor.available is True
        assert count_sensor.available is True
    
    def test_sensors_unavailable_when_coordinator_failed(self, mock_coordinator, mock_config_entry):
        """Test sensors are unavailable when coordinator update failed."""
        from custom_components.smart_climate.binary_sensor import OutlierDetectionSensor
        from custom_components.smart_climate.sensor import OutlierCountSensor
        
        # Coordinator failed
        mock_coordinator.last_update_success = False
        
        binary_sensor = OutlierDetectionSensor(mock_coordinator, "climate.test_ac")
        count_sensor = OutlierCountSensor(mock_coordinator, "climate.test_ac", mock_config_entry)
        
        # Both sensors should be unavailable
        assert binary_sensor.available is False
        assert count_sensor.available is False
    
    def test_sensor_availability_changes_dynamically(self, mock_coordinator, mock_config_entry):
        """Test sensor availability changes dynamically with coordinator status."""
        from custom_components.smart_climate.binary_sensor import OutlierDetectionSensor
        
        sensor = OutlierDetectionSensor(mock_coordinator, "climate.test_ac")
        
        # Initially available
        mock_coordinator.last_update_success = True
        assert sensor.available is True
        
        # Becomes unavailable
        mock_coordinator.last_update_success = False
        assert sensor.available is False
        
        # Becomes available again
        mock_coordinator.last_update_success = True
        assert sensor.available is True


class TestDashboardSensorsWithMultipleClimateEntities:
    """Test dashboard sensors with multiple climate entities."""
    
    @pytest.mark.asyncio
    async def test_sensors_created_for_multiple_climate_entities(
        self, mock_hass, mock_config_entry, mock_async_add_entities
    ):
        """Test sensors are created for multiple climate entities."""
        # Create multiple coordinators
        coordinator1 = Mock()
        coordinator1.last_update_success = True
        coordinator1.data = SmartClimateData(
            room_temp=22.0, outdoor_temp=28.0, power=1200.0, calculated_offset=1.5,
            mode_adjustments=ModeAdjustments(None, 0.0, None, 0.0),
            outliers={"climate.ac1": False}, outlier_count=0,
            outlier_statistics={"enabled": True, "total_samples": 10, "outlier_rate": 0.0}
        )
        coordinator1.outlier_detection_enabled = True
        
        coordinator2 = Mock()
        coordinator2.last_update_success = True
        coordinator2.data = SmartClimateData(
            room_temp=24.0, outdoor_temp=30.0, power=1500.0, calculated_offset=2.0,
            mode_adjustments=ModeAdjustments(None, 0.0, None, 0.0),
            outliers={"climate.ac2": True}, outlier_count=1,
            outlier_statistics={"enabled": True, "total_samples": 8, "outlier_rate": 0.125}
        )
        coordinator2.outlier_detection_enabled = True
        
        # Setup hass data with multiple coordinators
        mock_hass.data[DOMAIN] = {
            mock_config_entry.entry_id: {
                "coordinators": {
                    "climate.ac1": coordinator1,
                    "climate.ac2": coordinator2,
                }
            }
        }
        
        with patch("custom_components.smart_climate.binary_sensor.async_setup_entry") as mock_binary_setup:
            from custom_components.smart_climate.binary_sensor import async_setup_entry as binary_setup
            
            await binary_setup(mock_hass, mock_config_entry, mock_async_add_entities)
            
            # Should create sensors for both climate entities
            created_entities = mock_async_add_entities.call_args[0][0]
            
            # Should have OutlierDetectionSensor for each climate entity
            entity_ids = [getattr(entity, '_entity_id', None) for entity in created_entities]
            assert "climate.ac1" in entity_ids
            assert "climate.ac2" in entity_ids
    
    def test_sensors_maintain_separate_state_for_multiple_entities(self):
        """Test sensors maintain separate state for different climate entities."""
        from custom_components.smart_climate.binary_sensor import OutlierDetectionSensor
        
        # Create shared coordinator with data for multiple entities
        coordinator = Mock()
        coordinator.last_update_success = True
        coordinator.data = Mock()
        coordinator.data.outliers = {
            "climate.ac1": False,
            "climate.ac2": True,
            "climate.ac3": False,
        }
        coordinator.data.outlier_count = 1
        
        # Create sensors for different entities
        sensor1 = OutlierDetectionSensor(coordinator, "climate.ac1")
        sensor2 = OutlierDetectionSensor(coordinator, "climate.ac2")
        sensor3 = OutlierDetectionSensor(coordinator, "climate.ac3")
        
        # Each sensor should reflect its specific entity state
        assert sensor1.is_on is False  # No outliers
        assert sensor2.is_on is True   # Has outliers
        assert sensor3.is_on is False  # No outliers
        
        # All should share the same outlier count in attributes
        for sensor in [sensor1, sensor2, sensor3]:
            assert sensor.extra_state_attributes["outlier_count"] == 1


class TestSensorStatePersistenceAcrossRestarts:
    """Test sensor state persistence across restarts."""
    
    def test_sensors_restore_state_after_coordinator_restart(self, mock_config_entry):
        """Test sensors restore state when coordinator data is restored."""
        from custom_components.smart_climate.binary_sensor import OutlierDetectionSensor
        from custom_components.smart_climate.sensor import OutlierCountSensor
        
        # Create initial coordinator with data
        initial_coordinator = Mock()
        initial_coordinator.last_update_success = True
        initial_coordinator.data = Mock()
        initial_coordinator.data.outliers = {"climate.test_ac": True}
        initial_coordinator.data.outlier_count = 2
        initial_coordinator.data.outlier_statistics = {"outlier_rate": 0.2, "total_samples": 10}
        
        # Create sensors
        binary_sensor = OutlierDetectionSensor(initial_coordinator, "climate.test_ac")
        count_sensor = OutlierCountSensor(initial_coordinator, "climate.test_ac", mock_config_entry)
        
        # Verify initial state
        assert binary_sensor.is_on is True
        assert count_sensor.native_value == 2
        
        # Simulate restart - coordinator loses data temporarily
        initial_coordinator.last_update_success = False
        initial_coordinator.data = None
        
        # Sensors should become unavailable
        assert binary_sensor.available is False
        assert count_sensor.available is False
        
        # Simulate coordinator data restoration
        restored_data = Mock()
        restored_data.outliers = {"climate.test_ac": True}
        restored_data.outlier_count = 2
        restored_data.outlier_statistics = {"outlier_rate": 0.2, "total_samples": 10}
        
        initial_coordinator.last_update_success = True
        initial_coordinator.data = restored_data
        
        # Sensors should restore their state
        assert binary_sensor.available is True
        assert binary_sensor.is_on is True
        assert count_sensor.available is True
        assert count_sensor.native_value == 2
    
    def test_sensors_handle_coordinator_data_evolution(self, mock_config_entry):
        """Test sensors handle coordinator data structure evolution."""
        from custom_components.smart_climate.sensor import OutlierCountSensor
        
        coordinator = Mock()
        coordinator.last_update_success = True
        
        # Initial data structure
        coordinator.data = Mock()
        coordinator.data.outlier_count = 1
        coordinator.data.outlier_statistics = {"total_samples": 5, "outlier_rate": 0.2}
        
        sensor = OutlierCountSensor(coordinator, "climate.test_ac", mock_config_entry)
        
        # Verify initial state
        assert sensor.native_value == 1
        assert sensor.extra_state_attributes["total_sensors"] == 5
        
        # Simulate data evolution with additional fields
        coordinator.data.outlier_statistics.update({
            "temperature_outliers": 1,
            "power_outliers": 0,
            "history_size": 25,
            "detection_threshold": 2.5,
        })
        
        # Sensor should handle new fields gracefully
        attributes = sensor.extra_state_attributes
        assert attributes["total_sensors"] == 5  # Still works
        assert attributes["outlier_rate"] == 0.2  # Still works


class TestSensorDeviceInfoLinking:
    """Test sensors properly link to climate entity devices."""
    
    def test_sensors_have_proper_device_info(self, mock_coordinator, mock_config_entry):
        """Test sensors have proper device info for UI grouping."""
        from custom_components.smart_climate.binary_sensor import OutlierDetectionSensor
        from custom_components.smart_climate.sensor import OutlierCountSensor
        
        entity_id = "climate.test_ac"
        
        binary_sensor = OutlierDetectionSensor(mock_coordinator, entity_id)
        count_sensor = OutlierCountSensor(mock_coordinator, entity_id, mock_config_entry)
        
        # Both sensors should have device info
        assert hasattr(binary_sensor, 'device_info')
        assert hasattr(count_sensor, 'device_info')
        
        # Device info should link to parent climate entity
        binary_device_info = binary_sensor.device_info
        count_device_info = count_sensor.device_info
        
        # Should have consistent identifiers
        expected_identifier = (DOMAIN, f"{mock_config_entry.unique_id}_{entity_id.replace('.', '_')}")
        
        assert binary_device_info["identifiers"] == {expected_identifier}
        assert count_device_info["identifiers"] == {expected_identifier}
        
        # Should have meaningful names
        assert "Smart Climate" in binary_device_info["name"]
        assert "Smart Climate" in count_device_info["name"]
    
    def test_sensors_have_correct_unique_ids(self, mock_coordinator, mock_config_entry):
        """Test sensors have correct unique IDs for entity registry."""
        from custom_components.smart_climate.binary_sensor import OutlierDetectionSensor
        from custom_components.smart_climate.sensor import OutlierCountSensor
        
        entity_id = "climate.test_ac"
        
        binary_sensor = OutlierDetectionSensor(mock_coordinator, entity_id)
        count_sensor = OutlierCountSensor(mock_coordinator, entity_id, mock_config_entry)
        
        # Unique IDs should follow expected pattern
        expected_binary_id = f"{mock_config_entry.unique_id}_{entity_id.replace('.', '_')}_outlier_detection"
        expected_count_id = f"{mock_config_entry.unique_id}_{entity_id.replace('.', '_')}_outlier_count"
        
        assert binary_sensor.unique_id == expected_binary_id
        assert count_sensor.unique_id == expected_count_id
    
    def test_sensors_have_proper_entity_categories(self, mock_coordinator, mock_config_entry):
        """Test sensors have proper entity categories for UI organization."""
        from custom_components.smart_climate.binary_sensor import OutlierDetectionSensor
        from custom_components.smart_climate.sensor import OutlierCountSensor
        
        entity_id = "climate.test_ac"
        
        binary_sensor = OutlierDetectionSensor(mock_coordinator, entity_id)
        count_sensor = OutlierCountSensor(mock_coordinator, entity_id, mock_config_entry)
        
        # OutlierDetectionSensor should be diagnostic
        assert binary_sensor._attr_device_class == BinarySensorDeviceClass.PROBLEM
        
        # OutlierCountSensor should be diagnostic
        assert count_sensor.entity_category == EntityCategory.DIAGNOSTIC
        assert count_sensor.state_class == SensorStateClass.MEASUREMENT


class TestDashboardSensorDiscovery:
    """Test sensors are discoverable in Home Assistant UI."""
    
    @pytest.mark.asyncio
    async def test_sensors_discoverable_through_entity_registry(
        self, mock_hass, mock_config_entry, mock_entity_registry, mock_async_add_entities
    ):
        """Test sensors are discoverable through entity registry."""
        # Setup entity registry mock
        with patch("homeassistant.helpers.entity_registry.async_get", return_value=mock_entity_registry):
            
            # Setup coordinator
            coordinator = Mock()
            coordinator.last_update_success = True
            coordinator.outlier_detection_enabled = True
            coordinator.data = SmartClimateData(
                room_temp=22.0, outdoor_temp=28.0, power=1200.0, calculated_offset=1.5,
                mode_adjustments=ModeAdjustments(None, 0.0, None, 0.0),
                outliers={"climate.test_ac": False}, outlier_count=0,
                outlier_statistics={"enabled": True, "total_samples": 10, "outlier_rate": 0.0}
            )
            
            mock_hass.data[DOMAIN] = {
                mock_config_entry.entry_id: {
                    "coordinators": {"climate.test_ac": coordinator}
                }
            }
            
            from custom_components.smart_climate.binary_sensor import async_setup_entry
            
            await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
            
            # Verify entities were created
            created_entities = mock_async_add_entities.call_args[0][0]
            assert len(created_entities) > 0
            
            # Verify entities have discoverable properties
            for entity in created_entities:
                assert hasattr(entity, 'unique_id')
                assert hasattr(entity, 'name') 
                assert hasattr(entity, 'device_info')
                assert entity.unique_id is not None
                assert entity.name is not None
    
    def test_sensors_have_meaningful_names_and_icons(self, mock_coordinator, mock_config_entry):
        """Test sensors have meaningful names and icons for UI display."""
        from custom_components.smart_climate.binary_sensor import OutlierDetectionSensor
        from custom_components.smart_climate.sensor import OutlierCountSensor
        
        entity_id = "climate.test_ac"
        
        binary_sensor = OutlierDetectionSensor(mock_coordinator, entity_id)
        count_sensor = OutlierCountSensor(mock_coordinator, entity_id, mock_config_entry)
        
        # Names should be meaningful
        assert binary_sensor.name == "Outlier Detection"
        assert count_sensor.name == "Outlier Count"
        
        # Icons should be appropriate
        assert binary_sensor.icon == "mdi:alert-circle-outline"
        assert count_sensor.icon == "mdi:alert-circle-check-outline"
    
    def test_sensors_have_proper_state_classes_and_attributes(self, mock_coordinator, mock_config_entry):
        """Test sensors have proper state classes and attributes for UI functionality."""
        from custom_components.smart_climate.binary_sensor import OutlierDetectionSensor
        from custom_components.smart_climate.sensor import OutlierCountSensor
        
        entity_id = "climate.test_ac"
        
        binary_sensor = OutlierDetectionSensor(mock_coordinator, entity_id)
        count_sensor = OutlierCountSensor(mock_coordinator, entity_id, mock_config_entry)
        
        # Binary sensor should provide state and attributes
        assert hasattr(binary_sensor, 'is_on')
        assert hasattr(binary_sensor, 'extra_state_attributes')
        
        # Count sensor should have measurement state class
        assert count_sensor.state_class == SensorStateClass.MEASUREMENT
        assert hasattr(count_sensor, 'native_value')
        assert hasattr(count_sensor, 'extra_state_attributes')
        
        # Attributes should contain useful information
        binary_attrs = binary_sensor.extra_state_attributes
        count_attrs = count_sensor.extra_state_attributes
        
        assert "outlier_count" in binary_attrs
        assert "detection_enabled" in binary_attrs
        assert "total_sensors" in count_attrs
        assert "outlier_rate" in count_attrs
    
    @pytest.mark.asyncio
    async def test_sensors_integration_with_ui_discovery_flow(
        self, mock_hass, mock_config_entry, mock_async_add_entities
    ):
        """Test sensors integrate properly with UI discovery flow."""
        # Create coordinator with realistic data
        coordinator = Mock()
        coordinator.last_update_success = True
        coordinator.outlier_detection_enabled = True
        coordinator.data = SmartClimateData(
            room_temp=22.5, outdoor_temp=29.0, power=1350.0, calculated_offset=1.8,
            mode_adjustments=ModeAdjustments(None, 0.0, None, 0.0),
            outliers={"climate.test_ac": True}, outlier_count=1,
            outlier_statistics={
                "enabled": True, "temperature_outliers": 1, "power_outliers": 0,
                "total_samples": 12, "outlier_rate": 0.083, "history_size": 30,
                "has_sufficient_data": True
            }
        )
        
        mock_hass.data[DOMAIN] = {
            mock_config_entry.entry_id: {
                "coordinators": {"climate.test_ac": coordinator}
            }
        }
        
        # Setup both platforms
        from custom_components.smart_climate.binary_sensor import async_setup_entry as binary_setup
        from custom_components.smart_climate.sensor import async_setup_entry as sensor_setup
        
        await binary_setup(mock_hass, mock_config_entry, mock_async_add_entities)
        await sensor_setup(mock_hass, mock_config_entry, mock_async_add_entities)
        
        # Collect all created entities
        all_entities = []
        for call in mock_async_add_entities.call_args_list:
            entities = call[0][0] if call[0] else []
            all_entities.extend(entities)
        
        # Verify comprehensive UI integration
        for entity in all_entities:
            if 'outlier' in type(entity).__name__.lower():
                # Should have all required properties for UI discovery
                assert entity.unique_id is not None
                assert entity.name is not None
                assert entity.device_info is not None
                assert entity.available is True
                
                # Should have proper entity category for organization
                assert hasattr(entity, 'entity_category') or hasattr(entity, '_attr_entity_category')
                
                # Should provide meaningful state and attributes
                if hasattr(entity, 'is_on'):
                    assert isinstance(entity.is_on, bool)
                if hasattr(entity, 'native_value'):
                    assert entity.native_value is not None
                    
                # Should have extra attributes for debugging/monitoring
                attrs = entity.extra_state_attributes
                assert isinstance(attrs, dict)
                assert len(attrs) > 0


class TestSensorErrorHandlingAndEdgeCases:
    """Test sensor error handling and edge cases."""
    
    def test_sensors_handle_missing_coordinator_data_gracefully(self, mock_config_entry):
        """Test sensors handle missing coordinator data gracefully."""
        from custom_components.smart_climate.binary_sensor import OutlierDetectionSensor
        from custom_components.smart_climate.sensor import OutlierCountSensor
        
        # Coordinator with no data
        coordinator = Mock()
        coordinator.last_update_success = True
        coordinator.data = None
        
        binary_sensor = OutlierDetectionSensor(coordinator, "climate.test_ac")
        count_sensor = OutlierCountSensor(coordinator, "climate.test_ac", mock_config_entry)
        
        # Should handle gracefully without crashing
        assert binary_sensor.is_on is False  # Default to False
        assert count_sensor.native_value == 0  # Default to 0
        
        # Attributes should be safe defaults
        binary_attrs = binary_sensor.extra_state_attributes
        count_attrs = count_sensor.extra_state_attributes
        
        assert isinstance(binary_attrs, dict)
        assert isinstance(count_attrs, dict)
    
    def test_sensors_handle_coordinator_exceptions_gracefully(self, mock_config_entry):
        """Test sensors handle coordinator exceptions gracefully."""
        from custom_components.smart_climate.binary_sensor import OutlierDetectionSensor
        
        # Coordinator that raises exceptions
        coordinator = Mock()
        coordinator.last_update_success = True
        coordinator.data = Mock()
        coordinator.data.outliers = {"climate.test_ac": True}
        
        # Make outliers property raise exception
        type(coordinator.data).outliers = property(lambda self: (_ for _ in ()).throw(AttributeError("Test error")))
        
        sensor = OutlierDetectionSensor(coordinator, "climate.test_ac")
        
        # Should handle exception gracefully
        assert sensor.is_on is False  # Safe fallback
        
        # Should still provide attributes
        attrs = sensor.extra_state_attributes
        assert isinstance(attrs, dict)