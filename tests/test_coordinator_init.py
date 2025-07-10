"""Test DataUpdateCoordinator implementation in __init__.py."""

import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import timedelta
import pytest
import sys
import os

# Add the test fixtures directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'fixtures'))

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.exceptions import HomeAssistantError
from custom_components.smart_climate.const import DOMAIN, PLATFORMS
from custom_components.smart_climate import async_setup_entry
from sensor_test_fixtures import create_mock_config_entry

# Create a real UpdateFailed exception for testing
class UpdateFailed(Exception):
    """Exception raised when update fails."""
    pass

# Create fixtures
@pytest.fixture
def hass():
    """Create a mock Home Assistant instance."""
    mock_hass = Mock()
    mock_hass.data = {}
    mock_hass.config_entries = Mock()
    mock_hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    mock_hass.services = Mock()
    mock_hass.services.has_service = Mock(return_value=False)
    return mock_hass

@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    return create_mock_config_entry()


@pytest.mark.asyncio
async def test_coordinator_added_to_entry_data(hass, mock_config_entry):
    """Test that coordinators dict is added to entry_data."""
    # Mock EntityWaiter to pass through quickly
    with patch("custom_components.smart_climate.EntityWaiter") as mock_waiter_class:
        mock_waiter = Mock()
        mock_waiter.wait_for_required_entities = AsyncMock()
        mock_waiter_class.return_value = mock_waiter
        
        # Mock platform forward setup
        with patch.object(hass.config_entries, "async_forward_entry_setups", return_value=True):
            # Mock service registration
            with patch("custom_components.smart_climate._async_register_services", new=AsyncMock()):
                # Setup entry
                result = await async_setup_entry(hass, mock_config_entry)
                
                assert result is True
                assert DOMAIN in hass.data
                assert mock_config_entry.entry_id in hass.data[DOMAIN]
                
                entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
                assert "coordinators" in entry_data
                assert isinstance(entry_data["coordinators"], dict)


@pytest.mark.asyncio
async def test_coordinator_created_for_each_entity(hass, mock_config_entry):
    """Test that a coordinator is created for each climate entity."""
    # Add climate entity to config
    mock_config_entry.data = {
        **mock_config_entry.data,
        "climate_entity": "climate.test_ac"
    }
    
    with patch("custom_components.smart_climate.EntityWaiter") as mock_waiter_class:
        mock_waiter = Mock()
        mock_waiter.wait_for_required_entities = AsyncMock()
        mock_waiter_class.return_value = mock_waiter
        
        with patch.object(hass.config_entries, "async_forward_entry_setups", return_value=True):
            with patch("custom_components.smart_climate._async_register_services", new=AsyncMock()):
                # Setup entry
                await async_setup_entry(hass, mock_config_entry)
                
                entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
                
                # Check coordinator was created for the entity
                assert "climate.test_ac" in entry_data["coordinators"]
                coordinator = entry_data["coordinators"]["climate.test_ac"]
                assert coordinator is not None
                # Check it has the expected attributes of a DataUpdateCoordinator
                assert hasattr(coordinator, 'name')
                assert hasattr(coordinator, 'update_interval')
                assert hasattr(coordinator, '_async_update_data')


@pytest.mark.asyncio
async def test_coordinator_configuration(hass, mock_config_entry):
    """Test that coordinator is configured correctly."""
    mock_config_entry.data = {
        **mock_config_entry.data,
        "climate_entity": "climate.test_ac"
    }
    
    with patch("custom_components.smart_climate.EntityWaiter") as mock_waiter_class:
        mock_waiter = Mock()
        mock_waiter.wait_for_required_entities = AsyncMock()
        mock_waiter_class.return_value = mock_waiter
        
        with patch.object(hass.config_entries, "async_forward_entry_setups", return_value=True):
            with patch("custom_components.smart_climate._async_register_services", new=AsyncMock()):
                # Create a custom coordinator class to track initialization
                class TestCoordinator:
                    def __init__(self, hass, logger, name, update_method, update_interval):
                        self.hass = hass
                        self.logger = logger
                        self.name = name
                        self.update_method = update_method
                        self.update_interval = update_interval
                        self.async_config_entry_first_refresh = AsyncMock()
                        self._async_update_data = update_method
                        
                # Patch DataUpdateCoordinator with our test class
                with patch("custom_components.smart_climate.DataUpdateCoordinator", TestCoordinator):
                    await async_setup_entry(hass, mock_config_entry)
                    
                    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
                    coordinator = entry_data["coordinators"]["climate.test_ac"]
                    
                    # Check coordinator configuration
                    assert coordinator.name == f"smart_climate_{mock_config_entry.entry_id}_climate.test_ac"
                    assert coordinator.update_interval == timedelta(seconds=30)


