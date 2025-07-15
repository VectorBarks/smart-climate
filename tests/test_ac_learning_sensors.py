"""Tests for AC learning sensors."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    STATE_UNAVAILABLE,
)
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.helpers.device_registry import DeviceInfo

from custom_components.smart_climate.sensor_ac_learning import (
    TemperatureWindowSensor,
    PowerCorrelationSensor,
    HysteresisCyclesSensor,
    ReactiveOffsetSensor,
    PredictiveOffsetSensor,
)
from custom_components.smart_climate.const import DOMAIN


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = {
        "calculated_offset": 2.5,
        "predictive_offset": -1.2,
        "ac_behavior": {
            "temperature_window": "±0.5°C",
            "power_correlation_accuracy": 85.5,
            "hysteresis_cycle_count": 42,
        },
    }
    return coordinator


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    config_entry = MagicMock()
    config_entry.unique_id = "test_unique_id"
    config_entry.title = "Test Climate"
    return config_entry


@pytest.fixture
def device_info():
    """Create mock device info."""
    return DeviceInfo(
        identifiers={(DOMAIN, "test_unique_id_climate_test")},
        name="Test Climate (climate.test)",
    )


class TestTemperatureWindowSensor:
    """Tests for TemperatureWindowSensor."""
    
    def test_initialization(self, mock_coordinator, mock_config_entry, device_info):
        """Test sensor initialization."""
        sensor = TemperatureWindowSensor(
            mock_coordinator,
            "climate.test",
            mock_config_entry,
        )
        
        assert sensor._attr_unique_id == "test_unique_id_climate_test_temperature_window"
        assert sensor._attr_name == "Temperature Window"
        assert sensor._attr_icon == "mdi:arrow-expand-vertical"
        assert sensor._attr_entity_category is None  # Should be visible by default
        assert sensor.should_poll is False
        
    def test_value_with_valid_data(self, mock_coordinator, mock_config_entry, device_info):
        """Test sensor value with valid data."""
        sensor = TemperatureWindowSensor(
            mock_coordinator,
            "climate.test",
            mock_config_entry,
        )
        
        assert sensor.native_value == "±0.5°C"
        
    def test_value_with_missing_data(self, mock_coordinator, mock_config_entry, device_info):
        """Test sensor value with missing data."""
        mock_coordinator.data = {}
        sensor = TemperatureWindowSensor(
            mock_coordinator,
            "climate.test", 
            mock_config_entry,
        )
        
        assert sensor.native_value is None
        
    def test_value_with_none_data(self, mock_coordinator, mock_config_entry, device_info):
        """Test sensor value with None data."""
        mock_coordinator.data = {
            "ac_behavior": {
                "temperature_window": None,
            }
        }
        sensor = TemperatureWindowSensor(
            mock_coordinator,
            "climate.test",
            mock_config_entry,
        )
        
        assert sensor.native_value is None


class TestPowerCorrelationSensor:
    """Tests for PowerCorrelationSensor."""
    
    def test_initialization(self, mock_coordinator, mock_config_entry, device_info):
        """Test sensor initialization."""
        sensor = PowerCorrelationSensor(
            mock_coordinator,
            "climate.test",
            mock_config_entry,
        )
        
        assert sensor._attr_unique_id == "test_unique_id_climate_test_power_correlation"
        assert sensor._attr_name == "Power Correlation Accuracy"
        assert sensor._attr_icon == "mdi:lightning-bolt-circle"
        assert sensor._attr_native_unit_of_measurement == PERCENTAGE
        assert sensor._attr_state_class == SensorStateClass.MEASUREMENT
        assert sensor._attr_entity_category is None
        
    def test_value_with_valid_data(self, mock_coordinator, mock_config_entry, device_info):
        """Test sensor value with valid data."""
        sensor = PowerCorrelationSensor(
            mock_coordinator,
            "climate.test",
            mock_config_entry,
        )
        
        assert sensor.native_value == 85.5
        
    def test_value_with_missing_data(self, mock_coordinator, mock_config_entry, device_info):
        """Test sensor value with missing data."""
        mock_coordinator.data = {"ac_behavior": {}}
        sensor = PowerCorrelationSensor(
            mock_coordinator,
            "climate.test",
            mock_config_entry,
        )
        
        assert sensor.native_value is None


class TestHysteresisCyclesSensor:
    """Tests for HysteresisCyclesSensor."""
    
    def test_initialization(self, mock_coordinator, mock_config_entry, device_info):
        """Test sensor initialization."""
        sensor = HysteresisCyclesSensor(
            mock_coordinator,
            "climate.test",
            mock_config_entry,
        )
        
        assert sensor._attr_unique_id == "test_unique_id_climate_test_hysteresis_cycles"
        assert sensor._attr_name == "Hysteresis Cycles"
        assert sensor._attr_icon == "mdi:sync-circle"
        assert sensor._attr_native_unit_of_measurement == "cycles"
        assert sensor._attr_state_class == SensorStateClass.TOTAL_INCREASING
        assert sensor._attr_entity_category is None
        
    def test_value_with_valid_data(self, mock_coordinator, mock_config_entry, device_info):
        """Test sensor value with valid data."""
        sensor = HysteresisCyclesSensor(
            mock_coordinator,
            "climate.test",
            mock_config_entry,
        )
        
        assert sensor.native_value == 42


class TestReactiveOffsetSensor:
    """Tests for ReactiveOffsetSensor."""
    
    def test_initialization(self, mock_coordinator, mock_config_entry, device_info):
        """Test sensor initialization."""
        sensor = ReactiveOffsetSensor(
            mock_coordinator,
            "climate.test",
            mock_config_entry,
        )
        
        assert sensor._attr_unique_id == "test_unique_id_climate_test_reactive_offset"
        assert sensor._attr_name == "Reactive Offset"
        assert sensor._attr_icon == "mdi:thermometer-chevron-up"
        assert sensor._attr_native_unit_of_measurement == UnitOfTemperature.CELSIUS
        assert sensor._attr_device_class == SensorDeviceClass.TEMPERATURE
        assert sensor._attr_state_class == SensorStateClass.MEASUREMENT
        assert sensor._attr_entity_category is None
        
    def test_value_with_valid_data(self, mock_coordinator, mock_config_entry, device_info):
        """Test sensor value with valid data."""
        sensor = ReactiveOffsetSensor(
            mock_coordinator,
            "climate.test",
            mock_config_entry,
        )
        
        assert sensor.native_value == 2.5
        
    def test_value_with_missing_data(self, mock_coordinator, mock_config_entry, device_info):
        """Test sensor value with missing data."""
        mock_coordinator.data = {}
        sensor = ReactiveOffsetSensor(
            mock_coordinator,
            "climate.test",
            mock_config_entry,
        )
        
        assert sensor.native_value is None


class TestPredictiveOffsetSensor:
    """Tests for PredictiveOffsetSensor."""
    
    def test_initialization(self, mock_coordinator, mock_config_entry, device_info):
        """Test sensor initialization."""
        sensor = PredictiveOffsetSensor(
            mock_coordinator,
            "climate.test",
            mock_config_entry,
        )
        
        assert sensor._attr_unique_id == "test_unique_id_climate_test_predictive_offset"
        assert sensor._attr_name == "Predictive Offset"
        assert sensor._attr_icon == "mdi:thermometer-chevron-down"
        assert sensor._attr_native_unit_of_measurement == UnitOfTemperature.CELSIUS
        assert sensor._attr_device_class == SensorDeviceClass.TEMPERATURE
        assert sensor._attr_state_class == SensorStateClass.MEASUREMENT
        assert sensor._attr_entity_category is None
        
    def test_value_with_valid_data(self, mock_coordinator, mock_config_entry, device_info):
        """Test sensor value with valid data."""
        sensor = PredictiveOffsetSensor(
            mock_coordinator,
            "climate.test",
            mock_config_entry,
        )
        
        assert sensor.native_value == -1.2
        
    def test_value_with_missing_data(self, mock_coordinator, mock_config_entry, device_info):
        """Test sensor value with missing data - shows unavailable."""
        mock_coordinator.data = {}
        sensor = PredictiveOffsetSensor(
            mock_coordinator,
            "climate.test",
            mock_config_entry,
        )
        
        assert sensor.native_value is None