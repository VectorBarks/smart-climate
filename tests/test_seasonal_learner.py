"""Tests for Seasonal Learning Infrastructure components.

ABOUTME: Comprehensive test suite for LearnedPattern dataclass and SeasonalHysteresisLearner class.
Tests outdoor temperature bucket matching, pattern persistence, and graceful degradation scenarios.
"""

import pytest
import asyncio
import statistics
import time as time_module
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Optional, Dict, Any

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.storage import Store

from custom_components.smart_climate.seasonal_learner import (
    LearnedPattern,
    SeasonalHysteresisLearner
)


class TestLearnedPattern:
    """Test suite for LearnedPattern dataclass."""

    def test_learned_pattern_creation(self):
        """Test LearnedPattern creation with all required fields."""
        pattern = LearnedPattern(
            timestamp=1234567890.0,
            start_temp=25.0,
            stop_temp=23.5,
            outdoor_temp=30.0
        )
        
        assert pattern.timestamp == 1234567890.0
        assert pattern.start_temp == 25.0
        assert pattern.stop_temp == 23.5
        assert pattern.outdoor_temp == 30.0

    def test_hysteresis_delta_property(self):
        """Test hysteresis_delta property calculation."""
        pattern = LearnedPattern(
            timestamp=1234567890.0,
            start_temp=25.0,
            stop_temp=22.0,
            outdoor_temp=30.0
        )
        
        assert pattern.hysteresis_delta == 3.0

    def test_hysteresis_delta_zero(self):
        """Test hysteresis_delta when start and stop temps are equal."""
        pattern = LearnedPattern(
            timestamp=1234567890.0,
            start_temp=24.0,
            stop_temp=24.0,
            outdoor_temp=25.0
        )
        
        assert pattern.hysteresis_delta == 0.0

    def test_hysteresis_delta_negative(self):
        """Test hysteresis_delta when stop temp is higher than start (edge case)."""
        pattern = LearnedPattern(
            timestamp=1234567890.0,
            start_temp=22.0,
            stop_temp=24.0,
            outdoor_temp=20.0
        )
        
        assert pattern.hysteresis_delta == -2.0

    def test_learned_pattern_field_types(self):
        """Test LearnedPattern field types are correct."""
        pattern = LearnedPattern(
            timestamp=1234567890.0,
            start_temp=25.5,
            stop_temp=23.2,
            outdoor_temp=28.7
        )
        
        assert isinstance(pattern.timestamp, float)
        assert isinstance(pattern.start_temp, float)
        assert isinstance(pattern.stop_temp, float)
        assert isinstance(pattern.outdoor_temp, float)


