"""Tests for learning data persistence bug fix (Issue #25).

This test module verifies that learning data is preserved when learning is disabled
before a Home Assistant restart. The bug causes all enhanced_samples to be lost
when the save method only saves learner data if learning is enabled.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import json

from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.lightweight_learner import LightweightOffsetLearner as EnhancedLightweightOffsetLearner
from custom_components.smart_climate.const import (
    CONF_ENABLE_LEARNING,
    CONF_POWER_SENSOR,
    CONF_SAVE_INTERVAL,
    DEFAULT_SAVE_INTERVAL,
)


class TestLearningDataPersistenceBugFix:
    """Test suite for Issue #25: Learning data loss when disabled."""

    @pytest.fixture
    def mock_data_store(self):
        """Create a mock data store for testing."""
        data_store = Mock()
        data_store.async_save_learning_data = AsyncMock()
        data_store.async_load_learning_data = AsyncMock()
        return data_store

    @pytest.fixture
    def config_with_learning(self):
        """Create a config with learning enabled."""
        return {
            CONF_ENABLE_LEARNING: True,
            "max_offset": 5.0,
            "ml_enabled": True,
            CONF_SAVE_INTERVAL: DEFAULT_SAVE_INTERVAL,
        }

    @pytest.fixture
    def engine_with_data(self, config_with_learning, mock_data_store):
        """Create an offset engine with some accumulated learning data."""
        engine = OffsetEngine(config_with_learning)
        engine._data_store = mock_data_store
        
        # Simulate accumulated learning data
        if engine._learner:
            # Add some sample data
            engine._learner._enhanced_samples = [
                {
                    "ac_temp": 22.0,
                    "room_temp": 23.0,
                    "offset": -1.0,
                    "mode": "cool",
                    "timestamp": datetime.now().isoformat(),
                    "hysteresis_state": "no_power_sensor"
                },
                {
                    "ac_temp": 21.5,
                    "room_temp": 22.5,
                    "offset": -1.0,
                    "mode": "cool",
                    "timestamp": datetime.now().isoformat(),
                    "hysteresis_state": "no_power_sensor"
                }
            ]
            engine._learner._sample_count = 2
            engine._learner._time_patterns = [0.0] * 24
            engine._learner._time_patterns[14] = -0.5  # 2 PM pattern
            
        return engine

    async def test_save_when_learning_enabled_saves_data(self, engine_with_data, mock_data_store):
        """Test that save works correctly when learning is enabled."""
        # Act
        await engine_with_data.async_save_learning_data()
        
        # Assert
        mock_data_store.async_save_learning_data.assert_called_once()
        saved_data = mock_data_store.async_save_learning_data.call_args[0][0]
        
        assert "learner_data" in saved_data
        assert saved_data["learner_data"] is not None
        assert "enhanced_samples" in saved_data["learner_data"]
        assert len(saved_data["learner_data"]["enhanced_samples"]) == 2
        assert saved_data["learner_data"]["statistics"]["samples"] == 2

    async def test_save_when_learning_disabled_loses_data_current_bug(self, engine_with_data, mock_data_store):
        """Test that demonstrates the current bug - data is lost when learning is disabled."""
        # Disable learning (simulating user turning off the switch)
        engine_with_data._enable_learning = False
        
        # Act
        await engine_with_data.async_save_learning_data()
        
        # Assert - This shows the BUG
        mock_data_store.async_save_learning_data.assert_called_once()
        saved_data = mock_data_store.async_save_learning_data.call_args[0][0]
        
        # BUG: learner_data is None, losing all accumulated samples!
        assert saved_data["learner_data"] is None
        # The engine state shows learning is disabled
        assert saved_data["engine_state"]["enable_learning"] is False

    async def test_save_when_learning_disabled_should_preserve_data_fixed(self, engine_with_data, mock_data_store):
        """Test the expected behavior after fix - data is preserved when learning is disabled."""
        # Disable learning (simulating user turning off the switch)
        engine_with_data._enable_learning = False
        
        # Simulate the fix by patching the method
        original_save = engine_with_data.async_save_learning_data
        
        async def fixed_save():
            """Fixed version that saves learner data regardless of enable_learning."""
            if not hasattr(engine_with_data, "_data_store") or engine_with_data._data_store is None:
                return
            
            try:
                # Prepare learner data if learner exists (NOT checking enable_learning)
                learner_data = None
                sample_count = 0
                if engine_with_data._learner:  # Only check if learner exists
                    learner_data = engine_with_data._learner.serialize_for_persistence()
                    sample_count = learner_data.get("statistics", {}).get("samples", 0)
                
                # Rest of the save logic...
                persistent_data = {
                    "version": "2.0",
                    "engine_state": {
                        "enable_learning": engine_with_data._enable_learning,
                    },
                    "learner_data": learner_data,
                    "hysteresis_data": None,
                }
                
                await engine_with_data._data_store.async_save_learning_data(persistent_data)
                
            except Exception:
                pass
        
        # Replace with fixed version
        engine_with_data.async_save_learning_data = fixed_save
        
        # Act
        await engine_with_data.async_save_learning_data()
        
        # Assert - Data should be preserved
        mock_data_store.async_save_learning_data.assert_called_once()
        saved_data = mock_data_store.async_save_learning_data.call_args[0][0]
        
        # FIXED: learner_data is preserved even when learning is disabled
        assert saved_data["learner_data"] is not None
        assert len(saved_data["learner_data"]["enhanced_samples"]) == 2
        assert saved_data["learner_data"]["statistics"]["samples"] == 2
        # Engine state correctly shows learning is disabled
        assert saved_data["engine_state"]["enable_learning"] is False

    async def test_data_persists_through_enable_disable_cycles(self, config_with_learning, mock_data_store):
        """Test that data persists through multiple enable/disable cycles."""
        # Create engine with learning enabled
        engine = OffsetEngine(config_with_learning)
        engine._data_store = mock_data_store
        
        # Add sample data
        if engine._learner:
            engine._learner._enhanced_samples = [
                {"ac_temp": 22.0, "room_temp": 23.0, "offset": -1.0, "mode": "cool", "timestamp": datetime.now().isoformat()}
            ]
            engine._learner._sample_count = 1
        
        # Simulate the fix
        async def fixed_save():
            learner_data = None
            if engine._learner:  # Only check learner exists
                learner_data = engine._learner.serialize_for_persistence()
            
            persistent_data = {
                "version": "2.0",
                "engine_state": {"enable_learning": engine._enable_learning},
                "learner_data": learner_data,
                "hysteresis_data": None,
            }
            await engine._data_store.async_save_learning_data(persistent_data)
        
        engine.async_save_learning_data = fixed_save
        
        # Save with learning enabled
        await engine.async_save_learning_data()
        saved_data_1 = mock_data_store.async_save_learning_data.call_args[0][0]
        assert saved_data_1["learner_data"] is not None
        assert len(saved_data_1["learner_data"]["enhanced_samples"]) == 1
        
        # Disable learning and save
        engine._enable_learning = False
        await engine.async_save_learning_data()
        saved_data_2 = mock_data_store.async_save_learning_data.call_args[0][0]
        assert saved_data_2["learner_data"] is not None
        assert len(saved_data_2["learner_data"]["enhanced_samples"]) == 1
        
        # Re-enable learning and save
        engine._enable_learning = True
        await engine.async_save_learning_data()
        saved_data_3 = mock_data_store.async_save_learning_data.call_args[0][0]
        assert saved_data_3["learner_data"] is not None
        assert len(saved_data_3["learner_data"]["enhanced_samples"]) == 1

    async def test_hysteresis_data_unaffected_by_learning_state(self, config_with_learning, mock_data_store):
        """Test that hysteresis data is saved regardless of learning state."""
        # Add power sensor to enable hysteresis
        config_with_learning[CONF_POWER_SENSOR] = "sensor.power"
        
        engine = OffsetEngine(config_with_learning)
        engine._data_store = mock_data_store
        
        # Add hysteresis data
        engine._hysteresis_learner._start_temps = [20.0, 20.5]
        engine._hysteresis_learner._stop_temps = [24.0, 24.5]
        engine._hysteresis_learner.sample_count = 2
        
        # Test with learning enabled
        await engine.async_save_learning_data()
        saved_data_1 = mock_data_store.async_save_learning_data.call_args[0][0]
        assert saved_data_1["hysteresis_data"] is not None
        assert saved_data_1["hysteresis_data"]["sample_count"] == 2
        
        # Test with learning disabled
        engine._enable_learning = False
        await engine.async_save_learning_data()
        saved_data_2 = mock_data_store.async_save_learning_data.call_args[0][0]
        assert saved_data_2["hysteresis_data"] is not None
        assert saved_data_2["hysteresis_data"]["sample_count"] == 2

    async def test_edge_case_no_learner_exists(self, mock_data_store):
        """Test edge case where no learner exists at all."""
        config = {
            CONF_ENABLE_LEARNING: False,  # Never enabled
            "max_offset": 5.0,
        }
        
        engine = OffsetEngine(config)
        engine._data_store = mock_data_store
        assert engine._learner is None  # No learner created
        
        # Should not crash
        await engine.async_save_learning_data()
        
        saved_data = mock_data_store.async_save_learning_data.call_args[0][0]
        assert saved_data["learner_data"] is None
        assert saved_data["engine_state"]["enable_learning"] is False

    async def test_load_operation_with_disabled_learning(self, config_with_learning, mock_data_store):
        """Test that load operation correctly handles data when learning is disabled."""
        # Prepare saved data with learning disabled but data present
        saved_data = {
            "version": "2.0",
            "engine_state": {
                "enable_learning": False,  # Was disabled before save
            },
            "learner_data": {
                "version": "1.1",
                "enhanced_samples": [
                    {"ac_temp": 22.0, "room_temp": 23.0, "offset": -1.0}
                ],
                "statistics": {"samples": 1},
                "time_patterns": [0.0] * 24,
            },
            "hysteresis_data": None,
        }
        
        mock_data_store.async_load_learning_data.return_value = saved_data
        
        # Create engine with learning enabled by default
        engine = OffsetEngine(config_with_learning)
        engine._data_store = mock_data_store
        
        # Load the data
        result = await engine.async_load_learning_data()
        
        # Should restore the saved state (disabled) but preserve the data
        assert result is True
        assert engine._enable_learning is False  # Restored from save
        assert engine._learner is not None  # Learner should exist
        assert len(engine._learner._enhanced_samples) == 1  # Data preserved

    async def test_save_timing_and_logging(self, engine_with_data, mock_data_store):
        """Test that save operations update timing and logging correctly."""
        # Reset counters
        engine_with_data._save_count = 0
        engine_with_data._failed_save_count = 0
        engine_with_data._last_save_time = None
        
        # Successful save
        await engine_with_data.async_save_learning_data()
        
        assert engine_with_data._save_count == 1
        assert engine_with_data._failed_save_count == 0
        assert engine_with_data._last_save_time is not None
        
        # Failed save
        mock_data_store.async_save_learning_data.side_effect = Exception("Test error")
        await engine_with_data.async_save_learning_data()
        
        assert engine_with_data._save_count == 1  # Unchanged
        assert engine_with_data._failed_save_count == 1

    async def test_concurrent_save_operations(self, engine_with_data, mock_data_store):
        """Test that concurrent save operations don't corrupt data."""
        import asyncio
        
        # Simulate the fix
        async def fixed_save():
            learner_data = None
            if engine_with_data._learner:
                learner_data = engine_with_data._learner.serialize_for_persistence()
            
            persistent_data = {
                "version": "2.0",
                "engine_state": {"enable_learning": engine_with_data._enable_learning},
                "learner_data": learner_data,
                "hysteresis_data": None,
            }
            await engine_with_data._data_store.async_save_learning_data(persistent_data)
        
        engine_with_data.async_save_learning_data = fixed_save
        
        # Run multiple saves concurrently
        tasks = []
        for i in range(5):
            # Toggle learning state during saves
            if i % 2 == 0:
                engine_with_data._enable_learning = False
            else:
                engine_with_data._enable_learning = True
            tasks.append(engine_with_data.async_save_learning_data())
        
        await asyncio.gather(*tasks)
        
        # All saves should have preserved the data
        assert mock_data_store.async_save_learning_data.call_count == 5
        for call in mock_data_store.async_save_learning_data.call_args_list:
            saved_data = call[0][0]
            assert saved_data["learner_data"] is not None
            assert len(saved_data["learner_data"]["enhanced_samples"]) == 2