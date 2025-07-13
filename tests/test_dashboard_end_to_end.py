"""End-to-end dashboard workflow tests."""
# ABOUTME: Complete end-to-end tests for the dashboard system workflow
# Tests the entire user journey from service call through notification delivery

import pytest
import yaml
import os
import re
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, mock_open, call
import logging
from datetime import datetime, timedelta

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


class TestDashboardEndToEnd:
    """End-to-end workflow tests for dashboard system."""

    @pytest.fixture
    def realistic_hass_environment(self):
        """Create a realistic Home Assistant environment for testing."""
        hass = Mock()
        hass.services = Mock()
        hass.services.has_service = Mock(return_value=False)
        hass.services.async_register = AsyncMock()
        hass.states = Mock()
        hass.data = {DOMAIN: {}}
        hass.async_add_executor_job = AsyncMock()
        hass.config_entries = Mock()
        
        # Realistic climate entity state with full v1.3.0 attributes
        climate_state = Mock()
        climate_state.attributes = {
            "friendly_name": "Master Bedroom AC",
            "current_temperature": 23.5,
            "target_temperature": 24.0,
            "hvac_mode": "cool",
            "preset_mode": "none",
            # v1.3.0 Multi-layered intelligence attributes
            "reactive_offset": 1.5,
            "predictive_offset": -0.3,
            "total_offset": 1.2,
            "predictive_strategy": {
                "name": "heat_wave",
                "adjustment": -0.3,
                "end_time": "2025-07-14T18:00:00"
            },
            # Adaptive timing attributes
            "adaptive_delay": 48,
            "temperature_stability_detected": True,
            "learned_delay_seconds": 48,
            "ema_coefficient": 0.15,
            # Weather integration attributes
            "weather_forecast": True,
            "seasonal_adaptation": True,
            "outdoor_temp_bucket": "30-35°C",
            "seasonal_pattern_count": 23,
            "seasonal_accuracy": 87.3,
            # Performance metrics
            "prediction_latency_ms": 0.8,
            "energy_efficiency_score": 91.2,
            "sensor_availability_score": 98.5,
            "temperature_window_learned": "1.8°C",
            "power_correlation_accuracy": 94.7,
            "hysteresis_cycle_count": 12,
            # Technical diagnostics
            "memory_usage_kb": 245,
            "persistence_latency_ms": 3.2,
            "outlier_detection_active": True,
            "samples_per_day": 12.4,
            "accuracy_improvement_rate": 2.1,
            "convergence_trend": "improving",
            # Algorithm internals
            "correlation_coefficient": 0.89,
            "prediction_variance": 0.182,
            "model_entropy": 1.34,
            "temporal_stability_index": 0.923,
            "learning_rate": 0.08,
            "momentum_factor": 0.92,
            "regularization_strength": 0.005,
            # Statistical metrics
            "mean_squared_error": 0.041,
            "mean_absolute_error": 0.156,
            "r_squared": 0.847,
            "cross_validation_score": 0.823,
        }
        
        # Realistic sensor states
        sensor_states = {
            "sensor.master_bedroom_ac_offset_current": Mock(state="1.2", attributes={"unit_of_measurement": "°C"}),
            "sensor.master_bedroom_ac_learning_progress": Mock(state="89", attributes={"unit_of_measurement": "%"}),
            "sensor.master_bedroom_ac_accuracy_current": Mock(state="87", attributes={"unit_of_measurement": "%"}),
            "sensor.master_bedroom_ac_calibration_status": Mock(
                state="calibrated", 
                attributes={
                    "samples_collected": 156,
                    "last_sample": "2025-07-13T21:45:32",
                    "calibration_confidence": 0.92
                }
            ),
            "sensor.master_bedroom_ac_hysteresis_state": Mock(
                state="learning_hysteresis",
                attributes={
                    "temperature_window": "1.8°C",
                    "ready": True,
                    "start_threshold": 24.8,
                    "stop_threshold": 23.0,
                    "start_samples": 89,
                    "stop_samples": 87
                }
            ),
            "sensor.bedroom_temperature": Mock(state="23.5", attributes={"unit_of_measurement": "°C"}),
            "sensor.outdoor_temperature": Mock(state="31.2", attributes={"unit_of_measurement": "°C"}),
            "sensor.ac_power_consumption": Mock(state="1850", attributes={"unit_of_measurement": "W"}),
            "switch.master_bedroom_ac_learning": Mock(
                state="on",
                attributes={
                    "has_sufficient_data": True,
                    "confidence_level": 87.3,
                    "patterns_learned": 23,
                    "last_learning_time": "2025-07-13T21:30:00"
                }
            ),
            "button.master_bedroom_ac_reset": Mock(state="unknown"),
        }
        
        def get_state(entity_id):
            if entity_id == "climate.master_bedroom_ac":
                return climate_state
            return sensor_states.get(entity_id)
        
        hass.states.get = get_state
        return hass

    @pytest.fixture
    def realistic_entity_registry(self):
        """Create realistic entity registry with proper hierarchy."""
        registry = Mock()
        config_entry_id = "smart_climate_bedroom_001"
        
        # Climate entity
        climate_entity = Mock()
        climate_entity.config_entry_id = config_entry_id
        climate_entity.platform = DOMAIN
        climate_entity.domain = "climate"
        climate_entity.entity_id = "climate.master_bedroom_ac"
        climate_entity.unique_id = f"{DOMAIN}_master_bedroom_ac_climate"
        
        # Dashboard sensor entities with realistic unique IDs
        sensor_entities = {}
        sensor_types = ["offset_current", "learning_progress", "accuracy_current", 
                       "calibration_status", "hysteresis_state"]
        for sensor_type in sensor_types:
            entity = Mock()
            entity.config_entry_id = config_entry_id
            entity.platform = DOMAIN
            entity.domain = "sensor"
            entity.entity_id = f"sensor.master_bedroom_ac_{sensor_type}"
            entity.unique_id = f"{DOMAIN}_master_bedroom_ac_{sensor_type}"
            sensor_entities[entity.entity_id] = entity
        
        # Learning switch
        switch_entity = Mock()
        switch_entity.config_entry_id = config_entry_id
        switch_entity.platform = DOMAIN
        switch_entity.domain = "switch"
        switch_entity.entity_id = "switch.master_bedroom_ac_learning"
        switch_entity.unique_id = f"{DOMAIN}_master_bedroom_ac_learning"
        
        # Reset button
        button_entity = Mock()
        button_entity.config_entry_id = config_entry_id
        button_entity.platform = DOMAIN
        button_entity.domain = "button"
        button_entity.entity_id = "button.master_bedroom_ac_reset"
        button_entity.unique_id = f"{DOMAIN}_master_bedroom_ac_reset"
        
        # Combine all entities
        all_entities = {
            "climate.master_bedroom_ac": climate_entity,
            "switch.master_bedroom_ac_learning": switch_entity,
            "button.master_bedroom_ac_reset": button_entity,
            **sensor_entities
        }
        
        registry.entities = all_entities
        registry.async_get = lambda entity_id: all_entities.get(entity_id)
        
        return registry

    @pytest.fixture
    def realistic_config_entry(self):
        """Create realistic config entry with all sensor types."""
        config_entry = Mock()
        config_entry.entry_id = "smart_climate_bedroom_001"
        config_entry.data = {
            "climate_entity": "climate.bedroom_ac_original",
            "room_sensor": "sensor.bedroom_temperature",
            "outdoor_sensor": "sensor.outdoor_temperature",
            "power_sensor": "sensor.ac_power_consumption",
            "update_interval": 180,
            "max_offset": 5.0,
            "learning_enabled": True,
        }
        return config_entry

    @pytest.fixture
    def full_dashboard_template(self):
        """Complete realistic dashboard template."""
        # Load the actual template content from the file system for testing
        template_path = Path(__file__).parent.parent / "custom_components" / "smart_climate" / "dashboard" / "dashboard_generic.yaml"
        if template_path.exists():
            return template_path.read_text()
        
        # Fallback comprehensive template for testing
        return """# Smart Climate Control Dashboard Template
title: Smart Climate - REPLACE_ME_NAME
views:
  - title: Overview
    path: overview
    icon: mdi:home-thermometer
    cards:
      - type: vertical-stack
        cards:
          - type: custom:mushroom-climate-card
            entity: REPLACE_ME_CLIMATE
            name: Smart Climate Control
            show_current_as_primary: true
            hvac_modes:
              - heat_cool
              - cool
              - heat
              - fan_only
              - dry
              - 'off'
            layout: horizontal
          - type: thermostat
            entity: REPLACE_ME_CLIMATE
            name: Smart Climate Control
          - type: horizontal-stack
            cards:
              - type: gauge
                entity: REPLACE_ME_SENSOR_OFFSET
                name: Total Offset
                unit: °C
                min: -5
                max: 5
                severity:
                  green: -1
                  yellow: -3
                  red: -5
                needle: true
              - type: gauge
                entity: REPLACE_ME_SENSOR_PROGRESS
                name: Learning Progress
                unit: '%'
                min: 0
                max: 100
                severity:
                  red: 0
                  yellow: 50
                  green: 80
                needle: true
              - type: gauge
                entity: REPLACE_ME_SENSOR_ACCURACY
                name: Accuracy
                unit: '%'
                min: 0
                max: 100
                severity:
                  red: 0
                  yellow: 60
                  green: 85
                needle: true
      - type: vertical-stack
        cards:
          - type: markdown
            content: '## Learning System Status'
          - type: horizontal-stack
            cards:
              - type: custom:button-card
                entity: REPLACE_ME_SWITCH
                name: Learning System
                show_state: true
                show_last_changed: true
                state:
                  - value: 'on'
                    color: green
                    icon: mdi:brain
                  - value: 'off'
                    color: red
                    icon: mdi:brain-off
              - type: custom:mushroom-entity-card
                entity: REPLACE_ME_SENSOR_CALIBRATION
                name: Calibration Status
                icon: mdi:progress-check
                layout: vertical
              - type: custom:mushroom-template-card
                entity: REPLACE_ME_SENSOR_CALIBRATION
                primary: >-
                  {{ state_attr('REPLACE_ME_SENSOR_CALIBRATION', 'samples_collected') | default('0') }}
                secondary: Samples Collected
                icon: mdi:counter
                layout: vertical
      - type: vertical-stack
        cards:
          - type: markdown
            content: '## v1.3.0 Multi-Layered Intelligence'
          - type: horizontal-stack
            cards:
              - type: custom:mushroom-template-card
                entity: REPLACE_ME_CLIMATE
                primary: >-
                  {{ state_attr('REPLACE_ME_CLIMATE', 'reactive_offset') | default('0.0') | round(1) }}°C
                secondary: Reactive Offset
                icon: mdi:thermometer-lines
                layout: vertical
                badge_color: blue
              - type: custom:mushroom-template-card
                entity: REPLACE_ME_CLIMATE
                primary: >-
                  {{ state_attr('REPLACE_ME_CLIMATE', 'predictive_offset') | default('0.0') | round(1) }}°C
                secondary: Predictive Offset
                icon: mdi:weather-partly-cloudy
                layout: vertical
                badge_color: green
              - type: custom:mushroom-template-card
                entity: REPLACE_ME_CLIMATE
                primary: >-
                  {{ state_attr('REPLACE_ME_CLIMATE', 'total_offset') | default('0.0') | round(1) }}°C
                secondary: Total Offset
                icon: mdi:sigma
                layout: vertical
                badge_color: orange
          - type: conditional
            conditions:
              - entity: REPLACE_ME_CLIMATE
                attribute: predictive_strategy
                state_not: null
            card:
              type: vertical-stack
              cards:
                - type: markdown
                  content: '### Active Weather Strategy'
                - type: custom:mushroom-entity-card
                  entity: REPLACE_ME_CLIMATE
                  name: >-
                    {{ state_attr('REPLACE_ME_CLIMATE', 'predictive_strategy')['name'] if state_attr('REPLACE_ME_CLIMATE', 'predictive_strategy') else 'No Strategy' }}
                  secondary_info: >-
                    {{ state_attr('REPLACE_ME_CLIMATE', 'predictive_strategy')['adjustment'] if state_attr('REPLACE_ME_CLIMATE', 'predictive_strategy') else '' }}°C adjustment
                  icon: mdi:strategy
                  layout: vertical
      - type: vertical-stack
        cards:
          - type: markdown
            content: '## Performance Charts'
          - type: custom:apexcharts-card
            header:
              show: true
              title: Multi-Layered Offset Analysis (24h)
            graph_span: 24h
            update_interval: 1min
            series:
              - entity: REPLACE_ME_CLIMATE
                attribute: current_temperature
                name: Indoor Temperature
                color: cyan
                stroke_width: 2
                yaxis_id: temperature
              - entity: REPLACE_ME_OUTDOOR_SENSOR
                name: Outdoor Temperature
                color: blue
                stroke_width: 2
                yaxis_id: temperature
                show: >-
                  ${ states('REPLACE_ME_OUTDOOR_SENSOR') not in ['unavailable', 'unknown'] }
              - entity: REPLACE_ME_CLIMATE
                attribute: reactive_offset
                name: Reactive Offset
                color: orange
                stroke_width: 2
                yaxis_id: offset
              - entity: REPLACE_ME_CLIMATE
                attribute: predictive_offset
                name: Predictive Offset
                color: green
                stroke_width: 2
                yaxis_id: offset
              - entity: REPLACE_ME_CLIMATE
                attribute: total_offset
                name: Total Offset
                color: red
                stroke_width: 3
                yaxis_id: offset
            yaxis:
              - id: temperature
                decimals: 1
                apex_config:
                  title:
                    text: Temperature (°C)
              - id: offset
                opposite: true
                decimals: 1
                apex_config:
                  title:
                    text: Offset (°C)
  - title: Detailed Stats
    path: stats
    icon: mdi:chart-line
    cards:
      - type: custom:apexcharts-card
        header:
          show: true
          title: Detailed Learning Metrics (7 days)
        graph_span: 7d
        update_interval: 5min
        series:
          - entity: REPLACE_ME_SENSOR_PROGRESS
            name: Learning Progress
            color: purple
            stroke_width: 2
            yaxis_id: percentage
          - entity: REPLACE_ME_SENSOR_ACCURACY
            name: Accuracy
            color: green
            stroke_width: 2
            yaxis_id: percentage
          - entity: REPLACE_ME_SENSOR_OFFSET
            name: Applied Offset
            color: red
            stroke_width: 2
            yaxis_id: offset
        yaxis:
          - id: percentage
            decimals: 0
            apex_config:
              title:
                text: Progress & Accuracy (%)
          - id: offset
            opposite: true
            decimals: 1
            apex_config:
              title:
                text: Offset (°C)
"""

    @pytest.mark.asyncio
    async def test_complete_user_workflow_success(
        self, realistic_hass_environment, realistic_entity_registry, realistic_config_entry, full_dashboard_template
    ):
        """Test complete user workflow from service call to usable dashboard."""
        # Setup the complete environment
        with patch("custom_components.smart_climate.er.async_get", return_value=realistic_entity_registry), \
             patch("custom_components.smart_climate.os.path.exists", return_value=True), \
             patch("custom_components.smart_climate.async_create_notification") as mock_notification:
            
            realistic_hass_environment.config_entries.async_get_entry = Mock(return_value=realistic_config_entry)
            realistic_hass_environment.async_add_executor_job.return_value = full_dashboard_template
            
            # Simulate user calling the service
            call_data = {"climate_entity_id": "climate.master_bedroom_ac"}
            service_call = Mock()
            service_call.hass = realistic_hass_environment
            service_call.data = call_data
            
            # Execute the complete workflow
            await handle_generate_dashboard(service_call)
            
            # Verify notification was created successfully
            mock_notification.assert_called_once()
            notification_call = mock_notification.call_args
            
            # Validate notification structure
            assert notification_call[0][0] == realistic_hass_environment  # hass instance
            notification_data = notification_call[1]
            
            assert "title" in notification_data
            assert "message" in notification_data
            assert "notification_id" in notification_data
            assert "Smart Climate Dashboard - Master Bedroom AC" in notification_data["title"]
            assert "master_bedroom_ac" in notification_data["notification_id"]
            
            # Extract and validate generated dashboard YAML
            message = notification_data["message"]
            assert "Copy the YAML below" in message
            assert "```yaml" in message
            
            yaml_start = message.find("```yaml\n") + 8
            yaml_end = message.find("\n```", yaml_start)
            generated_yaml = message[yaml_start:yaml_end]
            
            # Comprehensive validation of generated dashboard
            self._validate_complete_dashboard_yaml(generated_yaml)
            
            # Verify user instructions are present
            instructions = [
                "Go to Settings → Dashboards",
                "Click 'Add Dashboard'",
                "Click 'Edit Dashboard'",
                "Click 'Raw Configuration Editor'",
                "Replace the content with the YAML below"
            ]
            for instruction in instructions:
                assert instruction in message

    def _validate_complete_dashboard_yaml(self, yaml_content: str):
        """Comprehensive validation of generated dashboard YAML."""
        # 1. Verify no unreplaced placeholders
        remaining_placeholders = re.findall(r'REPLACE_ME_\w+', yaml_content)
        assert len(remaining_placeholders) == 0, f"Unreplaced placeholders found: {remaining_placeholders}"
        
        # 2. Verify YAML is valid and parseable
        try:
            parsed_yaml = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            pytest.fail(f"Generated YAML is invalid: {e}")
        
        # 3. Verify dashboard structure
        assert isinstance(parsed_yaml, dict)
        assert "title" in parsed_yaml
        assert "views" in parsed_yaml
        assert parsed_yaml["title"] == "Smart Climate - Master Bedroom AC"
        assert isinstance(parsed_yaml["views"], list)
        assert len(parsed_yaml["views"]) >= 2  # Overview + Detailed Stats
        
        # 4. Verify entity references are realistic
        expected_entities = [
            "climate.master_bedroom_ac",
            "sensor.master_bedroom_ac_offset_current",
            "sensor.master_bedroom_ac_learning_progress",
            "sensor.master_bedroom_ac_accuracy_current", 
            "sensor.master_bedroom_ac_calibration_status",
            "sensor.master_bedroom_ac_hysteresis_state",
            "switch.master_bedroom_ac_learning",
            "button.master_bedroom_ac_reset",
            "sensor.bedroom_temperature",
            "sensor.outdoor_temperature",
            "sensor.ac_power_consumption"
        ]
        
        for entity in expected_entities:
            assert entity in yaml_content, f"Expected entity {entity} not found in dashboard"
        
        # 5. Verify v1.3.0 intelligence features are present
        intelligence_features = [
            "reactive_offset",
            "predictive_offset", 
            "total_offset",
            "predictive_strategy",
            "adaptive_delay",
            "weather_forecast",
            "seasonal_adaptation"
        ]
        
        for feature in intelligence_features:
            assert feature in yaml_content, f"v1.3.0 feature {feature} not found in dashboard"
        
        # 6. Verify chart configurations
        assert "apexcharts-card" in yaml_content
        assert "graph_span: 24h" in yaml_content
        assert "graph_span: 7d" in yaml_content
        
        # 7. Verify conditional logic for optional sensors
        assert "state_not: 'unavailable'" in yaml_content or "states('sensor." in yaml_content

    @pytest.mark.asyncio
    async def test_user_workflow_with_partial_configuration(
        self, realistic_hass_environment, realistic_entity_registry, full_dashboard_template
    ):
        """Test user workflow with minimal sensor configuration (common real-world scenario)."""
        # Create minimal config entry (only required sensors)
        minimal_config = Mock()
        minimal_config.entry_id = "smart_climate_bedroom_001"
        minimal_config.data = {
            "climate_entity": "climate.bedroom_ac_original",
            "room_sensor": "sensor.bedroom_temperature",
            # Missing outdoor_sensor and power_sensor
        }
        
        with patch("custom_components.smart_climate.er.async_get", return_value=realistic_entity_registry), \
             patch("custom_components.smart_climate.os.path.exists", return_value=True), \
             patch("custom_components.smart_climate.async_create_notification") as mock_notification:
            
            realistic_hass_environment.config_entries.async_get_entry = Mock(return_value=minimal_config)
            realistic_hass_environment.async_add_executor_job.return_value = full_dashboard_template
            
            call_data = {"climate_entity_id": "climate.master_bedroom_ac"}
            service_call = Mock()
            service_call.hass = realistic_hass_environment
            service_call.data = call_data
            
            # Execute workflow
            await handle_generate_dashboard(service_call)
            
            # Extract generated YAML
            notification_message = mock_notification.call_args[1]["message"]
            yaml_start = notification_message.find("```yaml\n") + 8
            yaml_end = notification_message.find("\n```", yaml_start)
            generated_yaml = notification_message[yaml_start:yaml_end]
            
            # Verify dashboard still generates successfully with fallbacks
            assert "sensor.bedroom_temperature" in generated_yaml  # Required sensor present
            assert "sensor.unknown" in generated_yaml  # Fallback for missing optional sensors
            
            # Verify YAML is still valid despite missing sensors
            try:
                yaml.safe_load(generated_yaml)
            except yaml.YAMLError as e:
                pytest.fail(f"Generated YAML with partial config is invalid: {e}")

    @pytest.mark.asyncio
    async def test_workflow_timing_and_performance(
        self, realistic_hass_environment, realistic_entity_registry, realistic_config_entry, full_dashboard_template
    ):
        """Test workflow performance and timing characteristics."""
        import time
        
        with patch("custom_components.smart_climate.er.async_get", return_value=realistic_entity_registry), \
             patch("custom_components.smart_climate.os.path.exists", return_value=True), \
             patch("custom_components.smart_climate.async_create_notification") as mock_notification:
            
            realistic_hass_environment.config_entries.async_get_entry = Mock(return_value=realistic_config_entry)
            realistic_hass_environment.async_add_executor_job.return_value = full_dashboard_template
            
            call_data = {"climate_entity_id": "climate.master_bedroom_ac"}
            service_call = Mock()
            service_call.hass = realistic_hass_environment
            service_call.data = call_data
            
            # Measure execution time
            start_time = time.time()
            await handle_generate_dashboard(service_call)
            execution_time = time.time() - start_time
            
            # Verify reasonable performance (should complete quickly)
            assert execution_time < 5.0, f"Dashboard generation took too long: {execution_time:.2f}s"
            
            # Verify all operations were called
            mock_notification.assert_called_once()
            realistic_hass_environment.async_add_executor_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_workflow_with_complex_entity_names(
        self, realistic_hass_environment, full_dashboard_template
    ):
        """Test workflow with complex entity naming scenarios."""
        # Create entity registry with complex names
        registry = Mock()
        config_entry_id = "smart_climate_complex_001"
        
        # Entity with complex name
        complex_climate_entity = Mock()
        complex_climate_entity.config_entry_id = config_entry_id
        complex_climate_entity.platform = DOMAIN
        complex_climate_entity.domain = "climate"
        complex_climate_entity.entity_id = "climate.living_room_split_system_ac_unit_1"
        complex_climate_entity.unique_id = f"{DOMAIN}_living_room_split_system_ac_unit_1"
        
        # Corresponding sensor entities
        sensor_entities = {}
        sensor_types = ["offset_current", "learning_progress", "accuracy_current", 
                       "calibration_status", "hysteresis_state"]
        for sensor_type in sensor_types:
            entity = Mock()
            entity.config_entry_id = config_entry_id
            entity.platform = DOMAIN
            entity.domain = "sensor"
            entity.entity_id = f"sensor.living_room_split_system_ac_unit_1_{sensor_type}"
            entity.unique_id = f"{DOMAIN}_living_room_split_system_ac_unit_1_{sensor_type}"
            sensor_entities[entity.entity_id] = entity
        
        switch_entity = Mock()
        switch_entity.config_entry_id = config_entry_id
        switch_entity.platform = DOMAIN
        switch_entity.domain = "switch"
        switch_entity.entity_id = "switch.living_room_split_system_ac_unit_1_learning"
        switch_entity.unique_id = f"{DOMAIN}_living_room_split_system_ac_unit_1_learning"
        
        button_entity = Mock()
        button_entity.config_entry_id = config_entry_id
        button_entity.platform = DOMAIN
        button_entity.domain = "button"
        button_entity.entity_id = "button.living_room_split_system_ac_unit_1_reset"
        button_entity.unique_id = f"{DOMAIN}_living_room_split_system_ac_unit_1_reset"
        
        all_entities = {
            "climate.living_room_split_system_ac_unit_1": complex_climate_entity,
            "switch.living_room_split_system_ac_unit_1_learning": switch_entity,
            "button.living_room_split_system_ac_unit_1_reset": button_entity,
            **sensor_entities
        }
        
        registry.entities = all_entities
        registry.async_get = lambda entity_id: all_entities.get(entity_id)
        
        # Complex config entry
        complex_config = Mock()
        complex_config.entry_id = config_entry_id
        complex_config.data = {
            "climate_entity": "climate.original_long_name_ac",
            "room_sensor": "sensor.living_room_temperature_sensor_main",
            "outdoor_sensor": "sensor.outdoor_weather_station_temperature",
            "power_sensor": "sensor.ac_unit_1_power_consumption_watts",
        }
        
        # Setup state with complex friendly name
        complex_state = Mock()
        complex_state.attributes = {"friendly_name": "Living Room Split System AC Unit #1"}
        realistic_hass_environment.states.get.return_value = complex_state
        
        with patch("custom_components.smart_climate.er.async_get", return_value=registry), \
             patch("custom_components.smart_climate.os.path.exists", return_value=True), \
             patch("custom_components.smart_climate.async_create_notification") as mock_notification:
            
            realistic_hass_environment.config_entries.async_get_entry = Mock(return_value=complex_config)
            realistic_hass_environment.async_add_executor_job.return_value = full_dashboard_template
            
            call_data = {"climate_entity_id": "climate.living_room_split_system_ac_unit_1"}
            service_call = Mock()
            service_call.hass = realistic_hass_environment
            service_call.data = call_data
            
            # Execute workflow
            await handle_generate_dashboard(service_call)
            
            # Verify complex names are handled correctly
            notification_message = mock_notification.call_args[1]["message"]
            yaml_start = notification_message.find("```yaml\n") + 8
            yaml_end = notification_message.find("\n```", yaml_start)
            generated_yaml = notification_message[yaml_start:yaml_end]
            
            # Verify complex entity IDs are properly referenced
            assert "climate.living_room_split_system_ac_unit_1" in generated_yaml
            assert "sensor.living_room_split_system_ac_unit_1_offset_current" in generated_yaml
            assert "sensor.living_room_temperature_sensor_main" in generated_yaml
            assert "Living Room Split System AC Unit #1" in notification_message
            
            # Verify no placeholder issues with complex names
            remaining_placeholders = re.findall(r'REPLACE_ME_\w+', generated_yaml)
            assert len(remaining_placeholders) == 0

    @pytest.mark.asyncio
    async def test_workflow_integration_with_home_assistant_services(self, realistic_hass_environment):
        """Test integration with Home Assistant service registration and management."""
        # Test service registration workflow
        await _async_register_services(realistic_hass_environment)
        
        # Verify service was registered with correct parameters
        realistic_hass_environment.services.async_register.assert_called_once()
        call_args = realistic_hass_environment.services.async_register.call_args
        
        assert call_args[0][0] == DOMAIN  # domain
        assert call_args[0][1] == "generate_dashboard"  # service name
        assert callable(call_args[0][2])  # service handler
        
        # Verify schema was provided
        assert "schema" in call_args[1]
        
        # Test service already registered scenario
        realistic_hass_environment.services.has_service.return_value = True
        realistic_hass_environment.services.async_register.reset_mock()
        
        # Should not register again
        await _async_register_services(realistic_hass_environment)
        realistic_hass_environment.services.async_register.assert_not_called()

    @pytest.mark.asyncio
    async def test_end_to_end_error_recovery_scenarios(
        self, realistic_hass_environment, realistic_entity_registry, realistic_config_entry
    ):
        """Test end-to-end error recovery and graceful degradation."""
        scenarios = [
            {
                "name": "Template file read failure",
                "setup": lambda: patch("custom_components.smart_climate.os.path.exists", return_value=False),
                "expected_error": "Dashboard template file not found"
            },
            {
                "name": "Invalid entity",
                "setup": lambda: patch("custom_components.smart_climate.er.async_get", return_value=Mock(async_get=Mock(return_value=None))),
                "expected_error": "not found"
            },
            {
                "name": "Wrong integration entity",
                "setup": lambda: self._setup_wrong_integration_entity(),
                "expected_error": "not a Smart Climate entity"
            },
        ]
        
        for scenario in scenarios:
            with scenario["setup"]():
                realistic_hass_environment.config_entries.async_get_entry = Mock(return_value=realistic_config_entry)
                
                call_data = {"climate_entity_id": "climate.master_bedroom_ac"}
                service_call = Mock()
                service_call.hass = realistic_hass_environment
                service_call.data = call_data
                
                with pytest.raises(ServiceValidationError, match=scenario["expected_error"]):
                    await handle_generate_dashboard(service_call)

    def _setup_wrong_integration_entity(self):
        """Setup entity from wrong integration for testing."""
        wrong_entity = Mock()
        wrong_entity.platform = "other_integration"
        wrong_registry = Mock()
        wrong_registry.async_get.return_value = wrong_entity
        return patch("custom_components.smart_climate.er.async_get", return_value=wrong_registry)

    @pytest.mark.asyncio
    async def test_dashboard_yaml_usability_validation(
        self, realistic_hass_environment, realistic_entity_registry, realistic_config_entry, full_dashboard_template
    ):
        """Test that generated dashboard YAML is immediately usable in Home Assistant."""
        with patch("custom_components.smart_climate.er.async_get", return_value=realistic_entity_registry), \
             patch("custom_components.smart_climate.os.path.exists", return_value=True), \
             patch("custom_components.smart_climate.async_create_notification") as mock_notification:
            
            realistic_hass_environment.config_entries.async_get_entry = Mock(return_value=realistic_config_entry)
            realistic_hass_environment.async_add_executor_job.return_value = full_dashboard_template
            
            call_data = {"climate_entity_id": "climate.master_bedroom_ac"}
            service_call = Mock()
            service_call.hass = realistic_hass_environment
            service_call.data = call_data
            
            await handle_generate_dashboard(service_call)
            
            # Extract generated YAML
            notification_message = mock_notification.call_args[1]["message"]
            yaml_start = notification_message.find("```yaml\n") + 8
            yaml_end = notification_message.find("\n```", yaml_start)
            generated_yaml = notification_message[yaml_start:yaml_end]
            
            # Test YAML usability checks
            self._validate_dashboard_usability(generated_yaml)

    def _validate_dashboard_usability(self, yaml_content: str):
        """Validate that dashboard YAML is usable in Home Assistant."""
        # 1. Valid YAML structure
        try:
            parsed = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            pytest.fail(f"Dashboard YAML is not valid: {e}")
        
        # 2. Required dashboard structure
        assert "title" in parsed
        assert "views" in parsed
        assert isinstance(parsed["views"], list)
        assert len(parsed["views"]) > 0
        
        # 3. Valid view structure
        for view in parsed["views"]:
            assert "title" in view
            assert "cards" in view
            assert isinstance(view["cards"], list)
        
        # 4. Valid card types
        valid_card_types = [
            "thermostat", "gauge", "entities", "button", "horizontal-stack",
            "vertical-stack", "conditional", "markdown", "custom:mushroom-climate-card",
            "custom:mushroom-entity-card", "custom:mushroom-template-card", 
            "custom:button-card", "custom:apexcharts-card"
        ]
        
        def validate_cards(cards):
            for card in cards:
                assert "type" in card
                # Allow any card type that starts with "custom:" or is in valid list
                if not card["type"].startswith("custom:"):
                    assert card["type"] in valid_card_types, f"Unknown card type: {card['type']}"
                
                # Recursively check nested cards
                if "cards" in card:
                    validate_cards(card["cards"])
                
                # If card has entity, verify it follows proper naming
                if "entity" in card:
                    entity_id = card["entity"]
                    assert re.match(r'[a-z_]+\.[a-z0-9_]+', entity_id), f"Invalid entity ID format: {entity_id}"
        
        validate_cards(parsed["views"][0]["cards"])
        
        # 5. Template syntax validation for Jinja2 templates
        jinja_patterns = re.findall(r'\{\{.*?\}\}', yaml_content)
        for pattern in jinja_patterns:
            # Basic validation that templates are properly formed
            assert pattern.count("{{") == 1, f"Malformed template: {pattern}"
            assert pattern.count("}}") == 1, f"Malformed template: {pattern}"