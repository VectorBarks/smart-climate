"""Helper utilities for dashboard integration tests."""

from unittest.mock import Mock, AsyncMock
from typing import Dict, Any, List, Optional
from datetime import datetime
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from custom_components.smart_climate.const import DOMAIN
from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.coordinator import SmartClimateCoordinator
from custom_components.smart_climate.models import SmartClimateData, ModeAdjustments


def create_mock_climate_state(
    entity_id: str = "climate.test_ac",
    state: str = "cool",
    temperature: float = 24.0,
    current_temperature: float = 25.0,
    hvac_modes: List[str] = None
) -> Mock:
    """Create a mock climate entity state."""
    if hvac_modes is None:
        hvac_modes = ["off", "cool", "heat", "auto"]
    
    mock_state = Mock()
    mock_state.entity_id = entity_id
    mock_state.state = state
    mock_state.attributes = {
        "temperature": temperature,
        "current_temperature": current_temperature,
        "hvac_modes": hvac_modes,
        "hvac_action": "cooling" if state == "cool" else "idle",
        "preset_mode": "none",
        "preset_modes": ["none", "away", "sleep", "boost"],
    }
    return mock_state


def create_mock_sensor_state(
    entity_id: str,
    state: str,
    unit: Optional[str] = None,
    device_class: Optional[str] = None
) -> Mock:
    """Create a mock sensor entity state."""
    mock_state = Mock()
    mock_state.entity_id = entity_id
    mock_state.state = state
    mock_state.attributes = {}
    
    if unit:
        mock_state.attributes["unit_of_measurement"] = unit
    if device_class:
        mock_state.attributes["device_class"] = device_class
    
    return mock_state


def setup_mock_hass_with_entities(
    climate_entities: Dict[str, Dict[str, Any]] = None,
    sensor_entities: Dict[str, str] = None
) -> HomeAssistant:
    """Set up a mock HomeAssistant with predefined entities."""
    hass = Mock(spec=HomeAssistant)
    hass.data = {DOMAIN: {}}
    hass.states = Mock()
    hass.services = Mock()
    hass.config_entries = Mock()
    
    # Default entities
    if climate_entities is None:
        climate_entities = {
            "climate.test_ac": {
                "state": "cool",
                "temperature": 24.0,
                "current_temperature": 25.0,
            }
        }
    
    if sensor_entities is None:
        sensor_entities = {
            "sensor.test_room": "23.5",
            "sensor.test_power": "850",
            "sensor.test_outdoor": "30.0",
        }
    
    # Create states dict
    states = {}
    
    # Add climate entities
    for entity_id, config in climate_entities.items():
        states[entity_id] = create_mock_climate_state(entity_id, **config)
    
    # Add sensor entities
    for entity_id, state_value in sensor_entities.items():
        states[entity_id] = create_mock_sensor_state(entity_id, state_value)
    
    # Mock state getter
    def mock_get_state(entity_id):
        return states.get(entity_id)
    
    hass.states.get = mock_get_state
    hass.states.async_all = Mock(return_value=list(states.values()))
    
    # Mock services
    hass.services.async_call = AsyncMock()
    hass.services.async_register = AsyncMock()
    
    return hass


def create_mock_offset_engine_with_learning(
    samples: int = 15,
    accuracy: float = 0.85,
    confidence: float = 0.75,
    hysteresis_enabled: bool = True,
    hysteresis_state: str = "idle_stable_zone",
    start_threshold: Optional[float] = 26.5,
    stop_threshold: Optional[float] = 24.0,
) -> OffsetEngine:
    """Create a mock offset engine with learning data."""
    engine = Mock(spec=OffsetEngine)
    engine.is_learning_enabled = True
    
    learning_info = {
        "enabled": True,
        "samples": samples,
        "accuracy": accuracy,
        "confidence": confidence,
        "has_sufficient_data": samples >= 10,
        "last_sample_time": datetime.now().isoformat(),
        "hysteresis_enabled": hysteresis_enabled,
        "hysteresis_state": hysteresis_state,
        "start_samples_collected": min(samples, 8),
        "stop_samples_collected": min(samples, 7),
        "hysteresis_ready": samples >= 5 and hysteresis_enabled,
    }
    
    if hysteresis_enabled and start_threshold and stop_threshold:
        learning_info.update({
            "learned_start_threshold": start_threshold,
            "learned_stop_threshold": stop_threshold,
            "temperature_window": abs(start_threshold - stop_threshold),
        })
    
    engine.get_learning_info = Mock(return_value=learning_info)
    
    # Mock coordinator
    mock_coordinator = Mock()
    mock_coordinator.data = Mock(calculated_offset=2.3)
    engine._coordinator = mock_coordinator
    
    return engine


