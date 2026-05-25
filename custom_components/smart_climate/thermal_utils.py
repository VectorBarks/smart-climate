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


def _fit_exponential_decay_numpy(times_rel: np.ndarray, temps: np.ndarray):
    """Fit exponential decay using only numpy.

    For each tau candidate, T(t)=a+b*exp(-t/tau) is linear in a/b, so a
    simple least-squares solve finds the best final/initial terms. This keeps
    passive learning functional on HA installs without scipy.
    """
    tau_candidates = np.unique(np.concatenate([
        np.linspace(300.0, 3600.0, 220),
        np.linspace(3600.0, 21600.0, 160),
        np.linspace(21600.0, 86400.0, 120),
    ]))
    best = None
    for tau in tau_candidates:
        exp_term = np.exp(-times_rel / tau)
        design = np.column_stack([np.ones_like(exp_term), exp_term])
        try:
            params, *_ = np.linalg.lstsq(design, temps, rcond=None)
        except np.linalg.LinAlgError:
            continue
        predicted = design @ params
        sse = float(np.sum((temps - predicted) ** 2))
        if best is None or sse < best[0]:
            t_final = float(params[0])
            t_initial = float(params[0] + params[1])
            best = (sse, t_final, t_initial, float(tau), predicted)
    return best


def analyze_drift_data(
    data_segment: List[Tuple[float, float]], 
    is_passive: bool = False,
    outdoor_temp: Optional[float] = None
) -> Optional[ProbeResult]:
    """Analyze temperature drift data and extract thermal time constant.
    
    Uses scipy.optimize.curve_fit when available and falls back to a numpy-only
    grid/least-squares fit otherwise. Returns None for insufficient or invalid
    data.
    """
    # Validate minimum data points
    if len(data_segment) < 10:
        return None
        
    if not data_segment:
        return None
        
    try:
        for point in data_segment:
            if not hasattr(point, '__len__') or len(point) != 2:
                raise TypeError("Data points must be tuples/lists with 2 elements")
        
        times = np.array([point[0] for point in data_segment], dtype=float)
        temps = np.array([point[1] for point in data_segment], dtype=float)
        times_rel = times - times[0]
        duration = float(times_rel[-1])
        if duration <= 0 or np.any(~np.isfinite(times_rel)) or np.any(~np.isfinite(temps)):
            return None
        
        def fit_func(t, T_final, T_initial, tau):
            return exponential_decay(t, T_final, T_initial, tau)

        try:
            from scipy.optimize import curve_fit
            T_initial_guess = temps[0]
            T_final_guess = temps[-1]
            tau_guess = max(300.0, duration / 3)
            bounds = ([-20.0, -20.0, 300.0], [40.0, 40.0, 86400.0])
            popt, pcov = curve_fit(
                fit_func,
                times_rel,
                temps,
                p0=[T_final_guess, T_initial_guess, tau_guess],
                bounds=bounds,
                maxfev=1000,
            )
            T_final_fit, T_initial_fit, tau_fit = popt
            temps_predicted = fit_func(times_rel, *popt)
            param_errors = np.sqrt(np.diag(pcov))
            tau_error = param_errors[2]
            if tau_fit > 0:
                relative_tau_error = tau_error / tau_fit
                confidence_scale = max(0.0, min(1.0, 1.0 - relative_tau_error))
            else:
                confidence_scale = 0.0
        except Exception:
            fitted = _fit_exponential_decay_numpy(times_rel, temps)
            if fitted is None:
                return None
            _sse, T_final_fit, T_initial_fit, tau_fit, temps_predicted = fitted
            confidence_scale = 1.0
        
        ss_res = float(np.sum((temps - temps_predicted) ** 2))
        ss_tot = float(np.sum((temps - np.mean(temps)) ** 2))
        if ss_tot == 0:
            fit_quality = 1.0 if ss_res == 0 else 0.0
        else:
            fit_quality = max(0.0, min(1.0, 1 - (ss_res / ss_tot)))

        # Penalize implausible extrapolation from the numpy fallback lightly, but
        # keep confidence primarily tied to observed fit quality.
        confidence = max(0.0, min(1.0, confidence_scale * fit_quality))
        if is_passive:
            confidence *= 0.5
            
        return ProbeResult(
            tau_value=float(tau_fit),
            confidence=float(confidence),
            duration=int(duration),
            fit_quality=float(fit_quality),
            aborted=False,
            outdoor_temp=outdoor_temp,
            source="passive" if is_passive else "active",
        )
        
    except (RuntimeError, ValueError, TypeError, IndexError, OverflowError):
        return None
