"""Test Graph Templates for Advanced Analytics Dashboard.

ABOUTME: Comprehensive tests for GraphTemplates class ensuring predefined graph configurations
work correctly with overrides and produce valid YAML structures.
"""

import pytest
import copy
from unittest.mock import patch

# Import the class we're testing
from custom_components.smart_climate.dashboard.templates import GraphTemplates


class TestGraphTemplates:
    """Test cases for GraphTemplates class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.templates = GraphTemplates()

    def test_class_constants_exist(self):
        """Test that all required class constants are defined."""
        # Test LINE_GRAPH constant exists and has required fields
        assert hasattr(GraphTemplates, 'LINE_GRAPH')
        assert isinstance(GraphTemplates.LINE_GRAPH, dict)
        assert 'type' in GraphTemplates.LINE_GRAPH
        assert 'graph_span' in GraphTemplates.LINE_GRAPH
        assert 'header' in GraphTemplates.LINE_GRAPH
        assert 'series' in GraphTemplates.LINE_GRAPH
        assert 'apex_config' in GraphTemplates.LINE_GRAPH
        
        # Test HEATMAP constant exists and has required fields
        assert hasattr(GraphTemplates, 'HEATMAP')
        assert isinstance(GraphTemplates.HEATMAP, dict)
        assert 'type' in GraphTemplates.HEATMAP
        assert 'hours_to_show' in GraphTemplates.HEATMAP
        assert 'refresh_interval' in GraphTemplates.HEATMAP
        assert 'layout' in GraphTemplates.HEATMAP
        
        # Test GAUGE constant exists and has required fields
        assert hasattr(GraphTemplates, 'GAUGE')
        assert isinstance(GraphTemplates.GAUGE, dict)
        assert 'type' in GraphTemplates.GAUGE
        assert 'min' in GraphTemplates.GAUGE
        assert 'max' in GraphTemplates.GAUGE
        assert 'needle' in GraphTemplates.GAUGE
        assert 'severity' in GraphTemplates.GAUGE

    def test_line_graph_template_structure(self):
        """Test LINE_GRAPH template has correct structure and values."""
        template = GraphTemplates.LINE_GRAPH
        
        # Test top-level structure
        assert template['type'] == 'custom:apexcharts-card'
        assert template['graph_span'] == '24h'
        assert isinstance(template['header'], dict)
        assert isinstance(template['series'], list)
        assert isinstance(template['apex_config'], dict)
        
        # Test header structure
        header = template['header']
        assert header['show'] is True
        assert header['title'] == ''
        
        # Test apex_config structure
        apex = template['apex_config']
        assert 'chart' in apex
        assert 'legend' in apex
        assert 'tooltip' in apex
        assert apex['chart']['height'] == 250
        assert apex['legend']['show'] is True
        assert apex['tooltip']['enabled'] is True
        assert apex['tooltip']['shared'] is True

    def test_heatmap_template_structure(self):
        """Test HEATMAP template has correct structure and values."""
        template = GraphTemplates.HEATMAP
        
        # Test top-level structure
        assert template['type'] == 'custom:plotly-graph-card'
        assert template['hours_to_show'] == 168
        assert template['refresh_interval'] == 300
        assert isinstance(template['layout'], dict)
        
        # Test layout structure
        layout = template['layout']
        assert layout['height'] == 300
        assert layout['showlegend'] is True
        assert layout['hovermode'] == 'closest'

    def test_gauge_template_structure(self):
        """Test GAUGE template has correct structure and values."""
        template = GraphTemplates.GAUGE
        
        # Test top-level structure
        assert template['type'] == 'gauge'
        assert template['min'] == 0
        assert template['max'] == 100
        assert template['needle'] is True
        assert isinstance(template['severity'], dict)
        
        # Test severity structure
        severity = template['severity']
        assert severity['green'] == 80
        assert severity['yellow'] == 50
        assert severity['red'] == 0

    def test_get_line_graph_returns_deep_copy(self):
        """Test that get_line_graph returns a deep copy, not reference."""
        result1 = self.templates.get_line_graph()
        result2 = self.templates.get_line_graph()
        
        # Should be equal in content
        assert result1 == result2
        
        # But should be different objects
        assert result1 is not result2
        assert result1['header'] is not result2['header']
        assert result1['apex_config'] is not result2['apex_config']
        
        # Modifying one should not affect the other
        result1['header']['title'] = 'Modified'
        assert result2['header']['title'] == ''

    def test_get_heatmap_returns_deep_copy(self):
        """Test that get_heatmap returns a deep copy, not reference."""
        result1 = self.templates.get_heatmap()
        result2 = self.templates.get_heatmap()
        
        # Should be equal in content
        assert result1 == result2
        
        # But should be different objects
        assert result1 is not result2
        assert result1['layout'] is not result2['layout']
        
        # Modifying one should not affect the other
        result1['layout']['height'] = 500
        assert result2['layout']['height'] == 300

    def test_get_gauge_returns_deep_copy(self):
        """Test that get_gauge returns a deep copy, not reference."""
        result1 = self.templates.get_gauge()
        result2 = self.templates.get_gauge()
        
        # Should be equal in content
        assert result1 == result2
        
        # But should be different objects
        assert result1 is not result2
        assert result1['severity'] is not result2['severity']
        
        # Modifying one should not affect the other
        result1['severity']['green'] = 90
        assert result2['severity']['green'] == 80

    def test_get_line_graph_with_simple_overrides(self):
        """Test get_line_graph with simple override values."""
        overrides = {
            'graph_span': '48h',
            'type': 'custom:mini-graph-card'
        }
        
        result = self.templates.get_line_graph(**overrides)
        
        # Overridden values should be applied
        assert result['graph_span'] == '48h'
        assert result['type'] == 'custom:mini-graph-card'
        
        # Non-overridden values should remain the same
        assert result['header']['show'] is True
        assert result['apex_config']['chart']['height'] == 250

    def test_get_line_graph_with_nested_overrides(self):
        """Test get_line_graph with nested override values."""
        overrides = {
            'header': {'title': 'Temperature Trends', 'show': False},
            'apex_config': {'chart': {'height': 400}}
        }
        
        result = self.templates.get_line_graph(**overrides)
        
        # Nested overrides should be applied
        assert result['header']['title'] == 'Temperature Trends'
        assert result['header']['show'] is False
        assert result['apex_config']['chart']['height'] == 400
        
        # Other nested values should remain
        assert result['apex_config']['legend']['show'] is True
        assert result['apex_config']['tooltip']['enabled'] is True

    def test_get_heatmap_with_overrides(self):
        """Test get_heatmap with override values."""
        overrides = {
            'hours_to_show': 72,
            'layout': {'height': 400, 'title': 'Thermal Heatmap'}
        }
        
        result = self.templates.get_heatmap(**overrides)
        
        # Overridden values should be applied
        assert result['hours_to_show'] == 72
        assert result['layout']['height'] == 400
        assert result['layout']['title'] == 'Thermal Heatmap'
        
        # Non-overridden values should remain
        assert result['layout']['showlegend'] is True
        assert result['layout']['hovermode'] == 'closest'

    def test_get_gauge_with_overrides(self):
        """Test get_gauge with override values."""
        overrides = {
            'min': -10,
            'max': 50,
            'severity': {'green': 40, 'yellow': 20, 'red': -10}
        }
        
        result = self.templates.get_gauge(**overrides)
        
        # Overridden values should be applied
        assert result['min'] == -10
        assert result['max'] == 50
        assert result['severity']['green'] == 40
        assert result['severity']['yellow'] == 20
        assert result['severity']['red'] == -10
        
        # Non-overridden values should remain
        assert result['needle'] is True

    def test_templates_produce_valid_yaml_structure(self):
        """Test that templates produce valid YAML-serializable structures."""
        import yaml
        
        # Test LINE_GRAPH can be serialized to YAML
        line_result = self.templates.get_line_graph()
        yaml_str = yaml.dump(line_result)
        yaml_parsed = yaml.safe_load(yaml_str)
        assert yaml_parsed == line_result
        
        # Test HEATMAP can be serialized to YAML
        heatmap_result = self.templates.get_heatmap()
        yaml_str = yaml.dump(heatmap_result)
        yaml_parsed = yaml.safe_load(yaml_str)
        assert yaml_parsed == heatmap_result
        
        # Test GAUGE can be serialized to YAML
        gauge_result = self.templates.get_gauge()
        yaml_str = yaml.dump(gauge_result)
        yaml_parsed = yaml.safe_load(yaml_str)
        assert yaml_parsed == gauge_result

    def test_card_types_are_correctly_specified(self):
        """Test that card types match expected values for HA/HACS."""
        # LINE_GRAPH should use ApexCharts (custom card)
        line_graph = self.templates.get_line_graph()
        assert line_graph['type'] == 'custom:apexcharts-card'
        
        # HEATMAP should use Plotly (custom card)
        heatmap = self.templates.get_heatmap()
        assert heatmap['type'] == 'custom:plotly-graph-card'
        
        # GAUGE should use core HA gauge
        gauge = self.templates.get_gauge()
        assert gauge['type'] == 'gauge'

    def test_override_with_none_values(self):
        """Test that None override values are handled gracefully."""
        overrides = {
            'graph_span': None,
            'header': None
        }
        
        result = self.templates.get_line_graph(**overrides)
        
        # None values should override original values
        assert result['graph_span'] is None
        assert result['header'] is None
        
        # Other values should remain unchanged
        assert result['type'] == 'custom:apexcharts-card'

    def test_override_with_empty_dict(self):
        """Test that empty dict overrides work correctly."""
        overrides = {}
        
        result = self.templates.get_line_graph(**overrides)
        
        # Should return unmodified template
        assert result == GraphTemplates.LINE_GRAPH

    def test_series_field_modification(self):
        """Test that series field can be properly modified."""
        overrides = {
            'series': [
                {'entity': 'sensor.temperature', 'name': 'Indoor Temp'},
                {'entity': 'sensor.outdoor_temp', 'name': 'Outdoor Temp'}
            ]
        }
        
        result = self.templates.get_line_graph(**overrides)
        
        # Series should be overridden
        assert len(result['series']) == 2
        assert result['series'][0]['entity'] == 'sensor.temperature'
        assert result['series'][1]['name'] == 'Outdoor Temp'
        
        # Original template should still have empty series
        assert GraphTemplates.LINE_GRAPH['series'] == []

    def test_deep_merge_behavior(self):
        """Test that overrides perform deep merge, not replacement."""
        overrides = {
            'apex_config': {
                'chart': {'type': 'area'}  # Only override chart type
            }
        }
        
        result = self.templates.get_line_graph(**overrides)
        
        # New chart type should be applied
        assert result['apex_config']['chart']['type'] == 'area'
        
        # Original chart height should be preserved
        assert result['apex_config']['chart']['height'] == 250
        
        # Other apex_config sections should be preserved
        assert result['apex_config']['legend']['show'] is True
        assert result['apex_config']['tooltip']['enabled'] is True

    def test_all_getter_methods_exist(self):
        """Test that all required getter methods are implemented."""
        # Check methods exist
        assert hasattr(self.templates, 'get_line_graph')
        assert hasattr(self.templates, 'get_heatmap')
        assert hasattr(self.templates, 'get_gauge')
        
        # Check methods are callable
        assert callable(getattr(self.templates, 'get_line_graph'))
        assert callable(getattr(self.templates, 'get_heatmap'))
        assert callable(getattr(self.templates, 'get_gauge'))

    def test_method_return_types(self):
        """Test that getter methods return correct types."""
        # All should return dictionaries
        assert isinstance(self.templates.get_line_graph(), dict)
        assert isinstance(self.templates.get_heatmap(), dict)
        assert isinstance(self.templates.get_gauge(), dict)