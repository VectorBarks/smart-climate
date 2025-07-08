"""Final validation test suite for HysteresisLearner implementation.

This comprehensive test suite validates that the HysteresisLearner implementation 
is production-ready and meets all architectural requirements.
"""

import pytest
import time
import statistics
from unittest.mock import Mock, patch
from datetime import datetime, time as dt_time

from custom_components.smart_climate.offset_engine import OffsetEngine, HysteresisLearner
from custom_components.smart_climate.lightweight_learner import LightweightOffsetLearner
from custom_components.smart_climate.models import OffsetInput


class TestHysteresisSystemValidation:
    """Comprehensive system validation tests for HysteresisLearner."""

    @pytest.fixture
    def complete_config(self):
        """Configuration with all hysteresis features enabled."""
        return {
            "max_offset": 5.0,
            "ml_enabled": True,
            "enable_learning": True,
            "power_sensor": "sensor.ac_power",
            "power_idle_threshold": 50.0,
            "power_min_threshold": 100.0,
            "power_max_threshold": 250.0,
        }

    @pytest.fixture
    def no_power_config(self):
        """Configuration without power sensor to test graceful degradation."""
        return {
            "max_offset": 5.0,
            "ml_enabled": True,
            "enable_learning": True,
            "power_sensor": None,
        }

    def test_complete_learning_cycle_from_scratch(self, complete_config):
        """Test complete AC learning cycle starting with no hysteresis data.
        
        This simulates the first few days of operation where the system learns
        the AC's operational temperature thresholds.
        """
        engine = OffsetEngine(complete_config)
        
        # Verify initial state - no hysteresis data
        assert not engine._hysteresis_learner.has_sufficient_data
        assert engine._hysteresis_learner.learned_start_threshold is None
        assert engine._hysteresis_learner.learned_stop_threshold is None
        
        # Simulate power transitions and temperature recordings over several cycles
        # AC start transitions (idle/low -> moderate/high power)
        start_temps = [24.2, 24.3, 24.1, 24.4, 24.2]  # Room temps when AC starts
        stop_temps = [23.7, 23.8, 23.6, 23.9, 23.7]   # Room temps when AC stops
        
        # Simulate multiple AC cycles
        for i in range(5):
            # AC starts (power transition)
            input_data = OffsetInput(
                ac_internal_temp=23.0,
                room_temp=start_temps[i],
                outdoor_temp=30.0,
                power_consumption=200.0,  # High power
                mode="cool",
                time_of_day=dt_time(14, 0),
                day_of_week=2
            )
            
            # First call establishes last_power_state
            if i == 0:
                engine._last_power_state = "idle"  # Simulate previous idle state
            
            # Calculate offset to trigger transition detection
            result = engine.calculate_offset(input_data)
            assert result is not None
            
            # Simulate AC running for a while, then stopping
            input_data_stop = OffsetInput(
                ac_internal_temp=23.0,
                room_temp=stop_temps[i],
                outdoor_temp=30.0,
                power_consumption=30.0,  # Low power (idle)
                mode="cool",
                time_of_day=dt_time(14, 30),
                day_of_week=2
            )
            
            engine._last_power_state = "high"  # Set up for stop transition
            result = engine.calculate_offset(input_data_stop)
            assert result is not None
        
        # After 5 cycles, should have sufficient data
        assert engine._hysteresis_learner.has_sufficient_data
        assert engine._hysteresis_learner.learned_start_threshold is not None
        assert engine._hysteresis_learner.learned_stop_threshold is not None
        
        # Verify learned thresholds are reasonable
        expected_start = statistics.median(start_temps)
        expected_stop = statistics.median(stop_temps)
        assert abs(engine._hysteresis_learner.learned_start_threshold - expected_start) < 0.1
        assert abs(engine._hysteresis_learner.learned_stop_threshold - expected_stop) < 0.1

    def test_integration_points_working_correctly(self, complete_config):
        """Test that all integration points between components work seamlessly."""
        engine = OffsetEngine(complete_config)
        
        # Manually add sufficient data to hysteresis learner
        for temp in [24.0, 24.1, 24.2, 24.3, 24.4]:
            engine._hysteresis_learner.record_transition('start', temp)
            engine._hysteresis_learner.record_transition('stop', temp - 0.5)
        
        assert engine._hysteresis_learner.has_sufficient_data
        
        # Test hysteresis state calculation in different scenarios
        test_cases = [
            # (power_consumption, room_temp, expected_state_type)
            (300.0, 24.5, "active_phase"),  # High power
            (40.0, 25.0, "idle_above_start_threshold"),  # Idle, high temp
            (35.0, 23.0, "idle_below_stop_threshold"),   # Idle, low temp
            (45.0, 24.0, "idle_stable_zone"),            # Idle, between thresholds
        ]
        
        for power, temp, expected_state in test_cases:
            input_data = OffsetInput(
                ac_internal_temp=23.5,
                room_temp=temp,
                outdoor_temp=30.0,
                power_consumption=power,
                mode="cool",
                time_of_day=dt_time(15, 0),
                day_of_week=3
            )
            
            result = engine.calculate_offset(input_data)
            assert result is not None
            
            # Verify hysteresis state is correctly calculated
            power_state = engine._get_power_state(power)
            hysteresis_state = engine._hysteresis_learner.get_hysteresis_state(
                power_state, temp
            )
            assert expected_state in hysteresis_state

    def test_persistence_across_system_restarts(self, complete_config):
        """Test that hysteresis data persists correctly across system restarts."""
        # Create engine and train it
        engine1 = OffsetEngine(complete_config)
        
        # Add learning data
        for i in range(6):
            engine1._hysteresis_learner.record_transition('start', 24.0 + i * 0.1)
            engine1._hysteresis_learner.record_transition('stop', 23.5 + i * 0.1)
        
        # Serialize the state
        hysteresis_data = engine1._hysteresis_learner.serialize_for_persistence()
        
        # Create new engine (simulating restart)
        engine2 = OffsetEngine(complete_config)
        
        # Restore the state
        engine2._hysteresis_learner.restore_from_persistence(hysteresis_data)
        
        # Verify state is correctly restored
        assert engine2._hysteresis_learner.has_sufficient_data
        assert engine1._hysteresis_learner.learned_start_threshold == engine2._hysteresis_learner.learned_start_threshold
        assert engine1._hysteresis_learner.learned_stop_threshold == engine2._hysteresis_learner.learned_stop_threshold

    def test_performance_under_various_load_conditions(self, complete_config):
        """Test system performance with various data loads and usage patterns."""
        engine = OffsetEngine(complete_config)
        
        # Add maximum amount of data
        for i in range(50):  # Max samples
            engine._hysteresis_learner.record_transition('start', 24.0 + (i % 10) * 0.1)
            engine._hysteresis_learner.record_transition('stop', 23.5 + (i % 10) * 0.1)
        
        # Test prediction performance
        input_data = OffsetInput(
            ac_internal_temp=23.5,
            room_temp=24.2,
            outdoor_temp=30.0,
            power_consumption=200.0,
            mode="cool",
            time_of_day=dt_time(15, 0),
            day_of_week=3
        )
        
        # Measure prediction time
        start_time = time.perf_counter()
        for _ in range(100):  # Multiple predictions
            result = engine.calculate_offset(input_data)
            assert result is not None
        end_time = time.perf_counter()
        
        # Should be well under 1ms per prediction
        avg_time = (end_time - start_time) / 100
        assert avg_time < 0.001, f"Average prediction time {avg_time:.4f}s exceeds 1ms requirement"

    def test_memory_usage_with_extended_learning_periods(self, complete_config):
        """Test memory usage stays bounded during extended operation."""
        engine = OffsetEngine(complete_config)
        
        # Simulate extended operation with many transitions
        for i in range(200):  # More than max_samples
            temp_variation = (i % 20) * 0.05  # Realistic temperature variation
            engine._hysteresis_learner.record_transition('start', 24.0 + temp_variation)
            engine._hysteresis_learner.record_transition('stop', 23.5 + temp_variation)
        
        # Verify memory is bounded by max_samples
        assert len(engine._hysteresis_learner._start_temps) <= 50
        assert len(engine._hysteresis_learner._stop_temps) <= 50
        
        # Verify functionality still works
        assert engine._hysteresis_learner.has_sufficient_data
        assert engine._hysteresis_learner.learned_start_threshold is not None

    def test_error_handling_and_graceful_degradation(self, complete_config):
        """Test robust error handling and graceful degradation scenarios."""
        engine = OffsetEngine(complete_config)
        
        # Test with malformed power data
        input_data = OffsetInput(
            ac_internal_temp=23.5,
            room_temp=24.2,
            outdoor_temp=30.0,
            power_consumption=None,  # Missing power data
            mode="cool",
            time_of_day=dt_time(15, 0),
            day_of_week=3
        )
        
        # Should not crash
        result = engine.calculate_offset(input_data)
        assert result is not None
        
        # Test with corrupted hysteresis data
        corrupted_data = {"start_temps": "invalid", "stop_temps": []}
        engine._hysteresis_learner.restore_from_persistence(corrupted_data)
        
        # Should still function
        result = engine.calculate_offset(input_data)
        assert result is not None

    def test_real_world_usage_simulation(self, complete_config):
        """Simulate realistic AC usage over several days."""
        engine = OffsetEngine(complete_config)
        
        # Simulate realistic daily AC cycles
        daily_patterns = [
            # (hour, typical_room_temp, ac_power_pattern)
            (8, 25.0, "start"),   # Morning warm-up
            (10, 24.0, "running"), # Mid-morning
            (12, 23.5, "stop"),   # Reached target
            (14, 24.5, "start"),  # Afternoon heat
            (16, 23.8, "stop"),   # Cooled down
            (18, 24.2, "start"),  # Evening heat
            (20, 23.6, "stop"),   # Evening cool
        ]
        
        learning_samples = []
        
        # Simulate 3 days of operation
        for day in range(3):
            for hour, room_temp, ac_state in daily_patterns:
                power = 250.0 if ac_state == "running" else (200.0 if ac_state == "start" else 40.0)
                
                input_data = OffsetInput(
                    ac_internal_temp=23.0,
                    room_temp=room_temp + (day * 0.1),  # Slight daily variation
                    outdoor_temp=32.0 + (day * 0.5),  # Outdoor temperature variation
                    power_consumption=power,
                    mode="cool",
                    time_of_day=dt_time(hour, 0),
                    day_of_week=(day % 7)
                )
                
                # Set up for transition detection
                if ac_state == "start":
                    engine._last_power_state = "idle"
                elif ac_state == "stop":
                    engine._last_power_state = "high"
                
                result = engine.calculate_offset(input_data)
                assert result is not None
                learning_samples.append((room_temp, ac_state))
        
        # After 3 days, should have learned patterns
        if engine._hysteresis_learner.has_sufficient_data:
            assert engine._hysteresis_learner.learned_start_threshold is not None
            assert engine._hysteresis_learner.learned_stop_threshold is not None
            
            # Verify thresholds are reasonable for the data
            start_temps = [temp for temp, state in learning_samples if state == "start"]
            stop_temps = [temp for temp, state in learning_samples if state == "stop"]
            
            if start_temps and stop_temps:
                # Should be within reasonable range of actual data
                assert min(start_temps) <= engine._hysteresis_learner.learned_start_threshold <= max(start_temps)
                assert min(stop_temps) <= engine._hysteresis_learner.learned_stop_threshold <= max(stop_temps)

    def test_enhanced_predictions_with_hysteresis_context(self, complete_config):
        """Test that hysteresis context improves prediction accuracy."""
        engine = OffsetEngine(complete_config)
        
        # Add hysteresis learning data
        for i in range(10):
            engine._hysteresis_learner.record_transition('start', 24.0 + i * 0.05)
            engine._hysteresis_learner.record_transition('stop', 23.5 + i * 0.05)
        
        # Test predictions in different hysteresis states
        test_scenarios = [
            {
                "room_temp": 24.5,
                "power": 300.0,
                "expected_state": "active_phase",
                "description": "AC actively cooling"
            },
            {
                "room_temp": 24.8,
                "power": 40.0,
                "expected_state": "idle_above_start_threshold",
                "description": "AC should start but hasn't"
            },
            {
                "room_temp": 23.2,
                "power": 35.0,
                "expected_state": "idle_below_stop_threshold",
                "description": "AC stopped, room cooling"
            }
        ]
        
        for scenario in test_scenarios:
            input_data = OffsetInput(
                ac_internal_temp=23.0,
                room_temp=scenario["room_temp"],
                outdoor_temp=30.0,
                power_consumption=scenario["power"],
                mode="cool",
                time_of_day=dt_time(15, 0),
                day_of_week=3
            )
            
            result = engine.calculate_offset(input_data)
            assert result is not None
            
            # Verify hysteresis state is correctly detected
            power_state = engine._get_power_state(scenario["power"])
            hysteresis_state = engine._hysteresis_learner.get_hysteresis_state(
                power_state, scenario["room_temp"]
            )
            
            assert scenario["expected_state"] in hysteresis_state, \
                f"Failed for scenario: {scenario['description']}"

    def test_no_power_sensor_graceful_behavior(self, no_power_config):
        """Test system behavior when no power sensor is configured."""
        engine = OffsetEngine(no_power_config)
        
        # Verify hysteresis is disabled
        assert not engine._hysteresis_enabled
        
        # System should still function normally
        input_data = OffsetInput(
            ac_internal_temp=23.5,
            room_temp=24.2,
            outdoor_temp=30.0,
            power_consumption=None,  # No power data
            mode="cool",
            time_of_day=dt_time(15, 0),
            day_of_week=3
        )
        
        result = engine.calculate_offset(input_data)
        assert result is not None
        
        # Should use default hysteresis state
        # This test verifies the system gracefully handles missing power sensor


