"""
ABOUTME: Thermal model v1.5.3 test fixtures for enhanced probe history testing.
Provides fixture generators for ProbeResult objects with time manipulation and validation.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional
import random

from custom_components.smart_climate.thermal_models import ProbeResult


def create_probe_result(
    tau_value: float,
    confidence: float,
    age_days: float = 0,
    outdoor_temp: Optional[float] = None,
    duration: Optional[int] = None,
    fit_quality: Optional[float] = None,
    aborted: bool = False
) -> ProbeResult:
    """
    Create a ProbeResult with specified parameters and optional time offset.
    
    Args:
        tau_value: Thermal time constant in minutes
        confidence: Confidence level (0.0-1.0)
        age_days: How many days ago this probe was created (default: 0 = now)
        outdoor_temp: Outdoor temperature during probe (optional)
        duration: Probe duration in seconds (optional, uses reasonable default)
        fit_quality: Quality of exponential fit (optional, uses reasonable default)
        aborted: Whether probe was aborted early
        
    Returns:
        ProbeResult instance with specified timestamp
    """
    # Apply validation/clamping
    confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
    tau_value = max(30.0, min(300.0, tau_value))  # Physical limits
    
    # Generate reasonable defaults
    if duration is None:
        duration = random.randint(600, 3600)  # 10-60 minutes
    
    if fit_quality is None:
        # Correlate with confidence for realism
        fit_quality = max(0.1, min(0.95, confidence * random.uniform(0.8, 1.2)))
    
    # Calculate timestamp based on age
    timestamp = datetime.now(timezone.utc) - timedelta(days=age_days)
    
    return ProbeResult(
        tau_value=tau_value,
        confidence=confidence,
        duration=duration,
        fit_quality=fit_quality,
        aborted=aborted,
        timestamp=timestamp,
        outdoor_temp=outdoor_temp
    )


def create_probe_sequence(
    count: int,
    start_days_ago: float,
    outdoor_temps: Optional[List[float]] = None,
    tau_base: float = 90.0,
    tau_variation: float = 20.0,
    confidence_base: float = 0.8,
    confidence_variation: float = 0.15
) -> List[ProbeResult]:
    """
    Create a time-sequenced list of ProbeResult objects.
    
    Args:
        count: Number of probes to create
        start_days_ago: How many days ago the oldest probe should be
        outdoor_temps: Optional list of outdoor temperatures (must match count)
        tau_base: Base tau value for variation
        tau_variation: Maximum variation in tau values (±)
        confidence_base: Base confidence for variation  
        confidence_variation: Maximum variation in confidence (±)
        
    Returns:
        List of ProbeResult objects in temporal order (oldest first)
    """
    if outdoor_temps and len(outdoor_temps) != count:
        raise ValueError(f"outdoor_temps length ({len(outdoor_temps)}) must match count ({count})")
    
    probes = []
    
    # Calculate time spacing between probes
    if count > 1:
        time_span_days = start_days_ago
        interval_days = time_span_days / (count - 1)
    else:
        interval_days = 0
    
    for i in range(count):
        # Calculate age for this probe (oldest first)
        age_days = start_days_ago - (i * interval_days)
        
        # Generate varied tau and confidence values
        tau = tau_base + random.uniform(-tau_variation, tau_variation)
        confidence = confidence_base + random.uniform(-confidence_variation, confidence_variation)
        
        # Get outdoor temp if provided
        outdoor_temp = outdoor_temps[i] if outdoor_temps else None
        
        probe = create_probe_result(
            tau_value=tau,
            confidence=confidence,
            age_days=age_days,
            outdoor_temp=outdoor_temp
        )
        
        probes.append(probe)
    
    return probes


def create_legacy_probe(
    tau_value: float,
    confidence: float,
    age_days: float = 0,
    duration: Optional[int] = None
) -> ProbeResult:
    """
    Create a legacy probe result without outdoor_temp field.
    
    This simulates probes from before v1.5.3 that didn't capture outdoor temperature.
    
    Args:
        tau_value: Thermal time constant in minutes
        confidence: Confidence level (0.0-1.0)
        age_days: How many days ago this probe was created
        duration: Probe duration in seconds (optional)
        
    Returns:
        ProbeResult with outdoor_temp=None
    """
    return create_probe_result(
        tau_value=tau_value,
        confidence=confidence,
        age_days=age_days,
        outdoor_temp=None,  # Legacy probes don't have outdoor temp
        duration=duration
    )