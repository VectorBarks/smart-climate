"""ValidationMetricsManager for ProbeScheduler performance monitoring.

This module implements validation metrics sensors for ProbeScheduler performance
monitoring according to Architecture Section 20.12.
"""
import logging
import statistics
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class ValidationMetricsManager:
    """Manages performance validation metrics for ProbeScheduler.
    
    Tracks three key validation metrics:
    1. Thermal drift prediction accuracy (MAE)
    2. Temperature overshoot past comfort band boundaries
    3. HVAC cycle efficiency analysis
    
    Args:
        hass: Home Assistant instance
        entity_id: Entity ID for the climate device being monitored
    """
    
    def __init__(self, hass: HomeAssistant, entity_id: str) -> None:
        """Initialize the ValidationMetricsManager."""
        self._hass = hass
        self._entity_id = entity_id
        
        # Storage for validation metrics (in-memory with periodic cleanup)
        self._prediction_errors: List[Dict[str, Any]] = []
        self._overshoot_events: List[Dict[str, Any]] = []
        self._cycle_efficiency_data: List[Dict[str, Any]] = []
        
        _LOGGER.debug("ValidationMetricsManager initialized for %s", entity_id)
    
    def record_prediction_error(self, predicted_drift: float, actual_drift: float) -> None:
        """Record thermal drift prediction accuracy.
        
        Calculates and stores Mean Absolute Error (MAE) between predicted
        and actual thermal drift values.
        
        Args:
            predicted_drift: Predicted thermal drift in °C
            actual_drift: Actual measured thermal drift in °C
        """
        mae = abs(predicted_drift - actual_drift)
        timestamp = datetime.now(timezone.utc)
        
        # Store prediction error record
        error_record = {
            "timestamp": timestamp,
            "mae": mae,
            "predicted": predicted_drift,
            "actual": actual_drift
        }
        self._prediction_errors.append(error_record)
        
        # Clean up old data (keep only last 7 days)
        cutoff = timestamp - timedelta(days=7)
        self._prediction_errors = [
            e for e in self._prediction_errors 
            if e["timestamp"] > cutoff
        ]
        
        _LOGGER.debug(
            "Recorded prediction error: MAE=%.3f°C (predicted=%.2f, actual=%.2f)",
            mae, predicted_drift, actual_drift
        )
    
    def record_temperature_overshoot(
        self, 
        setpoint: float, 
        actual: float, 
        comfort_band: float
    ) -> None:
        """Record temperature overshoot past comfort band.
        
        Tracks when actual temperature exceeds the comfort band boundaries
        for comfort validation metrics.
        
        Args:
            setpoint: Target temperature setpoint in °C
            actual: Actual measured temperature in °C
            comfort_band: Comfort band width in °C (±)
        """
        timestamp = datetime.now(timezone.utc)
        
        # Calculate overshoot amount (positive = overshoot, negative = within band)
        upper_bound = setpoint + comfort_band
        overshoot_amount = actual - upper_bound
        
        # Store overshoot event
        overshoot_record = {
            "timestamp": timestamp,
            "setpoint": setpoint,
            "actual": actual,
            "comfort_band": comfort_band,
            "overshoot_amount": overshoot_amount
        }
        self._overshoot_events.append(overshoot_record)
        
        # Clean up old data (keep only last 24 hours for daily statistics)
        cutoff = timestamp - timedelta(hours=24)
        self._overshoot_events = [
            e for e in self._overshoot_events 
            if e["timestamp"] > cutoff
        ]
        
        if overshoot_amount > 0:
            _LOGGER.debug(
                "Recorded temperature overshoot: %.2f°C (actual=%.1f°C, limit=%.1f°C)",
                overshoot_amount, actual, upper_bound
            )
    
    def record_hvac_cycle(self, duration_minutes: int, is_on_cycle: bool) -> None:
        """Record HVAC cycle for efficiency analysis.
        
        Tracks HVAC on/off cycle durations for efficiency metrics
        and short-cycling detection.
        
        Args:
            duration_minutes: Duration of the cycle in minutes
            is_on_cycle: True for on-cycle, False for off-cycle
        """
        timestamp = datetime.now(timezone.utc)
        
        # Store cycle record
        cycle_record = {
            "timestamp": timestamp,
            "duration_minutes": duration_minutes,
            "is_on_cycle": is_on_cycle
        }
        self._cycle_efficiency_data.append(cycle_record)
        
        # Clean up old data (keep only last 7 days for trend analysis)
        cutoff = timestamp - timedelta(days=7)
        self._cycle_efficiency_data = [
            c for c in self._cycle_efficiency_data 
            if c["timestamp"] > cutoff
        ]
        
        cycle_type = "ON" if is_on_cycle else "OFF"
        _LOGGER.debug(
            "Recorded HVAC %s cycle: %d minutes", 
            cycle_type, duration_minutes
        )
    
    def get_prediction_error_sensor_data(self) -> Dict[str, Any]:
        """Get data for prediction error sensor.
        
        Returns:
            Sensor data dict with state and attributes for prediction error sensor.
        """
        if not self._prediction_errors:
            return {"state": None, "attributes": {}}
        
        # Calculate current MAE from recent errors
        recent_errors = [e["mae"] for e in self._prediction_errors]
        current_mae = statistics.mean(recent_errors)
        
        # Calculate daily MAE breakdown
        daily_mae = self._calculate_daily_mae()
        
        # Calculate trend (Improving, Stable, Degrading)
        trend = self._calculate_trend(recent_errors)
        
        return {
            "state": round(current_mae, 3),
            "attributes": {
                "unit_of_measurement": "°C",
                "friendly_name": "Thermal Prediction Error",
                "device_class": "temperature",
                "sample_count": len(recent_errors),
                "daily_mae": daily_mae,
                "trend": trend,
                "target_mae": 0.5,
                "within_target": current_mae <= 0.5
            }
        }
    
    def get_setpoint_overshoot_sensor_data(self) -> Dict[str, Any]:
        """Get data for setpoint overshoot sensor.
        
        Returns:
            Sensor data dict with state and attributes for setpoint overshoot sensor.
        """
        if not self._overshoot_events:
            return {
                "state": 0.0,
                "attributes": {
                    "unit_of_measurement": "%",
                    "friendly_name": "Temperature Overshoot",
                    "overshoot_events_today": 0,
                    "max_overshoot_today": 0.0,
                    "average_overshoot": 0.0,
                    "comfort_band_size": 0.0
                }
            }
        
        # Calculate metrics from overshoot events
        overshoot_events = [e for e in self._overshoot_events if e["overshoot_amount"] > 0]
        
        overshoot_events_today = len(overshoot_events)
        
        max_overshoot_today = (
            max(e["overshoot_amount"] for e in overshoot_events)
            if overshoot_events else 0.0
        )
        
        average_overshoot = (
            statistics.mean(e["overshoot_amount"] for e in overshoot_events)
            if overshoot_events else 0.0
        )
        
        # Get comfort band size from most recent event
        comfort_band_size = (
            self._overshoot_events[-1]["comfort_band"]
            if self._overshoot_events else 0.0
        )
        
        # Calculate percentage of time outside comfort band
        # For simplification, we'll use ratio of overshoot events to total events
        total_events = len(self._overshoot_events)
        overshoot_percentage = (
            (overshoot_events_today / total_events * 100.0)
            if total_events > 0 else 0.0
        )
        
        return {
            "state": round(overshoot_percentage, 1),
            "attributes": {
                "unit_of_measurement": "%",
                "friendly_name": "Temperature Overshoot",
                "overshoot_events_today": overshoot_events_today,
                "max_overshoot_today": round(max_overshoot_today, 2),
                "average_overshoot": round(average_overshoot, 2),
                "comfort_band_size": round(comfort_band_size, 1)
            }
        }
    
    def get_cycle_efficiency_sensor_data(self) -> Dict[str, Any]:
        """Get data for HVAC cycle efficiency sensor.
        
        Returns:
            Sensor data dict with state and attributes for cycle efficiency sensor.
        """
        if not self._cycle_efficiency_data:
            return {
                "state": 0,
                "attributes": {
                    "unit_of_measurement": None,
                    "friendly_name": "HVAC Cycle Efficiency",
                    "average_on_cycle_minutes": 0.0,
                    "average_off_cycle_minutes": 0.0,
                    "short_cycle_count": 0,
                    "efficiency_trend": "Stable"
                }
            }
        
        # Separate on and off cycles
        on_cycles = [
            c["duration_minutes"] for c in self._cycle_efficiency_data 
            if c["is_on_cycle"]
        ]
        off_cycles = [
            c["duration_minutes"] for c in self._cycle_efficiency_data 
            if not c["is_on_cycle"]
        ]
        
        # Calculate averages
        avg_on_cycle = statistics.mean(on_cycles) if on_cycles else 0.0
        avg_off_cycle = statistics.mean(off_cycles) if off_cycles else 0.0
        
        # Count short cycles (< 10 minutes = inefficient)
        short_cycle_count = len([d for d in on_cycles if d < 10])
        
        # Calculate efficiency score (0-100)
        efficiency_score = self._calculate_efficiency_score(
            avg_on_cycle, avg_off_cycle, short_cycle_count, len(self._cycle_efficiency_data)
        )
        
        # Calculate efficiency trend
        efficiency_trend = self._calculate_efficiency_trend(self._cycle_efficiency_data)
        
        return {
            "state": efficiency_score,
            "attributes": {
                "unit_of_measurement": None,
                "friendly_name": "HVAC Cycle Efficiency",
                "average_on_cycle_minutes": round(avg_on_cycle, 1),
                "average_off_cycle_minutes": round(avg_off_cycle, 1),
                "short_cycle_count": short_cycle_count,
                "efficiency_trend": efficiency_trend
            }
        }
    
    def _calculate_daily_mae(self) -> List[float]:
        """Calculate MAE for each of the last 7 days.
        
        Returns:
            List of daily MAE values for up to 7 days.
        """
        if not self._prediction_errors:
            return []
        
        now = datetime.now(timezone.utc)
        daily_mae = []
        
        for day_offset in range(7):
            day_start = (now - timedelta(days=day_offset)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            day_end = day_start + timedelta(days=1)
            
            day_errors = [
                e["mae"] for e in self._prediction_errors
                if day_start <= e["timestamp"] < day_end
            ]
            
            if day_errors:
                daily_mae.append(round(statistics.mean(day_errors), 3))
        
        return daily_mae[::-1]  # Return in chronological order
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend from a list of values.
        
        Args:
            values: List of numerical values (most recent first)
            
        Returns:
            Trend string: "Improving", "Stable", or "Degrading"
        """
        if len(values) < 3:
            return "Stable"
        
        # Use simple linear regression slope to determine trend
        # For prediction errors, decreasing values = improving
        x_values = list(range(len(values)))
        
        try:
            # Calculate slope using least squares
            n = len(values)
            sum_x = sum(x_values)
            sum_y = sum(values)
            sum_xy = sum(x * y for x, y in zip(x_values, values))
            sum_x2 = sum(x * x for x in x_values)
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            
            # For prediction errors: negative slope = improving, positive = degrading
            if slope < -0.05:  # Threshold for significant improvement
                return "Improving"
            elif slope > 0.05:  # Threshold for significant degradation
                return "Degrading"
            else:
                return "Stable"
                
        except (ZeroDivisionError, ValueError):
            return "Stable"
    
    def _calculate_efficiency_score(
        self, 
        avg_on: float, 
        avg_off: float, 
        short_cycle_count: int, 
        total_cycles: int
    ) -> int:
        """Calculate HVAC efficiency score (0-100).
        
        Args:
            avg_on: Average on-cycle duration in minutes
            avg_off: Average off-cycle duration in minutes
            short_cycle_count: Number of short cycles (<10 min)
            total_cycles: Total number of cycles
            
        Returns:
            Efficiency score from 0-100
        """
        if total_cycles == 0:
            return 0
        
        # Base score from cycle durations
        # Ideal: on cycles 15-30 min, off cycles 30-60 min
        on_score = min(100, max(0, (avg_on - 5) / 25 * 100)) if avg_on > 0 else 0
        off_score = min(100, max(0, (avg_off - 10) / 50 * 100)) if avg_off > 0 else 0
        
        # Penalty for short cycling
        short_cycle_penalty = (short_cycle_count / total_cycles) * 50
        
        # Combined score
        efficiency_score = (on_score + off_score) / 2 - short_cycle_penalty
        
        return max(0, min(100, int(efficiency_score)))
    
    def _calculate_efficiency_trend(self, cycle_data: List[Dict[str, Any]]) -> str:
        """Calculate efficiency trend from cycle data.
        
        Args:
            cycle_data: List of cycle records
            
        Returns:
            Trend string: "Improving", "Stable", or "Degrading"
        """
        if len(cycle_data) < 6:  # Need enough data for trend analysis
            return "Stable"
        
        # Calculate efficiency scores for recent periods
        now = datetime.now(timezone.utc)
        periods = []
        
        for days_back in [1, 2, 3]:  # Last 3 days
            period_start = now - timedelta(days=days_back)
            period_end = now - timedelta(days=days_back-1)
            
            period_cycles = [
                c for c in cycle_data
                if period_start <= c["timestamp"] < period_end
            ]
            
            if len(period_cycles) >= 2:  # Need minimum cycles for meaningful score
                on_cycles = [c["duration_minutes"] for c in period_cycles if c["is_on_cycle"]]
                off_cycles = [c["duration_minutes"] for c in period_cycles if not c["is_on_cycle"]]
                
                if on_cycles and off_cycles:
                    avg_on = statistics.mean(on_cycles)
                    avg_off = statistics.mean(off_cycles)
                    short_count = len([d for d in on_cycles if d < 10])
                    
                    score = self._calculate_efficiency_score(
                        avg_on, avg_off, short_count, len(period_cycles)
                    )
                    
                    periods.append({"efficiency": score, "timestamp": period_start})
        
        if len(periods) < 2:
            return "Stable"
        
        # Sort by timestamp (oldest first) and check trend
        periods.sort(key=lambda x: x["timestamp"])
        efficiency_values = [p["efficiency"] for p in periods]
        
        return self._calculate_trend(efficiency_values[::-1])  # Reverse for trend calculation