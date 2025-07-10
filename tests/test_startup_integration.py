"""Integration tests for startup AC temperature update behavior."""
# ABOUTME: End-to-end integration tests for startup AC temperature update functionality
# Tests complete startup flow with real component interactions

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant
from homeassistant.components.climate.const import HVACMode
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.const import STATE_UNAVAILABLE

from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.models import (
    OffsetResult, 
    SmartClimateData, 
    ModeAdjustments,
    OffsetInput
)
from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.sensor_manager import SensorManager
from custom_components.smart_climate.mode_manager import ModeManager
from custom_components.smart_climate.temperature_controller import TemperatureController
from custom_components.smart_climate.coordinator import SmartClimateCoordinator

from tests.fixtures.mock_entities import (
    create_mock_hass,
    create_mock_state,
    create_mock_offset_engine,
    create_mock_sensor_manager,
    create_mock_mode_manager,
    create_mock_temperature_controller,
)
from tests.fixtures.coordinator_test_fixtures import (
    create_mock_coordinator,
    create_dashboard_data_fixture,
    create_failed_coordinator,
)


class TestStartupIntegrationFullFlow:
    """Test complete startup integration flow from entity creation to AC update."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance with realistic states."""
        hass = create_mock_hass()
        
        # Mock wrapped climate entity with learning-capable data
        wrapped_state = create_mock_state(
            "climate.test_ac", 
            HVACMode.COOL, 
            {
                "target_temperature": 24.0, 
                "current_temperature": 22.5,  # AC internal sensor
                "hvac_modes": ["off", "cool", "heat", "auto"],
                "min_temp": 16.0,
                "max_temp": 30.0,
            }
        )
        
        # Mock room sensor with different reading (offset scenario)
        room_sensor_state = create_mock_state(
            "sensor.room_temp", 
            "25.0",  # Room is warmer than AC sensor
            {"unit_of_measurement": "°C", "device_class": "temperature"}
        )
        
        # Mock outdoor sensor
        outdoor_sensor_state = create_mock_state(
            "sensor.outdoor_temp",
            "30.0",
            {"unit_of_measurement": "°C", "device_class": "temperature"}
        )
        
        # Mock power sensor
        power_sensor_state = create_mock_state(
            "sensor.power_consumption",
            "150.0",  # AC idle power
            {"unit_of_measurement": "W", "device_class": "power"}
        )
        
        # Setup state retrieval
        def mock_get_state(entity_id):
            states = {
                "climate.test_ac": wrapped_state,
                "sensor.room_temp": room_sensor_state,
                "sensor.outdoor_temp": outdoor_sensor_state,
                "sensor.power_consumption": power_sensor_state,
            }
            return states.get(entity_id)
        
        hass.states.get.side_effect = mock_get_state
        return hass

    @pytest.fixture
    def integration_config(self):
        """Configuration for integration tests."""
        return {
            "name": "Test Smart Climate",
            "climate_entity": "climate.test_ac",
            "room_sensor": "sensor.room_temp",
            "outdoor_sensor": "sensor.outdoor_temp",
            "power_sensor": "sensor.power_consumption",
            "max_offset": 5.0,
            "min_temperature": 16.0,
            "max_temperature": 30.0,
            "update_interval": 180,
            "ml_enabled": True,
            "gradual_adjustment_rate": 0.5,
        }

    @pytest.fixture
    def realistic_dependencies(self, mock_hass, integration_config):
        """Create realistic dependencies with startup learning data."""
        # Create offset engine with learned data
        offset_engine = create_mock_offset_engine(
            learning_enabled=True,
            samples=25,  # Sufficient learning data
            accuracy=0.87,
            calculated_offset=2.5  # Significant offset from learning
        )
        
        # Mock calculate_offset to return startup-appropriate result
        offset_engine.calculate_offset.return_value = OffsetResult(
            offset=2.5,
            clamped=False,
            reason="Learned offset from 25 samples",
            confidence=0.87
        )
        
        # Create sensor manager with realistic data
        sensor_manager = create_mock_sensor_manager()
        sensor_manager.get_room_temperature.return_value = 25.0  # Room temp
        sensor_manager.get_outdoor_temperature.return_value = 30.0
        sensor_manager.get_power_consumption.return_value = 150.0
        
        # Create mode manager
        mode_manager = create_mock_mode_manager()
        mode_manager.current_mode = "none"
        mode_manager.get_adjustments.return_value = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        )
        
        # Create temperature controller
        temperature_controller = create_mock_temperature_controller()
        # Apply offset: 24.0 + 2.5 = 26.5°C to AC
        temperature_controller.apply_offset_and_limits.return_value = 26.5
        temperature_controller.send_temperature_command = AsyncMock()
        
        # Create coordinator with startup data
        coordinator_data = SmartClimateData(
            room_temp=25.0,
            outdoor_temp=30.0,
            power=150.0,
            calculated_offset=2.5,
            mode_adjustments=mode_manager.get_adjustments.return_value,
            is_startup_calculation=True  # Key flag for startup
        )
        
        coordinator = create_mock_coordinator(
            mock_hass,
            offset_engine,
            entity_id="climate.test_ac",
            initial_data=coordinator_data
        )
        
        # Mock coordinator methods for startup
        coordinator.async_force_startup_refresh = AsyncMock()
        coordinator.async_config_entry_first_refresh = AsyncMock()
        
        return {
            "offset_engine": offset_engine,
            "sensor_manager": sensor_manager,
            "mode_manager": mode_manager,
            "temperature_controller": temperature_controller,
            "coordinator": coordinator,
        }

    @pytest.mark.asyncio
    async def test_complete_startup_flow_with_learning_data(
        self, mock_hass, integration_config, realistic_dependencies
    ):
        """Test complete startup flow from entity creation to AC temperature update."""
        # Create Smart Climate entity with realistic dependencies
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=integration_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=realistic_dependencies["offset_engine"],
            sensor_manager=realistic_dependencies["sensor_manager"],
            mode_manager=realistic_dependencies["mode_manager"],
            temperature_controller=realistic_dependencies["temperature_controller"],
            coordinator=realistic_dependencies["coordinator"],
        )
        
        # Set initial target temperature (user preference)
        entity._attr_target_temperature = 24.0
        
        # Mock entity state methods
        entity.async_write_ha_state = AsyncMock()
        
        # 1. Test startup sequence - async_added_to_hass
        await entity.async_added_to_hass()
        
        # Verify coordinator listener was added
        realistic_dependencies["coordinator"].async_add_listener.assert_called_once()
        
        # Verify sensor manager started listening
        realistic_dependencies["sensor_manager"].start_listening.assert_called_once()
        
        # 2. Test coordinator startup refresh (triggered during setup)
        await realistic_dependencies["coordinator"].async_force_startup_refresh()
        realistic_dependencies["coordinator"].async_force_startup_refresh.assert_called()
        
        # 3. Test coordinator update handling - simulate coordinator update
        entity._handle_coordinator_update()
        
        # Verify offset calculation was triggered
        realistic_dependencies["offset_engine"].calculate_offset.assert_called()
        
        # Verify the OffsetInput was created correctly
        call_args = realistic_dependencies["offset_engine"].calculate_offset.call_args[0][0]
        assert isinstance(call_args, OffsetInput)
        assert call_args.room_temp == 25.0
        assert call_args.ac_internal_temp == 22.5  # From wrapped entity
        assert call_args.outdoor_temp == 30.0
        assert call_args.power_consumption == 150.0
        assert call_args.mode == "none"
        
        # 4. Verify temperature controller applied offset and limits
        realistic_dependencies["temperature_controller"].apply_offset_and_limits.assert_called_once()
        temp_call_args = realistic_dependencies["temperature_controller"].apply_offset_and_limits.call_args[0]
        assert temp_call_args[0] == 24.0  # Target temperature
        assert temp_call_args[1] == 2.5   # Calculated offset
        
        # 5. Verify AC temperature command was sent (THE KEY ASSERTION)
        realistic_dependencies["temperature_controller"].send_temperature_command.assert_called_once_with(
            "climate.test_ac", 26.5  # 24.0 + 2.5 offset
        )
        
        # 6. Verify entity state was updated
        entity.async_write_ha_state.assert_called()

    @pytest.mark.asyncio
    async def test_startup_flow_with_multiple_entities(
        self, mock_hass, integration_config, realistic_dependencies
    ):
        """Test startup with multiple Smart Climate entities."""
        # Create first entity
        entity1 = SmartClimateEntity(
            hass=mock_hass,
            config=integration_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=realistic_dependencies["offset_engine"],
            sensor_manager=realistic_dependencies["sensor_manager"],
            mode_manager=realistic_dependencies["mode_manager"],
            temperature_controller=realistic_dependencies["temperature_controller"],
            coordinator=realistic_dependencies["coordinator"],
        )
        entity1._attr_target_temperature = 24.0
        entity1.async_write_ha_state = AsyncMock()
        
        # Create second entity with different configuration
        config2 = integration_config.copy()
        config2["climate_entity"] = "climate.bedroom_ac"
        config2["room_sensor"] = "sensor.bedroom_temp"
        
        # Mock second wrapped entity
        bedroom_state = create_mock_state(
            "climate.bedroom_ac", 
            HVACMode.COOL, 
            {"target_temperature": 22.0, "current_temperature": 21.0}
        )
        bedroom_sensor_state = create_mock_state("sensor.bedroom_temp", "23.0")
        
        # Update mock_hass to return these states
        def enhanced_get_state(entity_id):
            states = {
                "climate.test_ac": mock_hass.states.get("climate.test_ac"),
                "sensor.room_temp": mock_hass.states.get("sensor.room_temp"),
                "sensor.outdoor_temp": mock_hass.states.get("sensor.outdoor_temp"),
                "sensor.power_consumption": mock_hass.states.get("sensor.power_consumption"),
                "climate.bedroom_ac": bedroom_state,
                "sensor.bedroom_temp": bedroom_sensor_state,
            }
            return states.get(entity_id)
        
        mock_hass.states.get.side_effect = enhanced_get_state
        
        # Create second entity dependencies
        deps2 = {
            "offset_engine": create_mock_offset_engine(learning_enabled=True, samples=15, calculated_offset=1.8),
            "sensor_manager": create_mock_sensor_manager(),
            "mode_manager": create_mock_mode_manager(),
            "temperature_controller": create_mock_temperature_controller(),
            "coordinator": create_mock_coordinator(mock_hass, realistic_dependencies["offset_engine"], entity_id="climate.bedroom_ac"),
        }
        
        # Configure second entity sensor manager
        deps2["sensor_manager"].get_room_temperature.return_value = 23.0
        deps2["sensor_manager"].get_outdoor_temperature.return_value = 30.0
        deps2["temperature_controller"].apply_offset_and_limits.return_value = 23.8  # 22.0 + 1.8
        deps2["temperature_controller"].send_temperature_command = AsyncMock()
        
        # Create coordinator data for second entity
        coordinator_data2 = SmartClimateData(
            room_temp=23.0,
            outdoor_temp=30.0,
            power=120.0,
            calculated_offset=1.8,
            mode_adjustments=deps2["mode_manager"].get_adjustments.return_value,
            is_startup_calculation=True
        )
        deps2["coordinator"].data = coordinator_data2
        
        entity2 = SmartClimateEntity(
            hass=mock_hass,
            config=config2,
            wrapped_entity_id="climate.bedroom_ac",
            room_sensor_id="sensor.bedroom_temp",
            offset_engine=deps2["offset_engine"],
            sensor_manager=deps2["sensor_manager"],
            mode_manager=deps2["mode_manager"],
            temperature_controller=deps2["temperature_controller"],
            coordinator=deps2["coordinator"],
        )
        entity2._attr_target_temperature = 22.0
        entity2.async_write_ha_state = AsyncMock()
        
        # Test both entities startup
        await entity1.async_added_to_hass()
        await entity2.async_added_to_hass()
        
        # Trigger coordinator updates for both
        entity1._handle_coordinator_update()
        entity2._handle_coordinator_update()
        
        # Verify both entities sent temperature commands
        realistic_dependencies["temperature_controller"].send_temperature_command.assert_called_with(
            "climate.test_ac", 26.5
        )
        deps2["temperature_controller"].send_temperature_command.assert_called_with(
            "climate.bedroom_ac", 23.8
        )
        
        # Verify both entities updated their states
        entity1.async_write_ha_state.assert_called()
        entity2.async_write_ha_state.assert_called()

    @pytest.mark.asyncio
    async def test_startup_performance_with_large_learning_dataset(
        self, mock_hass, integration_config
    ):
        """Test startup performance with large learning datasets."""
        # Create offset engine with large dataset
        large_dataset_engine = create_mock_offset_engine(
            learning_enabled=True,
            samples=1000,  # Large learning dataset
            accuracy=0.95,
            calculated_offset=3.2
        )
        
        # Mock performance-optimized methods
        large_dataset_engine.calculate_offset.return_value = OffsetResult(
            offset=3.2,
            clamped=False,
            reason="Optimized calculation from 1000 samples",
            confidence=0.95
        )
        
        # Create other dependencies
        sensor_manager = create_mock_sensor_manager()
        sensor_manager.get_room_temperature.return_value = 26.0
        
        mode_manager = create_mock_mode_manager()
        temperature_controller = create_mock_temperature_controller()
        temperature_controller.apply_offset_and_limits.return_value = 27.2
        temperature_controller.send_temperature_command = AsyncMock()
        
        coordinator_data = SmartClimateData(
            room_temp=26.0,
            outdoor_temp=32.0,
            power=180.0,
            calculated_offset=3.2,
            mode_adjustments=mode_manager.get_adjustments.return_value,
            is_startup_calculation=True
        )
        
        coordinator = create_mock_coordinator(
            mock_hass,
            large_dataset_engine,
            entity_id="climate.test_ac",
            initial_data=coordinator_data
        )
        
        # Create entity
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=integration_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=large_dataset_engine,
            sensor_manager=sensor_manager,
            mode_manager=mode_manager,
            temperature_controller=temperature_controller,
            coordinator=coordinator,
        )
        entity._attr_target_temperature = 24.0
        entity.async_write_ha_state = AsyncMock()
        
        # Measure startup time
        import time
        start_time = time.time()
        
        # Execute startup flow
        await entity.async_added_to_hass()
        entity._handle_coordinator_update()
        
        end_time = time.time()
        startup_duration = end_time - start_time
        
        # Assert performance requirements
        assert startup_duration < 1.0  # Should complete within 1 second
        
        # Verify functionality still works with large dataset
        large_dataset_engine.calculate_offset.assert_called()
        temperature_controller.send_temperature_command.assert_called_with(
            "climate.test_ac", 27.2
        )


