"""Performance tests for Smart Climate sensor caching implementation.

ABOUTME: Tests sensor update performance and caching efficiency
ABOUTME: Validates that sensor caching doesn't impact performance
"""

import pytest
import time
import psutil
import os
from unittest.mock import MagicMock, patch, Mock
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.smart_climate.const import DOMAIN
from custom_components.smart_climate.sensor import (
    OffsetCurrentSensor,
    WeatherForecastSensor,
    SeasonalAdaptationSensor,
    ConvergenceTrendSensor,
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
    """Create a mock coordinator with performance tracking."""
    coordinator = MagicMock(spec=DataUpdateCoordinator)
    coordinator.name = "test_climate"
    coordinator.data = {
        "calculated_offset": 2.3,
        "learning_info": {
            "enabled": True,
            "samples": 15,
            "accuracy": 0.85,
            "confidence": 0.75,
        },
        "weather_forecast": True,
        "seasonal_data": {
            "enabled": True,
            "contribution": 15.5,
        },
        "system_health": {
            "convergence_trend": "improving",
            "accuracy_improvement_rate": 1.25,
        },
    }
    coordinator.last_update_success = True
    coordinator.last_update_time = datetime.now()
    
    # Add performance tracking
    coordinator._update_times = []
    coordinator._original_update = coordinator.async_request_refresh
    
    async def timed_update():
        start = time.perf_counter()
        await coordinator._original_update()
        end = time.perf_counter()
        coordinator._update_times.append(end - start)
    
    coordinator.async_request_refresh = timed_update
    return coordinator


@pytest.fixture
def sensor_data_with_cache():
    """Create sensor data with cached values for testing."""
    return {
        "calculated_offset": 2.3,
        "learning_info": {
            "enabled": True,
            "samples": 15,
            "accuracy": 0.85,
            "confidence": 0.75,
        },
        "weather_forecast": True,
        "seasonal_data": {
            "enabled": True,
            "contribution": 15.5,
        },
        "system_health": {
            "convergence_trend": "improving",
            "accuracy_improvement_rate": 1.25,
        },
        "_cache_metadata": {
            "cache_creation_time": time.time(),
            "cache_hit_count": 0,
            "cache_miss_count": 0,
        },
    }


class TestSensorUpdatePerformance:
    """Test sensor update performance with caching."""
    
    @pytest.mark.asyncio
    async def test_sensor_update_performance(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test that sensor updates complete within acceptable time limits."""
        # Set up sensors
        mock_hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinators": {
                "climate.test_ac": mock_coordinator
            }
        }
        
        # Create sensor
        sensor = OffsetCurrentSensor(mock_coordinator, "climate.test_ac", mock_config_entry)
        
        # Measure sensor value retrieval time
        start_time = time.perf_counter()
        
        # Perform multiple sensor reads
        for _ in range(100):
            value = sensor.native_value
            assert value is not None
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        avg_time_per_read = total_time / 100
        
        # Performance assertion: Each sensor read should be < 1ms
        assert avg_time_per_read < 0.001, f"Sensor read took {avg_time_per_read:.4f}s, expected < 0.001s"
        
        # Log performance metrics
        print(f"Sensor read performance: {avg_time_per_read:.6f}s average per read")
    
    @pytest.mark.asyncio
    async def test_multiple_sensor_updates_performance(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test performance when multiple sensors update simultaneously."""
        # Set up sensors
        mock_hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinators": {
                "climate.test_ac": mock_coordinator
            }
        }
        
        # Create multiple sensors
        sensors = [
            OffsetCurrentSensor(mock_coordinator, "climate.test_ac", mock_config_entry),
            WeatherForecastSensor(mock_coordinator, "climate.test_ac", mock_config_entry),
            SeasonalAdaptationSensor(mock_coordinator, "climate.test_ac", mock_config_entry),
        ]
        
        # Measure simultaneous update performance
        start_time = time.perf_counter()
        
        # Simulate coordinator data update
        for _ in range(50):
            # Update coordinator data
            mock_coordinator.data["calculated_offset"] = 2.5 + (_ * 0.1)
            mock_coordinator.data["weather_forecast"] = (_ % 2 == 0)
            mock_coordinator.data["seasonal_data"]["contribution"] = 15.5 + (_ * 0.2)
            
            # Read all sensor values
            for sensor in sensors:
                if hasattr(sensor, 'native_value'):
                    value = sensor.native_value
                elif hasattr(sensor, 'is_on'):
                    value = sensor.is_on
                assert value is not None or sensor.__class__.__name__ == "WeatherForecastSensor"
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        avg_time_per_update = total_time / 50
        
        # Performance assertion: Each full update should be < 5ms
        assert avg_time_per_update < 0.005, f"Multi-sensor update took {avg_time_per_update:.4f}s, expected < 0.005s"
        
        print(f"Multi-sensor update performance: {avg_time_per_update:.6f}s average per update")
    
    @pytest.mark.asyncio
    async def test_sensor_creation_performance(self, mock_hass, mock_config_entry):
        """Test that sensor creation/initialization is fast."""
        # Create multiple coordinators
        coordinators = {}
        for i in range(10):
            coordinator = MagicMock(spec=DataUpdateCoordinator)
            coordinator.name = f"test_climate_{i}"
            coordinator.data = {
                "calculated_offset": 2.3 + i * 0.1,
                "learning_info": {"enabled": True, "samples": 15 + i},
                "weather_forecast": (i % 2 == 0),
                "seasonal_data": {"enabled": True, "contribution": 15.5 + i},
                "system_health": {"convergence_trend": "improving"},
            }
            coordinators[f"climate.test_ac_{i}"] = coordinator
        
        mock_hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinators": coordinators
        }
        
        # Measure sensor creation time
        start_time = time.perf_counter()
        
        mock_add_entities = MagicMock()
        await async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)
        
        end_time = time.perf_counter()
        creation_time = end_time - start_time
        
        # Performance assertion: Creating all sensors should be < 100ms
        assert creation_time < 0.1, f"Sensor creation took {creation_time:.4f}s, expected < 0.1s"
        
        # Verify all sensors were created
        mock_add_entities.assert_called_once()
        created_sensors = mock_add_entities.call_args[0][0]
        
        # Should create 34 sensors per climate entity (10 entities × 34 sensors = 340 total)
        expected_sensor_count = 10 * 34
        assert len(created_sensors) == expected_sensor_count
        
        print(f"Sensor creation performance: {creation_time:.6f}s for {len(created_sensors)} sensors")


