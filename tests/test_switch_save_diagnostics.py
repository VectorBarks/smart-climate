"""Test save diagnostics attributes for Smart Climate switch entities."""

import pytest
from unittest.mock import Mock
from datetime import datetime
from homeassistant.config_entries import ConfigEntry

from custom_components.smart_climate.switch import LearningSwitch
from custom_components.smart_climate.offset_engine import OffsetEngine


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = Mock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.unique_id = "test_unique_id"
    entry.title = "Test Climate"
    entry.data = {
        "max_offset": 5.0,
        "enable_learning": True
    }
    return entry


@pytest.fixture
def mock_offset_engine():
    """Create a mock offset engine with save statistics."""
    engine = Mock(spec=OffsetEngine)
    engine.is_learning_enabled = True
    engine.save_count = 5
    engine.failed_save_count = 2
    engine.last_save_time = datetime(2025, 7, 9, 14, 30, 0)
    
    # Mock the get_learning_info method
    engine.get_learning_info = Mock(return_value={
        "enabled": True,
        "samples": 10,
        "accuracy": 0.85,
        "confidence": 0.75,
        "has_sufficient_data": True,
        "last_sample_time": "2025-07-09T14:25:00"
    })
    
    return engine


@pytest.fixture
def learning_switch(mock_config_entry, mock_offset_engine):
    """Create a learning switch with save statistics."""
    return LearningSwitch(
        mock_config_entry,
        mock_offset_engine,
        "Test Climate",
        "climate.test"
    )