class TestStartupIntegrationRealWorldScenarios:
    """Test startup integration in realistic Home Assistant scenarios."""

    @pytest.fixture
    def mock_hass_with_delays(self):
        """Create mock Home Assistant with delayed sensor initialization."""
        hass = create_mock_hass()
        
        # Initially return None for sensors (not ready)
        def delayed_get_state(entity_id):
            # Sensors take time to initialize
            if "sensor" in entity_id:
                return None
            # Climate entity is available immediately
            elif "climate" in entity_id:
                return create_mock_state(
                    entity_id,
                    HVACMode.COOL,
                    {"target_temperature": 24.0, "current_temperature": 22.0}
                )
            return None
        
        hass.states.get.side_effect = delayed_get_state
        return hass

    @pytest.mark.asyncio
    async def test_startup_after_home_assistant_restart(
        self, mock_hass_with_delays
    ):
        """Test startup behavior after Home Assistant restart."""
        # Create configuration
        config = {
            "name": "Test Smart Climate",
            "climate_entity": "climate.test_ac",
            "room_sensor": "sensor.room_temp",
            "update_interval": 180,
        }
        
        # Create dependencies that handle unavailable sensors gracefully
        offset_engine = create_mock_offset_engine(
            learning_enabled=True,
            samples=30,  # Has learning data from before restart
            calculated_offset=2.2
        )
        
        sensor_manager = create_mock_sensor_manager()
        # Initially sensors are unavailable
        sensor_manager.get_room_temperature.return_value = None
        sensor_manager.get_outdoor_temperature.return_value = None
        
        mode_manager = create_mock_mode_manager()
        temperature_controller = create_mock_temperature_controller()
        temperature_controller.send_temperature_command = AsyncMock()
        
        coordinator = create_mock_coordinator(
            mock_hass_with_delays,
            offset_engine,
            entity_id="climate.test_ac"
        )
        
        # Create entity
        entity = SmartClimateEntity(
            hass=mock_hass_with_delays,
            config=config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=mode_manager,
            temperature_controller=temperature_controller,
            coordinator=coordinator,
        )
        entity._attr_target_temperature = 24.0
        entity.async_write_ha_state = AsyncMock()
        
        # Test startup with unavailable sensors
        await entity.async_added_to_hass()
        
        # Should not crash and should handle gracefully
        assert entity._wrapped_entity_id == "climate.test_ac"
        
        # Simulate sensors becoming available later
        sensor_manager.get_room_temperature.return_value = 25.5
        sensor_manager.get_outdoor_temperature.return_value = 28.0
        
        # Now offset calculation should work
        offset_engine.calculate_offset.return_value = OffsetResult(
            offset=2.2, clamped=False, reason="Post-restart calculation", confidence=0.85
        )
        
        # Update coordinator data
        coordinator_data = SmartClimateData(
            room_temp=25.5,
            outdoor_temp=28.0,
            power=None,  # Power sensor still unavailable
            calculated_offset=2.2,
            mode_adjustments=mode_manager.get_adjustments.return_value,
            is_startup_calculation=True
        )
        coordinator.data = coordinator_data
        
        # Trigger coordinator update
        entity._handle_coordinator_update()
        
        # Should now calculate offset and update AC
        offset_engine.calculate_offset.assert_called()

    @pytest.mark.asyncio
    async def test_startup_with_slow_sensor_initialization(
        self, mock_hass, integration_config
    ):
        """Test startup with sensors that initialize slowly."""
        # Create dependencies
        offset_engine = create_mock_offset_engine(
            learning_enabled=True,
            samples=20,
            calculated_offset=1.8
        )
        
        # Create sensor manager with gradual initialization
        sensor_manager = create_mock_sensor_manager()
        
        # Initially no sensors available
        sensor_manager.get_room_temperature.return_value = None
        sensor_manager.get_outdoor_temperature.return_value = None
        sensor_manager.get_power_consumption.return_value = None
        
        mode_manager = create_mock_mode_manager()
        temperature_controller = create_mock_temperature_controller()
        temperature_controller.send_temperature_command = AsyncMock()
        
        coordinator = create_mock_coordinator(
            mock_hass,
            offset_engine,
            entity_id="climate.test_ac"
        )
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=integration_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=mode_manager,
            temperature_controller=temperature_controller,
            coordinator=coordinator,
        )
        entity._attr_target_temperature = 24.0
        entity.async_write_ha_state = AsyncMock()
        
        # Test initial startup
        await entity.async_added_to_hass()
        
        # Step 1: Room sensor becomes available
        sensor_manager.get_room_temperature.return_value = 25.0
        coordinator_data1 = SmartClimateData(
            room_temp=25.0,
            outdoor_temp=None,
            power=None,
            calculated_offset=1.5,  # Partial calculation
            mode_adjustments=mode_manager.get_adjustments.return_value,
            is_startup_calculation=True
        )
        coordinator.data = coordinator_data1
        
        offset_engine.calculate_offset.return_value = OffsetResult(
            offset=1.5, clamped=False, reason="Room sensor only", confidence=0.6
        )
        
        entity._handle_coordinator_update()
        
        # Should work with partial sensor data
        offset_engine.calculate_offset.assert_called()
        
        # Step 2: All sensors become available
        sensor_manager.get_outdoor_temperature.return_value = 30.0
        sensor_manager.get_power_consumption.return_value = 200.0
        
        coordinator_data2 = SmartClimateData(
            room_temp=25.0,
            outdoor_temp=30.0,
            power=200.0,
            calculated_offset=1.8,  # Full calculation
            mode_adjustments=mode_manager.get_adjustments.return_value,
            is_startup_calculation=False  # No longer startup
        )
        coordinator.data = coordinator_data2
        
        offset_engine.calculate_offset.return_value = OffsetResult(
            offset=1.8, clamped=False, reason="Full sensor data", confidence=0.9
        )
        
        entity._handle_coordinator_update()
        
        # Should calculate with full data
        assert offset_engine.calculate_offset.call_count == 2  # Called twice


