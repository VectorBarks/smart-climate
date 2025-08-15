"""Tests for thermal state + mode priority integration in SmartClimateEntity.

ABOUTME: Tests the _resolve_target_temperature() priority resolver method 
that coordinates thermal state machine with mode priority hierarchy.
"""

import pytest
from unittest.mock import Mock, patch
from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.models import ModeAdjustments
from custom_components.smart_climate.thermal_models import ThermalState


class TestClimateTherm‌alPriority:
    """Test priority resolution between thermal states and modes."""

    @pytest.fixture
    def mock_climate_entity(self):
        """Create a mock SmartClimateEntity for testing."""
        entity = Mock(spec=SmartClimateEntity)
        
        # Mock the method we're testing as a real method
        entity._resolve_target_temperature = SmartClimateEntity._resolve_target_temperature.__get__(entity)
        
        # Mock the standard offset logic method
        entity._apply_standard_offset_logic = Mock(return_value=22.0)
        
        return entity

    @pytest.fixture
    def base_target_temp(self):
        """Base target temperature for tests."""
        return 24.0

    @pytest.fixture
    def current_room_temp(self):
        """Current room temperature for tests."""
        return 25.5

    @pytest.fixture
    def boost_mode_adjustments(self):
        """Mode adjustments for boost mode with force_operation=True."""
        return ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=-2.0,
            force_operation=True
        )

    @pytest.fixture
    def away_mode_adjustments(self):
        """Mode adjustments for away mode with force_operation=False."""
        return ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0,
            force_operation=False
        )

    @pytest.fixture
    def standard_mode_adjustments(self):
        """Mode adjustments for standard operation."""
        return ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0,
            force_operation=False
        )

    def test_resolve_target_temp_boost_override_ignores_drifting(
        self, mock_climate_entity, base_target_temp, current_room_temp, boost_mode_adjustments
    ):
        """Test PRIORITY 1: Boost mode overrides DRIFTING state.
        
        When force_operation=True (boost mode), the priority resolver should
        ignore thermal state directives and apply mode override.
        """
        # Arrange
        thermal_state = ThermalState.DRIFTING
        
        # Act
        result = mock_climate_entity._resolve_target_temperature(
            base_target_temp, current_room_temp, thermal_state, boost_mode_adjustments
        )
        
        # Assert - Should use boost offset, ignore DRIFTING directive
        expected = base_target_temp + boost_mode_adjustments.boost_offset  # 24.0 + (-2.0) = 22.0
        assert result == expected
        
        # Verify standard offset logic not called during override
        mock_climate_entity._apply_standard_offset_logic.assert_not_called()

    def test_resolve_target_temp_drifting_state_sets_high_target(
        self, mock_climate_entity, base_target_temp, current_room_temp, away_mode_adjustments
    ):
        """Test PRIORITY 2: DRIFTING state turns A/C off when no mode override.
        
        When no force_operation and thermal state is DRIFTING,
        should set target = current_room_temp + 3.0 to turn A/C off.
        """
        # Arrange
        thermal_state = ThermalState.DRIFTING
        
        # Act
        result = mock_climate_entity._resolve_target_temperature(
            base_target_temp, current_room_temp, thermal_state, away_mode_adjustments
        )
        
        # Assert - Should set target above room temp to turn A/C off
        expected = current_room_temp + 3.0  # 25.5 + 3.0 = 28.5
        assert result == expected
        
        # Verify standard offset logic not called during thermal directive
        mock_climate_entity._apply_standard_offset_logic.assert_not_called()

    def test_resolve_target_temp_standard_operation_normal_logic(
        self, mock_climate_entity, base_target_temp, current_room_temp, standard_mode_adjustments
    ):
        """Test PRIORITY 3: Standard operation uses normal offset logic.
        
        When no force_operation and thermal state is not DRIFTING,
        should delegate to standard offset logic.
        """
        # Arrange
        thermal_state = ThermalState.CORRECTING
        mock_climate_entity._apply_standard_offset_logic.return_value = 23.5
        
        # Act
        result = mock_climate_entity._resolve_target_temperature(
            base_target_temp, current_room_temp, thermal_state, standard_mode_adjustments
        )
        
        # Assert - Should use standard offset logic result
        assert result == 23.5
        
        # Verify standard offset logic was called with correct parameters
        mock_climate_entity._apply_standard_offset_logic.assert_called_once_with(
            base_target_temp, standard_mode_adjustments
        )

    def test_resolve_target_temp_away_mode_with_drifting_coexists(
        self, mock_climate_entity, base_target_temp, current_room_temp, away_mode_adjustments
    ):
        """Test AWAY mode coexists with DRIFTING state.
        
        AWAY mode has force_operation=False, so DRIFTING state directive
        should still apply. Thermal learning continues during away mode.
        """
        # Arrange
        thermal_state = ThermalState.DRIFTING
        
        # Act
        result = mock_climate_entity._resolve_target_temperature(
            base_target_temp, current_room_temp, thermal_state, away_mode_adjustments
        )
        
        # Assert - DRIFTING logic should apply even with away mode
        expected = current_room_temp + 3.0  # 25.5 + 3.0 = 28.5
        assert result == expected

    def test_resolve_target_temp_priority_hierarchy_complete(
        self, mock_climate_entity, base_target_temp, current_room_temp
    ):
        """Test complete priority hierarchy with all thermal states.
        
        Verify the priority order: Mode override > Thermal state > Standard operation
        across all possible thermal states.
        """
        # Test all thermal states with boost mode (should always override)
        boost_adjustments = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=-1.5,
            force_operation=True
        )
        
        thermal_states = [
            ThermalState.PRIMING,
            ThermalState.DRIFTING,
            ThermalState.CORRECTING,
            ThermalState.RECOVERY,
            ThermalState.PROBING,
            ThermalState.CALIBRATING
        ]
        
        for thermal_state in thermal_states:
            result = mock_climate_entity._resolve_target_temperature(
                base_target_temp, current_room_temp, thermal_state, boost_adjustments
            )
            
            # All should use boost mode override regardless of thermal state
            expected = base_target_temp + boost_adjustments.boost_offset  # 24.0 + (-1.5) = 22.5
            assert result == expected, f"Failed for thermal state: {thermal_state}"

        # Test DRIFTING with standard mode (no override)
        standard_adjustments = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0,
            force_operation=False
        )
        
        result = mock_climate_entity._resolve_target_temperature(
            base_target_temp, current_room_temp, ThermalState.DRIFTING, standard_adjustments
        )
        
        # Should use DRIFTING directive
        expected = current_room_temp + 3.0  # 25.5 + 3.0 = 28.5
        assert result == expected

        # Test non-DRIFTING with standard mode (should use standard logic)
        mock_climate_entity._apply_standard_offset_logic.return_value = 24.2
        
        result = mock_climate_entity._resolve_target_temperature(
            base_target_temp, current_room_temp, ThermalState.CORRECTING, standard_adjustments
        )
        
        # Should use standard offset logic
        assert result == 24.2

    @patch('custom_components.smart_climate.climate._LOGGER')
    def test_resolve_target_temp_logging_verification(
        self, mock_logger, mock_climate_entity, base_target_temp, current_room_temp
    ):
        """Test that priority resolution decisions are logged for debugging.
        
        Each priority level should log its decision to help with debugging
        conflicts and understanding system behavior.
        """
        # Test boost mode override logging
        boost_adjustments = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=-2.0,
            force_operation=True
        )
        
        with patch.object(mock_climate_entity, '_log_priority_decision') as mock_log:
            mock_climate_entity._resolve_target_temperature(
                base_target_temp, current_room_temp, ThermalState.DRIFTING, boost_adjustments
            )
            
            # Should log mode override decision
            mock_log.assert_called_with(
                "Mode override active (force_operation=True). Target: 22.0, ignoring thermal state: DRIFTING"
            )

        # Test DRIFTING state logging
        standard_adjustments = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0,
            force_operation=False
        )
        
        with patch.object(mock_climate_entity, '_log_priority_decision') as mock_log:
            mock_climate_entity._resolve_target_temperature(
                base_target_temp, current_room_temp, ThermalState.DRIFTING, standard_adjustments
            )
            
            # Should log thermal state decision
            mock_log.assert_called_with(
                "Thermal state directive active (DRIFTING). Target: 28.5 (room + 3.0°C)"
            )

        # Test standard operation logging
        with patch.object(mock_climate_entity, '_log_priority_decision') as mock_log:
            mock_climate_entity._apply_standard_offset_logic.return_value = 23.8
            
            mock_climate_entity._resolve_target_temperature(
                base_target_temp, current_room_temp, ThermalState.CORRECTING, standard_adjustments
            )
            
            # Should log standard operation decision
            mock_log.assert_called_with(
                "Standard operation. Target: 23.8 (from offset logic)"
            )