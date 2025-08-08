"""ABOUTME: Thermal data migration and validation for Smart Climate Control.
ABOUTME: Handles v1.0→v2.1 migration, field validation with recovery hierarchy, and corruption handling."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

from .thermal_models import ThermalState

_LOGGER = logging.getLogger(__name__)


class ThermalDataMigrator:
    """Migrates and validates thermal persistence data.
    
    Handles migration from v1.0 to v2.1 format and validates thermal data
    with comprehensive recovery mechanisms per c_architecture.md §10.3.2 and §10.4.
    """
    
    def __init__(self):
        """Initialize migrator with validation ranges per c_architecture.md §10.4.1."""
        # Validation ranges from architecture specification
        self._tau_min = 1.0    # 1 minute minimum
        self._tau_max = 1000.0 # 1000 minutes maximum
        self._confidence_min = 0.0
        self._confidence_max = 1.0
        self._fit_quality_min = 0.0
        self._fit_quality_max = 1.0
        
        # Valid ThermalState enum values (both uppercase and lowercase)
        self._valid_thermal_states = {state.value for state in ThermalState}
        # Also accept uppercase versions for backward compatibility
        self._valid_thermal_states.update({state.name for state in ThermalState})
        
        # Default values for recovery per §10.4.2
        self._default_tau_cooling = 90.0
        self._default_tau_warming = 150.0
        self._default_confidence = 0.0
        self._default_thermal_state = ThermalState.PRIMING.name
        self._default_probe_history = []
    
    def migrate_v1_to_v2(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Migrate v1.0 persistence data to v2.1 format.
        
        Migration logic per c_architecture.md §10.3.2:
        - Detect version="1.0"
        - Treat entire file as learning_data
        - Add empty thermal_data section
        - Return v2.1 structure
        
        Args:
            data: Input persistence data (v1.0 or v2.1)
            
        Returns:
            Migrated v2.1 data or None if invalid input
        """
        if not data or not isinstance(data, dict):
            return None
            
        # Check if already v2.1 format
        if data.get("version") == "2.1":
            return data
            
        # Check if v1.0 format
        if data.get("version") != "1.0":
            _LOGGER.warning(f"Unknown data version: {data.get('version')}")
            return None
            
        _LOGGER.debug("Migrating thermal data from v1.0 to v2.1")
        
        # Create v2.1 structure
        migrated_data = {
            "version": "2.1",
            "thermal_data": None  # Empty thermal_data section per spec
        }
        
        # Copy all existing fields (preserves learning_data and extra fields)
        for key, value in data.items():
            if key != "version":  # Don't copy old version
                migrated_data[key] = value
        
        return migrated_data
    
    def validate_thermal_data(self, data: Optional[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], int]:
        """Validate thermal data with field-level recovery.
        
        Validation strategy per c_architecture.md §10.4.1 and recovery hierarchy per §10.4.2:
        - Field Level: Invalid field → log debug → use default → increment recovery_count
        - Object Level: Invalid probe → discard → increment recovery_count  
        - System Level: Invalid state → default to PRIMING
        
        Args:
            data: Thermal data dictionary to validate
            
        Returns:
            Tuple of (validated_data, recovery_count)
        """
        if data is None:
            return None, 0
            
        if not isinstance(data, dict):
            return None, 0
            
        # Handle empty dict by providing full defaults
        if not data:
            data = {}
            
        recovery_count = 0
        validated_data = {}
        
        # Ensure base structure exists
        validated_data["version"] = data.get("version", "1.0")
        
        # Validate state section (System Level Recovery)
        state_section, state_recoveries = self._validate_state_section(data.get("state"))
        validated_data["state"] = state_section
        recovery_count += state_recoveries
        
        # Validate model section (Field Level Recovery)
        model_section, model_recoveries = self._validate_model_section(data.get("model"))
        validated_data["model"] = model_section
        recovery_count += model_recoveries
        
        # Validate probe_history (Object Level Recovery)
        probe_history, probe_recoveries = self._validate_probe_history(data.get("probe_history"))
        validated_data["probe_history"] = probe_history
        recovery_count += probe_recoveries
        
        # Validate confidence (Field Level Recovery)
        confidence, confidence_recoveries = self._validate_confidence(data.get("confidence"))
        validated_data["confidence"] = confidence
        recovery_count += confidence_recoveries
        
        # Validate metadata section
        metadata_section, metadata_recoveries = self._validate_metadata_section(data.get("metadata"))
        validated_data["metadata"] = metadata_section
        recovery_count += metadata_recoveries
        
        # Log summary if any recoveries occurred
        if recovery_count > 0:
            _LOGGER.warning(f"Thermal data validation required {recovery_count} field recoveries")
            
        return validated_data, recovery_count
    
    def _validate_state_section(self, state_data: Any) -> Tuple[Dict[str, Any], int]:
        """Validate thermal state section with system-level recovery."""
        recovery_count = 0
        
        if not isinstance(state_data, dict):
            _LOGGER.debug("Invalid state section, using default PRIMING state")
            return {
                "current_state": self._default_thermal_state,
                "last_transition": self._get_current_timestamp()
            }, 1
            
        current_state = state_data.get("current_state")
        if current_state not in self._valid_thermal_states:
            _LOGGER.debug(f"Invalid thermal state '{current_state}', defaulting to PRIMING")
            current_state = self._default_thermal_state
            recovery_count += 1
            
        # Validate timestamp format (basic check)
        last_transition = state_data.get("last_transition")
        if not self._is_valid_timestamp(last_transition):
            _LOGGER.debug("Invalid last_transition timestamp, using current time")
            last_transition = self._get_current_timestamp()
            recovery_count += 1
            
        return {
            "current_state": current_state,
            "last_transition": last_transition
        }, recovery_count
    
    def _validate_model_section(self, model_data: Any) -> Tuple[Dict[str, Any], int]:
        """Validate thermal model section with field-level recovery.""" 
        recovery_count = 0
        
        if not isinstance(model_data, dict):
            _LOGGER.debug("Invalid model section, using defaults")
            return {
                "tau_cooling": self._default_tau_cooling,
                "tau_warming": self._default_tau_warming,
                "last_modified": self._get_current_timestamp()
            }, 2
            
        # Validate tau_cooling
        tau_cooling = model_data.get("tau_cooling")
        if not self._is_valid_tau_value(tau_cooling):
            _LOGGER.debug(f"Invalid tau_cooling value '{tau_cooling}', using default {self._default_tau_cooling}")
            tau_cooling = self._default_tau_cooling
            recovery_count += 1
            
        # Validate tau_warming
        tau_warming = model_data.get("tau_warming")
        if not self._is_valid_tau_value(tau_warming):
            _LOGGER.debug(f"Invalid tau_warming value '{tau_warming}', using default {self._default_tau_warming}")
            tau_warming = self._default_tau_warming
            recovery_count += 1
            
        # Validate timestamp
        last_modified = model_data.get("last_modified")
        if not self._is_valid_timestamp(last_modified):
            _LOGGER.debug("Invalid last_modified timestamp, using current time")
            last_modified = self._get_current_timestamp()
            recovery_count += 1
            
        return {
            "tau_cooling": tau_cooling,
            "tau_warming": tau_warming,
            "last_modified": last_modified
        }, recovery_count
    
    def _validate_probe_history(self, probe_history: Any) -> Tuple[List[Dict[str, Any]], int]:
        """Validate probe history with object-level recovery."""
        recovery_count = 0
        
        if not isinstance(probe_history, list):
            _LOGGER.debug("Invalid probe_history (not a list), using empty history")
            return self._default_probe_history, 1 if probe_history is not None else 0
            
        validated_probes = []
        
        for i, probe in enumerate(probe_history):
            if self._is_valid_probe_result(probe):
                validated_probes.append(probe)
            else:
                _LOGGER.debug(f"Discarding invalid probe at index {i}")
                recovery_count += 1
                
        # Limit to maximum 5 probes per specification
        if len(validated_probes) > 5:
            _LOGGER.debug(f"Truncating probe history from {len(validated_probes)} to 5 probes")
            validated_probes = validated_probes[:5]
            
        return validated_probes, recovery_count
    
    def _validate_confidence(self, confidence: Any) -> Tuple[float, int]:
        """Validate confidence value with field-level recovery."""
        if self._is_valid_confidence_value(confidence):
            return confidence, 0
            
        _LOGGER.debug(f"Invalid confidence value '{confidence}', using default {self._default_confidence}")
        return self._default_confidence, 1
    
    def _validate_metadata_section(self, metadata: Any) -> Tuple[Dict[str, Any], int]:
        """Validate metadata section."""
        if not isinstance(metadata, dict):
            _LOGGER.debug("Invalid metadata section, using defaults")
            return {
                "saves_count": 0,
                "corruption_recoveries": 0,
                "schema_version": "1.0"
            }, 1 if metadata is not None else 0
            
        # Use existing values or defaults
        return {
            "saves_count": metadata.get("saves_count", 0),
            "corruption_recoveries": metadata.get("corruption_recoveries", 0),
            "schema_version": metadata.get("schema_version", "1.0")
        }, 0
    
    def _is_valid_tau_value(self, value: Any) -> bool:
        """Check if tau value is valid (1-1000 minutes)."""
        try:
            if not isinstance(value, (int, float)):
                return False
            return self._tau_min <= float(value) <= self._tau_max
        except (ValueError, TypeError):
            return False
    
    def _is_valid_confidence_value(self, value: Any) -> bool:
        """Check if confidence value is valid (0.0-1.0)."""
        try:
            if not isinstance(value, (int, float)):
                return False
            return self._confidence_min <= float(value) <= self._confidence_max
        except (ValueError, TypeError):
            return False
    
    def _is_valid_probe_result(self, probe: Any) -> bool:
        """Check if ProbeResult is valid per §10.4.1."""
        if not isinstance(probe, dict):
            return False
            
        # Check required fields exist
        required_fields = ["tau_value", "confidence", "duration", "fit_quality", "aborted", "timestamp"]
        if not all(field in probe for field in required_fields):
            return False
            
        # Validate tau_value
        if not self._is_valid_tau_value(probe["tau_value"]):
            return False
            
        # Validate confidence (0.0-1.0)
        if not self._is_valid_confidence_value(probe["confidence"]):
            return False
            
        # Validate duration (> 0)
        try:
            duration = probe["duration"]
            if not isinstance(duration, (int, float)) or duration <= 0:
                return False
        except (ValueError, TypeError):
            return False
            
        # Validate fit_quality (0.0-1.0)
        try:
            fit_quality = probe["fit_quality"]
            if not isinstance(fit_quality, (int, float)):
                return False
            if not (self._fit_quality_min <= fit_quality <= self._fit_quality_max):
                return False
        except (ValueError, TypeError):
            return False
            
        # Validate aborted (boolean)
        if not isinstance(probe["aborted"], bool):
            return False
            
        # Validate timestamp
        if not self._is_valid_timestamp(probe["timestamp"]):
            return False
            
        return True
    
    def _is_valid_timestamp(self, timestamp: Any) -> bool:
        """Check if timestamp is valid ISO format and not in future."""
        if not isinstance(timestamp, str):
            return False
            
        try:
            # Handle various ISO timestamp formats
            if timestamp.endswith('Z'):
                parsed_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                parsed_time = datetime.fromisoformat(timestamp)
                
            # Check not in future (allow 1 hour tolerance for clock differences)
            current_time = datetime.now()
            if parsed_time.tzinfo:
                current_time = current_time.astimezone(parsed_time.tzinfo)
            else:
                # If timestamp has no timezone, assume local time
                current_time = current_time.replace(tzinfo=None)
                
            return parsed_time <= current_time.replace(microsecond=0) + timedelta(hours=1)
        except (ValueError, TypeError):
            return False
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now().isoformat() + "Z"