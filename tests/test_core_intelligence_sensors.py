"""Tests for core intelligence sensor entities."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from homeassistant.components.sensor import SensorStateClass, SensorDeviceClass
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.config_entries import ConfigEntry

from custom_components.smart_climate.sensor import (
    SmartClimateDashboardSensor,
    AdaptiveDelaySensor,
    WeatherForecastSensor,
    SeasonalAdaptationSensor,
    SeasonalContributionSensor,
)
from custom_components.smart_climate.const import DOMAIN


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator with test data."""
    coordinator = Mock()
    coordinator.last_update_success = True
    coordinator.name = "test_climate"
    coordinator.data = {
        "calculated_offset": 2.5,
        "learning_info": {
            "enabled": True,
            "samples": 15,
            "accuracy": 0.85,
        },
        "save_diagnostics": {
            "save_count": 10,
            "failed_save_count": 1,
            "last_save_time": "2025-07-15T12:00:00",
        },
        "calibration_info": {
            "in_calibration": False,
            "cached_offset": 1.5,
        },
        "seasonal_data": {
            "enabled": True,
            "contribution": 25.5,
            "pattern_count": 5,
            "outdoor_temp_bucket": "20-25°C",
            "accuracy": 87.3,
        },
        "delay_data": {
            "adaptive_delay": 45.0,
            "temperature_stability_detected": True,
            "learned_delay_seconds": 60.0,
        },
        "ac_behavior": {
            "temperature_window": "±0.5°C",
            "power_correlation_accuracy": 92.5,
            "hysteresis_cycle_count": 25,
        },
        "performance": {
            "ema_coefficient": 0.123,
            "prediction_latency_ms": 1.5,
            "energy_efficiency_score": 85,
            "sensor_availability_score": 95.5,
        },
        "system_health": {
            "memory_usage_kb": 1024.5,
            "persistence_latency_ms": 5.2,
            "outlier_detection_active": True,
            "samples_per_day": 288.0,
            "accuracy_improvement_rate": 2.5,
            "convergence_trend": "improving",
        },
        "diagnostics": {
            "last_update_duration_ms": 15.3,
            "cache_hit_rate": 0.85,
            "cached_keys": 12,
        },
    }
    return coordinator


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = Mock(spec=ConfigEntry)
    entry.unique_id = "test_unique_id"
    entry.title = "Test Climate"
    entry.entry_id = "test_entry_id"
    return entry


@pytest.fixture
def mock_device_info():
    """Create mock device info."""
    return DeviceInfo(
        identifiers={(DOMAIN, "test_unique_id_climate_test_entity")},
        name="Test Climate (climate.test_entity)",
    )


class TestAdaptiveDelaySensor:
    """Test the Adaptive Delay sensor."""
    
    def test_sensor_initialization(self, mock_coordinator, mock_config_entry):
        """Test sensor initializes correctly."""
        sensor = AdaptiveDelaySensor(
            mock_coordinator,
            "climate.test_entity",
            mock_config_entry
        )
        
        assert sensor._sensor_type == "adaptive_delay"
        assert sensor.name == "Adaptive Delay"
        assert sensor.native_unit_of_measurement == UnitOfTime.SECONDS
        assert sensor.device_class == SensorDeviceClass.DURATION
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.icon == "mdi:camera-timer"
        assert sensor.entity_category is not None  # Should be diagnostic
    
    def test_sensor_value_from_data(self, mock_coordinator, mock_config_entry):
        """Test sensor returns correct value from coordinator data."""
        sensor = AdaptiveDelaySensor(
            mock_coordinator,
            "climate.test_entity",
            mock_config_entry
        )
        
        assert sensor.native_value == 45.0
    
    def test_sensor_handles_missing_data(self, mock_coordinator, mock_config_entry):
        """Test sensor handles missing delay_data gracefully."""
        mock_coordinator.data = {"calculated_offset": 0.0}
        
        sensor = AdaptiveDelaySensor(
            mock_coordinator,
            "climate.test_entity",
            mock_config_entry
        )
        
        assert sensor.native_value is None
    
    def test_sensor_handles_none_coordinator_data(self, mock_coordinator, mock_config_entry):
        """Test sensor handles None coordinator data."""
        mock_coordinator.data = None
        
        sensor = AdaptiveDelaySensor(
            mock_coordinator,
            "climate.test_entity",
            mock_config_entry
        )
        
        assert sensor.native_value is None


