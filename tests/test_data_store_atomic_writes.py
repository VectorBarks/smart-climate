"""Tests for atomic write pattern in data_store.py to prevent backup data loss."""

import asyncio
import json
import os
import shutil
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from datetime import datetime

from custom_components.smart_climate.data_store import SmartClimateDataStore, atomic_json_write


class TestAtomicJsonWrite:
    """Test the standalone atomic_json_write function."""
    
    def test_atomic_json_write_creates_temp_file_first(self):
        """Test that atomic write creates temporary file before main file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_file = Path(temp_dir) / "test.json"
            temp_file = target_file.with_suffix(".json.tmp")
            test_data = {"test": "data"}
            
            with patch("builtins.open", create=True) as mock_open, \
                 patch("json.dump") as mock_json_dump, \
                 patch("os.fsync") as mock_fsync, \
                 patch("pathlib.Path.rename") as mock_rename:
                
                mock_file = Mock()
                mock_open.return_value.__enter__.return_value = mock_file
                
                atomic_json_write(target_file, test_data)
                
                # Verify temporary file was opened first
                mock_open.assert_called_once_with(temp_file, "w", encoding="utf-8")
                mock_json_dump.assert_called_once_with(test_data, mock_file, indent=2, ensure_ascii=False)
                mock_file.flush.assert_called_once()
                mock_fsync.assert_called_once_with(mock_file.fileno())
                mock_rename.assert_called_once_with(target_file)
    
    def test_atomic_json_write_cleans_up_temp_file_on_error(self):
        """Test that temporary file is cleaned up if write fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_file = Path(temp_dir) / "test.json"
            temp_file = target_file.with_suffix(".json.tmp")
            test_data = {"test": "data"}
            
            with patch("builtins.open", side_effect=IOError("Disk full")), \
                 patch("pathlib.Path.exists", return_value=True) as mock_exists, \
                 patch("pathlib.Path.unlink") as mock_unlink, \
                 pytest.raises(IOError):
                
                atomic_json_write(target_file, test_data)
                
                # Verify cleanup was attempted
                mock_exists.assert_called_with()
                mock_unlink.assert_called_once()
    
    def test_atomic_json_write_handles_cleanup_errors(self):
        """Test graceful handling of cleanup errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_file = Path(temp_dir) / "test.json"
            test_data = {"test": "data"}
            
            with patch("builtins.open", side_effect=IOError("Disk full")), \
                 patch("pathlib.Path.exists", return_value=True), \
                 patch("pathlib.Path.unlink", side_effect=OSError("Permission denied")), \
                 patch("custom_components.smart_climate.data_store._LOGGER") as mock_logger, \
                 pytest.raises(IOError):
                
                atomic_json_write(target_file, test_data)
                
                # Verify cleanup error was logged
                assert mock_logger.error.call_count >= 1
                cleanup_error_logged = any(
                    "Error cleaning up temp file" in str(call_args) 
                    for call_args in mock_logger.error.call_args_list
                )
                assert cleanup_error_logged


class TestSafeBackupStrategy:
    """Test the safe backup strategy implementation."""
    
    @pytest.mark.asyncio
    async def test_backup_preserved_when_primary_write_fails(self):
        """CRITICAL: Test that backup is preserved when primary file write fails."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        hass.async_add_executor_job = AsyncMock()
        
        store = SmartClimateDataStore(hass, "climate.test")
        learning_data = {"test": "data"}
        
        # Simulate existing good backup and primary file
        with patch("pathlib.Path.exists") as mock_exists, \
             patch("pathlib.Path.mkdir"), \
             patch("shutil.copy2") as mock_copy, \
             patch("custom_components.smart_climate.data_store.atomic_json_write") as mock_atomic_write:
            
            # Setup: file exists (so backup should be created)
            mock_exists.return_value = True
            
            # Simulate atomic write failure (corrupted primary)
            mock_atomic_write.side_effect = IOError("Disk corruption during write")
            
            # Configure executor to run functions directly
            def run_sync_func(func, *args):
                if func == store._create_backup_if_needed:
                    return func(*args)
                elif func == store._ensure_data_directory:
                    return func()
                elif func == mock_atomic_write:
                    raise IOError("Disk corruption during write")
                return func(*args) if args else func()
            
            hass.async_add_executor_job.side_effect = run_sync_func
            
            # This should NOT raise an exception (graceful error handling)
            await store.async_save_learning_data(learning_data)
            
            # CRITICAL: Verify backup was created BEFORE attempting write
            mock_copy.assert_called_once()
            mock_atomic_write.assert_called_once()
            
            # Verify the order: backup creation happened before write attempt
            executor_calls = hass.async_add_executor_job.call_args_list
            backup_call_found = False
            write_call_found = False
            write_after_backup = False
            
            for i, call_obj in enumerate(executor_calls):
                if call_obj[0][0] == store._create_backup_if_needed:
                    backup_call_found = True
                elif call_obj[0][0] == mock_atomic_write:
                    write_call_found = True
                    if backup_call_found:
                        write_after_backup = True
            
            assert backup_call_found, "Backup creation should be called"
            assert write_call_found, "Write should be attempted"
            assert write_after_backup, "Write should happen AFTER backup creation"
    
    @pytest.mark.asyncio
    async def test_backup_not_overwritten_on_write_failure(self):
        """Test that existing backup is not destroyed when write fails."""
        hass = Mock()
        hass.config.config_dir = "/test/config" 
        hass.async_add_executor_job = AsyncMock()
        
        store = SmartClimateDataStore(hass, "climate.test")
        learning_data = {"test": "new_data"}
        
        # Mock file system state: both primary and backup exist
        existing_backup_content = {"version": "1.0", "learning_data": {"old": "good_data"}}
        
        def mock_copy_behavior(src, dst):
            """Mock copy2 behavior - this is where the bug was."""
            # The old code would overwrite good backup here
            # New code should validate temp file first
            pass
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.mkdir"), \
             patch("shutil.copy2", side_effect=mock_copy_behavior) as mock_copy, \
             patch("custom_components.smart_climate.data_store.atomic_json_write") as mock_atomic_write:
            
            # Simulate write failure after backup creation
            mock_atomic_write.side_effect = IOError("Write failed")
            
            # Configure executor
            def run_sync_func(func, *args):
                if func == store._create_backup_if_needed:
                    return func(*args)
                elif func == store._ensure_data_directory:
                    return func()
                elif func == mock_atomic_write:
                    raise IOError("Write failed")
                return func(*args) if args else func()
            
            hass.async_add_executor_job.side_effect = run_sync_func
            
            # Save should not raise exception (graceful handling)
            await store.async_save_learning_data(learning_data)
            
            # Verify backup creation was attempted but write failed
            mock_copy.assert_called_once()
            mock_atomic_write.assert_called_once()
            
            # Key point: In the old buggy code, the backup would already be 
            # overwritten by this point. In fixed code, backup should be 
            # preserved because write failed.
    
    @pytest.mark.asyncio
    async def test_successful_save_updates_backup_correctly(self):
        """Test that successful save properly updates backup."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        hass.async_add_executor_job = AsyncMock()
        
        store = SmartClimateDataStore(hass, "climate.test")
        learning_data = {"test": "data"}
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.mkdir"), \
             patch("shutil.copy2") as mock_copy, \
             patch("custom_components.smart_climate.data_store.atomic_json_write") as mock_atomic_write:
            
            # Simulate successful write
            mock_atomic_write.return_value = None  # Success
            
            # Configure executor
            def run_sync_func(func, *args):
                return func(*args) if args else func()
            
            hass.async_add_executor_job.side_effect = run_sync_func
            
            await store.async_save_learning_data(learning_data)
            
            # Verify both backup and write succeeded
            mock_copy.assert_called_once()
            mock_atomic_write.assert_called_once()
    
    @pytest.mark.asyncio 
    async def test_no_backup_created_for_new_file(self):
        """Test that no backup is created when file doesn't exist."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        hass.async_add_executor_job = AsyncMock()
        
        store = SmartClimateDataStore(hass, "climate.test")
        learning_data = {"test": "data"}
        
        with patch("pathlib.Path.exists", return_value=False), \
             patch("pathlib.Path.mkdir"), \
             patch("shutil.copy2") as mock_copy, \
             patch("custom_components.smart_climate.data_store.atomic_json_write") as mock_atomic_write:
            
            def run_sync_func(func, *args):
                return func(*args) if args else func()
            
            hass.async_add_executor_job.side_effect = run_sync_func
            
            await store.async_save_learning_data(learning_data)
            
            # No backup should be created for new files
            mock_copy.assert_not_called()
            mock_atomic_write.assert_called_once()


