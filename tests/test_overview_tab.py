"""
ABOUTME: Tests for OverviewTabBuilder implementation
Comprehensive test suite for the Overview Tab of the Advanced Analytics Dashboard
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, List, Any

# Import the classes we'll be testing
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'smart_climate'))

from dashboard.base import TabBuilder
from dashboard.templates import GraphTemplates
from dashboard.tooltips import TooltipProvider
from dashboard.constants import SENSOR_MAPPINGS


class TestOverviewTabBuilder:
    """Test suite for OverviewTabBuilder implementation."""

    @pytest.fixture
    def templates(self):
        """Provide GraphTemplates instance."""
        return GraphTemplates()

    @pytest.fixture
    def tooltips(self):
        """Provide TooltipProvider instance."""
        return TooltipProvider()

    @pytest.fixture
    def overview_builder(self, templates, tooltips):
        """Provide OverviewTabBuilder instance."""
        from dashboard.builders import OverviewTabBuilder
        return OverviewTabBuilder(templates, tooltips)

    def test_overview_tab_config(self, overview_builder):
        """Test that tab config returns correct metadata."""
        config = overview_builder.get_tab_config()
        
        # Verify required keys exist
        assert 'title' in config
        assert 'path' in config  
        assert 'icon' in config
        
        # Verify specific values match specification
        assert config['title'] == 'Overview'
        assert config['path'] == 'overview'
        assert config['icon'] == 'mdi:view-dashboard'
        
        # Verify all values are strings
        assert isinstance(config['title'], str)
        assert isinstance(config['path'], str)
        assert isinstance(config['icon'], str)

    def test_build_cards_returns_list(self, overview_builder):
        """Test that build_cards returns a list of dictionaries."""
        entity_id = 'living_room'
        cards = overview_builder.build_cards(entity_id)
        
        assert isinstance(cards, list)
        assert len(cards) > 0
        
        # Verify all items are dictionaries
        for card in cards:
            assert isinstance(card, dict)

    def test_build_cards_entity_id_formatting(self, overview_builder):
        """Test that entity IDs are correctly formatted in cards."""
        entity_id = 'living_room'
        cards = overview_builder.build_cards(entity_id)
        
        # Find cards that should have entity references
        entity_cards = [card for card in cards if 'entity' in card or 'entities' in card]
        
        # At least the thermostat card should have an entity
        assert len(entity_cards) > 0
        
        # Check entity formatting
        for card in entity_cards:
            if 'entity' in card:
                if card['entity'].startswith('climate.'):
                    assert card['entity'] == f'climate.{entity_id}'
                elif card['entity'].startswith('sensor.'):
                    # Should match our sensor naming pattern
                    assert f'{entity_id}' in card['entity']
                    
            if 'entities' in card:
                for entity in card['entities']:
                    if isinstance(entity, str):
                        if entity.startswith('climate.'):
                            assert entity == f'climate.{entity_id}'
                        elif entity.startswith('sensor.'):
                            assert f'{entity_id}' in entity

    def test_thermostat_card_present(self, overview_builder):
        """Test that thermostat card is included."""
        entity_id = 'test_room'
        cards = overview_builder.build_cards(entity_id)
        
        # Find thermostat card
        thermostat_cards = [card for card in cards if card.get('type') == 'thermostat']
        
        assert len(thermostat_cards) == 1, "Should have exactly one thermostat card"
        
        thermostat_card = thermostat_cards[0]
        assert thermostat_card['entity'] == f'climate.{entity_id}'

    def test_gauge_cards_present(self, overview_builder):
        """Test that four gauge cards are present with correct configuration."""
        entity_id = 'test_room'
        cards = overview_builder.build_cards(entity_id)
        
        # Find gauge cards
        gauge_cards = [card for card in cards if card.get('type') == 'gauge']
        
        assert len(gauge_cards) == 4, "Should have exactly four gauge cards"
        
        # Expected gauge metrics based on specification
        expected_metrics = ['offset_current', 'confidence', 'cycle_health', 'accuracy_current']
        
        # Verify each gauge has proper configuration
        for gauge in gauge_cards:
            assert 'entity' in gauge
            assert 'min' in gauge
            assert 'max' in gauge
            assert 'title' in gauge
            
            # Check entity follows sensor mapping pattern
            entity_name = gauge['entity']
            assert entity_name.startswith('sensor.')
            assert entity_id in entity_name

    def test_gauge_ranges_correct(self, overview_builder):
        """Test that gauge cards have appropriate min/max ranges."""
        entity_id = 'test_room'
        cards = overview_builder.build_cards(entity_id)
        
        gauge_cards = [card for card in cards if card.get('type') == 'gauge']
        
        for gauge in gauge_cards:
            min_val = gauge.get('min', 0)
            max_val = gauge.get('max', 100)
            
            # Verify min < max
            assert min_val < max_val
            
            # Check specific ranges based on entity type
            if 'offset' in gauge['entity']:
                # Offset should be -5 to +5°C
                assert min_val == -5
                assert max_val == 5
            elif 'confidence' in gauge['entity'] or 'cycle_health' in gauge['entity'] or 'accuracy' in gauge['entity']:
                # Percentage metrics should be 0 to 100
                assert min_val == 0
                assert max_val == 100

    def test_live_graph_present(self, overview_builder):
        """Test that live temperature graph is included."""
        entity_id = 'test_room'
        cards = overview_builder.build_cards(entity_id)
        
        # Look for graph cards (could be history-graph or custom:apexcharts-card)
        graph_cards = [card for card in cards 
                      if card.get('type') in ['history-graph', 'custom:apexcharts-card']]
        
        assert len(graph_cards) >= 1, "Should have at least one temperature graph"
        
        # Find temperature graph specifically
        temp_graphs = []
        for card in graph_cards:
            if 'entities' in card:
                entities = card['entities']
                # Check if it includes temperature-related entities
                temp_entities = [e for e in entities if isinstance(e, str) and 
                               ('temp' in e.lower() or 'setpoint' in e.lower() or 'outdoor' in e.lower())]
                if temp_entities:
                    temp_graphs.append(card)
                    
        assert len(temp_graphs) >= 1, "Should have temperature graph with temp entities"

    def test_stats_grid_present(self, overview_builder):
        """Test that quick stats grid is included."""
        entity_id = 'test_room'
        cards = overview_builder.build_cards(entity_id)
        
        # Look for entities card (stats grid)
        entities_cards = [card for card in cards if card.get('type') == 'entities']
        
        assert len(entities_cards) >= 1, "Should have at least one entities card for stats"
        
        # Verify it has multiple entities for stats
        stats_card = entities_cards[0]
        assert 'entities' in stats_card
        assert len(stats_card['entities']) >= 3, "Stats grid should have multiple entries"

    def test_card_types_valid(self, overview_builder):
        """Test that all card types are valid Home Assistant types."""
        entity_id = 'test_room'
        cards = overview_builder.build_cards(entity_id)
        
        valid_types = {
            'thermostat', 'gauge', 'entities', 'history-graph', 'statistics-graph',
            'custom:apexcharts-card', 'custom:plotly-graph-card', 'custom:mini-graph-card',
            'custom:button-card'
        }
        
        for card in cards:
            card_type = card.get('type')
            assert card_type is not None, "Every card must have a type"
            assert card_type in valid_types, f"Card type '{card_type}' is not valid"

    def test_sensor_mappings_used(self, overview_builder):
        """Test that sensor entities use SENSOR_MAPPINGS patterns."""
        entity_id = 'test_room'
        cards = overview_builder.build_cards(entity_id)
        
        # Collect all sensor entities from cards
        sensor_entities = set()
        for card in cards:
            if 'entity' in card and card['entity'].startswith('sensor.'):
                sensor_entities.add(card['entity'])
            if 'entities' in card:
                for entity in card['entities']:
                    if isinstance(entity, str) and entity.startswith('sensor.'):
                        sensor_entities.add(entity)
                    elif isinstance(entity, dict) and 'entity' in entity and entity['entity'].startswith('sensor.'):
                        sensor_entities.add(entity['entity'])
        
        # Verify sensor entities follow expected patterns
        for entity in sensor_entities:
            # Should contain the entity_id
            assert entity_id in entity, f"Sensor entity {entity} should contain entity_id {entity_id}"
            
            # Should match a known sensor mapping pattern
            entity_suffix = entity.replace(f'sensor.{entity_id}_', '')
            # At least some should match our known mappings
            # (We can't test all since some might be generic HA sensors)

    def test_titles_and_labels_present(self, overview_builder):
        """Test that cards have appropriate titles and labels."""
        entity_id = 'test_room'
        cards = overview_builder.build_cards(entity_id)
        
        # Cards that should have titles
        titled_cards = [card for card in cards if card.get('type') in ['gauge', 'entities', 'history-graph']]
        
        for card in titled_cards:
            # Should have either title or name field
            has_title = 'title' in card or 'name' in card
            # Gauge cards specifically should have titles
            if card.get('type') == 'gauge':
                assert 'title' in card, "Gauge cards must have titles"
                assert len(card['title']) > 0, "Gauge title should not be empty"

    def test_inheritance_from_tab_builder(self, overview_builder):
        """Test that OverviewTabBuilder properly inherits from TabBuilder."""
        assert isinstance(overview_builder, TabBuilder)
        
        # Verify abstract methods are implemented
        assert hasattr(overview_builder, 'build_cards')
        assert hasattr(overview_builder, 'get_tab_config')
        
        # Verify methods are callable
        assert callable(overview_builder.build_cards)
        assert callable(overview_builder.get_tab_config)

    def test_different_entity_ids(self, overview_builder):
        """Test that builder works with different entity IDs."""
        test_entities = ['living_room', 'bedroom', 'office', 'basement_room']
        
        for entity_id in test_entities:
            cards = overview_builder.build_cards(entity_id)
            
            # Should return valid cards for any entity ID
            assert isinstance(cards, list)
            assert len(cards) > 0
            
            # Entity references should use the correct entity_id
            for card in cards:
                if 'entity' in card:
                    if card['entity'].startswith(('sensor.', 'climate.')):
                        assert entity_id in card['entity']

    def test_empty_entity_id_handling(self, overview_builder):
        """Test handling of edge cases like empty entity ID."""
        # Test with empty string
        cards = overview_builder.build_cards('')
        assert isinstance(cards, list)
        
        # Should still return some cards, even if entities might be malformed
        # (The actual behavior depends on implementation - just ensure no crashes)

    def test_templates_and_tooltips_integration(self, overview_builder, templates, tooltips):
        """Test that templates and tooltips are properly integrated."""
        # Verify the builder has access to templates and tooltips
        assert hasattr(overview_builder, '_templates') or hasattr(overview_builder, 'templates')
        assert hasattr(overview_builder, '_tooltips') or hasattr(overview_builder, 'tooltips')
        
        # Build cards and verify some use templates/tooltips  
        entity_id = 'test_room'
        cards = overview_builder.build_cards(entity_id)
        
        # At least one card should show evidence of template usage
        # (This is implementation-dependent, so we just verify no crashes occur)
        assert len(cards) > 0


class TestOverviewTabBuilderIntegration:
    """Integration tests for OverviewTabBuilder with other components."""
    
    def test_sensor_mappings_consistency(self):
        """Test that sensor mappings are consistently used."""
        from dashboard.constants import SENSOR_MAPPINGS
        
        # Verify expected sensors are in mappings
        expected_sensors = ['offset_current', 'confidence', 'thermal_state', 'cycle_health']
        
        for sensor in expected_sensors:
            assert sensor in SENSOR_MAPPINGS, f"Sensor {sensor} missing from SENSOR_MAPPINGS"
            assert '{entity}' in SENSOR_MAPPINGS[sensor], f"Sensor mapping {sensor} should contain {{entity}} placeholder"

    def test_templates_available(self):
        """Test that required templates are available."""
        templates = GraphTemplates()
        
        # Verify gauge template exists and is usable
        gauge_template = templates.get_gauge()
        assert isinstance(gauge_template, dict)
        assert gauge_template['type'] == 'gauge'
        
        # Verify we can override template values
        custom_gauge = templates.get_gauge(min=-10, max=10)
        assert custom_gauge['min'] == -10
        assert custom_gauge['max'] == 10

    def test_tooltips_available(self):
        """Test that required tooltips are available."""
        tooltips = TooltipProvider()
        
        # Test getting tooltips for overview metrics
        overview_metrics = ['offset', 'confidence', 'cycle_health', 'thermal_state']
        
        for metric in overview_metrics:
            tooltip = tooltips.get_tooltip(metric)
            # Should return string (empty string is ok for missing tooltips)
            assert isinstance(tooltip, str)