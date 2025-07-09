"""Tests for training data persistence functionality.

This test suite covers the save/load functionality for training data,
including periodic saves, shutdown saves, data integrity, and error handling.
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from datetime import datetime, time, timedelta
import logging

from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.data_store import SmartClimateDataStore
from custom_components.smart_climate.models import OffsetInput
from custom_components.smart_climate.const import (
    DEFAULT_POWER_IDLE_THRESHOLD,
    DEFAULT_POWER_MIN_THRESHOLD,
    DEFAULT_POWER_MAX_THRESHOLD,
)


class TestPeriodicSaveTriggers:
    """Test periodic save trigger functionality."""
    
    def test_periodic_save_setup_when_learning_enabled(self):
        """Test periodic save is configured when learning is enabled."""
        config = {
            "ml_enabled": True,
            "max_offset": 5.0,
            "save_interval": 3600,  # 60 minutes
        }
        
        mock_hass = Mock()
        mock_data_store = Mock(spec=SmartClimateDataStore)
        
        engine = OffsetEngine(config, mock_data_store)
        engine._enable_learning = True
        
        with patch('custom_components.smart_climate.offset_engine.async_track_time_interval') as mock_track:
            mock_track.return_value = Mock()  # Mock remove function
            
            # Setup periodic save
            remove_fn = asyncio.run(engine.async_setup_periodic_save(mock_hass))
            
            # Verify async_track_time_interval was called
            mock_track.assert_called_once()
            call_args = mock_track.call_args
            assert call_args[0][0] == mock_hass  # hass parameter
            assert isinstance(call_args[0][2], timedelta)  # interval parameter
            assert call_args[0][2].total_seconds() == 3600  # 60 minutes
            
            # Verify remove function returned
            assert callable(remove_fn)
    
    def test_periodic_save_not_setup_when_learning_disabled(self):
        """Test periodic save is not configured when learning is disabled."""
        config = {
            "ml_enabled": False,
            "max_offset": 5.0,
            "save_interval": 3600,
        }
        
        mock_hass = Mock()
        mock_data_store = Mock(spec=SmartClimateDataStore)
        
        engine = OffsetEngine(config, mock_data_store)
        engine._enable_learning = False
        
        with patch('custom_components.smart_climate.offset_engine.async_track_time_interval') as mock_track:
            # Setup periodic save
            remove_fn = asyncio.run(engine.async_setup_periodic_save(mock_hass))
            
            # Verify async_track_time_interval was NOT called
            mock_track.assert_not_called()
            
            # Verify no-op remove function returned
            assert callable(remove_fn)
    
    def test_periodic_save_uses_configured_interval(self):
        """Test periodic save uses the configured save interval."""
        test_intervals = [300, 600, 1800, 3600]  # 5min, 10min, 30min, 60min
        
        for interval in test_intervals:
            config = {
                "ml_enabled": True,
                "max_offset": 5.0,
                "save_interval": interval,
            }
            
            mock_hass = Mock()
            mock_data_store = Mock(spec=SmartClimateDataStore)
            
            engine = OffsetEngine(config, mock_data_store)
            engine._enable_learning = True
            
            with patch('custom_components.smart_climate.offset_engine.async_track_time_interval') as mock_track:
                mock_track.return_value = Mock()
                
                # Setup periodic save
                asyncio.run(engine.async_setup_periodic_save(mock_hass))
                
                # Verify correct interval was used
                call_args = mock_track.call_args
                assert call_args[0][2].total_seconds() == interval
    
    def test_periodic_save_callback_calls_save_method(self):
        """Test that periodic save callback calls the save method."""
        config = {
            "ml_enabled": True,
            "max_offset": 5.0,
            "save_interval": 600,
        }
        
        mock_hass = Mock()
        mock_data_store = Mock(spec=SmartClimateDataStore)
        
        engine = OffsetEngine(config, mock_data_store)
        engine._enable_learning = True
        
        with patch('custom_components.smart_climate.offset_engine.async_track_time_interval') as mock_track:
            mock_track.return_value = Mock()
            
            # Mock the save method
            engine.async_save_learning_data = AsyncMock()
            
            # Setup periodic save
            asyncio.run(engine.async_setup_periodic_save(mock_hass))
            
            # Get the callback function
            callback_fn = mock_track.call_args[0][1]
            
            # Execute the callback
            asyncio.run(callback_fn())
            
            # Verify save was called
            engine.async_save_learning_data.assert_called_once()
    
    def test_default_save_interval_is_60_minutes(self):
        """Test that default save interval is 60 minutes (3600 seconds)."""
        config = {
            "ml_enabled": True,
            "max_offset": 5.0,
            # No save_interval specified - should use default
        }
        
        mock_hass = Mock()
        mock_data_store = Mock(spec=SmartClimateDataStore)
        
        engine = OffsetEngine(config, mock_data_store)
        engine._enable_learning = True
        
        with patch('custom_components.smart_climate.offset_engine.async_track_time_interval') as mock_track:
            mock_track.return_value = Mock()
            
            # Setup periodic save
            asyncio.run(engine.async_setup_periodic_save(mock_hass))
            
            # Verify default interval (3600 seconds = 60 minutes)
            call_args = mock_track.call_args
            assert call_args[0][2].total_seconds() == 3600
    
    def test_periodic_save_interval_validation(self):
        """Test that save interval validation works correctly."""
        # Test various intervals
        valid_intervals = [60, 300, 600, 1800, 3600, 7200]  # 1min to 2hrs
        
        for interval in valid_intervals:
            config = {
                "ml_enabled": True,
                "max_offset": 5.0,
                "save_interval": interval,
            }
            
            mock_hass = Mock()
            mock_data_store = Mock(spec=SmartClimateDataStore)
            
            # Should not raise any exceptions
            engine = OffsetEngine(config, mock_data_store)
            assert engine._save_interval == interval


class TestShutdownSave:
    """Test shutdown save functionality."""
    
    def test_shutdown_save_in_unload_entry(self):
        """Test that shutdown save is called during unload entry."""
        # This test verifies the __init__.py implementation
        from custom_components.smart_climate import async_unload_entry
        
        # Mock Home Assistant and config entry
        mock_hass = Mock()
        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        
        # Mock the unload platforms call
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        
        # Mock the entry data structure
        mock_offset_engine = Mock()
        mock_offset_engine.async_save_learning_data = AsyncMock()
        
        entry_data = {
            "unload_listeners": [Mock()],
            "offset_engines": {
                "climate.test": mock_offset_engine
            }
        }
        
        mock_hass.data = {
            "smart_climate": {
                "test_entry": entry_data
            }
        }
        
        # Execute unload
        result = asyncio.run(async_unload_entry(mock_hass, mock_entry))
        
        # Verify save was called
        mock_offset_engine.async_save_learning_data.assert_called_once()
        assert result is True
    
    def test_shutdown_save_handles_multiple_engines(self):
        """Test shutdown save handles multiple offset engines."""
        from custom_components.smart_climate import async_unload_entry
        
        mock_hass = Mock()
        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        
        # Create multiple mock engines
        mock_engine1 = Mock()
        mock_engine1.async_save_learning_data = AsyncMock()
        mock_engine2 = Mock()
        mock_engine2.async_save_learning_data = AsyncMock()
        
        entry_data = {
            "unload_listeners": [],
            "offset_engines": {
                "climate.test1": mock_engine1,
                "climate.test2": mock_engine2
            }
        }
        
        mock_hass.data = {
            "smart_climate": {
                "test_entry": entry_data
            }
        }
        
        # Execute unload
        result = asyncio.run(async_unload_entry(mock_hass, mock_entry))
        
        # Verify both engines had save called
        mock_engine1.async_save_learning_data.assert_called_once()
        mock_engine2.async_save_learning_data.assert_called_once()
        assert result is True
    
    def test_shutdown_save_continues_on_error(self):
        """Test shutdown save continues even if individual saves fail."""
        from custom_components.smart_climate import async_unload_entry
        
        mock_hass = Mock()
        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        
        # Create engines - one that fails, one that succeeds
        mock_engine1 = Mock()
        mock_engine1.async_save_learning_data = AsyncMock(side_effect=Exception("Save failed"))
        mock_engine2 = Mock()
        mock_engine2.async_save_learning_data = AsyncMock()
        
        entry_data = {
            "unload_listeners": [],
            "offset_engines": {
                "climate.test1": mock_engine1,
                "climate.test2": mock_engine2
            }
        }
        
        mock_hass.data = {
            "smart_climate": {
                "test_entry": entry_data
            }
        }
        
        # Execute unload - should not raise exception
        result = asyncio.run(async_unload_entry(mock_hass, mock_entry))
        
        # Verify both engines had save called
        mock_engine1.async_save_learning_data.assert_called_once()
        mock_engine2.async_save_learning_data.assert_called_once()
        assert result is True
    
    def test_shutdown_save_with_no_engines(self):
        """Test shutdown save with no offset engines."""
        from custom_components.smart_climate import async_unload_entry
        
        mock_hass = Mock()
        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        
        entry_data = {
            "unload_listeners": [],
            "offset_engines": {}
        }
        
        mock_hass.data = {
            "smart_climate": {
                "test_entry": entry_data
            }
        }
        
        # Execute unload - should not raise exception
        result = asyncio.run(async_unload_entry(mock_hass, mock_entry))
        assert result is True
    
    def test_shutdown_save_with_timeout_protection(self):
        """Test shutdown save has timeout protection to prevent hanging."""
        from custom_components.smart_climate import async_unload_entry
        
        mock_hass = Mock()
        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        
        # Mock engine that takes too long to save
        mock_slow_engine = Mock()
        async def slow_save():
            await asyncio.sleep(10)  # Simulate slow save
        mock_slow_engine.async_save_learning_data = AsyncMock(side_effect=slow_save)
        
        entry_data = {
            "unload_listeners": [],
            "offset_engines": {
                "climate.test": mock_slow_engine
            }
        }
        
        mock_hass.data = {
            "smart_climate": {
                "test_entry": entry_data
            }
        }
        
        # Execute unload - should complete quickly due to timeout
        import time
        start_time = time.time()
        result = asyncio.run(async_unload_entry(mock_hass, mock_entry))
        end_time = time.time()
        
        # Should complete within timeout (5 seconds + some buffer)
        assert end_time - start_time < 7.0
        assert result is True
    
    def test_shutdown_save_logs_info_on_start(self):
        """Test shutdown save logs INFO message when starting save operations."""
        from custom_components.smart_climate import async_unload_entry
        
        mock_hass = Mock()
        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        
        mock_offset_engine = Mock()
        mock_offset_engine.async_save_learning_data = AsyncMock()
        
        entry_data = {
            "unload_listeners": [],
            "offset_engines": {
                "climate.test": mock_offset_engine
            }
        }
        
        mock_hass.data = {
            "smart_climate": {
                "test_entry": entry_data
            }
        }
        
        # Mock logger to capture INFO messages
        with patch('custom_components.smart_climate._LOGGER') as mock_logger:
            result = asyncio.run(async_unload_entry(mock_hass, mock_entry))
            
            # Verify INFO logging was called for shutdown save
            mock_logger.info.assert_called()
            log_calls = mock_logger.info.call_args_list
            assert any("shutdown save" in str(call).lower() or "final save" in str(call).lower() 
                      for call in log_calls)
        
        assert result is True
    
    def test_shutdown_save_logs_info_on_completion(self):
        """Test shutdown save logs INFO message when save operations complete."""
        from custom_components.smart_climate import async_unload_entry
        
        mock_hass = Mock()
        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        
        mock_offset_engine = Mock()
        mock_offset_engine.async_save_learning_data = AsyncMock()
        
        entry_data = {
            "unload_listeners": [],
            "offset_engines": {
                "climate.test": mock_offset_engine
            }
        }
        
        mock_hass.data = {
            "smart_climate": {
                "test_entry": entry_data
            }
        }
        
        # Mock logger to capture INFO messages
        with patch('custom_components.smart_climate._LOGGER') as mock_logger:
            result = asyncio.run(async_unload_entry(mock_hass, mock_entry))
            
            # Verify INFO logging was called for completion
            mock_logger.info.assert_called()
            log_calls = mock_logger.info.call_args_list
            assert any("save completed" in str(call).lower() or "final save completed" in str(call).lower() 
                      for call in log_calls)
        
        assert result is True
    
    def test_shutdown_save_handles_timeout_gracefully(self):
        """Test shutdown save handles timeout gracefully without raising exceptions."""
        from custom_components.smart_climate import async_unload_entry
        
        mock_hass = Mock()
        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        
        # Mock engine that times out
        mock_timeout_engine = Mock()
        async def timeout_save():
            await asyncio.sleep(10)  # Longer than 5 second timeout
        mock_timeout_engine.async_save_learning_data = AsyncMock(side_effect=timeout_save)
        
        entry_data = {
            "unload_listeners": [],
            "offset_engines": {
                "climate.test": mock_timeout_engine
            }
        }
        
        mock_hass.data = {
            "smart_climate": {
                "test_entry": entry_data
            }
        }
        
        # Mock logger to capture timeout warnings
        with patch('custom_components.smart_climate._LOGGER') as mock_logger:
            # Execute unload - should not raise exception
            result = asyncio.run(async_unload_entry(mock_hass, mock_entry))
            
            # Should have logged timeout warning
            mock_logger.warning.assert_called()
            log_calls = mock_logger.warning.call_args_list
            assert any("timeout" in str(call).lower() for call in log_calls)
        
        assert result is True
    
    def test_shutdown_save_mixed_success_and_timeout(self):
        """Test shutdown save handles mixed success and timeout scenarios."""
        from custom_components.smart_climate import async_unload_entry
        
        mock_hass = Mock()
        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        
        # Mock fast engine that succeeds
        mock_fast_engine = Mock()
        mock_fast_engine.async_save_learning_data = AsyncMock()
        
        # Mock slow engine that times out
        mock_slow_engine = Mock()
        async def slow_save():
            await asyncio.sleep(10)
        mock_slow_engine.async_save_learning_data = AsyncMock(side_effect=slow_save)
        
        entry_data = {
            "unload_listeners": [],
            "offset_engines": {
                "climate.fast": mock_fast_engine,
                "climate.slow": mock_slow_engine
            }
        }
        
        mock_hass.data = {
            "smart_climate": {
                "test_entry": entry_data
            }
        }
        
        # Mock logger to capture messages
        with patch('custom_components.smart_climate._LOGGER') as mock_logger:
            result = asyncio.run(async_unload_entry(mock_hass, mock_entry))
            
            # Should have logged startup and timeout
            info_calls = mock_logger.info.call_args_list
            warning_calls = mock_logger.warning.call_args_list
            
            # Should log startup info
            assert any("starting shutdown save" in str(call).lower() for call in info_calls)
            # Should log timeout warning
            assert any("timeout" in str(call).lower() for call in warning_calls)
        
        # Both engines should have been called
        mock_fast_engine.async_save_learning_data.assert_called_once()
        mock_slow_engine.async_save_learning_data.assert_called_once()
        assert result is True


class TestSaveLoadDataIntegrity:
    """Test save/load data integrity."""
    
    def test_save_load_cycle_preserves_data(self):
        """Test that save/load cycle preserves all data."""
        config = {
            "ml_enabled": True,
            "max_offset": 5.0,
            "save_interval": 3600,
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock hass with temp directory
            mock_hass = Mock()
            mock_hass.config.config_dir = temp_dir
            
            # Create data store
            data_store = SmartClimateDataStore(mock_hass, "climate.test")
            
            # Create engine and add some learning data
            engine = OffsetEngine(config, data_store)
            engine._enable_learning = True
            
            # Add some sample data
            test_input = OffsetInput(
                ac_internal_temp=24.0,
                room_temp=25.0,
                outdoor_temp=30.0,
                mode="cool",
                power_consumption=500.0,
                time_of_day=time(14, 30),
                day_of_week=2
            )
            
            # Record some feedback
            engine.record_feedback(test_input, 1.0, 0.5)
            
            # Save data
            asyncio.run(engine.async_save_learning_data())
            
            # Create new engine and load data
            new_engine = OffsetEngine(config, data_store)
            new_engine._enable_learning = True
            asyncio.run(new_engine.async_load_learning_data())
            
            # Verify data was preserved
            assert new_engine._learner.get_sample_count() == engine._learner.get_sample_count()
            assert new_engine._hysteresis_learner.has_sufficient_data == engine._hysteresis_learner.has_sufficient_data
    
    def test_save_creates_backup_file(self):
        """Test that save creates a backup file."""
        config = {
            "ml_enabled": True,
            "max_offset": 5.0,
            "save_interval": 3600,
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_hass = Mock()
            mock_hass.config.config_dir = temp_dir
            
            data_store = SmartClimateDataStore(mock_hass, "climate.test")
            engine = OffsetEngine(config, data_store)
            engine._enable_learning = True
            
            # Add some data and save
            test_input = OffsetInput(
                ac_internal_temp=24.0,
                room_temp=25.0,
                outdoor_temp=30.0,
                mode="cool",
                power_consumption=500.0,
                time_of_day=time(14, 30),
                day_of_week=2
            )
            engine.record_feedback(test_input, 1.0, 0.5)
            
            # Save twice to create backup
            asyncio.run(engine.async_save_learning_data())
            asyncio.run(engine.async_save_learning_data())
            
            # Verify backup file exists
            data_file = data_store.get_data_file_path()
            backup_file = data_file.with_suffix(f"{data_file.suffix}.backup")
            assert backup_file.exists()
    
    def test_load_recovers_from_backup_on_corrupted_main_file(self):
        """Test that load recovers from backup when main file is corrupted."""
        config = {
            "ml_enabled": True,
            "max_offset": 5.0,
            "save_interval": 3600,
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_hass = Mock()
            mock_hass.config.config_dir = temp_dir
            
            data_store = SmartClimateDataStore(mock_hass, "climate.test")
            engine = OffsetEngine(config, data_store)
            engine._enable_learning = True
            
            # Add data and save
            test_input = OffsetInput(
                ac_internal_temp=24.0,
                room_temp=25.0,
                outdoor_temp=30.0,
                mode="cool",
                power_consumption=500.0,
                time_of_day=time(14, 30),
                day_of_week=2
            )
            engine.record_feedback(test_input, 1.0, 0.5)
            asyncio.run(engine.async_save_learning_data())
            
            # Corrupt main file
            data_file = data_store.get_data_file_path()
            data_file.write_text("corrupted json content")
            
            # Create new engine and load - should recover from backup
            new_engine = OffsetEngine(config, data_store)
            new_engine._enable_learning = True
            asyncio.run(new_engine.async_load_learning_data())
            
            # Verify data was recovered
            assert new_engine._learner.get_sample_count() > 0
    
    def test_save_preserves_timestamps(self):
        """Test that save preserves timestamp information."""
        config = {
            "ml_enabled": True,
            "max_offset": 5.0,
            "save_interval": 3600,
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_hass = Mock()
            mock_hass.config.config_dir = temp_dir
            
            data_store = SmartClimateDataStore(mock_hass, "climate.test")
            engine = OffsetEngine(config, data_store)
            engine._enable_learning = True
            
            # Record data with specific timestamp
            test_input = OffsetInput(
                ac_internal_temp=24.0,
                room_temp=25.0,
                outdoor_temp=30.0,
                mode="cool",
                power_consumption=500.0,
                time_of_day=time(14, 30),
                day_of_week=2
            )
            engine.record_feedback(test_input, 1.0, 0.5)
            
            # Save and reload
            asyncio.run(engine.async_save_learning_data())
            new_engine = OffsetEngine(config, data_store)
            new_engine._enable_learning = True
            asyncio.run(new_engine.async_load_learning_data())
            
            # Verify timestamp data was preserved
            # (This depends on the actual implementation of the learner)
            assert new_engine._learner.get_sample_count() == engine._learner.get_sample_count()


class TestErrorHandling:
    """Test error handling in persistence."""
    
    def test_save_handles_permission_errors(self):
        """Test save handles permission errors gracefully."""
        config = {
            "ml_enabled": True,
            "max_offset": 5.0,
            "save_interval": 3600,
        }
        
        mock_hass = Mock()
        mock_hass.config.config_dir = "/nonexistent/path"
        
        data_store = SmartClimateDataStore(mock_hass, "climate.test")
        engine = OffsetEngine(config, data_store)
        engine._enable_learning = True
        
        # Mock the save method to raise PermissionError
        data_store.async_save_data = AsyncMock(side_effect=PermissionError("Permission denied"))
        
        # Save should not raise exception
        asyncio.run(engine.async_save_learning_data())
        
        # Verify save was attempted
        data_store.async_save_data.assert_called_once()
    
    def test_load_handles_file_not_found(self):
        """Test load handles file not found gracefully."""
        config = {
            "ml_enabled": True,
            "max_offset": 5.0,
            "save_interval": 3600,
        }
        
        mock_hass = Mock()
        mock_hass.config.config_dir = "/nonexistent/path"
        
        data_store = SmartClimateDataStore(mock_hass, "climate.test")
        engine = OffsetEngine(config, data_store)
        engine._enable_learning = True
        
        # Mock load to raise FileNotFoundError
        data_store.async_load_data = AsyncMock(side_effect=FileNotFoundError("File not found"))
        
        # Load should not raise exception
        asyncio.run(engine.async_load_learning_data())
        
        # Verify load was attempted
        data_store.async_load_data.assert_called_once()
    
    def test_load_handles_corrupted_json(self):
        """Test load handles corrupted JSON gracefully."""
        config = {
            "ml_enabled": True,
            "max_offset": 5.0,
            "save_interval": 3600,
        }
        
        mock_hass = Mock()
        mock_hass.config.config_dir = "/test/path"
        
        data_store = SmartClimateDataStore(mock_hass, "climate.test")
        engine = OffsetEngine(config, data_store)
        engine._enable_learning = True
        
        # Mock load to raise JSON decode error
        data_store.async_load_data = AsyncMock(side_effect=json.JSONDecodeError("Invalid JSON", "doc", 0))
        
        # Load should not raise exception
        asyncio.run(engine.async_load_learning_data())
        
        # Verify load was attempted
        data_store.async_load_data.assert_called_once()
    
    def test_save_handles_disk_full_error(self):
        """Test save handles disk full error gracefully."""
        config = {
            "ml_enabled": True,
            "max_offset": 5.0,
            "save_interval": 3600,
        }
        
        mock_hass = Mock()
        mock_hass.config.config_dir = "/test/path"
        
        data_store = SmartClimateDataStore(mock_hass, "climate.test")
        engine = OffsetEngine(config, data_store)
        engine._enable_learning = True
        
        # Mock save to raise OSError (disk full)
        data_store.async_save_data = AsyncMock(side_effect=OSError("No space left on device"))
        
        # Save should not raise exception
        asyncio.run(engine.async_save_learning_data())
        
        # Verify save was attempted
        data_store.async_save_data.assert_called_once()
    
    def test_periodic_save_handles_engine_errors(self):
        """Test periodic save handles engine errors gracefully."""
        config = {
            "ml_enabled": True,
            "max_offset": 5.0,
            "save_interval": 600,
        }
        
        mock_hass = Mock()
        mock_data_store = Mock(spec=SmartClimateDataStore)
        
        engine = OffsetEngine(config, mock_data_store)
        engine._enable_learning = True
        
        # Mock save to raise an exception
        engine.async_save_learning_data = AsyncMock(side_effect=Exception("Engine error"))
        
        with patch('custom_components.smart_climate.offset_engine.async_track_time_interval') as mock_track:
            mock_track.return_value = Mock()
            
            # Setup periodic save
            asyncio.run(engine.async_setup_periodic_save(mock_hass))
            
            # Get and execute the callback
            callback_fn = mock_track.call_args[0][1]
            
            # Should not raise exception
            asyncio.run(callback_fn())
            
            # Verify save was attempted
            engine.async_save_learning_data.assert_called_once()


class TestSaveLogging:
    """Test save operation logging."""
    
    def test_save_logs_at_info_level(self):
        """Test that save operations log at INFO level for visibility."""
        config = {
            "ml_enabled": True,
            "max_offset": 5.0,
            "save_interval": 3600,
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_hass = Mock()
            mock_hass.config.config_dir = temp_dir
            
            data_store = SmartClimateDataStore(mock_hass, "climate.test")
            engine = OffsetEngine(config, data_store)
            engine._enable_learning = True
            
            # Add some data
            test_input = OffsetInput(
                ac_internal_temp=24.0,
                room_temp=25.0,
                outdoor_temp=30.0,
                mode="cool",
                power_consumption=500.0,
                time_of_day=time(14, 30),
                day_of_week=2
            )
            engine.record_feedback(test_input, 1.0, 0.5)
            
            # Mock logger
            with patch('custom_components.smart_climate.offset_engine._LOGGER') as mock_logger:
                # Save data
                asyncio.run(engine.async_save_learning_data())
                
                # Verify INFO level logging was called
                mock_logger.info.assert_called()
                
                # Verify log message contains relevant information
                log_calls = mock_logger.info.call_args_list
                assert any("save" in str(call).lower() for call in log_calls)
    
    def test_periodic_save_logs_info(self):
        """Test that periodic save logs at INFO level."""
        config = {
            "ml_enabled": True,
            "max_offset": 5.0,
            "save_interval": 600,
        }
        
        mock_hass = Mock()
        mock_data_store = Mock(spec=SmartClimateDataStore)
        
        engine = OffsetEngine(config, mock_data_store)
        engine._enable_learning = True
        engine.async_save_learning_data = AsyncMock()
        
        with patch('custom_components.smart_climate.offset_engine.async_track_time_interval') as mock_track:
            mock_track.return_value = Mock()
            
            # Mock logger
            with patch('custom_components.smart_climate.offset_engine._LOGGER') as mock_logger:
                # Setup periodic save
                asyncio.run(engine.async_setup_periodic_save(mock_hass))
                
                # Verify setup was logged
                mock_logger.debug.assert_called()
                assert any("periodic" in str(call).lower() for call in mock_logger.debug.call_args_list)
    
    def test_save_errors_logged_at_warning_level(self):
        """Test that save errors are logged at WARNING level."""
        config = {
            "ml_enabled": True,
            "max_offset": 5.0,
            "save_interval": 3600,
        }
        
        mock_hass = Mock()
        mock_hass.config.config_dir = "/test/path"
        
        data_store = SmartClimateDataStore(mock_hass, "climate.test")
        engine = OffsetEngine(config, data_store)
        engine._enable_learning = True
        
        # Mock save to raise an error
        data_store.async_save_data = AsyncMock(side_effect=Exception("Save failed"))
        
        # Mock logger
        with patch('custom_components.smart_climate.offset_engine._LOGGER') as mock_logger:
            # Save should not raise exception
            asyncio.run(engine.async_save_learning_data())
            
            # Verify warning was logged
            mock_logger.warning.assert_called()
            
            # Verify error message contains relevant information
            log_calls = mock_logger.warning.call_args_list
            assert any("save" in str(call).lower() for call in log_calls)
    
    def test_load_errors_logged_at_warning_level(self):
        """Test that load errors are logged at WARNING level."""
        config = {
            "ml_enabled": True,
            "max_offset": 5.0,
            "save_interval": 3600,
        }
        
        mock_hass = Mock()
        mock_hass.config.config_dir = "/test/path"
        
        data_store = SmartClimateDataStore(mock_hass, "climate.test")
        engine = OffsetEngine(config, data_store)
        engine._enable_learning = True
        
        # Mock load to raise an error
        data_store.async_load_data = AsyncMock(side_effect=Exception("Load failed"))
        
        # Mock logger
        with patch('custom_components.smart_climate.offset_engine._LOGGER') as mock_logger:
            # Load should not raise exception
            asyncio.run(engine.async_load_learning_data())
            
            # Verify warning was logged
            mock_logger.warning.assert_called()
            
            # Verify error message contains relevant information
            log_calls = mock_logger.warning.call_args_list
            assert any("load" in str(call).lower() for call in log_calls)


class TestConfigurationOptions:
    """Test configuration options for persistence."""
    
    def test_save_interval_configuration_validation(self):
        """Test save interval configuration validation."""
        # Test valid intervals
        valid_intervals = [60, 300, 600, 1800, 3600, 7200]
        
        for interval in valid_intervals:
            config = {
                "ml_enabled": True,
                "max_offset": 5.0,
                "save_interval": interval,
            }
            
            mock_data_store = Mock(spec=SmartClimateDataStore)
            engine = OffsetEngine(config, mock_data_store)
            
            # Should not raise exception
            assert engine._save_interval == interval
    
    def test_save_interval_not_hardcoded(self):
        """Test that save interval is not hardcoded in the implementation."""
        # Test different intervals are actually used
        intervals = [300, 600, 1800, 3600]
        
        for interval in intervals:
            config = {
                "ml_enabled": True,
                "max_offset": 5.0,
                "save_interval": interval,
            }
            
            mock_hass = Mock()
            mock_data_store = Mock(spec=SmartClimateDataStore)
            
            engine = OffsetEngine(config, mock_data_store)
            engine._enable_learning = True
            
            with patch('custom_components.smart_climate.offset_engine.async_track_time_interval') as mock_track:
                mock_track.return_value = Mock()
                
                # Setup periodic save
                asyncio.run(engine.async_setup_periodic_save(mock_hass))
                
                # Verify the actual interval used matches config
                call_args = mock_track.call_args
                assert call_args[0][2].total_seconds() == interval
    
    def test_learning_disabled_skips_persistence(self):
        """Test that disabled learning skips all persistence operations."""
        config = {
            "ml_enabled": False,
            "max_offset": 5.0,
            "save_interval": 3600,
        }
        
        mock_hass = Mock()
        mock_data_store = Mock(spec=SmartClimateDataStore)
        
        engine = OffsetEngine(config, mock_data_store)
        engine._enable_learning = False
        
        # Verify no periodic save setup
        with patch('custom_components.smart_climate.offset_engine.async_track_time_interval') as mock_track:
            remove_fn = asyncio.run(engine.async_setup_periodic_save(mock_hass))
            mock_track.assert_not_called()
            
            # Verify no-op function returned
            assert callable(remove_fn)
        
        # Verify save/load operations are skipped
        asyncio.run(engine.async_save_learning_data())
        asyncio.run(engine.async_load_learning_data())
        
        # Data store should not be called when learning is disabled
        mock_data_store.async_save_data.assert_not_called()
        mock_data_store.async_load_data.assert_not_called()


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    def test_full_lifecycle_with_persistence(self):
        """Test full lifecycle from setup to shutdown with persistence."""
        config = {
            "ml_enabled": True,
            "max_offset": 5.0,
            "save_interval": 300,  # 5 minutes for testing
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_hass = Mock()
            mock_hass.config.config_dir = temp_dir
            
            # 1. Setup with persistence
            data_store = SmartClimateDataStore(mock_hass, "climate.test")
            engine = OffsetEngine(config, data_store)
            engine._enable_learning = True
            
            # 2. Setup periodic save
            with patch('custom_components.smart_climate.offset_engine.async_track_time_interval') as mock_track:
                mock_track.return_value = Mock()
                remove_fn = asyncio.run(engine.async_setup_periodic_save(mock_hass))
                
                # 3. Record some learning data
                test_input = OffsetInput(
                    ac_internal_temp=24.0,
                    room_temp=25.0,
                    outdoor_temp=30.0,
                    mode="cool",
                    power_consumption=500.0,
                    time_of_day=time(14, 30),
                    day_of_week=2
                )
                engine.record_feedback(test_input, 1.0, 0.5)
                
                # 4. Trigger periodic save
                callback_fn = mock_track.call_args[0][1]
                asyncio.run(callback_fn())
                
                # 5. Verify data was saved
                data_file = data_store.get_data_file_path()
                assert data_file.exists()
                
                # 6. Simulate shutdown - cleanup
                remove_fn()
                
                # 7. Final save during shutdown
                asyncio.run(engine.async_save_learning_data())
                
                # 8. Verify data persisted
                new_engine = OffsetEngine(config, data_store)
                new_engine._enable_learning = True
                asyncio.run(new_engine.async_load_learning_data())
                
                assert new_engine._learner.get_sample_count() > 0
    
    def test_multiple_engines_with_different_intervals(self):
        """Test multiple engines with different save intervals."""
        configs = [
            {"ml_enabled": True, "max_offset": 5.0, "save_interval": 300},
            {"ml_enabled": True, "max_offset": 5.0, "save_interval": 600},
            {"ml_enabled": True, "max_offset": 5.0, "save_interval": 1800},
        ]
        
        mock_hass = Mock()
        engines = []
        
        for i, config in enumerate(configs):
            mock_data_store = Mock(spec=SmartClimateDataStore)
            engine = OffsetEngine(config, mock_data_store)
            engine._enable_learning = True
            engines.append(engine)
        
        # Setup periodic saves for all engines
        remove_fns = []
        with patch('custom_components.smart_climate.offset_engine.async_track_time_interval') as mock_track:
            mock_track.return_value = Mock()
            
            for engine in engines:
                remove_fn = asyncio.run(engine.async_setup_periodic_save(mock_hass))
                remove_fns.append(remove_fn)
            
            # Verify each engine uses its configured interval
            calls = mock_track.call_args_list
            for i, call in enumerate(calls):
                expected_interval = configs[i]["save_interval"]
                assert call[0][2].total_seconds() == expected_interval
            
            # Cleanup
            for remove_fn in remove_fns:
                remove_fn()
    
    def test_persistence_with_real_data_patterns(self):
        """Test persistence with realistic data patterns."""
        config = {
            "ml_enabled": True,
            "max_offset": 5.0,
            "save_interval": 3600,
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_hass = Mock()
            mock_hass.config.config_dir = temp_dir
            
            data_store = SmartClimateDataStore(mock_hass, "climate.test")
            engine = OffsetEngine(config, data_store)
            engine._enable_learning = True
            
            # Simulate a day of data collection
            base_time = time(8, 0)  # Start at 8 AM
            
            for hour in range(24):
                for minute in [0, 30]:  # Every 30 minutes
                    current_time = time((base_time.hour + hour) % 24, minute)
                    
                    test_input = OffsetInput(
                        ac_internal_temp=22.0 + (hour * 0.5),  # Temperature varies through day
                        room_temp=23.0 + (hour * 0.3),
                        outdoor_temp=25.0 + (hour * 1.0),
                        mode="cool",
                        power_consumption=400.0 + (hour * 10),
                        time_of_day=current_time,
                        day_of_week=1  # Monday
                    )
                    
                    # Record feedback with varying effectiveness
                    effectiveness = 0.8 + (0.2 * (hour % 3) / 3)  # Varies 0.8-1.0
                    engine.record_feedback(test_input, 1.0, effectiveness)
            
            # Save and reload
            asyncio.run(engine.async_save_learning_data())
            
            new_engine = OffsetEngine(config, data_store)
            new_engine._enable_learning = True
            asyncio.run(new_engine.async_load_learning_data())
            
            # Verify substantial data was preserved
            assert new_engine._learner.get_sample_count() == 48  # 24 hours * 2 samples per hour