"""Test sensor platform setup for Smart Climate integration.

ABOUTME: Tests for sensor platform integration with outlier detection.
Tests platform setup functions, sensor creation, and configuration gating.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.smart_climate import binary_sensor, sensor
from custom_components.smart_climate.binary_sensor import OutlierDetectionSensor
from custom_components.smart_climate.sensor import OutlierCountSensor
from custom_components.smart_climate.const import DOMAIN


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.data = {DOMAIN: {}}
    return hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = Mock()
    entry.entry_id = "test_entry_id"
    entry.data = {
        "climate_entity": "climate.test",
        "room_sensor": "sensor.room_temp",
    }
    entry.options = {
        "outlier_detection_enabled": True,
        "outlier_sensitivity": 2.5,
    }
    return entry


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator with outlier detection data."""
    coordinator = Mock()
    coordinator.data = Mock()
    coordinator.data.outliers = {"climate.test": True}
    coordinator.data.outlier_count = 5
    coordinator.data.outlier_statistics = {
        "enabled": True,
        "outlier_rate": 0.15,
        "detected_outliers": 5,
        "filtered_samples": 100,
    }
    coordinator.last_update_success = True
    return coordinator


@pytest.fixture
def mock_add_entities():
    """Create a mock AddEntitiesCallback."""
    return Mock()


class TestBinarySensorPlatformSetup:
    """Test binary sensor platform setup integration."""

    @pytest.mark.asyncio
    async def test_binary_sensor_platform_setup(self, mock_hass, mock_config_entry, mock_add_entities):
        """Test binary_sensor.async_setup_entry creates OutlierDetectionSensor.
        
        This test verifies that the binary sensor platform setup function:
        1. Retrieves coordinators from hass.data
        2. Creates OutlierDetectionSensor for each climate entity
        3. Only creates sensors when outlier_detection_enabled=True
        4. Calls async_add_entities with created sensors
        """
        # Arrange
        mock_coordinator = Mock()
        mock_hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinators": {"climate.test": mock_coordinator}
        }

        # Act
        await binary_sensor.async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)

        # Assert
        mock_add_entities.assert_called_once()
        call_args = mock_add_entities.call_args[0][0]  # Get the first argument (sensors list)
        
        # Verify correct number and type of sensors created
        assert len(call_args) == 1
        assert isinstance(call_args[0], OutlierDetectionSensor)
        assert call_args[0]._entity_id == "climate.test"

    @pytest.mark.asyncio
    async def test_binary_sensor_setup_handles_missing_coordinators(self, mock_hass, mock_config_entry, mock_add_entities):
        """Test binary sensor setup handles missing coordinators gracefully."""
        # Arrange - no coordinators in hass.data
        mock_hass.data[DOMAIN][mock_config_entry.entry_id] = {}

        # Act
        await binary_sensor.async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)

        # Assert - no entities should be added
        mock_add_entities.assert_not_called()

    @pytest.mark.asyncio
    async def test_binary_sensor_setup_outlier_detection_disabled(self, mock_hass, mock_config_entry, mock_add_entities):
        """Test binary sensor setup when outlier detection is disabled."""
        # Arrange
        mock_config_entry.options = {"outlier_detection_enabled": False}
        mock_coordinator = Mock()
        mock_hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinators": {"climate.test": mock_coordinator}
        }

        # Act
        await binary_sensor.async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)

        # Assert - no entities should be added when disabled
        mock_add_entities.assert_not_called()


class TestSensorPlatformSetup:
    """Test sensor platform setup integration."""

    @pytest.mark.asyncio
    async def test_sensor_platform_setup(self, mock_hass, mock_config_entry, mock_add_entities):
        """Test sensor.async_setup_entry creates OutlierCountSensor.
        
        This test verifies that the sensor platform setup function:
        1. Retrieves coordinators from hass.data
        2. Creates OutlierCountSensor when outlier detection enabled
        3. Creates sensor alongside existing sensors
        4. Calls async_add_entities with all sensors
        """
        # Arrange
        mock_coordinator = Mock()
        mock_hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinators": {"climate.test": mock_coordinator}
        }

        # Act
        await sensor.async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)

        # Assert
        mock_add_entities.assert_called_once()
        call_args = mock_add_entities.call_args[0][0]  # Get the first argument (sensors list)
        
        # Verify OutlierCountSensor is included when outlier detection enabled
        outlier_count_sensors = [s for s in call_args if isinstance(s, OutlierCountSensor)]
        assert len(outlier_count_sensors) == 1
        assert outlier_count_sensors[0]._base_entity_id == "climate.test"

    @pytest.mark.asyncio
    async def test_sensor_setup_outlier_detection_disabled(self, mock_hass, mock_config_entry, mock_add_entities):
        """Test sensor setup when outlier detection is disabled."""
        # Arrange
        mock_config_entry.options = {"outlier_detection_enabled": False}
        mock_coordinator = Mock()
        mock_hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinators": {"climate.test": mock_coordinator}
        }

        # Act
        await sensor.async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)

        # Assert
        mock_add_entities.assert_called_once()
        call_args = mock_add_entities.call_args[0][0]  # Get the first argument (sensors list)
        
        # Verify OutlierCountSensor is NOT included when disabled
        outlier_count_sensors = [s for s in call_args if isinstance(s, OutlierCountSensor)]
        assert len(outlier_count_sensors) == 0


