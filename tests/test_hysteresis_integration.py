"""Test hysteresis integration - end-to-end hysteresis learning workflow."""

import pytest
import time
import unittest.mock as mock
from dataclasses import replace
from datetime import datetime, time as dt_time

from custom_components.smart_climate.compressor_state_analyzer import CompressorStateAnalyzer
from custom_components.smart_climate.offset_engine import OffsetEngine, HysteresisLearner
from custom_components.smart_climate.lightweight_learner import LightweightOffsetLearner
from custom_components.smart_climate.models import OffsetInput


class TestHysteresisIntegration:
    """Test complete end-to-end hysteresis learning integration."""

    @pytest.fixture
    def config_with_hysteresis(self):
        """Configuration with hysteresis enabled."""
        return {
            "max_offset": 5.0,
            "ml_enabled": True,
            "enable_learning": True,
            "power_sensor": "sensor.ac_power",  # Enables hysteresis
            "power_idle_threshold": 50.0,
            "power_min_threshold": 100.0,
            "power_max_threshold": 250.0,
        }

    @pytest.fixture
    def config_without_power(self):
        """Configuration without power sensor (hysteresis disabled)."""
        return {
            "max_offset": 5.0,
            "ml_enabled": True,
            "enable_learning": True,
            "power_sensor": None,  # Disables hysteresis
        }

    @pytest.fixture
    def sample_input_data(self):
        """Sample input data for testing."""
        return OffsetInput(
            ac_internal_temp=24.0,
            room_temp=24.5,
            outdoor_temp=30.0,
            mode="cool",
            time_of_day=dt_time(15, 30),
            day_of_week=2,
            power_consumption=200.0
        )

    def test_records_setpoint_relative_hysteresis_offsets(self):
        """Learn compressor thresholds as room-temp offsets from active AC setpoint."""
        learner = HysteresisLearner(min_samples=2)

        learner.record_transition("start", 24.6, ac_setpoint_after=24.0)
        learner.record_transition("start", 25.1, ac_setpoint_after=24.5)
        learner.record_transition("stop", 23.6, ac_setpoint_after=24.0)
        learner.record_transition("stop", 24.1, ac_setpoint_after=24.5)

        assert learner.learned_start_offset == pytest.approx(0.6)
        assert learner.learned_stop_offset == pytest.approx(-0.4)
        latest_transition = learner.get_latest_transition_event()
        assert latest_transition is not None
        assert latest_transition["offset_from_setpoint"] == pytest.approx(-0.4)

    def test_compressor_activation_uses_setpoint_relative_start_offset(self):
        """Activation analysis should compare room temp against new setpoint + learned offset."""
        learner = HysteresisLearner(min_samples=2)
        for setpoint in (24.0, 25.0):
            learner.record_transition("start", setpoint + 0.6, ac_setpoint_after=setpoint)
            learner.record_transition("stop", setpoint - 0.4, ac_setpoint_after=setpoint)

        analyzer = CompressorStateAnalyzer(power_threshold=50.0)

        assert analyzer.would_adjustment_activate_compressor(
            current_room_temp=23.9,
            new_setpoint=23.2,
            hysteresis_learner=learner,
            hvac_mode="cool",
        ) is True
        assert analyzer.would_adjustment_activate_compressor(
            current_room_temp=23.9,
            new_setpoint=23.95,
            hysteresis_learner=learner,
            hvac_mode="cool",
        ) is False
        assert analyzer.get_adjustment_needed_to_activate(23.9, learner, "cool") == pytest.approx(23.3)

    def test_probe_start_records_bounds_without_promoting_to_exact_samples(self):
        """Probe starts constrain the threshold interval but must not count as exact samples."""
        learner = HysteresisLearner(min_samples=1)

        learner.record_transition(
            "start",
            23.6,
            ac_setpoint_before=23.8,
            ac_setpoint_after=22.8,
            power_before=4.0,
            power_after=511.0,
            transition_cause="probe",
        )

        assert list(learner._start_temps) == []
        assert list(learner._start_offsets) == []
        assert learner.learned_start_threshold is None
        assert learner.learned_start_offset is None
        assert learner.has_sufficient_data is False
        assert learner.learned_start_offset_lower_bound == pytest.approx(-0.2)
        assert learner.learned_start_offset_upper_bound == pytest.approx(0.8)

        latest_transition = learner.get_latest_transition_event()
        assert latest_transition["transition_sample_type"] == "constraint"
        assert latest_transition["offset_from_setpoint"] == pytest.approx(0.8)
        assert latest_transition["offset_lower_bound"] == pytest.approx(-0.2)
        assert latest_transition["offset_upper_bound"] == pytest.approx(0.8)

        persisted = learner.serialize_for_persistence()
        assert persisted["start_probe_bounds"] == [
            {"lower": pytest.approx(-0.2), "upper": pytest.approx(0.8)}
        ]

    def test_probe_bounds_restore_without_becoming_exact_samples(self):
        """Restored probe bounds stay separate from natural threshold samples."""
        learner = HysteresisLearner(min_samples=1)

        learner.restore_from_persistence({
            "start_probe_bounds": [{"lower": -0.2, "upper": 0.8}],
            "stop_probe_bounds": [{"lower": -0.5, "upper": -0.1}],
            "transition_events": [
                {
                    "transition_type": "start",
                    "room_temp_at_transition": 23.6,
                    "ac_setpoint_before": 23.8,
                    "ac_setpoint_after": 22.8,
                    "transition_cause": "probe",
                }
            ],
        })

        assert list(learner._start_temps) == []
        assert list(learner._stop_temps) == []
        assert learner.has_sufficient_data is False
        assert learner.learned_start_offset_lower_bound == pytest.approx(-0.2)
        assert learner.learned_start_offset_upper_bound == pytest.approx(0.8)
        assert learner.learned_stop_offset_lower_bound == pytest.approx(-0.5)
        assert learner.learned_stop_offset_upper_bound == pytest.approx(-0.1)
        assert learner.get_latest_transition_event()["offset_from_setpoint"] == pytest.approx(0.8)

    def test_probe_command_preserves_pre_and_post_setpoint_context(self, config_with_hysteresis, sample_input_data):
        """Probe transition telemetry should keep both setpoints for interval learning."""
        engine = OffsetEngine(config_with_hysteresis)

        idle_input = replace(
            sample_input_data,
            room_temp=23.6,
            power_consumption=4.0,
            ac_setpoint=23.8,
        )
        engine.calculate_offset(idle_input)
        engine.record_setpoint_command(22.8, was_learning_probe=True, previous_setpoint=23.8)

        active_input = replace(
            sample_input_data,
            room_temp=23.6,
            power_consumption=511.0,
            ac_setpoint=22.8,
        )
        engine.calculate_offset(active_input)

        latest_transition = engine._hysteresis_learner.get_latest_transition_event()
        assert latest_transition["transition_cause"] == "probe"
        assert latest_transition["ac_setpoint_before"] == pytest.approx(23.8)
        assert latest_transition["ac_setpoint_after"] == pytest.approx(22.8)
        assert latest_transition["offset_lower_bound"] == pytest.approx(-0.2)
        assert latest_transition["offset_upper_bound"] == pytest.approx(0.8)
        assert list(engine._hysteresis_learner._start_offsets) == []

    def test_hysteresis_enabled_initialization(self, config_with_hysteresis):
        """Test that hysteresis learning is properly enabled when power sensor configured."""
        engine = OffsetEngine(config_with_hysteresis)
        
        # Verify hysteresis is enabled
        assert engine._hysteresis_enabled is True
        assert engine._hysteresis_learner is not None
        assert engine._last_power_state is None
        
        # Verify learning is enabled
        assert engine._enable_learning is True
        assert engine._learner is not None

    def test_hysteresis_disabled_initialization(self, config_without_power):
        """Test that hysteresis learning is disabled when no power sensor."""
        engine = OffsetEngine(config_without_power)
        
        # Verify hysteresis is disabled
        assert engine._hysteresis_enabled is False
        assert engine._hysteresis_learner is not None  # Still exists, just inactive
        
        # Verify learning is still enabled (separate feature)
        assert engine._enable_learning is True
        assert engine._learner is not None

    def test_power_transition_detection_start(self, config_with_hysteresis, sample_input_data):
        """Test detection of AC start transition (idle/low to moderate/high)."""
        engine = OffsetEngine(config_with_hysteresis)
        
        # First call with low power (idle state)
        low_power_input = replace(sample_input_data, power_consumption=30.0)  # Below idle threshold
        engine.calculate_offset(low_power_input)
        assert engine._last_power_state == "idle"
        
        # Second call with high power (should detect start transition)
        high_power_input = replace(sample_input_data, power_consumption=300.0)  # Above max threshold
        with mock.patch.object(engine._hysteresis_learner, 'record_transition') as mock_record:
            engine.calculate_offset(high_power_input)
            
            # Verify transition was recorded
            mock_record.assert_called_once_with(
                'start',
                sample_input_data.room_temp,
                ac_setpoint_before=None,
                ac_setpoint_after=None,
                power_before=30.0,
                power_after=300.0,
                transition_cause='natural',
            )
            assert engine._last_power_state == "high"

    def test_power_transition_detection_stop(self, config_with_hysteresis, sample_input_data):
        """Test detection of AC stop transition (moderate/high to idle/low)."""
        engine = OffsetEngine(config_with_hysteresis)
        
        # First call with high power (active state)
        high_power_input = replace(sample_input_data, power_consumption=300.0)
        engine.calculate_offset(high_power_input)
        assert engine._last_power_state == "high"
        
        # Second call with low power (should detect stop transition)
        low_power_input = replace(sample_input_data, power_consumption=30.0)
        with mock.patch.object(engine._hysteresis_learner, 'record_transition') as mock_record:
            engine.calculate_offset(low_power_input)
            
            # Verify transition was recorded
            mock_record.assert_called_once_with(
                'stop',
                sample_input_data.room_temp,
                ac_setpoint_before=None,
                ac_setpoint_after=None,
                power_before=300.0,
                power_after=30.0,
                transition_cause='natural',
            )
            assert engine._last_power_state == "idle"

    def test_hysteresis_state_calculation_with_sufficient_data(self, config_with_hysteresis, sample_input_data):
        """Test hysteresis state calculation when learner has sufficient data."""
        engine = OffsetEngine(config_with_hysteresis)
        
        # Setup hysteresis learner with sufficient data
        # Add enough samples to make has_sufficient_data return True
        for i in range(10):  # Default min_samples is 5
            engine._hysteresis_learner._start_temps.append(24.5 + i * 0.1)
            engine._hysteresis_learner._stop_temps.append(23.5 + i * 0.1)
        engine._hysteresis_learner._update_thresholds()
        
        # Test with moderate power (should be active_phase)
        moderate_power_input = replace(sample_input_data, power_consumption=150.0)
        
        with mock.patch.object(engine._hysteresis_learner, 'get_hysteresis_state') as mock_get_state:
            mock_get_state.return_value = "active_phase"
            
            result = engine.calculate_offset(moderate_power_input)
            
            # Verify hysteresis state was requested
            mock_get_state.assert_called_once_with("moderate", sample_input_data.room_temp)

    def test_hysteresis_state_passed_to_learner_predict(self, config_with_hysteresis, sample_input_data):
        """Test that hysteresis state is passed to LightweightOffsetLearner.predict()."""
        engine = OffsetEngine(config_with_hysteresis)
        
        # Setup hysteresis learner with sufficient data
        # Add enough samples to make has_sufficient_data return True
        for i in range(10):  # Default min_samples is 5
            engine._hysteresis_learner._start_temps.append(24.5 + i * 0.1)
            engine._hysteresis_learner._stop_temps.append(23.5 + i * 0.1)
        engine._hysteresis_learner._update_thresholds()
        
        # Setup main learner with sufficient data
        engine._learner._enhanced_samples = [
            {
                "predicted": -0.5, "actual": -0.6, "ac_temp": 24.0, "room_temp": 24.5,
                "outdoor_temp": 30.0, "mode": "cool", "power": 200.0,
                "hysteresis_state": "active_phase", "timestamp": "2025-01-01T15:30:00"
            }
        ]
        
        # Mock hysteresis state calculation
        with mock.patch.object(engine._hysteresis_learner, 'get_hysteresis_state') as mock_get_state:
            mock_get_state.return_value = "active_phase"
            
            # Mock learner predict to verify hysteresis_state is passed
            with mock.patch.object(engine._learner, 'predict') as mock_predict:
                mock_predict.return_value = -0.3
                
                engine.calculate_offset(sample_input_data)
                
                # Verify predict was called with hysteresis_state
                mock_predict.assert_called_once_with(
                    ac_temp=sample_input_data.ac_internal_temp,
                    room_temp=sample_input_data.room_temp,
                    outdoor_temp=sample_input_data.outdoor_temp,
                    mode=sample_input_data.mode,
                    power=sample_input_data.power_consumption,
                    hysteresis_state="active_phase"
                )

    def test_hysteresis_state_passed_to_learner_add_sample(self, config_with_hysteresis, sample_input_data):
        """Test that hysteresis state is passed to LightweightOffsetLearner.add_sample()."""
        engine = OffsetEngine(config_with_hysteresis)
        
        # Setup hysteresis learner with sufficient data
        # Add enough samples to make has_sufficient_data return True
        for i in range(10):  # Default min_samples is 5
            engine._hysteresis_learner._start_temps.append(24.5 + i * 0.1)
            engine._hysteresis_learner._stop_temps.append(23.5 + i * 0.1)
        engine._hysteresis_learner._update_thresholds()
        
        # Mock hysteresis state calculation
        with mock.patch.object(engine._hysteresis_learner, 'get_hysteresis_state') as mock_get_state:
            mock_get_state.return_value = "idle_above_start_threshold"
            
            # Mock learner add_sample to verify hysteresis_state is passed
            with mock.patch.object(engine._learner, 'add_sample') as mock_add_sample:
                
                engine.record_actual_performance(-0.5, -0.6, sample_input_data)
                
                # Verify add_sample was called with hysteresis_state
                mock_add_sample.assert_called_once_with(
                    predicted=-0.5,
                    actual=-0.6,
                    ac_temp=sample_input_data.ac_internal_temp,
                    room_temp=sample_input_data.room_temp,
                    outdoor_temp=sample_input_data.outdoor_temp,
                    mode=sample_input_data.mode,
                    power=sample_input_data.power_consumption,
                    hysteresis_state="idle_above_start_threshold"
                )

    def test_no_power_sensor_fallback_to_default_state(self, config_without_power, sample_input_data):
        """Test fallback to default hysteresis state when no power sensor."""
        engine = OffsetEngine(config_without_power)
        
        # Add sample data so predict method is called
        engine._learner._enhanced_samples = [
            {
                "predicted": -0.5, "actual": -0.6, "ac_temp": 24.0, "room_temp": 24.5,
                "outdoor_temp": 30.0, "mode": "cool", "power": 200.0,
                "hysteresis_state": "no_power_sensor", "timestamp": "2025-01-01T15:30:00"
            }
        ]
        
        # Mock learner predict to verify default hysteresis_state is passed
        with mock.patch.object(engine._learner, 'predict') as mock_predict:
            mock_predict.return_value = -0.3
            
            engine.calculate_offset(sample_input_data)
            
            # Verify predict was called with default hysteresis_state
            mock_predict.assert_called_once_with(
                ac_temp=sample_input_data.ac_internal_temp,
                room_temp=sample_input_data.room_temp,
                outdoor_temp=sample_input_data.outdoor_temp,
                mode=sample_input_data.mode,
                power=sample_input_data.power_consumption,
                hysteresis_state="no_power_sensor"
            )

    def test_insufficient_hysteresis_data_fallback(self, config_with_hysteresis, sample_input_data):
        """Test fallback when hysteresis learner has insufficient data."""
        engine = OffsetEngine(config_with_hysteresis)
        
        # Ensure hysteresis learner has insufficient data
        assert not engine._hysteresis_learner.has_sufficient_data
        
        # Add sample data so predict method is called
        engine._learner._enhanced_samples = [
            {
                "predicted": -0.5, "actual": -0.6, "ac_temp": 24.0, "room_temp": 24.5,
                "outdoor_temp": 30.0, "mode": "cool", "power": 200.0,
                "hysteresis_state": "no_power_sensor", "timestamp": "2025-01-01T15:30:00"
            }
        ]
        
        # Mock learner predict to verify default hysteresis_state is passed
        with mock.patch.object(engine._learner, 'predict') as mock_predict:
            mock_predict.return_value = -0.3
            
            engine.calculate_offset(sample_input_data)
            
            # Verify predict was called with default hysteresis_state
            mock_predict.assert_called_once_with(
                ac_temp=sample_input_data.ac_internal_temp,
                room_temp=sample_input_data.room_temp,
                outdoor_temp=sample_input_data.outdoor_temp,
                mode=sample_input_data.mode,
                power=sample_input_data.power_consumption,
                hysteresis_state="no_power_sensor"
            )

    def test_hysteresis_error_handling_graceful_degradation(self, config_with_hysteresis, sample_input_data):
        """Test graceful degradation when hysteresis operations fail."""
        engine = OffsetEngine(config_with_hysteresis)
        
        # Add sample data so predict method is called
        engine._learner._enhanced_samples = [
            {
                "predicted": -0.5, "actual": -0.6, "ac_temp": 24.0, "room_temp": 24.5,
                "outdoor_temp": 30.0, "mode": "cool", "power": 200.0,
                "hysteresis_state": "no_power_sensor", "timestamp": "2025-01-01T15:30:00"
            }
        ]
        
        # Mock hysteresis learner to raise exception
        with mock.patch.object(engine._hysteresis_learner, 'get_hysteresis_state') as mock_get_state:
            mock_get_state.side_effect = Exception("Hysteresis error")
            
            # Mock learner predict to verify fallback hysteresis_state is used
            with mock.patch.object(engine._learner, 'predict') as mock_predict:
                mock_predict.return_value = -0.3
                
                # Should not raise exception
                result = engine.calculate_offset(sample_input_data)
                
                # Verify operation completed successfully with fallback
                assert result.offset is not None
                
                # Verify predict was called with fallback hysteresis_state
                mock_predict.assert_called_once_with(
                    ac_temp=sample_input_data.ac_internal_temp,
                    room_temp=sample_input_data.room_temp,
                    outdoor_temp=sample_input_data.outdoor_temp,
                    mode=sample_input_data.mode,
                    power=sample_input_data.power_consumption,
                    hysteresis_state="no_power_sensor"
                )

    def test_performance_prediction_time_requirement(self, config_with_hysteresis, sample_input_data):
        """Test that prediction times remain under 1ms requirement with hysteresis."""
        engine = OffsetEngine(config_with_hysteresis)
        
        # Setup hysteresis learner with sufficient data
        # Add enough samples to make has_sufficient_data return True
        for i in range(10):  # Default min_samples is 5
            engine._hysteresis_learner._start_temps.append(24.5 + i * 0.1)
            engine._hysteresis_learner._stop_temps.append(23.5 + i * 0.1)
        engine._hysteresis_learner._update_thresholds()
        
        # Add sample data to main learner
        for i in range(50):  # Add sufficient samples
            engine._learner.add_sample(
                predicted=-0.5,
                actual=-0.6,
                ac_temp=24.0 + i * 0.1,
                room_temp=24.5 + i * 0.1,
                outdoor_temp=30.0,
                mode="cool",
                power=200.0,
                hysteresis_state="active_phase"
            )
        
        # Time the prediction operation
        start_time = time.perf_counter()
        result = engine.calculate_offset(sample_input_data)
        end_time = time.perf_counter()
        
        prediction_time_ms = (end_time - start_time) * 1000
        
        # Verify prediction time is under 1ms requirement
        assert prediction_time_ms < 1.0, f"Prediction took {prediction_time_ms:.3f}ms, exceeds 1ms requirement"
        assert result.offset is not None

    def test_end_to_end_hysteresis_learning_workflow(self, config_with_hysteresis):
        """Test complete end-to-end hysteresis learning workflow."""
        engine = OffsetEngine(config_with_hysteresis)
        
        # Simulate AC cycle: idle -> start -> active -> stop -> idle
        workflow_inputs = [
            # AC is idle
            OffsetInput(24.0, 25.0, 30.0, "cool", 30.0, dt_time(15, 0), 2),  # idle
            # AC starts cooling
            OffsetInput(24.0, 24.8, 30.0, "cool", 200.0, dt_time(15, 5), 2),  # moderate -> start transition
            # AC is actively cooling
            OffsetInput(24.1, 24.6, 30.0, "cool", 250.0, dt_time(15, 10), 2),  # high -> active
            OffsetInput(24.2, 24.4, 30.0, "cool", 230.0, dt_time(15, 15), 2),  # moderate -> active
            # AC stops cooling
            OffsetInput(24.2, 24.2, 30.0, "cool", 40.0, dt_time(15, 20), 2),  # idle -> stop transition
            # AC is idle again
            OffsetInput(24.3, 24.1, 30.0, "cool", 35.0, dt_time(15, 25), 2),  # idle
        ]
        
        results = []
        for input_data in workflow_inputs:
            result = engine.calculate_offset(input_data)
            results.append(result)
        
        # Verify all operations completed successfully
        assert len(results) == 6
        for result in results:
            assert result.offset is not None
            assert result.confidence >= 0.0
        
        # Verify hysteresis learner collected transition data
        assert len(engine._hysteresis_learner._start_temps) >= 1  # At least one start transition
        assert len(engine._hysteresis_learner._stop_temps) >= 1   # At least one stop transition

    def test_enhanced_learning_accuracy_with_hysteresis(self, config_with_hysteresis):
        """Test that hysteresis context improves learning accuracy over time."""
        engine = OffsetEngine(config_with_hysteresis)
        
        # Setup hysteresis learner with sufficient data
        # Add enough samples to make has_sufficient_data return True
        for i in range(10):  # Default min_samples is 5
            engine._hysteresis_learner._start_temps.append(24.5 + i * 0.1)
            engine._hysteresis_learner._stop_temps.append(23.5 + i * 0.1)
        engine._hysteresis_learner._update_thresholds()
        
        # Add samples with different hysteresis states
        active_phase_samples = [
            (24.0, 24.5, 200.0, "active_phase", -0.5),
            (24.1, 24.6, 220.0, "active_phase", -0.5),
            (24.0, 24.4, 210.0, "active_phase", -0.4),
        ]
        
        idle_stable_samples = [
            (24.2, 24.0, 40.0, "idle_stable_zone", -0.2),
            (24.3, 24.1, 35.0, "idle_stable_zone", -0.2),
            (24.1, 23.9, 45.0, "idle_stable_zone", -0.2),
        ]
        
        # Add samples to learner
        for ac_temp, room_temp, power, hysteresis_state, actual_offset in active_phase_samples + idle_stable_samples:
            engine._learner.add_sample(
                predicted=-0.3,
                actual=actual_offset,
                ac_temp=ac_temp,
                room_temp=room_temp,
                outdoor_temp=30.0,
                mode="cool",
                power=power,
                hysteresis_state=hysteresis_state
            )
        
        # Test prediction for active phase
        active_input = OffsetInput(24.0, 24.5, 30.0, "cool", 200.0, dt_time(15, 30), 2)
        with mock.patch.object(engine._hysteresis_learner, 'get_hysteresis_state') as mock_get_state:
            mock_get_state.return_value = "active_phase"
            
            predicted_active = engine._learner.predict(
                ac_temp=active_input.ac_internal_temp,
                room_temp=active_input.room_temp,
                outdoor_temp=active_input.outdoor_temp,
                mode=active_input.mode,
                power=active_input.power_consumption,
                hysteresis_state="active_phase"
            )
        
        # Test prediction for idle stable zone
        idle_input = OffsetInput(24.2, 24.0, 30.0, "cool", 40.0, dt_time(15, 30), 2)
        predicted_idle = engine._learner.predict(
            ac_temp=idle_input.ac_internal_temp,
            room_temp=idle_input.room_temp,
            outdoor_temp=idle_input.outdoor_temp,
            mode=idle_input.mode,
            power=idle_input.power_consumption,
            hysteresis_state="idle_stable_zone"
        )
        
        # Verify different predictions for different hysteresis states
        assert abs(predicted_active - (-0.5)) < 0.2, f"Active phase prediction {predicted_active} should be close to -0.5"
        assert abs(predicted_idle - (-0.2)) < 0.2, f"Idle phase prediction {predicted_idle} should be close to -0.2"
        assert abs(predicted_active - predicted_idle) > 0.05, "Different hysteresis states should yield different predictions"

    def test_memory_usage_with_hysteresis_data(self, config_with_hysteresis):
        """Test that memory usage stays reasonable with enhanced hysteresis sample data."""
        engine = OffsetEngine(config_with_hysteresis)
        
        # Add many samples to test memory management
        for i in range(2000):  # Add more than max_history
            engine._learner.add_sample(
                predicted=-0.3,
                actual=-0.5 + (i % 10) * 0.01,  # Vary actual values slightly
                ac_temp=24.0 + (i % 50) * 0.1,
                room_temp=24.5 + (i % 50) * 0.1,
                outdoor_temp=30.0 + (i % 20),
                mode="cool",
                power=200.0 + (i % 100),
                hysteresis_state=["active_phase", "idle_stable_zone", "idle_above_start_threshold"][i % 3]
            )
        
        # Verify samples are limited to max_history
        assert len(engine._learner._enhanced_samples) <= engine._learner._max_history
        
        # Verify system still functions efficiently
        test_input = OffsetInput(24.0, 24.5, 30.0, "cool", dt_time(15, 30), 2, 200.0)
        result = engine.calculate_offset(test_input)
        assert result.offset is not None

    def test_integration_with_existing_functionality(self, config_with_hysteresis, sample_input_data):
        """Test that hysteresis integration doesn't break existing functionality."""
        engine = OffsetEngine(config_with_hysteresis)
        
        # Test basic offset calculation still works
        result = engine.calculate_offset(sample_input_data)
        assert result.offset is not None
        assert result.confidence >= 0.0
        assert result.reason is not None
        
        # Test learning info still works
        info = engine.get_learning_info()
        assert "enabled" in info
        assert "samples" in info
        
        # Test reset learning still works
        engine.reset_learning()
        assert len(engine._learner._enhanced_samples) == 0
        assert len(engine._hysteresis_learner._start_temps) == 0
        assert len(engine._hysteresis_learner._stop_temps) == 0