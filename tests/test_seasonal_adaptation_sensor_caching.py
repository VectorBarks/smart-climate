"""Test SeasonalAdaptationSensor caching and error handling behavior.

ABOUTME: Tests for seasonal adaptation sensor caching implementation and error handling.
This test suite addresses the "unbekannt" state issue in Home Assistant sensors.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory

from custom_components.smart_climate.sensor import SeasonalAdaptationSensor
from custom_components.smart_climate.const import DOMAIN


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    hass = Mock(spec=HomeAssistant)
    return hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    config_entry = Mock(spec=ConfigEntry)
    config_entry.entry_id = "test_entry"
    config_entry.title = "Test Climate"
    return config_entry


@pytest.fixture
def mock_coordinator_none_data():
    """Create a mock coordinator with None data."""
    coordinator = Mock(spec=DataUpdateCoordinator)
    coordinator.data = None
    coordinator.last_update_success = False
    coordinator.async_add_listener = Mock()
    return coordinator


@pytest.fixture
def mock_coordinator_missing_seasonal_data():
    """Create a mock coordinator with missing seasonal_data key."""
    coordinator = Mock(spec=DataUpdateCoordinator)
    coordinator.data = {
        "calculated_offset": 2.0,
        "learning_info": {"enabled": True},
        # Missing seasonal_data key
    }
    coordinator.last_update_success = True
    coordinator.async_add_listener = Mock()
    return coordinator


@pytest.fixture
def mock_coordinator_none_seasonal_data():
    """Create a mock coordinator with None seasonal_data."""
    coordinator = Mock(spec=DataUpdateCoordinator)
    coordinator.data = {
        "calculated_offset": 2.0,
        "learning_info": {"enabled": True},
        "seasonal_data": None,
    }
    coordinator.last_update_success = True
    coordinator.async_add_listener = Mock()
    return coordinator


@pytest.fixture
def mock_coordinator_missing_enabled_key():
    """Create a mock coordinator with seasonal_data but missing enabled key."""
    coordinator = Mock(spec=DataUpdateCoordinator)
    coordinator.data = {
        "calculated_offset": 2.0,
        "learning_info": {"enabled": True},
        "seasonal_data": {
            "contribution": 0.15,
            "outdoor_temp": 22.5,
            # Missing enabled key
        }
    }
    coordinator.last_update_success = True
    coordinator.async_add_listener = Mock()
    return coordinator


@pytest.fixture
def mock_coordinator_invalid_seasonal_data():
    """Create a mock coordinator with invalid seasonal_data type."""
    coordinator = Mock(spec=DataUpdateCoordinator)
    coordinator.data = {
        "calculated_offset": 2.0,
        "learning_info": {"enabled": True},
        "seasonal_data": "not_a_dict",  # Invalid type
    }
    coordinator.last_update_success = True
    coordinator.async_add_listener = Mock()
    return coordinator


@pytest.fixture
def mock_coordinator_valid_seasonal_data():
    """Create a mock coordinator with valid seasonal_data."""
    coordinator = Mock(spec=DataUpdateCoordinator)
    coordinator.data = {
        "calculated_offset": 2.0,
        "learning_info": {"enabled": True},
        "seasonal_data": {
            "enabled": True,
            "contribution": 0.25,
            "outdoor_temp": 18.0,
            "patterns_learned": 15,
        }
    }
    coordinator.last_update_success = True
    coordinator.async_add_listener = Mock()
    return coordinator


class TestSeasonalAdaptationSensorCaching:
    """Test suite for SeasonalAdaptationSensor caching and error handling."""

    def test_seasonal_adaptation_none_coordinator_data(self, mock_hass, mock_config_entry, mock_coordinator_none_data):
        """Test SeasonalAdaptationSensor returns None when coordinator.data is None.
        
        This test should FAIL initially, demonstrating the current issue where
        sensors show "unbekannt" instead of properly handling None data.
        """
        sensor = SeasonalAdaptationSensor(
            coordinator=mock_coordinator_none_data,
            base_entity_id="climate.test",
            config_entry=mock_config_entry,
        )
        
        # This should return None for proper error handling
        result = sensor.is_on
        
        # Currently FAILS - sensor doesn't handle None coordinator data properly
        assert result is None, "Expected None when coordinator.data is None, but got different value"
    
    def test_seasonal_adaptation_missing_seasonal_data(self, mock_hass, mock_config_entry, mock_coordinator_missing_seasonal_data):
        """Test SeasonalAdaptationSensor returns None when seasonal_data key is missing.
        
        This test should FAIL initially, demonstrating the current issue where
        sensors don't gracefully handle missing nested data keys.
        """
        sensor = SeasonalAdaptationSensor(
            coordinator=mock_coordinator_missing_seasonal_data,
            base_entity_id="climate.test",
            config_entry=mock_config_entry,
        )
        
        # This should return None when seasonal_data key is missing
        result = sensor.is_on
        
        # Currently FAILS - sensor doesn't handle missing seasonal_data key properly
        assert result is None, "Expected None when seasonal_data key is missing, but got different value"
    
    def test_seasonal_adaptation_none_seasonal_data(self, mock_hass, mock_config_entry, mock_coordinator_none_seasonal_data):
        """Test SeasonalAdaptationSensor handles when seasonal_data is None.
        
        This test should FAIL initially, demonstrating the current issue where
        sensors don't handle None values in nested data structures.
        """
        sensor = SeasonalAdaptationSensor(
            coordinator=mock_coordinator_none_seasonal_data,
            base_entity_id="climate.test",
            config_entry=mock_config_entry,
        )
        
        # This should return None when seasonal_data is None
        result = sensor.is_on
        
        # Currently FAILS - sensor doesn't handle None seasonal_data properly
        assert result is None, "Expected None when seasonal_data is None, but got different value"
    
    def test_seasonal_adaptation_missing_enabled_key(self, mock_hass, mock_config_entry, mock_coordinator_missing_enabled_key):
        """Test SeasonalAdaptationSensor returns None when enabled key is missing.
        
        This test should FAIL initially, demonstrating the current issue where
        sensors don't gracefully handle missing keys in nested structures.
        """
        sensor = SeasonalAdaptationSensor(
            coordinator=mock_coordinator_missing_enabled_key,
            base_entity_id="climate.test",
            config_entry=mock_config_entry,
        )
        
        # This should return None when enabled key is missing
        result = sensor.is_on
        
        # Currently FAILS - sensor doesn't handle missing enabled key properly
        assert result is None, "Expected None when enabled key is missing, but got different value"
    
    def test_seasonal_adaptation_invalid_data_type(self, mock_hass, mock_config_entry, mock_coordinator_invalid_seasonal_data):
        """Test SeasonalAdaptationSensor handles non-dict seasonal_data.
        
        This test should FAIL initially, demonstrating the current issue where
        sensors don't handle type errors in nested data access.
        """
        sensor = SeasonalAdaptationSensor(
            coordinator=mock_coordinator_invalid_seasonal_data,
            base_entity_id="climate.test",
            config_entry=mock_config_entry,
        )
        
        # This should return None when seasonal_data is not a dict
        result = sensor.is_on
        
        # Currently FAILS - sensor doesn't handle invalid data types properly
        assert result is None, "Expected None when seasonal_data is not a dict, but got different value"
    
    def test_seasonal_adaptation_caching_behavior(self, mock_hass, mock_config_entry, mock_coordinator_valid_seasonal_data):
        """Test SeasonalAdaptationSensor caching behavior with valid data.
        
        This test should FAIL initially, demonstrating the current lack of
        proper caching mechanism for last known good values.
        """
        sensor = SeasonalAdaptationSensor(
            coordinator=mock_coordinator_valid_seasonal_data,
            base_entity_id="climate.test",
            config_entry=mock_config_entry,
        )
        
        # First call should return True from valid data
        first_result = sensor.is_on
        assert first_result is True, "Expected True from valid seasonal data"
        
        # Now simulate coordinator data becoming None (startup race condition)
        mock_coordinator_valid_seasonal_data.data = None
        
        # Second call should return cached value, not None
        second_result = sensor.is_on
        
        # Currently FAILS - sensor doesn't cache last known good value
        assert second_result is True, "Expected cached value True, but got None (no caching implemented)"
    
    def test_seasonal_adaptation_startup_race_condition(self, mock_hass, mock_config_entry):
        """Test SeasonalAdaptationSensor handles initialization gracefully.
        
        This test should FAIL initially, demonstrating the current issue where
        sensors don't handle startup race conditions properly.
        """
        # Create coordinator that starts with None data (startup condition)
        coordinator = Mock(spec=DataUpdateCoordinator)
        coordinator.data = None
        coordinator.last_update_success = False
        coordinator.async_add_listener = Mock()
        
        sensor = SeasonalAdaptationSensor(
            coordinator=coordinator,
            base_entity_id="climate.test",
            config_entry=mock_config_entry,
        )
        
        # Initially should return None (not crash)
        initial_result = sensor.is_on
        assert initial_result is None, "Expected None during startup, but got different value"
        
        # Simulate coordinator getting data after startup
        coordinator.data = {
            "seasonal_data": {
                "enabled": True,
                "contribution": 0.3,
            }
        }
        coordinator.last_update_success = True
        
        # Now should return the actual value
        updated_result = sensor.is_on
        
        # Currently FAILS - sensor doesn't handle startup race condition properly
        assert updated_result is True, "Expected True after coordinator gets data, but got different value"
    
    def test_seasonal_adaptation_sensor_properties(self, mock_hass, mock_config_entry, mock_coordinator_valid_seasonal_data):
        """Test SeasonalAdaptationSensor has correct properties and metadata.
        
        This test verifies the sensor has the correct configuration and
        should pass once basic sensor structure is confirmed.
        """
        sensor = SeasonalAdaptationSensor(
            coordinator=mock_coordinator_valid_seasonal_data,
            base_entity_id="climate.test",
            config_entry=mock_config_entry,
        )
        
        # Check sensor properties
        assert sensor.name == "Seasonal Adaptation"
        assert sensor.icon == "mdi:sun-snowflake"
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC
        assert sensor.unique_id == "climate.test_seasonal_adaptation"
        
        # Check sensor inherits from correct base classes
        assert hasattr(sensor, 'is_on')
        assert hasattr(sensor, 'native_value')
        assert sensor.native_value is None  # Binary sensors don't have native_value
        
        # Check sensor doesn't poll
        assert sensor.should_poll is False
    
    def test_seasonal_adaptation_availability(self, mock_hass, mock_config_entry):
        """Test SeasonalAdaptationSensor availability based on coordinator status.
        
        This test verifies the sensor correctly reports availability based on
        coordinator update success status.
        """
        # Test with successful coordinator
        coordinator_success = Mock(spec=DataUpdateCoordinator)
        coordinator_success.last_update_success = True
        coordinator_success.async_add_listener = Mock()
        
        sensor = SeasonalAdaptationSensor(
            coordinator=coordinator_success,
            base_entity_id="climate.test",
            config_entry=mock_config_entry,
        )
        
        assert sensor.available is True
        
        # Test with failed coordinator
        coordinator_failed = Mock(spec=DataUpdateCoordinator)
        coordinator_failed.last_update_success = False
        coordinator_failed.async_add_listener = Mock()
        
        sensor_failed = SeasonalAdaptationSensor(
            coordinator=coordinator_failed,
            base_entity_id="climate.test",
            config_entry=mock_config_entry,
        )
        
        assert sensor_failed.available is False