"""Integration smoke test for humidity sensors with HumidityMonitor."""

import pytest
from unittest.mock import Mock, AsyncMock

from custom_components.smart_climate.humidity_monitor import HumidityMonitor
from custom_components.smart_climate.humidity_sensors import (
    IndoorHumiditySensor,
    OutdoorHumiditySensor,
    HumidityDifferentialSensor,
)


class TestHumiditySensorIntegration:
    """Integration tests for humidity sensors with HumidityMonitor."""

    @pytest.mark.asyncio
    async def test_end_to_end_sensor_data_flow(self):
        """Test complete data flow from SensorManager through HumidityMonitor to sensor entities."""
        # Mock dependencies
        mock_hass = Mock()
        mock_sensor_manager = Mock()
        mock_offset_engine = Mock()
        
        # Set up sensor manager return values
        mock_sensor_manager.get_indoor_humidity.return_value = 42.5
        mock_sensor_manager.get_outdoor_humidity.return_value = 75.2
        mock_sensor_manager.get_room_temperature.return_value = 22.0
        mock_sensor_manager.get_outdoor_temperature.return_value = 15.0
        
        # Create HumidityMonitor 
        monitor = HumidityMonitor(mock_hass, mock_sensor_manager, mock_offset_engine, {})
        
        # Create sensor entities
        indoor_sensor = IndoorHumiditySensor(monitor)
        outdoor_sensor = OutdoorHumiditySensor(monitor)
        differential_sensor = HumidityDifferentialSensor(monitor)
        
        # Update all sensors
        await indoor_sensor.async_update()
        await outdoor_sensor.async_update()
        await differential_sensor.async_update()
        
        # Verify sensor states
        assert indoor_sensor._attr_native_value == 42.5
        assert outdoor_sensor._attr_native_value == 75.2
        assert differential_sensor._attr_native_value == -32.7  # 42.5 - 75.2 = -32.7
        
        # Verify all sensors are available
        assert indoor_sensor._attr_available is True
        assert outdoor_sensor._attr_available is True
        assert differential_sensor._attr_available is True
        
        # Verify sensor manager was called
        assert mock_sensor_manager.get_indoor_humidity.call_count == 3
        assert mock_sensor_manager.get_outdoor_humidity.call_count == 3

    @pytest.mark.asyncio
    async def test_integration_with_missing_sensors(self):
        """Test integration when some sensors are unavailable."""
        # Mock dependencies
        mock_hass = Mock()
        mock_sensor_manager = Mock()
        mock_offset_engine = Mock()
        
        # Set up sensor manager - only indoor available
        mock_sensor_manager.get_indoor_humidity.return_value = 45.0
        mock_sensor_manager.get_outdoor_humidity.return_value = None
        mock_sensor_manager.get_room_temperature.return_value = 22.0
        mock_sensor_manager.get_outdoor_temperature.return_value = None
        
        # Create HumidityMonitor and sensors
        monitor = HumidityMonitor(mock_hass, mock_sensor_manager, mock_offset_engine, {})
        
        indoor_sensor = IndoorHumiditySensor(monitor)
        outdoor_sensor = OutdoorHumiditySensor(monitor)
        differential_sensor = HumidityDifferentialSensor(monitor)
        
        # Update all sensors
        await indoor_sensor.async_update()
        await outdoor_sensor.async_update()
        await differential_sensor.async_update()
        
        # Indoor should be available
        assert indoor_sensor._attr_native_value == 45.0
        assert indoor_sensor._attr_available is True
        
        # Outdoor should be unavailable
        assert outdoor_sensor._attr_native_value is None
        assert outdoor_sensor._attr_available is False
        
        # Differential should be unavailable (missing outdoor)
        assert differential_sensor._attr_native_value is None
        assert differential_sensor._attr_available is False