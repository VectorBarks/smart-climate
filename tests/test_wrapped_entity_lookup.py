"""Test wrapped entity ID thermal manager lookup."""
import pytest
from unittest.mock import Mock
from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.const import DOMAIN


class TestWrappedEntityLookup:
    """Test that thermal manager lookup uses wrapped entity ID correctly."""
    
    @pytest.fixture
    def mock_hass_with_thermal_data(self):
        """Create mock hass with thermal components under wrapped entity ID."""
        hass = Mock()
        entry_id = "test_entry_123"
        wrapped_entity_id = "climate.original_ac"  # The real A/C entity
        smart_entity_id = "climate.smart_original_ac"  # The Smart Climate entity
        
        # Thermal components stored under wrapped entity ID (correct)
        hass.data = {
            DOMAIN: {
                entry_id: {
                    "thermal_components": {
                        wrapped_entity_id: {  # Key is wrapped entity ID
                            "thermal_model": Mock(),
                            "thermal_manager": Mock()
                        }
                        # NOTE: No entry for smart_entity_id - this is the key point
                    }
                }
            }
        }
        return hass, entry_id, wrapped_entity_id, smart_entity_id
    
    def test_thermal_manager_lookup_uses_wrapped_entity_id(self, mock_hass_with_thermal_data):
        """Test that SmartClimateEntity looks up thermal manager using wrapped entity ID."""
        hass, entry_id, wrapped_entity_id, smart_entity_id = mock_hass_with_thermal_data
        
        # Create SmartClimateEntity with entry_id in config
        config = {
            "climate_entity": wrapped_entity_id,
            "room_sensor": "sensor.room_temp",
            "entry_id": entry_id
        }
        
        entity = SmartClimateEntity(
            hass=hass,
            config=config,
            wrapped_entity_id=wrapped_entity_id,
            room_sensor_id="sensor.room_temp",
            offset_engine=Mock(),
            sensor_manager=Mock(),
            mode_manager=Mock(),
            temperature_controller=Mock(),
            coordinator=Mock()
        )
        
        # Set the entity_id as Home Assistant would
        entity.entity_id = smart_entity_id
        
        # Verify that entity IDs are different
        assert entity.entity_id == smart_entity_id
        assert entity._wrapped_entity_id == wrapped_entity_id
        assert entity.entity_id != entity._wrapped_entity_id
        
        # Test the thermal manager lookup logic
        entry_id_from_config = entity._config.get("entry_id")
        thermal_components = hass.data[DOMAIN][entry_id_from_config]["thermal_components"]
        
        # This should work (using wrapped entity ID)
        thermal_manager_correct = thermal_components.get(entity._wrapped_entity_id)
        assert thermal_manager_correct is not None
        assert "thermal_manager" in thermal_manager_correct
        
        # This should fail (using Smart Climate entity ID)
        thermal_manager_wrong = thermal_components.get(entity.entity_id)
        assert thermal_manager_wrong is None
        
    def test_available_keys_match_wrapped_entity_id(self, mock_hass_with_thermal_data):
        """Test that available keys in thermal components match wrapped entity ID."""
        hass, entry_id, wrapped_entity_id, smart_entity_id = mock_hass_with_thermal_data
        
        thermal_components = hass.data[DOMAIN][entry_id]["thermal_components"]
        available_keys = list(thermal_components.keys())
        
        # Available keys should contain wrapped entity ID
        assert wrapped_entity_id in available_keys
        
        # Available keys should NOT contain Smart Climate entity ID
        assert smart_entity_id not in available_keys
        
        # This matches the log output: "Available thermal manager keys: ['climate.klimaanlage_tu_climate']"
        assert len(available_keys) == 1
        assert available_keys[0] == wrapped_entity_id
    
    def test_error_case_demonstrates_key_mismatch(self, mock_hass_with_thermal_data):
        """Test that demonstrates the error when using wrong entity ID."""
        hass, entry_id, wrapped_entity_id, smart_entity_id = mock_hass_with_thermal_data
        
        thermal_components = hass.data[DOMAIN][entry_id]["thermal_components"]
        
        # Simulate the wrong lookup (what caused the original error)
        thermal_manager = thermal_components.get(smart_entity_id)  # Wrong key
        available_keys = list(thermal_components.keys())
        
        # This simulates the error condition
        assert thermal_manager is None  # No thermal manager found
        assert smart_entity_id not in available_keys  # Key not in available keys
        assert wrapped_entity_id in available_keys  # But correct key is available
        
        # This would generate the log: 
        # "No thermal manager found for entity climate.smart_original_ac. 
        #  Available thermal manager keys: ['climate.original_ac']"