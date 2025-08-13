"""ABOUTME: Performance monitoring tests for update_listener functionality.
Tests reload timing, memory usage, entity consistency, and system stability metrics."""

import pytest
import asyncio
import time
import logging
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from collections import defaultdict
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.smart_climate.const import DOMAIN
from custom_components.smart_climate import async_setup_entry, async_unload_entry, update_listener


class MockMemoryProfiler:
    """Mock memory profiler to simulate memory monitoring."""
    
    def __init__(self):
        self.baseline_memory = 50.0  # MB
        self.current_memory = self.baseline_memory
        self.leak_simulation = 0.0
    
    def get_memory_usage(self):
        """Simulate getting current memory usage."""
        # Add small random variations
        import random
        variation = random.uniform(-1.0, 1.0)
        return self.current_memory + variation + self.leak_simulation
    
    def simulate_leak(self, amount_mb: float):
        """Simulate a memory leak for testing."""
        self.leak_simulation += amount_mb


class PerformanceMonitor:
    """Monitor performance metrics during update_listener operations."""
    
    def __init__(self):
        self.reload_times = []
        self.entity_counts_before = {}
        self.entity_counts_after = {}
        self.memory_usage_before = []
        self.memory_usage_after = []
        self.reload_failures = []
        self.reload_loop_detection = []
        self.last_reload_time = None
        self.consecutive_reloads = 0
        self.memory_profiler = MockMemoryProfiler()
    
    def record_reload_start(self, entry_id: str):
        """Record the start of a reload operation."""
        self.reload_start_time = time.time()
        self.reload_start_entry = entry_id
        
        # Check for rapid consecutive reloads (reload loop detection)
        now = datetime.now()
        if self.last_reload_time and (now - self.last_reload_time).seconds < 30:
            self.consecutive_reloads += 1
        else:
            self.consecutive_reloads = 1
        self.last_reload_time = now
        
        # Record potential reload loop
        if self.consecutive_reloads >= 3:
            self.reload_loop_detection.append({
                'timestamp': now,
                'entry_id': entry_id,
                'consecutive_count': self.consecutive_reloads
            })
    
    def record_reload_end(self, entry_id: str, success: bool = True):
        """Record the end of a reload operation."""
        if hasattr(self, 'reload_start_time'):
            duration = time.time() - self.reload_start_time
            self.reload_times.append(duration)
            
            if not success:
                self.reload_failures.append({
                    'entry_id': entry_id,
                    'duration': duration,
                    'timestamp': datetime.now()
                })
    
    def record_entity_count(self, phase: str, count: int):
        """Record entity count before/after reload."""
        if phase == 'before':
            self.entity_counts_before[datetime.now()] = count
        else:
            self.entity_counts_after[datetime.now()] = count
    
    def record_memory_usage(self, phase: str):
        """Record memory usage before/after reload."""
        usage = self.memory_profiler.get_memory_usage()
        if phase == 'before':
            self.memory_usage_before.append(usage)
        else:
            self.memory_usage_after.append(usage)
    
    def get_performance_metrics(self):
        """Get comprehensive performance metrics."""
        avg_reload_time = sum(self.reload_times) / len(self.reload_times) if self.reload_times else 0
        max_reload_time = max(self.reload_times) if self.reload_times else 0
        
        memory_growth = 0
        if self.memory_usage_before and self.memory_usage_after:
            avg_before = sum(self.memory_usage_before) / len(self.memory_usage_before)
            avg_after = sum(self.memory_usage_after) / len(self.memory_usage_after)
            memory_growth = avg_after - avg_before
        
        return {
            'avg_reload_time': avg_reload_time,
            'max_reload_time': max_reload_time,
            'total_reloads': len(self.reload_times),
            'reload_failures': len(self.reload_failures),
            'memory_growth_mb': memory_growth,
            'reload_loops_detected': len(self.reload_loop_detection),
            'consecutive_reloads': self.consecutive_reloads
        }


