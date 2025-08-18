# ABOUTME: Intelligently decides when to run thermal probes based on context

"""ProbeScheduler: Context-aware thermal probe scheduling."""

import logging
from datetime import datetime, time, timedelta, timezone
from typing import Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from homeassistant.core import HomeAssistant

from .thermal_model import PassiveThermalModel
from .thermal_models import ProbeResult

_LOGGER = logging.getLogger(__name__)
# Configuration constants from architecture specification
MIN_PROBE_INTERVAL = timedelta(hours=12)  # System recovery time
MAX_PROBE_INTERVAL = timedelta(days=7)    # Force probe if exceeded
QUIET_HOURS_START = time(22, 0)           # No probes during sleep
QUIET_HOURS_END = time(7, 0)              # Resume after wake time
OUTDOOR_TEMP_BINS = [-10, 0, 10, 20, 30]  # Adaptive based on climate


@dataclass
class AdvancedSettings:
    """Advanced configuration settings for probe scheduling."""
    min_probe_interval_hours: int = 12    # 6-24 hours range
    max_probe_interval_days: int = 7      # 3-14 days range
    quiet_hours_start: time = time(22, 0) # Customizable start time
    quiet_hours_end: time = time(7, 0)    # Customizable end time  
    information_gain_threshold: float = 0.5  # 0.1-0.9 range
    temperature_bins: List[int] = field(default_factory=lambda: [-10, 0, 10, 20, 30])
    presence_override_enabled: bool = False  # Ignore presence detection
    outdoor_temp_change_threshold: float = 5.0  # °C change for abort
    min_probe_duration_minutes: int = 15  # Minimum useful probe duration


def validate_advanced_settings(settings: AdvancedSettings) -> Tuple[bool, List[str]]:
    """Validate advanced settings configuration."""
    errors = []
    
    # Range validations
    if not (6 <= settings.min_probe_interval_hours <= 24):
        errors.append("min_probe_interval_hours must be 6-24")
        
    if not (3 <= settings.max_probe_interval_days <= 14):
        errors.append("max_probe_interval_days must be 3-14")
        
    if not (0.1 <= settings.information_gain_threshold <= 0.9):
        errors.append("information_gain_threshold must be 0.1-0.9")
        
    if not (1.0 <= settings.outdoor_temp_change_threshold <= 10.0):
        errors.append("outdoor_temp_change_threshold must be 1.0-10.0")
        
    if not (5 <= settings.min_probe_duration_minutes <= 60):
        errors.append("min_probe_duration_minutes must be 5-60")
    
    # Logical consistency checks
    min_hours = settings.min_probe_interval_hours
    max_hours = settings.max_probe_interval_days * 24
    if min_hours >= max_hours:
        errors.append("max_probe_interval must be greater than min_probe_interval")
    
    # Quiet hours validation
    if settings.quiet_hours_start == settings.quiet_hours_end:
        errors.append("quiet_hours_start and quiet_hours_end must be different")
    
    # Temperature bins validation
    if settings.temperature_bins != sorted(settings.temperature_bins):
        errors.append("temperature_bins must be sorted in ascending order")
        
    # Check for unreasonable temperature values
    if (any(temp < -40 for temp in settings.temperature_bins) or 
        any(temp > 60 for temp in settings.temperature_bins)):
        errors.append("temperature_bins contain unreasonable values (should be -40°C to 60°C)")
    
    return len(errors) == 0, errors




class LearningProfile(Enum):
    """Learning profile options for probe scheduling."""
    COMFORT = "comfort"      # Default - long intervals, requires presence
    BALANCED = "balanced"    # Standard opportunistic model  
    AGGRESSIVE = "aggressive" # Shorter intervals, may ignore presence
    CUSTOM = "custom"        # Advanced users can override all parameters


@dataclass
class ProfileConfig:
    """Configuration parameters for learning profiles."""
    min_probe_interval_hours: int
    max_probe_interval_days: int
    presence_required: bool
    information_gain_threshold: float
    quiet_hours_enabled: bool
    outdoor_temp_bins: List[int]


