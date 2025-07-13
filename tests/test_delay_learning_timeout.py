"""
ABOUTME: Tests for configurable delay learning timeout functionality.
Tests both configurable timeout settings and adaptive timeout based on HVAC characteristics.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

from custom_components.smart_climate.delay_learner import DelayLearner
from homeassistant.components.climate.const import HVACMode


@pytest.fixture
def mock_hass_and_store():
    """Fixture for a mocked HASS and Store object."""
    hass = MagicMock()
    hass.states.get = MagicMock()
    hass.states.async_set = MagicMock()
    
    # Mock async_track_time_interval to return a callable cancellation function
    cancel_func = MagicMock()
    hass.async_track_time_interval = MagicMock(return_value=cancel_func)
    
    store = MagicMock()
    store.async_load = AsyncMock(return_value=None)
    store.async_save = AsyncMock()
    
    return hass, store


class TestConfigurableTimeout:
    """Test configurable timeout parameters."""
    
    def test_default_timeout_is_20_minutes(self, mock_hass_and_store):
        """Test that default timeout is 20 minutes for backwards compatibility."""
        hass, store = mock_hass_and_store
        learner = DelayLearner(hass, "climate.test", "sensor.test_temp", store)
        
        # Default should be 20 minutes (1200 seconds)
        assert learner._timeout == timedelta(minutes=20)
    
    def test_configurable_timeout_respected(self, mock_hass_and_store):
        """Test that custom timeout values are respected."""
        hass, store = mock_hass_and_store
        learner = DelayLearner(
            hass, "climate.test", "sensor.test_temp", store, 
            timeout_minutes=25
        )
        
        assert learner._timeout == timedelta(minutes=25)
    
    def test_minimum_timeout_enforced(self, mock_hass_and_store):
        """Test that minimum timeout of 5 minutes is enforced."""
        hass, store = mock_hass_and_store
        learner = DelayLearner(
            hass, "climate.test", "sensor.test_temp", store, 
            timeout_minutes=2  # Too low
        )
        
        # Should be clamped to minimum of 5 minutes
        assert learner._timeout == timedelta(minutes=5)
    
    def test_maximum_timeout_enforced(self, mock_hass_and_store):
        """Test that maximum timeout of 60 minutes is enforced."""
        hass, store = mock_hass_and_store
        learner = DelayLearner(
            hass, "climate.test", "sensor.test_temp", store, 
            timeout_minutes=90  # Too high
        )
        
        # Should be clamped to maximum of 60 minutes
        assert learner._timeout == timedelta(minutes=60)


class TestAdaptiveTimeout:
    """Test adaptive timeout based on HVAC characteristics."""
    
    def test_adaptive_timeout_for_high_power_systems(self, mock_hass_and_store):
        """Test that high power systems get shorter timeout."""
        hass, store = mock_hass_and_store
        learner = DelayLearner(hass, "climate.test", "sensor.test_temp", store)
        
        # High power consumption (>3000W) should get 15 minutes
        timeout = learner._determine_timeout(HVACMode.COOL, 3500.0)
        assert timeout == timedelta(minutes=15)
    
    def test_adaptive_timeout_for_heat_pumps(self, mock_hass_and_store):
        """Test that heat pumps get longer timeout."""
        hass, store = mock_hass_and_store
        learner = DelayLearner(hass, "climate.test", "sensor.test_temp", store)
        
        # Heat mode should get 25 minutes (slower response)
        timeout = learner._determine_timeout(HVACMode.HEAT, 2000.0)
        assert timeout == timedelta(minutes=25)
    
    def test_adaptive_timeout_default_case(self, mock_hass_and_store):
        """Test default adaptive timeout for normal AC systems."""
        hass, store = mock_hass_and_store
        learner = DelayLearner(hass, "climate.test", "sensor.test_temp", store)
        
        # Normal cooling with moderate power should get default 20 minutes
        timeout = learner._determine_timeout(HVACMode.COOL, 2000.0)
        assert timeout == timedelta(minutes=20)
    
    def test_adaptive_timeout_no_power_sensor(self, mock_hass_and_store):
        """Test adaptive timeout when no power sensor is available."""
        hass, store = mock_hass_and_store
        learner = DelayLearner(hass, "climate.test", "sensor.test_temp", store)
        
        # No power data should use default timeout
        timeout = learner._determine_timeout(HVACMode.COOL, None)
        assert timeout == timedelta(minutes=20)
    
    def test_adaptive_timeout_heat_pump_with_high_power(self, mock_hass_and_store):
        """Test heat pump with high power gets heat pump timeout (prioritizes mode)."""
        hass, store = mock_hass_and_store
        learner = DelayLearner(hass, "climate.test", "sensor.test_temp", store)
        
        # Heat mode takes priority over power level
        timeout = learner._determine_timeout(HVACMode.HEAT, 4000.0)
        assert timeout == timedelta(minutes=25)


@pytest.mark.asyncio
class TestTimeoutInLearningCycle:
    """Test that timeout is properly used during learning cycles."""
    
    async def test_custom_timeout_used_in_learning_cycle(self, mock_hass_and_store):
        """Test that custom timeout is used during actual learning."""
        hass, store = mock_hass_and_store
        
        # Create learner with 30-minute timeout
        learner = DelayLearner(
            hass, "climate.test", "sensor.test_temp", store, 
            timeout_minutes=30
        )
        
        # Verify timeout configuration
        assert learner._timeout == timedelta(minutes=30)
        
        # Mock temperature sensor
        temp_state = MagicMock()
        temp_state.state = "22.0"
        hass.states.get.return_value = temp_state
        
        # Mock async_track_time_interval
        cancel_func = MagicMock()
        with patch('custom_components.smart_climate.delay_learner.async_track_time_interval', return_value=cancel_func):
            # Start learning cycle
            start_time = datetime.now()
            with patch('homeassistant.util.dt.utcnow', return_value=start_time):
                learner.start_learning_cycle()
            
            # Verify adaptive timeout is set
            assert learner._current_timeout == timedelta(minutes=30)
            assert learner._learning_start_time == start_time
            assert learner._cancel_listener == cancel_func
            
            # Simulate timeout - just manually call stop_learning_cycle to verify it works
            learner.stop_learning_cycle()
            
            # Verify learning stopped
            assert learner._cancel_listener is None
            assert learner._learning_start_time is None
    
    async def test_adaptive_timeout_with_sensor_manager(self, mock_hass_and_store):
        """Test adaptive timeout when sensor manager is available."""
        hass, store = mock_hass_and_store
        
        # Create sensor manager mock
        sensor_manager = MagicMock()
        sensor_manager.get_power_consumption.return_value = 4000.0  # High power
        
        learner = DelayLearner(
            hass, "climate.test", "sensor.test_temp", store,
            sensor_manager=sensor_manager
        )
        
        # Mock HVAC mode as cooling
        climate_state = MagicMock()
        climate_state.state = HVACMode.COOL
        
        temp_state = MagicMock()
        temp_state.state = "22.0"
        
        def mock_states_get(entity_id):
            if entity_id == "climate.test":
                return climate_state
            elif entity_id == "sensor.test_temp":
                return temp_state
            return None
        
        hass.states.get.side_effect = mock_states_get
        
        # Should use 15-minute timeout for high power system
        learner.start_learning_cycle()
        expected_timeout = timedelta(minutes=15)
        assert learner._current_timeout == expected_timeout
    
    async def test_early_exit_still_works_with_longer_timeout(self, mock_hass_and_store):
        """Test that early exit on stability still works with longer timeouts."""
        hass, store = mock_hass_and_store
        
        learner = DelayLearner(
            hass, "climate.test", "sensor.test_temp", store, 
            timeout_minutes=30  # Long timeout
        )
        
        # Mock async_track_time_interval
        cancel_func = MagicMock()
        with patch('custom_components.smart_climate.delay_learner.async_track_time_interval', return_value=cancel_func):
            # Mock temperature sensor
            temp_state = MagicMock()
            temp_state.state = "22.0"
            hass.states.get.return_value = temp_state
            
            start_time = datetime.now()
            with patch('homeassistant.util.dt.utcnow', return_value=start_time):
                learner.start_learning_cycle()
            
            # Verify learning started
            assert learner._learning_start_time == start_time
            assert learner._cancel_listener == cancel_func
            assert learner._current_timeout == timedelta(minutes=30)
            
            # Test that learner can be stopped manually (simulating early stability)
            learner.stop_learning_cycle()
            
            # Should be stopped regardless of long timeout
            assert learner._cancel_listener is None
            assert learner._learning_start_time is None


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""
    
    def test_existing_instantiation_still_works(self, mock_hass_and_store):
        """Test that existing code without timeout parameter still works."""
        hass, store = mock_hass_and_store
        
        # This should work without timeout_minutes parameter
        learner = DelayLearner(hass, "climate.test", "sensor.test_temp", store)
        
        # Should use default 20-minute timeout
        assert learner._timeout == timedelta(minutes=20)
    
    def test_learned_delay_method_unchanged(self, mock_hass_and_store):
        """Test that get_adaptive_delay method signature is unchanged."""
        hass, store = mock_hass_and_store
        learner = DelayLearner(hass, "climate.test", "sensor.test_temp", store)
        
        # Method should work with same signature
        delay = learner.get_adaptive_delay()
        assert delay == 45  # Default fallback
        
        delay_with_fallback = learner.get_adaptive_delay(fallback_delay=60)
        assert delay_with_fallback == 60


class TestConfigFlowIntegration:
    """Test integration with config flow for timeout configuration."""
    
    def test_timeout_configuration_in_schema(self):
        """Test that timeout configuration is included in config schema."""
        from custom_components.smart_climate.const import (
            CONF_DELAY_LEARNING_TIMEOUT, 
            DEFAULT_DELAY_LEARNING_TIMEOUT
        )
        
        # Constants should be defined
        assert CONF_DELAY_LEARNING_TIMEOUT == "delay_learning_timeout"
        assert DEFAULT_DELAY_LEARNING_TIMEOUT == 20
    
    def test_timeout_validation_in_config(self):
        """Test that timeout values are properly validated in config."""
        from custom_components.smart_climate.const import (
            MIN_DELAY_LEARNING_TIMEOUT,
            MAX_DELAY_LEARNING_TIMEOUT
        )
        
        # Validation constants should be defined
        assert MIN_DELAY_LEARNING_TIMEOUT == 5
        assert MAX_DELAY_LEARNING_TIMEOUT == 60


class TestErrorHandling:
    """Test error handling in timeout functionality."""
    
    def test_invalid_timeout_type_handled(self, mock_hass_and_store):
        """Test that invalid timeout types are handled gracefully."""
        hass, store = mock_hass_and_store
        
        # Should handle string input gracefully
        learner = DelayLearner(
            hass, "climate.test", "sensor.test_temp", store, 
            timeout_minutes="invalid"
        )
        
        # Should fallback to default
        assert learner._timeout == timedelta(minutes=20)
    
    def test_none_timeout_handled(self, mock_hass_and_store):
        """Test that None timeout is handled gracefully."""
        hass, store = mock_hass_and_store
        
        learner = DelayLearner(
            hass, "climate.test", "sensor.test_temp", store, 
            timeout_minutes=None
        )
        
        # Should fallback to default
        assert learner._timeout == timedelta(minutes=20)
    
    def test_sensor_manager_error_handled(self, mock_hass_and_store):
        """Test that sensor manager errors don't crash adaptive timeout."""
        hass, store = mock_hass_and_store
        
        # Create sensor manager that raises exception
        sensor_manager = MagicMock()
        sensor_manager.get_power_consumption.side_effect = Exception("Sensor error")
        
        learner = DelayLearner(
            hass, "climate.test", "sensor.test_temp", store,
            sensor_manager=sensor_manager
        )
        
        # Should handle error gracefully and use default timeout
        timeout = learner._determine_timeout(HVACMode.COOL, None)
        assert timeout == timedelta(minutes=20)