"""Test dashboard service functionality."""
# ABOUTME: Tests for the Smart Climate dashboard generation service
# Validates service registration, entity validation, template processing, and notifications

import os
from unittest.mock import AsyncMock, MagicMock, Mock, patch, mock_open, call
import pytest

# Define mock exception class
class ServiceValidationError(Exception):
    """Mock ServiceValidationError."""
    pass

# Mock homeassistant exceptions module
import sys
if 'homeassistant.exceptions' not in sys.modules:
    sys.modules['homeassistant.exceptions'] = Mock()
sys.modules['homeassistant.exceptions'].ServiceValidationError = ServiceValidationError

from custom_components.smart_climate import (
    DOMAIN,
    _async_register_services,
)
from custom_components.smart_climate.const import (
    CONF_CLIMATE_ENTITY,
    CONF_ROOM_SENSOR,
)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.services = Mock()
    hass.services.has_service = Mock(return_value=False)
    hass.services.async_register = AsyncMock()
    hass.states = Mock()
    hass.states.get = Mock()
    hass.data = {DOMAIN: {}}
    return hass


@pytest.fixture
def mock_entity_registry():
    """Create a mock entity registry."""
    registry = Mock()
    return registry


@pytest.fixture
def mock_service_call():
    """Create a mock service call."""
    call = Mock()
    call.data = {"climate_entity_id": "climate.test_ac"}
    return call


@pytest.mark.asyncio
async def test_service_registration(mock_hass):
    """Test that generate_dashboard service is registered."""
    # Register services
    await _async_register_services(mock_hass)
    
    # Check service is registered
    mock_hass.services.async_register.assert_called_once()
    call_args = mock_hass.services.async_register.call_args
    
    assert call_args[0][0] == DOMAIN
    assert call_args[0][1] == "generate_dashboard"
    assert callable(call_args[0][2])  # Service handler


@pytest.mark.asyncio
async def test_service_validates_entity_exists(mock_hass, mock_service_call):
    """Test service validates that the climate entity exists."""
    # Setup
    with patch("custom_components.smart_climate.er") as mock_er:
        mock_registry = Mock()
        mock_er.async_get.return_value = mock_registry
        mock_registry.async_get.return_value = None  # Entity not found
        
        # Register services
        await _async_register_services(mock_hass)
        
        # Get the service handler
        service_handler = mock_hass.services.async_register.call_args[0][2]
        
        # Call with non-existent entity
        mock_service_call.data = {"climate_entity_id": "climate.nonexistent"}
        
        # Should raise error
        with pytest.raises(ServiceValidationError, match="Entity climate.nonexistent not found"):
            await service_handler(mock_service_call)


@pytest.mark.asyncio
async def test_service_validates_entity_is_smart_climate(mock_hass, mock_service_call):
    """Test service validates that entity belongs to smart_climate integration."""
    # Setup
    with patch("custom_components.smart_climate.er") as mock_er:
        mock_registry = Mock()
        mock_er.async_get.return_value = mock_registry
        
        # Entity exists but from different integration
        mock_entity = Mock()
        mock_entity.platform = "other_integration"
        mock_registry.async_get.return_value = mock_entity
        
        # Register services
        await _async_register_services(mock_hass)
        
        # Get the service handler
        service_handler = mock_hass.services.async_register.call_args[0][2]
        
        # Call with non-smart_climate entity
        mock_service_call.data = {"climate_entity_id": "climate.other_ac"}
        
        # Should raise error
        with pytest.raises(
            ServiceValidationError,
            match="Entity climate.other_ac is not a Smart Climate entity"
        ):
            await service_handler(mock_service_call)


@pytest.mark.asyncio
async def test_service_reads_template_file(mock_hass, mock_service_call):
    """Test service reads the dashboard template file."""
    # Setup
    with patch("custom_components.smart_climate.er") as mock_er:
        with patch("custom_components.smart_climate.async_create_notification", new_callable=AsyncMock) as mock_notify:
            mock_registry = Mock()
            mock_er.async_get.return_value = mock_registry
            
            # Entity exists and is from smart_climate
            mock_entity = Mock()
            mock_entity.platform = DOMAIN
            mock_registry.async_get.return_value = mock_entity
            
            # Mock state
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "Smart AC"}
            mock_hass.states.get.return_value = mock_state
            
            # Mock file reading
            template_content = "title: Smart Climate - REPLACE_ME_NAME\nentity: climate.REPLACE_ME_ENTITY"
            mock_file = mock_open(read_data=template_content)
            
            with patch("builtins.open", mock_file):
                with patch("os.path.exists", return_value=True):
                    # Register services
                    await _async_register_services(mock_hass)
                    
                    # Get the service handler
                    service_handler = mock_hass.services.async_register.call_args[0][2]
                    
                    # Call service
                    await service_handler(mock_service_call)
            
            # Should have tried to open the template file
            # The open call should include the dashboard path
            open_calls = mock_file.call_args_list
            assert any("dashboard.yaml" in str(call) for call in open_calls)


