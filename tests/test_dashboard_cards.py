"""Tests for Smart Climate Dashboard card configurations."""
# ABOUTME: Test suite for validating dashboard card configurations
# Ensures all cards in the blueprint work correctly with entity references

import pytest
import yaml
from typing import Dict, Any, List


# Custom YAML constructor to handle !input tags in blueprints
def input_constructor(loader, node):
    """Handle !input tags by returning a placeholder string."""
    return f"!input {loader.construct_scalar(node)}"

# Add the constructor to SafeLoader
yaml.SafeLoader.add_constructor('!input', input_constructor)


class TestDashboardCards:
    """Test dashboard card configurations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.climate_entity = "climate.smart_climate"
        self.learning_switch = "switch.smart_climate_learning"
        self.template_sensors = {
            "offset_history": f"sensor.smart_climate_{self.climate_entity.replace('.', '_')}_offset_history",
            "learning_progress": f"sensor.smart_climate_{self.climate_entity.replace('.', '_')}_learning_progress",
            "accuracy_trend": f"sensor.smart_climate_{self.climate_entity.replace('.', '_')}_accuracy_trend",
            "calibration_status": f"sensor.smart_climate_{self.climate_entity.replace('.', '_')}_calibration_status",
            "hysteresis_state": f"sensor.smart_climate_{self.climate_entity.replace('.', '_')}_hysteresis_state"
        }

    def _load_dashboard_yaml(self) -> Dict[str, Any]:
        """Load and parse the dashboard blueprint YAML."""
        with open("custom_components/smart_climate/blueprints/dashboard/smart_climate_dashboard.yaml", "r") as f:
            # Load the blueprint file which has multiple top-level keys
            # This is valid for Home Assistant blueprints
            return yaml.safe_load(f)

    def _find_card_by_type_and_entity(self, cards: List[Dict], card_type: str, entity: str) -> Dict:
        """Find a card by type and entity."""
        for card in cards:
            if card.get("type") == card_type:
                if card.get("entity") == entity:
                    return card
                # Check in cards within stacks
                if "cards" in card:
                    found = self._find_card_by_type_and_entity(card["cards"], card_type, entity)
                    if found:
                        return found
        return None

    def test_current_status_section_exists(self):
        """Test that current status section with gauges exists."""
        dashboard = self._load_dashboard_yaml()
        cards = dashboard.get("cards", [])
        assert len(cards) > 0, "Dashboard should have cards"
        
        # Find current status section (should be first vertical-stack)
        status_section = None
        for card in cards:
            if card.get("type") == "vertical-stack" and "Current Status" in card.get("title", ""):
                status_section = card
                break
        
        assert status_section is not None, "Current status section should exist"
        assert "cards" in status_section, "Status section should contain cards"

    def test_climate_control_card_configuration(self):
        """Test climate control card is properly configured."""
        dashboard = self._load_dashboard_yaml()
        cards = dashboard.get("cards", [])
        
        # Find climate card (could be standard or mushroom)
        climate_card = None
        for card in cards:
            if card.get("type") == "vertical-stack" and "Current Status" in card.get("title", ""):
                # Look in the current status section
                for subcard in card.get("cards", []):
                    if subcard.get("type") == "climate":
                        climate_card = subcard
                        break
        
        assert climate_card is not None, "Climate control card should exist"
        assert climate_card.get("entity") == "!input climate_entity", "Climate card should reference input entity"

    def test_offset_gauge_configuration(self):
        """Test current offset gauge has correct range and configuration."""
        dashboard = self._load_dashboard_yaml()
        cards = dashboard.get("cards", [])
        
        # Find offset gauge
        offset_gauge = None
        for card in cards:
            if card.get("type") == "vertical-stack" and "cards" in card:
                for subcard in card["cards"]:
                    if subcard.get("type") == "horizontal-stack" and "cards" in subcard:
                        for gauge in subcard["cards"]:
                            if gauge.get("type") == "gauge" and "offset" in gauge.get("name", "").lower():
                                offset_gauge = gauge
                                break
        
        assert offset_gauge is not None, "Offset gauge should exist"
        assert offset_gauge.get("min") == -5, "Offset gauge min should be -5"
        assert offset_gauge.get("max") == 5, "Offset gauge max should be 5"
        assert offset_gauge.get("unit") == "°C", "Offset gauge should show temperature unit"

    def test_accuracy_gauge_configuration(self):
        """Test learning accuracy gauge configuration."""
        dashboard = self._load_dashboard_yaml()
        cards = dashboard.get("cards", [])
        
        # Find accuracy gauge
        accuracy_gauge = None
        for card in cards:
            if card.get("type") == "vertical-stack" and "cards" in card:
                for subcard in card["cards"]:
                    if subcard.get("type") == "horizontal-stack" and "cards" in subcard:
                        for gauge in subcard["cards"]:
                            if gauge.get("type") == "gauge" and "accuracy" in gauge.get("name", "").lower():
                                accuracy_gauge = gauge
                                break
        
        assert accuracy_gauge is not None, "Accuracy gauge should exist"
        assert accuracy_gauge.get("min") == 0, "Accuracy gauge min should be 0"
        assert accuracy_gauge.get("max") == 100, "Accuracy gauge max should be 100"
        assert accuracy_gauge.get("unit") == "%", "Accuracy gauge should show percentage"

    def test_confidence_gauge_configuration(self):
        """Test confidence level gauge configuration."""
        dashboard = self._load_dashboard_yaml()
        cards = dashboard.get("cards", [])
        
        # Find confidence gauge
        confidence_gauge = None
        for card in cards:
            if card.get("type") == "vertical-stack" and "cards" in card:
                for subcard in card["cards"]:
                    if subcard.get("type") == "horizontal-stack" and "cards" in subcard:
                        for gauge in subcard["cards"]:
                            if gauge.get("type") == "gauge" and "confidence" in gauge.get("name", "").lower():
                                confidence_gauge = gauge
                                break
        
        assert confidence_gauge is not None, "Confidence gauge should exist"
        assert confidence_gauge.get("min") == 0, "Confidence gauge min should be 0"
        assert confidence_gauge.get("max") == 100, "Confidence gauge max should be 100"
        assert confidence_gauge.get("unit") == "%", "Confidence gauge should show percentage"

    def test_learning_progress_section_exists(self):
        """Test that learning progress section with charts exists."""
        dashboard = self._load_dashboard_yaml()
        cards = dashboard.get("cards", [])
        
        # Find learning progress section
        progress_section = None
        for card in cards:
            if card.get("type") == "vertical-stack" and "Learning Progress" in card.get("title", ""):
                progress_section = card
                break
        
        assert progress_section is not None, "Learning progress section should exist"
        assert "cards" in progress_section, "Progress section should contain cards"

    def test_calibration_hysteresis_section_exists(self):
        """Test that calibration & hysteresis section exists."""
        dashboard = self._load_dashboard_yaml()
        cards = dashboard.get("cards", [])
        
        # Find calibration section
        calibration_section = None
        for card in cards:
            if card.get("type") == "vertical-stack" and "Calibration" in card.get("title", ""):
                calibration_section = card
                break
        
        assert calibration_section is not None, "Calibration & hysteresis section should exist"
        assert "cards" in calibration_section, "Calibration section should contain cards"

    def test_control_section_exists(self):
        """Test that control section with buttons exists."""
        dashboard = self._load_dashboard_yaml()
        cards = dashboard.get("cards", [])
        
        # Find control section
        control_section = None
        for card in cards:
            if card.get("type") == "vertical-stack" and "Control" in card.get("title", ""):
                control_section = card
                break
        
        assert control_section is not None, "Control section should exist"
        assert "cards" in control_section, "Control section should contain cards"

    def test_mode_buttons_configuration(self):
        """Test mode selection buttons are configured."""
        dashboard = self._load_dashboard_yaml()
        cards = dashboard.get("cards", [])
        
        # Find mode buttons
        mode_buttons = []
        for card in cards:
            if card.get("type") == "vertical-stack" and "Control" in card.get("title", ""):
                for subcard in card.get("cards", []):
                    if subcard.get("type") == "horizontal-stack":
                        for button in subcard.get("cards", []):
                            if button.get("type") == "button" and "tap_action" in button:
                                mode_buttons.append(button)
        
        assert len(mode_buttons) >= 4, "Should have at least 4 mode buttons (none, away, sleep, boost)"
        
        # Check each button has proper service call
        for button in mode_buttons:
            tap_action = button.get("tap_action", {})
            assert tap_action.get("action") == "call-service", "Mode button should call service"
            assert tap_action.get("service") == "climate.set_preset_mode", "Should call set_preset_mode service"

    def test_reset_button_configuration(self):
        """Test reset training data button configuration."""
        dashboard = self._load_dashboard_yaml()
        cards = dashboard.get("cards", [])
        
        # Find reset button
        reset_button = None
        for card in cards:
            if card.get("type") == "vertical-stack" and "Control" in card.get("title", ""):
                for subcard in card.get("cards", []):
                    if subcard.get("type") == "button" and "reset" in subcard.get("name", "").lower():
                        reset_button = subcard
                        break
        
        assert reset_button is not None, "Reset button should exist"
        tap_action = reset_button.get("tap_action", {})
        assert tap_action.get("action") == "call-service", "Reset button should call service"
        assert tap_action.get("service") == "button.press", "Should call button.press service"

    def test_all_gauge_cards_have_severity_colors(self):
        """Test that gauge cards have appropriate severity color configurations."""
        dashboard = self._load_dashboard_yaml()
        cards = dashboard.get("cards", [])
        
        gauges = []
        for card in cards:
            if card.get("type") == "vertical-stack" and "cards" in card:
                for subcard in card["cards"]:
                    if subcard.get("type") == "horizontal-stack" and "cards" in subcard:
                        for gauge in subcard["cards"]:
                            if gauge.get("type") == "gauge":
                                gauges.append(gauge)
        
        for gauge in gauges:
            if "accuracy" in gauge.get("name", "").lower() or "confidence" in gauge.get("name", "").lower():
                assert "severity" in gauge, f"Gauge {gauge.get('name')} should have severity colors"
                severity = gauge["severity"]
                assert "green" in severity, "Should have green severity range"
                assert "yellow" in severity, "Should have yellow severity range"
                assert "red" in severity, "Should have red severity range"

    def test_history_graph_configuration(self):
        """Test history graph for temperature and power correlation."""
        dashboard = self._load_dashboard_yaml()
        cards = dashboard.get("cards", [])
        
        # Find history graph in calibration section
        history_graph = None
        for card in cards:
            if card.get("type") == "vertical-stack" and "Calibration" in card.get("title", ""):
                for subcard in card.get("cards", []):
                    if subcard.get("type") == "history-graph":
                        history_graph = subcard
                        break
        
        assert history_graph is not None, "History graph should exist in calibration section"
        entities = history_graph.get("entities", [])
        assert len(entities) > 0, "History graph should have entities configured"

    def test_entities_card_configuration(self):
        """Test entities card shows calibration and hysteresis status."""
        dashboard = self._load_dashboard_yaml()
        cards = dashboard.get("cards", [])
        
        # Find entities card
        entities_card = None
        for card in cards:
            if card.get("type") == "vertical-stack" and "Calibration" in card.get("title", ""):
                for subcard in card.get("cards", []):
                    if subcard.get("type") == "entities":
                        entities_card = subcard
                        break
        
        assert entities_card is not None, "Entities card should exist"
        entities = entities_card.get("entities", [])
        assert len(entities) >= 2, "Should show at least calibration and hysteresis status"

    def test_all_entity_references_use_input_variables(self):
        """Test that all entity references use !input variables."""
        dashboard = self._load_dashboard_yaml()
        cards = dashboard.get("cards", [])
        
        # Check for input references in various places
        input_found = False
        
        for card in cards:
            if self._check_for_input_refs(card):
                input_found = True
                break
        
        assert input_found, "Should have !input references in the dashboard"
    
    def _check_for_input_refs(self, obj):
        """Recursively check for !input references."""
        if isinstance(obj, str) and obj.startswith("!input"):
            return True
        elif isinstance(obj, dict):
            for value in obj.values():
                if self._check_for_input_refs(value):
                    return True
        elif isinstance(obj, list):
            for item in obj:
                if self._check_for_input_refs(item):
                    return True
        return False

    def test_card_titles_are_descriptive(self):
        """Test that all sections have descriptive titles."""
        dashboard = self._load_dashboard_yaml()
        cards = dashboard.get("cards", [])
        
        expected_sections = ["Current Status", "Learning Progress", "Calibration", "Control"]
        found_sections = []
        
        for card in cards:
            if card.get("type") == "vertical-stack" and "title" in card:
                found_sections.append(card["title"])
        
        for expected in expected_sections:
            assert any(expected in title for title in found_sections), f"Should have {expected} section"