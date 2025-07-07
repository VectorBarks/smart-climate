"""ABOUTME: Configuration schema for Smart Climate Control integration.
Defines validation rules and defaults for component configuration."""

try:
    import voluptuous as vol
    from homeassistant.const import CONF_ENTITY_ID
    from homeassistant.helpers import config_validation as cv
    HA_AVAILABLE = True
except ImportError:
    # For testing without Home Assistant
    HA_AVAILABLE = False
    vol = None
    cv = None

from .const import (
    CONF_CLIMATE_ENTITY,
    CONF_ROOM_SENSOR,
    CONF_OUTDOOR_SENSOR,
    CONF_POWER_SENSOR,
    CONF_MAX_OFFSET,
    CONF_MIN_TEMPERATURE,
    CONF_MAX_TEMPERATURE,
    CONF_UPDATE_INTERVAL,
    CONF_ML_ENABLED,
    DEFAULT_MAX_OFFSET,
    DEFAULT_MIN_TEMPERATURE,
    DEFAULT_MAX_TEMPERATURE,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_ML_ENABLED,
)


def validate_temperature_limits(config):
    """Validate that min_temperature < max_temperature."""
    min_temp = config.get(CONF_MIN_TEMPERATURE, DEFAULT_MIN_TEMPERATURE)
    max_temp = config.get(CONF_MAX_TEMPERATURE, DEFAULT_MAX_TEMPERATURE)
    
    if min_temp >= max_temp:
        error_msg = f"min_temperature ({min_temp}) must be less than max_temperature ({max_temp})"
        if HA_AVAILABLE and vol:
            raise vol.Invalid(error_msg)
        else:
            raise Exception(error_msg)
    
    return config


def validate_offset_limits(config):
    """Validate that max_offset is positive."""
    max_offset = config.get(CONF_MAX_OFFSET, DEFAULT_MAX_OFFSET)
    
    if max_offset <= 0:
        error_msg = f"max_offset ({max_offset}) must be greater than 0"
        if HA_AVAILABLE and vol:
            raise vol.Invalid(error_msg)
        else:
            raise Exception(error_msg)
    
    return config


if HA_AVAILABLE:
    # Configuration schema for the component
    CONFIG_SCHEMA = vol.Schema(
        {
            # Required fields
            vol.Required(CONF_CLIMATE_ENTITY): cv.entity_id,
            vol.Required(CONF_ROOM_SENSOR): cv.entity_id,
            
            # Optional fields with defaults
            vol.Optional(CONF_OUTDOOR_SENSOR): cv.entity_id,
            vol.Optional(CONF_POWER_SENSOR): cv.entity_id,
            vol.Optional(CONF_MAX_OFFSET, default=DEFAULT_MAX_OFFSET): vol.Coerce(float),
            vol.Optional(CONF_MIN_TEMPERATURE, default=DEFAULT_MIN_TEMPERATURE): vol.Coerce(float),
            vol.Optional(CONF_MAX_TEMPERATURE, default=DEFAULT_MAX_TEMPERATURE): vol.Coerce(float),
            vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.Coerce(int),
            vol.Optional(CONF_ML_ENABLED, default=DEFAULT_ML_ENABLED): cv.boolean,
        },
        extra=vol.ALLOW_EXTRA,
    )

    # Apply validation functions
    CONFIG_SCHEMA = vol.All(
        CONFIG_SCHEMA,
        validate_temperature_limits,
        validate_offset_limits,
    )

    # PLATFORM_SCHEMA for YAML configuration
    # This is used by Home Assistant to validate configuration.yaml entries
    try:
        from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
        PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
            {
                # Required fields
                vol.Required(CONF_CLIMATE_ENTITY): cv.entity_id,
                vol.Required(CONF_ROOM_SENSOR): cv.entity_id,
                
                # Optional fields with defaults
                vol.Optional(CONF_OUTDOOR_SENSOR): cv.entity_id,
                vol.Optional(CONF_POWER_SENSOR): cv.entity_id,
                vol.Optional(CONF_MAX_OFFSET, default=DEFAULT_MAX_OFFSET): vol.Coerce(float),
                vol.Optional(CONF_MIN_TEMPERATURE, default=DEFAULT_MIN_TEMPERATURE): vol.Coerce(float),
                vol.Optional(CONF_MAX_TEMPERATURE, default=DEFAULT_MAX_TEMPERATURE): vol.Coerce(float),
                vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.Coerce(int),
                vol.Optional(CONF_ML_ENABLED, default=DEFAULT_ML_ENABLED): cv.boolean,
            }
        )
        
        # Apply validation functions to PLATFORM_SCHEMA
        PLATFORM_SCHEMA = vol.All(
            PLATFORM_SCHEMA,
            validate_temperature_limits,
            validate_offset_limits,
        )
    except ImportError:
        # If PLATFORM_SCHEMA is not available, use CONFIG_SCHEMA
        PLATFORM_SCHEMA = CONFIG_SCHEMA
else:
    # Simple mock schema for testing
    class MockConfigSchema:
        def __call__(self, config):
            # Apply defaults
            result = dict(config)
            result.setdefault(CONF_MAX_OFFSET, DEFAULT_MAX_OFFSET)
            result.setdefault(CONF_MIN_TEMPERATURE, DEFAULT_MIN_TEMPERATURE)
            result.setdefault(CONF_MAX_TEMPERATURE, DEFAULT_MAX_TEMPERATURE)
            result.setdefault(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
            result.setdefault(CONF_ML_ENABLED, DEFAULT_ML_ENABLED)
            
            # Apply validation
            result = validate_temperature_limits(result)
            result = validate_offset_limits(result)
            
            return result
    
    CONFIG_SCHEMA = MockConfigSchema()