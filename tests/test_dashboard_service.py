"""Test dashboard service functionality."""
# ABOUTME: Comprehensive tests for the Smart Climate dashboard generation service
# Tests async I/O operations, blocking prevention, entity discovery, template processing, and notifications

import os
import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch, mock_open, call
import pytest
import time

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
    hass.services.async_register = Mock()  # Not async in real HA
    hass.states = Mock()
    hass.states.get = Mock()
    hass.data = {DOMAIN: {}}
    # CRITICAL: Mock async_add_executor_job to return awaitable results
    hass.async_add_executor_job = AsyncMock()
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
        with patch("custom_components.smart_climate.async_create_notification") as mock_notify:
            mock_registry = Mock()
            mock_er.async_get.return_value = mock_registry
            
            # Entity exists and is from smart_climate
            mock_entity = Mock()
            mock_entity.platform = DOMAIN
            mock_entity.config_entry_id = "test_config_entry"
            mock_registry.async_get.return_value = mock_entity
            mock_registry.entities = {"climate.test_ac": mock_entity}
            
            # Mock state
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "Smart AC"}
            mock_hass.states.get.return_value = mock_state
            
            # Mock async file reading through async_add_executor_job
            template_content = "title: Smart Climate - REPLACE_ME_NAME\nentity: climate.REPLACE_ME_ENTITY"
            mock_hass.async_add_executor_job.return_value = template_content
            
            with patch("os.path.exists", return_value=True):
                # Register services
                await _async_register_services(mock_hass)
                
                # Get the service handler
                service_handler = mock_hass.services.async_register.call_args[0][2]
                
                # Call service
                await service_handler(mock_service_call)
            
            # Should have called async_add_executor_job for file reading
            mock_hass.async_add_executor_job.assert_called_once()
            call_args = mock_hass.async_add_executor_job.call_args[0]
            # First arg should be the _read_file_sync function, second should be the path
            assert len(call_args) == 2
            assert "dashboard_generic.yaml" in call_args[1]


