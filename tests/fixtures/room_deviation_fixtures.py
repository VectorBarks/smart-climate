"""Test fixtures and utilities for room temperature deviation testing."""

from unittest.mock import Mock, AsyncMock
from typing import Optional, Dict, Any
import pytest

from custom_components.smart_climate.models import SmartClimateData, ModeAdjustments, OffsetResult
from tests.fixtures.mock_entities import (
    create_mock_hass,
    create_mock_state,
    create_mock_offset_engine,
    create_mock_sensor_manager,
    create_mock_mode_manager,
    create_mock_temperature_controller,
    create_mock_coordinator,
)


class CoordinatorDataBuilder:
    """Builder class for creating SmartClimateData with different scenarios."""
    
    def __init__(self):
        """Initialize with default values."""
        self.room_temp = 24.0
        self.outdoor_temp = 28.0
        self.power = 150.0
        self.calculated_offset = 0.0
        self.is_startup_calculation = False
        self.mode_adjustments = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        )
    
    def with_room_temp(self, temp: Optional[float]) -> 'CoordinatorDataBuilder':
        """Set the room temperature."""
        self.room_temp = temp
        return self
    
    def with_outdoor_temp(self, temp: Optional[float]) -> 'CoordinatorDataBuilder':
        """Set the outdoor temperature."""
        self.outdoor_temp = temp
        return self
    
    def with_power(self, power: Optional[float]) -> 'CoordinatorDataBuilder':
        """Set the power consumption."""
        self.power = power
        return self
    
    def with_calculated_offset(self, offset: float) -> 'CoordinatorDataBuilder':
        """Set the calculated offset."""
        self.calculated_offset = offset
        return self
    
    def with_startup_flag(self, is_startup: bool) -> 'CoordinatorDataBuilder':
        """Set the startup calculation flag."""
        self.is_startup_calculation = is_startup
        return self
    
    def with_mode_adjustments(self, adjustments: ModeAdjustments) -> 'CoordinatorDataBuilder':
        """Set the mode adjustments."""
        self.mode_adjustments = adjustments
        return self
    
    def build(self) -> SmartClimateData:
        """Build the SmartClimateData object."""
        data = SmartClimateData(
            room_temp=self.room_temp,
            outdoor_temp=self.outdoor_temp,
            power=self.power,
            calculated_offset=self.calculated_offset,
            mode_adjustments=self.mode_adjustments
        )
        # Add the startup flag if set
        if self.is_startup_calculation:
            data.is_startup_calculation = True
        return data


def create_room_deviation_scenarios():
    """Create various room temperature deviation test scenarios."""
    return [
        # (room_temp, target_temp, should_trigger, description)
        (24.0, 24.0, False, "Room at target"),
        (23.9, 24.0, False, "Room 0.1°C below target"),
        (24.1, 24.0, False, "Room 0.1°C above target"),
        (23.7, 24.0, False, "Room 0.3°C below target"),
        (24.3, 24.0, False, "Room 0.3°C above target"),
        (23.5, 24.0, False, "Room at 0.5°C threshold below"),
        (24.5, 24.0, False, "Room at 0.5°C threshold above"),
        (23.49, 24.0, True, "Room just over 0.5°C below"),
        (24.51, 24.0, True, "Room just over 0.5°C above"),
        (23.0, 24.0, True, "Room 1°C below target"),
        (25.0, 24.0, True, "Room 1°C above target"),
        (22.0, 24.0, True, "Room 2°C below target"),
        (26.0, 24.0, True, "Room 2°C above target"),
    ]


def create_combined_trigger_scenarios():
    """Create scenarios with both offset and room deviation changes."""
    return [
        # (room_temp, target_temp, offset_change, should_trigger, description)
        (24.0, 24.0, 0.0, False, "No change at all"),
        (24.0, 24.0, 0.2, False, "Small offset change only"),
        (24.0, 24.0, 0.4, True, "Large offset change only"),
        (24.3, 24.0, 0.0, False, "Small room deviation only"),
        (24.6, 24.0, 0.0, True, "Large room deviation only"),
        (24.3, 24.0, 0.2, False, "Both small changes"),
        (24.3, 24.0, 0.4, True, "Small room dev + large offset"),
        (24.6, 24.0, 0.2, True, "Large room dev + small offset"),
        (24.6, 24.0, 0.4, True, "Both large changes"),
    ]


def create_edge_case_scenarios():
    """Create edge case scenarios for room deviation testing."""
    return [
        # (room_temp, target_temp, hvac_mode, description)
        (None, 24.0, "cool", "Missing room temperature"),
        (24.0, None, "cool", "Missing target temperature"),
        (None, None, "cool", "Both temperatures missing"),
        (25.0, 24.0, "off", "HVAC is OFF"),
        (float('inf'), 24.0, "cool", "Invalid room temperature"),
        (24.0, float('inf'), "cool", "Invalid target temperature"),
        (-273.0, 24.0, "cool", "Extreme cold room temperature"),
        (100.0, 24.0, "cool", "Extreme hot room temperature"),
    ]


@pytest.fixture
def coordinator_data_builder():
    """Provide a CoordinatorDataBuilder instance."""
    return CoordinatorDataBuilder()


