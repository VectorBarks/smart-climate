"""ABOUTME: Regression tests for v1.5.3 thermal model enhancements.
Ensures core thermal physics unchanged, API compatibility maintained, and existing integrations work."""

import pytest
import math
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from custom_components.smart_climate.thermal_model import PassiveThermalModel, ProbeResult
from custom_components.smart_climate.thermal_manager import ThermalManager
from custom_components.smart_climate.const import (
    MAX_PROBE_HISTORY_SIZE,
    CONFIDENCE_REQUIRED_SAMPLES,
    DECAY_RATE_PER_DAY
)
from tests.fixtures.thermal_v153 import create_probe_result, create_probe_sequence, create_legacy_probe


class TestThermalV153Regression:
    """Regression tests ensuring v1.5.3 doesn't break existing functionality."""

    @pytest.fixture
    def thermal_model(self):
        """Create thermal model for regression testing."""
        return PassiveThermalModel()

    @pytest.fixture
    def legacy_thermal_model(self):
        """Create thermal model with legacy-style data."""
        model = PassiveThermalModel()
        # Add legacy probes (no outdoor_temp)
        legacy_probes = [
            create_legacy_probe(tau_value=85.0, confidence=0.7, age_days=5),
            create_legacy_probe(tau_value=90.0, confidence=0.8, age_days=3),
            create_legacy_probe(tau_value=88.0, confidence=0.75, age_days=1),
        ]
        for probe in legacy_probes:
            model.update_tau(probe, is_cooling=True)
        return model

    def test_core_thermal_physics_unchanged(self, thermal_model):
        """Test that core RC circuit physics remain unchanged in v1.5.3.
        
        Critical regression test - thermal physics must be identical.
        """
        # Test fundamental RC circuit formula: T(t) = T_current + (T_outdoor - T_current) * (1 - exp(-t/tau))
        test_cases = [
            # (current, outdoor, minutes, tau, expected_delta_approx)
            (20.0, 30.0, 60, 90.0, 4.87),    # Warming scenario
            (25.0, 20.0, 90, 90.0, -3.16),   # Cooling scenario  
            (22.0, 22.0, 120, 90.0, 0.0),    # No temperature difference
            (18.0, 35.0, 30, 90.0, 4.82),    # Large temperature difference
            (30.0, 10.0, 45, 150.0, -5.18),  # Different tau value
        ]
        
        for current, outdoor, minutes, tau, expected_delta in test_cases:
            # Set the model's tau values for testing
            thermal_model._tau_cooling = tau
            thermal_model._tau_warming = tau
            
            # Calculate prediction
            is_cooling = outdoor < current
            predicted = thermal_model.predict_drift(current, outdoor, minutes, is_cooling)
            actual_delta = predicted - current
            
            # Assert physics correctness (within 0.1°C tolerance)
            assert abs(actual_delta - expected_delta) < 0.1, f"Physics regression for case {current}→{outdoor} in {minutes}min: got {actual_delta:.2f}, expected {expected_delta:.2f}"
            
            # Verify direction is correct
            if outdoor > current:
                assert predicted > current, "Should warm toward higher outdoor temperature"
            elif outdoor < current:
                assert predicted < current, "Should cool toward lower outdoor temperature"
            else:
                assert abs(predicted - current) < 0.001, "Should remain stable when temperatures equal"
        
        # Test edge cases remain unchanged
        # Zero time should return current temperature
        assert thermal_model.predict_drift(22.0, 28.0, 0, True) == 22.0
        
        # Large time should approach outdoor temperature asymptotically
        long_prediction = thermal_model.predict_drift(20.0, 30.0, 1000, False)  # ~16.7 hours
        assert 29.5 < long_prediction < 30.0  # Should be very close to outdoor temp

    def test_api_compatibility_maintained(self, thermal_model):
        """Test that all existing API methods work identically.
        
        Ensures no breaking changes in public interface.
        """
        # Test PassiveThermalModel constructor (existing signature)
        model_default = PassiveThermalModel()
        assert model_default._tau_cooling == 90.0
        assert model_default._tau_warming == 150.0
        
        model_custom = PassiveThermalModel(tau_cooling=80.0, tau_warming=140.0)
        assert model_custom._tau_cooling == 80.0
        assert model_custom._tau_warming == 140.0
        
        # Test predict_drift method (existing signature)
        prediction = thermal_model.predict_drift(
            current=22.0,
            outdoor=28.0,
            minutes=60,
            is_cooling=True
        )
        assert isinstance(prediction, float)
        assert prediction > 22.0  # Should warm toward outdoor
        
        # Test with edge cases that might have been used
        assert thermal_model.predict_drift(20.0, 25.0, 0, True) == 20.0
        
        with pytest.raises(ValueError):
            thermal_model.predict_drift(20.0, 25.0, -10, True)  # Negative time should still raise
        
        # Test get_confidence method (existing signature)
        confidence = thermal_model.get_confidence()
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
        
        # Test get_probe_count method (existing, undocumented)
        count = thermal_model.get_probe_count()
        assert isinstance(count, int)
        assert count >= 0
        
        # Test update_tau method (existing signature)
        test_probe = create_probe_result(tau_value=92.0, confidence=0.8)
        initial_count = thermal_model.get_probe_count()
        thermal_model.update_tau(test_probe, is_cooling=True)
        assert thermal_model.get_probe_count() == initial_count + 1

    def test_probe_result_backward_compatibility(self):
        """Test ProbeResult dataclass maintains backward compatibility.
        
        Ensures existing code can create ProbeResult objects.
        """
        # Test original constructor (required fields only)
        probe_minimal = ProbeResult(
            tau_value=90.0,
            confidence=0.8,
            duration=1800,
            fit_quality=0.85,
            aborted=False
        )
        
        assert probe_minimal.tau_value == 90.0
        assert probe_minimal.confidence == 0.8
        assert probe_minimal.duration == 1800
        assert probe_minimal.fit_quality == 0.85
        assert probe_minimal.aborted == False
        assert isinstance(probe_minimal.timestamp, datetime)
        assert probe_minimal.outdoor_temp is None  # New field defaults to None
        
        # Test with timestamp (common pattern)
        custom_timestamp = datetime(2025, 8, 15, 10, 0, 0, tzinfo=timezone.utc)
        probe_with_timestamp = ProbeResult(
            tau_value=85.0,
            confidence=0.9,
            duration=2400,
            fit_quality=0.92,
            aborted=False,
            timestamp=custom_timestamp
        )
        
        assert probe_with_timestamp.timestamp == custom_timestamp
        assert probe_with_timestamp.outdoor_temp is None
        
        # Test with new outdoor_temp field (v1.5.3)
        probe_with_outdoor = ProbeResult(
            tau_value=88.0,
            confidence=0.85,
            duration=2100,
            fit_quality=0.88,
            aborted=False,
            outdoor_temp=25.5
        )
        
        assert probe_with_outdoor.outdoor_temp == 25.5

    def test_existing_probe_history_behavior(self, thermal_model):
        """Test probe history behavior with existing patterns.
        
        Ensures existing code patterns continue to work.
        """
        # Test empty history behavior (existing)
        assert thermal_model.get_probe_count() == 0
        assert thermal_model.get_confidence() == 0.0
        
        # Test single probe behavior (existing)
        single_probe = create_probe_result(tau_value=90.0, confidence=0.7)
        thermal_model.update_tau(single_probe, is_cooling=True)
        
        assert thermal_model.get_probe_count() == 1
        single_confidence = thermal_model.get_confidence()
        assert single_confidence > 0.0
        assert single_confidence < 0.5  # Should be low with single probe
        
        # Test multiple probe behavior (existing - up to 5 probes was common)
        for i in range(4):  # Add 4 more for total of 5
            probe = create_probe_result(tau_value=90.0 + i, confidence=0.7 + (i * 0.05))
            thermal_model.update_tau(probe, is_cooling=True)
        
        assert thermal_model.get_probe_count() == 5
        five_probe_confidence = thermal_model.get_confidence()
        assert five_probe_confidence > single_confidence  # Should improve with more data
        
        # Test that tau updates still work as expected
        original_tau = thermal_model._tau_cooling
        high_tau_probe = create_probe_result(tau_value=120.0, confidence=0.95)
        thermal_model.update_tau(high_tau_probe, is_cooling=True)
        
        new_tau = thermal_model._tau_cooling
        assert new_tau != original_tau  # Should have changed
        assert new_tau > original_tau   # Should have increased toward 120.0

    def test_serialization_compatibility(self):
        """Test thermal manager serialization remains compatible.
        
        Ensures existing persistence code continues to work.
        """
        # Create thermal manager with mixed probe types
        mock_hass = Mock()
        thermal_model = PassiveThermalModel()
        thermal_manager = ThermalManager(mock_hass, thermal_model, Mock())
        
        # Add legacy probes (existing format)
        legacy_probes = [
            create_legacy_probe(tau_value=85.0, confidence=0.7, age_days=3),
            create_legacy_probe(tau_value=90.0, confidence=0.8, age_days=1),
        ]
        
        for probe in legacy_probes:
            thermal_model.update_tau(probe, is_cooling=True)
        
        # Add v1.5.3 probes
        v153_probes = [
            create_probe_result(tau_value=88.0, confidence=0.85, outdoor_temp=25.0),
            create_probe_result(tau_value=92.0, confidence=0.90, outdoor_temp=30.0),
        ]
        
        for probe in v153_probes:
            thermal_model.update_tau(probe, is_cooling=True)
        
        # Test serialization
        serialized = thermal_manager.serialize()
        
        # Assert serialization format compatibility
        assert isinstance(serialized, dict)
        assert 'probe_history' in serialized
        assert 'model' in serialized
        
        probe_data = serialized['probe_history']
        assert len(probe_data) == 4
        
        # Check legacy probe serialization
        legacy_serialized = [p for p in probe_data if p.get('outdoor_temp') is None]
        assert len(legacy_serialized) == 2
        
        # Check v1.5.3 probe serialization
        v153_serialized = [p for p in probe_data if p.get('outdoor_temp') is not None]
        assert len(v153_serialized) == 2
        
        # Test deserialization
        fresh_manager = ThermalManager(mock_hass, PassiveThermalModel(), Mock())
        fresh_manager.restore(serialized)
        
        assert fresh_manager._model.get_probe_count() == 4
        restored_confidence = fresh_manager._model.get_confidence()
        assert restored_confidence > 0.0

    def test_confidence_calculation_regression(self, thermal_model):
        """Test confidence calculation produces expected results.
        
        Ensures confidence formula changes don't break existing behavior expectations.
        """
        # Test known confidence scenarios
        
        # Scenario 1: Single high-confidence probe
        single_probe = create_probe_result(tau_value=90.0, confidence=0.9)
        thermal_model.update_tau(single_probe, is_cooling=True)
        
        single_confidence = thermal_model.get_confidence()
        # With 1 probe and CONFIDENCE_REQUIRED_SAMPLES=30: confidence = 0.9 * (1/30) = 0.03
        expected_single = 0.9 * (1 / CONFIDENCE_REQUIRED_SAMPLES)
        assert abs(single_confidence - expected_single) < 0.01
        
        # Scenario 2: Multiple probes below threshold
        for i in range(14):  # Total 15 probes (half of required samples)
            probe = create_probe_result(tau_value=90.0, confidence=0.8)
            thermal_model.update_tau(probe, is_cooling=True)
        
        partial_confidence = thermal_model.get_confidence()
        # With 15 probes: confidence = 0.8 * (15/30) = 0.4
        expected_partial = 0.8 * (15 / CONFIDENCE_REQUIRED_SAMPLES)
        assert abs(partial_confidence - expected_partial) < 0.05
        
        # Scenario 3: Full threshold reached
        for i in range(15):  # Add 15 more for total of 30
            probe = create_probe_result(tau_value=90.0, confidence=0.85)
            thermal_model.update_tau(probe, is_cooling=True)
        
        full_confidence = thermal_model.get_confidence()
        # Average confidence should be weighted average of all probes
        # Should be close to statistical maximum
        assert full_confidence > 0.7  # Should be high with 30 good probes
        assert full_confidence <= 1.0

    def test_thermal_manager_integration_regression(self):
        """Test thermal manager integration points remain stable.
        
        Ensures existing thermal manager usage patterns work.
        """
        # Test thermal manager creation (existing pattern)
        mock_hass = Mock()
        thermal_model = PassiveThermalModel()
        thermal_manager = ThermalManager(mock_hass, thermal_model, Mock())
        
        # Test basic operations that existing code relies on
        assert hasattr(thermal_manager, 'serialize')
        assert hasattr(thermal_manager, 'restore')
        assert hasattr(thermal_manager, '_model')
        
        # Test model access patterns
        assert thermal_manager._model is thermal_model
        assert thermal_manager._model.get_probe_count() == 0
        
        # Test probe addition through manager (if this pattern exists)
        test_probe = create_probe_result(tau_value=90.0, confidence=0.8)
        thermal_manager._model.update_tau(test_probe, is_cooling=True)
        
        assert thermal_manager._model.get_probe_count() == 1
        
        # Test serialization roundtrip (critical for persistence)
        serialized = thermal_manager.serialize()
        fresh_manager = ThermalManager(mock_hass, PassiveThermalModel(), Mock())
        fresh_manager.restore(serialized)
        
        assert fresh_manager._model.get_probe_count() == 1

    def test_no_breaking_changes_in_constants(self):
        """Test that constant changes don't break existing assumptions.
        
        Validates that new constants are additions, not breaking changes.
        """
        # Test that existing constants still exist and have reasonable values
        assert MAX_PROBE_HISTORY_SIZE == 75  # New v1.5.3 value
        assert MAX_PROBE_HISTORY_SIZE > 5    # Should be larger than old limit
        
        assert CONFIDENCE_REQUIRED_SAMPLES == 30  # New v1.5.3 value
        assert CONFIDENCE_REQUIRED_SAMPLES <= MAX_PROBE_HISTORY_SIZE
        
        assert DECAY_RATE_PER_DAY == 0.98  # New v1.5.3 value
        assert 0.9 < DECAY_RATE_PER_DAY < 1.0  # Should be reasonable decay rate
        
        # Test that these constants work in formulas
        test_confidence = 0.8 * min(10 / CONFIDENCE_REQUIRED_SAMPLES, 1.0)
        assert 0.0 <= test_confidence <= 1.0
        
        test_weight = DECAY_RATE_PER_DAY ** 30  # 30 days old
        assert 0.0 < test_weight < 1.0

    def test_legacy_data_migration_safety(self, legacy_thermal_model):
        """Test that existing data migrates safely to v1.5.3.
        
        Ensures no data loss or corruption during migration.
        """
        # Verify legacy model has expected initial state
        assert legacy_thermal_model.get_probe_count() == 3
        initial_confidence = legacy_thermal_model.get_confidence()
        initial_tau = legacy_thermal_model._tau_cooling
        
        # All probes should have outdoor_temp = None
        legacy_probes = list(legacy_thermal_model._probe_history)
        assert all(probe.outdoor_temp is None for probe in legacy_probes)
        
        # Test serialization of legacy data
        mock_hass = Mock()
        thermal_manager = ThermalManager(mock_hass, legacy_thermal_model, Mock())
        serialized = thermal_manager.serialize()
        
        # Verify legacy probes serialize correctly
        probe_data = serialized['probe_history']
        assert len(probe_data) == 3
        assert all(p.get('outdoor_temp') is None for p in probe_data)
        
        # Test restoration preserves legacy data
        fresh_manager = ThermalManager(mock_hass, PassiveThermalModel(), Mock())
        fresh_manager.restore(serialized)
        
        assert fresh_manager._model.get_probe_count() == 3
        restored_probes = list(fresh_manager._model._probe_history)
        assert all(probe.outdoor_temp is None for probe in restored_probes)
        
        # Test mixed operation (legacy + new data)
        new_probe = create_probe_result(tau_value=95.0, confidence=0.9, outdoor_temp=28.0)
        fresh_manager._model.update_tau(new_probe, is_cooling=True)
        
        assert fresh_manager._model.get_probe_count() == 4
        mixed_confidence = fresh_manager._model.get_confidence()
        assert mixed_confidence > 0.0  # Should work with mixed data

    def test_performance_regression_baseline(self, thermal_model):
        """Test that v1.5.3 doesn't regress performance significantly.
        
        Basic performance regression test (detailed testing in performance file).
        """
        import time
        
        # Create moderate dataset for regression testing
        baseline_probes = create_probe_sequence(
            count=20,
            start_days_ago=20,
            tau_base=90.0,
            confidence_base=0.8
        )
        
        for probe in baseline_probes:
            thermal_model.update_tau(probe, is_cooling=True)
        
        # Test key operations stay performant
        
        # Confidence calculation should be fast
        start_time = time.perf_counter()
        for _ in range(100):
            thermal_model.get_confidence()
        confidence_time = (time.perf_counter() - start_time) * 1000
        
        assert confidence_time < 50.0, f"Confidence regression: {confidence_time:.2f}ms (target: <50ms)"
        
        # Prediction should be very fast
        start_time = time.perf_counter()
        for _ in range(100):
            thermal_model.predict_drift(22.0, 28.0, 60, True)
        prediction_time = (time.perf_counter() - start_time) * 1000
        
        assert prediction_time < 20.0, f"Prediction regression: {prediction_time:.2f}ms (target: <20ms)"
        
        # Tau calculation should be reasonable
        start_time = time.perf_counter()
        for _ in range(50):
            thermal_model._calculate_weighted_tau(is_cooling=True)
        tau_time = (time.perf_counter() - start_time) * 1000
        
        assert tau_time < 100.0, f"Tau calculation regression: {tau_time:.2f}ms (target: <100ms)"

    def test_mathematical_precision_regression(self, thermal_model):
        """Test mathematical precision hasn't regressed with new algorithms.
        
        Ensures numerical stability and precision are maintained.
        """
        # Test edge cases for numerical precision
        
        # Very small time differences
        tiny_prediction = thermal_model.predict_drift(22.0, 22.001, 1, True)  # 1 minute, tiny difference
        assert abs(tiny_prediction - 22.0) < 0.1  # Should be very small change
        
        # Very large time differences (asymptotic behavior)
        large_prediction = thermal_model.predict_drift(20.0, 30.0, 10000, False)  # Very long time
        assert 29.9 <= large_prediction <= 30.0  # Should approach outdoor temp
        
        # Test with extreme confidence values
        extreme_probe = create_probe_result(tau_value=90.0, confidence=0.001)  # Very low confidence
        thermal_model.update_tau(extreme_probe, is_cooling=True)
        
        low_confidence = thermal_model.get_confidence()
        assert 0.0 <= low_confidence <= 1.0  # Should remain in valid range
        
        high_confidence_probe = create_probe_result(tau_value=90.0, confidence=0.999)  # Very high confidence
        thermal_model.update_tau(high_confidence_probe, is_cooling=True)
        
        high_confidence = thermal_model.get_confidence()
        assert 0.0 <= high_confidence <= 1.0  # Should remain in valid range
        
        # Test exponential decay precision
        very_old_probe = create_probe_result(tau_value=100.0, confidence=0.8, age_days=365)  # 1 year old
        thermal_model.update_tau(very_old_probe, is_cooling=True)
        
        # Should not cause numerical issues
        final_confidence = thermal_model.get_confidence()
        assert 0.0 <= final_confidence <= 1.0
        
        # Decay weight should be very small but not zero
        decay_weight = DECAY_RATE_PER_DAY ** 365
        assert 0.0 < decay_weight < 0.01  # Very small but not zero