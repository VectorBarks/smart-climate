"""Tests for coordinator learning data collection fix."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime

from custom_components.smart_climate.coordinator import SmartClimateCoordinator
from custom_components.smart_climate.models import OffsetInput, OffsetResult, ModeAdjustments


class TestCoordinatorLearningFix:
    """Test coordinator properly provides AC internal temperature for learning."""
    
    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = Mock()
        hass.states = Mock()
        return hass
    
    @pytest.fixture
    def mock_wrapped_entity_state(self):
        """Create a mock wrapped climate entity state."""
        state = Mock()
        state.state = "cool"
        state.attributes = {
            "current_temperature": 26.5,  # AC's internal sensor reading
            "target_temperature": 24.0,
            "hvac_modes": ["off", "cool", "heat"],
            "supported_features": 1
        }
        return state
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for coordinator."""
        # Mock sensor manager
        sensor_manager = Mock()
        sensor_manager.get_room_temperature = Mock(return_value=25.2)  # External room sensor
        sensor_manager.get_outdoor_temperature = Mock(return_value=30.0)
        sensor_manager.get_power_consumption = Mock(return_value=150.0)
        
        # Mock offset engine
        offset_engine = Mock()
        offset_engine.calculate_offset = Mock(return_value=OffsetResult(
            offset=1.3,
            clamped=False,
            reason="Test reason",
            confidence=0.8
        ))
        
        # Mock mode manager
        mode_manager = Mock()
        mode_manager.current_mode = "none"
        mode_manager.get_adjustments = Mock(return_value=ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        ))
        
        return {
            "sensor_manager": sensor_manager,
            "offset_engine": offset_engine,
            "mode_manager": mode_manager
        }
    
    @pytest.mark.asyncio
    async def test_coordinator_uses_correct_temperatures_for_offset_calculation(
        self, mock_hass, mock_wrapped_entity_state, mock_dependencies
    ):
        """Test that coordinator uses AC internal temp, not room temp for both values."""
        # Create coordinator
        coordinator = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=180,
            **mock_dependencies
        )
        
        # Set the wrapped entity ID (normally done by climate entity)
        coordinator._wrapped_entity_id = "climate.test_ac"
        
        # Mock hass.states.get to return our wrapped entity
        mock_hass.states.get = Mock(return_value=mock_wrapped_entity_state)
        
        # Run coordinator update
        data = await coordinator._async_update_data()
        
        # Verify offset engine was called
        mock_dependencies["offset_engine"].calculate_offset.assert_called_once()
        
        # Get the OffsetInput that was passed
        offset_input = mock_dependencies["offset_engine"].calculate_offset.call_args[0][0]
        
        # Verify it used different temperatures for AC internal and room
        assert isinstance(offset_input, OffsetInput)
        assert offset_input.ac_internal_temp == 26.5  # From wrapped entity's current_temperature
        assert offset_input.room_temp == 25.2  # From room sensor
        assert offset_input.ac_internal_temp != offset_input.room_temp  # Should be different!
        
        # Verify other data is correct
        assert offset_input.outdoor_temp == 30.0
        assert offset_input.power_consumption == 150.0
        assert offset_input.mode == "none"
        assert isinstance(offset_input.time_of_day, datetime.time)
        assert isinstance(offset_input.day_of_week, int)
    
    @pytest.mark.asyncio
    async def test_coordinator_handles_missing_wrapped_entity_temperature(
        self, mock_hass, mock_dependencies
    ):
        """Test coordinator handles missing AC internal temperature gracefully."""
        coordinator = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=180,
            **mock_dependencies
        )
        
        coordinator._wrapped_entity_id = "climate.test_ac"
        
        # Mock wrapped entity without current_temperature attribute
        wrapped_state = Mock()
        wrapped_state.attributes = {"target_temperature": 24.0}  # No current_temperature
        mock_hass.states.get = Mock(return_value=wrapped_state)
        
        # Run coordinator update
        data = await coordinator._async_update_data()
        
        # Should still calculate offset using room temp as fallback
        mock_dependencies["offset_engine"].calculate_offset.assert_called_once()
        offset_input = mock_dependencies["offset_engine"].calculate_offset.call_args[0][0]
        
        # When AC internal temp is not available, it should fall back to room temp
        assert offset_input.ac_internal_temp == 25.2  # Falls back to room temp
        assert offset_input.room_temp == 25.2
    
    @pytest.mark.asyncio
    async def test_coordinator_handles_unavailable_wrapped_entity(
        self, mock_hass, mock_dependencies
    ):
        """Test coordinator handles unavailable wrapped entity."""
        coordinator = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=180,
            **mock_dependencies
        )
        
        coordinator._wrapped_entity_id = "climate.test_ac"
        
        # Mock wrapped entity as unavailable
        mock_hass.states.get = Mock(return_value=None)
        
        # Run coordinator update
        data = await coordinator._async_update_data()
        
        # Should still calculate offset using room temp for both
        mock_dependencies["offset_engine"].calculate_offset.assert_called_once()
        offset_input = mock_dependencies["offset_engine"].calculate_offset.call_args[0][0]
        
        # Both temps should be room temp when entity unavailable
        assert offset_input.ac_internal_temp == 25.2
        assert offset_input.room_temp == 25.2
    
    @pytest.mark.asyncio
    async def test_coordinator_offset_calculation_produces_meaningful_learning_data(
        self, mock_hass, mock_wrapped_entity_state, mock_dependencies
    ):
        """Test that temperature differences produce meaningful offset calculations."""
        coordinator = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=180,
            **mock_dependencies
        )
        
        coordinator._wrapped_entity_id = "climate.test_ac"
        mock_hass.states.get = Mock(return_value=mock_wrapped_entity_state)
        
        # Run multiple updates with different temperature scenarios
        test_scenarios = [
            # (ac_internal, room_temp, expected_description)
            (28.0, 25.0, "AC much warmer than room"),
            (25.0, 25.0, "AC matches room"),
            (23.0, 25.0, "AC cooler than room"),
        ]
        
        for ac_temp, room_temp, description in test_scenarios:
            # Update temperatures
            mock_wrapped_entity_state.attributes["current_temperature"] = ac_temp
            mock_dependencies["sensor_manager"].get_room_temperature.return_value = room_temp
            
            # Run update
            data = await coordinator._async_update_data()
            
            # Get the offset input
            offset_input = mock_dependencies["offset_engine"].calculate_offset.call_args[0][0]
            
            # Verify meaningful temperature difference
            temp_diff = ac_temp - room_temp
            assert offset_input.ac_internal_temp == ac_temp
            assert offset_input.room_temp == room_temp
            
            # The offset engine should see the temperature difference
            # This difference is what drives the learning system
            assert (offset_input.ac_internal_temp - offset_input.room_temp) == temp_diff