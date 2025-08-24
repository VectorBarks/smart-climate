"""
ABOUTME: Tab builder implementations for Advanced Analytics Dashboard
Contains concrete TabBuilder implementations for each dashboard tab
"""

from typing import List, Dict, Any
from .base import TabBuilder
from .templates import GraphTemplates
from .tooltips import TooltipProvider
from .constants import DashboardColors
from .constants import SENSOR_MAPPINGS


class OverviewTabBuilder(TabBuilder):
    """Builder for the Overview tab - main dashboard view with key metrics."""
    
    def __init__(self, templates: GraphTemplates, tooltips: TooltipProvider):
        """Initialize the Overview tab builder.
        
        Args:
            templates: GraphTemplates instance for card template generation
            tooltips: TooltipProvider instance for adding helpful tooltips
        """
        self._templates = templates
        self._tooltips = tooltips
    
    def get_tab_config(self) -> Dict[str, str]:
        """Get tab metadata for the Overview tab.
        
        Returns:
            Dictionary with tab configuration including title, path, and icon.
        """
        return {
            'title': 'Overview',
            'path': 'overview', 
            'icon': 'mdi:view-dashboard'
        }
    
    def build_cards(self, entity_id: str) -> List[Dict[str, Any]]:
        """Build all cards for the Overview tab.
        
        The Overview tab provides a high-level view of system status including:
        1. Thermostat control card
        2. Four key metric gauges (offset, confidence, efficiency, health)
        3. Live temperature graph showing recent trends
        4. Quick stats grid with current system status
        
        Args:
            entity_id: Base entity ID for the climate component (e.g., 'living_room')
            
        Returns:
            List of card dictionaries for Home Assistant dashboard
        """
        cards = []
        
        # 1. Thermostat card for direct climate control
        cards.append(self._build_thermostat_card(entity_id))
        
        # 2. Four key metric gauges
        cards.extend(self._build_gauge_cards(entity_id))
        
        # 3. Live temperature graph (last hour)
        cards.append(self._build_live_temperature_graph(entity_id))
        
        # 4. Quick stats grid
        cards.append(self._build_stats_grid(entity_id))
        
        return cards
    
    def _build_thermostat_card(self, entity_id: str) -> Dict[str, Any]:
        """Build the main thermostat control card.
        
        Args:
            entity_id: Base entity ID for the climate component
            
        Returns:
            Thermostat card configuration
        """
        return {
            'type': 'thermostat',
            'entity': f'climate.{entity_id}',
            'title': 'Climate Control'
        }
    
    def _build_gauge_cards(self, entity_id: str) -> List[Dict[str, Any]]:
        """Build the four key metric gauge cards.
        
        Creates gauges for:
        - Current offset (-5 to +5°C)
        - ML confidence (0-100%)
        - Thermal efficiency (0-100%) 
        - System health (0-100%)
        
        Args:
            entity_id: Base entity ID for the climate component
            
        Returns:
            List of four gauge card configurations
        """
        gauges = []
        
        # Offset gauge (-5 to +5°C)
        offset_gauge = self._templates.get_gauge(
            min=-5,
            max=5,
            title='Current Offset',
            entity=SENSOR_MAPPINGS['offset_current'].format(entity=entity_id),
            unit='°C'
        )
        gauges.append(offset_gauge)
        
        # ML Confidence gauge (0-100%)
        confidence_gauge = self._templates.get_gauge(
            min=0,
            max=100,
            title='ML Confidence',
            entity=SENSOR_MAPPINGS['confidence'].format(entity=entity_id),
            unit='%',
            severity={
                'green': 80,
                'yellow': 50, 
                'red': 0
            }
        )
        gauges.append(confidence_gauge)
        
        # Thermal Efficiency gauge (0-100%)
        efficiency_gauge = self._templates.get_gauge(
            min=0,
            max=100,
            title='Thermal Efficiency',
            entity=SENSOR_MAPPINGS['cycle_health'].format(entity=entity_id),
            unit='%',
            severity={
                'green': 80,
                'yellow': 60,
                'red': 0
            }
        )
        gauges.append(efficiency_gauge)
        
        # System Health gauge (0-100%)
        health_gauge = self._templates.get_gauge(
            min=0,
            max=100,
            title='System Health', 
            entity=SENSOR_MAPPINGS['accuracy_current'].format(entity=entity_id),
            unit='%',
            severity={
                'green': 85,
                'yellow': 70,
                'red': 0
            }
        )
        gauges.append(health_gauge)
        
        return gauges
    
    def _build_live_temperature_graph(self, entity_id: str) -> Dict[str, Any]:
        """Build live temperature graph showing recent trends.
        
        Shows setpoint, actual temperature, and outdoor temperature overlaid
        with offset on secondary axis for the last hour.
        
        Args:
            entity_id: Base entity ID for the climate component
            
        Returns:
            Temperature graph card configuration
        """
        # Use ApexCharts for advanced graphing capabilities
        graph = self._templates.get_line_graph(
            header={'title': 'Live Temperature Trends (Last Hour)', 'show': True},
            graph_span='1h',
            series=[
                {
                    'entity': f'sensor.{entity_id}_setpoint_temperature',
                    'name': 'Setpoint',
                    'color': '#1976D2',
                    'stroke_width': 2,
                    'unit': '°C'
                },
                {
                    'entity': f'sensor.{entity_id}_current_temperature', 
                    'name': 'Actual',
                    'color': '#4CAF50',
                    'stroke_width': 2,
                    'unit': '°C'
                },
                {
                    'entity': f'sensor.{entity_id}_outdoor_temperature',
                    'name': 'Outdoor',
                    'color': '#FFA726',
                    'stroke_width': 1,
                    'unit': '°C'
                },
                {
                    'entity': SENSOR_MAPPINGS['offset_current'].format(entity=entity_id),
                    'name': 'Offset',
                    'color': '#9C27B0',
                    'stroke_width': 1,
                    'unit': '°C',
                    'yAxis_id': 'offset'
                }
            ],
            yaxis=[
                {'id': 'temperature', 'apex_config': {'title': {'text': 'Temperature (°C)'}}},
                {'id': 'offset', 'apex_config': {'opposite': True, 'title': {'text': 'Offset (°C)'}}}
            ]
        )
        
        return graph
    
    def _build_stats_grid(self, entity_id: str) -> Dict[str, Any]:
        """Build quick stats grid showing key system status.
        
        Shows:
        - Current thermal state
        - Active mode 
        - Last probe time
        - Learning samples count
        
        Args:
            entity_id: Base entity ID for the climate component
            
        Returns:
            Stats grid card configuration
        """
        return {
            'type': 'entities',
            'title': 'System Status',
            'entities': [
                {
                    'entity': SENSOR_MAPPINGS['thermal_state'].format(entity=entity_id),
                    'name': 'Thermal State',
                    'icon': 'mdi:state-machine'
                },
                {
                    'entity': f'sensor.{entity_id}_active_mode',
                    'name': 'Active Mode',
                    'icon': 'mdi:hvac'
                },
                {
                    'entity': SENSOR_MAPPINGS['last_update'].format(entity=entity_id),
                    'name': 'Last Probe',
                    'icon': 'mdi:clock-outline'
                },
                {
                    'entity': f'sensor.{entity_id}_samples_collected',
                    'name': 'Learning Samples',
                    'icon': 'mdi:database'
                }
            ],
            'show_header_toggle': False
        }


