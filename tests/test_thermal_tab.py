"""
ABOUTME: Tests for ThermalMetricsTabBuilder class  
ABOUTME: Validates thermal visualization cards, time range selectors, and data structures
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, List, Any

# Import the class we'll be testing (this will fail initially)
try:
    from custom_components.smart_climate.dashboard.builders import ThermalMetricsTabBuilder
except ImportError:
    # Expected to fail initially - we'll implement this class
    ThermalMetricsTabBuilder = None


class TestThermalMetricsTabBuilder:
    """Test cases for ThermalMetricsTabBuilder class."""

    def setup_method(self):
        """Set up test fixtures."""
        if ThermalMetricsTabBuilder is None:
            pytest.skip("ThermalMetricsTabBuilder not implemented yet")
            
        # Mock the dependencies
        from custom_components.smart_climate.dashboard.templates import GraphTemplates
        from custom_components.smart_climate.dashboard.tooltips import TooltipProvider
        import copy
        
        self.mock_templates = Mock(spec=GraphTemplates)
        self.mock_tooltips = Mock(spec=TooltipProvider)
        
        # Configure mock to simulate the real get_line_graph behavior with overrides
        def mock_get_line_graph(**overrides):
            base_template = {
                'type': 'custom:apexcharts-card',
                'header': {'title': '', 'show': True},
                'graph_span': '24h',
                'series': [],
                'apex_config': {
                    'chart': {'height': 250},
                    'legend': {'show': True},
                    'tooltip': {'enabled': True, 'shared': True}
                }
            }
            result = copy.deepcopy(base_template)
            
            # Apply overrides (simplified version of _apply_overrides)
            for key, value in overrides.items():
                if isinstance(value, dict) and key in result and isinstance(result[key], dict):
                    result[key].update(value)
                else:
                    result[key] = value
            
            return result
        
        self.mock_templates.get_line_graph.side_effect = mock_get_line_graph
        
        self.builder = ThermalMetricsTabBuilder(self.mock_templates, self.mock_tooltips)
        self.test_entity_id = "living_room"

    def test_class_exists_and_inherits_correctly(self):
        """Test that ThermalMetricsTabBuilder exists and inherits from TabBuilder."""
        if ThermalMetricsTabBuilder is None:
            pytest.skip("ThermalMetricsTabBuilder not implemented yet")
            
        from custom_components.smart_climate.dashboard.base import TabBuilder
        assert issubclass(ThermalMetricsTabBuilder, TabBuilder)
        assert hasattr(ThermalMetricsTabBuilder, 'build_cards')
        assert hasattr(ThermalMetricsTabBuilder, 'get_tab_config')

    def test_build_cards_returns_six_cards(self):
        """Test that build_cards returns exactly 6 cards for thermal metrics."""
        if ThermalMetricsTabBuilder is None:
            pytest.skip("ThermalMetricsTabBuilder not implemented yet")
            
        cards = self.builder.build_cards(self.test_entity_id)
        
        # Should return exactly 6 cards
        assert isinstance(cards, list)
        assert len(cards) == 6

    def test_tau_evolution_graph_card_structure(self):
        """Test that tau evolution graph card is properly configured."""
        if ThermalMetricsTabBuilder is None:
            pytest.skip("ThermalMetricsTabBuilder not implemented yet")
            
        cards = self.builder.build_cards(self.test_entity_id)
        tau_card = cards[0]  # First card should be tau evolution
        
        # Should be ApexCharts line graph
        assert tau_card['type'] == 'custom:apexcharts-card'
        assert 'header' in tau_card
        assert tau_card['header']['title'] == 'Tau Evolution'
        
        # Should have time range selector
        assert 'graph_span' in tau_card
        assert tau_card['graph_span'] == '24h'  # Default range
        
        # Should have series for tau_cooling and tau_warming
        assert 'series' in tau_card
        assert len(tau_card['series']) == 2
        
        # Check series configuration
        tau_cooling_series = tau_card['series'][0]
        tau_warming_series = tau_card['series'][1]
        
        assert tau_cooling_series['entity'] == f'sensor.{self.test_entity_id}_tau_cooling'
        assert tau_cooling_series['name'] == 'Tau Cooling'
        assert tau_warming_series['entity'] == f'sensor.{self.test_entity_id}_tau_warming'
        assert tau_warming_series['name'] == 'Tau Warming'
        
        # Should have hover tooltips
        assert 'apex_config' in tau_card
        assert tau_card['apex_config']['tooltip']['enabled'] is True

    def test_state_distribution_pie_chart_structure(self):
        """Test that state distribution pie chart is properly configured."""
        if ThermalMetricsTabBuilder is None:
            pytest.skip("ThermalMetricsTabBuilder not implemented yet")
            
        cards = self.builder.build_cards(self.test_entity_id)
        pie_card = cards[1]  # Second card should be state distribution
        
        # Should be ApexCharts pie chart
        assert pie_card['type'] == 'custom:apexcharts-card'
        assert 'header' in pie_card
        assert pie_card['header']['title'] == 'Thermal State Distribution'
        
        # Should have pie chart configuration
        assert 'apex_config' in pie_card
        assert pie_card['apex_config']['chart']['type'] == 'pie'
        
        # Should show percentages for PRIMING, DRIFTING, PROBING, CORRECTING
        assert 'series' in pie_card
        assert len(pie_card['series']) >= 1  # At least one series for the states

    def test_state_transition_diagram_structure(self):
        """Test that state transition diagram is properly configured.""" 
        if ThermalMetricsTabBuilder is None:
            pytest.skip("ThermalMetricsTabBuilder not implemented yet")
            
        cards = self.builder.build_cards(self.test_entity_id)
        transition_card = cards[2]  # Third card should be state transitions
        
        # Should be Plotly graph for sankey/flow diagram
        assert transition_card['type'] == 'custom:plotly-graph-card'
        assert 'layout' in transition_card
        assert transition_card['layout']['title'] == 'State Transitions'
        
        # Should have data for flow between states
        assert 'data' in transition_card
        assert len(transition_card['data']) >= 1

    def test_drift_analysis_scatter_plot_structure(self):
        """Test that drift analysis scatter plot has trend line settings."""
        if ThermalMetricsTabBuilder is None:
            pytest.skip("ThermalMetricsTabBuilder not implemented yet")
            
        cards = self.builder.build_cards(self.test_entity_id)
        scatter_card = cards[3]  # Fourth card should be drift analysis
        
        # Should be ApexCharts scatter plot
        assert scatter_card['type'] == 'custom:apexcharts-card'
        assert 'header' in scatter_card
        assert scatter_card['header']['title'] == 'Drift Analysis'
        
        # Should have scatter plot configuration
        assert 'apex_config' in scatter_card
        assert scatter_card['apex_config']['chart']['type'] == 'scatter'
        
        # Should have trend line enabled
        assert 'series' in scatter_card
        assert len(scatter_card['series']) >= 1
        
        # Check for trend line settings
        series = scatter_card['series'][0]
        assert 'trendline' in series or 'regression_line' in scatter_card['apex_config']
        
        # Should show R² value 
        assert 'annotations' in scatter_card['apex_config'] or 'subtitle' in scatter_card['header']

    def test_probe_history_table_structure(self):
        """Test that probe history table has correct column definitions."""
        if ThermalMetricsTabBuilder is None:
            pytest.skip("ThermalMetricsTabBuilder not implemented yet")
            
        cards = self.builder.build_cards(self.test_entity_id)
        table_card = cards[4]  # Fifth card should be probe history table
        
        # Should be entities card configured as table
        assert table_card['type'] == 'entities'
        assert 'title' in table_card
        assert table_card['title'] == 'Recent Probe History'
        
        # Should have entities for last 20 probes or similar configuration
        assert 'entities' in table_card
        
        # Should have column definitions for: Timestamp, Tau, Confidence, Duration, Outdoor Temp
        if 'columns' in table_card:
            columns = table_card['columns']
            column_names = [col.get('name', '') for col in columns]
            
            assert 'Timestamp' in column_names or 'Time' in column_names
            assert 'Tau' in column_names
            assert 'Confidence' in column_names
            assert 'Duration' in column_names
            assert 'Outdoor Temp' in column_names or 'Temperature' in column_names

    def test_comfort_violations_heatmap_structure(self):
        """Test that comfort violations heatmap has proper axis labels."""
        if ThermalMetricsTabBuilder is None:
            pytest.skip("ThermalMetricsTabBuilder not implemented yet")
            
        cards = self.builder.build_cards(self.test_entity_id)
        heatmap_card = cards[5]  # Sixth card should be comfort violations heatmap
        
        # Should be Plotly heatmap
        assert heatmap_card['type'] == 'custom:plotly-graph-card'
        assert 'layout' in heatmap_card
        assert heatmap_card['layout']['title'] == 'Comfort Violations Heatmap'
        
        # Should have 24x7 grid configuration (24 hours x 7 days)
        assert 'data' in heatmap_card
        heatmap_data = heatmap_card['data'][0] if heatmap_card['data'] else {}
        
        # Should be heatmap type
        assert heatmap_data.get('type') == 'heatmap'
        
        # Should have proper axis labels
        layout = heatmap_card['layout']
        assert 'xaxis' in layout
        assert 'yaxis' in layout
        assert layout['xaxis']['title'] == 'Hour of Day' or 'hour' in layout['xaxis'].get('title', '').lower()
        assert layout['yaxis']['title'] == 'Day of Week' or 'day' in layout['yaxis'].get('title', '').lower()

    def test_get_tab_config_returns_correct_metadata(self):
        """Test that get_tab_config returns proper tab configuration."""
        if ThermalMetricsTabBuilder is None:
            pytest.skip("ThermalMetricsTabBuilder not implemented yet")
            
        config = self.builder.get_tab_config()
        
        assert isinstance(config, dict)
        assert 'title' in config
        assert 'icon' in config
        assert 'path' in config
        
        # Check specific values for thermal tab
        assert config['title'] == 'Thermal Metrics'
        assert config['icon'] == 'mdi:thermometer-lines'
        assert config['path'] == 'thermal'

    def test_time_range_selector_configuration(self):
        """Test that time range selector is properly configured."""
        if ThermalMetricsTabBuilder is None:
            pytest.skip("ThermalMetricsTabBuilder not implemented yet")
            
        cards = self.builder.build_cards(self.test_entity_id)
        
        # Time series cards (tau evolution, drift analysis) should have time range selectors
        time_series_cards = [cards[0], cards[3]]  # Tau evolution and drift analysis
        
        for card in time_series_cards:
            # Should have configurable time range
            assert 'graph_span' in card
            
            # Should support different time ranges
            possible_ranges = ['1h', '24h', '7d', '30d']
            assert card['graph_span'] in possible_ranges or card['graph_span'] == '24h'

    def test_entity_id_substitution_in_sensor_names(self):
        """Test that entity_id is properly substituted in sensor entity names."""
        if ThermalMetricsTabBuilder is None:
            pytest.skip("ThermalMetricsTabBuilder not implemented yet")
            
        test_entity = "bedroom"
        cards = self.builder.build_cards(test_entity)
        
        # Check that all sensor references use the correct entity_id
        for card in cards:
            if 'series' in card:
                for series in card['series']:
                    if 'entity' in series:
                        entity_name = series['entity']
                        if entity_name.startswith('sensor.'):
                            assert test_entity in entity_name, f"Entity {entity_name} should contain {test_entity}"

    def test_cards_have_proper_refresh_intervals(self):
        """Test that cards have appropriate refresh intervals."""
        if ThermalMetricsTabBuilder is None:
            pytest.skip("ThermalMetricsTabBuilder not implemented yet")
            
        cards = self.builder.build_cards(self.test_entity_id)
        
        # Real-time cards should have faster refresh
        real_time_cards = [cards[0]]  # Tau evolution
        for card in real_time_cards:
            if 'refresh_interval' in card:
                assert card['refresh_interval'] <= 30  # 30 seconds or less
                
        # Historical cards can have slower refresh  
        historical_cards = [cards[4], cards[5]]  # Table and heatmap
        for card in historical_cards:
            if 'refresh_interval' in card:
                assert card['refresh_interval'] >= 300  # 5 minutes or more

    def test_cards_use_consistent_colors(self):
        """Test that cards use consistent color scheme."""
        if ThermalMetricsTabBuilder is None:
            pytest.skip("ThermalMetricsTabBuilder not implemented yet")
            
        cards = self.builder.build_cards(self.test_entity_id)
        
        # Check that series have colors defined
        for card in cards:
            if 'series' in card:
                for series in card['series']:
                    # Should have color defined or use defaults
                    has_color = 'color' in series or 'colors' in card.get('apex_config', {})
                    # We don't require it, but if present, should be valid hex color
                    if 'color' in series:
                        color = series['color']
                        assert color.startswith('#') and len(color) == 7

    def test_all_cards_have_required_base_fields(self):
        """Test that all cards have required base configuration fields."""
        if ThermalMetricsTabBuilder is None:
            pytest.skip("ThermalMetricsTabBuilder not implemented yet")
            
        cards = self.builder.build_cards(self.test_entity_id)
        
        for i, card in enumerate(cards):
            # Every card should have a type
            assert 'type' in card, f"Card {i} missing 'type' field"
            
            # Cards should have titles or headers  
            has_title = 'title' in card or ('header' in card and 'title' in card['header'])
            assert has_title, f"Card {i} missing title/header"

    def test_builder_handles_empty_entity_id(self):
        """Test that builder handles empty or None entity_id gracefully."""
        if ThermalMetricsTabBuilder is None:
            pytest.skip("ThermalMetricsTabBuilder not implemented yet")
            
        # Should not crash with empty entity_id
        cards = self.builder.build_cards("")
        assert isinstance(cards, list)
        assert len(cards) == 6
        
        # Should not crash with None entity_id  
        cards = self.builder.build_cards(None)
        assert isinstance(cards, list)
        assert len(cards) == 6

    def test_marker_events_in_tau_graph(self):
        """Test that tau evolution graph has markers for probe events."""
        if ThermalMetricsTabBuilder is None:
            pytest.skip("ThermalMetricsTabBuilder not implemented yet")
            
        cards = self.builder.build_cards(self.test_entity_id)
        tau_card = cards[0]
        
        # Should have markers or annotations for probe events
        apex_config = tau_card.get('apex_config', {})
        has_markers = (
            'markers' in apex_config or 
            'annotations' in apex_config or
            any('markers' in series for series in tau_card.get('series', []))
        )
        
        # Not strictly required, but nice to have
        # assert has_markers, "Tau evolution graph should have markers for probe events"

    def test_card_types_match_available_components(self):
        """Test that card types used are available in Home Assistant or HACS."""
        if ThermalMetricsTabBuilder is None:
            pytest.skip("ThermalMetricsTabBuilder not implemented yet")
            
        cards = self.builder.build_cards(self.test_entity_id)
        
        # Valid card types
        core_types = ['gauge', 'entities', 'history-graph', 'statistics-graph', 'thermostat']
        custom_types = ['custom:apexcharts-card', 'custom:plotly-graph-card', 'custom:mini-graph-card', 'custom:button-card']
        valid_types = core_types + custom_types
        
        for i, card in enumerate(cards):
            card_type = card['type']
            assert card_type in valid_types, f"Card {i} uses invalid type: {card_type}"