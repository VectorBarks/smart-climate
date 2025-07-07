"""ABOUTME: Integration utilities for Smart Climate Control system.
Provides helper functions for component integration and system coordination."""

import logging
from typing import Dict, Any, Optional
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.device_registry import async_get as async_get_device_registry

from .const import DOMAIN
from .errors import ConfigurationError, WrappedEntityError

_LOGGER = logging.getLogger(__name__)


async def validate_entity_exists(hass: HomeAssistant, entity_id: str) -> bool:
    """Validate that an entity exists in Home Assistant.
    
    Args:
        hass: Home Assistant instance
        entity_id: Entity ID to validate
        
    Returns:
        bool: True if entity exists, False otherwise
    """
    entity_registry = async_get_entity_registry(hass)
    entity = entity_registry.async_get(entity_id)
    
    if entity is None:
        # Check if entity exists in states even if not in registry
        state = hass.states.get(entity_id)
        if state is None:
            _LOGGER.warning("Entity %s does not exist", entity_id)
            return False
    
    _LOGGER.debug("Entity %s validated successfully", entity_id)
    return True


async def validate_climate_entity(hass: HomeAssistant, entity_id: str) -> bool:
    """Validate that an entity is a climate entity.
    
    Args:
        hass: Home Assistant instance
        entity_id: Climate entity ID to validate
        
    Returns:
        bool: True if valid climate entity, False otherwise
        
    Raises:
        WrappedEntityError: If entity is not a climate entity
    """
    if not entity_id.startswith("climate."):
        raise WrappedEntityError(f"Entity {entity_id} is not a climate entity")
    
    state = hass.states.get(entity_id)
    if state is None:
        raise WrappedEntityError(f"Climate entity {entity_id} does not exist")
    
    # Check if entity has required climate attributes
    required_attrs = ["temperature", "hvac_modes"]
    missing_attrs = [attr for attr in required_attrs if attr not in state.attributes]
    
    if missing_attrs:
        raise WrappedEntityError(
            f"Climate entity {entity_id} missing required attributes: {missing_attrs}"
        )
    
    _LOGGER.debug("Climate entity %s validated successfully", entity_id)
    return True


async def validate_sensor_entity(hass: HomeAssistant, entity_id: str, required: bool = True) -> bool:
    """Validate that an entity is a sensor entity.
    
    Args:
        hass: Home Assistant instance
        entity_id: Sensor entity ID to validate
        required: Whether this sensor is required
        
    Returns:
        bool: True if valid sensor entity or not required, False otherwise
        
    Raises:
        ConfigurationError: If required sensor is invalid
    """
    if not entity_id:
        if required:
            raise ConfigurationError("Required sensor entity not specified")
        return True
    
    if not entity_id.startswith("sensor."):
        if required:
            raise ConfigurationError(f"Entity {entity_id} is not a sensor entity")
        _LOGGER.warning("Entity %s is not a sensor entity", entity_id)
        return False
    
    state = hass.states.get(entity_id)
    if state is None:
        if required:
            raise ConfigurationError(f"Sensor entity {entity_id} does not exist")
        _LOGGER.warning("Sensor entity %s does not exist", entity_id)
        return False
    
    # Check if sensor has a numeric value
    try:
        float(state.state)
    except (ValueError, TypeError):
        if state.state not in ["unknown", "unavailable"]:
            message = f"Sensor {entity_id} does not have a numeric value: {state.state}"
            if required:
                raise ConfigurationError(message)
            _LOGGER.warning(message)
            return False
    
    _LOGGER.debug("Sensor entity %s validated successfully", entity_id)
    return True


