"""ABOUTME: Simple verification test for outlier detection configuration constants.
Tests that outlier detection constants are properly defined and available."""

import pytest
from custom_components.smart_climate.const import (
    CONF_OUTLIER_DETECTION_ENABLED,
    CONF_OUTLIER_SENSITIVITY,
    DEFAULT_OUTLIER_DETECTION_ENABLED,
    DEFAULT_OUTLIER_SENSITIVITY,
)


class TestOutlierConstants:
    """Test outlier detection constants are properly defined."""

    def test_outlier_detection_enabled_constant(self):
        """Test outlier detection enabled constant is defined."""
        assert CONF_OUTLIER_DETECTION_ENABLED == "outlier_detection_enabled"
        assert isinstance(CONF_OUTLIER_DETECTION_ENABLED, str)
        assert len(CONF_OUTLIER_DETECTION_ENABLED) > 0

    def test_outlier_sensitivity_constant(self):
        """Test outlier sensitivity constant is defined."""
        assert CONF_OUTLIER_SENSITIVITY == "outlier_sensitivity"
        assert isinstance(CONF_OUTLIER_SENSITIVITY, str)
        assert len(CONF_OUTLIER_SENSITIVITY) > 0

    def test_default_outlier_detection_enabled(self):
        """Test default outlier detection enabled value."""
        assert DEFAULT_OUTLIER_DETECTION_ENABLED is True
        assert isinstance(DEFAULT_OUTLIER_DETECTION_ENABLED, bool)

    def test_default_outlier_sensitivity(self):
        """Test default outlier sensitivity value."""
        assert DEFAULT_OUTLIER_SENSITIVITY == 2.5
        assert isinstance(DEFAULT_OUTLIER_SENSITIVITY, (int, float))
        assert 1.0 <= DEFAULT_OUTLIER_SENSITIVITY <= 5.0

    def test_config_flow_imports_constants(self):
        """Test that config flow file imports outlier constants."""
        import importlib.util
        import sys
        
        # Load config_flow.py as a module
        spec = importlib.util.spec_from_file_location(
            "config_flow_test",
            "/home/vector/git/vector-climate/custom_components/smart_climate/config_flow.py"
        )
        
        # Read the file content directly to verify imports
        with open("/home/vector/git/vector-climate/custom_components/smart_climate/config_flow.py", "r") as f:
            content = f.read()
            
        # Verify the constants are imported
        assert "CONF_OUTLIER_DETECTION_ENABLED" in content
        assert "CONF_OUTLIER_SENSITIVITY" in content
        assert "DEFAULT_OUTLIER_DETECTION_ENABLED" in content
        assert "DEFAULT_OUTLIER_SENSITIVITY" in content

    def test_config_flow_uses_constants_in_schema(self):
        """Test that config flow uses outlier constants in options schema."""
        with open("/home/vector/git/vector-climate/custom_components/smart_climate/config_flow.py", "r") as f:
            content = f.read()
            
        # Verify the constants are used in the schema
        assert "vol.Optional(" in content
        assert "CONF_OUTLIER_DETECTION_ENABLED," in content
        assert "CONF_OUTLIER_SENSITIVITY," in content
        
        # Verify proper default value handling
        assert "current_options.get(CONF_OUTLIER_DETECTION_ENABLED" in content
        assert "current_options.get(CONF_OUTLIER_SENSITIVITY" in content
        assert "DEFAULT_OUTLIER_DETECTION_ENABLED)" in content
        assert "DEFAULT_OUTLIER_SENSITIVITY)" in content
        
        # Verify validation configuration
        assert "selector.BooleanSelector()" in content
        assert "selector.NumberSelector(" in content
        assert "min=1.0" in content
        assert "max=5.0" in content
        
    def test_architecture_compliance(self):
        """Test implementation matches c_architecture.md Section 9.5 requirements."""
        # According to architecture:
        # - outlier_detection_enabled: bool (default=True)
        # - outlier_sensitivity: float (default=2.5, range=1.0-5.0)
        
        # Test enabled field
        assert DEFAULT_OUTLIER_DETECTION_ENABLED is True
        
        # Test sensitivity field  
        assert DEFAULT_OUTLIER_SENSITIVITY == 2.5
        assert 1.0 <= DEFAULT_OUTLIER_SENSITIVITY <= 5.0
        
        # Test that options are saved to config_entry.options
        # (verified by reading the async_step_init implementation)
        with open("/home/vector/git/vector-climate/custom_components/smart_climate/config_flow.py", "r") as f:
            content = f.read()
            
        # Should save options via async_create_entry
        assert "async_create_entry" in content
        assert "data=user_input" in content
        
        # Should trigger integration reload (done by async_create_entry)
        assert "self.async_create_entry(title=\"\", data=user_input)" in content