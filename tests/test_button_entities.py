"""Tests for the Smart Climate button entities."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.smart_climate.button import (
    ResetTrainingDataButton,
    async_setup_entry
)
from custom_components.smart_climate.const import DOMAIN


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.data = {
        DOMAIN: {
            "test_entry": {
                "offset_engines": {
                    "climate.test_ac": Mock(),
                    "climate.test_ac2": Mock()
                },
                "data_stores": {
                    "climate.test_ac": Mock(),
                    "climate.test_ac2": Mock()
                }
            }
        }
    }
    return hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = Mock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.unique_id = "test_unique"
    entry.title = "Test Climate"
    return entry


@pytest.fixture
def mock_offset_engine():
    """Create a mock offset engine."""
    engine = Mock()
    engine.reset_learning = Mock()
    return engine


@pytest.fixture
def mock_data_store():
    """Create a mock data store."""
    store = Mock()
    store.delete_learning_data = AsyncMock()
    return store


class TestResetTrainingDataButton:
    """Test the ResetTrainingDataButton entity."""
    
    def test_init(self, mock_config_entry, mock_offset_engine, mock_data_store):
        """Test button initialization."""
        button = ResetTrainingDataButton(
            mock_config_entry,
            mock_offset_engine,
            mock_data_store,
            "Test Climate",
            "climate.test_ac"
        )
        
        assert button._offset_engine == mock_offset_engine
        assert button._data_store == mock_data_store
        assert button._entity_id == "climate.test_ac"
        assert button._attr_name == "Reset Training Data"
        assert button._attr_unique_id == "test_unique_climate_test_ac_reset_training_data"
        assert button.icon == "mdi:database-remove"
        
    def test_device_info(self, mock_config_entry, mock_offset_engine, mock_data_store):
        """Test device info property."""
        button = ResetTrainingDataButton(
            mock_config_entry,
            mock_offset_engine,
            mock_data_store,
            "Test Climate",
            "climate.test_ac"
        )
        
        device_info = button._attr_device_info
        assert device_info["identifiers"] == {(DOMAIN, "test_unique_climate_test_ac")}
        assert device_info["name"] == "Test Climate"
        
    @pytest.mark.asyncio
    async def test_async_press_success(self, mock_config_entry, mock_offset_engine, mock_data_store):
        """Test successful button press."""
        button = ResetTrainingDataButton(
            mock_config_entry,
            mock_offset_engine,
            mock_data_store,
            "Test Climate",
            "climate.test_ac"
        )
        
        # Mock the logger to verify logging
        with patch("custom_components.smart_climate.button._LOGGER") as mock_logger:
            await button.async_press()
            
            # Verify methods were called
            mock_offset_engine.reset_learning.assert_called_once()
            mock_data_store.delete_learning_data.assert_called_once()
            
            # Verify logging - check any of the info calls
            mock_logger.info.assert_called()
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("Reset training data" in call or "Training data reset completed" in call for call in info_calls)
            
    @pytest.mark.asyncio
    async def test_async_press_offset_engine_error(self, mock_config_entry, mock_offset_engine, mock_data_store):
        """Test button press when offset engine reset fails."""
        button = ResetTrainingDataButton(
            mock_config_entry,
            mock_offset_engine,
            mock_data_store,
            "Test Climate",
            "climate.test_ac"
        )
        
        # Make reset_learning raise an exception
        mock_offset_engine.reset_learning.side_effect = Exception("Reset failed")
        
        with patch("custom_components.smart_climate.button._LOGGER") as mock_logger:
            await button.async_press()
            
            # Verify error was logged
            mock_logger.error.assert_called()
            assert "Failed to reset training data" in str(mock_logger.error.call_args)
            
            # Data store delete should not be called if offset engine fails
            mock_data_store.delete_learning_data.assert_not_called()
            
    @pytest.mark.asyncio
    async def test_async_press_data_store_error(self, mock_config_entry, mock_offset_engine, mock_data_store):
        """Test button press when data store delete fails."""
        button = ResetTrainingDataButton(
            mock_config_entry,
            mock_offset_engine,
            mock_data_store,
            "Test Climate",
            "climate.test_ac"
        )
        
        # Make delete_learning_data raise an exception
        mock_data_store.delete_learning_data.side_effect = Exception("Delete failed")
        
        with patch("custom_components.smart_climate.button._LOGGER") as mock_logger:
            await button.async_press()
            
            # Offset engine should still be reset
            mock_offset_engine.reset_learning.assert_called_once()
            
            # Error should be logged but not crash
            mock_logger.warning.assert_called()
            assert "Failed to delete learning data file" in str(mock_logger.warning.call_args)


class TestAsyncSetupEntry:
    """Test the async_setup_entry function."""
    
    @pytest.mark.asyncio
    async def test_setup_with_entities(self, mock_hass, mock_config_entry):
        """Test setting up button entities."""
        async_add_entities = AsyncMock()
        
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        
        # Should create 2 buttons for 2 climate entities
        async_add_entities.assert_called_once()
        buttons = async_add_entities.call_args[0][0]
        assert len(buttons) == 2
        assert all(isinstance(button, ResetTrainingDataButton) for button in buttons)
        
    @pytest.mark.asyncio
    async def test_setup_no_engines(self, mock_hass, mock_config_entry):
        """Test setup when no offset engines exist."""
        # Clear the offset engines
        mock_hass.data[DOMAIN]["test_entry"]["offset_engines"] = {}
        
        async_add_entities = AsyncMock()
        
        with patch("custom_components.smart_climate.button._LOGGER") as mock_logger:
            await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
            
            # Should not add any entities
            async_add_entities.assert_not_called()
            
            # Should log warning
            mock_logger.warning.assert_called()
            assert "No offset engines found" in str(mock_logger.warning.call_args)
            
    @pytest.mark.asyncio
    async def test_setup_no_data_stores(self, mock_hass, mock_config_entry):
        """Test setup when data stores are missing."""
        # Clear the data stores
        mock_hass.data[DOMAIN]["test_entry"]["data_stores"] = {}
        
        async_add_entities = AsyncMock()
        
        with patch("custom_components.smart_climate.button._LOGGER") as mock_logger:
            await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
            
            # Should still create buttons but log warnings
            async_add_entities.assert_called_once()
            buttons = async_add_entities.call_args[0][0]
            assert len(buttons) == 2
            
            # Should log warning for missing data stores
            mock_logger.warning.assert_called()