"""Integration tests for data persistence using real filesystem."""

import tempfile
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from datetime import datetime, time

from custom_components.smart_climate.data_store import SmartClimateDataStore
from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.models import OffsetInput


class TestRealFilesystemPersistence:
    """Test persistence using real filesystem operations."""
    
    @pytest.mark.asyncio
    async def test_complete_save_load_cycle(self):
        """Test complete save and load cycle with real files."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock hass with real directory
            hass = Mock()
            hass.config.config_dir = temp_dir
            hass.async_add_executor_job = AsyncMock()
            
            # Mock executor to run functions directly (simulating real execution)
            def mock_executor(func, *args, **kwargs):
                return func(*args, **kwargs)
            hass.async_add_executor_job.side_effect = mock_executor
            
            # Create data store
            store = SmartClimateDataStore(hass, "climate.living_room")
            
            # Prepare test data
            test_learning_data = {
                "samples": [
                    {
                        "predicted": 1.0,
                        "actual": 0.8,
                        "ac_temp": 24.0,
                        "room_temp": 23.0,
                        "outdoor_temp": 30.0,
                        "mode": "normal",
                        "power": 150.0,
                        "hour": 14,
                        "day_of_week": 0,
                        "timestamp": "2025-07-07T14:30:00"
                    },
                    {
                        "predicted": 1.2,
                        "actual": 1.0,
                        "ac_temp": 25.0,
                        "room_temp": 24.0,
                        "outdoor_temp": 32.0,
                        "mode": "normal",
                        "power": 180.0,
                        "hour": 15,
                        "day_of_week": 0,
                        "timestamp": "2025-07-07T15:30:00"
                    }
                ],
                "statistics": {
                    "samples": 2,
                    "accuracy": 0.85,
                    "mean_error": 0.15
                }
            }
            
            # Save data
            await store.async_save_learning_data(test_learning_data)
            
            # Verify file was created
            data_file = store.get_data_file_path()
            assert data_file.exists()
            
            # Verify file contents
            with data_file.open("r", encoding="utf-8") as f:
                saved_data = json.load(f)
            
            assert saved_data["version"] == "1.0"
            assert saved_data["entity_id"] == "climate.living_room"
            assert saved_data["learning_enabled"] is True
            assert "last_updated" in saved_data
            assert saved_data["learning_data"] == test_learning_data
            
            # Load data back
            loaded_data = await store.async_load_learning_data()
            
            # Verify loaded data matches original
            assert loaded_data == test_learning_data
    
    @pytest.mark.asyncio
    async def test_offset_engine_full_persistence_cycle(self):
        """Test full OffsetEngine persistence cycle."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create first engine instance
            hass = Mock()
            hass.config.config_dir = temp_dir
            hass.async_add_executor_job = AsyncMock()
            
            # Mock executor to run functions directly
            def mock_executor(func, *args, **kwargs):
                return func(*args, **kwargs)
            hass.async_add_executor_job.side_effect = mock_executor
            
            # Create first engine with learning enabled
            config = {"max_offset": 5.0, "enable_learning": True}
            engine1 = OffsetEngine(config)
            
            # Set up data store
            store = SmartClimateDataStore(hass, "climate.test")
            engine1.set_data_store(store)
            
            # Record some learning data
            input_data = OffsetInput(
                ac_internal_temp=24.0,
                room_temp=23.0,
                outdoor_temp=30.0,
                mode="normal",
                power_consumption=150.0,
                time_of_day=time(14, 30),
                day_of_week=0
            )
            
            # Record multiple samples
            engine1.record_actual_performance(1.0, 0.8, input_data)
            engine1.record_actual_performance(1.2, 1.0, input_data)
            engine1.record_actual_performance(0.9, 0.7, input_data)
            
            # Verify data was recorded
            stats1 = engine1.get_learning_info()
            assert stats1["samples"] == 3
            assert stats1["enabled"] is True
            
            # Save learning data
            await engine1.async_save_learning_data()
            
            # Verify file was created
            data_file = store.get_data_file_path()
            assert data_file.exists()
            
            # Create second engine (simulating restart)
            engine2 = OffsetEngine(config)
            store2 = SmartClimateDataStore(hass, "climate.test")  # Same entity
            engine2.set_data_store(store2)
            
            # Initially, second engine should have no learning data
            stats2_before = engine2.get_learning_info()
            assert stats2_before["samples"] == 0
            
            # Load data into second engine
            success = await engine2.async_load_learning_data()
            assert success is True
            
            # Verify data was restored
            stats2_after = engine2.get_learning_info()
            assert stats2_after["samples"] == 3
            assert stats2_after["enabled"] is True
            
            # Verify learner state matches
            assert len(engine2._learner._training_samples) == 3
            
            # Test that both engines produce similar results
            result1 = engine1.calculate_offset(input_data)
            result2 = engine2.calculate_offset(input_data)
            
            # Results should be very similar (allowing for small floating point differences)
            assert abs(result1.offset - result2.offset) < 0.01
    
    @pytest.mark.asyncio
    async def test_backup_creation_and_atomic_write(self):
        """Test that backup files are created and atomic writes work."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            hass = Mock()
            hass.config.config_dir = temp_dir
            hass.async_add_executor_job = AsyncMock()
            
            def mock_executor(func, *args, **kwargs):
                return func(*args, **kwargs)
            hass.async_add_executor_job.side_effect = mock_executor
            
            store = SmartClimateDataStore(hass, "climate.test")
            
            # Save initial data
            initial_data = {"samples": [{"test": "initial"}]}
            await store.async_save_learning_data(initial_data)
            
            data_file = store.get_data_file_path()
            assert data_file.exists()
            
            # Save new data (should create backup)
            updated_data = {"samples": [{"test": "updated"}]}
            await store.async_save_learning_data(updated_data)
            
            # Verify backup was created
            backup_file = data_file.with_suffix(f"{data_file.suffix}.backup")
            assert backup_file.exists()
            
            # Verify backup contains initial data
            with backup_file.open("r", encoding="utf-8") as f:
                backup_data = json.load(f)
            assert backup_data["learning_data"] == initial_data
            
            # Verify main file contains updated data
            with data_file.open("r", encoding="utf-8") as f:
                current_data = json.load(f)
            assert current_data["learning_data"] == updated_data
    
    @pytest.mark.asyncio
    async def test_multiple_entities_separate_files(self):
        """Test that multiple entities get separate files."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            hass = Mock()
            hass.config.config_dir = temp_dir
            hass.async_add_executor_job = AsyncMock()
            
            def mock_executor(func, *args, **kwargs):
                return func(*args, **kwargs)
            hass.async_add_executor_job.side_effect = mock_executor
            
            # Create data stores for different entities
            store1 = SmartClimateDataStore(hass, "climate.living_room")
            store2 = SmartClimateDataStore(hass, "climate.bedroom")
            
            # Save different data to each
            data1 = {"samples": [{"entity": "living_room"}]}
            data2 = {"samples": [{"entity": "bedroom"}]}
            
            await store1.async_save_learning_data(data1)
            await store2.async_save_learning_data(data2)
            
            # Verify separate files were created
            file1 = store1.get_data_file_path()
            file2 = store2.get_data_file_path()
            
            assert file1.exists()
            assert file2.exists()
            assert file1 != file2
            assert "living_room" in file1.name
            assert "bedroom" in file2.name
            
            # Verify data is isolated
            loaded1 = await store1.async_load_learning_data()
            loaded2 = await store2.async_load_learning_data()
            
            assert loaded1 == data1
            assert loaded2 == data2
            assert loaded1 != loaded2
    
    def test_safe_filename_generation(self):
        """Test filename generation for various entity IDs."""
        hass = Mock()
        hass.config.config_dir = "/test"
        
        test_cases = [
            ("climate.living_room", "climate_living_room"),
            ("climate.main/floor", "climate_main_floor"),
            ("climate.room-1", "climate_room-1"),  # Hyphens are safe
            ("climate.test%entity", "climate_test_entity"),
            ("climate.test@home.com", "climate_test_home_com"),
        ]
        
        for entity_id, expected_part in test_cases:
            store = SmartClimateDataStore(hass, entity_id)
            filename = store.get_data_file_path().name
            
            # Should contain the expected safe part
            assert expected_part in filename
            # Should be a valid JSON filename
            assert filename.endswith(".json")
            # Should start with the prefix
            assert filename.startswith("smart_climate_learning_")
            # Should not contain unsafe characters
            unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
            assert not any(char in filename for char in unsafe_chars)
        
        # Test Unicode characters (modern filesystems handle these fine)
        unicode_entity = "climate.über_room"
        store = SmartClimateDataStore(hass, unicode_entity)
        filename = store.get_data_file_path().name
        
        # Should be a valid filename
        assert filename.endswith(".json")
        assert filename.startswith("smart_climate_learning_")
        # Should contain recognizable parts (über is valid in modern filesystems)
        assert "über" in filename or "_ber" in filename  # Either Unicode preserved or converted