"""Exception definitions for Smart Climate Control integration."""


class SmartClimateError(Exception):
    """Base exception for all smart climate errors."""
    pass


class SensorUnavailableError(SmartClimateError):
    """Raised when required sensor is unavailable."""
    pass


class OffsetCalculationError(SmartClimateError):
    """Raised when offset calculation fails."""
    pass


class ConfigurationError(SmartClimateError):
    """Raised when configuration is invalid."""
    pass


class WrappedEntityError(SmartClimateError):
    """Raised when wrapped entity operations fail."""
    pass