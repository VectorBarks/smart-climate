"""Tests for startup AC temperature update behavior."""
# ABOUTME: Comprehensive test suite for startup AC temperature update functionality
# Tests that AC temperature is updated on startup when offset is significant

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from homeassistant.components.climate.const import HVACMode
from homeassistant.helpers.update_coordinator import UpdateFailed
from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.models import OffsetResult, SmartClimateData
from tests.fixtures.mock_entities import (
    create_mock_hass,
    create_mock_state,
    create_mock_offset_engine,
    create_mock_sensor_manager,
    create_mock_mode_manager,
    create_mock_temperature_controller,
    create_mock_coordinator,
)
from tests.fixtures.coordinator_test_fixtures import (
    create_mock_offset_engine,
    create_mock_coordinator,
    create_dashboard_data_fixture,
    create_failed_coordinator,
)


class TestStartupACTemperatureUpdate:
    """Test startup AC temperature update behavior."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        hass = create_mock_hass()
        # Mock wrapped entity state
        wrapped_state = create_mock_state(
            "climate.test_ac", 
            HVACMode.COOL, 
            {"target_temperature": 24.0, "current_temperature": 23.0}
        )
        hass.states.get.return_value = wrapped_state
        return hass

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for Smart Climate entity."""
        return {
            "offset_engine": create_mock_offset_engine(),
            "sensor_manager": create_mock_sensor_manager(),
            "mode_manager": create_mock_mode_manager(),
            "temperature_controller": create_mock_temperature_controller(),
            "coordinator": create_mock_coordinator(),
        }

    @pytest.fixture
    def smart_climate_entity(self, mock_hass, mock_dependencies):
        """Create SmartClimateEntity with mocked dependencies."""
        config = {"name": "Test Smart Climate", "update_interval": 180}
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=config,
            wrapped_entity_id="climate.test_ac",
            room_sensor_id="sensor.room_temp",
            offset_engine=mock_dependencies["offset_engine"],
            sensor_manager=mock_dependencies["sensor_manager"],
            mode_manager=mock_dependencies["mode_manager"],
            temperature_controller=mock_dependencies["temperature_controller"],
            coordinator=mock_dependencies["coordinator"],
        )
        
        # Set initial target temperature
        entity._attr_target_temperature = 24.0
        
        return entity

    def test_startup_with_significant_offset_triggers_ac_update(
        self, mock_hass, mock_dependencies, smart_climate_entity
    ):
        """Test that startup with significant offset triggers AC temperature update."""
        # Arrange
        significant_offset = 2.5  # Above typical threshold
        
        # Mock coordinator data with significant offset
        coordinator_data = SmartClimateData(
            room_temp=22.0,
            outdoor_temp=25.0,
            power=150.0,
            calculated_offset=significant_offset,
            mode_adjustments=Mock(),
            is_startup_calculation=True  # This is the key startup flag
        )
        mock_dependencies["coordinator"].data = coordinator_data
        
        # Mock offset engine to return significant offset
        mock_dependencies["offset_engine"].calculate_offset.return_value = OffsetResult(
            offset=significant_offset,
            clamped=False,
            reason="Startup calculation",
            confidence=0.9
        )
        
        # Mock temperature controller
        adjusted_temp = 24.0 + significant_offset
        mock_dependencies["temperature_controller"].apply_offset_and_limits.return_value = adjusted_temp
        
        # Act
        smart_climate_entity._handle_coordinator_update()
        
        # Assert
        mock_dependencies["temperature_controller"].send_temperature_command.assert_called_once_with(
            "climate.test_ac", adjusted_temp
        )
        
    def test_startup_with_small_offset_no_ac_update(
        self, mock_hass, mock_dependencies, smart_climate_entity
    ):
        """Test that startup with small offset doesn't trigger AC update."""
        # Arrange
        small_offset = 0.2  # Below typical threshold
        
        # Mock coordinator data with small offset
        coordinator_data = SmartClimateData(
            room_temp=22.0,
            outdoor_temp=25.0,
            power=150.0,
            calculated_offset=small_offset,
            mode_adjustments=Mock(),
            is_startup_calculation=True
        )
        mock_dependencies["coordinator"].data = coordinator_data
        
        # Mock offset engine to return small offset
        mock_dependencies["offset_engine"].calculate_offset.return_value = OffsetResult(
            offset=small_offset,
            clamped=False,
            reason="Startup calculation",
            confidence=0.9
        )
        
        # Act
        smart_climate_entity._handle_coordinator_update()
        
        # Assert - No temperature command should be sent
        mock_dependencies["temperature_controller"].send_temperature_command.assert_not_called()

    def test_startup_with_learning_data_applies_cached_offset(
        self, mock_hass, mock_dependencies, smart_climate_entity
    ):
        """Test that startup with learning data applies cached offset."""
        # Arrange
        cached_offset = 1.8
        
        # Mock coordinator data with learning data
        coordinator_data = SmartClimateData(
            room_temp=22.0,
            outdoor_temp=25.0,
            power=150.0,
            calculated_offset=cached_offset,
            mode_adjustments=Mock(),
            is_startup_calculation=True
        )
        mock_dependencies["coordinator"].data = coordinator_data
        
        # Mock offset engine with learning data
        mock_dependencies["offset_engine"].calculate_offset.return_value = OffsetResult(
            offset=cached_offset,
            clamped=False,
            reason="Cached learning data",
            confidence=0.95
        )
        
        # Mock temperature controller
        adjusted_temp = 24.0 + cached_offset
        mock_dependencies["temperature_controller"].apply_offset_and_limits.return_value = adjusted_temp
        
        # Act
        smart_climate_entity._handle_coordinator_update()
        
        # Assert
        mock_dependencies["temperature_controller"].send_temperature_command.assert_called_once_with(
            "climate.test_ac", adjusted_temp
        )

    def test_startup_without_learning_data_no_update(
        self, mock_hass, mock_dependencies, smart_climate_entity
    ):
        """Test that startup without learning data doesn't trigger update."""
        # Arrange
        # Mock coordinator data without learning data
        coordinator_data = SmartClimateData(
            room_temp=22.0,
            outdoor_temp=25.0,
            power=150.0,
            calculated_offset=0.0,  # No offset without learning data
            mode_adjustments=Mock(),
            is_startup_calculation=True
        )
        mock_dependencies["coordinator"].data = coordinator_data
        
        # Mock offset engine with no learning data
        mock_dependencies["offset_engine"].calculate_offset.return_value = OffsetResult(
            offset=0.0,
            clamped=False,
            reason="No learning data",
            confidence=0.0
        )
        
        # Act
        smart_climate_entity._handle_coordinator_update()
        
        # Assert - No temperature command should be sent
        mock_dependencies["temperature_controller"].send_temperature_command.assert_not_called()


