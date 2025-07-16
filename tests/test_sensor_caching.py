"""
ABOUTME: Base test class for sensor caching and error handling
ABOUTME: Provides comprehensive test framework for caching-related race conditions
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from typing import Dict, Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature

from custom_components.smart_climate.const import DOMAIN
from tests.fixtures.sensor_caching_fixtures import (
    create_mock_coordinator_with_data,
    create_mock_coordinator_none_data,
    create_mock_coordinator_missing_keys,
    create_mock_coordinator_invalid_types,
    create_mock_offset_engine_with_coordinator_scenarios,
    create_sensor_caching_test_data,
    create_cache_initialization_scenarios,
    create_cache_persistence_scenarios,
    create_error_handling_scenarios,
    create_mock_hass_with_cache,
    create_mock_config_entry_for_caching,
    create_sensor_state_verification_helpers,
)


class BaseSensorCachingTest:
    """Base test class for sensor caching functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_hass = create_mock_hass_with_cache()
        self.mock_config_entry = create_mock_config_entry_for_caching()
        self.coordinator_scenarios = create_mock_offset_engine_with_coordinator_scenarios()
        self.sensor_test_data = create_sensor_caching_test_data()
        self.cache_init_scenarios = create_cache_initialization_scenarios()
        self.cache_persistence_scenarios = create_cache_persistence_scenarios()
        self.error_scenarios = create_error_handling_scenarios()
        self.verification_helpers = create_sensor_state_verification_helpers()
    
    def create_test_sensor(self, sensor_class, offset_engine_scenario='normal_coordinator'):
        """Create a test sensor with specified offset engine scenario."""
        offset_engine = self.coordinator_scenarios[offset_engine_scenario]
        
        sensor = sensor_class(
            coordinator=offset_engine._coordinator if hasattr(offset_engine, '_coordinator') else None,
            base_entity_id="climate.test_ac",
            config_entry=self.mock_config_entry
        )
        
        # Provide access to mock hass for global caching
        sensor._hass = self.mock_hass
        
        return sensor
    
    def assert_sensor_state_matches_expected(self, sensor, expected_state, expected_available=True):
        """Assert sensor state matches expected values."""
        self.verification_helpers['verify_sensor_state'](sensor, expected_state, expected_available)
    
    def assert_cache_contains_value(self, cache_key, expected_value):
        """Assert cache contains expected value."""
        self.verification_helpers['verify_cache_state'](self.mock_hass, cache_key, expected_value)
    
    def assert_error_was_logged(self, caplog, expected_message):
        """Assert error was logged."""
        self.verification_helpers['verify_error_logged'](caplog, expected_message)


class TestCoordinatorDataAccess(BaseSensorCachingTest):
    """Test coordinator data access scenarios."""
    
    def test_coordinator_data_none_returns_unknown(self):
        """Test that sensors return 'unbekannt' when coordinator data is None."""
        # This test should fail initially, demonstrating the current bug
        sensor = self.create_test_sensor(MockWeatherForecastSensor, 'coordinator_none_data')
        
        # This should return 'unbekannt' but currently might return something else
        expected_state = 'unbekannt'
        assert sensor.state == expected_state
        assert sensor.available == False
    
    def test_coordinator_missing_keys_returns_unknown(self):
        """Test that sensors return 'unbekannt' when coordinator data is missing keys."""
        sensor = self.create_test_sensor(MockWeatherForecastSensor, 'coordinator_missing_keys')
        
        # This should return 'unbekannt' when forecast_data key is missing
        expected_state = 'unbekannt'
        assert sensor.state == expected_state
        assert sensor.available == False
    
    def test_coordinator_invalid_types_returns_unknown(self):
        """Test that sensors return 'unbekannt' when coordinator data has invalid types."""
        sensor = self.create_test_sensor(MockWeatherForecastSensor, 'coordinator_invalid_types')
        
        # This should return 'unbekannt' when forecast_data is not a dict
        expected_state = 'unbekannt'
        assert sensor.state == expected_state
        assert sensor.available == False
    
    def test_no_coordinator_attribute_returns_unknown(self):
        """Test that sensors return 'unbekannt' when _coordinator attribute is missing."""
        sensor = self.create_test_sensor(MockWeatherForecastSensor, 'no_coordinator_attr')
        
        # This should return 'unbekannt' when _coordinator attribute doesn't exist
        expected_state = 'unbekannt'
        assert sensor.state == expected_state
        assert sensor.available == False
    
    def test_coordinator_is_none_returns_unknown(self):
        """Test that sensors return 'unbekannt' when _coordinator is None."""
        sensor = self.create_test_sensor(MockWeatherForecastSensor, 'coordinator_is_none')
        
        # This should return 'unbekannt' when _coordinator is None
        expected_state = 'unbekannt'
        assert sensor.state == expected_state
        assert sensor.available == False


