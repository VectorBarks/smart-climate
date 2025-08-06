"""Tests for thermal efficiency models and enums."""

import pytest
from enum import Enum
from dataclasses import dataclass

from custom_components.smart_climate.thermal_models import (
    ThermalConstants,
    ProbeResult,
    ThermalState,
    PreferenceLevel,
)


class TestThermalConstants:
    """Test suite for ThermalConstants dataclass."""
    
    def test_thermal_constants_default_values(self):
        """Test ThermalConstants dataclass with default values."""
        constants = ThermalConstants()
        
        # Verify default thermal time constants 
        assert constants.tau_cooling == 90.0
        assert constants.tau_warming == 150.0
        
        # Verify default timing constraints
        assert constants.min_off_time == 600  # 10 minutes
        assert constants.min_on_time == 300   # 5 minutes
        
        # Verify default learning durations
        assert constants.priming_duration == 86400  # 24 hours
        assert constants.recovery_duration == 1800  # 30 minutes
    
    def test_thermal_constants_custom_values(self):
        """Test ThermalConstants dataclass with custom values."""
        constants = ThermalConstants(
            tau_cooling=120.0,
            tau_warming=180.0,
            min_off_time=480,
            min_on_time=240,
            priming_duration=172800,  # 48 hours
            recovery_duration=3600    # 60 minutes
        )
        
        assert constants.tau_cooling == 120.0
        assert constants.tau_warming == 180.0
        assert constants.min_off_time == 480
        assert constants.min_on_time == 240
        assert constants.priming_duration == 172800
        assert constants.recovery_duration == 3600
    
    def test_thermal_constants_type_annotations(self):
        """Test that ThermalConstants has proper type annotations."""
        constants = ThermalConstants()
        
        assert isinstance(constants.tau_cooling, float)
        assert isinstance(constants.tau_warming, float)
        assert isinstance(constants.min_off_time, int)
        assert isinstance(constants.min_on_time, int)
        assert isinstance(constants.priming_duration, int)
        assert isinstance(constants.recovery_duration, int)


class TestProbeResult:
    """Test suite for ProbeResult dataclass."""
    
    def test_probe_result_creation(self):
        """Test ProbeResult dataclass creation."""
        result = ProbeResult(
            tau_value=95.5,
            confidence=0.85,
            duration=1800,
            fit_quality=0.92,
            aborted=False
        )
        
        assert result.tau_value == 95.5
        assert result.confidence == 0.85
        assert result.duration == 1800
        assert result.fit_quality == 0.92
        assert result.aborted is False
    
    def test_probe_result_aborted_scenario(self):
        """Test ProbeResult for aborted probe."""
        result = ProbeResult(
            tau_value=0.0,
            confidence=0.0,
            duration=300,
            fit_quality=0.0,
            aborted=True
        )
        
        assert result.tau_value == 0.0
        assert result.confidence == 0.0
        assert result.duration == 300
        assert result.fit_quality == 0.0
        assert result.aborted is True
    
    def test_probe_result_type_annotations(self):
        """Test that ProbeResult has proper type annotations."""
        result = ProbeResult(
            tau_value=90.0,
            confidence=0.75,
            duration=1200,
            fit_quality=0.88,
            aborted=False
        )
        
        assert isinstance(result.tau_value, float)
        assert isinstance(result.confidence, float)
        assert isinstance(result.duration, int)
        assert isinstance(result.fit_quality, float)
        assert isinstance(result.aborted, bool)


class TestThermalState:
    """Test suite for ThermalState enum."""
    
    def test_thermal_state_enum_values(self):
        """Test ThermalState enum contains all required states."""
        # Test that enum has exactly 6 states
        assert len(ThermalState) == 6
        
        # Test each required state exists
        assert ThermalState.PRIMING
        assert ThermalState.DRIFTING  
        assert ThermalState.CORRECTING
        assert ThermalState.RECOVERY
        assert ThermalState.PROBING
        assert ThermalState.CALIBRATING
    
    def test_thermal_state_is_enum(self):
        """Test that ThermalState is properly defined as an Enum."""
        assert issubclass(ThermalState, Enum)
        
        # Test that states are accessible by name
        assert ThermalState.PRIMING.name == "PRIMING"
        assert ThermalState.DRIFTING.name == "DRIFTING"
        assert ThermalState.CORRECTING.name == "CORRECTING"
        assert ThermalState.RECOVERY.name == "RECOVERY"
        assert ThermalState.PROBING.name == "PROBING"
        assert ThermalState.CALIBRATING.name == "CALIBRATING"
    
    def test_thermal_state_comparison(self):
        """Test that ThermalState enum values can be compared."""
        state1 = ThermalState.PRIMING
        state2 = ThermalState.PRIMING
        state3 = ThermalState.DRIFTING
        
        assert state1 == state2
        assert state1 != state3
    
    def test_thermal_state_in_collection(self):
        """Test that ThermalState enum values work in collections."""
        active_states = {ThermalState.CORRECTING, ThermalState.PROBING}
        
        assert ThermalState.CORRECTING in active_states
        assert ThermalState.PROBING in active_states
        assert ThermalState.DRIFTING not in active_states


