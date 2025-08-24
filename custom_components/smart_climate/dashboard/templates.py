"""Graph Templates for Advanced Analytics Dashboard.

ABOUTME: Predefined graph configurations for consistent appearance across all dashboard tabs
ABOUTME: Supports both core HA cards and custom cards (via HACS) with override capabilities
"""

import copy
from typing import Dict, Any


class GraphTemplates:
    """Provides predefined graph configurations for dashboard components."""
    
    # LINE_GRAPH template for ApexCharts (custom card)
    LINE_GRAPH = {
        'type': 'custom:apexcharts-card',
        'graph_span': '24h',
        'header': {
            'show': True,
            'title': ''
        },
        'series': [],
        'apex_config': {
            'chart': {
                'height': 250
            },
            'legend': {
                'show': True
            },
            'tooltip': {
                'enabled': True,
                'shared': True
            }
        }
    }
    
    # HEATMAP template for Plotly (custom card)  
    HEATMAP = {
        'type': 'custom:plotly-graph-card',
        'hours_to_show': 168,
        'refresh_interval': 300,
        'layout': {
            'height': 300,
            'showlegend': True,
            'hovermode': 'closest'
        }
    }
    
    # GAUGE template for core HA gauge card
    GAUGE = {
        'type': 'gauge',
        'min': 0,
        'max': 100,
        'needle': True,
        'severity': {
            'green': 80,
            'yellow': 50,
            'red': 0
        }
    }
    
    def get_line_graph(self, **overrides) -> Dict[str, Any]:
        """Get line graph template with optional overrides.
        
        Args:
            **overrides: Key-value pairs to override in the template
            
        Returns:
            Deep copy of LINE_GRAPH template with overrides applied
        """
        result = copy.deepcopy(self.LINE_GRAPH)
        self._apply_overrides(result, overrides)
        return result
    
    def get_heatmap(self, **overrides) -> Dict[str, Any]:
        """Get heatmap template with optional overrides.
        
        Args:
            **overrides: Key-value pairs to override in the template
            
        Returns:
            Deep copy of HEATMAP template with overrides applied
        """
        result = copy.deepcopy(self.HEATMAP)
        self._apply_overrides(result, overrides)
        return result
    
    def get_gauge(self, **overrides) -> Dict[str, Any]:
        """Get gauge template with optional overrides.
        
        Args:
            **overrides: Key-value pairs to override in the template
            
        Returns:
            Deep copy of GAUGE template with overrides applied
        """
        result = copy.deepcopy(self.GAUGE)
        self._apply_overrides(result, overrides)
        return result
    
    def _apply_overrides(self, template: Dict[str, Any], overrides: Dict[str, Any]) -> None:
        """Apply overrides to template using deep merge strategy.
        
        Args:
            template: Template dictionary to modify in-place
            overrides: Override values to apply
        """
        for key, value in overrides.items():
            if isinstance(value, dict) and key in template and isinstance(template[key], dict):
                # Deep merge for nested dictionaries
                self._apply_overrides(template[key], value)
            else:
                # Direct assignment for non-dict values or new keys
                template[key] = value