class TestWeatherForecastSensor:
    """Test the Weather Forecast binary sensor."""
    
    def test_sensor_initialization(self, mock_coordinator, mock_config_entry):
        """Test sensor initializes correctly."""
        sensor = WeatherForecastSensor(
            mock_coordinator,
            "climate.test_entity",
            mock_config_entry
        )
        
        assert sensor._sensor_type == "weather_forecast"
        assert sensor.name == "Weather Forecast"
        assert sensor.icon == "mdi:weather-partly-cloudy"
        assert sensor.entity_category is not None  # Should be diagnostic
        assert isinstance(sensor, BinarySensorEntity)
    
    def test_sensor_on_when_forecast_enabled(self, mock_coordinator, mock_config_entry):
        """Test sensor is on when weather forecast is enabled."""
        # Add weather_forecast field to coordinator data
        mock_coordinator.data["weather_forecast"] = True
        
        sensor = WeatherForecastSensor(
            mock_coordinator,
            "climate.test_entity",
            mock_config_entry
        )
        
        assert sensor.is_on is True
    
    def test_sensor_off_when_forecast_disabled(self, mock_coordinator, mock_config_entry):
        """Test sensor is off when weather forecast is disabled."""
        mock_coordinator.data["weather_forecast"] = False
        
        sensor = WeatherForecastSensor(
            mock_coordinator,
            "climate.test_entity",
            mock_config_entry
        )
        
        assert sensor.is_on is False
    
    def test_sensor_handles_missing_data(self, mock_coordinator, mock_config_entry):
        """Test sensor handles missing weather_forecast field."""
        # Remove weather_forecast from data
        if "weather_forecast" in mock_coordinator.data:
            del mock_coordinator.data["weather_forecast"]
        
        sensor = WeatherForecastSensor(
            mock_coordinator,
            "climate.test_entity",
            mock_config_entry
        )
        
        assert sensor.is_on is None


class TestSeasonalAdaptationSensor:
    """Test the Seasonal Adaptation binary sensor."""
    
    def test_sensor_initialization(self, mock_coordinator, mock_config_entry):
        """Test sensor initializes correctly."""
        sensor = SeasonalAdaptationSensor(
            mock_coordinator,
            "climate.test_entity",
            mock_config_entry
        )
        
        assert sensor._sensor_type == "seasonal_adaptation"
        assert sensor.name == "Seasonal Adaptation"
        assert sensor.icon == "mdi:sun-snowflake"
        assert sensor.entity_category is not None  # Should be diagnostic
        assert isinstance(sensor, BinarySensorEntity)
    
    def test_sensor_on_when_seasonal_enabled(self, mock_coordinator, mock_config_entry):
        """Test sensor is on when seasonal learning is enabled."""
        sensor = SeasonalAdaptationSensor(
            mock_coordinator,
            "climate.test_entity",
            mock_config_entry
        )
        
        # seasonal_data.enabled is True in fixture
        assert sensor.is_on is True
    
    def test_sensor_off_when_seasonal_disabled(self, mock_coordinator, mock_config_entry):
        """Test sensor is off when seasonal learning is disabled."""
        mock_coordinator.data["seasonal_data"]["enabled"] = False
        
        sensor = SeasonalAdaptationSensor(
            mock_coordinator,
            "climate.test_entity",
            mock_config_entry
        )
        
        assert sensor.is_on is False
    
    def test_sensor_handles_missing_data(self, mock_coordinator, mock_config_entry):
        """Test sensor handles missing seasonal_data."""
        mock_coordinator.data = {"calculated_offset": 0.0}
        
        sensor = SeasonalAdaptationSensor(
            mock_coordinator,
            "climate.test_entity",
            mock_config_entry
        )
        
        assert sensor.is_on is None