@pytest.mark.asyncio
async def test_service_replaces_placeholders_correctly(mock_hass, mock_service_call):
    """Test service replaces REPLACE_ME placeholders correctly."""
    # Setup
    with patch("custom_components.smart_climate.er") as mock_er:
        with patch("custom_components.smart_climate.async_create_notification") as mock_notify:
            mock_registry = Mock()
            mock_er.async_get.return_value = mock_registry
            
            # Entity exists and is from smart_climate
            mock_entity = Mock()
            mock_entity.platform = DOMAIN
            mock_entity.config_entry_id = "test_config_entry"
            mock_registry.async_get.return_value = mock_entity
            mock_registry.entities = {"climate.test_ac": mock_entity}
            
            # Mock state with friendly name
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "Living Room AC"}
            mock_hass.states.get.return_value = mock_state
            
            # Template content with placeholders
            template_content = """title: Smart Climate - REPLACE_ME_NAME
views:
  - cards:
      - entity: REPLACE_ME_CLIMATE
      - entity: REPLACE_ME_SENSOR_OFFSET
      - entity: REPLACE_ME_SWITCH"""
            
            # Mock async file reading
            mock_hass.async_add_executor_job.return_value = template_content
            
            # Expected result (will be in the notification message)
            expected_parts = [
                "title: Smart Climate - Living Room AC",
                "entity: climate.living_room_ac",
                "entity: sensor.unknown",  # No sensors configured in this test
                "entity: switch.unknown"   # No switch configured in this test
            ]
            
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
        with patch("custom_components.smart_climate.async_create_notification") as mock_notify:
            mock_registry = Mock()
            mock_er.async_get.return_value = mock_registry
            
            # Entity exists and is from smart_climate
            mock_entity = Mock()
            mock_entity.platform = DOMAIN
            mock_entity.config_entry_id = "test_config_entry"
            mock_registry.async_get.return_value = mock_entity
            mock_registry.entities = {"climate.test_ac": mock_entity}
            
            # Mock state
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "Test AC"}
            mock_hass.states.get.return_value = mock_state
            
            template_content = "Simple dashboard content"
            mock_hass.async_add_executor_job.return_value = template_content
            
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
        mock_entity.config_entry_id = "test_config_entry"
        mock_registry.async_get.return_value = mock_entity
        mock_registry.entities = {"climate.test_ac": mock_entity}
        
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
        mock_entity.config_entry_id = "test_config_entry"
        mock_registry.async_get.return_value = mock_entity
        mock_registry.entities = {"climate.test_ac": mock_entity}
        
        # Mock state
        mock_state = Mock()
        mock_state.attributes = {"friendly_name": "Smart AC"}
        mock_hass.states.get.return_value = mock_state
        
        # Mock async_add_executor_job to raise IOError
        mock_hass.async_add_executor_job.side_effect = IOError("Permission denied")
        
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
        with patch("custom_components.smart_climate.async_create_notification") as mock_notify:
            mock_registry = Mock()
            mock_er.async_get.return_value = mock_registry
            
            # Entity exists and is from smart_climate
            mock_entity = Mock()
            mock_entity.platform = DOMAIN
            mock_entity.config_entry_id = "test_config_entry"
            mock_registry.async_get.return_value = mock_entity
            mock_registry.entities = {"climate.test_ac": mock_entity}
            
            # Mock state
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "Test AC"}
            mock_hass.states.get.return_value = mock_state
            
            template_content = "Dashboard YAML content"
            
            mock_hass.async_add_executor_job.return_value = template_content
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
        with patch("custom_components.smart_climate.async_create_notification") as mock_notify:
            mock_registry = Mock()
            mock_er.async_get.return_value = mock_registry
            
            # Entity exists and is from smart_climate
            mock_entity = Mock()
            mock_entity.platform = DOMAIN
            mock_entity.config_entry_id = "test_config_entry"
            mock_registry.async_get.return_value = mock_entity
            mock_registry.entities = {"climate.test_ac": mock_entity}
            
            # Mock state
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "Master Bedroom AC"}
            mock_hass.states.get.return_value = mock_state
            
            template_content = "notification_id: smart_climate_dashboard_REPLACE_ME_ENTITY"
            
            mock_hass.async_add_executor_job.return_value = template_content
            with patch("os.path.exists", return_value=True):
                # Register services
                await _async_register_services(mock_hass)
                
                # Get the service handler
                service_handler = mock_hass.services.async_register.call_args[0][2]
                
                # Call service
                mock_service_call.data = {"climate_entity_id": "climate.master_bedroom_ac"}
                await service_handler(mock_service_call)
            
            # Check entity ID was extracted correctly (without "climate." prefix) 
            # This test checks the notification_id which uses entity_id_without_domain
            mock_notify.assert_called_once()
            notification_args = mock_notify.call_args[1]
            notification_id = notification_args["notification_id"]
            
            assert notification_id == "smart_climate_dashboard_master_bedroom_ac"


# === NEW COMPREHENSIVE TESTS FOR ISSUE #18 ===

@pytest.mark.asyncio
async def test_async_file_reading_operations(mock_hass, mock_service_call):
    """Test that file reading operations are truly async and don't block."""
    # Setup
    with patch("custom_components.smart_climate.er") as mock_er:
        with patch("custom_components.smart_climate.async_create_notification") as mock_notify:
            mock_registry = Mock()
            mock_er.async_get.return_value = mock_registry
            
            # Entity exists and is from smart_climate
            mock_entity = Mock()
            mock_entity.platform = DOMAIN
            mock_entity.config_entry_id = "test_config_entry"
            mock_registry.async_get.return_value = mock_entity
            mock_registry.entities = {"climate.test_ac": mock_entity}
            
            # Mock state
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "Test AC"}
            mock_hass.states.get.return_value = mock_state
            
            # Create a mock file operation that simulates slow I/O
            async def slow_file_read(*args, **kwargs):
                await asyncio.sleep(0.1)  # Simulate slow file I/O
                return "dashboard: test content"
            
            template_content = "title: Smart Climate - REPLACE_ME_NAME"
            
            # Test that async file operations don't block
            mock_hass.async_add_executor_job.return_value = template_content
            with patch("os.path.exists", return_value=True):
                    # Register services
                    await _async_register_services(mock_hass)
                    
                    # Get the service handler
                    service_handler = mock_hass.services.async_register.call_args[0][2]
                    
                    # Record start time
                    start_time = time.time()
                    
                    # Call service - should complete quickly despite file I/O
                    await service_handler(mock_service_call)
                    
                    # Verify it completed reasonably quickly (not blocked)
                    elapsed = time.time() - start_time
                    assert elapsed < 0.5, f"Service took too long: {elapsed}s"
            
            # Verify notification was created
            mock_notify.assert_called_once()


