"""ABOUTME: Tests for outlier detection configuration in options flow.
Tests UI form includes outlier settings with proper validation and defaults."""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import sys

# Mock homeassistant modules
sys.modules['homeassistant.helpers.selector'] = MagicMock()
sys.modules['homeassistant.helpers.entity_registry'] = MagicMock()
sys.modules['homeassistant.helpers.device_registry'] = MagicMock()

# Mock config_entries and data_entry_flow
mock_config_entries = MagicMock()
mock_config_entries.ConfigFlow = MagicMock()
mock_config_entries.OptionsFlow = MagicMock()
mock_config_entries.ConfigEntry = MagicMock()
sys.modules['homeassistant.config_entries'] = mock_config_entries

# Mock data_entry_flow
mock_data_entry_flow = MagicMock()
mock_data_entry_flow.FlowResultType = MagicMock()
mock_data_entry_flow.FlowResultType.FORM = "form"
mock_data_entry_flow.FlowResultType.CREATE_ENTRY = "create_entry"
mock_data_entry_flow.FlowResult = dict
sys.modules['homeassistant.data_entry_flow'] = mock_data_entry_flow

from custom_components.smart_climate.config_flow import SmartClimateOptionsFlow
from custom_components.smart_climate.const import (
    DOMAIN,
    CONF_CLIMATE_ENTITY,
    CONF_ROOM_SENSOR,
    CONF_OUTLIER_DETECTION_ENABLED,
    CONF_OUTLIER_SENSITIVITY,
    DEFAULT_OUTLIER_DETECTION_ENABLED,
    DEFAULT_OUTLIER_SENSITIVITY,
)


@pytest.fixture
def hass():
    """Create a mock Home Assistant instance."""
    mock_hass = MagicMock()
    mock_hass.states = MagicMock()
    mock_hass.states.async_all = MagicMock(return_value=[])
    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_entries = MagicMock(return_value=[])
    return mock_hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    config_entry = MagicMock()
    config_entry.data = {
        CONF_CLIMATE_ENTITY: "climate.test",
        CONF_ROOM_SENSOR: "sensor.test_temp",
    }
    config_entry.options = {}
    return config_entry


@pytest.fixture
def options_flow(hass, mock_config_entry):
    """Create options flow instance."""
    flow = SmartClimateOptionsFlow()
    flow.hass = hass
    flow.config_entry = mock_config_entry
    return flow


