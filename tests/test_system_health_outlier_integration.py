"""Tests for system health outlier detection integration."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from custom_components.smart_climate.models import SmartClimateData, ModeAdjustments
from custom_components.smart_climate.dto import SystemHealthData
from custom_components.smart_climate.outlier_detector import OutlierDetector


class TestSystemHealthOutlierIntegration:
    """Test system health integration with outlier detection."""
    
    def test_system_health_includes_outlier_detection_active(self):
        """Test that system health data includes outlier_detection_active field."""
        # This test should fail initially - SystemHealthData needs the field
        from custom_components.smart_climate.dto import SystemHealthData
        
        health_data = SystemHealthData(
            memory_usage_kb=1024.0,
            persistence_latency_ms=5.0,
            outlier_detection_active=True,  # This field should exist
            samples_per_day=480.0
        )
        
        assert hasattr(health_data, 'outlier_detection_active')
        assert health_data.outlier_detection_active is True
        
    def test_system_health_includes_outlier_statistics(self):
        """Test that system health data includes outlier statistics fields."""
        # This test should fail initially - SystemHealthData needs these fields
        from custom_components.smart_climate.dto import SystemHealthData
        
        health_data = SystemHealthData(
            memory_usage_kb=1024.0,
            persistence_latency_ms=5.0,
            outlier_detection_active=True,
            outliers_detected_today=5,  # This field should exist
            samples_per_day=480.0
        )
        
        assert hasattr(health_data, 'outliers_detected_today')
        assert health_data.outliers_detected_today == 5
        
    def test_system_health_tracks_detection_threshold(self):
        """Test that system health data tracks current detection threshold."""
        # This test should fail initially - SystemHealthData needs this field
        from custom_components.smart_climate.dto import SystemHealthData
        
        health_data = SystemHealthData(
            memory_usage_kb=1024.0,
            persistence_latency_ms=5.0,
            outlier_detection_active=True,
            outlier_detection_threshold=2.5,  # This field should exist
            samples_per_day=480.0
        )
        
        assert hasattr(health_data, 'outlier_detection_threshold')
        assert health_data.outlier_detection_threshold == 2.5
        
    def test_system_health_tracks_last_detection_time(self):
        """Test that system health data tracks last outlier detection time."""
        # This test should fail initially - SystemHealthData needs this field
        from custom_components.smart_climate.dto import SystemHealthData
        
        last_detection = datetime.now()
        health_data = SystemHealthData(
            memory_usage_kb=1024.0,
            persistence_latency_ms=5.0,
            outlier_detection_active=True,
            last_outlier_detection_time=last_detection,  # This field should exist
            samples_per_day=480.0
        )
        
        assert hasattr(health_data, 'last_outlier_detection_time')
        assert health_data.last_outlier_detection_time == last_detection
        
    def test_health_data_updates_with_outlier_changes(self):
        """Test that system health data can be constructed with outlier changes."""
        # Test that SystemHealthData can be created with outlier information
        # This tests the data structure integration
        from custom_components.smart_climate.dto import SystemHealthData
        
        # Test creating health data with outlier information
        health_data = SystemHealthData(
            memory_usage_kb=1024.0,
            persistence_latency_ms=5.0,
            outlier_detection_active=True,
            outliers_detected_today=3,
            outlier_detection_threshold=2.5,
            last_outlier_detection_time=datetime.now()
        )
        
        # Verify that all outlier fields are properly set
        assert health_data.outlier_detection_active is True
        assert health_data.outliers_detected_today == 3
        assert health_data.outlier_detection_threshold == 2.5
        assert health_data.last_outlier_detection_time is not None
        
        # Test that the health data can be updated
        health_data.outliers_detected_today = 5
        health_data.last_outlier_detection_time = datetime.now()
        
        assert health_data.outliers_detected_today == 5
        
    def test_health_sensors_reflect_outlier_information(self):
        """Test that system health sensors include outlier information."""
        # This test should fail initially - health sensors need outlier data
        from custom_components.smart_climate.models import SmartClimateData
        
        # Create coordinator data with outlier information
        coordinator_data = SmartClimateData(
            room_temp=22.5,
            outdoor_temp=28.0,
            power=1200.0,
            calculated_offset=2.0,
            mode_adjustments=ModeAdjustments(
                temperature_override=None,
                offset_adjustment=0.0,
                update_interval_override=None,
                boost_offset=0.0
            ),
            outliers={"temperature": True, "power": False},
            outlier_count=1,
            outlier_statistics={
                "enabled": True,
                "temperature_outliers": 1,
                "power_outliers": 0,
                "total_samples": 2,
                "outlier_rate": 0.5,
                "history_size": 10,
                "has_sufficient_data": True
            }
        )
        
        # Test that system health data can be derived from coordinator data
        # This logic needs to be implemented in coordinator._async_update_data
        health_data = SystemHealthData(
            memory_usage_kb=1024.0,
            persistence_latency_ms=5.0,
            outlier_detection_active=True,
            outliers_detected_today=coordinator_data.outlier_count,
            outlier_detection_threshold=2.5,
            last_outlier_detection_time=datetime.now() if coordinator_data.outlier_count > 0 else None
        )
        
        # Verify the health data reflects current outlier state
        assert health_data.outlier_detection_active is True
        assert health_data.outliers_detected_today == 1
        assert health_data.last_outlier_detection_time is not None
        
    def test_coordinator_health_integration_logic(self):
        """Test the logic for integrating outlier detection with health reporting."""
        # This test verifies the integration logic without full coordinator setup
        from custom_components.smart_climate.dto import SystemHealthData
        from custom_components.smart_climate.outlier_detector import OutlierDetector
        
        # Test the logic that would be used in coordinator
        outlier_config = {'temperature_bounds': (-10.0, 50.0), 'zscore_threshold': 2.5}
        outlier_detector = OutlierDetector(config=outlier_config)
        
        # Simulate outlier detection results
        outlier_results = {
            "outliers": {"temperature": True, "power": False},
            "outlier_count": 1,
            "outlier_statistics": {
                "enabled": True,
                "temperature_outliers": 1,
                "power_outliers": 0,
                "total_samples": 2,
                "outlier_rate": 0.5
            }
        }
        
        # Test creating system health data with outlier information  
        outlier_detection_active = True
        outliers_detected_today = outlier_results["outlier_count"]
        outlier_detection_threshold = outlier_detector.zscore_threshold
        last_outlier_detection_time = datetime.now() if outliers_detected_today > 0 else None
        
        health_data = SystemHealthData(
            memory_usage_kb=1024.0,
            persistence_latency_ms=5.0,
            outlier_detection_active=outlier_detection_active,
            outliers_detected_today=outliers_detected_today,
            outlier_detection_threshold=outlier_detection_threshold,
            last_outlier_detection_time=last_outlier_detection_time
        )
        
        # Verify the health data properly reflects outlier information
        assert health_data.outlier_detection_active is True
        assert health_data.outliers_detected_today == 1
        assert health_data.outlier_detection_threshold == 2.5
        assert health_data.last_outlier_detection_time is not None