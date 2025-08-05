"""Update coordinator for Smart Climate Control integration."""

import logging
from datetime import timedelta, datetime
from typing import TYPE_CHECKING, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .models import SmartClimateData, OffsetInput, ModeAdjustments
from .errors import SmartClimateError
from .outlier_detector import OutlierDetector

if TYPE_CHECKING:
    from .sensor_manager import SensorManager
    from .offset_engine import OffsetEngine
    from .mode_manager import ModeManager
    from .forecast_engine import ForecastEngine

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
        outlier_detection_config: Optional[dict] = None
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
                outlier_statistics=outlier_results["outlier_statistics"]
            )
            
        except Exception as err:
            _LOGGER.error("Error updating coordinator data: %s", err)
            raise SmartClimateError(f"Failed to update coordinator data: {err}") from err