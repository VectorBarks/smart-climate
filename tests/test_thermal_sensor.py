"""Tests for thermal status sensor UI/UX component.

Tests the SmartClimateStatusSensor which provides human-readable status messages
and detailed JSON attributes for the thermal efficiency system.
"""

import pytest
from unittest.mock import Mock, MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorEntity

from custom_components.smart_climate.thermal_models import ThermalState
from custom_components.smart_climate.thermal_sensor import SmartClimateStatusSensor


@pytest.fixture
def mock_thermal_manager():
    """Create a mock thermal manager."""
    manager = Mock()
    manager.current_state = ThermalState.DRIFTING
    manager.get_operating_window.return_value = (22.5, 25.5)
    manager._setpoint = 24.0
    manager._model.tau_cooling = 90.0
    manager._model.tau_warming = 150.0
    manager._model.get_confidence.return_value = 0.85
    return manager


@pytest.fixture
def mock_offset_engine():
    """Create a mock offset engine."""
    engine = Mock()
    engine.is_learning_paused.return_value = False
    engine.get_effective_target.return_value = 24.0
    return engine


@pytest.fixture
def mock_cycle_monitor():
    """Create a mock cycle monitor."""
    monitor = Mock()
    monitor.get_average_cycle_duration.return_value = (480.0, 720.0)  # 8 min, 12 min
    monitor.needs_adjustment.return_value = False
    return monitor


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    return Mock()


@pytest.fixture
def thermal_sensor(mock_hass, mock_thermal_manager, mock_offset_engine, mock_cycle_monitor):
    """Create a SmartClimateStatusSensor for testing."""
    return SmartClimateStatusSensor(
        mock_hass, 
        mock_thermal_manager, 
        mock_offset_engine, 
        mock_cycle_monitor
    )


class TestSmartClimateStatusSensorStructure:
    """Test the basic structure and properties of SmartClimateStatusSensor."""
    
    def test_sensor_extends_sensor_entity(self, thermal_sensor):
        """Test that SmartClimateStatusSensor extends SensorEntity."""
        assert isinstance(thermal_sensor, SensorEntity)
    
    def test_sensor_name_property(self, thermal_sensor):
        """Test sensor name property returns correct value."""
        assert thermal_sensor.name == "Smart Climate Status"
    
    def test_sensor_initialization(self, mock_hass, mock_thermal_manager, mock_offset_engine, mock_cycle_monitor):
        """Test sensor initializes correctly with required dependencies."""
        sensor = SmartClimateStatusSensor(
            mock_hass, 
            mock_thermal_manager, 
            mock_offset_engine, 
            mock_cycle_monitor
        )
        
        assert sensor._thermal_manager is mock_thermal_manager
        assert sensor._offset_engine is mock_offset_engine
        assert sensor._cycle_monitor is mock_cycle_monitor


class TestThermalStateMessages:
    """Test state message generation for each thermal state."""
    
    def test_priming_state_message(self, thermal_sensor, mock_thermal_manager):
        """Test message for PRIMING state."""
        mock_thermal_manager.current_state = ThermalState.PRIMING
        
        state = thermal_sensor.state
        
        assert "Initializing" in state
        # Should include hours remaining - exact format tested separately
    
    def test_drifting_state_message(self, thermal_sensor, mock_thermal_manager):
        """Test message for DRIFTING state."""
        mock_thermal_manager.current_state = ThermalState.DRIFTING
        mock_thermal_manager._setpoint = 24.0
        
        state = thermal_sensor.state
        
        assert "Idle - saving energy" in state
        assert "drift to" in state.lower()
        assert "24.0°C" in state
    
    def test_correcting_state_cooling_message(self, thermal_sensor, mock_thermal_manager):
        """Test message for CORRECTING state when cooling."""
        mock_thermal_manager.current_state = ThermalState.CORRECTING
        mock_thermal_manager._last_hvac_mode = "cool"
        
        state = thermal_sensor.state
        
        assert "Active cooling" in state
        assert "comfort zone" in state
    
    def test_correcting_state_heating_message(self, thermal_sensor, mock_thermal_manager):
        """Test message for CORRECTING state when heating."""
        mock_thermal_manager.current_state = ThermalState.CORRECTING
        mock_thermal_manager._last_hvac_mode = "heat"
        
        state = thermal_sensor.state
        
        assert "Active heating" in state
        assert "comfort zone" in state
    
    def test_recovery_state_message(self, thermal_sensor, mock_thermal_manager):
        """Test message for RECOVERY state."""
        mock_thermal_manager.current_state = ThermalState.RECOVERY
        
        state = thermal_sensor.state
        
        assert "Adjusting to new settings" in state
        # Should include percentage complete - exact format tested separately
    
    def test_probing_state_message(self, thermal_sensor, mock_thermal_manager):
        """Test message for PROBING state."""
        mock_thermal_manager.current_state = ThermalState.PROBING
        
        state = thermal_sensor.state
        
        assert "Learning thermal properties" in state
        # Should include percentage complete - exact format tested separately
    
    def test_calibrating_state_message(self, thermal_sensor, mock_thermal_manager):
        """Test message for CALIBRATING state."""
        mock_thermal_manager.current_state = ThermalState.CALIBRATING
        
        state = thermal_sensor.state
        
        assert "Calibrating sensors for accuracy" in state