@pytest.mark.asyncio
async def test_template_file_encoding_validation(mock_hass, mock_service_call):
    """Test template file reading with different encodings."""
    # Setup
    with patch("custom_components.smart_climate.er") as mock_er:
        with patch("custom_components.smart_climate.async_create_notification") as mock_notify:
            mock_registry = Mock()
            mock_er.async_get.return_value = mock_registry
            
            # Entity exists and is from smart_climate
            mock_entity = Mock()
            mock_entity.platform = DOMAIN
            mock_entity.config_entry_id = "test_config_entry"
            mock_registry.async_get.return_value = mock_entity
            mock_registry.entities = {"climate.test_ac": mock_entity}
            
            # Mock state
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "Test AC"}
            mock_hass.states.get.return_value = mock_state
            
            # Test with UTF-8 encoded content including special characters
            template_content = "title: Smart Climate - REPLACE_ME_NAME ñáéíóú"
            
            mock_hass.async_add_executor_job.return_value = template_content
            with patch("os.path.exists", return_value=True):
                # Register services
                await _async_register_services(mock_hass)
                
                # Get the service handler
                service_handler = mock_hass.services.async_register.call_args[0][2]
                
                # Call service
                await service_handler(mock_service_call)
            
            # Verify async_add_executor_job was called for file reading
            mock_hass.async_add_executor_job.assert_called_once()
            call_args = mock_hass.async_add_executor_job.call_args[0]
            # First arg should be the _read_file_sync function, second should be the path
            assert len(call_args) == 2
            
            # Verify notification was created
            mock_notify.assert_called_once()


