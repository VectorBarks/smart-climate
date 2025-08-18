"""Tests for probe scheduler status attributes in SmartClimateStatusSensor.

Tests the probe scheduler status integration in SmartClimateStatusSensor 
according to architecture Section 20.10 specifications.
"""

import pytest
from unittest.mock import Mock, MagicMock, PropertyMock
from datetime import datetime, timezone, timedelta
from homeassistant.core import HomeAssistant

from custom_components.smart_climate.thermal_models import ThermalState
from custom_components.smart_climate.thermal_sensor import SmartClimateStatusSensor
from custom_components.smart_climate.probe_scheduler import LearningProfile


@pytest.fixture
def mock_probe_scheduler():
    """Create a mock probe scheduler."""
    scheduler = Mock()
    # Mock status methods
    scheduler.should_probe_now.return_value = True
    scheduler._is_opportune_time.return_value = True
    scheduler._has_high_information_gain.return_value = True
    scheduler._is_quiet_hours.return_value = False
    scheduler._check_presence_entity.return_value = False
    scheduler._check_calendar_entity.return_value = False
    scheduler._check_manual_override.return_value = False
    scheduler._enforce_minimum_interval.return_value = True
    scheduler._check_maximum_interval_exceeded.return_value = False
    scheduler._get_bin_coverage.return_value = {"covered_bins": [0, 2, 3, 4], "total_bins": 6}
    scheduler._get_current_outdoor_temperature.return_value = 25.0
    scheduler._get_last_probe_time.return_value = datetime.now(timezone.utc) - timedelta(hours=18)
    scheduler._get_probe_history.return_value = [
        Mock(confidence=0.8, timestamp=datetime.now(timezone.utc) - timedelta(days=1)),
        Mock(confidence=0.9, timestamp=datetime.now(timezone.utc) - timedelta(days=3))
    ]
    scheduler._learning_profile = LearningProfile.BALANCED
    return scheduler


@pytest.fixture
def mock_thermal_manager_with_scheduler(mock_probe_scheduler):
    """Create a mock thermal manager with probe scheduler."""
    manager = Mock()
    manager.current_state = ThermalState.DRIFTING
    manager.get_operating_window.return_value = (22.5, 25.5)
    manager._setpoint = 24.0
    manager._model.tau_cooling = 90.0
    manager._model.tau_warming = 150.0
    manager._model.get_confidence.return_value = 0.65
    manager._model.get_probe_history.return_value = [
        Mock(confidence=0.8, timestamp=datetime.now(timezone.utc) - timedelta(days=1)),
        Mock(confidence=0.9, timestamp=datetime.now(timezone.utc) - timedelta(days=3))
    ]
    manager.probe_scheduler = mock_probe_scheduler
    return manager


@pytest.fixture
def mock_thermal_manager_no_scheduler():
    """Create a mock thermal manager without probe scheduler."""
    manager = Mock()
    manager.current_state = ThermalState.DRIFTING
    manager.get_operating_window.return_value = (22.5, 25.5)
    manager._setpoint = 24.0
    manager._model.tau_cooling = 90.0
    manager._model.tau_warming = 150.0
    manager._model.get_confidence.return_value = 0.65
    manager.probe_scheduler = None
    return manager


@pytest.fixture
def mock_offset_engine():
    """Create a mock offset engine."""
    engine = Mock()
    engine.is_learning_paused.return_value = False
    engine.get_effective_target.return_value = 24.0
    return engine


@pytest.fixture
def mock_cycle_monitor():
    """Create a mock cycle monitor."""
    monitor = Mock()
    monitor.get_average_cycle_duration.return_value = (480.0, 720.0)
    monitor.needs_adjustment.return_value = False
    return monitor


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    return Mock()