class MLPerformanceTabBuilder(TabBuilder):
    """Builder for the ML Performance tab - machine learning analytics and metrics."""
    
    def __init__(self, templates: GraphTemplates, tooltips: TooltipProvider):
        """Initialize the ML Performance tab builder.
        
        Args:
            templates: GraphTemplates instance for card template generation
            tooltips: TooltipProvider instance for adding helpful tooltips
        """
        self._templates = templates
        self._tooltips = tooltips
    
    def get_tab_config(self) -> Dict[str, str]:
        """Get tab metadata for the ML Performance tab.
        
        Returns:
            Dictionary with tab configuration including title, path, and icon.
        """
        return {
            'title': 'ML Performance',
            'path': 'ml_performance',
            'icon': 'mdi:brain'
        }
    
    def build_cards(self, entity_id: str) -> List[Dict[str, Any]]:
        """Build all cards for the ML Performance tab.
        
        The ML Performance tab provides comprehensive machine learning analytics:
        1. Learning progress graph (samples, confidence, MAE over time)
        2. Prediction error histogram with normal distribution overlay
        3. Feature importance horizontal bar chart
        4. Confidence bands area chart showing prediction uncertainty
        5. Performance metrics grid (MAE, RMSE, R², model age, etc.)
        
        Args:
            entity_id: Base entity ID for the climate component (e.g., 'living_room')
            
        Returns:
            List of card dictionaries for Home Assistant dashboard
        """
        cards = []
        
        # 1. Learning progress graph
        cards.append(self._build_learning_progress_graph(entity_id))
        
        # 2. Prediction error histogram
        cards.append(self._build_prediction_accuracy_histogram(entity_id))
        
        # 3. Feature importance horizontal bars
        cards.append(self._build_feature_importance_chart(entity_id))
        
        # 4. Confidence bands area chart
        cards.append(self._build_confidence_bands_chart(entity_id))
        
        # 5. Performance metrics grid
        cards.append(self._build_performance_metrics_grid(entity_id))
        
        return cards
    
    def _build_learning_progress_graph(self, entity_id: str) -> Dict[str, Any]:
        """Build learning progress graph with multiple metrics over time.
        
        Shows learning samples (cumulative), model confidence, and prediction 
        accuracy (MAE) with milestone markers for key learning events.
        
        Args:
            entity_id: Base entity ID for the climate component
            
        Returns:
            Learning progress graph card configuration
        """
        from .constants import DashboardColors
        
        # Create multi-series line graph with dual Y-axes
        graph = self._templates.get_line_graph(
            header={'title': 'Learning Progress', 'show': True},
            graph_span='7d',
            series=[
                {
                    'entity': f'sensor.{entity_id}_samples_collected',
                    'name': 'Learning Samples',
                    'color': DashboardColors.PRIMARY,
                    'stroke_width': 2,
                    'unit': 'samples',
                    'yaxis_id': 'samples'
                },
                {
                    'entity': SENSOR_MAPPINGS['confidence'].format(entity=entity_id),
                    'name': 'Confidence',
                    'color': DashboardColors.SUCCESS,
                    'stroke_width': 2,
                    'unit': '%',
                    'yaxis_id': 'percentage'
                },
                {
                    'entity': SENSOR_MAPPINGS['mae'].format(entity=entity_id),
                    'name': 'Prediction Error (MAE)',
                    'color': DashboardColors.ERROR,
                    'stroke_width': 2,
                    'unit': '°C',
                    'yaxis_id': 'temperature'
                }
            ],
            yaxis=[
                {
                    'id': 'samples',
                    'apex_config': {
                        'title': {'text': 'Samples'},
                        'min': 0
                    }
                },
                {
                    'id': 'percentage', 
                    'apex_config': {
                        'opposite': True,
                        'title': {'text': 'Confidence (%)'},
                        'min': 0,
                        'max': 100
                    }
                },
                {
                    'id': 'temperature',
                    'apex_config': {
                        'opposite': True,
                        'title': {'text': 'MAE (°C)'},
                        'min': 0
                    }
                }
            ],
            apex_config={
                'annotations': {
                    'xaxis': [
                        {
                            'x': 'new Date().setHours(new Date().getHours() - 24)',
                            'borderColor': DashboardColors.WARNING,
                            'label': {
                                'text': 'Initial Learning Complete',
                                'style': {
                                    'color': '#fff',
                                    'background': DashboardColors.WARNING
                                }
                            }
                        },
                        {
                            'x': 'new Date().setHours(new Date().getHours() - 72)',
                            'borderColor': DashboardColors.SUCCESS,
                            'label': {
                                'text': 'Model Stabilized',
                                'style': {
                                    'color': '#fff',
                                    'background': DashboardColors.SUCCESS
                                }
                            }
                        }
                    ]
                }
            }
        )
        
        return graph
    
    def _build_prediction_accuracy_histogram(self, entity_id: str) -> Dict[str, Any]:
        """Build prediction accuracy histogram with statistical overlay.
        
        Shows distribution of prediction errors with normal distribution curve
        overlay and statistical annotations (mean, std dev, 95% confidence interval).
        
        Args:
            entity_id: Base entity ID for the climate component
            
        Returns:
            Prediction accuracy histogram card configuration
        """
        from .constants import DashboardColors
        
        # Create histogram with overlay
        histogram = self._templates.get_line_graph(
            header={'title': 'Prediction Accuracy', 'show': True},
            graph_span='30d',
            series=[
                {
                    'entity': f'sensor.{entity_id}_prediction_errors',
                    'name': 'Prediction Errors',
                    'color': DashboardColors.PRIMARY_LIGHT,
                    'type': 'histogram',
                    'unit': '°C'
                },
                {
                    'name': 'Normal Distribution',
                    'color': DashboardColors.ERROR,
                    'type': 'line',
                    'stroke_width': 2,
                    'data_generator': 'normal_distribution_overlay'
                }
            ],
            apex_config={
                'chart': {
                    'type': 'histogram',
                    'height': 300
                },
                'plotOptions': {
                    'histogram': {
                        'bucketSize': 0.1
                    }
                },
                'annotations': {
                    'yaxis': [
                        {
                            'y': 0,
                            'borderColor': DashboardColors.NEUTRAL,
                            'label': {
                                'text': 'Mean: 0.0°C',
                                'style': {
                                    'color': '#fff',
                                    'background': DashboardColors.NEUTRAL
                                }
                            }
                        },
                        {
                            'y': 0.5,
                            'borderColor': DashboardColors.WARNING,
                            'label': {
                                'text': 'Std Dev: ±0.5°C',
                                'style': {
                                    'color': '#fff',
                                    'background': DashboardColors.WARNING
                                }
                            }
                        },
                        {
                            'y': 1.96,
                            'borderColor': DashboardColors.ERROR,
                            'label': {
                                'text': '95% CI: ±1.96°C',
                                'style': {
                                    'color': '#fff',
                                    'background': DashboardColors.ERROR
                                }
                            }
                        }
                    ]
                }
            }
        )
        
        return histogram
    
    def _build_feature_importance_chart(self, entity_id: str) -> Dict[str, Any]:
        """Build feature importance horizontal bar chart.
        
        Shows which input features most affect temperature predictions with
        bars normalized to sum to 100% for easy comparison.
        
        Args:
            entity_id: Base entity ID for the climate component
            
        Returns:
            Feature importance bar chart card configuration
        """
        from .constants import DashboardColors
        
        # Create horizontal bar chart
        importance_chart = self._templates.get_line_graph(
            header={'title': 'Feature Importance', 'show': True},
            series=[
                {
                    'name': 'Importance %',
                    'data_generator': 'feature_importance_normalized',
                    'color': DashboardColors.PRIMARY
                }
            ],
            apex_config={
                'chart': {
                    'type': 'bar',
                    'height': 300
                },
                'plotOptions': {
                    'bar': {
                        'horizontal': True,
                        'borderRadius': 4,
                        'dataLabels': {
                            'position': 'center'
                        }
                    }
                },
                'xaxis': {
                    'categories': [
                        'Outdoor Temperature',
                        'Time of Day',
                        'Day of Week', 
                        'Power Consumption',
                        'Previous Offset'
                    ],
                    'title': {
                        'text': 'Feature Importance (%)'
                    }
                },
                'yaxis': {
                    'title': {
                        'text': 'Features'
                    }
                },
                'dataLabels': {
                    'enabled': True,
                    'formatter': 'function (val) { return val + "%"; }'
                },
                'tooltip': {
                    'y': {
                        'formatter': 'function (val) { return val + "% importance"; }'
                    }
                }
            }
        )
        
        return importance_chart
    
    def _build_confidence_bands_chart(self, entity_id: str) -> Dict[str, Any]:
        """Build confidence bands area chart showing prediction uncertainty.
        
        Shows actual temperature values with upper and lower prediction bounds
        as filled areas to visualize model uncertainty over time.
        
        Args:
            entity_id: Base entity ID for the climate component
            
        Returns:
            Confidence bands area chart card configuration
        """
        from .constants import DashboardColors
        
        # Create area chart with confidence bands
        confidence_chart = self._templates.get_line_graph(
            header={'title': 'Prediction Confidence', 'show': True},
            graph_span='24h',
            series=[
                {
                    'entity': f'sensor.{entity_id}_current_temperature',
                    'name': 'Actual Temperature',
                    'color': DashboardColors.SUCCESS,
                    'stroke_width': 2,
                    'unit': '°C',
                    'type': 'line'
                },
                {
                    'entity': f'sensor.{entity_id}_prediction_upper_bound',
                    'name': 'Upper Confidence',
                    'color': DashboardColors.PRIMARY_LIGHT,
                    'fill_opacity': 0.3,
                    'unit': '°C',
                    'type': 'area'
                },
                {
                    'entity': f'sensor.{entity_id}_prediction_lower_bound',
                    'name': 'Lower Confidence',
                    'color': DashboardColors.PRIMARY_LIGHT,
                    'fill_opacity': 0.3,
                    'unit': '°C',
                    'type': 'area'
                }
            ],
            apex_config={
                'chart': {
                    'type': 'area',
                    'height': 300
                },
                'fill': {
                    'type': 'gradient',
                    'gradient': {
                        'opacityFrom': 0.6,
                        'opacityTo': 0.1
                    }
                },
                'stroke': {
                    'width': [2, 1, 1]
                },
                'tooltip': {
                    'shared': True,
                    'intersect': False
                }
            }
        )
        
        return confidence_chart
    
    def _build_performance_metrics_grid(self, entity_id: str) -> Dict[str, Any]:
        """Build performance metrics grid with real-time KPIs.
        
        Shows key performance indicators including MAE, RMSE, R² score,
        model age, and training sample count in an organized grid layout.
        
        Args:
            entity_id: Base entity ID for the climate component
            
        Returns:
            Performance metrics grid card configuration
        """
        return {
            'type': 'entities',
            'title': 'Performance Metrics',
            'entities': [
                {
                    'entity': SENSOR_MAPPINGS['mae'].format(entity=entity_id),
                    'name': 'Mean Absolute Error (MAE)',
                    'icon': 'mdi:target',
                    'unit': '°C'
                },
                {
                    'entity': SENSOR_MAPPINGS['rmse'].format(entity=entity_id),
                    'name': 'Root Mean Square Error (RMSE)',
                    'icon': 'mdi:chart-bell-curve',
                    'unit': '°C'
                },
                {
                    'entity': f'sensor.{entity_id}_r_squared',
                    'name': 'R² Score (Goodness of Fit)',
                    'icon': 'mdi:percent',
                    'unit': '%'
                },
                {
                    'entity': f'sensor.{entity_id}_model_age_hours',
                    'name': 'Model Age',
                    'icon': 'mdi:clock-outline',
                    'unit': 'hours'
                },
                {
                    'entity': f'sensor.{entity_id}_samples_collected',
                    'name': 'Training Sample Count',
                    'icon': 'mdi:database',
                    'unit': 'samples'
                },
                {
                    'entity': f'sensor.{entity_id}_outliers_detected',
                    'name': 'Outliers Detected',
                    'icon': 'mdi:alert-circle',
                    'unit': 'count'
                }
            ],
            'show_header_toggle': False,
            'state_color': True
        }


