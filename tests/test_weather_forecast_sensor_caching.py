"""Test WeatherForecastSensor caching and error handling.

ABOUTME: Tests for WeatherForecastSensor caching issues causing "unbekannt" state
ABOUTME: Demonstrates race conditions and type handling bugs requiring fixes
"""

import pytest
from unittest.mock import Mock, MagicMock
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN

from custom_components.smart_climate.sensor import WeatherForecastSensor
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
        "weather_entity": "weather.test_weather",
        "enable_weather_forecast": True,
    }
    return entry


@pytest.fixture
def mock_coordinator_with_data():
    """Create a mock coordinator with valid data."""
    coordinator = Mock()
    coordinator.data = {
        "calculated_offset": 2.5,
        "weather_forecast": True,
        "learning_info": {"enabled": True},
        "seasonal_data": {"enabled": True, "contribution": 25.0},
        "delay_data": {"adaptive_delay": 45.0},
    }
    return coordinator


@pytest.fixture
def mock_coordinator_none_data():
    """Create a mock coordinator with None data."""
    coordinator = Mock()
    coordinator.data = None
    return coordinator


@pytest.fixture
def mock_coordinator_missing_key():
    """Create a mock coordinator missing weather_forecast key."""
    coordinator = Mock()
    coordinator.data = {
        "calculated_offset": 2.5,
        "learning_info": {"enabled": True},
        "seasonal_data": {"enabled": True, "contribution": 25.0},
        "delay_data": {"adaptive_delay": 45.0},
        # Missing "weather_forecast" key
    }
    return coordinator


@pytest.fixture
def mock_coordinator_invalid_type():
    """Create a mock coordinator with invalid type data."""
    coordinator = Mock()
    coordinator.data = {
        "calculated_offset": 2.5,
        "weather_forecast": "true",  # String instead of boolean
        "learning_info": {"enabled": True},
        "seasonal_data": {"enabled": True, "contribution": 25.0},
        "delay_data": {"adaptive_delay": 45.0},
    }
    return coordinator


