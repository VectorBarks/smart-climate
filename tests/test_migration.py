"""ABOUTME: Tests for thermal data migration and validation functionality.
ABOUTME: Covers v1.0→v2.1 migration, field validation, recovery hierarchy, and corruption handling."""

import pytest
from datetime import datetime
from typing import Dict, Any, Tuple
from unittest.mock import Mock, patch

# Import test fixtures
from tests.fixtures.thermal_persistence_data import (
    v1_persistence_data,
    v2_persistence_data,
    empty_thermal_data,
    corrupted_tau_values,
    corrupted_thermal_state,
    corrupted_probe_results,
    malformed_thermal_data,
    migration_scenarios,
    tau_value_ranges,
    thermal_data_factory,
)

# Import the component to test (will create after tests)
from custom_components.smart_climate.data_migration import ThermalDataMigrator


class TestThermalDataMigrator:
    """Test ThermalDataMigrator class for data migration and validation."""
    
    def test_migrator_initialization(self):
        """Test ThermalDataMigrator initialization with defaults."""
        migrator = ThermalDataMigrator()
        assert migrator is not None
        # Should have default validation ranges per c_architecture.md §10.4.1
        
    def test_migrate_v1_to_v2_simple_case(self, v1_persistence_data):
        """Test v1.0 to v2.1 migration for simple case."""
        migrator = ThermalDataMigrator()
        
        result = migrator.migrate_v1_to_v2(v1_persistence_data)
        
        # Should return v2.1 format
        assert result["version"] == "2.1"
        assert result["entity_id"] == v1_persistence_data["entity_id"]
        assert result["last_updated"] == v1_persistence_data["last_updated"]
        
        # Learning data should be preserved exactly
        assert result["learning_data"] == v1_persistence_data["learning_data"]
        
        # Should add empty thermal_data section
        assert "thermal_data" in result
        assert result["thermal_data"] is None
        
    def test_migrate_v1_to_v2_preserves_extra_fields(self, migration_scenarios):
        """Test migration preserves extra fields not part of core schema."""
        migrator = ThermalDataMigrator()
        
        complex_input = migration_scenarios["complex_v1"]["input"]
        result = migrator.migrate_v1_to_v2(complex_input)
        
        # Should preserve extra fields
        assert result["extra_field"] == "should_be_preserved"
        assert result["version"] == "2.1"
        
    def test_migrate_v1_to_v2_already_v2_returns_unchanged(self, v2_persistence_data):
        """Test migration returns v2.1 data unchanged."""
        migrator = ThermalDataMigrator()
        
        result = migrator.migrate_v1_to_v2(v2_persistence_data)
        
        # Should return unchanged v2.1 data
        assert result == v2_persistence_data
        
    def test_migrate_v1_to_v2_invalid_data_handling(self):
        """Test migration handles invalid input data gracefully."""
        migrator = ThermalDataMigrator()
        
        # Test with None
        result = migrator.migrate_v1_to_v2(None)
        assert result is None
        
        # Test with empty dict
        result = migrator.migrate_v1_to_v2({})
        assert result is None
        
        # Test with malformed data
        malformed = {"version": "unknown", "data": "invalid"}
        result = migrator.migrate_v1_to_v2(malformed)
        assert result is None


