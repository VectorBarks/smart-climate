"""Tests for learning enable/disable state persistence (Issue #35).

This test module verifies that the learning enable/disable preference is correctly
restored after Home Assistant restarts. Users who disable learning should find it
still disabled after restart, and vice versa.
"""
import pytest
from unittest.mock import Mock, AsyncMock
import asyncio

from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.lightweight_learner import LightweightOffsetLearner as EnhancedLightweightOffsetLearner
from custom_components.smart_climate.const import (
    CONF_ENABLE_LEARNING,
    CONF_POWER_SENSOR,
    DEFAULT_SAVE_INTERVAL,
)


class TestLearningStatePersistence:
    """Test suite for Issue #35: Learning enable/disable state persistence."""

    @pytest.fixture
    def mock_data_store(self):
        """Create a mock data store for testing."""
        data_store = Mock()
        data_store.async_save_learning_data = AsyncMock()
        data_store.async_load_learning_data = AsyncMock()
        return data_store

    @pytest.fixture
    def config_learning_enabled(self):
        """Create a config with learning enabled by default."""
        return {
            CONF_ENABLE_LEARNING: True,
            "max_offset": 5.0,
            "ml_enabled": True,
        }

    @pytest.fixture
    def config_learning_disabled(self):
        """Create a config with learning disabled by default."""
        return {
            CONF_ENABLE_LEARNING: False,
            "max_offset": 5.0,
            "ml_enabled": True,
        }

    @pytest.mark.asyncio
    async def test_learning_disabled_state_restored_after_restart(self, config_learning_enabled, mock_data_store):
        """Test that learning disabled state is restored after HA restart.
        
        This is the core issue: User disables learning via switch, restarts HA,
        learning should still be disabled.
        """
        # Simulate saved data where learning was disabled
        saved_data = {
            "version": "2.0",
            "engine_state": {
                "enable_learning": False  # User had disabled learning
            },
            "learner_data": None,
            "hysteresis_data": None,
        }
        mock_data_store.async_load_learning_data.return_value = saved_data
        
        # Create engine with config default enabled (simulating fresh startup)
        engine = OffsetEngine(config_learning_enabled)
        engine._data_store = mock_data_store
        
        # Verify initial state from config
        assert engine._enable_learning is True, "Config should set learning enabled initially"
        
        # Load persisted data (simulating HA restart)
        result = await engine.async_load_learning_data()
        
        # Verify restoration
        assert result is True, "Load should succeed"
        assert engine._enable_learning is False, "Learning state should be restored to disabled"

    @pytest.mark.asyncio
    async def test_learning_enabled_state_restored_after_restart(self, config_learning_disabled, mock_data_store):
        """Test that learning enabled state is restored after HA restart."""
        # Simulate saved data where learning was enabled
        saved_data = {
            "version": "2.0",
            "engine_state": {
                "enable_learning": True  # User had enabled learning
            },
            "learner_data": {
                "version": "1.1",
                "time_patterns": {},  # No patterns learned yet
                "time_pattern_counts": {},
                "temp_correlation_data": [],
                "power_state_patterns": {},
                "enhanced_samples": [],
                "sample_count": 0,
            },
            "hysteresis_data": None,
        }
        mock_data_store.async_load_learning_data.return_value = saved_data
        
        # Create engine with config default disabled (simulating fresh startup)
        engine = OffsetEngine(config_learning_disabled)
        engine._data_store = mock_data_store
        
        # Verify initial state from config
        assert engine._enable_learning is False, "Config should set learning disabled initially"
        
        # Load persisted data (simulating HA restart)
        result = await engine.async_load_learning_data()
        
        # Verify restoration
        assert result is True, "Load should succeed"
        assert engine._enable_learning is True, "Learning state should be restored to enabled"
        assert engine._learner is not None, "Learner should be initialized when enabled"

    @pytest.mark.asyncio
    async def test_missing_engine_state_uses_config_default(self, config_learning_enabled, mock_data_store):
        """Test that missing engine_state falls back to config default."""
        # Simulate old save format without engine_state
        saved_data = {
            "version": "1.0",  # Old version
            "learner_data": None,
            # No engine_state key
        }
        mock_data_store.async_load_learning_data.return_value = saved_data
        
        engine = OffsetEngine(config_learning_enabled)
        engine._data_store = mock_data_store
        
        # Load data
        result = await engine.async_load_learning_data()
        
        # Should fall back to config default
        assert result is True, "Load should succeed"
        assert engine._enable_learning is True, "Should keep config default when no engine_state"

    @pytest.mark.asyncio
    async def test_corrupted_engine_state_uses_config_default(self, config_learning_disabled, mock_data_store):
        """Test that corrupted engine_state falls back to config default gracefully."""
        # Simulate corrupted engine_state
        saved_data = {
            "version": "2.0",
            "engine_state": "not_a_dict",  # Corrupted data
            "learner_data": None,
            "hysteresis_data": None,
        }
        mock_data_store.async_load_learning_data.return_value = saved_data
        
        engine = OffsetEngine(config_learning_disabled)
        engine._data_store = mock_data_store
        
        # Load data
        result = await engine.async_load_learning_data()
        
        # Should handle corruption gracefully
        assert result is True, "Load should succeed despite corruption"
        assert engine._enable_learning is False, "Should keep config default when engine_state corrupted"

    @pytest.mark.asyncio
    async def test_missing_enable_learning_key_uses_config_default(self, config_learning_enabled, mock_data_store):
        """Test that missing enable_learning key in engine_state uses config default."""
        # Simulate partial engine_state without enable_learning
        saved_data = {
            "version": "2.0",
            "engine_state": {
                "some_other_setting": "value"
                # Missing enable_learning key
            },
            "learner_data": None,
            "hysteresis_data": None,
        }
        mock_data_store.async_load_learning_data.return_value = saved_data
        
        engine = OffsetEngine(config_learning_enabled)
        engine._data_store = mock_data_store
        
        # Load data
        result = await engine.async_load_learning_data()
        
        # Should use config default
        assert result is True, "Load should succeed"
        assert engine._enable_learning is True, "Should keep config default when enable_learning key missing"

    @pytest.mark.asyncio
    async def test_learner_initialization_on_enabled_restoration(self, config_learning_disabled, mock_data_store):
        """Test that learner is properly initialized when learning is restored to enabled."""
        # Simulate saved data where learning was enabled
        saved_data = {
            "version": "2.0",
            "engine_state": {
                "enable_learning": True
            },
            "learner_data": {
                "version": "1.1",
                "time_patterns": {0: -0.5},  # Hour 0 pattern
                "time_pattern_counts": {0: 1},  # Count for hour 0
                "temp_correlation_data": [],
                "power_state_patterns": {},
                "enhanced_samples": [
                    {
                        "predicted": -1.0,
                        "actual": -1.0,
                        "ac_temp": 22.0,
                        "room_temp": 23.0,
                        "outdoor_temp": None,
                        "mode": "cool",
                        "power": None,
                        "hysteresis_state": "no_power_sensor",
                        "timestamp": "2025-07-13T20:00:00"
                    }
                ],
                "sample_count": 1,
            },
            "hysteresis_data": None,
        }
        mock_data_store.async_load_learning_data.return_value = saved_data
        
        # Start with learning disabled
        engine = OffsetEngine(config_learning_disabled)
        engine._data_store = mock_data_store
        
        assert engine._enable_learning is False
        assert engine._learner is None  # No learner when disabled
        
        # Load data
        result = await engine.async_load_learning_data()
        
        # Verify learner is created and data restored
        assert result is True
        assert engine._enable_learning is True, "Learning should be enabled"
        assert engine._learner is not None, "Learner should be initialized"
        
        # Verify learner data was restored
        assert engine._learner._sample_count == 1, "Sample count should be restored"
        assert len(engine._learner._enhanced_samples) == 1, "Samples should be restored"

    @pytest.mark.asyncio
    async def test_switch_ui_synchronization_disabled_to_enabled(self, config_learning_disabled, mock_data_store):
        """Test that switch UI stays synchronized with engine state changes."""
        # This test verifies the switch entity reflects the restored state
        # Note: This tests the engine state; actual switch testing would be in switch entity tests
        
        saved_data = {
            "version": "2.0",
            "engine_state": {
                "enable_learning": True  # User enabled it before restart
            },
            "learner_data": {
                "version": "1.1",
                "enhanced_samples": [],
                "sample_count": 0,
                "time_patterns": [0.0] * 24,
            },
        }
        mock_data_store.async_load_learning_data.return_value = saved_data
        
        engine = OffsetEngine(config_learning_disabled)
        engine._data_store = mock_data_store
        
        # Track state changes via callback
        state_changes = []
        def track_changes():
            state_changes.append(engine._enable_learning)
        
        engine._update_callbacks.append(track_changes)
        
        # Load data
        await engine.async_load_learning_data()
        
        # Verify state change was notified
        assert engine._enable_learning is True
        assert len(state_changes) > 0, "Update callbacks should be notified"
        assert state_changes[-1] is True, "Latest state should be enabled"

    @pytest.mark.asyncio
    async def test_switch_ui_synchronization_enabled_to_disabled(self, config_learning_enabled, mock_data_store):
        """Test that switch UI reflects disabled state after restoration."""
        saved_data = {
            "version": "2.0",
            "engine_state": {
                "enable_learning": False  # User disabled it before restart
            },
            "learner_data": None,
        }
        mock_data_store.async_load_learning_data.return_value = saved_data
        
        engine = OffsetEngine(config_learning_enabled)
        engine._data_store = mock_data_store
        
        # Track state changes
        state_changes = []
        def track_changes():
            state_changes.append(engine._enable_learning)
        
        engine._update_callbacks.append(track_changes)
        
        # Load data
        await engine.async_load_learning_data()
        
        # Verify state change was notified
        assert engine._enable_learning is False
        assert len(state_changes) > 0, "Update callbacks should be notified"
        assert state_changes[-1] is False, "Latest state should be disabled"

    @pytest.mark.asyncio
    async def test_no_state_change_when_same_as_config(self, config_learning_enabled, mock_data_store):
        """Test that no unnecessary state changes occur when persisted state matches config."""
        saved_data = {
            "version": "2.0",
            "engine_state": {
                "enable_learning": True  # Same as config default
            },
            "learner_data": None,
        }
        mock_data_store.async_load_learning_data.return_value = saved_data
        
        engine = OffsetEngine(config_learning_enabled)
        engine._data_store = mock_data_store
        
        # Track state changes
        state_changes = []
        def track_changes():
            state_changes.append(engine._enable_learning)
        
        engine._update_callbacks.append(track_changes)
        
        # Load data
        await engine.async_load_learning_data()
        
        # State should remain the same
        assert engine._enable_learning is True
        # Update callback should still be called once for general data load
        assert len(state_changes) >= 1, "Update callback should be called"

    @pytest.mark.asyncio
    async def test_concurrent_load_operations_stability(self, config_learning_enabled, mock_data_store):
        """Test that concurrent load operations don't cause race conditions."""
        saved_data = {
            "version": "2.0",
            "engine_state": {
                "enable_learning": False
            },
            "learner_data": None,
        }
        mock_data_store.async_load_learning_data.return_value = saved_data
        
        engine = OffsetEngine(config_learning_enabled)
        engine._data_store = mock_data_store
        
        # Run multiple concurrent loads
        tasks = [engine.async_load_learning_data() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        # All should succeed and state should be consistent
        assert all(results), "All loads should succeed"
        assert engine._enable_learning is False, "Final state should be disabled"

    @pytest.mark.asyncio
    async def test_data_store_unavailable_preserves_config_state(self, config_learning_disabled):
        """Test that unavailable data store preserves config state."""
        # No data store configured
        engine = OffsetEngine(config_learning_disabled)
        # engine._data_store is None
        
        # Attempt to load
        result = await engine.async_load_learning_data()
        
        # Should fail gracefully and preserve config state
        assert result is False, "Load should fail with no data store"
        assert engine._enable_learning is False, "Should preserve config state"

    @pytest.mark.asyncio
    async def test_load_exception_preserves_config_state(self, config_learning_enabled, mock_data_store):
        """Test that load exceptions preserve config state."""
        # Configure data store to raise exception
        mock_data_store.async_load_learning_data.side_effect = Exception("Storage error")
        
        engine = OffsetEngine(config_learning_enabled)
        engine._data_store = mock_data_store
        
        # Attempt to load
        result = await engine.async_load_learning_data()
        
        # Should fail gracefully and preserve config state
        assert result is False, "Load should fail with exception"
        assert engine._enable_learning is True, "Should preserve config state"

    @pytest.mark.asyncio
    async def test_empty_persistence_data_preserves_config_state(self, config_learning_disabled, mock_data_store):
        """Test that empty/None persistence data preserves config state."""
        # Return None (no saved data)
        mock_data_store.async_load_learning_data.return_value = None
        
        engine = OffsetEngine(config_learning_disabled)
        engine._data_store = mock_data_store
        
        # Load data
        result = await engine.async_load_learning_data()
        
        # Should preserve config state
        assert result is False, "Load should return False for no data"
        assert engine._enable_learning is False, "Should preserve config state"

    @pytest.mark.asyncio
    async def test_round_trip_save_and_load_consistency(self, config_learning_enabled, mock_data_store):
        """Test that save and load operations are consistent."""
        engine = OffsetEngine(config_learning_enabled)
        engine._data_store = mock_data_store
        
        # Change state and save
        engine._enable_learning = False
        await engine.async_save_learning_data()
        
        # Get the saved data
        saved_data = mock_data_store.async_save_learning_data.call_args[0][0]
        mock_data_store.async_load_learning_data.return_value = saved_data
        
        # Reset engine to config default
        engine._enable_learning = True
        
        # Load and verify restoration
        result = await engine.async_load_learning_data()
        assert result is True
        assert engine._enable_learning is False, "State should be restored to saved value"