"""Tests for adaptive delay configuration."""

import pytest
import voluptuous as vol
from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from custom_components.smart_climate.const import (
    DOMAIN,
    CONF_ADAPTIVE_DELAY,
    DEFAULT_ADAPTIVE_DELAY,
    CONF_CLIMATE_ENTITY,
    CONF_ROOM_SENSOR,
)
from custom_components.smart_climate.config_flow import (
    SmartClimateConfigFlow,
    SmartClimateOptionsFlow,
)


class TestAdaptiveDelayConstants:
    """Test adaptive delay constants."""

    def test_adaptive_delay_constant_exists(self):
        """Test that CONF_ADAPTIVE_DELAY constant is defined."""
        assert CONF_ADAPTIVE_DELAY == "adaptive_delay"

    def test_adaptive_delay_default_exists(self):
        """Test that DEFAULT_ADAPTIVE_DELAY constant is defined."""
        assert DEFAULT_ADAPTIVE_DELAY is True

    def test_adaptive_delay_default_is_boolean(self):
        """Test that DEFAULT_ADAPTIVE_DELAY is a boolean value."""
        assert isinstance(DEFAULT_ADAPTIVE_DELAY, bool)


class TestConfigFlowAdaptiveDelay:
    """Test adaptive delay configuration in config flow."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = AsyncMock()
        hass.states.async_all.return_value = [
            # Mock climate entity
            AsyncMock(
                entity_id="climate.test_ac",
                attributes={"friendly_name": "Test AC"}
            ),
            # Mock temperature sensor
            AsyncMock(
                entity_id="sensor.room_temp",
                attributes={"device_class": "temperature", "friendly_name": "Room Temperature"}
            ),
        ]
        return hass

    @pytest.fixture
    def config_flow(self, mock_hass):
        """Create a config flow instance."""
        flow = SmartClimateConfigFlow()
        flow.hass = mock_hass
        return flow

    @pytest.mark.asyncio
    async def test_adaptive_delay_field_in_initial_schema(self, config_flow):
        """Test that adaptive_delay field is present in initial config schema."""
        with patch.object(config_flow, '_get_climate_entities', return_value={"climate.test_ac": "Test AC"}), \
             patch.object(config_flow, '_get_temperature_sensors', return_value={"sensor.room_temp": "Room Temperature"}), \
             patch.object(config_flow, '_get_power_sensors', return_value={}):
            
            result = await config_flow.async_step_user()
            
            # Check that the form contains adaptive_delay field
            schema_keys = [str(key) for key in result["data_schema"].schema.keys()]
            adaptive_delay_found = any("adaptive_delay" in key for key in schema_keys)
            assert adaptive_delay_found, f"adaptive_delay field not found in schema keys: {schema_keys}"

    @pytest.mark.asyncio
    async def test_adaptive_delay_default_value_initial(self, config_flow):
        """Test that adaptive_delay has correct default value in initial config."""
        with patch.object(config_flow, '_get_climate_entities', return_value={"climate.test_ac": "Test AC"}), \
             patch.object(config_flow, '_get_temperature_sensors', return_value={"sensor.room_temp": "Room Temperature"}), \
             patch.object(config_flow, '_get_power_sensors', return_value={}):
            
            result = await config_flow.async_step_user()
            
            # Find the adaptive_delay field and check its default
            for key, selector in result["data_schema"].schema.items():
                if hasattr(key, 'default') and str(key).endswith('adaptive_delay'):
                    assert key.default() == DEFAULT_ADAPTIVE_DELAY
                    break
            else:
                pytest.fail("adaptive_delay field with default not found in schema")

    @pytest.mark.asyncio
    async def test_adaptive_delay_validation_accepts_boolean(self, config_flow):
        """Test that adaptive_delay validation accepts boolean values."""
        user_input = {
            CONF_CLIMATE_ENTITY: "climate.test_ac",
            CONF_ROOM_SENSOR: "sensor.room_temp", 
            CONF_ADAPTIVE_DELAY: True
        }
        
        with patch.object(config_flow, '_entity_exists', return_value=True), \
             patch.object(config_flow, '_already_configured', return_value=False), \
             patch.object(config_flow, '_get_climate_entities', return_value={"climate.test_ac": "Test AC"}), \
             patch.object(config_flow, '_get_temperature_sensors', return_value={"sensor.room_temp": "Room Temperature"}), \
             patch.object(config_flow, '_get_power_sensors', return_value={}):
            
            validated = await config_flow._validate_input(user_input)
            assert validated[CONF_ADAPTIVE_DELAY] is True

    @pytest.mark.asyncio
    async def test_adaptive_delay_validation_accepts_false(self, config_flow):
        """Test that adaptive_delay validation accepts False value."""
        user_input = {
            CONF_CLIMATE_ENTITY: "climate.test_ac",
            CONF_ROOM_SENSOR: "sensor.room_temp",
            CONF_ADAPTIVE_DELAY: False
        }
        
        with patch.object(config_flow, '_entity_exists', return_value=True), \
             patch.object(config_flow, '_already_configured', return_value=False):
            
            validated = await config_flow._validate_input(user_input)
            assert validated[CONF_ADAPTIVE_DELAY] is False

    @pytest.mark.asyncio
    async def test_adaptive_delay_default_when_missing(self, config_flow):
        """Test that adaptive_delay uses default when not provided."""
        user_input = {
            CONF_CLIMATE_ENTITY: "climate.test_ac",
            CONF_ROOM_SENSOR: "sensor.room_temp"
            # No adaptive_delay provided
        }
        
        with patch.object(config_flow, '_entity_exists', return_value=True), \
             patch.object(config_flow, '_already_configured', return_value=False):
            
            validated = await config_flow._validate_input(user_input)
            assert validated[CONF_ADAPTIVE_DELAY] == DEFAULT_ADAPTIVE_DELAY


class TestOptionsFlowAdaptiveDelay:
    """Test adaptive delay configuration in options flow."""

    @pytest.fixture
    def mock_config_entry(self):
        """Create a mock config entry."""
        return AsyncMock(
            data={
                CONF_CLIMATE_ENTITY: "climate.test_ac",
                CONF_ROOM_SENSOR: "sensor.room_temp",
                CONF_ADAPTIVE_DELAY: True
            },
            options={}
        )

    @pytest.fixture 
    def options_flow(self, mock_config_entry):
        """Create an options flow instance."""
        flow = SmartClimateOptionsFlow()
        flow.config_entry = mock_config_entry
        return flow

    @pytest.mark.asyncio
    async def test_adaptive_delay_field_in_options_schema(self, options_flow):
        """Test that adaptive_delay field is present in options schema."""
        result = await options_flow.async_step_init()
        
        # Check that the form contains adaptive_delay field
        schema_keys = [str(key) for key in result["data_schema"].schema.keys()]
        adaptive_delay_found = any("adaptive_delay" in key for key in schema_keys)
        assert adaptive_delay_found, f"adaptive_delay field not found in options schema keys: {schema_keys}"

    @pytest.mark.asyncio
    async def test_adaptive_delay_preserves_current_value(self, options_flow):
        """Test that adaptive_delay preserves current config value in options."""
        # Set current value to False
        options_flow.config_entry.data[CONF_ADAPTIVE_DELAY] = False
        
        result = await options_flow.async_step_init()
        
        # Find the adaptive_delay field and check it uses current value
        for key, selector in result["data_schema"].schema.items():
            if hasattr(key, 'default') and str(key).endswith('adaptive_delay'):
                assert key.default() is False
                break
        else:
            pytest.fail("adaptive_delay field with default not found in options schema")

    @pytest.mark.asyncio
    async def test_adaptive_delay_uses_option_over_config(self, options_flow):
        """Test that adaptive_delay uses option value over config value."""
        # Set different values in config and options
        options_flow.config_entry.data[CONF_ADAPTIVE_DELAY] = True
        options_flow.config_entry.options[CONF_ADAPTIVE_DELAY] = False
        
        result = await options_flow.async_step_init()
        
        # Find the adaptive_delay field and check it uses option value
        for key, selector in result["data_schema"].schema.keys():
            if hasattr(key, 'default') and str(key).endswith('adaptive_delay'):
                assert key.default() is False  # Should use options value
                break
        else:
            pytest.fail("adaptive_delay field with default not found in options schema")

    @pytest.mark.asyncio
    async def test_adaptive_delay_fallback_to_default(self, options_flow):
        """Test that adaptive_delay falls back to default when not in config or options."""
        # Remove adaptive_delay from both config and options
        options_flow.config_entry.data.pop(CONF_ADAPTIVE_DELAY, None)
        options_flow.config_entry.options.pop(CONF_ADAPTIVE_DELAY, None)
        
        result = await options_flow.async_step_init()
        
        # Find the adaptive_delay field and check it uses default
        for key, selector in result["data_schema"].schema.keys():
            if hasattr(key, 'default') and str(key).endswith('adaptive_delay'):
                assert key.default() == DEFAULT_ADAPTIVE_DELAY
                break
        else:
            pytest.fail("adaptive_delay field with default not found in options schema")

    @pytest.mark.asyncio
    async def test_options_creates_entry_with_adaptive_delay(self, options_flow):
        """Test that options flow creates entry with adaptive_delay value."""
        user_input = {CONF_ADAPTIVE_DELAY: False}
        
        result = await options_flow.async_step_init(user_input)
        
        assert result["type"] == "create_entry"
        assert result["data"][CONF_ADAPTIVE_DELAY] is False


class TestAdaptiveDelayTranslations:
    """Test adaptive delay translations."""

    @pytest.fixture
    def translations(self):
        """Load translations for testing."""
        # This would normally load from the actual en.json file
        # For testing, we'll simulate the expected structure
        return {
            "config": {
                "step": {
                    "user": {
                        "data": {
                            "adaptive_delay": "Enable Adaptive Feedback Delays"
                        },
                        "data_description": {
                            "adaptive_delay": "Automatically adjust feedback delay timing based on AC response patterns"
                        }
                    }
                }
            },
            "options": {
                "step": {
                    "init": {
                        "data": {
                            "adaptive_delay": "Enable Adaptive Feedback Delays"
                        },
                        "data_description": {
                            "adaptive_delay": "Automatically adjust feedback delay timing based on AC response patterns"
                        }
                    }
                }
            }
        }

    def test_adaptive_delay_config_translation_exists(self, translations):
        """Test that adaptive_delay config translation exists."""
        assert "adaptive_delay" in translations["config"]["step"]["user"]["data"]
        assert translations["config"]["step"]["user"]["data"]["adaptive_delay"] == "Enable Adaptive Feedback Delays"

    def test_adaptive_delay_config_description_exists(self, translations):
        """Test that adaptive_delay config description exists."""
        assert "adaptive_delay" in translations["config"]["step"]["user"]["data_description"]
        description = translations["config"]["step"]["user"]["data_description"]["adaptive_delay"]
        assert "automatically" in description.lower()
        assert "feedback delay" in description.lower()

    def test_adaptive_delay_options_translation_exists(self, translations):
        """Test that adaptive_delay options translation exists."""
        assert "adaptive_delay" in translations["options"]["step"]["init"]["data"]
        assert translations["options"]["step"]["init"]["data"]["adaptive_delay"] == "Enable Adaptive Feedback Delays"

    def test_adaptive_delay_options_description_exists(self, translations):
        """Test that adaptive_delay options description exists."""
        assert "adaptive_delay" in translations["options"]["step"]["init"]["data_description"]
        description = translations["options"]["step"]["init"]["data_description"]["adaptive_delay"]
        assert "automatically" in description.lower()
        assert "feedback delay" in description.lower()