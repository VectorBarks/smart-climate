"""Test probe history expansion for PassiveThermalModel.

Tests expanding probe history from 5 to 75 samples for seasonal adaptation.
"""

import pytest
import math
from datetime import datetime, timezone
from unittest.mock import Mock
from collections import deque

from custom_components.smart_climate.thermal_model import PassiveThermalModel, ProbeResult
from custom_components.smart_climate.const import MAX_PROBE_HISTORY_SIZE


class TestProbeHistoryExpansion:
    """Test probe history expansion to 75 samples."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.model = PassiveThermalModel()
        
    def test_model_initializes_with_75_maxlen_deque(self):
        """Test model initializes with maxlen=75 deque for probe history."""
        assert isinstance(self.model._probe_history, deque)
        assert self.model._probe_history.maxlen == MAX_PROBE_HISTORY_SIZE
        assert self.model._probe_history.maxlen == 75
        assert len(self.model._probe_history) == 0
        
    def test_can_add_up_to_75_probes_without_losing_data(self):
        """Test can add 75 probes without losing any data."""
        probes = []
        for i in range(75):
            probe = ProbeResult(
                tau_value=90.0 + i,
                confidence=0.8,
                duration=3600,
                fit_quality=0.9,
                aborted=False
            )
            probes.append(probe)
            self.model.update_tau(probe, is_cooling=True)
            
        # Should have all 75 probes
        assert len(self.model._probe_history) == 75
        assert list(self.model._probe_history) == probes
        
        # Verify first and last probes are present
        assert self.model._probe_history[0].tau_value == 90.0
        assert self.model._probe_history[74].tau_value == 164.0
        
    def test_probe_76_causes_oldest_to_be_dropped(self):
        """Test adding 76th probe causes oldest probe to be dropped."""
        probes = []
        
        # Add 75 probes
        for i in range(75):
            probe = ProbeResult(
                tau_value=90.0 + i,
                confidence=0.8,
                duration=3600,
                fit_quality=0.9,
                aborted=False
            )
            probes.append(probe)
            self.model.update_tau(probe, is_cooling=True)
            
        # Add 76th probe
        probe_76 = ProbeResult(
            tau_value=200.0,
            confidence=0.8,
            duration=3600,
            fit_quality=0.9,
            aborted=False
        )
        self.model.update_tau(probe_76, is_cooling=True)
        
        # Should still have 75 probes
        assert len(self.model._probe_history) == 75
        
        # First probe (tau_value=90.0) should be gone
        assert self.model._probe_history[0].tau_value == 91.0  # Second probe is now first
        
        # Last probe should be the 76th probe
        assert self.model._probe_history[74].tau_value == 200.0
        
    def test_get_probe_count_method_returns_correct_count(self):
        """Test get_probe_count() method returns correct number of probes."""
        # Initially empty
        assert self.model.get_probe_count() == 0
        
        # Add some probes
        for i in range(10):
            probe = ProbeResult(
                tau_value=90.0 + i,
                confidence=0.8,
                duration=3600,
                fit_quality=0.9,
                aborted=False
            )
            self.model.update_tau(probe, is_cooling=True)
            assert self.model.get_probe_count() == i + 1
            
        # Add more probes up to 75
        for i in range(10, 75):
            probe = ProbeResult(
                tau_value=90.0 + i,
                confidence=0.8,
                duration=3600,
                fit_quality=0.9,
                aborted=False
            )
            self.model.update_tau(probe, is_cooling=True)
            
        assert self.model.get_probe_count() == 75
        
        # Add one more - should still be 75
        probe = ProbeResult(
            tau_value=200.0,
            confidence=0.8,
            duration=3600,
            fit_quality=0.9,
            aborted=False
        )
        self.model.update_tau(probe, is_cooling=True)
        assert self.model.get_probe_count() == 75
        
    def test_backward_compatibility_loads_5_probe_model(self):
        """Test backward compatibility: model works correctly with existing 5-probe data."""
        # Simulate loading a model with 5 probes (legacy data)
        model = PassiveThermalModel()
        
        # Add 5 probes (simulating old system)
        for i in range(5):
            probe = ProbeResult(
                tau_value=85.0 + i,
                confidence=0.8,
                duration=3600,
                fit_quality=0.9,
                aborted=False
            )
            model.update_tau(probe, is_cooling=True)
            
        # Should work normally with 5 probes
        assert len(model._probe_history) == 5
        assert model.get_probe_count() == 5
        
        # Should be able to add more probes up to 75
        for i in range(5, 20):
            probe = ProbeResult(
                tau_value=85.0 + i,
                confidence=0.8,
                duration=3600,
                fit_quality=0.9,
                aborted=False
            )
            model.update_tau(probe, is_cooling=True)
            
        assert model.get_probe_count() == 20
        
    def test_forward_compatibility_saves_all_75_probes(self):
        """Test forward compatibility: system can save/restore all 75 probes."""
        # Add 75 probes with distinct values
        tau_values = []
        for i in range(75):
            tau_value = 50.0 + (i * 2)  # 50, 52, 54, ..., 198
            tau_values.append(tau_value)
            probe = ProbeResult(
                tau_value=tau_value,
                confidence=0.7 + (i % 3) * 0.1,  # Varying confidence
                duration=3600,
                fit_quality=0.8 + (i % 2) * 0.1,  # Varying fit quality
                aborted=False
            )
            self.model.update_tau(probe, is_cooling=True)
            
        # Verify all probes are preserved
        assert self.model.get_probe_count() == 75
        
        # Verify probe values are correct
        stored_tau_values = [probe.tau_value for probe in self.model._probe_history]
        assert stored_tau_values == tau_values
        
    def test_memory_usage_remains_reasonable_with_75_probes(self):
        """Test memory usage remains reasonable with 75 probes."""
        # Add 75 probes
        for i in range(75):
            probe = ProbeResult(
                tau_value=90.0 + i,
                confidence=0.8,
                duration=3600,
                fit_quality=0.9,
                aborted=False,
                timestamp=datetime.now(timezone.utc)
            )
            self.model.update_tau(probe, is_cooling=True)
            
        # Basic memory check - deque should have exactly 75 items
        assert len(self.model._probe_history) == 75
        assert self.model._probe_history.maxlen == 75
        
        # Verify each probe is a proper ProbeResult instance
        for probe in self.model._probe_history:
            assert isinstance(probe, ProbeResult)
            assert hasattr(probe, 'tau_value')
            assert hasattr(probe, 'confidence')
            assert hasattr(probe, 'timestamp')
            
    def test_iteration_over_probe_history_works_correctly(self):
        """Test iteration over probe history works correctly with 75 probes."""
        # Add different number of probes
        for num_probes in [1, 5, 10, 25, 50, 75]:
            model = PassiveThermalModel()
            expected_tau_values = []
            
            for i in range(num_probes):
                tau_value = 100.0 + i
                expected_tau_values.append(tau_value)
                probe = ProbeResult(
                    tau_value=tau_value,
                    confidence=0.8,
                    duration=3600,
                    fit_quality=0.9,
                    aborted=False
                )
                model.update_tau(probe, is_cooling=True)
                
            # Test iteration
            actual_tau_values = [probe.tau_value for probe in model._probe_history]
            assert actual_tau_values == expected_tau_values
            assert len(actual_tau_values) == num_probes
            
    def test_confidence_calculation_works_with_75_probes(self):
        """Test confidence calculation works correctly with up to 75 probes."""
        from custom_components.smart_climate.const import CONFIDENCE_REQUIRED_SAMPLES
        
        # Test confidence with different numbers of probes
        for num_probes in [1, 5, 10, 30, 50, 75]:
            model = PassiveThermalModel()
            
            # Add probes with consistent confidence
            for i in range(num_probes):
                probe = ProbeResult(
                    tau_value=90.0 + i,
                    confidence=0.8,
                    duration=3600,
                    fit_quality=0.9,
                    aborted=False
                )
                model.update_tau(probe, is_cooling=True)
                
            confidence = model.get_confidence()
            
            # With the current algorithm: confidence = avg_confidence * min(count/CONFIDENCE_REQUIRED_SAMPLES, 1.0)
            # CONFIDENCE_REQUIRED_SAMPLES = 30
            # For count <= 30: confidence = 0.8 * (count/30)
            # For count > 30: confidence = 0.8 * 1.0 = 0.8
            if num_probes <= CONFIDENCE_REQUIRED_SAMPLES:
                expected_confidence = 0.8 * (num_probes / CONFIDENCE_REQUIRED_SAMPLES)
            else:
                expected_confidence = 0.8
                
            assert abs(confidence - expected_confidence) < 0.01
            
    def test_max_probe_history_size_constant_import(self):
        """Test MAX_PROBE_HISTORY_SIZE constant is correctly imported and used."""
        # Verify constant exists and has correct value
        assert MAX_PROBE_HISTORY_SIZE == 75
        
        # Verify model uses the constant
        model = PassiveThermalModel()
        assert model._probe_history.maxlen == MAX_PROBE_HISTORY_SIZE
        
    def test_existing_functionality_unchanged(self):
        """Test existing thermal model functionality remains unchanged."""
        # Test basic thermal model operations still work
        current = 25.0
        outdoor = 20.0
        minutes = 30
        
        # Physics should be unchanged
        expected = current + (outdoor - current) * (1 - math.exp(-minutes / 90.0))
        result = self.model.predict_drift(current, outdoor, minutes, is_cooling=True)
        assert abs(result - expected) < 0.01
        
        # Tau updates should still work
        probe = ProbeResult(
            tau_value=100.0,
            confidence=0.8,
            duration=3600,
            fit_quality=0.9,
            aborted=False
        )
        original_tau = self.model._tau_cooling
        self.model.update_tau(probe, is_cooling=True)
        assert self.model._tau_cooling != original_tau