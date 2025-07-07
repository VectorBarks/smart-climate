"""ABOUTME: Manual override management for smart climate control.
Provides dataclass and manager for tracking manual temperature overrides."""

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class OverrideNotActiveError(Exception):
    """Raised when trying to access override data when no override is active."""
    pass


class OverrideExpiredError(Exception):
    """Raised when trying to access expired override data."""
    pass


@dataclass
class ManualOverride:
    """Represents a manual temperature override with duration tracking."""
    
    offset: float  # Temperature offset in degrees
    duration: int  # Duration in minutes
    start_time: Optional[datetime] = None  # When override was activated
    active: bool = False  # Whether override is currently active
    
    def is_expired(self) -> bool:
        """Check if the override has expired.
        
        Returns:
            bool: True if override is expired, False otherwise.
        """
        if not self.active or self.start_time is None:
            return False
        
        elapsed_time = datetime.now() - self.start_time
        return elapsed_time.total_seconds() > (self.duration * 60)
    
    def remaining_time(self) -> int:
        """Get remaining time in minutes.
        
        Returns:
            int: Remaining time in minutes, 0 if expired or not active.
        """
        if not self.active or self.start_time is None:
            return 0
        
        elapsed_time = datetime.now() - self.start_time
        elapsed_minutes = elapsed_time.total_seconds() / 60
        
        remaining = self.duration - elapsed_minutes
        return max(0, int(remaining))


class OverrideManager:
    """Manages manual temperature overrides with activation, deactivation, and expiration."""
    
    def __init__(self):
        """Initialize the override manager."""
        self.current_override: Optional[ManualOverride] = None
    
    def has_active_override(self) -> bool:
        """Check if there is an active override.
        
        Returns:
            bool: True if there is an active override, False otherwise.
        """
        return self.current_override is not None and self.current_override.active
    
    def activate_override(self, offset: float, duration: int) -> None:
        """Activate a manual override.
        
        Args:
            offset: Temperature offset in degrees
            duration: Duration in minutes
        """
        self.current_override = ManualOverride(
            offset=offset,
            duration=duration,
            start_time=datetime.now(),
            active=True
        )
    
    def deactivate_override(self) -> None:
        """Deactivate the current override."""
        self.current_override = None
    
    def get_current_offset(self) -> float:
        """Get the current override offset.
        
        Returns:
            float: Current offset value
            
        Raises:
            OverrideNotActiveError: If no override is active
            OverrideExpiredError: If override has expired
        """
        if not self.has_active_override():
            raise OverrideNotActiveError("No active override")
        
        if self.current_override.is_expired():
            raise OverrideExpiredError("Override has expired")
        
        return self.current_override.offset
    
    def check_and_expire_override(self) -> bool:
        """Check if current override has expired and remove it if so.
        
        Returns:
            bool: True if an override was expired and removed, False otherwise.
        """
        if not self.has_active_override():
            return False
        
        if self.current_override.is_expired():
            self.deactivate_override()
            return True
        
        return False
    
    def get_remaining_time(self) -> int:
        """Get remaining time for current override.
        
        Returns:
            int: Remaining time in minutes, 0 if no active override.
        """
        if not self.has_active_override():
            return 0
        
        return self.current_override.remaining_time()
    
    def get_state_data(self) -> Dict[str, Any]:
        """Get state data for persistence.
        
        Returns:
            Dict with state data suitable for serialization.
        """
        if not self.has_active_override():
            return {
                'has_override': False,
                'current_override': None
            }
        
        override_data = asdict(self.current_override)
        # Convert datetime to ISO string for serialization
        if override_data['start_time'] is not None:
            override_data['start_time'] = self.current_override.start_time.isoformat()
        
        return {
            'has_override': True,
            'current_override': override_data
        }
    
    def restore_state_data(self, state_data: Dict[str, Any]) -> None:
        """Restore state from persistence data.
        
        Args:
            state_data: State data from get_state_data()
        """
        if not state_data.get('has_override', False) or state_data.get('current_override') is None:
            self.current_override = None
            return
        
        override_data = state_data['current_override']
        
        # Convert ISO string back to datetime
        start_time = None
        if override_data.get('start_time') is not None:
            start_time = datetime.fromisoformat(override_data['start_time'])
        
        self.current_override = ManualOverride(
            offset=override_data['offset'],
            duration=override_data['duration'],
            start_time=start_time,
            active=override_data['active']
        )