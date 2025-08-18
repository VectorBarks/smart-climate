"""
ABOUTME: Test infrastructure validation for v1.5.3 thermal model enhancements.
Tests probe fixtures, helpers, and validation utilities for enhanced thermal testing.
"""

import pytest
from datetime import datetime, timezone, timedelta
from custom_components.smart_climate.thermal_models import ProbeResult

# Import the modules that we will create
from tests.fixtures.thermal_v153 import (
    create_probe_result,
    create_probe_sequence,
    create_legacy_probe
)
from tests.helpers.probe_helpers import (
    validate_probe_history,
    calculate_expected_weight,
    generate_outdoor_temp_sequence
)


class TestProbeResultFixtures:
    """Test fixture generators for ProbeResult objects."""

    def test_create_probe_result_basic(self):
        """Test basic probe result creation with all parameters."""
        probe = create_probe_result(
            tau_value=90.0,
            confidence=0.8,
            age_days=2,
            outdoor_temp=25.0
        )
        
        assert isinstance(probe, ProbeResult)
        assert probe.tau_value == 90.0
        assert probe.confidence == 0.8
        assert probe.outdoor_temp == 25.0
        
        # Check timestamp is approximately 2 days ago
        expected_time = datetime.now(timezone.utc) - timedelta(days=2)
        time_diff = abs((probe.timestamp - expected_time).total_seconds())
        assert time_diff < 60  # Within 1 minute tolerance

    def test_create_probe_result_defaults(self):
        """Test probe result creation with minimal parameters."""
        probe = create_probe_result(tau_value=120.0, confidence=0.9)
        
        assert probe.tau_value == 120.0
        assert probe.confidence == 0.9
        assert probe.outdoor_temp is None  # Default
        assert probe.aborted is False  # Default
        assert probe.duration > 0  # Should have reasonable default

    def test_create_probe_result_validation(self):
        """Test probe result parameter validation."""
        # Test confidence bounds
        probe = create_probe_result(tau_value=90.0, confidence=1.2)
        assert probe.confidence <= 1.0
        
        probe = create_probe_result(tau_value=90.0, confidence=-0.1)
        assert probe.confidence >= 0.0
        
        # Test tau value bounds
        probe = create_probe_result(tau_value=10.0, confidence=0.8)
        assert probe.tau_value >= 30.0  # Minimum physical limit
        
        probe = create_probe_result(tau_value=500.0, confidence=0.8)
        assert probe.tau_value <= 300.0  # Maximum physical limit

    def test_create_probe_sequence(self):
        """Test creation of time-sequenced probe results."""
        outdoor_temps = [20.0, 22.0, 25.0]
        probes = create_probe_sequence(
            count=3,
            start_days_ago=10,
            outdoor_temps=outdoor_temps
        )
        
        assert len(probes) == 3
        
        # Check temporal ordering (oldest first)
        for i in range(len(probes) - 1):
            assert probes[i].timestamp < probes[i + 1].timestamp
        
        # Check outdoor temps assigned correctly
        for i, probe in enumerate(probes):
            assert probe.outdoor_temp == outdoor_temps[i]
        
        # Check first probe is approximately 10 days ago
        expected_start = datetime.now(timezone.utc) - timedelta(days=10)
        time_diff = abs((probes[0].timestamp - expected_start).total_seconds())
        assert time_diff < 3600  # Within 1 hour tolerance

    def test_create_legacy_probe(self):
        """Test creation of legacy probe without outdoor_temp field."""
        probe = create_legacy_probe(tau_value=150.0, confidence=0.7)
        
        assert probe.tau_value == 150.0
        assert probe.confidence == 0.7
        assert probe.outdoor_temp is None
        assert isinstance(probe.timestamp, datetime)