class TestSeasonalContributionSensor:
    """Test the Seasonal Contribution sensor."""
    
    def test_sensor_initialization(self, mock_coordinator, mock_config_entry):
        """Test sensor initializes correctly."""
        sensor = SeasonalContributionSensor(
            mock_coordinator,
            "climate.test_entity",
            mock_config_entry
        )
        
        assert sensor._sensor_type == "seasonal_contribution"
        assert sensor.name == "Seasonal Contribution"
        assert sensor.native_unit_of_measurement == PERCENTAGE
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.icon == "mdi:sun-snowflake"
        assert sensor.entity_category is not None  # Should be diagnostic
    
    def test_sensor_value_from_data(self, mock_coordinator, mock_config_entry):
        """Test sensor returns correct value from coordinator data."""
        sensor = SeasonalContributionSensor(
            mock_coordinator,
            "climate.test_entity",
            mock_config_entry
        )
        
        assert sensor.native_value == 25.5
    
    def test_sensor_handles_missing_data(self, mock_coordinator, mock_config_entry):
        """Test sensor handles missing seasonal_data gracefully."""
        mock_coordinator.data = {"calculated_offset": 0.0}
        
        sensor = SeasonalContributionSensor(
            mock_coordinator,
            "climate.test_entity",
            mock_config_entry
        )
        
        assert sensor.native_value is None
    
    def test_sensor_handles_none_value(self, mock_coordinator, mock_config_entry):
        """Test sensor handles None contribution value."""
        mock_coordinator.data["seasonal_data"]["contribution"] = None
        
        sensor = SeasonalContributionSensor(
            mock_coordinator,
            "climate.test_entity",
            mock_config_entry
        )
        
        assert sensor.native_value is None


class TestSensorIntegration:
    """Test sensor integration with async_setup_entry."""
    
    @pytest.mark.asyncio
    async def test_setup_adds_all_sensors(self, mock_coordinator, mock_config_entry):
        """Test that async_setup_entry adds all core intelligence sensors."""
        # Create a mock hass object
        hass = Mock()
        hass.data = {
            DOMAIN: {
                mock_config_entry.entry_id: {
                    "coordinators": {
                        "climate.test_entity": mock_coordinator
                    }
                }
            }
        }
        
        # Mock async_add_entities
        added_entities = []
        def mock_add_entities(entities):
            added_entities.extend(entities)
        
        # Import and call async_setup_entry
        from custom_components.smart_climate.sensor import async_setup_entry
        
        with patch('custom_components.smart_climate.sensor.AdaptiveDelaySensor', AdaptiveDelaySensor):
            with patch('custom_components.smart_climate.sensor.WeatherForecastSensor', WeatherForecastSensor):
                with patch('custom_components.smart_climate.sensor.SeasonalAdaptationSensor', SeasonalAdaptationSensor):
                    with patch('custom_components.smart_climate.sensor.SeasonalContributionSensor', SeasonalContributionSensor):
                        await async_setup_entry(hass, mock_config_entry, mock_add_entities)
        
        # Check that all sensors were added
        assert len(added_entities) > 0, "No entities were added"
        
        # Filter out the new sensors
        new_sensors = [sensor for sensor in added_entities if hasattr(sensor, '_sensor_type') and sensor._sensor_type in ["adaptive_delay", "weather_forecast", "seasonal_adaptation", "seasonal_contribution"]]
        
        # Check that all new sensor types were added
        sensor_types = [sensor._sensor_type for sensor in new_sensors]
        assert "adaptive_delay" in sensor_types
        assert "weather_forecast" in sensor_types
        assert "seasonal_adaptation" in sensor_types
        assert "seasonal_contribution" in sensor_types