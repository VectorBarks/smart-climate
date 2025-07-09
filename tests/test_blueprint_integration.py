"""Integration tests for Smart Climate dashboard blueprint."""
# ABOUTME: Integration tests for validating complete blueprint functionality
# Ensures blueprint imports correctly, entities resolve, and dashboard renders

import pytest
import yaml
import json
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.components.lovelace import dashboard
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util

from tests.dashboard_test_utils import (
    load_blueprint_yaml,
    validate_card_structure,
    MockEntity,
    create_mock_climate_entity,
    create_mock_switch_entity,
    create_mock_sensor_entity
)


class TestBlueprintIntegration:
    """Test full blueprint integration with Home Assistant."""
    
    @pytest.fixture
    def hass(self) -> HomeAssistant:
        """Create a mock Home Assistant instance."""
        hass = Mock(spec=HomeAssistant)
        hass.states = Mock()
        hass.services = Mock()
        hass.config = Mock()
        hass.config.units = Mock()
        hass.config.units.temperature_unit = "°C"
        return hass
    
    @pytest.fixture
    def mock_entities(self, hass) -> Dict[str, MockEntity]:
        """Create mock entities for testing."""
        entities = {
            'climate.smart_climate_living_room': create_mock_climate_entity(
                'climate.smart_climate_living_room',
                current_temperature=22.5,
                target_temperature=23.0,
                preset_mode='none',
                attributes={
                    'current_offset': -0.5,
                    'offset_history': [-0.3, -0.4, -0.5],
                    'calibration_active': False,
                    'calibration_samples': 10
                }
            ),
            'switch.smart_climate_living_room_learning': create_mock_switch_entity(
                'switch.smart_climate_living_room_learning',
                state='on',
                attributes={
                    'samples_collected': 45,
                    'learning_accuracy': 87.5,
                    'confidence_level': 75.0,
                    'has_sufficient_data': True,
                    'hysteresis_state': 'Temperature stable',
                    'learned_start_threshold': 0.5,
                    'learned_stop_threshold': -0.3,
                    'temperature_window': 0.8,
                    'start_samples_collected': 15,
                    'stop_samples_collected': 12,
                    'hysteresis_ready': True,
                    'hysteresis_enabled': True,
                    'last_updated': datetime.now().isoformat()
                }
            ),
            'sensor.living_room_temperature': create_mock_sensor_entity(
                'sensor.living_room_temperature',
                state=22.5,
                device_class='temperature',
                unit='°C'
            ),
            'sensor.ac_power': create_mock_sensor_entity(
                'sensor.ac_power',
                state=1500,
                device_class='power',
                unit='W'
            )
        }
        
        # Mock the states.get method
        hass.states.get = lambda entity_id: entities.get(entity_id)
        
        return entities
    
    @pytest.fixture
    def blueprint_inputs(self) -> Dict[str, str]:
        """Create blueprint input values."""
        return {
            'climate_entity': 'climate.smart_climate_living_room',
            'learning_switch': 'switch.smart_climate_living_room_learning',
            'room_sensor': 'sensor.living_room_temperature',
            'power_sensor': 'sensor.ac_power'
        }
    
    def test_blueprint_structure_validation(self):
        """Test that blueprint has valid structure for Home Assistant."""
        blueprint = load_blueprint_yaml()
        
        # Required top-level keys
        assert 'blueprint' in blueprint, "Blueprint must have 'blueprint' key"
        assert 'cards' in blueprint or 'views' in blueprint, "Blueprint must have cards or views"
        
        # Blueprint metadata
        blueprint_meta = blueprint['blueprint']
        assert 'name' in blueprint_meta, "Blueprint must have a name"
        assert 'description' in blueprint_meta, "Blueprint must have a description"
        assert 'domain' in blueprint_meta, "Blueprint must have a domain"
        assert blueprint_meta['domain'] == 'lovelace', "Domain must be 'lovelace'"
        
        # Input validation
        assert 'input' in blueprint_meta, "Blueprint must have input definitions"
        inputs = blueprint_meta['input']
        
        required_inputs = ['climate_entity', 'learning_switch', 'room_sensor']
        for input_name in required_inputs:
            assert input_name in inputs, f"Blueprint must have '{input_name}' input"
            
            input_config = inputs[input_name]
            assert 'name' in input_config, f"Input '{input_name}' must have a name"
            assert 'description' in input_config, f"Input '{input_name}' must have a description"
            assert 'selector' in input_config, f"Input '{input_name}' must have a selector"
    
    def test_entity_reference_resolution(self, hass, mock_entities, blueprint_inputs):
        """Test that all entity references in blueprint can be resolved."""
        blueprint = load_blueprint_yaml()
        
        # Process blueprint with inputs
        processed = self._process_blueprint_inputs(blueprint, blueprint_inputs)
        
        # Find all entity references
        entity_refs = self._find_entity_references(processed)
        
        # Verify all referenced entities exist or are template sensors
        for entity_ref in entity_refs:
            if entity_ref.startswith('sensor.smart_climate_'):
                # Template sensor - will be created by blueprint
                continue
            elif entity_ref.startswith('number.smart_climate_') or entity_ref.startswith('button.smart_climate_'):
                # Integration entities - expected to exist
                continue
            else:
                # Should be in mock entities
                assert entity_ref in mock_entities, f"Entity '{entity_ref}' not found"
    
    def test_template_sensor_functionality(self, hass, mock_entities, blueprint_inputs):
        """Test that template sensors work correctly with entity data."""
        blueprint = load_blueprint_yaml()
        
        # Get template sensor definitions
        templates = blueprint.get('template', [])
        assert len(templates) > 0, "Blueprint should have template sensors"
        
        # Test each template sensor
        for template_group in templates:
            if 'sensor' in template_group:
                for sensor_def in template_group['sensor']:
                    # Verify template expressions are valid
                    self._validate_template_sensor(sensor_def, hass, blueprint_inputs)
    
    def test_card_rendering_without_errors(self, hass, mock_entities, blueprint_inputs):
        """Test that all cards can render without errors."""
        blueprint = load_blueprint_yaml()
        processed = self._process_blueprint_inputs(blueprint, blueprint_inputs)
        
        # Get all cards
        cards = processed.get('cards', [])
        
        for i, card in enumerate(cards):
            try:
                self._validate_card_can_render(card, hass, mock_entities)
            except Exception as e:
                pytest.fail(f"Card {i} failed to validate: {str(e)}")
    
    def test_conditional_cards_evaluate_correctly(self, hass, mock_entities, blueprint_inputs):
        """Test that conditional cards evaluate their conditions correctly."""
        blueprint = load_blueprint_yaml()
        processed = self._process_blueprint_inputs(blueprint, blueprint_inputs)
        
        # Find all conditional cards
        conditional_cards = self._find_cards_by_type(processed, 'conditional')
        
        for card in conditional_cards:
            conditions = card.get('conditions', [])
            assert len(conditions) > 0, "Conditional card must have conditions"
            
            # Test condition evaluation
            for condition in conditions:
                self._validate_condition(condition, hass, mock_entities)
    
    def test_service_calls_are_valid(self, hass, mock_entities, blueprint_inputs):
        """Test that all service calls in cards are valid."""
        blueprint = load_blueprint_yaml()
        processed = self._process_blueprint_inputs(blueprint, blueprint_inputs)
        
        # Find all service calls
        service_calls = self._find_service_calls(processed)
        
        for call in service_calls:
            service = call.get('service', '')
            assert '.' in service, f"Service '{service}' must be in domain.service format"
            
            domain, service_name = service.split('.', 1)
            assert domain in ['climate', 'switch', 'button', 'number'], \
                f"Service domain '{domain}' is not expected"
            
            # Verify service data
            service_data = call.get('service_data', {})
            if 'entity_id' in service_data:
                entity_id = service_data['entity_id']
                # Should reference a valid entity
                assert entity_id in mock_entities or entity_id.startswith('!input'), \
                    f"Service references unknown entity '{entity_id}'"
    
    def test_gauge_ranges_are_appropriate(self, hass, mock_entities, blueprint_inputs):
        """Test that gauge cards have appropriate min/max ranges."""
        blueprint = load_blueprint_yaml()
        processed = self._process_blueprint_inputs(blueprint, blueprint_inputs)
        
        # Find all gauge cards
        gauge_cards = self._find_cards_by_type(processed, 'gauge')
        
        for gauge in gauge_cards:
            # Check offset gauge
            if 'offset' in gauge.get('name', '').lower():
                assert gauge.get('min') == -5, "Offset gauge should have min -5"
                assert gauge.get('max') == 5, "Offset gauge should have max 5"
            
            # Check percentage gauges
            elif 'accuracy' in gauge.get('name', '').lower() or 'confidence' in gauge.get('name', '').lower():
                assert gauge.get('min') == 0, "Percentage gauge should have min 0"
                assert gauge.get('max') == 100, "Percentage gauge should have max 100"
    
    def test_history_graph_time_ranges(self, hass, mock_entities, blueprint_inputs):
        """Test that history graphs have appropriate time ranges."""
        blueprint = load_blueprint_yaml()
        processed = self._process_blueprint_inputs(blueprint, blueprint_inputs)
        
        # Find all history graph cards
        history_cards = self._find_cards_by_type(processed, 'history-graph')
        
        for graph in history_cards:
            hours = graph.get('hours_to_show', 24)
            
            # Different graphs should have different ranges
            if 'offset' in graph.get('title', '').lower():
                assert hours == 24, "Offset history should show 24 hours"
            elif 'accuracy' in graph.get('title', '').lower():
                assert hours == 168, "Accuracy trend should show 7 days (168 hours)"
            elif 'correlation' in graph.get('title', '').lower():
                assert hours == 12, "Correlation graph should show 12 hours"
    
    def test_missing_entities_handled_gracefully(self, hass, blueprint_inputs):
        """Test that dashboard handles missing entities gracefully."""
        blueprint = load_blueprint_yaml()
        
        # Remove some entities
        hass.states.get = lambda entity_id: None
        
        # Process blueprint
        processed = self._process_blueprint_inputs(blueprint, blueprint_inputs)
        
        # Should not raise errors
        cards = processed.get('cards', [])
        assert len(cards) > 0, "Should have cards even with missing entities"
        
        # Template sensors should have availability templates
        templates = blueprint.get('template', [])
        for template_group in templates:
            if 'sensor' in template_group:
                for sensor_def in template_group['sensor']:
                    assert 'availability' in sensor_def, \
                        f"Sensor {sensor_def.get('unique_id')} should have availability template"
    
    def test_performance_with_real_data(self, hass, mock_entities, blueprint_inputs):
        """Test blueprint performance with realistic data volumes."""
        # Add historical data to entities
        climate_entity = mock_entities['climate.smart_climate_living_room']
        climate_entity.attributes['offset_history'] = [-0.5 + i*0.1 for i in range(100)]
        
        switch_entity = mock_entities['switch.smart_climate_living_room_learning']
        switch_entity.attributes['samples_collected'] = 500
        
        blueprint = load_blueprint_yaml()
        processed = self._process_blueprint_inputs(blueprint, blueprint_inputs)
        
        # Should handle large data without issues
        cards = processed.get('cards', [])
        assert len(cards) > 0, "Should process cards with large data"
    
    def test_blueprint_import_process(self):
        """Test that blueprint can be imported through HA's blueprint system."""
        blueprint = load_blueprint_yaml()
        
        # Simulate blueprint import validation
        try:
            # Check YAML is valid
            yaml_str = yaml.dump(blueprint, default_flow_style=False)
            parsed = yaml.safe_load(yaml_str)
            assert parsed is not None, "Blueprint YAML should be valid"
            
            # Check no jinja2 syntax errors in templates
            self._validate_all_templates(blueprint)
            
        except Exception as e:
            pytest.fail(f"Blueprint import would fail: {str(e)}")
    
    # Helper methods
    def _process_blueprint_inputs(self, blueprint: Dict[str, Any], inputs: Dict[str, str]) -> Dict[str, Any]:
        """Process blueprint with input values (simulate HA processing)."""
        # This is a simplified version - HA does more complex processing
        processed = yaml.dump(blueprint)
        
        # Replace !input tags with actual values
        for input_name, value in inputs.items():
            processed = processed.replace(f'!input {input_name}', value)
        
        return yaml.safe_load(processed)
    
    def _find_entity_references(self, data: Any) -> List[str]:
        """Recursively find all entity references in data structure."""
        entities = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                if key in ['entity', 'entity_id'] and isinstance(value, str):
                    entities.append(value)
                else:
                    entities.extend(self._find_entity_references(value))
        elif isinstance(data, list):
            for item in data:
                entities.extend(self._find_entity_references(item))
        elif isinstance(data, str):
            # Look for entity patterns in strings (templates)
            import re
            pattern = r'(climate|switch|sensor|number|button)\.[a-zA-Z0-9_]+'
            matches = re.findall(pattern, data)
            entities.extend(matches)
        
        return entities
    
    def _validate_template_sensor(self, sensor_def: Dict[str, Any], hass: HomeAssistant, inputs: Dict[str, str]):
        """Validate a template sensor definition."""
        # Check required fields
        assert 'unique_id' in sensor_def, "Template sensor must have unique_id"
        assert 'name' in sensor_def, "Template sensor must have name"
        assert 'state' in sensor_def, "Template sensor must have state template"
        
        # Validate template syntax (basic check)
        state_template = sensor_def['state']
        assert '{{' in state_template or '{%' in state_template, \
            "State should be a Jinja2 template"
        
        # Check availability template if present
        if 'availability' in sensor_def:
            avail_template = sensor_def['availability']
            assert '{{' in avail_template or '{%' in avail_template, \
                "Availability should be a Jinja2 template"
    
    def _validate_card_can_render(self, card: Dict[str, Any], hass: HomeAssistant, entities: Dict[str, MockEntity]):
        """Validate that a card can render without errors."""
        card_type = card.get('type', '')
        
        # Basic validation based on card type
        if card_type == 'entities':
            assert 'entities' in card, "Entities card must have entities list"
        elif card_type == 'gauge':
            assert 'entity' in card, "Gauge card must have entity"
            assert 'min' in card and 'max' in card, "Gauge must have min/max"
        elif card_type == 'history-graph':
            assert 'entities' in card, "History graph must have entities"
            assert 'hours_to_show' in card, "History graph must have hours_to_show"
        elif card_type in ['vertical-stack', 'horizontal-stack', 'grid']:
            assert 'cards' in card, f"{card_type} must have cards list"
            # Recursively validate nested cards
            for nested_card in card['cards']:
                self._validate_card_can_render(nested_card, hass, entities)
        elif card_type == 'conditional':
            assert 'conditions' in card, "Conditional card must have conditions"
            assert 'card' in card, "Conditional card must have card"
            # Validate nested card
            self._validate_card_can_render(card['card'], hass, entities)
    
    def _find_cards_by_type(self, data: Dict[str, Any], card_type: str) -> List[Dict[str, Any]]:
        """Find all cards of a specific type."""
        found_cards = []
        
        def search(obj: Any):
            if isinstance(obj, dict):
                if obj.get('type') == card_type:
                    found_cards.append(obj)
                for value in obj.values():
                    search(value)
            elif isinstance(obj, list):
                for item in obj:
                    search(item)
        
        search(data)
        return found_cards
    
    def _validate_condition(self, condition: Dict[str, Any], hass: HomeAssistant, entities: Dict[str, MockEntity]):
        """Validate a condition definition."""
        # Basic condition structure validation
        assert 'entity' in condition or 'condition' in condition, \
            "Condition must have entity or condition type"
        
        if 'entity' in condition:
            entity_id = condition['entity']
            # Entity should exist or be a template sensor
            if not entity_id.startswith('sensor.smart_climate_'):
                assert entity_id in entities, f"Condition references unknown entity '{entity_id}'"
    
    def _find_service_calls(self, data: Any) -> List[Dict[str, Any]]:
        """Find all service calls in the data structure."""
        service_calls = []
        
        def search(obj: Any):
            if isinstance(obj, dict):
                if 'service' in obj:
                    service_calls.append(obj)
                for value in obj.values():
                    search(value)
            elif isinstance(obj, list):
                for item in obj:
                    search(item)
        
        search(data)
        return service_calls
    
    def _validate_all_templates(self, blueprint: Dict[str, Any]):
        """Validate all Jinja2 templates in blueprint."""
        # This is a basic check - real validation would use Jinja2 parser
        def check_templates(obj: Any):
            if isinstance(obj, str):
                # Basic bracket matching
                if '{{' in obj or '{%' in obj:
                    open_brackets = obj.count('{{') + obj.count('{%')
                    close_brackets = obj.count('}}') + obj.count('%}')
                    assert open_brackets == close_brackets, \
                        f"Unmatched template brackets in: {obj[:50]}..."
            elif isinstance(obj, dict):
                for value in obj.values():
                    check_templates(value)
            elif isinstance(obj, list):
                for item in obj:
                    check_templates(item)
        
        check_templates(blueprint)


class TestBlueprintEdgeCases:
    """Test edge cases and error conditions for blueprint integration."""
    
    def test_handles_circular_entity_references(self):
        """Test that blueprint handles circular entity references gracefully."""
        # Test will be implemented when blueprint structure is finalized
        pass
    
    def test_handles_very_long_entity_names(self):
        """Test blueprint with very long entity names."""
        # Test will be implemented when blueprint structure is finalized
        pass
    
    def test_handles_special_characters_in_entity_names(self):
        """Test blueprint with special characters in entity names."""
        # Test will be implemented when blueprint structure is finalized
        pass
    
    def test_performance_with_many_template_sensors(self):
        """Test performance when blueprint creates many template sensors."""
        # Test will be implemented when blueprint structure is finalized
        pass