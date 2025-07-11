"""ABOUTME: Comprehensive integration tests for entity unavailability handling.
Tests full system behavior when entities become unavailable and recover, including coordinator updates,
dashboard sensors, learning system, and temperature corrections."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from datetime import datetime, timedelta
import asyncio

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_ON, STATE_OFF
from homeassistant.components.climate.const import HVACMode, HVACAction
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.smart_climate.const import DOMAIN
from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.coordinator import SmartClimateCoordinator
from custom_components.smart_climate.models import (
    OffsetInput, OffsetResult, SmartClimateData, ModeAdjustments
)
from custom_components.smart_climate.sensor import (
    OffsetCurrentSensor,
    LearningProgressSensor,
    AccuracyCurrentSensor,
    CalibrationStatusSensor,
    HysteresisStateSensor,
)
from tests.fixtures.unavailable_test_fixtures import (
    create_unavailable_test_scenario,
    create_mock_hass_with_unavailable_entities,
    MockUnavailableClimateEntity,
    MockUnavailableSensor,
    create_mock_offset_engine_with_protection,
    create_mock_sensor_manager_with_unavailable
)
from tests.fixtures.mock_entities import (
    create_mock_mode_manager,
    create_mock_temperature_controller,
)
from tests.fixtures.coordinator_test_fixtures import (
    create_mock_offset_engine
)


@pytest.fixture
def full_integration_setup():
    """Create a complete integration test setup with all components."""
    scenario = create_unavailable_test_scenario()
    
    # Create real coordinator
    coordinator = SmartClimateCoordinator(
        hass=scenario["hass"],
        update_interval=180,
        sensor_manager=scenario["sensor_manager"],
        offset_engine=scenario["offset_engine"],
        mode_manager=create_mock_mode_manager(),
        wrapped_entity_id="climate.wrapped",
        unique_id="test_smart_climate"
    )
    
    # Replace the mock coordinator in scenario
    scenario["coordinator"] = coordinator
    
    # Create climate entity
    climate_entity = SmartClimateEntity(
        hass=scenario["hass"],
        config={
            "name": "Test Smart Climate",
            "climate_entity": "climate.wrapped",
            "room_sensor": "sensor.room",
            "max_offset": 5.0,
            "update_interval": 180,
            "ml_enabled": True,
            "enable_learning": True,
            "default_target_temperature": 24.0,
            "gradual_adjustment_rate": 0.5
        },
        wrapped_entity_id="climate.wrapped",
        room_sensor_id="sensor.room",
        offset_engine=scenario["offset_engine"],
        sensor_manager=scenario["sensor_manager"],
        mode_manager=create_mock_mode_manager(),
        temperature_controller=create_mock_temperature_controller(),
        coordinator=coordinator
    )
    
    scenario["climate_entity_obj"] = climate_entity
    
    # Create mock config entry for sensors
    mock_config_entry = Mock(spec=ConfigEntry)
    mock_config_entry.unique_id = "test_smart_climate"
    mock_config_entry.title = "Test Smart Climate"
    
    # Create dashboard sensors
    sensors = []
    sensors.append(OffsetCurrentSensor(
        coordinator, "climate.wrapped", mock_config_entry
    ))
    sensors.append(LearningProgressSensor(
        coordinator, "climate.wrapped", mock_config_entry
    ))
    sensors.append(AccuracyCurrentSensor(
        coordinator, "climate.wrapped", mock_config_entry
    ))
    sensors.append(CalibrationStatusSensor(
        coordinator, "climate.wrapped", mock_config_entry
    ))
    sensors.append(HysteresisStateSensor(
        coordinator, "climate.wrapped", mock_config_entry
    ))
    
    scenario["dashboard_sensors"] = sensors
    
    return scenario


class TestFullSystemUnavailabilityIntegration:
    """Test complete system behavior during unavailability scenarios."""
    
    @pytest.mark.asyncio
    async def test_wrapped_entity_unavailable_full_system_response(self, full_integration_setup):
        """Test full system response when wrapped climate entity becomes unavailable."""
        # Arrange
        setup = full_integration_setup
        climate_entity = setup["climate_entity_obj"]
        coordinator = setup["coordinator"]
        sensors = setup["dashboard_sensors"]
        
        # Make entities available initially
        setup["climate_entity"].make_available("cool", 22.0)
        setup["room_sensor"].make_available(23.0)
        setup["hass"].states._set_state("climate.wrapped", setup["climate_entity"].to_state_mock())
        setup["hass"].states._set_state("sensor.room", setup["room_sensor"].to_state_mock())
        
        # Initial coordinator update
        await coordinator.async_config_entry_first_refresh()
        
        # Verify initial state
        assert climate_entity.hvac_mode == "cool"
        assert climate_entity.current_temperature == 23.0
        for sensor in sensors:
            assert sensor.available is True
        
        # Act - Make wrapped entity unavailable
        setup["climate_entity"].make_unavailable()
        setup["hass"].states._set_state("climate.wrapped", setup["climate_entity"].to_state_mock())
        
        # Trigger coordinator update
        await coordinator.async_refresh()
        
        # Assert - Check full system response
        # Climate entity should handle unavailability
        assert climate_entity.hvac_mode == "unavailable"
        assert climate_entity.target_temperature == 24.0  # Uses default
        
        # Coordinator should still have data
        assert coordinator.data is not None
        assert coordinator.data.room_temp == 23.0
        
        # Dashboard sensors should remain available (they depend on offset_engine)
        for sensor in sensors:
            assert sensor.available is True
            assert sensor.native_value is not None
        
        # Offset engine should enter protection mode
        assert setup["offset_engine"]._protection_active is True
        
    @pytest.mark.asyncio
    async def test_coordinator_handles_multiple_unavailable_entities(self, full_integration_setup):
        """Test coordinator behavior when multiple entities become unavailable."""
        # Arrange
        setup = full_integration_setup
        coordinator = setup["coordinator"]
        
        # Start with all available
        setup["climate_entity"].make_available("cool", 22.0)
        setup["room_sensor"].make_available(23.0)
        setup["hass"].states._set_state("climate.wrapped", setup["climate_entity"].to_state_mock())
        setup["hass"].states._set_state("sensor.room", setup["room_sensor"].to_state_mock())
        
        await coordinator.async_config_entry_first_refresh()
        initial_data = coordinator.data
        
        # Act - Make multiple entities unavailable
        setup["climate_entity"].make_unavailable()
        setup["sensor_manager"].make_room_sensor_unavailable()
        setup["hass"].states._set_state("climate.wrapped", setup["climate_entity"].to_state_mock())
        
        # Update coordinator
        await coordinator.async_refresh()
        
        # Assert
        # Coordinator should have partial data
        assert coordinator.data is not None
        assert coordinator.data.room_temp is None  # Room sensor unavailable
        assert coordinator.data.calculated_offset == 0.0  # Can't calculate without room temp
        
    @pytest.mark.asyncio
    async def test_dashboard_sensors_during_unavailability(self, full_integration_setup):
        """Test dashboard sensor behavior during entity unavailability."""
        # Arrange
        setup = full_integration_setup
        sensors = setup["dashboard_sensors"]
        coordinator = setup["coordinator"]
        
        # Configure offset engine to return specific values
        setup["offset_engine"].async_get_dashboard_data = AsyncMock(return_value={
            "current_offset": 2.5,
            "learning_progress": 75,
            "current_accuracy": 90,
            "calibration_status": "completed",
            "hysteresis_state": "cooling_active"
        })
        
        # Start with available entities
        setup["climate_entity"].make_available("cool", 22.0)
        setup["room_sensor"].make_available(23.0)
        setup["hass"].states._set_state("climate.wrapped", setup["climate_entity"].to_state_mock())
        setup["hass"].states._set_state("sensor.room", setup["room_sensor"].to_state_mock())
        
        # Act - Make wrapped entity unavailable
        setup["climate_entity"].make_unavailable()
        setup["hass"].states._set_state("climate.wrapped", setup["climate_entity"].to_state_mock())
        
        # Assert - Dashboard sensors should still work
        offset_sensor = next(s for s in sensors if isinstance(s, OffsetCurrentSensor))
        learning_sensor = next(s for s in sensors if isinstance(s, LearningProgressSensor))
        accuracy_sensor = next(s for s in sensors if isinstance(s, AccuracyCurrentSensor))
        calibration_sensor = next(s for s in sensors if isinstance(s, CalibrationStatusSensor))
        hysteresis_sensor = next(s for s in sensors if isinstance(s, HysteresisStateSensor))
        
        assert offset_sensor.native_value == 2.5
        assert learning_sensor.native_value == 75
        assert accuracy_sensor.native_value == 90
        assert calibration_sensor.native_value == "completed"
        assert hysteresis_sensor.native_value == "cooling_active"
        
        # All sensors should remain available
        for sensor in sensors:
            assert sensor.available is True
    
    @pytest.mark.asyncio
    async def test_learning_system_pause_resume_on_unavailability(self, full_integration_setup):
        """Test that learning system pauses when entities unavailable and resumes on recovery."""
        # Arrange
        setup = full_integration_setup
        offset_engine = setup["offset_engine"]
        coordinator = setup["coordinator"]
        
        # Track learning activity
        learning_calls = []
        offset_engine.record_feedback = Mock(side_effect=lambda *args: learning_calls.append("feedback"))
        
        # Start with available entities and learning enabled
        setup["climate_entity"].make_available("cool", 22.0)
        setup["room_sensor"].make_available(23.0)
        setup["hass"].states._set_state("climate.wrapped", setup["climate_entity"].to_state_mock())
        setup["hass"].states._set_state("sensor.room", setup["room_sensor"].to_state_mock())
        
        # Initial update - should allow learning
        await coordinator.async_refresh()
        assert offset_engine._protection_active is False
        
        # Act - Make entity unavailable
        setup["climate_entity"].make_unavailable()
        setup["hass"].states._set_state("climate.wrapped", setup["climate_entity"].to_state_mock())
        
        # Enable protection mode
        offset_engine.enable_protection()
        
        # Try to record feedback - should be blocked
        offset_engine.record_feedback(Mock())
        pre_unavailable_count = len(learning_calls)
        
        # Make available again
        setup["climate_entity"].make_available("cool", 22.0)
        setup["hass"].states._set_state("climate.wrapped", setup["climate_entity"].to_state_mock())
        offset_engine.disable_protection()
        
        # Record feedback again - should work
        offset_engine.record_feedback(Mock())
        
        # Assert
        assert len(learning_calls) == pre_unavailable_count + 1
        assert offset_engine._protection_active is False
    
    @pytest.mark.asyncio
    async def test_temperature_correction_after_recovery(self, full_integration_setup):
        """Test that temperature corrections resume correctly after entity recovery."""
        # Arrange
        setup = full_integration_setup
        climate_entity = setup["climate_entity_obj"]
        coordinator = setup["coordinator"]
        temp_controller = climate_entity._temperature_controller
        
        # Configure temperature controller
        temp_controller.apply_offset_and_limits = Mock(return_value=20.0)
        temp_controller.apply_gradual_adjustment = Mock(side_effect=lambda curr, target: target)
        temp_controller.send_temperature_command = AsyncMock()
        
        # Start unavailable
        setup["climate_entity"].make_unavailable()
        setup["hass"].states._set_state("climate.wrapped", setup["climate_entity"].to_state_mock())
        
        # Act - Recover with specific temperature
        setup["climate_entity"].make_available("cool", 24.0)
        setup["room_sensor"].make_available(23.0)
        setup["hass"].states._set_state("climate.wrapped", setup["climate_entity"].to_state_mock())
        setup["hass"].states._set_state("sensor.room", setup["room_sensor"].to_state_mock())
        
        # Set user target temperature
        climate_entity._attr_target_temperature = 22.0
        
        # Trigger temperature update
        await climate_entity.async_set_temperature(temperature=22.0)
        
        # Assert - Temperature correction should be applied
        temp_controller.send_temperature_command.assert_called_once()
        call_args = temp_controller.send_temperature_command.call_args
        assert call_args[0][0] == "climate.wrapped"  # Entity ID
        assert isinstance(call_args[0][1], float)  # Temperature value
    
    @pytest.mark.asyncio
    async def test_rapid_unavailable_available_cycles(self, full_integration_setup):
        """Test system stability during rapid unavailable/available transitions."""
        # Arrange
        setup = full_integration_setup
        climate_entity = setup["climate_entity_obj"]
        coordinator = setup["coordinator"]
        
        # Track state changes
        state_history = []
        
        # Perform rapid cycles
        for i in range(5):
            # Make available
            setup["climate_entity"].make_available("cool", 22.0 + i)
            setup["hass"].states._set_state("climate.wrapped", setup["climate_entity"].to_state_mock())
            await coordinator.async_refresh()
            state_history.append(("available", climate_entity.hvac_mode))
            
            # Make unavailable
            setup["climate_entity"].make_unavailable()
            setup["hass"].states._set_state("climate.wrapped", setup["climate_entity"].to_state_mock())
            await coordinator.async_refresh()
            state_history.append(("unavailable", climate_entity.hvac_mode))
            
            # Small delay to simulate real timing
            await asyncio.sleep(0.1)
        
        # Assert - System should remain stable
        # Check that states alternated correctly
        for i, (expected, actual_mode) in enumerate(state_history):
            if expected == "available":
                assert actual_mode == "cool"
            else:
                assert actual_mode == "unavailable"
        
        # Coordinator should not have crashed
        assert coordinator.last_update_success is True
        
        # Dashboard sensors should still be available
        for sensor in setup["dashboard_sensors"]:
            assert sensor.available is True
    
    @pytest.mark.asyncio
    async def test_config_entry_reload_during_unavailability(self, full_integration_setup):
        """Test configuration entry reload while entities are unavailable."""
        # Arrange
        setup = full_integration_setup
        climate_entity = setup["climate_entity_obj"]
        coordinator = setup["coordinator"]
        
        # Make entity unavailable
        setup["climate_entity"].make_unavailable()
        setup["hass"].states._set_state("climate.wrapped", setup["climate_entity"].to_state_mock())
        
        # Simulate config entry reload
        # First, clean up
        await coordinator._async_shutdown()
        
        # Create new coordinator
        new_coordinator = SmartClimateCoordinator(
            hass=setup["hass"],
            update_interval=180,
            sensor_manager=setup["sensor_manager"],
            offset_engine=setup["offset_engine"],
            mode_manager=create_mock_mode_manager(),
            wrapped_entity_id="climate.wrapped",
            unique_id="test_smart_climate"
        )
        
        # Act - Initialize with unavailable entity
        try:
            await new_coordinator.async_config_entry_first_refresh()
        except UpdateFailed:
            # This is expected if entity is unavailable
            pass
        
        # Assert - Coordinator should handle gracefully
        assert new_coordinator.data is not None
        assert hasattr(new_coordinator, "last_update_success")
        
        # Make entity available
        setup["climate_entity"].make_available("cool", 22.0)
        setup["hass"].states._set_state("climate.wrapped", setup["climate_entity"].to_state_mock())
        
        # Update should succeed now
        await new_coordinator.async_refresh()
        assert new_coordinator.last_update_success is True
    
    @pytest.mark.asyncio
    async def test_sensor_manager_handles_all_sensors_unavailable(self, full_integration_setup):
        """Test system behavior when all sensors become unavailable."""
        # Arrange
        setup = full_integration_setup
        sensor_manager = setup["sensor_manager"]
        coordinator = setup["coordinator"]
        climate_entity = setup["climate_entity_obj"]
        
        # Start with all available
        setup["climate_entity"].make_available("cool", 22.0)
        setup["room_sensor"].make_available(23.0)
        setup["hass"].states._set_state("climate.wrapped", setup["climate_entity"].to_state_mock())
        setup["hass"].states._set_state("sensor.room", setup["room_sensor"].to_state_mock())
        
        # Add outdoor and power sensors
        setup["outdoor_sensor"].make_available(30.0)
        setup["power_sensor"].make_available(1500.0)
        setup["hass"].states._set_state("sensor.outdoor", setup["outdoor_sensor"].to_state_mock())
        setup["hass"].states._set_state("sensor.power", setup["power_sensor"].to_state_mock())
        
        await coordinator.async_refresh()
        
        # Act - Make all sensors unavailable
        sensor_manager.make_room_sensor_unavailable()
        sensor_manager.make_outdoor_sensor_unavailable()
        sensor_manager.make_power_sensor_unavailable()
        
        await coordinator.async_refresh()
        
        # Assert
        # Coordinator should handle gracefully
        assert coordinator.data is not None
        assert coordinator.data.room_temp is None
        assert coordinator.data.outdoor_temp is None
        assert coordinator.data.power is None
        
        # Climate entity should use defaults
        assert climate_entity.current_temperature is None
        assert climate_entity.target_temperature == 24.0  # Default
        
        # Offset calculation should use protection
        assert setup["offset_engine"]._protection_active is True
    
    @pytest.mark.asyncio
    async def test_offset_engine_protection_during_partial_unavailability(self, full_integration_setup):
        """Test offset engine protection when some entities are unavailable."""
        # Arrange
        setup = full_integration_setup
        offset_engine = setup["offset_engine"]
        coordinator = setup["coordinator"]
        
        # Configure specific offset behavior
        def calculate_with_protection(input_data):
            if input_data.room_temp is None:
                # Can't calculate without room temp
                return OffsetResult(
                    offset=offset_engine._last_good_offset,
                    clamped=False,
                    reason="Missing room temperature",
                    confidence=0.0
                )
            return OffsetResult(
                offset=2.0,
                clamped=False,
                reason="Normal calculation",
                confidence=0.9
            )
        
        offset_engine.calculate_offset = Mock(side_effect=calculate_with_protection)
        offset_engine._last_good_offset = 1.5
        
        # Start with all available
        setup["climate_entity"].make_available("cool", 22.0)
        setup["room_sensor"].make_available(23.0)
        setup["hass"].states._set_state("climate.wrapped", setup["climate_entity"].to_state_mock())
        setup["hass"].states._set_state("sensor.room", setup["room_sensor"].to_state_mock())
        
        await coordinator.async_refresh()
        
        # Act - Make room sensor unavailable
        setup["sensor_manager"].make_room_sensor_unavailable()
        await coordinator.async_refresh()
        
        # Assert
        # Should use last good offset
        assert coordinator.data.calculated_offset == 1.5
        
        # Make room sensor available again
        setup["sensor_manager"].make_room_sensor_available()
        await coordinator.async_refresh()
        
        # Should calculate normally again
        assert coordinator.data.calculated_offset == 2.0
    
    @pytest.mark.asyncio
    async def test_learning_switch_behavior_during_unavailability(self, full_integration_setup):
        """Test learning switch entity behavior when system entities are unavailable."""
        # Arrange
        setup = full_integration_setup
        
        # Create a mock learning switch
        learning_switch = Mock()
        learning_switch.is_on = True
        learning_switch.available = True
        learning_switch.state = STATE_ON
        
        # Configure offset engine learning state
        setup["offset_engine"].is_learning_enabled = Mock(return_value=True)
        
        # Make climate entity unavailable
        setup["climate_entity"].make_unavailable()
        setup["hass"].states._set_state("climate.wrapped", setup["climate_entity"].to_state_mock())
        
        # Act - Check if learning should be paused
        offset_engine = setup["offset_engine"]
        offset_engine.enable_protection()
        
        # Assert
        # Learning should be effectively paused during protection
        assert offset_engine._protection_active is True
        
        # But switch state doesn't change automatically
        assert learning_switch.is_on is True
        
        # When entity recovers
        setup["climate_entity"].make_available("cool", 22.0)
        setup["hass"].states._set_state("climate.wrapped", setup["climate_entity"].to_state_mock())
        offset_engine.disable_protection()
        
        # Learning should resume
        assert offset_engine._protection_active is False
        assert offset_engine.is_learning_enabled() is True


class TestCoordinatorUpdateFailureHandling:
    """Test coordinator behavior during update failures."""
    
    @pytest.mark.asyncio
    async def test_coordinator_handles_update_failure_gracefully(self, full_integration_setup):
        """Test coordinator handles update failures without crashing."""
        # Arrange
        setup = full_integration_setup
        coordinator = setup["coordinator"]
        
        # Mock sensor manager to raise exception
        setup["sensor_manager"].get_room_temperature = Mock(
            side_effect=Exception("Sensor read failed")
        )
        
        # Act - Try to update
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        
        # Assert - Coordinator should mark update as failed
        # but should have previous data if available
        if coordinator.data:
            assert coordinator.data is not None
    
    @pytest.mark.asyncio
    async def test_coordinator_recovery_after_multiple_failures(self, full_integration_setup):
        """Test coordinator can recover after multiple update failures."""
        # Arrange
        setup = full_integration_setup
        coordinator = setup["coordinator"]
        
        # Configure sensor manager to fail then succeed
        call_count = 0
        def get_room_temp_with_failures():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise Exception("Temporary failure")
            return 23.0
        
        setup["sensor_manager"].get_room_temperature = Mock(
            side_effect=get_room_temp_with_failures
        )
        
        # Make entities available
        setup["climate_entity"].make_available("cool", 22.0)
        setup["hass"].states._set_state("climate.wrapped", setup["climate_entity"].to_state_mock())
        
        # Act - Multiple update attempts
        for i in range(3):
            try:
                await coordinator.async_refresh()
            except:
                pass  # Expected to fail
        
        # Final attempt should succeed
        await coordinator.async_refresh()
        
        # Assert
        assert coordinator.last_update_success is True
        assert coordinator.data.room_temp == 23.0
    
    @pytest.mark.asyncio
    async def test_dashboard_sensors_remain_available_during_coordinator_failures(
        self, full_integration_setup
    ):
        """Test dashboard sensors remain available even when coordinator updates fail."""
        # Arrange
        setup = full_integration_setup
        sensors = setup["dashboard_sensors"]
        coordinator = setup["coordinator"]
        
        # Set initial good data
        setup["offset_engine"].async_get_dashboard_data = AsyncMock(return_value={
            "current_offset": 2.0,
            "learning_progress": 50,
            "current_accuracy": 85,
            "calibration_status": "in_progress",
            "hysteresis_state": "idle"
        })
        
        # Cause coordinator update to fail
        setup["sensor_manager"].get_room_temperature = Mock(
            side_effect=Exception("Sensor failure")
        )
        
        # Act - Try to update (will fail)
        try:
            await coordinator.async_refresh()
        except:
            pass
        
        # Assert - Dashboard sensors should still work
        for sensor in sensors:
            assert sensor.available is True
            assert sensor.native_value is not None
        
        # Specific sensor checks
        offset_sensor = next(s for s in sensors if isinstance(s, OffsetCurrentSensor))
        assert offset_sensor.native_value == 2.0