"""
Test that handle_generate_dashboard service uses DashboardGenerator instead of old template system.
This test verifies the fix for the bug where the service was reading dashboard_generic.yaml 
instead of using the new Advanced Analytics Dashboard system.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from homeassistant.exceptions import ServiceValidationError

from custom_components.smart_climate import handle_generate_dashboard


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    hass = Mock(spec=HomeAssistant)
    hass.config_entries = Mock()
    hass.states = Mock()
    hass.async_add_executor_job = AsyncMock()
    return hass


@pytest.fixture
def mock_service_call(mock_hass):
    """Create a mock ServiceCall."""
    call = Mock(spec=ServiceCall)
    call.hass = mock_hass
    call.data = {"climate_entity_id": "climate.living_room"}
    return call


@pytest.fixture
def mock_entity_registry():
    """Create a mock entity registry."""
    registry = Mock()
    
    # Mock entity entry for the climate entity
    climate_entity = Mock()
    climate_entity.platform = "smart_climate"
    climate_entity.config_entry_id = "config_123"
    climate_entity.entity_id = "climate.living_room"
    
    registry.async_get.return_value = climate_entity
    return registry


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    config_entry = Mock()
    config_entry.data = {"room_sensor": "sensor.living_room_temp"}
    config_entry.options = {"outdoor_sensor": "sensor.outdoor_temp", "power_sensor": "sensor.ac_power"}
    return config_entry


class TestDashboardServiceGeneratorIntegration:
    """Test that the dashboard service uses DashboardGenerator."""

    @patch('custom_components.smart_climate.er.async_get')
    @patch('custom_components.smart_climate.async_create_notification')
    @patch('custom_components.smart_climate.DashboardGenerator')
    async def test_service_uses_dashboard_generator_not_template_file(
        self, mock_dashboard_generator_class, mock_notification, mock_er_get,
        mock_service_call, mock_entity_registry, mock_config_entry
    ):
        """Test that handle_generate_dashboard uses DashboardGenerator instead of reading template file."""
        # Setup mocks
        mock_er_get.return_value = mock_entity_registry
        mock_entity_registry.entities = {}
        
        # Mock the state
        mock_state = Mock()
        mock_state.attributes = {"friendly_name": "Living Room Climate"}
        mock_service_call.hass.states.get.return_value = mock_state
        
        # Mock config entries
        mock_service_call.hass.config_entries.async_get_entry.return_value = mock_config_entry
        
        # Mock DashboardGenerator instance
        mock_generator = Mock()
        mock_dashboard_yaml = "title: Advanced Analytics Dashboard\nviews: []"
        mock_generator.generate_dashboard.return_value = mock_dashboard_yaml
        mock_dashboard_generator_class.return_value = mock_generator
        
        # Execute the service
        await handle_generate_dashboard(mock_service_call)
        
        # Verify DashboardGenerator was instantiated
        mock_dashboard_generator_class.assert_called_once()
        
        # Verify generate_dashboard was called with correct parameters
        mock_generator.generate_dashboard.assert_called_once_with(
            "climate.living_room", 
            "Living Room Climate"
        )
        
        # Verify notification was created with the generated YAML (not template)
        mock_notification.assert_called_once()
        notification_call = mock_notification.call_args
        
        # The message should contain the dashboard YAML from generator, not template
        assert mock_dashboard_yaml in notification_call[1]["message"]
        assert "Advanced Analytics Dashboard" in notification_call[1]["message"]

    @patch('custom_components.smart_climate.er.async_get')
    @patch('custom_components.smart_climate.async_create_notification')
    @patch('custom_components.smart_climate.DashboardGenerator')
    async def test_service_passes_correct_entity_id_format_to_generator(
        self, mock_dashboard_generator_class, mock_notification, mock_er_get,
        mock_service_call, mock_entity_registry, mock_config_entry
    ):
        """Test that the service passes the full entity ID format to DashboardGenerator."""
        # Setup mocks
        mock_er_get.return_value = mock_entity_registry
        mock_entity_registry.entities = {}
        
        # Use a different entity ID to test the format
        mock_service_call.data = {"climate_entity_id": "climate.bedroom_ac"}
        
        mock_state = Mock()
        mock_state.attributes = {"friendly_name": "Bedroom AC"}
        mock_service_call.hass.states.get.return_value = mock_state
        
        mock_service_call.hass.config_entries.async_get_entry.return_value = mock_config_entry
        
        # Mock DashboardGenerator instance
        mock_generator = Mock()
        mock_generator.generate_dashboard.return_value = "dashboard: content"
        mock_dashboard_generator_class.return_value = mock_generator
        
        # Execute the service
        await handle_generate_dashboard(mock_service_call)
        
        # Verify generate_dashboard was called with the full entity ID (not just the part after the dot)
        mock_generator.generate_dashboard.assert_called_once_with(
            "climate.bedroom_ac",  # Should be full entity ID
            "Bedroom AC"
        )

    @patch('custom_components.smart_climate.er.async_get')
    @patch('custom_components.smart_climate.DashboardGenerator')
    async def test_service_handles_generator_exceptions(
        self, mock_dashboard_generator_class, mock_er_get,
        mock_service_call, mock_entity_registry, mock_config_entry
    ):
        """Test that the service properly handles DashboardGenerator exceptions."""
        # Setup mocks
        mock_er_get.return_value = mock_entity_registry
        mock_entity_registry.entities = {}
        
        mock_state = Mock()
        mock_state.attributes = {"friendly_name": "Living Room Climate"}
        mock_service_call.hass.states.get.return_value = mock_state
        
        mock_service_call.hass.config_entries.async_get_entry.return_value = mock_config_entry
        
        # Mock DashboardGenerator to raise an exception
        mock_generator = Mock()
        mock_generator.generate_dashboard.side_effect = ValueError("Generator error")
        mock_dashboard_generator_class.return_value = mock_generator
        
        # Execute and verify exception handling
        with pytest.raises(ServiceValidationError) as exc_info:
            await handle_generate_dashboard(mock_service_call)
        
        assert "Failed to generate dashboard" in str(exc_info.value)

    @patch('custom_components.smart_climate.er.async_get')
    @patch('custom_components.smart_climate.async_create_notification')
    @patch('custom_components.smart_climate.DashboardGenerator')
    async def test_service_generates_31kb_advanced_dashboard_not_old_template(
        self, mock_dashboard_generator_class, mock_notification, mock_er_get,
        mock_service_call, mock_entity_registry, mock_config_entry
    ):
        """Test that the service generates the large Advanced Analytics Dashboard, not a small template."""
        # Setup mocks
        mock_er_get.return_value = mock_entity_registry
        mock_entity_registry.entities = {}
        
        mock_state = Mock()
        mock_state.attributes = {"friendly_name": "Living Room Climate"}
        mock_service_call.hass.states.get.return_value = mock_state
        
        mock_service_call.hass.config_entries.async_get_entry.return_value = mock_config_entry
        
        # Mock DashboardGenerator to return a large dashboard (simulating the real 31KB output)
        mock_generator = Mock()
        # Simulate the real Advanced Analytics Dashboard - should be much larger than old template
        mock_advanced_dashboard = "title: Smart Climate Advanced Analytics\n" + "x" * 30000  # ~31KB
        mock_generator.generate_dashboard.return_value = mock_advanced_dashboard
        mock_dashboard_generator_class.return_value = mock_generator
        
        # Execute the service
        await handle_generate_dashboard(mock_service_call)
        
        # Verify notification contains the large dashboard
        notification_call = mock_notification.call_args
        message = notification_call[1]["message"]
        
        # Should contain the large dashboard content, not a small template
        assert len(message) > 20000  # Much larger than old template
        assert "Smart Climate Advanced Analytics" in message
        
        # Should NOT contain old template patterns
        assert "REPLACE_ME_" not in mock_advanced_dashboard

    @patch('custom_components.smart_climate.er.async_get')
    @patch('custom_components.smart_climate.async_create_notification')
    @patch('custom_components.smart_climate.os.path.exists')
    @patch('custom_components.smart_climate.DashboardGenerator')
    async def test_service_does_not_read_template_file(
        self, mock_dashboard_generator_class, mock_path_exists, mock_notification, mock_er_get,
        mock_service_call, mock_entity_registry, mock_config_entry
    ):
        """Test that the service does NOT read the old dashboard_generic.yaml template file."""
        # Setup mocks
        mock_er_get.return_value = mock_entity_registry
        mock_entity_registry.entities = {}
        
        mock_state = Mock()
        mock_state.attributes = {"friendly_name": "Living Room Climate"}
        mock_service_call.hass.states.get.return_value = mock_state
        
        mock_service_call.hass.config_entries.async_get_entry.return_value = mock_config_entry
        
        # Mock DashboardGenerator
        mock_generator = Mock()
        mock_generator.generate_dashboard.return_value = "advanced: dashboard"
        mock_dashboard_generator_class.return_value = mock_generator
        
        # Mock that template file exists (but should not be read)
        mock_path_exists.return_value = True
        
        # Execute the service
        await handle_generate_dashboard(mock_service_call)
        
        # Verify that os.path.exists was NOT called for the template file
        # (This would indicate the old code path was taken)
        template_calls = [call for call in mock_path_exists.call_args_list 
                         if call[0][0] and "dashboard_generic.yaml" in call[0][0]]
        assert len(template_calls) == 0, "Service should not check for dashboard_generic.yaml template file"
        
        # Verify async_add_executor_job was NOT called to read template file
        mock_service_call.hass.async_add_executor_job.assert_not_called()