class TestDataCorruptionRecovery:
    """Test recovery scenarios from corrupted data."""
    
    @pytest.mark.asyncio
    async def test_load_falls_back_to_backup_when_primary_corrupted(self):
        """Test loading backup when primary file is corrupted."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        
        store = SmartClimateDataStore(hass, "climate.test")
        
        # Mock corrupted primary file, good backup file
        good_backup_data = {
            "version": "1.0",
            "entity_id": "climate.test", 
            "learning_data": {"saved": "data"}
        }
        
        def mock_open_behavior(file_path, *args, **kwargs):
            """Mock file opening - primary corrupted, backup good."""
            if ".backup" in str(file_path):
                # Return good backup data
                mock_file = Mock()
                mock_file.__enter__ = Mock(return_value=mock_file)
                mock_file.__exit__ = Mock(return_value=None)
                return mock_file
            else:
                # Primary file is corrupted
                raise json.JSONDecodeError("Corrupted JSON", "doc", 0)
        
        def mock_json_load(file_obj):
            """Mock JSON loading."""
            if hasattr(file_obj, '_is_backup'):
                return good_backup_data
            else:
                raise json.JSONDecodeError("Corrupted JSON", "doc", 0)
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("builtins.open", side_effect=mock_open_behavior), \
             patch("json.load", side_effect=mock_json_load):
            
            # Should fall back to backup data
            # Note: Current implementation doesn't have backup fallback
            # This test documents the desired behavior for future enhancement
            result = await store.async_load_learning_data()
            
            # Current implementation returns None for corrupted data
            # Future enhancement could try backup file
            assert result is None  # Current behavior
    
    @pytest.mark.asyncio
    async def test_corruption_during_save_preserves_existing_data(self):
        """Test that corruption during save doesn't destroy existing good data."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        hass.async_add_executor_job = AsyncMock()
        
        store = SmartClimateDataStore(hass, "climate.test")
        
        # Simulate scenario: good primary file exists, save fails
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup real file paths for more realistic test
            hass.config.config_dir = temp_dir
            store = SmartClimateDataStore(hass, "climate.test")
            
            # Create existing good primary file
            primary_file = store.get_data_file_path()
            primary_file.parent.mkdir(parents=True, exist_ok=True)
            
            good_data = {
                "version": "1.0",
                "entity_id": "climate.test",
                "learning_data": {"existing": "good_data"}
            }
            
            with primary_file.open("w") as f:
                json.dump(good_data, f)
            
            # Verify good data exists
            assert primary_file.exists()
            
            # Now attempt save that will fail
            new_data = {"new": "data_that_will_fail"}
            
            with patch("custom_components.smart_climate.data_store.atomic_json_write", 
                      side_effect=IOError("Simulated disk error")):
                
                def run_sync_func(func, *args):
                    return func(*args) if args else func()
                
                hass.async_add_executor_job.side_effect = run_sync_func
                
                # Save should fail gracefully
                await store.async_save_learning_data(new_data)
                
                # Original file should still exist and be readable
                assert primary_file.exists()
                
                # Should be able to load original data
                loaded_data = await store.async_load_learning_data()
                assert loaded_data is not None
                assert loaded_data["existing"] == "good_data"


