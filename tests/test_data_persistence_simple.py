"""Simple integration tests for learning data persistence system."""

import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from datetime import datetime, time

from custom_components.smart_climate.data_store import SmartClimateDataStore
from custom_components.smart_climate.offset_engine import OffsetEngine, LightweightOffsetLearner
from custom_components.smart_climate.models import OffsetInput


class TestDataPersistenceIntegration:
    """Test the complete data persistence integration."""
    
    def test_data_store_initialization(self):
        """Test that SmartClimateDataStore initializes correctly."""
        hass = Mock()
        hass.config.config_dir = "/test/config"
        
        store = SmartClimateDataStore(hass, "climate.test_entity")
        
        assert store._entity_id == "climate.test_entity"
        assert "climate_test_entity" in str(store._data_file_path)
        assert store._data_file_path.name.endswith(".json")
    
    def test_offset_engine_has_persistence_methods(self):
        """Test that OffsetEngine has the required persistence methods."""
        config = {"max_offset": 5.0, "enable_learning": True}
        engine = OffsetEngine(config)
        
        # Check that all required methods exist
        assert hasattr(engine, "set_data_store")
        assert hasattr(engine, "async_save_learning_data")
        assert hasattr(engine, "async_load_learning_data")
        assert hasattr(engine, "async_setup_periodic_save")
        assert callable(engine.set_data_store)
        assert callable(engine.async_save_learning_data)
        assert callable(engine.async_load_learning_data)
        assert callable(engine.async_setup_periodic_save)
    
    def test_learner_serialization_methods(self):
        """Test that LightweightOffsetLearner has serialization methods."""
        learner = LightweightOffsetLearner()
        
        # Check serialization methods exist
        assert hasattr(learner, "serialize_for_persistence")
        assert hasattr(learner, "restore_from_persistence")
        assert callable(learner.serialize_for_persistence)
        assert callable(learner.restore_from_persistence)
    
    def test_learner_serialization_basic(self):
        """Test basic serialization and deserialization."""
        learner = LightweightOffsetLearner()
        
        # Add some sample data
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=23.0,
            outdoor_temp=30.0,
            mode="normal",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=0
        )
        
        learner.record_sample(1.0, 0.8, input_data)
        
        # Serialize
        serialized = learner.serialize_for_persistence()
        
        # Verify structure
        assert isinstance(serialized, dict)
        assert "samples" in serialized
        assert "statistics" in serialized
        assert "has_sufficient_data" in serialized
        assert len(serialized["samples"]) == 1
        
        # Test deserialization
        new_learner = LightweightOffsetLearner()
        success = new_learner.restore_from_persistence(serialized)
        
        assert success is True
        assert len(new_learner._training_samples) == 1
        assert new_learner._training_samples[0]["predicted"] == 1.0
        assert new_learner._training_samples[0]["actual"] == 0.8
    
    @pytest.mark.asyncio
    async def test_offset_engine_persistence_integration(self):
        """Test OffsetEngine persistence integration."""
        # Create mock hass
        hass = Mock()
        hass.config.config_dir = "/tmp"
        hass.async_add_executor_job = AsyncMock()
        
        # Create engine with learning enabled
        config = {"max_offset": 5.0, "enable_learning": True}
        engine = OffsetEngine(config)
        
        # Create and set data store
        store = SmartClimateDataStore(hass, "climate.test")
        engine.set_data_store(store)
        
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
        
        # Test save (should not raise exception)
        await engine.async_save_learning_data()
        
        # Verify executor was called
        assert hass.async_add_executor_job.called
    
    @pytest.mark.asyncio
    async def test_offset_engine_load_with_no_data(self):
        """Test loading when no data exists."""
        # Create mock hass
        hass = Mock()
        hass.config.config_dir = "/tmp"
        hass.async_add_executor_job = AsyncMock(return_value=None)  # Simulate no data
        
        # Create engine with learning enabled
        config = {"max_offset": 5.0, "enable_learning": True}
        engine = OffsetEngine(config)
        
        # Create and set data store
        store = SmartClimateDataStore(hass, "climate.test")
        engine.set_data_store(store)
        
        # Test load (should return False for no data)
        result = await engine.async_load_learning_data()
        
        assert result is False
        assert hass.async_add_executor_job.called
    
    @pytest.mark.asyncio 
    async def test_periodic_save_setup(self):
        """Test periodic save setup."""
        # Create mock hass
        hass = Mock()
        hass.config.config_dir = "/tmp"
        
        # Create engine with learning enabled
        config = {"max_offset": 5.0, "enable_learning": True}
        engine = OffsetEngine(config)
        
        # Mock the track_time_interval function
        from unittest.mock import patch
        with patch("homeassistant.helpers.event.async_track_time_interval") as mock_track:
            mock_track.return_value = Mock()  # Mock remove function
            
            # Setup periodic save
            remove_func = await engine.async_setup_periodic_save(hass)
            
            # Verify it was called
            mock_track.assert_called_once()
            
            # Verify the interval is 600 seconds (10 minutes)
            call_args = mock_track.call_args
            assert call_args[0][2].total_seconds() == 600
            
            # Verify we got a removal function
            assert callable(remove_func)
    
    def test_data_store_safe_filename_generation(self):
        """Test that entity IDs are converted to safe filenames."""
        hass = Mock()
        hass.config.config_dir = "/test"
        
        # Test various entity ID formats
        test_cases = [
            ("climate.living_room", "climate_living_room"),
            ("climate.test/entity", "climate_test_entity"),
            ("climate.test-entity.with.dots", "climate_test-entity_with_dots"),
            ("climate.special%chars&here", "climate_special_chars_here")
        ]
        
        for entity_id, expected_safe_part in test_cases:
            store = SmartClimateDataStore(hass, entity_id)
            filename = store._data_file_path.name
            assert expected_safe_part in filename
            assert filename.endswith(".json")
            assert filename.startswith("smart_climate_learning_")


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_learner_handles_invalid_persistence_data(self):
        """Test learner handles corrupted persistence data gracefully."""
        learner = LightweightOffsetLearner()
        
        # Test with invalid data types that should return False
        invalid_data_cases = [
            None,
            "not a dict",
            {"samples": "not a list"},  # Invalid samples
        ]
        
        for invalid_data in invalid_data_cases:
            result = learner.restore_from_persistence(invalid_data)
            # Should fail gracefully and return False
            assert result is False
            # Should not crash and learner should remain in valid state
            assert len(learner._training_samples) == 0
        
        # Test with empty dict (should succeed but with no data)
        result = learner.restore_from_persistence({})
        assert result is True  # Empty dict is valid, just no samples
        assert len(learner._training_samples) == 0
        
        # Test with samples containing invalid entries (should succeed but skip invalid samples)
        result = learner.restore_from_persistence({"samples": [{"invalid": "sample"}]})
        assert result is True  # Should succeed but skip invalid samples
        assert len(learner._training_samples) == 0  # No valid samples
    
    @pytest.mark.asyncio
    async def test_offset_engine_handles_missing_data_store(self):
        """Test OffsetEngine handles missing data store gracefully."""
        config = {"max_offset": 5.0, "enable_learning": True}
        engine = OffsetEngine(config)
        
        # Try to save without setting data store (should not crash)
        await engine.async_save_learning_data()
        
        # Try to load without setting data store (should return False)
        result = await engine.async_load_learning_data()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_offset_engine_handles_learning_disabled(self):
        """Test OffsetEngine handles learning disabled scenario."""
        config = {"max_offset": 5.0, "enable_learning": False}
        engine = OffsetEngine(config)
        
        # Mock hass and data store
        hass = Mock()
        hass.config.config_dir = "/tmp"
        hass.async_add_executor_job = AsyncMock()
        store = SmartClimateDataStore(hass, "climate.test")
        engine.set_data_store(store)
        
        # Try to save (should skip gracefully)
        await engine.async_save_learning_data()
        assert not hass.async_add_executor_job.called
        
        # Try to load (should return False)
        result = await engine.async_load_learning_data()
        assert result is False