class TestSensorAttributes:
    """Test the extra_state_attributes property and structure."""
    
    def test_attributes_structure(self, thermal_sensor, mock_thermal_manager, mock_offset_engine):
        """Test that attributes contain all required keys."""
        mock_thermal_manager.current_state = ThermalState.DRIFTING
        mock_offset_engine.is_learning_paused.return_value = True
        
        attrs = thermal_sensor.extra_state_attributes
        
        required_keys = [
            "thermal_mode", "offset_mode", "active_component",
            "comfort_window", "effective_target", "confidence",
            "tau_cooling", "tau_warming", "cycle_health"
        ]
        
        for key in required_keys:
            assert key in attrs
    
    def test_thermal_mode_values(self, thermal_sensor, mock_thermal_manager):
        """Test thermal_mode attribute reflects current state."""
        test_cases = [
            (ThermalState.PRIMING, "priming"),
            (ThermalState.DRIFTING, "drifting"),
            (ThermalState.CORRECTING, "correcting"),
            (ThermalState.RECOVERY, "recovery"),
            (ThermalState.PROBING, "probing"),
            (ThermalState.CALIBRATING, "calibrating"),
        ]
        
        for state, expected_mode in test_cases:
            mock_thermal_manager.current_state = state
            attrs = thermal_sensor.extra_state_attributes
            assert attrs["thermal_mode"] == expected_mode
    
    def test_offset_mode_active(self, thermal_sensor, mock_offset_engine):
        """Test offset_mode shows 'active' when learning not paused."""
        mock_offset_engine.is_learning_paused.return_value = False
        
        attrs = thermal_sensor.extra_state_attributes
        
        assert attrs["offset_mode"] == "active"
    
    def test_offset_mode_paused(self, thermal_sensor, mock_offset_engine):
        """Test offset_mode shows 'paused' when learning is paused."""
        mock_offset_engine.is_learning_paused.return_value = True
        
        attrs = thermal_sensor.extra_state_attributes
        
        assert attrs["offset_mode"] == "paused"
    
    def test_active_component_thermal_manager(self, thermal_sensor, mock_thermal_manager):
        """Test active_component shows ThermalManager when in drift state."""
        mock_thermal_manager.current_state = ThermalState.DRIFTING
        
        attrs = thermal_sensor.extra_state_attributes
        
        assert attrs["active_component"] == "ThermalManager"
    
    def test_active_component_offset_engine(self, thermal_sensor, mock_thermal_manager):
        """Test active_component shows OffsetEngine when in correcting state."""
        mock_thermal_manager.current_state = ThermalState.CORRECTING
        
        attrs = thermal_sensor.extra_state_attributes
        
        assert attrs["active_component"] == "OffsetEngine"
    
    def test_comfort_window_format(self, thermal_sensor, mock_thermal_manager):
        """Test comfort_window is formatted as list of floats."""
        mock_thermal_manager.get_operating_window.return_value = (22.5, 25.5)
        
        attrs = thermal_sensor.extra_state_attributes
        
        assert attrs["comfort_window"] == [22.5, 25.5]
        assert isinstance(attrs["comfort_window"], list)
        assert all(isinstance(temp, float) for temp in attrs["comfort_window"])


class TestCycleHealthMetrics:
    """Test cycle health metrics in attributes."""
    
    def test_cycle_health_structure(self, thermal_sensor, mock_cycle_monitor):
        """Test cycle_health contains required keys."""
        attrs = thermal_sensor.extra_state_attributes
        
        cycle_health = attrs["cycle_health"]
        assert isinstance(cycle_health, dict)
        assert "avg_on_time" in cycle_health
        assert "avg_off_time" in cycle_health
        assert "needs_adjustment" in cycle_health
    
    def test_cycle_health_values(self, thermal_sensor, mock_cycle_monitor):
        """Test cycle_health values are correctly formatted."""
        mock_cycle_monitor.get_average_cycle_duration.return_value = (480.0, 720.0)
        mock_cycle_monitor.needs_adjustment.return_value = False
        
        attrs = thermal_sensor.extra_state_attributes
        cycle_health = attrs["cycle_health"]
        
        assert cycle_health["avg_on_time"] == 480.0
        assert cycle_health["avg_off_time"] == 720.0
        assert cycle_health["needs_adjustment"] is False
    
    def test_cycle_health_needs_adjustment(self, thermal_sensor, mock_cycle_monitor):
        """Test cycle_health indicates when adjustment needed."""
        mock_cycle_monitor.needs_adjustment.return_value = True
        
        attrs = thermal_sensor.extra_state_attributes
        cycle_health = attrs["cycle_health"]
        
        assert cycle_health["needs_adjustment"] is True


