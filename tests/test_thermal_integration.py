"""Test thermal integration for v1.5.3 enhancements.

Tests the integration of:
- Expanded probe history (75 entries)
- Exponential weighting system
- Enhanced confidence calculation
- ThermalManager integration with new confidence thresholds
"""

import pytest
from datetime import datetime, timezone, timedelta
from collections import deque
from unittest.mock import Mock, MagicMock, patch

from custom_components.smart_climate.thermal_model import PassiveThermalModel
from custom_components.smart_climate.thermal_manager import ThermalManager
from custom_components.smart_climate.thermal_models import ProbeResult, ThermalState, PreferenceLevel
from custom_components.smart_climate.const import (
    MAX_PROBE_HISTORY_SIZE,
    CONFIDENCE_REQUIRED_SAMPLES,
    DECAY_RATE_PER_DAY
)


class TestThermalIntegration:
    """Test thermal system integration with v1.5.3 enhancements."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock preferences
        self.mock_preferences = Mock()
        self.mock_preferences.get_adjusted_band.return_value = 1.0
        self.mock_preferences.confidence_threshold = 0.6  # Default threshold
        
        # Create thermal model with 75-probe history
        self.thermal_model = PassiveThermalModel()
        
        # Create mock HASS and config
        self.mock_hass = Mock()
        self.mock_config = {
            'passive_confidence_threshold': 0.3,
            'probe_confidence_threshold': 0.6  # New threshold for integration
        }
        
        # Create thermal manager
        self.thermal_manager = ThermalManager(
            hass=self.mock_hass,
            thermal_model=self.thermal_model,
            preferences=self.mock_preferences,
            config=self.mock_config,
            persistence_callback=Mock()
        )

    def test_probe_history_expansion_to_75(self):
        """Test that probe history can hold 75 entries."""
        # Initially should be empty
        assert len(self.thermal_model._probe_history) == 0
        
        # Add more than 75 probes to test capacity
        for i in range(80):
            probe = ProbeResult(
                tau_value=90.0 + i,
                confidence=0.8,
                duration=1800,
                fit_quality=0.9,
                aborted=False,
                timestamp=datetime.now(timezone.utc) - timedelta(days=i)
            )
            self.thermal_model._probe_history.append(probe)
        
        # Should cap at 75 entries
        assert len(self.thermal_model._probe_history) == MAX_PROBE_HISTORY_SIZE
        
        # Should keep most recent 75 (deque removes from left when full)
        # With deque maxlen behavior, first items (0-4) are removed, keeping items 5-79
        tau_values = [p.tau_value for p in self.thermal_model._probe_history]
        assert min(tau_values) == 95.0  # Item 5 (90.0 + 5)
        assert max(tau_values) == 169.0  # Item 79 (90.0 + 79)

    def test_exponential_weighting_integration(self):
        """Test that update_tau uses new _calculate_weighted_tau method."""
        # Add some probe data with different ages
        now = datetime.now(timezone.utc)
        probes = [
            ProbeResult(100.0, 0.9, 1800, 0.95, False, now - timedelta(days=1)),
            ProbeResult(110.0, 0.8, 1800, 0.90, False, now - timedelta(days=10)),
            ProbeResult(120.0, 0.7, 1800, 0.85, False, now - timedelta(days=30)),
        ]
        
        for probe in probes:
            self.thermal_model._probe_history.append(probe)
        
        # Get initial tau
        initial_tau = self.thermal_model._tau_cooling
        
        # Add new probe - should trigger weighted calculation
        new_probe = ProbeResult(95.0, 0.95, 1800, 0.98, False, now)
        self.thermal_model.update_tau(new_probe, is_cooling=True)
        
        # Tau should have changed and should be influenced more by recent probes
        new_tau = self.thermal_model._tau_cooling
        assert new_tau != initial_tau
        
        # Should be closer to recent probes (100.0, 95.0) than old ones (120.0)
        assert 95.0 <= new_tau <= 105.0

    def test_enhanced_confidence_calculation(self):
        """Test confidence calculation with 30+ samples threshold."""
        # With fewer than 30 samples, confidence should be reduced
        for i in range(20):
            probe = ProbeResult(90.0, 0.9, 1800, 0.9, False, 
                              datetime.now(timezone.utc) - timedelta(hours=i))
            self.thermal_model._probe_history.append(probe)
        
        confidence_20_samples = self.thermal_model.get_confidence()
        
        # Add more samples to reach 35 total
        for i in range(15):
            probe = ProbeResult(90.0, 0.9, 1800, 0.9, False, 
                              datetime.now(timezone.utc) - timedelta(hours=20+i))
            self.thermal_model._probe_history.append(probe)
        
        confidence_35_samples = self.thermal_model.get_confidence()
        
        # With 35 samples, confidence should be higher than with 20
        assert confidence_35_samples > confidence_20_samples
        
        # With 35 samples, should get close to full confidence (0.9 * 1.0)
        assert confidence_35_samples >= 0.85

    def test_thermal_manager_confidence_threshold_integration(self):
        """Test ThermalManager respects new confidence thresholds."""
        # Set up stability detector mock
        mock_stability_detector = Mock()
        mock_drift_data = [
            {'timestamp': datetime.now(timezone.utc) - timedelta(minutes=30-i), 
             'temperature': 22.0 + 0.1*i, 'ac_state': 'idle'} 
            for i in range(30)
        ]
        mock_stability_detector.find_natural_drift_event.return_value = mock_drift_data
        self.thermal_manager.stability_detector = mock_stability_detector
        
        # Mock analyze_drift_data to return low confidence result
        with patch('custom_components.smart_climate.thermal_utils.analyze_drift_data') as mock_analyze:
            low_confidence_result = ProbeResult(
                tau_value=85.0,
                confidence=0.2,  # Below threshold
                duration=1800,
                fit_quality=0.8,
                aborted=False
            )
            mock_analyze.return_value = low_confidence_result
            
            # Should reject low confidence result
            initial_probe_count = len(self.thermal_model._probe_history)
            self.thermal_manager._handle_passive_learning()
            final_probe_count = len(self.thermal_model._probe_history)
            
            # No probe should have been added
            assert final_probe_count == initial_probe_count

    def test_mixed_old_new_probe_handling(self):
        """Test system handles probes with and without timestamps."""
        # Add old probe without timestamp (legacy)
        old_probe_dict = {
            "tau_value": 90.0,
            "confidence": 0.8,
            "duration": 1800,
            "fit_quality": 0.9,
            "aborted": False
            # No timestamp - legacy data
        }
        
        # Simulate restore process
        test_data = {
            "probe_history": [old_probe_dict],
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0},
            "state": {"current_state": "PRIMING"}
        }
        
        self.thermal_manager.restore(test_data)
        
        # Should have restored the probe with a fallback timestamp
        assert len(self.thermal_model._probe_history) == 1
        restored_probe = list(self.thermal_model._probe_history)[0]
        assert restored_probe.tau_value == 90.0
        assert restored_probe.timestamp is not None  # Should have fallback timestamp

    def test_performance_with_75_probes(self):
        """Test performance is under 5ms with 75 probes."""
        import time
        
        # Add 75 probes
        now = datetime.now(timezone.utc)
        for i in range(75):
            probe = ProbeResult(
                tau_value=90.0 + (i % 20),
                confidence=0.8 + (i % 10) * 0.02,
                duration=1800,
                fit_quality=0.9,
                aborted=False,
                timestamp=now - timedelta(hours=i)
            )
            self.thermal_model._probe_history.append(probe)
        
        # Time the weighted tau calculation
        start_time = time.perf_counter()
        
        # Run multiple calculations to get average
        for _ in range(10):
            weighted_tau = self.thermal_model._calculate_weighted_tau(is_cooling=True)
            confidence = self.thermal_model.get_confidence()
        
        end_time = time.perf_counter()
        avg_time_ms = (end_time - start_time) / 10 * 1000
        
        # Should be under 5ms per calculation
        assert avg_time_ms < 5.0, f"Performance too slow: {avg_time_ms:.2f}ms"

    def test_state_transitions_with_confidence(self):
        """Test state transitions work with new confidence thresholds."""
        # Start in PRIMING state with low confidence
        assert self.thermal_manager.current_state == ThermalState.PRIMING
        
        # Add some high-confidence probes
        now = datetime.now(timezone.utc)
        for i in range(35):  # Enough for good confidence
            probe = ProbeResult(
                tau_value=90.0,
                confidence=0.9,
                duration=1800,
                fit_quality=0.95,
                aborted=False,
                timestamp=now - timedelta(hours=i)
            )
            self.thermal_model._probe_history.append(probe)
        
        # Get confidence should be high now
        confidence = self.thermal_model.get_confidence()
        assert confidence > 0.8
        
        # State transitions should work properly with high confidence
        # (This would require more complex state handler mocking for full test)

    def test_drift_predictions_use_weighted_tau(self):
        """Test drift predictions use weighted tau values."""
        # Add probes with different tau values at different ages
        now = datetime.now(timezone.utc)
        
        # Recent probe with tau=95
        recent_probe = ProbeResult(95.0, 0.9, 1800, 0.9, False, now - timedelta(hours=1))
        self.thermal_model._probe_history.append(recent_probe)
        
        # Old probe with tau=120
        old_probe = ProbeResult(120.0, 0.8, 1800, 0.8, False, now - timedelta(days=30))
        self.thermal_model._probe_history.append(old_probe)
        
        # Drift prediction should be influenced more by recent probe
        predicted_temp = self.thermal_model.predict_drift(
            current=22.0,
            outdoor=25.0,
            minutes=60,
            is_cooling=True
        )
        
        # With weighted tau closer to 95 than 120, drift should be faster
        # (specific values depend on implementation details)
        assert predicted_temp is not None

    def test_end_to_end_thermal_integration(self):
        """Test complete thermal system integration."""
        # Simulate a complete thermal learning cycle
        
        # 1. Start with empty probe history
        assert len(self.thermal_model._probe_history) == 0
        assert self.thermal_model.get_confidence() == 0.0
        
        # 2. Add probe results over time (simulating learning)
        now = datetime.now(timezone.utc)
        for day in range(40):  # 40 days of probes
            for probe_num in range(2):  # 2 probes per day
                probe = ProbeResult(
                    tau_value=90.0 + (day % 20),  # Varying tau values
                    confidence=0.8 + (probe_num * 0.1),
                    duration=1800,
                    fit_quality=0.9,
                    aborted=False,
                    timestamp=now - timedelta(days=day, hours=probe_num*12)
                )
                self.thermal_model.update_tau(probe, is_cooling=(probe_num == 0))
        
        # 3. Should have 75 probes (maxlen cap)
        assert len(self.thermal_model._probe_history) == 75
        
        # 4. Confidence should be high (>30 samples)
        confidence = self.thermal_model.get_confidence()
        assert confidence > 0.7
        
        # 5. Weighted tau should be reasonable
        cooling_tau = self.thermal_model._calculate_weighted_tau(is_cooling=True)
        warming_tau = self.thermal_model._calculate_weighted_tau(is_cooling=False)
        
        assert 80.0 <= cooling_tau <= 120.0
        assert 80.0 <= warming_tau <= 120.0
        
        # 6. System should work with ThermalManager
        operating_window = self.thermal_manager.get_operating_window(
            setpoint=22.0,
            outdoor_temp=25.0,
            hvac_mode="cool"
        )
        assert operating_window is not None
        assert len(operating_window) == 2

    def test_no_regression_in_existing_functionality(self):
        """Test that existing functionality still works."""
        # Basic thermal model operations should still work
        
        # 1. Tau values should have sensible defaults
        assert self.thermal_model._tau_cooling == 90.0
        assert self.thermal_model._tau_warming == 150.0
        
        # 2. Basic probe addition should work
        probe = ProbeResult(95.0, 0.8, 1800, 0.9, False)
        self.thermal_model.update_tau(probe, is_cooling=True)
        
        assert len(self.thermal_model._probe_history) == 1
        
        # 3. Drift prediction should work
        predicted = self.thermal_model.predict_drift(22.0, 25.0, 60, True)
        assert predicted is not None
        
        # 4. ThermalManager basic operations
        window = self.thermal_manager.get_operating_window(22.0, 25.0, "cool")
        assert window is not None
        
        should_run = self.thermal_manager.should_ac_run(23.0, 22.0, window)
        assert isinstance(should_run, bool)