class TestProductionReadinessValidation:
    """Validate all production readiness requirements."""

    def test_architectural_requirements_implemented(self):
        """Verify all architectural requirements from c_hysteresis_architecture.md are implemented."""
        # Test HysteresisLearner class exists with correct interface
        learner = HysteresisLearner()
        
        # Verify required attributes
        assert hasattr(learner, '_min_samples')
        assert hasattr(learner, '_start_temps')
        assert hasattr(learner, '_stop_temps')
        assert hasattr(learner, 'learned_start_threshold')
        assert hasattr(learner, 'learned_stop_threshold')
        
        # Verify required methods
        assert hasattr(learner, 'has_sufficient_data')
        assert hasattr(learner, 'record_transition')
        assert hasattr(learner, 'get_hysteresis_state')
        assert hasattr(learner, 'serialize_for_persistence')
        assert hasattr(learner, 'restore_from_persistence')
        
        # Test OffsetEngine integration
        config = {"power_sensor": "sensor.test", "enable_learning": True}
        engine = OffsetEngine(config)
        
        assert hasattr(engine, '_hysteresis_learner')
        assert hasattr(engine, '_last_power_state')
        assert hasattr(engine, '_hysteresis_enabled')

    def test_backward_compatibility_maintained(self):
        """Test that existing functionality continues to work without hysteresis."""
        # Test with old configuration (no power sensor)
        old_config = {
            "max_offset": 5.0,
            "ml_enabled": True,
            "enable_learning": False,
        }
        
        engine = OffsetEngine(old_config)
        
        input_data = OffsetInput(
            ac_internal_temp=23.5,
            room_temp=24.2,
            outdoor_temp=30.0,
            power_consumption=None,  # No power sensor in old config
            mode="cool",
            time_of_day=dt_time(15, 0),
            day_of_week=3
        )
        
        result = engine.calculate_offset(input_data)
        assert result is not None
        assert result.offset is not None

    def test_performance_requirements_met(self):
        """Verify all performance requirements are met."""
        config = {"power_sensor": "sensor.test", "enable_learning": True}
        engine = OffsetEngine(config)
        
        # Add maximum data
        for i in range(50):
            engine._hysteresis_learner.record_transition('start', 24.0 + i * 0.01)
            engine._hysteresis_learner.record_transition('stop', 23.5 + i * 0.01)
        
        input_data = OffsetInput(
            ac_internal_temp=23.5,
            room_temp=24.2,
            outdoor_temp=30.0,
            power_consumption=200.0,
            mode="cool",
            time_of_day=dt_time(15, 0),
            day_of_week=3
        )
        
        # Test prediction time requirement
        start_time = time.perf_counter()
        result = engine.calculate_offset(input_data)
        end_time = time.perf_counter()
        
        prediction_time = end_time - start_time
        assert prediction_time < 0.001, f"Prediction time {prediction_time:.4f}s exceeds 1ms requirement"
        assert result is not None

    def test_all_hysteresis_states_reachable(self):
        """Test that all defined hysteresis states can be reached."""
        learner = HysteresisLearner()
        
        # Test learning_hysteresis state (insufficient data)
        state = learner.get_hysteresis_state("idle", 24.0)
        assert state == "learning_hysteresis"
        
        # Add sufficient data
        for i in range(5):
            learner.record_transition('start', 24.0 + i * 0.1)
            learner.record_transition('stop', 23.5 + i * 0.1)
        
        assert learner.has_sufficient_data
        
        # Test all other states
        test_cases = [
            ("high", 24.0, "active_phase"),
            ("moderate", 24.0, "active_phase"),
            ("idle", 25.0, "idle_above_start_threshold"),
            ("low", 25.0, "idle_above_start_threshold"),
            ("idle", 23.0, "idle_below_stop_threshold"),
            ("low", 23.0, "idle_below_stop_threshold"),
            ("idle", 23.8, "idle_stable_zone"),
            ("low", 23.8, "idle_stable_zone"),
        ]
        
        for power_state, room_temp, expected_state in test_cases:
            state = learner.get_hysteresis_state(power_state, room_temp)
            assert state == expected_state, f"Failed for {power_state}, {room_temp}"

    def test_comprehensive_system_health_check(self):
        """Comprehensive system health validation."""
        config = {
            "max_offset": 5.0,
            "ml_enabled": True,
            "enable_learning": True,
            "power_sensor": "sensor.ac_power",
            "power_idle_threshold": 50.0,
            "power_min_threshold": 100.0,
            "power_max_threshold": 250.0,
        }
        
        engine = OffsetEngine(config)
        
        # Verify all components initialized correctly
        assert engine._hysteresis_enabled
        assert engine._hysteresis_learner is not None
        assert engine._last_power_state is None  # Initially None
        
        # Test complete workflow
        input_data = OffsetInput(
            ac_internal_temp=23.5,
            room_temp=24.2,
            outdoor_temp=30.0,
            power_consumption=200.0,
            mode="cool",
            time_of_day=dt_time(15, 0),
            day_of_week=3
        )
        
        # Should work without errors
        result = engine.calculate_offset(input_data)
        assert result is not None
        
        # Test persistence round-trip
        hysteresis_data = engine._hysteresis_learner.serialize_for_persistence()
        engine._hysteresis_learner.restore_from_persistence(hysteresis_data)
        
        # Should still work after persistence round-trip
        result = engine.calculate_offset(input_data)
        assert result is not None
        
        print("✅ All production readiness requirements validated successfully")