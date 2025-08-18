"""ABOUTME: Status sensor providing human-readable thermal system status and detailed technical attributes.
UI/UX component that translates thermal system state into user-friendly messages and technical data."""

import logging
import math
from datetime import datetime, timezone, timedelta, time
from typing import Dict, Any, Optional, List

from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorEntity

from .thermal_models import ThermalState

_LOGGER = logging.getLogger(__name__)


class SmartClimateStatusSensor(SensorEntity):
    """Status sensor for thermal efficiency system UI/UX.
    
    Provides human-readable state messages and detailed JSON attributes
    describing the current operation of the thermal efficiency system.
    
    Args:
        hass: Home Assistant instance
        thermal_manager: ThermalManager for state and window information
        offset_engine: OffsetEngine for learning status and targets
        cycle_monitor: CycleMonitor for cycle health metrics
    """
    
    def __init__(
        self,
        hass: HomeAssistant,
        thermal_manager,
        offset_engine,
        cycle_monitor
    ) -> None:
        """Initialize the status sensor."""
        self._hass = hass
        self._thermal_manager = thermal_manager
        self._offset_engine = offset_engine
        self._cycle_monitor = cycle_monitor
        self._attr_name = "Smart Climate Status"
        
        _LOGGER.debug("SmartClimateStatusSensor initialized")
    
    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._attr_name
    
    @property
    def state(self) -> str:
        """Return human-readable state message describing current operation."""
        current_state = self._thermal_manager.current_state
        
        try:
            if current_state == ThermalState.PRIMING:
                return self._get_priming_message()
            elif current_state == ThermalState.DRIFTING:
                return self._get_drifting_message()
            elif current_state == ThermalState.CORRECTING:
                return self._get_correcting_message()
            elif current_state == ThermalState.RECOVERY:
                return self._get_recovery_message()
            elif current_state == ThermalState.PROBING:
                return self._get_probing_message()
            elif current_state == ThermalState.CALIBRATING:
                return self._get_calibrating_message()
            else:
                return f"Unknown state: {current_state.value}"
                
        except Exception as e:
            _LOGGER.error("Error generating state message: %s", e)
            return f"Status unavailable ({current_state.value})"
    
    def _get_priming_message(self) -> str:
        """Generate message for PRIMING state."""
        # For now, show generic initializing message
        # Future: calculate actual hours remaining based on priming start time
        return "Initializing (learning system behavior)"
    
    def _get_drifting_message(self) -> str:
        """Generate message for DRIFTING state."""
        setpoint = getattr(self._thermal_manager, '_setpoint', 24.0)
        return f"Idle - saving energy (drift to {setpoint:.1f}°C)"
    
    def _get_correcting_message(self) -> str:
        """Generate message for CORRECTING state."""
        hvac_mode = getattr(self._thermal_manager, '_last_hvac_mode', 'cool')
        
        if hvac_mode == 'heat':
            return "Active heating to comfort zone"
        else:
            return "Active cooling to comfort zone"
    
    def _get_recovery_message(self) -> str:
        """Generate message for RECOVERY state."""
        # For now, show generic recovery message
        # Future: calculate actual progress percentage
        return "Adjusting to new settings (stabilizing)"
    
    def _get_probing_message(self) -> str:
        """Generate message for PROBING state."""
        # For now, show generic probing message
        # Future: calculate actual progress percentage
        return "Learning thermal properties (probing system)"
    
    def _get_calibrating_message(self) -> str:
        """Generate message for CALIBRATING state."""
        return "Calibrating sensors for accuracy"
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes including probe scheduler status."""
        try:
            current_state = self._thermal_manager.current_state
            
            # Get comfort window
            comfort_window = self._get_comfort_window()
            
            # Get effective target from offset engine
            effective_target = self._get_effective_target()
            
            # Get confidence from thermal model
            confidence = self._get_confidence()
            
            # Get tau values from thermal model
            tau_cooling, tau_warming = self._get_tau_values()
            
            # Get cycle health metrics
            cycle_health = self._get_cycle_health()
            
            # Get probe scheduler status information (NEW v1.5.3-beta)
            attributes = {
                "thermal_mode": current_state.value.lower(),
                "offset_mode": self._get_offset_mode(),
                "active_component": self._get_active_component(current_state),
                "comfort_window": comfort_window,
                "effective_target": effective_target,
                "confidence": confidence,
                "tau_cooling": tau_cooling,
                "tau_warming": tau_warming,
                "cycle_health": cycle_health,
                
                # Probe Scheduler Status (NEW v1.5.3-beta):
                "probe_scheduler_status": self._get_probe_scheduler_status(),
                "next_probe_eligible": self._get_next_probe_eligible_time(),
                "confidence_breakdown": self._get_confidence_breakdown(),
                "learning_progress": self._get_learning_progress(),
                "probe_count": self._get_probe_count(),
                "last_probe_time": self._get_last_probe_time(),
                "temperature_bins_covered": self._get_temperature_bins_covered(),
            }
            
            return attributes
            
        except Exception as e:
            _LOGGER.error("Error generating sensor attributes: %s", e)
            return {
                "error": f"Attributes unavailable: {e}",
                "thermal_mode": "unknown",
                "offset_mode": "unknown",
                "active_component": "unknown",
                # Provide fallback probe scheduler attributes
                "probe_scheduler_status": "Error",
                "next_probe_eligible": "Unknown",
                "confidence_breakdown": {"base_confidence": 0.0, "diversity_bonus": 0.0, "total_confidence": 0.0},
                "learning_progress": {"phase": "Unknown", "confidence_level": "Unknown"},
                "probe_count": 0,
                "last_probe_time": None,
                "temperature_bins_covered": {"covered_bins": [], "total_bins": 0, "coverage_ratio": 0.0}
            }
    
    def _get_comfort_window(self) -> List[float]:
        """Get current comfort window as list of floats."""
        try:
            window = self._thermal_manager.get_operating_window(
                getattr(self._thermal_manager, '_setpoint', 24.0),
                22.0,  # Default outdoor temp for window calculation
                getattr(self._thermal_manager, '_last_hvac_mode', 'cool')
            )
            if window and len(window) == 2:
                return [float(window[0]), float(window[1])]
            else:
                return [20.0, 26.0]  # Fallback window
        except Exception as e:
            _LOGGER.warning("Error getting comfort window: %s", e)
            return [20.0, 26.0]  # Fallback window
    
    def _get_offset_mode(self) -> str:
        """Get offset engine mode (active/paused)."""
        try:
            if hasattr(self._offset_engine, 'is_learning_paused') and callable(self._offset_engine.is_learning_paused):
                is_paused = self._offset_engine.is_learning_paused()
                return "paused" if is_paused else "active"
            else:
                # Fallback: assume active if method not available
                return "active"
        except Exception as e:
            _LOGGER.warning("Error getting offset mode: %s", e)
            return "active"
    
    def _get_active_component(self, current_state: ThermalState) -> str:
        """Determine which component is currently active."""
        if current_state in [ThermalState.DRIFTING, ThermalState.PROBING]:
            return "ThermalManager"
        elif current_state in [ThermalState.CORRECTING, ThermalState.CALIBRATING]:
            return "OffsetEngine"
        else:
            # PRIMING, RECOVERY can be either - default to ThermalManager
            return "ThermalManager"
    
    def _get_effective_target(self) -> float:
        """Get effective target temperature from offset engine."""
        try:
            if hasattr(self._offset_engine, 'get_effective_target') and callable(self._offset_engine.get_effective_target):
                target = self._offset_engine.get_effective_target()
                return float(target) if target is not None else 24.0
            else:
                # Fallback to thermal manager setpoint
                return float(getattr(self._thermal_manager, '_setpoint', 24.0))
        except Exception as e:
            _LOGGER.warning("Error getting effective target: %s", e)
            return 24.0
    
    def _get_confidence(self) -> float:
        """Get confidence level from thermal model."""
        try:
            if hasattr(self._thermal_manager, '_model') and hasattr(self._thermal_manager._model, 'get_confidence'):
                confidence = self._thermal_manager._model.get_confidence()
                return float(confidence) if confidence is not None else 0.5
            else:
                return 0.5  # Default moderate confidence
        except Exception as e:
            _LOGGER.warning("Error getting confidence: %s", e)
            return 0.5
    
    def _get_tau_values(self) -> tuple[float, float]:
        """Get tau_cooling and tau_warming from thermal model."""
        try:
            model = getattr(self._thermal_manager, '_model', None)
            if model:
                tau_cooling = getattr(model, 'tau_cooling', 90.0)
                tau_warming = getattr(model, 'tau_warming', 150.0)
                return float(tau_cooling), float(tau_warming)
            else:
                return 90.0, 150.0  # Default values
        except Exception as e:
            _LOGGER.warning("Error getting tau values: %s", e)
            return 90.0, 150.0
    
    def _get_cycle_health(self) -> Dict[str, Any]:
        """Get cycle health metrics from cycle monitor."""
        try:
            if hasattr(self._cycle_monitor, 'get_average_cycle_duration') and hasattr(self._cycle_monitor, 'needs_adjustment'):
                avg_on, avg_off = self._cycle_monitor.get_average_cycle_duration()
                needs_adjustment = self._cycle_monitor.needs_adjustment()
                
                return {
                    "avg_on_time": float(avg_on),
                    "avg_off_time": float(avg_off),
                    "needs_adjustment": bool(needs_adjustment)
                }
            else:
                return {
                    "avg_on_time": 0.0,
                    "avg_off_time": 0.0,
                    "needs_adjustment": False
                }
        except Exception as e:
            _LOGGER.warning("Error getting cycle health: %s", e)
            return {
                "avg_on_time": 0.0,
                "avg_off_time": 0.0,
                "needs_adjustment": False
            }

    # ProbeScheduler Status Methods (v1.5.3-beta)
    
    def _get_probe_scheduler_status(self) -> str:
        """Get human-readable probe scheduler status."""
        try:
            probe_scheduler = getattr(self._thermal_manager, 'probe_scheduler', None)
            if probe_scheduler is None:
                return "Disabled"
            
            # Check if probe scheduler would approve probing now
            if probe_scheduler.should_probe_now():
                # Check if forced due to maximum interval
                if probe_scheduler._check_maximum_interval_exceeded():
                    return "Forced - Max Interval"
                else:
                    return "Ready"
            
            # Determine the blocking condition
            if probe_scheduler._is_quiet_hours():
                return "Blocked - Quiet Hours"
            elif probe_scheduler._check_presence_entity():
                return "Blocked - User Present"
            elif not probe_scheduler._enforce_minimum_interval():
                return "Blocked - Min Interval"
            elif not probe_scheduler._has_high_information_gain(
                self._get_current_temperature(),
                probe_scheduler._get_probe_history()
            ):
                return "Blocked - Low Information Gain"
            else:
                return "Blocked - Other"
                
        except Exception as e:
            _LOGGER.warning("Error getting probe scheduler status: %s", e)
            return "Unknown"
    
    def _get_current_temperature(self) -> float:
        """Get current room temperature for probe scheduler analysis."""
        try:
            # Try to get from thermal manager or fallback to default
            return getattr(self._thermal_manager, '_current_temp', 22.0)
        except Exception:
            return 22.0
    
    def _get_next_probe_eligible_time(self) -> str:
        """Get next time when probe would be eligible."""
        try:
            probe_scheduler = getattr(self._thermal_manager, 'probe_scheduler', None)
            if probe_scheduler is None:
                return "Unknown"
            
            # If currently eligible
            if probe_scheduler.should_probe_now():
                return "Now"
            
            # Calculate next eligible time based on blocking condition
            now = datetime.now(timezone.utc)
            
            # Check minimum interval constraint
            if not probe_scheduler._enforce_minimum_interval():
                last_probe_time = probe_scheduler._get_last_probe_time()
                if last_probe_time:
                    # Minimum interval is 12 hours
                    next_time = last_probe_time + timedelta(hours=12)
                    return next_time.isoformat()
            
            # Check quiet hours constraint
            if probe_scheduler._is_quiet_hours():
                # Next eligible is 7:00 AM
                next_day = now.replace(hour=7, minute=0, second=0, microsecond=0)
                if next_day <= now:
                    next_day += timedelta(days=1)
                return next_day.isoformat()
            
            # For other blocks, assume eligible in near future
            return (now + timedelta(hours=1)).isoformat()
            
        except Exception as e:
            _LOGGER.warning("Error calculating next probe eligible time: %s", e)
            return "Unknown"
    
    def _get_confidence_breakdown(self) -> Dict[str, Any]:
        """Get confidence breakdown with base and diversity components."""
        try:
            probe_scheduler = getattr(self._thermal_manager, 'probe_scheduler', None)
            thermal_model = getattr(self._thermal_manager, '_model', None)
            
            # Base confidence from thermal model
            base_confidence = 0.5
            if thermal_model and hasattr(thermal_model, 'get_confidence'):
                base_confidence = float(thermal_model.get_confidence())
            
            # Initialize values
            diversity_bonus = 0.0
            probe_count = 0
            bins_covered = 0
            total_bins = 6  # Default number of temperature bins
            
            if probe_scheduler:
                # Get probe count
                probe_history = probe_scheduler._get_probe_history()
                probe_count = len(probe_history) if probe_history else 0
                
                # Calculate base confidence from probe count (log-based, up to 0.8)
                if probe_count > 0:
                    base_confidence = min(math.log(probe_count + 1) / math.log(16), 0.8)
                
                # Get bin coverage for diversity bonus
                bin_coverage = probe_scheduler._get_bin_coverage()
                if bin_coverage:
                    bins_covered = len(bin_coverage.get("covered_bins", []))
                    total_bins = bin_coverage.get("total_bins", 6)
                    diversity_score = bins_covered / total_bins if total_bins > 0 else 0.0
                    diversity_bonus = diversity_score * 0.2  # Up to 20% bonus
            
            # Total confidence is sum, clamped to 1.0
            total_confidence = min(base_confidence + diversity_bonus, 1.0)
            
            return {
                "base_confidence": base_confidence,
                "diversity_bonus": diversity_bonus,
                "total_confidence": total_confidence,
                "probe_count": probe_count,
                "bins_covered": bins_covered,
                "total_bins": total_bins
            }
            
        except Exception as e:
            _LOGGER.warning("Error calculating confidence breakdown: %s", e)
            return {
                "base_confidence": 0.5,
                "diversity_bonus": 0.0,
                "total_confidence": 0.5,
                "probe_count": 0,
                "bins_covered": 0,
                "total_bins": 6
            }
    
    def _get_learning_progress(self) -> Dict[str, str]:
        """Get learning progress indicators."""
        try:
            probe_scheduler = getattr(self._thermal_manager, 'probe_scheduler', None)
            confidence_breakdown = self._get_confidence_breakdown()
            
            # Determine phase based on probe count and confidence
            probe_count = confidence_breakdown["probe_count"]
            total_confidence = confidence_breakdown["total_confidence"]
            
            # Phase determination
            if probe_count < 5 or total_confidence < 0.4:
                phase = "Initial"
            elif total_confidence >= 0.8:
                phase = "Optimized"
            else:
                phase = "Active Learning"
            
            # Confidence level
            if total_confidence < 0.4:
                confidence_level = "Low"
            elif total_confidence < 0.7:
                confidence_level = "Medium"
            else:
                confidence_level = "High"
            
            # Estimated completion
            if total_confidence >= 0.9:
                estimated_completion = "Complete"
            elif total_confidence >= 0.7:
                estimated_completion = "1 week"
            elif total_confidence >= 0.5:
                estimated_completion = "2 weeks"
            elif total_confidence >= 0.3:
                estimated_completion = "3 weeks"
            else:
                estimated_completion = "1-2 months"
            
            # Learning profile
            learning_profile = "balanced"  # Default
            if probe_scheduler:
                try:
                    profile = getattr(probe_scheduler, '_learning_profile', None)
                    if profile:
                        learning_profile = profile.value.lower()
                except Exception:
                    pass
            
            return {
                "phase": phase,
                "confidence_level": confidence_level,
                "estimated_completion": estimated_completion,
                "learning_profile": learning_profile
            }
            
        except Exception as e:
            _LOGGER.warning("Error calculating learning progress: %s", e)
            return {
                "phase": "Unknown",
                "confidence_level": "Unknown",
                "estimated_completion": "Unknown",
                "learning_profile": "balanced"
            }
    
    def _get_probe_count(self) -> int:
        """Get number of successful probes."""
        try:
            probe_scheduler = getattr(self._thermal_manager, 'probe_scheduler', None)
            if probe_scheduler:
                probe_history = probe_scheduler._get_probe_history()
                return len(probe_history) if probe_history else 0
            return 0
        except Exception as e:
            _LOGGER.warning("Error getting probe count: %s", e)
            return 0
    
    def _get_last_probe_time(self) -> Optional[str]:
        """Get timestamp of last successful probe."""
        try:
            probe_scheduler = getattr(self._thermal_manager, 'probe_scheduler', None)
            if probe_scheduler:
                last_time = probe_scheduler._get_last_probe_time()
                return last_time.isoformat() if last_time else None
            return None
        except Exception as e:
            _LOGGER.warning("Error getting last probe time: %s", e)
            return None
    
    def _get_temperature_bins_covered(self) -> Dict[str, Any]:
        """Get temperature bin coverage display."""
        try:
            probe_scheduler = getattr(self._thermal_manager, 'probe_scheduler', None)
            
            # Default bin setup (6 bins covering typical temperature range)
            total_bins = 6
            default_ranges = ["<-10°C", "-10-0°C", "0-10°C", "10-20°C", "20-30°C", ">30°C"]
            
            if probe_scheduler:
                try:
                    bin_coverage = probe_scheduler._get_bin_coverage()
                    if bin_coverage:
                        covered_bins = bin_coverage.get("covered_bins", [])
                        total_bins = bin_coverage.get("total_bins", 6)
                        
                        # Calculate missing ranges
                        missing_bins = []
                        for i in range(total_bins):
                            if i not in covered_bins:
                                missing_bins.append(i)
                        
                        # Get bin ranges if available, otherwise use defaults
                        bin_ranges = bin_coverage.get("bin_ranges", {})
                        if not bin_ranges:
                            # Create default bin ranges
                            bin_ranges = {i: default_ranges[i] for i in range(min(len(default_ranges), total_bins))}
                        
                        missing_ranges = [bin_ranges.get(i, f"Bin {i}") for i in missing_bins]
                        coverage_ratio = len(covered_bins) / total_bins if total_bins > 0 else 0.0
                        
                        return {
                            "covered_bins": covered_bins,
                            "total_bins": total_bins,
                            "coverage_ratio": coverage_ratio,
                            "missing_ranges": missing_ranges
                        }
                except Exception as e:
                    _LOGGER.debug("Error getting detailed bin coverage: %s", e)
            
            # Fallback when no probe scheduler or error
            return {
                "covered_bins": [],
                "total_bins": total_bins,
                "coverage_ratio": 0.0,
                "missing_ranges": default_ranges[:total_bins]
            }
            
        except Exception as e:
            _LOGGER.warning("Error getting temperature bins covered: %s", e)
            return {
                "covered_bins": [],
                "total_bins": 6,
                "coverage_ratio": 0.0,
                "missing_ranges": ["All ranges"]
            }