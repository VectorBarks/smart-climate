"""Integration tests for dashboard generation service with updated template."""
# ABOUTME: Integration tests for the Smart Climate dashboard generation service
# Tests the complete flow from service call to notification with the updated template

import pytest
import yaml
import os
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, mock_open, call
import logging

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

_LOGGER = logging.getLogger(__name__)


@pytest.fixture
def mock_hass_with_entities():
    """Create a mock Home Assistant instance with configured entities."""
    hass = Mock()
    hass.services = Mock()
    hass.services.has_service = Mock(return_value=False)
    hass.services.async_register = AsyncMock()
    hass.states = Mock()
    hass.data = {DOMAIN: {}}
    
    # Setup entity states
    climate_state = Mock()
    climate_state.attributes = {"friendly_name": "Living Room AC"}
    
    sensor_states = {
        "sensor.living_room_ac_offset_current": Mock(state="1.5"),
        "sensor.living_room_ac_learning_progress": Mock(state="75"),
        "sensor.living_room_ac_accuracy_current": Mock(state="92"),
        "sensor.living_room_ac_calibration_status": Mock(state="calibrated"),
        "sensor.living_room_ac_hysteresis_state": Mock(state="learning"),
    }
    
    switch_state = Mock(state="on")
    button_state = Mock()
    
    def get_state(entity_id):
        if entity_id == "climate.living_room_ac":
            return climate_state
        elif entity_id == "switch.living_room_ac_learning":
            return switch_state
        elif entity_id == "button.living_room_ac_reset":
            return button_state
        return sensor_states.get(entity_id)
    
    hass.states.get = Mock(side_effect=get_state)
    return hass


@pytest.fixture
def mock_entity_registry_with_smart_climate():
    """Create a mock entity registry with Smart Climate entities."""
    registry = Mock()
    
    # Climate entity
    climate_entity = Mock()
    climate_entity.platform = DOMAIN
    climate_entity.config_entry_id = "test_config_entry"
    climate_entity.entity_id = "climate.living_room_ac"
    climate_entity.unique_id = "living_room_ac"
    
    # Sensor entities
    sensor_entities = {}
    sensor_types = ["offset_current", "learning_progress", "accuracy_current", 
                   "calibration_status", "hysteresis_state"]
    
    for sensor_type in sensor_types:
        sensor = Mock()
        sensor.platform = DOMAIN
        sensor.config_entry_id = "test_config_entry"
        sensor.entity_id = f"sensor.living_room_ac_{sensor_type}"
        sensor.unique_id = f"living_room_ac_{sensor_type}"
        sensor.domain = "sensor"
        sensor_entities[sensor.entity_id] = sensor
    
    # Switch entity
    switch_entity = Mock()
    switch_entity.platform = DOMAIN
    switch_entity.config_entry_id = "test_config_entry"
    switch_entity.entity_id = "switch.living_room_ac_learning"
    switch_entity.unique_id = "living_room_ac_learning"
    switch_entity.domain = "switch"
    
    # Button entity
    button_entity = Mock()
    button_entity.platform = DOMAIN
    button_entity.config_entry_id = "test_config_entry"
    button_entity.entity_id = "button.living_room_ac_reset"
    button_entity.unique_id = "living_room_ac_reset"
    button_entity.domain = "button"
    
    # Build entities dict
    all_entities = {
        "climate.living_room_ac": climate_entity,
        "switch.living_room_ac_learning": switch_entity,
        "button.living_room_ac_reset": button_entity,
    }
    all_entities.update(sensor_entities)
    
    # Mock registry methods
    registry.entities = all_entities
    
    def async_get(entity_id):
        if entity_id == "climate.living_room_ac":
            return climate_entity
        return None
    
    registry.async_get = Mock(side_effect=async_get)
    return registry


@pytest.fixture
def mock_service_call():
    """Create a mock service call."""
    call = Mock()
    call.data = {"climate_entity_id": "climate.living_room_ac"}
    return call


@pytest.fixture
def actual_dashboard_template():
    """Load the actual dashboard template file."""
    template_path = Path(__file__).parent.parent / "custom_components" / "smart_climate" / "dashboard" / "dashboard_generic.yaml"
    if template_path.exists():
        with open(template_path, "r") as f:
            return f.read()
    return None