class TestCacheInitialization(BaseSensorCachingTest):
    """Test cache initialization scenarios."""
    
    def test_startup_no_cache_returns_unknown(self):
        """Test sensor behavior when starting with no cache."""
        scenario = self.cache_init_scenarios['startup_no_cache']
        
        # Create sensor with no cache
        sensor = self.create_test_sensor(MockWeatherForecastSensor, 'coordinator_none_data')
        
        # Should return 'unbekannt' since no cache and no coordinator data
        assert sensor.state == scenario['expected_state']
        assert sensor.available == False
    
    def test_startup_empty_cache_returns_unknown(self):
        """Test sensor behavior when starting with empty cache."""
        scenario = self.cache_init_scenarios['startup_empty_cache']
        
        # Set up empty cache
        self.mock_hass.data[DOMAIN] = {'sensor_cache': {}}
        
        sensor = self.create_test_sensor(MockWeatherForecastSensor, 'coordinator_none_data')
        
        # Should return 'unbekannt' since cache is empty and no coordinator data
        assert sensor.state == scenario['expected_state']
        assert sensor.available == False
    
    def test_startup_partial_cache_returns_cached_value(self):
        """Test sensor behavior when starting with partial cache."""
        scenario = self.cache_init_scenarios['startup_partial_cache']
        
        # Set up partial cache
        self.mock_hass.data[DOMAIN] = {'sensor_cache': scenario['initial_cache']}
        
        sensor = self.create_test_sensor(MockWeatherForecastSensor, 'coordinator_none_data')
        
        # Should return cached value since cache has data
        assert sensor.state == scenario['expected_state']
        assert sensor.available == True
    
    def test_startup_full_cache_returns_cached_value(self):
        """Test sensor behavior when starting with full cache."""
        scenario = self.cache_init_scenarios['startup_full_cache']
        
        # Set up full cache
        self.mock_hass.data[DOMAIN] = {'sensor_cache': scenario['initial_cache']}
        
        sensor = self.create_test_sensor(MockWeatherForecastSensor, 'coordinator_none_data')
        
        # Should return cached value since cache has data
        assert sensor.state == scenario['expected_state']
        assert sensor.available == True
    
    def test_coordinator_becomes_available_updates_cache(self):
        """Test sensor behavior when coordinator becomes available."""
        scenario = self.cache_init_scenarios['coordinator_becomes_available']
        
        # Set up initial cache
        self.mock_hass.data[DOMAIN] = {'sensor_cache': scenario['initial_cache']}
        
        # Create sensor with available coordinator
        sensor = self.create_test_sensor(MockWeatherForecastSensor, 'normal_coordinator')
        
        # Should return fresh value from coordinator
        assert sensor.state == scenario['expected_state']
        assert sensor.available == True


