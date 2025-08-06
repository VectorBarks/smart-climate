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

if TYPE_CHECKING:
    from .sensor_manager import SensorManager
    from .offset_engine import OffsetEngine
    from .mode_manager import ModeManager
    from .forecast_engine import ForecastEngine
    from .thermal_model import PassiveThermalModel
    from .thermal_preferences import UserPreferences
    from .cycle_monitor import CycleMonitor
    from .comfort_band_controller import ComfortBandController

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
            _LOGGER.debug("Thermal efficiency enabled with components: model=%s, prefs=%s, monitor=%s, controller=%s",
                         thermal_model is not None, user_preferences is not None,
                         cycle_monitor is not None, comfort_band_controller is not None)
        else:
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
                
                offset_result = self._offset_engine.calculate_offset(offset_input)
                calculated_offset = offset_result.offset
                
                _LOGGER.debug(
                    "Updated coordinator data: ac_internal=%.1f°C, room_temp=%.1f°C, "
                    "outdoor_temp=%s, power=%s, offset=%.1f°C, reason=%s",
                    ac_internal_temp, room_temp, outdoor_temp, power, 
                    calculated_offset, offset_result.reason
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
            
            # Execute thermal efficiency calculations (Phase 1)
            thermal_window = None
            should_ac_run = None
            cycle_health = None
            
            if self.thermal_efficiency_enabled and room_temp is not None:
                try:
                    # Calculate operating window based on current setpoint
                    setpoint = room_temp  # Use room temp as approximate setpoint for now
                    thermal_window = self._comfort_band_controller.get_operating_window(
                        setpoint=setpoint,
                        outdoor_temp=outdoor_temp,
                        hvac_mode=hvac_mode
                    )
                    
                    # Determine if AC should run based on thermal efficiency logic
                    should_ac_run = self._comfort_band_controller.should_ac_run(
                        current_temp=room_temp,
                        setpoint=setpoint,
                        operating_window=thermal_window,
                        hvac_mode=hvac_mode,
                        outdoor_temp=outdoor_temp,
                        prediction_minutes=15  # 15-minute prediction window for Phase 1
                    )
                    
                    # Get cycle health data
                    avg_on, avg_off = self._cycle_monitor.get_average_cycle_duration()
                    cycle_health = {
                        "can_turn_on": self._cycle_monitor.can_turn_on(),
                        "can_turn_off": self._cycle_monitor.can_turn_off(),
                        "needs_adjustment": self._cycle_monitor.needs_adjustment(),
                        "avg_on_duration": avg_on,
                        "avg_off_duration": avg_off
                    }
                    
                    _LOGGER.debug(
                        "Thermal efficiency calculations: window=(%.1f, %.1f), should_run=%s, cycle_health=%s",
                        thermal_window[0], thermal_window[1], should_ac_run, cycle_health["needs_adjustment"]
                    )
                    
                except Exception as exc:
                    _LOGGER.warning("Error in thermal efficiency calculations: %s", exc)
                    # Use safe defaults on error
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
                thermal_efficiency_enabled=self.thermal_efficiency_enabled
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