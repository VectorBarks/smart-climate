"""Feature Engineering component for Smart Climate Control integration.

ABOUTME: Calculate derived climate metrics for ML model using Magnus and Steadman formulas.
Purpose: Enhance ML predictions with dew point, heat index, and humidity differential calculations.
"""

import math
from typing import Optional
from .models import OffsetInput


class FeatureEngineering:
    """Calculate derived climate metrics for ML model."""
    
    def calculate_dew_point(self, temp_c: Optional[float], humidity: Optional[float]) -> Optional[float]:
        """Calculate dew point using Magnus formula.
        
        Args:
            temp_c: Temperature in Celsius
            humidity: Relative humidity as percentage (0-100)
            
        Returns:
            Dew point in Celsius, rounded to 2 decimal places, or None if inputs are missing/invalid
        """
        if temp_c is None or humidity is None:
            return None
        
        # Validate humidity range (0-100%)
        if humidity <= 0 or humidity > 100:
            return None
            
        try:
            # Magnus formula constants
            b = 17.62
            c = 243.12
            
            # Calculate gamma term
            gamma = (b * temp_c) / (c + temp_c) + math.log(humidity / 100.0)
            
            # Calculate dew point
            dew_point = (c * gamma) / (b - gamma)
            
            return round(dew_point, 2)
        except (ValueError, ZeroDivisionError, OverflowError):
            # Handle mathematical errors gracefully
            return None
    
    def calculate_heat_index(self, temp_c: Optional[float], humidity: Optional[float]) -> Optional[float]:
        """Calculate heat index using Steadman's formula.
        
        Args:
            temp_c: Temperature in Celsius
            humidity: Relative humidity as percentage (0-100)
            
        Returns:
            Heat index in Celsius, or None if inputs are missing/invalid or temperature < 20°C
        """
        if temp_c is None or humidity is None or temp_c < 20.0:
            return None
        
        # Validate humidity range (0-100%)
        if humidity <= 0 or humidity > 100:
            return None
        
        try:
            # Convert to Fahrenheit for calculation
            temp_f = temp_c * 9/5 + 32
            
            # Steadman's heat index formula coefficients
            c1 = -42.379
            c2 = 2.04901523
            c3 = 10.14333127
            c4 = -0.22475541
            c5 = -6.83783e-3
            c6 = -5.481717e-2
            c7 = 1.22874e-3
            c8 = 8.5282e-4
            c9 = -1.99e-6
            
            # Calculate heat index in Fahrenheit
            hi_f = (c1 + c2*temp_f + c3*humidity + c4*temp_f*humidity + 
                    c5*temp_f*temp_f + c6*humidity*humidity + c7*temp_f*temp_f*humidity +
                    c8*temp_f*humidity*humidity + c9*temp_f*temp_f*humidity*humidity)
            
            # Convert back to Celsius
            hi_c = (hi_f - 32) * 5/9
            
            return round(hi_c, 1)
        except (ValueError, ZeroDivisionError, OverflowError):
            # Handle mathematical errors gracefully
            return None
    
    def enrich_features(self, data: OffsetInput) -> OffsetInput:
        """Add all derived metrics to OffsetInput.
        
        Args:
            data: OffsetInput instance to enrich with calculated features
            
        Returns:
            OffsetInput instance with derived humidity features populated
        """
        # Calculate humidity differential if both indoor and outdoor humidity are available
        if data.indoor_humidity is not None and data.outdoor_humidity is not None:
            data.humidity_differential = data.indoor_humidity - data.outdoor_humidity
        else:
            data.humidity_differential = None
        
        # Calculate indoor dew point
        data.indoor_dew_point = self.calculate_dew_point(data.room_temp, data.indoor_humidity)
        
        # Calculate outdoor dew point
        data.outdoor_dew_point = self.calculate_dew_point(data.outdoor_temp, data.outdoor_humidity)
        
        # Calculate heat index using room temperature and indoor humidity
        data.heat_index = self.calculate_heat_index(data.room_temp, data.indoor_humidity)
        
        return data