class TestDashboardServiceIntegration:
    """Integration tests for dashboard service with updated template."""

    @pytest.mark.asyncio
    async def test_complete_dashboard_generation_flow(
        self, mock_hass_with_entities, mock_entity_registry_with_smart_climate, mock_service_call
    ):
        """Test complete flow from service call to notification with actual template."""
        # Get actual template for realistic testing
        template_path = Path(__file__).parent.parent / "custom_components" / "smart_climate" / "dashboard" / "dashboard_generic.yaml"
        
        if not template_path.exists():
            pytest.skip("dashboard_generic.yaml not found")
        
        with open(template_path, "r") as f:
            actual_template = f.read()
        
        with patch("custom_components.smart_climate.er") as mock_er:
            with patch("custom_components.smart_climate.async_create_notification", new_callable=AsyncMock) as mock_notify:
                mock_er.async_get.return_value = mock_entity_registry_with_smart_climate
                
                with patch("builtins.open", mock_open(read_data=actual_template)):
                    with patch("os.path.exists", return_value=True):
                        # Register services
                        await _async_register_services(mock_hass_with_entities)
                        
                        # Get the service handler
                        service_handler = mock_hass_with_entities.services.async_register.call_args[0][2]
                        
                        # Call service
                        await service_handler(mock_service_call)
                
                # Verify notification was created
                mock_notify.assert_called_once()
                notification_args = mock_notify.call_args[1]
                
                # Verify notification structure
                assert "title" in notification_args
                assert "message" in notification_args
                assert "notification_id" in notification_args
                assert notification_args["title"] == "Smart Climate Dashboard - Living Room AC"
                assert notification_args["notification_id"] == "smart_climate_dashboard_living_room_ac"
                
                # Extract dashboard YAML from notification message
                message = notification_args["message"]
                assert "Copy the YAML below" in message
                
                # Extract YAML part (after instructions)
                yaml_start = message.find("title:")
                dashboard_yaml = message[yaml_start:]
                
                # Parse the generated YAML
                parsed = yaml.safe_load(dashboard_yaml)
                assert parsed is not None
                assert "title" in parsed
                assert parsed["title"] == "Smart Climate - Living Room AC"
                assert "views" in parsed

    @pytest.mark.asyncio
    async def test_dashboard_has_no_span_properties(
        self, mock_hass_with_entities, mock_entity_registry_with_smart_climate, mock_service_call
    ):
        """Test that generated dashboard has no span properties in ApexCharts cards."""
        template_path = Path(__file__).parent.parent / "custom_components" / "smart_climate" / "dashboard" / "dashboard_generic.yaml"
        
        if not template_path.exists():
            pytest.skip("dashboard_generic.yaml not found")
        
        with open(template_path, "r") as f:
            actual_template = f.read()
        
        with patch("custom_components.smart_climate.er") as mock_er:
            with patch("custom_components.smart_climate.async_create_notification", new_callable=AsyncMock) as mock_notify:
                mock_er.async_get.return_value = mock_entity_registry_with_smart_climate
                
                with patch("builtins.open", mock_open(read_data=actual_template)):
                    with patch("os.path.exists", return_value=True):
                        await _async_register_services(mock_hass_with_entities)
                        service_handler = mock_hass_with_entities.services.async_register.call_args[0][2]
                        await service_handler(mock_service_call)
                
                # Get generated dashboard
                message = mock_notify.call_args[1]["message"]
                yaml_start = message.find("title:")
                dashboard_yaml = message[yaml_start:]
                
                # Check raw YAML text
                assert "span:" not in dashboard_yaml or "graph_span:" in dashboard_yaml
                
                # Parse and check structure
                parsed = yaml.safe_load(dashboard_yaml)
                
                # Check all ApexCharts cards
                apex_cards_found = 0
                for view in parsed.get("views", []):
                    cards = self._get_all_cards(view.get("cards", []))
                    for card in cards:
                        if card.get("type") == "custom:apexcharts-card":
                            apex_cards_found += 1
                            assert "span" not in card, f"Found span property in ApexCharts card: {card}"
                            assert "graph_span" in card, f"Missing graph_span in ApexCharts card: {card}"
                
                # Verify we found ApexCharts cards
                assert apex_cards_found >= 3, f"Expected at least 3 ApexCharts cards, found {apex_cards_found}"

    @pytest.mark.asyncio
    async def test_all_placeholders_replaced(
        self, mock_hass_with_entities, mock_entity_registry_with_smart_climate, mock_service_call
    ):
        """Test that all REPLACE_ME placeholders are replaced correctly."""
        template_path = Path(__file__).parent.parent / "custom_components" / "smart_climate" / "dashboard" / "dashboard_generic.yaml"
        
        if not template_path.exists():
            pytest.skip("dashboard_generic.yaml not found")
        
        with open(template_path, "r") as f:
            actual_template = f.read()
        
        with patch("custom_components.smart_climate.er") as mock_er:
            with patch("custom_components.smart_climate.async_create_notification", new_callable=AsyncMock) as mock_notify:
                mock_er.async_get.return_value = mock_entity_registry_with_smart_climate
                
                with patch("builtins.open", mock_open(read_data=actual_template)):
                    with patch("os.path.exists", return_value=True):
                        await _async_register_services(mock_hass_with_entities)
                        service_handler = mock_hass_with_entities.services.async_register.call_args[0][2]
                        await service_handler(mock_service_call)
                
                # Get generated dashboard
                message = mock_notify.call_args[1]["message"]
                yaml_start = message.find("title:")
                dashboard_yaml = message[yaml_start:]
                
                # Check no placeholders remain
                assert "REPLACE_ME" not in dashboard_yaml
                
                # Check specific replacements
                assert "climate.living_room_ac" in dashboard_yaml
                assert "sensor.living_room_ac_offset_current" in dashboard_yaml
                assert "sensor.living_room_ac_learning_progress" in dashboard_yaml
                assert "sensor.living_room_ac_accuracy_current" in dashboard_yaml
                assert "sensor.living_room_ac_calibration_status" in dashboard_yaml
                assert "sensor.living_room_ac_hysteresis_state" in dashboard_yaml
                assert "switch.living_room_ac_learning" in dashboard_yaml
                assert "button.living_room_ac_reset" in dashboard_yaml

    @pytest.mark.asyncio
    async def test_entity_discovery_works_correctly(
        self, mock_hass_with_entities, mock_entity_registry_with_smart_climate, mock_service_call
    ):
        """Test that the service correctly discovers all related entities."""
        with patch("custom_components.smart_climate.er") as mock_er:
            with patch("custom_components.smart_climate.async_create_notification", new_callable=AsyncMock) as mock_notify:
                mock_er.async_get.return_value = mock_entity_registry_with_smart_climate
                
                # Mock template content to test entity discovery
                template_content = """
title: REPLACE_ME_NAME
sensors:
  - REPLACE_ME_SENSOR_OFFSET
  - REPLACE_ME_SENSOR_PROGRESS
  - REPLACE_ME_SENSOR_ACCURACY
  - REPLACE_ME_SENSOR_CALIBRATION
  - REPLACE_ME_SENSOR_HYSTERESIS
switch: REPLACE_ME_SWITCH
button: REPLACE_ME_BUTTON
"""
                
                with patch("builtins.open", mock_open(read_data=template_content)):
                    with patch("os.path.exists", return_value=True):
                        await _async_register_services(mock_hass_with_entities)
                        service_handler = mock_hass_with_entities.services.async_register.call_args[0][2]
                        
                        # Add debug logging mock
                        with patch("custom_components.smart_climate._LOGGER") as mock_logger:
                            await service_handler(mock_service_call)
                            
                            # Check that entity discovery logging occurred
                            debug_calls = [call for call in mock_logger.debug.call_args_list 
                                         if "Found" in str(call) or "Identified" in str(call)]
                            assert len(debug_calls) >= 7  # 5 sensors + switch + button

    @pytest.mark.asyncio
    async def test_generated_dashboard_is_valid_yaml(
        self, mock_hass_with_entities, mock_entity_registry_with_smart_climate, mock_service_call
    ):
        """Test that the generated dashboard is valid YAML that can be parsed."""
        template_path = Path(__file__).parent.parent / "custom_components" / "smart_climate" / "dashboard" / "dashboard_generic.yaml"
        
        if not template_path.exists():
            pytest.skip("dashboard_generic.yaml not found")
        
        with open(template_path, "r") as f:
            actual_template = f.read()
        
        with patch("custom_components.smart_climate.er") as mock_er:
            with patch("custom_components.smart_climate.async_create_notification", new_callable=AsyncMock) as mock_notify:
                mock_er.async_get.return_value = mock_entity_registry_with_smart_climate
                
                with patch("builtins.open", mock_open(read_data=actual_template)):
                    with patch("os.path.exists", return_value=True):
                        await _async_register_services(mock_hass_with_entities)
                        service_handler = mock_hass_with_entities.services.async_register.call_args[0][2]
                        await service_handler(mock_service_call)
                
                # Get generated dashboard
                message = mock_notify.call_args[1]["message"]
                yaml_start = message.find("title:")
                dashboard_yaml = message[yaml_start:]
                
                # Parse multiple times to ensure consistency
                parsed1 = yaml.safe_load(dashboard_yaml)
                yaml_str = yaml.dump(parsed1, default_flow_style=False)
                parsed2 = yaml.safe_load(yaml_str)
                
                # Basic structure validation
                assert parsed1 == parsed2  # Ensure consistent parsing
                assert isinstance(parsed1["views"], list)
                assert len(parsed1["views"]) > 0
                
                # Validate all cards have required properties
                for view in parsed1["views"]:
                    for card in self._get_all_cards(view.get("cards", [])):
                        assert "type" in card, f"Card missing type: {card}"

    @pytest.mark.asyncio
    async def test_file_read_error_handling(
        self, mock_hass_with_entities, mock_entity_registry_with_smart_climate, mock_service_call
    ):
        """Test that file read errors are handled properly."""
        with patch("custom_components.smart_climate.er") as mock_er:
            mock_er.async_get.return_value = mock_entity_registry_with_smart_climate
            
            # Simulate read error
            with patch("builtins.open", side_effect=IOError("Permission denied")):
                with patch("os.path.exists", return_value=True):
                    await _async_register_services(mock_hass_with_entities)
                    service_handler = mock_hass_with_entities.services.async_register.call_args[0][2]
                    
                    # Should raise ServiceValidationError
                    with pytest.raises(ServiceValidationError, match="Failed to read dashboard template"):
                        await service_handler(mock_service_call)

    @pytest.mark.asyncio
    async def test_missing_related_entities_warning(
        self, mock_hass_with_entities, mock_service_call
    ):
        """Test that missing related entities generate warnings but don't fail."""
        # Create registry with only climate entity (no sensors/switch/button)
        registry = Mock()
        climate_entity = Mock()
        climate_entity.platform = DOMAIN
        climate_entity.config_entry_id = "test_config_entry"
        
        registry.entities = {"climate.living_room_ac": climate_entity}
        registry.async_get = Mock(return_value=climate_entity)
        
        with patch("custom_components.smart_climate.er") as mock_er:
            with patch("custom_components.smart_climate.async_create_notification", new_callable=AsyncMock) as mock_notify:
                mock_er.async_get.return_value = registry
                
                template_content = "title: REPLACE_ME_NAME\nentity: REPLACE_ME_CLIMATE"
                
                with patch("builtins.open", mock_open(read_data=template_content)):
                    with patch("os.path.exists", return_value=True):
                        with patch("custom_components.smart_climate._LOGGER") as mock_logger:
                            await _async_register_services(mock_hass_with_entities)
                            service_handler = mock_hass_with_entities.services.async_register.call_args[0][2]
                            await service_handler(mock_service_call)
                            
                            # Check warnings were logged
                            warning_calls = [call for call in mock_logger.warning.call_args_list]
                            assert any("Missing sensors" in str(call) for call in warning_calls)
                            assert any("Learning switch not found" in str(call) for call in warning_calls)
                            assert any("Reset button not found" in str(call) for call in warning_calls)
                
                # Service should still complete
                mock_notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_custom_cards_configuration(
        self, mock_hass_with_entities, mock_entity_registry_with_smart_climate, mock_service_call
    ):
        """Test that custom cards in the dashboard are properly configured."""
        template_path = Path(__file__).parent.parent / "custom_components" / "smart_climate" / "dashboard" / "dashboard_generic.yaml"
        
        if not template_path.exists():
            pytest.skip("dashboard_generic.yaml not found")
        
        with open(template_path, "r") as f:
            actual_template = f.read()
        
        with patch("custom_components.smart_climate.er") as mock_er:
            with patch("custom_components.smart_climate.async_create_notification", new_callable=AsyncMock) as mock_notify:
                mock_er.async_get.return_value = mock_entity_registry_with_smart_climate
                
                with patch("builtins.open", mock_open(read_data=actual_template)):
                    with patch("os.path.exists", return_value=True):
                        await _async_register_services(mock_hass_with_entities)
                        service_handler = mock_hass_with_entities.services.async_register.call_args[0][2]
                        await service_handler(mock_service_call)
                
                # Parse generated dashboard
                message = mock_notify.call_args[1]["message"]
                yaml_start = message.find("title:")
                dashboard_yaml = message[yaml_start:]
                parsed = yaml.safe_load(dashboard_yaml)
                
                # Check ApexCharts configuration
                for view in parsed.get("views", []):
                    for card in self._get_all_cards(view.get("cards", [])):
                        if card.get("type") == "custom:apexcharts-card":
                            # Required properties for ApexCharts
                            assert "graph_span" in card
                            assert "series" in card
                            assert isinstance(card["series"], list)
                            assert len(card["series"]) > 0
                            
                            # Each series should have entity
                            for series in card["series"]:
                                assert "entity" in series or "attribute" in series

    # Helper methods
    def _get_all_cards(self, cards):
        """Recursively get all cards including nested ones."""
        all_cards = []
        for card in cards:
            all_cards.append(card)
            if isinstance(card, dict) and "cards" in card:
                all_cards.extend(self._get_all_cards(card["cards"]))
        return all_cards


