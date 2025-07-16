"""Tests for learning data persistence system."""

import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, time

from custom_components.smart_climate.data_store import SmartClimateDataStore
from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.lightweight_learner import LightweightOffsetLearner
from custom_components.smart_climate.models import OffsetInput


class TestSmartClimateDataStore:
    """Test the SmartClimateDataStore class."""
    
    def test_init_creates_data_store_with_entity_id(self):
        """Test initialization with entity ID."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        
        store = SmartClimateDataStore(hass, "climate.test_entity")
        
        assert store._hass == hass
        assert store._entity_id == "climate.test_entity"
        assert "climate_test_entity" in str(store._data_file_path)
    
    def test_get_data_file_path_creates_safe_filename(self):
        """Test data file path creation with safe filename."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        
        store = SmartClimateDataStore(hass, "climate.test/entity-with.special%chars")
        path = store.get_data_file_path()
        
        assert path.name == "smart_climate_learning_climate_test_entity-with_special_chars.json"
        assert path.parent.name == ".storage"
    
    def test_ensure_data_directory_creates_directory(self):
        """Test data directory creation."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        
        store = SmartClimateDataStore(hass, "climate.test")
        
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            store._ensure_data_directory()
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    
    @pytest.mark.asyncio
    async def test_save_learning_data_creates_json_file(self):
        """Test saving learning data to JSON file."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        hass.async_add_executor_job = AsyncMock()
        
        store = SmartClimateDataStore(hass, "climate.test")
        
        learning_data = {
            "samples": [{"test": "data"}],
            "time_patterns": {"morning": 0.5},
            "temperature_correlation": 0.75,
            "stats": {"accuracy": 0.8}
        }
        
        with patch("pathlib.Path.mkdir"), \
             patch("builtins.open", create=True) as mock_open, \
             patch("json.dump") as mock_json_dump, \
             patch("pathlib.Path.rename") as mock_rename:
            
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            await store.async_save_learning_data(learning_data)
            
            # Verify that executor jobs were called for directory creation, backup, and atomic write
            assert hass.async_add_executor_job.call_count >= 2  # At least directory and write operations
            
            # Verify atomic write was called through executor
            executor_calls = [call[0][0] for call in hass.async_add_executor_job.call_args_list]
            assert any("atomic_json_write" in str(func) for func in executor_calls)
    
    @pytest.mark.asyncio
    async def test_save_learning_data_creates_backup_if_file_exists(self):
        """Test backup creation when overwriting existing file."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        hass.async_add_executor_job = AsyncMock()
        
        store = SmartClimateDataStore(hass, "climate.test")
        
        learning_data = {"test": "data"}
        
        with patch("pathlib.Path.mkdir"), \
             patch("builtins.open", create=True), \
             patch("json.dump"), \
             patch("pathlib.Path.rename"), \
             patch("pathlib.Path.exists") as mock_exists, \
             patch("shutil.copy2") as mock_copy:
            
            mock_exists.return_value = True
            
            await store.async_save_learning_data(learning_data)
            
            # Verify executor jobs were called 
            assert hass.async_add_executor_job.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_save_learning_data_handles_write_errors(self):
        """Test error handling during save operations."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        
        store = SmartClimateDataStore(hass, "climate.test")
        
        learning_data = {"test": "data"}
        
        with patch("pathlib.Path.mkdir"), \
             patch("builtins.open", side_effect=OSError("Disk full")), \
             patch("custom_components.smart_climate.data_store._LOGGER") as mock_logger:
            
            await store.async_save_learning_data(learning_data)
            
            # Should log error and not raise exception
            mock_logger.error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_load_learning_data_returns_saved_data(self):
        """Test loading learning data from JSON file."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        
        store = SmartClimateDataStore(hass, "climate.test")
        
        saved_data = {
            "version": "1.0",
            "entity_id": "climate.test",
            "last_updated": "2025-07-07T17:15:00Z",
            "learning_enabled": True,
            "learning_data": {
                "samples": [{"test": "data"}],
                "time_patterns": {"morning": 0.5}
            }
        }
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("builtins.open", create=True) as mock_open, \
             patch("json.load", return_value=saved_data):
            
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            result = await store.async_load_learning_data()
            
            assert result == saved_data["learning_data"]
    
    @pytest.mark.asyncio
    async def test_load_learning_data_handles_missing_file(self):
        """Test loading when file doesn't exist."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        
        store = SmartClimateDataStore(hass, "climate.test")
        
        with patch("pathlib.Path.exists", return_value=False):
            result = await store.async_load_learning_data()
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_load_learning_data_handles_corrupted_json(self):
        """Test loading corrupted JSON file."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        
        store = SmartClimateDataStore(hass, "climate.test")
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("builtins.open", create=True), \
             patch("json.load", side_effect=json.JSONDecodeError("Bad JSON", "", 0)), \
             patch("custom_components.smart_climate.data_store._LOGGER") as mock_logger:
            
            result = await store.async_load_learning_data()
            
            assert result is None
            mock_logger.warning.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_load_learning_data_handles_permission_errors(self):
        """Test loading with permission errors."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        
        store = SmartClimateDataStore(hass, "climate.test")
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("builtins.open", side_effect=PermissionError("Access denied")), \
             patch("custom_components.smart_climate.data_store._LOGGER") as mock_logger:
            
            result = await store.async_load_learning_data()
            
            assert result is None
            mock_logger.error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_load_learning_data_validates_version(self):
        """Test loading data with version validation."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        
        store = SmartClimateDataStore(hass, "climate.test")
        
        # Test unsupported version
        saved_data = {
            "version": "2.0",
            "entity_id": "climate.test",
            "learning_data": {"test": "data"}
        }
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("builtins.open", create=True), \
             patch("json.load", return_value=saved_data), \
             patch("custom_components.smart_climate.data_store._LOGGER") as mock_logger:
            
            result = await store.async_load_learning_data()
            
            assert result is None
            mock_logger.warning.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_load_learning_data_validates_entity_id(self):
        """Test loading data with entity ID validation."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        
        store = SmartClimateDataStore(hass, "climate.test")
        
        # Test mismatched entity ID
        saved_data = {
            "version": "1.0",
            "entity_id": "climate.different",
            "learning_data": {"test": "data"}
        }
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("builtins.open", create=True), \
             patch("json.load", return_value=saved_data), \
             patch("custom_components.smart_climate.data_store._LOGGER") as mock_logger:
            
            result = await store.async_load_learning_data()
            
            assert result is None
            mock_logger.warning.assert_called_once()


