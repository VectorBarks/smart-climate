"""Test the override manager functionality."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from custom_components.smart_climate.override_manager import (
    ManualOverride,
    OverrideManager,
    OverrideNotActiveError,
    OverrideExpiredError,
)


class TestManualOverride:
    """Test the ManualOverride dataclass."""

    def test_manual_override_creation(self):
        """Test creating a manual override."""
        override = ManualOverride(
            offset=2.5,
            duration=30,  # 30 minutes
            start_time=datetime.now(),
            active=True
        )
        
        assert override.offset == 2.5
        assert override.duration == 30
        assert override.active is True
        assert isinstance(override.start_time, datetime)

    def test_manual_override_defaults(self):
        """Test manual override with default values."""
        override = ManualOverride(
            offset=1.0,
            duration=60
        )
        
        assert override.offset == 1.0
        assert override.duration == 60
        assert override.active is False
        assert override.start_time is None

    def test_manual_override_is_expired_not_active(self):
        """Test that inactive override is not considered expired."""
        override = ManualOverride(
            offset=1.0,
            duration=30,
            active=False
        )
        
        assert not override.is_expired()

    def test_manual_override_is_expired_no_start_time(self):
        """Test that override without start time is not expired."""
        override = ManualOverride(
            offset=1.0,
            duration=30,
            active=True,
            start_time=None
        )
        
        assert not override.is_expired()

    def test_manual_override_is_expired_within_duration(self):
        """Test that override within duration is not expired."""
        start_time = datetime.now() - timedelta(minutes=10)
        override = ManualOverride(
            offset=1.0,
            duration=30,
            active=True,
            start_time=start_time
        )
        
        assert not override.is_expired()

    def test_manual_override_is_expired_beyond_duration(self):
        """Test that override beyond duration is expired."""
        start_time = datetime.now() - timedelta(minutes=45)
        override = ManualOverride(
            offset=1.0,
            duration=30,
            active=True,
            start_time=start_time
        )
        
        assert override.is_expired()

    def test_manual_override_remaining_time_not_active(self):
        """Test remaining time when override is not active."""
        override = ManualOverride(
            offset=1.0,
            duration=30,
            active=False
        )
        
        assert override.remaining_time() == 0

    def test_manual_override_remaining_time_no_start_time(self):
        """Test remaining time when no start time is set."""
        override = ManualOverride(
            offset=1.0,
            duration=30,
            active=True,
            start_time=None
        )
        
        assert override.remaining_time() == 0

    def test_manual_override_remaining_time_within_duration(self):
        """Test remaining time calculation within duration."""
        start_time = datetime.now() - timedelta(minutes=10)
        override = ManualOverride(
            offset=1.0,
            duration=30,
            active=True,
            start_time=start_time
        )
        
        remaining = override.remaining_time()
        assert 19 <= remaining <= 21  # Should be around 20 minutes

    def test_manual_override_remaining_time_expired(self):
        """Test remaining time when override is expired."""
        start_time = datetime.now() - timedelta(minutes=45)
        override = ManualOverride(
            offset=1.0,
            duration=30,
            active=True,
            start_time=start_time
        )
        
        assert override.remaining_time() == 0


class TestOverrideManager:
    """Test the OverrideManager class."""

    def test_override_manager_creation(self):
        """Test creating an override manager."""
        manager = OverrideManager()
        
        assert manager.current_override is None
        assert not manager.has_active_override()

    def test_activate_override(self):
        """Test activating a manual override."""
        manager = OverrideManager()
        
        with patch('custom_components.smart_climate.override_manager.datetime') as mock_datetime:
            mock_now = datetime(2025, 7, 7, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            manager.activate_override(
                offset=2.5,
                duration=60  # 60 minutes
            )
            
            assert manager.has_active_override()
            override = manager.current_override
            assert override.offset == 2.5
            assert override.duration == 60
            assert override.active is True
            assert override.start_time == mock_now

    def test_activate_override_replaces_existing(self):
        """Test that activating override replaces existing one."""
        manager = OverrideManager()
        
        with patch('custom_components.smart_climate.override_manager.datetime') as mock_datetime:
            mock_now = datetime(2025, 7, 7, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            # First override
            manager.activate_override(offset=1.0, duration=30)
            first_override = manager.current_override
            
            # Second override
            manager.activate_override(offset=2.0, duration=45)
            second_override = manager.current_override
            
            assert first_override != second_override
            assert second_override.offset == 2.0
            assert second_override.duration == 45

    def test_deactivate_override(self):
        """Test deactivating a manual override."""
        manager = OverrideManager()
        
        # First activate
        manager.activate_override(offset=1.0, duration=30)
        assert manager.has_active_override()
        
        # Then deactivate
        manager.deactivate_override()
        
        assert not manager.has_active_override()
        assert manager.current_override is None

    def test_deactivate_override_when_none_active(self):
        """Test deactivating override when none is active."""
        manager = OverrideManager()
        
        # Should not raise error
        manager.deactivate_override()
        
        assert not manager.has_active_override()
        assert manager.current_override is None

    def test_get_current_offset_no_override(self):
        """Test getting current offset when no override is active."""
        manager = OverrideManager()
        
        with pytest.raises(OverrideNotActiveError):
            manager.get_current_offset()

    def test_get_current_offset_with_override(self):
        """Test getting current offset with active override."""
        manager = OverrideManager()
        
        manager.activate_override(offset=3.0, duration=30)
        
        assert manager.get_current_offset() == 3.0

    def test_get_current_offset_expired_override(self):
        """Test getting current offset when override is expired."""
        manager = OverrideManager()
        
        with patch('custom_components.smart_climate.override_manager.datetime') as mock_datetime:
            start_time = datetime(2025, 7, 7, 12, 0, 0)
            mock_datetime.now.return_value = start_time
            
            # Activate override
            manager.activate_override(offset=2.0, duration=30)
            
            # Now move time forward past expiration
            expired_time = start_time + timedelta(minutes=45)
            mock_datetime.now.return_value = expired_time
            
            with pytest.raises(OverrideExpiredError):
                manager.get_current_offset()

    def test_check_and_expire_override_not_expired(self):
        """Test checking expiration when override is not expired."""
        manager = OverrideManager()
        
        with patch('custom_components.smart_climate.override_manager.datetime') as mock_datetime:
            start_time = datetime(2025, 7, 7, 12, 0, 0)
            mock_datetime.now.return_value = start_time
            
            manager.activate_override(offset=1.0, duration=30)
            
            # Move time forward but not past expiration
            current_time = start_time + timedelta(minutes=15)
            mock_datetime.now.return_value = current_time
            
            expired = manager.check_and_expire_override()
            
            assert not expired
            assert manager.has_active_override()

    def test_check_and_expire_override_expired(self):
        """Test checking expiration when override is expired."""
        manager = OverrideManager()
        
        with patch('custom_components.smart_climate.override_manager.datetime') as mock_datetime:
            start_time = datetime(2025, 7, 7, 12, 0, 0)
            mock_datetime.now.return_value = start_time
            
            manager.activate_override(offset=1.0, duration=30)
            
            # Move time forward past expiration
            expired_time = start_time + timedelta(minutes=45)
            mock_datetime.now.return_value = expired_time
            
            expired = manager.check_and_expire_override()
            
            assert expired
            assert not manager.has_active_override()
            assert manager.current_override is None

    def test_check_and_expire_override_no_active(self):
        """Test checking expiration when no override is active."""
        manager = OverrideManager()
        
        expired = manager.check_and_expire_override()
        
        assert not expired
        assert not manager.has_active_override()

    def test_get_remaining_time_no_override(self):
        """Test getting remaining time when no override is active."""
        manager = OverrideManager()
        
        assert manager.get_remaining_time() == 0

    def test_get_remaining_time_with_override(self):
        """Test getting remaining time with active override."""
        manager = OverrideManager()
        
        with patch('custom_components.smart_climate.override_manager.datetime') as mock_datetime:
            start_time = datetime(2025, 7, 7, 12, 0, 0)
            mock_datetime.now.return_value = start_time
            
            manager.activate_override(offset=1.0, duration=30)
            
            # Move time forward 10 minutes
            current_time = start_time + timedelta(minutes=10)
            mock_datetime.now.return_value = current_time
            
            remaining = manager.get_remaining_time()
            assert remaining == 20  # 30 - 10 = 20 minutes

    def test_state_persistence_data(self):
        """Test getting state data for persistence."""
        manager = OverrideManager()
        
        # Test with no override
        state = manager.get_state_data()
        assert state == {
            'has_override': False,
            'current_override': None
        }
        
        # Test with active override
        with patch('custom_components.smart_climate.override_manager.datetime') as mock_datetime:
            mock_now = datetime(2025, 7, 7, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            manager.activate_override(offset=2.0, duration=45)
            
            state = manager.get_state_data()
            assert state['has_override'] is True
            assert state['current_override']['offset'] == 2.0
            assert state['current_override']['duration'] == 45
            assert state['current_override']['active'] is True
            assert state['current_override']['start_time'] == mock_now.isoformat()

    def test_state_persistence_restore(self):
        """Test restoring state from persistence data."""
        manager = OverrideManager()
        
        # Test restoring empty state
        manager.restore_state_data({
            'has_override': False,
            'current_override': None
        })
        
        assert not manager.has_active_override()
        
        # Test restoring with override
        start_time = datetime(2025, 7, 7, 12, 0, 0)
        state_data = {
            'has_override': True,
            'current_override': {
                'offset': 3.0,
                'duration': 60,
                'active': True,
                'start_time': start_time.isoformat()
            }
        }
        
        manager.restore_state_data(state_data)
        
        assert manager.has_active_override()
        override = manager.current_override
        assert override.offset == 3.0
        assert override.duration == 60
        assert override.active is True
        assert override.start_time == start_time