"""Tests for humidity contribution calculation in OffsetEngine."""

import pytest
from datetime import time
from unittest.mock import Mock, patch, MagicMock

from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.models import OffsetInput
from custom_components.smart_climate.lightweight_learner import LightweightOffsetLearner


class TestOffsetEngineHumidityContribution:
    """Test suite for humidity contribution calculation methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            "max_offset": 5.0,
            "ml_enabled": True,
            "enable_learning": True
        }
        
    def test_get_feature_contribution_humidity_returns_stored_value(self):
        """Test that get_feature_contribution returns stored humidity contribution."""
        engine = OffsetEngine(self.config)
        
        # Simulate stored humidity contribution
        engine._last_humidity_contribution = 0.3
        
        result = engine.get_feature_contribution("humidity")
        
        assert result == 0.3
        
    def test_get_feature_contribution_humidity_returns_zero_if_not_stored(self):
        """Test that get_feature_contribution returns 0 if no humidity contribution stored."""
        engine = OffsetEngine(self.config)
        
        # No stored contribution (should default to 0.0)
        result = engine.get_feature_contribution("humidity")
        
        assert result == 0.0
        
    def test_get_feature_contribution_unknown_feature_returns_zero(self):
        """Test that get_feature_contribution returns 0 for unknown features."""
        engine = OffsetEngine(self.config)
        
        result = engine.get_feature_contribution("unknown_feature")
        
        assert result == 0.0
        
    def test_humidity_contribution_calculated_during_ml_prediction(self):
        """Test that humidity contribution is calculated when ML learning is used."""
        engine = OffsetEngine(self.config)
        
        # Set up mock learner with predict method
        mock_learner = Mock(spec=LightweightOffsetLearner)
        mock_learner._enhanced_samples = [{"sample": "data"}]  # Non-empty to enable learning
        mock_learner.predict.side_effect = [2.5, 2.2, 2.5]  # First prediction during learning, then our two predictions
        
        # Mock get_statistics to return enough samples to exit calibration phase
        mock_stats = Mock()
        mock_stats.samples_collected = 15  # More than MIN_SAMPLES_FOR_ACTIVE_CONTROL (10)
        mock_learner.get_statistics.return_value = mock_stats
        
        engine._learner = mock_learner
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="auto",
            power_consumption=150.0,
            time_of_day=time(14, 0),
            day_of_week=2,
            indoor_humidity=65.0,
            outdoor_humidity=80.0,
            humidity_differential=15.0
        )
        
        result = engine.calculate_offset(input_data)
        
        # Should have called predict three times: once for main calculation, twice for contribution
        assert mock_learner.predict.call_count == 3
        
        # First call is the main learning calculation
        first_call = mock_learner.predict.call_args_list[0]
        assert first_call[1]["indoor_humidity"] == 65.0
        assert first_call[1]["outdoor_humidity"] == 80.0
        
        # Second call should have None for humidity (for contribution calculation)
        second_call = mock_learner.predict.call_args_list[1]
        assert second_call[1]["indoor_humidity"] is None
        assert second_call[1]["outdoor_humidity"] is None
        
        # Third call should have humidity data again (for contribution calculation)
        third_call = mock_learner.predict.call_args_list[2]
        assert third_call[1]["indoor_humidity"] == 65.0
        assert third_call[1]["outdoor_humidity"] == 80.0
        
        # Contribution should be stored (2.5 - 2.2 = 0.3)
        assert engine.get_feature_contribution("humidity") == pytest.approx(0.3, abs=0.01)
        
    def test_humidity_contribution_zero_when_no_ml_learning(self):
        """Test that humidity contribution is 0 when ML learning is disabled."""
        config = {
            "max_offset": 5.0,
            "ml_enabled": False,
            "enable_learning": False
        }
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="auto",
            power_consumption=150.0,
            indoor_humidity=65.0,
            outdoor_humidity=80.0,
            time_of_day=time(14, 0),
            day_of_week=2
        )
        
        result = engine.calculate_offset(input_data)
        
        # No ML learning means no contribution
        assert engine.get_feature_contribution("humidity") == 0.0
        
    def test_humidity_contribution_zero_when_no_humidity_data(self):
        """Test that humidity contribution is 0 when no humidity data present."""
        engine = OffsetEngine(self.config)
        
        # Set up mock learner but with no humidity data
        mock_learner = Mock(spec=LightweightOffsetLearner)
        mock_learner._enhanced_samples = [{"sample": "data"}]
        mock_learner.predict.return_value = 2.0
        engine._learner = mock_learner
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="auto",
            power_consumption=150.0,
            time_of_day=time(14, 0),
            day_of_week=2,
            indoor_humidity=None,
            outdoor_humidity=None
        )
        
        result = engine.calculate_offset(input_data)
        
        # No humidity data means no contribution calculation
        assert engine.get_feature_contribution("humidity") == 0.0
        
    def test_humidity_contribution_zero_when_all_humidity_values_zero(self):
        """Test that humidity contribution is 0 when all humidity values are 0."""
        engine = OffsetEngine(self.config)
        
        # Set up mock learner
        mock_learner = Mock(spec=LightweightOffsetLearner)
        mock_learner._enhanced_samples = [{"sample": "data"}]
        mock_learner.predict.return_value = 2.0
        engine._learner = mock_learner
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="auto",
            power_consumption=150.0,
            time_of_day=time(14, 0),
            day_of_week=2,
            indoor_humidity=0.0,
            outdoor_humidity=0.0
        )
        
        result = engine.calculate_offset(input_data)
        
        # All zero humidity values means no contribution calculation
        assert engine.get_feature_contribution("humidity") == 0.0
        
    def test_reason_includes_humidity_contribution_positive(self):
        """Test that reason string includes positive humidity contribution in °C."""
        engine = OffsetEngine(self.config)
        
        # Set up mock learner with significant positive contribution
        mock_learner = Mock(spec=LightweightOffsetLearner)
        mock_learner._enhanced_samples = [{"sample": "data"}]
        mock_learner.predict.side_effect = [2.8, 2.5, 2.8]  # Main prediction, then contribution predictions
        
        # Mock get_statistics to exit calibration phase
        mock_stats = Mock()
        mock_stats.samples_collected = 15
        mock_learner.get_statistics.return_value = mock_stats
        
        engine._learner = mock_learner
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="auto",
            power_consumption=150.0,
            time_of_day=time(14, 0),
            day_of_week=2,
            indoor_humidity=65.0,
            outdoor_humidity=80.0,
            humidity_differential=15.0
        )
        
        result = engine.calculate_offset(input_data)
        
        # Should show positive contribution in reason
        assert "humidity-adjusted (+0.3°C from indoor: 65.0%, outdoor: 80.0%, diff: 15.0%)" in result.reason
        
    def test_reason_includes_humidity_contribution_negative(self):
        """Test that reason string includes negative humidity contribution in °C."""
        engine = OffsetEngine(self.config)
        
        # Set up mock learner with significant negative contribution  
        mock_learner = Mock(spec=LightweightOffsetLearner)
        mock_learner._enhanced_samples = [{"sample": "data"}]
        mock_learner.predict.side_effect = [2.2, 2.5, 2.2]  # Main prediction, then contribution predictions
        
        # Mock get_statistics to exit calibration phase
        mock_stats = Mock()
        mock_stats.samples_collected = 15
        mock_learner.get_statistics.return_value = mock_stats
        
        engine._learner = mock_learner
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="auto",
            power_consumption=150.0,
            time_of_day=time(14, 0),
            day_of_week=2,
            indoor_humidity=65.0,
            outdoor_humidity=80.0,
            humidity_differential=15.0
        )
        
        result = engine.calculate_offset(input_data)
        
        # Should show negative contribution in reason
        assert "humidity-adjusted (-0.3°C from indoor: 65.0%, outdoor: 80.0%, diff: 15.0%)" in result.reason
        
    def test_reason_excludes_humidity_contribution_when_too_small(self):
        """Test that reason string excludes humidity contribution when < 0.05°C."""
        engine = OffsetEngine(self.config)
        
        # Set up mock learner with tiny contribution
        mock_learner = Mock(spec=LightweightOffsetLearner)
        mock_learner._enhanced_samples = [{"sample": "data"}]
        mock_learner.predict.side_effect = [2.51, 2.50, 2.51]  # Main prediction, then contribution predictions
        
        # Mock get_statistics to exit calibration phase
        mock_stats = Mock()
        mock_stats.samples_collected = 15
        mock_learner.get_statistics.return_value = mock_stats
        
        engine._learner = mock_learner
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="auto",
            power_consumption=150.0,
            time_of_day=time(14, 0),
            day_of_week=2,
            indoor_humidity=65.0,
            outdoor_humidity=80.0,
            humidity_differential=15.0
        )
        
        result = engine.calculate_offset(input_data)
        
        # Should not show contribution in reason (too small)
        assert "humidity-adjusted" in result.reason  # Still show humidity info
        assert "°C from" not in result.reason  # But not the contribution amount
        
    def test_reason_handles_partial_humidity_data_in_contribution(self):
        """Test that reason string handles partial humidity data correctly in contribution display."""
        engine = OffsetEngine(self.config)
        
        # Set up mock learner with contribution
        mock_learner = Mock(spec=LightweightOffsetLearner)
        mock_learner._enhanced_samples = [{"sample": "data"}]
        mock_learner.predict.side_effect = [2.3, 2.0, 2.3]  # Main prediction, then contribution predictions
        
        # Mock get_statistics to exit calibration phase
        mock_stats = Mock()
        mock_stats.samples_collected = 15
        mock_learner.get_statistics.return_value = mock_stats
        
        engine._learner = mock_learner
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="auto",
            power_consumption=150.0,
            time_of_day=time(14, 0),
            day_of_week=2,
            indoor_humidity=60.0,
            outdoor_humidity=None,  # Only indoor humidity present
            humidity_differential=None
        )
        
        result = engine.calculate_offset(input_data)
        
        # Should show contribution with only available humidity data
        assert "humidity-adjusted (+0.3°C from indoor: 60.0%)" in result.reason
        
    def test_humidity_contribution_handles_learner_prediction_error(self):
        """Test that humidity contribution gracefully handles learner prediction errors."""
        engine = OffsetEngine(self.config)
        
        # Set up mock learner that fails on second call
        mock_learner = Mock(spec=LightweightOffsetLearner)
        mock_learner._enhanced_samples = [{"sample": "data"}]
        mock_learner.predict.side_effect = [2.5, Exception("Prediction failed")]
        engine._learner = mock_learner
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="auto",
            power_consumption=150.0,
            time_of_day=time(14, 0),
            day_of_week=2,
            indoor_humidity=65.0,
            outdoor_humidity=80.0
        )
        
        result = engine.calculate_offset(input_data)
        
        # Should not crash and should have 0 contribution
        assert engine.get_feature_contribution("humidity") == 0.0
        
    def test_humidity_contribution_caching_between_calls(self):
        """Test that humidity contribution is cached correctly between calls."""
        engine = OffsetEngine(self.config)
        
        # Set up mock learner
        mock_learner = Mock(spec=LightweightOffsetLearner)
        mock_learner._enhanced_samples = [{"sample": "data"}]
        mock_learner.predict.side_effect = [2.5, 2.2, 2.5]  # Main prediction, then contribution predictions
        
        # Mock get_statistics to exit calibration phase
        mock_stats = Mock()
        mock_stats.samples_collected = 15
        mock_learner.get_statistics.return_value = mock_stats
        
        engine._learner = mock_learner
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="auto",
            power_consumption=150.0,
            indoor_humidity=65.0,
            time_of_day=time(14, 0),
            day_of_week=2
        )
        
        # First calculation
        result1 = engine.calculate_offset(input_data)
        contribution1 = engine.get_feature_contribution("humidity")
        
        # Second call to get_feature_contribution should return same value
        contribution2 = engine.get_feature_contribution("humidity")
        
        assert contribution1 == contribution2
        assert contribution1 == pytest.approx(0.3, abs=0.01)
        
    def test_humidity_contribution_updates_with_new_calculation(self):
        """Test that humidity contribution updates with new offset calculations."""
        engine = OffsetEngine(self.config)
        
        # Set up mock learner
        mock_learner = Mock(spec=LightweightOffsetLearner)
        mock_learner._enhanced_samples = [{"sample": "data"}]
        
        # Mock get_statistics to exit calibration phase
        mock_stats = Mock()
        mock_stats.samples_collected = 15
        mock_learner.get_statistics.return_value = mock_stats
        
        engine._learner = mock_learner
        
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="auto",
            power_consumption=150.0,
            indoor_humidity=65.0,
            time_of_day=time(14, 0),
            day_of_week=2
        )
        
        # First calculation with +0.3°C contribution: main, without, with
        mock_learner.predict.side_effect = [2.5, 2.2, 2.5]
        result1 = engine.calculate_offset(input_data)
        contribution1 = engine.get_feature_contribution("humidity")
        
        # Second calculation with +0.5°C contribution: main, without, with
        mock_learner.predict.side_effect = [3.0, 2.5, 3.0]
        result2 = engine.calculate_offset(input_data)
        contribution2 = engine.get_feature_contribution("humidity")
        
        # Contribution should update
        assert contribution1 == pytest.approx(0.3, abs=0.01)
        assert contribution2 == pytest.approx(0.5, abs=0.01)
        assert contribution1 != contribution2