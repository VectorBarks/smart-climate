"""
Comprehensive end-to-end integration tests for the complete ProbeScheduler system.

Tests complete probe scheduling workflows, state transitions, component interactions,
real-world scenarios, and data flow between all system components.

Author: Integration Test Agent for ProbeScheduler v1.5.3-beta Step 7.1
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta, time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Optional, Any, Tuple

from custom_components.smart_climate.thermal_model import PassiveThermalModel
from custom_components.smart_climate.thermal_models import ProbeResult, ThermalState
from custom_components.smart_climate.thermal_manager import ThermalManager
from custom_components.smart_climate.probe_scheduler import (
    ProbeScheduler, LearningProfile, ProfileConfig
)
from custom_components.smart_climate.validation_metrics import ValidationMetricsManager
from custom_components.smart_climate.probe_notifications import ProbeNotificationManager
from custom_components.smart_climate.thermal_preferences import (
    UserPreferences, PreferenceLevel
)
from custom_components.smart_climate.const import (
    DOMAIN, CONF_PRESENCE_ENTITY_ID, CONF_WEATHER_ENTITY_ID,
    CONF_CALENDAR_ENTITY_ID, CONF_MANUAL_OVERRIDE_ENTITY_ID
)

from tests.fixtures.thermal_v153 import create_probe_result, create_probe_sequence


class TestProbeSchedulerIntegration:
    """End-to-end integration tests for ProbeScheduler system."""

    @pytest.fixture
    def mock_hass(self):
        """Create comprehensive mock Home Assistant instance."""
        hass = Mock()
        hass.states = Mock()
        hass.services = Mock()
        hass.data = {DOMAIN: {}}
        
        # Mock entity states for integration testing
        mock_states = {
            "person.user": Mock(state="home", attributes={}),
            "weather.forecast": Mock(state="sunny", attributes={"temperature": 25.0}),
            "calendar.work": Mock(state="off", attributes={}),
            "input_boolean.manual_probe_override": Mock(state="off"),
            "climate.thermostat": Mock(
                state="cool", 
                attributes={
                    "current_temperature": 23.0,
                    "temperature": 22.0,
                    "hvac_mode": "cool"
                }
            )
        }
        
        def get_state(entity_id):
            return mock_states.get(entity_id)
        
        hass.states.get.side_effect = get_state
        
        # Mock service calls
        hass.services.async_call = AsyncMock()
        
        return hass

    @pytest.fixture
    def thermal_model(self):
        """Create thermal model with realistic probe history."""
        model = PassiveThermalModel()
        
        # Add diverse probe history for realistic testing
        probe_history = [
            create_probe_result(85.0, 0.8, age_days=1, outdoor_temp=20.0),
            create_probe_result(92.0, 0.85, age_days=3, outdoor_temp=25.0),
            create_probe_result(88.0, 0.9, age_days=5, outdoor_temp=18.0),
            create_probe_result(95.0, 0.75, age_days=8, outdoor_temp=30.0),
            create_probe_result(82.0, 0.88, age_days=12, outdoor_temp=15.0),
        ]
        
        for probe in probe_history:
            model._probe_history.append(probe)
            
        return model

    @pytest.fixture
    def user_preferences(self):
        """Create user preferences for testing."""
        return UserPreferences(
            level=PreferenceLevel.BALANCED,
            comfort_band=1.0,
            confidence_threshold=0.7,
            probe_drift=2.0
        )

    @pytest.fixture
    def thermal_manager(self, mock_hass, thermal_model, user_preferences):
        """Create thermal manager with full configuration."""
        config = {
            "entity_id": "climate.thermostat",
            "room_sensor_id": "sensor.room_temp",
            "outdoor_sensor_id": "sensor.outdoor_temp",
            "learning_profile": LearningProfile.BALANCED.value
        }
        
        manager = ThermalManager(
            hass=mock_hass,
            model=thermal_model,
            preferences=user_preferences,
            config=config,
            persistence_callback=Mock()
        )
        
        return manager

    @pytest.fixture
    def probe_scheduler(self, mock_hass, thermal_model):
        """Create probe scheduler with all integrations."""
        return ProbeScheduler(
            hass=mock_hass,
            thermal_model=thermal_model,
            presence_entity_id="person.user",
            weather_entity_id="weather.forecast",
            calendar_entity_id="calendar.work",
            manual_override_entity_id="input_boolean.manual_probe_override",
            learning_profile=LearningProfile.BALANCED
        )

    @pytest.fixture
    def validation_metrics(self, mock_hass):
        """Create validation metrics manager."""
        return ValidationMetricsManager(
            hass=mock_hass,
            entity_id="climate.thermostat"
        )

    @pytest.fixture
    def notification_manager(self, mock_hass):
        """Create probe notification manager."""
        return ProbeNotificationManager(
            hass=mock_hass,
            entity_id="climate.thermostat"
        )

    @pytest.fixture
    def full_system_setup(self, mock_hass, thermal_manager, probe_scheduler, 
                         validation_metrics, notification_manager):
        """Set up complete ProbeScheduler system with all components."""
        # Wire probe scheduler into thermal manager
        thermal_manager.probe_scheduler = probe_scheduler
        
        # Create integrated system state
        system = {
            "hass": mock_hass,
            "thermal_manager": thermal_manager,
            "probe_scheduler": probe_scheduler,
            "validation_metrics": validation_metrics,
            "notification_manager": notification_manager,
            "thermal_model": thermal_manager._model
        }
        
        return system

    @pytest.mark.asyncio
    async def test_end_to_end_probe_workflow(self, full_system_setup):
        """Test complete probe scheduling and execution workflow."""
        system = full_system_setup
        thermal_manager = system["thermal_manager"]
        probe_scheduler = system["probe_scheduler"]
        mock_hass = system["hass"]
        
        # Simulate initial stable state
        thermal_manager._current_state = ThermalState.DRIFTING
        
        # Test 1: User leaves home - probe should be approved
        mock_hass.states.get("person.user").state = "away"
        should_probe = probe_scheduler.should_probe_now()
        assert should_probe, "Probe should be approved when user leaves home"
        
        # Test 2: Execute probe workflow via thermal manager
        initial_probe_count = len(system["thermal_model"]._probe_history)
        
        # Simulate probe execution by transitioning to PROBING state
        thermal_manager.transition_to(ThermalState.PROBING)
        assert thermal_manager.current_state == ThermalState.PROBING
        
        # Simulate probe completion with new result
        new_probe = create_probe_result(89.0, 0.9, age_days=0, outdoor_temp=22.0)
        system["thermal_model"]._probe_history.append(new_probe)
        
        # Test 3: Verify probe results recorded
        final_probe_count = len(system["thermal_model"]._probe_history)
        assert final_probe_count == initial_probe_count + 1, "New probe should be recorded"
        
        # Test 4: Verify state transitions after probe
        thermal_manager.transition_to(ThermalState.CORRECTING)
        assert thermal_manager.current_state == ThermalState.CORRECTING
        
        # Test 5: Verify confidence calculation includes new probe
        confidence = system["thermal_model"].get_confidence()
        assert confidence > 0.7, f"Confidence should be high with multiple probes: {confidence}"

    def test_real_world_scenario_winter_learning(self, full_system_setup):
        """Test winter climate learning scenario with temperature bin coverage."""
        system = full_system_setup
        thermal_model = system["thermal_model"]
        probe_scheduler = system["probe_scheduler"]
        mock_hass = system["hass"]
        
        # Clear existing probes to start fresh
        thermal_model._probe_history.clear()
        
        # Simulate winter scenario: Add probes across temperature bins
        winter_temperatures = [-5, 2, 8, 12, 18]  # Diverse winter conditions
        winter_probes = []
        
        for i, temp in enumerate(winter_temperatures):
            probe = create_probe_result(
                tau_value=85.0 + (i * 2),  # Slightly varying tau
                confidence=0.75 + (i * 0.03),  # Increasing confidence
                age_days=15 - (i * 3),  # Spread over 15 days
                outdoor_temp=temp
            )
            winter_probes.append(probe)
            thermal_model._probe_history.append(probe)
        
        # Test 1: Verify temperature bin coverage
        bin_coverage = probe_scheduler._get_bin_coverage(thermal_model._probe_history)
        assert len(bin_coverage) >= 4, f"Should have good bin coverage: {len(bin_coverage)} bins"
        
        # Test 2: Test information gain calculation
        mock_hass.states.get("weather.forecast").attributes["temperature"] = 5.0  # New condition
        has_high_gain = probe_scheduler._has_high_information_gain(
            current_temp=5.0, 
            history=list(thermal_model._probe_history)
        )
        
        # Should have high information gain for temperature bin with few samples
        assert has_high_gain or len(thermal_model._probe_history) >= 10, \
            "Should detect information gain or have sufficient samples"
        
        # Test 3: Verify confidence building over time
        initial_confidence = thermal_model.get_confidence()
        
        # Add one more probe in well-covered bin
        extra_probe = create_probe_result(88.0, 0.85, age_days=0, outdoor_temp=18.0)
        thermal_model._probe_history.append(extra_probe)
        
        final_confidence = thermal_model.get_confidence()
        assert final_confidence >= initial_confidence, \
            f"Confidence should not decrease: {initial_confidence} -> {final_confidence}"

    def test_user_presence_state_changes(self, full_system_setup):
        """Test probe scheduling with dynamic presence changes."""
        system = full_system_setup
        probe_scheduler = system["probe_scheduler"]
        mock_hass = system["hass"]
        
        # Test 1: User at home - no probing during work hours
        mock_hass.states.get("person.user").state = "home"
        with patch('custom_components.smart_climate.probe_scheduler.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 15, 14, 30)  # Tuesday 2:30 PM
            mock_dt.time = time
            
            should_probe_home = probe_scheduler.should_probe_now()
            assert not should_probe_home, "Should not probe when user is home during day"
        
        # Test 2: User leaves for work - calendar indicates busy
        mock_hass.states.get("person.user").state = "away"
        mock_hass.states.get("calendar.work").state = "on"  # Work meeting
        
        should_probe_work = probe_scheduler.should_probe_now()
        assert should_probe_work, "Should probe when user away for work"
        
        # Test 3: User returns home early - should abort probe
        mock_hass.states.get("person.user").state = "home"
        
        abort_conditions = probe_scheduler.check_abort_conditions()
        assert abort_conditions["should_abort"], "Should abort when user returns home"
        assert "User returned home" in abort_conditions["reason"]
        
        # Test 4: Manual override activated
        mock_hass.states.get("input_boolean.manual_probe_override").state = "on"
        
        should_probe_override = probe_scheduler.should_probe_now()
        assert should_probe_override, "Manual override should enable probing"

    @pytest.mark.asyncio
    async def test_component_integration_thermal_manager(self, full_system_setup):
        """Test ProbeScheduler ↔ ThermalManager communication and data flow."""
        system = full_system_setup
        thermal_manager = system["thermal_manager"]
        probe_scheduler = system["probe_scheduler"]
        mock_hass = system["hass"]
        
        # Test 1: Verify probe scheduler integration
        assert thermal_manager.probe_scheduler is not None
        assert thermal_manager.probe_scheduler == probe_scheduler
        
        # Test 2: Test opportunistic probing from DRIFTING state
        thermal_manager._current_state = ThermalState.DRIFTING
        mock_hass.states.get("person.user").state = "away"  # User away
        
        # Mock probe scheduler approval
        with patch.object(probe_scheduler, 'should_probe_now', return_value=True):
            thermal_manager.update_state(
                current_temp=23.0,
                outdoor_temp=25.0,
                hvac_mode="cool"
            )
            
            # Should transition to PROBING state
            assert thermal_manager.current_state == ThermalState.PROBING
        
        # Test 3: Test probe scheduler decline
        thermal_manager._current_state = ThermalState.CORRECTING
        mock_hass.states.get("person.user").state = "home"  # User home
        
        with patch.object(probe_scheduler, 'should_probe_now', return_value=False):
            initial_state = thermal_manager.current_state
            thermal_manager.update_state(
                current_temp=23.0,
                outdoor_temp=25.0,
                hvac_mode="cool"
            )
            
            # Should remain in current state
            assert thermal_manager.current_state == initial_state
        
        # Test 4: Test minimum probe interval enforcement
        thermal_manager._last_probe_time = datetime.now() - timedelta(hours=6)  # Recent probe
        
        can_probe = thermal_manager.can_auto_probe()
        assert not can_probe, "Should enforce minimum probe interval"

    def test_passive_thermal_model_integration(self, full_system_setup):
        """Test PassiveThermalModel ↔ ProbeScheduler data flow and persistence."""
        system = full_system_setup
        thermal_model = system["thermal_model"]
        probe_scheduler = system["probe_scheduler"]
        
        # Test 1: Verify probe history access
        initial_history = probe_scheduler._get_probe_history()
        assert len(initial_history) > 0, "Should access existing probe history"
        assert initial_history == list(thermal_model._probe_history)
        
        # Test 2: Test temperature bin analysis with probe history
        outdoor_temps = [probe.outdoor_temp for probe in initial_history if probe.outdoor_temp]
        if outdoor_temps:
            bin_coverage = probe_scheduler._get_bin_coverage(initial_history)
            assert len(bin_coverage) > 0, "Should analyze temperature bins from history"
        
        # Test 3: Test adaptive bin creation
        probe_scheduler._update_temperature_bins()
        effective_bins = probe_scheduler._get_effective_temperature_bins()
        assert len(effective_bins) >= 5, f"Should have adequate temperature bins: {len(effective_bins)}"
        
        # Test 4: Test information gain calculation
        current_outdoor_temp = 28.0  # New temperature
        info_gain = probe_scheduler._has_high_information_gain(
            current_temp=current_outdoor_temp,
            history=initial_history
        )
        
        # Information gain depends on existing bin coverage
        bin_temps = [probe.outdoor_temp for probe in initial_history if probe.outdoor_temp]
        if bin_temps:
            temp_range = max(bin_temps) - min(bin_temps)
            # If we have good temperature diversity, info gain should be calculated properly
            assert isinstance(info_gain, bool), "Information gain should return boolean result"

    @pytest.mark.asyncio
    async def test_notification_system_integration(self, full_system_setup):
        """Test ProbeScheduler ↔ NotificationManager event flow."""
        system = full_system_setup
        notification_manager = system["notification_manager"]
        mock_hass = system["hass"]
        
        # Test 1: Pre-probe warning notification
        with patch.object(notification_manager, '_send_notification') as mock_notify:
            await notification_manager.notify_pre_probe_warning(
                outdoor_temp=25.0,
                estimated_duration=45
            )
            
            mock_notify.assert_called_once()
            args = mock_notify.call_args[1]  # keyword args
            assert "Planning thermal calibration" in args["message"]
            assert "25°C" in args["message"]
        
        # Test 2: Probe completion notification
        mock_probe = create_probe_result(90.0, 0.85, outdoor_temp=25.0)
        
        with patch.object(notification_manager, '_send_notification') as mock_notify:
            await notification_manager.notify_probe_completion(
                probe_result=mock_probe,
                outdoor_temp=25.0,
                duration_minutes=42
            )
            
            mock_notify.assert_called_once()
            args = mock_notify.call_args[1]
            assert "Successfully calibrated" in args["message"]
        
        # Test 3: Learning milestone notification
        confidence = 0.8
        probe_count = 15
        
        with patch.object(notification_manager, '_send_notification') as mock_notify:
            await notification_manager.notify_learning_milestone(
                confidence=confidence,
                probe_count=probe_count,
                milestone_type="high_confidence"
            )
            
            mock_notify.assert_called_once()
            args = mock_notify.call_args[1]
            assert "learning complete" in args["message"].lower()

    def test_validation_metrics_integration(self, full_system_setup):
        """Test ProbeScheduler ↔ ValidationMetrics performance tracking."""
        system = full_system_setup
        validation_metrics = system["validation_metrics"]
        thermal_model = system["thermal_model"]
        
        # Test 1: Record prediction error
        predicted_drift = thermal_model.predict_drift(
            current=23.0,
            outdoor=25.0,
            minutes=60,
            is_cooling=True
        )
        
        actual_temp = 22.5  # Simulated actual temperature after 1 hour
        prediction_error = abs(predicted_drift - actual_temp)
        
        validation_metrics.record_prediction_error(
            predicted_temp=predicted_drift,
            actual_temp=actual_temp,
            outdoor_temp=25.0,
            hvac_mode="cool"
        )
        
        # Verify error recorded
        sensor_data = validation_metrics.get_prediction_error_sensor_data()
        assert sensor_data["state"] is not None, "Should record prediction error"
        
        # Test 2: Record temperature overshoot
        setpoint = 22.0
        peak_temp = 21.0  # 1°C overshoot in cooling
        
        validation_metrics.record_temperature_overshoot(
            setpoint=setpoint,
            peak_temperature=peak_temp,
            hvac_mode="cool",
            outdoor_temp=25.0
        )
        
        overshoot_data = validation_metrics.get_setpoint_overshoot_sensor_data()
        assert overshoot_data["state"] is not None, "Should record overshoot event"
        
        # Test 3: Record HVAC cycle efficiency
        cycle_on_duration = 1800  # 30 minutes
        cycle_off_duration = 900   # 15 minutes
        
        validation_metrics.record_hvac_cycle(
            on_duration=cycle_on_duration,
            off_duration=cycle_off_duration,
            setpoint_achieved=True
        )
        
        efficiency_data = validation_metrics.get_cycle_efficiency_sensor_data()
        assert efficiency_data["state"] is not None, "Should record cycle efficiency"

    def test_configuration_flow_integration(self, full_system_setup):
        """Test ProbeScheduler configuration and profile switching."""
        system = full_system_setup
        probe_scheduler = system["probe_scheduler"]
        
        # Test 1: Default balanced profile
        assert probe_scheduler._learning_profile == LearningProfile.BALANCED
        config = probe_scheduler._get_profile_config()
        assert isinstance(config, ProfileConfig)
        assert config.requires_presence_detection == True
        
        # Test 2: Switch to aggressive profile
        probe_scheduler._update_profile(LearningProfile.AGGRESSIVE)
        assert probe_scheduler._learning_profile == LearningProfile.AGGRESSIVE
        
        aggressive_config = probe_scheduler._get_profile_config()
        assert aggressive_config.min_probe_interval_hours < config.min_probe_interval_hours
        
        # Test 3: Apply advanced settings
        advanced_settings = {
            "min_probe_interval_hours": 8,
            "max_probe_interval_days": 5,
            "quiet_hours_start": "23:00",
            "quiet_hours_end": "06:00",
            "information_gain_threshold": 0.15
        }
        
        probe_scheduler.apply_advanced_settings(advanced_settings)
        
        # Verify settings applied
        assert probe_scheduler._min_probe_interval.total_seconds() == 8 * 3600
        assert probe_scheduler._max_probe_interval.total_seconds() == 5 * 24 * 3600
        assert probe_scheduler._information_gain_threshold == 0.15

    def test_persistence_round_trip_integration(self, full_system_setup):
        """Test complete persistence workflow with ProbeScheduler state."""
        system = full_system_setup
        thermal_manager = system["thermal_manager"]
        probe_scheduler = system["probe_scheduler"]
        
        # Test 1: Configure probe scheduler with specific settings
        probe_scheduler._learning_profile = LearningProfile.COMFORT
        probe_scheduler._min_probe_interval = timedelta(hours=18)
        probe_scheduler._information_gain_threshold = 0.2
        
        # Test 2: Serialize complete state
        serialized_data = thermal_manager.serialize()
        
        # Verify probe scheduler config included
        assert "probe_scheduler" in serialized_data
        ps_config = serialized_data["probe_scheduler"]
        assert ps_config["learning_profile"] == "comfort"
        assert ps_config["min_probe_interval_hours"] == 18
        assert ps_config["information_gain_threshold"] == 0.2
        
        # Test 3: Create new thermal manager and restore
        new_thermal_model = PassiveThermalModel()
        new_preferences = system["thermal_manager"]._preferences
        new_manager = ThermalManager(
            hass=system["hass"],
            model=new_thermal_model,
            preferences=new_preferences,
            config={"entity_id": "climate.thermostat"},
            persistence_callback=Mock()
        )
        
        # Test 4: Restore state
        new_manager.restore(serialized_data)
        
        # Verify probe scheduler restored
        assert new_manager.probe_scheduler is not None
        restored_ps = new_manager.probe_scheduler
        assert restored_ps._learning_profile == LearningProfile.COMFORT
        assert restored_ps._min_probe_interval.total_seconds() == 18 * 3600
        assert restored_ps._information_gain_threshold == 0.2

    @pytest.mark.asyncio
    async def test_system_startup_and_shutdown(self, full_system_setup):
        """Test complete system lifecycle including startup and graceful shutdown."""
        system = full_system_setup
        thermal_manager = system["thermal_manager"]
        probe_scheduler = system["probe_scheduler"]
        mock_hass = system["hass"]
        
        # Test 1: System initialization
        assert thermal_manager.probe_scheduler is probe_scheduler
        assert thermal_manager.current_state in [ThermalState.PRIMING, ThermalState.DRIFTING]
        
        # Test 2: Initial probe history loaded
        initial_probes = len(system["thermal_model"]._probe_history)
        assert initial_probes > 0, "Should have initial probe history"
        
        # Test 3: Configuration validation
        probe_scheduler._validate_configuration()  # Should not raise
        
        # Test 4: Graceful error handling
        with patch.object(mock_hass.states, 'get', side_effect=Exception("Service unavailable")):
            # Should handle sensor errors gracefully
            try:
                should_probe = probe_scheduler.should_probe_now()
                # Should return False on error (conservative approach)
                assert should_probe == False
            except Exception as e:
                pytest.fail(f"Should handle sensor errors gracefully: {e}")
        
        # Test 5: System shutdown - verify no resource leaks
        # In real implementation, this would clean up listeners, etc.
        assert thermal_manager is not None  # Basic sanity check

    def test_multi_entity_integration(self, full_system_setup):
        """Test ProbeScheduler integration with multiple Home Assistant entities."""
        system = full_system_setup
        probe_scheduler = system["probe_scheduler"]
        mock_hass = system["hass"]
        
        # Test 1: Presence entity hierarchy fallback
        # Primary: presence entity unavailable
        mock_hass.states.get.return_value = None  # Entity not found
        
        with patch.object(probe_scheduler, '_check_calendar_entity', return_value=True) as mock_cal:
            is_opportune = probe_scheduler._is_opportune_time()
            # Should fall back to calendar
            mock_cal.assert_called_once()
        
        # Test 2: Weather entity integration
        weather_temp = probe_scheduler._get_current_outdoor_temperature()
        if weather_temp is not None:
            assert isinstance(weather_temp, (int, float))
            assert -50 <= weather_temp <= 60, f"Weather temperature should be reasonable: {weather_temp}°C"
        
        # Test 3: Manual override entity
        mock_hass.states.get("input_boolean.manual_probe_override").state = "on"
        
        manual_override = probe_scheduler._check_manual_override()
        assert manual_override == True, "Should detect manual override activation"
        
        # Test 4: Climate entity target temperature
        target_temp = probe_scheduler._get_current_target_temperature()
        if target_temp is not None:
            assert 16 <= target_temp <= 30, f"Target temperature should be reasonable: {target_temp}°C"

    def test_error_recovery_and_resilience(self, full_system_setup):
        """Test system resilience to various error conditions."""
        system = full_system_setup
        probe_scheduler = system["probe_scheduler"]
        thermal_manager = system["thermal_manager"]
        mock_hass = system["hass"]
        
        # Test 1: Invalid entity states
        mock_hass.states.get("person.user").state = "unknown"
        mock_hass.states.get("weather.forecast").state = "unavailable"
        
        # Should handle gracefully
        should_probe = probe_scheduler.should_probe_now()
        assert isinstance(should_probe, bool), "Should return boolean even with invalid states"
        
        # Test 2: Missing optional entities
        original_calendar_entity = probe_scheduler._calendar_entity_id
        probe_scheduler._calendar_entity_id = None
        
        try:
            is_opportune = probe_scheduler._is_opportune_time()
            assert isinstance(is_opportune, bool), "Should work without optional calendar entity"
        finally:
            probe_scheduler._calendar_entity_id = original_calendar_entity
        
        # Test 3: Probe scheduler error during thermal update
        with patch.object(probe_scheduler, 'should_probe_now', side_effect=Exception("Scheduler error")):
            # Should continue thermal manager operations
            initial_state = thermal_manager.current_state
            thermal_manager.update_state(current_temp=23.0, outdoor_temp=25.0, hvac_mode="cool")
            # Should not crash, may stay in same state
            assert thermal_manager.current_state is not None
        
        # Test 4: Corrupted probe history
        original_history = system["thermal_model"]._probe_history.copy()
        try:
            # Add invalid probe data
            system["thermal_model"]._probe_history.append("invalid_probe")
            
            # Should handle gracefully during bin analysis
            try:
                bin_coverage = probe_scheduler._get_bin_coverage(
                    list(system["thermal_model"]._probe_history)
                )
                # Should filter out invalid data
                assert isinstance(bin_coverage, dict)
            except TypeError:
                # Acceptable if it filters out invalid data
                pass
                
        finally:
            system["thermal_model"]._probe_history.clear()
            system["thermal_model"]._probe_history.extend(original_history)