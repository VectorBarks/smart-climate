"""ABOUTME: Mathematical utilities for thermal curve fitting and analysis.
Provides exponential decay modeling and drift data analysis for passive thermal learning."""

import numpy as np
from typing import List, Tuple, Optional

from .thermal_models import ProbeResult


def exponential_decay(t: float, T_final: float, T_initial: float, tau: float) -> float:
    """Calculate temperature at time t using exponential decay model.
    
    Models thermal drift using: T(t) = T_final + (T_initial - T_final) * exp(-t/tau)
    
    Args:
        t: Time since start of drift (seconds)
        T_final: Final equilibrium temperature (°C)  
        T_initial: Initial temperature at t=0 (°C)
        tau: Thermal time constant (seconds)
        
    Returns:
        Temperature at time t (°C)
    """
    return T_final + (T_initial - T_final) * np.exp(-t / tau)


def analyze_drift_data(
    data_segment: List[Tuple[float, float]], 
    is_passive: bool = False,
    outdoor_temp: Optional[float] = None
) -> Optional[ProbeResult]:
    """Analyze temperature drift data and extract thermal time constant.
    
    Uses scipy.optimize.curve_fit to fit exponential decay model to temperature data.
    Returns None if insufficient data, scipy unavailable, or curve fitting fails.
    
    Args:
        data_segment: List of (timestamp, temperature) tuples
        is_passive: If True, applies 0.5x confidence scaling for passive measurements
        outdoor_temp: Outdoor temperature during drift (°C) - for ProbeResult enhancement
        
    Returns:
        ProbeResult with tau_value, confidence, duration, fit_quality, aborted=False, outdoor_temp
        Returns None if analysis fails or insufficient data
    """
    # Lazy import scipy to avoid blocking event loop during startup
    try:
        from scipy.optimize import curve_fit
    except ImportError:
        return None
        
    # Validate minimum data points
    if len(data_segment) < 10:
        return None
        
    # Handle empty or invalid data
    if not data_segment:
        return None
        
    try:
        # Validate data format - each element should be a tuple/list with 2 elements
        for point in data_segment:
            if not hasattr(point, '__len__') or len(point) != 2:
                raise TypeError("Data points must be tuples/lists with 2 elements")
        
        # Extract time and temperature arrays
        times = np.array([point[0] for point in data_segment])
        temps = np.array([point[1] for point in data_segment])
        
        # Convert to relative time (start at 0)
        times_rel = times - times[0]
        duration = times_rel[-1]
        
        # Define fitting function for curve_fit
        def fit_func(t, T_final, T_initial, tau):
            return exponential_decay(t, T_final, T_initial, tau)
            
        # Initial parameter guess
        T_initial_guess = temps[0]
        T_final_guess = temps[-1] 
        tau_guess = duration / 3  # Start with 1/3 of total duration
        
        # Parameter bounds: T_final, T_initial (-20 to 40°C), tau (300-86400s)
        bounds = (
            [-20.0, -20.0, 300.0],      # Lower bounds
            [40.0, 40.0, 86400.0]       # Upper bounds  
        )
        
        # Perform curve fitting
        popt, pcov = curve_fit(
            fit_func, 
            times_rel, 
            temps,
            p0=[T_final_guess, T_initial_guess, tau_guess],
            bounds=bounds,
            maxfev=1000
        )
        
        T_final_fit, T_initial_fit, tau_fit = popt
        
        # Calculate fit quality (R²)
        temps_predicted = fit_func(times_rel, *popt)
        ss_res = np.sum((temps - temps_predicted) ** 2)
        ss_tot = np.sum((temps - np.mean(temps)) ** 2)
        
        if ss_tot == 0:
            fit_quality = 1.0 if ss_res == 0 else 0.0
        else:
            fit_quality = max(0.0, 1 - (ss_res / ss_tot))
        
        # Calculate confidence based on parameter covariance and fit quality
        # Use diagonal elements of covariance matrix as parameter uncertainties
        param_errors = np.sqrt(np.diag(pcov))
        tau_error = param_errors[2]  # tau is third parameter
        
        # Confidence inversely related to relative parameter uncertainty
        if tau_fit > 0:
            relative_tau_error = tau_error / tau_fit
            confidence = max(0.0, min(1.0, (1.0 - relative_tau_error) * fit_quality))
        else:
            confidence = 0.0
            
        # Apply passive confidence scaling
        if is_passive:
            confidence *= 0.5
            
        return ProbeResult(
            tau_value=tau_fit,
            confidence=confidence,
            duration=int(duration),
            fit_quality=fit_quality,
            aborted=False,
            outdoor_temp=outdoor_temp  # FIXED: Pass outdoor_temp to ProbeResult
        )
        
    except (RuntimeError, ValueError, TypeError, IndexError) as e:
        # Curve fitting failed or invalid data
        # For debugging: could log the specific error
        # print(f"Curve fitting error: {type(e).__name__}: {e}")
        return None