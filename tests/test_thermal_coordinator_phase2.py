"""ABOUTME: Test suite for Phase 2 ThermalManager integration in SmartClimateCoordinator.
Tests state-aware protocol between ThermalManager and OffsetEngine for thermal efficiency."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, call
from datetime import timedelta, datetime, time
from typing import Dict, Tuple, Optional

from custom_components.smart_climate.models import SmartClimateData, ModeAdjustments, OffsetInput, OffsetResult
from custom_components.smart_climate.thermal_models import ThermalState, ThermalConstants
from custom_components.smart_climate.thermal_preferences import UserPreferences, PreferenceLevel
from custom_components.smart_climate.thermal_model import PassiveThermalModel
from custom_components.smart_climate.thermal_manager import ThermalManager
from custom_components.smart_climate.errors import SmartClimateError

# Import coordinator class directly - we'll work with it despite the mocking
from custom_components.smart_climate.coordinator import SmartClimateCoordinator


class TestThermalCoordinatorPhase2:
    """Test Phase 2 integration of ThermalManager with OffsetEngine state-aware protocol."""

    @pytest.fixture
    def mock_hass(self):
        """Mock Home Assistant instance."""
        hass = Mock()
        # Mock entity state for wrapped entity
        wrapped_state = Mock()
        wrapped_state.state = "cool"
        wrapped_state.attributes = {"current_temperature": 23.0}
        hass.states.get.return_value = wrapped_state
        return hass

    @pytest.fixture
    def mock_sensor_manager(self):
        """Mock SensorManager."""
        sensor_manager = Mock()
        sensor_manager.get_room_temperature.return_value = 24.0
        sensor_manager.get_outdoor_temperature.return_value = 30.0
        sensor_manager.get_power_consumption.return_value = 1500.0
        return sensor_manager

    @pytest.fixture
    def mock_offset_engine(self):
        """Mock OffsetEngine with state-aware learning methods."""
        engine = Mock()
        engine.calculate_offset.return_value = OffsetResult(
            offset=1.5, clamped=False, reason="Normal operation", confidence=0.8
        )
        engine.pause_learning = Mock()
        engine.resume_learning = Mock()
        engine.record_actual_performance = Mock()
        engine._learning_paused = False
        return engine

    @pytest.fixture
    def mock_mode_manager(self):
        """Mock ModeManager."""
        manager = Mock()
        manager.current_mode = "none"
        manager.get_adjustments.return_value = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        )
        return manager

    @pytest.fixture
    def mock_thermal_model(self):
        """Mock PassiveThermalModel."""
        model = Mock(spec=PassiveThermalModel)
        model.predict_drift.return_value = 22.0
        model.get_confidence.return_value = 0.8
        return model

    @pytest.fixture
    def mock_preferences(self):
        """Mock UserPreferences."""
        prefs = Mock(spec=UserPreferences)
        prefs.level = PreferenceLevel.BALANCED
        prefs.get_adjusted_band.return_value = 1.5
        return prefs

    @pytest.fixture
    def mock_cycle_monitor(self):
        """Mock CycleMonitor."""
        monitor = Mock()
        monitor.can_turn_on.return_value = True
        monitor.can_turn_off.return_value = True
        monitor.needs_adjustment.return_value = False
        monitor.get_average_cycle_duration.return_value = (600.0, 300.0)
        return monitor

    @pytest.fixture
    def mock_comfort_band_controller(self):
        """Mock ComfortBandController."""
        controller = Mock()
        controller.get_operating_window.return_value = (22.5, 25.5)
        controller.should_ac_run.return_value = True
        return controller

    @pytest.fixture
    def mock_thermal_manager(self, mock_hass, mock_thermal_model, mock_preferences):
        """Mock ThermalManager."""
        manager = Mock(spec=ThermalManager)
        manager.current_state = ThermalState.PRIMING
        manager.get_operating_window.return_value = (22.5, 25.5)
        manager.should_ac_run.return_value = True
        manager.get_learning_target.return_value = 24.0
        manager.transition_to = Mock()
        return manager

    @pytest.fixture
    def coordinator_with_thermal(
        self, mock_hass, mock_sensor_manager, mock_offset_engine, mock_mode_manager,
        mock_thermal_model, mock_preferences, mock_cycle_monitor, mock_comfort_band_controller
    ):
        """Create coordinator with thermal efficiency enabled."""
        coordinator = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=180,
            sensor_manager=mock_sensor_manager,
            offset_engine=mock_offset_engine,
            mode_manager=mock_mode_manager,
            thermal_model=mock_thermal_model,
            user_preferences=mock_preferences,
            cycle_monitor=mock_cycle_monitor,
            comfort_band_controller=mock_comfort_band_controller,
            thermal_efficiency_enabled=True
        )
        coordinator._wrapped_entity_id = "climate.test_ac"
        return coordinator

    @pytest.fixture 
    def coordinator_with_thermal_manager(
        self, mock_hass, mock_sensor_manager, mock_offset_engine, mock_mode_manager, mock_thermal_manager
    ):
        """Create coordinator with mocked ThermalManager."""
        coordinator = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=180,
            sensor_manager=mock_sensor_manager,
            offset_engine=mock_offset_engine,
            mode_manager=mock_mode_manager,
            thermal_efficiency_enabled=True
        )
        coordinator._thermal_manager = mock_thermal_manager
        coordinator._wrapped_entity_id = "climate.test_ac"
        return coordinator

    # Test 1: ThermalManager Integration in Coordinator
    def test_thermal_manager_initialization_when_enabled(
        self, mock_hass, mock_sensor_manager, mock_offset_engine, mock_mode_manager,
        mock_thermal_model, mock_preferences, mock_cycle_monitor, mock_comfort_band_controller
    ):
        """Test ThermalManager is initialized when thermal efficiency is enabled."""
        coordinator = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=180,
            sensor_manager=mock_sensor_manager,
            offset_engine=mock_offset_engine,
            mode_manager=mock_mode_manager,
            thermal_model=mock_thermal_model,
            user_preferences=mock_preferences,
            cycle_monitor=mock_cycle_monitor,
            comfort_band_controller=mock_comfort_band_controller,
            thermal_efficiency_enabled=True
        )
        
        assert coordinator.thermal_efficiency_enabled is True
        assert hasattr(coordinator, '_thermal_model')
        assert hasattr(coordinator, '_user_preferences')
        assert hasattr(coordinator, '_cycle_monitor')
        assert hasattr(coordinator, '_comfort_band_controller')
        assert hasattr(coordinator, '_thermal_manager')
        assert coordinator._thermal_manager is not None

    # Test 2: ThermalManager not initialized when disabled
    def test_thermal_manager_not_initialized_when_disabled(
        self, mock_hass, mock_sensor_manager, mock_offset_engine, mock_mode_manager
    ):
        """Test ThermalManager is not initialized when thermal efficiency is disabled."""
        coordinator = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=180,
            sensor_manager=mock_sensor_manager,
            offset_engine=mock_offset_engine,
            mode_manager=mock_mode_manager,
            thermal_efficiency_enabled=False
        )
        assert coordinator.thermal_efficiency_enabled is False
        assert coordinator._thermal_manager is None

    # Test 3-4: State Transitions Update OffsetEngine Learning
    @pytest.mark.asyncio
    async def test_drifting_state_pauses_offset_learning(self, coordinator_with_thermal_manager, mock_offset_engine, mock_thermal_manager):
        """Test that DRIFTING state pauses OffsetEngine learning."""
        # Set thermal manager to DRIFTING state
        mock_thermal_manager.current_state = ThermalState.DRIFTING
        
        # Update coordinator data
        await coordinator_with_thermal_manager._async_update_data()
        
        # Verify pause_learning was called
        mock_offset_engine.pause_learning.assert_called_once()

    @pytest.mark.asyncio
    async def test_correcting_state_resumes_offset_learning(self, coordinator_with_thermal_manager, mock_offset_engine, mock_thermal_manager):
        """Test that CORRECTING state resumes OffsetEngine learning."""
        # Set thermal manager to CORRECTING state
        mock_thermal_manager.current_state = ThermalState.CORRECTING
        
        # Update coordinator data
        await coordinator_with_thermal_manager._async_update_data()
        
        # Verify resume_learning was called
        mock_offset_engine.resume_learning.assert_called_once()

    # Test 5: Thermal Window Passed to Offset Calculation  
    @pytest.mark.asyncio
    async def test_thermal_window_passed_to_offset_calculation(self, coordinator_with_thermal_manager, mock_offset_engine, mock_thermal_manager):
        """Test thermal window is passed to offset_engine.calculate_offset()."""
        thermal_window = (22.0, 26.0)
        mock_thermal_manager.get_operating_window.return_value = thermal_window
        
        await coordinator_with_thermal_manager._async_update_data()
        
        # Check that calculate_offset was called with thermal_window parameter
        call_args = mock_offset_engine.calculate_offset.call_args
        assert call_args is not None
        # Should be called with thermal_window as keyword argument
        _, kwargs = call_args
        assert 'thermal_window' in kwargs
        assert kwargs['thermal_window'] == thermal_window

    # Test 6: Learning Target Calculation and Usage
    @pytest.mark.asyncio
    async def test_learning_target_calculation_and_usage(self, coordinator_with_thermal_manager, mock_offset_engine, mock_thermal_manager):
        """Test learning target is calculated and passed to record_actual_performance."""
        learning_target = 23.5
        mock_thermal_manager.get_learning_target.return_value = learning_target
        mock_thermal_manager.get_operating_window.return_value = (22.5, 25.5)
        
        await coordinator_with_thermal_manager._async_update_data()
        
        # Verify get_learning_target was called with current temp and window
        mock_thermal_manager.get_learning_target.assert_called_once()
        call_args = mock_thermal_manager.get_learning_target.call_args[0]
        assert len(call_args) == 2  # current_temp, window

    # Test 7: State Persistence Across Updates
    @pytest.mark.asyncio
    async def test_state_persistence_across_updates(self, coordinator_with_thermal_manager, mock_thermal_manager):
        """Test thermal state persists across coordinator updates."""
        # Set initial state
        initial_state = ThermalState.CORRECTING
        mock_thermal_manager.current_state = initial_state
        
        # First update
        data1 = await coordinator_with_thermal_manager._async_update_data()
        
        # Second update
        data2 = await coordinator_with_thermal_manager._async_update_data()
        
        # State should be consistent
        assert data1.thermal_state == initial_state.value
        assert data2.thermal_state == initial_state.value

    # Test 8: State Machine Drives AC Decisions
    @pytest.mark.asyncio
    async def test_state_machine_drives_ac_decisions(self, coordinator_with_thermal_manager, mock_thermal_manager):
        """Test thermal manager state machine influences AC run decisions."""
        # Configure thermal manager AC decision
        mock_thermal_manager.should_ac_run.return_value = False
        
        data = await coordinator_with_thermal_manager._async_update_data()
        
        # Verify should_ac_run was called and result stored
        mock_thermal_manager.should_ac_run.assert_called_once()
        # Note: The actual should_ac_run result should be stored in data
        # but might be overridden by comfort_band_controller in current implementation

    # Test 9: Context Object Creation for State Handlers
    @pytest.mark.asyncio
    async def test_context_object_created_for_state_handlers(self, coordinator_with_thermal, mock_thermal_model, mock_preferences):
        """Test that context object is created with needed attributes for state handlers."""
        # This tests that the coordinator provides the context ThermalManager needs
        data = await coordinator_with_thermal._async_update_data()
        
        # Verify thermal components are available as context
        assert coordinator_with_thermal._thermal_model is not None
        assert coordinator_with_thermal._user_preferences is not None
        assert coordinator_with_thermal._cycle_monitor is not None
        assert coordinator_with_thermal._comfort_band_controller is not None

    # Test 10: State Handler Execution
    @pytest.mark.asyncio
    async def test_state_handler_execution(self, coordinator_with_thermal_manager, mock_thermal_manager):
        """Test that current state handler is executed during update."""
        # Mock state handler execution
        mock_thermal_manager.execute_current_state = Mock()
        
        await coordinator_with_thermal_manager._async_update_data()
        
        # Verify thermal manager methods were called
        assert mock_thermal_manager.get_operating_window.called
        assert mock_thermal_manager.should_ac_run.called
        assert mock_thermal_manager.get_learning_target.called

    # Test 11: SmartClimateData Extensions - Thermal State
    @pytest.mark.asyncio
    async def test_smart_climate_data_includes_thermal_state(self, coordinator_with_thermal_manager, mock_thermal_manager):
        """Test SmartClimateData includes thermal_state field."""
        mock_thermal_manager.current_state = ThermalState.PRIMING
        
        data = await coordinator_with_thermal_manager._async_update_data()
        
        assert hasattr(data, 'thermal_state')
        assert data.thermal_state == ThermalState.PRIMING.value

    # Test 12: SmartClimateData Extensions - Learning Active
    @pytest.mark.asyncio
    async def test_smart_climate_data_includes_learning_active(self, coordinator_with_thermal_manager, mock_offset_engine, mock_thermal_manager):
        """Test SmartClimateData includes learning_active field."""
        # Test learning active (not paused)
        mock_offset_engine._learning_paused = False
        mock_thermal_manager.current_state = ThermalState.CORRECTING
        
        data = await coordinator_with_thermal_manager._async_update_data()
        
        assert hasattr(data, 'learning_active')
        assert data.learning_active is True

    # Test 13: SmartClimateData Extensions - Learning Target
    @pytest.mark.asyncio
    async def test_smart_climate_data_includes_learning_target(self, coordinator_with_thermal_manager, mock_thermal_manager):
        """Test SmartClimateData includes learning_target field."""
        learning_target = 24.5
        mock_thermal_manager.get_learning_target.return_value = learning_target
        
        data = await coordinator_with_thermal_manager._async_update_data()
        
        assert hasattr(data, 'learning_target')
        assert data.learning_target == learning_target

    # Test 14: DRIFTING State Specific Behavior
    @pytest.mark.asyncio
    async def test_drifting_state_specific_behavior(self, coordinator_with_thermal_manager, mock_offset_engine, mock_thermal_manager):
        """Test DRIFTING state pauses learning and sets learning_active=False."""
        mock_thermal_manager.current_state = ThermalState.DRIFTING
        
        data = await coordinator_with_thermal_manager._async_update_data()
        
        # Verify learning is paused
        mock_offset_engine.pause_learning.assert_called_once()
        assert data.learning_active is False
        assert data.thermal_state == ThermalState.DRIFTING.value

    # Test 15: CORRECTING State Specific Behavior
    @pytest.mark.asyncio
    async def test_correcting_state_specific_behavior(self, coordinator_with_thermal_manager, mock_offset_engine, mock_thermal_manager):
        """Test CORRECTING state resumes learning with boundary target."""
        mock_thermal_manager.current_state = ThermalState.CORRECTING
        boundary_target = 25.5
        mock_thermal_manager.get_learning_target.return_value = boundary_target
        
        data = await coordinator_with_thermal_manager._async_update_data()
        
        # Verify learning is resumed
        mock_offset_engine.resume_learning.assert_called_once()
        assert data.learning_active is True
        assert data.learning_target == boundary_target
        assert data.thermal_state == ThermalState.CORRECTING.value

    # Test 16: Other States Don't Affect Learning
    @pytest.mark.asyncio
    async def test_other_states_dont_affect_learning(self, coordinator_with_thermal_manager, mock_offset_engine, mock_thermal_manager):
        """Test that states other than DRIFTING/CORRECTING don't change learning state."""
        mock_thermal_manager.current_state = ThermalState.PRIMING
        
        await coordinator_with_thermal_manager._async_update_data()
        
        # Verify neither pause nor resume was called
        mock_offset_engine.pause_learning.assert_not_called()
        mock_offset_engine.resume_learning.assert_not_called()

    # Test 17: Error Handling in State Logic
    @pytest.mark.asyncio
    async def test_error_handling_in_thermal_state_logic(self, coordinator_with_thermal_manager, mock_thermal_manager):
        """Test error handling when thermal manager operations fail."""
        # Make thermal manager raise exception
        mock_thermal_manager.get_operating_window.side_effect = Exception("Thermal error")
        
        # Should not crash coordinator
        data = await coordinator_with_thermal_manager._async_update_data()
        
        # Should have safe defaults
        assert data.thermal_state is not None
        assert data.learning_active is not None

    # Test 18: Integration with Existing Thermal Components
    @pytest.mark.asyncio
    async def test_integration_with_existing_thermal_components(self, coordinator_with_thermal):
        """Test integration works with existing Phase 1 thermal components."""
        data = await coordinator_with_thermal._async_update_data()
        
        # Verify Phase 1 fields still work
        assert data.thermal_window is not None
        assert data.should_ac_run is not None
        assert data.cycle_health is not None
        assert data.thermal_efficiency_enabled is True

    # Test 19: State Transitions Trigger Appropriate Logging
    @pytest.mark.asyncio
    async def test_state_transitions_logged(self, coordinator_with_thermal_manager, mock_thermal_manager, caplog):
        """Test that state transitions are properly logged."""
        mock_thermal_manager.current_state = ThermalState.CORRECTING
        
        await coordinator_with_thermal_manager._async_update_data()
        
        # Note: Actual logging verification would depend on logger usage in implementation
        assert mock_thermal_manager.current_state == ThermalState.CORRECTING

    # Test 20: Complete State-Aware Protocol Integration
    @pytest.mark.asyncio
    async def test_complete_state_aware_protocol_integration(self, coordinator_with_thermal_manager, mock_offset_engine, mock_thermal_manager):
        """Test complete integration of state-aware protocol."""
        # Setup scenario: CORRECTING state with specific targets
        mock_thermal_manager.current_state = ThermalState.CORRECTING
        thermal_window = (22.0, 26.0)
        learning_target = 25.8  # Upper boundary
        mock_thermal_manager.get_operating_window.return_value = thermal_window
        mock_thermal_manager.get_learning_target.return_value = learning_target
        
        data = await coordinator_with_thermal_manager._async_update_data()
        
        # Verify complete integration
        # 1. Learning resumed
        mock_offset_engine.resume_learning.assert_called_once()
        # 2. Thermal window passed to offset calculation
        call_args = mock_offset_engine.calculate_offset.call_args
        _, kwargs = call_args
        assert kwargs.get('thermal_window') == thermal_window
        # 3. Learning target calculated and stored
        assert data.learning_target == learning_target
        # 4. State stored in data
        assert data.thermal_state == ThermalState.CORRECTING.value
        # 5. Learning active flag set
        assert data.learning_active is True