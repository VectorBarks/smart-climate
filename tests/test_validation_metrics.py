"""Tests for ValidationMetricsManager."""
import pytest
import statistics
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock
from typing import List, Dict, Any

from custom_components.smart_climate.validation_metrics import ValidationMetricsManager
from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    return Mock(spec=HomeAssistant)


@pytest.fixture
def validation_manager(mock_hass):
    """Create a ValidationMetricsManager instance."""
    return ValidationMetricsManager(mock_hass, "climate.test_thermostat")


class TestValidationMetricsManagerStructure:
    """Test ValidationMetricsManager class structure."""

    def test_initialization(self, validation_manager, mock_hass):
        """Test proper initialization of ValidationMetricsManager."""
        assert validation_manager._hass is mock_hass
        assert validation_manager._entity_id == "climate.test_thermostat"
        assert isinstance(validation_manager._prediction_errors, list)
        assert isinstance(validation_manager._overshoot_events, list)
        assert isinstance(validation_manager._cycle_efficiency_data, list)
        assert len(validation_manager._prediction_errors) == 0
        assert len(validation_manager._overshoot_events) == 0
        assert len(validation_manager._cycle_efficiency_data) == 0

    def test_required_methods_exist(self, validation_manager):
        """Test all required methods exist."""
        assert hasattr(validation_manager, 'record_prediction_error')
        assert callable(validation_manager.record_prediction_error)
        
        assert hasattr(validation_manager, 'record_temperature_overshoot')
        assert callable(validation_manager.record_temperature_overshoot)
        
        assert hasattr(validation_manager, 'record_hvac_cycle')
        assert callable(validation_manager.record_hvac_cycle)
        
        assert hasattr(validation_manager, 'get_prediction_error_sensor_data')
        assert callable(validation_manager.get_prediction_error_sensor_data)
        
        assert hasattr(validation_manager, 'get_setpoint_overshoot_sensor_data')
        assert callable(validation_manager.get_setpoint_overshoot_sensor_data)
        
        assert hasattr(validation_manager, 'get_cycle_efficiency_sensor_data')
        assert callable(validation_manager.get_cycle_efficiency_sensor_data)


