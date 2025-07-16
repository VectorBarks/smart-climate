"""
ABOUTME: Test fixtures for sensor caching and error handling scenarios
ABOUTME: Provides comprehensive mock scenarios for caching-related race conditions
"""

from unittest.mock import Mock, AsyncMock
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
import pytest

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


class MockCoordinatorData:
    """Mock coordinator data object with configurable attributes."""
    
    def __init__(self, **kwargs):
        """Initialize with configurable attributes."""
        # Set all provided attributes
        for key, value in kwargs.items():
            setattr(self, key, value)


def create_mock_coordinator_with_data(data_attrs: Dict[str, Any]) -> Mock:
    """Create a mock coordinator with specified data attributes."""
    mock_coordinator = Mock()
    mock_coordinator.data = MockCoordinatorData(**data_attrs)
    return mock_coordinator


def create_mock_coordinator_none_data() -> Mock:
    """Create a mock coordinator with None data."""
    mock_coordinator = Mock()
    mock_coordinator.data = None
    return mock_coordinator


def create_mock_coordinator_missing_keys(present_keys: List[str]) -> Mock:
    """Create a mock coordinator with only specified keys present."""
    data_attrs = {}
    
    # Only include the specified keys
    all_possible_keys = [
        'calculated_offset', 'room_temp', 'outdoor_temp', 'power',
        'mode_adjustments', 'learning_info', 'forecast_data',
        'seasonal_data', 'convergence_data'
    ]
    
    for key in all_possible_keys:
        if key in present_keys:
            # Set reasonable default values
            if key == 'calculated_offset':
                data_attrs[key] = 1.5
            elif key == 'room_temp':
                data_attrs[key] = 22.0
            elif key == 'outdoor_temp':
                data_attrs[key] = 28.0
            elif key == 'power':
                data_attrs[key] = 150.0
            elif key == 'mode_adjustments':
                data_attrs[key] = Mock()
            elif key == 'learning_info':
                data_attrs[key] = {'enabled': True, 'samples': 5}
            elif key == 'forecast_data':
                data_attrs[key] = {'active_strategy': 'none'}
            elif key == 'seasonal_data':
                data_attrs[key] = {'enabled': True, 'contribution': 0.2}
            elif key == 'convergence_data':
                data_attrs[key] = {'trend': 'stable'}
    
    return create_mock_coordinator_with_data(data_attrs)


def create_mock_coordinator_invalid_types() -> Mock:
    """Create a mock coordinator with invalid data types."""
    data_attrs = {
        'calculated_offset': "not_a_number",  # Should be float
        'room_temp': [],  # Should be float
        'outdoor_temp': {},  # Should be float
        'power': "150",  # Should be float
        'learning_info': "not_a_dict",  # Should be dict
        'forecast_data': None,  # Should be dict
        'seasonal_data': "invalid",  # Should be dict
        'convergence_data': 42  # Should be dict
    }
    
    return create_mock_coordinator_with_data(data_attrs)


def create_mock_offset_engine_with_coordinator_scenarios() -> Dict[str, Mock]:
    """Create mock offset engines for different coordinator scenarios."""
    scenarios = {}
    
    # Scenario 1: Normal coordinator with data
    scenarios['normal_coordinator'] = Mock()
    scenarios['normal_coordinator'].is_learning_enabled = True
    scenarios['normal_coordinator']._coordinator = create_mock_coordinator_with_data({
        'calculated_offset': 1.5,
        'room_temp': 22.0,
        'outdoor_temp': 28.0,
        'power': 150.0,
        'learning_info': {'enabled': True, 'samples': 8},
        'forecast_data': {'active_strategy': 'none'},
        'seasonal_data': {'enabled': True, 'contribution': 0.2},
        'convergence_data': {'trend': 'stable'}
    })
    
    # Scenario 2: Coordinator with None data
    scenarios['coordinator_none_data'] = Mock()
    scenarios['coordinator_none_data'].is_learning_enabled = True
    scenarios['coordinator_none_data']._coordinator = create_mock_coordinator_none_data()
    
    # Scenario 3: Coordinator with missing keys
    scenarios['coordinator_missing_keys'] = Mock()
    scenarios['coordinator_missing_keys'].is_learning_enabled = True
    scenarios['coordinator_missing_keys']._coordinator = create_mock_coordinator_missing_keys(['calculated_offset', 'room_temp'])
    
    # Scenario 4: Coordinator with invalid types
    scenarios['coordinator_invalid_types'] = Mock()
    scenarios['coordinator_invalid_types'].is_learning_enabled = True
    scenarios['coordinator_invalid_types']._coordinator = create_mock_coordinator_invalid_types()
    
    # Scenario 5: No coordinator attribute
    scenarios['no_coordinator_attr'] = Mock()
    scenarios['no_coordinator_attr'].is_learning_enabled = True
    # Don't set _coordinator at all - use spec to prevent dynamic attribute creation
    scenarios['no_coordinator_attr'] = Mock(spec=['is_learning_enabled'])
    
    # Scenario 6: Coordinator is None
    scenarios['coordinator_is_none'] = Mock()
    scenarios['coordinator_is_none'].is_learning_enabled = True
    scenarios['coordinator_is_none']._coordinator = None
    
    return scenarios