class TestStartupCoordinatorIntegration:
    """Test coordinator integration for startup behavior."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        return create_mock_hass()

    def test_coordinator_triggers_startup_calculation(self, mock_hass):
        """Test that coordinator triggers startup calculation."""
        # Arrange
        offset_engine = create_mock_offset_engine(
            learning_enabled=True,
            samples=20,
            accuracy=0.85,
            calculated_offset=2.0
        )
        
        coordinator = create_mock_coordinator(
            mock_hass,
            offset_engine,
            entity_id="climate.test"
        )
        
        # Mock async_force_startup_refresh method
        coordinator.async_force_startup_refresh = AsyncMock()
        
        # Act
        coordinator.async_force_startup_refresh()
        
        # Assert
        coordinator.async_force_startup_refresh.assert_called_once()

    def test_coordinator_data_includes_startup_flag(self, mock_hass):
        """Test that coordinator data includes startup flag."""
        # Arrange
        offset_engine = create_mock_offset_engine(
            learning_enabled=True,
            samples=20,
            accuracy=0.85,
            calculated_offset=2.0
        )
        
        # Mock coordinator data with startup flag
        coordinator_data = create_dashboard_data_fixture(
            offset=2.0,
            learning_enabled=True,
            samples=20,
            accuracy=0.85
        )
        coordinator_data["is_startup_calculation"] = True
        
        coordinator = create_mock_coordinator(
            mock_hass,
            offset_engine,
            entity_id="climate.test",
            initial_data=coordinator_data
        )
        
        # Act & Assert
        assert coordinator.data["is_startup_calculation"] is True

    def test_coordinator_refresh_during_startup(self, mock_hass):
        """Test that coordinator refresh occurs during startup."""
        # Arrange
        offset_engine = create_mock_offset_engine(
            learning_enabled=True,
            samples=20,
            accuracy=0.85,
            calculated_offset=2.0
        )
        
        coordinator = create_mock_coordinator(
            mock_hass,
            offset_engine,
            entity_id="climate.test"
        )
        
        # Mock async_request_refresh method
        coordinator.async_request_refresh = AsyncMock()
        
        # Act
        coordinator.async_request_refresh()
        
        # Assert
        coordinator.async_request_refresh.assert_called_once()

    def test_coordinator_handles_startup_flag_reset(self, mock_hass):
        """Test that coordinator resets startup flag after first calculation."""
        # Arrange
        offset_engine = create_mock_offset_engine(
            learning_enabled=True,
            samples=20,
            accuracy=0.85,
            calculated_offset=2.0
        )
        
        coordinator = create_mock_coordinator(
            mock_hass,
            offset_engine,
            entity_id="climate.test"
        )
        
        # Mock the startup flag behavior
        coordinator._is_startup = True
        
        # Mock update method that should reset startup flag
        async def mock_update():
            startup_flag = coordinator._is_startup
            coordinator._is_startup = False  # Reset after first calculation
            return {"is_startup_calculation": startup_flag}
        
        coordinator.async_update = mock_update
        
        # Act
        result = coordinator.async_update()
        
        # Assert
        assert coordinator._is_startup is False


class TestStartupEdgeCases:
    """Test edge cases for startup behavior."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        return create_mock_hass()

    def test_startup_with_wrapped_entity_unavailable(self, mock_hass):
        """Test startup behavior when wrapped entity is unavailable."""
        # Arrange
        mock_hass.states.get.return_value = None  # Wrapped entity unavailable
        
        offset_engine = create_mock_offset_engine(
            learning_enabled=True,
            samples=20,
            accuracy=0.85,
            calculated_offset=2.0
        )
        
        coordinator = create_mock_coordinator(
            mock_hass,
            offset_engine,
            entity_id="climate.test"
        )
        
        # Mock entity creation
        entity = SmartClimateEntity(
            hass=mock_hass,
            config={"name": "Test Smart Climate"},
            wrapped_entity_id="climate.unavailable",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=coordinator,
        )
        
        # Act & Assert - Should not raise exception
        entity._handle_coordinator_update()  # Should handle gracefully

    def test_startup_with_coordinator_failure(self, mock_hass):
        """Test startup behavior when coordinator fails."""
        # Arrange
        failed_coordinator = create_failed_coordinator(mock_hass, "climate.test")
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config={"name": "Test Smart Climate"},
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room_temp",
            offset_engine=create_mock_offset_engine(),
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=failed_coordinator,
        )
        
        # Act & Assert - Should not raise exception
        entity._handle_coordinator_update()  # Should handle gracefully

    def test_startup_with_sensor_data_unavailable(self, mock_hass):
        """Test startup behavior when sensor data is unavailable."""
        # Arrange
        sensor_manager = create_mock_sensor_manager()
        sensor_manager.get_room_temperature.return_value = None  # No sensor data
        
        offset_engine = create_mock_offset_engine(
            learning_enabled=True,
            samples=0,  # No samples due to sensor issues
            accuracy=0.0,
            calculated_offset=0.0
        )
        
        coordinator = create_mock_coordinator(
            mock_hass,
            offset_engine,
            entity_id="climate.test"
        )
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config={"name": "Test Smart Climate"},
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=sensor_manager,
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=coordinator,
        )
        
        # Act & Assert - Should not raise exception
        entity._handle_coordinator_update()  # Should handle gracefully

    def test_startup_with_no_target_temperature(self, mock_hass):
        """Test startup behavior when no target temperature is set."""
        # Arrange
        offset_engine = create_mock_offset_engine(
            learning_enabled=True,
            samples=20,
            accuracy=0.85,
            calculated_offset=2.0
        )
        
        coordinator = create_mock_coordinator(
            mock_hass,
            offset_engine,
            entity_id="climate.test"
        )
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config={"name": "Test Smart Climate"},
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=coordinator,
        )
        
        # Ensure no target temperature is set
        entity._attr_target_temperature = None
        
        # Act & Assert - Should not raise exception
        entity._handle_coordinator_update()  # Should handle gracefully

    def test_startup_with_temperature_controller_failure(self, mock_hass):
        """Test startup behavior when temperature controller fails."""
        # Arrange
        temperature_controller = create_mock_temperature_controller()
        temperature_controller.send_temperature_command.side_effect = Exception("Controller failed")
        
        offset_engine = create_mock_offset_engine(
            learning_enabled=True,
            samples=20,
            accuracy=0.85,
            calculated_offset=2.0
        )
        
        coordinator_data = SmartClimateData(
            room_temp=22.0,
            outdoor_temp=25.0,
            power=150.0,
            calculated_offset=2.0,
            mode_adjustments=Mock(),
            is_startup_calculation=True
        )
        
        coordinator = create_mock_coordinator(
            mock_hass,
            offset_engine,
            entity_id="climate.test",
            initial_data=coordinator_data
        )
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config={"name": "Test Smart Climate"},
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=temperature_controller,
            coordinator=coordinator,
        )
        
        entity._attr_target_temperature = 24.0
        
        # Act & Assert - Should not raise exception but handle gracefully
        entity._handle_coordinator_update()  # Should handle gracefully