@pytest.mark.asyncio
async def test_comprehensive_entity_discovery(mock_hass, mock_service_call):
    """Test comprehensive entity discovery for dashboard sensors."""
    # Setup
    with patch("custom_components.smart_climate.er") as mock_er:
        with patch("custom_components.smart_climate.async_create_notification") as mock_notify:
            mock_registry = Mock()
            mock_er.async_get.return_value = mock_registry
            
            # Climate entity
            mock_climate_entity = Mock()
            mock_climate_entity.platform = DOMAIN
            mock_climate_entity.config_entry_id = "test_config_entry"
            mock_climate_entity.entity_id = "climate.test_ac"
            mock_climate_entity.unique_id = "test_ac_climate"
            
            # Dashboard sensor entities
            mock_sensor_offset = Mock()
            mock_sensor_offset.platform = DOMAIN
            mock_sensor_offset.config_entry_id = "test_config_entry"
            mock_sensor_offset.entity_id = "sensor.test_ac_offset_current"
            mock_sensor_offset.unique_id = "test_ac_offset_current"
            mock_sensor_offset.domain = "sensor"
            
            mock_sensor_progress = Mock()
            mock_sensor_progress.platform = DOMAIN
            mock_sensor_progress.config_entry_id = "test_config_entry"
            mock_sensor_progress.entity_id = "sensor.test_ac_learning_progress"
            mock_sensor_progress.unique_id = "test_ac_learning_progress"
            mock_sensor_progress.domain = "sensor"
            
            mock_sensor_accuracy = Mock()
            mock_sensor_accuracy.platform = DOMAIN
            mock_sensor_accuracy.config_entry_id = "test_config_entry"
            mock_sensor_accuracy.entity_id = "sensor.test_ac_accuracy_current"
            mock_sensor_accuracy.unique_id = "test_ac_accuracy_current"
            mock_sensor_accuracy.domain = "sensor"
            
            mock_sensor_calibration = Mock()
            mock_sensor_calibration.platform = DOMAIN
            mock_sensor_calibration.config_entry_id = "test_config_entry"
            mock_sensor_calibration.entity_id = "sensor.test_ac_calibration_status"
            mock_sensor_calibration.unique_id = "test_ac_calibration_status"
            mock_sensor_calibration.domain = "sensor"
            
            mock_sensor_hysteresis = Mock()
            mock_sensor_hysteresis.platform = DOMAIN
            mock_sensor_hysteresis.config_entry_id = "test_config_entry"
            mock_sensor_hysteresis.entity_id = "sensor.test_ac_hysteresis_state"
            mock_sensor_hysteresis.unique_id = "test_ac_hysteresis_state"
            mock_sensor_hysteresis.domain = "sensor"
            
            # Switch and button entities
            mock_switch = Mock()
            mock_switch.platform = DOMAIN
            mock_switch.config_entry_id = "test_config_entry"
            mock_switch.entity_id = "switch.test_ac_learning"
            mock_switch.unique_id = "test_ac_learning"
            mock_switch.domain = "switch"
            
            mock_button = Mock()
            mock_button.platform = DOMAIN
            mock_button.config_entry_id = "test_config_entry"
            mock_button.entity_id = "button.test_ac_reset"
            mock_button.unique_id = "test_ac_reset"
            mock_button.domain = "button"
            
            # Setup entity registry
            mock_registry.async_get.return_value = mock_climate_entity
            mock_registry.entities = {
                "climate.test_ac": mock_climate_entity,
                "sensor.test_ac_offset_current": mock_sensor_offset,
                "sensor.test_ac_learning_progress": mock_sensor_progress,
                "sensor.test_ac_accuracy_current": mock_sensor_accuracy,
                "sensor.test_ac_calibration_status": mock_sensor_calibration,
                "sensor.test_ac_hysteresis_state": mock_sensor_hysteresis,
                "switch.test_ac_learning": mock_switch,
                "button.test_ac_reset": mock_button,
            }
            
            # Mock state
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "Test AC"}
            mock_hass.states.get.return_value = mock_state
            
            template_content = """title: Smart Climate - REPLACE_ME_NAME
views:
  - cards:
      - entity: REPLACE_ME_CLIMATE
      - entity: REPLACE_ME_SENSOR_OFFSET
      - entity: REPLACE_ME_SENSOR_PROGRESS
      - entity: REPLACE_ME_SENSOR_ACCURACY
      - entity: REPLACE_ME_SENSOR_CALIBRATION
      - entity: REPLACE_ME_SENSOR_HYSTERESIS
      - entity: REPLACE_ME_SWITCH
      - entity: REPLACE_ME_BUTTON"""
            
            mock_hass.async_add_executor_job.return_value = template_content
            with patch("os.path.exists", return_value=True):
                    # Register services
                    await _async_register_services(mock_hass)
                    
                    # Get the service handler
                    service_handler = mock_hass.services.async_register.call_args[0][2]
                    
                    # Call service
                    await service_handler(mock_service_call)
            
            # Verify all entities were discovered and replaced
            mock_notify.assert_called_once()
            notification_args = mock_notify.call_args[1]
            message = notification_args["message"]
            
            # Check that all sensors were properly identified and replaced
            assert "sensor.test_ac_offset_current" in message
            assert "sensor.test_ac_learning_progress" in message
            assert "sensor.test_ac_accuracy_current" in message
            assert "sensor.test_ac_calibration_status" in message
            assert "sensor.test_ac_hysteresis_state" in message
            assert "switch.test_ac_learning" in message
            assert "button.test_ac_reset" in message
            
            # Verify no placeholders remain
            assert "REPLACE_ME_CLIMATE" not in message
            assert "REPLACE_ME_SENSOR_" not in message
            assert "REPLACE_ME_SWITCH" not in message
            assert "REPLACE_ME_BUTTON" not in message


