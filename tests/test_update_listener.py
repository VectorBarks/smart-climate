"""Test update_listener function for HACS reload support."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.smart_climate import update_listener


class TestUpdateListener:
    """Test cases for update_listener function."""
    
    def test_update_listener_exists_and_callable(self):
        """Test that update_listener function exists and is callable."""
        # Import should not raise
        from custom_components.smart_climate import update_listener
        
        # Function should be callable
        assert callable(update_listener), "update_listener should be callable"
    
    @pytest.mark.asyncio
    async def test_update_listener_calls_async_reload(self):
        """Test that update_listener calls hass.config_entries.async_reload with correct entry_id."""
        # Create mock HomeAssistant
        hass = Mock()
        hass.config_entries = Mock()
        hass.config_entries.async_reload = AsyncMock()
        
        # Create mock ConfigEntry
        entry = Mock()
        entry.entry_id = "test_entry_123"
        
        # Call update_listener
        await update_listener(hass, entry)
        
        # Verify async_reload was called with correct entry_id
        hass.config_entries.async_reload.assert_called_once_with("test_entry_123")
    
    @pytest.mark.asyncio
    async def test_update_listener_logs_reload_action(self, caplog):
        """Test that update_listener logs the reload action at INFO level."""
        # Create mock HomeAssistant
        hass = Mock()
        hass.config_entries = Mock()
        hass.config_entries.async_reload = AsyncMock()
        
        # Create mock ConfigEntry
        entry = Mock()
        entry.entry_id = "test_entry_456"
        
        # Set logging level to capture INFO
        with caplog.at_level(logging.INFO):
            # Call update_listener
            await update_listener(hass, entry)
        
        # Verify log message was created
        assert any(
            "Reloading Smart Climate integration due to options update" in record.message
            for record in caplog.records
        ), "Expected INFO log message not found"
        
        # Verify log level is INFO
        info_records = [r for r in caplog.records if r.levelno == logging.INFO]
        assert len(info_records) > 0, "No INFO level log records found"