@pytest.fixture
def mock_climate_entity_with_room_deviation():
    """Create a mock climate entity configured for room deviation testing."""
    from custom_components.smart_climate.climate import SmartClimateEntity
    
    mock_hass = create_mock_hass()
    config = {
        "name": "Test Smart Climate",
        "feedback_delay": 45,
        "min_temperature": 16.0,
        "max_temperature": 30.0,
        "default_target_temperature": 24.0,
        "room_deviation_threshold": 0.5  # Make this configurable if needed
    }
    
    # Create mock dependencies
    mock_offset_engine = create_mock_offset_engine()
    mock_sensor_manager = create_mock_sensor_manager()
    mock_mode_manager = create_mock_mode_manager()
    mock_temperature_controller = create_mock_temperature_controller()
    mock_coordinator = create_mock_coordinator()
    
    # Configure default coordinator data
    default_data = CoordinatorDataBuilder().build()
    mock_coordinator.data = default_data
    
    entity = SmartClimateEntity(
        hass=mock_hass,
        config=config,
        wrapped_entity_id="climate.test_ac",
        room_sensor_id="sensor.room_temp",
        offset_engine=mock_offset_engine,
        sensor_manager=mock_sensor_manager,
        mode_manager=mock_mode_manager,
        temperature_controller=mock_temperature_controller,
        coordinator=mock_coordinator
    )
    
    # Set default target temperature
    entity._attr_target_temperature = 24.0
    entity._last_offset = 0.0
    
    # Mock the async methods
    entity.async_write_ha_state = Mock()
    entity.async_on_remove = Mock()
    
    return entity


def assert_temperature_update_triggered(entity, expected: bool = True):
    """Assert whether a temperature update was triggered."""
    if expected:
        entity.hass.async_create_task.assert_called_once()
        # Verify the task is for temperature adjustment
        call_args = entity.hass.async_create_task.call_args[0][0]
        assert hasattr(call_args, 'cr_frame'), "Expected a coroutine to be scheduled"
    else:
        entity.hass.async_create_task.assert_not_called()
    
    # State should always be updated
    entity.async_write_ha_state.assert_called_once()


def configure_entity_for_scenario(
    entity,
    room_temp: Optional[float],
    target_temp: Optional[float],
    offset_change: float = 0.0,
    hvac_mode: str = "cool",
    wrapped_entity_attrs: Optional[Dict[str, Any]] = None
):
    """Configure the entity for a specific test scenario."""
    # Set room temperature in coordinator data
    if hasattr(entity._coordinator.data, 'room_temp'):
        entity._coordinator.data.room_temp = room_temp
    
    # Set target temperature
    entity._attr_target_temperature = target_temp
    
    # Set offset change in coordinator data
    entity._coordinator.data.calculated_offset = entity._last_offset + offset_change
    
    # Configure wrapped entity state
    default_attrs = {
        "target_temperature": 22.0,
        "current_temperature": 23.0
    }
    if wrapped_entity_attrs:
        default_attrs.update(wrapped_entity_attrs)
    
    wrapped_state = create_mock_state(
        entity_id=entity._wrapped_entity_id,
        state=hvac_mode,
        attributes=default_attrs
    )
    entity.hass.states.get.return_value = wrapped_state
    
    # Reset mocks
    entity.hass.async_create_task.reset_mock()
    entity.async_write_ha_state.reset_mock()


def create_offset_result_for_room_deviation(
    room_temp: float,
    target_temp: float,
    base_offset: float = 0.0
) -> OffsetResult:
    """Create an OffsetResult based on room deviation from target."""
    deviation = room_temp - target_temp
    
    # Simple logic: if room is warmer, we need more cooling (negative offset)
    # if room is cooler, we need less cooling (positive offset)
    if abs(deviation) < 0.5:
        reason = "Room temperature close to target"
        offset = base_offset
    elif deviation > 0:
        reason = f"Room {deviation:.1f}°C warmer than target"
        offset = base_offset - (deviation * 0.5)  # Cool more
    else:
        reason = f"Room {abs(deviation):.1f}°C cooler than target"
        offset = base_offset + (abs(deviation) * 0.5)  # Cool less
    
    return OffsetResult(
        offset=offset,
        clamped=False,
        reason=reason,
        confidence=0.9
    )


class MockTemperatureController:
    """Enhanced mock temperature controller for room deviation tests."""
    
    def __init__(self):
        """Initialize the mock controller."""
        self.apply_offset_and_limits = Mock(return_value=22.0)
        self.send_temperature_command = AsyncMock()
        self.last_room_temp = None
        self.last_target_temp = None
        self.last_offset = None
    
    def configure_for_scenario(self, target_temp: float, offset: float, room_temp: float):
        """Configure the controller to calculate adjusted temperature."""
        # Store parameters for verification
        self.last_room_temp = room_temp
        self.last_target_temp = target_temp
        self.last_offset = offset
        
        # Calculate adjusted temperature (simplified logic)
        # If room is warmer than target, set AC lower
        # If room is cooler than target, set AC higher
        room_deviation = room_temp - target_temp
        adjusted = target_temp + offset
        
        # Additional adjustment based on room deviation
        if room_deviation > 0:
            # Room is warmer, cool more
            adjusted -= min(room_deviation * 0.3, 2.0)
        elif room_deviation < 0:
            # Room is cooler, cool less
            adjusted += min(abs(room_deviation) * 0.3, 2.0)
        
        # Clamp to reasonable limits
        adjusted = max(16.0, min(30.0, adjusted))
        
        self.apply_offset_and_limits.return_value = adjusted
        
        return adjusted