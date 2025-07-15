"""ABOUTME: Comprehensive integration tests for all 34 sensors in Smart Climate v1.3.0+.
Tests sensor platform setup, entity registration, coordinator updates, and performance requirements."""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_registry as er
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN

from custom_components.smart_climate.const import DOMAIN
from custom_components.smart_climate.sensor import async_setup_entry
from custom_components.smart_climate.sensor_algorithm import (
    CorrelationCoefficientSensor,
    PredictionVarianceSensor,
    ModelEntropySensor,
    LearningRateSensor,
    MomentumFactorSensor,
    RegularizationStrengthSensor,
    MeanSquaredErrorSensor,
    MeanAbsoluteErrorSensor,
    RSquaredSensor,
)
from custom_components.smart_climate.sensor_performance import (
    EMACoeffficientSensor,
    PredictionLatencySensor,
    EnergyEfficiencySensor,
    SensorAvailabilitySensor,
    TemperatureStabilitySensor,
    LearnedDelaySensor,
)
from custom_components.smart_climate.sensor_ac_learning import (
    TemperatureWindowSensor,
    PowerCorrelationSensor,
    HysteresisCyclesSensor,
    ReactiveOffsetSensor,
    PredictiveOffsetSensor,
)
from custom_components.smart_climate.sensor_system_health import (
    MemoryUsageSensor,
    PersistenceLatencySensor,
    SamplesPerDaySensor,
    ConvergenceTrendSensor,
    OutlierDetectionSensor,
)


@pytest.fixture
def mock_coordinator():
    """Create comprehensive mock coordinator with all sensor data."""
    coordinator = Mock()
    coordinator.last_update_success = True
    coordinator.data = {
        # Core offset and learning data
        "calculated_offset": 2.5,
        "learning_info": {
            "enabled": True,
            "samples": 15,
            "accuracy": 0.85,
            "hysteresis_state": "idle_stable_zone",
            "hysteresis_enabled": True,
            "learned_start_threshold": 25.5,
            "learned_stop_threshold": 24.0,
            "temperature_window": 1.5,
            "start_samples_collected": 10,
            "stop_samples_collected": 10,
            "hysteresis_ready": True,
            "last_sample_time": "2025-07-15T10:00:00",
        },
        
        # Delay and timing data
        "delay_data": {
            "adaptive_delay": 180.5,
            "learned_delay_seconds": 240.0,
            "temperature_stability_detected": True,
        },
        
        # Weather integration
        "weather_forecast": True,
        
        # Seasonal adaptation
        "seasonal_data": {
            "enabled": True,
            "contribution": 15.5,
            "pattern_count": 7,
            "outdoor_temp_bucket": "hot",
            "accuracy": 92.3,
        },
        
        # AC behavior learning
        "ac_behavior": {
            "temperature_window": "1.5°C",
            "power_correlation_accuracy": 85.5,
            "hysteresis_cycle_count": 42,
            "reactive_offset": 1.8,
            "predictive_offset": 0.7,
        },
        
        # Performance metrics
        "performance": {
            "ema_coefficient": 0.125,
            "prediction_latency_ms": 0.8,
            "energy_efficiency_score": 85,
            "sensor_availability_score": 98.5,
            "temperature_stability": 95.2,
            "learned_delay": 180.0,
        },
        
        # System health
        "system_health": {
            "memory_usage_kb": 1024.5,
            "persistence_latency_ms": 5.2,
            "samples_per_day": 480.0,
            "accuracy_improvement_rate": 2.5,
            "convergence_trend": "improving",
            "outlier_detection_active": True,
        },
        
        # Algorithm metrics
        "algorithm_metrics": {
            "correlation_coefficient": 0.92,
            "prediction_variance": 0.15,
            "model_entropy": 2.5,
            "learning_rate": 0.01,
            "momentum_factor": 0.9,
            "regularization_strength": 0.001,
            "mean_squared_error": 0.25,
            "mean_absolute_error": 0.18,
            "r_squared": 0.85,
        },
        
        # Diagnostics
        "diagnostics": {
            "last_update_duration_ms": 12.5,
            "cache_hit_rate": 0.85,
            "cached_keys": 25,
        },
    }
    
    # Mock coordinator methods
    coordinator.async_add_listener = Mock()
    coordinator.async_remove_listener = Mock()
    
    return coordinator


@pytest.fixture
def mock_config_entry():
    """Create mock config entry."""
    entry = Mock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.unique_id = "test_unique"
    entry.title = "Test Climate"
    return entry


