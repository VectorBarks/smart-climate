"""ABOUTME: Smart Climate Entity for Home Assistant integration.
Virtual climate entity that wraps any existing climate entity with intelligent offset compensation."""

import logging
from typing import Optional, List

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_OFF, HVAC_MODE_COOL, HVAC_MODE_HEAT, HVAC_MODE_AUTO,
    SUPPORT_TARGET_TEMPERATURE, SUPPORT_PRESET_MODE
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity

from .models import OffsetInput, OffsetResult
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


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
        
        # Initialize attributes
        self._attr_target_temperature = None
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
    def current_temperature(self) -> Optional[float]:
        """Return room sensor temperature."""
        return self._sensor_manager.get_room_temperature()
    
    @property
    def target_temperature(self) -> Optional[float]:
        """Return the user-facing target temperature."""
        return self._attr_target_temperature
    
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
        """Forward to wrapped entity."""
        wrapped_state = self.hass.states.get(self._wrapped_entity_id)
        return wrapped_state.state if wrapped_state else HVAC_MODE_OFF
    
    @property
    def hvac_modes(self) -> List[str]:
        """Forward to wrapped entity."""
        wrapped_state = self.hass.states.get(self._wrapped_entity_id)
        if wrapped_state and wrapped_state.attributes.get("hvac_modes"):
            return wrapped_state.attributes["hvac_modes"]
        return []
    
    @property
    def supported_features(self) -> int:
        """Forward to wrapped entity."""
        wrapped_state = self.hass.states.get(self._wrapped_entity_id)
        if wrapped_state and wrapped_state.attributes.get("supported_features"):
            return wrapped_state.attributes["supported_features"]
        return 0
    
    @property
    def min_temp(self) -> float:
        """Forward to wrapped entity."""
        wrapped_state = self.hass.states.get(self._wrapped_entity_id)
        if wrapped_state and wrapped_state.attributes.get("min_temp"):
            return wrapped_state.attributes["min_temp"]
        return 16.0  # Default minimum
    
    @property
    def max_temp(self) -> float:
        """Forward to wrapped entity."""
        wrapped_state = self.hass.states.get(self._wrapped_entity_id)
        if wrapped_state and wrapped_state.attributes.get("max_temp"):
            return wrapped_state.attributes["max_temp"]
        return 30.0  # Default maximum
    
    @property
    def temperature_unit(self) -> str:
        """Forward to wrapped entity."""
        wrapped_state = self.hass.states.get(self._wrapped_entity_id)
        if wrapped_state and wrapped_state.attributes.get("temperature_unit"):
            return wrapped_state.attributes["temperature_unit"]
        return "°C"  # Default unit
    
    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        if "temperature" in kwargs:
            target_temp = kwargs["temperature"]
            self._attr_target_temperature = target_temp
            
            # Calculate offset and apply to wrapped entity
            await self._apply_temperature_with_offset(target_temp)
            
            _LOGGER.debug(
                "Target temperature set to %.1f°C for %s",
                target_temp,
                self._wrapped_entity_id
            )
    
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode in self.preset_modes:
            self._mode_manager.set_mode(preset_mode)
            
            # Recalculate temperature with new mode
            if self._attr_target_temperature is not None:
                await self._apply_temperature_with_offset(self._attr_target_temperature)
            
            _LOGGER.debug(
                "Preset mode set to %s for %s",
                preset_mode,
                self._wrapped_entity_id
            )
    
    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new HVAC mode on wrapped entity."""
        await self.hass.services.async_call(
            "climate",
            "set_hvac_mode",
            {
                "entity_id": self._wrapped_entity_id,
                "hvac_mode": hvac_mode
            },
            blocking=False
        )
        
        _LOGGER.debug(
            "HVAC mode set to %s for %s",
            hvac_mode,
            self._wrapped_entity_id
        )
    
    async def _apply_temperature_with_offset(self, target_temp: float) -> None:
        """Apply target temperature with calculated offset to wrapped entity."""
        try:
            # Get current sensor readings
            room_temp = self._sensor_manager.get_room_temperature()
            outdoor_temp = self._sensor_manager.get_outdoor_temperature()
            power_consumption = self._sensor_manager.get_power_consumption()
            
            # Get wrapped entity's current temperature (AC internal sensor)
            wrapped_state = self.hass.states.get(self._wrapped_entity_id)
            ac_internal_temp = None
            if wrapped_state and wrapped_state.attributes.get("current_temperature"):
                ac_internal_temp = wrapped_state.attributes["current_temperature"]
            
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
            
            # Calculate offset
            offset_result = self._offset_engine.calculate_offset(offset_input)
            self._last_offset = offset_result.offset
            
            # Get mode adjustments
            mode_adjustments = self._mode_manager.get_adjustments()
            
            # Apply offset and limits
            adjusted_temp = self._temperature_controller.apply_offset_and_limits(
                target_temp,
                offset_result.offset,
                mode_adjustments
            )
            
            # Send adjusted temperature to wrapped entity
            await self._temperature_controller.send_temperature_command(
                self._wrapped_entity_id,
                adjusted_temp
            )
            
            _LOGGER.debug(
                "Applied offset %.2f°C: target=%.1f°C, adjusted=%.1f°C, reason=%s",
                offset_result.offset,
                target_temp,
                adjusted_temp,
                offset_result.reason
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
    
    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        await super().async_added_to_hass()
        
        # Start listening to sensor updates
        await self._sensor_manager.start_listening()
        
        # Register for coordinator updates
        self._coordinator.async_add_listener(self.async_write_ha_state)
        
        _LOGGER.debug("SmartClimateEntity added to hass: %s", self.entity_id)
    
    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        await super().async_will_remove_from_hass()
        
        # Stop listening to sensor updates
        await self._sensor_manager.stop_listening()
        
        _LOGGER.debug("SmartClimateEntity removed from hass: %s", self.entity_id)


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
    
    # Get configuration
    config = config_entry.data
    
    _LOGGER.debug("Config entry data: %s", config)
    
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
        
        _LOGGER.debug("Creating OffsetEngine with config: %s", 
                      {k: v for k, v in config.items() if k in ["max_offset", "ml_enabled"]})
        
        offset_engine = OffsetEngine(config)
        
        _LOGGER.debug("Creating ModeManager with config")
        mode_manager = ModeManager(config)
        
        _LOGGER.debug("Creating TemperatureController with limits: min=%s, max=%s", 
                      config.get("min_temperature", 16), config.get("max_temperature", 30))
        
        limits = TemperatureLimits(
            min_temperature=config.get("min_temperature", 16),
            max_temperature=config.get("max_temperature", 30)
        )
        temperature_controller = TemperatureController(hass, limits)
        
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