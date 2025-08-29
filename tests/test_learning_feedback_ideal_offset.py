"""
ABOUTME: Comprehensive test infrastructure for learning feedback fix with ideal offset calculation.
Tests the new feedback mechanism that calculates hindsight ideal offsets instead of reactive ones.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
import asyncio
from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.sensor_manager import SensorManager
from custom_components.smart_climate.models import OffsetInput


class TestLearningFeedbackIdealOffset:
    """Test suite for learning feedback with ideal offset calculation."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        hass = Mock()
        hass.async_create_task = AsyncMock()
        return hass

    @pytest.fixture
    def mock_config_entry(self):
        """Create mock config entry."""
        config_entry = Mock()
        config_entry.data = {
            'entity_id': 'climate.test_ac',
            'room_sensor': 'sensor.room_temp',
            'outdoor_sensor': 'sensor.outdoor_temp',
            'target_sensor': 'sensor.target_temp',
            'learning_enabled': True,
        }
        config_entry.options = {}
        return config_entry

    @pytest.fixture
    def mock_offset_engine(self):
        """Create mock offset engine."""
        engine = Mock(spec=OffsetEngine)
        engine.calculate_offset = Mock(return_value=2.0)
        engine.record_actual_performance = Mock()
        engine.get_learning_info = Mock(return_value={
            'total_samples': 10,
            'confidence': 0.8
        })
        return engine

    @pytest.fixture
    def mock_sensor_manager(self):
        """Create mock sensor manager."""
        manager = Mock(spec=SensorManager)
        manager.get_room_temperature = AsyncMock(return_value=22.0)
        manager.get_outdoor_temperature = AsyncMock(return_value=15.0)
        manager.get_target_temperature = AsyncMock(return_value=24.0)
        manager.get_ac_temperature = AsyncMock(return_value=18.0)
        return manager

    @pytest.fixture
    def climate_entity(self, mock_hass, mock_config_entry, mock_offset_engine, mock_sensor_manager):
        """Create SmartClimateEntity instance with mocked dependencies."""
        with patch('custom_components.smart_climate.climate.OffsetEngine', return_value=mock_offset_engine), \
             patch('custom_components.smart_climate.climate.SensorManager', return_value=mock_sensor_manager):
            
            entity = SmartClimateEntity(mock_hass, mock_config_entry)
            entity._attr_target_temperature = 24.0
            entity._offset_engine = mock_offset_engine
            entity._sensor_manager = mock_sensor_manager
            
            # Initialize new attributes for learning feedback fix
            entity._last_initial_room_temp = None
            entity._last_target_temperature = None
            entity._last_predicted_offset = None
            entity._last_offset_input = None
            
            return entity

    async def test_stores_initial_room_temperature(self, climate_entity, mock_sensor_manager):
        """Test that initial room temperature is stored when applying offset."""
        # Arrange
        mock_sensor_manager.get_room_temperature.return_value = 23.0
        mock_sensor_manager.get_outdoor_temperature.return_value = 16.0
        climate_entity._attr_target_temperature = 25.0
        
        # Act
        await climate_entity._apply_temperature_with_offset(25.0)
        
        # Assert
        assert climate_entity._last_initial_room_temp == 23.0
        assert climate_entity._last_target_temperature == 25.0

    async def test_stores_target_temperature(self, climate_entity, mock_sensor_manager):
        """Test that target temperature is stored for validation."""
        # Arrange
        mock_sensor_manager.get_room_temperature.return_value = 20.0
        climate_entity._attr_target_temperature = 22.0
        
        # Act
        await climate_entity._apply_temperature_with_offset(22.0)
        
        # Assert
        assert climate_entity._last_target_temperature == 22.0

    async def test_calculates_ideal_offset(self, climate_entity, mock_sensor_manager, mock_offset_engine):
        """Test that ideal offset is calculated correctly (target - initial_room_temp)."""
        # Arrange - Setup initial conditions
        climate_entity._last_initial_room_temp = 21.0
        climate_entity._last_target_temperature = 24.0
        climate_entity._last_predicted_offset = 2.5
        climate_entity._last_offset_input = OffsetInput(
            room_temp=21.0,
            outdoor_temp=15.0,
            target_temp=24.0,
            current_time=datetime.now()
        )
        
        # Mock current conditions for feedback collection
        mock_sensor_manager.get_room_temperature.return_value = 23.5
        mock_sensor_manager.get_ac_temperature.return_value = 19.0
        climate_entity._attr_target_temperature = 24.0  # No change
        
        # Act
        await climate_entity._collect_learning_feedback(datetime.now())
        
        # Assert - Ideal offset should be target - initial = 24.0 - 21.0 = 3.0
        mock_offset_engine.record_actual_performance.assert_called_once_with(
            predicted_offset=2.5,
            actual_offset=3.0,  # The ideal offset
            input_data=climate_entity._last_offset_input
        )

    async def test_skips_feedback_if_target_changed(self, climate_entity, mock_sensor_manager, mock_offset_engine):
        """Test that feedback is skipped if user changed target temperature."""
        # Arrange - Setup initial conditions
        climate_entity._last_initial_room_temp = 20.0
        climate_entity._last_target_temperature = 22.0
        climate_entity._last_predicted_offset = 1.5
        climate_entity._last_offset_input = Mock()
        
        # Mock current conditions with changed target
        mock_sensor_manager.get_room_temperature.return_value = 21.5
        climate_entity._attr_target_temperature = 25.0  # User changed target
        
        # Act
        await climate_entity._collect_learning_feedback(datetime.now())
        
        # Assert - Should skip feedback due to target change
        mock_offset_engine.record_actual_performance.assert_not_called()

    async def test_records_ideal_offset_as_actual(self, climate_entity, mock_sensor_manager, mock_offset_engine):
        """Test that ideal offset is recorded as the actual offset for learning."""
        # Arrange
        climate_entity._last_initial_room_temp = 19.0
        climate_entity._last_target_temperature = 23.0
        climate_entity._last_predicted_offset = 3.2
        climate_entity._last_offset_input = Mock()
        climate_entity._attr_target_temperature = 23.0  # No change
        
        # Act
        await climate_entity._collect_learning_feedback(datetime.now())
        
        # Assert - Actual should be ideal offset: 23.0 - 19.0 = 4.0
        mock_offset_engine.record_actual_performance.assert_called_once()
        call_args = mock_offset_engine.record_actual_performance.call_args
        assert call_args[1]['actual_offset'] == 4.0

    async def test_feedback_with_cooling_scenario(self, climate_entity, mock_sensor_manager, mock_offset_engine):
        """Test feedback with cooling scenario: Room 25°C → Target 22°C → Ideal -3°C."""
        # Arrange - Hot room needs cooling
        climate_entity._last_initial_room_temp = 25.0
        climate_entity._last_target_temperature = 22.0
        climate_entity._last_predicted_offset = -2.0
        climate_entity._last_offset_input = Mock()
        climate_entity._attr_target_temperature = 22.0  # No change
        
        # Mock current conditions after cooling attempt
        mock_sensor_manager.get_room_temperature.return_value = 23.0
        mock_sensor_manager.get_ac_temperature.return_value = 16.0
        
        # Act
        await climate_entity._collect_learning_feedback(datetime.now())
        
        # Assert - Ideal offset should be negative: 22.0 - 25.0 = -3.0
        mock_offset_engine.record_actual_performance.assert_called_once()
        call_args = mock_offset_engine.record_actual_performance.call_args
        assert call_args[1]['actual_offset'] == -3.0

    async def test_feedback_with_heating_scenario(self, climate_entity, mock_sensor_manager, mock_offset_engine):
        """Test feedback with heating scenario: Room 18°C → Target 22°C → Ideal +4°C."""
        # Arrange - Cold room needs heating
        climate_entity._last_initial_room_temp = 18.0
        climate_entity._last_target_temperature = 22.0
        climate_entity._last_predicted_offset = 3.5
        climate_entity._last_offset_input = Mock()
        climate_entity._attr_target_temperature = 22.0  # No change
        
        # Mock current conditions after heating attempt
        mock_sensor_manager.get_room_temperature.return_value = 21.0
        mock_sensor_manager.get_ac_temperature.return_value = 28.0
        
        # Act
        await climate_entity._collect_learning_feedback(datetime.now())
        
        # Assert - Ideal offset should be positive: 22.0 - 18.0 = 4.0
        mock_offset_engine.record_actual_performance.assert_called_once()
        call_args = mock_offset_engine.record_actual_performance.call_args
        assert call_args[1]['actual_offset'] == 4.0

    async def test_handles_missing_initial_data(self, climate_entity, mock_sensor_manager, mock_offset_engine):
        """Test graceful handling when initial data is missing."""
        # Arrange - Missing initial room temperature
        climate_entity._last_initial_room_temp = None
        climate_entity._last_target_temperature = 22.0
        climate_entity._last_predicted_offset = 2.0
        climate_entity._last_offset_input = Mock()
        climate_entity._attr_target_temperature = 22.0
        
        # Act
        await climate_entity._collect_learning_feedback(datetime.now())
        
        # Assert - Should skip feedback due to missing data
        mock_offset_engine.record_actual_performance.assert_not_called()

    async def test_handles_missing_target_data(self, climate_entity, mock_sensor_manager, mock_offset_engine):
        """Test graceful handling when target data is missing."""
        # Arrange - Missing target temperature
        climate_entity._last_initial_room_temp = 20.0
        climate_entity._last_target_temperature = None
        climate_entity._last_predicted_offset = 2.0
        climate_entity._last_offset_input = Mock()
        climate_entity._attr_target_temperature = 22.0
        
        # Act
        await climate_entity._collect_learning_feedback(datetime.now())
        
        # Assert - Should skip feedback due to missing data
        mock_offset_engine.record_actual_performance.assert_not_called()

    async def test_preserves_predicted_offset(self, climate_entity, mock_sensor_manager, mock_offset_engine):
        """Test that predicted offset is preserved unchanged in feedback."""
        # Arrange
        original_predicted = 2.7
        climate_entity._last_initial_room_temp = 21.5
        climate_entity._last_target_temperature = 24.0
        climate_entity._last_predicted_offset = original_predicted
        climate_entity._last_offset_input = Mock()
        climate_entity._attr_target_temperature = 24.0  # No change
        
        # Act
        await climate_entity._collect_learning_feedback(datetime.now())
        
        # Assert - Predicted offset should be unchanged
        mock_offset_engine.record_actual_performance.assert_called_once()
        call_args = mock_offset_engine.record_actual_performance.call_args
        assert call_args[1]['predicted_offset'] == original_predicted

    async def test_feedback_timing_requirements(self, climate_entity, mock_sensor_manager, mock_offset_engine):
        """Test that feedback collection respects timing requirements."""
        # Arrange - Setup timing
        apply_time = datetime.now() - timedelta(minutes=5)  # 5 minutes ago
        climate_entity._last_offset_apply_time = apply_time
        climate_entity._last_initial_room_temp = 20.0
        climate_entity._last_target_temperature = 23.0
        climate_entity._last_predicted_offset = 2.5
        climate_entity._last_offset_input = Mock()
        climate_entity._attr_target_temperature = 23.0
        
        # Act
        current_time = datetime.now()
        await climate_entity._collect_learning_feedback(current_time)
        
        # Assert - Should proceed with feedback collection
        mock_offset_engine.record_actual_performance.assert_called_once()

    async def test_edge_case_zero_ideal_offset(self, climate_entity, mock_sensor_manager, mock_offset_engine):
        """Test edge case where ideal offset is zero (room already at target)."""
        # Arrange - Room already at target temperature
        climate_entity._last_initial_room_temp = 22.0
        climate_entity._last_target_temperature = 22.0
        climate_entity._last_predicted_offset = 1.0
        climate_entity._last_offset_input = Mock()
        climate_entity._attr_target_temperature = 22.0
        
        # Act
        await climate_entity._collect_learning_feedback(datetime.now())
        
        # Assert - Ideal offset should be zero: 22.0 - 22.0 = 0.0
        mock_offset_engine.record_actual_performance.assert_called_once()
        call_args = mock_offset_engine.record_actual_performance.call_args
        assert call_args[1]['actual_offset'] == 0.0

    async def test_large_temperature_differences(self, climate_entity, mock_sensor_manager, mock_offset_engine):
        """Test handling of large temperature differences."""
        # Arrange - Large temperature difference
        climate_entity._last_initial_room_temp = 10.0  # Very cold
        climate_entity._last_target_temperature = 30.0  # Very warm
        climate_entity._last_predicted_offset = 15.0
        climate_entity._last_offset_input = Mock()
        climate_entity._attr_target_temperature = 30.0
        
        # Act
        await climate_entity._collect_learning_feedback(datetime.now())
        
        # Assert - Ideal offset should handle large difference: 30.0 - 10.0 = 20.0
        mock_offset_engine.record_actual_performance.assert_called_once()
        call_args = mock_offset_engine.record_actual_performance.call_args
        assert call_args[1]['actual_offset'] == 20.0

    async def test_multiple_feedback_cycles(self, climate_entity, mock_sensor_manager, mock_offset_engine):
        """Test multiple feedback cycles with different scenarios."""
        # First cycle - Cooling
        climate_entity._last_initial_room_temp = 26.0
        climate_entity._last_target_temperature = 23.0
        climate_entity._last_predicted_offset = -2.5
        climate_entity._last_offset_input = Mock()
        climate_entity._attr_target_temperature = 23.0
        
        await climate_entity._collect_learning_feedback(datetime.now())
        
        # Verify first cycle
        assert mock_offset_engine.record_actual_performance.call_count == 1
        first_call = mock_offset_engine.record_actual_performance.call_args
        assert first_call[1]['actual_offset'] == -3.0  # 23.0 - 26.0
        
        # Reset mock for second cycle
        mock_offset_engine.record_actual_performance.reset_mock()
        
        # Second cycle - Heating
        climate_entity._last_initial_room_temp = 19.0
        climate_entity._last_target_temperature = 24.0
        climate_entity._last_predicted_offset = 4.2
        climate_entity._attr_target_temperature = 24.0
        
        await climate_entity._collect_learning_feedback(datetime.now())
        
        # Verify second cycle
        assert mock_offset_engine.record_actual_performance.call_count == 1
        second_call = mock_offset_engine.record_actual_performance.call_args
        assert second_call[1]['actual_offset'] == 5.0  # 24.0 - 19.0

    async def test_input_data_preservation(self, climate_entity, mock_sensor_manager, mock_offset_engine):
        """Test that input data is correctly preserved and passed to learning."""
        # Arrange - Create specific input data
        input_data = OffsetInput(
            room_temp=21.0,
            outdoor_temp=18.0,
            target_temp=25.0,
            current_time=datetime.now()
        )
        
        climate_entity._last_initial_room_temp = 21.0
        climate_entity._last_target_temperature = 25.0
        climate_entity._last_predicted_offset = 3.8
        climate_entity._last_offset_input = input_data
        climate_entity._attr_target_temperature = 25.0
        
        # Act
        await climate_entity._collect_learning_feedback(datetime.now())
        
        # Assert - Input data should be preserved
        mock_offset_engine.record_actual_performance.assert_called_once()
        call_args = mock_offset_engine.record_actual_performance.call_args
        assert call_args[1]['input_data'] is input_data

    async def test_learning_disabled_scenario(self, climate_entity, mock_sensor_manager):
        """Test behavior when learning is disabled."""
        # Arrange - Disable learning in offset engine
        climate_entity._offset_engine = Mock()
        climate_entity._offset_engine.record_actual_performance = Mock()
        
        climate_entity._last_initial_room_temp = 20.0
        climate_entity._last_target_temperature = 23.0
        climate_entity._last_predicted_offset = 2.5
        climate_entity._last_offset_input = Mock()
        climate_entity._attr_target_temperature = 23.0
        
        # Act
        await climate_entity._collect_learning_feedback(datetime.now())
        
        # Assert - Should still call record_actual_performance (engine handles learning state)
        climate_entity._offset_engine.record_actual_performance.assert_called_once()