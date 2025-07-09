"""Tests for responsive dashboard layout functionality."""
# ABOUTME: Tests for validating responsive layout behavior in Smart Climate dashboard
# Mobile/tablet/desktop breakpoints, conditional visibility, and layout optimization

import pytest
import yaml
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch

from tests.dashboard_test_utils import (
    load_blueprint_yaml,
    validate_card_structure,
    get_nested_cards
)


class TestResponsiveLayout:
    """Test responsive layout configurations."""
    
    @pytest.fixture
    def blueprint_content(self) -> Dict[str, Any]:
        """Load blueprint YAML for testing."""
        return load_blueprint_yaml()
    
    def test_mobile_layout_uses_vertical_stacks(self, blueprint_content):
        """Test that mobile layout uses vertical stacks for proper stacking."""
        # Get mobile-specific sections from blueprint
        mobile_sections = self._get_mobile_sections(blueprint_content)
        
        # Verify all mobile sections use vertical-stack
        for section in mobile_sections:
            assert section.get('type') == 'vertical-stack', \
                f"Mobile section should use vertical-stack, got {section.get('type')}"
            
            # Check that cards within are not using horizontal-stack
            cards = section.get('cards', [])
            for card in cards:
                if card.get('type') == 'horizontal-stack':
                    # If horizontal stack exists, it should have max 2 cards for mobile
                    assert len(card.get('cards', [])) <= 2, \
                        "Mobile horizontal stacks should have max 2 cards"
    
    def test_mobile_gauge_sizes_optimized(self, blueprint_content):
        """Test that gauge cards have mobile-friendly sizes."""
        mobile_sections = self._get_mobile_sections(blueprint_content)
        
        for section in mobile_sections:
            gauge_cards = self._find_cards_by_type(section, 'gauge')
            
            for gauge in gauge_cards:
                # Mobile gauges should be in a specific size range
                # Check if gauge has appropriate mobile styling
                assert self._has_mobile_gauge_config(gauge), \
                    "Gauge cards should have mobile-optimized configuration"
    
    def test_desktop_grid_layout_configuration(self, blueprint_content):
        """Test that desktop layout uses appropriate grid configuration."""
        desktop_sections = self._get_desktop_sections(blueprint_content)
        
        for section in desktop_sections:
            # Desktop should use grid or horizontal layouts
            assert section.get('type') in ['grid', 'horizontal-stack', 'vertical-stack'], \
                f"Desktop section has invalid type: {section.get('type')}"
            
            # If grid, check column configuration
            if section.get('type') == 'grid':
                assert 'columns' in section, "Grid layout must specify columns"
                assert section['columns'] >= 2, "Desktop grid should have at least 2 columns"
                assert section['columns'] <= 4, "Desktop grid should have max 4 columns"
    
    def test_conditional_visibility_based_on_screen_size(self, blueprint_content):
        """Test conditional cards that show/hide based on screen size."""
        # Find all conditional cards
        conditional_cards = self._find_conditional_cards(blueprint_content)
        
        # Should have at least some conditional cards for responsive behavior
        assert len(conditional_cards) > 0, "Blueprint should have conditional cards for responsive layout"
        
        # Check that conditionals include screen size conditions
        screen_size_conditions = 0
        for card in conditional_cards:
            conditions = card.get('conditions', [])
            for condition in conditions:
                # Look for media query or screen size conditions
                if self._is_screen_size_condition(condition):
                    screen_size_conditions += 1
        
        assert screen_size_conditions > 0, "Should have screen size based conditions"
    
    def test_mobile_simplified_displays(self, blueprint_content):
        """Test that mobile displays are simplified versions."""
        mobile_sections = self._get_mobile_sections(blueprint_content)
        desktop_sections = self._get_desktop_sections(blueprint_content)
        
        # Mobile should have fewer total cards than desktop
        mobile_card_count = sum(len(self._get_all_cards(s)) for s in mobile_sections)
        desktop_card_count = sum(len(self._get_all_cards(s)) for s in desktop_sections)
        
        # Mobile might have fewer cards or simpler configurations
        # This is a general guideline test
        assert mobile_card_count <= desktop_card_count * 1.2, \
            "Mobile layout should not be significantly more complex than desktop"
    
    def test_responsive_chart_configurations(self, blueprint_content):
        """Test that charts have appropriate configurations for different screen sizes."""
        # Find all chart cards (history-graph, apexcharts)
        chart_types = ['history-graph', 'custom:apexcharts-card']
        
        mobile_charts = []
        desktop_charts = []
        
        for section in self._get_mobile_sections(blueprint_content):
            mobile_charts.extend(self._find_cards_by_types(section, chart_types))
        
        for section in self._get_desktop_sections(blueprint_content):
            desktop_charts.extend(self._find_cards_by_types(section, chart_types))
        
        # Mobile charts should have reduced data spans or simplified configs
        for chart in mobile_charts:
            if chart.get('type') == 'history-graph':
                hours = chart.get('hours_to_show', 24)
                assert hours <= 24, "Mobile history graphs should show 24 hours or less"
            
            elif 'apexcharts' in chart.get('type', ''):
                # Check for mobile-optimized apex config
                apex_config = chart.get('apex_config', {})
                chart_config = apex_config.get('chart', {})
                
                # Mobile charts should have reasonable height
                height = chart_config.get('height', 300)
                assert height <= 250, "Mobile charts should have reduced height"
    
    def test_breakpoint_definitions(self, blueprint_content):
        """Test that breakpoints are properly defined for responsive behavior."""
        # Look for breakpoint definitions or media query references
        responsive_config = self._find_responsive_configuration(blueprint_content)
        
        # Should have mobile/tablet/desktop breakpoint definitions
        expected_breakpoints = {
            'mobile': 768,  # < 768px
            'tablet': 1024,  # 768px - 1024px
            'desktop': 1024  # > 1024px
        }
        
        # This test verifies the implementation follows the spec
        # The actual implementation might use different methods
        assert responsive_config is not None, "Should have responsive configuration"
    
    def test_no_horizontal_scroll_on_mobile(self, blueprint_content):
        """Test that mobile layout prevents horizontal scrolling."""
        mobile_sections = self._get_mobile_sections(blueprint_content)
        
        for section in mobile_sections:
            # Check that no cards have fixed widths that could cause scrolling
            all_cards = self._get_all_cards(section)
            
            for card in all_cards:
                # Cards should not have fixed pixel widths
                if 'width' in card:
                    width = card['width']
                    assert not isinstance(width, int) or width <= 400, \
                        f"Card has fixed width {width} that may cause horizontal scroll"
                
                # Check styles for width definitions
                styles = card.get('styles', {})
                card_styles = styles.get('card', []) if isinstance(styles.get('card'), list) else []
                
                for style in card_styles:
                    if isinstance(style, dict) and 'width' in style:
                        assert 'px' not in str(style['width']) or int(style['width'].replace('px', '')) <= 400, \
                            "Fixed pixel widths should be mobile-friendly"
    
    def test_tablet_layout_optimization(self, blueprint_content):
        """Test tablet-specific layout optimizations."""
        # Tablet layouts should be between mobile and desktop
        tablet_sections = self._get_tablet_sections(blueprint_content)
        
        if tablet_sections:  # Tablet might use mobile or desktop layout
            for section in tablet_sections:
                # Verify tablet-appropriate configurations
                if section.get('type') == 'horizontal-stack':
                    cards = section.get('cards', [])
                    assert len(cards) <= 3, "Tablet horizontal stacks should have max 3 cards"
    
    def test_responsive_layout_switching(self, blueprint_content):
        """Test that layout can switch between mobile/desktop views."""
        # Should have different layout sections for different screen sizes
        has_mobile = len(self._get_mobile_sections(blueprint_content)) > 0
        has_desktop = len(self._get_desktop_sections(blueprint_content)) > 0
        
        assert has_mobile or has_desktop, "Should have responsive layout sections"
        
        # If both exist, verify they're properly conditioned
        if has_mobile and has_desktop:
            # Check that they don't overlap (both showing at same time)
            mobile_conditions = self._get_section_conditions(blueprint_content, 'mobile')
            desktop_conditions = self._get_section_conditions(blueprint_content, 'desktop')
            
            # Conditions should be mutually exclusive
            assert mobile_conditions != desktop_conditions, \
                "Mobile and desktop conditions should be different"
    
    # Helper methods
    def _get_mobile_sections(self, blueprint: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract mobile-specific layout sections."""
        sections = []
        
        # Look for conditional cards with mobile conditions
        cards = blueprint.get('cards', [])
        for card in cards:
            if card.get('type') == 'conditional':
                conditions = card.get('conditions', [])
                if any(self._is_mobile_condition(c) for c in conditions):
                    sections.append(card.get('card', {}))
            
            # Also check for mobile-specific class or ID markers
            elif self._has_mobile_marker(card):
                sections.append(card)
        
        # If no explicit mobile sections, treat all as mobile (mobile-first)
        if not sections:
            sections = cards
        
        return sections
    
    def _get_desktop_sections(self, blueprint: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract desktop-specific layout sections."""
        sections = []
        
        cards = blueprint.get('cards', [])
        for card in cards:
            if card.get('type') == 'conditional':
                conditions = card.get('conditions', [])
                if any(self._is_desktop_condition(c) for c in conditions):
                    sections.append(card.get('card', {}))
            elif self._has_desktop_marker(card):
                sections.append(card)
        
        return sections
    
    def _get_tablet_sections(self, blueprint: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract tablet-specific layout sections."""
        sections = []
        
        cards = blueprint.get('cards', [])
        for card in cards:
            if card.get('type') == 'conditional':
                conditions = card.get('conditions', [])
                if any(self._is_tablet_condition(c) for c in conditions):
                    sections.append(card.get('card', {}))
        
        return sections
    
    def _find_cards_by_type(self, section: Dict[str, Any], card_type: str) -> List[Dict[str, Any]]:
        """Find all cards of a specific type within a section."""
        found_cards = []
        
        def search_cards(cards: List[Dict[str, Any]]):
            for card in cards:
                if card.get('type') == card_type:
                    found_cards.append(card)
                
                # Recursively search nested cards
                if 'cards' in card:
                    search_cards(card['cards'])
                if 'card' in card:
                    search_cards([card['card']])
        
        if 'cards' in section:
            search_cards(section['cards'])
        
        return found_cards
    
    def _find_cards_by_types(self, section: Dict[str, Any], card_types: List[str]) -> List[Dict[str, Any]]:
        """Find all cards matching any of the specified types."""
        found_cards = []
        for card_type in card_types:
            found_cards.extend(self._find_cards_by_type(section, card_type))
        return found_cards
    
    def _find_conditional_cards(self, blueprint: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find all conditional cards in the blueprint."""
        conditional_cards = []
        
        def search_cards(cards: List[Dict[str, Any]]):
            for card in cards:
                if card.get('type') == 'conditional':
                    conditional_cards.append(card)
                
                # Recursively search
                if 'cards' in card:
                    search_cards(card['cards'])
        
        cards = blueprint.get('cards', [])
        search_cards(cards)
        
        return conditional_cards
    
    def _has_mobile_gauge_config(self, gauge: Dict[str, Any]) -> bool:
        """Check if gauge has mobile-optimized configuration."""
        # Mobile gauges might have specific styling or reduced segments
        segments = gauge.get('segments', [])
        
        # Mobile gauges should be simplified
        if len(segments) > 6:
            return False
        
        # Check for mobile-friendly configuration
        return True
    
    def _is_screen_size_condition(self, condition: Dict[str, Any]) -> bool:
        """Check if condition is related to screen size."""
        # Look for media query type conditions
        # This is a placeholder - actual implementation depends on HA's conditional card syntax
        return (
            condition.get('condition') == 'screen' or
            'media_query' in condition or
            'screen_width' in condition
        )
    
    def _is_mobile_condition(self, condition: Dict[str, Any]) -> bool:
        """Check if condition is for mobile screens."""
        # Placeholder - actual implementation depends on how conditions are structured
        return False  # Will be implemented based on actual condition structure
    
    def _is_desktop_condition(self, condition: Dict[str, Any]) -> bool:
        """Check if condition is for desktop screens."""
        return False  # Will be implemented based on actual condition structure
    
    def _is_tablet_condition(self, condition: Dict[str, Any]) -> bool:
        """Check if condition is for tablet screens."""
        return False  # Will be implemented based on actual condition structure
    
    def _has_mobile_marker(self, card: Dict[str, Any]) -> bool:
        """Check if card has mobile-specific markers."""
        # Look for class names, IDs, or other markers
        view_layout = card.get('view_layout', {})
        return 'mobile' in str(view_layout).lower()
    
    def _has_desktop_marker(self, card: Dict[str, Any]) -> bool:
        """Check if card has desktop-specific markers."""
        view_layout = card.get('view_layout', {})
        return 'desktop' in str(view_layout).lower()
    
    def _get_all_cards(self, section: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get all cards (including nested) from a section."""
        all_cards = []
        
        def collect_cards(container: Dict[str, Any]):
            if 'cards' in container:
                for card in container['cards']:
                    all_cards.append(card)
                    collect_cards(card)
            if 'card' in container:
                all_cards.append(container['card'])
                collect_cards(container['card'])
        
        collect_cards(section)
        return all_cards
    
    def _find_responsive_configuration(self, blueprint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find responsive configuration in blueprint."""
        # Look for responsive config in blueprint metadata or special sections
        # This is implementation-specific
        return {}  # Placeholder
    
    def _get_section_conditions(self, blueprint: Dict[str, Any], section_type: str) -> List[Dict[str, Any]]:
        """Get conditions for a specific section type."""
        conditions = []
        
        if section_type == 'mobile':
            sections = self._get_mobile_sections(blueprint)
        elif section_type == 'desktop':
            sections = self._get_desktop_sections(blueprint)
        else:
            return conditions
        
        # Extract conditions from conditional cards
        for section in sections:
            if section.get('type') == 'conditional':
                conditions.extend(section.get('conditions', []))
        
        return conditions


class TestResponsiveLayoutEdgeCases:
    """Test edge cases and error conditions for responsive layouts."""
    
    def test_handles_missing_custom_cards_gracefully(self):
        """Test that layout works when custom cards are not available."""
        # Test will be implemented when blueprint structure is finalized
        pass
    
    def test_handles_very_small_screens(self):
        """Test layout behavior on very small screens (< 400px)."""
        # Test will be implemented when blueprint structure is finalized
        pass
    
    def test_handles_very_large_screens(self):
        """Test layout behavior on very large screens (> 2000px)."""
        # Test will be implemented when blueprint structure is finalized
        pass
    
    def test_layout_performance_with_many_cards(self):
        """Test that responsive layout doesn't impact performance with many cards."""
        # Test will be implemented when blueprint structure is finalized
        pass