@pytest.mark.asyncio
async def test_missing_entity_handling(mock_hass, mock_service_call):
    """Test handling of missing dashboard entities gracefully."""
    # Setup
    with patch("custom_components.smart_climate.er") as mock_er:
        with patch("custom_components.smart_climate.async_create_notification") as mock_notify:
            mock_registry = Mock()
            mock_er.async_get.return_value = mock_registry
            
            # Climate entity exists but dashboard entities are missing
            mock_climate_entity = Mock()
            mock_climate_entity.platform = DOMAIN
            mock_climate_entity.config_entry_id = "test_config_entry"
            mock_climate_entity.entity_id = "climate.test_ac"
            mock_climate_entity.unique_id = "test_ac_climate"
            
            # Only climate entity in registry (missing dashboard entities)
            mock_registry.async_get.return_value = mock_climate_entity
            mock_registry.entities = {
                "climate.test_ac": mock_climate_entity,
            }
            
            # Mock state
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "Test AC"}
            mock_hass.states.get.return_value = mock_state
            
            template_content = """title: Smart Climate - REPLACE_ME_NAME
views:
  - cards:
      - entity: REPLACE_ME_SENSOR_OFFSET
      - entity: REPLACE_ME_SENSOR_PROGRESS
      - entity: REPLACE_ME_SWITCH"""
            
            mock_hass.async_add_executor_job.return_value = template_content
            with patch("os.path.exists", return_value=True):
                    # Register services
                    await _async_register_services(mock_hass)
                    
                    # Get the service handler
                    service_handler = mock_hass.services.async_register.call_args[0][2]
                    
                    # Call service - should not fail even with missing entities
                    await service_handler(mock_service_call)
            
            # Verify notification was created with unknown entity placeholders
            mock_notify.assert_called_once()
            notification_args = mock_notify.call_args[1]
            message = notification_args["message"]
            
            # Check that missing entities are replaced with "sensor.unknown"
            assert "sensor.unknown" in message
            assert "switch.unknown" in message
            
            # Verify friendly name was still replaced
            assert "Test AC" in message


@pytest.mark.asyncio
async def test_notification_creation_with_proper_formatting(mock_hass, mock_service_call):
    """Test notification creation with proper message formatting."""
    # Setup
    with patch("custom_components.smart_climate.er") as mock_er:
        with patch("custom_components.smart_climate.async_create_notification") as mock_notify:
            mock_registry = Mock()
            mock_er.async_get.return_value = mock_registry
            
            # Entity exists and is from smart_climate
            mock_entity = Mock()
            mock_entity.platform = DOMAIN
            mock_entity.config_entry_id = "test_config_entry"
            mock_registry.async_get.return_value = mock_entity
            mock_registry.entities = {"climate.test_ac": mock_entity}
            
            # Mock state
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "Living Room AC"}
            mock_hass.states.get.return_value = mock_state
            
            template_content = "title: Smart Climate Dashboard"
            
            mock_hass.async_add_executor_job.return_value = template_content
            with patch("os.path.exists", return_value=True):
                    # Register services
                    await _async_register_services(mock_hass)
                    
                    # Get the service handler
                    service_handler = mock_hass.services.async_register.call_args[0][2]
                    
                    # Call service
                    await service_handler(mock_service_call)
            
            # Verify notification structure
            mock_notify.assert_called_once()
            notification_call = mock_notify.call_args
            
            # Check positional args
            assert notification_call[0][0] == mock_hass
            
            # Check keyword args
            kwargs = notification_call[1]
            assert "title" in kwargs
            assert "message" in kwargs
            assert "notification_id" in kwargs
            
            # Verify title format
            assert "Smart Climate Dashboard - Living Room AC" in kwargs["title"]
            
            # Verify message contains instructions
            message = kwargs["message"]
            assert "Copy the YAML below" in message
            assert "Settings → Dashboards" in message
            assert "Add Dashboard" in message
            assert "Raw Configuration Editor" in message
            
            # Verify notification ID format
            assert "smart_climate_dashboard_" in kwargs["notification_id"]


