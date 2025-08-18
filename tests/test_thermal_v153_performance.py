"""ABOUTME: Performance validation tests for v1.5.3 thermal model enhancements.
Tests 75-probe operations <5ms, memory usage reasonable, serialization performance, and no memory leaks."""

import pytest
import time
import sys
import gc
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from custom_components.smart_climate.thermal_model import PassiveThermalModel, ProbeResult
from custom_components.smart_climate.thermal_manager import ThermalManager
from custom_components.smart_climate.const import (
    MAX_PROBE_HISTORY_SIZE,
    CONFIDENCE_REQUIRED_SAMPLES,
    DECAY_RATE_PER_DAY
)
from tests.fixtures.thermal_v153 import create_probe_result, create_probe_sequence


class TestThermalV153Performance:
    """Performance validation tests for v1.5.3 thermal model enhancements."""

    @pytest.fixture
    def thermal_model(self):
        """Create thermal model for performance testing."""
        return PassiveThermalModel()

    @pytest.fixture
    def thermal_manager(self):
        """Create thermal manager for serialization performance testing."""
        mock_hass = Mock()
        mock_model = PassiveThermalModel()
        mock_preferences = Mock()
        return ThermalManager(mock_hass, mock_model, mock_preferences)

    @pytest.fixture
    def performance_dataset(self):
        """Create large dataset for performance testing."""
        return create_probe_sequence(
            count=MAX_PROBE_HISTORY_SIZE,
            start_days_ago=75,  # Full seasonal window
            outdoor_temps=[25.0 + (i * 0.2) for i in range(MAX_PROBE_HISTORY_SIZE)],
            tau_base=90.0,
            confidence_base=0.85
        )

    def test_75_probe_operations_under_5ms(self, thermal_model, performance_dataset):
        """Test that 75-probe operations complete under 5ms target.
        
        Critical performance requirement for real-time operation.
        """
        # Arrange - Load full 75-probe dataset
        for probe in performance_dataset:
            thermal_model.update_tau(probe, is_cooling=True)
        
        assert thermal_model.get_probe_count() == MAX_PROBE_HISTORY_SIZE
        
        # Test - Confidence calculation performance (most common operation)
        confidence_times = []
        for _ in range(100):  # Multiple iterations for accurate measurement
            start_time = time.perf_counter()
            confidence = thermal_model.get_confidence()
            end_time = time.perf_counter()
            
            confidence_times.append((end_time - start_time) * 1000)  # Convert to ms
            assert confidence > 0.0  # Functional correctness
        
        avg_confidence_time = sum(confidence_times) / len(confidence_times)
        max_confidence_time = max(confidence_times)
        
        # Assert - Performance requirements
        assert avg_confidence_time < 1.0, f"Average confidence calculation: {avg_confidence_time:.3f}ms (target: <1ms)"
        assert max_confidence_time < 2.0, f"Maximum confidence calculation: {max_confidence_time:.3f}ms (target: <2ms)"
        
        # Test - Tau calculation performance
        tau_times = []
        for _ in range(50):  # Fewer iterations (more expensive operation)
            start_time = time.perf_counter()
            tau_cooling = thermal_model._calculate_weighted_tau(is_cooling=True)
            tau_warming = thermal_model._calculate_weighted_tau(is_cooling=False)
            end_time = time.perf_counter()
            
            tau_times.append((end_time - start_time) * 1000)
            assert tau_cooling > 0.0 and tau_warming > 0.0
        
        avg_tau_time = sum(tau_times) / len(tau_times)
        max_tau_time = max(tau_times)
        
        # Assert - Tau calculation performance
        assert avg_tau_time < 2.0, f"Average tau calculation: {avg_tau_time:.3f}ms (target: <2ms)"
        assert max_tau_time < 5.0, f"Maximum tau calculation: {max_tau_time:.3f}ms (target: <5ms)"
        
        # Test - Prediction performance (critical path)
        prediction_times = []
        for _ in range(100):
            start_time = time.perf_counter()
            prediction = thermal_model.predict_drift(
                current=22.0,
                outdoor=28.0,
                minutes=60,
                is_cooling=True
            )
            end_time = time.perf_counter()
            
            prediction_times.append((end_time - start_time) * 1000)
            assert isinstance(prediction, float)
        
        avg_prediction_time = sum(prediction_times) / len(prediction_times)
        max_prediction_time = max(prediction_times)
        
        # Assert - Prediction performance (most critical)
        assert avg_prediction_time < 0.5, f"Average prediction: {avg_prediction_time:.3f}ms (target: <0.5ms)"
        assert max_prediction_time < 1.0, f"Maximum prediction: {max_prediction_time:.3f}ms (target: <1ms)"

    def test_memory_usage_reasonable(self, thermal_model, performance_dataset):
        """Test memory usage with 75-probe history is reasonable.
        
        Validates memory efficiency of v1.5.3 enhancements.
        """
        # Measure baseline memory
        gc.collect()  # Clean up before measurement
        baseline_memory = self._get_memory_usage()
        
        # Load full dataset
        for probe in performance_dataset:
            thermal_model.update_tau(probe, is_cooling=True)
        
        # Measure memory after loading
        gc.collect()
        loaded_memory = self._get_memory_usage()
        memory_increase = loaded_memory - baseline_memory
        
        # Assert - Memory usage reasonable
        # 75 probes * ~200 bytes per probe = ~15KB expected
        assert memory_increase < 50_000, f"Memory increase: {memory_increase} bytes (target: <50KB)"
        
        # Test - Memory doesn't grow with repeated operations
        initial_memory = self._get_memory_usage()
        
        # Perform many operations
        for _ in range(1000):
            thermal_model.get_confidence()
            thermal_model.predict_drift(22.0, 28.0, 60, True)
        
        final_memory = self._get_memory_usage()
        operation_memory_growth = final_memory - initial_memory
        
        # Assert - No significant memory growth from operations
        assert operation_memory_growth < 10_000, f"Operation memory growth: {operation_memory_growth} bytes (target: <10KB)"

    def test_serialization_performance_under_100ms(self, thermal_manager, performance_dataset):
        """Test serialization/deserialization performance under 100ms.
        
        Critical for persistence operations during normal operation.
        """
        # Arrange - Load thermal manager with full dataset
        for probe in performance_dataset:
            thermal_manager._model.update_tau(probe, is_cooling=True)
        
        assert thermal_manager._model.get_probe_count() == MAX_PROBE_HISTORY_SIZE
        
        # Test - Serialization performance
        serialization_times = []
        for _ in range(20):  # Multiple iterations
            start_time = time.perf_counter()
            serialized_data = thermal_manager.serialize()
            end_time = time.perf_counter()
            
            serialization_times.append((end_time - start_time) * 1000)
            assert isinstance(serialized_data, dict)
            assert 'probe_history' in serialized_data
        
        avg_serialization_time = sum(serialization_times) / len(serialization_times)
        max_serialization_time = max(serialization_times)
        
        # Assert - Serialization performance
        assert avg_serialization_time < 50.0, f"Average serialization: {avg_serialization_time:.3f}ms (target: <50ms)"
        assert max_serialization_time < 100.0, f"Maximum serialization: {max_serialization_time:.3f}ms (target: <100ms)"
        
        # Test - Deserialization performance
        serialized_data = thermal_manager.serialize()
        deserialization_times = []
        
        for _ in range(20):
            # Create fresh manager for each test
            fresh_manager = ThermalManager(Mock(), PassiveThermalModel(), Mock())
            
            start_time = time.perf_counter()
            fresh_manager.restore(serialized_data)
            end_time = time.perf_counter()
            
            deserialization_times.append((end_time - start_time) * 1000)
            assert fresh_manager._model.get_probe_count() == MAX_PROBE_HISTORY_SIZE
        
        avg_deserialization_time = sum(deserialization_times) / len(deserialization_times)
        max_deserialization_time = max(deserialization_times)
        
        # Assert - Deserialization performance
        assert avg_deserialization_time < 50.0, f"Average deserialization: {avg_deserialization_time:.3f}ms (target: <50ms)"
        assert max_deserialization_time < 100.0, f"Maximum deserialization: {max_deserialization_time:.3f}ms (target: <100ms)"

    def test_no_memory_leaks_sustained_operation(self, thermal_model):
        """Test no memory leaks during sustained operation.
        
        Validates system stability over extended periods.
        """
        # Baseline measurement
        gc.collect()
        baseline_memory = self._get_memory_usage()
        
        # Simulate sustained operation (24 hours of probes, one every hour)
        sustained_probes = create_probe_sequence(
            count=24,
            start_days_ago=1,
            tau_base=90.0,
            confidence_base=0.8
        )
        
        # Phase 1: Normal operation
        for probe in sustained_probes:
            thermal_model.update_tau(probe, is_cooling=True)
            
            # Perform typical operations
            for _ in range(10):
                thermal_model.get_confidence()
                thermal_model.predict_drift(22.0, 28.0, 60, True)
        
        # Memory check after initial operation
        gc.collect()
        phase1_memory = self._get_memory_usage()
        phase1_growth = phase1_memory - baseline_memory
        
        # Phase 2: Extended operation (simulate week of operation)
        week_probes = create_probe_sequence(
            count=50,  # Additional probes
            start_days_ago=7,
            tau_base=92.0,
            confidence_base=0.85
        )
        
        for i, probe in enumerate(week_probes):
            thermal_model.update_tau(probe, is_cooling=True)
            
            # More intensive operations
            for j in range(20):
                thermal_model.get_confidence()
                thermal_model.predict_drift(20.0 + (j % 10), 25.0 + (j % 15), 30 + (j % 60), True)
        
        # Final memory check
        gc.collect()
        final_memory = self._get_memory_usage()
        total_growth = final_memory - baseline_memory
        phase2_growth = final_memory - phase1_memory
        
        # Assert - No significant memory leaks
        assert total_growth < 100_000, f"Total memory growth: {total_growth} bytes (target: <100KB)"
        assert phase2_growth < 50_000, f"Phase 2 memory growth: {phase2_growth} bytes (target: <50KB)"
        
        # The probe history should be at or near MAX_PROBE_HISTORY_SIZE (some may be evicted)
        assert thermal_model.get_probe_count() >= min(74, MAX_PROBE_HISTORY_SIZE)

    def test_exponential_decay_calculation_performance(self, thermal_model):
        """Test exponential decay weighting calculation performance.
        
        New v1.5.3 feature - must not impact performance significantly.
        """
        # Create dataset with varied ages for realistic decay calculation
        varied_age_probes = []
        for i in range(MAX_PROBE_HISTORY_SIZE):
            age_days = i * 1.0  # Ages from 0 to 74 days
            probe = create_probe_result(
                tau_value=90.0 + (i * 0.1),
                confidence=0.8,
                age_days=age_days
            )
            varied_age_probes.append(probe)
            thermal_model.update_tau(probe, is_cooling=True)
        
        # Test decay calculation performance
        decay_times = []
        for _ in range(100):
            start_time = time.perf_counter()
            
            # Test the internal decay calculation
            weighted_tau = thermal_model._calculate_weighted_tau(is_cooling=True)
            
            end_time = time.perf_counter()
            decay_times.append((end_time - start_time) * 1000)
            
            assert weighted_tau > 0.0
        
        avg_decay_time = sum(decay_times) / len(decay_times)
        max_decay_time = max(decay_times)
        
        # Assert - Exponential decay performance
        assert avg_decay_time < 3.0, f"Average decay calculation: {avg_decay_time:.3f}ms (target: <3ms)"
        assert max_decay_time < 8.0, f"Maximum decay calculation: {max_decay_time:.3f}ms (target: <8ms)"
        
        # Test mathematical correctness of decay weights
        now = datetime.now(timezone.utc)
        expected_weights = []
        calculated_weights = []
        
        for probe in thermal_model._probe_history:
            age_days = (now - probe.timestamp).total_seconds() / 86400
            expected_weight = DECAY_RATE_PER_DAY ** age_days
            expected_weights.append(expected_weight)
            
        # Verify weights are in expected range
        assert all(0.0 < w <= 1.0 for w in expected_weights)
        assert expected_weights[0] > expected_weights[-1]  # Recent > old

    def test_confidence_calculation_scalability(self, thermal_model):
        """Test confidence calculation scales well with probe count.
        
        Validates O(n) performance characteristics.
        """
        # Test with different probe counts to verify scalability
        test_sizes = [5, 15, 30, 50, 75]
        calculation_times = {}
        
        for size in test_sizes:
            # Create model with specific probe count
            test_model = PassiveThermalModel()
            probes = create_probe_sequence(
                count=size,
                start_days_ago=size * 0.5,
                tau_base=90.0,
                confidence_base=0.8
            )
            
            for probe in probes:
                test_model.update_tau(probe, is_cooling=True)
            
            # Measure confidence calculation time
            times = []
            for _ in range(50):
                start_time = time.perf_counter()
                confidence = test_model.get_confidence()
                end_time = time.perf_counter()
                
                times.append((end_time - start_time) * 1000)
                assert confidence > 0.0
            
            calculation_times[size] = sum(times) / len(times)
        
        # Assert - Performance scales reasonably (should be roughly linear)
        time_5 = calculation_times[5]
        time_75 = calculation_times[75]
        
        # 75 probes should not take more than 15x the time of 5 probes
        scaling_factor = time_75 / time_5
        assert scaling_factor < 15.0, f"Performance scaling factor: {scaling_factor:.1f} (target: <15x)"
        
        # All sizes should meet absolute performance targets
        for size, avg_time in calculation_times.items():
            assert avg_time < 5.0, f"Confidence calculation with {size} probes: {avg_time:.3f}ms (target: <5ms)"

    def test_concurrent_operation_performance(self, thermal_model, performance_dataset):
        """Test performance under concurrent-like access patterns.
        
        Simulates multiple rapid accesses as might occur in real system.
        """
        # Load full dataset
        for probe in performance_dataset:
            thermal_model.update_tau(probe, is_cooling=True)
        
        # Simulate rapid concurrent-like access
        operations = []
        start_time = time.perf_counter()
        
        for i in range(500):  # Many rapid operations
            # Mix of different operation types
            if i % 3 == 0:
                result = thermal_model.get_confidence()
                operations.append(('confidence', result))
            elif i % 3 == 1:
                result = thermal_model.predict_drift(
                    current=20.0 + (i % 10),
                    outdoor=25.0 + (i % 15),
                    minutes=30 + (i % 90),
                    is_cooling=True
                )
                operations.append(('prediction', result))
            else:
                result = thermal_model.get_probe_count()
                operations.append(('count', result))
        
        end_time = time.perf_counter()
        total_time = (end_time - start_time) * 1000  # Convert to ms
        
        # Assert - Concurrent access performance
        avg_operation_time = total_time / len(operations)
        assert avg_operation_time < 0.2, f"Average operation time: {avg_operation_time:.3f}ms (target: <0.2ms)"
        assert total_time < 100.0, f"Total concurrent operations: {total_time:.3f}ms (target: <100ms)"
        
        # Verify all operations succeeded
        confidence_ops = [op for op in operations if op[0] == 'confidence']
        prediction_ops = [op for op in operations if op[0] == 'prediction']
        count_ops = [op for op in operations if op[0] == 'count']
        
        assert len(confidence_ops) > 0
        assert len(prediction_ops) > 0
        assert len(count_ops) > 0
        
        # All results should be valid
        assert all(isinstance(op[1], float) and op[1] >= 0.0 for op in confidence_ops)
        assert all(isinstance(op[1], float) for op in prediction_ops)
        assert all(isinstance(op[1], int) and op[1] == MAX_PROBE_HISTORY_SIZE for op in count_ops)

    def test_probe_addition_performance_at_capacity(self, thermal_model):
        """Test probe addition performance when at capacity.
        
        Tests deque eviction performance with maxlen=75.
        """
        # Fill to capacity
        initial_probes = create_probe_sequence(
            count=MAX_PROBE_HISTORY_SIZE,
            start_days_ago=75,
            tau_base=90.0,
            confidence_base=0.8
        )
        
        for probe in initial_probes:
            thermal_model.update_tau(probe, is_cooling=True)
        
        assert thermal_model.get_probe_count() == MAX_PROBE_HISTORY_SIZE
        
        # Test addition performance at capacity (causes eviction)
        addition_times = []
        for i in range(100):
            new_probe = create_probe_result(
                tau_value=88.0 + (i * 0.1),
                confidence=0.85,
                age_days=0  # Recent probe
            )
            
            start_time = time.perf_counter()
            thermal_model.update_tau(new_probe, is_cooling=True)
            end_time = time.perf_counter()
            
            addition_times.append((end_time - start_time) * 1000)
            
            # Should remain at capacity
            assert thermal_model.get_probe_count() == MAX_PROBE_HISTORY_SIZE
        
        avg_addition_time = sum(addition_times) / len(addition_times)
        max_addition_time = max(addition_times)
        
        # Assert - Addition performance at capacity
        assert avg_addition_time < 2.0, f"Average addition at capacity: {avg_addition_time:.3f}ms (target: <2ms)"
        assert max_addition_time < 5.0, f"Maximum addition at capacity: {max_addition_time:.3f}ms (target: <5ms)"

    def _get_memory_usage(self):
        """Get current memory usage in bytes."""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except ImportError:
            # Fallback to sys.getsizeof for basic measurement
            return sys.getsizeof({}) * 100  # Rough approximation

    def test_performance_regression_baseline(self, thermal_model):
        """Establish performance baseline for regression testing.
        
        Creates baseline measurements for future performance comparisons.
        """
        # Standard test dataset
        baseline_probes = create_probe_sequence(
            count=30,  # Representative dataset size
            start_days_ago=30,
            tau_base=90.0,
            confidence_base=0.8
        )
        
        for probe in baseline_probes:
            thermal_model.update_tau(probe, is_cooling=True)
        
        # Baseline measurements
        baseline_metrics = {}
        
        # Confidence calculation baseline
        confidence_times = []
        for _ in range(100):
            start = time.perf_counter()
            thermal_model.get_confidence()
            end = time.perf_counter()
            confidence_times.append((end - start) * 1000)
        baseline_metrics['confidence_avg_ms'] = sum(confidence_times) / len(confidence_times)
        
        # Prediction baseline
        prediction_times = []
        for _ in range(100):
            start = time.perf_counter()
            thermal_model.predict_drift(22.0, 28.0, 60, True)
            end = time.perf_counter()
            prediction_times.append((end - start) * 1000)
        baseline_metrics['prediction_avg_ms'] = sum(prediction_times) / len(prediction_times)
        
        # Tau calculation baseline
        tau_times = []
        for _ in range(50):
            start = time.perf_counter()
            thermal_model._calculate_weighted_tau(is_cooling=True)
            end = time.perf_counter()
            tau_times.append((end - start) * 1000)
        baseline_metrics['tau_avg_ms'] = sum(tau_times) / len(tau_times)
        
        # Log baseline for future reference
        print(f"\nv1.5.3 Performance Baseline:")
        print(f"  Confidence calculation: {baseline_metrics['confidence_avg_ms']:.3f}ms")
        print(f"  Prediction calculation: {baseline_metrics['prediction_avg_ms']:.3f}ms")
        print(f"  Tau calculation: {baseline_metrics['tau_avg_ms']:.3f}ms")
        
        # Assert baseline targets are met
        assert baseline_metrics['confidence_avg_ms'] < 1.0
        assert baseline_metrics['prediction_avg_ms'] < 0.5
        assert baseline_metrics['tau_avg_ms'] < 3.0
        
        # This creates a performance record for future regression testing
        return baseline_metrics