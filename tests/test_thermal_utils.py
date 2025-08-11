"""ABOUTME: Unit tests for thermal utility functions.
Tests mathematical curve fitting functions for passive thermal learning."""

import pytest
import numpy as np
from typing import List, Tuple, Optional

from custom_components.smart_climate.thermal_utils import exponential_decay, analyze_drift_data
from custom_components.smart_climate.thermal_models import ProbeResult


class TestExponentialDecay:
    """Test the exponential decay mathematical function."""
    
    def test_exponential_decay_basic(self):
        """Test basic exponential decay calculation."""
        # Test at t=0: should equal T_initial
        result = exponential_decay(0.0, T_final=20.0, T_initial=25.0, tau=100.0)
        assert result == 25.0
        
    def test_exponential_decay_at_infinity(self):
        """Test decay approaches T_final as t approaches infinity."""
        # Test at very large t: should approach T_final
        result = exponential_decay(10000.0, T_final=20.0, T_initial=25.0, tau=100.0)
        assert abs(result - 20.0) < 0.001  # Very close to T_final
        
    def test_exponential_decay_tau_time_constant(self):
        """Test decay at tau time: should be ~63% of the way from initial to final."""
        T_initial, T_final, tau = 25.0, 20.0, 100.0
        result = exponential_decay(tau, T_final, T_initial, tau)
        
        # At t=tau, value should be T_final + (T_initial - T_final) * exp(-1)
        # exp(-1) ≈ 0.368, so we should be ~63% of the way to final value
        expected = T_final + (T_initial - T_final) * np.exp(-1)
        assert abs(result - expected) < 0.001
        
    def test_exponential_decay_negative_time(self):
        """Test exponential decay with negative time."""
        # Negative time should extrapolate backwards (temperature higher than initial)
        result = exponential_decay(-100.0, T_final=20.0, T_initial=25.0, tau=100.0)
        assert result > 25.0  # Should be higher than initial temp
        
    def test_exponential_decay_zero_temperature_difference(self):
        """Test when initial and final temperatures are equal."""
        result = exponential_decay(100.0, T_final=25.0, T_initial=25.0, tau=100.0)
        assert result == 25.0  # Should remain constant


class TestAnalyzeDriftData:
    """Test the drift data analysis function."""
    
    def test_analyze_drift_data_insufficient_points(self):
        """Test with insufficient data points (< 10)."""
        # Create data with only 9 points
        data = [(float(i), 25.0 - i * 0.1) for i in range(9)]
        result = analyze_drift_data(data)
        assert result is None
        
    def test_analyze_drift_data_empty_list(self):
        """Test with empty data list."""
        result = analyze_drift_data([])
        assert result is None
        
    def test_analyze_drift_data_perfect_exponential(self):
        """Test with perfect exponential decay data."""
        # Generate perfect exponential decay data
        tau_actual = 600.0  # 10 minutes
        T_initial, T_final = 25.0, 20.0
        times = np.linspace(0, 3600, 50)  # 1 hour of data, 50 points
        
        data = []
        for t in times:
            temp = exponential_decay(t, T_final, T_initial, tau_actual)
            data.append((t, temp))
            
        result = analyze_drift_data(data)
        assert result is not None
        assert isinstance(result, ProbeResult)
        
        # Should recover original tau (within reasonable tolerance)
        assert abs(result.tau_value - tau_actual) < 50  # Within 50 seconds
        assert result.confidence > 0.8  # Should have high confidence for perfect data
        assert result.duration == times[-1] - times[0]
        assert result.fit_quality > 0.9  # Should have excellent fit quality
        assert not result.aborted
        
    def test_analyze_drift_data_passive_confidence_scaling(self):
        """Test that passive mode scales confidence by 0.5x."""
        # Generate reasonable exponential data
        tau_actual = 600.0
        T_initial, T_final = 25.0, 20.0
        times = np.linspace(0, 3600, 20)  # Fewer points for lower confidence
        
        data = []
        for t in times:
            temp = exponential_decay(t, T_final, T_initial, tau_actual)
            # Add small amount of noise
            temp += np.random.normal(0, 0.05)
            data.append((t, temp))
            
        # Compare active vs passive confidence
        result_active = analyze_drift_data(data, is_passive=False)
        result_passive = analyze_drift_data(data, is_passive=True)
        
        assert result_active is not None
        assert result_passive is not None
        
        # Passive confidence should be ~0.5x active confidence
        expected_passive_confidence = result_active.confidence * 0.5
        assert abs(result_passive.confidence - expected_passive_confidence) < 0.01
        
    def test_analyze_drift_data_noisy_data(self):
        """Test with noisy exponential data."""
        tau_actual = 900.0  # 15 minutes
        T_initial, T_final = 24.0, 21.0
        times = np.linspace(0, 2700, 30)  # 45 minutes, 30 points
        
        data = []
        np.random.seed(42)  # For reproducible test
        for t in times:
            temp = exponential_decay(t, T_final, T_initial, tau_actual)
            # Add realistic measurement noise
            temp += np.random.normal(0, 0.1)
            data.append((t, temp))
            
        result = analyze_drift_data(data)
        assert result is not None
        
        # Should still recover tau reasonably well despite noise
        assert abs(result.tau_value - tau_actual) < 200  # Within 200 seconds
        assert result.confidence > 0.3  # Should have reasonable confidence
        assert result.fit_quality > 0.5  # Decent fit quality
        
    def test_analyze_drift_data_linear_data_behavior(self):
        """Test behavior with purely linear data."""
        # Create linear temperature change (not exponential)
        times = np.linspace(0, 1800, 20)
        data = [(t, 25.0 - t * 0.001) for t in times]  # Linear decrease
        
        result = analyze_drift_data(data)
        # Linear data can still be fit with exponential, but tau should be very large
        if result is not None:
            # Linear behavior corresponds to very large tau (slow exponential)
            assert result.tau_value > 10000  # Should be much larger than typical tau values
            
    def test_analyze_drift_data_tau_bounds_respected(self):
        """Test that returned tau values respect the 300-86400 second bounds."""
        # This test uses realistic data that should produce valid tau
        tau_actual = 1200.0  # 20 minutes - within bounds
        T_initial, T_final = 26.0, 22.0
        times = np.linspace(0, 3600, 25)
        
        data = []
        for t in times:
            temp = exponential_decay(t, T_final, T_initial, tau_actual)
            data.append((t, temp))
            
        result = analyze_drift_data(data)
        if result is not None:
            assert 300 <= result.tau_value <= 86400
            
    def test_analyze_drift_data_invalid_input_types(self):
        """Test with invalid input data types."""
        # Test with non-tuple data - should return None
        invalid_data = [1, 2, 3, 4, 5]
        result = analyze_drift_data(invalid_data)
        assert result is None
        
        # Test with points that don't have 2 elements
        invalid_data2 = [(1, 2, 3), (4, 5, 6)]
        result2 = analyze_drift_data(invalid_data2)
        assert result2 is None