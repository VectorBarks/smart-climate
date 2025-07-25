"""Smart Climate Control integration."""

import asyncio
import logging
import os
from typing import Any, Dict, List
from datetime import timedelta

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import Platform
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er, config_validation as cv
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.components.persistent_notification import (
    async_create as async_create_notification,
)

from .const import DOMAIN, PLATFORMS
from .data_store import SmartClimateDataStore
from .entity_waiter import EntityWaiter, EntityNotAvailableError
from .offset_engine import OffsetEngine
from .seasonal_learner import SeasonalHysteresisLearner

# Version and basic metadata
__version__ = "0.1.0"
__author__ = "Smart Climate Team"


def _read_file_sync(file_path: str) -> str:
    """Read file synchronously - for use with async_add_executor_job."""
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()

_LOGGER = logging.getLogger(__name__)

# Retry configuration defaults
DEFAULT_RETRY_ENABLED = True
DEFAULT_MAX_RETRY_ATTEMPTS = 4
DEFAULT_INITIAL_TIMEOUT = 60
RETRY_DELAYS = [30, 60, 120, 240]  # Exponential backoff in seconds


async def _schedule_retry(hass: HomeAssistant, entry: ConfigEntry, attempt: int) -> None:
    """Schedule a retry for config entry setup."""
    # Calculate delay with exponential backoff, capped at 240 seconds
    delay = RETRY_DELAYS[min(attempt - 1, len(RETRY_DELAYS) - 1)]
    
    _LOGGER.info(
        "Scheduling retry #%d for Smart Climate entry %s in %d seconds",
        attempt, entry.entry_id, delay
    )
    
    async def retry_setup(now):
        """Retry the setup."""
        _LOGGER.info("Retrying setup for Smart Climate entry %s (attempt #%d)", entry.entry_id, attempt)
        await hass.config_entries.async_reload(entry.entry_id)
    
    # Schedule the retry
    async_call_later(hass, delay, retry_setup)


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
    entry_data = {
        "config": entry.data,
        "offset_engines": {},  # Stores one engine per climate entity
        "data_stores": {},  # Stores one data store per climate entity
        "coordinators": {},  # Stores one coordinator per climate entity
        "unload_listeners": [],  # To clean up periodic save tasks
    }
    
    # Get retry attempt from runtime data if exists
    retry_attempt = hass.data.setdefault(DOMAIN, {}).get(entry.entry_id, {}).get("_retry_attempt", 0)
    
    # Store entry data
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry_data

    # Wait for required entities to become available
    try:
        entity_waiter = EntityWaiter()
        # Get configurable timeout, cap at 300 seconds
        timeout = min(entry.data.get("initial_timeout", DEFAULT_INITIAL_TIMEOUT), 300)
        await entity_waiter.wait_for_required_entities(hass, entry.data, timeout=timeout)
        _LOGGER.info("All required entities are available for entry: %s", entry.entry_id)
        
        # Clear retry attempt on successful entity wait
        if "_retry_attempt" in hass.data[DOMAIN][entry.entry_id]:
            del hass.data[DOMAIN][entry.entry_id]["_retry_attempt"]
            
    except EntityNotAvailableError as exc:
        # Check if retry is enabled
        if not entry.data.get("enable_retry", DEFAULT_RETRY_ENABLED):
            raise HomeAssistantError(f"Required entities not available: {exc}") from exc
            
        # Check if we've exceeded max retry attempts
        max_attempts = entry.data.get("max_retry_attempts", DEFAULT_MAX_RETRY_ATTEMPTS)
        if retry_attempt >= max_attempts:
            # Send notification about failure
            await async_create_notification(
                hass,
                title="Smart Climate Setup Failed",
                message=(
                    f"Smart Climate '{entry.title}' failed to initialize after {max_attempts} attempts. "
                    f"Required entities are not available: {exc}\n\n"
                    "You can manually reload the integration when entities are available:\n"
                    "1. Go to Settings → Devices & Services\n"
                    "2. Find the Smart Climate integration\n"
                    "3. Click the three dots menu\n"
                    "4. Select 'Reload'"
                ),
                notification_id=f"smart_climate_setup_failed_{entry.entry_id}",
            )
            _LOGGER.error(
                "Smart Climate setup failed after %d retry attempts for entry %s: %s",
                max_attempts, entry.entry_id, exc
            )
            return False
            
        # Schedule retry
        retry_attempt += 1
        hass.data[DOMAIN][entry.entry_id]["_retry_attempt"] = retry_attempt
        await _schedule_retry(hass, entry, retry_attempt)
        return False

    # --- SEASONAL ADAPTATION INTEGRATION ---
    # Set up seasonal learning infrastructure for each climate entity
    climate_entities = []
    
    # Handle both single entity (climate_entity) and multiple entities configurations
    if "climate_entity" in entry.data:
        climate_entities = [entry.data["climate_entity"]]
    elif "climate_entities" in entry.data:
        climate_entities = entry.data["climate_entities"]
    
    if climate_entities:
        _LOGGER.debug("Setting up seasonal adaptation for climate entities: %s", climate_entities)
        
        # Initialize seasonal learners storage
        entry_data["seasonal_learners"] = {}
        
        # Check for outdoor sensor configuration
        outdoor_sensor_id = entry.data.get("outdoor_sensor")
        
        # Handle empty string as None (invalid configuration)
        if outdoor_sensor_id == "":
            outdoor_sensor_id = None
        
        for entity_id in climate_entities:
            if outdoor_sensor_id is not None:
                try:
                    # Create seasonal learner for this entity
                    seasonal_learner = SeasonalHysteresisLearner(hass, outdoor_sensor_id)
                    
                    # Store for OffsetEngine integration
                    entry_data["seasonal_learners"][entity_id] = seasonal_learner
                    
                    # Load seasonal patterns from storage
                    try:
                        await seasonal_learner.async_load()
                    except Exception as load_exc:
                        _LOGGER.warning(
                            "Failed to load seasonal patterns for entity %s: %s",
                            entity_id, load_exc
                        )
                        # Continue with empty patterns - graceful degradation
                    
                    _LOGGER.info(
                        "Seasonal adaptation features enabled for entity %s with outdoor sensor %s",
                        entity_id, outdoor_sensor_id
                    )
                    
                except Exception as exc:
                    _LOGGER.warning(
                        "Failed to create seasonal learner for entity %s: %s - continuing without seasonal features",
                        entity_id, exc
                    )
                    # Continue setup without seasonal features (graceful degradation)
            else:
                _LOGGER.info(
                    "Seasonal adaptation features disabled for entity %s (no outdoor sensor configured)",
                    entity_id
                )
    
    # --- END SEASONAL ADAPTATION INTEGRATION ---

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

    # Register the dashboard generation service (only once per HA instance)
    await _async_register_services(hass)

    return True


