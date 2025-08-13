"""Tests for OffsetEngine component."""

import pytest
import numpy as np
from datetime import time
from unittest.mock import Mock, MagicMock

from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.models import OffsetInput, OffsetResult
from custom_components.smart_climate.feature_engineering import FeatureEngineering


class TestOffsetEngine:
    """Test suite for OffsetEngine class."""

    def test_init_with_default_config(self):
        """Test OffsetEngine initialization with default config."""
        config = {}
        engine = OffsetEngine(config)
        
        assert engine._max_offset == 5.0
        assert engine._ml_enabled is True
        assert engine._ml_model is None

    def test_init_with_custom_config(self):
        """Test OffsetEngine initialization with custom config."""
        config = {
            "max_offset": 3.0,
            "ml_enabled": False
        }
        engine = OffsetEngine(config)
        
        assert engine._max_offset == 3.0
        assert engine._ml_enabled is False
        assert engine._ml_model is None

    def test_calculate_offset_basic_scenario(self):
        """Test basic offset calculation."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=1
        )
        
        result = engine.calculate_offset(input_data)
        
        assert isinstance(result, OffsetResult)
        assert isinstance(result.offset, float)
        assert isinstance(result.clamped, bool)
        assert isinstance(result.reason, str)
        assert 0.0 <= result.confidence <= 1.0
        assert -5.0 <= result.offset <= 5.0

    def test_calculate_offset_ac_warmer_than_room(self):
        """Test offset when AC internal sensor reads warmer than room."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=24.0,
            room_temp=22.0,
            outdoor_temp=None,
            mode="none",
            power_consumption=None,
            time_of_day=time(12, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        # AC reads warmer than room, so we need positive offset to cool less
        assert result.offset > 0
        assert not result.clamped
        assert "AC sensor warmer than room" in result.reason

    def test_calculate_offset_ac_cooler_than_room(self):
        """Test offset when AC internal sensor reads cooler than room."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=20.0,
            room_temp=22.0,
            outdoor_temp=None,
            mode="none",
            power_consumption=None,
            time_of_day=time(12, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        # AC reads cooler than room, so we need negative offset to cool more
        assert result.offset < 0
        assert not result.clamped
        assert "AC sensor cooler than room" in result.reason

    def test_calculate_offset_max_limit_clamping(self):
        """Test offset clamping to maximum limit."""
        config = {"max_offset": 2.0}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=15.0,  # Very different from room
            room_temp=25.0,
            outdoor_temp=None,
            mode="none",
            power_consumption=None,
            time_of_day=time(12, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        assert abs(result.offset) <= 2.0
        assert result.clamped
        assert "clamped to limit" in result.reason

    def test_calculate_offset_zero_difference(self):
        """Test offset when AC and room temperatures are equal."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=22.0,
            outdoor_temp=None,
            mode="none",
            power_consumption=None,
            time_of_day=time(12, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        assert result.offset == 0.0
        assert not result.clamped
        assert "no offset needed" in result.reason.lower()

    def test_calculate_offset_away_mode(self):
        """Test offset calculation in away mode."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=25.0,
            mode="away",
            power_consumption=None,
            time_of_day=time(12, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        assert isinstance(result, OffsetResult)
        assert "away mode" in result.reason.lower()

    def test_calculate_offset_sleep_mode(self):
        """Test offset calculation in sleep mode."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=25.0,
            mode="sleep",
            power_consumption=None,
            time_of_day=time(23, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        assert isinstance(result, OffsetResult)
        assert "sleep mode" in result.reason.lower()

    def test_calculate_offset_boost_mode(self):
        """Test offset calculation in boost mode."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=30.0,
            mode="boost",
            power_consumption=200.0,
            time_of_day=time(15, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        assert isinstance(result, OffsetResult)
        assert "boost mode" in result.reason.lower()

    def test_calculate_offset_with_outdoor_temp(self):
        """Test offset calculation with outdoor temperature consideration."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=35.0,  # Very hot outside
            mode="none",
            power_consumption=None,
            time_of_day=time(15, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        assert isinstance(result, OffsetResult)
        # Should consider outdoor temperature in reasoning
        assert result.reason is not None

    def test_calculate_offset_with_power_consumption(self):
        """Test offset calculation with power consumption data."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=300.0,  # High power usage
            time_of_day=time(15, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        assert isinstance(result, OffsetResult)
        # Should consider power consumption in reasoning
        assert result.reason is not None

    def test_calculate_offset_confidence_levels(self):
        """Test that confidence levels are reasonable."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        # Test with complete data
        input_complete = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=150.0,
            time_of_day=time(15, 0),
            day_of_week=2
        )
        
        result_complete = engine.calculate_offset(input_complete)
        
        # Test with minimal data
        input_minimal = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=None,
            mode="none",
            power_consumption=None,
            time_of_day=time(15, 0),
            day_of_week=2
        )
        
        result_minimal = engine.calculate_offset(input_minimal)
        
        # Complete data should have higher confidence
        assert result_complete.confidence >= result_minimal.confidence

    def test_update_ml_model(self):
        """Test ML model update functionality."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        # Should not raise an exception
        engine.update_ml_model("/path/to/model.pkl")
        
        # For now, this is a placeholder implementation
        # In future, this would load and validate the model

    def test_calculate_offset_edge_cases(self):
        """Test edge cases and error conditions."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        # Test with extreme temperature differences
        input_extreme = OffsetInput(
            ac_internal_temp=10.0,
            room_temp=30.0,
            outdoor_temp=None,
            mode="none",
            power_consumption=None,
            time_of_day=time(12, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_extreme)
        
        assert isinstance(result, OffsetResult)
        assert abs(result.offset) <= 5.0
        assert result.clamped


class TestOffsetEngineFeatureIntegration:
    """Test suite for OffsetEngine feature engineering integration."""

    def test_constructor_accepts_feature_engineer_parameter(self):
        """Test OffsetEngine constructor accepts feature_engineer parameter."""
        config = {"max_offset": 5.0}
        feature_engineer = Mock(spec=FeatureEngineering)
        
        # This should work - optional parameter with None default
        engine = OffsetEngine(config, feature_engineer=None)
        assert engine._feature_engineer is None
        
        # This should also work - with actual feature engineer
        engine_with_fe = OffsetEngine(config, feature_engineer=feature_engineer)
        assert engine_with_fe._feature_engineer is feature_engineer

    def test_calculate_offset_enriches_input_with_feature_engineer(self):
        """Test calculate_offset enriches input when feature_engineer provided."""
        config = {"max_offset": 5.0}
        mock_feature_engineer = Mock(spec=FeatureEngineering)
        
        # Create enriched input data that enrich_features will return
        enriched_input = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=1,
            indoor_humidity=60.0,
            outdoor_humidity=55.0,
            humidity_differential=5.0,
            indoor_dew_point=12.5,
            outdoor_dew_point=15.2,
            heat_index=21.3
        )
        mock_feature_engineer.enrich_features.return_value = enriched_input
        
        engine = OffsetEngine(config, feature_engineer=mock_feature_engineer)
        
        original_input = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=1,
            indoor_humidity=60.0,
            outdoor_humidity=55.0
        )
        
        result = engine.calculate_offset(original_input)
        
        # Verify enrich_features was called with original input
        mock_feature_engineer.enrich_features.assert_called_once_with(original_input)
        
        assert isinstance(result, OffsetResult)

    def test_calculate_offset_works_without_feature_engineer(self):
        """Test calculate_offset works without feature_engineer (backward compatibility)."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config, feature_engineer=None)
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=1
        )
        
        result = engine.calculate_offset(input_data)
        
        assert isinstance(result, OffsetResult)
        assert isinstance(result.offset, float)

    def test_prepare_feature_vector_handles_numpy_nan(self):
        """Test _prepare_feature_vector converts None values to numpy.nan."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=None,  # None value
            mode="none",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=1,
            indoor_humidity=None,  # None value
            outdoor_humidity=55.0,
            humidity_differential=None  # None value
        )
        
        feature_vector = engine._prepare_feature_vector(input_data)
        
        assert isinstance(feature_vector, (list, np.ndarray))
        # Check that None values were converted to np.nan
        if isinstance(feature_vector, list):
            nan_count = sum(1 for x in feature_vector if x is None or (isinstance(x, float) and np.isnan(x)))
            assert nan_count > 0  # Should have some nan values
        else:  # numpy array
            assert np.any(np.isnan(feature_vector))

    def test_model_versioning_support(self):
        """Test model package loading with features list."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        # Mock model package format
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1.5])
        
        model_package = {
            'model': mock_model,
            'features': ['ac_internal_temp', 'room_temp', 'indoor_humidity'],
            'version': '2.0-humidity'
        }
        
        # This should work - loading model package format
        engine._ml_model = model_package
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=1,
            indoor_humidity=60.0
        )
        
        result = engine.calculate_offset(input_data)
        
        assert isinstance(result, OffsetResult)

    def test_model_versioning_backward_compatibility(self):
        """Test old model format still works."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        # Mock old model format (just the model object)
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1.5])
        
        engine._ml_model = mock_model  # Old format - direct model
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=1
        )
        
        result = engine.calculate_offset(input_data)
        
        assert isinstance(result, OffsetResult)

    def test_feature_alignment(self):
        """Test feature alignment with different feature sets."""
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        # Mock model trained with subset of features
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1.5])
        
        model_package = {
            'model': mock_model,
            'features': ['ac_internal_temp', 'room_temp', 'indoor_humidity'],  # Only 3 features
            'version': '2.0-humidity'
        }
        engine._ml_model = model_package
        
        # Input has more features than model expects
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=25.0,  # Extra feature
            mode="none",
            power_consumption=150.0,  # Extra feature  
            time_of_day=time(14, 30),
            day_of_week=1,
            indoor_humidity=60.0,
            outdoor_humidity=55.0,  # Extra feature
            humidity_differential=5.0  # Extra feature
        )
        
        result = engine.calculate_offset(input_data)
        
        assert isinstance(result, OffsetResult)
        # Verify only model's features were used for prediction
        # The exact verification will depend on implementation details