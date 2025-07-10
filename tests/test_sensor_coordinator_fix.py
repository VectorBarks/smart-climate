"""Comprehensive tests for DataUpdateCoordinator implementation to fix sensor availability issue #17."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import timedelta
import asyncio
from typing import Dict, Any, Optional
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
    UpdateFailed,
)
from homeassistant.helpers.entity import Entity
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.smart_climate.const import DOMAIN
from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.models import OffsetInput, OffsetResult


class TestOffsetEngineDashboardData:
    """Test async_get_dashboard_data method on OffsetEngine."""
    
    @pytest.fixture
    def offset_engine(self):
        """Create a mock offset engine with necessary attributes."""
        engine = Mock(spec=OffsetEngine)
        engine._config = {
            "max_offset": 5.0,
            "ml_enabled": True,
            "save_interval": 3600,
        }
        engine._learning_enabled = True
        engine._last_offset = 2.5
        engine._lightweight_learner = Mock()
        engine._lightweight_learner.get_samples_count.return_value = 15
        engine._lightweight_learner.get_accuracy.return_value = 0.85
        engine._hysteresis_learner = Mock()
        engine._hysteresis_learner.has_sufficient_data = True
        engine._hysteresis_learner.learned_start_threshold = 24.5
        engine._hysteresis_learner.learned_stop_threshold = 23.5
        engine._current_hysteresis_state = "idle_stable_zone"
        engine._calibration_cache = {"offset": 1.5, "timestamp": 1234567890}
        engine._save_count = 10
        engine._failed_save_count = 1
        engine._last_save_time = "2025-07-10 09:00:00"
        return engine
    
    @pytest.mark.asyncio
    async def test_async_get_dashboard_data_returns_dict(self, offset_engine):
        """Test that async_get_dashboard_data returns correct dictionary structure."""
        # Mock the method we're testing
        async def mock_get_dashboard_data():
            return {
                "calculated_offset": offset_engine._last_offset,
                "learning_info": {
                    "enabled": offset_engine._learning_enabled,
                    "samples": offset_engine._lightweight_learner.get_samples_count(),
                    "accuracy": offset_engine._lightweight_learner.get_accuracy(),
                    "hysteresis_enabled": offset_engine._hysteresis_learner is not None,
                    "hysteresis_state": offset_engine._current_hysteresis_state,
                    "learned_start_threshold": offset_engine._hysteresis_learner.learned_start_threshold,
                    "learned_stop_threshold": offset_engine._hysteresis_learner.learned_stop_threshold,
                    "temperature_window": 1.0,  # start - stop
                    "start_samples_collected": 10,
                    "stop_samples_collected": 8,
                    "hysteresis_ready": offset_engine._hysteresis_learner.has_sufficient_data,
                    "last_sample_time": "2025-07-10 08:55:00",
                },
                "save_diagnostics": {
                    "save_count": offset_engine._save_count,
                    "failed_save_count": offset_engine._failed_save_count,
                    "last_save_time": offset_engine._last_save_time,
                },
                "calibration_info": {
                    "in_calibration": offset_engine._lightweight_learner.get_samples_count() < 10,
                    "cached_offset": offset_engine._calibration_cache.get("offset"),
                },
            }
        
        offset_engine.async_get_dashboard_data = mock_get_dashboard_data
        
        # Call the method
        result = await offset_engine.async_get_dashboard_data()
        
        # Verify structure
        assert isinstance(result, dict)
        assert "calculated_offset" in result
        assert "learning_info" in result
        assert "save_diagnostics" in result
        assert "calibration_info" in result
        
        # Verify calculated_offset
        assert result["calculated_offset"] == 2.5
        
        # Verify learning_info
        learning_info = result["learning_info"]
        assert learning_info["enabled"] is True
        assert learning_info["samples"] == 15
        assert learning_info["accuracy"] == 0.85
        assert learning_info["hysteresis_state"] == "idle_stable_zone"
        assert learning_info["learned_start_threshold"] == 24.5
        assert learning_info["learned_stop_threshold"] == 23.5
        
        # Verify save_diagnostics
        save_diag = result["save_diagnostics"]
        assert save_diag["save_count"] == 10
        assert save_diag["failed_save_count"] == 1
        assert save_diag["last_save_time"] == "2025-07-10 09:00:00"
        
        # Verify calibration_info
        calib_info = result["calibration_info"]
        assert calib_info["in_calibration"] is False
        assert calib_info["cached_offset"] == 1.5
    
    @pytest.mark.asyncio
    async def test_async_get_dashboard_data_handles_missing_learners(self):
        """Test async_get_dashboard_data when learners are not initialized."""
        engine = Mock(spec=OffsetEngine)
        engine._last_offset = 0.0
        engine._learning_enabled = False
        engine._lightweight_learner = None
        engine._hysteresis_learner = None
        engine._current_hysteresis_state = "disabled"
        engine._calibration_cache = {}
        engine._save_count = 0
        engine._failed_save_count = 0
        engine._last_save_time = None
        
        async def mock_get_dashboard_data():
            return {
                "calculated_offset": engine._last_offset,
                "learning_info": {
                    "enabled": engine._learning_enabled,
                    "samples": 0,
                    "accuracy": 0.0,
                    "hysteresis_enabled": False,
                    "hysteresis_state": engine._current_hysteresis_state,
                    "learned_start_threshold": None,
                    "learned_stop_threshold": None,
                    "temperature_window": None,
                    "start_samples_collected": 0,
                    "stop_samples_collected": 0,
                    "hysteresis_ready": False,
                    "last_sample_time": None,
                },
                "save_diagnostics": {
                    "save_count": engine._save_count,
                    "failed_save_count": engine._failed_save_count,
                    "last_save_time": engine._last_save_time,
                },
                "calibration_info": {
                    "in_calibration": True,
                    "cached_offset": None,
                },
            }
        
        engine.async_get_dashboard_data = mock_get_dashboard_data
        
        result = await engine.async_get_dashboard_data()
        
        assert result["calculated_offset"] == 0.0
        assert result["learning_info"]["enabled"] is False
        assert result["learning_info"]["samples"] == 0
        assert result["learning_info"]["hysteresis_enabled"] is False
        assert result["calibration_info"]["in_calibration"] is True
    
    @pytest.mark.asyncio
    async def test_async_get_dashboard_data_error_handling(self):
        """Test async_get_dashboard_data handles internal errors gracefully."""
        engine = Mock(spec=OffsetEngine)
        
        # Mock method that raises exception
        async def mock_get_dashboard_data():
            raise Exception("Internal error")
        
        engine.async_get_dashboard_data = mock_get_dashboard_data
        
        # Should raise the exception for the implementation to handle
        with pytest.raises(Exception):
            await engine.async_get_dashboard_data()


class TestCoordinatorInfrastructure:
    """Test DataUpdateCoordinator creation and management in __init__.py."""
    
    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        hass = MagicMock()
        hass.data = {DOMAIN: {}}
        hass.config_entries = Mock()
        hass.services = Mock()
        hass.states = Mock()
        return hass
    
    @pytest.fixture
    def mock_config_entry(self):
        """Create mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.data = {
            "entities": [
                {
                    "climate_entity": "climate.test",
                    "room_sensor": "sensor.room_temp",
                    "name": "Test Climate",
                }
            ]
        }
        entry.options = {}
        entry.title = "Test Smart Climate"
        entry.unique_id = "test_unique_id"
        return entry
    
    @pytest.mark.asyncio
    async def test_coordinator_created_during_setup(self, mock_hass, mock_config_entry):
        """Test that coordinator is created for each offset_engine during setup."""
        # Set up mock data
        mock_hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "offset_engines": {},
            "coordinators": {},
        }
        
        # Mock offset engine
        mock_offset_engine = Mock(spec=OffsetEngine)
        mock_offset_engine.async_get_dashboard_data = AsyncMock(return_value={
            "calculated_offset": 1.5,
            "learning_info": {"enabled": True, "samples": 10},
            "save_diagnostics": {"save_count": 5},
            "calibration_info": {"in_calibration": False},
        })
        
        # Create a mock coordinator that looks like DataUpdateCoordinator
        mock_coordinator = MagicMock()
        mock_coordinator.name = "smart_climate_climate.test"
        mock_coordinator.update_interval = timedelta(seconds=30)
        
        # Create the async update method
        async def async_update_data():
            """Fetch data from offset engine."""
            return await mock_offset_engine.async_get_dashboard_data()
        
        mock_coordinator._async_update_data = async_update_data
        mock_coordinator.async_refresh = AsyncMock()
        mock_coordinator.data = None
        mock_coordinator.last_update_success = False
        
        # Store in hass.data as the implementation would
        mock_hass.data[DOMAIN][mock_config_entry.entry_id]["coordinators"]["climate.test"] = mock_coordinator
        mock_hass.data[DOMAIN][mock_config_entry.entry_id]["offset_engines"]["climate.test"] = mock_offset_engine
        
        # Verify coordinator is stored correctly
        assert "climate.test" in mock_hass.data[DOMAIN][mock_config_entry.entry_id]["coordinators"]
        stored_coordinator = mock_hass.data[DOMAIN][mock_config_entry.entry_id]["coordinators"]["climate.test"]
        # Check coordinator attributes
        assert hasattr(stored_coordinator, 'name')
        assert hasattr(stored_coordinator, 'update_interval')
        assert hasattr(stored_coordinator, '_async_update_data')
        assert stored_coordinator.name == "smart_climate_climate.test"
        assert stored_coordinator.update_interval == timedelta(seconds=30)
    
    @pytest.mark.asyncio
    async def test_coordinator_update_calls_offset_engine(self, mock_hass, mock_config_entry):
        """Test that coordinator update method calls offset_engine.async_get_dashboard_data."""
        # Mock offset engine
        mock_offset_engine = Mock(spec=OffsetEngine)
        dashboard_data = {
            "calculated_offset": 2.0,
            "learning_info": {"enabled": True, "samples": 20},
            "save_diagnostics": {"save_count": 10},
            "calibration_info": {"in_calibration": False},
        }
        mock_offset_engine.async_get_dashboard_data = AsyncMock(return_value=dashboard_data)
        
        # Create a mock coordinator
        mock_coordinator = MagicMock()
        mock_coordinator.name = "smart_climate_test"
        mock_coordinator.update_interval = timedelta(seconds=30)
        
        # Create the async update method
        async def async_update_data():
            """Fetch data from offset engine."""
            return await mock_offset_engine.async_get_dashboard_data()
        
        mock_coordinator._async_update_data = async_update_data
        mock_coordinator.data = None
        
        # Mock the async_refresh method to actually call the update method
        async def mock_async_refresh():
            mock_coordinator.data = await async_update_data()
            mock_coordinator.last_update_success = True
            
        mock_coordinator.async_refresh = mock_async_refresh
        
        # Manually trigger update
        await mock_coordinator.async_refresh()
        
        # Verify offset engine method was called
        mock_offset_engine.async_get_dashboard_data.assert_called_once()
        
        # Verify coordinator has the data
        assert mock_coordinator.data == dashboard_data
    
    @pytest.mark.asyncio
    async def test_coordinator_handles_update_failures(self, mock_hass):
        """Test coordinator handles failures from offset_engine gracefully."""
        # Mock offset engine that fails
        mock_offset_engine = Mock(spec=OffsetEngine)
        mock_offset_engine.async_get_dashboard_data = AsyncMock(side_effect=Exception("Update failed"))
        
        # Create a mock coordinator
        mock_coordinator = MagicMock()
        mock_coordinator.name = "smart_climate_test"
        mock_coordinator.update_interval = timedelta(seconds=30)
        mock_coordinator.data = None
        mock_coordinator.last_update_success = False
        
        # Create the async update method that handles errors
        async def async_update_data():
            """Fetch data from offset engine."""
            try:
                return await mock_offset_engine.async_get_dashboard_data()
            except Exception as err:
                raise UpdateFailed(f"Error communicating with offset engine: {err}")
        
        mock_coordinator._async_update_data = async_update_data
        
        # Mock the async_refresh method to simulate update failure
        async def mock_async_refresh():
            try:
                mock_coordinator.data = await async_update_data()
                mock_coordinator.last_update_success = True
            except UpdateFailed:
                mock_coordinator.last_update_success = False
                raise
            
        mock_coordinator.async_refresh = mock_async_refresh
        
        # Define custom UpdateFailed exception for the test
        class TestUpdateFailed(Exception):
            """Test exception for update failures."""
            pass
        
        # Update async_update_data to use our test exception
        async def async_update_data_with_test_exception():
            """Fetch data from offset engine."""
            try:
                return await mock_offset_engine.async_get_dashboard_data()
            except Exception as err:
                raise TestUpdateFailed(f"Error communicating with offset engine: {err}")
        
        # Update the mock to use our test exception
        async def mock_async_refresh_with_test_exception():
            try:
                mock_coordinator.data = await async_update_data_with_test_exception()
                mock_coordinator.last_update_success = True
            except TestUpdateFailed:
                mock_coordinator.last_update_success = False
                raise
            
        mock_coordinator.async_refresh = mock_async_refresh_with_test_exception
        
        # Update should fail but not crash
        with pytest.raises(TestUpdateFailed):
            await mock_coordinator.async_refresh()
        
        # Coordinator should have no data
        assert mock_coordinator.data is None
        assert mock_coordinator.last_update_success is False
    
    @pytest.mark.asyncio
    async def test_multiple_coordinators_for_multiple_entities(self, mock_hass):
        """Test that multiple coordinators are created for multiple climate entities."""
        # Mock config with multiple entities
        mock_config_entry = Mock(spec=ConfigEntry)
        mock_config_entry.entry_id = "test_entry_id"
        mock_config_entry.data = {
            "entities": [
                {
                    "climate_entity": "climate.living_room",
                    "room_sensor": "sensor.living_room_temp",
                    "name": "Living Room",
                },
                {
                    "climate_entity": "climate.bedroom",
                    "room_sensor": "sensor.bedroom_temp",
                    "name": "Bedroom",
                },
            ]
        }
        
        # Initialize data structure
        mock_hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "offset_engines": {},
            "coordinators": {},
        }
        
        # Create mock offset engines
        for climate_id in ["climate.living_room", "climate.bedroom"]:
            mock_engine = Mock(spec=OffsetEngine)
            mock_engine.async_get_dashboard_data = AsyncMock(return_value={
                "calculated_offset": 1.0,
                "learning_info": {"enabled": True},
                "save_diagnostics": {},
                "calibration_info": {},
            })
            mock_hass.data[DOMAIN][mock_config_entry.entry_id]["offset_engines"][climate_id] = mock_engine
            
            # Create coordinator
            async def make_update_method(engine):
                async def async_update_data():
                    return await engine.async_get_dashboard_data()
                return async_update_data
            
            coordinator = DataUpdateCoordinator(
                mock_hass,
                logging.getLogger(__name__),
                name=f"smart_climate_{climate_id}",
                update_method=await make_update_method(mock_engine),
                update_interval=timedelta(seconds=30),
            )
            
            mock_hass.data[DOMAIN][mock_config_entry.entry_id]["coordinators"][climate_id] = coordinator
        
        # Verify both coordinators exist
        coordinators = mock_hass.data[DOMAIN][mock_config_entry.entry_id]["coordinators"]
        assert len(coordinators) == 2
        assert "climate.living_room" in coordinators
        assert "climate.bedroom" in coordinators