@pytest.fixture
def thermal_sensor_with_scheduler(mock_hass, mock_thermal_manager_with_scheduler, mock_offset_engine, mock_cycle_monitor):
    """Create a SmartClimateStatusSensor with probe scheduler for testing."""
    return SmartClimateStatusSensor(
        mock_hass, 
        mock_thermal_manager_with_scheduler, 
        mock_offset_engine, 
        mock_cycle_monitor
    )


@pytest.fixture
def thermal_sensor_no_scheduler(mock_hass, mock_thermal_manager_no_scheduler, mock_offset_engine, mock_cycle_monitor):
    """Create a SmartClimateStatusSensor without probe scheduler for testing."""
    return SmartClimateStatusSensor(
        mock_hass, 
        mock_thermal_manager_no_scheduler, 
        mock_offset_engine, 
        mock_cycle_monitor
    )


class TestProbeSchedulerStatusAttributes:
    """Test probe scheduler status attributes are added to extra_state_attributes."""
    
    def test_probe_scheduler_attributes_present(self, thermal_sensor_with_scheduler):
        """Test that probe scheduler attributes are included when scheduler available."""
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        
        # Verify probe scheduler attributes are present
        probe_scheduler_attrs = [
            "probe_scheduler_status",
            "next_probe_eligible", 
            "confidence_breakdown",
            "learning_progress",
            "probe_count",
            "last_probe_time",
            "temperature_bins_covered"
        ]
        
        for attr in probe_scheduler_attrs:
            assert attr in attrs, f"Missing probe scheduler attribute: {attr}"
    
    def test_probe_scheduler_attributes_graceful_when_none(self, thermal_sensor_no_scheduler):
        """Test graceful handling when probe scheduler is None."""
        attrs = thermal_sensor_no_scheduler.extra_state_attributes
        
        # Should still include probe scheduler attributes with appropriate defaults
        assert attrs["probe_scheduler_status"] == "Disabled"
        assert attrs["next_probe_eligible"] == "Unknown"
        assert attrs["confidence_breakdown"]["base_confidence"] == 0.65  # From thermal model
        assert attrs["confidence_breakdown"]["diversity_bonus"] == 0.0
        assert attrs["learning_progress"]["phase"] == "Unknown"
        assert attrs["probe_count"] == 0
        assert attrs["last_probe_time"] is None
        assert attrs["temperature_bins_covered"]["coverage_ratio"] == 0.0


class TestProbeSchedulerStatus:
    """Test probe_scheduler_status attribute generation."""
    
    def test_ready_status(self, thermal_sensor_with_scheduler, mock_probe_scheduler):
        """Test 'Ready' status when all conditions favorable."""
        # Setup conditions for ready state
        mock_probe_scheduler.should_probe_now.return_value = True
        mock_probe_scheduler._is_opportune_time.return_value = True
        mock_probe_scheduler._has_high_information_gain.return_value = True
        mock_probe_scheduler._is_quiet_hours.return_value = False
        mock_probe_scheduler._enforce_minimum_interval.return_value = True
        mock_probe_scheduler._check_maximum_interval_exceeded.return_value = False
        
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        assert attrs["probe_scheduler_status"] == "Ready"
    
    def test_blocked_quiet_hours_status(self, thermal_sensor_with_scheduler, mock_probe_scheduler):
        """Test 'Blocked - Quiet Hours' status during quiet hours."""
        mock_probe_scheduler.should_probe_now.return_value = False
        mock_probe_scheduler._is_quiet_hours.return_value = True
        
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        assert attrs["probe_scheduler_status"] == "Blocked - Quiet Hours"
    
    def test_blocked_user_present_status(self, thermal_sensor_with_scheduler, mock_probe_scheduler):
        """Test 'Blocked - User Present' status when presence detected."""
        mock_probe_scheduler.should_probe_now.return_value = False
        mock_probe_scheduler._is_quiet_hours.return_value = False
        mock_probe_scheduler._check_presence_entity.return_value = True
        
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        assert attrs["probe_scheduler_status"] == "Blocked - User Present"
    
    def test_blocked_low_information_gain_status(self, thermal_sensor_with_scheduler, mock_probe_scheduler):
        """Test 'Blocked - Low Information Gain' status for well-represented temperature."""
        mock_probe_scheduler.should_probe_now.return_value = False
        mock_probe_scheduler._is_opportune_time.return_value = True
        mock_probe_scheduler._has_high_information_gain.return_value = False
        
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        assert attrs["probe_scheduler_status"] == "Blocked - Low Information Gain"
    
    def test_blocked_min_interval_status(self, thermal_sensor_with_scheduler, mock_probe_scheduler):
        """Test 'Blocked - Min Interval' status when too soon since last probe."""
        mock_probe_scheduler.should_probe_now.return_value = False
        mock_probe_scheduler._enforce_minimum_interval.return_value = False
        
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        assert attrs["probe_scheduler_status"] == "Blocked - Min Interval"
    
    def test_forced_max_interval_status(self, thermal_sensor_with_scheduler, mock_probe_scheduler):
        """Test 'Forced - Max Interval' status when maximum interval exceeded."""
        mock_probe_scheduler.should_probe_now.return_value = True
        mock_probe_scheduler._check_maximum_interval_exceeded.return_value = True
        
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        assert attrs["probe_scheduler_status"] == "Forced - Max Interval"
    
    def test_disabled_status(self, thermal_sensor_no_scheduler):
        """Test 'Disabled' status when probe scheduler not configured."""
        attrs = thermal_sensor_no_scheduler.extra_state_attributes
        assert attrs["probe_scheduler_status"] == "Disabled"


