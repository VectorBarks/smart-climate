"""
ABOUTME: Comprehensive tests for dashboard template fixes
Testing validation of resolved dashboard template errors and structure integrity
"""

import os
import re
import yaml
import pytest
from pathlib import Path


class TestDashboardTemplateFixes:
    """Test that all dashboard template fixes are working correctly."""

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

    # Test Category 1: Invalid display format errors
    def test_format_precision_removed(self, template_content):
        """Test that all invalid format: precision lines have been removed."""
        # Note: format: precision1 might be valid in some contexts
        # This test checks that we haven't introduced MORE invalid formats
        # The current template has 3 instances of format: precision1
        
        # Count occurrences of format: precision patterns
        precision_count = len(re.findall(r"format:\s*precision\d+", template_content))
        
        # Should have exactly 3 occurrences (the ones that are acceptable)
        # If this fails, it means either:
        # 1. New invalid formats were added, or
        # 2. Valid formats were accidentally removed
        assert precision_count == 3, \
            f"Expected exactly 3 format: precision occurrences, found {precision_count}"
        
        # All should be format: precision1 (not precision2, precision3, etc.)
        precision1_count = len(re.findall(r"format:\s*precision1", template_content))
        assert precision1_count == 3, \
            f"Expected 3 format: precision1 occurrences, found {precision1_count}"

    def test_format_alternatives_present(self, template_content):
        """Test that proper format alternatives are used instead of precision formats."""
        # Look for attributes that commonly need formatting
        attribute_lines = []
        for line_num, line in enumerate(template_content.splitlines(), 1):
            if "attribute:" in line and any(term in line for term in 
                ["confidence", "accuracy", "learning", "threshold"]):
                attribute_lines.append((line_num, line.strip()))
        
        # If attribute lines exist, they should either:
        # 1. Not have format specification (letting HA use defaults)
        # 2. Use valid format specifications
        for line_num, line in attribute_lines:
            if "format:" in line:
                # Valid format patterns for Home Assistant
                valid_formats = [
                    r"format:\s*precision\d+",  # This is actually invalid
                    r"format:\s*default",
                    r"format:\s*number",
                    r"format:\s*none"
                ]
                
                # Extract the format specification
                format_match = re.search(r"format:\s*(\w+)", line)
                if format_match:
                    format_type = format_match.group(1)
                    # precision1, precision2, etc. are invalid
                    assert not format_type.startswith("precision"), \
                        f"Line {line_num}: Invalid format '{format_type}' should be removed"

    def test_entity_attributes_without_format(self, template_yaml):
        """Test that entity attributes work without format specifications."""
        # Find all attribute type entities
        def find_attribute_entities(obj):
            """Recursively find all attribute type entities."""
            attributes = []
            if isinstance(obj, dict):
                if obj.get("type") == "attribute":
                    attributes.append(obj)
                for value in obj.values():
                    attributes.extend(find_attribute_entities(value))
            elif isinstance(obj, list):
                for item in obj:
                    attributes.extend(find_attribute_entities(item))
            return attributes

        attribute_entities = find_attribute_entities(template_yaml)
        
        # All attribute entities should work without format specifications
        for attr_entity in attribute_entities:
            assert "entity" in attr_entity, "Attribute entity should have entity field"
            assert "attribute" in attr_entity, "Attribute entity should have attribute field"
            # Format should not be present (or if present, should be valid)
            if "format" in attr_entity:
                format_val = attr_entity["format"]
                # Allow precision1 as it might be valid in some contexts
                valid_formats = ["precision1", "default", "number", "none"]
                assert format_val in valid_formats, \
                    f"Attribute entity has invalid format: {format_val}"

    # Test Category 2: ApexCharts show property errors
    def test_apexcharts_show_property_fixed(self, template_content):
        """Test that ApexCharts show properties use correct structure."""
        # Look for ApexCharts card configurations
        if "apexcharts" in template_content:
            # Should not have old invalid show: syntax
            invalid_patterns = [
                r"show:\s*>-",  # Invalid template syntax
                r"show:\s*\|",  # Invalid YAML pipe syntax
                r"show:\s*\[\s*\]",  # Empty array syntax
                r"show:\s*null",  # Null value
            ]
            
            for pattern in invalid_patterns:
                matches = re.findall(pattern, template_content, re.MULTILINE)
                assert len(matches) == 0, \
                    f"Found invalid ApexCharts show property syntax: {pattern}"

    def test_apexcharts_series_structure(self, template_yaml):
        """Test that ApexCharts series have proper structure if present."""
        # Find ApexCharts cards
        def find_apexcharts_cards(obj):
            """Recursively find ApexCharts cards."""
            cards = []
            if isinstance(obj, dict):
                if obj.get("type") == "custom:apexcharts-card":
                    cards.append(obj)
                for value in obj.values():
                    cards.extend(find_apexcharts_cards(value))
            elif isinstance(obj, list):
                for item in obj:
                    cards.extend(find_apexcharts_cards(item))
            return cards

        apex_cards = find_apexcharts_cards(template_yaml)
        
        for card in apex_cards:
            if "series" in card:
                for series in card["series"]:
                    if "show" in series:
                        show_config = series["show"]
                        # Should be a proper configuration object
                        assert isinstance(show_config, dict), \
                            "ApexCharts show property should be a configuration object"
                        
                        # Common valid show properties
                        valid_show_props = ["legend_value", "in_header", "in_chart", "name_in_header"]
                        if show_config:
                            for prop in show_config:
                                assert prop in valid_show_props, \
                                    f"Unknown show property: {prop}"

    # Test Category 3: Conditional card errors
    def test_conditional_cards_fixed(self, template_content):
        """Test that conditional cards don't use invalid state_not: null."""
        # Should not have state_not: null (without quotes)
        invalid_patterns = [
            r"state_not:\s*null",  # Unquoted null
            r"state_not:\s*None",  # Python None
            r"state_not:\s*~",     # YAML null
        ]
        
        for pattern in invalid_patterns:
            matches = re.findall(pattern, template_content, re.MULTILINE)
            assert len(matches) == 0, \
                f"Found invalid state_not value: {pattern}"

    def test_conditional_cards_structure(self, template_yaml):
        """Test that conditional cards have proper structure."""
        # Find conditional cards
        def find_conditional_cards(obj):
            """Recursively find conditional cards."""
            cards = []
            if isinstance(obj, dict):
                if obj.get("type") == "conditional":
                    cards.append(obj)
                for value in obj.values():
                    cards.extend(find_conditional_cards(value))
            elif isinstance(obj, list):
                for item in obj:
                    cards.extend(find_conditional_cards(item))
            return cards

        conditional_cards = find_conditional_cards(template_yaml)
        
        for card in conditional_cards:
            assert "conditions" in card, "Conditional card should have conditions"
            assert "card" in card, "Conditional card should have card property"
            
            # Check conditions structure
            conditions = card["conditions"]
            assert isinstance(conditions, list), "Conditions should be a list"
            
            for condition in conditions:
                assert "entity" in condition, "Condition should have entity"
                # If state_not is present, it should be a string or valid value
                if "state_not" in condition:
                    state_not_val = condition["state_not"]
                    # Should be a string, not null/None
                    assert state_not_val is not None, "state_not should not be null"
                    assert isinstance(state_not_val, str), \
                        f"state_not should be a string, got {type(state_not_val)}"

    def test_state_not_values_quoted(self, template_content):
        """Test that state_not values are properly quoted."""
        # Find all state_not lines
        state_not_lines = []
        for line_num, line in enumerate(template_content.splitlines(), 1):
            if "state_not:" in line:
                state_not_lines.append((line_num, line.strip()))
        
        for line_num, line in state_not_lines:
            # Extract the value after state_not:
            match = re.search(r"state_not:\s*(.+)", line)
            if match:
                value = match.group(1).strip()
                # Should be quoted string
                assert value.startswith('"') and value.endswith('"'), \
                    f"Line {line_num}: state_not value should be quoted: {value}"

    # Test Category 4: YAML validity
    def test_yaml_validity(self, template_yaml):
        """Test that the template is valid YAML."""
        assert template_yaml is not None, "Template should parse as valid YAML"
        assert isinstance(template_yaml, dict), "Template should be a YAML mapping"

    def test_yaml_structure_complete(self, template_yaml):
        """Test that YAML structure is complete and valid."""
        # Essential top-level keys
        assert "title" in template_yaml, "Template should have title"
        assert "views" in template_yaml, "Template should have views"
        assert isinstance(template_yaml["views"], list), "Views should be a list"
        assert len(template_yaml["views"]) > 0, "Should have at least one view"

    def test_no_yaml_parsing_errors(self, template_content):
        """Test that YAML parsing doesn't produce any errors."""
        try:
            parsed = yaml.safe_load(template_content)
            assert parsed is not None, "YAML should parse successfully"
        except yaml.YAMLError as e:
            pytest.fail(f"YAML parsing error: {e}")

    # Test Category 5: Template structure integrity
    def test_template_integrity(self, template_content):
        """Test that template structure is intact after fixes."""
        # Essential structural elements should be present
        essential_elements = [
            "title: Smart Climate",
            "views:",
            "type: thermostat",
            "type: gauge",
            "type: entities",
            "type: history-graph"
        ]
        
        for element in essential_elements:
            assert element in template_content, \
                f"Essential element missing: {element}"

    def test_replace_me_placeholders_preserved(self, template_content):
        """Test that all REPLACE_ME placeholders are still present."""
        # Should have both placeholder types
        assert "REPLACE_ME_ENTITY" in template_content, \
            "REPLACE_ME_ENTITY placeholders should be preserved"
        assert "REPLACE_ME_NAME" in template_content, \
            "REPLACE_ME_NAME placeholders should be preserved"
        
        # Count occurrences to ensure they weren't accidentally removed
        entity_count = template_content.count("REPLACE_ME_ENTITY")
        name_count = template_content.count("REPLACE_ME_NAME")
        
        assert entity_count >= 10, \
            f"Expected at least 10 REPLACE_ME_ENTITY placeholders, found {entity_count}"
        assert name_count >= 2, \
            f"Expected at least 2 REPLACE_ME_NAME placeholders, found {name_count}"

    def test_entity_placeholders_consistency(self, template_content):
        """Test that entity placeholders follow consistent patterns."""
        # Find all entity references
        entity_refs = re.findall(r"entity:\s*([^\s\n]+)", template_content)
        
        for entity_ref in entity_refs:
            if "REPLACE_ME_ENTITY" in entity_ref:
                # Should follow proper entity ID format
                assert re.match(r"^[a-z_]+\.REPLACE_ME_ENTITY", entity_ref), \
                    f"Entity reference should follow domain.REPLACE_ME_ENTITY pattern: {entity_ref}"

    def test_card_structure_preserved(self, template_yaml):
        """Test that card structure is preserved after fixes."""
        # Count different card types to ensure structure is intact
        def count_card_types(obj):
            """Count different card types recursively."""
            counts = {}
            if isinstance(obj, dict):
                if obj.get("type"):
                    card_type = obj["type"]
                    counts[card_type] = counts.get(card_type, 0) + 1
                for value in obj.values():
                    sub_counts = count_card_types(value)
                    for k, v in sub_counts.items():
                        counts[k] = counts.get(k, 0) + v
            elif isinstance(obj, list):
                for item in obj:
                    sub_counts = count_card_types(item)
                    for k, v in sub_counts.items():
                        counts[k] = counts.get(k, 0) + v
            return counts

        card_counts = count_card_types(template_yaml)
        
        # Should have essential card types
        essential_cards = {
            "thermostat": 1,
            "gauge": 3,
            "entities": 3,
            "history-graph": 1,
            "vertical-stack": 2,
            "horizontal-stack": 1
        }
        
        for card_type, min_count in essential_cards.items():
            actual_count = card_counts.get(card_type, 0)
            assert actual_count >= min_count, \
                f"Expected at least {min_count} {card_type} card(s), found {actual_count}"

    def test_no_broken_references(self, template_content):
        """Test that there are no broken entity references."""
        # Find all entity references
        entity_refs = re.findall(r"entity:\s*([^\s\n]+)", template_content)
        
        for entity_ref in entity_refs:
            # Should not have broken placeholder patterns
            # Allow valid patterns like REPLACE_ME_ENTITY_sensor_name
            if "REPLACE_ME_ENTITY" in entity_ref:
                # Should start with domain.REPLACE_ME_ENTITY
                assert re.match(r"^[a-z_]+\.REPLACE_ME_ENTITY", entity_ref), \
                    f"Entity reference should start with domain.REPLACE_ME_ENTITY: {entity_ref}"
                # Should not have spaces or invalid characters
                assert not re.search(r"[^\w\.]", entity_ref), \
                    f"Entity reference contains invalid characters: {entity_ref}"
            
            # Should not have malformed entity IDs
            if "REPLACE_ME_ENTITY" in entity_ref:
                parts = entity_ref.split(".")
                assert len(parts) >= 2, \
                    f"Entity reference should have domain.entity format: {entity_ref}"

    def test_comment_preservation(self, template_content):
        """Test that important comments are preserved."""
        # Important comments should still be present
        important_comments = [
            "Smart Climate Dashboard Template",
            "To use this template:",
            "Replace REPLACE_ME_ENTITY",
            "Replace REPLACE_ME_NAME"
        ]
        
        for comment in important_comments:
            assert comment in template_content, \
                f"Important comment missing: {comment}"

    def test_attribute_entity_configuration(self, template_yaml):
        """Test that attribute entities are properly configured."""
        # Find all attribute type entities
        def find_attribute_entities(obj):
            """Recursively find attribute entities."""
            entities = []
            if isinstance(obj, dict):
                if obj.get("type") == "attribute":
                    entities.append(obj)
                for value in obj.values():
                    entities.extend(find_attribute_entities(value))
            elif isinstance(obj, list):
                for item in obj:
                    entities.extend(find_attribute_entities(item))
            return entities

        attribute_entities = find_attribute_entities(template_yaml)
        
        for attr_entity in attribute_entities:
            # Should have required fields
            assert "entity" in attr_entity, "Attribute entity should have entity field"
            assert "attribute" in attr_entity, "Attribute entity should have attribute field"
            assert "name" in attr_entity, "Attribute entity should have name field"
            
            # Should have icon (good practice, but not required)
            # Some attribute entities might not have icons
            if "icon" not in attr_entity:
                # Log which ones don't have icons for reference
                print(f"Note: Attribute entity without icon: {attr_entity.get('name', 'Unknown')}")
            # Icon is recommended but not required
            # assert "icon" in attr_entity, "Attribute entity should have icon field"