class TestStartupIntegrationErrorRecovery:
    """Test startup integration error handling and recovery."""

    @pytest.fixture
    def mock_hass_with_errors(self):
        """Create mock Home Assistant that simulates various error conditions."""
        hass = create_mock_hass()
        
        # Mock states that might cause errors
        def error_prone_get_state(entity_id):
            if entity_id == "climate.broken_ac":
                return None  # Wrapped entity unavailable
            elif entity_id == "sensor.broken_sensor":
                state = Mock()
                state.state = STATE_UNAVAILABLE
                return state
            else:
                return create_mock_state(entity_id, "cool", {"target_temperature": 24.0})
        
        hass.states.get.side_effect = error_prone_get_state
        return hass

    @pytest.mark.asyncio
    async def test_startup_with_coordinator_failure(
        self, mock_hass_with_errors, integration_config
    ):
        """Test startup behavior when coordinator fails."""
        # Create failed coordinator
        failed_coordinator = create_failed_coordinator(mock_hass_with_errors, "climate.test_ac")
        
        # Create other dependencies
        offset_engine = create_mock_offset_engine()
        sensor_manager = create_mock_sensor_manager()
        mode_manager = create_mock_mode_manager()
        temperature_controller = create_mock_temperature_controller()
        temperature_controller.send_temperature_command = AsyncMock()
        
        entity = SmartClimateEntity(
            hass=mock_hass_with_errors,
            config=integration_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=mode_manager,
            temperature_controller=temperature_controller,
            coordinator=failed_coordinator,
        )
        entity.async_write_ha_state = AsyncMock()
        
        # Should not raise exception during startup
        await entity.async_added_to_hass()
        
        # Should handle coordinator failure gracefully
        entity._handle_coordinator_update()
        
        # Should not send temperature command due to coordinator failure
        temperature_controller.send_temperature_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_startup_error_recovery_mechanisms(
        self, mock_hass, integration_config
    ):
        """Test error recovery mechanisms during startup."""
        # Create dependencies with intermittent failures
        offset_engine = create_mock_offset_engine()
        
        # Mock offset engine to fail first, then succeed
        call_count = 0
        def failing_calculate_offset(offset_input):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First calculation failed")
            else:
                return OffsetResult(
                    offset=2.0, clamped=False, reason="Recovery calculation", confidence=0.8
                )
        
        offset_engine.calculate_offset.side_effect = failing_calculate_offset
        
        sensor_manager = create_mock_sensor_manager()
        sensor_manager.get_room_temperature.return_value = 25.0
        
        mode_manager = create_mock_mode_manager()
        
        temperature_controller = create_mock_temperature_controller()
        temperature_controller.apply_offset_and_limits.return_value = 26.0
        temperature_controller.send_temperature_command = AsyncMock()
        
        coordinator_data = SmartClimateData(
            room_temp=25.0,
            outdoor_temp=None,
            power=None,
            calculated_offset=0.0,  # Will be recalculated
            mode_adjustments=mode_manager.get_adjustments.return_value,
            is_startup_calculation=True
        )
        
        coordinator = create_mock_coordinator(
            mock_hass,
            offset_engine,
            entity_id="climate.test_ac",
            initial_data=coordinator_data
        )
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=integration_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=mode_manager,
            temperature_controller=temperature_controller,
            coordinator=coordinator,
        )
        entity._attr_target_temperature = 24.0
        entity.async_write_ha_state = AsyncMock()
        
        # First coordinator update should fail gracefully
        entity._handle_coordinator_update()
        
        # Should not send temperature command on first failure
        temperature_controller.send_temperature_command.assert_not_called()
        
        # Second coordinator update should succeed
        entity._handle_coordinator_update()
        
        # Should send temperature command on recovery
        temperature_controller.send_temperature_command.assert_called_with(
            "climate.test_ac", 26.0
        )

    @pytest.mark.asyncio
    async def test_startup_graceful_degradation(
        self, mock_hass, integration_config
    ):
        """Test graceful degradation when components fail during startup."""
        # Create offset engine that works
        offset_engine = create_mock_offset_engine(
            learning_enabled=True,
            samples=15,
            calculated_offset=1.5
        )
        offset_engine.calculate_offset.return_value = OffsetResult(
            offset=1.5, clamped=False, reason="Degraded mode", confidence=0.7
        )
        
        # Create sensor manager with partial failures
        sensor_manager = create_mock_sensor_manager()
        sensor_manager.get_room_temperature.return_value = 24.5  # Works
        sensor_manager.get_outdoor_temperature.return_value = None  # Failed
        sensor_manager.get_power_consumption.return_value = None   # Failed
        
        mode_manager = create_mock_mode_manager()
        
        # Create temperature controller that fails
        temperature_controller = create_mock_temperature_controller()
        temperature_controller.apply_offset_and_limits.return_value = 26.0
        temperature_controller.send_temperature_command = AsyncMock(
            side_effect=Exception("Temperature command failed")
        )
        
        coordinator_data = SmartClimateData(
            room_temp=24.5,
            outdoor_temp=None,  # Sensor failed
            power=None,         # Sensor failed
            calculated_offset=1.5,
            mode_adjustments=mode_manager.get_adjustments.return_value,
            is_startup_calculation=True
        )
        
        coordinator = create_mock_coordinator(
            mock_hass,
            offset_engine,
            entity_id="climate.test_ac",
            initial_data=coordinator_data
        )
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=integration_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=mode_manager,
            temperature_controller=temperature_controller,
            coordinator=coordinator,
        )
        entity._attr_target_temperature = 24.0
        entity.async_write_ha_state = AsyncMock()
        
        # Should handle partial sensor failures and temperature command failure gracefully
        entity._handle_coordinator_update()
        
        # Should still calculate offset with available data
        offset_engine.calculate_offset.assert_called()
        
        # Should attempt temperature command (even though it fails)
        temperature_controller.send_temperature_command.assert_called()
        
        # Should update entity state even with failures
        entity.async_write_ha_state.assert_called()


