"""Tests for learning feedback mechanism in Smart Climate Control."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch, call
from datetime import datetime, timedelta
import asyncio

from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util

from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.coordinator import SmartClimateCoordinator
from custom_components.smart_climate.models import OffsetInput, OffsetResult
from custom_components.smart_climate.offset_engine import OffsetEngine


class TestLearningFeedback:
    """Test learning feedback functionality."""
    
    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = Mock()
        hass.states = Mock()
        hass.services = AsyncMock()
        hass.async_add_job = Mock()
        hass.async_create_task = Mock()
        # Mock the event loop for async_call_later
        hass.loop = asyncio.get_event_loop()
        return hass
    
    @pytest.fixture
    def mock_wrapped_entity_state(self):
        """Create a mock wrapped entity state."""
        state = Mock()
        state.state = "cool"
        state.attributes = {
            "current_temperature": 26.5,  # AC internal sensor reading
            "target_temperature": 24.0,
            "hvac_modes": ["off", "cool", "heat", "auto"],
            "supported_features": 1
        }
        return state
    
    @pytest.fixture
    def mock_dependencies(self, mock_hass, mock_wrapped_entity_state):
        """Create mock dependencies for SmartClimateEntity."""
        # Mock sensor manager
        sensor_manager = Mock()
        sensor_manager.get_room_temperature = Mock(return_value=25.2)  # Room sensor reading
        sensor_manager.get_outdoor_temperature = Mock(return_value=30.0)
        sensor_manager.get_power_consumption = Mock(return_value=150.0)
        sensor_manager.start_listening = AsyncMock()
        sensor_manager.stop_listening = AsyncMock()
        
        # Mock offset engine with learning enabled
        offset_engine = Mock(spec=OffsetEngine)
        offset_engine.calculate_offset = Mock(return_value=OffsetResult(
            offset=1.3,  # Predicted offset
            clamped=False,
            reason="AC sensor warmer than room",
            confidence=0.8
        ))
        offset_engine.record_actual_performance = Mock()
        offset_engine._enable_learning = True
        
        # Mock mode manager
        mode_manager = Mock()
        mode_manager.current_mode = "none"
        mode_manager.get_adjustments = Mock(return_value=Mock(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        ))
        
        # Mock temperature controller
        temperature_controller = Mock()
        temperature_controller.apply_offset_and_limits = Mock(return_value=25.3)
        temperature_controller.send_temperature_command = AsyncMock()
        
        # Mock coordinator
        coordinator = Mock()
        coordinator.async_add_listener = Mock()
        
        # Setup hass.states.get to return our mock state
        mock_hass.states.get = Mock(return_value=mock_wrapped_entity_state)
        
        return {
            "sensor_manager": sensor_manager,
            "offset_engine": offset_engine,
            "mode_manager": mode_manager,
            "temperature_controller": temperature_controller,
            "coordinator": coordinator
        }
    
    @pytest.mark.asyncio
    async def test_delayed_feedback_scheduled_after_temperature_adjustment(
        self, mock_hass, mock_dependencies
    ):
        """Test that delayed feedback is scheduled after temperature adjustment."""
        entity = SmartClimateEntity(
            hass=mock_hass,
            config={"name": "Test Climate"},
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room",
            **mock_dependencies
        )
        
        # Mock async_call_later to verify it's called
        with patch("custom_components.smart_climate.climate.async_call_later") as mock_call_later:
            mock_call_later.return_value = Mock()  # Return a cancel function
            
            # Apply temperature with offset
            await entity._apply_temperature_with_offset(24.0)
            
            # Verify offset was calculated
            mock_dependencies["offset_engine"].calculate_offset.assert_called_once()
            
            # Verify temperature was sent to wrapped entity
            mock_dependencies["temperature_controller"].send_temperature_command.assert_called_once()
            
            # Verify delayed feedback was scheduled
            mock_call_later.assert_called_once()
            args = mock_call_later.call_args
            assert args[0][0] == mock_hass  # hass instance
            assert 30 <= args[0][1] <= 60  # delay between 30-60 seconds
            assert callable(args[0][2])  # callback function
    
    @pytest.mark.asyncio
    async def test_feedback_records_actual_performance_when_called(
        self, mock_hass, mock_dependencies
    ):
        """Test that the feedback callback records actual performance."""
        entity = SmartClimateEntity(
            hass=mock_hass,
            config={"name": "Test Climate"},
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room",
            **mock_dependencies
        )
        
        # Store the feedback callback
        feedback_callback = None
        
        def capture_callback(hass, delay, callback):
            nonlocal feedback_callback
            feedback_callback = callback
            return Mock()  # Return cancel function
        
        with patch("custom_components.smart_climate.climate.async_call_later", side_effect=capture_callback):
            # Apply temperature with offset
            await entity._apply_temperature_with_offset(24.0)
        
        # Verify we captured the callback
        assert feedback_callback is not None
        
        # Simulate time passing and AC adjusting - room temp changes
        mock_dependencies["sensor_manager"].get_room_temperature.return_value = 24.8
        
        # Mock the wrapped entity's new internal temperature after adjustment
        new_wrapped_state = Mock()
        new_wrapped_state.attributes = {"current_temperature": 25.5}
        mock_hass.states.get.return_value = new_wrapped_state
        
        # Call the feedback callback
        await feedback_callback(datetime.now())
        
        # Verify record_actual_performance was called
        mock_dependencies["offset_engine"].record_actual_performance.assert_called_once()
        
        # Check the recorded values
        # The mock.call_args_list contains all calls made
        assert mock_dependencies["offset_engine"].record_actual_performance.call_count == 1
        call = mock_dependencies["offset_engine"].record_actual_performance.call_args
        
        # Extract keyword arguments (method is called with kwargs)
        predicted_offset = call.kwargs["predicted_offset"]
        actual_offset = call.kwargs["actual_offset"]
        input_data = call.kwargs["input_data"]
        
        # The predicted offset should be what was calculated (1.3)
        assert predicted_offset == 1.3
        
        # The actual offset should be the real difference after time passed
        # AC internal: 25.5, Room: 24.8, so actual offset needed was -0.7
        assert actual_offset == pytest.approx(-0.7, abs=0.1)
        
        # Input data should have the original conditions
        assert isinstance(input_data, OffsetInput)
        assert input_data.room_temp == 25.2  # Original room temp
    
    @pytest.mark.asyncio
    async def test_feedback_cancelled_on_entity_removal(
        self, mock_hass, mock_dependencies
    ):
        """Test that feedback tasks are cancelled when entity is removed."""
        entity = SmartClimateEntity(
            hass=mock_hass,
            config={"name": "Test Climate"},
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room",
            **mock_dependencies
        )
        
        # Track cancel calls
        cancel_mock = Mock()
        
        with patch("custom_components.smart_climate.climate.async_call_later") as mock_call_later:
            mock_call_later.return_value = cancel_mock
            
            # Apply temperature multiple times to create multiple feedback tasks
            await entity._apply_temperature_with_offset(24.0)
            await entity._apply_temperature_with_offset(23.5)
            await entity._apply_temperature_with_offset(23.0)
            
            # Should have 3 scheduled feedbacks
            assert mock_call_later.call_count == 3
        
        # Remove entity from hass
        await entity.async_will_remove_from_hass()
        
        # Verify all feedback tasks were cancelled
        assert cancel_mock.call_count == 3
    
    @pytest.mark.asyncio
    async def test_feedback_handles_missing_sensors_gracefully(
        self, mock_hass, mock_dependencies
    ):
        """Test that feedback handles missing sensor data gracefully."""
        entity = SmartClimateEntity(
            hass=mock_hass,
            config={"name": "Test Climate"},
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room",
            **mock_dependencies
        )
        
        # Capture the feedback callback
        feedback_callback = None
        
        def capture_callback(hass, delay, callback):
            nonlocal feedback_callback
            feedback_callback = callback
            return Mock()
        
        with patch("custom_components.smart_climate.climate.async_call_later", side_effect=capture_callback):
            await entity._apply_temperature_with_offset(24.0)
        
        # Simulate sensors becoming unavailable
        mock_dependencies["sensor_manager"].get_room_temperature.return_value = None
        mock_hass.states.get.return_value = None  # Wrapped entity unavailable
        
        # Call feedback - should not crash
        await feedback_callback(datetime.now())
        
        # Should not record performance with missing data
        mock_dependencies["offset_engine"].record_actual_performance.assert_not_called()
    
    # This test is moved to test_coordinator_learning_fix.py
    # The coordinator functionality is better tested there with proper setup
    
    @pytest.mark.asyncio
    async def test_learning_disabled_no_feedback_scheduled(
        self, mock_hass, mock_dependencies
    ):
        """Test that no feedback is scheduled when learning is disabled."""
        # Disable learning
        mock_dependencies["offset_engine"]._enable_learning = False
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config={"name": "Test Climate"},
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room",
            **mock_dependencies
        )
        
        with patch("custom_components.smart_climate.climate.async_call_later") as mock_call_later:
            # Apply temperature
            await entity._apply_temperature_with_offset(24.0)
            
            # No feedback should be scheduled when learning is disabled
            mock_call_later.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_feedback_delay_configurable(
        self, mock_hass, mock_dependencies
    ):
        """Test that feedback delay is configurable."""
        entity = SmartClimateEntity(
            hass=mock_hass,
            config={
                "name": "Test Climate",
                "learning_feedback_delay": 45  # Custom delay
            },
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room",
            **mock_dependencies
        )
        
        with patch("custom_components.smart_climate.climate.async_call_later") as mock_call_later:
            mock_call_later.return_value = Mock()
            
            await entity._apply_temperature_with_offset(24.0)
            
            # Verify custom delay was used
            args = mock_call_later.call_args[0]
            assert args[1] == 45  # Custom delay