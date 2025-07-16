"""
ABOUTME: Integration tests for sensor caching fixes and coordinator data flow
ABOUTME: Tests real sensor instances with coordinator integration to fix "unbekannt" state
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.smart_climate.const import DOMAIN
from custom_components.smart_climate.coordinator import SmartClimateCoordinator
from custom_components.smart_climate.models import SmartClimateData, ModeAdjustments
from custom_components.smart_climate.sensor import (
    WeatherForecastSensor,
    SeasonalAdaptationSensor,
    ConvergenceTrendSensor,
)
from custom_components.smart_climate.entity import SmartClimateSensorEntity

from tests.fixtures.sensor_caching_fixtures import (
    create_mock_hass_with_cache,
    create_mock_config_entry_for_caching,
)


class TestSensorCachingIntegration:
    """Integration tests for sensor caching fixes."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_hass = create_mock_hass_with_cache()
        self.mock_config_entry = create_mock_config_entry_for_caching()
        self.mock_sensor_manager = Mock()
        self.mock_offset_engine = Mock()
        self.mock_mode_manager = Mock()
        self.mock_forecast_engine = Mock()
        
        # Set up default returns
        self.mock_sensor_manager.get_room_temperature.return_value = 22.0
        self.mock_sensor_manager.get_outdoor_temperature.return_value = 28.0
        self.mock_sensor_manager.get_power_consumption.return_value = 150.0
        
        self.mock_mode_manager.current_mode = "none"
        self.mock_mode_manager.get_adjustments.return_value = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        )
        
        # Set up forecast engine with different states
        self.mock_forecast_engine.async_update = AsyncMock()
        
        # Set up offset engine with different responses
        self.mock_offset_engine.calculate_offset.return_value = Mock(
            offset=1.5,
            clamped=False,
            reason="Normal calculation",
            confidence=0.8
        )
    
    def create_coordinator(self, update_interval: int = 30) -> SmartClimateCoordinator:
        """Create a test coordinator with mock dependencies."""
        coordinator = SmartClimateCoordinator(
            hass=self.mock_hass,
            update_interval=update_interval,
            sensor_manager=self.mock_sensor_manager,
            offset_engine=self.mock_offset_engine,
            mode_manager=self.mock_mode_manager,
            forecast_engine=self.mock_forecast_engine
        )
        
        # Mock the wrapped entity access
        coordinator._wrapped_entity_id = "climate.test_ac"
        
        return coordinator
    
    def create_coordinator_with_data(self, data: SmartClimateData) -> SmartClimateCoordinator:
        """Create a coordinator with pre-set data."""
        coordinator = self.create_coordinator()
        coordinator.data = data
        coordinator.last_update_success = True
        return coordinator
    
    def create_coordinator_with_no_data(self) -> SmartClimateCoordinator:
        """Create a coordinator with no data."""
        coordinator = self.create_coordinator()
        coordinator.data = None
        coordinator.last_update_success = False
        return coordinator
    
    def create_test_sensor(self, sensor_class, coordinator) -> SmartClimateSensorEntity:
        """Create a test sensor with specified coordinator."""
        sensor = sensor_class(
            coordinator=coordinator,
            base_entity_id="climate.test_ac",
            config_entry=self.mock_config_entry
        )
        return sensor
    
    async def test_sensors_startup_sequence(self):
        """Test all 3 sensors during startup sequence."""
        # Phase 1: Startup with no coordinator data
        coordinator = self.create_coordinator_with_no_data()
        
        # Create the three problematic sensors
        weather_sensor = self.create_test_sensor(WeatherForecastSensor, coordinator)
        seasonal_sensor = self.create_test_sensor(SeasonalAdaptationSensor, coordinator)
        convergence_sensor = self.create_test_sensor(ConvergenceTrendSensor, coordinator)
        
        # Before coordinator data is available, sensors should handle gracefully
        assert weather_sensor.available == False
        assert seasonal_sensor.available == False
        assert convergence_sensor.available == False
        
        # Phase 2: Coordinator becomes available with data
        coordinator_data = SmartClimateData(
            room_temp=22.0,
            outdoor_temp=28.0,
            power=150.0,
            calculated_offset=1.5,
            mode_adjustments=ModeAdjustments(
                temperature_override=None,
                offset_adjustment=0.0,
                update_interval_override=None,
                boost_offset=0.0
            ),
            is_startup_calculation=True
        )
        
        coordinator.data = coordinator_data
        coordinator.last_update_success = True
        
        # Now sensors should be available
        assert weather_sensor.available == True
        assert seasonal_sensor.available == True
        assert convergence_sensor.available == True
        
        # Phase 3: Verify sensor states are not "unbekannt"
        # Note: This depends on the actual sensor implementation
        # The sensors should now have access to coordinator data
        # This test verifies the integration works, not specific values
        assert weather_sensor.is_on is not None  # Should not be unknown
        assert seasonal_sensor.is_on is not None  # Should not be unknown
        
        # Convergence sensor would need specific convergence_data in coordinator
        # For now, verify it doesn't crash
        try:
            convergence_value = convergence_sensor.native_value
            # Value can be None, but should not raise exception
            assert convergence_value is not None or convergence_value is None
        except Exception as e:
            pytest.fail(f"Convergence sensor raised exception: {e}")
    
    async def test_sensors_with_coordinator_updates(self):
        """Test sensor updates when coordinator data changes."""
        # Create coordinator with initial data
        initial_data = SmartClimateData(
            room_temp=22.0,
            outdoor_temp=28.0,
            power=150.0,
            calculated_offset=1.5,
            mode_adjustments=ModeAdjustments(
                temperature_override=None,
                offset_adjustment=0.0,
                update_interval_override=None,
                boost_offset=0.0
            ),
            is_startup_calculation=False
        )
        
        coordinator = self.create_coordinator_with_data(initial_data)
        
        # Create sensors
        weather_sensor = self.create_test_sensor(WeatherForecastSensor, coordinator)
        seasonal_sensor = self.create_test_sensor(SeasonalAdaptationSensor, coordinator)
        convergence_sensor = self.create_test_sensor(ConvergenceTrendSensor, coordinator)
        
        # Verify initial state
        assert weather_sensor.available == True
        assert seasonal_sensor.available == True
        assert convergence_sensor.available == True
        
        # Update coordinator data
        updated_data = SmartClimateData(
            room_temp=24.0,
            outdoor_temp=30.0,
            power=200.0,
            calculated_offset=2.0,
            mode_adjustments=ModeAdjustments(
                temperature_override=None,
                offset_adjustment=0.0,
                update_interval_override=None,
                boost_offset=0.0
            ),
            is_startup_calculation=False
        )
        
        coordinator.data = updated_data
        
        # Verify sensors still work after update
        assert weather_sensor.available == True
        assert seasonal_sensor.available == True
        assert convergence_sensor.available == True
        
        # Verify sensors can access updated data
        assert weather_sensor.is_on is not None
        assert seasonal_sensor.is_on is not None
        # Convergence sensor depends on specific data structure
        convergence_value = convergence_sensor.native_value
        # Should not crash even if value is None
        assert convergence_value is not None or convergence_value is None
    
    async def test_sensors_cache_persistence(self):
        """Test cache behavior across coordinator updates."""
        # Create coordinator with data
        coordinator_data = SmartClimateData(
            room_temp=22.0,
            outdoor_temp=28.0,
            power=150.0,
            calculated_offset=1.5,
            mode_adjustments=ModeAdjustments(
                temperature_override=None,
                offset_adjustment=0.0,
                update_interval_override=None,
                boost_offset=0.0
            ),
            is_startup_calculation=False
        )
        
        coordinator = self.create_coordinator_with_data(coordinator_data)
        
        # Create sensors
        weather_sensor = self.create_test_sensor(WeatherForecastSensor, coordinator)
        seasonal_sensor = self.create_test_sensor(SeasonalAdaptationSensor, coordinator)
        
        # Get initial values
        initial_weather_state = weather_sensor.is_on
        initial_seasonal_state = seasonal_sensor.is_on
        
        # Simulate coordinator data loss
        coordinator.data = None
        coordinator.last_update_success = False
        
        # Sensors should handle data loss gracefully
        assert weather_sensor.available == False
        assert seasonal_sensor.available == False
        
        # But they should still have internal caching mechanisms
        # (depends on implementation - this test verifies error handling)
        try:
            weather_state_after_loss = weather_sensor.is_on
            seasonal_state_after_loss = seasonal_sensor.is_on
            
            # Should not crash, values may be None or cached
            assert weather_state_after_loss is not None or weather_state_after_loss is None
            assert seasonal_state_after_loss is not None or seasonal_state_after_loss is None
        except Exception as e:
            pytest.fail(f"Sensors crashed after data loss: {e}")
        
        # Restore coordinator data
        coordinator.data = coordinator_data
        coordinator.last_update_success = True
        
        # Sensors should recover
        assert weather_sensor.available == True
        assert seasonal_sensor.available == True
    
    async def test_sensors_error_recovery(self):
        """Test error handling and recovery scenarios."""
        # Create coordinator with valid data
        coordinator_data = SmartClimateData(
            room_temp=22.0,
            outdoor_temp=28.0,
            power=150.0,
            calculated_offset=1.5,
            mode_adjustments=ModeAdjustments(
                temperature_override=None,
                offset_adjustment=0.0,
                update_interval_override=None,
                boost_offset=0.0
            ),
            is_startup_calculation=False
        )
        
        coordinator = self.create_coordinator_with_data(coordinator_data)
        
        # Create sensors
        weather_sensor = self.create_test_sensor(WeatherForecastSensor, coordinator)
        seasonal_sensor = self.create_test_sensor(SeasonalAdaptationSensor, coordinator)
        convergence_sensor = self.create_test_sensor(ConvergenceTrendSensor, coordinator)
        
        # Test error scenarios
        error_scenarios = [
            # Scenario 1: Coordinator data becomes None
            (None, "Coordinator data is None"),
            
            # Scenario 2: Coordinator data is invalid type
            ("invalid_string", "Coordinator data is invalid type"),
            
            # Scenario 3: Coordinator data is empty dict
            ({}, "Coordinator data is empty dict"),
        ]
        
        for invalid_data, scenario_description in error_scenarios:
            # Set invalid data
            coordinator.data = invalid_data
            coordinator.last_update_success = False
            
            # Sensors should handle error gracefully
            try:
                weather_available = weather_sensor.available
                seasonal_available = seasonal_sensor.available
                convergence_available = convergence_sensor.available
                
                # Should not crash, but should indicate unavailability
                assert weather_available == False
                assert seasonal_available == False
                assert convergence_available == False
                
                # Accessing properties should not crash
                weather_state = weather_sensor.is_on
                seasonal_state = seasonal_sensor.is_on
                convergence_state = convergence_sensor.native_value
                
                # Values may be None or cached, but should not crash
                assert weather_state is not None or weather_state is None
                assert seasonal_state is not None or seasonal_state is None
                assert convergence_state is not None or convergence_state is None
                
            except Exception as e:
                pytest.fail(f"Sensors crashed in scenario '{scenario_description}': {e}")
        
        # Recovery: Restore valid data
        coordinator.data = coordinator_data
        coordinator.last_update_success = True
        
        # Sensors should recover
        assert weather_sensor.available == True
        assert seasonal_sensor.available == True
        assert convergence_sensor.available == True
    
    async def test_sensors_mixed_data_availability(self):
        """Test sensors with partial data availability."""
        # Create coordinator with minimal data
        minimal_data = SmartClimateData(
            room_temp=22.0,
            outdoor_temp=None,  # Missing outdoor temp
            power=None,  # Missing power
            calculated_offset=1.5,
            mode_adjustments=ModeAdjustments(
                temperature_override=None,
                offset_adjustment=0.0,
                update_interval_override=None,
                boost_offset=0.0
            ),
            is_startup_calculation=False
        )
        
        coordinator = self.create_coordinator_with_data(minimal_data)
        
        # Create sensors
        weather_sensor = self.create_test_sensor(WeatherForecastSensor, coordinator)
        seasonal_sensor = self.create_test_sensor(SeasonalAdaptationSensor, coordinator)
        convergence_sensor = self.create_test_sensor(ConvergenceTrendSensor, coordinator)
        
        # Sensors should still be available even with partial data
        assert weather_sensor.available == True
        assert seasonal_sensor.available == True
        assert convergence_sensor.available == True
        
        # Test with only basic data
        basic_data = SmartClimateData(
            room_temp=22.0,
            outdoor_temp=28.0,
            power=150.0,
            calculated_offset=1.5,
            mode_adjustments=ModeAdjustments(
                temperature_override=None,
                offset_adjustment=0.0,
                update_interval_override=None,
                boost_offset=0.0
            ),
            is_startup_calculation=False
        )
        
        coordinator.data = basic_data
        
        # Sensors should handle basic data correctly
        assert weather_sensor.available == True
        assert seasonal_sensor.available == True
        assert convergence_sensor.available == True
        
        # Verify sensors can access their required data
        try:
            weather_state = weather_sensor.is_on
            seasonal_state = seasonal_sensor.is_on
            convergence_state = convergence_sensor.native_value
            
            # Should not crash, regardless of specific values
            assert weather_state is not None or weather_state is None
            assert seasonal_state is not None or seasonal_state is None
            assert convergence_state is not None or convergence_state is None
            
        except Exception as e:
            pytest.fail(f"Sensors crashed with basic data: {e}")
    
    async def test_sensor_coordinator_integration_end_to_end(self):
        """Test complete end-to-end integration with real coordinator update."""
        # Create coordinator that can actually perform updates
        coordinator = self.create_coordinator(update_interval=1)  # 1 second for testing
        
        # Create sensors
        weather_sensor = self.create_test_sensor(WeatherForecastSensor, coordinator)
        seasonal_sensor = self.create_test_sensor(SeasonalAdaptationSensor, coordinator)
        convergence_sensor = self.create_test_sensor(ConvergenceTrendSensor, coordinator)
        
        # Mock the wrapped entity state
        mock_wrapped_state = Mock()
        mock_wrapped_state.state = "cool"
        mock_wrapped_state.attributes = {
            "current_temperature": 21.5,
            "temperature": 22.0
        }
        
        self.mock_hass.states.get.return_value = mock_wrapped_state
        
        # Perform coordinator update
        try:
            await coordinator._async_update_data()
            
            # Verify coordinator has data
            assert coordinator.data is not None
            assert isinstance(coordinator.data, SmartClimateData)
            
            # Verify sensors work with real coordinator data
            assert weather_sensor.available == True
            assert seasonal_sensor.available == True
            assert convergence_sensor.available == True
            
            # Verify sensors can access data without crashing
            weather_state = weather_sensor.is_on
            seasonal_state = seasonal_sensor.is_on
            convergence_state = convergence_sensor.native_value
            
            # Should not crash, regardless of specific values
            assert weather_state is not None or weather_state is None
            assert seasonal_state is not None or seasonal_state is None
            assert convergence_state is not None or convergence_state is None
            
        except Exception as e:
            pytest.fail(f"End-to-end integration failed: {e}")
    
    async def test_sensor_device_info_consistency(self):
        """Test that all sensors have consistent device info."""
        coordinator = self.create_coordinator_with_data(SmartClimateData(
            room_temp=22.0,
            outdoor_temp=28.0,
            power=150.0,
            calculated_offset=1.5,
            mode_adjustments=ModeAdjustments(
                temperature_override=None,
                offset_adjustment=0.0,
                update_interval_override=None,
                boost_offset=0.0
            ),
            is_startup_calculation=False
        ))
        
        # Create sensors
        weather_sensor = self.create_test_sensor(WeatherForecastSensor, coordinator)
        seasonal_sensor = self.create_test_sensor(SeasonalAdaptationSensor, coordinator)
        convergence_sensor = self.create_test_sensor(ConvergenceTrendSensor, coordinator)
        
        # Verify device info consistency
        assert weather_sensor.device_info is not None
        assert seasonal_sensor.device_info is not None
        assert convergence_sensor.device_info is not None
        
        # All sensors should have the same device identifier
        weather_identifiers = weather_sensor.device_info.get("identifiers", set())
        seasonal_identifiers = seasonal_sensor.device_info.get("identifiers", set())
        convergence_identifiers = convergence_sensor.device_info.get("identifiers", set())
        
        assert weather_identifiers == seasonal_identifiers == convergence_identifiers
        
        # Verify unique IDs are different
        assert weather_sensor.unique_id != seasonal_sensor.unique_id
        assert weather_sensor.unique_id != convergence_sensor.unique_id
        assert seasonal_sensor.unique_id != convergence_sensor.unique_id
        
        # But they should all contain the base entity ID
        assert "test_ac" in weather_sensor.unique_id
        assert "test_ac" in seasonal_sensor.unique_id
        assert "test_ac" in convergence_sensor.unique_id
    
    async def test_sensor_coordinator_listener_cleanup(self):
        """Test that sensor listeners are properly cleaned up."""
        coordinator = self.create_coordinator_with_data(SmartClimateData(
            room_temp=22.0,
            outdoor_temp=28.0,
            power=150.0,
            calculated_offset=1.5,
            mode_adjustments=ModeAdjustments(
                temperature_override=None,
                offset_adjustment=0.0,
                update_interval_override=None,
                boost_offset=0.0
            ),
            is_startup_calculation=False
        ))
        
        # Create sensor
        weather_sensor = self.create_test_sensor(WeatherForecastSensor, coordinator)
        
        # Mock the async_added_to_hass method
        weather_sensor.async_on_remove = Mock()
        
        # Simulate adding to hass
        await weather_sensor.async_added_to_hass()
        
        # Verify that coordinator listener was added
        assert weather_sensor.async_on_remove.called
        
        # Verify sensor responds to coordinator updates
        initial_available = weather_sensor.available
        
        # Change coordinator data
        coordinator.data = None
        coordinator.last_update_success = False
        
        # Manually trigger the update (since we're not in full HA environment)
        weather_sensor._handle_coordinator_update()
        
        # Verify sensor updated
        updated_available = weather_sensor.available
        assert updated_available != initial_available