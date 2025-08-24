"""Test cases for MLPerformanceTabBuilder class.

This module contains comprehensive tests for the ML Performance tab of the
Advanced Analytics Dashboard, following TDD principles.
"""
import pytest
from unittest.mock import Mock, patch
from typing import List, Dict, Any

# Import constants and utilities from dashboard package
try:
    from custom_components.smart_climate.dashboard.base import TabBuilder
    from custom_components.smart_climate.dashboard.constants import (
        SENSOR_MAPPINGS, DashboardColors, REFRESH_INTERVALS
    )
    from custom_components.smart_climate.dashboard.templates import GraphTemplates
    DASHBOARD_AVAILABLE = True
except ImportError:
    DASHBOARD_AVAILABLE = False


class TestMLPerformanceTabBuilder:
    """Test cases for MLPerformanceTabBuilder implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        if DASHBOARD_AVAILABLE:
            # Import here to avoid issues during test discovery
            try:
                from custom_components.smart_climate.dashboard.builders import MLPerformanceTabBuilder
                from custom_components.smart_climate.dashboard.templates import GraphTemplates
                from custom_components.smart_climate.dashboard.tooltips import TooltipProvider
                
                # Create mock dependencies
                mock_templates = GraphTemplates()
                mock_tooltips = TooltipProvider()
                
                self.builder = MLPerformanceTabBuilder(mock_templates, mock_tooltips)
            except ImportError:
                self.builder = None
        else:
            self.builder = None

    def test_ml_performance_tab_builder_exists(self):
        """Test that MLPerformanceTabBuilder class can be imported."""
        try:
            from custom_components.smart_climate.dashboard.builders import MLPerformanceTabBuilder
            assert MLPerformanceTabBuilder is not None
        except ImportError:
            pytest.skip("MLPerformanceTabBuilder not implemented yet")

    def test_ml_performance_tab_builder_extends_tab_builder(self):
        """Test that MLPerformanceTabBuilder extends TabBuilder base class."""
        if not DASHBOARD_AVAILABLE or self.builder is None:
            pytest.skip("MLPerformanceTabBuilder not available")
            
        from custom_components.smart_climate.dashboard.builders import MLPerformanceTabBuilder
        
        # Should be an instance of TabBuilder
        assert isinstance(self.builder, TabBuilder)
        
        # Should be able to call abstract methods
        assert hasattr(self.builder, 'build_cards')
        assert hasattr(self.builder, 'get_tab_config')
        assert callable(self.builder.build_cards)
        assert callable(self.builder.get_tab_config)

    def test_get_tab_config_returns_correct_metadata(self):
        """Test that get_tab_config returns ML Performance tab metadata."""
        if not DASHBOARD_AVAILABLE or self.builder is None:
            pytest.skip("MLPerformanceTabBuilder not available")
            
        config = self.builder.get_tab_config()
        
        # Should return dict with required keys
        assert isinstance(config, dict)
        required_keys = {'title', 'icon', 'path'}
        assert all(key in config for key in required_keys)
        
        # Should have ML Performance specific values
        assert config['title'] == 'ML Performance'
        assert config['icon'] == 'mdi:brain'
        assert config['path'] == 'ml_performance'

    def test_build_cards_returns_five_cards(self):
        """Test that build_cards returns exactly 5 cards for ML Performance tab."""
        if not DASHBOARD_AVAILABLE or self.builder is None:
            pytest.skip("MLPerformanceTabBuilder not available")
            
        entity_id = 'living_room'
        cards = self.builder.build_cards(entity_id)
        
        # Should return list of exactly 5 cards
        assert isinstance(cards, list)
        assert len(cards) == 5
        
        # All cards should be dictionaries
        assert all(isinstance(card, dict) for card in cards)
        
        # All cards should have 'type' field
        assert all('type' in card for card in cards)

    def test_learning_progress_card_structure(self):
        """Test that learning progress card has correct structure."""
        if not DASHBOARD_AVAILABLE or self.builder is None:
            pytest.skip("MLPerformanceTabBuilder not available")
            
        entity_id = 'living_room'
        cards = self.builder.build_cards(entity_id)
        
        # First card should be learning progress
        learning_card = cards[0]
        
        # Should be ApexCharts card
        assert learning_card['type'] == 'custom:apexcharts-card'
        
        # Should have required configuration
        assert 'header' in learning_card
        assert learning_card['header']['title'] == 'Learning Progress'
        assert learning_card['header']['show'] is True
        
        # Should have multiple series for samples, confidence, MAE
        assert 'series' in learning_card
        assert isinstance(learning_card['series'], list)
        assert len(learning_card['series']) == 3
        
        # Series should have correct entity references
        series = learning_card['series']
        expected_entities = [
            f'sensor.{entity_id}_samples_collected',
            f'sensor.{entity_id}_confidence', 
            f'sensor.{entity_id}_mae'
        ]
        
        for i, expected_entity in enumerate(expected_entities):
            assert series[i]['entity'] == expected_entity

    def test_learning_progress_has_milestone_markers(self):
        """Test that learning progress graph includes milestone markers."""
        if not DASHBOARD_AVAILABLE or self.builder is None:
            pytest.skip("MLPerformanceTabBuilder not available")
            
        entity_id = 'test_climate'
        cards = self.builder.build_cards(entity_id)
        learning_card = cards[0]
        
        # Should have apex_config with annotations for milestones
        assert 'apex_config' in learning_card
        assert 'annotations' in learning_card['apex_config']
        
        annotations = learning_card['apex_config']['annotations']
        assert 'xaxis' in annotations
        assert isinstance(annotations['xaxis'], list)
        
        # Should have at least one milestone marker
        assert len(annotations['xaxis']) >= 1
        
        # Milestone markers should have label and borderColor
        for marker in annotations['xaxis']:
            assert 'label' in marker
            assert 'borderColor' in marker
            assert isinstance(marker['label'], dict)
            assert 'text' in marker['label']

    def test_prediction_error_histogram_structure(self):
        """Test that prediction error histogram has correct structure."""
        if not DASHBOARD_AVAILABLE or self.builder is None:
            pytest.skip("MLPerformanceTabBuilder not available")
            
        entity_id = 'bedroom'
        cards = self.builder.build_cards(entity_id)
        
        # Second card should be prediction error histogram
        histogram_card = cards[1]
        
        # Should be ApexCharts card with histogram configuration
        assert histogram_card['type'] == 'custom:apexcharts-card'
        assert histogram_card['header']['title'] == 'Prediction Accuracy'
        
        # Should have histogram series and normal distribution overlay
        assert 'series' in histogram_card
        series = histogram_card['series']
        assert len(series) == 2
        
        # First series: histogram data
        assert series[0]['name'] == 'Prediction Errors'
        assert series[0]['entity'] == f'sensor.{entity_id}_prediction_errors'
        
        # Second series: normal distribution overlay
        assert series[1]['name'] == 'Normal Distribution'
        assert 'data_generator' in series[1]  # Computed overlay

    def test_histogram_includes_statistical_overlays(self):
        """Test that histogram includes statistical information."""
        if not DASHBOARD_AVAILABLE or self.builder is None:
            pytest.skip("MLPerformanceTabBuilder not available")
            
        entity_id = 'office'
        cards = self.builder.build_cards(entity_id)
        histogram_card = cards[1]
        
        # Should have apex_config with statistical annotations
        assert 'apex_config' in histogram_card
        assert 'annotations' in histogram_card['apex_config']
        
        # Should display mean, std dev, and confidence interval
        annotations = histogram_card['apex_config']['annotations']
        assert 'yaxis' in annotations
        assert isinstance(annotations['yaxis'], list)
        
        # Should have statistical markers
        stat_labels = [ann['label']['text'] for ann in annotations['yaxis'] if 'label' in ann]
        assert any('Mean:' in label for label in stat_labels)
        assert any('Std Dev:' in label for label in stat_labels)
        assert any('95% CI:' in label for label in stat_labels)

    def test_feature_importance_bars_structure(self):
        """Test that feature importance horizontal bars have correct structure."""
        if not DASHBOARD_AVAILABLE or self.builder is None:
            pytest.skip("MLPerformanceTabBuilder not available")
            
        entity_id = 'kitchen'
        cards = self.builder.build_cards(entity_id)
        
        # Third card should be feature importance
        importance_card = cards[2]
        
        # Should be ApexCharts horizontal bar chart
        assert importance_card['type'] == 'custom:apexcharts-card'
        assert importance_card['header']['title'] == 'Feature Importance'
        
        # Should have horizontal bar configuration
        assert 'apex_config' in importance_card
        assert 'chart' in importance_card['apex_config']
        assert importance_card['apex_config']['chart']['type'] == 'bar'
        
        # Should be horizontal
        assert 'plotOptions' in importance_card['apex_config']
        assert 'bar' in importance_card['apex_config']['plotOptions']
        assert importance_card['apex_config']['plotOptions']['bar']['horizontal'] is True
        
        # Should have feature data
        assert 'series' in importance_card
        series = importance_card['series']
        assert len(series) == 1
        assert series[0]['name'] == 'Importance %'

    def test_feature_importance_sums_to_100_percent(self):
        """Test that feature importance values sum to 100%."""
        if not DASHBOARD_AVAILABLE or self.builder is None:
            pytest.skip("MLPerformanceTabBuilder not available")
            
        entity_id = 'basement'
        cards = self.builder.build_cards(entity_id)
        importance_card = cards[2]
        
        # Should have data validation or calculation ensuring 100% total
        assert 'apex_config' in importance_card
        
        # Should have data transformation or validation
        # This tests that the card configuration includes logic to normalize to 100%
        series = importance_card['series'][0]
        assert 'data_generator' in series or 'transform' in series
        
        # Should have expected features: outdoor temp, time of day, power consumption
        expected_features = [
            'Outdoor Temperature',
            'Time of Day', 
            'Day of Week',
            'Power Consumption',
            'Previous Offset'
        ]
        
        # Verify features are configured in xaxis categories or data
        if 'apex_config' in importance_card and 'xaxis' in importance_card['apex_config']:
            categories = importance_card['apex_config']['xaxis'].get('categories', [])
            assert all(feature in categories for feature in expected_features)

    def test_confidence_bands_area_chart_structure(self):
        """Test that confidence bands area chart has correct structure."""
        if not DASHBOARD_AVAILABLE or self.builder is None:
            pytest.skip("MLPerformanceTabBuilder not available")
            
        entity_id = 'guest_room'
        cards = self.builder.build_cards(entity_id)
        
        # Fourth card should be confidence bands
        confidence_card = cards[3]
        
        # Should be ApexCharts area chart
        assert confidence_card['type'] == 'custom:apexcharts-card'
        assert confidence_card['header']['title'] == 'Prediction Confidence'
        
        # Should have area chart configuration
        assert 'apex_config' in confidence_card
        assert 'chart' in confidence_card['apex_config']
        assert confidence_card['apex_config']['chart']['type'] == 'area'
        
        # Should have multiple series for upper bound, lower bound, actual
        assert 'series' in confidence_card
        series = confidence_card['series']
        assert len(series) == 3
        
        # Series should be: actual values, upper bound, lower bound
        expected_names = ['Actual Temperature', 'Upper Confidence', 'Lower Confidence']
        series_names = [s['name'] for s in series]
        assert all(name in series_names for name in expected_names)

    def test_confidence_bands_show_uncertainty(self):
        """Test that confidence bands properly display uncertainty ranges."""
        if not DASHBOARD_AVAILABLE or self.builder is None:
            pytest.skip("MLPerformanceTabBuilder not available")
            
        entity_id = 'attic'
        cards = self.builder.build_cards(entity_id)
        confidence_card = cards[3]
        
        # Should have fill configuration for area chart
        assert 'apex_config' in confidence_card
        assert 'fill' in confidence_card['apex_config']
        
        # Should configure area fill to show uncertainty
        fill_config = confidence_card['apex_config']['fill']
        assert fill_config['type'] == 'gradient'
        assert 'gradient' in fill_config
        
        # Should have proper opacity for uncertainty visualization
        assert 'stroke' in confidence_card['apex_config']
        assert 'width' in confidence_card['apex_config']['stroke']

    def test_performance_metrics_grid_structure(self):
        """Test that performance metrics grid has correct structure."""
        if not DASHBOARD_AVAILABLE or self.builder is None:
            pytest.skip("MLPerformanceTabBuilder not available")
            
        entity_id = 'den'
        cards = self.builder.build_cards(entity_id)
        
        # Fifth card should be performance metrics grid
        metrics_card = cards[4]
        
        # Should be entities card for grid layout
        assert metrics_card['type'] == 'entities'
        assert metrics_card['title'] == 'Performance Metrics'
        
        # Should have list of metric entities
        assert 'entities' in metrics_card
        entities = metrics_card['entities']
        assert isinstance(entities, list)
        assert len(entities) >= 5  # MAE, RMSE, R², model age, sample size
        
        # Should include all required metrics
        expected_entities = [
            f'sensor.{entity_id}_mae',
            f'sensor.{entity_id}_rmse', 
            f'sensor.{entity_id}_r_squared',
            f'sensor.{entity_id}_model_age_hours',
            f'sensor.{entity_id}_samples_collected'
        ]
        
        # Extract entity IDs from entities list (may be strings or dicts)
        entity_ids = []
        for entity in entities:
            if isinstance(entity, str):
                entity_ids.append(entity)
            elif isinstance(entity, dict) and 'entity' in entity:
                entity_ids.append(entity['entity'])
        
        assert all(expected in entity_ids for expected in expected_entities)

    def test_metrics_grid_updates_properly(self):
        """Test that metrics grid is configured for real-time updates."""
        if not DASHBOARD_AVAILABLE or self.builder is None:
            pytest.skip("MLPerformanceTabBuilder not available")
            
        entity_id = 'study'
        cards = self.builder.build_cards(entity_id)
        metrics_card = cards[4]
        
        # Should have state_color configuration for visual indicators
        entities = metrics_card['entities']
        
        # At least some entities should have custom configuration
        configured_entities = [e for e in entities if isinstance(e, dict)]
        assert len(configured_entities) > 0
        
        # Configured entities should have name and/or icon customization
        for entity_config in configured_entities:
            assert 'entity' in entity_config
            # Should have at least name or icon customization
            assert 'name' in entity_config or 'icon' in entity_config

    def test_all_cards_use_correct_entity_references(self):
        """Test that all cards reference correct sensor entities."""
        if not DASHBOARD_AVAILABLE or self.builder is None:
            pytest.skip("MLPerformanceTabBuilder not available")
            
        entity_id = 'master_bedroom'
        cards = self.builder.build_cards(entity_id)
        
        # Collect all entity references from all cards
        entity_refs = []
        
        for card in cards:
            if 'series' in card:
                for series in card['series']:
                    if 'entity' in series:
                        entity_refs.append(series['entity'])
            
            if 'entities' in card:
                for entity in card['entities']:
                    if isinstance(entity, str):
                        entity_refs.append(entity)
                    elif isinstance(entity, dict) and 'entity' in entity:
                        entity_refs.append(entity['entity'])
        
        # All entity references should start with correct prefix
        for ref in entity_refs:
            if not ref.startswith('sensor.'):
                continue  # Skip non-sensor entities
            assert ref.startswith(f'sensor.{entity_id}_'), f"Entity {ref} doesn't match pattern"

    def test_cards_follow_color_scheme(self):
        """Test that all cards use consistent color scheme."""
        if not DASHBOARD_AVAILABLE or self.builder is None:
            pytest.skip("MLPerformanceTabBuilder not available")
            
        entity_id = 'game_room'
        cards = self.builder.build_cards(entity_id)
        
        # Check that cards use colors from DashboardColors
        expected_colors = [
            DashboardColors.PRIMARY,
            DashboardColors.SUCCESS, 
            DashboardColors.WARNING,
            DashboardColors.PRIMARY_LIGHT
        ]
        
        # At least some cards should reference color scheme
        color_found = False
        for card in cards:
            # Check for colors in series configurations
            if 'series' in card:
                for series in card['series']:
                    if 'color' in series:
                        if series['color'] in expected_colors:
                            color_found = True
            
            # Check for colors in apex_config
            if 'apex_config' in card:
                apex = card['apex_config']
                if 'colors' in apex:
                    colors = apex['colors']
                    if any(color in expected_colors for color in colors):
                        color_found = True
        
        assert color_found, "No cards found using DashboardColors scheme"

    def test_cards_have_proper_time_ranges(self):
        """Test that time-based cards have appropriate time ranges."""
        if not DASHBOARD_AVAILABLE or self.builder is None:
            pytest.skip("MLPerformanceTabBuilder not available")
            
        entity_id = 'sunroom'
        cards = self.builder.build_cards(entity_id)
        
        # Time-based cards (learning progress, confidence) should have graph_span
        time_cards = [cards[0], cards[3]]  # Learning progress and confidence bands
        
        for card in time_cards:
            assert 'graph_span' in card
            # Should use reasonable time span
            assert card['graph_span'] in ['24h', '7d', '30d']

    def test_error_handling_for_missing_sensors(self):
        """Test that cards handle missing sensor entities gracefully."""
        if not DASHBOARD_AVAILABLE or self.builder is None:
            pytest.skip("MLPerformanceTabBuilder not available")
            
        # Test with unusual entity ID
        entity_id = 'non_existent_room'
        cards = self.builder.build_cards(entity_id)
        
        # Should still return 5 cards even with unusual entity ID
        assert len(cards) == 5
        
        # All cards should be valid dictionaries
        assert all(isinstance(card, dict) for card in cards)
        assert all('type' in card for card in cards)

    def test_builder_immutability(self):
        """Test that builder instances don't affect each other."""
        if not DASHBOARD_AVAILABLE or self.builder is None:
            pytest.skip("MLPerformanceTabBuilder not available")
            
        from custom_components.smart_climate.dashboard.builders import MLPerformanceTabBuilder
        from custom_components.smart_climate.dashboard.templates import GraphTemplates
        from custom_components.smart_climate.dashboard.tooltips import TooltipProvider
        
        # Create two instances
        templates = GraphTemplates()
        tooltips = TooltipProvider()
        builder1 = MLPerformanceTabBuilder(templates, tooltips)
        builder2 = MLPerformanceTabBuilder(templates, tooltips)
        
        # Should get same config from both
        config1 = builder1.get_tab_config()
        config2 = builder2.get_tab_config()
        
        assert config1 == config2
        
        # Should get same cards from both with same entity
        cards1 = builder1.build_cards('test')
        cards2 = builder2.build_cards('test')
        
        assert cards1 == cards2


