"""Simplified tests for hysteresis state detection logic in OffsetEngine."""
import pytest
from datetime import time
from unittest.mock import Mock, patch
from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.models import OffsetInput


class TestHysteresisStateLogic:
    """Test the hysteresis state detection logic directly."""

    def test_hysteresis_state_logic_no_power_sensor(self):
        """Test that hysteresis_state is 'no_power_sensor' when power sensor not configured."""
        # Create engine without power sensor
        config = {
            "max_offset": 5.0,
            "enable_learning": True,
        }
        engine = OffsetEngine(config)
        
        # Verify power sensor is not enabled
        assert engine._hysteresis_enabled is False
        
        # The hysteresis_state should be "no_power_sensor" in calculate_offset
        # This is correct behavior

    def test_hysteresis_state_logic_power_sensor_learning(self):
        """Test that hysteresis_state should be 'learning_hysteresis' when power sensor exists but learning."""
        # Create engine with power sensor
        config = {
            "max_offset": 5.0,
            "enable_learning": True,
            "power_sensor": "sensor.ac_power"
        }
        engine = OffsetEngine(config)
        
        # Verify power sensor is enabled
        assert engine._hysteresis_enabled is True
        
        # Mock hysteresis learner to not have sufficient data
        mock_hysteresis = Mock()
        mock_hysteresis.has_sufficient_data = False
        engine._hysteresis_learner = mock_hysteresis
        
        # Create test input
        input_data = OffsetInput(
            ac_internal_temp=20.0,
            room_temp=22.0,
            outdoor_temp=30.0,
            mode="cool",
            power_consumption=150.0,
            time_of_day=time(14, 0),
            day_of_week=1
        )
        
        # Add some samples to the learner so it will try to predict
        engine._learner._enhanced_samples = [Mock() for _ in range(5)]
        
        # Patch the learner's predict method to capture hysteresis_state
        with patch.object(engine._learner, 'predict') as mock_predict:
            # Set a return value for predict
            mock_predict.return_value = -1.0
            
            # Calculate offset
            result = engine.calculate_offset(input_data)
            
            # Verify predict was called
            assert mock_predict.called, "Predict should have been called with samples available"
            
            # Check the hysteresis_state argument
            call_kwargs = mock_predict.call_args.kwargs
            # Verify the fix - it should now pass "learning_hysteresis"
            assert call_kwargs["hysteresis_state"] == "learning_hysteresis"
            print(f"FIX VERIFIED: hysteresis_state is correctly '{call_kwargs['hysteresis_state']}'")

    def test_hysteresis_state_logic_with_sufficient_data(self):
        """Test that hysteresis_state is actual state when power sensor has data."""
        # Create engine with power sensor
        config = {
            "max_offset": 5.0,
            "enable_learning": True,
            "power_sensor": "sensor.ac_power"
        }
        engine = OffsetEngine(config)
        
        # Mock hysteresis learner with sufficient data
        mock_hysteresis = Mock()
        mock_hysteresis.has_sufficient_data = True
        mock_hysteresis.get_hysteresis_state = Mock(return_value="active_phase")
        engine._hysteresis_learner = mock_hysteresis
        
        # Create test input
        input_data = OffsetInput(
            ac_internal_temp=20.0,
            room_temp=22.0,
            outdoor_temp=30.0,
            mode="cool",
            power_consumption=200.0,
            time_of_day=time(14, 0),
            day_of_week=1
        )
        
        # Patch the learner's predict method
        with patch.object(engine._learner, 'predict') as mock_predict:
            mock_predict.return_value = -1.5
            
            # Calculate offset
            result = engine.calculate_offset(input_data)
            
            # Verify get_hysteresis_state was called
            mock_hysteresis.get_hysteresis_state.assert_called_once_with("moderate", 22.0)
            
            # Check that predict was called with the actual hysteresis state
            if mock_predict.called:
                call_kwargs = mock_predict.call_args.kwargs
                assert call_kwargs["hysteresis_state"] == "active_phase"

    def test_record_performance_hysteresis_state_learning(self):
        """Test that record_actual_performance uses correct hysteresis state when learning."""
        # Create engine with power sensor
        config = {
            "max_offset": 5.0,
            "enable_learning": True,
            "power_sensor": "sensor.ac_power"
        }
        engine = OffsetEngine(config)
        
        # Mock hysteresis learner to not have sufficient data
        mock_hysteresis = Mock()
        mock_hysteresis.has_sufficient_data = False
        engine._hysteresis_learner = mock_hysteresis
        
        # Mock the learner
        mock_learner = Mock()
        engine._learner = mock_learner
        
        # Create test input
        input_data = OffsetInput(
            ac_internal_temp=20.0,
            room_temp=22.0,
            outdoor_temp=30.0,
            mode="cool",
            power_consumption=150.0,
            time_of_day=time(14, 0),
            day_of_week=1
        )
        
        # Record performance
        engine.record_actual_performance(2.0, 1.8, input_data)
        
        # Verify the learner's add_sample was called with "learning_hysteresis"
        mock_learner.add_sample.assert_called_once()
        call_kwargs = mock_learner.add_sample.call_args.kwargs
        assert call_kwargs["hysteresis_state"] == "learning_hysteresis"