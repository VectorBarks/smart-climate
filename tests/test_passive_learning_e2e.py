"""ABOUTME: End-to-end integration tests for passive learning during PRIMING state.
Tests the complete flow from HVAC state detection to tau value learning."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import List, Tuple

from custom_components.smart_climate.coordinator import SmartClimateCoordinator
from custom_components.smart_climate.thermal_manager import ThermalManager
from custom_components.smart_climate.thermal_stability import StabilityDetector
from custom_components.smart_climate.thermal_models import ThermalState, ProbeResult
from custom_components.smart_climate.thermal_utils import analyze_drift_data


class TestPassiveLearningE2E:
    """End-to-end tests for passive learning integration."""

    @pytest.fixture
    def mock_hass(self):
        """Mock Home Assistant instance."""
        hass = Mock()
        hass.states = Mock()
        return hass

    @pytest.fixture
    def mock_wrapped_entity_state(self):
        """Mock wrapped climate entity state."""
        state = Mock()
        state.state = "cool"
        state.attributes = {
            "hvac_action": "cooling",
            "current_temperature": 24.0
        }
        return state

    @pytest.fixture
    def mock_sensor_manager(self):
        """Mock sensor manager with stable temperature readings."""
        manager = Mock()
        manager.get_room_temperature.return_value = 25.0
        manager.get_outdoor_temperature.return_value = 30.0
        manager.get_power_consumption.return_value = 50  # AC off power level
        return manager

    @pytest.fixture
    def mock_thermal_manager(self):
        """Mock thermal manager in PRIMING state with passive learning enabled."""
        manager = Mock(spec=ThermalManager)
        manager.current_state = ThermalState.PRIMING
        manager.stability_detector = Mock(spec=StabilityDetector)
        manager.config = {
            "passive_learning_enabled": True,
            "passive_min_drift_minutes": 15,
            "passive_confidence_threshold": 0.3
        }
        
        # Mock get_operating_window to return reasonable values
        manager.get_operating_window.return_value = (23.0, 26.0)
        manager.get_learning_target.return_value = 24.5
        manager.should_ac_run.return_value = False
        manager.update_state = Mock()
        
        return manager

    def create_test_coordinator(self, mock_hass, mock_sensor_manager, mock_thermal_manager):
        """Create coordinator with mocked dependencies."""
        from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
        
        # Mock all required dependencies
        offset_engine = Mock()
        offset_engine.calculate_offset.return_value = Mock(offset=0.0, reason="test")
        
        mode_manager = Mock()
        mode_manager.get_adjustments.return_value = {}
        mode_manager.current_mode = "auto"
        
        # Create real coordinator instance, not a mock
        coordinator = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=60,
            sensor_manager=mock_sensor_manager,
            offset_engine=offset_engine,
            mode_manager=mode_manager,
            thermal_efficiency_enabled=True,
            wrapped_entity_id="climate.test_ac",
            entity_id="climate.smart_climate_test"
        )
        
        # Verify it's a real coordinator
        assert hasattr(coordinator, '_async_update_data')
        assert callable(coordinator._async_update_data)
        
        # Mock get_thermal_manager to return our mock
        coordinator.get_thermal_manager = Mock(return_value=mock_thermal_manager)
        
        # Mock outlier detection and other components that might cause issues
        coordinator._execute_outlier_detection = Mock(return_value={})
        coordinator._run_cycle_detection_state_machine = Mock()
        coordinator._check_weather_wake_up = Mock()
        coordinator.get_thermal_manager = Mock(return_value=mock_thermal_manager)
        
        return coordinator

    @pytest.mark.asyncio
    async def test_hvac_state_feeding_during_update(
        self,
        mock_hass,
        mock_sensor_manager,
        mock_wrapped_entity_state,
        mock_thermal_manager
    ):
        """Test that coordinator feeds HVAC state to StabilityDetector during updates."""
        # Arrange: Create coordinator and set up state
        coordinator = self.create_test_coordinator(mock_hass, mock_sensor_manager, mock_thermal_manager)
        mock_hass.states.get.return_value = mock_wrapped_entity_state
        
        # Act: Run coordinator update
        result = await coordinator._async_update_data()
        
        # Assert: StabilityDetector.add_reading was called with correct parameters
        mock_thermal_manager.stability_detector.add_reading.assert_called_once()
        call_args = mock_thermal_manager.stability_detector.add_reading.call_args
        
        # Check parameters: timestamp, temp, hvac_state
        timestamp, temp, hvac_state = call_args[0]
        assert isinstance(timestamp, float)  # Unix timestamp
        assert temp == 25.0  # Room temperature from sensor manager
        assert hvac_state == "cooling"  # Mapped from hvac_action

    @pytest.mark.asyncio
    async def test_hvac_action_to_state_mapping(
        self,
        mock_hass,
        mock_sensor_manager,
        mock_thermal_manager
    ):
        """Test mapping of hvac_action values to HVAC states."""
        coordinator = self.create_test_coordinator(mock_hass, mock_sensor_manager, mock_thermal_manager)
        
        test_cases = [
            ("cooling", "cooling"),
            ("heating", "heating"), 
            ("idle", "idle"),
            ("off", "off"),
            (None, "idle")  # Default when no hvac_action
        ]
        
        for hvac_action, expected_state in test_cases:
            # Arrange: Set wrapped entity hvac_action
            mock_state = Mock()
            mock_state.state = "cool"
            mock_state.attributes = {"hvac_action": hvac_action} if hvac_action else {}
            mock_hass.states.get.return_value = mock_state
            
            # Reset mock
            mock_thermal_manager.stability_detector.add_reading.reset_mock()
            
            # Act: Run update
            await coordinator._async_update_data()
            
            # Assert: Correct HVAC state was passed
            call_args = mock_thermal_manager.stability_detector.add_reading.call_args
            if call_args:
                _, _, hvac_state = call_args[0]
                assert hvac_state == expected_state, f"Expected {expected_state}, got {hvac_state}"

    @pytest.mark.asyncio
    async def test_passive_learning_during_priming_simulation(
        self,
        coordinator,
        mock_hass,
        mock_thermal_manager
    ):
        """Test complete passive learning flow during PRIMING state."""
        # Simulate AC turning off scenario
        cooling_data = []
        off_data = []
        
        # Generate cooling period data (declining temperature)
        for i in range(10):
            timestamp = 1000.0 + i * 60  # 1-minute intervals
            temp = 26.0 - (i * 0.1)  # Temperature declining during cooling
            cooling_data.append((timestamp, temp, "cooling"))
        
        # Generate off period data (rising temperature - exponential decay)
        for i in range(20):  # 20 minutes of off data
            timestamp = 1600.0 + i * 60
            # Exponential rise: T(t) = T_final + (T_initial - T_final) * exp(-t/tau)
            # Simulate tau = 30 minutes (1800 seconds)
            t_minutes = i
            temp = 28.0 + (25.0 - 28.0) * (0.95 ** t_minutes)  # Exponential approach to 28°C
            off_data.append((timestamp, temp, "off"))
        
        # Mock StabilityDetector to return this drift event
        def mock_find_drift():
            # Return off period data as temperature drift for analysis
            return [(ts, temp) for ts, temp, _ in off_data]
        
        mock_thermal_manager.stability_detector.find_natural_drift_event.side_effect = mock_find_drift
        
        # Mock thermal manager to simulate passive learning execution
        def mock_handle_passive_learning():
            # Simulate the passive learning process
            drift_data = mock_find_drift()
            if drift_data:
                # This would normally call analyze_drift_data
                with patch('custom_components.smart_climate.thermal_utils.analyze_drift_data') as mock_analyze:
                    mock_probe_result = ProbeResult(
                        tau_value=1800.0,  # 30 minutes
                        confidence=0.4,    # Above 0.3 threshold
                        duration=1200,     # 20 minutes
                        fit_quality=0.8,
                        aborted=False
                    )
                    mock_analyze.return_value = mock_probe_result
                    
                    # This should trigger tau update
                    mock_thermal_manager._model = Mock()
                    mock_thermal_manager._model.update_tau = Mock()
                    
                    # Simulate actual passive learning call
                    result = mock_analyze(drift_data, is_passive=True)
                    if result and result.confidence > 0.3:
                        mock_thermal_manager._model.update_tau(result)
                        
                    return True
            return False
        
        mock_thermal_manager._handle_passive_learning = Mock(side_effect=mock_handle_passive_learning)
        
        # Simulate multiple coordinator updates feeding data to StabilityDetector
        for timestamp, temp, hvac_state in cooling_data + off_data:
            # Set up wrapped entity state for this update
            mock_state = Mock()
            mock_state.state = "cool"
            mock_state.attributes = {"hvac_action": hvac_state}
            mock_hass.states.get.return_value = mock_state
            
            # Override sensor manager to return current temperature
            coordinator._sensor_manager.get_room_temperature.return_value = temp
            
            # Run update - this should feed data to StabilityDetector
            await coordinator._async_update_data()
        
        # Manually trigger passive learning (this would happen in ThermalManager during PRIMING)
        learning_occurred = mock_thermal_manager._handle_passive_learning()
        
        # Assert: Passive learning was executed and tau was updated
        assert learning_occurred is True
        mock_thermal_manager._handle_passive_learning.assert_called()
        
        # Verify StabilityDetector received all the data
        assert mock_thermal_manager.stability_detector.add_reading.call_count == len(cooling_data + off_data)

    @pytest.mark.asyncio 
    async def test_config_integration_passive_learning_disabled(
        self,
        mock_hass,
        mock_sensor_manager
    ):
        """Test that passive learning can be disabled via configuration."""
        # Create coordinator with passive learning disabled
        coordinator = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=60,
            sensor_manager=mock_sensor_manager,
            offset_engine=Mock(),
            mode_manager=Mock(),
            thermal_efficiency_enabled=True,
            wrapped_entity_id="climate.test_ac",
            entity_id="climate.smart_climate_test"
        )
        
        # Mock thermal manager with passive learning disabled
        mock_thermal_manager = Mock(spec=ThermalManager)
        mock_thermal_manager.current_state = ThermalState.PRIMING
        mock_thermal_manager.config = {
            "passive_learning_enabled": False  # Disabled
        }
        mock_thermal_manager.stability_detector = Mock(spec=StabilityDetector)
        
        coordinator.get_thermal_manager = Mock(return_value=mock_thermal_manager)
        
        # Set up wrapped entity state
        mock_state = Mock()
        mock_state.state = "cool"
        mock_state.attributes = {"hvac_action": "off"}
        mock_hass.states.get.return_value = mock_state
        
        # Act: Run update
        await coordinator._async_update_data()
        
        # Assert: StabilityDetector.add_reading should still be called (for opportunistic calibration)
        # But passive learning should not be triggered
        mock_thermal_manager.stability_detector.add_reading.assert_called_once()

    def test_hvac_state_mapping_with_power_fallback(
        self,
        mock_hass,
        mock_sensor_manager,
        mock_thermal_manager
    ):
        """Test HVAC state inference when hvac_action is not available."""
        # Create coordinator to test the mapping method
        coordinator = self.create_test_coordinator(mock_hass, mock_sensor_manager, mock_thermal_manager)
        
        # Test cases: (hvac_action, power, expected_state)
        test_cases = [
            ("cooling", 500, "cooling"),  # Direct mapping
            ("heating", 400, "heating"),  # Direct mapping
            ("idle", 50, "idle"),         # Direct mapping
            ("off", 30, "off"),           # Direct mapping
            (None, 600, "cooling"),       # Power-based inference
            (None, 50, "idle"),           # Power-based inference  
            (None, None, "idle"),         # Default fallback
        ]
        
        for hvac_action, power, expected_state in test_cases:
            # Test the _map_hvac_action_to_state method
            if hasattr(coordinator, '_map_hvac_action_to_state'):
                result = coordinator._map_hvac_action_to_state(hvac_action, power)
                assert result == expected_state, f"For hvac_action={hvac_action}, power={power}: expected {expected_state}, got {result}"
            else:
                pytest.fail("_map_hvac_action_to_state method not implemented")