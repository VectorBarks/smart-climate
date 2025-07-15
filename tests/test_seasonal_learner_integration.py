"""Tests for SeasonalLearner data access methods for dashboard integration.

ABOUTME: Tests for SeasonalLearner data exposure methods.
Ensures proper data formatting and graceful error handling for dashboard requirements.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import time

from custom_components.smart_climate.seasonal_learner import (
    SeasonalHysteresisLearner,
    LearnedPattern
)


class TestSeasonalLearnerDataAccess:
    """Test data access methods for dashboard integration."""
    
    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = Mock()
        hass.states.get.return_value = None
        hass.data = {}
        return hass
    
    @pytest.fixture
    def learner(self, mock_hass):
        """Create a SeasonalHysteresisLearner instance."""
        with patch('custom_components.smart_climate.seasonal_learner.Store'):
            return SeasonalHysteresisLearner(mock_hass, "sensor.outdoor_temp")
    
    def test_get_pattern_count_no_data(self, learner):
        """Test pattern count with no data."""
        assert learner.get_pattern_count() == 0
    
    def test_get_pattern_count_with_data(self, learner):
        """Test pattern count with learned patterns."""
        # Add some patterns
        learner._patterns = [
            LearnedPattern(time.time(), 25.0, 23.0, 30.0),
            LearnedPattern(time.time(), 26.0, 24.0, 31.0),
            LearnedPattern(time.time(), 24.0, 22.0, 29.0),
        ]
        
        assert learner.get_pattern_count() == 3
    
    def test_get_outdoor_temp_bucket_no_sensor(self, learner):
        """Test bucket generation when no outdoor sensor configured."""
        learner._outdoor_sensor_id = None
        assert learner.get_outdoor_temp_bucket() is None
    
    def test_get_outdoor_temp_bucket_sensor_unavailable(self, learner, mock_hass):
        """Test bucket generation when sensor is unavailable."""
        mock_hass.states.get.return_value = None
        assert learner.get_outdoor_temp_bucket() is None
    
    def test_get_outdoor_temp_bucket_invalid_state(self, learner, mock_hass):
        """Test bucket generation with invalid sensor state."""
        state = Mock()
        state.state = "unavailable"
        mock_hass.states.get.return_value = state
        
        assert learner.get_outdoor_temp_bucket() is None
    
    def test_get_outdoor_temp_bucket_valid_temps(self, learner, mock_hass):
        """Test bucket generation with valid temperatures."""
        # Test various temperature ranges
        test_cases = [
            (22.5, "20-25°C"),  # Mid bucket
            (20.0, "20-25°C"),  # Lower boundary
            (24.9, "20-25°C"),  # Upper boundary
            (25.0, "25-30°C"),  # Next bucket
            (19.9, "15-20°C"),  # Previous bucket
            (-2.5, "-5-0°C"),   # Negative range
            (0.0, "0-5°C"),     # Zero boundary
            (-0.1, "-5-0°C"),   # Just below zero
        ]
        
        for temp, expected_bucket in test_cases:
            state = Mock()
            state.state = str(temp)
            mock_hass.states.get.return_value = state
            
            assert learner.get_outdoor_temp_bucket() == expected_bucket, \
                f"Temperature {temp} should be in bucket {expected_bucket}"
    
    def test_get_seasonal_accuracy_no_patterns(self, learner):
        """Test accuracy calculation with no patterns."""
        assert learner.get_seasonal_accuracy() == 0.0
    
    def test_get_seasonal_accuracy_insufficient_patterns(self, learner):
        """Test accuracy with less than minimum required patterns."""
        # Add only 2 patterns (less than min_samples_for_bucket=3)
        learner._patterns = [
            LearnedPattern(time.time(), 25.0, 23.0, 30.0),
            LearnedPattern(time.time(), 26.0, 24.0, 31.0),
        ]
        
        # Should return 0 as insufficient data
        assert learner.get_seasonal_accuracy() == 0.0
    
    def test_get_seasonal_accuracy_with_patterns(self, learner, mock_hass):
        """Test accuracy calculation with sufficient patterns."""
        # Mock outdoor temp at 30°C
        state = Mock()
        state.state = "30.0"
        mock_hass.states.get.return_value = state
        
        # Add patterns with varying deltas
        current_time = time.time()
        learner._patterns = [
            LearnedPattern(current_time, 25.0, 23.0, 30.0),  # delta=2.0
            LearnedPattern(current_time, 26.0, 23.5, 30.5),  # delta=2.5
            LearnedPattern(current_time, 24.0, 22.0, 29.5),  # delta=2.0
            LearnedPattern(current_time, 25.5, 23.5, 30.2),  # delta=2.0
        ]
        
        # Calculate expected accuracy
        # Median delta = 2.0
        # Deviations: 0.0, 0.5, 0.0, 0.0
        # Average deviation = 0.125
        # Accuracy = max(0, 100 - (0.125 * 100)) = 87.5
        
        accuracy = learner.get_seasonal_accuracy()
        assert 85.0 <= accuracy <= 90.0, f"Expected accuracy around 87.5, got {accuracy}"
    
    def test_get_seasonal_accuracy_perfect_consistency(self, learner, mock_hass):
        """Test accuracy with perfectly consistent patterns."""
        state = Mock()
        state.state = "25.0"
        mock_hass.states.get.return_value = state
        
        # Add patterns with identical deltas
        current_time = time.time()
        learner._patterns = [
            LearnedPattern(current_time, 25.0, 23.0, 25.0),  # delta=2.0
            LearnedPattern(current_time, 26.0, 24.0, 25.0),  # delta=2.0
            LearnedPattern(current_time, 24.0, 22.0, 25.0),  # delta=2.0
        ]
        
        # Perfect consistency should give 100% accuracy
        assert learner.get_seasonal_accuracy() == 100.0
    
    def test_get_seasonal_contribution_exists(self, learner):
        """Test that get_seasonal_contribution method exists."""
        # This method might already exist, so we test both cases
        contribution = learner.get_seasonal_contribution()
        assert isinstance(contribution, (int, float))
        assert 0 <= contribution <= 100
    
    def test_get_seasonal_contribution_no_patterns(self, learner):
        """Test contribution calculation with no patterns."""
        if hasattr(learner, 'get_seasonal_contribution'):
            assert learner.get_seasonal_contribution() == 0.0
        else:
            # If method doesn't exist, we'll add it
            pytest.skip("get_seasonal_contribution not yet implemented")
    
    def test_method_error_handling(self, learner):
        """Test that all methods handle errors gracefully."""
        # Simulate internal error by setting patterns to None
        learner._patterns = None
        
        # All methods should return safe defaults
        assert learner.get_pattern_count() == 0
        assert learner.get_outdoor_temp_bucket() is None
        assert learner.get_seasonal_accuracy() == 0.0
        
        if hasattr(learner, 'get_seasonal_contribution'):
            assert learner.get_seasonal_contribution() == 0.0
    
    def test_bucket_formatting(self, learner, mock_hass):
        """Test bucket string formatting is consistent."""
        # Test edge cases for bucket formatting
        test_temps = [-10, -5, 0, 5, 10, 15, 20, 25, 30, 35, 40]
        
        for temp in test_temps:
            state = Mock()
            state.state = str(temp)
            mock_hass.states.get.return_value = state
            
            bucket = learner.get_outdoor_temp_bucket()
            if bucket:
                # Check format: "X-Y°C" where X and Y are integers
                assert "°C" in bucket, f"Bucket {bucket} missing °C suffix"
                
                # Remove °C suffix and handle negative numbers properly
                bucket_nums = bucket.replace("°C", "")
                
                # Parse the bucket range - handle negative numbers
                import re
                match = re.match(r'^(-?\d+)-(-?\d+)°C$', bucket)
                assert match, f"Invalid bucket format: {bucket}"
                
                low = int(match.group(1))
                high = int(match.group(2))
                
                assert high == low + 5, f"Bucket range should be 5°C: {bucket} (low={low}, high={high})"
    
    def test_data_types(self, learner):
        """Test that all methods return correct data types."""
        # Pattern count should be int
        count = learner.get_pattern_count()
        assert isinstance(count, int)
        assert count >= 0
        
        # Bucket should be str or None
        bucket = learner.get_outdoor_temp_bucket()
        assert bucket is None or isinstance(bucket, str)
        
        # Accuracy should be float
        accuracy = learner.get_seasonal_accuracy()
        assert isinstance(accuracy, (int, float))
        assert 0 <= accuracy <= 100
        
        # Contribution should be float (if exists)
        if hasattr(learner, 'get_seasonal_contribution'):
            contribution = learner.get_seasonal_contribution()
            assert isinstance(contribution, (int, float))
            assert 0 <= contribution <= 100