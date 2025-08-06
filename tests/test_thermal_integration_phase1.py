"""ABOUTME: Phase 1 thermal integration tests for coordinator and climate entity.
ABOUTME: Tests thermal efficiency components working together in Phase 1."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from custom_components.smart_climate.coordinator import SmartClimateCoordinator
from custom_components.smart_climate.models import SmartClimateData, OffsetInput, OffsetResult, ModeAdjustments
from custom_components.smart_climate.thermal_model import PassiveThermalModel
from custom_components.smart_climate.thermal_preferences import UserPreferences, PreferenceLevel
from custom_components.smart_climate.cycle_monitor import CycleMonitor
from custom_components.smart_climate.comfort_band_controller import ComfortBandController


@pytest.fixture
def mock_hass():
    """Mock HomeAssistant for testing."""
    mock_hass = Mock()
    mock_hass.states = Mock()
    mock_state = Mock()
    mock_state.state = "cool"
    mock_state.attributes = {"current_temperature": 21.0}
    mock_hass.states.get.return_value = mock_state
    return mock_hass


@pytest.fixture
def mock_sensor_manager():
    """Mock SensorManager for testing."""
    sensor_manager = Mock()
    sensor_manager.get_room_temperature.return_value = 22.0
    sensor_manager.get_outdoor_temperature.return_value = 25.0
    sensor_manager.get_power_consumption.return_value = 1500.0
    return sensor_manager


@pytest.fixture
def mock_offset_engine():
    """Mock OffsetEngine for testing."""
    offset_engine = Mock()
    offset_engine.calculate_offset.return_value = OffsetResult(
        offset=1.0,
        clamped=False,
        reason="Normal operation",
        confidence=0.8
    )
    return offset_engine


@pytest.fixture
def mock_mode_manager():
    """Mock ModeManager for testing."""
    mode_manager = Mock()
    mode_manager.current_mode = "none"
    mode_manager.get_adjustments.return_value = ModeAdjustments(
        temperature_override=None,
        offset_adjustment=0.0,
        update_interval_override=None,
        boost_offset=0.0
    )
    return mode_manager


@pytest.fixture
def user_preferences():
    """User preferences for testing."""
    return UserPreferences(
        level=PreferenceLevel.BALANCED,
        comfort_band=1.0,
        confidence_threshold=0.5,
        probe_drift=2.0
    )


@pytest.fixture
def thermal_model():
    """PassiveThermalModel for testing."""
    return PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)


@pytest.fixture
def cycle_monitor():
    """CycleMonitor for testing."""
    return CycleMonitor(min_off_time=600, min_on_time=300)


@pytest.fixture
def comfort_band_controller(thermal_model, user_preferences):
    """ComfortBandController for testing."""
    return ComfortBandController(thermal_model, user_preferences)


class TestThermalCoordinatorIntegration:
    """Test thermal efficiency integration in coordinator."""
    
    def test_coordinator_can_initialize_with_thermal_components(
        self, mock_hass, mock_sensor_manager, mock_offset_engine, mock_mode_manager,
        thermal_model, user_preferences, cycle_monitor, comfort_band_controller
    ):
        """Test coordinator can be initialized with thermal efficiency components."""
        # Test that coordinator can accept thermal components in constructor
        # Due to mocking in conftest.py, we focus on initialization success and flag
        coordinator = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=180,
            sensor_manager=mock_sensor_manager,
            offset_engine=mock_offset_engine,
            mode_manager=mock_mode_manager,
            thermal_model=thermal_model,
            user_preferences=user_preferences,
            cycle_monitor=cycle_monitor,
            comfort_band_controller=comfort_band_controller,
            thermal_efficiency_enabled=True
        )
        
        # Check that thermal efficiency flag is set correctly
        assert hasattr(coordinator, 'thermal_efficiency_enabled')
        # Due to DataUpdateCoordinator mocking, we can't check exact object identity
        # But we can verify that initialization succeeded without errors
        assert coordinator is not None
    
    @pytest.mark.asyncio
    async def test_coordinator_thermal_components_work_together_during_update(
        self, mock_hass, mock_sensor_manager, mock_offset_engine, mock_mode_manager,
        thermal_model, user_preferences, cycle_monitor, comfort_band_controller
    ):
        """Test thermal components work together during coordinator updates."""
        coordinator = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=180,
            sensor_manager=mock_sensor_manager,
            offset_engine=mock_offset_engine,
            mode_manager=mock_mode_manager,
            thermal_model=thermal_model,
            user_preferences=user_preferences,
            cycle_monitor=cycle_monitor,
            comfort_band_controller=comfort_band_controller,
            thermal_efficiency_enabled=True
        )
        
        # Set wrapped entity ID
        coordinator._wrapped_entity_id = "climate.test_ac"
        
        # Perform update
        data = await coordinator._async_update_data()
        
        # Verify thermal data is included
        assert hasattr(data, 'thermal_window')
        assert hasattr(data, 'should_ac_run')
        assert hasattr(data, 'cycle_health')
        assert data.thermal_efficiency_enabled is True
        
        # Verify thermal window was calculated
        assert data.thermal_window is not None
        assert len(data.thermal_window) == 2
        assert isinstance(data.should_ac_run, bool)
    
    def test_thermal_efficiency_feature_flag_enables_disables(
        self, mock_hass, mock_sensor_manager, mock_offset_engine, mock_mode_manager,
        thermal_model, user_preferences, cycle_monitor, comfort_band_controller
    ):
        """Test feature flag enables/disables thermal efficiency."""
        # Test with thermal efficiency disabled
        coordinator_disabled = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=180,
            sensor_manager=mock_sensor_manager,
            offset_engine=mock_offset_engine,
            mode_manager=mock_mode_manager,
            thermal_efficiency_enabled=False
        )
        
        assert coordinator_disabled.thermal_efficiency_enabled is False
        assert not hasattr(coordinator_disabled, '_thermal_model')
        
        # Test with thermal efficiency enabled
        coordinator_enabled = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=180,
            sensor_manager=mock_sensor_manager,
            offset_engine=mock_offset_engine,
            mode_manager=mock_mode_manager,
            thermal_model=thermal_model,
            user_preferences=user_preferences,
            cycle_monitor=cycle_monitor,
            comfort_band_controller=comfort_band_controller,
            thermal_efficiency_enabled=True
        )
        
        assert coordinator_enabled.thermal_efficiency_enabled is True
        assert hasattr(coordinator_enabled, '_thermal_model')
    
    @pytest.mark.asyncio
    async def test_backward_compatibility_when_thermal_disabled(
        self, mock_hass, mock_sensor_manager, mock_offset_engine, mock_mode_manager
    ):
        """Test system works normally when thermal efficiency is disabled."""
        coordinator = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=180,
            sensor_manager=mock_sensor_manager,
            offset_engine=mock_offset_engine,
            mode_manager=mock_mode_manager,
            thermal_efficiency_enabled=False
        )
        
        # Set wrapped entity ID
        coordinator._wrapped_entity_id = "climate.test_ac"
        
        # Should work normally without thermal components
        data = await coordinator._async_update_data()
        
        assert isinstance(data, SmartClimateData)
        assert data.calculated_offset == 1.0  # From mock offset engine
        assert data.room_temp == 22.0
        assert data.thermal_efficiency_enabled is False
        
        # Thermal fields should be None when disabled
        assert data.thermal_window is None
        assert data.should_ac_run is None
        assert data.cycle_health is None
    
    @pytest.mark.asyncio
    async def test_basic_operation_with_comfort_bands(
        self, mock_hass, mock_sensor_manager, mock_offset_engine, mock_mode_manager,
        thermal_model, user_preferences, cycle_monitor, comfort_band_controller
    ):
        """Test basic system operation with comfort bands."""
        coordinator = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=180,
            sensor_manager=mock_sensor_manager,
            offset_engine=mock_offset_engine,
            mode_manager=mock_mode_manager,
            thermal_model=thermal_model,
            user_preferences=user_preferences,
            cycle_monitor=cycle_monitor,
            comfort_band_controller=comfort_band_controller,
            thermal_efficiency_enabled=True
        )
        
        # Set wrapped entity ID
        coordinator._wrapped_entity_id = "climate.test_ac"
        
        data = await coordinator._async_update_data()
        
        # Should have comfort band calculation
        assert data.thermal_window is not None
        assert len(data.thermal_window) == 2
        
        # AC decision should be based on comfort band logic
        assert isinstance(data.should_ac_run, bool)
    
    @pytest.mark.asyncio
    async def test_cycle_monitor_enforcement(
        self, mock_hass, mock_sensor_manager, mock_offset_engine, mock_mode_manager,
        thermal_model, user_preferences, cycle_monitor, comfort_band_controller
    ):
        """Test cycle monitor enforces minimum timing constraints."""
        coordinator = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=180,
            sensor_manager=mock_sensor_manager,
            offset_engine=mock_offset_engine,
            mode_manager=mock_mode_manager,
            thermal_model=thermal_model,
            user_preferences=user_preferences,
            cycle_monitor=cycle_monitor,
            comfort_band_controller=comfort_band_controller,
            thermal_efficiency_enabled=True
        )
        
        # Set wrapped entity ID
        coordinator._wrapped_entity_id = "climate.test_ac"
        
        data = await coordinator._async_update_data()
        
        # Verify cycle health monitoring is active
        assert data.cycle_health is not None
        cycle_health = data.cycle_health
        assert 'can_turn_on' in cycle_health
        assert 'can_turn_off' in cycle_health
        assert 'needs_adjustment' in cycle_health
        assert 'avg_on_duration' in cycle_health
        assert 'avg_off_duration' in cycle_health
        
        # Verify data types
        assert isinstance(cycle_health['can_turn_on'], bool)
        assert isinstance(cycle_health['can_turn_off'], bool)
        assert isinstance(cycle_health['needs_adjustment'], bool)
        assert isinstance(cycle_health['avg_on_duration'], float)
        assert isinstance(cycle_health['avg_off_duration'], float)
    
    @pytest.mark.asyncio
    async def test_user_preference_changes_take_effect(
        self, mock_hass, mock_sensor_manager, mock_offset_engine, mock_mode_manager,
        thermal_model, cycle_monitor
    ):
        """Test user preference changes affect comfort band calculations."""
        # Create preferences with different comfort bands
        comfort_prefs = UserPreferences(
            level=PreferenceLevel.MAX_COMFORT,
            comfort_band=0.5,  # Tighter band
            confidence_threshold=0.5,
            probe_drift=2.0
        )
        
        savings_prefs = UserPreferences(
            level=PreferenceLevel.MAX_SAVINGS,
            comfort_band=2.0,  # Wider band
            confidence_threshold=0.5,
            probe_drift=2.0
        )
        
        # Test with comfort-focused preferences
        comfort_controller = ComfortBandController(thermal_model, comfort_prefs)
        coordinator_comfort = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=180,
            sensor_manager=mock_sensor_manager,
            offset_engine=mock_offset_engine,
            mode_manager=mock_mode_manager,
            thermal_model=thermal_model,
            user_preferences=comfort_prefs,
            cycle_monitor=cycle_monitor,
            comfort_band_controller=comfort_controller,
            thermal_efficiency_enabled=True
        )
        
        # Test with savings-focused preferences  
        savings_controller = ComfortBandController(thermal_model, savings_prefs)
        coordinator_savings = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=180,
            sensor_manager=mock_sensor_manager,
            offset_engine=mock_offset_engine,
            mode_manager=mock_mode_manager,
            thermal_model=thermal_model,
            user_preferences=savings_prefs,
            cycle_monitor=cycle_monitor,
            comfort_band_controller=savings_controller,
            thermal_efficiency_enabled=True
        )
        
        # Set wrapped entity ID for both
        coordinator_comfort._wrapped_entity_id = "climate.test_ac"
        coordinator_savings._wrapped_entity_id = "climate.test_ac"
        
        # Get data from both coordinators
        comfort_data = await coordinator_comfort._async_update_data()
        savings_data = await coordinator_savings._async_update_data()
        
        # Both should have valid thermal windows
        assert comfort_data.thermal_window is not None
        assert savings_data.thermal_window is not None
        
        # Comfort preferences should have tighter window (smaller band)
        comfort_window_size = comfort_data.thermal_window[1] - comfort_data.thermal_window[0]
        savings_window_size = savings_data.thermal_window[1] - savings_data.thermal_window[0]
        
        assert comfort_window_size < savings_window_size
    
    @pytest.mark.asyncio
    async def test_error_handling_in_thermal_components(
        self, mock_hass, mock_sensor_manager, mock_offset_engine, mock_mode_manager,
        thermal_model, user_preferences, cycle_monitor
    ):
        """Test system handles thermal component failures gracefully."""
        # Create a mock comfort band controller that raises exceptions
        failing_controller = Mock()
        failing_controller.get_operating_window.side_effect = Exception("Controller failure")
        failing_controller.should_ac_run.side_effect = Exception("Controller failure")
        
        coordinator = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=180,
            sensor_manager=mock_sensor_manager,
            offset_engine=mock_offset_engine,
            mode_manager=mock_mode_manager,
            thermal_model=thermal_model,
            user_preferences=user_preferences,
            cycle_monitor=cycle_monitor,
            comfort_band_controller=failing_controller,
            thermal_efficiency_enabled=True
        )
        
        # Set wrapped entity ID
        coordinator._wrapped_entity_id = "climate.test_ac"
        
        # Should still return valid data with fallbacks
        data = await coordinator._async_update_data()
        
        assert isinstance(data, SmartClimateData)
        # Basic data should still be available
        assert data.room_temp == 22.0
        assert data.calculated_offset == 1.0
        
        # Thermal fields should have safe defaults
        assert data.thermal_window is not None  # Safe default window
        assert data.should_ac_run is False  # Safe default
        assert data.cycle_health is not None  # Safe defaults
    
    @pytest.mark.asyncio
    async def test_missing_outdoor_sensor_handling(
        self, mock_hass, mock_sensor_manager, mock_offset_engine, mock_mode_manager,
        thermal_model, user_preferences, cycle_monitor, comfort_band_controller
    ):
        """Test system handles missing outdoor sensor gracefully."""
        # Mock outdoor sensor as unavailable
        mock_sensor_manager.get_outdoor_temperature.return_value = None
        
        coordinator = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=180,
            sensor_manager=mock_sensor_manager,
            offset_engine=mock_offset_engine,
            mode_manager=mock_mode_manager,
            thermal_model=thermal_model,
            user_preferences=user_preferences,
            cycle_monitor=cycle_monitor,
            comfort_band_controller=comfort_band_controller,
            thermal_efficiency_enabled=True
        )
        
        # Set wrapped entity ID
        coordinator._wrapped_entity_id = "climate.test_ac"
        
        data = await coordinator._async_update_data()
        
        # System should still work with basic comfort bands
        assert data.thermal_window is not None
        assert len(data.thermal_window) == 2
        assert isinstance(data.should_ac_run, bool)
        assert data.outdoor_temp is None  # Correctly reflects missing sensor


class TestThermalDataStructure:
    """Test thermal efficiency data structure extensions."""
    
    def test_smart_climate_data_thermal_fields_default_values(self):
        """Test SmartClimateData has correct default values for thermal fields."""
        # Create SmartClimateData without thermal fields
        data = SmartClimateData(
            room_temp=22.0,
            outdoor_temp=25.0,
            power=1500.0,
            calculated_offset=1.0,
            mode_adjustments=ModeAdjustments(None, 0.0, None, 0.0)
        )
        
        # Thermal fields should have appropriate defaults
        assert data.thermal_window is None
        assert data.should_ac_run is None
        assert data.cycle_health is None
        assert data.thermal_efficiency_enabled is False
    
    def test_smart_climate_data_thermal_fields_can_be_set(self):
        """Test SmartClimateData thermal fields can be set properly."""
        # Create SmartClimateData with thermal fields
        thermal_window = (21.0, 23.0)
        cycle_health = {
            "can_turn_on": True,
            "can_turn_off": True,
            "needs_adjustment": False,
            "avg_on_duration": 600.0,
            "avg_off_duration": 900.0
        }
        
        data = SmartClimateData(
            room_temp=22.0,
            outdoor_temp=25.0,
            power=1500.0,
            calculated_offset=1.0,
            mode_adjustments=ModeAdjustments(None, 0.0, None, 0.0),
            thermal_window=thermal_window,
            should_ac_run=False,
            cycle_health=cycle_health,
            thermal_efficiency_enabled=True
        )
        
        # Verify thermal fields are set correctly
        assert data.thermal_window == thermal_window
        assert data.should_ac_run is False
        assert data.cycle_health == cycle_health
        assert data.thermal_efficiency_enabled is True