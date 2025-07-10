"""Test fixtures for DataUpdateCoordinator implementation tests."""

from unittest.mock import Mock, AsyncMock
from datetime import timedelta
from typing import Dict, Any, Optional

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from custom_components.smart_climate.offset_engine import OffsetEngine


def create_mock_offset_engine(
    learning_enabled: bool = True,
    samples: int = 20,
    accuracy: float = 0.85,
    has_hysteresis: bool = True,
    calculated_offset: float = 2.0,
) -> Mock:
    """Create a mock OffsetEngine with configurable dashboard data."""
    engine = Mock(spec=OffsetEngine)
    
    # Configure basic attributes
    engine._learning_enabled = learning_enabled
    engine._last_offset = calculated_offset
    engine._save_count = 10
    engine._failed_save_count = 1
    engine._last_save_time = "2025-07-10 09:00:00"
    
    # Configure learners
    if samples > 0:
        engine._lightweight_learner = Mock()
        engine._lightweight_learner.get_samples_count.return_value = samples
        engine._lightweight_learner.get_accuracy.return_value = accuracy
    else:
        engine._lightweight_learner = None
    
    if has_hysteresis:
        engine._hysteresis_learner = Mock()
        engine._hysteresis_learner.has_sufficient_data = samples >= 10
        engine._hysteresis_learner.learned_start_threshold = 24.5 if samples >= 10 else None
        engine._hysteresis_learner.learned_stop_threshold = 23.5 if samples >= 10 else None
        engine._current_hysteresis_state = "idle_stable_zone" if samples >= 10 else "learning_hysteresis"
    else:
        engine._hysteresis_learner = None
        engine._current_hysteresis_state = "disabled"
    
    # Configure calibration
    engine._calibration_cache = {"offset": 1.5, "timestamp": 1234567890} if samples > 5 else {}
    
    # Mock the async_get_dashboard_data method
    async def mock_get_dashboard_data():
        learning_info = {
            "enabled": engine._learning_enabled,
            "samples": engine._lightweight_learner.get_samples_count() if engine._lightweight_learner else 0,
            "accuracy": engine._lightweight_learner.get_accuracy() if engine._lightweight_learner else 0.0,
            "hysteresis_enabled": engine._hysteresis_learner is not None,
            "hysteresis_state": engine._current_hysteresis_state,
            "learned_start_threshold": engine._hysteresis_learner.learned_start_threshold if engine._hysteresis_learner else None,
            "learned_stop_threshold": engine._hysteresis_learner.learned_stop_threshold if engine._hysteresis_learner else None,
            "temperature_window": 1.0 if engine._hysteresis_learner and engine._hysteresis_learner.has_sufficient_data else None,
            "start_samples_collected": 10 if engine._hysteresis_learner else 0,
            "stop_samples_collected": 8 if engine._hysteresis_learner else 0,
            "hysteresis_ready": engine._hysteresis_learner.has_sufficient_data if engine._hysteresis_learner else False,
            "last_sample_time": "2025-07-10 08:55:00" if samples > 0 else None,
        }
        
        return {
            "calculated_offset": engine._last_offset,
            "learning_info": learning_info,
            "save_diagnostics": {
                "save_count": engine._save_count,
                "failed_save_count": engine._failed_save_count,
                "last_save_time": engine._last_save_time,
            },
            "calibration_info": {
                "in_calibration": samples < 10,
                "cached_offset": engine._calibration_cache.get("offset"),
            },
        }
    
    engine.async_get_dashboard_data = mock_get_dashboard_data
    
    return engine


def create_mock_coordinator(
    hass: Mock,
    offset_engine: Mock,
    entity_id: str = "climate.test",
    update_interval: int = 30,
    initial_data: Optional[Dict[str, Any]] = None,
) -> DataUpdateCoordinator:
    """Create a mock DataUpdateCoordinator for testing."""
    
    async def async_update_data():
        """Fetch data from offset engine."""
        return await offset_engine.async_get_dashboard_data()
    
    coordinator = DataUpdateCoordinator(
        hass,
        Mock(),  # logger
        name=f"smart_climate_{entity_id}",
        update_method=async_update_data,
        update_interval=timedelta(seconds=update_interval),
    )
    
    # Set initial data if provided
    if initial_data:
        coordinator.data = initial_data
        coordinator.last_update_success = True
    
    return coordinator


def create_dashboard_data_fixture(
    offset: float = 2.0,
    learning_enabled: bool = True,
    samples: int = 20,
    accuracy: float = 0.85,
    in_calibration: bool = False,
    has_hysteresis: bool = True,
) -> Dict[str, Any]:
    """Create a complete dashboard data structure for testing."""
    return {
        "calculated_offset": offset,
        "learning_info": {
            "enabled": learning_enabled,
            "samples": samples,
            "accuracy": accuracy,
            "hysteresis_enabled": has_hysteresis,
            "hysteresis_state": "idle_stable_zone" if samples >= 10 else "learning_hysteresis",
            "learned_start_threshold": 24.5 if samples >= 10 and has_hysteresis else None,
            "learned_stop_threshold": 23.5 if samples >= 10 and has_hysteresis else None,
            "temperature_window": 1.0 if samples >= 10 and has_hysteresis else None,
            "start_samples_collected": 10 if has_hysteresis else 0,
            "stop_samples_collected": 8 if has_hysteresis else 0,
            "hysteresis_ready": samples >= 10 and has_hysteresis,
            "last_sample_time": "2025-07-10 08:55:00" if samples > 0 else None,
        },
        "save_diagnostics": {
            "save_count": 10,
            "failed_save_count": 1,
            "last_save_time": "2025-07-10 09:00:00",
        },
        "calibration_info": {
            "in_calibration": in_calibration,
            "cached_offset": 1.5 if not in_calibration else None,
        },
    }


def create_failed_coordinator(hass: Mock, entity_id: str = "climate.test") -> DataUpdateCoordinator:
    """Create a coordinator that simulates update failure."""
    
    async def async_update_data():
        """Simulate update failure."""
        from homeassistant.helpers.update_coordinator import UpdateFailed
        raise UpdateFailed("Simulated update failure")
    
    coordinator = DataUpdateCoordinator(
        hass,
        Mock(),  # logger
        name=f"smart_climate_{entity_id}",
        update_method=async_update_data,
        update_interval=timedelta(seconds=30),
    )
    
    coordinator.data = None
    coordinator.last_update_success = False
    
    return coordinator