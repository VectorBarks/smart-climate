"""Test the learning switch enhancement with technical metrics."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from homeassistant.core import HomeAssistant, State
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_OFF

from custom_components.smart_climate.switch import LearningSwitch
from custom_components.smart_climate.offset_engine import OffsetEngine


class TestLearningSwitchEnhancement:
    """Test suite for learning switch technical metrics enhancement."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = Mock()
        hass.states = Mock()
        return hass

    @pytest.fixture
    def mock_config_entry(self):
        """Create a mock config entry."""
        config_entry = Mock()
        config_entry.title = "Test Climate"
        config_entry.unique_id = "test_unique_id"
        return config_entry

    @pytest.fixture
    def mock_offset_engine(self):
        """Create a mock offset engine."""
        engine = Mock()
        engine.is_learning_enabled = True
        engine.save_count = 5
        engine.failed_save_count = 0
        engine.last_save_time = None
        
        # Mock learning info
        engine.get_learning_info.return_value = {
            "samples": 10,
            "accuracy": 85.5,
            "confidence": 0.75,
            "has_sufficient_data": True,
            "enabled": True,
            "last_sample_time": "2023-07-13T10:30:00",
            "hysteresis_enabled": True,
            "hysteresis_state": "learning_hysteresis",
            "learned_start_threshold": 24.5,
            "learned_stop_threshold": 23.2,
            "temperature_window": 1.3,
            "start_samples_collected": 5,
            "stop_samples_collected": 5,
            "hysteresis_ready": True
        }
        
        # Mock callback registration
        engine.register_update_callback.return_value = Mock()
        
        return engine

    @pytest.fixture
    def learning_switch(self, mock_config_entry, mock_offset_engine):
        """Create a learning switch instance."""
        return LearningSwitch(
            config_entry=mock_config_entry,
            offset_engine=mock_offset_engine,
            climate_name="Test Climate",
            entity_id="climate.test_ac"
        )

    def test_access_climate_entity_success(self, learning_switch, mock_hass):
        """Test successful access to climate entity for technical metrics."""
        # Arrange
        learning_switch.hass = mock_hass
        
        # Create mock climate state with technical metrics
        climate_state = Mock()
        climate_state.attributes = {
            "prediction_latency_ms": 0.5,
            "energy_efficiency_score": 85,
            "memory_usage_kb": 2048.5,
            "seasonal_pattern_count": 15,
            "temperature_window_learned": True,
            "convergence_trend": "improving",
            "outlier_detection_active": True,
            "power_correlation_accuracy": 92.3,
            "hysteresis_cycle_count": 8
        }
        
        mock_hass.states.get.return_value = climate_state
        
        # Act
        climate_metrics = learning_switch._get_climate_technical_metrics()
        
        # Assert
        mock_hass.states.get.assert_called_once_with("climate.test_ac")
        assert climate_metrics["prediction_latency_ms"] == 0.5
        assert climate_metrics["energy_efficiency_score"] == 85
        assert climate_metrics["memory_usage_kb"] == 2048.5
        assert climate_metrics["seasonal_pattern_count"] == 15
        assert climate_metrics["temperature_window_learned"] is True
        assert climate_metrics["convergence_trend"] == "improving"
        assert climate_metrics["outlier_detection_active"] is True
        assert climate_metrics["power_correlation_accuracy"] == 92.3
        assert climate_metrics["hysteresis_cycle_count"] == 8

    def test_access_climate_entity_not_found(self, learning_switch, mock_hass):
        """Test handling when climate entity is not found."""
        # Arrange
        learning_switch.hass = mock_hass
        mock_hass.states.get.return_value = None
        
        # Act
        climate_metrics = learning_switch._get_climate_technical_metrics()
        
        # Assert
        mock_hass.states.get.assert_called_once_with("climate.test_ac")
        # Should return empty dict when entity not found
        assert climate_metrics == {}

    def test_access_climate_entity_missing_attributes(self, learning_switch, mock_hass):
        """Test handling when climate entity has missing technical metrics."""
        # Arrange
        learning_switch.hass = mock_hass
        
        climate_state = Mock()
        climate_state.attributes = {
            "prediction_latency_ms": 1.2,
            # Missing other metrics
        }
        
        mock_hass.states.get.return_value = climate_state
        
        # Act
        climate_metrics = learning_switch._get_climate_technical_metrics()
        
        # Assert
        assert climate_metrics["prediction_latency_ms"] == 1.2
        # Missing metrics should not be in the result
        assert "energy_efficiency_score" not in climate_metrics
        assert "memory_usage_kb" not in climate_metrics

    def test_access_climate_entity_exception_handling(self, learning_switch, mock_hass):
        """Test exception handling during climate entity access."""
        # Arrange
        learning_switch.hass = mock_hass
        mock_hass.states.get.side_effect = Exception("Connection error")
        
        # Act
        climate_metrics = learning_switch._get_climate_technical_metrics()
        
        # Assert
        # Should return empty dict on exception
        assert climate_metrics == {}

    def test_enhanced_extra_state_attributes_with_technical_metrics(self, learning_switch, mock_hass):
        """Test that extra_state_attributes includes technical metrics from climate entity."""
        # Arrange
        learning_switch.hass = mock_hass
        
        # Mock climate entity with technical metrics
        climate_state = Mock()
        climate_state.attributes = {
            "prediction_latency_ms": 0.8,
            "energy_efficiency_score": 92,
            "memory_usage_kb": 1536.2,
            "seasonal_pattern_count": 12,
            "temperature_window_learned": True,
            "convergence_trend": "stable",
            "outlier_detection_active": False,
            "power_correlation_accuracy": 88.7,
            "hysteresis_cycle_count": 6
        }
        mock_hass.states.get.return_value = climate_state
        
        # Act
        attributes = learning_switch.extra_state_attributes
        
        # Assert - should include all existing attributes plus technical metrics
        # Existing attributes
        assert "samples_collected" in attributes
        assert "learning_accuracy" in attributes
        assert "confidence_level" in attributes
        
        # New technical metrics from climate entity
        assert attributes["prediction_latency_ms"] == 0.8
        assert attributes["energy_efficiency_score"] == 92
        assert attributes["memory_usage_kb"] == 1536.2
        assert attributes["seasonal_pattern_count"] == 12
        assert attributes["temperature_window_learned"] is True
        assert attributes["convergence_trend"] == "stable"
        assert attributes["outlier_detection_active"] is False
        assert attributes["power_correlation_accuracy"] == 88.7
        assert attributes["hysteresis_cycle_count"] == 6

    def test_enhanced_extra_state_attributes_fallback_on_climate_failure(self, learning_switch, mock_hass):
        """Test that extra_state_attributes gracefully handles climate entity access failure."""
        # Arrange
        learning_switch.hass = mock_hass
        mock_hass.states.get.return_value = None  # Climate entity not found
        
        # Act
        attributes = learning_switch.extra_state_attributes
        
        # Assert - should include existing attributes but not technical metrics
        assert "samples_collected" in attributes
        assert "learning_accuracy" in attributes
        assert "confidence_level" in attributes
        
        # Technical metrics should not be present
        assert "prediction_latency_ms" not in attributes
        assert "energy_efficiency_score" not in attributes
        assert "memory_usage_kb" not in attributes

    def test_enhanced_extra_state_attributes_preserves_existing_behavior(self, learning_switch, mock_hass):
        """Test that enhancement preserves all existing switch attribute behavior."""
        # Arrange
        learning_switch.hass = mock_hass
        
        # Mock climate entity (can be None to test fallback)
        mock_hass.states.get.return_value = None
        
        # Act
        attributes = learning_switch.extra_state_attributes
        
        # Assert - all existing attributes should still be present
        expected_existing_attributes = [
            "samples_collected",
            "learning_accuracy", 
            "confidence_level",
            "patterns_learned",
            "has_sufficient_data",
            "enabled",
            "last_sample_collected",
            "hysteresis_enabled",
            "hysteresis_state",
            "learned_start_threshold",
            "learned_stop_threshold",
            "temperature_window",
            "start_samples_collected",
            "stop_samples_collected", 
            "hysteresis_ready",
            "save_count",
            "failed_save_count",
            "last_save_time"
        ]
        
        for attr in expected_existing_attributes:
            assert attr in attributes, f"Existing attribute '{attr}' missing from enhanced switch"

    def test_performance_impact_minimal(self, learning_switch, mock_hass):
        """Test that accessing climate metrics has minimal performance impact."""
        # Arrange
        learning_switch.hass = mock_hass
        
        climate_state = Mock()
        climate_state.attributes = {
            "prediction_latency_ms": 0.3,
            "energy_efficiency_score": 88
        }
        mock_hass.states.get.return_value = climate_state
        
        # Act - multiple calls should be efficient
        import time
        start_time = time.time()
        
        for _ in range(10):
            _ = learning_switch.extra_state_attributes
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Assert - should complete quickly (less than 100ms for 10 calls)
        assert total_time < 0.1, f"Performance test failed: {total_time}s for 10 calls"

    def test_integration_with_offset_engine_learning_info(self, learning_switch, mock_hass):
        """Test integration between offset engine learning info and climate technical metrics."""
        # Arrange
        learning_switch.hass = mock_hass
        
        # Set up offset engine learning info
        learning_switch._offset_engine.get_learning_info.return_value = {
            "samples": 25,
            "accuracy": 91.2,
            "confidence": 0.85,
            "enabled": True
        }
        
        # Set up climate technical metrics
        climate_state = Mock()
        climate_state.attributes = {
            "seasonal_pattern_count": 20,
            "convergence_trend": "improving"
        }
        mock_hass.states.get.return_value = climate_state
        
        # Act
        attributes = learning_switch.extra_state_attributes
        
        # Assert - should include both offset engine data and climate metrics
        assert attributes["samples_collected"] == 25
        assert attributes["learning_accuracy"] == 91.2
        assert attributes["confidence_level"] == 0.85
        assert attributes["seasonal_pattern_count"] == 20
        assert attributes["convergence_trend"] == "improving"

    def test_error_recovery_from_partial_climate_data(self, learning_switch, mock_hass):
        """Test error recovery when climate entity has partial or corrupted data."""
        # Arrange
        learning_switch.hass = mock_hass
        
        climate_state = Mock()
        # Simulate corrupted data - some values are wrong types
        climate_state.attributes = {
            "prediction_latency_ms": "invalid_string",
            "energy_efficiency_score": None,
            "memory_usage_kb": 1024.5,  # This one is valid
            "seasonal_pattern_count": "not_a_number"
        }
        mock_hass.states.get.return_value = climate_state
        
        # Act
        climate_metrics = learning_switch._get_climate_technical_metrics()
        
        # Assert - should only include valid data
        assert "memory_usage_kb" in climate_metrics
        assert climate_metrics["memory_usage_kb"] == 1024.5
        # Invalid data should be filtered out
        assert "prediction_latency_ms" not in climate_metrics
        assert "energy_efficiency_score" not in climate_metrics
        assert "seasonal_pattern_count" not in climate_metrics

    def test_backwards_compatibility_without_technical_metrics(self, learning_switch, mock_hass):
        """Test backwards compatibility with climate entities that don't have technical metrics."""
        # Arrange
        learning_switch.hass = mock_hass
        
        # Mock older climate entity without technical metrics
        climate_state = Mock()
        climate_state.attributes = {
            "current_temperature": 23.5,
            "target_temperature": 24.0,
            # No technical metrics
        }
        mock_hass.states.get.return_value = climate_state
        
        # Act
        attributes = learning_switch.extra_state_attributes
        
        # Assert - should work fine, just without technical metrics
        assert "samples_collected" in attributes
        assert "learning_accuracy" in attributes
        # Technical metrics should not be present
        assert "prediction_latency_ms" not in attributes
        assert "energy_efficiency_score" not in attributes

    def test_climate_entity_id_derivation(self, learning_switch):
        """Test that climate entity ID is correctly derived from switch entity ID."""
        # Arrange - switch was created with entity_id="climate.test_ac"
        
        # Act & Assert - the _entity_id should be stored correctly
        assert learning_switch._entity_id == "climate.test_ac"

    def test_selective_metric_inclusion(self, learning_switch, mock_hass):
        """Test that only relevant technical metrics are included, not all climate attributes."""
        # Arrange
        learning_switch.hass = mock_hass
        
        climate_state = Mock()
        climate_state.attributes = {
            # Technical metrics we want
            "prediction_latency_ms": 0.7,
            "energy_efficiency_score": 90,
            
            # Climate attributes we don't want in switch
            "current_temperature": 23.5,
            "target_temperature": 24.0,
            "hvac_mode": "cool",
            "preset_mode": "none",
            
            # More technical metrics we do want
            "seasonal_pattern_count": 8,
            "convergence_trend": "stable"
        }
        mock_hass.states.get.return_value = climate_state
        
        # Act
        attributes = learning_switch.extra_state_attributes
        
        # Assert - should include technical metrics but not regular climate attributes
        assert attributes["prediction_latency_ms"] == 0.7
        assert attributes["energy_efficiency_score"] == 90
        assert attributes["seasonal_pattern_count"] == 8
        assert attributes["convergence_trend"] == "stable"
        
        # Should NOT include regular climate attributes
        assert "current_temperature" not in attributes
        assert "target_temperature" not in attributes
        assert "hvac_mode" not in attributes
        assert "preset_mode" not in attributes

    def test_exception_handling_in_extra_state_attributes(self, learning_switch, mock_hass):
        """Test that exceptions in technical metrics don't break existing functionality."""
        # Arrange
        learning_switch.hass = mock_hass
        
        # Mock climate access to raise exception
        mock_hass.states.get.side_effect = Exception("Climate entity error")
        
        # Act
        attributes = learning_switch.extra_state_attributes
        
        # Assert - should still have existing attributes despite climate access failure
        assert "samples_collected" in attributes
        assert "learning_accuracy" in attributes
        assert "confidence_level" in attributes
        # No technical metrics should be present due to exception
        assert "prediction_latency_ms" not in attributes
        assert "energy_efficiency_score" not in attributes

    def test_missing_hass_attribute_handling(self, learning_switch):
        """Test handling when hass attribute is not yet available on switch."""
        # Arrange - don't set hass attribute on switch
        
        # Act
        climate_metrics = learning_switch._get_climate_technical_metrics()
        
        # Assert - should return empty dict when hass not available
        assert climate_metrics == {}

    def test_get_climate_technical_metrics_method_exists(self, learning_switch):
        """Test that the new _get_climate_technical_metrics method exists and is callable."""
        # Assert
        assert hasattr(learning_switch, '_get_climate_technical_metrics')
        assert callable(getattr(learning_switch, '_get_climate_technical_metrics'))