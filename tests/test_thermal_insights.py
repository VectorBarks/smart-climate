"""Tests for ThermalInsightsEngine component - Step 3.4 Smart Insights Engine."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any

from custom_components.smart_climate.thermal_insights import ThermalInsightsEngine


class TestThermalInsightsEngine:
    """Test suite for ThermalInsightsEngine class."""
    
    @pytest.fixture
    def hass(self):
        """Home Assistant fixture."""
        return Mock()
    
    @pytest.fixture 
    def mock_cycle_monitor(self):
        """Mock CycleMonitor fixture."""
        monitor = Mock()
        monitor.get_average_cycle_duration.return_value = (450.0, 650.0)  # 7.5 min on, 10.8 min off
        monitor.needs_adjustment.return_value = False
        return monitor
    
    @pytest.fixture
    def mock_thermal_manager(self):
        """Mock ThermalManager fixture."""
        manager = Mock()
        manager.current_state.value = "drifting"
        return manager
    
    @pytest.fixture
    def insights_engine(self, hass, mock_cycle_monitor, mock_thermal_manager):
        """ThermalInsightsEngine fixture."""
        return ThermalInsightsEngine(hass, mock_cycle_monitor, mock_thermal_manager)
    
    def test_init_creates_engine_with_components(self, hass, mock_cycle_monitor, mock_thermal_manager):
        """Test ThermalInsightsEngine initialization with required components."""
        engine = ThermalInsightsEngine(hass, mock_cycle_monitor, mock_thermal_manager)
        
        assert engine._hass == hass
        assert engine._cycle_monitor == mock_cycle_monitor
        assert engine._thermal_manager == mock_thermal_manager
        assert isinstance(engine._historical_data, list)
        assert engine._last_update is None
    
    def test_calculate_runtime_saved_no_baseline_data(self, insights_engine):
        """Test runtime saved calculation with no baseline data returns 0."""
        result = insights_engine.calculate_runtime_saved(period_hours=24)
        assert result == 0.0
    
    def test_calculate_runtime_saved_with_baseline_data(self, insights_engine):
        """Test runtime saved calculation with baseline comparison data."""
        # Mock baseline runtime of 8 hours/day, actual runtime of 6.2 hours
        baseline_runtime = 8.0 * 3600  # 8 hours in seconds
        actual_runtime = 6.2 * 3600    # 6.2 hours in seconds
        
        with patch.object(insights_engine, '_get_baseline_runtime', return_value=baseline_runtime):
            with patch.object(insights_engine, '_get_actual_runtime', return_value=actual_runtime):
                result = insights_engine.calculate_runtime_saved(period_hours=24)
                
                expected_hours_saved = (baseline_runtime - actual_runtime) / 3600
                assert result == expected_hours_saved
                assert result == pytest.approx(1.8)  # 8.0 - 6.2 = 1.8 hours
    
    def test_calculate_runtime_saved_negative_savings(self, insights_engine):
        """Test runtime saved returns 0 when actual runtime exceeds baseline."""
        baseline_runtime = 6.0 * 3600  # 6 hours
        actual_runtime = 7.5 * 3600    # 7.5 hours - worse than baseline
        
        with patch.object(insights_engine, '_get_baseline_runtime', return_value=baseline_runtime):
            with patch.object(insights_engine, '_get_actual_runtime', return_value=actual_runtime):
                result = insights_engine.calculate_runtime_saved(period_hours=24)
                
                assert result == 0.0  # No savings reported when worse than baseline
    
    def test_calculate_cycles_reduced_no_baseline_data(self, insights_engine):
        """Test cycles reduced calculation with no baseline data returns 0."""
        result = insights_engine.calculate_cycles_reduced(period_hours=24)
        assert result == 0
    
    def test_calculate_cycles_reduced_with_baseline_data(self, insights_engine):
        """Test cycles reduced calculation with baseline comparison data."""
        baseline_cycles = 35  # cycles per day without thermal efficiency
        actual_cycles = 22    # cycles per day with thermal efficiency
        
        with patch.object(insights_engine, '_get_baseline_cycles', return_value=baseline_cycles):
            with patch.object(insights_engine, '_get_actual_cycles', return_value=actual_cycles):
                result = insights_engine.calculate_cycles_reduced(period_hours=24)
                
                expected_reduction = baseline_cycles - actual_cycles
                assert result == expected_reduction
                assert result == 13  # 35 - 22 = 13 cycles reduced
    
    def test_calculate_cycles_reduced_negative_reduction(self, insights_engine):
        """Test cycles reduced returns 0 when actual cycles exceed baseline."""
        baseline_cycles = 20
        actual_cycles = 28  # More cycles than baseline
        
        with patch.object(insights_engine, '_get_baseline_cycles', return_value=baseline_cycles):
            with patch.object(insights_engine, '_get_actual_cycles', return_value=actual_cycles):
                result = insights_engine.calculate_cycles_reduced(period_hours=24)
                
                assert result == 0  # No reduction reported when worse than baseline
    
    def test_detect_patterns_insufficient_history(self, insights_engine):
        """Test pattern detection with insufficient historical data."""
        result = insights_engine.detect_patterns(history_days=7)
        assert result == []
    
    def test_detect_patterns_best_efficiency_times(self, insights_engine):
        """Test pattern detection identifies best efficiency times of day."""
        # Mock historical data showing better efficiency in morning hours
        # Use absolute datetimes to ensure hour values are correct
        base_date = datetime(2024, 1, 1)  # Use fixed date to ensure consistent hours
        mock_history = [
            {"timestamp": base_date.replace(day=1, hour=8), "efficiency": 0.25},  # 8 AM
            {"timestamp": base_date.replace(day=1, hour=14), "efficiency": 0.15},  # 2 PM
            {"timestamp": base_date.replace(day=1, hour=20), "efficiency": 0.18},  # 8 PM
            {"timestamp": base_date.replace(day=2, hour=8), "efficiency": 0.26},   # 8 AM
            {"timestamp": base_date.replace(day=2, hour=9), "efficiency": 0.28},   # 9 AM
            {"timestamp": base_date.replace(day=2, hour=15), "efficiency": 0.12},  # 3 PM
            {"timestamp": base_date.replace(day=3, hour=8), "efficiency": 0.24},   # 8 AM
        ]
        
        # Set mock historical data on the engine
        insights_engine._mock_historical_data = mock_history
        patterns = insights_engine.detect_patterns(history_days=7)
        
        assert len(patterns) > 0
        # Should detect morning hours as best efficiency pattern
        morning_pattern = next((p for p in patterns if "morning" in p.get("description", "").lower()), None)
        assert morning_pattern is not None
        assert morning_pattern["type"] == "efficiency_window"
    
    def test_detect_patterns_degradation_trend(self, insights_engine):
        """Test pattern detection identifies thermal response degradation."""
        # Mock historical data showing degrading response times
        mock_history = [
            {"timestamp": datetime.now() - timedelta(days=1), "response_time": 12.5},
            {"timestamp": datetime.now() - timedelta(days=2), "response_time": 11.8},
            {"timestamp": datetime.now() - timedelta(days=3), "response_time": 11.2},
            {"timestamp": datetime.now() - timedelta(days=4), "response_time": 10.5},
            {"timestamp": datetime.now() - timedelta(days=5), "response_time": 10.1},
        ]
        
        with patch.object(insights_engine, '_get_historical_data', return_value=mock_history):
            patterns = insights_engine.detect_patterns(history_days=7)
            
            degradation_pattern = next((p for p in patterns if p.get("type") == "degradation"), None)
            assert degradation_pattern is not None
            assert "slower" in degradation_pattern.get("description", "").lower()
    
    def test_generate_recommendations_runtime_savings(self, insights_engine):
        """Test recommendation generation for runtime savings."""
        with patch.object(insights_engine, 'calculate_runtime_saved', return_value=3.2):
            recommendations = insights_engine.generate_recommendations()
            
            assert len(recommendations) > 0
            runtime_rec = next((r for r in recommendations if "3.2 hours" in r), None)
            assert runtime_rec is not None
            assert "%" in runtime_rec  # Should show percentage (exact value may vary)
    
    def test_generate_recommendations_cycle_reduction(self, insights_engine):
        """Test recommendation generation for cycle count reduction."""
        with patch.object(insights_engine, 'calculate_cycles_reduced', return_value=18):
            recommendations = insights_engine.generate_recommendations()
            
            cycle_rec = next((r for r in recommendations if "18 fewer cycles" in r), None)
            assert cycle_rec is not None
    
    def test_generate_recommendations_comfort_band_suggestion(self, insights_engine):
        """Test recommendation generation suggests comfort band adjustment."""
        # Mock data showing potential for more savings with wider comfort band
        with patch.object(insights_engine, '_analyze_comfort_potential', return_value=0.15):
            recommendations = insights_engine.generate_recommendations()
            
            comfort_rec = next((r for r in recommendations if "comfort band" in r.lower()), None)
            assert comfort_rec is not None
            assert "15%" in comfort_rec  # Should show potential additional savings
    
    def test_generate_recommendations_thermal_response_issue(self, insights_engine):
        """Test recommendation generation identifies thermal response issues."""
        mock_patterns = [
            {"type": "degradation", "description": "Thermal response 15% slower in evenings", "severity": "medium"}
        ]
        
        with patch.object(insights_engine, 'detect_patterns', return_value=mock_patterns):
            recommendations = insights_engine.generate_recommendations()
            
            thermal_rec = next((r for r in recommendations if "thermal response" in r.lower()), None)
            assert thermal_rec is not None
            assert "check for heat sources" in thermal_rec.lower()
    
    def test_get_aggregated_metrics_daily(self, insights_engine):
        """Test aggregated metrics calculation for daily period."""
        with patch.object(insights_engine, 'calculate_runtime_saved', return_value=2.5):
            with patch.object(insights_engine, 'calculate_cycles_reduced', return_value=12):
                with patch.object(insights_engine, '_calculate_energy_cost_savings', return_value=1.85):
                    
                    metrics = insights_engine.get_aggregated_metrics(period="daily")
                    
                    assert metrics["runtime_saved_hours"] == 2.5
                    assert metrics["cycles_reduced"] == 12
                    assert metrics["energy_cost_savings"] == 1.85
                    assert metrics["period"] == "daily"
    
    def test_get_aggregated_metrics_weekly(self, insights_engine):
        """Test aggregated metrics calculation for weekly period."""
        with patch.object(insights_engine, 'calculate_runtime_saved', return_value=18.2):
            with patch.object(insights_engine, 'calculate_cycles_reduced', return_value=85):
                metrics = insights_engine.get_aggregated_metrics(period="weekly")
                
                assert metrics["runtime_saved_hours"] == 18.2
                assert metrics["cycles_reduced"] == 85
                assert metrics["period"] == "weekly"
    
    def test_get_aggregated_metrics_monthly(self, insights_engine):
        """Test aggregated metrics calculation for monthly period."""
        with patch.object(insights_engine, 'calculate_runtime_saved', return_value=75.6):
            metrics = insights_engine.get_aggregated_metrics(period="monthly")
            
            assert metrics["period"] == "monthly"
            assert metrics["runtime_saved_hours"] == 75.6
    
    def test_rank_insights_by_priority(self, insights_engine):
        """Test insight ranking by priority and impact."""
        mock_insights = [
            {"type": "savings", "impact": "low", "description": "Minor optimization"},
            {"type": "savings", "impact": "high", "description": "Major runtime reduction"},
            {"type": "issue", "impact": "medium", "description": "Thermal response degradation"},
            {"type": "savings", "impact": "medium", "description": "Moderate cycle reduction"}
        ]
        
        ranked = insights_engine.rank_insights(mock_insights)
        
        assert len(ranked) == 4
        # High impact should be first
        assert ranked[0]["impact"] == "high"
        # Issues should be prioritized over savings of same impact
        assert ranked[1]["type"] == "issue"
        assert ranked[1]["impact"] == "medium"
    
    def test_rank_insights_empty_list(self, insights_engine):
        """Test insight ranking with empty input list."""
        result = insights_engine.rank_insights([])
        assert result == []
    
    def test_energy_cost_calculation(self, insights_engine):
        """Test energy cost savings calculation."""
        runtime_saved_hours = 3.5
        power_consumption_kw = 2.8
        electricity_rate_per_kwh = 0.12
        
        with patch.object(insights_engine, '_get_power_consumption', return_value=power_consumption_kw):
            with patch.object(insights_engine, '_get_electricity_rate', return_value=electricity_rate_per_kwh):
                cost_savings = insights_engine._calculate_energy_cost_savings(runtime_saved_hours)
                
                expected = runtime_saved_hours * power_consumption_kw * electricity_rate_per_kwh
                assert cost_savings == pytest.approx(expected)
                assert cost_savings == pytest.approx(1.176)  # 3.5 * 2.8 * 0.12
    
    def test_seasonal_variation_pattern_detection(self, insights_engine):
        """Test detection of seasonal performance variations."""
        # Mock data showing seasonal efficiency differences
        mock_history = []
        base_time = datetime.now() - timedelta(days=30)
        for day in range(30):
            # Create clearer temperature groups for better pattern detection
            if day < 10:
                outdoor_temp = 32.0  # Hot days
                efficiency = 0.15
            elif day < 20:
                outdoor_temp = 28.0  # Moderate days 
                efficiency = 0.18
            else:
                outdoor_temp = 22.0  # Cool days
                efficiency = 0.25  # Much better efficiency
            
            mock_history.append({
                "timestamp": base_time + timedelta(days=day),
                "efficiency": efficiency,
                "outdoor_temp": outdoor_temp
            })
        
        # Set mock historical data on the engine
        insights_engine._mock_historical_data = mock_history
        patterns = insights_engine.detect_patterns(history_days=30)
        
        seasonal_pattern = next((p for p in patterns if p.get("type") == "seasonal"), None)
        assert seasonal_pattern is not None
        assert "outdoor" in seasonal_pattern.get("description", "").lower()
    
    def test_user_behavior_pattern_detection(self, insights_engine):
        """Test detection of user behavior patterns."""
        # Mock data showing weekday vs weekend differences
        mock_history = []
        base_time = datetime.now() - timedelta(days=14)
        for day in range(14):
            current_day = base_time + timedelta(days=day)
            is_weekday = current_day.weekday() < 5
            
            # Simulate different patterns for weekday vs weekend
            efficiency = 0.22 if is_weekday else 0.18
            mock_history.append({
                "timestamp": current_day,
                "efficiency": efficiency,
                "is_weekday": is_weekday
            })
        
        with patch.object(insights_engine, '_get_historical_data', return_value=mock_history):
            patterns = insights_engine.detect_patterns(history_days=14)
            
            behavior_pattern = next((p for p in patterns if p.get("type") == "behavior"), None)
            assert behavior_pattern is not None
            assert "weekday" in behavior_pattern.get("description", "").lower()