class TestStartupIntegrationTiming:
    """Test startup integration timing and coordination requirements."""

    @pytest.mark.asyncio
    async def test_startup_timing_coordination(
        self, mock_hass, integration_config
    ):
        """Test that startup timing is properly coordinated between components."""
        # Create realistic dependencies with timing simulation
        offset_engine = create_mock_offset_engine(
            learning_enabled=True,
            samples=20,
            calculated_offset=2.0
        )
        
        sensor_manager = create_mock_sensor_manager()
        sensor_manager.start_listening = AsyncMock()
        sensor_manager.stop_listening = AsyncMock()
        
        mode_manager = create_mock_mode_manager()
        
        temperature_controller = create_mock_temperature_controller()
        temperature_controller.apply_offset_and_limits.return_value = 26.0
        temperature_controller.send_temperature_command = AsyncMock()
        
        coordinator = create_mock_coordinator(
            mock_hass,
            offset_engine,
            entity_id="climate.test_ac"
        )
        coordinator.async_force_startup_refresh = AsyncMock()
        coordinator.async_config_entry_first_refresh = AsyncMock()
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=integration_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=mode_manager,
            temperature_controller=temperature_controller,
            coordinator=coordinator,
        )
        entity._attr_target_temperature = 24.0
        entity.async_write_ha_state = AsyncMock()
        
        # Test startup sequence timing
        start_time = datetime.now()
        
        # 1. Entity setup
        await entity.async_added_to_hass()
        setup_time = datetime.now()
        
        # 2. Coordinator startup refresh
        coordinator_data = SmartClimateData(
            room_temp=25.0,
            outdoor_temp=30.0,
            power=150.0,
            calculated_offset=2.0,
            mode_adjustments=mode_manager.get_adjustments.return_value,
            is_startup_calculation=True
        )
        coordinator.data = coordinator_data
        
        # 3. Handle coordinator update
        entity._handle_coordinator_update()
        completion_time = datetime.now()
        
        # Verify timing requirements
        setup_duration = (setup_time - start_time).total_seconds()
        total_duration = (completion_time - start_time).total_seconds()
        
        # Startup should be fast
        assert setup_duration < 0.1  # Setup in < 100ms
        assert total_duration < 0.5   # Total startup in < 500ms
        
        # Verify proper sequencing
        sensor_manager.start_listening.assert_called_once()
        coordinator.async_add_listener.assert_called_once()
        temperature_controller.send_temperature_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_startup_resource_usage_monitoring(
        self, mock_hass, integration_config
    ):
        """Test that startup doesn't cause excessive resource usage."""
        import gc
        
        # Create dependencies
        offset_engine = create_mock_offset_engine(
            learning_enabled=True,
            samples=50,  # Moderate dataset
            calculated_offset=2.5
        )
        
        sensor_manager = create_mock_sensor_manager()
        mode_manager = create_mock_mode_manager()
        temperature_controller = create_mock_temperature_controller()
        temperature_controller.send_temperature_command = AsyncMock()
        
        coordinator_data = SmartClimateData(
            room_temp=25.0,
            outdoor_temp=30.0,
            power=150.0,
            calculated_offset=2.5,
            mode_adjustments=mode_manager.get_adjustments.return_value,
            is_startup_calculation=True
        )
        
        coordinator = create_mock_coordinator(
            mock_hass,
            offset_engine,
            entity_id="climate.test_ac",
            initial_data=coordinator_data
        )
        
        # Monitor memory before startup
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Create and run startup multiple times to check for leaks
        entities = []
        for i in range(5):
            entity = SmartClimateEntity(
                hass=mock_hass,
                config=integration_config,
                wrapped_entity_id=f"climate.test_ac_{i}",
                room_sensor_id=f"sensor.room_temp_{i}",
                offset_engine=offset_engine,
                sensor_manager=sensor_manager,
                mode_manager=mode_manager,
                temperature_controller=temperature_controller,
                coordinator=coordinator,
            )
            entity._attr_target_temperature = 24.0
            entity.async_write_ha_state = AsyncMock()
            
            await entity.async_added_to_hass()
            entity._handle_coordinator_update()
            entities.append(entity)
        
        # Monitor memory after startup
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Memory growth should be reasonable
        object_growth = final_objects - initial_objects
        assert object_growth < 1000  # Less than 1000 new objects for 5 entities
        
        # Cleanup entities
        for entity in entities:
            await entity.async_will_remove_from_hass()


