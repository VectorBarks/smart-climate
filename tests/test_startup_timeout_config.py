"""Test startup timeout configuration functionality."""
import pytest
from custom_components.smart_climate.const import (
    CONF_STARTUP_TIMEOUT,
    STARTUP_TIMEOUT_SEC,
)


class TestStartupTimeoutConfig:
    """Test startup timeout configuration in config flow."""

    def test_startup_timeout_default_value(self):
        """Test startup timeout has correct default value."""
        assert STARTUP_TIMEOUT_SEC == 90  # 90 seconds

    def test_startup_timeout_constant_exists(self):
        """Test startup timeout constant exists."""
        assert CONF_STARTUP_TIMEOUT == "startup_timeout"

    def test_startup_timeout_validation_range(self):
        """Test startup timeout validation range."""
        # Range should be 30-300 seconds according to architecture
        assert 30 <= STARTUP_TIMEOUT_SEC <= 300

    def test_startup_timeout_import_in_config_flow(self):
        """Test that startup timeout constants are importable in config flow."""
        from custom_components.smart_climate.config_flow import SmartClimateOptionsFlow
        # If import succeeds without error, the constants are properly imported
        assert SmartClimateOptionsFlow is not None