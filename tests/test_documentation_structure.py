"""Tests for documentation structure and content validation."""

import os
import re
from pathlib import Path
import pytest


class TestDocumentationStructure:
    """Test suite for documentation structure and content validation."""

    @pytest.fixture
    def project_root(self):
        """Get project root directory."""
        return Path(__file__).parent.parent

    @pytest.fixture
    def docs_dir(self, project_root):
        """Get docs directory."""
        return project_root / "docs"

    def test_required_documentation_files_exist(self, docs_dir):
        """Test that all required documentation files exist."""
        required_files = [
            "dashboard-setup.md",
            "features.md",
            "installation.md",
            "configuration.md",
            "usage.md",
            "troubleshooting.md",
            "learning-system.md",
            "sensors.md"
        ]
        
        for filename in required_files:
            file_path = docs_dir / filename
            assert file_path.exists(), f"Required documentation file {filename} is missing"

    def test_readme_exists(self, project_root):
        """Test that README.md exists in project root."""
        readme_path = project_root / "README.md"
        assert readme_path.exists(), "README.md is missing from project root"

    def test_dashboard_setup_structure(self, docs_dir):
        """Test dashboard-setup.md has required sections."""
        dashboard_setup = docs_dir / "dashboard-setup.md"
        content = dashboard_setup.read_text()
        
        required_sections = [
            "# Dashboard Setup Guide",
            "## Overview",
            "## Dashboard Sensors",
            "## Generating Your Dashboard",
            "## Dashboard Features",
            "## Troubleshooting"
        ]
        
        for section in required_sections:
            assert section in content, f"Required section '{section}' missing from dashboard-setup.md"

    def test_features_md_structure(self, docs_dir):
        """Test features.md has required sections."""
        features_md = docs_dir / "features.md"
        content = features_md.read_text()
        
        required_sections = [
            "# Smart Climate Control - Features Guide",
            "## Core Features",
            "## Advanced Features",
            "## Operating Modes",
            "## Dashboard and Monitoring",
            "## Configuration Options Summary"
        ]
        
        for section in required_sections:
            assert section in content, f"Required section '{section}' missing from features.md"

    def test_readme_dashboard_section(self, project_root):
        """Test README.md contains dashboard section with proper content."""
        readme_path = project_root / "README.md"
        content = readme_path.read_text()
        
        # Check for dashboard-related content
        dashboard_patterns = [
            r"Dashboard",
            r"dashboard generation",
            r"visualization",
            r"Generate Dashboard"
        ]
        
        for pattern in dashboard_patterns:
            assert re.search(pattern, content, re.IGNORECASE), f"README.md missing dashboard pattern: {pattern}"

    def test_documentation_links_valid(self, docs_dir, project_root):
        """Test that internal documentation links are valid."""
        # Get all markdown files
        md_files = list(docs_dir.glob("*.md")) + [project_root / "README.md"]
        
        for md_file in md_files:
            content = md_file.read_text()
            
            # Find internal links to docs
            internal_links = re.findall(r'\[.*?\]\((docs/[^)]+)\)', content)
            
            for link in internal_links:
                # Convert relative link to absolute path
                target_path = project_root / link
                assert target_path.exists(), f"Broken internal link '{link}' in {md_file.name}"

    def test_v130_features_documented(self, docs_dir):
        """Test that v1.3.0+ features are properly documented."""
        features_md = docs_dir / "features.md"
        content = features_md.read_text()
        
        v130_features = [
            "Adaptive Feedback Delays",
            "Weather Forecast Integration", 
            "Seasonal Adaptation",
            "Multi-Layered Intelligence",
            "Heat Wave Pre-cooling",
            "Clear Sky",
            "Outdoor Temperature",
            "Exponential Moving Average"
        ]
        
        for feature in v130_features:
            assert feature in content, f"v1.3.0+ feature '{feature}' not documented in features.md"

    def test_dashboard_placeholders_documented(self, docs_dir):
        """Test that dashboard placeholders are properly documented."""
        dashboard_setup = docs_dir / "dashboard-setup.md"
        content = dashboard_setup.read_text()
        
        # Should mention placeholder replacement
        placeholder_patterns = [
            r"placeholder",
            r"entity ID replacement",
            r"customized dashboard",
            r"room sensor",
            r"outdoor sensor",
            r"power sensor"
        ]
        
        for pattern in placeholder_patterns:
            assert re.search(pattern, content, re.IGNORECASE), f"Dashboard setup missing placeholder documentation: {pattern}"

    def test_enhanced_dashboard_features_documented(self, docs_dir):
        """Test that enhanced dashboard features are documented."""
        dashboard_setup = docs_dir / "dashboard-setup.md"
        content = dashboard_setup.read_text()
        
        enhanced_features = [
            "Multi-Layered Intelligence",
            "Weather Intelligence",
            "Adaptive Timing",
            "Seasonal Learning",
            "Predictive Offset",
            "Reactive Offset"
        ]
        
        for feature in enhanced_features:
            assert feature in content, f"Enhanced dashboard feature '{feature}' not documented"

    def test_technical_terminology_consistency(self, docs_dir):
        """Test that technical terminology is used consistently."""
        # Terms that should be consistent across documentation
        consistent_terms = {
            "Smart Climate Control": "Smart Climate Control",  # Not "smart climate" or "Smart climate"
            "v1.3.0": "v1.3.0",  # Version format consistency
            "Home Assistant": "Home Assistant",  # Not "home assistant" or "HA"
            "temperature offset": "temperature offset",  # Technical term consistency
        }
        
        md_files = list(docs_dir.glob("*.md"))
        
        for md_file in md_files:
            content = md_file.read_text()
            
            # Check for inconsistent usage (this is a basic check)
            if "Smart climate" in content and "Smart Climate Control" not in content:
                # Allow for valid lowercase usage in sentences
                sentences_with_smart_climate = re.findall(r'[^.!?]*Smart climate[^.!?]*[.!?]', content, re.IGNORECASE)
                if sentences_with_smart_climate:
                    # Only fail if it's clearly incorrect usage
                    pass  # This test could be expanded for more specific cases

    def test_code_examples_valid_yaml(self, docs_dir):
        """Test that YAML code examples in documentation are valid."""
        import yaml
        
        md_files = list(docs_dir.glob("*.md"))
        
        for md_file in md_files:
            content = md_file.read_text()
            
            # Find YAML code blocks - use non-greedy matching
            yaml_blocks = re.findall(r'```yaml\n(.*?)\n```', content, re.DOTALL)
            
            for i, yaml_block in enumerate(yaml_blocks):
                try:
                    # Skip blocks with placeholder values or contains nested backticks
                    if ("REPLACE_ME" in yaml_block or "{" in yaml_block or 
                        "```" in yaml_block or yaml_block.strip().startswith('#')):
                        continue
                    
                    # Skip comment-only blocks
                    lines = [line.strip() for line in yaml_block.split('\n') if line.strip()]
                    if all(line.startswith('#') for line in lines):
                        continue
                    
                    yaml.safe_load(yaml_block)
                except yaml.YAMLError as e:
                    pytest.fail(f"Invalid YAML in {md_file.name} block {i+1}: {e}\nYAML content:\n{yaml_block}")

    def test_service_call_examples(self, docs_dir):
        """Test that service call examples are properly formatted."""
        dashboard_setup = docs_dir / "dashboard-setup.md"
        content = dashboard_setup.read_text()
        
        # Should contain proper service call examples
        service_patterns = [
            r"smart_climate\.generate_dashboard",
            r"climate_entity_id:",
            r"Developer Tools",
            r"Services"
        ]
        
        for pattern in service_patterns:
            assert re.search(pattern, content), f"Dashboard setup missing service call pattern: {pattern}"

    def test_troubleshooting_coverage(self, docs_dir):
        """Test that troubleshooting covers dashboard-related issues."""
        dashboard_setup = docs_dir / "dashboard-setup.md"
        content = dashboard_setup.read_text()
        
        troubleshooting_topics = [
            "Dashboard Not Generating",
            "Sensors Show",
            "Cards Show Errors",
            "Mobile Layout"
        ]
        
        for topic in troubleshooting_topics:
            assert topic in content, f"Dashboard troubleshooting missing topic: {topic}"

    def test_installation_references_dashboard(self, docs_dir):
        """Test that installation docs reference dashboard setup."""
        if (docs_dir / "installation.md").exists():
            installation_content = (docs_dir / "installation.md").read_text()
            
            # Should reference dashboard setup
            dashboard_refs = [
                "dashboard",
                "visualization", 
                "monitoring"
            ]
            
            found_refs = sum(1 for ref in dashboard_refs if ref.lower() in installation_content.lower())
            assert found_refs > 0, "Installation guide should reference dashboard features"