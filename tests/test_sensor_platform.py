"""Test the Smart Climate sensor platform."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er
from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    EntityCategory,
)
from custom_components.smart_climate.const import DOMAIN


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = Mock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.unique_id = "test_unique_id"
    entry.title = "Test Smart Climate"
    entry.data = {
        "climate_entity": "climate.test_ac",
        "room_sensor": "sensor.test_room",
        "power_sensor": "sensor.test_power",
        "max_offset": 5.0,
        "enable_learning": True,
    }
    return entry


@pytest.fixture
def mock_offset_engine():
    """Create a mock offset engine with learning capabilities."""
    engine = Mock()
    engine.is_learning_enabled = True
    engine.get_learning_info = Mock(return_value={
        "enabled": True,
        "samples": 15,
        "accuracy": 0.85,
        "confidence": 0.75,
        "has_sufficient_data": True,
        "last_sample_time": "2025-07-09T12:00:00",
        "hysteresis_enabled": True,
        "hysteresis_state": "idle_stable_zone",
        "learned_start_threshold": 26.5,
        "learned_stop_threshold": 24.0,
        "temperature_window": 2.5,
        "start_samples_collected": 8,
        "stop_samples_collected": 7,
        "hysteresis_ready": True
    })
    
    # Mock coordinator data
    mock_coordinator = Mock()
    mock_coordinator.data = Mock()
    mock_coordinator.data.calculated_offset = 2.3
    engine._coordinator = mock_coordinator
    
    return engine


@pytest.fixture
def mock_hass_data(hass: HomeAssistant, mock_config_entry, mock_offset_engine):
    """Set up hass data with mocked components."""
    hass.data[DOMAIN] = {
        mock_config_entry.entry_id: {
            "offset_engines": {
                "climate.test_ac": mock_offset_engine
            }
        }
    }
    return hass


class TestSensorPlatformSetup:
    """Test sensor platform setup."""
    
    async def test_async_setup_entry_creates_sensors(self, mock_hass_data, mock_config_entry):
        """Test that sensor platform creates all expected sensors."""
        from custom_components.smart_climate.sensor import async_setup_entry
        
        async_add_entities = AsyncMock()
        
        await async_setup_entry(mock_hass_data, mock_config_entry, async_add_entities)
        
        # Should create 5 sensors per climate entity
        async_add_entities.assert_called_once()
        sensors = async_add_entities.call_args[0][0]
        assert len(sensors) == 5
        
        # Check sensor types
        sensor_types = [s._sensor_type for s in sensors]
        expected_types = [
            "offset_current",
            "learning_progress", 
            "accuracy_current",
            "calibration_status",
            "hysteresis_state"
        ]
        assert sorted(sensor_types) == sorted(expected_types)
    
    async def test_no_offset_engines_warning(self, hass: HomeAssistant, mock_config_entry, caplog):
        """Test warning when no offset engines found."""
        from custom_components.smart_climate.sensor import async_setup_entry
        
        # Set up empty data
        hass.data[DOMAIN] = {mock_config_entry.entry_id: {}}
        
        async_add_entities = AsyncMock()
        await async_setup_entry(hass, mock_config_entry, async_add_entities)
        
        async_add_entities.assert_not_called()
        assert "No offset engines found for sensor setup" in caplog.text


class TestSmartClimateDashboardSensor:
    """Test the base dashboard sensor class."""
    
    async def test_sensor_properties(self, mock_offset_engine, mock_config_entry):
        """Test basic sensor properties."""
        from custom_components.smart_climate.sensor import SmartClimateDashboardSensor
        
        sensor = SmartClimateDashboardSensor(
            mock_offset_engine,
            "climate.test_ac",
            "offset_current",
            mock_config_entry
        )
        
        assert sensor.unique_id == "test_unique_id_climate_test_ac_offset_current"
        assert sensor.device_info["identifiers"] == {(DOMAIN, "test_unique_id_climate_test_ac")}
        assert sensor.device_info["name"] == "Test Smart Climate (climate.test_ac)"
        assert sensor._attr_has_entity_name is True
    
    async def test_sensor_available_when_coordinator_has_data(self, mock_offset_engine):
        """Test sensor is available when coordinator has data."""
        from custom_components.smart_climate.sensor import SmartClimateDashboardSensor
        
        sensor = SmartClimateDashboardSensor(
            mock_offset_engine,
            "climate.test_ac",
            "offset_current",
            Mock()
        )
        
        assert sensor.available is True
    
    async def test_sensor_unavailable_when_no_coordinator_data(self, mock_offset_engine):
        """Test sensor is unavailable when coordinator has no data."""
        from custom_components.smart_climate.sensor import SmartClimateDashboardSensor
        
        mock_offset_engine._coordinator.data = None
        
        sensor = SmartClimateDashboardSensor(
            mock_offset_engine,
            "climate.test_ac",
            "offset_current",
            Mock()
        )
        
        assert sensor.available is False


class TestOffsetCurrentSensor:
    """Test the current offset sensor."""
    
    async def test_offset_sensor_attributes(self, mock_offset_engine, mock_config_entry):
        """Test offset sensor specific attributes."""
        from custom_components.smart_climate.sensor import OffsetCurrentSensor
        
        sensor = OffsetCurrentSensor(
            mock_offset_engine,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.name == "Current Offset"
        assert sensor.native_unit_of_measurement == UnitOfTemperature.CELSIUS
        assert sensor.device_class == SensorDeviceClass.TEMPERATURE
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.suggested_display_precision == 1
    
    async def test_offset_sensor_state(self, mock_offset_engine, mock_config_entry):
        """Test offset sensor returns correct state."""
        from custom_components.smart_climate.sensor import OffsetCurrentSensor
        
        sensor = OffsetCurrentSensor(
            mock_offset_engine,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.native_value == 2.3
    
    async def test_offset_sensor_state_when_unavailable(self, mock_offset_engine, mock_config_entry):
        """Test offset sensor state when coordinator data unavailable."""
        from custom_components.smart_climate.sensor import OffsetCurrentSensor
        
        mock_offset_engine._coordinator.data = None
        
        sensor = OffsetCurrentSensor(
            mock_offset_engine,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.native_value is None


class TestLearningProgressSensor:
    """Test the learning progress sensor."""
    
    async def test_progress_sensor_attributes(self, mock_offset_engine, mock_config_entry):
        """Test learning progress sensor specific attributes."""
        from custom_components.smart_climate.sensor import LearningProgressSensor
        
        sensor = LearningProgressSensor(
            mock_offset_engine,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.name == "Learning Progress"
        assert sensor.native_unit_of_measurement == PERCENTAGE
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.icon == "mdi:brain"
    
    async def test_progress_calculation(self, mock_offset_engine, mock_config_entry):
        """Test learning progress calculation."""
        from custom_components.smart_climate.sensor import LearningProgressSensor
        
        sensor = LearningProgressSensor(
            mock_offset_engine,
            "climate.test_ac",
            mock_config_entry
        )
        
        # With 15 samples and min 10 required, progress should be 100%
        assert sensor.native_value == 100
    
    async def test_progress_calculation_partial(self, mock_offset_engine, mock_config_entry):
        """Test learning progress calculation when partially complete."""
        from custom_components.smart_climate.sensor import LearningProgressSensor
        
        # Set samples to 5 (50% of 10 required)
        mock_offset_engine.get_learning_info.return_value["samples"] = 5
        
        sensor = LearningProgressSensor(
            mock_offset_engine,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.native_value == 50
    
    async def test_progress_when_learning_disabled(self, mock_offset_engine, mock_config_entry):
        """Test learning progress when learning is disabled."""
        from custom_components.smart_climate.sensor import LearningProgressSensor
        
        mock_offset_engine.get_learning_info.return_value["enabled"] = False
        
        sensor = LearningProgressSensor(
            mock_offset_engine,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.native_value == 0


class TestAccuracyCurrentSensor:
    """Test the current accuracy sensor."""
    
    async def test_accuracy_sensor_attributes(self, mock_offset_engine, mock_config_entry):
        """Test accuracy sensor specific attributes."""
        from custom_components.smart_climate.sensor import AccuracyCurrentSensor
        
        sensor = AccuracyCurrentSensor(
            mock_offset_engine,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.name == "Current Accuracy"
        assert sensor.native_unit_of_measurement == PERCENTAGE
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.icon == "mdi:target"
    
    async def test_accuracy_value(self, mock_offset_engine, mock_config_entry):
        """Test accuracy sensor returns correct value."""
        from custom_components.smart_climate.sensor import AccuracyCurrentSensor
        
        sensor = AccuracyCurrentSensor(
            mock_offset_engine,
            "climate.test_ac",
            mock_config_entry
        )
        
        # Should return 85% (0.85 * 100)
        assert sensor.native_value == 85
    
    async def test_accuracy_when_no_data(self, mock_offset_engine, mock_config_entry):
        """Test accuracy when no learning data available."""
        from custom_components.smart_climate.sensor import AccuracyCurrentSensor
        
        mock_offset_engine.get_learning_info.return_value["accuracy"] = 0.0
        
        sensor = AccuracyCurrentSensor(
            mock_offset_engine,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.native_value == 0


class TestCalibrationStatusSensor:
    """Test the calibration status sensor."""
    
    async def test_calibration_sensor_attributes(self, mock_offset_engine, mock_config_entry):
        """Test calibration status sensor specific attributes."""
        from custom_components.smart_climate.sensor import CalibrationStatusSensor
        
        sensor = CalibrationStatusSensor(
            mock_offset_engine,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.name == "Calibration Status"
        assert sensor.icon == "mdi:progress-check"
        assert sensor.device_class is None
        assert sensor.native_unit_of_measurement is None
    
    async def test_calibration_complete_status(self, mock_offset_engine, mock_config_entry):
        """Test calibration status when complete."""
        from custom_components.smart_climate.sensor import CalibrationStatusSensor
        
        sensor = CalibrationStatusSensor(
            mock_offset_engine,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.native_value == "Complete"
    
    async def test_calibration_in_progress_status(self, mock_offset_engine, mock_config_entry):
        """Test calibration status when in progress."""
        from custom_components.smart_climate.sensor import CalibrationStatusSensor
        
        # Set samples to 5 (less than 10 required)
        mock_offset_engine.get_learning_info.return_value["samples"] = 5
        
        sensor = CalibrationStatusSensor(
            mock_offset_engine,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.native_value == "In Progress (5/10 samples)"
    
    async def test_calibration_waiting_status(self, mock_offset_engine, mock_config_entry):
        """Test calibration status when learning disabled."""
        from custom_components.smart_climate.sensor import CalibrationStatusSensor
        
        mock_offset_engine.get_learning_info.return_value["enabled"] = False
        
        sensor = CalibrationStatusSensor(
            mock_offset_engine,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.native_value == "Waiting (Learning Disabled)"
    
    async def test_calibration_extra_attributes(self, mock_offset_engine, mock_config_entry):
        """Test calibration sensor extra attributes."""
        from custom_components.smart_climate.sensor import CalibrationStatusSensor
        
        sensor = CalibrationStatusSensor(
            mock_offset_engine,
            "climate.test_ac",
            mock_config_entry
        )
        
        attrs = sensor.extra_state_attributes
        assert attrs["samples_collected"] == 15
        assert attrs["minimum_required"] == 10
        assert attrs["learning_enabled"] is True
        assert attrs["last_sample"] == "2025-07-09T12:00:00"


class TestHysteresisStateSensor:
    """Test the hysteresis state sensor."""
    
    async def test_hysteresis_sensor_attributes(self, mock_offset_engine, mock_config_entry):
        """Test hysteresis state sensor specific attributes."""
        from custom_components.smart_climate.sensor import HysteresisStateSensor
        
        sensor = HysteresisStateSensor(
            mock_offset_engine,
            "climate.test_ac",
            mock_config_entry
        )
        
        assert sensor.name == "Hysteresis State"
        assert sensor.icon == "mdi:sine-wave"
    
    async def test_hysteresis_state_mapping(self, mock_offset_engine, mock_config_entry):
        """Test hysteresis state human-readable mapping."""
        from custom_components.smart_climate.sensor import HysteresisStateSensor
        
        test_cases = [
            ("learning_hysteresis", "Learning AC behavior"),
            ("active_phase", "AC actively cooling"),
            ("idle_above_start_threshold", "AC should start soon"),
            ("idle_below_stop_threshold", "AC recently stopped"),
            ("idle_stable_zone", "Temperature stable"),
            ("disabled", "No power sensor"),
            ("no_power_sensor", "No power sensor"),
            ("unknown_state", "Unknown"),
        ]
        
        for state_key, expected_text in test_cases:
            mock_offset_engine.get_learning_info.return_value["hysteresis_state"] = state_key
            
            sensor = HysteresisStateSensor(
                mock_offset_engine,
                "climate.test_ac",
                mock_config_entry
            )
            
            assert sensor.native_value == expected_text
    
    async def test_hysteresis_extra_attributes(self, mock_offset_engine, mock_config_entry):
        """Test hysteresis sensor extra attributes."""
        from custom_components.smart_climate.sensor import HysteresisStateSensor
        
        sensor = HysteresisStateSensor(
            mock_offset_engine,
            "climate.test_ac",
            mock_config_entry
        )
        
        attrs = sensor.extra_state_attributes
        assert attrs["power_sensor_configured"] is True
        assert attrs["start_threshold"] == "26.5°C"
        assert attrs["stop_threshold"] == "24.0°C"
        assert attrs["temperature_window"] == "2.5°C"
        assert attrs["start_samples"] == 8
        assert attrs["stop_samples"] == 7
        assert attrs["ready"] is True
    
    async def test_hysteresis_attributes_no_power_sensor(self, mock_offset_engine, mock_config_entry):
        """Test hysteresis attributes when no power sensor configured."""
        from custom_components.smart_climate.sensor import HysteresisStateSensor
        
        mock_offset_engine.get_learning_info.return_value.update({
            "hysteresis_enabled": False,
            "hysteresis_state": "disabled",
            "learned_start_threshold": None,
            "learned_stop_threshold": None,
            "temperature_window": None,
        })
        
        sensor = HysteresisStateSensor(
            mock_offset_engine,
            "climate.test_ac",
            mock_config_entry
        )
        
        attrs = sensor.extra_state_attributes
        assert attrs["power_sensor_configured"] is False
        assert attrs["start_threshold"] == "Not available"
        assert attrs["stop_threshold"] == "Not available"
        assert attrs["temperature_window"] == "Not available"
    
    async def test_hysteresis_attributes_learning(self, mock_offset_engine, mock_config_entry):
        """Test hysteresis attributes when still learning."""
        from custom_components.smart_climate.sensor import HysteresisStateSensor
        
        mock_offset_engine.get_learning_info.return_value.update({
            "hysteresis_state": "learning_hysteresis",
            "learned_start_threshold": None,
            "learned_stop_threshold": None,
            "temperature_window": None,
            "hysteresis_ready": False,
        })
        
        sensor = HysteresisStateSensor(
            mock_offset_engine,
            "climate.test_ac",
            mock_config_entry
        )
        
        attrs = sensor.extra_state_attributes
        assert attrs["start_threshold"] == "Learning..."
        assert attrs["stop_threshold"] == "Learning..."
        assert attrs["temperature_window"] == "Learning..."


class TestSensorCoordinatorIntegration:
    """Test sensor integration with coordinator updates."""
    
    async def test_sensor_updates_on_coordinator_refresh(self, mock_offset_engine, mock_config_entry):
        """Test that sensors update when coordinator refreshes."""
        from custom_components.smart_climate.sensor import OffsetCurrentSensor
        
        sensor = OffsetCurrentSensor(
            mock_offset_engine,
            "climate.test_ac",
            mock_config_entry
        )
        
        # Initial value
        assert sensor.native_value == 2.3
        
        # Update coordinator data
        mock_offset_engine._coordinator.data.calculated_offset = 3.5
        
        # Sensor should reflect new value
        assert sensor.native_value == 3.5
    
    async def test_multiple_sensors_share_coordinator(self, mock_offset_engine, mock_config_entry):
        """Test that multiple sensors share the same coordinator."""
        from custom_components.smart_climate.sensor import (
            OffsetCurrentSensor,
            LearningProgressSensor,
            AccuracyCurrentSensor,
        )
        
        offset_sensor = OffsetCurrentSensor(
            mock_offset_engine,
            "climate.test_ac",
            mock_config_entry
        )
        
        progress_sensor = LearningProgressSensor(
            mock_offset_engine,
            "climate.test_ac",
            mock_config_entry
        )
        
        accuracy_sensor = AccuracyCurrentSensor(
            mock_offset_engine,
            "climate.test_ac",
            mock_config_entry
        )
        
        # All should use the same coordinator
        assert offset_sensor._offset_engine._coordinator is progress_sensor._offset_engine._coordinator
        assert offset_sensor._offset_engine._coordinator is accuracy_sensor._offset_engine._coordinator