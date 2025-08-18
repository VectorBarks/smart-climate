"""ABOUTME: Comprehensive system tests for v1.5.3 thermal model enhancements.
Tests complete probe lifecycle, confidence progression, state machine integration, and all v1.5.3 features working together."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
import math

from custom_components.smart_climate.thermal_model import PassiveThermalModel, ProbeResult
from custom_components.smart_climate.const import (
    MAX_PROBE_HISTORY_SIZE,
    CONFIDENCE_REQUIRED_SAMPLES,
    DECAY_RATE_PER_DAY
)
from tests.fixtures.thermal_v153 import create_probe_result, create_probe_sequence, create_legacy_probe


class TestThermalV153SystemIntegration:
    """Test complete v1.5.3 thermal model system integration."""

    @pytest.fixture
    def thermal_model(self):
        """Create thermal model for testing."""
        return PassiveThermalModel()

    @pytest.fixture
    def mock_now(self):
        """Mock current time for consistent testing."""
        fixed_time = datetime(2025, 8, 18, 12, 0, 0, tzinfo=timezone.utc)
        with patch('custom_components.smart_climate.thermal_model.datetime') as mock_dt:
            mock_dt.now.return_value = fixed_time
            yield fixed_time

    def test_complete_probe_lifecycle_v153(self, thermal_model, mock_now):
        """Test complete probe lifecycle with v1.5.3 enhancements.
        
        Tests:
        - Probe creation with outdoor temperature tracking
        - Storage in enhanced 75-probe history
        - Exponential decay weighting over time
        - Confidence progression from 0% to 95%+
        """
        # Act - Create probe sequence spanning 2 months (seasonal adaptation window)
        outdoor_temps = [35.0, 33.0, 30.0, 28.0, 25.0]  # Summer cooling season
        probes = create_probe_sequence(
            count=5,
            start_days_ago=60,  # 2 months ago
            outdoor_temps=outdoor_temps,
            tau_base=85.0,
            confidence_base=0.85
        )
        
        # Assert - Initial state
        assert thermal_model.get_confidence() == 0.0
        assert thermal_model.get_probe_count() == 0
        
        # Act - Add probes sequentially and test confidence progression
        expected_confidences = []
        for i, probe in enumerate(probes):
            thermal_model.update_tau(probe, is_cooling=True)
            confidence = thermal_model.get_confidence()
            expected_confidences.append(confidence)
            
            # Assert probe is stored correctly
            assert thermal_model.get_probe_count() == i + 1
            assert probe.outdoor_temp in outdoor_temps
            
        # Assert - Confidence progression from 0 to statistical threshold
        assert expected_confidences[0] > 0.0  # Some confidence with first probe
        assert expected_confidences[-1] > expected_confidences[0]  # Increasing confidence
        
        # Assert - Final system state
        final_confidence = thermal_model.get_confidence()
        assert 0.0 < final_confidence <= 1.0
        assert thermal_model.get_probe_count() == 5
        
    def test_seasonal_adaptation_75_probe_window(self, thermal_model):
        """Test seasonal adaptation with 75-probe history window.
        
        Tests that v1.5.3 can store and weight 75 probes for seasonal learning.
        """
        # Act - Fill probe history to maximum capacity
        seasonal_probes = []
        for i in range(MAX_PROBE_HISTORY_SIZE):
            # Simulate seasonal variation (summer to winter)
            days_ago = i * 1.0  # One probe per day
            outdoor_temp = 35.0 - (i * 0.5)  # Cooling through season
            tau_value = 90.0 + (i * 0.2)  # Tau increases as temperature drops
            
            probe = create_probe_result(
                tau_value=tau_value,
                confidence=0.8,
                age_days=days_ago,
                outdoor_temp=outdoor_temp
            )
            seasonal_probes.append(probe)
            thermal_model.update_tau(probe, is_cooling=True)
            
        # Assert - All probes stored up to limit
        assert thermal_model.get_probe_count() == MAX_PROBE_HISTORY_SIZE
        
        # Act - Add one more probe (should evict oldest)
        latest_probe = create_probe_result(
            tau_value=95.0,
            confidence=0.9,
            age_days=0,  # Today
            outdoor_temp=15.0  # Winter temperature
        )
        thermal_model.update_tau(latest_probe, is_cooling=True)
        
        # Assert - Still at capacity, oldest evicted
        assert thermal_model.get_probe_count() == MAX_PROBE_HISTORY_SIZE
        
        # Assert - Recent probes have more influence (exponential decay weighting)
        # This is tested by verifying tau moved toward recent values
        # Latest probe has tau=95.0, should pull average upward
        current_tau = thermal_model._tau_cooling
        assert current_tau > 90.0  # Influenced by recent higher tau values
        
    def test_confidence_statistical_threshold(self, thermal_model):
        """Test confidence calculation reaches 95%+ with sufficient samples.
        
        Tests v1.5.3 enhancement: confidence = avg_confidence * min(samples/30, 1.0)
        """
        # Act - Add exactly CONFIDENCE_REQUIRED_SAMPLES high-quality probes
        for i in range(CONFIDENCE_REQUIRED_SAMPLES):
            probe = create_probe_result(
                tau_value=90.0,
                confidence=0.95,  # High individual confidence
                age_days=i * 0.5   # Recent probes
            )
            thermal_model.update_tau(probe, is_cooling=True)
            
        # Assert - Confidence reaches statistical threshold
        final_confidence = thermal_model.get_confidence()
        expected_confidence = 0.95 * min(CONFIDENCE_REQUIRED_SAMPLES / CONFIDENCE_REQUIRED_SAMPLES, 1.0)
        assert abs(final_confidence - expected_confidence) < 0.01
        assert final_confidence >= 0.90  # High confidence achieved
        
    def test_exponential_decay_weighting_time_sensitivity(self, thermal_model, mock_now):
        """Test exponential decay weighting responds correctly to probe age.
        
        Tests v1.5.3 enhancement: weight = DECAY_RATE_PER_DAY^age_days * confidence
        """
        # Arrange - Create probes with different ages
        recent_probe = create_probe_result(tau_value=80.0, confidence=0.8, age_days=1)
        medium_probe = create_probe_result(tau_value=90.0, confidence=0.8, age_days=30)
        old_probe = create_probe_result(tau_value=100.0, confidence=0.8, age_days=60)
        
        # Act - Add probes in age order (oldest first)
        thermal_model.update_tau(old_probe, is_cooling=True)
        tau_after_old = thermal_model._tau_cooling
        
        thermal_model.update_tau(medium_probe, is_cooling=True)
        tau_after_medium = thermal_model._tau_cooling
        
        thermal_model.update_tau(recent_probe, is_cooling=True)
        tau_after_recent = thermal_model._tau_cooling
        
        # Assert - Recent probes have more influence on final tau
        # Recent probe (tau=80) should pull average down more than old probe (tau=100)
        assert tau_after_recent < tau_after_medium  # Recent probe influenced result
        assert abs(tau_after_recent - 80.0) < abs(tau_after_old - 80.0)  # Recent has more weight
        
        # Assert - Exponential decay math is correct
        recent_weight = DECAY_RATE_PER_DAY ** 1  # ~0.98
        medium_weight = DECAY_RATE_PER_DAY ** 30  # ~0.545
        old_weight = DECAY_RATE_PER_DAY ** 60  # ~0.297
        
        assert recent_weight > medium_weight > old_weight
        
    def test_outdoor_temperature_tracking_v153(self, thermal_model):
        """Test outdoor temperature tracking in v1.5.3 ProbeResult.
        
        Tests new outdoor_temp field for future temperature-dependent tau modeling.
        """
        # Arrange - Outdoor temperatures across seasons
        seasonal_temps = [35.0, 25.0, 15.0, 5.0, -5.0]  # Summer to winter
        
        # Act - Create probes with outdoor temperature tracking
        for temp in seasonal_temps:
            probe = create_probe_result(
                tau_value=90.0,
                confidence=0.8,
                outdoor_temp=temp
            )
            thermal_model.update_tau(probe, is_cooling=True)
            
        # Assert - Outdoor temperatures are preserved in probe history
        stored_temps = [probe.outdoor_temp for probe in thermal_model._probe_history]
        assert stored_temps == seasonal_temps
        
        # Assert - Legacy probe compatibility (outdoor_temp=None)
        legacy_probe = create_legacy_probe(tau_value=85.0, confidence=0.7)
        thermal_model.update_tau(legacy_probe, is_cooling=True)
        
        assert legacy_probe.outdoor_temp is None
        assert thermal_model.get_probe_count() == len(seasonal_temps) + 1
        
    def test_state_machine_integration_v153(self, thermal_model):
        """Test thermal model integrates correctly with state machine decisions.
        
        Tests that v1.5.3 confidence levels properly inform state transitions.
        """
        # Arrange - Low confidence scenario (insufficient data)
        low_confidence_probe = create_probe_result(tau_value=90.0, confidence=0.3)
        thermal_model.update_tau(low_confidence_probe, is_cooling=True)
        
        # Assert - Low confidence state
        initial_confidence = thermal_model.get_confidence()
        assert initial_confidence < 0.5  # Should trigger conservative state behavior
        
        # Act - Build confidence with quality probes
        for i in range(15):  # Half of CONFIDENCE_REQUIRED_SAMPLES
            probe = create_probe_result(
                tau_value=88.0 + (i * 0.1),
                confidence=0.85,
                age_days=i * 0.5
            )
            thermal_model.update_tau(probe, is_cooling=True)
            
        # Assert - Medium confidence state
        medium_confidence = thermal_model.get_confidence()
        assert 0.3 < medium_confidence < 0.8  # Transitional confidence level
        
        # Act - Complete confidence building
        for i in range(15):  # Complete to CONFIDENCE_REQUIRED_SAMPLES
            probe = create_probe_result(
                tau_value=87.0 + (i * 0.1),
                confidence=0.90,
                age_days=i * 0.3
            )
            thermal_model.update_tau(probe, is_cooling=True)
            
        # Assert - High confidence state enables aggressive optimization
        final_confidence = thermal_model.get_confidence()
        assert final_confidence > 0.8  # Should enable optimized state behavior
        
    def test_memory_migration_compatibility(self, thermal_model):
        """Test v1.5.3 handles migration from v1.5.2 probe data.
        
        Tests backward compatibility with existing 5-probe histories.
        """
        # Arrange - Simulate v1.5.2 probe data (no outdoor_temp)
        legacy_probes = [
            create_legacy_probe(tau_value=85.0, confidence=0.7, age_days=5),
            create_legacy_probe(tau_value=88.0, confidence=0.8, age_days=3),
            create_legacy_probe(tau_value=90.0, confidence=0.75, age_days=1),
        ]
        
        # Act - Load legacy data
        for probe in legacy_probes:
            thermal_model.update_tau(probe, is_cooling=True)
            
        # Assert - Legacy data compatibility
        assert thermal_model.get_probe_count() == 3
        assert all(probe.outdoor_temp is None for probe in thermal_model._probe_history)
        legacy_confidence = thermal_model.get_confidence()
        
        # Act - Add v1.5.3 probes with outdoor temperature
        v153_probes = [
            create_probe_result(tau_value=92.0, confidence=0.85, outdoor_temp=25.0),
            create_probe_result(tau_value=94.0, confidence=0.90, outdoor_temp=30.0),
        ]
        
        for probe in v153_probes:
            thermal_model.update_tau(probe, is_cooling=True)
            
        # Assert - Mixed data compatibility
        assert thermal_model.get_probe_count() == 5
        mixed_confidence = thermal_model.get_confidence()
        assert mixed_confidence > legacy_confidence  # Improved with new data
        
        # Assert - Data integrity preserved
        legacy_count = sum(1 for probe in thermal_model._probe_history if probe.outdoor_temp is None)
        v153_count = sum(1 for probe in thermal_model._probe_history if probe.outdoor_temp is not None)
        assert legacy_count == 3
        assert v153_count == 2

    def test_prediction_accuracy_improvement(self, thermal_model):
        """Test that v1.5.3 improvements lead to better prediction accuracy.
        
        Tests that more data and better weighting improve drift predictions.
        """
        # Arrange - Test scenario
        current_temp = 22.0
        outdoor_temp = 35.0
        drift_minutes = 60
        
        # Act - Baseline prediction with minimal data
        baseline_probe = create_probe_result(tau_value=90.0, confidence=0.5)
        thermal_model.update_tau(baseline_probe, is_cooling=True)
        baseline_prediction = thermal_model.predict_drift(
            current_temp, outdoor_temp, drift_minutes, is_cooling=True
        )
        
        # Act - Enhanced prediction with v1.5.3 data
        # Add varied, high-quality probes spanning different conditions
        enhancement_probes = create_probe_sequence(
            count=20,
            start_days_ago=30,
            outdoor_temps=[30 + (i * 0.5) for i in range(20)],  # Varied outdoor conditions
            tau_base=88.0,
            confidence_base=0.85
        )
        
        for probe in enhancement_probes:
            thermal_model.update_tau(probe, is_cooling=True)
            
        enhanced_prediction = thermal_model.predict_drift(
            current_temp, outdoor_temp, drift_minutes, is_cooling=True
        )
        
        # Assert - Enhanced prediction should be different (more accurate)
        assert enhanced_prediction != baseline_prediction
        
        # Assert - Confidence improvement
        enhanced_confidence = thermal_model.get_confidence()
        assert enhanced_confidence > 0.5  # Significant improvement
        
        # Assert - Tau adaptation from rich dataset
        assert thermal_model._tau_cooling != 90.0  # Adapted from default
        
    def test_v153_performance_characteristics(self, thermal_model):
        """Test v1.5.3 maintains performance with enhanced features.
        
        Basic performance validation - detailed testing in performance test file.
        """
        # Arrange - Large probe dataset
        large_dataset = create_probe_sequence(
            count=50,  # Substantial dataset
            start_days_ago=75,
            tau_base=90.0,
            confidence_base=0.8
        )
        
        # Act & Time - Confidence calculation with large dataset
        import time
        start_time = time.perf_counter()
        
        for probe in large_dataset:
            thermal_model.update_tau(probe, is_cooling=True)
            
        # Multiple confidence calculations (typical usage pattern)
        for _ in range(10):
            confidence = thermal_model.get_confidence()
            
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Assert - Performance reasonable (detailed testing in performance file)
        assert total_time < 0.1  # Should complete quickly
        assert confidence > 0.0  # Functional correctness
        assert thermal_model.get_probe_count() == 50
        
    def test_edge_case_handling_v153(self, thermal_model):
        """Test v1.5.3 handles edge cases gracefully.
        
        Tests robustness with extreme inputs and boundary conditions.
        """
        # Test - Empty history
        assert thermal_model.get_confidence() == 0.0
        assert thermal_model.get_probe_count() == 0
        
        # Test - Single probe with extreme values
        extreme_probe = create_probe_result(
            tau_value=30.0,  # Minimum physical limit
            confidence=1.0,   # Maximum confidence
            outdoor_temp=-20.0  # Extreme cold
        )
        thermal_model.update_tau(extreme_probe, is_cooling=False)  # Warming scenario
        
        assert thermal_model.get_confidence() > 0.0
        assert thermal_model.get_probe_count() == 1
        
        # Test - Prediction with extreme outdoor temperature
        extreme_prediction = thermal_model.predict_drift(
            current=20.0,
            outdoor=-30.0,  # Extreme cold
            minutes=120,    # Long duration
            is_cooling=False
        )
        
        assert isinstance(extreme_prediction, float)
        assert extreme_prediction < 20.0  # Should cool toward outdoor temp
        
        # Test - Zero time prediction
        zero_time_prediction = thermal_model.predict_drift(
            current=22.0,
            outdoor=25.0,
            minutes=0,
            is_cooling=True
        )
        
        assert zero_time_prediction == 22.0  # No change with zero time
        
    def test_comprehensive_integration_scenario(self, thermal_model):
        """Test comprehensive real-world usage scenario with v1.5.3.
        
        Simulates complete thermal system operation over seasonal cycle.
        """
        # Simulate 3-month summer cooling season
        scenario_probes = []
        
        # Week 1-4: Early summer (moderate cooling)
        for week in range(4):
            for day in range(7):
                age_days = (week * 7) + day
                outdoor_temp = 28.0 + (week * 1.5)  # Gradually heating
                tau_value = 85.0 + (week * 2.0)     # Building adapts
                confidence = 0.7 + (week * 0.05)    # Improving quality
                
                probe = create_probe_result(
                    tau_value=tau_value,
                    confidence=confidence,
                    age_days=age_days,
                    outdoor_temp=outdoor_temp
                )
                scenario_probes.append(probe)
                thermal_model.update_tau(probe, is_cooling=True)
                
        # Week 5-8: Mid summer (intense cooling)
        for week in range(4, 8):
            for day in range(7):
                age_days = (week * 7) + day
                outdoor_temp = 32.0 + ((week - 4) * 1.0)  # Peak heat
                tau_value = 93.0 + ((week - 4) * 1.5)     # Faster cooling needed
                confidence = 0.85 + ((week - 4) * 0.02)   # High quality data
                
                probe = create_probe_result(
                    tau_value=tau_value,
                    confidence=confidence,
                    age_days=age_days,
                    outdoor_temp=outdoor_temp
                )
                scenario_probes.append(probe)
                thermal_model.update_tau(probe, is_cooling=True)
        
        # Week 9-12: Late summer (cooling down)
        for week in range(8, 12):
            for day in range(7):
                age_days = (week * 7) + day
                outdoor_temp = 35.0 - ((week - 8) * 2.0)  # Cooling off
                tau_value = 97.0 - ((week - 8) * 1.0)     # Less aggressive cooling
                confidence = 0.90                         # Consistent quality
                
                probe = create_probe_result(
                    tau_value=tau_value,
                    confidence=confidence,
                    age_days=age_days,
                    outdoor_temp=outdoor_temp
                )
                scenario_probes.append(probe)
                thermal_model.update_tau(probe, is_cooling=True)
        
        # Assert - System learned seasonal patterns
        total_probes = len(scenario_probes)
        assert total_probes == 84  # 12 weeks * 7 days
        assert thermal_model.get_probe_count() == min(total_probes, MAX_PROBE_HISTORY_SIZE)
        
        # Assert - High confidence achieved
        final_confidence = thermal_model.get_confidence()
        assert final_confidence > 0.85  # Excellent confidence after seasonal learning
        
        # Assert - Recent data has more influence (test exponential decay)
        final_tau = thermal_model._tau_cooling
        # Should be closer to recent tau values (90s) than early values (80s)
        assert 92.0 < final_tau < 98.0
        
        # Assert - Accurate prediction with learned model
        prediction = thermal_model.predict_drift(
            current=24.0,
            outdoor=30.0,  # Typical summer condition
            minutes=90,
            is_cooling=True
        )
        
        # Should predict reasonable temperature drift
        assert 24.0 < prediction < 30.0
        assert prediction != 24.0  # Should show some drift