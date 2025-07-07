"""ABOUTME: Integration tests for YAML configuration setup.
Tests the integration of YAML config with the component initialization."""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from custom_components.smart_climate import async_setup
from custom_components.smart_climate.const import DOMAIN


class TestYAMLIntegration:
    """Test YAML configuration integration with component setup."""

    @pytest.mark.asyncio
    async def test_setup_with_yaml_config(self):
        """Test component setup with YAML configuration."""
        # Mock HomeAssistant instance
        hass = Mock()
        hass.data = {}
        
        # YAML configuration
        config = {
            DOMAIN: {
                "climate_entity": "climate.existing_ac",
                "room_sensor": "sensor.room_temperature",
                "max_offset": 3.0,
                "ml_enabled": True,
            }
        }
        
        # Set up the integration
        result = await async_setup(hass, config)
        
        # Verify setup succeeded
        assert result is True
        
        # Verify domain was initialized
        assert DOMAIN in hass.data
        
        # Verify YAML config was stored
        assert "yaml_config" in hass.data[DOMAIN]
        assert hass.data[DOMAIN]["yaml_config"] == config[DOMAIN]

    @pytest.mark.asyncio
    async def test_setup_without_yaml_config(self):
        """Test component setup without YAML configuration."""
        # Mock HomeAssistant instance
        hass = Mock()
        hass.data = {}
        
        # Empty configuration
        config = {}
        
        # Set up the integration
        result = await async_setup(hass, config)
        
        # Verify setup succeeded
        assert result is True
        
        # Verify domain was initialized
        assert DOMAIN in hass.data
        
        # Verify no YAML config was stored
        assert "yaml_config" not in hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_setup_with_multiple_instances_yaml(self):
        """Test that YAML configuration supports multiple instances."""
        # Mock HomeAssistant instance
        hass = Mock()
        hass.data = {}
        
        # YAML configuration with multiple instances
        # Note: In real HA, multiple instances would be in a list under the domain
        config = {
            DOMAIN: [
                {
                    "climate_entity": "climate.living_room_ac",
                    "room_sensor": "sensor.living_room_temperature",
                    "name": "Living Room Smart Climate",
                },
                {
                    "climate_entity": "climate.bedroom_ac", 
                    "room_sensor": "sensor.bedroom_temperature",
                    "name": "Bedroom Smart Climate",
                    "max_offset": 2.0,
                }
            ]
        }
        
        # Set up the integration
        result = await async_setup(hass, config)
        
        # Verify setup succeeded
        assert result is True
        
        # Verify domain was initialized
        assert DOMAIN in hass.data
        
        # Verify YAML config was stored
        assert "yaml_config" in hass.data[DOMAIN]
        assert hass.data[DOMAIN]["yaml_config"] == config[DOMAIN]
        
        # Verify multiple instances are present
        yaml_config = hass.data[DOMAIN]["yaml_config"]
        assert isinstance(yaml_config, list)
        assert len(yaml_config) == 2
        assert yaml_config[0]["climate_entity"] == "climate.living_room_ac"
        assert yaml_config[1]["climate_entity"] == "climate.bedroom_ac"

    @pytest.mark.asyncio
    async def test_setup_preserves_existing_data(self):
        """Test that setup preserves existing domain data."""
        # Mock HomeAssistant instance
        hass = Mock()
        hass.data = {
            DOMAIN: {
                "existing_key": "existing_value"
            }
        }
        
        # YAML configuration
        config = {
            DOMAIN: {
                "climate_entity": "climate.existing_ac",
                "room_sensor": "sensor.room_temperature",
            }
        }
        
        # Set up the integration
        result = await async_setup(hass, config)
        
        # Verify setup succeeded
        assert result is True
        
        # Verify existing data was preserved
        assert hass.data[DOMAIN]["existing_key"] == "existing_value"
        
        # Verify YAML config was added
        assert "yaml_config" in hass.data[DOMAIN]
        assert hass.data[DOMAIN]["yaml_config"] == config[DOMAIN]


class TestConfigEntryIntegration:
    """Test config entry integration (for UI configuration)."""

    @pytest.mark.asyncio
    async def test_async_setup_entry(self):
        """Test config entry setup."""
        from custom_components.smart_climate import async_setup_entry
        
        # Mock HomeAssistant instance
        hass = Mock()
        hass.data = {}
        hass.config_entries = Mock()
        hass.config_entries.async_forward_entry_setup = AsyncMock(return_value=True)
        
        # Mock config entry
        entry = Mock()
        entry.entry_id = "test_entry_id"
        entry.data = {
            "climate_entity": "climate.test_ac",
            "room_sensor": "sensor.test_room",
        }
        
        # Set up from config entry
        result = await async_setup_entry(hass, entry)
        
        # Verify setup succeeded
        assert result is True
        
        # Verify domain was initialized
        assert DOMAIN in hass.data
        
        # Verify config entry data was stored
        assert entry.entry_id in hass.data[DOMAIN]
        assert hass.data[DOMAIN][entry.entry_id] == entry.data
        
        # Verify platform setup was called
        hass.config_entries.async_forward_entry_setup.assert_called_once_with(
            entry, "climate"
        )

    @pytest.mark.asyncio
    async def test_async_unload_entry(self):
        """Test config entry unload."""
        from custom_components.smart_climate import async_unload_entry
        
        # Mock HomeAssistant instance
        hass = Mock()
        hass.data = {
            DOMAIN: {
                "test_entry_id": {"some": "data"}
            }
        }
        hass.config_entries = Mock()
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        
        # Mock config entry
        entry = Mock()
        entry.entry_id = "test_entry_id"
        
        # Unload the entry
        result = await async_unload_entry(hass, entry)
        
        # Verify unload succeeded
        assert result is True
        
        # Verify config entry data was removed
        assert entry.entry_id not in hass.data[DOMAIN]
        
        # Verify platform unload was called
        hass.config_entries.async_unload_platforms.assert_called_once_with(
            entry, ["climate"]
        )

    @pytest.mark.asyncio
    async def test_async_unload_entry_fails(self):
        """Test config entry unload when platform unload fails."""
        from custom_components.smart_climate import async_unload_entry
        
        # Mock HomeAssistant instance
        hass = Mock()
        hass.data = {
            DOMAIN: {
                "test_entry_id": {"some": "data"}
            }
        }
        hass.config_entries = Mock()
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)
        
        # Mock config entry
        entry = Mock()
        entry.entry_id = "test_entry_id"
        
        # Unload the entry
        result = await async_unload_entry(hass, entry)
        
        # Verify unload failed
        assert result is False
        
        # Verify config entry data was NOT removed
        assert entry.entry_id in hass.data[DOMAIN]