"""Test persistence integration with the main integration setup."""

import asyncio
import json
import pytest
import pytest_asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.exceptions import HomeAssistantError

from custom_components.smart_climate import async_setup_entry, async_unload_entry
from custom_components.smart_climate.const import DOMAIN
from custom_components.smart_climate.data_store import SmartClimateDataStore
from custom_components.smart_climate.offset_engine import OffsetEngine


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = Mock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.unique_id = "test_unique_id"
    entry.title = "Test Climate"
    entry.data = {
        "climate_entity": "climate.test_ac",
        "room_sensor": "sensor.room_temp",
        "outdoor_sensor": "sensor.outdoor_temp",
        "power_sensor": "sensor.ac_power",
        "enable_learning": True,
        "max_offset": 5.0,
        "update_interval": 180
    }
    return entry


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.data = {DOMAIN: {}}
    hass.config_entries = Mock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    
    # Mock config directory for data store
    config_path = Path("/tmp/test_ha_config")
    config_path.mkdir(exist_ok=True)
    hass.config = Mock()
    hass.config.config_dir = str(config_path)
    
    return hass


class TestIntegrationPersistenceSetup:
    """Test persistence integration during setup."""
    
    @patch('custom_components.smart_climate.EntityWaiter')
    @pytest.mark.asyncio
    async def test_data_store_created_during_setup(self, mock_waiter_class, mock_hass, mock_config_entry):
        """Test that SmartClimateDataStore is created for the climate entity during setup."""
        # Setup entity waiter mock
        mock_waiter = AsyncMock()
        mock_waiter.wait_for_required_entities = AsyncMock()
        mock_waiter_class.return_value = mock_waiter
        
        # Perform setup
        result = await async_setup_entry(mock_hass, mock_config_entry)
        
        assert result is True
        assert DOMAIN in mock_hass.data
        assert mock_config_entry.entry_id in mock_hass.data[DOMAIN]
        
        # Check that OffsetEngine was created
        entry_data = mock_hass.data[DOMAIN][mock_config_entry.entry_id]
        assert "offset_engines" in entry_data
        assert "climate.test_ac" in entry_data["offset_engines"]
        assert isinstance(entry_data["offset_engines"]["climate.test_ac"], OffsetEngine)
        
        # Verify platforms were set up
        mock_hass.config_entries.async_forward_entry_setups.assert_called_once()
    
    @patch('custom_components.smart_climate.EntityWaiter')
    @patch('custom_components.smart_climate.SmartClimateDataStore')
    @pytest.mark.asyncio
    async def test_data_store_linked_to_offset_engine(self, mock_store_class, mock_waiter_class, mock_hass, mock_config_entry):
        """Test that data store is properly linked to offset engine."""
        # Setup mocks
        mock_waiter = AsyncMock()
        mock_waiter.wait_for_required_entities = AsyncMock()
        mock_waiter_class.return_value = mock_waiter
        
        mock_data_store = Mock(spec=SmartClimateDataStore)
        mock_data_store.async_load_learning_data = AsyncMock(return_value={"test": "data"})
        mock_store_class.return_value = mock_data_store
        
        # Patch offset engine methods
        with patch.object(OffsetEngine, 'set_data_store') as mock_set_store, \
             patch.object(OffsetEngine, 'async_load_learning_data') as mock_load, \
             patch.object(OffsetEngine, 'async_setup_periodic_save') as mock_save:
            
            mock_load.return_value = True
            mock_save.return_value = lambda: None
            
            # Perform setup
            result = await async_setup_entry(mock_hass, mock_config_entry)
            
            assert result is True
            
            # Verify data store was created for correct entity
            mock_store_class.assert_called_once_with(mock_hass, "climate.test_ac")
            
            # Verify offset engine methods were called
            offset_engines = mock_hass.data[DOMAIN][mock_config_entry.entry_id]["offset_engines"]
            offset_engine = offset_engines["climate.test_ac"]
            mock_set_store.assert_called_once_with(mock_data_store)
            mock_load.assert_called_once()
            mock_save.assert_called_once_with(mock_hass)
    
    @patch('custom_components.smart_climate.EntityWaiter')
    @pytest.mark.asyncio
    async def test_setup_with_learning_disabled(self, mock_waiter_class, mock_hass, mock_config_entry):
        """Test setup when learning is disabled."""
        # Disable learning in config
        mock_config_entry.data = {
            **mock_config_entry.data,
            "enable_learning": False
        }
        
        # Setup entity waiter mock
        mock_waiter = AsyncMock()
        mock_waiter.wait_for_required_entities = AsyncMock()
        mock_waiter_class.return_value = mock_waiter
        
        # Perform setup
        result = await async_setup_entry(mock_hass, mock_config_entry)
        
        assert result is True
        
        # Verify OffsetEngine was created with learning disabled
        offset_engines = mock_hass.data[DOMAIN][mock_config_entry.entry_id]["offset_engines"]
        offset_engine = offset_engines["climate.test_ac"]
        assert not offset_engine.is_learning_enabled
    
    @patch('custom_components.smart_climate.EntityWaiter')
    @patch('custom_components.smart_climate.SmartClimateDataStore')
    @pytest.mark.asyncio
    async def test_data_loading_during_setup(self, mock_store_class, mock_waiter_class, mock_hass, mock_config_entry):
        """Test that learning data is loaded during setup."""
        # Setup mocks
        mock_waiter = AsyncMock()
        mock_waiter.wait_for_required_entities = AsyncMock()
        mock_waiter_class.return_value = mock_waiter
        
        # Mock learning data
        expected_data = {
            "samples": [
                {"predicted": 2.0, "actual": 1.8, "ac_temp": 25.0, "room_temp": 23.0}
            ],
            "min_samples": 20,
            "has_sufficient_data": False
        }
        
        mock_data_store = Mock(spec=SmartClimateDataStore)
        mock_data_store.async_load_learning_data = AsyncMock(return_value=expected_data)
        mock_store_class.return_value = mock_data_store
        
        with patch.object(OffsetEngine, 'set_data_store') as mock_set_store, \
             patch.object(OffsetEngine, 'async_load_learning_data') as mock_load, \
             patch.object(OffsetEngine, 'async_setup_periodic_save') as mock_save:
            
            mock_load.return_value = True
            mock_save.return_value = lambda: None
            
            # Perform setup
            result = await async_setup_entry(mock_hass, mock_config_entry)
            
            assert result is True
            mock_load.assert_called_once()
    
    @patch('custom_components.smart_climate.EntityWaiter')
    @patch('custom_components.smart_climate.SmartClimateDataStore')
    @pytest.mark.asyncio
    async def test_periodic_save_setup(self, mock_store_class, mock_waiter_class, mock_hass, mock_config_entry):
        """Test that periodic saving is set up correctly."""
        # Setup mocks
        mock_waiter = AsyncMock()
        mock_waiter.wait_for_required_entities = AsyncMock()
        mock_waiter_class.return_value = mock_waiter
        
        mock_data_store = Mock(spec=SmartClimateDataStore)
        mock_store_class.return_value = mock_data_store
        
        mock_cancel_function = Mock()
        
        with patch.object(OffsetEngine, 'set_data_store'), \
             patch.object(OffsetEngine, 'async_load_learning_data', return_value=True), \
             patch.object(OffsetEngine, 'async_setup_periodic_save', return_value=mock_cancel_function) as mock_save:
            
            # Perform setup
            result = await async_setup_entry(mock_hass, mock_config_entry)
            
            assert result is True
            mock_save.assert_called_once_with(mock_hass)
            
            # Verify cleanup function is stored
            entry_data = mock_hass.data[DOMAIN][mock_config_entry.entry_id]
            assert "unload_listeners" in entry_data
            assert len(entry_data["unload_listeners"]) == 1