class TestDashboardYAMLValidationUpdates:
    """Update tests for YAML validation now that span is removed."""

    def test_dashboard_generic_has_no_span_properties(self):
        """Test that dashboard_generic.yaml has no span properties in ApexCharts cards."""
        dashboard_path = Path(__file__).parent.parent / "custom_components" / "smart_climate" / "dashboard" / "dashboard_generic.yaml"
        
        if not dashboard_path.exists():
            pytest.skip("dashboard_generic.yaml not found")
        
        with open(dashboard_path, "r") as f:
            content = f.read()
        
        # Parse YAML
        dashboard = yaml.safe_load(content)
        
        # Count ApexCharts cards and check for span
        apex_cards_count = 0
        apex_cards_with_span = 0
        
        for view in dashboard.get("views", []):
            for card in self._get_all_cards_recursive(view.get("cards", [])):
                if card.get("type") == "custom:apexcharts-card":
                    apex_cards_count += 1
                    if "span" in card:
                        apex_cards_with_span += 1
                    # But graph_span should exist
                    assert "graph_span" in card, f"ApexCharts card missing graph_span: {card}"
        
        # There should be ApexCharts cards but none with span
        assert apex_cards_count >= 3, f"Expected at least 3 ApexCharts cards, found {apex_cards_count}"
        assert apex_cards_with_span == 0, f"Found {apex_cards_with_span} ApexCharts cards with span properties"

    def test_yaml_structure_remains_valid(self):
        """Test that the YAML structure is valid after span removal."""
        dashboard_path = Path(__file__).parent.parent / "custom_components" / "smart_climate" / "dashboard" / "dashboard_generic.yaml"
        
        if not dashboard_path.exists():
            pytest.skip("dashboard_generic.yaml not found")
        
        with open(dashboard_path, "r") as f:
            content = f.read()
        
        # Should parse without errors
        try:
            dashboard = yaml.safe_load(content)
        except yaml.YAMLError as e:
            pytest.fail(f"Dashboard YAML is invalid: {e}")
        
        # Validate structure
        assert dashboard is not None
        assert "title" in dashboard
        assert "views" in dashboard
        assert isinstance(dashboard["views"], list)
        assert len(dashboard["views"]) > 0

    def _get_all_cards_recursive(self, cards):
        """Get all cards recursively."""
        all_cards = []
        for card in cards:
            all_cards.append(card)
            if isinstance(card, dict) and "cards" in card:
                all_cards.extend(self._get_all_cards_recursive(card["cards"]))
        return all_cards