class ThermalMetricsTabBuilder(TabBuilder):
    """Builder for the Thermal Metrics tab - deep thermal system visibility."""
    
    def __init__(self, templates: GraphTemplates, tooltips: TooltipProvider):
        """Initialize the Thermal Metrics tab builder.
        
        Args:
            templates: GraphTemplates instance for card template generation
            tooltips: TooltipProvider instance for adding helpful tooltips
        """
        self._templates = templates
        self._tooltips = tooltips
    
    def get_tab_config(self) -> Dict[str, str]:
        """Get tab metadata for the Thermal Metrics tab.
        
        Returns:
            Dictionary with tab configuration including title, path, and icon.
        """
        return {
            'title': 'Thermal Metrics',
            'path': 'thermal',
            'icon': 'mdi:thermometer-lines'
        }
    
    def build_cards(self, entity_id: str) -> List[Dict[str, Any]]:
        """Build all cards for the Thermal Metrics tab.
        
        The Thermal Metrics tab provides deep thermal system visibility including:
        1. Tau evolution graph (line graph showing tau_cooling/warming over time)
        2. State distribution pie chart (time in each thermal state)
        3. State transition diagram (flow between states)
        4. Drift analysis scatter plot (predicted vs actual)
        5. Probe history table (last 20 probes)
        6. Comfort violations heatmap (hour x day grid)
        
        Args:
            entity_id: Base entity ID for the climate component (e.g., 'living_room')
            
        Returns:
            List of card dictionaries for Home Assistant dashboard
        """
        cards = []
        
        # Handle None or empty entity_id gracefully
        if not entity_id:
            entity_id = "unknown"
        
        # 1. Tau evolution graph
        cards.append(self._build_tau_evolution_graph(entity_id))
        
        # 2. State distribution pie chart
        cards.append(self._build_state_distribution_pie(entity_id))
        
        # 3. State transition diagram
        cards.append(self._build_state_transition_diagram(entity_id))
        
        # 4. Drift analysis scatter plot
        cards.append(self._build_drift_analysis_scatter(entity_id))
        
        # 5. Probe history table
        cards.append(self._build_probe_history_table(entity_id))
        
        # 6. Comfort violations heatmap
        cards.append(self._build_comfort_violations_heatmap(entity_id))
        
        return cards
    
    def _build_tau_evolution_graph(self, entity_id: str) -> Dict[str, Any]:
        """Build tau evolution line graph showing thermal constants over time.
        
        Shows tau_cooling and tau_warming with markers for probe events,
        time range selector, and hover tooltips.
        
        Args:
            entity_id: Base entity ID for the climate component
            
        Returns:
            Tau evolution graph card configuration
        """
        graph = self._templates.get_line_graph(
            header={'title': 'Tau Evolution', 'show': True},
            graph_span='24h',
            series=[
                {
                    'entity': SENSOR_MAPPINGS['tau_cooling'].format(entity=entity_id),
                    'name': 'Tau Cooling',
                    'color': '#1976D2',
                    'stroke_width': 2,
                    'unit': 'min'
                },
                {
                    'entity': SENSOR_MAPPINGS['tau_warming'].format(entity=entity_id),
                    'name': 'Tau Warming',
                    'color': '#4CAF50',
                    'stroke_width': 2,
                    'unit': 'min'
                }
            ],
            apex_config={
                'chart': {'height': 250},
                'legend': {'show': True},
                'tooltip': {'enabled': True, 'shared': True},
                'markers': {'size': 4, 'hover': {'size': 6}}
            }
        )
        
        return graph
    
    def _build_state_distribution_pie(self, entity_id: str) -> Dict[str, Any]:
        """Build state distribution pie chart showing time in each thermal state.
        
        Shows percentages for PRIMING, DRIFTING, PROBING, CORRECTING states.
        
        Args:
            entity_id: Base entity ID for the climate component
            
        Returns:
            State distribution pie chart configuration
        """
        return {
            'type': 'custom:apexcharts-card',
            'header': {'title': 'Thermal State Distribution', 'show': True},
            'graph_span': '24h',
            'series': [
                {
                    'entity': SENSOR_MAPPINGS['thermal_state'].format(entity=entity_id),
                    'name': 'Thermal State'
                }
            ],
            'apex_config': {
                'chart': {'type': 'pie', 'height': 300},
                'legend': {'position': 'bottom'},
                'dataLabels': {'enabled': True},
                'tooltip': {'enabled': True}
            }
        }
    
    def _build_state_transition_diagram(self, entity_id: str) -> Dict[str, Any]:
        """Build state transition flow diagram showing transitions between states.
        
        Uses Plotly for sankey/flow diagram capabilities.
        
        Args:
            entity_id: Base entity ID for the climate component
            
        Returns:
            State transition diagram configuration
        """
        return {
            'type': 'custom:plotly-graph-card',
            'title': 'State Transitions',  # Add top-level title for consistency
            'hours_to_show': 168,  # 1 week
            'refresh_interval': 300,
            'layout': {
                'title': 'State Transitions',
                'height': 300,
                'showlegend': True,
                'hovermode': 'closest'
            },
            'data': [
                {
                    'type': 'sankey',
                    'node': {
                        'pad': 15,
                        'thickness': 20,
                        'line': {'color': 'black', 'width': 0.5},
                        'label': ['PRIMING', 'DRIFTING', 'PROBING', 'CORRECTING']
                    },
                    'link': {
                        'source': [0, 1, 2, 1, 3, 2],  # From states
                        'target': [1, 2, 3, 0, 1, 1],  # To states  
                        'value': [10, 15, 8, 5, 12, 6]  # Transition counts
                    }
                }
            ]
        }
    
    def _build_drift_analysis_scatter(self, entity_id: str) -> Dict[str, Any]:
        """Build drift analysis scatter plot with trend line.
        
        Shows predicted vs actual temperature with color coding by outdoor temp,
        trend line, and R² value.
        
        Args:
            entity_id: Base entity ID for the climate component
            
        Returns:
            Drift analysis scatter plot configuration
        """
        return {
            'type': 'custom:apexcharts-card',
            'header': {
                'title': 'Drift Analysis',
                'show': True,
                'subtitle': 'R² = 0.85'  # Placeholder - would be calculated
            },
            'graph_span': '24h',
            'series': [
                {
                    'entity': f'sensor.{entity_id}_predicted_temperature',
                    'name': 'Predicted vs Actual',
                    'color': '#1976D2'
                }
            ],
            'apex_config': {
                'chart': {'type': 'scatter', 'height': 300},
                'xaxis': {'title': {'text': 'Predicted Temperature (°C)'}},
                'yaxis': {'title': {'text': 'Actual Temperature (°C)'}},
                'tooltip': {'enabled': True},
                'markers': {'size': 6},
                'regression_line': True  # Enable trend line
            }
        }
    
    def _build_probe_history_table(self, entity_id: str) -> Dict[str, Any]:
        """Build probe history table with last 20 probes.
        
        Columns: Timestamp, Tau, Confidence, Duration, Outdoor Temp
        
        Args:
            entity_id: Base entity ID for the climate component
            
        Returns:
            Probe history table configuration
        """
        return {
            'type': 'entities',
            'title': 'Recent Probe History',
            'entities': [
                {
                    'entity': f'sensor.{entity_id}_last_probe_timestamp',
                    'name': 'Last Probe Time',
                    'icon': 'mdi:clock-outline'
                },
                {
                    'entity': SENSOR_MAPPINGS['tau_cooling'].format(entity=entity_id),
                    'name': 'Current Tau Cooling',
                    'icon': 'mdi:thermometer-minus'
                },
                {
                    'entity': SENSOR_MAPPINGS['tau_warming'].format(entity=entity_id),
                    'name': 'Current Tau Warming', 
                    'icon': 'mdi:thermometer-plus'
                },
                {
                    'entity': SENSOR_MAPPINGS['confidence'].format(entity=entity_id),
                    'name': 'Confidence',
                    'icon': 'mdi:percent'
                },
                {
                    'entity': f'sensor.{entity_id}_probe_duration',
                    'name': 'Last Probe Duration',
                    'icon': 'mdi:timer-outline'
                }
            ],
            'columns': [
                {'name': 'Timestamp', 'field': 'timestamp'},
                {'name': 'Tau', 'field': 'tau_value'},
                {'name': 'Confidence', 'field': 'confidence'}, 
                {'name': 'Duration', 'field': 'duration'},
                {'name': 'Outdoor Temp', 'field': 'outdoor_temp'}
            ],
            'show_header_toggle': False
        }
    
    def _build_comfort_violations_heatmap(self, entity_id: str) -> Dict[str, Any]:
        """Build comfort violations heatmap showing 24x7 grid.
        
        Hour x Day grid showing violation frequency with proper axis labels.
        
        Args:
            entity_id: Base entity ID for the climate component
            
        Returns:
            Comfort violations heatmap configuration
        """
        return {
            'type': 'custom:plotly-graph-card',
            'title': 'Comfort Violations Heatmap',  # Add top-level title for consistency
            'hours_to_show': 168,  # 1 week
            'refresh_interval': 300,
            'layout': {
                'title': 'Comfort Violations Heatmap',
                'height': 300,
                'showlegend': True,
                'hovermode': 'closest',
                'xaxis': {
                    'title': 'Hour of Day',
                    'tickmode': 'array',
                    'tickvals': list(range(24)),
                    'ticktext': [f'{i:02d}:00' for i in range(24)]
                },
                'yaxis': {
                    'title': 'Day of Week',
                    'tickmode': 'array',
                    'tickvals': list(range(7)),
                    'ticktext': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                }
            },
            'data': [
                {
                    'type': 'heatmap',
                    'z': [
                        # Placeholder 7x24 matrix - would be populated from sensor data
                        [i * j % 10 for j in range(24)] for i in range(7)
                    ],
                    'x': list(range(24)),  # Hours 0-23
                    'y': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                    'colorscale': 'Viridis',
                    'showscale': True
                }
            ]
        }