class TestFieldValidation:
    """Test field-level validation per c_architecture.md §10.4.1."""
    
    def test_validate_thermal_data_valid_data(self, empty_thermal_data):
        """Test validation passes for valid thermal data."""
        migrator = ThermalDataMigrator()
        
        validated_data, recovery_count = migrator.validate_thermal_data(empty_thermal_data)
        
        assert validated_data == empty_thermal_data
        assert recovery_count == 0
        
    def test_validate_thermal_data_invalid_tau_values(self, corrupted_tau_values, tau_value_ranges):
        """Test field-level recovery for invalid tau values."""
        migrator = ThermalDataMigrator()
        
        validated_data, recovery_count = migrator.validate_thermal_data(corrupted_tau_values)
        
        # Should recover with default values per §10.4.2
        assert validated_data["model"]["tau_cooling"] == 90.0  # Default value
        assert validated_data["model"]["tau_warming"] == 150.0  # Default value
        assert recovery_count == 2  # Two field recoveries
        
    def test_validate_thermal_data_invalid_state(self, corrupted_thermal_state):
        """Test system-level recovery for invalid thermal state."""
        migrator = ThermalDataMigrator()
        
        validated_data, recovery_count = migrator.validate_thermal_data(corrupted_thermal_state)
        
        # Should default to PRIMING state per §10.4.2
        assert validated_data["state"]["current_state"] == "PRIMING"
        assert recovery_count == 1
        
    def test_validate_thermal_data_invalid_probe_results(self, corrupted_probe_results):
        """Test object-level recovery for invalid probe results."""
        migrator = ThermalDataMigrator()
        
        validated_data, recovery_count = migrator.validate_thermal_data(corrupted_probe_results)
        
        # Should discard invalid probes per §10.4.2
        assert len(validated_data["probe_history"]) < len(corrupted_probe_results["probe_history"])
        assert recovery_count > 0  # At least some probes discarded
        
    def test_validate_thermal_data_confidence_validation(self):
        """Test confidence value validation (0.0-1.0)."""
        migrator = ThermalDataMigrator()
        
        # Test invalid confidence values
        invalid_data = {
            "version": "1.0",
            "state": {"current_state": "PRIMING", "last_transition": "2025-08-08T16:00:00Z"},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0, "last_modified": "2025-08-08T16:00:00Z"},
            "probe_history": [],
            "confidence": 1.5,  # Invalid > 1.0
            "metadata": {"saves_count": 0, "corruption_recoveries": 0, "schema_version": "1.0"}
        }
        
        validated_data, recovery_count = migrator.validate_thermal_data(invalid_data)
        
        assert validated_data["confidence"] == 0.0  # Default value
        assert recovery_count == 1
        
    def test_validate_thermal_data_probe_duration_validation(self):
        """Test ProbeResult.duration validation (> 0)."""
        migrator = ThermalDataMigrator()
        
        invalid_data = {
            "version": "1.0",
            "state": {"current_state": "PRIMING", "last_transition": "2025-08-08T16:00:00Z"},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0, "last_modified": "2025-08-08T16:00:00Z"},
            "probe_history": [
                {
                    "tau_value": 95.0,
                    "confidence": 0.85,
                    "duration": -100,  # Invalid negative duration
                    "fit_quality": 0.92,
                    "aborted": False,
                    "timestamp": "2025-08-08T15:30:00Z"
                }
            ],
            "confidence": 0.75,
            "metadata": {"saves_count": 0, "corruption_recoveries": 0, "schema_version": "1.0"}
        }
        
        validated_data, recovery_count = migrator.validate_thermal_data(invalid_data)
        
        # Should discard probe with invalid duration
        assert len(validated_data["probe_history"]) == 0
        assert recovery_count == 1
        
    def test_validate_thermal_data_fit_quality_validation(self):
        """Test ProbeResult.fit_quality validation (0.0-1.0)."""
        migrator = ThermalDataMigrator()
        
        invalid_data = {
            "version": "1.0",
            "state": {"current_state": "PRIMING", "last_transition": "2025-08-08T16:00:00Z"},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0, "last_modified": "2025-08-08T16:00:00Z"},
            "probe_history": [
                {
                    "tau_value": 95.0,
                    "confidence": 0.85,
                    "duration": 3600,
                    "fit_quality": 2.0,  # Invalid > 1.0
                    "aborted": False,
                    "timestamp": "2025-08-08T15:30:00Z"
                }
            ],
            "confidence": 0.75,
            "metadata": {"saves_count": 0, "corruption_recoveries": 0, "schema_version": "1.0"}
        }
        
        validated_data, recovery_count = migrator.validate_thermal_data(invalid_data)
        
        # Should discard probe with invalid fit_quality
        assert len(validated_data["probe_history"]) == 0
        assert recovery_count == 1