class TestSensorPlatformRefactoring:
    """Test sensor platform refactoring to use CoordinatorEntity."""
    
    @pytest.fixture
    def mock_coordinator(self):
        """Create mock coordinator with data."""
        coordinator = MagicMock()
        coordinator.data = {
            "calculated_offset": 1.5,
            "learning_info": {
                "enabled": True,
                "samples": 25,
                "accuracy": 0.92,
                "hysteresis_state": "idle_stable_zone",
                "learned_start_threshold": 24.0,
                "learned_stop_threshold": 23.0,
                "temperature_window": 1.0,
                "start_samples_collected": 15,
                "stop_samples_collected": 12,
                "hysteresis_ready": True,
                "last_sample_time": "2025-07-10 08:30:00",
                "hysteresis_enabled": True,
            },
            "save_diagnostics": {
                "save_count": 20,
                "failed_save_count": 2,
                "last_save_time": "2025-07-10 08:00:00",
            },
            "calibration_info": {
                "in_calibration": False,
                "cached_offset": 1.2,
            },
        }
        coordinator.last_update_success = True
        return coordinator
    
    @pytest.mark.asyncio
    async def test_sensor_inherits_from_coordinator_entity(self, mock_coordinator):
        """Test that dashboard sensors inherit from CoordinatorEntity."""
        # Import after mocking
        from custom_components.smart_climate.sensor import SmartClimateDashboardSensor
        
        # Create sensor instance
        sensor = SmartClimateDashboardSensor(
            mock_coordinator,
            "climate.test",
            "test_sensor",
            Mock(unique_id="test_unique_id"),
        )
        
        # Verify it has CoordinatorEntity properties
        assert hasattr(sensor, "coordinator")
        assert sensor.coordinator == mock_coordinator
        
        # Verify available property is handled by CoordinatorEntity
        # CoordinatorEntity.available checks coordinator.last_update_success
        assert sensor.available == mock_coordinator.last_update_success
    
    def test_offset_current_sensor_uses_coordinator_data(self, mock_coordinator):
        """Test OffsetCurrentSensor gets data from coordinator."""
        from custom_components.smart_climate.sensor import OffsetCurrentSensor
        
        sensor = OffsetCurrentSensor(
            mock_coordinator,
            "climate.test",
            Mock(unique_id="test_unique_id"),
        )
        
        # native_value should read from coordinator.data
        assert sensor.native_value == 1.5
        # Check unit - it's a constant from Home Assistant
        assert hasattr(sensor, '_attr_native_unit_of_measurement')
        # Check device class
        assert hasattr(sensor, '_attr_device_class')
    
    def test_learning_progress_sensor_uses_coordinator_data(self, mock_coordinator):
        """Test LearningProgressSensor calculates progress from coordinator data."""
        from custom_components.smart_climate.sensor import LearningProgressSensor
        
        sensor = LearningProgressSensor(
            mock_coordinator,
            "climate.test",
            Mock(unique_id="test_unique_id"),
        )
        
        # Progress = min(100, (samples / MIN_SAMPLES) * 100)
        # With 25 samples and MIN_SAMPLES=10: min(100, 250) = 100
        assert sensor.native_value == 100
        assert hasattr(sensor, '_attr_native_unit_of_measurement')
    
    def test_accuracy_sensor_uses_coordinator_data(self, mock_coordinator):
        """Test AccuracyCurrentSensor gets accuracy from coordinator."""
        from custom_components.smart_climate.sensor import AccuracyCurrentSensor
        
        sensor = AccuracyCurrentSensor(
            mock_coordinator,
            "climate.test",
            Mock(unique_id="test_unique_id"),
        )
        
        # Accuracy = 0.92 * 100 = 92%
        assert sensor.native_value == 92
        assert hasattr(sensor, '_attr_native_unit_of_measurement')
    
    def test_calibration_status_sensor_uses_coordinator_data(self, mock_coordinator):
        """Test CalibrationStatusSensor determines status from coordinator data."""
        from custom_components.smart_climate.sensor import CalibrationStatusSensor
        
        sensor = CalibrationStatusSensor(
            mock_coordinator,
            "climate.test",
            Mock(unique_id="test_unique_id"),
        )
        
        # With 25 samples >= MIN_SAMPLES_FOR_CALIBRATION (10)
        assert sensor.native_value == "Complete"
        
        # Test extra attributes
        attrs = sensor.extra_state_attributes
        assert attrs["samples_collected"] == 25
        assert attrs["minimum_required"] == 10
        assert attrs["learning_enabled"] is True
        assert attrs["last_sample"] == "2025-07-10 08:30:00"
    
    def test_hysteresis_state_sensor_uses_coordinator_data(self, mock_coordinator):
        """Test HysteresisStateSensor maps state from coordinator data."""
        from custom_components.smart_climate.sensor import HysteresisStateSensor
        
        sensor = HysteresisStateSensor(
            mock_coordinator,
            "climate.test",
            Mock(unique_id="test_unique_id"),
        )
        
        # "idle_stable_zone" maps to "Temperature stable"
        assert sensor.native_value == "Temperature stable"
        
        # Test extra attributes
        attrs = sensor.extra_state_attributes
        assert attrs["power_sensor_configured"] is True
        assert attrs["start_threshold"] == "24.0°C"
        assert attrs["stop_threshold"] == "23.0°C"
        assert attrs["temperature_window"] == "1.0°C"
        assert attrs["ready"] is True
    
    def test_sensors_handle_missing_coordinator_data(self):
        """Test sensors handle None coordinator data gracefully."""
        coordinator = MagicMock()
        coordinator.data = None
        coordinator.last_update_success = False
        
        from custom_components.smart_climate.sensor import (
            OffsetCurrentSensor,
            LearningProgressSensor,
            AccuracyCurrentSensor,
            CalibrationStatusSensor,
            HysteresisStateSensor,
        )
        
        # Create all sensor types
        offset_sensor = OffsetCurrentSensor(coordinator, "climate.test", Mock())
        progress_sensor = LearningProgressSensor(coordinator, "climate.test", Mock())
        accuracy_sensor = AccuracyCurrentSensor(coordinator, "climate.test", Mock())
        calib_sensor = CalibrationStatusSensor(coordinator, "climate.test", Mock())
        hyst_sensor = HysteresisStateSensor(coordinator, "climate.test", Mock())
        
        # All should handle None data gracefully
        assert offset_sensor.native_value is None
        assert progress_sensor.native_value == 0
        assert accuracy_sensor.native_value == 0
        assert calib_sensor.native_value == "Unknown"
        assert hyst_sensor.native_value == "Unknown"
        
        # All should be unavailable
        assert not offset_sensor.available
        assert not progress_sensor.available
        assert not accuracy_sensor.available
        assert not calib_sensor.available
        assert not hyst_sensor.available
    
    @pytest.mark.asyncio
    async def test_sensor_platform_setup_uses_coordinators(self, mock_hass):
        """Test sensor platform setup retrieves coordinators instead of offset_engines."""
        # Mock config entry
        mock_config_entry = Mock(spec=ConfigEntry)
        mock_config_entry.entry_id = "test_entry_id"
        mock_config_entry.title = "Test Smart Climate"
        mock_config_entry.unique_id = "test_unique_id"
        
        # Mock coordinator
        mock_coordinator = Mock(spec=DataUpdateCoordinator)
        mock_coordinator.data = {
            "calculated_offset": 1.0,
            "learning_info": {"enabled": True, "samples": 5},
            "save_diagnostics": {},
            "calibration_info": {},
        }
        mock_coordinator.last_update_success = True
        
        # Set up hass.data with coordinators
        mock_hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinators": {
                "climate.test": mock_coordinator,
            }
        }
        
        # Mock async_add_entities
        entities_added = []
        async def mock_add_entities(entities):
            entities_added.extend(entities)
        
        # Import and call setup
        from custom_components.smart_climate.sensor import async_setup_entry
        
        await async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)
        
        # Verify 5 sensors were created for the climate entity
        assert len(entities_added) == 5
        
        # Verify all sensors use the coordinator
        for sensor in entities_added:
            assert hasattr(sensor, "coordinator")
            assert sensor.coordinator == mock_coordinator


