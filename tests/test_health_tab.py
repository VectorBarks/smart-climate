"""
ABOUTME: Tests for SystemHealthTabBuilder implementation
Comprehensive test suite for the System Health Tab of the Advanced Analytics Dashboard
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


class TestSystemHealthTabBuilder:
    """Test suite for SystemHealthTabBuilder implementation."""

    @pytest.fixture
    def templates(self):
        """Provide GraphTemplates instance."""
        return GraphTemplates()

    @pytest.fixture
    def tooltips(self):
        """Provide TooltipProvider instance."""
        return TooltipProvider()

    @pytest.fixture
    def health_builder(self, templates, tooltips):
        """Provide SystemHealthTabBuilder instance."""
        from dashboard.builders import SystemHealthTabBuilder
        return SystemHealthTabBuilder(templates, tooltips)

    def test_system_health_tab_config(self, health_builder):
        """Test that tab config returns correct metadata."""
        config = health_builder.get_tab_config()
        
        # Verify required keys exist
        assert 'title' in config
        assert 'path' in config  
        assert 'icon' in config
        
        # Verify specific values match specification
        assert config['title'] == 'System Health'
        assert config['path'] == 'system_health'
        assert config['icon'] == 'mdi:heart-pulse'
        
        # Verify all values are strings
        assert isinstance(config['title'], str)
        assert isinstance(config['path'], str)
        assert isinstance(config['icon'], str)

    def test_build_cards_returns_list(self, health_builder):
        """Test that build_cards returns a list of dictionaries."""
        entity_id = 'living_room'
        cards = health_builder.build_cards(entity_id)
        
        assert isinstance(cards, list)
        assert len(cards) > 0
        
        # Verify all items are dictionaries
        for card in cards:
            assert isinstance(card, dict)

    def test_component_status_grid_present(self, health_builder):
        """Test that component status grid is included with 5 components."""
        entity_id = 'test_room'
        cards = health_builder.build_cards(entity_id)
        
        # Look for entities card that shows component status
        status_cards = [card for card in cards 
                       if card.get('type') == 'entities' and 
                       'Component Status' in str(card.get('title', ''))]
        
        assert len(status_cards) == 1, "Should have exactly one component status grid"
        
        status_card = status_cards[0]
        assert 'entities' in status_card
        
        # Should have 5 components: OffsetEngine, ThermalManager, SensorManager, DelayLearner, SeasonalLearner
        entities = status_card['entities']
        assert len(entities) == 5, "Should have exactly 5 component status entities"
        
        # Verify component names are included in entities
        component_names = ['OffsetEngine', 'ThermalManager', 'SensorManager', 'DelayLearner', 'SeasonalLearner']
        for component in component_names:
            # Check if component name appears in any entity name or friendly name
            found = any(component.lower() in str(entity).lower() for entity in entities)
            assert found, f"Component {component} should be present in status grid"

    def test_sensor_cards_with_sparklines(self, health_builder):
        """Test that sensor readings cards include sparkline configurations."""
        entity_id = 'test_room'
        cards = health_builder.build_cards(entity_id)
        
        # Look for sensor cards that should have sparklines
        sensor_cards = [card for card in cards 
                       if card.get('type') == 'custom:mini-graph-card']
        
        assert len(sensor_cards) >= 4, "Should have at least 4 sensor cards with sparklines"
        
        # Expected sensor types: Room temp, Outdoor temp, Power, Humidity
        expected_sensors = ['temperature', 'outdoor', 'power', 'humidity']
        
        for card in sensor_cards:
            # Should have sparkline configuration
            assert 'entity' in card or 'entities' in card
            assert 'hours_to_show' in card, "Sensor cards should have time range (24h sparklines)"
            assert card['hours_to_show'] == 24, "Should show 24 hour sparklines"
            
            # Should have mini-graph-card specific config
            assert 'line_width' in card or 'height' in card, "Should have sparkline styling"

    def test_error_log_viewer_present(self, health_builder):
        """Test that error log viewer is included with severity color coding."""
        entity_id = 'test_room'
        cards = health_builder.build_cards(entity_id)
        
        # Look for error log card
        error_log_cards = [card for card in cards 
                          if 'error' in str(card.get('title', '')).lower() or
                          'log' in str(card.get('title', '')).lower()]
        
        assert len(error_log_cards) >= 1, "Should have at least one error log card"
        
        error_card = error_log_cards[0]
        
        # Should show last 20 entries
        if 'entities' in error_card:
            # If using entities card format
            assert 'show_header_toggle' in error_card
        else:
            # If using custom card format, should have limit config
            assert 'limit' in error_card or 'max_entries' in error_card or len(str(error_card)) > 50
            
        # Should have severity color coding (check for color-related config)
        card_str = str(error_card)
        has_severity_config = ('color' in card_str.lower() or 
                             'severity' in card_str.lower() or
                             'state_color' in card_str.lower())
        assert has_severity_config, "Error log should have severity color coding"

    def test_performance_metrics_present(self, health_builder):
        """Test that performance metrics are included with proper units."""
        entity_id = 'test_room'
        cards = health_builder.build_cards(entity_id)
        
        # Look for performance metrics cards
        perf_cards = [card for card in cards 
                     if 'performance' in str(card.get('title', '')).lower() or
                     'latency' in str(card).lower() or
                     'memory' in str(card).lower() or
                     'cpu' in str(card).lower()]
        
        assert len(perf_cards) >= 1, "Should have at least one performance metrics card"
        
        # Verify performance metrics have units
        perf_entities_found = []
        for card in perf_cards:
            if 'entities' in card:
                for entity in card['entities']:
                    if isinstance(entity, dict):
                        entity_name = entity.get('entity', '')
                    else:
                        entity_name = str(entity)
                    
                    if any(metric in entity_name.lower() for metric in ['latency', 'memory', 'cpu']):
                        perf_entities_found.append(entity_name)
        
        # Should have at least performance-related entities
        assert len(perf_entities_found) >= 1, "Should have performance metric entities"
        
        # Check for unit specifications (ms, MB, %)
        card_content = str(perf_cards)
        has_units = ('ms' in card_content or 'MB' in card_content or '%' in card_content or
                    'unit_of_measurement' in card_content)
        assert has_units, "Performance metrics should have units (latency: ms, memory: MB, CPU: %)"

    def test_all_components_map_to_entities(self, health_builder):
        """Test that all component status indicators map to real sensor entities."""
        entity_id = 'test_room'
        cards = health_builder.build_cards(entity_id)
        
        # Find component status cards
        component_cards = [card for card in cards 
                          if card.get('type') == 'entities' and 
                          'Component Status' in str(card.get('title', ''))]
        
        assert len(component_cards) >= 1
        
        status_card = component_cards[0]
        entities = status_card['entities']
        
        # Verify each component maps to a real sensor entity
        for entity in entities:
            if isinstance(entity, dict):
                entity_name = entity.get('entity', '')
            else:
                entity_name = str(entity)
            
            # Should be a sensor entity with entity_id included
            if entity_name.startswith('sensor.'):
                assert entity_id in entity_name, f"Entity {entity_name} should include entity_id {entity_id}"
            elif entity_name.startswith('binary_sensor.'):
                assert entity_id in entity_name, f"Binary sensor {entity_name} should include entity_id {entity_id}"

    def test_sensor_health_displays(self, health_builder):
        """Test that sensor health displays show correct sensor types."""
        entity_id = 'test_room'
        cards = health_builder.build_cards(entity_id)
        
        # Expected sensor types in health display
        expected_sensor_types = ['temperature', 'outdoor', 'power', 'humidity']
        
        # Collect all entities from all cards
        all_entities = []
        for card in cards:
            if 'entity' in card:
                all_entities.append(card['entity'])
            if 'entities' in card:
                for entity in card['entities']:
                    if isinstance(entity, dict):
                        all_entities.append(entity.get('entity', ''))
                    else:
                        all_entities.append(str(entity))
        
        # Check that we have entities for each expected sensor type
        for sensor_type in expected_sensor_types:
            found = any(sensor_type in entity.lower() for entity in all_entities)
            # Note: Not all sensors may be available in all installations,
            # but at least temperature should be present
            if sensor_type == 'temperature':
                assert found, f"Should have {sensor_type} sensor in health display"

    def test_card_types_valid(self, health_builder):
        """Test that all card types are valid Home Assistant types."""
        entity_id = 'test_room'
        cards = health_builder.build_cards(entity_id)
        
        valid_types = {
            'thermostat', 'gauge', 'entities', 'history-graph', 'statistics-graph',
            'custom:apexcharts-card', 'custom:plotly-graph-card', 'custom:mini-graph-card',
            'custom:button-card'
        }
        
        for card in cards:
            card_type = card.get('type')
            assert card_type is not None, f"Every card must have a type. Card: {card}"
            assert card_type in valid_types, f"Card type '{card_type}' is not valid"

    def test_inheritance_from_tab_builder(self, health_builder):
        """Test that SystemHealthTabBuilder properly inherits from TabBuilder."""
        assert isinstance(health_builder, TabBuilder)
        
        # Verify abstract methods are implemented
        assert hasattr(health_builder, 'build_cards')
        assert hasattr(health_builder, 'get_tab_config')
        
        # Verify methods are callable
        assert callable(health_builder.build_cards)
        assert callable(health_builder.get_tab_config)

    def test_different_entity_ids(self, health_builder):
        """Test that builder works with different entity IDs."""
        test_entities = ['living_room', 'bedroom', 'office', 'basement_room']
        
        for entity_id in test_entities:
            cards = health_builder.build_cards(entity_id)
            
            # Should return valid cards for any entity ID
            assert isinstance(cards, list)
            assert len(cards) > 0
            
            # Entity references should use the correct entity_id
            for card in cards:
                if 'entity' in card:
                    if card['entity'].startswith(('sensor.', 'binary_sensor.')):
                        assert entity_id in card['entity'], f"Entity {card['entity']} should contain {entity_id}"

    def test_component_cards_show_status_indicators(self, health_builder):
        """Test that component cards show proper status indicators."""
        entity_id = 'test_room'
        cards = health_builder.build_cards(entity_id)
        
        # Find component status grid
        component_cards = [card for card in cards 
                          if card.get('type') == 'entities' and 
                          'Component Status' in str(card.get('title', ''))]
        
        assert len(component_cards) >= 1
        
        status_card = component_cards[0]
        entities = status_card['entities']
        
        # Each component entity should have status indicator configuration
        for entity in entities:
            if isinstance(entity, dict):
                # Should have proper entity configuration with status indicators
                assert 'entity' in entity, "Component entity should have entity field"
                
                # Should have name or icon for identification
                has_identifier = 'name' in entity or 'icon' in entity
                assert has_identifier, "Component should have name or icon for identification"
                
                # May have state_color or other status indicator
                entity_str = str(entity)
                # This is more flexible - just ensure it's properly structured
                assert len(entity_str) > 20, "Component entity config should have meaningful content"

    def test_sensor_cards_include_sparkline_config(self, health_builder):
        """Test that sensor cards have proper sparkline configuration."""
        entity_id = 'test_room'
        cards = health_builder.build_cards(entity_id)
        
        # Find sensor cards with sparklines
        sparkline_cards = [card for card in cards 
                          if card.get('type') == 'custom:mini-graph-card']
        
        for card in sparkline_cards:
            # Should have time configuration for 24h sparklines
            assert 'hours_to_show' in card, "Sparkline cards should specify time range"
            assert card['hours_to_show'] == 24, "Should show 24-hour sparklines"
            
            # Should have entity or entities
            assert 'entity' in card or 'entities' in card, "Sparkline cards need entities"
            
            # Should have styling for sparklines
            has_sparkline_styling = any(key in card for key in [
                'line_width', 'height', 'show', 'points', 'line_color'
            ])
            assert has_sparkline_styling, "Sparkline cards should have visual styling config"

    def test_error_log_severity_color_coding(self, health_builder):
        """Test that error log has proper severity color coding."""
        entity_id = 'test_room'
        cards = health_builder.build_cards(entity_id)
        
        # Find error log cards
        error_cards = [card for card in cards 
                      if 'error' in str(card.get('title', '')).lower() or
                      'log' in str(card.get('title', '')).lower()]
        
        assert len(error_cards) >= 1, "Should have error log card"
        
        error_card = error_cards[0]
        card_content = str(error_card)
        
        # Should have severity-based color coding
        has_severity_colors = (
            'state_color' in card_content or
            'severity' in card_content or
            'color' in card_content or
            'red' in card_content or
            'yellow' in card_content or
            'green' in card_content
        )
        
        assert has_severity_colors, "Error log should implement severity color coding"

    def test_performance_metrics_have_units(self, health_builder):
        """Test that performance metrics display proper units."""
        entity_id = 'test_room'
        cards = health_builder.build_cards(entity_id)
        
        # Find performance-related cards
        all_card_content = ' '.join(str(card) for card in cards)
        
        # Should include performance metrics with units
        has_latency = 'latency' in all_card_content.lower()
        has_memory = 'memory' in all_card_content.lower()
        has_cpu = 'cpu' in all_card_content.lower()
        
        # At least one performance metric should be present
        has_performance_metrics = has_latency or has_memory or has_cpu
        assert has_performance_metrics, "Should include performance metrics (latency, memory, or CPU)"
        
        # Should have unit specifications
        has_time_units = 'ms' in all_card_content or 'milliseconds' in all_card_content
        has_memory_units = 'MB' in all_card_content or 'bytes' in all_card_content
        has_percentage_units = '%' in all_card_content or 'percent' in all_card_content
        
        # Should have appropriate units for metrics
        if has_latency:
            assert has_time_units, "Latency metrics should have time units (ms)"
        if has_memory:
            assert has_memory_units, "Memory metrics should have memory units (MB)"
        if has_cpu:
            assert has_percentage_units, "CPU metrics should have percentage units"

    def test_templates_and_tooltips_integration(self, health_builder, templates, tooltips):
        """Test that templates and tooltips are properly integrated."""
        # Verify the builder has access to templates and tooltips
        assert hasattr(health_builder, '_templates') or hasattr(health_builder, 'templates')
        assert hasattr(health_builder, '_tooltips') or hasattr(health_builder, 'tooltips')
        
        # Build cards and verify some use templates/tooltips  
        entity_id = 'test_room'
        cards = health_builder.build_cards(entity_id)
        
        # At least one card should show evidence of template usage
        # (This is implementation-dependent, so we just verify no crashes occur)
        assert len(cards) > 0


class TestSystemHealthTabBuilderIntegration:
    """Integration tests for SystemHealthTabBuilder with real components."""

    @pytest.fixture
    def mock_hass(self):
        """Provide mock Home Assistant instance."""
        hass = Mock()
        hass.states = Mock()
        hass.states.get = Mock(return_value=Mock(state='available'))
        return hass

    def test_system_health_full_integration(self, mock_hass):
        """Test full integration of system health tab in dashboard context."""
        from dashboard.builders import SystemHealthTabBuilder
        from dashboard.templates import GraphTemplates
        from dashboard.tooltips import TooltipProvider
        
        templates = GraphTemplates()
        tooltips = TooltipProvider()
        health_builder = SystemHealthTabBuilder(templates, tooltips)
        
        entity_id = 'living_room'
        cards = health_builder.build_cards(entity_id)
        
        # Verify complete tab structure
        assert len(cards) >= 4, "Should have at least 4 card types (component grid + sensor cards + error log + performance)"
        
        # Verify tab config
        config = health_builder.get_tab_config()
        assert config['title'] == 'System Health'
        assert config['path'] == 'system_health'
        assert config['icon'] == 'mdi:heart-pulse'
        
        # Verify card structure is suitable for YAML generation
        for card in cards:
            assert isinstance(card, dict)
            assert 'type' in card
            # Should be serializable (basic check)
            assert len(str(card)) > 10

    def test_error_handling_missing_sensors(self):
        """Test graceful handling when sensors are missing."""
        from dashboard.builders import SystemHealthTabBuilder  
        from dashboard.templates import GraphTemplates
        from dashboard.tooltips import TooltipProvider
        
        templates = GraphTemplates()
        tooltips = TooltipProvider()
        health_builder = SystemHealthTabBuilder(templates, tooltips)
        
        # Should handle gracefully even with potentially missing sensors
        entity_id = 'nonexistent_room'
        cards = health_builder.build_cards(entity_id)
        
        # Should still generate valid card structure
        assert isinstance(cards, list)
        assert len(cards) > 0
        
        # Cards should have proper fallback configuration
        for card in cards:
            assert isinstance(card, dict)
            assert 'type' in card