"""Update coordinator for Smart Climate Control integration."""

import logging
from datetime import timedelta, datetime
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .models import SmartClimateData, OffsetInput, ModeAdjustments
from .errors import SmartClimateError

if TYPE_CHECKING:
    from .sensor_manager import SensorManager
    from .offset_engine import OffsetEngine
    from .mode_manager import ModeManager

_LOGGER = logging.getLogger(__name__)


class SmartClimateCoordinator(DataUpdateCoordinator[SmartClimateData]):
    """Coordinates updates for smart climate system."""
    
    def __init__(
        self,
        hass: HomeAssistant,
        update_interval: int,
        sensor_manager: "SensorManager",
        offset_engine: "OffsetEngine",
        mode_manager: "ModeManager"
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
    
    async def _async_update_data(self) -> SmartClimateData:
        """Fetch latest data from all sources."""
        try:
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
                    day_of_week=now.weekday()
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
            
            return SmartClimateData(
                room_temp=room_temp,
                outdoor_temp=outdoor_temp,
                power=power,
                calculated_offset=calculated_offset,
                mode_adjustments=mode_adjustments
            )
            
        except Exception as err:
            _LOGGER.error("Error updating coordinator data: %s", err)
            raise SmartClimateError(f"Failed to update coordinator data: {err}") from err