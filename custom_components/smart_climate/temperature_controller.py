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
    
    def __init__(
        self, 
        hass: HomeAssistant, 
        limits: TemperatureLimits,
        gradual_adjustment_rate: Optional[float] = None
    ):
        """Initialize TemperatureController.
        
        Args:
            hass: Home Assistant instance
            limits: Temperature safety limits
            gradual_adjustment_rate: Rate of gradual adjustment (default: 0.5°C per update)
        """
        self._hass = hass
        self._limits = limits
        self._gradual_adjustment_rate = gradual_adjustment_rate if gradual_adjustment_rate is not None else 0.5
        self._last_adjustment = 0.0
        
        _LOGGER.debug(
            "TemperatureController initialized with limits: %.1f-%.1f°C, gradual_adjustment_rate: %.1f°C",
            limits.min_temperature,
            limits.max_temperature,
            self._gradual_adjustment_rate
        )
    
    def apply_offset_and_limits(
        self,
        target_temp: float,
        offset: float,
        mode_adjustments: ModeAdjustments,
        room_temp: Optional[float] = None
    ) -> float:
        """Apply offset and safety limits to target temperature.
        
        Args:
            target_temp: User's desired temperature
            offset: Calculated offset from OffsetEngine
            mode_adjustments: Current mode adjustments
            room_temp: Current room temperature (optional for backward compatibility)
            
        Returns:
            Adjusted temperature to send to wrapped entity
        """
        # Log input parameters
        _LOGGER.debug(
            "apply_offset_and_limits - Input: target_temp=%.1f°C, offset=%.2f°C, room_temp=%s°C, "
            "mode_adjustments=(temp_override=%s, offset_adj=%.2f°C, boost=%.2f°C)",
            target_temp,
            offset,
            room_temp if room_temp is not None else "N/A",
            mode_adjustments.temperature_override,
            mode_adjustments.offset_adjustment,
            mode_adjustments.boost_offset
        )
        
        # Use override temperature if available (for away mode)
        if mode_adjustments.temperature_override is not None:
            base_temp = mode_adjustments.temperature_override
            _LOGGER.debug(
                "Using mode override temperature: %.1f°C instead of target: %.1f°C",
                base_temp,
                target_temp
            )
        else:
            base_temp = target_temp
            _LOGGER.debug("Using user target temperature: %.1f°C", base_temp)
        
        # Apply base offset (compensates for sensor difference)
        adjusted_temp = base_temp + offset
        _LOGGER.debug(
            "After applying base offset: %.1f°C + %.2f°C = %.1f°C",
            base_temp,
            offset,
            adjusted_temp
        )
        
        # Apply room temperature deviation adjustment if room_temp is provided
        if room_temp is not None:
            room_deviation = room_temp - target_temp
            _LOGGER.debug(
                "Room temperature deviation: %.1f°C - %.1f°C = %.2f°C",
                room_temp,
                target_temp,
                room_deviation
            )
            
            # When room is warmer than target, we need MORE cooling (lower AC temp)
            # When room is cooler than target, we need LESS cooling (higher AC temp)
            # So we subtract the room deviation from the adjusted temperature
            adjusted_temp -= room_deviation
            _LOGGER.debug(
                "After room deviation adjustment: %.1f°C - %.2f°C = %.1f°C",
                adjusted_temp + room_deviation,
                room_deviation,
                adjusted_temp
            )
        
        # Apply mode adjustments
        if mode_adjustments.offset_adjustment != 0:
            adjusted_temp += mode_adjustments.offset_adjustment
            _LOGGER.debug(
                "After mode offset adjustment: %.1f°C + %.2f°C = %.1f°C",
                adjusted_temp - mode_adjustments.offset_adjustment,
                mode_adjustments.offset_adjustment,
                adjusted_temp
            )
        
        if mode_adjustments.boost_offset != 0:
            adjusted_temp += mode_adjustments.boost_offset
            _LOGGER.debug(
                "After boost offset: %.1f°C + %.2f°C = %.1f°C",
                adjusted_temp - mode_adjustments.boost_offset,
                mode_adjustments.boost_offset,
                adjusted_temp
            )
        
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
        else:
            _LOGGER.debug(
                "Temperature within limits: %.1f°C (limits: %.1f-%.1f°C)",
                clamped_temp,
                self._limits.min_temperature,
                self._limits.max_temperature
            )
        
        _LOGGER.debug(
            "apply_offset_and_limits - Final result: %.1f°C",
            clamped_temp
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
        
        _LOGGER.debug(
            "apply_gradual_adjustment - Input: current=%.2f°C, target=%.2f°C, "
            "difference=%.2f°C, rate_limit=%.2f°C",
            current_adjustment,
            target_adjustment,
            difference,
            self._gradual_adjustment_rate
        )
        
        # Apply rate limiting
        if abs(difference) <= self._gradual_adjustment_rate:
            # Small change, apply fully
            _LOGGER.debug(
                "Small change within rate limit: applying full adjustment to %.2f°C",
                target_adjustment
            )
            return target_adjustment
        elif difference > 0:
            # Increase limited by rate
            result = current_adjustment + self._gradual_adjustment_rate
            _LOGGER.debug(
                "Large increase: limiting to +%.2f°C per update, result=%.2f°C",
                self._gradual_adjustment_rate,
                result
            )
            return result
        else:
            # Decrease limited by rate
            result = current_adjustment - self._gradual_adjustment_rate
            _LOGGER.debug(
                "Large decrease: limiting to -%.2f°C per update, result=%.2f°C",
                self._gradual_adjustment_rate,
                result
            )
            return result
    
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