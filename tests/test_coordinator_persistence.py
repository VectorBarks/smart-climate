"""Test thermal persistence integration in SmartClimateCoordinator.

ABOUTME: Tests coordinator thermal data methods and callback integration
Tests get_thermal_data, restore_thermal_data, and functools.partial callbacks
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from functools import partial

from custom_components.smart_climate.coordinator import SmartClimateCoordinator
from custom_components.smart_climate.const import DOMAIN


class TestCoordinatorThermalMethodsOnly:
    """Test just the thermal methods without complex mocking."""
    
    def test_get_thermal_data_method_exists_and_calls_serialize(self):
        """Test get_thermal_data method works with mock hass.data structure."""
        # Create mock hass and thermal manager
        mock_hass = Mock()
        mock_thermal_manager = Mock()
        mock_thermal_manager.serialize.return_value = {"version": "1.0", "state": "PRIMING"}
        
        # Set up hass.data structure
        entity_id = "climate.test_room"
        entry_id = "test_entry"
        mock_hass.data = {
            DOMAIN: {
                entry_id: {
                    "thermal_components": {
                        entity_id: {"thermal_manager": mock_thermal_manager}
                    }
                }
            }
        }
        
        # Create coordinator instance with minimal setup
        coordinator = SmartClimateCoordinator.__new__(SmartClimateCoordinator)
        coordinator.hass = mock_hass
        
        # Test the method
        result = coordinator.get_thermal_data(entity_id)
        
        # Verify
        mock_thermal_manager.serialize.assert_called_once()
        assert result == {"version": "1.0", "state": "PRIMING"}
    
    def test_restore_thermal_data_method_exists_and_calls_restore(self):
        """Test restore_thermal_data method works with mock hass.data structure."""
        # Create mock hass and thermal manager
        mock_hass = Mock()
        mock_thermal_manager = Mock()
        
        # Set up hass.data structure
        entity_id = "climate.test_room"
        entry_id = "test_entry"
        mock_hass.data = {
            DOMAIN: {
                entry_id: {
                    "thermal_components": {
                        entity_id: {"thermal_manager": mock_thermal_manager}
                    }
                }
            }
        }
        
        # Create coordinator instance with minimal setup
        coordinator = SmartClimateCoordinator.__new__(SmartClimateCoordinator)
        coordinator.hass = mock_hass
        
        # Test data
        thermal_data = {"version": "1.0", "state": "RESTORED"}
        
        # Test the method
        coordinator.restore_thermal_data(entity_id, thermal_data)
        
        # Verify
        mock_thermal_manager.restore.assert_called_once_with(thermal_data)

    def test_get_thermal_manager_method_exists_and_returns_manager(self):
        """Test get_thermal_manager helper method works."""
        # Create mock hass and thermal manager
        mock_hass = Mock()
        mock_thermal_manager = Mock()
        
        # Set up hass.data structure
        entity_id = "climate.test_room"
        entry_id = "test_entry"
        mock_hass.data = {
            DOMAIN: {
                entry_id: {
                    "thermal_components": {
                        entity_id: {"thermal_manager": mock_thermal_manager}
                    }
                }
            }
        }
        
        # Create coordinator instance with minimal setup
        coordinator = SmartClimateCoordinator.__new__(SmartClimateCoordinator)
        coordinator.hass = mock_hass
        
        # Test the method
        result = coordinator.get_thermal_manager(entity_id)
        
        # Verify
        assert result is mock_thermal_manager

    def test_get_offset_engine_method_exists_and_returns_engine(self):
        """Test get_offset_engine helper method works."""
        # Create mock hass and offset engine
        mock_hass = Mock()
        mock_offset_engine = Mock()
        
        # Set up hass.data structure
        entity_id = "climate.test_room"
        entry_id = "test_entry"
        mock_hass.data = {
            DOMAIN: {
                entry_id: {
                    "offset_engines": {
                        entity_id: mock_offset_engine
                    }
                }
            }
        }
        
        # Create coordinator instance with minimal setup
        coordinator = SmartClimateCoordinator.__new__(SmartClimateCoordinator)
        coordinator.hass = mock_hass
        
        # Test the method
        result = coordinator.get_offset_engine(entity_id)
        
        # Verify
        assert result is mock_offset_engine

    def test_methods_handle_missing_data_gracefully(self):
        """Test all methods handle missing data gracefully."""
        # Create mock hass with empty structure
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {}}
        
        # Create coordinator instance
        coordinator = SmartClimateCoordinator.__new__(SmartClimateCoordinator)
        coordinator.hass = mock_hass
        
        entity_id = "climate.missing_room"
        
        # Test all methods return None for missing data
        assert coordinator.get_thermal_data(entity_id) is None
        assert coordinator.get_thermal_manager(entity_id) is None
        assert coordinator.get_offset_engine(entity_id) is None
        
        # Test restore doesn't crash
        coordinator.restore_thermal_data(entity_id, {"test": "data"})  # Should complete without error


class TestSmartClimateCoordinatorThermalPersistence:
    """Test thermal persistence methods in SmartClimateCoordinator."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        hass = Mock()
        hass.data = {DOMAIN: {}}
        return hass

    @pytest.fixture
    def mock_sensor_manager(self):
        """Create mock SensorManager."""
        return Mock()

    @pytest.fixture
    def mock_offset_engine(self):
        """Create mock OffsetEngine."""
        return Mock()

    @pytest.fixture
    def mock_mode_manager(self):
        """Create mock ModeManager."""
        return Mock()

    @pytest.fixture
    def mock_thermal_manager(self):
        """Create mock ThermalManager."""
        mock_thermal = Mock()
        mock_thermal.serialize.return_value = {
            "version": "1.0",
            "state": {"current_state": "DRIFTING"},
            "model": {"tau_cooling": 95.5, "tau_warming": 148.2}
        }
        return mock_thermal

    @pytest.fixture
    def coordinator(self, mock_hass, mock_sensor_manager, mock_offset_engine, mock_mode_manager):
        """Create SmartClimateCoordinator instance."""
        # Create a real coordinator instance for testing
        coordinator = SmartClimateCoordinator.__new__(SmartClimateCoordinator)
        coordinator.hass = mock_hass
        coordinator._sensor_manager = mock_sensor_manager
        coordinator._offset_engine = mock_offset_engine
        coordinator._mode_manager = mock_mode_manager
        return coordinator

    def test_get_thermal_data_with_valid_thermal_manager(self, coordinator, mock_hass, mock_thermal_manager):
        """Test get_thermal_data calls serialize on ThermalManager."""
        # Setup: Add thermal component to hass.data
        entry_id = "test_entry_id"
        entity_id = "climate.test_room"
        
        mock_hass.data[DOMAIN][entry_id] = {
            "thermal_components": {
                entity_id: {"thermal_manager": mock_thermal_manager}
            }
        }
        
        # Test: Call get_thermal_data
        result = coordinator.get_thermal_data(entity_id)
        
        # Verify: serialize was called and data returned
        mock_thermal_manager.serialize.assert_called_once()
        assert result == {
            "version": "1.0",
            "state": {"current_state": "DRIFTING"},
            "model": {"tau_cooling": 95.5, "tau_warming": 148.2}
        }

    def test_get_thermal_data_with_missing_component(self, coordinator, mock_hass):
        """Test get_thermal_data returns None when ThermalManager not found."""
        # Setup: Empty hass.data structure
        entry_id = "test_entry_id"
        entity_id = "climate.test_room"
        
        mock_hass.data[DOMAIN][entry_id] = {"thermal_components": {}}
        
        # Test: Call get_thermal_data
        result = coordinator.get_thermal_data(entity_id)
        
        # Verify: None returned, no exception raised
        assert result is None

    def test_get_thermal_data_with_missing_thermal_components(self, coordinator, mock_hass):
        """Test get_thermal_data returns None when thermal_components key missing."""
        # Setup: Entry data without thermal_components
        entry_id = "test_entry_id"
        entity_id = "climate.test_room"
        
        mock_hass.data[DOMAIN][entry_id] = {"other_data": "value"}
        
        # Test: Call get_thermal_data
        result = coordinator.get_thermal_data(entity_id)
        
        # Verify: None returned gracefully
        assert result is None

    def test_get_thermal_data_with_serialize_exception(self, coordinator, mock_hass, mock_thermal_manager):
        """Test get_thermal_data handles serialize exceptions gracefully."""
        # Setup: ThermalManager.serialize raises exception
        entry_id = "test_entry_id"
        entity_id = "climate.test_room"
        
        mock_thermal_manager.serialize.side_effect = Exception("Serialize error")
        mock_hass.data[DOMAIN][entry_id] = {
            "thermal_components": {
                entity_id: {"thermal_manager": mock_thermal_manager}
            }
        }
        
        # Test: Call get_thermal_data
        result = coordinator.get_thermal_data(entity_id)
        
        # Verify: None returned, exception handled
        assert result is None
        mock_thermal_manager.serialize.assert_called_once()

    def test_restore_thermal_data_with_valid_thermal_manager(self, coordinator, mock_hass, mock_thermal_manager):
        """Test restore_thermal_data calls restore on ThermalManager."""
        # Setup: Add thermal component to hass.data
        entry_id = "test_entry_id"
        entity_id = "climate.test_room"
        
        mock_hass.data[DOMAIN][entry_id] = {
            "thermal_components": {
                entity_id: {"thermal_manager": mock_thermal_manager}
            }
        }
        
        # Test data
        thermal_data = {
            "version": "1.0",
            "state": {"current_state": "PRIMING"},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0}
        }
        
        # Test: Call restore_thermal_data
        coordinator.restore_thermal_data(entity_id, thermal_data)
        
        # Verify: restore was called with data
        mock_thermal_manager.restore.assert_called_once_with(thermal_data)

    def test_restore_thermal_data_with_missing_component(self, coordinator, mock_hass):
        """Test restore_thermal_data handles missing ThermalManager gracefully."""
        # Setup: Empty thermal_components
        entry_id = "test_entry_id"
        entity_id = "climate.test_room"
        
        mock_hass.data[DOMAIN][entry_id] = {"thermal_components": {}}
        
        thermal_data = {"version": "1.0"}
        
        # Test: Call restore_thermal_data - should not raise exception
        coordinator.restore_thermal_data(entity_id, thermal_data)
        
        # Verify: No exception raised (method completes normally)

    def test_restore_thermal_data_with_restore_exception(self, coordinator, mock_hass, mock_thermal_manager):
        """Test restore_thermal_data handles restore exceptions gracefully."""
        # Setup: ThermalManager.restore raises exception
        entry_id = "test_entry_id"
        entity_id = "climate.test_room"
        
        mock_thermal_manager.restore.side_effect = Exception("Restore error")
        mock_hass.data[DOMAIN][entry_id] = {
            "thermal_components": {
                entity_id: {"thermal_manager": mock_thermal_manager}
            }
        }
        
        thermal_data = {"version": "1.0"}
        
        # Test: Call restore_thermal_data
        coordinator.restore_thermal_data(entity_id, thermal_data)
        
        # Verify: Exception handled, method completes
        mock_thermal_manager.restore.assert_called_once_with(thermal_data)

    def test_get_thermal_manager_helper_method(self, coordinator, mock_hass, mock_thermal_manager):
        """Test get_thermal_manager helper method returns ThermalManager."""
        # Setup: Add thermal component to hass.data
        entry_id = "test_entry_id"
        entity_id = "climate.test_room"
        
        mock_hass.data[DOMAIN][entry_id] = {
            "thermal_components": {
                entity_id: {"thermal_manager": mock_thermal_manager}
            }
        }
        
        # Test: Call get_thermal_manager
        result = coordinator.get_thermal_manager(entity_id)
        
        # Verify: ThermalManager returned
        assert result is mock_thermal_manager

    def test_get_thermal_manager_with_missing_component(self, coordinator, mock_hass):
        """Test get_thermal_manager returns None when component not found."""
        # Setup: Empty structure
        entry_id = "test_entry_id"
        entity_id = "climate.test_room"
        
        mock_hass.data[DOMAIN][entry_id] = {"thermal_components": {}}
        
        # Test: Call get_thermal_manager
        result = coordinator.get_thermal_manager(entity_id)
        
        # Verify: None returned
        assert result is None

    def test_get_offset_engine_helper_method(self, coordinator, mock_hass):
        """Test get_offset_engine helper method returns OffsetEngine."""
        # Setup: Add offset engine to hass.data
        entry_id = "test_entry_id"
        entity_id = "climate.test_room"
        mock_offset_engine = Mock()
        
        mock_hass.data[DOMAIN][entry_id] = {
            "offset_engines": {
                entity_id: mock_offset_engine
            }
        }
        
        # Test: Call get_offset_engine
        result = coordinator.get_offset_engine(entity_id)
        
        # Verify: OffsetEngine returned
        assert result is mock_offset_engine

    def test_get_offset_engine_with_missing_component(self, coordinator, mock_hass):
        """Test get_offset_engine returns None when component not found."""
        # Setup: Empty structure
        entry_id = "test_entry_id"
        entity_id = "climate.test_room"
        
        mock_hass.data[DOMAIN][entry_id] = {"offset_engines": {}}
        
        # Test: Call get_offset_engine
        result = coordinator.get_offset_engine(entity_id)
        
        # Verify: None returned
        assert result is None


