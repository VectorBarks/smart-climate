"""Tests for the Smart Climate dashboard template."""

import os
import yaml
import pytest
from pathlib import Path


class TestDashboardTemplate:
    """Test the dashboard template YAML file."""

    @pytest.fixture
    def template_path(self):
        """Get the path to the dashboard template file."""
        return Path(__file__).parent.parent / "custom_components" / "smart_climate" / "dashboard" / "dashboard.yaml"

    @pytest.fixture
    def template_content(self, template_path):
        """Load the dashboard template content."""
        if not template_path.exists():
            pytest.skip("Dashboard template not yet created")
        with open(template_path, "r") as f:
            return f.read()

    @pytest.fixture
    def template_yaml(self, template_content):
        """Parse the dashboard template as YAML."""
        return yaml.safe_load(template_content)

    def test_dashboard_directory_exists(self):
        """Test that the dashboard directory exists."""
        dashboard_dir = Path(__file__).parent.parent / "custom_components" / "smart_climate" / "dashboard"
        assert dashboard_dir.exists(), "Dashboard directory should exist"
        assert dashboard_dir.is_dir(), "Dashboard should be a directory"

    def test_dashboard_template_exists(self, template_path):
        """Test that the dashboard template file exists."""
        assert template_path.exists(), "Dashboard template file should exist"
        assert template_path.suffix == ".yaml", "Dashboard template should be a YAML file"

    def test_yaml_validity(self, template_yaml):
        """Test that the template is valid YAML."""
        assert template_yaml is not None, "Template should parse as valid YAML"
        assert isinstance(template_yaml, dict), "Template should be a YAML mapping"

    def test_dashboard_structure(self, template_yaml):
        """Test the basic dashboard structure."""
        assert "title" in template_yaml, "Dashboard should have a title"
        assert "views" in template_yaml, "Dashboard should have views"
        assert isinstance(template_yaml["views"], list), "Views should be a list"
        assert len(template_yaml["views"]) > 0, "Dashboard should have at least one view"

    def test_placeholder_consistency(self, template_content):
        """Test that placeholders follow consistent pattern."""
        # Check for consistent placeholder pattern
        assert "REPLACE_ME_ENTITY" in template_content, "Should use REPLACE_ME_ENTITY placeholder"
        assert "REPLACE_ME_NAME" in template_content, "Should use REPLACE_ME_NAME placeholder"
        
        # Ensure no other placeholder patterns
        assert "{{" not in template_content, "Should not use Jinja2 template syntax"
        assert "${" not in template_content, "Should not use shell variable syntax"
        assert "<" not in template_content or "<=" in template_content, "Should not use XML-style placeholders"

    def test_overview_view(self, template_yaml):
        """Test the overview view structure."""
        views = template_yaml.get("views", [])
        overview = next((v for v in views if v.get("path") == "overview"), None)
        assert overview is not None, "Should have an overview view"
        assert "title" in overview, "Overview should have a title"
        assert "cards" in overview, "Overview should have cards"
        assert isinstance(overview["cards"], list), "Overview cards should be a list"

    def test_thermostat_card(self, template_yaml):
        """Test that a thermostat card exists."""
        views = template_yaml.get("views", [])
        cards = []
        for view in views:
            cards.extend(self._flatten_cards(view.get("cards", [])))
        
        thermostat_cards = [c for c in cards if c.get("type") == "thermostat"]
        assert len(thermostat_cards) > 0, "Should have at least one thermostat card"
        
        # Check thermostat configuration
        thermostat = thermostat_cards[0]
        assert "entity" in thermostat, "Thermostat should have an entity"
        assert "climate.REPLACE_ME_ENTITY" in thermostat["entity"], "Thermostat should use placeholder"

    def test_gauge_cards(self, template_yaml):
        """Test that gauge cards exist for key metrics."""
        views = template_yaml.get("views", [])
        cards = []
        for view in views:
            cards.extend(self._flatten_cards(view.get("cards", [])))
        
        gauge_cards = [c for c in cards if c.get("type") == "gauge"]
        assert len(gauge_cards) >= 3, "Should have at least 3 gauge cards"
        
        # Check for specific gauges
        gauge_entities = [g.get("entity", "") for g in gauge_cards]
        assert any("offset_current" in e for e in gauge_entities), "Should have current offset gauge"
        assert any("learning_progress" in e for e in gauge_entities), "Should have learning progress gauge"
        assert any("accuracy_current" in e for e in gauge_entities), "Should have accuracy gauge"

    def test_history_graph_cards(self, template_yaml):
        """Test that history graph cards exist."""
        views = template_yaml.get("views", [])
        cards = []
        for view in views:
            cards.extend(self._flatten_cards(view.get("cards", [])))
        
        history_cards = [c for c in cards if c.get("type") == "history-graph"]
        assert len(history_cards) >= 1, "Should have at least one history graph"

    def test_entities_card(self, template_yaml):
        """Test that entities card exists for status information."""
        views = template_yaml.get("views", [])
        cards = []
        for view in views:
            cards.extend(self._flatten_cards(view.get("cards", [])))
        
        entities_cards = [c for c in cards if c.get("type") == "entities"]
        assert len(entities_cards) >= 1, "Should have at least one entities card"
        
        # Check for learning switch
        for card in entities_cards:
            entities = card.get("entities", [])
            if any("switch.REPLACE_ME_ENTITY_learning" in str(e) for e in entities):
                break
        else:
            pytest.fail("Should have learning switch in entities card")

    def test_button_card(self, template_yaml):
        """Test that reset button exists."""
        views = template_yaml.get("views", [])
        cards = []
        for view in views:
            cards.extend(self._flatten_cards(view.get("cards", [])))
        
        # Check for button in entities cards or as standalone
        button_found = False
        for card in cards:
            if card.get("type") == "button":
                if "button.REPLACE_ME_ENTITY_reset_training_data" in card.get("entity", ""):
                    button_found = True
                    break
            elif card.get("type") == "entities":
                entities = card.get("entities", [])
                if any("button.REPLACE_ME_ENTITY_reset_training_data" in str(e) for e in entities):
                    button_found = True
                    break
        
        assert button_found, "Should have reset training data button"

    def test_responsive_layout(self, template_yaml):
        """Test that layout uses responsive design patterns."""
        views = template_yaml.get("views", [])
        cards = []
        for view in views:
            cards.extend(view.get("cards", []))
        
        # Check for layout cards
        layout_types = ["vertical-stack", "horizontal-stack", "grid"]
        layout_cards = [c for c in cards if c.get("type") in layout_types]
        assert len(layout_cards) > 0, "Should use layout cards for responsive design"

    def test_conditional_cards(self, template_yaml):
        """Test that conditional cards exist for enhanced experience."""
        views = template_yaml.get("views", [])
        cards = []
        for view in views:
            cards.extend(self._flatten_cards(view.get("cards", [])))
        
        # Check for markdown cards with custom card suggestions
        markdown_cards = [c for c in cards if c.get("type") == "markdown"]
        custom_card_mentions = 0
        for card in markdown_cards:
            content = card.get("content", "")
            if "custom:" in content or "HACS" in content:
                custom_card_mentions += 1
        
        # Also check in conditional cards that might contain markdown
        conditional_cards = [c for c in cards if c.get("type") == "conditional"]
        for card in conditional_cards:
            if "card" in card and card["card"].get("type") == "vertical-stack":
                nested_cards = card["card"].get("cards", [])
                for nested in nested_cards:
                    if nested.get("type") == "markdown":
                        content = nested.get("content", "")
                        if "custom:" in content or "HACS" in content:
                            custom_card_mentions += 1
        
        assert custom_card_mentions > 0, "Should mention custom card options"

    def test_all_sensors_used(self, template_yaml):
        """Test that all dashboard sensors are utilized."""
        views = template_yaml.get("views", [])
        all_content = yaml.dump(template_yaml)
        
        # Check that all expected sensors appear
        expected_sensors = [
            "offset_current",
            "learning_progress", 
            "accuracy_current",
            "calibration_status",
            "hysteresis_state"
        ]
        
        for sensor in expected_sensors:
            assert f"sensor.REPLACE_ME_ENTITY_{sensor}" in all_content, f"Should use {sensor} sensor"

    def test_card_titles_and_names(self, template_yaml):
        """Test that cards have appropriate titles or names."""
        views = template_yaml.get("views", [])
        cards = []
        for view in views:
            cards.extend(self._flatten_cards(view.get("cards", [])))
        
        # Cards that should have titles
        for card in cards:
            card_type = card.get("type")
            if card_type in ["entities", "history-graph"]:
                assert "title" in card or "name" in card, f"{card_type} card should have title or name"

    def test_no_hardcoded_entity_ids(self, template_content):
        """Test that no hardcoded entity IDs exist."""
        # Common entity patterns that shouldn't appear
        hardcoded_patterns = [
            "climate.living_room",
            "sensor.temperature",
            "switch.smart_climate",
            "climate.ac_unit",
            "sensor.room_temp"
        ]
        
        for pattern in hardcoded_patterns:
            assert pattern not in template_content, f"Should not contain hardcoded entity ID: {pattern}"

    def _flatten_cards(self, cards):
        """Recursively flatten nested cards from stacks."""
        flattened = []
        for card in cards:
            flattened.append(card)
            if card.get("type") in ["vertical-stack", "horizontal-stack", "grid"]:
                if "cards" in card:
                    flattened.extend(self._flatten_cards(card["cards"]))
        return flattened

    def test_mode_selector(self, template_yaml):
        """Test that preset mode selector exists."""
        views = template_yaml.get("views", [])
        all_content = yaml.dump(template_yaml)
        
        # Should have some way to control preset modes
        assert "preset_mode" in all_content or "preset mode" in all_content.lower(), \
            "Should have preset mode control"

    def test_learning_status_section(self, template_yaml):
        """Test that learning status information is displayed."""
        views = template_yaml.get("views", [])
        cards = []
        for view in views:
            cards.extend(self._flatten_cards(view.get("cards", [])))
        
        # Look for entities cards that might show learning status
        learning_info_found = False
        for card in cards:
            if card.get("type") == "entities":
                entities = card.get("entities", [])
                # Check if any entity shows learning information
                entity_strings = str(entities)
                if any(term in entity_strings for term in ["calibration", "hysteresis", "learning"]):
                    learning_info_found = True
                    break
        
        assert learning_info_found, "Should display learning status information"

    def test_custom_card_fallbacks(self, template_yaml):
        """Test that core card alternatives exist for custom cards."""
        views = template_yaml.get("views", [])
        all_content = yaml.dump(template_yaml)
        
        # If custom cards are mentioned, should also have core alternatives
        if "custom:apexcharts-card" in all_content:
            assert "history-graph" in all_content, "Should provide history-graph as fallback for apexcharts"
        
        if "custom:mushroom-" in all_content:
            assert "thermostat" in all_content or "climate" in all_content, \
                "Should provide core climate card as fallback"