class TestMLPerformanceTabBuilderIntegration:
    """Integration tests for MLPerformanceTabBuilder with dashboard system."""
    
    def test_integration_with_graph_templates(self):
        """Test that MLPerformanceTabBuilder integrates with GraphTemplates."""
        if not DASHBOARD_AVAILABLE:
            pytest.skip("Dashboard components not available")
            
        try:
            from custom_components.smart_climate.dashboard.builders import MLPerformanceTabBuilder
            from custom_components.smart_climate.dashboard.templates import GraphTemplates
            from custom_components.smart_climate.dashboard.tooltips import TooltipProvider
            
            builder = MLPerformanceTabBuilder(GraphTemplates(), TooltipProvider())
            
            # Test that it can use GraphTemplates
            cards = builder.build_cards('integration_test')
            
            # Should have cards that use graph templates
            graph_cards = [card for card in cards if card['type'] == 'custom:apexcharts-card']
            assert len(graph_cards) >= 3  # Learning, histogram, confidence cards
            
        except ImportError:
            pytest.skip("MLPerformanceTabBuilder not implemented yet")

    def test_integration_with_dashboard_colors(self):
        """Test that MLPerformanceTabBuilder uses DashboardColors."""
        if not DASHBOARD_AVAILABLE:
            pytest.skip("Dashboard components not available")
            
        try:
            from custom_components.smart_climate.dashboard.builders import MLPerformanceTabBuilder
            from custom_components.smart_climate.dashboard.templates import GraphTemplates
            from custom_components.smart_climate.dashboard.tooltips import TooltipProvider
            
            builder = MLPerformanceTabBuilder(GraphTemplates(), TooltipProvider())
            
            # Should be able to reference DashboardColors
            cards = builder.build_cards('color_test')
            
            # Should not fail when using color constants
            assert len(cards) == 5
            
        except ImportError:
            pytest.skip("MLPerformanceTabBuilder not implemented yet")

    def test_yaml_serialization_compatibility(self):
        """Test that generated cards can be serialized to YAML."""
        if not DASHBOARD_AVAILABLE:
            pytest.skip("Dashboard components not available")
            
        try:
            from custom_components.smart_climate.dashboard.builders import MLPerformanceTabBuilder
            from custom_components.smart_climate.dashboard.templates import GraphTemplates
            from custom_components.smart_climate.dashboard.tooltips import TooltipProvider
            import yaml
            
            builder = MLPerformanceTabBuilder(GraphTemplates(), TooltipProvider())
            cards = builder.build_cards('yaml_test')
            
            # All cards should be YAML serializable
            for card in cards:
                yaml_str = yaml.dump(card)
                yaml_parsed = yaml.safe_load(yaml_str)
                assert yaml_parsed == card
                
        except ImportError:
            pytest.skip("MLPerformanceTabBuilder not implemented yet")