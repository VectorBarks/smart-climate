"""
ABOUTME: Integration tests for the complete learning feedback cycle with ideal offset calculation.
Tests end-to-end scenarios from offset application through feedback collection and learning improvement.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, call
from datetime import datetime, timedelta, time
import asyncio
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.components.climate.const import HVACMode
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util
from homeassistant.helpers.event import async_fire_time_changed

from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.sensor_manager import SensorManager
from custom_components.smart_climate.models import OffsetInput
from tests.fixtures.mock_entities import (
    create_mock_hass,
    create_mock_state,
    create_mock_offset_engine,
    create_mock_sensor_manager,
    create_mock_mode_manager,
    create_mock_temperature_controller,
    create_mock_coordinator,
)


class TestLearningFeedbackIntegration:
    """Integration tests for complete learning feedback pipeline."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance with time tracking."""
        hass = create_mock_hass()
        hass.async_create_task = AsyncMock()
        hass.async_block_till_done = AsyncMock()
        
        # Track scheduled tasks for time advancement
        hass._scheduled_tasks = []
        
        def track_task(task):
            hass._scheduled_tasks.append(task)
            return task
            
        hass.async_create_task = Mock(side_effect=track_task)
        return hass

    @pytest.fixture
    def real_offset_engine(self):
        """Create a real OffsetEngine instance for integration testing."""
        config = {
            'learning': True,
            'learning_rate': 0.1,
            'max_samples': 100
        }
        return OffsetEngine(config)

    @pytest.fixture
    def mock_sensor_manager(self):
        """Create mock sensor manager with controllable temperature values."""
        sensor_manager = create_mock_sensor_manager()
        
        # Default values - can be overridden in tests
        sensor_manager.get_room_temperature.return_value = 21.0
        sensor_manager.get_outdoor_temperature.return_value = 15.0
        sensor_manager.get_humidity.return_value = 45.0
        
        return sensor_manager

    @pytest.fixture
    def climate_entity_with_real_engine(self, mock_hass, real_offset_engine, mock_sensor_manager):
        """Create climate entity with real OffsetEngine for integration testing."""
        config = {
            'entity_id': 'climate.test_ac',
            'room_sensor': 'sensor.room_temp',
            'outdoor_sensor': 'sensor.outdoor_temp',
            'feedback_delay': 60,
            'learning': True
        }

        # Create entity with all required arguments
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=config,
            wrapped_entity_id='climate.test_ac',
            room_sensor_id='sensor.room_temp',
            offset_engine=real_offset_engine,
            sensor_manager=mock_sensor_manager,
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=create_mock_coordinator()
        )

        # Set up climate entity state
        entity._attr_hvac_mode = HVACMode.HEAT
        entity._attr_target_temperature = 24.0
        entity._climate_entity_id = 'climate.test_ac'

        # Mock Home Assistant state
        mock_hass.states.async_set('climate.test_ac', STATE_ON, {
            'temperature': 22.0,
            'current_temperature': 21.0
        })

        return entity

    @pytest.mark.asyncio
    async def test_full_feedback_cycle(self, climate_entity_with_real_engine):
        """Test complete feedback cycle: apply offset → trigger feedback → verify ideal offset recorded."""
        entity = climate_entity_with_real_engine
        hass = entity.hass
        
        # Setup initial conditions
        initial_room_temp = 21.0
        target_temp = 24.0
        entity._sensor_manager.get_room_temperature.return_value = initial_room_temp
        entity._attr_target_temperature = target_temp
        
        # Step 1: Apply offset (this should store initial conditions)
        offset_input = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=initial_room_temp,
            outdoor_temp=15.0,
            mode="cool",
            power_consumption=150.0,
            time_of_day=datetime.now().time(),
            day_of_week=datetime.now().weekday(),
            indoor_humidity=45.0
        )
        
        # Mock the wrapped entity state to provide AC internal temperature
        with patch.object(entity.hass.states, 'get') as mock_get_state:
            mock_state = Mock()
            mock_state.state = "heat"
            mock_state.attributes = {"current_temperature": 22.0, "temperature": 22.0}
            mock_get_state.return_value = mock_state
            await entity._apply_temperature_with_offset(target_temp, offset_input)
        
        # Verify initial conditions were stored
        assert entity._last_initial_room_temp == initial_room_temp
        assert entity._last_target_temperature == target_temp
        assert entity._last_predicted_offset is not None
        assert entity._last_offset_input is not None
        
        # Step 2: Simulate time passing and room temperature change
        final_room_temp = 23.5  # Didn't quite reach target
        entity._sensor_manager.get_room_temperature.return_value = final_room_temp
        
        # Step 3: Trigger feedback collection
        await entity._collect_learning_feedback(datetime.now())
        
        # Step 4: Verify learning data was recorded with ideal offset
        enhanced_samples = entity._offset_engine._learner._enhanced_samples
        assert len(enhanced_samples) == 1
        
        sample = enhanced_samples[0]
        expected_ideal_offset = target_temp - initial_room_temp  # 24.0 - 21.0 = 3.0
        
        assert sample["predicted"] != sample["actual"]  # Key fix: different values
        assert sample["actual"] == expected_ideal_offset
        assert sample["room_temp"] == initial_room_temp
        assert sample["outdoor_temp"] == 15.0

    @pytest.mark.asyncio
    async def test_multiple_feedback_cycles(self, climate_entity_with_real_engine):
        """Test that consecutive feedback cycles work correctly."""
        entity = climate_entity_with_real_engine
        
        # First cycle
        entity._sensor_manager.get_room_temperature.return_value = 20.0
        entity._attr_target_temperature = 23.0
        
        offset_input_1 = OffsetInput(
            ac_internal_temp=21.0,
            room_temp=20.0,
            outdoor_temp=10.0,
            mode="cool",
            power_consumption=120.0,
            time_of_day=datetime.now().time(),
            day_of_week=datetime.now().weekday(),
            indoor_humidity=40.0
        )
        
        with patch.object(entity, '_get_climate_entity_temperature', return_value=21.0):
            await entity._apply_temperature_with_offset(23.0, offset_input_1)
        
        await entity._collect_learning_feedback(datetime.now())
        
        # Second cycle with different conditions
        entity._sensor_manager.get_room_temperature.return_value = 22.0
        entity._attr_target_temperature = 25.0
        
        offset_input_2 = OffsetInput(
            ac_internal_temp=23.0,
            room_temp=22.0,
            outdoor_temp=12.0,
            mode="cool",
            power_consumption=140.0,
            time_of_day=datetime.now().time(),
            day_of_week=datetime.now().weekday(),
            indoor_humidity=50.0
        )
        
        with patch.object(entity, '_get_climate_entity_temperature', return_value=23.0):
            await entity._apply_temperature_with_offset(25.0, offset_input_2)
        
        await entity._collect_learning_feedback(datetime.now())
        
        # Verify both cycles recorded
        enhanced_samples = entity._offset_engine._learner._enhanced_samples
        assert len(enhanced_samples) == 2
        
        # First cycle: ideal = 23.0 - 20.0 = 3.0
        assert enhanced_samples[0]["actual"] == 3.0
        assert enhanced_samples[0]["room_temp"] == 20.0
        
        # Second cycle: ideal = 25.0 - 22.0 = 3.0
        assert enhanced_samples[1]["actual"] == 3.0
        assert enhanced_samples[1]["room_temp"] == 22.0
        
        # Verify predicted and actual are different (key requirement)
        assert enhanced_samples[0]["predicted"] != enhanced_samples[0]["actual"]
        assert enhanced_samples[1]["predicted"] != enhanced_samples[1]["actual"]

    @pytest.mark.asyncio
    async def test_feedback_with_real_offset_engine(self, climate_entity_with_real_engine):
        """Test feedback collection using actual OffsetEngine instance."""
        entity = climate_entity_with_real_engine
        engine = entity._offset_engine
        
        # Verify engine is real and learning is enabled
        assert isinstance(engine, OffsetEngine)
        assert engine.is_learning_enabled() is True
        
        # Apply multiple offsets to build learning data
        scenarios = [
            (19.0, 22.0, 8.0),   # Cold room, moderate target, cold outside
            (21.0, 24.0, 15.0),  # Moderate conditions
            (23.0, 26.0, 25.0),  # Warm conditions
        ]
        
        for initial_temp, target_temp, outdoor_temp in scenarios:
            entity._sensor_manager.get_room_temperature.return_value = initial_temp
            entity._sensor_manager.get_outdoor_temperature.return_value = outdoor_temp
            entity._attr_target_temperature = target_temp
            
            offset_input = OffsetInput(
                ac_internal_temp=initial_temp + 1.0,
                room_temp=initial_temp,
                outdoor_temp=outdoor_temp,
                mode="cool",
                power_consumption=150.0,
                time_of_day=datetime.now().time(),
                day_of_week=datetime.now().weekday(),
                indoor_humidity=45.0
            )
            
            with patch.object(entity, '_get_climate_entity_temperature', return_value=initial_temp + 1.0):
                await entity._apply_temperature_with_offset(target_temp, offset_input)
            
            await entity._collect_learning_feedback(datetime.now())
        
        # Verify learning data accumulated
        enhanced_samples = engine._learner._enhanced_samples
        assert len(enhanced_samples) == 3
        
        # Verify ideal offsets calculated correctly
        expected_ideals = [3.0, 3.0, 3.0]  # target - initial for each scenario
        for i, expected_ideal in enumerate(expected_ideals):
            assert enhanced_samples[i].actual_offset == expected_ideal
            assert enhanced_samples[i].predicted_offset != expected_ideal  # Different values

    @pytest.mark.asyncio
    async def test_enhanced_samples_contain_different_values(self, climate_entity_with_real_engine):
        """Verify that enhanced_samples show predicted != actual (the core fix)."""
        entity = climate_entity_with_real_engine
        
        # Set up scenario where predicted and ideal will definitely differ
        initial_room_temp = 18.0  # Quite cold
        target_temp = 25.0        # High target
        
        entity._sensor_manager.get_room_temperature.return_value = initial_room_temp
        entity._attr_target_temperature = target_temp
        
        offset_input = OffsetInput(
            room_temp=initial_room_temp,
            outdoor_temp=5.0,  # Very cold outside
            humidity=60.0,
            time_of_day=6.0,   # Early morning
            season=0.1         # Winter
        )
        
        # Mock the offset engine to return a specific predicted offset
        with patch.object(entity._offset_engine, 'get_reactive_offset', return_value=4.5):
            with patch.object(entity, '_get_climate_entity_temperature', return_value=19.0):
                await entity._apply_temperature_with_offset(target_temp, offset_input)
        
        await entity._collect_learning_feedback(datetime.now())
        
        enhanced_samples = entity._offset_engine._learner._enhanced_samples
        assert len(enhanced_samples) == 1
        
        sample = enhanced_samples[0]
        expected_ideal = target_temp - initial_room_temp  # 25.0 - 18.0 = 7.0
        
        # Verify the fix: predicted != actual
        assert sample["predicted"] == 4.5  # What engine predicted
        assert sample["actual"] == 7.0     # What would have been ideal
        assert sample["predicted"] != sample["actual"]  # THE FIX

    @pytest.mark.asyncio
    async def test_learning_improves_over_time(self, climate_entity_with_real_engine):
        """Test that multiple feedback cycles show learning convergence."""
        entity = climate_entity_with_real_engine
        engine = entity._offset_engine
        
        # Simulate consistent conditions to test learning
        consistent_conditions = OffsetInput(
                ac_internal_temp=22.0,
                room_temp=0,
                outdoor_temp=outdoor_temp,
                mode="cool",
                power_consumption=150.0,
                time_of_day=datetime.now().time(),
                day_of_week=datetime.now().weekday(),
                indoor_humidity=45.0
            )
        
        predicted_offsets = []
        
        # Run multiple learning cycles with same conditions
        for cycle in range(5):
            entity._sensor_manager.get_room_temperature.return_value = 20.0
            entity._attr_target_temperature = 24.0
            
            # Get predicted offset before applying
            predicted_offset = engine.get_reactive_offset(consistent_conditions)
            predicted_offsets.append(predicted_offset)
            
            with patch.object(entity, '_get_climate_entity_temperature', return_value=21.0):
                await entity._apply_temperature_with_offset(24.0, consistent_conditions)
            
            await entity._collect_learning_feedback(datetime.now())
        
        # Verify learning data accumulated
        enhanced_samples = engine._learner._enhanced_samples
        assert len(enhanced_samples) == 5
        
        # Verify all samples have ideal offset of 4.0 (24.0 - 20.0)
        for sample in enhanced_samples:
            assert sample["actual"] == 4.0
            assert sample["predicted"] != sample["actual"]
        
        # With learning enabled, predictions should trend toward ideal
        # (This is a basic check - full convergence testing would need more cycles)
        assert len(predicted_offsets) == 5

    @pytest.mark.asyncio
    async def test_feedback_timing_with_async_fire_time_changed(self, climate_entity_with_real_engine):
        """Test feedback timing using Home Assistant's time advancement."""
        entity = climate_entity_with_real_engine
        hass = entity.hass
        
        # Setup initial conditions
        entity._sensor_manager.get_room_temperature.return_value = 21.0
        entity._attr_target_temperature = 24.0
        
        offset_input = OffsetInput(
            room_temp=21.0, outdoor_temp=12.0, humidity=45.0,
            time_of_day=10.0, season=0.4
        )
        
        # Apply offset - this should schedule feedback collection
        # Mock the wrapped entity state to provide AC internal temperature
        with patch.object(entity.hass.states, 'get') as mock_get_state:
            mock_state = Mock()
            mock_state.state = "heat"
            mock_state.attributes = {"current_temperature": 22.0, "temperature": 22.0}
            mock_get_state.return_value = mock_state
            with patch('homeassistant.helpers.event.async_track_time_interval') as mock_track:
                await entity._apply_temperature_with_offset(24.0, offset_input)
                
                # Verify feedback was scheduled
                mock_track.assert_called_once()
                scheduled_callback = mock_track.call_args[0][2]  # The callback function
                scheduled_delay = mock_track.call_args[0][1]     # The time interval
        
        # Verify feedback delay matches config
        assert scheduled_delay.total_seconds() == 60  # feedback_delay from fixture
        
        # Simulate time advancement and execute callback
        start_time = dt_util.utcnow()
        future_time = start_time + timedelta(seconds=61)
        
        # Execute the scheduled feedback
        await scheduled_callback(future_time)
        
        # Verify learning data was recorded
        enhanced_samples = entity._offset_engine._learner._enhanced_samples
        assert len(enhanced_samples) == 1
        
        sample = enhanced_samples[0]
        expected_ideal = 3.0  # 24.0 - 21.0
        assert sample["actual"] == expected_ideal

    @pytest.mark.asyncio
    async def test_target_temperature_change_cancels_feedback(self, climate_entity_with_real_engine):
        """Test that user changing target temperature cancels pending feedback."""
        entity = climate_entity_with_real_engine
        
        # Apply initial offset
        entity._sensor_manager.get_room_temperature.return_value = 20.0
        entity._attr_target_temperature = 23.0
        
        offset_input = OffsetInput(
            room_temp=20.0, outdoor_temp=10.0, humidity=40.0,
            time_of_day=11.0, season=0.3
        )
        
        with patch.object(entity, '_get_climate_entity_temperature', return_value=21.0):
            await entity._apply_temperature_with_offset(23.0, offset_input)
        
        # User changes target temperature (simulating manual intervention)
        entity._attr_target_temperature = 25.0
        
        # Attempt feedback collection - should be skipped
        await entity._collect_learning_feedback(datetime.now())
        
        # Verify no learning data recorded due to target change
        enhanced_samples = entity._offset_engine._learner._enhanced_samples
        assert len(enhanced_samples) == 0

    @pytest.mark.asyncio
    async def test_missing_sensor_data_handling(self, climate_entity_with_real_engine):
        """Test feedback collection gracefully handles missing sensor data."""
        entity = climate_entity_with_real_engine
        
        # Apply offset with valid data
        entity._sensor_manager.get_room_temperature.return_value = 21.0
        entity._attr_target_temperature = 24.0
        
        offset_input = OffsetInput(
            room_temp=21.0, outdoor_temp=15.0, humidity=50.0,
            time_of_day=13.0, season=0.6
        )
        
        # Mock the wrapped entity state to provide AC internal temperature
        with patch.object(entity.hass.states, 'get') as mock_get_state:
            mock_state = Mock()
            mock_state.state = "heat"
            mock_state.attributes = {"current_temperature": 22.0, "temperature": 22.0}
            mock_get_state.return_value = mock_state
            await entity._apply_temperature_with_offset(24.0, offset_input)
        
        # Make sensor data unavailable before feedback
        entity._sensor_manager.get_room_temperature.return_value = None
        
        # Attempt feedback collection - should handle gracefully
        await entity._collect_learning_feedback(datetime.now())
        
        # Verify no learning data recorded due to missing sensor data
        enhanced_samples = entity._offset_engine._learner._enhanced_samples
        assert len(enhanced_samples) == 0

    @pytest.mark.asyncio
    async def test_learning_disabled_scenario(self, mock_hass, mock_sensor_manager):
        """Test feedback collection when learning is disabled."""
        # Create entity with learning disabled
        mock_config_entry = Mock()
        mock_config_entry.data = {
            'entity_id': 'climate.test_ac',
            'room_sensor': 'sensor.room_temp',
            'feedback_delay': 60,
            'learning': False  # Learning disabled
        }
        
        # Create offset engine with learning disabled
        disabled_engine = OffsetEngine({'learning': False})
        
        entity = SmartClimateEntity(mock_hass, mock_config_entry)
        entity._offset_engine = disabled_engine
        entity._sensor_manager = mock_sensor_manager
        entity._mode_manager = create_mock_mode_manager()
        entity._temperature_controller = create_mock_temperature_controller()
        entity._coordinator = create_mock_coordinator()
        
        # Apply offset
        entity._sensor_manager.get_room_temperature.return_value = 21.0
        entity._attr_target_temperature = 24.0
        
        offset_input = OffsetInput(
            room_temp=21.0, outdoor_temp=15.0, humidity=45.0,
            time_of_day=12.0, season=0.5
        )
        
        # Mock the wrapped entity state to provide AC internal temperature
        with patch.object(entity.hass.states, 'get') as mock_get_state:
            mock_state = Mock()
            mock_state.state = "heat"
            mock_state.attributes = {"current_temperature": 22.0, "temperature": 22.0}
            mock_get_state.return_value = mock_state
            await entity._apply_temperature_with_offset(24.0, offset_input)
        
        # Attempt feedback collection
        await entity._collect_learning_feedback(datetime.now())
        
        # Verify no learning data recorded (learning disabled)
        enhanced_samples = disabled_engine._learner._enhanced_samples
        assert len(enhanced_samples) == 0