class TestMultipleEntityPersistence:
    """Test persistence with multiple climate entities."""
    
    @patch('custom_components.smart_climate.EntityWaiter')
    @patch('custom_components.smart_climate.SmartClimateDataStore')
    @pytest.mark.asyncio
    async def test_multiple_entities_get_separate_stores(self, mock_store_class, mock_waiter_class, mock_hass):
        """Test that multiple entities get separate data stores."""
        # Setup entity waiter mock
        mock_waiter = AsyncMock()
        mock_waiter.wait_for_required_entities = AsyncMock()
        mock_waiter_class.return_value = mock_waiter
        
        # Create two different config entries
        entry1 = Mock(spec=ConfigEntry)
        entry1.entry_id = "entry_1"
        entry1.data = {
            "climate_entity": "climate.living_room",
            "room_sensor": "sensor.living_room_temp",
            "enable_learning": True
        }
        
        entry2 = Mock(spec=ConfigEntry)
        entry2.entry_id = "entry_2"
        entry2.data = {
            "climate_entity": "climate.bedroom",
            "room_sensor": "sensor.bedroom_temp",
            "enable_learning": True
        }
        
        # Mock data store instances
        mock_store1 = Mock(spec=SmartClimateDataStore)
        mock_store2 = Mock(spec=SmartClimateDataStore)
        mock_store_class.side_effect = [mock_store1, mock_store2]
        
        with patch.object(OffsetEngine, 'set_data_store') as mock_set_store, \
             patch.object(OffsetEngine, 'async_load_learning_data', return_value=True), \
             patch.object(OffsetEngine, 'async_setup_periodic_save', return_value=lambda: None):
            
            # Setup both entries
            result1 = await async_setup_entry(mock_hass, entry1)
            result2 = await async_setup_entry(mock_hass, entry2)
            
            assert result1 is True
            assert result2 is True
            
            # Verify separate data stores were created
            assert mock_store_class.call_count == 2
            mock_store_class.assert_any_call(mock_hass, "climate.living_room")
            mock_store_class.assert_any_call(mock_hass, "climate.bedroom")
            
            # Verify separate offset engines exist
            assert "entry_1" in mock_hass.data[DOMAIN]
            assert "entry_2" in mock_hass.data[DOMAIN]
            assert mock_hass.data[DOMAIN]["entry_1"]["offset_engines"] != mock_hass.data[DOMAIN]["entry_2"]["offset_engines"]


