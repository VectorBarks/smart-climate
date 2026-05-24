"""ABOUTME: Comprehensive tests for AC behavior learning attributes in Smart Climate entity.
Tests temperature window learning, power correlation accuracy, and hysteresis cycle counting."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.const import STATE_OFF, STATE_ON

from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.models import OffsetInput, OffsetResult
from tests.fixtures.mock_entities import (
    create_mock_hass,
    create_mock_offset_engine,
    create_mock_sensor_manager,
    create_mock_mode_manager,
    create_mock_temperature_controller,
    create_mock_coordinator,
)


class TestACLearningAttributes:
    """Test AC behavior learning attribute calculations and display."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        return {
            "climate_entity": "climate.test_ac",
            "room_sensor": "sensor.room_temp",
            "outdoor_sensor": "sensor.outdoor_temp",
            "power_sensor": "sensor.ac_power",
            "max_offset": 5.0,
            "update_interval": 180,
        }

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for SmartClimateEntity."""
        offset_engine = create_mock_offset_engine()
        offset_engine._hysteresis_learner = Mock()
        offset_engine._hysteresis_learner.learned_start_threshold = 25.5
        offset_engine._hysteresis_learner.learned_stop_threshold = 23.5
        offset_engine._hysteresis_learner._start_temps = [25.0, 25.5, 26.0, 25.2, 25.8]
        offset_engine._hysteresis_learner._stop_temps = [23.0, 23.5, 24.0, 23.2, 23.8]
        offset_engine._hysteresis_learner.has_sufficient_data = True
        
        return {
            "offset_engine": offset_engine,
            "sensor_manager": create_mock_sensor_manager(),
            "mode_manager": create_mock_mode_manager(),
            "temperature_controller": create_mock_temperature_controller(),
            "coordinator": create_mock_coordinator(),
        }

    @pytest.fixture
    def smart_climate_entity(self, mock_config, mock_dependencies):
        """Create a SmartClimateEntity instance for testing."""
        mock_hass = create_mock_hass()
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=mock_config,
            wrapped_entity_id=mock_config["climate_entity"],
            room_sensor_id=mock_config["room_sensor"],
            **mock_dependencies,
        )
        entity._attr_target_temperature = 24.0
        return entity

    def test_temperature_window_learned_with_sufficient_data(self, smart_climate_entity):
        """Test temperature_window_learned calculation with sufficient hysteresis data."""
        # Arrange
        # Mock data already set in fixture with start_threshold=25.5, stop_threshold=23.5
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        assert "temperature_window_learned" in attributes
        assert attributes["temperature_window_learned"] == "2.0°C"

    def test_temperature_window_learned_insufficient_data(self, smart_climate_entity):
        """Test temperature_window_learned when insufficient hysteresis data available."""
        # Arrange
        smart_climate_entity._offset_engine._hysteresis_learner.has_sufficient_data = False
        smart_climate_entity._offset_engine._hysteresis_learner.learned_start_threshold = None
        smart_climate_entity._offset_engine._hysteresis_learner.learned_stop_threshold = None
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        assert "temperature_window_learned" in attributes
        assert attributes["temperature_window_learned"] == "learning"
        assert "Collecting compressor" in attributes["temperature_window_status_detail"]

    def test_temperature_window_learned_no_hysteresis_learner(self, smart_climate_entity):
        """Test temperature_window_learned when no hysteresis learner available."""
        # Arrange
        smart_climate_entity._offset_engine._hysteresis_learner = None
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        assert "temperature_window_learned" in attributes
        assert attributes["temperature_window_learned"] == "not_available"
        assert attributes["temperature_window_source"] == "offset_engine.hysteresis_learner"

    def test_power_correlation_accuracy_with_power_data(self, smart_climate_entity):
        """Test power_correlation_accuracy calculation with available power sensor data."""
        # Arrange
        # Mock power correlation calculation (simplified for test)
        power_data_points = 50
        correct_predictions = 45
        expected_accuracy = round((correct_predictions / power_data_points) * 100, 1)
        
        with patch.object(smart_climate_entity, '_calculate_power_correlation_accuracy', return_value=expected_accuracy):
            # Act
            attributes = smart_climate_entity.extra_state_attributes
            
            # Assert
            assert "power_correlation_accuracy" in attributes
            assert attributes["power_correlation_accuracy"] == expected_accuracy

    def test_power_correlation_accuracy_no_power_sensor(self, smart_climate_entity):
        """Test power_correlation_accuracy when no power sensor configured."""
        # Arrange
        smart_climate_entity._power_sensor_id = None
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        assert "power_correlation_accuracy" in attributes
        assert attributes["power_correlation_accuracy"] == 0.0

    def test_power_correlation_accuracy_insufficient_data(self, smart_climate_entity):
        """Test power_correlation_accuracy with insufficient power monitoring data."""
        # Arrange
        with patch.object(smart_climate_entity, '_calculate_power_correlation_accuracy', return_value=0.0):
            # Act
            attributes = smart_climate_entity.extra_state_attributes
            
            # Assert
            assert "power_correlation_accuracy" in attributes
            assert attributes["power_correlation_accuracy"] == 0.0

    def test_hysteresis_cycle_count_with_cycles(self, smart_climate_entity):
        """Test hysteresis_cycle_count calculation with completed AC cycles."""
        # Arrange
        # Mock completed cycles based on start/stop temperature samples
        expected_cycles = 5  # Based on 5 start temps and 5 stop temps in fixture
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        assert "hysteresis_cycle_count" in attributes
        assert attributes["hysteresis_cycle_count"] == expected_cycles

    def test_hysteresis_cycle_count_no_cycles(self, smart_climate_entity):
        """Test hysteresis_cycle_count when no cycles completed."""
        # Arrange
        smart_climate_entity._offset_engine._hysteresis_learner._start_temps = []
        smart_climate_entity._offset_engine._hysteresis_learner._stop_temps = []
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        assert "hysteresis_cycle_count" in attributes
        assert attributes["hysteresis_cycle_count"] == 0

    def test_hysteresis_cycle_count_no_hysteresis_learner(self, smart_climate_entity):
        """Test hysteresis_cycle_count when no hysteresis learner available."""
        # Arrange
        smart_climate_entity._offset_engine._hysteresis_learner = None
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert
        assert "hysteresis_cycle_count" in attributes
        assert attributes["hysteresis_cycle_count"] == 0

    def test_temperature_window_calculation_precision(self, smart_climate_entity):
        """Test temperature window calculation with various precision scenarios."""
        # Test Case 1: Small window
        smart_climate_entity._offset_engine._hysteresis_learner.learned_start_threshold = 24.3
        smart_climate_entity._offset_engine._hysteresis_learner.learned_stop_threshold = 23.9
        
        attributes = smart_climate_entity.extra_state_attributes
        assert attributes["temperature_window_learned"] == "0.4°C"
        
        # Test Case 2: Large window
        smart_climate_entity._offset_engine._hysteresis_learner.learned_start_threshold = 27.0
        smart_climate_entity._offset_engine._hysteresis_learner.learned_stop_threshold = 22.0
        
        attributes = smart_climate_entity.extra_state_attributes
        assert attributes["temperature_window_learned"] == "5.0°C"

    def test_power_correlation_edge_cases(self, smart_climate_entity):
        """Test power correlation accuracy edge cases."""
        # Test Case 1: Perfect correlation (100%)
        with patch.object(smart_climate_entity, '_calculate_power_correlation_accuracy', return_value=100.0):
            attributes = smart_climate_entity.extra_state_attributes
            assert attributes["power_correlation_accuracy"] == 100.0
        
        # Test Case 2: No correlation (0%)
        with patch.object(smart_climate_entity, '_calculate_power_correlation_accuracy', return_value=0.0):
            attributes = smart_climate_entity.extra_state_attributes
            assert attributes["power_correlation_accuracy"] == 0.0
        
        # Test Case 3: Partial correlation
        with patch.object(smart_climate_entity, '_calculate_power_correlation_accuracy', return_value=73.5):
            attributes = smart_climate_entity.extra_state_attributes
            assert attributes["power_correlation_accuracy"] == 73.5

    def test_existing_attributes_preserved(self, smart_climate_entity):
        """Test that existing extra_state_attributes are preserved when adding AC learning attributes."""
        # Arrange
        smart_climate_entity._last_offset = 2.5
        with patch.object(smart_climate_entity, '_calculate_power_correlation_accuracy', return_value=85.0):
            # Act
            attributes = smart_climate_entity.extra_state_attributes
            
            # Assert - Check existing attributes still present
            assert "reactive_offset" in attributes
            assert attributes["reactive_offset"] == 2.5
            assert "predictive_offset" in attributes
            assert "total_offset" in attributes
            assert "predictive_strategy" in attributes
            
            # Check new AC learning attributes
            assert "temperature_window_learned" in attributes
            assert "power_correlation_accuracy" in attributes
            assert "hysteresis_cycle_count" in attributes

    def test_graceful_degradation_on_errors(self, smart_climate_entity):
        """Test graceful degradation when errors occur accessing hysteresis data."""
        # Arrange - Mock exception when accessing hysteresis learner
        smart_climate_entity._offset_engine._hysteresis_learner = Mock()
        smart_climate_entity._offset_engine._hysteresis_learner.has_sufficient_data = Mock(side_effect=Exception("Test error"))
        
        # Act
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert - Should not crash and return safe defaults
        assert "temperature_window_learned" in attributes
        assert attributes["temperature_window_learned"] == "error"
        assert "Temperature-window" in attributes["temperature_window_status_detail"]
        assert "power_correlation_accuracy" in attributes
        assert attributes["power_correlation_accuracy"] == 0.0
        assert "hysteresis_cycle_count" in attributes
        assert attributes["hysteresis_cycle_count"] == 0


class TestPowerCorrelationCalculation:
    """Test the power correlation accuracy calculation logic."""
    
    @pytest.fixture
    def smart_climate_entity_for_power_calc(self):
        """Create entity with specific setup for power correlation testing."""
        mock_hass = create_mock_hass()
        mock_config = {
            "climate_entity": "climate.test_ac",
            "room_sensor": "sensor.room_temp",
            "power_sensor": "sensor.ac_power",
            "max_offset": 5.0,
        }
        mock_dependencies = {
            "offset_engine": create_mock_offset_engine(),
            "sensor_manager": create_mock_sensor_manager(),
            "mode_manager": create_mock_mode_manager(),
            "temperature_controller": create_mock_temperature_controller(),
            "coordinator": create_mock_coordinator(),
        }
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=mock_config,
            wrapped_entity_id=mock_config["climate_entity"],
            room_sensor_id=mock_config["room_sensor"],
            **mock_dependencies,
        )
        entity._power_sensor_id = "sensor.ac_power"
        return entity

    def test_calculate_power_correlation_accuracy_basic(self, smart_climate_entity_for_power_calc):
        """Test basic power correlation accuracy calculation."""
        # Arrange
        entity = smart_climate_entity_for_power_calc
        entity._config.update({
            "power_idle_threshold": 200,
            "power_min_threshold": 800,
            "power_max_threshold": 800,
        })
        
        # Mock power state history for correlation calculation
        # Simulate 10 predictions with 8 correct correlations
        mock_power_history = [
            {"timestamp": 1000, "predicted_state": "high", "actual_power": 1500},  # Correct
            {"timestamp": 1001, "predicted_state": "high", "actual_power": 1600},  # Correct
            {"timestamp": 1002, "predicted_state": "idle", "actual_power": 50},    # Correct
            {"timestamp": 1003, "predicted_state": "idle", "actual_power": 45},    # Correct
            {"timestamp": 1004, "predicted_state": "high", "actual_power": 40},    # Wrong
            {"timestamp": 1005, "predicted_state": "idle", "actual_power": 1400},  # Wrong
            {"timestamp": 1006, "predicted_state": "high", "actual_power": 1550},  # Correct
            {"timestamp": 1007, "predicted_state": "high", "actual_power": 1450},  # Correct
            {"timestamp": 1008, "predicted_state": "idle", "actual_power": 60},    # Correct
            {"timestamp": 1009, "predicted_state": "idle", "actual_power": 55},    # Correct
        ]
        
        with patch.object(entity, '_get_power_prediction_history', return_value=mock_power_history):
            # Act
            accuracy = entity._calculate_power_correlation_accuracy()
            
            # Assert
            assert accuracy == 80.0  # 8/10 = 80%

    def test_calculate_power_correlation_accuracy_no_data(self, smart_climate_entity_for_power_calc):
        """Test power correlation accuracy when no historical data available."""
        # Arrange
        entity = smart_climate_entity_for_power_calc
        
        with patch.object(entity, '_get_power_prediction_history', return_value=[]):
            # Act
            accuracy = entity._calculate_power_correlation_accuracy()
            
            # Assert
            assert accuracy == 0.0

    def test_power_prediction_history_uses_hysteresis_transition_events(self, smart_climate_entity_for_power_calc):
        """Power prediction history should come from recorded hysteresis transition power telemetry."""
        entity = smart_climate_entity_for_power_calc
        hysteresis_learner = Mock()
        hysteresis_learner.get_transition_events.return_value = [
            {
                "transition_type": "start",
                "power_before": 20.0,
                "power_after": 420.0,
                "timestamp": "2026-05-24T10:00:00",
            },
            {
                "transition_type": "stop",
                "power_before": 410.0,
                "power_after": 15.0,
                "timestamp": "2026-05-24T10:12:00",
            },
        ]
        entity._offset_engine._hysteresis_learner = hysteresis_learner

        history = entity._get_power_prediction_history()

        assert history == [
            {
                "timestamp": "2026-05-24T10:00:00",
                "transition_type": "start",
                "transition_side": "before",
                "predicted_state": "idle",
                "actual_power": 20.0,
            },
            {
                "timestamp": "2026-05-24T10:00:00",
                "transition_type": "start",
                "transition_side": "after",
                "predicted_state": "active",
                "actual_power": 420.0,
            },
            {
                "timestamp": "2026-05-24T10:12:00",
                "transition_type": "stop",
                "transition_side": "before",
                "predicted_state": "active",
                "actual_power": 410.0,
            },
            {
                "timestamp": "2026-05-24T10:12:00",
                "transition_type": "stop",
                "transition_side": "after",
                "predicted_state": "idle",
                "actual_power": 15.0,
            },
        ]

    def test_power_correlation_accuracy_uses_transition_telemetry(self, smart_climate_entity_for_power_calc):
        """Accuracy should measure expected active/idle transition sides against actual power."""
        entity = smart_climate_entity_for_power_calc
        hysteresis_learner = Mock()
        hysteresis_learner.get_transition_events.return_value = [
            {"transition_type": "start", "power_before": 20.0, "power_after": 420.0},
            {"transition_type": "stop", "power_before": 420.0, "power_after": 15.0},
            {"transition_type": "start", "power_before": 320.0, "power_after": 450.0},
        ]
        entity._offset_engine._hysteresis_learner = hysteresis_learner

        assert entity._calculate_power_correlation_accuracy() == 83.3

    def test_power_correlation_status_attributes_explain_sample_count(self, smart_climate_entity_for_power_calc):
        """Climate attributes should expose correlation readiness instead of a silent placeholder zero."""
        entity = smart_climate_entity_for_power_calc
        hysteresis_learner = Mock()
        hysteresis_learner.has_sufficient_data = False
        hysteresis_learner.learned_start_offset = None
        hysteresis_learner.learned_stop_offset = None
        hysteresis_learner.learned_start_offset_lower_bound = None
        hysteresis_learner.learned_start_offset_upper_bound = None
        hysteresis_learner.learned_stop_offset_lower_bound = None
        hysteresis_learner.learned_stop_offset_upper_bound = None
        hysteresis_learner.get_latest_transition_event.return_value = None
        hysteresis_learner.get_transition_events.return_value = [
            {"transition_type": "start", "power_before": 20.0, "power_after": 420.0},
            {"transition_type": "stop", "power_before": 420.0, "power_after": 15.0},
        ]
        entity._offset_engine._hysteresis_learner = hysteresis_learner

        attributes = entity.extra_state_attributes

        assert attributes["power_correlation_sample_count"] == 4
        assert attributes["power_correlation_source"] == "offset_engine.hysteresis_learner.transition_events"
        assert attributes["power_correlation_status_detail"] == "Collecting transition power checks: 4/5 available"

    def test_calculate_power_correlation_accuracy_no_power_sensor(self, smart_climate_entity_for_power_calc):
        """Test power correlation accuracy when no power sensor configured."""
        # Arrange
        entity = smart_climate_entity_for_power_calc
        entity._power_sensor_id = None
        
        # Act
        accuracy = entity._calculate_power_correlation_accuracy()
        
        # Assert
        assert accuracy == 0.0


class TestHysteresisIntegration:
    """Test integration with HysteresisLearner component."""

    @pytest.fixture
    def entity_with_hysteresis(self):
        """Create entity with realistic hysteresis learner setup."""
        mock_hass = create_mock_hass()
        mock_config = {
            "climate_entity": "climate.test_ac",
            "room_sensor": "sensor.room_temp",
            "max_offset": 5.0,
        }
        
        # Create a more realistic hysteresis learner mock
        hysteresis_learner = Mock()
        hysteresis_learner.has_sufficient_data = True
        hysteresis_learner.learned_start_threshold = 25.5
        hysteresis_learner.learned_stop_threshold = 22.5
        hysteresis_learner._start_temps = [25.0, 25.5, 26.0, 25.2, 25.8, 25.3, 25.7]
        hysteresis_learner._stop_temps = [22.0, 22.5, 23.0, 22.3, 22.8, 22.1, 22.6]
        
        mock_dependencies = {
            "offset_engine": create_mock_offset_engine(),
            "sensor_manager": create_mock_sensor_manager(),
            "mode_manager": create_mock_mode_manager(),
            "temperature_controller": create_mock_temperature_controller(),
            "coordinator": create_mock_coordinator(),
        }
        mock_dependencies["offset_engine"]._hysteresis_learner = hysteresis_learner
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=mock_config,
            wrapped_entity_id=mock_config["climate_entity"],
            room_sensor_id=mock_config["room_sensor"],
            **mock_dependencies,
        )
        
        return entity

    def test_hysteresis_cycle_counting_logic(self, entity_with_hysteresis):
        """Test the logic for counting completed hysteresis cycles."""
        # Act
        attributes = entity_with_hysteresis.extra_state_attributes
        
        # Assert
        # Should use minimum of start_temps and stop_temps count
        assert attributes["hysteresis_cycle_count"] == 7  # min(7, 7)

    def test_temperature_window_from_thresholds(self, entity_with_hysteresis):
        """Test temperature window calculation from learned thresholds."""
        # Act
        attributes = entity_with_hysteresis.extra_state_attributes
        
        # Assert
        # Window = start_threshold - stop_threshold = 25.5 - 22.5 = 3.0
        assert attributes["temperature_window_learned"] == "3.0°C"

    def test_partial_hysteresis_data(self, entity_with_hysteresis):
        """Test behavior with partial hysteresis learning data."""
        # Arrange - Simulate more start samples than stop samples
        hysteresis_learner = entity_with_hysteresis._offset_engine._hysteresis_learner
        hysteresis_learner._start_temps = [25.0, 25.5, 26.0, 25.2, 25.8]
        hysteresis_learner._stop_temps = [22.0, 22.5, 23.0]  # Fewer stop samples
        
        # Act
        attributes = entity_with_hysteresis.extra_state_attributes
        
        # Assert
        # Cycle count should be minimum of available samples
        assert attributes["hysteresis_cycle_count"] == 3  # min(5, 3)