"""Utilities for testing dashboard blueprints."""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
import re
from datetime import datetime


def load_blueprint_yaml(blueprint_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load and parse blueprint YAML file.
    
    Args:
        blueprint_path: Path to the blueprint YAML file, defaults to smart_climate_dashboard.yaml
        
    Returns:
        Parsed YAML content as dictionary
        
    Raises:
        FileNotFoundError: If blueprint file doesn't exist
        yaml.YAMLError: If YAML is invalid
    """
    if blueprint_path is None:
        # Default to the smart climate dashboard blueprint
        blueprint_path = Path(__file__).parent.parent / "custom_components" / "smart_climate" / "blueprints" / "dashboard" / "smart_climate_dashboard.yaml"
    
    if not blueprint_path.exists():
        raise FileNotFoundError(f"Blueprint file not found: {blueprint_path}")
    
    with open(blueprint_path, 'r') as f:
        return yaml.safe_load(f)


def validate_template_expression(expression: str) -> bool:
    """Validate a Jinja2 template expression.
    
    Args:
        expression: Template expression to validate
        
    Returns:
        True if expression appears valid, False otherwise
    """
    if not isinstance(expression, str):
        return False
    
    # Check for basic template markers
    if not (expression.startswith('{{') and expression.endswith('}}')):
        return False
    
    # Check for balanced parentheses
    open_parens = expression.count('(')
    close_parens = expression.count(')')
    if open_parens != close_parens:
        return False
    
    # Check for balanced quotes
    single_quotes = expression.count("'")
    double_quotes = expression.count('"')
    if single_quotes % 2 != 0 or double_quotes % 2 != 0:
        return False
    
    return True


def validate_entity_selector(selector: Dict[str, Any]) -> bool:
    """Validate an entity selector configuration.
    
    Args:
        selector: Entity selector configuration
        
    Returns:
        True if selector is valid, False otherwise
    """
    if not isinstance(selector, dict):
        return False
    
    if 'entity' not in selector:
        return False
    
    entity_config = selector['entity']
    if not isinstance(entity_config, dict):
        return False
    
    # For smart_climate, we require filters to ensure proper entity selection
    # An empty entity selector is considered valid only if it has a filter
    if not entity_config:
        return False
    
    # Check for filter if present
    if 'filter' in entity_config:
        filter_config = entity_config['filter']
        if not isinstance(filter_config, dict):
            return False
        
        # Validate filter has at least one criterion
        if not filter_config:
            return False
    
    return True


def validate_card_configuration(card: Dict[str, Any]) -> bool:
    """Validate a Lovelace card configuration.
    
    Args:
        card: Card configuration dictionary
        
    Returns:
        True if card configuration is valid, False otherwise
    """
    if not isinstance(card, dict):
        return False
    
    # Must have a type
    if 'type' not in card:
        return False
    
    card_type = card['type']
    
    # Validate based on card type
    if card_type == 'gauge':
        # Gauge cards need entity, min, and max
        return all(key in card for key in ['entity', 'min', 'max'])
    
    elif card_type == 'entities':
        # Entities card needs entities list
        return 'entities' in card and isinstance(card['entities'], list)
    
    elif card_type == 'history-graph':
        # History graph needs entities
        return 'entities' in card and isinstance(card['entities'], list)
    
    elif card_type == 'vertical-stack' or card_type == 'horizontal-stack':
        # Stack cards need cards list
        return 'cards' in card and isinstance(card['cards'], list)
    
    elif card_type.startswith('custom:'):
        # Custom cards just need an entity or entities
        return 'entity' in card or 'entities' in card
    
    # For other card types, just check they have some configuration
    return len(card) > 1  # More than just 'type'


def create_mock_entity_state(entity_id: str, state: str, attributes: Optional[Dict] = None):
    """Create a mock entity state for testing templates.
    
    Args:
        entity_id: Entity ID
        state: Entity state value
        attributes: Optional attributes dictionary
        
    Returns:
        Mock state object
    """
    class MockState:
        def __init__(self, entity_id, state, attributes):
            self.entity_id = entity_id
            self.state = state
            self.attributes = attributes or {}
    
    return MockState(entity_id, state, attributes)


def extract_template_entities(template: str) -> list:
    """Extract entity IDs referenced in a template.
    
    Args:
        template: Jinja2 template string
        
    Returns:
        List of entity IDs found in the template
    """
    # Pattern to match states('entity.id') or state_attr('entity.id', ...)
    pattern = r"states?\s*\(\s*['\"]([^'\"]+)['\"]\s*[,)]"
    matches = re.findall(pattern, template)
    
    # Also match direct entity references like {{ entity.id }}
    direct_pattern = r"{{\s*([a-z_]+\.[a-z0-9_]+)"
    direct_matches = re.findall(direct_pattern, template)
    
    return list(set(matches + direct_matches))


def validate_blueprint_imports_in_ha(blueprint: Dict[str, Any]) -> bool:
    """Validate that a blueprint would import successfully in Home Assistant.
    
    Args:
        blueprint: Parsed blueprint dictionary
        
    Returns:
        True if blueprint appears valid for HA import
    """
    # Must have blueprint key
    if 'blueprint' not in blueprint:
        return False
    
    bp_config = blueprint['blueprint']
    
    # Required blueprint fields
    required_fields = ['name', 'description', 'domain']
    if not all(field in bp_config for field in required_fields):
        return False
    
    # Domain must be valid
    valid_domains = ['automation', 'script', 'lovelace']
    if bp_config['domain'] not in valid_domains:
        return False
    
    # If inputs defined, validate them
    if 'input' in bp_config:
        if not isinstance(bp_config['input'], dict):
            return False
        
        # Each input must have at least a name
        for input_key, input_config in bp_config['input'].items():
            if not isinstance(input_config, dict):
                return False
            if 'name' not in input_config:
                return False
    
    return True


def generate_test_climate_attributes() -> Dict[str, Any]:
    """Generate test attributes for a smart climate entity.
    
    Returns:
        Dictionary of test attributes
    """
    return {
        'current_offset': 2.5,
        'learning_progress': 45,
        'accuracy_percentage': 87.5,
        'confidence_level': 0.92,
        'samples_collected': 450,
        'calibration_samples': 10,
        'hysteresis_active': True,
        'hysteresis_start_threshold': 22.0,
        'hysteresis_stop_threshold': 24.0,
        'last_learning_timestamp': '2025-07-09T10:30:00',
        'offset_history': [
            {'timestamp': '2025-07-09T10:00:00', 'offset': 2.3},
            {'timestamp': '2025-07-09T09:30:00', 'offset': 2.1},
            {'timestamp': '2025-07-09T09:00:00', 'offset': 2.4}
        ]
    }


def validate_responsive_layout(cards: list) -> Dict[str, bool]:
    """Validate cards for responsive layout compatibility.
    
    Args:
        cards: List of card configurations
        
    Returns:
        Dictionary with 'mobile' and 'desktop' compatibility flags
    """
    mobile_compatible = True
    desktop_compatible = True
    
    for card in cards:
        if not isinstance(card, dict):
            continue
            
        # Check for mobile-unfriendly configurations
        if card.get('type') == 'horizontal-stack':
            # Horizontal stacks with too many cards aren't mobile friendly
            if len(card.get('cards', [])) > 3:
                mobile_compatible = False
        
        # Check for desktop-specific features
        if 'view_layout' in card:
            layout = card['view_layout']
            if isinstance(layout, dict) and layout.get('position') == 'sidebar':
                # Sidebar layouts are desktop-only
                desktop_compatible = True
    
    return {
        'mobile': mobile_compatible,
        'desktop': desktop_compatible
    }


def validate_card_structure(card: Dict[str, Any]) -> bool:
    """Validate the structure of a card configuration.
    
    Args:
        card: Card configuration dictionary
        
    Returns:
        True if card structure is valid
    """
    return validate_card_configuration(card)


def get_nested_cards(container: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract all nested cards from a container card.
    
    Args:
        container: Container card (stack, grid, etc.)
        
    Returns:
        List of all nested cards
    """
    cards = []
    
    if 'cards' in container:
        cards.extend(container['cards'])
        # Recursively get nested cards
        for card in container['cards']:
            cards.extend(get_nested_cards(card))
    
    if 'card' in container:
        cards.append(container['card'])
        cards.extend(get_nested_cards(container['card']))
    
    return cards


class MockEntity:
    """Mock entity for testing."""
    
    def __init__(self, entity_id: str, state: Any = None, attributes: Optional[Dict] = None):
        self.entity_id = entity_id
        self.state = state
        self.attributes = attributes or {}
        self.last_updated = datetime.now()
        self.last_changed = datetime.now()
    
    def __repr__(self):
        return f"<MockEntity({self.entity_id}={self.state})>"


def create_mock_climate_entity(entity_id: str, current_temperature: float = 22.0, 
                             target_temperature: float = 23.0, preset_mode: str = 'none',
                             attributes: Optional[Dict] = None) -> MockEntity:
    """Create a mock climate entity for testing.
    
    Args:
        entity_id: Entity ID
        current_temperature: Current temperature
        target_temperature: Target temperature
        preset_mode: Preset mode
        attributes: Additional attributes
        
    Returns:
        MockEntity instance
    """
    base_attributes = {
        'current_temperature': current_temperature,
        'temperature': target_temperature,
        'preset_mode': preset_mode,
        'hvac_modes': ['off', 'cool', 'heat', 'auto'],
        'preset_modes': ['none', 'away', 'sleep', 'boost'],
        'min_temp': 16,
        'max_temp': 30,
        'friendly_name': entity_id.split('.')[-1].replace('_', ' ').title()
    }
    
    if attributes:
        base_attributes.update(attributes)
    
    return MockEntity(entity_id, 'cool', base_attributes)


def create_mock_switch_entity(entity_id: str, state: str = 'on', 
                            attributes: Optional[Dict] = None) -> MockEntity:
    """Create a mock switch entity for testing.
    
    Args:
        entity_id: Entity ID
        state: Switch state ('on' or 'off')
        attributes: Additional attributes
        
    Returns:
        MockEntity instance
    """
    base_attributes = {
        'friendly_name': entity_id.split('.')[-1].replace('_', ' ').title()
    }
    
    if attributes:
        base_attributes.update(attributes)
    
    return MockEntity(entity_id, state, base_attributes)


def create_mock_sensor_entity(entity_id: str, state: Any = 0, 
                            device_class: Optional[str] = None,
                            unit: Optional[str] = None,
                            attributes: Optional[Dict] = None) -> MockEntity:
    """Create a mock sensor entity for testing.
    
    Args:
        entity_id: Entity ID
        state: Sensor state value
        device_class: Device class (temperature, power, etc.)
        unit: Unit of measurement
        attributes: Additional attributes
        
    Returns:
        MockEntity instance
    """
    base_attributes = {
        'friendly_name': entity_id.split('.')[-1].replace('_', ' ').title()
    }
    
    if device_class:
        base_attributes['device_class'] = device_class
    
    if unit:
        base_attributes['unit_of_measurement'] = unit
    
    if attributes:
        base_attributes.update(attributes)
    
    return MockEntity(entity_id, state, base_attributes)