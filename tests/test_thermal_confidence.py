"""ABOUTME: Test suite for thermal model confidence calculation using statistical threshold.
Tests the new statistical confidence formula: avg_confidence * min(count/30, 1.0)"""

import pytest
from datetime import datetime, timezone, timedelta
from custom_components.smart_climate.thermal_model import PassiveThermalModel
from custom_components.smart_climate.thermal_models import ProbeResult
from custom_components.smart_climate.const import CONFIDENCE_REQUIRED_SAMPLES


class TestThermalConfidence:
    """Test thermal model confidence calculation with statistical threshold."""

    def setup_method(self):
        """Set up thermal model for each test."""
        self.thermal_model = PassiveThermalModel()

    def create_probe_result(self, confidence: float, days_ago: int = 0) -> ProbeResult:
        """Create a ProbeResult with specified confidence and age."""
        timestamp = datetime.now(timezone.utc) - timedelta(days=days_ago)
        return ProbeResult(
            tau_value=120.0,
            confidence=confidence,
            duration=3600,
            fit_quality=0.9,
            aborted=False,
            timestamp=timestamp
        )

    def test_zero_probes_returns_zero_confidence(self):
        """Test that zero probes returns 0% confidence."""
        confidence = self.thermal_model.get_confidence()
        assert confidence == 0.0

    def test_single_probe_returns_low_confidence(self):
        """Test that 1 probe returns low confidence (<10%)."""
        # Single probe with 80% confidence should be scaled by 1/30
        probe = self.create_probe_result(confidence=0.8)
        self.thermal_model._probe_history.append(probe)
        
        confidence = self.thermal_model.get_confidence()
        expected = 0.8 * (1 / CONFIDENCE_REQUIRED_SAMPLES)  # 0.8 * (1/30) ≈ 0.027
        assert abs(confidence - expected) < 0.001
        assert confidence < 0.1  # Less than 10%

    def test_fifteen_probes_returns_fifty_percent_scaling(self):
        """Test that 15 probes returns ~50% of average confidence."""
        # 15 probes with average 80% confidence
        for _ in range(15):
            probe = self.create_probe_result(confidence=0.8)
            self.thermal_model._probe_history.append(probe)
        
        confidence = self.thermal_model.get_confidence()
        expected = 0.8 * (15 / CONFIDENCE_REQUIRED_SAMPLES)  # 0.8 * 0.5 = 0.4
        assert abs(confidence - expected) < 0.001

    def test_thirty_probes_returns_full_average_confidence(self):
        """Test that 30 probes returns scaled confidence based on average."""
        # 30 probes with average 80% confidence should get full scaling
        for _ in range(30):
            probe = self.create_probe_result(confidence=0.8)
            self.thermal_model._probe_history.append(probe)
        
        confidence = self.thermal_model.get_confidence()
        expected = 0.8 * min(30 / CONFIDENCE_REQUIRED_SAMPLES, 1.0)  # 0.8 * 1.0 = 0.8
        assert abs(confidence - expected) < 0.001

    def test_seventy_five_probes_high_quality_returns_high_confidence(self):
        """Test that 75 probes with high quality returns >90% confidence."""
        # 75 high-quality probes with 95% confidence
        for _ in range(75):
            probe = self.create_probe_result(confidence=0.95)
            self.thermal_model._probe_history.append(probe)
        
        confidence = self.thermal_model.get_confidence()
        expected = 0.95 * min(75 / CONFIDENCE_REQUIRED_SAMPLES, 1.0)  # 0.95 * 1.0 = 0.95
        assert abs(confidence - expected) < 0.001
        assert confidence > 0.9  # Greater than 90%

    def test_low_quality_probes_reduce_confidence(self):
        """Test that low quality probes reduce overall confidence."""
        # 30 low-quality probes with 20% confidence
        for _ in range(30):
            probe = self.create_probe_result(confidence=0.2)
            self.thermal_model._probe_history.append(probe)
        
        confidence = self.thermal_model.get_confidence()
        expected = 0.2 * min(30 / CONFIDENCE_REQUIRED_SAMPLES, 1.0)  # 0.2 * 1.0 = 0.2
        assert abs(confidence - expected) < 0.001
        assert confidence < 0.3  # Significantly reduced due to low quality

    def test_statistical_formula_exact_calculation(self):
        """Test exact formula: avg_confidence * min(count/30, 1.0)."""
        # Test various probe counts with mixed confidence levels
        test_cases = [
            (5, [0.6, 0.8, 0.7, 0.9, 0.5]),   # 5 probes, avg=0.7
            (10, [0.8] * 10),                  # 10 probes, avg=0.8
            (40, [0.9] * 40),                  # 40 probes, avg=0.9 (should cap at 1.0 scaling)
        ]
        
        for count, confidences in test_cases:
            # Clear history and add new probes
            self.thermal_model._probe_history.clear()
            for conf in confidences:
                probe = self.create_probe_result(confidence=conf)
                self.thermal_model._probe_history.append(probe)
            
            confidence = self.thermal_model.get_confidence()
            avg_confidence = sum(confidences) / len(confidences)
            sample_factor = min(count / CONFIDENCE_REQUIRED_SAMPLES, 1.0)
            expected = avg_confidence * sample_factor
            
            assert abs(confidence - expected) < 0.001, f"Failed for {count} probes"

    def test_confidence_never_exceeds_100_percent(self):
        """Test that confidence never exceeds 100%."""
        # Edge case: perfect probes beyond threshold
        for _ in range(50):
            probe = self.create_probe_result(confidence=1.0)
            self.thermal_model._probe_history.append(probe)
        
        confidence = self.thermal_model.get_confidence()
        assert confidence <= 1.0
        assert confidence == 1.0  # Should be exactly 1.0 for perfect probes

    def test_confidence_never_goes_negative(self):
        """Test that confidence never goes negative."""
        # Edge case: zero confidence probes
        for _ in range(10):
            probe = self.create_probe_result(confidence=0.0)
            self.thermal_model._probe_history.append(probe)
        
        confidence = self.thermal_model.get_confidence()
        assert confidence >= 0.0
        assert confidence == 0.0  # Should be exactly 0.0 for zero confidence probes

    def test_mixed_probe_confidence_levels(self):
        """Test calculation with mixed confidence levels."""
        # Mix of high and low confidence probes
        confidences = [0.9, 0.1, 0.8, 0.3, 0.7, 0.2, 0.9, 0.4]  # avg = 0.5375
        for conf in confidences:
            probe = self.create_probe_result(confidence=conf)
            self.thermal_model._probe_history.append(probe)
        
        confidence = self.thermal_model.get_confidence()
        avg_confidence = sum(confidences) / len(confidences)
        sample_factor = min(len(confidences) / CONFIDENCE_REQUIRED_SAMPLES, 1.0)
        expected = avg_confidence * sample_factor
        
        assert abs(confidence - expected) < 0.001

    def test_none_confidence_probes_handled_gracefully(self):
        """Test that probes with None confidence are handled correctly."""
        # Create probes with None confidence (edge case)
        probe_with_none = ProbeResult(
            tau_value=120.0,
            confidence=None,  # This should be handled
            duration=3600,
            fit_quality=0.9,
            aborted=False,
            timestamp=datetime.now(timezone.utc)
        )
        self.thermal_model._probe_history.append(probe_with_none)
        
        # Should not crash and should return 0.0 for no valid probes
        confidence = self.thermal_model.get_confidence()
        assert confidence == 0.0

    def test_confidence_with_required_samples_constant(self):
        """Test that confidence calculation uses CONFIDENCE_REQUIRED_SAMPLES constant."""
        # Verify the constant is being used correctly
        assert CONFIDENCE_REQUIRED_SAMPLES == 30
        
        # Test at exactly the threshold
        for _ in range(CONFIDENCE_REQUIRED_SAMPLES):
            probe = self.create_probe_result(confidence=0.6)
            self.thermal_model._probe_history.append(probe)
        
        confidence = self.thermal_model.get_confidence()
        # At exactly 30 samples, should get full scaling
        expected = 0.6 * 1.0
        assert abs(confidence - expected) < 0.001

    def test_confidence_progression_is_smooth(self):
        """Test that confidence progression is smooth as probes are added."""
        confidences = []
        
        # Add probes one by one and track confidence progression
        for i in range(1, 50):
            probe = self.create_probe_result(confidence=0.8)
            self.thermal_model._probe_history.append(probe)
            confidences.append(self.thermal_model.get_confidence())
        
        # Confidence should increase monotonically until threshold
        for i in range(1, min(30, len(confidences))):
            assert confidences[i] >= confidences[i-1], f"Confidence decreased at probe {i+1}"
        
        # After threshold, confidence should remain stable
        if len(confidences) > 30:
            for i in range(30, len(confidences)):
                assert abs(confidences[i] - 0.8) < 0.001, f"Confidence not stable after threshold at probe {i+1}"