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
    CONF_INDOOR_HUMIDITY_SENSOR,
    CONF_OUTDOOR_HUMIDITY_SENSOR,
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
    CONF_SAVE_INTERVAL,
    CONF_ADAPTIVE_DELAY,
    CONF_DELAY_LEARNING_TIMEOUT,
    CONF_FORECAST_ENABLED,
    CONF_WEATHER_ENTITY,
    CONF_HEAT_WAVE_TEMP_THRESHOLD,
    CONF_HEAT_WAVE_MIN_DURATION_HOURS,
    CONF_HEAT_WAVE_LOOKAHEAD_HOURS,
    CONF_HEAT_WAVE_PRE_ACTION_HOURS,
    CONF_HEAT_WAVE_ADJUSTMENT,
    CONF_CLEAR_SKY_CONDITION,
    CONF_CLEAR_SKY_MIN_DURATION_HOURS,
    CONF_CLEAR_SKY_LOOKAHEAD_HOURS,
    CONF_CLEAR_SKY_PRE_ACTION_HOURS,
    CONF_CLEAR_SKY_ADJUSTMENT,
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
    DEFAULT_SAVE_INTERVAL,
    DEFAULT_ADAPTIVE_DELAY,
    DEFAULT_DELAY_LEARNING_TIMEOUT,
    MIN_DELAY_LEARNING_TIMEOUT,
    MAX_DELAY_LEARNING_TIMEOUT,
    DEFAULT_FORECAST_ENABLED,
    DEFAULT_HEAT_WAVE_TEMP_THRESHOLD,
    DEFAULT_HEAT_WAVE_MIN_DURATION_HOURS,
    DEFAULT_HEAT_WAVE_LOOKAHEAD_HOURS,
    DEFAULT_HEAT_WAVE_PRE_ACTION_HOURS,
    DEFAULT_HEAT_WAVE_ADJUSTMENT,
    DEFAULT_CLEAR_SKY_CONDITION,
    DEFAULT_CLEAR_SKY_MIN_DURATION_HOURS,
    DEFAULT_CLEAR_SKY_LOOKAHEAD_HOURS,
    DEFAULT_CLEAR_SKY_PRE_ACTION_HOURS,
    DEFAULT_CLEAR_SKY_ADJUSTMENT,
    CONF_OUTLIER_DETECTION_ENABLED,
    CONF_OUTLIER_SENSITIVITY,
    DEFAULT_OUTLIER_DETECTION_ENABLED,
    DEFAULT_OUTLIER_SENSITIVITY,
    # Thermal efficiency imports
    CONF_THERMAL_EFFICIENCY_ENABLED,
    CONF_PREFERENCE_LEVEL,
    CONF_SHADOW_MODE,
    CONF_PRIMING_DURATION_HOURS,
    CONF_RECOVERY_DURATION_MINUTES,
    CONF_PROBE_DRIFT_LIMIT,
    CONF_CALIBRATION_IDLE_MINUTES,
    CONF_CALIBRATION_DRIFT_THRESHOLD,
    # Passive learning imports
    CONF_PASSIVE_LEARNING_ENABLED,
    CONF_PASSIVE_MIN_DRIFT_MINUTES,
    CONF_PASSIVE_CONFIDENCE_THRESHOLD,
    DEFAULT_THERMAL_EFFICIENCY_ENABLED,
    DEFAULT_PREFERENCE_LEVEL,
    DEFAULT_SHADOW_MODE,
    DEFAULT_PRIMING_DURATION_HOURS,
    DEFAULT_RECOVERY_DURATION_MINUTES,
    DEFAULT_PROBE_DRIFT_LIMIT,
    DEFAULT_CALIBRATION_IDLE_MINUTES,
    DEFAULT_CALIBRATION_DRIFT_THRESHOLD,
    # Passive learning defaults
    DEFAULT_PASSIVE_LEARNING_ENABLED,
    DEFAULT_PASSIVE_MIN_DRIFT_MINUTES,
    DEFAULT_PASSIVE_CONFIDENCE_THRESHOLD,
    PREFERENCE_LEVELS,
    # Humidity monitoring imports
    CONF_HUMIDITY_CHANGE_THRESHOLD,
    CONF_HEAT_INDEX_WARNING,
    CONF_HEAT_INDEX_HIGH,
    CONF_DEW_POINT_WARNING,
    CONF_DEW_POINT_CRITICAL,
    CONF_DIFFERENTIAL_SIGNIFICANT,
    CONF_DIFFERENTIAL_EXTREME,
    CONF_HUMIDITY_LOG_LEVEL,
    DEFAULT_HUMIDITY_CHANGE_THRESHOLD,
    DEFAULT_HEAT_INDEX_WARNING,
    DEFAULT_HEAT_INDEX_HIGH,
    DEFAULT_DEW_POINT_WARNING,
    DEFAULT_DEW_POINT_CRITICAL,
    DEFAULT_DIFFERENTIAL_SIGNIFICANT,
    DEFAULT_DIFFERENTIAL_EXTREME,
    DEFAULT_HUMIDITY_LOG_LEVEL,
    # Probe Scheduler imports (v1.5.3-beta)
    CONF_LEARNING_PROFILE,
    CONF_PRESENCE_ENTITY_ID,
    CONF_WEATHER_ENTITY_ID,
    CONF_CALENDAR_ENTITY_ID,
    CONF_MANUAL_OVERRIDE_ENTITY_ID,
    CONF_MIN_PROBE_INTERVAL,
    CONF_MAX_PROBE_INTERVAL,
    CONF_QUIET_HOURS_START,
    CONF_QUIET_HOURS_END,
    CONF_INFO_GAIN_THRESHOLD,
    DEFAULT_LEARNING_PROFILE,
    DEFAULT_MIN_PROBE_INTERVAL,
    DEFAULT_MAX_PROBE_INTERVAL,
    DEFAULT_QUIET_HOURS_START,
    DEFAULT_QUIET_HOURS_END,
    DEFAULT_INFO_GAIN_THRESHOLD,
    # Entity availability waiting imports
    CONF_STARTUP_TIMEOUT,
    STARTUP_TIMEOUT_SEC,
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
                elif "weather_entity" in str(ex):
                    errors[CONF_WEATHER_ENTITY] = "entity_not_found"
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
        humidity_sensors = await self._get_humidity_sensors()
        weather_entities = await self._get_weather_entities()

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
            vol.Optional(CONF_INDOOR_HUMIDITY_SENSOR): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=entity_id, label=f"{entity_id} ({friendly_name})")
                        for entity_id, friendly_name in humidity_sensors.items()
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_OUTDOOR_HUMIDITY_SENSOR): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=entity_id, label=f"{entity_id} ({friendly_name})")
                        for entity_id, friendly_name in humidity_sensors.items()
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
            vol.Optional(CONF_SAVE_INTERVAL, default=DEFAULT_SAVE_INTERVAL): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=300,
                    max=86400,
                    step=300,
                    unit_of_measurement="seconds",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_ADAPTIVE_DELAY, default=DEFAULT_ADAPTIVE_DELAY): selector.BooleanSelector(),
            vol.Optional(CONF_DELAY_LEARNING_TIMEOUT, default=DEFAULT_DELAY_LEARNING_TIMEOUT): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_DELAY_LEARNING_TIMEOUT,
                    max=MAX_DELAY_LEARNING_TIMEOUT,
                    step=5,
                    unit_of_measurement="minutes",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            
            # Weather forecast configuration
            vol.Optional(CONF_FORECAST_ENABLED, default=DEFAULT_FORECAST_ENABLED): selector.BooleanSelector(),
            vol.Optional(CONF_WEATHER_ENTITY): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=entity_id, label=f"{entity_id} ({friendly_name})")
                        for entity_id, friendly_name in weather_entities.items()
                    ] if weather_entities else [],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            
            # Heat wave strategy configuration
            vol.Optional(CONF_HEAT_WAVE_TEMP_THRESHOLD, default=DEFAULT_HEAT_WAVE_TEMP_THRESHOLD): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=20.0,
                    max=40.0,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_HEAT_WAVE_MIN_DURATION_HOURS, default=DEFAULT_HEAT_WAVE_MIN_DURATION_HOURS): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=24,
                    step=1,
                    unit_of_measurement="hours",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_HEAT_WAVE_LOOKAHEAD_HOURS, default=DEFAULT_HEAT_WAVE_LOOKAHEAD_HOURS): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=72,
                    step=1,
                    unit_of_measurement="hours",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_HEAT_WAVE_PRE_ACTION_HOURS, default=DEFAULT_HEAT_WAVE_PRE_ACTION_HOURS): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=12,
                    step=1,
                    unit_of_measurement="hours",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_HEAT_WAVE_ADJUSTMENT, default=DEFAULT_HEAT_WAVE_ADJUSTMENT): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=-5.0,
                    max=0.0,
                    step=0.1,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            
            # Clear sky strategy configuration
            vol.Optional(CONF_CLEAR_SKY_CONDITION, default=DEFAULT_CLEAR_SKY_CONDITION): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value="sunny", label="Sunny"),
                        selector.SelectOptionDict(value="clear", label="Clear"),
                        selector.SelectOptionDict(value="clear-night", label="Clear Night"),
                        selector.SelectOptionDict(value="partly-cloudy", label="Partly Cloudy"),
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_CLEAR_SKY_MIN_DURATION_HOURS, default=DEFAULT_CLEAR_SKY_MIN_DURATION_HOURS): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=24,
                    step=1,
                    unit_of_measurement="hours",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_CLEAR_SKY_LOOKAHEAD_HOURS, default=DEFAULT_CLEAR_SKY_LOOKAHEAD_HOURS): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=48,
                    step=1,
                    unit_of_measurement="hours",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_CLEAR_SKY_PRE_ACTION_HOURS, default=DEFAULT_CLEAR_SKY_PRE_ACTION_HOURS): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=6,
                    step=1,
                    unit_of_measurement="hours",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_CLEAR_SKY_ADJUSTMENT, default=DEFAULT_CLEAR_SKY_ADJUSTMENT): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=-3.0,
                    max=0.0,
                    step=0.1,
                    unit_of_measurement="°C",
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
        
        # Validate optional indoor humidity sensor
        indoor_humidity_sensor = user_input.get(CONF_INDOOR_HUMIDITY_SENSOR)
        if indoor_humidity_sensor:
            if not await self._entity_exists(indoor_humidity_sensor, "sensor"):
                raise vol.Invalid("indoor_humidity_sensor not found")
            validated[CONF_INDOOR_HUMIDITY_SENSOR] = indoor_humidity_sensor
        
        # Validate optional outdoor humidity sensor
        outdoor_humidity_sensor = user_input.get(CONF_OUTDOOR_HUMIDITY_SENSOR)
        if outdoor_humidity_sensor:
            if not await self._entity_exists(outdoor_humidity_sensor, "sensor"):
                raise vol.Invalid("outdoor_humidity_sensor not found")
            validated[CONF_OUTDOOR_HUMIDITY_SENSOR] = outdoor_humidity_sensor
        
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
        validated[CONF_SAVE_INTERVAL] = user_input.get(CONF_SAVE_INTERVAL, DEFAULT_SAVE_INTERVAL)
        validated[CONF_ADAPTIVE_DELAY] = user_input.get(CONF_ADAPTIVE_DELAY, DEFAULT_ADAPTIVE_DELAY)
        
        # Validate weather forecast configuration
        forecast_enabled = user_input.get(CONF_FORECAST_ENABLED, DEFAULT_FORECAST_ENABLED)
        validated[CONF_FORECAST_ENABLED] = forecast_enabled
        
        if forecast_enabled:
            # Weather entity is required when forecast is enabled
            weather_entity = user_input.get(CONF_WEATHER_ENTITY)
            if weather_entity:
                if not await self._entity_exists(weather_entity, "weather"):
                    raise vol.Invalid("weather_entity not found")
                validated[CONF_WEATHER_ENTITY] = weather_entity
            else:
                raise vol.Invalid("weather_entity required when forecast is enabled")
        elif user_input.get(CONF_WEATHER_ENTITY):
            # Weather entity provided even when forecast disabled - still validate if present
            weather_entity = user_input.get(CONF_WEATHER_ENTITY)
            if not await self._entity_exists(weather_entity, "weather"):
                raise vol.Invalid("weather_entity not found")
            validated[CONF_WEATHER_ENTITY] = weather_entity
        
        # Copy forecast strategy parameters (these are always saved for future use)
        validated[CONF_HEAT_WAVE_TEMP_THRESHOLD] = user_input.get(CONF_HEAT_WAVE_TEMP_THRESHOLD, DEFAULT_HEAT_WAVE_TEMP_THRESHOLD)
        validated[CONF_HEAT_WAVE_MIN_DURATION_HOURS] = user_input.get(CONF_HEAT_WAVE_MIN_DURATION_HOURS, DEFAULT_HEAT_WAVE_MIN_DURATION_HOURS)
        validated[CONF_HEAT_WAVE_LOOKAHEAD_HOURS] = user_input.get(CONF_HEAT_WAVE_LOOKAHEAD_HOURS, DEFAULT_HEAT_WAVE_LOOKAHEAD_HOURS)
        validated[CONF_HEAT_WAVE_PRE_ACTION_HOURS] = user_input.get(CONF_HEAT_WAVE_PRE_ACTION_HOURS, DEFAULT_HEAT_WAVE_PRE_ACTION_HOURS)
        validated[CONF_HEAT_WAVE_ADJUSTMENT] = user_input.get(CONF_HEAT_WAVE_ADJUSTMENT, DEFAULT_HEAT_WAVE_ADJUSTMENT)
        
        validated[CONF_CLEAR_SKY_CONDITION] = user_input.get(CONF_CLEAR_SKY_CONDITION, DEFAULT_CLEAR_SKY_CONDITION)
        validated[CONF_CLEAR_SKY_MIN_DURATION_HOURS] = user_input.get(CONF_CLEAR_SKY_MIN_DURATION_HOURS, DEFAULT_CLEAR_SKY_MIN_DURATION_HOURS)
        validated[CONF_CLEAR_SKY_LOOKAHEAD_HOURS] = user_input.get(CONF_CLEAR_SKY_LOOKAHEAD_HOURS, DEFAULT_CLEAR_SKY_LOOKAHEAD_HOURS)
        validated[CONF_CLEAR_SKY_PRE_ACTION_HOURS] = user_input.get(CONF_CLEAR_SKY_PRE_ACTION_HOURS, DEFAULT_CLEAR_SKY_PRE_ACTION_HOURS)
        validated[CONF_CLEAR_SKY_ADJUSTMENT] = user_input.get(CONF_CLEAR_SKY_ADJUSTMENT, DEFAULT_CLEAR_SKY_ADJUSTMENT)
        
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

    async def _get_humidity_sensors(self) -> Dict[str, str]:
        """Get all humidity sensors."""
        entities = {}
        
        for state in self.hass.states.async_all():
            if (
                state.entity_id.startswith("sensor.") and
                state.attributes.get("device_class") == "humidity"
            ):
                friendly_name = state.attributes.get("friendly_name", state.entity_id)
                entities[state.entity_id] = friendly_name
        
        return entities

    async def _get_weather_entities(self) -> Dict[str, str]:
        """Get all weather entities."""
        entities = {}
        
        for state in self.hass.states.async_all():
            if state.entity_id.startswith("weather."):
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
    
    def __init__(self, config_entry: config_entries.ConfigEntry = None) -> None:
        """Initialize options flow."""
        self._basic_settings: Optional[Dict[str, Any]] = None
    
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
    
    async def _get_humidity_sensors(self) -> Dict[str, str]:
        """Get all humidity sensors."""
        entities = {}
        
        for state in self.hass.states.async_all():
            if (
                state.entity_id.startswith("sensor.") and
                state.attributes.get("device_class") == "humidity"
            ):
                friendly_name = state.attributes.get("friendly_name", state.entity_id)
                entities[state.entity_id] = friendly_name
        
        return entities

    def _get_options_schema(self) -> vol.Schema:
        """Return options schema with properly optional entities."""
        current_options = self.config_entry.options
        
        return vol.Schema({
            # ProbeScheduler Configuration
            vol.Optional(
                "probe_scheduler_enabled",
                default=current_options.get("probe_scheduler_enabled", True)
            ): bool,
            vol.Optional(
                CONF_LEARNING_PROFILE, 
                default=current_options.get(CONF_LEARNING_PROFILE, DEFAULT_LEARNING_PROFILE)
            ): vol.In(["comfort", "balanced", "aggressive", "custom"]),
            vol.Optional(
                CONF_PRESENCE_ENTITY_ID,
                default=current_options.get(CONF_PRESENCE_ENTITY_ID, "")  # Empty string default
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["binary_sensor", "person", "device_tracker"],
                    multiple=False
                )
            ),
            vol.Optional(
                CONF_WEATHER_ENTITY_ID,
                default=current_options.get(CONF_WEATHER_ENTITY_ID, "weather.home")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="weather",
                    multiple=False
                )
            ),
            vol.Optional(
                CONF_CALENDAR_ENTITY_ID,
                default=current_options.get(CONF_CALENDAR_ENTITY_ID, "")  # Empty string default
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="calendar",
                    multiple=False
                )
            ),
            vol.Optional(
                CONF_MANUAL_OVERRIDE_ENTITY_ID,
                default=current_options.get(CONF_MANUAL_OVERRIDE_ENTITY_ID, "")  # Empty string default
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="input_boolean",
                    multiple=False
                )
            ),
        })

    def _clean_entity_ids(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """Clean empty string entity IDs to None for optional entities."""
        cleaned = user_input.copy()
        optional_entities = [
            CONF_PRESENCE_ENTITY_ID,
            CONF_CALENDAR_ENTITY_ID, 
            CONF_MANUAL_OVERRIDE_ENTITY_ID
        ]
        
        for entity_key in optional_entities:
            if entity_key in cleaned and cleaned[entity_key] == "":
                cleaned[entity_key] = None
                
        return cleaned

    def _get_advanced_schema(self) -> vol.Schema:
        """Return advanced settings schema for custom profile."""
        current_options = self.config_entry.options
        
        return vol.Schema({
            vol.Optional(
                CONF_MIN_PROBE_INTERVAL,
                default=current_options.get(CONF_MIN_PROBE_INTERVAL, DEFAULT_MIN_PROBE_INTERVAL)
            ): vol.All(vol.Coerce(int), vol.Range(min=6, max=24)),
            vol.Optional(
                CONF_MAX_PROBE_INTERVAL, 
                default=current_options.get(CONF_MAX_PROBE_INTERVAL, DEFAULT_MAX_PROBE_INTERVAL)
            ): vol.All(vol.Coerce(int), vol.Range(min=3, max=14)),
            vol.Optional(
                CONF_QUIET_HOURS_START,
                default=current_options.get(CONF_QUIET_HOURS_START, DEFAULT_QUIET_HOURS_START)
            ): str,
            vol.Optional(
                CONF_QUIET_HOURS_END,
                default=current_options.get(CONF_QUIET_HOURS_END, DEFAULT_QUIET_HOURS_END)  
            ): str,
            vol.Optional(
                CONF_INFO_GAIN_THRESHOLD,
                default=current_options.get(CONF_INFO_GAIN_THRESHOLD, DEFAULT_INFO_GAIN_THRESHOLD)
            ): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=0.9)),
        })

    def _get_description_placeholders(self) -> Dict[str, str]:
        """Get description placeholders for UI."""
        return {
            "probe_scheduler_info": (
                "Enable intelligent context-aware probe scheduling. "
                "Reduces 30-day learning period to days with zero comfort impact."
            ),
            "learning_profiles": (
                "Comfort: 24h intervals, minimal disruption\n"
                "Balanced: 12h intervals, standard learning\n" 
                "Aggressive: 6h intervals, fastest learning\n"
                "Custom: Configure all parameters manually"
            ),
            "presence_sensor_info": (
                "Optional: Presence sensor for away detection. "
                "Without this, system uses conservative quiet hours only."
            ),
            "fallback_behavior": (
                "System works without presence sensor using quiet hours + maximum interval forcing. "
                "Probes only when absolutely necessary (every 7 days max)."
            )
        }

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle options flow."""
        if user_input is not None:
            # Clean up empty string entity IDs to None
            cleaned_input = self._clean_entity_ids(user_input)
            
            if cleaned_input.get(CONF_LEARNING_PROFILE) == "custom":
                # Store basic settings and move to advanced
                self._basic_settings = cleaned_input
                return await self.async_step_advanced()
            else:
                # Direct save for non-custom profiles
                return self.async_create_entry(title="", data=cleaned_input)
        
        current_config = self.config_entry.data
        current_options = self.config_entry.options
        
        # Get available humidity sensors for selectors
        humidity_sensors = await self._get_humidity_sensors()
        
        # Create the combined schema with existing options + ProbeScheduler options
        probe_scheduler_schema = self._get_options_schema()
        
        # Build existing configuration schema
        existing_schema = vol.Schema({
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
            
            # Humidity sensor configuration
            vol.Optional(
                CONF_INDOOR_HUMIDITY_SENSOR,
                default=current_options.get(CONF_INDOOR_HUMIDITY_SENSOR, current_config.get(CONF_INDOOR_HUMIDITY_SENSOR))
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=entity_id, label=f"{entity_id} ({friendly_name})")
                        for entity_id, friendly_name in humidity_sensors.items()
                    ] if humidity_sensors else [],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_OUTDOOR_HUMIDITY_SENSOR,
                default=current_options.get(CONF_OUTDOOR_HUMIDITY_SENSOR, current_config.get(CONF_OUTDOOR_HUMIDITY_SENSOR))
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=entity_id, label=f"{entity_id} ({friendly_name})")
                        for entity_id, friendly_name in humidity_sensors.items()
                    ] if humidity_sensors else [],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            
            # Humidity monitoring configuration
            vol.Optional(
                CONF_HUMIDITY_CHANGE_THRESHOLD,
                default=current_options.get(CONF_HUMIDITY_CHANGE_THRESHOLD, current_config.get(CONF_HUMIDITY_CHANGE_THRESHOLD, DEFAULT_HUMIDITY_CHANGE_THRESHOLD))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.5,
                    max=10.0,
                    step=0.1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_HEAT_INDEX_WARNING,
                default=current_options.get(CONF_HEAT_INDEX_WARNING, current_config.get(CONF_HEAT_INDEX_WARNING, DEFAULT_HEAT_INDEX_WARNING))
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
                CONF_HEAT_INDEX_HIGH,
                default=current_options.get(CONF_HEAT_INDEX_HIGH, current_config.get(CONF_HEAT_INDEX_HIGH, DEFAULT_HEAT_INDEX_HIGH))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=25.0,
                    max=40.0,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_DEW_POINT_WARNING,
                default=current_options.get(CONF_DEW_POINT_WARNING, current_config.get(CONF_DEW_POINT_WARNING, DEFAULT_DEW_POINT_WARNING))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.5,
                    max=5.0,
                    step=0.1,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_DEW_POINT_CRITICAL,
                default=current_options.get(CONF_DEW_POINT_CRITICAL, current_config.get(CONF_DEW_POINT_CRITICAL, DEFAULT_DEW_POINT_CRITICAL))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.1,
                    max=3.0,
                    step=0.1,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_DIFFERENTIAL_SIGNIFICANT,
                default=current_options.get(CONF_DIFFERENTIAL_SIGNIFICANT, current_config.get(CONF_DIFFERENTIAL_SIGNIFICANT, DEFAULT_DIFFERENTIAL_SIGNIFICANT))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=10.0,
                    max=50.0,
                    step=1.0,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_DIFFERENTIAL_EXTREME,
                default=current_options.get(CONF_DIFFERENTIAL_EXTREME, current_config.get(CONF_DIFFERENTIAL_EXTREME, DEFAULT_DIFFERENTIAL_EXTREME))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=20.0,
                    max=80.0,
                    step=1.0,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_HUMIDITY_LOG_LEVEL,
                default=current_options.get(CONF_HUMIDITY_LOG_LEVEL, current_config.get(CONF_HUMIDITY_LOG_LEVEL, DEFAULT_HUMIDITY_LOG_LEVEL))
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value="INFO", label="INFO"),
                        selector.SelectOptionDict(value="DEBUG", label="DEBUG"),
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            
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
            vol.Optional(
                CONF_SAVE_INTERVAL,
                default=current_options.get(CONF_SAVE_INTERVAL, current_config.get(CONF_SAVE_INTERVAL, DEFAULT_SAVE_INTERVAL))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=300,
                    max=86400,
                    step=300,
                    unit_of_measurement="seconds",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_ADAPTIVE_DELAY,
                default=current_options.get(CONF_ADAPTIVE_DELAY, current_config.get(CONF_ADAPTIVE_DELAY, DEFAULT_ADAPTIVE_DELAY))
            ): selector.BooleanSelector(),
            
            # Entity availability waiting configuration
            vol.Optional(
                CONF_STARTUP_TIMEOUT,
                default=current_options.get(CONF_STARTUP_TIMEOUT, current_config.get(CONF_STARTUP_TIMEOUT, STARTUP_TIMEOUT_SEC))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=30,
                    max=300,
                    step=10,
                    unit_of_measurement="seconds",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            
            # Weather forecast configuration
            vol.Optional(
                CONF_FORECAST_ENABLED,
                default=current_options.get(CONF_FORECAST_ENABLED, current_config.get(CONF_FORECAST_ENABLED, DEFAULT_FORECAST_ENABLED))
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_WEATHER_ENTITY,
                default=current_options.get(CONF_WEATHER_ENTITY, current_config.get(CONF_WEATHER_ENTITY))
            ): selector.TextSelector(),
            
            # Heat wave strategy configuration
            vol.Optional(
                CONF_HEAT_WAVE_TEMP_THRESHOLD,
                default=current_options.get(CONF_HEAT_WAVE_TEMP_THRESHOLD, current_config.get(CONF_HEAT_WAVE_TEMP_THRESHOLD, DEFAULT_HEAT_WAVE_TEMP_THRESHOLD))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=20.0,
                    max=40.0,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_HEAT_WAVE_MIN_DURATION_HOURS,
                default=current_options.get(CONF_HEAT_WAVE_MIN_DURATION_HOURS, current_config.get(CONF_HEAT_WAVE_MIN_DURATION_HOURS, DEFAULT_HEAT_WAVE_MIN_DURATION_HOURS))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=24,
                    step=1,
                    unit_of_measurement="hours",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_HEAT_WAVE_LOOKAHEAD_HOURS,
                default=current_options.get(CONF_HEAT_WAVE_LOOKAHEAD_HOURS, current_config.get(CONF_HEAT_WAVE_LOOKAHEAD_HOURS, DEFAULT_HEAT_WAVE_LOOKAHEAD_HOURS))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=72,
                    step=1,
                    unit_of_measurement="hours",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_HEAT_WAVE_PRE_ACTION_HOURS,
                default=current_options.get(CONF_HEAT_WAVE_PRE_ACTION_HOURS, current_config.get(CONF_HEAT_WAVE_PRE_ACTION_HOURS, DEFAULT_HEAT_WAVE_PRE_ACTION_HOURS))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=12,
                    step=1,
                    unit_of_measurement="hours",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_HEAT_WAVE_ADJUSTMENT,
                default=current_options.get(CONF_HEAT_WAVE_ADJUSTMENT, current_config.get(CONF_HEAT_WAVE_ADJUSTMENT, DEFAULT_HEAT_WAVE_ADJUSTMENT))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=-5.0,
                    max=0.0,
                    step=0.1,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            
            # Clear sky strategy configuration
            vol.Optional(
                CONF_CLEAR_SKY_CONDITION,
                default=current_options.get(CONF_CLEAR_SKY_CONDITION, current_config.get(CONF_CLEAR_SKY_CONDITION, DEFAULT_CLEAR_SKY_CONDITION))
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value="sunny", label="Sunny"),
                        selector.SelectOptionDict(value="clear", label="Clear"),
                        selector.SelectOptionDict(value="clear-night", label="Clear Night"),
                        selector.SelectOptionDict(value="partly-cloudy", label="Partly Cloudy"),
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_CLEAR_SKY_MIN_DURATION_HOURS,
                default=current_options.get(CONF_CLEAR_SKY_MIN_DURATION_HOURS, current_config.get(CONF_CLEAR_SKY_MIN_DURATION_HOURS, DEFAULT_CLEAR_SKY_MIN_DURATION_HOURS))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=24,
                    step=1,
                    unit_of_measurement="hours",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_CLEAR_SKY_LOOKAHEAD_HOURS,
                default=current_options.get(CONF_CLEAR_SKY_LOOKAHEAD_HOURS, current_config.get(CONF_CLEAR_SKY_LOOKAHEAD_HOURS, DEFAULT_CLEAR_SKY_LOOKAHEAD_HOURS))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=48,
                    step=1,
                    unit_of_measurement="hours",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_CLEAR_SKY_PRE_ACTION_HOURS,
                default=current_options.get(CONF_CLEAR_SKY_PRE_ACTION_HOURS, current_config.get(CONF_CLEAR_SKY_PRE_ACTION_HOURS, DEFAULT_CLEAR_SKY_PRE_ACTION_HOURS))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=6,
                    step=1,
                    unit_of_measurement="hours",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_CLEAR_SKY_ADJUSTMENT,
                default=current_options.get(CONF_CLEAR_SKY_ADJUSTMENT, current_config.get(CONF_CLEAR_SKY_ADJUSTMENT, DEFAULT_CLEAR_SKY_ADJUSTMENT))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=-3.0,
                    max=0.0,
                    step=0.1,
                    unit_of_measurement="°C",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            
            # Outlier detection configuration
            vol.Optional(
                CONF_OUTLIER_DETECTION_ENABLED,
                default=current_options.get(CONF_OUTLIER_DETECTION_ENABLED, current_config.get(CONF_OUTLIER_DETECTION_ENABLED, DEFAULT_OUTLIER_DETECTION_ENABLED))
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_OUTLIER_SENSITIVITY,
                default=current_options.get(CONF_OUTLIER_SENSITIVITY, current_config.get(CONF_OUTLIER_SENSITIVITY, DEFAULT_OUTLIER_SENSITIVITY))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1.0,
                    max=5.0,
                    step=0.1,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            
            # Thermal efficiency configuration
            vol.Optional(
                CONF_THERMAL_EFFICIENCY_ENABLED,
                default=current_options.get(CONF_THERMAL_EFFICIENCY_ENABLED, current_config.get(CONF_THERMAL_EFFICIENCY_ENABLED, DEFAULT_THERMAL_EFFICIENCY_ENABLED))
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_PREFERENCE_LEVEL,
                default=current_options.get(CONF_PREFERENCE_LEVEL, current_config.get(CONF_PREFERENCE_LEVEL, DEFAULT_PREFERENCE_LEVEL))
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value="max_comfort", label="Maximum Comfort"),
                        selector.SelectOptionDict(value="comfort_priority", label="Comfort Priority"),
                        selector.SelectOptionDict(value="balanced", label="Balanced"),
                        selector.SelectOptionDict(value="savings_priority", label="Savings Priority"),
                        selector.SelectOptionDict(value="max_savings", label="Maximum Savings"),
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_SHADOW_MODE,
                default=current_options.get(CONF_SHADOW_MODE, current_config.get(CONF_SHADOW_MODE, DEFAULT_SHADOW_MODE))
            ): selector.BooleanSelector(),
        })
        
        # Combine the schemas
        combined_schema_dict = dict(existing_schema.schema)
        combined_schema_dict.update(probe_scheduler_schema.schema)
        data_schema = vol.Schema(combined_schema_dict)
        
        # Add thermal efficiency advanced options if thermal efficiency is enabled
        thermal_enabled = current_options.get(CONF_THERMAL_EFFICIENCY_ENABLED, current_config.get(CONF_THERMAL_EFFICIENCY_ENABLED, DEFAULT_THERMAL_EFFICIENCY_ENABLED))
        if thermal_enabled:
            schema_dict = dict(data_schema.schema)
            schema_dict.update({
                vol.Optional(
                    CONF_PRIMING_DURATION_HOURS,
                    default=current_options.get(CONF_PRIMING_DURATION_HOURS, current_config.get(CONF_PRIMING_DURATION_HOURS, DEFAULT_PRIMING_DURATION_HOURS))
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=24,
                        max=48,
                        step=1,
                        unit_of_measurement="hours",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_RECOVERY_DURATION_MINUTES,
                    default=current_options.get(CONF_RECOVERY_DURATION_MINUTES, current_config.get(CONF_RECOVERY_DURATION_MINUTES, DEFAULT_RECOVERY_DURATION_MINUTES))
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=30,
                        max=60,
                        step=1,
                        unit_of_measurement="minutes",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_PROBE_DRIFT_LIMIT,
                    default=current_options.get(CONF_PROBE_DRIFT_LIMIT, current_config.get(CONF_PROBE_DRIFT_LIMIT, DEFAULT_PROBE_DRIFT_LIMIT))
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1.0,
                        max=3.0,
                        step=0.1,
                        unit_of_measurement="°C",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_CALIBRATION_IDLE_MINUTES,
                    default=current_options.get(CONF_CALIBRATION_IDLE_MINUTES, current_config.get(CONF_CALIBRATION_IDLE_MINUTES, DEFAULT_CALIBRATION_IDLE_MINUTES))
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=15,
                        max=120,
                        step=1,
                        unit_of_measurement="minutes",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_CALIBRATION_DRIFT_THRESHOLD,
                    default=current_options.get(CONF_CALIBRATION_DRIFT_THRESHOLD, current_config.get(CONF_CALIBRATION_DRIFT_THRESHOLD, DEFAULT_CALIBRATION_DRIFT_THRESHOLD))
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.1,
                        max=1.0,
                        step=0.01,
                        unit_of_measurement="°C",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                
                # Passive learning configuration (v1.4.3+)
                vol.Optional(
                    CONF_PASSIVE_LEARNING_ENABLED,
                    default=current_options.get(CONF_PASSIVE_LEARNING_ENABLED, current_config.get(CONF_PASSIVE_LEARNING_ENABLED, DEFAULT_PASSIVE_LEARNING_ENABLED))
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_PASSIVE_MIN_DRIFT_MINUTES,
                    default=current_options.get(CONF_PASSIVE_MIN_DRIFT_MINUTES, current_config.get(CONF_PASSIVE_MIN_DRIFT_MINUTES, DEFAULT_PASSIVE_MIN_DRIFT_MINUTES))
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=10,
                        max=30,
                        step=1,
                        unit_of_measurement="minutes",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_PASSIVE_CONFIDENCE_THRESHOLD,
                    default=current_options.get(CONF_PASSIVE_CONFIDENCE_THRESHOLD, current_config.get(CONF_PASSIVE_CONFIDENCE_THRESHOLD, DEFAULT_PASSIVE_CONFIDENCE_THRESHOLD))
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.2,
                        max=0.5,
                        step=0.01,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            })
            data_schema = vol.Schema(schema_dict)

        # Add power threshold fields if power sensor is configured
        if current_config.get(CONF_POWER_SENSOR):
            data_schema = self._add_power_threshold_fields_options(data_schema, current_config, current_options)

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            description_placeholders=self._get_description_placeholders()
        )

    async def async_step_advanced(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle advanced settings for custom profile."""
        if user_input is not None:
            # Combine basic and advanced settings
            if self._basic_settings:
                combined_settings = {**self._basic_settings, **user_input}
            else:
                # Fallback if basic settings missing
                combined_settings = user_input
            
            # Clean up empty string entity IDs to None
            cleaned_settings = self._clean_entity_ids(combined_settings)
            return self.async_create_entry(title="", data=cleaned_settings)
            
        return self.async_show_form(
            step_id="advanced",
            data_schema=self._get_advanced_schema(),
            description_placeholders=self._get_description_placeholders()
        )