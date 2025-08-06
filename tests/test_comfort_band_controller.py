"""Tests for ComfortBandController - Step 1.5 TDD Implementation

Tests for operating window calculation, predictive cooling logic, 
and integration with UserPreferences and PassiveThermalModel.
"""

import pytest
from unittest.mock import Mock, MagicMock
from custom_components.smart_climate.comfort_band_controller import ComfortBandController
from custom_components.smart_climate.thermal_preferences import UserPreferences, PreferenceLevel
from custom_components.smart_climate.thermal_model import PassiveThermalModel


@pytest.fixture
def mock_thermal_model():
    """Mock PassiveThermalModel for testing."""
    mock = Mock(spec=PassiveThermalModel)
    mock.predict_drift.return_value = 22.0  # Default prediction
    mock.get_confidence.return_value = 0.7
    return mock


@pytest.fixture
def balanced_preferences():
    """UserPreferences with balanced settings."""
    return UserPreferences(
        level=PreferenceLevel.BALANCED,
        comfort_band=1.5,
        confidence_threshold=0.5,
        probe_drift=2.0,
        extreme_heat_start=30.0,
        extreme_cold_start=0.0
    )


@pytest.fixture
def comfort_preferences():
    """UserPreferences prioritizing comfort."""
    return UserPreferences(
        level=PreferenceLevel.MAX_COMFORT,
        comfort_band=0.8,
        confidence_threshold=0.7,
        probe_drift=1.0,
        extreme_heat_start=30.0,
        extreme_cold_start=0.0
    )


@pytest.fixture
def savings_preferences():
    """UserPreferences prioritizing savings."""
    return UserPreferences(
        level=PreferenceLevel.MAX_SAVINGS,
        comfort_band=2.5,
        confidence_threshold=0.3,
        probe_drift=3.0,
        extreme_heat_start=30.0,
        extreme_cold_start=0.0
    )


@pytest.fixture
def comfort_controller(mock_thermal_model, balanced_preferences):
    """ComfortBandController with balanced preferences."""
    return ComfortBandController(
        thermal_model=mock_thermal_model,
        preferences=balanced_preferences
    )


class TestComfortBandController:
    """Test ComfortBandController initialization and basic functionality."""
    
    def test_controller_initialization(self, mock_thermal_model, balanced_preferences):
        """Test ComfortBandController initializes correctly."""
        controller = ComfortBandController(
            thermal_model=mock_thermal_model,
            preferences=balanced_preferences
        )
        
        assert controller._thermal_model is mock_thermal_model
        assert controller._preferences is balanced_preferences
    
    def test_controller_requires_thermal_model(self, balanced_preferences):
        """Test ComfortBandController requires thermal model."""
        with pytest.raises(TypeError):
            ComfortBandController(preferences=balanced_preferences)
    
    def test_controller_requires_preferences(self, mock_thermal_model):
        """Test ComfortBandController requires preferences."""
        with pytest.raises(TypeError):
            ComfortBandController(thermal_model=mock_thermal_model)


