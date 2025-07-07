"""Smart Climate Control integration."""

import asyncio
import logging
from typing import Any, Dict, List

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import Platform
from homeassistant.exceptions import HomeAssistantError
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, PLATFORMS
from .data_store import SmartClimateDataStore
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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Smart Climate Control from a config entry."""
    _LOGGER.info("Setting up Smart Climate Control from config entry: %s", entry.entry_id)

    # Initialize data structure for this config entry
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "config": entry.data,
        "offset_engines": {},  # Stores one engine per climate entity
        "unload_listeners": [],  # To clean up periodic save tasks
    }

    # Wait for required entities to become available
    try:
        entity_waiter = EntityWaiter()
        await entity_waiter.wait_for_required_entities(hass, entry.data, timeout=60)
        _LOGGER.info("All required entities are available for entry: %s", entry.entry_id)
    except EntityNotAvailableError as exc:
        raise HomeAssistantError(f"Required entities not available: {exc}") from exc

    # --- PERSISTENCE INTEGRATION ---
    # Set up persistence for each climate entity
    climate_entities = []
    
    # Handle both single entity (climate_entity) and multiple entities configurations
    if "climate_entity" in entry.data:
        climate_entities = [entry.data["climate_entity"]]
    elif "climate_entities" in entry.data:
        climate_entities = entry.data["climate_entities"]
    
    if not climate_entities:
        _LOGGER.warning("No climate entities found in config entry for persistence setup")
    else:
        _LOGGER.info("Setting up persistence for climate entities: %s", climate_entities)
        
        # Create setup tasks for all entities
        setup_tasks = [
            _async_setup_entity_persistence(hass, entry, entity_id)
            for entity_id in climate_entities
        ]
        
        # Run all setup tasks concurrently with error handling
        results = await asyncio.gather(*setup_tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                _LOGGER.error(
                    "Failed to set up persistence for entity %s: %s",
                    climate_entities[i], result, exc_info=result
                )
                # Entity will lack persistence, but setup continues

    # --- END PERSISTENCE INTEGRATION ---

    # Forward the setup to the platforms (climate, switch)
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        _LOGGER.info("Smart Climate Control setup completed for entry: %s", entry.entry_id)
    except Exception as exc:
        error_msg = f"Error setting up Smart Climate platforms: {exc}"
        _LOGGER.error(error_msg, exc_info=True)
        raise HomeAssistantError(error_msg) from exc

    return True


async def _async_setup_entity_persistence(hass: HomeAssistant, entry: ConfigEntry, entity_id: str):
    """Set up persistence for a single climate entity."""
    _LOGGER.debug("Setting up persistence for entity: %s", entity_id)

    # 1. Always create a dedicated OffsetEngine for this entity
    offset_engine = OffsetEngine(entry.data)
    
    # Store the engine instance for the platform to use, keyed by entity_id
    hass.data[DOMAIN][entry.entry_id]["offset_engines"][entity_id] = offset_engine

    # 2. Try to create persistence - graceful degradation if it fails
    try:
        data_store = SmartClimateDataStore(hass, entity_id)
        
        # 3. Link the data store to the engine for persistence operations
        offset_engine.set_data_store(data_store)
        
        # 4. Load saved learning data asynchronously
        try:
            await offset_engine.async_load_learning_data()
            _LOGGER.debug("Learning data loaded for entity: %s", entity_id)
        except Exception as exc:
            _LOGGER.warning("Failed to load learning data for %s: %s", entity_id, exc)
            # Continue setup without loaded data

        # 5. Set up periodic saving and store the unload callback for cleanup
        try:
            unload_listener = await offset_engine.async_setup_periodic_save(hass)
            hass.data[DOMAIN][entry.entry_id]["unload_listeners"].append(unload_listener)
            _LOGGER.debug("Periodic save configured for entity: %s", entity_id)
        except Exception as exc:
            _LOGGER.warning("Failed to setup periodic save for %s: %s", entity_id, exc)
            # Continue without periodic saving

        _LOGGER.debug("Persistence setup complete for entity: %s", entity_id)

    except Exception as exc:
        _LOGGER.warning(
            "Failed to set up persistence for entity %s: %s - continuing without persistence", 
            entity_id, exc
        )
        # Entity will work without persistence - graceful degradation


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Smart Climate Control for entry: %s", entry.entry_id)

    # Unload platforms first
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id, {})

        # --- PERSISTENCE CLEANUP ---
        # Cancel all periodic save listeners to prevent resource leaks
        unload_listeners = entry_data.get("unload_listeners", [])
        _LOGGER.debug("Canceling %d periodic save listeners", len(unload_listeners))
        
        for remove_listener in unload_listeners:
            try:
                remove_listener()
            except Exception as exc:
                _LOGGER.warning("Error removing listener during unload: %s", exc)

        # Perform final save for all offset engines
        offset_engines = entry_data.get("offset_engines", {})
        if offset_engines:
            _LOGGER.debug("Performing final save for %d offset engines", len(offset_engines))
            
            # Create save tasks for all engines
            save_tasks = []
            for entity_id, offset_engine in offset_engines.items():
                try:
                    save_tasks.append(offset_engine.async_save_learning_data())
                except Exception as exc:
                    _LOGGER.warning("Error creating save task for %s: %s", entity_id, exc)
            
            # Execute all saves concurrently
            if save_tasks:
                try:
                    await asyncio.gather(*save_tasks, return_exceptions=True)
                    _LOGGER.debug("Final save completed for all entities")
                except Exception as exc:
                    _LOGGER.warning("Error during final save: %s", exc)
        # --- END PERSISTENCE CLEANUP ---

    _LOGGER.info("Smart Climate Control unload completed for entry: %s", entry.entry_id)
    return unload_ok