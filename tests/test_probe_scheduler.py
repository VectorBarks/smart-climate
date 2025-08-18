# ABOUTME: Tests ProbeScheduler class initialization and configuration constants

import pytest
from unittest.mock import Mock, patch
from datetime import time, timedelta
from typing import Optional

from homeassistant.core import HomeAssistant
from custom_components.smart_climate.probe_scheduler import (
    ProbeScheduler,
    LearningProfile,
    ProfileConfig,
    MIN_PROBE_INTERVAL,
    MAX_PROBE_INTERVAL,
    QUIET_HOURS_START,
    QUIET_HOURS_END,
    OUTDOOR_TEMP_BINS
)
from custom_components.smart_climate.thermal_model import PassiveThermalModel


class TestProbeScheduler:
    """Test ProbeScheduler initialization and configuration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.hass = Mock()
        self.thermal_model = Mock()
        self.presence_entity_id = "binary_sensor.presence"
        self.weather_entity_id = "weather.test"
        
    def test_init_with_all_parameters(self):
        """Test initialization with all parameters provided."""
        calendar_entity_id = "calendar.work"
        manual_override_entity_id = "input_boolean.manual_override"
        
        scheduler = ProbeScheduler(
            self.hass,
            self.thermal_model,
            self.presence_entity_id,
            self.weather_entity_id,
            calendar_entity_id,
            manual_override_entity_id
        )
        
        assert scheduler._hass == self.hass
        assert scheduler._model == self.thermal_model
        assert scheduler._presence_entity_id == self.presence_entity_id
        assert scheduler._weather_entity_id == self.weather_entity_id
        assert scheduler._calendar_entity_id == calendar_entity_id
        assert scheduler._manual_override_entity_id == manual_override_entity_id
        
    def test_init_with_minimal_parameters(self):
        """Test initialization with minimal required parameters."""
        scheduler = ProbeScheduler(
            self.hass,
            self.thermal_model,
            self.presence_entity_id,
            self.weather_entity_id
        )
        
        assert scheduler._hass == self.hass
        assert scheduler._model == self.thermal_model
        assert scheduler._presence_entity_id == self.presence_entity_id
        assert scheduler._weather_entity_id == self.weather_entity_id
        assert scheduler._calendar_entity_id is None
        assert scheduler._manual_override_entity_id is None
        
    def test_init_with_none_optional_parameters(self):
        """Test initialization with explicitly None optional parameters."""
        scheduler = ProbeScheduler(
            self.hass,
            self.thermal_model,
            self.presence_entity_id,
            self.weather_entity_id,
            calendar_entity_id=None,
            manual_override_entity_id=None
        )
        
        assert scheduler._calendar_entity_id is None
        assert scheduler._manual_override_entity_id is None
        
    def test_init_invalid_hass_parameter(self):
        """Test initialization with invalid hass parameter."""
        with pytest.raises(TypeError):
            ProbeScheduler(
                None,  # Invalid hass
                self.thermal_model,
                self.presence_entity_id,
                self.weather_entity_id
            )
            
    def test_init_invalid_thermal_model_parameter(self):
        """Test initialization with invalid thermal_model parameter."""
        with pytest.raises(TypeError):
            ProbeScheduler(
                self.hass,
                None,  # Invalid thermal_model
                self.presence_entity_id,
                self.weather_entity_id
            )
            
    def test_init_missing_required_parameters(self):
        """Test initialization fails with missing required parameters."""
        with pytest.raises(TypeError):
            ProbeScheduler(self.hass)  # Missing required parameters
            
    def test_logger_setup(self):
        """Test that logger is properly set up."""
        scheduler = ProbeScheduler(
            self.hass,
            self.thermal_model,
            self.presence_entity_id,
            self.weather_entity_id
        )
        
        # Logger should be set up and available
        assert hasattr(scheduler, '_logger')
        assert scheduler._logger is not None
        assert scheduler._logger.name.endswith('probe_scheduler')


class TestProbeSchedulerConstants:
    """Test ProbeScheduler configuration constants."""
    
    def test_min_probe_interval_constant(self):
        """Test MIN_PROBE_INTERVAL constant value."""
        assert MIN_PROBE_INTERVAL == timedelta(hours=12)
        
    def test_max_probe_interval_constant(self):
        """Test MAX_PROBE_INTERVAL constant value."""
        assert MAX_PROBE_INTERVAL == timedelta(days=7)
        
    def test_quiet_hours_start_constant(self):
        """Test QUIET_HOURS_START constant value."""
        assert QUIET_HOURS_START == time(22, 0)
        
    def test_quiet_hours_end_constant(self):
        """Test QUIET_HOURS_END constant value."""
        assert QUIET_HOURS_END == time(7, 0)
        
    def test_outdoor_temp_bins_constant(self):
        """Test OUTDOOR_TEMP_BINS constant value."""
        expected_bins = [-10, 0, 10, 20, 30]
        assert OUTDOOR_TEMP_BINS == expected_bins
        assert len(OUTDOOR_TEMP_BINS) == 5
        
    def test_outdoor_temp_bins_ordered(self):
        """Test OUTDOOR_TEMP_BINS are properly ordered."""
        bins = OUTDOOR_TEMP_BINS
        for i in range(len(bins) - 1):
            assert bins[i] < bins[i + 1], f"Bins not ordered: {bins[i]} >= {bins[i + 1]}"
            
    def test_constants_types(self):
        """Test that constants have correct types."""
        assert isinstance(MIN_PROBE_INTERVAL, timedelta)
        assert isinstance(MAX_PROBE_INTERVAL, timedelta)
        assert isinstance(QUIET_HOURS_START, time)
        assert isinstance(QUIET_HOURS_END, time)
        assert isinstance(OUTDOOR_TEMP_BINS, list)
        assert all(isinstance(bin_val, int) for bin_val in OUTDOOR_TEMP_BINS)


class TestProbeSchedulerQuietHours:
    """Test ProbeScheduler quiet hours detection functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.hass = Mock()
        self.thermal_model = Mock()
        self.scheduler = ProbeScheduler(
            hass=self.hass,
            thermal_model=self.thermal_model,
            presence_entity_id="binary_sensor.presence",
            weather_entity_id="weather.home"
        )
    
    def test_quiet_hours_during_night_hours(self):
        """Test that times between 22:00-07:00 are detected as quiet hours."""
        from datetime import datetime
        
        # Test various times during quiet hours
        quiet_times = [
            datetime(2025, 8, 18, 22, 30, 0),  # 22:30
            datetime(2025, 8, 18, 23, 15, 0),  # 23:15  
            datetime(2025, 8, 19, 2, 0, 0),    # 02:00 (next day)
            datetime(2025, 8, 19, 6, 30, 0),   # 06:30 (next day)
        ]
        
        for quiet_time in quiet_times:
            result = self.scheduler._is_quiet_hours(quiet_time)
            assert result is True, f"Expected {quiet_time.strftime('%H:%M')} to be quiet hours"
    
    def test_active_hours_during_day(self):
        """Test that times between 07:00-22:00 are NOT quiet hours."""
        from datetime import datetime
        
        # Test various times during active hours
        active_times = [
            datetime(2025, 8, 18, 8, 0, 0),    # 08:00
            datetime(2025, 8, 18, 12, 30, 0),  # 12:30
            datetime(2025, 8, 18, 15, 45, 0),  # 15:45
            datetime(2025, 8, 18, 21, 30, 0),  # 21:30
        ]
        
        for active_time in active_times:
            result = self.scheduler._is_quiet_hours(active_time)
            assert result is False, f"Expected {active_time.strftime('%H:%M')} to be active hours"
    
    def test_quiet_hours_boundary_times(self):
        """Test exact boundary times for quiet hours transitions."""
        from datetime import datetime
        
        # Test boundary cases
        boundary_cases = [
            (datetime(2025, 8, 18, 21, 59, 0), False),  # 21:59 - still active
            (datetime(2025, 8, 18, 22, 0, 0), True),    # 22:00 - start of quiet
            (datetime(2025, 8, 18, 22, 1, 0), True),    # 22:01 - within quiet
            (datetime(2025, 8, 19, 6, 59, 0), True),    # 06:59 - still quiet (next day)
            (datetime(2025, 8, 19, 7, 0, 0), False),    # 07:00 - end of quiet
            (datetime(2025, 8, 19, 7, 1, 0), False),    # 07:01 - back to active
        ]
        
        for test_time, expected_quiet in boundary_cases:
            result = self.scheduler._is_quiet_hours(test_time)
            assert result is expected_quiet, f"Expected {test_time.strftime('%H:%M')} quiet={expected_quiet}"
    
    def test_quiet_hours_with_none_uses_current_time(self):
        """Test that _is_quiet_hours() uses current time when current_time=None."""
        from datetime import datetime
        from unittest.mock import patch
        
        with patch('custom_components.smart_climate.probe_scheduler.datetime') as mock_datetime:
            # Mock current time to be during quiet hours
            mock_now = datetime(2025, 8, 18, 23, 30, 0)
            mock_datetime.now.return_value = mock_now
            
            result = self.scheduler._is_quiet_hours(None)
            assert result is True
            mock_datetime.now.assert_called_once()
    
    def test_quiet_hours_overnight_span_handling(self):
        """Test that overnight quiet hours (22:00 to 07:00 next day) work correctly."""
        from datetime import datetime
        
        # Test that the overnight span is handled correctly
        test_cases = [
            (datetime(2025, 8, 18, 23, 45, 0), True),   # Late night should be quiet
            (datetime(2025, 8, 19, 5, 30, 0), True),    # Early morning should be quiet
            (datetime(2025, 8, 18, 21, 45, 0), False),  # Late evening should NOT be quiet
            (datetime(2025, 8, 19, 8, 30, 0), False),   # Morning should NOT be quiet
        ]
        
        for test_time, expected_quiet in test_cases:
            result = self.scheduler._is_quiet_hours(test_time)
            assert result is expected_quiet, f"Time {test_time} should be quiet={expected_quiet}"
    
    def test_quiet_hours_timezone_awareness(self):
        """Test that quiet hours work with timezone-aware datetime objects."""
        from datetime import datetime, timezone
        
        # Create timezone-aware datetime objects
        tz = timezone.utc
        
        # 22:30 UTC should be treated as quiet hours
        utc_quiet_time = datetime(2025, 8, 18, 22, 30, 0, tzinfo=tz)
        # 08:00 UTC should be treated as active hours  
        utc_active_time = datetime(2025, 8, 18, 8, 0, 0, tzinfo=tz)
        
        quiet_result = self.scheduler._is_quiet_hours(utc_quiet_time)
        active_result = self.scheduler._is_quiet_hours(utc_active_time)
        
        assert quiet_result is True
        assert active_result is False


