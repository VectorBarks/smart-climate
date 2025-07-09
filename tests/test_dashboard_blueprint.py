"""Test the dashboard blueprint structure and validation."""

import sys
import os
import yaml
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.dashboard_test_utils import (
    load_blueprint_yaml,
    validate_template_expression,
    validate_entity_selector,
    validate_card_configuration
)


class TestBlueprintStructure:
    """Test blueprint has correct structure."""
    
    @pytest.fixture
    def blueprint_path(self):
        """Get the blueprint file path."""
        return Path("custom_components/smart_climate/blueprints/dashboard/smart_climate_dashboard.yaml")
    
    def test_blueprint_has_required_metadata(self, blueprint_path):
        """Test blueprint has all required metadata fields."""
        blueprint = load_blueprint_yaml(blueprint_path)
        
        assert 'blueprint' in blueprint
        assert 'name' in blueprint['blueprint']
        assert 'description' in blueprint['blueprint']
        assert 'domain' in blueprint['blueprint']
        assert 'input' in blueprint['blueprint']
        
        # Validate metadata values
        assert blueprint['blueprint']['name'] == "Smart Climate Dashboard"
        assert "visualization" in blueprint['blueprint']['description'].lower()
        assert blueprint['blueprint']['domain'] == "lovelace"
    
    def test_blueprint_inputs_are_valid(self, blueprint_path):
        """Test blueprint input specifications are valid."""
        blueprint = load_blueprint_yaml(blueprint_path)
        
        inputs = blueprint['blueprint']['input']
        
        # Required inputs
        assert 'climate_entity' in inputs
        assert 'learning_switch' in inputs
        
        # Validate climate entity input
        climate_input = inputs['climate_entity']
        assert 'name' in climate_input
        assert 'description' in climate_input
        assert 'selector' in climate_input
        assert 'entity' in climate_input['selector']
        
        # Validate learning switch input
        switch_input = inputs['learning_switch']
        assert 'name' in switch_input
        assert 'description' in switch_input
        assert 'selector' in switch_input
        assert 'entity' in switch_input['selector']
    
    def test_blueprint_yaml_is_parseable(self, blueprint_path):
        """Test blueprint YAML is valid and parseable."""
        try:
            blueprint = load_blueprint_yaml(blueprint_path)
            assert isinstance(blueprint, dict)
        except yaml.YAMLError as e:
            pytest.fail(f"Blueprint YAML is not parseable: {e}")
    
    def test_all_entity_selectors_have_filters(self, blueprint_path):
        """Test all entity selectors have proper filters."""
        blueprint = load_blueprint_yaml(blueprint_path)
        
        inputs = blueprint['blueprint']['input']
        
        # Check climate entity filter
        climate_filter = inputs['climate_entity']['selector']['entity'].get('filter', {})
        assert climate_filter.get('integration') == 'smart_climate'
        assert climate_filter.get('domain') == 'climate'
        
        # Check learning switch filter
        switch_filter = inputs['learning_switch']['selector']['entity'].get('filter', {})
        assert switch_filter.get('integration') == 'smart_climate'
        assert switch_filter.get('domain') == 'switch'


class TestBlueprintContent:
    """Test blueprint content and dashboard configuration."""
    
    @pytest.fixture
    def blueprint_path(self):
        """Get the blueprint file path."""
        return Path("custom_components/smart_climate/blueprints/dashboard/smart_climate_dashboard.yaml")
    
    @pytest.fixture
    def blueprint(self, blueprint_path):
        """Load the blueprint."""
        return load_blueprint_yaml(blueprint_path)
    
    def test_dashboard_has_title(self, blueprint):
        """Test dashboard configuration has a title."""
        # Blueprint should define a dashboard
        assert 'title' in blueprint or 'views' in blueprint
    
    def test_dashboard_has_views(self, blueprint):
        """Test dashboard has at least one view."""
        if 'views' in blueprint:
            assert len(blueprint['views']) > 0
            assert 'title' in blueprint['views'][0]
    
    def test_template_sensors_defined(self, blueprint):
        """Test template sensors are defined in blueprint."""
        # This test will check for template sensor definitions
        # once they're added by Agent 2
        pass  # Placeholder for Agent 2's work
    
    def test_cards_reference_valid_entities(self, blueprint):
        """Test all cards reference valid entity patterns."""
        # This test will validate card configurations
        # once they're added by Agent 4
        pass  # Placeholder for Agent 4's work


class TestBlueprintValidation:
    """Test blueprint validation utilities."""
    
    def test_validate_template_expression(self):
        """Test template expression validation."""
        # Valid expressions
        assert validate_template_expression("{{ states('sensor.test') }}")
        assert validate_template_expression("{{ state_attr('climate.test', 'offset') }}")
        
        # Invalid expressions
        assert not validate_template_expression("{{ states(")
        assert not validate_template_expression("invalid template")
    
    def test_validate_entity_selector(self):
        """Test entity selector validation."""
        valid_selector = {
            'entity': {
                'filter': {
                    'integration': 'smart_climate',
                    'domain': 'climate'
                }
            }
        }
        assert validate_entity_selector(valid_selector)
        
        # Missing filter
        invalid_selector = {'entity': {}}
        assert not validate_entity_selector(invalid_selector)
    
    def test_validate_card_configuration(self):
        """Test card configuration validation."""
        # Valid gauge card
        valid_gauge = {
            'type': 'gauge',
            'entity': 'sensor.test',
            'min': 0,
            'max': 100
        }
        assert validate_card_configuration(valid_gauge)
        
        # Invalid card (missing type)
        invalid_card = {'entity': 'sensor.test'}
        assert not validate_card_configuration(invalid_card)


class TestBlueprintStructureValidation:
    """Test complete blueprint structure validation."""
    
    @pytest.fixture
    def blueprint_path(self):
        """Get the blueprint file path."""
        return Path("custom_components/smart_climate/blueprints/dashboard/smart_climate_dashboard.yaml")
    
    def test_blueprint_directory_exists(self):
        """Test blueprint directory structure exists."""
        blueprint_dir = Path("custom_components/smart_climate/blueprints/dashboard")
        assert blueprint_dir.exists()
        assert blueprint_dir.is_dir()
    
    def test_blueprint_file_exists(self, blueprint_path):
        """Test blueprint file exists."""
        assert blueprint_path.exists()
        assert blueprint_path.is_file()
        assert blueprint_path.suffix == '.yaml'
    
    def test_blueprint_follows_ha_conventions(self, blueprint_path):
        """Test blueprint follows Home Assistant naming conventions."""
        # File name should be snake_case
        assert '_' in blueprint_path.stem
        assert blueprint_path.stem.islower()
        
        # Blueprint should be in correct directory
        assert 'blueprints' in str(blueprint_path)
        assert 'dashboard' in str(blueprint_path)