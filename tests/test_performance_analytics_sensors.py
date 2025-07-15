"""Tests for performance analytics sensors."""
import pytest
from unittest.mock import MagicMock, patch
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTime,
)
from custom_components.smart_climate.sensor_performance import (
    PredictionLatencySensor,
    EnergyEfficiencySensor,
    TemperatureStabilitySensor,
    LearnedDelaySensor,
    EMACoeffficientSensor,
    SensorAvailabilitySensor,
)


@pytest.fixture
def hass():
    """Return a mock Home Assistant instance."""
    return MagicMock()


@pytest.fixture
def device_info():
    """Return mock device info."""
    return DeviceInfo(
        identifiers={("smart_climate", "test_climate")},
        name="Test Climate",
        manufacturer="Smart Climate",
    )


@pytest.fixture
def coordinator(hass):
    """Return a mock coordinator."""
    coordinator = MagicMock()
    coordinator.hass = hass
    coordinator.name = "test_climate"
    coordinator.config_entry = MagicMock()
    coordinator.config_entry.entry_id = "test_entry"
    coordinator.last_update_success = True
    return coordinator


@pytest.fixture
def dashboard_data():
    """Return sample dashboard data with all fields."""
    return {
        "api_version": "1.3.0",
        "calculated_offset": 2.5,
        "learning_info": {"enabled": True},
        "save_diagnostics": {"last_save": "2025-07-15"},
        "calibration_info": {"status": "calibrated"},
        "seasonal_data": {
            "enabled": True,
            "contribution": 15.5,
            "pattern_count": 42,
            "outdoor_temp_bucket": "20-25°C",
            "accuracy": 87.3,
        },
        "delay_data": {
            "adaptive_delay": 45.0,
            "temperature_stability_detected": True,
            "learned_delay_seconds": 50.5,
        },
        "ac_behavior": {
            "temperature_window": "±0.5°C",
            "power_correlation_accuracy": 92.1,
            "hysteresis_cycle_count": 156,
        },
        "performance": {
            "ema_coefficient": 0.123,
            "prediction_latency_ms": 2.5,
            "energy_efficiency_score": 85,
            "sensor_availability_score": 98.7,
        },
        "system_health": {
            "memory_usage_kb": 1024.5,
            "persistence_latency_ms": 15.3,
            "outlier_detection_active": True,
            "samples_per_day": 288.0,
            "accuracy_improvement_rate": 1.25,
            "convergence_trend": "improving",
        },
        "diagnostics": {
            "last_update_duration_ms": 125.4,
            "cache_hit_rate": 0.875,
            "cached_keys": 15,
        },
    }


class TestPredictionLatencySensor:
    """Test the PredictionLatencySensor class."""

    def test_init(self, coordinator, device_info):
        """Test sensor initialization."""
        sensor = PredictionLatencySensor(coordinator, device_info, "Test Climate")
        
        assert sensor.entity_description.key == "prediction_latency"
        assert sensor.entity_description.name == "Prediction Latency"
        assert sensor.entity_description.native_unit_of_measurement == "ms"
        assert sensor.entity_description.device_class == SensorDeviceClass.DURATION
        assert sensor.entity_description.state_class == SensorStateClass.MEASUREMENT
        assert sensor._attr_unique_id == "test_entry_prediction_latency"

    def test_native_value_with_data(self, coordinator, device_info, dashboard_data):
        """Test sensor returns correct value when data is available."""
        coordinator.data = dashboard_data
        sensor = PredictionLatencySensor(coordinator, device_info, "Test Climate")
        
        assert sensor.native_value == 2.5

    def test_native_value_missing_performance(self, coordinator, device_info):
        """Test sensor returns None when performance data is missing."""
        coordinator.data = {"api_version": "1.3.0"}
        sensor = PredictionLatencySensor(coordinator, device_info, "Test Climate")
        
        assert sensor.native_value is None

    def test_native_value_none_data(self, coordinator, device_info):
        """Test sensor returns None when coordinator data is None."""
        coordinator.data = None
        sensor = PredictionLatencySensor(coordinator, device_info, "Test Climate")
        
        assert sensor.native_value is None


class TestEnergyEfficiencySensor:
    """Test the EnergyEfficiencySensor class."""

    def test_init(self, coordinator, device_info):
        """Test sensor initialization."""
        sensor = EnergyEfficiencySensor(coordinator, device_info, "Test Climate")
        
        assert sensor.entity_description.key == "energy_efficiency_score"
        assert sensor.entity_description.name == "Energy Efficiency Score"
        assert sensor.entity_description.native_unit_of_measurement == "/100"
        assert sensor.entity_description.state_class == SensorStateClass.MEASUREMENT
        assert sensor.entity_description.icon == "mdi:leaf-circle"
        assert sensor._attr_unique_id == "test_entry_energy_efficiency_score"

    def test_native_value_with_data(self, coordinator, device_info, dashboard_data):
        """Test sensor returns correct value when data is available."""
        coordinator.data = dashboard_data
        sensor = EnergyEfficiencySensor(coordinator, device_info, "Test Climate")
        
        assert sensor.native_value == 85

    def test_native_value_missing_field(self, coordinator, device_info):
        """Test sensor returns None when field is missing."""
        coordinator.data = {
            "performance": {
                "ema_coefficient": 0.123,
                # energy_efficiency_score missing
            }
        }
        sensor = EnergyEfficiencySensor(coordinator, device_info, "Test Climate")
        
        assert sensor.native_value is None