@pytest.mark.asyncio
async def test_coordinator_async_config_entry_first_refresh_called(hass, mock_config_entry):
    """Test that async_config_entry_first_refresh is called on coordinator."""
    mock_config_entry.data = {
        **mock_config_entry.data,
        "climate_entity": "climate.test_ac"
    }
    
    with patch("custom_components.smart_climate.EntityWaiter") as mock_waiter_class:
        mock_waiter = Mock()
        mock_waiter.wait_for_required_entities = AsyncMock()
        mock_waiter_class.return_value = mock_waiter
        
        with patch.object(hass.config_entries, "async_forward_entry_setups", return_value=True):
            with patch("custom_components.smart_climate._async_register_services", new=AsyncMock()):
                # Track async_config_entry_first_refresh calls
                refresh_called = []
                
                # Create a custom coordinator class that tracks method calls
                class TestCoordinator:
                    def __init__(self, hass, logger, name, update_method, update_interval):
                        self.hass = hass
                        self.logger = logger
                        self.name = name
                        self.update_method = update_method
                        self.update_interval = update_interval
                        self._async_update_data = update_method
                        
                    async def async_config_entry_first_refresh(self):
                        refresh_called.append(True)
                
                # Patch the DataUpdateCoordinator with our test class
                with patch("custom_components.smart_climate.DataUpdateCoordinator", TestCoordinator):
                    
                    await async_setup_entry(hass, mock_config_entry)
                    
                    # Verify first refresh was called
                    assert len(refresh_called) == 1
                    assert refresh_called[0] is True


@pytest.mark.asyncio 
async def test_coordinator_update_method_calls_offset_engine(hass, mock_config_entry):
    """Test that coordinator update method calls offset_engine.async_get_dashboard_data()."""
    mock_config_entry.data = {
        **mock_config_entry.data,
        "climate_entity": "climate.test_ac"
    }
    
    # Create mock offset engine
    mock_offset_engine = Mock()
    mock_offset_engine.async_get_dashboard_data = AsyncMock(return_value={
        "calculated_offset": 2.5,
        "learning_info": {"enabled": True, "samples": 50},
        "save_diagnostics": {"save_count": 10},
        "calibration_info": {"in_calibration": False}
    })
    
    with patch("custom_components.smart_climate.EntityWaiter") as mock_waiter_class:
        mock_waiter = Mock()
        mock_waiter.wait_for_required_entities = AsyncMock()
        mock_waiter_class.return_value = mock_waiter
        
        # Patch OffsetEngine creation to return our mock
        with patch("custom_components.smart_climate.OffsetEngine") as mock_engine_class:
            mock_engine_class.return_value = mock_offset_engine
            
            with patch.object(hass.config_entries, "async_forward_entry_setups", return_value=True):
                with patch("custom_components.smart_climate._async_register_services", new=AsyncMock()):
                    # Create a custom coordinator class that captures the update method
                    captured_update_method = None
                    
                    class TestCoordinator:
                        def __init__(self, hass, logger, name, update_method, update_interval):
                            nonlocal captured_update_method
                            self.hass = hass
                            self.logger = logger
                            self.name = name
                            self.update_method = update_method
                            self.update_interval = update_interval
                            self._async_update_data = update_method
                            self.async_config_entry_first_refresh = AsyncMock()
                            captured_update_method = update_method
                    
                    with patch("custom_components.smart_climate.DataUpdateCoordinator", TestCoordinator):
                        await async_setup_entry(hass, mock_config_entry)
                        
                        # Manually call the captured update method
                        data = await captured_update_method()
                        
                        # Verify it called offset engine
                        mock_offset_engine.async_get_dashboard_data.assert_called_once()
                        
                        # Verify it returns the data
                        assert data == {
                            "calculated_offset": 2.5,
                            "learning_info": {"enabled": True, "samples": 50},
                            "save_diagnostics": {"save_count": 10},
                            "calibration_info": {"in_calibration": False}
                        }


