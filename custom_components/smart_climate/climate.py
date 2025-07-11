"""ABOUTME: Smart Climate Entity for Home Assistant integration.
Virtual climate entity that wraps any existing climate entity with intelligent offset compensation."""

import logging
from typing import Optional, List, Callable
from datetime import datetime

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode, HVACAction, ClimateEntityFeature
)
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_call_later
from homeassistant.exceptions import HomeAssistantError

from .models import OffsetInput, OffsetResult
from .const import DOMAIN, TEMP_DEVIATION_THRESHOLD

_LOGGER = logging.getLogger(__name__)

# Define a threshold for triggering automatic updates.
# This prevents tiny, insignificant fluctuations from causing unnecessary adjustments.
OFFSET_UPDATE_THRESHOLD = 0.3  # degrees Celsius


class SmartClimateEntity(ClimateEntity):
    """Virtual climate entity that wraps another climate entity."""
    
    def __init__(
        self,
        hass: HomeAssistant,
        config: dict,
        wrapped_entity_id: str,
        room_sensor_id: str,
        offset_engine,
        sensor_manager,
        mode_manager,
        temperature_controller,
        coordinator
    ):
        """Initialize the SmartClimateEntity.
        
        Args:
            hass: Home Assistant instance
            config: Configuration dictionary
            wrapped_entity_id: ID of the climate entity to wrap
            room_sensor_id: ID of the room temperature sensor
            offset_engine: OffsetEngine instance
            sensor_manager: SensorManager instance
            mode_manager: ModeManager instance
            temperature_controller: TemperatureController instance
            coordinator: SmartClimateCoordinator instance
        """
        super().__init__()
        
        # Store dependencies (exact names from architecture)
        self._wrapped_entity_id = wrapped_entity_id
        self._room_sensor_id = room_sensor_id
        self._outdoor_sensor_id = config.get("outdoor_sensor")
        self._power_sensor_id = config.get("power_sensor")
        self._offset_engine = offset_engine
        self._sensor_manager = sensor_manager
        self._mode_manager = mode_manager
        self._temperature_controller = temperature_controller
        self._coordinator = coordinator
        self._config = config
        self._last_offset = 0.0
        self._manual_override = None
        
        # Track availability state changes
        self._was_unavailable = False
        
        # Pass wrapped entity ID to coordinator for AC internal temp access
        self._coordinator._wrapped_entity_id = wrapped_entity_id
        
        # Learning feedback tracking
        self._feedback_tasks: List[Callable] = []  # Cancel functions for scheduled feedbacks
        self._last_predicted_offset: Optional[float] = None
        self._last_offset_input: Optional[OffsetInput] = None
        self._feedback_delay = config.get("feedback_delay", 45)  # Default 45 seconds
        
        # Initialize Home Assistant required attributes
        self._attr_target_temperature = None
        self._attr_current_temperature = None
        self._attr_hvac_mode = None
        self._attr_hvac_modes = None
        self._attr_hvac_action = None
        self._attr_fan_mode = None
        self._attr_fan_modes = None
        self._attr_swing_mode = None
        self._attr_swing_modes = None
        self._attr_preset_mode = None
        self._attr_preset_modes = None
        self._attr_supported_features = None
        self._attr_temperature_unit = None
        self._attr_min_temp = None
        self._attr_max_temp = None
        self._attr_target_temperature_step = None
        self._attr_current_humidity = None
        self._attr_target_humidity = None
        self._attr_min_humidity = None
        self._attr_max_humidity = None
        self._attr_target_temperature_high = None
        self._attr_target_temperature_low = None
        self.hass = hass
        
        _LOGGER.debug(
            "SmartClimateEntity initialized for wrapped entity: %s",
            wrapped_entity_id
        )
    
    @property
    def unique_id(self) -> str:
        """Return unique identifier for this entity."""
        # Extract device part from wrapped entity ID
        wrapped_device = self._wrapped_entity_id.split('.', 1)[1]
        return f"smart_climate.{wrapped_device}"
    
    @property
    def name(self) -> str:
        """Return the name of the entity."""
        wrapped_state = self.hass.states.get(self._wrapped_entity_id)
        if wrapped_state and wrapped_state.attributes.get("friendly_name"):
            base_name = wrapped_state.attributes["friendly_name"]
            return f"Smart {base_name}"
        else:
            # Fallback to config name or wrapped entity ID
            return self._config.get("name", f"Smart {self._wrapped_entity_id}")
    
    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        try:
            wrapped_state = self.hass.states.get(self._wrapped_entity_id)
            if not wrapped_state:
                return False
            
            # Check if the wrapped entity is unavailable
            is_unavailable = wrapped_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN, None)
            
            # Track state changes for recovery handling
            if is_unavailable and not self._was_unavailable:
                _LOGGER.debug(
                    "Wrapped entity %s became unavailable (state: %s)",
                    self._wrapped_entity_id,
                    wrapped_state.state
                )
                self._was_unavailable = True
            elif not is_unavailable and self._was_unavailable:
                _LOGGER.info(
                    "Wrapped entity %s recovered from unavailable state (state: %s)",
                    self._wrapped_entity_id,
                    wrapped_state.state
                )
                self._was_unavailable = False
                
                # Check if we need to update temperature on recovery
                if self._attr_target_temperature is not None:
                    # Get current temperatures
                    room_temp = self._sensor_manager.get_room_temperature()
                    if room_temp is not None:
                        temp_diff = abs(room_temp - self._attr_target_temperature)
                        if temp_diff > OFFSET_UPDATE_THRESHOLD:
                            _LOGGER.info(
                                "Temperature update needed on recovery: room=%.1f°C, target=%.1f°C, diff=%.1f°C",
                                room_temp,
                                self._attr_target_temperature,
                                temp_diff
                            )
                            # Schedule temperature update
                            self.hass.async_create_task(
                                self._apply_temperature_with_offset(self._attr_target_temperature)
                            )
            
            # Return availability based on wrapped entity state
            return not is_unavailable
            
        except Exception as exc:
            _LOGGER.error(
                "Error checking availability for wrapped entity %s: %s",
                self._wrapped_entity_id,
                exc
            )
            return False
    
    @property
    def current_temperature(self) -> Optional[float]:
        """Return room sensor temperature."""
        return self._sensor_manager.get_room_temperature()
    
    @property
    def target_temperature(self) -> float:
        """Return the user-facing target temperature."""
        # If we have a stored target temperature, use it
        if self._attr_target_temperature is not None:
            _LOGGER.debug(
                "Returning stored target temperature: %.1f°C",
                self._attr_target_temperature
            )
            return self._attr_target_temperature
        
        # Otherwise, fall back to wrapped entity's target temperature
        try:
            wrapped_state = self.hass.states.get(self._wrapped_entity_id)
            if wrapped_state and wrapped_state.attributes:
                wrapped_target = wrapped_state.attributes.get("target_temperature")
                if wrapped_target is not None and isinstance(wrapped_target, (int, float)):
                    wrapped_temp = float(wrapped_target)
                    _LOGGER.debug(
                        "Returning wrapped entity target temperature: %.1f°C",
                        wrapped_temp
                    )
                    return wrapped_temp
            
            _LOGGER.debug(
                "No target temperature available from wrapped entity %s, using default",
                self._wrapped_entity_id
            )
            # Never return None - provide configurable default
            return self._config.get("default_target_temperature", 24.0)
            
        except Exception as exc:
            _LOGGER.error(
                "Error getting target_temperature from wrapped entity %s: %s, using default",
                self._wrapped_entity_id,
                exc
            )
            # Never return None - provide configurable default
            return self._config.get("default_target_temperature", 24.0)
    
    @property
    def preset_modes(self) -> List[str]:
        """Return available preset modes."""
        return ["none", "away", "sleep", "boost"]
    
    @property
    def preset_mode(self) -> Optional[str]:
        """Return current preset mode."""
        return self._mode_manager.current_mode
    
    @property
    def hvac_mode(self) -> str:
        """Forward to wrapped entity with defensive programming."""
        try:
            wrapped_state = self.hass.states.get(self._wrapped_entity_id)
            if wrapped_state and wrapped_state.state:
                return wrapped_state.state
                
            _LOGGER.warning(
                "Wrapped entity %s has no state, defaulting to OFF",
                self._wrapped_entity_id
            )
            return HVACMode.OFF
            
        except Exception as exc:
            _LOGGER.error(
                "Error getting hvac_mode from wrapped entity %s: %s",
                self._wrapped_entity_id,
                exc
            )
            return HVACMode.OFF
    
    @property
    def hvac_modes(self) -> List[str]:
        """Forward to wrapped entity with defensive programming."""
        try:
            wrapped_state = self.hass.states.get(self._wrapped_entity_id)
            if wrapped_state and wrapped_state.attributes:
                hvac_modes = wrapped_state.attributes.get("hvac_modes")
                if hvac_modes and isinstance(hvac_modes, list):
                    return hvac_modes
                    
            # Log warning if wrapped entity doesn't have hvac_modes
            _LOGGER.warning(
                "Wrapped entity %s missing hvac_modes attribute. Wrapped state: %s",
                self._wrapped_entity_id,
                wrapped_state.state if wrapped_state else "None"
            )
            
            # Return reasonable defaults based on common climate entities
            return [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.AUTO]
            
        except Exception as exc:
            _LOGGER.error(
                "Error getting hvac_modes from wrapped entity %s: %s",
                self._wrapped_entity_id,
                exc
            )
            return [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.AUTO]
    
    @property
    def supported_features(self) -> int:
        """Forward to wrapped entity with defensive programming."""
        try:
            wrapped_state = self.hass.states.get(self._wrapped_entity_id)
            if wrapped_state and wrapped_state.attributes:
                supported_features = wrapped_state.attributes.get("supported_features")
                if supported_features is not None and isinstance(supported_features, int):
                    # Always add preset mode support since we manage our own presets
                    return supported_features | ClimateEntityFeature.PRESET_MODE
                    
            # Log warning if wrapped entity doesn't have supported_features
            _LOGGER.warning(
                "Wrapped entity %s missing supported_features attribute. Wrapped state: %s",
                self._wrapped_entity_id,
                wrapped_state.state if wrapped_state else "None"
            )
            
            # Return reasonable defaults for climate entities
            base_features = int(ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE)
            
            # Dynamically add features based on wrapped entity capabilities
            if wrapped_state and wrapped_state.attributes:
                if wrapped_state.attributes.get("fan_modes"):
                    base_features |= ClimateEntityFeature.FAN_MODE
                if wrapped_state.attributes.get("swing_modes"):
                    base_features |= ClimateEntityFeature.SWING_MODE
                if wrapped_state.attributes.get("target_humidity") is not None:
                    base_features |= ClimateEntityFeature.TARGET_HUMIDITY
                if (wrapped_state.attributes.get("target_temperature_high") is not None or
                    wrapped_state.attributes.get("target_temperature_low") is not None):
                    base_features |= ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
                    
            return base_features
            
        except Exception as exc:
            _LOGGER.error(
                "Error getting supported_features from wrapped entity %s: %s",
                self._wrapped_entity_id,
                exc
            )
            return int(ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE)
    
    @property
    def min_temp(self) -> float:
        """Forward to wrapped entity with defensive programming."""
        try:
            wrapped_state = self.hass.states.get(self._wrapped_entity_id)
            if wrapped_state and wrapped_state.attributes:
                min_temp = wrapped_state.attributes.get("min_temp")
                if min_temp is not None and isinstance(min_temp, (int, float)):
                    return float(min_temp)
                    
            return 16.0  # Default minimum
            
        except Exception as exc:
            _LOGGER.error(
                "Error getting min_temp from wrapped entity %s: %s",
                self._wrapped_entity_id,
                exc
            )
            return 16.0
    
    @property
    def max_temp(self) -> float:
        """Forward to wrapped entity with defensive programming."""
        try:
            wrapped_state = self.hass.states.get(self._wrapped_entity_id)
            if wrapped_state and wrapped_state.attributes:
                max_temp = wrapped_state.attributes.get("max_temp")
                if max_temp is not None and isinstance(max_temp, (int, float)):
                    return float(max_temp)
                    
            return 30.0  # Default maximum
            
        except Exception as exc:
            _LOGGER.error(
                "Error getting max_temp from wrapped entity %s: %s",
                self._wrapped_entity_id,
                exc
            )
            return 30.0
    
    @property
    def temperature_unit(self) -> str:
        """Forward to wrapped entity with defensive programming."""
        try:
            wrapped_state = self.hass.states.get(self._wrapped_entity_id)
            if wrapped_state and wrapped_state.attributes:
                temp_unit = wrapped_state.attributes.get("temperature_unit")
                if temp_unit and isinstance(temp_unit, str):
                    return temp_unit
                    
            return "°C"  # Default unit
            
        except Exception as exc:
            _LOGGER.error(
                "Error getting temperature_unit from wrapped entity %s: %s",
                self._wrapped_entity_id,
                exc
            )
            return "°C"
    
    @property
    def hvac_action(self) -> Optional[str]:
        """Forward to wrapped entity with defensive programming."""
        try:
            wrapped_state = self.hass.states.get(self._wrapped_entity_id)
            if wrapped_state and wrapped_state.attributes:
                hvac_action = wrapped_state.attributes.get("hvac_action")
                if hvac_action and isinstance(hvac_action, str):
                    return hvac_action
                    
            return None  # No action if not available
            
        except Exception as exc:
            _LOGGER.error(
                "Error getting hvac_action from wrapped entity %s: %s",
                self._wrapped_entity_id,
                exc
            )
            return None
    
    @property
    def fan_mode(self) -> Optional[str]:
        """Forward to wrapped entity with defensive programming."""
        try:
            wrapped_state = self.hass.states.get(self._wrapped_entity_id)
            if wrapped_state and wrapped_state.attributes:
                fan_mode = wrapped_state.attributes.get("fan_mode")
                if fan_mode and isinstance(fan_mode, str):
                    return fan_mode
                    
            return None  # No fan mode if not available
            
        except Exception as exc:
            _LOGGER.error(
                "Error getting fan_mode from wrapped entity %s: %s",
                self._wrapped_entity_id,
                exc
            )
            return None
    
    @property
    def fan_modes(self) -> Optional[List[str]]:
        """Forward to wrapped entity with defensive programming."""
        try:
            wrapped_state = self.hass.states.get(self._wrapped_entity_id)
            if wrapped_state and wrapped_state.attributes:
                fan_modes = wrapped_state.attributes.get("fan_modes")
                if fan_modes and isinstance(fan_modes, list):
                    return fan_modes
                    
            return None  # No fan modes if not available
            
        except Exception as exc:
            _LOGGER.error(
                "Error getting fan_modes from wrapped entity %s: %s",
                self._wrapped_entity_id,
                exc
            )
            return None
    
    @property
    def swing_mode(self) -> Optional[str]:
        """Forward to wrapped entity with defensive programming."""
        try:
            wrapped_state = self.hass.states.get(self._wrapped_entity_id)
            if wrapped_state and wrapped_state.attributes:
                swing_mode = wrapped_state.attributes.get("swing_mode")
                if swing_mode and isinstance(swing_mode, str):
                    return swing_mode
                    
            return None  # No swing mode if not available
            
        except Exception as exc:
            _LOGGER.error(
                "Error getting swing_mode from wrapped entity %s: %s",
                self._wrapped_entity_id,
                exc
            )
            return None
    
    @property
    def swing_modes(self) -> Optional[List[str]]:
        """Forward to wrapped entity with defensive programming."""
        try:
            wrapped_state = self.hass.states.get(self._wrapped_entity_id)
            if wrapped_state and wrapped_state.attributes:
                swing_modes = wrapped_state.attributes.get("swing_modes")
                if swing_modes and isinstance(swing_modes, list):
                    return swing_modes
                    
            return None  # No swing modes if not available
            
        except Exception as exc:
            _LOGGER.error(
                "Error getting swing_modes from wrapped entity %s: %s",
                self._wrapped_entity_id,
                exc
            )
            return None
    
    @property
    def target_temperature_step(self) -> Optional[float]:
        """Forward to wrapped entity with defensive programming."""
        try:
            wrapped_state = self.hass.states.get(self._wrapped_entity_id)
            if wrapped_state and wrapped_state.attributes:
                temp_step = wrapped_state.attributes.get("target_temperature_step")
                if temp_step is not None and isinstance(temp_step, (int, float)):
                    return float(temp_step)
                    
            return 0.5  # Default step
            
        except Exception as exc:
            _LOGGER.error(
                "Error getting target_temperature_step from wrapped entity %s: %s",
                self._wrapped_entity_id,
                exc
            )
            return 0.5
    
    @property
    def current_humidity(self) -> Optional[float]:
        """Forward to wrapped entity with defensive programming."""
        try:
            wrapped_state = self.hass.states.get(self._wrapped_entity_id)
            if wrapped_state and wrapped_state.attributes:
                humidity = wrapped_state.attributes.get("current_humidity")
                if humidity is not None and isinstance(humidity, (int, float)):
                    return float(humidity)
                    
            return None  # No humidity if not available
            
        except Exception as exc:
            _LOGGER.error(
                "Error getting current_humidity from wrapped entity %s: %s",
                self._wrapped_entity_id,
                exc
            )
            return None
    
    @property
    def target_humidity(self) -> Optional[float]:
        """Forward to wrapped entity with defensive programming."""
        try:
            wrapped_state = self.hass.states.get(self._wrapped_entity_id)
            if wrapped_state and wrapped_state.attributes:
                humidity = wrapped_state.attributes.get("target_humidity")
                if humidity is not None and isinstance(humidity, (int, float)):
                    return float(humidity)
                    
            return None  # No target humidity if not available
            
        except Exception as exc:
            _LOGGER.error(
                "Error getting target_humidity from wrapped entity %s: %s",
                self._wrapped_entity_id,
                exc
            )
            return None
    
    @property
    def min_humidity(self) -> Optional[float]:
        """Forward to wrapped entity with defensive programming."""
        try:
            wrapped_state = self.hass.states.get(self._wrapped_entity_id)
            if wrapped_state and wrapped_state.attributes:
                min_humidity = wrapped_state.attributes.get("min_humidity")
                if min_humidity is not None and isinstance(min_humidity, (int, float)):
                    return float(min_humidity)
                    
            return None  # No min humidity if not available
            
        except Exception as exc:
            _LOGGER.error(
                "Error getting min_humidity from wrapped entity %s: %s",
                self._wrapped_entity_id,
                exc
            )
            return None
    
    @property
    def max_humidity(self) -> Optional[float]:
        """Forward to wrapped entity with defensive programming."""
        try:
            wrapped_state = self.hass.states.get(self._wrapped_entity_id)
            if wrapped_state and wrapped_state.attributes:
                max_humidity = wrapped_state.attributes.get("max_humidity")
                if max_humidity is not None and isinstance(max_humidity, (int, float)):
                    return float(max_humidity)
                    
            return None  # No max humidity if not available
            
        except Exception as exc:
            _LOGGER.error(
                "Error getting max_humidity from wrapped entity %s: %s",
                self._wrapped_entity_id,
                exc
            )
            return None
    
    @property
    def target_temperature_high(self) -> Optional[float]:
        """Forward to wrapped entity with defensive programming."""
        try:
            wrapped_state = self.hass.states.get(self._wrapped_entity_id)
            if wrapped_state and wrapped_state.attributes:
                temp_high = wrapped_state.attributes.get("target_temperature_high")
                if temp_high is not None and isinstance(temp_high, (int, float)):
                    return float(temp_high)
                    
            return None  # No high temp if not available
            
        except Exception as exc:
            _LOGGER.error(
                "Error getting target_temperature_high from wrapped entity %s: %s",
                self._wrapped_entity_id,
                exc
            )
            return None
    
    @property
    def target_temperature_low(self) -> Optional[float]:
        """Forward to wrapped entity with defensive programming."""
        try:
            wrapped_state = self.hass.states.get(self._wrapped_entity_id)
            if wrapped_state and wrapped_state.attributes:
                temp_low = wrapped_state.attributes.get("target_temperature_low")
                if temp_low is not None and isinstance(temp_low, (int, float)):
                    return float(temp_low)
                    
            return None  # No low temp if not available
            
        except Exception as exc:
            _LOGGER.error(
                "Error getting target_temperature_low from wrapped entity %s: %s",
                self._wrapped_entity_id,
                exc
            )
            return None
    
    def debug_state(self) -> dict:
        """Return debug information about the entity state."""
        wrapped_state = self.hass.states.get(self._wrapped_entity_id)
        return {
            "smart_climate_target_temp": self._attr_target_temperature,
            "wrapped_entity_id": self._wrapped_entity_id,
            "wrapped_entity_state": wrapped_state.state if wrapped_state else None,
            "wrapped_entity_target_temp": wrapped_state.attributes.get("target_temperature") if wrapped_state and wrapped_state.attributes else None,
            "current_temperature": self.current_temperature,
            "target_temperature": self.target_temperature,
            "hvac_mode": self.hvac_mode,
            "preset_mode": self.preset_mode,
            "room_sensor_temp": self._sensor_manager.get_room_temperature(),
            "last_offset": self._last_offset,
        }
    
    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        if "temperature" in kwargs:
            target_temp = kwargs["temperature"]
            
            # Check if wrapped entity is available
            if not self.available:
                _LOGGER.warning(
                    "Cannot set temperature %.1f°C: wrapped entity %s is unavailable",
                    target_temp,
                    self._wrapped_entity_id
                )
                # Still store the user's desired temperature for when entity recovers
                self._attr_target_temperature = target_temp
                self.async_write_ha_state()
                return
            
            _LOGGER.debug(
                "Setting target temperature to %.1f°C (was %.1f°C) for %s",
                target_temp,
                self._attr_target_temperature or 0,
                self._wrapped_entity_id
            )
            
            # Store the user-requested target temperature
            self._attr_target_temperature = target_temp
            
            # Calculate offset and apply to wrapped entity
            await self._apply_temperature_with_offset(target_temp)
            
            # Schedule a state update to refresh the UI
            self.async_write_ha_state()
            
            _LOGGER.debug(
                "Target temperature successfully set to %.1f°C for %s",
                target_temp,
                self._wrapped_entity_id
            )
    
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode in self.preset_modes:
            _LOGGER.debug(
                "Setting preset mode to %s (was %s) for %s",
                preset_mode,
                self._mode_manager.current_mode,
                self._wrapped_entity_id
            )
            
            self._mode_manager.set_mode(preset_mode)
            
            # Recalculate temperature with new mode
            if self._attr_target_temperature is not None:
                await self._apply_temperature_with_offset(self._attr_target_temperature)
            
            # Schedule a state update to refresh the UI
            self.async_write_ha_state()
            
            _LOGGER.debug(
                "Preset mode set to %s for %s",
                preset_mode,
                self._wrapped_entity_id
            )
    
    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new HVAC mode on wrapped entity."""
        try:
            # Check if wrapped entity is available
            if not self.available:
                _LOGGER.warning(
                    "Cannot set HVAC mode %s: wrapped entity %s is unavailable",
                    hvac_mode,
                    self._wrapped_entity_id
                )
                return
            
            _LOGGER.debug(
                "Setting HVAC mode to %s (was %s) for %s",
                hvac_mode,
                self.hvac_mode,
                self._wrapped_entity_id
            )
            
            await self.hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {
                    "entity_id": self._wrapped_entity_id,
                    "hvac_mode": hvac_mode
                },
                blocking=False
            )
            
            # Schedule immediate state update to refresh the UI
            self.async_write_ha_state()
            
            _LOGGER.debug(
                "HVAC mode set to %s for %s with immediate UI update",
                hvac_mode,
                self._wrapped_entity_id
            )
            
        except Exception as exc:
            _LOGGER.error(
                "Error setting HVAC mode %s for %s: %s",
                hvac_mode,
                self._wrapped_entity_id,
                exc
            )
            # Still trigger UI update for consistency
            self.async_write_ha_state()
    
    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new fan mode on wrapped entity."""
        # Check if wrapped entity is available
        if not self.available:
            _LOGGER.warning(
                "Cannot set fan mode %s: wrapped entity %s is unavailable",
                fan_mode,
                self._wrapped_entity_id
            )
            return
            
        # Check if wrapped entity supports fan modes
        if self.fan_modes and fan_mode in self.fan_modes:
            await self.hass.services.async_call(
                "climate",
                "set_fan_mode",
                {
                    "entity_id": self._wrapped_entity_id,
                    "fan_mode": fan_mode
                },
                blocking=False
            )
            
            _LOGGER.debug(
                "Fan mode set to %s for %s",
                fan_mode,
                self._wrapped_entity_id
            )
        else:
            _LOGGER.warning(
                "Fan mode %s not supported by wrapped entity %s (supported: %s)",
                fan_mode,
                self._wrapped_entity_id,
                self.fan_modes
            )
    
    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set new swing mode on wrapped entity."""
        # Check if wrapped entity is available
        if not self.available:
            _LOGGER.warning(
                "Cannot set swing mode %s: wrapped entity %s is unavailable",
                swing_mode,
                self._wrapped_entity_id
            )
            return
            
        # Check if wrapped entity supports swing modes
        if self.swing_modes and swing_mode in self.swing_modes:
            await self.hass.services.async_call(
                "climate",
                "set_swing_mode",
                {
                    "entity_id": self._wrapped_entity_id,
                    "swing_mode": swing_mode
                },
                blocking=False
            )
            
            _LOGGER.debug(
                "Swing mode set to %s for %s",
                swing_mode,
                self._wrapped_entity_id
            )
        else:
            _LOGGER.warning(
                "Swing mode %s not supported by wrapped entity %s (supported: %s)",
                swing_mode,
                self._wrapped_entity_id,
                self.swing_modes
            )
    
    async def async_set_humidity(self, humidity: float) -> None:
        """Set new target humidity on wrapped entity."""
        # Check if wrapped entity is available
        if not self.available:
            _LOGGER.warning(
                "Cannot set humidity %s: wrapped entity %s is unavailable",
                humidity,
                self._wrapped_entity_id
            )
            return
            
        # Check if wrapped entity supports humidity
        if self.target_humidity is not None:
            await self.hass.services.async_call(
                "climate",
                "set_humidity",
                {
                    "entity_id": self._wrapped_entity_id,
                    "humidity": humidity
                },
                blocking=False
            )
            
            _LOGGER.debug(
                "Humidity set to %s for %s",
                humidity,
                self._wrapped_entity_id
            )
        else:
            _LOGGER.warning(
                "Humidity control not supported by wrapped entity %s",
                self._wrapped_entity_id
            )
    
    async def _apply_temperature_with_offset(self, target_temp: float) -> None:
        """Apply target temperature with calculated offset to wrapped entity."""
        _LOGGER.debug(
            "=== _apply_temperature_with_offset START ===\n"
            "Target temperature: %.1f°C for %s",
            target_temp,
            self._wrapped_entity_id
        )
        
        # Check if wrapped entity is available
        if not self.available:
            _LOGGER.warning(
                "Cannot apply temperature offset: wrapped entity %s is unavailable",
                self._wrapped_entity_id
            )
            return
        
        try:
            # Get current sensor readings
            room_temp = self._sensor_manager.get_room_temperature()
            outdoor_temp = self._sensor_manager.get_outdoor_temperature()
            power_consumption = self._sensor_manager.get_power_consumption()
            
            _LOGGER.debug(
                "Sensor readings: room_temp=%s°C, outdoor_temp=%s°C, power=%sW",
                room_temp, outdoor_temp, power_consumption
            )
            
            # Get wrapped entity's current temperature (AC internal sensor)
            wrapped_state = self.hass.states.get(self._wrapped_entity_id)
            ac_internal_temp = None
            if wrapped_state and wrapped_state.attributes.get("current_temperature"):
                ac_internal_temp = wrapped_state.attributes["current_temperature"]
            
            _LOGGER.debug(
                "AC internal sensor temperature: %s°C",
                ac_internal_temp
            )
            
            # Log room vs target comparison
            if room_temp is not None:
                room_deviation = room_temp - target_temp
                _LOGGER.debug(
                    "Room vs Target: %.1f°C - %.1f°C = %.2f°C %s",
                    room_temp,
                    target_temp,
                    room_deviation,
                    "(room is warmer, needs MORE cooling)" if room_deviation > 0 else "(room is cooler, needs LESS cooling)"
                )
            
            # Skip offset calculation if we don't have essential data
            if room_temp is None or ac_internal_temp is None:
                _LOGGER.warning(
                    "Cannot calculate offset: room_temp=%s, ac_internal_temp=%s",
                    room_temp, ac_internal_temp
                )
                # Send target temperature directly to wrapped entity
                await self._temperature_controller.send_temperature_command(
                    self._wrapped_entity_id,
                    target_temp
                )
                _LOGGER.debug(
                    "Sent target temperature %.1f°C directly to %s (no offset calculation possible)",
                    target_temp,
                    self._wrapped_entity_id
                )
                return
            
            # Create offset input
            from datetime import datetime
            now = datetime.now()
            offset_input = OffsetInput(
                ac_internal_temp=ac_internal_temp,
                room_temp=room_temp,
                outdoor_temp=outdoor_temp,
                mode=self._mode_manager.current_mode,
                power_consumption=power_consumption,
                time_of_day=now.time(),
                day_of_week=now.weekday()
            )
            
            _LOGGER.debug(
                "Created OffsetInput: ac_temp=%.1f°C, room_temp=%.1f°C, mode=%s",
                ac_internal_temp,
                room_temp,
                self._mode_manager.current_mode
            )
            
            # Calculate offset
            offset_result = self._offset_engine.calculate_offset(offset_input)
            self._last_offset = offset_result.offset
            
            _LOGGER.debug(
                "OffsetEngine result: offset=%.2f°C, clamped=%s, reason='%s', confidence=%.2f",
                offset_result.offset,
                offset_result.clamped,
                offset_result.reason,
                offset_result.confidence
            )
            
            # Get mode adjustments
            mode_adjustments = self._mode_manager.get_adjustments()
            
            _LOGGER.debug(
                "Mode adjustments: temp_override=%s, offset_adj=%.2f°C, boost=%.2f°C",
                mode_adjustments.temperature_override,
                mode_adjustments.offset_adjustment,
                mode_adjustments.boost_offset
            )
            
            # Apply offset and limits
            adjusted_temp = self._temperature_controller.apply_offset_and_limits(
                target_temp,
                offset_result.offset,
                mode_adjustments,
                room_temp
            )
            
            _LOGGER.debug(
                "FINAL CALCULATION: target=%.1f°C + offset=%.2f°C = adjusted=%.1f°C",
                target_temp,
                offset_result.offset,
                adjusted_temp
            )
            
            # Send adjusted temperature to wrapped entity
            await self._temperature_controller.send_temperature_command(
                self._wrapped_entity_id,
                adjusted_temp
            )
            
            _LOGGER.info(
                "Temperature adjustment complete: target=%.1f°C -> adjusted=%.1f°C (offset=%.2f°C, reason='%s')",
                target_temp,
                adjusted_temp,
                offset_result.offset,
                offset_result.reason
            )
            
            _LOGGER.debug("=== _apply_temperature_with_offset END ===")
            
            # Schedule learning feedback if learning is enabled
            if (hasattr(self._offset_engine, '_enable_learning') and 
                self._offset_engine._enable_learning and
                offset_result.offset != 0.0):  # Only schedule if there was an offset
                
                # Store current prediction data
                self._last_predicted_offset = offset_result.offset
                self._last_offset_input = offset_input
                
                # Schedule feedback collection
                cancel_callback = async_call_later(
                    self.hass,
                    self._feedback_delay,
                    self._collect_learning_feedback
                )
                self._feedback_tasks.append(cancel_callback)
                
                _LOGGER.debug(
                    "Scheduled learning feedback in %d seconds for offset %.2f°C",
                    self._feedback_delay,
                    offset_result.offset
                )
            
        except Exception as exc:
            _LOGGER.error(
                "Error applying temperature with offset: %s",
                exc,
                exc_info=True
            )
            # Fallback: send target temperature directly
            await self._temperature_controller.send_temperature_command(
                self._wrapped_entity_id,
                target_temp
            )
            _LOGGER.warning(
                "FALLBACK: Sent target temperature %.1f°C directly to %s (no offset) due to error: %s",
                target_temp,
                self._wrapped_entity_id,
                exc
            )
            _LOGGER.debug("=== _apply_temperature_with_offset END (error path) ===")
    
    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        await super().async_added_to_hass()
        
        # Validate that wrapped entity exists and is available
        wrapped_state = self.hass.states.get(self._wrapped_entity_id)
        if not wrapped_state:
            _LOGGER.error(
                "Wrapped entity %s is not available when SmartClimateEntity is added",
                self._wrapped_entity_id
            )
            # Initialize with default if wrapped entity not available
            if self._attr_target_temperature is None:
                self._attr_target_temperature = self._config.get("default_target_temperature", 24.0)
                _LOGGER.debug(
                    "Wrapped entity not available, using default target temperature: %.1f°C",
                    self._attr_target_temperature
                )
        else:
            _LOGGER.debug(
                "Wrapped entity %s is available with state: %s, attributes: %s",
                self._wrapped_entity_id,
                wrapped_state.state,
                list(wrapped_state.attributes.keys()) if wrapped_state.attributes else "None"
            )
            
            # Initialize target temperature from wrapped entity if not already set
            if self._attr_target_temperature is None and wrapped_state.attributes:
                wrapped_target = wrapped_state.attributes.get("target_temperature")
                if wrapped_target is not None and isinstance(wrapped_target, (int, float)):
                    self._attr_target_temperature = float(wrapped_target)
                    _LOGGER.debug(
                        "Initialized target temperature from wrapped entity: %.1f°C",
                        self._attr_target_temperature
                    )
                else:
                    # Set sensible default if wrapped entity has no target temperature
                    self._attr_target_temperature = self._config.get("default_target_temperature", 24.0)
                    _LOGGER.debug(
                        "Wrapped entity has no valid target_temperature attribute (value: %s), using default: %.1f°C",
                        wrapped_target,
                        self._attr_target_temperature
                    )
            elif self._attr_target_temperature is None:
                # Fallback default if wrapped entity has no attributes
                self._attr_target_temperature = self._config.get("default_target_temperature", 24.0)
                _LOGGER.debug(
                    "No attributes from wrapped entity, using default target temperature: %.1f°C",
                    self._attr_target_temperature
                )
        
        # Start listening to sensor updates
        await self._sensor_manager.start_listening()
        
        # Register our new handler for coordinator updates.
        # This replaces the old listener and ensures automatic cleanup on removal.
        self.async_on_remove(
            self._coordinator.async_add_listener(self._handle_coordinator_update)
        )
        
        # Log full debug state for troubleshooting
        debug_info = self.debug_state()
        _LOGGER.debug("SmartClimateEntity added to hass: %s, debug state: %s", self.entity_id, debug_info)
        
        # NEW: Trigger initial temperature calculation after setup
        if self._attr_target_temperature is not None:
            _LOGGER.debug("Triggering startup temperature calculation")
            try:
                # Force coordinator update to get latest offset
                await self._coordinator.async_force_startup_refresh()
                
                # Apply current offset to AC if significant
                await self._apply_temperature_with_offset(self._attr_target_temperature)
                
                _LOGGER.info("Startup temperature update completed successfully")
            except Exception as exc:
                _LOGGER.warning("Startup temperature update failed: %s", exc)
        
        _LOGGER.debug("SmartClimateEntity fully initialized: %s", self.entity_id)
        
    def _sync_target_temperature_from_wrapped(self) -> bool:
        """Sync target temperature from wrapped entity if it has changed.
        
        Returns:
            bool: True if temperature was updated, False otherwise
        """
        try:
            wrapped_state = self.hass.states.get(self._wrapped_entity_id)
            if wrapped_state and wrapped_state.attributes:
                wrapped_target = wrapped_state.attributes.get("target_temperature")
                if wrapped_target is not None and isinstance(wrapped_target, (int, float)):
                    wrapped_temp = float(wrapped_target)
                    # Only update if there's a significant difference (more than 0.1°C)
                    if self._attr_target_temperature is None or abs(wrapped_temp - self._attr_target_temperature) > 0.1:
                        old_temp = self._attr_target_temperature
                        self._attr_target_temperature = wrapped_temp
                        _LOGGER.info(
                            "Target temperature synced from wrapped entity: %.1f°C → %.1f°C (change: %.1f°C)",
                            old_temp if old_temp is not None else 0.0,
                            wrapped_temp,
                            wrapped_temp - (old_temp if old_temp is not None else 0.0)
                        )
                        return True
                    else:
                        _LOGGER.debug(
                            "Target temp sync: no significant change (wrapped=%.1f°C, current=%.1f°C, diff=%.1f°C)",
                            wrapped_temp,
                            self._attr_target_temperature,
                            abs(wrapped_temp - self._attr_target_temperature)
                        )
            else:
                _LOGGER.debug(
                    "Target temp sync: wrapped entity has no valid target_temperature (state=%s)",
                    wrapped_state.state if wrapped_state else "None"
                )
            return False
        except Exception as exc:
            _LOGGER.error(
                "Error syncing target_temperature from wrapped entity %s: %s",
                self._wrapped_entity_id,
                exc
            )
            return False
    
    async def _collect_learning_feedback(self, _now) -> None:
        """Collect learning feedback after temperature adjustment settles.
        
        This method is called after a delay to measure how well the predicted
        offset worked by comparing current temperatures.
        
        Args:
            _now: Current time (required by async_call_later but not used)
        """
        if (self._last_predicted_offset is None or 
            self._last_offset_input is None):
            _LOGGER.debug("No prediction data available for feedback")
            return
        
        try:
            # Get current temperatures
            current_room_temp = self._sensor_manager.get_room_temperature()
            if current_room_temp is None:
                _LOGGER.debug("Room temperature unavailable for feedback")
                return
            
            # Get current AC internal temperature
            wrapped_state = self.hass.states.get(self._wrapped_entity_id)
            if not wrapped_state or not wrapped_state.attributes:
                _LOGGER.debug("Wrapped entity unavailable for feedback")
                return
            
            current_ac_temp = wrapped_state.attributes.get("current_temperature")
            if current_ac_temp is None:
                _LOGGER.debug("AC internal temperature unavailable for feedback")
                return
            
            # Calculate actual offset that exists now
            # The offset is: AC internal temp - Room temp
            # When room is warmer than AC (cooling): AC=22, Room=25 -> offset = -3 (need to cool MORE)
            # When room is cooler than AC (overcooled): AC=25, Room=22 -> offset = 3 (need to cool LESS)
            actual_offset = float(current_ac_temp) - current_room_temp
            
            # Record the performance
            self._offset_engine.record_actual_performance(
                predicted_offset=self._last_predicted_offset,
                actual_offset=actual_offset,  # Use the offset directly without negation
                input_data=self._last_offset_input
            )
            
            _LOGGER.debug(
                "Learning feedback collected: predicted_offset=%.2f°C, actual_offset=%.2f°C, "
                "ac_temp=%.1f°C, room_temp=%.1f°C",
                self._last_predicted_offset,
                actual_offset,
                current_ac_temp,
                current_room_temp
            )
            
        except Exception as exc:
            _LOGGER.warning("Error collecting learning feedback: %s", exc)
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator to apply periodic adjustments."""
        _LOGGER.debug("=== Coordinator update received ===")
        
        if not self._coordinator.data:
            _LOGGER.debug("Coordinator update skipped: no data available.")
            return

        # Only apply automatic adjustments if the climate entity is active (not OFF)
        if self.hvac_mode == HVACMode.OFF:
            _LOGGER.debug("Skipping automatic adjustment: HVAC mode is OFF.")
            self.async_write_ha_state()  # Update state even if off
            return

        new_offset = self._coordinator.data.calculated_offset
        
        _LOGGER.debug(
            "Coordinator data: calculated_offset=%.2f°C, last_applied_offset=%.2f°C, "
            "room_temp=%s, mode_adjustments=%s",
            new_offset,
            self._last_offset,
            self._coordinator.data.room_temp if hasattr(self._coordinator.data, 'room_temp') else "N/A",
            self._coordinator.data.mode_adjustments if hasattr(self._coordinator.data, 'mode_adjustments') else "N/A"
        )
        
        # Check for startup scenario OR significant offset change OR room temperature deviation
        is_startup = getattr(self._coordinator.data, 'is_startup_calculation', False)
        offset_change = abs(new_offset - self._last_offset)
        
        # Calculate room temperature deviation from target
        room_temp = self._coordinator.data.room_temp if self._coordinator.data else None
        target_temp = self.target_temperature
        room_deviation = abs(room_temp - target_temp) if room_temp is not None and target_temp is not None else 0
        
        if is_startup or offset_change > OFFSET_UPDATE_THRESHOLD or room_deviation > TEMP_DEVIATION_THRESHOLD:
            _LOGGER.info(
                "Triggering AC temperature update: startup=%s, offset_change=%.2f°C, room_deviation=%.2f°C "
                "(last_offset=%.2f°C, new_offset=%.2f°C, offset_threshold=%.2f°C, "
                "room_temp=%.1f°C, target_temp=%.1f°C, deviation_threshold=%.1f°C)",
                is_startup,
                offset_change,
                room_deviation,
                self._last_offset,
                new_offset,
                OFFSET_UPDATE_THRESHOLD,
                room_temp if room_temp is not None else 0,
                target_temp if target_temp is not None else 0,
                TEMP_DEVIATION_THRESHOLD
            )
            
            # To call an async method from this synchronous callback, schedule it as a task.
            # This re-applies the current target temperature with the new offset.
            if self.target_temperature is not None:
                _LOGGER.debug(
                    "Scheduling temperature adjustment task with target=%.1f°C",
                    self.target_temperature
                )
                self.hass.async_create_task(
                    self._apply_temperature_with_offset(self.target_temperature)
                )
            else:
                _LOGGER.warning("Cannot apply automatic adjustment: target_temperature is None")
        else:
            _LOGGER.debug(
                "No AC update needed: startup=%s, offset_change=%.2f°C (%.2f°C -> %.2f°C) within threshold %.2f°C, "
                "room_deviation=%.2f°C (room=%.1f°C, target=%.1f°C) within threshold %.1f°C",
                is_startup,
                offset_change,
                self._last_offset, 
                new_offset, 
                OFFSET_UPDATE_THRESHOLD,
                room_deviation,
                room_temp if room_temp is not None else 0,
                target_temp if target_temp is not None else 0,
                TEMP_DEVIATION_THRESHOLD
            )

        # Always update the state to reflect the latest sensor values from the coordinator
        self.async_write_ha_state()
        _LOGGER.debug("=== Coordinator update complete ===")
    
    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        # ClimateEntity doesn't have async_will_remove_from_hass, but Entity does
        # Check if parent has the method before calling
        if hasattr(super(), 'async_will_remove_from_hass'):
            await super().async_will_remove_from_hass()
        
        # Cancel any pending feedback tasks
        task_count = len(self._feedback_tasks)
        for cancel_func in self._feedback_tasks:
            if cancel_func:
                cancel_func()
        self._feedback_tasks.clear()
        if task_count > 0:
            _LOGGER.debug("Cancelled %d pending feedback tasks", task_count)
        
        # Stop listening to sensor updates
        await self._sensor_manager.stop_listening()
        
        _LOGGER.debug("SmartClimateEntity removed from hass: %s", self.unique_id)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up Smart Climate entities from a config entry."""
    from datetime import timedelta
    
    from .sensor_manager import SensorManager
    from .offset_engine import OffsetEngine
    from .mode_manager import ModeManager
    from .temperature_controller import TemperatureController, TemperatureLimits
    from .coordinator import SmartClimateCoordinator
    from .integration import validate_configuration, get_unique_id, get_entity_name
    from .const import DOMAIN
    
    _LOGGER.info("Setting up Smart Climate platform from config entry")
    
    # Get configuration and shared offset engine
    config = hass.data[DOMAIN][config_entry.entry_id]["config"]
    # Access the correct offset engine using the climate entity ID as the key
    climate_entity_id = config["climate_entity"]
    try:
        offset_engine = hass.data[DOMAIN][config_entry.entry_id]["offset_engines"][climate_entity_id]
    except KeyError as exc:
        raise HomeAssistantError(
            f"Offset engine not found for climate entity '{climate_entity_id}'. "
            f"This indicates a setup issue. Available engines: "
            f"{list(hass.data[DOMAIN][config_entry.entry_id]['offset_engines'].keys())}"
        ) from exc
    
    _LOGGER.debug("Config entry data: %s", config)
    _LOGGER.debug("Using shared OffsetEngine instance")
    
    try:
        # Validate configuration before proceeding
        _LOGGER.debug("Validating configuration")
        await validate_configuration(hass, config)
        
        # Create all components with dependencies following architecture Section 4.1
        _LOGGER.debug("Creating SensorManager with sensors: room=%s, outdoor=%s, power=%s", 
                      config["room_sensor"], config.get("outdoor_sensor"), config.get("power_sensor"))
        
        sensor_manager = SensorManager(
            hass,
            config["room_sensor"],
            config.get("outdoor_sensor"),
            config.get("power_sensor")
        )
        
        _LOGGER.debug("Creating ModeManager with config")
        mode_manager = ModeManager(config)
        
        _LOGGER.debug("Creating TemperatureController with limits: min=%s, max=%s, gradual_rate=%s", 
                      config.get("min_temperature", 16), config.get("max_temperature", 30),
                      config.get("gradual_adjustment_rate", 0.5))
        
        limits = TemperatureLimits(
            min_temperature=config.get("min_temperature", 16),
            max_temperature=config.get("max_temperature", 30)
        )
        temperature_controller = TemperatureController(
            hass, 
            limits,
            gradual_adjustment_rate=config.get("gradual_adjustment_rate", 0.5)
        )
        
        _LOGGER.debug("Creating SmartClimateCoordinator with update interval: %s", 
                      config.get("update_interval", 180))
        
        coordinator = SmartClimateCoordinator(
            hass,
            config.get("update_interval", 180),
            sensor_manager,
            offset_engine,
            mode_manager
        )
        
        # Create entity with all dependencies
        _LOGGER.debug("Creating SmartClimateEntity with wrapped entity: %s", config["climate_entity"])
        
        entity = SmartClimateEntity(
            hass,
            config,
            config["climate_entity"],
            config["room_sensor"],
            offset_engine,
            sensor_manager,
            mode_manager,
            temperature_controller,
            coordinator
        )
        
        # Set unique ID and name from integration utilities
        entity._attr_unique_id = get_unique_id(config)
        entity._attr_name = get_entity_name(config)
        
        _LOGGER.debug("Entity unique_id: %s, name: %s", entity._attr_unique_id, entity._attr_name)
        
        # Start background tasks
        _LOGGER.debug("Starting sensor manager and coordinator")
        await sensor_manager.start_listening()
        await coordinator.async_config_entry_first_refresh()
        
        # Add entity to Home Assistant
        _LOGGER.info("Adding SmartClimateEntity to Home Assistant")
        async_add_entities([entity])
        
        _LOGGER.info("Smart Climate platform setup completed successfully")
        
    except Exception as exc:
        _LOGGER.error("Error setting up Smart Climate platform: %s", exc, exc_info=True)
        raise