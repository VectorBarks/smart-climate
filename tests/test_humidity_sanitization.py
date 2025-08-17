"""Test suite for humidity learning data collection bug fix.

Tests the sanitization helper and fixes for handling non-numeric sensor values
that was causing learning data collection to stop on Aug 14.
"""
import pytest
from datetime import datetime, time
from unittest.mock import Mock, patch
from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.models import OffsetInput


class TestHumiditySanitization:
    """Test humidity data sanitization and robust error handling."""

    @pytest.fixture
    def offset_engine(self):
        """Create a test OffsetEngine instance."""
        config = {
            "learning_enabled": True,
            "max_offset": 5.0,
            "power_idle_threshold": 50,
            "power_min_threshold": 100,
            "power_max_threshold": 3000,
        }
        engine = OffsetEngine(config)
        
        # Enable learning for testing
        engine._enable_learning = True
        
        # Disable validation to focus on sanitization testing
        engine._validate_feedback = Mock(return_value=True)
        engine._validate_learning_data = Mock(return_value=True)
        
        # Mock the learner
        engine._learner = Mock()
        engine._learner.add_sample = Mock()
        
        return engine

    def test_sanitize_float_with_valid_numeric_values(self, offset_engine):
        """Test _sanitize_float with valid numeric inputs."""
        # Test valid float
        result = offset_engine._sanitize_float(45.5, "test_param")
        assert result == 45.5
        
        # Test valid int
        result = offset_engine._sanitize_float(50, "test_param")
        assert result == 50.0
        
        # Test numeric string
        result = offset_engine._sanitize_float("42.3", "test_param")
        assert result == 42.3

    def test_sanitize_float_with_invalid_values(self, offset_engine):
        """Test _sanitize_float with invalid inputs returns None."""
        # Test None
        result = offset_engine._sanitize_float(None, "test_param")
        assert result is None
        
        # Test non-numeric string
        result = offset_engine._sanitize_float("unavailable", "test_param")
        assert result is None
        
        # Test "unknown"
        result = offset_engine._sanitize_float("unknown", "test_param")
        assert result is None
        
        # Test empty string
        result = offset_engine._sanitize_float("", "test_param")
        assert result is None

    def test_sanitize_float_with_out_of_range_values(self, offset_engine):
        """Test _sanitize_float rejects values outside reasonable range."""
        # Test value too high
        result = offset_engine._sanitize_float(15000, "test_param")
        assert result is None
        
        # Test value too low
        result = offset_engine._sanitize_float(-15000, "test_param")
        assert result is None

    @patch('custom_components.smart_climate.offset_engine._LOGGER')
    def test_sanitize_float_logs_warnings(self, mock_logger, offset_engine):
        """Test that _sanitize_float logs warnings for invalid conversions."""
        # Test with a non-numeric string that should trigger warning
        offset_engine._sanitize_float("not_a_number", "humidity")
        mock_logger.warning.assert_called_once()
        
        # Check that the warning mentions the parameter name and value
        call_args = mock_logger.warning.call_args[0]
        # First arg is the format string, second and third are the parameter values
        assert len(call_args) == 3
        assert "humidity" == call_args[1]  # param_name argument
        assert "not_a_number" == call_args[2]  # value argument

    def test_record_actual_performance_with_valid_humidity(self, offset_engine):
        """Test record_actual_performance works with valid humidity values."""
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=25.0,
            outdoor_temp=30.0,
            mode="cool",
            power_consumption=200.0,
            time_of_day=time(14, 30),
            day_of_week=1,
            indoor_humidity=45.5,
            outdoor_humidity=60.2
        )
        
        # This should not raise an exception
        offset_engine.record_actual_performance(2.0, 1.5, input_data)
        
        # Verify add_sample was called with sanitized values
        offset_engine._learner.add_sample.assert_called_once()
        call_kwargs = offset_engine._learner.add_sample.call_args[1]
        assert call_kwargs['indoor_humidity'] == 45.5
        assert call_kwargs['outdoor_humidity'] == 60.2

    def test_record_actual_performance_with_invalid_humidity_strings(self, offset_engine):
        """Test record_actual_performance handles string humidity values gracefully."""
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=25.0,
            outdoor_temp=30.0,
            mode="cool",
            power_consumption=200.0,
            time_of_day=time(14, 30),
            day_of_week=1,
            indoor_humidity="unavailable",  # String value that caused the bug
            outdoor_humidity="unknown"       # Another string value
        )
        
        # This should not raise an exception
        offset_engine.record_actual_performance(2.0, 1.5, input_data)
        
        # Verify add_sample was called with None for invalid humidity values
        offset_engine._learner.add_sample.assert_called_once()
        call_kwargs = offset_engine._learner.add_sample.call_args[1]
        assert call_kwargs['indoor_humidity'] is None
        assert call_kwargs['outdoor_humidity'] is None

    def test_record_actual_performance_with_mixed_humidity_validity(self, offset_engine):
        """Test record_actual_performance with one valid and one invalid humidity."""
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=25.0,
            outdoor_temp=30.0,
            mode="cool",
            power_consumption=200.0,
            time_of_day=time(14, 30),
            day_of_week=1,
            indoor_humidity=47.3,           # Valid numeric
            outdoor_humidity="unavailable"  # Invalid string
        )
        
        # This should not raise an exception
        offset_engine.record_actual_performance(2.0, 1.5, input_data)
        
        # Verify add_sample was called with correct values
        offset_engine._learner.add_sample.assert_called_once()
        call_kwargs = offset_engine._learner.add_sample.call_args[1]
        assert call_kwargs['indoor_humidity'] == 47.3
        assert call_kwargs['outdoor_humidity'] is None

    def test_record_actual_performance_with_none_humidity_values(self, offset_engine):
        """Test record_actual_performance handles None humidity values."""
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=25.0,
            outdoor_temp=30.0,
            mode="cool",
            power_consumption=200.0,
            time_of_day=time(14, 30),
            day_of_week=1,
            indoor_humidity=None,
            outdoor_humidity=None
        )
        
        # This should not raise an exception
        offset_engine.record_actual_performance(2.0, 1.5, input_data)
        
        # Verify add_sample was called with None values
        offset_engine._learner.add_sample.assert_called_once()
        call_kwargs = offset_engine._learner.add_sample.call_args[1]
        assert call_kwargs['indoor_humidity'] is None
        assert call_kwargs['outdoor_humidity'] is None

    @patch('custom_components.smart_climate.offset_engine._LOGGER')
    def test_record_actual_performance_logs_detailed_errors(self, mock_logger, offset_engine):
        """Test that record_actual_performance logs detailed error information."""
        # Mock add_sample to raise an exception
        offset_engine._learner.add_sample.side_effect = ValueError("Test error")
        
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=25.0,
            outdoor_temp=30.0,
            mode="cool",
            power_consumption=200.0,
            time_of_day=time(14, 30),
            day_of_week=1,
            indoor_humidity="unavailable",
            outdoor_humidity=50.0
        )
        
        # Should not raise exception due to try/catch
        offset_engine.record_actual_performance(2.0, 1.5, input_data)
        
        # Verify detailed error logging was called
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0]
        assert "Failed to record learning sample" in call_args[0]
        # Check that exc_info=True was passed as keyword argument
        call_kwargs = mock_logger.error.call_args[1]
        assert call_kwargs.get('exc_info') is True

    def test_sanitize_float_with_numeric_strings(self, offset_engine):
        """Test _sanitize_float correctly converts numeric strings."""
        # Test integer string
        result = offset_engine._sanitize_float("42", "test_param")
        assert result == 42.0
        
        # Test float string with decimals
        result = offset_engine._sanitize_float("45.67", "test_param")
        assert result == 45.67
        
        # Test negative numeric string
        result = offset_engine._sanitize_float("-10.5", "test_param")
        assert result == -10.5

    def test_sanitize_float_edge_case_values(self, offset_engine):
        """Test _sanitize_float with edge case numeric values."""
        # Test zero
        result = offset_engine._sanitize_float(0, "test_param")
        assert result == 0.0
        
        # Test very small positive number
        result = offset_engine._sanitize_float(0.001, "test_param")
        assert result == 0.001
        
        # Test boundary values (should pass)
        result = offset_engine._sanitize_float(100.0, "test_param")
        assert result == 100.0

    def test_complete_humidity_learning_workflow(self, offset_engine):
        """Integration test for the complete humidity learning workflow."""
        # Test multiple samples with various humidity states
        test_cases = [
            {
                "indoor_humidity": 45.5,
                "outdoor_humidity": 60.0,
                "expected_indoor": 45.5,
                "expected_outdoor": 60.0
            },
            {
                "indoor_humidity": "unavailable",
                "outdoor_humidity": "unknown",
                "expected_indoor": None,
                "expected_outdoor": None
            },
            {
                "indoor_humidity": None,
                "outdoor_humidity": 55.2,
                "expected_indoor": None,
                "expected_outdoor": 55.2
            },
            {
                "indoor_humidity": "50.5",  # Numeric string
                "outdoor_humidity": 65,     # Integer
                "expected_indoor": 50.5,
                "expected_outdoor": 65.0
            }
        ]
        
        for i, case in enumerate(test_cases):
            offset_engine._learner.add_sample.reset_mock()
            
            input_data = OffsetInput(
                ac_internal_temp=24.0,
                room_temp=25.0,
                outdoor_temp=30.0,
                mode="cool",
                power_consumption=200.0,
                time_of_day=time(14, 30),
                day_of_week=1,
                indoor_humidity=case["indoor_humidity"],
                outdoor_humidity=case["outdoor_humidity"]
            )
            
            # This should not raise an exception for any case
            offset_engine.record_actual_performance(2.0, 1.5, input_data)
            
            # Verify correct sanitization
            offset_engine._learner.add_sample.assert_called_once()
            call_kwargs = offset_engine._learner.add_sample.call_args[1]
            assert call_kwargs['indoor_humidity'] == case["expected_indoor"], f"Case {i}: indoor humidity mismatch"
            assert call_kwargs['outdoor_humidity'] == case["expected_outdoor"], f"Case {i}: outdoor humidity mismatch"