class TestProbeSchedulerTemperatureBins:
    """Test temperature bin calculation methods."""
    
    @pytest.fixture
    def probe_scheduler(self):
        """Create a ProbeScheduler instance for testing."""
        hass = Mock()
        thermal_model = Mock()
        return ProbeScheduler(
            hass=hass,
            thermal_model=thermal_model,
            presence_entity_id="binary_sensor.home_presence",
            weather_entity_id="weather.home"
        )
    
    def test_get_temp_bin_normal_temperatures(self, probe_scheduler):
        """Test temperature bin assignment for normal temperature ranges."""
        # OUTDOOR_TEMP_BINS = [-10, 0, 10, 20, 30] creates 6 bins:
        # bin 0: < -10, bin 1: -10 to 0, bin 2: 0 to 10, bin 3: 10 to 20, bin 4: 20 to 30, bin 5: > 30
        
        # Test temperatures in each bin
        assert probe_scheduler._get_temp_bin(-15.0) == 0  # < -10
        assert probe_scheduler._get_temp_bin(-5.0) == 1   # -10 to 0
        assert probe_scheduler._get_temp_bin(5.0) == 2    # 0 to 10
        assert probe_scheduler._get_temp_bin(15.0) == 3   # 10 to 20
        assert probe_scheduler._get_temp_bin(25.0) == 4   # 20 to 30
        assert probe_scheduler._get_temp_bin(35.0) == 5   # > 30
    
    def test_get_temp_bin_boundary_values(self, probe_scheduler):
        """Test temperature bin assignment at exact boundary values."""
        # Test exact boundary values - should go to higher bin
        assert probe_scheduler._get_temp_bin(-10.0) == 1  # Exactly -10
        assert probe_scheduler._get_temp_bin(0.0) == 2    # Exactly 0
        assert probe_scheduler._get_temp_bin(10.0) == 3   # Exactly 10
        assert probe_scheduler._get_temp_bin(20.0) == 4   # Exactly 20
        assert probe_scheduler._get_temp_bin(30.0) == 5   # Exactly 30
    
    def test_get_temp_bin_extreme_temperatures(self, probe_scheduler):
        """Test temperature bin assignment for extreme values."""
        # Test very extreme temperatures
        assert probe_scheduler._get_temp_bin(-50.0) == 0  # Very cold
        assert probe_scheduler._get_temp_bin(50.0) == 5   # Very hot
        
        # Test just outside normal range
        assert probe_scheduler._get_temp_bin(-10.1) == 0  # Just below -10
        assert probe_scheduler._get_temp_bin(30.1) == 5   # Just above 30
    
    def test_get_bin_coverage_empty_history(self, probe_scheduler):
        """Test bin coverage calculation with empty probe history."""
        empty_history = []
        coverage = probe_scheduler._get_bin_coverage(empty_history)
        assert coverage == 0.0  # No probes means no coverage
    
    def test_get_bin_coverage_single_bin(self, probe_scheduler):
        """Test bin coverage with probes from only one temperature bin."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        # Create probes all from the same temperature bin (bin 2: 0-10°C)
        probe_history = [
            ProbeResult(
                tau_value=90.0,
                confidence=0.8,
                duration=3600,
                fit_quality=0.9,
                aborted=False,
                timestamp=datetime.now(timezone.utc),
                outdoor_temp=5.0  # bin 2
            ),
            ProbeResult(
                tau_value=92.0,
                confidence=0.85,
                duration=3600,
                fit_quality=0.88,
                aborted=False,
                timestamp=datetime.now(timezone.utc),
                outdoor_temp=8.0  # bin 2
            )
        ]
        
        coverage = probe_scheduler._get_bin_coverage(probe_history)
        # 1 bin out of 6 total bins = 1/6 ≈ 0.167
        assert coverage == pytest.approx(1.0 / 6.0, abs=0.001)
    
    def test_get_bin_coverage_multiple_bins(self, probe_scheduler):
        """Test bin coverage with probes from multiple temperature bins."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        probe_history = [
            ProbeResult(
                tau_value=90.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=-5.0  # bin 1
            ),
            ProbeResult(
                tau_value=92.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=5.0  # bin 2
            ),
            ProbeResult(
                tau_value=94.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=15.0  # bin 3
            ),
            ProbeResult(
                tau_value=96.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=25.0  # bin 4
            )
        ]
        
        coverage = probe_scheduler._get_bin_coverage(probe_history)
        # 4 bins out of 6 total bins = 4/6 ≈ 0.667
        assert coverage == pytest.approx(4.0 / 6.0, abs=0.001)
    
    def test_get_bin_coverage_full_coverage(self, probe_scheduler):
        """Test bin coverage with probes covering all temperature bins."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        probe_history = [
            ProbeResult(
                tau_value=90.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=-15.0  # bin 0
            ),
            ProbeResult(
                tau_value=91.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=-5.0  # bin 1
            ),
            ProbeResult(
                tau_value=92.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=5.0  # bin 2
            ),
            ProbeResult(
                tau_value=93.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=15.0  # bin 3
            ),
            ProbeResult(
                tau_value=94.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=25.0  # bin 4
            ),
            ProbeResult(
                tau_value=95.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=35.0  # bin 5
            )
        ]
        
        coverage = probe_scheduler._get_bin_coverage(probe_history)
        # All 6 bins covered = 6/6 = 1.0
        assert coverage == 1.0
    
    def test_get_bin_coverage_with_none_outdoor_temp(self, probe_scheduler):
        """Test bin coverage calculation when some probes have None outdoor_temp."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        probe_history = [
            ProbeResult(
                tau_value=90.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=5.0  # bin 2 - valid
            ),
            ProbeResult(
                tau_value=91.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=None  # Should be ignored
            ),
            ProbeResult(
                tau_value=92.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=15.0  # bin 3 - valid
            )
        ]
        
        coverage = probe_scheduler._get_bin_coverage(probe_history)
        # 2 valid bins out of 6 total bins = 2/6 ≈ 0.333
        assert coverage == pytest.approx(2.0 / 6.0, abs=0.001)
    
    def test_get_bin_coverage_duplicate_bins(self, probe_scheduler):
        """Test bin coverage when multiple probes are in the same bins."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        probe_history = [
            ProbeResult(
                tau_value=90.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=5.0  # bin 2
            ),
            ProbeResult(
                tau_value=91.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=7.0  # bin 2 (same bin)
            ),
            ProbeResult(
                tau_value=92.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=15.0  # bin 3
            ),
            ProbeResult(
                tau_value=93.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=17.0  # bin 3 (same bin)
            )
        ]
        
        coverage = probe_scheduler._get_bin_coverage(probe_history)
        # Only 2 unique bins covered out of 6 total bins = 2/6 ≈ 0.333
        assert coverage == pytest.approx(2.0 / 6.0, abs=0.001)

    def test_create_adaptive_bins_insufficient_data(self, probe_scheduler):
        """Test adaptive bin creation with insufficient historical data."""
        # Less than 50 samples should return static fallback bins
        historical_temps = [15.0, 20.0, 25.0]  # Only 3 samples
        
        adaptive_bins = probe_scheduler._create_adaptive_bins(historical_temps)
        
        # Should fallback to static bins: [-10, 0, 10, 20, 30]
        assert adaptive_bins == [-10, 0, 10, 20, 30]
    
    def test_create_adaptive_bins_sufficient_data_temperate(self, probe_scheduler):
        """Test adaptive bin creation with sufficient temperate climate data."""
        # Temperate climate: temperatures ranging from -5 to 35°C
        historical_temps = []
        # Create 60 temperature samples distributed across temperate range
        for temp in range(-5, 36, 2):  # -5, -3, -1, 1, 3, ... 35 (21 unique temps)
            historical_temps.extend([temp] * 3)  # 3 samples each = 63 total samples
        
        adaptive_bins = probe_scheduler._create_adaptive_bins(historical_temps)
        
        # Should create 5 boundaries for 6 bins based on percentiles
        assert len(adaptive_bins) == 5
        # Bins should be roughly: [-5, 5, 15, 25, 35] for temperate climate
        assert adaptive_bins[0] >= -10  # First bin shouldn't be too extreme
        assert adaptive_bins[-1] <= 40   # Last bin shouldn't be too extreme
        assert all(adaptive_bins[i] < adaptive_bins[i+1] for i in range(len(adaptive_bins)-1))  # Sorted
    
    def test_create_adaptive_bins_tropical_climate(self, probe_scheduler):
        """Test adaptive bin creation with tropical climate data."""
        # Tropical climate: temperatures ranging from 15 to 35°C (narrow high-temp range)
        historical_temps = []
        for temp in range(15, 36):  # 15-35°C
            historical_temps.extend([temp] * 3)  # 3 samples each = 63 total samples
        
        adaptive_bins = probe_scheduler._create_adaptive_bins(historical_temps)
        
        assert len(adaptive_bins) == 5
        # All bins should be in tropical range
        assert all(bin_temp >= 10 for bin_temp in adaptive_bins)
        assert all(bin_temp <= 40 for bin_temp in adaptive_bins)
        # Should have finer granularity in the narrow tropical range
        assert max(adaptive_bins) - min(adaptive_bins) <= 30
    
    def test_create_adaptive_bins_arctic_climate(self, probe_scheduler):
        """Test adaptive bin creation with arctic climate data."""
        # Arctic climate: temperatures ranging from -30 to 10°C (narrow low-temp range)
        historical_temps = []
        for temp in range(-30, 11, 2):  # -30 to 10°C, every 2°C
            historical_temps.extend([temp] * 3)  # 3 samples each = 63 total samples
        
        adaptive_bins = probe_scheduler._create_adaptive_bins(historical_temps)
        
        assert len(adaptive_bins) == 5
        # All bins should be in arctic range
        assert all(bin_temp >= -35 for bin_temp in adaptive_bins)
        assert all(bin_temp <= 15 for bin_temp in adaptive_bins)
        # Should focus on narrow arctic range
        assert min(adaptive_bins) <= -20
    
    def test_create_adaptive_bins_desert_climate(self, probe_scheduler):
        """Test adaptive bin creation with desert climate data."""
        # Desert climate: extreme range from -5 to 55°C
        historical_temps = []
        # Create samples with more extreme spread
        for temp in [-5, 0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]:
            historical_temps.extend([temp] * 4)  # 4 samples each = 52 total samples
        
        adaptive_bins = probe_scheduler._create_adaptive_bins(historical_temps)
        
        assert len(adaptive_bins) == 5
        # Should span the full desert range
        assert min(adaptive_bins) <= 0
        assert max(adaptive_bins) >= 45
        # Should have wide spread
        assert max(adaptive_bins) - min(adaptive_bins) >= 40
    
    def test_create_adaptive_bins_custom_bin_count(self, probe_scheduler):
        """Test adaptive bin creation with custom number of bins."""
        historical_temps = list(range(-10, 41, 2))  # 26 samples from -10 to 40
        historical_temps.extend(historical_temps)  # Duplicate to get 52 samples
        
        # Test with 4 bins (3 boundaries)
        adaptive_bins = probe_scheduler._create_adaptive_bins(historical_temps, num_bins=4)
        assert len(adaptive_bins) == 3
        
        # Test with 8 bins (7 boundaries)  
        adaptive_bins = probe_scheduler._create_adaptive_bins(historical_temps, num_bins=8)
        assert len(adaptive_bins) == 7
    
    def test_create_adaptive_bins_minimum_spread(self, probe_scheduler):
        """Test that adaptive bins maintain minimum 5°C spread between boundaries."""
        # Create data clustered around 20°C with very little variation
        historical_temps = []
        for temp in [19.0, 19.5, 20.0, 20.5, 21.0]:
            historical_temps.extend([temp] * 11)  # 55 total samples
        
        adaptive_bins = probe_scheduler._create_adaptive_bins(historical_temps)
        
        # Should enforce minimum 5°C spread between bins
        for i in range(len(adaptive_bins) - 1):
            assert adaptive_bins[i+1] - adaptive_bins[i] >= 5
    
    def test_analyze_historical_temperatures_empty_history(self, probe_scheduler):
        """Test historical temperature analysis with empty probe history."""
        # Mock empty probe history
        probe_scheduler._model._probe_history = []
        
        with patch.object(probe_scheduler, '_get_current_outdoor_temperature', return_value=None):
            historical_temps = probe_scheduler._analyze_historical_temperatures()
        
        # Should return empty list when no data available
        assert historical_temps == []
    
    def test_analyze_historical_temperatures_probe_history_only(self, probe_scheduler):
        """Test historical temperature analysis using only probe history."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        # Mock probe history with outdoor temperatures
        mock_probes = [
            ProbeResult(90.0, 0.8, 3600, 0.9, False, datetime.now(timezone.utc), 15.0),
            ProbeResult(92.0, 0.8, 3600, 0.9, False, datetime.now(timezone.utc), 20.0),
            ProbeResult(88.0, 0.8, 3600, 0.9, False, datetime.now(timezone.utc), 10.0),
            ProbeResult(94.0, 0.8, 3600, 0.9, False, datetime.now(timezone.utc), None),  # Should be ignored
        ]
        probe_scheduler._model._probe_history = mock_probes
        
        with patch.object(probe_scheduler, '_get_current_outdoor_temperature', return_value=None):
            historical_temps = probe_scheduler._analyze_historical_temperatures()
        
        # Should extract temperatures from probe history, ignoring None values
        assert sorted(historical_temps) == [10.0, 15.0, 20.0]
    
    def test_analyze_historical_temperatures_with_current_weather(self, probe_scheduler):
        """Test historical temperature analysis including current weather data."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        # Mock probe history
        mock_probes = [
            ProbeResult(90.0, 0.8, 3600, 0.9, False, datetime.now(timezone.utc), 15.0),
            ProbeResult(92.0, 0.8, 3600, 0.9, False, datetime.now(timezone.utc), 20.0),
        ]
        probe_scheduler._model._probe_history = mock_probes
        
        # Mock current outdoor temperature
        with patch.object(probe_scheduler, '_get_current_outdoor_temperature', return_value=25.0):
            historical_temps = probe_scheduler._analyze_historical_temperatures()
        
        # Should include current weather data
        assert sorted(historical_temps) == [15.0, 20.0, 25.0]
    
    def test_update_temperature_bins_sufficient_data(self, probe_scheduler):
        """Test temperature bin update with sufficient historical data."""
        # Mock sufficient historical data
        with patch.object(probe_scheduler, '_analyze_historical_temperatures') as mock_analyze:
            mock_analyze.return_value = list(range(-10, 41, 2))  # 26 samples
            mock_analyze.return_value.extend(mock_analyze.return_value)  # 52 samples total
            
            with patch.object(probe_scheduler, '_create_adaptive_bins') as mock_create:
                mock_create.return_value = [-5, 5, 15, 25, 35]
                
                probe_scheduler._update_temperature_bins()
                
                # Should call analysis and bin creation
                mock_analyze.assert_called_once()
                mock_create.assert_called_once()
                
                # Should update internal adaptive bins
                assert hasattr(probe_scheduler, '_adaptive_bins')
                assert probe_scheduler._adaptive_bins == [-5, 5, 15, 25, 35]
    
    def test_update_temperature_bins_insufficient_data(self, probe_scheduler):
        """Test temperature bin update with insufficient historical data."""
        # Mock insufficient historical data
        with patch.object(probe_scheduler, '_analyze_historical_temperatures') as mock_analyze:
            mock_analyze.return_value = [15.0, 20.0, 25.0]  # Only 3 samples
            
            probe_scheduler._update_temperature_bins()
            
            # Should fallback to static bins (stored in _adaptive_bins as None or static)
            assert not hasattr(probe_scheduler, '_adaptive_bins') or probe_scheduler._adaptive_bins is None
    
    def test_get_effective_temperature_bins_static_fallback(self, probe_scheduler):
        """Test getting effective temperature bins when using static fallback."""
        # No adaptive bins set (fallback scenario)
        if hasattr(probe_scheduler, '_adaptive_bins'):
            delattr(probe_scheduler, '_adaptive_bins')
        
        effective_bins = probe_scheduler._get_effective_temperature_bins()
        
        # Should return static OUTDOOR_TEMP_BINS
        assert effective_bins == [-10, 0, 10, 20, 30]
    
    def test_get_effective_temperature_bins_adaptive(self, probe_scheduler):
        """Test getting effective temperature bins when adaptive bins are available."""
        # Set adaptive bins
        probe_scheduler._adaptive_bins = [-5, 5, 15, 25, 35]
        
        effective_bins = probe_scheduler._get_effective_temperature_bins()
        
        # Should return adaptive bins
        assert effective_bins == [-5, 5, 15, 25, 35]
    
    def test_get_temp_bin_with_adaptive_bins(self, probe_scheduler):
        """Test temperature bin calculation using adaptive bins."""
        # Set adaptive bins for tropical climate
        probe_scheduler._adaptive_bins = [15, 20, 25, 30, 35]
        
        # Mock _get_effective_temperature_bins to return adaptive bins
        with patch.object(probe_scheduler, '_get_effective_temperature_bins', return_value=[15, 20, 25, 30, 35]):
            # Test binning with adaptive tropical bins
            assert probe_scheduler._get_temp_bin(10.0) == 0   # < 15 (first bin)
            assert probe_scheduler._get_temp_bin(17.0) == 1   # 15-20 (second bin)  
            assert probe_scheduler._get_temp_bin(22.0) == 2   # 20-25 (third bin)
            assert probe_scheduler._get_temp_bin(27.0) == 3   # 25-30 (fourth bin)
            assert probe_scheduler._get_temp_bin(32.0) == 4   # 30-35 (fifth bin)
            assert probe_scheduler._get_temp_bin(40.0) == 5   # > 35 (last bin)
    
    def test_adaptive_bins_integration_workflow(self, probe_scheduler):
        """Test complete adaptive binning workflow integration."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        # Simulate probe history for temperate climate
        mock_probes = []
        for temp in range(-5, 36, 5):  # Temperate range: -5, 0, 5, 10, 15, 20, 25, 30, 35
            for _ in range(6):  # 6 samples per temperature = 54 total samples
                mock_probes.append(
                    ProbeResult(90.0, 0.8, 3600, 0.9, False, datetime.now(timezone.utc), float(temp))
                )
        
        probe_scheduler._model._probe_history = mock_probes
        
        # Run complete workflow
        with patch.object(probe_scheduler, '_get_current_outdoor_temperature', return_value=18.0):
            probe_scheduler._update_temperature_bins()
            
            # Should have created adaptive bins
            assert hasattr(probe_scheduler, '_adaptive_bins')
            adaptive_bins = probe_scheduler._get_effective_temperature_bins()
            
            # Adaptive bins should be different from static bins
            assert adaptive_bins != [-10, 0, 10, 20, 30]
            
            # Should work with temperature binning
            current_bin = probe_scheduler._get_temp_bin(18.0)
            assert 0 <= current_bin <= 5  # Valid bin index


