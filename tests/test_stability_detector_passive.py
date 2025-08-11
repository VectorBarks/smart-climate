"""ABOUTME: Tests for StabilityDetector passive learning extensions.
Tests HVAC state tracking and natural drift event detection."""

import pytest
from datetime import datetime, timedelta
from collections import deque

from custom_components.smart_climate.thermal_stability import StabilityDetector


class TestStabilityDetectorPassiveExtensions:
    """Test passive learning extensions to StabilityDetector."""
    
    def test_init_adds_passive_learning_attributes(self):
        """Test that __init__ adds new attributes for passive learning."""
        detector = StabilityDetector()
        
        # Check new attributes exist
        assert hasattr(detector, '_history')
        assert hasattr(detector, '_MIN_DRIFT_DURATION_S')  
        assert hasattr(detector, '_last_event_ts')
        
        # Check initial values
        assert isinstance(detector._history, deque)
        assert detector._history.maxlen == 240  # 4 hours at 1-minute intervals
        assert detector._MIN_DRIFT_DURATION_S == 900  # 15 minutes
        assert detector._last_event_ts == 0.0
        
    def test_add_reading_accepts_hvac_state(self):
        """Test that add_reading method accepts timestamp, temp, hvac_state."""
        detector = StabilityDetector()
        
        timestamp = 1000.0
        temp = 22.5
        hvac_state = "cooling"
        
        # This should not raise an exception
        detector.add_reading(timestamp, temp, hvac_state)
        
        # Check data was stored
        assert len(detector._history) == 1
        entry = detector._history[0]
        assert entry['ts'] == timestamp
        assert entry['temp'] == temp
        assert entry['hvac'] == hvac_state
        
    def test_add_reading_stores_multiple_entries(self):
        """Test that add_reading stores multiple entries in history."""
        detector = StabilityDetector()
        
        # Add multiple readings
        readings = [
            (1000.0, 22.0, "cooling"),
            (1060.0, 21.8, "cooling"), 
            (1120.0, 21.5, "off"),
            (1180.0, 21.7, "off"),
        ]
        
        for timestamp, temp, hvac_state in readings:
            detector.add_reading(timestamp, temp, hvac_state)
            
        assert len(detector._history) == 4
        
        # Verify entries are stored correctly
        for i, (ts, temp, hvac) in enumerate(readings):
            entry = detector._history[i]
            assert entry['ts'] == ts
            assert entry['temp'] == temp
            assert entry['hvac'] == hvac
            
    def test_find_natural_drift_event_returns_none_insufficient_data(self):
        """Test find_natural_drift_event returns None with insufficient data.""" 
        detector = StabilityDetector()
        
        # No data
        result = detector.find_natural_drift_event()
        assert result is None
        
        # Insufficient data (< 10 points after transition)
        base_ts = 1000.0
        for i in range(5):
            detector.add_reading(base_ts + i*60, 22.0, "cooling")
        for i in range(3):  # Only 3 off readings
            detector.add_reading(base_ts + (5+i)*60, 22.0 + i*0.1, "off")
            
        result = detector.find_natural_drift_event()
        assert result is None
        
    def test_find_natural_drift_event_returns_none_no_transition(self):
        """Test find_natural_drift_event returns None when no valid transition found."""
        detector = StabilityDetector()
        
        # All readings in same state
        base_ts = 1000.0
        for i in range(20):
            detector.add_reading(base_ts + i*60, 22.0 + i*0.05, "off")
            
        result = detector.find_natural_drift_event()
        assert result is None
        
    def test_find_natural_drift_event_returns_none_insufficient_duration(self):
        """Test find_natural_drift_event returns None for drift < 15 minutes."""
        detector = StabilityDetector()
        
        base_ts = 1000.0
        
        # Cooling phase
        for i in range(5):
            detector.add_reading(base_ts + i*60, 22.0, "cooling")
            
        # Off phase - but only 10 minutes (600 seconds)
        for i in range(10):
            detector.add_reading(base_ts + (5+i)*60, 22.0 + i*0.1, "off")
            
        result = detector.find_natural_drift_event()
        assert result is None
        
    def test_find_natural_drift_event_finds_valid_cooling_off_transition(self):
        """Test find_natural_drift_event detects valid cooling->off transition."""
        detector = StabilityDetector()
        
        base_ts = 1000.0
        
        # Cooling phase (5 minutes)
        for i in range(5):
            detector.add_reading(base_ts + i*60, 20.0, "cooling")
            
        # Off phase (20 minutes = 1200 seconds > 900 minimum)
        off_data = []
        for i in range(20):
            ts = base_ts + (5+i)*60  
            temp = 20.0 + i * 0.1  # Temperature rising
            detector.add_reading(ts, temp, "off")
            off_data.append((ts, temp))
            
        result = detector.find_natural_drift_event()
        
        # Should return the off phase data
        assert result is not None
        assert len(result) == 20
        
        # Check data matches what we added
        for i, (ts, temp) in enumerate(result):
            assert ts == off_data[i][0]
            assert temp == off_data[i][1]
            
    def test_find_natural_drift_event_finds_valid_heating_off_transition(self):
        """Test find_natural_drift_event detects valid heating->off transition."""
        detector = StabilityDetector()
        
        base_ts = 1000.0
        
        # Heating phase
        for i in range(5):
            detector.add_reading(base_ts + i*60, 25.0, "heating")
            
        # Off phase (16 minutes = 960 seconds > 900 minimum)
        off_data = []
        for i in range(16):
            ts = base_ts + (5+i)*60
            temp = 25.0 - i * 0.05  # Temperature falling  
            detector.add_reading(ts, temp, "off")
            off_data.append((ts, temp))
            
        result = detector.find_natural_drift_event()
        
        assert result is not None
        assert len(result) == 16
        
        # Verify data correctness
        for i, (ts, temp) in enumerate(result):
            assert ts == off_data[i][0]
            assert temp == off_data[i][1]
            
    def test_find_natural_drift_event_prevents_reanalysis_same_event(self):
        """Test find_natural_drift_event prevents reanalyzing same event."""
        detector = StabilityDetector()
        
        base_ts = 1000.0
        
        # Cooling phase
        for i in range(5):
            detector.add_reading(base_ts + i*60, 22.0, "cooling") 
            
        # Off phase (20 minutes)
        for i in range(20):
            detector.add_reading(base_ts + (5+i)*60, 22.0 + i*0.1, "off")
            
        # First call should return data
        result1 = detector.find_natural_drift_event()
        assert result1 is not None
        assert len(result1) == 20
        
        # Second call should return None (already analyzed)
        result2 = detector.find_natural_drift_event()
        assert result2 is None
        
    def test_find_natural_drift_event_analyzes_new_events(self):
        """Test find_natural_drift_event analyzes new events after first one."""
        detector = StabilityDetector()
        
        base_ts = 1000.0
        
        # First event: cooling -> off
        for i in range(5):
            detector.add_reading(base_ts + i*60, 22.0, "cooling")
        for i in range(20):
            detector.add_reading(base_ts + (5+i)*60, 22.0 + i*0.1, "off")
            
        # Analyze first event 
        result1 = detector.find_natural_drift_event()
        assert result1 is not None
        
        # Add new data: off -> heating -> off
        for i in range(5):
            detector.add_reading(base_ts + (25+i)*60, 23.0, "heating")
        for i in range(20):
            detector.add_reading(base_ts + (30+i)*60, 23.0 - i*0.05, "off")
            
        # Should find the new event
        result2 = detector.find_natural_drift_event()
        assert result2 is not None
        assert len(result2) == 20
        
        # Temperatures should be from the new event
        assert result2[0][1] == 23.0  # First temp of new off phase
        
    def test_backward_compatibility_existing_methods(self):
        """Test that existing StabilityDetector methods still work."""
        detector = StabilityDetector(idle_threshold_minutes=45, drift_threshold=0.2)
        
        # Original update method should still work
        detector.update("cooling", 22.0)
        detector.update("idle", 22.1)
        
        # Original methods should still work
        idle_duration = detector.get_idle_duration()
        assert isinstance(idle_duration, timedelta)
        
        temp_drift = detector.get_temperature_drift()
        assert isinstance(temp_drift, float)
        
        is_stable = detector.is_stable_for_calibration()
        assert isinstance(is_stable, bool)
        
        # Should have both old and new history structures
        assert hasattr(detector, '_temperature_history')  # Old
        assert hasattr(detector, '_history')  # New