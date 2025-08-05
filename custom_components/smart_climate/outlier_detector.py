"""
ABOUTME: OutlierDetector for Smart Climate - statistical outlier detection for temperature and power
ABOUTME: Uses modified Z-score with MAD for robust outlier detection, falls back to absolute bounds
"""

import logging
import math
import statistics
from collections import deque
from typing import Any, Dict, List, Optional, Union

_LOGGER = logging.getLogger(__name__)


class OutlierDetector:
    """Detects outliers in temperature and power consumption data using statistical methods."""
    
    def __init__(self, 
                 temp_bounds: tuple = (-10.0, 50.0),
                 power_bounds: tuple = (0.0, 5000.0), 
                 zscore_threshold: float = 2.5,
                 history_size: int = 50,
                 min_samples_for_stats: int = 5,
                 config: Optional[Dict[str, Any]] = None):
        """Initialize OutlierDetector with configuration."""
        
        # Apply config overrides if provided
        if config:
            temp_bounds = config.get('temperature_bounds', temp_bounds)
            power_bounds = config.get('power_bounds', power_bounds)
            zscore_threshold = config.get('zscore_threshold', zscore_threshold)
            history_size = config.get('history_size', history_size)
            min_samples_for_stats = config.get('min_samples_for_stats', min_samples_for_stats)
        
        self.temperature_bounds = temp_bounds
        self.power_bounds = power_bounds
        self.zscore_threshold = zscore_threshold
        self.min_samples_for_stats = min_samples_for_stats
        
        # History storage
        self._temperature_history = deque(maxlen=history_size)
        self._power_history = deque(maxlen=history_size)
        
        _LOGGER.debug(
            "OutlierDetector initialized: temp_bounds=%s, power_bounds=%s, "
            "zscore_threshold=%.2f, min_samples=%d",
            temp_bounds, power_bounds, zscore_threshold, min_samples_for_stats
        )
    
    def is_temperature_outlier(self, temp: Any) -> bool:
        """Check if temperature value is an outlier."""
        if not self._is_valid_numeric(temp):
            _LOGGER.warning("Invalid temperature value: %s", temp)
            return True
        
        temp_float = float(temp)
        
        # Check absolute bounds first
        if not self._in_absolute_bounds(temp_float, self.temperature_bounds):
            _LOGGER.debug("Temperature %.2f outside absolute bounds %s", temp_float, self.temperature_bounds)
            return True
        
        # Use statistical detection if sufficient data
        if self.has_sufficient_data():
            zscore = self._calculate_modified_zscore(temp_float, self._temperature_history)
            is_outlier = abs(zscore) > self.zscore_threshold
            _LOGGER.debug(
                "Temperature %.2f statistical check: zscore=%.3f, threshold=%.2f, outlier=%s",
                temp_float, zscore, self.zscore_threshold, is_outlier
            )
            return is_outlier
        
        # Insufficient data - passed absolute bounds check
        _LOGGER.debug("Temperature %.2f within bounds, insufficient data for stats", temp_float)
        return False
    
    def is_power_outlier(self, power: Any) -> bool:
        """Check if power value is an outlier."""
        if not self._is_valid_numeric(power):
            _LOGGER.warning("Invalid power value: %s", power)
            return True
        
        power_float = float(power)
        
        # Check absolute bounds first
        if not self._in_absolute_bounds(power_float, self.power_bounds):
            _LOGGER.debug("Power %.2f outside absolute bounds %s", power_float, self.power_bounds)
            return True
        
        # Use statistical detection if sufficient data
        if len(self._power_history) >= self.min_samples_for_stats:
            zscore = self._calculate_modified_zscore(power_float, self._power_history)
            is_outlier = abs(zscore) > self.zscore_threshold
            _LOGGER.debug(
                "Power %.2f statistical check: zscore=%.3f, threshold=%.2f, outlier=%s",
                power_float, zscore, self.zscore_threshold, is_outlier
            )
            return is_outlier
        
        # Insufficient data - passed absolute bounds check
        _LOGGER.debug("Power %.2f within bounds, insufficient data for stats", power_float)
        return False
    
    def add_temperature_sample(self, temp: Any) -> None:
        """Add temperature sample to history."""
        if self._is_valid_numeric(temp):
            temp_float = float(temp)
            self._temperature_history.append(temp_float)
            _LOGGER.debug("Added temperature sample: %.2f (history size: %d)", 
                         temp_float, len(self._temperature_history))
        else:
            _LOGGER.warning("Rejected invalid temperature sample: %s", temp)
    
    def add_power_sample(self, power: Any) -> None:
        """Add power sample to history."""
        if self._is_valid_numeric(power):
            power_float = float(power)
            self._power_history.append(power_float)
            _LOGGER.debug("Added power sample: %.2f (history size: %d)", 
                         power_float, len(self._power_history))
        else:
            _LOGGER.warning("Rejected invalid power sample: %s", power)
    
    def get_history_size(self) -> int:
        """Get current temperature history size."""
        return len(self._temperature_history)
    
    def has_sufficient_data(self) -> bool:
        """Check if we have sufficient data for statistical analysis."""
        # Return True if either temperature OR power has sufficient data
        return (len(self._temperature_history) >= self.min_samples_for_stats or 
                len(self._power_history) >= self.min_samples_for_stats)
    
    def calculate_modified_zscore(self, value: float, data: List[float]) -> float:
        """Calculate modified Z-score using MAD (public method for tests)."""
        return self._calculate_modified_zscore(value, data)
    
    def calculate_mad(self, data: List[float]) -> float:
        """Calculate Median Absolute Deviation (public method for tests)."""
        return self._calculate_median_absolute_deviation(data)
    
    def _calculate_modified_zscore(self, value: float, history: deque) -> float:
        """Calculate modified Z-score using MAD."""
        if len(history) < 2:
            return 0.0
        
        data = list(history)
        median = statistics.median(data)
        mad = self._calculate_median_absolute_deviation(data)
        
        if mad == 0.0:
            # All values are identical - any deviation is an outlier
            return float('inf') if value != median else 0.0
        
        # Modified Z-score formula: 0.6745 * (value - median) / MAD
        modified_zscore = 0.6745 * (value - median) / mad
        
        _LOGGER.debug(
            "Modified Z-score calculation: value=%.2f, median=%.2f, mad=%.3f, zscore=%.3f",
            value, median, mad, modified_zscore
        )
        
        return modified_zscore
    
    def _calculate_median_absolute_deviation(self, data: List[float]) -> float:
        """Calculate Median Absolute Deviation."""
        if len(data) == 0:
            return 0.0
        
        median = statistics.median(data)
        absolute_deviations = [abs(x - median) for x in data]
        mad = statistics.median(absolute_deviations)
        
        return mad
    
    def _in_absolute_bounds(self, value: float, bounds: tuple) -> bool:
        """Check if value is within absolute bounds."""
        min_bound, max_bound = bounds
        return min_bound <= value <= max_bound
    
    def _is_valid_numeric(self, value: Any) -> bool:
        """Check if value is a valid numeric type."""
        if value is None:
            return False
        
        # Only allow int and float types - reject strings, booleans, and other types
        if not isinstance(value, (int, float)):
            return False
        
        # Additional check: reject bool subclass (since bool is subclass of int)
        if isinstance(value, bool):
            return False
        
        try:
            float_val = float(value)
            return not (math.isnan(float_val) or math.isinf(float_val))
        except (TypeError, ValueError):
            return False