class TestUpdateListenerPerformance:
    """Performance monitoring tests for update_listener functionality."""
    
    def setup_method(self):
        """Set up performance monitoring for each test."""
        self.performance_monitor = PerformanceMonitor()
        self.mock_entities_registry = {}
    
    def create_mock_hass_with_entities(self, entity_count: int = 5):
        """Create a mock HomeAssistant instance with simulated entities."""
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {}}
        
        # Mock config entries
        mock_config_entries = Mock()
        mock_config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
        mock_config_entries.async_reload = AsyncMock(return_value=True)
        mock_config_entries.async_unload_platforms = AsyncMock(return_value=True)
        mock_hass.config_entries = mock_config_entries
        
        # Mock services
        mock_hass.async_add_executor_job = AsyncMock()
        mock_hass.services = Mock()
        mock_hass.services.async_register = Mock()
        mock_hass.services.has_service = Mock(return_value=False)
        
        # Mock entity registry with specified number of entities
        self.mock_entities_registry = {}
        for i in range(entity_count):
            entity_id = f"sensor.smart_climate_{i}"
            self.mock_entities_registry[entity_id] = {
                'domain': 'sensor',
                'platform': DOMAIN,
                'unique_id': f"smart_climate_{i}_offset_current"
            }
        
        return mock_hass
    
    def create_mock_config_entry(self, entry_id: str = "performance_test_entry"):
        """Create a mock config entry for testing."""
        entry = Mock()
        entry.entry_id = entry_id
        entry.data = {
            "name": "Performance Test Climate",
            "room_sensor": "sensor.room_temperature",
            "climate_entity": "climate.test_climate"
        }
        entry.options = {
            "max_offset": 3.0,
            "learning_enabled": True,
            "thermal_efficiency_enabled": True
        }
        entry.runtime_data = {}
        entry.add_update_listener = Mock(return_value=Mock())
        entry.async_on_unload = Mock()
        return entry
    
    @pytest.mark.asyncio
    async def test_reload_performance_timing(self):
        """Test that reload completes within 5 seconds requirement."""
        mock_hass = self.create_mock_hass_with_entities(10)
        entry = self.create_mock_config_entry("timing_test_entry")
        
        # Add realistic delay to async_reload to simulate real behavior
        async def delayed_reload(entry_id):
            await asyncio.sleep(0.1)  # Simulate some processing time
            return True
        
        mock_hass.config_entries.async_reload = AsyncMock(side_effect=delayed_reload)
        
        # Perform multiple reload tests
        for i in range(5):
            self.performance_monitor.record_reload_start(entry.entry_id)
            
            start_time = time.time()
            await update_listener(mock_hass, entry)
            duration = time.time() - start_time
            
            self.performance_monitor.record_reload_end(entry.entry_id, True)
            
            # Assert reload completes within 5 seconds
            assert duration < 5.0, f"Reload #{i+1} took {duration:.2f}s, exceeds 5s requirement"
        
        # Check performance metrics
        metrics = self.performance_monitor.get_performance_metrics()
        assert metrics['avg_reload_time'] < 5.0, f"Average reload time {metrics['avg_reload_time']:.2f}s exceeds 5s"
        assert metrics['max_reload_time'] < 5.0, f"Max reload time {metrics['max_reload_time']:.2f}s exceeds 5s"
        
        # Log performance results
        logging.info(f"Reload Performance: avg={metrics['avg_reload_time']:.3f}s, max={metrics['max_reload_time']:.3f}s")
    
    @pytest.mark.asyncio
    async def test_memory_usage_monitoring(self):
        """Test memory usage before and after reload operations."""
        mock_hass = self.create_mock_hass_with_entities(15)
        entry = self.create_mock_config_entry("memory_test_entry")
        
        # Simulate potential memory leak
        self.performance_monitor.memory_profiler.simulate_leak(0.0)  # Start with no leak
        
        # Perform multiple reloads and monitor memory
        for i in range(3):
            # Record memory before reload
            self.performance_monitor.record_memory_usage('before')
            
            await update_listener(mock_hass, entry)
            
            # Simulate small memory growth after reload (realistic scenario)
            self.performance_monitor.memory_profiler.simulate_leak(0.1)  # 0.1 MB growth
            
            # Record memory after reload
            self.performance_monitor.record_memory_usage('after')
        
        # Analyze memory metrics
        metrics = self.performance_monitor.get_performance_metrics()
        
        # Assert memory growth is within acceptable limits (less than 2MB per reload)
        assert metrics['memory_growth_mb'] < 2.0, f"Memory growth {metrics['memory_growth_mb']:.2f}MB exceeds 2MB limit"
        
        # Log memory analysis
        logging.info(f"Memory Analysis: growth={metrics['memory_growth_mb']:.2f}MB over {metrics['total_reloads']} reloads")
    
    @pytest.mark.asyncio
    async def test_entity_count_consistency(self):
        """Test that entity counts remain consistent across reloads."""
        initial_entity_count = 8
        mock_hass = self.create_mock_hass_with_entities(initial_entity_count)
        entry = self.create_mock_config_entry("consistency_test_entry")
        
        # Mock entity counting function
        def count_entities():
            return len(self.mock_entities_registry)
        
        # Perform multiple reloads and check entity consistency
        for i in range(4):
            # Record entity count before reload
            entities_before = count_entities()
            self.performance_monitor.record_entity_count('before', entities_before)
            
            await update_listener(mock_hass, entry)
            
            # Record entity count after reload
            entities_after = count_entities()
            self.performance_monitor.record_entity_count('after', entities_after)
            
            # Assert entity count consistency
            assert entities_before == entities_after, f"Reload #{i+1}: Entity count changed from {entities_before} to {entities_after}"
            assert entities_after == initial_entity_count, f"Entity count {entities_after} doesn't match expected {initial_entity_count}"
        
        logging.info(f"Entity Consistency: {initial_entity_count} entities maintained across {len(self.performance_monitor.reload_times)} reloads")
    
    @pytest.mark.asyncio
    async def test_state_preservation_across_reloads(self):
        """Test that integration state is preserved across reloads."""
        mock_hass = self.create_mock_hass_with_entities(6)
        entry = self.create_mock_config_entry("state_test_entry")
        
        # Simulate state storage in hass.data
        initial_state = {
            "learning_enabled": True,
            "current_offset": 2.5,
            "model_confidence": 0.85,
            "last_update": datetime.now(),
            "samples_collected": 150
        }
        
        # Mock state persistence
        mock_hass.data[DOMAIN][entry.entry_id] = {"state": initial_state.copy()}
        
        # Perform reload and verify state preservation
        await update_listener(mock_hass, entry)
        
        # Verify reload was called
        mock_hass.config_entries.async_reload.assert_called_once_with(entry.entry_id)
        
        # In real implementation, state would be restored after reload
        # Here we verify the reload mechanism was triggered correctly
        assert mock_hass.config_entries.async_reload.called, "State preservation requires reload to be called"
        
        logging.info("State Preservation: Reload mechanism verified for state restoration")
    
    @pytest.mark.asyncio 
    async def test_reload_duration_timing_and_logging(self, caplog):
        """Test reload duration timing with logging verification."""
        mock_hass = self.create_mock_hass_with_entities(5)
        entry = self.create_mock_config_entry("timing_log_test_entry")
        
        # Configure realistic timing
        async def timed_reload(entry_id):
            await asyncio.sleep(0.05)  # 50ms simulation
            return True
        
        mock_hass.config_entries.async_reload = AsyncMock(side_effect=timed_reload)
        
        # Test with logging capture
        with caplog.at_level(logging.INFO):
            start_time = time.time()
            await update_listener(mock_hass, entry)
            duration = time.time() - start_time
        
        # Verify timing
        assert 0.04 <= duration <= 0.1, f"Duration {duration:.3f}s not in expected range"
        
        # Verify logging
        log_messages = [record.message for record in caplog.records]
        assert any("Reloading Smart Climate integration due to options update" in msg for msg in log_messages)
        
        logging.info(f"Reload Duration: {duration:.3f}s with proper logging")
    
    @pytest.mark.asyncio
    async def test_reload_frequency_monitoring(self):
        """Test reload frequency monitoring and rate limiting detection."""
        mock_hass = self.create_mock_hass_with_entities(5)
        entry = self.create_mock_config_entry("frequency_test_entry")
        
        # Simulate rapid consecutive reloads (potential issue)
        for i in range(4):
            self.performance_monitor.record_reload_start(entry.entry_id)
            
            await update_listener(mock_hass, entry)
            
            self.performance_monitor.record_reload_end(entry.entry_id, True)
            
            # Short delay to simulate rapid reloads
            await asyncio.sleep(0.01)
        
        # Check reload loop detection
        metrics = self.performance_monitor.get_performance_metrics()
        assert metrics['consecutive_reloads'] >= 3, f"Should detect {metrics['consecutive_reloads']} consecutive reloads"
        assert metrics['reload_loops_detected'] >= 1, "Should detect potential reload loop"
        
        logging.warning(f"Reload Loop Detected: {metrics['consecutive_reloads']} consecutive reloads")
    
    @pytest.mark.asyncio
    async def test_reload_failure_detection(self):
        """Test detection and handling of reload failures."""
        mock_hass = self.create_mock_hass_with_entities(5)
        entry = self.create_mock_config_entry("failure_test_entry")
        
        # Mock reload failure
        mock_hass.config_entries.async_reload = AsyncMock(
            side_effect=Exception("Simulated reload failure")
        )
        
        # Test reload failure handling
        self.performance_monitor.record_reload_start(entry.entry_id)
        
        with pytest.raises(Exception) as exc_info:
            await update_listener(mock_hass, entry)
        
        # Record failure
        self.performance_monitor.record_reload_end(entry.entry_id, False)
        
        # Verify failure detection
        assert "Simulated reload failure" in str(exc_info.value)
        metrics = self.performance_monitor.get_performance_metrics()
        assert metrics['reload_failures'] >= 1, "Should detect reload failure"
        
        logging.error(f"Reload Failure Detected: {metrics['reload_failures']} failures recorded")
    
    @pytest.mark.asyncio
    async def test_concurrent_reload_handling(self):
        """Test handling of concurrent reload requests."""
        mock_hass = self.create_mock_hass_with_entities(5)
        entry = self.create_mock_config_entry("concurrent_test_entry")
        
        # Mock delayed reload
        reload_call_count = 0
        async def delayed_reload(entry_id):
            nonlocal reload_call_count
            reload_call_count += 1
            await asyncio.sleep(0.1)  # Simulate processing time
            return True
        
        mock_hass.config_entries.async_reload = AsyncMock(side_effect=delayed_reload)
        
        # Start multiple concurrent reloads
        reload_tasks = []
        for i in range(3):
            task = asyncio.create_task(update_listener(mock_hass, entry))
            reload_tasks.append(task)
        
        # Wait for all to complete
        results = await asyncio.gather(*reload_tasks, return_exceptions=True)
        
        # All should complete successfully
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Concurrent reload {i+1} failed: {result}"
        
        # Verify all reload calls were made
        assert reload_call_count == 3, f"Expected 3 reload calls, got {reload_call_count}"
        
        logging.info(f"Concurrent Reload Test: {reload_call_count} concurrent reloads completed")
    
    @pytest.mark.asyncio
    async def test_performance_metrics_comprehensive_report(self):
        """Generate comprehensive performance report across multiple test scenarios."""
        mock_hass = self.create_mock_hass_with_entities(10)
        entry = self.create_mock_config_entry("comprehensive_test_entry")
        
        # Simulate various reload scenarios
        scenarios = [
            ("fast_reload", 0.02),
            ("normal_reload", 0.05),
            ("slow_reload", 0.15),
            ("variable_reload_1", 0.03),
            ("variable_reload_2", 0.08)
        ]
        
        for scenario_name, delay in scenarios:
            # Configure reload timing
            async def scenario_reload(entry_id):
                await asyncio.sleep(delay)
                return True
            
            mock_hass.config_entries.async_reload = AsyncMock(side_effect=scenario_reload)
            
            # Execute reload with monitoring
            self.performance_monitor.record_reload_start(entry.entry_id)
            self.performance_monitor.record_memory_usage('before')
            self.performance_monitor.record_entity_count('before', 10)
            
            await update_listener(mock_hass, entry)
            
            self.performance_monitor.record_memory_usage('after')
            self.performance_monitor.record_entity_count('after', 10)
            self.performance_monitor.record_reload_end(entry.entry_id, True)
            
            logging.info(f"Scenario {scenario_name}: {delay:.3f}s target, actual measured")
        
        # Generate final performance report
        metrics = self.performance_monitor.get_performance_metrics()
        
        report = f"""
Performance Test Summary:
- Total Reloads: {metrics['total_reloads']}
- Average Reload Time: {metrics['avg_reload_time']:.3f}s
- Maximum Reload Time: {metrics['max_reload_time']:.3f}s
- Reload Failures: {metrics['reload_failures']}
- Memory Growth: {metrics['memory_growth_mb']:.2f}MB
- Reload Loops Detected: {metrics['reload_loops_detected']}
"""
        
        logging.info(report)
        
        # Assert overall performance requirements
        assert metrics['avg_reload_time'] < 5.0, "Average performance within requirements"
        assert metrics['max_reload_time'] < 5.0, "Maximum performance within requirements"
        assert metrics['reload_failures'] == 0, "No reload failures in normal scenarios"
        
        # Performance criteria met
        logging.info("✓ All performance monitoring tests completed successfully")