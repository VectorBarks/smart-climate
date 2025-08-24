"""Tests for the TooltipProvider class for Advanced Analytics Dashboard."""

import pytest
from custom_components.smart_climate.dashboard.tooltips import TooltipProvider


class TestTooltipProvider:
    """Test cases for TooltipProvider class."""

    def test_tooltip_provider_initialization(self):
        """Test TooltipProvider can be instantiated."""
        provider = TooltipProvider()
        assert provider is not None
        assert hasattr(provider, 'TOOLTIPS')
        assert hasattr(provider, 'get_tooltip')

    def test_all_required_metric_tooltips_exist(self):
        """Test that all required metrics have tooltips defined."""
        provider = TooltipProvider()
        
        # Required metrics from architecture specification
        required_metrics = [
            'tau_value',
            'mae', 
            'thermal_state',
            'confidence',
            'offset',
            'learning_progress',
            'cycle_health',
            'rmse',
            'hysteresis',
            'drift_rate'
        ]
        
        for metric in required_metrics:
            assert metric in provider.TOOLTIPS, f"Missing tooltip for metric: {metric}"
            assert provider.TOOLTIPS[metric], f"Empty tooltip for metric: {metric}"

    def test_tooltip_content_quality(self):
        """Test that tooltip content meets quality requirements."""
        provider = TooltipProvider()
        
        for metric_key, tooltip_text in provider.TOOLTIPS.items():
            # Test maximum length (150 chars recommended)
            assert len(tooltip_text) <= 150, f"Tooltip for '{metric_key}' too long: {len(tooltip_text)} chars"
            
            # Test minimum length (should be meaningful)
            assert len(tooltip_text) >= 10, f"Tooltip for '{metric_key}' too short: {len(tooltip_text)} chars"
            
            # Test that tooltip is a string
            assert isinstance(tooltip_text, str), f"Tooltip for '{metric_key}' must be a string"
            
            # Test that tooltip doesn't start/end with whitespace
            assert tooltip_text == tooltip_text.strip(), f"Tooltip for '{metric_key}' has leading/trailing whitespace"

    def test_tooltip_technical_explanations(self):
        """Test that tooltips provide technical but understandable explanations."""
        provider = TooltipProvider()
        
        # Test specific tooltips contain expected technical terms
        tau_tooltip = provider.TOOLTIPS['tau_value']
        assert 'time constant' in tau_tooltip.lower(), "Tau tooltip should explain time constant"
        assert 'temperature changes' in tau_tooltip.lower(), "Tau tooltip should mention temperature changes"
        
        mae_tooltip = provider.TOOLTIPS['mae']
        assert 'error' in mae_tooltip.lower(), "MAE tooltip should explain error"
        assert '°c' in mae_tooltip.lower(), "MAE tooltip should mention temperature units"
        
        confidence_tooltip = provider.TOOLTIPS['confidence']
        assert 'confidence' in confidence_tooltip.lower(), "Confidence tooltip should explain confidence"
        assert '%' in confidence_tooltip or 'percent' in confidence_tooltip.lower(), "Confidence tooltip should mention percentage"

    def test_get_tooltip_valid_keys(self):
        """Test get_tooltip method returns correct text for valid keys."""
        provider = TooltipProvider()
        
        # Test all defined tooltips
        for metric_key, expected_tooltip in provider.TOOLTIPS.items():
            result = provider.get_tooltip(metric_key)
            assert result == expected_tooltip, f"get_tooltip('{metric_key}') returned wrong text"

    def test_get_tooltip_invalid_keys(self):
        """Test get_tooltip method returns empty string for invalid keys."""
        provider = TooltipProvider()
        
        invalid_keys = [
            'nonexistent_metric',
            'invalid_key',
            'unknown_metric',
            '',
            None,
            123
        ]
        
        for invalid_key in invalid_keys:
            result = provider.get_tooltip(invalid_key)
            assert result == "", f"get_tooltip('{invalid_key}') should return empty string"

    def test_get_tooltip_method_signature(self):
        """Test get_tooltip method has correct signature."""
        provider = TooltipProvider()
        
        # Should accept string parameter
        result = provider.get_tooltip('tau_value')
        assert isinstance(result, str)
        
        # Should handle edge cases gracefully
        assert provider.get_tooltip(None) == ""
        assert provider.get_tooltip('') == ""

    def test_tooltip_constants_immutable(self):
        """Test that TOOLTIPS dictionary is not modified accidentally."""
        provider = TooltipProvider()
        
        # Get original tooltips
        original_tooltips = dict(provider.TOOLTIPS)
        
        # Try to access tooltips
        provider.get_tooltip('tau_value')
        provider.get_tooltip('invalid_key')
        
        # Verify TOOLTIPS unchanged
        assert provider.TOOLTIPS == original_tooltips, "TOOLTIPS dictionary should remain unchanged"

    def test_tooltip_keys_consistency(self):
        """Test that tooltip keys are consistent with expected naming."""
        provider = TooltipProvider()
        
        # All keys should be lowercase with underscores
        for key in provider.TOOLTIPS.keys():
            assert isinstance(key, str), f"Tooltip key '{key}' should be string"
            assert key.islower() or '_' in key, f"Tooltip key '{key}' should be lowercase/underscore format"

    def test_architecture_specification_compliance(self):
        """Test compliance with architecture specification."""
        provider = TooltipProvider()
        
        # Architecture specifies exact tooltip texts - test a few key ones
        expected_tooltips = {
            'tau_value': "Time constant indicating how quickly temperature changes. Lower = faster response",
            'mae': "Mean Absolute Error - average prediction error in °C",
            'thermal_state': "Current operating mode of the thermal management system",
            'confidence': "Statistical confidence in the current prediction (0-100%)",
            'offset': "Temperature adjustment applied to achieve comfort"
        }
        
        for key, expected_text in expected_tooltips.items():
            actual_text = provider.TOOLTIPS[key]
            assert actual_text == expected_text, f"Tooltip for '{key}' doesn't match architecture specification"

    def test_tooltip_provider_coverage(self):
        """Test that TooltipProvider covers all expected use cases."""
        provider = TooltipProvider()
        
        # Should have exactly 10 tooltips as per architecture
        assert len(provider.TOOLTIPS) == 10, f"Expected 10 tooltips, found {len(provider.TOOLTIPS)}"
        
        # Should cover all major metric categories
        categories = {
            'thermal': ['tau_value', 'thermal_state', 'drift_rate'],
            'learning': ['confidence', 'learning_progress'],
            'performance': ['mae', 'rmse'],
            'system': ['cycle_health', 'offset', 'hysteresis']
        }
        
        for category, metrics in categories.items():
            for metric in metrics:
                assert metric in provider.TOOLTIPS, f"Missing {category} metric: {metric}"

    def test_tooltip_no_jargon_without_explanation(self):
        """Test tooltips explain technical terms appropriately."""
        provider = TooltipProvider()
        
        # Terms that should be explained if used
        technical_terms_that_need_explanation = {
            'mae': ['mean absolute error', 'error'],
            'rmse': ['root mean square error', 'error'],
            'tau': ['time constant'],
            'hysteresis': ['temperature difference', 'difference']
        }
        
        for metric_key, tooltip_text in provider.TOOLTIPS.items():
            tooltip_lower = tooltip_text.lower()
            
            # Check if tooltip uses technical terms and explains them
            if metric_key in technical_terms_that_need_explanation:
                required_explanations = technical_terms_that_need_explanation[metric_key]
                has_explanation = any(explanation in tooltip_lower for explanation in required_explanations)
                assert has_explanation, f"Tooltip for '{metric_key}' uses technical term without explanation"