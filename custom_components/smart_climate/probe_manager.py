"""ABOUTME: ProbeManager for thermal efficiency probe orchestration and learning
ABOUTME: Handles active and passive thermal probing with Home Assistant notifications"""

import uuid
import math
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from homeassistant.core import HomeAssistant
from custom_components.smart_climate.thermal_models import ProbeResult
from custom_components.smart_climate.thermal_preferences import UserPreferences
from custom_components.smart_climate.thermal_model import PassiveThermalModel

_LOGGER = logging.getLogger(__name__)


class ProbeManager:
    """
    Manages thermal efficiency probing for learning thermal constants.
    
    Supports both active (user-triggered) and passive (opportunistic) probing
    to improve thermal model accuracy and HVAC efficiency.
    
    Active probes:
    - User-triggered learning cycles
    - Home Assistant notifications with progress updates
    - Abort capability with data cleanup
    - Controlled temperature drift up to specified limits
    
    Passive probes:
    - Opportunistic learning when AC naturally off >60 minutes
    - Automatic detection of suitable conditions
    - No user interaction required
    - Stable outdoor temperature and significant drift required
    """
    
    def __init__(
        self,
        hass: HomeAssistant,
        thermal_model: PassiveThermalModel,
        preferences: UserPreferences,
        max_concurrent_probes: int = 1,
        passive_detection_enabled: bool = True
    ):
        """
        Initialize ProbeManager.
        
        Args:
            hass: Home Assistant instance
            thermal_model: Passive thermal model for tau updates
            preferences: User preferences for probe settings
            max_concurrent_probes: Maximum concurrent active probes
            passive_detection_enabled: Whether to detect passive probes
        """
        self._hass = hass
        self._thermal_model = thermal_model
        self._preferences = preferences
        self._max_concurrent_probes = max_concurrent_probes
        self._passive_detection_enabled = passive_detection_enabled
        
        # Active probe tracking
        self._active_probes: Dict[str, Dict[str, Any]] = {}
        
        _LOGGER.debug(
            "ProbeManager initialized: max_concurrent=%d, passive_enabled=%s",
            max_concurrent_probes,
            passive_detection_enabled
        )
    
    def can_start_probe(self, current_conditions: Dict[str, Any]) -> bool:
        """
        Check if conditions allow starting a new probe.
        
        Conditions required:
        - HVAC is off
        - AC has been stable (off) for at least 10 minutes
        - Thermal state is suitable (drifting)
        - No concurrent probe limit exceeded
        - All required sensor data available
        
        Args:
            current_conditions: Dict with hvac_mode, indoor_temp, outdoor_temp,
                               target_temp, ac_stable_duration, thermal_state
                               
        Returns:
            True if probe can be started, False otherwise
        """
        try:
            # Check concurrent probe limit
            if len(self._active_probes) >= self._max_concurrent_probes:
                _LOGGER.debug("Probe start blocked: concurrent limit exceeded")
                return False
            
            # Check required data availability
            required_keys = ['hvac_mode', 'indoor_temp', 'outdoor_temp', 
                           'target_temp', 'ac_stable_duration', 'thermal_state']
            for key in required_keys:
                if key not in current_conditions or current_conditions[key] is None:
                    _LOGGER.debug("Probe start blocked: missing %s", key)
                    return False
            
            # Check HVAC is off
            if current_conditions['hvac_mode'] != 'off':
                _LOGGER.debug("Probe start blocked: HVAC is running (%s)", 
                             current_conditions['hvac_mode'])
                return False
            
            # Check AC stability duration (minimum 10 minutes)
            if current_conditions['ac_stable_duration'] < 600:
                _LOGGER.debug("Probe start blocked: insufficient stability (%ds)", 
                             current_conditions['ac_stable_duration'])
                return False
            
            # Check thermal state is suitable for probing
            suitable_states = ['drifting', 'probing']
            if current_conditions['thermal_state'] not in suitable_states:
                _LOGGER.debug("Probe start blocked: unsuitable thermal state (%s)", 
                             current_conditions['thermal_state'])
                return False
            
            _LOGGER.debug("Probe start conditions satisfied")
            return True
            
        except Exception as e:
            _LOGGER.error("Error checking probe start conditions: %s", e)
            return False
    
    def start_active_probe(self, max_drift: Optional[float] = None, current_conditions: Optional[Dict[str, Any]] = None) -> str:
        """
        Start an active thermal probe with user notification.
        
        Creates a probe tracking entry, generates unique probe ID,
        and creates Home Assistant notification with progress updates
        and abort capability.
        
        Args:
            max_drift: Maximum temperature drift allowed (°C).
                      Defaults to preferences.probe_drift or 2.0°C
                      
        Returns:
            Unique probe ID string
            
        Raises:
            RuntimeError: If concurrent probe limit exceeded
        """
        # Check concurrent limit
        if len(self._active_probes) >= self._max_concurrent_probes:
            raise RuntimeError("Maximum concurrent probes exceeded")
        
        # Generate unique probe ID
        probe_id = uuid.uuid4().hex
        
        # Determine max drift - default to 2.0°C regardless of preferences
        if max_drift is None:
            max_drift = 2.0
        
        # Initialize probe data
        probe_data = {
            'probe_id': probe_id,
            'probe_type': 'active',
            'start_time': datetime.now(),
            'start_temp': None,  # Will be set when first temperature recorded
            'max_drift': max_drift,
            'temperatures': [],  # List of (timestamp, temperature) tuples
            'aborted': False,
            'completed': False,
            'outdoor_temp': current_conditions.get('outdoor_temp') if current_conditions else None
        }
        
        self._active_probes[probe_id] = probe_data
        
        # Create notification
        self.create_notification(
            title='Smart Climate Thermal Probe Active',
            message=f'Temperature drift learning in progress. Allow temperature to drift up to {max_drift}°C for accurate thermal modeling.',
            notification_id=f'smart_climate_probe_{probe_id}',
            actions=[
                {
                    'action': f'smart_climate_abort_probe_{probe_id}',
                    'title': 'Abort Probe'
                }
            ]
        )
        
        _LOGGER.info("Started active probe %s with max drift %.1f°C", probe_id, max_drift)
        return probe_id
    
    def detect_passive_probe(self, ac_state_history: List[Tuple[str, datetime, float, float]]) -> bool:
        """
        Detect if conditions are suitable for passive probe learning.
        
        Passive probe conditions:
        - AC has been off for >60 minutes
        - Outdoor temperature stable (±1°C variation)
        - Significant indoor temperature drift observed (>1°C)
        - No AC cycling during the period
        
        Args:
            ac_state_history: List of (hvac_mode, timestamp, indoor_temp, outdoor_temp)
                            tuples in chronological order
                            
        Returns:
            True if passive probe conditions detected, False otherwise
        """
        if not self._passive_detection_enabled:
            return False
        
        if len(ac_state_history) < 2:
            return False
        
        try:
            # Check duration - must be >60 minutes
            start_time = ac_state_history[0][1]
            end_time = ac_state_history[-1][1]
            duration_minutes = (end_time - start_time).total_seconds() / 60
            
            if duration_minutes < 60:
                _LOGGER.debug("Passive probe: insufficient duration (%.1f min)", duration_minutes)
                return False
            
            # Check all entries are AC off
            for hvac_mode, _, _, _ in ac_state_history:
                if hvac_mode != 'off':
                    _LOGGER.debug("Passive probe: AC cycling detected")
                    return False
            
            # Extract temperatures
            indoor_temps = [entry[2] for entry in ac_state_history]
            outdoor_temps = [entry[3] for entry in ac_state_history]
            
            # Check outdoor temperature stability (±1°C)
            outdoor_range = max(outdoor_temps) - min(outdoor_temps)
            if outdoor_range > 1.0:
                _LOGGER.debug("Passive probe: unstable outdoor temp (%.1f°C range)", outdoor_range)
                return False
            
            # Check significant indoor drift (>1°C)
            indoor_drift = abs(indoor_temps[-1] - indoor_temps[0])
            if indoor_drift < 1.0:
                _LOGGER.debug("Passive probe: insufficient drift (%.1f°C)", indoor_drift)
                return False
            
            _LOGGER.info("Passive probe conditions detected: %.1f min duration, %.1f°C drift",
                        duration_minutes, indoor_drift)
            return True
            
        except Exception as e:
            _LOGGER.error("Error detecting passive probe: %s", e)
            return False
    
    def abort_probe(self, probe_id: str) -> bool:
        """
        Abort an active probe and clean up all associated data.
        
        Removes probe from active tracking, dismisses notifications,
        and performs complete cleanup.
        
        Args:
            probe_id: Unique probe identifier
            
        Returns:
            True if probe was aborted, False if probe not found
        """
        if probe_id not in self._active_probes:
            _LOGGER.warning("Cannot abort probe %s: not found", probe_id)
            return False
        
        try:
            # Mark as aborted
            self._active_probes[probe_id]['aborted'] = True
            
            # Dismiss notification
            self._hass.services.call(
                'persistent_notification',
                'dismiss',
                service_data={
                    'notification_id': f'smart_climate_probe_{probe_id}'
                }
            )
            
            # Remove from active probes
            del self._active_probes[probe_id]
            
            _LOGGER.info("Aborted probe %s", probe_id)
            return True
            
        except Exception as e:
            _LOGGER.error("Error aborting probe %s: %s", probe_id, e)
            return False
    
    def complete_probe(self, probe_id: str) -> Optional[ProbeResult]:
        """
        Complete an active probe and calculate thermal constants.
        
        Analyzes collected temperature data, calculates thermal time
        constant, and updates the thermal model. Cleans up probe data
        and dismisses notifications.
        
        Args:
            probe_id: Unique probe identifier
            
        Returns:
            ProbeResult with calculated tau, confidence, and quality metrics,
            or None if probe not found
        """
        if probe_id not in self._active_probes:
            _LOGGER.warning("Cannot complete probe %s: not found", probe_id)
            return None
        
        try:
            probe_data = self._active_probes[probe_id]
            
            # Calculate duration
            start_time = probe_data['start_time']
            # Use last temperature timestamp if available for more accurate duration
            if probe_data['temperatures']:
                end_time = probe_data['temperatures'][-1][0]
                duration_seconds = int((end_time - start_time).total_seconds())
            else:
                duration_seconds = int((datetime.now() - start_time).total_seconds())
            
            # Calculate tau from temperature data
            if probe_data['temperatures']:
                tau_value, fit_quality = self._calculate_tau_from_temperatures(
                    probe_data['temperatures'],
                    probe_data['start_temp']
                )
            else:
                tau_value, fit_quality = 0.0, 0.0
            
            # Calculate confidence based on data quality and duration
            confidence = self._calculate_probe_confidence(
                len(probe_data['temperatures']),
                duration_seconds,
                fit_quality
            )
            
            # Create probe result with outdoor temperature
            result = ProbeResult(
                tau_value=tau_value,
                confidence=confidence,
                duration=duration_seconds,
                fit_quality=fit_quality,
                aborted=False,
                outdoor_temp=probe_data.get('outdoor_temp')
            )
            
            # Update thermal model
            if result.confidence > 0.1 and result.tau_value > 0:
                # Determine if cooling or warming based on temperature change
                is_cooling = self._determine_cooling_scenario(probe_data)
                self._thermal_model.update_tau(result, is_cooling)
                _LOGGER.info("Updated thermal model: tau=%.1f, cooling=%s, confidence=%.2f",
                           tau_value, is_cooling, confidence)
            
            # Cleanup
            self._hass.services.call(
                'persistent_notification',
                'dismiss',
                service_data={
                    'notification_id': f'smart_climate_probe_{probe_id}'
                }
            )
            
            del self._active_probes[probe_id]
            
            _LOGGER.info("Completed probe %s: tau=%.1f, confidence=%.2f", 
                        probe_id, tau_value, confidence)
            return result
            
        except Exception as e:
            _LOGGER.error("Error completing probe %s: %s", probe_id, e)
            return None
    
    def get_probe_status(self, probe_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of an active probe.
        
        Args:
            probe_id: Unique probe identifier
            
        Returns:
            Dict with probe status info, or None if probe not found
        """
        if probe_id not in self._active_probes:
            return None
        
        try:
            probe_data = self._active_probes[probe_id]
            current_time = datetime.now()
            
            # Calculate duration
            duration_seconds = int((current_time - probe_data['start_time']).total_seconds())
            
            # Calculate current drift
            current_drift = 0.0
            if probe_data['start_temp'] is not None and probe_data['temperatures']:
                current_temp = probe_data['temperatures'][-1][1]
                current_drift = round(abs(current_temp - probe_data['start_temp']), 1)
            
            # Calculate completion percentage
            completion_percentage = min(100, int(current_drift / probe_data['max_drift'] * 100))
            
            return {
                'probe_id': probe_id,
                'status': 'active',
                'duration_seconds': duration_seconds,
                'current_drift': current_drift,
                'max_drift': probe_data['max_drift'],
                'completion_percentage': completion_percentage,
                'temperature_count': len(probe_data['temperatures']),
                'start_temp': probe_data['start_temp']
            }
            
        except Exception as e:
            _LOGGER.error("Error getting probe status %s: %s", probe_id, e)
            return None
    
    def create_notification(
        self,
        title: str,
        message: str,
        notification_id: str,
        actions: Optional[List[Dict[str, str]]] = None
    ) -> None:
        """
        Create a Home Assistant persistent notification.
        
        Args:
            title: Notification title
            message: Notification message content
            notification_id: Unique notification identifier
            actions: Optional list of action buttons
        """
        service_data = {
            'notification_id': notification_id,
            'title': title,
            'message': message
        }
        
        if actions:
            service_data['data'] = {'actions': actions}
        
        self._hass.services.call(
            'persistent_notification',
            'create',
            service_data=service_data
        )
    
    def _update_probe_notification(self, probe_id: str) -> None:
        """
        Update probe notification with current progress.
        
        Args:
            probe_id: Unique probe identifier
        """
        status = self.get_probe_status(probe_id)
        if not status:
            return
        
        # Calculate estimated time remaining
        if status['completion_percentage'] > 0:
            total_estimated_duration = status['duration_seconds'] / (status['completion_percentage'] / 100)
            remaining_seconds = max(0, total_estimated_duration - status['duration_seconds'])
            remaining_minutes = int(remaining_seconds / 60)
            time_remaining = f"~{remaining_minutes} minutes"
        else:
            time_remaining = "unknown"
        
        message = (
            f"Current drift: {status['current_drift']:.1f}°C of {status['max_drift']:.1f}°C target.\n"
            f"Progress: {status['completion_percentage']}%\n"
            f"Time remaining: {time_remaining}"
        )
        
        self.create_notification(
            title='Smart Climate Thermal Probe Active',
            message=message,
            notification_id=f'smart_climate_probe_{probe_id}',
            actions=[
                {
                    'action': f'smart_climate_abort_probe_{probe_id}',
                    'title': 'Abort Probe'
                }
            ]
        )
    
    def _calculate_tau_from_temperatures(
        self,
        temperatures: List[Tuple[datetime, float]],
        start_temp: Optional[float]
    ) -> Tuple[float, float]:
        """
        Calculate thermal time constant from temperature data.
        
        Uses exponential curve fitting to determine tau value.
        
        Args:
            temperatures: List of (timestamp, temperature) tuples
            start_temp: Starting temperature
            
        Returns:
            Tuple of (tau_value, fit_quality)
        """
        if len(temperatures) < 2 or start_temp is None:
            return 0.0, 0.0
        
        try:
            # Simple tau estimation using half-life approach
            # Find time to reach halfway to target temperature
            
            target_temp = temperatures[-1][1]  # Final temperature as target
            temp_change = target_temp - start_temp
            
            if abs(temp_change) < 0.1:
                return 0.0, 0.0
            
            half_change = start_temp + (temp_change * 0.632)  # 1 - e^(-1) ≈ 0.632
            
            # Find time when temperature reached this level
            for timestamp, temp in temperatures:
                if abs(temp - half_change) < 0.2:  # Close enough
                    start_time = temperatures[0][0]
                    tau_minutes = (timestamp - start_time).total_seconds() / 60
                    
                    # Quality based on data points and consistency
                    quality = min(1.0, len(temperatures) / 10.0)  # More points = better quality
                    
                    return float(tau_minutes), quality
            
            # Fallback: estimate based on rate of change
            if len(temperatures) >= 3:
                # Use first and last points
                time_span = (temperatures[-1][0] - temperatures[0][0]).total_seconds() / 60
                temp_span = temperatures[-1][1] - temperatures[0][1]
                
                if abs(temp_span) > 0.1 and time_span > 0:
                    # Rough tau estimation
                    tau_estimate = time_span / abs(temp_span) * 60  # Scale factor
                    quality = 0.6  # Lower quality for fallback method
                    return tau_estimate, quality
            
            return 0.0, 0.0
            
        except Exception as e:
            _LOGGER.error("Error calculating tau from temperatures: %s", e)
            return 0.0, 0.0
    
    def _calculate_probe_confidence(
        self,
        temperature_count: int,
        duration_seconds: int,
        fit_quality: float
    ) -> float:
        """
        Calculate confidence level for probe result.
        
        Args:
            temperature_count: Number of temperature readings
            duration_seconds: Probe duration in seconds
            fit_quality: Quality of curve fit (0.0-1.0)
            
        Returns:
            Confidence level (0.0-1.0)
        """
        # Base confidence on data quantity
        data_confidence = min(1.0, temperature_count / 20.0)  # Ideal: 20+ readings
        
        # Duration confidence (ideal: >30 minutes)
        duration_confidence = min(1.0, duration_seconds / 1800.0)
        
        # Combined confidence
        confidence = (data_confidence * 0.4 + duration_confidence * 0.3 + fit_quality * 0.3)
        
        return max(0.0, min(1.0, confidence))
    
    def _determine_cooling_scenario(self, probe_data: Dict[str, Any]) -> bool:
        """
        Determine if probe represents cooling or warming scenario.
        
        Args:
            probe_data: Active probe data dictionary
            
        Returns:
            True if warming scenario (temperature rising), False if cooling
        """
        if not probe_data['temperatures'] or probe_data['start_temp'] is None:
            return True  # Default to warming
        
        final_temp = probe_data['temperatures'][-1][1]
        temp_change = final_temp - probe_data['start_temp']
        
        # Positive change = warming, negative change = cooling
        return temp_change > 0