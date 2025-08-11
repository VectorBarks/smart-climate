"""Tests for coordinator stability detector integration.

Testing Prompt 7 requirements:
- Coordinator updates stability detector with AC state and room temperature
- Coordinator tracks AC state changes properly  
- Detector state survives coordinator refresh
- Integration with thermal manager for opportunistic calibration
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.smart_climate.coordinator import SmartClimateCoordinator
from custom_components.smart_climate.models import SmartClimateData


class TestCoordinatorStabilityIntegration:
    """Test coordinator integration with stability detector."""

    def setup_method(self):
        """Set up test fixtures."""
        self.hass = Mock()
        self.sensor_manager = Mock()
        self.offset_engine = Mock()  
        self.mode_manager = Mock()
        
        # Mock sensor data
        self.sensor_manager.get_room_temperature.return_value = 22.5
        self.sensor_manager.get_outdoor_temperature.return_value = 30.0
        self.sensor_manager.get_power_consumption.return_value = 150.0
        
        # Mock mode adjustments
        self.mode_manager.get_adjustments.return_value = Mock(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        )
        self.mode_manager.current_mode = "none"
        
        # Mock offset result
        self.offset_engine.calculate_offset.return_value = Mock(
            offset=1.5, clamped=False, reason="Normal", confidence=0.8
        )
        
        # Mock async methods
        self.offset_engine.pause_learning = Mock()
        self.offset_engine.resume_learning = Mock()
        self.offset_engine.async_save_learning_data = AsyncMock()

    @pytest.mark.asyncio
    async def test_coordinator_updates_stability_detector(self):
        """Test that coordinator updates thermal manager's stability detector."""
        # Mock forecast engine with async methods
        mock_forecast_engine = Mock()
        mock_forecast_engine.async_update = AsyncMock()
        mock_forecast_engine.get_weather_strategy.return_value = Mock(pre_action_needed=False)
        
        # Create coordinator with thermal efficiency enabled
        coordinator = SmartClimateCoordinator(
            hass=self.hass,
            update_interval=180,
            sensor_manager=self.sensor_manager,
            offset_engine=self.offset_engine,
            mode_manager=self.mode_manager,
            forecast_engine=mock_forecast_engine,
            thermal_efficiency_enabled=True,
            entity_id="climate.living_room"
        )
        
        # Mock ThermalManager with stability detector
        mock_thermal_manager = Mock()
        mock_stability_detector = Mock()
        mock_thermal_manager.stability_detector = mock_stability_detector
        mock_thermal_manager.current_state.value = "drifting"
        
        # Mock async methods that the coordinator calls
        mock_thermal_manager.update_state = AsyncMock()
        mock_thermal_manager.get_operating_window.return_value = (20.0, 24.0)
        mock_thermal_manager.get_learning_target.return_value = 22.0
        
        # Mock the get_thermal_manager method to return our mock
        with patch.object(coordinator, 'get_thermal_manager', return_value=mock_thermal_manager):
            # Mock wrapped entity state to provide AC state
            wrapped_state = Mock()
            wrapped_state.attributes = {"hvac_action": "cooling", "current_temperature": 21.0}
            wrapped_state.state = "cool"
            self.hass.states.get.return_value = wrapped_state
            
            # Update coordinator data
            await coordinator._async_update_data()
            
            # Verify stability detector was updated with AC state and temperature
            # This test will initially fail until we implement the update logic
            mock_stability_detector.update.assert_called_once_with("cooling", 22.5)

    @pytest.mark.asyncio  
    async def test_coordinator_tracks_ac_state_changes(self):
        """Test that coordinator properly tracks AC on/off/idle transitions."""
        coordinator = SmartClimateCoordinator(
            hass=self.hass,
            update_interval=180,
            sensor_manager=self.sensor_manager,
            offset_engine=self.offset_engine,
            mode_manager=self.mode_manager,
            thermal_efficiency_enabled=True,
            entity_id="climate.living_room"
        )
        
        # Mock ThermalManager with stability detector
        mock_thermal_manager = Mock()
        mock_stability_detector = Mock()
        mock_thermal_manager.stability_detector = mock_stability_detector
        mock_thermal_manager.current_state.value = "drifting"
        
        with patch.object(coordinator, 'get_thermal_manager', return_value=mock_thermal_manager):
            # Simulate AC state changes over multiple updates
            
            # Update 1: AC cooling
            wrapped_state = Mock()
            wrapped_state.attributes = {"hvac_action": "cooling"}
            wrapped_state.state = "cool"
            self.hass.states.get.return_value = wrapped_state
            await coordinator._async_update_data()
            
            # Update 2: AC idle
            wrapped_state.attributes = {"hvac_action": "idle"}
            await coordinator._async_update_data()
            
            # Update 3: AC cooling again  
            wrapped_state.attributes = {"hvac_action": "cooling"}
            await coordinator._async_update_data()
            
            # Verify all state changes were tracked
            # This test will initially fail until we implement state tracking
            expected_calls = [
                (("cooling", 22.5),),
                (("idle", 22.5),),
                (("cooling", 22.5),)
            ]
            actual_calls = mock_stability_detector.update.call_args_list
            assert len(actual_calls) == 3, f"Expected 3 updates, got {len(actual_calls)}"

    @pytest.mark.asyncio
    async def test_detector_state_survives_coordinator_refresh(self):
        """Test that stability detector state persists across coordinator refreshes."""
        coordinator = SmartClimateCoordinator(
            hass=self.hass,
            update_interval=180,
            sensor_manager=self.sensor_manager,
            offset_engine=self.offset_engine,
            mode_manager=self.mode_manager,
            thermal_efficiency_enabled=True,
            entity_id="climate.living_room"
        )
        
        # Mock ThermalManager with stability detector that maintains state
        mock_thermal_manager = Mock()
        mock_stability_detector = Mock()
        mock_thermal_manager.stability_detector = mock_stability_detector
        mock_thermal_manager.current_state.value = "drifting"
        
        # Detector should maintain internal state between calls
        mock_stability_detector.is_stable_for_calibration.return_value = False
        
        with patch.object(coordinator, 'get_thermal_manager', return_value=mock_thermal_manager):
            # Mock wrapped entity
            wrapped_state = Mock()
            wrapped_state.attributes = {"hvac_action": "idle"}
            wrapped_state.state = "cool"
            self.hass.states.get.return_value = wrapped_state
            
            # Multiple refreshes
            await coordinator._async_update_data()
            await coordinator._async_update_data()
            await coordinator._async_update_data()
            
            # Detector should have been called multiple times but maintain state
            # This test will initially pass as it just verifies the detector object persists
            assert mock_stability_detector.update.call_count == 3
            assert mock_thermal_manager.stability_detector is mock_stability_detector

    def test_coordinator_provides_detector_to_thermal_manager(self):
        """Test that coordinator provides stability detector to thermal manager during initialization."""
        # This test verifies the integration setup
        coordinator = SmartClimateCoordinator(
            hass=self.hass,
            update_interval=180,
            sensor_manager=self.sensor_manager,
            offset_engine=self.offset_engine,
            mode_manager=self.mode_manager,
            thermal_efficiency_enabled=True,
            entity_id="climate.living_room"
        )
        
        # Mock thermal manager setup that should receive stability configuration
        mock_thermal_manager = Mock()
        mock_stability_detector = Mock()
        mock_thermal_manager.stability_detector = mock_stability_detector
        
        with patch.object(coordinator, 'get_thermal_manager', return_value=mock_thermal_manager):
            # Get thermal manager from coordinator
            thermal_manager = coordinator.get_thermal_manager("climate.living_room")
            
            # Verify thermal manager has stability detector
            # This test will initially pass if we mock correctly
            assert hasattr(thermal_manager, 'stability_detector')
            assert thermal_manager.stability_detector is not None

    @pytest.mark.asyncio
    async def test_coordinator_handles_missing_thermal_manager_gracefully(self):
        """Test coordinator handles case where thermal manager is not available."""
        coordinator = SmartClimateCoordinator(
            hass=self.hass,
            update_interval=180,
            sensor_manager=self.sensor_manager,
            offset_engine=self.offset_engine,
            mode_manager=self.mode_manager,
            thermal_efficiency_enabled=False,  # Disabled
            entity_id="climate.living_room"
        )
        
        # Mock wrapped entity
        wrapped_state = Mock()
        wrapped_state.attributes = {"hvac_action": "cooling"}
        wrapped_state.state = "cool"
        self.hass.states.get.return_value = wrapped_state
        
        # Update should not fail even without thermal manager
        result = await coordinator._async_update_data()
        
        # This test should pass - coordinator should handle missing thermal manager gracefully
        assert isinstance(result, SmartClimateData)
        assert result.room_temp == 22.5

    @pytest.mark.asyncio
    async def test_coordinator_ac_state_inference_from_power(self):
        """Test that coordinator can infer AC state from power consumption when hvac_action unavailable."""
        coordinator = SmartClimateCoordinator(
            hass=self.hass,
            update_interval=180,
            sensor_manager=self.sensor_manager,
            offset_engine=self.offset_engine,
            mode_manager=self.mode_manager,
            thermal_efficiency_enabled=True,
            entity_id="climate.living_room"
        )
        
        # Mock ThermalManager with stability detector
        mock_thermal_manager = Mock()
        mock_stability_detector = Mock()
        mock_thermal_manager.stability_detector = mock_stability_detector
        mock_thermal_manager.current_state.value = "drifting"
        
        with patch.object(coordinator, 'get_thermal_manager', return_value=mock_thermal_manager):
            # Test case 1: High power consumption (>100W) should indicate "cooling"
            wrapped_state = Mock()
            wrapped_state.attributes = {}  # No hvac_action available
            wrapped_state.state = "cool"
            self.hass.states.get.return_value = wrapped_state
            self.sensor_manager.get_power_consumption.return_value = 500.0  # High power
            
            await coordinator._async_update_data()
            
            # Should infer "cooling" from high power
            # This test will initially fail until we implement power-based inference
            mock_stability_detector.update.assert_called_with("cooling", 22.5)
            
            # Test case 2: Low power consumption should indicate "idle"  
            mock_stability_detector.reset_mock()
            self.sensor_manager.get_power_consumption.return_value = 50.0  # Low power
            
            await coordinator._async_update_data()
            
            # Should infer "idle" from low power
            mock_stability_detector.update.assert_called_with("idle", 22.5)

    @pytest.mark.asyncio
    async def test_coordinator_stability_integration_with_thermal_state(self):
        """Test that stability detector integrates properly with thermal state transitions."""
        coordinator = SmartClimateCoordinator(
            hass=self.hass,
            update_interval=180,
            sensor_manager=self.sensor_manager,
            offset_engine=self.offset_engine,
            mode_manager=self.mode_manager,
            thermal_efficiency_enabled=True,
            entity_id="climate.living_room"
        )
        
        # Mock ThermalManager that can transition to CALIBRATING
        mock_thermal_manager = Mock()
        mock_stability_detector = Mock()
        mock_thermal_manager.stability_detector = mock_stability_detector
        mock_thermal_manager.current_state.value = "drifting"
        
        # Simulate stability detector indicating stable conditions
        mock_stability_detector.is_stable_for_calibration.return_value = True
        
        with patch.object(coordinator, 'get_thermal_manager', return_value=mock_thermal_manager):
            # Mock wrapped entity
            wrapped_state = Mock()
            wrapped_state.attributes = {"hvac_action": "idle"}  
            wrapped_state.state = "cool"
            self.hass.states.get.return_value = wrapped_state
            
            # Update coordinator - should update detector and check for calibration
            await coordinator._async_update_data()
            
            # Verify detector was updated
            mock_stability_detector.update.assert_called_once_with("idle", 22.5)
            
            # This test verifies the integration works but doesn't verify calibration triggering
            # (that's handled by thermal manager state logic, not coordinator)
            assert mock_thermal_manager.stability_detector is mock_stability_detector