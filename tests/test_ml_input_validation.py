"""Tests for ML input validation security features.

ABOUTME: Tests security validation of ML training data to prevent data poisoning.
Comprehensive test coverage for bounds checking, rate limiting, and timestamp validation.
"""

import pytest
import time
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.models import OffsetInput


class TestMLInputValidation:
    """Test ML input validation security features."""

    @pytest.fixture
    def config(self):
        """Standard test configuration."""
        return {
            "max_offset": 5.0,
            "enable_learning": True,
            "power_sensor": "sensor.power",
        }

    @pytest.fixture
    def offset_engine(self, config):
        """Create offset engine with learning enabled."""
        engine = OffsetEngine(config)
        return engine

    @pytest.fixture
    def valid_input_data(self):
        """Valid input data for testing."""
        return OffsetInput(
            ac_internal_temp=24.0,
            room_temp=22.0,
            outdoor_temp=25.0,
            mode="cool",
            power_consumption=150.0,
            time_of_day=datetime.now().time(),
            day_of_week=1
        )

    def test_validate_feedback_valid_data_passes(self, offset_engine):
        """Test that valid feedback data passes validation."""
        current_time = time.time()
        
        # Test valid offset within bounds
        assert offset_engine._validate_feedback(2.5, 23.0, current_time) is True
        
        # Test edge case values (using past timestamps to avoid future/rate limit issues)
        past_time_1 = current_time - 200  # 200 seconds ago
        past_time_2 = current_time - 300  # 300 seconds ago
        assert offset_engine._validate_feedback(-10.0, 10.0, past_time_1) is True
        assert offset_engine._validate_feedback(10.0, 40.0, past_time_2) is True

    def test_validate_feedback_rejects_extreme_offsets(self, offset_engine):
        """Test that extreme offset values are rejected."""
        current_time = time.time()
        
        # Test offset too high
        assert offset_engine._validate_feedback(15.0, 23.0, current_time) is False
        
        # Test offset too low  
        assert offset_engine._validate_feedback(-15.0, 23.0, current_time) is False
        
        # Test exactly at bounds (should pass)
        assert offset_engine._validate_feedback(10.0, 23.0, current_time) is True
        assert offset_engine._validate_feedback(-10.0, 23.0, current_time) is True

    def test_validate_feedback_rejects_future_timestamps(self, offset_engine):
        """Test that future timestamps are rejected."""
        future_time = time.time() + 3600  # 1 hour in future
        
        assert offset_engine._validate_feedback(2.0, 23.0, future_time) is False

    def test_validate_feedback_rejects_invalid_temperatures(self, offset_engine):
        """Test that invalid temperature values are rejected."""
        current_time = time.time()
        
        # Test temperature too low
        assert offset_engine._validate_feedback(2.0, 5.0, current_time) is False
        
        # Test temperature too high
        assert offset_engine._validate_feedback(2.0, 50.0, current_time) is False
        
        # Test edge case temperatures (should pass)
        assert offset_engine._validate_feedback(2.0, 10.0, current_time) is True
        assert offset_engine._validate_feedback(2.0, 40.0, current_time) is True

    def test_validate_feedback_rate_limiting(self, offset_engine):
        """Test that rate limiting prevents too frequent samples."""
        base_time = time.time() - 300  # Start 5 minutes ago to avoid future timestamps
        
        # First sample should pass
        assert offset_engine._validate_feedback(2.0, 23.0, base_time) is True
        
        # Second sample within 60 seconds should be rejected
        assert offset_engine._validate_feedback(2.5, 23.5, base_time + 30) is False
        
        # Sample after 60 seconds should pass
        assert offset_engine._validate_feedback(2.5, 23.5, base_time + 65) is True

    def test_validate_feedback_logs_rejections(self, offset_engine, caplog):
        """Test that validation rejections are properly logged."""
        import logging
        caplog.set_level(logging.WARNING)
        
        current_time = time.time()
        
        # Test extreme offset logging
        offset_engine._validate_feedback(15.0, 23.0, current_time)
        assert "Invalid offset range: 15.0" in caplog.text
        
        # Test future timestamp logging
        future_time = time.time() + 3600
        offset_engine._validate_feedback(2.0, 23.0, future_time)
        assert "Future timestamp rejected" in caplog.text
        
        # Test invalid temperature logging
        offset_engine._validate_feedback(2.0, 5.0, current_time)
        assert "Invalid temperature: 5.0" in caplog.text

    def test_validate_feedback_rate_limit_logging(self, offset_engine, caplog):
        """Test that rate limiting is logged at debug level."""
        import logging
        caplog.set_level(logging.DEBUG)
        
        base_time = time.time() - 300  # Start 5 minutes ago to avoid future timestamps
        
        # First sample
        offset_engine._validate_feedback(2.0, 23.0, base_time)
        
        # Second sample should trigger rate limit
        offset_engine._validate_feedback(2.5, 23.5, base_time + 30)
        assert "Rate limit: too frequent samples" in caplog.text

    def test_record_feedback_with_validation_integration(self, offset_engine, valid_input_data):
        """Test that record_feedback integrates validation properly."""
        with patch.object(offset_engine, '_validate_feedback') as mock_validate:
            mock_validate.return_value = True
            
            # Should call validation and proceed
            offset_engine.record_feedback(2.0, 2.5, valid_input_data)
            mock_validate.assert_called_once()

    def test_record_feedback_rejects_invalid_data(self, offset_engine, valid_input_data, caplog):
        """Test that record_feedback rejects invalid data."""
        import logging
        caplog.set_level(logging.WARNING)
        
        with patch.object(offset_engine, '_validate_feedback') as mock_validate:
            mock_validate.return_value = False
            
            # Should call validation and NOT proceed with learning
            offset_engine.record_feedback(2.0, 2.5, valid_input_data)
            mock_validate.assert_called_once()
            
            # Should log rejection
            assert "Rejecting invalid feedback data" in caplog.text

    def test_record_actual_performance_with_validation_integration(self, offset_engine, valid_input_data):
        """Test that record_actual_performance integrates validation properly."""
        with patch.object(offset_engine, '_validate_feedback') as mock_validate:
            mock_validate.return_value = True
            
            # Should call validation and proceed
            offset_engine.record_actual_performance(2.0, 2.5, valid_input_data)
            mock_validate.assert_called_once()

    def test_record_actual_performance_rejects_invalid_data(self, offset_engine, valid_input_data, caplog):
        """Test that record_actual_performance rejects invalid data."""
        import logging
        caplog.set_level(logging.WARNING)
        
        with patch.object(offset_engine, '_validate_feedback') as mock_validate:
            mock_validate.return_value = False
            
            # Should call validation and NOT proceed with learning
            offset_engine.record_actual_performance(2.0, 2.5, valid_input_data)
            mock_validate.assert_called_once()
            
            # Should log rejection
            assert "Rejecting invalid feedback data" in caplog.text

    def test_validation_bounds_configurable(self):
        """Test that validation bounds can be configured."""
        config = {
            "max_offset": 5.0,
            "enable_learning": True,
            "power_sensor": "sensor.power",
            "validation_offset_min": -8.0,
            "validation_offset_max": 8.0,
            "validation_temp_min": 15.0,
            "validation_temp_max": 35.0,
        }
        
        engine = OffsetEngine(config)
        current_time = time.time()
        
        # Test custom bounds
        assert engine._validate_feedback(8.0, 35.0, current_time) is True
        assert engine._validate_feedback(-8.0, 15.0, current_time) is True
        assert engine._validate_feedback(9.0, 36.0, current_time) is False
        assert engine._validate_feedback(-9.0, 14.0, current_time) is False

    def test_validation_handles_none_values_gracefully(self, offset_engine):
        """Test that validation handles None values gracefully."""
        current_time = time.time()
        
        # Test None offset (should be rejected)
        assert offset_engine._validate_feedback(None, 23.0, current_time) is False
        
        # Test None temperature (should be rejected)
        assert offset_engine._validate_feedback(2.0, None, current_time) is False
        
        # Test None timestamp (should be rejected)
        assert offset_engine._validate_feedback(2.0, 23.0, None) is False

    def test_validation_handles_invalid_types(self, offset_engine):
        """Test that validation handles invalid data types gracefully."""
        current_time = time.time()
        
        # Test string values (should be rejected)
        assert offset_engine._validate_feedback("invalid", 23.0, current_time) is False
        assert offset_engine._validate_feedback(2.0, "invalid", current_time) is False
        
        # Test boolean values (should be rejected, even though they are technically numeric in Python)
        assert offset_engine._validate_feedback(True, 23.0, current_time) is False
        assert offset_engine._validate_feedback(2.0, False, current_time) is False

    def test_validation_performance_with_large_volumes(self, offset_engine):
        """Test that validation performs well with large volumes of data."""
        current_time = time.time()
        
        # Test multiple validations don't slow down significantly
        start_time = time.time()
        
        for i in range(1000):
            offset_engine._validate_feedback(2.0, 23.0, current_time + i * 120)  # 2 minutes apart
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert execution_time < 1.0, f"Validation took too long: {execution_time}s"

    def test_rate_limiting_resets_after_timeout(self, offset_engine):
        """Test that rate limiting properly resets after timeout period."""
        base_time = time.time() - 300  # Start 5 minutes ago to avoid future timestamps
        
        # First sample
        assert offset_engine._validate_feedback(2.0, 23.0, base_time) is True
        
        # Sample too soon (should be rejected)
        assert offset_engine._validate_feedback(2.5, 23.5, base_time + 30) is False
        
        # Sample after timeout (should pass)
        assert offset_engine._validate_feedback(2.5, 23.5, base_time + 65) is True
        
        # Another sample too soon (should be rejected again)
        assert offset_engine._validate_feedback(3.0, 24.0, base_time + 90) is False

    def test_validation_statistics_tracking(self, offset_engine):
        """Test that validation statistics are properly tracked."""
        current_time = time.time()
        
        # Valid samples
        offset_engine._validate_feedback(2.0, 23.0, current_time)
        offset_engine._validate_feedback(2.5, 23.5, current_time + 65)
        
        # Invalid samples
        offset_engine._validate_feedback(15.0, 23.0, current_time + 130)  # Invalid offset
        offset_engine._validate_feedback(2.0, 50.0, current_time + 195)   # Invalid temp
        
        # Check statistics if implemented
        if hasattr(offset_engine, 'get_validation_stats'):
            stats = offset_engine.get_validation_stats()
            assert stats['valid_samples'] == 2
            assert stats['invalid_samples'] == 2
            assert stats['rejection_rate'] == 0.5

    def test_validation_with_edge_case_values(self, offset_engine):
        """Test validation with edge case numeric values."""
        base_time = time.time() - 500  # Start far enough back to avoid future timestamps
        
        # Test very small positive values
        assert offset_engine._validate_feedback(0.01, 23.0, base_time) is True
        
        # Test very small negative values  
        assert offset_engine._validate_feedback(-0.01, 23.0, base_time + 65) is True
        
        # Test zero
        assert offset_engine._validate_feedback(0.0, 23.0, base_time + 130) is True
        
        # Test floating point precision edge cases
        assert offset_engine._validate_feedback(9.999999, 23.0, base_time + 195) is True
        assert offset_engine._validate_feedback(10.000001, 23.0, base_time + 260) is False