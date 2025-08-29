"""Test Quiet Mode sensors."""
import pytest
from unittest.mock import Mock

from homeassistant.components.sensor import SensorStateClass
from homeassistant.const import EntityCategory

from custom_components.smart_climate.sensor import (
    QuietModeStatusSensor,
    QuietModeSuppressionSensor,  
    CompressorStateSensor
)


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator with quiet mode test data."""
    coordinator = Mock()
    coordinator.last_update_success = True
    coordinator.data = Mock()
    
    # Quiet mode status data
    coordinator.data.quiet_mode_enabled = True
    coordinator.data.quiet_mode_status = "enabled"  # enabled/disabled/learning
    coordinator.data.quiet_mode_suppressions = 5
    coordinator.data.compressor_state = "active"  # active/idle/unknown
    
    coordinator.async_add_listener = Mock(return_value=lambda: None)
    return coordinator


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = Mock()
    entry.unique_id = "test_unique_id"
    entry.title = "Test Climate"
    return entry


class TestQuietModeStatusSensor:
    """Test QuietModeStatusSensor class."""
    
    def test_quiet_mode_status_sensor_creation(self, mock_coordinator, mock_config_entry):
        """Test sensor initializes with coordinator."""
        sensor = QuietModeStatusSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.coordinator == mock_coordinator
        assert sensor._base_entity_id == "climate.test"
        assert sensor._sensor_type == "quiet_mode_status"
        assert sensor.name == "Quiet Mode Status"
        assert sensor.icon == "mdi:volume-off"
        assert sensor._attr_unique_id == "test_unique_id_climate_test_quiet_mode_status"
    
    def test_quiet_mode_status_shows_enabled(self, mock_coordinator, mock_config_entry):
        """Test sensor shows enabled status."""
        mock_coordinator.data.quiet_mode_status = "enabled"
        sensor = QuietModeStatusSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value == "enabled"
        assert sensor.icon == "mdi:volume-off"
    
    def test_quiet_mode_status_shows_disabled(self, mock_coordinator, mock_config_entry):
        """Test sensor shows disabled status."""
        mock_coordinator.data.quiet_mode_status = "disabled"
        sensor = QuietModeStatusSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value == "disabled"
        assert sensor.icon == "mdi:volume-high"
    
    def test_quiet_mode_status_shows_learning(self, mock_coordinator, mock_config_entry):
        """Test sensor shows learning status."""
        mock_coordinator.data.quiet_mode_status = "learning"
        sensor = QuietModeStatusSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value == "learning"
        assert sensor.icon == "mdi:volume-off"
    
    def test_quiet_mode_status_no_data(self, mock_coordinator, mock_config_entry):
        """Test sensor with no data."""
        mock_coordinator.data = None
        sensor = QuietModeStatusSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value is None


class TestQuietModeSuppressionSensor:
    """Test QuietModeSuppressionSensor class."""
    
    def test_quiet_mode_suppressions_sensor(self, mock_coordinator, mock_config_entry):
        """Test suppressions sensor creation and state."""
        sensor = QuietModeSuppressionSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.coordinator == mock_coordinator
        assert sensor._base_entity_id == "climate.test"
        assert sensor._sensor_type == "quiet_mode_suppressions"
        assert sensor.name == "Quiet Mode Suppressions"
        assert sensor.icon == "mdi:counter"
        assert sensor.native_unit_of_measurement == "suppressions"
        assert sensor.state_class == SensorStateClass.TOTAL_INCREASING
        assert sensor._attr_unique_id == "test_unique_id_climate_test_quiet_mode_suppressions"
    
    def test_quiet_mode_suppressions_value(self, mock_coordinator, mock_config_entry):
        """Test suppressions sensor value."""
        mock_coordinator.data.quiet_mode_suppressions = 10
        sensor = QuietModeSuppressionSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value == 10
    
    def test_quiet_mode_suppressions_no_data(self, mock_coordinator, mock_config_entry):
        """Test suppressions sensor with no data."""
        mock_coordinator.data = None
        sensor = QuietModeSuppressionSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value is None


class TestCompressorStateSensor:
    """Test CompressorStateSensor class."""
    
    def test_compressor_state_sensor(self, mock_coordinator, mock_config_entry):
        """Test compressor state sensor creation and state."""
        sensor = CompressorStateSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.coordinator == mock_coordinator
        assert sensor._base_entity_id == "climate.test"
        assert sensor._sensor_type == "compressor_state"
        assert sensor.name == "Compressor State"
        assert sensor._attr_unique_id == "test_unique_id_climate_test_compressor_state"
    
    def test_compressor_state_active(self, mock_coordinator, mock_config_entry):
        """Test compressor state shows active."""
        mock_coordinator.data.compressor_state = "active"
        sensor = CompressorStateSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value == "active"
        assert sensor.icon == "mdi:air-conditioner"
    
    def test_compressor_state_idle(self, mock_coordinator, mock_config_entry):
        """Test compressor state shows idle."""
        mock_coordinator.data.compressor_state = "idle"
        sensor = CompressorStateSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value == "idle"
        assert sensor.icon == "mdi:pause"
    
    def test_compressor_state_unknown(self, mock_coordinator, mock_config_entry):
        """Test compressor state shows unknown."""
        mock_coordinator.data.compressor_state = "unknown"
        sensor = CompressorStateSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value == "unknown"
        assert sensor.icon == "mdi:help-circle"
    
    def test_compressor_state_no_data(self, mock_coordinator, mock_config_entry):
        """Test compressor state sensor with no data."""
        mock_coordinator.data = None
        sensor = CompressorStateSensor(mock_coordinator, "climate.test", mock_config_entry)
        
        assert sensor.native_value is None