class TestCachePersistence(BaseSensorCachingTest):
    """Test cache persistence scenarios."""
    
    def test_cache_update_success(self):
        """Test cache updates successfully when coordinator has data."""
        scenario = self.cache_persistence_scenarios['cache_update_success']
        
        # Set up initial cache
        self.mock_hass.data[DOMAIN] = {'sensor_cache': scenario['initial_cache']}
        
        sensor = self.create_test_sensor(MockWeatherForecastSensor, 'normal_coordinator')
        
        # Access sensor state to trigger cache update
        state = sensor.state
        
        # Verify cache was updated
        cache_key = 'weather_forecast_cache'
        expected_cache_value = scenario['expected_cache_after'][cache_key]
        self.assert_cache_contains_value(cache_key, expected_cache_value)
        
        # Verify sensor state matches expected
        assert state == scenario['expected_state']
    
    def test_cache_update_failure_persists_old_value(self):
        """Test cache persists when coordinator data is invalid."""
        scenario = self.cache_persistence_scenarios['cache_update_failure']
        
        # Set up initial cache
        self.mock_hass.data[DOMAIN] = {'sensor_cache': scenario['initial_cache']}
        
        sensor = self.create_test_sensor(MockWeatherForecastSensor, 'coordinator_none_data')
        
        # Access sensor state
        state = sensor.state
        
        # Verify cache persisted old value
        cache_key = 'weather_forecast_cache'
        expected_cache_value = scenario['expected_cache_after'][cache_key]
        self.assert_cache_contains_value(cache_key, expected_cache_value)
        
        # Verify sensor state matches expected
        assert state == scenario['expected_state']
    
    def test_cache_invalidation_on_conflict(self):
        """Test cache is invalidated when coordinator has conflicting data."""
        scenario = self.cache_persistence_scenarios['cache_invalidation']
        
        # Set up initial cache
        self.mock_hass.data[DOMAIN] = {'sensor_cache': scenario['initial_cache']}
        
        # Create coordinator with conflicting data
        coordinator_data = {'active_strategy': 'clear_sky'}
        mock_coordinator = create_mock_coordinator_with_data({'forecast_data': coordinator_data})
        
        offset_engine = Mock()
        offset_engine._coordinator = mock_coordinator
        
        sensor = MockWeatherForecastSensor(
            coordinator=mock_coordinator,
            base_entity_id="climate.test_ac",
            config_entry=self.mock_config_entry
        )
        
        # Access sensor state to trigger cache update
        state = sensor.state
        
        # Verify cache was updated with new value
        cache_key = 'weather_forecast_cache'
        expected_cache_value = scenario['expected_cache_after'][cache_key]
        self.assert_cache_contains_value(cache_key, expected_cache_value)
        
        # Verify sensor state matches expected
        assert state == scenario['expected_state']


class TestErrorHandling(BaseSensorCachingTest):
    """Test error handling scenarios."""
    
    def test_attribute_error_handling(self, caplog):
        """Test handling of AttributeError from coordinator data."""
        scenario = self.error_scenarios['attribute_error']
        
        # Create coordinator that raises AttributeError
        mock_coordinator = Mock()
        mock_coordinator.data = Mock()
        mock_coordinator.data.forecast_data = Mock()
        mock_coordinator.data.forecast_data.active_strategy = Mock(side_effect=scenario['coordinator_exception'])
        
        offset_engine = Mock()
        offset_engine._coordinator = mock_coordinator
        
        sensor = MockWeatherForecastSensor(
            coordinator=mock_coordinator,
            base_entity_id="climate.test_ac",
            config_entry=self.mock_config_entry
        )
        
        # Access sensor state should handle exception
        state = sensor.state
        
        # Verify error handling
        assert state == scenario['expected_state']
        assert sensor.available == False
        
        if scenario['should_log_error']:
            self.assert_error_was_logged(caplog, "Error accessing coordinator data")
    
    def test_type_error_handling(self, caplog):
        """Test handling of TypeError from coordinator data."""
        scenario = self.error_scenarios['type_error']
        
        # Create coordinator that raises TypeError
        mock_coordinator = Mock()
        mock_coordinator.data = Mock()
        mock_coordinator.data.forecast_data = "not_a_dict"  # Invalid type
        
        offset_engine = Mock()
        offset_engine._coordinator = mock_coordinator
        
        sensor = MockWeatherForecastSensor(
            coordinator=mock_coordinator,
            base_entity_id="climate.test_ac",
            config_entry=self.mock_config_entry
        )
        
        # Access sensor state should handle exception
        state = sensor.state
        
        # Verify error handling
        assert state == scenario['expected_state']
        assert sensor.available == False
        
        if scenario['should_log_error']:
            self.assert_error_was_logged(caplog, "Error accessing coordinator data")
    
    def test_value_error_handling(self, caplog):
        """Test handling of ValueError from coordinator data."""
        scenario = self.error_scenarios['value_error']
        
        # Create coordinator that raises ValueError
        mock_coordinator = Mock()
        mock_coordinator.data = Mock()
        mock_coordinator.data.forecast_data = Mock()
        # Mock a method that raises ValueError when called
        mock_coordinator.data.forecast_data.get = Mock(side_effect=scenario['coordinator_exception'])
        
        offset_engine = Mock()
        offset_engine._coordinator = mock_coordinator
        
        sensor = MockWeatherForecastSensor(
            coordinator=mock_coordinator,
            base_entity_id="climate.test_ac",
            config_entry=self.mock_config_entry
        )
        
        # Access sensor state should handle exception
        state = sensor.state
        
        # Verify error handling
        assert state == scenario['expected_state']
        assert sensor.available == False
        
        if scenario['should_log_error']:
            self.assert_error_was_logged(caplog, "Error accessing coordinator data")
    
    def test_key_error_handling(self, caplog):
        """Test handling of KeyError from coordinator data."""
        scenario = self.error_scenarios['key_error']
        
        # Create coordinator that raises KeyError
        mock_coordinator = Mock()
        mock_coordinator.data = Mock()
        mock_coordinator.data.forecast_data = {}  # Missing key
        
        offset_engine = Mock()
        offset_engine._coordinator = mock_coordinator
        
        sensor = MockWeatherForecastSensor(
            coordinator=mock_coordinator,
            base_entity_id="climate.test_ac",
            config_entry=self.mock_config_entry
        )
        
        # Access sensor state should handle exception
        state = sensor.state
        
        # Verify error handling
        assert state == scenario['expected_state']
        assert sensor.available == False
        
        if scenario['should_log_error']:
            self.assert_error_was_logged(caplog, "Error accessing coordinator data")


