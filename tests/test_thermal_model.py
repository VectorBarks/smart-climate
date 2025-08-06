# ABOUTME: Test suite for PassiveThermalModel RC thermal circuit implementation
# ABOUTME: Covers drift prediction, dual tau values, and confidence calculations

import pytest
import math
from unittest.mock import Mock

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
        assert model._probe_history == []
        
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
        
    def test_get_confidence_returns_fixed_value(self):
        """Test get_confidence returns fixed 0.3 for now."""
        confidence = self.model.get_confidence()
        assert confidence == 0.3
        
    def test_get_confidence_consistent(self):
        """Test get_confidence returns consistent value."""
        confidence1 = self.model.get_confidence()
        confidence2 = self.model.get_confidence()
        assert confidence1 == confidence2 == 0.3
        
    def test_probe_history_initialized_empty(self):
        """Test probe history is initialized as empty list."""
        assert self.model._probe_history == []
        assert len(self.model._probe_history) == 0
        
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