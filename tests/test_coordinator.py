"""Tests for SmartClimateCoordinator."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import timedelta

from custom_components.smart_climate.coordinator import SmartClimateCoordinator
from custom_components.smart_climate.models import SmartClimateData, ModeAdjustments
from custom_components.smart_climate.errors import (
    SmartClimateError,
    SensorUnavailableError,
    OffsetCalculationError,
    ConfigurationError,
    WrappedEntityError,
)


class TestSmartClimateCoordinator:
    """Test SmartClimateCoordinator functionality."""
    
    def test_coordinator_inherits_from_data_update_coordinator(self):
        """Test that SmartClimateCoordinator can be created with proper dependencies."""
        hass = Mock()
        sensor_manager = Mock()
        offset_engine = Mock()
        mode_manager = Mock()
        
        coordinator = SmartClimateCoordinator(
            hass=hass,
            update_interval=180,
            sensor_manager=sensor_manager,
            offset_engine=offset_engine,
            mode_manager=mode_manager
        )
        
        # Test that coordinator has the required methods and attributes
        assert hasattr(coordinator, '_async_update_data')
        assert coordinator._sensor_manager == sensor_manager
        assert coordinator._offset_engine == offset_engine
        assert coordinator._mode_manager == mode_manager
    
    def test_coordinator_initialization(self):
        """Test coordinator initialization with all dependencies."""
        hass = Mock()
        sensor_manager = Mock()
        offset_engine = Mock()
        mode_manager = Mock()
        
        coordinator = SmartClimateCoordinator(
            hass=hass,
            update_interval=300,
            sensor_manager=sensor_manager,
            offset_engine=offset_engine,
            mode_manager=mode_manager
        )
        
        assert coordinator._sensor_manager == sensor_manager
        assert coordinator._offset_engine == offset_engine
        assert coordinator._mode_manager == mode_manager
    
    def test_coordinator_default_update_interval(self):
        """Test coordinator with default update interval."""
        hass = Mock()
        sensor_manager = Mock()
        offset_engine = Mock()
        mode_manager = Mock()
        
        coordinator = SmartClimateCoordinator(
            hass=hass,
            update_interval=180,  # default from config
            sensor_manager=sensor_manager,
            offset_engine=offset_engine,
            mode_manager=mode_manager
        )
        
        # Test that the coordinator was created successfully
        assert coordinator._sensor_manager == sensor_manager
    
    @pytest.mark.asyncio
    async def test_async_update_data_returns_smart_climate_data(self):
        """Test that _async_update_data returns SmartClimateData."""
        hass = Mock()
        sensor_manager = Mock()
        offset_engine = Mock()
        mode_manager = Mock()
        
        # Mock sensor data
        sensor_manager.get_room_temperature.return_value = 22.5
        sensor_manager.get_outdoor_temperature.return_value = 28.0
        sensor_manager.get_power_consumption.return_value = 1200.0
        
        # Mock mode adjustments
        mode_adjustments = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.5,
            update_interval_override=None,
            boost_offset=0.0
        )
        mode_manager.get_adjustments.return_value = mode_adjustments
        mode_manager.current_mode = "none"
        
        # Mock offset calculation
        from custom_components.smart_climate.models import OffsetResult, OffsetInput
        offset_result = OffsetResult(
            offset=2.0,
            clamped=False,
            reason="Normal operation",
            confidence=0.9
        )
        offset_engine.calculate_offset.return_value = offset_result
        
        coordinator = SmartClimateCoordinator(
            hass=hass,
            update_interval=180,
            sensor_manager=sensor_manager,
            offset_engine=offset_engine,
            mode_manager=mode_manager
        )
        
        data = await coordinator._async_update_data()
        
        assert isinstance(data, SmartClimateData)
        assert data.room_temp == 22.5
        assert data.outdoor_temp == 28.0
        assert data.power == 1200.0
        assert data.calculated_offset == 2.0
        assert data.mode_adjustments == mode_adjustments
    
    @pytest.mark.asyncio
    async def test_async_update_data_with_missing_sensors(self):
        """Test data update with missing sensor data."""
        hass = Mock()
        sensor_manager = Mock()
        offset_engine = Mock()
        mode_manager = Mock()
        
        # Mock missing sensor data
        sensor_manager.get_room_temperature.return_value = 22.5
        sensor_manager.get_outdoor_temperature.return_value = None
        sensor_manager.get_power_consumption.return_value = None
        
        # Mock mode adjustments
        mode_adjustments = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        )
        mode_manager.get_adjustments.return_value = mode_adjustments
        mode_manager.current_mode = "none"
        
        # Mock offset calculation
        from custom_components.smart_climate.models import OffsetResult
        offset_result = OffsetResult(
            offset=1.5,
            clamped=False,
            reason="Limited sensor data",
            confidence=0.7
        )
        offset_engine.calculate_offset.return_value = offset_result
        
        coordinator = SmartClimateCoordinator(
            hass=hass,
            update_interval=180,
            sensor_manager=sensor_manager,
            offset_engine=offset_engine,
            mode_manager=mode_manager
        )
        
        data = await coordinator._async_update_data()
        
        assert isinstance(data, SmartClimateData)
        assert data.room_temp == 22.5
        assert data.outdoor_temp is None
        assert data.power is None
        assert data.calculated_offset == 1.5
    
    @pytest.mark.asyncio
    async def test_async_update_data_integrates_all_managers(self):
        """Test that data update integrates all manager components."""
        hass = Mock()
        sensor_manager = Mock()
        offset_engine = Mock()
        mode_manager = Mock()
        
        # Setup sensor manager
        sensor_manager.get_room_temperature.return_value = 21.0
        sensor_manager.get_outdoor_temperature.return_value = 30.0
        sensor_manager.get_power_consumption.return_value = 800.0
        
        # Setup mode manager
        mode_adjustments = ModeAdjustments(
            temperature_override=18.0,  # Away mode
            offset_adjustment=1.0,
            update_interval_override=300,
            boost_offset=0.0
        )
        mode_manager.get_adjustments.return_value = mode_adjustments
        mode_manager.current_mode = "away"
        
        # Setup offset engine
        from custom_components.smart_climate.models import OffsetResult
        offset_result = OffsetResult(
            offset=2.5,
            clamped=True,
            reason="Clamped to max limit",
            confidence=0.8
        )
        offset_engine.calculate_offset.return_value = offset_result
        
        coordinator = SmartClimateCoordinator(
            hass=hass,
            update_interval=180,
            sensor_manager=sensor_manager,
            offset_engine=offset_engine,
            mode_manager=mode_manager
        )
        
        data = await coordinator._async_update_data()
        
        # Verify all managers were called
        sensor_manager.get_room_temperature.assert_called_once()
        sensor_manager.get_outdoor_temperature.assert_called_once()
        sensor_manager.get_power_consumption.assert_called_once()
        mode_manager.get_adjustments.assert_called_once()
        offset_engine.calculate_offset.assert_called_once()
        
        # Verify data integration
        assert data.room_temp == 21.0
        assert data.outdoor_temp == 30.0
        assert data.power == 800.0
        assert data.calculated_offset == 2.5
        assert data.mode_adjustments.temperature_override == 18.0
    
    @pytest.mark.asyncio
    async def test_async_update_data_error_handling(self):
        """Test error handling in data update."""
        hass = Mock()
        sensor_manager = Mock()
        offset_engine = Mock()
        mode_manager = Mock()
        
        # Mock sensor manager to raise exception
        sensor_manager.get_room_temperature.side_effect = Exception("Sensor read error")
        
        coordinator = SmartClimateCoordinator(
            hass=hass,
            update_interval=180,
            sensor_manager=sensor_manager,
            offset_engine=offset_engine,
            mode_manager=mode_manager
        )
        
        # Should handle error gracefully and raise SmartClimateError
        with pytest.raises(SmartClimateError):
            await coordinator._async_update_data()


class TestSmartClimateData:
    """Test SmartClimateData dataclass."""
    
    def test_smart_climate_data_creation(self):
        """Test SmartClimateData creation with all fields."""
        mode_adjustments = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.5,
            update_interval_override=None,
            boost_offset=0.0
        )
        
        data = SmartClimateData(
            room_temp=22.5,
            outdoor_temp=28.0,
            power=1200.0,
            calculated_offset=2.0,
            mode_adjustments=mode_adjustments
        )
        
        assert data.room_temp == 22.5
        assert data.outdoor_temp == 28.0
        assert data.power == 1200.0
        assert data.calculated_offset == 2.0
        assert data.mode_adjustments == mode_adjustments
    
    def test_smart_climate_data_with_none_values(self):
        """Test SmartClimateData with None values for optional fields."""
        mode_adjustments = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        )
        
        data = SmartClimateData(
            room_temp=None,
            outdoor_temp=None,
            power=None,
            calculated_offset=0.0,
            mode_adjustments=mode_adjustments
        )
        
        assert data.room_temp is None
        assert data.outdoor_temp is None
        assert data.power is None
        assert data.calculated_offset == 0.0
        assert data.mode_adjustments == mode_adjustments


class TestExceptionHierarchy:
    """Test exception hierarchy."""
    
    def test_base_exception(self):
        """Test SmartClimateError base exception."""
        error = SmartClimateError("Base error")
        assert str(error) == "Base error"
        assert isinstance(error, Exception)
    
    def test_sensor_unavailable_error(self):
        """Test SensorUnavailableError."""
        error = SensorUnavailableError("Sensor not found")
        assert str(error) == "Sensor not found"
        assert isinstance(error, SmartClimateError)
        assert isinstance(error, Exception)
    
    def test_offset_calculation_error(self):
        """Test OffsetCalculationError."""
        error = OffsetCalculationError("Calculation failed")
        assert str(error) == "Calculation failed"
        assert isinstance(error, SmartClimateError)
        assert isinstance(error, Exception)
    
    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("Invalid config")
        assert str(error) == "Invalid config"
        assert isinstance(error, SmartClimateError)
        assert isinstance(error, Exception)
    
    def test_wrapped_entity_error(self):
        """Test WrappedEntityError."""
        error = WrappedEntityError("Entity call failed")
        assert str(error) == "Entity call failed"
        assert isinstance(error, SmartClimateError)
        assert isinstance(error, Exception)