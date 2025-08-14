"""Tests for SensorManager humidity sensor extensions.

Following strict TDD: Tests created first, must fail, then implement to pass.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN

from custom_components.smart_climate.sensor_manager import SensorManager


class TestSensorManagerHumidityExtensions:
    """Test humidity sensor extensions to SensorManager."""
    
    def test_constructor_accepts_humidity_sensor_ids(self):
        """Test constructor accepts optional humidity sensor IDs."""
        hass = Mock()
        
        # Test with both humidity sensors
        manager = SensorManager(
            hass=hass,
            room_sensor_id="sensor.room_temp",
            outdoor_sensor_id="sensor.outdoor_temp",
            power_sensor_id="sensor.ac_power",
            indoor_humidity_sensor_id="sensor.indoor_humidity",
            outdoor_humidity_sensor_id="sensor.outdoor_humidity"
        )
        
        # These attributes should exist after implementation
        assert hasattr(manager, '_indoor_humidity_sensor_id')
        assert hasattr(manager, '_outdoor_humidity_sensor_id')
        assert manager._indoor_humidity_sensor_id == "sensor.indoor_humidity"
        assert manager._outdoor_humidity_sensor_id == "sensor.outdoor_humidity"
    
    def test_constructor_humidity_sensors_default_to_none(self):
        """Test humidity sensor IDs default to None when not provided."""
        hass = Mock()
        
        # Test without humidity sensors
        manager = SensorManager(
            hass=hass,
            room_sensor_id="sensor.room_temp"
        )
        
        # Should default to None
        assert manager._indoor_humidity_sensor_id is None
        assert manager._outdoor_humidity_sensor_id is None
    
    def test_constructor_partial_humidity_sensors(self):
        """Test constructor with only one humidity sensor."""
        hass = Mock()
        
        # Test with only indoor humidity
        manager_indoor_only = SensorManager(
            hass=hass,
            room_sensor_id="sensor.room_temp",
            indoor_humidity_sensor_id="sensor.indoor_humidity"
        )
        
        assert manager_indoor_only._indoor_humidity_sensor_id == "sensor.indoor_humidity"
        assert manager_indoor_only._outdoor_humidity_sensor_id is None
        
        # Test with only outdoor humidity
        manager_outdoor_only = SensorManager(
            hass=hass,
            room_sensor_id="sensor.room_temp",
            outdoor_humidity_sensor_id="sensor.outdoor_humidity"
        )
        
        assert manager_outdoor_only._indoor_humidity_sensor_id is None
        assert manager_outdoor_only._outdoor_humidity_sensor_id == "sensor.outdoor_humidity"

    def test_get_indoor_humidity_returns_float_when_available(self):
        """Test get_indoor_humidity returns float when sensor available."""
        hass = Mock()
        mock_state = Mock()
        mock_state.state = "55.5"
        hass.states.get.return_value = mock_state
        
        manager = SensorManager(
            hass=hass,
            room_sensor_id="sensor.room_temp",
            indoor_humidity_sensor_id="sensor.indoor_humidity"
        )
        
        result = manager.get_indoor_humidity()
        assert result == 55.5
        assert isinstance(result, float)
        hass.states.get.assert_called_with("sensor.indoor_humidity")
    
    def test_get_indoor_humidity_returns_none_when_sensor_unavailable(self):
        """Test get_indoor_humidity returns None when sensor unavailable."""
        hass = Mock()
        manager = SensorManager(
            hass=hass,
            room_sensor_id="sensor.room_temp",
            indoor_humidity_sensor_id="sensor.indoor_humidity"
        )
        
        # Test when sensor not found
        hass.states.get.return_value = None
        result = manager.get_indoor_humidity()
        assert result is None
        
        # Test when sensor state is unavailable
        mock_state = Mock()
        mock_state.state = STATE_UNAVAILABLE
        hass.states.get.return_value = mock_state
        result = manager.get_indoor_humidity()
        assert result is None
        
        # Test when sensor state is unknown
        mock_state.state = STATE_UNKNOWN
        result = manager.get_indoor_humidity()
        assert result is None
    
    def test_get_indoor_humidity_returns_none_when_not_configured(self):
        """Test get_indoor_humidity returns None when sensor not configured."""
        hass = Mock()
        manager = SensorManager(
            hass=hass,
            room_sensor_id="sensor.room_temp"
        )
        
        result = manager.get_indoor_humidity()
        assert result is None
        # Should not call hass.states.get when sensor not configured
        hass.states.get.assert_not_called()
    
    def test_get_indoor_humidity_handles_value_error(self):
        """Test get_indoor_humidity handles ValueError for non-numeric states."""
        hass = Mock()
        mock_state = Mock()
        mock_state.state = "invalid_number"
        hass.states.get.return_value = mock_state
        
        manager = SensorManager(
            hass=hass,
            room_sensor_id="sensor.room_temp",
            indoor_humidity_sensor_id="sensor.indoor_humidity"
        )
        
        result = manager.get_indoor_humidity()
        assert result is None
    
    def test_get_indoor_humidity_handles_type_error(self):
        """Test get_indoor_humidity handles TypeError for None states."""
        hass = Mock()
        mock_state = Mock()
        mock_state.state = None
        hass.states.get.return_value = mock_state
        
        manager = SensorManager(
            hass=hass,
            room_sensor_id="sensor.room_temp",
            indoor_humidity_sensor_id="sensor.indoor_humidity"
        )
        
        result = manager.get_indoor_humidity()
        assert result is None
    
    def test_get_outdoor_humidity_returns_float_when_available(self):
        """Test get_outdoor_humidity returns float when sensor available."""
        hass = Mock()
        mock_state = Mock()
        mock_state.state = "72.3"
        hass.states.get.return_value = mock_state
        
        manager = SensorManager(
            hass=hass,
            room_sensor_id="sensor.room_temp",
            outdoor_humidity_sensor_id="sensor.outdoor_humidity"
        )
        
        result = manager.get_outdoor_humidity()
        assert result == 72.3
        assert isinstance(result, float)
        hass.states.get.assert_called_with("sensor.outdoor_humidity")
    
    def test_get_outdoor_humidity_returns_none_when_sensor_unavailable(self):
        """Test get_outdoor_humidity returns None when sensor unavailable."""
        hass = Mock()
        manager = SensorManager(
            hass=hass,
            room_sensor_id="sensor.room_temp",
            outdoor_humidity_sensor_id="sensor.outdoor_humidity"
        )
        
        # Test when sensor not found
        hass.states.get.return_value = None
        result = manager.get_outdoor_humidity()
        assert result is None
        
        # Test when sensor state is unavailable
        mock_state = Mock()
        mock_state.state = STATE_UNAVAILABLE
        hass.states.get.return_value = mock_state
        result = manager.get_outdoor_humidity()
        assert result is None
        
        # Test when sensor state is unknown
        mock_state.state = STATE_UNKNOWN
        result = manager.get_outdoor_humidity()
        assert result is None
    
    def test_get_outdoor_humidity_returns_none_when_not_configured(self):
        """Test get_outdoor_humidity returns None when sensor not configured."""
        hass = Mock()
        manager = SensorManager(
            hass=hass,
            room_sensor_id="sensor.room_temp"
        )
        
        result = manager.get_outdoor_humidity()
        assert result is None
        # Should not call hass.states.get when sensor not configured
        hass.states.get.assert_not_called()
    
    def test_get_outdoor_humidity_handles_value_error(self):
        """Test get_outdoor_humidity handles ValueError for non-numeric states."""
        hass = Mock()
        mock_state = Mock()
        mock_state.state = "not_a_number"
        hass.states.get.return_value = mock_state
        
        manager = SensorManager(
            hass=hass,
            room_sensor_id="sensor.room_temp",
            outdoor_humidity_sensor_id="sensor.outdoor_humidity"
        )
        
        result = manager.get_outdoor_humidity()
        assert result is None
    
    def test_get_outdoor_humidity_handles_type_error(self):
        """Test get_outdoor_humidity handles TypeError for None states."""
        hass = Mock()
        mock_state = Mock()
        mock_state.state = None
        hass.states.get.return_value = mock_state
        
        manager = SensorManager(
            hass=hass,
            room_sensor_id="sensor.room_temp",
            outdoor_humidity_sensor_id="sensor.outdoor_humidity"
        )
        
        result = manager.get_outdoor_humidity()
        assert result is None

    @pytest.mark.asyncio
    async def test_start_listening_creates_humidity_listeners_when_configured(self):
        """Test start_listening creates listeners for humidity sensors when provided."""
        hass = Mock()
        
        # Mock async_track_state_change_event
        mock_remove_listener = Mock()
        with patch('custom_components.smart_climate.sensor_manager.async_track_state_change_event', return_value=mock_remove_listener) as mock_track:
            manager = SensorManager(
                hass=hass,
                room_sensor_id="sensor.room_temp",
                outdoor_sensor_id="sensor.outdoor_temp", 
                power_sensor_id="sensor.ac_power",
                indoor_humidity_sensor_id="sensor.indoor_humidity",
                outdoor_humidity_sensor_id="sensor.outdoor_humidity"
            )
            
            await manager.start_listening()
            
            # Should have 5 calls: room, outdoor, power, indoor_humidity, outdoor_humidity
            assert mock_track.call_count == 5
            
            # Check that humidity sensors were registered
            call_entity_ids = [call[0][1] for call in mock_track.call_args_list]
            assert "sensor.indoor_humidity" in call_entity_ids
            assert "sensor.outdoor_humidity" in call_entity_ids
            assert "sensor.room_temp" in call_entity_ids
            assert "sensor.outdoor_temp" in call_entity_ids
            assert "sensor.ac_power" in call_entity_ids
    
    @pytest.mark.asyncio
    async def test_start_listening_skips_humidity_listeners_when_not_configured(self):
        """Test start_listening doesn't create humidity listeners when not configured."""
        hass = Mock()
        
        # Mock async_track_state_change_event
        mock_remove_listener = Mock()
        with patch('custom_components.smart_climate.sensor_manager.async_track_state_change_event', return_value=mock_remove_listener) as mock_track:
            manager = SensorManager(
                hass=hass,
                room_sensor_id="sensor.room_temp",
                outdoor_sensor_id="sensor.outdoor_temp",
                power_sensor_id="sensor.ac_power"
                # No humidity sensors configured
            )
            
            await manager.start_listening()
            
            # Should have 3 calls: room, outdoor, power (no humidity)
            assert mock_track.call_count == 3
            
            # Check that humidity sensors were NOT registered
            call_entity_ids = [call[0][1] for call in mock_track.call_args_list]
            assert "sensor.indoor_humidity" not in call_entity_ids
            assert "sensor.outdoor_humidity" not in call_entity_ids
    
    @pytest.mark.asyncio
    async def test_start_listening_partial_humidity_sensors(self):
        """Test start_listening with only one humidity sensor configured."""
        hass = Mock()
        
        # Mock async_track_state_change_event
        mock_remove_listener = Mock()
        with patch('custom_components.smart_climate.sensor_manager.async_track_state_change_event', return_value=mock_remove_listener) as mock_track:
            manager = SensorManager(
                hass=hass,
                room_sensor_id="sensor.room_temp",
                indoor_humidity_sensor_id="sensor.indoor_humidity"
                # Only indoor humidity configured
            )
            
            await manager.start_listening()
            
            # Should have 2 calls: room, indoor_humidity
            assert mock_track.call_count == 2
            
            # Check calls
            call_entity_ids = [call[0][1] for call in mock_track.call_args_list]
            assert "sensor.room_temp" in call_entity_ids
            assert "sensor.indoor_humidity" in call_entity_ids
            assert "sensor.outdoor_humidity" not in call_entity_ids

    @pytest.mark.asyncio 
    async def test_humidity_state_change_triggers_callbacks(self):
        """Test that humidity sensor state changes trigger update callbacks."""
        hass = Mock()
        
        # Mock async_track_state_change_event to capture the callback
        captured_callback = None
        def capture_callback(hass_obj, entity_id, callback):
            nonlocal captured_callback
            captured_callback = callback
            return Mock()  # return remove listener mock
        
        with patch('custom_components.smart_climate.sensor_manager.async_track_state_change_event', side_effect=capture_callback):
            manager = SensorManager(
                hass=hass,
                room_sensor_id="sensor.room_temp",
                indoor_humidity_sensor_id="sensor.indoor_humidity"
            )
            
            # Register a callback
            update_callback = Mock()
            manager.register_update_callback(update_callback)
            
            await manager.start_listening()
            
            # Simulate humidity sensor state change
            mock_event = Mock()
            mock_event.data = {
                'entity_id': 'sensor.indoor_humidity',
                'old_state': Mock(state='50.0'),
                'new_state': Mock(state='55.0')
            }
            
            # Trigger the callback that was captured
            await captured_callback(mock_event)
            
            # Callback should have been called
            update_callback.assert_called_once()

    def test_backward_compatibility_existing_methods_still_work(self):
        """Test that existing temperature and power methods still work unchanged."""
        hass = Mock()
        
        # Test with humidity sensors added
        manager = SensorManager(
            hass=hass,
            room_sensor_id="sensor.room_temp",
            outdoor_sensor_id="sensor.outdoor_temp",
            power_sensor_id="sensor.ac_power",
            indoor_humidity_sensor_id="sensor.indoor_humidity",
            outdoor_humidity_sensor_id="sensor.outdoor_humidity"
        )
        
        # Mock temperature sensor responses
        mock_room_state = Mock()
        mock_room_state.state = "22.5"
        
        mock_outdoor_state = Mock()
        mock_outdoor_state.state = "18.0"
        
        mock_power_state = Mock()
        mock_power_state.state = "1200"
        
        def mock_states_get(entity_id):
            if entity_id == "sensor.room_temp":
                return mock_room_state
            elif entity_id == "sensor.outdoor_temp":
                return mock_outdoor_state
            elif entity_id == "sensor.ac_power":
                return mock_power_state
            return None
        
        hass.states.get.side_effect = mock_states_get
        
        # Test that existing methods work
        assert manager.get_room_temperature() == 22.5
        assert manager.get_outdoor_temperature() == 18.0
        assert manager.get_power_consumption() == 1200.0
        
        # Verify backward compatibility
        assert hasattr(manager, 'register_update_callback')
        assert hasattr(manager, 'start_listening')
        assert hasattr(manager, 'stop_listening')

    def test_backward_compatibility_without_humidity_sensors(self):
        """Test that SensorManager works unchanged without humidity sensors."""
        hass = Mock()
        
        # Create manager without humidity sensors (original constructor)
        manager = SensorManager(
            hass=hass,
            room_sensor_id="sensor.room_temp",
            outdoor_sensor_id="sensor.outdoor_temp",
            power_sensor_id="sensor.ac_power"
        )
        
        # Should have None humidity sensor IDs
        assert manager._indoor_humidity_sensor_id is None
        assert manager._outdoor_humidity_sensor_id is None
        
        # Humidity methods should return None
        assert manager.get_indoor_humidity() is None
        assert manager.get_outdoor_humidity() is None
        
        # Original methods should work
        mock_room_state = Mock()
        mock_room_state.state = "23.0"
        hass.states.get.return_value = mock_room_state
        
        assert manager.get_room_temperature() == 23.0