class TestPredictionErrorTracking:
    """Test prediction error calculation and tracking."""

    def test_record_single_prediction_error(self, validation_manager):
        """Test recording a single prediction error."""
        predicted_drift = 2.5
        actual_drift = 2.2
        
        validation_manager.record_prediction_error(predicted_drift, actual_drift)
        
        assert len(validation_manager._prediction_errors) == 1
        error_record = validation_manager._prediction_errors[0]
        assert error_record["mae"] == abs(predicted_drift - actual_drift)
        assert error_record["predicted"] == predicted_drift
        assert error_record["actual"] == actual_drift
        assert "timestamp" in error_record
        assert isinstance(error_record["timestamp"], datetime)

    def test_record_multiple_prediction_errors(self, validation_manager):
        """Test recording multiple prediction errors."""
        test_cases = [
            (2.5, 2.2),  # MAE = 0.3
            (1.8, 2.1),  # MAE = 0.3
            (3.0, 2.5),  # MAE = 0.5
        ]
        
        for predicted, actual in test_cases:
            validation_manager.record_prediction_error(predicted, actual)
        
        assert len(validation_manager._prediction_errors) == 3
        
        # Check MAE calculations
        expected_maes = [0.3, 0.3, 0.5]
        for i, expected_mae in enumerate(expected_maes):
            assert abs(validation_manager._prediction_errors[i]["mae"] - expected_mae) < 0.001

    def test_prediction_error_data_retention_7_days(self, validation_manager):
        """Test that prediction errors older than 7 days are cleaned up."""
        now = datetime.now(timezone.utc)
        
        # Add old error (8 days ago)
        old_error = {
            "timestamp": now - timedelta(days=8),
            "mae": 0.5,
            "predicted": 2.0,
            "actual": 1.5
        }
        validation_manager._prediction_errors.append(old_error)
        
        # Add recent error
        validation_manager.record_prediction_error(2.5, 2.2)
        
        # Only the recent error should remain
        assert len(validation_manager._prediction_errors) == 1
        assert validation_manager._prediction_errors[0]["mae"] == 0.3

    def test_get_prediction_error_sensor_data_empty(self, validation_manager):
        """Test prediction error sensor data when no data available."""
        sensor_data = validation_manager.get_prediction_error_sensor_data()
        
        assert sensor_data["state"] is None
        assert sensor_data["attributes"] == {}

    def test_get_prediction_error_sensor_data_with_data(self, validation_manager):
        """Test prediction error sensor data generation with data."""
        # Add some test data
        test_errors = [0.2, 0.4, 0.3, 0.5, 0.1]
        for i, mae_val in enumerate(test_errors):
            validation_manager._prediction_errors.append({
                "timestamp": datetime.now(timezone.utc),
                "mae": mae_val,
                "predicted": 2.0 + mae_val,
                "actual": 2.0
            })
        
        sensor_data = validation_manager.get_prediction_error_sensor_data()
        
        expected_mae = statistics.mean(test_errors)
        
        assert abs(sensor_data["state"] - expected_mae) < 0.001
        assert sensor_data["attributes"]["unit_of_measurement"] == "°C"
        assert sensor_data["attributes"]["friendly_name"] == "Thermal Prediction Error"
        assert sensor_data["attributes"]["device_class"] == "temperature"
        assert sensor_data["attributes"]["sample_count"] == 5
        assert sensor_data["attributes"]["target_mae"] == 0.5
        assert sensor_data["attributes"]["within_target"] == (expected_mae <= 0.5)
        assert "daily_mae" in sensor_data["attributes"]
        assert "trend" in sensor_data["attributes"]

    def test_prediction_error_trend_calculation(self, validation_manager):
        """Test trend calculation for prediction errors."""
        # Test improving trend (errors getting smaller)
        improving_errors = [0.8, 0.6, 0.4, 0.3, 0.2]
        for mae_val in improving_errors:
            validation_manager._prediction_errors.append({
                "timestamp": datetime.now(timezone.utc),
                "mae": mae_val,
                "predicted": 2.0,
                "actual": 2.0
            })
        
        sensor_data = validation_manager.get_prediction_error_sensor_data()
        trend = validation_manager._calculate_trend(improving_errors)
        
        assert trend == "Improving"

    def test_daily_mae_calculation(self, validation_manager):
        """Test daily MAE calculation over multiple days."""
        now = datetime.now(timezone.utc)
        
        # Add errors for different days
        for day_offset in range(7):
            timestamp = now - timedelta(days=day_offset)
            mae_val = 0.1 + (day_offset * 0.1)  # Varying MAE by day
            validation_manager._prediction_errors.append({
                "timestamp": timestamp,
                "mae": mae_val,
                "predicted": 2.0,
                "actual": 2.0
            })
        
        daily_mae = validation_manager._calculate_daily_mae()
        
        # Should have up to 7 days of data
        assert isinstance(daily_mae, list)
        assert len(daily_mae) <= 7