class TestNextProbeEligible:
    """Test next_probe_eligible attribute calculation."""
    
    def test_now_when_currently_eligible(self, thermal_sensor_with_scheduler, mock_probe_scheduler):
        """Test 'Now' when currently eligible for probing."""
        mock_probe_scheduler.should_probe_now.return_value = True
        
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        assert attrs["next_probe_eligible"] == "Now"
    
    def test_timestamp_when_blocked_by_interval(self, thermal_sensor_with_scheduler, mock_probe_scheduler):
        """Test ISO timestamp when blocked by minimum interval."""
        mock_probe_scheduler.should_probe_now.return_value = False
        mock_probe_scheduler._enforce_minimum_interval.return_value = False
        last_probe_time = datetime.now(timezone.utc) - timedelta(hours=8)
        mock_probe_scheduler._get_last_probe_time.return_value = last_probe_time
        
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        # Should be 12 hours after last probe (minimum interval)
        expected_time = last_probe_time + timedelta(hours=12)
        assert attrs["next_probe_eligible"] == expected_time.isoformat()
    
    def test_timestamp_when_blocked_by_quiet_hours(self, thermal_sensor_with_scheduler, mock_probe_scheduler):
        """Test timestamp when blocked by quiet hours."""
        mock_probe_scheduler.should_probe_now.return_value = False
        mock_probe_scheduler._is_quiet_hours.return_value = True
        
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        # Should be next 7:00 AM
        next_eligible = datetime.fromisoformat(attrs["next_probe_eligible"])
        assert next_eligible.hour == 7
        assert next_eligible.minute == 0
        assert next_eligible > datetime.now(timezone.utc)
    
    def test_unknown_when_disabled(self, thermal_sensor_no_scheduler):
        """Test 'Unknown' when probe scheduler disabled."""
        attrs = thermal_sensor_no_scheduler.extra_state_attributes
        assert attrs["next_probe_eligible"] == "Unknown"