async def _async_setup_entity_persistence(hass: HomeAssistant, entry: ConfigEntry, entity_id: str):
    """Set up persistence for a single climate entity."""
    _LOGGER.debug("Setting up persistence for entity: %s", entity_id)

    # 1. Get seasonal learner for this entity (if available)
    entry_data = hass.data[DOMAIN][entry.entry_id]
    seasonal_learner = entry_data.get("seasonal_learners", {}).get(entity_id, None)
    
    # 2. Always create a dedicated OffsetEngine for this entity
    offset_engine = OffsetEngine(entry.data, seasonal_learner)
    
    # Store the engine instance for the platform to use, keyed by entity_id
    hass.data[DOMAIN][entry.entry_id]["offset_engines"][entity_id] = offset_engine
    
    # Create DataUpdateCoordinator for this entity
    async def async_update_data():
        """Fetch data from offset engine."""
        try:
            data = await offset_engine.async_get_dashboard_data()
            return data
        except Exception as exc:
            _LOGGER.error("Error fetching dashboard data for %s: %s", entity_id, exc)
            raise UpdateFailed(f"Error fetching dashboard data: {exc}") from exc
    
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"smart_climate_{entry.entry_id}_{entity_id}",
        update_method=async_update_data,
        update_interval=timedelta(seconds=30),
    )
    
    # Store the coordinator instance for the sensor platform to use
    hass.data[DOMAIN][entry.entry_id]["coordinators"][entity_id] = coordinator

    # 3. Try to create persistence - graceful degradation if it fails
    try:
        data_store = SmartClimateDataStore(hass, entity_id)
        
        # Store the data store instance for the button platform to use
        hass.data[DOMAIN][entry.entry_id]["data_stores"][entity_id] = data_store
        
        # 4. Link the data store to the engine for persistence operations
        offset_engine.set_data_store(data_store)
        
        # 5. Load saved learning data and restore engine state
        try:
            learning_data_loaded = await offset_engine.async_load_learning_data()
            if learning_data_loaded:
                _LOGGER.debug("Learning data and engine state restored for entity: %s", entity_id)
            else:
                _LOGGER.debug("No learning data to restore for entity: %s", entity_id)
        except Exception as exc:
            _LOGGER.warning("Failed to load learning data for %s: %s", entity_id, exc)
            # Continue setup without loaded data

        # 6. Set up periodic saving and store the unload callback for cleanup
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
    
    # 7. Perform initial coordinator data fetch
    try:
        await coordinator.async_config_entry_first_refresh()
        _LOGGER.debug("Initial coordinator data fetched for entity: %s", entity_id)
    except Exception as exc:
        _LOGGER.warning("Failed to fetch initial coordinator data for %s: %s", entity_id, exc)
        # Continue without initial data - coordinator will retry on its schedule


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

        # Perform final save for all offset engines with timeout protection
        offset_engines = entry_data.get("offset_engines", {})
        if offset_engines:
            _LOGGER.info("Starting shutdown save for %d offset engines", len(offset_engines))
            
            # Create save tasks for all engines
            save_tasks = []
            for entity_id, offset_engine in offset_engines.items():
                try:
                    save_tasks.append(offset_engine.async_save_learning_data())
                except Exception as exc:
                    _LOGGER.warning("Error creating save task for %s: %s", entity_id, exc)
            
            # Execute all saves concurrently with timeout protection
            if save_tasks:
                try:
                    # Wait for all save tasks with 5 second timeout
                    await asyncio.wait_for(
                        asyncio.gather(*save_tasks, return_exceptions=True),
                        timeout=5.0
                    )
                    _LOGGER.info("Final save completed for all entities")
                except asyncio.TimeoutError:
                    _LOGGER.warning(
                        "Shutdown save timeout after 5 seconds - some data may not be saved. "
                        "This prevents Home Assistant shutdown from hanging."
                    )
                except Exception as exc:
                    _LOGGER.warning("Error during final save: %s", exc)
        # --- END PERSISTENCE CLEANUP ---

    _LOGGER.info("Smart Climate Control unload completed for entry: %s", entry.entry_id)
    return unload_ok