class TestTemperatureOvershoot:
    """Test temperature overshoot recording and analysis."""

    def test_record_temperature_overshoot(self, validation_manager):
        """Test recording a temperature overshoot event."""
        setpoint = 24.0
        actual = 26.0
        comfort_band = 1.5
        
        validation_manager.record_temperature_overshoot(setpoint, actual, comfort_band)
        
        assert len(validation_manager._overshoot_events) == 1
        
        overshoot = validation_manager._overshoot_events[0]
        assert overshoot["setpoint"] == setpoint
        assert overshoot["actual"] == actual
        assert overshoot["comfort_band"] == comfort_band
        assert overshoot["overshoot_amount"] == actual - (setpoint + comfort_band)
        assert "timestamp" in overshoot
        assert isinstance(overshoot["timestamp"], datetime)

    def test_record_multiple_overshoot_events(self, validation_manager):
        """Test recording multiple overshoot events."""
        test_cases = [
            (24.0, 26.0, 1.5),  # Overshoot = 0.5°C
            (22.0, 24.5, 1.0),  # Overshoot = 1.5°C
            (25.0, 26.2, 1.0),  # Overshoot = 0.2°C
        ]
        
        for setpoint, actual, comfort_band in test_cases:
            validation_manager.record_temperature_overshoot(setpoint, actual, comfort_band)
        
        assert len(validation_manager._overshoot_events) == 3
        
        # Check overshoot calculations
        expected_overshoots = [0.5, 1.5, 0.2]
        for i, expected_overshoot in enumerate(expected_overshoots):
            actual_overshoot = validation_manager._overshoot_events[i]["overshoot_amount"]
            assert abs(actual_overshoot - expected_overshoot) < 0.001

    def test_overshoot_data_retention_24_hours(self, validation_manager):
        """Test that overshoot events older than 24 hours are cleaned up."""
        now = datetime.now(timezone.utc)
        
        # Add old overshoot (25 hours ago)
        old_overshoot = {
            "timestamp": now - timedelta(hours=25),
            "setpoint": 24.0,
            "actual": 26.0,
            "comfort_band": 1.5,
            "overshoot_amount": 0.5
        }
        validation_manager._overshoot_events.append(old_overshoot)
        
        # Add recent overshoot
        validation_manager.record_temperature_overshoot(24.0, 26.2, 1.5)
        
        # Only the recent overshoot should remain
        assert len(validation_manager._overshoot_events) == 1
        assert abs(validation_manager._overshoot_events[0]["overshoot_amount"] - 0.7) < 0.001

    def test_get_setpoint_overshoot_sensor_data_empty(self, validation_manager):
        """Test setpoint overshoot sensor data when no data available."""
        sensor_data = validation_manager.get_setpoint_overshoot_sensor_data()
        
        assert sensor_data["state"] == 0.0
        assert sensor_data["attributes"]["overshoot_events_today"] == 0
        assert sensor_data["attributes"]["max_overshoot_today"] == 0.0
        assert sensor_data["attributes"]["average_overshoot"] == 0.0

    def test_get_setpoint_overshoot_sensor_data_with_data(self, validation_manager):
        """Test setpoint overshoot sensor data generation with data."""
        now = datetime.now(timezone.utc)
        
        # Add overshoot events for testing
        overshoot_amounts = [0.5, 1.2, 0.8, 0.3]
        for amount in overshoot_amounts:
            validation_manager._overshoot_events.append({
                "timestamp": now,
                "setpoint": 24.0,
                "actual": 24.0 + 1.5 + amount,  # setpoint + comfort_band + overshoot
                "comfort_band": 1.5,
                "overshoot_amount": amount
            })
        
        sensor_data = validation_manager.get_setpoint_overshoot_sensor_data()
        
        # Test state (percentage of time outside comfort band)
        # For this test, we'll assume all readings are overshoots
        assert sensor_data["state"] >= 0.0
        
        assert sensor_data["attributes"]["overshoot_events_today"] == 4
        assert sensor_data["attributes"]["max_overshoot_today"] == max(overshoot_amounts)
        
        expected_avg = statistics.mean(overshoot_amounts)
        assert abs(sensor_data["attributes"]["average_overshoot"] - expected_avg) < 0.001
        assert sensor_data["attributes"]["comfort_band_size"] == 1.5


