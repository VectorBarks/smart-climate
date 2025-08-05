"""
ABOUTME: Comprehensive end-to-end system integration tests for complete outlier detection system
ABOUTME: Tests complete data flow from sensors through coordinator to entities and dashboard sensors
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform

from custom_components.smart_climate.const import (
    DOMAIN,
    CONF_OUTLIER_DETECTION_ENABLED,
    CONF_OUTLIER_SENSITIVITY,
)
from custom_components.smart_climate.coordinator import SmartClimateCoordinator
from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.outlier_detector import OutlierDetector
from custom_components.smart_climate.models import SmartClimateData, ModeAdjustments, OffsetResult
from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.sensor_manager import SensorManager
from custom_components.smart_climate.mode_manager import ModeManager
from custom_components.smart_climate.temperature_controller import TemperatureController
from custom_components.smart_climate.sensor_system_health import OutlierDetectionSensor
from tests.fixtures.mock_entities import (
    create_mock_hass,
    create_mock_offset_engine,
    create_mock_sensor_manager,
    create_mock_mode_manager,
    create_mock_temperature_controller,
)


@pytest.fixture
def system_hass():
    """Create a comprehensive Home Assistant test environment."""
    hass = create_mock_hass()
    
    # Add realistic entity states for integration testing
    hass.states.async_set("climate.test_ac", "cool", {
        "current_temperature": 20.0,
        "target_temperature": 22.0,
        "hvac_action": "cooling"
    })
    hass.states.async_set("sensor.room_temp", "22.5", {
        "unit_of_measurement": "°C",
        "device_class": "temperature"
    })
    hass.states.async_set("sensor.outdoor_temp", "28.0", {
        "unit_of_measurement": "°C", 
        "device_class": "temperature"
    })
    hass.states.async_set("sensor.power_consumption", "1200.0", {
        "unit_of_measurement": "W",
        "device_class": "power"
    })
    
    return hass


@pytest.fixture
def outlier_detection_config():
    """Configuration with outlier detection enabled."""
    return {
        "climate_entity": "climate.test_ac",
        "room_sensor": "sensor.room_temp", 
        "outdoor_sensor": "sensor.outdoor_temp",
        "power_sensor": "sensor.power_consumption",
        "max_offset": 5.0,
        "update_interval": 180,
        "ml_enabled": True,
        CONF_OUTLIER_DETECTION_ENABLED: True,
        CONF_OUTLIER_SENSITIVITY: 2.5,
    }


@pytest.fixture
def system_sensor_manager(system_hass):
    """Create a sensor manager with realistic data."""
    sensor_manager = Mock(spec=SensorManager)
    sensor_manager.get_room_temperature.return_value = 22.5
    sensor_manager.get_outdoor_temperature.return_value = 28.0
    sensor_manager.get_power_consumption.return_value = 1200.0
    sensor_manager.start_listening = AsyncMock()
    sensor_manager.stop_listening = AsyncMock()
    return sensor_manager


@pytest.fixture
def system_offset_engine():
    """Create offset engine with ML model protection."""
    engine = Mock(spec=OffsetEngine)
    engine.calculate_offset.return_value = OffsetResult(
        offset=1.5,
        clamped=False,
        reason="ML prediction",
        confidence=0.85
    )
    engine.has_outlier_detection.return_value = True
    engine.record_actual_performance = Mock()
    return engine


@pytest.fixture
def realistic_sensor_data():
    """Realistic sensor data scenarios for testing."""
    return {
        "normal_scenario": {
            "room_temps": [22.0, 22.5, 23.0, 22.5, 22.0, 21.5, 22.0, 22.5, 23.0, 22.0],
            "outdoor_temps": [28.0, 28.5, 29.0, 28.5, 28.0, 27.5, 28.0, 28.5, 29.0, 28.0],
            "power_values": [1200, 1150, 1300, 1250, 1200, 1100, 1200, 1150, 1300, 1200]
        },
        "outlier_scenario": {
            "room_temps": [22.0, 22.5, 45.0, 22.5, 22.0, 21.5, -5.0, 22.5, 23.0, 22.0],  # 45°C and -5°C outliers
            "outdoor_temps": [28.0, 28.5, 29.0, 28.5, 28.0, 27.5, 28.0, 28.5, 29.0, 28.0],
            "power_values": [1200, 1150, 4500, 1250, 1200, 1100, 1200, 6000, 1300, 1200]  # 4500W and 6000W spikes
        },
        "mixed_scenario": {
            "room_temps": [22.0, 22.5, 35.0, 22.5, 22.0, 21.5, 22.0, 22.5, 50.0, 22.0],  # Some outliers
            "outdoor_temps": [28.0, 28.5, 29.0, 28.5, 28.0, 27.5, 28.0, 28.5, 29.0, 28.0],
            "power_values": [1200, 1150, 1300, 3000, 1200, 1100, 1200, 1150, 1300, 1200]  # One power spike
        }
    }


class TestCompleteOutlierDetectionLifecycle:
    """Test complete outlier detection system lifecycle."""
    
    @pytest.mark.asyncio
    async def test_complete_outlier_detection_lifecycle(self, system_hass, outlier_detection_config, system_sensor_manager, system_offset_engine):
        """Test complete lifecycle from setup to operation with outlier detection."""
        
        # Arrange - Create complete system with outlier detection enabled
        mode_manager = create_mock_mode_manager()
        mode_manager.get_adjustments.return_value = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        )
        
        # Create coordinator with outlier detection config
        coordinator = SmartClimateCoordinator(
            hass=system_hass,
            update_interval=180,
            sensor_manager=system_sensor_manager,
            offset_engine=system_offset_engine,
            mode_manager=mode_manager,
            outlier_detection_config=outlier_detection_config
        )
        
        # Create climate entity
        entity = SmartClimateEntity(
            hass=system_hass,
            config={"name": "Test Smart Climate"},
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=system_offset_engine,
            sensor_manager=system_sensor_manager,
            mode_manager=mode_manager,
            temperature_controller=create_mock_temperature_controller(),
            coordinator=coordinator,
        )
        entity.entity_id = "climate.smart_test"
        
        # Act - Execute complete lifecycle
        # 1. Initialize system
        await coordinator.async_config_entry_first_refresh()
        
        # 2. Verify outlier detection is active
        assert coordinator.outlier_detection_enabled is True
        assert coordinator._outlier_detector is not None
        
        # 3. Verify data update includes outlier detection
        data = coordinator.data
        assert hasattr(data, 'outliers')
        assert hasattr(data, 'outlier_count')
        assert hasattr(data, 'outlier_statistics')
        
        # 4. Verify entity reflects outlier detection state
        assert entity.outlier_detection_active is True
        
        # 5. Verify attributes include outlier information
        attributes = entity.extra_state_attributes
        assert "is_outlier" in attributes
        assert "outlier_statistics" in attributes
        
        # Assert - Complete system is operational
        assert data.outlier_statistics["enabled"] is True
        assert isinstance(data.outlier_count, int)
        assert isinstance(data.outliers, dict)
        
        # Verify system health data includes outlier information
        assert data.outlier_statistics["total_samples"] >= 0
        assert data.outlier_statistics["outlier_rate"] >= 0.0


class TestOutlierDetectionWithRealSensorData:
    """Test outlier detection with realistic sensor data scenarios."""
    
    @pytest.mark.asyncio 
    async def test_outlier_detection_with_real_sensor_data(self, system_hass, outlier_detection_config, realistic_sensor_data):
        """Test outlier detection with realistic sensor data patterns."""
        
        # Arrange - Create system components
        sensor_manager = Mock(spec=SensorManager)
        offset_engine = Mock(spec=OffsetEngine)
        mode_manager = create_mock_mode_manager()
        
        # Use normal scenario data initially
        normal_data = realistic_sensor_data["normal_scenario"]
        sensor_manager.get_room_temperature.return_value = normal_data["room_temps"][0]
        sensor_manager.get_outdoor_temperature.return_value = normal_data["outdoor_temps"][0]
        sensor_manager.get_power_consumption.return_value = normal_data["power_values"][0]
        
        offset_engine.calculate_offset.return_value = OffsetResult(
            offset=1.5, clamped=False, reason="ML prediction", confidence=0.85
        )
        
        coordinator = SmartClimateCoordinator(
            hass=system_hass,
            update_interval=180,
            sensor_manager=sensor_manager,
            offset_engine=offset_engine,
            mode_manager=mode_manager,
            outlier_detection_config=outlier_detection_config
        )
        
        # Act - Process normal data sequence
        await coordinator.async_config_entry_first_refresh()
        
        # Simulate processing normal data points
        normal_outlier_count = 0
        for i in range(len(normal_data["room_temps"])):
            sensor_manager.get_room_temperature.return_value = normal_data["room_temps"][i]
            sensor_manager.get_outdoor_temperature.return_value = normal_data["outdoor_temps"][i] 
            sensor_manager.get_power_consumption.return_value = normal_data["power_values"][i]
            
            await coordinator.async_request_refresh()
            
            # Normal data should not trigger many outliers
            if coordinator.data.outlier_count > 0:
                normal_outlier_count += 1
        
        # Assert - Normal data produces minimal outliers
        assert normal_outlier_count <= 2, f"Normal data triggered {normal_outlier_count} outliers, expected <= 2"
        
        # Act - Process outlier scenario data
        outlier_data = realistic_sensor_data["outlier_scenario"]
        outlier_detections = 0
        
        for i in range(len(outlier_data["room_temps"])):
            sensor_manager.get_room_temperature.return_value = outlier_data["room_temps"][i]
            sensor_manager.get_outdoor_temperature.return_value = outlier_data["outdoor_temps"][i]
            sensor_manager.get_power_consumption.return_value = outlier_data["power_values"][i]
            
            await coordinator.async_request_refresh()
            
            # Count outlier detections
            if coordinator.data.outlier_count > 0:
                outlier_detections += 1
        
        # Assert - Outlier scenario produces more detections
        assert outlier_detections >= 3, f"Outlier data triggered {outlier_detections} detections, expected >= 3"
        
        # Verify outlier statistics are updated
        stats = coordinator.data.outlier_statistics
        assert stats["total_samples"] > 10
        assert stats["outlier_rate"] > 0.0


class TestSystemBehaviorWithOutlierSpikes:
    """Test system response to actual outlier conditions."""
    
    @pytest.mark.asyncio
    async def test_system_behavior_with_outlier_spikes(self, system_hass, outlier_detection_config, system_sensor_manager, system_offset_engine):
        """Test system response to temperature and power spikes."""
        
        # Arrange - Create system with outlier detection
        coordinator = SmartClimateCoordinator(
            hass=system_hass,
            update_interval=180,
            sensor_manager=system_sensor_manager,
            offset_engine=system_offset_engine,
            mode_manager=create_mock_mode_manager(),
            outlier_detection_config=outlier_detection_config
        )
        
        entity = SmartClimateEntity(
            hass=system_hass,
            config={"name": "Test Smart Climate"},
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=system_offset_engine,
            sensor_manager=system_sensor_manager,
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=coordinator,
        )
        entity.entity_id = "climate.smart_test"
        
        await coordinator.async_config_entry_first_refresh()
        
        # Act - Simulate normal operation first
        system_sensor_manager.get_room_temperature.return_value = 22.5
        system_sensor_manager.get_power_consumption.return_value = 1200.0
        await coordinator.async_request_refresh()
        
        normal_data = coordinator.data
        normal_outlier_count = normal_data.outlier_count
        
        # Act - Simulate temperature spike (sensor malfunction)
        system_sensor_manager.get_room_temperature.return_value = 55.0  # Extreme temperature
        await coordinator.async_request_refresh()
        
        temp_spike_data = coordinator.data
        
        # Act - Simulate power spike (AC malfunction)
        system_sensor_manager.get_room_temperature.return_value = 22.5  # Normal temp
        system_sensor_manager.get_power_consumption.return_value = 7000.0  # Extreme power
        await coordinator.async_request_refresh()
        
        power_spike_data = coordinator.data
        
        # Assert - System detects and responds to spikes
        assert temp_spike_data.outlier_count > normal_outlier_count, "Temperature spike should increase outlier count"
        assert power_spike_data.outlier_count > normal_outlier_count, "Power spike should increase outlier count"
        
        # Verify entity reflects spike detection
        entity_attrs = entity.extra_state_attributes
        assert entity_attrs["outlier_statistics"]["total_samples"] > 0
        assert entity_attrs["outlier_statistics"]["outlier_rate"] > 0.0
        
        # Act - Return to normal values
        system_sensor_manager.get_room_temperature.return_value = 22.5
        system_sensor_manager.get_power_consumption.return_value = 1200.0
        await coordinator.async_request_refresh()
        
        recovery_data = coordinator.data
        
        # Assert - System continues operating normally after spikes
        assert recovery_data.outlier_statistics["enabled"] is True
        assert entity.outlier_detection_active is True


class TestMLModelProtectionIntegration:
    """Test ML model protection from outliers end-to-end."""
    
    @pytest.mark.asyncio
    async def test_ml_model_protection_integration(self, system_hass, outlier_detection_config):
        """Test ML model protection prevents corruption from outlier data."""
        
        # Arrange - Create offset engine that tracks ML model updates
        offset_engine = Mock(spec=OffsetEngine)
        offset_engine.calculate_offset.return_value = OffsetResult(
            offset=1.5, clamped=False, reason="ML prediction", confidence=0.85
        )
        offset_engine.has_outlier_detection.return_value = True
        offset_engine.record_actual_performance = Mock()
        
        sensor_manager = Mock(spec=SensorManager)
        sensor_manager.get_room_temperature.return_value = 22.5
        sensor_manager.get_outdoor_temperature.return_value = 28.0
        sensor_manager.get_power_consumption.return_value = 1200.0
        
        coordinator = SmartClimateCoordinator(
            hass=system_hass,
            update_interval=180,
            sensor_manager=sensor_manager,
            offset_engine=offset_engine,
            mode_manager=create_mock_mode_manager(),
            outlier_detection_config=outlier_detection_config
        )
        
        await coordinator.async_config_entry_first_refresh()
        
        # Act - Process normal data (should update ML model)
        normal_data_cycles = 5
        for _ in range(normal_data_cycles):
            sensor_manager.get_room_temperature.return_value = 22.5 + (_ * 0.1)  # Slight variation
            sensor_manager.get_power_consumption.return_value = 1200 + (_ * 10)    # Slight variation
            await coordinator.async_request_refresh()
        
        normal_ml_calls = offset_engine.record_actual_performance.call_count
        
        # Act - Process outlier data (should NOT update ML model)
        outlier_scenarios = [
            (55.0, 1200.0),   # Temperature outlier
            (22.5, 8000.0),   # Power outlier  
            (-10.0, 1200.0),  # Extreme temperature outlier
            (22.5, -500.0),   # Invalid power outlier
        ]
        
        for temp, power in outlier_scenarios:
            sensor_manager.get_room_temperature.return_value = temp
            sensor_manager.get_power_consumption.return_value = power
            await coordinator.async_request_refresh()
        
        # Assert - ML model updates should not increase due to outliers
        final_ml_calls = offset_engine.record_actual_performance.call_count
        
        # ML model should be protected from outlier data
        # Normal data should trigger updates, outliers should not
        assert final_ml_calls <= normal_ml_calls + 1, f"ML model received {final_ml_calls - normal_ml_calls} outlier updates, expected <= 1"
        
        # Verify outlier detection statistics show filtering
        final_data = coordinator.data
        assert final_data.outlier_statistics["total_samples"] > 0
        assert final_data.outlier_count > 0  # Outliers were detected
        assert final_data.outlier_statistics["outlier_rate"] > 0.0


class TestDashboardReflectsOutlierDetection:
    """Test dashboard sensors reflect actual outlier detection state."""
    
    @pytest.mark.asyncio
    async def test_dashboard_reflects_outlier_detection(self, system_hass, outlier_detection_config):
        """Test dashboard sensors accurately reflect outlier detection state."""
        
        # Arrange - Create full system with dashboard sensors
        coordinator = SmartClimateCoordinator(
            hass=system_hass,
            update_interval=180,
            sensor_manager=create_mock_sensor_manager(),
            offset_engine=create_mock_offset_engine(),
            mode_manager=create_mock_mode_manager(),
            outlier_detection_config=outlier_detection_config
        )
        
        # Create dashboard sensors
        outlier_detection_sensor = OutlierDetectionSensor(coordinator, "climate.smart_test")
        # Note: OutlierCountSensor not implemented in current design
        
        await coordinator.async_config_entry_first_refresh()
        
        # Act - Test initial state (no outliers)
        initial_detection = outlier_detection_sensor.is_on
        initial_count = outlier_count_sensor.native_value
        initial_attrs = outlier_detection_sensor.extra_state_attributes
        
        # Simulate outlier detection by updating coordinator data
        coordinator.data.outliers = {"climate.smart_test": True}
        coordinator.data.outlier_count = 1
        coordinator.data.outlier_statistics.update({
            "temperature_outliers": 1,
            "power_outliers": 0,
            "total_samples": 25,
            "outlier_rate": 0.04
        })
        
        # Act - Check sensors reflect outlier detection
        detection_with_outlier = outlier_detection_sensor.is_on
        count_with_outlier = outlier_count_sensor.native_value
        attrs_with_outlier = outlier_detection_sensor.extra_state_attributes
        
        # Assert - Dashboard sensors reflect actual outlier state
        assert initial_detection is False, "Initial state should show no outlier"
        assert initial_count == 0, "Initial count should be 0"
        
        assert detection_with_outlier is True, "Detection sensor should show outlier detected"
        assert count_with_outlier == 1, "Count sensor should show 1 outlier"
        
        # Verify sensor attributes provide detailed information
        assert attrs_with_outlier["outlier_count"] == 1
        assert attrs_with_outlier["outlier_rate"] == 0.04
        assert attrs_with_outlier["detection_enabled"] is True
        
        # Act - Test outlier resolution
        coordinator.data.outliers = {"climate.smart_test": False}
        coordinator.data.outlier_count = 0
        coordinator.data.outlier_statistics.update({
            "temperature_outliers": 0,
            "power_outliers": 0,
            "total_samples": 26,
            "outlier_rate": 0.0
        })
        
        # Assert - Sensors reflect outlier resolution
        resolved_detection = outlier_detection_sensor.is_on
        resolved_count = outlier_count_sensor.native_value
        
        assert resolved_detection is False, "Detection sensor should show no outlier"
        assert resolved_count == 0, "Count sensor should return to 0"


class TestConfigurationChangesAffectSystem:
    """Test configuration changes affect entire outlier detection system."""
    
    @pytest.mark.asyncio
    async def test_configuration_changes_affect_system(self, system_hass):
        """Test that configuration changes propagate through entire system."""
        
        # Arrange - Create system with outlier detection disabled initially
        disabled_config = {
            CONF_OUTLIER_DETECTION_ENABLED: False,
            CONF_OUTLIER_SENSITIVITY: 2.5,
        }
        
        coordinator = SmartClimateCoordinator(
            hass=system_hass,
            update_interval=180,
            sensor_manager=create_mock_sensor_manager(),
            offset_engine=create_mock_offset_engine(),
            mode_manager=create_mock_mode_manager(),
            outlier_detection_config=None  # Disabled
        )
        
        entity = SmartClimateEntity(
            hass=system_hass,
            config={"name": "Test Smart Climate"},
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=create_mock_offset_engine(),
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=coordinator,
        )
        entity.entity_id = "climate.smart_test"
        
        await coordinator.async_config_entry_first_refresh()
        
        # Assert - System reflects disabled state
        assert coordinator.outlier_detection_enabled is False
        assert entity.outlier_detection_active is False
        assert coordinator.data.outlier_statistics["enabled"] is False
        
        # Act - Enable outlier detection with new configuration
        enabled_config = {
            CONF_OUTLIER_DETECTION_ENABLED: True,
            CONF_OUTLIER_SENSITIVITY: 1.5,  # More sensitive
        }
        
        # Simulate config change by creating new coordinator (as would happen in HA)
        new_coordinator = SmartClimateCoordinator(
            hass=system_hass,
            update_interval=180,
            sensor_manager=create_mock_sensor_manager(),
            offset_engine=create_mock_offset_engine(),
            mode_manager=create_mock_mode_manager(),
            outlier_detection_config=enabled_config
        )
        
        # Update entity with new coordinator
        entity._coordinator = new_coordinator
        await new_coordinator.async_config_entry_first_refresh()
        
        # Assert - System reflects enabled state with new sensitivity
        assert new_coordinator.outlier_detection_enabled is True
        assert entity.outlier_detection_active is True
        assert new_coordinator.data.outlier_statistics["enabled"] is True
        
        # Verify sensitivity change affects outlier detector
        assert new_coordinator._outlier_detector is not None
        # Sensitivity would be passed to OutlierDetector constructor in real implementation
        
        # Act - Change sensitivity again
        high_sensitivity_config = {
            CONF_OUTLIER_DETECTION_ENABLED: True,
            CONF_OUTLIER_SENSITIVITY: 1.0,  # Very sensitive
        }
        
        very_sensitive_coordinator = SmartClimateCoordinator(
            hass=system_hass,
            update_interval=180,
            sensor_manager=create_mock_sensor_manager(),
            offset_engine=create_mock_offset_engine(),
            mode_manager=create_mock_mode_manager(),
            outlier_detection_config=high_sensitivity_config
        )
        
        await very_sensitive_coordinator.async_config_entry_first_refresh()
        
        # Assert - High sensitivity configuration is applied
        assert very_sensitive_coordinator.outlier_detection_enabled is True
        assert very_sensitive_coordinator._outlier_detector is not None


class TestSystemRecoveryFromOutlierConditions:
    """Test system recovery when outlier conditions are resolved."""
    
    @pytest.mark.asyncio
    async def test_system_recovery_from_outlier_conditions(self, system_hass, outlier_detection_config):
        """Test system recovery and normal operation after outlier conditions resolve."""
        
        # Arrange - Create system with outlier detection
        sensor_manager = Mock(spec=SensorManager)
        coordinator = SmartClimateCoordinator(
            hass=system_hass,
            update_interval=180,
            sensor_manager=sensor_manager,
            offset_engine=create_mock_offset_engine(),
            mode_manager=create_mock_mode_manager(),
            outlier_detection_config=outlier_detection_config
        )
        
        entity = SmartClimateEntity(
            hass=system_hass,
            config={"name": "Test Smart Climate"},
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=create_mock_offset_engine(),
            sensor_manager=sensor_manager,
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=coordinator,
        )
        entity.entity_id = "climate.smart_test"
        
        await coordinator.async_config_entry_first_refresh()
        
        # Act - Simulate outlier condition (sensor malfunction)
        sensor_manager.get_room_temperature.return_value = 55.0  # Extreme outlier
        sensor_manager.get_outdoor_temperature.return_value = 28.0
        sensor_manager.get_power_consumption.return_value = 1200.0
        
        # Process outlier data for several cycles
        outlier_cycles = 5
        for _ in range(outlier_cycles):
            await coordinator.async_request_refresh()
        
        # Capture outlier state
        outlier_data = coordinator.data
        outlier_count = outlier_data.outlier_count
        outlier_stats = outlier_data.outlier_statistics.copy()
        
        # Act - Simulate recovery (sensor returns to normal)
        sensor_manager.get_room_temperature.return_value = 22.5  # Normal temperature
        
        # Process normal data for several cycles
        recovery_cycles = 10
        for _ in range(recovery_cycles):
            await coordinator.async_request_refresh()
        
        # Capture recovery state
        recovery_data = coordinator.data
        recovery_stats = recovery_data.outlier_statistics
        
        # Assert - System demonstrates recovery
        assert outlier_count > 0, "System should have detected outliers"
        assert outlier_stats["outlier_rate"] > 0.0, "Outlier rate should be > 0 during malfunction"
        
        # System should continue operating normally after recovery
        assert recovery_data.outlier_statistics["enabled"] is True, "Outlier detection should remain enabled"
        assert recovery_stats["total_samples"] > outlier_stats["total_samples"], "System should continue collecting samples"
        
        # Entity should reflect normal operation
        assert entity.outlier_detection_active is True, "Entity outlier detection should remain active"
        
        # Outlier rate should decrease as normal samples are added
        if recovery_stats["total_samples"] > outlier_stats["total_samples"]:
            # With more normal samples, outlier rate should trend down
            assert recovery_stats["outlier_rate"] <= outlier_stats["outlier_rate"], "Outlier rate should not increase with normal data"


class TestMultipleClimateEntitiesIndependence:
    """Test outlier detection independence across multiple climate entities."""
    
    @pytest.mark.asyncio
    async def test_multiple_climate_entities_independence(self, system_hass, outlier_detection_config):
        """Test that outlier detection works independently for multiple climate entities."""
        
        # Arrange - Create coordinator and multiple entities
        coordinator = SmartClimateCoordinator(
            hass=system_hass,
            update_interval=180,
            sensor_manager=create_mock_sensor_manager(),
            offset_engine=create_mock_offset_engine(),
            mode_manager=create_mock_mode_manager(),
            outlier_detection_config=outlier_detection_config
        )
        
        # Create three climate entities
        entities = []
        entity_configs = [
            {"entity_id": "climate.smart_test_1", "name": "Smart Climate 1"},
            {"entity_id": "climate.smart_test_2", "name": "Smart Climate 2"},
            {"entity_id": "climate.smart_test_3", "name": "Smart Climate 3"},
        ]
        
        for config in entity_configs:
            entity = SmartClimateEntity(
                hass=system_hass,
                config={"name": config["name"]},
                wrapped_entity_id=f"climate.test_ac_{config['entity_id'][-1]}",
                room_sensor_id=f"sensor.room_temp_{config['entity_id'][-1]}",
                offset_engine=create_mock_offset_engine(),
                sensor_manager=create_mock_sensor_manager(),
                mode_manager=create_mock_mode_manager(),
                temperature_controller=create_mock_temperature_controller(),
                coordinator=coordinator,
            )
            entity.entity_id = config["entity_id"]
            entities.append(entity)
        
        await coordinator.async_config_entry_first_refresh()
        
        # Act - Simulate different outlier states for different entities
        coordinator.data.outliers = {
            "climate.smart_test_1": False,  # Normal
            "climate.smart_test_2": True,   # Outlier detected
            "climate.smart_test_3": False,  # Normal
        }
        coordinator.data.outlier_count = 1
        coordinator.data.outlier_statistics.update({
            "temperature_outliers": 1,
            "power_outliers": 0,
            "total_samples": 50,
            "outlier_rate": 0.02
        })
        
        # Assert - Each entity reflects its independent outlier state
        assert entities[0].outlier_detected is False, "Entity 1 should not have outlier"
        assert entities[1].outlier_detected is True, "Entity 2 should have outlier"
        assert entities[2].outlier_detected is False, "Entity 3 should not have outlier"
        
        # All entities should have outlier detection active
        for entity in entities:
            assert entity.outlier_detection_active is True, f"{entity.entity_id} should have outlier detection active"
        
        # All entities should share same outlier statistics from coordinator
        for entity in entities:
            attrs = entity.extra_state_attributes
            assert attrs["outlier_statistics"]["total_samples"] == 50
            assert attrs["outlier_statistics"]["outlier_rate"] == 0.02
            assert attrs["outlier_statistics"]["enabled"] is True
        
        # Act - Change outlier status for specific entities
        coordinator.data.outliers = {
            "climate.smart_test_1": True,   # Now has outlier
            "climate.smart_test_2": False,  # Outlier resolved
            "climate.smart_test_3": True,   # Now has outlier
        }
        coordinator.data.outlier_count = 2
        
        # Assert - Entities reflect independent status changes
        assert entities[0].outlier_detected is True, "Entity 1 should now have outlier"
        assert entities[1].outlier_detected is False, "Entity 2 should no longer have outlier"
        assert entities[2].outlier_detected is True, "Entity 3 should now have outlier"
        
        # Verify entity attributes reflect independent outlier states
        for i, entity in enumerate(entities):
            attrs = entity.extra_state_attributes
            expected_outlier = coordinator.data.outliers[entity.entity_id]
            assert attrs["is_outlier"] == expected_outlier, f"Entity {i+1} attributes should reflect outlier state"


class TestSystemPerformanceWithOutlierDetection:
    """Test system performance impact of outlier detection."""
    
    @pytest.mark.asyncio
    async def test_system_performance_with_outlier_detection(self, system_hass, outlier_detection_config):
        """Test that outlier detection does not significantly impact system performance."""
        
        # Arrange - Create system with outlier detection enabled
        coordinator_with_outliers = SmartClimateCoordinator(
            hass=system_hass,
            update_interval=180,
            sensor_manager=create_mock_sensor_manager(),
            offset_engine=create_mock_offset_engine(),
            mode_manager=create_mock_mode_manager(),
            outlier_detection_config=outlier_detection_config
        )
        
        # Create system without outlier detection for comparison
        coordinator_without_outliers = SmartClimateCoordinator(
            hass=system_hass,
            update_interval=180,
            sensor_manager=create_mock_sensor_manager(),
            offset_engine=create_mock_offset_engine(),
            mode_manager=create_mock_mode_manager(),
            outlier_detection_config=None  # Disabled
        )
        
        # Act - Measure performance with outlier detection
        import time
        
        # Initialize both coordinators
        await coordinator_with_outliers.async_config_entry_first_refresh()
        await coordinator_without_outliers.async_config_entry_first_refresh()
        
        # Measure time for data updates with outlier detection
        start_time = time.time()
        update_cycles = 20
        
        for _ in range(update_cycles):
            await coordinator_with_outliers.async_request_refresh()
        
        outlier_detection_time = time.time() - start_time
        
        # Measure time for data updates without outlier detection
        start_time = time.time()
        
        for _ in range(update_cycles):
            await coordinator_without_outliers.async_request_refresh()
        
        no_outlier_detection_time = time.time() - start_time
        
        # Assert - Performance impact should be minimal
        performance_overhead = outlier_detection_time - no_outlier_detection_time
        overhead_percentage = (performance_overhead / no_outlier_detection_time) * 100
        
        # Outlier detection should add < 50% overhead (generous allowance for testing)
        assert overhead_percentage < 50, f"Outlier detection adds {overhead_percentage:.1f}% overhead, expected < 50%"
        
        # Both update cycles should complete in reasonable time (< 2 seconds each)
        assert outlier_detection_time < 2.0, f"Updates with outlier detection took {outlier_detection_time:.2f}s, expected < 2.0s"
        assert no_outlier_detection_time < 2.0, f"Updates without outlier detection took {no_outlier_detection_time:.2f}s, expected < 2.0s"
        
        # Verify system functionality is maintained
        assert coordinator_with_outliers.data is not None
        assert coordinator_with_outliers.outlier_detection_enabled is True
        assert coordinator_without_outliers.data is not None
        assert coordinator_without_outliers.outlier_detection_enabled is False
        
        # Act - Test performance under high outlier load
        sensor_manager = Mock(spec=SensorManager)
        
        # Create alternating normal/outlier data to stress test outlier detection
        outlier_values = [22.5, 65.0, 22.0, -15.0, 23.0, 75.0, 21.5, -20.0, 22.5, 80.0]
        
        start_time = time.time()
        for temp in outlier_values:
            sensor_manager.get_room_temperature.return_value = temp
            sensor_manager.get_outdoor_temperature.return_value = 28.0
            sensor_manager.get_power_consumption.return_value = 1200.0
            
            # Update coordinator with stress test sensor manager
            coordinator_with_outliers._sensor_manager = sensor_manager
            await coordinator_with_outliers.async_request_refresh()
        
        stress_test_time = time.time() - start_time
        
        # Assert - System handles high outlier load efficiently
        assert stress_test_time < 1.0, f"Stress test took {stress_test_time:.2f}s, expected < 1.0s"
        
        # Verify outlier detection still works under load
        final_data = coordinator_with_outliers.data
        assert final_data.outlier_statistics["total_samples"] > 0
        assert final_data.outlier_statistics["enabled"] is True


class TestErrorHandlingAcrossSystemComponents:
    """Test error handling and resilience across all system components."""
    
    @pytest.mark.asyncio
    async def test_error_handling_across_system_components(self, system_hass, outlier_detection_config):
        """Test robust error handling across all outlier detection system components."""
        
        # Arrange - Create system with outlier detection
        sensor_manager = Mock(spec=SensorManager)
        offset_engine = Mock(spec=OffsetEngine)
        
        coordinator = SmartClimateCoordinator(
            hass=system_hass,
            update_interval=180,
            sensor_manager=sensor_manager,
            offset_engine=offset_engine,
            mode_manager=create_mock_mode_manager(),
            outlier_detection_config=outlier_detection_config
        )
        
        entity = SmartClimateEntity(
            hass=system_hass,
            config={"name": "Test Smart Climate"},
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=coordinator,
        )
        entity.entity_id = "climate.smart_test"
        
        await coordinator.async_config_entry_first_refresh()
        
        # Act & Assert - Test sensor failure scenarios
        
        # 1. Sensor returns None values
        sensor_manager.get_room_temperature.return_value = None
        sensor_manager.get_outdoor_temperature.return_value = None
        sensor_manager.get_power_consumption.return_value = None
        
        # System should handle None gracefully
        await coordinator.async_request_refresh()
        
        assert coordinator.data is not None, "Coordinator should handle None sensor values"
        assert entity.outlier_detection_active is True, "Entity should remain active with None sensors"
        
        # 2. Sensor raises exceptions
        sensor_manager.get_room_temperature.side_effect = Exception("Sensor communication error")
        sensor_manager.get_outdoor_temperature.side_effect = Exception("Sensor timeout")
        sensor_manager.get_power_consumption.side_effect = Exception("Sensor hardware failure")
        
        # System should handle exceptions gracefully
        await coordinator.async_request_refresh()
        
        assert coordinator.data is not None, "Coordinator should handle sensor exceptions"
        assert entity.outlier_detection_active is True, "Entity should remain active with sensor exceptions"
        
        # 3. Reset sensors for further testing
        sensor_manager.get_room_temperature.side_effect = None
        sensor_manager.get_outdoor_temperature.side_effect = None
        sensor_manager.get_power_consumption.side_effect = None
        sensor_manager.get_room_temperature.return_value = 22.5
        sensor_manager.get_outdoor_temperature.return_value = 28.0
        sensor_manager.get_power_consumption.return_value = 1200.0
        
        # Act & Assert - Test offset engine failure scenarios
        
        # 4. Offset engine calculation fails
        offset_engine.calculate_offset.side_effect = Exception("ML model error")
        
        # System should handle offset calculation errors
        await coordinator.async_request_refresh()
        
        assert coordinator.data is not None, "Coordinator should handle offset engine errors"
        assert entity.outlier_detection_active is True, "Entity should remain active with offset engine errors"
        
        # 5. Reset offset engine
        offset_engine.calculate_offset.side_effect = None
        offset_engine.calculate_offset.return_value = OffsetResult(
            offset=1.5, clamped=False, reason="ML prediction", confidence=0.85
        )
        
        # Act & Assert - Test outlier detector internal failure scenarios
        
        # 6. Test with corrupted outlier detector state
        original_detector = coordinator._outlier_detector
        coordinator._outlier_detector = None  # Simulate detector failure
        
        # System should handle missing outlier detector
        await coordinator.async_request_refresh()
        
        assert coordinator.data is not None, "Coordinator should handle missing outlier detector"
        assert coordinator.data.outlier_statistics["enabled"] is False, "Statistics should reflect disabled state"
        
        # 7. Restore outlier detector
        coordinator._outlier_detector = original_detector
        
        # Act & Assert - Test entity attribute failure scenarios
        
        # 8. Test entity with None coordinator
        entity_with_no_coordinator = SmartClimateEntity(
            hass=system_hass,
            config={"name": "Test Smart Climate No Coordinator"},
            wrapped_entity_id="climate.test_ac_2",
            room_sensor_id="sensor.room_temp_2",
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=None,
        )
        entity_with_no_coordinator.entity_id = "climate.smart_test_no_coord"
        
        # Entity should handle None coordinator gracefully
        assert entity_with_no_coordinator.outlier_detection_active is False
        assert entity_with_no_coordinator.outlier_detected is False
        
        attributes = entity_with_no_coordinator.extra_state_attributes
        assert attributes["is_outlier"] is False
        assert attributes["outlier_statistics"] == {}
        
        # Act & Assert - Test system recovery after errors
        
        # 9. Verify system recovers after all error conditions resolved
        await coordinator.async_request_refresh()
        
        # System should be fully operational again
        assert coordinator.data is not None
        assert coordinator.outlier_detection_enabled is True
        assert coordinator.data.outlier_statistics["enabled"] is True
        assert entity.outlier_detection_active is True
        
        # Final system health check
        final_attributes = entity.extra_state_attributes
        assert "is_outlier" in final_attributes
        assert "outlier_statistics" in final_attributes
        assert final_attributes["outlier_statistics"]["enabled"] is True


# Helper functions for creating realistic test scenarios

def create_temperature_outlier_scenario():
    """Create realistic temperature outlier test data."""
    return {
        "normal_temps": [20.0, 21.0, 22.0, 23.0, 22.5, 21.5, 22.0, 23.5, 21.0, 22.5],
        "outlier_temps": [55.0, -15.0, 75.0, -25.0],  # Extreme outliers
        "edge_case_temps": [15.0, 35.0, 10.0, 40.0],  # Borderline cases
    }


def create_power_outlier_scenario():
    """Create realistic power consumption outlier test data."""
    return {
        "normal_power": [800, 900, 1000, 1100, 950, 850, 1050, 900, 950, 1000],
        "outlier_power": [5500, 8000, -100, 10000],  # Extreme outliers
        "edge_case_power": [2500, 3000, 50, 0],  # Borderline cases
    }


def verify_system_integration_health(coordinator, entity, sensors=None):
    """Verify complete system integration health."""
    # Check coordinator health
    assert coordinator.data is not None
    assert hasattr(coordinator.data, 'outliers')
    assert hasattr(coordinator.data, 'outlier_count')
    assert hasattr(coordinator.data, 'outlier_statistics')
    
    # Check entity health
    assert hasattr(entity, 'outlier_detection_active')
    assert hasattr(entity, 'outlier_detected')
    
    # Check entity attributes
    attributes = entity.extra_state_attributes
    assert "is_outlier" in attributes
    assert "outlier_statistics" in attributes
    
    # Check sensor health if provided
    if sensors:
        for sensor in sensors:
            assert sensor.available is True
            assert hasattr(sensor, 'native_value') or hasattr(sensor, 'is_on')
    
    return True