class TestOperatingWindow:
    """Test get_operating_window() method for different scenarios."""
    
    def test_basic_operating_window_cooling(self, comfort_controller):
        """Test basic operating window calculation for cooling mode."""
        # Setpoint 22°C, balanced preferences (1.5°C band)
        min_temp, max_temp = comfort_controller.get_operating_window(
            setpoint=22.0,
            outdoor_temp=25.0,
            hvac_mode="cool"
        )
        
        # Should be symmetrical around setpoint
        assert min_temp == 20.5  # 22.0 - 1.5
        assert max_temp == 23.5  # 22.0 + 1.5
        assert max_temp - min_temp == 3.0  # 2 * comfort_band
    
    def test_basic_operating_window_heating(self, comfort_controller):
        """Test basic operating window calculation for heating mode."""
        min_temp, max_temp = comfort_controller.get_operating_window(
            setpoint=20.0,
            outdoor_temp=10.0,
            hvac_mode="heat"
        )
        
        # Should be symmetrical around setpoint  
        assert min_temp == 18.5  # 20.0 - 1.5
        assert max_temp == 21.5  # 20.0 + 1.5
    
    def test_operating_window_with_comfort_preferences(self, mock_thermal_model, comfort_preferences):
        """Test operating window with comfort-prioritized preferences."""
        controller = ComfortBandController(
            thermal_model=mock_thermal_model,
            preferences=comfort_preferences
        )
        
        min_temp, max_temp = controller.get_operating_window(
            setpoint=22.0,
            outdoor_temp=25.0, 
            hvac_mode="cool"
        )
        
        # Tighter band for comfort (0.8°C)
        assert abs(min_temp - 21.2) < 0.01  # 22.0 - 0.8
        assert abs(max_temp - 22.8) < 0.01  # 22.0 + 0.8
        assert abs((max_temp - min_temp) - 1.6) < 0.01  # 2 * 0.8
    
    def test_operating_window_with_savings_preferences(self, mock_thermal_model, savings_preferences):
        """Test operating window with savings-prioritized preferences."""
        controller = ComfortBandController(
            thermal_model=mock_thermal_model,
            preferences=savings_preferences
        )
        
        min_temp, max_temp = controller.get_operating_window(
            setpoint=22.0,
            outdoor_temp=25.0,
            hvac_mode="cool"
        )
        
        # Wider band for savings (2.5°C)
        assert min_temp == 19.5  # 22.0 - 2.5
        assert max_temp == 24.5  # 22.0 + 2.5
        assert max_temp - min_temp == 5.0  # 2 * 2.5
    
    def test_operating_window_extreme_heat_adjustment(self, comfort_controller):
        """Test operating window adjustment in extreme heat."""
        # 32°C outdoor temp should trigger extreme heat adjustment
        min_temp, max_temp = comfort_controller.get_operating_window(
            setpoint=22.0,
            outdoor_temp=32.0,  # 2°C above extreme_heat_start (30°C)
            hvac_mode="cool"
        )
        
        # Band should be tighter in extreme heat (adjustment up to 30%)
        band_width = max_temp - min_temp
        assert band_width < 3.0  # Less than normal 2 * 1.5°C
        assert band_width > 2.1  # But not too tight (30% reduction max)
    
    def test_operating_window_extreme_cold_max_comfort(self, mock_thermal_model):
        """Test operating window adjustment in extreme cold with max comfort."""
        preferences = UserPreferences(
            level=PreferenceLevel.MAX_COMFORT,
            comfort_band=1.5,
            confidence_threshold=0.7,
            probe_drift=1.0
        )
        controller = ComfortBandController(
            thermal_model=mock_thermal_model,
            preferences=preferences
        )
        
        # -5°C outdoor temp should trigger extreme cold adjustment
        min_temp, max_temp = controller.get_operating_window(
            setpoint=20.0,
            outdoor_temp=-5.0,
            hvac_mode="heat"
        )
        
        # Band should be tighter for comfort in extreme cold
        band_width = max_temp - min_temp
        assert band_width < 3.0  # Less than normal 2 * 1.5°C
    
    def test_operating_window_extreme_cold_max_savings(self, mock_thermal_model):
        """Test operating window adjustment in extreme cold with max savings."""
        preferences = UserPreferences(
            level=PreferenceLevel.MAX_SAVINGS,
            comfort_band=1.5,
            confidence_threshold=0.3,
            probe_drift=3.0
        )
        controller = ComfortBandController(
            thermal_model=mock_thermal_model,
            preferences=preferences
        )
        
        # -5°C outdoor temp should trigger extreme cold adjustment
        min_temp, max_temp = controller.get_operating_window(
            setpoint=20.0,
            outdoor_temp=-5.0,
            hvac_mode="heat"
        )
        
        # Band should be wider for savings in extreme cold
        band_width = max_temp - min_temp
        assert band_width > 3.0  # More than normal 2 * 1.5°C
    
    def test_operating_window_boundary_enforcement(self, comfort_controller):
        """Test that operating window boundaries are enforced."""
        min_temp, max_temp = comfort_controller.get_operating_window(
            setpoint=22.0,
            outdoor_temp=25.0,
            hvac_mode="cool"
        )
        
        # Should not have infinite bounds
        assert min_temp != float('-inf')
        assert max_temp != float('inf')
        assert min_temp < max_temp
        assert max_temp - min_temp > 0
    
    def test_operating_window_none_outdoor_temp(self, comfort_controller):
        """Test operating window with None outdoor temperature."""
        min_temp, max_temp = comfort_controller.get_operating_window(
            setpoint=22.0,
            outdoor_temp=None,
            hvac_mode="cool"
        )
        
        # Should use base comfort band when outdoor temp unavailable
        assert min_temp == 20.5  # 22.0 - 1.5
        assert max_temp == 23.5  # 22.0 + 1.5
    
    def test_operating_window_none_hvac_mode(self, comfort_controller):
        """Test operating window with None HVAC mode."""
        min_temp, max_temp = comfort_controller.get_operating_window(
            setpoint=22.0,
            outdoor_temp=25.0,
            hvac_mode=None
        )
        
        # Should use base comfort band when HVAC mode unavailable
        assert min_temp == 20.5  # 22.0 - 1.5
        assert max_temp == 23.5  # 22.0 + 1.5


