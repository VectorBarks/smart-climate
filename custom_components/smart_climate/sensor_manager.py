"""ABOUTME: SensorManager for reading temperature and power sensors.
Manages sensor state tracking and provides callbacks for state changes."""

import logging
from typing import Callable, Optional, List

from homeassistant.core import HomeAssistant, State
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.helpers.event import async_track_state_change_event

_LOGGER = logging.getLogger(__name__)


class SensorManager:
    """Manages sensor reading and state tracking."""
    
    def __init__(
        self,
        hass: HomeAssistant,
        room_sensor_id: str,
        outdoor_sensor_id: Optional[str] = None,
        power_sensor_id: Optional[str] = None,
        indoor_humidity_sensor_id: Optional[str] = None,
        outdoor_humidity_sensor_id: Optional[str] = None
    ):
        """Initialize SensorManager.
        
        Args:
            hass: Home Assistant instance
            room_sensor_id: Entity ID of room temperature sensor (required)
            outdoor_sensor_id: Entity ID of outdoor temperature sensor (optional)
            power_sensor_id: Entity ID of power consumption sensor (optional)
            indoor_humidity_sensor_id: Entity ID of indoor humidity sensor (optional)
            outdoor_humidity_sensor_id: Entity ID of outdoor humidity sensor (optional)
        """
        self._hass = hass
        self._room_sensor_id = room_sensor_id
        self._outdoor_sensor_id = outdoor_sensor_id
        self._power_sensor_id = power_sensor_id
        self._indoor_humidity_sensor_id = indoor_humidity_sensor_id
        self._outdoor_humidity_sensor_id = outdoor_humidity_sensor_id
        self._update_callbacks: List[Callable] = []
        self._remove_listeners: List[Callable] = []
        
        _LOGGER.debug(
            "SensorManager initialized with room=%s, outdoor=%s, power=%s, indoor_humidity=%s, outdoor_humidity=%s",
            room_sensor_id, outdoor_sensor_id, power_sensor_id, indoor_humidity_sensor_id, outdoor_humidity_sensor_id
        )
    
    def get_room_temperature(self) -> Optional[float]:
        """Get current room temperature from sensor.
        
        Returns:
            Temperature in degrees Celsius, or None if unavailable
        """
        try:
            state = self._hass.states.get(self._room_sensor_id)
            if state is None:
                _LOGGER.debug("Room sensor state not found: %s", self._room_sensor_id)
                return None
            
            if state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                _LOGGER.debug("Room sensor unavailable: %s", self._room_sensor_id)
                return None
            
            temperature = float(state.state)
            return temperature
            
        except (ValueError, TypeError) as exc:
            _LOGGER.warning(
                "Failed to parse room temperature from %s: %s",
                self._room_sensor_id, exc
            )
            return None
        except Exception as exc:
            _LOGGER.error(
                "Error reading room temperature from %s: %s",
                self._room_sensor_id, exc
            )
            return None
    
    def get_outdoor_temperature(self) -> Optional[float]:
        """Get current outdoor temperature if available.
        
        Returns:
            Temperature in degrees Celsius, or None if unavailable or not configured
        """
        if self._outdoor_sensor_id is None:
            return None
        
        try:
            state = self._hass.states.get(self._outdoor_sensor_id)
            if state is None:
                _LOGGER.debug("Outdoor sensor state not found: %s", self._outdoor_sensor_id)
                return None
            
            if state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                _LOGGER.debug("Outdoor sensor unavailable: %s", self._outdoor_sensor_id)
                return None
            
            temperature = float(state.state)
            return temperature
            
        except (ValueError, TypeError) as exc:
            _LOGGER.warning(
                "Failed to parse outdoor temperature from %s: %s",
                self._outdoor_sensor_id, exc
            )
            return None
        except Exception as exc:
            _LOGGER.error(
                "Error reading outdoor temperature from %s: %s",
                self._outdoor_sensor_id, exc
            )
            return None
    
    def get_power_consumption(self) -> Optional[float]:
        """Get current power consumption if available.
        
        Returns:
            Power consumption in watts, or None if unavailable or not configured
        """
        if self._power_sensor_id is None:
            return None
        
        try:
            state = self._hass.states.get(self._power_sensor_id)
            if state is None:
                _LOGGER.debug("Power sensor state not found: %s", self._power_sensor_id)
                return None
            
            if state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                _LOGGER.debug("Power sensor unavailable: %s", self._power_sensor_id)
                return None
            
            power = float(state.state)
            _LOGGER.debug("Power consumption: %.1f W", power)
            return power
            
        except (ValueError, TypeError) as exc:
            _LOGGER.warning(
                "Failed to parse power consumption from %s: %s",
                self._power_sensor_id, exc
            )
            return None
        except Exception as exc:
            _LOGGER.error(
                "Error reading power consumption from %s: %s",
                self._power_sensor_id, exc
            )
            return None
    
    def get_indoor_humidity(self) -> Optional[float]:
        """Get current indoor humidity if available.
        
        Returns:
            Humidity percentage, or None if unavailable or not configured
        """
        if self._indoor_humidity_sensor_id is None:
            return None
        
        try:
            state = self._hass.states.get(self._indoor_humidity_sensor_id)
            if state is None:
                _LOGGER.debug("Indoor humidity sensor state not found: %s", self._indoor_humidity_sensor_id)
                return None
            
            if state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                _LOGGER.debug("Indoor humidity sensor unavailable: %s", self._indoor_humidity_sensor_id)
                return None
            
            humidity = float(state.state)
            return humidity
            
        except (ValueError, TypeError) as exc:
            _LOGGER.warning(
                "Failed to parse indoor humidity from %s: %s",
                self._indoor_humidity_sensor_id, exc
            )
            return None
        except Exception as exc:
            _LOGGER.error(
                "Error reading indoor humidity from %s: %s",
                self._indoor_humidity_sensor_id, exc
            )
            return None
    
    def get_outdoor_humidity(self) -> Optional[float]:
        """Get current outdoor humidity if available.
        
        Returns:
            Humidity percentage, or None if unavailable or not configured
        """
        if self._outdoor_humidity_sensor_id is None:
            return None
        
        try:
            state = self._hass.states.get(self._outdoor_humidity_sensor_id)
            if state is None:
                _LOGGER.debug("Outdoor humidity sensor state not found: %s", self._outdoor_humidity_sensor_id)
                return None
            
            if state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                _LOGGER.debug("Outdoor humidity sensor unavailable: %s", self._outdoor_humidity_sensor_id)
                return None
            
            humidity = float(state.state)
            return humidity
            
        except (ValueError, TypeError) as exc:
            _LOGGER.warning(
                "Failed to parse outdoor humidity from %s: %s",
                self._outdoor_humidity_sensor_id, exc
            )
            return None
        except Exception as exc:
            _LOGGER.error(
                "Error reading outdoor humidity from %s: %s",
                self._outdoor_humidity_sensor_id, exc
            )
            return None
    
    def register_update_callback(self, callback: Callable) -> None:
        """Register callback for sensor updates.
        
        Args:
            callback: Function to call when sensor state changes
        """
        if callback not in self._update_callbacks:
            self._update_callbacks.append(callback)
            _LOGGER.debug("Registered sensor update callback: %s", callback)
    
    async def start_listening(self) -> None:
        """Start listening to sensor state changes."""
        _LOGGER.debug("Starting sensor state listeners")
        
        # Track room sensor (required)
        remove_listener = async_track_state_change_event(
            self._hass,
            self._room_sensor_id,
            self._async_sensor_state_changed
        )
        self._remove_listeners.append(remove_listener)
        _LOGGER.debug("Started listening to room sensor: %s", self._room_sensor_id)
        
        # Track outdoor sensor if configured
        if self._outdoor_sensor_id is not None:
            remove_listener = async_track_state_change_event(
                self._hass,
                self._outdoor_sensor_id,
                self._async_sensor_state_changed
            )
            self._remove_listeners.append(remove_listener)
            _LOGGER.debug("Started listening to outdoor sensor: %s", self._outdoor_sensor_id)
        
        # Track power sensor if configured
        if self._power_sensor_id is not None:
            remove_listener = async_track_state_change_event(
                self._hass,
                self._power_sensor_id,
                self._async_sensor_state_changed
            )
            self._remove_listeners.append(remove_listener)
            _LOGGER.debug("Started listening to power sensor: %s", self._power_sensor_id)
        
        # Track indoor humidity sensor if configured
        if self._indoor_humidity_sensor_id is not None:
            remove_listener = async_track_state_change_event(
                self._hass,
                self._indoor_humidity_sensor_id,
                self._async_sensor_state_changed
            )
            self._remove_listeners.append(remove_listener)
            _LOGGER.debug("Started listening to indoor humidity sensor: %s", self._indoor_humidity_sensor_id)
        
        # Track outdoor humidity sensor if configured
        if self._outdoor_humidity_sensor_id is not None:
            remove_listener = async_track_state_change_event(
                self._hass,
                self._outdoor_humidity_sensor_id,
                self._async_sensor_state_changed
            )
            self._remove_listeners.append(remove_listener)
            _LOGGER.debug("Started listening to outdoor humidity sensor: %s", self._outdoor_humidity_sensor_id)
        
        _LOGGER.info("Started listening to %d sensors", len(self._remove_listeners))
    
    async def stop_listening(self) -> None:
        """Stop all sensor listeners."""
        _LOGGER.debug("Stopping sensor state listeners")
        
        # Remove all listeners
        for remove_listener in self._remove_listeners:
            try:
                remove_listener()
            except Exception as exc:
                _LOGGER.warning("Error removing sensor listener: %s", exc)
        
        # Clear the listeners list
        self._remove_listeners.clear()
        
        _LOGGER.info("Stopped all sensor listeners")
    
    async def _async_sensor_state_changed(
        self,
        event
    ) -> None:
        """Handle sensor state change events.
        
        Args:
            event: Home Assistant event containing entity_id, old_state, new_state
        """
        entity_id = event.data.get('entity_id')
        old_state = event.data.get('old_state')
        new_state = event.data.get('new_state')
        
        _LOGGER.debug(
            "Sensor state changed: %s from %s to %s",
            entity_id,
            old_state.state if old_state else None,
            new_state.state if new_state else None
        )
        
        # Notify all registered callbacks
        for callback in self._update_callbacks:
            try:
                if hasattr(callback, '__call__'):
                    callback()
            except Exception as exc:
                _LOGGER.error(
                    "Error calling sensor update callback %s: %s",
                    callback, exc
                )