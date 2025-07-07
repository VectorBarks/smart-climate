"""Data models for Smart Climate Control integration."""

from dataclasses import dataclass
from datetime import time
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
    """Data structure for coordinator updates."""
    room_temp: Optional[float]
    outdoor_temp: Optional[float]
    power: Optional[float]
    calculated_offset: float
    mode_adjustments: ModeAdjustments