"""Test calibration phase functionality for stable state offset caching."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from custom_components.smart_climate.offset_engine import OffsetEngine, MIN_SAMPLES_FOR_ACTIVE_CONTROL
from custom_components.smart_climate.models import OffsetInput
from custom_components.smart_climate.const import (
    DEFAULT_POWER_IDLE_THRESHOLD,
    DEFAULT_POWER_MIN_THRESHOLD,
    DEFAULT_POWER_MAX_THRESHOLD,
)


class TestCalibrationPhase:
    """Test suite for calibration phase offset caching."""

    def test_stable_state_detection(self):
        """Test that stable state is detected when AC idle with converged temps."""
        # Arrange
        config = {
            "enable_learning": True,
            "power_idle_threshold": DEFAULT_POWER_IDLE_THRESHOLD,
            "power_sensor": "sensor.ac_power"  # Enable hysteresis
        }
        engine = OffsetEngine(config)
        
        # Mock learner to report insufficient samples
        engine._learner = Mock()
        engine._learner.get_statistics.return_value = Mock(samples_collected=5)  # < 10
        engine._learner._enhanced_samples = []
        
        # Create input with stable state conditions
        input_data = OffsetInput(
            ac_internal_temp=22.5,
            room_temp=21.0,  # 1.5°C difference (< 2°C threshold)
            outdoor_temp=None,
            mode="cool",
            power_consumption=10.0,  # Below idle threshold (50W)
            time_of_day=datetime.now().time(),
            day_of_week=datetime.now().weekday()
        )
        
        # Act
        result = engine.calculate_offset(input_data)
        
        # Assert
        assert engine._stable_calibration_offset is not None
        assert engine._stable_calibration_offset == 1.5  # ac_internal - room
        assert result.offset == 1.5
        assert "Calibration (Stable)" in result.reason
        assert "(5/10 samples)" in result.reason
        assert result.confidence == 0.2  # Low confidence during calibration

    def test_active_cooling_cached_offset(self):
        """Test that cached offset is used during active cooling."""
        # Arrange
        config = {
            "enable_learning": True,
            "power_idle_threshold": DEFAULT_POWER_IDLE_THRESHOLD,
            "power_sensor": "sensor.ac_power"
        }
        engine = OffsetEngine(config)
        
        # Mock learner to report insufficient samples
        engine._learner = Mock()
        engine._learner.get_statistics.return_value = Mock(samples_collected=7)
        engine._learner._enhanced_samples = []
        
        # Set a cached stable offset
        engine._stable_calibration_offset = -2.1
        
        # Create input with active cooling conditions
        input_data = OffsetInput(
            ac_internal_temp=15.0,  # Evaporator coil temperature
            room_temp=24.0,  # Big difference due to evaporator sensor
            outdoor_temp=None,
            mode="cool",
            power_consumption=800.0,  # High power (active cooling)
            time_of_day=datetime.now().time(),
            day_of_week=datetime.now().weekday()
        )
        
        # Act
        result = engine.calculate_offset(input_data)
        
        # Assert
        assert result.offset == -2.1  # Using cached offset, not current difference
        assert "Calibration (Active)" in result.reason
        assert "cached stable offset of -2.1°C" in result.reason
        assert result.confidence == 0.2

    def test_initial_run_no_cache(self):
        """Test temporary offset calculation on first run with no cache."""
        # Arrange
        config = {
            "enable_learning": True,
            "power_idle_threshold": DEFAULT_POWER_IDLE_THRESHOLD,
            "power_sensor": "sensor.ac_power"
        }
        engine = OffsetEngine(config)
        
        # Mock learner to report insufficient samples
        engine._learner = Mock()
        engine._learner.get_statistics.return_value = Mock(samples_collected=0)
        engine._learner._enhanced_samples = []
        
        # No cached offset (first run)
        assert engine._stable_calibration_offset is None
        
        # Create input with active cooling but no cache
        input_data = OffsetInput(
            ac_internal_temp=15.0,
            room_temp=24.0,
            outdoor_temp=None,
            mode="cool",
            power_consumption=800.0,  # High power
            time_of_day=datetime.now().time(),
            day_of_week=datetime.now().weekday()
        )
        
        # Act
        result = engine.calculate_offset(input_data)
        
        # Assert
        # Should use current difference as temporary offset
        assert result.offset == -5.0  # Clamped to max offset
        assert result.clamped == False  # The overall result is not marked as clamped
        assert "Calibration (Initial)" in result.reason
        assert "No cached offset" in result.reason
        assert "temporary offset of -5.0°C" in result.reason
        assert result.confidence == 0.2

    def test_calibration_exit(self):
        """Test that normal operation occurs after 10 samples collected."""
        # Arrange
        config = {
            "enable_learning": True,
            "power_idle_threshold": DEFAULT_POWER_IDLE_THRESHOLD,
            "power_sensor": "sensor.ac_power"
        }
        engine = OffsetEngine(config)
        
        # Mock learner to report sufficient samples
        engine._learner = Mock()
        engine._learner.get_statistics.return_value = Mock(samples_collected=10)  # >= 10
        engine._learner._enhanced_samples = [Mock()]  # Has samples
        engine._learner.predict.return_value = -1.8  # Learned offset
        
        # Create input data
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=None,
            mode="cool",
            power_consumption=100.0,
            time_of_day=datetime.now().time(),
            day_of_week=datetime.now().weekday()
        )
        
        # Act
        result = engine.calculate_offset(input_data)
        
        # Assert
        # Should use normal learning-based calculation
        assert "Calibration" not in result.reason
        assert result.confidence > 0.2  # Higher confidence after calibration
        # The exact offset will be a weighted combination

    def test_no_power_sensor(self):
        """Test graceful fallback when power sensor unavailable."""
        # Arrange
        config = {
            "enable_learning": True,
            # No power_sensor in config - hysteresis disabled
        }
        engine = OffsetEngine(config)
        
        # Mock learner to report insufficient samples
        engine._learner = Mock()
        engine._learner.get_statistics.return_value = Mock(samples_collected=3)
        engine._learner._enhanced_samples = []
        
        # Create input with no power data
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=21.5,
            outdoor_temp=None,
            mode="cool",
            power_consumption=None,  # No power data
            time_of_day=datetime.now().time(),
            day_of_week=datetime.now().weekday()
        )
        
        # Act
        result = engine.calculate_offset(input_data)
        
        # Assert
        # Should still work with temperature-based offset
        assert result.offset == 0.5
        assert "Calibration (Stable)" in result.reason
        assert "(3/10 samples)" in result.reason
        assert result.confidence == 0.2

    def test_stable_state_updates_cache(self):
        """Test that stable state detection updates the cached offset."""
        # Arrange
        config = {
            "enable_learning": True,
            "power_idle_threshold": DEFAULT_POWER_IDLE_THRESHOLD,
            "power_sensor": "sensor.ac_power"
        }
        engine = OffsetEngine(config)
        
        # Mock learner
        engine._learner = Mock()
        engine._learner.get_statistics.return_value = Mock(samples_collected=4)
        engine._learner._enhanced_samples = []
        
        # Set initial cached offset
        engine._stable_calibration_offset = -1.0
        
        # Create stable state with different offset
        input_data = OffsetInput(
            ac_internal_temp=22.8,
            room_temp=21.0,  # 1.8°C difference (< 2.0°C threshold)
            outdoor_temp=None,
            mode="cool",
            power_consumption=20.0,  # Idle
            time_of_day=datetime.now().time(),
            day_of_week=datetime.now().weekday()
        )
        
        # Act
        result = engine.calculate_offset(input_data)
        
        # Assert
        assert engine._stable_calibration_offset == pytest.approx(1.8, abs=0.001)  # Updated
        assert result.offset == pytest.approx(1.8, abs=0.001)
        assert "Updated offset to 1.8°C" in result.reason

    def test_unstable_state_uses_cache(self):
        """Test that unstable state (large temp diff) uses cached offset."""
        # Arrange
        config = {
            "enable_learning": True,
            "power_idle_threshold": DEFAULT_POWER_IDLE_THRESHOLD,
            "power_sensor": "sensor.ac_power"
        }
        engine = OffsetEngine(config)
        
        # Mock learner
        engine._learner = Mock()
        engine._learner.get_statistics.return_value = Mock(samples_collected=6)
        engine._learner._enhanced_samples = []
        
        # Set cached offset
        engine._stable_calibration_offset = -1.5
        
        # Create unstable state (large temp diff but low power)
        input_data = OffsetInput(
            ac_internal_temp=18.0,
            room_temp=24.0,  # 6°C difference (> 2°C threshold)
            outdoor_temp=None,
            mode="cool",
            power_consumption=30.0,  # Low power but unstable temps
            time_of_day=datetime.now().time(),
            day_of_week=datetime.now().weekday()
        )
        
        # Act
        result = engine.calculate_offset(input_data)
        
        # Assert
        assert result.offset == -1.5  # Using cached offset
        assert "Calibration (Active)" in result.reason
        assert "cached stable offset" in result.reason

    def test_reset_learning_clears_calibration_cache(self):
        """Test that reset_learning clears the calibration cache."""
        # Arrange
        config = {
            "enable_learning": True,
            "power_idle_threshold": DEFAULT_POWER_IDLE_THRESHOLD,
            "power_sensor": "sensor.ac_power"
        }
        engine = OffsetEngine(config)
        
        # Set cached offset
        engine._stable_calibration_offset = -2.5
        
        # Act
        engine.reset_learning()
        
        # Assert
        assert engine._stable_calibration_offset is None