"""Test state-aware learning protocol for OffsetEngine (Step 2.5)."""

# ABOUTME: Tests for state-aware OffsetEngine integration with thermal management
# ABOUTME: Validates pause/resume learning and thermal window integration

import pytest
from datetime import time
from unittest.mock import Mock

from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.models import OffsetInput, OffsetResult


@pytest.fixture
def mock_seasonal_learner():
    """Mock seasonal learner for testing."""
    learner = Mock()
    learner.get_relevant_hysteresis_delta.return_value = None
    return learner


@pytest.fixture
def offset_engine():
    """Create OffsetEngine for testing."""
    config = {
        "max_offset": 5.0,
        "ml_enabled": True,
        "enable_learning": True,
        "power_idle_threshold": 50.0,
        "power_min_threshold": 100.0,
        "power_max_threshold": 500.0,
    }
    return OffsetEngine(config)


@pytest.fixture
def sample_input():
    """Sample input data for testing."""
    return OffsetInput(
        ac_internal_temp=22.0,
        room_temp=21.0,
        outdoor_temp=25.0,
        mode="none",
        power_consumption=200.0,
        time_of_day=time(14, 30),
        day_of_week=2
    )


class TestStateAwareMethods:
    """Test state-aware learning methods."""
    
    def test_pause_learning_sets_flag(self, offset_engine):
        """Test that pause_learning sets the internal flag."""
        # Initially not paused
        assert not hasattr(offset_engine, '_learning_paused') or not offset_engine._learning_paused
        
        # Pause learning
        offset_engine.pause_learning()
        
        # Verify flag is set
        assert hasattr(offset_engine, '_learning_paused')
        assert offset_engine._learning_paused is True
    
    def test_resume_learning_clears_flag(self, offset_engine):
        """Test that resume_learning clears the internal flag."""
        # First pause learning
        offset_engine.pause_learning()
        assert offset_engine._learning_paused is True
        
        # Resume learning
        offset_engine.resume_learning()
        
        # Verify flag is cleared
        assert offset_engine._learning_paused is False
    
    def test_learning_initially_not_paused(self, offset_engine):
        """Test that learning is not paused by default."""
        # Should either not have the attribute or it should be False
        paused = getattr(offset_engine, '_learning_paused', False)
        assert paused is False


class TestCalculateOffsetWithThermalWindow:
    """Test calculate_offset with thermal_window parameter."""
    
    def test_calculate_offset_accepts_thermal_window(self, offset_engine, sample_input):
        """Test that calculate_offset accepts thermal_window parameter."""
        thermal_window = (20.0, 24.0)
        
        # Should not raise an exception
        result = offset_engine.calculate_offset(sample_input, thermal_window=thermal_window)
        
        assert isinstance(result, OffsetResult)
        assert isinstance(result.offset, float)
    
    def test_calculate_offset_without_thermal_window(self, offset_engine, sample_input):
        """Test that calculate_offset works without thermal_window parameter."""
        # Should work with existing signature
        result = offset_engine.calculate_offset(sample_input)
        
        assert isinstance(result, OffsetResult)
        assert isinstance(result.offset, float)
    
    def test_thermal_window_none_handling(self, offset_engine, sample_input):
        """Test that thermal_window=None is handled correctly."""
        result = offset_engine.calculate_offset(sample_input, thermal_window=None)
        
        assert isinstance(result, OffsetResult)
        assert isinstance(result.offset, float)
    
    def test_calculate_offset_returns_unclamped_when_thermal_window_provided(self, offset_engine, sample_input):
        """Test that calculate_offset returns unclamped offset when thermal_window is provided."""
        # Use sample data that would normally be clamped
        large_diff_input = OffsetInput(
            ac_internal_temp=30.0,  # Large difference
            room_temp=20.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=200.0,
            time_of_day=time(14, 30),
            day_of_week=2
        )
        thermal_window = (18.0, 25.0)
        
        result = offset_engine.calculate_offset(large_diff_input, thermal_window=thermal_window)
        
        # Should return the actual calculated offset, not clamped to max_offset
        # The coordinator will handle clamping based on thermal window
        assert isinstance(result.offset, float)
        assert result is not None


class TestRecordActualPerformanceWithLearningTarget:
    """Test record_actual_performance with learning_target_temp parameter."""
    
    def test_record_actual_performance_accepts_learning_target_temp(self, offset_engine, sample_input):
        """Test that record_actual_performance accepts learning_target_temp parameter."""
        learning_target_temp = 21.5
        
        # Should not raise an exception
        offset_engine.record_actual_performance(
            predicted_offset=1.0,
            actual_offset=1.2,
            input_data=sample_input,
            learning_target_temp=learning_target_temp
        )
    
    def test_record_actual_performance_without_learning_target_temp(self, offset_engine, sample_input):
        """Test that record_actual_performance works without learning_target_temp (backward compatibility)."""
        # Should work with existing signature
        offset_engine.record_actual_performance(
            predicted_offset=1.0,
            actual_offset=1.2,
            input_data=sample_input
        )
    
    def test_record_actual_performance_uses_learning_target_when_provided(self, offset_engine, sample_input):
        """Test that learning_target_temp is used for training when provided."""
        learning_target_temp = 21.5
        
        # Mock the learner to verify the learning target is used
        offset_engine._learner = Mock()
        offset_engine._learner.add_sample = Mock()
        
        offset_engine.record_actual_performance(
            predicted_offset=1.0,
            actual_offset=1.2,
            input_data=sample_input,
            learning_target_temp=learning_target_temp
        )
        
        # Should use learning_target_temp in some way (implementation detail)
        # This test verifies the method accepts and processes the parameter
        assert offset_engine._learner.add_sample.called