@pytest.mark.asyncio
async def test_service_replaces_placeholders_correctly(mock_hass, mock_service_call):
    """Test service replaces REPLACE_ME placeholders correctly."""
    # Setup
    with patch("custom_components.smart_climate.er") as mock_er:
        with patch("custom_components.smart_climate.async_create_notification", new_callable=AsyncMock) as mock_notify:
            mock_registry = Mock()
            mock_er.async_get.return_value = mock_registry
            
            # Entity exists and is from smart_climate
            mock_entity = Mock()
            mock_entity.platform = DOMAIN
            mock_registry.async_get.return_value = mock_entity
            
            # Mock state with friendly name
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "Living Room AC"}
            mock_hass.states.get.return_value = mock_state
            
            # Template content with placeholders
            template_content = """title: Smart Climate - REPLACE_ME_NAME
views:
  - cards:
      - entity: climate.REPLACE_ME_ENTITY
      - entity: sensor.REPLACE_ME_ENTITY_offset_current
      - entity: switch.REPLACE_ME_ENTITY_learning"""
            
            # Expected result (will be in the notification message)
            expected_parts = [
                "title: Smart Climate - Living Room AC",
                "entity: climate.living_room_ac",
                "entity: sensor.living_room_ac_offset_current",
                "entity: switch.living_room_ac_learning"
            ]
            
            with patch("builtins.open", mock_open(read_data=template_content)):
                with patch("os.path.exists", return_value=True):
                    # Register services
                    await _async_register_services(mock_hass)
                    
                    # Get the service handler
                    service_handler = mock_hass.services.async_register.call_args[0][2]
                    
                    # Call service with living_room_ac entity
                    mock_service_call.data = {"climate_entity_id": "climate.living_room_ac"}
                    await service_handler(mock_service_call)
            
            # Check notification was called with correct replacements
            mock_notify.assert_called_once()
            notification_args = mock_notify.call_args[1]
            message = notification_args["message"]
            
            # Verify all replacements were made
            for expected_part in expected_parts:
                assert expected_part in message
            
            # Verify placeholders were replaced
            assert "REPLACE_ME_NAME" not in message
            assert "REPLACE_ME_ENTITY" not in message


@pytest.mark.asyncio
async def test_service_sends_persistent_notification(mock_hass, mock_service_call):
    """Test service sends dashboard via persistent notification."""
    # Setup
    with patch("custom_components.smart_climate.er") as mock_er:
        with patch("custom_components.smart_climate.async_create_notification", new_callable=AsyncMock) as mock_notify:
            mock_registry = Mock()
            mock_er.async_get.return_value = mock_registry
            
            # Entity exists and is from smart_climate
            mock_entity = Mock()
            mock_entity.platform = DOMAIN
            mock_registry.async_get.return_value = mock_entity
            
            # Mock state
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "Test AC"}
            mock_hass.states.get.return_value = mock_state
            
            template_content = "Simple dashboard content"
            
            with patch("builtins.open", mock_open(read_data=template_content)):
                with patch("os.path.exists", return_value=True):
                    # Register services
                    await _async_register_services(mock_hass)
                    
                    # Get the service handler
                    service_handler = mock_hass.services.async_register.call_args[0][2]
                    
                    # Call service
                    await service_handler(mock_service_call)
            
            # Verify notification was sent
            mock_notify.assert_called_once()
            notification_args = mock_notify.call_args
            
            # Check notification parameters
            assert notification_args[0][0] == mock_hass  # hass instance
            assert "title" in notification_args[1]
            assert "message" in notification_args[1]
            assert "notification_id" in notification_args[1]


