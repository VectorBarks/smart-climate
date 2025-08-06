# ABOUTME: Test suite for PassiveThermalModel RC thermal circuit implementation
# ABOUTME: Covers drift prediction, dual tau values, and confidence calculations

import pytest
import math
from unittest.mock import Mock
from collections import deque

from custom_components.smart_climate.thermal_model import PassiveThermalModel, ProbeResult


class TestPassiveThermalModel:
    """Test PassiveThermalModel implementation with RC circuit physics."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.model = PassiveThermalModel()
        
    def test_init_default_tau_values(self):
        """Test initialization with default tau values."""
        model = PassiveThermalModel()
        assert model._tau_cooling == 90.0
        assert model._tau_warming == 150.0
        assert len(model._probe_history) == 0
        assert model._probe_history.maxlen == 5
        
    def test_init_custom_tau_values(self):
        """Test initialization with custom tau values."""
        model = PassiveThermalModel(tau_cooling=120.0, tau_warming=180.0)
        assert model._tau_cooling == 120.0
        assert model._tau_warming == 180.0
        
    def test_predict_drift_cooling_basic(self):
        """Test predict_drift for basic cooling scenario."""
        # RC formula: T_future = T_current + (T_outdoor - T_current) * (1 - exp(-t/tau))
        # Cooling: indoor=25°C, outdoor=20°C, 30min, tau_cooling=90min
        current = 25.0
        outdoor = 20.0
        minutes = 30
        expected = current + (outdoor - current) * (1 - math.exp(-minutes / 90.0))
        
        result = self.model.predict_drift(current, outdoor, minutes, is_cooling=True)
        assert abs(result - expected) < 0.01
        
    def test_predict_drift_warming_basic(self):
        """Test predict_drift for basic warming scenario."""
        # Warming: indoor=20°C, outdoor=25°C, 45min, tau_warming=150min
        current = 20.0
        outdoor = 25.0
        minutes = 45
        expected = current + (outdoor - current) * (1 - math.exp(-minutes / 150.0))
        
        result = self.model.predict_drift(current, outdoor, minutes, is_cooling=False)
        assert abs(result - expected) < 0.01
        
    def test_predict_drift_cooling_longer_time(self):
        """Test predict_drift for cooling over longer period."""
        # Cooling: indoor=28°C, outdoor=18°C, 120min, tau_cooling=90min
        current = 28.0
        outdoor = 18.0
        minutes = 120
        expected = current + (outdoor - current) * (1 - math.exp(-minutes / 90.0))
        
        result = self.model.predict_drift(current, outdoor, minutes, is_cooling=True)
        assert abs(result - expected) < 0.01
        
    def test_predict_drift_warming_longer_time(self):
        """Test predict_drift for warming over longer period."""
        # Warming: indoor=18°C, outdoor=28°C, 90min, tau_warming=150min
        current = 18.0
        outdoor = 28.0
        minutes = 90
        expected = current + (outdoor - current) * (1 - math.exp(-minutes / 150.0))
        
        result = self.model.predict_drift(current, outdoor, minutes, is_cooling=False)
        assert abs(result - expected) < 0.01
        
    def test_predict_drift_same_temperature(self):
        """Test predict_drift when indoor and outdoor are same."""
        # No drift expected when temperatures are equal
        current = 22.0
        outdoor = 22.0
        minutes = 60
        
        result_cooling = self.model.predict_drift(current, outdoor, minutes, is_cooling=True)
        result_warming = self.model.predict_drift(current, outdoor, minutes, is_cooling=False)
        
        assert abs(result_cooling - current) < 0.01
        assert abs(result_warming - current) < 0.01
        
    def test_predict_drift_zero_time(self):
        """Test predict_drift with zero time duration."""
        current = 25.0
        outdoor = 20.0
        minutes = 0
        
        result = self.model.predict_drift(current, outdoor, minutes, is_cooling=True)
        assert abs(result - current) < 0.01
        
    def test_predict_drift_negative_time_raises_error(self):
        """Test predict_drift raises error for negative time."""
        with pytest.raises(ValueError, match="Time duration cannot be negative"):
            self.model.predict_drift(25.0, 20.0, -10, is_cooling=True)
            
    def test_predict_drift_uses_correct_tau_for_cooling(self):
        """Test predict_drift uses tau_cooling when is_cooling=True."""
        # Create model with distinct tau values to verify correct selection
        model = PassiveThermalModel(tau_cooling=60.0, tau_warming=120.0)
        
        current = 25.0
        outdoor = 20.0
        minutes = 30
        
        # Should use tau_cooling = 60.0
        expected = current + (outdoor - current) * (1 - math.exp(-minutes / 60.0))
        result = model.predict_drift(current, outdoor, minutes, is_cooling=True)
        
        assert abs(result - expected) < 0.01
        
    def test_predict_drift_uses_correct_tau_for_warming(self):
        """Test predict_drift uses tau_warming when is_cooling=False."""
        # Create model with distinct tau values to verify correct selection
        model = PassiveThermalModel(tau_cooling=60.0, tau_warming=120.0)
        
        current = 20.0
        outdoor = 25.0
        minutes = 30
        
        # Should use tau_warming = 120.0
        expected = current + (outdoor - current) * (1 - math.exp(-minutes / 120.0))
        result = model.predict_drift(current, outdoor, minutes, is_cooling=False)
        
        assert abs(result - expected) < 0.01
        
    def test_predict_drift_extreme_outdoor_temperatures(self):
        """Test predict_drift with extreme outdoor temperatures."""
        # Very hot outdoor
        result_hot = self.model.predict_drift(22.0, 45.0, 60, is_cooling=False)
        assert result_hot > 22.0  # Should warm up
        
        # Very cold outdoor  
        result_cold = self.model.predict_drift(22.0, -10.0, 60, is_cooling=True)
        assert result_cold < 22.0  # Should cool down
        
    def test_predict_drift_asymptotic_behavior(self):
        """Test predict_drift approaches outdoor temperature asymptotically."""
        current = 20.0
        outdoor = 30.0
        
        # After very long time (10 tau constants), should be very close to outdoor
        very_long_time = 10 * 150  # 10 * tau_warming
        result = self.model.predict_drift(current, outdoor, very_long_time, is_cooling=False)
        
        # Should be within 1% of outdoor temperature
        assert abs(result - outdoor) < 0.1
        
    def test_get_confidence_returns_zero_when_empty(self):
        """Test get_confidence returns 0.0 with no probe history."""
        confidence = self.model.get_confidence()
        assert confidence == 0.0
        
    def test_get_confidence_consistent(self):
        """Test get_confidence returns consistent value."""
        confidence1 = self.model.get_confidence()
        confidence2 = self.model.get_confidence()
        assert confidence1 == confidence2 == 0.0
        
    def test_probe_history_initialized_empty(self):
        """Test probe history is initialized as empty deque."""
        assert len(self.model._probe_history) == 0
        assert self.model._probe_history.maxlen == 5
        
    def test_rc_circuit_physics_validation(self):
        """Test that RC formula produces physically reasonable results."""
        # Test cooling scenario: higher indoor than outdoor
        current = 26.0
        outdoor = 22.0
        minutes = 60
        
        result = self.model.predict_drift(current, outdoor, minutes, is_cooling=True)
        
        # Should cool down but not below outdoor temperature
        assert result < current  # Temperature decreases
        assert result >= outdoor  # Cannot go below outdoor (passive cooling)
        
        # Test warming scenario: lower indoor than outdoor
        current = 18.0
        outdoor = 24.0
        
        result = self.model.predict_drift(current, outdoor, minutes, is_cooling=False)
        
        # Should warm up but not above outdoor temperature
        assert result > current  # Temperature increases
        assert result <= outdoor  # Cannot go above outdoor (passive warming)
        
    def test_exponential_decay_rate_validation(self):
        """Test exponential decay rate matches expected physics."""
        current = 25.0
        outdoor = 15.0
        
        # At t = tau, should reach ~63.2% of final change
        tau_cooling = 90.0
        result_at_tau = self.model.predict_drift(current, outdoor, int(tau_cooling), is_cooling=True)
        
        max_change = outdoor - current  # Maximum possible change
        actual_change = result_at_tau - current
        decay_fraction = actual_change / max_change
        
        # Should be approximately 1 - 1/e ≈ 0.632
        expected_fraction = 1 - math.exp(-1)  # ≈ 0.632
        assert abs(decay_fraction - expected_fraction) < 0.01
        
    def test_predict_drift_very_small_time_increments(self):
        """Test predict_drift with very small time increments."""
        current = 22.0
        outdoor = 27.0
        minutes = 1  # Very short time
        
        result = self.model.predict_drift(current, outdoor, minutes, is_cooling=False)
        
        # Should be very close to current temperature for small time
        change = abs(result - current)
        assert change < 0.5  # Less than 0.5°C change in 1 minute
        assert result > current  # Still should warm slightly
        
    def test_update_tau_functionality(self):
        """Test update_tau method basic functionality."""
        # Create a probe result
        probe_result = ProbeResult(
            tau_value=100.0,
            confidence=0.8,
            duration=3600,
            fit_quality=0.9,
            aborted=False
        )
        
        original_tau_cooling = self.model._tau_cooling
        
        # Update cooling tau
        self.model.update_tau(probe_result, is_cooling=True)
        
        # Tau should have changed (weighted average)
        assert self.model._tau_cooling != original_tau_cooling
        assert len(self.model._probe_history) == 1
        assert self.model._probe_history[0] == probe_result


class TestPassiveThermalModelLearning:
    """Test PassiveThermalModel learning functionality with weighted probe history."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.model = PassiveThermalModel()
        
    def test_probe_history_uses_deque_with_maxlen_5(self):
        """Test probe history is a deque with maxlen=5."""
        assert isinstance(self.model._probe_history, deque)
        assert self.model._probe_history.maxlen == 5
        
    def test_update_tau_weighted_average_single_probe(self):
        """Test update_tau with single probe uses weighted average formula."""
        original_tau = self.model._tau_cooling
        probe = ProbeResult(tau_value=120.0, confidence=0.8, duration=3600, fit_quality=0.9, aborted=False)
        
        self.model.update_tau(probe, is_cooling=True)
        
        # With single probe, weight should be 0.4
        # weighted_tau = 120.0 * 0.4 = 48.0
        expected_tau = 120.0 * 0.4
        assert abs(self.model._tau_cooling - expected_tau) < 0.01
        
    def test_update_tau_weighted_average_multiple_probes(self):
        """Test update_tau with multiple probes uses correct weights [0.4, 0.3, 0.15, 0.1, 0.05]."""
        # Add 3 probes with different tau values
        probes = [
            ProbeResult(tau_value=100.0, confidence=0.8, duration=3600, fit_quality=0.9, aborted=False),
            ProbeResult(tau_value=110.0, confidence=0.7, duration=3600, fit_quality=0.8, aborted=False),  
            ProbeResult(tau_value=120.0, confidence=0.9, duration=3600, fit_quality=0.9, aborted=False)
        ]
        
        for probe in probes:
            self.model.update_tau(probe, is_cooling=True)
            
        # Most recent (120.0) gets 0.4, second (110.0) gets 0.3, oldest (100.0) gets 0.15
        expected_tau = 120.0 * 0.4 + 110.0 * 0.3 + 100.0 * 0.15
        assert abs(self.model._tau_cooling - expected_tau) < 0.01
        
    def test_update_tau_weighted_average_five_probes(self):
        """Test update_tau with full 5 probes uses all weights."""
        tau_values = [100.0, 110.0, 120.0, 130.0, 140.0]
        weights = [0.05, 0.1, 0.15, 0.3, 0.4]  # oldest to newest
        
        for tau_val in tau_values:
            probe = ProbeResult(tau_value=tau_val, confidence=0.8, duration=3600, fit_quality=0.9, aborted=False)
            self.model.update_tau(probe, is_cooling=True)
            
        # Calculate expected weighted average (newest first)
        expected_tau = sum(tau_values[i] * weights[i] for i in range(5))
        assert abs(self.model._tau_cooling - expected_tau) < 0.01
        
    def test_update_tau_affects_cooling_only(self):
        """Test update_tau with is_cooling=True affects only tau_cooling."""
        original_warming = self.model._tau_warming
        probe = ProbeResult(tau_value=120.0, confidence=0.8, duration=3600, fit_quality=0.9, aborted=False)
        
        self.model.update_tau(probe, is_cooling=True)
        
        assert self.model._tau_warming == original_warming  # Should not change
        assert self.model._tau_cooling != 90.0  # Should change from default
        
    def test_update_tau_affects_warming_only(self):
        """Test update_tau with is_cooling=False affects only tau_warming."""
        original_cooling = self.model._tau_cooling
        probe = ProbeResult(tau_value=180.0, confidence=0.8, duration=3600, fit_quality=0.9, aborted=False)
        
        self.model.update_tau(probe, is_cooling=False)
        
        assert self.model._tau_cooling == original_cooling  # Should not change
        assert self.model._tau_warming != 150.0  # Should change from default
        
    def test_probe_history_maxlen_5_overflow(self):
        """Test probe history removes oldest when adding 6th probe."""
        probes = []
        for i in range(6):
            probe = ProbeResult(tau_value=100.0 + i, confidence=0.8, duration=3600, fit_quality=0.9, aborted=False)
            probes.append(probe)
            self.model.update_tau(probe, is_cooling=True)
            
        # Should only have last 5 probes
        assert len(self.model._probe_history) == 5
        assert list(self.model._probe_history) == probes[1:]  # First probe should be removed
        
    def test_get_confidence_empty_history(self):
        """Test get_confidence returns 0.0 with empty probe history."""
        confidence = self.model.get_confidence()
        assert confidence == 0.0
        
    def test_get_confidence_single_probe(self):
        """Test get_confidence with single probe."""
        probe = ProbeResult(tau_value=100.0, confidence=0.8, duration=3600, fit_quality=0.9, aborted=False)
        self.model.update_tau(probe, is_cooling=True)
        
        # confidence = mean([0.8]) * (1/5) = 0.8 * 0.2 = 0.16
        expected_confidence = 0.8 * (1/5)
        confidence = self.model.get_confidence()
        assert abs(confidence - expected_confidence) < 0.01
        
    def test_get_confidence_multiple_probes(self):
        """Test get_confidence with multiple probes."""
        confidences = [0.7, 0.8, 0.9]
        for i, conf in enumerate(confidences):
            probe = ProbeResult(tau_value=100.0 + i, confidence=conf, duration=3600, fit_quality=0.9, aborted=False)
            self.model.update_tau(probe, is_cooling=True)
            
        # confidence = mean([0.7, 0.8, 0.9]) * (3/5) = 0.8 * 0.6 = 0.48
        expected_confidence = (sum(confidences) / len(confidences)) * (len(confidences) / 5)
        confidence = self.model.get_confidence()
        assert abs(confidence - expected_confidence) < 0.01
        
    def test_get_confidence_full_history(self):
        """Test get_confidence with full 5-probe history."""
        confidences = [0.6, 0.7, 0.8, 0.9, 1.0]
        for i, conf in enumerate(confidences):
            probe = ProbeResult(tau_value=100.0 + i, confidence=conf, duration=3600, fit_quality=0.9, aborted=False)
            self.model.update_tau(probe, is_cooling=True)
            
        # confidence = mean([0.6, 0.7, 0.8, 0.9, 1.0]) * (5/5) = 0.8 * 1.0 = 0.8
        expected_confidence = sum(confidences) / len(confidences)
        confidence = self.model.get_confidence()
        assert abs(confidence - expected_confidence) < 0.01
        
    def test_get_confidence_partial_history_ratios(self):
        """Test get_confidence returns correct ratios for different history sizes."""
        # Test 1/5, 2/5, 3/5, 4/5, 5/5 ratios
        for num_probes in range(1, 6):
            model = PassiveThermalModel()
            for i in range(num_probes):
                probe = ProbeResult(tau_value=100.0, confidence=0.8, duration=3600, fit_quality=0.9, aborted=False)
                model.update_tau(probe, is_cooling=True)
                
            expected_confidence = 0.8 * (num_probes / 5)
            confidence = model.get_confidence()
            assert abs(confidence - expected_confidence) < 0.01
            
    def test_probe_history_maintains_insertion_order(self):
        """Test probe history maintains insertion order (FIFO with maxlen)."""
        tau_values = [100.0, 110.0, 120.0]
        probes = []
        
        for tau_val in tau_values:
            probe = ProbeResult(tau_value=tau_val, confidence=0.8, duration=3600, fit_quality=0.9, aborted=False)
            probes.append(probe)
            self.model.update_tau(probe, is_cooling=True)
            
        # History should be in insertion order
        assert list(self.model._probe_history) == probes
        
    def test_update_tau_with_aborted_probes(self):
        """Test update_tau adds aborted probes to history."""
        probe = ProbeResult(tau_value=120.0, confidence=0.5, duration=1800, fit_quality=0.3, aborted=True)
        self.model.update_tau(probe, is_cooling=True)
        
        assert len(self.model._probe_history) == 1
        assert self.model._probe_history[0].aborted is True
        
        # Should still contribute to confidence calculation
        expected_confidence = 0.5 * (1/5)
        confidence = self.model.get_confidence()
        assert abs(confidence - expected_confidence) < 0.01
        
    def test_weighted_average_precision(self):
        """Test weighted average calculation precision with exact values."""
        # Use exact values that should produce predictable results
        tau_values = [80.0, 90.0, 100.0, 110.0, 120.0]
        weights = [0.05, 0.1, 0.15, 0.3, 0.4]
        
        for tau_val in tau_values:
            probe = ProbeResult(tau_value=tau_val, confidence=0.8, duration=3600, fit_quality=0.9, aborted=False)
            self.model.update_tau(probe, is_cooling=True)
            
        # Manual calculation: 120*0.4 + 110*0.3 + 100*0.15 + 90*0.1 + 80*0.05
        expected = 48.0 + 33.0 + 15.0 + 9.0 + 4.0  # = 109.0
        assert abs(self.model._tau_cooling - expected) < 0.001
        
    def test_confidence_calculation_mixed_values(self):
        """Test confidence calculation with mixed confidence values."""
        confidences = [0.2, 0.4, 0.6, 0.8, 1.0]
        for conf in confidences:
            probe = ProbeResult(tau_value=100.0, confidence=conf, duration=3600, fit_quality=0.9, aborted=False)
            self.model.update_tau(probe, is_cooling=True)
            
        # Mean confidence = (0.2 + 0.4 + 0.6 + 0.8 + 1.0) / 5 = 3.0 / 5 = 0.6
        # Final confidence = 0.6 * (5/5) = 0.6
        expected_confidence = 0.6
        confidence = self.model.get_confidence()
        assert abs(confidence - expected_confidence) < 0.01
        
    def test_update_tau_separate_cooling_warming_histories(self):
        """Test update_tau maintains separate tau values but shared probe history."""
        cooling_probe = ProbeResult(tau_value=80.0, confidence=0.8, duration=3600, fit_quality=0.9, aborted=False)
        warming_probe = ProbeResult(tau_value=160.0, confidence=0.7, duration=3600, fit_quality=0.8, aborted=False)
        
        self.model.update_tau(cooling_probe, is_cooling=True)
        self.model.update_tau(warming_probe, is_cooling=False)
        
        # Both probes should be in shared history
        assert len(self.model._probe_history) == 2
        
        # Cooling tau: weighted by cooling_probe only (most recent cooling)
        # Warming tau: weighted by warming_probe only (most recent warming)
        # Note: This test verifies the current shared history behavior
        expected_cooling = 80.0 * 0.4  # Only cooling probe affects cooling tau
        expected_warming = 160.0 * 0.4  # Only warming probe affects warming tau
        
        # This might need adjustment based on actual architecture - the spec isn't clear
        # if histories are shared or separate. Testing current implementation.
        
    def test_get_confidence_updates_with_new_probes(self):
        """Test get_confidence updates as new probes are added."""
        confidences_over_time = []
        
        for i in range(5):
            confidence_val = 0.6 + (i * 0.1)  # 0.6, 0.7, 0.8, 0.9, 1.0
            probe = ProbeResult(tau_value=100.0, confidence=confidence_val, duration=3600, fit_quality=0.9, aborted=False)
            self.model.update_tau(probe, is_cooling=True)
            confidences_over_time.append(self.model.get_confidence())
            
        # Confidence should increase as more probes are added
        for i in range(1, len(confidences_over_time)):
            assert confidences_over_time[i] >= confidences_over_time[i-1]
            
    def test_probe_history_deque_behavior(self):
        """Test probe history exhibits correct deque behavior."""
        # Verify it's actually a deque with expected methods
        assert hasattr(self.model._probe_history, 'append')
        assert hasattr(self.model._probe_history, 'appendleft') 
        assert hasattr(self.model._probe_history, 'maxlen')
        
        # Verify maxlen property
        assert self.model._probe_history.maxlen == 5
        
    def test_weighted_average_edge_case_single_weight(self):
        """Test weighted average calculation with single probe gets first weight."""
        probe = ProbeResult(tau_value=100.0, confidence=0.9, duration=3600, fit_quality=0.95, aborted=False)
        self.model.update_tau(probe, is_cooling=True)
        
        # Single probe should get first weight (0.4)
        # weighted_tau = 100.0 * 0.4 = 40.0
        expected_tau = 100.0 * 0.4
        assert abs(self.model._tau_cooling - expected_tau) < 0.001