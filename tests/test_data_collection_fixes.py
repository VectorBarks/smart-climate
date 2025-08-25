"""Test data collection fixes for Smart Climate Control.

Tests for critical data collection issues:
1. OffsetEngine learning enabled by default
2. analyze_drift_data outdoor_temp parameter and ProbeResult population
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock

from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.thermal_utils import analyze_drift_data
from custom_components.smart_climate.thermal_models import ProbeResult
from custom_components.smart_climate.thermal_manager import ThermalManager


class TestOffsetEngineLearningDefault:
    """Test that OffsetEngine learning is enabled by default."""
    
    def test_learning_enabled_by_default_empty_config(self):
        """Test learning is enabled with empty configuration."""
        config = {}
        engine = OffsetEngine(config)
        
        # CRITICAL: Learning should be enabled by default for new installs
        assert engine.is_learning_enabled() is True
        assert engine._enable_learning is True
    
    def test_learning_enabled_by_default_minimal_config(self):
        """Test learning is enabled with minimal configuration."""
        config = {
            "max_offset": 3.0,
            "ml_enabled": True
        }
        engine = OffsetEngine(config)
        
        # Should still be enabled by default
        assert engine.is_learning_enabled() is True
        assert engine._enable_learning is True
    
    def test_learning_can_be_explicitly_disabled(self):
        """Test learning can still be explicitly disabled if needed."""
        config = {
            "enable_learning": False
        }
        engine = OffsetEngine(config)
        
        # Explicit false should still work
        assert engine.is_learning_enabled() is False
        assert engine._enable_learning is False
    
    def test_learning_can_be_explicitly_enabled(self):
        """Test learning can be explicitly enabled."""
        config = {
            "enable_learning": True
        }
        engine = OffsetEngine(config)
        
        # Explicit true should work
        assert engine.is_learning_enabled() is True
        assert engine._enable_learning is True


class TestAnalyzeDriftDataOutdoorTemp:
    """Test analyze_drift_data function with outdoor temperature support."""
    
    def create_test_drift_data(self, tau_actual=1800, noise_level=0.0):
        """Create test drift data for thermal analysis."""
        import numpy as np
        from custom_components.smart_climate.thermal_utils import exponential_decay
        
        # Generate realistic thermal drift data
        T_initial = 22.0
        T_final = 25.0
        times = np.linspace(0, 3600, 50)  # 1 hour of data, 50 points
        
        data = []
        for t in times:
            temp = exponential_decay(t, T_final, T_initial, tau_actual)
            if noise_level > 0:
                temp += np.random.normal(0, noise_level)  # Add noise
            data.append((t, temp))
        
        return data
    
    def test_analyze_drift_data_without_outdoor_temp(self):
        """Test analyze_drift_data works without outdoor_temp parameter (backward compatibility)."""
        data = self.create_test_drift_data(tau_actual=1800)
        
        # Original signature should still work
        result = analyze_drift_data(data, is_passive=False)
        
        assert result is not None
        assert isinstance(result, ProbeResult)
        assert result.outdoor_temp is None  # Should be None when not provided
        assert result.tau_value > 0
        assert 0.0 <= result.confidence <= 1.0
    
    def test_analyze_drift_data_with_outdoor_temp(self):
        """Test analyze_drift_data accepts outdoor_temp parameter."""
        data = self.create_test_drift_data(tau_actual=1800)
        outdoor_temp = 15.5
        
        # New signature with outdoor_temp parameter
        result = analyze_drift_data(data, is_passive=False, outdoor_temp=outdoor_temp)
        
        assert result is not None
        assert isinstance(result, ProbeResult)
        assert result.outdoor_temp == outdoor_temp  # Should be populated
        assert result.tau_value > 0
        assert 0.0 <= result.confidence <= 1.0
    
    def test_analyze_drift_data_with_none_outdoor_temp(self):
        """Test analyze_drift_data handles None outdoor_temp gracefully."""
        data = self.create_test_drift_data(tau_actual=1800)
        
        # None outdoor_temp should be handled gracefully
        result = analyze_drift_data(data, is_passive=False, outdoor_temp=None)
        
        assert result is not None
        assert isinstance(result, ProbeResult)
        assert result.outdoor_temp is None
        assert result.tau_value > 0
        assert 0.0 <= result.confidence <= 1.0
    
    def test_analyze_drift_data_passive_with_outdoor_temp(self):
        """Test passive learning with outdoor temperature data."""
        data = self.create_test_drift_data(tau_actual=1200)  # 20 minutes
        outdoor_temp = 30.2
        
        result = analyze_drift_data(data, is_passive=True, outdoor_temp=outdoor_temp)
        
        assert result is not None
        assert isinstance(result, ProbeResult)
        assert result.outdoor_temp == outdoor_temp
        assert result.confidence < 1.0  # Passive should have reduced confidence
        assert result.tau_value > 0
    
    def test_probe_result_outdoor_temp_field_exists(self):
        """Test ProbeResult has outdoor_temp field with correct default."""
        # Test direct ProbeResult creation
        result = ProbeResult(
            tau_value=1500.0,
            confidence=0.85,
            duration=3600,
            fit_quality=0.92,
            aborted=False,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Default outdoor_temp should be None
        assert hasattr(result, 'outdoor_temp')
        assert result.outdoor_temp is None
        
        # Test with outdoor_temp provided
        result_with_outdoor = ProbeResult(
            tau_value=1500.0,
            confidence=0.85,
            duration=3600,
            fit_quality=0.92,
            aborted=False,
            timestamp=datetime.now(timezone.utc),
            outdoor_temp=28.5
        )
        
        assert result_with_outdoor.outdoor_temp == 28.5


class TestThermalManagerPassiveLearningOutdoorTemp:
    """Test ThermalManager passes outdoor_temp to passive learning analysis."""
    
    def create_mock_thermal_manager(self):
        """Create a mock thermal manager for testing."""
        mock_hass = Mock()
        mock_thermal_model = Mock()
        mock_preferences = Mock()
        
        # Create real ThermalManager instance
        thermal_manager = ThermalManager(
            hass=mock_hass,
            thermal_model=mock_thermal_model,
            preferences=mock_preferences,
            config={}
        )
        
        # Mock stability detector with drift data
        mock_stability_detector = Mock()
        thermal_manager.stability_detector = mock_stability_detector
        
        return thermal_manager, mock_stability_detector, mock_thermal_model
    
    def test_passive_learning_passes_outdoor_temp(self):
        """Test that passive learning passes outdoor_temp to analyze_drift_data."""
        thermal_manager, mock_stability, mock_model = self.create_mock_thermal_manager()
        
        # Mock drift data from stability detector
        test_drift_data = [
            (0, 22.0), (300, 22.5), (600, 23.0), (900, 23.4),
            (1200, 23.7), (1500, 24.0), (1800, 24.2), (2100, 24.4),
            (2400, 24.5), (2700, 24.6), (3000, 24.7), (3300, 24.75),
            (3600, 24.8)
        ]
        mock_stability.find_natural_drift_event.return_value = test_drift_data
        
        # Setup thermal manager state
        thermal_manager._last_hvac_mode = "cool"
        thermal_manager._setpoint = 24.0
        
        # Mock analyze_drift_data to capture the call
        import custom_components.smart_climate.thermal_utils as thermal_utils
        original_analyze = thermal_utils.analyze_drift_data
        
        captured_calls = []
        def mock_analyze_drift_data(*args, **kwargs):
            captured_calls.append((args, kwargs))
            # Return a valid ProbeResult for testing
            return ProbeResult(
                tau_value=1800.0,
                confidence=0.4,  # Above default threshold of 0.3
                duration=3600,
                fit_quality=0.8,
                aborted=False,
                outdoor_temp=kwargs.get('outdoor_temp')
            )
        
        thermal_utils.analyze_drift_data = mock_analyze_drift_data
        
        try:
            # Call update_state with outdoor temperature
            outdoor_temp = 18.5
            thermal_manager.update_state(
                current_temp=24.0,
                outdoor_temp=outdoor_temp,
                hvac_mode="cool"
            )
            
            # Verify analyze_drift_data was called with outdoor_temp
            assert len(captured_calls) == 1
            args, kwargs = captured_calls[0]
            
            # Check that outdoor_temp was passed
            assert 'outdoor_temp' in kwargs
            assert kwargs['outdoor_temp'] == outdoor_temp
            assert kwargs['is_passive'] is True
            
            # Verify drift data was passed correctly
            assert args[0] == test_drift_data
            
        finally:
            # Restore original function
            thermal_utils.analyze_drift_data = original_analyze
    
    def test_passive_learning_without_outdoor_temp(self):
        """Test passive learning works when outdoor_temp is None."""
        thermal_manager, mock_stability, mock_model = self.create_mock_thermal_manager()
        
        # Mock drift data
        test_drift_data = [
            (0, 22.0), (300, 22.5), (600, 23.0), (900, 23.4),
            (1200, 23.7), (1500, 24.0), (1800, 24.2), (2100, 24.4),
            (2400, 24.5), (2700, 24.6), (3000, 24.7), (3300, 24.75),
            (3600, 24.8)
        ]
        mock_stability.find_natural_drift_event.return_value = test_drift_data
        
        # Setup thermal manager state
        thermal_manager._last_hvac_mode = "cool"
        thermal_manager._setpoint = 24.0
        
        # Mock analyze_drift_data
        import custom_components.smart_climate.thermal_utils as thermal_utils
        original_analyze = thermal_utils.analyze_drift_data
        
        captured_calls = []
        def mock_analyze_drift_data(*args, **kwargs):
            captured_calls.append((args, kwargs))
            return ProbeResult(
                tau_value=1800.0,
                confidence=0.4,
                duration=3600,
                fit_quality=0.8,
                aborted=False,
                outdoor_temp=kwargs.get('outdoor_temp')
            )
        
        thermal_utils.analyze_drift_data = mock_analyze_drift_data
        
        try:
            # Call update_state without outdoor temperature
            thermal_manager.update_state(
                current_temp=24.0,
                outdoor_temp=None,
                hvac_mode="cool"
            )
            
            # Verify analyze_drift_data was called with outdoor_temp=None
            assert len(captured_calls) == 1
            args, kwargs = captured_calls[0]
            
            # Check that outdoor_temp was passed as None
            assert 'outdoor_temp' in kwargs
            assert kwargs['outdoor_temp'] is None
            
        finally:
            # Restore original function
            thermal_utils.analyze_drift_data = original_analyze


class TestDataCollectionIntegration:
    """Integration tests for complete data collection pipeline."""
    
    def test_end_to_end_learning_and_probe_data_collection(self):
        """Test complete data flow from sensor → thermal_manager → probe creation."""
        # This test verifies that both issues are fixed:
        # 1. Learning is enabled by default
        # 2. Outdoor temp flows through to ProbeResult
        
        # Create OffsetEngine with default config (should have learning enabled)
        config = {}
        engine = OffsetEngine(config)
        
        # Verify learning is enabled by default
        assert engine.is_learning_enabled() is True
        
        # Create test drift data
        drift_data = [
            (0, 20.0), (600, 21.0), (1200, 21.8), (1800, 22.4),
            (2400, 22.8), (3000, 23.1), (3600, 23.3)
        ]
        
        outdoor_temp = 12.5
        
        # Analyze drift data with outdoor temperature
        result = analyze_drift_data(drift_data, is_passive=True, outdoor_temp=outdoor_temp)
        
        # Verify both issues are resolved
        assert result is not None
        assert isinstance(result, ProbeResult)
        assert result.outdoor_temp == outdoor_temp  # Issue #2: outdoor_temp populated
        assert result.tau_value > 0
        assert result.confidence > 0
        
        # Learning should be ready to accept this data (Issue #1: learning enabled)
        assert engine._enable_learning is True
        assert engine._learner is not None  # Should be initialized when learning enabled