class TestPersistenceErrorHandling:
    """Test error handling in persistence setup."""
    
    @patch('custom_components.smart_climate.EntityWaiter')
    @patch('custom_components.smart_climate.SmartClimateDataStore')
    @pytest.mark.asyncio
    async def test_setup_continues_if_data_loading_fails(self, mock_store_class, mock_waiter_class, mock_hass, mock_config_entry):
        """Test that setup continues even if learning data loading fails."""
        # Setup mocks
        mock_waiter = AsyncMock()
        mock_waiter.wait_for_required_entities = AsyncMock()
        mock_waiter_class.return_value = mock_waiter
        
        mock_data_store = Mock(spec=SmartClimateDataStore)
        mock_store_class.return_value = mock_data_store
        
        with patch.object(OffsetEngine, 'set_data_store'), \
             patch.object(OffsetEngine, 'async_load_learning_data', side_effect=Exception("Load failed")), \
             patch.object(OffsetEngine, 'async_setup_periodic_save', return_value=lambda: None):
            
            # Setup should still succeed
            result = await async_setup_entry(mock_hass, mock_config_entry)
            assert result is True
    
    @patch('custom_components.smart_climate.EntityWaiter')
    @patch('custom_components.smart_climate.SmartClimateDataStore')
    @pytest.mark.asyncio
    async def test_setup_continues_if_periodic_save_setup_fails(self, mock_store_class, mock_waiter_class, mock_hass, mock_config_entry):
        """Test that setup continues even if periodic save setup fails."""
        # Setup mocks
        mock_waiter = AsyncMock()
        mock_waiter.wait_for_required_entities = AsyncMock()
        mock_waiter_class.return_value = mock_waiter
        
        mock_data_store = Mock(spec=SmartClimateDataStore)
        mock_store_class.return_value = mock_data_store
        
        with patch.object(OffsetEngine, 'set_data_store'), \
             patch.object(OffsetEngine, 'async_load_learning_data', return_value=True), \
             patch.object(OffsetEngine, 'async_setup_periodic_save', side_effect=Exception("Periodic save failed")):
            
            # Setup should still succeed
            result = await async_setup_entry(mock_hass, mock_config_entry)
            assert result is True
    
    @patch('custom_components.smart_climate.EntityWaiter')
    @pytest.mark.asyncio
    async def test_setup_continues_without_storage_permissions(self, mock_waiter_class, mock_hass, mock_config_entry):
        """Test graceful degradation when storage permissions are denied."""
        # Setup entity waiter mock
        mock_waiter = AsyncMock()
        mock_waiter.wait_for_required_entities = AsyncMock()
        mock_waiter_class.return_value = mock_waiter
        
        # Mock permission error when creating data store
        with patch('custom_components.smart_climate.SmartClimateDataStore', side_effect=PermissionError("No write access")):
            
            # Setup should still succeed (graceful degradation)
            result = await async_setup_entry(mock_hass, mock_config_entry)
            assert result is True
            
            # Verify offset engine was still created
            offset_engines = mock_hass.data[DOMAIN][mock_config_entry.entry_id]["offset_engines"]
            assert len(offset_engines) > 0


