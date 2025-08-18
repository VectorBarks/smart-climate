# ABOUTME: PassiveThermalModel for RC thermal circuit drift prediction
# ABOUTME: Implements exponential temperature drift using dual tau constants

import math
from typing import List, Optional
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime, timezone


@dataclass(frozen=True)
class ProbeResult:
    """Result from thermal probing operation.
    
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
        from .const import MAX_PROBE_HISTORY_SIZE
        
        self._tau_cooling = tau_cooling
        self._tau_warming = tau_warming
        self._probe_history: deque = deque(maxlen=MAX_PROBE_HISTORY_SIZE)
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
        """Confidence based on count AND diversity."""
        import math
        
        if not self._probe_history:
            return 0.0
            
        # Base confidence from probe count (up to 80%)
        probe_count = len(self._probe_history)
        base_confidence = min(math.log(probe_count + 1) / math.log(16), 0.8)
        
        # Diversity bonus (up to 20%)
        diversity_score = self._calculate_diversity_score()
        diversity_bonus = diversity_score * 0.2
        
        return min(base_confidence + diversity_bonus, 1.0)

    def _calculate_diversity_score(self) -> float:
        """Calculate diversity score based on temperature bin coverage.
        
        Returns:
            Diversity score as ratio of covered bins to total bins (0.0-1.0)
        """
        # Import here to avoid circular imports
        from .probe_scheduler import OUTDOOR_TEMP_BINS
        
        if not self._probe_history:
            return 0.0
            
        # Count unique temperature bins represented in probe history
        covered_bins = set()
        
        for probe in self._probe_history:
            if probe.outdoor_temp is not None:
                bin_index = self._get_temperature_bin_index(probe.outdoor_temp)
                covered_bins.add(bin_index)
        
        # Total possible bins (including below first and above last)
        total_bins = len(OUTDOOR_TEMP_BINS) + 1
        
        # Return ratio of covered bins to total bins
        return len(covered_bins) / total_bins if total_bins > 0 else 0.0
    
    def _get_temperature_bin_index(self, temperature: float) -> int:
        """Get temperature bin index for given temperature.
        
        Args:
            temperature: Outdoor temperature in Celsius
            
        Returns:
            Bin index (0-based)
        """
        # Import here to avoid circular imports
        from .probe_scheduler import OUTDOOR_TEMP_BINS
        
        # Below first bin
        if temperature < OUTDOOR_TEMP_BINS[0]:
            return 0
        
        # Find appropriate bin
        for i, boundary in enumerate(OUTDOOR_TEMP_BINS):
            if temperature < boundary:
                return i
                
        # Above last bin
        return len(OUTDOOR_TEMP_BINS)

    
    def get_probe_count(self) -> int:
        """Get the current number of probes in history.
        
        Returns:
            Number of probes currently stored in history
        """
        return len(self._probe_history)

    def get_probe_history(self) -> List[ProbeResult]:
        """Get probe history for ProbeScheduler analysis.
        
        Returns:
            Immutable copy of probe history in chronological order
        """
        return list(self._probe_history)
    
    def get_last_probe_time(self) -> Optional[datetime]:
        """Get timestamp of most recent probe.
        
        Returns:
            Timestamp of most recent probe, or None if no probes
        """
        if not self._probe_history:
            return None
        return max(probe.timestamp for probe in self._probe_history)
    
    def add_probe_result(self, probe_result: ProbeResult) -> None:
        """Add probe result to history (for testing/external integration).
        
        Args:
            probe_result: ProbeResult object to add to history
            
        Raises:
            TypeError: If probe_result is not a ProbeResult instance
        """
        if not isinstance(probe_result, ProbeResult):
            raise TypeError(f"Expected ProbeResult, got {type(probe_result)}")
        
        self._probe_history.append(probe_result)
        
        # Update last modified timestamp when probe added
        self._tau_last_modified = datetime.now(timezone.utc)
    
    @property
    def tau_last_modified(self) -> Optional[datetime]:
        """
        Get timestamp of last tau values modification.
        
        Returns:
            Datetime when tau values were last modified, or None if never modified
        """
        return self._tau_last_modified
    
    def _calculate_weighted_tau(self, is_cooling: bool) -> float:
        """Calculate weighted tau using exponential decay based on probe age."""
        from datetime import datetime, timezone
        from .const import DECAY_RATE_PER_DAY
        
        if not self._probe_history:
            return self._tau_cooling if is_cooling else self._tau_warming
        
        now = datetime.now(timezone.utc)
        total_weighted_value = 0.0
        total_weight = 0.0
        
        for probe in self._probe_history:
            # Calculate age in days
            age_days = (now - probe.timestamp).total_seconds() / 86400
            
            # Apply exponential decay
            time_weight = DECAY_RATE_PER_DAY ** age_days
            
            # Apply confidence weight (default to 1.0 if None)
            confidence_weight = probe.confidence if probe.confidence is not None else 1.0
            
            # Combined weight
            final_weight = time_weight * confidence_weight
            
            total_weighted_value += probe.tau_value * final_weight
            total_weight += final_weight
        
        if total_weight > 0:
            return total_weighted_value / total_weight
        else:
            return self._tau_cooling if is_cooling else self._tau_warming

    def update_tau(self, probe_result: ProbeResult, is_cooling: bool) -> None:
        """
        Update time constants based on probe results.
        
        Uses exponential decay weighting based on probe age with DECAY_RATE_PER_DAY = 0.98.
        Maintains max 75 probe history entries for seasonal adaptation.
        Only updates tau_last_modified timestamp when tau values actually change.
        
        Args:
            probe_result: Result from thermal probing
            is_cooling: True if cooling scenario, False if warming
        """
        # Store original values to detect changes
        original_tau_cooling = self._tau_cooling
        original_tau_warming = self._tau_warming
        
        # Add to probe history (deque automatically handles maxlen=75)
        self._probe_history.append(probe_result)
        
        # Calculate new tau using exponential decay weighting
        new_tau = self._calculate_weighted_tau(is_cooling)
        
        # Update the appropriate tau
        if is_cooling:
            # Only update timestamp if value actually changed
            if abs(new_tau - original_tau_cooling) > 0.01:  # Small tolerance for float comparison
                self._tau_cooling = new_tau
                self._tau_last_modified = datetime.now()
        else:
            # Only update timestamp if value actually changed
            if abs(new_tau - original_tau_warming) > 0.01:  # Small tolerance for float comparison
                self._tau_warming = new_tau
                self._tau_last_modified = datetime.now()

    def refine_tau_passively(self, passive_observation) -> None:
        """Apply exponential moving average for continuous tau refinement.
        
        Provides continuous passive refinement of thermal time constants
        between active probe sessions using quality-weighted observations
        from natural temperature drift periods.
        
        Uses a two-tier system where active probes provide primary calibration
        and passive refinement provides small adjustments for accuracy.
        
        Args:
            passive_observation: PassiveObservation containing tau measurement,
                                fit quality, duration, and cooling/warming flag
        """
        from .thermal_models import PassiveObservation
        
        # Quality-weighted alpha calculation (max 0.1 for stability)
        normalized_duration = min(passive_observation.duration_seconds / 3600.0, 1.0)
        quality_score = passive_observation.fit_quality * normalized_duration
        alpha = 0.1 * quality_score
        
        # Exponential Moving Average (EMA) update
        if passive_observation.is_cooling:
            new_tau = (alpha * passive_observation.tau_measured) + ((1 - alpha) * self._tau_cooling)
            self._tau_cooling = new_tau
        else:
            new_tau = (alpha * passive_observation.tau_measured) + ((1 - alpha) * self._tau_warming)
            self._tau_warming = new_tau
