"""Tests for HysteresisLearner integration into OffsetEngine."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, time

from custom_components.smart_climate.offset_engine import OffsetEngine, HysteresisLearner
from custom_components.smart_climate.models import OffsetInput


class TestOffsetEngineHysteresisIntegration:
    """Test the integration of HysteresisLearner into OffsetEngine."""

    def test_initialization_with_power_sensor_configured(self):
        """Test OffsetEngine initialization when power sensor is configured."""
        config = {
            "max_offset": 5.0,
            "power_sensor": "sensor.ac_power",  # Power sensor configured
            "enable_learning": True
        }
        
        engine = OffsetEngine(config)
        
        # Hysteresis should be enabled when power sensor is configured
        assert hasattr(engine, '_hysteresis_enabled')
        assert engine._hysteresis_enabled is True
        assert hasattr(engine, '_hysteresis_learner')
        assert isinstance(engine._hysteresis_learner, HysteresisLearner)
        assert hasattr(engine, '_last_power_state')
        assert engine._last_power_state is None

    def test_initialization_without_power_sensor(self):
        """Test OffsetEngine initialization when no power sensor is configured."""
        config = {
            "max_offset": 5.0,
            "power_sensor": None,  # No power sensor
            "enable_learning": True
        }
        
        engine = OffsetEngine(config)
        
        # Hysteresis should be disabled when no power sensor is configured
        assert hasattr(engine, '_hysteresis_enabled')
        assert engine._hysteresis_enabled is False
        assert hasattr(engine, '_hysteresis_learner')
        assert isinstance(engine._hysteresis_learner, HysteresisLearner)
        assert hasattr(engine, '_last_power_state')
        assert engine._last_power_state is None

    def test_initialization_power_sensor_empty_string(self):
        """Test OffsetEngine initialization when power sensor is empty string."""
        config = {
            "max_offset": 5.0,
            "power_sensor": "",  # Empty string (no power sensor)
            "enable_learning": True
        }
        
        engine = OffsetEngine(config)
        
        # Hysteresis should be disabled with empty string
        assert engine._hysteresis_enabled is False

    def test_power_transition_detection_idle_to_high(self):
        """Test power transition detection from idle to high power."""
        config = {
            "max_offset": 5.0,
            "power_sensor": "sensor.ac_power",
            "enable_learning": True,
            "power_idle_threshold": 50.0,
            "power_max_threshold": 250.0
        }
        
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=25.0,
            time_of_day=time(15, 30),
            day_of_week=2,
            mode="cool",
            outdoor_temp=30.0,
            power_consumption=300.0  # High power
        )
        
        # Mock the hysteresis learner to verify record_transition is called
        engine._hysteresis_learner.record_transition = Mock()
        
        # First call - no previous state, should set last_power_state but not record transition
        result = engine.calculate_offset(input_data)
        assert engine._last_power_state == "high"
        engine._hysteresis_learner.record_transition.assert_not_called()
        
        # Second call with low power - should detect transition and record 'stop'
        input_data.power_consumption = 20.0  # Idle power
        result = engine.calculate_offset(input_data)
        assert engine._last_power_state == "idle"
        engine._hysteresis_learner.record_transition.assert_called_once_with('stop', 25.0)

    def test_power_transition_detection_idle_to_moderate(self):
        """Test power transition detection from idle to moderate power."""
        config = {
            "max_offset": 5.0,
            "power_sensor": "sensor.ac_power",
            "enable_learning": True,
            "power_idle_threshold": 50.0,
            "power_min_threshold": 100.0,
            "power_max_threshold": 250.0
        }
        
        engine = OffsetEngine(config)
        
        # Set initial state to idle
        engine._last_power_state = "idle"
        engine._hysteresis_learner.record_transition = Mock()
        
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=25.0,
            time_of_day=time(15, 30),
            day_of_week=2,
            mode="cool",
            outdoor_temp=30.0,
            power_consumption=150.0  # Moderate power
        )
        
        result = engine.calculate_offset(input_data)
        
        # Should detect idle -> moderate transition and record 'start'
        assert engine._last_power_state == "moderate"
        engine._hysteresis_learner.record_transition.assert_called_once_with('start', 25.0)

    def test_no_power_transition_same_state(self):
        """Test that no transition is recorded when power state doesn't change."""
        config = {
            "max_offset": 5.0,
            "power_sensor": "sensor.ac_power",
            "enable_learning": True,
            "power_idle_threshold": 50.0,
            "power_max_threshold": 250.0
        }
        
        engine = OffsetEngine(config)
        engine._last_power_state = "high"
        engine._hysteresis_learner.record_transition = Mock()
        
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=25.0,
            time_of_day=time(15, 30),
            day_of_week=2,
            mode="cool",
            outdoor_temp=30.0,
            power_consumption=300.0  # Still high power
        )
        
        result = engine.calculate_offset(input_data)
        
        # No transition should be recorded
        assert engine._last_power_state == "high"
        engine._hysteresis_learner.record_transition.assert_not_called()

    def test_hysteresis_disabled_no_power_sensor(self):
        """Test that hysteresis logic is skipped when no power sensor is configured."""
        config = {
            "max_offset": 5.0,
            "power_sensor": None,  # No power sensor
            "enable_learning": True
        }
        
        engine = OffsetEngine(config)
        engine._hysteresis_learner.record_transition = Mock()
        
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=25.0,
            time_of_day=time(15, 30),
            day_of_week=2,
            mode="cool",
            outdoor_temp=30.0,
            power_consumption=300.0  # Would be high power if hysteresis was enabled
        )
        
        result = engine.calculate_offset(input_data)
        
        # No hysteresis logic should run
        assert engine._last_power_state is None
        engine._hysteresis_learner.record_transition.assert_not_called()

    def test_hysteresis_state_calculation_works(self):
        """Test that hysteresis state calculation is available when hysteresis is enabled."""
        config = {
            "max_offset": 5.0,
            "power_sensor": "sensor.ac_power",
            "enable_learning": True,
            "power_idle_threshold": 50.0,
            "power_max_threshold": 250.0
        }
        
        engine = OffsetEngine(config)
        
        # Add some data to hysteresis learner so it has sufficient data
        engine._hysteresis_learner.record_transition('start', 24.5)
        engine._hysteresis_learner.record_transition('start', 24.3)
        engine._hysteresis_learner.record_transition('start', 24.4)
        engine._hysteresis_learner.record_transition('start', 24.2)
        engine._hysteresis_learner.record_transition('start', 24.6)
        
        engine._hysteresis_learner.record_transition('stop', 23.5)
        engine._hysteresis_learner.record_transition('stop', 23.7)
        engine._hysteresis_learner.record_transition('stop', 23.6)
        engine._hysteresis_learner.record_transition('stop', 23.4)
        engine._hysteresis_learner.record_transition('stop', 23.8)
        
        # Verify the learner has sufficient data
        assert engine._hysteresis_learner.has_sufficient_data
        
        # Test hysteresis state calculation for different power states
        assert engine._hysteresis_learner.get_hysteresis_state("high", 25.0) == "active_phase"
        assert engine._hysteresis_learner.get_hysteresis_state("idle", 25.0) == "idle_above_start_threshold"
        assert engine._hysteresis_learner.get_hysteresis_state("idle", 23.0) == "idle_below_stop_threshold"
        assert engine._hysteresis_learner.get_hysteresis_state("idle", 24.0) == "idle_stable_zone"

    def test_hysteresis_state_no_power_sensor_fallback(self):
        """Test that hysteresis_state defaults to 'no_power_sensor' when power sensor not configured."""
        config = {
            "max_offset": 5.0,
            "power_sensor": None,  # No power sensor
            "enable_learning": True
        }
        
        engine = OffsetEngine(config)
        
        # This test verifies the fallback behavior - when hysteresis is disabled,
        # the system should use default hysteresis_state = "no_power_sensor"
        # This will be verified through the integration behavior
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=25.0,
            time_of_day=time(15, 30),
            day_of_week=2,
            mode="cool",
            outdoor_temp=30.0,
            power_consumption=None  # No power data
        )
        
        result = engine.calculate_offset(input_data)
        
        # The calculation should succeed without errors
        assert result.offset is not None

    def test_persistence_serialization_with_hysteresis_data(self):
        """Test that persistence includes hysteresis data in v2 schema when enabled."""
        config = {
            "max_offset": 5.0,
            "power_sensor": "sensor.ac_power",
            "enable_learning": True
        }
        
        engine = OffsetEngine(config)
        engine.set_data_store(Mock())
        
        # Add some data to hysteresis learner
        engine._hysteresis_learner.record_transition('start', 24.5)
        engine._hysteresis_learner.record_transition('stop', 23.5)
        
        # Mock the data store save method to capture what's being saved
        with patch.object(engine._data_store, 'async_save_learning_data', new_callable=AsyncMock) as mock_save:
            import asyncio
            asyncio.run(engine.async_save_learning_data())
            
            # Verify the saved data includes v2 schema with hysteresis_data
            mock_save.assert_called_once()
            saved_data = mock_save.call_args[0][0]
            
            assert saved_data["version"] == "2.1"
            assert "learning_data" in saved_data
            assert "hysteresis_data" in saved_data["learning_data"]
            assert saved_data["learning_data"]["hysteresis_data"]["start_temps"] == [24.5]
            assert saved_data["learning_data"]["hysteresis_data"]["stop_temps"] == [23.5]

    @pytest.mark.asyncio
    async def test_persistence_serialization_without_hysteresis_when_disabled(self):
        """Test that persistence excludes hysteresis data when hysteresis is disabled."""
        config = {
            "max_offset": 5.0,
            "power_sensor": None,  # No power sensor - hysteresis disabled
            "enable_learning": True
        }
        
        engine = OffsetEngine(config)
        engine.set_data_store(Mock())
        
        # Mock the data store save method to capture what's being saved
        with patch.object(engine._data_store, 'async_save_learning_data', new_callable=AsyncMock) as mock_save:
            await engine.async_save_learning_data()
            
            # Verify the saved data doesn't include hysteresis_data when disabled
            mock_save.assert_called_once()
            saved_data = mock_save.call_args[0][0]
            
            # Should be v2.1 with null hysteresis_data when disabled
            assert saved_data["version"] == "2.1"
            assert "learning_data" in saved_data
            assert saved_data["learning_data"]["hysteresis_data"] is None

    @pytest.mark.asyncio
    async def test_persistence_backward_compatibility_v1_data(self):
        """Test that v1 data loading works without hysteresis_data key."""
        config = {
            "max_offset": 5.0,
            "power_sensor": "sensor.ac_power",
            "enable_learning": True
        }
        
        engine = OffsetEngine(config)
        
        # Mock data store to return v1 data without hysteresis_data
        mock_data_store = Mock()
        v1_data = {
            "version": 1,
            "engine_state": {"enable_learning": True},
            "learner_data": {"samples": [], "min_samples": 20, "max_samples": 1000, "has_sufficient_data": False}
            # No hysteresis_data key
        }
        mock_data_store.async_load_learning_data = AsyncMock(return_value=v1_data)
        engine.set_data_store(mock_data_store)
        
        # Should load successfully without errors
        result = await engine.async_load_learning_data()
        
        assert result is True
        # Hysteresis learner should still be available but with no data
        assert engine._hysteresis_learner is not None
        assert len(engine._hysteresis_learner._start_temps) == 0
        assert len(engine._hysteresis_learner._stop_temps) == 0

    @pytest.mark.asyncio
    async def test_persistence_v2_data_with_hysteresis_restoration(self):
        """Test that v2 data with hysteresis_data is properly restored."""
        config = {
            "max_offset": 5.0,
            "power_sensor": "sensor.ac_power",
            "enable_learning": True
        }
        
        engine = OffsetEngine(config)
        
        # Mock data store to return v2 data with hysteresis_data
        mock_data_store = Mock()
        v2_data = {
            "version": 2,
            "engine_state": {"enable_learning": True},
            "learner_data": {"samples": [], "min_samples": 20, "max_samples": 1000, "has_sufficient_data": False},
            "hysteresis_data": {
                "start_temps": [24.5, 24.3, 24.4],
                "stop_temps": [23.5, 23.7, 23.6]
            }
        }
        mock_data_store.async_load_learning_data = AsyncMock(return_value=v2_data)
        engine.set_data_store(mock_data_store)
        
        # Should load successfully and restore hysteresis data
        result = await engine.async_load_learning_data()
        
        assert result is True
        # Hysteresis learner should have restored data
        assert list(engine._hysteresis_learner._start_temps) == [24.5, 24.3, 24.4]
        assert list(engine._hysteresis_learner._stop_temps) == [23.5, 23.7, 23.6]

    def test_reset_learning_includes_hysteresis_learner(self):
        """Test that reset_learning() also resets the hysteresis learner."""
        config = {
            "max_offset": 5.0,
            "power_sensor": "sensor.ac_power",
            "enable_learning": True
        }
        
        engine = OffsetEngine(config)
        
        # Add some data to hysteresis learner
        engine._hysteresis_learner.record_transition('start', 24.5)
        engine._hysteresis_learner.record_transition('stop', 23.5)
        assert len(engine._hysteresis_learner._start_temps) == 1
        assert len(engine._hysteresis_learner._stop_temps) == 1
        
        # Reset learning
        engine.reset_learning()
        
        # Hysteresis learner should be reset
        assert len(engine._hysteresis_learner._start_temps) == 0
        assert len(engine._hysteresis_learner._stop_temps) == 0
        assert engine._hysteresis_learner.learned_start_threshold is None
        assert engine._hysteresis_learner.learned_stop_threshold is None

    def test_error_handling_hysteresis_operations_fail(self):
        """Test graceful degradation when hysteresis operations fail."""
        config = {
            "max_offset": 5.0,
            "power_sensor": "sensor.ac_power",
            "enable_learning": True
        }
        
        engine = OffsetEngine(config)
        
        # Mock hysteresis learner to raise exceptions
        engine._hysteresis_learner.record_transition = Mock(side_effect=Exception("Test error"))
        engine._hysteresis_learner.get_hysteresis_state = Mock(side_effect=Exception("Test error"))
        
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=25.0,
            time_of_day=time(15, 30),
            day_of_week=2,
            mode="cool",
            outdoor_temp=30.0,
            power_consumption=300.0
        )
        
        # Should not raise exception - system should continue working
        result = engine.calculate_offset(input_data)
        
        # Basic offset calculation should still work
        assert result.offset is not None
        assert result.reason is not None

    def test_power_consumption_none_handling(self):
        """Test handling when power_consumption is None."""
        config = {
            "max_offset": 5.0,
            "power_sensor": "sensor.ac_power",
            "enable_learning": True
        }
        
        engine = OffsetEngine(config)
        engine._hysteresis_learner.record_transition = Mock()
        
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=25.0,
            time_of_day=time(15, 30),
            day_of_week=2,
            mode="cool",
            outdoor_temp=30.0,
            power_consumption=None  # No power data
        )
        
        result = engine.calculate_offset(input_data)
        
        # Should not attempt power state transitions
        assert engine._last_power_state is None
        engine._hysteresis_learner.record_transition.assert_not_called()

    def test_all_power_transition_combinations(self):
        """Test all power state transition combinations."""
        config = {
            "max_offset": 5.0,
            "power_sensor": "sensor.ac_power",
            "enable_learning": True,
            "power_idle_threshold": 50.0,
            "power_min_threshold": 100.0,
            "power_max_threshold": 250.0
        }
        
        engine = OffsetEngine(config)
        engine._hysteresis_learner.record_transition = Mock()
        
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=25.0,
            time_of_day=time(15, 30),
            day_of_week=2,
            mode="cool",
            outdoor_temp=30.0,
            power_consumption=300.0  # High
        )
        
        # Test various transitions that should trigger record_transition
        test_cases = [
            # (from_power, to_power, expected_transition)
            ("idle", "moderate", "start"),
            ("idle", "high", "start"),
            ("low", "moderate", "start"),
            ("low", "high", "start"),
            ("moderate", "idle", "stop"),
            ("moderate", "low", "stop"),
            ("high", "idle", "stop"),
            ("high", "low", "stop"),
        ]
        
        power_values = {
            "idle": 30.0,
            "low": 75.0,
            "moderate": 150.0,
            "high": 300.0
        }
        
        for from_state, to_state, expected_transition in test_cases:
            engine._hysteresis_learner.record_transition.reset_mock()
            engine._last_power_state = from_state
            
            input_data.power_consumption = power_values[to_state]
            result = engine.calculate_offset(input_data)
            
            engine._hysteresis_learner.record_transition.assert_called_once_with(expected_transition, 25.0)
            assert engine._last_power_state == to_state

        # Test transitions that should NOT trigger record_transition
        no_transition_cases = [
            ("idle", "low"),
            ("low", "idle"),
            ("moderate", "high"),
            ("high", "moderate"),
        ]
        
        for from_state, to_state in no_transition_cases:
            engine._hysteresis_learner.record_transition.reset_mock()
            engine._last_power_state = from_state
            
            input_data.power_consumption = power_values[to_state]
            result = engine.calculate_offset(input_data)
            
            engine._hysteresis_learner.record_transition.assert_not_called()
            assert engine._last_power_state == to_state