class TestRecoveryHierarchy:
    """Test recovery hierarchy per c_architecture.md §10.4.2."""
    
    def test_field_level_recovery(self, thermal_data_factory):
        """Test field level recovery: invalid field → use default → continue."""
        migrator = ThermalDataMigrator()
        
        data = thermal_data_factory(tau_cooling=-50.0, tau_warming=2000.0)
        
        validated_data, recovery_count = migrator.validate_thermal_data(data)
        
        # Field level: invalid values replaced with defaults
        assert validated_data["model"]["tau_cooling"] == 90.0
        assert validated_data["model"]["tau_warming"] == 150.0
        assert recovery_count == 2
        
    def test_object_level_recovery(self):
        """Test object level recovery: invalid probe → discard → continue.""" 
        migrator = ThermalDataMigrator()
        
        data = {
            "version": "1.0",
            "state": {"current_state": "PRIMING", "last_transition": "2025-08-08T16:00:00Z"},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0, "last_modified": "2025-08-08T16:00:00Z"},
            "probe_history": [
                # Valid probe
                {
                    "tau_value": 95.0,
                    "confidence": 0.85,
                    "duration": 3600,
                    "fit_quality": 0.92,
                    "aborted": False,
                    "timestamp": "2025-08-08T15:30:00Z"
                },
                # Invalid probe - should be discarded
                {
                    "tau_value": -10.0,  # Invalid
                    "confidence": 1.5,   # Invalid
                    "duration": -300,    # Invalid
                    "fit_quality": 2.0,  # Invalid
                    "aborted": "maybe",  # Invalid
                    "timestamp": "invalid-date"
                }
            ],
            "confidence": 0.75,
            "metadata": {"saves_count": 0, "corruption_recoveries": 0, "schema_version": "1.0"}
        }
        
        validated_data, recovery_count = migrator.validate_thermal_data(data)
        
        # Object level: invalid probe discarded, valid probe retained
        assert len(validated_data["probe_history"]) == 1
        assert validated_data["probe_history"][0]["tau_value"] == 95.0
        assert recovery_count == 1
        
    def test_system_level_recovery(self):
        """Test system level recovery: invalid state → default to PRIMING."""
        migrator = ThermalDataMigrator()
        
        data = {
            "version": "1.0",
            "state": {"current_state": "INVALID_STATE", "last_transition": "2025-08-08T16:00:00Z"},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0, "last_modified": "2025-08-08T16:00:00Z"},
            "probe_history": [],
            "confidence": 0.0,
            "metadata": {"saves_count": 0, "corruption_recoveries": 0, "schema_version": "1.0"}
        }
        
        validated_data, recovery_count = migrator.validate_thermal_data(data)
        
        # System level: invalid state defaults to PRIMING
        assert validated_data["state"]["current_state"] == "PRIMING"
        assert recovery_count == 1


class TestCorruptionRecovery:
    """Test corruption recovery and edge cases."""
    
    def test_completely_malformed_data_recovery(self, malformed_thermal_data):
        """Test recovery from completely malformed thermal data."""
        migrator = ThermalDataMigrator()
        
        validated_data, recovery_count = migrator.validate_thermal_data(malformed_thermal_data)
        
        # Should provide valid defaults for malformed data
        assert validated_data["state"]["current_state"] == "PRIMING"
        assert validated_data["model"]["tau_cooling"] == 90.0
        assert validated_data["model"]["tau_warming"] == 150.0
        assert validated_data["probe_history"] == []
        assert validated_data["confidence"] == 0.0
        assert recovery_count > 0
        
    def test_missing_required_fields_recovery(self):
        """Test recovery when required fields are missing."""
        migrator = ThermalDataMigrator()
        
        incomplete_data = {
            "version": "1.0",
            # Missing state section
            "model": {"tau_cooling": 90.0},  # Missing tau_warming
            # Missing probe_history
            # Missing confidence
            # Missing metadata
        }
        
        validated_data, recovery_count = migrator.validate_thermal_data(incomplete_data)
        
        # Should provide all required fields with defaults
        assert "state" in validated_data
        assert "probe_history" in validated_data
        assert "confidence" in validated_data
        assert "metadata" in validated_data
        assert validated_data["model"]["tau_warming"] == 150.0
        assert recovery_count > 0
        
    def test_timestamp_validation_future_dates(self):
        """Test timestamp validation rejects future dates."""
        migrator = ThermalDataMigrator()
        
        future_date = "2030-12-31T23:59:59Z"  # Future date
        data = {
            "version": "1.0",
            "state": {"current_state": "PRIMING", "last_transition": future_date},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0, "last_modified": future_date},
            "probe_history": [
                {
                    "tau_value": 95.0,
                    "confidence": 0.85,
                    "duration": 3600,
                    "fit_quality": 0.92,
                    "aborted": False,
                    "timestamp": future_date
                }
            ],
            "confidence": 0.75,
            "metadata": {"saves_count": 0, "corruption_recoveries": 0, "schema_version": "1.0"}
        }
        
        validated_data, recovery_count = migrator.validate_thermal_data(data)
        
        # Should discard probe with future timestamp
        assert len(validated_data["probe_history"]) == 0
        assert recovery_count > 0  # At least probe discarded
        
    def test_tau_value_boundary_cases(self):
        """Test tau value validation boundary cases (1-1000 minutes)."""
        migrator = ThermalDataMigrator()
        
        # Test boundary values
        boundary_cases = [
            {"tau_cooling": 0.5, "tau_warming": 1.5, "expected_recoveries": 1},  # tau_cooling invalid
            {"tau_cooling": 1.0, "tau_warming": 1.0, "expected_recoveries": 0},  # Both valid 
            {"tau_cooling": 1000.0, "tau_warming": 1000.0, "expected_recoveries": 0},  # Both valid
            {"tau_cooling": 1000.5, "tau_warming": 500.0, "expected_recoveries": 1},  # tau_cooling invalid
        ]
        
        for case in boundary_cases:
            data = {
                "version": "1.0",
                "state": {"current_state": "PRIMING", "last_transition": "2025-08-08T16:00:00Z"},
                "model": {
                    "tau_cooling": case["tau_cooling"],
                    "tau_warming": case["tau_warming"],
                    "last_modified": "2025-08-08T16:00:00Z"
                },
                "probe_history": [],
                "confidence": 0.0,
                "metadata": {"saves_count": 0, "corruption_recoveries": 0, "schema_version": "1.0"}
            }
            
            validated_data, recovery_count = migrator.validate_thermal_data(data)
            
            assert recovery_count == case["expected_recoveries"]
            
            # Check defaults were applied when needed
            if case["tau_cooling"] < 1.0 or case["tau_cooling"] > 1000.0:
                assert validated_data["model"]["tau_cooling"] == 90.0
            if case["tau_warming"] < 1.0 or case["tau_warming"] > 1000.0:
                assert validated_data["model"]["tau_warming"] == 150.0