async def validate_configuration(hass: HomeAssistant, config: Dict[str, Any]) -> bool:
    """Validate the complete Smart Climate configuration.
    
    Args:
        hass: Home Assistant instance
        config: Configuration dictionary
        
    Returns:
        bool: True if configuration is valid
        
    Raises:
        ConfigurationError: If configuration is invalid
    """
    _LOGGER.debug("Validating Smart Climate configuration")
    
    # Validate required fields
    required_fields = ["climate_entity", "room_sensor"]
    missing_fields = [field for field in required_fields if field not in config]
    
    if missing_fields:
        raise ConfigurationError(f"Missing required configuration fields: {missing_fields}")
    
    # Validate climate entity
    await validate_climate_entity(hass, config["climate_entity"])
    
    # Validate room sensor (required)
    await validate_sensor_entity(hass, config["room_sensor"], required=True)
    
    # Validate optional sensors
    if "outdoor_sensor" in config and config["outdoor_sensor"]:
        await validate_sensor_entity(hass, config["outdoor_sensor"], required=False)
    
    if "power_sensor" in config and config["power_sensor"]:
        await validate_sensor_entity(hass, config["power_sensor"], required=False)
    
    # Validate numeric parameters
    numeric_params = {
        "max_offset": (0.1, 10.0, 5.0),  # (min, max, default)
        "min_temperature": (10.0, 25.0, 16.0),
        "max_temperature": (20.0, 40.0, 30.0),
        "update_interval": (30, 3600, 180)
    }
    
    for param, (min_val, max_val, default_val) in numeric_params.items():
        value = config.get(param, default_val)
        try:
            value = float(value)
            if not min_val <= value <= max_val:
                raise ConfigurationError(
                    f"Parameter {param} must be between {min_val} and {max_val}, got {value}"
                )
        except (ValueError, TypeError):
            raise ConfigurationError(f"Parameter {param} must be a number, got {value}")
    
    # Validate temperature range consistency
    min_temp = config.get("min_temperature", 16.0)
    max_temp = config.get("max_temperature", 30.0)
    if min_temp >= max_temp:
        raise ConfigurationError(
            f"min_temperature ({min_temp}) must be less than max_temperature ({max_temp})"
        )
    
    _LOGGER.info("Smart Climate configuration validated successfully")
    return True


def get_unique_id(config: Dict[str, Any]) -> str:
    """Generate a unique ID for the Smart Climate entity.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        str: Unique ID for the entity
    """
    climate_entity = config["climate_entity"]
    room_sensor = config["room_sensor"]
    
    # Create unique ID based on wrapped entity and room sensor
    # Remove domain prefixes for cleaner ID
    climate_name = climate_entity.replace("climate.", "")
    sensor_name = room_sensor.replace("sensor.", "")
    
    unique_id = f"smart_climate_{climate_name}_{sensor_name}"
    
    _LOGGER.debug("Generated unique ID: %s", unique_id)
    return unique_id


def get_entity_name(config: Dict[str, Any]) -> str:
    """Generate a friendly name for the Smart Climate entity.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        str: Friendly name for the entity
    """
    climate_entity = config["climate_entity"]
    
    # Try to get the friendly name from the wrapped entity
    # For now, create a simple name based on the entity ID
    climate_name = climate_entity.replace("climate.", "").replace("_", " ").title()
    
    entity_name = f"Smart {climate_name}"
    
    _LOGGER.debug("Generated entity name: %s", entity_name)
    return entity_name


async def check_system_health(hass: HomeAssistant, config: Dict[str, Any]) -> Dict[str, Any]:
    """Check the health of the Smart Climate system.
    
    Args:
        hass: Home Assistant instance
        config: Configuration dictionary
        
    Returns:
        Dict[str, Any]: Health status information
    """
    health_status = {
        "overall": "healthy",
        "entities": {},
        "issues": []
    }
    
    try:
        # Check climate entity
        climate_state = hass.states.get(config["climate_entity"])
        if climate_state is None:
            health_status["entities"]["climate"] = "unavailable"
            health_status["issues"].append(f"Climate entity {config['climate_entity']} not found")
            health_status["overall"] = "degraded"
        else:
            health_status["entities"]["climate"] = climate_state.state
        
        # Check room sensor
        room_state = hass.states.get(config["room_sensor"])
        if room_state is None:
            health_status["entities"]["room_sensor"] = "unavailable"
            health_status["issues"].append(f"Room sensor {config['room_sensor']} not found")
            health_status["overall"] = "degraded"
        else:
            health_status["entities"]["room_sensor"] = room_state.state
        
        # Check optional sensors
        if "outdoor_sensor" in config and config["outdoor_sensor"]:
            outdoor_state = hass.states.get(config["outdoor_sensor"])
            health_status["entities"]["outdoor_sensor"] = (
                outdoor_state.state if outdoor_state else "unavailable"
            )
        
        if "power_sensor" in config and config["power_sensor"]:
            power_state = hass.states.get(config["power_sensor"])
            health_status["entities"]["power_sensor"] = (
                power_state.state if power_state else "unavailable"
            )
        
        # Determine overall health
        if len(health_status["issues"]) == 0:
            health_status["overall"] = "healthy"
        elif len(health_status["issues"]) <= 2:
            health_status["overall"] = "degraded"
        else:
            health_status["overall"] = "unhealthy"
        
    except Exception as exc:
        _LOGGER.error("Error checking system health: %s", exc)
        health_status["overall"] = "error"
        health_status["issues"].append(f"Health check failed: {exc}")
    
    return health_status