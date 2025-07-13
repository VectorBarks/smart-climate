"""Data models for Smart Climate Control integration."""

from dataclasses import dataclass
from datetime import time, datetime
from typing import Optional


@dataclass
class OffsetResult:
    """Result of offset calculation."""
    offset: float  # Calculated offset in degrees
    clamped: bool  # Whether offset was clamped to limits
    reason: str    # Human-readable reason for offset
    confidence: float  # 0.0 to 1.0 confidence in calculation


@dataclass
class OffsetInput:
    """Input parameters for offset calculation."""
    ac_internal_temp: float
    room_temp: float
    outdoor_temp: Optional[float]
    mode: str
    power_consumption: Optional[float]
    time_of_day: time
    day_of_week: int


@dataclass
class ModeAdjustments:
    """Adjustments to apply for current mode."""
    temperature_override: Optional[float]  # Fixed temp for away mode
    offset_adjustment: float  # Additional offset for night mode
    update_interval_override: Optional[int]  # Different update frequency
    boost_offset: float  # Extra cooling for boost mode


@dataclass
class SmartClimateData:
    """Data structure for coordinator updates.
    
    Contains all data needed for Smart Climate coordination including sensor readings,
    calculated offsets, mode adjustments, and startup state tracking.
    
    Args:
        room_temp: Current room temperature from sensor
        outdoor_temp: Current outdoor temperature (if available)
        power: Current power consumption (if available)
        calculated_offset: Calculated temperature offset for AC control
        mode_adjustments: Mode-specific adjustments to apply
        is_startup_calculation: Flag indicating if this is a startup calculation.
            When True, the climate entity will apply the calculated offset to the AC
            even if the offset change is below the normal update threshold. This ensures
            that learned temperature adjustments are applied immediately when the
            integration starts up, rather than waiting for the next significant change.
    """
    room_temp: Optional[float]
    outdoor_temp: Optional[float]
    power: Optional[float]
    calculated_offset: float
    mode_adjustments: ModeAdjustments
    is_startup_calculation: bool = False


@dataclass
class Forecast:
    """Represents a single point in a weather forecast."""
    datetime: datetime
    temperature: float
    condition: Optional[str] = None


@dataclass
class ActiveStrategy:
    """Represents a strategy that is currently active."""
    name: str
    adjustment: float
    end_time: datetime