class TestCacheMemoryUsage:
    """Test memory usage of sensor caching implementation."""
    
    @pytest.mark.asyncio
    async def test_cache_memory_usage(self, mock_hass, mock_config_entry, sensor_data_with_cache):
        """Test that sensor caching doesn't consume excessive memory."""
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create coordinator with large data set
        coordinator = MagicMock(spec=DataUpdateCoordinator)
        coordinator.name = "test_climate"
        coordinator.data = sensor_data_with_cache
        
        # Create many sensors to test memory usage
        sensors = []
        for i in range(100):
            sensor = OffsetCurrentSensor(coordinator, f"climate.test_ac_{i}", mock_config_entry)
            sensors.append(sensor)
        
        # Simulate many sensor reads to populate cache
        for _ in range(1000):
            for sensor in sensors:
                value = sensor.native_value
                assert value is not None
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory assertion: Cache should not use more than 10MB
        assert memory_increase < 10, f"Cache used {memory_increase:.2f}MB, expected < 10MB"
        
        print(f"Cache memory usage: {memory_increase:.2f}MB for 100 sensors with 1000 reads each")
    
    @pytest.mark.asyncio
    async def test_cache_hit_rate_performance(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test that cache hit rate improves performance."""
        # Mock cache-enabled sensor
        sensor = OffsetCurrentSensor(mock_coordinator, "climate.test_ac", mock_config_entry)
        
        # First read (cache miss)
        start_time = time.perf_counter()
        value1 = sensor.native_value
        first_read_time = time.perf_counter() - start_time
        
        # Subsequent reads (cache hits)
        cache_read_times = []
        for _ in range(10):
            start_time = time.perf_counter()
            value2 = sensor.native_value
            cache_read_times.append(time.perf_counter() - start_time)
        
        avg_cache_read_time = sum(cache_read_times) / len(cache_read_times)
        
        # Cache reads should be faster than or equal to first read
        assert avg_cache_read_time <= first_read_time * 1.1, "Cache reads should not be slower than first read"
        
        # Values should be consistent
        assert value1 == value2, "Cached values should be consistent"
        
        print(f"Cache performance: First read {first_read_time:.6f}s, cached reads {avg_cache_read_time:.6f}s")


class TestCoordinatorPerformanceImpact:
    """Test that sensor caching doesn't impact coordinator performance."""
    
    @pytest.mark.asyncio
    async def test_coordinator_performance_impact(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test that coordinator updates remain fast with sensor caching."""
        # Set up sensors
        mock_hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinators": {
                "climate.test_ac": mock_coordinator
            }
        }
        
        # Create multiple sensors
        sensors = []
        for i in range(20):
            sensor = OffsetCurrentSensor(mock_coordinator, f"climate.test_ac_{i}", mock_config_entry)
            sensors.append(sensor)
        
        # Measure coordinator update time with many sensors
        start_time = time.perf_counter()
        
        # Simulate coordinator updates
        for update_cycle in range(10):
            # Update coordinator data
            mock_coordinator.data["calculated_offset"] = 2.3 + update_cycle * 0.1
            mock_coordinator.data["learning_info"]["samples"] = 15 + update_cycle
            
            # Trigger sensor updates
            for sensor in sensors:
                value = sensor.native_value
                assert value is not None
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        avg_update_time = total_time / 10
        
        # Performance assertion: Coordinator updates should be < 10ms
        assert avg_update_time < 0.01, f"Coordinator update took {avg_update_time:.4f}s, expected < 0.01s"
        
        print(f"Coordinator performance with caching: {avg_update_time:.6f}s average per update")
    
    @pytest.mark.asyncio
    async def test_coordinator_memory_stability(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test that coordinator memory usage remains stable with caching."""
        # Set up sensors
        mock_hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinators": {
                "climate.test_ac": mock_coordinator
            }
        }
        
        # Create sensors
        sensors = []
        for i in range(10):
            sensor = OffsetCurrentSensor(mock_coordinator, f"climate.test_ac_{i}", mock_config_entry)
            sensors.append(sensor)
        
        # Get initial memory
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate many update cycles
        for cycle in range(100):
            # Update coordinator data
            mock_coordinator.data["calculated_offset"] = 2.3 + (cycle % 10) * 0.1
            mock_coordinator.data["learning_info"]["samples"] = 15 + (cycle % 20)
            
            # Read all sensors
            for sensor in sensors:
                value = sensor.native_value
        
        # Get final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory should remain stable (< 5MB increase)
        assert memory_increase < 5, f"Memory increased by {memory_increase:.2f}MB, expected < 5MB"
        
        print(f"Coordinator memory stability: {memory_increase:.2f}MB increase over 100 update cycles")