def create_sensor_caching_test_data() -> Dict[str, Dict[str, Any]]:
    """Create test data for sensor caching scenarios."""
    return {
        'weather_forecast': {
            'coordinator_key': 'forecast_data',
            'expected_states': {
                'normal': 'No active strategy',
                'missing_key': 'unbekannt',
                'invalid_type': 'unbekannt',
                'none_data': 'unbekannt'
            },
            'cache_key': 'weather_forecast_cache',
            'fallback_value': 'No active strategy'
        },
        'seasonal_adaptation': {
            'coordinator_key': 'seasonal_data',
            'expected_states': {
                'normal': '20.0%',
                'missing_key': 'unbekannt',
                'invalid_type': 'unbekannt',
                'none_data': 'unbekannt'
            },
            'cache_key': 'seasonal_adaptation_cache',
            'fallback_value': '0.0%'
        },
        'convergence_trend': {
            'coordinator_key': 'convergence_data',
            'expected_states': {
                'normal': 'stable',
                'missing_key': 'unbekannt',
                'invalid_type': 'unbekannt',
                'none_data': 'unbekannt'
            },
            'cache_key': 'convergence_trend_cache',
            'fallback_value': 'unknown'
        }
    }


def create_cache_initialization_scenarios() -> Dict[str, Dict[str, Any]]:
    """Create scenarios for cache initialization testing."""
    return {
        'startup_no_cache': {
            'description': 'Sensor starts with no cache at all',
            'initial_cache': None,
            'coordinator_available': False,
            'expected_state': 'unbekannt'
        },
        'startup_empty_cache': {
            'description': 'Sensor starts with empty cache dict',
            'initial_cache': {},
            'coordinator_available': False,
            'expected_state': 'unbekannt'
        },
        'startup_partial_cache': {
            'description': 'Sensor starts with partial cache data',
            'initial_cache': {'weather_forecast_cache': 'Heat wave active'},
            'coordinator_available': False,
            'expected_state': 'Heat wave active'
        },
        'startup_full_cache': {
            'description': 'Sensor starts with full cache data',
            'initial_cache': {
                'weather_forecast_cache': 'Heat wave active',
                'seasonal_adaptation_cache': '15.0%',
                'convergence_trend_cache': 'improving'
            },
            'coordinator_available': False,
            'expected_state': 'Heat wave active'  # For weather sensor
        },
        'coordinator_becomes_available': {
            'description': 'Coordinator becomes available after startup',
            'initial_cache': {'weather_forecast_cache': 'Heat wave active'},
            'coordinator_available': True,
            'expected_state': 'No active strategy'  # Fresh from coordinator
        }
    }


def create_cache_persistence_scenarios() -> Dict[str, Dict[str, Any]]:
    """Create scenarios for cache persistence testing."""
    return {
        'cache_update_success': {
            'description': 'Cache successfully updates when coordinator has data',
            'initial_cache': {'weather_forecast_cache': 'old_value'},
            'coordinator_data': {'active_strategy': 'heat_wave'},
            'expected_cache_after': {'weather_forecast_cache': 'Heat wave active'},
            'expected_state': 'Heat wave active'
        },
        'cache_update_failure': {
            'description': 'Cache persists when coordinator data is invalid',
            'initial_cache': {'weather_forecast_cache': 'Heat wave active'},
            'coordinator_data': None,
            'expected_cache_after': {'weather_forecast_cache': 'Heat wave active'},
            'expected_state': 'Heat wave active'
        },
        'cache_invalidation': {
            'description': 'Cache is invalidated when coordinator has conflicting data',
            'initial_cache': {'weather_forecast_cache': 'Heat wave active'},
            'coordinator_data': {'active_strategy': 'clear_sky'},
            'expected_cache_after': {'weather_forecast_cache': 'Clear sky active'},
            'expected_state': 'Clear sky active'
        }
    }


