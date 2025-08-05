"""End-to-end tests for system health outlier integration."""

import pytest
from unittest.mock import Mock
from datetime import datetime

from custom_components.smart_climate.dto import SystemHealthData
from custom_components.smart_climate.outlier_detector import OutlierDetector
from custom_components.smart_climate.offset_engine import OffsetEngine


class TestSystemHealthOutlierEndToEnd:
    """Test end-to-end system health outlier integration."""
    
    def test_offset_engine_generates_system_health_with_outlier_data(self):
        """Test that offset engine generates system health data with outlier information."""
        # Create a real OffsetEngine with outlier detection enabled
        config = {
            'max_offset': 5.0,
            'ml_enabled': True
        }
        
        outlier_config = {
            'temperature_bounds': (-10.0, 50.0),
            'power_bounds': (0.0, 5000.0),
            'zscore_threshold': 2.5
        }
        
        # Create offset engine
        offset_engine = OffsetEngine(config=config, outlier_detection_config=outlier_config)
        
        # Verify outlier detection is enabled
        assert offset_engine.has_outlier_detection() is True
        
        # Test that system health generation methods exist and work
        assert hasattr(offset_engine, '_get_outliers_detected_today')
        assert hasattr(offset_engine, '_get_outlier_detection_threshold')  
        assert hasattr(offset_engine, '_get_last_outlier_detection_time')
        
        # Test the methods return expected types
        outliers_today = offset_engine._get_outliers_detected_today()
        threshold = offset_engine._get_outlier_detection_threshold()
        last_detection = offset_engine._get_last_outlier_detection_time()
        
        assert isinstance(outliers_today, int)
        assert isinstance(threshold, float)
        assert last_detection is None or isinstance(last_detection, datetime)
        
        # Verify threshold matches configured value
        assert threshold == 2.5
        
    def test_system_health_data_includes_all_outlier_fields(self):
        """Test that SystemHealthData properly supports all outlier fields."""
        # Create system health data with all outlier fields
        health_data = SystemHealthData(
            memory_usage_kb=1024.0,
            persistence_latency_ms=5.0,
            outlier_detection_active=True,
            samples_per_day=480.0,
            accuracy_improvement_rate=2.5,
            convergence_trend="improving",
            outliers_detected_today=3,
            outlier_detection_threshold=2.5,
            last_outlier_detection_time=datetime.now()
        )
        
        # Verify all fields are accessible
        assert health_data.outlier_detection_active is True
        assert health_data.outliers_detected_today == 3
        assert health_data.outlier_detection_threshold == 2.5
        assert health_data.last_outlier_detection_time is not None
        
        # Verify the data can be converted to dict (for serialization)
        health_dict = health_data.__dict__
        assert 'outlier_detection_active' in health_dict
        assert 'outliers_detected_today' in health_dict
        assert 'outlier_detection_threshold' in health_dict
        assert 'last_outlier_detection_time' in health_dict
        
    def test_integration_with_disabled_outlier_detection(self):
        """Test system health works correctly when outlier detection is disabled."""
        # Create offset engine without outlier detection
        config = {
            'max_offset': 5.0,
            'ml_enabled': True,
            # No outlier_detection_config
        }
        
        offset_engine = OffsetEngine(config=config)
        
        # Verify outlier detection is disabled
        assert offset_engine.has_outlier_detection() is False
        
        # Test that methods still work but return appropriate defaults
        outliers_today = offset_engine._get_outliers_detected_today()
        threshold = offset_engine._get_outlier_detection_threshold()
        last_detection = offset_engine._get_last_outlier_detection_time()
        
        assert outliers_today == 0  # No outliers when disabled
        assert threshold == 2.5     # Default threshold
        assert last_detection is None  # No detection time when disabled
        
        # Create system health data
        health_data = SystemHealthData(
            outlier_detection_active=False,
            outliers_detected_today=outliers_today,
            outlier_detection_threshold=threshold,
            last_outlier_detection_time=last_detection
        )
        
        assert health_data.outlier_detection_active is False
        assert health_data.outliers_detected_today == 0
        assert health_data.outlier_detection_threshold == 2.5
        assert health_data.last_outlier_detection_time is None