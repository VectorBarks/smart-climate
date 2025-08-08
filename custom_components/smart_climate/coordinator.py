"""Update coordinator for Smart Climate Control integration."""

import logging
from datetime import timedelta, datetime
from typing import TYPE_CHECKING, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .models import SmartClimateData, OffsetInput, ModeAdjustments
from .errors import SmartClimateError
from .outlier_detector import OutlierDetector
from .dto import SystemHealthData
from .thermal_models import ThermalState
from .const import DOMAIN

if TYPE_CHECKING:
    from .sensor_manager import SensorManager
    from .offset_engine import OffsetEngine
    from .mode_manager import ModeManager
    from .forecast_engine import ForecastEngine
    from .thermal_model import PassiveThermalModel
    from .thermal_preferences import UserPreferences
    from .cycle_monitor import CycleMonitor
    from .comfort_band_controller import ComfortBandController
    from .thermal_manager import ThermalManager

_LOGGER = logging.getLogger(__name__)


class SmartClimateCoordinator(DataUpdateCoordinator[SmartClimateData]):
    """Coordinates updates for smart climate system."""
    
    def __init__(
        self,
        hass: HomeAssistant,
        update_interval: int,
        sensor_manager: "SensorManager",
        offset_engine: "OffsetEngine",
        mode_manager: "ModeManager",
        forecast_engine: Optional["ForecastEngine"] = None,
        outlier_detection_config: Optional[dict] = None,
        thermal_model: Optional["PassiveThermalModel"] = None,
        user_preferences: Optional["UserPreferences"] = None,
        cycle_monitor: Optional["CycleMonitor"] = None,
        comfort_band_controller: Optional["ComfortBandController"] = None,
        thermal_efficiency_enabled: bool = False
    ):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="smart_climate",
            update_interval=timedelta(seconds=update_interval)
        )
        self._sensor_manager = sensor_manager
        self._offset_engine = offset_engine
        self._mode_manager = mode_manager
        self._forecast_engine = forecast_engine
        self._is_startup = True  # Flag for startup calculation
        
        # Initialize thermal efficiency components (Phase 1)
        self.thermal_efficiency_enabled = thermal_efficiency_enabled
        if thermal_efficiency_enabled:
            self._thermal_model = thermal_model
            self._user_preferences = user_preferences
            self._cycle_monitor = cycle_monitor
            self._comfort_band_controller = comfort_band_controller
            
            # Initialize ThermalManager (Phase 2)
            if thermal_model and user_preferences:
                from .thermal_manager import ThermalManager
                self._thermal_manager = ThermalManager(hass, thermal_model, user_preferences)
                _LOGGER.debug("ThermalManager initialized in %s state", self._thermal_manager.current_state.value)
            else:
                self._thermal_manager = None
                _LOGGER.warning("ThermalManager not initialized - missing thermal_model or user_preferences")
            
            _LOGGER.debug("Thermal efficiency enabled with components: model=%s, prefs=%s, monitor=%s, controller=%s, manager=%s",
                         thermal_model is not None, user_preferences is not None,
                         cycle_monitor is not None, comfort_band_controller is not None,
                         self._thermal_manager is not None)
        else:
            self._thermal_manager = None
            _LOGGER.debug("Thermal efficiency disabled")
        
        # Initialize outlier detection
        self.outlier_detection_enabled = outlier_detection_config is not None
        if self.outlier_detection_enabled:
            self._outlier_detector = OutlierDetector(config=outlier_detection_config)
            _LOGGER.debug("Outlier detection enabled with config: %s", outlier_detection_config)
        else:
            self._outlier_detector = None
            _LOGGER.debug("Outlier detection disabled")
    
    async def async_force_startup_refresh(self) -> None:
        """Force immediate refresh for startup scenario."""
        _LOGGER.debug("Forcing startup refresh for coordinator")
        self._is_startup = True
        await self.async_request_refresh()
    
    def _execute_outlier_detection(self, sensor_data: dict) -> dict:
        """Execute outlier detection on sensor data and return results."""
        if not self.outlier_detection_enabled or not self._outlier_detector:
            return {
                "outliers": {},
                "outlier_count": 0,
                "outlier_statistics": {
                    "enabled": False,
                    "temperature_outliers": 0,
                    "power_outliers": 0,
                    "total_samples": 0,
                    "outlier_rate": 0.0
                }
            }
        
        outliers = {}
        outlier_count = 0
        temperature_outliers = 0
        power_outliers = 0
        total_samples = 0
        
        # Check temperature outlier
        room_temp = sensor_data.get("room_temp")
        if room_temp is not None:
            is_temp_outlier = self._outlier_detector.is_temperature_outlier(room_temp)
            outliers["temperature"] = is_temp_outlier
            if is_temp_outlier:
                temperature_outliers += 1
                outlier_count += 1
            # Add sample to history
            self._outlier_detector.add_temperature_sample(room_temp)
            total_samples += 1
        
        # Check power outlier  
        power = sensor_data.get("power")
        if power is not None:
            is_power_outlier = self._outlier_detector.is_power_outlier(power)
            outliers["power"] = is_power_outlier
            if is_power_outlier:
                power_outliers += 1
                outlier_count += 1
            # Add sample to history
            self._outlier_detector.add_power_sample(power)
            total_samples += 1
        
        # Calculate outlier rate
        outlier_rate = (outlier_count / total_samples) if total_samples > 0 else 0.0
        
        outlier_statistics = {
            "enabled": True,
            "temperature_outliers": temperature_outliers,
            "power_outliers": power_outliers,
            "total_samples": total_samples,
            "outlier_rate": outlier_rate,
            "history_size": self._outlier_detector.get_history_size() if self._outlier_detector else 0,
            "has_sufficient_data": self._outlier_detector.has_sufficient_data() if self._outlier_detector else False
        }
        
        _LOGGER.debug(
            "Outlier detection results: outliers=%s, count=%d, stats=%s",
            outliers, outlier_count, outlier_statistics
        )
        
        return {
            "outliers": outliers,
            "outlier_count": outlier_count,
            "outlier_statistics": outlier_statistics
        }
    
    async def _async_update_data(self) -> SmartClimateData:
        """Fetch latest data from all sources."""
        try:
            # Update forecast engine (it handles its own throttling)
            if self._forecast_engine:
                try:
                    await self._forecast_engine.async_update()
                    _LOGGER.debug("ForecastEngine updated successfully")
                except Exception as exc:
                    _LOGGER.warning("Error updating ForecastEngine: %s", exc)
            # Gather sensor data
            room_temp = self._sensor_manager.get_room_temperature()
            outdoor_temp = self._sensor_manager.get_outdoor_temperature()
            power = self._sensor_manager.get_power_consumption()
            
            # Get AC internal temperature from wrapped entity if available
            ac_internal_temp = room_temp  # Default to room temp if unavailable
            if hasattr(self, '_wrapped_entity_id') and self._wrapped_entity_id:
                wrapped_state = self.hass.states.get(self._wrapped_entity_id)
                if wrapped_state and wrapped_state.attributes:
                    ac_temp = wrapped_state.attributes.get("current_temperature")
                    if ac_temp is not None and isinstance(ac_temp, (int, float)):
                        ac_internal_temp = float(ac_temp)
                        _LOGGER.debug(
                            "Got AC internal temperature: %.1f°C (room: %.1f°C)",
                            ac_internal_temp, room_temp or 0
                        )
            
            # Get mode adjustments
            mode_adjustments = self._mode_manager.get_adjustments()
            
            # Get HVAC mode from wrapped entity
            hvac_mode = None
            if hasattr(self, '_wrapped_entity_id') and self._wrapped_entity_id:
                wrapped_state = self.hass.states.get(self._wrapped_entity_id)
                if wrapped_state:
                    hvac_mode = wrapped_state.state
            
            # Calculate offset if we have room temperature
            calculated_offset = 0.0
            thermal_window = None
            learning_target = None
            
            # Phase 2: ThermalManager state-aware protocol
            if self.thermal_efficiency_enabled and self._thermal_manager and room_temp is not None:
                try:
                    # Get current setpoint (approximate from room temp for now)
                    setpoint = room_temp  # TODO: Get actual setpoint from wrapped entity
                    
                    # Calculate operating window using ThermalManager
                    thermal_window = self._thermal_manager.get_operating_window(
                        setpoint=setpoint,
                        outdoor_temp=outdoor_temp or 25.0,  # Default outdoor temp
                        hvac_mode=hvac_mode or "cool"
                    )
                    
                    # Control OffsetEngine learning based on current state
                    current_state = self._thermal_manager.current_state
                    if current_state == ThermalState.DRIFTING:
                        self._offset_engine.pause_learning()
                        _LOGGER.debug("Learning paused for DRIFTING state")
                    elif current_state == ThermalState.CORRECTING:
                        self._offset_engine.resume_learning()
                        _LOGGER.debug("Learning resumed for CORRECTING state")
                    
                    # Get learning target for state-aware training
                    learning_target = self._thermal_manager.get_learning_target(
                        current=room_temp,
                        window=thermal_window
                    )
                    
                    _LOGGER.debug(
                        "ThermalManager state: %s, window: (%.1f, %.1f), learning_target: %.1f",
                        current_state.value, thermal_window[0], thermal_window[1], learning_target
                    )
                    
                except Exception as exc:
                    _LOGGER.warning("Error in ThermalManager state logic: %s", exc)
                    thermal_window = None
                    learning_target = None
            
            if room_temp is not None:
                # Create offset input with proper AC internal temp
                now = datetime.now()
                offset_input = OffsetInput(
                    ac_internal_temp=ac_internal_temp,  # AC's internal sensor
                    room_temp=room_temp,  # External room sensor
                    outdoor_temp=outdoor_temp,
                    mode=self._mode_manager.current_mode,
                    power_consumption=power,
                    time_of_day=now.time(),
                    day_of_week=now.weekday(),
                    hvac_mode=hvac_mode
                )
                
                # Pass thermal window to offset calculation (Phase 2 integration)
                if thermal_window is not None:
                    offset_result = self._offset_engine.calculate_offset(offset_input, thermal_window=thermal_window)
                else:
                    offset_result = self._offset_engine.calculate_offset(offset_input)
                    
                calculated_offset = offset_result.offset
                
                _LOGGER.debug(
                    "Updated coordinator data: ac_internal=%.1f°C, room_temp=%.1f°C, "
                    "outdoor_temp=%s, power=%s, offset=%.1f°C, reason=%s, thermal_window=%s",
                    ac_internal_temp, room_temp, outdoor_temp, power, 
                    calculated_offset, offset_result.reason, thermal_window
                )
            else:
                _LOGGER.warning("No room temperature available for offset calculation")
            
            # Execute outlier detection
            sensor_data = {
                "room_temp": room_temp,
                "outdoor_temp": outdoor_temp,
                "power": power
            }
            outlier_results = self._execute_outlier_detection(sensor_data)
            
            # Execute thermal efficiency calculations (Phase 1 & Phase 2 integration)
            should_ac_run = None
            cycle_health = None
            
            if self.thermal_efficiency_enabled and room_temp is not None:
                try:
                    # If ThermalManager is available (Phase 2), use it for AC decisions
                    if self._thermal_manager and thermal_window:
                        setpoint = room_temp  # Approximate setpoint
                        should_ac_run = self._thermal_manager.should_ac_run(
                            current=room_temp,
                            setpoint=setpoint,
                            window=thermal_window
                        )
                        _LOGGER.debug("Using ThermalManager AC decision: %s", should_ac_run)
                    
                    # Otherwise fall back to Phase 1 comfort band controller
                    elif self._comfort_band_controller:
                        setpoint = room_temp  # Use room temp as approximate setpoint for now
                        if thermal_window is None:
                            thermal_window = self._comfort_band_controller.get_operating_window(
                                setpoint=setpoint,
                                outdoor_temp=outdoor_temp,
                                hvac_mode=hvac_mode
                            )
                        
                        # Determine if AC should run based on comfort band logic
                        should_ac_run = self._comfort_band_controller.should_ac_run(
                            current_temp=room_temp,
                            setpoint=setpoint,
                            operating_window=thermal_window,
                            hvac_mode=hvac_mode,
                            outdoor_temp=outdoor_temp,
                            prediction_minutes=15  # 15-minute prediction window for Phase 1
                        )
                        _LOGGER.debug("Using ComfortBandController AC decision: %s", should_ac_run)
                    
                    # Get cycle health data (both Phase 1 & 2)
                    if self._cycle_monitor:
                        avg_on, avg_off = self._cycle_monitor.get_average_cycle_duration()
                        cycle_health = {
                            "can_turn_on": self._cycle_monitor.can_turn_on(),
                            "can_turn_off": self._cycle_monitor.can_turn_off(),
                            "needs_adjustment": self._cycle_monitor.needs_adjustment(),
                            "avg_on_duration": avg_on,
                            "avg_off_duration": avg_off
                        }
                    
                    _LOGGER.debug(
                        "Thermal efficiency calculations: window=%s, should_run=%s, cycle_health=%s",
                        thermal_window, should_ac_run, cycle_health["needs_adjustment"] if cycle_health else None
                    )
                    
                except Exception as exc:
                    _LOGGER.warning("Error in thermal efficiency calculations: %s", exc)
                    # Use safe defaults on error
                    if thermal_window is None:
                        thermal_window = (room_temp - 1.0, room_temp + 1.0) if room_temp else None
                    should_ac_run = False
                    cycle_health = {
                        "can_turn_on": True,
                        "can_turn_off": True, 
                        "needs_adjustment": False,
                        "avg_on_duration": 0.0,
                        "avg_off_duration": 0.0
                    }
            
            # Handle startup flag
            startup_flag = self._is_startup
            if startup_flag:
                _LOGGER.info("Coordinator performing startup calculation (offset=%.1f°C)", calculated_offset)
                self._is_startup = False  # Reset after first calculation
            
            # Determine Phase 2 state information
            thermal_state = None
            learning_active = False
            
            if self.thermal_efficiency_enabled and self._thermal_manager:
                thermal_state = self._thermal_manager.current_state.value
                learning_active = not getattr(self._offset_engine, '_learning_paused', False)
            
            return SmartClimateData(
                room_temp=room_temp,
                outdoor_temp=outdoor_temp,
                power=power,
                calculated_offset=calculated_offset,
                mode_adjustments=mode_adjustments,
                is_startup_calculation=startup_flag,
                outliers=outlier_results["outliers"],
                outlier_count=outlier_results["outlier_count"],
                outlier_statistics=outlier_results["outlier_statistics"],
                thermal_window=thermal_window,
                should_ac_run=should_ac_run,
                cycle_health=cycle_health,
                thermal_efficiency_enabled=self.thermal_efficiency_enabled,
                # Phase 2 fields
                thermal_state=thermal_state,
                learning_active=learning_active,
                learning_target=learning_target
            )
            
        except Exception as err:
            _LOGGER.error("Error updating coordinator data: %s", err)
            raise SmartClimateError(f"Failed to update coordinator data: {err}") from err
    
    def _get_system_health_data(self) -> SystemHealthData:
        """Get system health data including outlier detection information.
        
        This method integrates outlier detection statistics with system health reporting
        as specified in c_architecture.md Section 9.6.
        """
        # Get base system health data from offset engine if available
        if hasattr(self._offset_engine, 'get_dashboard_data'):
            try:
                dashboard_data = self._offset_engine.get_dashboard_data()
                if hasattr(dashboard_data, 'system_health'):
                    base_health = dashboard_data.system_health
                else:
                    base_health = SystemHealthData()
            except Exception as exc:
                _LOGGER.warning("Could not get base system health data: %s", exc)
                base_health = SystemHealthData()
        else:
            base_health = SystemHealthData()
        
        # Update with outlier-specific information
        outlier_detection_active = self.outlier_detection_enabled
        outliers_detected_today = 0
        outlier_detection_threshold = 2.5
        last_outlier_detection_time = None
        
        if self.data and hasattr(self.data, 'outlier_statistics'):
            stats = self.data.outlier_statistics
            if stats and stats.get('enabled', False):
                # Get outlier count from current data
                outliers_detected_today = self.data.outlier_count or 0
                # Get threshold from outlier detector if available
                if self._outlier_detector:
                    outlier_detection_threshold = self._outlier_detector.zscore_threshold
                # Set last detection time if outliers were detected
                if outliers_detected_today > 0:
                    last_outlier_detection_time = datetime.now()
        
        # Return updated health data with outlier information
        return SystemHealthData(
            memory_usage_kb=base_health.memory_usage_kb,
            persistence_latency_ms=base_health.persistence_latency_ms,
            outlier_detection_active=outlier_detection_active,
            samples_per_day=base_health.samples_per_day,
            accuracy_improvement_rate=base_health.accuracy_improvement_rate,
            convergence_trend=base_health.convergence_trend,
            outliers_detected_today=outliers_detected_today,
            outlier_detection_threshold=outlier_detection_threshold,
            last_outlier_detection_time=last_outlier_detection_time
        )
    
    def _get_system_health_with_outliers(self) -> SystemHealthData:
        """Get system health data with outlier integration.
        
        Alias method for _get_system_health_data to match test expectations.
        """
        return self._get_system_health_data()
    
    # Thermal Data Persistence Methods (Architecture §10.2.2)
    
    def get_thermal_data(self, entity_id: str) -> Optional[dict]:
        """Get thermal data for specific entity persistence.
        
        Architecture compliance: §10.2.2 SmartClimateCoordinator extensions
        Component access pattern: hass.data[DOMAIN][entry_id]["thermal_components"][entity_id]
        
        Args:
            entity_id: Climate entity ID to get thermal data for
            
        Returns:
            Dict with thermal data if ThermalManager found, None otherwise
        """
        try:
            # Look up ThermalManager via hass.data pattern
            # Note: We need to find the correct entry_id for this entity
            for entry_id, entry_data in self.hass.data.get(DOMAIN, {}).items():
                thermal_components = entry_data.get("thermal_components", {})
                if entity_id in thermal_components:
                    thermal_manager = thermal_components[entity_id].get("thermal_manager")
                    if thermal_manager:
                        # Call thermal_manager.serialize() if found
                        _LOGGER.debug("Getting thermal data for entity %s", entity_id)
                        return thermal_manager.serialize()
                    break
            
            _LOGGER.debug("No thermal manager found for entity %s", entity_id)
            return None
            
        except Exception as exc:
            _LOGGER.warning("Error getting thermal data for entity %s: %s", entity_id, exc)
            return None
    
    def restore_thermal_data(self, entity_id: str, data: dict) -> None:
        """Restore thermal data for specific entity.
        
        Architecture compliance: §10.2.2 SmartClimateCoordinator extensions
        Component access pattern: hass.data[DOMAIN][entry_id]["thermal_components"][entity_id]
        
        Args:
            entity_id: Climate entity ID to restore thermal data for
            data: Thermal data dict to restore
        """
        try:
            # Look up ThermalManager via hass.data pattern
            # Note: We need to find the correct entry_id for this entity
            for entry_id, entry_data in self.hass.data.get(DOMAIN, {}).items():
                thermal_components = entry_data.get("thermal_components", {})
                if entity_id in thermal_components:
                    thermal_manager = thermal_components[entity_id].get("thermal_manager")
                    if thermal_manager:
                        # Call thermal_manager.restore(data) if found
                        _LOGGER.debug("Restoring thermal data for entity %s", entity_id)
                        thermal_manager.restore(data)
                        return
                    break
            
            _LOGGER.debug("No thermal manager found for entity %s to restore data", entity_id)
            
        except Exception as exc:
            _LOGGER.warning("Error restoring thermal data for entity %s: %s", entity_id, exc)
    
    # Helper methods for button entity use (Architecture §10.2.2)
    
    def get_thermal_manager(self, entity_id: str) -> Optional["ThermalManager"]:
        """Get ThermalManager for specific entity.
        
        Helper method for button entity use per architecture.
        
        Args:
            entity_id: Climate entity ID to get thermal manager for
            
        Returns:
            ThermalManager instance if found, None otherwise
        """
        try:
            # Look up ThermalManager via hass.data pattern
            for entry_id, entry_data in self.hass.data.get(DOMAIN, {}).items():
                thermal_components = entry_data.get("thermal_components", {})
                if entity_id in thermal_components:
                    return thermal_components[entity_id].get("thermal_manager")
            return None
        except Exception as exc:
            _LOGGER.warning("Error getting thermal manager for entity %s: %s", entity_id, exc)
            return None
    
    def get_offset_engine(self, entity_id: str) -> Optional["OffsetEngine"]:
        """Get OffsetEngine for specific entity.
        
        Helper method for button entity use per architecture.
        
        Args:
            entity_id: Climate entity ID to get offset engine for
            
        Returns:
            OffsetEngine instance if found, None otherwise
        """
        try:
            # Look up OffsetEngine via hass.data pattern
            for entry_id, entry_data in self.hass.data.get(DOMAIN, {}).items():
                offset_engines = entry_data.get("offset_engines", {})
                if entity_id in offset_engines:
                    return offset_engines[entity_id]
            return None
        except Exception as exc:
            _LOGGER.warning("Error getting offset engine for entity %s: %s", entity_id, exc)
            return None