class TestOutlierOptionsFlow:
    """Test outlier detection options flow configuration."""

    @pytest.mark.asyncio
    async def test_options_flow_includes_outlier_settings(self, options_flow):
        """Test that options form includes outlier detection fields."""
        result = await options_flow.async_step_init()
        
        assert result["type"] == "form"
        assert result["step_id"] == "init"
        
        # Check that schema includes outlier detection fields
        schema_keys = [str(key) for key in result["data_schema"].schema.keys()]
        
        # Should include outlier detection enabled field
        assert any(CONF_OUTLIER_DETECTION_ENABLED in key for key in schema_keys)
        
        # Should include outlier sensitivity field  
        assert any(CONF_OUTLIER_SENSITIVITY in key for key in schema_keys)

    @pytest.mark.asyncio
    async def test_options_flow_default_values(self, options_flow):
        """Test that options form shows correct default values."""
        result = await options_flow.async_step_init()
        
        schema = result["data_schema"].schema
        
        # Find outlier detection enabled field and check default
        outlier_enabled_field = None
        outlier_sensitivity_field = None
        
        for key, selector in schema.items():
            key_str = str(key)
            if CONF_OUTLIER_DETECTION_ENABLED in key_str:
                outlier_enabled_field = key
            elif CONF_OUTLIER_SENSITIVITY in key_str:
                outlier_sensitivity_field = key
        
        assert outlier_enabled_field is not None
        assert outlier_sensitivity_field is not None
        
        # Default should be enabled=True
        assert outlier_enabled_field.default is True
        
        # Default sensitivity should be 2.5
        assert outlier_sensitivity_field.default == 2.5

    @pytest.mark.asyncio
    async def test_options_flow_validation(self, options_flow):
        """Test that sensitivity field has proper validation range (1.0-5.0)."""
        result = await options_flow.async_step_init()
        
        schema = result["data_schema"].schema
        
        # Find sensitivity field and check range
        sensitivity_field = None
        for key, selector in schema.items():
            if CONF_OUTLIER_SENSITIVITY in str(key):
                sensitivity_field = selector
                break
        
        assert sensitivity_field is not None
        
        # Check that it's a NumberSelector with proper range
        assert hasattr(sensitivity_field, 'config')
        config = sensitivity_field.config
        assert config.min == 1.0
        assert config.max == 5.0

    @pytest.mark.asyncio
    async def test_options_flow_saves_configuration(self, options_flow):
        """Test that options are properly saved to config_entry.options."""
        user_input = {
            CONF_OUTLIER_DETECTION_ENABLED: False,
            CONF_OUTLIER_SENSITIVITY: 3.0,
            "max_offset": 4.0,  # Include other existing option
        }
        
        result = await options_flow.async_step_init(user_input)
        
        assert result["type"] == "create_entry"
        assert result["data"][CONF_OUTLIER_DETECTION_ENABLED] is False
        assert result["data"][CONF_OUTLIER_SENSITIVITY] == 3.0
        assert result["data"]["max_offset"] == 4.0

    @pytest.mark.asyncio
    async def test_options_flow_triggers_reload(self, options_flow):
        """Test that options changes trigger integration reload."""
        user_input = {
            CONF_OUTLIER_DETECTION_ENABLED: True,
            CONF_OUTLIER_SENSITIVITY: 2.0,
        }
        
        # Mock the async_create_entry method to verify it's called
        with patch.object(options_flow, 'async_create_entry') as mock_create:
            mock_create.return_value = {"type": "create_entry", "data": user_input}
            
            result = await options_flow.async_step_init(user_input)
            
            # Verify async_create_entry was called (which triggers reload)
            mock_create.assert_called_once_with(title="", data=user_input)

    @pytest.mark.asyncio
    async def test_options_flow_preserves_existing_settings(self, options_flow):
        """Test that existing options are preserved when not changed."""
        # Set up existing options
        options_flow.config_entry.options = {
            "max_offset": 3.5,
            CONF_OUTLIER_DETECTION_ENABLED: False,
            CONF_OUTLIER_SENSITIVITY: 4.0,
        }
        
        result = await options_flow.async_step_init()
        
        schema = result["data_schema"].schema
        
        # Check that existing values are used as defaults
        max_offset_field = None
        outlier_enabled_field = None
        outlier_sensitivity_field = None
        
        for key, selector in schema.items():
            key_str = str(key)
            if "max_offset" in key_str:
                max_offset_field = key
            elif CONF_OUTLIER_DETECTION_ENABLED in key_str:
                outlier_enabled_field = key
            elif CONF_OUTLIER_SENSITIVITY in key_str:
                outlier_sensitivity_field = key
        
        # Should use existing values as defaults
        assert max_offset_field.default == 3.5
        assert outlier_enabled_field.default is False
        assert outlier_sensitivity_field.default == 4.0

    @pytest.mark.asyncio
    async def test_options_flow_uses_config_fallback(self, options_flow):
        """Test that config.data is used as fallback when option not in config_entry.options."""
        # Set up config.data with outlier settings but no options
        options_flow.config_entry.data = {
            CONF_CLIMATE_ENTITY: "climate.test",
            CONF_ROOM_SENSOR: "sensor.test_temp",
            CONF_OUTLIER_DETECTION_ENABLED: True,
            CONF_OUTLIER_SENSITIVITY: 1.5,
        }
        options_flow.config_entry.options = {}
        
        result = await options_flow.async_step_init()
        
        schema = result["data_schema"].schema
        
        # Find outlier fields
        outlier_enabled_field = None
        outlier_sensitivity_field = None
        
        for key, selector in schema.items():
            key_str = str(key)
            if CONF_OUTLIER_DETECTION_ENABLED in key_str:
                outlier_enabled_field = key
            elif CONF_OUTLIER_SENSITIVITY in key_str:
                outlier_sensitivity_field = key
        
        # Should fall back to config.data values
        assert outlier_enabled_field.default is True
        assert outlier_sensitivity_field.default == 1.5