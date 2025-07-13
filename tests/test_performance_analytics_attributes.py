"""ABOUTME: Tests for performance analytics attributes in SmartClimateEntity.
Comprehensive test suite covering all Phase 2 performance monitoring attributes."""

import pytest
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import HVACMode
from homeassistant.const import STATE_ON, STATE_OFF, STATE_UNAVAILABLE

from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.models import OffsetResult
from tests.fixtures.mock_entities import (
    create_mock_hass,
    create_mock_state,
    create_mock_offset_engine,
    create_mock_sensor_manager,
    create_mock_mode_manager,
    create_mock_temperature_controller,
    create_mock_coordinator
)


class TestPerformanceAnalyticsAttributes:
    """Test performance analytics attributes implementation."""

    @pytest.fixture
    def smart_climate_entity(self):
        """Create a SmartClimateEntity instance for testing."""
        mock_hass = create_mock_hass()
        config = {
            "name": "Test Smart Climate",
            "update_interval": 180,
            "gradual_adjustment_rate": 0.5
        }
        
        # Create mock dependencies
        mock_offset_engine = create_mock_offset_engine()
        mock_sensor_manager = create_mock_sensor_manager()
        mock_mode_manager = create_mock_mode_manager()
        mock_temperature_controller = create_mock_temperature_controller()
        mock_coordinator = create_mock_coordinator()
        
        # Mock delay learner for timing metrics
        mock_delay_learner = Mock()
        mock_delay_learner.get_adaptive_delay.return_value = 45
        mock_delay_learner.get_learned_delay_seconds.return_value = 42.5
        mock_delay_learner.get_ema_coefficient.return_value = 0.3
        mock_delay_learner._learned_delay_secs = 42.5
        mock_delay_learner.get_temperature_stability_detected.return_value = True
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=config,
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room_temp",
            offset_engine=mock_offset_engine,
            sensor_manager=mock_sensor_manager,
            mode_manager=mock_mode_manager,
            temperature_controller=mock_temperature_controller,
            coordinator=mock_coordinator
        )
        
        # Inject mock delay learner
        entity._delay_learner = mock_delay_learner
        
        return entity

    # Test 1: Temperature Stability Detection
    def test_temperature_stability_detected_attribute_present(self, smart_climate_entity):
        """Test that temperature_stability_detected attribute is present."""
        attributes = smart_climate_entity.extra_state_attributes
        assert "temperature_stability_detected" in attributes
        
    def test_temperature_stability_detected_with_delay_learner(self, smart_climate_entity):
        """Test temperature_stability_detected when DelayLearner is available."""
        # Arrange
        smart_climate_entity._delay_learner.get_temperature_stability_detected.return_value = True
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        assert attributes["temperature_stability_detected"] is True
        smart_climate_entity._delay_learner.get_temperature_stability_detected.assert_called_once()

    def test_temperature_stability_detected_without_delay_learner(self, smart_climate_entity):
        """Test temperature_stability_detected when DelayLearner is not available."""
        # Arrange
        smart_climate_entity._delay_learner = None
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        assert attributes["temperature_stability_detected"] is False

    def test_temperature_stability_detected_with_delay_learner_error(self, smart_climate_entity):
        """Test temperature_stability_detected when DelayLearner raises an exception."""
        # Arrange
        smart_climate_entity._delay_learner.get_temperature_stability_detected.side_effect = Exception("Test error")
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        assert attributes["temperature_stability_detected"] is False

    # Test 2: Learned Delay Seconds
    def test_learned_delay_seconds_attribute_present(self, smart_climate_entity):
        """Test that learned_delay_seconds attribute is present."""
        attributes = smart_climate_entity.extra_state_attributes
        assert "learned_delay_seconds" in attributes
        
    def test_learned_delay_seconds_with_delay_learner(self, smart_climate_entity):
        """Test learned_delay_seconds when DelayLearner is available."""
        # Arrange
        smart_climate_entity._delay_learner.get_learned_delay_seconds.return_value = 42.5
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        assert attributes["learned_delay_seconds"] == 42.5
        smart_climate_entity._delay_learner.get_learned_delay_seconds.assert_called_once()

    def test_learned_delay_seconds_without_delay_learner(self, smart_climate_entity):
        """Test learned_delay_seconds when DelayLearner is not available."""
        # Arrange
        smart_climate_entity._delay_learner = None
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        assert attributes["learned_delay_seconds"] == 0.0

    def test_learned_delay_seconds_with_delay_learner_none_result(self, smart_climate_entity):
        """Test learned_delay_seconds when DelayLearner returns None."""
        # Arrange
        smart_climate_entity._delay_learner.get_learned_delay_seconds.return_value = None
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        assert attributes["learned_delay_seconds"] == 0.0

    def test_learned_delay_seconds_with_delay_learner_error(self, smart_climate_entity):
        """Test learned_delay_seconds when DelayLearner raises an exception."""
        # Arrange
        smart_climate_entity._delay_learner.get_learned_delay_seconds.side_effect = Exception("Test error")
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        assert attributes["learned_delay_seconds"] == 0.0

    # Test 3: EMA Coefficient
    def test_ema_coefficient_attribute_present(self, smart_climate_entity):
        """Test that ema_coefficient attribute is present."""
        attributes = smart_climate_entity.extra_state_attributes
        assert "ema_coefficient" in attributes
        
    def test_ema_coefficient_with_delay_learner(self, smart_climate_entity):
        """Test ema_coefficient when DelayLearner is available."""
        # Arrange
        smart_climate_entity._delay_learner.get_ema_coefficient.return_value = 0.3
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        assert attributes["ema_coefficient"] == 0.3
        smart_climate_entity._delay_learner.get_ema_coefficient.assert_called_once()

    def test_ema_coefficient_without_delay_learner(self, smart_climate_entity):
        """Test ema_coefficient when DelayLearner is not available."""
        # Arrange
        smart_climate_entity._delay_learner = None
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        assert attributes["ema_coefficient"] == 0.2  # Default value

    def test_ema_coefficient_bounds_validation(self, smart_climate_entity):
        """Test that ema_coefficient is properly bounded between 0.0 and 1.0."""
        # Test values outside bounds
        test_values = [-0.1, 1.1, 1.5, -1.0]
        for test_value in test_values:
            smart_climate_entity._delay_learner.get_ema_coefficient.return_value = test_value
            attributes = smart_climate_entity.extra_state_attributes
            assert 0.0 <= attributes["ema_coefficient"] <= 1.0

    def test_ema_coefficient_with_delay_learner_error(self, smart_climate_entity):
        """Test ema_coefficient when DelayLearner raises an exception."""
        # Arrange
        smart_climate_entity._delay_learner.get_ema_coefficient.side_effect = Exception("Test error")
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        assert attributes["ema_coefficient"] == 0.2  # Default value

    # Test 4: Prediction Latency
    def test_prediction_latency_ms_attribute_present(self, smart_climate_entity):
        """Test that prediction_latency_ms attribute is present."""
        attributes = smart_climate_entity.extra_state_attributes
        assert "prediction_latency_ms" in attributes

    @patch('time.perf_counter')
    def test_prediction_latency_ms_measurement(self, mock_perf_counter, smart_climate_entity):
        """Test that prediction_latency_ms correctly measures ML prediction timing."""
        # Arrange - simulate timing measurement
        mock_perf_counter.side_effect = [1000.0, 1000.0025]  # 2.5ms difference
        
        # Mock offset engine with timing measurement
        smart_climate_entity._offset_engine.calculate_offset.side_effect = lambda x: time.sleep(0.001) or OffsetResult(
            offset=1.5, clamped=False, reason="Test", confidence=0.8
        )
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        assert "prediction_latency_ms" in attributes
        assert isinstance(attributes["prediction_latency_ms"], float)
        assert attributes["prediction_latency_ms"] >= 0.0

    def test_prediction_latency_ms_without_recent_calculation(self, smart_climate_entity):
        """Test prediction_latency_ms when no recent calculation available."""
        # Arrange - no recent calculation
        smart_climate_entity._last_prediction_latency_ms = None
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        assert attributes["prediction_latency_ms"] == 0.0

    def test_prediction_latency_ms_caching(self, smart_climate_entity):
        """Test that prediction_latency_ms is cached and not recalculated on every access."""
        # Arrange
        smart_climate_entity._last_prediction_latency_ms = 1.5
        
        # Act - call multiple times
        attributes1 = smart_climate_entity.extra_state_attributes
        attributes2 = smart_climate_entity.extra_state_attributes
        
        # Assert - same value returned
        assert attributes1["prediction_latency_ms"] == 1.5
        assert attributes2["prediction_latency_ms"] == 1.5

    # Test 5: Energy Efficiency Score
    def test_energy_efficiency_score_attribute_present(self, smart_climate_entity):
        """Test that energy_efficiency_score attribute is present."""
        attributes = smart_climate_entity.extra_state_attributes
        assert "energy_efficiency_score" in attributes

    def test_energy_efficiency_score_calculation_with_good_accuracy(self, smart_climate_entity):
        """Test energy efficiency score calculation with good accuracy."""
        # Arrange - mock high accuracy and low offset variance
        mock_result = OffsetResult(offset=0.5, clamped=False, reason="Test", confidence=0.9)
        smart_climate_entity._offset_engine.calculate_offset.return_value = mock_result
        smart_climate_entity._offset_engine.get_confidence_level.return_value = 0.9
        smart_climate_entity._offset_engine.get_recent_offset_variance.return_value = 0.2
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        score = attributes["energy_efficiency_score"]
        assert isinstance(score, int)
        assert 0 <= score <= 100
        assert score >= 70  # Should be high with good accuracy and low variance

    def test_energy_efficiency_score_calculation_with_poor_accuracy(self, smart_climate_entity):
        """Test energy efficiency score calculation with poor accuracy."""
        # Arrange - mock low accuracy and high offset variance
        mock_result = OffsetResult(offset=3.0, clamped=True, reason="Test", confidence=0.2)
        smart_climate_entity._offset_engine.calculate_offset.return_value = mock_result
        smart_climate_entity._offset_engine.get_confidence_level.return_value = 0.2
        smart_climate_entity._offset_engine.get_recent_offset_variance.return_value = 2.5
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        score = attributes["energy_efficiency_score"]
        assert isinstance(score, int)
        assert 0 <= score <= 100
        assert score <= 40  # Should be low with poor accuracy and high variance

    def test_energy_efficiency_score_with_offset_engine_error(self, smart_climate_entity):
        """Test energy efficiency score when offset engine raises an exception."""
        # Arrange
        smart_climate_entity._offset_engine.get_confidence_level.side_effect = Exception("Test error")
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        assert attributes["energy_efficiency_score"] == 50  # Default/fallback value

    def test_energy_efficiency_score_bounds(self, smart_climate_entity):
        """Test that energy efficiency score is always within valid bounds."""
        # Test with various extreme values
        test_cases = [
            (0.0, 10.0),  # Very low confidence, high variance
            (1.0, 0.0),   # Perfect confidence, no variance
            (0.5, 1.0),   # Medium confidence, medium variance
        ]
        
        for confidence, variance in test_cases:
            smart_climate_entity._offset_engine.get_confidence_level.return_value = confidence
            smart_climate_entity._offset_engine.get_recent_offset_variance.return_value = variance
            
            attributes = smart_climate_entity.extra_state_attributes
            score = attributes["energy_efficiency_score"]
            assert 0 <= score <= 100

    # Test 6: Sensor Availability Score
    def test_sensor_availability_score_attribute_present(self, smart_climate_entity):
        """Test that sensor_availability_score attribute is present."""
        attributes = smart_climate_entity.extra_state_attributes
        assert "sensor_availability_score" in attributes

    def test_sensor_availability_score_all_sensors_available(self, smart_climate_entity):
        """Test sensor availability score when all sensors are available."""
        # Arrange - all sensors available
        smart_climate_entity._sensor_manager.get_room_temperature.return_value = 25.0
        smart_climate_entity._sensor_manager.get_outdoor_temperature.return_value = 30.0
        smart_climate_entity._sensor_manager.get_power_consumption.return_value = 1500.0
        smart_climate_entity._sensor_manager.get_sensor_availability_stats.return_value = {
            'room_sensor_uptime': 100.0,
            'outdoor_sensor_uptime': 100.0,
            'power_sensor_uptime': 100.0,
            'total_uptime': 100.0
        }
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        assert attributes["sensor_availability_score"] == 100.0

    def test_sensor_availability_score_partial_availability(self, smart_climate_entity):
        """Test sensor availability score with partial sensor availability."""
        # Arrange - mixed availability
        smart_climate_entity._sensor_manager.get_room_temperature.return_value = 25.0
        smart_climate_entity._sensor_manager.get_outdoor_temperature.return_value = None
        smart_climate_entity._sensor_manager.get_power_consumption.return_value = 1500.0
        smart_climate_entity._sensor_manager.get_sensor_availability_stats.return_value = {
            'room_sensor_uptime': 100.0,
            'outdoor_sensor_uptime': 0.0,
            'power_sensor_uptime': 85.0,
            'total_uptime': 61.7  # Weighted average
        }
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        score = attributes["sensor_availability_score"]
        assert isinstance(score, float)
        assert 0.0 <= score <= 100.0
        assert 60.0 <= score <= 65.0  # Should be around 61.7

    def test_sensor_availability_score_no_sensors(self, smart_climate_entity):
        """Test sensor availability score when no sensors are available."""
        # Arrange - no sensors available
        smart_climate_entity._sensor_manager.get_room_temperature.return_value = None
        smart_climate_entity._sensor_manager.get_outdoor_temperature.return_value = None
        smart_climate_entity._sensor_manager.get_power_consumption.return_value = None
        smart_climate_entity._sensor_manager.get_sensor_availability_stats.return_value = {
            'room_sensor_uptime': 0.0,
            'outdoor_sensor_uptime': 0.0,
            'power_sensor_uptime': 0.0,
            'total_uptime': 0.0
        }
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        assert attributes["sensor_availability_score"] == 0.0

    def test_sensor_availability_score_with_sensor_manager_error(self, smart_climate_entity):
        """Test sensor availability score when sensor manager raises an exception."""
        # Arrange
        smart_climate_entity._sensor_manager.get_sensor_availability_stats.side_effect = Exception("Test error")
        # Also make sensor readings fail to test complete fallback
        smart_climate_entity._sensor_manager.get_room_temperature.return_value = None
        smart_climate_entity._sensor_manager.get_outdoor_temperature.return_value = None
        smart_climate_entity._sensor_manager.get_power_consumption.return_value = None
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        assert attributes["sensor_availability_score"] == 0.0  # Default/fallback value

    # Integration Tests
    def test_all_performance_attributes_present(self, smart_climate_entity):
        """Test that all required performance attributes are present in extra_state_attributes."""
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert - all required attributes present
        required_attributes = [
            "temperature_stability_detected",
            "learned_delay_seconds", 
            "ema_coefficient",
            "prediction_latency_ms",
            "energy_efficiency_score",
            "sensor_availability_score"
        ]
        
        for attr in required_attributes:
            assert attr in attributes, f"Required attribute '{attr}' missing from extra_state_attributes"

    def test_performance_attributes_types(self, smart_climate_entity):
        """Test that performance attributes have correct data types."""
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert - correct types
        assert isinstance(attributes["temperature_stability_detected"], bool)
        assert isinstance(attributes["learned_delay_seconds"], (int, float))
        assert isinstance(attributes["ema_coefficient"], (int, float))
        assert isinstance(attributes["prediction_latency_ms"], (int, float))
        assert isinstance(attributes["energy_efficiency_score"], int)
        assert isinstance(attributes["sensor_availability_score"], (int, float))

    def test_performance_attributes_ranges(self, smart_climate_entity):
        """Test that performance attributes are within expected ranges."""
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert - valid ranges
        assert attributes["learned_delay_seconds"] >= 0.0
        assert 0.0 <= attributes["ema_coefficient"] <= 1.0
        assert attributes["prediction_latency_ms"] >= 0.0
        assert 0 <= attributes["energy_efficiency_score"] <= 100
        assert 0.0 <= attributes["sensor_availability_score"] <= 100.0

    def test_performance_attributes_caching_efficiency(self, smart_climate_entity):
        """Test that expensive calculations are cached for performance."""
        # Arrange - setup mocks to track call counts
        smart_climate_entity._offset_engine.get_confidence_level = Mock(return_value=0.8)
        smart_climate_entity._sensor_manager.get_sensor_availability_stats = Mock(return_value={
            'total_uptime': 95.0
        })
        
        # Act - call multiple times quickly
        attributes1 = smart_climate_entity.extra_state_attributes
        attributes2 = smart_climate_entity.extra_state_attributes
        attributes3 = smart_climate_entity.extra_state_attributes
        
        # Assert - expensive calculations should be cached
        # Efficiency score calculation should not be called multiple times
        assert smart_climate_entity._offset_engine.get_confidence_level.call_count <= 1
        assert smart_climate_entity._sensor_manager.get_sensor_availability_stats.call_count <= 1

    def test_performance_attributes_with_existing_attributes(self, smart_climate_entity):
        """Test that performance attributes are added to existing attributes without conflict."""
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert - existing attributes still present
        assert "reactive_offset" in attributes
        assert "predictive_offset" in attributes 
        assert "total_offset" in attributes
        assert "predictive_strategy" in attributes
        
        # Assert - new performance attributes also present
        assert "temperature_stability_detected" in attributes
        assert "energy_efficiency_score" in attributes

    def test_performance_attributes_resilience_to_component_failures(self, smart_climate_entity):
        """Test that performance attributes gracefully handle component failures."""
        # Arrange - simulate various component failures
        smart_climate_entity._delay_learner = None
        smart_climate_entity._offset_engine.get_confidence_level.side_effect = Exception("Engine error")
        smart_climate_entity._sensor_manager.get_sensor_availability_stats.side_effect = Exception("Sensor error")
        # Also make sensor readings fail to test complete fallback
        smart_climate_entity._sensor_manager.get_room_temperature.return_value = None
        smart_climate_entity._sensor_manager.get_outdoor_temperature.return_value = None
        smart_climate_entity._sensor_manager.get_power_consumption.return_value = None
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert - should not raise exception and return fallback values
        assert attributes["temperature_stability_detected"] is False
        assert attributes["learned_delay_seconds"] == 0.0
        assert attributes["ema_coefficient"] == 0.2
        assert attributes["energy_efficiency_score"] == 50
        assert attributes["sensor_availability_score"] == 0.0