"""Tests for missing methods in seasonal learner and data store."""

import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from custom_components.smart_climate.seasonal_learner import SeasonalHysteresisLearner
from custom_components.smart_climate.data_store import SmartClimateDataStore


class TestSeasonalHysteresisLearnerMissingMethods:
    """Test missing methods in SeasonalHysteresisLearner."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = Mock()
        hass.states = Mock()
        hass.data = {}
        return hass

    @pytest.fixture
    def learner(self, mock_hass):
        """Create a SeasonalHysteresisLearner instance."""
        # Mock the Store to avoid storage issues in tests
        with patch('custom_components.smart_climate.seasonal_learner.Store') as mock_store:
            mock_store.return_value = Mock()
            return SeasonalHysteresisLearner(mock_hass, "sensor.outdoor_temp")

    def test_get_accuracy_method_exists(self, learner):
        """Test that get_accuracy method exists."""
        assert hasattr(learner, 'get_accuracy')
        assert callable(learner.get_accuracy)

    def test_get_accuracy_returns_float(self, learner):
        """Test that get_accuracy returns a float."""
        result = learner.get_accuracy()
        assert isinstance(result, float)
        assert 0.0 <= result <= 100.0

    def test_get_accuracy_wraps_get_seasonal_accuracy(self, learner):
        """Test that get_accuracy wraps get_seasonal_accuracy."""
        # Mock the get_seasonal_accuracy method
        learner.get_seasonal_accuracy = Mock(return_value=85.5)
        
        result = learner.get_accuracy()
        
        assert result == 85.5
        learner.get_seasonal_accuracy.assert_called_once()

    def test_get_accuracy_handles_exceptions(self, learner):
        """Test that get_accuracy handles exceptions gracefully."""
        # Mock get_seasonal_accuracy to raise exception
        learner.get_seasonal_accuracy = Mock(side_effect=Exception("Test error"))
        
        result = learner.get_accuracy()
        
        assert result == 0.0


class TestSmartClimateDataStoreMissingMethods:
    """Test missing methods in SmartClimateDataStore."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = Mock()
        hass.config = Mock()
        hass.config.config_dir = "/tmp/test_config"
        hass.async_add_executor_job = AsyncMock()
        return hass

    @pytest.fixture
    def data_store(self, mock_hass):
        """Create a SmartClimateDataStore instance."""
        return SmartClimateDataStore(mock_hass, "climate.test_entity")

    def test_get_last_write_latency_method_exists(self, data_store):
        """Test that get_last_write_latency method exists."""
        assert hasattr(data_store, 'get_last_write_latency')
        assert callable(data_store.get_last_write_latency)

    def test_get_last_write_latency_returns_float(self, data_store):
        """Test that get_last_write_latency returns a float."""
        result = data_store.get_last_write_latency()
        assert isinstance(result, float)
        assert result >= 0.0

    def test_get_last_write_latency_default_value(self, data_store):
        """Test that get_last_write_latency returns 0.0 by default."""
        result = data_store.get_last_write_latency()
        assert result == 0.0

    def test_get_last_write_latency_after_save(self, data_store):
        """Test that get_last_write_latency returns measured latency after save."""
        # Set a mock latency value
        data_store._last_write_latency_ms = 5.2
        
        result = data_store.get_last_write_latency()
        
        assert result == 5.2

    @pytest.mark.asyncio
    async def test_save_learning_data_tracks_latency(self, data_store):
        """Test that async_save_learning_data tracks write latency."""
        # Mock the file operations to be instant
        data_store._ensure_data_directory = Mock()
        data_store._create_backup_if_needed = Mock()
        data_store._validate_json_file = Mock(return_value=True)
        
        # Mock the atomic write and rename operations
        with patch('custom_components.smart_climate.data_store.atomic_json_write') as mock_write, \
             patch('pathlib.Path.rename') as mock_rename, \
             patch('pathlib.Path.stat') as mock_stat:
            
            mock_stat.return_value.st_size = 1024
            
            # Add some delay to the write operation
            def slow_write(*args, **kwargs):
                time.sleep(0.01)  # 10ms delay
                
            mock_write.side_effect = slow_write
            
            # Call the save method
            await data_store.async_save_learning_data({"test": "data"})
            
            # Check that latency was tracked
            latency = data_store.get_last_write_latency()
            assert latency > 0.0
            assert latency < 100.0  # Should be reasonable (< 100ms)

    @pytest.mark.asyncio
    async def test_save_learning_data_error_handling(self, data_store):
        """Test that write errors are handled gracefully."""
        # Set initial latency  
        initial_latency = data_store.get_last_write_latency()
        
        # Mock the atomic_json_write function to fail
        with patch('custom_components.smart_climate.data_store.atomic_json_write') as mock_write:
            mock_write.side_effect = Exception("Test error")
            
            # Call save method (should handle error gracefully without raising exception)
            await data_store.async_save_learning_data({"test": "data"})
            
            # Should not raise an exception - error is handled gracefully
            # Latency might be updated but method call should succeed
            assert data_store.get_last_write_latency() >= 0.0