class TestConfidenceAndTauValues:
    """Test confidence levels and tau values in attributes."""
    
    def test_confidence_value(self, thermal_sensor, mock_thermal_manager):
        """Test confidence value from thermal model."""
        mock_thermal_manager._model.get_confidence.return_value = 0.75
        
        attrs = thermal_sensor.extra_state_attributes
        
        assert attrs["confidence"] == 0.75
    
    def test_tau_values(self, thermal_sensor, mock_thermal_manager):
        """Test tau_cooling and tau_warming values."""
        mock_thermal_manager._model.tau_cooling = 95.0
        mock_thermal_manager._model.tau_warming = 155.0
        
        attrs = thermal_sensor.extra_state_attributes
        
        assert attrs["tau_cooling"] == 95.0
        assert attrs["tau_warming"] == 155.0
    
    def test_effective_target_value(self, thermal_sensor, mock_offset_engine):
        """Test effective_target from offset engine."""
        mock_offset_engine.get_effective_target.return_value = 23.5
        
        attrs = thermal_sensor.extra_state_attributes
        
        assert attrs["effective_target"] == 23.5


class TestSensorUpdateHandling:
    """Test sensor updates from thermal manager changes."""
    
    def test_state_change_updates_message(self, thermal_sensor, mock_thermal_manager):
        """Test state message updates when thermal state changes."""
        # Initial state
        mock_thermal_manager.current_state = ThermalState.DRIFTING
        initial_state = thermal_sensor.state
        
        # Change state
        mock_thermal_manager.current_state = ThermalState.CORRECTING
        new_state = thermal_sensor.state
        
        assert initial_state != new_state
        assert "Idle - saving energy" in initial_state
        assert "Active" in new_state
    
    def test_attributes_update_with_data_changes(self, thermal_sensor, mock_thermal_manager):
        """Test attributes update when underlying data changes."""
        # Initial values
        mock_thermal_manager._model.get_confidence.return_value = 0.8
        initial_attrs = thermal_sensor.extra_state_attributes
        
        # Change values
        mock_thermal_manager._model.get_confidence.return_value = 0.9
        new_attrs = thermal_sensor.extra_state_attributes
        
        assert initial_attrs["confidence"] != new_attrs["confidence"]
        assert new_attrs["confidence"] == 0.9


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_none_values_handled_gracefully(self, thermal_sensor, mock_thermal_manager, mock_offset_engine):
        """Test handling of None values from dependencies."""
        mock_thermal_manager.get_operating_window.return_value = None
        mock_offset_engine.get_effective_target.return_value = None
        
        # Should not raise exception
        attrs = thermal_sensor.extra_state_attributes
        state = thermal_sensor.state
        
        # Should have fallback values
        assert attrs is not None
        assert state is not None
    
    def test_missing_attributes_handled(self, thermal_sensor, mock_thermal_manager):
        """Test handling when thermal model missing attributes."""
        # Remove some attributes
        del mock_thermal_manager._model.tau_cooling
        
        # Should not raise exception
        attrs = thermal_sensor.extra_state_attributes
        
        # Should provide fallback or skip missing values
        assert attrs is not None


class TestTemperatureFormatting:
    """Test temperature value formatting in messages."""
    
    def test_temperature_one_decimal_place(self, thermal_sensor, mock_thermal_manager):
        """Test temperatures formatted to 1 decimal place."""
        mock_thermal_manager.current_state = ThermalState.DRIFTING
        mock_thermal_manager._setpoint = 24.567
        
        state = thermal_sensor.state
        
        assert "24.6°C" in state  # Should round to 1 decimal
    
    def test_comfort_window_precision(self, thermal_sensor, mock_thermal_manager):
        """Test comfort window values maintain precision."""
        mock_thermal_manager.get_operating_window.return_value = (22.345, 25.678)
        
        attrs = thermal_sensor.extra_state_attributes
        
        # Should preserve precision in attributes for API consumers
        assert attrs["comfort_window"] == [22.345, 25.678]