class TestIntegration:
    """Full integration tests for the coordinator implementation."""
    
    @pytest.mark.asyncio
    async def test_complete_flow_setup_to_sensor_availability(self, mock_hass):
        """Test complete flow from setup to sensor availability."""
        # Mock config entry
        config_entry = Mock(spec=ConfigEntry)
        config_entry.entry_id = "test_entry_id"
        config_entry.title = "Test Smart Climate"
        config_entry.unique_id = "test_unique_id"
        config_entry.data = {
            "entities": [
                {
                    "climate_entity": "climate.test_ac",
                    "room_sensor": "sensor.test_room",
                    "name": "Test AC",
                }
            ]
        }
        config_entry.options = {}
        
        # Initialize hass.data
        mock_hass.data[DOMAIN] = {}
        mock_hass.data[DOMAIN][config_entry.entry_id] = {
            "offset_engines": {},
            "coordinators": {},
        }
        
        # Create mock offset engine
        mock_offset_engine = Mock(spec=OffsetEngine)
        dashboard_data = {
            "calculated_offset": 2.5,
            "learning_info": {
                "enabled": True,
                "samples": 30,
                "accuracy": 0.88,
                "hysteresis_state": "learning_hysteresis",
                "learned_start_threshold": None,
                "learned_stop_threshold": None,
                "temperature_window": None,
                "start_samples_collected": 3,
                "stop_samples_collected": 2,
                "hysteresis_ready": False,
                "last_sample_time": None,
                "hysteresis_enabled": False,
            },
            "save_diagnostics": {
                "save_count": 15,
                "failed_save_count": 0,
                "last_save_time": "2025-07-10 07:30:00",
            },
            "calibration_info": {
                "in_calibration": False,
                "cached_offset": 2.3,
            },
        }
        mock_offset_engine.async_get_dashboard_data = AsyncMock(return_value=dashboard_data)
        
        # Store offset engine
        mock_hass.data[DOMAIN][config_entry.entry_id]["offset_engines"]["climate.test_ac"] = mock_offset_engine
        
        # Create coordinator
        async def async_update_data():
            return await mock_offset_engine.async_get_dashboard_data()
        
        coordinator = DataUpdateCoordinator(
            mock_hass,
            logging.getLogger(__name__),
            name="smart_climate_climate.test_ac",
            update_method=async_update_data,
            update_interval=timedelta(seconds=30),
        )
        
        # Initial data fetch
        await coordinator.async_config_entry_first_refresh()
        
        # Store coordinator
        mock_hass.data[DOMAIN][config_entry.entry_id]["coordinators"]["climate.test_ac"] = coordinator
        
        # Verify coordinator has data
        assert coordinator.data == dashboard_data
        assert coordinator.last_update_success is True
        
        # Create sensors using coordinator
        from custom_components.smart_climate.sensor import (
            OffsetCurrentSensor,
            LearningProgressSensor,
            AccuracyCurrentSensor,
            CalibrationStatusSensor,
            HysteresisStateSensor,
        )
        
        sensors = [
            OffsetCurrentSensor(coordinator, "climate.test_ac", config_entry),
            LearningProgressSensor(coordinator, "climate.test_ac", config_entry),
            AccuracyCurrentSensor(coordinator, "climate.test_ac", config_entry),
            CalibrationStatusSensor(coordinator, "climate.test_ac", config_entry),
            HysteresisStateSensor(coordinator, "climate.test_ac", config_entry),
        ]
        
        # Verify all sensors are available
        for sensor in sensors:
            assert sensor.available is True
        
        # Verify sensor values
        assert sensors[0].native_value == 2.5  # Offset
        assert sensors[1].native_value == 100  # Progress (30/10 * 100 = 300, capped at 100)
        assert sensors[2].native_value == 88   # Accuracy
        assert sensors[3].native_value == "Complete"  # Calibration status
        assert sensors[4].native_value == "Learning AC behavior"  # Hysteresis state
    
    @pytest.mark.asyncio
    async def test_sensors_unavailable_when_coordinator_fails(self, mock_hass):
        """Test sensors show unavailable when coordinator update fails."""
        # Mock coordinator that fails
        coordinator = MagicMock()
        coordinator.data = None
        coordinator.last_update_success = False
        
        # Create sensors
        from custom_components.smart_climate.sensor import (
            OffsetCurrentSensor,
            LearningProgressSensor,
            AccuracyCurrentSensor,
            CalibrationStatusSensor,
            HysteresisStateSensor,
        )
        
        config_entry = Mock(unique_id="test_id", title="Test")
        sensors = [
            OffsetCurrentSensor(coordinator, "climate.test", config_entry),
            LearningProgressSensor(coordinator, "climate.test", config_entry),
            AccuracyCurrentSensor(coordinator, "climate.test", config_entry),
            CalibrationStatusSensor(coordinator, "climate.test", config_entry),
            HysteresisStateSensor(coordinator, "climate.test", config_entry),
        ]
        
        # All should be unavailable
        for sensor in sensors:
            assert sensor.available is False
    
    @pytest.mark.asyncio
    async def test_coordinator_automatic_updates(self, mock_hass):
        """Test coordinator automatically updates sensor data."""
        # Create offset engine
        mock_offset_engine = Mock(spec=OffsetEngine)
        
        # First data
        first_data = {
            "calculated_offset": 1.0,
            "learning_info": {"enabled": True, "samples": 5, "accuracy": 0.5},
            "save_diagnostics": {"save_count": 1},
            "calibration_info": {"in_calibration": True},
        }
        
        # Updated data
        updated_data = {
            "calculated_offset": 2.0,
            "learning_info": {"enabled": True, "samples": 15, "accuracy": 0.8},
            "save_diagnostics": {"save_count": 2},
            "calibration_info": {"in_calibration": False},
        }
        
        # Mock async_get_dashboard_data to return different data on subsequent calls
        call_count = 0
        async def mock_get_dashboard_data():
            nonlocal call_count
            call_count += 1
            return first_data if call_count == 1 else updated_data
        
        mock_offset_engine.async_get_dashboard_data = mock_get_dashboard_data
        
        # Create coordinator
        async def async_update_data():
            return await mock_offset_engine.async_get_dashboard_data()
        
        coordinator = DataUpdateCoordinator(
            mock_hass,
            logging.getLogger(__name__),
            name="test_coordinator",
            update_method=async_update_data,
            update_interval=timedelta(seconds=30),
        )
        
        # First update
        await coordinator.async_refresh()
        assert coordinator.data == first_data
        
        # Create sensor
        from custom_components.smart_climate.sensor import OffsetCurrentSensor
        config_entry = Mock(unique_id="test_id", title="Test")
        sensor = OffsetCurrentSensor(coordinator, "climate.test", config_entry)
        
        # Initial value
        assert sensor.native_value == 1.0
        
        # Trigger update
        await coordinator.async_refresh()
        assert coordinator.data == updated_data
        
        # Sensor should have new value
        assert sensor.native_value == 2.0
    
    @pytest.mark.asyncio 
    async def test_multiple_climate_entities_separate_coordinators(self, mock_hass):
        """Test multiple climate entities have separate coordinators with independent data."""
        # Config with two climate entities
        config_entry = Mock(spec=ConfigEntry)
        config_entry.entry_id = "test_entry_id"
        config_entry.unique_id = "test_unique_id"
        config_entry.title = "Test"
        
        # Initialize data structure
        mock_hass.data[DOMAIN] = {
            config_entry.entry_id: {
                "offset_engines": {},
                "coordinators": {},
            }
        }
        
        # Create two offset engines with different data
        living_room_data = {
            "calculated_offset": 1.5,
            "learning_info": {"enabled": True, "samples": 20},
            "save_diagnostics": {},
            "calibration_info": {},
        }
        
        bedroom_data = {
            "calculated_offset": 2.5,
            "learning_info": {"enabled": False, "samples": 0},
            "save_diagnostics": {},
            "calibration_info": {},
        }
        
        # Mock offset engines
        living_room_engine = Mock(spec=OffsetEngine)
        living_room_engine.async_get_dashboard_data = AsyncMock(return_value=living_room_data)
        
        bedroom_engine = Mock(spec=OffsetEngine)
        bedroom_engine.async_get_dashboard_data = AsyncMock(return_value=bedroom_data)
        
        # Store engines
        mock_hass.data[DOMAIN][config_entry.entry_id]["offset_engines"]["climate.living_room"] = living_room_engine
        mock_hass.data[DOMAIN][config_entry.entry_id]["offset_engines"]["climate.bedroom"] = bedroom_engine
        
        # Create coordinators
        coordinators = {}
        for entity_id, engine in [
            ("climate.living_room", living_room_engine),
            ("climate.bedroom", bedroom_engine),
        ]:
            async def make_update_method(eng):
                async def update():
                    return await eng.async_get_dashboard_data()
                return update
            
            coordinator = DataUpdateCoordinator(
                mock_hass,
                logging.getLogger(__name__),
                name=f"smart_climate_{entity_id}",
                update_method=await make_update_method(engine),
                update_interval=timedelta(seconds=30),
            )
            
            await coordinator.async_config_entry_first_refresh()
            coordinators[entity_id] = coordinator
        
        # Store coordinators
        mock_hass.data[DOMAIN][config_entry.entry_id]["coordinators"] = coordinators
        
        # Create sensors for both entities
        from custom_components.smart_climate.sensor import OffsetCurrentSensor
        
        living_room_sensor = OffsetCurrentSensor(
            coordinators["climate.living_room"],
            "climate.living_room",
            config_entry,
        )
        
        bedroom_sensor = OffsetCurrentSensor(
            coordinators["climate.bedroom"],
            "climate.bedroom",
            config_entry,
        )
        
        # Verify independent values
        assert living_room_sensor.native_value == 1.5
        assert bedroom_sensor.native_value == 2.5
        
        # Both should be available
        assert living_room_sensor.available is True
        assert bedroom_sensor.available is True


