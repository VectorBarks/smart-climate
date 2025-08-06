"""ABOUTME: Status sensor providing human-readable thermal system status and detailed technical attributes.
UI/UX component that translates thermal system state into user-friendly messages and technical data."""

import logging
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
        """Return detailed technical attributes for API consumers."""
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
            
            return {
                "thermal_mode": current_state.value.lower(),
                "offset_mode": self._get_offset_mode(),
                "active_component": self._get_active_component(current_state),
                "comfort_window": comfort_window,
                "effective_target": effective_target,
                "confidence": confidence,
                "tau_cooling": tau_cooling,
                "tau_warming": tau_warming,
                "cycle_health": cycle_health
            }
            
        except Exception as e:
            _LOGGER.error("Error generating sensor attributes: %s", e)
            return {
                "error": f"Attributes unavailable: {e}",
                "thermal_mode": "unknown",
                "offset_mode": "unknown",
                "active_component": "unknown"
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