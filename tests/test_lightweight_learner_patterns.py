"""Tests for LightweightOffsetLearner pattern building fixes.

ABOUTME: Tests the critical bug fix where add_sample() wasn't calling update_pattern(),
leaving pattern structures empty despite having enhanced_samples data.
"""

import pytest
from datetime import datetime, time
from unittest.mock import patch, MagicMock
from typing import Dict, Any

from custom_components.smart_climate.lightweight_learner import (
    LightweightOffsetLearner,
)


class TestPatternBuilding:
    """Test suite for pattern building functionality fixes."""

    def test_add_sample_updates_patterns_basic(self):
        """Test that add_sample() properly updates pattern structures."""
        learner = LightweightOffsetLearner()
        
        # Initially patterns should be empty
        assert all(count == 0 for count in learner._time_pattern_counts)
        assert len(learner._power_state_patterns) == 0
        assert len(learner._temp_correlation_data) == 0
        
        # Mock datetime to control hour
        with patch('custom_components.smart_climate.lightweight_learner.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 8, 8, 14, 30)  # Hour 14
            
            # Add a sample - this should update patterns now
            learner.add_sample(
                predicted=1.0,
                actual=1.5,
                ac_temp=21.0,
                room_temp=22.0,
                outdoor_temp=25.0,
                mode="cool",
                power=150.0,
                hysteresis_state="cooling"
            )
        
        # Verify patterns were updated
        assert learner._time_pattern_counts[14] == 1, "Hour 14 should have 1 sample"
        assert learner._time_patterns[14] == 1.5, "Hour 14 should have actual offset"
        assert len(learner._temp_correlation_data) == 1, "Should have temperature correlation data"
        assert "cooling" in learner._power_state_patterns, "Should have power state pattern"
        assert learner._power_state_patterns["cooling"]["avg_offset"] == 1.5
        assert learner._power_state_patterns["cooling"]["count"] == 1

    def test_add_sample_updates_patterns_multiple_samples(self):
        """Test that multiple add_sample() calls build patterns correctly."""
        learner = LightweightOffsetLearner()
        
        # Mock datetime for different hours
        with patch('custom_components.smart_climate.lightweight_learner.datetime') as mock_datetime:
            # First sample at hour 10
            mock_datetime.now.return_value = datetime(2025, 8, 8, 10, 0)
            learner.add_sample(
                predicted=0.5,
                actual=1.0,
                ac_temp=20.0,
                room_temp=21.0,
                outdoor_temp=20.0,
                power=200.0
            )
            
            # Second sample at hour 15
            mock_datetime.now.return_value = datetime(2025, 8, 8, 15, 0)
            learner.add_sample(
                predicted=1.0,
                actual=2.0,
                ac_temp=22.0,
                room_temp=23.0,
                outdoor_temp=28.0,
                power=50.0
            )
        
        # Verify multiple hour patterns
        assert learner._time_pattern_counts[10] == 1
        assert learner._time_pattern_counts[15] == 1
        assert learner._time_patterns[10] == 1.0
        assert learner._time_patterns[15] == 2.0
        
        # Verify temperature correlation data
        assert len(learner._temp_correlation_data) == 2
        temp_data = list(learner._temp_correlation_data)
        assert temp_data[0]["outdoor_temp"] == 20.0
        assert temp_data[0]["offset"] == 1.0
        assert temp_data[1]["outdoor_temp"] == 28.0
        assert temp_data[1]["offset"] == 2.0

    def test_determine_power_state_helper(self):
        """Test the _determine_power_state() helper method."""
        learner = LightweightOffsetLearner()
        
        # Test None power
        assert learner._determine_power_state(None) is None
        
        # Test low power (idle)
        assert learner._determine_power_state(50.0) == "idle"
        assert learner._determine_power_state(0.0) == "idle"
        
        # Test high power (cooling)  
        assert learner._determine_power_state(150.0) == "cooling"
        assert learner._determine_power_state(500.0) == "cooling"
        
        # Test boundary conditions
        assert learner._determine_power_state(100.0) == "idle"  # At threshold
        assert learner._determine_power_state(100.1) == "cooling"  # Just above threshold

    def test_rebuild_patterns_from_enhanced_samples(self):
        """Test rebuilding patterns from existing enhanced samples."""
        learner = LightweightOffsetLearner()
        
        # Manually add enhanced samples (simulating the bug scenario)
        learner._enhanced_samples = [
            {
                "predicted": 0.5,
                "actual": 1.0,
                "ac_temp": 20.0,
                "room_temp": 21.0,
                "outdoor_temp": 20.0,
                "mode": "cool",
                "power": 200.0,
                "hysteresis_state": "cooling",
                "timestamp": "2025-08-08T10:30:00"
            },
            {
                "predicted": 1.0,
                "actual": 2.0,
                "ac_temp": 22.0,
                "room_temp": 23.0,
                "outdoor_temp": 28.0,
                "mode": "cool",
                "power": 50.0,
                "hysteresis_state": "idle",
                "timestamp": "2025-08-08T15:45:00"
            }
        ]
        
        # Patterns should be empty initially (bug scenario)
        assert all(count == 0 for count in learner._time_pattern_counts)
        assert len(learner._power_state_patterns) == 0
        assert len(learner._temp_correlation_data) == 0
        
        # Rebuild patterns
        learner.rebuild_patterns_from_enhanced_samples()
        
        # Verify patterns were built
        assert learner._time_pattern_counts[10] == 1  # Hour 10 from first timestamp
        assert learner._time_pattern_counts[15] == 1  # Hour 15 from second timestamp
        assert learner._time_patterns[10] == 1.0
        assert learner._time_patterns[15] == 2.0
        
        # Verify temperature correlation data
        assert len(learner._temp_correlation_data) == 2
        
        # Verify power state patterns
        assert "cooling" in learner._power_state_patterns
        assert "idle" in learner._power_state_patterns
        assert learner._power_state_patterns["cooling"]["avg_offset"] == 1.0
        assert learner._power_state_patterns["idle"]["avg_offset"] == 2.0

    def test_rebuild_patterns_idempotent(self):
        """Test that rebuild_patterns_from_enhanced_samples() is idempotent."""
        learner = LightweightOffsetLearner()
        
        # Add enhanced sample
        learner._enhanced_samples = [
            {
                "predicted": 0.5,
                "actual": 1.0,
                "ac_temp": 20.0,
                "room_temp": 21.0,
                "outdoor_temp": 20.0,
                "mode": "cool",
                "power": 200.0,
                "hysteresis_state": "cooling",
                "timestamp": "2025-08-08T10:30:00"
            }
        ]
        
        # First rebuild
        learner.rebuild_patterns_from_enhanced_samples()
        
        # Capture first state
        first_time_patterns = learner._time_patterns.copy()
        first_time_counts = learner._time_pattern_counts.copy()
        first_power_patterns = dict(learner._power_state_patterns)
        first_temp_data = list(learner._temp_correlation_data)
        
        # Second rebuild should produce same results
        learner.rebuild_patterns_from_enhanced_samples()
        
        # Verify results are identical
        assert learner._time_patterns == first_time_patterns
        assert learner._time_pattern_counts == first_time_counts
        assert learner._power_state_patterns == first_power_patterns
        assert list(learner._temp_correlation_data) == first_temp_data

    def test_rebuild_patterns_handles_malformed_samples(self):
        """Test that rebuild handles malformed enhanced samples gracefully."""
        learner = LightweightOffsetLearner()
        
        # Add mix of good and malformed samples
        learner._enhanced_samples = [
            # Good sample
            {
                "predicted": 0.5,
                "actual": 1.0,
                "ac_temp": 20.0,
                "room_temp": 21.0,
                "outdoor_temp": 20.0,
                "mode": "cool",
                "power": 200.0,
                "hysteresis_state": "cooling",
                "timestamp": "2025-08-08T10:30:00"
            },
            # Malformed timestamp
            {
                "predicted": 1.0,
                "actual": 2.0,
                "ac_temp": 22.0,
                "room_temp": 23.0,
                "outdoor_temp": 28.0,
                "mode": "cool",
                "power": 50.0,
                "hysteresis_state": "idle",
                "timestamp": "invalid-timestamp"
            },
            # Missing fields
            {
                "predicted": 0.8,
                "actual": 1.5,
                "ac_temp": 21.0,
                "room_temp": 22.0
                # Missing other fields
            }
        ]
        
        # Rebuild should handle malformed data gracefully
        learner.rebuild_patterns_from_enhanced_samples()
        
        # Should have processed at least the good sample
        assert learner._time_pattern_counts[10] == 1  # From good sample
        assert learner._time_patterns[10] == 1.0
        assert "cooling" in learner._power_state_patterns

    def test_rebuild_patterns_clears_existing_patterns(self):
        """Test that rebuild clears existing patterns before rebuilding."""
        learner = LightweightOffsetLearner()
        
        # Manually set some existing patterns
        learner._time_patterns[5] = 3.0
        learner._time_pattern_counts[5] = 2
        learner._power_state_patterns["existing"] = {"avg_offset": 5.0, "count": 3}
        learner._temp_correlation_data.append({"outdoor_temp": 15.0, "offset": 4.0})
        
        # Add enhanced sample with different data
        learner._enhanced_samples = [
            {
                "predicted": 0.5,
                "actual": 1.0,
                "ac_temp": 20.0,
                "room_temp": 21.0,
                "outdoor_temp": 20.0,
                "mode": "cool",
                "power": 200.0,
                "hysteresis_state": "cooling",
                "timestamp": "2025-08-08T10:30:00"
            }
        ]
        
        # Rebuild - should clear existing and build from enhanced samples
        learner.rebuild_patterns_from_enhanced_samples()
        
        # Old patterns should be gone
        assert learner._time_patterns[5] == 0.0
        assert learner._time_pattern_counts[5] == 0
        assert "existing" not in learner._power_state_patterns
        
        # New patterns should exist
        assert learner._time_patterns[10] == 1.0
        assert learner._time_pattern_counts[10] == 1
        assert "cooling" in learner._power_state_patterns

    def test_load_patterns_triggers_rebuild_when_needed(self):
        """Test that load_patterns() triggers rebuild when patterns are empty but samples exist."""
        learner = LightweightOffsetLearner()
        
        # Simulate loading data with enhanced samples but empty patterns (the bug scenario)
        pattern_data = {
            "version": "1.1",
            "time_patterns": {},  # Empty patterns
            "time_pattern_counts": {},  # Empty counts  
            "temp_correlation_data": [],  # Empty temp data
            "power_state_patterns": {},  # Empty power patterns
            "enhanced_samples": [  # But enhanced samples exist!
                {
                    "predicted": 0.5,
                    "actual": 1.0,
                    "ac_temp": 20.0,
                    "room_temp": 21.0,
                    "outdoor_temp": 20.0,
                    "mode": "cool",
                    "power": 200.0,
                    "hysteresis_state": "cooling",
                    "timestamp": "2025-08-08T10:30:00"
                }
            ],
            "sample_count": 1
        }
        
        # Load patterns - should trigger rebuild
        learner.load_patterns(pattern_data)
        
        # Verify rebuild occurred
        assert learner._time_pattern_counts[10] == 1  # Should have been rebuilt
        assert learner._time_patterns[10] == 1.0
        assert "cooling" in learner._power_state_patterns

    def test_load_patterns_no_rebuild_when_patterns_exist(self):
        """Test that load_patterns() doesn't rebuild when patterns already exist."""
        learner = LightweightOffsetLearner()
        
        # Simulate loading data with both patterns and enhanced samples
        pattern_data = {
            "version": "1.1",
            "time_patterns": {"10": 2.5},  # Existing patterns
            "time_pattern_counts": {"10": 3},  
            "temp_correlation_data": [{"outdoor_temp": 25.0, "offset": 2.5}],
            "power_state_patterns": {"cooling": {"avg_offset": 2.5, "count": 3}},
            "enhanced_samples": [
                {
                    "predicted": 0.5,
                    "actual": 1.0,
                    "ac_temp": 20.0,
                    "room_temp": 21.0,
                    "outdoor_temp": 20.0,
                    "mode": "cool",
                    "power": 200.0,
                    "hysteresis_state": "cooling",
                    "timestamp": "2025-08-08T10:30:00"
                }
            ],
            "sample_count": 1
        }
        
        # Load patterns - should NOT trigger rebuild since patterns exist
        learner.load_patterns(pattern_data)
        
        # Verify loaded patterns were preserved (not rebuilt)
        assert learner._time_pattern_counts[10] == 3  # Original count, not 1
        assert learner._time_patterns[10] == 2.5  # Original pattern, not 1.0
        assert learner._power_state_patterns["cooling"]["count"] == 3  # Original count

    def test_rebuild_patterns_empty_enhanced_samples(self):
        """Test rebuild with empty enhanced samples."""
        learner = LightweightOffsetLearner()
        
        # No enhanced samples
        assert len(learner._enhanced_samples) == 0
        
        # Rebuild should complete without errors
        learner.rebuild_patterns_from_enhanced_samples()
        
        # Patterns should remain empty
        assert all(count == 0 for count in learner._time_pattern_counts)
        assert len(learner._power_state_patterns) == 0
        assert len(learner._temp_correlation_data) == 0