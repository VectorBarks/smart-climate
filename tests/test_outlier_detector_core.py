"""
ABOUTME: Comprehensive failing tests for OutlierDetector class core functionality
ABOUTME: Tests demonstrate expected behavior for temperature and power outlier detection
"""

import pytest
import statistics
from unittest.mock import Mock, patch
from typing import List, Optional, Dict, Any

# This import will fail initially - demonstrating TDD approach
try:
    from custom_components.smart_climate.outlier_detector import OutlierDetector
except ImportError:
    # Expected to fail initially
    OutlierDetector = None


class TestOutlierDetectorInitialization:
    """Test OutlierDetector initialization and configuration."""
    
    def test_outlier_detector_initialization(self):
        """Test proper initialization with default configuration."""
        if OutlierDetector is None:
            pytest.skip("OutlierDetector not implemented yet")
        
        detector = OutlierDetector()
        
        # Test that detector initializes with sensible defaults
        assert detector is not None
        assert hasattr(detector, 'temperature_bounds')
        assert hasattr(detector, 'power_bounds')
        assert hasattr(detector, 'zscore_threshold')
        
        # Test default bounds
        assert detector.temperature_bounds == (-10.0, 50.0)
        assert detector.power_bounds == (0.0, 5000.0)
        assert detector.zscore_threshold == 2.5  # Common outlier threshold
    
    def test_outlier_detector_empty_history(self):
        """Test behavior with no historical data."""
        if OutlierDetector is None:
            pytest.skip("OutlierDetector not implemented yet")
        
        detector = OutlierDetector()
        
        # With no history, should fall back to absolute bounds only
        assert detector.get_history_size() == 0
        assert detector.has_sufficient_data() is False
        
        # Should still be able to detect absolute outliers
        assert detector.is_temperature_outlier(-15.0) is True  # Below -10°C
        assert detector.is_temperature_outlier(55.0) is True   # Above 50°C
        assert detector.is_temperature_outlier(22.0) is False  # Normal temp
    
    def test_outlier_detector_configuration(self):
        """Test configuration options."""
        if OutlierDetector is None:
            pytest.skip("OutlierDetector not implemented yet")
        
        config = {
            'temperature_bounds': (-5.0, 45.0),
            'power_bounds': (0.0, 3000.0),
            'zscore_threshold': 3.0,
            'min_samples_for_stats': 10
        }
        
        detector = OutlierDetector(config=config)
        
        assert detector.temperature_bounds == (-5.0, 45.0)
        assert detector.power_bounds == (0.0, 3000.0)
        assert detector.zscore_threshold == 3.0
        assert detector.min_samples_for_stats == 10


class TestTemperatureOutlierDetection:
    """Test temperature outlier detection methods."""
    
    def test_temperature_outlier_detection_absolute_bounds(self):
        """Test absolute temperature bounds (-10°C to 50°C)."""
        if OutlierDetector is None:
            pytest.skip("OutlierDetector not implemented yet")
        
        detector = OutlierDetector()
        
        # Test values outside absolute bounds
        assert detector.is_temperature_outlier(-15.0) is True   # Too cold
        assert detector.is_temperature_outlier(-10.1) is True   # Just below bound
        assert detector.is_temperature_outlier(50.1) is True    # Just above bound  
        assert detector.is_temperature_outlier(75.0) is True    # Too hot
        
        # Test values within bounds
        assert detector.is_temperature_outlier(-10.0) is False  # At lower bound
        assert detector.is_temperature_outlier(-5.0) is False   # Cold but valid
        assert detector.is_temperature_outlier(0.0) is False    # Freezing but valid
        assert detector.is_temperature_outlier(22.0) is False   # Room temp
        assert detector.is_temperature_outlier(30.0) is False   # Warm but valid
        assert detector.is_temperature_outlier(50.0) is False   # At upper bound
    
    def test_temperature_outlier_detection_zscore(self):
        """Test Z-score method with sufficient historical data."""
        if OutlierDetector is None:
            pytest.skip("OutlierDetector not implemented yet")
        
        detector = OutlierDetector()
        
        # Build history with normal temperatures around 22°C (±2°C variation)
        normal_temps = [20.0, 21.0, 22.0, 23.0, 24.0, 21.5, 22.5, 23.5, 20.5, 24.5]
        for temp in normal_temps:
            detector.add_temperature_sample(temp)
        
        assert detector.has_sufficient_data() is True
        
        # Test values within normal variation (should not be outliers)
        assert detector.is_temperature_outlier(21.0) is False
        assert detector.is_temperature_outlier(23.0) is False
        assert detector.is_temperature_outlier(19.5) is False  # Slightly outside but not outlier
        
        # Test statistical outliers (beyond Z-score threshold)
        assert detector.is_temperature_outlier(15.0) is True   # Way below normal range
        assert detector.is_temperature_outlier(30.0) is True   # Way above normal range
        
        # Test values that should still respect absolute bounds
        assert detector.is_temperature_outlier(-15.0) is True  # Absolute bound violation
        assert detector.is_temperature_outlier(55.0) is True   # Absolute bound violation
    
    def test_temperature_outlier_detection_gradual_change(self):
        """Test detection of gradual vs sudden temperature changes."""
        if OutlierDetector is None:
            pytest.skip("OutlierDetector not implemented yet")
        
        detector = OutlierDetector()
        
        # Build history showing gradual warming trend
        gradual_temps = [20.0, 20.5, 21.0, 21.5, 22.0, 22.5, 23.0, 23.5, 24.0, 24.5]
        for temp in gradual_temps:
            detector.add_temperature_sample(temp)
        
        # Continuing the trend should not be an outlier
        assert detector.is_temperature_outlier(25.0) is False  # Continues trend
        
        # Sudden jump should be detected
        assert detector.is_temperature_outlier(35.0) is True   # Sudden jump
        assert detector.is_temperature_outlier(15.0) is True   # Sudden drop
    
    def test_temperature_outlier_detection_history_building(self):
        """Test history accumulation and management."""
        if OutlierDetector is None:
            pytest.skip("OutlierDetector not implemented yet")
        
        detector = OutlierDetector()
        
        # Initially no data
        assert detector.get_history_size() == 0
        assert detector.has_sufficient_data() is False
        
        # Add samples and verify history builds
        temps = [20.0, 21.0, 22.0, 23.0, 24.0]
        for i, temp in enumerate(temps):
            detector.add_temperature_sample(temp)
            assert detector.get_history_size() == i + 1
        
        # Test that history is used for calculations
        detector.add_temperature_sample(25.0)  # Should be within normal range
        
        # Test history management (should not grow indefinitely)
        for i in range(100):
            detector.add_temperature_sample(22.0 + (i % 5))  # Cyclic pattern
        
        # History should be capped (e.g., last 50 samples)
        assert detector.get_history_size() <= 50


