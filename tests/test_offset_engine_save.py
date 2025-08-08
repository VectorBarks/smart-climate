"""Tests for OffsetEngine save functionality."""

import pytest
from datetime import timedelta
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.const import (
    CONF_SAVE_INTERVAL,
    DEFAULT_SAVE_INTERVAL,
)


class TestOffsetEngineSave:
    """Test suite for OffsetEngine save functionality."""

    def test_save_interval_from_config(self):
        """Test that save interval is read from config."""
        config = {
            CONF_SAVE_INTERVAL: 1800,  # 30 minutes
            "enable_learning": True
        }
        engine = OffsetEngine(config)
        
        # The save interval should be accessible for testing
        assert hasattr(engine, '_save_interval')
        assert engine._save_interval == 1800

    def test_save_interval_default(self):
        """Test that default save interval is used when not in config."""
        config = {"enable_learning": True}
        engine = OffsetEngine(config)
        
        # Should use default value
        assert engine._save_interval == DEFAULT_SAVE_INTERVAL

    @pytest.mark.asyncio
    async def test_periodic_save_uses_config_interval(self):
        """Test that periodic save uses the configured interval."""
        config = {
            CONF_SAVE_INTERVAL: 300,  # 5 minutes
            "enable_learning": True
        }
        engine = OffsetEngine(config)
        
        # Mock the data store
        mock_data_store = AsyncMock()
        engine.set_data_store(mock_data_store)
        
        # Mock Home Assistant instance
        mock_hass = Mock()
        
        # Mock the time tracking function
        with patch('homeassistant.helpers.event.async_track_time_interval') as mock_track:
            mock_track.return_value = Mock()
            
            # Call setup_periodic_save with save_interval parameter
            cancel_func = await engine.async_setup_periodic_save(mock_hass, save_interval=300)
            
            # Verify the tracking was set up with correct interval
            mock_track.assert_called_once()
            args, kwargs = mock_track.call_args
            assert args[0] == mock_hass
            assert args[2] == timedelta(seconds=300)  # 5 minutes

    @pytest.mark.asyncio
    async def test_periodic_save_backward_compatibility(self):
        """Test that periodic save works without save_interval parameter."""
        config = {
            CONF_SAVE_INTERVAL: 1200,  # 20 minutes
            "enable_learning": True
        }
        engine = OffsetEngine(config)
        
        # Mock the data store
        mock_data_store = AsyncMock()
        engine.set_data_store(mock_data_store)
        
        # Mock Home Assistant instance
        mock_hass = Mock()
        
        # Mock the time tracking function
        with patch('homeassistant.helpers.event.async_track_time_interval') as mock_track:
            mock_track.return_value = Mock()
            
            # Call setup_periodic_save without save_interval parameter (backward compatibility)
            cancel_func = await engine.async_setup_periodic_save(mock_hass)
            
            # Verify the tracking was set up with config interval
            mock_track.assert_called_once()
            args, kwargs = mock_track.call_args
            assert args[0] == mock_hass
            assert args[2] == timedelta(seconds=1200)  # 20 minutes from config

    @pytest.mark.asyncio
    async def test_save_logging_success(self):
        """Test that successful saves are logged at INFO level."""
        config = {"enable_learning": True}
        engine = OffsetEngine(config)
        
        # Mock the data store
        mock_data_store = AsyncMock()
        engine.set_data_store(mock_data_store)
        
        # Mock learner with sample data
        mock_learner = Mock()
        mock_learner.serialize_for_persistence.return_value = {
            "statistics": {"samples": 25}
        }
        engine._learner = mock_learner
        
        # Mock logger
        with patch('custom_components.smart_climate.offset_engine._LOGGER') as mock_logger:
            await engine.async_save_learning_data()
            
            # Verify INFO log was called with sample count
            mock_logger.info.assert_called()
            info_calls = [call for call in mock_logger.info.call_args_list if "save successful" in str(call).lower()]
            assert len(info_calls) > 0

    @pytest.mark.asyncio
    async def test_save_logging_error(self):
        """Test that save errors are logged at WARNING level."""
        config = {"enable_learning": True}
        engine = OffsetEngine(config)
        
        # Mock the data store to raise an exception
        mock_data_store = AsyncMock()
        mock_data_store.async_save_learning_data.side_effect = Exception("Save failed")
        engine.set_data_store(mock_data_store)
        
        # Mock logger
        with patch('custom_components.smart_climate.offset_engine._LOGGER') as mock_logger:
            await engine.async_save_learning_data()
            
            # Verify WARNING log was called
            mock_logger.warning.assert_called()
            warning_calls = [call for call in mock_logger.warning.call_args_list if "save failed" in str(call).lower()]
            assert len(warning_calls) > 0

    @pytest.mark.asyncio
    async def test_save_statistics_tracking(self):
        """Test that save statistics are tracked correctly."""
        config = {"enable_learning": True}
        engine = OffsetEngine(config)
        
        # Mock the data store
        mock_data_store = AsyncMock()
        engine.set_data_store(mock_data_store)
        
        # Initial state
        assert engine._save_count == 0
        assert engine._failed_save_count == 0
        assert engine._last_save_time is None
        
        # Successful save
        await engine.async_save_learning_data()
        
        assert engine._save_count == 1
        assert engine._failed_save_count == 0
        assert engine._last_save_time is not None
        
        # Failed save
        mock_data_store.async_save_learning_data.side_effect = Exception("Save failed")
        await engine.async_save_learning_data()
        
        assert engine._save_count == 1  # Unchanged
        assert engine._failed_save_count == 1
        # last_save_time should not be updated on failure

    def test_save_statistics_properties(self):
        """Test that save statistics are accessible via properties."""
        config = {"enable_learning": True}
        engine = OffsetEngine(config)
        
        # Properties should exist and be accessible
        assert hasattr(engine, 'save_count')
        assert hasattr(engine, 'failed_save_count')
        assert hasattr(engine, 'last_save_time')
        
        # Initial values
        assert engine.save_count == 0
        assert engine.failed_save_count == 0
        assert engine.last_save_time is None

    @pytest.mark.asyncio
    async def test_save_with_no_data_store(self):
        """Test that save handles missing data store gracefully."""
        config = {"enable_learning": True}
        engine = OffsetEngine(config)
        
        # No data store set
        with patch('custom_components.smart_climate.offset_engine._LOGGER') as mock_logger:
            await engine.async_save_learning_data()
            
            # Should log warning about missing data store
            mock_logger.warning.assert_called()
            warning_calls = [call for call in mock_logger.warning.call_args_list if "no data store" in str(call).lower()]
            assert len(warning_calls) > 0

    @pytest.mark.asyncio
    async def test_save_data_integrity(self):
        """Test that save operation maintains data integrity."""
        config = {"enable_learning": True}
        engine = OffsetEngine(config)
        
        # Mock the data store
        mock_data_store = AsyncMock()
        engine.set_data_store(mock_data_store)
        
        # Mock learner with sample data
        mock_learner = Mock()
        mock_learner.serialize_for_persistence.return_value = {
            "statistics": {"samples": 42}
        }
        engine._learner = mock_learner
        
        await engine.async_save_learning_data()
        
        # Verify data store was called with correct data
        mock_data_store.async_save_learning_data.assert_called_once()
        saved_data = mock_data_store.async_save_learning_data.call_args[0][0]
        
        # Verify data integrity with v2.1 schema
        assert saved_data["version"] == "2.1"
        assert saved_data["learning_data"]["engine_state"]["enable_learning"] is True
        assert saved_data["learning_data"]["learner_data"]["statistics"]["samples"] == 42
        assert "thermal_data" in saved_data

    @pytest.mark.asyncio
    async def test_periodic_save_disabled_when_learning_disabled(self):
        """Test that periodic save is disabled when learning is disabled."""
        config = {"enable_learning": False}
        engine = OffsetEngine(config)
        
        # Mock Home Assistant instance
        mock_hass = Mock()
        
        # Mock the time tracking function
        with patch('homeassistant.helpers.event.async_track_time_interval') as mock_track:
            # Call setup_periodic_save
            cancel_func = await engine.async_setup_periodic_save(mock_hass)
            
            # Verify tracking was NOT set up
            mock_track.assert_not_called()
            
            # Cancel function should do nothing
            assert cancel_func() is None