class TestConfidenceBreakdown:
    """Test confidence_breakdown attribute structure and calculation."""
    
    def test_confidence_breakdown_structure(self, thermal_sensor_with_scheduler):
        """Test confidence breakdown contains required keys."""
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        breakdown = attrs["confidence_breakdown"]
        
        required_keys = [
            "base_confidence", "diversity_bonus", "total_confidence", 
            "probe_count", "bins_covered", "total_bins"
        ]
        
        for key in required_keys:
            assert key in breakdown, f"Missing confidence breakdown key: {key}"
    
    def test_confidence_calculation_with_scheduler(self, thermal_sensor_with_scheduler, mock_probe_scheduler):
        """Test confidence calculation with probe scheduler data."""
        # Setup bin coverage and probe history
        mock_probe_scheduler._get_bin_coverage.return_value = {"covered_bins": [0, 2, 3, 4], "total_bins": 6}
        probe_history = [Mock() for _ in range(12)]  # 12 probes
        mock_probe_scheduler._get_probe_history.return_value = probe_history
        
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        breakdown = attrs["confidence_breakdown"]
        
        # Base confidence from probe count (log-based up to 0.8)
        assert breakdown["probe_count"] == 12
        assert 0.0 <= breakdown["base_confidence"] <= 0.8
        
        # Diversity bonus from bin coverage (4/6 = 0.67, up to 0.2 bonus)
        assert breakdown["bins_covered"] == 4
        assert breakdown["total_bins"] == 6
        expected_diversity = (4 / 6) * 0.2  # ~0.133
        assert abs(breakdown["diversity_bonus"] - expected_diversity) < 0.01
        
        # Total confidence is sum, clamped to 1.0
        expected_total = min(breakdown["base_confidence"] + breakdown["diversity_bonus"], 1.0)
        assert abs(breakdown["total_confidence"] - expected_total) < 0.01
    
    def test_confidence_calculation_without_scheduler(self, thermal_sensor_no_scheduler):
        """Test confidence calculation without probe scheduler."""
        attrs = thermal_sensor_no_scheduler.extra_state_attributes
        breakdown = attrs["confidence_breakdown"]
        
        # Should use thermal model confidence as base
        assert breakdown["base_confidence"] == 0.65  # From mock thermal model
        assert breakdown["diversity_bonus"] == 0.0  # No scheduler data
        assert breakdown["total_confidence"] == 0.65
        assert breakdown["probe_count"] == 0
        assert breakdown["bins_covered"] == 0


class TestLearningProgress:
    """Test learning_progress attribute structure and values."""
    
    def test_learning_progress_structure(self, thermal_sensor_with_scheduler):
        """Test learning progress contains required keys."""
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        progress = attrs["learning_progress"]
        
        required_keys = [
            "phase", "confidence_level", "estimated_completion", "learning_profile"
        ]
        
        for key in required_keys:
            assert key in progress, f"Missing learning progress key: {key}"
    
    def test_learning_phase_detection(self, thermal_sensor_with_scheduler, mock_probe_scheduler):
        """Test learning phase detection based on confidence and probe count."""
        # Test Initial phase (low confidence, few probes)
        mock_probe_scheduler._get_probe_history.return_value = [Mock(), Mock()]  # 2 probes
        thermal_sensor_with_scheduler._thermal_manager._model.get_confidence.return_value = 0.3
        
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        assert attrs["learning_progress"]["phase"] == "Initial"
        assert attrs["learning_progress"]["confidence_level"] == "Low"
        
        # Test Active Learning phase (medium confidence)
        mock_probe_scheduler._get_probe_history.return_value = [Mock() for _ in range(8)]  # 8 probes
        thermal_sensor_with_scheduler._thermal_manager._model.get_confidence.return_value = 0.6
        
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        assert attrs["learning_progress"]["phase"] == "Active Learning"
        assert attrs["learning_progress"]["confidence_level"] == "Medium"
        
        # Test Optimized phase (high confidence)
        mock_probe_scheduler._get_probe_history.return_value = [Mock() for _ in range(15)]  # 15 probes
        thermal_sensor_with_scheduler._thermal_manager._model.get_confidence.return_value = 0.85
        
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        assert attrs["learning_progress"]["phase"] == "Optimized"
        assert attrs["learning_progress"]["confidence_level"] == "High"
    
    def test_estimated_completion_calculation(self, thermal_sensor_with_scheduler, mock_probe_scheduler):
        """Test estimated completion time calculation."""
        # Setup current state - medium confidence, some probes
        probe_history = [Mock() for _ in range(8)]
        mock_probe_scheduler._get_probe_history.return_value = probe_history
        thermal_sensor_with_scheduler._thermal_manager._model.get_confidence.return_value = 0.6
        
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        progress = attrs["learning_progress"]
        
        # Should provide reasonable completion estimate
        completion = progress["estimated_completion"]
        assert completion in ["1 week", "2 weeks", "3 weeks", "4 weeks", "1-2 months"]
    
    def test_learning_profile_display(self, thermal_sensor_with_scheduler, mock_probe_scheduler):
        """Test learning profile display in progress."""
        mock_probe_scheduler._learning_profile = LearningProfile.COMFORT
        
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        assert attrs["learning_progress"]["learning_profile"] == "comfort"