class TestSensorManagerNoneEntityGracefulDegradation:
    """Test graceful degradation when optional sensor entity IDs are None."""
    
    def test_handles_none_outdoor_sensor_gracefully(self):
        """Test get_outdoor_temperature returns None gracefully when outdoor sensor ID is None."""
        hass = Mock()
        
        # Create manager with None outdoor sensor ID
        manager = SensorManager(
            hass=hass,
            room_sensor_id="sensor.room_temp",
            outdoor_sensor_id=None  # Explicitly None
        )
        
        # Should return None without calling hass.states.get
        result = manager.get_outdoor_temperature()
        assert result is None
        hass.states.get.assert_not_called()
    
    def test_handles_none_power_sensor_gracefully(self):
        """Test get_power_consumption returns None gracefully when power sensor ID is None.""" 
        hass = Mock()
        
        # Create manager with None power sensor ID
        manager = SensorManager(
            hass=hass,
            room_sensor_id="sensor.room_temp",
            power_sensor_id=None  # Explicitly None
        )
        
        # Should return None without calling hass.states.get
        result = manager.get_power_consumption()
        assert result is None
        hass.states.get.assert_not_called()
    
    def test_handles_none_humidity_sensors_gracefully(self):
        """Test humidity methods return None gracefully when humidity sensor IDs are None."""
        hass = Mock()
        
        # Create manager with None humidity sensor IDs
        manager = SensorManager(
            hass=hass,
            room_sensor_id="sensor.room_temp",
            indoor_humidity_sensor_id=None,  # Explicitly None
            outdoor_humidity_sensor_id=None  # Explicitly None
        )
        
        # Should return None without calling hass.states.get
        indoor_result = manager.get_indoor_humidity()
        outdoor_result = manager.get_outdoor_humidity()
        
        assert indoor_result is None
        assert outdoor_result is None
        hass.states.get.assert_not_called()
    
    def test_returns_none_for_missing_optional_sensors(self):
        """Test all optional sensor methods return None when not configured."""
        hass = Mock()
        
        # Create manager with only required room sensor
        manager = SensorManager(
            hass=hass,
            room_sensor_id="sensor.room_temp"
            # All optional sensors default to None
        )
        
        # All optional methods should return None
        assert manager.get_outdoor_temperature() is None
        assert manager.get_power_consumption() is None
        assert manager.get_indoor_humidity() is None
        assert manager.get_outdoor_humidity() is None
        
        # Should not call hass.states.get for any optional sensors
        hass.states.get.assert_not_called()
    
    def test_logs_appropriate_messages_for_missing_sensors(self):
        """Test appropriate debug messages are logged when sensors are not configured."""
        hass = Mock()
        
        manager = SensorManager(
            hass=hass,
            room_sensor_id="sensor.room_temp"
            # All optional sensors default to None
        )
        
        with patch('custom_components.smart_climate.sensor_manager._LOGGER') as mock_logger:
            # Call humidity methods which have debug logging for None sensors
            manager.get_indoor_humidity()
            manager.get_outdoor_humidity()
            
            # Should log debug messages for None sensor IDs
            assert mock_logger.debug.call_count == 2
            
            # Verify the log messages contain appropriate information
            debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
            assert any("Indoor humidity sensor ID is None" in msg for msg in debug_calls)
            assert any("Outdoor humidity sensor ID is None" in msg for msg in debug_calls)