class TestShouldAcRun:
    """Test should_ac_run() decision logic with predictive cooling."""
    
    def test_should_ac_run_below_window(self, comfort_controller):
        """Test AC should not run when temperature is below operating window."""
        window = (20.0, 24.0)
        
        # Current temp below window
        should_run = comfort_controller.should_ac_run(
            current_temp=19.5,
            setpoint=22.0,
            operating_window=window,
            hvac_mode="cool"
        )
        
        assert should_run is False
    
    def test_should_ac_run_within_window(self, comfort_controller):
        """Test AC should not run when temperature is within operating window."""
        window = (20.0, 24.0)
        
        # Current temp within window
        should_run = comfort_controller.should_ac_run(
            current_temp=22.0,
            setpoint=22.0, 
            operating_window=window,
            hvac_mode="cool"
        )
        
        assert should_run is False
    
    def test_should_ac_run_above_window(self, comfort_controller):
        """Test AC should run when temperature is above operating window."""
        window = (20.0, 24.0)
        
        # Current temp above window
        should_run = comfort_controller.should_ac_run(
            current_temp=24.5,
            setpoint=22.0,
            operating_window=window,
            hvac_mode="cool"
        )
        
        assert should_run is True
    
    def test_should_ac_run_predictive_cooling(self, mock_thermal_model, balanced_preferences):
        """Test predictive cooling logic prevents overshoot."""
        # Configure thermal model to predict overshoot
        mock_thermal_model.predict_drift.return_value = 24.5  # Will exceed upper bound
        mock_thermal_model.get_confidence.return_value = 0.8  # High confidence
        
        controller = ComfortBandController(
            thermal_model=mock_thermal_model,
            preferences=balanced_preferences
        )
        
        window = (20.0, 24.0)
        
        # Current temp within window, but predicted to exceed upper bound
        should_run = controller.should_ac_run(
            current_temp=23.0,  # Within window currently
            setpoint=22.0,
            operating_window=window,
            hvac_mode="cool",
            outdoor_temp=30.0,
            prediction_minutes=15
        )
        
        assert should_run is True
        # Verify thermal model was called for prediction
        mock_thermal_model.predict_drift.assert_called_once()
    
    def test_should_ac_run_predictive_heating(self, mock_thermal_model, balanced_preferences):
        """Test predictive heating logic prevents undershoot."""
        # Configure thermal model to predict undershoot
        mock_thermal_model.predict_drift.return_value = 19.5  # Will drop below lower bound
        mock_thermal_model.get_confidence.return_value = 0.8  # High confidence
        
        controller = ComfortBandController(
            thermal_model=mock_thermal_model,
            preferences=balanced_preferences
        )
        
        window = (20.0, 24.0)
        
        # Current temp within window, but predicted to drop below lower bound
        should_run = controller.should_ac_run(
            current_temp=21.0,  # Within window currently
            setpoint=22.0,
            operating_window=window,
            hvac_mode="heat",
            outdoor_temp=5.0,
            prediction_minutes=20
        )
        
        assert should_run is True
        # Verify thermal model was called for prediction
        mock_thermal_model.predict_drift.assert_called_once()
    
    def test_should_ac_run_low_confidence_prediction(self, mock_thermal_model, balanced_preferences):
        """Test predictive logic ignores low confidence predictions."""
        # Configure thermal model with low confidence prediction
        mock_thermal_model.predict_drift.return_value = 24.5  # Would exceed bound
        mock_thermal_model.get_confidence.return_value = 0.3  # Low confidence (below 0.5 threshold)
        
        controller = ComfortBandController(
            thermal_model=mock_thermal_model,
            preferences=balanced_preferences
        )
        
        window = (20.0, 24.0)
        
        # Should not run AC due to low confidence
        should_run = controller.should_ac_run(
            current_temp=23.0,
            setpoint=22.0,
            operating_window=window,
            hvac_mode="cool",
            outdoor_temp=30.0,
            prediction_minutes=15
        )
        
        assert should_run is False
    
    def test_should_ac_run_no_prediction_params(self, comfort_controller):
        """Test AC decision without prediction parameters."""
        window = (20.0, 24.0)
        
        # No outdoor temp or prediction minutes - should use basic logic
        should_run = comfort_controller.should_ac_run(
            current_temp=23.0,
            setpoint=22.0,
            operating_window=window,
            hvac_mode="cool"
        )
        
        # Within window, so should not run
        assert should_run is False
    
    def test_should_ac_run_heating_mode(self, comfort_controller):
        """Test heating mode AC decision logic."""
        window = (18.0, 22.0)
        
        # Temperature below window in heating mode
        should_run = comfort_controller.should_ac_run(
            current_temp=17.5,
            setpoint=20.0,
            operating_window=window,
            hvac_mode="heat"
        )
        
        assert should_run is True
        
        # Temperature above window in heating mode  
        should_run = comfort_controller.should_ac_run(
            current_temp=22.5,
            setpoint=20.0,
            operating_window=window,
            hvac_mode="heat"
        )
        
        assert should_run is False
    
    def test_should_ac_run_auto_mode(self, comfort_controller):
        """Test auto mode defaults to cooling logic."""
        window = (20.0, 24.0)
        
        # Temperature above window in auto mode
        should_run = comfort_controller.should_ac_run(
            current_temp=24.5,
            setpoint=22.0,
            operating_window=window,
            hvac_mode="auto"
        )
        
        assert should_run is True