class TestProbeCountAndTime:
    """Test probe_count and last_probe_time attributes."""
    
    def test_probe_count_with_scheduler(self, thermal_sensor_with_scheduler, mock_probe_scheduler):
        """Test probe count from scheduler history."""
        probe_history = [Mock() for _ in range(15)]
        mock_probe_scheduler._get_probe_history.return_value = probe_history
        
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        assert attrs["probe_count"] == 15
    
    def test_probe_count_without_scheduler(self, thermal_sensor_no_scheduler):
        """Test probe count defaults to 0 without scheduler."""
        attrs = thermal_sensor_no_scheduler.extra_state_attributes
        assert attrs["probe_count"] == 0
    
    def test_last_probe_time_with_scheduler(self, thermal_sensor_with_scheduler, mock_probe_scheduler):
        """Test last probe time from scheduler."""
        last_time = datetime.now(timezone.utc) - timedelta(hours=6)
        mock_probe_scheduler._get_last_probe_time.return_value = last_time
        
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        assert attrs["last_probe_time"] == last_time.isoformat()
    
    def test_last_probe_time_without_scheduler(self, thermal_sensor_no_scheduler):
        """Test last probe time is None without scheduler."""
        attrs = thermal_sensor_no_scheduler.extra_state_attributes
        assert attrs["last_probe_time"] is None


class TestTemperatureBinsCovered:
    """Test temperature_bins_covered attribute structure and calculation."""
    
    def test_temperature_bins_structure(self, thermal_sensor_with_scheduler):
        """Test temperature bins covered contains required keys."""
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        bins_covered = attrs["temperature_bins_covered"]
        
        required_keys = [
            "covered_bins", "total_bins", "coverage_ratio", "missing_ranges"
        ]
        
        for key in required_keys:
            assert key in bins_covered, f"Missing temperature bins key: {key}"
    
    def test_bin_coverage_calculation(self, thermal_sensor_with_scheduler, mock_probe_scheduler):
        """Test bin coverage calculation and ratio."""
        # Setup bin coverage data
        coverage_data = {
            "covered_bins": [0, 2, 3, 4], 
            "total_bins": 6,
            "missing_bins": [1, 5],
            "bin_ranges": {
                0: "<-10°C", 1: "-10-0°C", 2: "0-10°C", 
                3: "10-20°C", 4: "20-30°C", 5: ">30°C"
            }
        }
        mock_probe_scheduler._get_bin_coverage.return_value = coverage_data
        
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        bins_covered = attrs["temperature_bins_covered"]
        
        assert bins_covered["covered_bins"] == [0, 2, 3, 4]
        assert bins_covered["total_bins"] == 6
        assert abs(bins_covered["coverage_ratio"] - (4/6)) < 0.01  # 0.67
        assert "-10-0°C" in bins_covered["missing_ranges"]
        assert ">30°C" in bins_covered["missing_ranges"]
    
    def test_bin_coverage_without_scheduler(self, thermal_sensor_no_scheduler):
        """Test bin coverage defaults without scheduler."""
        attrs = thermal_sensor_no_scheduler.extra_state_attributes
        bins_covered = attrs["temperature_bins_covered"]
        
        assert bins_covered["covered_bins"] == []
        assert bins_covered["total_bins"] == 6  # Default bins
        assert bins_covered["coverage_ratio"] == 0.0
        assert len(bins_covered["missing_ranges"]) == 6  # All ranges missing