async def handle_generate_dashboard(call: ServiceCall) -> None:
    """Handle the generate_dashboard service call."""
    hass = call.hass
    climate_entity_id = call.data.get("climate_entity_id")
    _LOGGER.debug("Generating dashboard for entity: %s", climate_entity_id)

    # Validate entity exists
    entity_registry = er.async_get(hass)
    entity_entry = entity_registry.async_get(climate_entity_id)
    if not entity_entry:
        raise ServiceValidationError(
            f"Entity {climate_entity_id} not found"
        )
    
    # Validate entity is from smart_climate integration
    if entity_entry.platform != DOMAIN:
        raise ServiceValidationError(
            f"Entity {climate_entity_id} is not a Smart Climate entity"
        )
    
    # Get entity friendly name
    state = hass.states.get(climate_entity_id)
    friendly_name = state.attributes.get("friendly_name", climate_entity_id) if state else climate_entity_id
    
    # Extract entity ID without domain
    entity_id_without_domain = climate_entity_id.split(".", 1)[1]
    
    # Find the config entry for this climate entity
    config_entry_id = entity_entry.config_entry_id
    if not config_entry_id:
        raise ServiceValidationError(
            f"No config entry found for {climate_entity_id}"
        )
    
    # Get the config entry to access user-configured sensor entity IDs
    config_entry = hass.config_entries.async_get_entry(config_entry_id)
    if not config_entry:
        raise ServiceValidationError(
            f"Config entry {config_entry_id} not found"
        )
    
    # Extract user's configured sensor entity IDs from config entry data
    user_room_sensor = config_entry.data.get("room_sensor") or "sensor.unknown"
    user_outdoor_sensor = config_entry.data.get("outdoor_sensor") or "sensor.unknown"
    user_power_sensor = config_entry.data.get("power_sensor") or "sensor.unknown"
    
    _LOGGER.debug("User configured sensors - room: %s, outdoor: %s, power: %s", 
                 user_room_sensor, user_outdoor_sensor, user_power_sensor)
    # Dynamically discover all related entities for this Smart Climate instance
    # Pattern 1: Look for entities with matching config_entry_id
    all_entities = entity_registry.entities
    related_entities = {
        "sensors": {},
        "switch": None,
        "button": None
    }
    
    # Sensor types we're looking for
    sensor_types = ["offset_current", "learning_progress", "accuracy_current", 
                   "calibration_status", "hysteresis_state"]
    
    _LOGGER.debug("Looking for entities with config_entry_id: %s", config_entry_id)
    
    for entity_id, entity in all_entities.items():
        if entity.config_entry_id == config_entry_id:
            _LOGGER.debug("Found entity %s: domain=%s, platform=%s, unique_id=%s", 
                        entity.entity_id, entity.domain, entity.platform, entity.unique_id)
            # Check if it's a sensor
            if entity.domain == "sensor" and entity.platform == DOMAIN:
                # Try to identify sensor type from unique_id
                for sensor_type in sensor_types:
                    if sensor_type in entity.unique_id:
                        related_entities["sensors"][sensor_type] = entity.entity_id
                        _LOGGER.debug("Identified %s sensor: %s", sensor_type, entity.entity_id)
                        break
            # Check if it's the learning switch
            elif entity.domain == "switch" and entity.platform == DOMAIN:
                related_entities["switch"] = entity.entity_id
                _LOGGER.debug("Found learning switch: %s", entity.entity_id)
            # Check if it's the reset button
            elif entity.domain == "button" and entity.platform == DOMAIN:
                related_entities["button"] = entity.entity_id
                _LOGGER.debug("Found reset button: %s", entity.entity_id)
    
    # Validate we found all required entities
    missing_sensors = [st for st in sensor_types if st not in related_entities["sensors"]]
    if missing_sensors:
        _LOGGER.warning("Missing sensors: %s", missing_sensors)
    
    if not related_entities["switch"]:
        _LOGGER.warning("Learning switch not found")
    
    if not related_entities["button"]:
        _LOGGER.warning("Reset button not found")
    
    # Read dashboard template
    template_path = os.path.join(
        os.path.dirname(__file__),
        "dashboard",
        "dashboard_generic.yaml"
    )
    
    if not os.path.exists(template_path):
        raise ServiceValidationError(
            "Dashboard template file not found"
        )
    
    try:
        _LOGGER.debug("Reading dashboard template from %s", template_path)
        template_content = await hass.async_add_executor_job(
            _read_file_sync, template_path
        )
        _LOGGER.debug("Dashboard template read successfully (%d characters)", len(template_content))
    except Exception as exc:
        _LOGGER.error("Failed to read dashboard template: %s", exc)
        raise ServiceValidationError(
            f"Failed to read dashboard template: {exc}"
        ) from exc
    
    # Replace placeholders with actual entity IDs
    _LOGGER.debug("Replacing template placeholders for %s", climate_entity_id)
    dashboard_yaml = template_content.replace(
        "REPLACE_ME_CLIMATE", climate_entity_id
    ).replace(
        "REPLACE_ME_NAME", friendly_name
    ).replace(
        "REPLACE_ME_SENSOR_OFFSET", related_entities["sensors"].get("offset_current", "sensor.unknown")
    ).replace(
        "REPLACE_ME_SENSOR_PROGRESS", related_entities["sensors"].get("learning_progress", "sensor.unknown")
    ).replace(
        "REPLACE_ME_SENSOR_ACCURACY", related_entities["sensors"].get("accuracy_current", "sensor.unknown")
    ).replace(
        "REPLACE_ME_SENSOR_CALIBRATION", related_entities["sensors"].get("calibration_status", "sensor.unknown")
    ).replace(
        "REPLACE_ME_SENSOR_HYSTERESIS", related_entities["sensors"].get("hysteresis_state", "sensor.unknown")
    ).replace(
        "REPLACE_ME_SWITCH", related_entities["switch"] or "switch.unknown"
    ).replace(
        "REPLACE_ME_BUTTON", related_entities["button"] or "button.unknown"
    ).replace(
        "REPLACE_ME_ROOM_SENSOR", user_room_sensor
    ).replace(
        "REPLACE_ME_OUTDOOR_SENSOR", user_outdoor_sensor
    ).replace(
        "REPLACE_ME_POWER_SENSOR", user_power_sensor
    )
    _LOGGER.debug("Template processing complete, dashboard YAML generated (%d characters)", len(dashboard_yaml))
    _LOGGER.debug("Replaced sensor placeholders - room: %s, outdoor: %s, power: %s", 
                 user_room_sensor, user_outdoor_sensor, user_power_sensor)
    
    # CRITICAL BUG FIX: Validate that ALL placeholders were replaced
    import re
    remaining_placeholders = re.findall(r'REPLACE_ME_\w+', dashboard_yaml)
    if remaining_placeholders:
        _LOGGER.error("Dashboard generation failed: Unreplaced placeholders found: %s", remaining_placeholders)
        raise ServiceValidationError(
            f"Dashboard generation failed: The following placeholders could not be replaced: {', '.join(remaining_placeholders)}. "
            f"This indicates missing entities or incomplete placeholder replacement logic."
        )
    
    _LOGGER.debug("Placeholder validation successful: All placeholders replaced")
    
    # Create notification with instructions
    notification_message = (
        "Copy the YAML below and use it to create a new dashboard:\n\n"
        "1. Go to Settings → Dashboards\n"
        "2. Click 'Add Dashboard'\n"
        "3. Give it a name and click 'Create'\n"
        "4. Click 'Edit Dashboard' (three dots menu)\n"
        "5. Click 'Raw Configuration Editor' (three dots menu)\n"
        "6. Replace the content with the YAML below\n"
        "7. Click 'Save'\n\n"
        f"```yaml\n{dashboard_yaml}\n```"
    )
    
    # Create notification with dashboard YAML
    _LOGGER.debug("Creating notification for dashboard generation")
    try:
        async_create_notification(
            hass,
            title=f"Smart Climate Dashboard - {friendly_name}",
            message=notification_message,
            notification_id=f"smart_climate_dashboard_{entity_id_without_domain}",
        )
        _LOGGER.debug("Notification created successfully")
    except Exception as exc:
        _LOGGER.error("Failed to create notification: %s", exc)
        raise ServiceValidationError(
            f"Failed to create notification: {exc}"
        ) from exc
    
    _LOGGER.info(
        "Dashboard generated for %s and sent via notification",
        climate_entity_id
    )


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register Smart Climate services."""
    if hass.services.has_service(DOMAIN, "generate_dashboard"):
        return  # Service already registered
    
    # Define schema for generate_dashboard service
    generate_dashboard_schema = vol.Schema({
        vol.Required("climate_entity_id"): cv.entity_id,
    })

    # Register the service
    try:
        hass.services.async_register(
            DOMAIN,
            "generate_dashboard",
            handle_generate_dashboard,
            schema=generate_dashboard_schema,
        )
        
        _LOGGER.info("Smart Climate service 'generate_dashboard' registered successfully")
    except Exception as exc:
        _LOGGER.error("Failed to register Smart Climate service: %s", exc, exc_info=True)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    _LOGGER.info("Reloading Smart Climate Control for entry: %s", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)