class TestProbeHelpers:
    """Test validation and calculation helper functions."""

    def test_validate_probe_history_valid(self):
        """Test probe history validation with valid data."""
        probes = create_probe_sequence(count=5, start_days_ago=20)
        
        # Should pass validation
        is_valid, message = validate_probe_history(probes, expected_size=5)
        assert is_valid
        assert message == "Valid probe history"

    def test_validate_probe_history_size_mismatch(self):
        """Test probe history validation with size mismatch."""
        probes = create_probe_sequence(count=3, start_days_ago=20)
        
        is_valid, message = validate_probe_history(probes, expected_size=5)
        assert not is_valid
        assert "Expected 5 probes, got 3" in message

    def test_validate_probe_history_temporal_order(self):
        """Test probe history validation detects temporal disorder."""
        # Create probes with wrong temporal order
        probe1 = create_probe_result(tau_value=90.0, confidence=0.8, age_days=1)
        probe2 = create_probe_result(tau_value=95.0, confidence=0.7, age_days=5)
        probes = [probe1, probe2]  # Wrong order (newer first)
        
        is_valid, message = validate_probe_history(probes, expected_size=2)
        assert not is_valid
        assert "temporal order" in message.lower()

    def test_calculate_expected_weight(self):
        """Test exponential decay weight calculation."""
        # Recent probe should have high weight
        weight_recent = calculate_expected_weight(age_days=0, decay_rate=0.98)
        assert weight_recent == 1.0
        
        # Older probe should have lower weight
        weight_old = calculate_expected_weight(age_days=30, decay_rate=0.98)
        assert 0.0 < weight_old < 1.0
        assert weight_old < weight_recent
        
        # Very old probe should have very low weight
        weight_very_old = calculate_expected_weight(age_days=100, decay_rate=0.98)
        assert weight_very_old < weight_old

    def test_calculate_expected_weight_half_life(self):
        """Test weight calculation matches expected half-life."""
        # With decay_rate=0.98, half-life should be ~34.3 days
        weight_half_life = calculate_expected_weight(age_days=34.3, decay_rate=0.98)
        assert abs(weight_half_life - 0.5) < 0.05  # Within 5% of 0.5

    def test_generate_outdoor_temp_sequence(self):
        """Test outdoor temperature sequence generation."""
        temps = generate_outdoor_temp_sequence(
            base_temp=20.0,
            variation=5.0,
            count=10
        )
        
        assert len(temps) == 10
        
        # All temperatures should be within reasonable bounds
        for temp in temps:
            assert 15.0 <= temp <= 25.0  # base ± variation
        
        # Should have some variation (not all identical)
        assert len(set(temps)) > 1


class TestTimeManipulation:
    """Test time manipulation utilities for probe testing."""

    def test_probe_aging_consistency(self):
        """Test that probe aging produces consistent timestamps."""
        # Create multiple probes with same age
        probes = [
            create_probe_result(tau_value=90.0, confidence=0.8, age_days=5)
            for _ in range(3)
        ]
        
        # All should have similar timestamps (within 1 second)
        timestamps = [p.timestamp for p in probes]
        max_diff = max(timestamps) - min(timestamps)
        assert max_diff.total_seconds() < 1.0

    def test_probe_sequence_spacing(self):
        """Test probe sequence has appropriate time spacing."""
        probes = create_probe_sequence(count=5, start_days_ago=25)
        
        # Check spacing between consecutive probes
        for i in range(len(probes) - 1):
            time_diff = probes[i + 1].timestamp - probes[i].timestamp
            # Should be roughly 5-6 days apart (25 days / 4 intervals)
            assert 3 * 24 * 3600 <= time_diff.total_seconds() <= 8 * 24 * 3600


class TestFixtureIntegration:
    """Integration tests between fixtures and helpers."""

    def test_fixture_helper_integration(self):
        """Test fixtures work correctly with validation helpers."""
        # Create a sequence and validate it
        probes = create_probe_sequence(count=7, start_days_ago=35)
        is_valid, message = validate_probe_history(probes, expected_size=7)
        
        assert is_valid
        assert message == "Valid probe history"

    def test_weighted_calculation_with_fixtures(self):
        """Test weight calculations work with fixture-generated probes."""
        probes = create_probe_sequence(count=3, start_days_ago=60)
        
        # Calculate weights for each probe
        weights = []
        for probe in probes:
            age = (datetime.now(timezone.utc) - probe.timestamp).days
            weight = calculate_expected_weight(age, decay_rate=0.98)
            weights.append(weight)
        
        # Weights should decrease with age
        assert weights[0] < weights[1] < weights[2]  # Oldest to newest

    def test_outdoor_temp_probe_assignment(self):
        """Test outdoor temperatures are correctly assigned to probes."""
        temps = generate_outdoor_temp_sequence(base_temp=15.0, variation=10.0, count=4)
        probes = create_probe_sequence(count=4, start_days_ago=20, outdoor_temps=temps)
        
        for i, probe in enumerate(probes):
            assert probe.outdoor_temp == temps[i]