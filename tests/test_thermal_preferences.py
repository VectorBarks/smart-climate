"""
ABOUTME: Test suite for thermal efficiency UserPreferences component (Step 1.2)
Tests all preference levels, asymmetric heating/cooling behavior, and extreme weather adjustments
"""

import pytest
from unittest.mock import Mock, patch
from custom_components.smart_climate.thermal_preferences import (
    PreferenceLevel,
    UserPreferences,
)


class TestPreferenceLevel:
    """Test PreferenceLevel enum values."""
    
    def test_all_preference_levels_exist(self):
        """Test that all 5 preference levels are defined."""
        expected_levels = [
            "MAX_COMFORT",
            "COMFORT_PRIORITY", 
            "BALANCED",
            "SAVINGS_PRIORITY",
            "MAX_SAVINGS"
        ]
        actual_levels = [level.name for level in PreferenceLevel]
        assert set(actual_levels) == set(expected_levels)
        assert len(actual_levels) == 5


class TestUserPreferences:
    """Test UserPreferences dataclass and methods."""
    
    def test_user_preferences_dataclass_fields(self):
        """Test UserPreferences has all required fields with correct defaults."""
        prefs = UserPreferences(
            level=PreferenceLevel.BALANCED,
            comfort_band=1.2,
            confidence_threshold=0.8,
            probe_drift=2.0
        )
        
        assert prefs.level == PreferenceLevel.BALANCED
        assert prefs.comfort_band == 1.2
        assert prefs.confidence_threshold == 0.8
        assert prefs.probe_drift == 2.0
        assert prefs.extreme_heat_start == 30.0  # default
        assert prefs.extreme_cold_start == 0.0   # default
    
    def test_user_preferences_custom_extreme_temperatures(self):
        """Test UserPreferences with custom extreme temperature thresholds."""
        prefs = UserPreferences(
            level=PreferenceLevel.MAX_COMFORT,
            comfort_band=0.5,
            confidence_threshold=0.9,
            probe_drift=1.0,
            extreme_heat_start=28.0,
            extreme_cold_start=-5.0
        )
        
        assert prefs.extreme_heat_start == 28.0
        assert prefs.extreme_cold_start == -5.0


class TestPreferenceLevelBehaviors:
    """Test base comfort band values for each preference level."""
    
    def test_max_comfort_base_band(self):
        """Test MAX_COMFORT has tightest comfort band (0.5°C)."""
        prefs = UserPreferences(
            level=PreferenceLevel.MAX_COMFORT,
            comfort_band=0.5,
            confidence_threshold=0.9,
            probe_drift=1.0
        )
        
        # Normal weather - should return base band
        adjusted_band = prefs.get_adjusted_band(outdoor_temp=20.0, hvac_mode="cool")
        assert adjusted_band == 0.5
    
    def test_comfort_priority_base_band(self):
        """Test COMFORT_PRIORITY has comfort-focused band (0.8°C)."""
        prefs = UserPreferences(
            level=PreferenceLevel.COMFORT_PRIORITY,
            comfort_band=0.8,
            confidence_threshold=0.85,
            probe_drift=1.2
        )
        
        adjusted_band = prefs.get_adjusted_band(outdoor_temp=20.0, hvac_mode="heat")
        assert adjusted_band == 0.8
    
    def test_balanced_base_band(self):
        """Test BALANCED has default band (1.2°C)."""
        prefs = UserPreferences(
            level=PreferenceLevel.BALANCED,
            comfort_band=1.2,
            confidence_threshold=0.8,
            probe_drift=2.0
        )
        
        adjusted_band = prefs.get_adjusted_band(outdoor_temp=20.0, hvac_mode="cool")
        assert adjusted_band == 1.2
    
    def test_savings_priority_base_band(self):
        """Test SAVINGS_PRIORITY has efficiency-focused band (1.8°C)."""
        prefs = UserPreferences(
            level=PreferenceLevel.SAVINGS_PRIORITY,
            comfort_band=1.8,
            confidence_threshold=0.7,
            probe_drift=2.5
        )
        
        adjusted_band = prefs.get_adjusted_band(outdoor_temp=20.0, hvac_mode="heat")
        assert adjusted_band == 1.8
    
    def test_max_savings_base_band(self):
        """Test MAX_SAVINGS has widest band (2.5°C)."""
        prefs = UserPreferences(
            level=PreferenceLevel.MAX_SAVINGS,
            comfort_band=2.5,
            confidence_threshold=0.6,
            probe_drift=3.0
        )
        
        adjusted_band = prefs.get_adjusted_band(outdoor_temp=20.0, hvac_mode="cool")
        assert adjusted_band == 2.5


