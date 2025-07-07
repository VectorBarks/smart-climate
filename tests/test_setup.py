"""ABOUTME: Tests for smart climate integration setup functionality.
Verifies async_setup function, config handling, and platform initialization."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, call
import logging

# Test imports
from custom_components.smart_climate.const import DOMAIN

# Configure pytest for async tests
# pytest_plugins = ("pytest_asyncio",)  # Not available, using manual approach


class TestSetupFunction:
    """Test the async_setup function in __init__.py"""
    
    def test_async_setup_called_with_correct_parameters(self):
        """Test that async_setup is called with hass and config parameters."""
        import asyncio
        from custom_components.smart_climate import async_setup
        
        async def run_test():
            # Mock Home Assistant instance
            mock_hass = Mock()
            mock_hass.data = {}
            mock_hass.async_create_task = AsyncMock()
            
            # Mock config
            mock_config = {
                DOMAIN: {
                    "climate_entity": "climate.test",
                    "room_sensor": "sensor.test_room",
                    "outdoor_sensor": "sensor.test_outdoor",
                    "power_sensor": "sensor.test_power",
                    "max_offset": 3.0,
                    "min_temperature": 18.0,
                    "max_temperature": 28.0,
                    "update_interval": 120,
                    "ml_enabled": True
                }
            }
            
            # Call async_setup
            result = await async_setup(mock_hass, mock_config)
            
            # Should return True on success
            assert result is True
            
            # Should store config in hass.data
            assert DOMAIN in mock_hass.data
            assert mock_hass.data[DOMAIN] == mock_config[DOMAIN]
        
        asyncio.run(run_test())
    
    def test_async_setup_returns_true_on_success(self):
        """Test that async_setup returns True when setup succeeds."""
        import asyncio
        from custom_components.smart_climate import async_setup
        
        async def run_test():
            mock_hass = Mock()
            mock_hass.data = {}
            mock_hass.async_create_task = AsyncMock()
            
            mock_config = {DOMAIN: {"climate_entity": "climate.test", "room_sensor": "sensor.test"}}
            
            result = await async_setup(mock_hass, mock_config)
            assert result is True
        
        asyncio.run(run_test())
    
    def test_async_setup_handles_empty_config(self):
        """Test that async_setup handles empty config gracefully."""
        import asyncio
        from custom_components.smart_climate import async_setup
        
        async def run_test():
            mock_hass = Mock()
            mock_hass.data = {}
            mock_hass.async_create_task = AsyncMock()
            
            # Empty config - should still work
            mock_config = {}
            
            result = await async_setup(mock_hass, mock_config)
            assert result is True
            
            # Should initialize empty data
            assert DOMAIN in mock_hass.data
            assert mock_hass.data[DOMAIN] == {}
        
        asyncio.run(run_test())
    
    def test_async_setup_logs_initialization(self):
        """Test that async_setup logs setup initiation."""
        import asyncio
        from custom_components.smart_climate import async_setup
        
        async def run_test():
            mock_hass = Mock()
            mock_hass.data = {}
            mock_hass.async_create_task = AsyncMock()
            
            mock_config = {DOMAIN: {"climate_entity": "climate.test"}}
            
            # Mock logger
            with patch('custom_components.smart_climate._LOGGER') as mock_logger:
                await async_setup(mock_hass, mock_config)
                
                # Should log setup start
                mock_logger.info.assert_called_once_with("Setting up Smart Climate Control integration")
        
        asyncio.run(run_test())
    
    def test_async_setup_initiates_platform_setup(self):
        """Test that async_setup initiates platform setup for climate."""
        import asyncio
        from custom_components.smart_climate import async_setup
        
        async def run_test():
            mock_hass = Mock()
            mock_hass.data = {}
            mock_hass.async_create_task = AsyncMock()
            
            mock_config = {DOMAIN: {"climate_entity": "climate.test"}}
            
            # Mock the forward entry setup
            with patch('custom_components.smart_climate.async_forward_entry_setup') as mock_forward:
                mock_forward.return_value = True
                
                await async_setup(mock_hass, mock_config)
                
                # Should call async_forward_entry_setup for climate platform
                mock_forward.assert_called_once_with(mock_hass, "climate")
        
        asyncio.run(run_test())
    
    def test_async_setup_initializes_hass_data(self):
        """Test that async_setup initializes hass.data correctly."""
        import asyncio
        from custom_components.smart_climate import async_setup
        
        async def run_test():
            mock_hass = Mock()
            mock_hass.data = {}
            mock_hass.async_create_task = AsyncMock()
            
            mock_config = {
                DOMAIN: {
                    "climate_entity": "climate.test",
                    "room_sensor": "sensor.test_room",
                    "max_offset": 2.5
                }
            }
            
            await async_setup(mock_hass, mock_config)
            
            # Should initialize the domain in hass.data
            assert DOMAIN in mock_hass.data
            assert isinstance(mock_hass.data[DOMAIN], dict)
            assert mock_hass.data[DOMAIN]["climate_entity"] == "climate.test"
            assert mock_hass.data[DOMAIN]["room_sensor"] == "sensor.test_room"
            assert mock_hass.data[DOMAIN]["max_offset"] == 2.5
        
        asyncio.run(run_test())
    
    def test_async_setup_handles_missing_domain_config(self):
        """Test that async_setup handles missing domain config gracefully."""
        import asyncio
        from custom_components.smart_climate import async_setup
        
        async def run_test():
            mock_hass = Mock()
            mock_hass.data = {}
            mock_hass.async_create_task = AsyncMock()
            
            # Config without our domain
            mock_config = {"other_domain": {"setting": "value"}}
            
            result = await async_setup(mock_hass, mock_config)
            assert result is True
            
            # Should initialize empty domain data
            assert DOMAIN in mock_hass.data
            assert mock_hass.data[DOMAIN] == {}
        
        asyncio.run(run_test())
    
    def test_async_setup_preserves_existing_hass_data(self):
        """Test that async_setup preserves existing hass.data structure."""
        import asyncio
        from custom_components.smart_climate import async_setup
        
        async def run_test():
            mock_hass = Mock()
            mock_hass.data = {"existing_domain": {"key": "value"}}
            mock_hass.async_create_task = AsyncMock()
            
            mock_config = {DOMAIN: {"climate_entity": "climate.test"}}
            
            await async_setup(mock_hass, mock_config)
            
            # Should preserve existing data
            assert "existing_domain" in mock_hass.data
            assert mock_hass.data["existing_domain"]["key"] == "value"
            
            # Should add our domain
            assert DOMAIN in mock_hass.data
            assert mock_hass.data[DOMAIN]["climate_entity"] == "climate.test"
        
        asyncio.run(run_test())


class TestConfigSchema:
    """Test the configuration schema validation."""
    
    def test_config_schema_exists(self):
        """Test that config schema module exists."""
        from custom_components.smart_climate import config_schema
        assert config_schema is not None
    
    def test_config_schema_validates_required_fields(self):
        """Test that config schema validates required fields."""
        from custom_components.smart_climate.config_schema import CONFIG_SCHEMA
        
        # Should have schema defined
        assert CONFIG_SCHEMA is not None
        
        # Test valid config
        valid_config = {
            "climate_entity": "climate.test",
            "room_sensor": "sensor.test_room"
        }
        
        # Should validate without error
        try:
            validated = CONFIG_SCHEMA(valid_config)
            assert validated["climate_entity"] == "climate.test"
            assert validated["room_sensor"] == "sensor.test_room"
        except Exception as e:
            pytest.fail(f"Valid config should not raise exception: {e}")
    
    def test_config_schema_applies_defaults(self):
        """Test that config schema applies default values."""
        from custom_components.smart_climate.config_schema import CONFIG_SCHEMA
        
        # Minimal config
        config = {
            "climate_entity": "climate.test",
            "room_sensor": "sensor.test_room"
        }
        
        validated = CONFIG_SCHEMA(config)
        
        # Should have default values applied
        assert validated["max_offset"] == 5.0
        assert validated["min_temperature"] == 16.0
        assert validated["max_temperature"] == 30.0
        assert validated["update_interval"] == 180
        assert validated["ml_enabled"] is True
    
    def test_config_schema_validates_temperature_limits(self):
        """Test that config schema validates temperature limits."""
        from custom_components.smart_climate.config_schema import CONFIG_SCHEMA
        
        # Test invalid temperature limits
        invalid_config = {
            "climate_entity": "climate.test",
            "room_sensor": "sensor.test_room",
            "min_temperature": 25.0,
            "max_temperature": 20.0  # Lower than min
        }
        
        with pytest.raises(Exception):
            CONFIG_SCHEMA(invalid_config)
    
    def test_config_schema_validates_offset_limits(self):
        """Test that config schema validates offset limits."""
        from custom_components.smart_climate.config_schema import CONFIG_SCHEMA
        
        # Test invalid offset (negative)
        invalid_config = {
            "climate_entity": "climate.test",
            "room_sensor": "sensor.test_room",
            "max_offset": -1.0
        }
        
        with pytest.raises(Exception):
            CONFIG_SCHEMA(invalid_config)