class TestProbeSchedulerInformationGain:
    """Test suite for information gain calculation methods."""
    
    @pytest.fixture
    def probe_scheduler(self):
        """Create ProbeScheduler instance for testing."""
        from unittest.mock import Mock
        from custom_components.smart_climate.probe_scheduler import ProbeScheduler
        
        mock_hass = Mock()
        mock_thermal_model = Mock()
        
        return ProbeScheduler(
            hass=mock_hass,
            thermal_model=mock_thermal_model,
            presence_entity_id=None,
            weather_entity_id=None
        )
    
    def test_calculate_information_gain_empty_history(self, probe_scheduler):
        """Test information gain with empty probe history."""
        current_temp = 15.0
        probe_history = []
        
        gain = probe_scheduler._calculate_information_gain(current_temp, probe_history)
        
        # Empty history = maximum gain
        assert gain == 1.0
    
    def test_calculate_information_gain_single_probe_same_bin(self, probe_scheduler):
        """Test information gain when current temp is in same bin as only probe."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        current_temp = 15.0  # bin 3
        probe_history = [
            ProbeResult(
                tau_value=90.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=12.0  # bin 3 (same bin)
            )
        ]
        
        gain = probe_scheduler._calculate_information_gain(current_temp, probe_history)
        
        # Low bin coverage (1/6) but high bin saturation (1 probe in same bin)
        # Coverage factor = 1.0 - (1/6) = 5/6 ≈ 0.833
        # Saturation factor = 1.0 / (1 + 1) = 0.5
        # Total gain = min(0.833 + 0.5, 1.0) = 1.0 (clamped)
        assert gain == pytest.approx(1.0, abs=0.01)
    
    def test_calculate_information_gain_single_probe_different_bin(self, probe_scheduler):
        """Test information gain when current temp is in different bin than existing probe."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        current_temp = 15.0  # bin 3
        probe_history = [
            ProbeResult(
                tau_value=90.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=5.0  # bin 2 (different bin)
            )
        ]
        
        gain = probe_scheduler._calculate_information_gain(current_temp, probe_history)
        
        # Low bin coverage (1/6) and no saturation in current bin (0 probes)
        # Coverage factor = 1.0 - (1/6) = 5/6 ≈ 0.833
        # Saturation factor = 1.0 / (0 + 1) = 1.0
        # Total gain = min(0.833 + 1.0, 1.0) = 1.0 (clamped)
        assert gain == pytest.approx(1.0, abs=0.01)
    
    def test_calculate_information_gain_high_coverage_unsaturated_bin(self, probe_scheduler):
        """Test information gain with high coverage but current bin unsaturated."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        current_temp = 35.0  # bin 5 (highest bin, >= 30°C)
        probe_history = [
            # Cover 5 out of 6 bins (high coverage)
            ProbeResult(tau_value=90.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=-15.0),  # bin 0
            ProbeResult(tau_value=91.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=-5.0),   # bin 1
            ProbeResult(tau_value=92.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=5.0),    # bin 2
            ProbeResult(tau_value=93.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=15.0),   # bin 3
            ProbeResult(tau_value=94.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=25.0),   # bin 4
        ]
        
        gain = probe_scheduler._calculate_information_gain(current_temp, probe_history)
        
        # High coverage (5/6) but no probes in current bin (35°C = bin 5)
        # Coverage factor = 1.0 - (5/6) = 1/6 ≈ 0.167
        # Saturation factor = 1.0 / (0 + 1) = 1.0
        # Total gain = min(0.167 + 1.0, 1.0) = 1.0 (clamped)
        assert gain == pytest.approx(1.0, abs=0.01)
    
    def test_calculate_information_gain_high_coverage_saturated_bin(self, probe_scheduler):
        """Test information gain with high coverage and saturated current bin."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        current_temp = 25.0  # bin 4
        probe_history = [
            # Cover all 6 bins with multiple probes in target bin
            ProbeResult(tau_value=90.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=-15.0),  # bin 0
            ProbeResult(tau_value=91.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=-5.0),   # bin 1
            ProbeResult(tau_value=92.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=5.0),    # bin 2
            ProbeResult(tau_value=93.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=15.0),   # bin 3
            ProbeResult(tau_value=94.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=22.0),   # bin 4
            ProbeResult(tau_value=95.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=24.0),   # bin 4 (same)
            ProbeResult(tau_value=96.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=26.0),   # bin 4 (same)
            ProbeResult(tau_value=97.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=35.0),   # bin 5
        ]
        
        gain = probe_scheduler._calculate_information_gain(current_temp, probe_history)
        
        # Full coverage (6/6 = 1.0) and high saturation in current bin (3 probes in bin 4)
        # Coverage factor = 1.0 - 1.0 = 0.0
        # Saturation factor = 1.0 / (3 + 1) = 0.25
        # Total gain = min(0.0 + 0.25, 1.0) = 0.25
        assert gain == pytest.approx(0.25, abs=0.01)
    
    def test_calculate_information_gain_with_none_outdoor_temps(self, probe_scheduler):
        """Test information gain calculation ignores probes with None outdoor_temp."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        current_temp = 15.0  # bin 3
        probe_history = [
            ProbeResult(
                tau_value=90.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=None  # Should be ignored
            ),
            ProbeResult(
                tau_value=91.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=12.0  # bin 3, should be counted
            ),
            ProbeResult(
                tau_value=92.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=None  # Should be ignored
            )
        ]
        
        gain = probe_scheduler._calculate_information_gain(current_temp, probe_history)
        
        # Only 1 valid probe in bin 3, coverage = 1/6
        # Coverage factor = 1.0 - (1/6) = 5/6 ≈ 0.833
        # Saturation factor = 1.0 / (1 + 1) = 0.5 
        # Total gain = min(0.833 + 0.5, 1.0) = 1.0 (clamped)
        assert gain == pytest.approx(1.0, abs=0.01)
    
    def test_calculate_information_gain_medium_scenario(self, probe_scheduler):
        """Test information gain calculation in medium coverage scenario."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        current_temp = 15.0  # bin 3
        probe_history = [
            # 3 bins covered (50% coverage), 2 probes in target bin
            ProbeResult(tau_value=90.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=5.0),    # bin 2
            ProbeResult(tau_value=91.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=12.0),   # bin 3
            ProbeResult(tau_value=92.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=18.0),   # bin 3 (same)
            ProbeResult(tau_value=93.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=25.0),   # bin 4
        ]
        
        gain = probe_scheduler._calculate_information_gain(current_temp, probe_history)
        
        # Medium coverage (3/6 = 0.5) and medium saturation in current bin (2 probes)
        # Coverage factor = 1.0 - 0.5 = 0.5
        # Saturation factor = 1.0 / (2 + 1) = 0.333
        # Total gain = min(0.5 + 0.333, 1.0) = 0.833
        assert gain == pytest.approx(0.833, abs=0.01)
    
    def test_has_high_information_gain_empty_history(self, probe_scheduler):
        """Test high information gain determination with empty history."""
        current_temp = 15.0
        history = []
        
        result = probe_scheduler._has_high_information_gain(current_temp, history)
        
        # Empty history always has high gain
        assert result is True
    
    def test_has_high_information_gain_new_temperature_bin(self, probe_scheduler):
        """Test high gain when current temperature is in a new bin."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        current_temp = 35.0  # bin 5 (not covered)
        history = [
            ProbeResult(
                tau_value=90.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=5.0  # bin 2
            )
        ]
        
        result = probe_scheduler._has_high_information_gain(current_temp, history)
        
        # New bin should have high gain
        assert result is True
    
    def test_has_high_information_gain_low_coverage(self, probe_scheduler):
        """Test high gain with low coverage scenario."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        current_temp = 15.0  # bin 3
        history = [
            ProbeResult(
                tau_value=90.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=5.0  # bin 2
            ),
            ProbeResult(
                tau_value=91.0, confidence=0.8, duration=3600, fit_quality=0.9,
                aborted=False, timestamp=datetime.now(timezone.utc),
                outdoor_temp=12.0  # bin 3 (same as current)
            )
        ]
        
        result = probe_scheduler._has_high_information_gain(current_temp, history)
        
        # Low coverage (2/6 = 33%) should have high gain
        assert result is True
    
    def test_has_high_information_gain_high_coverage_low_saturation(self, probe_scheduler):
        """Test gain when coverage is high but current bin has low saturation."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        current_temp = 35.0  # bin 5 (unsaturated)
        history = [
            # High coverage but target bin unsaturated
            ProbeResult(tau_value=90.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=-15.0),  # bin 0
            ProbeResult(tau_value=91.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=-5.0),   # bin 1
            ProbeResult(tau_value=92.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=5.0),    # bin 2
            ProbeResult(tau_value=93.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=15.0),   # bin 3
            ProbeResult(tau_value=94.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=25.0),   # bin 4
        ]
        
        result = probe_scheduler._has_high_information_gain(current_temp, history)
        
        # High coverage but unsaturated bin should still have high gain
        assert result is True
    
    def test_has_high_information_gain_high_coverage_high_saturation(self, probe_scheduler):
        """Test low gain when both coverage and saturation are high.""" 
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        current_temp = 25.0  # bin 4 (highly saturated)
        history = [
            # Full coverage with high saturation in target bin
            ProbeResult(tau_value=90.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=-15.0),  # bin 0
            ProbeResult(tau_value=91.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=-5.0),   # bin 1  
            ProbeResult(tau_value=92.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=5.0),    # bin 2
            ProbeResult(tau_value=93.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=15.0),   # bin 3
            ProbeResult(tau_value=94.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=22.0),   # bin 4
            ProbeResult(tau_value=95.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=24.0),   # bin 4 (same)
            ProbeResult(tau_value=96.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=26.0),   # bin 4 (same)
            ProbeResult(tau_value=97.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=28.0),   # bin 4 (same)
            ProbeResult(tau_value=98.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=35.0),   # bin 5
        ]
        
        result = probe_scheduler._has_high_information_gain(current_temp, history)
        
        # Full coverage + high saturation should have low gain
        assert result is False
    
    def test_has_high_information_gain_threshold_boundary(self, probe_scheduler):
        """Test gain determination at threshold boundaries."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        current_temp = 15.0  # bin 3
        # Create scenario that results in exactly 0.5 information gain
        history = [
            # Medium coverage, medium saturation scenario
            ProbeResult(tau_value=90.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=5.0),    # bin 2
            ProbeResult(tau_value=91.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=12.0),   # bin 3
            ProbeResult(tau_value=92.0, confidence=0.8, duration=3600, fit_quality=0.9,
                       aborted=False, timestamp=datetime.now(timezone.utc), outdoor_temp=25.0),   # bin 4
        ]
        
        # Calculate the actual gain to verify it triggers the threshold
        actual_gain = probe_scheduler._calculate_information_gain(current_temp, history)
        
        result = probe_scheduler._has_high_information_gain(current_temp, history)
        
        # Should be based on calculated gain vs threshold (0.5 is default threshold)
        if actual_gain >= 0.5:
            assert result is True
        else:
            assert result is False