class TestCoolingModeExtremeHeat:
    """Test cooling mode behavior during extreme heat (30-35°C range)."""
    
    @pytest.fixture
    def balanced_prefs(self):
        return UserPreferences(
            level=PreferenceLevel.BALANCED,
            comfort_band=1.2,
            confidence_threshold=0.8,
            probe_drift=2.0,
            extreme_heat_start=30.0
        )
    
    def test_cooling_normal_temperature(self, balanced_prefs):
        """Test cooling mode at normal temperature returns base band."""
        adjusted_band = balanced_prefs.get_adjusted_band(outdoor_temp=25.0, hvac_mode="cool")
        assert adjusted_band == 1.2  # No adjustment
    
    def test_cooling_extreme_heat_start(self, balanced_prefs):
        """Test cooling mode at extreme heat start (30°C) begins adjustment."""
        adjusted_band = balanced_prefs.get_adjusted_band(outdoor_temp=30.0, hvac_mode="cool")
        # Should start tightening: heat_factor = 0.0, so no adjustment yet
        assert adjusted_band == 1.2
    
    def test_cooling_moderate_extreme_heat(self, balanced_prefs):
        """Test cooling mode at moderate extreme heat (32°C) tightens bands."""
        adjusted_band = balanced_prefs.get_adjusted_band(outdoor_temp=32.0, hvac_mode="cool")
        # heat_factor = (32-30)/5 = 0.4, adjustment = 1.2 * (1 - 0.4*0.3) = 1.056
        expected = 1.2 * (1.0 - 0.4 * 0.3)
        assert abs(adjusted_band - expected) < 0.001
    
    def test_cooling_peak_extreme_heat(self, balanced_prefs):
        """Test cooling mode at peak extreme heat (35°C) maximum tightening."""
        adjusted_band = balanced_prefs.get_adjusted_band(outdoor_temp=35.0, hvac_mode="cool")
        # heat_factor = (35-30)/5 = 1.0, adjustment = 1.2 * (1 - 1.0*0.3) = 0.84
        expected = 1.2 * (1.0 - 1.0 * 0.3)
        assert abs(adjusted_band - expected) < 0.001
        assert adjusted_band == 0.84
    
    def test_cooling_beyond_extreme_heat(self, balanced_prefs):
        """Test cooling mode beyond extreme heat range caps adjustment."""
        adjusted_band = balanced_prefs.get_adjusted_band(outdoor_temp=40.0, hvac_mode="cool")
        # heat_factor capped at 1.0, same as 35°C
        expected = 1.2 * (1.0 - 1.0 * 0.3)
        assert abs(adjusted_band - expected) < 0.001
        assert adjusted_band == 0.84


