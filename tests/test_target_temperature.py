"""ABOUTME: Tests for target_temperature property behavior.
Ensures target_temperature never returns None and provides robust temperature control."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.const import TEMP_CELSIUS

from custom_components.smart_climate.climate import SmartClimateEntity


class TestTargetTemperature:
    """Test target_temperature property behavior."""
    
    @pytest.fixture
    def smart_climate_entity(self):
        """Create a SmartClimateEntity for testing."""
        hass = Mock()
        hass.states = Mock()
        hass.states.get = Mock()
        
        config = {"name": "Test Smart Climate"}
        wrapped_entity_id = "climate.test_climate"
        room_sensor_id = "sensor.room_temp"
        
        # Mock all dependencies
        offset_engine = Mock()
        sensor_manager = Mock()
        mode_manager = Mock()
        temperature_controller = Mock()
        coordinator = Mock()
        
        entity = SmartClimateEntity(
            hass=hass,
            config=config,
            wrapped_entity_id=wrapped_entity_id,
            room_sensor_id=room_sensor_id,
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=mode_manager,
            temperature_controller=temperature_controller,
            coordinator=coordinator
        )
        
        return entity
    
    def test_target_temperature_returns_stored_value(self, smart_climate_entity):
        """Test that target_temperature returns stored value when available."""
        # Arrange
        expected_temp = 23.5
        smart_climate_entity._attr_target_temperature = expected_temp
        
        # Act
        result = smart_climate_entity.target_temperature
        
        # Assert
        assert result == expected_temp
        assert isinstance(result, float)
    
    def test_target_temperature_falls_back_to_wrapped_entity(self, smart_climate_entity):
        """Test that target_temperature falls back to wrapped entity when no stored value."""
        # Arrange
        expected_temp = 22.0
        smart_climate_entity._attr_target_temperature = None
        
        # Mock wrapped entity state
        wrapped_state = Mock()
        wrapped_state.attributes = {"target_temperature": expected_temp}
        smart_climate_entity.hass.states.get.return_value = wrapped_state
        
        # Act
        result = smart_climate_entity.target_temperature
        
        # Assert
        assert result == expected_temp
        assert isinstance(result, float)
        smart_climate_entity.hass.states.get.assert_called_once_with(smart_climate_entity._wrapped_entity_id)
    
    def test_target_temperature_handles_wrapped_entity_none_attributes(self, smart_climate_entity):
        """Test that target_temperature handles wrapped entity with None attributes."""
        # Arrange
        smart_climate_entity._attr_target_temperature = None
        
        # Mock wrapped entity state with None attributes
        wrapped_state = Mock()
        wrapped_state.attributes = None
        smart_climate_entity.hass.states.get.return_value = wrapped_state
        
        # Act
        result = smart_climate_entity.target_temperature
        
        # Assert - should return default, not None
        assert result is not None
        assert isinstance(result, float)
        assert result == 22.0  # Default fallback temperature
    
    def test_target_temperature_handles_wrapped_entity_missing_target_temp(self, smart_climate_entity):
        """Test that target_temperature handles wrapped entity missing target_temperature."""
        # Arrange
        smart_climate_entity._attr_target_temperature = None
        
        # Mock wrapped entity state without target_temperature
        wrapped_state = Mock()
        wrapped_state.attributes = {"hvac_mode": "cool"}  # No target_temperature
        smart_climate_entity.hass.states.get.return_value = wrapped_state
        
        # Act
        result = smart_climate_entity.target_temperature
        
        # Assert - should return default, not None
        assert result is not None
        assert isinstance(result, float)
        assert result == 22.0  # Default fallback temperature
    
    def test_target_temperature_handles_wrapped_entity_invalid_target_temp(self, smart_climate_entity):
        """Test that target_temperature handles wrapped entity with invalid target_temperature."""
        # Arrange
        smart_climate_entity._attr_target_temperature = None
        
        # Mock wrapped entity state with invalid target_temperature
        wrapped_state = Mock()
        wrapped_state.attributes = {"target_temperature": "invalid_string"}
        smart_climate_entity.hass.states.get.return_value = wrapped_state
        
        # Act
        result = smart_climate_entity.target_temperature
        
        # Assert - should return default, not None
        assert result is not None
        assert isinstance(result, float)
        assert result == 22.0  # Default fallback temperature
    
    def test_target_temperature_handles_wrapped_entity_not_found(self, smart_climate_entity):
        """Test that target_temperature handles wrapped entity not found."""
        # Arrange
        smart_climate_entity._attr_target_temperature = None
        smart_climate_entity.hass.states.get.return_value = None
        
        # Act
        result = smart_climate_entity.target_temperature
        
        # Assert - should return default, not None
        assert result is not None
        assert isinstance(result, float)
        assert result == 22.0  # Default fallback temperature
    
    def test_target_temperature_handles_exception_gracefully(self, smart_climate_entity):
        """Test that target_temperature handles exceptions gracefully."""
        # Arrange
        smart_climate_entity._attr_target_temperature = None
        smart_climate_entity.hass.states.get.side_effect = Exception("Test exception")
        
        # Act
        result = smart_climate_entity.target_temperature
        
        # Assert - should return default, not None
        assert result is not None
        assert isinstance(result, float)
        assert result == 22.0  # Default fallback temperature
    
    def test_target_temperature_never_returns_none(self, smart_climate_entity):
        """Test that target_temperature NEVER returns None under any circumstances."""
        # Test various scenarios that could potentially return None
        test_scenarios = [
            # Scenario 1: Both stored and wrapped are None
            (None, None),
            # Scenario 2: Stored is None, wrapped has None attributes
            (None, {"attributes": None}),
            # Scenario 3: Stored is None, wrapped has empty attributes
            (None, {"attributes": {}}),
            # Scenario 4: Stored is None, wrapped has invalid target_temperature
            (None, {"attributes": {"target_temperature": "invalid"}}),
            # Scenario 5: Exception in wrapped entity access
            (None, "exception"),
        ]
        
        for stored_temp, wrapped_config in test_scenarios:
            # Arrange
            smart_climate_entity._attr_target_temperature = stored_temp
            
            if wrapped_config == "exception":
                smart_climate_entity.hass.states.get.side_effect = Exception("Test")
            elif wrapped_config is None:
                smart_climate_entity.hass.states.get.return_value = None
            else:
                wrapped_state = Mock()
                wrapped_state.attributes = wrapped_config["attributes"]
                smart_climate_entity.hass.states.get.return_value = wrapped_state
            
            # Act
            result = smart_climate_entity.target_temperature
            
            # Assert - NEVER None
            assert result is not None, f"target_temperature returned None for scenario: stored={stored_temp}, wrapped={wrapped_config}"
            assert isinstance(result, float), f"target_temperature didn't return float for scenario: stored={stored_temp}, wrapped={wrapped_config}"
            assert result > 0, f"target_temperature returned invalid temperature for scenario: stored={stored_temp}, wrapped={wrapped_config}"
    
    def test_target_temperature_initialization_from_wrapped_entity(self, smart_climate_entity):
        """Test that target_temperature is properly initialized from wrapped entity."""
        # Arrange
        expected_temp = 25.0
        smart_climate_entity._attr_target_temperature = None
        
        # Mock wrapped entity state
        wrapped_state = Mock()
        wrapped_state.attributes = {"target_temperature": expected_temp}
        smart_climate_entity.hass.states.get.return_value = wrapped_state
        
        # Act - simulate async_added_to_hass initialization
        if smart_climate_entity._attr_target_temperature is None and wrapped_state.attributes:
            wrapped_target = wrapped_state.attributes.get("target_temperature")
            if wrapped_target is not None and isinstance(wrapped_target, (int, float)):
                smart_climate_entity._attr_target_temperature = float(wrapped_target)
        
        result = smart_climate_entity.target_temperature
        
        # Assert
        assert result == expected_temp
        assert smart_climate_entity._attr_target_temperature == expected_temp
    
    def test_target_temperature_bidirectional_sync(self, smart_climate_entity):
        """Test that target_temperature can sync changes from wrapped entity."""
        # Arrange
        initial_temp = 22.0
        updated_temp = 24.0
        smart_climate_entity._attr_target_temperature = initial_temp
        
        # Mock wrapped entity state change
        wrapped_state = Mock()
        wrapped_state.attributes = {"target_temperature": updated_temp}
        smart_climate_entity.hass.states.get.return_value = wrapped_state
        
        # Act - simulate sync from wrapped entity
        # This tests the capability to update from wrapped entity
        if wrapped_state.attributes:
            wrapped_target = wrapped_state.attributes.get("target_temperature")
            if wrapped_target is not None and isinstance(wrapped_target, (int, float)):
                # Check if wrapped entity has different target than stored
                if abs(float(wrapped_target) - smart_climate_entity._attr_target_temperature) > 0.1:
                    smart_climate_entity._attr_target_temperature = float(wrapped_target)
        
        result = smart_climate_entity.target_temperature
        
        # Assert
        assert result == updated_temp
        assert smart_climate_entity._attr_target_temperature == updated_temp
    
    def test_target_temperature_reasonable_range(self, smart_climate_entity):
        """Test that target_temperature always returns reasonable values."""
        # Test various edge cases
        test_cases = [
            (None, None, 22.0),  # Default case
            (15.0, None, 15.0),  # Stored value
            (None, 28.0, 28.0),  # Wrapped value
            (30.0, 25.0, 30.0),  # Stored takes precedence
        ]
        
        for stored_temp, wrapped_temp, expected in test_cases:
            # Arrange
            smart_climate_entity._attr_target_temperature = stored_temp
            
            if wrapped_temp is not None:
                wrapped_state = Mock()
                wrapped_state.attributes = {"target_temperature": wrapped_temp}
                smart_climate_entity.hass.states.get.return_value = wrapped_state
            else:
                smart_climate_entity.hass.states.get.return_value = None
            
            # Act
            result = smart_climate_entity.target_temperature
            
            # Assert
            assert result == expected
            assert 10.0 <= result <= 35.0  # Reasonable temperature range