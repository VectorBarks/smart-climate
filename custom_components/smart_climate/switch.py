"""Switch platform for the Smart Climate integration."""

import logging
from typing import Any, Dict

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .offset_engine import OffsetEngine

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Smart Climate switch platform from a config entry."""
    # Retrieve the OffsetEngine instances created in __init__.py
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    offset_engines = entry_data.get("offset_engines", {})
    
    # Create switches for each climate entity
    switches = []
    for entity_id, offset_engine in offset_engines.items():
        # Use config entry title plus entity ID for unique naming
        climate_name = f"{config_entry.title} ({entity_id})"
        switch = LearningSwitch(config_entry, offset_engine, climate_name, entity_id)
        switches.append(switch)
    
    if switches:
        async_add_entities(switches)
    else:
        _LOGGER.warning("No offset engines found for switch setup in entry: %s", config_entry.entry_id)


class LearningSwitch(SwitchEntity):
    """A switch to control the learning functionality of the Smart Climate system."""

    _attr_has_entity_name = True

    def __init__(
        self,
        config_entry: ConfigEntry,
        offset_engine: OffsetEngine,
        climate_name: str,
        entity_id: str,
    ) -> None:
        """Initialize the switch."""
        self._offset_engine = offset_engine
        self._entity_id = entity_id
        
        self._attr_name = "Learning"
        # Include entity ID in unique_id to ensure uniqueness across multiple entities
        safe_entity_id = entity_id.replace(".", "_")
        self._attr_unique_id = f"{config_entry.unique_id}_{safe_entity_id}_learning_switch"
        
        # This links the switch to the same device as the climate entity,
        # ensuring they are grouped together in the Home Assistant UI.
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{config_entry.unique_id}_{safe_entity_id}")},
            name=climate_name,
        )

    @property
    def icon(self) -> str:
        """Return the icon for the switch."""
        return "mdi:brain" if self.is_on else "mdi:brain-off"

    @property
    def is_on(self) -> bool:
        """Return true if the learning system is enabled."""
        return self._offset_engine.is_learning_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the learning system."""
        try:
            old_state = self._offset_engine.is_learning_enabled
            self._offset_engine.enable_learning()
            new_state = self._offset_engine.is_learning_enabled
            _LOGGER.debug("Learning enabled via switch for %s: %s -> %s", self._entity_id, old_state, new_state)
            # Trigger save to persist the learning state change
            await self._trigger_save()
        except Exception as exc:
            _LOGGER.error("Failed to enable learning for %s: %s", self._entity_id, exc)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the learning system."""
        try:
            old_state = self._offset_engine.is_learning_enabled
            self._offset_engine.disable_learning()
            new_state = self._offset_engine.is_learning_enabled
            _LOGGER.debug("Learning disabled via switch for %s: %s -> %s", self._entity_id, old_state, new_state)
            # Trigger save to persist the learning state change
            await self._trigger_save()
        except Exception as exc:
            _LOGGER.error("Failed to disable learning for %s: %s", self._entity_id, exc)

    async def _trigger_save(self) -> None:
        """Trigger save of learning data when switch state changes."""
        try:
            _LOGGER.debug("Triggering learning data save for %s", self._entity_id)
            await self._offset_engine.async_save_learning_data()
            _LOGGER.debug("Learning data saved after switch state change for %s", self._entity_id)
        except Exception as exc:
            _LOGGER.warning("Failed to save learning data for %s: %s", self._entity_id, exc)

    def _get_climate_technical_metrics(self) -> Dict[str, Any]:
        """Get technical metrics from the associated climate entity.
        
        Returns:
            Dictionary of technical metrics or empty dict if unavailable.
        """
        try:
            # Check if hass is available
            if not hasattr(self, 'hass') or self.hass is None:
                return {}
            
            # Get the climate entity state
            climate_state = self.hass.states.get(self._entity_id)
            if not climate_state:
                _LOGGER.debug("Climate entity %s not found for technical metrics", self._entity_id)
                return {}
            
            # Extract only the technical metrics we want for the switch
            technical_metrics = {}
            metrics_to_extract = [
                "prediction_latency_ms",
                "energy_efficiency_score", 
                "memory_usage_kb",
                "seasonal_pattern_count",
                "temperature_window_learned",
                "convergence_trend",
                "outlier_detection_active",
                "power_correlation_accuracy",
                "hysteresis_cycle_count"
            ]
            
            for metric in metrics_to_extract:
                if metric in climate_state.attributes:
                    value = climate_state.attributes[metric]
                    # Only include valid values (not None, not empty strings, valid types)
                    if value is not None and value != "":
                        # Basic type validation
                        if metric.endswith("_ms") or metric.endswith("_kb") or metric.endswith("_accuracy"):
                            # Should be numeric
                            try:
                                float(value)
                                technical_metrics[metric] = value
                            except (ValueError, TypeError):
                                continue
                        elif metric.endswith("_count"):
                            # Should be integer
                            try:
                                int(value)
                                technical_metrics[metric] = value
                            except (ValueError, TypeError):
                                continue
                        elif metric.endswith("_score"):
                            # Should be numeric (integer score)
                            try:
                                int(value)
                                technical_metrics[metric] = value
                            except (ValueError, TypeError):
                                continue
                        elif metric.endswith("_learned") or metric.endswith("_active"):
                            # Should be boolean
                            if isinstance(value, bool):
                                technical_metrics[metric] = value
                        elif metric == "convergence_trend":
                            # Should be string
                            if isinstance(value, str):
                                technical_metrics[metric] = value
                        else:
                            # Other metrics - include as-is if valid type
                            technical_metrics[metric] = value
            
            _LOGGER.debug("Retrieved %d technical metrics from climate entity %s", 
                         len(technical_metrics), self._entity_id)
            return technical_metrics
            
        except Exception as exc:
            _LOGGER.debug("Error getting technical metrics from climate entity %s: %s", 
                         self._entity_id, exc)
            return {}

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes of the learning system for diagnostics."""
        try:
            learning_info = self._offset_engine.get_learning_info()
            _LOGGER.debug("Retrieved learning info for switch %s: %s", self._entity_id, learning_info)
            
            # Format last sample time for display
            last_sample_display = "Never"
            last_sample_time = learning_info.get("last_sample_time")
            if last_sample_time:
                try:
                    # Parse ISO timestamp and format for display
                    from datetime import datetime
                    dt = datetime.fromisoformat(last_sample_time.replace('Z', '+00:00'))
                    last_sample_display = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    last_sample_display = str(last_sample_time)
            
            # Get save statistics from offset engine
            save_count = 0
            failed_save_count = 0
            last_save_display = "Never"
            try:
                save_count = self._offset_engine.save_count
                failed_save_count = self._offset_engine.failed_save_count
                last_save_time = self._offset_engine.last_save_time
                
                # Format last save time for display
                if last_save_time:
                    try:
                        last_save_display = last_save_time.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        last_save_display = str(last_save_time)
            except Exception:
                # If save statistics access fails, use defaults
                save_count = 0
                failed_save_count = 0
                last_save_display = "Error"
            
            # Format hysteresis thresholds
            start_threshold = learning_info.get("learned_start_threshold")
            stop_threshold = learning_info.get("learned_stop_threshold")
            temperature_window = learning_info.get("temperature_window")
            hysteresis_state = learning_info.get("hysteresis_state", "no_power_sensor")
            
            # Show "Learning..." when actively learning, otherwise "Not available"
            if hysteresis_state == "learning_hysteresis":
                start_threshold_display = f"{start_threshold:.2f}°C" if start_threshold is not None else "Learning..."
                stop_threshold_display = f"{stop_threshold:.2f}°C" if stop_threshold is not None else "Learning..."
                temperature_window_display = f"{temperature_window:.2f}°C" if temperature_window is not None else "Learning..."
            else:
                start_threshold_display = f"{start_threshold:.2f}°C" if start_threshold is not None else "Not available"
                stop_threshold_display = f"{stop_threshold:.2f}°C" if stop_threshold is not None else "Not available"
                temperature_window_display = f"{temperature_window:.2f}°C" if temperature_window is not None else "Not available"
            
            # Map hysteresis state to human-readable description
            hysteresis_state_display = {
                "learning_hysteresis": "Learning AC behavior",
                "active_phase": "AC actively cooling",
                "idle_above_start_threshold": "AC should start soon",
                "idle_below_stop_threshold": "AC recently stopped",
                "idle_stable_zone": "Temperature stable",
                "ready": "Ready",
                "disabled": "No power sensor",
                "no_power_sensor": "No power sensor",
                "error": "Error"
            }.get(hysteresis_state, hysteresis_state)
            
            # Base attributes from learning system
            base_attributes = {
                "samples_collected": learning_info.get("samples", 0),
                "learning_accuracy": learning_info.get("accuracy", 0.0),
                "confidence_level": learning_info.get("confidence", 0.0),
                "patterns_learned": learning_info.get("samples", 0),  # Use samples as patterns count
                "has_sufficient_data": learning_info.get("has_sufficient_data", False),
                "enabled": learning_info.get("enabled", False),
                "last_sample_collected": last_sample_display,
                "hysteresis_enabled": learning_info.get("hysteresis_enabled", False),
                "hysteresis_state": hysteresis_state_display,
                "learned_start_threshold": start_threshold_display,
                "learned_stop_threshold": stop_threshold_display,
                "temperature_window": temperature_window_display,
                "start_samples_collected": learning_info.get("start_samples_collected", 0),
                "stop_samples_collected": learning_info.get("stop_samples_collected", 0),
                "hysteresis_ready": learning_info.get("hysteresis_ready", False),
                "save_count": save_count,
                "failed_save_count": failed_save_count,
                "last_save_time": last_save_display
            }
            
            # Get technical metrics from climate entity
            technical_metrics = self._get_climate_technical_metrics()
            
            # Combine base attributes with technical metrics
            base_attributes.update(technical_metrics)
            
            return base_attributes
        except Exception as exc:
            _LOGGER.warning("Failed to get learning info for switch attributes: %s", exc)
            # Try to get save statistics even if learning info fails
            save_count = 0
            failed_save_count = 0
            last_save_display = "Error"
            try:
                save_count = self._offset_engine.save_count
                failed_save_count = self._offset_engine.failed_save_count
                last_save_time = self._offset_engine.last_save_time
                if last_save_time:
                    try:
                        last_save_display = last_save_time.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        last_save_display = str(last_save_time)
                else:
                    last_save_display = "Never"
            except Exception:
                # If save statistics also fail, use error defaults
                pass
            
            # Base error attributes
            error_attributes = {
                "samples_collected": 0,
                "learning_accuracy": 0.0,
                "confidence_level": 0.0,
                "patterns_learned": 0,
                "has_sufficient_data": False,
                "enabled": False,
                "last_sample_collected": "Error",
                "hysteresis_enabled": False,
                "hysteresis_state": "Error",
                "learned_start_threshold": "Not available",
                "learned_stop_threshold": "Not available",
                "temperature_window": "Not available",
                "start_samples_collected": 0,
                "stop_samples_collected": 0,
                "hysteresis_ready": False,
                "save_count": save_count,
                "failed_save_count": failed_save_count,
                "last_save_time": last_save_display,
                "error": str(exc)
            }
            
            # Try to get technical metrics even if learning info failed
            try:
                technical_metrics = self._get_climate_technical_metrics()
                error_attributes.update(technical_metrics)
            except Exception:
                # If technical metrics also fail, just continue with base attributes
                pass
            
            return error_attributes

    async def async_added_to_hass(self) -> None:
        """Register callbacks when the entity is added to Home Assistant."""
        # This ensures the switch state updates automatically when the
        # learning state changes from any source.
        try:
            _LOGGER.debug("Setting up learning switch %s callbacks", self._entity_id)
            unregister_callback = self._offset_engine.register_update_callback(self._handle_update)
            self.async_on_remove(unregister_callback)
            _LOGGER.debug("Registered update callback for learning switch %s", self._entity_id)
        except Exception as exc:
            _LOGGER.warning("Failed to register update callback for %s: %s", self._entity_id, exc)

    @callback
    def _handle_update(self) -> None:
        """Handle updates from the OffsetEngine and schedule a state update."""
        try:
            current_state = self._offset_engine.is_learning_enabled
            _LOGGER.debug("Learning switch %s state update triggered: is_on=%s", self._entity_id, current_state)
            self.async_write_ha_state()
            _LOGGER.debug("Learning switch %s state updated in HA", self._entity_id)
        except Exception as exc:
            _LOGGER.warning("Failed to update switch state for %s: %s", self._entity_id, exc)