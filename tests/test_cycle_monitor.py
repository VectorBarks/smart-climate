"""Tests for CycleMonitor component."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import time

from custom_components.smart_climate.cycle_monitor import CycleMonitor


class TestCycleMonitor:
    """Test suite for CycleMonitor class."""

    def test_init_with_default_values(self):
        """Test CycleMonitor initialization with default values."""
        monitor = CycleMonitor()
        
        assert monitor._min_off_time == 600  # 10 minutes
        assert monitor._min_on_time == 300   # 5 minutes
        assert len(monitor._cycle_history) == 0
        assert monitor._last_on_time is None
        assert monitor._last_off_time is None

    def test_init_with_custom_values(self):
        """Test CycleMonitor initialization with custom values."""
        monitor = CycleMonitor(min_off_time=900, min_on_time=450)
        
        assert monitor._min_off_time == 900  # 15 minutes
        assert monitor._min_on_time == 450   # 7.5 minutes

    @patch('time.time', return_value=1000)
    def test_can_turn_on_no_previous_off_time(self, mock_time):
        """Test can_turn_on when no previous off time recorded."""
        monitor = CycleMonitor()
        
        assert monitor.can_turn_on() is True

    @patch('time.time', return_value=1000)
    def test_can_turn_on_sufficient_off_time(self, mock_time):
        """Test can_turn_on when sufficient off time has passed."""
        monitor = CycleMonitor()
        monitor._last_off_time = 300  # 700 seconds ago (> 600 min_off_time)
        
        assert monitor.can_turn_on() is True

    @patch('time.time', return_value=1000)
    def test_can_turn_on_insufficient_off_time(self, mock_time):
        """Test can_turn_on when insufficient off time has passed."""
        monitor = CycleMonitor()
        monitor._last_off_time = 500  # 500 seconds ago (< 600 min_off_time)
        
        assert monitor.can_turn_on() is False

    @patch('time.time', return_value=1000)
    def test_can_turn_off_no_previous_on_time(self, mock_time):
        """Test can_turn_off when no previous on time recorded."""
        monitor = CycleMonitor()
        
        assert monitor.can_turn_off() is True

    @patch('time.time', return_value=1000)
    def test_can_turn_off_sufficient_on_time(self, mock_time):
        """Test can_turn_off when sufficient on time has passed."""
        monitor = CycleMonitor()
        monitor._last_on_time = 600  # 400 seconds ago (> 300 min_on_time)
        
        assert monitor.can_turn_off() is True

    @patch('time.time', return_value=1000)
    def test_can_turn_off_insufficient_on_time(self, mock_time):
        """Test can_turn_off when insufficient on time has passed."""
        monitor = CycleMonitor()
        monitor._last_on_time = 800  # 200 seconds ago (< 300 min_on_time)
        
        assert monitor.can_turn_off() is False

    @patch('time.time', return_value=1000)
    def test_record_cycle_on_cycle_updates_last_on_time(self, mock_time):
        """Test record_cycle updates last_on_time for on cycles."""
        monitor = CycleMonitor()
        
        monitor.record_cycle(duration=400, is_on=True)
        
        assert monitor._last_on_time == 1000
        assert len(monitor._cycle_history) == 1
        assert monitor._cycle_history[0] == (400, True, 1000)

    @patch('time.time', return_value=1000)
    def test_record_cycle_off_cycle_updates_last_off_time(self, mock_time):
        """Test record_cycle updates last_off_time for off cycles."""
        monitor = CycleMonitor()
        
        monitor.record_cycle(duration=700, is_on=False)
        
        assert monitor._last_off_time == 1000
        assert len(monitor._cycle_history) == 1
        assert monitor._cycle_history[0] == (700, False, 1000)

    def test_record_cycle_history_size_limit(self):
        """Test that cycle history is limited to 50 entries."""
        monitor = CycleMonitor()
        
        # Add 55 cycles to exceed limit
        for i in range(55):
            monitor.record_cycle(duration=300 + i, is_on=i % 2 == 0)
        
        assert len(monitor._cycle_history) == 50
        # Should contain the most recent 50 cycles
        assert monitor._cycle_history[0][0] == 305  # duration=305 (i=5)
        assert monitor._cycle_history[-1][0] == 354  # duration=354 (i=54)

    def test_get_average_cycle_duration_empty_history(self):
        """Test get_average_cycle_duration with empty history."""
        monitor = CycleMonitor()
        
        on_avg, off_avg = monitor.get_average_cycle_duration()
        
        assert on_avg == 0.0
        assert off_avg == 0.0

    def test_get_average_cycle_duration_mixed_cycles(self):
        """Test get_average_cycle_duration with mixed on/off cycles."""
        monitor = CycleMonitor()
        
        # Add on cycles: 300, 400, 500 seconds (avg = 400)
        monitor.record_cycle(duration=300, is_on=True)
        monitor.record_cycle(duration=400, is_on=True)
        monitor.record_cycle(duration=500, is_on=True)
        
        # Add off cycles: 600, 800 seconds (avg = 700)
        monitor.record_cycle(duration=600, is_on=False)
        monitor.record_cycle(duration=800, is_on=False)
        
        on_avg, off_avg = monitor.get_average_cycle_duration()
        
        assert on_avg == 400.0
        assert off_avg == 700.0

    def test_get_average_cycle_duration_only_on_cycles(self):
        """Test get_average_cycle_duration with only on cycles."""
        monitor = CycleMonitor()
        
        monitor.record_cycle(duration=300, is_on=True)
        monitor.record_cycle(duration=500, is_on=True)
        
        on_avg, off_avg = monitor.get_average_cycle_duration()
        
        assert on_avg == 400.0
        assert off_avg == 0.0

    def test_get_average_cycle_duration_only_off_cycles(self):
        """Test get_average_cycle_duration with only off cycles."""
        monitor = CycleMonitor()
        
        monitor.record_cycle(duration=600, is_on=False)
        monitor.record_cycle(duration=1000, is_on=False)
        
        on_avg, off_avg = monitor.get_average_cycle_duration()
        
        assert on_avg == 0.0
        assert off_avg == 800.0

    def test_needs_adjustment_healthy_cycles(self):
        """Test needs_adjustment returns False for healthy cycles."""
        monitor = CycleMonitor()
        
        # Add cycles that average above 7 minutes (420 seconds)
        for i in range(10):
            monitor.record_cycle(duration=450, is_on=True)  # 7.5 minutes each
        
        assert monitor.needs_adjustment() is False

    def test_needs_adjustment_short_on_cycles(self):
        """Test needs_adjustment returns True for short on cycles."""
        monitor = CycleMonitor()
        
        # Add cycles that average below 7 minutes (420 seconds)
        for i in range(10):
            monitor.record_cycle(duration=300, is_on=True)  # 5 minutes each
        
        assert monitor.needs_adjustment() is True

    def test_needs_adjustment_short_off_cycles(self):
        """Test needs_adjustment returns True for short off cycles."""
        monitor = CycleMonitor()
        
        # Add healthy on cycles but short off cycles
        for i in range(5):
            monitor.record_cycle(duration=500, is_on=True)   # 8.3 minutes each
            monitor.record_cycle(duration=300, is_on=False)  # 5 minutes each
        
        assert monitor.needs_adjustment() is True

    def test_needs_adjustment_mixed_healthy_and_unhealthy(self):
        """Test needs_adjustment with mix of healthy and unhealthy cycles."""
        monitor = CycleMonitor()
        
        # Add some short cycles
        for i in range(3):
            monitor.record_cycle(duration=300, is_on=True)  # 5 minutes
        
        # Add some healthy cycles
        for i in range(7):
            monitor.record_cycle(duration=500, is_on=True)  # 8.3 minutes
        
        # Average = (3*300 + 7*500) / 10 = 440 seconds = 7.33 minutes > 7 minutes
        assert monitor.needs_adjustment() is False

    def test_needs_adjustment_empty_history(self):
        """Test needs_adjustment with empty history."""
        monitor = CycleMonitor()
        
        assert monitor.needs_adjustment() is False