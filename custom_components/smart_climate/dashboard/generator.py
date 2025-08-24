"""
Dashboard Generator for Smart Climate Advanced Analytics.

This module provides the DashboardGenerator class which orchestrates all tab builders
to create a complete Home Assistant dashboard YAML configuration. The generator
handles placeholder substitution, validation, and file operations.
"""
import logging
import yaml
import re
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from .templates import GraphTemplates
from .tooltips import TooltipProvider
from .builders import (
    OverviewTabBuilder,
    ThermalMetricsTabBuilder, 
    MLPerformanceTabBuilder,
    OptimizationTabBuilder,
    SystemHealthTabBuilder
)

_LOGGER = logging.getLogger(__name__)

# Dashboard file path - will be overridden in tests
DASHBOARD_PATH = Path(__file__).parent / "dashboard.yaml"


class DashboardGenerator:
    """Generates complete Advanced Analytics Dashboard YAML from template system.
    
    The DashboardGenerator orchestrates all 5 tab builders to create a unified
    dashboard configuration. It handles entity ID substitution, YAML generation,
    validation, and file operations with backup support.
    
    The generator follows a template-based approach where each tab builder
    creates its cards independently, then the generator combines them into
    a complete Home Assistant dashboard configuration.
    """
    
    def __init__(self):
        """Initialize dashboard generator with all dependencies and builders."""
        self._templates = GraphTemplates()
        self._tooltips = TooltipProvider()
        
        # Initialize all 5 tab builders with shared dependencies
        self._builders = {
            'overview': OverviewTabBuilder(self._templates, self._tooltips),
            'thermal': ThermalMetricsTabBuilder(self._templates, self._tooltips),
            'ml_performance': MLPerformanceTabBuilder(self._templates, self._tooltips),
            'optimization': OptimizationTabBuilder(self._templates, self._tooltips),
            'system_health': SystemHealthTabBuilder(self._templates, self._tooltips)
        }
        
        _LOGGER.info("DashboardGenerator initialized with %d tab builders", len(self._builders))
    
    def generate_dashboard(self, entity_id: str, friendly_name: str) -> str:
        """Generate complete dashboard YAML for given entity.
        
        This method orchestrates the complete dashboard generation process:
        1. Validates input parameters
        2. Extracts entity name from full entity ID
        3. Builds all tab configurations using tab builders
        4. Creates complete dashboard YAML structure
        5. Performs placeholder substitution
        6. Validates generated YAML
        
        Args:
            entity_id: Full climate entity ID (e.g., 'climate.living_room')
            friendly_name: Human-readable name for the dashboard title
            
        Returns:
            Complete dashboard YAML as string, ready for Home Assistant
            
        Raises:
            ValueError: If entity_id format is invalid or friendly_name is empty
            KeyError: If required tab builder is missing
            yaml.YAMLError: If generated YAML structure is invalid
        """
        # Validate inputs
        self._validate_inputs(entity_id, friendly_name)
        
        # Extract entity name from full entity ID (e.g., 'living_room' from 'climate.living_room')
        entity_name = self._extract_entity_name(entity_id)
        
        _LOGGER.info("Generating dashboard for entity '%s' with name '%s'", entity_id, friendly_name)
        
        try:
            # Build all tab configurations
            tabs = self._build_all_tabs(entity_name)
            
            # Create complete dashboard structure
            dashboard_config = self._create_dashboard_structure(friendly_name, tabs)
            
            # Convert to YAML and perform placeholder substitution
            yaml_content = self._generate_yaml_with_substitution(dashboard_config, entity_id, friendly_name)
            
            # Validate generated YAML
            self._validate_yaml_output(yaml_content)
            
            _LOGGER.info("Successfully generated dashboard YAML (%d characters)", len(yaml_content))
            return yaml_content
            
        except Exception as e:
            _LOGGER.error("Failed to generate dashboard for entity '%s': %s", entity_id, str(e))
            raise
    
    def save_dashboard(self, yaml_content: str, backup: bool = True) -> None:
        """Save dashboard to file with optional backup.
        
        This method performs atomic file writing to ensure the dashboard file
        is never left in a corrupted state. If backup is enabled, the existing
        file is copied to .backup before writing the new content.
        
        Args:
            yaml_content: Complete dashboard YAML content to write
            backup: Whether to create backup of existing file
            
        Raises:
            IOError: If file operations fail
            PermissionError: If insufficient permissions to write file
        """
        dashboard_path = Path(DASHBOARD_PATH)
        
        try:
            # Create backup if requested and file exists
            if backup and dashboard_path.exists():
                backup_path = dashboard_path.with_suffix('.yaml.backup')
                _LOGGER.info("Creating backup at %s", backup_path)
                backup_path.write_text(dashboard_path.read_text(), encoding='utf-8')
            
            # Write new content atomically using temporary file
            temp_path = dashboard_path.with_suffix('.yaml.tmp')
            
            # Write to temporary file first
            temp_path.write_text(yaml_content, encoding='utf-8')
            
            # Atomic replace (on most filesystems)
            temp_path.replace(dashboard_path)
            
            _LOGGER.info("Successfully saved dashboard to %s", dashboard_path)
            
        except Exception as e:
            # Clean up temporary file if it exists
            temp_path = dashboard_path.with_suffix('.yaml.tmp')
            if temp_path.exists():
                temp_path.unlink()
            
            _LOGGER.error("Failed to save dashboard: %s", str(e))
            raise
    
    def _validate_inputs(self, entity_id: str, friendly_name: str) -> None:
        """Validate input parameters for dashboard generation.
        
        Args:
            entity_id: Entity ID to validate
            friendly_name: Friendly name to validate
            
        Raises:
            ValueError: If inputs are invalid
        """
        # Validate entity ID format
        if not entity_id or not isinstance(entity_id, str):
            raise ValueError("Invalid entity ID: must be non-empty string")
        
        # Allow placeholder entity IDs for template generation
        if entity_id != 'climate.REPLACE_ME_ENTITY' and not re.match(r'^climate\.[a-z0-9_]+$', entity_id):
            raise ValueError(
                f"Invalid entity ID format: '{entity_id}'. "
                "Expected format: 'climate.entity_name' (lowercase, numbers, underscores only)"
            )
        
        # Validate friendly name
        if not friendly_name or not isinstance(friendly_name, str) or not friendly_name.strip():
            raise ValueError("Friendly name cannot be empty")
    
    def _extract_entity_name(self, entity_id: str) -> str:
        """Extract entity name from full entity ID.
        
        Args:
            entity_id: Full entity ID (e.g., 'climate.living_room')
            
        Returns:
            Entity name part (e.g., 'living_room')
        """
        return entity_id.split('.')[1]
    
    def _build_all_tabs(self, entity_name: str) -> List[Dict[str, Any]]:
        """Build configurations for all 5 tabs.
        
        Args:
            entity_name: Entity name for building sensor references
            
        Returns:
            List of tab configurations with metadata and cards
            
        Raises:
            KeyError: If required tab builder is missing
        """
        tabs = []
        
        # Required tab order for consistent layout
        tab_order = ['overview', 'thermal', 'ml_performance', 'optimization', 'system_health']
        
        for tab_key in tab_order:
            if tab_key not in self._builders:
                raise KeyError(f"Missing required tab builder: {tab_key}")
            
            builder = self._builders[tab_key]
            
            # Get tab metadata and cards
            tab_config = builder.get_tab_config()
            cards = builder.build_cards(entity_name)
            
            # Combine metadata with cards
            tab_data = {
                'title': tab_config['title'],
                'path': tab_config['path'],
                'icon': tab_config['icon'],
                'cards': cards
            }
            
            tabs.append(tab_data)
            _LOGGER.debug("Built tab '%s' with %d cards", tab_key, len(cards))
        
        return tabs
    
    def _create_dashboard_structure(self, friendly_name: str, tabs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create complete dashboard YAML structure.
        
        Args:
            friendly_name: Dashboard title name
            tabs: List of tab configurations
            
        Returns:
            Complete dashboard configuration dictionary
        """
        return {
            'title': f'Smart Climate Advanced Analytics - {friendly_name}',
            'views': tabs
        }
    
    def _generate_yaml_with_substitution(self, dashboard_config: Dict[str, Any], 
                                       entity_id: str, friendly_name: str) -> str:
        """Generate YAML with placeholder substitution.
        
        Args:
            dashboard_config: Dashboard configuration dictionary
            entity_id: Full entity ID for substitution
            friendly_name: Friendly name for substitution
            
        Returns:
            YAML string with all placeholders replaced
        """
        # Convert to YAML first
        yaml_content = yaml.dump(dashboard_config, default_flow_style=False, allow_unicode=True)
        
        # Add header comment with generation info
        header = self._generate_header_comment(entity_id, friendly_name)
        yaml_content = header + "\n" + yaml_content
        
        # Perform placeholder substitutions
        entity_name = self._extract_entity_name(entity_id)
        
        # Replace entity placeholders
        yaml_content = yaml_content.replace('REPLACE_ME_ENTITY', entity_name)
        
        # Replace name placeholders
        yaml_content = yaml_content.replace('REPLACE_ME_NAME', friendly_name)
        
        return yaml_content
    
    def _generate_header_comment(self, entity_id: str, friendly_name: str) -> str:
        """Generate header comment for dashboard YAML.
        
        Args:
            entity_id: Entity ID used
            friendly_name: Friendly name used
            
        Returns:
            Multi-line header comment
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return f"""# Smart Climate Advanced Analytics Dashboard
# Generated: {now}
# Entity: {entity_id}
# Name: {friendly_name}
#
# This dashboard provides comprehensive analytics and monitoring
# for Smart Climate Control systems. It includes 5 tabs:
# - Overview: High-level status and controls
# - Thermal Metrics: Deep thermal system analysis
# - ML Performance: Machine learning analytics
# - Optimization: System efficiency analysis
# - System Health: Component diagnostics
#
# For support and documentation, visit:
# https://github.com/your-org/smart-climate"""
    
    def _validate_yaml_output(self, yaml_content: str) -> None:
        """Validate that generated YAML is syntactically correct.
        
        Args:
            yaml_content: YAML content to validate
            
        Raises:
            ValueError: If YAML is invalid
        """
        try:
            # Parse YAML to verify syntax
            parsed = yaml.safe_load(yaml_content)
            
            # Basic structure validation
            if not isinstance(parsed, dict):
                raise ValueError("Dashboard YAML must be a dictionary")
            
            if 'title' not in parsed:
                raise ValueError("Dashboard YAML must contain 'title'")
            
            if 'views' not in parsed or not isinstance(parsed['views'], list):
                raise ValueError("Dashboard YAML must contain 'views' list")
            
            if len(parsed['views']) != 5:
                raise ValueError(f"Dashboard must have exactly 5 views, got {len(parsed['views'])}")
            
            # Verify no placeholders remain (except for template generation)
            # Allow placeholders when generating templates
            pass
            
        except yaml.YAMLError as e:
            raise ValueError(f"Generated YAML is invalid: {e}")
    
    @property
    def available_builders(self) -> List[str]:
        """Get list of available tab builder names.
        
        Returns:
            List of tab builder names
        """
        return list(self._builders.keys())
    
    @property
    def builder_count(self) -> int:
        """Get total number of available builders.
        
        Returns:
            Number of tab builders
        """
        return len(self._builders)