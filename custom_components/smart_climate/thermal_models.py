"""ABOUTME: Thermal efficiency models and enums for Smart Climate Control.
Data structures for thermal state machine, probe results, and user preferences."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


@dataclass
class ThermalConstants:
    """Thermal constants for passive thermal model and state machine.
    
    Defines time constants for thermal behavior and minimum cycle times
    to prevent excessive HVAC cycling.
    
    Args:
        tau_cooling: Time constant for passive cooling (seconds)
        tau_warming: Time constant for passive warming (seconds)
        min_off_time: Minimum time AC must stay off (seconds)
        min_on_time: Minimum time AC must stay on (seconds)
        priming_duration: Duration of priming phase (seconds)
        recovery_duration: Duration of recovery transitions (seconds)
    """
    tau_cooling: float = 90.0      # 1.5 minutes - how fast temperature drops when AC off
    tau_warming: float = 150.0     # 2.5 minutes - how fast temperature rises when AC off  
    min_off_time: int = 600        # 10 minutes minimum off time
    min_on_time: int = 300         # 5 minutes minimum on time
    priming_duration: int = 86400  # 24 hours for initial learning
    recovery_duration: int = 1800  # 30 minutes for mode change recovery


@dataclass(frozen=True)
class ProbeResult:
    """Result of thermal time constant probing.
    
    Contains the measured thermal time constant and quality metrics
    from active thermal probing experiments.
    
    Args:
        tau_value: Measured thermal time constant (minutes)
        confidence: Statistical confidence in measurement (0.0-1.0)
        duration: Duration of probe experiment (seconds)
        fit_quality: Quality of exponential fit (0.0-1.0)
        aborted: Whether the probe was aborted early
        timestamp: When the probe was created (UTC)
        outdoor_temp: Outdoor temperature during probe (°C) - v1.5.3 enhancement
    """
    tau_value: float
    confidence: float
    duration: int
    fit_quality: float
    aborted: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    outdoor_temp: Optional[float] = field(default=None)


class ThermalState(Enum):
    """Thermal efficiency state machine states.
    
    Defines the six states of the thermal efficiency state machine
    as specified in the architecture document.
    """
    PRIMING = "priming"           # Initial learning phase (24-48 hours)
    DRIFTING = "drifting"         # AC off, passive temperature drift
    CORRECTING = "correcting"     # AC on, returning from boundary
    RECOVERY = "recovery"         # Gradual transition after mode changes
    PROBING = "probing"           # Active learning with user consent
    CALIBRATING = "calibrating"   # Daily precise offset calibration


class PreferenceLevel(Enum):
    """User preference levels for comfort vs energy savings.
    
    Defines five levels from maximum comfort to maximum savings,
    affecting comfort band sizes and thermal efficiency aggressiveness.
    """
    MAX_COMFORT = "max_comfort"           # Tightest comfort bands
    COMFORT_PRIORITY = "comfort_priority" # Comfort-focused with some savings
    BALANCED = "balanced"                 # Equal comfort and savings priority  
    SAVINGS_PRIORITY = "savings_priority" # Savings-focused with acceptable comfort
    MAX_SAVINGS = "max_savings"           # Maximum energy savings


@dataclass
class PassiveObservation:
    """Passive observation data for continuous tau refinement.
    
    Contains measurements from passive temperature drift observations
    used for continuous refinement of thermal time constants between
    active probe sessions.
    
    Args:
        tau_measured: Measured thermal time constant from passive observation (minutes)
        fit_quality: Quality of curve fit (0.0-1.0, where 1.0 is perfect fit)
        duration_seconds: Duration of the passive observation (seconds)
        is_cooling: True if observation was during cooling, False for warming
        outdoor_temp: Outdoor temperature during observation (°C), optional
    """
    tau_measured: float
    fit_quality: float  # 0.0 to 1.0
    duration_seconds: int
    is_cooling: bool
    outdoor_temp: Optional[float] = None
