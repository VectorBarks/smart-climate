"""ABOUTME: Core humidity monitoring component with threshold detection.
Monitors humidity sensors and detects threshold crossings for event-driven updates."""

from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from homeassistant.core import HomeAssistant
import logging

_LOGGER = logging.getLogger(__name__)


class HumidityMonitor:
    """Core humidity monitoring class with threshold detection."""

    def __init__(self, hass: HomeAssistant, sensor_manager, offset_engine, config: Dict[str, Any]):
        """Initialize HumidityMonitor with dependencies and configuration.
        
        Args:
            hass: Home Assistant instance
            sensor_manager: SensorManager instance for reading sensor data
            offset_engine: OffsetEngine instance for ML impact
            config: Configuration dictionary with threshold overrides
        """
        self._hass = hass
        self._sensor_manager = sensor_manager
        self._offset_engine = offset_engine
        self._config = config
        self._last_values: Dict[str, float] = {}
        self._thresholds = self._init_thresholds(config)
        
        # Initialize buffer and aggregator for data persistence
        self._buffer = HumidityBuffer(hours=config.get("buffer_hours", 24))
        self._aggregator = HumidityAggregator()
        self._daily_aggregates: Dict[str, Any] = {}

    def _init_thresholds(self, config: Dict[str, Any]) -> Dict[str, float]:
        """Initialize configurable thresholds.
        
        Args:
            config: Configuration dictionary with optional threshold overrides
            
        Returns:
            Dictionary of threshold names to values
        """
        return {
            'humidity_change': config.get('humidity_change_threshold', 2.0),  # 2%
            'heat_index_warning': config.get('heat_index_warning', 26.0),  # 26°C
            'dew_point_warning': config.get('dew_point_warning', 2.0),  # 2°C
            'differential_significant': config.get('differential_significant', 25.0)  # 25%
        }

    def check_triggers(self, new_values: Dict[str, Any]) -> List[str]:
        """Check if any thresholds are crossed.
        
        Args:
            new_values: Dictionary of current sensor values
            
        Returns:
            List of triggered event types
        """
        triggered_events = []
        
        # Skip if no previous values for comparison (first reading)
        if not self._last_values:
            return triggered_events
        
        # Check humidity change threshold
        if self._check_humidity_change(new_values):
            triggered_events.append('humidity_change')
        
        # Check heat index warning threshold
        if self._check_heat_index_warning(new_values):
            triggered_events.append('heat_index_warning')
        
        # Check dew point warning threshold
        if self._check_dew_point_warning(new_values):
            triggered_events.append('dew_point_warning')
        
        # Check humidity differential threshold
        if self._check_differential_significant(new_values):
            triggered_events.append('differential_significant')
            
        return triggered_events

    def _check_humidity_change(self, new_values: Dict[str, Any]) -> bool:
        """Check for significant humidity change.
        
        Args:
            new_values: Current sensor values
            
        Returns:
            True if humidity change exceeds threshold
        """
        current = new_values.get('indoor_humidity')
        previous = self._last_values.get('indoor_humidity')
        
        if current is None or previous is None:
            return False
            
        change = abs(current - previous)
        return change >= self._thresholds['humidity_change']

    def _check_heat_index_warning(self, new_values: Dict[str, Any]) -> bool:
        """Check for heat index warning threshold.
        
        Args:
            new_values: Current sensor values
            
        Returns:
            True if heat index exceeds warning threshold
        """
        current = new_values.get('heat_index')
        previous = self._last_values.get('heat_index')
        
        if current is None:
            return False
        
        # Only trigger if crossing threshold from below
        if previous is not None and previous >= self._thresholds['heat_index_warning']:
            return False
            
        return current >= self._thresholds['heat_index_warning']

    def _check_dew_point_warning(self, new_values: Dict[str, Any]) -> bool:
        """Check for dew point warning (dew point approaching temperature).
        
        Args:
            new_values: Current sensor values
            
        Returns:
            True if dew point is within warning threshold of temperature
        """
        temp = new_values.get('indoor_temp')
        dew_point = new_values.get('indoor_dew_point')
        
        if temp is None or dew_point is None:
            return False
            
        # Check if dew point is within threshold of temperature
        delta = temp - dew_point
        return delta <= self._thresholds['dew_point_warning']

    def _check_differential_significant(self, new_values: Dict[str, Any]) -> bool:
        """Check for significant humidity differential change.
        
        Args:
            new_values: Current sensor values
            
        Returns:
            True if humidity differential exceeds threshold
        """
        current = new_values.get('humidity_differential')
        previous = self._last_values.get('humidity_differential')
        
        if current is None:
            return False
        
        # Trigger if differential exceeds threshold
        if abs(current) >= self._thresholds['differential_significant']:
            # Only trigger if wasn't already above threshold
            if previous is None or abs(previous) < self._thresholds['differential_significant']:
                return True
                
        return False

    async def async_update(self) -> Dict[str, Any]:
        """Process updates and return triggered events.
        
        Returns:
            Dictionary containing triggered events and updated values
        """
        # Get current sensor values
        new_values = {
            'indoor_humidity': self._sensor_manager.get_indoor_humidity(),
            'outdoor_humidity': self._sensor_manager.get_outdoor_humidity(),
        }
        
        # Check for triggered events
        triggered_events = self.check_triggers(new_values)
        
        # Update last values for next comparison
        self._last_values.update({k: v for k, v in new_values.items() if v is not None})
        
        return {
            'triggered_events': triggered_events,
            'new_values': new_values
        }

    async def async_get_sensor_data(self) -> Dict[str, Any]:
        """Get current sensor data for all humidity sensor entities.
        
        Returns:
            Dictionary containing current humidity values and calculated derivatives
        """
        # Get raw humidity values
        indoor_humidity = self._sensor_manager.get_indoor_humidity() 
        outdoor_humidity = self._sensor_manager.get_outdoor_humidity()
        
        # Get temperature values for calculations
        indoor_temp = self._sensor_manager.get_room_temperature()
        outdoor_temp = self._sensor_manager.get_outdoor_temperature()
        
        # Calculate differential if both humidity sensors available
        differential = None
        if indoor_humidity is not None and outdoor_humidity is not None:
            differential = indoor_humidity - outdoor_humidity
            
        # Calculate derived values
        heat_index = self._calculate_heat_index(indoor_temp, indoor_humidity)
        indoor_dew_point = self._calculate_dew_point(indoor_temp, indoor_humidity)
        outdoor_dew_point = self._calculate_dew_point(outdoor_temp, outdoor_humidity)
        absolute_humidity = self._calculate_absolute_humidity(indoor_temp, indoor_humidity)
        
        # Get ML impact metrics
        ml_humidity_offset = self._get_ml_humidity_offset()
        ml_humidity_confidence = self._get_ml_humidity_confidence() 
        ml_humidity_weight = self._get_ml_humidity_weight()
            
        # Determine sensor status
        sensor_status = self._determine_sensor_status(indoor_humidity, outdoor_humidity)
        
        # Determine comfort level
        comfort_level = self._determine_comfort_level(indoor_humidity, heat_index)
        
        return {
            'indoor_humidity': indoor_humidity,
            'outdoor_humidity': outdoor_humidity,
            'humidity_differential': differential,
            'heat_index': heat_index,
            'dew_point_indoor': indoor_dew_point,
            'dew_point_outdoor': outdoor_dew_point,
            'absolute_humidity': absolute_humidity,
            'ml_humidity_offset': ml_humidity_offset,
            'ml_humidity_confidence': ml_humidity_confidence,
            'ml_humidity_weight': ml_humidity_weight,
            'humidity_sensor_status': sensor_status,
            'humidity_comfort_level': comfort_level
        }
    
    def _get_ml_humidity_offset(self) -> Optional[float]:
        """Get humidity's contribution to ML offset prediction.
        
        Returns:
            Humidity contribution in degrees Celsius, or None if ML not available
        """
        if self._offset_engine is None:
            return 0.0
            
        try:
            if hasattr(self._offset_engine, 'get_feature_contribution'):
                return self._offset_engine.get_feature_contribution("humidity")
            else:
                # Mock implementation for now - OffsetEngine doesn't have this method yet
                return 0.0
        except Exception as e:
            _LOGGER.debug(f"Error getting ML humidity offset: {e}")
            return 0.0
    
    def _get_ml_humidity_confidence(self) -> Optional[float]:
        """Get humidity's impact on ML prediction confidence.
        
        Returns:
            Confidence impact as percentage change, or None if ML not available
        """
        if self._offset_engine is None:
            return 0.0
            
        try:
            if hasattr(self._offset_engine, 'get_confidence_impact'):
                return self._offset_engine.get_confidence_impact("humidity")
            else:
                # Mock implementation for now - OffsetEngine doesn't have this method yet
                return 0.0
        except Exception as e:
            _LOGGER.debug(f"Error getting ML humidity confidence impact: {e}")
            return 0.0
    
    def _get_ml_humidity_weight(self) -> Optional[float]:
        """Get humidity's relative importance in ML model.
        
        Returns:
            Feature importance as percentage (0-100), or None if ML not available
        """
        if self._offset_engine is None:
            return 0.0
            
        try:
            if hasattr(self._offset_engine, 'get_feature_importance'):
                return self._offset_engine.get_feature_importance("humidity")
            else:
                # Mock implementation for now - OffsetEngine doesn't have this method yet
                return 0.0
        except Exception as e:
            _LOGGER.debug(f"Error getting ML humidity feature importance: {e}")
            return 0.0
    
    def _calculate_heat_index(self, temp_c: Optional[float], humidity: Optional[float]) -> Optional[float]:
        """Calculate heat index using simplified Steadman formula for Celsius.
        
        Args:
            temp_c: Temperature in degrees Celsius
            humidity: Relative humidity percentage (0-100)
            
        Returns:
            Heat index in degrees Celsius, or None if inputs are invalid
        """
        if temp_c is None or humidity is None:
            return None
            
        # Only calculate heat index for warm conditions where it's meaningful
        if temp_c < 20.0 or humidity < 40.0:
            return temp_c  # Return regular temperature when heat index not applicable
            
        # Simplified heat index formula for Celsius (adapted from Steadman)
        # HI = T + 0.348 * RH - 0.70 * WS - 4.25
        # Where WS (wind speed) = 0 for indoor conditions
        heat_index = temp_c + (0.348 * humidity) - 4.25
        
        return round(heat_index, 1)
    
    def _calculate_dew_point(self, temp_c: Optional[float], humidity: Optional[float]) -> Optional[float]:
        """Calculate dew point using Magnus formula.
        
        Args:
            temp_c: Temperature in degrees Celsius
            humidity: Relative humidity percentage (0-100)
            
        Returns:
            Dew point in degrees Celsius, or None if inputs are invalid
        """
        if temp_c is None or humidity is None:
            return None
            
        if humidity <= 0 or humidity > 100:
            return None
            
        # Magnus formula constants
        b = 17.62
        c = 243.12
        
        # Avoid math domain error for log
        if humidity <= 0:
            return None
            
        # Calculate gamma
        import math
        gamma = (b * temp_c) / (c + temp_c) + math.log(humidity / 100.0)
        
        # Calculate dew point
        dew_point = (c * gamma) / (b - gamma)
        
        return round(dew_point, 1)
    
    def _determine_sensor_status(self, indoor: Optional[float], outdoor: Optional[float]) -> str:
        """Determine sensor status based on availability.
        
        Args:
            indoor: Indoor humidity value
            outdoor: Outdoor humidity value
            
        Returns:
            Status string: "Both", "Indoor Only", "Outdoor Only", or "None"
        """
        if indoor is not None and outdoor is not None:
            return "Both"
        elif indoor is not None:
            return "Indoor Only"
        elif outdoor is not None:
            return "Outdoor Only"
        else:
            return "None"
    
    def _determine_comfort_level(self, humidity: Optional[float], heat_index: Optional[float]) -> str:
        """Determine comfort level based on humidity and heat index.
        
        Args:
            humidity: Indoor humidity percentage
            heat_index: Calculated heat index
            
        Returns:
            Comfort level string
        """
        if humidity is None:
            return "Unknown"
            
        # Check humidity ranges
        if humidity < 30:
            return "Too Dry"
        elif humidity > 60:
            return "Too Humid"
        elif heat_index is not None and heat_index > self._thresholds.get('heat_index_high', 29):
            return "Uncomfortable - High Heat Index"
        elif heat_index is not None and heat_index > self._thresholds.get('heat_index_warning', 26):
            return "Caution - Elevated Heat Index"
        elif 40 <= humidity <= 50:
            return "Optimal"
        else:
            return "Comfortable"
    
    def _calculate_absolute_humidity(self, temp_c: Optional[float], humidity: Optional[float]) -> Optional[float]:
        """Calculate absolute humidity in grams per cubic meter.
        
        Args:
            temp_c: Temperature in degrees Celsius
            humidity: Relative humidity percentage (0-100)
            
        Returns:
            Absolute humidity in g/m³, or None if inputs are invalid
        """
        if temp_c is None or humidity is None:
            return None
            
        if humidity <= 0 or humidity > 100:
            return None
            
        # Buck equation for saturated vapor pressure (in kPa)
        import math
        svp = 0.61121 * math.exp((18.678 - temp_c / 234.5) * (temp_c / (257.14 + temp_c)))
        
        # Actual vapor pressure
        vp = humidity / 100.0 * svp
        
        # Absolute humidity in g/m³ using ideal gas law
        # AH = (vp * Mw) / (R * T)
        # Where: Mw = 18.016 g/mol (molecular weight of water)
        #        R = 8.314 J/(mol·K) (universal gas constant)
        #        T = temperature in Kelvin
        temp_k = temp_c + 273.15
        absolute_humidity = (vp * 1000 * 18.016) / (8.314 * temp_k)
        
        return round(absolute_humidity, 1)

    def serialize_data(self) -> Dict[str, Any]:
        """Serialize buffer and aggregates for persistence.
        
        Returns:
            Dictionary containing buffer events and daily aggregates
        """
        buffer_events = []
        for event in self._buffer._buffer:
            buffer_events.append(event.copy())
        
        return {
            "version": "1.0",
            "humidity_24h_buffer": buffer_events,
            "humidity_daily_aggregates": self._daily_aggregates.copy(),
            "last_values": self._last_values.copy(),
            "thresholds": self._thresholds.copy(),
        }
    
    def deserialize_data(self, data: Dict[str, Any]) -> bool:
        """Deserialize and restore buffer and aggregates from persistence.
        
        Args:
            data: Previously serialized data
            
        Returns:
            True if data was successfully restored, False otherwise
        """
        try:
            if not isinstance(data, dict):
                _LOGGER.warning("Invalid humidity data format: expected dict, got %s", type(data))
                return False
            
            version = data.get("version", "unknown")
            _LOGGER.debug("Deserializing humidity data version %s", version)
            
            # Restore buffer events
            buffer_events = data.get("humidity_24h_buffer", [])
            if isinstance(buffer_events, list):
                self._buffer._buffer.clear()
                for event in buffer_events:
                    if isinstance(event, dict):
                        self._buffer._buffer.append(event.copy())
                _LOGGER.debug("Restored %d humidity buffer events", len(buffer_events))
            
            # Restore daily aggregates
            daily_aggregates = data.get("humidity_daily_aggregates", {})
            if isinstance(daily_aggregates, dict):
                self._daily_aggregates = daily_aggregates.copy()
                _LOGGER.debug("Restored humidity daily aggregates for %d days", len(daily_aggregates))
            
            # Restore last values
            last_values = data.get("last_values", {})
            if isinstance(last_values, dict):
                self._last_values = last_values.copy()
                _LOGGER.debug("Restored humidity last values: %s", last_values)
            
            # Restore thresholds (but don't override current config)
            stored_thresholds = data.get("thresholds", {})
            if isinstance(stored_thresholds, dict):
                _LOGGER.debug("Stored thresholds: %s (current: %s)", stored_thresholds, self._thresholds)
            
            return True
            
        except Exception as e:
            _LOGGER.warning("Error deserializing humidity data: %s", e, exc_info=True)
            return False
    
    def add_event_to_buffer(self, event_data: Dict[str, Any]) -> None:
        """Add event to the 24-hour buffer for persistence.
        
        Args:
            event_data: Event data to store in buffer
        """
        self._buffer.add_event(event_data)
    
    def get_daily_aggregate(self, date_str: str) -> Optional[Dict[str, Any]]:
        """Get daily aggregate for a specific date.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            Daily aggregate data or None if not found
        """
        return self._daily_aggregates.get(date_str)
    
    def update_daily_aggregate(self, date_str: str, aggregate_data: Dict[str, Any]) -> None:
        """Update daily aggregate for a specific date.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            aggregate_data: Aggregate statistics for the date
        """
        self._daily_aggregates[date_str] = aggregate_data
        
        # Keep only recent aggregates (e.g., last 90 days)
        max_days = self._config.get("aggregate_days", 90)
        if len(self._daily_aggregates) > max_days:
            # Remove oldest entries
            sorted_dates = sorted(self._daily_aggregates.keys())
            for old_date in sorted_dates[:-max_days]:
                del self._daily_aggregates[old_date]
    
    def get_buffer_data(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get recent buffer data for analysis.
        
        Args:
            minutes: Time window in minutes
            
        Returns:
            List of recent events
        """
        return self._buffer.get_recent(minutes)


class HumidityBuffer:
    """Efficient 24-hour circular buffer for humidity events."""
    
    def __init__(self, hours: int = 24):
        """Initialize buffer with specified capacity.
        
        Args:
            hours: Number of hours to store (default: 24)
                  Uses 5-minute granularity (12 entries per hour)
        """
        self._buffer = deque(maxlen=hours * 12)  # 5-min granularity
        self._hours = hours
        
    def add_event(self, event: dict) -> None:
        """Add timestamped event to buffer.
        
        Args:
            event: Event dictionary to store
                  Timestamp will be added automatically in ISO format
        """
        # Create copy to avoid modifying original
        event_with_timestamp = event.copy()
        event_with_timestamp["timestamp"] = datetime.now().isoformat()
        self._buffer.append(event_with_timestamp)
        
    def get_recent(self, minutes: int = 60) -> List[dict]:
        """Get events from last N minutes.
        
        Args:
            minutes: Time window in minutes (default: 60)
            
        Returns:
            List of events within the time window, chronologically ordered
        """
        if not self._buffer:
            return []
            
        cutoff = datetime.now() - timedelta(minutes=minutes)
        
        recent_events = []
        for event in self._buffer:
            # Use datetime from the stdlib directly to avoid mock conflicts
            from datetime import datetime as dt
            event_time = dt.fromisoformat(event["timestamp"])
            if event_time > cutoff:
                recent_events.append(event)
                
        return recent_events


class HumidityAggregator:
    """Calculate daily statistics for humidity data."""
    
    def calculate_daily_stats(self, events: Optional[List[dict]]) -> dict:
        """Calculate min/max/avg statistics for the day.
        
        Args:
            events: List of event dictionaries
            
        Returns:
            Statistics dictionary with indoor/outdoor/ml_impact/comfort_time_percent
            Returns empty dict if events is None or empty
        """
        if not events:
            return {}
            
        indoor_values = [e["indoor"] for e in events if "indoor" in e and e["indoor"] is not None]
        outdoor_values = [e["outdoor"] for e in events if "outdoor" in e and e["outdoor"] is not None]
        
        if not indoor_values and not outdoor_values:
            # No data to aggregate
            return {}
            
        result = {}
        
        if indoor_values:
            result["indoor"] = {
                "min": min(indoor_values),
                "max": max(indoor_values),
                "avg": sum(indoor_values) / len(indoor_values)
            }
        
        if outdoor_values:
            result["outdoor"] = {
                "min": min(outdoor_values),
                "max": max(outdoor_values),
                "avg": sum(outdoor_values) / len(outdoor_values)
            }
            
        # Always include ML impact and comfort percentage if we have any data
        result["ml_impact"] = self._calculate_ml_averages(events)
        result["comfort_time_percent"] = self._calculate_comfort_percentage(events)
        
        return result
        
    def _calculate_ml_averages(self, events: List[dict]) -> dict:
        """Calculate average ML impact metrics.
        
        Args:
            events: List of event dictionaries
            
        Returns:
            Dict with avg_offset and avg_confidence
        """
        offset_values = [e["ml_offset_impact"] for e in events 
                        if "ml_offset_impact" in e and e["ml_offset_impact"] is not None]
        confidence_values = [e["ml_confidence_impact"] for e in events 
                           if "ml_confidence_impact" in e and e["ml_confidence_impact"] is not None]
        
        return {
            "avg_offset": sum(offset_values) / len(offset_values) if offset_values else 0.0,
            "avg_confidence": sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
        }
        
    def _calculate_comfort_percentage(self, events: List[dict]) -> float:
        """Calculate percentage of time in comfort zone.
        
        Args:
            events: List of event dictionaries
            
        Returns:
            Percentage (0-100) of events in comfort zone
        """
        if not events:
            return 0.0
            
        comfort_events = 0
        total_events = 0
        
        for event in events:
            total_events += 1
            
            # Check if comfort_zone indicator exists
            if "comfort_zone" in event:
                if event["comfort_zone"]:
                    comfort_events += 1
            elif "indoor" in event and event["indoor"] is not None:
                # Calculate comfort zone from indoor humidity (30-60% range)
                indoor = event["indoor"]
                if 30.0 <= indoor <= 60.0:
                    comfort_events += 1
                    
        if total_events == 0:
            return 0.0
            
        return (comfort_events / total_events) * 100.0


class HumidityLogger:
    """Structured diagnostic logging for humidity monitoring events.
    
    Provides contextual logging across different categories:
    - smart_climate.humidity: General humidity monitoring
    - smart_climate.humidity.ml: ML impact calculations
    - smart_climate.humidity.comfort: Comfort assessments
    """
    
    def __init__(self, level: str = "DEBUG"):
        """Initialize humidity logger with specified level.
        
        Args:
            level: Log level (default "DEBUG")
        """
        self._logger = logging.getLogger("smart_climate.humidity")
        self._ml_logger = logging.getLogger("smart_climate.humidity.ml")
        self._comfort_logger = logging.getLogger("smart_climate.humidity.comfort")
    
    def log_humidity_change(self, indoor_old: float, indoor_new: float, 
                           context: Dict[str, Any]) -> None:
        """Log humidity change with contextual information.
        
        Args:
            indoor_old: Previous indoor humidity percentage
            indoor_new: New indoor humidity percentage
            context: Context dict with keys: outdoor, heat_index, ml_offset, 
                    ml_conf_old, ml_conf_new
        """
        msg = (f"Indoor humidity changed: {indoor_old}% → {indoor_new}% "
               f"(outdoor: {context['outdoor']}%, heat index: {context['heat_index']}°C, "
               f"ML impact: {context['ml_offset']:+.1f}°C offset, "
               f"confidence: {context['ml_conf_old']}%→{context['ml_conf_new']}%)")
        self._logger.debug(msg)
    
    def log_ml_impact(self, message: str) -> None:
        """Log ML-specific events using the ML logger.
        
        Args:
            message: ML impact message to log
        """
        self._ml_logger.debug(message)
    
    def log_comfort_event(self, message: str) -> None:
        """Log comfort transition events using the comfort logger.
        
        Args:
            message: Comfort event message to log
        """
        self._comfort_logger.info(message)