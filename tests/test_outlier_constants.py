"""ABOUTME: Tests for outlier detection configuration constants.
Tests that all required outlier detection constants exist with correct values."""

import pytest
from custom_components.smart_climate.const import (
    CONF_OUTLIER_DETECTION_ENABLED,
    CONF_OUTLIER_SENSITIVITY,
    DEFAULT_OUTLIER_SENSITIVITY,
    DEFAULT_OUTLIER_HISTORY_SIZE,
    DEFAULT_OUTLIER_MIN_SAMPLES,
    DEFAULT_OUTLIER_TEMP_BOUNDS,
    DEFAULT_OUTLIER_POWER_BOUNDS,
)


class TestOutlierConstants:
    """Test class for outlier detection constants."""

    def test_conf_outlier_detection_enabled_exists(self):
        """Test that CONF_OUTLIER_DETECTION_ENABLED constant exists with correct value."""
        assert CONF_OUTLIER_DETECTION_ENABLED == "outlier_detection_enabled"

    def test_conf_outlier_sensitivity_exists(self):
        """Test that CONF_OUTLIER_SENSITIVITY constant exists with correct value."""
        assert CONF_OUTLIER_SENSITIVITY == "outlier_sensitivity"

    def test_default_outlier_sensitivity_exists(self):
        """Test that DEFAULT_OUTLIER_SENSITIVITY constant exists with correct value."""
        assert DEFAULT_OUTLIER_SENSITIVITY == 2.5

    def test_default_outlier_history_size_exists(self):
        """Test that DEFAULT_OUTLIER_HISTORY_SIZE constant exists with correct value."""
        assert DEFAULT_OUTLIER_HISTORY_SIZE == 100

    def test_default_outlier_min_samples_exists(self):
        """Test that DEFAULT_OUTLIER_MIN_SAMPLES constant exists with correct value."""
        assert DEFAULT_OUTLIER_MIN_SAMPLES == 10

    def test_default_outlier_temp_bounds_exists(self):
        """Test that DEFAULT_OUTLIER_TEMP_BOUNDS constant exists with correct value."""
        assert DEFAULT_OUTLIER_TEMP_BOUNDS == (0, 40)

    def test_default_outlier_power_bounds_exists(self):
        """Test that DEFAULT_OUTLIER_POWER_BOUNDS constant exists with correct value."""
        assert DEFAULT_OUTLIER_POWER_BOUNDS == (0, 5000)