class TestSeasonalHysteresisLearner:
    """Test suite for SeasonalHysteresisLearner class."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = Mock()
        hass.states = Mock()
        return hass

    @pytest.fixture
    def mock_store(self):
        """Create a mock Store instance."""
        store = Mock()
        store.async_load = AsyncMock(return_value=None)
        store.async_save = AsyncMock()
        return store

    @pytest.fixture
    def learner(self, mock_hass, mock_store):
        """Create a SeasonalHysteresisLearner instance for testing."""
        with patch('custom_components.smart_climate.seasonal_learner.Store', return_value=mock_store):
            return SeasonalHysteresisLearner(mock_hass, "sensor.outdoor_temperature")

    @pytest.fixture
    def learner_no_outdoor(self, mock_hass, mock_store):
        """Create a SeasonalHysteresisLearner instance without outdoor sensor."""
        with patch('custom_components.smart_climate.seasonal_learner.Store', return_value=mock_store):
            return SeasonalHysteresisLearner(mock_hass, None)

    def test_initialization_with_outdoor_sensor(self, mock_hass, mock_store):
        """Test SeasonalHysteresisLearner initialization with outdoor sensor."""
        with patch('custom_components.smart_climate.seasonal_learner.Store', return_value=mock_store):
            learner = SeasonalHysteresisLearner(mock_hass, "sensor.outdoor_temperature")
        
        assert learner._hass == mock_hass
        assert learner._outdoor_sensor_id == "sensor.outdoor_temperature"
        assert learner._patterns == []
        assert learner._data_retention_days == 45
        assert learner._outdoor_temp_bucket_size == 5.0
        assert learner._min_samples_for_bucket == 3

    def test_initialization_without_outdoor_sensor(self, mock_hass, mock_store):
        """Test SeasonalHysteresisLearner initialization without outdoor sensor."""
        with patch('custom_components.smart_climate.seasonal_learner.Store', return_value=mock_store):
            learner = SeasonalHysteresisLearner(mock_hass, None)
        
        assert learner._hass == mock_hass
        assert learner._outdoor_sensor_id is None
        assert learner._patterns == []

    def test_get_current_outdoor_temp_with_sensor(self, learner, mock_hass):
        """Test _get_current_outdoor_temp with valid outdoor sensor."""
        # Mock valid state
        mock_state = Mock()
        mock_state.state = "25.5"
        mock_hass.states.get.return_value = mock_state
        
        result = learner._get_current_outdoor_temp()
        
        assert result == 25.5
        mock_hass.states.get.assert_called_once_with("sensor.outdoor_temperature")

    def test_get_current_outdoor_temp_invalid_state(self, learner, mock_hass):
        """Test _get_current_outdoor_temp with invalid state value."""
        # Mock invalid state
        mock_state = Mock()
        mock_state.state = "unavailable"
        mock_hass.states.get.return_value = mock_state
        
        result = learner._get_current_outdoor_temp()
        
        assert result is None

    def test_get_current_outdoor_temp_no_sensor(self, learner_no_outdoor):
        """Test _get_current_outdoor_temp without outdoor sensor."""
        result = learner_no_outdoor._get_current_outdoor_temp()
        
        assert result is None

    def test_get_current_outdoor_temp_no_state(self, learner, mock_hass):
        """Test _get_current_outdoor_temp when state doesn't exist."""
        mock_hass.states.get.return_value = None
        
        result = learner._get_current_outdoor_temp()
        
        assert result is None

    def test_learn_new_cycle_with_outdoor_temp(self, learner, mock_hass):
        """Test learn_new_cycle with outdoor temperature available."""
        # Mock outdoor temperature
        mock_state = Mock()
        mock_state.state = "30.0"
        mock_hass.states.get.return_value = mock_state
        
        with patch('time.time', return_value=1234567890.0):
            learner.learn_new_cycle(25.0, 22.0)
        
        assert len(learner._patterns) == 1
        pattern = learner._patterns[0]
        assert pattern.timestamp == 1234567890.0
        assert pattern.start_temp == 25.0
        assert pattern.stop_temp == 22.0
        assert pattern.outdoor_temp == 30.0

    def test_learn_new_cycle_without_outdoor_temp(self, learner, mock_hass):
        """Test learn_new_cycle without outdoor temperature available."""
        # Mock no outdoor temperature available
        mock_hass.states.get.return_value = None
        
        with patch('time.time', return_value=1234567890.0):
            learner.learn_new_cycle(25.0, 22.0)
        
        # Should not create pattern without outdoor temp
        assert len(learner._patterns) == 0

    def test_find_patterns_by_outdoor_temp_exact_match(self, learner):
        """Test _find_patterns_by_outdoor_temp with exact temperature match."""
        # Add test patterns
        learner._patterns = [
            LearnedPattern(123.0, 25.0, 22.0, 30.0),
            LearnedPattern(124.0, 24.0, 21.0, 30.0),
            LearnedPattern(125.0, 26.0, 23.0, 20.0),
        ]
        
        patterns = learner._find_patterns_by_outdoor_temp(30.0, 0.5)
        
        assert len(patterns) == 2
        assert all(p.outdoor_temp == 30.0 for p in patterns)

    def test_find_patterns_by_outdoor_temp_tolerance_match(self, learner):
        """Test _find_patterns_by_outdoor_temp with tolerance matching."""
        # Add test patterns
        learner._patterns = [
            LearnedPattern(123.0, 25.0, 22.0, 30.0),
            LearnedPattern(124.0, 24.0, 21.0, 32.0),  # Within 2.5 tolerance
            LearnedPattern(125.0, 26.0, 23.0, 35.5),  # Outside tolerance
        ]
        
        patterns = learner._find_patterns_by_outdoor_temp(30.0, 2.5)
        
        assert len(patterns) == 2
        outdoor_temps = [p.outdoor_temp for p in patterns]
        assert 30.0 in outdoor_temps
        assert 32.0 in outdoor_temps
        assert 35.5 not in outdoor_temps

    def test_find_patterns_by_outdoor_temp_no_matches(self, learner):
        """Test _find_patterns_by_outdoor_temp with no matches."""
        # Add test patterns far from target
        learner._patterns = [
            LearnedPattern(123.0, 25.0, 22.0, 10.0),
            LearnedPattern(124.0, 24.0, 21.0, 50.0),
        ]
        
        patterns = learner._find_patterns_by_outdoor_temp(30.0, 2.5)
        
        assert len(patterns) == 0

    def test_get_relevant_hysteresis_delta_with_current_temp(self, learner, mock_hass):
        """Test get_relevant_hysteresis_delta with current outdoor temperature."""
        # Mock current outdoor temperature
        mock_state = Mock()
        mock_state.state = "25.0"
        mock_hass.states.get.return_value = mock_state
        
        # Add patterns in bucket range
        learner._patterns = [
            LearnedPattern(123.0, 25.0, 22.0, 24.0),  # delta = 3.0
            LearnedPattern(124.0, 24.0, 20.0, 26.0),  # delta = 4.0
            LearnedPattern(125.0, 23.0, 19.0, 25.5),  # delta = 4.0
        ]
        
        result = learner.get_relevant_hysteresis_delta()
        
        # Should return median of deltas: [3.0, 4.0, 4.0] -> 4.0
        assert result == 4.0

    def test_get_relevant_hysteresis_delta_with_provided_temp(self, learner):
        """Test get_relevant_hysteresis_delta with provided outdoor temperature."""
        # Add patterns in bucket range  
        learner._patterns = [
            LearnedPattern(123.0, 25.0, 23.0, 24.0),  # delta = 2.0
            LearnedPattern(124.0, 24.0, 21.0, 26.0),  # delta = 3.0
            LearnedPattern(125.0, 23.0, 20.0, 25.5),  # delta = 3.0
        ]
        
        result = learner.get_relevant_hysteresis_delta(current_outdoor_temp=25.0)
        
        # Should return median of deltas: [2.0, 3.0, 3.0] -> 3.0
        assert result == 3.0

    def test_get_relevant_hysteresis_delta_insufficient_bucket_data(self, learner, mock_hass):
        """Test get_relevant_hysteresis_delta with insufficient data in bucket."""
        # Mock current outdoor temperature
        mock_state = Mock()
        mock_state.state = "25.0"
        mock_hass.states.get.return_value = mock_state
        
        # Add only 2 patterns in bucket (less than min_samples_for_bucket=3)
        learner._patterns = [
            LearnedPattern(123.0, 25.0, 22.0, 24.0),  # delta = 3.0
            LearnedPattern(124.0, 24.0, 20.0, 26.0),  # delta = 4.0
            LearnedPattern(125.0, 23.0, 18.0, 35.0),  # delta = 5.0, outside bucket
        ]
        
        result = learner.get_relevant_hysteresis_delta()
        
        # Should fall back to using all patterns: [3.0, 4.0, 5.0] -> 4.0
        assert result == 4.0

    def test_get_relevant_hysteresis_delta_no_patterns(self, learner):
        """Test get_relevant_hysteresis_delta with no patterns available."""
        result = learner.get_relevant_hysteresis_delta(current_outdoor_temp=25.0)
        
        assert result is None

    def test_get_relevant_hysteresis_delta_fallback_tolerance(self, learner, mock_hass):
        """Test get_relevant_hysteresis_delta fallback to wider tolerance."""
        # Mock current outdoor temperature
        mock_state = Mock()
        mock_state.state = "25.0"
        mock_hass.states.get.return_value = mock_state
        
        # Add patterns outside initial tolerance but within fallback
        learner._patterns = [
            LearnedPattern(123.0, 25.0, 22.0, 20.0),  # delta = 3.0, outside 2.5°C
            LearnedPattern(124.0, 24.0, 20.0, 21.0),  # delta = 4.0, outside 2.5°C
            LearnedPattern(125.0, 23.0, 19.0, 30.0),  # delta = 4.0, within 5°C
            LearnedPattern(126.0, 22.0, 18.0, 31.0),  # delta = 4.0, outside 5°C
        ]
        
        result = learner.get_relevant_hysteresis_delta()
        
        # Should use fallback tolerance (5°C) and find one pattern: [4.0] -> 4.0
        assert result == 4.0

    def test_prune_old_patterns(self, learner):
        """Test _prune_old_patterns removes patterns older than retention period."""
        current_time = time_module.time()
        old_time = current_time - (learner._data_retention_days * 24 * 3600 + 1000)  # Older than retention
        recent_time = current_time - 1000  # Recent
        
        # Add mix of old and recent patterns
        learner._patterns = [
            LearnedPattern(old_time, 25.0, 22.0, 30.0),      # Should be removed
            LearnedPattern(recent_time, 24.0, 21.0, 28.0),   # Should remain
            LearnedPattern(current_time, 23.0, 20.0, 26.0),  # Should remain
        ]
        
        learner._prune_old_patterns()
        
        assert len(learner._patterns) == 2
        timestamps = [p.timestamp for p in learner._patterns]
        assert old_time not in timestamps
        assert recent_time in timestamps
        assert current_time in timestamps

    def test_prune_old_patterns_no_old_patterns(self, learner):
        """Test _prune_old_patterns when no patterns are old."""
        current_time = time_module.time()
        recent_time = current_time - 1000  # Recent
        
        # Add only recent patterns
        learner._patterns = [
            LearnedPattern(recent_time, 24.0, 21.0, 28.0),
            LearnedPattern(current_time, 23.0, 20.0, 26.0),
        ]
        
        original_count = len(learner._patterns)
        learner._prune_old_patterns()
        
        assert len(learner._patterns) == original_count

    @pytest.mark.asyncio
    async def test_async_load_success(self, learner, mock_store):
        """Test successful async_load from storage."""
        # Use a current timestamp to avoid pruning
        current_time = time_module.time()
        
        # Mock stored data
        stored_data = {
            "patterns": [
                {
                    "timestamp": current_time,
                    "start_temp": 25.0,
                    "stop_temp": 22.0,
                    "outdoor_temp": 30.0
                }
            ]
        }
        mock_store.async_load.return_value = stored_data
        
        await learner.async_load()
        
        assert len(learner._patterns) == 1
        pattern = learner._patterns[0]
        assert pattern.timestamp == current_time
        assert pattern.start_temp == 25.0
        assert pattern.stop_temp == 22.0
        assert pattern.outdoor_temp == 30.0

    @pytest.mark.asyncio
    async def test_async_load_no_data(self, learner, mock_store):
        """Test async_load when no data exists."""
        mock_store.async_load.return_value = None
        
        await learner.async_load()
        
        assert len(learner._patterns) == 0

    @pytest.mark.asyncio
    async def test_async_load_invalid_data(self, learner, mock_store):
        """Test async_load with invalid data structure."""
        mock_store.async_load.return_value = {"invalid": "data"}
        
        await learner.async_load()
        
        assert len(learner._patterns) == 0

    @pytest.mark.asyncio
    async def test_async_load_with_pruning(self, learner, mock_store):
        """Test async_load that triggers pruning of old patterns."""
        current_time = time_module.time()
        old_time = current_time - (learner._data_retention_days * 24 * 3600 + 1000)
        
        # Mock stored data with old patterns
        stored_data = {
            "patterns": [
                {
                    "timestamp": old_time,
                    "start_temp": 25.0,
                    "stop_temp": 22.0,
                    "outdoor_temp": 30.0
                },
                {
                    "timestamp": current_time,
                    "start_temp": 24.0,
                    "stop_temp": 21.0,
                    "outdoor_temp": 28.0
                }
            ]
        }
        mock_store.async_load.return_value = stored_data
        
        await learner.async_load()
        
        # Should only have recent pattern after pruning
        assert len(learner._patterns) == 1
        assert learner._patterns[0].timestamp == current_time

    @pytest.mark.asyncio
    async def test_async_save_success(self, learner, mock_store):
        """Test successful async_save to storage."""
        # Add a pattern
        learner._patterns = [
            LearnedPattern(1234567890.0, 25.0, 22.0, 30.0)
        ]
        
        await learner.async_save()
        
        mock_store.async_save.assert_called_once()
        saved_data = mock_store.async_save.call_args[0][0]
        
        assert "patterns" in saved_data
        assert len(saved_data["patterns"]) == 1
        pattern_data = saved_data["patterns"][0]
        assert pattern_data["timestamp"] == 1234567890.0
        assert pattern_data["start_temp"] == 25.0
        assert pattern_data["stop_temp"] == 22.0
        assert pattern_data["outdoor_temp"] == 30.0

    @pytest.mark.asyncio
    async def test_async_save_empty_patterns(self, learner, mock_store):
        """Test async_save with no patterns."""
        await learner.async_save()
        
        mock_store.async_save.assert_called_once()
        saved_data = mock_store.async_save.call_args[0][0]
        
        assert "patterns" in saved_data
        assert len(saved_data["patterns"]) == 0

    def test_integration_learn_and_retrieve_cycle(self, learner, mock_hass):
        """Test complete integration: learn patterns and retrieve relevant delta."""
        # Mock outdoor temperature sensor
        mock_state = Mock()
        mock_state.state = "25.0"
        mock_hass.states.get.return_value = mock_state
        
        # Learn multiple cycles with similar outdoor temperatures
        with patch('time.time', return_value=1234567890.0):
            learner.learn_new_cycle(25.0, 22.0)  # delta = 3.0
        with patch('time.time', return_value=1234567900.0):
            learner.learn_new_cycle(24.5, 21.0)  # delta = 3.5
        with patch('time.time', return_value=1234567910.0):
            learner.learn_new_cycle(26.0, 22.5)  # delta = 3.5
        
        # Should now have 3 patterns
        assert len(learner._patterns) == 3
        
        # Retrieve relevant delta
        delta = learner.get_relevant_hysteresis_delta()
        
        # Should return median: [3.0, 3.5, 3.5] -> 3.5
        assert delta == 3.5

    def test_edge_case_single_pattern_in_bucket(self, learner):
        """Test edge case with only one pattern in temperature bucket."""
        learner._patterns = [
            LearnedPattern(123.0, 25.0, 22.0, 25.0),  # delta = 3.0
        ]
        
        result = learner.get_relevant_hysteresis_delta(current_outdoor_temp=25.0)
        
        # With min_samples_for_bucket=3, should fall back to all patterns
        assert result == 3.0

    def test_edge_case_no_outdoor_temp_available(self, learner_no_outdoor):
        """Test behavior when no outdoor temperature sensor is configured."""
        result = learner_no_outdoor.get_relevant_hysteresis_delta()
        
        assert result is None

    def test_statistics_median_robustness(self, learner):
        """Test that statistics.median is used for robust delta calculation."""
        # Create patterns with outlier
        learner._patterns = [
            LearnedPattern(123.0, 25.0, 23.0, 25.0),  # delta = 2.0
            LearnedPattern(124.0, 24.0, 22.0, 25.0),  # delta = 2.0
            LearnedPattern(125.0, 30.0, 20.0, 25.0),  # delta = 10.0 (outlier)
            LearnedPattern(126.0, 23.0, 21.0, 25.0),  # delta = 2.0
            LearnedPattern(127.0, 22.0, 20.0, 25.0),  # delta = 2.0
        ]
        
        result = learner.get_relevant_hysteresis_delta(current_outdoor_temp=25.0)
        
        # Median should be resistant to outlier: [2.0, 2.0, 2.0, 2.0, 10.0] -> 2.0
        assert result == 2.0