"""Tests for humidity data migration and model versioning."""

import pytest
from datetime import datetime
from typing import Dict, Any

from custom_components.smart_climate.lightweight_learner import LightweightOffsetLearner


class TestHumidityDataMigration:
    """Test suite for humidity data migration and model versioning."""

    def test_migration_from_v10_to_v12_adds_humidity_fields(self):
        """Test migration from version 1.0 to 1.2 preserves existing data and adds humidity fields."""
        # Create v1.0 format data (no enhanced_samples, no humidity)
        v10_data = {
            "version": "1.0",
            "time_patterns": {
                "14": 1.5
            },
            "time_pattern_counts": {
                "14": 3
            },
            "temp_correlation_data": [
                {"outdoor_temp": 25.0, "offset": 1.2},
                {"outdoor_temp": 30.0, "offset": 1.8}
            ],
            "power_state_patterns": {
                "cooling": {"avg_offset": 1.6, "count": 5}
            },
            "sample_count": 3
        }
        
        learner = LightweightOffsetLearner()
        learner.load_patterns(v10_data)
        
        # Should load existing patterns correctly
        assert learner._sample_count == 3
        assert learner._time_patterns[14] == 1.5
        assert learner._time_pattern_counts[14] == 3
        assert len(learner._temp_correlation_data) == 2
        assert "cooling" in learner._power_state_patterns
        
        # Should have empty enhanced samples for v1.0 data
        assert len(learner._enhanced_samples) == 0
        
        # When saving, should bump to v1.2
        saved_patterns = learner.save_patterns()
        assert saved_patterns["version"] == "1.2"

    def test_migration_preserves_all_sample_fields(self):
        """Test that migration preserves all existing sample fields and adds humidity fields."""
        # Create v1.1 sample with all existing fields but no humidity
        v11_sample = {
            "predicted": 1.0,
            "actual": 1.2,
            "ac_temp": 22.0,
            "room_temp": 24.0,
            "outdoor_temp": 30.0,
            "mode": "cool",
            "power": 250.0,
            "hysteresis_state": "active_phase",
            "timestamp": "2023-01-01T12:00:00"
        }
        
        v11_data = {
            "version": "1.1",
            "time_patterns": {},
            "time_pattern_counts": {},
            "temp_correlation_data": [],
            "power_state_patterns": {},
            "enhanced_samples": [v11_sample],
            "sample_count": 1
        }
        
        learner = LightweightOffsetLearner()
        learner.load_patterns(v11_data)
        
        # Should have migrated the sample
        assert len(learner._enhanced_samples) == 1
        migrated_sample = learner._enhanced_samples[0]
        
        # All existing fields should be preserved
        assert migrated_sample["predicted"] == 1.0
        assert migrated_sample["actual"] == 1.2
        assert migrated_sample["ac_temp"] == 22.0
        assert migrated_sample["room_temp"] == 24.0
        assert migrated_sample["outdoor_temp"] == 30.0
        assert migrated_sample["mode"] == "cool"
        assert migrated_sample["power"] == 250.0
        assert migrated_sample["hysteresis_state"] == "active_phase"
        assert migrated_sample["timestamp"] == "2023-01-01T12:00:00"
        
        # New humidity fields should be added with None values
        assert "indoor_humidity" in migrated_sample
        assert "outdoor_humidity" in migrated_sample
        assert migrated_sample["indoor_humidity"] is None
        assert migrated_sample["outdoor_humidity"] is None

    def test_migration_handles_mixed_samples(self):
        """Test migration handles mixed samples (some with humidity, some without)."""
        # Create samples with mixed humidity data
        sample_without_humidity = {
            "predicted": 1.0,
            "actual": 1.2,
            "ac_temp": 22.0,
            "room_temp": 24.0,
            "outdoor_temp": 30.0,
            "mode": "cool",
            "power": 250.0,
            "hysteresis_state": "active_phase",
            "timestamp": "2023-01-01T12:00:00"
        }
        
        sample_with_humidity = {
            "predicted": 1.1,
            "actual": 1.3,
            "ac_temp": 23.0,
            "room_temp": 25.0,
            "outdoor_temp": 31.0,
            "mode": "cool",
            "power": 260.0,
            "hysteresis_state": "active_phase",
            "timestamp": "2023-01-01T13:00:00",
            "indoor_humidity": 45.0,
            "outdoor_humidity": 65.0
        }
        
        v11_data = {
            "version": "1.1",
            "time_patterns": {},
            "time_pattern_counts": {},
            "temp_correlation_data": [],
            "power_state_patterns": {},
            "enhanced_samples": [sample_without_humidity, sample_with_humidity],
            "sample_count": 2
        }
        
        learner = LightweightOffsetLearner()
        learner.load_patterns(v11_data)
        
        # Should have loaded both samples
        assert len(learner._enhanced_samples) == 2
        
        # First sample should have None humidity values
        sample1 = learner._enhanced_samples[0]
        assert sample1["indoor_humidity"] is None
        assert sample1["outdoor_humidity"] is None
        
        # Second sample should preserve its humidity values
        sample2 = learner._enhanced_samples[1]
        assert sample2["indoor_humidity"] == 45.0
        assert sample2["outdoor_humidity"] == 65.0

    def test_v12_data_loads_without_migration(self):
        """Test that v1.2 data loads without any migration needed."""
        # Create v1.2 format data with humidity
        v12_data = {
            "version": "1.2",
            "time_patterns": {"14": 1.5},
            "time_pattern_counts": {"14": 1},
            "temp_correlation_data": [],
            "power_state_patterns": {},
            "enhanced_samples": [
                {
                    "predicted": 1.0,
                    "actual": 1.2,
                    "ac_temp": 22.0,
                    "room_temp": 24.0,
                    "outdoor_temp": 30.0,
                    "mode": "cool",
                    "power": 250.0,
                    "hysteresis_state": "active_phase",
                    "timestamp": "2023-01-01T12:00:00",
                    "indoor_humidity": 45.0,
                    "outdoor_humidity": 65.0
                }
            ],
            "sample_count": 1
        }
        
        learner = LightweightOffsetLearner()
        learner.load_patterns(v12_data)
        
        # Should load without issues
        assert len(learner._enhanced_samples) == 1
        sample = learner._enhanced_samples[0]
        assert sample["indoor_humidity"] == 45.0
        assert sample["outdoor_humidity"] == 65.0
        
        # Should maintain v1.2 version
        saved_patterns = learner.save_patterns()
        assert saved_patterns["version"] == "1.2"

    def test_backward_compatibility_with_new_features(self):
        """Test that old models work with new humidity-aware prediction code."""
        # Load old data (v1.1 without humidity)
        v11_data = {
            "version": "1.1",
            "time_patterns": {"14": 1.5},
            "time_pattern_counts": {"14": 5},
            "temp_correlation_data": [
                {"outdoor_temp": 25.0, "offset": 1.2}
            ],
            "power_state_patterns": {
                "cooling": {"avg_offset": 1.4, "count": 3}
            },
            "enhanced_samples": [
                {
                    "predicted": 1.0,
                    "actual": 1.2,
                    "ac_temp": 22.0,
                    "room_temp": 24.0,
                    "outdoor_temp": 25.0,
                    "mode": "cool",
                    "power": 250.0,
                    "hysteresis_state": "active_phase",
                    "timestamp": "2023-01-01T12:00:00"
                }
            ],
            "sample_count": 1
        }
        
        learner = LightweightOffsetLearner()
        learner.load_patterns(v11_data)
        
        # Should be able to make predictions with new humidity-aware code
        prediction = learner.predict(
            ac_temp=22.0,
            room_temp=24.0,
            outdoor_temp=25.0,
            mode="cool",
            power=250.0,
            hysteresis_state="active_phase",
            indoor_humidity=None,  # No humidity data available
            outdoor_humidity=None
        )
        
        # Should work and return reasonable prediction
        assert prediction != 0.0
        
        # Should also work with humidity data for new predictions
        prediction_with_humidity = learner.predict(
            ac_temp=22.0,
            room_temp=24.0,
            outdoor_temp=25.0,
            mode="cool",
            power=250.0,
            hysteresis_state="active_phase",
            indoor_humidity=45.0,
            outdoor_humidity=65.0
        )
        
        # Should still work
        assert prediction_with_humidity != 0.0

    def test_model_feature_list_for_backward_compatibility(self):
        """Test that model includes feature list for backward compatibility."""
        learner = LightweightOffsetLearner()
        
        # Add samples with various feature combinations
        learner.add_sample(
            predicted=1.0, actual=1.2, ac_temp=22.0, room_temp=24.0,
            outdoor_temp=30.0, mode="cool", power=250.0,
            hysteresis_state="active_phase",
            indoor_humidity=45.0, outdoor_humidity=65.0
        )
        
        learner.add_sample(
            predicted=1.1, actual=1.3, ac_temp=23.0, room_temp=25.0,
            outdoor_temp=None, mode="cool", power=None,
            hysteresis_state="idle_stable_zone",
            indoor_humidity=None, outdoor_humidity=None
        )
        
        # Save patterns should include feature information
        saved_patterns = learner.save_patterns()
        
        # Check that all expected features are represented in samples
        samples = saved_patterns["enhanced_samples"]
        assert len(samples) == 2
        
        # Verify all expected fields are present (even if None)
        expected_fields = [
            "predicted", "actual", "ac_temp", "room_temp", "outdoor_temp",
            "mode", "power", "hysteresis_state", "timestamp",
            "indoor_humidity", "outdoor_humidity"
        ]
        
        for sample in samples:
            for field in expected_fields:
                assert field in sample, f"Field {field} missing from sample"

    def test_corrupted_sample_migration_recovery(self):
        """Test that migration handles corrupted samples gracefully."""
        # Create data with corrupted samples
        corrupted_data = {
            "version": "1.1",
            "time_patterns": {},
            "time_pattern_counts": {},
            "temp_correlation_data": [],
            "power_state_patterns": {},
            "enhanced_samples": [
                # Valid sample without humidity
                {
                    "predicted": 1.0,
                    "actual": 1.2,
                    "ac_temp": 22.0,
                    "room_temp": 24.0,
                    "outdoor_temp": 30.0,
                    "mode": "cool",
                    "power": 250.0,
                    "hysteresis_state": "active_phase",
                    "timestamp": "2023-01-01T12:00:00"
                },
                # Corrupted sample (missing required fields)
                {
                    "predicted": 1.1,
                    "ac_temp": 23.0,
                    # Missing other required fields
                },
                # Another valid sample
                {
                    "predicted": 1.2,
                    "actual": 1.4,
                    "ac_temp": 24.0,
                    "room_temp": 26.0,
                    "outdoor_temp": 32.0,
                    "mode": "cool",
                    "power": 270.0,
                    "hysteresis_state": "active_phase",
                    "timestamp": "2023-01-01T14:00:00"
                }
            ],
            "sample_count": 3
        }
        
        learner = LightweightOffsetLearner()
        
        # Should load without crashing, filtering out corrupted samples
        try:
            learner.load_patterns(corrupted_data)
        except Exception as e:
            pytest.fail(f"Migration should handle corrupted samples gracefully, but failed with: {e}")
        
        # Should have loaded only the valid samples
        assert len(learner._enhanced_samples) == 2  # Corrupted sample filtered out
        
        # Valid samples should have humidity fields added
        for sample in learner._enhanced_samples:
            assert "indoor_humidity" in sample
            assert "outdoor_humidity" in sample
            assert sample["indoor_humidity"] is None
            assert sample["outdoor_humidity"] is None