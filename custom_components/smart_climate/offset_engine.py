"""Offset calculation engine for Smart Climate Control."""

import logging
from typing import Optional

from .models import OffsetInput, OffsetResult

_LOGGER = logging.getLogger(__name__)


class OffsetEngine:
    """Calculates temperature offset for accurate climate control."""
    
    def __init__(self, config: dict):
        """Initialize the offset engine with configuration."""
        self._max_offset = config.get("max_offset", 5.0)
        self._ml_enabled = config.get("ml_enabled", True)
        self._ml_model = None  # Loaded when available
        
        _LOGGER.debug(
            "OffsetEngine initialized with max_offset=%s, ml_enabled=%s",
            self._max_offset,
            self._ml_enabled
        )
    
    def calculate_offset(self, input_data: OffsetInput) -> OffsetResult:
        """Calculate temperature offset based on current conditions.
        
        Args:
            input_data: OffsetInput containing all sensor data and context
            
        Returns:
            OffsetResult with calculated offset and metadata
        """
        try:
            # Calculate basic offset from temperature difference
            temp_diff = input_data.ac_internal_temp - input_data.room_temp
            base_offset = -temp_diff  # Negative because we want to correct the difference
            
            # Apply mode-specific adjustments
            mode_adjusted_offset = self._apply_mode_adjustments(base_offset, input_data)
            
            # Apply contextual adjustments
            context_adjusted_offset = self._apply_contextual_adjustments(
                mode_adjusted_offset, input_data
            )
            
            # Clamp to maximum limit
            final_offset, was_clamped = self._clamp_offset(context_adjusted_offset)
            
            # Generate reason and confidence
            reason = self._generate_reason(input_data, final_offset, was_clamped)
            confidence = self._calculate_confidence(input_data)
            
            _LOGGER.debug(
                "Calculated offset: %.2f (clamped: %s, reason: %s, confidence: %.2f)",
                final_offset, was_clamped, reason, confidence
            )
            
            return OffsetResult(
                offset=final_offset,
                clamped=was_clamped,
                reason=reason,
                confidence=confidence
            )
            
        except Exception as exc:
            _LOGGER.error("Error calculating offset: %s", exc)
            # Return safe fallback
            return OffsetResult(
                offset=0.0,
                clamped=False,
                reason="Error in calculation, using safe fallback",
                confidence=0.0
            )
    
    def _apply_mode_adjustments(self, base_offset: float, input_data: OffsetInput) -> float:
        """Apply mode-specific adjustments to the base offset."""
        if input_data.mode == "away":
            # In away mode, we might want less aggressive offset
            return base_offset * 0.5
        elif input_data.mode == "sleep":
            # In sleep mode, slightly less aggressive for comfort
            return base_offset * 0.8
        elif input_data.mode == "boost":
            # In boost mode, more aggressive offset for faster response
            return base_offset * 1.2
        else:
            # Normal mode, no adjustment
            return base_offset
    
    def _apply_contextual_adjustments(self, offset: float, input_data: OffsetInput) -> float:
        """Apply contextual adjustments based on outdoor temp, power, etc."""
        adjusted_offset = offset
        
        # Consider outdoor temperature
        if input_data.outdoor_temp is not None:
            outdoor_diff = input_data.outdoor_temp - input_data.room_temp
            if outdoor_diff > 10:  # Very hot outside
                # Might need more aggressive cooling
                adjusted_offset *= 1.1
            elif outdoor_diff < -10:  # Very cold outside
                # Might need less aggressive heating
                adjusted_offset *= 0.9
        
        # Consider power consumption
        if input_data.power_consumption is not None:
            if input_data.power_consumption > 250:  # High power usage
                # AC is working hard, might need less offset
                adjusted_offset *= 0.9
            elif input_data.power_consumption < 100:  # Low power usage
                # AC is not working much, might need more offset
                adjusted_offset *= 1.1
        
        return adjusted_offset
    
    def _clamp_offset(self, offset: float) -> tuple[float, bool]:
        """Clamp offset to maximum limits."""
        if abs(offset) <= self._max_offset:
            return offset, False
        
        # Clamp to maximum
        clamped_offset = max(-self._max_offset, min(self._max_offset, offset))
        return clamped_offset, True
    
    def _generate_reason(self, input_data: OffsetInput, offset: float, clamped: bool) -> str:
        """Generate human-readable reason for the offset."""
        if offset == 0.0:
            return "No offset needed - AC and room temperatures match"
        
        reasons = []
        
        # Main temperature difference reason
        if input_data.ac_internal_temp > input_data.room_temp:
            reasons.append("AC sensor warmer than room")
        elif input_data.ac_internal_temp < input_data.room_temp:
            reasons.append("AC sensor cooler than room")
        
        # Mode-specific reasons
        if input_data.mode == "away":
            reasons.append("away mode adjustment")
        elif input_data.mode == "sleep":
            reasons.append("sleep mode adjustment")
        elif input_data.mode == "boost":
            reasons.append("boost mode adjustment")
        
        # Contextual reasons
        if input_data.outdoor_temp is not None:
            outdoor_diff = input_data.outdoor_temp - input_data.room_temp
            if outdoor_diff > 10:
                reasons.append("hot outdoor conditions")
            elif outdoor_diff < -10:
                reasons.append("cold outdoor conditions")
        
        if input_data.power_consumption is not None:
            if input_data.power_consumption > 250:
                reasons.append("high power usage")
            elif input_data.power_consumption < 100:
                reasons.append("low power usage")
        
        # Clamping reason
        if clamped:
            reasons.append(f"clamped to limit (±{self._max_offset}°C)")
        
        return ", ".join(reasons) if reasons else "Basic offset calculation"
    
    def _calculate_confidence(self, input_data: OffsetInput) -> float:
        """Calculate confidence level in the offset calculation."""
        confidence = 0.5  # Base confidence
        
        # More data points increase confidence
        if input_data.outdoor_temp is not None:
            confidence += 0.2
        if input_data.power_consumption is not None:
            confidence += 0.2
        
        # Mode-specific confidence adjustments
        if input_data.mode in ["away", "sleep", "boost"]:
            confidence += 0.1
        
        # Ensure confidence is within bounds
        return min(1.0, max(0.0, confidence))
    
    def update_ml_model(self, model_path: str) -> None:
        """Update the ML model used for predictions.
        
        Args:
            model_path: Path to the ML model file
        """
        _LOGGER.info("ML model update requested for path: %s", model_path)
        
        if not self._ml_enabled:
            _LOGGER.warning("ML is disabled, ignoring model update")
            return
        
        # TODO: Implement ML model loading when ML features are added
        # For now, this is a placeholder
        _LOGGER.debug("ML model update is not yet implemented")
        self._ml_model = None