class TestProbeSchedulerMainDecision:
    """Test ProbeScheduler main decision logic - should_probe_now method."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.hass = Mock()
        self.thermal_model = Mock()
        self.thermal_model.get_probe_count = Mock(return_value=0)
        self.scheduler = ProbeScheduler(
            hass=self.hass,
            thermal_model=self.thermal_model,
            presence_entity_id="binary_sensor.presence",
            weather_entity_id="weather.test"
        )
        
        # Mock the internal methods to allow isolated testing
        self.scheduler._check_maximum_interval_exceeded = Mock(return_value=False)
        self.scheduler._enforce_minimum_interval = Mock(return_value=True) 
        self.scheduler._is_quiet_hours = Mock(return_value=False)
        self.scheduler._is_opportune_time = Mock(return_value=True)
        self.scheduler._has_high_information_gain = Mock(return_value=True)
        
    def test_should_probe_ideal_conditions(self):
        """Test that probe is approved when all conditions are favorable."""
        # Set up ideal conditions
        self.scheduler._check_maximum_interval_exceeded.return_value = False  # Not forced
        self.scheduler._enforce_minimum_interval.return_value = True         # Min interval met
        self.scheduler._is_quiet_hours.return_value = False                  # Not quiet hours
        self.scheduler._is_opportune_time.return_value = True               # User away
        self.scheduler._has_high_information_gain.return_value = True       # High info gain
        
        result = self.scheduler.should_probe_now()
        
        assert result is True
        # Verify all checks were called
        self.scheduler._check_maximum_interval_exceeded.assert_called_once()
        self.scheduler._enforce_minimum_interval.assert_called_once()
        self.scheduler._is_quiet_hours.assert_called_once()
        self.scheduler._is_opportune_time.assert_called_once()
        self.scheduler._has_high_information_gain.assert_called_once()
        
    def test_should_probe_forced_by_maximum_interval(self):
        """Test that probe is forced when maximum interval exceeded."""
        # Maximum interval exceeded should force probe regardless of other conditions
        self.scheduler._check_maximum_interval_exceeded.return_value = True  # FORCE
        self.scheduler._enforce_minimum_interval.return_value = False        # Min not met
        self.scheduler._is_quiet_hours.return_value = True                   # Quiet hours
        self.scheduler._is_opportune_time.return_value = False              # User present
        self.scheduler._has_high_information_gain.return_value = False      # Low info gain
        
        result = self.scheduler.should_probe_now()
        
        assert result is True
        # Should short-circuit after maximum interval check
        self.scheduler._check_maximum_interval_exceeded.assert_called_once()
        # Other methods should not be called when maximum interval forces probe
        self.scheduler._enforce_minimum_interval.assert_not_called()
        self.scheduler._is_quiet_hours.assert_not_called()
        self.scheduler._is_opportune_time.assert_not_called()
        self.scheduler._has_high_information_gain.assert_not_called()
        
    def test_should_probe_blocked_minimum_interval(self):
        """Test that probe is blocked when minimum interval not met."""
        self.scheduler._check_maximum_interval_exceeded.return_value = False  
        self.scheduler._enforce_minimum_interval.return_value = False        # BLOCKED
        
        result = self.scheduler.should_probe_now()
        
        assert result is False
        # Should stop after minimum interval check
        self.scheduler._check_maximum_interval_exceeded.assert_called_once()
        self.scheduler._enforce_minimum_interval.assert_called_once()
        # Subsequent checks should not be called
        self.scheduler._is_quiet_hours.assert_not_called()
        self.scheduler._is_opportune_time.assert_not_called()
        self.scheduler._has_high_information_gain.assert_not_called()
        
    def test_should_probe_blocked_quiet_hours(self):
        """Test that probe is blocked during quiet hours."""
        self.scheduler._check_maximum_interval_exceeded.return_value = False
        self.scheduler._enforce_minimum_interval.return_value = True         
        self.scheduler._is_quiet_hours.return_value = True                   # BLOCKED
        
        result = self.scheduler.should_probe_now()
        
        assert result is False
        # Should stop after quiet hours check
        self.scheduler._check_maximum_interval_exceeded.assert_called_once()
        self.scheduler._enforce_minimum_interval.assert_called_once()
        self.scheduler._is_quiet_hours.assert_called_once()
        # Subsequent checks should not be called
        self.scheduler._is_opportune_time.assert_not_called()
        self.scheduler._has_high_information_gain.assert_not_called()
        
    def test_should_probe_blocked_user_present(self):
        """Test that probe is blocked when user is present."""
        self.scheduler._check_maximum_interval_exceeded.return_value = False
        self.scheduler._enforce_minimum_interval.return_value = True         
        self.scheduler._is_quiet_hours.return_value = False                  
        self.scheduler._is_opportune_time.return_value = False              # BLOCKED
        
        result = self.scheduler.should_probe_now()
        
        assert result is False
        # Should stop after opportune time check
        self.scheduler._check_maximum_interval_exceeded.assert_called_once()
        self.scheduler._enforce_minimum_interval.assert_called_once()
        self.scheduler._is_quiet_hours.assert_called_once()
        self.scheduler._is_opportune_time.assert_called_once()
        # Information gain check should not be called
        self.scheduler._has_high_information_gain.assert_not_called()
        
    def test_should_probe_blocked_low_information_gain(self):
        """Test that probe is blocked when information gain is low."""
        self.scheduler._check_maximum_interval_exceeded.return_value = False
        self.scheduler._enforce_minimum_interval.return_value = True         
        self.scheduler._is_quiet_hours.return_value = False                  
        self.scheduler._is_opportune_time.return_value = True               
        self.scheduler._has_high_information_gain.return_value = False      # BLOCKED
        
        result = self.scheduler.should_probe_now()
        
        assert result is False
        # All checks should be called in order
        self.scheduler._check_maximum_interval_exceeded.assert_called_once()
        self.scheduler._enforce_minimum_interval.assert_called_once()
        self.scheduler._is_quiet_hours.assert_called_once()
        self.scheduler._is_opportune_time.assert_called_once()
        self.scheduler._has_high_information_gain.assert_called_once()
        
    def test_should_probe_decision_tree_logging(self):
        """Test that decision tree includes appropriate logging messages."""
        import logging
        from unittest.mock import patch
        
        # Test the logging for ideal conditions
        self.scheduler._check_maximum_interval_exceeded.return_value = False
        self.scheduler._enforce_minimum_interval.return_value = True         
        self.scheduler._is_quiet_hours.return_value = False                  
        self.scheduler._is_opportune_time.return_value = True               
        self.scheduler._has_high_information_gain.return_value = True       
        
        with patch.object(self.scheduler._logger, 'info') as mock_info:
            with patch.object(self.scheduler._logger, 'debug') as mock_debug:
                result = self.scheduler.should_probe_now()
                
                assert result is True
                # Should log approval message
                mock_info.assert_called_with("Probe approved: all conditions favorable")
                
        # Test the logging for blocked conditions
        self.scheduler._enforce_minimum_interval.return_value = False        
        
        with patch.object(self.scheduler._logger, 'debug') as mock_debug:
            result = self.scheduler.should_probe_now()
            
            assert result is False
            # Should log blocking reason
            mock_debug.assert_called_with("Probe blocked: minimum interval not met")
    
    def test_should_probe_various_blocking_combinations(self):
        """Test probe blocking with various combinations of conditions."""
        # Test case: minimum interval met, but quiet hours and user present
        self.scheduler._check_maximum_interval_exceeded.return_value = False
        self.scheduler._enforce_minimum_interval.return_value = True         
        self.scheduler._is_quiet_hours.return_value = True                   # First blocker
        self.scheduler._is_opportune_time.return_value = False              # Would also block
        self.scheduler._has_high_information_gain.return_value = True       
        
        result = self.scheduler.should_probe_now()
        assert result is False
        
        # Should short-circuit at first blocker (quiet hours)
        self.scheduler._is_quiet_hours.assert_called_once()
        self.scheduler._is_opportune_time.assert_not_called()  # Should not reach this check
        
        # Reset mocks and test different combination
        for method in [self.scheduler._check_maximum_interval_exceeded, 
                      self.scheduler._enforce_minimum_interval,
                      self.scheduler._is_quiet_hours, 
                      self.scheduler._is_opportune_time,
                      self.scheduler._has_high_information_gain]:
            method.reset_mock()
        
        # Test case: all conditions pass except information gain
        self.scheduler._check_maximum_interval_exceeded.return_value = False
        self.scheduler._enforce_minimum_interval.return_value = True         
        self.scheduler._is_quiet_hours.return_value = False                  
        self.scheduler._is_opportune_time.return_value = True               
        self.scheduler._has_high_information_gain.return_value = False      # Only blocker
        
        result = self.scheduler.should_probe_now()
        assert result is False
        
        # All checks should be called since this is the last one
        self.scheduler._check_maximum_interval_exceeded.assert_called_once()
        self.scheduler._enforce_minimum_interval.assert_called_once()
        self.scheduler._is_quiet_hours.assert_called_once()
        self.scheduler._is_opportune_time.assert_called_once()
        self.scheduler._has_high_information_gain.assert_called_once()

class TestProbeSchedulerIntervalChecking:
    """Test ProbeScheduler interval checking methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.hass = Mock()
        self.thermal_model = Mock()
        self.scheduler = ProbeScheduler(
            hass=self.hass,
            thermal_model=self.thermal_model,
            presence_entity_id="binary_sensor.presence",
            weather_entity_id="weather.test"
        )
        
    def test_check_maximum_interval_exceeded_never_probed(self):
        """Test maximum interval check when never probed before."""
        # Mock ThermalManager to return None for last probe time
        mock_thermal_manager = Mock()
        mock_thermal_manager._last_probe_time = None
        self.hass.data = {'smart_climate': {'test_entry': {'thermal_components': {'climate.test': {'thermal_manager': mock_thermal_manager}}}}}
        
        result = self.scheduler._check_maximum_interval_exceeded()
        
        # Should allow probe when never probed before
        assert result is False
        
    def test_check_maximum_interval_exceeded_within_limit(self):
        """Test maximum interval check when within time limit."""
        from datetime import datetime, timedelta
        
        # Mock last probe time to be 3 days ago (within 7-day limit)
        last_probe_time = datetime.now() - timedelta(days=3)
        mock_thermal_manager = Mock()
        mock_thermal_manager._last_probe_time = last_probe_time
        self.hass.data = {'smart_climate': {'test_entry': {'thermal_components': {'climate.test': {'thermal_manager': mock_thermal_manager}}}}}
        
        result = self.scheduler._check_maximum_interval_exceeded()
        
        # Should not force probe when within limit
        assert result is False
        
    def test_check_maximum_interval_exceeded_limit_reached(self):
        """Test maximum interval check when limit is exceeded."""
        from datetime import datetime, timedelta
        
        # Mock last probe time to be 8 days ago (exceeds 7-day limit)
        last_probe_time = datetime.now() - timedelta(days=8)
        mock_thermal_manager = Mock()
        mock_thermal_manager._last_probe_time = last_probe_time
        self.hass.data = {'smart_climate': {'test_entry': {'thermal_components': {'climate.test': {'thermal_manager': mock_thermal_manager}}}}}
        
        result = self.scheduler._check_maximum_interval_exceeded()
        
        # Should force probe when limit exceeded
        assert result is True
        
    def test_check_maximum_interval_exceeded_no_thermal_manager(self):
        """Test maximum interval check when ThermalManager is not available."""
        # Mock missing thermal manager
        self.hass.data = {'smart_climate': {'test_entry': {'thermal_components': {}}}}
        
        result = self.scheduler._check_maximum_interval_exceeded()
        
        # Should not force probe when data unavailable (conservative approach)
        assert result is False
        
    def test_enforce_minimum_interval_never_probed(self):
        """Test minimum interval check when never probed before."""
        # Mock ThermalManager to return None for last probe time
        mock_thermal_manager = Mock()
        mock_thermal_manager._last_probe_time = None
        self.hass.data = {'smart_climate': {'test_entry': {'thermal_components': {'climate.test': {'thermal_manager': mock_thermal_manager}}}}}
        
        result = self.scheduler._enforce_minimum_interval()
        
        # Should allow probe when never probed before
        assert result is True
        
    def test_enforce_minimum_interval_within_limit(self):
        """Test minimum interval check when within time limit."""
        from datetime import datetime, timedelta
        
        # Mock last probe time to be 6 hours ago (within 12-hour minimum)
        last_probe_time = datetime.now() - timedelta(hours=6)
        mock_thermal_manager = Mock()
        mock_thermal_manager._last_probe_time = last_probe_time
        self.hass.data = {'smart_climate': {'test_entry': {'thermal_components': {'climate.test': {'thermal_manager': mock_thermal_manager}}}}}
        
        result = self.scheduler._enforce_minimum_interval()
        
        # Should block probe when within minimum interval
        assert result is False
        
    def test_enforce_minimum_interval_limit_met(self):
        """Test minimum interval check when limit is met."""
        from datetime import datetime, timedelta
        
        # Mock last probe time to be 13 hours ago (exceeds 12-hour minimum)
        last_probe_time = datetime.now() - timedelta(hours=13)
        mock_thermal_manager = Mock()
        mock_thermal_manager._last_probe_time = last_probe_time
        self.hass.data = {'smart_climate': {'test_entry': {'thermal_components': {'climate.test': {'thermal_manager': mock_thermal_manager}}}}}
        
        result = self.scheduler._enforce_minimum_interval()
        
        # Should allow probe when minimum interval exceeded
        assert result is True
        
    def test_enforce_minimum_interval_exactly_at_limit(self):
        """Test minimum interval check at exact boundary."""
        from datetime import datetime, timedelta
        
        # Mock last probe time to be exactly 12 hours ago (at limit)
        last_probe_time = datetime.now() - timedelta(hours=12)
        mock_thermal_manager = Mock()
        mock_thermal_manager._last_probe_time = last_probe_time
        self.hass.data = {'smart_climate': {'test_entry': {'thermal_components': {'climate.test': {'thermal_manager': mock_thermal_manager}}}}}
        
        result = self.scheduler._enforce_minimum_interval()
        
        # Should allow probe when minimum interval is met (>=)
        assert result is True
        
    def test_enforce_minimum_interval_no_thermal_manager(self):
        """Test minimum interval check when ThermalManager is not available."""
        # Mock missing thermal manager
        self.hass.data = {'smart_climate': {'test_entry': {'thermal_components': {}}}}
        
        result = self.scheduler._enforce_minimum_interval()
        
        # Should allow probe when data unavailable (conservative approach)
        assert result is True
        
    def test_interval_checking_with_multiple_entries(self):
        """Test interval checking when multiple config entries exist."""
        from datetime import datetime, timedelta
        
        # Mock multiple config entries - should find the right one
        last_probe_time = datetime.now() - timedelta(days=8)
        mock_thermal_manager = Mock()
        mock_thermal_manager._last_probe_time = last_probe_time
        
        self.hass.data = {
            'smart_climate': {
                'entry1': {'thermal_components': {'climate.other': {'thermal_manager': Mock()}}},
                'test_entry': {'thermal_components': {'climate.test': {'thermal_manager': mock_thermal_manager}}},
                'entry3': {'thermal_components': {'climate.another': {'thermal_manager': Mock()}}}
            }
        }
        
        result = self.scheduler._check_maximum_interval_exceeded()
        
        # Should find the correct thermal manager and return True for exceeded interval
        assert result is True
        
    def test_interval_checking_error_handling(self):
        """Test interval checking with invalid data structures."""
        # Test with completely invalid hass.data structure
        self.hass.data = None
        
        max_result = self.scheduler._check_maximum_interval_exceeded()
        min_result = self.scheduler._enforce_minimum_interval()
        
        # Should handle errors gracefully
        assert max_result is False  # Conservative: don't force probe
        assert min_result is True   # Conservative: allow probe
        
        # Test with missing domain data
        self.hass.data = {'other_domain': {}}
        
        max_result = self.scheduler._check_maximum_interval_exceeded()
        min_result = self.scheduler._enforce_minimum_interval()
        
        assert max_result is False
        assert min_result is True