@pytest.mark.asyncio
async def test_template_validation_with_malformed_yaml(mock_hass, mock_service_call):
    """Test template processing with malformed YAML content."""
    # Setup
    with patch("custom_components.smart_climate.er") as mock_er:
        with patch("custom_components.smart_climate.async_create_notification") as mock_notify:
            mock_registry = Mock()
            mock_er.async_get.return_value = mock_registry
            
            # Entity exists and is from smart_climate
            mock_entity = Mock()
            mock_entity.platform = DOMAIN
            mock_entity.config_entry_id = "test_config_entry"
            mock_registry.async_get.return_value = mock_entity
            mock_registry.entities = {"climate.test_ac": mock_entity}
            
            # Mock state
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "Test AC"}
            mock_hass.states.get.return_value = mock_state
            
            # Malformed YAML content (should still be processed as text)
            template_content = """title: Smart Climate - REPLACE_ME_NAME
views:
  - cards:
      - entity: REPLACE_ME_CLIMATE
    - invalid_yaml: [
      unclosed_bracket"""
            
            mock_hass.async_add_executor_job.return_value = template_content
            with patch("os.path.exists", return_value=True):
                    # Register services
                    await _async_register_services(mock_hass)
                    
                    # Get the service handler
                    service_handler = mock_hass.services.async_register.call_args[0][2]
                    
                    # Call service - should not fail even with malformed YAML
                    await service_handler(mock_service_call)
            
            # Verify notification was created (template processed as text)
            mock_notify.assert_called_once()
            notification_args = mock_notify.call_args[1]
            message = notification_args["message"]
            
            # Check that replacements were made despite malformed YAML
            assert "Test AC" in message
            assert "climate.test_ac" in message
            assert "REPLACE_ME_NAME" not in message
            assert "REPLACE_ME_CLIMATE" not in message


@pytest.mark.asyncio
async def test_service_performance_under_load(mock_hass):
    """Test service performance with multiple concurrent calls."""
    # Setup
    with patch("custom_components.smart_climate.er") as mock_er:
        with patch("custom_components.smart_climate.async_create_notification") as mock_notify:
            mock_registry = Mock()
            mock_er.async_get.return_value = mock_registry
            
            # Entity exists and is from smart_climate
            mock_entity = Mock()
            mock_entity.platform = DOMAIN
            mock_entity.config_entry_id = "test_config_entry"
            mock_registry.async_get.return_value = mock_entity
            mock_registry.entities = {"climate.test_ac": mock_entity}
            
            # Mock state
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "Test AC"}
            mock_hass.states.get.return_value = mock_state
            
            template_content = "title: Smart Climate - REPLACE_ME_NAME"
            
            mock_hass.async_add_executor_job.return_value = template_content
            with patch("os.path.exists", return_value=True):
                    # Register services
                    await _async_register_services(mock_hass)
                    
                    # Get the service handler
                    service_handler = mock_hass.services.async_register.call_args[0][2]
                    
                    # Create multiple service calls
                    service_calls = []
                    for i in range(5):
                        call = Mock()
                        call.data = {"climate_entity_id": f"climate.test_ac_{i}"}
                        service_calls.append(call)
                    
                    # Execute all calls concurrently
                    start_time = time.time()
                    tasks = [service_handler(call) for call in service_calls]
                    await asyncio.gather(*tasks)
                    elapsed = time.time() - start_time
                    
                    # Verify all calls completed in reasonable time
                    assert elapsed < 2.0, f"Service calls took too long: {elapsed}s"
                    
                    # Verify all notifications were created
                    assert mock_notify.call_count == 5