class TestHeatingModeAsymmetricBehavior:
    """Test heating mode asymmetric behavior based on preference level."""
    
    def test_heating_normal_temperature_all_levels(self):
        """Test heating mode at normal temperature returns base band for all levels."""
        for level, base_band in [
            (PreferenceLevel.MAX_COMFORT, 0.5),
            (PreferenceLevel.COMFORT_PRIORITY, 0.8),
            (PreferenceLevel.BALANCED, 1.2),
            (PreferenceLevel.SAVINGS_PRIORITY, 1.8),
            (PreferenceLevel.MAX_SAVINGS, 2.5)
        ]:
            prefs = UserPreferences(
                level=level,
                comfort_band=base_band,
                confidence_threshold=0.8,
                probe_drift=2.0
            )
            adjusted_band = prefs.get_adjusted_band(outdoor_temp=10.0, hvac_mode="heat")
            assert adjusted_band == base_band
    
    def test_heating_max_comfort_cold_weather_tightens(self):
        """Test MAX_COMFORT tightens bands in cold weather for comfort."""
        prefs = UserPreferences(
            level=PreferenceLevel.MAX_COMFORT,
            comfort_band=0.5,
            confidence_threshold=0.9,
            probe_drift=1.0,
            extreme_cold_start=0.0
        )
        
        # At -10°C: cold_factor = (0-(-10))/10 = 1.0, adjustment = 0.5 * (1-1.0*0.4) = 0.3
        adjusted_band = prefs.get_adjusted_band(outdoor_temp=-10.0, hvac_mode="heat")
        expected = 0.5 * (1.0 - 1.0 * 0.4)
        assert abs(adjusted_band - expected) < 0.001
        assert adjusted_band == 0.3
    
    def test_heating_max_comfort_moderate_cold_tightens(self):
        """Test MAX_COMFORT moderate cold weather tightening."""
        prefs = UserPreferences(
            level=PreferenceLevel.MAX_COMFORT,
            comfort_band=0.5,
            confidence_threshold=0.9,
            probe_drift=1.0,
            extreme_cold_start=0.0
        )
        
        # At -5°C: cold_factor = (0-(-5))/10 = 0.5, adjustment = 0.5 * (1-0.5*0.4) = 0.4
        adjusted_band = prefs.get_adjusted_band(outdoor_temp=-5.0, hvac_mode="heat")
        expected = 0.5 * (1.0 - 0.5 * 0.4)
        assert abs(adjusted_band - expected) < 0.001
        assert adjusted_band == 0.4
    
    def test_heating_balanced_cold_weather_no_change(self):
        """Test BALANCED preference has no change in cold weather."""
        prefs = UserPreferences(
            level=PreferenceLevel.BALANCED,
            comfort_band=1.2,
            confidence_threshold=0.8,
            probe_drift=2.0,
            extreme_cold_start=0.0
        )
        
        adjusted_band = prefs.get_adjusted_band(outdoor_temp=-10.0, hvac_mode="heat")
        assert adjusted_band == 1.2  # No change
    
    def test_heating_comfort_priority_cold_weather_no_change(self):
        """Test COMFORT_PRIORITY has no change in cold weather."""
        prefs = UserPreferences(
            level=PreferenceLevel.COMFORT_PRIORITY,
            comfort_band=0.8,
            confidence_threshold=0.85,
            probe_drift=1.2,
            extreme_cold_start=0.0
        )
        
        adjusted_band = prefs.get_adjusted_band(outdoor_temp=-5.0, hvac_mode="heat")
        assert adjusted_band == 0.8  # No change
    
    def test_heating_savings_priority_cold_weather_no_change(self):
        """Test SAVINGS_PRIORITY has no change in cold weather."""
        prefs = UserPreferences(
            level=PreferenceLevel.SAVINGS_PRIORITY,
            comfort_band=1.8,
            confidence_threshold=0.7,
            probe_drift=2.5,
            extreme_cold_start=0.0
        )
        
        adjusted_band = prefs.get_adjusted_band(outdoor_temp=-8.0, hvac_mode="heat")
        assert adjusted_band == 1.8  # No change
    
    def test_heating_max_savings_cold_weather_widens(self):
        """Test MAX_SAVINGS widens bands in cold weather for savings."""
        prefs = UserPreferences(
            level=PreferenceLevel.MAX_SAVINGS,
            comfort_band=2.5,
            confidence_threshold=0.6,
            probe_drift=3.0,
            extreme_cold_start=0.0
        )
        
        # At -10°C: cold_factor = (0-(-10))/10 = 1.0, adjustment = 2.5 * (1+1.0*0.5) = 3.75
        adjusted_band = prefs.get_adjusted_band(outdoor_temp=-10.0, hvac_mode="heat")
        expected = 2.5 * (1.0 + 1.0 * 0.5)
        assert abs(adjusted_band - expected) < 0.001
        assert adjusted_band == 3.75
    
    def test_heating_max_savings_moderate_cold_widens(self):
        """Test MAX_SAVINGS moderate cold weather widening."""
        prefs = UserPreferences(
            level=PreferenceLevel.MAX_SAVINGS,
            comfort_band=2.5,
            confidence_threshold=0.6,
            probe_drift=3.0,
            extreme_cold_start=0.0
        )
        
        # At -6°C: cold_factor = (0-(-6))/10 = 0.6, adjustment = 2.5 * (1+0.6*0.5) = 3.25
        adjusted_band = prefs.get_adjusted_band(outdoor_temp=-6.0, hvac_mode="heat")
        expected = 2.5 * (1.0 + 0.6 * 0.5)
        assert abs(adjusted_band - expected) < 0.001
        assert adjusted_band == 3.25