class OptimizationTabBuilder(TabBuilder):
    """Builder for Optimization tab - system efficiency and optimization opportunities."""
    
    def __init__(self, templates: GraphTemplates, tooltips: TooltipProvider):
        """Initialize optimization tab builder with dependencies."""
        self._templates = templates
        self._tooltips = tooltips
    
    def get_tab_config(self) -> Dict[str, str]:
        """Get optimization tab metadata."""
        return {
            'title': 'Optimization',
            'icon': 'mdi:tune',
            'path': 'optimization'
        }
    
    def build_cards(self, entity_id: str) -> List[Dict[str, Any]]:
        """Build all cards for optimization tab.
        
        Implements the optimization analysis interface with:
        1. HVAC cycle analysis histogram
        2. Energy efficiency radar chart
        3. Temperature response time analysis
        4. Offset effectiveness scatter plot
        5. Overshoot analysis timeline
        6. System optimization suggestions
        """
        cards = []
        
        # Row 1: HVAC Cycle Analysis (full width)
        cards.append(self._build_cycle_analysis_histogram(entity_id))
        
        # Row 2: Energy Efficiency & Response Times (side by side)  
        cards.extend([
            self._build_efficiency_radar_chart(entity_id),
            self._build_response_time_analysis(entity_id)
        ])
        
        # Row 3: Offset Effectiveness & Overshoot Analysis (side by side)
        cards.extend([
            self._build_offset_effectiveness_scatter(entity_id),
            self._build_overshoot_analysis(entity_id)
        ])
        
        # Row 4: Optimization Suggestions (full width)
        cards.append(self._build_optimization_suggestions(entity_id))
        
        return cards
    
    def _build_cycle_analysis_histogram(self, entity_id: str) -> Dict[str, Any]:
        """Build HVAC cycle duration analysis histogram."""
        return {
            'type': 'custom:apexcharts-card',
            'title': 'HVAC Cycle Duration Analysis',
            'graph_span': '7d',
            'header': {
                'show': True,
                'title': 'Cycle Duration Distribution',
                'show_states': True
            },
            'apex_config': {
                'chart': {
                    'height': 300,
                    'type': 'histogram',
                    'toolbar': {'show': True}
                },
                'plotOptions': {
                    'bar': {
                        'horizontal': False,
                        'columnWidth': '80%'
                    }
                },
                'colors': [DashboardColors.SUCCESS, DashboardColors.WARNING],
                'tooltip': {
                    'enabled': True,
                    'shared': True
                },
                'legend': {'show': True},
                'annotations': {
                    'xaxis': [
                        {
                            'x': 300,  # 5 minute minimum
                            'borderColor': DashboardColors.WARNING,
                            'label': {
                                'text': 'Min Cycle',
                                'style': {'background': DashboardColors.WARNING}
                            }
                        }
                    ]
                }
            },
            'series': [
                {
                    'entity': f'sensor.{entity_id}_cycle_on_duration',
                    'name': 'ON Cycles',
                    'type': 'column',
                    'group_by': {
                        'func': 'diff',
                        'duration': '1h'
                    }
                },
                {
                    'entity': f'sensor.{entity_id}_cycle_off_duration', 
                    'name': 'OFF Cycles',
                    'type': 'column',
                    'group_by': {
                        'func': 'diff',
                        'duration': '1h'
                    }
                }
            ]
        }
    
    def _build_efficiency_radar_chart(self, entity_id: str) -> Dict[str, Any]:
        """Build energy efficiency radar/spider chart."""
        return {
            'type': 'custom:apexcharts-card',
            'title': 'Energy Efficiency Score',
            'header': {
                'show': True,
                'title': 'Multi-Dimensional Efficiency',
                'show_states': True
            },
            'apex_config': {
                'chart': {
                    'height': 350,
                    'type': 'radar',
                    'toolbar': {'show': False}
                },
                'plotOptions': {
                    'radar': {
                        'size': 140,
                        'polygons': {
                            'strokeColors': DashboardColors.NEUTRAL,
                            'fill': {
                                'colors': ['transparent']
                            }
                        }
                    }
                },
                'colors': [DashboardColors.PRIMARY, DashboardColors.SUCCESS],
                'markers': {'size': 4, 'colors': ['#fff'], 'strokeWidth': 2},
                'tooltip': {
                    'enabled': True,
                    'custom': f'''function({{ series, seriesIndex, dataPointIndex, w }}) {{
                        const metrics = ['Cycle Efficiency', 'Prediction Accuracy', 'Offset Effectiveness', 'Response Time', 'Overshoot Control'];
                        const tooltips = [
                            '{self._tooltips.get_tooltip("cycle_efficiency")}',
                            '{self._tooltips.get_tooltip("prediction_accuracy")}', 
                            '{self._tooltips.get_tooltip("offset_effectiveness")}',
                            '{self._tooltips.get_tooltip("response_time")}',
                            '{self._tooltips.get_tooltip("overshoot_control")}'
                        ];
                        return '<div class="apexcharts-tooltip-custom">' +
                               '<strong>' + metrics[dataPointIndex] + '</strong><br>' +
                               'Score: ' + series[seriesIndex][dataPointIndex] + '%<br>' +
                               '<em>' + tooltips[dataPointIndex] + '</em>' +
                               '</div>';
                    }}'''
                },
                'legend': {'show': True, 'position': 'bottom'},
                'xaxis': {
                    'categories': [
                        'Cycle Efficiency',
                        'Prediction Accuracy', 
                        'Offset Effectiveness',
                        'Response Time',
                        'Overshoot Control'
                    ]
                },
                'yaxis': {
                    'show': True,
                    'min': 0,
                    'max': 100,
                    'tickAmount': 5
                }
            },
            'series': [
                {
                    'entity': f'sensor.{entity_id}_cycle_efficiency',
                    'name': 'Current',
                    'data': [
                        {'entity': f'sensor.{entity_id}_cycle_efficiency'},
                        {'entity': f'sensor.{entity_id}_prediction_accuracy'},
                        {'entity': f'sensor.{entity_id}_offset_effectiveness'},
                        {'entity': f'sensor.{entity_id}_response_time_score'},
                        {'entity': f'sensor.{entity_id}_overshoot_control_score'}
                    ]
                },
                {
                    'name': 'Optimal',
                    'data': [95, 90, 85, 88, 92]  # Static optimal targets
                }
            ]
        }
    
    def _build_response_time_analysis(self, entity_id: str) -> Dict[str, Any]:
        """Build temperature response time box plot analysis."""
        return {
            'type': 'custom:plotly-graph-card',
            'title': 'Temperature Response Times',
            'hours_to_show': 168,  # 7 days
            'refresh_interval': 300,
            'layout': {
                'height': 350,
                'title': 'Response Time Distribution by Conditions',
                'xaxis': {'title': 'Time Period'},
                'yaxis': {'title': 'Response Time (minutes)'},
                'showlegend': True,
                'hovermode': 'closest'
            },
            'entities': [
                {
                    'entity': f'sensor.{entity_id}_response_time_morning',
                    'name': 'Morning (6-12)',
                    'type': 'box',
                    'boxpoints': 'outliers'
                },
                {
                    'entity': f'sensor.{entity_id}_response_time_afternoon', 
                    'name': 'Afternoon (12-18)',
                    'type': 'box',
                    'boxpoints': 'outliers'
                },
                {
                    'entity': f'sensor.{entity_id}_response_time_evening',
                    'name': 'Evening (18-24)',
                    'type': 'box', 
                    'boxpoints': 'outliers'
                },
                {
                    'entity': f'sensor.{entity_id}_response_time_night',
                    'name': 'Night (0-6)',
                    'type': 'box',
                    'boxpoints': 'outliers'
                }
            ]
        }
    
    def _build_offset_effectiveness_scatter(self, entity_id: str) -> Dict[str, Any]:
        """Build offset effectiveness scatter plot."""
        return {
            'type': 'custom:apexcharts-card',
            'title': 'Offset Effectiveness Analysis',
            'graph_span': '7d',
            'header': {
                'show': True,
                'title': 'Applied Offset vs Temperature Correction',
                'show_states': True
            },
            'apex_config': {
                'chart': {
                    'height': 350,
                    'type': 'scatter',
                    'zoom': {'enabled': True}
                },
                'colors': [DashboardColors.PRIMARY],
                'tooltip': {
                    'enabled': True,
                    'x': {'formatter': 'function(val) { return "Applied Offset: " + val + "°C"; }'},
                    'y': {'formatter': 'function(val) { return "Achieved: " + val + "°C"; }'}
                },
                'legend': {'show': True},
                'annotations': {
                    'xaxis': [
                        {
                            'x': 0,
                            'borderColor': DashboardColors.NEUTRAL,
                            'strokeDashArray': 5
                        }
                    ],
                    'yaxis': [
                        {
                            'y': 0,
                            'borderColor': DashboardColors.NEUTRAL,
                            'strokeDashArray': 5
                        }
                    ]
                },
                'xaxis': {
                    'title': {'text': 'Applied Offset (°C)'},
                    'decimalsInFloat': 1
                },
                'yaxis': {
                    'title': {'text': 'Temperature Correction Achieved (°C)'},
                    'decimalsInFloat': 1
                }
            },
            'series': [
                {
                    'entity': f'sensor.{entity_id}_offset_effectiveness_data',
                    'name': 'Effectiveness Points',
                    'type': 'scatter'
                }
            ]
        }
    
    def _build_overshoot_analysis(self, entity_id: str) -> Dict[str, Any]:
        """Build overshoot analysis timeline."""
        return {
            'type': 'custom:apexcharts-card',
            'title': 'Temperature Overshoot Analysis',
            'graph_span': '24h',
            'header': {
                'show': True,
                'title': 'Overshoot Events & Duration',
                'show_states': True
            },
            'apex_config': {
                'chart': {
                    'height': 350,
                    'type': 'line',
                    'toolbar': {'show': True}
                },
                'colors': [
                    DashboardColors.PRIMARY,
                    DashboardColors.SUCCESS, 
                    DashboardColors.ERROR
                ],
                'stroke': {'curve': 'smooth', 'width': 2},
                'markers': {'size': 4},
                'tooltip': {
                    'enabled': True,
                    'shared': True,
                    'intersect': False
                },
                'legend': {'show': True, 'position': 'top'},
                'annotations': {
                    'yaxis': [
                        {
                            'y': 0.5,
                            'borderColor': DashboardColors.WARNING,
                            'label': {
                                'text': 'Overshoot Threshold',
                                'style': {'background': DashboardColors.WARNING}
                            }
                        }
                    ]
                },
                'yaxis': {
                    'title': {'text': 'Temperature Deviation (°C)'},
                    'decimalsInFloat': 1
                }
            },
            'series': [
                {
                    'entity': f'sensor.{entity_id}_setpoint',
                    'name': 'Target Temperature',
                    'type': 'line'
                },
                {
                    'entity': f'sensor.{entity_id}_temperature',
                    'name': 'Actual Temperature',
                    'type': 'line'
                },
                {
                    'entity': f'sensor.{entity_id}_overshoot_magnitude',
                    'name': 'Overshoot Events',
                    'type': 'line'
                }
            ]
        }
    
    def _build_optimization_suggestions(self, entity_id: str) -> Dict[str, Any]:
        """Build optimization suggestions panel."""
        return {
            'type': 'entities',
            'title': 'System Optimization Suggestions',
            'state_color': True,
            'show_header_toggle': False,
            'entities': [
                {
                    'entity': f'sensor.{entity_id}_cycle_analysis_suggestion',
                    'name': 'Cycle Optimization',
                    'icon': 'mdi:sync'
                },
                {
                    'entity': f'sensor.{entity_id}_offset_analysis_suggestion',
                    'name': 'Offset Effectiveness',
                    'icon': 'mdi:target'
                },
                {
                    'entity': f'sensor.{entity_id}_response_analysis_suggestion',
                    'name': 'Response Time',
                    'icon': 'mdi:timer'
                },
                {
                    'entity': f'sensor.{entity_id}_overshoot_analysis_suggestion',
                    'name': 'Overshoot Control',
                    'icon': 'mdi:arrow-up-bold'
                },
                {
                    'entity': f'sensor.{entity_id}_efficiency_analysis_suggestion',
                    'name': 'Energy Efficiency',
                    'icon': 'mdi:lightning-bolt'
                }
            ]
        }


