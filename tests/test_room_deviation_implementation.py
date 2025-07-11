"""Simple test to verify room temperature deviation implementation."""

import pytest
from custom_components.smart_climate.const import TEMP_DEVIATION_THRESHOLD
from custom_components.smart_climate.climate import OFFSET_UPDATE_THRESHOLD


def test_temp_deviation_threshold_exists():
    """Test that TEMP_DEVIATION_THRESHOLD constant exists and has correct value."""
    assert TEMP_DEVIATION_THRESHOLD == 0.5


def test_offset_update_threshold_unchanged():
    """Test that existing OFFSET_UPDATE_THRESHOLD is unchanged."""
    assert OFFSET_UPDATE_THRESHOLD == 0.3


def test_threshold_values_are_different():
    """Test that the two thresholds have different values as designed."""
    assert TEMP_DEVIATION_THRESHOLD != OFFSET_UPDATE_THRESHOLD
    assert TEMP_DEVIATION_THRESHOLD > OFFSET_UPDATE_THRESHOLD