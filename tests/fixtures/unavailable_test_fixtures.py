"""ABOUTME: Test fixtures for unavailable entity handling scenarios.
Provides specialized fixtures for testing entity unavailability and recovery."""

from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Optional
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN


class MockUnavailableClimateEntity:
    """Mock climate entity that can simulate unavailable states."""
    
    def __init__(self, entity_id: str = "climate.test"):
        """Initialize mock climate entity."""
        self.entity_id = entity_id
        self._state = STATE_UNAVAILABLE
        self._attributes = {}
        self._available = False
        
    def make_available(self, hvac_mode: str = "cool", temp: float = 20.0):
        """Make the entity available with specified state."""
        self._state = hvac_mode
        self._available = True
        self._attributes = {
            "temperature": temp,
            "current_temperature": temp,
            "min_temp": 16.0,
            "max_temp": 30.0,
            "supported_features": 1,
            "hvac_modes": ["off", "cool", "heat", "auto"]
        }
        
    def make_unavailable(self):
        """Make the entity unavailable."""
        self._state = STATE_UNAVAILABLE
        self._available = False
        self._attributes = {}
        
    def to_state_mock(self):
        """Convert to a mock state object."""
        mock_state = Mock()
        mock_state.entity_id = self.entity_id
        mock_state.state = self._state
        mock_state.attributes = self._attributes.copy()
        return mock_state


class MockUnavailableSensor:
    """Mock sensor entity that can simulate unavailable states."""
    
    def __init__(self, entity_id: str = "sensor.test"):
        """Initialize mock sensor entity."""
        self.entity_id = entity_id
        self._state = STATE_UNAVAILABLE
        self._attributes = {}
        self._available = False
        
    def make_available(self, value: float = 22.0):
        """Make the sensor available with specified value."""
        self._state = str(value)
        self._available = True
        self._attributes = {
            "unit_of_measurement": "°C",
            "state_class": "measurement"
        }
        
    def make_unavailable(self):
        """Make the sensor unavailable."""
        self._state = STATE_UNAVAILABLE
        self._available = False
        self._attributes = {}
        
    def to_state_mock(self):
        """Convert to a mock state object."""
        mock_state = Mock()
        mock_state.entity_id = self.entity_id
        mock_state.state = self._state
        mock_state.attributes = self._attributes.copy()
        return mock_state


def create_mock_hass_with_unavailable_entities():
    """Create a mock Home Assistant instance with unavailable entity support."""
    mock_hass = Mock()
    mock_hass.states = Mock()
    mock_hass.services = Mock()
    mock_hass.services.async_call = AsyncMock()
    
    # State storage
    _states = {}
    
    def get_state(entity_id):
        """Get state, returning None if entity doesn't exist."""
        return _states.get(entity_id)
    
    def set_state(entity_id, state_mock):
        """Set state for an entity."""
        _states[entity_id] = state_mock
        
    def remove_state(entity_id):
        """Remove state for an entity."""
        if entity_id in _states:
            del _states[entity_id]
    
    mock_hass.states.get = get_state
    mock_hass.states._set_state = set_state
    mock_hass.states._remove_state = remove_state
    
    return mock_hass


def create_mock_offset_engine_with_protection():
    """Create a mock OffsetEngine with data protection for unavailable entities."""
    from custom_components.smart_climate.models import OffsetResult, OffsetInput
    
    mock_engine = Mock()
    
    # Track whether protection is active
    mock_engine._protection_active = False
    mock_engine._last_good_offset = 0.0
    
    def calculate_offset(input_data: OffsetInput) -> OffsetResult:
        """Calculate offset with protection logic."""
        if mock_engine._protection_active:
            # Return last good offset when protection is active
            return OffsetResult(
                offset=mock_engine._last_good_offset,
                clamped=False,
                reason="Using cached offset due to unavailable entity",
                confidence=0.5
            )
        else:
            # Normal calculation
            offset = input_data.ac_internal_temp - input_data.room_temp
            mock_engine._last_good_offset = offset
            return OffsetResult(
                offset=offset,
                clamped=False,
                reason="Normal calculation",
                confidence=0.9
            )
    
    def enable_protection():
        """Enable protection mode."""
        mock_engine._protection_active = True
        
    def disable_protection():
        """Disable protection mode."""
        mock_engine._protection_active = False
    
    mock_engine.calculate_offset = calculate_offset
    mock_engine.enable_protection = enable_protection
    mock_engine.disable_protection = disable_protection
    mock_engine.is_learning_enabled = Mock(return_value=True)
    mock_engine.record_feedback = Mock()
    mock_engine.get_learning_info = Mock(return_value={
        "samples_collected": 50,
        "confidence": 0.85,
        "accuracy": 0.92
    })
    
    # Add mock for hysteresis state
    mock_engine.get_hysteresis_state = Mock(return_value="idle_stable_zone")
    
    # Add mock for dashboard data
    mock_engine.async_get_dashboard_data = AsyncMock(return_value={
        "current_offset": 0.0,
        "learning_progress": 50,
        "current_accuracy": 85,
        "calibration_status": "completed",
        "hysteresis_state": "idle_stable_zone"
    })
    
    return mock_engine


