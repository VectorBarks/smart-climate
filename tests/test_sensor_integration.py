"""ABOUTME: Integration tests for the Smart Climate sensor platform.
Tests sensor platform setup, entity registration, state updates, and availability in realistic HA environment."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN

from custom_components.smart_climate.const import DOMAIN
from custom_components.smart_climate.sensor import (
    async_setup_entry,
    OffsetCurrentSensor,
    LearningProgressSensor,
    AccuracyCurrentSensor,
    CalibrationStatusSensor,
    HysteresisStateSensor,
)
from tests.fixtures.sensor_test_fixtures import (
    create_mock_offset_engine_with_coordinator,
    create_mock_offset_engine_without_coordinator,
    create_mock_offset_engine_coordinator_no_data,
    create_mock_config_entry,
    create_realistic_learning_info,
    create_sensor_test_data,
)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock(spec=HomeAssistant)
    hass.data = {}
    return hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    return create_mock_config_entry()


@pytest.fixture
def mock_offset_engine():
    """Create a mock offset engine with coordinator."""
    return create_mock_offset_engine_with_coordinator()


@pytest.fixture
def mock_hass_data(mock_hass, mock_config_entry, mock_offset_engine):
    """Set up hass.data with mock data."""
    mock_hass.data[DOMAIN] = {
        mock_config_entry.entry_id: {
            "offset_engines": {
                "climate.test_ac": mock_offset_engine
            }
        }
    }
    return mock_hass


@pytest.fixture
def mock_async_add_entities():
    """Create a mock async_add_entities callback."""
    return AsyncMock(spec=AddEntitiesCallback)


class TestSensorPlatformSetup:
    """Test sensor platform setup and entity creation."""
    
    async def test_sensor_platform_setup_creates_all_sensors(
        self, mock_hass_data, mock_config_entry, mock_async_add_entities
    ):
        """Test that sensor platform setup creates all expected sensors."""
        await async_setup_entry(mock_hass_data, mock_config_entry, mock_async_add_entities)
        
        # Verify async_add_entities was called
        mock_async_add_entities.assert_called_once()
        
        # Get the sensors that were created
        created_sensors = mock_async_add_entities.call_args[0][0]
        
        # Should create 5 sensors for the climate entity
        assert len(created_sensors) == 5
        
        # Check that all expected sensor types were created
        sensor_types = [sensor._sensor_type for sensor in created_sensors]
        expected_types = [
            "offset_current",
            "learning_progress",
            "accuracy_current",
            "calibration_status",
            "hysteresis_state"
        ]
        assert sorted(sensor_types) == sorted(expected_types)
        
        # Check that all sensors are proper instances
        sensor_classes = [type(sensor).__name__ for sensor in created_sensors]
        expected_classes = [
            "OffsetCurrentSensor",
            "LearningProgressSensor",
            "AccuracyCurrentSensor",
            "CalibrationStatusSensor",
            "HysteresisStateSensor"
        ]
        assert sorted(sensor_classes) == sorted(expected_classes)
    
    async def test_sensor_platform_setup_with_multiple_climate_entities(
        self, mock_hass, mock_config_entry, mock_async_add_entities
    ):
        """Test sensor platform setup with multiple climate entities."""
        # Create multiple offset engines
        offset_engine1 = create_mock_offset_engine_with_coordinator()
        offset_engine2 = create_mock_offset_engine_with_coordinator()
        
        mock_hass.data[DOMAIN] = {
            mock_config_entry.entry_id: {
                "offset_engines": {
                    "climate.test_ac_1": offset_engine1,
                    "climate.test_ac_2": offset_engine2
                }
            }
        }
        
        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        
        # Should create 5 sensors per climate entity = 10 total
        created_sensors = mock_async_add_entities.call_args[0][0]
        assert len(created_sensors) == 10
        
        # Check that sensors are created for both climate entities
        base_entity_ids = [sensor._base_entity_id for sensor in created_sensors]
        assert base_entity_ids.count("climate.test_ac_1") == 5
        assert base_entity_ids.count("climate.test_ac_2") == 5
    
    async def test_sensor_platform_setup_no_offset_engines(
        self, mock_hass, mock_config_entry, mock_async_add_entities, caplog
    ):
        """Test sensor platform setup when no offset engines found."""
        # Set up empty hass data
        mock_hass.data[DOMAIN] = {mock_config_entry.entry_id: {}}
        
        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        
        # Should not create any sensors
        mock_async_add_entities.assert_not_called()
        
        # Should log a warning
        assert "No offset engines found for sensor setup" in caplog.text
        assert mock_config_entry.entry_id in caplog.text
    
    async def test_sensor_platform_setup_missing_domain_data(
        self, mock_hass, mock_config_entry, mock_async_add_entities, caplog
    ):
        """Test sensor platform setup when domain data is missing."""
        # Don't set up any hass data
        mock_hass.data = {}
        
        # Should handle gracefully (KeyError might be raised)
        with pytest.raises(KeyError):
            await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        
        # Should not create any sensors
        mock_async_add_entities.assert_not_called()


class TestSensorEntityRegistration:
    """Test sensor entity registration in Home Assistant."""
    
    async def test_sensors_have_correct_unique_ids(
        self, mock_hass_data, mock_config_entry, mock_async_add_entities
    ):
        """Test that sensors have correct unique IDs for entity registry."""
        await async_setup_entry(mock_hass_data, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        
        # Check unique IDs follow the expected pattern
        for sensor in created_sensors:
            expected_unique_id = f"{mock_config_entry.unique_id}_climate_test_ac_{sensor._sensor_type}"
            assert sensor.unique_id == expected_unique_id
    
    async def test_sensors_have_correct_device_info(
        self, mock_hass_data, mock_config_entry, mock_async_add_entities
    ):
        """Test that sensors have correct device info for grouping."""
        await async_setup_entry(mock_hass_data, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        
        # Check device info is consistent across all sensors
        for sensor in created_sensors:
            assert sensor.device_info is not None
            assert sensor.device_info["identifiers"] == {(DOMAIN, "test_unique_id_climate_test_ac")}
            assert sensor.device_info["name"] == "Test Smart Climate (climate.test_ac)"
    
    async def test_sensors_have_entity_name_flag(
        self, mock_hass_data, mock_config_entry, mock_async_add_entities
    ):
        """Test that sensors have the entity name flag set."""
        await async_setup_entry(mock_hass_data, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        
        # All sensors should have entity name flag set
        for sensor in created_sensors:
            assert sensor._attr_has_entity_name is True


class TestSensorStateUpdates:
    """Test sensor state updates through coordinator."""
    
    async def test_offset_current_sensor_updates_with_coordinator(
        self, mock_hass_data, mock_config_entry, mock_async_add_entities
    ):
        """Test that offset current sensor updates when coordinator data changes."""
        await async_setup_entry(mock_hass_data, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        offset_sensor = next(s for s in created_sensors if isinstance(s, OffsetCurrentSensor))
        
        # Initial value
        assert offset_sensor.native_value == 1.5
        
        # Update coordinator data
        offset_sensor._offset_engine._coordinator.data.calculated_offset = 2.8
        
        # Sensor should reflect new value
        assert offset_sensor.native_value == 2.8
    
    async def test_learning_progress_sensor_updates_with_learning_info(
        self, mock_hass_data, mock_config_entry, mock_async_add_entities
    ):
        """Test that learning progress sensor updates when learning info changes."""
        await async_setup_entry(mock_hass_data, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        progress_sensor = next(s for s in created_sensors if isinstance(s, LearningProgressSensor))
        
        # Initial value (8 samples = 80% of 10 required)
        assert progress_sensor.native_value == 80
        
        # Update learning info
        progress_sensor._offset_engine.get_learning_info.return_value["samples"] = 12
        
        # Sensor should reflect new value (12 samples = 100% capped)
        assert progress_sensor.native_value == 100
    
    async def test_accuracy_current_sensor_updates_with_learning_info(
        self, mock_hass_data, mock_config_entry, mock_async_add_entities
    ):
        """Test that accuracy current sensor updates when learning info changes."""
        await async_setup_entry(mock_hass_data, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        accuracy_sensor = next(s for s in created_sensors if isinstance(s, AccuracyCurrentSensor))
        
        # Initial value (0.75 accuracy = 75%)
        assert accuracy_sensor.native_value == 75
        
        # Update learning info
        accuracy_sensor._offset_engine.get_learning_info.return_value["accuracy"] = 0.92
        
        # Sensor should reflect new value (0.92 accuracy = 92%)
        assert accuracy_sensor.native_value == 92
    
    async def test_calibration_status_sensor_updates_with_learning_info(
        self, mock_hass_data, mock_config_entry, mock_async_add_entities
    ):
        """Test that calibration status sensor updates when learning info changes."""
        await async_setup_entry(mock_hass_data, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        calibration_sensor = next(s for s in created_sensors if isinstance(s, CalibrationStatusSensor))
        
        # Initial value (8 samples = In Progress)
        assert calibration_sensor.native_value == "In Progress (8/10 samples)"
        
        # Update learning info to complete
        calibration_sensor._offset_engine.get_learning_info.return_value["samples"] = 15
        
        # Sensor should reflect new value
        assert calibration_sensor.native_value == "Complete"
    
    async def test_hysteresis_state_sensor_updates_with_learning_info(
        self, mock_hass_data, mock_config_entry, mock_async_add_entities
    ):
        """Test that hysteresis state sensor updates when learning info changes."""
        await async_setup_entry(mock_hass_data, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        hysteresis_sensor = next(s for s in created_sensors if isinstance(s, HysteresisStateSensor))
        
        # Initial value (learning_hysteresis state)
        assert hysteresis_sensor.native_value == "Learning AC behavior"
        
        # Update learning info to active phase
        hysteresis_sensor._offset_engine.get_learning_info.return_value["hysteresis_state"] = "active_phase"
        
        # Sensor should reflect new value
        assert hysteresis_sensor.native_value == "AC actively cooling"


class TestSensorAvailabilityInIntegration:
    """Test sensor availability in integration context."""
    
    async def test_sensors_available_when_coordinator_has_data(
        self, mock_hass_data, mock_config_entry, mock_async_add_entities
    ):
        """Test that sensors are available when coordinator has data."""
        await async_setup_entry(mock_hass_data, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        
        # All sensors should be available
        for sensor in created_sensors:
            assert sensor.available is True
    
    async def test_sensors_unavailable_when_coordinator_has_no_data(
        self, mock_hass, mock_config_entry, mock_async_add_entities
    ):
        """Test that sensors are unavailable when coordinator has no data."""
        # Create offset engine without coordinator data
        offset_engine = create_mock_offset_engine_coordinator_no_data()
        mock_hass.data[DOMAIN] = {
            mock_config_entry.entry_id: {
                "offset_engines": {
                    "climate.test_ac": offset_engine
                }
            }
        }
        
        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        
        # All sensors should be unavailable
        for sensor in created_sensors:
            assert sensor.available is False
    
    async def test_sensors_unavailable_when_no_coordinator(
        self, mock_hass, mock_config_entry, mock_async_add_entities
    ):
        """Test that sensors are unavailable when no coordinator exists."""
        # Create offset engine without coordinator
        offset_engine = create_mock_offset_engine_without_coordinator()
        mock_hass.data[DOMAIN] = {
            mock_config_entry.entry_id: {
                "offset_engines": {
                    "climate.test_ac": offset_engine
                }
            }
        }
        
        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        
        # All sensors should be unavailable
        for sensor in created_sensors:
            assert sensor.available is False
    
    async def test_sensor_availability_changes_dynamically(
        self, mock_hass_data, mock_config_entry, mock_async_add_entities
    ):
        """Test that sensor availability changes dynamically when coordinator changes."""
        await async_setup_entry(mock_hass_data, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        offset_sensor = next(s for s in created_sensors if isinstance(s, OffsetCurrentSensor))
        
        # Initially available
        assert offset_sensor.available is True
        assert offset_sensor.native_value == 1.5
        
        # Remove coordinator data
        offset_sensor._offset_engine._coordinator.data = None
        
        # Should become unavailable
        assert offset_sensor.available is False
        assert offset_sensor.native_value is None
        
        # Restore coordinator data
        offset_sensor._offset_engine._coordinator.data = Mock()
        offset_sensor._offset_engine._coordinator.data.calculated_offset = 3.2
        
        # Should become available again
        assert offset_sensor.available is True
        assert offset_sensor.native_value == 3.2


class TestSensorErrorHandling:
    """Test sensor error handling in integration context."""
    
    async def test_sensor_native_value_handles_missing_data_gracefully(
        self, mock_hass_data, mock_config_entry, mock_async_add_entities
    ):
        """Test that sensors handle missing data gracefully."""
        await async_setup_entry(mock_hass_data, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        offset_sensor = next(s for s in created_sensors if isinstance(s, OffsetCurrentSensor))
        
        # Make coordinator data access raise AttributeError
        offset_sensor._offset_engine._coordinator.data = Mock()
        del offset_sensor._offset_engine._coordinator.data.calculated_offset
        
        # Should handle gracefully and return None
        assert offset_sensor.native_value is None
        # But should still be available since coordinator exists
        assert offset_sensor.available is True
    
    async def test_sensor_get_learning_info_exception_handling(
        self, mock_hass_data, mock_config_entry, mock_async_add_entities
    ):
        """Test that sensors handle get_learning_info exceptions gracefully."""
        await async_setup_entry(mock_hass_data, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        
        # Make get_learning_info raise an exception
        for sensor in created_sensors:
            sensor._offset_engine.get_learning_info.side_effect = Exception("Test error")
        
        # Test each sensor type handles exceptions gracefully
        progress_sensor = next(s for s in created_sensors if isinstance(s, LearningProgressSensor))
        accuracy_sensor = next(s for s in created_sensors if isinstance(s, AccuracyCurrentSensor))
        calibration_sensor = next(s for s in created_sensors if isinstance(s, CalibrationStatusSensor))
        hysteresis_sensor = next(s for s in created_sensors if isinstance(s, HysteresisStateSensor))
        
        # All should handle exceptions gracefully
        assert progress_sensor.native_value == 0
        assert accuracy_sensor.native_value == 0
        assert calibration_sensor.native_value == "Unknown"
        assert hysteresis_sensor.native_value == "Unknown"
        
        # All should still be available
        assert progress_sensor.available is True
        assert accuracy_sensor.available is True
        assert calibration_sensor.available is True
        assert hysteresis_sensor.available is True
    
    async def test_sensor_extra_attributes_exception_handling(
        self, mock_hass_data, mock_config_entry, mock_async_add_entities
    ):
        """Test that sensor extra attributes handle exceptions gracefully."""
        await async_setup_entry(mock_hass_data, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        calibration_sensor = next(s for s in created_sensors if isinstance(s, CalibrationStatusSensor))
        hysteresis_sensor = next(s for s in created_sensors if isinstance(s, HysteresisStateSensor))
        
        # Make get_learning_info raise an exception
        calibration_sensor._offset_engine.get_learning_info.side_effect = Exception("Test error")
        hysteresis_sensor._offset_engine.get_learning_info.side_effect = Exception("Test error")
        
        # Should handle exceptions gracefully and return default attributes
        calibration_attrs = calibration_sensor.extra_state_attributes
        assert calibration_attrs["samples_collected"] == 0
        assert calibration_attrs["minimum_required"] == 10
        assert calibration_attrs["learning_enabled"] is False
        assert calibration_attrs["last_sample"] is None
        
        hysteresis_attrs = hysteresis_sensor.extra_state_attributes
        assert hysteresis_attrs["power_sensor_configured"] is False
        assert hysteresis_attrs["start_threshold"] == "Not available"
        assert hysteresis_attrs["stop_threshold"] == "Not available"
        assert hysteresis_attrs["temperature_window"] == "Not available"


class TestSensorIntegrationWithCoordinator:
    """Test sensor integration with coordinator updates."""
    
    async def test_multiple_sensors_share_coordinator(
        self, mock_hass_data, mock_config_entry, mock_async_add_entities
    ):
        """Test that multiple sensors share the same coordinator."""
        await async_setup_entry(mock_hass_data, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        
        # All sensors should share the same coordinator
        coordinators = [sensor._offset_engine._coordinator for sensor in created_sensors]
        assert all(coord is coordinators[0] for coord in coordinators)
    
    async def test_sensor_coordinator_data_consistency(
        self, mock_hass_data, mock_config_entry, mock_async_add_entities
    ):
        """Test that sensors maintain data consistency with coordinator."""
        await async_setup_entry(mock_hass_data, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        offset_sensor = next(s for s in created_sensors if isinstance(s, OffsetCurrentSensor))
        
        # Test multiple coordinator updates
        test_values = [1.0, 2.5, -1.2, 0.0, 4.8]
        
        for test_value in test_values:
            offset_sensor._offset_engine._coordinator.data.calculated_offset = test_value
            assert offset_sensor.native_value == test_value
    
    async def test_sensor_learning_info_consistency(
        self, mock_hass_data, mock_config_entry, mock_async_add_entities
    ):
        """Test that sensors maintain consistency with learning info updates."""
        await async_setup_entry(mock_hass_data, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        progress_sensor = next(s for s in created_sensors if isinstance(s, LearningProgressSensor))
        accuracy_sensor = next(s for s in created_sensors if isinstance(s, AccuracyCurrentSensor))
        calibration_sensor = next(s for s in created_sensors if isinstance(s, CalibrationStatusSensor))
        
        # Test different learning states
        test_scenarios = [
            {"samples": 0, "accuracy": 0.0, "enabled": False},
            {"samples": 5, "accuracy": 0.3, "enabled": True},
            {"samples": 10, "accuracy": 0.8, "enabled": True},
            {"samples": 15, "accuracy": 0.95, "enabled": True},
        ]
        
        for scenario in test_scenarios:
            # Update learning info
            new_info = create_realistic_learning_info(scenario["samples"], scenario["enabled"])
            new_info["accuracy"] = scenario["accuracy"]
            
            for sensor in created_sensors:
                sensor._offset_engine.get_learning_info.return_value = new_info
            
            # Check consistency
            expected_progress = min(100, int((scenario["samples"] / 10) * 100)) if scenario["enabled"] else 0
            expected_accuracy = int(scenario["accuracy"] * 100)
            
            if scenario["enabled"]:
                if scenario["samples"] >= 10:
                    expected_status = "Complete"
                else:
                    expected_status = f"In Progress ({scenario['samples']}/10 samples)"
            else:
                expected_status = "Waiting (Learning Disabled)"
            
            assert progress_sensor.native_value == expected_progress
            assert accuracy_sensor.native_value == expected_accuracy
            assert calibration_sensor.native_value == expected_status


class TestSensorPlatformScenarios:
    """Test realistic sensor platform scenarios."""
    
    async def test_sensor_platform_startup_with_delayed_coordinator(
        self, mock_hass, mock_config_entry, mock_async_add_entities
    ):
        """Test sensor platform startup when coordinator data is delayed."""
        # Create offset engine with coordinator but no data initially
        offset_engine = create_mock_offset_engine_coordinator_no_data()
        mock_hass.data[DOMAIN] = {
            mock_config_entry.entry_id: {
                "offset_engines": {
                    "climate.test_ac": offset_engine
                }
            }
        }
        
        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        offset_sensor = next(s for s in created_sensors if isinstance(s, OffsetCurrentSensor))
        
        # Initially unavailable (no coordinator data)
        assert offset_sensor.available is False
        assert offset_sensor.native_value is None
        
        # Simulate coordinator data becoming available
        offset_sensor._offset_engine._coordinator.data = Mock()
        offset_sensor._offset_engine._coordinator.data.calculated_offset = 2.1
        
        # Should become available
        assert offset_sensor.available is True
        assert offset_sensor.native_value == 2.1
    
    async def test_sensor_platform_with_learning_disabled(
        self, mock_hass, mock_config_entry, mock_async_add_entities
    ):
        """Test sensor platform behavior when learning is disabled."""
        # Create offset engine with learning disabled
        offset_engine = create_mock_offset_engine_with_coordinator()
        offset_engine.get_learning_info.return_value = create_realistic_learning_info(0, False)
        
        mock_hass.data[DOMAIN] = {
            mock_config_entry.entry_id: {
                "offset_engines": {
                    "climate.test_ac": offset_engine
                }
            }
        }
        
        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        progress_sensor = next(s for s in created_sensors if isinstance(s, LearningProgressSensor))
        accuracy_sensor = next(s for s in created_sensors if isinstance(s, AccuracyCurrentSensor))
        calibration_sensor = next(s for s in created_sensors if isinstance(s, CalibrationStatusSensor))
        
        # Check expected values when learning is disabled
        assert progress_sensor.native_value == 0
        assert accuracy_sensor.native_value == 0
        assert calibration_sensor.native_value == "Waiting (Learning Disabled)"
        
        # All should still be available
        assert progress_sensor.available is True
        assert accuracy_sensor.available is True
        assert calibration_sensor.available is True
    
    async def test_sensor_platform_complete_integration_scenario(
        self, mock_hass, mock_config_entry, mock_async_add_entities
    ):
        """Test complete integration scenario with realistic data flow."""
        # Create offset engine with complete learning data
        offset_engine = create_mock_offset_engine_with_coordinator()
        offset_engine.get_learning_info.return_value = create_realistic_learning_info(15, True)
        offset_engine._coordinator.data.calculated_offset = 1.8
        
        mock_hass.data[DOMAIN] = {
            mock_config_entry.entry_id: {
                "offset_engines": {
                    "climate.test_ac": offset_engine
                }
            }
        }
        
        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        
        # Verify all sensors are created and configured correctly
        assert len(created_sensors) == 5
        
        # Check each sensor type
        offset_sensor = next(s for s in created_sensors if isinstance(s, OffsetCurrentSensor))
        progress_sensor = next(s for s in created_sensors if isinstance(s, LearningProgressSensor))
        accuracy_sensor = next(s for s in created_sensors if isinstance(s, AccuracyCurrentSensor))
        calibration_sensor = next(s for s in created_sensors if isinstance(s, CalibrationStatusSensor))
        hysteresis_sensor = next(s for s in created_sensors if isinstance(s, HysteresisStateSensor))
        
        # Verify all sensors are available
        for sensor in created_sensors:
            assert sensor.available is True
        
        # Verify sensor values are correct
        assert offset_sensor.native_value == 1.8
        assert progress_sensor.native_value == 100  # 15 samples = 100%
        assert accuracy_sensor.native_value == 95   # 0.95 accuracy = 95%
        assert calibration_sensor.native_value == "Complete"
        assert hysteresis_sensor.native_value == "Temperature stable"  # idle_stable_zone
        
        # Verify sensor attributes
        assert offset_sensor.unique_id == "test_unique_id_climate_test_ac_offset_current"
        assert progress_sensor.unique_id == "test_unique_id_climate_test_ac_learning_progress"
        assert accuracy_sensor.unique_id == "test_unique_id_climate_test_ac_accuracy_current"
        assert calibration_sensor.unique_id == "test_unique_id_climate_test_ac_calibration_status"
        assert hysteresis_sensor.unique_id == "test_unique_id_climate_test_ac_hysteresis_state"
        
        # Verify device info consistency
        for sensor in created_sensors:
            assert sensor.device_info["identifiers"] == {(DOMAIN, "test_unique_id_climate_test_ac")}
            assert sensor.device_info["name"] == "Test Smart Climate (climate.test_ac)"