"""ABOUTME: Unit tests for StabilityDetector class.
Tests the opportunistic calibration stability detection logic for thermal system."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from collections import deque

from custom_components.smart_climate.thermal_stability import StabilityDetector


class TestStabilityDetector:
    """Tests for StabilityDetector class - opportunistic calibration component."""

    def test_tracks_ac_idle_duration(self):
        """Test that StabilityDetector correctly tracks AC idle duration."""
        detector = StabilityDetector(idle_threshold_minutes=30, drift_threshold=0.1)
        
        # Start with AC running
        with patch('custom_components.smart_climate.thermal_stability.datetime') as mock_dt:
            start_time = datetime(2025, 8, 11, 10, 0, 0)
            mock_dt.now.return_value = start_time
            
            detector.update("cooling", 24.0)
            idle_duration = detector.get_idle_duration()
            assert idle_duration == timedelta(0), "AC running should have zero idle time"
            
            # Switch to idle
            mock_dt.now.return_value = start_time + timedelta(minutes=5)
            detector.update("idle", 24.0)
            
            # Check idle duration after 15 minutes
            mock_dt.now.return_value = start_time + timedelta(minutes=20)
            detector.update("idle", 24.0)
            idle_duration = detector.get_idle_duration()
            assert idle_duration == timedelta(minutes=15), "Should track idle time from first idle state"

    def test_maintains_temperature_history(self):
        """Test that StabilityDetector maintains temperature history correctly."""
        detector = StabilityDetector(idle_threshold_minutes=30, drift_threshold=0.1)
        
        # Add temperatures and verify history length
        temps = [24.0, 24.1, 24.2, 23.9, 24.0]
        for temp in temps:
            detector.update("idle", temp)
        
        assert len(detector._temperature_history) == 5, "Should store all temperatures"
        
        # Test maxlen=20 by adding more temperatures
        for i in range(20):
            detector.update("idle", 24.0 + i * 0.1)
        
        assert len(detector._temperature_history) == 20, "Should cap at maxlen=20"
        assert detector._temperature_history[-1][1] == 25.9, "Should keep most recent temperatures"

    def test_calculates_drift_correctly(self):
        """Test that StabilityDetector calculates temperature drift correctly."""
        detector = StabilityDetector(idle_threshold_minutes=30, drift_threshold=0.1)
        
        with patch('custom_components.smart_climate.thermal_stability.datetime') as mock_dt:
            base_time = datetime(2025, 8, 11, 10, 0, 0)
            
            # Add temperatures over 15 minutes: 0, 3, 6, 9, 12, 15 minutes
            temperatures = []
            for i in range(6):
                timestamp = base_time + timedelta(minutes=i * 3)
                temp = 24.0 + i * 0.02  # 24.0, 24.02, 24.04, 24.06, 24.08, 24.10
                mock_dt.now.return_value = timestamp
                detector.update("idle", temp)
                temperatures.append((timestamp, temp))
            
            # Last 10 minutes from 15-minute mark: entries from 6+ minutes onwards
            # Entries at 6min(24.04), 9min(24.06), 12min(24.08), 15min(24.10)
            # Expected drift = 24.10 - 24.04 = 0.06°C
            drift = detector.get_temperature_drift()
            expected_drift = 0.06  # Only entries from last 10 minutes
            assert abs(drift - expected_drift) < 0.01, f"Expected {expected_drift}°C drift, got {drift}°C"

    def test_detects_stability_conditions(self):
        """Test that StabilityDetector detects stable conditions for calibration."""
        detector = StabilityDetector(idle_threshold_minutes=30, drift_threshold=0.1)
        
        with patch('custom_components.smart_climate.thermal_stability.datetime') as mock_dt:
            base_time = datetime(2025, 8, 11, 10, 0, 0)
            
            # Test unstable - AC running
            mock_dt.now.return_value = base_time
            detector.update("cooling", 24.0)
            assert not detector.is_stable_for_calibration(), "Should be unstable when AC running"
            
            # Test unstable - recently idle (< 30 minutes)
            mock_dt.now.return_value = base_time + timedelta(minutes=5)
            detector.update("idle", 24.0)
            mock_dt.now.return_value = base_time + timedelta(minutes=25)
            detector.update("idle", 24.0)
            assert not detector.is_stable_for_calibration(), "Should be unstable with < 30 min idle"
            
            # Test unstable - enough idle time but too much drift
            mock_dt.now.return_value = base_time + timedelta(minutes=35)
            detector.update("idle", 24.2)  # 0.2°C drift over time
            assert not detector.is_stable_for_calibration(), "Should be unstable with high drift"
            
            # Test stable - enough idle time AND low drift
            # Reset with stable conditions
            detector = StabilityDetector(idle_threshold_minutes=30, drift_threshold=0.1)
            
            # Simulate 35 minutes of idle with minimal drift
            for i in range(12):  # 12 samples over 35 minutes
                mock_dt.now.return_value = base_time + timedelta(minutes=i * 3)
                temp = 24.0 + (i % 2) * 0.02  # Small oscillation ±0.02°C
                detector.update("idle", temp)
            
            mock_dt.now.return_value = base_time + timedelta(minutes=35)
            assert detector.is_stable_for_calibration(), "Should be stable with 35min idle and low drift"

    def test_handles_empty_history(self):
        """Test that StabilityDetector handles empty temperature history gracefully."""
        detector = StabilityDetector(idle_threshold_minutes=30, drift_threshold=0.1)
        
        # Test with empty history
        drift = detector.get_temperature_drift()
        assert drift == 0.0, "Should return zero drift with empty history"
        
        assert not detector.is_stable_for_calibration(), "Should be unstable with empty history"
        
        # Test with single temperature sample
        detector.update("idle", 24.0)
        drift = detector.get_temperature_drift()
        assert drift == 0.0, "Should return zero drift with single sample"

    def test_ac_state_change_resets_idle_timer(self):
        """Test that AC state changes from idle properly reset the idle timer."""
        detector = StabilityDetector(idle_threshold_minutes=30, drift_threshold=0.1)
        
        with patch('custom_components.smart_climate.thermal_stability.datetime') as mock_dt:
            base_time = datetime(2025, 8, 11, 10, 0, 0)
            
            # Start idle
            mock_dt.now.return_value = base_time
            detector.update("idle", 24.0)
            
            # 20 minutes of idle
            mock_dt.now.return_value = base_time + timedelta(minutes=20)
            detector.update("idle", 24.0)
            idle_duration = detector.get_idle_duration()
            assert idle_duration == timedelta(minutes=20)
            
            # AC turns on
            mock_dt.now.return_value = base_time + timedelta(minutes=22)
            detector.update("cooling", 24.0)
            idle_duration = detector.get_idle_duration()
            assert idle_duration == timedelta(0), "AC running should reset idle duration"
            
            # Back to idle - timer should restart
            mock_dt.now.return_value = base_time + timedelta(minutes=25)
            detector.update("idle", 24.0)
            
            # 10 minutes later
            mock_dt.now.return_value = base_time + timedelta(minutes=35)
            detector.update("idle", 24.0)
            idle_duration = detector.get_idle_duration()
            assert idle_duration == timedelta(minutes=10), "Should track new idle period"

    def test_drift_calculation_over_ten_minutes(self):
        """Test that drift calculation uses 10-minute window correctly."""
        detector = StabilityDetector(idle_threshold_minutes=30, drift_threshold=0.1)
        
        with patch('custom_components.smart_climate.thermal_stability.datetime') as mock_dt:
            base_time = datetime(2025, 8, 11, 10, 0, 0)
            
            # Add 20 minutes of data with increasing temperature
            for i in range(21):  # 0 to 20 minutes, every minute
                mock_dt.now.return_value = base_time + timedelta(minutes=i)
                temp = 24.0 + i * 0.01  # Linear increase: 0.2°C over 20 minutes
                detector.update("idle", temp)
            
            # Drift should be calculated over last 10 minutes only
            # Last 10 minutes: 24.10°C to 24.20°C = 0.1°C drift
            drift = detector.get_temperature_drift()
            expected_drift = 0.1  # 24.20 - 24.10
            assert abs(drift - expected_drift) < 0.01, f"Expected ~{expected_drift}°C drift, got {drift}°C"

    def test_configurable_thresholds(self):
        """Test that StabilityDetector respects configurable thresholds."""
        # Test custom idle threshold
        detector_45min = StabilityDetector(idle_threshold_minutes=45, drift_threshold=0.1)
        
        with patch('custom_components.smart_climate.thermal_stability.datetime') as mock_dt:
            base_time = datetime(2025, 8, 11, 10, 0, 0)
            
            mock_dt.now.return_value = base_time
            detector_45min.update("idle", 24.0)
            
            # 35 minutes idle - not enough for 45-minute threshold
            mock_dt.now.return_value = base_time + timedelta(minutes=35)
            detector_45min.update("idle", 24.0)
            assert not detector_45min.is_stable_for_calibration(), "Should require 45 minutes idle"
            
            # 50 minutes idle - enough for 45-minute threshold
            mock_dt.now.return_value = base_time + timedelta(minutes=50)
            detector_45min.update("idle", 24.0)
            assert detector_45min.is_stable_for_calibration(), "Should be stable after 50 minutes"
        
        # Test custom drift threshold
        detector_strict = StabilityDetector(idle_threshold_minutes=30, drift_threshold=0.1)
        
        with patch('custom_components.smart_climate.thermal_stability.datetime') as mock_dt:
            base_time = datetime(2025, 8, 11, 10, 0, 0)
            
            # 35 minutes idle with significant drift - exceeds 0.05°C threshold
            for i in range(12):
                mock_dt.now.return_value = base_time + timedelta(minutes=i * 3)
                temp = 24.0 + i * 0.01  # 0.11°C drift over entire period
                detector_strict.update("idle", temp)
            
            # Within last 10 minutes (from 25-35 min), we have samples at 27, 30, 33 min
            # Temps: 24.09, 24.10, 24.11 = 0.02°C drift (under 0.05 threshold)
            # Let's add a bigger drift in the 10-minute window
            
            # Add more samples with bigger drift in last 10 minutes
            detector_strict = StabilityDetector(idle_threshold_minutes=30, drift_threshold=0.1)
            for i in range(4):  # First 4 samples - establish idle time
                mock_dt.now.return_value = base_time + timedelta(minutes=i * 5)
                detector_strict.update("idle", 24.0)
            
            # Add samples in last 10 minutes with 0.08°C drift
            for i in range(4):
                mock_dt.now.return_value = base_time + timedelta(minutes=25 + i * 2)  # 25, 27, 29, 31 min
                temp = 24.0 + i * 0.027  # 0.08°C drift over 6 minutes
                detector_strict.update("idle", temp)
                
            mock_dt.now.return_value = base_time + timedelta(minutes=35)
            assert not detector_strict.is_stable_for_calibration(), "Should be unstable with 0.08°C drift (threshold 0.05°C)"