"""ABOUTME: Stability detection for opportunistic thermal calibration.
Tracks AC idle duration and temperature drift to identify stable conditions."""

import logging
from datetime import datetime, timedelta
from collections import deque
from typing import Tuple, Optional, Deque, List, Dict, Any

_LOGGER = logging.getLogger(__name__)


class StabilityDetector:
    """Detects stable conditions suitable for thermal calibration.
    
    Tracks AC state changes and temperature history to identify periods
    where the system is idle long enough with minimal temperature drift
    for accurate calibration measurements.
    
    Args:
        idle_threshold_minutes: Minimum AC idle time required for stability
        drift_threshold: Maximum temperature drift (°C) over 10 minutes
    """

    def __init__(self, idle_threshold_minutes: int = 30, drift_threshold: float = 0.3, 
                 passive_min_drift_minutes: int = 15):
        """Initialize StabilityDetector with configurable thresholds."""
        self._idle_threshold = timedelta(minutes=idle_threshold_minutes)
        self._drift_threshold = drift_threshold
        
        # Track AC state changes
        self._last_ac_state: Optional[str] = None
        self._last_ac_state_change: Optional[datetime] = None
        
        # Temperature history: (timestamp, temperature) tuples
        self._temperature_history: Deque[Tuple[datetime, float]] = deque(maxlen=20)
        
        # Passive learning extensions
        self._history: Deque[Dict[str, Any]] = deque(maxlen=240)  # 4 hours of data
        self._MIN_DRIFT_DURATION_S = passive_min_drift_minutes * 60  # Convert minutes to seconds
        self._last_event_ts = 0.0
        
        _LOGGER.debug("StabilityDetector initialized: idle_threshold=%d min, drift_threshold=%.2f°C",
                     idle_threshold_minutes, drift_threshold)

    def update(self, ac_state: str, room_temp: float) -> None:
        """Update detector with current AC state and room temperature.
        
        Args:
            ac_state: Current AC state ("cooling", "heating", "idle", "off")
            room_temp: Current room temperature in Celsius
        """
        current_time = datetime.now()
        
        # Track AC state changes
        if ac_state != self._last_ac_state:
            _LOGGER.debug("AC state changed: %s -> %s", self._last_ac_state, ac_state)
            self._last_ac_state = ac_state
            self._last_ac_state_change = current_time
        
        # Add temperature to history with timestamp
        self._temperature_history.append((current_time, room_temp))
        
        _LOGGER.debug("Updated stability detector: state=%s, temp=%.1f°C, history_len=%d",
                     ac_state, room_temp, len(self._temperature_history))

    def add_reading(self, timestamp: float, temp: float, hvac_state: str) -> None:
        """Add timestamped temperature and HVAC state reading for passive learning.
        
        Args:
            timestamp: Unix timestamp (seconds)
            temp: Temperature reading (°C) 
            hvac_state: HVAC state ("off", "cooling", "heating", "idle")
        """
        entry = {
            'ts': timestamp,
            'temp': temp,
            'hvac': hvac_state
        }
        self._history.append(entry)
        
        _LOGGER.debug("Added reading: ts=%.1f, temp=%.1f°C, hvac=%s, history_len=%d",
                     timestamp, temp, hvac_state, len(self._history))

    def is_stable_for_calibration(self) -> bool:
        """Check if conditions are stable enough for calibration.
        
        Returns True if:
        1. AC has been idle for at least idle_threshold_minutes
        2. Temperature drift over last 10 minutes is below drift_threshold
        
        Returns:
            True if conditions are stable for calibration
        """
        # Check if we have enough data
        if not self._temperature_history:
            _LOGGER.debug("No temperature history for stability check")
            return False
        
        # Check AC idle duration
        idle_duration = self.get_idle_duration()
        if idle_duration < self._idle_threshold:
            _LOGGER.debug("Insufficient idle time: %s < %s", idle_duration, self._idle_threshold)
            return False
        
        # Check temperature drift
        drift = self.get_temperature_drift()
        if drift > self._drift_threshold:
            _LOGGER.debug("Excessive temperature drift: %.3f°C > %.3f°C", drift, self._drift_threshold)
            return False
        
        _LOGGER.debug("Stable conditions detected: idle=%s, drift=%.3f°C", idle_duration, drift)
        return True

    def get_idle_duration(self) -> timedelta:
        """Get duration since AC last became idle.
        
        Returns:
            Duration since AC entered idle state, or zero if AC is running
        """
        if not self._last_ac_state_change:
            return timedelta(0)
        
        # Only count idle time if currently in idle state
        if self._last_ac_state not in ["idle", "off"]:
            return timedelta(0)
        
        current_time = datetime.now()
        idle_duration = current_time - self._last_ac_state_change
        
        return idle_duration

    def get_temperature_drift(self) -> float:
        """Calculate temperature drift over the last 10 minutes.
        
        Returns maximum temperature change (max - min) within the last
        10 minutes of temperature readings.
        
        Returns:
            Temperature drift in degrees Celsius
        """
        if len(self._temperature_history) == 0:
            return 0.0
        
        if len(self._temperature_history) == 1:
            return 0.0
        
        # Get current time for 10-minute window - use last entry timestamp if available
        if self._temperature_history:
            current_time = self._temperature_history[-1][0]
        else:
            current_time = datetime.now()
        cutoff_time = current_time - timedelta(minutes=10)
        
        # Filter temperatures within 10-minute window
        recent_entries = [
            (timestamp, temp) for timestamp, temp in self._temperature_history
            if timestamp >= cutoff_time
        ]
        
        if len(recent_entries) < 2:
            # Not enough recent data, use all available data
            recent_temps = [temp for _, temp in self._temperature_history]
        else:
            recent_temps = [temp for _, temp in recent_entries]
        
        if len(recent_temps) < 2:
            return 0.0
        
        # Calculate drift as max - min over window
        max_temp = max(recent_temps)
        min_temp = min(recent_temps)
        drift = max_temp - min_temp
        
        _LOGGER.debug("Temperature drift over %d samples: %.3f°C (%.2f - %.2f)",
                     len(recent_temps), drift, max_temp, min_temp)
        
        return drift

    def find_natural_drift_event(self) -> Optional[List[Tuple[float, float]]]:
        """Search history for valid natural drift events (HVAC off transitions).
        
        Looks for cooling->off or heating->off transitions with sufficient data
        and duration (>= 15 minutes) for thermal analysis.
        
        Returns:
            List of (timestamp, temperature) tuples for the off period, or None
            if no valid drift event is found or event already analyzed.
        """
        if len(self._history) < 10:
            _LOGGER.debug("Insufficient history for drift detection: %d entries", len(self._history))
            return None
        
        # Search backwards through history to find transitions
        for i in range(len(self._history) - 1, 0, -1):
            current = self._history[i]
            previous = self._history[i-1]
            
            # Look for cooling->off or heating->off transitions
            if (previous['hvac'] in ['cooling', 'heating'] and 
                current['hvac'] == 'off'):
                
                transition_ts = current['ts']
                
                # Skip if we already analyzed this event
                if transition_ts <= self._last_event_ts:
                    continue
                
                # Collect all consecutive 'off' readings after this transition
                off_data = []
                for j in range(i, len(self._history)):
                    if self._history[j]['hvac'] == 'off':
                        entry = self._history[j]
                        off_data.append((entry['ts'], entry['temp']))
                    else:
                        break
                
                # Check if we have enough data and duration
                if len(off_data) < 10:
                    _LOGGER.debug("Insufficient off data points: %d < 10", len(off_data))
                    continue
                
                # Check duration (last - first timestamp)
                duration = off_data[-1][0] - off_data[0][0]
                if duration < self._MIN_DRIFT_DURATION_S:
                    _LOGGER.debug("Insufficient drift duration: %.1fs < %ds", 
                                 duration, self._MIN_DRIFT_DURATION_S)
                    continue
                
                # Valid drift event found
                self._last_event_ts = transition_ts
                _LOGGER.debug("Found natural drift event: %s->off at ts=%.1f, duration=%.1fs, points=%d",
                             previous['hvac'], transition_ts, duration, len(off_data))
                return off_data
        
        # No valid drift event found
        _LOGGER.debug("No valid natural drift event found")
        return None

    def find_natural_drift_event_priming(self, min_duration_minutes: int = 5) -> Optional[List[Tuple[float, float]]]:
        """Search history for valid natural drift events with shorter duration requirement for PRIMING.
        
        Looks for cooling->off or heating->off transitions with sufficient data
        and shorter duration (>= 5 minutes) for enhanced passive learning during PRIMING.
        
        Args:
            min_duration_minutes: Minimum duration in minutes (default 5 for PRIMING)
        
        Returns:
            List of (timestamp, temperature) tuples for the off period, or None
            if no valid drift event is found or event already analyzed.
        """
        if len(self._history) < 10:
            _LOGGER.debug("Insufficient history for PRIMING drift detection: %d entries", len(self._history))
            return None
        
        min_duration_s = min_duration_minutes * 60
        
        # Search backwards through history to find transitions
        for i in range(len(self._history) - 1, 0, -1):
            current = self._history[i]
            previous = self._history[i-1]
            
            # Look for cooling->off or heating->off transitions
            if (previous['hvac'] in ['cooling', 'heating'] and 
                current['hvac'] == 'off'):
                
                transition_ts = current['ts']
                
                # Skip if we already analyzed this event
                if transition_ts <= self._last_event_ts:
                    continue
                
                # Collect all consecutive 'off' readings after this transition
                off_data = []
                for j in range(i, len(self._history)):
                    if self._history[j]['hvac'] == 'off':
                        entry = self._history[j]
                        off_data.append((entry['ts'], entry['temp']))
                    else:
                        break
                
                # Check if we have enough data and duration (lower requirements for PRIMING)
                if len(off_data) < 6:  # Lower from 10 to 6 data points
                    _LOGGER.debug("Insufficient off data points for PRIMING: %d < 6", len(off_data))
                    continue
                
                # Check duration (last - first timestamp)
                duration = off_data[-1][0] - off_data[0][0]
                if duration < min_duration_s:
                    _LOGGER.debug("Insufficient PRIMING drift duration: %.1fs < %ds", 
                                 duration, min_duration_s)
                    continue
                
                # Valid drift event found
                self._last_event_ts = transition_ts
                _LOGGER.debug("Found PRIMING drift event: %s->off at ts=%.1f, duration=%.1fs, points=%d",
                             previous['hvac'], transition_ts, duration, len(off_data))
                return off_data
        
        # No valid drift event found
        _LOGGER.debug("No valid PRIMING natural drift event found")
        return None