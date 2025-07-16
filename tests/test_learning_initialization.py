"""Tests for learning state initialization and persistence restoration."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, time
import json

from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.lightweight_learner import LightweightOffsetLearner
from custom_components.smart_climate.models import OffsetInput
from custom_components.smart_climate.data_store import SmartClimateDataStore


@pytest.fixture
def basic_config():
    """Basic configuration without learning enabled."""
    return {
        "max_offset": 5.0,
        "ml_enabled": True,
        "enable_learning": False  # Default to disabled
    }


@pytest.fixture
def learning_enabled_config():
    """Configuration with learning explicitly enabled."""
    return {
        "max_offset": 5.0,
        "ml_enabled": True,
        "enable_learning": True
    }


@pytest.fixture
def mock_data_store():
    """Mock data store for testing persistence."""
    mock_store = Mock(spec=SmartClimateDataStore)
    mock_store.async_save_learning_data = AsyncMock()
    mock_store.async_load_learning_data = AsyncMock()
    return mock_store


class TestLearningStateInitialization:
    """Test learning state initialization from configuration and persistence."""
    
    def test_initialization_learning_disabled_by_default(self, basic_config):
        """Test that learning is disabled by default during initialization."""
        engine = OffsetEngine(basic_config)
        
        assert not engine.is_learning_enabled
        assert engine._learner is None
        assert engine._enable_learning is False
    
    def test_initialization_learning_enabled_from_config(self, learning_enabled_config):
        """Test that learning can be enabled via configuration."""
        engine = OffsetEngine(learning_enabled_config)
        
        assert engine.is_learning_enabled
        assert engine._learner is not None
        assert isinstance(engine._learner, LightweightOffsetLearner)
    
    def test_learning_state_callbacks_registration(self, basic_config):
        """Test that state change callbacks can be registered."""
        engine = OffsetEngine(basic_config)
        callback_called = False
        
        def test_callback():
            nonlocal callback_called
            callback_called = True
        
        # Register callback
        unregister = engine.register_update_callback(test_callback)
        
        # Enable learning - should trigger callback
        engine.enable_learning()
        
        assert callback_called
        
        # Test unregistration
        callback_called = False
        unregister()
        engine.disable_learning()
        
        assert not callback_called  # Should not be called after unregistering


class TestLearningStatePersistence:
    """Test learning state persistence and restoration."""
    
    @pytest.fixture
    def engine_with_store(self, basic_config, mock_data_store):
        """Create engine with attached data store."""
        engine = OffsetEngine(basic_config)
        engine.set_data_store(mock_data_store)
        return engine, mock_data_store
    
    @pytest.mark.asyncio
    async def test_save_learning_state_disabled(self, engine_with_store):
        """Test saving when learning is disabled."""
        engine, mock_store = engine_with_store
        
        await engine.async_save_learning_data()
        
        # Should save engine state even when learning is disabled
        mock_store.async_save_learning_data.assert_called_once()
        saved_data = mock_store.async_save_learning_data.call_args[0][0]
        
        assert "engine_state" in saved_data
        assert saved_data["engine_state"]["enable_learning"] is False
        assert saved_data["learner_data"] is None
    
    @pytest.mark.asyncio
    async def test_save_learning_state_enabled(self, learning_enabled_config, mock_data_store):
        """Test saving when learning is enabled with data."""
        engine = OffsetEngine(learning_enabled_config)
        engine.set_data_store(mock_data_store)
        
        # Add some learning data
        input_data = OffsetInput(
            ac_internal_temp=25.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="normal",
            power_consumption=200.0,
            time_of_day=time(14, 30),
            day_of_week=1
        )
        engine.record_actual_performance(2.0, 1.5, input_data)
        
        await engine.async_save_learning_data()
        
        # Should save both engine state and learner data
        mock_data_store.async_save_learning_data.assert_called_once()
        saved_data = mock_data_store.async_save_learning_data.call_args[0][0]
        
        assert "engine_state" in saved_data
        assert saved_data["engine_state"]["enable_learning"] is True
        assert saved_data["learner_data"] is not None
        assert "samples" in saved_data["learner_data"]
    
    @pytest.mark.asyncio
    async def test_load_no_persistent_data(self, engine_with_store):
        """Test loading when no persistent data exists."""
        engine, mock_store = engine_with_store
        mock_store.async_load_learning_data.return_value = None
        
        result = await engine.async_load_learning_data()
        
        assert result is False
        assert not engine.is_learning_enabled  # Should remain as configured
    
    @pytest.mark.asyncio
    async def test_load_learning_disabled_state(self, learning_enabled_config, mock_data_store):
        """Test loading when persistent data shows learning was disabled."""
        # Start with learning enabled in config
        engine = OffsetEngine(learning_enabled_config)
        engine.set_data_store(mock_data_store)
        
        # Mock persistent data showing learning was disabled
        persistent_data = {
            "version": 1,
            "engine_state": {
                "enable_learning": False
            },
            "learner_data": None
        }
        mock_data_store.async_load_learning_data.return_value = persistent_data
        
        result = await engine.async_load_learning_data()
        
        assert result is True
        assert not engine.is_learning_enabled  # Should be overridden from persistence
        
    @pytest.mark.asyncio
    async def test_load_learning_enabled_state(self, basic_config, mock_data_store):
        """Test loading when persistent data shows learning was enabled."""
        # Start with learning disabled in config
        engine = OffsetEngine(basic_config)
        engine.set_data_store(mock_data_store)
        
        # Mock persistent data showing learning was enabled with sample data
        sample_data = {
            "samples": [
                {
                    "predicted": 2.0,
                    "actual": 1.5,
                    "ac_temp": 25.0,
                    "room_temp": 24.0,
                    "outdoor_temp": 30.0,
                    "mode": "normal",
                    "power": 200.0,
                    "hour": 14,
                    "day_of_week": 1,
                    "timestamp": datetime.now().isoformat()
                }
            ],
            "min_samples": 20,
            "max_samples": 1000,
            "has_sufficient_data": False
        }
        
        persistent_data = {
            "version": 1,
            "engine_state": {
                "enable_learning": True
            },
            "learner_data": sample_data
        }
        mock_data_store.async_load_learning_data.return_value = persistent_data
        
        result = await engine.async_load_learning_data()
        
        assert result is True
        assert engine.is_learning_enabled  # Should be overridden from persistence
        assert engine._learner is not None  # Learner should be created
        
        # Verify learner data was restored
        stats = engine.get_learning_info()
        assert stats["enabled"] is True
        assert stats["samples"] == 1
    
    @pytest.mark.asyncio 
    async def test_callbacks_triggered_on_state_restoration(self, basic_config, mock_data_store):
        """Test that callbacks are triggered when state is restored from persistence."""
        engine = OffsetEngine(basic_config)
        engine.set_data_store(mock_data_store)
        
        callback_called = False
        
        def test_callback():
            nonlocal callback_called
            callback_called = True
        
        engine.register_update_callback(test_callback)
        
        # Mock persistent data showing learning was enabled
        persistent_data = {
            "version": 1,
            "engine_state": {
                "enable_learning": True
            },
            "learner_data": None
        }
        mock_data_store.async_load_learning_data.return_value = persistent_data
        
        await engine.async_load_learning_data()
        
        assert callback_called  # Should be triggered by state change


class TestLearningStateIntegration:
    """Test integration scenarios with learning state and persistence."""
    
    @pytest.mark.asyncio
    async def test_multiple_restart_scenario(self, basic_config, mock_data_store):
        """Test multiple restart scenarios to ensure state persistence."""
        # First startup - learning disabled by config
        engine1 = OffsetEngine(basic_config)
        engine1.set_data_store(mock_data_store)
        assert not engine1.is_learning_enabled
        
        # User enables learning
        engine1.enable_learning()
        assert engine1.is_learning_enabled
        
        # Save state
        await engine1.async_save_learning_data()
        saved_data = mock_data_store.async_save_learning_data.call_args[0][0]
        
        # Simulate restart - new engine instance
        mock_data_store.async_load_learning_data.return_value = saved_data
        engine2 = OffsetEngine(basic_config)  # Same config (learning disabled)
        engine2.set_data_store(mock_data_store)
        
        # Load state - should restore learning enabled
        result = await engine2.async_load_learning_data()
        assert result is True
        assert engine2.is_learning_enabled  # Should be restored from persistence
        
        # User disables learning
        engine2.disable_learning()
        assert not engine2.is_learning_enabled
        
        # Save disabled state
        await engine2.async_save_learning_data()
        saved_data = mock_data_store.async_save_learning_data.call_args[0][0]
        
        # Another restart
        mock_data_store.async_load_learning_data.return_value = saved_data
        engine3 = OffsetEngine(basic_config)
        engine3.set_data_store(mock_data_store)
        
        # Load state - should restore learning disabled
        result = await engine3.async_load_learning_data()
        assert result is True
        assert not engine3.is_learning_enabled  # Should be restored as disabled
    
    @pytest.mark.asyncio
    async def test_corrupted_persistent_data_handling(self, basic_config, mock_data_store):
        """Test handling of corrupted or invalid persistent data."""
        engine = OffsetEngine(basic_config)
        engine.set_data_store(mock_data_store)
        
        # Test with completely invalid data
        mock_data_store.async_load_learning_data.return_value = "invalid_data"
        result = await engine.async_load_learning_data()
        assert result is False
        assert not engine.is_learning_enabled  # Should remain as configured
        
        # Test with missing engine_state
        mock_data_store.async_load_learning_data.return_value = {"learner_data": {}}
        result = await engine.async_load_learning_data()
        assert result is True  # Should succeed but not change state
        assert not engine.is_learning_enabled
        
        # Test with invalid engine_state type
        mock_data_store.async_load_learning_data.return_value = {
            "engine_state": "invalid_type"
        }
        result = await engine.async_load_learning_data()
        assert result is True  # Should succeed but not change state
        assert not engine.is_learning_enabled
    
    @pytest.mark.asyncio
    async def test_learning_starts_immediately_when_enabled(self, basic_config, mock_data_store):
        """Test that learning starts immediately when enabled from persistent state."""
        engine = OffsetEngine(basic_config)
        engine.set_data_store(mock_data_store)
        
        # Mock persistent data showing learning was enabled
        persistent_data = {
            "version": 1,
            "engine_state": {
                "enable_learning": True
            },
            "learner_data": None
        }
        mock_data_store.async_load_learning_data.return_value = persistent_data
        
        # Load state
        result = await engine.async_load_learning_data()
        assert result is True
        assert engine.is_learning_enabled
        
        # Test that learning functionality is immediately available
        input_data = OffsetInput(
            ac_internal_temp=25.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="normal",
            power_consumption=200.0,
            time_of_day=time(14, 30),
            day_of_week=1
        )
        
        # Should be able to record samples immediately
        engine.record_actual_performance(2.0, 1.5, input_data)
        
        # Verify learning info shows enabled state
        info = engine.get_learning_info()
        assert info["enabled"] is True
        assert info["samples"] == 1


class TestErrorCases:
    """Test error cases and edge conditions."""
    
    @pytest.mark.asyncio
    async def test_no_data_store_configured(self, basic_config):
        """Test behavior when no data store is configured."""
        engine = OffsetEngine(basic_config)
        # Don't set data store
        
        # Save should log warning but not fail
        await engine.async_save_learning_data()
        
        # Load should log warning and return False
        result = await engine.async_load_learning_data()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_data_store_exceptions(self, basic_config, mock_data_store):
        """Test handling of data store exceptions."""
        engine = OffsetEngine(basic_config)
        engine.set_data_store(mock_data_store)
        
        # Configure data store to raise exceptions
        mock_data_store.async_save_learning_data.side_effect = Exception("Save error")
        mock_data_store.async_load_learning_data.side_effect = Exception("Load error")
        
        # Save should not raise exception
        await engine.async_save_learning_data()
        
        # Load should not raise exception and return False
        result = await engine.async_load_learning_data()
        assert result is False
        assert not engine.is_learning_enabled  # Should remain unchanged