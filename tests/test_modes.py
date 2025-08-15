"""Tests for ModeManager functionality."""

import pytest
from unittest.mock import Mock

from custom_components.smart_climate.mode_manager import ModeManager
from custom_components.smart_climate.models import ModeAdjustments


class TestModeManager:
    """Test ModeManager functionality."""

    def test_init_sets_default_mode_to_none(self):
        """Test that ModeManager initializes with 'none' mode."""
        config = {}
        manager = ModeManager(config)
        assert manager.current_mode == "none"

    def test_current_mode_property_returns_string(self):
        """Test that current_mode property returns string value."""
        config = {}
        manager = ModeManager(config)
        assert isinstance(manager.current_mode, str)
        assert manager.current_mode == "none"

    def test_set_mode_accepts_valid_modes(self):
        """Test that set_mode accepts all valid modes."""
        config = {}
        manager = ModeManager(config)
        
        valid_modes = ["none", "away", "sleep", "boost"]
        for mode in valid_modes:
            manager.set_mode(mode)
            assert manager.current_mode == mode

    def test_set_mode_rejects_invalid_modes(self):
        """Test that set_mode raises ValueError for invalid modes."""
        config = {}
        manager = ModeManager(config)
        
        invalid_modes = ["invalid", "test", "unknown", ""]
        for mode in invalid_modes:
            with pytest.raises(ValueError, match=f"Invalid mode: {mode}"):
                manager.set_mode(mode)

    def test_get_adjustments_returns_mode_adjustments_dataclass(self):
        """Test that get_adjustments returns ModeAdjustments instance."""
        config = {}
        manager = ModeManager(config)
        
        adjustments = manager.get_adjustments()
        assert isinstance(adjustments, ModeAdjustments)

    def test_register_mode_change_callback_stores_callback(self):
        """Test that callbacks are stored and can be registered."""
        config = {}
        manager = ModeManager(config)
        
        callback = Mock()
        manager.register_mode_change_callback(callback)
        
        # Change mode should trigger callback
        manager.set_mode("away")
        callback.assert_called_once()

    def test_mode_change_triggers_all_callbacks(self):
        """Test that mode changes trigger all registered callbacks."""
        config = {}
        manager = ModeManager(config)
        
        callback1 = Mock()
        callback2 = Mock()
        manager.register_mode_change_callback(callback1)
        manager.register_mode_change_callback(callback2)
        
        # Change mode should trigger both callbacks
        manager.set_mode("sleep")
        callback1.assert_called_once()
        callback2.assert_called_once()

    def test_mode_change_to_same_mode_still_triggers_callbacks(self):
        """Test that setting the same mode still triggers callbacks."""
        config = {}
        manager = ModeManager(config)
        
        callback = Mock()
        manager.register_mode_change_callback(callback)
        
        # Set same mode should still trigger callback
        manager.set_mode("none")
        callback.assert_called_once()

    def test_get_adjustments_for_none_mode(self):
        """Test adjustments for 'none' mode."""
        config = {}
        manager = ModeManager(config)
        manager.set_mode("none")
        
        adjustments = manager.get_adjustments()
        assert adjustments.temperature_override is None
        assert adjustments.offset_adjustment == 0.0
        assert adjustments.update_interval_override is None
        assert adjustments.boost_offset == 0.0

    def test_get_adjustments_for_away_mode(self):
        """Test adjustments for 'away' mode."""
        config = {"away_temperature": 24.0}
        manager = ModeManager(config)
        manager.set_mode("away")
        
        adjustments = manager.get_adjustments()
        assert adjustments.temperature_override == 24.0
        assert adjustments.offset_adjustment == 0.0
        assert adjustments.update_interval_override is None
        assert adjustments.boost_offset == 0.0

    def test_get_adjustments_for_sleep_mode(self):
        """Test adjustments for 'sleep' mode."""
        config = {"sleep_offset": 1.0}
        manager = ModeManager(config)
        manager.set_mode("sleep")
        
        adjustments = manager.get_adjustments()
        assert adjustments.temperature_override is None
        assert adjustments.offset_adjustment == 1.0
        assert adjustments.update_interval_override is None
        assert adjustments.boost_offset == 0.0

    def test_get_adjustments_for_boost_mode(self):
        """Test adjustments for 'boost' mode."""
        config = {"boost_offset": -2.0}
        manager = ModeManager(config)
        manager.set_mode("boost")
        
        adjustments = manager.get_adjustments()
        assert adjustments.temperature_override is None
        assert adjustments.offset_adjustment == 0.0
        assert adjustments.update_interval_override is None
        assert adjustments.boost_offset == -2.0

    def test_get_adjustments_uses_default_values_when_not_configured(self):
        """Test that get_adjustments uses defaults when config values missing."""
        config = {}  # Empty config
        manager = ModeManager(config)
        
        # Test away mode with default temperature
        manager.set_mode("away")
        adjustments = manager.get_adjustments()
        assert adjustments.temperature_override == 19.0  # Default away temp
        
        # Test sleep mode with default offset
        manager.set_mode("sleep")
        adjustments = manager.get_adjustments()
        assert adjustments.offset_adjustment == 1.0  # Default sleep offset
        
        # Test boost mode with default offset
        manager.set_mode("boost")
        adjustments = manager.get_adjustments()
        assert adjustments.boost_offset == -2.0  # Default boost offset

    def test_boost_mode_sets_force_operation_true(self):
        """Test that boost mode sets force_operation=True."""
        config = {"boost_offset": -2.0}
        manager = ModeManager(config)
        manager.set_mode("boost")
        
        adjustments = manager.get_adjustments()
        assert adjustments.force_operation is True

    def test_non_boost_modes_force_operation_false(self):
        """Test that non-boost modes set force_operation=False."""
        config = {}
        manager = ModeManager(config)
        
        non_boost_modes = ["none", "away", "sleep"]
        for mode in non_boost_modes:
            manager.set_mode(mode)
            adjustments = manager.get_adjustments()
            assert adjustments.force_operation is False, f"Mode {mode} should have force_operation=False"

    def test_boost_mode_retains_existing_boost_offset(self):
        """Test that boost mode retains existing boost_offset behavior."""
        config = {"boost_offset": -3.0}
        manager = ModeManager(config)
        manager.set_mode("boost")
        
        adjustments = manager.get_adjustments()
        assert adjustments.boost_offset == -3.0
        assert adjustments.force_operation is True
        assert adjustments.temperature_override is None
        assert adjustments.offset_adjustment == 0.0

    def test_away_mode_force_operation_false(self):
        """Test that away mode specifically sets force_operation=False."""
        config = {"away_temperature": 22.0}
        manager = ModeManager(config)
        manager.set_mode("away")
        
        adjustments = manager.get_adjustments()
        assert adjustments.force_operation is False
        assert adjustments.temperature_override == 22.0

    def test_sleep_mode_force_operation_false(self):
        """Test that sleep mode specifically sets force_operation=False."""
        config = {"sleep_offset": 2.0}
        manager = ModeManager(config)
        manager.set_mode("sleep")
        
        adjustments = manager.get_adjustments()
        assert adjustments.force_operation is False
        assert adjustments.offset_adjustment == 2.0

    def test_none_mode_force_operation_false(self):
        """Test that none mode specifically sets force_operation=False."""
        config = {}
        manager = ModeManager(config)
        manager.set_mode("none")
        
        adjustments = manager.get_adjustments()
        assert adjustments.force_operation is False
        assert adjustments.offset_adjustment == 0.0