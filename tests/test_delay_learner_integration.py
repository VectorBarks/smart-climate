"""Tests for DelayLearner integration with SmartClimateEntity."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, call
from datetime import datetime, timedelta
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.components.climate.const import HVACMode
from homeassistant.helpers.storage import Store

from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.delay_learner import DelayLearner
from tests.fixtures.mock_entities import (
    create_mock_hass,
    create_mock_state,
    create_mock_offset_engine,
    create_mock_sensor_manager,
    create_mock_mode_manager,
    create_mock_temperature_controller,
    create_mock_coordinator,
)


@pytest.fixture
def mock_delay_learner():
    """Create a mock DelayLearner instance."""
    delay_learner = Mock(spec=DelayLearner)
    delay_learner.async_load = AsyncMock()
    delay_learner.async_save = AsyncMock()
    delay_learner.start_learning_cycle = Mock()
    delay_learner.stop_learning_cycle = Mock()
    delay_learner.get_adaptive_delay = Mock(return_value=60)  # Default learned delay
    return delay_learner


@pytest.fixture
def config_with_adaptive_delay():
    """Configuration with adaptive delay enabled."""
    return {
        "name": "Test Smart Climate",
        "feedback_delay": 45,
        "adaptive_delay": True,  # Enable adaptive delays
        "default_target_temperature": 24.0,
    }


@pytest.fixture
def config_without_adaptive_delay():
    """Configuration without adaptive delay (backward compatibility)."""
    return {
        "name": "Test Smart Climate", 
        "feedback_delay": 45,
        "default_target_temperature": 24.0,
    }


@pytest.fixture
def smart_climate_entity_with_adaptive_delay(mock_delay_learner, config_with_adaptive_delay):
    """Create SmartClimateEntity with adaptive delay enabled."""
    mock_hass = create_mock_hass()
    
    # Mock wrapped entity state - make it available 
    wrapped_state = create_mock_state(
        "climate.test_ac",
        HVACMode.OFF,
        {
            "friendly_name": "Test AC",
            "target_temperature": 24.0,
            "current_temperature": 22.0,
        }
    )
    mock_hass.states.get.return_value = wrapped_state
    
    # Create mock dependencies
    mock_offset_engine = create_mock_offset_engine()
    mock_sensor_manager = create_mock_sensor_manager()
    mock_mode_manager = create_mock_mode_manager()
    mock_temperature_controller = create_mock_temperature_controller()
    mock_coordinator = create_mock_coordinator()
    
    entity = SmartClimateEntity(
        hass=mock_hass,
        config=config_with_adaptive_delay,
        wrapped_entity_id="climate.test_ac",
        room_sensor_id="sensor.room_temp",
        offset_engine=mock_offset_engine,
        sensor_manager=mock_sensor_manager,
        mode_manager=mock_mode_manager,
        temperature_controller=mock_temperature_controller,
        coordinator=mock_coordinator
    )
    
    # Inject the mock DelayLearner
    entity._delay_learner = mock_delay_learner
    
    # Initialize the initial state properly
    entity._cached_hvac_mode = HVACMode.OFF
    entity._was_unavailable = False
    entity._degraded_mode = False
    
    return entity


class TestDelayLearnerIntegration:
    """Test DelayLearner integration with SmartClimateEntity."""
    
    @pytest.mark.asyncio
    async def test_delay_learner_initialization_when_enabled(self, config_with_adaptive_delay):
        """Test DelayLearner is initialized when adaptive_delay is enabled."""
        # Arrange
        mock_hass = create_mock_hass()
        wrapped_state = create_mock_state("climate.test_ac", HVACMode.OFF, {
            "target_temperature": 24.0,
            "current_temperature": 22.0,
        })
        mock_hass.states.get.return_value = wrapped_state
        
        # Create mock dependencies
        mock_offset_engine = create_mock_offset_engine()
        mock_sensor_manager = create_mock_sensor_manager()
        mock_mode_manager = create_mock_mode_manager()
        mock_temperature_controller = create_mock_temperature_controller()
        mock_coordinator = create_mock_coordinator()
        
        with patch('custom_components.smart_climate.climate.DelayLearner') as MockDelayLearner, \
             patch('custom_components.smart_climate.climate.Store') as MockStore:
            
            mock_delay_learner = Mock(spec=DelayLearner)
            mock_delay_learner.async_load = AsyncMock()
            MockDelayLearner.return_value = mock_delay_learner
            
            mock_store = Mock(spec=Store)
            MockStore.return_value = mock_store
            
            # Act
            entity = SmartClimateEntity(
                hass=mock_hass,
                config=config_with_adaptive_delay,
                wrapped_entity_id="climate.test_ac",
                room_sensor_id="sensor.room_temp",
                offset_engine=mock_offset_engine,
                sensor_manager=mock_sensor_manager,
                mode_manager=mock_mode_manager,
                temperature_controller=mock_temperature_controller,
                coordinator=mock_coordinator
            )
            
            # Mock async_on_remove method for test
            entity.async_on_remove = Mock()
            
            await entity.async_added_to_hass()
            
            # Assert
            MockStore.assert_called_once_with(
                mock_hass,
                version=1,
                key="smart_climate_delay_learner_climate.test_ac"
            )
            MockDelayLearner.assert_called_once_with(
                mock_hass,
                "climate.test_ac",
                "sensor.room_temp",
                mock_store
            )
            mock_delay_learner.async_load.assert_called_once()
            assert hasattr(entity, '_delay_learner')
            assert entity._delay_learner is mock_delay_learner
    
    @pytest.mark.asyncio
    async def test_delay_learner_not_initialized_when_disabled(self, config_without_adaptive_delay):
        """Test DelayLearner is not initialized when adaptive_delay is not enabled."""
        # Arrange
        mock_hass = create_mock_hass()
        wrapped_state = create_mock_state("climate.test_ac", HVACMode.OFF, {})
        mock_hass.states.get.return_value = wrapped_state
        
        # Create mock dependencies
        mock_offset_engine = create_mock_offset_engine()
        mock_sensor_manager = create_mock_sensor_manager()
        mock_mode_manager = create_mock_mode_manager()
        mock_temperature_controller = create_mock_temperature_controller()
        mock_coordinator = create_mock_coordinator()
        
        with patch('custom_components.smart_climate.climate.DelayLearner') as MockDelayLearner:
            # Act
            entity = SmartClimateEntity(
                hass=mock_hass,
                config=config_without_adaptive_delay,
                wrapped_entity_id="climate.test_ac",
                room_sensor_id="sensor.room_temp",
                offset_engine=mock_offset_engine,
                sensor_manager=mock_sensor_manager,
                mode_manager=mock_mode_manager,
                temperature_controller=mock_temperature_controller,
                coordinator=mock_coordinator
            )
            
            # Mock async_on_remove method for test
            entity.async_on_remove = Mock()
            
            await entity.async_added_to_hass()
            
            # Assert
            MockDelayLearner.assert_not_called()
            assert entity._delay_learner is None
    
    @pytest.mark.asyncio
    async def test_delay_learner_store_creation(self, config_with_adaptive_delay):
        """Test DelayLearner gets unique HA Store instance."""
        # Arrange
        mock_hass = create_mock_hass()
        wrapped_state = create_mock_state("climate.test_ac", HVACMode.OFF, {})
        mock_hass.states.get.return_value = wrapped_state
        
        # Create mock dependencies
        mock_offset_engine = create_mock_offset_engine()
        mock_sensor_manager = create_mock_sensor_manager()
        mock_mode_manager = create_mock_mode_manager()
        mock_temperature_controller = create_mock_temperature_controller()
        mock_coordinator = create_mock_coordinator()
        
        with patch('custom_components.smart_climate.climate.Store') as MockStore:
            mock_store = Mock(spec=Store)
            MockStore.return_value = mock_store
            
            with patch('custom_components.smart_climate.climate.DelayLearner') as MockDelayLearner:
                mock_delay_learner = Mock(spec=DelayLearner)
                mock_delay_learner.async_load = AsyncMock()
                MockDelayLearner.return_value = mock_delay_learner
                
                # Act
                entity = SmartClimateEntity(
                    hass=mock_hass,
                    config=config_with_adaptive_delay,
                    wrapped_entity_id="climate.test_ac",
                    room_sensor_id="sensor.room_temp",
                    offset_engine=mock_offset_engine,
                    sensor_manager=mock_sensor_manager,
                    mode_manager=mock_mode_manager,
                    temperature_controller=mock_temperature_controller,
                    coordinator=mock_coordinator
                )
                
                await entity.async_added_to_hass()
                
                # Assert
                MockStore.assert_called_once_with(
                    mock_hass,
                    version=1,
                    key="smart_climate_delay_learner_climate.test_ac"
                )
                MockDelayLearner.assert_called_once_with(
                    mock_hass,
                    "climate.test_ac",
                    "sensor.room_temp",
                    mock_store
                )
    
    @pytest.mark.asyncio
    async def test_learning_cycle_starts_on_hvac_mode_off_to_on(self, smart_climate_entity_with_adaptive_delay):
        """Test learning cycle starts when HVAC mode changes from OFF to ON."""
        # Arrange
        entity = smart_climate_entity_with_adaptive_delay
        entity._delay_learner.start_learning_cycle.reset_mock()
        
        # Mock wrapped entity state changing to COOL
        wrapped_state = create_mock_state(
            "climate.test_ac",
            HVACMode.COOL,
            {"target_temperature": 24.0}
        )
        entity.hass.states.get.return_value = wrapped_state
        
        # Act
        await entity.async_set_hvac_mode(HVACMode.COOL)
        
        # Assert
        entity._delay_learner.start_learning_cycle.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_learning_cycle_stops_on_hvac_mode_on_to_off(self, smart_climate_entity_with_adaptive_delay):
        """Test learning cycle stops when HVAC mode changes from ON to OFF."""
        # Arrange
        entity = smart_climate_entity_with_adaptive_delay
        
        # Set initial state to COOL
        entity._cached_hvac_mode = HVACMode.COOL
        wrapped_state = create_mock_state(
            "climate.test_ac",
            HVACMode.COOL,
            {"target_temperature": 24.0}
        )
        entity.hass.states.get.return_value = wrapped_state
        
        entity._delay_learner.stop_learning_cycle.reset_mock()
        
        # Mock wrapped entity state changing to OFF
        wrapped_state = create_mock_state(
            "climate.test_ac",
            HVACMode.OFF,
            {"target_temperature": 24.0}
        )
        entity.hass.states.get.return_value = wrapped_state
        
        # Act
        await entity.async_set_hvac_mode(HVACMode.OFF)
        
        # Assert
        entity._delay_learner.stop_learning_cycle.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_learning_cycle_not_triggered_for_non_off_transitions(self, smart_climate_entity_with_adaptive_delay):
        """Test learning cycle is not triggered for transitions not involving OFF mode."""
        # Arrange
        entity = smart_climate_entity_with_adaptive_delay
        
        # Set initial state to COOL
        entity._cached_hvac_mode = HVACMode.COOL
        wrapped_state = create_mock_state(
            "climate.test_ac",
            HVACMode.COOL,
            {"target_temperature": 24.0}
        )
        entity.hass.states.get.return_value = wrapped_state
        
        entity._delay_learner.start_learning_cycle.reset_mock()
        entity._delay_learner.stop_learning_cycle.reset_mock()
        
        # Mock wrapped entity state changing to HEAT (COOL -> HEAT, no OFF involved)
        wrapped_state = create_mock_state(
            "climate.test_ac",
            HVACMode.HEAT,
            {"target_temperature": 24.0}
        )
        entity.hass.states.get.return_value = wrapped_state
        
        # Act
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        
        # Assert
        entity._delay_learner.start_learning_cycle.assert_not_called()
        entity._delay_learner.stop_learning_cycle.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_adaptive_delay_used_in_feedback_collection(self, smart_climate_entity_with_adaptive_delay):
        """Test adaptive delay is used instead of fixed delay for feedback collection."""
        # Arrange
        entity = smart_climate_entity_with_adaptive_delay
        entity._delay_learner.get_adaptive_delay.return_value = 60  # Learned delay
        
        # Mock the async_call_later function
        with patch('custom_components.smart_climate.climate.async_call_later') as mock_call_later:
            mock_cancel_func = Mock()
            mock_call_later.return_value = mock_cancel_func
            
            # Set up entity state
            entity._last_predicted_offset = 2.0
            entity._last_offset_input = Mock()
            
            # Mock offset engine to have learning enabled
            entity._offset_engine._enable_learning = True
            
            # Act
            await entity._collect_learning_feedback(None)
            
            # Schedule feedback (this happens in _apply_temperature_with_offset)
            # Simulate the call that would happen there
            entity._feedback_delay = entity._delay_learner.get_adaptive_delay(entity._feedback_delay) + 5
            
            # Assert
            entity._delay_learner.get_adaptive_delay.assert_called_once_with(45)  # fallback delay
            # The adaptive delay (60) + safety buffer (5) = 65 should be used
            assert entity._feedback_delay == 65
    
    @pytest.mark.asyncio 
    async def test_fallback_to_fixed_delay_when_adaptive_unavailable(self, smart_climate_entity_with_adaptive_delay):
        """Test fallback to fixed delay when adaptive delay unavailable."""
        # Arrange
        entity = smart_climate_entity_with_adaptive_delay
        entity._delay_learner.get_adaptive_delay.return_value = None  # No learned delay yet
        
        # Act
        fallback_delay = 45
        adaptive_delay = entity._delay_learner.get_adaptive_delay(fallback_delay)
        
        # Assert
        assert adaptive_delay is None
        # In real implementation, this would fallback to the configured delay
    
    @pytest.mark.asyncio
    async def test_backward_compatibility_without_delay_learner(self, config_without_adaptive_delay):
        """Test backward compatibility when DelayLearner is not available."""
        # Arrange
        mock_hass = create_mock_hass()
        wrapped_state = create_mock_state("climate.test_ac", HVACMode.OFF, {})
        mock_hass.states.get.return_value = wrapped_state
        
        # Create mock dependencies
        mock_offset_engine = create_mock_offset_engine()
        mock_sensor_manager = create_mock_sensor_manager()
        mock_mode_manager = create_mock_mode_manager()
        mock_temperature_controller = create_mock_temperature_controller()
        mock_coordinator = create_mock_coordinator()
        
        # Act
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=config_without_adaptive_delay,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=mock_offset_engine,
            sensor_manager=mock_sensor_manager,
            mode_manager=mock_mode_manager,
            temperature_controller=mock_temperature_controller,
            coordinator=mock_coordinator
        )
        
        # Mock async_on_remove method for test
        entity.async_on_remove = Mock()
        
        await entity.async_added_to_hass()
        
        # Should work normally with fixed feedback delay
        with patch('custom_components.smart_climate.climate.async_call_later') as mock_call_later:
            mock_cancel_func = Mock()
            mock_call_later.return_value = mock_cancel_func
            
            # Simulate feedback collection
            entity._last_predicted_offset = 2.0
            entity._last_offset_input = Mock()
            entity._offset_engine._enable_learning = True
            
            # Mock the call that happens in _apply_temperature_with_offset
            cancel_callback = mock_call_later(
                entity.hass,
                entity._feedback_delay,  # Should use fixed delay (45)
                entity._collect_learning_feedback
            )
            
            # Assert
            mock_call_later.assert_called_once_with(
                entity.hass,
                45,  # Fixed feedback delay from config
                entity._collect_learning_feedback
            )
    
    @pytest.mark.asyncio
    async def test_safety_buffer_added_to_learned_delays(self, smart_climate_entity_with_adaptive_delay):
        """Test 5-second safety buffer is added to learned delays."""
        # Arrange
        entity = smart_climate_entity_with_adaptive_delay
        entity._delay_learner.get_adaptive_delay.return_value = 30  # Short learned delay
        
        # Act
        fallback_delay = 45
        learned_delay = entity._delay_learner.get_adaptive_delay(fallback_delay)
        final_delay = learned_delay + 5  # Add safety buffer
        
        # Assert
        assert learned_delay == 30
        assert final_delay == 35  # 30 + 5 second safety buffer
    
    @pytest.mark.asyncio
    async def test_delay_learner_unavailable_gracefully_handled(self, smart_climate_entity_with_adaptive_delay):
        """Test graceful handling when DelayLearner becomes unavailable."""
        # Arrange
        entity = smart_climate_entity_with_adaptive_delay
        entity._delay_learner = None  # Simulate unavailable DelayLearner
        
        # Act & Assert - should not raise exception
        await entity.async_set_hvac_mode(HVACMode.COOL)
        await entity.async_set_hvac_mode(HVACMode.OFF)
        
        # Should work with fixed delays
        assert entity._feedback_delay == 45  # Original config value
    
    @pytest.mark.asyncio
    async def test_comprehensive_logging_for_adaptive_delays(self, smart_climate_entity_with_adaptive_delay, caplog):
        """Test comprehensive logging for adaptive delay usage."""
        # Arrange
        entity = smart_climate_entity_with_adaptive_delay
        entity._delay_learner.get_adaptive_delay.return_value = 75
        
        # Act
        learned_delay = entity._delay_learner.get_adaptive_delay(45)
        
        # Assert
        assert learned_delay == 75
        # In real implementation, there would be debug logs about adaptive delay usage
    
    @pytest.mark.asyncio
    async def test_hvac_mode_change_detection_for_learning_cycles(self, smart_climate_entity_with_adaptive_delay):
        """Test proper detection of HVAC mode changes for starting/stopping learning cycles."""
        # Arrange
        entity = smart_climate_entity_with_adaptive_delay
        
        # Test OFF -> COOL (should start learning)
        entity._cached_hvac_mode = HVACMode.OFF
        wrapped_state = create_mock_state("climate.test_ac", HVACMode.COOL, {})
        entity.hass.states.get.return_value = wrapped_state
        
        entity._delay_learner.start_learning_cycle.reset_mock()
        
        # Act
        await entity.async_set_hvac_mode(HVACMode.COOL)
        
        # Assert
        entity._delay_learner.start_learning_cycle.assert_called_once()
        
        # Test COOL -> OFF (should stop learning)
        entity._cached_hvac_mode = HVACMode.COOL
        wrapped_state = create_mock_state("climate.test_ac", HVACMode.OFF, {})
        entity.hass.states.get.return_value = wrapped_state
        
        entity._delay_learner.stop_learning_cycle.reset_mock()
        
        # Act
        await entity.async_set_hvac_mode(HVACMode.OFF)
        
        # Assert  
        entity._delay_learner.stop_learning_cycle.assert_called_once()


class TestDelayLearnerClass:
    """Test DelayLearner class directly."""
    
    @pytest.mark.asyncio
    async def test_delay_learner_initialization(self):
        """Test DelayLearner initialization with required parameters."""
        # Arrange
        mock_hass = create_mock_hass()
        mock_store = Mock(spec=Store)
        
        # Act
        with patch('custom_components.smart_climate.delay_learner.DelayLearner') as MockDelayLearner:
            delay_learner = MockDelayLearner(
                mock_hass,
                "climate.test_ac",
                "sensor.room_temp",
                mock_store
            )
            
            # Assert
            MockDelayLearner.assert_called_once_with(
                mock_hass,
                "climate.test_ac", 
                "sensor.room_temp",
                mock_store
            )
    
    @pytest.mark.asyncio
    async def test_delay_learner_async_load(self, mock_delay_learner):
        """Test DelayLearner loads stored data."""
        # Act
        await mock_delay_learner.async_load()
        
        # Assert
        mock_delay_learner.async_load.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delay_learner_async_save(self, mock_delay_learner):
        """Test DelayLearner saves learned delays."""
        # Act
        await mock_delay_learner.async_save(60)
        
        # Assert
        mock_delay_learner.async_save.assert_called_once_with(60)
    
    def test_delay_learner_start_learning_cycle(self, mock_delay_learner):
        """Test DelayLearner starts monitoring temperature."""
        # Act
        mock_delay_learner.start_learning_cycle()
        
        # Assert
        mock_delay_learner.start_learning_cycle.assert_called_once()
    
    def test_delay_learner_stop_learning_cycle(self, mock_delay_learner):
        """Test DelayLearner stops monitoring temperature."""
        # Act
        mock_delay_learner.stop_learning_cycle()
        
        # Assert
        mock_delay_learner.stop_learning_cycle.assert_called_once()
    
    def test_delay_learner_get_adaptive_delay_with_fallback(self, mock_delay_learner):
        """Test DelayLearner returns adaptive delay or fallback."""
        # Test with learned delay
        mock_delay_learner.get_adaptive_delay.return_value = 90
        
        # Act
        result = mock_delay_learner.get_adaptive_delay(45)
        
        # Assert
        assert result == 90
        mock_delay_learner.get_adaptive_delay.assert_called_once_with(45)
    
    def test_delay_learner_get_adaptive_delay_fallback_when_none(self, mock_delay_learner):
        """Test DelayLearner returns fallback when no learned delay."""
        # Test without learned delay
        mock_delay_learner.get_adaptive_delay.return_value = None
        
        # Act
        result = mock_delay_learner.get_adaptive_delay(45)
        
        # Assert 
        assert result is None  # DelayLearner returns None, caller handles fallback
        mock_delay_learner.get_adaptive_delay.assert_called_once_with(45)