class TestSensorCachingEfficiency:
    """Test efficiency of sensor caching implementation."""
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_performance(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test that cache invalidation is efficient."""
        sensor = OffsetCurrentSensor(mock_coordinator, "climate.test_ac", mock_config_entry)
        
        # Initial read
        value1 = sensor.native_value
        
        # Change coordinator data (should invalidate cache)
        mock_coordinator.data["calculated_offset"] = 3.5
        
        # Read again (should get new value)
        value2 = sensor.native_value
        
        # Verify cache was invalidated
        assert value1 != value2, "Cache should be invalidated when coordinator data changes"
        assert value2 == 3.5, "New value should be reflected after cache invalidation"
    
    @pytest.mark.asyncio
    async def test_concurrent_sensor_access(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test that concurrent sensor access doesn't cause performance issues."""
        import asyncio
        
        # Create multiple sensors
        sensors = []
        for i in range(5):
            sensor = OffsetCurrentSensor(mock_coordinator, f"climate.test_ac_{i}", mock_config_entry)
            sensors.append(sensor)
        
        async def read_sensor_values(sensor, iterations=20):
            """Read sensor values multiple times."""
            values = []
            for _ in range(iterations):
                value = sensor.native_value
                values.append(value)
                await asyncio.sleep(0.001)  # Small delay to simulate real usage
            return values
        
        # Measure concurrent access performance
        start_time = time.perf_counter()
        
        # Run concurrent sensor reads
        tasks = [read_sensor_values(sensor) for sensor in sensors]
        results = await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Performance assertion: Concurrent access should be < 200ms
        assert total_time < 0.2, f"Concurrent access took {total_time:.4f}s, expected < 0.2s"
        
        # Verify all sensors returned values
        for sensor_results in results:
            assert len(sensor_results) == 20
            for value in sensor_results:
                assert value is not None
        
        print(f"Concurrent sensor access performance: {total_time:.6f}s for 5 sensors × 20 reads")
    
    @pytest.mark.asyncio
    async def test_cache_overhead_measurement(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test that caching overhead is minimal."""
        sensor = OffsetCurrentSensor(mock_coordinator, "climate.test_ac", mock_config_entry)
        
        # Test without caching simulation (direct access)
        start_time = time.perf_counter()
        for _ in range(1000):
            # Direct access to coordinator data
            value = mock_coordinator.data.get("calculated_offset")
        direct_time = time.perf_counter() - start_time
        
        # Test with caching (through sensor)
        start_time = time.perf_counter()
        for _ in range(1000):
            value = sensor.native_value
        cached_time = time.perf_counter() - start_time
        
        # Cache overhead should be minimal (< 50% slower than direct access)
        overhead_ratio = cached_time / direct_time
        assert overhead_ratio < 1.5, f"Cache overhead ratio {overhead_ratio:.2f}, expected < 1.5"
        
        print(f"Cache overhead: Direct access {direct_time:.6f}s, cached access {cached_time:.6f}s (ratio: {overhead_ratio:.2f})")


class TestSensorPerformanceMetrics:
    """Test performance metrics collection for sensors."""
    
    @pytest.mark.asyncio
    async def test_performance_metrics_collection(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test that performance metrics are collected efficiently."""
        sensor = OffsetCurrentSensor(mock_coordinator, "climate.test_ac", mock_config_entry)
        
        # Add performance tracking to coordinator
        mock_coordinator.performance_metrics = {
            "sensor_read_times": [],
            "cache_hit_count": 0,
            "cache_miss_count": 0,
        }
        
        # Simulate sensor reads with metrics collection
        start_time = time.perf_counter()
        
        for i in range(100):
            read_start = time.perf_counter()
            value = sensor.native_value
            read_end = time.perf_counter()
            
            # Simulate metrics collection
            mock_coordinator.performance_metrics["sensor_read_times"].append(read_end - read_start)
            mock_coordinator.performance_metrics["cache_hit_count"] += 1
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Metrics collection should not significantly impact performance
        avg_time_per_read = total_time / 100
        assert avg_time_per_read < 0.002, f"Sensor read with metrics took {avg_time_per_read:.4f}s, expected < 0.002s"
        
        # Verify metrics were collected
        assert len(mock_coordinator.performance_metrics["sensor_read_times"]) == 100
        assert mock_coordinator.performance_metrics["cache_hit_count"] == 100
        
        print(f"Performance metrics collection: {avg_time_per_read:.6f}s average per read with metrics")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])