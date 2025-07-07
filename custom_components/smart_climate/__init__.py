"""Smart Climate Control integration."""

import logging
from typing import Any, Dict, List
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import Platform

from .const import DOMAIN

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
    
    # Store the config entry
    hass.data[DOMAIN][entry.entry_id] = entry.data
    
    # Set up the climate platform
    await hass.config_entries.async_forward_entry_setup(entry, Platform.CLIMATE)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, [Platform.CLIMATE])
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok