"""Tests for extended dashboard data functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from datetime import datetime
import time

from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.dto import (
    DashboardData,
    SeasonalData,
    DelayData,
    ACBehaviorData,
    PerformanceData,
    SystemHealthData,
    DiagnosticsData,
    API_VERSION
)


class TestDashboardDataDTO:
    """Test the dashboard data DTOs."""
    
    def test_dashboard_data_to_dict(self):
        """Test converting DashboardData to dictionary."""
        data = DashboardData(
            calculated_offset=2.5,
            learning_info={"enabled": True, "samples": 50},
            save_diagnostics={"save_count": 10},
            calibration_info={"in_calibration": False}
        )
        
        result = data.to_dict()
        
        assert result["api_version"] == API_VERSION
        assert result["calculated_offset"] == 2.5
        assert result["learning_info"]["enabled"] is True
        assert result["seasonal_data"]["enabled"] is False  # Default value
        assert "delay_data" in result
        assert "ac_behavior" in result
        assert "performance" in result
        assert "system_health" in result
        assert "diagnostics" in result
    
    def test_dashboard_data_with_all_fields(self):
        """Test DashboardData with all fields populated."""
        data = DashboardData(
            calculated_offset=1.5,
            learning_info={"enabled": True},
            save_diagnostics={"save_count": 5},
            calibration_info={"in_calibration": True},
            seasonal_data=SeasonalData(
                enabled=True,
                contribution=25.5,
                pattern_count=100,
                outdoor_temp_bucket="20-25°C",
                accuracy=85.0
            ),
            delay_data=DelayData(
                adaptive_delay=45.0,
                temperature_stability_detected=True,
                learned_delay_seconds=60.0
            ),
            ac_behavior=ACBehaviorData(
                temperature_window="±0.5°C",
                power_correlation_accuracy=92.0,
                hysteresis_cycle_count=50
            ),
            performance=PerformanceData(
                ema_coefficient=0.8,
                prediction_latency_ms=1.5,
                energy_efficiency_score=85,
                sensor_availability_score=100.0
            ),
            system_health=SystemHealthData(
                memory_usage_kb=1024.5,
                persistence_latency_ms=5.2,
                outlier_detection_active=True,
                samples_per_day=288.0,
                accuracy_improvement_rate=2.5,
                convergence_trend="improving"
            ),
            diagnostics=DiagnosticsData(
                last_update_duration_ms=15.3,
                cache_hit_rate=0.85,
                cached_keys=12
            )
        )
        
        result = data.to_dict()
        
        # Check nested structures
        assert result["seasonal_data"]["enabled"] is True
        assert result["seasonal_data"]["contribution"] == 25.5
        assert result["delay_data"]["adaptive_delay"] == 45.0
        assert result["ac_behavior"]["temperature_window"] == "±0.5°C"
        assert result["performance"]["energy_efficiency_score"] == 85
        assert result["system_health"]["convergence_trend"] == "improving"
        assert result["diagnostics"]["cache_hit_rate"] == 0.85


class TestOffsetEngineExtendedDashboard:
    """Test the extended dashboard data functionality in OffsetEngine."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return {
            "max_offset": 5.0,
            "ml_enabled": True,
            "enable_learning": True,
            "power_sensor": "sensor.power",
            "save_interval": 300
        }
    
    @pytest.fixture
    def mock_delay_learner(self):
        """Create mock DelayLearner."""
        learner = Mock()
        learner.get_adaptive_delay.return_value = 45
        learner.is_temperature_stable.return_value = True
        learner.get_learned_delay.return_value = 60
        return learner
    
    @pytest.fixture
    def mock_seasonal_learner(self):
        """Create mock SeasonalLearner."""
        learner = Mock()
        learner.get_seasonal_contribution.return_value = 30.0
        learner.get_pattern_count.return_value = 150
        learner.get_outdoor_temp_bucket.return_value = "25-30°C"
        learner.get_accuracy.return_value = 88.5
        return learner
    
    @pytest.fixture
    def engine_with_mocks(self, config, mock_delay_learner, mock_seasonal_learner):
        """Create OffsetEngine with mocked components."""
        engine = OffsetEngine(config, seasonal_learner=mock_seasonal_learner)
        engine._delay_learner = mock_delay_learner
        engine._seasonal_learner = mock_seasonal_learner
        return engine
    
    @pytest.mark.asyncio
    async def test_async_get_dashboard_data_backward_compatibility(self, engine_with_mocks):
        """Test that existing fields remain at root level for backward compatibility."""
        # Set up some test state
        engine_with_mocks._last_offset = 2.5
        engine_with_mocks._save_count = 10
        engine_with_mocks._failed_save_count = 2
        engine_with_mocks._last_save_time = datetime.now()
        engine_with_mocks._stable_calibration_offset = 1.5
        
        result = await engine_with_mocks.async_get_dashboard_data()
        
        # Check backward compatibility fields at root
        assert "calculated_offset" in result
        assert "learning_info" in result
        assert "save_diagnostics" in result
        assert "calibration_info" in result
        
        # These should be at root level, not nested
        assert result["calculated_offset"] == 2.5
        assert isinstance(result["learning_info"], dict)
        assert result["save_diagnostics"]["save_count"] == 10
        assert result["calibration_info"]["cached_offset"] == 1.5
    
    @pytest.mark.asyncio
    async def test_async_get_dashboard_data_new_fields(self, engine_with_mocks):
        """Test that new v1.3.0 fields are included."""
        result = await engine_with_mocks.async_get_dashboard_data()
        
        # Check for new structured fields
        assert "api_version" in result
        assert result["api_version"] == API_VERSION
        
        assert "seasonal_data" in result
        assert "delay_data" in result
        assert "ac_behavior" in result
        assert "performance" in result
        assert "system_health" in result
        assert "diagnostics" in result
    
    @pytest.mark.asyncio
    async def test_seasonal_data_when_enabled(self, engine_with_mocks):
        """Test seasonal data when seasonal learner is available."""
        result = await engine_with_mocks.async_get_dashboard_data()
        
        seasonal = result["seasonal_data"]
        assert seasonal["enabled"] is True
        assert seasonal["contribution"] == 30.0
        assert seasonal["pattern_count"] == 150
        assert seasonal["outdoor_temp_bucket"] == "25-30°C"
        assert seasonal["accuracy"] == 88.5
    
    @pytest.mark.asyncio
    async def test_seasonal_data_when_disabled(self, config):
        """Test seasonal data when seasonal learner is not available."""
        engine = OffsetEngine(config, seasonal_learner=None)
        
        result = await engine.async_get_dashboard_data()
        
        seasonal = result["seasonal_data"]
        assert seasonal["enabled"] is False
        assert seasonal["contribution"] == 0.0
        assert seasonal["pattern_count"] == 0
        assert seasonal["outdoor_temp_bucket"] is None
        assert seasonal["accuracy"] == 0.0
    
    @pytest.mark.asyncio
    async def test_delay_data_when_available(self, engine_with_mocks):
        """Test delay data when delay learner is available."""
        result = await engine_with_mocks.async_get_dashboard_data()
        
        delay = result["delay_data"]
        assert delay["adaptive_delay"] == 45.0
        assert delay["temperature_stability_detected"] is True
        assert delay["learned_delay_seconds"] == 60.0
    
    @pytest.mark.asyncio
    async def test_delay_data_when_unavailable(self, config, mock_seasonal_learner):
        """Test delay data when delay learner is not available."""
        engine = OffsetEngine(config, seasonal_learner=mock_seasonal_learner)
        engine._delay_learner = None
        
        result = await engine.async_get_dashboard_data()
        
        delay = result["delay_data"]
        assert delay["adaptive_delay"] == 0.0
        assert delay["temperature_stability_detected"] is False
        assert delay["learned_delay_seconds"] == 0.0
    
    @pytest.mark.asyncio
    async def test_ac_behavior_data(self, engine_with_mocks):
        """Test AC behavior data calculation."""
        # Mock the internal methods
        engine_with_mocks._get_temperature_window = Mock(return_value="±0.8°C")
        engine_with_mocks._calculate_power_correlation = Mock(return_value=95.0)
        engine_with_mocks._get_hysteresis_cycle_count = Mock(return_value=75)
        
        result = await engine_with_mocks.async_get_dashboard_data()
        
        ac_behavior = result["ac_behavior"]
        assert ac_behavior["temperature_window"] == "±0.8°C"
        assert ac_behavior["power_correlation_accuracy"] == 95.0
        assert ac_behavior["hysteresis_cycle_count"] == 75
    
    @pytest.mark.asyncio
    async def test_performance_data_caching(self, engine_with_mocks):
        """Test that performance data is cached appropriately."""
        # Mock the compute methods
        engine_with_mocks._get_ema_coefficient = Mock(return_value=0.85)
        engine_with_mocks._measure_prediction_latency = Mock(return_value=2.1)
        engine_with_mocks._calculate_energy_efficiency_score = Mock(return_value=90)
        engine_with_mocks._calculate_sensor_availability = Mock(return_value=75.0)
        
        # First call
        result1 = await engine_with_mocks.async_get_dashboard_data()
        
        # Second call (should use cache)
        result2 = await engine_with_mocks.async_get_dashboard_data()
        
        # Performance methods should only be called once due to caching
        assert engine_with_mocks._get_ema_coefficient.call_count == 1
        assert engine_with_mocks._measure_prediction_latency.call_count == 1
        
        # Results should be the same
        assert result1["performance"] == result2["performance"]
    
    @pytest.mark.asyncio
    async def test_system_health_data_with_mixed_caching(self, engine_with_mocks):
        """Test system health data with different cache durations."""
        # Mock the compute methods
        engine_with_mocks._calculate_memory_usage_kb = Mock(return_value=2048.5)
        engine_with_mocks._data_store = Mock()
        engine_with_mocks._data_store.get_last_write_latency = Mock(return_value=8.5)
        engine_with_mocks._is_outlier_detection_active = Mock(return_value=True)
        engine_with_mocks._calculate_samples_per_day = Mock(return_value=144.0)
        engine_with_mocks._calculate_accuracy_improvement_rate = Mock(return_value=3.2)
        engine_with_mocks._analyze_convergence_trend = Mock(return_value="stable")
        
        result = await engine_with_mocks.async_get_dashboard_data()
        
        health = result["system_health"]
        assert health["memory_usage_kb"] == 2048.5
        assert health["persistence_latency_ms"] == 8.5
        assert health["outlier_detection_active"] is True
        assert health["samples_per_day"] == 144.0
        assert health["accuracy_improvement_rate"] == 3.2
        assert health["convergence_trend"] == "stable"
    
    @pytest.mark.asyncio
    async def test_diagnostics_data_timing(self, engine_with_mocks):
        """Test diagnostics data includes timing information."""
        # Mock internal methods to speed up test
        engine_with_mocks._get_seasonal_data = Mock(return_value=SeasonalData())
        engine_with_mocks._get_delay_data = Mock(return_value=DelayData())
        engine_with_mocks._get_ac_behavior_data = Mock(return_value=ACBehaviorData())
        engine_with_mocks._compute_performance_data = Mock(return_value=PerformanceData())
        engine_with_mocks._compute_system_health_data = Mock(return_value=SystemHealthData())
        
        result = await engine_with_mocks.async_get_dashboard_data()
        
        diagnostics = result["diagnostics"]
        assert "last_update_duration_ms" in diagnostics
        assert diagnostics["last_update_duration_ms"] > 0
        assert "cache_hit_rate" in diagnostics
        assert "cached_keys" in diagnostics
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, engine_with_mocks):
        """Test cache invalidation functionality."""
        # Set up some cached data
        engine_with_mocks._dashboard_cache = {
            "performance": {"data": {"test": "value"}, "timestamp": time.monotonic()},
            "memory_usage": {"data": 1024, "timestamp": time.monotonic()}
        }
        
        # Invalidate specific key
        engine_with_mocks.invalidate_cache_key("performance")
        
        assert "performance" not in engine_with_mocks._dashboard_cache
        assert "memory_usage" in engine_with_mocks._dashboard_cache
    
    @pytest.mark.asyncio
    async def test_error_handling_in_seasonal_data(self, engine_with_mocks):
        """Test graceful error handling when seasonal data fails."""
        # Make seasonal learner raise an exception
        engine_with_mocks._seasonal_learner.get_seasonal_contribution.side_effect = Exception("Test error")
        
        result = await engine_with_mocks.async_get_dashboard_data()
        
        # Should return default SeasonalData
        seasonal = result["seasonal_data"]
        assert seasonal["enabled"] is False
        assert seasonal["contribution"] == 0.0
    
    @pytest.mark.asyncio
    async def test_error_handling_in_delay_data(self, engine_with_mocks):
        """Test graceful error handling when delay data fails."""
        # Make delay learner raise an exception
        engine_with_mocks._delay_learner.get_adaptive_delay.side_effect = Exception("Test error")
        
        result = await engine_with_mocks.async_get_dashboard_data()
        
        # Should return default DelayData
        delay = result["delay_data"]
        assert delay["adaptive_delay"] == 0.0
        assert delay["temperature_stability_detected"] is False
    
    @pytest.mark.asyncio
    async def test_cache_hit_rate_calculation(self, engine_with_mocks):
        """Test cache hit rate calculation in diagnostics."""
        # Reset cache statistics
        engine_with_mocks._cache_hits = 0
        engine_with_mocks._cache_misses = 0
        
        # First call - all cache misses
        result1 = await engine_with_mocks.async_get_dashboard_data()
        diagnostics1 = result1["diagnostics"]
        
        # Should have some cache misses from first call
        assert diagnostics1["cache_hit_rate"] == 0.0  # All misses on first call
        
        # Second call - should have some hits
        result2 = await engine_with_mocks.async_get_dashboard_data()
        diagnostics2 = result2["diagnostics"]
        
        # Cache hit rate should be > 0 on second call
        assert diagnostics2["cache_hit_rate"] > 0.0
        assert diagnostics2["cache_hit_rate"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self, engine_with_mocks):
        """Test that cache expires after configured duration."""
        # Mock a cacheable method
        mock_func = Mock(return_value=123.45)
        
        # First call - should compute
        result1 = engine_with_mocks._get_cached_or_recompute("test_key", mock_func, 1, default_value=0)
        assert result1 == 123.45
        assert mock_func.call_count == 1
        
        # Second call immediately - should use cache
        result2 = engine_with_mocks._get_cached_or_recompute("test_key", mock_func, 1, default_value=0)
        assert result2 == 123.45
        assert mock_func.call_count == 1  # Not called again
        
        # Wait for cache to expire
        time.sleep(1.1)
        
        # Third call - should recompute
        mock_func.return_value = 678.90
        result3 = engine_with_mocks._get_cached_or_recompute("test_key", mock_func, 1, default_value=0)
        assert result3 == 678.90
        assert mock_func.call_count == 2
    
    @pytest.mark.asyncio
    async def test_complete_dashboard_data_structure(self, engine_with_mocks):
        """Test the complete dashboard data structure matches specification."""
        # Set up all internal methods
        engine_with_mocks._get_temperature_window = Mock(return_value="±0.5°C")
        engine_with_mocks._calculate_power_correlation = Mock(return_value=88.5)
        engine_with_mocks._get_hysteresis_cycle_count = Mock(return_value=42)
        engine_with_mocks._get_ema_coefficient = Mock(return_value=0.75)
        engine_with_mocks._measure_prediction_latency = Mock(return_value=1.8)
        engine_with_mocks._calculate_energy_efficiency_score = Mock(return_value=82)
        engine_with_mocks._calculate_sensor_availability = Mock(return_value=100.0)
        engine_with_mocks._calculate_memory_usage_kb = Mock(return_value=1536.8)
        engine_with_mocks._data_store = Mock()
        engine_with_mocks._data_store.get_last_write_latency = Mock(return_value=4.2)
        engine_with_mocks._is_outlier_detection_active = Mock(return_value=False)
        engine_with_mocks._calculate_samples_per_day = Mock(return_value=192.0)
        engine_with_mocks._calculate_accuracy_improvement_rate = Mock(return_value=1.8)
        engine_with_mocks._analyze_convergence_trend = Mock(return_value="improving")
        
        result = await engine_with_mocks.async_get_dashboard_data()
        
        # Verify all top-level fields exist
        expected_fields = [
            "api_version",
            "calculated_offset",
            "learning_info",
            "save_diagnostics",
            "calibration_info",
            "seasonal_data",
            "delay_data",
            "ac_behavior",
            "performance",
            "system_health",
            "diagnostics",
            "weather_forecast",
            "predictive_offset"
        ]
        
        for field in expected_fields:
            assert field in result, f"Missing expected field: {field}"
        
        # Verify nested structure matches DTOs
        assert isinstance(result["seasonal_data"], dict)
        assert isinstance(result["delay_data"], dict)
        assert isinstance(result["ac_behavior"], dict)
        assert isinstance(result["performance"], dict)
        assert isinstance(result["system_health"], dict)
        assert isinstance(result["diagnostics"], dict)
    
    @pytest.mark.asyncio
    async def test_forecast_engine_wiring_via_set_method(self, config):
        """Test that set_forecast_engine method properly wires the ForecastEngine."""
        # Create OffsetEngine without ForecastEngine
        engine = OffsetEngine(config)
        assert engine._forecast_engine is None
        
        # Get initial dashboard data
        result1 = await engine.async_get_dashboard_data()
        assert result1["weather_forecast"] is False
        assert result1["predictive_offset"] == 0.0
        
        # Create and wire a ForecastEngine
        mock_forecast_engine = Mock()
        mock_forecast_engine.predictive_offset = 2.7
        engine.set_forecast_engine(mock_forecast_engine)
        
        # Verify it's wired
        assert engine._forecast_engine is mock_forecast_engine
        
        # Get dashboard data after wiring
        result2 = await engine.async_get_dashboard_data()
        assert result2["weather_forecast"] is True
        assert result2["predictive_offset"] == 2.7
    
    @pytest.mark.asyncio
    async def test_weather_forecast_field_when_forecast_engine_exists(self, engine_with_mocks):
        """Test weather_forecast field is True when ForecastEngine exists."""
        # Mock ForecastEngine
        mock_forecast_engine = Mock()
        mock_forecast_engine.predictive_offset = 2.5
        engine_with_mocks._forecast_engine = mock_forecast_engine
        
        result = await engine_with_mocks.async_get_dashboard_data()
        
        assert "weather_forecast" in result
        assert result["weather_forecast"] is True
    
    @pytest.mark.asyncio
    async def test_weather_forecast_field_when_no_forecast_engine(self, config):
        """Test weather_forecast field is False when no ForecastEngine."""
        engine = OffsetEngine(config)
        engine._forecast_engine = None
        
        result = await engine.async_get_dashboard_data()
        
        assert "weather_forecast" in result
        assert result["weather_forecast"] is False
    
    @pytest.mark.asyncio
    async def test_predictive_offset_field_with_forecast_engine(self, engine_with_mocks):
        """Test predictive_offset field returns value from ForecastEngine."""
        # Mock ForecastEngine with predictive offset
        mock_forecast_engine = Mock()
        mock_forecast_engine.predictive_offset = 3.5
        engine_with_mocks._forecast_engine = mock_forecast_engine
        
        result = await engine_with_mocks.async_get_dashboard_data()
        
        assert "predictive_offset" in result
        assert result["predictive_offset"] == 3.5
    
    @pytest.mark.asyncio
    async def test_predictive_offset_field_without_forecast_engine(self, config):
        """Test predictive_offset field returns 0.0 when no ForecastEngine."""
        engine = OffsetEngine(config)
        engine._forecast_engine = None
        
        result = await engine.async_get_dashboard_data()
        
        assert "predictive_offset" in result
        assert result["predictive_offset"] == 0.0
    
    @pytest.mark.asyncio
    async def test_predictive_offset_handles_forecast_engine_errors(self, engine_with_mocks):
        """Test predictive_offset gracefully handles ForecastEngine errors."""
        # Mock ForecastEngine that raises exception when accessing predictive_offset
        mock_forecast_engine = Mock()
        # Use PropertyMock to mock a property that raises an exception
        type(mock_forecast_engine).predictive_offset = PropertyMock(side_effect=Exception("ForecastEngine error"))
        engine_with_mocks._forecast_engine = mock_forecast_engine
        
        # Capture the warning log
        with patch("custom_components.smart_climate.offset_engine._LOGGER") as mock_logger:
            result = await engine_with_mocks.async_get_dashboard_data()
        
        # Should handle error gracefully
        assert "weather_forecast" in result
        assert result["weather_forecast"] is True  # Engine exists
        assert "predictive_offset" in result
        assert result["predictive_offset"] == 0.0  # But returns default on error
        
        # Verify warning was logged
        mock_logger.warning.assert_called_once()
        args = mock_logger.warning.call_args[0]
        assert "Failed to get predictive offset from ForecastEngine" in args[0]