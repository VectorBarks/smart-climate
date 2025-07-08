"""Integration tests for hysteresis display from engine to switch attributes."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from custom_components.smart_climate.offset_engine import OffsetEngine, HysteresisLearner
from custom_components.smart_climate.switch import LearningSwitch
from custom_components.smart_climate.models import OffsetInput
from homeassistant.config_entries import ConfigEntry


class TestHysteresisDisplayIntegration:
    """Test the full flow of hysteresis data from engine to switch display."""

    @pytest.fixture
    def config_with_power_sensor(self):
        """Configuration with power sensor enabled."""
        return {
            "power_sensor": "sensor.ac_power",
            "enable_learning": True,
            "power_idle_threshold": 10.0,
            "power_min_threshold": 50.0,
            "power_max_threshold": 200.0,
        }

    @pytest.fixture
    def mock_config_entry(self):
        """Create a mock config entry."""
        entry = Mock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.unique_id = "test_unique_id"
        entry.title = "Test Climate"
        return entry

    def test_full_flow_from_transitions_to_display(self, config_with_power_sensor, mock_config_entry):
        """Test complete flow from recording transitions to displaying in switch."""
        # GIVEN: Real OffsetEngine with hysteresis enabled
        engine = OffsetEngine(config_with_power_sensor)
        
        # Simulate AC operation: idle -> high -> idle transitions
        transitions = [
            # AC starts (idle to high) at different room temps
            (5.0, 300.0, 26.5),   # Power goes from 5W to 300W at 26.5°C
            (8.0, 280.0, 26.8),   # Another start at 26.8°C
            (4.0, 290.0, 26.3),   # Another start at 26.3°C
            (6.0, 310.0, 26.6),   # Another start at 26.6°C
            (7.0, 295.0, 26.4),   # Another start at 26.4°C
        ]
        
        # Record start transitions
        for idle_power, high_power, room_temp in transitions:
            # First, set to idle state
            input_idle = OffsetInput(
                ac_internal_temp=25.0,
                room_temp=room_temp,
                outdoor_temp=None,
                mode="cool",
                power_consumption=idle_power,
                time_of_day=datetime.now().time(),
                day_of_week=datetime.now().weekday()
            )
            engine.calculate_offset(input_idle)
            
            # Then transition to high power
            input_high = OffsetInput(
                ac_internal_temp=25.0,
                room_temp=room_temp,
                outdoor_temp=None,
                mode="cool",
                power_consumption=high_power,
                time_of_day=datetime.now().time(),
                day_of_week=datetime.now().weekday()
            )
            engine.calculate_offset(input_high)
        
        # Now record stop transitions (high to idle)
        stop_transitions = [
            (295.0, 6.0, 23.2),   # Power goes from 295W to 6W at 23.2°C
            (300.0, 5.0, 23.0),   # Another stop at 23.0°C
            (285.0, 7.0, 23.5),   # Another stop at 23.5°C
            (290.0, 4.0, 23.1),   # Another stop at 23.1°C
            (305.0, 8.0, 23.3),   # Another stop at 23.3°C
        ]
        
        for high_power, idle_power, room_temp in stop_transitions:
            # First, ensure we're in high state
            input_high = OffsetInput(
                ac_internal_temp=22.0,
                room_temp=room_temp,
                outdoor_temp=None,
                mode="cool",
                power_consumption=high_power,
                time_of_day=datetime.now().time(),
                day_of_week=datetime.now().weekday()
            )
            engine.calculate_offset(input_high)
            
            # Then transition to idle
            input_idle = OffsetInput(
                ac_internal_temp=22.0,
                room_temp=room_temp,
                outdoor_temp=None,
                mode="cool",
                power_consumption=idle_power,
                time_of_day=datetime.now().time(),
                day_of_week=datetime.now().weekday()
            )
            engine.calculate_offset(input_idle)
        
        # Create switch with this engine
        switch = LearningSwitch(mock_config_entry, engine, "Test Climate", "climate.test")
        
        # WHEN: Getting switch attributes
        attrs = switch.extra_state_attributes
        
        # THEN: Should show learned thresholds
        assert attrs["hysteresis_enabled"] is True
        assert attrs["hysteresis_state"] == "Ready"  # Or specific state based on implementation
        assert attrs["learned_start_threshold"] == "26.50°C"  # Median of [26.3, 26.4, 26.5, 26.6, 26.8]
        assert attrs["learned_stop_threshold"] == "23.20°C"   # Median of [23.0, 23.1, 23.2, 23.3, 23.5]
        assert attrs["temperature_window"] == "3.30°C"        # 26.5 - 23.2
        assert attrs["start_samples_collected"] == 5
        assert attrs["stop_samples_collected"] == 5
        assert attrs["hysteresis_ready"] is True

    def test_state_transitions_reflected_in_attributes(self, config_with_power_sensor, mock_config_entry):
        """Test that hysteresis state transitions are reflected in switch attributes."""
        # GIVEN: Engine with sufficient data
        engine = OffsetEngine(config_with_power_sensor)
        
        # Manually set up hysteresis data for testing
        engine._hysteresis_learner._start_temps.extend([26.5, 26.6, 26.4, 26.7, 26.3])
        engine._hysteresis_learner._stop_temps.extend([23.0, 23.2, 23.1, 23.3, 22.9])
        engine._hysteresis_learner._update_thresholds()
        
        switch = LearningSwitch(mock_config_entry, engine, "Test Climate", "climate.test")
        
        # Test different states
        test_cases = [
            # (power, room_temp, expected_state_display)
            (250.0, 25.0, "AC actively cooling"),           # High power = active
            (5.0, 27.0, "AC should start soon"),            # Idle above start threshold
            (5.0, 22.0, "AC recently stopped"),             # Idle below stop threshold
            (5.0, 25.0, "Temperature stable"),              # Idle in stable zone
        ]
        
        for power, room_temp, expected_state in test_cases:
            # WHEN: Processing input with specific conditions
            input_data = OffsetInput(
                ac_internal_temp=24.0,
                room_temp=room_temp,
                outdoor_temp=None,
                mode="cool",
                power_consumption=power,
                time_of_day=datetime.now().time(),
                day_of_week=datetime.now().weekday()
            )
            engine.calculate_offset(input_data)
            
            # Get fresh attributes after state update
            attrs = switch.extra_state_attributes
            
            # THEN: State should match expected
            assert attrs["hysteresis_state"] == expected_state

    def test_learning_progression_updates(self, config_with_power_sensor, mock_config_entry):
        """Test that attributes update as samples are collected."""
        # GIVEN: Fresh engine with no data
        engine = OffsetEngine(config_with_power_sensor)
        switch = LearningSwitch(mock_config_entry, engine, "Test Climate", "climate.test")
        
        # Initial state - no data
        attrs = switch.extra_state_attributes
        assert attrs["hysteresis_state"] == "Learning AC behavior"
        assert attrs["learned_start_threshold"] == "Learning..."
        assert attrs["learned_stop_threshold"] == "Learning..."
        assert attrs["start_samples_collected"] == 0
        assert attrs["stop_samples_collected"] == 0
        
        # Add some samples (but not enough)
        for i in range(3):
            # Simulate start transition
            input_idle = OffsetInput(
                ac_internal_temp=25.0,
                room_temp=26.0 + i * 0.1,
                outdoor_temp=None,
                mode="cool",
                power_consumption=5.0,
                time_of_day=datetime.now().time(),
                day_of_week=datetime.now().weekday()
            )
            engine.calculate_offset(input_idle)
            
            input_high = OffsetInput(
                ac_internal_temp=25.0,
                room_temp=26.0 + i * 0.1,
                outdoor_temp=None,
                mode="cool",
                power_consumption=300.0,
                time_of_day=datetime.now().time(),
                day_of_week=datetime.now().weekday()
            )
            engine.calculate_offset(input_high)
        
        # Check intermediate state
        attrs = switch.extra_state_attributes
        assert attrs["hysteresis_state"] == "Learning AC behavior"
        assert attrs["start_samples_collected"] == 3
        assert attrs["stop_samples_collected"] == 0
        assert attrs["hysteresis_ready"] is False
        
        # Add stop transitions to complete learning
        for i in range(5):
            # Simulate stop transition
            input_high = OffsetInput(
                ac_internal_temp=22.0,
                room_temp=23.0 + i * 0.1,
                outdoor_temp=None,
                mode="cool",
                power_consumption=300.0,
                time_of_day=datetime.now().time(),
                day_of_week=datetime.now().weekday()
            )
            engine.calculate_offset(input_high)
            
            input_idle = OffsetInput(
                ac_internal_temp=22.0,
                room_temp=23.0 + i * 0.1,
                outdoor_temp=None,
                mode="cool",
                power_consumption=5.0,
                time_of_day=datetime.now().time(),
                day_of_week=datetime.now().weekday()
            )
            engine.calculate_offset(input_idle)
        
        # Add more start transitions to reach minimum
        for i in range(2):
            input_idle = OffsetInput(
                ac_internal_temp=25.0,
                room_temp=26.2 + i * 0.1,
                outdoor_temp=None,
                mode="cool",
                power_consumption=5.0,
                time_of_day=datetime.now().time(),
                day_of_week=datetime.now().weekday()
            )
            engine.calculate_offset(input_idle)
            
            input_high = OffsetInput(
                ac_internal_temp=25.0,
                room_temp=26.2 + i * 0.1,
                outdoor_temp=None,
                mode="cool",
                power_consumption=300.0,
                time_of_day=datetime.now().time(),
                day_of_week=datetime.now().weekday()
            )
            engine.calculate_offset(input_high)
        
        # Check final state with sufficient data
        attrs = switch.extra_state_attributes
        assert attrs["hysteresis_ready"] is True
        assert attrs["start_samples_collected"] == 5
        assert attrs["stop_samples_collected"] == 5
        assert isinstance(attrs["learned_start_threshold"], str)
        assert "°C" in attrs["learned_start_threshold"]
        assert isinstance(attrs["learned_stop_threshold"], str)
        assert "°C" in attrs["learned_stop_threshold"]

    def test_no_power_sensor_integration(self, mock_config_entry):
        """Test integration when no power sensor is configured."""
        # GIVEN: Engine without power sensor
        config = {"enable_learning": True}
        engine = OffsetEngine(config)
        switch = LearningSwitch(mock_config_entry, engine, "Test Climate", "climate.test")
        
        # WHEN: Getting attributes
        attrs = switch.extra_state_attributes
        
        # THEN: Should show disabled state consistently
        assert attrs["hysteresis_enabled"] is False
        assert attrs["hysteresis_state"] == "No power sensor"
        assert attrs["learned_start_threshold"] == "Not available"
        assert attrs["learned_stop_threshold"] == "Not available"
        assert attrs["temperature_window"] == "Not available"
        assert attrs["start_samples_collected"] == 0
        assert attrs["stop_samples_collected"] == 0
        assert attrs["hysteresis_ready"] is False

    def test_error_propagation_through_stack(self, config_with_power_sensor, mock_config_entry):
        """Test that errors in hysteresis learner are handled gracefully."""
        # GIVEN: Engine with mocked failing hysteresis learner
        engine = OffsetEngine(config_with_power_sensor)
        
        # Mock the hysteresis learner to fail
        failing_learner = Mock(spec=HysteresisLearner)
        failing_learner.has_sufficient_data = False
        failing_learner.serialize_for_persistence = Mock(side_effect=RuntimeError("Test error"))
        failing_learner.get_hysteresis_state = Mock(side_effect=ValueError("State error"))
        failing_learner._start_temps = []
        failing_learner._stop_temps = []
        failing_learner.learned_start_threshold = None
        failing_learner.learned_stop_threshold = None
        
        engine._hysteresis_learner = failing_learner
        
        switch = LearningSwitch(mock_config_entry, engine, "Test Climate", "climate.test")
        
        # WHEN: Getting attributes (should not crash)
        attrs = switch.extra_state_attributes
        
        # THEN: Should have safe defaults
        assert attrs["samples_collected"] >= 0  # Should have basic info
        # Error handling might result in missing hysteresis attributes or defaults
        if "hysteresis_state" in attrs:
            assert isinstance(attrs["hysteresis_state"], str)

    def test_threshold_persistence_integration(self, config_with_power_sensor, mock_config_entry):
        """Test that learned thresholds persist through save/load cycle."""
        # GIVEN: Engine with learned data
        engine = OffsetEngine(config_with_power_sensor)
        
        # Add sufficient samples
        engine._hysteresis_learner._start_temps.extend([26.5, 26.6, 26.4, 26.7, 26.3])
        engine._hysteresis_learner._stop_temps.extend([23.0, 23.2, 23.1, 23.3, 22.9])
        engine._hysteresis_learner._update_thresholds()
        
        # Get initial state
        switch1 = LearningSwitch(mock_config_entry, engine, "Test Climate", "climate.test")
        attrs1 = switch1.extra_state_attributes
        
        # Serialize the data
        persistence_data = {
            "hysteresis_data": engine._hysteresis_learner.serialize_for_persistence()
        }
        
        # Create new engine and restore
        engine2 = OffsetEngine(config_with_power_sensor)
        engine2._hysteresis_learner.restore_from_persistence(persistence_data["hysteresis_data"])
        
        # Create switch with restored engine
        switch2 = LearningSwitch(mock_config_entry, engine2, "Test Climate", "climate.test")
        attrs2 = switch2.extra_state_attributes
        
        # THEN: Attributes should match
        assert attrs2["learned_start_threshold"] == attrs1["learned_start_threshold"]
        assert attrs2["learned_stop_threshold"] == attrs1["learned_stop_threshold"]
        assert attrs2["temperature_window"] == attrs1["temperature_window"]
        assert attrs2["start_samples_collected"] == attrs1["start_samples_collected"]
        assert attrs2["stop_samples_collected"] == attrs1["stop_samples_collected"]
        assert attrs2["hysteresis_ready"] == attrs1["hysteresis_ready"]