class TestHVACCycleEfficiency:
    """Test HVAC cycle efficiency metrics."""

    def test_record_hvac_on_cycle(self, validation_manager):
        """Test recording an HVAC on cycle."""
        duration_minutes = 15
        is_on_cycle = True
        
        validation_manager.record_hvac_cycle(duration_minutes, is_on_cycle)
        
        assert len(validation_manager._cycle_efficiency_data) == 1
        
        cycle = validation_manager._cycle_efficiency_data[0]
        assert cycle["duration_minutes"] == duration_minutes
        assert cycle["is_on_cycle"] == is_on_cycle
        assert "timestamp" in cycle
        assert isinstance(cycle["timestamp"], datetime)

    def test_record_hvac_off_cycle(self, validation_manager):
        """Test recording an HVAC off cycle."""
        duration_minutes = 45
        is_on_cycle = False
        
        validation_manager.record_hvac_cycle(duration_minutes, is_on_cycle)
        
        assert len(validation_manager._cycle_efficiency_data) == 1
        
        cycle = validation_manager._cycle_efficiency_data[0]
        assert cycle["duration_minutes"] == duration_minutes
        assert cycle["is_on_cycle"] == is_on_cycle

    def test_record_multiple_hvac_cycles(self, validation_manager):
        """Test recording multiple HVAC cycles."""
        test_cycles = [
            (12, True),   # Short on cycle
            (35, False),  # Normal off cycle  
            (18, True),   # Normal on cycle
            (60, False),  # Long off cycle
            (8, True),    # Very short on cycle (inefficient)
        ]
        
        for duration, is_on in test_cycles:
            validation_manager.record_hvac_cycle(duration, is_on)
        
        assert len(validation_manager._cycle_efficiency_data) == 5

    def test_cycle_data_retention_7_days(self, validation_manager):
        """Test that cycle data older than 7 days is cleaned up."""
        now = datetime.now(timezone.utc)
        
        # Add old cycle (8 days ago)
        old_cycle = {
            "timestamp": now - timedelta(days=8),
            "duration_minutes": 15,
            "is_on_cycle": True
        }
        validation_manager._cycle_efficiency_data.append(old_cycle)
        
        # Add recent cycle
        validation_manager.record_hvac_cycle(20, True)
        
        # Only the recent cycle should remain
        assert len(validation_manager._cycle_efficiency_data) == 1
        assert validation_manager._cycle_efficiency_data[0]["duration_minutes"] == 20

    def test_get_cycle_efficiency_sensor_data_empty(self, validation_manager):
        """Test cycle efficiency sensor data when no data available."""
        sensor_data = validation_manager.get_cycle_efficiency_sensor_data()
        
        assert sensor_data["state"] == 0
        assert sensor_data["attributes"]["average_on_cycle_minutes"] == 0.0
        assert sensor_data["attributes"]["average_off_cycle_minutes"] == 0.0
        assert sensor_data["attributes"]["short_cycle_count"] == 0
        assert sensor_data["attributes"]["efficiency_trend"] == "Stable"

    def test_get_cycle_efficiency_sensor_data_with_data(self, validation_manager):
        """Test cycle efficiency sensor data generation with data."""
        # Add test cycle data
        test_cycles = [
            (15, True),   # On cycle
            (45, False),  # Off cycle
            (18, True),   # On cycle
            (50, False),  # Off cycle
            (8, True),    # Short on cycle (<10 min = inefficient)
            (40, False),  # Off cycle
            (20, True),   # On cycle
        ]
        
        for duration, is_on in test_cycles:
            validation_manager.record_hvac_cycle(duration, is_on)
        
        sensor_data = validation_manager.get_cycle_efficiency_sensor_data()
        
        # Calculate expected values
        on_cycles = [15, 18, 8, 20]
        off_cycles = [45, 50, 40]
        short_cycles = [8]  # Cycles < 10 minutes
        
        expected_avg_on = statistics.mean(on_cycles)
        expected_avg_off = statistics.mean(off_cycles)
        expected_short_count = len(short_cycles)
        
        # Efficiency score calculation (0-100)
        # Higher on/off cycle durations = better efficiency
        # Fewer short cycles = better efficiency
        expected_efficiency = validation_manager._calculate_efficiency_score(
            expected_avg_on, expected_avg_off, expected_short_count, len(test_cycles)
        )
        
        assert sensor_data["state"] == expected_efficiency
        assert abs(sensor_data["attributes"]["average_on_cycle_minutes"] - expected_avg_on) < 0.001
        assert abs(sensor_data["attributes"]["average_off_cycle_minutes"] - expected_avg_off) < 0.001
        assert sensor_data["attributes"]["short_cycle_count"] == expected_short_count
        assert "efficiency_trend" in sensor_data["attributes"]

    def test_efficiency_score_calculation(self, validation_manager):
        """Test efficiency score calculation logic."""
        # Test perfect efficiency (long cycles, no short cycles)
        perfect_score = validation_manager._calculate_efficiency_score(
            avg_on=25.0, avg_off=60.0, short_cycle_count=0, total_cycles=10
        )
        assert perfect_score == 100
        
        # Test poor efficiency (short cycles, many inefficient cycles)
        poor_score = validation_manager._calculate_efficiency_score(
            avg_on=5.0, avg_off=15.0, short_cycle_count=8, total_cycles=10
        )
        assert poor_score < 50

    def test_efficiency_trend_calculation(self, validation_manager):
        """Test efficiency trend calculation."""
        # Test improving trend
        recent_data = [
            {"efficiency": 60, "timestamp": datetime.now(timezone.utc)},
            {"efficiency": 70, "timestamp": datetime.now(timezone.utc)},
            {"efficiency": 80, "timestamp": datetime.now(timezone.utc)},
        ]
        
        trend = validation_manager._calculate_efficiency_trend(recent_data)
        assert trend == "Improving"
        
        # Test degrading trend
        degrading_data = [
            {"efficiency": 80, "timestamp": datetime.now(timezone.utc)},
            {"efficiency": 70, "timestamp": datetime.now(timezone.utc)},
            {"efficiency": 60, "timestamp": datetime.now(timezone.utc)},
        ]
        
        trend = validation_manager._calculate_efficiency_trend(degrading_data)
        assert trend == "Degrading"
        
        # Test stable trend
        stable_data = [
            {"efficiency": 75, "timestamp": datetime.now(timezone.utc)},
            {"efficiency": 74, "timestamp": datetime.now(timezone.utc)},
            {"efficiency": 76, "timestamp": datetime.now(timezone.utc)},
        ]
        
        trend = validation_manager._calculate_efficiency_trend(stable_data)
        assert trend == "Stable"


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling."""

    def test_prediction_error_with_zero_values(self, validation_manager):
        """Test prediction error handling with zero values."""
        validation_manager.record_prediction_error(0.0, 0.0)
        
        assert len(validation_manager._prediction_errors) == 1
        assert validation_manager._prediction_errors[0]["mae"] == 0.0

    def test_prediction_error_with_negative_values(self, validation_manager):
        """Test prediction error handling with negative values."""
        validation_manager.record_prediction_error(-1.5, -2.0)
        
        assert len(validation_manager._prediction_errors) == 1
        assert validation_manager._prediction_errors[0]["mae"] == 0.5

    def test_overshoot_with_no_actual_overshoot(self, validation_manager):
        """Test overshoot recording when temperature is within comfort band."""
        setpoint = 24.0
        actual = 24.5  # Within comfort band
        comfort_band = 1.5
        
        validation_manager.record_temperature_overshoot(setpoint, actual, comfort_band)
        
        assert len(validation_manager._overshoot_events) == 1
        overshoot_amount = validation_manager._overshoot_events[0]["overshoot_amount"]
        assert overshoot_amount < 0  # Negative overshoot means within band

    def test_hvac_cycle_with_zero_duration(self, validation_manager):
        """Test HVAC cycle recording with zero duration."""
        validation_manager.record_hvac_cycle(0, True)
        
        assert len(validation_manager._cycle_efficiency_data) == 1
        assert validation_manager._cycle_efficiency_data[0]["duration_minutes"] == 0

    def test_sensor_data_with_extreme_values(self, validation_manager):
        """Test sensor data generation with extreme values."""
        # Add extreme prediction errors
        validation_manager.record_prediction_error(100.0, -100.0)  # MAE = 200
        
        sensor_data = validation_manager.get_prediction_error_sensor_data()
        assert sensor_data["state"] == 200.0
        assert not sensor_data["attributes"]["within_target"]  # Way above 0.5°C target

    def test_data_cleanup_preserves_recent_data(self, validation_manager):
        """Test that data cleanup only removes old data, preserves recent data."""
        now = datetime.now(timezone.utc)
        
        # Add mix of old and recent data
        old_time = now - timedelta(days=8)
        recent_time = now - timedelta(hours=1)
        
        # Old prediction error (should be removed)
        validation_manager._prediction_errors.append({
            "timestamp": old_time,
            "mae": 0.8,
            "predicted": 2.0,
            "actual": 1.2
        })
        
        # Recent prediction error (should be kept)
        validation_manager._prediction_errors.append({
            "timestamp": recent_time,
            "mae": 0.3,
            "predicted": 2.0,
            "actual": 1.7
        })
        
        # Trigger cleanup by adding new error
        validation_manager.record_prediction_error(2.5, 2.2)
        
        # Should have 2 entries (recent + new), old one removed
        assert len(validation_manager._prediction_errors) == 2
        
        # Verify recent data is preserved
        maes = [e["mae"] for e in validation_manager._prediction_errors]
        assert 0.3 in maes  # Recent data preserved
        assert 0.8 not in maes  # Old data removed


class TestStatisticalCalculations:
    """Test statistical calculations and data aggregation."""

    def test_mae_calculation_accuracy(self, validation_manager):
        """Test Mean Absolute Error calculation accuracy."""
        # Test data with known MAE
        test_data = [
            (2.0, 2.3),  # MAE = 0.3
            (1.5, 1.2),  # MAE = 0.3
            (3.0, 2.5),  # MAE = 0.5
            (2.5, 3.0),  # MAE = 0.5
        ]
        
        for predicted, actual in test_data:
            validation_manager.record_prediction_error(predicted, actual)
        
        sensor_data = validation_manager.get_prediction_error_sensor_data()
        
        expected_mae = (0.3 + 0.3 + 0.5 + 0.5) / 4  # = 0.4
        assert abs(sensor_data["state"] - expected_mae) < 0.001

    def test_overshoot_percentage_calculation(self, validation_manager):
        """Test overshoot percentage calculation."""
        # For accurate percentage testing, we need to simulate
        # time-based sampling where some readings are overshoots
        # and others are within the comfort band
        
        # This would typically be calculated based on
        # total time outside comfort band / total time * 100
        # For now, test that the method exists and returns valid range
        
        validation_manager.record_temperature_overshoot(24.0, 26.0, 1.5)
        sensor_data = validation_manager.get_setpoint_overshoot_sensor_data()
        
        # State should be a percentage between 0-100
        assert 0.0 <= sensor_data["state"] <= 100.0

    def test_efficiency_score_bounds(self, validation_manager):
        """Test that efficiency score stays within 0-100 bounds."""
        # Test with extreme values
        validation_manager.record_hvac_cycle(1, True)    # Very short on cycle
        validation_manager.record_hvac_cycle(1, False)   # Very short off cycle
        
        sensor_data = validation_manager.get_cycle_efficiency_sensor_data()
        
        # Efficiency score should be between 0-100
        assert 0 <= sensor_data["state"] <= 100

    def test_trend_calculation_with_insufficient_data(self, validation_manager):
        """Test trend calculation when there's insufficient data."""
        # Add single data point
        validation_manager.record_prediction_error(2.0, 1.8)
        
        sensor_data = validation_manager.get_prediction_error_sensor_data()
        
        # With insufficient data, trend should default to "Stable"
        assert sensor_data["attributes"]["trend"] == "Stable"