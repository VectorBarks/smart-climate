"""Tests for core humidity sensor entities (sensors 1-3).

Tests the base HumiditySensorEntity class and the first 3 sensor implementations:
- IndoorHumiditySensor
- OutdoorHumiditySensor  
- HumidityDifferentialSensor
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE

from custom_components.smart_climate.humidity_sensors import (
    HumiditySensorEntity,
    IndoorHumiditySensor,
    OutdoorHumiditySensor,
    HumidityDifferentialSensor,
)
from custom_components.smart_climate.humidity_monitor import HumidityMonitor


class TestHumiditySensorEntity:
    """Test suite for HumiditySensorEntity base class."""
    
    def test_base_class_attributes(self):
        """Test base class has correct attributes."""
        mock_monitor = Mock(spec=HumidityMonitor)
        sensor_type = "test_humidity"
        
        sensor = HumiditySensorEntity(mock_monitor, sensor_type)
        
        assert sensor._monitor == mock_monitor
        assert sensor._sensor_type == sensor_type
        # Base class should not set state_class by default
        assert not hasattr(sensor, '_attr_state_class')
        
    def test_name_property(self):
        """Test name property formats sensor type correctly."""
        mock_monitor = Mock(spec=HumidityMonitor)
        
        sensor = HumiditySensorEntity(mock_monitor, "indoor_humidity")
        assert sensor.name == "Smart Climate Indoor Humidity"
        
        sensor2 = HumiditySensorEntity(mock_monitor, "humidity_differential")
        assert sensor2.name == "Smart Climate Humidity Differential"
        
    def test_unique_id_property(self):
        """Test unique_id property formats correctly."""
        mock_monitor = Mock(spec=HumidityMonitor)
        
        sensor = HumiditySensorEntity(mock_monitor, "indoor_humidity")
        assert sensor.unique_id == "smart_climate_indoor_humidity"
        
        sensor2 = HumiditySensorEntity(mock_monitor, "humidity_differential")
        assert sensor2.unique_id == "smart_climate_humidity_differential"


class TestIndoorHumiditySensor:
    """Test suite for IndoorHumiditySensor."""
    
    def test_sensor_attributes(self):
        """Test IndoorHumiditySensor has correct attributes."""
        mock_monitor = Mock(spec=HumidityMonitor)
        
        sensor = IndoorHumiditySensor(mock_monitor)
        
        assert sensor._sensor_type == "indoor_humidity"
        assert sensor.name == "Smart Climate Indoor Humidity"
        assert sensor.unique_id == "smart_climate_indoor_humidity"
        assert sensor._attr_device_class == SensorDeviceClass.HUMIDITY
        assert sensor._attr_native_unit_of_measurement == PERCENTAGE
        assert sensor._attr_state_class == SensorStateClass.MEASUREMENT
        
    @pytest.mark.asyncio
    async def test_async_update(self):
        """Test async_update gets data from HumidityMonitor."""
        mock_monitor = Mock(spec=HumidityMonitor)
        mock_monitor.async_get_sensor_data = AsyncMock(return_value={
            "indoor_humidity": 45.2,
            "outdoor_humidity": 68.1,
            "humidity_differential": -22.9
        })
        
        sensor = IndoorHumiditySensor(mock_monitor)
        await sensor.async_update()
        
        assert sensor._attr_native_value == 45.2
        mock_monitor.async_get_sensor_data.assert_called_once()
        
    @pytest.mark.asyncio  
    async def test_async_update_unavailable(self):
        """Test async_update handles unavailable sensor gracefully."""
        mock_monitor = Mock(spec=HumidityMonitor)
        mock_monitor.async_get_sensor_data = AsyncMock(return_value={
            "indoor_humidity": None,
            "outdoor_humidity": 68.1,
            "humidity_differential": None
        })
        
        sensor = IndoorHumiditySensor(mock_monitor)
        await sensor.async_update()
        
        assert sensor._attr_native_value is None
        assert sensor._attr_available is False
        

class TestOutdoorHumiditySensor:
    """Test suite for OutdoorHumiditySensor."""
    
    def test_sensor_attributes(self):
        """Test OutdoorHumiditySensor has correct attributes."""
        mock_monitor = Mock(spec=HumidityMonitor)
        
        sensor = OutdoorHumiditySensor(mock_monitor)
        
        assert sensor._sensor_type == "outdoor_humidity"
        assert sensor.name == "Smart Climate Outdoor Humidity" 
        assert sensor.unique_id == "smart_climate_outdoor_humidity"
        assert sensor._attr_device_class == SensorDeviceClass.HUMIDITY
        assert sensor._attr_native_unit_of_measurement == PERCENTAGE
        assert sensor._attr_state_class == SensorStateClass.MEASUREMENT
        
    @pytest.mark.asyncio
    async def test_async_update(self):
        """Test async_update gets data from HumidityMonitor."""
        mock_monitor = Mock(spec=HumidityMonitor)
        mock_monitor.async_get_sensor_data = AsyncMock(return_value={
            "indoor_humidity": 45.2,
            "outdoor_humidity": 68.1,
            "humidity_differential": -22.9
        })
        
        sensor = OutdoorHumiditySensor(mock_monitor)
        await sensor.async_update()
        
        assert sensor._attr_native_value == 68.1
        mock_monitor.async_get_sensor_data.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_async_update_unavailable(self):
        """Test async_update handles unavailable sensor gracefully."""
        mock_monitor = Mock(spec=HumidityMonitor)
        mock_monitor.async_get_sensor_data = AsyncMock(return_value={
            "indoor_humidity": 45.2,
            "outdoor_humidity": None,
            "humidity_differential": None
        })
        
        sensor = OutdoorHumiditySensor(mock_monitor)
        await sensor.async_update()
        
        assert sensor._attr_native_value is None
        assert sensor._attr_available is False


class TestHumidityDifferentialSensor:
    """Test suite for HumidityDifferentialSensor."""
    
    def test_sensor_attributes(self):
        """Test HumidityDifferentialSensor has correct attributes."""
        mock_monitor = Mock(spec=HumidityMonitor)
        
        sensor = HumidityDifferentialSensor(mock_monitor)
        
        assert sensor._sensor_type == "humidity_differential"
        assert sensor.name == "Smart Climate Humidity Differential"
        assert sensor.unique_id == "smart_climate_humidity_differential"
        assert sensor._attr_device_class is None  # Differential doesn't use humidity device class
        assert sensor._attr_native_unit_of_measurement == PERCENTAGE
        assert sensor._attr_state_class == SensorStateClass.MEASUREMENT
        
    @pytest.mark.asyncio
    async def test_async_update(self):
        """Test async_update gets data from HumidityMonitor."""
        mock_monitor = Mock(spec=HumidityMonitor)
        mock_monitor.async_get_sensor_data = AsyncMock(return_value={
            "indoor_humidity": 45.2,
            "outdoor_humidity": 68.1,
            "humidity_differential": -22.9
        })
        
        sensor = HumidityDifferentialSensor(mock_monitor)
        await sensor.async_update()
        
        assert sensor._attr_native_value == -22.9
        mock_monitor.async_get_sensor_data.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_async_update_unavailable(self):
        """Test async_update handles unavailable sensor gracefully."""
        mock_monitor = Mock(spec=HumidityMonitor)
        mock_monitor.async_get_sensor_data = AsyncMock(return_value={
            "indoor_humidity": None,
            "outdoor_humidity": None,
            "humidity_differential": None
        })
        
        sensor = HumidityDifferentialSensor(mock_monitor)
        await sensor.async_update()
        
        assert sensor._attr_native_value is None
        assert sensor._attr_available is False


class TestSensorDataFlow:
    """Test suite for sensor data flow integration."""
    
    @pytest.mark.asyncio
    async def test_all_sensors_get_different_data(self):
        """Test that all sensors get their respective data fields."""
        mock_monitor = Mock(spec=HumidityMonitor)
        mock_monitor.async_get_sensor_data = AsyncMock(return_value={
            "indoor_humidity": 45.2,
            "outdoor_humidity": 68.1,
            "humidity_differential": -22.9
        })
        
        indoor_sensor = IndoorHumiditySensor(mock_monitor)
        outdoor_sensor = OutdoorHumiditySensor(mock_monitor)
        diff_sensor = HumidityDifferentialSensor(mock_monitor)
        
        await indoor_sensor.async_update()
        await outdoor_sensor.async_update()
        await diff_sensor.async_update()
        
        assert indoor_sensor._attr_native_value == 45.2
        assert outdoor_sensor._attr_native_value == 68.1
        assert diff_sensor._attr_native_value == -22.9
        
        # Verify HumidityMonitor was called for each sensor
        assert mock_monitor.async_get_sensor_data.call_count == 3