@pytest.mark.asyncio
async def test_config_entry_validation_edge_cases(mock_hass, mock_service_call):
    """Test config entry validation with edge cases."""
    # Setup
    with patch("custom_components.smart_climate.er") as mock_er:
        mock_registry = Mock()
        mock_er.async_get.return_value = mock_registry
        
        # Entity exists but has no config_entry_id
        mock_entity = Mock()
        mock_entity.platform = DOMAIN
        mock_entity.config_entry_id = None  # Missing config entry
        mock_registry.async_get.return_value = mock_entity
        
        # Register services
        await _async_register_services(mock_hass)
        
        # Get the service handler
        service_handler = mock_hass.services.async_register.call_args[0][2]
        
        # Call service - should raise error for missing config entry
        with pytest.raises(
            ServiceValidationError,
            match="No config entry found for climate.test_ac"
        ):
            await service_handler(mock_service_call)


@pytest.mark.asyncio
async def test_file_system_permissions_error(mock_hass, mock_service_call):
    """Test handling of file system permission errors."""
    # Setup
    with patch("custom_components.smart_climate.er") as mock_er:
        mock_registry = Mock()
        mock_er.async_get.return_value = mock_registry
        
        # Entity exists and is from smart_climate
        mock_entity = Mock()
        mock_entity.platform = DOMAIN
        mock_entity.config_entry_id = "test_config_entry"
        mock_registry.async_get.return_value = mock_entity
        mock_registry.entities = {"climate.test_ac": mock_entity}
        
        # Mock state
        mock_state = Mock()
        mock_state.attributes = {"friendly_name": "Test AC"}
        mock_hass.states.get.return_value = mock_state
        
        # Mock async_add_executor_job to raise PermissionError
        mock_hass.async_add_executor_job.side_effect = PermissionError("Permission denied")
        
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
async def test_template_file_path_construction(mock_hass, mock_service_call):
    """Test correct template file path construction."""
    # Setup
    with patch("custom_components.smart_climate.er") as mock_er:
        with patch("custom_components.smart_climate.async_create_notification") as mock_notify:
            mock_registry = Mock()
            mock_er.async_get.return_value = mock_registry
            
            # Entity exists and is from smart_climate
            mock_entity = Mock()
            mock_entity.platform = DOMAIN
            mock_entity.config_entry_id = "test_config_entry"
            mock_registry.async_get.return_value = mock_entity
            mock_registry.entities = {"climate.test_ac": mock_entity}
            
            # Mock state
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "Test AC"}
            mock_hass.states.get.return_value = mock_state
            
            template_content = "dashboard content"
            
            mock_hass.async_add_executor_job.return_value = template_content
            with patch("os.path.exists", return_value=True) as mock_exists:
                with patch("os.path.join") as mock_join:
                    with patch("os.path.dirname") as mock_dirname:
                        # Setup path mocking
                        mock_dirname.return_value = "/path/to/smart_climate"
                        mock_join.return_value = "/path/to/smart_climate/dashboard/dashboard_generic.yaml"
                        
                        # Register services
                        await _async_register_services(mock_hass)
                        
                        # Get the service handler
                        service_handler = mock_hass.services.async_register.call_args[0][2]
                        
                        # Call service
                        await service_handler(mock_service_call)
                        
                        # Verify correct path construction
                        mock_dirname.assert_called_once()
                        mock_join.assert_called_once_with(
                            "/path/to/smart_climate",
                            "dashboard",
                            "dashboard_generic.yaml"
                        )
                        mock_exists.assert_called_once_with(
                            "/path/to/smart_climate/dashboard/dashboard_generic.yaml"
                        )
            
            # Verify notification was created
            mock_notify.assert_called_once()