class TestStatusUpdatesOnSchedulerStateChanges:
    """Test status updates when probe scheduler state changes."""
    
    def test_status_changes_with_scheduler_conditions(self, thermal_sensor_with_scheduler, mock_probe_scheduler):
        """Test status updates when scheduler conditions change."""
        # Initial state - ready to probe
        mock_probe_scheduler.should_probe_now.return_value = True
        initial_attrs = thermal_sensor_with_scheduler.extra_state_attributes
        assert initial_attrs["probe_scheduler_status"] == "Ready"
        
        # Change to quiet hours
        mock_probe_scheduler.should_probe_now.return_value = False
        mock_probe_scheduler._is_quiet_hours.return_value = True
        new_attrs = thermal_sensor_with_scheduler.extra_state_attributes
        assert new_attrs["probe_scheduler_status"] == "Blocked - Quiet Hours"
        
        # Verify next eligible time updates accordingly
        assert initial_attrs["next_probe_eligible"] == "Now"
        assert new_attrs["next_probe_eligible"] != "Now"
    
    def test_confidence_updates_with_new_probes(self, thermal_sensor_with_scheduler, mock_probe_scheduler):
        """Test confidence breakdown updates when new probes added."""
        # Initial state with few probes
        mock_probe_scheduler._get_probe_history.return_value = [Mock() for _ in range(5)]
        initial_attrs = thermal_sensor_with_scheduler.extra_state_attributes
        initial_count = initial_attrs["confidence_breakdown"]["probe_count"]
        
        # Add more probes
        mock_probe_scheduler._get_probe_history.return_value = [Mock() for _ in range(12)]
        new_attrs = thermal_sensor_with_scheduler.extra_state_attributes
        new_count = new_attrs["confidence_breakdown"]["probe_count"]
        
        assert new_count > initial_count
        # Base confidence should increase with more probes
        assert new_attrs["confidence_breakdown"]["base_confidence"] >= initial_attrs["confidence_breakdown"]["base_confidence"]


class TestErrorHandlingProbeScheduler:
    """Test error handling for probe scheduler integration."""
    
    def test_scheduler_method_errors_handled(self, thermal_sensor_with_scheduler, mock_probe_scheduler):
        """Test graceful handling when scheduler methods raise exceptions."""
        # Setup scheduler method to raise exception
        mock_probe_scheduler.should_probe_now.side_effect = Exception("Sensor error")
        
        # Should not raise exception, should provide fallback values
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        
        assert "probe_scheduler_status" in attrs
        assert attrs["probe_scheduler_status"] != "Ready"  # Should detect error
    
    def test_missing_scheduler_attributes_handled(self, thermal_sensor_with_scheduler):
        """Test handling when scheduler is missing expected attributes."""
        # Remove some scheduler attributes
        delattr(thermal_sensor_with_scheduler._thermal_manager.probe_scheduler, '_learning_profile')
        
        # Should not raise exception
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        
        assert attrs is not None
        assert "learning_progress" in attrs
    
    def test_none_values_from_scheduler_handled(self, thermal_sensor_with_scheduler, mock_probe_scheduler):
        """Test handling of None values returned from scheduler methods."""
        mock_probe_scheduler._get_last_probe_time.return_value = None
        mock_probe_scheduler._get_current_outdoor_temperature.return_value = None
        
        # Should not raise exception
        attrs = thermal_sensor_with_scheduler.extra_state_attributes
        
        assert attrs["last_probe_time"] is None
        assert "probe_scheduler_status" in attrs