class TestProbeSchedulerFallbackStrategies:
    """Test fallback strategies and error handling methods."""

    @pytest.fixture
    def probe_scheduler(self):
        """Create a ProbeScheduler instance for testing."""
        hass = Mock()
        thermal_model = Mock()
        return ProbeScheduler(
            hass=hass,
            thermal_model=thermal_model,
            presence_entity_id="binary_sensor.home_presence",
            weather_entity_id="weather.home"
        )

    def test_get_fallback_behavior_maximum_interval_exceeded(self, probe_scheduler):
        """Test fallback behavior forces probe when maximum interval exceeded."""
        # Mock the _check_maximum_interval_exceeded to return True
        with patch.object(probe_scheduler, '_check_maximum_interval_exceeded', return_value=True):
            result = probe_scheduler._get_fallback_behavior()
            assert result is True

    def test_get_fallback_behavior_quiet_hours_block(self, probe_scheduler):
        """Test fallback behavior blocks probe during quiet hours."""
        # Mock maximum interval not exceeded but in quiet hours
        with patch.object(probe_scheduler, '_check_maximum_interval_exceeded', return_value=False), \
             patch.object(probe_scheduler, '_is_quiet_hours', return_value=True):
            result = probe_scheduler._get_fallback_behavior()
            assert result is False

    def test_get_fallback_behavior_conservative_default(self, probe_scheduler):
        """Test fallback behavior is conservative by default."""
        # Mock no maximum interval exceeded, not quiet hours
        with patch.object(probe_scheduler, '_check_maximum_interval_exceeded', return_value=False), \
             patch.object(probe_scheduler, '_is_quiet_hours', return_value=False):
            result = probe_scheduler._get_fallback_behavior()
            assert result is False

    def test_get_fallback_behavior_no_sensors_configured(self, probe_scheduler):
        """Test fallback behavior with no presence sensors configured."""
        # Create scheduler with no sensors
        hass = Mock()
        thermal_model = Mock()
        no_sensor_scheduler = ProbeScheduler(
            hass=hass,
            thermal_model=thermal_model,
            presence_entity_id=None,
            weather_entity_id=None
        )

        with patch.object(no_sensor_scheduler, '_check_maximum_interval_exceeded', return_value=False), \
             patch.object(no_sensor_scheduler, '_is_quiet_hours', return_value=False):
            result = no_sensor_scheduler._get_fallback_behavior()
            assert result is False

    def test_handle_sensor_errors_with_context(self, probe_scheduler):
        """Test error handling logs errors with context."""
        test_error = ValueError("Sensor communication failed")
        test_context = "presence_detection"

        with patch.object(probe_scheduler._logger, 'warning') as mock_warning:
            probe_scheduler._handle_sensor_errors(test_error, test_context)
            
            # Verify error was logged with context
            mock_warning.assert_called_once()
            call_args = mock_warning.call_args[0][0]
            assert "presence_detection" in call_args
            assert "Sensor communication failed" in call_args

    def test_handle_sensor_errors_different_error_types(self, probe_scheduler):
        """Test error handling works with different exception types."""
        errors_to_test = [
            (ConnectionError("Network unreachable"), "network_connection"),
            (TimeoutError("Request timeout"), "sensor_timeout"),
            (KeyError("entity_not_found"), "entity_lookup"),
            (AttributeError("state is None"), "state_access"),
        ]

        with patch.object(probe_scheduler._logger, 'warning') as mock_warning:
            for error, context in errors_to_test:
                probe_scheduler._handle_sensor_errors(error, context)

            # Verify all errors were logged
            assert mock_warning.call_count == len(errors_to_test)

    def test_handle_sensor_errors_does_not_crash_system(self, probe_scheduler):
        """Test error handling doesn't raise exceptions that would crash system."""
        test_error = RuntimeError("Critical sensor failure")
        
        # Should not raise any exception
        try:
            probe_scheduler._handle_sensor_errors(test_error, "critical_test")
        except Exception as e:
            pytest.fail(f"Error handler should not raise exceptions: {e}")

    def test_validate_configuration_minimal_valid_config(self, probe_scheduler):
        """Test configuration validation with minimal valid configuration."""
        # Mock thermal_model is available (which is required)
        result = probe_scheduler._validate_configuration()
        assert result is True

    def test_validate_configuration_with_all_sensors(self, probe_scheduler):
        """Test configuration validation with all optional sensors configured."""
        # Create scheduler with all sensors
        hass = Mock()
        thermal_model = Mock()
        full_scheduler = ProbeScheduler(
            hass=hass,
            thermal_model=thermal_model,
            presence_entity_id="binary_sensor.home_presence",
            weather_entity_id="weather.home",
            calendar_entity_id="calendar.work_schedule",
            manual_override_entity_id="input_boolean.manual_probe_override"
        )

        result = full_scheduler._validate_configuration()
        assert result is True

    def test_validate_configuration_warns_missing_optional_sensors(self, probe_scheduler):
        """Test configuration validation warns about missing optional sensors."""
        # Create scheduler with minimal config (no optional sensors)
        hass = Mock()
        thermal_model = Mock()
        minimal_scheduler = ProbeScheduler(
            hass=hass,
            thermal_model=thermal_model,
            presence_entity_id=None,
            weather_entity_id=None
        )

        with patch.object(minimal_scheduler._logger, 'warning') as mock_warning:
            result = minimal_scheduler._validate_configuration()
            
            assert result is True  # Still valid, just warns
            # Should have warned about missing optional sensors
            assert mock_warning.called

    def test_validate_configuration_entity_id_validation(self, probe_scheduler):
        """Test configuration validation checks entity ID format."""
        # Create scheduler with invalid entity IDs
        hass = Mock()
        thermal_model = Mock()
        invalid_scheduler = ProbeScheduler(
            hass=hass,
            thermal_model=thermal_model,
            presence_entity_id="invalid_entity_id",  # Missing domain
            weather_entity_id="weather.home"
        )

        with patch.object(invalid_scheduler._logger, 'error') as mock_error:
            result = invalid_scheduler._validate_configuration()
            
            # Should still return True (functional with warnings) but log error
            assert result is True
            # Should have logged error about invalid entity ID format
            mock_error.assert_called()

    def test_validate_configuration_thermal_model_available(self, probe_scheduler):
        """Test configuration validation requires thermal_model."""
        # This should always be True since thermal_model is required in constructor
        result = probe_scheduler._validate_configuration()
        assert result is True
        assert probe_scheduler._model is not None

    def test_fallback_behavior_recovery_from_error_conditions(self, probe_scheduler):
        """Test fallback behavior works after sensor errors."""
        test_error = ConnectionError("Network down")
        
        # First, handle an error
        probe_scheduler._handle_sensor_errors(test_error, "recovery_test")
        
        # Then test that fallback behavior still works
        with patch.object(probe_scheduler, '_check_maximum_interval_exceeded', return_value=False), \
             patch.object(probe_scheduler, '_is_quiet_hours', return_value=False):
            result = probe_scheduler._get_fallback_behavior()
            assert result is False  # Conservative behavior continues

    def test_graceful_degradation_pathways(self, probe_scheduler):
        """Test various graceful degradation scenarios."""
        # Test that system can function with degraded capability
        
        # Scenario 1: Presence sensor fails, but scheduler still works
        with patch.object(probe_scheduler._logger, 'warning') as mock_warning:
            probe_scheduler._handle_sensor_errors(
                ConnectionError("Presence sensor offline"), 
                "presence_detection"
            )
            
            # System should still be able to make decisions
            with patch.object(probe_scheduler, '_check_maximum_interval_exceeded', return_value=False), \
                 patch.object(probe_scheduler, '_is_quiet_hours', return_value=False):
                result = probe_scheduler._get_fallback_behavior()
                assert isinstance(result, bool)  # Should return valid decision

        # Scenario 2: Weather sensor fails, but scheduler continues
        probe_scheduler._handle_sensor_errors(
            TimeoutError("Weather service timeout"),
            "weather_data"
        )
        
        # Configuration should still be valid
        config_valid = probe_scheduler._validate_configuration()
        assert config_valid is True

    def test_error_handling_for_various_sensor_failure_types(self, probe_scheduler):
        """Test specific error handling for different sensor failure scenarios."""
        failure_scenarios = [
            # (error, context, expected_behavior)
            (ConnectionError("Network unreachable"), "network", "log_and_continue"),
            (TimeoutError("Sensor timeout"), "timeout", "log_and_continue"), 
            (ValueError("Invalid sensor data"), "data_validation", "log_and_continue"),
            (AttributeError("Sensor state is None"), "state_access", "log_and_continue"),
            (KeyError("Entity not found"), "entity_lookup", "log_and_continue"),
        ]

        with patch.object(probe_scheduler._logger, 'warning') as mock_warning:
            for error, context, expected in failure_scenarios:
                # Should not raise exception
                probe_scheduler._handle_sensor_errors(error, context)
                
                # Should continue to function normally after error
                with patch.object(probe_scheduler, '_check_maximum_interval_exceeded', return_value=False), \
                     patch.object(probe_scheduler, '_is_quiet_hours', return_value=False):
                    result = probe_scheduler._get_fallback_behavior()
                    assert isinstance(result, bool)

        # Verify all errors were logged
        assert mock_warning.call_count == len(failure_scenarios)