def create_mock_coordinator_with_data(
    room_temp: float = 23.5,
    outdoor_temp: Optional[float] = 30.0,
    power: Optional[float] = 850.0,
    calculated_offset: float = 2.3,
    mode: str = "none"
) -> SmartClimateCoordinator:
    """Create a mock coordinator with test data."""
    coordinator = Mock(spec=SmartClimateCoordinator)
    
    # Create data object
    mode_adjustments = ModeAdjustments(
        temperature_override=None,
        offset_adjustment=0.0,
        update_interval_override=None,
        boost_offset=0.0
    )
    
    data = SmartClimateData(
        room_temp=room_temp,
        outdoor_temp=outdoor_temp,
        power=power,
        calculated_offset=calculated_offset,
        mode_adjustments=mode_adjustments
    )
    
    coordinator.data = data
    coordinator.last_update_success = True
    coordinator.async_request_refresh = AsyncMock()
    
    return coordinator


def assert_sensor_entity_ids(sensors: List[Any], base_entity_id: str) -> None:
    """Assert that sensors have correct entity IDs based on base entity."""
    expected_suffixes = [
        "offset_current",
        "learning_progress",
        "accuracy_current",
        "calibration_status",
        "hysteresis_state"
    ]
    
    sensor_types = [s._sensor_type for s in sensors]
    assert sorted(sensor_types) == sorted(expected_suffixes)
    
    # Check unique IDs contain base entity
    safe_base = base_entity_id.replace(".", "_")
    for sensor in sensors:
        assert safe_base in sensor.unique_id


def validate_dashboard_yaml_replacements(
    yaml_content: str,
    entity_id: str,
    friendly_name: str
) -> bool:
    """Validate that dashboard YAML has correct replacements."""
    # Check that placeholders are replaced
    if "REPLACE_ME_ENTITY" in yaml_content:
        return False
    if "REPLACE_ME_NAME" in yaml_content:
        return False
    
    # Check that actual values are present
    if entity_id not in yaml_content:
        return False
    if friendly_name not in yaml_content:
        return False
    
    # Check sensor entity IDs are correct
    expected_sensors = [
        f"sensor.{entity_id}_offset_current",
        f"sensor.{entity_id}_learning_progress",
        f"sensor.{entity_id}_accuracy_current",
        f"sensor.{entity_id}_calibration_status",
        f"sensor.{entity_id}_hysteresis_state",
    ]
    
    for sensor_id in expected_sensors:
        if sensor_id not in yaml_content:
            return False
    
    return True


def create_mock_config_entry_with_options(
    entry_id: str = "test_entry",
    unique_id: str = "test_unique",
    title: str = "Test Climate",
    climate_entity: str = "climate.test_ac",
    room_sensor: str = "sensor.test_room",
    **kwargs
) -> ConfigEntry:
    """Create a mock config entry with custom options."""
    entry = Mock(spec=ConfigEntry)
    entry.entry_id = entry_id
    entry.unique_id = unique_id
    entry.title = title
    
    # Default data
    data = {
        "climate_entity": climate_entity,
        "room_sensor": room_sensor,
        "max_offset": 5.0,
        "enable_learning": True,
        "update_interval": 180,
        "gradual_adjustment_rate": 0.5,
    }
    
    # Update with any additional kwargs
    data.update(kwargs)
    
    entry.data = data
    entry.options = {}
    
    return entry


async def simulate_coordinator_update(
    coordinator: SmartClimateCoordinator,
    room_temp: float,
    power: Optional[float] = None,
    offset: float = 0.0
) -> None:
    """Simulate a coordinator data update."""
    # Update the data
    coordinator.data.room_temp = room_temp
    coordinator.data.power = power
    coordinator.data.calculated_offset = offset
    
    # Trigger update callbacks if any
    if hasattr(coordinator, '_update_listeners'):
        for callback in coordinator._update_listeners:
            await callback()


def get_dashboard_sensor_states(
    hass: HomeAssistant,
    base_entity_id: str
) -> Dict[str, Any]:
    """Get all dashboard sensor states for a climate entity."""
    sensor_suffixes = [
        "offset_current",
        "learning_progress",
        "accuracy_current",
        "calibration_status",
        "hysteresis_state"
    ]
    
    states = {}
    for suffix in sensor_suffixes:
        sensor_id = f"sensor.{base_entity_id}_{suffix}"
        state = hass.states.get(sensor_id)
        if state:
            states[suffix] = {
                "state": state.state,
                "attributes": state.attributes
            }
    
    return states