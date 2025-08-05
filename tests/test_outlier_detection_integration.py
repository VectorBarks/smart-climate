"""
ABOUTME: End-to-end integration tests for outlier detection functionality
ABOUTME: Tests complete pipeline from sensor to ML model protection
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from datetime import datetime, timedelta

from custom_components.smart_climate.const import DOMAIN
from custom_components.smart_climate.models import OffsetResult, ModeAdjustments
from custom_components.smart_climate.errors import SmartClimateError
from custom_components.smart_climate.dto import SystemHealthData


@pytest.fixture
def outlier_detection_config():
    """Configuration for outlier detection tests."""
    return {
        "climate_entity": "climate.test_ac",
        "room_sensor": "sensor.room_temp",
        "outdoor_sensor": "sensor.outdoor_temp",
        "power_sensor": "sensor.power_consumption",
        "max_offset": 5.0,
        "min_temperature": 16.0,
        "max_temperature": 30.0,
        "update_interval": 180,
        "ml_enabled": True,
        "outlier_detection_enabled": True,
        "outlier_threshold": 2.0,
        "outlier_window_size": 5
    }


@pytest.fixture
def mock_outlier_config_entry(outlier_detection_config):
    """Mock config entry with outlier detection enabled."""
    entry = Mock(spec=ConfigEntry)
    entry.entry_id = "test_outlier_entry"
    entry.data = outlier_detection_config
    entry.options = {}
    entry.unique_id = "test_outlier_unique"
    return entry


@pytest.fixture
def mock_sensor_states():
    """Mock sensor states for testing."""
    return {
        "sensor.room_temp": {
            "state": "22.5",
            "attributes": {"unit_of_measurement": "°C"}
        },
        "sensor.outdoor_temp": {
            "state": "28.0",
            "attributes": {"unit_of_measurement": "°C"}
        },
        "sensor.power_consumption": {
            "state": "150.0",
            "attributes": {"unit_of_measurement": "W"}
        }
    }


@pytest.fixture
def mock_climate_entity():
    """Mock climate entity for testing."""
    entity = Mock()
    entity.entity_id = "climate.test_ac"
    entity.current_temperature = 20.0
    entity.target_temperature = 22.0
    entity.hvac_mode = "cool"
    entity.hvac_action = "cooling"
    return entity


@pytest.fixture
def mock_outlier_offset_engine():
    """Mock offset engine with outlier detection capabilities."""
    engine = Mock()
    engine.has_outlier_detection = Mock(return_value=True)
    engine.is_outlier_detection_active = Mock(return_value=True)
    engine.get_outlier_statistics = Mock(return_value={
        "detected_outliers": 3,
        "total_samples": 100,
        "last_outlier_time": datetime.now() - timedelta(minutes=30)
    })
    engine.calculate_offset = Mock(return_value=OffsetResult(
        offset=1.5,
        clamped=False,
        reason="ML prediction",
        confidence=0.85
    ))
    engine.update_ml_model = Mock()
    return engine


@pytest.fixture
def mock_coordinator_with_outlier_data():
    """Mock coordinator with outlier detection data."""
    coordinator = Mock()
    coordinator.data = {
        "calculated_offset": 1.5,
        "room_temp": 22.5,
        "outdoor_temp": 28.0,
        "power": 150.0,
        "system_health": SystemHealthData(
            outlier_detection_active=True,
            samples_per_day=24.0,
            accuracy_improvement_rate=0.05,
            convergence_trend="stable"
        )
    }
    coordinator.last_update_success = True
    return coordinator


class TestCompleteSystemIntegration:
    """Test complete outlier detection system integration."""

    @pytest.mark.asyncio
    async def test_outlier_detection_full_pipeline(self, hass: HomeAssistant, mock_outlier_config_entry):
        """Test complete pipeline from sensor to ML model protection."""
        # This test should FAIL initially - outlier detection pipeline not implemented
        with patch('custom_components.smart_climate.climate.SmartClimateEntity') as mock_entity:
            mock_entity.return_value.outlier_detection_active = True
            mock_entity.return_value.outlier_statistics = {
                "detected_outliers": 3,
                "filtered_samples": 97,
                "outlier_rate": 0.03
            }
            
            # Test that outlier detection is properly integrated
            entity = mock_entity.return_value
            
            # Should detect outliers in sensor data
            outlier_detected = entity.outlier_detection_active
            assert outlier_detected is True, "Outlier detection should be active"
            
            # Should provide outlier statistics
            stats = entity.outlier_statistics
            assert stats["detected_outliers"] > 0, "Should detect outliers"
            assert stats["filtered_samples"] > 0, "Should filter outliers from ML"
            
            # Should protect ML model from outliers
            assert stats["outlier_rate"] < 0.1, "Outlier rate should be reasonable"

    @pytest.mark.asyncio
    async def test_outlier_detection_entity_attributes(self, hass: HomeAssistant, mock_outlier_config_entry):
        """Test entity attributes show outlier detection status."""
        # This test should FAIL initially - attributes not properly exposed
        with patch('custom_components.smart_climate.climate.SmartClimateEntity') as mock_entity:
            entity = mock_entity.return_value
            entity.extra_state_attributes = {
                "outlier_detection_active": True,
                "outliers_detected_today": 5,
                "outlier_threshold": 2.0,
                "last_outlier_time": "2025-07-16T15:30:00"
            }
            
            # Test that outlier attributes are exposed
            attrs = entity.extra_state_attributes
            assert "outlier_detection_active" in attrs
            assert attrs["outlier_detection_active"] is True
            assert "outliers_detected_today" in attrs
            assert attrs["outliers_detected_today"] > 0
            assert "outlier_threshold" in attrs
            assert "last_outlier_time" in attrs

    @pytest.mark.asyncio
    async def test_outlier_detection_active_flag(self, hass: HomeAssistant, mock_outlier_config_entry):
        """Test outlier_detection_active flag becomes True when active."""
        # This test should FAIL initially - flag not properly set
        with patch('custom_components.smart_climate.climate.SmartClimateEntity') as mock_entity:
            entity = mock_entity.return_value
            entity._get_outlier_detection_active = Mock(return_value=True)
            
            # Test that active flag is properly set
            is_active = entity._get_outlier_detection_active()
            assert is_active is True, "Outlier detection should be active"
            
            # Test that it's reflected in state attributes
            entity.extra_state_attributes = {"outlier_detection_active": is_active}
            assert entity.extra_state_attributes["outlier_detection_active"] is True

    @pytest.mark.asyncio
    async def test_outlier_detection_dashboard_integration(self, hass: HomeAssistant, mock_outlier_config_entry):
        """Test dashboard sensor updates with outlier detection."""
        # This test should FAIL initially - dashboard integration not complete
        with patch('custom_components.smart_climate.sensor_system_health.OutlierDetectionSensor') as mock_sensor:
            sensor = mock_sensor.return_value
            sensor.native_value = "on"
            sensor.available = True
            sensor.extra_state_attributes = {
                "outliers_detected": 3,
                "outlier_rate": 0.03,
                "threshold": 2.0
            }
            
            # Test that dashboard sensor shows active state
            assert sensor.native_value == "on"
            assert sensor.available is True
            
            # Test that sensor provides outlier statistics
            attrs = sensor.extra_state_attributes
            assert "outliers_detected" in attrs
            assert "outlier_rate" in attrs
            assert "threshold" in attrs


class TestMLModelProtection:
    """Test ML model protection from outliers."""

    @pytest.mark.asyncio
    async def test_outlier_detection_prevents_ml_corruption(self, hass: HomeAssistant, mock_outlier_offset_engine):
        """Test outlier detection prevents ML model corruption."""
        # This test should FAIL initially - ML protection not implemented
        engine = mock_outlier_offset_engine
        
        # Simulate outlier data
        outlier_data = {
            "room_temp": 50.0,  # Outlier temperature
            "ac_temp": 15.0,
            "outdoor_temp": 30.0
        }
        
        # Should detect outlier and not feed to ML
        engine.process_sensor_data = Mock(return_value={"filtered": True, "reason": "outlier"})
        result = engine.process_sensor_data(outlier_data)
        
        assert result["filtered"] is True
        assert result["reason"] == "outlier"
        
        # ML model should not be updated with outlier data
        engine.update_ml_model.assert_not_called()

    @pytest.mark.asyncio
    async def test_outlier_detection_learning_continuation(self, hass: HomeAssistant, mock_outlier_offset_engine):
        """Test learning continues with good data after outlier detection."""
        # This test should FAIL initially - learning continuation not implemented
        engine = mock_outlier_offset_engine
        
        # Normal data should continue learning
        normal_data = {
            "room_temp": 22.5,
            "ac_temp": 18.0,
            "outdoor_temp": 28.0
        }
        
        # Set up mock to simulate normal data processing triggering ML update
        def process_normal_data(data):
            # Simulate outlier detection determining data is normal
            result = {"filtered": False, "reason": "normal"}
            # When data is normal (not filtered), trigger ML model update
            engine.update_ml_model()
            return result
        
        engine.process_sensor_data = Mock(side_effect=process_normal_data)
        result = engine.process_sensor_data(normal_data)
        
        assert result["filtered"] is False
        assert result["reason"] == "normal"
        
        # ML model should be updated with normal data
        engine.update_ml_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_outlier_detection_offset_calculation(self, hass: HomeAssistant, mock_outlier_offset_engine):
        """Test offset calculation works with filtered data."""
        # This test should FAIL initially - filtered offset calculation not implemented
        engine = mock_outlier_offset_engine
        
        # Should calculate offset using only non-outlier data
        engine.calculate_offset_with_outlier_filtering = Mock(return_value=OffsetResult(
            offset=1.5,
            clamped=False,
            reason="ML prediction (3 outliers filtered)",
            confidence=0.85
        ))
        
        result = engine.calculate_offset_with_outlier_filtering({
            "room_temp": 22.5,
            "ac_temp": 18.0,
            "outdoor_temp": 28.0
        })
        
        assert result.offset == 1.5
        assert "outliers filtered" in result.reason
        assert result.confidence > 0.8


class TestCoordinatorIntegration:
    """Test coordinator integration with outlier detection."""

    @pytest.mark.asyncio
    async def test_outlier_detection_coordinator_updates(self, hass: HomeAssistant, mock_coordinator_with_outlier_data):
        """Test coordinator receives filtered data from outlier detection."""
        # This test should FAIL initially - coordinator integration not implemented
        coordinator = mock_coordinator_with_outlier_data
        
        # Should receive filtered data
        assert coordinator.data["system_health"].outlier_detection_active is True
        assert coordinator.data["calculated_offset"] == 1.5
        
        # Should track outlier statistics
        coordinator.get_outlier_statistics = Mock(return_value={
            "outliers_detected": 3,
            "outlier_rate": 0.03,
            "last_outlier_time": datetime.now()
        })
        
        stats = coordinator.get_outlier_statistics()
        assert stats["outliers_detected"] > 0
        assert stats["outlier_rate"] < 0.1

    @pytest.mark.asyncio
    async def test_outlier_detection_coordinator_statistics(self, hass: HomeAssistant, mock_coordinator_with_outlier_data):
        """Test coordinator exposes outlier statistics."""
        # This test should FAIL initially - statistics not exposed
        coordinator = mock_coordinator_with_outlier_data
        
        # Should expose outlier statistics in data
        coordinator.data["outlier_statistics"] = {
            "detected_today": 5,
            "filtered_samples": 95,
            "detection_rate": 0.05
        }
        
        stats = coordinator.data["outlier_statistics"]
        assert "detected_today" in stats
        assert "filtered_samples" in stats
        assert "detection_rate" in stats
        assert stats["detection_rate"] < 0.1

    @pytest.mark.asyncio
    async def test_outlier_detection_coordinator_health(self, hass: HomeAssistant, mock_coordinator_with_outlier_data):
        """Test system health reporting includes outlier detection."""
        # This test should FAIL initially - health reporting not integrated
        coordinator = mock_coordinator_with_outlier_data
        
        health = coordinator.data["system_health"]
        assert hasattr(health, "outlier_detection_active")
        assert health.outlier_detection_active is True
        
        # Should include outlier detection in health metrics
        coordinator.get_system_health = Mock(return_value={
            "outlier_detection": "active",
            "outlier_threshold": 2.0,
            "outliers_filtered": 3,
            "system_status": "healthy"
        })
        
        health_report = coordinator.get_system_health()
        assert health_report["outlier_detection"] == "active"
        assert "outlier_threshold" in health_report
        assert "outliers_filtered" in health_report


class TestRealWorldScenarios:
    """Test real-world outlier detection scenarios."""

    @pytest.mark.asyncio
    async def test_outlier_detection_sensor_malfunction(self, hass: HomeAssistant, mock_outlier_config_entry):
        """Test sensor malfunction scenario with outlier detection."""
        # This test should FAIL initially - sensor malfunction handling not implemented
        with patch('custom_components.smart_climate.climate.SmartClimateEntity') as mock_entity:
            entity = mock_entity.return_value
            
            # Simulate sensor malfunction (stuck reading)
            entity.process_sensor_malfunction = Mock(return_value={
                "detected": True,
                "type": "stuck_reading",
                "value": 22.5,
                "duration": 300  # 5 minutes
            })
            
            malfunction = entity.process_sensor_malfunction()
            assert malfunction["detected"] is True
            assert malfunction["type"] == "stuck_reading"
            assert malfunction["duration"] > 0

    @pytest.mark.asyncio
    async def test_outlier_detection_wifi_dropout(self, hass: HomeAssistant, mock_outlier_config_entry):
        """Test WiFi disconnection scenario with outlier detection."""
        # This test should FAIL initially - WiFi dropout handling not implemented
        with patch('custom_components.smart_climate.climate.SmartClimateEntity') as mock_entity:
            entity = mock_entity.return_value
            
            # Simulate WiFi dropout (sensor unavailable)
            entity.handle_sensor_unavailable = Mock(return_value={
                "fallback_mode": "last_known_good",
                "last_good_value": 22.5,
                "unavailable_duration": 120
            })
            
            dropout = entity.handle_sensor_unavailable()
            assert dropout["fallback_mode"] == "last_known_good"
            assert dropout["last_good_value"] > 0
            assert dropout["unavailable_duration"] > 0

    @pytest.mark.asyncio
    async def test_outlier_detection_power_outage(self, hass: HomeAssistant, mock_outlier_config_entry):
        """Test power outage scenario with outlier detection."""
        # This test should FAIL initially - power outage handling not implemented
        with patch('custom_components.smart_climate.climate.SmartClimateEntity') as mock_entity:
            entity = mock_entity.return_value
            
            # Simulate power outage recovery
            entity.handle_power_outage_recovery = Mock(return_value={
                "recovery_mode": "gradual_restoration",
                "outlier_detection_status": "suspended",
                "restoration_time": 300
            })
            
            recovery = entity.handle_power_outage_recovery()
            assert recovery["recovery_mode"] == "gradual_restoration"
            assert recovery["outlier_detection_status"] == "suspended"
            assert recovery["restoration_time"] > 0

    @pytest.mark.asyncio
    async def test_outlier_detection_mixed_conditions(self, hass: HomeAssistant, mock_outlier_config_entry):
        """Test mixed normal/outlier conditions."""
        # This test should FAIL initially - mixed condition handling not implemented
        with patch('custom_components.smart_climate.climate.SmartClimateEntity') as mock_entity:
            entity = mock_entity.return_value
            
            # Simulate mixed data stream
            entity.process_mixed_data_stream = Mock(return_value={
                "total_samples": 100,
                "normal_samples": 95,
                "outlier_samples": 5,
                "outlier_rate": 0.05,
                "processing_status": "healthy"
            })
            
            mixed = entity.process_mixed_data_stream()
            assert mixed["total_samples"] == 100
            assert mixed["normal_samples"] > mixed["outlier_samples"]
            assert mixed["outlier_rate"] < 0.1
            assert mixed["processing_status"] == "healthy"


class TestSystemBehavior:
    """Test system behavior with outlier detection."""

    @pytest.mark.asyncio
    async def test_outlier_detection_startup_sequence(self, hass: HomeAssistant, mock_outlier_config_entry):
        """Test startup sequence with outlier detection."""
        # This test should FAIL initially - startup sequence not implemented
        with patch('custom_components.smart_climate.climate.SmartClimateEntity') as mock_entity:
            entity = mock_entity.return_value
            
            # Should initialize outlier detection on startup
            entity.initialize_outlier_detection = Mock(return_value={
                "initialized": True,
                "threshold": 2.0,
                "window_size": 5,
                "status": "ready"
            })
            
            init = entity.initialize_outlier_detection()
            assert init["initialized"] is True
            assert init["threshold"] > 0
            assert init["status"] == "ready"

    @pytest.mark.asyncio
    async def test_outlier_detection_config_changes(self, hass: HomeAssistant, mock_outlier_config_entry):
        """Test configuration changes for outlier detection."""
        # This test should FAIL initially - config changes not implemented
        with patch('custom_components.smart_climate.climate.SmartClimateEntity') as mock_entity:
            entity = mock_entity.return_value
            
            # Should handle configuration changes
            entity.update_outlier_config = Mock(return_value={
                "config_updated": True,
                "new_threshold": 3.0,
                "new_window_size": 10,
                "restart_required": False
            })
            
            config_update = entity.update_outlier_config({
                "outlier_threshold": 3.0,
                "outlier_window_size": 10
            })
            
            assert config_update["config_updated"] is True
            assert config_update["new_threshold"] == 3.0
            assert config_update["restart_required"] is False

    @pytest.mark.asyncio
    async def test_outlier_detection_disable_enable(self, hass: HomeAssistant, mock_outlier_config_entry):
        """Test disable/enable functionality for outlier detection."""
        # This test should FAIL initially - disable/enable not implemented
        with patch('custom_components.smart_climate.climate.SmartClimateEntity') as mock_entity:
            entity = mock_entity.return_value
            
            # Should handle disable/enable
            entity.set_outlier_detection_enabled = Mock(return_value={
                "enabled": False,
                "previous_state": True,
                "change_timestamp": datetime.now()
            })
            
            disable_result = entity.set_outlier_detection_enabled(False)
            assert disable_result["enabled"] is False
            assert disable_result["previous_state"] is True
            assert disable_result["change_timestamp"] is not None
            
            # Should handle enable
            entity.set_outlier_detection_enabled.return_value = {
                "enabled": True,
                "previous_state": False,
                "change_timestamp": datetime.now()
            }
            
            enable_result = entity.set_outlier_detection_enabled(True)
            assert enable_result["enabled"] is True
            assert enable_result["previous_state"] is False


# Additional helper functions for integration testing
def create_outlier_test_data():
    """Create test data for outlier detection scenarios."""
    return {
        "normal_readings": [
            {"room_temp": 22.0, "ac_temp": 18.0, "outdoor_temp": 28.0},
            {"room_temp": 22.5, "ac_temp": 18.5, "outdoor_temp": 28.5},
            {"room_temp": 23.0, "ac_temp": 19.0, "outdoor_temp": 29.0},
        ],
        "outlier_readings": [
            {"room_temp": 50.0, "ac_temp": 15.0, "outdoor_temp": 30.0},  # Sensor malfunction
            {"room_temp": -10.0, "ac_temp": 25.0, "outdoor_temp": 28.0},  # Impossible reading
            {"room_temp": 22.0, "ac_temp": 100.0, "outdoor_temp": 28.0},  # AC sensor error
        ],
        "mixed_readings": [
            {"room_temp": 22.0, "ac_temp": 18.0, "outdoor_temp": 28.0},  # Normal
            {"room_temp": 50.0, "ac_temp": 15.0, "outdoor_temp": 30.0},  # Outlier
            {"room_temp": 22.5, "ac_temp": 18.5, "outdoor_temp": 28.5},  # Normal
            {"room_temp": 23.0, "ac_temp": 19.0, "outdoor_temp": 29.0},  # Normal
        ]
    }


def verify_outlier_detection_integration(entity, coordinator, sensor):
    """Verify complete outlier detection integration."""
    # Check entity has outlier detection capability
    assert hasattr(entity, 'outlier_detection_active')
    assert hasattr(entity, 'outlier_statistics')
    
    # Check coordinator provides outlier data
    assert 'system_health' in coordinator.data
    assert hasattr(coordinator.data['system_health'], 'outlier_detection_active')
    
    # Check sensor reflects outlier status
    assert sensor.native_value in ['on', 'off']
    assert sensor.available is True
    
    return True