class TestWeatherForecastSensorCaching:
    """Test WeatherForecastSensor caching and error handling."""
    
    def test_weather_forecast_none_coordinator_data(self, mock_coordinator_none_data, mock_config_entry):
        """Test weather forecast sensor when coordinator.data is None.
        
        This test demonstrates the current issue where sensors show "unbekannt" 
        when coordinator.data is None during startup or data fetch failures.
        
        Expected behavior: Should return None, but currently may cause issues.
        """
        sensor = WeatherForecastSensor(
            mock_coordinator_none_data,
            "climate.test_ac",
            mock_config_entry
        )
        
        # This should return None but may cause "unbekannt" state
        # The test will initially FAIL until caching is implemented
        result = sensor.is_on
        
        # Expected: None (sensor unavailable)
        # Current: May return None or cause "unbekannt" state
        assert result is None, f"Expected None when coordinator.data is None, got {result}"
    
    def test_weather_forecast_missing_key(self, mock_coordinator_missing_key, mock_config_entry):
        """Test weather forecast sensor when weather_forecast key is missing.
        
        This test demonstrates the current issue where sensors show "unbekannt"
        when the weather_forecast key is missing from coordinator.data.
        
        Expected behavior: Should return None when key is missing.
        """
        sensor = WeatherForecastSensor(
            mock_coordinator_missing_key,
            "climate.test_ac",
            mock_config_entry
        )
        
        # This should return None but may cause "unbekannt" state
        # The test will initially FAIL until proper key handling is implemented
        result = sensor.is_on
        
        # Expected: None (key missing)
        # Current: May return None or cause "unbekannt" state
        assert result is None, f"Expected None when weather_forecast key missing, got {result}"
    
    def test_weather_forecast_invalid_type(self, mock_coordinator_invalid_type, mock_config_entry):
        """Test weather forecast sensor with invalid type data.
        
        This test demonstrates the current issue where sensors show "unbekannt"
        when weather_forecast contains string "true" instead of boolean True.
        
        Expected behavior: Should handle type coercion or return None.
        """
        sensor = WeatherForecastSensor(
            mock_coordinator_invalid_type,
            "climate.test_ac",
            mock_config_entry
        )
        
        # This should handle string "true" properly or return None
        # The test will initially FAIL until type handling is implemented
        result = sensor.is_on
        
        # Expected: True (type coercion) or None (error handling)
        # Current: May return string "true" or cause "unbekannt" state
        assert result is True or result is None, f"Expected True or None for string 'true', got {result}"
    
    def test_weather_forecast_caching_none_value(self, mock_coordinator_with_data, mock_config_entry):
        """Test weather forecast sensor caching when value becomes None.
        
        This test demonstrates the need for caching to maintain last known good value
        when coordinator.data temporarily becomes None during updates.
        
        Expected behavior: Should cache last known good value and return it when data is None.
        """
        sensor = WeatherForecastSensor(
            mock_coordinator_with_data,
            "climate.test_ac",
            mock_config_entry
        )
        
        # Initial value should be True
        initial_result = sensor.is_on
        assert initial_result is True, f"Expected True initially, got {initial_result}"
        
        # Simulate data becoming None (during update)
        mock_coordinator_with_data.data = None
        
        # Should return cached value, not None
        # The test will initially FAIL until caching is implemented
        cached_result = sensor.is_on
        
        # Expected: True (cached value)
        # Current: None (no caching)
        assert cached_result is True, f"Expected cached True when data is None, got {cached_result}"
    
    def test_weather_forecast_caching_initialization(self, mock_coordinator_none_data, mock_config_entry):
        """Test weather forecast sensor initialization race condition.
        
        This test demonstrates the startup race condition where coordinator.data
        is None during sensor initialization, causing "unbekannt" state.
        
        Expected behavior: Should handle initialization gracefully and update when data arrives.
        """
        sensor = WeatherForecastSensor(
            mock_coordinator_none_data,
            "climate.test_ac",
            mock_config_entry
        )
        
        # During initialization, data is None
        initial_result = sensor.is_on
        assert initial_result is None, f"Expected None during initialization, got {initial_result}"
        
        # Simulate data arriving after initialization
        mock_coordinator_none_data.data = {
            "weather_forecast": True,
            "calculated_offset": 2.5,
        }
        
        # Should now return the correct value
        # The test will initially FAIL until proper initialization handling is implemented
        updated_result = sensor.is_on
        
        # Expected: True (data now available)
        # Current: May still return None or cause issues
        assert updated_result is True, f"Expected True after data arrives, got {updated_result}"
    
    def test_weather_forecast_caching_persistence(self, mock_coordinator_with_data, mock_config_entry):
        """Test weather forecast sensor cache persistence across updates.
        
        This test demonstrates the need for persistent caching across multiple
        coordinator updates, especially when data temporarily becomes unavailable.
        
        Expected behavior: Should maintain cache across multiple None data states.
        """
        sensor = WeatherForecastSensor(
            mock_coordinator_with_data,
            "climate.test_ac",
            mock_config_entry
        )
        
        # Initial value should be True
        initial_result = sensor.is_on
        assert initial_result is True, f"Expected True initially, got {initial_result}"
        
        # Simulate multiple data update cycles with None data
        for cycle in range(3):
            # Data becomes None
            mock_coordinator_with_data.data = None
            
            # Should return cached value
            # The test will initially FAIL until persistent caching is implemented
            cached_result = sensor.is_on
            
            # Expected: True (persistent cache)
            # Current: None (no persistent caching)
            assert cached_result is True, f"Expected cached True in cycle {cycle}, got {cached_result}"
            
            # Data becomes available again with different value
            mock_coordinator_with_data.data = {
                "weather_forecast": False,
                "calculated_offset": 3.0,
            }
            
            # Should update to new value
            updated_result = sensor.is_on
            assert updated_result is False, f"Expected False after update in cycle {cycle}, got {updated_result}"
        
        # Final check: data becomes None again
        mock_coordinator_with_data.data = None
        
        # Should return last known good value (False)
        # The test will initially FAIL until persistent caching is implemented
        final_result = sensor.is_on
        
        # Expected: False (last known good value)
        # Current: None (no persistent caching)
        assert final_result is False, f"Expected cached False at end, got {final_result}"
    
    def test_weather_forecast_error_handling_attribute_error(self, mock_config_entry):
        """Test weather forecast sensor error handling for AttributeError.
        
        This test demonstrates proper error handling when coordinator.data.get()
        raises AttributeError, which can cause "unbekannt" state.
        
        Expected behavior: Should catch AttributeError and return None.
        """
        # Create a coordinator that raises AttributeError on data.get()
        coordinator = Mock()
        coordinator.data = Mock()
        coordinator.data.get = Mock(side_effect=AttributeError("Mock AttributeError"))
        
        sensor = WeatherForecastSensor(
            coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        # Should handle AttributeError gracefully
        # The test will initially FAIL until proper error handling is implemented
        result = sensor.is_on
        
        # Expected: None (error handled gracefully)
        # Current: May raise AttributeError or cause "unbekannt" state
        assert result is None, f"Expected None when AttributeError occurs, got {result}"
    
    def test_weather_forecast_error_handling_type_error(self, mock_config_entry):
        """Test weather forecast sensor error handling for TypeError.
        
        This test demonstrates proper error handling when coordinator.data.get()
        raises TypeError, which can cause "unbekannt" state.
        
        Expected behavior: Should catch TypeError and return None.
        """
        # Create a coordinator that raises TypeError on data.get()
        coordinator = Mock()
        coordinator.data = Mock()
        coordinator.data.get = Mock(side_effect=TypeError("Mock TypeError"))
        
        sensor = WeatherForecastSensor(
            coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        # Should handle TypeError gracefully
        # The test will initially FAIL until proper error handling is implemented
        result = sensor.is_on
        
        # Expected: None (error handled gracefully)
        # Current: May raise TypeError or cause "unbekannt" state
        assert result is None, f"Expected None when TypeError occurs, got {result}"
    
    def test_weather_forecast_sensor_attributes(self, mock_coordinator_with_data, mock_config_entry):
        """Test weather forecast sensor basic attributes are correct.
        
        This test verifies that the sensor has the correct attributes and configuration.
        """
        sensor = WeatherForecastSensor(
            mock_coordinator_with_data,
            "climate.test_ac",
            mock_config_entry
        )
        
        # Check basic attributes
        assert sensor.name == "Weather Forecast"
        assert sensor.icon == "mdi:weather-partly-cloudy"
        assert sensor.unique_id == "test_unique_id_climate_test_ac_weather_forecast"
        
        # Check that native_value is None (BinarySensorEntity requirement)
        assert sensor.native_value is None
        
        # Check device info
        assert sensor.device_info["identifiers"] == {(DOMAIN, "test_unique_id_climate_test_ac")}
        assert sensor.device_info["name"] == "Test Smart Climate (climate.test_ac)"