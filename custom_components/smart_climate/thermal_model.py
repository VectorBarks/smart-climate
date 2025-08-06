# ABOUTME: PassiveThermalModel for RC thermal circuit drift prediction
# ABOUTME: Implements exponential temperature drift using dual tau constants

import math
from typing import List, Optional
from dataclasses import dataclass


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
        self._probe_history: List[ProbeResult] = []
        
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
        
        For now returns fixed value. Future versions will base this on
        probe history quality and quantity.
        
        Returns:
            Confidence level (0.0 to 1.0)
        """
        return 0.3
    
    def update_tau(self, probe_result: ProbeResult, is_cooling: bool) -> None:
        """
        Update time constants based on probe results.
        
        Uses weighted average with existing values. Maintains max 5 probe
        history entries for memory management.
        
        Args:
            probe_result: Result from thermal probing
            is_cooling: True if cooling scenario, False if warming
        """
        # Add to probe history (max 5 entries)
        self._probe_history.append(probe_result)
        if len(self._probe_history) > 5:
            self._probe_history.pop(0)
            
        # Update appropriate tau using weighted average
        # Weight by confidence and fit quality
        weight = probe_result.confidence * probe_result.fit_quality
        
        if is_cooling:
            # Weighted average: new_tau = (old_tau * old_weight + new_tau * new_weight) / total_weight
            old_weight = 1.0  # Existing tau has weight of 1.0
            total_weight = old_weight + weight
            self._tau_cooling = (self._tau_cooling * old_weight + probe_result.tau_value * weight) / total_weight
        else:
            old_weight = 1.0
            total_weight = old_weight + weight  
            self._tau_warming = (self._tau_warming * old_weight + probe_result.tau_value * weight) / total_weight