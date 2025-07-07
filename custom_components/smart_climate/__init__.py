"""Smart Climate Control integration."""

import logging
from typing import Any, Dict, List
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import Platform
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, PLATFORMS
from .entity_waiter import EntityWaiter, EntityNotAvailableError
from .offset_engine import OffsetEngine

# Version and basic metadata
__version__ = "0.1.0"
__author__ = "Smart Climate Team"

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Smart Climate Control integration."""
    _LOGGER.info("Setting up Smart Climate Control integration")
    
    # Initialize the domain in hass.data
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    
    # Store config data for legacy YAML configuration
    domain_config = config.get(DOMAIN, {})
    if domain_config:
        _LOGGER.info("Found YAML configuration for Smart Climate Control")
        hass.data[DOMAIN]["yaml_config"] = domain_config
        
        # For YAML configuration, we would set up the climate platform
        # This is handled by the platform setup in climate.py
        _LOGGER.debug("YAML configuration will be processed by climate platform setup")
    
    return True


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    """Set up Smart Climate Control from a config entry."""
    _LOGGER.info("Setting up Smart Climate Control from config entry")
    
    # Initialize the domain in hass.data if not already done
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    
    # Create a shared OffsetEngine instance for all platforms
    offset_engine = OffsetEngine(entry.data)
    
    # Store the config entry and shared components
    hass.data[DOMAIN][entry.entry_id] = {
        "config": entry.data,
        "offset_engine": offset_engine
    }
    
    # Wait for required entities to become available before proceeding
    try:
        _LOGGER.debug("Checking availability of required entities before setup")
        entity_waiter = EntityWaiter()
        await entity_waiter.wait_for_required_entities(
            hass, 
            entry.data, 
            timeout=60  # Give up to 60 seconds for entities to become available
        )
        _LOGGER.info("All required entities are available, proceeding with platform setup")
        
    except EntityNotAvailableError as exc:
        error_msg = f"Required entities not available for Smart Climate setup: {exc}"
        _LOGGER.error(error_msg)
        raise HomeAssistantError(error_msg) from exc
    
    except Exception as exc:
        error_msg = f"Unexpected error while waiting for entities: {exc}"
        _LOGGER.error(error_msg, exc_info=True)
        raise HomeAssistantError(error_msg) from exc
    
    # Set up both climate and switch platforms
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        _LOGGER.info("Smart Climate Control setup completed successfully with platforms: %s", PLATFORMS)
        
    except Exception as exc:
        error_msg = f"Error setting up Smart Climate platform: {exc}"
        _LOGGER.error(error_msg, exc_info=True)
        raise HomeAssistantError(error_msg) from exc
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok