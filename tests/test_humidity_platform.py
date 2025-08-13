"""ABOUTME: Tests for humidity platform integration in sensor.py.
Verifies humidity sensors are created when configured and proper HumidityMonitor integration."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.smart_climate.sensor import async_setup_entry
from custom_components.smart_climate.humidity_sensors import (
    IndoorHumiditySensor,
    OutdoorHumiditySensor,
    HumidityDifferentialSensor,
    HeatIndexSensor,
    IndoorDewPointSensor,
    OutdoorDewPointSensor,
    AbsoluteHumiditySensor,
    MLHumidityOffsetSensor,
    MLHumidityConfidenceSensor,
    MLHumidityWeightSensor,
    HumiditySensorStatusSensor,
    HumidityComfortLevelSensor,
)


@pytest.fixture
def mock_hass():
    """Create mock Home Assistant instance."""
    hass = Mock()
    hass.data = {}
    return hass


@pytest.fixture
def mock_config_entry():
    """Create mock config entry."""
    entry = Mock()
    entry.entry_id = "test_entry"
    entry.options = {}
    return entry


@pytest.fixture
def mock_coordinator():
    """Create mock coordinator with humidity monitoring."""
    coordinator = Mock()
    
    # Mock the humidity monitor (from H1-H3)
    humidity_monitor = Mock()
    coordinator.smart_climate = Mock()
    coordinator.smart_climate.humidity_monitor = humidity_monitor
    
    return coordinator


@pytest.fixture
def mock_coordinator_no_humidity():
    """Create mock coordinator without humidity monitoring."""
    coordinator = Mock()
    coordinator.smart_climate = Mock()
    coordinator.smart_climate.humidity_monitor = None
    return coordinator


class TestHumidityPlatformIntegration:
    """Test humidity sensor platform integration."""
    
    @pytest.mark.asyncio
    async def test_humidity_sensors_created_when_configured(
        self, mock_hass, mock_config_entry, mock_coordinator
    ):
        """Test that humidity sensors are created when humidity sensors are configured."""
        # Arrange
        mock_config_entry.options = {"humidity_sensors_enabled": True}
        mock_hass.data = {
            "smart_climate": {
                "test_entry": {
                    "coordinators": {"climate.test": mock_coordinator}
                }
            }
        }
        
        mock_add_entities = Mock()
        
        # Act
        await async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)
        
        # Assert
        mock_add_entities.assert_called_once()
        created_sensors = mock_add_entities.call_args[0][0]
        
        # Find humidity sensors in the created sensors list
        humidity_sensor_types = {
            IndoorHumiditySensor,
            OutdoorHumiditySensor,
            HumidityDifferentialSensor,
            HeatIndexSensor,
            IndoorDewPointSensor,
            OutdoorDewPointSensor,
            AbsoluteHumiditySensor,
            MLHumidityOffsetSensor,
            MLHumidityConfidenceSensor,
            MLHumidityWeightSensor,
            HumiditySensorStatusSensor,
            HumidityComfortLevelSensor,
        }
        
        found_humidity_sensors = [
            sensor for sensor in created_sensors 
            if type(sensor) in humidity_sensor_types
        ]
        
        # Should find all 12 humidity sensor types
        assert len(found_humidity_sensors) == 12
        
        # Verify each sensor type is present
        found_types = {type(sensor) for sensor in found_humidity_sensors}
        assert found_types == humidity_sensor_types
        
        # Verify each humidity sensor was passed the HumidityMonitor instance
        for sensor in found_humidity_sensors:
            assert hasattr(sensor, '_monitor')
            assert sensor._monitor == mock_coordinator.smart_climate.humidity_monitor
    
    @pytest.mark.asyncio
    async def test_no_humidity_sensors_when_not_configured(
        self, mock_hass, mock_config_entry, mock_coordinator
    ):
        """Test that no humidity sensors are created when not configured."""
        # Arrange - humidity_sensors_enabled not set (defaults to False)
        mock_config_entry.options = {}
        mock_hass.data = {
            "smart_climate": {
                "test_entry": {
                    "coordinators": {"climate.test": mock_coordinator}
                }
            }
        }
        
        mock_add_entities = Mock()
        
        # Act
        await async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)
        
        # Assert
        mock_add_entities.assert_called_once()
        created_sensors = mock_add_entities.call_args[0][0]
        
        # Find humidity sensors in the created sensors list
        humidity_sensor_types = {
            IndoorHumiditySensor,
            OutdoorHumiditySensor,
            HumidityDifferentialSensor,
            HeatIndexSensor,
            IndoorDewPointSensor,
            OutdoorDewPointSensor,
            AbsoluteHumiditySensor,
            MLHumidityOffsetSensor,
            MLHumidityConfidenceSensor,
            MLHumidityWeightSensor,
            HumiditySensorStatusSensor,
            HumidityComfortLevelSensor,
        }
        
        found_humidity_sensors = [
            sensor for sensor in created_sensors 
            if type(sensor) in humidity_sensor_types
        ]
        
        # Should find no humidity sensors
        assert len(found_humidity_sensors) == 0
    
    @pytest.mark.asyncio
    async def test_no_humidity_sensors_when_monitor_unavailable(
        self, mock_hass, mock_config_entry, mock_coordinator_no_humidity
    ):
        """Test that no humidity sensors are created when HumidityMonitor is unavailable."""
        # Arrange
        mock_config_entry.options = {"humidity_sensors_enabled": True}
        mock_hass.data = {
            "smart_climate": {
                "test_entry": {
                    "coordinators": {"climate.test": mock_coordinator_no_humidity}
                }
            }
        }
        
        mock_add_entities = Mock()
        
        # Act
        await async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)
        
        # Assert
        mock_add_entities.assert_called_once()
        created_sensors = mock_add_entities.call_args[0][0]
        
        # Find humidity sensors in the created sensors list
        humidity_sensor_types = {
            IndoorHumiditySensor,
            OutdoorHumiditySensor,
            HumidityDifferentialSensor,
            HeatIndexSensor,
            IndoorDewPointSensor,
            OutdoorDewPointSensor,
            AbsoluteHumiditySensor,
            MLHumidityOffsetSensor,
            MLHumidityConfidenceSensor,
            MLHumidityWeightSensor,
            HumiditySensorStatusSensor,
            HumidityComfortLevelSensor,
        }
        
        found_humidity_sensors = [
            sensor for sensor in created_sensors 
            if type(sensor) in humidity_sensor_types
        ]
        
        # Should find no humidity sensors when monitor is unavailable
        assert len(found_humidity_sensors) == 0
    
    @pytest.mark.asyncio
    async def test_existing_sensors_still_created_with_humidity(
        self, mock_hass, mock_config_entry, mock_coordinator
    ):
        """Test that existing sensors are still created when humidity sensors are added."""
        # Arrange
        mock_config_entry.options = {"humidity_sensors_enabled": True}
        mock_hass.data = {
            "smart_climate": {
                "test_entry": {
                    "coordinators": {"climate.test": mock_coordinator}
                }
            }
        }
        
        mock_add_entities = Mock()
        
        # Act
        await async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)
        
        # Assert
        mock_add_entities.assert_called_once()
        created_sensors = mock_add_entities.call_args[0][0]
        
        # Should have many sensors (existing + 12 humidity sensors)
        # The exact number depends on what other sensors are configured
        # but should be > 12 (since existing sensors should still be there)
        assert len(created_sensors) > 12
        
        # Verify some key existing sensors are still present (these should always be there)
        from custom_components.smart_climate.sensor import (
            OffsetCurrentSensor,
            LearningProgressSensor,
            AccuracyCurrentSensor,
        )
        
        existing_sensor_types = {OffsetCurrentSensor, LearningProgressSensor, AccuracyCurrentSensor}
        found_existing_sensors = [
            sensor for sensor in created_sensors 
            if type(sensor) in existing_sensor_types
        ]
        
        # Should find the key existing sensors
        assert len(found_existing_sensors) >= 3
        
    @pytest.mark.asyncio
    async def test_humidity_sensors_multiple_entities(
        self, mock_hass, mock_config_entry, mock_coordinator
    ):
        """Test that humidity sensors are created for multiple climate entities."""
        # Arrange
        mock_config_entry.options = {"humidity_sensors_enabled": True}
        
        mock_coordinator_2 = Mock()
        humidity_monitor_2 = Mock()
        mock_coordinator_2.smart_climate = Mock()
        mock_coordinator_2.smart_climate.humidity_monitor = humidity_monitor_2
        
        mock_hass.data = {
            "smart_climate": {
                "test_entry": {
                    "coordinators": {
                        "climate.test1": mock_coordinator,
                        "climate.test2": mock_coordinator_2,
                    }
                }
            }
        }
        
        mock_add_entities = Mock()
        
        # Act
        await async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)
        
        # Assert
        mock_add_entities.assert_called_once()
        created_sensors = mock_add_entities.call_args[0][0]
        
        # Find humidity sensors in the created sensors list
        humidity_sensor_types = {
            IndoorHumiditySensor,
            OutdoorHumiditySensor,
            HumidityDifferentialSensor,
            HeatIndexSensor,
            IndoorDewPointSensor,
            OutdoorDewPointSensor,
            AbsoluteHumiditySensor,
            MLHumidityOffsetSensor,
            MLHumidityConfidenceSensor,
            MLHumidityWeightSensor,
            HumiditySensorStatusSensor,
            HumidityComfortLevelSensor,
        }
        
        found_humidity_sensors = [
            sensor for sensor in created_sensors 
            if type(sensor) in humidity_sensor_types
        ]
        
        # Should find 12 humidity sensors for each entity (24 total)
        assert len(found_humidity_sensors) == 24
    
    @pytest.mark.asyncio
    async def test_no_coordinators_handles_gracefully(
        self, mock_hass, mock_config_entry
    ):
        """Test that setup handles missing coordinators gracefully."""
        # Arrange
        mock_config_entry.options = {"humidity_sensors_enabled": True}
        mock_hass.data = {
            "smart_climate": {
                "test_entry": {
                    "coordinators": {}  # Empty coordinators
                }
            }
        }
        
        mock_add_entities = Mock()
        
        # Act
        await async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)
        
        # Assert - should not crash and should not call async_add_entities
        # (because the function returns early when no coordinators found)
        mock_add_entities.assert_not_called()