class TestProbeSchedulerPresenceDetection:
    """Test ProbeScheduler presence detection hierarchy methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.hass = Mock()
        self.thermal_model = Mock()
        self.presence_entity_id = "binary_sensor.presence"
        self.weather_entity_id = "weather.test"
        self.calendar_entity_id = "calendar.work"
        self.manual_override_entity_id = "input_boolean.manual_override"
        
        self.scheduler = ProbeScheduler(
            self.hass,
            self.thermal_model,
            self.presence_entity_id,
            self.weather_entity_id,
            self.calendar_entity_id,
            self.manual_override_entity_id
        )
        
    # Test _check_presence_entity method
    def test_check_presence_entity_away_returns_true(self):
        """Test presence entity returns True when away/off."""
        # Mock presence entity state as "off" (away)
        self.hass.states.get.return_value = Mock(state="off")
        
        result = self.scheduler._check_presence_entity()
        assert result is True
        self.hass.states.get.assert_called_once_with(self.presence_entity_id)
        
    def test_check_presence_entity_home_returns_false(self):
        """Test presence entity returns False when home/on."""
        # Mock presence entity state as "on" (home)
        self.hass.states.get.return_value = Mock(state="on")
        
        result = self.scheduler._check_presence_entity()
        assert result is False
        self.hass.states.get.assert_called_once_with(self.presence_entity_id)
        
    def test_check_presence_entity_unavailable_returns_none(self):
        """Test presence entity returns None when unavailable."""
        # Mock presence entity as unavailable
        self.hass.states.get.return_value = Mock(state="unavailable")
        
        result = self.scheduler._check_presence_entity()
        assert result is None
        self.hass.states.get.assert_called_once_with(self.presence_entity_id)
        
    def test_check_presence_entity_unknown_returns_none(self):
        """Test presence entity returns None when unknown."""
        # Mock presence entity as unknown
        self.hass.states.get.return_value = Mock(state="unknown")
        
        result = self.scheduler._check_presence_entity()
        assert result is None
        self.hass.states.get.assert_called_once_with(self.presence_entity_id)
        
    def test_check_presence_entity_not_found_returns_none(self):
        """Test presence entity returns None when entity not found."""
        # Mock entity as not found
        self.hass.states.get.return_value = None
        
        result = self.scheduler._check_presence_entity()
        assert result is None
        self.hass.states.get.assert_called_once_with(self.presence_entity_id)
        
    def test_check_presence_entity_no_entity_configured_returns_none(self):
        """Test presence entity returns None when no entity configured."""
        # Create scheduler without presence entity
        scheduler = ProbeScheduler(
            self.hass,
            self.thermal_model,
            None,  # No presence entity
            self.weather_entity_id
        )
        
        result = scheduler._check_presence_entity()
        assert result is None
        self.hass.states.get.assert_not_called()
        
    # Test _check_calendar_entity method
    def test_check_calendar_entity_at_work_returns_true(self):
        """Test calendar entity returns True when at work."""
        # Mock calendar entity state as "on" (busy/at work)
        self.hass.states.get.return_value = Mock(state="on")
        
        result = self.scheduler._check_calendar_entity()
        assert result is True
        self.hass.states.get.assert_called_once_with(self.calendar_entity_id)
        
    def test_check_calendar_entity_free_returns_false(self):
        """Test calendar entity returns False when free."""
        # Mock calendar entity state as "off" (free)
        self.hass.states.get.return_value = Mock(state="off")
        
        result = self.scheduler._check_calendar_entity()
        assert result is False
        self.hass.states.get.assert_called_once_with(self.calendar_entity_id)
        
    def test_check_calendar_entity_unavailable_returns_none(self):
        """Test calendar entity returns None when unavailable."""
        # Mock calendar entity as unavailable
        self.hass.states.get.return_value = Mock(state="unavailable")
        
        result = self.scheduler._check_calendar_entity()
        assert result is None
        self.hass.states.get.assert_called_once_with(self.calendar_entity_id)
        
    def test_check_calendar_entity_unknown_returns_none(self):
        """Test calendar entity returns None when unknown."""
        # Mock calendar entity as unknown
        self.hass.states.get.return_value = Mock(state="unknown")
        
        result = self.scheduler._check_calendar_entity()
        assert result is None
        self.hass.states.get.assert_called_once_with(self.calendar_entity_id)
        
    def test_check_calendar_entity_not_found_returns_none(self):
        """Test calendar entity returns None when entity not found."""
        # Mock entity as not found
        self.hass.states.get.return_value = None
        
        result = self.scheduler._check_calendar_entity()
        assert result is None
        self.hass.states.get.assert_called_once_with(self.calendar_entity_id)
        
    def test_check_calendar_entity_no_entity_configured_returns_none(self):
        """Test calendar entity returns None when no entity configured."""
        # Create scheduler without calendar entity
        scheduler = ProbeScheduler(
            self.hass,
            self.thermal_model,
            self.presence_entity_id,
            self.weather_entity_id,
            None  # No calendar entity
        )
        
        result = scheduler._check_calendar_entity()
        assert result is None
        self.hass.states.get.assert_not_called()
        
    # Test _check_manual_override method
    def test_check_manual_override_enabled_returns_true(self):
        """Test manual override returns True when enabled."""
        # Mock manual override as "on" (enabled)
        self.hass.states.get.return_value = Mock(state="on")
        
        result = self.scheduler._check_manual_override()
        assert result is True
        self.hass.states.get.assert_called_once_with(self.manual_override_entity_id)
        
    def test_check_manual_override_disabled_returns_false(self):
        """Test manual override returns False when disabled."""
        # Mock manual override as "off" (disabled)
        self.hass.states.get.return_value = Mock(state="off")
        
        result = self.scheduler._check_manual_override()
        assert result is False
        self.hass.states.get.assert_called_once_with(self.manual_override_entity_id)
        
    def test_check_manual_override_unavailable_returns_none(self):
        """Test manual override returns None when unavailable."""
        # Mock manual override as unavailable
        self.hass.states.get.return_value = Mock(state="unavailable")
        
        result = self.scheduler._check_manual_override()
        assert result is None
        self.hass.states.get.assert_called_once_with(self.manual_override_entity_id)
        
    def test_check_manual_override_unknown_returns_none(self):
        """Test manual override returns None when unknown."""
        # Mock manual override as unknown
        self.hass.states.get.return_value = Mock(state="unknown")
        
        result = self.scheduler._check_manual_override()
        assert result is None
        self.hass.states.get.assert_called_once_with(self.manual_override_entity_id)
        
    def test_check_manual_override_not_found_returns_none(self):
        """Test manual override returns None when entity not found."""
        # Mock entity as not found
        self.hass.states.get.return_value = None
        
        result = self.scheduler._check_manual_override()
        assert result is None
        self.hass.states.get.assert_called_once_with(self.manual_override_entity_id)
        
    def test_check_manual_override_no_entity_configured_returns_none(self):
        """Test manual override returns None when no entity configured."""
        # Create scheduler without manual override entity
        scheduler = ProbeScheduler(
            self.hass,
            self.thermal_model,
            self.presence_entity_id,
            self.weather_entity_id,
            self.calendar_entity_id,
            None  # No manual override entity
        )
        
        result = scheduler._check_manual_override()
        assert result is None
        self.hass.states.get.assert_not_called()
        
    # Test _is_opportune_time integration method
    def test_is_opportune_time_presence_away_returns_true(self):
        """Test opportune time returns True when presence shows away."""
        # Mock presence entity as away
        self.hass.states.get.side_effect = lambda entity_id: (
            Mock(state="off") if entity_id == self.presence_entity_id else None
        )
        
        result = self.scheduler._is_opportune_time()
        assert result is True
        
    def test_is_opportune_time_presence_home_returns_false(self):
        """Test opportune time returns False when presence shows home."""
        # Mock presence entity as home
        self.hass.states.get.side_effect = lambda entity_id: (
            Mock(state="on") if entity_id == self.presence_entity_id else None
        )
        
        result = self.scheduler._is_opportune_time()
        assert result is False
        
    def test_is_opportune_time_fallback_to_calendar_at_work(self):
        """Test fallback to calendar when presence unavailable - at work."""
        # Mock presence as unavailable, calendar as busy (at work)
        self.hass.states.get.side_effect = lambda entity_id: (
            Mock(state="unavailable") if entity_id == self.presence_entity_id 
            else Mock(state="on") if entity_id == self.calendar_entity_id
            else None
        )
        
        result = self.scheduler._is_opportune_time()
        assert result is True
        
    def test_is_opportune_time_fallback_to_calendar_free(self):
        """Test fallback to calendar when presence unavailable - free."""
        # Mock presence as unavailable, calendar as free
        self.hass.states.get.side_effect = lambda entity_id: (
            Mock(state="unavailable") if entity_id == self.presence_entity_id 
            else Mock(state="off") if entity_id == self.calendar_entity_id
            else None
        )
        
        result = self.scheduler._is_opportune_time()
        assert result is False
        
    def test_is_opportune_time_fallback_to_manual_override_enabled(self):
        """Test fallback to manual override when presence and calendar unavailable - enabled."""
        # Mock presence and calendar as unavailable, manual override as enabled
        self.hass.states.get.side_effect = lambda entity_id: (
            Mock(state="unavailable") if entity_id in [self.presence_entity_id, self.calendar_entity_id]
            else Mock(state="on") if entity_id == self.manual_override_entity_id
            else None
        )
        
        result = self.scheduler._is_opportune_time()
        assert result is True
        
    def test_is_opportune_time_fallback_to_manual_override_disabled(self):
        """Test fallback to manual override when presence and calendar unavailable - disabled."""
        # Mock presence and calendar as unavailable, manual override as disabled
        self.hass.states.get.side_effect = lambda entity_id: (
            Mock(state="unavailable") if entity_id in [self.presence_entity_id, self.calendar_entity_id]
            else Mock(state="off") if entity_id == self.manual_override_entity_id
            else None
        )
        
        result = self.scheduler._is_opportune_time()
        assert result is False
        
    def test_is_opportune_time_conservative_fallback(self):
        """Test conservative fallback when all detection methods unavailable."""
        # Mock all entities as unavailable/not found
        self.hass.states.get.return_value = None
        
        result = self.scheduler._is_opportune_time()
        assert result is False  # Conservative fallback
        
    def test_is_opportune_time_no_entities_configured(self):
        """Test opportune time with no entities configured."""
        # Create scheduler with no optional entities
        scheduler = ProbeScheduler(
            self.hass,
            self.thermal_model,
            None,  # No presence entity
            self.weather_entity_id,
            None,  # No calendar entity
            None   # No manual override entity
        )
        
        result = scheduler._is_opportune_time()
        assert result is False  # Conservative fallback
        self.hass.states.get.assert_not_called()


class TestProbeSchedulerAbortHandling:
    """Test ProbeScheduler abort condition detection and partial data handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.hass = Mock(spec=HomeAssistant)
        self.thermal_model = Mock(spec=PassiveThermalModel)
        self.presence_entity_id = "binary_sensor.presence"
        self.weather_entity_id = "weather.forecast"
        
        # Create scheduler with all entities for abort testing
        self.scheduler = ProbeScheduler(
            self.hass,
            self.thermal_model,
            self.presence_entity_id,
            self.weather_entity_id,
            calendar_entity_id="calendar.work",
            manual_override_entity_id="input_boolean.probe_override"
        )

    def test_check_abort_conditions_user_returns_home(self):
        """Test abort detection when user returns home."""
        # Mock presence entity state - user returned (away -> home)
        mock_state = Mock()
        mock_state.state = "on"  # User is now home
        self.hass.states.get.return_value = mock_state
        
        should_abort, reason = self.scheduler.check_abort_conditions()
        
        assert should_abort is True
        assert "User returned home" in reason
        self.hass.states.get.assert_called_with(self.presence_entity_id)

    def test_check_abort_conditions_presence_unavailable(self):
        """Test abort detection when presence entity unavailable."""
        # Mock presence entity unavailable
        self.hass.states.get.return_value = None
        
        should_abort, reason = self.scheduler.check_abort_conditions()
        
        # Should not abort if presence unavailable (graceful degradation)
        assert should_abort is False
        assert reason == ""

    def test_check_abort_conditions_outdoor_temp_change_large(self):
        """Test abort detection for large outdoor temperature changes."""
        # Mock presence entity away
        mock_presence = Mock()
        mock_presence.state = "off"  # User still away
        
        # Mock outdoor temperature change > 5°C
        mock_weather = Mock()
        mock_weather.attributes = {"temperature": 25.0}  # Current temp
        
        def mock_get_state(entity_id):
            if entity_id == self.presence_entity_id:
                return mock_presence
            elif entity_id == self.weather_entity_id:
                return mock_weather
            return None
            
        self.hass.states.get.side_effect = mock_get_state
        
        # Set probe start temperature (simulate large change)
        self.scheduler._probe_start_outdoor_temp = 18.0  # 7°C difference
        
        should_abort, reason = self.scheduler.check_abort_conditions()
        
        assert should_abort is True
        assert "Outdoor temperature changed 7.0°C" in reason

    def test_check_abort_conditions_outdoor_temp_change_small(self):
        """Test no abort for small outdoor temperature changes."""
        # Mock presence entity away
        mock_presence = Mock()
        mock_presence.state = "off"  # User still away
        
        # Mock outdoor temperature change < 5°C
        mock_weather = Mock()
        mock_weather.attributes = {"temperature": 21.0}  # Current temp
        
        def mock_get_state(entity_id):
            if entity_id == self.presence_entity_id:
                return mock_presence
            elif entity_id == self.weather_entity_id:
                return mock_weather
            return None
            
        self.hass.states.get.side_effect = mock_get_state
        
        # Set probe start temperature (simulate small change)
        self.scheduler._probe_start_outdoor_temp = 19.0  # 2°C difference
        
        should_abort, reason = self.scheduler.check_abort_conditions()
        
        assert should_abort is False
        assert reason == ""

    def test_check_abort_conditions_manual_climate_adjustment(self):
        """Test abort detection for manual climate adjustments."""
        # Mock presence entity away
        mock_presence = Mock()
        mock_presence.state = "off"  # User still away
        
        # Mock outdoor temperature unchanged
        mock_weather = Mock()
        mock_weather.attributes = {"temperature": 20.0}
        
        def mock_get_state(entity_id):
            if entity_id == self.presence_entity_id:
                return mock_presence
            elif entity_id == self.weather_entity_id:
                return mock_weather
            return None
            
        self.hass.states.get.side_effect = mock_get_state
        
        # Set probe start conditions
        self.scheduler._probe_start_outdoor_temp = 20.0  # No change
        self.scheduler._probe_start_target_temp = 22.0  # Original target
        
        # Simulate target temperature changed
        with patch.object(self.scheduler, '_get_current_target_temperature', return_value=25.0):
            should_abort, reason = self.scheduler.check_abort_conditions()
        
        assert should_abort is True
        assert "Manual climate adjustment detected" in reason

    def test_check_abort_conditions_hvac_fault(self):
        """Test abort detection for HVAC faults."""
        # Mock presence entity away
        mock_presence = Mock()
        mock_presence.state = "off"  # User still away
        
        # Mock outdoor temperature unchanged  
        mock_weather = Mock()
        mock_weather.attributes = {"temperature": 20.0}
        
        # Mock HVAC entity unavailable (fault condition)
        mock_hvac = Mock()
        mock_hvac.state = "unavailable"
        
        def mock_get_state(entity_id):
            if entity_id == self.presence_entity_id:
                return mock_presence
            elif entity_id == self.weather_entity_id:
                return mock_weather
            elif entity_id.startswith("climate."):
                return mock_hvac
            return None
            
        self.hass.states.get.side_effect = mock_get_state
        
        # Set probe start conditions
        self.scheduler._probe_start_outdoor_temp = 20.0  # No change
        self.scheduler._probe_start_target_temp = 22.0  # No change
        
        # Set wrapped entity ID for HVAC fault detection
        self.scheduler._wrapped_entity_id = "climate.thermostat"
        
        with patch.object(self.scheduler, '_get_current_target_temperature', return_value=22.0):
            should_abort, reason = self.scheduler.check_abort_conditions()
        
        assert should_abort is True
        assert "HVAC system fault detected" in reason

    def test_check_abort_conditions_no_triggers(self):
        """Test no abort when all conditions are normal."""
        # Mock presence entity away
        mock_presence = Mock()
        mock_presence.state = "off"  # User still away
        
        # Mock outdoor temperature unchanged
        mock_weather = Mock()
        mock_weather.attributes = {"temperature": 20.0}
        
        # Mock HVAC entity available
        mock_hvac = Mock()
        mock_hvac.state = "heat"  # Normal operation
        
        def mock_get_state(entity_id):
            if entity_id == self.presence_entity_id:
                return mock_presence
            elif entity_id == self.weather_entity_id:
                return mock_weather
            elif entity_id.startswith("climate."):
                return mock_hvac
            return None
            
        self.hass.states.get.side_effect = mock_get_state
        
        # Set probe start conditions (no changes)
        self.scheduler._probe_start_outdoor_temp = 20.0
        self.scheduler._probe_start_target_temp = 22.0
        self.scheduler._wrapped_entity_id = "climate.thermostat"
        
        with patch.object(self.scheduler, '_get_current_target_temperature', return_value=22.0):
            should_abort, reason = self.scheduler.check_abort_conditions()
        
        assert should_abort is False
        assert reason == ""

    def test_handle_partial_probe_data_duration_too_short(self):
        """Test partial data handling when duration < 15 minutes."""
        result = self.scheduler.handle_partial_probe_data(
            probe_duration_minutes=10,  # Too short
            tau_measured=90.5,
            fit_quality=0.8,
            abort_reason="User returned home"
        )
        
        assert result is None  # Should discard data

    def test_handle_partial_probe_data_duration_sufficient(self):
        """Test partial data handling when duration >= 15 minutes."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        from datetime import datetime, timezone
        
        result = self.scheduler.handle_partial_probe_data(
            probe_duration_minutes=20,  # Sufficient
            tau_measured=90.5,
            fit_quality=0.8,
            abort_reason="User returned home"
        )
        
        assert result is not None
        assert isinstance(result, ProbeResult)
        assert result.tau_value == 90.5
        assert result.confidence == 0.8 * 0.7  # 30% reduction
        assert result.duration == 20 * 60  # Convert to seconds
        assert result.fit_quality == 0.8
        assert result.aborted is True
        assert isinstance(result.timestamp, datetime)

    def test_handle_partial_probe_data_edge_case_15_minutes(self):
        """Test partial data handling exactly at 15 minute threshold."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        
        result = self.scheduler.handle_partial_probe_data(
            probe_duration_minutes=15,  # Exactly at threshold
            tau_measured=92.3,
            fit_quality=0.9,
            abort_reason="Outdoor temperature changed 6.2°C"
        )
        
        assert result is not None
        assert isinstance(result, ProbeResult)
        assert result.tau_value == 92.3
        assert result.confidence == 0.9 * 0.7  # 30% reduction
        assert result.duration == 15 * 60
        assert result.aborted is True

    def test_handle_partial_probe_data_confidence_reduction(self):
        """Test confidence reduction calculation for aborted probes."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        
        # Test various confidence levels
        test_cases = [
            (0.5, 0.35),  # 0.5 * 0.7 = 0.35
            (0.8, 0.56),  # 0.8 * 0.7 = 0.56  
            (1.0, 0.7),   # 1.0 * 0.7 = 0.7
            (0.2, 0.14),  # 0.2 * 0.7 = 0.14
        ]
        
        for original_confidence, expected_reduced in test_cases:
            result = self.scheduler.handle_partial_probe_data(
                probe_duration_minutes=20,
                tau_measured=90.0,
                fit_quality=original_confidence,
                abort_reason="Test abort"
            )
            
            assert result.confidence == pytest.approx(expected_reduced, abs=0.01)

    def test_handle_partial_probe_data_preserves_fit_quality(self):
        """Test that fit quality is preserved separately from confidence."""
        from custom_components.smart_climate.thermal_models import ProbeResult
        
        result = self.scheduler.handle_partial_probe_data(
            probe_duration_minutes=25,
            tau_measured=88.7,
            fit_quality=0.85,  # Original fit quality
            abort_reason="HVAC system fault detected"
        )
        
        # Fit quality should be preserved
        assert result.fit_quality == 0.85
        # But confidence should be reduced
        assert result.confidence == 0.85 * 0.7


class TestProbeSchedulerAdvancedSettings:
    """Test ProbeScheduler AdvancedSettings functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        from custom_components.smart_climate.probe_scheduler import AdvancedSettings, validate_advanced_settings
        self.hass = Mock()
        self.thermal_model = Mock()
        self.presence_entity_id = "binary_sensor.presence"
        self.weather_entity_id = "weather.home"
        
        # Create ProbeScheduler instance for testing apply_advanced_settings
        self.scheduler = ProbeScheduler(
            self.hass,
            self.thermal_model,
            self.presence_entity_id,
            self.weather_entity_id
        )

    def test_advanced_settings_default_values(self):
        """Test AdvancedSettings dataclass has correct default values."""
        from custom_components.smart_climate.probe_scheduler import AdvancedSettings
        
        settings = AdvancedSettings()
        
        # Test all default values from architecture specification
        assert settings.min_probe_interval_hours == 12
        assert settings.max_probe_interval_days == 7
        assert settings.quiet_hours_start == time(22, 0)
        assert settings.quiet_hours_end == time(7, 0)
        assert settings.information_gain_threshold == 0.5
        assert settings.temperature_bins == [-10, 0, 10, 20, 30]
        assert settings.presence_override_enabled == False
        assert settings.outdoor_temp_change_threshold == 5.0
        assert settings.min_probe_duration_minutes == 15

    def test_advanced_settings_custom_values(self):
        """Test AdvancedSettings dataclass with custom values."""
        from custom_components.smart_climate.probe_scheduler import AdvancedSettings
        
        settings = AdvancedSettings(
            min_probe_interval_hours=18,
            max_probe_interval_days=10,
            quiet_hours_start=time(23, 30),
            quiet_hours_end=time(6, 0),
            information_gain_threshold=0.7,
            temperature_bins=[-5, 5, 15, 25, 35],
            presence_override_enabled=True,
            outdoor_temp_change_threshold=8.0,
            min_probe_duration_minutes=30
        )
        
        assert settings.min_probe_interval_hours == 18
        assert settings.max_probe_interval_days == 10
        assert settings.quiet_hours_start == time(23, 30)
        assert settings.quiet_hours_end == time(6, 0)
        assert settings.information_gain_threshold == 0.7
        assert settings.temperature_bins == [-5, 5, 15, 25, 35]
        assert settings.presence_override_enabled == True
        assert settings.outdoor_temp_change_threshold == 8.0
        assert settings.min_probe_duration_minutes == 30

    def test_validate_advanced_settings_valid_configuration(self):
        """Test validate_advanced_settings with valid configuration."""
        from custom_components.smart_climate.probe_scheduler import AdvancedSettings, validate_advanced_settings
        
        settings = AdvancedSettings()  # Use default values (all valid)
        
        is_valid, errors = validate_advanced_settings(settings)
        
        assert is_valid is True
        assert errors == []

    def test_validate_advanced_settings_min_probe_interval_out_of_range(self):
        """Test validation fails for min_probe_interval_hours out of 6-24 range."""
        from custom_components.smart_climate.probe_scheduler import AdvancedSettings, validate_advanced_settings
        
        # Test below minimum (6 hours)
        settings = AdvancedSettings(min_probe_interval_hours=5)
        is_valid, errors = validate_advanced_settings(settings)
        assert is_valid is False
        assert "min_probe_interval_hours must be 6-24" in errors
        
        # Test above maximum (24 hours)
        settings = AdvancedSettings(min_probe_interval_hours=25)
        is_valid, errors = validate_advanced_settings(settings)
        assert is_valid is False
        assert "min_probe_interval_hours must be 6-24" in errors

    def test_validate_advanced_settings_max_probe_interval_out_of_range(self):
        """Test validation fails for max_probe_interval_days out of 3-14 range."""
        from custom_components.smart_climate.probe_scheduler import AdvancedSettings, validate_advanced_settings
        
        # Test below minimum (3 days)
        settings = AdvancedSettings(max_probe_interval_days=2)
        is_valid, errors = validate_advanced_settings(settings)
        assert is_valid is False
        assert "max_probe_interval_days must be 3-14" in errors
        
        # Test above maximum (14 days)
        settings = AdvancedSettings(max_probe_interval_days=15)
        is_valid, errors = validate_advanced_settings(settings)
        assert is_valid is False
        assert "max_probe_interval_days must be 3-14" in errors

    def test_validate_advanced_settings_information_gain_threshold_out_of_range(self):
        """Test validation fails for information_gain_threshold out of 0.1-0.9 range."""
        from custom_components.smart_climate.probe_scheduler import AdvancedSettings, validate_advanced_settings
        
        # Test below minimum (0.1)
        settings = AdvancedSettings(information_gain_threshold=0.05)
        is_valid, errors = validate_advanced_settings(settings)
        assert is_valid is False
        assert "information_gain_threshold must be 0.1-0.9" in errors
        
        # Test above maximum (0.9)
        settings = AdvancedSettings(information_gain_threshold=0.95)
        is_valid, errors = validate_advanced_settings(settings)
        assert is_valid is False
        assert "information_gain_threshold must be 0.1-0.9" in errors

    def test_validate_advanced_settings_outdoor_temp_change_threshold_out_of_range(self):
        """Test validation fails for outdoor_temp_change_threshold out of 1.0-10.0°C range."""
        from custom_components.smart_climate.probe_scheduler import AdvancedSettings, validate_advanced_settings
        
        # Test below minimum (1.0°C)
        settings = AdvancedSettings(outdoor_temp_change_threshold=0.5)
        is_valid, errors = validate_advanced_settings(settings)
        assert is_valid is False
        assert "outdoor_temp_change_threshold must be 1.0-10.0" in errors
        
        # Test above maximum (10.0°C)
        settings = AdvancedSettings(outdoor_temp_change_threshold=12.0)
        is_valid, errors = validate_advanced_settings(settings)
        assert is_valid is False
        assert "outdoor_temp_change_threshold must be 1.0-10.0" in errors

    def test_validate_advanced_settings_min_probe_duration_out_of_range(self):
        """Test validation fails for min_probe_duration_minutes out of 5-60 range."""
        from custom_components.smart_climate.probe_scheduler import AdvancedSettings, validate_advanced_settings
        
        # Test below minimum (5 minutes)
        settings = AdvancedSettings(min_probe_duration_minutes=3)
        is_valid, errors = validate_advanced_settings(settings)
        assert is_valid is False
        assert "min_probe_duration_minutes must be 5-60" in errors
        
        # Test above maximum (60 minutes)
        settings = AdvancedSettings(min_probe_duration_minutes=75)
        is_valid, errors = validate_advanced_settings(settings)
        assert is_valid is False
        assert "min_probe_duration_minutes must be 5-60" in errors

    def test_validate_advanced_settings_logical_consistency_min_max_intervals(self):
        """Test validation fails when min_probe_interval >= max_probe_interval."""
        from custom_components.smart_climate.probe_scheduler import AdvancedSettings, validate_advanced_settings
        
        # Test equal intervals (min_hours = max_hours)
        settings = AdvancedSettings(
            min_probe_interval_hours=24,  # 24 hours
            max_probe_interval_days=1     # 1 day = 24 hours  
        )
        is_valid, errors = validate_advanced_settings(settings)
        assert is_valid is False
        assert "max_probe_interval must be greater than min_probe_interval" in errors
        
        # Test min > max
        settings = AdvancedSettings(
            min_probe_interval_hours=18,  # 18 hours
            max_probe_interval_days=0.5   # 0.5 days = 12 hours
        )
        is_valid, errors = validate_advanced_settings(settings)
        assert is_valid is False
        assert "max_probe_interval must be greater than min_probe_interval" in errors

    def test_validate_advanced_settings_quiet_hours_logical_consistency(self):
        """Test validation fails when quiet_hours_start == quiet_hours_end."""
        from custom_components.smart_climate.probe_scheduler import AdvancedSettings, validate_advanced_settings
        
        settings = AdvancedSettings(
            quiet_hours_start=time(22, 0),
            quiet_hours_end=time(22, 0)  # Same as start
        )
        is_valid, errors = validate_advanced_settings(settings)
        assert is_valid is False
        assert "quiet_hours_start and quiet_hours_end must be different" in errors

    def test_validate_advanced_settings_temperature_bins_not_sorted(self):
        """Test validation fails when temperature_bins are not sorted."""
        from custom_components.smart_climate.probe_scheduler import AdvancedSettings, validate_advanced_settings
        
        settings = AdvancedSettings(
            temperature_bins=[10, -5, 0, 20, 15]  # Not sorted
        )
        is_valid, errors = validate_advanced_settings(settings)
        assert is_valid is False
        assert "temperature_bins must be sorted in ascending order" in errors

    def test_validate_advanced_settings_temperature_bins_unreasonable_range(self):
        """Test validation fails when temperature_bins have unreasonable range."""
        from custom_components.smart_climate.probe_scheduler import AdvancedSettings, validate_advanced_settings
        
        # Test extreme values
        settings = AdvancedSettings(
            temperature_bins=[-100, -50, 0, 50, 100]  # Too extreme
        )
        is_valid, errors = validate_advanced_settings(settings)
        assert is_valid is False
        assert "temperature_bins contain unreasonable values (should be -40°C to 60°C)" in errors

    def test_validate_advanced_settings_multiple_errors(self):
        """Test validation accumulates multiple errors."""
        from custom_components.smart_climate.probe_scheduler import AdvancedSettings, validate_advanced_settings
        
        settings = AdvancedSettings(
            min_probe_interval_hours=3,     # Out of range (6-24)
            max_probe_interval_days=20,     # Out of range (3-14)  
            information_gain_threshold=1.5, # Out of range (0.1-0.9)
            outdoor_temp_change_threshold=15.0,  # Out of range (1.0-10.0)
            min_probe_duration_minutes=70   # Out of range (5-60)
        )
        
        is_valid, errors = validate_advanced_settings(settings)
        assert is_valid is False
        assert len(errors) == 5
        assert "min_probe_interval_hours must be 6-24" in errors
        assert "max_probe_interval_days must be 3-14" in errors
        assert "information_gain_threshold must be 0.1-0.9" in errors
        assert "outdoor_temp_change_threshold must be 1.0-10.0" in errors
        assert "min_probe_duration_minutes must be 5-60" in errors

    def test_apply_advanced_settings_valid_configuration(self):
        """Test apply_advanced_settings updates ProbeScheduler configuration."""
        from custom_components.smart_climate.probe_scheduler import AdvancedSettings
        
        settings = AdvancedSettings(
            min_probe_interval_hours=18,
            max_probe_interval_days=10,
            quiet_hours_start=time(23, 30),
            quiet_hours_end=time(6, 0),
            information_gain_threshold=0.7,
            temperature_bins=[-5, 5, 15, 25, 35],
            presence_override_enabled=True,
            outdoor_temp_change_threshold=8.0,
            min_probe_duration_minutes=30
        )
        
        # Should not raise any exceptions
        self.scheduler.apply_advanced_settings(settings)
        
        # Verify internal configuration is updated (implementation will add these attributes)
        assert hasattr(self.scheduler, '_min_probe_interval')
        assert hasattr(self.scheduler, '_max_probe_interval')
        assert hasattr(self.scheduler, '_quiet_hours_start')
        assert hasattr(self.scheduler, '_quiet_hours_end')
        assert hasattr(self.scheduler, '_information_gain_threshold')
        assert hasattr(self.scheduler, '_temperature_bins')
        assert hasattr(self.scheduler, '_presence_override_enabled')
        assert hasattr(self.scheduler, '_outdoor_temp_change_threshold')
        assert hasattr(self.scheduler, '_min_probe_duration_minutes')

    def test_apply_advanced_settings_invalid_configuration_raises_exception(self):
        """Test apply_advanced_settings raises exception for invalid configuration."""
        from custom_components.smart_climate.probe_scheduler import AdvancedSettings
        
        settings = AdvancedSettings(
            min_probe_interval_hours=3,  # Invalid: out of range
            max_probe_interval_days=2    # Invalid: out of range
        )
        
        # Should raise ValueError with validation errors
        with pytest.raises(ValueError) as exc_info:
            self.scheduler.apply_advanced_settings(settings)
        
        error_message = str(exc_info.value)
        assert "min_probe_interval_hours must be 6-24" in error_message
        assert "max_probe_interval_days must be 3-14" in error_message

    def test_apply_advanced_settings_updates_internal_attributes(self):
        """Test apply_advanced_settings correctly updates internal ProbeScheduler attributes."""
        from custom_components.smart_climate.probe_scheduler import AdvancedSettings
        
        custom_settings = AdvancedSettings(
            min_probe_interval_hours=16,
            max_probe_interval_days=9,
            quiet_hours_start=time(23, 0),
            quiet_hours_end=time(6, 30),
            information_gain_threshold=0.8,
            temperature_bins=[-15, -5, 5, 15, 25, 40],
            presence_override_enabled=True,
            outdoor_temp_change_threshold=7.5,
            min_probe_duration_minutes=45
        )
        
        self.scheduler.apply_advanced_settings(custom_settings)
        
        # Verify all internal attributes are correctly updated
        assert self.scheduler._min_probe_interval == timedelta(hours=16)
        assert self.scheduler._max_probe_interval == timedelta(days=9)
        assert self.scheduler._quiet_hours_start == time(23, 0)
        assert self.scheduler._quiet_hours_end == time(6, 30)
        assert self.scheduler._information_gain_threshold == 0.8
        assert self.scheduler._temperature_bins == [-15, -5, 5, 15, 25, 40]
        assert self.scheduler._presence_override_enabled == True
        assert self.scheduler._outdoor_temp_change_threshold == 7.5
        assert self.scheduler._min_probe_duration_minutes == 45

    def test_apply_advanced_settings_default_values_behavior(self):
        """Test apply_advanced_settings works with default AdvancedSettings values."""
        from custom_components.smart_climate.probe_scheduler import AdvancedSettings
        
        default_settings = AdvancedSettings()  # All default values
        
        # Should not raise any exceptions
        self.scheduler.apply_advanced_settings(default_settings)
        
        # Verify defaults are applied correctly
        assert self.scheduler._min_probe_interval == timedelta(hours=12)
        assert self.scheduler._max_probe_interval == timedelta(days=7)
        assert self.scheduler._quiet_hours_start == time(22, 0)
        assert self.scheduler._quiet_hours_end == time(7, 0)
        assert self.scheduler._information_gain_threshold == 0.5
        assert self.scheduler._temperature_bins == [-10, 0, 10, 20, 30]
        assert self.scheduler._presence_override_enabled == False
        assert self.scheduler._outdoor_temp_change_threshold == 5.0
        assert self.scheduler._min_probe_duration_minutes == 15

    def test_temperature_bins_factory_function(self):
        """Test that temperature_bins default_factory works correctly."""
        from custom_components.smart_climate.probe_scheduler import AdvancedSettings
        
        # Create multiple instances to verify factory function creates separate lists
        settings1 = AdvancedSettings()
        settings2 = AdvancedSettings()
        
        # Modify one instance
        settings1.temperature_bins.append(40)
        
        # Verify they are separate objects
        assert settings1.temperature_bins == [-10, 0, 10, 20, 30, 40]
        assert settings2.temperature_bins == [-10, 0, 10, 20, 30]
        assert settings1.temperature_bins is not settings2.temperature_bins

    def test_advanced_settings_edge_case_values(self):
        """Test AdvancedSettings with edge case values at boundaries."""
        from custom_components.smart_climate.probe_scheduler import AdvancedSettings, validate_advanced_settings
        
        # Test boundary values that should be valid
        settings = AdvancedSettings(
            min_probe_interval_hours=6,   # Minimum valid
            max_probe_interval_days=14,   # Maximum valid
            information_gain_threshold=0.1,  # Minimum valid
            outdoor_temp_change_threshold=1.0,  # Minimum valid
            min_probe_duration_minutes=5  # Minimum valid
        )
        
        is_valid, errors = validate_advanced_settings(settings)
        assert is_valid is True
        assert errors == []
        
        # Test other boundary
        settings = AdvancedSettings(
            min_probe_interval_hours=24,  # Maximum valid
            max_probe_interval_days=3,    # Minimum valid (but will fail logical consistency)
            information_gain_threshold=0.9,  # Maximum valid
            outdoor_temp_change_threshold=10.0,  # Maximum valid
            min_probe_duration_minutes=60  # Maximum valid
        )
        
        is_valid, errors = validate_advanced_settings(settings)
        # This should fail logical consistency (24 hours = 1 day, but max is 3 days, so it's valid)
        # Wait, 24 hours < 3*24 hours, so it should be valid
        assert is_valid is True
        assert errors == []