class TestTemperatureStabilitySensor:
    """Test the TemperatureStabilitySensor class."""

    def test_init(self, coordinator, device_info):
        """Test sensor initialization."""
        sensor = TemperatureStabilitySensor(coordinator, device_info, "Test Climate")
        
        assert sensor.entity_description.key == "temperature_stability_detected"
        assert sensor.entity_description.name == "Temperature Stability Detected"
        assert sensor.entity_description.icon == "mdi:waves-arrow-up"
        assert sensor._attr_unique_id == "test_entry_temperature_stability_detected"

    def test_native_value_true(self, coordinator, device_info, dashboard_data):
        """Test sensor returns 'on' when stability is detected."""
        coordinator.data = dashboard_data
        sensor = TemperatureStabilitySensor(coordinator, device_info, "Test Climate")
        
        assert sensor.native_value == "on"

    def test_native_value_false(self, coordinator, device_info):
        """Test sensor returns 'off' when stability is not detected."""
        coordinator.data = {
            "delay_data": {
                "temperature_stability_detected": False,
            }
        }
        sensor = TemperatureStabilitySensor(coordinator, device_info, "Test Climate")
        
        assert sensor.native_value == "off"

    def test_native_value_missing_data(self, coordinator, device_info):
        """Test sensor returns None when data is missing."""
        coordinator.data = {}
        sensor = TemperatureStabilitySensor(coordinator, device_info, "Test Climate")
        
        assert sensor.native_value is None


class TestLearnedDelaySensor:
    """Test the LearnedDelaySensor class."""

    def test_init(self, coordinator, device_info):
        """Test sensor initialization."""
        sensor = LearnedDelaySensor(coordinator, device_info, "Test Climate")
        
        assert sensor.entity_description.key == "learned_delay"
        assert sensor.entity_description.name == "Learned Delay"
        assert sensor.entity_description.native_unit_of_measurement == UnitOfTime.SECONDS
        assert sensor.entity_description.device_class == SensorDeviceClass.DURATION
        assert sensor.entity_description.state_class == SensorStateClass.MEASUREMENT
        assert sensor._attr_unique_id == "test_entry_learned_delay"

    def test_native_value_with_data(self, coordinator, device_info, dashboard_data):
        """Test sensor returns correct value when data is available."""
        coordinator.data = dashboard_data
        sensor = LearnedDelaySensor(coordinator, device_info, "Test Climate")
        
        assert sensor.native_value == 50.5

    def test_native_value_zero(self, coordinator, device_info):
        """Test sensor returns 0 when learned delay is 0."""
        coordinator.data = {
            "delay_data": {
                "learned_delay_seconds": 0.0,
            }
        }
        sensor = LearnedDelaySensor(coordinator, device_info, "Test Climate")
        
        assert sensor.native_value == 0.0


class TestEMACoeffficientSensor:
    """Test the EMACoeffficientSensor class."""

    def test_init(self, coordinator, device_info):
        """Test sensor initialization."""
        sensor = EMACoeffficientSensor(coordinator, device_info, "Test Climate")
        
        assert sensor.entity_description.key == "ema_coefficient"
        assert sensor.entity_description.name == "EMA Coefficient"
        assert sensor.entity_description.state_class == SensorStateClass.MEASUREMENT
        assert sensor.entity_description.icon == "mdi:chart-bell-curve"
        assert sensor._attr_unique_id == "test_entry_ema_coefficient"

    def test_native_value_with_data(self, coordinator, device_info, dashboard_data):
        """Test sensor returns correct value when data is available."""
        coordinator.data = dashboard_data
        sensor = EMACoeffficientSensor(coordinator, device_info, "Test Climate")
        
        assert sensor.native_value == 0.123

    def test_native_value_with_rounding(self, coordinator, device_info):
        """Test sensor rounds value to 3 decimal places."""
        coordinator.data = {
            "performance": {
                "ema_coefficient": 0.12345678,
            }
        }
        sensor = EMACoeffficientSensor(coordinator, device_info, "Test Climate")
        
        assert sensor.native_value == 0.123


class TestSensorAvailabilitySensor:
    """Test the SensorAvailabilitySensor class."""

    def test_init(self, coordinator, device_info):
        """Test sensor initialization."""
        sensor = SensorAvailabilitySensor(coordinator, device_info, "Test Climate")
        
        assert sensor.entity_description.key == "sensor_availability"
        assert sensor.entity_description.name == "Sensor Availability"
        assert sensor.entity_description.native_unit_of_measurement == PERCENTAGE
        assert sensor.entity_description.state_class == SensorStateClass.MEASUREMENT
        assert sensor.entity_description.icon == "mdi:access-point-check"
        assert sensor._attr_unique_id == "test_entry_sensor_availability"

    def test_native_value_with_data(self, coordinator, device_info, dashboard_data):
        """Test sensor returns correct value when data is available."""
        coordinator.data = dashboard_data
        sensor = SensorAvailabilitySensor(coordinator, device_info, "Test Climate")
        
        assert sensor.native_value == 98.7

    def test_native_value_100_percent(self, coordinator, device_info):
        """Test sensor can return 100% availability."""
        coordinator.data = {
            "performance": {
                "sensor_availability_score": 100.0,
            }
        }
        sensor = SensorAvailabilitySensor(coordinator, device_info, "Test Climate")
        
        assert sensor.native_value == 100.0