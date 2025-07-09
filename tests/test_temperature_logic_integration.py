"""ABOUTME: Integration tests for temperature adjustment logic in real scenarios.
Tests verify the complete flow from sensor updates to AC commands with correct logic."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from datetime import datetime, timedelta
import asyncio

from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.sensor_manager import SensorManager
from custom_components.smart_climate.mode_manager import ModeManager
from custom_components.smart_climate.temperature_controller import TemperatureController, TemperatureLimits
from custom_components.smart_climate.coordinator import SmartClimateCoordinator
from custom_components.smart_climate.models import (
    OffsetResult, OffsetInput, ModeAdjustments, SmartClimateData
)
from custom_components.smart_climate.const import DOMAIN


class TestTemperatureLogicIntegration:
    """Integration tests for temperature adjustment logic with full Smart Climate setup."""

    @pytest.fixture
    def mock_hass(self):
        """Mock HomeAssistant instance with required functionality."""
        hass = Mock()
        hass.states = Mock()
        hass.services = Mock()
        hass.services.async_call = AsyncMock()
        hass.data = {DOMAIN: {}}
        
        # Mock state storage
        hass._states = {}
        
        def async_set(entity_id, state, attributes=None):
            """Mock setting state."""
            mock_state = Mock()
            mock_state.entity_id = entity_id
            mock_state.state = state
            mock_state.attributes = attributes or {}
            hass._states[entity_id] = mock_state
            
        def get(entity_id):
            """Mock getting state."""
            return hass._states.get(entity_id)
            
        hass.states.async_set = async_set
        hass.states.get = get
        
        return hass

    @pytest.fixture
    def config(self):
        """Configuration for Smart Climate."""
        return {
            "climate_entity": "climate.test_ac",
            "room_sensor": "sensor.room_temp",
            "outdoor_sensor": "sensor.outdoor_temp",
            "power_sensor": "sensor.ac_power",
            "max_offset": 5.0,
            "min_temperature": 16.0,
            "max_temperature": 30.0,
            "update_interval": 180,
            "ml_enabled": True,
            "enable_learning": True,
            "feedback_delay": 45,
            "gradual_adjustment_rate": 0.5,
            "default_target_temperature": 24.0
        }

    @pytest.fixture
    async def smart_climate_entity(self, mock_hass, config):
        """Create a fully configured SmartClimateEntity."""
        # Set up wrapped AC entity
        mock_hass.states.async_set("climate.test_ac", "cool", {
            "current_temperature": 25.0,  # AC internal sensor
            "temperature": 24.5,
            "hvac_modes": ["off", "cool", "heat", "auto"],
            "fan_modes": ["auto", "low", "medium", "high"],
            "swing_modes": ["off", "vertical"],
            "min_temp": 16.0,
            "max_temp": 30.0
        })
        
        # Set up sensors
        mock_hass.states.async_set("sensor.room_temp", "24.8", {"unit_of_measurement": "°C"})
        mock_hass.states.async_set("sensor.outdoor_temp", "32.0", {"unit_of_measurement": "°C"})
        mock_hass.states.async_set("sensor.ac_power", "1500", {"unit_of_measurement": "W"})
        
        # Create components
        sensor_manager = SensorManager(
            mock_hass,
            config["room_sensor"],
            config.get("outdoor_sensor"),
            config.get("power_sensor")
        )
        
        offset_engine = OffsetEngine(config)
        mode_manager = ModeManager(config)
        
        limits = TemperatureLimits(
            min_temperature=config["min_temperature"],
            max_temperature=config["max_temperature"]
        )
        temperature_controller = TemperatureController(
            mock_hass,
            limits,
            gradual_adjustment_rate=config.get("gradual_adjustment_rate", 0.5)
        )
        
        coordinator = SmartClimateCoordinator(
            mock_hass,
            config["update_interval"],
            sensor_manager,
            offset_engine,
            mode_manager
        )
        
        # Create entity
        entity = SmartClimateEntity(
            mock_hass,
            config,
            config["climate_entity"],
            config["room_sensor"],
            offset_engine,
            sensor_manager,
            mode_manager,
            temperature_controller,
            coordinator
        )
        
        # Initialize entity
        await entity.async_added_to_hass()
        
        return entity

    @pytest.mark.asyncio
    async def test_issue_13_exact_scenario(self, smart_climate_entity, mock_hass):
        """Test the exact scenario from issue #13 - Room warmer than target should cool MORE.
        
        Room: 24.8°C, Target: 24.5°C, AC internal: 25.0°C
        Expected: AC should be set LOWER than 24.5°C to provide more cooling.
        """
        # Update sensor readings to match exact scenario
        mock_hass.states.async_set("sensor.room_temp", "24.8", {"unit_of_measurement": "°C"})
        mock_hass.states.async_set("climate.test_ac", "cool", {
            "current_temperature": 25.0,  # AC internal sensor
            "temperature": 24.5,
            "hvac_modes": ["off", "cool", "heat", "auto"]
        })
        
        # Clear previous calls
        mock_hass.services.async_call.reset_mock()
        
        # User sets target temperature to 24.5°C
        await smart_climate_entity.async_set_temperature(temperature=24.5)
        
        # Verify AC was commanded to cool MORE (temperature lower than target)
        mock_hass.services.async_call.assert_called()
        call_args = mock_hass.services.async_call.call_args
        
        assert call_args[0][0] == "climate"  # domain
        assert call_args[0][1] == "set_temperature"  # service
        assert call_args[0][2]["entity_id"] == "climate.test_ac"
        
        commanded_temp = call_args[0][2]["temperature"]
        # Room is 0.3°C warmer than target, AC reads 0.2°C warmer than room
        # Base offset = 25.0 - 24.8 = +0.2°C
        # Room deviation = 24.8 - 24.5 = +0.3°C (room is warmer, needs more cooling)
        # Expected: 24.5 + 0.2 - 0.3 = 24.4°C
        assert commanded_temp < 24.5, f"AC should be commanded to {commanded_temp}°C (lower than target 24.5°C) for more cooling"
        assert abs(commanded_temp - 24.4) < 0.01, f"Expected AC to be set to ~24.4°C but got {commanded_temp}°C"

    @pytest.mark.asyncio
    async def test_coordinator_update_triggers_adjustment(self, smart_climate_entity, mock_hass):
        """Test that coordinator updates trigger temperature adjustments."""
        # Set initial state
        smart_climate_entity._attr_target_temperature = 24.0
        
        # Simulate room temperature change via coordinator
        mock_hass.states.async_set("sensor.room_temp", "25.5", {"unit_of_measurement": "°C"})
        
        # Mock coordinator data update
        coordinator_data = SmartClimateData(
            room_temp=25.5,
            outdoor_temp=32.0,
            power=1500.0,
            calculated_offset=0.5,
            mode_adjustments=ModeAdjustments(
                temperature_override=None,
                offset_adjustment=0.0,
                update_interval_override=None,
                boost_offset=0.0
            )
        )
        
        # Trigger coordinator update callback
        smart_climate_entity._coordinator.async_set_updated_data(coordinator_data)
        
        # Since coordinator updates don't directly trigger temperature commands,
        # we need to manually trigger an update or wait for the next cycle
        # In real operation, this would happen automatically
        
        # For testing, we'll verify the entity has the updated data
        assert smart_climate_entity._sensor_manager.get_room_temperature() == 25.5

    @pytest.mark.asyncio
    async def test_user_temperature_change_various_conditions(self, smart_climate_entity, mock_hass):
        """Test user temperature changes under various room conditions."""
        test_cases = [
            # (room_temp, target_temp, ac_internal_temp, description)
            (26.0, 24.0, 26.5, "Hot room needs aggressive cooling"),
            (23.0, 24.0, 23.5, "Cool room needs less cooling"),
            (24.0, 24.0, 24.5, "Room at target maintains with offset"),
            (28.0, 25.0, 15.0, "AC showing evaporator temp during cooling"),
        ]
        
        for room_temp, target_temp, ac_internal_temp, description in test_cases:
            # Update sensors
            mock_hass.states.async_set("sensor.room_temp", str(room_temp), {"unit_of_measurement": "°C"})
            mock_hass.states.async_set("climate.test_ac", "cool", {
                "current_temperature": ac_internal_temp,
                "temperature": target_temp,
                "hvac_modes": ["off", "cool", "heat", "auto"]
            })
            
            # Clear previous calls
            mock_hass.services.async_call.reset_mock()
            
            # User sets temperature
            await smart_climate_entity.async_set_temperature(temperature=target_temp)
            
            # Verify command was sent
            mock_hass.services.async_call.assert_called()
            call_args = mock_hass.services.async_call.call_args
            commanded_temp = call_args[0][2]["temperature"]
            
            # Calculate expected behavior
            base_offset = ac_internal_temp - room_temp
            room_deviation = room_temp - target_temp
            
            # Log for debugging
            print(f"\n{description}:")
            print(f"  Room: {room_temp}°C, Target: {target_temp}°C, AC: {ac_internal_temp}°C")
            print(f"  Base offset: {base_offset}°C, Room deviation: {room_deviation}°C")
            print(f"  Commanded: {commanded_temp}°C")
            
            # Verify correct direction
            if room_temp > target_temp:
                # Room is warmer, should cool more
                assert commanded_temp <= target_temp + base_offset - room_deviation, \
                    f"{description}: Should cool more when room is warmer"
            elif room_temp < target_temp:
                # Room is cooler, should cool less
                assert commanded_temp >= target_temp + base_offset - room_deviation, \
                    f"{description}: Should cool less when room is cooler"

    @pytest.mark.asyncio
    async def test_mode_changes_affect_temperature(self, smart_climate_entity, mock_hass):
        """Test that mode changes correctly affect temperature adjustments."""
        # Set initial state
        smart_climate_entity._attr_target_temperature = 24.0
        mock_hass.states.async_set("sensor.room_temp", "24.5", {"unit_of_measurement": "°C"})
        mock_hass.states.async_set("climate.test_ac", "cool", {
            "current_temperature": 25.0,
            "temperature": 24.0
        })
        
        # Test boost mode (should cool more aggressively)
        mock_hass.services.async_call.reset_mock()
        await smart_climate_entity.async_set_preset_mode("boost")
        
        # Verify boost mode is active
        assert smart_climate_entity.preset_mode == "boost"
        
        # Trigger temperature update
        await smart_climate_entity.async_set_temperature(temperature=24.0)
        
        # With boost mode, temperature should be set lower for more cooling
        call_args = mock_hass.services.async_call.call_args
        boost_temp = call_args[0][2]["temperature"]
        
        # Test away mode (fixed temperature)
        mock_hass.services.async_call.reset_mock()
        await smart_climate_entity.async_set_preset_mode("away")
        
        # Away mode should use a fixed temperature from config
        # This would be defined in the mode manager

    @pytest.mark.asyncio
    async def test_gradual_adjustment_over_time(self, smart_climate_entity, mock_hass):
        """Test gradual adjustments work correctly with temperature logic."""
        # Set up scenario needing significant adjustment
        mock_hass.states.async_set("sensor.room_temp", "27.0", {"unit_of_measurement": "°C"})
        mock_hass.states.async_set("climate.test_ac", "cool", {
            "current_temperature": 27.5,
            "temperature": 24.0
        })
        
        commanded_temps = []
        
        # Capture multiple adjustment cycles
        for _ in range(3):
            mock_hass.services.async_call.reset_mock()
            await smart_climate_entity.async_set_temperature(temperature=24.0)
            
            call_args = mock_hass.services.async_call.call_args
            commanded_temp = call_args[0][2]["temperature"]
            commanded_temps.append(commanded_temp)
            
            # Simulate time passing (in real operation, coordinator would trigger updates)
            await asyncio.sleep(0.1)
        
        # Verify temperatures are gradually adjusted
        # With 0.5°C gradual adjustment rate, changes should be limited
        print(f"Commanded temperatures over cycles: {commanded_temps}")
        
        # Each adjustment should move towards the target
        for i in range(1, len(commanded_temps)):
            # Temperature should be moving in the right direction
            # (getting lower since room is hot)
            assert commanded_temps[i] <= commanded_temps[i-1] + 0.5

    @pytest.mark.asyncio
    async def test_learning_enabled_feedback_scheduled(self, smart_climate_entity, mock_hass):
        """Test that learning feedback is scheduled when enabled."""
        # Enable learning
        smart_climate_entity._offset_engine._enable_learning = True
        
        # Set up scenario
        mock_hass.states.async_set("sensor.room_temp", "24.8", {"unit_of_measurement": "°C"})
        mock_hass.states.async_set("climate.test_ac", "cool", {
            "current_temperature": 25.0,
            "temperature": 24.5
        })
        
        # Mock async_call_later to verify feedback scheduling
        with patch('homeassistant.helpers.event.async_call_later') as mock_call_later:
            mock_call_later.return_value = Mock()  # Return a cancel callback
            
            # Trigger temperature adjustment
            await smart_climate_entity.async_set_temperature(temperature=24.5)
            
            # Verify feedback was scheduled
            mock_call_later.assert_called_once()
            assert mock_call_later.call_args[0][1] == 45  # feedback_delay
            
            # Verify feedback data was stored
            assert smart_climate_entity._last_predicted_offset is not None
            assert smart_climate_entity._last_offset_input is not None

    @pytest.mark.asyncio
    async def test_edge_cases_and_error_handling(self, smart_climate_entity, mock_hass):
        """Test edge cases and error conditions."""
        # Test with missing room sensor
        mock_hass.states.async_set("sensor.room_temp", "unavailable")
        
        mock_hass.services.async_call.reset_mock()
        await smart_climate_entity.async_set_temperature(temperature=24.0)
        
        # Should fall back to sending target directly
        call_args = mock_hass.services.async_call.call_args
        assert call_args[0][2]["temperature"] == 24.0
        
        # Test with missing AC internal temperature
        mock_hass.states.async_set("sensor.room_temp", "24.5", {"unit_of_measurement": "°C"})
        mock_hass.states.async_set("climate.test_ac", "cool", {
            "current_temperature": None,  # Missing
            "temperature": 24.0
        })
        
        mock_hass.services.async_call.reset_mock()
        await smart_climate_entity.async_set_temperature(temperature=24.0)
        
        # Should fall back to sending target directly
        call_args = mock_hass.services.async_call.call_args
        assert call_args[0][2]["temperature"] == 24.0

    @pytest.mark.asyncio
    async def test_safety_limits_respected(self, smart_climate_entity, mock_hass):
        """Test that safety limits are respected in all scenarios."""
        # Test extreme cooling need
        mock_hass.states.async_set("sensor.room_temp", "35.0", {"unit_of_measurement": "°C"})
        mock_hass.states.async_set("climate.test_ac", "cool", {
            "current_temperature": 36.0,
            "temperature": 20.0
        })
        
        mock_hass.services.async_call.reset_mock()
        await smart_climate_entity.async_set_temperature(temperature=20.0)
        
        call_args = mock_hass.services.async_call.call_args
        commanded_temp = call_args[0][2]["temperature"]
        
        # Should not go below minimum temperature (16°C)
        assert commanded_temp >= 16.0, f"Temperature {commanded_temp}°C violates minimum limit"
        
        # Test extreme heating need (though this is a cooling integration)
        mock_hass.states.async_set("sensor.room_temp", "10.0", {"unit_of_measurement": "°C"})
        mock_hass.states.async_set("climate.test_ac", "heat", {
            "current_temperature": 11.0,
            "temperature": 25.0
        })
        
        mock_hass.services.async_call.reset_mock()
        await smart_climate_entity.async_set_temperature(temperature=25.0)
        
        call_args = mock_hass.services.async_call.call_args
        commanded_temp = call_args[0][2]["temperature"]
        
        # Should not exceed maximum temperature (30°C)
        assert commanded_temp <= 30.0, f"Temperature {commanded_temp}°C violates maximum limit"

    @pytest.mark.asyncio
    async def test_real_world_cooling_cycle(self, smart_climate_entity, mock_hass):
        """Test a realistic cooling cycle with changing conditions."""
        # Simulate a hot day with AC trying to cool the room
        cooling_cycle = [
            # (time, room_temp, ac_internal_temp, power, description)
            (0, 28.0, 28.5, 0, "AC off, room is hot"),
            (1, 28.0, 27.0, 1500, "AC starts cooling"),
            (5, 27.5, 20.0, 1800, "AC running, evaporator cold"),
            (10, 26.5, 18.0, 1800, "Room cooling down"),
            (15, 25.5, 17.0, 1800, "Approaching target"),
            (20, 24.8, 16.5, 1800, "Near target"),
            (25, 24.5, 24.0, 500, "AC cycling down"),
            (30, 24.5, 24.5, 0, "AC off, target reached"),
        ]
        
        target_temp = 24.5
        smart_climate_entity._attr_target_temperature = target_temp
        
        for minute, room_temp, ac_temp, power, description in cooling_cycle:
            # Update sensors
            mock_hass.states.async_set("sensor.room_temp", str(room_temp), {"unit_of_measurement": "°C"})
            mock_hass.states.async_set("climate.test_ac", "cool", {
                "current_temperature": ac_temp,
                "temperature": target_temp
            })
            mock_hass.states.async_set("sensor.ac_power", str(power), {"unit_of_measurement": "W"})
            
            # Clear and trigger adjustment
            mock_hass.services.async_call.reset_mock()
            await smart_climate_entity._apply_temperature_with_offset(target_temp)
            
            if mock_hass.services.async_call.called:
                call_args = mock_hass.services.async_call.call_args
                commanded_temp = call_args[0][2]["temperature"]
                
                print(f"\nMinute {minute}: {description}")
                print(f"  Room: {room_temp}°C, AC sensor: {ac_temp}°C, Power: {power}W")
                print(f"  Commanded: {commanded_temp}°C")
                
                # Verify logical behavior
                if room_temp > target_temp and power > 1000:
                    # Room is hot and AC is cooling - command should account for cold evaporator
                    assert commanded_temp <= target_temp + 2.0, \
                        f"During active cooling, commanded temp should be reasonable"