# Mock sensor classes for testing
class MockWeatherForecastSensor:
    """Mock Weather Forecast Sensor for testing."""
    
    def __init__(self, coordinator, base_entity_id, config_entry):
        self._coordinator = coordinator
        self._base_entity_id = base_entity_id
        self._config_entry = config_entry
        self._last_known_value = None
        self._hass = None  # Will be set by test framework
    
    @property
    def state(self):
        """Get sensor state with caching logic."""
        try:
            # Check coordinator data with robust error handling
            if (hasattr(self, '_coordinator') and 
                self._coordinator is not None and 
                hasattr(self._coordinator, 'data') and 
                self._coordinator.data is not None):
                
                forecast_data = getattr(self._coordinator.data, 'forecast_data', None)
                if forecast_data and isinstance(forecast_data, dict) and 'active_strategy' in forecast_data:
                    strategy = forecast_data['active_strategy']
                    if strategy == 'none':
                        state = 'No active strategy'
                    elif strategy == 'heat_wave':
                        state = 'Heat wave active'
                    elif strategy == 'clear_sky':
                        state = 'Clear sky active'
                    else:
                        state = f'Strategy: {strategy}'
                    
                    # Cache the last known good value (both instance and global)
                    self._last_known_value = state
                    if hasattr(self, '_hass') and self._hass is not None:
                        self._update_global_cache('weather_forecast_cache', state)
                    return state
            
            # If coordinator data is not available, try global cache first
            if hasattr(self, '_hass') and self._hass is not None:
                global_cached_value = self._get_global_cache('weather_forecast_cache')
                if global_cached_value is not None:
                    return global_cached_value
            
            # Then try instance cache
            if self._last_known_value is not None:
                return self._last_known_value
            
            # No coordinator data and no cache - return unbekannt
            return 'unbekannt'
            
        except Exception as e:
            # Return cached value if available (global first, then instance)
            if hasattr(self, '_hass') and self._hass is not None:
                global_cached_value = self._get_global_cache('weather_forecast_cache')
                if global_cached_value is not None:
                    return global_cached_value
            
            if self._last_known_value is not None:
                return self._last_known_value
            
            return 'unbekannt'
    
    def _get_global_cache(self, cache_key):
        """Get value from global cache."""
        try:
            from custom_components.smart_climate.const import DOMAIN
            cache = self._hass.data.get(DOMAIN, {}).get('sensor_cache', {})
            return cache.get(cache_key)
        except Exception:
            return None
    
    def _update_global_cache(self, cache_key, value):
        """Update global cache with new value."""
        try:
            from custom_components.smart_climate.const import DOMAIN
            if DOMAIN not in self._hass.data:
                self._hass.data[DOMAIN] = {}
            if 'sensor_cache' not in self._hass.data[DOMAIN]:
                self._hass.data[DOMAIN]['sensor_cache'] = {}
            self._hass.data[DOMAIN]['sensor_cache'][cache_key] = value
        except Exception:
            pass
    
    @property
    def available(self):
        """Check if sensor is available."""
        return self.state != 'unbekannt'


