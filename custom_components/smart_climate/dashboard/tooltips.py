"""Tooltip provider for Advanced Analytics Dashboard metrics."""

from typing import Dict


class TooltipProvider:
    """Provides tooltip content for all dashboard elements."""

    TOOLTIPS: Dict[str, str] = {
        'tau_value': "Time constant indicating how quickly temperature changes. Lower = faster response",
        'mae': "Mean Absolute Error - average prediction error in °C",
        'thermal_state': "Current operating mode of the thermal management system",
        'confidence': "Statistical confidence in the current prediction (0-100%)",
        'offset': "Temperature adjustment applied to achieve comfort",
        'learning_progress': "Percentage of data collected for accurate predictions",
        'cycle_health': "HVAC cycling efficiency - higher is better",
        'rmse': "Root Mean Square Error - prediction accuracy metric",
        'hysteresis': "Temperature difference between AC start and stop",
        'drift_rate': "How fast temperature changes when AC is off"
    }

    def get_tooltip(self, metric_key: str) -> str:
        """Get tooltip text for metric.
        
        Args:
            metric_key: The key for the metric to get tooltip for
            
        Returns:
            Tooltip text for the metric, or empty string if key not found
        """
        if not isinstance(metric_key, str):
            return ""
        
        return self.TOOLTIPS.get(metric_key, "")