class TestPowerOutlierDetection:
    """Test power consumption outlier detection methods."""
    
    def test_power_outlier_detection_absolute_bounds(self):
        """Test power bounds (0W to 5000W)."""
        if OutlierDetector is None:
            pytest.skip("OutlierDetector not implemented yet")
        
        detector = OutlierDetector()
        
        # Test values outside absolute bounds
        assert detector.is_power_outlier(-10.0) is True     # Negative power
        assert detector.is_power_outlier(-0.1) is True      # Just below zero
        assert detector.is_power_outlier(5000.1) is True    # Just above bound
        assert detector.is_power_outlier(10000.0) is True   # Way too high
        
        # Test values within bounds
        assert detector.is_power_outlier(0.0) is False      # Zero power (off)
        assert detector.is_power_outlier(150.0) is False    # Low power
        assert detector.is_power_outlier(800.0) is False    # Normal AC power
        assert detector.is_power_outlier(2500.0) is False   # High power
        assert detector.is_power_outlier(5000.0) is False   # At upper bound
    
    def test_power_outlier_detection_spike_detection(self):
        """Test power spike detection using statistical methods."""
        if OutlierDetector is None:
            pytest.skip("OutlierDetector not implemented yet")
        
        detector = OutlierDetector()
        
        # Build history with normal AC power consumption (around 800W ±200W)
        normal_power = [600, 700, 800, 900, 1000, 750, 850, 950, 650, 1050]
        for power in normal_power:
            detector.add_power_sample(float(power))
        
        assert detector.has_sufficient_data() is True
        
        # Test normal variations (should not be outliers)
        assert detector.is_power_outlier(700.0) is False
        assert detector.is_power_outlier(900.0) is False
        assert detector.is_power_outlier(550.0) is False   # Low but not outlier
        
        # Test power spikes (should be detected)
        assert detector.is_power_outlier(2000.0) is True   # Major spike
        assert detector.is_power_outlier(3500.0) is True   # Extreme spike
    
    def test_power_outlier_detection_negative_values(self):
        """Test handling of negative power values."""
        if OutlierDetector is None:
            pytest.skip("OutlierDetector not implemented yet")
        
        detector = OutlierDetector()
        
        # All negative values should be outliers (invalid for AC)
        negative_values = [-1.0, -10.0, -100.0, -0.001]
        for power in negative_values:
            assert detector.is_power_outlier(power) is True
        
        # Zero and positive should be handled normally
        assert detector.is_power_outlier(0.0) is False
        assert detector.is_power_outlier(0.1) is False