def create_error_handling_scenarios() -> Dict[str, Dict[str, Any]]:
    """Create scenarios for error handling testing."""
    return {
        'attribute_error': {
            'description': 'Coordinator data raises AttributeError',
            'coordinator_exception': AttributeError("'NoneType' object has no attribute 'active_strategy'"),
            'expected_state': 'unbekannt',
            'should_log_error': True
        },
        'type_error': {
            'description': 'Coordinator data raises TypeError',
            'coordinator_exception': TypeError("unsupported operand type(s) for *: 'str' and 'int'"),
            'expected_state': 'unbekannt',
            'should_log_error': True
        },
        'value_error': {
            'description': 'Coordinator data raises ValueError',
            'coordinator_exception': ValueError("invalid literal for int() with base 10: 'abc'"),
            'expected_state': 'unbekannt',
            'should_log_error': True
        },
        'key_error': {
            'description': 'Coordinator data raises KeyError',
            'coordinator_exception': KeyError("'active_strategy'"),
            'expected_state': 'unbekannt',
            'should_log_error': True
        }
    }


@pytest.fixture
def mock_coordinator_scenarios():
    """Fixture providing mock coordinator scenarios."""
    return create_mock_offset_engine_with_coordinator_scenarios()


@pytest.fixture
def sensor_caching_test_data():
    """Fixture providing sensor caching test data."""
    return create_sensor_caching_test_data()


@pytest.fixture
def cache_initialization_scenarios():
    """Fixture providing cache initialization scenarios."""
    return create_cache_initialization_scenarios()


@pytest.fixture
def cache_persistence_scenarios():
    """Fixture providing cache persistence scenarios."""
    return create_cache_persistence_scenarios()


@pytest.fixture
def error_handling_scenarios():
    """Fixture providing error handling scenarios."""
    return create_error_handling_scenarios()


def create_mock_hass_with_cache(cache_data: Optional[Dict[str, Any]] = None) -> Mock:
    """Create a mock hass instance with configurable cache data."""
    mock_hass = Mock()
    mock_hass.data = {}
    
    if cache_data is not None:
        mock_hass.data[DOMAIN] = {'sensor_cache': cache_data}
    
    return mock_hass


def create_mock_config_entry_for_caching():
    """Create a mock config entry for caching tests."""
    entry = Mock(spec=ConfigEntry)
    entry.entry_id = "test_cache_entry"
    entry.unique_id = "test_cache_unique"
    entry.title = "Test Cache Smart Climate"
    entry.data = {
        "climate_entity": "climate.test_ac",
        "room_sensor": "sensor.test_room",
        "power_sensor": "sensor.test_power",
        "max_offset": 5.0,
        "enable_learning": True,
    }
    return entry


def create_sensor_state_verification_helpers():
    """Create helper functions for verifying sensor states."""
    def verify_sensor_state(sensor, expected_state, expected_available=True):
        """Verify sensor state matches expected values."""
        assert sensor.state == expected_state
        assert sensor.available == expected_available
    
    def verify_cache_state(hass, cache_key, expected_value):
        """Verify cache contains expected value."""
        cache = hass.data.get(DOMAIN, {}).get('sensor_cache', {})
        assert cache.get(cache_key) == expected_value
    
    def verify_error_logged(caplog, expected_message):
        """Verify error was logged."""
        assert expected_message in caplog.text
    
    return {
        'verify_sensor_state': verify_sensor_state,
        'verify_cache_state': verify_cache_state,
        'verify_error_logged': verify_error_logged
    }


@pytest.fixture
def state_verification_helpers():
    """Fixture providing state verification helpers."""
    return create_sensor_state_verification_helpers()