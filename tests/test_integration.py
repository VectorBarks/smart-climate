"""Integration tests for Smart Climate Control system."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.const import Platform

from custom_components.smart_climate.const import DOMAIN
from custom_components.smart_climate.models import OffsetResult, ModeAdjustments
from custom_components.smart_climate.errors import SmartClimateError


@pytest.fixture
def integration_config():
    """Configuration for integration tests."""
    return {
        "climate_entity": "climate.test_ac",
        "room_sensor": "sensor.room_temp",
        "outdoor_sensor": "sensor.outdoor_temp",
        "power_sensor": "sensor.power_consumption",
        "max_offset": 5.0,
        "min_temperature": 16.0,
        "max_temperature": 30.0,
        "update_interval": 180,
        "ml_enabled": True
    }


@pytest.fixture
def mock_config_entry(integration_config):
    """Mock config entry for integration tests."""
    entry = Mock()
    entry.entry_id = "test_entry_id"
    entry.data = integration_config
    return entry


class TestFullSystemIntegration:
    """Test complete system integration from config entry to entity."""

    @pytest.mark.asyncio
    async def test_full_setup_from_config_entry(self, hass: HomeAssistant, mock_config_entry):
        """Test complete setup from config entry creates all components."""
        # Mock the climate platform setup
        with patch('custom_components.smart_climate.async_setup_entry') as mock_setup:
            mock_setup.return_value = True
            
            # Import and call the actual setup
            from custom_components.smart_climate import async_setup_entry
            result = await async_setup_entry(hass, mock_config_entry)
            
            # Verify setup succeeded
            assert result is True
            
            # Verify domain data is stored
            assert DOMAIN in hass.data
            assert mock_config_entry.entry_id in hass.data[DOMAIN]
            assert hass.data[DOMAIN][mock_config_entry.entry_id] == mock_config_entry.data

    @pytest.mark.asyncio
    async def test_climate_entity_creation_with_all_components(self, hass: HomeAssistant, integration_config):
        """Test that climate entity is created with all components properly wired."""
        # Mock all required sensors
        hass.states.async_set("climate.test_ac", "cool", {
            "current_temperature": 24.0,
            "temperature": 22.0,
            "hvac_modes": ["off", "cool", "heat", "auto"]
        })
        hass.states.async_set("sensor.room_temp", "23.5")
        hass.states.async_set("sensor.outdoor_temp", "30.0")
        hass.states.async_set("sensor.power_consumption", "1500")
        
        # Mock the component creation
        with patch('custom_components.smart_climate.climate.async_setup_entry') as mock_climate_setup:
            mock_entity = Mock()
            mock_entity.entity_id = "climate.smart_climate_test"
            mock_entity.name = "Smart Climate Test"
            mock_entity.current_temperature = 23.5
            mock_entity.target_temperature = 22.0
            mock_entity.preset_mode = "none"
            mock_entity.preset_modes = ["none", "away", "sleep", "boost"]
            
            mock_climate_setup.return_value = True
            
            # Create the entity should work
            from custom_components.smart_climate.climate import SmartClimateEntity
            from custom_components.smart_climate.offset_engine import OffsetEngine
            from custom_components.smart_climate.sensor_manager import SensorManager
            from custom_components.smart_climate.mode_manager import ModeManager
            from custom_components.smart_climate.temperature_controller import TemperatureController
            from custom_components.smart_climate.coordinator import SmartClimateCoordinator
            
            # Mock all dependencies
            offset_engine = Mock(spec=OffsetEngine)
            sensor_manager = Mock(spec=SensorManager)
            mode_manager = Mock(spec=ModeManager)
            temperature_controller = Mock(spec=TemperatureController)
            coordinator = Mock(spec=SmartClimateCoordinator)
            
            # Create entity
            entity = SmartClimateEntity(
                hass=hass,
                config=integration_config,
                wrapped_entity_id="climate.test_ac",
                room_sensor_id="sensor.room_temp",
                offset_engine=offset_engine,
                sensor_manager=sensor_manager,
                mode_manager=mode_manager,
                temperature_controller=temperature_controller,
                coordinator=coordinator
            )
            
            # Verify entity was created properly
            assert entity is not None
            assert entity._wrapped_entity_id == "climate.test_ac"
            assert entity._room_sensor_id == "sensor.room_temp"


class TestClimateControlWithOffset:
    """Test climate control with offset calculation."""

    @pytest.mark.asyncio
    async def test_temperature_setting_with_offset_calculation(self, hass: HomeAssistant, integration_config):
        """Test setting temperature triggers offset calculation and applies to wrapped entity."""
        from custom_components.smart_climate.climate import SmartClimateEntity
        from custom_components.smart_climate.models import OffsetInput
        
        # Mock dependencies
        offset_engine = Mock()
        offset_engine.calculate_offset.return_value = OffsetResult(
            offset=2.0,
            clamped=False,
            reason="Room 2°C warmer than AC sensor",
            confidence=0.9
        )
        
        sensor_manager = Mock()
        sensor_manager.get_room_temperature.return_value = 24.0
        sensor_manager.get_outdoor_temperature.return_value = 30.0
        sensor_manager.get_power_consumption.return_value = 1500.0
        
        mode_manager = Mock()
        mode_manager.current_mode = "none"
        mode_manager.get_adjustments.return_value = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        )
        
        temperature_controller = Mock()
        temperature_controller.apply_offset_and_limits.return_value = 20.0
        temperature_controller.send_temperature_command = AsyncMock()
        
        coordinator = Mock()
        
        # Mock wrapped entity state
        hass.states.async_set("climate.test_ac", "cool", {
            "current_temperature": 22.0,
            "temperature": 22.0,
            "hvac_modes": ["off", "cool", "heat", "auto"]
        })
        
        # Create entity
        entity = SmartClimateEntity(
            hass=hass,
            config=integration_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=mode_manager,
            temperature_controller=temperature_controller,
            coordinator=coordinator
        )
        
        # Set target temperature
        await entity.async_set_temperature(temperature=22.0)
        
        # Verify offset was calculated
        offset_engine.calculate_offset.assert_called_once()
        call_args = offset_engine.calculate_offset.call_args[0][0]
        assert isinstance(call_args, OffsetInput)
        assert call_args.room_temp == 24.0
        assert call_args.ac_internal_temp == 22.0
        
        # Verify temperature was applied with offset
        temperature_controller.apply_offset_and_limits.assert_called_once()
        temperature_controller.send_temperature_command.assert_called_once_with(
            "climate.test_ac", 20.0
        )

    @pytest.mark.asyncio
    async def test_sensor_unavailable_fallback(self, hass: HomeAssistant, integration_config):
        """Test system continues to work when sensors are unavailable."""
        from custom_components.smart_climate.climate import SmartClimateEntity
        
        # Mock dependencies with unavailable sensors
        offset_engine = Mock()
        
        sensor_manager = Mock()
        sensor_manager.get_room_temperature.return_value = None  # Unavailable
        sensor_manager.get_outdoor_temperature.return_value = None
        sensor_manager.get_power_consumption.return_value = None
        
        mode_manager = Mock()
        mode_manager.current_mode = "none"
        
        temperature_controller = Mock()
        temperature_controller.send_temperature_command = AsyncMock()
        
        coordinator = Mock()
        
        # Mock wrapped entity state
        hass.states.async_set("climate.test_ac", "cool", {
            "current_temperature": 22.0,
            "temperature": 22.0,
            "hvac_modes": ["off", "cool", "heat", "auto"]
        })
        
        # Create entity
        entity = SmartClimateEntity(
            hass=hass,
            config=integration_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=mode_manager,
            temperature_controller=temperature_controller,
            coordinator=coordinator
        )
        
        # Set target temperature
        await entity.async_set_temperature(temperature=22.0)
        
        # Verify offset calculation was NOT called (no sensor data)
        offset_engine.calculate_offset.assert_not_called()
        
        # Verify temperature was sent directly to wrapped entity
        temperature_controller.send_temperature_command.assert_called_once_with(
            "climate.test_ac", 22.0
        )


class TestModeSwitchingEffects:
    """Test mode switching and its effects on climate control."""

    @pytest.mark.asyncio
    async def test_mode_change_triggers_temperature_adjustment(self, hass: HomeAssistant, integration_config):
        """Test that changing modes triggers appropriate temperature adjustments."""
        from custom_components.smart_climate.climate import SmartClimateEntity
        
        # Mock dependencies
        offset_engine = Mock()
        offset_engine.calculate_offset.return_value = OffsetResult(
            offset=1.0, clamped=False, reason="Normal", confidence=0.8
        )
        
        sensor_manager = Mock()
        sensor_manager.get_room_temperature.return_value = 24.0
        sensor_manager.get_outdoor_temperature.return_value = 30.0
        
        mode_manager = Mock()
        mode_manager.current_mode = "none"
        mode_manager.get_adjustments.return_value = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        )
        
        temperature_controller = Mock()
        temperature_controller.apply_offset_and_limits.return_value = 21.0
        temperature_controller.send_temperature_command = AsyncMock()
        
        coordinator = Mock()
        
        # Mock wrapped entity
        hass.states.async_set("climate.test_ac", "cool", {
            "current_temperature": 22.0,
            "temperature": 22.0,
            "hvac_modes": ["off", "cool", "heat", "auto"]
        })
        
        # Create entity
        entity = SmartClimateEntity(
            hass=hass,
            config=integration_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=mode_manager,
            temperature_controller=temperature_controller,
            coordinator=coordinator
        )
        
        # Set initial temperature
        await entity.async_set_temperature(temperature=22.0)
        
        # Change mode to "away" - should use fixed temperature
        mode_manager.current_mode = "away"
        mode_manager.get_adjustments.return_value = ModeAdjustments(
            temperature_override=18.0,  # Fixed away temperature
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        )
        
        await entity.async_set_preset_mode("away")
        
        # Verify mode change was handled
        mode_manager.set_mode.assert_called_with("away")

    @pytest.mark.asyncio
    async def test_boost_mode_applies_extra_cooling(self, hass: HomeAssistant, integration_config):
        """Test that boost mode applies extra cooling offset."""
        from custom_components.smart_climate.climate import SmartClimateEntity
        
        # Mock dependencies
        offset_engine = Mock()
        offset_engine.calculate_offset.return_value = OffsetResult(
            offset=1.0, clamped=False, reason="Normal", confidence=0.8
        )
        
        sensor_manager = Mock()
        sensor_manager.get_room_temperature.return_value = 26.0
        sensor_manager.get_outdoor_temperature.return_value = 35.0
        
        mode_manager = Mock()
        mode_manager.current_mode = "boost"
        mode_manager.get_adjustments.return_value = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=2.0  # Extra cooling
        )
        
        temperature_controller = Mock()
        temperature_controller.apply_offset_and_limits.return_value = 19.0  # Lower due to boost
        temperature_controller.send_temperature_command = AsyncMock()
        
        coordinator = Mock()
        
        # Mock wrapped entity
        hass.states.async_set("climate.test_ac", "cool", {
            "current_temperature": 24.0,
            "temperature": 22.0,
            "hvac_modes": ["off", "cool", "heat", "auto"]
        })
        
        # Create entity
        entity = SmartClimateEntity(
            hass=hass,
            config=integration_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=mode_manager,
            temperature_controller=temperature_controller,
            coordinator=coordinator
        )
        
        # Set temperature in boost mode
        await entity.async_set_temperature(temperature=22.0)
        
        # Verify boost adjustment was applied
        temperature_controller.apply_offset_and_limits.assert_called_once()
        call_args = temperature_controller.apply_offset_and_limits.call_args[0]
        mode_adjustments = call_args[2]
        assert mode_adjustments.boost_offset == 2.0


class TestManualOverrides:
    """Test manual override functionality."""

    @pytest.mark.asyncio
    async def test_manual_override_disables_offset(self, hass: HomeAssistant, integration_config):
        """Test that manual override disables offset calculation."""
        from custom_components.smart_climate.climate import SmartClimateEntity
        
        # Mock dependencies
        offset_engine = Mock()
        
        sensor_manager = Mock()
        sensor_manager.get_room_temperature.return_value = 24.0
        
        mode_manager = Mock()
        mode_manager.current_mode = "none"
        
        temperature_controller = Mock()
        temperature_controller.send_temperature_command = AsyncMock()
        
        coordinator = Mock()
        
        # Mock wrapped entity
        hass.states.async_set("climate.test_ac", "cool", {
            "current_temperature": 22.0,
            "temperature": 22.0,
            "hvac_modes": ["off", "cool", "heat", "auto"]
        })
        
        # Create entity with manual override
        entity = SmartClimateEntity(
            hass=hass,
            config=integration_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=mode_manager,
            temperature_controller=temperature_controller,
            coordinator=coordinator
        )
        
        # Simulate manual override active
        from custom_components.smart_climate.models import ManualOverride
        entity._manual_override = ManualOverride(
            active=True,
            temperature_offset=0.0,
            expires_at=None
        )
        
        # Set temperature
        await entity.async_set_temperature(temperature=22.0)
        
        # Verify offset engine was NOT called
        offset_engine.calculate_offset.assert_not_called()
        
        # Verify temperature was sent directly
        temperature_controller.send_temperature_command.assert_called_once_with(
            "climate.test_ac", 22.0
        )


class TestSensorUpdatePropagation:
    """Test sensor update propagation through the system."""

    @pytest.mark.asyncio
    async def test_sensor_update_triggers_coordinator_refresh(self, hass: HomeAssistant, integration_config):
        """Test that sensor updates trigger coordinator refresh."""
        from custom_components.smart_climate.climate import SmartClimateEntity
        
        # Mock dependencies
        offset_engine = Mock()
        
        sensor_manager = Mock()
        sensor_manager.get_room_temperature.return_value = 24.0
        sensor_manager.start_listening = AsyncMock()
        sensor_manager.stop_listening = AsyncMock()
        
        mode_manager = Mock()
        temperature_controller = Mock()
        
        coordinator = Mock()
        coordinator.async_add_listener = Mock()
        
        # Create entity
        entity = SmartClimateEntity(
            hass=hass,
            config=integration_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=mode_manager,
            temperature_controller=temperature_controller,
            coordinator=coordinator
        )
        
        # Simulate adding to hass
        await entity.async_added_to_hass()
        
        # Verify sensor manager started listening
        sensor_manager.start_listening.assert_called_once()
        
        # Verify coordinator listener was added
        coordinator.async_add_listener.assert_called_once()
        
        # Simulate removing from hass
        await entity.async_will_remove_from_hass()
        
        # Verify sensor manager stopped listening
        sensor_manager.stop_listening.assert_called_once()

    @pytest.mark.asyncio
    async def test_coordinator_update_triggers_entity_refresh(self, hass: HomeAssistant, integration_config):
        """Test that coordinator updates trigger entity state refresh."""
        from custom_components.smart_climate.climate import SmartClimateEntity
        
        # Mock dependencies
        offset_engine = Mock()
        sensor_manager = Mock()
        mode_manager = Mock()
        temperature_controller = Mock()
        coordinator = Mock()
        
        # Create entity
        entity = SmartClimateEntity(
            hass=hass,
            config=integration_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=mode_manager,
            temperature_controller=temperature_controller,
            coordinator=coordinator
        )
        
        # Mock the write_ha_state method
        entity.async_write_ha_state = AsyncMock()
        
        # Simulate coordinator update
        await entity.async_added_to_hass()
        
        # Get the callback that was registered
        callback = coordinator.async_add_listener.call_args[0][0]
        
        # Call the callback (simulating coordinator update)
        callback()
        
        # Verify entity state was updated
        entity.async_write_ha_state.assert_called_once()


class TestSystemEndToEndFunctionality:
    """Test complete end-to-end system functionality."""

    @pytest.mark.asyncio
    async def test_complete_temperature_control_flow(self, hass: HomeAssistant, integration_config):
        """Test complete flow from user input to AC control."""
        from custom_components.smart_climate.climate import SmartClimateEntity
        from custom_components.smart_climate.models import OffsetInput
        
        # Mock all dependencies for realistic flow
        offset_engine = Mock()
        offset_engine.calculate_offset.return_value = OffsetResult(
            offset=1.5,
            clamped=False,
            reason="Room sensor reads 1.5°C higher",
            confidence=0.9
        )
        
        sensor_manager = Mock()
        sensor_manager.get_room_temperature.return_value = 23.5
        sensor_manager.get_outdoor_temperature.return_value = 28.0
        sensor_manager.get_power_consumption.return_value = 1200.0
        sensor_manager.start_listening = AsyncMock()
        sensor_manager.stop_listening = AsyncMock()
        
        mode_manager = Mock()
        mode_manager.current_mode = "none"
        mode_manager.get_adjustments.return_value = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        )
        
        temperature_controller = Mock()
        temperature_controller.apply_offset_and_limits.return_value = 20.5
        temperature_controller.send_temperature_command = AsyncMock()
        
        coordinator = Mock()
        coordinator.async_add_listener = Mock()
        
        # Mock wrapped entity state
        hass.states.async_set("climate.test_ac", "cool", {
            "current_temperature": 22.0,
            "temperature": 22.0,
            "hvac_modes": ["off", "cool", "heat", "auto"]
        })
        
        # Create entity
        entity = SmartClimateEntity(
            hass=hass,
            config=integration_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=mode_manager,
            temperature_controller=temperature_controller,
            coordinator=coordinator
        )
        
        # Simulate complete lifecycle
        await entity.async_added_to_hass()
        
        # User sets temperature
        await entity.async_set_temperature(temperature=22.0)
        
        # Verify complete flow
        # 1. Sensor data was collected
        sensor_manager.get_room_temperature.assert_called()
        sensor_manager.get_outdoor_temperature.assert_called()
        sensor_manager.get_power_consumption.assert_called()
        
        # 2. Offset was calculated
        offset_engine.calculate_offset.assert_called_once()
        
        # 3. Temperature was adjusted and sent
        temperature_controller.apply_offset_and_limits.assert_called_once()
        temperature_controller.send_temperature_command.assert_called_once_with(
            "climate.test_ac", 20.5
        )
        
        # 4. Cleanup
        await entity.async_will_remove_from_hass()
        sensor_manager.stop_listening.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_throughout_system(self, hass: HomeAssistant, integration_config):
        """Test error handling throughout the entire system."""
        from custom_components.smart_climate.climate import SmartClimateEntity
        from custom_components.smart_climate.errors import OffsetCalculationError
        
        # Mock dependencies with errors
        offset_engine = Mock()
        offset_engine.calculate_offset.side_effect = OffsetCalculationError("Calculation failed")
        
        sensor_manager = Mock()
        sensor_manager.get_room_temperature.return_value = 24.0
        sensor_manager.get_outdoor_temperature.return_value = 30.0
        
        mode_manager = Mock()
        mode_manager.current_mode = "none"
        
        temperature_controller = Mock()
        temperature_controller.send_temperature_command = AsyncMock()
        
        coordinator = Mock()
        
        # Mock wrapped entity
        hass.states.async_set("climate.test_ac", "cool", {
            "current_temperature": 22.0,
            "temperature": 22.0,
            "hvac_modes": ["off", "cool", "heat", "auto"]
        })
        
        # Create entity
        entity = SmartClimateEntity(
            hass=hass,
            config=integration_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=mode_manager,
            temperature_controller=temperature_controller,
            coordinator=coordinator
        )
        
        # Try to set temperature (should handle error gracefully)
        await entity.async_set_temperature(temperature=22.0)
        
        # Verify error was handled and fallback was used
        temperature_controller.send_temperature_command.assert_called_once_with(
            "climate.test_ac", 22.0  # Direct temperature, no offset
        )

    @pytest.mark.asyncio
    async def test_comprehensive_logging_throughout_system(self, hass: HomeAssistant, integration_config):
        """Test that comprehensive logging is present throughout the system."""
        from custom_components.smart_climate.climate import SmartClimateEntity
        
        # Mock dependencies
        offset_engine = Mock()
        offset_engine.calculate_offset.return_value = OffsetResult(
            offset=1.0, clamped=False, reason="Normal", confidence=0.8
        )
        
        sensor_manager = Mock()
        sensor_manager.get_room_temperature.return_value = 24.0
        sensor_manager.start_listening = AsyncMock()
        sensor_manager.stop_listening = AsyncMock()
        
        mode_manager = Mock()
        mode_manager.current_mode = "none"
        mode_manager.get_adjustments.return_value = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        )
        
        temperature_controller = Mock()
        temperature_controller.apply_offset_and_limits.return_value = 21.0
        temperature_controller.send_temperature_command = AsyncMock()
        
        coordinator = Mock()
        coordinator.async_add_listener = Mock()
        
        # Mock wrapped entity
        hass.states.async_set("climate.test_ac", "cool", {
            "current_temperature": 22.0,
            "temperature": 22.0,
            "hvac_modes": ["off", "cool", "heat", "auto"]
        })
        
        # Create entity
        entity = SmartClimateEntity(
            hass=hass,
            config=integration_config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=mode_manager,
            temperature_controller=temperature_controller,
            coordinator=coordinator
        )
        
        # Test logging throughout operations
        with patch('custom_components.smart_climate.climate._LOGGER') as mock_logger:
            # Lifecycle operations
            await entity.async_added_to_hass()
            await entity.async_set_temperature(temperature=22.0)
            await entity.async_will_remove_from_hass()
            
            # Verify logging occurred
            assert mock_logger.debug.called
            assert mock_logger.info.called or mock_logger.debug.called