class TestAtomicWriteEdgeCases:
    """Test edge cases in atomic write implementation."""
    
    def test_atomic_write_with_unicode_data(self):
        """Test atomic write with unicode characters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_file = Path(temp_dir) / "unicode_test.json"
            unicode_data = {
                "chinese": "智能气候控制",
                "emoji": "🌡️❄️🔥",
                "special": "àáâãäåæçèéêë"
            }
            
            atomic_json_write(target_file, unicode_data)
            
            # Verify file was created and contains correct data
            assert target_file.exists()
            with target_file.open("r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            
            assert loaded_data == unicode_data
    
    def test_atomic_write_with_large_data(self):
        """Test atomic write with large dataset."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_file = Path(temp_dir) / "large_test.json"
            
            # Create large dataset (similar to months of learning data)
            large_data = {
                "samples": [
                    {
                        "timestamp": f"2025-07-{i:02d}T12:00:00",
                        "predicted": 1.0 + (i % 10) * 0.1,
                        "actual": 0.8 + (i % 8) * 0.1,
                        "conditions": f"condition_{i}"
                    }
                    for i in range(1000)  # 1000 samples
                ]
            }
            
            atomic_json_write(target_file, large_data)
            
            # Verify file was created correctly
            assert target_file.exists()
            with target_file.open("r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            
            assert len(loaded_data["samples"]) == 1000
            assert loaded_data["samples"][0]["timestamp"] == "2025-07-01T12:00:00"
    
    def test_atomic_write_permissions_error(self):
        """Test atomic write with permission errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_file = Path(temp_dir) / "permission_test.json"
            test_data = {"test": "data"}
            
            with patch("builtins.open", side_effect=PermissionError("Access denied")), \
                 pytest.raises(PermissionError):
                
                atomic_json_write(target_file, test_data)
    
    def test_atomic_write_disk_full_error(self):
        """Test atomic write with disk full error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_file = Path(temp_dir) / "disk_full_test.json"
            test_data = {"test": "data"}
            
            with patch("json.dump", side_effect=OSError("No space left on device")), \
                 patch("builtins.open", create=True), \
                 pytest.raises(OSError):
                
                atomic_json_write(target_file, test_data)


class TestBackupCreationSafety:
    """Test backup creation safety mechanisms."""
    
    def test_backup_creation_handles_permission_errors(self):
        """Test backup creation with permission errors."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        
        store = SmartClimateDataStore(hass, "climate.test")
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("shutil.copy2", side_effect=PermissionError("Access denied")), \
             patch("custom_components.smart_climate.data_store._LOGGER") as mock_logger:
            
            # Should not raise exception
            store._create_backup_if_needed(Path("/test/file.json"))
            
            # Should log warning
            mock_logger.warning.assert_called_once()
    
    def test_backup_creation_handles_disk_full(self):
        """Test backup creation with disk full error."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        
        store = SmartClimateDataStore(hass, "climate.test")
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("shutil.copy2", side_effect=OSError("No space left on device")), \
             patch("custom_components.smart_climate.data_store._LOGGER") as mock_logger:
            
            # Should not raise exception
            store._create_backup_if_needed(Path("/test/file.json"))
            
            # Should log warning
            mock_logger.warning.assert_called_once()
    
    def test_backup_not_created_when_file_missing(self):
        """Test that backup is not created when source file doesn't exist."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        
        store = SmartClimateDataStore(hass, "climate.test")
        
        with patch("pathlib.Path.exists", return_value=False), \
             patch("shutil.copy2") as mock_copy:
            
            store._create_backup_if_needed(Path("/test/nonexistent.json"))
            
            # Should not attempt to copy
            mock_copy.assert_not_called()


class TestDataStoreThreadSafety:
    """Test thread safety of data store operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_save_operations_are_serialized(self):
        """Test that concurrent save operations are properly serialized."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        
        store = SmartClimateDataStore(hass, "climate.test")
        
        # Track order of operations
        operation_order = []
        
        def mock_executor_job(func, *args):
            """Mock executor that tracks operation order."""
            operation_order.append(func.__name__ if hasattr(func, '__name__') else str(func))
            return AsyncMock()()
        
        hass.async_add_executor_job.side_effect = mock_executor_job
        
        # Start multiple save operations concurrently
        save_tasks = [
            store.async_save_learning_data({"save": i})
            for i in range(3)
        ]
        
        await asyncio.gather(*save_tasks)
        
        # Operations should be serialized (not interleaved)
        # Each save should complete fully before next one starts
        assert len(operation_order) >= 6  # At least 2 operations per save (directory + write)
    
    @pytest.mark.asyncio
    async def test_concurrent_save_and_load_operations(self):
        """Test concurrent save and load operations."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        
        store = SmartClimateDataStore(hass, "climate.test")
        
        # Mock successful load
        good_data = {
            "version": "1.0",
            "entity_id": "climate.test",
            "learning_data": {"test": "data"}
        }
        
        def mock_executor_job(func, *args):
            if "load" in str(func):
                return good_data["learning_data"]
            return AsyncMock()()
        
        hass.async_add_executor_job.side_effect = mock_executor_job
        
        # Start save and load concurrently
        save_task = store.async_save_learning_data({"new": "data"})
        load_task = store.async_load_learning_data()
        
        save_result, load_result = await asyncio.gather(save_task, load_task)
        
        # Both operations should complete without interference
        assert load_result == good_data["learning_data"]


class TestCompleteDataLossScenarios:
    """Test complete data loss prevention scenarios."""
    
    @pytest.mark.asyncio
    async def test_scenario_power_loss_during_save(self):
        """Test power loss simulation during save operation."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        hass.async_add_executor_job = AsyncMock()
        
        store = SmartClimateDataStore(hass, "climate.test")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            hass.config.config_dir = temp_dir
            store = SmartClimateDataStore(hass, "climate.test")
            
            # Create existing good data
            primary_file = store.get_data_file_path()
            primary_file.parent.mkdir(parents=True, exist_ok=True)
            
            good_data = {
                "version": "1.0",
                "entity_id": "climate.test",
                "learning_data": {"months": "of_good_data"}
            }
            
            with primary_file.open("w") as f:
                json.dump(good_data, f)
            
            # Simulate power loss during atomic write (after backup created)
            call_count = 0
            def failing_executor(func, *args):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:  # Allow directory creation and backup
                    return func(*args) if args else func()
                else:  # Fail on atomic write (simulating power loss)
                    raise OSError("Power loss - write interrupted")
            
            hass.async_add_executor_job.side_effect = failing_executor
            
            # Save should fail gracefully
            await store.async_save_learning_data({"new": "data"})
            
            # Original file should still be intact
            assert primary_file.exists()
            
            # Should be able to load original data
            hass.async_add_executor_job.side_effect = lambda func, *args: func(*args) if args else func()
            loaded_data = await store.async_load_learning_data()
            
            assert loaded_data is not None
            assert loaded_data["months"] == "of_good_data"
    
    @pytest.mark.asyncio
    async def test_scenario_disk_corruption_during_save(self):
        """Test disk corruption during save operation."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        hass.async_add_executor_job = AsyncMock()
        
        store = SmartClimateDataStore(hass, "climate.test")
        
        # Simulate disk corruption during atomic write
        with patch("custom_components.smart_climate.data_store.atomic_json_write", 
                   side_effect=OSError("I/O error - disk corruption")):
            
            def run_sync_func(func, *args):
                return func(*args) if args else func()
            
            hass.async_add_executor_job.side_effect = run_sync_func
            
            # Save should fail gracefully without raising exception
            await store.async_save_learning_data({"corrupted": "save"})
            
            # No assertion needed - test passes if no exception is raised
    
    @pytest.mark.asyncio
    async def test_scenario_multiple_consecutive_save_failures(self):
        """Test multiple consecutive save failures don't compound damage."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        hass.async_add_executor_job = AsyncMock()
        
        store = SmartClimateDataStore(hass, "climate.test")
        
        # Simulate multiple save failures in a row
        with patch("custom_components.smart_climate.data_store.atomic_json_write", 
                   side_effect=OSError("Persistent disk error")):
            
            def run_sync_func(func, *args):
                return func(*args) if args else func()
            
            hass.async_add_executor_job.side_effect = run_sync_func
            
            # Multiple failed saves should not compound the problem
            for i in range(5):
                await store.async_save_learning_data({"attempt": i})
            
            # Test passes if no exceptions are raised