class TestStatisticalMethods:
    """Test underlying statistical calculation methods."""
    
    def test_modified_zscore_calculation(self):
        """Test modified Z-score formula implementation."""
        if OutlierDetector is None:
            pytest.skip("OutlierDetector not implemented yet")
        
        detector = OutlierDetector()
        
        # Test data with known statistical properties
        data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        
        # Test modified Z-score calculation
        zscore_5 = detector.calculate_modified_zscore(5.0, data)
        zscore_1 = detector.calculate_modified_zscore(1.0, data)
        zscore_10 = detector.calculate_modified_zscore(10.0, data)
        
        # Middle value should have low Z-score
        assert abs(zscore_5) < 1.0
        
        # End values should have higher Z-scores but not outliers
        assert abs(zscore_1) > abs(zscore_5)
        assert abs(zscore_10) > abs(zscore_5)
        
        # Extreme value should have high Z-score
        zscore_extreme = detector.calculate_modified_zscore(50.0, data)
        assert abs(zscore_extreme) > 2.5  # Should exceed threshold
    
    def test_median_absolute_deviation(self):
        """Test MAD (Median Absolute Deviation) calculation."""
        if OutlierDetector is None:
            pytest.skip("OutlierDetector not implemented yet")
        
        detector = OutlierDetector()
        
        # Test data with known median and MAD
        data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        median_value = statistics.median(data)  # Should be 5.5
        
        mad_value = detector.calculate_mad(data)
        
        # MAD should be positive
        assert mad_value > 0
        
        # For this dataset, MAD should be reasonable (around 2.5)
        assert 2.0 <= mad_value <= 3.0
        
        # Test with constant data (MAD should be 0)
        constant_data = [5.0] * 10
        mad_constant = detector.calculate_mad(constant_data)
        assert mad_constant == 0.0
    
    def test_insufficient_data_handling(self):
        """Test fallback to absolute bounds when insufficient statistical data."""
        if OutlierDetector is None:
            pytest.skip("OutlierDetector not implemented yet")
        
        detector = OutlierDetector()
        
        # With no data, should use absolute bounds only
        assert detector.is_temperature_outlier(-15.0) is True   # Beyond absolute bound
        assert detector.is_temperature_outlier(22.0) is False   # Within absolute bound
        
        # Add insufficient data (less than min_samples_for_stats)
        detector.add_temperature_sample(22.0)
        detector.add_temperature_sample(23.0)
        
        # Should still use absolute bounds, not statistical methods
        assert detector.has_sufficient_data() is False
        assert detector.is_temperature_outlier(-15.0) is True
        assert detector.is_temperature_outlier(22.0) is False


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_zero_variation_detection(self):
        """Test behavior when all historical values are identical."""
        if OutlierDetector is None:
            pytest.skip("OutlierDetector not implemented yet")
        
        detector = OutlierDetector()
        
        # Add identical temperature values
        constant_temp = 22.0
        for _ in range(15):  # Enough for statistical analysis
            detector.add_temperature_sample(constant_temp)
        
        assert detector.has_sufficient_data() is True
        
        # The same value should not be an outlier
        assert detector.is_temperature_outlier(constant_temp) is False
        
        # Any deviation should be detected (since variation is zero)
        assert detector.is_temperature_outlier(constant_temp + 0.1) is True
        assert detector.is_temperature_outlier(constant_temp - 0.1) is True
        
        # But should still respect absolute bounds
        assert detector.is_temperature_outlier(-15.0) is True  # Absolute outlier
    
    def test_single_sample_handling(self):
        """Test behavior with single sample scenarios."""
        if OutlierDetector is None:
            pytest.skip("OutlierDetector not implemented yet")
        
        detector = OutlierDetector()
        
        # Add single sample
        detector.add_temperature_sample(22.0)
        
        assert detector.get_history_size() == 1
        assert detector.has_sufficient_data() is False  # Not enough for stats
        
        # Should fall back to absolute bounds
        assert detector.is_temperature_outlier(-15.0) is True
        assert detector.is_temperature_outlier(25.0) is False
        
        # The sample itself should not be an outlier
        assert detector.is_temperature_outlier(22.0) is False
    
    def test_nan_and_none_handling(self):
        """Test handling of invalid input values (NaN, None)."""
        if OutlierDetector is None:
            pytest.skip("OutlierDetector not implemented yet")
        
        detector = OutlierDetector()
        
        # Test None values
        assert detector.is_temperature_outlier(None) is True
        assert detector.is_power_outlier(None) is True
        
        # Test NaN values  
        import math
        assert detector.is_temperature_outlier(math.nan) is True
        assert detector.is_power_outlier(math.nan) is True
        
        # Test infinity values
        assert detector.is_temperature_outlier(float('inf')) is True
        assert detector.is_temperature_outlier(float('-inf')) is True
        assert detector.is_power_outlier(float('inf')) is True
        assert detector.is_power_outlier(float('-inf')) is True
        
        # Test that adding invalid samples doesn't corrupt history
        initial_size = detector.get_history_size()
        detector.add_temperature_sample(None)
        detector.add_temperature_sample(math.nan)
        detector.add_temperature_sample(float('inf'))
        
        # History size should not change (invalid samples rejected)
        assert detector.get_history_size() == initial_size
    
    def test_string_and_non_numeric_handling(self):
        """Test handling of non-numeric input values."""
        if OutlierDetector is None:
            pytest.skip("OutlierDetector not implemented yet")
        
        detector = OutlierDetector()
        
        # Test string values
        assert detector.is_temperature_outlier("22.0") is True  # String not allowed
        assert detector.is_temperature_outlier("hot") is True   # Non-numeric string
        assert detector.is_power_outlier("150") is True         # String power
        
        # Test other types
        assert detector.is_temperature_outlier([22.0]) is True  # List
        assert detector.is_temperature_outlier({"temp": 22.0}) is True  # Dict
        assert detector.is_power_outlier(True) is True          # Boolean
    
    def test_large_dataset_performance(self):
        """Test performance with large historical datasets."""
        if OutlierDetector is None:
            pytest.skip("OutlierDetector not implemented yet")
        
        detector = OutlierDetector()
        
        # Add large dataset
        import time
        start_time = time.time()
        
        for i in range(1000):
            temp = 22.0 + (i % 10) - 5  # Cyclic pattern around 22°C
            detector.add_temperature_sample(temp)
        
        # Test that outlier detection is still fast
        detection_start = time.time()
        result = detector.is_temperature_outlier(25.0)
        detection_time = time.time() - detection_start
        
        # Should complete within reasonable time (< 10ms)
        assert detection_time < 0.01
        assert isinstance(result, bool)
        
        # History should be managed (not grow indefinitely)
        assert detector.get_history_size() <= 100  # Reasonable cap