class TestConfigurationValidation:
    """Test configuration validation and edge cases."""
    
    def test_invalid_hvac_mode_returns_base_band(self):
        """Test invalid hvac_mode returns base comfort band."""
        prefs = UserPreferences(
            level=PreferenceLevel.BALANCED,
            comfort_band=1.2,
            confidence_threshold=0.8,
            probe_drift=2.0
        )
        
        adjusted_band = prefs.get_adjusted_band(outdoor_temp=30.0, hvac_mode="invalid")
        assert adjusted_band == 1.2
    
    def test_none_hvac_mode_returns_base_band(self):
        """Test None hvac_mode returns base comfort band."""
        prefs = UserPreferences(
            level=PreferenceLevel.BALANCED,
            comfort_band=1.2,
            confidence_threshold=0.8,
            probe_drift=2.0
        )
        
        adjusted_band = prefs.get_adjusted_band(outdoor_temp=30.0, hvac_mode=None)
        assert adjusted_band == 1.2
    
    def test_extreme_outdoor_temperatures(self):
        """Test extreme outdoor temperatures don't cause errors."""
        prefs = UserPreferences(
            level=PreferenceLevel.BALANCED,
            comfort_band=1.2,
            confidence_threshold=0.8,
            probe_drift=2.0
        )
        
        # Very hot
        adjusted_band = prefs.get_adjusted_band(outdoor_temp=50.0, hvac_mode="cool")
        assert isinstance(adjusted_band, float)
        assert adjusted_band > 0
        
        # Very cold
        adjusted_band = prefs.get_adjusted_band(outdoor_temp=-30.0, hvac_mode="heat")
        assert isinstance(adjusted_band, float)
        assert adjusted_band > 0
    
    def test_none_outdoor_temperature_returns_base_band(self):
        """Test None outdoor temperature returns base comfort band."""
        prefs = UserPreferences(
            level=PreferenceLevel.BALANCED,
            comfort_band=1.2,
            confidence_threshold=0.8,
            probe_drift=2.0
        )
        
        adjusted_band = prefs.get_adjusted_band(outdoor_temp=None, hvac_mode="cool")
        assert adjusted_band == 1.2
    
    def test_custom_extreme_temperature_thresholds(self):
        """Test custom extreme temperature thresholds work correctly."""
        prefs = UserPreferences(
            level=PreferenceLevel.BALANCED,
            comfort_band=1.2,
            confidence_threshold=0.8,
            probe_drift=2.0,
            extreme_heat_start=28.0,
            extreme_cold_start=-2.0
        )
        
        # Should start adjusting at 28°C instead of 30°C
        adjusted_band = prefs.get_adjusted_band(outdoor_temp=30.0, hvac_mode="cool")
        # heat_factor = (30-28)/5 = 0.4, adjustment = 1.2 * (1 - 0.4*0.3) = 1.056
        expected = 1.2 * (1.0 - 0.4 * 0.3)
        assert abs(adjusted_band - expected) < 0.001


class TestAsymmetricBehaviorComprehensive:
    """Comprehensive test of asymmetric heating vs cooling behavior."""
    
    def test_same_temperature_different_modes(self):
        """Test same outdoor temperature produces different results for heat vs cool."""
        prefs = UserPreferences(
            level=PreferenceLevel.MAX_COMFORT,
            comfort_band=0.5,
            confidence_threshold=0.9,
            probe_drift=1.0,
            extreme_heat_start=30.0,
            extreme_cold_start=0.0
        )
        
        # At 32°C - should affect cooling but not heating
        cool_band = prefs.get_adjusted_band(outdoor_temp=32.0, hvac_mode="cool")
        heat_band = prefs.get_adjusted_band(outdoor_temp=32.0, hvac_mode="heat")
        
        assert cool_band < 0.5  # Tightened for cooling
        assert heat_band == 0.5  # No change for heating
        assert cool_band != heat_band  # Asymmetric behavior
    
    def test_all_preference_levels_asymmetric_cold(self):
        """Test all preference levels show correct asymmetric behavior in cold."""
        outdoor_temp = -8.0
        
        results = {}
        for level, base_band in [
            (PreferenceLevel.MAX_COMFORT, 0.5),
            (PreferenceLevel.COMFORT_PRIORITY, 0.8),
            (PreferenceLevel.BALANCED, 1.2),
            (PreferenceLevel.SAVINGS_PRIORITY, 1.8),
            (PreferenceLevel.MAX_SAVINGS, 2.5)
        ]:
            prefs = UserPreferences(
                level=level,
                comfort_band=base_band,
                confidence_threshold=0.8,
                probe_drift=2.0
            )
            
            cool_band = prefs.get_adjusted_band(outdoor_temp=outdoor_temp, hvac_mode="cool")
            heat_band = prefs.get_adjusted_band(outdoor_temp=outdoor_temp, hvac_mode="heat")
            
            results[level.name] = {
                "cool": cool_band,
                "heat": heat_band,
                "base": base_band
            }
        
        # Cooling should be unchanged in cold weather
        assert results["MAX_COMFORT"]["cool"] == 0.5
        assert results["BALANCED"]["cool"] == 1.2
        assert results["MAX_SAVINGS"]["cool"] == 2.5
        
        # Heating should vary by preference
        assert results["MAX_COMFORT"]["heat"] < 0.5  # Tightened
        assert results["BALANCED"]["heat"] == 1.2      # Unchanged
        assert results["MAX_SAVINGS"]["heat"] > 2.5    # Widened