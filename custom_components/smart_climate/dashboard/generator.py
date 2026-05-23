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
from typing import Dict, Any, List, Optional
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

    def generate_runtime_dashboard(
        self,
        entity_id: str,
        friendly_name: str,
        related_entities: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Generate a resilient HA-core-only dashboard from live entity data.

        The legacy Advanced Analytics template guesses entity IDs from the climate
        entity name. Real installs can have different helper prefixes, so the
        runtime dashboard only references entities reported by Home Assistant.
        """
        self._validate_inputs(entity_id, friendly_name)
        related_entities = related_entities or []
        dashboard_config = {
            "title": f"Smart Climate - {friendly_name}",
            "views": self._build_runtime_views(entity_id, related_entities),
        }
        yaml_content = self._generate_header_comment(entity_id, friendly_name)
        yaml_content += "\n" + yaml.dump(
            dashboard_config,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        self._validate_runtime_yaml_output(yaml_content)
        return yaml_content
    
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
    
    def _build_runtime_views(self, climate_entity_id: str, related_entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build five robust dashboard tabs using only existing core HA entities/cards."""
        climate_card = {"type": "thermostat", "entity": climate_entity_id, "name": "Smart Climate Control"}
        numeric_entities = [
            entity for entity in related_entities
            if entity.get("domain") == "sensor" and self._is_numeric_state(entity.get("state"))
        ]
        overview_entities = self._select_entities(
            related_entities,
            ["current_offset", "learning_progress", "current_accuracy", "compressor_state", "temperature_window", "weather_forecast", "convergence_trend", "quiet_mode"],
            limit=14,
        )
        learning_entities = self._select_entities(
            related_entities,
            ["learning", "calibration", "hysteresis", "adaptive_delay", "sample", "window", "seasonal", "forecast"],
            limit=24,
        )
        thermal_entities = self._select_entities(
            related_entities,
            ["thermal", "cycle", "tau", "compressor", "quiet", "comfort", "operating_window"],
            limit=24,
        )
        performance_entities = self._select_entities(
            related_entities,
            ["accuracy", "offset", "model", "prediction", "correlation", "efficiency", "error", "latency", "mae", "mse", "r_squared"],
            limit=28,
        )
        diagnostic_entities = self._dedupe_entities(related_entities)[:40]
        history_entities = [entity["entity_id"] for entity in numeric_entities[:8]]

        return [
            {
                "title": "Overview",
                "path": "overview",
                "icon": "mdi:view-dashboard",
                "cards": [
                    climate_card,
                    self._build_markdown_status_card(climate_entity_id),
                    *self._build_gauge_cards(numeric_entities),
                    self._build_entities_card("Live Status", overview_entities),
                ],
            },
            {
                "title": "Learning",
                "path": "learning",
                "icon": "mdi:brain",
                "cards": [self._build_entities_card("Learning & Forecast", learning_entities)],
            },
            {
                "title": "Thermal",
                "path": "thermal",
                "icon": "mdi:thermometer-lines",
                "cards": [self._build_entities_card("Thermal & Quiet Mode", thermal_entities)],
            },
            {
                "title": "Performance",
                "path": "performance",
                "icon": "mdi:chart-line",
                "cards": [
                    self._build_history_card("Numeric Trends", history_entities),
                    self._build_entities_card("Performance Metrics", performance_entities),
                ],
            },
            {
                "title": "Diagnostics",
                "path": "diagnostics",
                "icon": "mdi:stethoscope",
                "cards": [
                    self._build_entities_card("All Smart Climate Entities", diagnostic_entities),
                    self._build_markdown_reference_card(climate_entity_id),
                ],
            },
        ]

    @staticmethod
    def _is_numeric_state(state: Any) -> bool:
        """Return true when a HA state can safely feed gauge/history cards."""
        try:
            float(state)
            return True
        except (TypeError, ValueError):
            return False

    def _select_entities(self, entities: List[Dict[str, Any]], keywords: List[str], limit: int) -> List[Dict[str, Any]]:
        """Select related entities matching any keyword in entity id or friendly name."""
        selected = []
        for entity in self._dedupe_entities(entities):
            haystack = f"{entity.get('entity_id', '')} {entity.get('friendly_name', '')}".lower()
            if any(keyword in haystack for keyword in keywords):
                selected.append(entity)
            if len(selected) >= limit:
                break
        return selected

    @staticmethod
    def _dedupe_entities(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Return entities sorted and deduplicated by entity_id."""
        seen = set()
        result = []
        for entity in sorted(entities, key=lambda item: item.get("entity_id", "")):
            entity_id = entity.get("entity_id")
            if not entity_id or entity_id in seen:
                continue
            seen.add(entity_id)
            result.append(entity)
        return result

    def _build_gauge_cards(self, numeric_entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build safe gauge cards only for known numeric entities."""
        preferred = [
            "current_offset",
            "learning_progress",
            "current_accuracy",
            "model_confidence",
            "energy_efficiency_score",
            "sensor_availability",
        ]
        cards = []
        used = set()
        for keyword in preferred:
            match = next((entity for entity in numeric_entities if keyword in entity.get("entity_id", "")), None)
            if not match or match["entity_id"] in used:
                continue
            used.add(match["entity_id"])
            min_value, max_value = self._gauge_range(match["entity_id"])
            cards.append({
                "type": "gauge",
                "entity": match["entity_id"],
                "name": self._display_name(match),
                "min": min_value,
                "max": max_value,
                "needle": True,
            })
            if len(cards) >= 4:
                break
        return cards

    @staticmethod
    def _gauge_range(entity_id: str) -> tuple[float, float]:
        """Return sensible gauge min/max values for common dashboard metrics."""
        if "offset" in entity_id:
            return -5, 5
        if any(part in entity_id for part in ("progress", "accuracy", "confidence", "efficiency", "availability")):
            return 0, 100
        return 0, 10

    @staticmethod
    def _display_name(entity: Dict[str, Any]) -> str:
        """Return a compact display name for an entity."""
        return entity.get("friendly_name") or entity.get("entity_id", "")

    def _build_entities_card(self, title: str, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build a core entities card."""
        return {
            "type": "entities",
            "title": title,
            "show_header_toggle": False,
            "entities": [entity["entity_id"] for entity in self._dedupe_entities(entities)],
        }

    @staticmethod
    def _build_history_card(title: str, entity_ids: List[str]) -> Dict[str, Any]:
        """Build a core history graph card."""
        return {
            "type": "history-graph",
            "title": title,
            "hours_to_show": 24,
            "entities": entity_ids,
        }

    @staticmethod
    def _build_markdown_status_card(climate_entity_id: str) -> Dict[str, Any]:
        """Build a templated status card for the main climate entity."""
        return {
            "type": "markdown",
            "title": "Status Details",
            "content": (
                f"### {{{{ state_attr('{climate_entity_id}', 'friendly_name') or '{climate_entity_id}' }}}}\n"
                f"- HVAC: `{{{{ states('{climate_entity_id}') }}}}`\n"
                f"- Predictive strategy: `{{{{ state_attr('{climate_entity_id}', 'predictive_strategy') }}}}`\n"
                f"- Strategy detail: {{{{ state_attr('{climate_entity_id}', 'predictive_strategy_status_detail') }}}}\n"
                f"- Temperature window: `{{{{ state_attr('{climate_entity_id}', 'temperature_window_learned') }}}}`\n"
                f"- Window detail: {{{{ state_attr('{climate_entity_id}', 'temperature_window_status_detail') }}}}\n"
            ),
        }

    @staticmethod
    def _build_markdown_reference_card(climate_entity_id: str) -> Dict[str, Any]:
        """Build a small reference card explaining dashboard design."""
        return {
            "type": "markdown",
            "title": "Dashboard Notes",
            "content": (
                "This dashboard is generated from the live Home Assistant entity registry. "
                "It intentionally uses only built-in Home Assistant cards and only references "
                f"entities that exist for `{climate_entity_id}`."
            ),
        }

    def _validate_runtime_yaml_output(self, yaml_content: str) -> None:
        """Validate runtime dashboard structure."""
        parsed = yaml.safe_load(yaml_content)
        if not isinstance(parsed, dict):
            raise ValueError("Dashboard YAML must be a dictionary")
        if "views" not in parsed or not isinstance(parsed["views"], list):
            raise ValueError("Dashboard YAML must contain a views list")
        if len(parsed["views"]) != 5:
            raise ValueError(f"Runtime dashboard must have exactly 5 views, got {len(parsed['views'])}")

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