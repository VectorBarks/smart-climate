"""Test dashboard service enhancement for user-configured sensor placeholders."""

import pytest
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from homeassistant.exceptions import ServiceValidationError
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import os
from custom_components.smart_climate import DOMAIN


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    hass = Mock()
    hass.config = Mock()
    hass.config.config_dir = "/test/config"
    hass.states = Mock()
    hass.data = {DOMAIN: {}}
    hass.async_add_executor_job = AsyncMock()
    return hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    config_entry = Mock()
    config_entry.entry_id = "test_entry_id"
    config_entry.data = {
        "room_sensor": "sensor.living_room_temp",
        "outdoor_sensor": "sensor.outdoor_temp", 
        "power_sensor": "sensor.ac_power",
        "climate_entity": "climate.climia",
        "name": "My Smart Climate"
    }
    return config_entry


@pytest.fixture
def mock_entity_registry(mock_config_entry):
    """Create a mock entity registry."""
    registry = Mock()
    
    # Mock climate entity
    climate_entity = Mock()
    climate_entity.config_entry_id = mock_config_entry.entry_id
    climate_entity.platform = DOMAIN
    climate_entity.entity_id = "climate.smart_climia"
    registry.async_get.return_value = climate_entity
    
    # Mock related entities
    registry.entities = {
        "sensor.smart_climia_offset_current": Mock(
            config_entry_id=mock_config_entry.entry_id,
            domain="sensor",
            platform=DOMAIN,
            unique_id="smart_climia_offset_current",
            entity_id="sensor.smart_climia_offset_current"
        ),
        "switch.smart_climia_learning": Mock(
            config_entry_id=mock_config_entry.entry_id,
            domain="switch", 
            platform=DOMAIN,
            unique_id="smart_climia_learning",
            entity_id="switch.smart_climia_learning"
        ),
        "button.smart_climia_reset": Mock(
            config_entry_id=mock_config_entry.entry_id,
            domain="button",
            platform=DOMAIN, 
            unique_id="smart_climia_reset",
            entity_id="button.smart_climia_reset"
        )
    }
    
    return registry


@pytest.fixture 
def mock_dashboard_template():
    """Mock dashboard template content with placeholders."""
    return """
title: Smart Climate - REPLACE_ME_NAME
views:
  - title: Overview
    cards:
      - type: thermostat
        entity: REPLACE_ME_CLIMATE
      - type: entities
        entities:
          - REPLACE_ME_ROOM_SENSOR
          - REPLACE_ME_OUTDOOR_SENSOR  
          - REPLACE_ME_POWER_SENSOR
          - REPLACE_ME_SENSOR_OFFSET
          - REPLACE_ME_SWITCH
          - REPLACE_ME_BUTTON
"""