@pytest.fixture
def sample_temperature_history():
    """Fixture providing sample temperature history for testing."""
    return [20.0, 20.5, 21.0, 21.5, 22.0, 22.5, 23.0, 23.5, 24.0, 24.5]


@pytest.fixture  
def sample_power_history():
    """Fixture providing sample power consumption history for testing."""
    return [600.0, 700.0, 800.0, 900.0, 1000.0, 750.0, 850.0, 950.0, 650.0, 1050.0]


@pytest.fixture
def outlier_detector_configured():
    """Fixture providing a configured OutlierDetector instance."""
    if OutlierDetector is None:
        pytest.skip("OutlierDetector not implemented yet")
    
    config = {
        'temperature_bounds': (-10.0, 50.0),
        'power_bounds': (0.0, 5000.0),
        'zscore_threshold': 2.5,
        'min_samples_for_stats': 8
    }
    return OutlierDetector(config=config)


class TestOutlierDetectorIntegration:
    """Test OutlierDetector integration scenarios."""
    
    def test_realistic_temperature_scenario(self, outlier_detector_configured, sample_temperature_history):
        """Test with realistic temperature data scenario."""
        if OutlierDetector is None:
            pytest.skip("OutlierDetector not implemented yet")
        
        detector = outlier_detector_configured
        
        # Build history with realistic data
        for temp in sample_temperature_history:
            detector.add_temperature_sample(temp)
        
        # Test realistic scenarios
        assert detector.is_temperature_outlier(22.0) is False   # Normal room temp
        assert detector.is_temperature_outlier(16.0) is True    # Statistical outlier (6.25°C below median)
        assert detector.is_temperature_outlier(19.0) is False   # Cool but within statistical range
        assert detector.is_temperature_outlier(25.0) is False   # Warm but within statistical range
        assert detector.is_temperature_outlier(10.0) is True    # Too cold for this pattern
        assert detector.is_temperature_outlier(35.0) is True    # Too hot for this pattern
    
    def test_realistic_power_scenario(self, outlier_detector_configured, sample_power_history):
        """Test with realistic power consumption data scenario."""
        if OutlierDetector is None:
            pytest.skip("OutlierDetector not implemented yet")
        
        detector = outlier_detector_configured
        
        # Build history with realistic data
        for power in sample_power_history:
            detector.add_power_sample(power)
        
        # Test realistic scenarios
        assert detector.is_power_outlier(800.0) is False    # Normal AC power
        assert detector.is_power_outlier(0.0) is True       # Statistical outlier (825W below median)
        assert detector.is_power_outlier(500.0) is False    # Low but within statistical range
        assert detector.is_power_outlier(1200.0) is False   # High but within statistical range
        assert detector.is_power_outlier(3000.0) is True    # Spike
        assert detector.is_power_outlier(-50.0) is True     # Invalid negative