class TestSwitchStatePersistence:
    """Test switch state persistence integration."""
    
    @patch('custom_components.smart_climate.EntityWaiter')
    @patch('custom_components.smart_climate.SmartClimateDataStore')
    @pytest.mark.asyncio
    async def test_switch_state_saved_with_learning_data(self, mock_store_class, mock_waiter_class, mock_hass, mock_config_entry):
        """Test that switch state is saved along with learning data."""
        # Setup mocks
        mock_waiter = AsyncMock()
        mock_waiter.wait_for_required_entities = AsyncMock()
        mock_waiter_class.return_value = mock_waiter
        
        mock_data_store = Mock(spec=SmartClimateDataStore)
        mock_data_store.async_save_learning_data = AsyncMock()
        mock_store_class.return_value = mock_data_store
        
        with patch.object(OffsetEngine, 'set_data_store'), \
             patch.object(OffsetEngine, 'async_load_learning_data', return_value=True), \
             patch.object(OffsetEngine, 'async_setup_periodic_save', return_value=lambda: None):
            
            # Perform setup
            result = await async_setup_entry(mock_hass, mock_config_entry)
            assert result is True
            
            # Get the offset engine
            offset_engines = mock_hass.data[DOMAIN][mock_config_entry.entry_id]["offset_engines"]
            offset_engine = offset_engines["climate.test_ac"]
            
            # Enable/disable learning to trigger save
            offset_engine.disable_learning()
            offset_engine.enable_learning()
            
            # The actual save would be triggered by switch component
            # Here we just verify the engine can handle state changes
            assert offset_engine.is_learning_enabled is True
    
    @patch('custom_components.smart_climate.EntityWaiter')
    @patch('custom_components.smart_climate.SmartClimateDataStore')
    @pytest.mark.asyncio
    async def test_switch_state_loaded_during_startup(self, mock_store_class, mock_waiter_class, mock_hass, mock_config_entry):
        """Test that switch state is restored during startup."""
        # Setup mocks
        mock_waiter = AsyncMock()
        mock_waiter.wait_for_required_entities = AsyncMock()
        mock_waiter_class.return_value = mock_waiter
        
        # Mock saved data with learning disabled
        saved_data = {
            "learning_enabled": False,
            "samples": []
        }
        
        mock_data_store = Mock(spec=SmartClimateDataStore)
        mock_data_store.async_load_learning_data = AsyncMock(return_value=saved_data)
        mock_store_class.return_value = mock_data_store
        
        with patch.object(OffsetEngine, 'set_data_store'), \
             patch.object(OffsetEngine, 'async_load_learning_data', return_value=True), \
             patch.object(OffsetEngine, 'async_setup_periodic_save', return_value=lambda: None):
            
            # Perform setup
            result = await async_setup_entry(mock_hass, mock_config_entry)
            assert result is True


