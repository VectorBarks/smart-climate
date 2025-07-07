"""ABOUTME: Test suite for SensorManager sensor integration and state handling.
Tests sensor reading, state change callbacks, and error handling for all sensor types."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from homeassistant.core import HomeAssistant, State
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN

from custom_components.smart_climate.sensor_manager import SensorManager


class TestSensorManager:
    """Test SensorManager functionality."""
    
    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        hass = Mock()
        hass.states = Mock()
        hass.helpers = Mock()
        hass.helpers.event = Mock()
        hass.helpers.event.async_track_state_change = Mock()
        return hass
    
    @pytest.fixture
    def sensor_manager(self, mock_hass):
        """Create SensorManager instance for testing."""
        return SensorManager(
            hass=mock_hass,
            room_sensor_id="sensor.room_temperature",
            outdoor_sensor_id="sensor.outdoor_temperature",
            power_sensor_id="sensor.power_consumption"
        )
    
    @pytest.fixture
    def sensor_manager_minimal(self, mock_hass):
        """Create SensorManager with only required sensors."""
        return SensorManager(
            hass=mock_hass,
            room_sensor_id="sensor.room_temperature"
        )
    
    def test_init_with_all_sensors(self, mock_hass):
        """Test SensorManager initialization with all sensors."""
        sensor_manager = SensorManager(
            hass=mock_hass,
            room_sensor_id="sensor.room_temperature",
            outdoor_sensor_id="sensor.outdoor_temperature",
            power_sensor_id="sensor.power_consumption"
        )
        
        assert sensor_manager._hass == mock_hass
        assert sensor_manager._room_sensor_id == "sensor.room_temperature"
        assert sensor_manager._outdoor_sensor_id == "sensor.outdoor_temperature"
        assert sensor_manager._power_sensor_id == "sensor.power_consumption"
        assert sensor_manager._update_callbacks == []
        assert sensor_manager._remove_listeners == []
    
    def test_init_with_minimal_sensors(self, mock_hass):
        """Test SensorManager initialization with only room sensor."""
        sensor_manager = SensorManager(
            hass=mock_hass,
            room_sensor_id="sensor.room_temperature"
        )
        
        assert sensor_manager._hass == mock_hass
        assert sensor_manager._room_sensor_id == "sensor.room_temperature"
        assert sensor_manager._outdoor_sensor_id is None
        assert sensor_manager._power_sensor_id is None
        assert sensor_manager._update_callbacks == []
        assert sensor_manager._remove_listeners == []
    
    def test_get_room_temperature_success(self, mock_hass, sensor_manager):
        """Test successful room temperature reading."""
        # Mock state with temperature value
        mock_state = Mock()
        mock_state.state = "22.5"
        mock_hass.states.get.return_value = mock_state
        
        result = sensor_manager.get_room_temperature()
        
        assert result == 22.5
        mock_hass.states.get.assert_called_once_with("sensor.room_temperature")
    
    def test_get_room_temperature_unavailable(self, mock_hass, sensor_manager):
        """Test room temperature reading when sensor unavailable."""
        mock_state = Mock()
        mock_state.state = STATE_UNAVAILABLE
        mock_hass.states.get.return_value = mock_state
        
        result = sensor_manager.get_room_temperature()
        
        assert result is None
        mock_hass.states.get.assert_called_once_with("sensor.room_temperature")
    
    def test_get_room_temperature_unknown(self, mock_hass, sensor_manager):
        """Test room temperature reading when sensor unknown."""
        mock_state = Mock()
        mock_state.state = STATE_UNKNOWN
        mock_hass.states.get.return_value = mock_state
        
        result = sensor_manager.get_room_temperature()
        
        assert result is None
        mock_hass.states.get.assert_called_once_with("sensor.room_temperature")
    
    def test_get_room_temperature_no_state(self, mock_hass, sensor_manager):
        """Test room temperature reading when no state available."""
        mock_hass.states.get.return_value = None
        
        result = sensor_manager.get_room_temperature()
        
        assert result is None
        mock_hass.states.get.assert_called_once_with("sensor.room_temperature")
    
    def test_get_room_temperature_invalid_float(self, mock_hass, sensor_manager):
        """Test room temperature reading with invalid float value."""
        mock_state = Mock()
        mock_state.state = "invalid_float"
        mock_hass.states.get.return_value = mock_state
        
        result = sensor_manager.get_room_temperature()
        
        assert result is None
        mock_hass.states.get.assert_called_once_with("sensor.room_temperature")
    
    def test_get_outdoor_temperature_success(self, mock_hass, sensor_manager):
        """Test successful outdoor temperature reading."""
        mock_state = Mock()
        mock_state.state = "18.2"
        mock_hass.states.get.return_value = mock_state
        
        result = sensor_manager.get_outdoor_temperature()
        
        assert result == 18.2
        mock_hass.states.get.assert_called_once_with("sensor.outdoor_temperature")
    
    def test_get_outdoor_temperature_no_sensor_configured(self, mock_hass, sensor_manager_minimal):
        """Test outdoor temperature reading when no sensor configured."""
        result = sensor_manager_minimal.get_outdoor_temperature()
        
        assert result is None
        mock_hass.states.get.assert_not_called()
    
    def test_get_outdoor_temperature_unavailable(self, mock_hass, sensor_manager):
        """Test outdoor temperature reading when sensor unavailable."""
        mock_state = Mock()
        mock_state.state = STATE_UNAVAILABLE
        mock_hass.states.get.return_value = mock_state
        
        result = sensor_manager.get_outdoor_temperature()
        
        assert result is None
        mock_hass.states.get.assert_called_once_with("sensor.outdoor_temperature")
    
    def test_get_power_consumption_success(self, mock_hass, sensor_manager):
        """Test successful power consumption reading."""
        mock_state = Mock()
        mock_state.state = "1250.5"
        mock_hass.states.get.return_value = mock_state
        
        result = sensor_manager.get_power_consumption()
        
        assert result == 1250.5
        mock_hass.states.get.assert_called_once_with("sensor.power_consumption")
    
    def test_get_power_consumption_no_sensor_configured(self, mock_hass, sensor_manager_minimal):
        """Test power consumption reading when no sensor configured."""
        result = sensor_manager_minimal.get_power_consumption()
        
        assert result is None
        mock_hass.states.get.assert_not_called()
    
    def test_get_power_consumption_unavailable(self, mock_hass, sensor_manager):
        """Test power consumption reading when sensor unavailable."""
        mock_state = Mock()
        mock_state.state = STATE_UNAVAILABLE
        mock_hass.states.get.return_value = mock_state
        
        result = sensor_manager.get_power_consumption()
        
        assert result is None
        mock_hass.states.get.assert_called_once_with("sensor.power_consumption")
    
    def test_register_update_callback(self, sensor_manager):
        """Test registering update callbacks."""
        callback1 = Mock()
        callback2 = Mock()
        
        sensor_manager.register_update_callback(callback1)
        sensor_manager.register_update_callback(callback2)
        
        assert len(sensor_manager._update_callbacks) == 2
        assert callback1 in sensor_manager._update_callbacks
        assert callback2 in sensor_manager._update_callbacks
    
    @pytest.mark.asyncio
    async def test_start_listening_all_sensors(self, mock_hass, sensor_manager):
        """Test starting listeners for all configured sensors."""
        # Mock the async_track_state_change function
        mock_remove_listener = Mock()
        
        with patch('custom_components.smart_climate.sensor_manager.async_track_state_change_event') as mock_track:
            mock_track.return_value = mock_remove_listener
            
            await sensor_manager.start_listening()
            
            # Should have called async_track_state_change 3 times (room, outdoor, power)
            assert mock_track.call_count == 3
            
            # Check that all sensors are being tracked
            call_args_list = mock_track.call_args_list
            tracked_entities = [call[0][1] for call in call_args_list]  # Second argument is entity_id
            assert "sensor.room_temperature" in tracked_entities
            assert "sensor.outdoor_temperature" in tracked_entities
            assert "sensor.power_consumption" in tracked_entities
            
            # Check that remove listeners are stored
            assert len(sensor_manager._remove_listeners) == 3
            assert mock_remove_listener in sensor_manager._remove_listeners
    
    @pytest.mark.asyncio
    async def test_start_listening_minimal_sensors(self, mock_hass, sensor_manager_minimal):
        """Test starting listeners for minimal sensor configuration."""
        mock_remove_listener = Mock()
        
        with patch('custom_components.smart_climate.sensor_manager.async_track_state_change_event') as mock_track:
            mock_track.return_value = mock_remove_listener
            
            await sensor_manager_minimal.start_listening()
            
            # Should have called async_track_state_change only once (room sensor)
            assert mock_track.call_count == 1
            
            # Check that only room sensor is being tracked
            call_args_list = mock_track.call_args_list
            tracked_entities = [call[0][1] for call in call_args_list]  # Second argument is entity_id
            assert "sensor.room_temperature" in tracked_entities
            
            # Check that remove listeners are stored
            assert len(sensor_manager_minimal._remove_listeners) == 1
            assert mock_remove_listener in sensor_manager_minimal._remove_listeners
    
    @pytest.mark.asyncio
    async def test_stop_listening(self, mock_hass, sensor_manager):
        """Test stopping all sensor listeners."""
        # Set up some mock listeners
        mock_remove_listener1 = Mock()
        mock_remove_listener2 = Mock()
        mock_remove_listener3 = Mock()
        sensor_manager._remove_listeners = [
            mock_remove_listener1,
            mock_remove_listener2,
            mock_remove_listener3
        ]
        
        await sensor_manager.stop_listening()
        
        # All listeners should be called
        mock_remove_listener1.assert_called_once()
        mock_remove_listener2.assert_called_once()
        mock_remove_listener3.assert_called_once()
        
        # Remove listeners list should be cleared
        assert sensor_manager._remove_listeners == []
    
    @pytest.mark.asyncio
    async def test_stop_listening_empty(self, sensor_manager):
        """Test stopping listeners when none are registered."""
        # This should not raise an exception
        await sensor_manager.stop_listening()
        
        assert sensor_manager._remove_listeners == []
    
    @pytest.mark.asyncio
    async def test_state_change_callback_execution(self, mock_hass, sensor_manager):
        """Test that state change callbacks are executed."""
        # Register callbacks
        callback1 = Mock()
        callback2 = Mock()
        sensor_manager.register_update_callback(callback1)
        sensor_manager.register_update_callback(callback2)
        
        with patch('custom_components.smart_climate.sensor_manager.async_track_state_change_event') as mock_track:
            mock_track.return_value = Mock()
            
            await sensor_manager.start_listening()
            
            # Get the callback function passed to async_track_state_change_event
            # This will be the third argument (index 2) in the first call
            call_args = mock_track.call_args_list[0]
            state_change_callback = call_args[0][2]  # Third positional argument
            
            # Mock event with old and new states
            old_state = Mock()
            old_state.state = "20.0"
            new_state = Mock()
            new_state.state = "22.0"
            
            mock_event = Mock()
            mock_event.data = {
                'entity_id': 'sensor.room_temperature',
                'old_state': old_state,
                'new_state': new_state
            }
            
            # Call the state change callback
            await state_change_callback(mock_event)
            
            # Both callbacks should have been called
            callback1.assert_called_once()
            callback2.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_state_change_callback_no_callbacks_registered(self, mock_hass, sensor_manager):
        """Test state change when no callbacks are registered."""
        with patch('custom_components.smart_climate.sensor_manager.async_track_state_change_event') as mock_track:
            mock_track.return_value = Mock()
            
            await sensor_manager.start_listening()
            
            # Get the callback function passed to async_track_state_change_event
            call_args = mock_track.call_args_list[0]
            state_change_callback = call_args[0][2]
            
            # Mock event with old and new states
            old_state = Mock()
            old_state.state = "20.0"
            new_state = Mock()
            new_state.state = "22.0"
            
            mock_event = Mock()
            mock_event.data = {
                'entity_id': 'sensor.room_temperature',
                'old_state': old_state,
                'new_state': new_state
            }
            
            # This should not raise an exception
            await state_change_callback(mock_event)