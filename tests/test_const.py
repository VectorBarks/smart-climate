"""Test module for Smart Climate Control constants.
Tests that required constants are defined with correct values."""

import pytest
from custom_components.smart_climate import const


class TestStartupTimeoutConstants:
    """Test startup timeout related constants."""

    def test_startup_timeout_sec_exists(self):
        """Test that STARTUP_TIMEOUT_SEC constant exists."""
        assert hasattr(const, 'STARTUP_TIMEOUT_SEC')

    def test_startup_timeout_sec_value(self):
        """Test that STARTUP_TIMEOUT_SEC has correct default value."""
        assert const.STARTUP_TIMEOUT_SEC == 90

    def test_startup_timeout_sec_is_reasonable(self):
        """Test that STARTUP_TIMEOUT_SEC is within reasonable range."""
        assert 30 <= const.STARTUP_TIMEOUT_SEC <= 300

    def test_conf_startup_timeout_exists(self):
        """Test that CONF_STARTUP_TIMEOUT constant exists."""
        assert hasattr(const, 'CONF_STARTUP_TIMEOUT')

    def test_conf_startup_timeout_value(self):
        """Test that CONF_STARTUP_TIMEOUT has correct string value."""
        assert const.CONF_STARTUP_TIMEOUT == "startup_timeout"

    def test_conf_startup_timeout_is_string(self):
        """Test that CONF_STARTUP_TIMEOUT is a string."""
        assert isinstance(const.CONF_STARTUP_TIMEOUT, str)


class TestExistingConstants:
    """Test that existing constants are still present and correct."""

    def test_domain_constant_exists(self):
        """Test that DOMAIN constant exists."""
        assert hasattr(const, 'DOMAIN')
        assert const.DOMAIN == "smart_climate"

    def test_platforms_constant_exists(self):
        """Test that PLATFORMS constant exists."""
        assert hasattr(const, 'PLATFORMS')
        assert isinstance(const.PLATFORMS, list)
        assert len(const.PLATFORMS) > 0