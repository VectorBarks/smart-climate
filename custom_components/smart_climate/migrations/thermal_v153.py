"""Thermal data migration for v1.5.3 - Handle transition from 5-probe to 75-probe history."""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from ..thermal_model import ProbeResult

_LOGGER = logging.getLogger(__name__)


def migrate_probe_data(probe_data_list: List[Dict[str, Any]]) -> List[ProbeResult]:
    """
    Migrate probe data from legacy format to v1.5.3 format.
    
    This function handles the transition from v1.5.2 (5 probes, no outdoor_temp) 
    to v1.5.3 (75 probes, with outdoor_temp field).
    
    Legacy probes (v1.5.2):
    - No outdoor_temp field
    - Limited to 5 probes
    
    v1.5.3 enhancements:
    - outdoor_temp field (Optional[float]) 
    - Support for up to 75 probes
    - Backward compatibility with legacy data
    
    Args:
        probe_data_list: List of probe dictionaries from persistence data
        
    Returns:
        List of ProbeResult objects with proper v1.5.3 format
        
    Raises:
        ValueError: If probe data is severely corrupted
    """
    if not probe_data_list:
        return []
    
    migrated_probes = []
    
    for probe_dict in probe_data_list:
        try:
            # Validate basic probe structure
            if not isinstance(probe_dict, dict):
                _LOGGER.debug("Skipping non-dict probe data: %s", type(probe_dict))
                continue
                
            required_fields = ["tau_value", "confidence", "duration", "fit_quality", "aborted"]
            if not all(field in probe_dict for field in required_fields):
                _LOGGER.debug("Skipping probe with missing required fields: %s", 
                             list(probe_dict.keys()))
                continue
            
            # Validate field types and ranges
            tau_value = probe_dict["tau_value"]
            confidence = probe_dict["confidence"] 
            duration = probe_dict["duration"]
            fit_quality = probe_dict["fit_quality"]
            aborted = probe_dict["aborted"]
            
            if not isinstance(tau_value, (int, float)) or tau_value <= 0:
                _LOGGER.debug("Invalid tau_value: %s", tau_value)
                continue
                
            if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
                _LOGGER.debug("Invalid confidence: %s", confidence)
                continue
                
            if not isinstance(duration, (int, float)) or duration <= 0:
                _LOGGER.debug("Invalid duration: %s", duration)
                continue
                
            if not isinstance(fit_quality, (int, float)) or not (0.0 <= fit_quality <= 1.0):
                _LOGGER.debug("Invalid fit_quality: %s", fit_quality)
                continue
                
            if not isinstance(aborted, bool):
                _LOGGER.debug("Invalid aborted flag: %s", aborted)
                continue
            
            # Handle timestamp - parse or use fallback for legacy data
            timestamp = None
            if "timestamp" in probe_dict and probe_dict["timestamp"]:
                try:
                    timestamp = datetime.fromisoformat(probe_dict["timestamp"])
                except (ValueError, TypeError) as e:
                    _LOGGER.debug("Invalid timestamp '%s', using current time: %s", 
                                 probe_dict["timestamp"], e)
                    timestamp = datetime.now(timezone.utc)
            else:
                # Legacy data without timestamp - use current time
                timestamp = datetime.now(timezone.utc)
            
            # Handle outdoor_temp - key v1.5.3 enhancement
            outdoor_temp = None
            if "outdoor_temp" in probe_dict:
                outdoor_temp_value = probe_dict["outdoor_temp"]
                if isinstance(outdoor_temp_value, (int, float)):
                    outdoor_temp = float(outdoor_temp_value)
                elif outdoor_temp_value is not None:
                    _LOGGER.debug("Invalid outdoor_temp type: %s", type(outdoor_temp_value))
            # If no outdoor_temp field, leave as None (legacy v1.5.2 behavior)
            
            # Create migrated ProbeResult
            probe = ProbeResult(
                tau_value=float(tau_value),
                confidence=float(confidence),
                duration=int(duration),
                fit_quality=float(fit_quality),
                aborted=bool(aborted),
                timestamp=timestamp,
                outdoor_temp=outdoor_temp
            )
            
            migrated_probes.append(probe)
            
            _LOGGER.debug("Migrated probe: tau=%.1f, confidence=%.2f, outdoor_temp=%s", 
                         probe.tau_value, probe.confidence, 
                         "None" if probe.outdoor_temp is None else f"{probe.outdoor_temp:.1f}")
                         
        except Exception as e:
            _LOGGER.warning("Error migrating probe data, skipping: %s", e)
            continue
    
    _LOGGER.info("Successfully migrated %d/%d probes", 
                 len(migrated_probes), len(probe_data_list))
    
    return migrated_probes


def detect_data_version(thermal_data: Dict[str, Any]) -> str:
    """
    Detect thermal data version based on probe structure.
    
    Args:
        thermal_data: Complete thermal persistence data
        
    Returns:
        Version string: "v1.5.2" or "v1.5.3"
    """
    if "probe_history" not in thermal_data:
        return "v1.5.2"  # Assume legacy if no probes
    
    probe_history = thermal_data["probe_history"]
    if not isinstance(probe_history, list) or not probe_history:
        return "v1.5.2"  # Assume legacy if empty or invalid
    
    # Check first probe for outdoor_temp field
    first_probe = probe_history[0]
    if isinstance(first_probe, dict) and "outdoor_temp" in first_probe:
        return "v1.5.3"
    else:
        return "v1.5.2"


def is_migration_needed(thermal_data: Dict[str, Any]) -> bool:
    """
    Check if thermal data needs migration to v1.5.3.
    
    Args:
        thermal_data: Complete thermal persistence data
        
    Returns:
        True if migration is needed, False otherwise
    """
    version = detect_data_version(thermal_data)
    return version == "v1.5.2"


def validate_migrated_data(probe_results: List[ProbeResult]) -> bool:
    """
    Validate that migrated probe data is consistent.
    
    Args:
        probe_results: List of migrated ProbeResult objects
        
    Returns:
        True if data is valid, False otherwise
    """
    if not probe_results:
        return True  # Empty list is valid
    
    for probe in probe_results:
        # Basic validation
        if not isinstance(probe, ProbeResult):
            return False
            
        if probe.tau_value <= 0:
            return False
            
        if not (0.0 <= probe.confidence <= 1.0):
            return False
            
        if probe.duration <= 0:
            return False
            
        if not (0.0 <= probe.fit_quality <= 1.0):
            return False
            
        if not isinstance(probe.aborted, bool):
            return False
            
        if not isinstance(probe.timestamp, datetime):
            return False
            
        # outdoor_temp can be None (legacy) or float
        if probe.outdoor_temp is not None and not isinstance(probe.outdoor_temp, (int, float)):
            return False
    
    return True