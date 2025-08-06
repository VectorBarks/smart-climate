"""
ABOUTME: User preference system for thermal efficiency with asymmetric heating/cooling behavior
Implements comfort band adjustments based on preference level and weather conditions
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PreferenceLevel(Enum):
    """Preference levels for thermal efficiency behavior."""
    MAX_COMFORT = "max_comfort"
    COMFORT_PRIORITY = "comfort_priority"
    BALANCED = "balanced"
    SAVINGS_PRIORITY = "savings_priority"
    MAX_SAVINGS = "max_savings"


@dataclass
class UserPreferences:
    """User preferences for thermal efficiency with asymmetric heating/cooling adjustments."""
    
    level: PreferenceLevel
    comfort_band: float
    confidence_threshold: float
    probe_drift: float
    extreme_heat_start: float = 30.0
    extreme_cold_start: float = 0.0
    
    def get_adjusted_band(self, outdoor_temp: Optional[float], hvac_mode: Optional[str]) -> float:
        """
        Get adjusted comfort band based on outdoor temperature and HVAC mode.
        
        Implements asymmetric behavior:
        - Cooling mode: Gradually tighten bands in extreme heat (30-35°C)
        - Heating mode: Preference-dependent behavior in cold weather
          - MAX_COMFORT: Tighten bands for comfort
          - BALANCED/others: No change
          - MAX_SAVINGS: Widen bands for savings
        
        Args:
            outdoor_temp: Current outdoor temperature in °C
            hvac_mode: "heat", "cool", or other
            
        Returns:
            Adjusted comfort band in °C
        """
        # Handle invalid inputs
        if outdoor_temp is None or hvac_mode is None:
            return self.comfort_band
        
        base_band = self.comfort_band
        
        # Cooling mode: extreme heat adjustment
        if hvac_mode == "cool" and outdoor_temp >= self.extreme_heat_start:
            # Gradually tighten bands as temperature increases from 30-35°C
            heat_factor = min(1.0, (outdoor_temp - self.extreme_heat_start) / 5.0)
            # Tighten up to 30% at maximum heat
            adjustment = base_band * (1.0 - heat_factor * 0.3)
            return adjustment
        
        # Heating mode: preference-based cold weather adjustment
        elif hvac_mode == "heat" and outdoor_temp <= self.extreme_cold_start:
            # Cold factor: 0-1 over range from 0°C to -10°C
            cold_factor = min(1.0, (self.extreme_cold_start - outdoor_temp) / 10.0)
            
            if self.level == PreferenceLevel.MAX_COMFORT:
                # Tighten bands up to 40% for comfort
                adjustment = base_band * (1.0 - cold_factor * 0.4)
                return adjustment
            elif self.level == PreferenceLevel.MAX_SAVINGS:
                # Widen bands up to 50% for savings
                adjustment = base_band * (1.0 + cold_factor * 0.5)
                return adjustment
            # BALANCED, COMFORT_PRIORITY, SAVINGS_PRIORITY: no change
        
        # No adjustment for normal weather or other modes
        return base_band