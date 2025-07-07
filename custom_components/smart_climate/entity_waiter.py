"""ABOUTME: Entity availability checking utility for startup timing.
Provides entity waiting logic with exponential backoff for robust startup handling."""

import asyncio
import logging
from typing import List, Optional
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class EntityNotAvailableError(Exception):
    """Exception raised when entities are not available within timeout."""
    pass


class EntityWaiter:
    """Utility class for waiting for entity availability with exponential backoff."""
    
    def __init__(self):
        """Initialize EntityWaiter."""
        pass
    
    async def wait_for_entity(
        self, 
        hass: HomeAssistant, 
        entity_id: str, 
        timeout: int = 30
    ) -> bool:
        """Wait for a single entity to become available.
        
        Args:
            hass: Home Assistant instance
            entity_id: ID of the entity to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if entity becomes available
            
        Raises:
            EntityNotAvailableError: If entity doesn't become available within timeout
        """
        _LOGGER.debug("Waiting for entity %s to become available (timeout=%ds)", entity_id, timeout)
        
        start_time = asyncio.get_event_loop().time()
        attempt = 0
        delay = 1  # Start with 1 second delay
        max_delay = 16  # Cap delay at 16 seconds
        
        while True:
            # Check if entity is available
            state = hass.states.get(entity_id)
            if state and state.state not in ("unavailable", "unknown"):
                _LOGGER.debug("Entity %s is now available with state: %s", entity_id, state.state)
                return True
            
            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                raise EntityNotAvailableError(
                    f"Entity {entity_id} not available after {timeout} seconds. "
                    f"Current state: {state.state if state else 'None'}"
                )
            
            # Log waiting status
            if attempt == 0:
                _LOGGER.info("Waiting for entity %s to become available...", entity_id)
            else:
                _LOGGER.debug(
                    "Entity %s still not available after %.1fs (attempt %d), retrying in %ds",
                    entity_id, elapsed, attempt + 1, delay
                )
            
            # Wait with exponential backoff
            await asyncio.sleep(delay)
            
            # Increase delay for next attempt (exponential backoff)
            attempt += 1
            delay = min(delay * 2, max_delay)
    
    async def wait_for_entities(
        self, 
        hass: HomeAssistant, 
        entity_ids: List[str], 
        timeout: int = 60
    ) -> bool:
        """Wait for multiple entities to become available.
        
        Args:
            hass: Home Assistant instance
            entity_ids: List of entity IDs to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if all entities become available
            
        Raises:
            EntityNotAvailableError: If any entity doesn't become available within timeout
        """
        if not entity_ids:
            _LOGGER.debug("No entities to wait for")
            return True
        
        _LOGGER.info("Waiting for %d entities to become available: %s", len(entity_ids), entity_ids)
        
        start_time = asyncio.get_event_loop().time()
        attempt = 0
        delay = 1  # Start with 1 second delay
        max_delay = 16  # Cap delay at 16 seconds
        
        while True:
            # Check all entities
            unavailable_entities = []
            
            for entity_id in entity_ids:
                state = hass.states.get(entity_id)
                if not state or state.state in ("unavailable", "unknown"):
                    unavailable_entities.append(entity_id)
            
            # If all entities are available, we're done
            if not unavailable_entities:
                _LOGGER.info("All entities are now available")
                return True
            
            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                raise EntityNotAvailableError(
                    f"Required entities not available after {timeout} seconds: {unavailable_entities}"
                )
            
            # Log waiting status
            if attempt == 0:
                _LOGGER.info("Waiting for %d entities: %s", len(unavailable_entities), unavailable_entities)
            else:
                _LOGGER.debug(
                    "Still waiting for %d entities after %.1fs (attempt %d): %s. Retrying in %ds",
                    len(unavailable_entities), elapsed, attempt + 1, unavailable_entities, delay
                )
            
            # Wait with exponential backoff
            await asyncio.sleep(delay)
            
            # Increase delay for next attempt (exponential backoff)
            attempt += 1
            delay = min(delay * 2, max_delay)
    
    async def wait_for_required_entities(
        self,
        hass: HomeAssistant,
        config: dict,
        timeout: int = 60
    ) -> bool:
        """Wait for required entities from configuration.
        
        Args:
            hass: Home Assistant instance
            config: Configuration dictionary
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if required entities become available
            
        Raises:
            EntityNotAvailableError: If required entities don't become available within timeout
        """
        # Identify required entities (must exist)
        required_entities = []
        
        # Climate entity is always required
        if "climate_entity" in config:
            required_entities.append(config["climate_entity"])
        
        # Room sensor is always required
        if "room_sensor" in config:
            required_entities.append(config["room_sensor"])
        
        if not required_entities:
            _LOGGER.warning("No required entities found in configuration")
            return True
        
        _LOGGER.info("Checking availability of required entities: %s", required_entities)
        
        # Optional entities (logged but not blocking)
        optional_entities = []
        for key in ["outdoor_sensor", "power_sensor"]:
            if config.get(key):
                optional_entities.append(config[key])
        
        if optional_entities:
            _LOGGER.debug("Optional entities (not blocking startup): %s", optional_entities)
            
            # Check optional entities availability for logging
            for entity_id in optional_entities:
                state = hass.states.get(entity_id)
                if state and state.state not in ("unavailable", "unknown"):
                    _LOGGER.debug("Optional entity %s is available", entity_id)
                else:
                    _LOGGER.info("Optional entity %s is not available (will proceed without it)", entity_id)
        
        # Wait for required entities only
        await self.wait_for_entities(hass, required_entities, timeout)
        
        _LOGGER.info("All required entities are available, proceeding with setup")
        return True