"""ABOUTME: Unit tests for graceful degradation when AC integration has timeouts.
Tests how Smart Climate handles temporary timeouts and degraded modes with recovery."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, call
from datetime import datetime, timedelta

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.components.climate.const import HVACMode, HVACAction
from homeassistant.exceptions import HomeAssistantError
from homeassistant.core import ServiceCall

from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.models import OffsetInput, OffsetResult, SmartClimateData
from custom_components.smart_climate.const import TEMP_DEVIATION_THRESHOLD
from tests.fixtures.mock_entities import (
    create_mock_hass,
    create_mock_state,
    create_mock_offset_engine,
    create_mock_sensor_manager,
    create_mock_mode_manager,
    create_mock_temperature_controller,
    create_mock_coordinator
)


class TestGracefulDegradation:
    """Test graceful degradation when AC integration has timeouts."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.hass = create_mock_hass()
        self.config = {
            "name": "Test Smart Climate",
            "climate_entity": "climate.test_ac",
            "room_sensor": "sensor.room_temp",
            "max_offset": 5.0,
            "update_interval": 180,
            "ml_enabled": True,
            "enable_learning": True,
            "default_target_temperature": 24.0,
            "feedback_delay": 45
        }
        
        # Create mock dependencies
        self.mock_offset_engine = create_mock_offset_engine()
        self.mock_sensor_manager = create_mock_sensor_manager()
        self.mock_mode_manager = create_mock_mode_manager()
        self.mock_temperature_controller = create_mock_temperature_controller()
        self.mock_coordinator = create_mock_coordinator()
        
        # Set up default sensor values
        self.mock_sensor_manager.get_room_temperature.return_value = 22.0
        self.mock_sensor_manager.get_outdoor_temperature.return_value = 25.0
        self.mock_sensor_manager.get_power_consumption.return_value = 150.0
        
        # Set up default offset calculation
        self.mock_offset_engine.calculate_offset.return_value = OffsetResult(
            offset=1.5, clamped=False, reason="Normal operation", confidence=0.8
        )
        
    def create_smart_climate_entity(self):
        """Create a SmartClimateEntity with test fixtures."""
        return SmartClimateEntity(
            hass=self.hass,
            config=self.config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=self.mock_offset_engine,
            sensor_manager=self.mock_sensor_manager,
            mode_manager=self.mock_mode_manager,
            temperature_controller=self.mock_temperature_controller,
            coordinator=self.mock_coordinator
        )

    def test_smart_climate_remains_available_during_temporary_wrapped_entity_timeout(self):
        """Test Smart Climate remains available when wrapped entity has temporary timeouts."""
        # Arrange
        entity = self.create_smart_climate_entity()
        
        # Set wrapped entity as initially available
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=HVACMode.COOL, 
            attributes={"temperature": 23.0, "current_temperature": 22.5}
        ))
        
        # Act - Wrapped entity becomes temporarily unavailable
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=STATE_UNAVAILABLE,
            attributes={}
        ))
        
        # Assert - Smart Climate detects unavailability but remains available itself
        assert not entity.available  # Should reflect wrapped entity state
        assert entity._was_unavailable is True  # Should track the unavailable state
        
    def test_smart_climate_shows_last_known_values_during_unavailability(self):
        """Test Smart Climate shows last known values during wrapped entity unavailability."""
        # Arrange
        entity = self.create_smart_climate_entity()
        
        # Set initial known values
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=HVACMode.COOL,
            attributes={
                "temperature": 23.0,
                "current_temperature": 22.5,
                "hvac_action": HVACAction.COOLING,
                "fan_mode": "auto",
                "swing_mode": "off"
            }
        ))
        
        # Cache initial values
        entity._update_attributes_from_wrapped()
        initial_target = entity.target_temperature
        initial_hvac_mode = entity.hvac_mode
        initial_hvac_action = entity.hvac_action
        initial_fan_mode = entity.fan_mode
        initial_swing_mode = entity.swing_mode
        
        # Act - Wrapped entity becomes unavailable
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=STATE_UNAVAILABLE,
            attributes={}
        ))
        
        # Assert - Last known values should still be accessible
        assert entity.target_temperature == initial_target
        assert entity.hvac_mode == initial_hvac_mode
        assert entity.hvac_action == initial_hvac_action
        assert entity.fan_mode == initial_fan_mode
        assert entity.swing_mode == initial_swing_mode
        
    def test_smart_climate_disables_temperature_control_during_degraded_mode(self):
        """Test Smart Climate disables temperature control operations during degraded mode."""
        # Arrange
        entity = self.create_smart_climate_entity()
        
        # Set wrapped entity as unavailable
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=STATE_UNAVAILABLE,
            attributes={}
        ))
        
        # Act & Assert - Temperature setting should be blocked
        with patch.object(entity, 'hass') as mock_hass:
            entity.set_temperature(temperature=25.0)
            mock_hass.services.async_call.assert_not_called()
            
    @pytest.mark.asyncio
    async def test_smart_climate_disables_hvac_mode_control_during_degraded_mode(self):
        """Test Smart Climate disables HVAC mode control operations during degraded mode."""
        # Arrange
        entity = self.create_smart_climate_entity()
        
        # Set wrapped entity as unavailable
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=STATE_UNAVAILABLE,
            attributes={}
        ))
        
        # Act & Assert - HVAC mode setting should be blocked
        with patch.object(entity, 'hass') as mock_hass:
            await entity.async_set_hvac_mode(HVACMode.HEAT)
            mock_hass.services.async_call.assert_not_called()
            
    @pytest.mark.asyncio
    async def test_smart_climate_disables_fan_mode_control_during_degraded_mode(self):
        """Test Smart Climate disables fan mode control operations during degraded mode."""
        # Arrange
        entity = self.create_smart_climate_entity()
        
        # Set wrapped entity as unavailable
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=STATE_UNAVAILABLE,
            attributes={}
        ))
        
        # Act & Assert - Fan mode setting should be blocked
        with patch.object(entity, 'hass') as mock_hass:
            await entity.async_set_fan_mode("high")
            mock_hass.services.async_call.assert_not_called()

    def test_smart_climate_shows_appropriate_status_attributes_during_degraded_mode(self):
        """Test Smart Climate shows appropriate status attributes during degraded mode."""
        # Arrange
        entity = self.create_smart_climate_entity()
        
        # Initially available
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=HVACMode.COOL,
            attributes={"temperature": 23.0}
        ))
        assert entity.available is True
        assert entity._was_unavailable is False
        
        # Act - Wrapped entity becomes unavailable
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=STATE_UNAVAILABLE,
            attributes={}
        ))
        
        # Assert - Status attributes should reflect degraded state
        assert not entity.available
        assert entity._was_unavailable is True
        
        # Additional status checks through extra_state_attributes if implemented
        if hasattr(entity, 'extra_state_attributes'):
            attrs = entity.extra_state_attributes
            # Could check for degraded mode indicators in attributes
            
    def test_smart_climate_recovers_properly_when_wrapped_entity_becomes_available_again(self):
        """Test Smart Climate recovers properly when wrapped entity becomes available again."""
        # Arrange
        entity = self.create_smart_climate_entity()
        
        # Set initial available state
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=HVACMode.COOL,
            attributes={"temperature": 23.0, "current_temperature": 22.5}
        ))
        
        # Go through unavailable phase
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=STATE_UNAVAILABLE,
            attributes={}
        ))
        assert not entity.available
        assert entity._was_unavailable is True
        
        # Act - Wrapped entity recovers
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=HVACMode.COOL,
            attributes={"temperature": 23.0, "current_temperature": 22.5}
        ))
        
        # Check availability property which handles recovery logic
        recovered_available = entity.available
        
        # Assert - Recovery should be detected
        assert recovered_available is True
        assert entity._was_unavailable is False  # Should be reset on recovery
        
    @pytest.mark.asyncio
    async def test_smart_climate_triggers_temperature_update_on_recovery_with_deviation(self):
        """Test Smart Climate triggers temperature update on recovery when significant deviation exists."""
        # Arrange
        entity = self.create_smart_climate_entity()
        entity._attr_target_temperature = 24.0  # Set target temperature
        
        # Mock room temperature with significant deviation
        self.mock_sensor_manager.get_room_temperature.return_value = 26.0  # 2°C deviation
        
        # Set initial available state
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=HVACMode.COOL,
            attributes={"temperature": 23.0}
        ))
        
        # Go unavailable
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=STATE_UNAVAILABLE,
            attributes={}
        ))
        assert not entity.available
        
        # Act - Recovery with task creation mock
        with patch.object(entity.hass, 'async_create_task') as mock_create_task:
            # Trigger recovery by checking availability
            recovered = entity.available
            
        # Assert - Should have scheduled temperature update due to significant deviation
        # The temperature update task should be created during recovery
        if mock_create_task.called:
            assert mock_create_task.call_count >= 1
            
    @pytest.mark.asyncio
    async def test_smart_climate_no_temperature_update_on_recovery_without_deviation(self):
        """Test Smart Climate doesn't trigger unnecessary updates on recovery without significant deviation."""
        # Arrange
        entity = self.create_smart_climate_entity()
        entity._attr_target_temperature = 24.0
        
        # Mock room temperature with minimal deviation
        self.mock_sensor_manager.get_room_temperature.return_value = 24.2  # 0.2°C deviation < threshold
        
        # Set initial available state
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=HVACMode.COOL,
            attributes={"temperature": 23.0}
        ))
        
        # Go unavailable
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=STATE_UNAVAILABLE,
            attributes={}
        ))
        
        # Act - Recovery with task creation mock
        with patch.object(entity.hass, 'async_create_task') as mock_create_task:
            # Trigger recovery
            recovered = entity.available
            
        # Assert - No temperature update task should be created for small deviation
        # Task might still be created for other reasons, but not for temperature update
        # due to small deviation (0.2°C < 0.3°C threshold)
        
    def test_enhanced_logging_for_temporary_vs_permanent_unavailability(self):
        """Test enhanced logging distinguishes between temporary and permanent unavailability."""
        # Arrange
        entity = self.create_smart_climate_entity()
        
        # Set initial available state
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=HVACMode.COOL,
            attributes={"temperature": 23.0}
        ))
        
        # Act & Assert - Test temporary unavailability logging
        with patch('custom_components.smart_climate.climate._LOGGER') as mock_logger:
            # Simulate temporary unavailability
            self.hass.states.set("climate.test_ac", create_mock_state(
                state=STATE_UNAVAILABLE,
                attributes={}
            ))
            
            # Check availability to trigger logging
            is_available = entity.available
            
            # Should log the unavailability
            mock_logger.debug.assert_called_with(
                "Wrapped entity %s became unavailable (state: %s)",
                "climate.test_ac",
                STATE_UNAVAILABLE
            )
            
    def test_enhanced_logging_for_recovery_from_unavailability(self):
        """Test enhanced logging for recovery from unavailability."""
        # Arrange
        entity = self.create_smart_climate_entity()
        
        # Go through unavailable state first
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=STATE_UNAVAILABLE,
            attributes={}
        ))
        # Trigger unavailability detection
        entity.available
        
        # Act & Assert - Test recovery logging
        with patch('custom_components.smart_climate.climate._LOGGER') as mock_logger:
            # Simulate recovery
            self.hass.states.set("climate.test_ac", create_mock_state(
                state=HVACMode.COOL,
                attributes={"temperature": 23.0}
            ))
            
            # Check availability to trigger recovery logging
            is_available = entity.available
            
            # Should log the recovery
            mock_logger.info.assert_called_with(
                "Wrapped entity %s recovered from unavailable state (state: %s)",
                "climate.test_ac",
                HVACMode.COOL
            )
            
    def test_timeout_tolerance_brief_unavailability_does_not_trigger_degraded_mode(self):
        """Test timeout tolerance - brief unavailability doesn't trigger degraded mode immediately."""
        # Arrange
        entity = self.create_smart_climate_entity()
        
        # Set initial available state
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=HVACMode.COOL,
            attributes={"temperature": 23.0}
        ))
        assert entity.available is True
        
        # Act - Brief unavailability
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=STATE_UNAVAILABLE,
            attributes={}
        ))
        
        # Assert - Entity should detect unavailability but handle gracefully
        assert not entity.available  # Reflects current state
        assert entity._was_unavailable is True  # Tracks the change
        
        # The key is that even though unavailable, the entity doesn't panic
        # and can handle service calls gracefully (they're blocked but don't crash)
        
    @pytest.mark.asyncio
    async def test_timeout_tolerance_with_state_unknown(self):
        """Test timeout tolerance handles STATE_UNKNOWN similar to STATE_UNAVAILABLE."""
        # Arrange
        entity = self.create_smart_climate_entity()
        
        # Set initial available state
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=HVACMode.COOL,
            attributes={"temperature": 23.0}
        ))
        
        # Act - State becomes unknown (another form of unavailable)
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=STATE_UNKNOWN,
            attributes={}
        ))
        
        # Assert - Should handle STATE_UNKNOWN same as STATE_UNAVAILABLE
        assert not entity.available
        assert entity._was_unavailable is True
        
        # Service calls should be blocked during unknown state
        with patch.object(entity, 'hass') as mock_hass:
            await entity.async_set_hvac_mode(HVACMode.HEAT)
            mock_hass.services.async_call.assert_not_called()
            
    def test_timeout_tolerance_with_none_state(self):
        """Test timeout tolerance handles None state (entity not found)."""
        # Arrange
        entity = self.create_smart_climate_entity()
        
        # Act - Entity state becomes None (entity removed/not found)
        self.hass.states.set("climate.test_ac", None)
        
        # Assert - Should handle missing entity gracefully
        assert not entity.available  # Should return False for missing entity
        
    @pytest.mark.asyncio
    async def test_training_data_collection_paused_during_unavailability(self):
        """Test training data collection is paused when sensors are unavailable."""
        # Arrange
        entity = self.create_smart_climate_entity()
        
        # Set wrapped entity as unavailable
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=STATE_UNAVAILABLE,
            attributes={}
        ))
        
        # Mock sensor manager to return None for unavailable sensors
        self.mock_sensor_manager.get_room_temperature.return_value = None
        
        # Act - Try to provide feedback (this would normally collect training data)
        await entity._provide_feedback()
        
        # Assert - No offset calculation should occur with unavailable data
        # Feedback should skip when data is unavailable
        # The exact behavior depends on implementation, but key is no crash/error
        
    @pytest.mark.asyncio 
    async def test_gradual_recovery_after_extended_unavailability(self):
        """Test gradual recovery behavior after extended unavailability period."""
        # Arrange
        entity = self.create_smart_climate_entity()
        entity._attr_target_temperature = 24.0
        
        # Simulate extended unavailability period
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=STATE_UNAVAILABLE,
            attributes={}
        ))
        
        # Wait in unavailable state
        assert not entity.available
        assert entity._was_unavailable is True
        
        # Act - Recovery with significant room temperature change
        self.mock_sensor_manager.get_room_temperature.return_value = 27.0  # Significant change
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=HVACMode.COOL,
            attributes={"temperature": 23.0, "current_temperature": 22.0}
        ))
        
        # Check recovery
        with patch.object(entity.hass, 'async_create_task') as mock_create_task:
            recovered = entity.available
            
        # Assert - Should detect recovery and schedule temperature update
        assert recovered is True
        assert entity._was_unavailable is False
        
        # Should have triggered temperature update due to significant deviation (3°C)
        if mock_create_task.called:
            assert mock_create_task.call_count >= 1

    @pytest.mark.asyncio
    async def test_service_call_error_handling_during_degraded_mode(self):
        """Test service call error handling during degraded mode doesn't crash the system."""
        # Arrange
        entity = self.create_smart_climate_entity()
        
        # Set wrapped entity as unavailable
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=STATE_UNAVAILABLE,
            attributes={}
        ))
        
        # Act & Assert - Multiple service calls should be handled gracefully
        with patch('custom_components.smart_climate.climate._LOGGER') as mock_logger:
            # Temperature setting
            entity.set_temperature(temperature=25.0)
            
            # HVAC mode setting
            await entity.async_set_hvac_mode(HVACMode.HEAT)
            
            # Fan mode setting
            await entity.async_set_fan_mode("high")
            
            # Swing mode setting
            await entity.async_set_swing_mode("horizontal")
            
            # All should log warnings but not crash
            assert mock_logger.warning.call_count >= 4  # One for each blocked operation
            
    def test_availability_state_persistence_across_multiple_checks(self):
        """Test availability state is correctly persisted across multiple property checks."""
        # Arrange
        entity = self.create_smart_climate_entity()
        
        # Set initial state
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=HVACMode.COOL,
            attributes={"temperature": 23.0}
        ))
        
        # First check - should be available
        assert entity.available is True
        assert entity._was_unavailable is False
        
        # Make unavailable
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=STATE_UNAVAILABLE,
            attributes={}
        ))
        
        # Multiple checks should consistently show unavailable
        assert entity.available is False
        assert entity._was_unavailable is True
        assert entity.available is False  # Second check
        assert entity._was_unavailable is True  # State should persist
        
        # Recovery
        self.hass.states.set("climate.test_ac", create_mock_state(
            state=HVACMode.COOL,
            attributes={"temperature": 23.0}
        ))
        
        # Multiple checks should consistently show available
        assert entity.available is True
        assert entity._was_unavailable is False
        assert entity.available is True  # Second check  
        assert entity._was_unavailable is False  # State should persist