@pytest.mark.asyncio
async def test_coordinator_handles_update_failures(hass, mock_config_entry):
    """Test that coordinator handles failures in offset_engine gracefully."""
    mock_config_entry.data = {
        **mock_config_entry.data,
        "climate_entity": "climate.test_ac"
    }
    
    # Create mock offset engine that raises exception
    mock_offset_engine = Mock()
    mock_offset_engine.async_get_dashboard_data = AsyncMock(side_effect=Exception("Test error"))
    
    with patch("custom_components.smart_climate.EntityWaiter") as mock_waiter_class:
        mock_waiter = Mock()
        mock_waiter.wait_for_required_entities = AsyncMock()
        mock_waiter_class.return_value = mock_waiter
        
        with patch("custom_components.smart_climate.OffsetEngine") as mock_engine_class:
            mock_engine_class.return_value = mock_offset_engine
            
            with patch.object(hass.config_entries, "async_forward_entry_setups", return_value=True):
                with patch("custom_components.smart_climate._async_register_services", new=AsyncMock()):
                    # Create a custom coordinator class that captures the update method
                    captured_update_method = None
                    
                    class TestCoordinator:
                        def __init__(self, hass, logger, name, update_method, update_interval):
                            nonlocal captured_update_method
                            self.hass = hass
                            self.logger = logger
                            self.name = name
                            self.update_method = update_method
                            self.update_interval = update_interval
                            self._async_update_data = update_method
                            self.async_config_entry_first_refresh = AsyncMock()
                            captured_update_method = update_method
                    
                    with patch("custom_components.smart_climate.DataUpdateCoordinator", TestCoordinator):
                        await async_setup_entry(hass, mock_config_entry)
                        
                        # Patch UpdateFailed so our code can use the real exception
                        with patch("custom_components.smart_climate.UpdateFailed", UpdateFailed):
                            # Update should raise UpdateFailed
                            exception_raised = False
                            try:
                                await captured_update_method()
                            except UpdateFailed as exc:
                                exception_raised = True
                                # Check that UpdateFailed was raised with the right message
                                assert "Error fetching dashboard data: Test error" in str(exc)
                            
                            assert exception_raised, "Expected update method to raise UpdateFailed"


@pytest.mark.asyncio
async def test_multiple_climate_entities_create_multiple_coordinators(hass, mock_config_entry):
    """Test that multiple climate entities create multiple coordinators."""
    # Remove single entity and add multiple
    del mock_config_entry.data["climate_entity"]
    mock_config_entry.data["climate_entities"] = ["climate.ac1", "climate.ac2", "climate.ac3"]
    
    with patch("custom_components.smart_climate.EntityWaiter") as mock_waiter_class:
        mock_waiter = Mock()
        mock_waiter.wait_for_required_entities = AsyncMock()
        mock_waiter_class.return_value = mock_waiter
        
        with patch.object(hass.config_entries, "async_forward_entry_setups", return_value=True):
            with patch("custom_components.smart_climate._async_register_services", new=AsyncMock()):
                await async_setup_entry(hass, mock_config_entry)
                
                entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
                
                # Check all coordinators were created
                assert "climate.ac1" in entry_data["coordinators"]
                assert "climate.ac2" in entry_data["coordinators"]
                assert "climate.ac3" in entry_data["coordinators"]
                
                # Each should be a DataUpdateCoordinator
                for entity_id in ["climate.ac1", "climate.ac2", "climate.ac3"]:
                    coordinator = entry_data["coordinators"][entity_id]
                    assert coordinator is not None
                    assert hasattr(coordinator, 'name')
                    assert hasattr(coordinator, 'update_interval')