"""Test ProbeScheduler integration methods for PassiveThermalModel."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

from custom_components.smart_climate.thermal_model import PassiveThermalModel, ProbeResult


class TestPassiveThermalModelProbeSupport:
    """Test probe support methods for ProbeScheduler integration."""

    @pytest.fixture
    def thermal_model(self):
        """Create thermal model instance."""
        return PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)

    @pytest.fixture
    def sample_probe_results(self):
        """Create sample probe results for testing."""
        base_time = datetime.now(timezone.utc)
        return [
            ProbeResult(
                tau_value=85.0,
                confidence=0.8,
                duration=3600,
                fit_quality=0.9,
                aborted=False,
                timestamp=base_time - timedelta(hours=24),
                outdoor_temp=25.0
            ),
            ProbeResult(
                tau_value=92.0,
                confidence=0.85,
                duration=3900,
                fit_quality=0.88,
                aborted=False,
                timestamp=base_time - timedelta(hours=12),
                outdoor_temp=28.0
            ),
            ProbeResult(
                tau_value=88.0,
                confidence=0.82,
                duration=3300,
                fit_quality=0.92,
                aborted=True,
                timestamp=base_time,
                outdoor_temp=30.0
            )
        ]

    def test_get_probe_history_empty(self, thermal_model):
        """Test get_probe_history returns empty list when no probes."""
        history = thermal_model.get_probe_history()
        
        assert isinstance(history, list)
        assert len(history) == 0

    def test_get_probe_history_returns_copy(self, thermal_model, sample_probe_results):
        """Test get_probe_history returns immutable copy."""
        # Add probes to model
        for probe in sample_probe_results:
            thermal_model.add_probe_result(probe)
        
        # Get history
        history = thermal_model.get_probe_history()
        
        # Verify it's a list (copy, not deque reference)
        assert isinstance(history, list)
        assert len(history) == 3
        
        # Verify contents match
        for i, probe in enumerate(history):
            assert probe.tau_value == sample_probe_results[i].tau_value
            assert probe.confidence == sample_probe_results[i].confidence
            assert probe.timestamp == sample_probe_results[i].timestamp
        
        # Verify it's immutable - modifying returned list shouldn't affect model
        original_count = thermal_model.get_probe_count()
        history.clear()
        assert thermal_model.get_probe_count() == original_count

    def test_get_probe_history_chronological_order(self, thermal_model, sample_probe_results):
        """Test get_probe_history returns probes in chronological order."""
        # Add probes in random order
        for probe in [sample_probe_results[2], sample_probe_results[0], sample_probe_results[1]]:
            thermal_model.add_probe_result(probe)
        
        history = thermal_model.get_probe_history()
        
        # Should be in chronological order (oldest first)
        assert len(history) == 3
        assert history[0].timestamp < history[1].timestamp < history[2].timestamp

    def test_get_last_probe_time_empty(self, thermal_model):
        """Test get_last_probe_time returns None when no probes."""
        last_time = thermal_model.get_last_probe_time()
        assert last_time is None

    def test_get_last_probe_time_single_probe(self, thermal_model, sample_probe_results):
        """Test get_last_probe_time with single probe."""
        thermal_model.add_probe_result(sample_probe_results[0])
        
        last_time = thermal_model.get_last_probe_time()
        assert last_time == sample_probe_results[0].timestamp

    def test_get_last_probe_time_multiple_probes(self, thermal_model, sample_probe_results):
        """Test get_last_probe_time returns most recent timestamp."""
        for probe in sample_probe_results:
            thermal_model.add_probe_result(probe)
        
        last_time = thermal_model.get_last_probe_time()
        
        # Should return the most recent timestamp
        expected_last = max(probe.timestamp for probe in sample_probe_results)
        assert last_time == expected_last

    def test_get_probe_count_accuracy(self, thermal_model, sample_probe_results):
        """Test get_probe_count returns accurate count."""
        # Should already be implemented - test it works
        assert thermal_model.get_probe_count() == 0
        
        thermal_model.add_probe_result(sample_probe_results[0])
        assert thermal_model.get_probe_count() == 1
        
        thermal_model.add_probe_result(sample_probe_results[1])
        assert thermal_model.get_probe_count() == 2
        
        thermal_model.add_probe_result(sample_probe_results[2])
        assert thermal_model.get_probe_count() == 3

    def test_add_probe_result_validation(self, thermal_model):
        """Test add_probe_result validates input."""
        valid_probe = ProbeResult(
            tau_value=90.0,
            confidence=0.8,
            duration=3600,
            fit_quality=0.9,
            aborted=False,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Should accept valid probe
        thermal_model.add_probe_result(valid_probe)
        assert thermal_model.get_probe_count() == 1

    def test_add_probe_result_invalid_type(self, thermal_model):
        """Test add_probe_result rejects invalid type."""
        with pytest.raises((TypeError, AttributeError)):
            thermal_model.add_probe_result("not_a_probe")

    def test_add_probe_result_storage_and_retrieval(self, thermal_model, sample_probe_results):
        """Test add_probe_result stores data correctly."""
        probe = sample_probe_results[0]
        thermal_model.add_probe_result(probe)
        
        # Verify storage
        assert thermal_model.get_probe_count() == 1
        history = thermal_model.get_probe_history()
        stored_probe = history[0]
        
        # Verify all fields preserved
        assert stored_probe.tau_value == probe.tau_value
        assert stored_probe.confidence == probe.confidence
        assert stored_probe.duration == probe.duration
        assert stored_probe.fit_quality == probe.fit_quality
        assert stored_probe.aborted == probe.aborted
        assert stored_probe.timestamp == probe.timestamp
        assert stored_probe.outdoor_temp == probe.outdoor_temp

    def test_add_probe_result_maintains_max_size(self, thermal_model):
        """Test add_probe_result respects maximum history size."""
        from custom_components.smart_climate.const import MAX_PROBE_HISTORY_SIZE
        
        # Add more probes than max size
        base_time = datetime.now(timezone.utc)
        for i in range(MAX_PROBE_HISTORY_SIZE + 5):
            probe = ProbeResult(
                tau_value=90.0 + i,
                confidence=0.8,
                duration=3600,
                fit_quality=0.9,
                aborted=False,
                timestamp=base_time + timedelta(hours=i)
            )
            thermal_model.add_probe_result(probe)
        
        # Should not exceed max size
        assert thermal_model.get_probe_count() == MAX_PROBE_HISTORY_SIZE
        
        # Should keep most recent probes
        history = thermal_model.get_probe_history()
        assert history[-1].tau_value == 90.0 + (MAX_PROBE_HISTORY_SIZE + 5 - 1)

    def test_edge_case_empty_history_operations(self, thermal_model):
        """Test all methods handle empty history gracefully."""
        # Empty history should not crash
        assert thermal_model.get_probe_history() == []
        assert thermal_model.get_last_probe_time() is None
        assert thermal_model.get_probe_count() == 0

    def test_edge_case_single_probe_operations(self, thermal_model, sample_probe_results):
        """Test all methods work correctly with single probe."""
        probe = sample_probe_results[0]
        thermal_model.add_probe_result(probe)
        
        # Single probe operations
        history = thermal_model.get_probe_history()
        assert len(history) == 1
        assert history[0] == probe
        
        assert thermal_model.get_last_probe_time() == probe.timestamp
        assert thermal_model.get_probe_count() == 1

    def test_timezone_aware_timestamps(self, thermal_model):
        """Test methods handle timezone-aware datetime objects correctly."""
        # Create probes with different timezones
        utc_time = datetime.now(timezone.utc)
        
        probe = ProbeResult(
            tau_value=90.0,
            confidence=0.8,
            duration=3600,
            fit_quality=0.9,
            aborted=False,
            timestamp=utc_time
        )
        
        thermal_model.add_probe_result(probe)
        
        # Should preserve timezone information
        last_time = thermal_model.get_last_probe_time()
        assert last_time.tzinfo is not None
        assert last_time == utc_time

    def test_data_consistency_after_operations(self, thermal_model, sample_probe_results):
        """Test data remains consistent after multiple operations."""
        # Add all probes
        for probe in sample_probe_results:
            thermal_model.add_probe_result(probe)
        
        initial_count = thermal_model.get_probe_count()
        initial_history = thermal_model.get_probe_history()
        initial_last_time = thermal_model.get_last_probe_time()
        
        # Multiple calls should return consistent data
        for _ in range(5):
            assert thermal_model.get_probe_count() == initial_count
            assert thermal_model.get_probe_history() == initial_history
            assert thermal_model.get_last_probe_time() == initial_last_time

    def test_integration_with_existing_methods(self, thermal_model, sample_probe_results):
        """Test new methods integrate properly with existing functionality."""
        # Add probes using new method
        for probe in sample_probe_results:
            thermal_model.add_probe_result(probe)
        
        # Existing methods should still work
        confidence = thermal_model.get_confidence()
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
        
        # Should be able to update tau (existing method)
        new_probe = ProbeResult(
            tau_value=95.0,
            confidence=0.9,
            duration=3600,
            fit_quality=0.95,
            aborted=False,
            timestamp=datetime.now(timezone.utc)
        )
        
        thermal_model.update_tau(new_probe, is_cooling=True)
        
        # New methods should reflect the update
        assert thermal_model.get_probe_count() > len(sample_probe_results)