class TestOffsetEnginePersistence:
    """Test OffsetEngine persistence integration."""
    
    def test_offset_engine_has_persistence_methods(self):
        """Test that OffsetEngine has persistence methods."""
        config = {"max_offset": 5.0, "enable_learning": True}
        engine = OffsetEngine(config)
        
        # Should have new persistence methods
        assert hasattr(engine, "async_save_learning_data")
        assert hasattr(engine, "async_load_learning_data")
        assert callable(engine.async_save_learning_data)
        assert callable(engine.async_load_learning_data)
    
    @pytest.mark.asyncio
    async def test_offset_engine_save_learning_data_serializes_learner_state(self):
        """Test saving learning data from OffsetEngine."""
        config = {"max_offset": 5.0, "enable_learning": True}
        engine = OffsetEngine(config)
        
        # Mock data store
        mock_store = Mock()
        mock_store.async_save_learning_data = AsyncMock()
        engine._data_store = mock_store
        
        # Add some learning data
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=23.0,
            outdoor_temp=30.0,
            mode="normal",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=0
        )
        
        engine.record_actual_performance(1.0, 0.8, input_data)
        
        # Save learning data
        await engine.async_save_learning_data()
        
        # Verify data store was called with learning data
        mock_store.async_save_learning_data.assert_called_once()
        call_args = mock_store.async_save_learning_data.call_args[0][0]
        
        assert "samples" in call_args
        assert "has_sufficient_data" in call_args
        assert "statistics" in call_args
    
    @pytest.mark.asyncio
    async def test_offset_engine_load_learning_data_restores_learner_state(self):
        """Test loading learning data into OffsetEngine."""
        config = {"max_offset": 5.0, "enable_learning": True}
        engine = OffsetEngine(config)
        
        # Mock data store with saved data
        mock_store = Mock()
        saved_data = {
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
                }
            ],
            "has_sufficient_data": False,
            "statistics": {
                "samples": 1,
                "accuracy": 0.8,
                "mean_error": 0.2
            }
        }
        mock_store.async_load_learning_data = AsyncMock(return_value=saved_data)
        engine._data_store = mock_store
        
        # Load learning data
        result = await engine.async_load_learning_data()
        
        assert result is True
        # Verify learner state was restored
        assert len(engine._learner._training_samples) == 1
        assert engine._learner._training_samples[0]["predicted"] == 1.0
        assert engine._learner._training_samples[0]["actual"] == 0.8
    
    @pytest.mark.asyncio
    async def test_offset_engine_load_learning_data_handles_missing_data(self):
        """Test loading when no saved data exists."""
        config = {"max_offset": 5.0, "enable_learning": True}
        engine = OffsetEngine(config)
        
        # Mock data store with no saved data
        mock_store = Mock()
        mock_store.async_load_learning_data = AsyncMock(return_value=None)
        engine._data_store = mock_store
        
        # Load learning data
        result = await engine.async_load_learning_data()
        
        assert result is False
        # Verify learner remains in initial state
        assert len(engine._learner._training_samples) == 0
    
    @pytest.mark.asyncio
    async def test_offset_engine_load_learning_data_handles_corrupted_data(self):
        """Test loading corrupted learning data."""
        config = {"max_offset": 5.0, "enable_learning": True}
        engine = OffsetEngine(config)
        
        # Mock data store with corrupted data
        mock_store = Mock()
        corrupted_data = {
            "samples": "invalid",  # Should be a list
            "statistics": None
        }
        mock_store.async_load_learning_data = AsyncMock(return_value=corrupted_data)
        engine._data_store = mock_store
        
        # Load learning data
        with patch("custom_components.smart_climate.offset_engine._LOGGER") as mock_logger:
            result = await engine.async_load_learning_data()
            
            assert result is False
            mock_logger.warning.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_offset_engine_auto_saves_periodically(self):
        """Test automatic periodic saving."""
        config = {"max_offset": 5.0, "enable_learning": True}
        engine = OffsetEngine(config)
        
        # Mock data store
        mock_store = Mock()
        mock_store.async_save_learning_data = AsyncMock()
        engine._data_store = mock_store
        
        # Mock the periodic save setup
        with patch("homeassistant.helpers.event.async_track_time_interval") as mock_track:
            await engine.async_setup_periodic_save()
            
            # Verify periodic save was set up (600 seconds = 10 minutes)
            mock_track.assert_called_once()
            call_args = mock_track.call_args
            assert call_args[0][1] == 600  # 10 minutes
    
    @pytest.mark.asyncio
    async def test_offset_engine_saves_on_learning_state_change(self):
        """Test saving when learning is enabled/disabled."""
        config = {"max_offset": 5.0, "enable_learning": False}
        engine = OffsetEngine(config)
        
        # Mock data store
        mock_store = Mock()
        mock_store.async_save_learning_data = AsyncMock()
        engine._data_store = mock_store
        
        # Enable learning (should trigger save)
        engine.enable_learning()
        
        # Wait for callback execution
        await engine._trigger_save_callback()
        
        # Verify save was called
        mock_store.async_save_learning_data.assert_called_once()


