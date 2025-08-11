"""ABOUTME: Integration tests for the opportunistic calibration system.
Tests the complete workflow from stability detection to offset capture."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from freezegun import freeze_time

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.smart_climate.coordinator import SmartClimateCoordinator
from custom_components.smart_climate.thermal_manager import ThermalManager
from custom_components.smart_climate.thermal_models import ThermalState
from custom_components.smart_climate.thermal_stability import StabilityDetector
from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.thermal_models import ThermalConstants
from custom_components.smart_climate.thermal_preferences import UserPreferences, PreferenceLevel
from custom_components.smart_climate.thermal_model import PassiveThermalModel
from custom_components.smart_climate.button import SmartClimateCalibrationButton


class TestOpportunisticCalibrationIntegration:
    """Integration tests for the complete opportunistic calibration system."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = Mock()
        hass.data = {}
        return hass

    @pytest.fixture 
    def mock_config_entry(self):
        """Create a mock config entry."""
        config_entry = Mock()
        config_entry.entry_id = "test_entry"
        config_entry.options = {
            "calibration_idle_minutes": 30,
            "calibration_drift_threshold": 0.1
        }
        return config_entry

    @pytest.fixture
    def stability_detector(self, mock_config_entry):
        """Create a StabilityDetector with test configuration."""
        return StabilityDetector(
            idle_threshold_minutes=mock_config_entry.options["calibration_idle_minutes"],
            drift_threshold=mock_config_entry.options["calibration_drift_threshold"]
        )

    @pytest.fixture
    def thermal_manager(self, mock_hass):
        """Create a ThermalManager with StabilityDetector integrated."""
        thermal_model = PassiveThermalModel()
        preferences = UserPreferences(
            level=PreferenceLevel.BALANCED,
            comfort_band=0.8,
            confidence_threshold=0.7,
            probe_drift=2.0
        )
        # Create thermal manager with stability detector
        config = {
            "calibration_idle_minutes": 30,
            "calibration_drift_threshold": 0.1
        }
        
        manager = ThermalManager(
            hass=mock_hass,
            thermal_model=thermal_model,
            preferences=preferences,
            config=config
        )
        
        return manager

    @pytest.fixture
    def mock_offset_engine(self):
        """Create a mock OffsetEngine."""
        engine = Mock()
        engine.calculate_offset = Mock(return_value=Mock(offset=2.5, clamped=False, reason="Test"))
        engine.pause_learning = Mock()
        engine.resume_learning = Mock()
        engine.save_learning_data = AsyncMock()
        return engine

    @pytest.fixture
    def mock_coordinator(self, mock_hass, mock_config_entry, mock_offset_engine):
        """Create a mock coordinator."""
        coordinator = Mock()
        coordinator.hass = mock_hass
        coordinator.config_entry = mock_config_entry
        coordinator.async_request_refresh = AsyncMock()
        
        # Setup hass.data structure as expected by button
        mock_hass.data = {
            "smart_climate": {
                "test_entry": {
                    "thermal_components": {
                        "climate.test": {
                            "thermal_manager": None  # Will be set by test
                        }
                    },
                    "coordinators": {
                        "climate.test": coordinator
                    },
                    "offset_engines": {
                        "climate.test": mock_offset_engine
                    }
                }
            }
        }
        
        return coordinator

    def test_stability_triggers_calibration_naturally(self, thermal_manager):
        """Test that stable conditions naturally trigger calibration transitions."""
        # Setup: Start in PRIMING state and ensure on_enter is called
        thermal_manager.transition_to(ThermalState.PRIMING)
        assert thermal_manager.current_state == ThermalState.PRIMING
        
        # Manually trigger on_enter to set start_time (normally done by transition_to)
        current_handler = thermal_manager._state_handlers.get(ThermalState.PRIMING)
        if current_handler:
            current_handler.on_enter(thermal_manager)
        
        # Mock the stability detector to return stable conditions
        with patch.object(thermal_manager.stability_detector, 'is_stable_for_calibration', return_value=True):
            # Simulate state handler execution (normally triggered by thermal system updates)
            current_handler = thermal_manager._state_handlers.get(thermal_manager.current_state)
            if current_handler:
                # Execute the state handler which should detect stability and return CALIBRATING
                next_state = current_handler.execute(thermal_manager)
                if next_state:
                    thermal_manager.transition_to(next_state)
            
        # Verify calibration was triggered
        assert thermal_manager.current_state == ThermalState.CALIBRATING

    def test_manual_button_forces_calibration(self, mock_hass, mock_config_entry, thermal_manager, mock_coordinator):
        """Test that the manual calibration button forces immediate calibration."""
        # Setup: Update hass.data with our thermal manager
        mock_hass.data["smart_climate"]["test_entry"]["thermal_components"]["climate.test"]["thermal_manager"] = thermal_manager
        
        # Create calibration button
        button = SmartClimateCalibrationButton(mock_hass, mock_config_entry, "climate.test")
        
        # Setup: Start in DRIFTING state (not naturally stable)
        thermal_manager.transition_to(ThermalState.DRIFTING)
        assert thermal_manager.current_state == ThermalState.DRIFTING
        
        # Simulate button press
        with patch.object(thermal_manager, 'force_calibration', wraps=thermal_manager.force_calibration) as mock_force:
            async def run_test():
                await button.async_press()
                
            # Run the async test
            import asyncio
            asyncio.run(run_test())
            
            # Verify force_calibration was called
            mock_force.assert_called_once()
            
            # Verify state transition occurred
            assert thermal_manager.current_state == ThermalState.CALIBRATING
            
            # Verify coordinator refresh was requested
            mock_coordinator.async_request_refresh.assert_called_once()

    def test_config_changes_affect_detection_thresholds(self, mock_hass):
        """Test that configuration changes properly affect stability detection thresholds."""
        # Test different configuration scenarios
        configs = [
            {"calibration_idle_minutes": 15, "calibration_drift_threshold": 0.05},
            {"calibration_idle_minutes": 60, "calibration_drift_threshold": 0.2},
            {"calibration_idle_minutes": 45, "calibration_drift_threshold": 0.15}
        ]
        
        for config in configs:
            detector = StabilityDetector(
                idle_threshold_minutes=config["calibration_idle_minutes"],
                drift_threshold=config["calibration_drift_threshold"]
            )
            
            # Verify thresholds are set correctly
            expected_idle = timedelta(minutes=config["calibration_idle_minutes"])
            assert detector._idle_threshold == expected_idle
            assert detector._drift_threshold == config["calibration_drift_threshold"]
            
            # Test detection with the configured thresholds
            base_time = datetime.now()
            with freeze_time(base_time) as frozen_time:
                detector.update("idle", 22.0)
                
                # Wait exactly the configured idle time
                frozen_time.tick(delta=timedelta(minutes=config["calibration_idle_minutes"]))
                
                # Add temperature readings with drift just below threshold
                drift_temp = config["calibration_drift_threshold"] * 0.9  # 90% of threshold
                detector.update("idle", 22.0)
                detector.update("idle", 22.0 + drift_temp)
                
                # Should be stable since we're at threshold times
                assert detector.is_stable_for_calibration() == True
                
                # Test with drift just above threshold
                detector.update("idle", 22.0 + config["calibration_drift_threshold"] * 1.1)
                assert detector.is_stable_for_calibration() == False

    def test_offset_capture_still_works_during_calibration(self, thermal_manager, mock_offset_engine):
        """Test that offset capture functionality works correctly during calibration state."""
        # Transition to calibrating state
        thermal_manager.transition_to(ThermalState.CALIBRATING)
        assert thermal_manager.current_state == ThermalState.CALIBRATING
        
        # Verify calibrating state characteristics
        calibrating_state = thermal_manager._state_handlers[ThermalState.CALIBRATING]
        
        # Test that calibration uses tight comfort bands for clean readings
        window = thermal_manager.get_operating_window(22.0, 25.0, "cool")
        window_size = window[1] - window[0]  # upper - lower
        
        # Calibration should use tighter bands than normal operation
        # (exact values depend on implementation but should be < 1.0°C)
        assert window_size < 1.0, f"Calibration window too wide: {window_size}°C"
        
        # Test that offset engine can still calculate and capture offsets
        # This simulates the offset calculation that would happen during calibration
        with patch.object(mock_offset_engine, 'calculate_offset') as mock_calc:
            mock_calc.return_value = Mock(offset=1.5, clamped=False, reason="Calibration")
            
            # This would be called by the climate entity during calibration
            result = mock_offset_engine.calculate_offset(Mock())
            
            assert result.offset == 1.5
            assert result.reason == "Calibration"
            mock_calc.assert_called_once()

    def test_calibration_transitions_recorded_correctly(self, thermal_manager):
        """Test that calibration state transitions are properly recorded and logged."""
        initial_state = ThermalState.DRIFTING
        thermal_manager.transition_to(initial_state)
        
        # Monitor state changes
        with patch('custom_components.smart_climate.thermal_manager._LOGGER') as mock_logger:
            # Force calibration
            thermal_manager.force_calibration()
            
            # Verify state transition
            assert thermal_manager.current_state == ThermalState.CALIBRATING
            
            # Verify logging occurred
            mock_logger.info.assert_called_with(
                "Manual calibration triggered from %s state", initial_state
            )

    def test_multiple_stability_periods_handled(self, stability_detector):
        """Test that multiple consecutive stability periods are handled correctly."""
        base_time = datetime.now()
        
        with freeze_time(base_time) as frozen_time:
            # First stability period: 35 minutes idle with stable temp
            stability_detector.update("idle", 22.0)
            frozen_time.tick(delta=timedelta(minutes=35))
            
            for i in range(7):
                frozen_time.tick(delta=timedelta(minutes=5))
                stability_detector.update("idle", 22.0 + 0.01 * i)  # Very stable
            
            # Should be stable
            assert stability_detector.is_stable_for_calibration() == True
            
            # Simulate AC turning on briefly (interrupting stability)
            stability_detector.update("cooling", 22.1)
            frozen_time.tick(delta=timedelta(minutes=5))
            
            # Should no longer be stable (idle timer reset)
            assert stability_detector.is_stable_for_calibration() == False
            
            # Return to idle and build up stability again
            stability_detector.update("idle", 22.1)
            frozen_time.tick(delta=timedelta(minutes=35))
            
            # Add more stable readings
            for i in range(7):
                frozen_time.tick(delta=timedelta(minutes=5))
                stability_detector.update("idle", 22.1 + 0.01 * i)
            
            # Should be stable again
            assert stability_detector.is_stable_for_calibration() == True

    def test_ac_state_changes_reset_idle_timer(self, stability_detector):
        """Test that AC state changes properly reset the idle timer."""
        base_time = datetime.now()
        
        with freeze_time(base_time) as frozen_time:
            # Start with idle state
            stability_detector.update("idle", 22.0)
            frozen_time.tick(delta=timedelta(minutes=25))  # 25 minutes idle
            
            # Add stable temperature readings
            stability_detector.update("idle", 22.0)
            stability_detector.update("idle", 22.01)
            
            # Not yet at 30 minute threshold
            assert stability_detector.is_stable_for_calibration() == False
            
            # AC starts cooling (resets idle timer)
            stability_detector.update("cooling", 22.1)
            frozen_time.tick(delta=timedelta(minutes=10))
            
            # Return to idle
            stability_detector.update("idle", 22.1)
            frozen_time.tick(delta=timedelta(minutes=25))  # Only 25 minutes since last idle start
            
            # Should not be stable yet (need 30 minutes from idle restart)
            assert stability_detector.is_stable_for_calibration() == False
            
            # Wait additional 10 minutes to reach 35 total idle time
            frozen_time.tick(delta=timedelta(minutes=10))
            stability_detector.update("idle", 22.1)
            
            # Now should be stable (35 minutes idle since last state change)
            assert stability_detector.is_stable_for_calibration() == True

    def test_force_calibration_blocked_during_probing(self, thermal_manager):
        """Test that manual calibration is properly blocked during PROBING state."""
        # Transition to PROBING state
        thermal_manager.transition_to(ThermalState.PROBING)
        assert thermal_manager.current_state == ThermalState.PROBING
        
        # Attempt to force calibration should be blocked
        with patch('custom_components.smart_climate.thermal_manager._LOGGER') as mock_logger:
            thermal_manager.force_calibration()
            
            # State should remain PROBING
            assert thermal_manager.current_state == ThermalState.PROBING
            
            # Warning should be logged
            mock_logger.warning.assert_called_with("Cannot force calibration during probing")

    def test_no_memory_leaks_or_performance_issues(self, stability_detector):
        """Test that long-term operation doesn't cause memory leaks or performance degradation."""
        base_time = datetime.now()
        
        with freeze_time(base_time) as frozen_time:
            # Simulate 24 hours of operation with temperature updates every 5 minutes
            updates_per_hour = 12  # Every 5 minutes
            total_hours = 24
            total_updates = updates_per_hour * total_hours
            
            for i in range(total_updates):
                # Vary AC state occasionally
                if i % 50 == 0:
                    ac_state = "cooling" if i % 100 == 0 else "idle"
                else:
                    ac_state = "idle"
                
                # Vary temperature slightly
                temp = 22.0 + (i % 10) * 0.01  # Small temperature variations
                
                stability_detector.update(ac_state, temp)
                frozen_time.tick(delta=timedelta(minutes=5))
            
            # Verify temperature history size is bounded (should not grow indefinitely)
            assert len(stability_detector._temperature_history) <= 20
            
            # Verify detector still functions correctly
            # Add stable conditions
            for j in range(10):
                stability_detector.update("idle", 22.0)
                frozen_time.tick(delta=timedelta(minutes=3))
            
            # Should still be able to detect stability
            drift = stability_detector.get_temperature_drift()
            assert drift >= 0  # Should calculate drift without errors
            
            # Verify no excessive memory usage (temperature history bounded)
            assert len(stability_detector._temperature_history) == 20  # At maxlen

    def test_integration_with_existing_thermal_states(self, thermal_manager):
        """Test that opportunistic calibration integrates properly with existing thermal states."""
        # Test transitions from each state
        test_states = [ThermalState.PRIMING, ThermalState.DRIFTING, ThermalState.CORRECTING, ThermalState.RECOVERY]
        
        for initial_state in test_states:
            thermal_manager.transition_to(initial_state)
            assert thermal_manager.current_state == initial_state
            
            # Force calibration from this state
            thermal_manager.force_calibration()
            
            if initial_state == ThermalState.PROBING:
                # Should be blocked
                assert thermal_manager.current_state == ThermalState.PROBING
            else:
                # Should transition to calibrating
                assert thermal_manager.current_state == ThermalState.CALIBRATING
                
            # Reset for next test
            thermal_manager.transition_to(ThermalState.PRIMING)

    def test_stability_detector_serialization(self, thermal_manager):
        """Test that StabilityDetector state is properly included in thermal manager serialization."""
        # Configure stability detector with some state
        thermal_manager.stability_detector.update("idle", 22.0)
        thermal_manager.stability_detector.update("idle", 22.1)
        
        # Serialize thermal manager
        serialized = thermal_manager.serialize()
        
        # Verify stability detector data is included
        assert "stability_detector" in serialized
        stability_data = serialized["stability_detector"]
        
        assert "idle_threshold_minutes" in stability_data
        assert "drift_threshold" in stability_data
        assert "last_ac_state" in stability_data
        assert "temperature_history_count" in stability_data
        
        # Verify values are reasonable
        assert stability_data["idle_threshold_minutes"] == 30  # Default from config
        assert stability_data["drift_threshold"] == 0.1  # Default from config
        assert stability_data["last_ac_state"] == "idle"
        assert stability_data["temperature_history_count"] == 2  # We added 2 readings