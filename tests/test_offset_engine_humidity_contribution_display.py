"""Test humidity contribution display in offset reasons."""

import pytest
from unittest.mock import MagicMock, patch

from custom_components.smart_climate.models import OffsetInput, OffsetResult
from custom_components.smart_climate.offset_engine import OffsetEngine


@pytest.fixture
def mock_hass():
    """Create mock Home Assistant."""
    hass = MagicMock()
    hass.loop = MagicMock()
    return hass


@pytest.fixture
def basic_config():
    """Basic configuration for OffsetEngine."""
    return {
        "max_offset": 5.0,
        "enable_learning": True,
        "enable_seasonal": False,
        "enable_forecasting": False,
        "enable_outlier_detection": False,
    }


@pytest.fixture
def offset_engine(mock_hass, basic_config):
    """Create OffsetEngine instance with mocked dependencies."""
    with patch('custom_components.smart_climate.offset_engine.EnhancedLightweightOffsetLearner'):
        engine = OffsetEngine(config=basic_config)
        # Initialize humidity contribution for testing
        engine._last_humidity_contribution = 0.0
        return engine


def create_humidity_input(indoor=65.0, outdoor=80.0, diff=15.0):
    """Create OffsetInput with humidity data."""
    return OffsetInput(
        ac_internal_temp=20.0,
        room_temp=22.0,
        outdoor_temp=30.0,
        mode="none",
        power_consumption=1500.0,
        time_of_day=12,
        day_of_week=1,
        indoor_humidity=indoor,
        outdoor_humidity=outdoor,
        humidity_differential=diff,
    )


def setup_learning_engine(engine):
    """Configure engine for learning mode with humidity."""
    # Mock learner to have enhanced samples and return result
    engine._learner._enhanced_samples = [{"dummy": "data"}]  # Simulate having data
    engine._learner.predict_offset_with_confidence = MagicMock(
        return_value=(2.0, 0.85)
    )
    # Note: predict method is set individually in each test
    
    # Mock statistics to show enough samples to exit calibration phase
    from collections import namedtuple
    MockStats = namedtuple('Statistics', ['samples_collected'])
    engine._learner.get_statistics = MagicMock(return_value=MockStats(samples_collected=15))
    
    # Set learning enabled and calibration disabled to ensure proper path
    engine._enable_learning = True
    engine._stable_calibration_offset = None  # Force out of calibration mode
    
    # Mock humidity contribution calculation to prevent overwriting manually set values
    engine._calculate_humidity_contribution = MagicMock()


