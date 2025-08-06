"""ABOUTME: Comfort band controller for thermal efficiency operating windows.
ABOUTME: Calculates operating windows and AC run decisions with predictive cooling."""

from typing import Optional, Tuple
from .thermal_model import PassiveThermalModel
from .thermal_preferences import UserPreferences


class ComfortBandController:
    """
    Controller for comfort band operations and AC decision logic.
    
    Calculates operating temperature windows based on user preferences and
    makes AC run decisions with predictive cooling to prevent overshoot.
    
    Integrates with PassiveThermalModel for drift prediction and
    UserPreferences for comfort band adjustments.
    """
    
    def __init__(self, thermal_model: PassiveThermalModel, preferences: UserPreferences):
        """
        Initialize comfort band controller.
        
        Args:
            thermal_model: PassiveThermalModel for temperature drift predictions
            preferences: UserPreferences for comfort band settings
        """
        self._thermal_model = thermal_model
        self._preferences = preferences
    
    def get_operating_window(
        self, 
        setpoint: float, 
        outdoor_temp: Optional[float], 
        hvac_mode: Optional[str]
    ) -> Tuple[float, float]:
        """
        Calculate operating temperature window around setpoint.
        
        Uses user preferences to determine comfort band size and applies
        weather-based adjustments for extreme temperatures.
        
        Args:
            setpoint: Target temperature in °C
            outdoor_temp: Current outdoor temperature in °C (None if unavailable)
            hvac_mode: "heat", "cool", "auto", or None
            
        Returns:
            Tuple of (min_temperature, max_temperature) in °C
        """
        # Get adjusted comfort band from preferences
        adjusted_band = self._preferences.get_adjusted_band(outdoor_temp, hvac_mode)
        
        # Calculate symmetric window around setpoint
        min_temp = setpoint - adjusted_band
        max_temp = setpoint + adjusted_band
        
        return (min_temp, max_temp)
    
    def should_ac_run(
        self,
        current_temp: float,
        setpoint: float,
        operating_window: Tuple[float, float],
        hvac_mode: Optional[str],
        outdoor_temp: Optional[float] = None,
        prediction_minutes: Optional[int] = None
    ) -> bool:
        """
        Determine if AC should run based on current conditions and predictions.
        
        Uses current temperature relative to operating window and predictive
        cooling/heating to prevent overshoot when thermal model confidence is sufficient.
        
        Args:
            current_temp: Current indoor temperature in °C
            setpoint: Target temperature in °C
            operating_window: (min_temp, max_temp) tuple from get_operating_window
            hvac_mode: "heat", "cool", "auto", or None
            outdoor_temp: Current outdoor temperature for predictions (optional)
            prediction_minutes: Minutes ahead to predict (optional)
            
        Returns:
            True if AC should run, False otherwise
        """
        min_temp, max_temp = operating_window
        
        # Basic logic: run if outside window
        if hvac_mode == "heat":
            # Heating mode: run if below window or predicted to go below
            if current_temp < min_temp:
                return True
            if current_temp > max_temp:
                return False
        else:
            # Cooling mode (default for cool/auto/None)
            if current_temp > max_temp:
                return True
            if current_temp < min_temp:
                return False
        
        # If within window, check predictive logic
        if (outdoor_temp is not None and 
            prediction_minutes is not None and
            prediction_minutes > 0):
            
            # Check thermal model confidence
            confidence = self._thermal_model.get_confidence()
            if confidence >= self._preferences.confidence_threshold:
                # Predict future temperature
                is_cooling_scenario = hvac_mode != "heat"  # Cooling for cool/auto/None
                predicted_temp = self._thermal_model.predict_drift(
                    current=current_temp,
                    outdoor=outdoor_temp,
                    minutes=prediction_minutes,
                    is_cooling=is_cooling_scenario
                )
                
                # Check if prediction would exceed window bounds
                if hvac_mode == "heat":
                    # For heating: run if predicted to drop below lower bound
                    if predicted_temp < min_temp:
                        return True
                else:
                    # For cooling: run if predicted to exceed upper bound
                    if predicted_temp > max_temp:
                        return True
        
        # Default: don't run if within window and no concerning predictions
        return False