class TestPlatformIntegrationConstraints:
    """Test platform integration constraints and edge cases."""

    @pytest.mark.asyncio
    async def test_platforms_only_created_when_enabled(self, mock_hass, mock_config_entry, mock_add_entities):
        """Test sensors only created when outlier_detection_enabled=True.
        
        This test ensures that outlier detection sensors are conditionally created
        based on the configuration setting.
        """
        # Test enabled case
        mock_config_entry.options = {"outlier_detection_enabled": True}
        mock_coordinator = Mock()
        mock_hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinators": {"climate.test": mock_coordinator}
        }

        await binary_sensor.async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)
        assert mock_add_entities.call_count == 1

        # Reset mock
        mock_add_entities.reset_mock()

        # Test disabled case
        mock_config_entry.options = {"outlier_detection_enabled": False}
        await binary_sensor.async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)
        assert mock_add_entities.call_count == 0

    @pytest.mark.asyncio
    async def test_multiple_climate_entities_create_multiple_sensors(self, mock_hass, mock_config_entry, mock_add_entities):
        """Test sensor creation for multiple climate entities.
        
        This test verifies that the platform setup creates sensors for each
        climate entity when multiple entities are configured.
        """
        # Arrange - multiple climate entities
        mock_coordinator1 = Mock()
        mock_coordinator2 = Mock()
        mock_hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinators": {
                "climate.test1": mock_coordinator1,
                "climate.test2": mock_coordinator2,
            }
        }

        # Act
        await binary_sensor.async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)

        # Assert
        mock_add_entities.assert_called_once()
        call_args = mock_add_entities.call_args[0][0]
        
        # Verify sensors created for both entities
        assert len(call_args) == 2
        entity_ids = [sensor._entity_id for sensor in call_args]
        assert "climate.test1" in entity_ids
        assert "climate.test2" in entity_ids

    @pytest.mark.asyncio
    async def test_platform_setup_handles_coordinator_unavailable(self, mock_hass, mock_config_entry, mock_add_entities):
        """Test graceful handling of coordinator setup failures.
        
        This test ensures platform setup handles cases where coordinators
        might be unavailable or in an error state.
        """
        # Arrange - missing entry data
        mock_config_entry.entry_id = "missing_entry"

        # Act & Assert - should not raise exception
        await binary_sensor.async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)
        mock_add_entities.assert_not_called()

    @pytest.mark.asyncio
    async def test_sensor_platform_integration(self, mock_hass, mock_config_entry, mock_add_entities):
        """Test sensors properly integrate with Home Assistant platform.
        
        This test verifies that created sensors have proper integration with
        the Home Assistant platform architecture including device info,
        unique IDs, and coordinator integration.
        """
        # Arrange
        mock_coordinator = Mock()
        mock_hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinators": {"climate.test": mock_coordinator}
        }

        # Act
        await binary_sensor.async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)

        # Assert
        mock_add_entities.assert_called_once()
        sensor_entity = mock_add_entities.call_args[0][0][0]
        
        # Verify platform integration properties
        assert hasattr(sensor_entity, 'unique_id')
        assert hasattr(sensor_entity, 'coordinator')
        assert sensor_entity.coordinator == mock_coordinator
        assert sensor_entity._attr_unique_id == "climate.test_outlier_detection"


class TestSensorFunctionality:
    """Test sensor functionality and data access."""

    def test_outlier_detection_sensor_properties(self, mock_coordinator):
        """Test OutlierDetectionSensor properties and state."""
        # Arrange
        sensor_entity = OutlierDetectionSensor(mock_coordinator, "climate.test")

        # Act & Assert
        assert sensor_entity.unique_id == "climate.test_outlier_detection"
        assert sensor_entity.is_on is True  # Based on mock coordinator data
        
        # Test state attributes
        attributes = sensor_entity.extra_state_attributes
        assert attributes["outlier_count"] == 5
        assert attributes["outlier_rate"] == 0.15
        assert attributes["detection_enabled"] is True

    def test_outlier_count_sensor_properties(self, mock_coordinator):
        """Test OutlierCountSensor properties and state."""
        # Arrange
        mock_config_entry = Mock()
        sensor_entity = OutlierCountSensor(mock_coordinator, "climate.test", mock_config_entry)

        # Act & Assert
        assert sensor_entity.native_value == 5  # Based on mock coordinator data
        
        # Test handling of missing data
        mock_coordinator.data = None
        assert sensor_entity.native_value == 0