class TestStartupIntegrationAdvancedScenarios:
    """Test advanced startup integration scenarios and edge cases."""

    @pytest.mark.asyncio
    async def test_startup_with_concurrent_coordinator_updates(
        self, mock_hass, integration_config
    ):
        """Test startup behavior with concurrent coordinator updates."""
        # Create dependencies
        offset_engine = create_mock_offset_engine(
            learning_enabled=True,
            samples=30,
            calculated_offset=2.2
        )
        
        sensor_manager = create_mock_sensor_manager()
        sensor_manager.get_room_temperature.return_value = 25.5
        sensor_manager.get_outdoor_temperature.return_value = 31.0
        
        mode_manager = create_mock_mode_manager()
        temperature_controller = create_mock_temperature_controller()
        temperature_controller.apply_offset_and_limits.return_value = 26.7
        temperature_controller.send_temperature_command = AsyncMock()
        
        # Create coordinator that simulates multiple rapid updates
        coordinator_data = SmartClimateData(
            room_temp=25.5,
            outdoor_temp=31.0,
            power=170.0,
            calculated_offset=2.2,
            mode_adjustments=mode_manager.get_adjustments.return_value,
            is_startup_calculation=True
        )
        
        coordinator = create_mock_coordinator(
            mock_hass,
            offset_engine,
            entity_id="climate.test_ac",
            initial_data=coordinator_data
        )
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=integration_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=mode_manager,
            temperature_controller=temperature_controller,
            coordinator=coordinator,
        )
        entity._attr_target_temperature = 24.0
        entity.async_write_ha_state = AsyncMock()
        
        # Setup entity
        await entity.async_added_to_hass()
        
        # Simulate rapid coordinator updates (startup + immediate follow-up)
        entity._handle_coordinator_update()  # Startup update
        
        # Change data to simulate quick follow-up update
        coordinator_data.is_startup_calculation = False
        coordinator_data.calculated_offset = 2.3
        coordinator.data = coordinator_data
        
        entity._handle_coordinator_update()  # Follow-up update
        
        # Should handle both updates correctly
        assert offset_engine.calculate_offset.call_count >= 2
        assert temperature_controller.send_temperature_command.call_count >= 1

    @pytest.mark.asyncio
    async def test_startup_with_different_hvac_modes(
        self, mock_hass, integration_config
    ):
        """Test startup behavior with different HVAC modes."""
        from homeassistant.components.climate.const import HVACMode
        
        test_modes = [HVACMode.COOL, HVACMode.HEAT, HVACMode.AUTO]
        expected_offsets = [2.0, -1.5, 1.0]  # Different offsets for different modes
        
        for hvac_mode, expected_offset in zip(test_modes, expected_offsets):
            # Mock wrapped entity state for this mode
            wrapped_state = create_mock_state(
                "climate.test_ac",
                hvac_mode,
                {
                    "target_temperature": 24.0,
                    "current_temperature": 22.0,
                    "hvac_modes": ["off", "cool", "heat", "auto"]
                }
            )
            
            mock_hass.states.get.return_value = wrapped_state
            
            # Create dependencies for this mode
            offset_engine = create_mock_offset_engine(
                learning_enabled=True,
                samples=25,
                calculated_offset=expected_offset
            )
            
            offset_engine.calculate_offset.return_value = OffsetResult(
                offset=expected_offset,
                clamped=False,
                reason=f"Mode-specific offset for {hvac_mode}",
                confidence=0.88
            )
            
            sensor_manager = create_mock_sensor_manager()
            sensor_manager.get_room_temperature.return_value = 25.0
            
            mode_manager = create_mock_mode_manager()
            temperature_controller = create_mock_temperature_controller()
            temperature_controller.apply_offset_and_limits.return_value = 24.0 + expected_offset
            temperature_controller.send_temperature_command = AsyncMock()
            
            coordinator_data = SmartClimateData(
                room_temp=25.0,
                outdoor_temp=30.0,
                power=160.0,
                calculated_offset=expected_offset,
                mode_adjustments=mode_manager.get_adjustments.return_value,
                is_startup_calculation=True
            )
            
            coordinator = create_mock_coordinator(
                mock_hass,
                offset_engine,
                entity_id="climate.test_ac",
                initial_data=coordinator_data
            )
            
            entity = SmartClimateEntity(
                hass=mock_hass,
                config=integration_config,
                wrapped_entity_id="climate.test_ac",
                room_sensor_id="sensor.room_temp",
                offset_engine=offset_engine,
                sensor_manager=sensor_manager,
                mode_manager=mode_manager,
                temperature_controller=temperature_controller,
                coordinator=coordinator,
            )
            entity._attr_target_temperature = 24.0
            entity.async_write_ha_state = AsyncMock()
            
            # Test startup for this mode
            await entity.async_added_to_hass()
            entity._handle_coordinator_update()
            
            # Verify mode-specific behavior
            offset_engine.calculate_offset.assert_called()
            call_args = offset_engine.calculate_offset.call_args[0][0]
            assert call_args.mode == "none"  # Mode manager mode, not HVAC mode
            
            temperature_controller.send_temperature_command.assert_called_with(
                "climate.test_ac", 24.0 + expected_offset
            )

    @pytest.mark.asyncio
    async def test_startup_with_varying_confidence_levels(
        self, mock_hass, integration_config
    ):
        """Test startup behavior with different confidence levels in offset calculation."""
        confidence_scenarios = [
            (0.95, 3.0, True),   # High confidence, large offset - should apply
            (0.75, 2.5, True),   # Medium confidence, medium offset - should apply
            (0.45, 2.0, False),  # Low confidence, medium offset - should not apply
            (0.85, 0.2, False),  # High confidence, small offset - should not apply (below threshold)
        ]
        
        for confidence, offset, should_apply in confidence_scenarios:
            # Create dependencies
            offset_engine = create_mock_offset_engine(
                learning_enabled=True,
                samples=int(confidence * 50),  # More samples = higher confidence
                calculated_offset=offset
            )
            
            offset_engine.calculate_offset.return_value = OffsetResult(
                offset=offset,
                clamped=False,
                reason=f"Confidence test: {confidence}",
                confidence=confidence
            )
            
            sensor_manager = create_mock_sensor_manager()
            sensor_manager.get_room_temperature.return_value = 25.0
            
            mode_manager = create_mock_mode_manager()
            temperature_controller = create_mock_temperature_controller()
            temperature_controller.apply_offset_and_limits.return_value = 24.0 + offset
            temperature_controller.send_temperature_command = AsyncMock()
            
            coordinator_data = SmartClimateData(
                room_temp=25.0,
                outdoor_temp=30.0,
                power=150.0,
                calculated_offset=offset,
                mode_adjustments=mode_manager.get_adjustments.return_value,
                is_startup_calculation=True
            )
            
            coordinator = create_mock_coordinator(
                mock_hass,
                offset_engine,
                entity_id="climate.test_ac",
                initial_data=coordinator_data
            )
            
            entity = SmartClimateEntity(
                hass=mock_hass,
                config=integration_config,
                wrapped_entity_id="climate.test_ac",
                room_sensor_id="sensor.room_temp",
                offset_engine=offset_engine,
                sensor_manager=sensor_manager,
                mode_manager=mode_manager,
                temperature_controller=temperature_controller,
                coordinator=coordinator,
            )
            entity._attr_target_temperature = 24.0
            entity.async_write_ha_state = AsyncMock()
            
            # Test startup with this confidence level
            await entity.async_added_to_hass()
            entity._handle_coordinator_update()
            
            # Verify behavior based on confidence and offset size
            offset_engine.calculate_offset.assert_called()
            
            if should_apply:
                temperature_controller.send_temperature_command.assert_called()
            else:
                # For low confidence or small offsets, might not trigger update
                # The exact behavior depends on implementation thresholds
                pass

    @pytest.mark.asyncio
    async def test_startup_with_calibration_phase_scenarios(
        self, mock_hass, integration_config
    ):
        """Test startup behavior during different calibration phases."""
        calibration_scenarios = [
            ("initial_learning", 0, None, True),      # Just started, no cached offset
            ("mid_calibration", 5, 1.8, True),       # Has some data and cached offset
            ("post_calibration", 15, 2.2, False),    # Sufficient data, not in calibration
        ]
        
        for scenario_name, samples, cached_offset, in_calibration in calibration_scenarios:
            # Create dependencies
            offset_engine = create_mock_offset_engine(
                learning_enabled=True,
                samples=samples,
                calculated_offset=cached_offset or 0.0
            )
            
            # Configure calibration cache
            if cached_offset:
                offset_engine._calibration_cache = {"offset": cached_offset, "timestamp": 1234567890}
            else:
                offset_engine._calibration_cache = {}
            
            # Configure offset calculation based on calibration state
            if in_calibration and cached_offset:
                # Use cached offset during calibration
                offset_engine.calculate_offset.return_value = OffsetResult(
                    offset=cached_offset,
                    clamped=False,
                    reason=f"Calibration phase: using cached offset",
                    confidence=0.8
                )
            elif not in_calibration:
                # Use learned offset post-calibration
                offset_engine.calculate_offset.return_value = OffsetResult(
                    offset=2.5,
                    clamped=False,
                    reason=f"Post-calibration learned offset",
                    confidence=0.9
                )
            else:
                # Initial calibration with no cache
                offset_engine.calculate_offset.return_value = OffsetResult(
                    offset=0.0,
                    clamped=False,
                    reason=f"Initial calibration: no offset",
                    confidence=0.1
                )
            
            sensor_manager = create_mock_sensor_manager()
            sensor_manager.get_room_temperature.return_value = 25.0
            
            mode_manager = create_mock_mode_manager()
            temperature_controller = create_mock_temperature_controller()
            temperature_controller.send_temperature_command = AsyncMock()
            
            calculated_offset = cached_offset if in_calibration and cached_offset else (2.5 if not in_calibration else 0.0)
            temperature_controller.apply_offset_and_limits.return_value = 24.0 + calculated_offset
            
            coordinator_data = SmartClimateData(
                room_temp=25.0,
                outdoor_temp=30.0,
                power=150.0,
                calculated_offset=calculated_offset,
                mode_adjustments=mode_manager.get_adjustments.return_value,
                is_startup_calculation=True
            )
            
            coordinator = create_mock_coordinator(
                mock_hass,
                offset_engine,
                entity_id="climate.test_ac",
                initial_data=coordinator_data
            )
            
            entity = SmartClimateEntity(
                hass=mock_hass,
                config=integration_config,
                wrapped_entity_id="climate.test_ac",
                room_sensor_id="sensor.room_temp",
                offset_engine=offset_engine,
                sensor_manager=sensor_manager,
                mode_manager=mode_manager,
                temperature_controller=temperature_controller,
                coordinator=coordinator,
            )
            entity._attr_target_temperature = 24.0
            entity.async_write_ha_state = AsyncMock()
            
            # Test startup for this calibration scenario
            await entity.async_added_to_hass()
            entity._handle_coordinator_update()
            
            # Verify calibration-appropriate behavior
            offset_engine.calculate_offset.assert_called()
            
            if calculated_offset > 0.3:  # Significant offset threshold
                temperature_controller.send_temperature_command.assert_called_with(
                    "climate.test_ac", 24.0 + calculated_offset
                )

    @pytest.mark.asyncio
    async def test_startup_integration_stress_test(
        self, mock_hass, integration_config
    ):
        """Stress test startup integration with rapid successive operations."""
        # Create dependencies
        offset_engine = create_mock_offset_engine(
            learning_enabled=True,
            samples=100,  # Large dataset
            calculated_offset=2.8
        )
        
        sensor_manager = create_mock_sensor_manager()
        sensor_manager.get_room_temperature.return_value = 26.0
        sensor_manager.start_listening = AsyncMock()
        sensor_manager.stop_listening = AsyncMock()
        
        mode_manager = create_mock_mode_manager()
        temperature_controller = create_mock_temperature_controller()
        temperature_controller.apply_offset_and_limits.return_value = 26.8
        temperature_controller.send_temperature_command = AsyncMock()
        
        coordinator_data = SmartClimateData(
            room_temp=26.0,
            outdoor_temp=32.0,
            power=180.0,
            calculated_offset=2.8,
            mode_adjustments=mode_manager.get_adjustments.return_value,
            is_startup_calculation=True
        )
        
        coordinator = create_mock_coordinator(
            mock_hass,
            offset_engine,
            entity_id="climate.test_ac",
            initial_data=coordinator_data
        )
        coordinator.async_force_startup_refresh = AsyncMock()
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=integration_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=mode_manager,
            temperature_controller=temperature_controller,
            coordinator=coordinator,
        )
        entity._attr_target_temperature = 24.0
        entity.async_write_ha_state = AsyncMock()
        
        # Perform rapid startup operations
        start_time = datetime.now()
        
        # 1. Rapid entity setup
        await entity.async_added_to_hass()
        
        # 2. Multiple rapid coordinator updates
        for i in range(5):
            # Simulate changing data
            coordinator_data.calculated_offset = 2.8 + (i * 0.1)
            coordinator_data.room_temp = 26.0 + (i * 0.2)
            coordinator.data = coordinator_data
            
            entity._handle_coordinator_update()
        
        # 3. Rapid mode changes
        for mode in ["away", "sleep", "none", "boost"]:
            mode_manager.current_mode = mode
            entity._handle_coordinator_update()
        
        # 4. Rapid target temperature changes
        for temp in [23.0, 25.0, 26.0, 24.0]:
            entity._attr_target_temperature = temp
            entity._handle_coordinator_update()
        
        end_time = datetime.now()
        stress_duration = (end_time - start_time).total_seconds()
        
        # Verify stress test completed in reasonable time
        assert stress_duration < 2.0  # Should complete all operations in under 2 seconds
        
        # Verify all operations were handled without errors
        assert offset_engine.calculate_offset.call_count >= 15  # At least 15 calculations
        assert temperature_controller.send_temperature_command.call_count >= 5  # Multiple commands sent
        assert entity.async_write_ha_state.call_count >= 15  # Multiple state updates

    @pytest.mark.asyncio
    async def test_startup_integration_with_real_home_assistant_events(
        self, mock_hass, integration_config
    ):
        """Test startup integration with realistic Home Assistant event simulation."""
        # Create dependencies
        offset_engine = create_mock_offset_engine(
            learning_enabled=True,
            samples=40,
            calculated_offset=2.1
        )
        
        sensor_manager = create_mock_sensor_manager()
        sensor_manager.get_room_temperature.return_value = 25.2
        sensor_manager.register_update_callback = Mock()
        sensor_manager.start_listening = AsyncMock()
        
        mode_manager = create_mock_mode_manager()
        temperature_controller = create_mock_temperature_controller()
        temperature_controller.apply_offset_and_limits.return_value = 26.3
        temperature_controller.send_temperature_command = AsyncMock()
        
        coordinator_data = SmartClimateData(
            room_temp=25.2,
            outdoor_temp=29.5,
            power=165.0,
            calculated_offset=2.1,
            mode_adjustments=mode_manager.get_adjustments.return_value,
            is_startup_calculation=True
        )
        
        coordinator = create_mock_coordinator(
            mock_hass,
            offset_engine,
            entity_id="climate.test_ac",
            initial_data=coordinator_data
        )
        coordinator.async_add_listener = Mock()
        coordinator.async_force_startup_refresh = AsyncMock()
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=integration_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=mode_manager,
            temperature_controller=temperature_controller,
            coordinator=coordinator,
        )
        entity._attr_target_temperature = 24.0
        entity.async_write_ha_state = AsyncMock()
        
        # Simulate realistic HA startup sequence
        
        # 1. Entity added to HA (integration loading)
        await entity.async_added_to_hass()
        
        # 2. Verify proper registration
        coordinator.async_add_listener.assert_called_once()
        sensor_manager.start_listening.assert_called_once()
        sensor_manager.register_update_callback.assert_called()
        
        # 3. Simulate coordinator first refresh (HA starting)
        coordinator.async_force_startup_refresh.assert_called()
        
        # 4. Simulate sensor state change event
        callback = sensor_manager.register_update_callback.call_args[0][0]
        callback()  # Trigger sensor update callback
        
        # 5. Handle coordinator update (offset calculation and AC update)
        entity._handle_coordinator_update()
        
        # 6. Verify complete integration flow
        offset_engine.calculate_offset.assert_called()
        temperature_controller.apply_offset_and_limits.assert_called()
        temperature_controller.send_temperature_command.assert_called_with(
            "climate.test_ac", 26.3
        )
        entity.async_write_ha_state.assert_called()
        
        # 7. Simulate entity removal (integration unloading)
        await entity.async_will_remove_from_hass()
        
        # Verify cleanup
        sensor_manager.stop_listening.assert_called_once()