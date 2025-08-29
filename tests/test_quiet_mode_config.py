"""
Tests for Quiet Mode configuration options.
Tests the ability to configure quiet mode through config flow.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from custom_components.smart_climate.config_flow import SmartClimateOptionsFlow
from custom_components.smart_climate.const import (
    DOMAIN,
    CONF_QUIET_MODE_ENABLED,
    DEFAULT_QUIET_MODE_ENABLED,
)


@pytest.fixture
def hass():
    """Create a mock Home Assistant instance."""
    mock_hass = Mock()
    mock_hass.states = Mock()
    mock_hass.states.async_all = Mock(return_value=[])
    mock_hass.states.async_entity_ids = Mock(return_value=[])
    return mock_hass


@pytest.fixture  
def mock_config_entry():
    """Create a mock config entry."""
    config_entry = Mock()
    config_entry.data = {}
    config_entry.options = {}
    return config_entry


class TestQuietModeConfig:
    """Test quiet mode configuration options."""

    def test_quiet_mode_default_enabled(self):
        """Test that quiet mode is enabled by default."""
        assert DEFAULT_QUIET_MODE_ENABLED is True

    @pytest.mark.asyncio
    async def test_config_flow_shows_quiet_mode_option(self, hass, mock_config_entry):
        """Test that quiet mode option appears in config flow."""
        # Create options flow instance using the same pattern as other tests
        options_flow = SmartClimateOptionsFlow()
        options_flow.hass = hass
        options_flow.config_entry = mock_config_entry
        
        # Mock async methods that are called internally
        from unittest.mock import AsyncMock
        options_flow._get_humidity_sensors = AsyncMock(return_value=[])
        
        result = await options_flow.async_step_init()
        
        assert result["type"] == "form"
        assert result["step_id"] == "init"
        
        # Check that schema includes quiet mode field
        schema_keys = [str(key) for key in result["data_schema"].schema.keys()]
        
        # Should include quiet mode enabled field
        assert any(CONF_QUIET_MODE_ENABLED in key for key in schema_keys)

    @pytest.mark.asyncio
    async def test_quiet_mode_setting_persists(self, hass, mock_config_entry):
        """Test that quiet mode setting saves and loads correctly."""
        # Create options flow instance 
        options_flow = SmartClimateOptionsFlow()
        options_flow.hass = hass
        options_flow.config_entry = mock_config_entry
        
        # Mock async methods that are called internally
        from unittest.mock import AsyncMock
        options_flow._get_humidity_sensors = AsyncMock(return_value=[])
        
        # Test saving quiet mode disabled
        user_input = {
            CONF_QUIET_MODE_ENABLED: False
        }
        
        result = await options_flow.async_step_init(user_input)
        
        assert result["type"] == "create_entry"
        assert result["data"][CONF_QUIET_MODE_ENABLED] is False
        
        # Test saving quiet mode enabled
        user_input[CONF_QUIET_MODE_ENABLED] = True
        
        result = await options_flow.async_step_init(user_input)
        
        assert result["type"] == "create_entry"
        assert result["data"][CONF_QUIET_MODE_ENABLED] is True

    @pytest.mark.asyncio 
    async def test_existing_config_gets_default(self, hass, mock_config_entry):
        """Test that existing configurations without quiet mode get the default value."""
        # Simulate existing config entry without quiet mode setting
        mock_config_entry.options = {
            # Other options would be here, but no CONF_QUIET_MODE_ENABLED
        }
        
        # Create options flow instance
        options_flow = SmartClimateOptionsFlow()
        options_flow.hass = hass
        options_flow.config_entry = mock_config_entry
        
        # Mock async methods that are called internally
        from unittest.mock import AsyncMock
        options_flow._get_humidity_sensors = AsyncMock(return_value=[])
        
        result = await options_flow.async_step_init()
        
        assert result["type"] == "form"
        
        # Check that quiet mode field exists in schema with correct default
        schema = result["data_schema"].schema
        
        # Find the quiet mode option and verify its default value
        for key, selector in schema.items():
            if CONF_QUIET_MODE_ENABLED in str(key):
                # Check that default matches our expectation
                assert hasattr(key, 'default')
                assert key.default == DEFAULT_QUIET_MODE_ENABLED
                return
        
        # If we get here, the field wasn't found
        assert False, f"{CONF_QUIET_MODE_ENABLED} not found in options schema"