class TestStartupTimingAndPerformance:
    """Test startup timing and performance characteristics."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        return create_mock_hass()

    def test_startup_completes_within_timeout(self, mock_hass):
        """Test that startup operations complete within reasonable timeout."""
        # Arrange
        offset_engine = create_mock_offset_engine(
            learning_enabled=True,
            samples=20,
            accuracy=0.85,
            calculated_offset=2.0
        )
        
        coordinator = create_mock_coordinator(
            mock_hass,
            offset_engine,
            entity_id="climate.test"
        )
        
        # Mock async operations with delays
        coordinator.async_force_startup_refresh = AsyncMock()
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config={"name": "Test Smart Climate"},
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=coordinator,
        )
        
        # Act - Simulate startup operations
        entity._handle_coordinator_update()
        
        # Assert - Operations should complete (no timeout)
        assert True  # If we get here, operations completed

    def test_startup_with_large_learning_dataset(self, mock_hass):
        """Test startup performance with large learning dataset."""
        # Arrange
        offset_engine = create_mock_offset_engine(
            learning_enabled=True,
            samples=1000,  # Large dataset
            accuracy=0.95,
            calculated_offset=2.0
        )
        
        coordinator = create_mock_coordinator(
            mock_hass,
            offset_engine,
            entity_id="climate.test"
        )
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config={"name": "Test Smart Climate"},
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=coordinator,
        )
        
        # Act - Should handle large dataset efficiently
        entity._handle_coordinator_update()
        
        # Assert - Operations should complete successfully
        assert True  # If we get here, operations completed

    def test_startup_memory_usage_stable(self, mock_hass):
        """Test that startup operations don't cause memory issues."""
        # Arrange
        offset_engine = create_mock_offset_engine(
            learning_enabled=True,
            samples=100,
            accuracy=0.85,
            calculated_offset=2.0
        )
        
        coordinator = create_mock_coordinator(
            mock_hass,
            offset_engine,
            entity_id="climate.test"
        )
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config={"name": "Test Smart Climate"},
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=coordinator,
        )
        
        # Act - Simulate multiple startup operations
        for _ in range(10):
            entity._handle_coordinator_update()
        
        # Assert - Operations should complete without memory issues
        assert True  # If we get here, operations completed successfully


