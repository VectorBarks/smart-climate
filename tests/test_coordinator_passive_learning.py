"""ABOUTME: Unit tests for coordinator passive learning HVAC state feeding.
Tests the _map_hvac_action_to_state method and integration functionality."""

import pytest
import sys
from unittest.mock import Mock, patch

# Import before conftest.py mocks are applied
from custom_components.smart_climate.coordinator import SmartClimateCoordinator

# Since conftest.py mocks DataUpdateCoordinator, we need to temporarily unmock it
# Store the original mock
_original_mock = sys.modules.get('homeassistant.helpers.update_coordinator')

# Create a minimal real DataUpdateCoordinator for testing
class MockDataUpdateCoordinator:
    def __init__(self, hass, logger, name, update_interval):
        self.hass = hass
        self.logger = logger  
        self.name = name
        self.update_interval = update_interval

# Replace the mock temporarily
if 'homeassistant.helpers.update_coordinator' in sys.modules:
    sys.modules['homeassistant.helpers.update_coordinator'].DataUpdateCoordinator = MockDataUpdateCoordinator


class TestCoordinatorPassiveLearning:
    """Test coordinator passive learning functionality."""

    def test_map_hvac_action_to_state_direct_mapping(self):
        """Test direct mapping of known HVAC actions."""
        # Create coordinator instance (we only need the method)
        hass = Mock()
        sensor_manager = Mock()
        offset_engine = Mock()
        mode_manager = Mock()
        
        coordinator = SmartClimateCoordinator(
            hass=hass,
            update_interval=60,
            sensor_manager=sensor_manager,
            offset_engine=offset_engine,
            mode_manager=mode_manager
        )
        
        # Test direct mappings
        assert coordinator._map_hvac_action_to_state("cooling", None) == "cooling"
        assert coordinator._map_hvac_action_to_state("heating", None) == "heating"
        assert coordinator._map_hvac_action_to_state("idle", None) == "idle"
        assert coordinator._map_hvac_action_to_state("off", None) == "off"

    def test_map_hvac_action_to_state_power_inference(self):
        """Test power-based HVAC state inference when action is unavailable."""
        hass = Mock()
        sensor_manager = Mock()
        offset_engine = Mock()
        mode_manager = Mock()
        
        coordinator = SmartClimateCoordinator(
            hass=hass,
            update_interval=60,
            sensor_manager=sensor_manager,
            offset_engine=offset_engine,
            mode_manager=mode_manager
        )
        
        # Test power-based inference
        assert coordinator._map_hvac_action_to_state(None, 500) == "cooling"  # High power
        assert coordinator._map_hvac_action_to_state(None, 150) == "cooling"  # Above threshold
        assert coordinator._map_hvac_action_to_state(None, 50) == "idle"      # Low power
        assert coordinator._map_hvac_action_to_state(None, 0) == "idle"       # Zero power
        
        # Test fallback behavior
        assert coordinator._map_hvac_action_to_state(None, None) == "idle"     # No data
        assert coordinator._map_hvac_action_to_state("unknown", None) == "idle"  # Unknown action

    @pytest.mark.asyncio
    async def test_hvac_state_feeding_integration(self):
        """Test that HVAC state is fed to StabilityDetector during coordinator update."""
        # Set up mocks
        hass = Mock()
        hass.states.get.return_value = Mock(
            state="cool",
            attributes={"hvac_action": "cooling"}
        )
        
        sensor_manager = Mock()
        sensor_manager.get_room_temperature.return_value = 25.0
        sensor_manager.get_outdoor_temperature.return_value = 30.0
        sensor_manager.get_power_consumption.return_value = 200
        
        offset_engine = Mock()
        offset_engine.calculate_offset.return_value = Mock(offset=0.0, reason="test")
        
        mode_manager = Mock()
        mode_manager.get_adjustments.return_value = {}
        mode_manager.current_mode = "auto"
        
        # Mock thermal manager and stability detector
        mock_stability_detector = Mock()
        mock_thermal_manager = Mock()
        mock_thermal_manager.stability_detector = mock_stability_detector
        mock_thermal_manager.current_state = Mock(value="PRIMING")
        mock_thermal_manager.get_operating_window.return_value = (23.0, 26.0)
        mock_thermal_manager.get_learning_target.return_value = 24.5
        mock_thermal_manager.should_ac_run.return_value = False
        mock_thermal_manager.update_state = Mock()
        
        # Create coordinator
        coordinator = SmartClimateCoordinator(
            hass=hass,
            update_interval=60,
            sensor_manager=sensor_manager,
            offset_engine=offset_engine,
            mode_manager=mode_manager,
            thermal_efficiency_enabled=True,
            wrapped_entity_id="climate.test_ac",
            entity_id="climate.smart_climate_test"
        )
        
        # Mock get_thermal_manager to return our mock
        coordinator.get_thermal_manager = Mock(return_value=mock_thermal_manager)
        
        # Mock other methods that might interfere
        coordinator._execute_outlier_detection = Mock(return_value={})
        coordinator._run_cycle_detection_state_machine = Mock()
        coordinator._check_weather_wake_up = Mock()
        
        # Patch datetime to get predictable timestamp
        with patch('homeassistant.util.dt.utcnow') as mock_utcnow:
            mock_utcnow.return_value.timestamp.return_value = 1234567890.0
            
            # Act: Run coordinator update
            result = await coordinator._async_update_data()
            
        # Assert: Verify add_reading was called with correct parameters
        mock_stability_detector.add_reading.assert_called_once_with(
            1234567890.0,  # timestamp
            25.0,          # temperature
            "cooling"      # HVAC state
        )
        
        # Also verify the old update method was called
        mock_stability_detector.update.assert_called_once_with("cooling", 25.0)

    @pytest.mark.asyncio
    async def test_hvac_state_feeding_with_power_fallback(self):
        """Test HVAC state feeding when hvac_action is not available."""
        # Set up mocks - no hvac_action in attributes
        hass = Mock()
        hass.states.get.return_value = Mock(
            state="cool",
            attributes={}  # No hvac_action
        )
        
        sensor_manager = Mock()
        sensor_manager.get_room_temperature.return_value = 24.0
        sensor_manager.get_outdoor_temperature.return_value = 28.0
        sensor_manager.get_power_consumption.return_value = 300  # High power -> cooling
        
        offset_engine = Mock()
        offset_engine.calculate_offset.return_value = Mock(offset=0.5, reason="power_inference")
        
        mode_manager = Mock()
        mode_manager.get_adjustments.return_value = {}
        mode_manager.current_mode = "auto"
        
        # Mock thermal components
        mock_stability_detector = Mock()
        mock_thermal_manager = Mock()
        mock_thermal_manager.stability_detector = mock_stability_detector
        mock_thermal_manager.current_state = Mock(value="PRIMING")
        mock_thermal_manager.get_operating_window.return_value = (22.0, 25.0)
        mock_thermal_manager.get_learning_target.return_value = 23.5
        mock_thermal_manager.should_ac_run.return_value = True
        mock_thermal_manager.update_state = Mock()
        
        # Create coordinator
        coordinator = SmartClimateCoordinator(
            hass=hass,
            update_interval=60,
            sensor_manager=sensor_manager,
            offset_engine=offset_engine,
            mode_manager=mode_manager,
            thermal_efficiency_enabled=True,
            wrapped_entity_id="climate.test_ac",
            entity_id="climate.smart_climate_test"
        )
        
        # Mock dependencies
        coordinator.get_thermal_manager = Mock(return_value=mock_thermal_manager)
        coordinator._execute_outlier_detection = Mock(return_value={})
        coordinator._run_cycle_detection_state_machine = Mock()
        coordinator._check_weather_wake_up = Mock()
        
        # Mock _infer_ac_state_from_power method that might be called
        coordinator._infer_ac_state_from_power = Mock(return_value="cooling")
        
        # Patch datetime
        with patch('homeassistant.util.dt.utcnow') as mock_utcnow:
            mock_utcnow.return_value.timestamp.return_value = 1234567891.0
            
            # Act: Run coordinator update
            await coordinator._async_update_data()
            
        # Assert: Verify add_reading was called with power-inferred state
        mock_stability_detector.add_reading.assert_called_once_with(
            1234567891.0,  # timestamp
            24.0,          # temperature
            "cooling"      # HVAC state inferred from power
        )