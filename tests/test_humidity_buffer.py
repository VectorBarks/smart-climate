"""Tests for HumidityBuffer class."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from collections import deque

# Import the class we're testing - this will fail initially (TDD)
from custom_components.smart_climate.humidity_monitor import HumidityBuffer


class TestHumidityBuffer:
    """Test cases for HumidityBuffer circular buffer."""
    
    def test_init_creates_deque_with_correct_maxlen(self):
        """Test that buffer is initialized with correct size for 24 hours."""
        buffer = HumidityBuffer(hours=24)
        # 24 hours * 12 entries per hour (5-minute granularity) = 288 entries
        assert buffer._buffer.maxlen == 288
        assert buffer._hours == 24
        assert len(buffer._buffer) == 0
        
    def test_init_custom_hours(self):
        """Test initialization with custom hours."""
        buffer = HumidityBuffer(hours=12)
        assert buffer._buffer.maxlen == 144  # 12 * 12
        assert buffer._hours == 12
        
    def test_add_event_adds_timestamp_automatically(self):
        """Test that add_event automatically adds ISO format timestamp."""
        buffer = HumidityBuffer()
        test_event = {"indoor": 45.0, "outdoor": 70.0}
        
        with patch('custom_components.smart_climate.humidity_monitor.datetime') as mock_dt:
            mock_now = datetime(2025, 8, 13, 14, 30, 0)
            mock_dt.now.return_value = mock_now
            
            buffer.add_event(test_event)
            
            # Check that timestamp was added
            stored_event = buffer._buffer[0]
            assert "timestamp" in stored_event
            assert stored_event["timestamp"] == "2025-08-13T14:30:00"
            assert stored_event["indoor"] == 45.0
            assert stored_event["outdoor"] == 70.0
            
    def test_add_event_preserves_original_data(self):
        """Test that original event dict is not modified."""
        buffer = HumidityBuffer()
        original_event = {"indoor": 45.0, "outdoor": 70.0}
        
        buffer.add_event(original_event)
        
        # Original should not have timestamp added
        assert "timestamp" not in original_event
        assert original_event == {"indoor": 45.0, "outdoor": 70.0}
        
    def test_buffer_circular_behavior_drops_old_entries(self):
        """Test that buffer drops old entries when maxlen is exceeded."""
        buffer = HumidityBuffer(hours=1)  # Only 12 entries max
        
        # Add 15 events (more than maxlen of 12)
        for i in range(15):
            buffer.add_event({"value": i})
            
        # Should only have 12 entries (the last 12)
        assert len(buffer._buffer) == 12
        
        # Should have values 3-14 (first 3 dropped)
        values = [event["value"] for event in buffer._buffer]
        assert values == list(range(3, 15))
        
    def test_get_recent_filters_by_time_correctly(self):
        """Test that get_recent returns only events within time window."""
        buffer = HumidityBuffer()
        base_time = datetime(2025, 8, 13, 14, 0, 0)
        
        with patch('custom_components.smart_climate.humidity_monitor.datetime') as mock_dt:
            # Add events at different times
            events_data = [
                (base_time - timedelta(minutes=120), {"value": "old1"}),     # 2h ago
                (base_time - timedelta(minutes=90), {"value": "old2"}),      # 1.5h ago  
                (base_time - timedelta(minutes=45), {"value": "recent1"}),   # 45min ago
                (base_time - timedelta(minutes=30), {"value": "recent2"}),   # 30min ago
                (base_time - timedelta(minutes=15), {"value": "recent3"}),   # 15min ago
            ]
            
            for timestamp, event in events_data:
                mock_dt.now.return_value = timestamp
                buffer.add_event(event)
            
            # Set current time for get_recent call
            mock_dt.now.return_value = base_time
            
            # Get last 60 minutes
            recent = buffer.get_recent(minutes=60)
            
            # Should only get the 3 events from last hour
            assert len(recent) == 3
            values = [event["value"] for event in recent]
            assert values == ["recent1", "recent2", "recent3"]
            
    def test_get_recent_default_60_minutes(self):
        """Test that get_recent defaults to 60 minutes if not specified."""
        buffer = HumidityBuffer()
        base_time = datetime(2025, 8, 13, 14, 0, 0)
        
        with patch('custom_components.smart_climate.humidity_monitor.datetime') as mock_dt:
            # Add one old event and one recent event
            mock_dt.now.return_value = base_time - timedelta(minutes=90)
            buffer.add_event({"value": "old"})
            
            mock_dt.now.return_value = base_time - timedelta(minutes=30)
            buffer.add_event({"value": "recent"})
            
            # Set current time for get_recent call
            mock_dt.now.return_value = base_time
            
            # Call without minutes parameter - should default to 60
            recent = buffer.get_recent()
            
            assert len(recent) == 1
            assert recent[0]["value"] == "recent"
            
    def test_get_recent_empty_buffer(self):
        """Test get_recent returns empty list for empty buffer."""
        buffer = HumidityBuffer()
        recent = buffer.get_recent(minutes=60)
        assert recent == []
        
    def test_get_recent_no_matches_in_timeframe(self):
        """Test get_recent returns empty list when no events in timeframe."""
        buffer = HumidityBuffer()
        base_time = datetime(2025, 8, 13, 14, 0, 0)
        
        with patch('custom_components.smart_climate.humidity_monitor.datetime') as mock_dt:
            # Add old event
            mock_dt.now.return_value = base_time - timedelta(hours=2)
            buffer.add_event({"value": "old"})
            
            # Set current time
            mock_dt.now.return_value = base_time
            
            # Try to get recent events - should be empty
            recent = buffer.get_recent(minutes=30)
            assert recent == []
            
    def test_buffer_maintains_fifo_order(self):
        """Test that buffer maintains first-in-first-out order."""
        buffer = HumidityBuffer()
        base_time = datetime(2025, 8, 13, 14, 0, 0)
        
        with patch('custom_components.smart_climate.humidity_monitor.datetime') as mock_dt:
            # Add events in chronological order
            for i in range(5):
                mock_dt.now.return_value = base_time + timedelta(minutes=i*10)
                buffer.add_event({"sequence": i})
                
            # Check that order is maintained
            sequences = [event["sequence"] for event in buffer._buffer]
            assert sequences == [0, 1, 2, 3, 4]
            
    def test_buffer_uses_collections_deque(self):
        """Test that buffer uses collections.deque for efficiency."""
        buffer = HumidityBuffer()
        assert isinstance(buffer._buffer, deque)
        assert hasattr(buffer._buffer, 'maxlen')
        
    def test_iso_timestamp_format(self):
        """Test that timestamps use ISO format for consistency."""
        buffer = HumidityBuffer()
        test_event = {"data": "test"}
        
        with patch('custom_components.smart_climate.humidity_monitor.datetime') as mock_dt:
            mock_now = datetime(2025, 8, 13, 14, 30, 45)
            mock_dt.now.return_value = mock_now
            
            buffer.add_event(test_event)
            
            stored_event = buffer._buffer[0]
            # Should be ISO format without microseconds
            assert stored_event["timestamp"] == "2025-08-13T14:30:45"