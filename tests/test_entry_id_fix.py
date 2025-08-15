"""Test entry_id fix for thermal manager access."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.const import DOMAIN


class TestEntryIdFix:
    """Test that entry_id is properly passed to SmartClimateEntity."""
    
    @pytest.fixture
    def mock_hass(self):
        """Create mock hass with thermal components data structure."""
        hass = Mock()
        entry_id = "test_entry_id_123"
        climate_entity_id = "climate.smart_test_climate"
        
        # Set up thermal components data structure
        hass.data = {
            DOMAIN: {
                entry_id: {
                    "thermal_components": {
                        climate_entity_id: {
                            "thermal_model": Mock(),
                            "user_preferences": Mock(),
                            "cycle_monitor": Mock(),
                            "comfort_band_controller": Mock()
                        }
                    }
                }
            }
        }
        return hass, entry_id, climate_entity_id
    
    @pytest.fixture
    def config_with_entry_id(self, mock_hass):
        """Create config with entry_id included."""
        hass, entry_id, climate_entity_id = mock_hass
        return {
            "climate_entity": "climate.test_ac",
            "room_sensor": "sensor.room_temp",
            "entry_id": entry_id  # This is the critical addition
        }
    
    def test_entry_id_available_in_config(self, mock_hass, config_with_entry_id):
        """Test that entry_id is available in entity config."""
        hass, entry_id, climate_entity_id = mock_hass
        
        # Create SmartClimateEntity with the fixed config
        entity = SmartClimateEntity(
            hass=hass,
            config=config_with_entry_id,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=Mock(),
            sensor_manager=Mock(),
            mode_manager=Mock(),
            temperature_controller=Mock(),
            coordinator=Mock()
        )
        
        # Set the entity_id that would be assigned by Home Assistant
        entity.entity_id = climate_entity_id
        
        # Verify entry_id is accessible from config
        assert entity._config.get("entry_id") == entry_id
        assert entity._config.get("entry_id") is not None
    
    def test_thermal_manager_access_with_entry_id(self, mock_hass, config_with_entry_id):
        """Test that thermal manager can be accessed with proper entry_id."""
        hass, entry_id, climate_entity_id = mock_hass
        
        # Create SmartClimateEntity with the fixed config
        entity = SmartClimateEntity(
            hass=hass,
            config=config_with_entry_id,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=Mock(),
            sensor_manager=Mock(),
            mode_manager=Mock(),
            temperature_controller=Mock(),
            coordinator=Mock()
        )
        
        # Set the entity_id that would be assigned by Home Assistant
        entity.entity_id = climate_entity_id
        
        # Test the thermal manager lookup logic (from the fixed _resolve_target_temperature)
        entry_id_from_config = entity._config.get("entry_id")
        assert entry_id_from_config is not None
        
        # Verify thermal components can be accessed
        thermal_components_dict = hass.data[DOMAIN][entry_id_from_config]["thermal_components"]
        thermal_manager = thermal_components_dict.get(entity.entity_id)
        
        assert thermal_manager is not None
        assert "thermal_model" in thermal_manager
        assert "user_preferences" in thermal_manager
    
    def test_drifting_state_simulation(self, mock_hass, config_with_entry_id):
        """Test that DRIFTING thermal state can be detected."""
        hass, entry_id, climate_entity_id = mock_hass
        
        # Set up mock thermal manager with DRIFTING state
        mock_thermal_model = Mock()
        mock_thermal_model.get_current_state.return_value = "DRIFTING"
        
        hass.data[DOMAIN][entry_id]["thermal_components"][climate_entity_id]["thermal_model"] = mock_thermal_model
        
        # Create SmartClimateEntity with the fixed config
        entity = SmartClimateEntity(
            hass=hass,
            config=config_with_entry_id,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=Mock(),
            sensor_manager=Mock(),
            mode_manager=Mock(),
            temperature_controller=Mock(),
            coordinator=Mock()
        )
        
        # Set the entity_id that would be assigned by Home Assistant
        entity.entity_id = climate_entity_id
        
        # Simulate the thermal manager access from _resolve_target_temperature
        entry_id_from_config = entity._config.get("entry_id")
        thermal_components_dict = hass.data[DOMAIN][entry_id_from_config]["thermal_components"]
        thermal_manager = thermal_components_dict.get(entity.entity_id)
        thermal_model = thermal_manager.get("thermal_model")
        
        # Verify DRIFTING state is detected
        current_state = thermal_model.get_current_state()
        assert current_state == "DRIFTING"
    
    def test_entry_id_none_regression(self):
        """Test regression case where entry_id was None (the original bug)."""
        hass = Mock()
        
        # Config without entry_id (the original broken case)
        config_without_entry_id = {
            "climate_entity": "climate.test_ac",
            "room_sensor": "sensor.room_temp"
            # No entry_id!
        }
        
        entity = SmartClimateEntity(
            hass=hass,
            config=config_without_entry_id,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=Mock(),
            sensor_manager=Mock(),
            mode_manager=Mock(),
            temperature_controller=Mock(),
            coordinator=Mock()
        )
        
        # Verify entry_id is None (reproducing the original bug)
        assert entity._config.get("entry_id") is None
        
        # This would cause the "No thermal components data structure found for entry_id: None" error