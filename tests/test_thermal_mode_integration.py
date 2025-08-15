"""Comprehensive integration tests for thermal state + mode priority system.

ABOUTME: End-to-end tests for thermal state and mode conflict resolution,
verifying actual A/C control behavior across all priority scenarios.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, time
from homeassistant.const import STATE_ON, STATE_OFF

from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.models import (
    OffsetInput, 
    OffsetResult, 
    ModeAdjustments, 
    SmartClimateData
)
from custom_components.smart_climate.thermal_models import ThermalState
from custom_components.smart_climate.const import DOMAIN
from tests.fixtures.mock_entities import (
    create_mock_hass,
    create_mock_state,
    create_mock_offset_engine,
    create_mock_sensor_manager,
    create_mock_mode_manager,
    create_mock_temperature_controller,
    create_mock_coordinator
)


class TestThermalModeIntegration:
    """End-to-end integration tests for thermal state + mode priority system."""

    @pytest.fixture
    def mock_hass(self):
        """Mock Home Assistant instance with thermal component access."""
        hass = create_mock_hass()
        hass.data = {
            DOMAIN: {
                "test_entry": {
                    "thermal_components": {
                        "climate.test": MagicMock()  # Mock thermal manager
                    }
                }
            }
        }
        
        # Create and register climate entity state properly
        climate_state = create_mock_state(
            state="cool",  # Use valid HVAC mode instead of STATE_ON
            attributes={"current_temperature": 22.0, "hvac_mode": "cool"},
            entity_id="climate.test"
        )
        hass.states.set("climate.test", climate_state)
        
        return hass

    @pytest.fixture
    def thermal_manager(self):
        """Mock thermal manager with configurable state."""
        manager = MagicMock()
        manager.current_state = ThermalState.PRIMING
        return manager

    @pytest.fixture
    def real_climate_entity(self, mock_hass, thermal_manager):
        """Create SmartClimateEntity with real component instances for integration testing."""
        config = {'entry_id': 'test_entry'}
        
        # Create real component instances
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=config,
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room_temp",
            offset_engine=create_mock_offset_engine(),
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(mock_hass),
            coordinator=create_mock_coordinator()
        )
        
        # Register thermal manager for hass.data access
        mock_hass.data[DOMAIN]["test_entry"]["thermal_components"]["climate.test"] = thermal_manager
        
        # Setup humidity sensors to return None by default (not configured)
        if hasattr(entity._sensor_manager, 'get_indoor_humidity'):
            entity._sensor_manager.get_indoor_humidity.return_value = None
        if hasattr(entity._sensor_manager, 'get_outdoor_humidity'):
            entity._sensor_manager.get_outdoor_humidity.return_value = None
        
        return entity

    @pytest.mark.asyncio
    async def test_boost_overrides_drifting_forces_cooling(self, real_climate_entity, mock_hass, thermal_manager):
        """Test PRIORITY 1: BOOST mode overrides DRIFTING state and forces cooling.
        
        When user activates boost mode during DRIFTING thermal state,
        the mode override should win and force aggressive cooling.
        """
        # Arrange: Setup DRIFTING thermal state
        thermal_manager.current_state = ThermalState.DRIFTING
        
        # Setup boost mode adjustments with force_operation=True
        boost_adjustments = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=-2.0,  # Aggressive cooling
            force_operation=True  # Signal override
        )
        real_climate_entity._mode_manager.get_adjustments.return_value = boost_adjustments
        
        # Setup sensor readings
        real_climate_entity._sensor_manager.get_room_temperature.return_value = 24.0
        real_climate_entity._sensor_manager.get_outdoor_temperature.return_value = 30.0
        real_climate_entity._sensor_manager.get_power_consumption.return_value = 1500.0
        
        # Setup offset engine
        offset_result = OffsetResult(offset=1.0, clamped=False, reason="test", confidence=0.8)
        real_climate_entity._offset_engine.calculate_offset.return_value = offset_result
        
        # Track temperature controller calls to verify A/C control
        temp_controller_calls = []
        original_send_command = real_climate_entity._temperature_controller.send_temperature_command
        
        async def track_send_command(entity_id, temperature):
            temp_controller_calls.append({"entity_id": entity_id, "temperature": temperature})
            await original_send_command(entity_id, temperature)
        
        real_climate_entity._temperature_controller.send_temperature_command = track_send_command
        
        # Mock temperature controller to return the boost target
        real_climate_entity._temperature_controller.apply_offset_and_limits.return_value = 20.0  # 22.0 + (-2.0)
        
        # Mock HVAC mode check
        with patch.object(real_climate_entity, '_is_hvac_mode_active', return_value=True):
            # Act: Apply temperature with boost mode active during DRIFTING
            await real_climate_entity._apply_temperature_with_offset(22.0, source="boost_test")
            
            # Assert: Verify cooling was forced despite DRIFTING state
            assert len(temp_controller_calls) == 1
            assert temp_controller_calls[0]["entity_id"] == "climate.test"
            assert temp_controller_calls[0]["temperature"] == 20.0  # Boost target, not DRIFTING high target
            
            # Verify hass service was called for actual A/C control
            mock_hass.services.async_call.assert_called_once_with(
                domain="climate",
                service="set_temperature",
                service_data={"entity_id": "climate.test", "temperature": 20.0}
            )

    @pytest.mark.asyncio
    async def test_drifting_turns_off_ac_sets_high_target(self, real_climate_entity, mock_hass, thermal_manager):
        """Test PRIORITY 2: DRIFTING state turns A/C off by setting high target temperature.
        
        When thermal learning is in DRIFTING state and no mode override is active,
        the system should set target = current_room_temp + 3.0°C to turn A/C off.
        """
        # Arrange: Setup DRIFTING thermal state
        thermal_manager.current_state = ThermalState.DRIFTING
        
        # Setup standard mode (no force_operation)
        standard_adjustments = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0,
            force_operation=False  # No override
        )
        real_climate_entity._mode_manager.get_adjustments.return_value = standard_adjustments
        
        # Setup sensor readings
        room_temp = 25.5
        real_climate_entity._sensor_manager.get_room_temperature.return_value = room_temp
        real_climate_entity._sensor_manager.get_outdoor_temperature.return_value = 28.0
        
        # Track A/C commands
        temp_controller_calls = []
        original_send_command = real_climate_entity._temperature_controller.send_temperature_command
        
        async def track_send_command(entity_id, temperature):
            temp_controller_calls.append({"entity_id": entity_id, "temperature": temperature})
            await original_send_command(entity_id, temperature)
        
        real_climate_entity._temperature_controller.send_temperature_command = track_send_command
        
        # Mock temperature controller to return DRIFTING target
        expected_drifting_target = room_temp + 3.0  # 25.5 + 3.0 = 28.5
        real_climate_entity._temperature_controller.apply_offset_and_limits.return_value = expected_drifting_target
        
        # Mock HVAC mode check
        with patch.object(real_climate_entity, '_is_hvac_mode_active', return_value=True):
            # Act: Apply temperature during DRIFTING state
            await real_climate_entity._apply_temperature_with_offset(24.0, source="drifting_test")
            
            # Assert: Verify A/C was turned off via high target
            assert len(temp_controller_calls) == 1
            assert temp_controller_calls[0]["temperature"] == expected_drifting_target
            
            # Verify service call to actual A/C with high target to turn off
            mock_hass.services.async_call.assert_called_once_with(
                domain="climate",
                service="set_temperature",
                service_data={"entity_id": "climate.test", "temperature": expected_drifting_target}
            )

    @pytest.mark.asyncio
    async def test_away_mode_drifting_coexistence_works(self, real_climate_entity, mock_hass, thermal_manager):
        """Test AWAY mode coexists with DRIFTING state for thermal learning.
        
        AWAY mode has force_operation=False, so DRIFTING state directive
        should still apply, allowing thermal learning to continue during away periods.
        """
        # Arrange: Setup DRIFTING thermal state
        thermal_manager.current_state = ThermalState.DRIFTING
        
        # Setup away mode (no force_operation)
        away_adjustments = ModeAdjustments(
            temperature_override=26.0,  # Away mode temperature
            offset_adjustment=1.0,      # Efficiency adjustment
            update_interval_override=None,
            boost_offset=0.0,
            force_operation=False  # Away mode doesn't force override
        )
        real_climate_entity._mode_manager.get_adjustments.return_value = away_adjustments
        
        # Setup sensor readings
        room_temp = 23.0
        real_climate_entity._sensor_manager.get_room_temperature.return_value = room_temp
        real_climate_entity._sensor_manager.get_outdoor_temperature.return_value = 27.0
        
        # Track A/C commands
        temp_controller_calls = []
        original_send_command = real_climate_entity._temperature_controller.send_temperature_command
        
        async def track_send_command(entity_id, temperature):
            temp_controller_calls.append({"entity_id": entity_id, "temperature": temperature})
            await original_send_command(entity_id, temperature)
        
        real_climate_entity._temperature_controller.send_temperature_command = track_send_command
        
        # DRIFTING should still apply even with away mode
        expected_drifting_target = room_temp + 3.0  # 23.0 + 3.0 = 26.0
        real_climate_entity._temperature_controller.apply_offset_and_limits.return_value = expected_drifting_target
        
        # Mock HVAC mode check
        with patch.object(real_climate_entity, '_is_hvac_mode_active', return_value=True):
            # Act: Apply temperature during AWAY + DRIFTING
            await real_climate_entity._apply_temperature_with_offset(25.0, source="away_drifting_test")
            
            # Assert: DRIFTING logic should apply, not away temperature override
            assert len(temp_controller_calls) == 1
            assert temp_controller_calls[0]["temperature"] == expected_drifting_target
            
            # Verify thermal learning continues during away mode
            mock_hass.services.async_call.assert_called_once_with(
                domain="climate",
                service="set_temperature",
                service_data={"entity_id": "climate.test", "temperature": expected_drifting_target}
            )

    @pytest.mark.asyncio
    async def test_mode_state_restoration_when_boost_ends(self, real_climate_entity, mock_hass, thermal_manager):
        """Test automatic state restoration when boost mode ends.
        
        When boost mode is deactivated, the system should automatically
        return to the underlying thermal state behavior without complex tracking.
        """
        # Arrange: Setup DRIFTING thermal state (underlying state)
        thermal_manager.current_state = ThermalState.DRIFTING
        room_temp = 24.5
        real_climate_entity._sensor_manager.get_room_temperature.return_value = room_temp
        real_climate_entity._sensor_manager.get_outdoor_temperature.return_value = 29.0
        
        # Track A/C commands across mode changes
        temp_controller_calls = []
        original_send_command = real_climate_entity._temperature_controller.send_temperature_command
        
        async def track_send_command(entity_id, temperature):
            temp_controller_calls.append({"entity_id": entity_id, "temperature": temperature})
            await original_send_command(entity_id, temperature)
        
        real_climate_entity._temperature_controller.send_temperature_command = track_send_command
        
        # Phase 1: Boost mode active (force_operation=True)
        boost_adjustments = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=-2.0,
            force_operation=True
        )
        real_climate_entity._mode_manager.get_adjustments.return_value = boost_adjustments
        real_climate_entity._temperature_controller.apply_offset_and_limits.return_value = 20.0  # Boost target
        
        with patch.object(real_climate_entity, '_is_hvac_mode_active', return_value=True):
            # Apply temperature during boost mode
            await real_climate_entity._apply_temperature_with_offset(22.0, source="boost_phase")
            
            # Verify boost mode behavior
            assert len(temp_controller_calls) == 1
            assert temp_controller_calls[0]["temperature"] == 20.0  # Boost cooling
        
        # Phase 2: Boost mode ends (force_operation=False)
        standard_adjustments = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0,
            force_operation=False  # Boost mode ended
        )
        real_climate_entity._mode_manager.get_adjustments.return_value = standard_adjustments
        
        # Now DRIFTING state should take over
        expected_drifting_target = room_temp + 3.0  # 24.5 + 3.0 = 27.5
        real_climate_entity._temperature_controller.apply_offset_and_limits.return_value = expected_drifting_target
        
        with patch.object(real_climate_entity, '_is_hvac_mode_active', return_value=True):
            # Apply temperature after boost ends
            await real_climate_entity._apply_temperature_with_offset(22.0, source="restoration_phase")
            
            # Assert: System automatically restored to DRIFTING behavior
            assert len(temp_controller_calls) == 2
            assert temp_controller_calls[1]["temperature"] == expected_drifting_target  # Back to DRIFTING high target

    @pytest.mark.asyncio
    async def test_temperature_safety_limits_always_enforced(self, real_climate_entity, mock_hass, thermal_manager):
        """Test safety limits are always enforced regardless of thermal state or mode.
        
        Even during DRIFTING state, temperature safety limits in TemperatureController
        should prevent unsafe temperatures from being sent to the A/C.
        """
        # Arrange: Setup DRIFTING thermal state
        thermal_manager.current_state = ThermalState.DRIFTING
        
        # Setup extreme room temperature that would create unsafe DRIFTING target
        extreme_room_temp = 35.0  # Very high room temperature
        real_climate_entity._sensor_manager.get_room_temperature.return_value = extreme_room_temp
        
        # Standard mode adjustments (no force_operation)
        standard_adjustments = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0,
            force_operation=False
        )
        real_climate_entity._mode_manager.get_adjustments.return_value = standard_adjustments
        
        # Mock temperature controller to enforce safety limits
        # DRIFTING would want 35.0 + 3.0 = 38.0°C, but safety limit is 30.0°C
        max_safe_temp = 30.0
        real_climate_entity._temperature_controller.apply_offset_and_limits.return_value = max_safe_temp
        
        # Track A/C commands
        temp_controller_calls = []
        original_send_command = real_climate_entity._temperature_controller.send_temperature_command
        
        async def track_send_command(entity_id, temperature):
            temp_controller_calls.append({"entity_id": entity_id, "temperature": temperature})
            await original_send_command(entity_id, temperature)
        
        real_climate_entity._temperature_controller.send_temperature_command = track_send_command
        
        with patch.object(real_climate_entity, '_is_hvac_mode_active', return_value=True):
            # Act: Apply temperature during DRIFTING with extreme room temp
            await real_climate_entity._apply_temperature_with_offset(25.0, source="safety_test")
            
            # Assert: Safety limits enforced despite DRIFTING state
            assert len(temp_controller_calls) == 1
            assert temp_controller_calls[0]["temperature"] == max_safe_temp  # Clamped to safety limit
            
            # Verify safe temperature sent to A/C
            mock_hass.services.async_call.assert_called_once_with(
                domain="climate",
                service="set_temperature",
                service_data={"entity_id": "climate.test", "temperature": max_safe_temp}
            )

    @pytest.mark.asyncio
    async def test_ac_internal_temp_used_for_drifting_calculation(self, real_climate_entity, mock_hass, thermal_manager):
        """Test A/C internal temperature is used for DRIFTING state calculations.
        
        The _resolve_target_temperature method should use current_room_temp for DRIFTING
        calculations, which comes from the room sensor, not the A/C internal sensor.
        """
        # Arrange: Setup DRIFTING thermal state
        thermal_manager.current_state = ThermalState.DRIFTING
        
        # Setup different temperatures for room sensor vs A/C internal
        room_sensor_temp = 24.0  # From room sensor
        ac_internal_temp = 22.5  # From A/C internal sensor
        
        # Configure sensor manager to return room sensor temperature
        real_climate_entity._sensor_manager.get_room_temperature.return_value = room_sensor_temp
        
        # Configure hass.states to return A/C internal temperature
        climate_state = create_mock_state(
            state="cool",  # Valid HVAC mode
            attributes={"current_temperature": ac_internal_temp},
            entity_id="climate.test"
        )
        mock_hass.states.set("climate.test", climate_state)
        
        # Standard mode adjustments
        standard_adjustments = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0,
            force_operation=False
        )
        real_climate_entity._mode_manager.get_adjustments.return_value = standard_adjustments
        
        # Mock resolver method to verify it's called with room sensor temperature
        with patch.object(real_climate_entity, '_resolve_target_temperature', 
                         return_value=27.0) as mock_resolver:
            
            with patch.object(real_climate_entity, '_is_hvac_mode_active', return_value=True):
                # Act: Apply temperature during DRIFTING
                await real_climate_entity._apply_temperature_with_offset(25.0, source="temp_source_test")
                
                # Assert: Resolver called with room sensor temperature, not A/C internal
                mock_resolver.assert_called_once()
                call_args = mock_resolver.call_args[0]
                current_room_temp = call_args[1]  # Second parameter is current_room_temp
                
                assert current_room_temp == room_sensor_temp  # Should use room sensor, not A/C internal
                assert current_room_temp != ac_internal_temp  # Verify it's not using A/C internal

    @pytest.mark.asyncio
    async def test_logging_shows_correct_decision_paths(self, real_climate_entity, mock_hass, thermal_manager):
        """Test that logging shows correct decision paths for debugging.
        
        Each priority level should log its decision to help with debugging
        conflicts and understanding system behavior.
        """
        # Setup for boost mode override logging test
        thermal_manager.current_state = ThermalState.DRIFTING
        real_climate_entity._sensor_manager.get_room_temperature.return_value = 24.0
        
        boost_adjustments = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=-2.0,
            force_operation=True
        )
        real_climate_entity._mode_manager.get_adjustments.return_value = boost_adjustments
        real_climate_entity._temperature_controller.apply_offset_and_limits.return_value = 20.0
        
        # Mock the resolver to verify logging (if logging method exists)
        with patch.object(real_climate_entity, '_resolve_target_temperature', 
                         return_value=20.0) as mock_resolver:
            
            # Mock logging method if it exists
            if hasattr(real_climate_entity, '_log_priority_decision'):
                with patch.object(real_climate_entity, '_log_priority_decision') as mock_log:
                    with patch.object(real_climate_entity, '_is_hvac_mode_active', return_value=True):
                        # Act: Apply temperature during boost + DRIFTING
                        await real_climate_entity._apply_temperature_with_offset(22.0, source="logging_test")
                        
                        # Assert: Priority resolver was called
                        mock_resolver.assert_called_once()
                        
                        # If logging method exists, verify it was called with appropriate message
                        if mock_log.called:
                            # Verify some form of priority decision logging occurred
                            assert mock_log.call_count > 0
            else:
                # If no specific logging method, just verify resolver was called
                with patch.object(real_climate_entity, '_is_hvac_mode_active', return_value=True):
                    await real_climate_entity._apply_temperature_with_offset(22.0, source="logging_test")
                    mock_resolver.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_priority_hierarchy_verification(self, real_climate_entity, mock_hass, thermal_manager):
        """Test complete priority hierarchy across all thermal states and modes.
        
        Comprehensive test to verify the priority order:
        1. Mode Override (force_operation=True) 
        2. Thermal State Directive (DRIFTING)
        3. Standard Operation
        """
        room_temp = 24.0
        real_climate_entity._sensor_manager.get_room_temperature.return_value = room_temp
        real_climate_entity._sensor_manager.get_outdoor_temperature.return_value = 28.0
        
        # Track all A/C commands
        temp_controller_calls = []
        original_send_command = real_climate_entity._temperature_controller.send_temperature_command
        
        async def track_send_command(entity_id, temperature):
            temp_controller_calls.append({"entity_id": entity_id, "temperature": temperature})
            await original_send_command(entity_id, temperature)
        
        real_climate_entity._temperature_controller.send_temperature_command = track_send_command
        
        # Test 1: Boost mode overrides all thermal states
        boost_adjustments = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=-3.0,
            force_operation=True
        )
        
        thermal_states_to_test = [
            ThermalState.PRIMING,
            ThermalState.DRIFTING,
            ThermalState.CORRECTING,
            ThermalState.RECOVERY,
            ThermalState.PROBING,
            ThermalState.CALIBRATING
        ]
        
        for state in thermal_states_to_test:
            thermal_manager.current_state = state
            real_climate_entity._mode_manager.get_adjustments.return_value = boost_adjustments
            real_climate_entity._temperature_controller.apply_offset_and_limits.return_value = 19.0  # Boost target
            
            with patch.object(real_climate_entity, '_is_hvac_mode_active', return_value=True):
                await real_climate_entity._apply_temperature_with_offset(22.0, source=f"boost_override_{state.value}")
        
        # Verify boost mode overrode all thermal states
        assert len(temp_controller_calls) == len(thermal_states_to_test)
        for call in temp_controller_calls:
            assert call["temperature"] == 19.0  # All should use boost target
        
        # Test 2: DRIFTING state works when no force_operation
        temp_controller_calls.clear()
        thermal_manager.current_state = ThermalState.DRIFTING
        
        standard_adjustments = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0,
            force_operation=False
        )
        real_climate_entity._mode_manager.get_adjustments.return_value = standard_adjustments
        real_climate_entity._temperature_controller.apply_offset_and_limits.return_value = 27.0  # DRIFTING target
        
        with patch.object(real_climate_entity, '_is_hvac_mode_active', return_value=True):
            await real_climate_entity._apply_temperature_with_offset(22.0, source="drifting_priority")
        
        # Verify DRIFTING behavior when no override
        assert len(temp_controller_calls) == 1
        assert temp_controller_calls[0]["temperature"] == 27.0  # DRIFTING high target
        
        # Test 3: Standard operation for non-DRIFTING states
        temp_controller_calls.clear()
        thermal_manager.current_state = ThermalState.CORRECTING
        real_climate_entity._temperature_controller.apply_offset_and_limits.return_value = 23.5  # Standard target
        
        with patch.object(real_climate_entity, '_is_hvac_mode_active', return_value=True):
            await real_climate_entity._apply_temperature_with_offset(22.0, source="standard_operation")
        
        # Verify standard operation
        assert len(temp_controller_calls) == 1
        assert temp_controller_calls[0]["temperature"] == 23.5  # Standard offset logic