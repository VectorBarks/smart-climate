"""Tests for SmartClimateEntity."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode, ClimateEntityFeature
)
from homeassistant.const import STATE_ON, STATE_OFF

from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.models import OffsetResult
from tests.fixtures.mock_entities import (
    create_mock_hass,
    create_mock_state,
    create_mock_offset_engine,
    create_mock_sensor_manager,
    create_mock_mode_manager,
    create_mock_temperature_controller,
    create_mock_coordinator,
    MockClimateEntity
)


class TestSmartClimateEntity:
    """Test SmartClimateEntity class."""

    def test_entity_inherits_from_climate_entity(self):
        """Test that SmartClimateEntity inherits from ClimateEntity."""
        # Arrange
        mock_hass = create_mock_hass()
        config = {"name": "Test Smart Climate"}
        
        # Create mock dependencies
        mock_offset_engine = create_mock_offset_engine()
        mock_sensor_manager = create_mock_sensor_manager()
        mock_mode_manager = create_mock_mode_manager()
        mock_temperature_controller = create_mock_temperature_controller()
        mock_coordinator = create_mock_coordinator()
        
        # Act
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=config,
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room_temp",
            offset_engine=mock_offset_engine,
            sensor_manager=mock_sensor_manager,
            mode_manager=mock_mode_manager,
            temperature_controller=mock_temperature_controller,
            coordinator=mock_coordinator
        )
        
        # Assert
        assert isinstance(entity, ClimateEntity)

    def test_unique_id_based_on_wrapped_entity(self):
        """Test that unique_id is based on wrapped entity."""
        # Arrange
        mock_hass = create_mock_hass()
        config = {"name": "Test Smart Climate"}
        wrapped_entity_id = "climate.test_ac"
        
        # Create mock dependencies
        mock_offset_engine = create_mock_offset_engine()
        mock_sensor_manager = create_mock_sensor_manager()
        mock_mode_manager = create_mock_mode_manager()
        mock_temperature_controller = create_mock_temperature_controller()
        mock_coordinator = create_mock_coordinator()
        
        # Act
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=config,
            wrapped_entity_id=wrapped_entity_id,
            room_sensor_id="sensor.room_temp",
            offset_engine=mock_offset_engine,
            sensor_manager=mock_sensor_manager,
            mode_manager=mock_mode_manager,
            temperature_controller=mock_temperature_controller,
            coordinator=mock_coordinator
        )
        
        # Assert
        assert entity.unique_id == "smart_climate.test_ac"

    def test_name_includes_smart_prefix(self):
        """Test that name includes 'Smart' prefix."""
        # Arrange
        mock_hass = create_mock_hass()
        config = {"name": "Test Smart Climate"}
        
        # Mock the wrapped entity state with attributes
        wrapped_state = create_mock_state(
            "climate.test_ac", 
            STATE_OFF, 
            {"friendly_name": "Test AC"}
        )
        mock_hass.states.get.return_value = wrapped_state
        
        # Create mock dependencies
        mock_offset_engine = create_mock_offset_engine()
        mock_sensor_manager = create_mock_sensor_manager()
        mock_mode_manager = create_mock_mode_manager()
        mock_temperature_controller = create_mock_temperature_controller()
        mock_coordinator = create_mock_coordinator()
        
        # Act
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=mock_offset_engine,
            sensor_manager=mock_sensor_manager,
            mode_manager=mock_mode_manager,
            temperature_controller=mock_temperature_controller,
            coordinator=mock_coordinator
        )
        
        # Assert
        assert "Smart" in entity.name

    def test_supported_features_forwarded_from_wrapped(self):
        """Test that supported_features are forwarded from wrapped entity."""
        # Arrange
        mock_hass = create_mock_hass()
        config = {"name": "Test Smart Climate"}
        
        # Mock the wrapped entity state with features
        wrapped_state = create_mock_state(
            "climate.test_ac", 
            STATE_OFF, 
            {"supported_features": ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE}
        )
        mock_hass.states.get.return_value = wrapped_state
        
        # Create mock dependencies
        mock_offset_engine = create_mock_offset_engine()
        mock_sensor_manager = create_mock_sensor_manager()
        mock_mode_manager = create_mock_mode_manager()
        mock_temperature_controller = create_mock_temperature_controller()
        mock_coordinator = create_mock_coordinator()
        
        # Act
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=mock_offset_engine,
            sensor_manager=mock_sensor_manager,
            mode_manager=mock_mode_manager,
            temperature_controller=mock_temperature_controller,
            coordinator=mock_coordinator
        )
        
        # Assert
        assert entity.supported_features == (ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE)

    def test_hvac_mode_forwarded_from_wrapped(self):
        """Test that hvac_mode is forwarded from wrapped entity."""
        # Arrange
        mock_hass = create_mock_hass()
        config = {"name": "Test Smart Climate"}
        
        # Mock the wrapped entity state
        wrapped_state = create_mock_state("climate.test_ac", HVACMode.COOL)
        mock_hass.states.get.return_value = wrapped_state
        
        # Create mock dependencies
        mock_offset_engine = create_mock_offset_engine()
        mock_sensor_manager = create_mock_sensor_manager()
        mock_mode_manager = create_mock_mode_manager()
        mock_temperature_controller = create_mock_temperature_controller()
        mock_coordinator = create_mock_coordinator()
        
        # Act
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=mock_offset_engine,
            sensor_manager=mock_sensor_manager,
            mode_manager=mock_mode_manager,
            temperature_controller=mock_temperature_controller,
            coordinator=mock_coordinator
        )
        
        # Assert
        assert entity.hvac_mode == HVACMode.COOL

    def test_hvac_modes_forwarded_from_wrapped(self):
        """Test that hvac_modes are forwarded from wrapped entity."""
        # Arrange
        mock_hass = create_mock_hass()
        config = {"name": "Test Smart Climate"}
        
        # Mock the wrapped entity state with hvac_modes
        wrapped_state = create_mock_state(
            "climate.test_ac", 
            HVACMode.COOL, 
            {"hvac_modes": [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT]}
        )
        mock_hass.states.get.return_value = wrapped_state
        
        # Create mock dependencies
        mock_offset_engine = create_mock_offset_engine()
        mock_sensor_manager = create_mock_sensor_manager()
        mock_mode_manager = create_mock_mode_manager()
        mock_temperature_controller = create_mock_temperature_controller()
        mock_coordinator = create_mock_coordinator()
        
        # Act
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=mock_offset_engine,
            sensor_manager=mock_sensor_manager,
            mode_manager=mock_mode_manager,
            temperature_controller=mock_temperature_controller,
            coordinator=mock_coordinator
        )
        
        # Assert
        assert entity.hvac_modes == [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT]

    def test_current_temperature_returns_room_sensor_value(self):
        """Test that current_temperature returns room sensor value."""
        # Arrange
        mock_hass = create_mock_hass()
        config = {"name": "Test Smart Climate"}
        
        # Create mock dependencies
        mock_offset_engine = create_mock_offset_engine()
        mock_sensor_manager = create_mock_sensor_manager()
        mock_sensor_manager.get_room_temperature.return_value = 23.5
        mock_mode_manager = create_mock_mode_manager()
        mock_temperature_controller = create_mock_temperature_controller()
        mock_coordinator = create_mock_coordinator()
        
        # Act
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=mock_offset_engine,
            sensor_manager=mock_sensor_manager,
            mode_manager=mock_mode_manager,
            temperature_controller=mock_temperature_controller,
            coordinator=mock_coordinator
        )
        
        # Assert
        assert entity.current_temperature == 23.5
        mock_sensor_manager.get_room_temperature.assert_called_once()

    def test_preset_modes_returns_smart_climate_modes(self):
        """Test that preset_modes returns smart climate specific modes."""
        # Arrange
        mock_hass = create_mock_hass()
        config = {"name": "Test Smart Climate"}
        
        # Create mock dependencies
        mock_offset_engine = create_mock_offset_engine()
        mock_sensor_manager = create_mock_sensor_manager()
        mock_mode_manager = create_mock_mode_manager()
        mock_temperature_controller = create_mock_temperature_controller()
        mock_coordinator = create_mock_coordinator()
        
        # Act
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=mock_offset_engine,
            sensor_manager=mock_sensor_manager,
            mode_manager=mock_mode_manager,
            temperature_controller=mock_temperature_controller,
            coordinator=mock_coordinator
        )
        
        # Assert
        assert entity.preset_modes == ["none", "away", "sleep", "boost"]

    def test_preset_mode_returns_current_mode_from_manager(self):
        """Test that preset_mode returns current mode from mode manager."""
        # Arrange
        mock_hass = create_mock_hass()
        config = {"name": "Test Smart Climate"}
        
        # Create mock dependencies
        mock_offset_engine = create_mock_offset_engine()
        mock_sensor_manager = create_mock_sensor_manager()
        mock_mode_manager = create_mock_mode_manager()
        mock_mode_manager.current_mode = "sleep"
        mock_temperature_controller = create_mock_temperature_controller()
        mock_coordinator = create_mock_coordinator()
        
        # Act
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=mock_offset_engine,
            sensor_manager=mock_sensor_manager,
            mode_manager=mock_mode_manager,
            temperature_controller=mock_temperature_controller,
            coordinator=mock_coordinator
        )
        
        # Assert
        assert entity.preset_mode == "sleep"

    def test_target_temperature_returns_user_facing_temperature(self):
        """Test that target_temperature returns user-facing temperature."""
        # Arrange
        mock_hass = create_mock_hass()
        config = {"name": "Test Smart Climate"}
        
        # Create mock dependencies
        mock_offset_engine = create_mock_offset_engine()
        mock_sensor_manager = create_mock_sensor_manager()
        mock_mode_manager = create_mock_mode_manager()
        mock_temperature_controller = create_mock_temperature_controller()
        mock_coordinator = create_mock_coordinator()
        
        # Act
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=mock_offset_engine,
            sensor_manager=mock_sensor_manager,
            mode_manager=mock_mode_manager,
            temperature_controller=mock_temperature_controller,
            coordinator=mock_coordinator
        )
        
        # Set target temperature
        entity._attr_target_temperature = 24.0
        
        # Assert
        assert entity.target_temperature == 24.0

    def test_all_climate_properties_properly_wrapped(self):
        """Test that all climate properties are properly wrapped."""
        # Arrange
        mock_hass = create_mock_hass()
        config = {"name": "Test Smart Climate"}
        
        # Mock the wrapped entity state with all properties
        wrapped_state = create_mock_state(
            "climate.test_ac", 
            HVACMode.COOL, 
            {
                "hvac_modes": [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT],
                "supported_features": ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE,
                "friendly_name": "Test AC",
                "min_temp": 16.0,
                "max_temp": 30.0,
                "temperature_unit": "°C"
            }
        )
        mock_hass.states.get.return_value = wrapped_state
        
        # Create mock dependencies
        mock_offset_engine = create_mock_offset_engine()
        mock_sensor_manager = create_mock_sensor_manager()
        mock_sensor_manager.get_room_temperature.return_value = 22.0
        mock_mode_manager = create_mock_mode_manager()
        mock_mode_manager.current_mode = "none"
        mock_temperature_controller = create_mock_temperature_controller()
        mock_coordinator = create_mock_coordinator()
        
        # Act
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=mock_offset_engine,
            sensor_manager=mock_sensor_manager,
            mode_manager=mock_mode_manager,
            temperature_controller=mock_temperature_controller,
            coordinator=mock_coordinator
        )
        
        # Assert - Check that all properties are properly wrapped
        assert entity.hvac_mode == HVACMode.COOL
        assert entity.hvac_modes == [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT]
        assert entity.supported_features == (ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE)
        assert entity.current_temperature == 22.0  # From room sensor
        assert entity.preset_modes == ["none", "away", "sleep", "boost"]  # Smart climate modes
        assert entity.preset_mode == "none"  # From mode manager
        assert "Smart" in entity.name  # Smart prefix added
        assert entity.unique_id == "smart_climate.test_ac"  # Smart prefix in unique_id

    def test_entity_handles_missing_wrapped_entity(self):
        """Test that entity handles missing wrapped entity gracefully."""
        # Arrange
        mock_hass = create_mock_hass()
        config = {"name": "Test Smart Climate"}
        
        # Mock missing wrapped entity
        mock_hass.states.get.return_value = None
        
        # Create mock dependencies
        mock_offset_engine = create_mock_offset_engine()
        mock_sensor_manager = create_mock_sensor_manager()
        mock_mode_manager = create_mock_mode_manager()
        mock_temperature_controller = create_mock_temperature_controller()
        mock_coordinator = create_mock_coordinator()
        
        # Act
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=config,
            wrapped_entity_id="climate.nonexistent",
            room_sensor_id="sensor.room_temp",
            offset_engine=mock_offset_engine,
            sensor_manager=mock_sensor_manager,
            mode_manager=mock_mode_manager,
            temperature_controller=mock_temperature_controller,
            coordinator=mock_coordinator
        )
        
        # Assert - Should handle missing entity gracefully
        assert entity.hvac_mode == HVACMode.OFF  # Default when entity missing
        assert entity.hvac_modes == []  # Empty when entity missing
        assert entity.supported_features == 0  # No features when entity missing