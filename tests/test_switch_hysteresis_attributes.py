"""Test hysteresis attributes display in Smart Climate switch entity."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from homeassistant.config_entries import ConfigEntry

from custom_components.smart_climate.switch import LearningSwitch
from custom_components.smart_climate.offset_engine import OffsetEngine


class TestSwitchHysteresisAttributes:
    """Test hysteresis attributes in switch extra_state_attributes."""

    @pytest.fixture
    def mock_config_entry(self):
        """Create a mock config entry."""
        entry = Mock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.unique_id = "test_unique_id"
        entry.title = "Test Climate"
        return entry

    @pytest.fixture
    def mock_offset_engine_with_hysteresis(self):
        """Create a mock offset engine with hysteresis data."""
        engine = Mock(spec=OffsetEngine)
        engine.is_learning_enabled = True
        
        # Mock get_learning_info to return hysteresis data
        engine.get_learning_info = Mock(return_value={
            "enabled": True,
            "samples": 25,
            "accuracy": 0.85,
            "confidence": 0.85,
            "has_sufficient_data": True,
            "last_sample_time": "2025-01-08T12:00:00",
            # New hysteresis attributes
            "hysteresis_enabled": True,
            "hysteresis_state": "ready",
            "learned_start_threshold": 26.58,
            "learned_stop_threshold": 22.87,
            "temperature_window": 3.71,
            "start_samples_collected": 12,
            "stop_samples_collected": 13,
            "hysteresis_ready": True,
        })
        
        engine.register_update_callback = Mock(return_value=Mock())
        return engine

    def test_extra_state_attributes_includes_hysteresis_fields(self, mock_config_entry, mock_offset_engine_with_hysteresis):
        """Test that extra_state_attributes includes all hysteresis fields."""
        # GIVEN: A learning switch with hysteresis-enabled engine
        switch = LearningSwitch(
            mock_config_entry,
            mock_offset_engine_with_hysteresis,
            "Test Climate",
            "climate.test"
        )
        
        # WHEN: Getting extra state attributes
        attrs = switch.extra_state_attributes
        
        # THEN: All hysteresis fields should be present
        assert "hysteresis_enabled" in attrs
        assert attrs["hysteresis_enabled"] is True
        assert "hysteresis_state" in attrs
        assert attrs["hysteresis_state"] == "Ready"
        assert "learned_start_threshold" in attrs
        assert attrs["learned_start_threshold"] == "26.58°C"  # Formatted
        assert "learned_stop_threshold" in attrs
        assert attrs["learned_stop_threshold"] == "22.87°C"  # Formatted
        assert "temperature_window" in attrs
        assert attrs["temperature_window"] == "3.71°C"  # Formatted
        assert "start_samples_collected" in attrs
        assert attrs["start_samples_collected"] == 12
        assert "stop_samples_collected" in attrs
        assert attrs["stop_samples_collected"] == 13
        assert "hysteresis_ready" in attrs
        assert attrs["hysteresis_ready"] is True

    def test_threshold_formatting_two_decimal_places(self, mock_config_entry):
        """Test that temperature thresholds are formatted to 2 decimal places with unit."""
        # GIVEN: Engine with precise threshold values
        engine = Mock(spec=OffsetEngine)
        engine.is_learning_enabled = True
        engine.get_learning_info = Mock(return_value={
            "enabled": True,
            "samples": 10,
            "accuracy": 0.8,
            "confidence": 0.8,
            "has_sufficient_data": True,
            "last_sample_time": None,
            "hysteresis_enabled": True,
            "hysteresis_state": "ready",
            "learned_start_threshold": 25.999999,
            "learned_stop_threshold": 22.111111,
            "temperature_window": 3.888888,
            "start_samples_collected": 5,
            "stop_samples_collected": 5,
            "hysteresis_ready": True,
        })
        engine.register_update_callback = Mock(return_value=Mock())
        
        switch = LearningSwitch(mock_config_entry, engine, "Test", "climate.test")
        
        # WHEN: Getting attributes
        attrs = switch.extra_state_attributes
        
        # THEN: Values should be formatted to 2 decimals with °C
        assert attrs["learned_start_threshold"] == "26.00°C"
        assert attrs["learned_stop_threshold"] == "22.11°C"
        assert attrs["temperature_window"] == "3.89°C"

    def test_temperature_window_calculation(self, mock_config_entry):
        """Test that temperature_window is calculated correctly."""
        # GIVEN: Engine with specific thresholds
        engine = Mock(spec=OffsetEngine)
        engine.is_learning_enabled = True
        engine.get_learning_info = Mock(return_value={
            "enabled": True,
            "samples": 10,
            "accuracy": 0.8,
            "confidence": 0.8,
            "has_sufficient_data": True,
            "last_sample_time": None,
            "hysteresis_enabled": True,
            "hysteresis_state": "ready",
            "learned_start_threshold": 28.5,
            "learned_stop_threshold": 21.0,
            "temperature_window": 7.5,  # Should be start - stop
            "start_samples_collected": 10,
            "stop_samples_collected": 10,
            "hysteresis_ready": True,
        })
        engine.register_update_callback = Mock(return_value=Mock())
        
        switch = LearningSwitch(mock_config_entry, engine, "Test", "climate.test")
        
        # WHEN: Getting attributes
        attrs = switch.extra_state_attributes
        
        # THEN: Window should be the difference
        assert attrs["temperature_window"] == "7.50°C"

    def test_hysteresis_not_visible_when_disabled(self, mock_config_entry):
        """Test that hysteresis attributes show disabled state when no power sensor."""
        # GIVEN: Engine without hysteresis (no power sensor)
        engine = Mock(spec=OffsetEngine)
        engine.is_learning_enabled = True
        engine.get_learning_info = Mock(return_value={
            "enabled": True,
            "samples": 50,
            "accuracy": 0.9,
            "confidence": 0.9,
            "has_sufficient_data": True,
            "last_sample_time": None,
            "hysteresis_enabled": False,
            "hysteresis_state": "disabled",
            "learned_start_threshold": None,
            "learned_stop_threshold": None,
            "temperature_window": None,
            "start_samples_collected": 0,
            "stop_samples_collected": 0,
            "hysteresis_ready": False,
        })
        engine.register_update_callback = Mock(return_value=Mock())
        
        switch = LearningSwitch(mock_config_entry, engine, "Test", "climate.test")
        
        # WHEN: Getting attributes
        attrs = switch.extra_state_attributes
        
        # THEN: Should show disabled state
        assert attrs["hysteresis_enabled"] is False
        assert attrs["hysteresis_state"] == "No power sensor"
        assert attrs["learned_start_threshold"] == "Not available"
        assert attrs["learned_stop_threshold"] == "Not available"
        assert attrs["temperature_window"] == "Not available"
        assert attrs["start_samples_collected"] == 0
        assert attrs["stop_samples_collected"] == 0
        assert attrs["hysteresis_ready"] is False

    def test_hysteresis_learning_state(self, mock_config_entry):
        """Test hysteresis attributes when still learning (insufficient data)."""
        # GIVEN: Engine in learning state
        engine = Mock(spec=OffsetEngine)
        engine.is_learning_enabled = True
        engine.get_learning_info = Mock(return_value={
            "enabled": True,
            "samples": 5,
            "accuracy": 0.5,
            "confidence": 0.5,
            "has_sufficient_data": False,
            "last_sample_time": None,
            "hysteresis_enabled": True,
            "hysteresis_state": "learning_hysteresis",
            "learned_start_threshold": None,
            "learned_stop_threshold": None,
            "temperature_window": None,
            "start_samples_collected": 3,
            "stop_samples_collected": 2,
            "hysteresis_ready": False,
        })
        engine.register_update_callback = Mock(return_value=Mock())
        
        switch = LearningSwitch(mock_config_entry, engine, "Test", "climate.test")
        
        # WHEN: Getting attributes
        attrs = switch.extra_state_attributes
        
        # THEN: Should show learning state
        assert attrs["hysteresis_enabled"] is True
        assert attrs["hysteresis_state"] == "Learning AC behavior"
        assert attrs["learned_start_threshold"] == "Learning..."
        assert attrs["learned_stop_threshold"] == "Learning..."
        assert attrs["temperature_window"] == "Learning..."
        assert attrs["start_samples_collected"] == 3
        assert attrs["stop_samples_collected"] == 2
        assert attrs["hysteresis_ready"] is False

    def test_attributes_with_exception_handling(self, mock_config_entry):
        """Test that attributes handle exceptions from get_learning_info gracefully."""
        # GIVEN: Engine that throws exception
        engine = Mock(spec=OffsetEngine)
        engine.is_learning_enabled = True
        engine.get_learning_info = Mock(side_effect=ValueError("Test exception"))
        engine.register_update_callback = Mock(return_value=Mock())
        
        switch = LearningSwitch(mock_config_entry, engine, "Test", "climate.test")
        
        # WHEN: Getting attributes
        attrs = switch.extra_state_attributes
        
        # THEN: Should return safe defaults
        assert attrs["error"] == "Test exception"
        assert attrs["samples_collected"] == 0
        assert attrs["learning_accuracy"] == 0.0
        # Hysteresis fields should have safe defaults
        assert "hysteresis_enabled" not in attrs or attrs["hysteresis_enabled"] is False

    def test_hysteresis_state_descriptions(self, mock_config_entry):
        """Test different hysteresis states are properly displayed."""
        states_to_test = [
            ("learning_hysteresis", "Learning AC behavior"),
            ("active_phase", "AC actively cooling"),
            ("idle_above_start_threshold", "AC should start soon"),
            ("idle_below_stop_threshold", "AC recently stopped"),
            ("idle_stable_zone", "Temperature stable"),
            ("ready", "Ready"),
            ("disabled", "No power sensor"),
        ]
        
        for state_value, expected_display in states_to_test:
            # GIVEN: Engine with specific hysteresis state
            engine = Mock(spec=OffsetEngine)
            engine.is_learning_enabled = True
            engine.get_learning_info = Mock(return_value={
                "enabled": True,
                "samples": 10,
                "accuracy": 0.8,
                "confidence": 0.8,
                "has_sufficient_data": True,
                "last_sample_time": None,
                "hysteresis_enabled": True,
                "hysteresis_state": state_value,
                "learned_start_threshold": 26.0 if state_value != "learning_hysteresis" else None,
                "learned_stop_threshold": 23.0 if state_value != "learning_hysteresis" else None,
                "temperature_window": 3.0 if state_value != "learning_hysteresis" else None,
                "start_samples_collected": 5,
                "stop_samples_collected": 5,
                "hysteresis_ready": state_value not in ["learning_hysteresis", "disabled"],
            })
            engine.register_update_callback = Mock(return_value=Mock())
            
            switch = LearningSwitch(mock_config_entry, engine, "Test", "climate.test")
            
            # WHEN: Getting attributes
            attrs = switch.extra_state_attributes
            
            # THEN: State should have human-readable description
            assert attrs["hysteresis_state"] == expected_display

    def test_integration_with_existing_attributes(self, mock_config_entry, mock_offset_engine_with_hysteresis):
        """Test that hysteresis attributes integrate with existing learning attributes."""
        # GIVEN: Switch with full data
        switch = LearningSwitch(
            mock_config_entry,
            mock_offset_engine_with_hysteresis,
            "Test Climate",
            "climate.test"
        )
        
        # WHEN: Getting attributes
        attrs = switch.extra_state_attributes
        
        # THEN: Both existing and new attributes should be present
        # Existing attributes
        assert "samples_collected" in attrs
        assert "learning_accuracy" in attrs
        assert "confidence_level" in attrs
        assert "patterns_learned" in attrs
        assert "has_sufficient_data" in attrs
        assert "enabled" in attrs
        assert "last_sample_collected" in attrs
        
        # New hysteresis attributes
        assert "hysteresis_enabled" in attrs
        assert "hysteresis_state" in attrs
        assert "learned_start_threshold" in attrs
        assert "learned_stop_threshold" in attrs
        assert "temperature_window" in attrs
        assert "start_samples_collected" in attrs
        assert "stop_samples_collected" in attrs
        assert "hysteresis_ready" in attrs