"""Tests for temperature adjustment behavior in different HVAC modes."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, call
from homeassistant.components.climate.const import HVACMode
from homeassistant.const import STATE_OFF

from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.models import OffsetResult, OffsetInput
from tests.fixtures.mock_entities import (
    create_mock_hass,
    create_mock_state,
    create_mock_offset_engine,
    create_mock_sensor_manager,
    create_mock_mode_manager,
    create_mock_temperature_controller,
    create_mock_coordinator,
)


class TestHVACModeAdjustments:
    """Test temperature adjustments based on HVAC mode."""

    def _set_wrapped_entity_state(self, mock_hass, hvac_mode, target_temp=22.0, current_temp=23.0):
        """Helper to set wrapped entity state."""
        wrapped_state = create_mock_state(
            state=hvac_mode,
            attributes={
                "friendly_name": "Test AC",
                "hvac_mode": hvac_mode,
                "target_temperature": target_temp,
                "current_temperature": current_temp
            },
            entity_id="climate.test_ac"
        )
        mock_hass.states.set("climate.test_ac", wrapped_state)

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        hass = create_mock_hass()
        # Mock the services.async_call method to track service calls
        hass.services.async_call = AsyncMock()
        return hass

    @pytest.fixture
    def mock_dependencies(self, mock_hass):
        """Create mock dependencies for SmartClimateEntity."""
        return {
            "offset_engine": create_mock_offset_engine(),
            "sensor_manager": create_mock_sensor_manager(),
            "mode_manager": create_mock_mode_manager(),
            "temperature_controller": create_mock_temperature_controller(mock_hass),
            "coordinator": create_mock_coordinator(),
        }

    @pytest_asyncio.fixture
    async def entity(self, mock_hass, mock_dependencies):
        """Create SmartClimateEntity instance."""
        config = {"name": "Test Smart Climate", "default_target_temperature": 24.0}
        
        # Create wrapped entity state with proper entity_id
        wrapped_state = create_mock_state(
            state=HVACMode.COOL,
            attributes={
                "friendly_name": "Test AC",
                "hvac_mode": HVACMode.COOL,
                "target_temperature": 22.0,
                "current_temperature": 23.0
            },
            entity_id="climate.test_ac"
        )
        # Store the state in the registry
        mock_hass.states.set("climate.test_ac", wrapped_state)
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            **mock_dependencies
        )
        
        # Set initial values
        entity._attr_target_temperature = 22.0
        entity._attr_hvac_mode = HVACMode.COOL
        
        return entity

    @pytest.mark.asyncio
    async def test_skip_adjustment_in_fan_only_mode(self, entity, mock_hass, mock_dependencies, caplog):
        """Test that temperature adjustments are skipped when HVAC mode is fan_only."""
        # Arrange
        entity._attr_hvac_mode = HVACMode.FAN_ONLY
        target_temp = 24.0
        
        # Ensure wrapped entity state is available during the test
        self._set_wrapped_entity_state(mock_hass, HVACMode.FAN_ONLY)
        
        # Configure offset engine to return a non-zero offset
        mock_dependencies["offset_engine"].calculate_offset.return_value = OffsetResult(
            offset=2.0,
            clamped=False,
            reason="Test offset calculation",
            confidence=0.8
        )
        
        # Act
        await entity._apply_temperature_with_offset(target_temp, source="manual")
        
        # Assert
        # Should NOT call the wrapped entity with adjusted temperature
        mock_hass.services.async_call.assert_not_called()
        
        # Should log that adjustment was skipped
        assert "Skipping temperature adjustment in fan_only HVAC mode" in caplog.text
        
        # Temperature controller should NOT be called
        mock_dependencies["temperature_controller"].apply_offset_and_limits.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_adjustment_in_off_mode(self, entity, mock_hass, mock_dependencies, caplog):
        """Test that temperature adjustments are skipped when HVAC mode is off."""
        # Arrange
        entity._attr_hvac_mode = HVACMode.OFF
        target_temp = 24.0
        
        # Ensure wrapped entity state is available during the test
        self._set_wrapped_entity_state(mock_hass, HVACMode.OFF)
        
        # Configure offset engine to return a non-zero offset
        mock_dependencies["offset_engine"].calculate_offset.return_value = OffsetResult(
            offset=2.0,
            clamped=False,
            reason="Test offset calculation",
            confidence=0.8
        )
        
        # Act
        await entity._apply_temperature_with_offset(target_temp, source="manual")
        
        # Assert
        # Should NOT call the wrapped entity with adjusted temperature
        mock_hass.services.async_call.assert_not_called()
        
        # Should log that adjustment was skipped
        assert "Skipping temperature adjustment in off HVAC mode" in caplog.text
        
        # Temperature controller should NOT be called
        mock_dependencies["temperature_controller"].apply_offset_and_limits.assert_not_called()

    @pytest.mark.asyncio
    async def test_apply_adjustment_in_cool_mode(self, entity, mock_hass, mock_dependencies):
        """Test that temperature adjustments are applied when HVAC mode is cool."""
        # Arrange
        entity._attr_hvac_mode = HVACMode.COOL
        target_temp = 24.0
        
        # Ensure wrapped entity state is available during the test
        self._set_wrapped_entity_state(mock_hass, HVACMode.COOL)
        
        # Configure offset engine to return an offset
        mock_dependencies["offset_engine"].calculate_offset.return_value = OffsetResult(
            offset=2.0,
            clamped=False,
            reason="Test offset calculation",
            confidence=0.8
        )
        
        # Configure temperature controller to return adjusted temperature
        mock_dependencies["temperature_controller"].apply_offset_and_limits.return_value = 22.0
        
        # Act
        await entity._apply_temperature_with_offset(target_temp, source="manual")
        
        # Assert
        # Should call the wrapped entity with adjusted temperature
        mock_hass.services.async_call.assert_called_once_with(
            domain="climate",
            service="set_temperature",
            service_data={"entity_id": "climate.test_ac", "temperature": 22.0}
        )
        
        # Temperature controller should be called with correct parameters
        mock_dependencies["temperature_controller"].apply_offset_and_limits.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_adjustment_in_heat_mode(self, entity, mock_hass, mock_dependencies):
        """Test that temperature adjustments are applied when HVAC mode is heat."""
        # Arrange
        entity._attr_hvac_mode = HVACMode.HEAT
        target_temp = 20.0
        
        # Ensure wrapped entity state is available during the test
        self._set_wrapped_entity_state(mock_hass, HVACMode.HEAT)
        
        # Configure offset engine to return an offset
        mock_dependencies["offset_engine"].calculate_offset.return_value = OffsetResult(
            offset=-2.0,
            clamped=False,
            reason="Test offset calculation",
            confidence=0.8
        )
        
        # Configure temperature controller to return adjusted temperature
        mock_dependencies["temperature_controller"].apply_offset_and_limits.return_value = 22.0
        
        # Act
        await entity._apply_temperature_with_offset(target_temp, source="manual")
        
        # Assert
        # Should call the wrapped entity with adjusted temperature
        mock_hass.services.async_call.assert_called_once_with(
            domain="climate",
            service="set_temperature",
            service_data={"entity_id": "climate.test_ac", "temperature": 22.0}
        )
        
        # Temperature controller should be called with correct parameters
        mock_dependencies["temperature_controller"].apply_offset_and_limits.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_adjustment_in_auto_mode(self, entity, mock_hass, mock_dependencies):
        """Test that temperature adjustments are applied when HVAC mode is auto."""
        # Arrange
        entity._attr_hvac_mode = HVACMode.AUTO
        target_temp = 22.0
        
        # Ensure wrapped entity state is available during the test
        self._set_wrapped_entity_state(mock_hass, HVACMode.AUTO)
        
        # Configure offset engine to return an offset
        mock_dependencies["offset_engine"].calculate_offset.return_value = OffsetResult(
            offset=1.5,
            clamped=False,
            reason="Test offset calculation",
            confidence=0.8
        )
        
        # Configure temperature controller to return adjusted temperature
        mock_dependencies["temperature_controller"].apply_offset_and_limits.return_value = 20.5
        
        # Act
        await entity._apply_temperature_with_offset(target_temp, source="manual")
        
        # Assert
        # Should call the wrapped entity with adjusted temperature
        mock_hass.services.async_call.assert_called_once_with(
            domain="climate",
            service="set_temperature",
            service_data={"entity_id": "climate.test_ac", "temperature": 20.5}
        )
        
        # Temperature controller should be called with correct parameters
        mock_dependencies["temperature_controller"].apply_offset_and_limits.assert_called_once()

    @pytest.mark.asyncio
    async def test_debug_logging_when_skipping_adjustments(self, entity, mock_hass, mock_dependencies, caplog):
        """Test that proper debug logging occurs when adjustments are skipped."""
        # Arrange
        entity._attr_hvac_mode = HVACMode.FAN_ONLY
        target_temp = 24.0
        
        # Ensure wrapped entity state is available during the test
        self._set_wrapped_entity_state(mock_hass, HVACMode.FAN_ONLY)
        
        # Configure offset engine to return a non-zero offset
        mock_dependencies["offset_engine"].calculate_offset.return_value = OffsetResult(
            offset=2.0,
            clamped=False,
            reason="Test offset calculation",
            confidence=0.8
        )
        
        # Enable debug logging
        import logging
        caplog.set_level(logging.DEBUG)
        
        # Act
        await entity._apply_temperature_with_offset(target_temp, source="manual")
        
        # Assert
        # Should have debug logs indicating skip reason
        assert "Skipping temperature adjustment" in caplog.text
        assert "fan_only" in caplog.text
        assert "HVAC mode" in caplog.text

    @pytest.mark.asyncio
    async def test_no_service_calls_in_non_active_modes(self, entity, mock_hass, mock_dependencies):
        """Test that no service calls are made to the wrapped entity in non-active modes."""
        # Arrange
        non_active_modes = [HVACMode.FAN_ONLY, HVACMode.OFF]
        
        for mode in non_active_modes:
            # Reset the mock
            mock_hass.services.async_call.reset_mock()
            
            # Set the mode
            entity._attr_hvac_mode = mode
            # Also set the wrapped entity state
            self._set_wrapped_entity_state(mock_hass, mode)
            
            # Act
            await entity._apply_temperature_with_offset(24.0, source="manual")
            
            # Assert
            mock_hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_mode_transition_behavior(self, entity, mock_hass, mock_dependencies):
        """Test behavior when transitioning between active and non-active modes."""
        # Arrange
        target_temp = 24.0
        
        # Configure offset engine
        mock_dependencies["offset_engine"].calculate_offset.return_value = OffsetResult(
            offset=2.0,
            clamped=False,
            reason="Test offset calculation",
            confidence=0.8
        )
        
        # Configure temperature controller
        mock_dependencies["temperature_controller"].apply_offset_and_limits.return_value = 22.0
        
        # Start in COOL mode - should apply adjustment
        entity._attr_hvac_mode = HVACMode.COOL
        self._set_wrapped_entity_state(mock_hass, HVACMode.COOL)
        await entity._apply_temperature_with_offset(target_temp, source="manual")
        
        # Verify adjustment was applied
        assert mock_hass.services.async_call.call_count == 1
        
        # Switch to FAN_ONLY mode
        entity._attr_hvac_mode = HVACMode.FAN_ONLY
        self._set_wrapped_entity_state(mock_hass, HVACMode.FAN_ONLY)
        mock_hass.services.async_call.reset_mock()
        
        # Try to apply adjustment again
        await entity._apply_temperature_with_offset(target_temp, source="manual")
        
        # Should not make any service calls
        mock_hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_dry_mode_applies_adjustments(self, entity, mock_hass, mock_dependencies):
        """Test that temperature adjustments are applied in DRY mode (dehumidify)."""
        # Arrange
        entity._attr_hvac_mode = HVACMode.DRY
        target_temp = 24.0
        
        # Ensure wrapped entity state is available during the test
        self._set_wrapped_entity_state(mock_hass, HVACMode.DRY)
        
        # Configure offset engine
        mock_dependencies["offset_engine"].calculate_offset.return_value = OffsetResult(
            offset=1.0,
            clamped=False,
            reason="Test offset calculation",
            confidence=0.8
        )
        
        # Configure temperature controller
        mock_dependencies["temperature_controller"].apply_offset_and_limits.return_value = 23.0
        
        # Act
        await entity._apply_temperature_with_offset(target_temp, source="manual")
        
        # Assert - should apply adjustment in DRY mode
        mock_hass.services.async_call.assert_called_once_with(
            domain="climate",
            service="set_temperature",
            service_data={"entity_id": "climate.test_ac", "temperature": 23.0}
        )

    @pytest.mark.asyncio
    async def test_heat_cool_mode_applies_adjustments(self, entity, mock_hass, mock_dependencies):
        """Test that temperature adjustments are applied in HEAT_COOL mode."""
        # Arrange
        entity._attr_hvac_mode = HVACMode.HEAT_COOL
        target_temp = 22.0
        
        # Ensure wrapped entity state is available during the test
        self._set_wrapped_entity_state(mock_hass, HVACMode.HEAT_COOL)
        
        # Configure offset engine
        mock_dependencies["offset_engine"].calculate_offset.return_value = OffsetResult(
            offset=1.5,
            clamped=False,
            reason="Test offset calculation",
            confidence=0.8
        )
        
        # Configure temperature controller
        mock_dependencies["temperature_controller"].apply_offset_and_limits.return_value = 20.5
        
        # Act
        await entity._apply_temperature_with_offset(target_temp, source="manual")
        
        # Assert - should apply adjustment in HEAT_COOL mode
        mock_hass.services.async_call.assert_called_once_with(
            domain="climate",
            service="set_temperature",
            service_data={"entity_id": "climate.test_ac", "temperature": 20.5}
        )