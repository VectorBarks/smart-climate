"""ABOUTME: Temperature Controller for Smart Climate Control integration.
Handles temperature commands with offset calculation and safety limits."""

import logging
from dataclasses import dataclass
from typing import Optional

from homeassistant.core import HomeAssistant

from .models import ModeAdjustments

_LOGGER = logging.getLogger(__name__)


@dataclass
class TemperatureLimits:
    """Temperature safety limits."""
    min_temperature: float = 16.0
    max_temperature: float = 30.0


class TemperatureController:
    """Controls temperature commands with offset and limits."""
    
    def __init__(self, hass: HomeAssistant, limits: TemperatureLimits):
        """Initialize TemperatureController.
        
        Args:
            hass: Home Assistant instance
            limits: Temperature safety limits
        """
        self._hass = hass
        self._limits = limits
        self._gradual_adjustment_rate = 0.5
        self._last_adjustment = 0.0
        
        _LOGGER.debug(
            "TemperatureController initialized with limits: %.1f-%.1f°C",
            limits.min_temperature,
            limits.max_temperature
        )
    
    def apply_offset_and_limits(
        self,
        target_temp: float,
        offset: float,
        mode_adjustments: ModeAdjustments
    ) -> float:
        """Apply offset and safety limits to target temperature.
        
        Args:
            target_temp: User's desired temperature
            offset: Calculated offset from OffsetEngine
            mode_adjustments: Current mode adjustments
            
        Returns:
            Adjusted temperature to send to wrapped entity
        """
        # Use override temperature if available (for away mode)
        if mode_adjustments.temperature_override is not None:
            base_temp = mode_adjustments.temperature_override
        else:
            base_temp = target_temp
        
        # Apply offset
        adjusted_temp = base_temp + offset
        
        # Apply mode adjustments
        adjusted_temp += mode_adjustments.offset_adjustment
        adjusted_temp += mode_adjustments.boost_offset
        
        # Clamp to safety limits
        clamped_temp = max(
            self._limits.min_temperature,
            min(self._limits.max_temperature, adjusted_temp)
        )
        
        if clamped_temp != adjusted_temp:
            _LOGGER.debug(
                "Temperature clamped: %.1f°C -> %.1f°C (limits: %.1f-%.1f°C)",
                adjusted_temp,
                clamped_temp,
                self._limits.min_temperature,
                self._limits.max_temperature
            )
        
        return clamped_temp
    
    def apply_gradual_adjustment(
        self,
        current_adjustment: float,
        target_adjustment: float
    ) -> float:
        """Apply gradual adjustment to prevent oscillation.
        
        Args:
            current_adjustment: Current total adjustment
            target_adjustment: Target total adjustment
            
        Returns:
            Adjusted value limited by rate
        """
        difference = target_adjustment - current_adjustment
        
        # Apply rate limiting
        if abs(difference) <= self._gradual_adjustment_rate:
            # Small change, apply fully
            return target_adjustment
        elif difference > 0:
            # Increase limited by rate
            return current_adjustment + self._gradual_adjustment_rate
        else:
            # Decrease limited by rate
            return current_adjustment - self._gradual_adjustment_rate
    
    async def send_temperature_command(
        self,
        entity_id: str,
        temperature: float
    ) -> None:
        """Send temperature command to wrapped entity.
        
        Args:
            entity_id: ID of the climate entity to control
            temperature: Target temperature to set
        """
        try:
            await self._hass.services.async_call(
                "climate",
                "set_temperature",
                {
                    "entity_id": entity_id,
                    "temperature": temperature
                },
                blocking=False
            )
            
            _LOGGER.debug(
                "Temperature command sent: %s -> %.1f°C",
                entity_id,
                temperature
            )
            
        except Exception as err:
            _LOGGER.error(
                "Unexpected error sending temperature command to %s: %s",
                entity_id,
                err,
                exc_info=True
            )