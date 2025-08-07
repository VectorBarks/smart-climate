"""Tests for system health analytics attributes in SmartClimateEntity.

This test suite validates the implementation of system monitoring and health 
attributes that provide visibility into resource usage, performance, and 
learning analytics for dashboard visualization.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from homeassistant.core import HomeAssistant

from custom_components.smart_climate.climate import SmartClimateEntity
from tests.fixtures.mock_entities import (
    create_mock_hass,
    create_mock_offset_engine,
    create_mock_sensor_manager,
    create_mock_mode_manager,
    create_mock_temperature_controller,
    create_mock_coordinator,
)


class TestSystemHealthAnalytics:
    """Test system health analytics attributes."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_hass = create_mock_hass()
        self.config = {
            "name": "Test Smart Climate",
            "climate_entity": "climate.test",
            "room_sensor": "sensor.room_temp",
        }
        
        # Create mock dependencies
        self.mock_offset_engine = create_mock_offset_engine()
        self.mock_sensor_manager = create_mock_sensor_manager()
        self.mock_mode_manager = create_mock_mode_manager()
        self.mock_temperature_controller = create_mock_temperature_controller()
        self.mock_coordinator = create_mock_coordinator()
        
        # Create entity instance
        self.entity = SmartClimateEntity(
            hass=self.mock_hass,
            config=self.config,
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room_temp",
            offset_engine=self.mock_offset_engine,
            sensor_manager=self.mock_sensor_manager,
            mode_manager=self.mock_mode_manager,
            temperature_controller=self.mock_temperature_controller,
            coordinator=self.mock_coordinator,
        )

    def test_memory_usage_kb_available_in_attributes(self):
        """Test that memory_usage_kb is available in extra_state_attributes."""
        # Act
        attributes = self.entity.extra_state_attributes
        
        # Assert
        assert "memory_usage_kb" in attributes
        assert isinstance(attributes["memory_usage_kb"], (int, float))
        assert attributes["memory_usage_kb"] >= 0

    def test_persistence_latency_ms_available_in_attributes(self):
        """Test that persistence_latency_ms is available in extra_state_attributes."""
        # Act
        attributes = self.entity.extra_state_attributes
        
        # Assert
        assert "persistence_latency_ms" in attributes
        assert isinstance(attributes["persistence_latency_ms"], (int, float))
        assert attributes["persistence_latency_ms"] >= 0

    def test_outlier_detection_active_available_in_attributes(self):
        """Test that outlier_detection_active is available in extra_state_attributes."""
        # Act
        attributes = self.entity.extra_state_attributes
        
        # Assert
        assert "outlier_detection_active" in attributes
        # Should be boolean False since offset engine has no outlier detection methods by default
        assert attributes["outlier_detection_active"] is False

    def test_samples_per_day_available_in_attributes(self):
        """Test that samples_per_day is available in extra_state_attributes."""
        # Act
        attributes = self.entity.extra_state_attributes
        
        # Assert
        assert "samples_per_day" in attributes
        assert isinstance(attributes["samples_per_day"], (int, float))
        assert attributes["samples_per_day"] >= 0

    def test_accuracy_improvement_rate_available_in_attributes(self):
        """Test that accuracy_improvement_rate is available in extra_state_attributes."""
        # Act
        attributes = self.entity.extra_state_attributes
        
        # Assert
        assert "accuracy_improvement_rate" in attributes
        assert isinstance(attributes["accuracy_improvement_rate"], (int, float))
        assert -100 <= attributes["accuracy_improvement_rate"] <= 100

    def test_convergence_trend_available_in_attributes(self):
        """Test that convergence_trend is available in extra_state_attributes."""
        # Arrange - set up a proper mock for _analyze_convergence_trend
        self.mock_offset_engine._analyze_convergence_trend = Mock(return_value="stable")
        
        # Act
        attributes = self.entity.extra_state_attributes
        
        # Assert
        assert "convergence_trend" in attributes
        assert isinstance(attributes["convergence_trend"], str)
        assert attributes["convergence_trend"] in [
            "improving", "stable", "declining", "unknown"
        ]

    @patch('psutil.Process')
    def test_memory_usage_calculation_with_psutil(self, mock_process_class):
        """Test memory usage calculation using psutil."""
        # Arrange
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 12345678  # 12 MB in bytes
        mock_process.memory_info.return_value = mock_memory_info
        mock_process_class.return_value = mock_process
        
        # Act
        memory_kb = self.entity._get_memory_usage_kb()
        
        # Assert
        expected_kb = 12345678 / 1024  # Convert bytes to KB
        assert memory_kb == pytest.approx(expected_kb, rel=1e-3)
        mock_process_class.assert_called_once()
        mock_process.memory_info.assert_called_once()

    @patch('psutil.Process')
    def test_memory_usage_error_handling(self, mock_process_class):
        """Test memory usage error handling when psutil fails."""
        # Arrange
        mock_process_class.side_effect = Exception("psutil error")
        
        # Act
        memory_kb = self.entity._get_memory_usage_kb()
        
        # Assert
        assert memory_kb == 0.0
        mock_process_class.assert_called_once()

    def test_persistence_latency_measurement(self):
        """Test persistence latency measurement."""
        # Arrange
        start_time = time.time()
        
        # Mock data store operations
        self.mock_offset_engine.data_store = Mock()
        self.mock_offset_engine.data_store.save_data = Mock()
        
        # Act
        latency_ms = self.entity._measure_persistence_latency_ms()
        
        # Assert
        assert isinstance(latency_ms, (int, float))
        assert latency_ms >= 0
        # Should be reasonable latency (under 1 second for mocked operation)
        assert latency_ms < 1000

    def test_persistence_latency_error_handling(self):
        """Test persistence latency error handling."""
        # Arrange
        self.mock_offset_engine.data_store = None
        
        # Act
        latency_ms = self.entity._measure_persistence_latency_ms()
        
        # Assert
        assert latency_ms == 0.0

    def test_outlier_detection_status_when_enabled(self):
        """Test outlier detection status when enabled."""
        # Arrange
        self.mock_offset_engine.has_outlier_detection = Mock(return_value=True)
        self.mock_offset_engine.is_outlier_detection_active = Mock(return_value=True)
        
        # Act
        is_active = self.entity._get_outlier_detection_active()
        
        # Assert
        assert is_active is True

    def test_outlier_detection_status_when_disabled(self):
        """Test outlier detection status when disabled."""
        # Arrange
        self.mock_offset_engine.has_outlier_detection = Mock(return_value=False)
        
        # Act
        is_active = self.entity._get_outlier_detection_active()
        
        # Assert
        assert is_active is False

    def test_outlier_detection_status_when_not_supported(self):
        """Test outlier detection status when not supported."""
        # Arrange
        # Don't add outlier detection methods to offset engine
        
        # Act
        is_active = self.entity._get_outlier_detection_active()
        
        # Assert
        assert is_active is False

    def test_samples_per_day_calculation(self):
        """Test samples per day calculation."""
        # Arrange
        mock_samples = [
            {"timestamp": time.time() - 86400 + 3600},  # 1 hour ago
            {"timestamp": time.time() - 43200},         # 12 hours ago
            {"timestamp": time.time() - 21600},         # 6 hours ago
        ]
        self.mock_offset_engine.get_recent_samples = Mock(return_value=mock_samples)
        
        # Act
        samples_per_day = self.entity._get_samples_per_day()
        
        # Assert
        assert isinstance(samples_per_day, (int, float))
        assert samples_per_day > 0
        # Should be reasonable rate (we have 3 samples in last 24h)
        assert samples_per_day == 3.0

    def test_samples_per_day_no_samples(self):
        """Test samples per day when no samples available."""
        # Arrange
        self.mock_offset_engine.get_recent_samples = Mock(return_value=[])
        
        # Act
        samples_per_day = self.entity._get_samples_per_day()
        
        # Assert
        assert samples_per_day == 0.0

    def test_samples_per_day_error_handling(self):
        """Test samples per day error handling."""
        # Arrange
        # Don't add get_recent_samples method to offset engine
        
        # Act
        samples_per_day = self.entity._get_samples_per_day()
        
        # Assert
        assert samples_per_day == 0.0

    def test_accuracy_improvement_rate_calculation(self):
        """Test accuracy improvement rate calculation."""
        # Arrange
        # Mock historical accuracy data showing improvement
        mock_accuracy_history = [
            {"timestamp": time.time() - 86400, "accuracy": 0.6},  # 24h ago
            {"timestamp": time.time() - 43200, "accuracy": 0.7},  # 12h ago  
            {"timestamp": time.time() - 21600, "accuracy": 0.8},  # 6h ago
            {"timestamp": time.time() - 3600, "accuracy": 0.85},  # 1h ago
        ]
        self.mock_offset_engine.get_accuracy_history = Mock(return_value=mock_accuracy_history)
        
        # Act
        improvement_rate = self.entity._get_accuracy_improvement_rate()
        
        # Assert
        assert isinstance(improvement_rate, (int, float))
        # Should show positive improvement (from 0.6 to 0.85 = 25% improvement)
        assert improvement_rate > 0
        assert improvement_rate <= 100

    def test_accuracy_improvement_rate_declining(self):
        """Test accuracy improvement rate when accuracy is declining."""
        # Arrange
        # Mock historical accuracy data showing decline
        mock_accuracy_history = [
            {"timestamp": time.time() - 86400, "accuracy": 0.9},  # 24h ago
            {"timestamp": time.time() - 43200, "accuracy": 0.8},  # 12h ago
            {"timestamp": time.time() - 21600, "accuracy": 0.7},  # 6h ago
            {"timestamp": time.time() - 3600, "accuracy": 0.6},   # 1h ago
        ]
        self.mock_offset_engine.get_accuracy_history = Mock(return_value=mock_accuracy_history)
        
        # Act
        improvement_rate = self.entity._get_accuracy_improvement_rate()
        
        # Assert
        assert isinstance(improvement_rate, (int, float))
        # Should show negative improvement (decline)
        assert improvement_rate < 0
        assert improvement_rate >= -100

    def test_accuracy_improvement_rate_insufficient_data(self):
        """Test accuracy improvement rate with insufficient data."""
        # Arrange
        mock_accuracy_history = [
            {"timestamp": time.time() - 3600, "accuracy": 0.8},  # Only 1 sample
        ]
        self.mock_offset_engine.get_accuracy_history = Mock(return_value=mock_accuracy_history)
        
        # Act
        improvement_rate = self.entity._get_accuracy_improvement_rate()
        
        # Assert
        assert improvement_rate == 0.0

    def test_accuracy_improvement_rate_error_handling(self):
        """Test accuracy improvement rate error handling."""
        # Arrange
        # Don't add get_accuracy_history method to offset engine
        
        # Act
        improvement_rate = self.entity._get_accuracy_improvement_rate()
        
        # Assert
        assert improvement_rate == 0.0

    def test_convergence_trend_improving(self):
        """Test convergence trend when learning is improving."""
        # Arrange
        # Mock the offset engine's _analyze_convergence_trend method
        self.mock_offset_engine._analyze_convergence_trend = Mock(return_value="improving")
        
        # Act
        trend = self.entity._get_convergence_trend()
        
        # Assert
        assert trend == "improving"

    def test_convergence_trend_stable(self):
        """Test convergence trend when learning is stable."""
        # Arrange
        # Mock the offset engine's _analyze_convergence_trend method
        self.mock_offset_engine._analyze_convergence_trend = Mock(return_value="stable")
        
        # Act
        trend = self.entity._get_convergence_trend()
        
        # Assert
        assert trend == "stable"

    def test_convergence_trend_declining(self):
        """Test convergence trend when learning is declining."""
        # Arrange
        # Mock the offset engine's _analyze_convergence_trend method
        self.mock_offset_engine._analyze_convergence_trend = Mock(return_value="declining")
        
        # Act
        trend = self.entity._get_convergence_trend()
        
        # Assert
        assert trend == "declining"

    def test_convergence_trend_insufficient_data(self):
        """Test convergence trend with insufficient data."""
        # Arrange
        # Mock the offset engine's _analyze_convergence_trend method returning unknown
        self.mock_offset_engine._analyze_convergence_trend = Mock(return_value="unknown")
        
        # Act
        trend = self.entity._get_convergence_trend()
        
        # Assert
        assert trend == "unknown"

    def test_convergence_trend_error_handling(self):
        """Test convergence trend error handling."""
        # Arrange
        # Remove the _analyze_convergence_trend method from offset engine
        if hasattr(self.mock_offset_engine, '_analyze_convergence_trend'):
            delattr(self.mock_offset_engine, '_analyze_convergence_trend')
        
        # Act
        trend = self.entity._get_convergence_trend()
        
        # Assert
        assert trend == "unknown"

    def test_system_health_attributes_integration(self):
        """Test integration of all system health attributes in extra_state_attributes."""
        # Arrange
        with patch('psutil.Process') as mock_process_class:
            mock_process = Mock()
            mock_memory_info = Mock()
            mock_memory_info.rss = 10485760  # 10 MB
            mock_process.memory_info.return_value = mock_memory_info
            mock_process_class.return_value = mock_process
            
            # Create a clean mock offset engine for this test
            clean_offset_engine = Mock()
            clean_offset_engine.data_store = Mock()
            clean_offset_engine.has_outlier_detection = Mock(return_value=True)
            clean_offset_engine.is_outlier_detection_active = Mock(return_value=True)
            clean_offset_engine.get_recent_samples = Mock(return_value=[
                {"timestamp": time.time() - 3600},
                {"timestamp": time.time() - 7200},
            ])
            clean_offset_engine.get_accuracy_history = Mock(return_value=[
                {"timestamp": time.time() - 86400, "accuracy": 0.7},
                {"timestamp": time.time() - 3600, "accuracy": 0.8},
            ])
            clean_offset_engine.get_variance_history = Mock(return_value=[
                {"timestamp": time.time() - 86400, "variance": 2.0},
                {"timestamp": time.time() - 43200, "variance": 1.8},
                {"timestamp": time.time() - 3600, "variance": 1.5},
            ])
            
            # Replace the entity's offset engine for this test
            original_offset_engine = self.entity._offset_engine
            self.entity._offset_engine = clean_offset_engine
            
            try:
                # Act
                attributes = self.entity.extra_state_attributes
            
                # Assert - all Phase 5 attributes present with correct types
                assert isinstance(attributes["memory_usage_kb"], (int, float))
                assert attributes["memory_usage_kb"] == pytest.approx(10240, rel=1e-3)  # 10MB in KB
                
                assert isinstance(attributes["persistence_latency_ms"], (int, float))
                assert attributes["persistence_latency_ms"] >= 0
                
                assert isinstance(attributes["outlier_detection_active"], bool)
                assert attributes["outlier_detection_active"] is True
                
                assert isinstance(attributes["samples_per_day"], (int, float))
                assert attributes["samples_per_day"] == 2.0
                
                assert isinstance(attributes["accuracy_improvement_rate"], (int, float))
                assert attributes["accuracy_improvement_rate"] > 0  # Should show improvement
                
                assert isinstance(attributes["convergence_trend"], str)
                assert attributes["convergence_trend"] == "improving"
            finally:
                # Restore original offset engine
                self.entity._offset_engine = original_offset_engine

    def test_system_health_attributes_error_resilience(self):
        """Test that system health attributes handle errors gracefully."""
        # Arrange - simulate various error conditions
        with patch('psutil.Process', side_effect=Exception("psutil unavailable")):
            # Offset engine missing methods (no get_recent_samples, etc.)
            
            # Act
            attributes = self.entity.extra_state_attributes
        
            # Assert - all attributes present with safe fallback values
            assert attributes["memory_usage_kb"] == 0.0
            # Persistence latency might have small timing overhead, so check it's small
            assert attributes["persistence_latency_ms"] < 1.0  # Less than 1ms is acceptable for mock
            assert attributes["outlier_detection_active"] is False
            assert attributes["samples_per_day"] == 0.0
            assert attributes["accuracy_improvement_rate"] == 0.0
            assert attributes["convergence_trend"] == "unknown"

    def test_system_health_calculation_performance(self):
        """Test that system health calculations are performant."""
        # Arrange
        with patch('psutil.Process') as mock_process_class:
            mock_process = Mock()
            mock_memory_info = Mock()
            mock_memory_info.rss = 10485760
            mock_process.memory_info.return_value = mock_memory_info
            mock_process_class.return_value = mock_process
            
            self.mock_offset_engine.data_store = Mock()
            self.mock_offset_engine.get_recent_samples = Mock(return_value=[])
            self.mock_offset_engine.get_accuracy_history = Mock(return_value=[])
            self.mock_offset_engine.get_variance_history = Mock(return_value=[])
        
            # Act - measure execution time
            start_time = time.time()
            attributes = self.entity.extra_state_attributes
            execution_time = time.time() - start_time
        
            # Assert - should complete quickly (under 100ms)
            assert execution_time < 0.1
            
            # Verify all attributes are calculated
            assert "memory_usage_kb" in attributes
            assert "persistence_latency_ms" in attributes
            assert "outlier_detection_active" in attributes
            assert "samples_per_day" in attributes
            assert "accuracy_improvement_rate" in attributes
            assert "convergence_trend" in attributes

    def test_memory_usage_caching_behavior(self):
        """Test that memory usage is calculated fresh each time (no inappropriate caching)."""
        # Arrange
        with patch('psutil.Process') as mock_process_class:
            mock_process = Mock()
            mock_memory_info1 = Mock()
            mock_memory_info1.rss = 10485760  # 10 MB
            mock_memory_info2 = Mock()
            mock_memory_info2.rss = 20971520  # 20 MB
            
            # First call returns 10MB, second call returns 20MB
            mock_process.memory_info.side_effect = [mock_memory_info1, mock_memory_info2]
            mock_process_class.return_value = mock_process
        
            # Act - call twice
            memory1 = self.entity._get_memory_usage_kb()
            memory2 = self.entity._get_memory_usage_kb()
        
            # Assert - should return different values (no caching)
            assert memory1 == pytest.approx(10240, rel=1e-3)  # 10MB in KB
            assert memory2 == pytest.approx(20480, rel=1e-3)  # 20MB in KB
            assert mock_process.memory_info.call_count == 2