"""Tests for algorithm metrics sensors."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from custom_components.smart_climate.const import DOMAIN
from custom_components.smart_climate.sensor_algorithm import (
    CorrelationCoefficientSensor,
    PredictionVarianceSensor,
    ModelEntropySensor,
    LearningRateSensor,
    MomentumFactorSensor,
    RegularizationStrengthSensor,
    MeanSquaredErrorSensor,
    MeanAbsoluteErrorSensor,
    RSquaredSensor,
)


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator with test data."""
    coordinator = Mock()
    coordinator.last_update_success = True
    coordinator.data = {
        "algorithm_metrics": {
            "correlation_coefficient": 0.8523,
            "prediction_variance": 0.0234,
            "model_entropy": 1.2345,
            "learning_rate": 0.0015,
            "momentum_factor": 0.9,
            "regularization_strength": 0.001,
            "mean_squared_error": 0.0567,
            "mean_absolute_error": 0.1234,
            "r_squared": 0.8756,
        }
    }
    return coordinator


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    config_entry = Mock()
    config_entry.unique_id = "test_unique_id"
    config_entry.title = "Test Smart Climate"
    return config_entry


class TestCorrelationCoefficientSensor:
    """Tests for CorrelationCoefficientSensor."""

    def test_sensor_properties(self, mock_coordinator, mock_config_entry):
        """Test sensor properties are set correctly."""
        sensor = CorrelationCoefficientSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.name == "Correlation Coefficient"
        assert sensor.native_unit_of_measurement is None
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC
        assert sensor.icon == "mdi:chart-scatter-plot"
        assert sensor.suggested_display_precision == 3
        assert sensor.unique_id == "test_unique_id_climate_test_ac_correlation_coefficient"

    def test_native_value_with_data(self, mock_coordinator, mock_config_entry):
        """Test native value returns correct data."""
        sensor = CorrelationCoefficientSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.native_value == 0.852  # Rounded to 3 decimals

    def test_native_value_with_missing_data(self, mock_coordinator, mock_config_entry):
        """Test native value returns None when data is missing."""
        mock_coordinator.data = {}
        sensor = CorrelationCoefficientSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.native_value is None

    def test_native_value_with_none_data(self, mock_coordinator, mock_config_entry):
        """Test native value returns None when coordinator data is None."""
        mock_coordinator.data = None
        sensor = CorrelationCoefficientSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.native_value is None

    def test_boundary_values(self, mock_coordinator, mock_config_entry):
        """Test handling of boundary values (-1 to 1)."""
        sensor = CorrelationCoefficientSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        # Test negative correlation
        mock_coordinator.data["algorithm_metrics"]["correlation_coefficient"] = -0.9876
        assert sensor.native_value == -0.988
        
        # Test perfect positive correlation
        mock_coordinator.data["algorithm_metrics"]["correlation_coefficient"] = 1.0
        assert sensor.native_value == 1.0
        
        # Test perfect negative correlation
        mock_coordinator.data["algorithm_metrics"]["correlation_coefficient"] = -1.0
        assert sensor.native_value == -1.0
        
        # Test zero correlation
        mock_coordinator.data["algorithm_metrics"]["correlation_coefficient"] = 0.0
        assert sensor.native_value == 0.0


class TestPredictionVarianceSensor:
    """Tests for PredictionVarianceSensor."""

    def test_sensor_properties(self, mock_coordinator, mock_config_entry):
        """Test sensor properties are set correctly."""
        sensor = PredictionVarianceSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.name == "Prediction Variance"
        assert sensor.native_unit_of_measurement is None
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC
        assert sensor.icon == "mdi:sigma"
        assert sensor.suggested_display_precision == 3

    def test_native_value_with_data(self, mock_coordinator, mock_config_entry):
        """Test native value returns correct data."""
        sensor = PredictionVarianceSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.native_value == 0.023  # Rounded to 3 decimals


class TestModelEntropySensor:
    """Tests for ModelEntropySensor."""

    def test_sensor_properties(self, mock_coordinator, mock_config_entry):
        """Test sensor properties are set correctly."""
        sensor = ModelEntropySensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.name == "Model Entropy"
        assert sensor.native_unit_of_measurement is None
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC
        assert sensor.icon == "mdi:chart-histogram"
        assert sensor.suggested_display_precision == 3

    def test_native_value_with_data(self, mock_coordinator, mock_config_entry):
        """Test native value returns correct data."""
        sensor = ModelEntropySensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.native_value == 1.234  # Rounded to 3 decimals


class TestLearningRateSensor:
    """Tests for LearningRateSensor."""

    def test_sensor_properties(self, mock_coordinator, mock_config_entry):
        """Test sensor properties are set correctly."""
        sensor = LearningRateSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.name == "Learning Rate"
        assert sensor.native_unit_of_measurement is None
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC
        assert sensor.icon == "mdi:speedometer"
        assert sensor.suggested_display_precision == 3

    def test_native_value_with_data(self, mock_coordinator, mock_config_entry):
        """Test native value returns correct data."""
        sensor = LearningRateSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.native_value == 0.002  # Rounded to 3 decimals

    def test_boundary_values(self, mock_coordinator, mock_config_entry):
        """Test handling of boundary values (0 to 1)."""
        sensor = LearningRateSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        # Test zero learning rate
        mock_coordinator.data["algorithm_metrics"]["learning_rate"] = 0.0
        assert sensor.native_value == 0.0
        
        # Test maximum learning rate
        mock_coordinator.data["algorithm_metrics"]["learning_rate"] = 1.0
        assert sensor.native_value == 1.0


