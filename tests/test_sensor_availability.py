"""Test sensor availability functionality for Smart Climate Control."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)

from custom_components.smart_climate.const import DOMAIN
from tests.fixtures.sensor_test_fixtures import (
    create_mock_offset_engine_with_coordinator,
    create_mock_offset_engine_without_coordinator,
    create_mock_offset_engine_coordinator_no_data,
    create_mock_config_entry,
    create_realistic_learning_info,
    create_sensor_test_data,
    create_exception_scenario_offset_engine,
    create_missing_coordinator_attribute_engine,
    create_sensor_availability_test_scenarios,
)


class TestSensorAvailability:
    """Test sensor availability logic."""
    
    def test_sensor_available_when_offset_engine_exists(self):
        """Test sensor is available when offset engine has coordinator with data."""
        from custom_components.smart_climate.sensor import SmartClimateDashboardSensor
        
        # Create offset engine with coordinator and data
        offset_engine = create_mock_offset_engine_with_coordinator()
        config_entry = create_mock_config_entry()
        
        sensor = SmartClimateDashboardSensor(
            offset_engine,
            "climate.test_ac",
            "offset_current",
            config_entry
        )
        
        # Should be available since coordinator has data
        assert sensor.available is True
        
        # Verify coordinator access
        assert hasattr(offset_engine, '_coordinator')
        assert offset_engine._coordinator is not None
        assert offset_engine._coordinator.data is not None
    
    def test_sensor_unavailable_when_offset_engine_none(self):
        """Test sensor is unavailable when offset engine has no coordinator."""
        from custom_components.smart_climate.sensor import SmartClimateDashboardSensor
        
        # Create offset engine without coordinator
        offset_engine = create_mock_offset_engine_without_coordinator()
        config_entry = create_mock_config_entry()
        
        sensor = SmartClimateDashboardSensor(
            offset_engine,
            "climate.test_ac",
            "offset_current",
            config_entry
        )
        
        # Should be unavailable since no coordinator
        assert sensor.available is False
    
    def test_sensor_unavailable_when_coordinator_no_data(self):
        """Test sensor is unavailable when coordinator has no data."""
        from custom_components.smart_climate.sensor import SmartClimateDashboardSensor
        
        # Create offset engine with coordinator but no data
        offset_engine = create_mock_offset_engine_coordinator_no_data()
        config_entry = create_mock_config_entry()
        
        sensor = SmartClimateDashboardSensor(
            offset_engine,
            "climate.test_ac",
            "offset_current",
            config_entry
        )
        
        # Should be unavailable since coordinator.data is None
        assert sensor.available is False
    
    def test_sensor_unavailable_missing_coordinator_attribute(self):
        """Test sensor is unavailable when _coordinator attribute missing."""
        from custom_components.smart_climate.sensor import SmartClimateDashboardSensor
        
        # Create offset engine without _coordinator attribute
        offset_engine = create_missing_coordinator_attribute_engine()
        config_entry = create_mock_config_entry()
        
        sensor = SmartClimateDashboardSensor(
            offset_engine,
            "climate.test_ac",
            "offset_current",
            config_entry
        )
        
        # Should be unavailable since hasattr returns False
        assert sensor.available is False
    
    @pytest.mark.parametrize("scenario_name", [
        "available_with_coordinator_data",
        "unavailable_no_coordinator", 
        "unavailable_coordinator_no_data",
        "unavailable_missing_coordinator_attribute",
        "exception_handling"
    ])
    def test_sensor_availability_scenarios(self, scenario_name):
        """Test all sensor availability scenarios."""
        from custom_components.smart_climate.sensor import SmartClimateDashboardSensor
        
        scenarios = create_sensor_availability_test_scenarios()
        scenario = scenarios[scenario_name]
        
        config_entry = create_mock_config_entry()
        
        sensor = SmartClimateDashboardSensor(
            scenario["offset_engine"],
            "climate.test_ac",
            "offset_current",
            config_entry
        )
        
        assert sensor.available is scenario["expected_available"], \
            f"Failed scenario: {scenario['description']}"


class TestSensorNativeValueHandling:
    """Test sensor native value handling in various availability states."""
    
    def test_sensor_native_value_returns_correct_data(self):
        """Test sensor native value returns correct data when available."""
        from custom_components.smart_climate.sensor import OffsetCurrentSensor
        
        # Create offset engine with coordinator and data
        offset_engine = create_mock_offset_engine_with_coordinator()
        config_entry = create_mock_config_entry()
        
        sensor = OffsetCurrentSensor(
            offset_engine,
            "climate.test_ac",
            config_entry
        )
        
        # Should return the coordinator data value
        assert sensor.native_value == 1.5
        assert sensor.available is True
    
    def test_sensor_native_value_handles_exceptions(self):
        """Test sensor native value handles exceptions gracefully."""
        from custom_components.smart_climate.sensor import OffsetCurrentSensor
        
        # Create offset engine with coordinator but data access throws exception
        offset_engine = create_mock_offset_engine_with_coordinator()
        # Make coordinator.data.calculated_offset access raise AttributeError
        offset_engine._coordinator.data.calculated_offset = Mock(side_effect=AttributeError("Test error"))
        config_entry = create_mock_config_entry()
        
        sensor = OffsetCurrentSensor(
            offset_engine,
            "climate.test_ac",
            config_entry
        )
        
        # Should return None when exception occurs
        assert sensor.native_value is None
        # But should still be available since coordinator and data exist
        assert sensor.available is True
    
    def test_sensor_native_value_unavailable_returns_none(self):
        """Test sensor native value returns None when unavailable."""
        from custom_components.smart_climate.sensor import OffsetCurrentSensor
        
        # Create offset engine without coordinator
        offset_engine = create_mock_offset_engine_without_coordinator()
        config_entry = create_mock_config_entry()
        
        sensor = OffsetCurrentSensor(
            offset_engine,
            "climate.test_ac",
            config_entry
        )
        
        # Should return None when not available
        assert sensor.native_value is None
        assert sensor.available is False


class TestAllSensorTypesAvailability:
    """Test availability for all 5 sensor types."""
    
    @pytest.mark.parametrize("sensor_class_name", [
        "OffsetCurrentSensor",
        "LearningProgressSensor", 
        "AccuracyCurrentSensor",
        "CalibrationStatusSensor",
        "HysteresisStateSensor"
    ])
    def test_all_sensor_types_availability_logic(self, sensor_class_name):
        """Test that all sensor types use the same availability logic."""
        from custom_components.smart_climate import sensor as sensor_module
        
        SensorClass = getattr(sensor_module, sensor_class_name)
        
        # Test with coordinator data (should be available)
        offset_engine_with_data = create_mock_offset_engine_with_coordinator()
        config_entry = create_mock_config_entry()
        
        sensor_with_data = SensorClass(
            offset_engine_with_data,
            "climate.test_ac",
            config_entry
        )
        
        assert sensor_with_data.available is True
        
        # Test without coordinator (should be unavailable)
        offset_engine_without_data = create_mock_offset_engine_without_coordinator()
        
        sensor_without_data = SensorClass(
            offset_engine_without_data,
            "climate.test_ac",
            config_entry
        )
        
        assert sensor_without_data.available is False
    
    def test_learning_progress_sensor_availability_special_case(self):
        """Test learning progress sensor availability with get_learning_info exception."""
        from custom_components.smart_climate.sensor import LearningProgressSensor
        
        # Create offset engine that raises exception in get_learning_info
        offset_engine = create_exception_scenario_offset_engine()
        config_entry = create_mock_config_entry()
        
        sensor = LearningProgressSensor(
            offset_engine,
            "climate.test_ac",
            config_entry
        )
        
        # Should be available (coordinator has data) but native_value should handle exception
        assert sensor.available is True
        assert sensor.native_value == 0  # Exception handling returns 0
    
    def test_accuracy_current_sensor_availability_special_case(self):
        """Test accuracy current sensor availability with get_learning_info exception."""
        from custom_components.smart_climate.sensor import AccuracyCurrentSensor
        
        # Create offset engine that raises exception in get_learning_info
        offset_engine = create_exception_scenario_offset_engine()
        config_entry = create_mock_config_entry()
        
        sensor = AccuracyCurrentSensor(
            offset_engine,
            "climate.test_ac",
            config_entry
        )
        
        # Should be available (coordinator has data) but native_value should handle exception
        assert sensor.available is True
        assert sensor.native_value == 0  # Exception handling returns 0
    
    def test_calibration_status_sensor_availability_special_case(self):
        """Test calibration status sensor availability with get_learning_info exception."""
        from custom_components.smart_climate.sensor import CalibrationStatusSensor
        
        # Create offset engine that raises exception in get_learning_info
        offset_engine = create_exception_scenario_offset_engine()
        config_entry = create_mock_config_entry()
        
        sensor = CalibrationStatusSensor(
            offset_engine,
            "climate.test_ac",
            config_entry
        )
        
        # Should be available (coordinator has data) but native_value should handle exception
        assert sensor.available is True
        assert sensor.native_value == "Unknown"  # Exception handling returns "Unknown"
    
    def test_hysteresis_state_sensor_availability_special_case(self):
        """Test hysteresis state sensor availability with get_learning_info exception."""
        from custom_components.smart_climate.sensor import HysteresisStateSensor
        
        # Create offset engine that raises exception in get_learning_info
        offset_engine = create_exception_scenario_offset_engine()
        config_entry = create_mock_config_entry()
        
        sensor = HysteresisStateSensor(
            offset_engine,
            "climate.test_ac",
            config_entry
        )
        
        # Should be available (coordinator has data) but native_value should handle exception
        assert sensor.available is True
        assert sensor.native_value == "Unknown"  # Exception handling returns "Unknown"


class TestSensorAvailabilityIntegration:
    """Test sensor availability in integration scenarios."""
    
    def test_sensor_availability_changes_dynamically(self):
        """Test that sensor availability changes when coordinator data changes."""
        from custom_components.smart_climate.sensor import OffsetCurrentSensor
        
        # Create offset engine with coordinator 
        offset_engine = create_mock_offset_engine_with_coordinator()
        config_entry = create_mock_config_entry()
        
        sensor = OffsetCurrentSensor(
            offset_engine,
            "climate.test_ac",
            config_entry
        )
        
        # Initially available
        assert sensor.available is True
        assert sensor.native_value == 1.5
        
        # Remove coordinator data
        offset_engine._coordinator.data = None
        
        # Should become unavailable
        assert sensor.available is False
        assert sensor.native_value is None
        
        # Restore coordinator data
        offset_engine._coordinator.data = Mock()
        offset_engine._coordinator.data.calculated_offset = 2.5
        
        # Should become available again
        assert sensor.available is True
        assert sensor.native_value == 2.5
    
    def test_multiple_sensors_same_engine_availability(self):
        """Test that multiple sensors sharing the same engine have consistent availability."""
        from custom_components.smart_climate.sensor import (
            OffsetCurrentSensor,
            LearningProgressSensor,
            AccuracyCurrentSensor,
            CalibrationStatusSensor,
            HysteresisStateSensor
        )
        
        # Create offset engine with coordinator
        offset_engine = create_mock_offset_engine_with_coordinator()
        config_entry = create_mock_config_entry()
        
        # Create all sensor types
        sensors = [
            OffsetCurrentSensor(offset_engine, "climate.test_ac", config_entry),
            LearningProgressSensor(offset_engine, "climate.test_ac", config_entry),
            AccuracyCurrentSensor(offset_engine, "climate.test_ac", config_entry),
            CalibrationStatusSensor(offset_engine, "climate.test_ac", config_entry),
            HysteresisStateSensor(offset_engine, "climate.test_ac", config_entry),
        ]
        
        # All should be available
        for sensor in sensors:
            assert sensor.available is True
        
        # Remove coordinator data
        offset_engine._coordinator.data = None
        
        # All should become unavailable
        for sensor in sensors:
            assert sensor.available is False
    
    def test_sensor_availability_after_coordinator_refresh(self):
        """Test sensor availability after coordinator refresh."""
        from custom_components.smart_climate.sensor import OffsetCurrentSensor
        
        # Create offset engine with coordinator but no data initially
        offset_engine = create_mock_offset_engine_coordinator_no_data()
        config_entry = create_mock_config_entry()
        
        sensor = OffsetCurrentSensor(
            offset_engine,
            "climate.test_ac",
            config_entry
        )
        
        # Initially unavailable
        assert sensor.available is False
        assert sensor.native_value is None
        
        # Simulate coordinator refresh with data
        offset_engine._coordinator.data = Mock()
        offset_engine._coordinator.data.calculated_offset = 3.0
        
        # Should become available
        assert sensor.available is True
        assert sensor.native_value == 3.0


class TestSensorAvailabilityEdgeCases:
    """Test edge cases for sensor availability."""
    
    def test_sensor_availability_coordinator_none(self):
        """Test sensor availability when coordinator is None."""
        from custom_components.smart_climate.sensor import SmartClimateDashboardSensor
        
        # Create offset engine with None coordinator
        offset_engine = Mock()
        offset_engine._coordinator = None
        
        config_entry = create_mock_config_entry()
        
        sensor = SmartClimateDashboardSensor(
            offset_engine,
            "climate.test_ac",
            "offset_current",
            config_entry
        )
        
        # Should be unavailable
        assert sensor.available is False
    
    def test_sensor_availability_hasattr_false(self):
        """Test sensor availability when hasattr(_coordinator) returns False."""
        from custom_components.smart_climate.sensor import SmartClimateDashboardSensor
        
        # Create offset engine without _coordinator attribute
        offset_engine = Mock()
        # Don't set _coordinator at all
        
        config_entry = create_mock_config_entry()
        
        sensor = SmartClimateDashboardSensor(
            offset_engine,
            "climate.test_ac",
            "offset_current",
            config_entry
        )
        
        # Should be unavailable
        assert sensor.available is False
    
    def test_sensor_availability_coordinator_data_empty_dict(self):
        """Test sensor availability when coordinator.data is empty dict."""
        from custom_components.smart_climate.sensor import SmartClimateDashboardSensor
        
        # Create offset engine with coordinator and empty data
        offset_engine = Mock()
        offset_engine._coordinator = Mock()
        offset_engine._coordinator.data = {}  # Empty dict, not None
        
        config_entry = create_mock_config_entry()
        
        sensor = SmartClimateDashboardSensor(
            offset_engine,
            "climate.test_ac",
            "offset_current",
            config_entry
        )
        
        # Should be available since data is not None (even if empty)
        assert sensor.available is True
    
    def test_sensor_availability_coordinator_data_false(self):
        """Test sensor availability when coordinator.data is False."""
        from custom_components.smart_climate.sensor import SmartClimateDashboardSensor
        
        # Create offset engine with coordinator and False data
        offset_engine = Mock()
        offset_engine._coordinator = Mock()
        offset_engine._coordinator.data = False  # Falsy but not None
        
        config_entry = create_mock_config_entry()
        
        sensor = SmartClimateDashboardSensor(
            offset_engine,
            "climate.test_ac",
            "offset_current",
            config_entry
        )
        
        # Should be available since data is not None (even if False)
        assert sensor.available is True