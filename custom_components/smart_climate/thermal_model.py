# ABOUTME: PassiveThermalModel for RC thermal circuit drift prediction
# ABOUTME: Implements exponential temperature drift using dual tau constants

import math
from typing import List, Optional
from dataclasses import dataclass
from collections import deque
from datetime import datetime


@dataclass
class ProbeResult:
    """Result from thermal probing operation."""
    tau_value: float
    confidence: float
    duration: int
    fit_quality: float
    aborted: bool


class PassiveThermalModel:
    """
    Passive thermal model using RC circuit physics.
    
    Predicts temperature drift when HVAC is off using exponential decay:
    T_future = T_current + (T_outdoor - T_current) * (1 - exp(-t/tau))
    
    Uses different time constants for cooling vs warming scenarios.
    """
    
    def __init__(self, tau_cooling: float = 90.0, tau_warming: float = 150.0):
        """
        Initialize thermal model with time constants.
        
        Args:
            tau_cooling: Time constant for cooling (minutes)
            tau_warming: Time constant for warming (minutes)
        """
        self._tau_cooling = tau_cooling
        self._tau_warming = tau_warming
        self._probe_history: deque = deque(maxlen=5)
        self._tau_last_modified: Optional[datetime] = None
        
    def predict_drift(
        self, 
        current: float, 
        outdoor: float, 
        minutes: int, 
        is_cooling: bool
    ) -> float:
        """
        Predict temperature after passive drift period.
        
        Uses RC circuit formula:
        T_future = T_current + (T_outdoor - T_current) * (1 - exp(-t/tau))
        
        Args:
            current: Current indoor temperature (°C)
            outdoor: Outdoor temperature (°C)
            minutes: Drift duration in minutes
            is_cooling: True if cooling scenario, False if warming
            
        Returns:
            Predicted indoor temperature after drift (°C)
            
        Raises:
            ValueError: If minutes is negative
        """
        if minutes < 0:
            raise ValueError("Time duration cannot be negative")
            
        # Select appropriate time constant
        tau = self._tau_cooling if is_cooling else self._tau_warming
        
        # RC circuit exponential decay formula
        # At t=0: T = T_current
        # At t=∞: T = T_outdoor  
        # T(t) = T_outdoor + (T_current - T_outdoor) * exp(-t/tau)
        # Rearranged: T(t) = T_current + (T_outdoor - T_current) * (1 - exp(-t/tau))
        
        if minutes == 0:
            return current
            
        decay_factor = 1 - math.exp(-minutes / tau)
        temperature_change = (outdoor - current) * decay_factor
        
        return current + temperature_change
    
    def get_confidence(self) -> float:
        """
        Get confidence level for thermal predictions.
        
        Calculates confidence based on probe history quality and quantity:
        confidence = mean(probe.confidence for probe in history) * (len(history) / 5)
        
        Returns:
            Confidence level (0.0 to 1.0)
        """
        if not self._probe_history:
            return 0.0
            
        # Average confidence from all probes in history
        avg_confidence = sum(probe.confidence for probe in self._probe_history) / len(self._probe_history)
        
        # Multiply by fullness ratio (how many of 5 slots are filled)
        fullness_ratio = len(self._probe_history) / 5
        
        return avg_confidence * fullness_ratio
    
    @property
    def tau_last_modified(self) -> Optional[datetime]:
        """
        Get timestamp of last tau values modification.
        
        Returns:
            Datetime when tau values were last modified, or None if never modified
        """
        return self._tau_last_modified
    
    def update_tau(self, probe_result: ProbeResult, is_cooling: bool) -> None:
        """
        Update time constants based on probe results.
        
        Uses weighted average of probe history with weights [0.4, 0.3, 0.15, 0.1, 0.05]
        applied to most recent probes first. Maintains max 5 probe history entries.
        Only updates tau_last_modified timestamp when tau values actually change.
        
        Args:
            probe_result: Result from thermal probing
            is_cooling: True if cooling scenario, False if warming
        """
        # Store original values to detect changes
        original_tau_cooling = self._tau_cooling
        original_tau_warming = self._tau_warming
        
        # Add to probe history (deque automatically handles maxlen=5)
        self._probe_history.append(probe_result)
        
        # Define weights for most recent to oldest probes
        weights = [0.4, 0.3, 0.15, 0.1, 0.05]
        
        # Get relevant probes for this tau type (cooling or warming)
        relevant_probes = [probe for probe in self._probe_history]
        
        if not relevant_probes:
            return
            
        # Calculate weighted average using most recent probes first
        # Reverse to get newest first, then zip with weights
        recent_probes = list(reversed(relevant_probes))
        weighted_sum = 0.0
        
        for i, probe in enumerate(recent_probes):
            if i < len(weights):  # Only use as many weights as we have
                weighted_sum += probe.tau_value * weights[i]
        
        # Update the appropriate tau
        if is_cooling:
            new_tau_cooling = weighted_sum
            # Only update timestamp if value actually changed
            if abs(new_tau_cooling - original_tau_cooling) > 0.01:  # Small tolerance for float comparison
                self._tau_cooling = new_tau_cooling
                self._tau_last_modified = datetime.now()
        else:
            new_tau_warming = weighted_sum
            # Only update timestamp if value actually changed
            if abs(new_tau_warming - original_tau_warming) > 0.01:  # Small tolerance for float comparison
                self._tau_warming = new_tau_warming
                self._tau_last_modified = datetime.now()