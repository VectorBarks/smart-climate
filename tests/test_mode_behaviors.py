"""Tests for mode-specific behaviors and adjustments."""

import pytest
from unittest.mock import Mock

from custom_components.smart_climate.mode_manager import ModeManager
from custom_components.smart_climate.models import ModeAdjustments


class TestModeBehaviors:
    """Test mode-specific behaviors and adjustments."""

    def test_away_mode_returns_fixed_temperature_override(self):
        """Test that away mode returns temperature_override=19.0 (fixed temp)."""
        config = {}
        manager = ModeManager(config)
        manager.set_mode("away")
        
        adjustments = manager.get_adjustments()
        assert adjustments.temperature_override == 19.0
        assert adjustments.offset_adjustment == 0.0
        assert adjustments.update_interval_override is None
        assert adjustments.boost_offset == 0.0

    def test_away_mode_uses_config_value_when_provided(self):
        """Test that away mode uses config value when available."""
        config = {"away_temperature": 21.0}
        manager = ModeManager(config)
        manager.set_mode("away")
        
        adjustments = manager.get_adjustments()
        assert adjustments.temperature_override == 21.0

    def test_sleep_mode_returns_warmer_offset_adjustment(self):
        """Test that sleep mode returns offset_adjustment=1.0 (warmer at night)."""
        config = {}
        manager = ModeManager(config)
        manager.set_mode("sleep")
        
        adjustments = manager.get_adjustments()
        assert adjustments.temperature_override is None
        assert adjustments.offset_adjustment == 1.0
        assert adjustments.update_interval_override is None
        assert adjustments.boost_offset == 0.0

    def test_sleep_mode_uses_config_value_when_provided(self):
        """Test that sleep mode uses config value when available."""
        config = {"sleep_offset": 1.5}
        manager = ModeManager(config)
        manager.set_mode("sleep")
        
        adjustments = manager.get_adjustments()
        assert adjustments.offset_adjustment == 1.5

    def test_boost_mode_returns_extra_cooling_offset(self):
        """Test that boost mode returns boost_offset=-2.0 (extra cooling)."""
        config = {}
        manager = ModeManager(config)
        manager.set_mode("boost")
        
        adjustments = manager.get_adjustments()
        assert adjustments.temperature_override is None
        assert adjustments.offset_adjustment == 0.0
        assert adjustments.update_interval_override is None
        assert adjustments.boost_offset == -2.0

    def test_boost_mode_uses_config_value_when_provided(self):
        """Test that boost mode uses config value when available."""
        config = {"boost_offset": -3.0}
        manager = ModeManager(config)
        manager.set_mode("boost")
        
        adjustments = manager.get_adjustments()
        assert adjustments.boost_offset == -3.0

    def test_none_mode_returns_all_adjustments_at_zero_or_none(self):
        """Test that none mode returns all adjustments at 0/None."""
        config = {}
        manager = ModeManager(config)
        manager.set_mode("none")
        
        adjustments = manager.get_adjustments()
        assert adjustments.temperature_override is None
        assert adjustments.offset_adjustment == 0.0
        assert adjustments.update_interval_override is None
        assert adjustments.boost_offset == 0.0

    def test_all_modes_return_proper_mode_adjustments_instance(self):
        """Test that all modes return proper ModeAdjustments instances."""
        config = {}
        manager = ModeManager(config)
        
        modes = ["none", "away", "sleep", "boost"]
        for mode in modes:
            manager.set_mode(mode)
            adjustments = manager.get_adjustments()
            assert isinstance(adjustments, ModeAdjustments)
            
            # Verify all fields are present
            assert hasattr(adjustments, 'temperature_override')
            assert hasattr(adjustments, 'offset_adjustment')
            assert hasattr(adjustments, 'update_interval_override')
            assert hasattr(adjustments, 'boost_offset')

    def test_mode_specific_defaults_match_requirements(self):
        """Test that mode-specific defaults match the task requirements."""
        config = {}
        manager = ModeManager(config)
        
        # Test away mode default
        manager.set_mode("away")
        adjustments = manager.get_adjustments()
        assert adjustments.temperature_override == 19.0
        
        # Test sleep mode default
        manager.set_mode("sleep")
        adjustments = manager.get_adjustments()
        assert adjustments.offset_adjustment == 1.0
        
        # Test boost mode default
        manager.set_mode("boost")
        adjustments = manager.get_adjustments()
        assert adjustments.boost_offset == -2.0
        
        # Test none mode (no changes)
        manager.set_mode("none")
        adjustments = manager.get_adjustments()
        assert adjustments.temperature_override is None
        assert adjustments.offset_adjustment == 0.0
        assert adjustments.boost_offset == 0.0