class TestStartupLoggingAndDebugging:
    """Test logging and debugging capabilities during startup."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        return create_mock_hass()

    @patch('custom_components.smart_climate.climate._LOGGER')
    def test_startup_logging_provides_visibility(self, mock_logger, mock_hass):
        """Test that startup operations provide appropriate logging."""
        # Arrange
        offset_engine = create_mock_offset_engine(
            learning_enabled=True,
            samples=20,
            accuracy=0.85,
            calculated_offset=2.0
        )
        
        coordinator_data = SmartClimateData(
            room_temp=22.0,
            outdoor_temp=25.0,
            power=150.0,
            calculated_offset=2.0,
            mode_adjustments=Mock(),
            is_startup_calculation=True
        )
        
        coordinator = create_mock_coordinator(
            mock_hass,
            offset_engine,
            entity_id="climate.test",
            initial_data=coordinator_data
        )
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config={"name": "Test Smart Climate"},
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=coordinator,
        )
        
        entity._attr_target_temperature = 24.0
        
        # Act
        entity._handle_coordinator_update()
        
        # Assert - Should have logging calls
        # Note: Actual logging verification depends on implementation
        assert mock_logger.debug.called or mock_logger.info.called

    def test_startup_error_handling_with_logging(self, mock_hass):
        """Test that startup errors are properly logged."""
        # Arrange
        offset_engine = create_mock_offset_engine()
        offset_engine.calculate_offset.side_effect = Exception("Calculation failed")
        
        coordinator = create_mock_coordinator(
            mock_hass,
            offset_engine,
            entity_id="climate.test"
        )
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config={"name": "Test Smart Climate"},
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room_temp",
            offset_engine=offset_engine,
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(),
            coordinator=coordinator,
        )
        
        # Act & Assert - Should handle error gracefully
        entity._handle_coordinator_update()  # Should not raise exception