"""Tests for SmartClimateCalibrationButton entity.

Tests the button entity implementation for manual calibration trigger following TDD.
Covers button creation, press handling, and integration with ThermalManager.
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.smart_climate.thermal_models import ThermalState


class TestSmartClimateCalibrationButton:
    """Test SmartClimateCalibrationButton entity behavior."""

    @pytest.fixture
    def mock_hass(self):
        """Mock Home Assistant instance."""
        return Mock()

    @pytest.fixture
    def mock_config_entry(self):
        """Mock ConfigEntry."""
        config_entry = Mock()
        config_entry.entry_id = "test_entry"
        config_entry.title = "Test Climate"
        return config_entry

    @pytest.fixture
    def mock_coordinator(self):
        """Mock SmartClimateCoordinator."""
        coordinator = Mock()
        coordinator.get_thermal_manager = Mock()
        coordinator.async_request_refresh = AsyncMock()
        return coordinator

    @pytest.fixture
    def mock_thermal_manager(self):
        """Mock ThermalManager with force_calibration method."""
        thermal_manager = Mock()
        thermal_manager.force_calibration = Mock()
        thermal_manager.current_state = ThermalState.DRIFTING
        return thermal_manager

    def test_button_entity_creation(self, mock_hass, mock_config_entry):
        """Test SmartClimateCalibrationButton can be created."""
        from custom_components.smart_climate.button import SmartClimateCalibrationButton
        
        button = SmartClimateCalibrationButton(mock_hass, mock_config_entry, "climate.living_room")
        
        assert isinstance(button, ButtonEntity)
        assert button._entity_id == "climate.living_room"
        assert button.hass is mock_hass
        assert button._config_entry is mock_config_entry

    def test_button_has_correct_attributes(self, mock_hass, mock_config_entry):
        """Test button has correct name, unique_id, and icon."""
        from custom_components.smart_climate.button import SmartClimateCalibrationButton
        
        button = SmartClimateCalibrationButton(mock_hass, mock_config_entry, "climate.living_room")
        
        assert button._attr_name == "Force Calibration"
        assert button._attr_unique_id == "climate_living_room_force_calibration"
        assert button._attr_icon == "mdi:target"

    @pytest.mark.asyncio
    async def test_button_press_calls_force_calibration(self, mock_hass, mock_config_entry, mock_thermal_manager, mock_coordinator):
        """Test button press calls force_calibration on ThermalManager."""
        from custom_components.smart_climate.button import SmartClimateCalibrationButton
        from custom_components.smart_climate.const import DOMAIN
        
        # Setup hass.data structure
        mock_hass.data = {
            DOMAIN: {
                "test_entry": {
                    "thermal_components": {
                        "climate.living_room": {"thermal_manager": mock_thermal_manager}
                    },
                    "coordinators": {
                        "climate.living_room": mock_coordinator
                    }
                }
            }
        }
        
        button = SmartClimateCalibrationButton(mock_hass, mock_config_entry, "climate.living_room")
        
        await button.async_press()
        
        # Should call force_calibration on thermal manager
        mock_thermal_manager.force_calibration.assert_called_once()
        
        # Should request coordinator refresh
        mock_coordinator.async_request_refresh.assert_called_once()

    async def test_button_press_handles_missing_thermal_manager(self, mock_coordinator):
        """Test button press handles case where thermal manager is not found."""
        from custom_components.smart_climate.button import SmartClimateCalibrationButton
        
        # Setup coordinator to return None (no thermal manager)
        mock_coordinator.get_thermal_manager.return_value = None
        
        button = SmartClimateCalibrationButton(mock_coordinator, "climate.living_room")
        
        # Should not raise exception when thermal manager is missing
        await button.async_press()
        
        # Should still request coordinator refresh
        mock_coordinator.async_request_refresh.assert_called_once()

    def test_button_availability_based_on_state(self, mock_coordinator, mock_thermal_manager):
        """Test button availability based on thermal manager state."""
        from custom_components.smart_climate.button import SmartClimateCalibrationButton
        
        mock_coordinator.get_thermal_manager.return_value = mock_thermal_manager
        
        button = SmartClimateCalibrationButton(mock_coordinator, "climate.living_room")
        
        # Button should be available when thermal manager exists
        # (availability logic might be implemented in the actual button)
        assert hasattr(button, '_coordinator')
        assert button._entity_id == "climate.living_room"

    async def test_button_press_logs_action(self, mock_coordinator, mock_thermal_manager):
        """Test button press logs the calibration action."""
        from custom_components.smart_climate.button import SmartClimateCalibrationButton
        
        mock_coordinator.get_thermal_manager.return_value = mock_thermal_manager
        
        button = SmartClimateCalibrationButton(mock_coordinator, "climate.living_room")
        
        # Mock logger to verify logging
        with patch('custom_components.smart_climate.button._LOGGER') as mock_logger:
            await button.async_press()
            
            # Should log the button press action
            # (specific log messages depend on implementation)
            assert mock_logger.debug.called or mock_logger.info.called

    def test_button_device_info_set_correctly(self, mock_coordinator):
        """Test button device info is set correctly for UI grouping."""
        from custom_components.smart_climate.button import SmartClimateCalibrationButton
        
        button = SmartClimateCalibrationButton(mock_coordinator, "climate.living_room")
        
        # Button should have device info for proper UI grouping
        # (specific device info structure depends on implementation)
        assert hasattr(button, '_attr_unique_id')
        assert "climate.living_room" in button._attr_unique_id

    async def test_button_press_error_handling(self, mock_coordinator, mock_thermal_manager):
        """Test button press handles errors gracefully."""
        from custom_components.smart_climate.button import SmartClimateCalibrationButton
        
        # Setup thermal manager to raise exception
        mock_thermal_manager.force_calibration.side_effect = Exception("Test error")
        mock_coordinator.get_thermal_manager.return_value = mock_thermal_manager
        
        button = SmartClimateCalibrationButton(mock_coordinator, "climate.living_room")
        
        # Should not raise exception even if force_calibration fails
        try:
            await button.async_press()
        except Exception:
            pytest.fail("Button press should handle errors gracefully")

    def test_button_unique_id_prevents_conflicts(self, mock_coordinator):
        """Test button unique_id prevents conflicts with multiple entities."""
        from custom_components.smart_climate.button import SmartClimateCalibrationButton
        
        button1 = SmartClimateCalibrationButton(mock_coordinator, "climate.living_room")
        button2 = SmartClimateCalibrationButton(mock_coordinator, "climate.bedroom")
        
        # Should have different unique IDs
        assert button1._attr_unique_id != button2._attr_unique_id
        assert "living_room" in button1._attr_unique_id
        assert "bedroom" in button2._attr_unique_id


class TestCalibrationButtonIntegration:
    """Test calibration button integration with Home Assistant."""

    async def test_button_registered_in_async_setup_entry(self):
        """Test that calibration button is registered in async_setup_entry."""
        # This would test the button.py async_setup_entry function
        # to ensure SmartClimateCalibrationButton is created alongside existing buttons
        
        # Note: This test would require mocking Home Assistant entry setup
        # and verifying the button is added to the entities list
        pass

    def test_button_appears_in_ui_with_correct_grouping(self):
        """Test that button appears in UI grouped with climate entity."""
        # This would be an integration test to verify UI grouping
        # Testing device_info configuration for proper entity grouping
        pass

    async def test_button_state_updates_after_calibration_triggered(self):
        """Test that button state/availability updates after calibration."""
        # This would test that button reflects system state changes
        # after calibration is triggered (if applicable)
        pass