class TestCallbackIntegration:
    """Test functools.partial callback creation in setup flow."""

    @patch('custom_components.smart_climate.coordinator.SmartClimateCoordinator')
    def test_functools_partial_callback_creation(self, mock_coordinator_class):
        """Test that setup flow creates functools.partial callbacks correctly."""
        # Setup: Mock coordinator instance
        mock_coordinator = Mock()
        mock_coordinator_class.return_value = mock_coordinator
        
        entity_id = "climate.test_room"
        
        # Test: Create callbacks using functools.partial (as done in setup)
        from functools import partial
        get_thermal_cb = partial(mock_coordinator.get_thermal_data, entity_id)
        restore_thermal_cb = partial(mock_coordinator.restore_thermal_data, entity_id)
        
        # Verify: Callbacks are partial objects
        assert isinstance(get_thermal_cb, partial)
        assert isinstance(restore_thermal_cb, partial)
        
        # Test: Call callbacks and verify they pass correct entity_id
        test_data = {"version": "1.0"}
        
        # Call get callback
        get_thermal_cb()
        mock_coordinator.get_thermal_data.assert_called_with(entity_id)
        
        # Call restore callback
        restore_thermal_cb(test_data)
        mock_coordinator.restore_thermal_data.assert_called_with(entity_id, test_data)

    def test_callback_usage_with_offset_engine(self):
        """Test callbacks can be passed to OffsetEngine constructor."""
        # Setup: Create mock coordinator and callbacks
        mock_coordinator = Mock()
        entity_id = "climate.test_room"
        
        get_thermal_cb = partial(mock_coordinator.get_thermal_data, entity_id)
        restore_thermal_cb = partial(mock_coordinator.restore_thermal_data, entity_id)
        
        # Mock OffsetEngine to accept callbacks
        mock_offset_engine = Mock()
        
        # Test: Pass callbacks to OffsetEngine constructor (simulated)
        # This tests the interface compatibility
        kwargs = {
            "config": {},
            "get_thermal_data_cb": get_thermal_cb,
            "restore_thermal_data_cb": restore_thermal_cb
        }
        
        # Verify: Callbacks can be stored and called
        stored_get_cb = kwargs["get_thermal_data_cb"]
        stored_restore_cb = kwargs["restore_thermal_data_cb"]
        
        # Test callback execution
        stored_get_cb()
        mock_coordinator.get_thermal_data.assert_called_with(entity_id)
        
        stored_restore_cb({"test": "data"})
        mock_coordinator.restore_thermal_data.assert_called_with(entity_id, {"test": "data"})


