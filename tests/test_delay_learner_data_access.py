"""
ABOUTME: Integration tests for DelayLearner data access methods for dashboard integration.
Tests the new methods that expose DelayLearner data for OffsetEngine to use.
"""

import pytest
from datetime import timedelta
from unittest.mock import Mock, patch, AsyncMock
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from custom_components.smart_climate.delay_learner import DelayLearner


@pytest.fixture
def mock_store():
    """Create a mock store for testing."""
    store = Mock(spec=Store)
    store.async_load = AsyncMock(return_value=None)
    store.async_save = AsyncMock(return_value=None)
    return store


@pytest.fixture
def delay_learner(hass: HomeAssistant, mock_store):
    """Create a DelayLearner instance for testing."""
    return DelayLearner(
        hass=hass,
        entity_id="climate.test",
        room_sensor_entity_id="sensor.room_temp",
        store=mock_store,
        timeout_minutes=20
    )


class TestDelayLearnerDataAccess:
    """Test DelayLearner data access methods for dashboard integration."""
    
    @pytest.mark.asyncio
    async def test_get_adaptive_delay_with_learned_value(self, delay_learner: DelayLearner):
        """Test get_adaptive_delay returns learned value when available."""
        # Set a learned delay
        delay_learner._learned_delay_secs = 60
        
        # Test that it returns the learned value
        assert delay_learner.get_adaptive_delay() == 60
        assert delay_learner.get_adaptive_delay(fallback_delay=30) == 60
    
    @pytest.mark.asyncio
    async def test_get_adaptive_delay_with_fallback(self, delay_learner: DelayLearner):
        """Test get_adaptive_delay returns fallback when no learned value."""
        # No learned delay
        delay_learner._learned_delay_secs = None
        
        # Test default fallback
        assert delay_learner.get_adaptive_delay() == 45
        
        # Test custom fallback
        assert delay_learner.get_adaptive_delay(fallback_delay=30) == 30
    
    @pytest.mark.asyncio
    async def test_is_temperature_stable_not_learning(self, delay_learner: DelayLearner):
        """Test is_temperature_stable returns False when not in learning cycle."""
        # Not in learning cycle
        delay_learner._cancel_listener = None
        delay_learner._last_temp = None
        
        assert delay_learner.is_temperature_stable() is False
    
    @pytest.mark.asyncio
    async def test_is_temperature_stable_during_learning(self, delay_learner: DelayLearner):
        """Test is_temperature_stable during active learning cycle."""
        # Simulate active learning cycle
        delay_learner._cancel_listener = Mock()  # Active listener
        delay_learner._last_temp = 22.5
        delay_learner._temp_history = [
            (Mock(), 22.45),
            (Mock(), 22.46),
            (Mock(), 22.48),
            (Mock(), 22.5),  # Temperature stabilizing with small variations
        ]
        
        # Temperature variation is 0.05°C (22.5 - 22.45), which is < 0.1°C threshold
        assert delay_learner.is_temperature_stable() is True
    
    @pytest.mark.asyncio
    async def test_is_temperature_stable_unstable_temp(self, delay_learner: DelayLearner):
        """Test is_temperature_stable when temperature is still changing."""
        # Simulate active learning with changing temperature
        delay_learner._cancel_listener = Mock()  # Active listener
        delay_learner._last_temp = 22.5
        delay_learner._temp_history = [
            (Mock(), 24.0),
            (Mock(), 23.5),
            (Mock(), 23.0),
            (Mock(), 22.5),  # Still dropping significantly
        ]
        
        # Temperature is still changing
        assert delay_learner.is_temperature_stable() is False
    
    @pytest.mark.asyncio
    async def test_get_learned_delay_with_value(self, delay_learner: DelayLearner):
        """Test get_learned_delay returns the learned delay value."""
        # Set a learned delay
        delay_learner._learned_delay_secs = 75
        
        assert delay_learner.get_learned_delay() == 75
    
    @pytest.mark.asyncio
    async def test_get_learned_delay_no_value(self, delay_learner: DelayLearner):
        """Test get_learned_delay returns 0 when no learned value."""
        # No learned delay
        delay_learner._learned_delay_secs = None
        
        assert delay_learner.get_learned_delay() == 0
    
    @pytest.mark.asyncio
    async def test_methods_handle_none_gracefully(self, delay_learner: DelayLearner):
        """Test all methods handle None/missing data gracefully."""
        # Ensure everything is None/empty
        delay_learner._learned_delay_secs = None
        delay_learner._cancel_listener = None
        delay_learner._last_temp = None
        delay_learner._temp_history = []
        
        # All methods should return safe defaults
        assert delay_learner.get_adaptive_delay() == 45  # default fallback
        assert delay_learner.is_temperature_stable() is False
        assert delay_learner.get_learned_delay() == 0
    
    @pytest.mark.asyncio
    async def test_thread_safety_considerations(self, delay_learner: DelayLearner):
        """Test that methods are safe to call from different contexts."""
        # This is more of a documentation test - the methods should be read-only
        # and not modify internal state
        
        initial_delay = delay_learner._learned_delay_secs
        initial_listener = delay_learner._cancel_listener
        initial_temp = delay_learner._last_temp
        initial_history = delay_learner._temp_history.copy() if delay_learner._temp_history else []
        
        # Call all read methods
        delay_learner.get_adaptive_delay()
        delay_learner.is_temperature_stable()
        delay_learner.get_learned_delay()
        
        # Verify no state was modified
        assert delay_learner._learned_delay_secs == initial_delay
        assert delay_learner._cancel_listener == initial_listener
        assert delay_learner._last_temp == initial_temp
        assert delay_learner._temp_history == initial_history
    
    @pytest.mark.asyncio
    async def test_integration_with_offset_engine(self, hass: HomeAssistant, delay_learner: DelayLearner):
        """Test that DelayLearner methods work correctly when called from OffsetEngine."""
        # This test simulates how OffsetEngine will use these methods
        from custom_components.smart_climate.dto import DelayData
        
        # Set up some test data
        delay_learner._learned_delay_secs = 90
        delay_learner._cancel_listener = Mock()  # Active learning
        delay_learner._last_temp = 22.0
        delay_learner._temp_history = [(Mock(), 22.0)] * 4  # Stable temperature
        
        # Simulate what OffsetEngine will do
        delay_data = DelayData(
            adaptive_delay=float(delay_learner.get_adaptive_delay()),
            temperature_stability_detected=delay_learner.is_temperature_stable(),
            learned_delay_seconds=float(delay_learner.get_learned_delay())
        )
        
        # Verify the data structure is populated correctly
        assert delay_data.adaptive_delay == 90.0
        assert delay_data.temperature_stability_detected is True
        assert delay_data.learned_delay_seconds == 90.0
    
    @pytest.mark.asyncio
    async def test_edge_case_empty_temp_history(self, delay_learner: DelayLearner):
        """Test is_temperature_stable with empty temperature history."""
        delay_learner._cancel_listener = Mock()  # Active learning
        delay_learner._temp_history = []  # Empty history
        
        # Should return False as we have no history to determine stability
        assert delay_learner.is_temperature_stable() is False
    
    @pytest.mark.asyncio
    async def test_edge_case_single_temp_reading(self, delay_learner: DelayLearner):
        """Test is_temperature_stable with only one temperature reading."""
        delay_learner._cancel_listener = Mock()  # Active learning
        delay_learner._last_temp = 22.0
        delay_learner._temp_history = [(Mock(), 22.0)]  # Only one reading
        
        # Should return False as we need multiple readings to determine stability
        assert delay_learner.is_temperature_stable() is False