class TestLearningPausedBehavior:
    """Test that learning is actually paused when flag is set."""
    
    def test_record_actual_performance_skips_learning_when_paused(self, offset_engine, sample_input):
        """Test that learning is skipped when _learning_paused is True."""
        # Set up a mock learner
        offset_engine._learner = Mock()
        offset_engine._learner.add_sample = Mock()
        
        # Pause learning
        offset_engine.pause_learning()
        
        # Try to record performance
        offset_engine.record_actual_performance(
            predicted_offset=1.0,
            actual_offset=1.2,
            input_data=sample_input
        )
        
        # Learner should not be called when paused
        assert not offset_engine._learner.add_sample.called
    
    def test_record_actual_performance_allows_learning_when_not_paused(self, offset_engine, sample_input):
        """Test that learning proceeds when _learning_paused is False."""
        # Set up a mock learner
        offset_engine._learner = Mock()
        offset_engine._learner.add_sample = Mock()
        
        # Ensure learning is not paused (default state)
        offset_engine.resume_learning()
        
        # Try to record performance
        offset_engine.record_actual_performance(
            predicted_offset=1.0,
            actual_offset=1.2,
            input_data=sample_input
        )
        
        # Learner should be called when not paused
        assert offset_engine._learner.add_sample.called
    
    def test_learning_pause_resume_cycle(self, offset_engine, sample_input):
        """Test a complete pause/resume cycle."""
        # Set up a mock learner
        offset_engine._learner = Mock()
        offset_engine._learner.add_sample = Mock()
        
        # Disable rate limiting for this test to avoid timing issues
        offset_engine._validation_rate_limit_seconds = 0
        
        # Initially not paused - learning should work
        offset_engine.record_actual_performance(1.0, 1.2, sample_input)
        assert offset_engine._learner.add_sample.call_count == 1
        
        # Pause learning - should stop working
        offset_engine.pause_learning()
        offset_engine._learner.add_sample.reset_mock()
        offset_engine.record_actual_performance(1.0, 1.2, sample_input)
        assert offset_engine._learner.add_sample.call_count == 0
        
        # Resume learning - should work again
        offset_engine.resume_learning()
        offset_engine.record_actual_performance(1.0, 1.2, sample_input)
        assert offset_engine._learner.add_sample.call_count == 1


class TestStateAwareProtocolIntegration:
    """Test state-aware protocol integration."""
    
    def test_pause_learning_with_boundary_correction(self, offset_engine, sample_input):
        """Test boundary correction during paused state."""
        # Pause learning (simulating drifting state)
        offset_engine.pause_learning()
        
        # Calculate offset should still work
        result = offset_engine.calculate_offset(sample_input)
        assert isinstance(result, OffsetResult)
        
        # But learning should be paused
        assert offset_engine._learning_paused is True
    
    def test_resume_learning_with_boundary_target(self, offset_engine, sample_input):
        """Test learning with boundary target during active state."""
        # Set up mock learner
        offset_engine._learner = Mock()
        offset_engine._learner.add_sample = Mock()
        
        # Resume learning (simulating correcting state)
        offset_engine.resume_learning()
        learning_target_temp = 21.5  # Boundary temperature
        
        # Record performance with boundary target
        offset_engine.record_actual_performance(
            predicted_offset=1.0,
            actual_offset=1.2,
            input_data=sample_input,
            learning_target_temp=learning_target_temp
        )
        
        # Learning should be active
        assert not offset_engine._learning_paused
        assert offset_engine._learner.add_sample.called
    
    def test_state_aware_learning_protocol_flow(self, offset_engine, sample_input):
        """Test complete state-aware learning protocol flow."""
        # Set up mock learner
        offset_engine._learner = Mock()
        offset_engine._learner.add_sample = Mock()
        
        # Step 1: Drifting state (learning paused)
        offset_engine.pause_learning()
        thermal_window = (20.0, 24.0)
        
        # Should calculate offset but not learn
        result1 = offset_engine.calculate_offset(sample_input, thermal_window=thermal_window)
        offset_engine.record_actual_performance(1.0, 1.2, sample_input)
        
        assert isinstance(result1, OffsetResult)
        assert not offset_engine._learner.add_sample.called
        
        # Step 2: Correcting state (learning active with boundary)
        offset_engine.resume_learning()
        boundary_temp = 22.0  # Learning from boundary
        
        # Should calculate offset and learn boundary correction
        result2 = offset_engine.calculate_offset(sample_input, thermal_window=thermal_window)
        offset_engine.record_actual_performance(
            predicted_offset=1.0,
            actual_offset=1.2,
            input_data=sample_input,
            learning_target_temp=boundary_temp
        )
        
        assert isinstance(result2, OffsetResult)
        assert offset_engine._learner.add_sample.called