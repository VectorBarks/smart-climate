"""
ABOUTME: Probe validation and calculation helpers for thermal model testing.
Provides utilities for validating probe history integrity and calculating expected weights.
"""

import random
import math
from typing import List, Tuple
from datetime import datetime, timezone

from custom_components.smart_climate.thermal_models import ProbeResult


def validate_probe_history(history: List[ProbeResult], expected_size: int) -> Tuple[bool, str]:
    """
    Validate probe history for integrity and expected characteristics.
    
    Args:
        history: List of ProbeResult objects to validate
        expected_size: Expected number of probes in history
        
    Returns:
        Tuple of (is_valid, message) indicating validation result
    """
    # Check size matches expectation
    if len(history) != expected_size:
        return False, f"Expected {expected_size} probes, got {len(history)}"
    
    # Check temporal ordering (oldest first)
    for i in range(len(history) - 1):
        if history[i].timestamp >= history[i + 1].timestamp:
            return False, "Probes not in correct temporal order (should be oldest first)"
    
    # Check all probes have valid basic properties
    for i, probe in enumerate(history):
        if not isinstance(probe, ProbeResult):
            return False, f"Probe {i} is not a ProbeResult instance"
        
        if not 0.0 <= probe.confidence <= 1.0:
            return False, f"Probe {i} has invalid confidence: {probe.confidence}"
        
        if probe.tau_value <= 0:
            return False, f"Probe {i} has invalid tau_value: {probe.tau_value}"
        
        if not isinstance(probe.timestamp, datetime):
            return False, f"Probe {i} has invalid timestamp type"
    
    return True, "Valid probe history"


def calculate_expected_weight(age_days: float, decay_rate: float = 0.98) -> float:
    """
    Calculate expected exponential decay weight for a probe of given age.
    
    Args:
        age_days: Age of probe in days
        decay_rate: Daily decay multiplier (default 0.98 for ~34.3 day half-life)
        
    Returns:
        Weight value between 0.0 and 1.0
    """
    return decay_rate ** age_days


def generate_outdoor_temp_sequence(base_temp: float, variation: float, count: int) -> List[float]:
    """
    Generate a sequence of realistic outdoor temperature values.
    
    Args:
        base_temp: Base temperature around which to vary
        variation: Maximum deviation from base temperature (±)
        count: Number of temperature values to generate
        
    Returns:
        List of outdoor temperature values
    """
    temps = []
    for _ in range(count):
        # Generate random temperature within variation range
        deviation = random.uniform(-variation, variation)
        temp = base_temp + deviation
        temps.append(round(temp, 1))
    
    return temps