class TestHumidityContributionDisplay:
    """Test humidity contribution display in offset reasons."""

    def test_zero_contribution_shows_celsius(self, offset_engine):
        """Test that 0.0°C contribution is displayed."""
        input_data = create_humidity_input()
        setup_learning_engine(offset_engine)
        
        # Mock same predictions to create zero contribution
        offset_engine._learner.predict = MagicMock(side_effect=[2.0, 2.0])  # Same values = no contribution
        
        result = offset_engine.calculate_offset(input_data)
        
        # Should show "0.0°C" even when contribution is zero
        assert "humidity-adjusted (0.0°C from" in result.reason
        assert "indoor: 65.0%" in result.reason
        assert "outdoor: 80.0%" in result.reason
        assert "diff: 15.0%" in result.reason

    def test_small_positive_contribution_shows_celsius(self, offset_engine):
        """Test that small positive contribution (0.01°C) is displayed."""
        input_data = create_humidity_input()
        setup_learning_engine(offset_engine)
        
        # Manually set the humidity contribution after setup
        offset_engine._last_humidity_contribution = 0.01
        
        # Mock prediction for main learning path
        offset_engine._learner.predict = MagicMock(return_value=2.0)
        
        result = offset_engine.calculate_offset(input_data)
        
        # The main fix: should show "+0.0°C" even for small values (now always shows °C)
        assert "humidity-adjusted (+0.0°C from" in result.reason
        assert "indoor: 65.0%" in result.reason

    def test_small_negative_contribution_shows_celsius(self, offset_engine):
        """Test that small negative contribution (-0.02°C) is displayed."""
        input_data = create_humidity_input()
        setup_learning_engine(offset_engine)
        
        # Manually set the humidity contribution after setup
        offset_engine._last_humidity_contribution = -0.02
        
        # Mock prediction for main learning path
        offset_engine._learner.predict = MagicMock(return_value=2.0)
        
        result = offset_engine.calculate_offset(input_data)
        
        # Should show "-0.0°C" (rounded) for small negative values
        assert "humidity-adjusted (-0.0°C from" in result.reason
        assert "indoor: 65.0%" in result.reason

    def test_regular_positive_contribution_shows_celsius(self, offset_engine):
        """Test that regular positive contribution (0.3°C) is displayed."""
        input_data = create_humidity_input()
        setup_learning_engine(offset_engine)
        
        # Manually set the humidity contribution after setup
        offset_engine._last_humidity_contribution = 0.3
        
        # Mock prediction for main learning path
        offset_engine._learner.predict = MagicMock(return_value=2.0)
        
        result = offset_engine.calculate_offset(input_data)
        
        # Should show "+0.3°C" for regular positive values
        assert "humidity-adjusted (+0.3°C from" in result.reason
        assert "indoor: 65.0%" in result.reason

    def test_regular_negative_contribution_shows_celsius(self, offset_engine):
        """Test that regular negative contribution (-0.3°C) is displayed."""
        input_data = create_humidity_input()
        setup_learning_engine(offset_engine)
        
        # Manually set the humidity contribution after setup
        offset_engine._last_humidity_contribution = -0.3
        
        # Mock prediction for main learning path
        offset_engine._learner.predict = MagicMock(return_value=2.0)
        
        result = offset_engine.calculate_offset(input_data)
        
        # Should show "-0.3°C" for regular negative values
        assert "humidity-adjusted (-0.3°C from" in result.reason
        assert "indoor: 65.0%" in result.reason

    def test_no_humidity_data_no_contribution_display(self, offset_engine):
        """Test that no contribution is shown when no humidity data."""
        input_data = OffsetInput(
            ac_internal_temp=20.0,
            room_temp=22.0,
            outdoor_temp=30.0,
            mode="none",
            power_consumption=1500.0,
            time_of_day=12,
            day_of_week=1,
            # No humidity data
        )
        
        setup_learning_engine(offset_engine)
        
        # Mock prediction for regular learning path
        offset_engine._learner.predict = MagicMock(return_value=2.0)
        
        result = offset_engine.calculate_offset(input_data)
        
        # Should not show humidity-adjusted when no humidity data
        assert "humidity-adjusted" not in result.reason

    def test_partial_humidity_data_shows_available(self, offset_engine):
        """Test that partial humidity data shows only available values."""
        input_data = OffsetInput(
            ac_internal_temp=20.0,
            room_temp=22.0,
            outdoor_temp=30.0,
            mode="none",
            power_consumption=1500.0,
            time_of_day=12,
            day_of_week=1,
            indoor_humidity=65.0,
            # No outdoor humidity or differential
        )
        
        setup_learning_engine(offset_engine)
        
        # Manually set the humidity contribution after setup
        offset_engine._last_humidity_contribution = 0.2
        
        # Mock prediction for main learning path
        offset_engine._learner.predict = MagicMock(return_value=2.0)
        
        result = offset_engine.calculate_offset(input_data)
        
        # Should show contribution with only available humidity data
        assert "humidity-adjusted (+0.2°C from indoor: 65.0%)" in result.reason
        assert "outdoor:" not in result.reason
        assert "diff:" not in result.reason

    def test_zero_humidity_values_not_displayed(self, offset_engine):
        """Test that zero humidity values are not displayed."""
        input_data = OffsetInput(
            ac_internal_temp=20.0,
            room_temp=22.0,
            outdoor_temp=30.0,
            mode="none",
            power_consumption=1500.0,
            time_of_day=12,
            day_of_week=1,
            indoor_humidity=0.0,  # Zero value should not be displayed
            outdoor_humidity=80.0,
            humidity_differential=0.0,  # Zero value should not be displayed
        )
        
        setup_learning_engine(offset_engine)
        
        # Manually set the humidity contribution after setup
        offset_engine._last_humidity_contribution = 0.1
        
        # Mock prediction for main learning path
        offset_engine._learner.predict = MagicMock(return_value=2.0)
        
        result = offset_engine.calculate_offset(input_data)
        
        # Should show contribution with only non-zero humidity data
        assert "humidity-adjusted (+0.1°C from outdoor: 80.0%)" in result.reason
        assert "indoor:" not in result.reason
        assert "diff:" not in result.reason