class TestDashboardServiceSensorPlaceholders:
    """Test dashboard service enhancement for sensor placeholders."""

    @pytest.mark.asyncio
    async def test_dashboard_service_replaces_room_sensor_placeholder(
        self, mock_hass, mock_config_entry, mock_entity_registry, mock_dashboard_template
    ):
        """Test that REPLACE_ME_ROOM_SENSOR is replaced with configured room sensor."""
        # Setup mocks
        with patch("custom_components.smart_climate.er.async_get", return_value=mock_entity_registry), \
             patch("os.path.exists", return_value=True), \
             patch("custom_components.smart_climate._read_file_sync", return_value=mock_dashboard_template), \
             patch("custom_components.smart_climate.async_create_notification") as mock_notification:
            
            # Setup config entries mock
            mock_entries_instance = Mock()
            mock_entries_instance.async_get_entry.return_value = mock_config_entry
            mock_hass.config_entries = mock_entries_instance
            
            # Setup state mock
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "My Smart Climate"}
            mock_hass.states.get.return_value = mock_state
            
            # Register the service and call it
            from custom_components.smart_climate import _async_register_services
            await _async_register_services(mock_hass)
            
            # Call the service
            await mock_hass.services.async_call(
                DOMAIN, "generate_dashboard", {"climate_entity_id": "climate.smart_climia"}
            )
            
            # Verify notification was called
            mock_notification.assert_called_once()
            notification_args = mock_notification.call_args[1]
            dashboard_yaml = notification_args["message"]
            
            # Verify room sensor placeholder was replaced
            assert "REPLACE_ME_ROOM_SENSOR" not in dashboard_yaml
            assert "sensor.living_room_temp" in dashboard_yaml

    @pytest.mark.asyncio
    async def test_dashboard_service_replaces_outdoor_sensor_placeholder(
        self, mock_hass, mock_config_entry, mock_entity_registry, mock_dashboard_template
    ):
        """Test that REPLACE_ME_OUTDOOR_SENSOR is replaced with configured outdoor sensor."""
        # Setup mocks (same as above test)
        with patch("custom_components.smart_climate.er.async_get", return_value=mock_entity_registry), \
             patch("os.path.exists", return_value=True), \
             patch("custom_components.smart_climate._read_file_sync", return_value=mock_dashboard_template), \
             patch("custom_components.smart_climate.async_create_notification") as mock_notification:
            
            mock_entries_instance = Mock()
            mock_entries_instance.async_get_entry.return_value = mock_config_entry
            mock_hass.config_entries = mock_entries_instance
            
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "My Smart Climate"}
            mock_hass.states.get.return_value = mock_state
            
            from custom_components.smart_climate import handle_generate_dashboard
            call = ServiceCall(DOMAIN, "generate_dashboard", {"climate_entity_id": "climate.smart_climia"})
            
            await handle_generate_dashboard(call)
            
            notification_args = mock_notification.call_args[1]
            dashboard_yaml = notification_args["message"]
            
            # Verify outdoor sensor placeholder was replaced
            assert "REPLACE_ME_OUTDOOR_SENSOR" not in dashboard_yaml  
            assert "sensor.outdoor_temp" in dashboard_yaml

    @pytest.mark.asyncio
    async def test_dashboard_service_replaces_power_sensor_placeholder(
        self, mock_hass, mock_config_entry, mock_entity_registry, mock_dashboard_template
    ):
        """Test that REPLACE_ME_POWER_SENSOR is replaced with configured power sensor."""
        with patch("custom_components.smart_climate.er.async_get", return_value=mock_entity_registry), \
             patch("os.path.exists", return_value=True), \
             patch("custom_components.smart_climate._read_file_sync", return_value=mock_dashboard_template), \
             patch("custom_components.smart_climate.async_create_notification") as mock_notification:
            
            mock_entries_instance = Mock()
            mock_entries_instance.async_get_entry.return_value = mock_config_entry
            mock_hass.config_entries = mock_entries_instance
            
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "My Smart Climate"}
            mock_hass.states.get.return_value = mock_state
            
            from custom_components.smart_climate import handle_generate_dashboard
            call = ServiceCall(DOMAIN, "generate_dashboard", {"climate_entity_id": "climate.smart_climia"})
            
            await handle_generate_dashboard(call)
            
            notification_args = mock_notification.call_args[1]
            dashboard_yaml = notification_args["message"]
            
            # Verify power sensor placeholder was replaced
            assert "REPLACE_ME_POWER_SENSOR" not in dashboard_yaml
            assert "sensor.ac_power" in dashboard_yaml

    @pytest.mark.asyncio
    async def test_dashboard_service_handles_missing_optional_sensors(
        self, mock_hass, mock_entity_registry, mock_dashboard_template
    ):
        """Test that missing optional sensors get fallback values."""
        # Create config entry without optional sensors
        config_entry_no_optional = Mock()
        config_entry_no_optional.entry_id = "test_entry_id"
        config_entry_no_optional.data = {
            "room_sensor": "sensor.living_room_temp",
            # outdoor_sensor and power_sensor are None/missing
            "outdoor_sensor": None,
            "power_sensor": None,
            "climate_entity": "climate.climia",
            "name": "My Smart Climate"
        }
        
        with patch("custom_components.smart_climate.er.async_get", return_value=mock_entity_registry), \
             patch("os.path.exists", return_value=True), \
             patch("custom_components.smart_climate._read_file_sync", return_value=mock_dashboard_template), \
             patch("custom_components.smart_climate.async_create_notification") as mock_notification:
            
            mock_entries_instance = Mock()
            mock_entries_instance.async_get_entry.return_value = config_entry_no_optional
            mock_hass.config_entries = mock_entries_instance
            
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "My Smart Climate"}
            mock_hass.states.get.return_value = mock_state
            
            from custom_components.smart_climate import handle_generate_dashboard
            call = ServiceCall(DOMAIN, "generate_dashboard", {"climate_entity_id": "climate.smart_climia"})
            
            await handle_generate_dashboard(call)
            
            notification_args = mock_notification.call_args[1]
            dashboard_yaml = notification_args["message"]
            
            # Verify optional sensors get fallback values
            assert "sensor.unknown" in dashboard_yaml
            assert "REPLACE_ME_OUTDOOR_SENSOR" not in dashboard_yaml
            assert "REPLACE_ME_POWER_SENSOR" not in dashboard_yaml
            # Required room sensor should still be replaced correctly
            assert "sensor.living_room_temp" in dashboard_yaml

    @pytest.mark.asyncio
    async def test_dashboard_service_logs_sensor_replacements(
        self, mock_hass, mock_config_entry, mock_entity_registry, mock_dashboard_template
    ):
        """Test that sensor placeholder replacements are logged for debugging."""
        with patch("custom_components.smart_climate.er.async_get", return_value=mock_entity_registry), \
             patch("os.path.exists", return_value=True), \
             patch("custom_components.smart_climate._read_file_sync", return_value=mock_dashboard_template), \
             patch("custom_components.smart_climate.async_create_notification"), \
             patch("custom_components.smart_climate._LOGGER") as mock_logger:
            
            mock_entries_instance = Mock()
            mock_entries_instance.async_get_entry.return_value = mock_config_entry
            mock_hass.config_entries = mock_entries_instance
            
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "My Smart Climate"}
            mock_hass.states.get.return_value = mock_state
            
            from custom_components.smart_climate import handle_generate_dashboard
            call = ServiceCall(DOMAIN, "generate_dashboard", {"climate_entity_id": "climate.smart_climia"})
            
            await handle_generate_dashboard(call)
            
            # Verify debug logging includes sensor replacements
            debug_calls = [call for call in mock_logger.debug.call_args_list if "placeholder" in str(call)]
            assert len(debug_calls) > 0

    @pytest.mark.asyncio  
    async def test_existing_placeholders_still_work(
        self, mock_hass, mock_config_entry, mock_entity_registry, mock_dashboard_template
    ):
        """Test that existing placeholders are not broken by the new ones."""
        with patch("custom_components.smart_climate.er.async_get", return_value=mock_entity_registry), \
             patch("os.path.exists", return_value=True), \
             patch("custom_components.smart_climate._read_file_sync", return_value=mock_dashboard_template), \
             patch("custom_components.smart_climate.async_create_notification") as mock_notification:
            
            mock_entries_instance = Mock()
            mock_entries_instance.async_get_entry.return_value = mock_config_entry
            mock_hass.config_entries = mock_entries_instance
            
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "My Smart Climate"}
            mock_hass.states.get.return_value = mock_state
            
            from custom_components.smart_climate import handle_generate_dashboard
            call = ServiceCall(DOMAIN, "generate_dashboard", {"climate_entity_id": "climate.smart_climia"})
            
            await handle_generate_dashboard(call)
            
            notification_args = mock_notification.call_args[1]
            dashboard_yaml = notification_args["message"]
            
            # Verify existing placeholders are still replaced
            assert "REPLACE_ME_CLIMATE" not in dashboard_yaml
            assert "climate.smart_climia" in dashboard_yaml
            assert "REPLACE_ME_NAME" not in dashboard_yaml
            assert "My Smart Climate" in dashboard_yaml
            assert "REPLACE_ME_SWITCH" not in dashboard_yaml
            assert "switch.smart_climia_learning" in dashboard_yaml
            assert "REPLACE_ME_BUTTON" not in dashboard_yaml
            assert "button.smart_climia_reset" in dashboard_yaml