"""ABOUTME: Integration test for StabilityDetector + thermal_utils passive learning workflow.
Tests the complete pipeline from HVAC state tracking to thermal analysis."""

import pytest
from custom_components.smart_climate.thermal_stability import StabilityDetector
from custom_components.smart_climate.thermal_utils import analyze_drift_data


class TestPassiveLearningIntegration:
    """Test integration between StabilityDetector and thermal_utils for passive learning."""
    
    def test_complete_passive_learning_workflow(self):
        """Test the complete workflow from HVAC tracking to thermal analysis."""
        detector = StabilityDetector()
        
        base_ts = 1000.0
        
        # Phase 1: Cooling phase
        for i in range(5):
            detector.add_reading(base_ts + i*60, 20.0, "cooling")
            
        # Phase 2: Off phase with exponential temperature drift
        for i in range(20):
            ts = base_ts + (5+i)*60
            # Simulate exponential decay: temp approaches 22°C asymptotically
            temp = 22.0 - 2.0 * (0.95 ** i)  # Exponential approach
            detector.add_reading(ts, temp, "off")
            
        # Phase 3: Detect drift event
        drift_data = detector.find_natural_drift_event()
        assert drift_data is not None, "Should detect valid cooling->off transition"
        assert len(drift_data) == 20, "Should return all off-phase data"
        
        # Verify data structure
        for ts, temp in drift_data:
            assert isinstance(ts, (int, float)), "Timestamp should be numeric"
            assert isinstance(temp, (int, float)), "Temperature should be numeric"
            
        # Phase 4: Analyze with thermal_utils
        result = analyze_drift_data(drift_data, is_passive=True)
        
        if result:  # Only test if scipy is available
            assert result.tau_value > 0, "Tau should be positive"
            assert 0 <= result.confidence <= 0.5, "Passive confidence should be scaled to ≤0.5"
            assert result.duration > 0, "Duration should be positive"
            assert 0 <= result.fit_quality <= 1, "Fit quality should be 0-1"
            assert not result.aborted, "Analysis should not be aborted"
            
        # Phase 5: Verify reanalysis prevention
        drift_data_2 = detector.find_natural_drift_event()
        assert drift_data_2 is None, "Should prevent reanalysis of same event"
        
    def test_workflow_with_heating_transition(self):
        """Test workflow with heating->off transition."""
        detector = StabilityDetector()
        
        base_ts = 1000.0
        
        # Heating phase
        for i in range(5):
            detector.add_reading(base_ts + i*60, 25.0, "heating")
            
        # Off phase - temperature falls
        for i in range(16):
            ts = base_ts + (5+i)*60
            temp = 23.0 + 2.0 * (0.9 ** i)  # Exponential decay toward 23°C
            detector.add_reading(ts, temp, "off")
            
        # Should find heating->off transition
        drift_data = detector.find_natural_drift_event()
        assert drift_data is not None
        assert len(drift_data) == 16
        
        # Duration should be 15*60 = 900+ seconds (meets minimum)
        duration = drift_data[-1][0] - drift_data[0][0]
        assert duration >= 900
        
    def test_workflow_insufficient_data(self):
        """Test workflow when insufficient data is present."""
        detector = StabilityDetector()
        
        base_ts = 1000.0
        
        # Add only 8 off readings after cooling (< 10 minimum)
        for i in range(3):
            detector.add_reading(base_ts + i*60, 20.0, "cooling")
        for i in range(8):
            detector.add_reading(base_ts + (3+i)*60, 20.0 + i*0.1, "off")
            
        drift_data = detector.find_natural_drift_event()
        assert drift_data is None, "Should reject insufficient data"
        
    def test_workflow_insufficient_duration(self):
        """Test workflow when drift duration is too short."""
        detector = StabilityDetector()
        
        base_ts = 1000.0
        
        # Cooling phase
        for i in range(5):
            detector.add_reading(base_ts + i*60, 20.0, "cooling")
            
        # Off phase - only 10 minutes (600s < 900s minimum)
        for i in range(10):
            ts = base_ts + (5+i)*60  # 60s intervals = 9*60 = 540s duration
            detector.add_reading(ts, 20.0 + i*0.1, "off")
            
        drift_data = detector.find_natural_drift_event()
        assert drift_data is None, "Should reject insufficient duration"
        
    def test_workflow_no_transitions(self):
        """Test workflow when no valid transitions exist."""
        detector = StabilityDetector()
        
        base_ts = 1000.0
        
        # All readings in same state
        for i in range(25):
            detector.add_reading(base_ts + i*60, 20.0 + i*0.05, "off")
            
        drift_data = detector.find_natural_drift_event()
        assert drift_data is None, "Should find no transitions"
        
    def test_workflow_multiple_events(self):
        """Test workflow with multiple drift events."""
        detector = StabilityDetector()
        
        base_ts = 1000.0
        
        # First event: cooling -> off
        for i in range(5):
            detector.add_reading(base_ts + i*60, 20.0, "cooling")
        for i in range(20):
            ts = base_ts + (5+i)*60
            detector.add_reading(ts, 20.0 + i*0.05, "off")
            
        # Get first event
        drift_data_1 = detector.find_natural_drift_event()
        assert drift_data_1 is not None
        assert len(drift_data_1) == 20
        
        # Add second event: heating -> off
        for i in range(5):
            ts = base_ts + (25+i)*60
            detector.add_reading(ts, 24.0, "heating")
        for i in range(18):
            ts = base_ts + (30+i)*60
            detector.add_reading(ts, 24.0 - i*0.03, "off")
            
        # Should detect new event
        drift_data_2 = detector.find_natural_drift_event()
        assert drift_data_2 is not None
        assert len(drift_data_2) == 18
        
        # Data should be from second event
        assert drift_data_2[0][1] == 24.0  # First temp from heating->off event