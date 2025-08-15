"""Tests for data models in Smart Climate Control integration."""

import pytest
from custom_components.smart_climate.models import ModeAdjustments


class TestModeAdjustments:
    """Test ModeAdjustments dataclass functionality."""

    def test_mode_adjustments_has_force_operation_field_default_false(self):
        """Test that ModeAdjustments has force_operation field with default value False."""
        adjustments = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        )
        
        # This test should pass once we add the force_operation field
        assert hasattr(adjustments, 'force_operation')
        assert adjustments.force_operation is False

    def test_mode_adjustments_force_operation_true_explicit(self):
        """Test that ModeAdjustments force_operation can be explicitly set to True."""
        adjustments = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0,
            force_operation=True
        )
        
        assert adjustments.force_operation is True

    def test_mode_adjustments_backward_compatibility_existing_code(self):
        """Test that existing code that doesn't specify force_operation continues to work."""
        # Test constructor without force_operation parameter (backward compatibility)
        adjustments = ModeAdjustments(
            temperature_override=24.0,
            offset_adjustment=1.5,
            update_interval_override=120,
            boost_offset=-2.0
        )
        
        # Should default to False
        assert adjustments.force_operation is False
        
        # Verify all existing fields still work
        assert adjustments.temperature_override == 24.0
        assert adjustments.offset_adjustment == 1.5
        assert adjustments.update_interval_override == 120
        assert adjustments.boost_offset == -2.0

    def test_mode_adjustments_all_fields_present(self):
        """Test that ModeAdjustments has all required fields including the new force_operation."""
        adjustments = ModeAdjustments(
            temperature_override=22.0,
            offset_adjustment=0.5,
            update_interval_override=180,
            boost_offset=-1.5,
            force_operation=True
        )
        
        # Verify all fields are present and have correct values
        assert adjustments.temperature_override == 22.0
        assert adjustments.offset_adjustment == 0.5
        assert adjustments.update_interval_override == 180
        assert adjustments.boost_offset == -1.5
        assert adjustments.force_operation is True
        
        # Verify field types
        assert isinstance(adjustments.force_operation, bool)