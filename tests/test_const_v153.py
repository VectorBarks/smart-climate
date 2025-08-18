"""
Test suite for Smart Climate v1.5.3 thermal model constants.

Tests validate that all required constants for the enhanced thermal model
are properly defined with correct types and values.
"""

import pytest
from custom_components.smart_climate.const import (
    # Expected v1.5.3 thermal model constants
    MAX_PROBE_HISTORY_SIZE,
    CONFIDENCE_REQUIRED_SAMPLES,
    DECAY_RATE_PER_DAY,
    DECAY_HALF_LIFE_DAYS,
    TAU_MIN_CLAMP,
    TAU_MAX_CLAMP,
    MIN_SAMPLES_FOR_REGRESSION,
    MIN_R2_FOR_MODEL_TRUST,
)


class TestThermalModelV153Constants:
    """Test thermal model v1.5.3 configuration constants."""

    def test_max_probe_history_size(self):
        """Test MAX_PROBE_HISTORY_SIZE constant."""
        assert MAX_PROBE_HISTORY_SIZE == 75
        assert isinstance(MAX_PROBE_HISTORY_SIZE, int)
        assert MAX_PROBE_HISTORY_SIZE > 0

    def test_confidence_required_samples(self):
        """Test CONFIDENCE_REQUIRED_SAMPLES constant."""
        assert CONFIDENCE_REQUIRED_SAMPLES == 30
        assert isinstance(CONFIDENCE_REQUIRED_SAMPLES, int)
        assert CONFIDENCE_REQUIRED_SAMPLES > 0
        # Should be less than max history for meaningful confidence calculation
        assert CONFIDENCE_REQUIRED_SAMPLES <= MAX_PROBE_HISTORY_SIZE

    def test_decay_rate_per_day(self):
        """Test DECAY_RATE_PER_DAY constant."""
        assert DECAY_RATE_PER_DAY == 0.98
        assert isinstance(DECAY_RATE_PER_DAY, float)
        assert 0 < DECAY_RATE_PER_DAY < 1  # Must be valid decay rate

    def test_decay_half_life_days(self):
        """Test DECAY_HALF_LIFE_DAYS constant."""
        # Half-life should be approximately -ln(2)/ln(0.98) ≈ 34.3
        expected_half_life = 34.3
        assert abs(DECAY_HALF_LIFE_DAYS - expected_half_life) < 0.1
        assert isinstance(DECAY_HALF_LIFE_DAYS, float)
        assert DECAY_HALF_LIFE_DAYS > 0

    def test_tau_clamps(self):
        """Test TAU_MIN_CLAMP and TAU_MAX_CLAMP constants."""
        assert TAU_MIN_CLAMP == 30.0
        assert TAU_MAX_CLAMP == 300.0
        assert isinstance(TAU_MIN_CLAMP, float)
        assert isinstance(TAU_MAX_CLAMP, float)
        assert TAU_MIN_CLAMP < TAU_MAX_CLAMP
        assert TAU_MIN_CLAMP > 0
        assert TAU_MAX_CLAMP > 0

    def test_regression_constants(self):
        """Test regression model constants."""
        assert MIN_SAMPLES_FOR_REGRESSION == 20
        assert MIN_R2_FOR_MODEL_TRUST == 0.4
        assert isinstance(MIN_SAMPLES_FOR_REGRESSION, int)
        assert isinstance(MIN_R2_FOR_MODEL_TRUST, float)
        assert MIN_SAMPLES_FOR_REGRESSION > 0
        assert 0 <= MIN_R2_FOR_MODEL_TRUST <= 1

    def test_constants_relationships(self):
        """Test logical relationships between constants."""
        # Regression minimum should be reasonable fraction of max history
        assert MIN_SAMPLES_FOR_REGRESSION <= MAX_PROBE_HISTORY_SIZE / 2
        
        # Confidence required should be reasonable for statistical validity
        assert CONFIDENCE_REQUIRED_SAMPLES >= 10  # Minimum for basic statistics
        assert CONFIDENCE_REQUIRED_SAMPLES <= MAX_PROBE_HISTORY_SIZE

    def test_constants_importable(self):
        """Test that all constants can be imported successfully."""
        # This test passes if the imports at the top work without errors
        constants = [
            MAX_PROBE_HISTORY_SIZE,
            CONFIDENCE_REQUIRED_SAMPLES,
            DECAY_RATE_PER_DAY,
            DECAY_HALF_LIFE_DAYS,
            TAU_MIN_CLAMP,
            TAU_MAX_CLAMP,
            MIN_SAMPLES_FOR_REGRESSION,
            MIN_R2_FOR_MODEL_TRUST,
        ]
        
        # Verify all constants are defined (not None)
        for constant in constants:
            assert constant is not None

    def test_physical_constraints(self):
        """Test that constants satisfy physical constraints."""
        # Tau clamps should be reasonable for HVAC systems
        assert TAU_MIN_CLAMP >= 10.0  # At least 10 minutes
        assert TAU_MAX_CLAMP <= 600.0  # At most 10 hours
        
        # History size should be reasonable for seasonal adaptation
        assert MAX_PROBE_HISTORY_SIZE >= 50  # Enough for seasonal trends
        assert MAX_PROBE_HISTORY_SIZE <= 200  # Not excessive memory usage
        
        # Decay rate should provide reasonable weighting
        assert DECAY_RATE_PER_DAY >= 0.9  # Not too aggressive
        assert DECAY_RATE_PER_DAY <= 0.99  # Still provides time weighting

    def test_statistical_validity(self):
        """Test constants provide statistical validity."""
        # Confidence required should follow Central Limit Theorem guidelines
        assert CONFIDENCE_REQUIRED_SAMPLES >= 20  # Basic CLT requirement
        
        # R² threshold should be meaningful
        assert MIN_R2_FOR_MODEL_TRUST >= 0.3  # Minimum meaningful correlation
        assert MIN_R2_FOR_MODEL_TRUST <= 0.8  # Not too strict
        
        # Regression minimum should provide sufficient data
        assert MIN_SAMPLES_FOR_REGRESSION >= 15  # Minimum for regression