class TestDefaultValues:
    """Test default values used in recovery per c_architecture.md §10.4.2."""
    
    def test_default_values_match_specification(self):
        """Test that default values match c_architecture.md specifications."""
        migrator = ThermalDataMigrator()
        
        # Test with completely empty/invalid data
        empty_data = {}
        
        validated_data, recovery_count = migrator.validate_thermal_data(empty_data)
        
        # Should match defaults from specification
        assert validated_data["model"]["tau_cooling"] == 90.0
        assert validated_data["model"]["tau_warming"] == 150.0  
        assert validated_data["confidence"] == 0.0
        assert validated_data["state"]["current_state"] == "PRIMING"
        assert validated_data["probe_history"] == []
        assert recovery_count > 0


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_none_input_handling(self):
        """Test handling of None inputs gracefully."""
        migrator = ThermalDataMigrator()
        
        # migrate_v1_to_v2 with None
        result = migrator.migrate_v1_to_v2(None)
        assert result is None
        
        # validate_thermal_data with None
        result, recovery_count = migrator.validate_thermal_data(None)
        assert result is None
        assert recovery_count == 0
        
    def test_empty_dict_handling(self):
        """Test handling of empty dictionaries."""
        migrator = ThermalDataMigrator()
        
        # migrate_v1_to_v2 with empty dict  
        result = migrator.migrate_v1_to_v2({})
        assert result is None
        
        # validate_thermal_data with empty dict should provide defaults
        result, recovery_count = migrator.validate_thermal_data({})
        assert result is not None
        assert "state" in result
        assert "model" in result
        assert recovery_count > 0
        
    def test_mixed_valid_invalid_probes(self):
        """Test handling mix of valid and invalid probes in history."""
        migrator = ThermalDataMigrator()
        
        data = {
            "version": "1.0",
            "state": {"current_state": "PRIMING", "last_transition": "2025-08-08T16:00:00Z"},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0, "last_modified": "2025-08-08T16:00:00Z"},
            "probe_history": [
                # Valid probe 1
                {
                    "tau_value": 95.0,
                    "confidence": 0.85,
                    "duration": 3600,
                    "fit_quality": 0.92,
                    "aborted": False,
                    "timestamp": "2025-08-08T15:30:00Z"
                },
                # Invalid probe - bad tau_value
                {
                    "tau_value": -10.0,
                    "confidence": 0.75,
                    "duration": 2400,
                    "fit_quality": 0.88,
                    "aborted": False,
                    "timestamp": "2025-08-08T14:30:00Z"
                },
                # Valid probe 2
                {
                    "tau_value": 88.5,
                    "confidence": 0.92,
                    "duration": 4200,
                    "fit_quality": 0.95,
                    "aborted": False,
                    "timestamp": "2025-08-08T13:30:00Z"
                },
                # Invalid probe - bad confidence
                {
                    "tau_value": 92.0,
                    "confidence": 1.5,
                    "duration": 3000,
                    "fit_quality": 0.90,
                    "aborted": False,
                    "timestamp": "2025-08-08T12:30:00Z"
                }
            ],
            "confidence": 0.75,
            "metadata": {"saves_count": 10, "corruption_recoveries": 0, "schema_version": "1.0"}
        }
        
        validated_data, recovery_count = migrator.validate_thermal_data(data)
        
        # Should keep only valid probes (2 out of 4)
        assert len(validated_data["probe_history"]) == 2
        assert validated_data["probe_history"][0]["tau_value"] == 95.0
        assert validated_data["probe_history"][1]["tau_value"] == 88.5
        assert recovery_count == 2  # Two invalid probes discarded