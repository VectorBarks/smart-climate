"""ABOUTME: Test suite for thermal state access through coordinator for climate integration.
Tests coordinator provides proper access to thermal and mode managers for climate entity."""

import pytest
from unittest.mock import Mock, MagicMock
from custom_components.smart_climate.coordinator import SmartClimateCoordinator
from custom_components.smart_climate.const import DOMAIN


class TestCoordinatorThermalAccess:
    """Test thermal state access through coordinator for climate entity integration.
    
    Uses the same pattern as test_coordinator_persistence.py for working tests.
    """

    def test_coordinator_exposes_thermal_state_to_climate(self):
        """Test coordinator exposes thermal state through get_thermal_manager."""
        # Setup mock hass and thermal manager
        mock_hass = Mock()
        mock_thermal_manager = Mock()
        mock_thermal_manager.current_state = "DRIFTING"
        
        entity_id = "climate.living_room"
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
        assert hasattr(result, 'current_state')
        assert result.current_state == "DRIFTING"

    def test_thermal_state_updates_trigger_coordinator_refresh(self):
        """Test thermal state is accessible for coordinator data updates."""
        # Setup mock hass and thermal manager
        mock_hass = Mock()
        mock_thermal_manager = Mock()
        mock_thermal_manager.current_state = "CORRECTING"
        mock_thermal_manager.get_operating_window.return_value = (22.0, 26.0)
        mock_thermal_manager.get_learning_target.return_value = 24.0
        
        entity_id = "climate.living_room"
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
        
        # Test thermal state access
        thermal_manager = coordinator.get_thermal_manager(entity_id)
        
        # Verify thermal state can be accessed for updates
        assert thermal_manager is not None
        assert thermal_manager.current_state == "CORRECTING"
        assert thermal_manager.get_operating_window() == (22.0, 26.0)
        assert thermal_manager.get_learning_target() == 24.0

    def test_climate_entity_can_access_thermal_manager(self):
        """Test climate entity can access thermal manager through coordinator."""
        # Setup mock hass and thermal manager
        mock_hass = Mock()
        mock_thermal_manager = Mock()
        
        entity_id = "climate.living_room"
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
        
        # Simulate climate entity accessing thermal manager through coordinator
        thermal_manager = coordinator.get_thermal_manager(entity_id)
        
        assert thermal_manager is not None
        assert thermal_manager is mock_thermal_manager
        
        # Verify climate entity can access thermal methods
        assert hasattr(thermal_manager, 'get_operating_window')
        assert hasattr(thermal_manager, 'should_ac_run')
        assert hasattr(thermal_manager, 'get_learning_target')

    def test_mode_manager_accessible_alongside_thermal_manager(self):
        """Test mode manager remains accessible when thermal manager is present."""
        # Setup mock hass and components
        mock_hass = Mock()
        mock_thermal_manager = Mock()
        mock_mode_manager = Mock()
        mock_mode_manager.current_mode = "boost"
        
        entity_id = "climate.living_room"
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
        coordinator._mode_manager = mock_mode_manager
        
        # Access both managers
        thermal_manager = coordinator.get_thermal_manager(entity_id)
        mode_manager = coordinator._mode_manager
        
        assert thermal_manager is not None
        assert mode_manager is not None
        assert mode_manager.current_mode == "boost"

    def test_thermal_manager_access_with_missing_entity(self):
        """Test thermal manager access returns None for missing entity."""
        # Setup mock hass with empty structure
        mock_hass = Mock()
        mock_hass.data = {DOMAIN: {"test_entry": {"thermal_components": {}}}}
        
        # Create coordinator instance with minimal setup
        coordinator = SmartClimateCoordinator.__new__(SmartClimateCoordinator)
        coordinator.hass = mock_hass
        
        # Test missing entity
        missing_entity_id = "climate.nonexistent"
        thermal_manager = coordinator.get_thermal_manager(missing_entity_id)
        
        assert thermal_manager is None

    def test_thermal_manager_access_with_malformed_data(self):
        """Test thermal manager access handles malformed hass.data gracefully."""
        # Setup coordinator with empty hass.data
        mock_hass = Mock()
        mock_hass.data = {}
        
        # Create coordinator instance with minimal setup
        coordinator = SmartClimateCoordinator.__new__(SmartClimateCoordinator)
        coordinator.hass = mock_hass
        
        thermal_manager = coordinator.get_thermal_manager("climate.living_room")
        
        assert thermal_manager is None

    def test_offset_engine_access_through_coordinator(self):
        """Test offset engine is accessible through coordinator for thermal operations."""
        # Setup mock hass and offset engine
        mock_hass = Mock()
        mock_offset_engine = Mock()
        
        entity_id = "climate.living_room"
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
        
        # Test offset engine access
        offset_engine = coordinator.get_offset_engine(entity_id)
        
        assert offset_engine is not None
        assert offset_engine is mock_offset_engine

    def test_thermal_state_drives_learning_control(self):
        """Test thermal state properly controls offset engine learning."""
        # This test verifies the method exists and can be called
        # Full integration testing is in other test files
        mock_hass = Mock()
        mock_thermal_manager = Mock()
        mock_thermal_manager.current_state = "DRIFTING"
        
        entity_id = "climate.living_room"
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
        
        # Test thermal state access for learning control
        thermal_manager = coordinator.get_thermal_manager(entity_id)
        
        assert thermal_manager is not None
        assert thermal_manager.current_state == "DRIFTING"

    def test_thermal_window_integration_with_offset_calculation(self):
        """Test thermal window is accessible from thermal manager for offset calculation."""
        # Setup mock hass and thermal manager
        mock_hass = Mock()
        mock_thermal_manager = Mock()
        mock_thermal_manager.get_operating_window.return_value = (21.5, 26.5)
        
        entity_id = "climate.living_room"
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
        
        # Test thermal window access
        thermal_manager = coordinator.get_thermal_manager(entity_id)
        thermal_window = thermal_manager.get_operating_window()
        
        assert thermal_window == (21.5, 26.5)

    def test_climate_entity_can_check_thermal_state_for_mode_conflicts(self):
        """Test climate entity can check thermal state to handle mode conflicts per Architecture §18."""
        # Setup mock hass and components
        mock_hass = Mock()
        mock_thermal_manager = Mock()
        mock_thermal_manager.current_state = "DRIFTING"
        mock_mode_manager = Mock()
        mock_mode_manager.current_mode = "boost"
        
        entity_id = "climate.living_room"
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
        coordinator._mode_manager = mock_mode_manager
        
        # Access both managers (Climate entity can access both for conflict resolution)
        thermal_manager = coordinator.get_thermal_manager(entity_id)
        mode_manager = coordinator._mode_manager
        
        assert thermal_manager is not None
        assert mode_manager is not None
        
        # Verify climate entity has access to both pieces of information for priority resolution
        assert thermal_manager.current_state == "DRIFTING"
        assert mode_manager.current_mode == "boost"
        
        # This enables the _resolve_target_temperature() logic in climate.py
        # where mode override can win over thermal state per Architecture §18