class TestPersistenceIntegration:
    """Test complete persistence integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_multiple_entities_get_separate_files(self):
        """Test that multiple climate entities get separate data files."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        
        store1 = SmartClimateDataStore(hass, "climate.living_room")
        store2 = SmartClimateDataStore(hass, "climate.bedroom")
        
        path1 = store1.get_data_file_path()
        path2 = store2.get_data_file_path()
        
        assert path1 != path2
        assert "climate_living_room" in path1.name
        assert "climate_bedroom" in path2.name
    
    @pytest.mark.asyncio
    async def test_data_persistence_survives_restart_simulation(self):
        """Test full restart simulation with data persistence."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        
        # Create temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            hass.config.config_dir = temp_dir
            
            # Phase 1: Create engine and record learning data
            config = {"max_offset": 5.0, "enable_learning": True}
            engine1 = OffsetEngine(config)
            
            # Initialize data store
            store = SmartClimateDataStore(hass, "climate.test")
            engine1._data_store = store
            
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
            
            engine1.record_actual_performance(1.0, 0.8, input_data)
            
            # Save learning data
            await engine1.async_save_learning_data()
            
            # Verify file was created
            data_file = store.get_data_file_path()
            assert data_file.exists()
            
            # Phase 2: Simulate restart - create new engine and load data
            engine2 = OffsetEngine(config)
            store2 = SmartClimateDataStore(hass, "climate.test")
            engine2._data_store = store2
            
            # Load learning data
            result = await engine2.async_load_learning_data()
            
            # Verify data was restored
            assert result is True
            assert len(engine2._learner._training_samples) == 1
            assert engine2._learner._training_samples[0]["predicted"] == 1.0
            assert engine2._learner._training_samples[0]["actual"] == 0.8
    
    @pytest.mark.asyncio
    async def test_performance_requirements_met(self):
        """Test that performance requirements are met."""
        import time
        
        hass = Mock()
        hass.config.config_dir = "/test/config"
        
        # Create data store with large dataset
        store = SmartClimateDataStore(hass, "climate.test")
        
        # Generate large learning dataset
        large_dataset = {
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
                } for _ in range(1000)  # 1000 samples
            ],
            "statistics": {"samples": 1000, "accuracy": 0.8}
        }
        
        # Test save performance
        start_time = time.time()
        with patch("pathlib.Path.mkdir"), \
             patch("builtins.open", create=True), \
             patch("json.dump"), \
             patch("pathlib.Path.rename"):
            await store.async_save_learning_data(large_dataset)
        save_time = time.time() - start_time
        
        # Test load performance
        start_time = time.time()
        with patch("pathlib.Path.exists", return_value=True), \
             patch("builtins.open", create=True), \
             patch("json.load", return_value={
                 "version": "1.0",
                 "entity_id": "climate.test",
                 "learning_data": large_dataset
             }):
            await store.async_load_learning_data()
        load_time = time.time() - start_time
        
        # Performance requirements: non-blocking operations
        assert save_time < 1.0  # Should complete within 1 second
        assert load_time < 1.0   # Should complete within 1 second