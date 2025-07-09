"""ABOUTME: Config flow for Smart Climate Control integration.
Provides UI-based configuration with entity selectors and validation."""

import logging
from typing import Dict, Any, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.const import CONF_NAME

from .const import (
    DOMAIN,
    CONF_CLIMATE_ENTITY,
    CONF_ROOM_SENSOR,
    CONF_OUTDOOR_SENSOR,
    CONF_POWER_SENSOR,
    CONF_MAX_OFFSET,
    CONF_MIN_TEMPERATURE,
    CONF_MAX_TEMPERATURE,
    CONF_UPDATE_INTERVAL,
    CONF_ML_ENABLED,
    CONF_AWAY_TEMPERATURE,
    CONF_SLEEP_OFFSET,
    CONF_BOOST_OFFSET,
    CONF_GRADUAL_ADJUSTMENT_RATE,
    CONF_FEEDBACK_DELAY,
    CONF_ENABLE_LEARNING,
    CONF_POWER_IDLE_THRESHOLD,
    CONF_POWER_MIN_THRESHOLD,
    CONF_POWER_MAX_THRESHOLD,
    CONF_DEFAULT_TARGET_TEMPERATURE,
    CONF_ENABLE_RETRY,
    CONF_MAX_RETRY_ATTEMPTS,
    CONF_INITIAL_TIMEOUT,
    DEFAULT_MAX_OFFSET,
    DEFAULT_MIN_TEMPERATURE,
    DEFAULT_MAX_TEMPERATURE,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_ML_ENABLED,
    DEFAULT_AWAY_TEMPERATURE,
    DEFAULT_SLEEP_OFFSET,
    DEFAULT_BOOST_OFFSET,
    DEFAULT_GRADUAL_ADJUSTMENT_RATE,
    DEFAULT_FEEDBACK_DELAY,
    DEFAULT_ENABLE_LEARNING,
    DEFAULT_POWER_IDLE_THRESHOLD,
    DEFAULT_POWER_MIN_THRESHOLD,
    DEFAULT_POWER_MAX_THRESHOLD,
    DEFAULT_TARGET_TEMPERATURE,
    DEFAULT_ENABLE_RETRY,
    DEFAULT_MAX_RETRY_ATTEMPTS,
    DEFAULT_INITIAL_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class SmartClimateConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smart Climate Control."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._errors = {}

    def _add_power_threshold_fields(self, schema: vol.Schema) -> vol.Schema:
        """Add power threshold fields to the schema."""
        schema_dict = dict(schema.schema)
        schema_dict.update({
            vol.Optional(CONF_POWER_IDLE_THRESHOLD, default=DEFAULT_POWER_IDLE_THRESHOLD): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=1000,
                    step=10,
                    unit_of_measurement="W",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_POWER_MIN_THRESHOLD, default=DEFAULT_POWER_MIN_THRESHOLD): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=1000,
                    step=10,
                    unit_of_measurement="W",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_POWER_MAX_THRESHOLD, default=DEFAULT_POWER_MAX_THRESHOLD): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=1000,
                    step=10,
                    unit_of_measurement="W",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        })
        return vol.Schema(schema_dict)
    
    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate user input
            try:
                validated_input = await self._validate_input(user_input)
                
                # Check if already configured
                if await self._already_configured(validated_input[CONF_CLIMATE_ENTITY]):
                    errors[CONF_CLIMATE_ENTITY] = "already_configured"
                else:
                    # Create the config entry
                    return self.async_create_entry(
                        title="Smart Climate Control",
                        data=validated_input,
                    )
            except vol.Invalid as ex:
                # Handle validation errors
                if "climate_entity" in str(ex):
                    errors[CONF_CLIMATE_ENTITY] = "entity_not_found"
                elif "room_sensor" in str(ex):
                    errors[CONF_ROOM_SENSOR] = "entity_not_found"
                elif "outdoor_sensor" in str(ex):
                    errors[CONF_OUTDOOR_SENSOR] = "entity_not_found"
                elif "power_sensor" in str(ex):
                    errors[CONF_POWER_SENSOR] = "entity_not_found"
                elif "temperature_range" in str(ex):
                    errors["base"] = "invalid_temperature_range"
                elif "away_temperature_out_of_range" in str(ex):
                    errors["away_temperature"] = "away_temperature_out_of_range"
                elif "power threshold" in str(ex):
                    errors["base"] = "power_threshold_invalid"
                else:
                    errors["base"] = "unknown"
                    _LOGGER.exception("Unexpected error in config flow: %s", ex)

        # Get available entities for selectors
        climate_entities = await self._get_climate_entities()
        temperature_sensors = await self._get_temperature_sensors()
        power_sensors = await self._get_power_sensors()

        # Build the form schema
        data_schema = vol.Schema({
            vol.Required(CONF_CLIMATE_ENTITY): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=entity_id, label=f"{entity_id} ({friendly_name})")
                        for entity_id, friendly_name in climate_entities.items()
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(CONF_ROOM_SENSOR): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=entity_id, label=f"{entity_id} ({friendly_name})")
                        for entity_id, friendly_name in temperature_sensors.items()
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_OUTDOOR_SENSOR): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=entity_id, label=f"{entity_id} ({friendly_name})")
                        for entity_id, friendly_name in temperature_sensors.items()
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_POWER_SENSOR): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=entity_id, label=f"{entity_id} ({friendly_name})")
                        for entity_id, friendly_name in power_sensors.items()
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_MAX_OFFSET, default=DEFAULT_MAX_OFFSET): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1.0,
                    max=10.0,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_MIN_TEMPERATURE, default=DEFAULT_MIN_TEMPERATURE): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=10.0,
                    max=25.0,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_MAX_TEMPERATURE, default=DEFAULT_MAX_TEMPERATURE): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=20.0,
                    max=35.0,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=30,
                    max=600,
                    step=30,
                    unit_of_measurement="seconds",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_ML_ENABLED, default=DEFAULT_ML_ENABLED): selector.BooleanSelector(),
            vol.Optional(CONF_AWAY_TEMPERATURE, default=DEFAULT_AWAY_TEMPERATURE): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=10.0,
                    max=35.0,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_SLEEP_OFFSET, default=DEFAULT_SLEEP_OFFSET): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=-5.0,
                    max=5.0,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_BOOST_OFFSET, default=DEFAULT_BOOST_OFFSET): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=-10.0,
                    max=0.0,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_GRADUAL_ADJUSTMENT_RATE, default=DEFAULT_GRADUAL_ADJUSTMENT_RATE): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.1,
                    max=2.0,
                    step=0.1,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_FEEDBACK_DELAY, default=DEFAULT_FEEDBACK_DELAY): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=10,
                    max=300,
                    step=5,
                    unit_of_measurement="seconds",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_ENABLE_LEARNING, default=DEFAULT_ENABLE_LEARNING): selector.BooleanSelector(),
            vol.Optional(CONF_DEFAULT_TARGET_TEMPERATURE, default=DEFAULT_TARGET_TEMPERATURE): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=16.0,
                    max=30.0,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_ENABLE_RETRY, default=DEFAULT_ENABLE_RETRY): selector.BooleanSelector(),
            vol.Optional(CONF_MAX_RETRY_ATTEMPTS, default=DEFAULT_MAX_RETRY_ATTEMPTS): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=10,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_INITIAL_TIMEOUT, default=DEFAULT_INITIAL_TIMEOUT): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=30,
                    max=300,
                    step=30,
                    unit_of_measurement="seconds",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        })
        
        # Add power threshold fields if power sensor is provided in user_input
        # These fields are conditional on power sensor selection
        if user_input and user_input.get(CONF_POWER_SENSOR):
            data_schema = self._add_power_threshold_fields(data_schema)

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def _validate_input(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the user input."""
        validated = {}
        
        # Validate climate entity
        climate_entity = user_input.get(CONF_CLIMATE_ENTITY)
        if climate_entity:
            if not await self._entity_exists(climate_entity, "climate"):
                raise vol.Invalid("climate_entity not found")
            validated[CONF_CLIMATE_ENTITY] = climate_entity
        
        # Validate room sensor
        room_sensor = user_input.get(CONF_ROOM_SENSOR)
        if room_sensor:
            if not await self._entity_exists(room_sensor, "sensor"):
                raise vol.Invalid("room_sensor not found")
            validated[CONF_ROOM_SENSOR] = room_sensor
        
        # Validate optional outdoor sensor
        outdoor_sensor = user_input.get(CONF_OUTDOOR_SENSOR)
        if outdoor_sensor:
            if not await self._entity_exists(outdoor_sensor, "sensor"):
                raise vol.Invalid("outdoor_sensor not found")
            validated[CONF_OUTDOOR_SENSOR] = outdoor_sensor
        
        # Validate optional power sensor
        power_sensor = user_input.get(CONF_POWER_SENSOR)
        if power_sensor:
            if not await self._entity_exists(power_sensor, "sensor"):
                raise vol.Invalid("power_sensor not found")
            validated[CONF_POWER_SENSOR] = power_sensor
        
        # Validate temperature range
        min_temp = user_input.get(CONF_MIN_TEMPERATURE, DEFAULT_MIN_TEMPERATURE)
        max_temp = user_input.get(CONF_MAX_TEMPERATURE, DEFAULT_MAX_TEMPERATURE)
        if min_temp >= max_temp:
            raise vol.Invalid("temperature_range invalid")
        
        # Validate away temperature is within min/max range
        away_temp = user_input.get(CONF_AWAY_TEMPERATURE, DEFAULT_AWAY_TEMPERATURE)
        if away_temp < min_temp or away_temp > max_temp:
            raise vol.Invalid("away_temperature_out_of_range")
        
        # Copy other validated values
        validated[CONF_MAX_OFFSET] = user_input.get(CONF_MAX_OFFSET, DEFAULT_MAX_OFFSET)
        validated[CONF_MIN_TEMPERATURE] = min_temp
        validated[CONF_MAX_TEMPERATURE] = max_temp
        validated[CONF_UPDATE_INTERVAL] = user_input.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        validated[CONF_ML_ENABLED] = user_input.get(CONF_ML_ENABLED, DEFAULT_ML_ENABLED)
        validated[CONF_AWAY_TEMPERATURE] = away_temp
        validated[CONF_SLEEP_OFFSET] = user_input.get(CONF_SLEEP_OFFSET, DEFAULT_SLEEP_OFFSET)
        validated[CONF_BOOST_OFFSET] = user_input.get(CONF_BOOST_OFFSET, DEFAULT_BOOST_OFFSET)
        validated[CONF_GRADUAL_ADJUSTMENT_RATE] = user_input.get(CONF_GRADUAL_ADJUSTMENT_RATE, DEFAULT_GRADUAL_ADJUSTMENT_RATE)
        validated[CONF_FEEDBACK_DELAY] = user_input.get(CONF_FEEDBACK_DELAY, DEFAULT_FEEDBACK_DELAY)
        validated[CONF_ENABLE_LEARNING] = user_input.get(CONF_ENABLE_LEARNING, DEFAULT_ENABLE_LEARNING)
        validated[CONF_DEFAULT_TARGET_TEMPERATURE] = user_input.get(CONF_DEFAULT_TARGET_TEMPERATURE, DEFAULT_TARGET_TEMPERATURE)
        validated[CONF_ENABLE_RETRY] = user_input.get(CONF_ENABLE_RETRY, DEFAULT_ENABLE_RETRY)
        validated[CONF_MAX_RETRY_ATTEMPTS] = user_input.get(CONF_MAX_RETRY_ATTEMPTS, DEFAULT_MAX_RETRY_ATTEMPTS)
        validated[CONF_INITIAL_TIMEOUT] = user_input.get(CONF_INITIAL_TIMEOUT, DEFAULT_INITIAL_TIMEOUT)
        
        # Validate power thresholds if power sensor is configured
        if power_sensor:
            idle_threshold = user_input.get(CONF_POWER_IDLE_THRESHOLD, DEFAULT_POWER_IDLE_THRESHOLD)
            min_threshold = user_input.get(CONF_POWER_MIN_THRESHOLD, DEFAULT_POWER_MIN_THRESHOLD)
            max_threshold = user_input.get(CONF_POWER_MAX_THRESHOLD, DEFAULT_POWER_MAX_THRESHOLD)
            
            # Validate that idle < min < max
            if not (idle_threshold < min_threshold < max_threshold):
                raise vol.Invalid("power threshold order invalid: must be idle < min < max")
            
            validated[CONF_POWER_IDLE_THRESHOLD] = idle_threshold
            validated[CONF_POWER_MIN_THRESHOLD] = min_threshold
            validated[CONF_POWER_MAX_THRESHOLD] = max_threshold
        
        return validated

    async def _entity_exists(self, entity_id: str, domain: str) -> bool:
        """Check if an entity exists and is from the correct domain."""
        state = self.hass.states.get(entity_id)
        if state is None:
            return False
        return entity_id.startswith(f"{domain}.")

    async def _already_configured(self, climate_entity: str) -> bool:
        """Check if the climate entity is already configured."""
        for config_entry in self.hass.config_entries.async_entries(DOMAIN):
            if config_entry.data.get(CONF_CLIMATE_ENTITY) == climate_entity:
                return True
        return False

    async def _get_climate_entities(self) -> Dict[str, str]:
        """Get all climate entities."""
        entities = {}
        
        for state in self.hass.states.async_all():
            if state.entity_id.startswith("climate."):
                friendly_name = state.attributes.get("friendly_name", state.entity_id)
                entities[state.entity_id] = friendly_name
        
        return entities

    async def _get_temperature_sensors(self) -> Dict[str, str]:
        """Get all temperature sensors."""
        entities = {}
        
        for state in self.hass.states.async_all():
            if (
                state.entity_id.startswith("sensor.") and
                state.attributes.get("device_class") == "temperature"
            ):
                friendly_name = state.attributes.get("friendly_name", state.entity_id)
                entities[state.entity_id] = friendly_name
        
        return entities

    async def _get_power_sensors(self) -> Dict[str, str]:
        """Get all power sensors."""
        entities = {}
        
        for state in self.hass.states.async_all():
            if (
                state.entity_id.startswith("sensor.") and
                state.attributes.get("device_class") == "power"
            ):
                friendly_name = state.attributes.get("friendly_name", state.entity_id)
                entities[state.entity_id] = friendly_name
        
        return entities

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> "SmartClimateOptionsFlow":
        """Get the options flow for this handler."""
        return SmartClimateOptionsFlow()


class SmartClimateOptionsFlow(config_entries.OptionsFlow):
    """Handle Smart Climate Control options."""
    
    def _add_power_threshold_fields_options(self, schema: vol.Schema, current_config: dict, current_options: dict) -> vol.Schema:
        """Add power threshold fields to the options schema."""
        schema_dict = dict(schema.schema)
        schema_dict.update({
            vol.Optional(
                CONF_POWER_IDLE_THRESHOLD,
                default=current_options.get(CONF_POWER_IDLE_THRESHOLD, current_config.get(CONF_POWER_IDLE_THRESHOLD, DEFAULT_POWER_IDLE_THRESHOLD))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=1000,
                    step=10,
                    unit_of_measurement="W",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_POWER_MIN_THRESHOLD,
                default=current_options.get(CONF_POWER_MIN_THRESHOLD, current_config.get(CONF_POWER_MIN_THRESHOLD, DEFAULT_POWER_MIN_THRESHOLD))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=1000,
                    step=10,
                    unit_of_measurement="W",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_POWER_MAX_THRESHOLD,
                default=current_options.get(CONF_POWER_MAX_THRESHOLD, current_config.get(CONF_POWER_MAX_THRESHOLD, DEFAULT_POWER_MAX_THRESHOLD))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=1000,
                    step=10,
                    unit_of_measurement="W",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        })
        return vol.Schema(schema_dict)

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_config = self.config_entry.data
        current_options = self.config_entry.options
        
        data_schema = vol.Schema({
            vol.Optional(
                CONF_MAX_OFFSET,
                default=current_options.get(CONF_MAX_OFFSET, current_config.get(CONF_MAX_OFFSET, DEFAULT_MAX_OFFSET))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1.0,
                    max=10.0,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_MIN_TEMPERATURE,
                default=current_options.get(CONF_MIN_TEMPERATURE, current_config.get(CONF_MIN_TEMPERATURE, DEFAULT_MIN_TEMPERATURE))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=10.0,
                    max=25.0,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_MAX_TEMPERATURE,
                default=current_options.get(CONF_MAX_TEMPERATURE, current_config.get(CONF_MAX_TEMPERATURE, DEFAULT_MAX_TEMPERATURE))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=20.0,
                    max=35.0,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_UPDATE_INTERVAL,
                default=current_options.get(CONF_UPDATE_INTERVAL, current_config.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=30,
                    max=600,
                    step=30,
                    unit_of_measurement="seconds",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_ML_ENABLED,
                default=current_options.get(CONF_ML_ENABLED, current_config.get(CONF_ML_ENABLED, DEFAULT_ML_ENABLED))
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_AWAY_TEMPERATURE,
                default=current_options.get(CONF_AWAY_TEMPERATURE, current_config.get(CONF_AWAY_TEMPERATURE, DEFAULT_AWAY_TEMPERATURE))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=10.0,
                    max=35.0,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_SLEEP_OFFSET,
                default=current_options.get(CONF_SLEEP_OFFSET, current_config.get(CONF_SLEEP_OFFSET, DEFAULT_SLEEP_OFFSET))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=-5.0,
                    max=5.0,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_BOOST_OFFSET,
                default=current_options.get(CONF_BOOST_OFFSET, current_config.get(CONF_BOOST_OFFSET, DEFAULT_BOOST_OFFSET))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=-10.0,
                    max=0.0,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_GRADUAL_ADJUSTMENT_RATE,
                default=current_options.get(CONF_GRADUAL_ADJUSTMENT_RATE, current_config.get(CONF_GRADUAL_ADJUSTMENT_RATE, DEFAULT_GRADUAL_ADJUSTMENT_RATE))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.1,
                    max=2.0,
                    step=0.1,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_FEEDBACK_DELAY,
                default=current_options.get(CONF_FEEDBACK_DELAY, current_config.get(CONF_FEEDBACK_DELAY, DEFAULT_FEEDBACK_DELAY))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=10,
                    max=300,
                    step=5,
                    unit_of_measurement="seconds",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_ENABLE_LEARNING,
                default=current_options.get(CONF_ENABLE_LEARNING, current_config.get(CONF_ENABLE_LEARNING, DEFAULT_ENABLE_LEARNING))
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_DEFAULT_TARGET_TEMPERATURE,
                default=current_options.get(CONF_DEFAULT_TARGET_TEMPERATURE, current_config.get(CONF_DEFAULT_TARGET_TEMPERATURE, DEFAULT_TARGET_TEMPERATURE))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=16.0,
                    max=30.0,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_ENABLE_RETRY,
                default=current_options.get(CONF_ENABLE_RETRY, current_config.get(CONF_ENABLE_RETRY, DEFAULT_ENABLE_RETRY))
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_MAX_RETRY_ATTEMPTS,
                default=current_options.get(CONF_MAX_RETRY_ATTEMPTS, current_config.get(CONF_MAX_RETRY_ATTEMPTS, DEFAULT_MAX_RETRY_ATTEMPTS))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=10,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_INITIAL_TIMEOUT,
                default=current_options.get(CONF_INITIAL_TIMEOUT, current_config.get(CONF_INITIAL_TIMEOUT, DEFAULT_INITIAL_TIMEOUT))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=30,
                    max=300,
                    step=30,
                    unit_of_measurement="seconds",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        })
        
        # Add power threshold fields if power sensor is configured
        if current_config.get(CONF_POWER_SENSOR):
            data_schema = self._add_power_threshold_fields_options(data_schema, current_config, current_options)

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
        )