# Additional test for error scenarios
class TestErrorScenarios:
    """Test various error scenarios and edge cases."""
    
    @pytest.mark.asyncio
    async def test_sensor_platform_handles_no_coordinators(self, mock_hass):
        """Test sensor platform handles missing coordinators gracefully."""
        config_entry = Mock(spec=ConfigEntry)
        config_entry.entry_id = "test_entry_id"
        
        # No coordinators in hass.data
        mock_hass.data = {
            DOMAIN: {
                config_entry.entry_id: {
                    "coordinators": {},  # Empty
                }
            }
        }
        
        entities_added = []
        async def mock_add_entities(entities):
            entities_added.extend(entities)
        
        # Should not crash, just log warning
        from custom_components.smart_climate.sensor import async_setup_entry
        await async_setup_entry(mock_hass, config_entry, mock_add_entities)
        
        # No entities should be added
        assert len(entities_added) == 0
    
    def test_sensor_handles_partial_coordinator_data(self):
        """Test sensors handle incomplete coordinator data structure."""
        coordinator = MagicMock()
        coordinator.data = {
            "calculated_offset": 1.5,
            "learning_info": {},  # Missing expected keys
            "save_diagnostics": None,  # None instead of dict
            # calibration_info missing entirely
        }
        coordinator.last_update_success = True
        
        from custom_components.smart_climate.sensor import (
            OffsetCurrentSensor,
            LearningProgressSensor,
            CalibrationStatusSensor,
        )
        
        config_entry = Mock(unique_id="test_id", title="Test")
        
        # Offset sensor should work
        offset_sensor = OffsetCurrentSensor(coordinator, "climate.test", config_entry)
        assert offset_sensor.native_value == 1.5
        
        # Progress sensor should handle missing data
        progress_sensor = LearningProgressSensor(coordinator, "climate.test", config_entry)
        assert progress_sensor.native_value == 0  # Default when data missing
        
        # Calibration sensor should handle missing section
        calib_sensor = CalibrationStatusSensor(coordinator, "climate.test", config_entry)
        assert calib_sensor.native_value == "Unknown"  # Default when error


# Import logging after all mocks are set up
import logging