"""
ABOUTME: Dashboard constants for Smart Climate Control Advanced Analytics
ABOUTME: Provides colors, sensor mappings, refresh intervals, and card type definitions
"""

from typing import Dict, Any


class DashboardColors:
    """Consistent color scheme across dashboard."""
    
    # Primary colors
    PRIMARY = '#1976D2'
    PRIMARY_LIGHT = '#42A5F5'
    SUCCESS = '#4CAF50'
    WARNING = '#FFA726'
    ERROR = '#EF5350'
    NEUTRAL = '#9E9E9E'
    
    # Series colors for graphs and charts
    SERIES_COLORS = {
        'setpoint': '#1976D2',
        'actual': '#4CAF50',
        'outdoor': '#FFA726',
        'offset': '#9C27B0',
        'prediction': '#00BCD4'
    }


# Sensor entity mappings with placeholders for entity substitution
SENSOR_MAPPINGS: Dict[str, str] = {
    # Offset metrics
    'offset_current': 'sensor.{entity}_offset_current',
    
    # Learning metrics  
    'learning_progress': 'sensor.{entity}_learning_progress',
    'confidence': 'sensor.{entity}_confidence',
    
    # Thermal metrics
    'tau_cooling': 'sensor.{entity}_tau_cooling',
    'tau_warming': 'sensor.{entity}_tau_warming',
    'thermal_state': 'sensor.{entity}_thermal_state',
    
    # Performance metrics
    'accuracy_current': 'sensor.{entity}_accuracy_current',
    'mae': 'sensor.{entity}_mae',
    'rmse': 'sensor.{entity}_rmse',
    
    # System health
    'last_update': 'sensor.{entity}_last_update',
    'error_count': 'sensor.{entity}_error_count',
    'cycle_health': 'sensor.{entity}_cycle_health'
}


# Smart refresh intervals in seconds
REFRESH_INTERVALS: Dict[str, int] = {
    'real_time': 1,      # WebSocket for critical metrics
    'recent': 30,        # 30 seconds for recent trends
    'historical': 300    # 5 minutes for historical data
}


# Card type definitions for dashboard
CARD_TYPES: Dict[str, Dict[str, str]] = {
    # Core Home Assistant cards (no external dependencies)
    'core': {
        'thermostat': 'thermostat',
        'gauge': 'gauge', 
        'entities': 'entities',
        'history_graph': 'history-graph',
        'statistics_graph': 'statistics-graph'
    },
    
    # Custom cards requiring HACS installation
    'custom': {
        'apexcharts': 'custom:apexcharts-card',
        'plotly_graph': 'custom:plotly-graph-card',
        'mini_graph': 'custom:mini-graph-card',
        'button': 'custom:button-card'
    }
}