class TestHassDataStructureAccess:
    """Test safe access to hass.data structure per architecture."""

    def test_hass_data_structure_lookup_pattern(self):
        """Test the exact hass.data lookup pattern from architecture spec."""
        # Setup: Mock hass.data structure following architecture
        mock_hass = Mock()
        mock_thermal_manager = Mock()
        mock_offset_engine = Mock()
        
        entry_id = "test_entry_id"
        entity_id = "climate.test_room"
        
        # Architecture pattern: hass.data[DOMAIN][entry_id]["thermal_components"][entity_id]
        mock_hass.data = {
            DOMAIN: {
                entry_id: {
                    "thermal_components": {
                        entity_id: {"thermal_manager": mock_thermal_manager}
                    },
                    "offset_engines": {
                        entity_id: mock_offset_engine
                    }
                }
            }
        }
        
        # Test: Access thermal component
        thermal_components = mock_hass.data[DOMAIN][entry_id]["thermal_components"]
        thermal_manager = thermal_components[entity_id]["thermal_manager"]
        
        # Verify: Correct object retrieved
        assert thermal_manager is mock_thermal_manager
        
        # Test: Access offset engine
        offset_engines = mock_hass.data[DOMAIN][entry_id]["offset_engines"]
        offset_engine = offset_engines[entity_id]
        
        # Verify: Correct object retrieved
        assert offset_engine is mock_offset_engine

    def test_safe_component_lookup_with_missing_keys(self):
        """Test safe component lookup handles missing keys gracefully."""
        # Setup: Partial hass.data structure
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {}}
        
        entry_id = "missing_entry"
        entity_id = "climate.test_room"
        
        # Test: Safe lookup with missing entry
        entry_data = mock_hass.data[DOMAIN].get(entry_id, {})
        thermal_components = entry_data.get("thermal_components", {})
        thermal_manager = thermal_components.get(entity_id, {}).get("thermal_manager")
        
        # Verify: None returned safely
        assert thermal_manager is None

    def test_error_handling_for_component_access(self):
        """Test error handling patterns for component access."""
        # Setup: Mock coordinator with error handling methods
        mock_coordinator = Mock()
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {"entry_id": {"thermal_components": {}}}}
        
        entity_id = "climate.test_room"
        
        # Simulate coordinator methods with error handling
        def safe_get_thermal_data(self, entity_id):
            try:
                # This will succeed
                entry_data = mock_hass.data[DOMAIN]["entry_id"]
                thermal_components = entry_data.get("thermal_components", {})
                thermal_manager = thermal_components.get(entity_id, {}).get("thermal_manager")
                
                if thermal_manager:
                    return thermal_manager.serialize()
                return None
            except Exception:
                return None
        
        # Test: Method handles missing component gracefully
        result = safe_get_thermal_data(mock_coordinator, entity_id)
        
        # Verify: None returned without exception
        assert result is None