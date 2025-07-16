"""Test sensor device registry functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo

from custom_components.smart_climate.sensor import (
    SmartClimateDashboardSensor,
    OffsetCurrentSensor,
)
from custom_components.smart_climate.const import DOMAIN


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.title = "Test Climate"
    entry.unique_id = "test_unique_id"
    entry.entry_id = "test_entry_id"
    return entry


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = {
        "calculated_offset": 2.5,
        "learning_info": {
            "enabled": True,
            "samples": 15,
            "accuracy": 0.85
        }
    }
    coordinator.last_update_success = True
    return coordinator


def test_sensor_device_info_creation(mock_coordinator, mock_config_entry):
    """Test that sensor device info is created correctly."""
    
    # Create sensor
    sensor = OffsetCurrentSensor(
        coordinator=mock_coordinator,
        base_entity_id="climate.test_ac",
        config_entry=mock_config_entry,
    )
    
    # Check device info
    device_info = sensor.device_info
    
    # Verify it's a dict-like object (DeviceInfo is a TypedDict)
    from collections.abc import Mapping
    assert isinstance(device_info, Mapping)
    
    # Verify required keys
    if isinstance(device_info, dict):
        assert "identifiers" in device_info
        assert "name" in device_info
        assert (DOMAIN, "test_unique_id_climate_test_ac") in device_info["identifiers"]
        assert device_info["name"] == "Test Climate (climate.test_ac)"
    else:
        # DeviceInfo object
        assert "identifiers" in device_info
        assert "name" in device_info
        assert (DOMAIN, "test_unique_id_climate_test_ac") in device_info["identifiers"]
        assert device_info["name"] == "Test Climate (climate.test_ac)"


def test_sensor_device_info_as_property(mock_coordinator, mock_config_entry):
    """Test device_info property vs attribute."""
    
    # Create sensor
    sensor = OffsetCurrentSensor(
        coordinator=mock_coordinator,
        base_entity_id="climate.test_ac",
        config_entry=mock_config_entry,
    )
    
    # Check that device_info is accessible as both property and attribute
    device_info_attr = sensor._attr_device_info
    device_info_prop = sensor.device_info
    
    # They should be the same
    assert device_info_attr == device_info_prop
    
    # Both should be dict-like
    from collections.abc import Mapping
    assert isinstance(device_info_attr, Mapping)
    assert isinstance(device_info_prop, Mapping)


def test_device_info_unpacking():
    """Test that DeviceInfo can be unpacked correctly."""
    
    # Create a DeviceInfo like our sensors do
    device_info = DeviceInfo(
        identifiers={(DOMAIN, "test_unique_id_climate_test_ac")},
        name="Test Climate (climate.test_ac)",
    )
    
    # Test unpacking with **
    try:
        unpacked = {**device_info}
        assert "identifiers" in unpacked
        assert "name" in unpacked
    except Exception as e:
        pytest.fail(f"DeviceInfo unpacking failed: {e}")
        
    # Test items() iteration
    try:
        for key, value in device_info.items():
            assert key in ["identifiers", "name"]
    except Exception as e:
        pytest.fail(f"DeviceInfo items() iteration failed: {e}")


def test_device_info_string_issue():
    """Test potential string conversion issue."""
    
    # Create a DeviceInfo
    device_info = DeviceInfo(
        identifiers={(DOMAIN, "test_unique_id_climate_test_ac")},
        name="Test Climate (climate.test_ac)",
    )
    
    # Test if accidentally converted to string
    device_info_str = str(device_info)
    assert isinstance(device_info_str, str)
    
    # Verify original is still dict-like
    from collections.abc import Mapping
    assert isinstance(device_info, Mapping)
    
    # Test that the string version would cause the error
    # This simulates what happens if device_info gets converted to string
    try:
        # This would cause the error "argument after ** must be a mapping, not str"
        unpacked = {**device_info_str}
        pytest.fail("String unpacking should have failed")
    except TypeError as e:
        assert "str' object is not a mapping" in str(e)