class TestMomentumFactorSensor:
    """Tests for MomentumFactorSensor."""

    def test_sensor_properties(self, mock_coordinator, mock_config_entry):
        """Test sensor properties are set correctly."""
        sensor = MomentumFactorSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.name == "Momentum Factor"
        assert sensor.native_unit_of_measurement is None
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC
        assert sensor.icon == "mdi:motion"
        assert sensor.suggested_display_precision == 3

    def test_native_value_with_data(self, mock_coordinator, mock_config_entry):
        """Test native value returns correct data."""
        sensor = MomentumFactorSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.native_value == 0.9  # No rounding needed


class TestRegularizationStrengthSensor:
    """Tests for RegularizationStrengthSensor."""

    def test_sensor_properties(self, mock_coordinator, mock_config_entry):
        """Test sensor properties are set correctly."""
        sensor = RegularizationStrengthSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.name == "Regularization Strength"
        assert sensor.native_unit_of_measurement is None
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC
        assert sensor.icon == "mdi:tune-vertical"
        assert sensor.suggested_display_precision == 3

    def test_native_value_with_data(self, mock_coordinator, mock_config_entry):
        """Test native value returns correct data."""
        sensor = RegularizationStrengthSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.native_value == 0.001


class TestMeanSquaredErrorSensor:
    """Tests for MeanSquaredErrorSensor."""

    def test_sensor_properties(self, mock_coordinator, mock_config_entry):
        """Test sensor properties are set correctly."""
        sensor = MeanSquaredErrorSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.name == "Mean Squared Error"
        assert sensor.native_unit_of_measurement is None
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC
        assert sensor.icon == "mdi:chart-line-variant"
        assert sensor.suggested_display_precision == 3

    def test_native_value_with_data(self, mock_coordinator, mock_config_entry):
        """Test native value returns correct data."""
        sensor = MeanSquaredErrorSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.native_value == 0.057  # Rounded to 3 decimals


class TestMeanAbsoluteErrorSensor:
    """Tests for MeanAbsoluteErrorSensor."""

    def test_sensor_properties(self, mock_coordinator, mock_config_entry):
        """Test sensor properties are set correctly."""
        sensor = MeanAbsoluteErrorSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.name == "Mean Absolute Error"
        assert sensor.native_unit_of_measurement is None
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC
        assert sensor.icon == "mdi:chart-line"
        assert sensor.suggested_display_precision == 3

    def test_native_value_with_data(self, mock_coordinator, mock_config_entry):
        """Test native value returns correct data."""
        sensor = MeanAbsoluteErrorSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.native_value == 0.123  # Rounded to 3 decimals


class TestRSquaredSensor:
    """Tests for RSquaredSensor."""

    def test_sensor_properties(self, mock_coordinator, mock_config_entry):
        """Test sensor properties are set correctly."""
        sensor = RSquaredSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.name == "R-Squared"
        assert sensor.native_unit_of_measurement is None
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC
        assert sensor.icon == "mdi:chart-box"
        assert sensor.suggested_display_precision == 3

    def test_native_value_with_data(self, mock_coordinator, mock_config_entry):
        """Test native value returns correct data."""
        sensor = RSquaredSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.native_value == 0.876  # Rounded to 3 decimals

    def test_boundary_values(self, mock_coordinator, mock_config_entry):
        """Test handling of boundary values (0 to 1)."""
        sensor = RSquaredSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        # Test perfect fit
        mock_coordinator.data["algorithm_metrics"]["r_squared"] = 1.0
        assert sensor.native_value == 1.0
        
        # Test no fit
        mock_coordinator.data["algorithm_metrics"]["r_squared"] = 0.0
        assert sensor.native_value == 0.0
        
        # Test typical good fit
        mock_coordinator.data["algorithm_metrics"]["r_squared"] = 0.95678
        assert sensor.native_value == 0.957


class TestSensorAvailability:
    """Test sensor availability based on coordinator status."""

    def test_sensor_available_when_coordinator_success(self, mock_coordinator, mock_config_entry):
        """Test sensor is available when coordinator update succeeds."""
        mock_coordinator.last_update_success = True
        sensor = CorrelationCoefficientSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.available is True

    def test_sensor_unavailable_when_coordinator_fails(self, mock_coordinator, mock_config_entry):
        """Test sensor is unavailable when coordinator update fails."""
        mock_coordinator.last_update_success = False
        sensor = CorrelationCoefficientSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.available is False


class TestInvalidDataHandling:
    """Test handling of invalid data types."""

    def test_non_numeric_data(self, mock_coordinator, mock_config_entry):
        """Test handling of non-numeric data."""
        mock_coordinator.data["algorithm_metrics"]["correlation_coefficient"] = "invalid"
        sensor = CorrelationCoefficientSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        # Should handle gracefully and return None
        assert sensor.native_value is None

    def test_none_metric_value(self, mock_coordinator, mock_config_entry):
        """Test handling of None metric value."""
        mock_coordinator.data["algorithm_metrics"]["correlation_coefficient"] = None
        sensor = CorrelationCoefficientSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.native_value is None