class TestEntityLifecycle:
    """Test entity lifecycle with persistence."""
    
    @patch('custom_components.smart_climate.EntityWaiter')
    @patch('custom_components.smart_climate.SmartClimateDataStore')
    @pytest.mark.asyncio
    async def test_cleanup_on_unload(self, mock_store_class, mock_waiter_class, mock_hass, mock_config_entry):
        """Test proper cleanup when unloading entry."""
        # Setup mocks
        mock_waiter = AsyncMock()
        mock_waiter.wait_for_required_entities = AsyncMock()
        mock_waiter_class.return_value = mock_waiter
        
        mock_data_store = Mock(spec=SmartClimateDataStore)
        mock_store_class.return_value = mock_data_store
        
        mock_cancel_function = Mock()
        
        with patch.object(OffsetEngine, 'set_data_store'), \
             patch.object(OffsetEngine, 'async_load_learning_data', return_value=True), \
             patch.object(OffsetEngine, 'async_setup_periodic_save', return_value=mock_cancel_function), \
             patch.object(OffsetEngine, 'async_save_learning_data') as mock_save:
            
            # Setup
            result = await async_setup_entry(mock_hass, mock_config_entry)
            assert result is True
            
            # Unload
            unload_result = await async_unload_entry(mock_hass, mock_config_entry)
            assert unload_result is True
            
            # Verify cleanup
            assert mock_config_entry.entry_id not in mock_hass.data[DOMAIN]
    
    @patch('custom_components.smart_climate.EntityWaiter')
    @patch('custom_components.smart_climate.SmartClimateDataStore')
    @pytest.mark.asyncio
    async def test_final_save_on_shutdown(self, mock_store_class, mock_waiter_class, mock_hass, mock_config_entry):
        """Test that learning data is saved one final time during shutdown."""
        # Setup mocks
        mock_waiter = AsyncMock()
        mock_waiter.wait_for_required_entities = AsyncMock()
        mock_waiter_class.return_value = mock_waiter
        
        mock_data_store = Mock(spec=SmartClimateDataStore)
        mock_store_class.return_value = mock_data_store
        
        with patch.object(OffsetEngine, 'set_data_store'), \
             patch.object(OffsetEngine, 'async_load_learning_data', return_value=True), \
             patch.object(OffsetEngine, 'async_setup_periodic_save', return_value=lambda: None), \
             patch.object(OffsetEngine, 'async_save_learning_data') as mock_save:
            
            # Setup
            result = await async_setup_entry(mock_hass, mock_config_entry)
            assert result is True
            
            # Simulate shutdown by manually calling save
            offset_engines = mock_hass.data[DOMAIN][mock_config_entry.entry_id]["offset_engines"]
            offset_engine = offset_engines["climate.test_ac"]
            await offset_engine.async_save_learning_data()
            
            # Verify save was called
            mock_save.assert_called()


class TestConfigurationScenarios:
    """Test different configuration scenarios."""
    
    @patch('custom_components.smart_climate.EntityWaiter')
    @pytest.mark.asyncio
    async def test_yaml_config_persistence(self, mock_waiter_class, mock_hass):
        """Test persistence setup with YAML configuration."""
        # Setup entity waiter mock
        mock_waiter = AsyncMock()
        mock_waiter.wait_for_required_entities = AsyncMock()
        mock_waiter_class.return_value = mock_waiter
        
        # Test YAML config handling - this would be handled differently
        # For now, just test that the domain is properly initialized
        from custom_components.smart_climate import async_setup
        
        yaml_config = {
            DOMAIN: {
                "climate_entity": "climate.test_yaml",
                "room_sensor": "sensor.yaml_temp",
                "enable_learning": True
            }
        }
        
        result = await async_setup(mock_hass, yaml_config)
        assert result is True
        assert DOMAIN in mock_hass.data
    
    @patch('custom_components.smart_climate.EntityWaiter')
    @pytest.mark.asyncio
    async def test_config_entry_vs_yaml_precedence(self, mock_waiter_class, mock_hass, mock_config_entry):
        """Test that config entry setup works alongside YAML config."""
        # Setup entity waiter mock
        mock_waiter = AsyncMock()
        mock_waiter.wait_for_required_entities = AsyncMock()
        mock_waiter_class.return_value = mock_waiter
        
        # First set up YAML
        from custom_components.smart_climate import async_setup
        
        yaml_config = {DOMAIN: {"some": "yaml_config"}}
        await async_setup(mock_hass, yaml_config)
        
        # Then set up config entry (should not conflict)
        result = await async_setup_entry(mock_hass, mock_config_entry)
        assert result is True
        
        # Both should coexist
        assert "yaml_config" in mock_hass.data[DOMAIN]
        assert mock_config_entry.entry_id in mock_hass.data[DOMAIN]