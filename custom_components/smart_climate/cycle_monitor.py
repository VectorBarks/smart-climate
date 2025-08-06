"""ABOUTME: CycleMonitor tracks HVAC cycle timing and health for thermal efficiency system.
Enforces minimum on/off times and detects short cycling issues."""

import time
from collections import deque
from typing import Tuple


class CycleMonitor:
    """Monitor HVAC cycle timing and health for thermal efficiency system.
    
    Tracks cycle timing to enforce minimum on/off times and detect short cycling
    issues that indicate system problems or thermal efficiency opportunities.
    """
    
    def __init__(self, min_off_time: int = 600, min_on_time: int = 300) -> None:
        """Initialize CycleMonitor with timing constraints.
        
        Args:
            min_off_time: Minimum off time in seconds (default: 600 = 10 minutes)
            min_on_time: Minimum on time in seconds (default: 300 = 5 minutes)
        """
        self._min_off_time = min_off_time
        self._min_on_time = min_on_time
        self._cycle_history = deque(maxlen=50)  # Store up to 50 cycles
        self._last_on_time = None
        self._last_off_time = None
    
    def can_turn_on(self) -> bool:
        """Check if HVAC system can turn on based on minimum off time.
        
        Returns:
            True if system can turn on (no previous off time or sufficient time passed)
        """
        if self._last_off_time is None:
            return True
        
        time_since_off = time.time() - self._last_off_time
        return time_since_off >= self._min_off_time
    
    def can_turn_off(self) -> bool:
        """Check if HVAC system can turn off based on minimum on time.
        
        Returns:
            True if system can turn off (no previous on time or sufficient time passed)
        """
        if self._last_on_time is None:
            return True
        
        time_since_on = time.time() - self._last_on_time
        return time_since_on >= self._min_on_time
    
    def record_cycle(self, duration: int, is_on: bool) -> None:
        """Record a completed cycle in the history.
        
        Args:
            duration: Duration of the cycle in seconds
            is_on: True if this was an ON cycle, False if OFF cycle
        """
        current_time = time.time()
        
        # Update last transition time
        if is_on:
            self._last_on_time = current_time
        else:
            self._last_off_time = current_time
        
        # Add to history (deque automatically limits to maxlen=50)
        self._cycle_history.append((duration, is_on, current_time))
    
    def get_average_cycle_duration(self) -> Tuple[float, float]:
        """Calculate average duration of on and off cycles.
        
        Returns:
            Tuple of (average_on_duration, average_off_duration) in seconds
        """
        if not self._cycle_history:
            return 0.0, 0.0
        
        on_cycles = [duration for duration, is_on, _ in self._cycle_history if is_on]
        off_cycles = [duration for duration, is_on, _ in self._cycle_history if not is_on]
        
        avg_on = sum(on_cycles) / len(on_cycles) if on_cycles else 0.0
        avg_off = sum(off_cycles) / len(off_cycles) if off_cycles else 0.0
        
        return avg_on, avg_off
    
    def needs_adjustment(self) -> bool:
        """Check if cycle patterns indicate need for thermal efficiency adjustment.
        
        Returns:
            True if average cycle durations are below 7 minutes (420 seconds),
            indicating potential short cycling issues
        """
        if not self._cycle_history:
            return False
        
        avg_on, avg_off = self.get_average_cycle_duration()
        min_healthy_duration = 420  # 7 minutes in seconds
        
        # Either on or off cycles averaging less than 7 minutes indicates issues
        if avg_on > 0 and avg_on < min_healthy_duration:
            return True
        if avg_off > 0 and avg_off < min_healthy_duration:
            return True
        
        return False