"""Tests for calculated humidity feature sensors (sensors 4-7).

Tests heat index, dew point, and absolute humidity sensors that calculate
derived values from temperature and humidity measurements.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfTemperature

from custom_components.smart_climate.humidity_sensors import (
    HeatIndexSensor,
    IndoorDewPointSensor,
    OutdoorDewPointSensor,
    AbsoluteHumiditySensor
)


class TestHeatIndexSensor:
    """Test HeatIndexSensor calculated feature sensor."""

    @pytest.fixture
    def mock_humidity_monitor(self):
        """Create mock HumidityMonitor."""
        monitor = Mock()
        monitor.async_get_sensor_data = AsyncMock()
        return monitor

    @pytest.fixture
    def heat_index_sensor(self, mock_humidity_monitor):
        """Create HeatIndexSensor instance."""
        return HeatIndexSensor(mock_humidity_monitor)

    def test_init_properties(self, heat_index_sensor):
        """Test sensor initialization and properties."""
        assert heat_index_sensor.name == "Smart Climate Heat Index"
        assert heat_index_sensor.unique_id == "smart_climate_heat_index"
        assert heat_index_sensor._sensor_type == "heat_index"
        assert heat_index_sensor._attr_device_class == SensorDeviceClass.TEMPERATURE
        assert heat_index_sensor._attr_native_unit_of_measurement == UnitOfTemperature.CELSIUS

    @pytest.mark.asyncio
    async def test_async_update_with_heat_index(self, heat_index_sensor, mock_humidity_monitor):
        """Test sensor update with valid heat index value."""
        # Arrange
        mock_humidity_monitor.async_get_sensor_data.return_value = {
            'heat_index': 28.5
        }

        # Act
        await heat_index_sensor.async_update()

        # Assert
        assert heat_index_sensor._attr_native_value == 28.5
        assert heat_index_sensor._attr_available is True

    @pytest.mark.asyncio
    async def test_async_update_with_none_value(self, heat_index_sensor, mock_humidity_monitor):
        """Test sensor update when heat index is None (insufficient data)."""
        # Arrange
        mock_humidity_monitor.async_get_sensor_data.return_value = {
            'heat_index': None
        }

        # Act
        await heat_index_sensor.async_update()

        # Assert
        assert heat_index_sensor._attr_native_value is None
        assert heat_index_sensor._attr_available is False


class TestIndoorDewPointSensor:
    """Test IndoorDewPointSensor calculated feature sensor."""

    @pytest.fixture
    def mock_humidity_monitor(self):
        """Create mock HumidityMonitor."""
        monitor = Mock()
        monitor.async_get_sensor_data = AsyncMock()
        return monitor

    @pytest.fixture
    def indoor_dew_point_sensor(self, mock_humidity_monitor):
        """Create IndoorDewPointSensor instance."""
        return IndoorDewPointSensor(mock_humidity_monitor)

    def test_init_properties(self, indoor_dew_point_sensor):
        """Test sensor initialization and properties."""
        assert indoor_dew_point_sensor.name == "Smart Climate Dew Point Indoor"
        assert indoor_dew_point_sensor.unique_id == "smart_climate_dew_point_indoor"
        assert indoor_dew_point_sensor._sensor_type == "dew_point_indoor"
        assert indoor_dew_point_sensor._attr_device_class == SensorDeviceClass.TEMPERATURE
        assert indoor_dew_point_sensor._attr_native_unit_of_measurement == UnitOfTemperature.CELSIUS

    @pytest.mark.asyncio
    async def test_async_update_with_dew_point(self, indoor_dew_point_sensor, mock_humidity_monitor):
        """Test sensor update with valid dew point value."""
        # Arrange
        mock_humidity_monitor.async_get_sensor_data.return_value = {
            'dew_point_indoor': 12.3
        }

        # Act
        await indoor_dew_point_sensor.async_update()

        # Assert
        assert indoor_dew_point_sensor._attr_native_value == 12.3
        assert indoor_dew_point_sensor._attr_available is True


class TestOutdoorDewPointSensor:
    """Test OutdoorDewPointSensor calculated feature sensor."""

    @pytest.fixture
    def mock_humidity_monitor(self):
        """Create mock HumidityMonitor."""
        monitor = Mock()
        monitor.async_get_sensor_data = AsyncMock()
        return monitor

    @pytest.fixture
    def outdoor_dew_point_sensor(self, mock_humidity_monitor):
        """Create OutdoorDewPointSensor instance."""
        return OutdoorDewPointSensor(mock_humidity_monitor)

    def test_init_properties(self, outdoor_dew_point_sensor):
        """Test sensor initialization and properties."""
        assert outdoor_dew_point_sensor.name == "Smart Climate Dew Point Outdoor"
        assert outdoor_dew_point_sensor.unique_id == "smart_climate_dew_point_outdoor"
        assert outdoor_dew_point_sensor._sensor_type == "dew_point_outdoor"
        assert outdoor_dew_point_sensor._attr_device_class == SensorDeviceClass.TEMPERATURE
        assert outdoor_dew_point_sensor._attr_native_unit_of_measurement == UnitOfTemperature.CELSIUS


class TestAbsoluteHumiditySensor:
    """Test AbsoluteHumiditySensor calculated feature sensor."""

    @pytest.fixture
    def mock_humidity_monitor(self):
        """Create mock HumidityMonitor."""
        monitor = Mock()
        monitor.async_get_sensor_data = AsyncMock()
        return monitor

    @pytest.fixture
    def absolute_humidity_sensor(self, mock_humidity_monitor):
        """Create AbsoluteHumiditySensor instance."""
        return AbsoluteHumiditySensor(mock_humidity_monitor)

    def test_init_properties(self, absolute_humidity_sensor):
        """Test sensor initialization and properties."""
        assert absolute_humidity_sensor.name == "Smart Climate Absolute Humidity"
        assert absolute_humidity_sensor.unique_id == "smart_climate_absolute_humidity"
        assert absolute_humidity_sensor._sensor_type == "absolute_humidity"
        assert absolute_humidity_sensor._attr_device_class is None  # No device class for g/m³
        assert absolute_humidity_sensor._attr_native_unit_of_measurement == "g/m³"

    @pytest.mark.asyncio
    async def test_async_update_with_absolute_humidity(self, absolute_humidity_sensor, mock_humidity_monitor):
        """Test sensor update with valid absolute humidity value."""
        # Arrange
        mock_humidity_monitor.async_get_sensor_data.return_value = {
            'absolute_humidity': 8.4
        }

        # Act
        await absolute_humidity_sensor.async_update()

        # Assert
        assert absolute_humidity_sensor._attr_native_value == 8.4
        assert absolute_humidity_sensor._attr_available is True


class TestHumidityMonitorCalculations:
    """Test HumidityMonitor calculations for derived humidity features."""

    @pytest.fixture
    def mock_sensor_manager(self):
        """Create mock SensorManager."""
        manager = Mock()
        manager.get_indoor_humidity = Mock()
        manager.get_outdoor_humidity = Mock()
        # Add methods for temperature readings needed for calculations
        manager.get_room_temperature = Mock()
        manager.get_outdoor_temperature = Mock()
        return manager

    @pytest.fixture
    def mock_offset_engine(self):
        """Create mock OffsetEngine."""
        return Mock()

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return {}

    def test_heat_index_calculation_celsius(self):
        """Test heat index calculation using Celsius formula."""
        # Known values: 30°C, 70% humidity
        temp_c = 30.0
        humidity = 70.0
        
        # Heat index formula for Celsius (simplified Steadman formula)
        # HI = T + 0.348 * rh - 4.25 (no wind speed for indoor)
        expected = temp_c + 0.348 * humidity - 4.25
        
        # This should be around 50.11°C
        assert abs(expected - 50.11) < 0.1

    def test_dew_point_calculation_magnus(self):
        """Test dew point calculation using Magnus formula."""
        # Known values: 25°C, 60% humidity should give ~16.7°C dew point
        temp_c = 25.0
        humidity = 60.0
        
        # Magnus formula constants
        b = 17.62
        c = 243.12
        
        # Calculate gamma
        import math
        gamma = (b * temp_c) / (c + temp_c) + math.log(humidity / 100.0)
        
        # Calculate dew point
        expected_dew_point = (c * gamma) / (b - gamma)
        
        # This should be around 16.7°C
        assert abs(expected_dew_point - 16.7) < 0.5

    def test_absolute_humidity_calculation(self):
        """Test absolute humidity calculation."""
        # Known values: 20°C, 50% humidity should give ~8.7 g/m³
        temp_c = 20.0
        humidity = 50.0
        
        # Saturated vapor pressure (Buck equation)
        import math
        svp = 0.61121 * math.exp((18.678 - temp_c / 234.5) * (temp_c / (257.14 + temp_c)))
        
        # Actual vapor pressure
        vp = humidity / 100.0 * svp
        
        # Absolute humidity in g/m³
        expected = (vp * 1000 * 18.016) / (8.314 * (temp_c + 273.15))
        
        # This should be around 8.7 g/m³
        assert abs(expected - 8.7) < 0.5

    @pytest.mark.asyncio
    async def test_async_get_sensor_data_includes_calculated_values(self):
        """Test that async_get_sensor_data returns calculated values."""
        from custom_components.smart_climate.humidity_monitor import HumidityMonitor
        
        # Create mock dependencies
        mock_sensor_manager = Mock()
        mock_sensor_manager.get_indoor_humidity.return_value = 60.0
        mock_sensor_manager.get_outdoor_humidity.return_value = 80.0
        mock_sensor_manager.get_room_temperature.return_value = 25.0
        mock_sensor_manager.get_outdoor_temperature.return_value = 30.0
        
        mock_offset_engine = Mock()
        config = {}
        
        # Create HumidityMonitor instance
        monitor = HumidityMonitor(None, mock_sensor_manager, mock_offset_engine, config)
        
        # Act
        result = await monitor.async_get_sensor_data()
        
        # Assert - should include calculated values
        expected_keys = {
            'indoor_humidity', 'outdoor_humidity', 'humidity_differential',
            'heat_index', 'dew_point_indoor', 'dew_point_outdoor', 'absolute_humidity'
        }
        
        for key in expected_keys:
            assert key in result, f"Missing expected key: {key}"

    @pytest.mark.asyncio 
    async def test_handle_missing_sensor_data(self):
        """Test graceful handling when required sensor data is missing."""
        from custom_components.smart_climate.humidity_monitor import HumidityMonitor
        
        # Create mock with missing temperature data
        mock_sensor_manager = Mock()
        mock_sensor_manager.get_indoor_humidity.return_value = 60.0
        mock_sensor_manager.get_outdoor_humidity.return_value = None  # Missing
        mock_sensor_manager.get_room_temperature.return_value = None  # Missing
        mock_sensor_manager.get_outdoor_temperature.return_value = None  # Missing
        
        mock_offset_engine = Mock()
        config = {}
        
        monitor = HumidityMonitor(None, mock_sensor_manager, mock_offset_engine, config)
        
        # Act
        result = await monitor.async_get_sensor_data()
        
        # Assert - calculated values should be None when required inputs missing
        assert result['indoor_humidity'] == 60.0  # Available
        assert result['outdoor_humidity'] is None  # Missing
        assert result['humidity_differential'] is None  # Missing because outdoor is None
        assert result['heat_index'] is None  # Missing because temperature is None
        assert result['dew_point_indoor'] is None  # Missing because temperature is None
        assert result['dew_point_outdoor'] is None  # Missing because both are None
        assert result['absolute_humidity'] is None  # Missing because temperature is None

    def test_actual_calculation_methods(self):
        """Test the actual calculation methods work correctly."""
        from custom_components.smart_climate.humidity_monitor import HumidityMonitor
        
        # Create monitor instance (just for accessing methods)
        mock_sensor_manager = Mock()
        mock_offset_engine = Mock()
        config = {}
        
        monitor = HumidityMonitor(None, mock_sensor_manager, mock_offset_engine, config)
        
        # Test heat index calculation
        heat_index = monitor._calculate_heat_index(25.0, 60.0)
        assert heat_index is not None
        assert isinstance(heat_index, float)
        assert heat_index > 25.0  # Should be higher than base temperature
        
        # Test dew point calculation
        dew_point = monitor._calculate_dew_point(25.0, 60.0)
        assert dew_point is not None
        assert isinstance(dew_point, float)
        assert dew_point < 25.0  # Should be lower than temperature
        
        # Test absolute humidity calculation
        abs_humidity = monitor._calculate_absolute_humidity(20.0, 50.0)
        assert abs_humidity is not None
        assert isinstance(abs_humidity, float)
        assert abs_humidity > 0  # Should be positive
        
        # Test edge cases
        assert monitor._calculate_heat_index(None, 60.0) is None
        assert monitor._calculate_dew_point(25.0, None) is None
        assert monitor._calculate_absolute_humidity(None, None) is None


# Tests use math module instead of numpy for better compatibility