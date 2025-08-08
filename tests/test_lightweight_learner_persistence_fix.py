"""Test for training data persistence synchronization fix.

Tests the fix for the issue where sample_count doesn't match actual
enhanced samples after loading from persistence.
"""

import pytest
from unittest.mock import patch
from custom_components.smart_climate.lightweight_learner import LightweightOffsetLearner


class TestPersistenceFix:
    """Test persistence synchronization fix."""
    
    def test_normal_save_and_load(self):
        """Test normal case where counts match."""
        learner = LightweightOffsetLearner()
        
        # Add samples
        for i in range(5):
            learner.add_sample(
                predicted=1.0 + i * 0.1,
                actual=1.1 + i * 0.1,
                ac_temp=22.0 + i,
                room_temp=24.0 + i,
                outdoor_temp=30.0 + i,
                mode="cool",
                power=150.0 + i * 10,
                hysteresis_state="cooling"
            )
        
        # Save and load
        patterns = learner.save_patterns()
        assert patterns["sample_count"] == 5
        assert len(patterns["enhanced_samples"]) == 5
        
        new_learner = LightweightOffsetLearner()
        new_learner.load_patterns(patterns)
        
        assert new_learner._sample_count == 5
        assert len(new_learner._enhanced_samples) == 5
        
        stats = new_learner.get_learning_stats()
        assert stats.samples_collected == 5
        assert stats.last_sample_time is not None
    
    def test_corrupted_sample_count_zero(self):
        """Test when sample_count is corrupted to 0."""
        learner = LightweightOffsetLearner()
        
        # Add samples
        for i in range(3):
            learner.add_sample(
                predicted=1.0,
                actual=1.1,
                ac_temp=22.0,
                room_temp=24.0,
                mode="cool"
            )
        
        patterns = learner.save_patterns()
        patterns["sample_count"] = 0  # Corrupt the count
        
        with patch('custom_components.smart_climate.lightweight_learner._LOGGER') as mock_logger:
            new_learner = LightweightOffsetLearner()
            new_learner.load_patterns(patterns)
            
            # Should log warning about mismatch
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "Sample count mismatch detected" in warning_call
        
        assert new_learner._sample_count == 3  # Fixed to actual count
        assert len(new_learner._enhanced_samples) == 3
    
    def test_corrupted_sample_count_too_high(self):
        """Test when sample_count is higher than actual samples."""
        learner = LightweightOffsetLearner()
        
        # Add samples
        for i in range(2):
            learner.add_sample(
                predicted=1.0,
                actual=1.1,
                ac_temp=22.0,
                room_temp=24.0,
                mode="cool"
            )
        
        patterns = learner.save_patterns()
        patterns["sample_count"] = 100  # Set count too high
        
        new_learner = LightweightOffsetLearner()
        new_learner.load_patterns(patterns)
        
        assert new_learner._sample_count == 2  # Fixed to actual count
        assert len(new_learner._enhanced_samples) == 2
    
    def test_version_10_compatibility(self):
        """Test version 1.0 patterns without enhanced samples."""
        patterns = {
            "version": "1.0",
            "time_patterns": {"12": 1.5, "13": 1.8},
            "time_pattern_counts": {"12": 10, "13": 15},
            "temp_correlation_data": [
                {"outdoor_temp": 30.0, "offset": 1.5}
            ],
            "power_state_patterns": {
                "cooling": {"avg_offset": 1.6, "count": 20}
            },
            "sample_count": 35
        }
        
        learner = LightweightOffsetLearner()
        learner.load_patterns(patterns)
        
        # Version 1.0 uses stored count since no enhanced samples
        assert learner._sample_count == 35
        assert len(learner._enhanced_samples) == 0
        
        stats = learner.get_learning_stats()
        assert stats.samples_collected == 35
        assert stats.last_sample_time is None  # No enhanced samples
    
    def test_invalid_enhanced_samples(self):
        """Test loading with some invalid enhanced samples."""
        patterns = {
            "version": "1.1",
            "time_patterns": {},
            "time_pattern_counts": {},
            "temp_correlation_data": [],
            "power_state_patterns": {},
            "enhanced_samples": [
                # Valid sample
                {
                    "predicted": 1.0,
                    "actual": 1.1,
                    "ac_temp": 22.0,
                    "room_temp": 24.0,
                    "timestamp": "2024-01-01T12:00:00"
                },
                # Invalid sample - missing required field
                {
                    "predicted": 1.0,
                    # Missing "actual"
                    "ac_temp": 22.0,
                    "room_temp": 24.0
                },
                # Invalid sample - wrong type
                {
                    "predicted": "not_a_float",
                    "actual": 1.1,
                    "ac_temp": 22.0,
                    "room_temp": 24.0
                }
            ],
            "sample_count": 3
        }
        
        with patch('custom_components.smart_climate.lightweight_learner._LOGGER') as mock_logger:
            learner = LightweightOffsetLearner()
            learner.load_patterns(patterns)
            
            # Should skip invalid samples
            assert len(learner._enhanced_samples) == 1  # Only 1 valid
            assert learner._sample_count == 2  # 1 from enhanced samples + 1 from rebuild pattern update
            
            # Should log warnings about invalid samples
            assert mock_logger.warning.call_count >= 2
    
    def test_save_synchronizes_count(self):
        """Test that save_patterns synchronizes count before saving."""
        learner = LightweightOffsetLearner()
        
        # Manually add to enhanced samples without updating count
        learner._enhanced_samples = [
            {
                "predicted": 1.0,
                "actual": 1.1,
                "ac_temp": 22.0,
                "room_temp": 24.0,
                "outdoor_temp": None,
                "mode": "cool",
                "power": None,
                "hysteresis_state": "no_power_sensor",
                "timestamp": "2024-01-01T12:00:00"
            }
        ]
        learner._sample_count = 0  # Mismatch
        
        with patch('custom_components.smart_climate.lightweight_learner._LOGGER') as mock_logger:
            patterns = learner.save_patterns()
            
            # Should log about synchronization
            mock_logger.debug.assert_called()
            debug_call = None
            for call in mock_logger.debug.call_args_list:
                if "Synchronizing sample count before save" in call[0][0]:
                    debug_call = call[0][0]
                    break
            assert debug_call is not None
        
        # Count should be synchronized in saved patterns
        assert patterns["sample_count"] == 1
        assert learner._sample_count == 1
    
    def test_empty_enhanced_samples(self):
        """Test when enhanced_samples is empty but sample_count is not."""
        patterns = {
            "version": "1.1",
            "time_patterns": {"12": 1.5},
            "time_pattern_counts": {"12": 10},
            "temp_correlation_data": [],
            "power_state_patterns": {},
            "enhanced_samples": [],
            "sample_count": 10
        }
        
        learner = LightweightOffsetLearner()
        learner.load_patterns(patterns)
        
        # Should use stored count when no enhanced samples
        assert learner._sample_count == 10
        assert len(learner._enhanced_samples) == 0