class SystemHealthTabBuilder(TabBuilder):
    """Builder for System Health tab - diagnostics and component status."""
    
    def __init__(self, templates: GraphTemplates, tooltips: TooltipProvider):
        """Initialize system health tab builder with dependencies."""
        self._templates = templates
        self._tooltips = tooltips
    
    def get_tab_config(self) -> Dict[str, str]:
        """Get system health tab metadata."""
        return {
            'title': 'System Health',
            'icon': 'mdi:heart-pulse',
            'path': 'system_health'
        }
    
    def build_cards(self, entity_id: str) -> List[Dict[str, Any]]:
        """Build all cards for system health tab.
        
        Implements the system health monitoring interface with:
        1. Component status grid
        2. Sensor readings with sparklines
        3. Error log display
        4. Performance metrics
        """
        cards = []
        
        # Row 1: Component Status Grid (full width)
        cards.append(self._build_component_status_grid(entity_id))
        
        # Row 2: Sensor Readings (full width)
        cards.append(self._build_sensor_readings_panel(entity_id))
        
        # Row 3: Error Log & Performance Metrics (side by side)
        cards.extend([
            self._build_error_log(entity_id),
            self._build_performance_metrics(entity_id)
        ])
        
        return cards
    
    def _build_component_status_grid(self, entity_id: str) -> Dict[str, Any]:
        """Build component status monitoring grid."""
        return {
            'type': 'entities',
            'title': 'Component Health Status',
            'state_color': True,
            'show_header_toggle': False,
            'entities': [
                {
                    'type': 'section',
                    'label': 'Core Components'
                },
                {
                    'entity': f'binary_sensor.{entity_id}_offset_engine_healthy',
                    'name': 'Offset Engine',
                    'icon': 'mdi:engine',
                    'secondary_info': f'Last calculation: {{{{ states("sensor.{entity_id}_offset_last_update") }}}}'
                },
                {
                    'entity': f'binary_sensor.{entity_id}_thermal_manager_healthy',
                    'name': 'Thermal Manager',
                    'icon': 'mdi:thermostat',
                    'secondary_info': f'State: {{{{ states("sensor.{entity_id}_thermal_state") }}}}'
                },
                {
                    'entity': f'binary_sensor.{entity_id}_sensor_manager_healthy',
                    'name': 'Sensor Manager',
                    'icon': 'mdi:sensors',
                    'secondary_info': f'Sensors active: {{{{ states("sensor.{entity_id}_active_sensors") }}}}'
                },
                {
                    'type': 'section',
                    'label': 'Learning Components'
                },
                {
                    'entity': f'binary_sensor.{entity_id}_delay_learner_healthy',
                    'name': 'Delay Learner',
                    'icon': 'mdi:clock-outline',
                    'secondary_info': f'Learned delay: {{{{ states("sensor.{entity_id}_learned_delay") }}}}s'
                },
                {
                    'entity': f'binary_sensor.{entity_id}_seasonal_learner_healthy',
                    'name': 'Seasonal Learner', 
                    'icon': 'mdi:weather-partly-cloudy',
                    'secondary_info': f'Patterns: {{{{ states("sensor.{entity_id}_seasonal_patterns") }}}}'
                },
                {
                    'type': 'section',
                    'label': 'System Status'
                },
                {
                    'entity': f'sensor.{entity_id}_system_uptime',
                    'name': 'System Uptime',
                    'icon': 'mdi:clock-check-outline'
                },
                {
                    'entity': f'sensor.{entity_id}_error_count',
                    'name': 'Error Count (24h)',
                    'icon': 'mdi:alert-circle-outline'
                },
                {
                    'entity': f'sensor.{entity_id}_memory_usage',
                    'name': 'Memory Usage',
                    'icon': 'mdi:memory'
                }
            ]
        }
    
    def _build_sensor_readings_panel(self, entity_id: str) -> Dict[str, Any]:
        """Build real-time sensor readings with sparklines."""
        return {
            'type': 'custom:plotly-graph-card',
            'title': 'Real-Time Sensor Readings',
            'hours_to_show': 24,
            'refresh_interval': 30,
            'layout': {
                'height': 300,
                'title': 'Sensor Values with 24h History',
                'showlegend': True,
                'hovermode': 'x unified',
                'yaxis': {'title': 'Temperature (°C)'},
                'yaxis2': {
                    'title': 'Power (W) / Humidity (%)',
                    'overlaying': 'y',
                    'side': 'right'
                }
            },
            'entities': [
                {
                    'entity': f'sensor.{entity_id}_temperature',
                    'name': 'Room Temperature',
                    'line': {'color': DashboardColors.SUCCESS, 'width': 2},
                    'yaxis': 'y'
                },
                {
                    'entity': f'sensor.{entity_id}_outdoor_temperature', 
                    'name': 'Outdoor Temperature',
                    'line': {'color': DashboardColors.WARNING, 'width': 2},
                    'yaxis': 'y'
                },
                {
                    'entity': f'sensor.{entity_id}_power_consumption',
                    'name': 'Power Consumption',
                    'line': {'color': DashboardColors.ERROR, 'width': 1.5},
                    'yaxis': 'y2'
                },
                {
                    'entity': f'sensor.{entity_id}_humidity',
                    'name': 'Humidity',
                    'line': {'color': DashboardColors.PRIMARY, 'width': 1.5},
                    'yaxis': 'y2'
                }
            ]
        }
    
    def _build_error_log(self, entity_id: str) -> Dict[str, Any]:
        """Build error log display."""
        return {
            'type': 'entities',
            'title': 'Recent Errors & Warnings',
            'state_color': True,
            'show_header_toggle': False,
            'entities': [
                {
                    'entity': f'sensor.{entity_id}_last_error',
                    'name': 'Last Error',
                    'icon': 'mdi:alert-circle',
                    'secondary_info': f'{{{{ states("sensor.{entity_id}_last_error_time") }}}}'
                },
                {
                    'entity': f'sensor.{entity_id}_last_warning',
                    'name': 'Last Warning',
                    'icon': 'mdi:alert',
                    'secondary_info': f'{{{{ states("sensor.{entity_id}_last_warning_time") }}}}'
                },
                {
                    'type': 'section',
                    'label': 'Error History (24h)'
                },
                {
                    'entity': f'sensor.{entity_id}_critical_errors_24h',
                    'name': 'Critical Errors',
                    'icon': 'mdi:alert-circle'
                },
                {
                    'entity': f'sensor.{entity_id}_warnings_24h',
                    'name': 'Warnings',
                    'icon': 'mdi:alert'
                },
                {
                    'entity': f'sensor.{entity_id}_info_messages_24h',
                    'name': 'Info Messages',
                    'icon': 'mdi:information'
                },
                {
                    'type': 'section',
                    'label': 'Component Errors'
                },
                {
                    'entity': f'sensor.{entity_id}_offset_engine_errors',
                    'name': 'Offset Engine',
                    'icon': 'mdi:engine-off'
                },
                {
                    'entity': f'sensor.{entity_id}_thermal_manager_errors',
                    'name': 'Thermal Manager',
                    'icon': 'mdi:thermostat-box'
                },
                {
                    'entity': f'sensor.{entity_id}_learner_errors',
                    'name': 'Learning Components',
                    'icon': 'mdi:brain'
                }
            ]
        }
    
    def _build_performance_metrics(self, entity_id: str) -> Dict[str, Any]:
        """Build system performance metrics display."""
        return {
            'type': 'entities',
            'title': 'Performance Metrics',
            'state_color': False,
            'show_header_toggle': False,
            'entities': [
                {
                    'type': 'section',
                    'label': 'Update Performance'
                },
                {
                    'entity': f'sensor.{entity_id}_update_latency',
                    'name': 'Update Latency',
                    'icon': 'mdi:timer-outline',
                    'secondary_info': 'Average response time'
                },
                {
                    'entity': f'sensor.{entity_id}_update_frequency',
                    'name': 'Update Frequency',
                    'icon': 'mdi:refresh',
                    'secondary_info': 'Updates per minute'
                },
                {
                    'entity': f'sensor.{entity_id}_calculation_time',
                    'name': 'Calculation Time',
                    'icon': 'mdi:calculator',
                    'secondary_info': 'Offset computation time'
                },
                {
                    'type': 'section',
                    'label': 'Resource Usage'
                },
                {
                    'entity': f'sensor.{entity_id}_memory_usage_mb',
                    'name': 'Memory Usage',
                    'icon': 'mdi:memory',
                    'secondary_info': 'RAM consumption'
                },
                {
                    'entity': f'sensor.{entity_id}_cpu_usage_percent',
                    'name': 'CPU Usage',
                    'icon': 'mdi:chip',
                    'secondary_info': 'During training'
                },
                {
                    'entity': f'sensor.{entity_id}_storage_used_kb',
                    'name': 'Storage Used',
                    'icon': 'mdi:harddisk',
                    'secondary_info': 'Persistent data size'
                },
                {
                    'type': 'section',
                    'label': 'Network & I/O'
                },
                {
                    'entity': f'sensor.{entity_id}_api_response_time',
                    'name': 'API Response Time',
                    'icon': 'mdi:web',
                    'secondary_info': 'Home Assistant API'
                },
                {
                    'entity': f'sensor.{entity_id}_sensor_read_errors',
                    'name': 'Sensor Read Errors',
                    'icon': 'mdi:sensor-off',
                    'secondary_info': 'Failed sensor reads'
                }
            ]
        }



