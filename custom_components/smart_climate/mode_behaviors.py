"""Mode-specific behavior constants and utilities for Smart Climate Control."""

from typing import Dict, Any

from .const import (
    DEFAULT_AWAY_TEMPERATURE,
    DEFAULT_BOOST_OFFSET as CONST_DEFAULT_BOOST_OFFSET,
    DEFAULT_SLEEP_OFFSET as CONST_DEFAULT_SLEEP_OFFSET,
)

# Default mode-specific configuration values
DEFAULT_MODE_CONFIG = {
    "away_temperature": DEFAULT_AWAY_TEMPERATURE,
    "sleep_offset": CONST_DEFAULT_SLEEP_OFFSET,
    "boost_offset": CONST_DEFAULT_BOOST_OFFSET,
}


def get_mode_defaults() -> Dict[str, Any]:
    """Get default mode configuration values.
    
    Returns:
        Dict containing default values for all modes.
    """
    return DEFAULT_MODE_CONFIG.copy()


def validate_mode_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize mode configuration.
    
    Args:
        config: Configuration dictionary to validate.
        
    Returns:
        Normalized configuration with defaults applied.
    """
    normalized = get_mode_defaults()
    
    # Apply user-provided values
    for key, value in config.items():
        if key in normalized:
            if isinstance(value, (int, float)):
                normalized[key] = float(value)
            else:
                # Keep default if invalid type
                continue
    
    return normalized


class ModeConfigConstants:
    """Constants for mode configuration keys."""
    
    AWAY_TEMPERATURE = "away_temperature"
    SLEEP_OFFSET = "sleep_offset"
    BOOST_OFFSET = "boost_offset"
    
    # Mode names
    MODE_NONE = "none"
    MODE_AWAY = "away"
    MODE_SLEEP = "sleep"
    MODE_BOOST = "boost"
    
    # Default values
    DEFAULT_AWAY_TEMP = DEFAULT_AWAY_TEMPERATURE
    DEFAULT_SLEEP_OFFSET = CONST_DEFAULT_SLEEP_OFFSET
    DEFAULT_BOOST_OFFSET = CONST_DEFAULT_BOOST_OFFSET
