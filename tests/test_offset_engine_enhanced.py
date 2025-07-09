"""Tests for enhanced OffsetEngine with learning capabilities."""

import pytest
from datetime import time
from unittest.mock import Mock, patch
import time as time_module

from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.models import OffsetInput, OffsetResult


class TestOffsetEngineEnhanced:
    """Test suite for enhanced OffsetEngine with learning capabilities."""

    def test_init_with_learning_enabled(self):
        """Test OffsetEngine initialization with learning enabled."""
        config = {
            "max_offset": 5.0,
            "ml_enabled": True,
            "enable_learning": True
        }
        engine = OffsetEngine(config)
        
        assert engine._max_offset == 5.0
        assert engine._ml_enabled is True
        assert engine._enable_learning is True
        assert engine._learner is not None
        assert hasattr(engine, 'record_actual_performance')
        assert hasattr(engine, 'get_learning_info')

    def test_init_with_learning_disabled(self):
        """Test OffsetEngine initialization with learning disabled."""
        config = {
            "max_offset": 5.0,
            "ml_enabled": True,
            "enable_learning": False
        }
        engine = OffsetEngine(config)
        
        assert engine._max_offset == 5.0
        assert engine._ml_enabled is True
        assert engine._enable_learning is False
        assert engine._learner is None

    def test_init_with_learning_default_disabled(self):
        """Test OffsetEngine initialization with default learning state."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        # Learning should be disabled by default for backward compatibility
        assert engine._enable_learning is False
        assert engine._learner is None

    def test_calculate_offset_without_learning(self):
        """Test that basic offset calculation still works without learning."""
        config = {"max_offset": 5.0, "enable_learning": False}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=22.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=1
        )
        
        result = engine.calculate_offset(input_data)
        
        # Should work exactly as before - rule-based calculation
        assert isinstance(result, OffsetResult)
        assert result.offset == 2.0  # AC sensor warmer than room, positive offset
        assert not result.clamped
        assert result.confidence >= 0.5
        assert "learning" not in result.reason.lower()

    def test_calculate_offset_with_learning_insufficient_data(self):
        """Test offset calculation with learning but insufficient training data."""
        config = {"max_offset": 5.0, "enable_learning": True}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=22.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=1
        )
        
        result = engine.calculate_offset(input_data)
        
        # During calibration phase with insufficient data
        assert isinstance(result, OffsetResult)
        assert result.offset == 2.0  # AC sensor warmer than room, positive offset
        assert not result.clamped
        assert result.confidence == 0.2  # Low confidence during calibration
        assert "calibration" in result.reason.lower()  # Should be in calibration phase

    def test_calculate_offset_with_learning_sufficient_data(self):
        """Test offset calculation with learning and sufficient training data."""
        config = {"max_offset": 5.0, "enable_learning": True}
        engine = OffsetEngine(config)
        
        # Mock learner to report sufficient samples (skip calibration phase)
        engine._learner = Mock()
        engine._learner.get_statistics.return_value = Mock(samples_collected=25)  # > 10
        engine._learner._enhanced_samples = [Mock()]  # Has samples
        engine._learner.predict.return_value = 1.8  # Learned offset
        
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=22.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=1
        )
        
        result = engine.calculate_offset(input_data)
        
        # Should use weighted combination of rule-based and learned
        assert isinstance(result, OffsetResult)
        assert result.confidence >= 0.5
        assert "learning" in result.reason.lower()

    def test_calculate_offset_with_power_state_awareness(self):
        """Test offset calculation considers power consumption for AC state."""
        config = {"max_offset": 5.0, "enable_learning": True}
        engine = OffsetEngine(config)
        
        # Mock learner to skip calibration phase
        engine._learner = Mock()
        engine._learner.get_statistics.return_value = Mock(samples_collected=15)  # > 10
        engine._learner._enhanced_samples = [Mock()]
        engine._learner.predict.return_value = 1.8
        
        # Test with high power (AC working hard)
        input_high_power = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=22.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=300.0,  # High power
            time_of_day=time(14, 30),
            day_of_week=1
        )
        
        result_high_power = engine.calculate_offset(input_high_power)
        
        # Test with low power (AC idle)
        input_low_power = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=22.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=50.0,  # Low power
            time_of_day=time(14, 30),
            day_of_week=1
        )
        
        result_low_power = engine.calculate_offset(input_low_power)
        
        # Power state should affect reasoning and potentially offset
        assert "power" in result_high_power.reason.lower()
        assert "power" in result_low_power.reason.lower()
        assert result_high_power.reason != result_low_power.reason

    def test_calculate_offset_power_state_fallback(self):
        """Test offset calculation fallback when power sensor unavailable."""
        config = {"max_offset": 5.0, "enable_learning": True}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=22.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=None,  # No power data
            time_of_day=time(14, 30),
            day_of_week=1
        )
        
        result = engine.calculate_offset(input_data)
        
        # Should work fine without power data
        assert isinstance(result, OffsetResult)
        # When power is unavailable, should mention temperature-only or not mention power at all
        power_mentions = result.reason.lower().count("power")
        # Either no power mentions, or specifically mentions power unavailable/temperature-only
        assert power_mentions == 0 or "unavailable" in result.reason.lower() or "temperature-only" in result.reason.lower()

    def test_record_actual_performance(self):
        """Test recording actual performance for learning feedback."""
        config = {"max_offset": 5.0, "enable_learning": True}
        engine = OffsetEngine(config)
        
        # Record performance sample
        engine.record_actual_performance(
            predicted_offset=2.0,
            actual_offset=1.8,
            input_data=OffsetInput(
                ac_internal_temp=24.0,
                room_temp=22.0,
                outdoor_temp=25.0,
                mode="none",
                power_consumption=150.0,
                time_of_day=time(14, 30),
                day_of_week=1
            )
        )
        
        # Should not raise exception and should have recorded the sample
        assert len(engine._learner._enhanced_samples) > 0

    def test_record_actual_performance_learning_disabled(self):
        """Test recording performance when learning is disabled."""
        config = {"max_offset": 5.0, "enable_learning": False}
        engine = OffsetEngine(config)
        
        # Should not raise exception even when learning disabled
        engine.record_actual_performance(
            predicted_offset=2.0,
            actual_offset=1.8,
            input_data=OffsetInput(
                ac_internal_temp=24.0,
                room_temp=22.0,
                outdoor_temp=25.0,
                mode="none",
                power_consumption=150.0,
                time_of_day=time(14, 30),
                day_of_week=1
            )
        )
        
        # Should complete without error

    def test_get_learning_info(self):
        """Test getting learning information and statistics."""
        config = {"max_offset": 5.0, "enable_learning": True}
        engine = OffsetEngine(config)
        
        # Add some training data
        for i in range(10):
            engine.record_actual_performance(
                predicted_offset=2.0,
                actual_offset=1.8 + (i * 0.01),
                input_data=OffsetInput(
                    ac_internal_temp=24.0,
                    room_temp=22.0,
                    outdoor_temp=25.0,
                    mode="none",
                    power_consumption=150.0,
                    time_of_day=time(14, 30),
                    day_of_week=1
                )
            )
        
        learning_info = engine.get_learning_info()
        
        assert isinstance(learning_info, dict)
        assert "enabled" in learning_info
        assert "samples" in learning_info
        assert "accuracy" in learning_info
        assert "confidence" in learning_info
        assert learning_info["enabled"] is True
        assert learning_info["samples"] == 10

    def test_get_learning_info_disabled(self):
        """Test getting learning info when learning is disabled."""
        config = {"max_offset": 5.0, "enable_learning": False}
        engine = OffsetEngine(config)
        
        learning_info = engine.get_learning_info()
        
        assert isinstance(learning_info, dict)
        assert learning_info["enabled"] is False
        assert learning_info["samples"] == 0

    def test_confidence_combines_rules_and_learning(self):
        """Test that confidence scoring combines rules and learning."""
        config = {"max_offset": 5.0, "enable_learning": True}
        engine = OffsetEngine(config)
        
        # Add sufficient training samples
        sample_input = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=22.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=1
        )
        
        for i in range(25):
            engine.record_actual_performance(-2.0, -1.8 + (i * 0.01), sample_input)
        
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=22.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=1
        )
        
        result = engine.calculate_offset(input_data)
        
        # Confidence should be higher with learning data
        assert result.confidence > 0.5
        assert result.confidence <= 1.0

    def test_performance_requirement_less_than_1ms(self):
        """Test that offset calculation takes less than 1ms."""
        config = {"max_offset": 5.0, "enable_learning": True}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=22.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=1
        )
        
        # Measure performance
        start_time = time_module.perf_counter()
        result = engine.calculate_offset(input_data)
        end_time = time_module.perf_counter()
        
        execution_time = (end_time - start_time) * 1000  # Convert to ms
        
        assert execution_time < 1.0  # Less than 1ms
        assert isinstance(result, OffsetResult)

    def test_weighted_combination_logic(self):
        """Test the weighted combination of rule-based and learned offsets."""
        config = {"max_offset": 5.0, "enable_learning": True}
        engine = OffsetEngine(config)
        
        # Mock learner to skip calibration phase and provide learned offset
        engine._learner = Mock()
        engine._learner.get_statistics.return_value = Mock(samples_collected=25)  # > 10
        engine._learner._enhanced_samples = [Mock()]  # Has samples
        engine._learner.predict.return_value = 1.5  # Learned offset
        
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=22.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=1
        )
        
        result = engine.calculate_offset(input_data)
        
        # Should use learning since we have sufficient data
        # The exact offset will be a weighted combination of rule-based (2.0) and learned (1.5)
        # With 0.8 confidence, it should be: 0.2 * 2.0 + 0.8 * 1.5 = 0.4 + 1.2 = 1.6
        assert result.offset != 2.0  # Should not be pure rule-based
        assert 1.5 <= result.offset <= 2.0  # Should be between learned and rule-based
        assert "learning" in result.reason.lower()
        assert result.confidence > 0.5

    def test_learning_pattern_differentiation_with_power(self):
        """Test that learning can differentiate patterns based on power state."""
        config = {"max_offset": 5.0, "enable_learning": True}
        engine = OffsetEngine(config)
        
        # Record different patterns for different power states
        high_power_input = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=22.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=300.0,  # High power
            time_of_day=time(14, 30),
            day_of_week=1
        )
        
        low_power_input = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=22.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=50.0,  # Low power
            time_of_day=time(14, 30),
            day_of_week=1
        )
        
        # Record different actual outcomes for different power states
        for _ in range(20):
            engine.record_actual_performance(
                predicted_offset=2.0,
                actual_offset=1.5,  # Better for high power
                input_data=high_power_input
            )
            
            engine.record_actual_performance(
                predicted_offset=2.0,
                actual_offset=2.5,  # Worse for low power
                input_data=low_power_input
            )
        
        # Learning should differentiate between power states
        assert len(engine._learner._enhanced_samples) == 40

    def test_graceful_degradation_when_power_unavailable(self):
        """Test graceful degradation when power sensor becomes unavailable."""
        config = {"max_offset": 5.0, "enable_learning": True}
        engine = OffsetEngine(config)
        
        # Train with power data
        input_with_power = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=22.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=1
        )
        
        for _ in range(20):
            engine.record_actual_performance(-2.0, -1.8, input_with_power)
        
        # Test with power unavailable
        input_without_power = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=22.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=None,  # No power data
            time_of_day=time(14, 30),
            day_of_week=1
        )
        
        result = engine.calculate_offset(input_without_power)
        
        # Should still work, just with different reasoning
        assert isinstance(result, OffsetResult)
        assert "power unavailable" in result.reason.lower() or "temperature-only" in result.reason.lower()

    def test_backward_compatibility_all_existing_tests_pass(self):
        """Test that all existing functionality remains unchanged."""
        config = {"max_offset": 5.0}  # Default config without learning
        engine = OffsetEngine(config)
        
        # Test basic offset calculation (existing test)
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=22.0,
            outdoor_temp=None,
            mode="none",
            power_consumption=None,
            time_of_day=time(12, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        # Should behave exactly as before (with corrected offset calculation)
        assert result.offset == 2.0  # AC sensor warmer than room, positive offset
        assert not result.clamped
        assert "AC sensor warmer than room" in result.reason
        assert result.confidence >= 0.5
        
        # Learning methods should exist but be no-ops
        assert hasattr(engine, 'record_actual_performance')
        assert hasattr(engine, 'get_learning_info')
        
        # Should not raise exceptions
        engine.record_actual_performance(2.0, 1.8, input_data)
        learning_info = engine.get_learning_info()
        assert learning_info["enabled"] is False

    def test_error_handling_in_learning_components(self):
        """Test error handling in learning components."""
        config = {"max_offset": 5.0, "enable_learning": True}
        engine = OffsetEngine(config)
        
        # Mock learner to skip calibration phase and throw exception on predict
        engine._learner = Mock()
        engine._learner.get_statistics.return_value = Mock(samples_collected=25)  # > 10
        engine._learner._enhanced_samples = [Mock()]  # Has samples
        engine._learner.predict.side_effect = ValueError("Mock learning error")
        
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=22.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=1
        )
        
        result = engine.calculate_offset(input_data)
        
        # Should fall back to rule-based calculation
        assert isinstance(result, OffsetResult)
        assert result.offset == 2.0  # Rule-based fallback (corrected offset)
        assert "fallback" in result.reason.lower()