class ProbeScheduler:
    """Intelligently decides when to run thermal probes based on context."""
    
    def __init__(
        self,
        hass: HomeAssistant,
        thermal_model: PassiveThermalModel,
        presence_entity_id: Optional[str],
        weather_entity_id: Optional[str],
        calendar_entity_id: Optional[str] = None,
        manual_override_entity_id: Optional[str] = None,
        learning_profile: LearningProfile = LearningProfile.BALANCED
    ):
        """Initialize ProbeScheduler.
        
        Args:
            hass: Home Assistant instance
            thermal_model: PassiveThermalModel instance for probe history access
            presence_entity_id: Entity ID for presence detection
            weather_entity_id: Entity ID for weather information
            calendar_entity_id: Optional entity ID for calendar integration
            manual_override_entity_id: Optional entity ID for manual override
            learning_profile: Learning profile for probe scheduling configuration
            
        Raises:
            TypeError: If required parameters are None or invalid types
        """
        if hass is None:
            raise TypeError("hass parameter cannot be None")
        if thermal_model is None:
            raise TypeError("thermal_model parameter cannot be None")
            
        self._hass = hass
        self._model = thermal_model
        self._presence_entity_id = presence_entity_id
        self._weather_entity_id = weather_entity_id
        self._calendar_entity_id = calendar_entity_id
        self._manual_override_entity_id = manual_override_entity_id
        
        # Initialize learning profile system
        self._learning_profile = learning_profile
        self._profile_config = self._get_profile_config(learning_profile)
        
        # Set up logger for this specific instance
        self._logger = logging.getLogger(f"{__name__}.probe_scheduler")
        self._logger.debug("ProbeScheduler initialized with presence=%s, weather=%s, calendar=%s, manual=%s, profile=%s",
                          presence_entity_id, weather_entity_id, calendar_entity_id, manual_override_entity_id, learning_profile.value)
        
    def _is_quiet_hours(self, current_time: Optional[datetime] = None) -> bool:
        """Check if current time is within quiet hours.
        
        Quiet hours are defined as 22:00-07:00 to avoid sleep disruption.
        Handles overnight span correctly (22:00 to 07:00 next day).
        
        Args:
            current_time: Optional datetime to check. If None, uses datetime.now()
            
        Returns:
            True if within quiet hours (22:00-07:00), False otherwise
        """
        if current_time is None:
            current_time = datetime.now()
        
        # Get just the time component for comparison
        check_time = current_time.time()
        
        # Handle overnight quiet hours: 22:00 to 07:00 next day
        # This means: time >= 22:00 OR time < 07:00
        if QUIET_HOURS_START > QUIET_HOURS_END:  # Overnight span
            return check_time >= QUIET_HOURS_START or check_time < QUIET_HOURS_END
        else:  # Same-day span (not currently used, but robust)
            return QUIET_HOURS_START <= check_time < QUIET_HOURS_END

    def _check_presence_entity(self) -> Optional[bool]:
        """Check presence entity state if configured.
        
        Returns:
            True if away/off, False if home/on, None if unavailable/unconfigured
        """
        if not self._presence_entity_id:
            return None
            
        state = self._hass.states.get(self._presence_entity_id)
        if not state:
            self._logger.debug("Presence entity %s not found", self._presence_entity_id)
            return None
            
        if state.state in ("unavailable", "unknown"):
            self._logger.debug("Presence entity %s is %s", self._presence_entity_id, state.state)
            return None
            
        # Return True when away (off), False when home (on)
        return state.state == "off"
        
    def _check_calendar_entity(self) -> Optional[bool]:
        """Check calendar entity for work schedule if configured.
        
        Returns:
            True if at work, False if free, None if unavailable/unconfigured
        """
        if not self._calendar_entity_id:
            return None
            
        state = self._hass.states.get(self._calendar_entity_id)
        if not state:
            self._logger.debug("Calendar entity %s not found", self._calendar_entity_id)
            return None
            
        if state.state in ("unavailable", "unknown"):
            self._logger.debug("Calendar entity %s is %s", self._calendar_entity_id, state.state)
            return None
            
        # Return True when busy/at work (on), False when free (off)
        return state.state == "on"
        
    def _check_manual_override(self) -> Optional[bool]:
        """Check manual override entity if configured.
        
        Returns:
            True if override enabled, False if disabled, None if unavailable/unconfigured
        """
        if not self._manual_override_entity_id:
            return None
            
        state = self._hass.states.get(self._manual_override_entity_id)
        if not state:
            self._logger.debug("Manual override entity %s not found", self._manual_override_entity_id)
            return None
            
        if state.state in ("unavailable", "unknown"):
            self._logger.debug("Manual override entity %s is %s", self._manual_override_entity_id, state.state)
            return None
            
        # Return True when override enabled (on), False when disabled (off)
        return state.state == "on"

    def should_probe_now(self) -> bool:
        """Main decision method combining all factors.
        
        Implements decision tree from architecture specification with profile-aware logic:
        1. Force probe if maximum interval exceeded
        2. Block if minimum interval not met
        3. Block during quiet hours (if enabled in profile)
        4. Block if not opportune time (only if presence_required in profile)
        5. Block if low information gain
        6. Approve if all conditions favorable
        
        Returns:
            True if conditions are ideal for thermal probing
        """
        try:
            # Step 1: Force probe if maximum interval exceeded
            if self._check_maximum_interval_exceeded():
                self._logger.info("Probe forced: maximum interval exceeded")
                return True
            
            # Step 2: Block if minimum interval not met
            if not self._enforce_minimum_interval():
                self._logger.debug("Probe blocked: minimum interval not met")
                return False
            
            # Step 3: Block during quiet hours (if enabled in profile)
            if self._profile_config.quiet_hours_enabled and self._is_quiet_hours():
                self._logger.debug("Probe blocked: quiet hours (profile: %s)", self._learning_profile.value)
                return False
            
            # Step 4: Block if not opportune time (only if presence required in profile)
            if self._profile_config.presence_required and not self._is_opportune_time():
                self._logger.debug("Probe blocked: user present (profile: %s requires presence)", self._learning_profile.value)
                return False
            elif not self._profile_config.presence_required:
                self._logger.debug("Presence check skipped (profile: %s allows probing regardless)", self._learning_profile.value)
            
            # Step 5: Block if low information gain
            # Get current outdoor temperature for information gain analysis
            current_outdoor_temp = self._get_current_outdoor_temperature()
            probe_history = self._get_probe_history()
            
            if not self._has_high_information_gain(current_outdoor_temp, probe_history):
                self._logger.debug("Probe blocked: low information gain (threshold: %.1f)", 
                                 self._profile_config.information_gain_threshold)
                return False
            
            # All conditions favorable - approve probe
            self._logger.info("Probe approved: all conditions favorable (profile: %s)", self._learning_profile.value)
            return True
            
        except Exception as e:
            self._logger.error("Error in probe decision logic: %s", e)
            # Conservative: block probe on error
            return False
        
    def _is_opportune_time(self) -> bool:
        """Check presence hierarchy for opportune probe timing.
        
        Uses graceful degradation:
        1. Primary: Presence entity (most reliable when available)
        2. Secondary: Calendar integration (work schedule proxy)  
        3. Tertiary: Manual override input_boolean
        4. Fallback: Conservative (False - no probe)
        
        Returns:
            True if this is an opportune time for probing
        """
        self._logger.debug("Checking if this is an opportune time for probing")
        
        # Primary: Check presence entity
        presence_result = self._check_presence_entity()
        if presence_result is not None:
            self._logger.debug("Presence detection result: %s", presence_result)
            return presence_result
            
        # Secondary: Check calendar entity (work schedule proxy)
        calendar_result = self._check_calendar_entity()
        if calendar_result is not None:
            self._logger.debug("Calendar detection result: %s (fallback from presence)", calendar_result)
            return calendar_result
            
        # Tertiary: Check manual override
        override_result = self._check_manual_override()
        if override_result is not None:
            self._logger.debug("Manual override result: %s (fallback from calendar)", override_result)
            return override_result
            
        # Fallback: Conservative (no probe when no detection methods available)
        self._logger.debug("No presence detection available, using conservative fallback (False)")
        return False
        
    def _has_high_information_gain(self, current_temp: Optional[float], history) -> bool:
        """Determine if probe would provide new information.
        
        Analyzes temperature bin diversity to decide if current conditions
        would add valuable data to the thermal model. Uses profile-specific
        information gain threshold.
        
        Args:
            current_temp: Current outdoor temperature (None if unavailable)
            history: List of previous ProbeResult objects
            
        Returns:
            True if probe would provide high information gain
        """
        try:
            # If we don't have outdoor temperature, assume high information gain
            # (conservative approach - allow probe when uncertain)
            if current_temp is None:
                self._logger.debug("No outdoor temperature available, assuming high information gain")
                return True
            
            # Calculate current bin coverage
            coverage = self._get_bin_coverage(history)
            self._logger.debug("Current temperature bin coverage: %.1f%%", coverage * 100)
            
            # Get information gain threshold from profile configuration
            threshold = self._profile_config.information_gain_threshold
            
            # High information gain if:
            # 1. Overall coverage is below profile threshold, OR
            # 2. Current temperature bin has never been probed
            if coverage < threshold:
                self._logger.debug("Low bin coverage (%.1f%% < %.1f%%), high information gain", 
                                 coverage * 100, threshold * 100)
                return True
            
            # Check if current temperature bin has been probed before
            current_bin = self._get_temp_bin(current_temp)
            probed_bins = set()
            
            for probe in history:
                if probe.outdoor_temp is not None:
                    bin_index = self._get_temp_bin(probe.outdoor_temp)
                    probed_bins.add(bin_index)
            
            if current_bin not in probed_bins:
                self._logger.debug(
                    "Current temperature bin %d (%.1f°C) has never been probed, high information gain",
                    current_bin, current_temp
                )
                return True
            
            # Current bin has been probed and overall coverage is above threshold
            self._logger.debug(
                "Current temperature bin %d (%.1f°C) already probed and coverage sufficient, low information gain",
                current_bin, current_temp
            )
            return False
            
        except Exception as e:
            self._logger.error("Error calculating information gain: %s", e)
            # Conservative: assume high information gain on error
            return True  # Threshold for "high" information gain  # Need more diversity if less than 80% coverage
        
    def _get_temp_bin(self, temperature: float) -> int:
        """Get temperature bin index for given temperature.
        
        Uses adaptive temperature bins if available, falls back to static bins.
        Bin assignment depends on the effective bins (adaptive or static):
        - Static: [-10, 0, 10, 20, 30] creating 6 bins  
        - Adaptive: Climate-specific boundaries creating 6 bins
        
        Args:
            temperature: Outdoor temperature in °C
            
        Returns:
            Bin index (0-5) for diversity tracking
        """
        # Get current effective temperature bins (adaptive or static)
        temp_bins = self._get_effective_temperature_bins()
        
        # Handle temperatures below the lowest boundary
        if temperature < temp_bins[0]:
            return 0
            
        # Find the appropriate bin
        for i, boundary in enumerate(temp_bins):
            if temperature < boundary:
                return i
                
        # Handle temperatures at or above the highest boundary
        return len(temp_bins)
        
    def _get_bin_coverage(self, probe_history) -> float:
        """Calculate what fraction of temperature bins have been probed.
        
        Analyzes probe history to determine temperature diversity.
        Only considers probes with valid outdoor_temp values.
        
        Args:
            probe_history: List of ProbeResult objects to analyze
            
        Returns:
            Coverage ratio (0.0 to 1.0) where 1.0 means all bins covered
        """
        if not probe_history:
            return 0.0
            
        # Track which bins have been probed
        probed_bins = set()
        
        for probe in probe_history:
            if probe.outdoor_temp is not None:
                bin_index = self._get_temp_bin(probe.outdoor_temp)
                probed_bins.add(bin_index)
                
        # Total possible bins (6: <-10, -10-0, 0-10, 10-20, 20-30, >30)
        total_bins = len(OUTDOOR_TEMP_BINS) + 1
        
        # Calculate coverage ratio
        return len(probed_bins) / total_bins

    def _check_maximum_interval_exceeded(self) -> bool:
        """Check if maximum probe interval has been exceeded.
        
        Force probe if more than MAX_PROBE_INTERVAL (7 days) have passed
        since the last probe, regardless of other conditions.
        
        Returns:
            True if maximum interval exceeded and probe should be forced
        """
        try:
            # Get the last probe time from ThermalManager
            last_probe_time = self._get_last_probe_time()
            
            if last_probe_time is None:
                # Never probed before - don't force probe
                self._logger.debug("No previous probe found, not forcing based on maximum interval")
                return False
            
            # Calculate time since last probe
            current_time = datetime.now()
            time_since_last = current_time - last_probe_time
            
            if time_since_last >= MAX_PROBE_INTERVAL:
                self._logger.info(
                    "Maximum probe interval exceeded: %.1f days since last probe (limit: %.1f days)",
                    time_since_last.total_seconds() / 86400,
                    MAX_PROBE_INTERVAL.total_seconds() / 86400
                )
                return True
            else:
                days_remaining = (MAX_PROBE_INTERVAL - time_since_last).total_seconds() / 86400
                self._logger.debug(
                    "Maximum interval not exceeded, %.1f days remaining until forced probe",
                    days_remaining
                )
                return False
                
        except Exception as e:
            self._logger.error("Error checking maximum probe interval: %s", e)
            # Conservative: don't force probe on error
            return False
    
    def _enforce_minimum_interval(self) -> bool:
        """Check if minimum probe interval has been met.
        
        Block probe if less than profile-configured minimum interval has passed
        since the last probe to allow system recovery time.
        
        Returns:
            True if minimum interval met and probe can proceed
        """
        try:
            # Get the last probe time from ThermalManager
            last_probe_time = self._get_last_probe_time()
            
            if last_probe_time is None:
                # Never probed before - allow probe
                self._logger.debug("No previous probe found, minimum interval requirement met")
                return True
            
            # Get minimum interval from profile configuration
            min_interval = timedelta(hours=self._profile_config.min_probe_interval_hours)
            
            # Calculate time since last probe
            current_time = datetime.now()
            time_since_last = current_time - last_probe_time
            
            if time_since_last >= min_interval:
                self._logger.debug(
                    "Minimum probe interval met: %.1f hours since last probe (minimum: %.1f hours)",
                    time_since_last.total_seconds() / 3600,
                    min_interval.total_seconds() / 3600
                )
                return True
            else:
                hours_remaining = (min_interval - time_since_last).total_seconds() / 3600
                self._logger.debug(
                    "Minimum interval not met, %.1f hours remaining until next probe allowed",
                    hours_remaining
                )
                return False
                
        except Exception as e:
            self._logger.error("Error checking minimum probe interval: %s", e)
            # Conservative: allow probe on error
            return True
    
    def _get_last_probe_time(self) -> Optional[datetime]:
        """Get the timestamp of the last probe from ThermalManager.
        
        Searches through hass.data to find ThermalManager instances and
        returns the most recent probe time.
        
        Returns:
            Datetime of last probe, or None if no probe history found
        """
        try:
            # Access thermal components via hass.data
            if not hasattr(self._hass, 'data') or not self._hass.data:
                self._logger.debug("No hass.data available for probe time lookup")
                return None
            
            domain_data = self._hass.data.get('smart_climate', {})
            if not domain_data:
                self._logger.debug("No smart_climate data found in hass.data")
                return None
            
            # Search through all config entries for ThermalManager instances
            for entry_id, entry_data in domain_data.items():
                thermal_components = entry_data.get('thermal_components', {})
                
                for entity_id, components in thermal_components.items():
                    thermal_manager = components.get('thermal_manager')
                    if thermal_manager and hasattr(thermal_manager, '_last_probe_time'):
                        last_probe_time = thermal_manager._last_probe_time
                        # Validate that it's actually a datetime object, not a Mock
                        if last_probe_time and isinstance(last_probe_time, datetime):
                            self._logger.debug(
                                "Found last probe time from ThermalManager: %s",
                                last_probe_time.isoformat()
                            )
                            return last_probe_time
            
            self._logger.debug("No ThermalManager with probe history found")
            return None
            
        except Exception as e:
            self._logger.error("Error retrieving last probe time: %s", e)
            return None

    def _get_current_outdoor_temperature(self) -> Optional[float]:
        """Get current outdoor temperature from weather entity.
        
        Returns:
            Current outdoor temperature in °C, or None if unavailable
        """
        try:
            if not self._weather_entity_id:
                self._logger.debug("No weather entity configured")
                return None
            
            # Get weather state from Home Assistant
            weather_state = self._hass.states.get(self._weather_entity_id)
            if not weather_state:
                self._logger.debug("Weather entity %s not found", self._weather_entity_id)
                return None
            
            # Try to get temperature from state attributes
            temperature = weather_state.attributes.get('temperature')
            if temperature is not None:
                try:
                    temp_float = float(temperature)
                    self._logger.debug("Current outdoor temperature: %.1f°C", temp_float)
                    return temp_float
                except (ValueError, TypeError):
                    self._logger.debug("Invalid temperature value: %s", temperature)
                    return None
            
            # Fallback: try to get from state value if it's numeric
            try:
                temp_float = float(weather_state.state)
                self._logger.debug("Current outdoor temperature from state: %.1f°C", temp_float)
                return temp_float
            except (ValueError, TypeError):
                self._logger.debug("No numeric temperature found in weather entity")
                return None
                
        except Exception as e:
            self._logger.error("Error retrieving outdoor temperature: %s", e)
            return None
    
    def _get_probe_history(self) -> list:
        """Get probe history from thermal model.
        
        Returns:
            List of ProbeResult objects from thermal model history
        """
        try:
            if hasattr(self._model, '_probe_history') and self._model._probe_history:
                probe_list = list(self._model._probe_history)
                self._logger.debug("Retrieved %d probes from thermal model history", len(probe_list))
                return probe_list
            else:
                self._logger.debug("No probe history available in thermal model")
                return []
                
        except Exception as e:
            self._logger.error("Error retrieving probe history: %s", e)
            return []

    
    def _calculate_information_gain(self, current_temp: float, probe_history: List) -> float:
        """Determine if probe would provide new information.
        
        Calculates information gain based on temperature bin diversity and saturation.
        Uses two factors: coverage (how many bins are covered) and saturation 
        (how many probes are in the current temperature's bin).
        
        Args:
            current_temp: Current outdoor temperature
            probe_history: List of previous ProbeResult objects
            
        Returns:
            Information gain score (0.0 to 1.0)
        """
        if not probe_history:
            return 1.0  # Maximum gain with no history
        
        current_bin = self._get_temp_bin(current_temp)
        bin_coverage = self._get_bin_coverage(probe_history)
        
        # Count probes in current bin
        probes_in_bin = sum(1 for probe in probe_history 
                           if probe.outdoor_temp is not None 
                           and self._get_temp_bin(probe.outdoor_temp) == current_bin)
        
        # Calculate gain based on coverage and bin saturation
        coverage_factor = 1.0 - bin_coverage  # Higher gain for lower coverage
        saturation_factor = 1.0 / (probes_in_bin + 1)  # Lower gain for saturated bins
        
        return min(coverage_factor + saturation_factor, 1.0)

    def _get_fallback_behavior(self) -> bool:
        """Conservative fallback when all sensors unavailable.
        
        Returns:
            True only when maximum interval exceeded, otherwise very conservative
        """
        # Force probe if maximum interval exceeded
        if self._check_maximum_interval_exceeded():
            return True
            
        # Block during quiet hours
        if self._is_quiet_hours():
            return False
            
        # Otherwise very conservative - no probe unless forced
        return False

    def _handle_sensor_errors(self, error: Exception, context: str) -> None:
        """Handle sensor reading errors gracefully.
        
        Args:
            error: The exception that occurred
            context: Context string describing where the error occurred
        """
        # Log errors appropriately, don't crash system
        self._logger.warning(
            f"Sensor error in {context}: {str(error)} - ProbeScheduler continuing with degraded capability"
        )

    def _validate_configuration(self) -> bool:
        """Validate that ProbeScheduler has minimum required configuration.
        
        Returns:
            True if configuration allows system to function, False if critical issues
        """
        # Check if thermal_model is available (required)
        if not self._model:
            self._logger.error("ProbeScheduler: thermal_model is required but not available")
            return False
            
        # Warn about missing optional sensors
        missing_sensors = []
        if not self._presence_entity_id:
            missing_sensors.append("presence sensor")
        if not self._weather_entity_id:
            missing_sensors.append("weather sensor")
        if not self._calendar_entity_id:
            missing_sensors.append("calendar integration")
        if not self._manual_override_entity_id:
            missing_sensors.append("manual override")
            
        if missing_sensors:
            self._logger.warning(
                f"ProbeScheduler: Optional sensors not configured: {', '.join(missing_sensors)}. "
                f"System will use fallback behavior only."
            )
            
        # Validate entity ID format for configured entities
        entity_ids_to_check = [
            ("presence", self._presence_entity_id),
            ("weather", self._weather_entity_id), 
            ("calendar", self._calendar_entity_id),
            ("manual_override", self._manual_override_entity_id)
        ]
        
        for sensor_type, entity_id in entity_ids_to_check:
            if entity_id and not self._is_valid_entity_id(entity_id):
                self._logger.error(
                    f"ProbeScheduler: Invalid entity ID format for {sensor_type}: {entity_id}"
                )
                # Continue functioning but log error
                
        return True

    def _check_maximum_interval_exceeded(self) -> bool:
        """Check if maximum probe interval has been exceeded.
        
        Force probe if more than profile-configured maximum interval has passed
        since the last probe, regardless of other conditions.
        
        Returns:
            True if maximum interval exceeded and probe should be forced
        """
        try:
            # Get the last probe time from ThermalManager
            last_probe_time = self._get_last_probe_time()
            
            if last_probe_time is None:
                # Never probed before - don't force probe
                self._logger.debug("No previous probe found, not forcing based on maximum interval")
                return False
            
            # Get maximum interval from profile configuration
            max_interval = timedelta(days=self._profile_config.max_probe_interval_days)
            
            # Calculate time since last probe
            current_time = datetime.now()
            time_since_last = current_time - last_probe_time
            
            if time_since_last >= max_interval:
                self._logger.info(
                    "Maximum probe interval exceeded: %.1f days since last probe (limit: %.1f days)",
                    time_since_last.total_seconds() / 86400,
                    max_interval.total_seconds() / 86400
                )
                return True
            else:
                days_remaining = (max_interval - time_since_last).total_seconds() / 86400
                self._logger.debug(
                    "Maximum interval not exceeded, %.1f days remaining until forced probe",
                    days_remaining
                )
                return False
                
        except Exception as e:
            self._logger.error("Error checking maximum probe interval: %s", e)
            # Conservative: don't force probe on error
            return False
        
    def _is_valid_entity_id(self, entity_id: str) -> bool:
        """Validate entity ID format.
        
        Args:
            entity_id: Entity ID to validate
            
        Returns:
            True if entity ID has valid format (domain.entity)
        """
        if not entity_id or not isinstance(entity_id, str):
            return False
            
        # Basic validation: should contain exactly one dot separating domain and entity
        parts = entity_id.split(".")
        if len(parts) != 2:
            return False
            
        domain, entity = parts
        if not domain or not entity:
            return False
            
        return True

    def check_abort_conditions(self) -> Tuple[bool, str]:
        """Check if probe should be aborted due to external conditions.
        
        Monitors for abort triggers:
        - User returns home (presence entity change)
        - Manual climate adjustment (target temperature change)
        - Outdoor temperature change >5°C
        - HVAC fault detection
        
        Returns:
            Tuple of (should_abort: bool, reason: str)
        """
        try:
            # Check if user returned home (presence entity change)
            if self._presence_entity_id:
                presence_state = self._hass.states.get(self._presence_entity_id)
                if presence_state and presence_state.state == "on":
                    _LOGGER.info("Probe abort: User returned home")
                    return True, "User returned home"
            
            # Check for outdoor temperature change >5°C
            current_outdoor = self._get_current_outdoor_temperature()
            if (current_outdoor is not None and 
                hasattr(self, '_probe_start_outdoor_temp') and 
                self._probe_start_outdoor_temp is not None):
                
                temp_delta = abs(current_outdoor - self._probe_start_outdoor_temp)
                if temp_delta > 5.0:
                    _LOGGER.info(f"Probe abort: Outdoor temperature changed {temp_delta:.1f}°C")
                    return True, f"Outdoor temperature changed {temp_delta:.1f}°C"
            
            # Check for manual climate adjustment (target temperature change)
            if (hasattr(self, '_probe_start_target_temp') and 
                self._probe_start_target_temp is not None and
                hasattr(self, '_wrapped_entity_id') and 
                self._wrapped_entity_id is not None):
                
                current_target = self._get_current_target_temperature()
                if (current_target is not None and 
                    abs(current_target - self._probe_start_target_temp) > 0.5):
                    _LOGGER.info("Probe abort: Manual climate adjustment detected")
                    return True, "Manual climate adjustment detected"
            
            # Check for HVAC fault (entity unavailable or error state)
            if (hasattr(self, '_wrapped_entity_id') and 
                self._wrapped_entity_id is not None):
                
                hvac_state = self._hass.states.get(self._wrapped_entity_id)
                if hvac_state and hvac_state.state in ["unavailable", "unknown"]:
                    _LOGGER.warning("Probe abort: HVAC system fault detected")
                    return True, "HVAC system fault detected"
            
            # No abort conditions detected
            return False, ""
            
        except Exception as e:
            _LOGGER.error(f"Error checking abort conditions: {e}")
            return False, ""
    
    def _get_current_target_temperature(self) -> Optional[float]:
        """Get current target temperature from wrapped HVAC entity.
        
        Returns:
            Current target temperature in °C, or None if unavailable
        """
        try:
            if not hasattr(self, '_wrapped_entity_id') or self._wrapped_entity_id is None:
                return None
                
            hvac_state = self._hass.states.get(self._wrapped_entity_id)
            if not hvac_state:
                return None
                
            target_temp = hvac_state.attributes.get("temperature")
            if target_temp is not None:
                return float(target_temp)
                
            return None
            
        except (ValueError, TypeError) as e:
            _LOGGER.warning(f"Error getting current target temperature: {e}")
            return None
    
    def handle_partial_probe_data(
        self, 
        probe_duration_minutes: int,
        tau_measured: float, 
        fit_quality: float,
        abort_reason: str
    ) -> Optional[ProbeResult]:
        """Handle partial data from aborted probe.
        
        Saves probe data if duration is sufficient (>= 15 minutes),
        applies confidence reduction for aborted probes.
        
        Args:
            probe_duration_minutes: Duration probe was running (minutes)
            tau_measured: Measured thermal time constant (minutes)
            fit_quality: Quality of exponential fit (0.0-1.0)
            abort_reason: Reason probe was aborted
            
        Returns:
            ProbeResult if data is useful, None if duration too short
        """
        try:
            # Minimum duration check - discard if too short
            if probe_duration_minutes < 15:
                _LOGGER.info(
                    f"Discarding partial probe data: duration {probe_duration_minutes}min < 15min threshold"
                )
                return None
            
            # Apply confidence reduction for aborted probes (30% reduction)
            base_confidence = fit_quality
            reduced_confidence = base_confidence * 0.7
            
            _LOGGER.info(
                f"Saving partial probe data: {probe_duration_minutes}min duration, "
                f"confidence {base_confidence:.3f} -> {reduced_confidence:.3f}, "
                f"reason: {abort_reason}"
            )
            
            # Create ProbeResult with aborted=True and reduced confidence
            return ProbeResult(
                tau_value=tau_measured,
                confidence=reduced_confidence,
                duration=probe_duration_minutes * 60,  # Convert to seconds
                fit_quality=fit_quality,
                aborted=True,
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            _LOGGER.error(f"Error handling partial probe data: {e}")
            return None

    def _create_adaptive_bins(self, historical_temperatures: List[float], 
                             num_bins: int = 6) -> List[int]:
        """Create temperature bins based on historical outdoor temperature data.
        
        Uses percentile-based bin creation for local climate adaptation.
        Returns bin boundaries adapted to local temperature range.
        
        Args:
            historical_temperatures: List of historical outdoor temperatures
            num_bins: Number of temperature bins to create (default 6)
            
        Returns:
            List of temperature boundaries for adaptive binning
        """
        try:
            # Insufficient data fallback to static bins
            if len(historical_temperatures) < 50:
                _LOGGER.debug(
                    f"Insufficient historical data ({len(historical_temperatures)} samples), "
                    f"using static fallback bins"
                )
                return [-10, 0, 10, 20, 30]  # Static fallback from OUTDOOR_TEMP_BINS
            
            # Calculate percentiles for bin boundaries (num_bins-1 boundaries)
            percentiles = [i * (100 / (num_bins - 1)) for i in range(num_bins - 1)]
            bin_boundaries = []
            
            for percentile in percentiles:
                boundary = np.percentile(historical_temperatures, percentile)
                bin_boundaries.append(int(round(boundary)))
            
            # Ensure minimum 5°C spread between bins
            adjusted_boundaries = self._ensure_minimum_spread(bin_boundaries)
            
            _LOGGER.info(
                f"Created adaptive temperature bins from {len(historical_temperatures)} samples: "
                f"{adjusted_boundaries}"
            )
            
            return adjusted_boundaries
            
        except Exception as e:
            _LOGGER.error(f"Error creating adaptive temperature bins: {e}")
            # Fallback to static bins on error
            return [-10, 0, 10, 20, 30]
    
    def _ensure_minimum_spread(self, bin_boundaries: List[int]) -> List[int]:
        """Ensure minimum 5°C spread between temperature bin boundaries.
        
        Args:
            bin_boundaries: Original percentile-based boundaries
            
        Returns:
            Adjusted boundaries with minimum spread enforced
        """
        if not bin_boundaries:
            return bin_boundaries
            
        adjusted = [bin_boundaries[0]]  # First boundary unchanged
        
        for i in range(1, len(bin_boundaries)):
            # Ensure at least 5°C gap from previous boundary
            min_boundary = adjusted[-1] + 5
            actual_boundary = bin_boundaries[i]
            
            # Use the larger of minimum spread or actual percentile
            adjusted.append(max(min_boundary, actual_boundary))
        
        return adjusted
    
    def _analyze_historical_temperatures(self) -> List[float]:
        """Analyze historical outdoor temperatures from probe history and weather.
        
        Collects outdoor temperatures from various sources:
        1. Probe history outdoor temperatures
        2. Current weather entity temperature
        3. Future: Weather service historical data (if accessible)
        4. Future: User-provided climate data
        
        Returns:
            List of historical temperatures for bin analysis
        """
        temperatures = []
        
        try:
            # Source 1: Extract outdoor temperatures from probe history
            if hasattr(self._model, '_probe_history'):
                for probe in self._model._probe_history:
                    if hasattr(probe, 'outdoor_temp') and probe.outdoor_temp is not None:
                        temperatures.append(float(probe.outdoor_temp))
                        
                _LOGGER.debug(f"Collected {len(temperatures)} temperatures from probe history")
            
            # Source 2: Add current outdoor temperature if available
            current_temp = self._get_current_outdoor_temperature()
            if current_temp is not None:
                temperatures.append(current_temp)
                _LOGGER.debug(f"Added current outdoor temperature: {current_temp}°C")
            
            # TODO: Future sources
            # - Weather service historical data (if accessible via API)
            # - User-configured climate data from config entry options
            
            _LOGGER.info(f"Analyzed {len(temperatures)} historical temperatures for adaptive binning")
            return temperatures
            
        except Exception as e:
            _LOGGER.error(f"Error analyzing historical temperatures: {e}")
            return []
    
    def _update_temperature_bins(self) -> None:
        """Update temperature bins based on current historical data.
        
        Refreshes adaptive bins based on latest temperature data.
        Falls back to static bins if insufficient data available.
        """
        try:
            # Analyze historical temperature data
            historical_temps = self._analyze_historical_temperatures()
            
            # Create adaptive bins if sufficient data
            if len(historical_temps) >= 50:
                self._adaptive_bins = self._create_adaptive_bins(historical_temps)
                _LOGGER.info(
                    f"Updated adaptive temperature bins: {self._adaptive_bins} "
                    f"(based on {len(historical_temps)} samples)"
                )
            else:
                # Clear adaptive bins to trigger static fallback
                self._adaptive_bins = None
                _LOGGER.info(
                    f"Insufficient data for adaptive binning ({len(historical_temps)} samples), "
                    f"using static fallback"
                )
                
        except Exception as e:
            _LOGGER.error(f"Error updating temperature bins: {e}")
            # Clear adaptive bins on error to ensure fallback
            self._adaptive_bins = None
    
    def _get_effective_temperature_bins(self) -> List[int]:
        """Get currently effective temperature bins (profile-specific or adaptive).
        
        Returns the temperature bin boundaries currently being used,
        either adaptive bins (if available) or profile-specific bins.
        
        Returns:
            List of temperature boundaries for current binning system
        """
        # Use adaptive bins if available and valid
        if (hasattr(self, '_adaptive_bins') and 
            self._adaptive_bins is not None and 
            len(self._adaptive_bins) >= 3):  # Minimum meaningful bins
            return self._adaptive_bins
        
        # Fallback to profile-specific bins
        return list(self._profile_config.outdoor_temp_bins)

    def _get_profile_config(self, profile: LearningProfile) -> ProfileConfig:
        """Get configuration for specified learning profile.
        
        Args:
            profile: Learning profile to get configuration for
            
        Returns:
            ProfileConfig: Configuration parameters for the profile
        """
        if profile == LearningProfile.COMFORT:
            return ProfileConfig(
                min_probe_interval_hours=24,  # Less disruptive
                max_probe_interval_days=7,
                presence_required=True,       # Must be away
                information_gain_threshold=0.6,  # Higher threshold
                quiet_hours_enabled=True,
                outdoor_temp_bins=[-10, 0, 10, 20, 30]  # Standard
            )
        elif profile == LearningProfile.BALANCED:
            return ProfileConfig(
                min_probe_interval_hours=12,  # Architectural default
                max_probe_interval_days=7,
                presence_required=True,       # Opportunistic
                information_gain_threshold=0.5,  # Standard
                quiet_hours_enabled=True,
                outdoor_temp_bins=[-10, 0, 10, 20, 30]  # Standard
            )
        elif profile == LearningProfile.AGGRESSIVE:
            return ProfileConfig(
                min_probe_interval_hours=6,   # Faster learning
                max_probe_interval_days=3,    # Force more frequently
                presence_required=False,      # May ignore presence
                information_gain_threshold=0.3,  # Lower threshold
                quiet_hours_enabled=True,     # Respect sleep
                outdoor_temp_bins=[-15, -5, 5, 15, 25, 35]  # Finer resolution
            )
        elif profile == LearningProfile.CUSTOM:
            # Custom profile with reasonable defaults that can be overridden
            return ProfileConfig(
                min_probe_interval_hours=12,  # Default to balanced
                max_probe_interval_days=7,
                presence_required=True,
                information_gain_threshold=0.5,
                quiet_hours_enabled=True,
                outdoor_temp_bins=[-10, 0, 10, 20, 30]
            )
        else:
            # Fallback to balanced
            self._logger.warning("Unknown profile %s, falling back to BALANCED", profile)
            return self._get_profile_config(LearningProfile.BALANCED)
    
    def _update_profile(self, new_profile: LearningProfile) -> None:
        """Update learning profile and reconfigure parameters.
        
        Args:
            new_profile: New learning profile to switch to
        """
        self._logger.info("Switching learning profile from %s to %s", 
                         self._learning_profile.value, new_profile.value)
        
        self._learning_profile = new_profile
        self._profile_config = self._get_profile_config(new_profile)
        
        self._logger.debug("Profile updated - min_interval=%dh, max_interval=%dd, presence_req=%s, threshold=%.1f",
                          self._profile_config.min_probe_interval_hours,
                          self._profile_config.max_probe_interval_days,
                          self._profile_config.presence_required,
                          self._profile_config.information_gain_threshold)

    def apply_advanced_settings(self, settings: AdvancedSettings) -> None:
        """Apply advanced settings to ProbeScheduler."""
        # Validate settings before applying
        is_valid, errors = validate_advanced_settings(settings)
        if not is_valid:
            error_msg = "Invalid advanced settings: " + "; ".join(errors)
            raise ValueError(error_msg)
        
        # Update internal configuration from advanced settings
        self._min_probe_interval = timedelta(hours=settings.min_probe_interval_hours)
        self._max_probe_interval = timedelta(days=settings.max_probe_interval_days)
        self._quiet_hours_start = settings.quiet_hours_start
        self._quiet_hours_end = settings.quiet_hours_end
        self._information_gain_threshold = settings.information_gain_threshold
        self._temperature_bins = settings.temperature_bins.copy()  # Copy to avoid shared references
        self._presence_override_enabled = settings.presence_override_enabled
        self._outdoor_temp_change_threshold = settings.outdoor_temp_change_threshold
        self._min_probe_duration_minutes = settings.min_probe_duration_minutes
        
        self._logger.info(
            "Applied advanced settings: min_interval=%sh, max_interval=%sd, "
            "gain_threshold=%.2f, temp_bins=%s, presence_override=%s",
            settings.min_probe_interval_hours,
            settings.max_probe_interval_days,
            settings.information_gain_threshold,
            settings.temperature_bins,
            settings.presence_override_enabled
        )