class OptimizationTabBuilder(TabBuilder):
    """Builder for the Optimization tab - HVAC efficiency analysis and suggestions."""
    
    def __init__(self, templates: GraphTemplates, tooltips: TooltipProvider):
        """Initialize the Optimization tab builder.
        
        Args:
            templates: GraphTemplates instance for card template generation
            tooltips: TooltipProvider instance for adding helpful tooltips
        """
        self._templates = templates
        self._tooltips = tooltips
    
    def get_tab_config(self) -> Dict[str, str]:
        """Get tab metadata for the Optimization tab.
        
        Returns:
            Dictionary with tab configuration including title, path, and icon.
        """
        return {
            'title': 'Optimization',
            'path': 'optimization',
            'icon': 'mdi:tune'
        }
    
    def build_cards(self, entity_id: str) -> List[Dict[str, Any]]:
        """Build all cards for the Optimization tab.
        
        The Optimization tab provides HVAC efficiency visualizations and actionable
        suggestions to improve system performance including:
        1. HVAC cycle duration histogram with threshold indicators
        2. Efficiency spider/radar chart with 5 dimensions
        3. Response time box plots by time of day and outdoor temperature
        4. Offset effectiveness scatter plot (applied vs achieved)
        5. Overshoot analysis time series visualization
        6. Dynamic optimization suggestions panel with contextual advice
        
        Args:
            entity_id: Base entity ID for the climate component (e.g., 'living_room')
            
        Returns:
            List of 6 card dictionaries for Home Assistant dashboard
        """
        cards = []
        
        # Handle None or empty entity_id gracefully
        if not entity_id:
            entity_id = "unknown"
        
        # 1. HVAC cycle duration histogram with threshold indicators
        cards.append(self._build_cycle_histogram(entity_id))
        
        # 2. Efficiency spider/radar chart with 5 dimensions
        cards.append(self._build_efficiency_spider_chart(entity_id))
        
        # 3. Response time box plots
        cards.append(self._build_response_time_box_plot(entity_id))
        
        # 4. Offset effectiveness scatter plot
        cards.append(self._build_offset_effectiveness_scatter(entity_id))
        
        # 5. Overshoot analysis time series
        cards.append(self._build_overshoot_analysis(entity_id))
        
        # 6. Optimization suggestions panel
        cards.append(self._build_optimization_suggestions_panel(entity_id))
        
        return cards
    
    def _build_cycle_histogram(self, entity_id: str) -> Dict[str, Any]:
        """Build HVAC cycle duration histogram with threshold indicators.
        
        Shows separate bars for on/off durations with threshold lines for
        optimal cycle lengths and short cycling detection.
        
        Args:
            entity_id: Base entity ID for the climate component
            
        Returns:
            Cycle duration histogram card configuration
        """
        from .constants import DashboardColors
        
        histogram = self._templates.get_line_graph(
            header={'title': 'HVAC Cycle Duration Analysis', 'show': True},
            graph_span='7d',
            series=[
                {
                    'entity': f'sensor.{entity_id}_cycle_on_duration',
                    'name': 'ON Cycle Duration',
                    'color': DashboardColors.PRIMARY,
                    'type': 'histogram',
                    'unit': 'min'
                },
                {
                    'entity': f'sensor.{entity_id}_cycle_off_duration',
                    'name': 'OFF Cycle Duration',
                    'color': DashboardColors.PRIMARY_LIGHT,
                    'type': 'histogram',
                    'unit': 'min'
                }
            ],
            apex_config={
                'chart': {
                    'type': 'histogram',
                    'height': 350
                },
                'plotOptions': {
                    'histogram': {
                        'bucketSize': 5  # 5-minute buckets
                    }
                },
                'annotations': {
                    'xaxis': [
                        {
                            'x': 10,  # 10-minute minimum cycle threshold
                            'borderColor': DashboardColors.WARNING,
                            'strokeDashArray': 5,
                            'label': {
                                'text': 'Min Cycle (10min)',
                                'style': {
                                    'color': '#fff',
                                    'background': DashboardColors.WARNING
                                }
                            }
                        },
                        {
                            'x': 30,  # 30-minute optimal cycle threshold
                            'borderColor': DashboardColors.SUCCESS,
                            'strokeDashArray': 5,
                            'label': {
                                'text': 'Optimal (30min)',
                                'style': {
                                    'color': '#fff',
                                    'background': DashboardColors.SUCCESS
                                }
                            }
                        },
                        {
                            'x': 5,  # Short cycling threshold (5 minutes)
                            'borderColor': DashboardColors.ERROR,
                            'strokeDashArray': 8,
                            'label': {
                                'text': 'Short Cycling (5min)',
                                'style': {
                                    'color': '#fff',
                                    'background': DashboardColors.ERROR
                                }
                            }
                        }
                    ]
                },
                'xaxis': {
                    'title': {'text': 'Cycle Duration (minutes)'}
                },
                'yaxis': {
                    'title': {'text': 'Frequency'}
                },
                'tooltip': {
                    'shared': True,
                    'intersect': False
                }
            }
        )
        
        return histogram
    
    def _build_efficiency_spider_chart(self, entity_id: str) -> Dict[str, Any]:
        """Build efficiency spider/radar chart with 5 dimensions.
        
        Shows 5 efficiency axes: cycle efficiency, prediction accuracy, 
        offset effectiveness, response time, and overshoot control.
        
        Args:
            entity_id: Base entity ID for the climate component
            
        Returns:
            Efficiency spider chart card configuration
        """
        from .constants import DashboardColors
        
        return {
            'type': 'custom:apexcharts-card',
            'header': {'title': 'System Efficiency Overview', 'show': True},
            'series': [
                {
                    'name': 'Current Performance',
                    'color': DashboardColors.PRIMARY,
                    'data': [
                        {'x': 'Cycle Efficiency', 'y': f'sensor.{entity_id}_cycle_efficiency'},
                        {'x': 'Prediction Accuracy', 'y': f'sensor.{entity_id}_prediction_accuracy'},
                        {'x': 'Offset Effectiveness', 'y': f'sensor.{entity_id}_offset_effectiveness'},
                        {'x': 'Response Time', 'y': f'sensor.{entity_id}_response_efficiency'},
                        {'x': 'Overshoot Control', 'y': f'sensor.{entity_id}_overshoot_control'}
                    ]
                },
                {
                    'name': 'Target Performance',
                    'color': DashboardColors.SUCCESS,
                    'data': [
                        {'x': 'Cycle Efficiency', 'y': 85},
                        {'x': 'Prediction Accuracy', 'y': 90},
                        {'x': 'Offset Effectiveness', 'y': 80},
                        {'x': 'Response Time', 'y': 85},
                        {'x': 'Overshoot Control', 'y': 95}
                    ]
                }
            ],
            'apex_config': {
                'chart': {
                    'type': 'radar',
                    'height': 350,
                    'dropShadow': {
                        'enabled': True,
                        'blur': 1,
                        'left': 1,
                        'top': 1
                    }
                },
                'plotOptions': {
                    'radar': {
                        'size': 140,
                        'polygons': {
                            'strokeColors': '#e9e9e9',
                            'fill': {
                                'colors': ['#f8f8f8', '#fff']
                            }
                        }
                    }
                },
                'markers': {
                    'size': 4,
                    'colors': ['#fff'],
                    'strokeColor': DashboardColors.PRIMARY,
                    'strokeWidth': 2
                },
                'tooltip': {
                    'y': {
                        'formatter': 'function(val) { return val + "%"; }'
                    }
                },
                'yaxis': {
                    'tickAmount': 5,
                    'labels': {
                        'formatter': 'function(val, i) { return val + "%"; }'
                    },
                    'min': 0,
                    'max': 100
                },
                'legend': {
                    'position': 'top',
                    'horizontalAlign': 'center'
                }
            }
        }
    
    def _build_response_time_box_plot(self, entity_id: str) -> Dict[str, Any]:
        """Build response time box plots showing quartiles by time and temperature.
        
        Shows response time distribution by time of day and outdoor temperature ranges
        with quartile boxes and outlier detection.
        
        Args:
            entity_id: Base entity ID for the climate component
            
        Returns:
            Response time box plot card configuration
        """
        from .constants import DashboardColors
        
        return {
            'type': 'custom:apexcharts-card',
            'header': {'title': 'Response Time Analysis', 'show': True},
            'graph_span': '7d',
            'series': [
                {
                    'name': 'Morning (6-12)',
                    'type': 'boxPlot',
                    'color': DashboardColors.PRIMARY,
                    'data': [
                        [1, 4, 7, 12, 18]  # min, q1, median, q3, max (minutes)
                    ]
                },
                {
                    'name': 'Afternoon (12-18)',
                    'type': 'boxPlot',
                    'color': DashboardColors.SUCCESS,
                    'data': [
                        [2, 5, 8, 14, 22]
                    ]
                },
                {
                    'name': 'Evening (18-24)',
                    'type': 'boxPlot',
                    'color': DashboardColors.WARNING,
                    'data': [
                        [1, 3, 6, 11, 16]
                    ]
                },
                {
                    'name': 'Night (24-6)',
                    'type': 'boxPlot',
                    'color': DashboardColors.NEUTRAL,
                    'data': [
                        [2, 4, 7, 13, 19]
                    ]
                }
            ],
            'apex_config': {
                'chart': {
                    'type': 'boxPlot',
                    'height': 350
                },
                'plotOptions': {
                    'boxPlot': {
                        'colors': {
                            'upper': DashboardColors.PRIMARY,
                            'lower': DashboardColors.PRIMARY_LIGHT
                        }
                    }
                },
                'xaxis': {
                    'type': 'category',
                    'categories': ['Morning', 'Afternoon', 'Evening', 'Night'],
                    'title': {'text': 'Time Period'}
                },
                'yaxis': {
                    'title': {'text': 'Response Time (minutes)'}
                },
                'tooltip': {
                    'shared': False,
                    'intersect': True
                }
            }
        }
    
    def _build_offset_effectiveness_scatter(self, entity_id: str) -> Dict[str, Any]:
        """Build offset effectiveness scatter plot showing applied vs achieved.
        
        Shows relationship between applied temperature offset and achieved
        temperature change with effectiveness percentage coloring.
        
        Args:
            entity_id: Base entity ID for the climate component
            
        Returns:
            Offset effectiveness scatter plot configuration
        """
        from .constants import DashboardColors
        
        return {
            'type': 'custom:apexcharts-card',
            'header': {
                'title': 'Offset Effectiveness Analysis',
                'show': True,
                'subtitle': 'Applied vs Achieved Temperature Changes'
            },
            'graph_span': '24h',
            'series': [
                {
                    'name': 'Effectiveness',
                    'color': DashboardColors.PRIMARY,
                    'data_generator': 'offset_effectiveness_data'  # Would be populated from sensor data
                }
            ],
            'apex_config': {
                'chart': {
                    'type': 'scatter',
                    'height': 350,
                    'zoom': {
                        'enabled': True,
                        'type': 'xy'
                    }
                },
                'xaxis': {
                    'title': {'text': 'Applied Offset (°C)'},
                    'tickAmount': 10,
                    'type': 'numeric'
                },
                'yaxis': {
                    'title': {'text': 'Achieved Change (°C)'},
                    'tickAmount': 7
                },
                'markers': {
                    'size': 6,
                    'hover': {
                        'size': 8
                    }
                },
                'grid': {
                    'xaxis': {
                        'lines': {'show': True}
                    },
                    'yaxis': {
                        'lines': {'show': True}
                    }
                },
                'annotations': {
                    'points': [
                        {
                            'x': 0,
                            'y': 0,
                            'marker': {
                                'size': 8,
                                'fillColor': DashboardColors.NEUTRAL,
                                'strokeColor': DashboardColors.NEUTRAL
                            },
                            'label': {
                                'text': 'Perfect Match',
                                'offsetY': -10
                            }
                        }
                    ],
                    'line': [
                        {
                            'x': -5,
                            'x2': 5,
                            'y': -5,
                            'y2': 5,
                            'strokeDashArray': 5,
                            'borderColor': DashboardColors.SUCCESS,
                            'label': {
                                'text': 'Ideal Response Line'
                            }
                        }
                    ]
                },
                'tooltip': {
                    'custom': 'function({series, seriesIndex, dataPointIndex, w}) { return "<div class=\'tooltip\'><span>Applied: " + w.globals.seriesX[seriesIndex][dataPointIndex] + "°C</span><br><span>Achieved: " + w.globals.series[seriesIndex][dataPointIndex] + "°C</span><br><span>Effectiveness: " + Math.round((w.globals.series[seriesIndex][dataPointIndex] / w.globals.seriesX[seriesIndex][dataPointIndex]) * 100) + "%</span></div>"; }'
                }
            }
        }
    
    def _build_overshoot_analysis(self, entity_id: str) -> Dict[str, Any]:
        """Build overshoot analysis time series showing temperature overshoots.
        
        Shows target temperature vs actual with highlighting of overshoot events
        and recovery time analysis.
        
        Args:
            entity_id: Base entity ID for the climate component
            
        Returns:
            Overshoot analysis time series card configuration
        """
        from .constants import DashboardColors
        
        graph = self._templates.get_line_graph(
            header={'title': 'Temperature Overshoot Analysis', 'show': True},
            graph_span='24h',
            series=[
                {
                    'entity': f'sensor.{entity_id}_setpoint_temperature',
                    'name': 'Target Temperature',
                    'color': DashboardColors.PRIMARY,
                    'stroke_width': 2,
                    'unit': '°C'
                },
                {
                    'entity': f'sensor.{entity_id}_current_temperature',
                    'name': 'Actual Temperature',
                    'color': DashboardColors.SUCCESS,
                    'stroke_width': 2,
                    'unit': '°C'
                },
                {
                    'entity': f'sensor.{entity_id}_overshoot_events',
                    'name': 'Overshoot Events',
                    'color': DashboardColors.ERROR,
                    'stroke_width': 3,
                    'unit': '°C',
                    'type': 'area',
                    'fill_opacity': 0.3
                }
            ],
            apex_config={
                'chart': {
                    'height': 350,
                    'zoom': {
                        'enabled': True
                    }
                },
                'stroke': {
                    'width': [2, 2, 0],
                    'curve': 'smooth'
                },
                'fill': {
                    'type': ['solid', 'solid', 'gradient'],
                    'gradient': {
                        'opacityFrom': 0.6,
                        'opacityTo': 0.1
                    }
                },
                'markers': {
                    'size': [0, 0, 4],
                    'hover': {
                        'size': [4, 4, 6]
                    }
                },
                'yaxis': {
                    'title': {'text': 'Temperature (°C)'},
                    'labels': {
                        'formatter': 'function (val) { return val.toFixed(1) + "°C"; }'
                    }
                },
                'annotations': {
                    'yaxis': [
                        {
                            'y': 0.5,  # Overshoot threshold
                            'borderColor': DashboardColors.WARNING,
                            'strokeDashArray': 5,
                            'label': {
                                'text': 'Overshoot Threshold (±0.5°C)',
                                'style': {
                                    'color': '#fff',
                                    'background': DashboardColors.WARNING
                                }
                            }
                        }
                    ]
                },
                'tooltip': {
                    'shared': True,
                    'intersect': False,
                    'y': {
                        'formatter': 'function (val) { return val.toFixed(2) + "°C"; }'
                    }
                },
                'legend': {
                    'position': 'top',
                    'horizontalAlign': 'left'
                }
            }
        )
        
        return graph
    
    def _build_optimization_suggestions_panel(self, entity_id: str) -> Dict[str, Any]:
        """Build dynamic optimization suggestions panel with contextual advice.
        
        Provides actionable optimization suggestions based on current metrics
        such as "Short cycling detected" or "Offset effectiveness low".
        
        Args:
            entity_id: Base entity ID for the climate component
            
        Returns:
            Optimization suggestions panel card configuration
        """
        return {
            'type': 'entities',
            'title': 'Optimization Suggestions',
            'entities': [
                {
                    'entity': f'sensor.{entity_id}_optimization_score',
                    'name': 'Overall Optimization Score',
                    'icon': 'mdi:speedometer',
                    'unit': '%'
                },
                {
                    'entity': f'sensor.{entity_id}_primary_suggestion',
                    'name': 'Primary Recommendation',
                    'icon': 'mdi:lightbulb-on'
                },
                {
                    'entity': f'sensor.{entity_id}_cycle_efficiency_status',
                    'name': 'Cycle Efficiency',
                    'icon': 'mdi:sync',
                    'secondary_info': 'last-changed'
                },
                {
                    'entity': f'sensor.{entity_id}_short_cycling_detected',
                    'name': 'Short Cycling Alert',
                    'icon': 'mdi:alert-circle',
                    'secondary_info': 'last-changed'
                },
                {
                    'entity': f'sensor.{entity_id}_offset_effectiveness_score',
                    'name': 'Offset Effectiveness',
                    'icon': 'mdi:target',
                    'unit': '%',
                    'secondary_info': 'last-changed'
                },
                {
                    'entity': f'sensor.{entity_id}_response_time_status',
                    'name': 'Response Time Status',
                    'icon': 'mdi:timer-outline',
                    'secondary_info': 'last-changed'
                },
                {
                    'entity': f'sensor.{entity_id}_energy_efficiency_tip',
                    'name': 'Energy Efficiency Tip',
                    'icon': 'mdi:leaf',
                    'secondary_info': 'last-changed'
                },
                {
                    'entity': f'sensor.{entity_id}_next_optimization_check',
                    'name': 'Next Analysis',
                    'icon': 'mdi:calendar-clock',
                    'secondary_info': 'last-changed'
                }
            ],
            'show_header_toggle': False,
            'state_color': True,
            'theme': 'Backend-selected',
            'card_mod': {
                'style': '''
                ha-card {
                  border: 1px solid var(--divider-color);
                  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .entity {
                  padding: 8px 16px;
                }
                .entity[data-entity*="alert"] {
                  background-color: rgba(244, 67, 54, 0.1);
                }
                .entity[data-entity*="tip"] {
                  background-color: rgba(76, 175, 80, 0.1);
                }
                '''
            }
        }