class TestProbeSchedulerLearningProfiles:
    """Test ProbeScheduler learning profile configuration system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.hass = Mock()
        self.thermal_model = Mock()
        self.presence_entity_id = "binary_sensor.presence"
        self.weather_entity_id = "weather.test"
        
    def test_default_profile_is_balanced(self):
        """Test that default profile is BALANCED when none specified."""
        
        scheduler = ProbeScheduler(
            self.hass,
            self.thermal_model,
            self.presence_entity_id,
            self.weather_entity_id
        )
        
        assert scheduler._learning_profile == LearningProfile.BALANCED
        
    def test_comfort_profile_configuration(self):
        """Test comfort profile has correct parameters."""
        
        scheduler = ProbeScheduler(
            self.hass,
            self.thermal_model,
            self.presence_entity_id,
            self.weather_entity_id,
            learning_profile=LearningProfile.COMFORT
        )
        
        config = scheduler._profile_config
        assert isinstance(config, ProfileConfig)
        assert config.min_probe_interval_hours == 24
        assert config.max_probe_interval_days == 7
        assert config.presence_required == True
        assert config.information_gain_threshold == 0.6
        assert config.quiet_hours_enabled == True
        assert config.outdoor_temp_bins == [-10, 0, 10, 20, 30]
        
    def test_balanced_profile_configuration(self):
        """Test balanced profile has correct parameters."""
        
        scheduler = ProbeScheduler(
            self.hass,
            self.thermal_model,
            self.presence_entity_id,
            self.weather_entity_id,
            learning_profile=LearningProfile.BALANCED
        )
        
        config = scheduler._profile_config
        assert isinstance(config, ProfileConfig)
        assert config.min_probe_interval_hours == 12
        assert config.max_probe_interval_days == 7
        assert config.presence_required == True
        assert config.information_gain_threshold == 0.5
        assert config.quiet_hours_enabled == True
        assert config.outdoor_temp_bins == [-10, 0, 10, 20, 30]
        
    def test_aggressive_profile_configuration(self):
        """Test aggressive profile has correct parameters."""
        
        scheduler = ProbeScheduler(
            self.hass,
            self.thermal_model,
            self.presence_entity_id,
            self.weather_entity_id,
            learning_profile=LearningProfile.AGGRESSIVE
        )
        
        config = scheduler._profile_config
        assert isinstance(config, ProfileConfig)
        assert config.min_probe_interval_hours == 6
        assert config.max_probe_interval_days == 3
        assert config.presence_required == False
        assert config.information_gain_threshold == 0.3
        assert config.quiet_hours_enabled == True
        assert config.outdoor_temp_bins == [-15, -5, 5, 15, 25, 35]
        
    def test_custom_profile_configuration(self):
        """Test custom profile allows user-configurable parameters."""
        
        scheduler = ProbeScheduler(
            self.hass,
            self.thermal_model,
            self.presence_entity_id,
            self.weather_entity_id,
            learning_profile=LearningProfile.CUSTOM
        )
        
        config = scheduler._profile_config
        assert isinstance(config, ProfileConfig)
        # Custom profile should have default values but be user-configurable
        # These are base defaults that can be overridden
        assert config.min_probe_interval_hours >= 6
        assert config.max_probe_interval_days >= 3
        assert isinstance(config.presence_required, bool)
        assert 0.1 <= config.information_gain_threshold <= 1.0
        assert isinstance(config.quiet_hours_enabled, bool)
        assert isinstance(config.outdoor_temp_bins, list)
        
    def test_profile_switching(self):
        """Test switching between profiles updates configuration."""
        
        scheduler = ProbeScheduler(
            self.hass,
            self.thermal_model,
            self.presence_entity_id,
            self.weather_entity_id,
            learning_profile=LearningProfile.BALANCED
        )
        
        # Initially balanced
        assert scheduler._learning_profile == LearningProfile.BALANCED
        assert scheduler._profile_config.min_probe_interval_hours == 12
        
        # Switch to aggressive
        scheduler._update_profile(LearningProfile.AGGRESSIVE)
        assert scheduler._learning_profile == LearningProfile.AGGRESSIVE
        assert scheduler._profile_config.min_probe_interval_hours == 6
        assert scheduler._profile_config.max_probe_interval_days == 3
        assert scheduler._profile_config.presence_required == False
        
        # Switch to comfort
        scheduler._update_profile(LearningProfile.COMFORT)
        assert scheduler._learning_profile == LearningProfile.COMFORT
        assert scheduler._profile_config.min_probe_interval_hours == 24
        assert scheduler._profile_config.presence_required == True
        
    def test_profile_validation(self):
        """Test profile configuration validation."""
        
        scheduler = ProbeScheduler(
            self.hass,
            self.thermal_model,
            self.presence_entity_id,
            self.weather_entity_id,
            learning_profile=LearningProfile.COMFORT
        )
        
        # Validate that profile config is properly initialized
        config = scheduler._profile_config
        assert config.min_probe_interval_hours > 0
        assert config.max_probe_interval_days > 0
        assert config.min_probe_interval_hours <= config.max_probe_interval_days * 24
        assert 0.0 <= config.information_gain_threshold <= 1.0
        assert len(config.outdoor_temp_bins) >= 3  # Minimum meaningful bins
        
    def test_all_profile_enum_values(self):
        """Test that all LearningProfile enum values work."""
        
        for profile in LearningProfile:
            scheduler = ProbeScheduler(
                self.hass,
                self.thermal_model,
                self.presence_entity_id,
                self.weather_entity_id,
                learning_profile=profile
            )
            
            # Should initialize without error
            assert scheduler._learning_profile == profile
            assert scheduler._profile_config is not None
            
    def test_profile_config_immutability(self):
        """Test that ProfileConfig is properly immutable after creation."""
        
        scheduler = ProbeScheduler(
            self.hass,
            self.thermal_model,
            self.presence_entity_id,
            self.weather_entity_id,
            learning_profile=LearningProfile.BALANCED
        )
        
        original_config = scheduler._profile_config
        
        # Switching profiles should create new config, not modify existing
        scheduler._update_profile(LearningProfile.AGGRESSIVE)
        
        # Original config should be unchanged
        assert original_config.min_probe_interval_hours == 12
        # New config should be different
        assert scheduler._profile_config.min_probe_interval_hours == 6
        assert scheduler._profile_config is not original_config