class TestPreferenceLevel:
    """Test suite for PreferenceLevel enum."""
    
    def test_preference_level_enum_values(self):
        """Test PreferenceLevel enum contains all required levels."""
        # Test that enum has exactly 5 levels
        assert len(PreferenceLevel) == 5
        
        # Test each required level exists
        assert PreferenceLevel.MAX_COMFORT
        assert PreferenceLevel.COMFORT_PRIORITY
        assert PreferenceLevel.BALANCED
        assert PreferenceLevel.SAVINGS_PRIORITY
        assert PreferenceLevel.MAX_SAVINGS
    
    def test_preference_level_is_enum(self):
        """Test that PreferenceLevel is properly defined as an Enum."""
        assert issubclass(PreferenceLevel, Enum)
        
        # Test that levels are accessible by name
        assert PreferenceLevel.MAX_COMFORT.name == "MAX_COMFORT"
        assert PreferenceLevel.COMFORT_PRIORITY.name == "COMFORT_PRIORITY"
        assert PreferenceLevel.BALANCED.name == "BALANCED"
        assert PreferenceLevel.SAVINGS_PRIORITY.name == "SAVINGS_PRIORITY"
        assert PreferenceLevel.MAX_SAVINGS.name == "MAX_SAVINGS"
    
    def test_preference_level_comparison(self):
        """Test that PreferenceLevel enum values can be compared."""
        level1 = PreferenceLevel.BALANCED
        level2 = PreferenceLevel.BALANCED
        level3 = PreferenceLevel.MAX_COMFORT
        
        assert level1 == level2
        assert level1 != level3
    
    def test_preference_level_in_collection(self):
        """Test that PreferenceLevel enum values work in collections."""
        comfort_levels = {PreferenceLevel.MAX_COMFORT, PreferenceLevel.COMFORT_PRIORITY}
        savings_levels = {PreferenceLevel.SAVINGS_PRIORITY, PreferenceLevel.MAX_SAVINGS}
        
        assert PreferenceLevel.MAX_COMFORT in comfort_levels
        assert PreferenceLevel.COMFORT_PRIORITY in comfort_levels
        assert PreferenceLevel.BALANCED not in comfort_levels
        
        assert PreferenceLevel.SAVINGS_PRIORITY in savings_levels
        assert PreferenceLevel.MAX_SAVINGS in savings_levels
        assert PreferenceLevel.BALANCED not in savings_levels


class TestModelValidation:
    """Test suite for model validation and edge cases."""
    
    def test_thermal_constants_negative_values(self):
        """Test ThermalConstants handles negative values appropriately."""
        # These should be allowed as they represent valid thermal constants
        constants = ThermalConstants(
            tau_cooling=-90.0,  # Could represent heating scenario
            tau_warming=-150.0,
            min_off_time=0,     # Edge case: no minimum off time
            min_on_time=0,      # Edge case: no minimum on time
            priming_duration=0, # Edge case: no priming phase
            recovery_duration=0 # Edge case: instant recovery
        )
        
        assert constants.tau_cooling == -90.0
        assert constants.tau_warming == -150.0
        assert constants.min_off_time == 0
        assert constants.min_on_time == 0
        assert constants.priming_duration == 0
        assert constants.recovery_duration == 0
    
    def test_probe_result_extreme_values(self):
        """Test ProbeResult handles extreme values appropriately."""
        # Test very high confidence and quality
        result_high = ProbeResult(
            tau_value=1000.0,
            confidence=1.0,
            duration=86400,  # 24 hours
            fit_quality=1.0,
            aborted=False
        )
        
        assert result_high.tau_value == 1000.0
        assert result_high.confidence == 1.0
        assert result_high.fit_quality == 1.0
        
        # Test very low values  
        result_low = ProbeResult(
            tau_value=0.1,
            confidence=0.01,
            duration=1,
            fit_quality=0.01,
            aborted=False
        )
        
        assert result_low.tau_value == 0.1
        assert result_low.confidence == 0.01
        assert result_low.fit_quality == 0.01