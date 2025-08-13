"""Tests for HumidityAggregator class."""
import pytest
from datetime import datetime

# Import the class we're testing - this will fail initially (TDD)
from custom_components.smart_climate.humidity_monitor import HumidityAggregator


class TestHumidityAggregator:
    """Test cases for HumidityAggregator statistics calculator."""
    
    def test_calculate_daily_stats_returns_empty_dict_for_empty_events(self):
        """Test that empty event list returns empty dict."""
        aggregator = HumidityAggregator()
        result = aggregator.calculate_daily_stats([])
        assert result == {}
        
    def test_calculate_daily_stats_returns_empty_dict_for_none(self):
        """Test that None input returns empty dict."""
        aggregator = HumidityAggregator()
        result = aggregator.calculate_daily_stats(None)
        assert result == {}
        
    def test_calculate_daily_stats_basic_indoor_outdoor_stats(self):
        """Test basic min/max/avg calculation for indoor and outdoor humidity."""
        aggregator = HumidityAggregator()
        events = [
            {"indoor": 40.0, "outdoor": 60.0},
            {"indoor": 50.0, "outdoor": 70.0},
            {"indoor": 45.0, "outdoor": 65.0},
        ]
        
        result = aggregator.calculate_daily_stats(events)
        
        # Check structure
        assert "indoor" in result
        assert "outdoor" in result
        assert "ml_impact" in result
        assert "comfort_time_percent" in result
        
        # Check indoor stats
        assert result["indoor"]["min"] == 40.0
        assert result["indoor"]["max"] == 50.0
        assert result["indoor"]["avg"] == 45.0  # (40+50+45)/3
        
        # Check outdoor stats
        assert result["outdoor"]["min"] == 60.0
        assert result["outdoor"]["max"] == 70.0
        assert result["outdoor"]["avg"] == 65.0  # (60+70+65)/3
        
    def test_calculate_daily_stats_missing_indoor_values(self):
        """Test handling of events missing indoor humidity."""
        aggregator = HumidityAggregator()
        events = [
            {"indoor": 40.0, "outdoor": 60.0},
            {"outdoor": 70.0},  # Missing indoor
            {"indoor": 50.0, "outdoor": 65.0},
        ]
        
        result = aggregator.calculate_daily_stats(events)
        
        # Indoor stats should only include events with indoor data
        assert result["indoor"]["min"] == 40.0
        assert result["indoor"]["max"] == 50.0
        assert result["indoor"]["avg"] == 45.0  # (40+50)/2
        
        # Outdoor stats should include all events with outdoor data
        assert result["outdoor"]["avg"] == 65.0  # (60+70+65)/3
        
    def test_calculate_daily_stats_missing_outdoor_values(self):
        """Test handling of events missing outdoor humidity."""
        aggregator = HumidityAggregator()
        events = [
            {"indoor": 40.0, "outdoor": 60.0},
            {"indoor": 45.0},  # Missing outdoor
            {"indoor": 50.0, "outdoor": 70.0},
        ]
        
        result = aggregator.calculate_daily_stats(events)
        
        # Indoor stats should include all events with indoor data
        assert result["indoor"]["avg"] == 45.0  # (40+45+50)/3
        
        # Outdoor stats should only include events with outdoor data
        assert result["outdoor"]["avg"] == 65.0  # (60+70)/2
        
    def test_calculate_daily_stats_single_event(self):
        """Test stats calculation with only one event."""
        aggregator = HumidityAggregator()
        events = [{"indoor": 42.5, "outdoor": 68.5}]
        
        result = aggregator.calculate_daily_stats(events)
        
        assert result["indoor"]["min"] == 42.5
        assert result["indoor"]["max"] == 42.5
        assert result["indoor"]["avg"] == 42.5
        
        assert result["outdoor"]["min"] == 68.5
        assert result["outdoor"]["max"] == 68.5
        assert result["outdoor"]["avg"] == 68.5
        
    def test_calculate_ml_averages_helper_method(self):
        """Test that _calculate_ml_averages helper method is called."""
        aggregator = HumidityAggregator()
        
        # Mock the helper method to verify it's called
        def mock_ml_averages(events):
            return {"avg_offset": 0.25, "avg_confidence": -2}
            
        aggregator._calculate_ml_averages = mock_ml_averages
        
        events = [{"indoor": 45.0, "outdoor": 65.0}]
        result = aggregator.calculate_daily_stats(events)
        
        assert result["ml_impact"]["avg_offset"] == 0.25
        assert result["ml_impact"]["avg_confidence"] == -2
        
    def test_calculate_comfort_percentage_helper_method(self):
        """Test that _calculate_comfort_percentage helper method is called."""
        aggregator = HumidityAggregator()
        
        # Mock the helper method to verify it's called
        def mock_comfort_percentage(events):
            return 78
            
        aggregator._calculate_comfort_percentage = mock_comfort_percentage
        
        events = [{"indoor": 45.0, "outdoor": 65.0}]
        result = aggregator.calculate_daily_stats(events)
        
        assert result["comfort_time_percent"] == 78
        
    def test_calculate_ml_averages_implementation(self):
        """Test _calculate_ml_averages implementation with sample data."""
        aggregator = HumidityAggregator()
        events = [
            {"ml_offset_impact": 0.1, "ml_confidence_impact": -1},
            {"ml_offset_impact": 0.3, "ml_confidence_impact": -3},
            {"ml_offset_impact": 0.2, "ml_confidence_impact": -2},
        ]
        
        result = aggregator._calculate_ml_averages(events)
        
        assert abs(result["avg_offset"] - 0.2) < 0.000001  # (0.1+0.3+0.2)/3
        assert result["avg_confidence"] == -2  # (-1-3-2)/3
        
    def test_calculate_ml_averages_missing_data(self):
        """Test _calculate_ml_averages with missing ML impact data."""
        aggregator = HumidityAggregator()
        events = [
            {"ml_offset_impact": 0.1, "ml_confidence_impact": -1},
            {"indoor": 45.0},  # Missing ML data
            {"ml_offset_impact": 0.3, "ml_confidence_impact": -3},
        ]
        
        result = aggregator._calculate_ml_averages(events)
        
        # Should average only events with ML data
        assert result["avg_offset"] == 0.2  # (0.1+0.3)/2
        assert result["avg_confidence"] == -2  # (-1-3)/2
        
    def test_calculate_ml_averages_no_ml_data(self):
        """Test _calculate_ml_averages with no ML impact data."""
        aggregator = HumidityAggregator()
        events = [
            {"indoor": 45.0, "outdoor": 65.0},
            {"indoor": 50.0, "outdoor": 70.0},
        ]
        
        result = aggregator._calculate_ml_averages(events)
        
        # Should return zeros when no ML data available
        assert result["avg_offset"] == 0.0
        assert result["avg_confidence"] == 0.0
        
    def test_calculate_comfort_percentage_implementation(self):
        """Test _calculate_comfort_percentage implementation."""
        aggregator = HumidityAggregator()
        
        # Mock events with comfort zone indicators (30-60% indoor humidity)
        events = [
            {"indoor": 25.0, "comfort_zone": False},  # Too low
            {"indoor": 45.0, "comfort_zone": True},   # In comfort zone
            {"indoor": 50.0, "comfort_zone": True},   # In comfort zone  
            {"indoor": 65.0, "comfort_zone": False},  # Too high
        ]
        
        result = aggregator._calculate_comfort_percentage(events)
        
        # 2 out of 4 events in comfort zone = 50%
        assert result == 50.0
        
    def test_calculate_comfort_percentage_no_events(self):
        """Test _calculate_comfort_percentage with no events."""
        aggregator = HumidityAggregator()
        result = aggregator._calculate_comfort_percentage([])
        assert result == 0.0
        
    def test_calculate_comfort_percentage_missing_comfort_data(self):
        """Test _calculate_comfort_percentage with missing comfort zone data."""
        aggregator = HumidityAggregator()
        events = [
            {"indoor": 45.0},  # Missing comfort_zone indicator
            {"indoor": 50.0},  # Missing comfort_zone indicator
        ]
        
        # Should calculate comfort zone from indoor humidity (30-60% range)
        result = aggregator._calculate_comfort_percentage(events)
        
        # Both 45% and 50% are in comfort zone
        assert result == 100.0
        
    def test_floating_point_precision_in_averages(self):
        """Test that averages handle floating point precision correctly."""
        aggregator = HumidityAggregator()
        events = [
            {"indoor": 33.333333, "outdoor": 66.666666},
            {"indoor": 33.333333, "outdoor": 66.666667},
            {"indoor": 33.333334, "outdoor": 66.666667},
        ]
        
        result = aggregator.calculate_daily_stats(events)
        
        # Should handle precision gracefully
        assert abs(result["indoor"]["avg"] - 33.333333) < 0.000001
        assert abs(result["outdoor"]["avg"] - 66.666667) < 0.000001
        
    def test_return_percentages_as_0_100_values(self):
        """Test that comfort percentages are returned as 0-100 values."""
        aggregator = HumidityAggregator()
        
        # Mock comfort calculation to return fraction
        def mock_comfort_percentage(events):
            return 0.75 * 100  # Convert fraction to percentage
            
        aggregator._calculate_comfort_percentage = mock_comfort_percentage
        
        events = [{"indoor": 45.0, "outdoor": 65.0}]
        result = aggregator.calculate_daily_stats(events)
        
        # Should be 75, not 0.75
        assert result["comfort_time_percent"] == 75