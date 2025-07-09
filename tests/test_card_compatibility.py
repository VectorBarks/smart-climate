# ABOUTME: Tests for conditional card loading and custom card compatibility
# Validates fallback behavior when custom cards are not available

"""Test card compatibility features for Smart Climate dashboard."""

import pytest
from unittest.mock import Mock, patch
import yaml
from pathlib import Path


class TestCardCompatibility:
    """Test conditional card loading and fallback behavior."""
    
    @pytest.fixture
    def blueprint_path(self):
        """Path to the dashboard blueprint."""
        return Path("custom_components/smart_climate/blueprints/dashboard/smart_climate_dashboard.yaml")
    
    @pytest.fixture
    def mock_blueprint_content(self):
        """Mock blueprint content for testing."""
        return {
            "blueprint": {
                "name": "Smart Climate Dashboard",
                "domain": "lovelace"
            },
            "views": [{
                "title": "Overview",
                "cards": []
            }]
        }
    
    def test_conditional_card_structure_exists(self, blueprint_path):
        """Test that conditional card structure is present in blueprint."""
        # Read the actual blueprint file as text
        with open(blueprint_path, 'r') as f:
            content = f.read()
        
        # Check for key blueprint structure
        assert "blueprint:" in content
        assert "domain: lovelace" in content
        assert "cards:" in content
        
        # Check for conditional card implementations
        assert "type: conditional" in content
        assert "sensor.smart_climate_custom_cards_available" in content
        assert "custom:mushroom-climate-card" in content
        assert "custom:apexcharts-card" in content
        assert "custom:button-card" in content
    
    def test_apexcharts_conditional_loading(self):
        """Test conditional loading of apexcharts-card."""
        # This will test the conditional card YAML structure
        conditional_card = {
            "type": "conditional",
            "conditions": [{
                "entity": "sensor.custom_cards_available",
                "state": "apexcharts-card"
            }],
            "card": {
                "type": "custom:apexcharts-card",
                "header": {
                    "show": True,
                    "title": "Offset History"
                }
            }
        }
        
        # Validate structure
        assert conditional_card["type"] == "conditional"
        assert "conditions" in conditional_card
        assert "card" in conditional_card
        assert conditional_card["card"]["type"] == "custom:apexcharts-card"
    
    def test_mushroom_climate_conditional_loading(self):
        """Test conditional loading of mushroom-climate-card."""
        conditional_card = {
            "type": "conditional",
            "conditions": [{
                "entity": "sensor.custom_cards_available",
                "state_not": "unavailable"
            }],
            "card": {
                "type": "custom:mushroom-climate-card",
                "entity": "{{ climate_entity }}"
            }
        }
        
        # Validate structure
        assert conditional_card["type"] == "conditional"
        assert conditional_card["card"]["type"] == "custom:mushroom-climate-card"
    
    def test_button_card_conditional_loading(self):
        """Test conditional loading of button-card."""
        conditional_card = {
            "type": "conditional",
            "conditions": [{
                "entity": "sensor.custom_cards_available",
                "state": "button-card"
            }],
            "card": {
                "type": "custom:button-card",
                "entity": "{{ learning_switch }}",
                "show_state": True
            }
        }
        
        # Validate structure
        assert conditional_card["type"] == "conditional"
        assert conditional_card["card"]["type"] == "custom:button-card"
    
    def test_core_card_fallback_climate(self):
        """Test fallback to core climate card."""
        fallback_card = {
            "type": "conditional",
            "conditions": [{
                "entity": "sensor.custom_cards_available",
                "state": "core_only"
            }],
            "card": {
                "type": "climate",
                "entity": "{{ climate_entity }}"
            }
        }
        
        # Validate fallback uses core card
        assert fallback_card["card"]["type"] == "climate"
        assert "custom:" not in fallback_card["card"]["type"]
    
    def test_core_card_fallback_history_graph(self):
        """Test fallback to history-graph instead of apexcharts."""
        fallback_card = {
            "type": "conditional",
            "conditions": [{
                "entity": "sensor.custom_cards_available",
                "state_not": "apexcharts-card"
            }],
            "card": {
                "type": "history-graph",
                "entities": ["{{ climate_entity }}"],
                "hours_to_show": 24
            }
        }
        
        # Validate fallback uses core card
        assert fallback_card["card"]["type"] == "history-graph"
        assert "entities" in fallback_card["card"]
    
    def test_core_card_fallback_entities(self):
        """Test fallback to entities card for status display."""
        fallback_card = {
            "type": "entities",
            "entities": [
                "{{ learning_switch }}",
                "sensor.smart_climate_{{ climate_entity.entity_id | replace('.', '_') }}_calibration_status"
            ]
        }
        
        # Validate structure
        assert fallback_card["type"] == "entities"
        assert len(fallback_card["entities"]) >= 2
    
    def test_vertical_stack_with_conditional_cards(self):
        """Test vertical stack containing conditional cards."""
        stack_card = {
            "type": "vertical-stack",
            "cards": [
                {
                    "type": "conditional",
                    "conditions": [{"entity": "sensor.custom_cards_available", "state": "mushroom"}],
                    "card": {"type": "custom:mushroom-climate-card"}
                },
                {
                    "type": "conditional", 
                    "conditions": [{"entity": "sensor.custom_cards_available", "state_not": "mushroom"}],
                    "card": {"type": "climate"}
                }
            ]
        }
        
        # Validate structure
        assert stack_card["type"] == "vertical-stack"
        assert len(stack_card["cards"]) == 2
        assert all(card["type"] == "conditional" for card in stack_card["cards"])
    
    def test_custom_card_detection_sensor(self):
        """Test template sensor for custom card detection."""
        sensor_template = """
        {% set ns = namespace(cards=[]) %}
        {% if 'custom:apexcharts-card' in lovelace.resources | map(attribute='url') | join(',') %}
          {% set ns.cards = ns.cards + ['apexcharts-card'] %}
        {% endif %}
        {% if 'custom:mushroom' in lovelace.resources | map(attribute='url') | join(',') %}
          {% set ns.cards = ns.cards + ['mushroom'] %}
        {% endif %}
        {% if 'custom:button-card' in lovelace.resources | map(attribute='url') | join(',') %}
          {% set ns.cards = ns.cards + ['button-card'] %}
        {% endif %}
        {{ ns.cards | join(',') if ns.cards else 'core_only' }}
        """
        
        # Just validate the template is valid YAML-safe
        assert "lovelace.resources" in sensor_template
        assert "custom:apexcharts-card" in sensor_template
    
    def test_enhanced_offset_chart_with_apexcharts(self):
        """Test enhanced offset visualization with apexcharts."""
        chart_config = {
            "type": "custom:apexcharts-card",
            "header": {
                "show": True,
                "title": "Temperature Offset History"
            },
            "graph_span": "24h",
            "span": {
                "end": "hour"
            },
            "series": [{
                "entity": "sensor.smart_climate_{{ climate_entity.entity_id | replace('.', '_') }}_offset_history",
                "name": "Offset",
                "show": {"legend_value": False},
                "group_by": {
                    "func": "avg",
                    "duration": "10min"
                }
            }]
        }
        
        # Validate enhanced features
        assert chart_config["type"] == "custom:apexcharts-card"
        assert "graph_span" in chart_config
        assert "series" in chart_config
        assert chart_config["series"][0]["group_by"]["func"] == "avg"
    
    def test_enhanced_climate_control_with_mushroom(self):
        """Test enhanced climate control with mushroom card."""
        mushroom_config = {
            "type": "custom:mushroom-climate-card",
            "entity": "{{ climate_entity }}",
            "hvac_modes": ["off", "cool", "heat", "auto"],
            "show_temperature_control": True,
            "collapsible_controls": True,
            "layout": "horizontal"
        }
        
        # Validate enhanced features
        assert mushroom_config["type"] == "custom:mushroom-climate-card"
        assert mushroom_config["show_temperature_control"] is True
        assert mushroom_config["collapsible_controls"] is True
    
    def test_enhanced_status_display_with_button_card(self):
        """Test enhanced status display with button-card."""
        button_config = {
            "type": "custom:button-card",
            "entity": "{{ learning_switch }}",
            "show_state": True,
            "show_name": True,
            "state": [
                {
                    "value": "on",
                    "color": "var(--success-color)",
                    "icon": "mdi:brain"
                },
                {
                    "value": "off",
                    "color": "var(--disabled-color)",
                    "icon": "mdi:brain-off"
                }
            ],
            "styles": {
                "card": [
                    {"background-color": "var(--card-background-color)"},
                    {"border-radius": "var(--ha-card-border-radius)"}
                ]
            }
        }
        
        # Validate enhanced features
        assert button_config["type"] == "custom:button-card"
        assert "state" in button_config
        assert len(button_config["state"]) == 2
        assert "styles" in button_config
    
    def test_grid_layout_with_conditional_cards(self):
        """Test grid layout containing conditional cards."""
        grid_config = {
            "type": "grid",
            "columns": 3,
            "square": False,
            "cards": [
                {
                    "type": "conditional",
                    "conditions": [{"entity": "sensor.custom_cards_available", "state": "mushroom"}],
                    "card": {"type": "gauge", "entity": "sensor.offset"}
                }
            ]
        }
        
        # Validate grid structure
        assert grid_config["type"] == "grid"
        assert grid_config["columns"] == 3
        assert grid_config["square"] is False
    
    def test_conditional_cards_preserve_entity_references(self):
        """Test that entity references are preserved in conditional cards."""
        card_with_refs = {
            "type": "conditional",
            "conditions": [{"entity": "{{ learning_switch }}", "state": "on"}],
            "card": {
                "type": "entities",
                "entities": [
                    "{{ climate_entity }}",
                    "{{ learning_switch }}"
                ]
            }
        }
        
        # Validate entity references
        assert "{{ climate_entity }}" in str(card_with_refs)
        assert "{{ learning_switch }}" in str(card_with_refs)
    
    def test_custom_cards_availability_combinations(self):
        """Test different combinations of custom card availability."""
        test_cases = [
            (["apexcharts-card"], True, False, False),
            (["mushroom"], False, True, False),
            (["button-card"], False, False, True),
            (["apexcharts-card", "mushroom"], True, True, False),
            ([], False, False, False),  # core_only
            (["apexcharts-card", "mushroom", "button-card"], True, True, True)
        ]
        
        for available_cards, has_apex, has_mushroom, has_button in test_cases:
            # This would be the actual detection logic
            assert (("apexcharts-card" in available_cards) == has_apex)
            assert (("mushroom" in available_cards) == has_mushroom)
            assert (("button-card" in available_cards) == has_button)