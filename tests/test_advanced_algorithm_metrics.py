"""Test advanced algorithm metrics for Smart Climate entity.

ABOUTME: Comprehensive tests for sophisticated ML algorithm internal metrics
that showcase the system's deep technical capabilities for advanced users.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.lightweight_learner import LightweightOffsetLearner, LearningStats
from custom_components.smart_climate.offset_engine import OffsetEngine
import statistics


class TestAdvancedAlgorithmMetrics:
    """Test advanced algorithm metrics calculation."""

    @pytest.fixture
    def mock_hass(self):
        """Mock Home Assistant."""
        hass = Mock()
        hass.states = Mock()
        hass.states.get = Mock(return_value=Mock(state="heat"))
        return hass

    @pytest.fixture
    def mock_offset_engine(self):
        """Mock offset engine with learner."""
        engine = Mock(spec=OffsetEngine)
        learner = Mock(spec=LightweightOffsetLearner)
        
        # Mock basic stats
        mock_stats = LearningStats(
            samples_collected=100,
            patterns_learned=15,
            avg_accuracy=0.85,
            last_sample_time="2025-07-13T20:30:00Z"
        )
        learner.get_learning_stats.return_value = mock_stats
        learner.get_statistics.return_value = mock_stats
        
        # Mock internal data for calculations
        learner._sample_count = 100
        learner._learning_rate = 0.1
        learner._enhanced_samples = [
            {"predicted": 1.0, "actual": 1.1, "timestamp": "2025-07-13T20:00:00Z"},
            {"predicted": 2.0, "actual": 1.9, "timestamp": "2025-07-13T20:15:00Z"},
            {"predicted": 1.5, "actual": 1.6, "timestamp": "2025-07-13T20:30:00Z"},
        ]
        learner._temp_correlation_data = [
            {"outdoor_temp": 20.0, "offset": 1.0},
            {"outdoor_temp": 22.0, "offset": 1.2},
            {"outdoor_temp": 24.0, "offset": 1.4},
            {"outdoor_temp": 26.0, "offset": 1.6}
        ]
        
        engine._learner = learner
        engine._enable_learning = True
        return engine

    @pytest.fixture
    def smart_climate_entity(self, mock_hass, mock_offset_engine):
        """Create Smart Climate entity with mocked dependencies."""
        entity = SmartClimateEntity(
            hass=mock_hass,
            config={"entity_id": "climate.test"},
            wrapped_entity_id="climate.real_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=mock_offset_engine,
            sensor_manager=Mock(),
            mode_manager=Mock(),
            temperature_controller=Mock(),
            coordinator=Mock(),
        )
        entity._offset_engine = mock_offset_engine
        return entity

    def test_correlation_coefficient_calculation(self, smart_climate_entity):
        """Test correlation coefficient calculation from temperature data."""
        # Test with sufficient data
        result = smart_climate_entity._calculate_correlation_coefficient()
        
        # Should return correlation between temperature and offset
        assert isinstance(result, float)
        assert -1.0 <= result <= 1.0
        
        # Test with no learner
        smart_climate_entity._offset_engine._learner = None
        result = smart_climate_entity._calculate_correlation_coefficient()
        assert result == 0.0

    def test_prediction_variance_calculation(self, smart_climate_entity):
        """Test prediction variance calculation."""
        result = smart_climate_entity._calculate_prediction_variance()
        
        # Should return variance of predictions
        assert isinstance(result, float)
        assert result >= 0.0  # Variance is always non-negative
        
        # Test with no samples
        smart_climate_entity._offset_engine._learner._enhanced_samples = []
        result = smart_climate_entity._calculate_prediction_variance()
        assert result == 0.0

    def test_model_entropy_calculation(self, smart_climate_entity):
        """Test information theory entropy calculation."""
        result = smart_climate_entity._calculate_model_entropy()
        
        # Should return entropy of prediction distribution
        assert isinstance(result, float)
        assert result >= 0.0  # Entropy is always non-negative
        
        # Test with no learner
        smart_climate_entity._offset_engine._learner = None
        result = smart_climate_entity._calculate_model_entropy()
        assert result == 0.0

    def test_learning_rate_extraction(self, smart_climate_entity):
        """Test learning rate extraction from ML model."""
        result = smart_climate_entity._get_learning_rate()
        
        # Should return configured learning rate
        assert result == 0.1
        
        # Test with no learner
        smart_climate_entity._offset_engine._learner = None
        result = smart_climate_entity._get_learning_rate()
        assert result == 0.0

    def test_momentum_factor_calculation(self, smart_climate_entity):
        """Test momentum factor for optimization."""
        result = smart_climate_entity._calculate_momentum_factor()
        
        # Should return momentum based on learning stability
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0
        
        # Test with no samples
        smart_climate_entity._offset_engine._learner._enhanced_samples = []
        result = smart_climate_entity._calculate_momentum_factor()
        assert result == 0.0

    def test_regularization_strength_calculation(self, smart_climate_entity):
        """Test L2 regularization strength calculation."""
        # Test with low variance predictions first
        low_variance_samples = [
            {"predicted": 1.0, "actual": 1.0},
            {"predicted": 1.01, "actual": 1.01},
            {"predicted": 1.02, "actual": 1.02},
        ]
        smart_climate_entity._offset_engine._learner._enhanced_samples = low_variance_samples
        low_variance_result = smart_climate_entity._calculate_regularization_strength()
        
        # Should return regularization parameter
        assert isinstance(low_variance_result, float)
        assert low_variance_result >= 0.0
        
        # Test with high variance (should increase regularization)
        high_variance_samples = [
            {"predicted": 1.0, "actual": 5.0},
            {"predicted": 5.0, "actual": -3.0},
            {"predicted": 10.0, "actual": 8.0},
        ]
        smart_climate_entity._offset_engine._learner._enhanced_samples = high_variance_samples
        high_variance_result = smart_climate_entity._calculate_regularization_strength()
        assert high_variance_result > low_variance_result

    def test_mean_squared_error_calculation(self, smart_climate_entity):
        """Test MSE performance metric calculation."""
        result = smart_climate_entity._calculate_mean_squared_error()
        
        # Should return MSE from prediction history
        assert isinstance(result, float)
        assert result >= 0.0  # MSE is always non-negative
        
        # Verify calculation with known data
        samples = smart_climate_entity._offset_engine._learner._enhanced_samples
        expected_mse = statistics.mean([
            (sample["predicted"] - sample["actual"]) ** 2 
            for sample in samples
        ])
        assert abs(result - expected_mse) < 0.001

    def test_mean_absolute_error_calculation(self, smart_climate_entity):
        """Test MAE performance metric calculation."""
        result = smart_climate_entity._calculate_mean_absolute_error()
        
        # Should return MAE from prediction history
        assert isinstance(result, float)
        assert result >= 0.0  # MAE is always non-negative
        
        # Verify calculation with known data
        samples = smart_climate_entity._offset_engine._learner._enhanced_samples
        expected_mae = statistics.mean([
            abs(sample["predicted"] - sample["actual"]) 
            for sample in samples
        ])
        assert abs(result - expected_mae) < 0.001

    def test_r_squared_calculation(self, smart_climate_entity):
        """Test R² coefficient of determination calculation."""
        result = smart_climate_entity._calculate_r_squared()
        
        # Should return R² between -inf and 1.0
        assert isinstance(result, float)
        assert result <= 1.0  # R² can be negative for poor fits
        
        # Test with perfect predictions (R² should be 1.0)
        perfect_samples = [
            {"predicted": 1.0, "actual": 1.0},
            {"predicted": 2.0, "actual": 2.0},
            {"predicted": 1.5, "actual": 1.5},
        ]
        smart_climate_entity._offset_engine._learner._enhanced_samples = perfect_samples
        perfect_result = smart_climate_entity._calculate_r_squared()
        assert abs(perfect_result - 1.0) < 0.001

    def test_extra_state_attributes_algorithm_metrics(self, smart_climate_entity):
        """Test that advanced algorithm metrics are included in extra_state_attributes."""
        # Mock the calculation methods
        smart_climate_entity._calculate_correlation_coefficient = Mock(return_value=0.85)
        smart_climate_entity._calculate_prediction_variance = Mock(return_value=0.15)
        smart_climate_entity._calculate_model_entropy = Mock(return_value=2.5)
        smart_climate_entity._get_learning_rate = Mock(return_value=0.1)
        smart_climate_entity._calculate_momentum_factor = Mock(return_value=0.3)
        smart_climate_entity._calculate_regularization_strength = Mock(return_value=0.01)
        smart_climate_entity._calculate_mean_squared_error = Mock(return_value=0.25)
        smart_climate_entity._calculate_mean_absolute_error = Mock(return_value=0.4)
        smart_climate_entity._calculate_r_squared = Mock(return_value=0.92)
        
        # Mock other required methods to avoid errors
        smart_climate_entity._forecast_engine = None
        smart_climate_entity._delay_learner = None
        smart_climate_entity._get_seasonal_pattern_count = Mock(return_value=0)
        smart_climate_entity._get_outdoor_temp_bucket = Mock(return_value="Unknown")
        smart_climate_entity._get_seasonal_accuracy = Mock(return_value=0.0)
        smart_climate_entity._get_temperature_window_learned = Mock(return_value="Unknown")
        smart_climate_entity._calculate_power_correlation_accuracy = Mock(return_value=0.0)
        smart_climate_entity._get_hysteresis_cycle_count = Mock(return_value=0)
        smart_climate_entity._get_temperature_stability_detected = Mock(return_value=False)
        smart_climate_entity._get_learned_delay_seconds = Mock(return_value=0.0)
        smart_climate_entity._get_ema_coefficient = Mock(return_value=0.2)
        smart_climate_entity._get_prediction_latency_ms = Mock(return_value=0.0)
        smart_climate_entity._get_energy_efficiency_score = Mock(return_value=50)
        smart_climate_entity._get_sensor_availability_score = Mock(return_value=0.0)
        smart_climate_entity._get_memory_usage_kb = Mock(return_value=0.0)
        smart_climate_entity._measure_persistence_latency_ms = Mock(return_value=0.0)
        smart_climate_entity._get_outlier_detection_active = Mock(return_value=False)
        smart_climate_entity._get_samples_per_day = Mock(return_value=0.0)
        smart_climate_entity._get_accuracy_improvement_rate = Mock(return_value=0.0)
        smart_climate_entity._get_convergence_trend = Mock(return_value="unknown")
        smart_climate_entity._last_offset = 0.0
        
        attributes = smart_climate_entity.extra_state_attributes
        
        # Verify all advanced algorithm metrics are present
        assert "correlation_coefficient" in attributes
        assert "prediction_variance" in attributes
        assert "model_entropy" in attributes
        assert "learning_rate" in attributes
        assert "momentum_factor" in attributes
        assert "regularization_strength" in attributes
        assert "mean_squared_error" in attributes
        assert "mean_absolute_error" in attributes
        assert "r_squared" in attributes
        
        # Verify values
        assert attributes["correlation_coefficient"] == 0.85
        assert attributes["prediction_variance"] == 0.15
        assert attributes["model_entropy"] == 2.5
        assert attributes["learning_rate"] == 0.1
        assert attributes["momentum_factor"] == 0.3
        assert attributes["regularization_strength"] == 0.01
        assert attributes["mean_squared_error"] == 0.25
        assert attributes["mean_absolute_error"] == 0.4
        assert attributes["r_squared"] == 0.92

    def test_algorithm_metrics_with_no_learner(self, smart_climate_entity):
        """Test algorithm metrics fallback when no learner is available."""
        smart_climate_entity._offset_engine._learner = None
        smart_climate_entity._offset_engine._enable_learning = False
        
        # Test each metric individually
        assert smart_climate_entity._calculate_correlation_coefficient() == 0.0
        assert smart_climate_entity._calculate_prediction_variance() == 0.0
        assert smart_climate_entity._calculate_model_entropy() == 0.0
        assert smart_climate_entity._get_learning_rate() == 0.0
        assert smart_climate_entity._calculate_momentum_factor() == 0.0
        assert smart_climate_entity._calculate_regularization_strength() == 0.0
        assert smart_climate_entity._calculate_mean_squared_error() == 0.0
        assert smart_climate_entity._calculate_mean_absolute_error() == 0.0
        assert smart_climate_entity._calculate_r_squared() == 0.0

    def test_algorithm_metrics_edge_cases(self, smart_climate_entity):
        """Test algorithm metrics with edge case data."""
        # Test with single sample
        single_sample = [{"predicted": 1.0, "actual": 1.0}]
        smart_climate_entity._offset_engine._learner._enhanced_samples = single_sample
        
        assert smart_climate_entity._calculate_prediction_variance() == 0.0
        assert smart_climate_entity._calculate_mean_squared_error() == 0.0
        assert smart_climate_entity._calculate_mean_absolute_error() == 0.0
        
        # Test with identical predictions (zero variance)
        identical_samples = [
            {"predicted": 1.0, "actual": 1.0},
            {"predicted": 1.0, "actual": 1.0},
            {"predicted": 1.0, "actual": 1.0},
        ]
        smart_climate_entity._offset_engine._learner._enhanced_samples = identical_samples
        
        assert smart_climate_entity._calculate_prediction_variance() == 0.0
        assert smart_climate_entity._calculate_model_entropy() >= 0.0

    def test_statistical_accuracy(self, smart_climate_entity):
        """Test statistical accuracy of calculations."""
        # Set up known data for verification
        test_samples = [
            {"predicted": 1.0, "actual": 1.1},  # error = 0.1, sq_error = 0.01
            {"predicted": 2.0, "actual": 1.8},  # error = -0.2, sq_error = 0.04
            {"predicted": 1.5, "actual": 1.6},  # error = 0.1, sq_error = 0.01
        ]
        smart_climate_entity._offset_engine._learner._enhanced_samples = test_samples
        
        # Verify MSE calculation
        expected_mse = (0.01 + 0.04 + 0.01) / 3  # 0.02
        calculated_mse = smart_climate_entity._calculate_mean_squared_error()
        assert abs(calculated_mse - expected_mse) < 0.001
        
        # Verify MAE calculation
        expected_mae = (0.1 + 0.2 + 0.1) / 3  # 0.133...
        calculated_mae = smart_climate_entity._calculate_mean_absolute_error()
        assert abs(calculated_mae - expected_mae) < 0.001
        
        # Verify prediction variance
        predictions = [1.0, 2.0, 1.5]
        expected_variance = statistics.variance(predictions)
        calculated_variance = smart_climate_entity._calculate_prediction_variance()
        assert abs(calculated_variance - expected_variance) < 0.001

    def test_correlation_coefficient_statistical_correctness(self, smart_climate_entity):
        """Test correlation coefficient calculation is statistically correct."""
        # Set up temperature correlation data with known correlation
        temp_data = [
            {"outdoor_temp": 20.0, "offset": 1.0},
            {"outdoor_temp": 25.0, "offset": 2.0}, 
            {"outdoor_temp": 30.0, "offset": 3.0},
            {"outdoor_temp": 35.0, "offset": 4.0}
        ]  # Perfect positive correlation
        smart_climate_entity._offset_engine._learner._temp_correlation_data = temp_data
        
        result = smart_climate_entity._calculate_correlation_coefficient()
        
        # Should be close to 1.0 for perfect positive correlation
        assert abs(result - 1.0) < 0.001
        
        # Test negative correlation
        negative_data = [
            {"outdoor_temp": 20.0, "offset": 4.0},
            {"outdoor_temp": 25.0, "offset": 3.0}, 
            {"outdoor_temp": 30.0, "offset": 2.0},
            {"outdoor_temp": 35.0, "offset": 1.0}
        ]
        smart_climate_entity._offset_engine._learner._temp_correlation_data = negative_data
        
        result = smart_climate_entity._calculate_correlation_coefficient()
        
        # Should be close to -1.0 for perfect negative correlation
        assert abs(result - (-1.0)) < 0.001

    @patch('numpy.corrcoef')
    def test_correlation_coefficient_with_numpy_unavailable(self, mock_corrcoef, smart_climate_entity):
        """Test correlation coefficient calculation when numpy is unavailable."""
        # Simulate numpy import error
        mock_corrcoef.side_effect = ImportError("No module named 'numpy'")
        
        result = smart_climate_entity._calculate_correlation_coefficient()
        
        # Should fall back to manual calculation
        assert isinstance(result, float)
        assert -1.0 <= result <= 1.0

    def test_entropy_calculation_mathematical_properties(self, smart_climate_entity):
        """Test entropy calculation follows mathematical properties."""
        # Uniform distribution should have higher entropy
        uniform_predictions = [1.0, 2.0, 3.0, 4.0, 5.0]
        uniform_samples = [{"predicted": p, "actual": p} for p in uniform_predictions]
        smart_climate_entity._offset_engine._learner._enhanced_samples = uniform_samples
        
        uniform_entropy = smart_climate_entity._calculate_model_entropy()
        
        # Concentrated distribution should have lower entropy
        concentrated_predictions = [2.0, 2.0, 2.0, 2.0, 2.0]
        concentrated_samples = [{"predicted": p, "actual": p} for p in concentrated_predictions]
        smart_climate_entity._offset_engine._learner._enhanced_samples = concentrated_samples
        
        concentrated_entropy = smart_climate_entity._calculate_model_entropy()
        
        # Uniform should have higher entropy than concentrated
        assert uniform_entropy > concentrated_entropy
        assert concentrated_entropy >= 0.0  # All entropies non-negative

    def test_momentum_factor_stability_relationship(self, smart_climate_entity):
        """Test momentum factor relationship to prediction stability."""
        # Stable predictions should have higher momentum
        stable_samples = [
            {"predicted": 1.0, "actual": 1.0},
            {"predicted": 1.01, "actual": 1.01},
            {"predicted": 1.02, "actual": 1.02},
        ]
        smart_climate_entity._offset_engine._learner._enhanced_samples = stable_samples
        
        stable_momentum = smart_climate_entity._calculate_momentum_factor()
        
        # Unstable predictions should have lower momentum
        unstable_samples = [
            {"predicted": 1.0, "actual": 3.0},
            {"predicted": 2.0, "actual": -1.0},
            {"predicted": 1.5, "actual": 5.0},
        ]
        smart_climate_entity._offset_engine._learner._enhanced_samples = unstable_samples
        
        unstable_momentum = smart_climate_entity._calculate_momentum_factor()
        
        # Stable should have higher momentum than unstable
        assert stable_momentum > unstable_momentum
        assert 0.0 <= unstable_momentum <= 1.0
        assert 0.0 <= stable_momentum <= 1.0