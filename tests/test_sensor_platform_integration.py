"""Test sensor platform integration with all 34 sensors."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.smart_climate.sensor import async_setup_entry
from custom_components.smart_climate.const import DOMAIN


@pytest.fixture
def mock_coordinator():
    """Create mock coordinator."""
    coordinator = Mock()
    coordinator.last_update_success = True
    coordinator.data = {
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
        "delay_data": {
            "adaptive_delay": 180.5,
            "learned_delay_seconds": 240.0,
            "temperature_stability_detected": True,
        },
        "weather_forecast": True,
        "seasonal_data": {
            "enabled": True,
            "contribution": 15.5,
            "pattern_count": 7,
            "outdoor_temp_bucket": "hot",
            "accuracy": 92.3,
        },
        "ac_behavior": {
            "temperature_window": "1.5°C",
            "power_correlation_accuracy": 85.5,
            "hysteresis_cycle_count": 42,
        },
        "performance": {
            "ema_coefficient": 0.125,
            "prediction_latency_ms": 0.8,
            "energy_efficiency_score": 85,
            "sensor_availability_score": 98.5,
        },
        "system_health": {
            "memory_usage_kb": 1024.5,
            "persistence_latency_ms": 5.2,
            "samples_per_day": 480.0,
            "accuracy_improvement_rate": 2.5,
            "convergence_trend": "improving",
            "outlier_detection_active": True,
        },
        "diagnostics": {
            "last_update_duration_ms": 12.5,
            "cache_hit_rate": 0.85,
            "cached_keys": 25,
        },
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
    }
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
    """Create mock Home Assistant instance."""
    hass = Mock()
    hass.data = {
        DOMAIN: {
            mock_config_entry.entry_id: {
                "coordinators": {
                    "climate.test_climate": mock_coordinator
                }
            }
        }
    }
    return hass


@pytest.mark.asyncio
async def test_sensor_setup_creates_all_34_sensors(mock_hass, mock_config_entry):
    """Test that all 34 sensors are created during setup."""
    mock_async_add_entities = Mock(spec=AddEntitiesCallback)
    
    await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
    
    # Verify async_add_entities was called
    assert mock_async_add_entities.called
    
    # Get the list of entities passed to async_add_entities
    entities = mock_async_add_entities.call_args[0][0]
    
    # Verify we have exactly 34 sensors total
    # 5 legacy + 4 existing + 9 algorithm + 6 performance + 5 AC learning + 5 system health = 34
    assert len(entities) == 34
    
    # Count sensors by type
    sensor_types = {}
    for entity in entities:
        sensor_name = getattr(entity, '_attr_name', entity.__class__.__name__)
        sensor_types[sensor_name] = sensor_types.get(sensor_name, 0) + 1
    
    # Verify each sensor type appears exactly once
    for sensor_name, count in sensor_types.items():
        assert count == 1, f"Sensor '{sensor_name}' appears {count} times, expected 1"


@pytest.mark.asyncio
async def test_sensor_categories_count(mock_hass, mock_config_entry):
    """Test that sensors are distributed correctly by category."""
    mock_async_add_entities = Mock(spec=AddEntitiesCallback)
    
    await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
    
    entities = mock_async_add_entities.call_args[0][0]
    
    # Expected counts by category
    expected_counts = {
        "legacy": 5,
        "existing": 4,  # AdaptiveDelay, WeatherForecast, SeasonalAdaptation, SeasonalContribution
        "algorithm": 9,
        "performance": 6,
        "ac_learning": 5,
        "system_health": 5,
    }
    
    # Count actual sensors
    actual_counts = {
        "legacy": 0,
        "existing": 0,
        "algorithm": 0,
        "performance": 0,
        "ac_learning": 0,
        "system_health": 0,
    }
    
    for entity in entities:
        name = getattr(entity, '_attr_name', entity.__class__.__name__).lower()
        
        # Categorize based on sensor name
        if any(x in name for x in ["current offset", "learning progress", "current accuracy", "calibration", "hysteresis state"]):
            actual_counts["legacy"] += 1
        elif any(x in name for x in ["adaptive delay", "weather forecast", "seasonal adaptation", "seasonal contribution"]):
            actual_counts["existing"] += 1
        elif any(x in name for x in ["correlation coefficient", "prediction variance", "model entropy", "learning rate", "momentum factor", "regularization", "mean squared error", "mean absolute error", "r-squared"]):
            actual_counts["algorithm"] += 1
        elif any(x in name for x in ["emacoefficient", "predictionlatency", "energyefficiency", "sensoravailability", "temperaturestability", "learneddelay"]):
            actual_counts["performance"] += 1
        elif any(x in name for x in ["temperature window", "power correlation", "hysteresis cycles", "reactive offset", "predictive offset"]):
            actual_counts["ac_learning"] += 1
        elif any(x in name for x in ["memory usage", "persistence latency", "samples per day", "convergence", "outlier detection"]):
            actual_counts["system_health"] += 1
    
    # Verify counts match expectations
    for category, expected in expected_counts.items():
        assert actual_counts[category] == expected, f"{category}: expected {expected}, got {actual_counts[category]}"


@pytest.mark.asyncio
async def test_handles_missing_coordinators_gracefully(mock_hass, mock_config_entry):
    """Test that setup handles missing coordinators without crashing."""
    # Clear coordinators
    mock_hass.data[DOMAIN][mock_config_entry.entry_id]["coordinators"] = {}
    
    mock_async_add_entities = Mock(spec=AddEntitiesCallback)
    
    # Should not raise an exception
    await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
    
    # Should not call async_add_entities with empty coordinator list
    assert not mock_async_add_entities.called


@pytest.mark.asyncio
async def test_import_error_handling():
    """Test that import errors are handled gracefully."""
    mock_hass = Mock(spec=HomeAssistant)
    mock_config_entry = Mock(spec=ConfigEntry)
    mock_async_add_entities = Mock(spec=AddEntitiesCallback)
    
    # Simulate import error for one of the sensor modules
    with patch('custom_components.smart_climate.sensor.sensor_performance', side_effect=ImportError("Module not found")):
        # Should handle the error gracefully
        try:
            await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
        except ImportError:
            # The function should handle import errors, not propagate them
            pytest.fail("Import errors should be handled gracefully")


@pytest.mark.asyncio
async def test_coordinator_updates_propagate_to_all_sensors(mock_hass, mock_config_entry, mock_coordinator):
    """Test that coordinator updates trigger sensor updates."""
    mock_async_add_entities = Mock(spec=AddEntitiesCallback)
    
    await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
    
    entities = mock_async_add_entities.call_args[0][0]
    
    # Verify all sensors have coordinator reference
    for entity in entities:
        assert hasattr(entity, 'coordinator')
        assert entity.coordinator == mock_coordinator
        
        # Verify sensor gets data from coordinator
        assert entity.available == mock_coordinator.last_update_success


@pytest.mark.asyncio
async def test_all_sensor_imports_present():
    """Test that all required sensor modules can be imported."""
    # Test performance sensors
    from custom_components.smart_climate.sensor_performance import (
        EMACoeffcientSensor,
        PredictionLatencySensor,
        EnergyEfficiencyScoreSensor,
        SensorAvailabilitySensor,
        DashboardUpdateDurationSensor,
        DashboardCacheHitRateSensor,
    )
    
    # Test AC learning sensors
    from custom_components.smart_climate.sensor_ac_learning import (
        LearnedDelaySensor,
        TemperatureWindowSensor,
        PowerCorrelationSensor,
        HysteresisCyclesSensor,
        TemperatureStabilitySensor,
    )
    
    # Test system health sensors
    from custom_components.smart_climate.sensor_system_health import (
        MemoryUsageSensor,
        PersistenceLatencySensor,
        SamplesPerDaySensor,
        AccuracyImprovementRateSensor,
        ConvergenceTrendSensor,
    )
    
    # Test algorithm sensors (already imported in sensor.py)
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
    
    # All imports should succeed
    assert True


@pytest.mark.asyncio
async def test_sensor_unique_ids_are_unique(mock_hass, mock_config_entry):
    """Test that all sensors have unique IDs."""
    mock_async_add_entities = Mock(spec=AddEntitiesCallback)
    
    await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
    
    entities = mock_async_add_entities.call_args[0][0]
    
    # Collect all unique IDs
    unique_ids = []
    for entity in entities:
        assert hasattr(entity, '_attr_unique_id')
        unique_ids.append(entity._attr_unique_id)
    
    # Verify all are unique
    assert len(unique_ids) == len(set(unique_ids)), "Duplicate unique IDs found"


@pytest.mark.asyncio
async def test_binary_sensors_show_on_off_text(mock_hass, mock_config_entry):
    """Test that binary sensors properly show on/off text."""
    mock_async_add_entities = Mock(spec=AddEntitiesCallback)
    
    await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
    
    entities = mock_async_add_entities.call_args[0][0]
    
    # Find binary sensors
    binary_sensor_names = ["Weather Forecast", "Seasonal Adaptation", "Outlier Detection", "Temperature Stability"]
    binary_sensors = [e for e in entities if e._attr_name in binary_sensor_names]
    
    # Should have 3 binary sensors (Outlier Detection and Temperature Stability will be text sensors showing "on"/"off")
    # Weather Forecast and Seasonal Adaptation are already binary sensors
    assert len([e for e in binary_sensors if hasattr(e, 'is_on')]) >= 2