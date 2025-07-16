"""Regression tests for Smart Climate sensor caching implementation.

ABOUTME: Tests that ensure existing sensor functionality remains intact
ABOUTME: Validates that caching doesn't break existing sensor behavior
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfTime
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

from custom_components.smart_climate.const import DOMAIN
from custom_components.smart_climate.sensor import (
    OffsetCurrentSensor,
    LearningProgressSensor,
    AccuracyCurrentSensor,
    CalibrationStatusSensor,
    HysteresisStateSensor,
    AdaptiveDelaySensor,
    WeatherForecastSensor,
    SeasonalAdaptationSensor,
    SeasonalContributionSensor,
    async_setup_entry,
)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {}}
    return hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.unique_id = "test_unique_id"
    entry.title = "Test Smart Climate"
    entry.data = {
        "climate_entity": "climate.test_ac",
        "room_sensor": "sensor.test_room",
        "power_sensor": "sensor.test_power",
        "max_offset": 5.0,
        "enable_learning": True,
    }
    return entry


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator with complete data."""
    coordinator = MagicMock(spec=DataUpdateCoordinator)
    coordinator.name = "test_climate"
    coordinator.data = {
        "calculated_offset": 2.3,
        "learning_info": {
            "enabled": True,
            "samples": 15,
            "accuracy": 0.85,
            "confidence": 0.75,
            "has_sufficient_data": True,
            "last_sample_time": "2025-07-16T12:00:00",
            "hysteresis_enabled": True,
            "hysteresis_state": "idle_stable_zone",
            "learned_start_threshold": 26.5,
            "learned_stop_threshold": 24.0,
            "temperature_window": 2.5,
            "start_samples_collected": 8,
            "stop_samples_collected": 7,
            "hysteresis_ready": True,
        },
        "delay_data": {
            "adaptive_delay": 45.0,
            "temperature_stability_detected": True,
            "learned_delay_seconds": 50.5,
        },
        "weather_forecast": True,
        "seasonal_data": {
            "enabled": True,
            "contribution": 15.5,
            "pattern_count": 42,
            "outdoor_temp_bucket": "20-25°C",
            "accuracy": 87.3,
        },
        "system_health": {
            "convergence_trend": "improving",
            "accuracy_improvement_rate": 1.25,
            "memory_usage_kb": 1024.5,
            "persistence_latency_ms": 15.3,
            "samples_per_day": 288.0,
        },
    }
    coordinator.last_update_success = True
    coordinator.last_update_time = datetime.now()
    return coordinator


@pytest.fixture
def mock_coordinator_none_data():
    """Create a coordinator with None data to test error handling."""
    coordinator = MagicMock(spec=DataUpdateCoordinator)
    coordinator.name = "test_climate"
    coordinator.data = None
    coordinator.last_update_success = False
    coordinator.last_update_time = None
    return coordinator