@pytest.mark.asyncio
async def test_service_handles_missing_template_file(mock_hass, mock_service_call):
    """Test service handles missing template file gracefully."""
    # Setup
    with patch("custom_components.smart_climate.er") as mock_er:
        mock_registry = Mock()
        mock_er.async_get.return_value = mock_registry
        
        # Entity exists and is from smart_climate
        mock_entity = Mock()
        mock_entity.platform = DOMAIN
        mock_registry.async_get.return_value = mock_entity
        
        # Mock state
        mock_state = Mock()
        mock_state.attributes = {"friendly_name": "Smart AC"}
        mock_hass.states.get.return_value = mock_state
        
        with patch("os.path.exists", return_value=False):
            # Register services
            await _async_register_services(mock_hass)
            
            # Get the service handler
            service_handler = mock_hass.services.async_register.call_args[0][2]
            
            # Call service - should raise error
            with pytest.raises(
                ServiceValidationError,
                match="Dashboard template file not found"
            ):
                await service_handler(mock_service_call)


@pytest.mark.asyncio
async def test_service_handles_template_read_error(mock_hass, mock_service_call):
    """Test service handles template file read errors."""
    # Setup
    with patch("custom_components.smart_climate.er") as mock_er:
        mock_registry = Mock()
        mock_er.async_get.return_value = mock_registry
        
        # Entity exists and is from smart_climate
        mock_entity = Mock()
        mock_entity.platform = DOMAIN
        mock_registry.async_get.return_value = mock_entity
        
        # Mock state
        mock_state = Mock()
        mock_state.attributes = {"friendly_name": "Smart AC"}
        mock_hass.states.get.return_value = mock_state
        
        with patch("builtins.open", side_effect=IOError("Permission denied")):
            with patch("os.path.exists", return_value=True):
                # Register services
                await _async_register_services(mock_hass)
                
                # Get the service handler
                service_handler = mock_hass.services.async_register.call_args[0][2]
                
                # Call service - should raise error
                with pytest.raises(
                    ServiceValidationError,
                    match="Failed to read dashboard template"
                ):
                    await service_handler(mock_service_call)


@pytest.mark.asyncio
async def test_service_includes_usage_instructions(mock_hass, mock_service_call):
    """Test service includes usage instructions in notification."""
    # Setup
    with patch("custom_components.smart_climate.er") as mock_er:
        with patch("custom_components.smart_climate.async_create_notification", new_callable=AsyncMock) as mock_notify:
            mock_registry = Mock()
            mock_er.async_get.return_value = mock_registry
            
            # Entity exists and is from smart_climate
            mock_entity = Mock()
            mock_entity.platform = DOMAIN
            mock_registry.async_get.return_value = mock_entity
            
            # Mock state
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "Test AC"}
            mock_hass.states.get.return_value = mock_state
            
            template_content = "Dashboard YAML content"
            
            with patch("builtins.open", mock_open(read_data=template_content)):
                with patch("os.path.exists", return_value=True):
                    # Register services
                    await _async_register_services(mock_hass)
                    
                    # Get the service handler
                    service_handler = mock_hass.services.async_register.call_args[0][2]
                    
                    # Call service
                    await service_handler(mock_service_call)
            
            # Check notification includes instructions
            mock_notify.assert_called_once()
            notification_args = mock_notify.call_args[1]
            message = notification_args["message"]
            
            assert "Dashboard YAML content" in message
            assert "Copy the YAML below" in message
            assert "Go to Settings" in message
            assert "Add Dashboard" in message


@pytest.mark.asyncio
async def test_service_entity_id_without_domain(mock_hass, mock_service_call):
    """Test service correctly extracts entity ID without domain for replacements."""
    # Setup
    with patch("custom_components.smart_climate.er") as mock_er:
        with patch("custom_components.smart_climate.async_create_notification", new_callable=AsyncMock) as mock_notify:
            mock_registry = Mock()
            mock_er.async_get.return_value = mock_registry
            
            # Entity exists and is from smart_climate
            mock_entity = Mock()
            mock_entity.platform = DOMAIN
            mock_registry.async_get.return_value = mock_entity
            
            # Mock state
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "Master Bedroom AC"}
            mock_hass.states.get.return_value = mock_state
            
            template_content = "sensor.REPLACE_ME_ENTITY_offset_current"
            
            with patch("builtins.open", mock_open(read_data=template_content)):
                with patch("os.path.exists", return_value=True):
                    # Register services
                    await _async_register_services(mock_hass)
                    
                    # Get the service handler
                    service_handler = mock_hass.services.async_register.call_args[0][2]
                    
                    # Call service
                    mock_service_call.data = {"climate_entity_id": "climate.master_bedroom_ac"}
                    await service_handler(mock_service_call)
            
            # Check entity ID was extracted correctly (without "climate." prefix)
            mock_notify.assert_called_once()
            notification_args = mock_notify.call_args[1]
            message = notification_args["message"]
            
            assert "sensor.master_bedroom_ac_offset_current" in message
            assert "sensor.REPLACE_ME_ENTITY" not in message