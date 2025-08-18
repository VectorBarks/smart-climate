"""Test thermal weighting exponential decay system."""
import pytest
from datetime import datetime, timezone, timedelta
from custom_components.smart_climate.thermal_model import PassiveThermalModel, ProbeResult
from custom_components.smart_climate.const import DECAY_RATE_PER_DAY


class TestExponentialDecayWeighting:
    """Test exponential decay weighting for thermal model."""

    def test_fresh_probe_gets_full_weight(self):
        """Test that a fresh probe (0 days old) gets weight 1.0."""
        model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        
        # Create a fresh probe (current time)
        fresh_probe = ProbeResult(
            tau_value=100.0,
            confidence=1.0,
            duration=3600,
            fit_quality=0.9,
            aborted=False,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Add probe to history
        model._probe_history.append(fresh_probe)
        
        # Calculate weighted tau - should be exactly the probe's tau_value since it's fresh
        result = model._calculate_weighted_tau(is_cooling=True)
        assert abs(result - 100.0) < 0.01, f"Expected ~100.0, got {result}"

    def test_one_day_old_probe_with_fresh_probe(self):
        """Test that aged probes have less influence when combined with fresh probes."""
        model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        
        now = datetime.now(timezone.utc)
        
        # Create fresh probe (100.0) and 1-day old probe (50.0)
        fresh_probe = ProbeResult(100.0, 1.0, 3600, 0.9, False, now)
        aged_probe = ProbeResult(50.0, 1.0, 3600, 0.9, False, now - timedelta(days=1))
        
        # Add both probes to history
        model._probe_history.append(fresh_probe)
        model._probe_history.append(aged_probe)
        
        # Calculate weighted tau
        result = model._calculate_weighted_tau(is_cooling=True)
        
        # Expected: (100*1.0 + 50*0.98) / (1.0 + 0.98) = 149/1.98 ≈ 75.25
        fresh_weight = 1.0
        aged_weight = DECAY_RATE_PER_DAY ** 1
        expected = (100.0 * fresh_weight + 50.0 * aged_weight) / (fresh_weight + aged_weight)
        assert abs(result - expected) < 0.1, f"Expected ~{expected}, got {result}"

    def test_half_life_probe_gets_half_weight(self):
        """Test that a 34.3-day old probe gets weight ~0.5 (half-life)."""
        model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        
        # Create a 34.3-day old probe (half-life)
        half_life_days = 34.3
        half_life_ago = datetime.now(timezone.utc) - timedelta(days=half_life_days)
        old_probe = ProbeResult(
            tau_value=100.0,
            confidence=1.0,
            duration=3600,
            fit_quality=0.9,
            aborted=False,
            timestamp=half_life_ago
        )
        
        # Add probe to history
        model._probe_history.append(old_probe)
        
        # Calculate weighted tau
        result = model._calculate_weighted_tau(is_cooling=True)
        
        # Expected weight: 0.98^34.3 ≈ 0.5
        expected_weight = DECAY_RATE_PER_DAY ** half_life_days
        expected_result = 100.0 * expected_weight
        assert abs(result - expected_result) < 1.0, f"Expected ~{expected_result}, got {result}"
        assert abs(expected_weight - 0.5) < 0.1, f"Half-life weight should be ~0.5, got {expected_weight}"

    def test_sixty_day_old_probe_gets_low_weight(self):
        """Test that a 60-day old probe gets weight ~0.3."""
        model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        
        # Create a 60-day old probe
        sixty_days_ago = datetime.now(timezone.utc) - timedelta(days=60)
        old_probe = ProbeResult(
            tau_value=100.0,
            confidence=1.0,
            duration=3600,
            fit_quality=0.9,
            aborted=False,
            timestamp=sixty_days_ago
        )
        
        # Add probe to history
        model._probe_history.append(old_probe)
        
        # Calculate weighted tau
        result = model._calculate_weighted_tau(is_cooling=True)
        
        # Expected weight: 0.98^60 ≈ 0.3
        expected_weight = DECAY_RATE_PER_DAY ** 60
        expected_result = 100.0 * expected_weight
        assert abs(result - expected_result) < 1.0, f"Expected ~{expected_result}, got {result}"
        assert abs(expected_weight - 0.3) < 0.1, f"60-day weight should be ~0.3, got {expected_weight}"

    def test_empty_history_returns_default_tau(self):
        """Test that empty probe history returns default tau values."""
        model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        
        # Ensure history is empty
        model._probe_history.clear()
        
        # Calculate weighted tau for cooling
        cooling_result = model._calculate_weighted_tau(is_cooling=True)
        assert cooling_result == 90.0, f"Expected default cooling tau 90.0, got {cooling_result}"
        
        # Calculate weighted tau for warming
        warming_result = model._calculate_weighted_tau(is_cooling=False)
        assert warming_result == 150.0, f"Expected default warming tau 150.0, got {warming_result}"

    def test_single_probe_returns_its_tau_value(self):
        """Test that a single probe returns its tau value (single probe always returns original value)."""
        model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        
        # Create a single probe with specific confidence
        single_probe = ProbeResult(
            tau_value=120.0,
            confidence=0.8,
            duration=3600,
            fit_quality=0.9,
            aborted=False,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Add probe to history
        model._probe_history.append(single_probe)
        
        # Calculate weighted tau - single probe always returns its tau_value
        result = model._calculate_weighted_tau(is_cooling=True)
        
        # Single probe: (tau * weight) / weight = tau (weight cancels out)
        assert abs(result - 120.0) < 0.01, f"Expected 120.0, got {result}"
    def test_multiple_probes_weighted_average(self):
        """Test that multiple probes get proper weighted average."""
        model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        
        now = datetime.now(timezone.utc)
        
        # Create probes at different ages
        probes = [
            ProbeResult(100.0, 1.0, 3600, 0.9, False, now),  # Fresh: weight = 1.0
            ProbeResult(110.0, 1.0, 3600, 0.9, False, now - timedelta(days=1)),  # 1 day: weight = 0.98
            ProbeResult(120.0, 1.0, 3600, 0.9, False, now - timedelta(days=2)),  # 2 days: weight = 0.98^2
        ]
        
        # Add probes to history
        for probe in probes:
            model._probe_history.append(probe)
        
        # Calculate expected result manually
        total_weighted_value = 0.0
        total_weight = 0.0
        
        for probe in probes:
            age_days = (now - probe.timestamp).total_seconds() / 86400
            time_weight = DECAY_RATE_PER_DAY ** age_days
            confidence_weight = probe.confidence
            final_weight = time_weight * confidence_weight
            
            total_weighted_value += probe.tau_value * final_weight
            total_weight += final_weight
        
        expected_result = total_weighted_value / total_weight
        
        # Calculate actual result
        result = model._calculate_weighted_tau(is_cooling=True)
        
        assert abs(result - expected_result) < 0.01, f"Expected {expected_result}, got {result}"

    def test_confidence_weighting_applied_correctly(self):
        """Test that confidence weighting is applied correctly."""
        model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        
        now = datetime.now(timezone.utc)
        
        # Create two fresh probes with different confidence levels
        high_conf_probe = ProbeResult(100.0, 1.0, 3600, 0.9, False, now)  # High confidence
        low_conf_probe = ProbeResult(200.0, 0.1, 3600, 0.9, False, now)   # Low confidence
        
        # Add probes to history
        model._probe_history.append(high_conf_probe)
        model._probe_history.append(low_conf_probe)
        
        # Calculate result
        result = model._calculate_weighted_tau(is_cooling=True)
        
        # Expected: (100*1.0 + 200*0.1) / (1.0 + 0.1) = 120/1.1 ≈ 109.09
        expected = (100.0 * 1.0 + 200.0 * 0.1) / (1.0 + 0.1)
        
        assert abs(result - expected) < 0.1, f"Expected ~{expected}, got {result}"

    def test_handles_none_confidence_gracefully(self):
        """Test that probes with None confidence default to 1.0."""
        model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        
        # Create a probe with None confidence
        probe_with_none = ProbeResult(
            tau_value=100.0,
            confidence=None,  # This should default to 1.0 in the calculation
            duration=3600,
            fit_quality=0.9,
            aborted=False,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Add probe to history
        model._probe_history.append(probe_with_none)
        
        # Calculate result - should treat None confidence as 1.0
        result = model._calculate_weighted_tau(is_cooling=True)
        
        # Should be exactly 100.0 since it's fresh with effective confidence 1.0
        assert abs(result - 100.0) < 0.01, f"Expected 100.0, got {result}"