class TestExistingSensorsStillWork:
    """Test that existing sensors continue to work correctly after caching implementation."""
    
    @pytest.mark.asyncio
    async def test_offset_current_sensor_regression(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test that OffsetCurrentSensor still works correctly."""
        sensor = OffsetCurrentSensor(mock_coordinator, "climate.test_ac", mock_config_entry)
        
        # Test basic properties
        assert sensor.name == "Current Offset"
        assert sensor.native_unit_of_measurement == UnitOfTemperature.CELSIUS
        assert sensor.device_class == SensorDeviceClass.TEMPERATURE
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.suggested_display_precision == 1
        assert sensor.icon == "mdi:thermometer-lines"
        
        # Test value retrieval
        assert sensor.native_value == 2.3
        
        # Test unique_id format
        assert sensor.unique_id == "test_unique_id_climate_test_ac_offset_current"
        
        # Test device_info
        assert sensor.device_info["identifiers"] == {(DOMAIN, "test_unique_id_climate_test_ac")}
        assert sensor.device_info["name"] == "Test Smart Climate (climate.test_ac)"
    
    @pytest.mark.asyncio
    async def test_learning_progress_sensor_regression(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test that LearningProgressSensor still works correctly."""
        sensor = LearningProgressSensor(mock_coordinator, "climate.test_ac", mock_config_entry)
        
        # Test basic properties
        assert sensor.name == "Learning Progress"
        assert sensor.native_unit_of_measurement == PERCENTAGE
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.icon == "mdi:brain"
        
        # Test value calculation (15 samples, min 10 required = 100%)
        assert sensor.native_value == 100
        
        # Test with partial progress
        mock_coordinator.data["learning_info"]["samples"] = 5
        assert sensor.native_value == 50
        
        # Test with learning disabled
        mock_coordinator.data["learning_info"]["enabled"] = False
        assert sensor.native_value == 0
    
    @pytest.mark.asyncio
    async def test_accuracy_current_sensor_regression(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test that AccuracyCurrentSensor still works correctly."""
        sensor = AccuracyCurrentSensor(mock_coordinator, "climate.test_ac", mock_config_entry)
        
        # Test basic properties
        assert sensor.name == "Current Accuracy"
        assert sensor.native_unit_of_measurement == PERCENTAGE
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.icon == "mdi:target"
        
        # Test value conversion (0.85 -> 85%)
        assert sensor.native_value == 85
        
        # Test with zero accuracy
        mock_coordinator.data["learning_info"]["accuracy"] = 0.0
        assert sensor.native_value == 0
    
    @pytest.mark.asyncio
    async def test_calibration_status_sensor_regression(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test that CalibrationStatusSensor still works correctly."""
        sensor = CalibrationStatusSensor(mock_coordinator, "climate.test_ac", mock_config_entry)
        
        # Test basic properties
        assert sensor.name == "Calibration Status"
        assert sensor.icon == "mdi:progress-check"
        
        # Test complete status (15 samples >= 10 required)
        assert sensor.native_value == "Complete"
        
        # Test in progress status
        mock_coordinator.data["learning_info"]["samples"] = 7
        assert sensor.native_value == "In Progress (7/10 samples)"
        
        # Test disabled status
        mock_coordinator.data["learning_info"]["enabled"] = False
        assert sensor.native_value == "Waiting (Learning Disabled)"
        
        # Test extra attributes
        attrs = sensor.extra_state_attributes
        assert attrs["samples_collected"] == 7
        assert attrs["minimum_required"] == 10
        assert attrs["learning_enabled"] == False
        assert attrs["last_sample"] == "2025-07-16T12:00:00"
    
    @pytest.mark.asyncio
    async def test_hysteresis_state_sensor_regression(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test that HysteresisStateSensor still works correctly."""
        sensor = HysteresisStateSensor(mock_coordinator, "climate.test_ac", mock_config_entry)
        
        # Test basic properties
        assert sensor.name == "Hysteresis State"
        assert sensor.icon == "mdi:sine-wave"
        
        # Test state mapping
        assert sensor.native_value == "Temperature stable"
        
        # Test different states
        test_states = [
            ("learning_hysteresis", "Learning AC behavior"),
            ("active_phase", "AC actively cooling"),
            ("idle_above_start_threshold", "AC should start soon"),
            ("idle_below_stop_threshold", "AC recently stopped"),
            ("disabled", "No power sensor"),
            ("unknown_state", "Unknown"),
        ]
        
        for state_key, expected_text in test_states:
            mock_coordinator.data["learning_info"]["hysteresis_state"] = state_key
            assert sensor.native_value == expected_text
        
        # Test extra attributes
        attrs = sensor.extra_state_attributes
        assert attrs["power_sensor_configured"] == True
        assert attrs["start_threshold"] == "26.5°C"
        assert attrs["stop_threshold"] == "24.0°C"
        assert attrs["temperature_window"] == "2.5°C"
        assert attrs["start_samples"] == 8
        assert attrs["stop_samples"] == 7
        assert attrs["ready"] == True
    
    @pytest.mark.asyncio
    async def test_adaptive_delay_sensor_regression(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test that AdaptiveDelaySensor still works correctly."""
        sensor = AdaptiveDelaySensor(mock_coordinator, "climate.test_ac", mock_config_entry)
        
        # Test basic properties
        assert sensor.name == "Adaptive Delay"
        assert sensor.native_unit_of_measurement == UnitOfTime.SECONDS
        assert sensor.device_class == SensorDeviceClass.DURATION
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.suggested_display_precision == 1
        assert sensor.icon == "mdi:camera-timer"
        
        # Test value retrieval
        assert sensor.native_value == 45.0
    
    @pytest.mark.asyncio
    async def test_weather_forecast_sensor_regression(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test that WeatherForecastSensor still works correctly."""
        sensor = WeatherForecastSensor(mock_coordinator, "climate.test_ac", mock_config_entry)
        
        # Test basic properties
        assert sensor.name == "Weather Forecast"
        assert sensor.icon == "mdi:weather-partly-cloudy"
        
        # Test binary sensor behavior
        assert sensor.is_on == True
        assert sensor.native_value is None  # Binary sensors don't have native_value
        
        # Test with caching (should maintain last known value)
        sensor._last_known_value = False
        mock_coordinator.data["weather_forecast"] = None
        assert sensor.is_on == False  # Should return cached value
        
        # Test with valid boolean value
        mock_coordinator.data["weather_forecast"] = False
        assert sensor.is_on == False
        assert sensor._last_known_value == False
    
    @pytest.mark.asyncio
    async def test_seasonal_adaptation_sensor_regression(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test that SeasonalAdaptationSensor still works correctly."""
        sensor = SeasonalAdaptationSensor(mock_coordinator, "climate.test_ac", mock_config_entry)
        
        # Test basic properties
        assert sensor.name == "Seasonal Adaptation"
        assert sensor.icon == "mdi:sun-snowflake"
        
        # Test binary sensor behavior
        assert sensor.is_on == True
        assert sensor.native_value is None  # Binary sensors don't have native_value
        
        # Test with caching behavior
        sensor._last_known_value = False
        mock_coordinator.data["seasonal_data"]["enabled"] = None
        assert sensor.is_on == False  # Should return cached value
        
        # Test with valid boolean value
        mock_coordinator.data["seasonal_data"]["enabled"] = False
        assert sensor.is_on == False
        assert sensor._last_known_value == False
    
    @pytest.mark.asyncio
    async def test_seasonal_contribution_sensor_regression(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test that SeasonalContributionSensor still works correctly."""
        sensor = SeasonalContributionSensor(mock_coordinator, "climate.test_ac", mock_config_entry)
        
        # Test basic properties
        assert sensor.name == "Seasonal Contribution"
        assert sensor.native_unit_of_measurement == PERCENTAGE
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.suggested_display_precision == 1
        assert sensor.icon == "mdi:sun-snowflake"
        
        # Test value retrieval
        assert sensor.native_value == 15.5


class TestErrorHandlingRegression:
    """Test that error handling continues to work correctly."""
    
    @pytest.mark.asyncio
    async def test_sensors_handle_none_data(self, mock_hass, mock_config_entry, mock_coordinator_none_data):
        """Test that sensors handle None coordinator data gracefully."""
        sensors = [
            OffsetCurrentSensor(mock_coordinator_none_data, "climate.test_ac", mock_config_entry),
            LearningProgressSensor(mock_coordinator_none_data, "climate.test_ac", mock_config_entry),
            AccuracyCurrentSensor(mock_coordinator_none_data, "climate.test_ac", mock_config_entry),
            CalibrationStatusSensor(mock_coordinator_none_data, "climate.test_ac", mock_config_entry),
            HysteresisStateSensor(mock_coordinator_none_data, "climate.test_ac", mock_config_entry),
            AdaptiveDelaySensor(mock_coordinator_none_data, "climate.test_ac", mock_config_entry),
            WeatherForecastSensor(mock_coordinator_none_data, "climate.test_ac", mock_config_entry),
            SeasonalAdaptationSensor(mock_coordinator_none_data, "climate.test_ac", mock_config_entry),
            SeasonalContributionSensor(mock_coordinator_none_data, "climate.test_ac", mock_config_entry),
        ]
        
        for sensor in sensors:
            # Should not raise exceptions
            if hasattr(sensor, 'native_value'):
                value = sensor.native_value
                # Should return None or default value
                if sensor.__class__.__name__ in ["LearningProgressSensor", "AccuracyCurrentSensor"]:
                    assert value == 0  # These return 0 as default
                elif sensor.__class__.__name__ == "CalibrationStatusSensor":
                    assert value == "Unknown"  # This returns "Unknown" as default
                elif sensor.__class__.__name__ == "HysteresisStateSensor":
                    assert value == "Unknown"  # This returns "Unknown" as default
                else:
                    assert value is None
            
            if hasattr(sensor, 'is_on'):
                value = sensor.is_on
                assert value is None or isinstance(value, bool)
    
    @pytest.mark.asyncio
    async def test_sensors_handle_missing_data_keys(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test that sensors handle missing data keys gracefully."""
        # Remove specific data keys
        mock_coordinator.data = {
            "calculated_offset": 2.3,
            # Missing learning_info, delay_data, weather_forecast, seasonal_data
        }
        
        sensors = [
            OffsetCurrentSensor(mock_coordinator, "climate.test_ac", mock_config_entry),
            LearningProgressSensor(mock_coordinator, "climate.test_ac", mock_config_entry),
            AccuracyCurrentSensor(mock_coordinator, "climate.test_ac", mock_config_entry),
            CalibrationStatusSensor(mock_coordinator, "climate.test_ac", mock_config_entry),
            HysteresisStateSensor(mock_coordinator, "climate.test_ac", mock_config_entry),
            AdaptiveDelaySensor(mock_coordinator, "climate.test_ac", mock_config_entry),
            WeatherForecastSensor(mock_coordinator, "climate.test_ac", mock_config_entry),
            SeasonalAdaptationSensor(mock_coordinator, "climate.test_ac", mock_config_entry),
            SeasonalContributionSensor(mock_coordinator, "climate.test_ac", mock_config_entry),
        ]
        
        for sensor in sensors:
            # Should not raise exceptions
            if hasattr(sensor, 'native_value'):
                value = sensor.native_value
                # Should handle missing keys gracefully
                assert value is not None or sensor.__class__.__name__ in [
                    "AdaptiveDelaySensor", "SeasonalContributionSensor"
                ]
            
            if hasattr(sensor, 'is_on'):
                value = sensor.is_on
                # Should handle missing keys gracefully
                assert value is None or isinstance(value, bool)
    
    @pytest.mark.asyncio
    async def test_sensors_handle_invalid_data_types(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test that sensors handle invalid data types gracefully."""
        # Set invalid data types
        mock_coordinator.data = {
            "calculated_offset": "invalid_float",
            "learning_info": "not_a_dict",
            "delay_data": None,
            "weather_forecast": "not_a_boolean",
            "seasonal_data": [],
        }
        
        sensors = [
            OffsetCurrentSensor(mock_coordinator, "climate.test_ac", mock_config_entry),
            LearningProgressSensor(mock_coordinator, "climate.test_ac", mock_config_entry),
            AccuracyCurrentSensor(mock_coordinator, "climate.test_ac", mock_config_entry),
            CalibrationStatusSensor(mock_coordinator, "climate.test_ac", mock_config_entry),
            HysteresisStateSensor(mock_coordinator, "climate.test_ac", mock_config_entry),
            AdaptiveDelaySensor(mock_coordinator, "climate.test_ac", mock_config_entry),
            WeatherForecastSensor(mock_coordinator, "climate.test_ac", mock_config_entry),
            SeasonalAdaptationSensor(mock_coordinator, "climate.test_ac", mock_config_entry),
            SeasonalContributionSensor(mock_coordinator, "climate.test_ac", mock_config_entry),
        ]
        
        for sensor in sensors:
            # Should not raise exceptions
            if hasattr(sensor, 'native_value'):
                value = sensor.native_value
                # Should handle invalid types gracefully
                assert value is not None or sensor.__class__.__name__ in [
                    "OffsetCurrentSensor", "AdaptiveDelaySensor", "SeasonalContributionSensor"
                ]
            
            if hasattr(sensor, 'is_on'):
                value = sensor.is_on
                # Should handle invalid types gracefully
                assert value is None or isinstance(value, bool)


class TestSensorSetupRegression:
    """Test that sensor setup process continues to work correctly."""
    
    @pytest.mark.asyncio
    async def test_async_setup_entry_regression(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test that async_setup_entry still works correctly."""
        # Set up hass data
        mock_hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinators": {
                "climate.test_ac": mock_coordinator
            }
        }
        
        async_add_entities = AsyncMock()
        
        # Should not raise exceptions
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        # Should create all expected sensors
        async_add_entities.assert_called_once()
        sensors = async_add_entities.call_args[0][0]
        
        # Should create 34 sensors (5 legacy + 4 existing + 9 algorithm + 6 performance + 5 AC learning + 5 system health)
        assert len(sensors) == 34
        
        # Verify sensor types
        sensor_types = [type(s).__name__ for s in sensors]
        expected_types = [
            "OffsetCurrentSensor", "LearningProgressSensor", "AccuracyCurrentSensor",
            "CalibrationStatusSensor", "HysteresisStateSensor", "AdaptiveDelaySensor",
            "WeatherForecastSensor", "SeasonalAdaptationSensor", "SeasonalContributionSensor",
        ]
        
        for expected_type in expected_types:
            assert expected_type in sensor_types, f"Missing sensor type: {expected_type}"
    
    @pytest.mark.asyncio
    async def test_no_coordinators_handling(self, mock_hass, mock_config_entry, caplog):
        """Test that missing coordinators are handled gracefully."""
        # Set up empty coordinators
        mock_hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinators": {}
        }
        
        async_add_entities = AsyncMock()
        
        # Should not raise exceptions
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        # Should not create any sensors
        async_add_entities.assert_not_called()
        
        # Should log warning
        assert "No coordinators found for sensor setup" in caplog.text
    
    @pytest.mark.asyncio
    async def test_multiple_climate_entities(self, mock_hass, mock_config_entry):
        """Test that multiple climate entities are handled correctly."""
        # Create multiple coordinators
        coordinators = {}
        for i in range(3):
            coordinator = MagicMock(spec=DataUpdateCoordinator)
            coordinator.name = f"test_climate_{i}"
            coordinator.data = {
                "calculated_offset": 2.3 + i * 0.1,
                "learning_info": {"enabled": True, "samples": 15 + i},
                "weather_forecast": (i % 2 == 0),
                "seasonal_data": {"enabled": True, "contribution": 15.5 + i},
            }
            coordinators[f"climate.test_ac_{i}"] = coordinator
        
        mock_hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinators": coordinators
        }
        
        async_add_entities = AsyncMock()
        
        # Should not raise exceptions
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        # Should create sensors for all climate entities
        async_add_entities.assert_called_once()
        sensors = async_add_entities.call_args[0][0]
        
        # Should create 34 sensors × 3 climate entities = 102 sensors
        assert len(sensors) == 102
        
        # Verify each climate entity has its sensors
        entity_ids = set()
        for sensor in sensors:
            entity_ids.add(sensor._base_entity_id)
        
        expected_entity_ids = {"climate.test_ac_0", "climate.test_ac_1", "climate.test_ac_2"}
        assert entity_ids == expected_entity_ids


class TestSensorAvailabilityRegression:
    """Test that sensor availability continues to work correctly."""
    
    @pytest.mark.asyncio
    async def test_sensor_availability_with_caching(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test that sensor availability works correctly with caching."""
        sensor = OffsetCurrentSensor(mock_coordinator, "climate.test_ac", mock_config_entry)
        
        # Should be available with valid data
        assert sensor.available == True
        
        # Should be unavailable with None data
        mock_coordinator.data = None
        assert sensor.available == False
        
        # Should be available again with valid data
        mock_coordinator.data = {"calculated_offset": 2.5}
        assert sensor.available == True
    
    @pytest.mark.asyncio
    async def test_binary_sensor_availability_with_caching(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test that binary sensor availability works correctly with caching."""
        sensor = WeatherForecastSensor(mock_coordinator, "climate.test_ac", mock_config_entry)
        
        # Should be available with valid data
        assert sensor.available == True
        
        # Should be unavailable with None data
        mock_coordinator.data = None
        assert sensor.available == False
        
        # Should be available again with valid data
        mock_coordinator.data = {"weather_forecast": True}
        assert sensor.available == True
    
    @pytest.mark.asyncio
    async def test_sensor_with_cached_values_availability(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test that sensors with cached values handle availability correctly."""
        sensor = WeatherForecastSensor(mock_coordinator, "climate.test_ac", mock_config_entry)
        
        # Initial state - should be available
        assert sensor.available == True
        assert sensor.is_on == True
        
        # Cache the value
        sensor._last_known_value = True
        
        # Remove coordinator data - should still be available due to cache
        mock_coordinator.data = None
        assert sensor.available == False  # Availability depends on coordinator data
        assert sensor.is_on == True  # But cached value should still be returned
        
        # Restore coordinator data - should be available again
        mock_coordinator.data = {"weather_forecast": False}
        assert sensor.available == True
        assert sensor.is_on == False
        assert sensor._last_known_value == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])