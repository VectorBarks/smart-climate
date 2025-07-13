"""Mock entities and fixtures for testing Smart Climate Control."""

from unittest.mock import Mock, AsyncMock
from typing import Optional, List
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode, ClimateEntityFeature
)
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.const import STATE_ON, STATE_OFF


class MockClimateEntity(ClimateEntity):
    """Mock climate entity for testing."""
    
    def __init__(self, entity_id: str = "climate.test"):
        """Initialize mock climate entity."""
        super().__init__()
        self.entity_id = entity_id
        self._hvac_mode = HVACMode.OFF
        self._hvac_modes = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.AUTO]
        self._target_temperature = 20.0
        self._current_temperature = 20.0
        self._supported_features = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
        self._preset_modes = ["none", "eco", "comfort"]
        self._preset_mode = "none"
        self._min_temp = 16.0
        self._max_temp = 30.0
        self._temperature_unit = "°C"
    
    @property
    def supported_features(self) -> int:
        """Return supported features."""
        return self._supported_features
    
    @property
    def hvac_mode(self) -> str:
        """Return current HVAC mode."""
        return self._hvac_mode
    
    @property
    def hvac_modes(self) -> List[str]:
        """Return available HVAC modes."""
        return self._hvac_modes
    
    @property
    def target_temperature(self) -> Optional[float]:
        """Return target temperature."""
        return self._target_temperature
    
    @property
    def current_temperature(self) -> Optional[float]:
        """Return current temperature."""
        return self._current_temperature
    
    @property
    def preset_modes(self) -> List[str]:
        """Return available preset modes."""
        return self._preset_modes
    
    @property
    def preset_mode(self) -> Optional[str]:
        """Return current preset mode."""
        return self._preset_mode
    
    @property
    def min_temp(self) -> float:
        """Return minimum temperature."""
        return self._min_temp
    
    @property
    def max_temp(self) -> float:
        """Return maximum temperature."""
        return self._max_temp
    
    @property
    def temperature_unit(self) -> str:
        """Return temperature unit."""
        return self._temperature_unit
    
    def set_hvac_mode(self, hvac_mode: str) -> None:
        """Set HVAC mode."""
        self._hvac_mode = hvac_mode
    
    def set_temperature(self, **kwargs) -> None:
        """Set target temperature."""
        if ATTR_TEMPERATURE in kwargs:
            self._target_temperature = kwargs[ATTR_TEMPERATURE]
    
    def set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        self._preset_mode = preset_mode


def create_mock_hass():
    """Create a mock Home Assistant instance."""
    mock_hass = Mock()
    
    # Create a proper state registry that stores and retrieves states
    _state_registry = {}
    
    def mock_set_state(entity_id, state_obj):
        _state_registry[entity_id] = state_obj
    
    def mock_get_state(entity_id):
        return _state_registry.get(entity_id)
    
    mock_hass.states = Mock()
    mock_hass.states.set = mock_set_state
    mock_hass.states.get = mock_get_state
    
    mock_hass.services = Mock()
    mock_hass.services.async_call = AsyncMock()
    mock_hass.async_create_task = Mock()
    mock_hass.async_write_ha_state = Mock()
    
    # Also add common async methods used by entities
    mock_hass.async_track_state_change = Mock()
    mock_hass.async_track_time_interval = Mock()
    
    return mock_hass


def create_mock_state(state: str, attributes: dict = None, entity_id: str = "test.entity"):
    """Create a mock state object."""
    mock_state = Mock()
    mock_state.entity_id = entity_id
    mock_state.state = state
    mock_state.attributes = attributes or {}
    return mock_state


def create_mock_offset_engine():
    """Create a mock OffsetEngine."""
    from custom_components.smart_climate.models import OffsetResult
    
    mock_engine = Mock()
    mock_engine.calculate_offset.return_value = OffsetResult(
        offset=0.0,
        clamped=False,
        reason="Test offset",
        confidence=1.0
    )
    
    # Configure system health analytics methods to return proper types
    mock_engine.has_outlier_detection.return_value = False
    mock_engine.is_outlier_detection_active.return_value = False
    mock_engine.get_recent_samples.return_value = []
    mock_engine.get_accuracy_history.return_value = []
    mock_engine.get_variance_history.return_value = []
    
    # Configure data store for persistence latency testing
    mock_engine.data_store = Mock()
    mock_engine.data_store.save_data = Mock()
    
    return mock_engine


def create_mock_sensor_manager():
    """Create a mock SensorManager."""
    mock_sensor_manager = Mock()
    mock_sensor_manager.get_room_temperature.return_value = 22.0
    mock_sensor_manager.get_outdoor_temperature.return_value = 25.0
    mock_sensor_manager.get_power_consumption.return_value = 150.0
    mock_sensor_manager.register_update_callback = Mock()
    mock_sensor_manager.start_listening = AsyncMock()
    mock_sensor_manager.stop_listening = AsyncMock()
    return mock_sensor_manager


def create_mock_mode_manager():
    """Create a mock ModeManager."""
    mock_mode_manager = Mock()
    mock_mode_manager.current_mode = "none"
    mock_mode_manager.set_mode = Mock()
    mock_mode_manager.get_adjustments.return_value = Mock(
        temperature_override=None,
        offset_adjustment=0.0,
        update_interval_override=None,
        boost_offset=0.0
    )
    mock_mode_manager.register_mode_change_callback = Mock()
    return mock_mode_manager


def create_mock_temperature_controller():
    """Create a mock TemperatureController."""
    mock_controller = Mock()
    mock_controller.apply_offset_and_limits.return_value = 22.0
    mock_controller.apply_gradual_adjustment.return_value = 1.0
    mock_controller.send_temperature_command = AsyncMock()
    return mock_controller


def create_mock_coordinator():
    """Create a mock SmartClimateCoordinator."""
    mock_coordinator = Mock()
    mock_coordinator.data = Mock(
        room_temp=22.0,
        outdoor_temp=25.0,
        power=150.0,
        calculated_offset=0.0,
        mode_adjustments=Mock()
    )
    mock_coordinator.async_config_entry_first_refresh = AsyncMock()
    mock_coordinator.async_request_refresh = AsyncMock()
    mock_coordinator.async_force_startup_refresh = AsyncMock()
    mock_coordinator.async_add_listener = Mock(return_value=Mock())  # Return a mock remove function
    return mock_coordinator