"""ABOUTME: Helper functions for Smart Climate Control integration.
Provides entity availability waiting and other utility functions."""

import asyncio
import logging
from typing import List
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_wait_for_entities(
    hass: HomeAssistant, entity_ids: List[str], timeout: int = 60
) -> bool:
    """Wait for entities to become available within timeout.
    
    Checks that entities are not STATE_UNAVAILABLE or STATE_UNKNOWN
    and returns True if all are available within timeout, False otherwise.
    
    Features:
    - 1-second polling interval for responsive checking
    - Progress logging for user visibility  
    - Graceful handling of cancelled tasks
    - Clear timeout reporting
    
    Args:
        hass: Home Assistant instance
        entity_ids: List of entity IDs to wait for
        timeout: Maximum time to wait in seconds (default: 60)
        
    Returns:
        True if all entities become available within timeout, False otherwise
    """
    if not entity_ids:
        _LOGGER.debug("No entities to wait for, returning True immediately")
        return True
    
    _LOGGER.info("Waiting for %d entities to become available: %s", len(entity_ids), entity_ids)
    
    try:
        loop = asyncio.get_running_loop()
        start_time = loop.time()
    except RuntimeError:
        # Fallback for older Python versions or edge cases
        start_time = asyncio.get_event_loop().time()
        loop = asyncio.get_event_loop()
    
    try:
        while True:
            # Check all entities
            unavailable_entities = []
            
            for entity_id in entity_ids:
                state = hass.states.get(entity_id)
                if not state or state.state in ("unavailable", "unknown"):
                    unavailable_entities.append(entity_id)
            
            # If all entities are available, we're done
            if not unavailable_entities:
                elapsed = loop.time() - start_time
                _LOGGER.info("All entities are now available after %.1fs", elapsed)
                return True
            
            # Check timeout
            elapsed = loop.time() - start_time
            if elapsed >= timeout:
                _LOGGER.warning("Entities not available after %ds timeout: %s", timeout, unavailable_entities)
                return False
            
            # Log waiting status (reduce log frequency after first message)
            if elapsed < 1.0:
                _LOGGER.info("Waiting for %d entities: %s", len(unavailable_entities), unavailable_entities)
            elif int(elapsed) % 10 == 0:  # Log every 10 seconds after initial
                _LOGGER.info(
                    "Still waiting for %d entities after %.0fs: %s", 
                    len(unavailable_entities), elapsed, unavailable_entities
                )
            
            # Wait 1 second before checking again
            await asyncio.sleep(1.0)
            
    except asyncio.CancelledError:
        elapsed = loop.time() - start_time
        _LOGGER.debug("Entity waiting cancelled after %.1fs", elapsed)
        raise  # Re-raise to preserve cancellation behavior