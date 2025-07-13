# ABOUTME: Comprehensive tests for AC terminology fix in dashboard template
# Validates correct terminology for temperature window vs absolute thresholds

import yaml
import pytest
from pathlib import Path


class TestDashboardTemperatureWindowTerminology:
    """Test suite for AC terminology fix in dashboard template."""
    
    @pytest.fixture
    def dashboard_yaml_path(self):
        """Path to the dashboard template file."""
        return Path(__file__).parent.parent / "custom_components" / "smart_climate" / "dashboard" / "dashboard_generic.yaml"
    
    @pytest.fixture
    def dashboard_content(self, dashboard_yaml_path):
        """Load dashboard YAML content."""
        with open(dashboard_yaml_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    @pytest.fixture
    def dashboard_data(self, dashboard_content):
        """Parse dashboard YAML data."""
        return yaml.safe_load(dashboard_content)
    
    def test_dashboard_file_exists(self, dashboard_yaml_path):
        """Test that dashboard template file exists."""
        assert dashboard_yaml_path.exists(), f"Dashboard template not found at {dashboard_yaml_path}"
    
    def test_dashboard_yaml_is_valid(self, dashboard_data):
        """Test that dashboard YAML is valid and parseable."""
        assert dashboard_data is not None
        assert isinstance(dashboard_data, dict)
        assert "title" in dashboard_data
        assert "views" in dashboard_data
    
    def test_ac_behavior_learning_section_exists(self, dashboard_data):
        """Test that AC Behavior Learning section exists in the dashboard."""
        overview_view = dashboard_data["views"][0]
        cards = overview_view["cards"]
        
        # Find the AC Behavior Learning section
        ac_section = None
        for card in cards:
            if card.get("type") == "vertical-stack":
                for subcard in card.get("cards", []):
                    if (subcard.get("type") == "markdown" and 
                        "AC Behavior Learning" in subcard.get("content", "")):
                        ac_section = card
                        break
        
        assert ac_section is not None, "AC Behavior Learning section not found"
    
    def test_hysteresis_entities_section_exists(self, dashboard_data):
        """Test that hysteresis entities section exists with temperature attributes."""
        overview_view = dashboard_data["views"][0]
        cards = overview_view["cards"]
        
        # Find entities section with start_threshold and stop_threshold
        hysteresis_entities = None
        for card in cards:
            if card.get("type") == "vertical-stack":
                for subcard in card.get("cards", []):
                    if (subcard.get("type") == "entities" and 
                        any("start_threshold" in str(entity) for entity in subcard.get("entities", []))):
                        hysteresis_entities = subcard
                        break
        
        assert hysteresis_entities is not None, "Hysteresis entities section not found"
        
        # Check that both threshold attributes exist
        entities = hysteresis_entities["entities"]
        threshold_attrs = [entity for entity in entities if entity.get("type") == "attribute"]
        
        start_attr = next((e for e in threshold_attrs if e.get("attribute") == "start_threshold"), None)
        stop_attr = next((e for e in threshold_attrs if e.get("attribute") == "stop_threshold"), None)
        
        assert start_attr is not None, "start_threshold attribute not found"
        assert stop_attr is not None, "stop_threshold attribute not found"
    
    def test_no_misleading_threshold_terminology(self, dashboard_content):
        """Test that misleading 'threshold' terminology is removed."""
        content_lower = dashboard_content.lower()
        
        # These specific misleading terms should not exist
        misleading_terms = [
            "ac start threshold",
            "ac stop threshold", 
            "start threshold",
            "stop threshold"
        ]
        
        for term in misleading_terms:
            assert term not in content_lower, f"Misleading terminology '{term}' still present in dashboard"
    
    def test_correct_temperature_window_terminology(self, dashboard_content):
        """Test that correct temperature window terminology is used."""
        content_lower = dashboard_content.lower()
        
        # At least one of these window-based terms should be present
        correct_terms = [
            "temperature window",
            "cooling window", 
            "window high",
            "window low",
            "window upper",
            "window lower",
            "hysteresis delta",
            "cooling range"
        ]
        
        found_terms = [term for term in correct_terms if term in content_lower]
        assert len(found_terms) > 0, f"No correct temperature window terminology found. Expected one of: {correct_terms}"
    
    def test_temperature_window_explanation_present(self, dashboard_content):
        """Test that some explanation of temperature window concept is present."""
        content_lower = dashboard_content.lower()
        
        # Look for explanatory terms that indicate window/delta concept
        explanatory_terms = [
            "window",
            "delta", 
            "range",
            "independent",
            "consistent"
        ]
        
        found_explanatory = [term for term in explanatory_terms if term in content_lower]
        assert len(found_explanatory) > 0, f"No explanatory temperature window terminology found. Expected some of: {explanatory_terms}"
    
    def test_preserve_all_replace_me_placeholders(self, dashboard_content):
        """Test that all REPLACE_ME_* placeholders are preserved."""
        expected_placeholders = [
            "REPLACE_ME_NAME",
            "REPLACE_ME_CLIMATE", 
            "REPLACE_ME_SWITCH",
            "REPLACE_ME_BUTTON",
            "REPLACE_ME_ROOM_SENSOR",
            "REPLACE_ME_OUTDOOR_SENSOR", 
            "REPLACE_ME_POWER_SENSOR",
            "REPLACE_ME_SENSOR_OFFSET",
            "REPLACE_ME_SENSOR_PROGRESS",
            "REPLACE_ME_SENSOR_ACCURACY", 
            "REPLACE_ME_SENSOR_CALIBRATION",
            "REPLACE_ME_SENSOR_HYSTERESIS"
        ]
        
        for placeholder in expected_placeholders:
            assert placeholder in dashboard_content, f"Required placeholder '{placeholder}' missing from dashboard"
    
    def test_entity_attribute_references_preserved(self, dashboard_data):
        """Test that entity attribute references are preserved correctly."""
        overview_view = dashboard_data["views"][0]
        
        # Find the hysteresis entities section
        hysteresis_entities = None
        for card in overview_view["cards"]:
            if card.get("type") == "vertical-stack":
                for subcard in card.get("cards", []):
                    if (subcard.get("type") == "entities" and 
                        any("start_threshold" in str(entity) for entity in subcard.get("entities", []))):
                        hysteresis_entities = subcard
                        break
        
        assert hysteresis_entities is not None
        
        # Check that attribute references are correct
        entities = hysteresis_entities["entities"]
        threshold_attrs = [entity for entity in entities if entity.get("type") == "attribute"]
        
        for entity in threshold_attrs:
            assert entity.get("entity") == "REPLACE_ME_SENSOR_HYSTERESIS", f"Wrong entity reference in {entity}"
            assert entity.get("attribute") in ["start_threshold", "stop_threshold"], f"Wrong attribute in {entity}"
    
    def test_appropriate_icons_for_temperature_window(self, dashboard_data):
        """Test that icons are appropriate for temperature window concept."""
        overview_view = dashboard_data["views"][0]
        
        # Find threshold entities and check their icons
        hysteresis_entities = None
        for card in overview_view["cards"]:
            if card.get("type") == "vertical-stack":
                for subcard in card.get("cards", []):
                    if (subcard.get("type") == "entities" and 
                        any("start_threshold" in str(entity) for entity in subcard.get("entities", []))):
                        hysteresis_entities = subcard
                        break
        
        assert hysteresis_entities is not None
        
        entities = hysteresis_entities["entities"]
        threshold_attrs = [entity for entity in entities if entity.get("type") == "attribute"]
        
        # Icons should represent temperature ranges/windows, not just up/down arrows
        appropriate_icons = [
            "mdi:thermometer-lines",
            "mdi:thermometer-high", 
            "mdi:thermometer-low",
            "mdi:thermometer-plus",
            "mdi:thermometer-minus",
            "mdi:arrow-expand-vertical",
            "mdi:arrow-expand-horizontal",
            "mdi:format-line-spacing",
            "mdi:unfold-more-vertical",
            "mdi:unfold-less-vertical"
        ]
        
        for entity in threshold_attrs:
            icon = entity.get("icon", "")
            # Icons should be appropriate (not just chevron up/down which imply absolute temps)
            inappropriate_icons = ["mdi:thermometer-chevron-up", "mdi:thermometer-chevron-down"]
            assert icon not in inappropriate_icons, f"Inappropriate icon '{icon}' for temperature window concept"
    
    def test_hysteresis_section_structure_preserved(self, dashboard_data):
        """Test that overall hysteresis section structure is preserved."""
        overview_view = dashboard_data["views"][0]
        
        # Find the AC Behavior Learning section
        ac_section = None
        for card in overview_view["cards"]:
            if card.get("type") == "vertical-stack":
                for subcard in card.get("cards", []):
                    if (subcard.get("type") == "markdown" and 
                        "AC Behavior Learning" in subcard.get("content", "")):
                        ac_section = card
                        break
        
        assert ac_section is not None
        
        # Check that it has both the template cards and entities sections
        cards = ac_section["cards"]
        has_markdown = any(c.get("type") == "markdown" for c in cards)
        has_horizontal_stack = any(c.get("type") == "horizontal-stack" for c in cards)
        has_entities = any(c.get("type") == "entities" for c in cards)
        
        assert has_markdown, "Missing markdown header"
        assert has_horizontal_stack, "Missing horizontal-stack with template cards" 
        assert has_entities, "Missing entities section"
    
    def test_conditional_logic_preserved(self, dashboard_data):
        """Test that conditional logic and card types are preserved."""
        # Check that conditional cards still exist
        found_conditionals = []
        
        def find_conditionals(obj):
            if isinstance(obj, dict):
                if obj.get("type") == "conditional":
                    found_conditionals.append(obj)
                for value in obj.values():
                    find_conditionals(value)
            elif isinstance(obj, list):
                for item in obj:
                    find_conditionals(item)
        
        find_conditionals(dashboard_data)
        
        # Should have at least the power monitoring conditional
        assert len(found_conditionals) > 0, "Conditional logic sections missing from dashboard"
    
    def test_temperature_window_context_in_hysteresis_display(self, dashboard_data):
        """Test that temperature window context is provided in hysteresis display."""
        overview_view = dashboard_data["views"][0]
        
        # Find template cards that display temperature window
        template_cards = []
        
        def find_template_cards(obj):
            if isinstance(obj, dict):
                if obj.get("type") == "custom:mushroom-template-card":
                    template_cards.append(obj)
                for value in obj.values():
                    find_template_cards(value)
            elif isinstance(obj, list):
                for item in obj:
                    find_template_cards(item)
        
        find_template_cards(overview_view)
        
        # Look for temperature window display
        temp_window_cards = [card for card in template_cards 
                           if "temperature_window" in str(card.get("primary", "")).lower()]
        
        assert len(temp_window_cards) > 0, "No template cards displaying temperature window found"
        
        # Check that secondary text provides helpful context
        for card in temp_window_cards:
            secondary = card.get("secondary", "")
            assert "window" in secondary.lower() or "range" in secondary.lower(), f"Secondary text should explain window concept: {secondary}"


class TestDashboardStructuralIntegrity:
    """Test suite to ensure dashboard structural integrity is maintained."""
    
    @pytest.fixture
    def dashboard_yaml_path(self):
        """Path to the dashboard template file."""
        return Path(__file__).parent.parent / "custom_components" / "smart_climate" / "dashboard" / "dashboard_generic.yaml"
    
    @pytest.fixture
    def dashboard_data(self, dashboard_yaml_path):
        """Parse dashboard YAML data."""
        with open(dashboard_yaml_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def test_main_dashboard_structure(self, dashboard_data):
        """Test that main dashboard structure is intact."""
        assert "title" in dashboard_data
        assert "views" in dashboard_data
        assert len(dashboard_data["views"]) >= 2  # Overview and Detailed Stats
        
        overview = dashboard_data["views"][0] 
        assert overview["title"] == "Overview"
        assert overview["path"] == "overview"
        assert "cards" in overview
        
        stats = dashboard_data["views"][1]
        assert stats["title"] == "Detailed Stats" 
        assert stats["path"] == "stats"
        assert "cards" in stats
    
    def test_all_major_sections_present(self, dashboard_data):
        """Test that all major dashboard sections are present."""
        overview_view = dashboard_data["views"][0]
        cards_content = str(overview_view["cards"])
        
        required_sections = [
            "Learning System Status",
            "AC Behavior Learning", 
            "Multi-Layered Intelligence",
            "Intelligent Features Configuration",
            "Performance Charts",
            "Controls"
        ]
        
        for section in required_sections:
            assert section in cards_content, f"Required section '{section}' missing from dashboard"
    
    def test_chart_configurations_intact(self, dashboard_data):
        """Test that chart configurations are intact."""
        overview_view = dashboard_data["views"][0]
        
        # Find ApexCharts cards
        apex_cards = []
        
        def find_apex_cards(obj):
            if isinstance(obj, dict):
                if obj.get("type") == "custom:apexcharts-card":
                    apex_cards.append(obj)
                for value in obj.values():
                    find_apex_cards(value)
            elif isinstance(obj, list):
                for item in obj:
                    find_apex_cards(item)
        
        find_apex_cards(overview_view)
        
        assert len(apex_cards) >= 4, f"Expected at least 4 ApexCharts cards, found {len(apex_cards)}"
        
        # Check that charts have proper configuration
        for card in apex_cards:
            assert "header" in card
            assert "series" in card
            assert len(card["series"]) > 0
    
    def test_v13_intelligence_features_preserved(self, dashboard_data):
        """Test that v1.3.0 intelligence features are preserved."""
        overview_view = dashboard_data["views"][0]
        cards_content = str(overview_view["cards"])
        
        v13_features = [
            "reactive_offset",
            "predictive_offset", 
            "total_offset",
            "predictive_strategy",
            "adaptive_delay",
            "weather_forecast",
            "seasonal_adaptation"
        ]
        
        for feature in v13_features:
            assert feature in cards_content, f"v1.3.0 feature '{feature}' missing from dashboard"