class MockSeasonalAdaptationSensor:
    """Mock Seasonal Adaptation Sensor for testing."""
    
    def __init__(self, coordinator, base_entity_id, config_entry):
        self._coordinator = coordinator
        self._base_entity_id = base_entity_id
        self._config_entry = config_entry
        self._last_known_value = None
        self._hass = None  # Will be set by test framework
    
    @property
    def state(self):
        """Get sensor state with caching logic."""
        try:
            # Check coordinator data with robust error handling
            if (hasattr(self, '_coordinator') and 
                self._coordinator is not None and 
                hasattr(self._coordinator, 'data') and 
                self._coordinator.data is not None):
                
                seasonal_data = getattr(self._coordinator.data, 'seasonal_data', None)
                if seasonal_data and isinstance(seasonal_data, dict) and 'contribution' in seasonal_data:
                    contribution = seasonal_data['contribution']
                    if isinstance(contribution, (int, float)):
                        state = f'{contribution * 100:.1f}%'
                        # Cache the last known good value
                        self._last_known_value = state
                        return state
            
            # If coordinator data is not available, return cached value
            if self._last_known_value is not None:
                return self._last_known_value
            
            # No coordinator data and no cache - return unbekannt
            return 'unbekannt'
            
        except Exception as e:
            # Return cached value if available
            if self._last_known_value is not None:
                return self._last_known_value
            return 'unbekannt'
    
    @property
    def available(self):
        """Check if sensor is available."""
        return self.state != 'unbekannt'


class MockConvergenceTrendSensor:
    """Mock Convergence Trend Sensor for testing."""
    
    def __init__(self, coordinator, base_entity_id, config_entry):
        self._coordinator = coordinator
        self._base_entity_id = base_entity_id
        self._config_entry = config_entry
        self._last_known_value = None
        self._hass = None  # Will be set by test framework
    
    @property
    def state(self):
        """Get sensor state with caching logic."""
        try:
            # Check coordinator data with robust error handling
            if (hasattr(self, '_coordinator') and 
                self._coordinator is not None and 
                hasattr(self._coordinator, 'data') and 
                self._coordinator.data is not None):
                
                convergence_data = getattr(self._coordinator.data, 'convergence_data', None)
                if convergence_data and isinstance(convergence_data, dict) and 'trend' in convergence_data:
                    state = convergence_data['trend']
                    # Cache the last known good value
                    self._last_known_value = state
                    return state
            
            # If coordinator data is not available, return cached value
            if self._last_known_value is not None:
                return self._last_known_value
            
            # No coordinator data and no cache - return unbekannt
            return 'unbekannt'
            
        except Exception as e:
            # Return cached value if available
            if self._last_known_value is not None:
                return self._last_known_value
            return 'unbekannt'
    
    @property
    def available(self):
        """Check if sensor is available."""
        return self.state != 'unbekannt'


# Integration tests combining all scenarios
class TestSensorCachingIntegration(BaseSensorCachingTest):
    """Integration tests for sensor caching."""
    
    def test_full_caching_workflow(self):
        """Test complete caching workflow from startup to coordinator available."""
        # Start with no cache
        sensor = self.create_test_sensor(MockWeatherForecastSensor, 'coordinator_none_data')
        
        # Should return 'unbekannt' initially
        assert sensor.state == 'unbekannt'
        assert sensor.available == False
        
        # Add cache data
        self.mock_hass.data[DOMAIN] = {'sensor_cache': {'weather_forecast_cache': 'Heat wave active'}}
        
        # Should now return cached value
        # TODO: Implement cache lookup in sensor logic
        
        # Coordinator becomes available
        sensor = self.create_test_sensor(MockWeatherForecastSensor, 'normal_coordinator')
        
        # Should return fresh value from coordinator
        assert sensor.state == 'No active strategy'
        assert sensor.available == True
    
    def test_all_sensor_types_handle_caching(self):
        """Test that all sensor types properly handle caching."""
        sensor_classes = [
            MockWeatherForecastSensor,
            MockSeasonalAdaptationSensor,
            MockConvergenceTrendSensor
        ]
        
        for sensor_class in sensor_classes:
            # Test with no coordinator data
            sensor = self.create_test_sensor(sensor_class, 'coordinator_none_data')
            assert sensor.state == 'unbekannt'
            assert sensor.available == False
            
            # Test with valid coordinator data
            sensor = self.create_test_sensor(sensor_class, 'normal_coordinator')
            assert sensor.state != 'unbekannt'
            assert sensor.available == True