class TestIntegration:
    """Test integration between components."""
    
    def test_integration_with_user_preferences(self, mock_thermal_model):
        """Test ComfortBandController properly uses UserPreferences."""
        preferences = UserPreferences(
            level=PreferenceLevel.COMFORT_PRIORITY,
            comfort_band=1.2,
            confidence_threshold=0.6,
            probe_drift=1.5
        )
        
        controller = ComfortBandController(
            thermal_model=mock_thermal_model,
            preferences=preferences
        )
        
        min_temp, max_temp = controller.get_operating_window(
            setpoint=22.0,
            outdoor_temp=25.0,
            hvac_mode="cool"
        )
        
        # Should use the preferences' comfort band
        expected_band = preferences.comfort_band
        assert abs((max_temp - min_temp) - (2 * expected_band)) < 0.01
    
    def test_integration_with_thermal_model(self, balanced_preferences):
        """Test ComfortBandController properly uses PassiveThermalModel."""
        thermal_model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        
        controller = ComfortBandController(
            thermal_model=thermal_model,
            preferences=balanced_preferences
        )
        
        # Test that thermal model is actually called
        window = (20.0, 24.0)
        should_run = controller.should_ac_run(
            current_temp=23.0,
            setpoint=22.0,
            operating_window=window,
            hvac_mode="cool",
            outdoor_temp=30.0,
            prediction_minutes=15
        )
        
        # Should work without errors (real thermal model integration)
        assert isinstance(should_run, bool)
    
    def test_extreme_temperature_behavior(self, comfort_controller):
        """Test behavior at extreme temperatures."""
        # Very hot outdoor temperature
        min_temp, max_temp = comfort_controller.get_operating_window(
            setpoint=22.0,
            outdoor_temp=45.0,  # Extreme heat
            hvac_mode="cool"
        )
        
        # Should still return valid bounds
        assert min_temp < max_temp
        assert min_temp > 10.0  # Reasonable lower bound
        assert max_temp < 35.0  # Reasonable upper bound
        
        # Very cold outdoor temperature
        min_temp, max_temp = comfort_controller.get_operating_window(
            setpoint=20.0,
            outdoor_temp=-20.0,  # Extreme cold
            hvac_mode="heat"
        )
        
        # Should still return valid bounds
        assert min_temp < max_temp
        assert min_temp > 10.0  # Reasonable lower bound
        assert max_temp < 30.0  # Reasonable upper bound