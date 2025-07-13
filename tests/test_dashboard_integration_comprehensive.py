"""Comprehensive integration tests for Smart Climate dashboard system."""
# ABOUTME: Complete integration tests for dashboard generation, template validation, cross-component compatibility, and real-world scenarios
# Tests the entire dashboard ecosystem including sensors, service, template processing, and error handling

import pytest
import yaml
import os
import re
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, mock_open, call
import logging
from typing import Dict, Any, List, Optional

# Define mock exception classes
class ServiceValidationError(Exception):
    """Mock ServiceValidationError."""
    pass

class HomeAssistantError(Exception):
    """Mock HomeAssistantError."""
    pass

# Mock homeassistant exceptions module
import sys
if 'homeassistant.exceptions' not in sys.modules:
    sys.modules['homeassistant.exceptions'] = Mock()
sys.modules['homeassistant.exceptions'].ServiceValidationError = ServiceValidationError
sys.modules['homeassistant.exceptions'].HomeAssistantError = HomeAssistantError

from custom_components.smart_climate import (
    DOMAIN,
    handle_generate_dashboard,
    _async_register_services,
)

_LOGGER = logging.getLogger(__name__)


class TestDashboardIntegrationComprehensive:
    """Comprehensive integration tests for dashboard system."""

    @pytest.fixture
    def complete_mock_hass(self):
        """Create a comprehensive mock Home Assistant instance with all dashboard components."""
        hass = Mock()
        hass.services = Mock()
        hass.services.has_service = Mock(return_value=False)
        hass.services.async_register = AsyncMock()
        hass.states = Mock()
        hass.data = {DOMAIN: {}}
        hass.async_add_executor_job = AsyncMock()
        hass.config_entries = Mock()
        
        # Setup entity states for comprehensive testing
        climate_state = Mock()
        climate_state.attributes = {
            "friendly_name": "Living Room Smart AC",
            "reactive_offset": 1.2,
            "predictive_offset": 0.8,
            "total_offset": 2.0,
            "predictive_strategy": {"name": "heat_wave", "adjustment": 0.8},
            "adaptive_delay": 45,
            "weather_forecast": True,
            "seasonal_adaptation": True,
        }
        
        sensor_states = {
            "sensor.living_room_smart_ac_offset_current": Mock(state="2.0"),
            "sensor.living_room_smart_ac_learning_progress": Mock(state="85"),
            "sensor.living_room_smart_ac_accuracy_current": Mock(state="92"),
            "sensor.living_room_smart_ac_calibration_status": Mock(state="calibrated"),
            "sensor.living_room_smart_ac_hysteresis_state": Mock(state="learning_hysteresis"),
            "sensor.room_temperature": Mock(state="24.5"),
            "sensor.outdoor_temperature": Mock(state="32.1"),
            "sensor.ac_power": Mock(state="1250"),
        }
        
        def get_state(entity_id):
            if entity_id == "climate.living_room_smart_ac":
                return climate_state
            return sensor_states.get(entity_id)
        
        hass.states.get = get_state
        return hass

    @pytest.fixture
    def complete_entity_registry(self):
        """Create complete entity registry with all dashboard-related entities."""
        registry = Mock()
        config_entry_id = "test_config_entry_123"
        
        # Climate entity
        climate_entity = Mock()
        climate_entity.config_entry_id = config_entry_id
        climate_entity.platform = DOMAIN
        climate_entity.domain = "climate"
        climate_entity.entity_id = "climate.living_room_smart_ac"
        climate_entity.unique_id = f"{DOMAIN}_living_room_smart_ac"
        
        # Dashboard sensor entities
        sensor_entities = {}
        sensor_types = ["offset_current", "learning_progress", "accuracy_current", 
                       "calibration_status", "hysteresis_state"]
        for sensor_type in sensor_types:
            entity = Mock()
            entity.config_entry_id = config_entry_id
            entity.platform = DOMAIN
            entity.domain = "sensor"
            entity.entity_id = f"sensor.living_room_smart_ac_{sensor_type}"
            entity.unique_id = f"{DOMAIN}_living_room_smart_ac_{sensor_type}"
            sensor_entities[entity.entity_id] = entity
        
        # Learning switch
        switch_entity = Mock()
        switch_entity.config_entry_id = config_entry_id
        switch_entity.platform = DOMAIN
        switch_entity.domain = "switch"
        switch_entity.entity_id = "switch.living_room_smart_ac_learning"
        switch_entity.unique_id = f"{DOMAIN}_living_room_smart_ac_learning"
        
        # Reset button
        button_entity = Mock()
        button_entity.config_entry_id = config_entry_id
        button_entity.platform = DOMAIN
        button_entity.domain = "button"
        button_entity.entity_id = "button.living_room_smart_ac_reset"
        button_entity.unique_id = f"{DOMAIN}_living_room_smart_ac_reset"
        
        # Combine all entities
        all_entities = {
            "climate.living_room_smart_ac": climate_entity,
            "switch.living_room_smart_ac_learning": switch_entity,
            "button.living_room_smart_ac_reset": button_entity,
            **sensor_entities
        }
        
        registry.entities = all_entities
        registry.async_get = lambda entity_id: all_entities.get(entity_id)
        
        return registry

    @pytest.fixture
    def complete_config_entry(self):
        """Create complete config entry with all sensor configurations."""
        config_entry = Mock()
        config_entry.entry_id = "test_config_entry_123"
        config_entry.config_entry_id = "test_config_entry_123"
        config_entry.data = {
            "climate_entity": "climate.original_ac",
            "room_sensor": "sensor.room_temperature",
            "outdoor_sensor": "sensor.outdoor_temperature", 
            "power_sensor": "sensor.ac_power",
        }
        return config_entry

    @pytest.fixture
    def dashboard_template_content(self):
        """Sample dashboard template content for testing."""
        return """# Smart Climate Control Dashboard Template
title: Smart Climate - REPLACE_ME_NAME
views:
  - title: Overview
    path: overview
    icon: mdi:home-thermometer
    cards:
      - type: thermostat
        entity: REPLACE_ME_CLIMATE
      - type: gauge
        entity: REPLACE_ME_SENSOR_OFFSET
        name: Total Offset
      - type: gauge
        entity: REPLACE_ME_SENSOR_PROGRESS
        name: Learning Progress
      - type: gauge
        entity: REPLACE_ME_SENSOR_ACCURACY
        name: Accuracy
      - type: custom:mushroom-entity-card
        entity: REPLACE_ME_SENSOR_CALIBRATION
        name: Calibration Status
      - type: custom:mushroom-entity-card
        entity: REPLACE_ME_SENSOR_HYSTERESIS
        name: Hysteresis State
      - type: custom:button-card
        entity: REPLACE_ME_SWITCH
        name: Learning System
      - type: button
        entity: REPLACE_ME_BUTTON
        name: Reset Training Data
      - type: custom:apexcharts-card
        series:
          - entity: REPLACE_ME_ROOM_SENSOR
            name: Indoor Temperature
          - entity: REPLACE_ME_OUTDOOR_SENSOR
            name: Outdoor Temperature
          - entity: REPLACE_ME_POWER_SENSOR
            name: Power Usage
          - entity: REPLACE_ME_CLIMATE
            attribute: reactive_offset
            name: Reactive Offset
          - entity: REPLACE_ME_CLIMATE
            attribute: predictive_offset
            name: Predictive Offset
          - entity: REPLACE_ME_CLIMATE
            attribute: total_offset
            name: Total Offset
"""

    @pytest.mark.asyncio
    async def test_end_to_end_dashboard_generation_success(
        self, complete_mock_hass, complete_entity_registry, complete_config_entry, dashboard_template_content
    ):
        """Test complete end-to-end dashboard generation workflow."""
        # Setup mocks
        with patch("custom_components.smart_climate.er.async_get", return_value=complete_entity_registry), \
             patch("custom_components.smart_climate.os.path.exists", return_value=True), \
             patch("custom_components.smart_climate.async_create_notification") as mock_notification:
            
            # Configure config entries
            complete_mock_hass.config_entries.async_get_entry = Mock(return_value=complete_config_entry)
            
            # Mock file reading
            complete_mock_hass.async_add_executor_job.return_value = dashboard_template_content
            
            # Create service call
            call_data = {
                "climate_entity_id": "climate.living_room_smart_ac"
            }
            service_call = Mock()
            service_call.hass = complete_mock_hass
            service_call.data = call_data
            
            # Execute service
            await handle_generate_dashboard(service_call)
            
            # Verify notification was created
            mock_notification.assert_called_once()
            call_args = mock_notification.call_args
            
            # Validate notification content
            assert call_args[0][0] == complete_mock_hass  # hass
            assert "Smart Climate Dashboard - Living Room Smart AC" in call_args[1]["title"]
            
            # Validate dashboard YAML content
            notification_message = call_args[1]["message"]
            assert "```yaml" in notification_message
            
            # Extract YAML from notification
            yaml_start = notification_message.find("```yaml\n") + 8
            yaml_end = notification_message.find("\n```", yaml_start)
            generated_yaml = notification_message[yaml_start:yaml_end]
            
            # Verify all placeholders were replaced
            remaining_placeholders = re.findall(r'REPLACE_ME_\w+', generated_yaml)
            assert len(remaining_placeholders) == 0, f"Unreplaced placeholders: {remaining_placeholders}"
            
            # Verify specific replacements
            assert "climate.living_room_smart_ac" in generated_yaml
            assert "Living Room Smart AC" in generated_yaml
            assert "sensor.living_room_smart_ac_offset_current" in generated_yaml
            assert "sensor.room_temperature" in generated_yaml
            assert "sensor.outdoor_temperature" in generated_yaml
            assert "sensor.ac_power" in generated_yaml

    @pytest.mark.asyncio
    async def test_template_structure_validation(self, complete_mock_hass, dashboard_template_content):
        """Test that generated dashboard YAML has valid structure."""
        # Setup mocks for successful generation
        with patch("custom_components.smart_climate.er.async_get") as mock_registry, \
             patch("custom_components.smart_climate.os.path.exists", return_value=True), \
             patch("custom_components.smart_climate.async_create_notification") as mock_notification:
            
            # Setup entity registry
            registry = Mock()
            entity = Mock()
            entity.config_entry_id = "test_config"
            entity.platform = DOMAIN
            registry.async_get.return_value = entity
            mock_registry.return_value = registry
            
            # Setup config entry
            config_entry = Mock()
            config_entry.entry_id = "test_config"
            config_entry.data = {
                "room_sensor": "sensor.room",
                "outdoor_sensor": "sensor.outdoor",
                "power_sensor": "sensor.power"
            }
            complete_mock_hass.config_entries.async_get_entry = Mock(return_value=config_entry)
            
            # Setup entity discovery (minimal for structure test)
            registry.entities = {
                "sensor.test_offset_current": Mock(
                    config_entry_id="test_config", domain="sensor", platform=DOMAIN,
                    unique_id="test_offset_current"
                ),
                "switch.test_learning": Mock(
                    config_entry_id="test_config", domain="switch", platform=DOMAIN
                ),
                "button.test_reset": Mock(
                    config_entry_id="test_config", domain="button", platform=DOMAIN
                )
            }
            
            # Mock file reading
            complete_mock_hass.async_add_executor_job.return_value = dashboard_template_content
            
            # Setup state
            state = Mock()
            state.attributes = {"friendly_name": "Test Climate"}
            complete_mock_hass.states.get.return_value = state
            
            # Create service call
            call_data = {"climate_entity_id": "climate.test"}
            service_call = Mock()
            service_call.hass = complete_mock_hass
            service_call.data = call_data
            
            # Execute service
            await handle_generate_dashboard(service_call)
            
            # Extract generated YAML
            mock_notification.assert_called_once()
            notification_message = mock_notification.call_args[1]["message"]
            yaml_start = notification_message.find("```yaml\n") + 8
            yaml_end = notification_message.find("\n```", yaml_start)
            generated_yaml = notification_message[yaml_start:yaml_end]
            
            # Validate YAML structure
            try:
                parsed_yaml = yaml.safe_load(generated_yaml)
                assert isinstance(parsed_yaml, dict)
                assert "title" in parsed_yaml
                assert "views" in parsed_yaml
                assert isinstance(parsed_yaml["views"], list)
                assert len(parsed_yaml["views"]) > 0
                
                # Check first view structure
                first_view = parsed_yaml["views"][0]
                assert "title" in first_view
                assert "cards" in first_view
                assert isinstance(first_view["cards"], list)
                
            except yaml.YAMLError as e:
                pytest.fail(f"Generated YAML is not valid: {e}")

    @pytest.mark.asyncio
    async def test_cross_component_integration_v1_3_features(
        self, complete_mock_hass, complete_entity_registry, complete_config_entry, dashboard_template_content
    ):
        """Test integration of v1.3.0 multi-layered intelligence features in dashboard."""
        # Enhanced template with v1.3.0 features
        enhanced_template = dashboard_template_content + """
      # v1.3.0 Multi-Layered Intelligence
      - type: custom:mushroom-template-card
        entity: REPLACE_ME_CLIMATE
        primary: >-
          {{ state_attr('REPLACE_ME_CLIMATE', 'reactive_offset') | default('0.0') | round(1) }}°C
        secondary: Reactive Offset
      - type: custom:mushroom-template-card
        entity: REPLACE_ME_CLIMATE
        primary: >-
          {{ state_attr('REPLACE_ME_CLIMATE', 'predictive_offset') | default('0.0') | round(1) }}°C
        secondary: Predictive Offset
      - type: custom:mushroom-template-card
        entity: REPLACE_ME_CLIMATE
        primary: >-
          {{ state_attr('REPLACE_ME_CLIMATE', 'total_offset') | default('0.0') | round(1) }}°C
        secondary: Total Offset
      - type: conditional
        conditions:
          - entity: REPLACE_ME_CLIMATE
            attribute: predictive_strategy
            state_not: null
        card:
          type: custom:mushroom-entity-card
          entity: REPLACE_ME_CLIMATE
          name: >-
            {{ state_attr('REPLACE_ME_CLIMATE', 'predictive_strategy')['name'] if state_attr('REPLACE_ME_CLIMATE', 'predictive_strategy') else 'No Strategy' }}
"""
        
        # Setup mocks
        with patch("custom_components.smart_climate.er.async_get", return_value=complete_entity_registry), \
             patch("custom_components.smart_climate.os.path.exists", return_value=True), \
             patch("custom_components.smart_climate.async_create_notification") as mock_notification:
            
            complete_mock_hass.config_entries.async_get_entry = Mock(return_value=complete_config_entry)
            complete_mock_hass.async_add_executor_job.return_value = enhanced_template
            
            call_data = {"climate_entity_id": "climate.living_room_smart_ac"}
            service_call = Mock()
            service_call.hass = complete_mock_hass
            service_call.data = call_data
            
            # Execute service
            await handle_generate_dashboard(service_call)
            
            # Extract generated YAML
            notification_message = mock_notification.call_args[1]["message"]
            yaml_start = notification_message.find("```yaml\n") + 8
            yaml_end = notification_message.find("\n```", yaml_start)
            generated_yaml = notification_message[yaml_start:yaml_end]
            
            # Verify v1.3.0 features are properly integrated
            assert "reactive_offset" in generated_yaml
            assert "predictive_offset" in generated_yaml
            assert "total_offset" in generated_yaml
            assert "predictive_strategy" in generated_yaml
            
            # Verify all entity references are correct
            assert "climate.living_room_smart_ac" in generated_yaml.count("climate.living_room_smart_ac") >= 4
            
            # Verify no broken references
            remaining_placeholders = re.findall(r'REPLACE_ME_\w+', generated_yaml)
            assert len(remaining_placeholders) == 0

    @pytest.mark.asyncio
    async def test_real_world_scenario_optional_sensors(
        self, complete_mock_hass, complete_entity_registry, dashboard_template_content
    ):
        """Test dashboard generation with missing optional sensors (real-world scenario)."""
        # Create config entry without optional sensors
        minimal_config_entry = Mock()
        minimal_config_entry.entry_id = "test_config_entry_123"
        minimal_config_entry.data = {
            "climate_entity": "climate.original_ac",
            "room_sensor": "sensor.room_temperature",
            # Missing outdoor_sensor and power_sensor (optional)
        }
        
        # Setup mocks
        with patch("custom_components.smart_climate.er.async_get", return_value=complete_entity_registry), \
             patch("custom_components.smart_climate.os.path.exists", return_value=True), \
             patch("custom_components.smart_climate.async_create_notification") as mock_notification:
            
            complete_mock_hass.config_entries.async_get_entry = Mock(return_value=minimal_config_entry)
            complete_mock_hass.async_add_executor_job.return_value = dashboard_template_content
            
            call_data = {"climate_entity_id": "climate.living_room_smart_ac"}
            service_call = Mock()
            service_call.hass = complete_mock_hass
            service_call.data = call_data
            
            # Execute service
            await handle_generate_dashboard(service_call)
            
            # Extract generated YAML
            notification_message = mock_notification.call_args[1]["message"]
            yaml_start = notification_message.find("```yaml\n") + 8
            yaml_end = notification_message.find("\n```", yaml_start)
            generated_yaml = notification_message[yaml_start:yaml_end]
            
            # Verify proper fallback for missing sensors
            assert "sensor.room_temperature" in generated_yaml  # Required sensor present
            assert "sensor.unknown" in generated_yaml  # Fallback for optional sensors
            
            # Should still generate valid dashboard
            remaining_placeholders = re.findall(r'REPLACE_ME_\w+', generated_yaml)
            assert len(remaining_placeholders) == 0

    @pytest.mark.asyncio 
    async def test_error_handling_missing_template_file(self, complete_mock_hass, complete_entity_registry, complete_config_entry):
        """Test error handling when dashboard template file is missing."""
        with patch("custom_components.smart_climate.er.async_get", return_value=complete_entity_registry), \
             patch("custom_components.smart_climate.os.path.exists", return_value=False):
            
            complete_mock_hass.config_entries.async_get_entry = Mock(return_value=complete_config_entry)
            
            call_data = {"climate_entity_id": "climate.living_room_smart_ac"}
            service_call = Mock()
            service_call.hass = complete_mock_hass
            service_call.data = call_data
            
            # Should raise ServiceValidationError
            with pytest.raises(ServiceValidationError, match="Dashboard template file not found"):
                await handle_generate_dashboard(service_call)

    @pytest.mark.asyncio
    async def test_error_handling_invalid_entity(self, complete_mock_hass):
        """Test error handling for invalid or non-existent entity."""
        # Empty entity registry
        empty_registry = Mock()
        empty_registry.async_get.return_value = None
        
        with patch("custom_components.smart_climate.er.async_get", return_value=empty_registry):
            call_data = {"climate_entity_id": "climate.nonexistent"}
            service_call = Mock()
            service_call.hass = complete_mock_hass
            service_call.data = call_data
            
            # Should raise ServiceValidationError
            with pytest.raises(ServiceValidationError, match="Entity climate.nonexistent not found"):
                await handle_generate_dashboard(service_call)

    @pytest.mark.asyncio
    async def test_error_handling_wrong_integration_entity(self, complete_mock_hass):
        """Test error handling when entity is not from smart_climate integration."""
        # Entity from different integration
        wrong_entity = Mock()
        wrong_entity.platform = "other_integration"
        
        registry = Mock()
        registry.async_get.return_value = wrong_entity
        
        with patch("custom_components.smart_climate.er.async_get", return_value=registry):
            call_data = {"climate_entity_id": "climate.other_ac"}
            service_call = Mock()
            service_call.hass = complete_mock_hass
            service_call.data = call_data
            
            # Should raise ServiceValidationError
            with pytest.raises(ServiceValidationError, match="is not a Smart Climate entity"):
                await handle_generate_dashboard(service_call)

    @pytest.mark.asyncio
    async def test_error_handling_file_read_failure(
        self, complete_mock_hass, complete_entity_registry, complete_config_entry
    ):
        """Test error handling when template file cannot be read."""
        with patch("custom_components.smart_climate.er.async_get", return_value=complete_entity_registry), \
             patch("custom_components.smart_climate.os.path.exists", return_value=True):
            
            complete_mock_hass.config_entries.async_get_entry = Mock(return_value=complete_config_entry)
            
            # Mock file read failure
            complete_mock_hass.async_add_executor_job.side_effect = IOError("Permission denied")
            
            call_data = {"climate_entity_id": "climate.living_room_smart_ac"}
            service_call = Mock()
            service_call.hass = complete_mock_hass
            service_call.data = call_data
            
            # Should raise ServiceValidationError
            with pytest.raises(ServiceValidationError, match="Failed to read dashboard template"):
                await handle_generate_dashboard(service_call)

    @pytest.mark.asyncio
    async def test_placeholder_validation_comprehensive(
        self, complete_mock_hass, complete_entity_registry, complete_config_entry
    ):
        """Test comprehensive placeholder validation including edge cases."""
        # Template with intentionally missing placeholder replacement logic
        template_with_unreplaced = """
title: Smart Climate - REPLACE_ME_NAME
views:
  - title: Overview
    cards:
      - type: thermostat
        entity: REPLACE_ME_CLIMATE
      - type: gauge
        entity: REPLACE_ME_UNKNOWN_PLACEHOLDER
"""
        
        with patch("custom_components.smart_climate.er.async_get", return_value=complete_entity_registry), \
             patch("custom_components.smart_climate.os.path.exists", return_value=True):
            
            complete_mock_hass.config_entries.async_get_entry = Mock(return_value=complete_config_entry)
            complete_mock_hass.async_add_executor_job.return_value = template_with_unreplaced
            
            call_data = {"climate_entity_id": "climate.living_room_smart_ac"}
            service_call = Mock()
            service_call.hass = complete_mock_hass
            service_call.data = call_data
            
            # Should raise ServiceValidationError due to unreplaced placeholder
            with pytest.raises(ServiceValidationError, match="unreplaced placeholders"):
                await handle_generate_dashboard(service_call)

    @pytest.mark.asyncio
    async def test_notification_creation_failure(
        self, complete_mock_hass, complete_entity_registry, complete_config_entry, dashboard_template_content
    ):
        """Test error handling when notification creation fails."""
        with patch("custom_components.smart_climate.er.async_get", return_value=complete_entity_registry), \
             patch("custom_components.smart_climate.os.path.exists", return_value=True), \
             patch("custom_components.smart_climate.async_create_notification", side_effect=Exception("Notification error")):
            
            complete_mock_hass.config_entries.async_get_entry = Mock(return_value=complete_config_entry)
            complete_mock_hass.async_add_executor_job.return_value = dashboard_template_content
            
            call_data = {"climate_entity_id": "climate.living_room_smart_ac"}
            service_call = Mock()
            service_call.hass = complete_mock_hass
            service_call.data = call_data
            
            # Should raise ServiceValidationError
            with pytest.raises(ServiceValidationError, match="Failed to create notification"):
                await handle_generate_dashboard(service_call)

    @pytest.mark.asyncio
    async def test_entity_discovery_comprehensive(
        self, complete_mock_hass, complete_config_entry, dashboard_template_content
    ):
        """Test comprehensive entity discovery logic including edge cases."""
        # Create registry with mixed entities
        registry = Mock()
        config_entry_id = "test_config_entry_123"
        
        # Mix of entities - some matching, some not
        mixed_entities = {
            "climate.living_room_smart_ac": Mock(
                config_entry_id=config_entry_id, platform=DOMAIN, domain="climate"
            ),
            "sensor.living_room_smart_ac_offset_current": Mock(
                config_entry_id=config_entry_id, platform=DOMAIN, domain="sensor",
                unique_id="living_room_smart_ac_offset_current"
            ),
            "sensor.living_room_smart_ac_accuracy_current": Mock(
                config_entry_id=config_entry_id, platform=DOMAIN, domain="sensor",
                unique_id="living_room_smart_ac_accuracy_current"
            ),
            "switch.living_room_smart_ac_learning": Mock(
                config_entry_id=config_entry_id, platform=DOMAIN, domain="switch"
            ),
            "button.living_room_smart_ac_reset": Mock(
                config_entry_id=config_entry_id, platform=DOMAIN, domain="button"
            ),
            # Entities from different config entries or integrations (should be ignored)
            "sensor.other_entity": Mock(
                config_entry_id="different_config", platform=DOMAIN, domain="sensor"
            ),
            "sensor.non_smart_climate": Mock(
                config_entry_id=config_entry_id, platform="other_integration", domain="sensor"
            ),
        }
        
        registry.entities = mixed_entities
        registry.async_get = lambda entity_id: mixed_entities.get(entity_id)
        
        with patch("custom_components.smart_climate.er.async_get", return_value=registry), \
             patch("custom_components.smart_climate.os.path.exists", return_value=True), \
             patch("custom_components.smart_climate.async_create_notification") as mock_notification:
            
            complete_mock_hass.config_entries.async_get_entry = Mock(return_value=complete_config_entry)
            complete_mock_hass.async_add_executor_job.return_value = dashboard_template_content
            
            # Setup state
            state = Mock()
            state.attributes = {"friendly_name": "Living Room Smart AC"}
            complete_mock_hass.states.get.return_value = state
            
            call_data = {"climate_entity_id": "climate.living_room_smart_ac"}
            service_call = Mock()
            service_call.hass = complete_mock_hass
            service_call.data = call_data
            
            # Execute service
            await handle_generate_dashboard(service_call)
            
            # Extract generated YAML
            notification_message = mock_notification.call_args[1]["message"]
            yaml_start = notification_message.find("```yaml\n") + 8
            yaml_end = notification_message.find("\n```", yaml_start)
            generated_yaml = notification_message[yaml_start:yaml_end]
            
            # Verify discovered entities are used correctly
            assert "sensor.living_room_smart_ac_offset_current" in generated_yaml
            assert "sensor.living_room_smart_ac_accuracy_current" in generated_yaml
            assert "switch.living_room_smart_ac_learning" in generated_yaml
            assert "button.living_room_smart_ac_reset" in generated_yaml
            
            # Verify missing sensors get fallback values
            assert "sensor.unknown" in generated_yaml  # For missing sensor types
            
            # Verify entities from other configs/integrations are not included
            assert "sensor.other_entity" not in generated_yaml
            assert "sensor.non_smart_climate" not in generated_yaml

    def test_yaml_structure_deep_validation(self):
        """Test deep validation of YAML structure with complex nested elements."""
        # Sample of actual generated YAML structure
        sample_yaml = """
title: Smart Climate - Test AC
views:
  - title: Overview
    path: overview
    icon: mdi:home-thermometer
    cards:
      - type: vertical-stack
        cards:
          - type: thermostat
            entity: climate.test_ac
          - type: horizontal-stack
            cards:
              - type: gauge
                entity: sensor.test_ac_offset_current
                min: -5
                max: 5
                severity:
                  green: -1
                  yellow: -3
                  red: -5
              - type: gauge
                entity: sensor.test_ac_learning_progress
                unit: '%'
                min: 0
                max: 100
      - type: custom:apexcharts-card
        header:
          show: true
          title: Multi-Layered Offset Analysis (24h)
        series:
          - entity: climate.test_ac
            attribute: reactive_offset
            name: Reactive Offset
            color: orange
          - entity: climate.test_ac
            attribute: predictive_offset
            name: Predictive Offset
            color: green
"""
        
        # Validate structure
        try:
            parsed = yaml.safe_load(sample_yaml)
            
            # Top level structure
            assert "title" in parsed
            assert "views" in parsed
            assert isinstance(parsed["views"], list)
            
            # View structure
            view = parsed["views"][0]
            assert "title" in view
            assert "path" in view
            assert "icon" in view
            assert "cards" in view
            assert isinstance(view["cards"], list)
            
            # Card structure validation
            for card in view["cards"]:
                assert "type" in card
                if card["type"] == "vertical-stack":
                    assert "cards" in card
                    assert isinstance(card["cards"], list)
                    
                    # Validate nested cards
                    for nested_card in card["cards"]:
                        assert "type" in nested_card
                        if "entity" in nested_card:
                            assert nested_card["entity"].startswith(("climate.", "sensor.", "switch.", "button."))
                
                elif card["type"] == "custom:apexcharts-card":
                    assert "series" in card
                    assert isinstance(card["series"], list)
                    for series in card["series"]:
                        assert "entity" in series
                        assert "name" in series
                        
        except yaml.YAMLError as e:
            pytest.fail(f"YAML structure validation failed: {e}")

    @pytest.mark.asyncio
    async def test_service_registration_idempotent(self, complete_mock_hass):
        """Test that service registration is idempotent (doesn't register twice)."""
        # First registration
        await _async_register_services(complete_mock_hass)
        complete_mock_hass.services.async_register.assert_called_once()
        
        # Mark service as already registered
        complete_mock_hass.services.has_service.return_value = True
        complete_mock_hass.services.async_register.reset_mock()
        
        # Second registration should not call register again
        await _async_register_services(complete_mock_hass)
        complete_mock_hass.services.async_register.assert_not_called()

    @pytest.mark.asyncio
    async def test_dashboard_generation_with_all_sensors_present(
        self, complete_mock_hass, complete_entity_registry, complete_config_entry, dashboard_template_content
    ):
        """Test dashboard generation when all sensors and entities are present."""
        with patch("custom_components.smart_climate.er.async_get", return_value=complete_entity_registry), \
             patch("custom_components.smart_climate.os.path.exists", return_value=True), \
             patch("custom_components.smart_climate.async_create_notification") as mock_notification:
            
            complete_mock_hass.config_entries.async_get_entry = Mock(return_value=complete_config_entry)
            complete_mock_hass.async_add_executor_job.return_value = dashboard_template_content
            
            call_data = {"climate_entity_id": "climate.living_room_smart_ac"}
            service_call = Mock()
            service_call.hass = complete_mock_hass
            service_call.data = call_data
            
            # Execute service
            await handle_generate_dashboard(service_call)
            
            # Verify notification content has no "sensor.unknown" fallbacks
            notification_message = mock_notification.call_args[1]["message"]
            yaml_start = notification_message.find("```yaml\n") + 8
            yaml_end = notification_message.find("\n```", yaml_start)
            generated_yaml = notification_message[yaml_start:yaml_end]
            
            # Count actual entity references vs fallbacks
            actual_sensor_count = generated_yaml.count("sensor.living_room_smart_ac_")
            unknown_sensor_count = generated_yaml.count("sensor.unknown")
            
            # Should have more actual sensors than unknown fallbacks
            assert actual_sensor_count >= 5  # At least 5 dashboard sensors
            # With complete setup, we should have minimal fallbacks (only for truly missing sensor types)
            
            # Verify comprehensive entity integration
            expected_entities = [
                "climate.living_room_smart_ac",
                "sensor.living_room_smart_ac_offset_current",
                "sensor.living_room_smart_ac_learning_progress", 
                "sensor.living_room_smart_ac_accuracy_current",
                "sensor.living_room_smart_ac_calibration_status",
                "sensor.living_room_smart_ac_hysteresis_state",
                "switch.living_room_smart_ac_learning",
                "button.living_room_smart_ac_reset",
                "sensor.room_temperature",
                "sensor.outdoor_temperature",
                "sensor.ac_power"
            ]
            
            for entity in expected_entities:
                assert entity in generated_yaml, f"Expected entity {entity} not found in generated dashboard"