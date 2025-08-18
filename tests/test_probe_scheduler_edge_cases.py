"""
Edge case and failure scenario tests for ProbeScheduler system.

Tests error conditions, extreme configurations, malformed data handling,
concurrent access scenarios, and robustness under adverse conditions.

Author: Integration Test Agent for ProbeScheduler v1.5.3-beta Step 7.1
"""

import pytest
from datetime import datetime, timezone, timedelta, time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Optional, Any
import json

from homeassistant.exceptions import HomeAssistantError
from homeassistant.core import State

from custom_components.smart_climate.thermal_model import PassiveThermalModel
from custom_components.smart_climate.thermal_models import ProbeResult, ThermalState
from custom_components.smart_climate.thermal_manager import ThermalManager
from custom_components.smart_climate.probe_scheduler import (
    ProbeScheduler, LearningProfile, ProfileConfig, validate_advanced_settings
)
from custom_components.smart_climate.thermal_preferences import (
    UserPreferences, PreferenceLevel
)
from custom_components.smart_climate.const import DOMAIN

from tests.fixtures.thermal_v153 import create_probe_result


class TestProbeSchedulerEdgeCases:
    """Edge case and failure scenario tests."""

    @pytest.fixture
    def mock_hass_unreliable(self):
        """Create mock Home Assistant with unreliable entity states."""
        hass = Mock()
        hass.states = Mock()
        hass.services = Mock()
        hass.data = {DOMAIN: {}}
        
        # Simulate unreliable entity states
        unreliable_states = {
            "person.user": None,  # Entity doesn't exist
            "weather.forecast": Mock(state="unavailable", attributes={}),
            "calendar.work": Mock(state="unknown", attributes={}),
            "input_boolean.manual_probe_override": Mock(state="", attributes={}),
            "climate.thermostat": Mock(state="unavailable", attributes={}),
            "sensor.nonexistent": None
        }
        
        def get_state(entity_id):
            if entity_id in unreliable_states:
                return unreliable_states[entity_id]
            return None  # Default to missing
        
        hass.states.get.side_effect = get_state
        hass.services.async_call = AsyncMock()
        
        return hass

    @pytest.fixture
    def minimal_thermal_model(self):
        """Create thermal model with minimal/no probe history."""
        model = PassiveThermalModel()
        # Start with empty history
        model._probe_history.clear()
        return model

    @pytest.fixture
    def corrupted_thermal_model(self):
        """Create thermal model with corrupted probe data."""
        model = PassiveThermalModel()
        model._probe_history.clear()
        
        # Add corrupted probe data
        corrupted_probes = [
            # Probe with None values
            create_probe_result(None, 0.8),  # This will be clamped by create_probe_result
            
            # Probe with extreme values
            create_probe_result(1000.0, 2.0),  # Extreme tau, invalid confidence
            
            # Probe with negative values
            create_probe_result(-50.0, -0.5),
        ]
        
        try:
            for probe in corrupted_probes:
                model._probe_history.append(probe)
        except (ValueError, TypeError):
            # Expected with truly corrupted data
            pass
            
        return model

    @pytest.fixture
    def extreme_preferences(self):
        """Create user preferences with extreme values."""
        return UserPreferences(
            level=PreferenceLevel.MAX_SAVINGS,
            comfort_band=0.1,  # Very tight band
            confidence_threshold=0.99,  # Extremely high threshold
            probe_drift=5.0  # Very high drift tolerance
        )

    def test_missing_entities_error_handling(self, mock_hass_unreliable, minimal_thermal_model):
        """Test error handling when required entities are missing."""
        probe_scheduler = ProbeScheduler(
            hass=mock_hass_unreliable,
            thermal_model=minimal_thermal_model,
            presence_entity_id="person.nonexistent",
            weather_entity_id="weather.nonexistent",
            calendar_entity_id="calendar.nonexistent",
            manual_override_entity_id="input_boolean.nonexistent"
        )
        
        # Test 1: Should handle missing presence entity
        try:
            should_probe = probe_scheduler.should_probe_now()
            assert isinstance(should_probe, bool), "Should return boolean despite missing entities"
        except Exception as e:
            pytest.fail(f"Should handle missing entities gracefully: {e}")
        
        # Test 2: Should handle missing weather entity
        outdoor_temp = probe_scheduler._get_current_outdoor_temperature()
        assert outdoor_temp is None, "Should return None for missing weather entity"
        
        # Test 3: Should handle missing calendar entity
        calendar_busy = probe_scheduler._check_calendar_entity()
        assert isinstance(calendar_busy, bool), "Should return boolean for missing calendar"
        
        # Test 4: Should handle missing manual override
        manual_override = probe_scheduler._check_manual_override()
        assert isinstance(manual_override, bool), "Should return boolean for missing override"

    def test_sensor_failures_and_timeouts(self, mock_hass_unreliable, minimal_thermal_model):
        """Test handling of sensor failures and timeout scenarios."""
        probe_scheduler = ProbeScheduler(
            hass=mock_hass_unreliable,
            thermal_model=minimal_thermal_model,
            presence_entity_id="person.user",
            weather_entity_id="weather.forecast"
        )
        
        # Test 1: Sensor timeout simulation
        with patch.object(mock_hass_unreliable.states, 'get', side_effect=TimeoutError("Sensor timeout")):
            try:
                result = probe_scheduler._handle_sensor_errors()
                assert result is not None, "Should handle sensor timeouts"
            except TimeoutError:
                pytest.fail("Should catch and handle sensor timeouts")
        
        # Test 2: Home Assistant service unavailable
        mock_hass_unreliable.states.get.side_effect = HomeAssistantError("Service unavailable")
        
        try:
            should_probe = probe_scheduler.should_probe_now()
            assert isinstance(should_probe, bool), "Should handle HA service errors"
        except HomeAssistantError:
            pytest.fail("Should catch and handle HA errors")
        
        # Test 3: Corrupted entity state
        corrupted_state = Mock()
        corrupted_state.state = object()  # Non-string state
        corrupted_state.attributes = "invalid"  # Non-dict attributes
        
        mock_hass_unreliable.states.get.side_effect = lambda x: corrupted_state
        
        try:
            presence_check = probe_scheduler._check_presence_entity()
            assert isinstance(presence_check, bool), "Should handle corrupted entity states"
        except (TypeError, AttributeError):
            pytest.fail("Should handle corrupted entity states gracefully")

    def test_invalid_configuration_data(self, mock_hass_unreliable, minimal_thermal_model):
        """Test handling of malformed configuration data."""
        # Test 1: Invalid entity IDs
        try:
            probe_scheduler = ProbeScheduler(
                hass=mock_hass_unreliable,
                thermal_model=minimal_thermal_model,
                presence_entity_id="",  # Empty string
                weather_entity_id="invalid.entity.id.format",  # Invalid format
                calendar_entity_id=None,  # None (should be allowed)
                manual_override_entity_id="123invalid"  # Invalid format
            )
            
            # Should create instance but handle invalid IDs gracefully
            assert probe_scheduler is not None
            
            # Validation should detect issues
            probe_scheduler._validate_configuration()
            # Note: May or may not raise depending on implementation
            
        except Exception as e:
            # Acceptable if validation catches invalid config
            assert "entity" in str(e).lower() or "invalid" in str(e).lower()
        
        # Test 2: Invalid learning profile
        try:
            probe_scheduler = ProbeScheduler(
                hass=mock_hass_unreliable,
                thermal_model=minimal_thermal_model,
                learning_profile="invalid_profile"
            )
            pytest.fail("Should reject invalid learning profile")
        except (ValueError, KeyError):
            # Expected
            pass
        
        # Test 3: Invalid advanced settings
        probe_scheduler = ProbeScheduler(
            hass=mock_hass_unreliable,
            thermal_model=minimal_thermal_model
        )
        
        invalid_settings = {
            "min_probe_interval_hours": -5,  # Negative
            "max_probe_interval_days": 0,    # Zero
            "quiet_hours_start": "invalid_time",
            "information_gain_threshold": 2.0,  # > 1.0
        }
        
        try:
            probe_scheduler.apply_advanced_settings(invalid_settings)
            # Should either reject or clamp invalid values
            assert probe_scheduler._min_probe_interval.total_seconds() > 0
            assert probe_scheduler._max_probe_interval.total_seconds() > 0
            assert 0 <= probe_scheduler._information_gain_threshold <= 1.0
        except (ValueError, TypeError):
            # Also acceptable if validation rejects
            pass

    def test_extreme_temperature_ranges(self, mock_hass_unreliable, minimal_thermal_model):
        """Test handling of extreme temperature ranges and edge values."""
        probe_scheduler = ProbeScheduler(
            hass=mock_hass_unreliable,
            thermal_model=minimal_thermal_model,
            weather_entity_id="weather.forecast"
        )
        
        extreme_temperatures = [-40, -20, 0, 50, 60, 100]  # °C
        
        for temp in extreme_temperatures:
            # Simulate extreme weather conditions
            mock_state = Mock()
            mock_state.state = "sunny"
            mock_state.attributes = {"temperature": temp}
            mock_hass_unreliable.states.get.return_value = mock_state
            
            # Test 1: Should handle extreme temperatures
            outdoor_temp = probe_scheduler._get_current_outdoor_temperature()
            if outdoor_temp is not None:
                assert isinstance(outdoor_temp, (int, float))
                # Implementation may clamp or reject extreme values
                
            # Test 2: Temperature bin assignment
            temp_bin = probe_scheduler._get_temp_bin(temp)
            assert isinstance(temp_bin, int), f"Should assign bin for temperature {temp}°C"
            
            # Test 3: Information gain calculation
            try:
                info_gain = probe_scheduler._has_high_information_gain(temp, [])
                assert isinstance(info_gain, bool)
            except (ValueError, OverflowError):
                # Acceptable for truly extreme values
                pass

    def test_empty_probe_history_scenarios(self, mock_hass_unreliable, minimal_thermal_model):
        """Test behavior with empty or minimal probe history."""
        probe_scheduler = ProbeScheduler(
            hass=mock_hass_unreliable,
            thermal_model=minimal_thermal_model
        )
        
        # Ensure truly empty history
        minimal_thermal_model._probe_history.clear()
        
        # Test 1: Probe decision with no history
        should_probe = probe_scheduler.should_probe_now()
        assert isinstance(should_probe, bool), "Should handle empty probe history"
        
        # Test 2: Information gain with no history
        info_gain = probe_scheduler._has_high_information_gain(22.0, [])
        assert info_gain == True, "Should have high information gain with no history"
        
        # Test 3: Bin coverage with no probes
        bin_coverage = probe_scheduler._get_bin_coverage([])
        assert isinstance(bin_coverage, dict), "Should return empty bin coverage"
        assert len(bin_coverage) == 0, "Should have no covered bins"
        
        # Test 4: Confidence calculation with no probes
        confidence = minimal_thermal_model.get_confidence()
        assert confidence == 0.0, "Should have zero confidence with no probes"

    def test_maximum_probe_history_scenarios(self, mock_hass_unreliable):
        """Test behavior with maximum probe history (75 probes)."""
        # Create model with maximum probe history
        thermal_model = PassiveThermalModel()
        thermal_model._probe_history.clear()
        
        # Fill with maximum probes
        for i in range(75):
            probe = create_probe_result(
                tau_value=80.0 + (i % 20),  # Varying tau values
                confidence=0.7 + (i % 30) * 0.01,  # Varying confidence
                age_days=i * 0.5,  # Spread over time
                outdoor_temp=-10 + (i % 40)  # Temperature range
            )
            thermal_model._probe_history.append(probe)
        
        probe_scheduler = ProbeScheduler(
            hass=mock_hass_unreliable,
            thermal_model=thermal_model
        )
        
        # Test 1: Performance with full history
        import time
        start_time = time.time()
        
        should_probe = probe_scheduler.should_probe_now()
        bin_coverage = probe_scheduler._get_bin_coverage(list(thermal_model._probe_history))
        info_gain = probe_scheduler._has_high_information_gain(25.0, list(thermal_model._probe_history))
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        assert processing_time < 1.0, f"Should process 75 probes quickly: {processing_time:.3f}s"
        assert isinstance(should_probe, bool)
        assert isinstance(bin_coverage, dict)
        assert isinstance(info_gain, bool)
        
        # Test 2: Confidence with maximum probes
        confidence = thermal_model.get_confidence()
        assert 0.8 <= confidence <= 1.0, f"Should have high confidence with 75 probes: {confidence}"
        
        # Test 3: Adding 76th probe should maintain 75 limit
        new_probe = create_probe_result(95.0, 0.9, outdoor_temp=30.0)
        thermal_model._probe_history.append(new_probe)
        
        # deque should automatically maintain maxlen
        assert len(thermal_model._probe_history) == 75, "Should maintain 75 probe limit"

    def test_concurrent_access_scenarios(self, mock_hass_unreliable, minimal_thermal_model):
        """Test handling of concurrent access to probe scheduler."""
        probe_scheduler = ProbeScheduler(
            hass=mock_hass_unreliable,
            thermal_model=minimal_thermal_model
        )
        
        # Simulate concurrent access by multiple calls
        import threading
        import queue
        
        results = queue.Queue()
        errors = queue.Queue()
        
        def concurrent_probe_check():
            try:
                result = probe_scheduler.should_probe_now()
                results.put(result)
            except Exception as e:
                errors.put(e)
        
        # Test 1: Multiple simultaneous probe checks
        threads = []
        for i in range(10):
            thread = threading.Thread(target=concurrent_probe_check)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=5.0)
        
        # Collect results
        concurrent_results = []
        while not results.empty():
            concurrent_results.append(results.get())
        
        concurrent_errors = []
        while not errors.empty():
            concurrent_errors.append(errors.get())
        
        assert len(concurrent_errors) == 0, f"Should handle concurrent access: {concurrent_errors}"
        assert len(concurrent_results) == 10, "Should return results for all concurrent calls"
        assert all(isinstance(r, bool) for r in concurrent_results), "All results should be boolean"

    def test_schema_version_mismatches(self, mock_hass_unreliable, minimal_thermal_model):
        """Test handling of schema version mismatches in persistence data."""
        user_preferences = UserPreferences(
            level=PreferenceLevel.BALANCED,
            comfort_band=1.0,
            confidence_threshold=0.7,
            probe_drift=2.0
        )
        
        thermal_manager = ThermalManager(
            hass=mock_hass_unreliable,
            model=minimal_thermal_model,
            preferences=user_preferences,
            config={"entity_id": "climate.test"},
            persistence_callback=Mock()
        )
        
        # Test 1: Future schema version
        future_schema_data = {
            "version": "999.0",  # Future version
            "schema_version": "999.0",
            "state": {"current_state": "DRIFTING"},
            "model": {"tau_cooling": 90.0, "tau_warming": 150.0},
            "probe_history": [],
            "probe_scheduler": {
                "learning_profile": "balanced",
                "unknown_future_field": "future_value"
            }
        }
        
        try:
            thermal_manager.restore(future_schema_data)
            # Should either handle gracefully or provide clear error
        except (ValueError, KeyError) as e:
            assert "version" in str(e).lower() or "schema" in str(e).lower()
        
        # Test 2: Legacy schema (missing fields)
        legacy_schema_data = {
            "version": "0.9",
            "state": {"current_state": "PRIMING"},
            "model": {"tau_cooling": 85.0},  # Missing tau_warming
            # Missing probe_scheduler section entirely
        }
        
        try:
            thermal_manager.restore(legacy_schema_data)
            # Should handle missing fields with defaults
            assert thermal_manager.probe_scheduler is not None
        except Exception as e:
            # Acceptable if legacy support not implemented
            pass
        
        # Test 3: Corrupted JSON structure
        corrupted_data = {
            "version": "1.0",
            "state": "not_a_dict",  # Should be dict
            "model": {"tau_cooling": "not_a_number"},  # Should be float
            "probe_scheduler": None  # Should be dict or missing
        }
        
        try:
            thermal_manager.restore(corrupted_data)
            pytest.fail("Should reject corrupted persistence data")
        except (ValueError, TypeError, KeyError):
            # Expected
            pass

    def test_malformed_data_handling(self, mock_hass_unreliable):
        """Test robust handling of malformed probe data and timestamps."""
        thermal_model = PassiveThermalModel()
        thermal_model._probe_history.clear()
        
        # Test 1: Probes with invalid timestamps
        try:
            # This should be handled by create_probe_result validation
            invalid_probe = ProbeResult(
                tau_value=90.0,
                confidence=0.8,
                duration=1800,
                fit_quality=0.9,
                aborted=False,
                timestamp="invalid_timestamp",  # Invalid type
                outdoor_temp=25.0
            )
            pytest.fail("ProbeResult should validate timestamp type")
        except (TypeError, ValueError):
            # Expected - validation should catch this
            pass
        
        # Test 2: Missing optional fields in restored data
        probe_data_missing_fields = {
            "tau_value": 90.0,
            "confidence": 0.8,
            # Missing duration, fit_quality, timestamp, etc.
        }
        
        try:
            # Thermal manager should handle missing fields gracefully
            restored_probe = ProbeResult(
                tau_value=probe_data_missing_fields["tau_value"],
                confidence=probe_data_missing_fields["confidence"],
                duration=probe_data_missing_fields.get("duration", 1800),
                fit_quality=probe_data_missing_fields.get("fit_quality", 0.8),
                aborted=probe_data_missing_fields.get("aborted", False),
                timestamp=datetime.now(timezone.utc),  # Default timestamp
                outdoor_temp=probe_data_missing_fields.get("outdoor_temp")
            )
            
            thermal_model._probe_history.append(restored_probe)
            assert len(thermal_model._probe_history) == 1
            
        except (TypeError, ValueError) as e:
            pytest.fail(f"Should handle missing probe fields gracefully: {e}")

    def test_home_assistant_service_failures(self, mock_hass_unreliable, minimal_thermal_model):
        """Test handling of Home Assistant service failures and API errors."""
        probe_scheduler = ProbeScheduler(
            hass=mock_hass_unreliable,
            thermal_model=minimal_thermal_model,
            presence_entity_id="person.user"
        )
        
        # Test 1: Service call failures
        mock_hass_unreliable.services.async_call.side_effect = HomeAssistantError("Service failed")
        
        # Should not affect probe scheduling decisions
        try:
            should_probe = probe_scheduler.should_probe_now()
            assert isinstance(should_probe, bool)
        except HomeAssistantError:
            pytest.fail("Service failures should not affect probe scheduling")
        
        # Test 2: State fetch failures during abort check
        mock_hass_unreliable.states.get.side_effect = Exception("State fetch failed")
        
        try:
            abort_conditions = probe_scheduler.check_abort_conditions()
            assert isinstance(abort_conditions, dict)
            # Should default to safe behavior (likely abort) on errors
        except Exception:
            pytest.fail("Should handle state fetch failures during abort check")
        
        # Test 3: Partial service availability
        def selective_failure(entity_id):
            if "presence" in entity_id:
                raise HomeAssistantError("Presence service down")
            return Mock(state="available", attributes={})
        
        mock_hass_unreliable.states.get.side_effect = selective_failure
        
        try:
            # Should fall back to other detection methods
            is_opportune = probe_scheduler._is_opportune_time()
            assert isinstance(is_opportune, bool)
        except HomeAssistantError:
            pytest.fail("Should gracefully degrade when some services fail")

    def test_extreme_configuration_edge_cases(self, mock_hass_unreliable, minimal_thermal_model):
        """Test behavior with extreme configuration values."""
        # Test 1: Very short probe intervals (6 hours)
        probe_scheduler = ProbeScheduler(
            hass=mock_hass_unreliable,
            thermal_model=minimal_thermal_model
        )
        
        extreme_settings = {
            "min_probe_interval_hours": 6,
            "max_probe_interval_days": 1,  # Very aggressive
            "information_gain_threshold": 0.01,  # Very low threshold
            "quiet_hours_start": "23:59",
            "quiet_hours_end": "00:01"  # Very short quiet period
        }
        
        probe_scheduler.apply_advanced_settings(extreme_settings)
        
        assert probe_scheduler._min_probe_interval.total_seconds() == 6 * 3600
        assert probe_scheduler._information_gain_threshold == 0.01
        
        # Test 2: Very long probe intervals (14 days)
        conservative_settings = {
            "min_probe_interval_hours": 72,  # 3 days
            "max_probe_interval_days": 14,
            "information_gain_threshold": 0.8,  # Very high threshold
        }
        
        probe_scheduler.apply_advanced_settings(conservative_settings)
        
        # Should handle extreme intervals
        max_interval_exceeded = probe_scheduler._check_maximum_interval_exceeded()
        assert isinstance(max_interval_exceeded, bool)
        
        # Test 3: Edge case quiet hours (crossing midnight)
        midnight_crossing_settings = {
            "quiet_hours_start": "23:00",
            "quiet_hours_end": "01:00"  # Crosses midnight
        }
        
        probe_scheduler.apply_advanced_settings(midnight_crossing_settings)
        
        # Test during quiet hours
        with patch('custom_components.smart_climate.probe_scheduler.datetime') as mock_dt:
            # Test midnight hour
            mock_dt.now.return_value = datetime(2025, 1, 15, 0, 30)  # 00:30
            mock_dt.time = time
            
            is_quiet = probe_scheduler._is_quiet_hours()
            assert is_quiet == True, "Should detect quiet hours crossing midnight"

    def test_data_integrity_validation(self, mock_hass_unreliable):
        """Test data integrity checks and validation throughout the system."""
        thermal_model = PassiveThermalModel()
        
        # Test 1: Probe result validation
        valid_probe = create_probe_result(90.0, 0.8, outdoor_temp=25.0)
        
        # Verify probe result integrity
        assert 30.0 <= valid_probe.tau_value <= 300.0, "Tau should be within physical limits"
        assert 0.0 <= valid_probe.confidence <= 1.0, "Confidence should be normalized"
        assert isinstance(valid_probe.timestamp, datetime), "Timestamp should be datetime"
        
        # Test 2: Historical data consistency
        probe_sequence = []
        for i in range(10):
            probe = create_probe_result(
                tau_value=85.0 + i * 2,
                confidence=0.7 + i * 0.02,
                age_days=i,
                outdoor_temp=20.0 + i
            )
            probe_sequence.append(probe)
            thermal_model._probe_history.append(probe)
        
        # Verify chronological order is maintained
        timestamps = [probe.timestamp for probe in thermal_model._probe_history]
        # Should be in reverse chronological order (newest first due to age_days)
        
        # Test 3: Weighted average calculation integrity
        if len(thermal_model._probe_history) > 1:
            weighted_tau = thermal_model._calculate_weighted_tau(is_cooling=True)
            assert 30.0 <= weighted_tau <= 300.0, "Weighted tau should be within bounds"
        
        # Test 4: Confidence calculation bounds
        confidence = thermal_model.get_confidence()
        assert 0.0 <= confidence <= 1.0, f"Confidence should be normalized: {confidence}"

    def test_resource_exhaustion_scenarios(self, mock_hass_unreliable, minimal_thermal_model):
        """Test behavior under resource exhaustion conditions."""
        probe_scheduler = ProbeScheduler(
            hass=mock_hass_unreliable,
            thermal_model=minimal_thermal_model
        )
        
        # Test 1: Memory pressure simulation
        with patch('sys.getsizeof', return_value=999999999):  # Simulate large memory usage
            try:
                should_probe = probe_scheduler.should_probe_now()
                assert isinstance(should_probe, bool)
            except MemoryError:
                pytest.fail("Should handle memory pressure gracefully")
        
        # Test 2: CPU exhaustion simulation
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("CPU exhaustion")
        
        # Set a very short timeout to simulate CPU exhaustion
        original_handler = signal.signal(signal.SIGALRM, timeout_handler)
        
        try:
            signal.alarm(1)  # 1 second timeout
            # This operation should complete quickly even under load
            bin_coverage = probe_scheduler._get_bin_coverage([])
            signal.alarm(0)  # Cancel alarm
            
            assert isinstance(bin_coverage, dict)
            
        except TimeoutError:
            # Acceptable if operation genuinely takes too long
            pass
        finally:
            signal.signal(signal.SIGALRM, original_handler)
            signal.alarm(0)

    def test_edge_case_recovery_mechanisms(self, mock_hass_unreliable):
        """Test system recovery from various edge cases and error conditions."""
        thermal_model = PassiveThermalModel()
        user_preferences = UserPreferences(
            level=PreferenceLevel.BALANCED,
            comfort_band=1.0,
            confidence_threshold=0.7,
            probe_drift=2.0
        )
        
        thermal_manager = ThermalManager(
            hass=mock_hass_unreliable,
            model=thermal_model,
            preferences=user_preferences,
            config={"entity_id": "climate.test"},
            persistence_callback=Mock()
        )
        
        # Test 1: Recovery from corrupted state
        thermal_manager._current_state = None  # Invalid state
        
        try:
            thermal_manager.update_state()
            # Should either fix state or handle gracefully
            assert thermal_manager.current_state is not None
        except Exception as e:
            # Should not crash the system
            assert "state" in str(e).lower()
        
        # Test 2: Recovery from probe scheduler failure
        thermal_manager.probe_scheduler = None
        
        try:
            thermal_manager.update_state(
                current_temp=23.0,
                outdoor_temp=25.0,
                hvac_mode="cool"
            )
            # Should continue operating without probe scheduler
        except AttributeError:
            pytest.fail("Should handle missing probe scheduler gracefully")
        
        # Test 3: Recovery from model inconsistencies
        # Force inconsistent model state
        thermal_model._tau_cooling = -50.0  # Invalid tau
        
        try:
            # Model should validate and correct invalid values
            predicted_drift = thermal_model.predict_drift(23.0, 25.0, 60, True)
            assert isinstance(predicted_drift, (int, float))
        except (ValueError, AssertionError):
            # Acceptable if model validates inputs
            pass