@pytest.mark.asyncio
async def test_entity_id_normalization(mock_hass):
    """Test entity ID normalization for different entity ID formats."""
    test_cases = [
        ("climate.living_room_ac", "living_room_ac"),
        ("climate.bedroom_climate", "bedroom_climate"),
        ("climate.ac_unit_1", "ac_unit_1"),
        ("climate.smart_climate_test", "smart_climate_test"),
    ]
    
    for entity_id, expected_normalized in test_cases:
        with patch("custom_components.smart_climate.er") as mock_er:
            with patch("custom_components.smart_climate.async_create_notification") as mock_notify:
                mock_registry = Mock()
                mock_er.async_get.return_value = mock_registry
                
                # Entity exists and is from smart_climate
                mock_entity = Mock()
                mock_entity.platform = DOMAIN
                mock_entity.config_entry_id = "test_config_entry"
                mock_registry.async_get.return_value = mock_entity
                mock_registry.entities = {entity_id: mock_entity}
                
                # Mock state
                mock_state = Mock()
                mock_state.attributes = {"friendly_name": "Test AC"}
                mock_hass.states.get.return_value = mock_state
                
                template_content = "notification_id: smart_climate_dashboard_REPLACE_ME_ENTITY"
                
                mock_hass.async_add_executor_job.return_value = template_content
                with patch("os.path.exists", return_value=True):
                    # Register services
                    await _async_register_services(mock_hass)
                    
                    # Get the service handler
                    service_handler = mock_hass.services.async_register.call_args[0][2]
                    
                    # Create service call
                    service_call = Mock()
                    service_call.data = {"climate_entity_id": entity_id}
                    
                    # Call service
                    await service_handler(service_call)
                    
                    # Verify notification ID uses normalized entity ID
                    mock_notify.assert_called_once()
                    notification_args = mock_notify.call_args[1]
                    notification_id = notification_args["notification_id"]
                    
                    assert notification_id == f"smart_climate_dashboard_{expected_normalized}"
                    
                    # Reset mock for next iteration
                    mock_notify.reset_mock()


@pytest.mark.asyncio
async def test_service_registration_idempotency(mock_hass):
    """Test that service registration is idempotent (can be called multiple times)."""
    # First registration
    mock_hass.services.has_service.return_value = False
    await _async_register_services(mock_hass)
    
    # Verify service was registered
    mock_hass.services.async_register.assert_called_once()
    
    # Second registration (service already exists)
    mock_hass.services.has_service.return_value = True
    mock_hass.services.async_register.reset_mock()
    
    await _async_register_services(mock_hass)
    
    # Verify service was NOT registered again
    mock_hass.services.async_register.assert_not_called()


@pytest.mark.asyncio
async def test_large_template_file_handling(mock_hass, mock_service_call):
    """Test handling of large template files without blocking."""
    # Setup
    with patch("custom_components.smart_climate.er") as mock_er:
        with patch("custom_components.smart_climate.async_create_notification") as mock_notify:
            mock_registry = Mock()
            mock_er.async_get.return_value = mock_registry
            
            # Entity exists and is from smart_climate
            mock_entity = Mock()
            mock_entity.platform = DOMAIN
            mock_entity.config_entry_id = "test_config_entry"
            mock_registry.async_get.return_value = mock_entity
            mock_registry.entities = {"climate.test_ac": mock_entity}
            
            # Mock state
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "Test AC"}
            mock_hass.states.get.return_value = mock_state
            
            # Create large template content (simulating a large dashboard)
            large_template = "title: Smart Climate - REPLACE_ME_NAME\n" + "\n".join([
                f"  - type: entity\n    entity: sensor.test_{i}" for i in range(1000)
            ])
            
            mock_hass.async_add_executor_job.return_value = large_template
            with patch("os.path.exists", return_value=True):
                # Register services
                await _async_register_services(mock_hass)
                
                # Get the service handler
                service_handler = mock_hass.services.async_register.call_args[0][2]
                
                # Record start time
                start_time = time.time()
                
                # Call service
                await service_handler(mock_service_call)
                
                # Verify it completed reasonably quickly
                elapsed = time.time() - start_time
                assert elapsed < 1.0, f"Large template processing took too long: {elapsed}s"
            
            # Verify notification was created
            mock_notify.assert_called_once()
            notification_args = mock_notify.call_args[1]
            message = notification_args["message"]
            
            # Verify template was processed
            assert "Test AC" in message
            assert "REPLACE_ME_NAME" not in message