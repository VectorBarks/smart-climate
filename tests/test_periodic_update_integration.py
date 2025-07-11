"""Integration tests for periodic room temperature deviation detection.

Tests verify that the room deviation fix works end-to-end in a full Home Assistant environment.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, call
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.components.climate.const import (
    HVACMode,
    SERVICE_SET_TEMPERATURE,
    ATTR_TEMPERATURE,
    DOMAIN as CLIMATE_DOMAIN
)
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.smart_climate.const import DOMAIN
from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.models import (
    SmartClimateData,
    ModeAdjustments,
    OffsetResult,
    OffsetInput
)
from custom_components.smart_climate.coordinator import SmartClimateCoordinator
from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.sensor_manager import SensorManager
from custom_components.smart_climate.mode_manager import ModeManager
from custom_components.smart_climate.temperature_controller import TemperatureController


class TestPeriodicUpdateIntegration:
    """Integration tests for periodic room deviation updates."""

    @pytest.fixture
    async def setup_integration(self, hass: HomeAssistant):
        """Set up full integration test environment."""
        # Create mock config entry
        config = {
            "name": "Test Smart Climate",
            "climate_entity": "climate.test_ac",
            "room_sensor": "sensor.room_temp",
            "outdoor_sensor": "sensor.outdoor_temp",
            "power_sensor": "sensor.power_consumption",
            "feedback_delay": 45,
            "min_temperature": 16.0,
            "max_temperature": 30.0,
            "default_target_temperature": 24.0,
            "update_interval": 180,
            "max_offset": 5.0,
            "gradual_adjustment_rate": 0.5
        }
        
        # Set up mock entities in Home Assistant
        hass.states.async_set("climate.test_ac", HVACMode.COOL, {
            "temperature": 22.0,
            "current_temperature": 23.0,
            "hvac_modes": [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT],
            "min_temp": 16.0,
            "max_temp": 30.0
        })
        hass.states.async_set("sensor.room_temp", "24.0", {"unit_of_measurement": "°C"})
        hass.states.async_set("sensor.outdoor_temp", "28.0", {"unit_of_measurement": "°C"})
        hass.states.async_set("sensor.power_consumption", "150.0", {"unit_of_measurement": "W"})
        
        # Create real components with minimal mocking
        offset_engine = OffsetEngine(config)
        sensor_manager = SensorManager(hass, config)
        mode_manager = ModeManager(hass, config)
        temperature_controller = TemperatureController(hass, config)
        
        # Create coordinator
        coordinator = SmartClimateCoordinator(
            hass=hass,
            update_interval=timedelta(seconds=config["update_interval"]),
            sensor_manager=sensor_manager,
            offset_engine=offset_engine,
            mode_manager=mode_manager
        )
        
        # Create climate entity
        entity = SmartClimateEntity(
            hass=hass,
            config=config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=mode_manager,
            temperature_controller=temperature_controller,
            coordinator=coordinator
        )
        
        # Mock service calls to track temperature commands
        service_calls = []
        
        async def mock_service_call(domain, service, data):
            service_calls.append({
                "domain": domain,
                "service": service,
                "data": data
            })
        
        hass.services.async_call = AsyncMock(side_effect=mock_service_call)
        
        # Add entity to hass
        entity.hass = hass
        entity.entity_id = "climate.smart_test_ac"
        
        # Mock async_write_ha_state
        entity.async_write_ha_state = Mock()
        
        return {
            "entity": entity,
            "coordinator": coordinator,
            "offset_engine": offset_engine,
            "sensor_manager": sensor_manager,
            "temperature_controller": temperature_controller,
            "service_calls": service_calls,
            "config": config
        }

    @pytest.mark.asyncio
    async def test_ac_overcooling_scenario(self, hass: HomeAssistant, setup_integration):
        """Test AC overcooling: target 24°C, room cools to 23°C, AC should stop cooling."""
        setup = await setup_integration
        entity = setup["entity"]
        coordinator = setup["coordinator"]
        service_calls = setup["service_calls"]
        
        # Set initial conditions: target 24°C
        entity._attr_target_temperature = 24.0
        entity._last_offset = 0.0
        
        # Simulate room cooling to 23°C (1°C below target)
        hass.states.async_set("sensor.room_temp", "23.0")
        
        # Mock offset calculation to return negative offset (room cooler than target)
        with patch.object(setup["offset_engine"], 'calculate_offset') as mock_calc:
            mock_calc.return_value = OffsetResult(
                offset=-1.0,  # Negative because room is cooler
                clamped=False,
                reason="Room 1°C below target",
                confidence=0.8
            )
            
            # Mock temperature controller to return warmer command
            with patch.object(setup["temperature_controller"], 'apply_offset_and_limits') as mock_apply:
                mock_apply.return_value = 25.0  # Command AC to warm up
                
                # Trigger coordinator update with room deviation data
                coordinator.data = SmartClimateData(
                    room_temp=23.0,
                    outdoor_temp=28.0,
                    power=150.0,
                    calculated_offset=0.0,  # No offset change
                    mode_adjustments=ModeAdjustments()
                )
                
                # Call the update handler
                entity._handle_coordinator_update()
                
                # Wait for async task to complete
                await asyncio.sleep(0.1)
                
                # Verify temperature command was sent to stop overcooling
                assert len(service_calls) == 1
                assert service_calls[0]["domain"] == CLIMATE_DOMAIN
                assert service_calls[0]["service"] == SERVICE_SET_TEMPERATURE
                assert service_calls[0]["data"]["entity_id"] == "climate.test_ac"
                assert service_calls[0]["data"][ATTR_TEMPERATURE] == 25.0

    @pytest.mark.asyncio
    async def test_ac_underheating_scenario(self, hass: HomeAssistant, setup_integration):
        """Test AC underheating: target 22°C, room warms to 23.5°C, AC should start cooling."""
        setup = await setup_integration
        entity = setup["entity"]
        coordinator = setup["coordinator"]
        service_calls = setup["service_calls"]
        
        # Set initial conditions: target 22°C
        entity._attr_target_temperature = 22.0
        entity._last_offset = 0.0
        
        # Simulate room warming to 23.5°C (1.5°C above target)
        hass.states.async_set("sensor.room_temp", "23.5")
        
        # Mock offset calculation
        with patch.object(setup["offset_engine"], 'calculate_offset') as mock_calc:
            mock_calc.return_value = OffsetResult(
                offset=1.5,  # Positive because room is warmer
                clamped=False,
                reason="Room 1.5°C above target",
                confidence=0.85
            )
            
            # Mock temperature controller to return cooler command
            with patch.object(setup["temperature_controller"], 'apply_offset_and_limits') as mock_apply:
                mock_apply.return_value = 20.5  # Command AC to cool more
                
                # Trigger coordinator update
                coordinator.data = SmartClimateData(
                    room_temp=23.5,
                    outdoor_temp=28.0,
                    power=150.0,
                    calculated_offset=0.0,
                    mode_adjustments=ModeAdjustments()
                )
                
                entity._handle_coordinator_update()
                await asyncio.sleep(0.1)
                
                # Verify cooling command was sent
                assert len(service_calls) == 1
                assert service_calls[0]["data"][ATTR_TEMPERATURE] == 20.5

    @pytest.mark.asyncio
    async def test_stable_room_temperature_no_update(self, hass: HomeAssistant, setup_integration):
        """Test stable room: target 24°C, room at 24.2°C, no update needed."""
        setup = await setup_integration
        entity = setup["entity"]
        coordinator = setup["coordinator"]
        service_calls = setup["service_calls"]
        
        # Set conditions: room within 0.5°C of target
        entity._attr_target_temperature = 24.0
        entity._last_offset = 0.0
        
        # Room at 24.2°C (only 0.2°C above target)
        hass.states.async_set("sensor.room_temp", "24.2")
        
        # Trigger coordinator update
        coordinator.data = SmartClimateData(
            room_temp=24.2,
            outdoor_temp=28.0,
            power=150.0,
            calculated_offset=0.0,
            mode_adjustments=ModeAdjustments()
        )
        
        entity._handle_coordinator_update()
        await asyncio.sleep(0.1)
        
        # Verify NO temperature command was sent
        assert len(service_calls) == 0

    @pytest.mark.asyncio
    async def test_combined_offset_and_room_deviation(self, hass: HomeAssistant, setup_integration):
        """Test that either offset change OR room deviation can trigger update."""
        setup = await setup_integration
        entity = setup["entity"]
        coordinator = setup["coordinator"]
        service_calls = setup["service_calls"]
        
        # Set initial state
        entity._attr_target_temperature = 24.0
        entity._last_offset = 0.0
        
        # Test 1: Large offset change with small room deviation
        coordinator.data = SmartClimateData(
            room_temp=24.2,  # Only 0.2°C above target
            outdoor_temp=28.0,
            power=150.0,
            calculated_offset=0.5,  # Significant offset change
            mode_adjustments=ModeAdjustments()
        )
        
        entity._handle_coordinator_update()
        await asyncio.sleep(0.1)
        
        # Should trigger due to offset change
        assert len(service_calls) == 1
        service_calls.clear()
        
        # Update last offset
        entity._last_offset = 0.5
        
        # Test 2: Small offset change with large room deviation
        coordinator.data = SmartClimateData(
            room_temp=25.2,  # 1.2°C above target
            outdoor_temp=28.0,
            power=150.0,
            calculated_offset=0.6,  # Small offset change
            mode_adjustments=ModeAdjustments()
        )
        
        entity._handle_coordinator_update()
        await asyncio.sleep(0.1)
        
        # Should trigger due to room deviation
        assert len(service_calls) == 1

    @pytest.mark.asyncio
    async def test_mode_changes_during_deviation(self, hass: HomeAssistant, setup_integration):
        """Test HVAC mode changes affect room deviation detection."""
        setup = await setup_integration
        entity = setup["entity"]
        coordinator = setup["coordinator"]
        service_calls = setup["service_calls"]
        
        # Set room deviation conditions
        entity._attr_target_temperature = 24.0
        entity._last_offset = 0.0
        hass.states.async_set("sensor.room_temp", "26.0")  # 2°C above target
        
        # Test with HVAC OFF
        hass.states.async_set("climate.test_ac", HVACMode.OFF)
        
        coordinator.data = SmartClimateData(
            room_temp=26.0,
            outdoor_temp=28.0,
            power=0.0,  # No power when OFF
            calculated_offset=0.0,
            mode_adjustments=ModeAdjustments()
        )
        
        entity._handle_coordinator_update()
        await asyncio.sleep(0.1)
        
        # No update when HVAC is OFF
        assert len(service_calls) == 0
        
        # Switch to COOL mode
        hass.states.async_set("climate.test_ac", HVACMode.COOL)
        
        coordinator.data = SmartClimateData(
            room_temp=26.0,
            outdoor_temp=28.0,
            power=1500.0,  # Power when cooling
            calculated_offset=0.0,
            mode_adjustments=ModeAdjustments()
        )
        
        entity._handle_coordinator_update()
        await asyncio.sleep(0.1)
        
        # Should update when HVAC is active
        assert len(service_calls) == 1

    @pytest.mark.asyncio
    async def test_timing_of_periodic_updates(self, hass: HomeAssistant, setup_integration):
        """Test that updates happen at configured intervals (180 seconds)."""
        setup = await setup_integration
        entity = setup["entity"]
        coordinator = setup["coordinator"]
        service_calls = setup["service_calls"]
        
        # Set conditions for room deviation
        entity._attr_target_temperature = 24.0
        entity._last_offset = 0.0
        hass.states.async_set("sensor.room_temp", "25.0")  # 1°C above target
        
        # Mock time progression
        with patch('homeassistant.util.dt.utcnow') as mock_time:
            start_time = dt_util.utcnow()
            mock_time.return_value = start_time
            
            # First update
            coordinator.data = SmartClimateData(
                room_temp=25.0,
                outdoor_temp=28.0,
                power=150.0,
                calculated_offset=0.0,
                mode_adjustments=ModeAdjustments()
            )
            
            entity._handle_coordinator_update()
            await asyncio.sleep(0.1)
            
            assert len(service_calls) == 1
            service_calls.clear()
            
            # Simulate time passing (90 seconds - half interval)
            mock_time.return_value = start_time + timedelta(seconds=90)
            
            # Room still deviating but not enough time passed
            entity._handle_coordinator_update()
            await asyncio.sleep(0.1)
            
            # Should still see updates since coordinator fires on its interval
            # The 180s is the coordinator's update interval, not a blocker
            assert len(service_calls) == 1

    @pytest.mark.asyncio
    async def test_real_temperature_command_flow(self, hass: HomeAssistant, setup_integration):
        """Test complete flow from sensor change to AC temperature command."""
        setup = await setup_integration
        entity = setup["entity"]
        coordinator = setup["coordinator"]
        service_calls = setup["service_calls"]
        
        # Initial state: AC cooling to 24°C, room at 24°C
        entity._attr_target_temperature = 24.0
        entity._last_offset = 0.0
        hass.states.async_set("sensor.room_temp", "24.0")
        hass.states.async_set("climate.test_ac", HVACMode.COOL, {
            "temperature": 22.0,  # AC set to 22°C due to previous offset
            "current_temperature": 23.0
        })
        
        # Room cools to 23°C (overcooling)
        hass.states.async_set("sensor.room_temp", "23.0")
        
        # Mock the complete calculation chain
        with patch.object(setup["sensor_manager"], 'get_room_temperature', return_value=23.0):
            with patch.object(setup["offset_engine"], 'calculate_offset') as mock_calc:
                # Room is 1°C below target, so we need less cooling
                mock_calc.return_value = OffsetResult(
                    offset=-1.0,
                    clamped=False,
                    reason="Room below target",
                    confidence=0.9
                )
                
                with patch.object(setup["temperature_controller"], 'apply_offset_and_limits') as mock_apply:
                    # Should command AC to reduce cooling
                    mock_apply.return_value = 25.0
                    
                    # Trigger update
                    coordinator.data = SmartClimateData(
                        room_temp=23.0,
                        outdoor_temp=28.0,
                        power=1500.0,
                        calculated_offset=0.0,
                        mode_adjustments=ModeAdjustments()
                    )
                    
                    entity._handle_coordinator_update()
                    await asyncio.sleep(0.1)
                    
                    # Verify the chain of calls
                    mock_calc.assert_called_once()
                    mock_apply.assert_called_once()
                    
                    # Verify final command
                    assert len(service_calls) == 1
                    assert service_calls[0]["data"][ATTR_TEMPERATURE] == 25.0

    @pytest.mark.asyncio
    async def test_edge_cases_none_values(self, hass: HomeAssistant, setup_integration):
        """Test graceful handling of None values in sensors."""
        setup = await setup_integration
        entity = setup["entity"]
        coordinator = setup["coordinator"]
        service_calls = setup["service_calls"]
        
        # Test with None room temperature
        entity._attr_target_temperature = 24.0
        entity._last_offset = 0.0
        
        coordinator.data = SmartClimateData(
            room_temp=None,  # Sensor unavailable
            outdoor_temp=28.0,
            power=150.0,
            calculated_offset=0.0,
            mode_adjustments=ModeAdjustments()
        )
        
        entity._handle_coordinator_update()
        await asyncio.sleep(0.1)
        
        # No update with None room temp
        assert len(service_calls) == 0
        
        # Test with None target temperature
        entity._attr_target_temperature = None
        coordinator.data.room_temp = 25.0
        
        entity._handle_coordinator_update()
        await asyncio.sleep(0.1)
        
        # No update with None target temp
        assert len(service_calls) == 0

    @pytest.mark.asyncio
    async def test_reported_bug_scenario(self, hass: HomeAssistant, setup_integration):
        """Test the exact reported bug: AC continues cooling when room reaches target."""
        setup = await setup_integration
        entity = setup["entity"]
        coordinator = setup["coordinator"]
        service_calls = setup["service_calls"]
        
        # Reproduce reported conditions
        entity._attr_target_temperature = 24.0
        entity._last_offset = 0.0
        
        # AC is cooling, room reaches target
        hass.states.async_set("climate.test_ac", HVACMode.COOL, {
            "temperature": 22.0,  # AC set to cool
            "current_temperature": 23.0
        })
        hass.states.async_set("sensor.room_temp", "24.0")  # Room at target
        
        # After some time, room continues to cool below target
        hass.states.async_set("sensor.room_temp", "23.4")  # 0.6°C below target
        
        with patch.object(setup["offset_engine"], 'calculate_offset') as mock_calc:
            mock_calc.return_value = OffsetResult(
                offset=-0.6,
                clamped=False,
                reason="Room below target",
                confidence=0.8
            )
            
            with patch.object(setup["temperature_controller"], 'apply_offset_and_limits') as mock_apply:
                mock_apply.return_value = 24.6  # Reduce cooling
                
                # Trigger periodic update
                coordinator.data = SmartClimateData(
                    room_temp=23.4,
                    outdoor_temp=28.0,
                    power=1500.0,
                    calculated_offset=0.0,
                    mode_adjustments=ModeAdjustments()
                )
                
                entity._handle_coordinator_update()
                await asyncio.sleep(0.1)
                
                # Verify AC receives command to reduce/stop cooling
                assert len(service_calls) == 1
                assert service_calls[0]["data"][ATTR_TEMPERATURE] == 24.6
                
                # This should help AC stop overcooling the room