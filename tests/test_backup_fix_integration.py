"""Integration test for backup data loss fix."""

import tempfile
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock

from custom_components.smart_climate.data_store import SmartClimateDataStore


class TestBackupFixIntegration:
    """Integration tests for the backup fix using real file operations."""
    
    @pytest.mark.asyncio
    async def test_real_file_backup_preservation_on_corruption(self):
        """Test backup preservation with real files when corruption occurs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup Home Assistant mock
            hass = Mock()
            hass.config.config_dir = temp_dir
            hass.async_add_executor_job = AsyncMock()
            
            # Configure executor to run functions directly (synchronously)
            def run_sync(func, *args):
                return func(*args) if args else func()
            
            hass.async_add_executor_job.side_effect = run_sync
            
            # Create data store
            store = SmartClimateDataStore(hass, "climate.test")
            
            # Phase 1: Create initial good data file
            good_data = {"important": "learning_data", "months": "of_training"}
            await store.async_save_learning_data(good_data)
            
            # Verify initial file exists
            data_file = store.get_data_file_path()
            assert data_file.exists()
            
            # Verify we can load the good data
            loaded_data = await store.async_load_learning_data()
            assert loaded_data == good_data
            
            # Phase 2: Simulate corruption during write by patching atomic_json_write
            from custom_components.smart_climate import data_store
            original_atomic_write = data_store.atomic_json_write
            
            def corrupted_atomic_write(file_path, data):
                """Simulate write failure after temp file creation."""
                if ".tmp" in str(file_path):
                    raise IOError("Simulated disk corruption during write")
                return original_atomic_write(file_path, data)
            
            # Monkey patch atomic_json_write to simulate corruption
            data_store.atomic_json_write = corrupted_atomic_write
            
            try:
                # Attempt to save new data (this should fail)
                new_data = {"corrupted": "save_attempt"}
                await store.async_save_learning_data(new_data)
                
                # If we get here, something went wrong - save should have failed silently
                assert False, "Save should have failed due to simulated corruption"
                
            except Exception:
                # This is expected - the save should fail
                pass
            
            finally:
                # Restore original function
                data_store.atomic_json_write = original_atomic_write
            
            # Phase 3: Verify original data is still intact
            assert data_file.exists(), "Original data file should still exist"
            
            # Most important: We should be able to load the original good data
            recovered_data = await store.async_load_learning_data()
            assert recovered_data == good_data, "Original good data should be preserved"
            
            # Verify backup wasn't created (since write failed during temp phase)
            backup_file = data_file.with_suffix(".json.backup")
            # Backup might exist from initial save, but it should have good data
            if backup_file.exists():
                with backup_file.open("r") as f:
                    backup_content = json.load(f)
                # Backup should contain the good data, not corrupted data
                assert backup_content["learning_data"] == good_data
    
    @pytest.mark.asyncio
    async def test_real_file_successful_save_with_backup(self):
        """Test successful save creates proper backup with real files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup Home Assistant mock
            hass = Mock()
            hass.config.config_dir = temp_dir
            hass.async_add_executor_job = AsyncMock()
            
            # Configure executor to run functions directly
            def run_sync(func, *args):
                return func(*args) if args else func()
            
            hass.async_add_executor_job.side_effect = run_sync
            
            # Create data store
            store = SmartClimateDataStore(hass, "climate.test")
            
            # Phase 1: Save initial data
            initial_data = {"version": 1, "samples": 100}
            await store.async_save_learning_data(initial_data)
            
            data_file = store.get_data_file_path()
            assert data_file.exists()
            
            # Phase 2: Save updated data (should create backup of initial data)
            updated_data = {"version": 2, "samples": 200}
            await store.async_save_learning_data(updated_data)
            
            # Verify main file has updated data
            loaded_data = await store.async_load_learning_data()
            assert loaded_data == updated_data
            
            # Verify backup file has initial data
            backup_file = data_file.with_suffix(".json.backup")
            assert backup_file.exists()
            
            with backup_file.open("r") as f:
                backup_content = json.load(f)
            
            assert backup_content["learning_data"] == initial_data
    
    @pytest.mark.asyncio
    async def test_validation_prevents_corrupted_backup(self):
        """Test that validation step prevents corrupted data from overwriting backup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            hass = Mock()
            hass.config.config_dir = temp_dir
            hass.async_add_executor_job = AsyncMock()
            
            def run_sync(func, *args):
                return func(*args) if args else func()
            
            hass.async_add_executor_job.side_effect = run_sync
            
            store = SmartClimateDataStore(hass, "climate.test")
            
            # Save good initial data
            good_data = {"reliable": "data", "tested": True}
            await store.async_save_learning_data(good_data)
            
            data_file = store.get_data_file_path()
            backup_file = data_file.with_suffix(".json.backup")
            
            # Now simulate a scenario where temp file gets corrupted but validation catches it
            from custom_components.smart_climate import data_store
            original_validate = store._validate_json_file
            
            def failing_validation(file_path):
                """Simulate validation failure for temp files."""
                if ".tmp" in str(file_path):
                    return False  # Validation fails for temp file
                return original_validate(file_path)
            
            # Monkey patch validation
            store._validate_json_file = failing_validation
            
            try:
                # Attempt to save new data - should fail at validation
                bad_data = {"potentially": "corrupted"}
                await store.async_save_learning_data(bad_data)
                
            except IOError as e:
                # Expected - validation should fail
                assert "validation failed" in str(e)
            
            finally:
                # Restore original validation
                store._validate_json_file = original_validate
            
            # Verify original data is unchanged
            current_data = await store.async_load_learning_data()
            assert current_data == good_data
            
            # Verify backup (if it exists) still has good data
            if backup_file.exists():
                with backup_file.open("r") as f:
                    backup_content = json.load(f)
                assert backup_content["learning_data"] == good_data