class TestSaveDiagnosticsAttributes:
    """Test save diagnostics in switch attributes."""
    
    def test_save_statistics_included_in_attributes(self, learning_switch, mock_offset_engine):
        """Test that save statistics are included in extra_state_attributes."""
        # Get the switch attributes
        attributes = learning_switch.extra_state_attributes
        
        # Verify save statistics are present
        assert "save_count" in attributes
        assert "failed_save_count" in attributes
        assert "last_save_time" in attributes
        
        # Verify the values match the offset engine
        assert attributes["save_count"] == 5
        assert attributes["failed_save_count"] == 2
        assert attributes["last_save_time"] == "2025-07-09 14:30:00"
    
    def test_save_statistics_with_no_saves(self, learning_switch, mock_offset_engine):
        """Test save statistics when no saves have occurred."""
        # Set up engine with no saves
        mock_offset_engine.save_count = 0
        mock_offset_engine.failed_save_count = 0
        mock_offset_engine.last_save_time = None
        
        attributes = learning_switch.extra_state_attributes
        
        # Verify initial state
        assert attributes["save_count"] == 0
        assert attributes["failed_save_count"] == 0
        assert attributes["last_save_time"] == "Never"
    
    def test_save_statistics_with_failed_saves_only(self, learning_switch, mock_offset_engine):
        """Test save statistics when only failed saves occurred."""
        # Set up engine with failed saves only
        mock_offset_engine.save_count = 0
        mock_offset_engine.failed_save_count = 3
        mock_offset_engine.last_save_time = None
        
        attributes = learning_switch.extra_state_attributes
        
        # Verify failed saves are tracked
        assert attributes["save_count"] == 0
        assert attributes["failed_save_count"] == 3
        assert attributes["last_save_time"] == "Never"
    
    def test_last_save_time_formatting(self, learning_switch, mock_offset_engine):
        """Test that last_save_time is formatted correctly."""
        # Test with various datetime formats
        test_times = [
            (datetime(2025, 7, 9, 14, 30, 0), "2025-07-09 14:30:00"),
            (datetime(2025, 1, 1, 0, 0, 0), "2025-01-01 00:00:00"),
            (datetime(2025, 12, 31, 23, 59, 59), "2025-12-31 23:59:59"),
        ]
        
        for dt, expected in test_times:
            mock_offset_engine.last_save_time = dt
            attributes = learning_switch.extra_state_attributes
            assert attributes["last_save_time"] == expected
    
    def test_save_statistics_handle_engine_errors(self, learning_switch, mock_offset_engine):
        """Test that save statistics handle offset engine errors gracefully."""
        # Make offset engine properties raise exceptions using PropertyMock
        from unittest.mock import PropertyMock
        type(mock_offset_engine).save_count = PropertyMock(side_effect=Exception("Engine error"))
        type(mock_offset_engine).failed_save_count = PropertyMock(side_effect=Exception("Engine error"))
        type(mock_offset_engine).last_save_time = PropertyMock(side_effect=Exception("Engine error"))
        
        attributes = learning_switch.extra_state_attributes
        
        # Should have graceful fallback values without crashing
        assert attributes["save_count"] == 0
        assert attributes["failed_save_count"] == 0
        assert attributes["last_save_time"] == "Error"
        # Other attributes should still work normally
        assert attributes["samples_collected"] == 10
        assert attributes["learning_accuracy"] == 0.85
    
    def test_save_statistics_with_learning_info_error(self, learning_switch, mock_offset_engine):
        """Test save statistics when get_learning_info fails."""
        # Make get_learning_info fail
        mock_offset_engine.get_learning_info = Mock(side_effect=Exception("Learning info error"))
        
        attributes = learning_switch.extra_state_attributes
        
        # Save statistics should still be attempted even if learning info fails
        # (They are separate operations)
        assert "save_count" in attributes
        assert "failed_save_count" in attributes
        assert "last_save_time" in attributes
        assert "error" in attributes
        
        # Should have fallback values for other attributes
        assert attributes["samples_collected"] == 0
        assert attributes["learning_accuracy"] == 0.0
    
    def test_save_statistics_integration_with_existing_attributes(self, learning_switch, mock_offset_engine):
        """Test that save statistics integrate properly with existing attributes."""
        attributes = learning_switch.extra_state_attributes
        
        # Verify all expected attributes are present
        expected_attrs = [
            "samples_collected", "learning_accuracy", "confidence_level",
            "patterns_learned", "has_sufficient_data", "enabled",
            "last_sample_collected", "save_count", "failed_save_count", 
            "last_save_time"
        ]
        
        for attr in expected_attrs:
            assert attr in attributes, f"Missing attribute: {attr}"
        
        # Verify save statistics don't interfere with existing attributes
        assert attributes["samples_collected"] == 10
        assert attributes["learning_accuracy"] == 0.85
        assert attributes["confidence_level"] == 0.75
        assert attributes["save_count"] == 5
        assert attributes["failed_save_count"] == 2
        assert attributes["last_save_time"] == "2025-07-09 14:30:00"
    
    def test_save_count_updates_reflect_in_attributes(self, learning_switch, mock_offset_engine):
        """Test that save count updates are reflected in attributes."""
        # Initial state
        attributes = learning_switch.extra_state_attributes
        assert attributes["save_count"] == 5
        
        # Simulate successful save
        mock_offset_engine.save_count = 6
        mock_offset_engine.last_save_time = datetime(2025, 7, 9, 14, 35, 0)
        
        # Get fresh attributes
        attributes = learning_switch.extra_state_attributes
        assert attributes["save_count"] == 6
        assert attributes["last_save_time"] == "2025-07-09 14:35:00"
    
    def test_failed_save_count_updates_reflect_in_attributes(self, learning_switch, mock_offset_engine):
        """Test that failed save count updates are reflected in attributes."""
        # Initial state
        attributes = learning_switch.extra_state_attributes
        assert attributes["failed_save_count"] == 2
        
        # Simulate failed save
        mock_offset_engine.failed_save_count = 3
        # Note: last_save_time should NOT update on failed saves
        
        # Get fresh attributes
        attributes = learning_switch.extra_state_attributes
        assert attributes["failed_save_count"] == 3
        assert attributes["last_save_time"] == "2025-07-09 14:30:00"  # Unchanged