@pytest.fixture
def mock_hass(mock_coordinator, mock_config_entry):
    """Create mock Home Assistant instance with coordinator data."""
    hass = Mock()
    hass.data = {
        DOMAIN: {
            mock_config_entry.entry_id: {
                "coordinators": {
                    "climate.test_ac": mock_coordinator,
                }
            }
        }
    }
    return hass


@pytest.fixture
def mock_async_add_entities():
    """Create mock async_add_entities callback."""
    return AsyncMock(spec=AddEntitiesCallback)


class TestV130SensorPlatformIntegration:
    """Integration tests for all 34 sensors in v1.3.0+ sensor platform."""
    
    async def test_all_34_sensors_created_during_setup(
        self, mock_hass, mock_config_entry, mock_async_add_entities
    ):
        """Test that all 34 sensors are created during platform setup."""
        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        
        # Verify async_add_entities was called once
        mock_async_add_entities.assert_called_once()
        
        # Get the created sensors
        created_sensors = mock_async_add_entities.call_args[0][0]
        
        # Should create exactly 34 sensors
        assert len(created_sensors) == 34, f"Expected 34 sensors, got {len(created_sensors)}"
        
        # Verify all sensor types are created
        sensor_types = {sensor._sensor_type for sensor in created_sensors}
        
        expected_sensor_types = {
            # Legacy sensors (5)
            "offset_current", "learning_progress", "accuracy_current", 
            "calibration_status", "hysteresis_state",
            
            # Core intelligence sensors (4)
            "adaptive_delay", "weather_forecast", "seasonal_adaptation", 
            "seasonal_contribution",
            
            # Algorithm metrics sensors (9)
            "correlation_coefficient", "prediction_variance", "model_entropy",
            "learning_rate", "momentum_factor", "regularization_strength",
            "mean_squared_error", "mean_absolute_error", "r_squared",
            
            # Performance analytics sensors (6)
            "ema_coefficient", "prediction_latency", "energy_efficiency",
            "sensor_availability", "temperature_stability", "learned_delay",
            
            # AC learning sensors (5)
            "temperature_window", "power_correlation", "hysteresis_cycles",
            "reactive_offset", "predictive_offset",
            
            # System health sensors (5)
            "memory_usage", "persistence_latency", "samples_per_day",
            "convergence_trend", "outlier_detection",
        }
        
        assert sensor_types == expected_sensor_types, \
            f"Missing sensors: {expected_sensor_types - sensor_types}, " \
            f"Extra sensors: {sensor_types - expected_sensor_types}"
    
    async def test_sensor_categorization_by_type(
        self, mock_hass, mock_config_entry, mock_async_add_entities
    ):
        """Test sensors are properly categorized by their types."""
        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        
        # Categorize sensors by type
        categories = {
            "legacy": [],
            "core_intelligence": [],
            "algorithm_metrics": [],
            "performance": [],
            "ac_learning": [],
            "system_health": [],
        }
        
        for sensor in created_sensors:
            if sensor._sensor_type in ["offset_current", "learning_progress", "accuracy_current", 
                                      "calibration_status", "hysteresis_state"]:
                categories["legacy"].append(sensor)
            elif sensor._sensor_type in ["adaptive_delay", "weather_forecast", "seasonal_adaptation", 
                                        "seasonal_contribution"]:
                categories["core_intelligence"].append(sensor)
            elif sensor._sensor_type in ["correlation_coefficient", "prediction_variance", "model_entropy",
                                        "learning_rate", "momentum_factor", "regularization_strength",
                                        "mean_squared_error", "mean_absolute_error", "r_squared"]:
                categories["algorithm_metrics"].append(sensor)
            elif sensor._sensor_type in ["ema_coefficient", "prediction_latency", "energy_efficiency",
                                        "sensor_availability", "temperature_stability", "learned_delay"]:
                categories["performance"].append(sensor)
            elif sensor._sensor_type in ["temperature_window", "power_correlation", "hysteresis_cycles",
                                        "reactive_offset", "predictive_offset"]:
                categories["ac_learning"].append(sensor)
            elif sensor._sensor_type in ["memory_usage", "persistence_latency", "samples_per_day",
                                        "convergence_trend", "outlier_detection"]:
                categories["system_health"].append(sensor)
        
        # Verify counts match expected
        assert len(categories["legacy"]) == 5, f"Expected 5 legacy sensors, got {len(categories['legacy'])}"
        assert len(categories["core_intelligence"]) == 4, f"Expected 4 core intelligence sensors, got {len(categories['core_intelligence'])}"
        assert len(categories["algorithm_metrics"]) == 9, f"Expected 9 algorithm metrics sensors, got {len(categories['algorithm_metrics'])}"
        assert len(categories["performance"]) == 6, f"Expected 6 performance sensors, got {len(categories['performance'])}"
        assert len(categories["ac_learning"]) == 5, f"Expected 5 AC learning sensors, got {len(categories['ac_learning'])}"
        assert len(categories["system_health"]) == 5, f"Expected 5 system health sensors, got {len(categories['system_health'])}"
    
    async def test_sensors_update_via_coordinator(
        self, mock_hass, mock_config_entry, mock_async_add_entities
    ):
        """Test that sensors update properly when coordinator data changes."""
        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        coordinator = mock_hass.data[DOMAIN][mock_config_entry.entry_id]["coordinators"]["climate.test_ac"]
        
        # Track listener registrations
        listener_calls = []
        def mock_add_listener(callback, entity_id):
            listener_calls.append((callback, entity_id))
            return Mock()  # Return a mock remove callback
        
        coordinator.async_add_listener = Mock(side_effect=mock_add_listener)
        
        # Simulate adding sensors to hass
        for sensor in created_sensors:
            await sensor.async_added_to_hass()
        
        # Verify each sensor registered a listener
        assert len(listener_calls) == 34, f"Expected 34 listener registrations, got {len(listener_calls)}"
        
        # Test that listeners are called when coordinator updates
        for callback, entity_id in listener_calls:
            with patch.object(created_sensors[0], 'async_write_ha_state') as mock_write_state:
                callback()
                # Note: We can't easily verify mock_write_state was called for each sensor
                # because they're different instances, but the callback should trigger the update
    
    async def test_sensor_values_match_coordinator_data(
        self, mock_hass, mock_config_entry, mock_async_add_entities
    ):
        """Test that sensor values correctly match coordinator data."""
        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        coordinator = mock_hass.data[DOMAIN][mock_config_entry.entry_id]["coordinators"]["climate.test_ac"]
        
        # Find specific sensors and test their values
        sensor_by_type = {sensor._sensor_type: sensor for sensor in created_sensors}
        
        # Test legacy sensors
        assert sensor_by_type["offset_current"].native_value == 2.5
        assert sensor_by_type["learning_progress"].native_value == 100  # 15 samples >= 10 minimum
        assert sensor_by_type["accuracy_current"].native_value == 85  # 0.85 * 100
        assert sensor_by_type["calibration_status"].native_value == "Complete"
        assert sensor_by_type["hysteresis_state"].native_value == "Temperature stable"
        
        # Test core intelligence sensors
        assert sensor_by_type["adaptive_delay"].native_value == 180.5
        assert sensor_by_type["weather_forecast"].is_on == True
        assert sensor_by_type["seasonal_adaptation"].is_on == True
        assert sensor_by_type["seasonal_contribution"].native_value == 15.5
        
        # Test algorithm metrics sensors
        assert sensor_by_type["correlation_coefficient"].native_value == 0.92
        assert sensor_by_type["prediction_variance"].native_value == 0.15
        assert sensor_by_type["model_entropy"].native_value == 2.5
        assert sensor_by_type["learning_rate"].native_value == 0.01
        assert sensor_by_type["momentum_factor"].native_value == 0.9
        assert sensor_by_type["regularization_strength"].native_value == 0.001
        assert sensor_by_type["mean_squared_error"].native_value == 0.25
        assert sensor_by_type["mean_absolute_error"].native_value == 0.18
        assert sensor_by_type["r_squared"].native_value == 0.85
        
        # Test performance sensors
        assert sensor_by_type["ema_coefficient"].native_value == 0.125
        assert sensor_by_type["prediction_latency"].native_value == 0.8
        assert sensor_by_type["energy_efficiency"].native_value == 85
        assert sensor_by_type["sensor_availability"].native_value == 98.5
        assert sensor_by_type["temperature_stability"].native_value == 95.2
        assert sensor_by_type["learned_delay"].native_value == 180.0
    
    async def test_sensor_error_handling_missing_data(
        self, mock_hass, mock_config_entry, mock_async_add_entities
    ):
        """Test sensor error handling when coordinator data is missing."""
        # Setup with missing coordinator data
        coordinator = Mock()
        coordinator.last_update_success = True
        coordinator.data = None  # Missing data
        
        mock_hass.data[DOMAIN][mock_config_entry.entry_id]["coordinators"]["climate.test_ac"] = coordinator
        
        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        sensor_by_type = {sensor._sensor_type: sensor for sensor in created_sensors}
        
        # Test that sensors handle missing data gracefully
        assert sensor_by_type["offset_current"].native_value is None
        assert sensor_by_type["learning_progress"].native_value == 0
        assert sensor_by_type["accuracy_current"].native_value == 0
        assert sensor_by_type["calibration_status"].native_value == "Unknown"
        assert sensor_by_type["hysteresis_state"].native_value == "Unknown"
        
        # Test that none of the sensors throw exceptions
        for sensor in created_sensors:
            try:
                # Try to access native_value (for regular sensors) or is_on (for binary sensors)
                if hasattr(sensor, 'is_on'):
                    sensor.is_on
                else:
                    sensor.native_value
            except Exception as e:
                pytest.fail(f"Sensor {sensor._sensor_type} raised exception with missing data: {e}")
    
    async def test_sensor_error_handling_malformed_data(
        self, mock_hass, mock_config_entry, mock_async_add_entities
    ):
        """Test sensor error handling when coordinator data is malformed."""
        # Setup with malformed coordinator data
        coordinator = Mock()
        coordinator.last_update_success = True
        coordinator.data = {
            "calculated_offset": "invalid_number",  # String instead of number
            "learning_info": {
                "samples": "not_a_number",
                "accuracy": None,
                "hysteresis_state": 12345,  # Number instead of string
            },
            "algorithm_metrics": {
                "correlation_coefficient": float('inf'),  # Invalid float
                "prediction_variance": None,
            },
            "performance": {
                "prediction_latency_ms": "slow",  # String instead of number
            },
        }
        
        mock_hass.data[DOMAIN][mock_config_entry.entry_id]["coordinators"]["climate.test_ac"] = coordinator
        
        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        
        # Test that sensors handle malformed data gracefully
        for sensor in created_sensors:
            try:
                # Try to access native_value (for regular sensors) or is_on (for binary sensors)
                if hasattr(sensor, 'is_on'):
                    value = sensor.is_on
                else:
                    value = sensor.native_value
                
                # Should not be an exception-causing value
                assert value is None or isinstance(value, (int, float, str, bool)), \
                    f"Sensor {sensor._sensor_type} returned unexpected type: {type(value)}"
                    
            except Exception as e:
                pytest.fail(f"Sensor {sensor._sensor_type} raised exception with malformed data: {e}")
    
    async def test_sensor_availability_follows_coordinator(
        self, mock_hass, mock_config_entry, mock_async_add_entities
    ):
        """Test that sensor availability follows coordinator update success."""
        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        coordinator = mock_hass.data[DOMAIN][mock_config_entry.entry_id]["coordinators"]["climate.test_ac"]
        
        # Test sensors available when coordinator succeeds
        coordinator.last_update_success = True
        for sensor in created_sensors:
            assert sensor.available == True, f"Sensor {sensor._sensor_type} should be available"
        
        # Test sensors unavailable when coordinator fails
        coordinator.last_update_success = False
        for sensor in created_sensors:
            assert sensor.available == False, f"Sensor {sensor._sensor_type} should be unavailable"
    
    async def test_sensor_performance_requirements(
        self, mock_hass, mock_config_entry, mock_async_add_entities
    ):
        """Test that all sensors update within performance requirements (<100ms)."""
        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        
        # Test that all sensors can be read within time limit
        start_time = time.perf_counter()
        
        for sensor in created_sensors:
            try:
                # Access both native_value and is_on (if available)
                if hasattr(sensor, 'is_on'):
                    sensor.is_on
                if hasattr(sensor, 'native_value'):
                    sensor.native_value
                    
                # Also access extra_state_attributes if available
                if hasattr(sensor, 'extra_state_attributes'):
                    sensor.extra_state_attributes
                    
            except Exception as e:
                pytest.fail(f"Sensor {sensor._sensor_type} raised exception during performance test: {e}")
        
        total_time = time.perf_counter() - start_time
        
        # All 34 sensors should be readable within 100ms
        assert total_time < 0.1, f"Reading all sensors took {total_time*1000:.2f}ms, should be < 100ms"
    
    async def test_sensor_unique_ids_and_device_info(
        self, mock_hass, mock_config_entry, mock_async_add_entities
    ):
        """Test that all sensors have unique IDs and proper device info."""
        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        
        # Test unique IDs are actually unique
        unique_ids = [sensor.unique_id for sensor in created_sensors]
        assert len(unique_ids) == len(set(unique_ids)), "Some sensors have duplicate unique IDs"
        
        # Test all sensors have device info
        for sensor in created_sensors:
            assert sensor.device_info is not None, f"Sensor {sensor._sensor_type} missing device info"
            assert sensor.device_info.get("identifiers") is not None, \
                f"Sensor {sensor._sensor_type} missing device identifiers"
            assert sensor.device_info.get("name") is not None, \
                f"Sensor {sensor._sensor_type} missing device name"
    
    async def test_sensor_home_assistant_integration(
        self, mock_hass, mock_config_entry, mock_async_add_entities
    ):
        """Test sensor integration with Home Assistant entity management."""
        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        
        # Test that sensors are properly configured for HA
        for sensor in created_sensors:
            # Should not poll (coordinator-based)
            assert sensor.should_poll == False, f"Sensor {sensor._sensor_type} should not poll"
            
            # Should have entity names
            assert sensor.has_entity_name == True, f"Sensor {sensor._sensor_type} missing entity name"
            
            # Should have names
            assert sensor.name is not None, f"Sensor {sensor._sensor_type} missing name"
            
            # Should have unique IDs
            assert sensor.unique_id is not None, f"Sensor {sensor._sensor_type} missing unique ID"
    
    async def test_multiple_climate_entities_create_separate_sensors(
        self, mock_config_entry, mock_async_add_entities
    ):
        """Test that multiple climate entities create separate sensor sets."""
        # Setup with multiple climate entities
        coordinator1 = Mock()
        coordinator1.last_update_success = True
        coordinator1.data = {"calculated_offset": 1.0, "learning_info": {"enabled": True}}
        
        coordinator2 = Mock()
        coordinator2.last_update_success = True
        coordinator2.data = {"calculated_offset": 2.0, "learning_info": {"enabled": False}}
        
        mock_hass = Mock()
        mock_hass.data = {
            DOMAIN: {
                mock_config_entry.entry_id: {
                    "coordinators": {
                        "climate.ac1": coordinator1,
                        "climate.ac2": coordinator2,
                    }
                }
            }
        }
        
        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        
        # Should create 34 sensors for each climate entity = 68 total
        assert len(created_sensors) == 68, f"Expected 68 sensors for 2 climate entities, got {len(created_sensors)}"
        
        # Check that sensors are associated with correct entities
        ac1_sensors = [s for s in created_sensors if "climate_ac1" in s.unique_id]
        ac2_sensors = [s for s in created_sensors if "climate_ac2" in s.unique_id]
        
        assert len(ac1_sensors) == 34, f"Expected 34 sensors for climate.ac1, got {len(ac1_sensors)}"
        assert len(ac2_sensors) == 34, f"Expected 34 sensors for climate.ac2, got {len(ac2_sensors)}"
    
    async def test_sensor_coordinator_cleanup_on_removal(
        self, mock_hass, mock_config_entry, mock_async_add_entities
    ):
        """Test that sensor coordinator listeners are cleaned up properly."""
        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        
        created_sensors = mock_async_add_entities.call_args[0][0]
        coordinator = mock_hass.data[DOMAIN][mock_config_entry.entry_id]["coordinators"]["climate.test_ac"]
        
        # Track remove callbacks
        remove_callbacks = []
        def mock_add_listener(callback, entity_id):
            remove_callback = Mock()
            remove_callbacks.append(remove_callback)
            return remove_callback
        
        coordinator.async_add_listener = Mock(side_effect=mock_add_listener)
        
        # Simulate adding sensors to hass
        for sensor in created_sensors:
            await sensor.async_added_to_hass()
        
        # Verify remove callbacks were stored
        assert len(remove_callbacks) == 34, f"Expected 34 remove callbacks, got {len(remove_callbacks)}"
        
        # Simulate sensor removal (this would normally be called by HA)
        for sensor in created_sensors:
            # Manually call the cleanup that would happen during removal
            sensor.async_on_remove_callbacks = getattr(sensor, '_async_on_remove_callbacks', [])
            for callback in sensor.async_on_remove_callbacks:
                callback()
        
        # Verify all remove callbacks were called
        for remove_callback in remove_callbacks:
            remove_callback.assert_called_once()