def create_mock_sensor_manager_with_unavailable():
    """Create a mock SensorManager that can simulate unavailable sensors."""
    mock_sensor_manager = Mock()
    
    # Track sensor states
    mock_sensor_manager._room_temp_available = True
    mock_sensor_manager._outdoor_temp_available = True
    mock_sensor_manager._power_available = True
    
    def get_room_temperature():
        """Get room temperature, returning None if unavailable."""
        return 22.0 if mock_sensor_manager._room_temp_available else None
        
    def get_outdoor_temperature():
        """Get outdoor temperature, returning None if unavailable."""
        return 25.0 if mock_sensor_manager._outdoor_temp_available else None
        
    def get_power_consumption():
        """Get power consumption, returning None if unavailable."""
        return 150.0 if mock_sensor_manager._power_available else None
    
    def make_room_sensor_unavailable():
        """Make room sensor unavailable."""
        mock_sensor_manager._room_temp_available = False
        
    def make_room_sensor_available():
        """Make room sensor available."""
        mock_sensor_manager._room_temp_available = True
        
    def make_outdoor_sensor_unavailable():
        """Make outdoor sensor unavailable."""
        mock_sensor_manager._outdoor_temp_available = False
        
    def make_outdoor_sensor_available():
        """Make outdoor sensor available."""
        mock_sensor_manager._outdoor_temp_available = True
        
    def make_power_sensor_unavailable():
        """Make power sensor unavailable."""
        mock_sensor_manager._power_available = False
        
    def make_power_sensor_available():
        """Make power sensor available."""
        mock_sensor_manager._power_available = True
    
    # Assign methods
    mock_sensor_manager.get_room_temperature = get_room_temperature
    mock_sensor_manager.get_outdoor_temperature = get_outdoor_temperature
    mock_sensor_manager.get_power_consumption = get_power_consumption
    mock_sensor_manager.make_room_sensor_unavailable = make_room_sensor_unavailable
    mock_sensor_manager.make_room_sensor_available = make_room_sensor_available
    mock_sensor_manager.make_outdoor_sensor_unavailable = make_outdoor_sensor_unavailable
    mock_sensor_manager.make_outdoor_sensor_available = make_outdoor_sensor_available
    mock_sensor_manager.make_power_sensor_unavailable = make_power_sensor_unavailable
    mock_sensor_manager.make_power_sensor_available = make_power_sensor_available
    
    # Standard mock methods
    mock_sensor_manager.register_update_callback = Mock()
    mock_sensor_manager.start_listening = AsyncMock()
    mock_sensor_manager.stop_listening = AsyncMock()
    
    return mock_sensor_manager


def create_unavailable_test_scenario():
    """Create a complete test scenario for unavailable entity testing."""
    scenario = {
        "hass": create_mock_hass_with_unavailable_entities(),
        "climate_entity": MockUnavailableClimateEntity("climate.wrapped"),
        "room_sensor": MockUnavailableSensor("sensor.room"),
        "outdoor_sensor": MockUnavailableSensor("sensor.outdoor"),
        "power_sensor": MockUnavailableSensor("sensor.power"),
        "offset_engine": create_mock_offset_engine_with_protection(),
        "sensor_manager": create_mock_sensor_manager_with_unavailable()
    }
    
    # Set up initial states in hass
    scenario["hass"].states._set_state(
        "climate.wrapped",
        scenario["climate_entity"].to_state_mock()
    )
    scenario["hass"].states._set_state(
        "sensor.room",
        scenario["room_sensor"].to_state_mock()
    )
    
    return scenario