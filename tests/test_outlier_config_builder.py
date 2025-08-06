"""ABOUTME: Tests for outlier detection configuration builder function.
Comprehensive test coverage for _build_outlier_config function."""

import pytest
from custom_components.smart_climate import _build_outlier_config
from custom_components.smart_climate.const import (
    CONF_OUTLIER_DETECTION_ENABLED,
    CONF_OUTLIER_SENSITIVITY,
    DEFAULT_OUTLIER_SENSITIVITY,
    DEFAULT_OUTLIER_HISTORY_SIZE,
    DEFAULT_OUTLIER_MIN_SAMPLES,
    DEFAULT_OUTLIER_TEMP_BOUNDS,
    DEFAULT_OUTLIER_POWER_BOUNDS,
)


class TestBuildOutlierConfig:
    """Test cases for _build_outlier_config function."""

    def test_outlier_detection_disabled_returns_none(self):
        """Test that disabled outlier detection returns None."""
        options = {CONF_OUTLIER_DETECTION_ENABLED: False}
        result = _build_outlier_config(options)
        assert result is None

    def test_outlier_detection_enabled_with_default_sensitivity(self):
        """Test outlier detection enabled with default sensitivity."""
        options = {CONF_OUTLIER_DETECTION_ENABLED: True}
        result = _build_outlier_config(options)
        
        expected = {
            "zscore_threshold": DEFAULT_OUTLIER_SENSITIVITY,
            "history_size": DEFAULT_OUTLIER_HISTORY_SIZE,
            "min_samples_for_stats": DEFAULT_OUTLIER_MIN_SAMPLES,
            "temperature_bounds": DEFAULT_OUTLIER_TEMP_BOUNDS,
            "power_bounds": DEFAULT_OUTLIER_POWER_BOUNDS,
        }
        assert result == expected

    def test_outlier_detection_enabled_with_custom_sensitivity(self):
        """Test outlier detection enabled with custom sensitivity."""
        custom_sensitivity = 3.0
        options = {
            CONF_OUTLIER_DETECTION_ENABLED: True,
            CONF_OUTLIER_SENSITIVITY: custom_sensitivity,
        }
        result = _build_outlier_config(options)
        
        expected = {
            "zscore_threshold": custom_sensitivity,
            "history_size": DEFAULT_OUTLIER_HISTORY_SIZE,
            "min_samples_for_stats": DEFAULT_OUTLIER_MIN_SAMPLES,
            "temperature_bounds": DEFAULT_OUTLIER_TEMP_BOUNDS,
            "power_bounds": DEFAULT_OUTLIER_POWER_BOUNDS,
        }
        assert result == expected

    def test_empty_options_dict_backward_compatibility(self):
        """Test backward compatibility with empty options dict."""
        options = {}
        result = _build_outlier_config(options)
        assert result is None

    def test_none_options_safety_check(self):
        """Test safety check when options dict is None."""
        result = _build_outlier_config(None)
        assert result is None

    def test_missing_enabled_key_returns_none(self):
        """Test that missing outlier_detection_enabled key returns None."""
        options = {CONF_OUTLIER_SENSITIVITY: 2.0}  # sensitivity without enabled
        result = _build_outlier_config(options)
        assert result is None

    def test_outlier_detection_enabled_false_with_sensitivity_returns_none(self):
        """Test that explicitly disabled detection returns None even with sensitivity."""
        options = {
            CONF_OUTLIER_DETECTION_ENABLED: False,
            CONF_OUTLIER_SENSITIVITY: 3.0,
        }
        result = _build_outlier_config(options)
        assert result is None

    def test_config_structure_completeness(self):
        """Test that all required config keys are present."""
        options = {CONF_OUTLIER_DETECTION_ENABLED: True}
        result = _build_outlier_config(options)
        
        required_keys = [
            "zscore_threshold",
            "history_size", 
            "min_samples_for_stats",
            "temperature_bounds",
            "power_bounds",
        ]
        
        assert result is not None
        assert all(key in result for key in required_keys)

    def test_config_value_types(self):
        """Test that config values have correct types."""
        options = {CONF_OUTLIER_DETECTION_ENABLED: True}
        result = _build_outlier_config(options)
        
        assert isinstance(result["zscore_threshold"], float)
        assert isinstance(result["history_size"], int)
        assert isinstance(result["min_samples_for_stats"], int)
        assert isinstance(result["temperature_bounds"], tuple)
        assert isinstance(result["power_bounds"], tuple)

    def test_bounds_tuple_structure(self):
        """Test that bounds are proper tuples with min/max values."""
        options = {CONF_OUTLIER_DETECTION_ENABLED: True}
        result = _build_outlier_config(options)
        
        temp_bounds = result["temperature_bounds"]
        power_bounds = result["power_bounds"]
        
        assert len(temp_bounds) == 2
        assert len(power_bounds) == 2
        assert temp_bounds[0] < temp_bounds[1]  # min < max
        assert power_bounds[0] < power_bounds[1]  # min < max

    def test_edge_case_zero_sensitivity(self):
        """Test edge case with zero sensitivity."""
        options = {
            CONF_OUTLIER_DETECTION_ENABLED: True,
            CONF_OUTLIER_SENSITIVITY: 0.0,
        }
        result = _build_outlier_config(options)
        
        assert result is not None
        assert result["zscore_threshold"] == 0.0

    def test_edge_case_negative_sensitivity(self):
        """Test edge case with negative sensitivity."""
        options = {
            CONF_OUTLIER_DETECTION_ENABLED: True,
            CONF_OUTLIER_SENSITIVITY: -1.0,
        }
        result = _build_outlier_config(options)
        
        assert result is not None
        assert result["zscore_threshold"] == -1.0