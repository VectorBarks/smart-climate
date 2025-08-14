"""Test module for DelayLearner class."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
from freezegun import freeze_time

from custom_components.smart_climate.delay_learner import DelayLearner

# Constants for tests (matching implementation)
CHECK_INTERVAL = timedelta(seconds=15)
LEARNING_TIMEOUT = timedelta(minutes=20)  # Updated to match new default timeout
EMA_ALPHA = 0.3
STABILITY_THRESHOLD = 0.1


@pytest.fixture
def mock_hass_and_store():
    """Fixture for a mocked HASS and Store object."""
    hass = MagicMock()
    hass.states.get = MagicMock()
    
    store = MagicMock()
    store.async_load = AsyncMock(return_value=None)
    store.async_save = AsyncMock()
    
    return hass, store


@pytest.mark.asyncio
class TestDelayLearner:
    """Tests for the DelayLearner class."""

    async def test_initialization_empty_store(self, mock_hass_and_store):
        """Test that the learner initializes correctly with no prior data."""
        hass, store = mock_hass_and_store
        learner = DelayLearner(hass, "climate.test", "sensor.test_temp", store)
        await learner.async_load()
        
        assert learner._learned_delay_secs is None
        store.async_load.assert_awaited_once()

    async def test_load_from_store(self, mock_hass_and_store):
        """Test loading a learned delay from the store."""
        hass, store = mock_hass_and_store
        store.async_load.return_value = {"learned_delay": 90}
        
        learner = DelayLearner(hass, "climate.test", "sensor.test_temp", store)
        await learner.async_load()
        
        assert learner._learned_delay_secs == 90

    async def test_save_first_value(self, mock_hass_and_store):
        """Test saving a value for the first time (no EMA)."""
        hass, store = mock_hass_and_store
        learner = DelayLearner(hass, "climate.test", "sensor.test_temp", store)
        
        await learner.async_save(120)
        
        assert learner._learned_delay_secs == 120
        store.async_save.assert_awaited_with({"learned_delay": 120})

    async def test_save_with_ema_smoothing(self, mock_hass_and_store):
        """Test that subsequent saves use EMA."""
        hass, store = mock_hass_and_store
        store.async_load.return_value = {"learned_delay": 100}
        learner = DelayLearner(hass, "climate.test", "sensor.test_temp", store)
        await learner.async_load()  # Load the initial value

        new_measurement = 50
        expected_ema = int((EMA_ALPHA * new_measurement) + (1 - EMA_ALPHA) * 100)  # 85
        
        await learner.async_save(new_measurement)
        
        assert learner._learned_delay_secs == expected_ema
        store.async_save.assert_awaited_with({"learned_delay": expected_ema})

    @patch("custom_components.smart_climate.delay_learner.async_track_time_interval")
    async def test_start_and_stop_learning_cycle(self, mock_tracker, mock_hass_and_store):
        """Test that the time interval tracker is started and can be stopped."""
        hass, store = mock_hass_and_store
        mock_cancel = MagicMock()
        mock_tracker.return_value = mock_cancel
        
        # Mock the temp sensor to allow starting
        temp_state = MagicMock()
        temp_state.state = "22.0"
        hass.states.get.return_value = temp_state
        
        learner = DelayLearner(hass, "climate.test", "sensor.test_temp", store)
        learner.start_learning_cycle()
        
        mock_tracker.assert_called_once_with(hass, learner._check_stability_sync, CHECK_INTERVAL)
        assert learner._cancel_listener is not None
        
        learner.stop_learning_cycle()
        mock_cancel.assert_called_once()
        assert learner._cancel_listener is None

    @patch("custom_components.smart_climate.delay_learner.async_track_time_interval")
    async def test_learning_cycle_detects_stability(self, mock_tracker, mock_hass_and_store):
        """Test the full cycle: start -> monitor -> stabilize -> save -> stop."""
        hass, store = mock_hass_and_store
        
        # Mock hass.async_create_task 
        hass.async_create_task = MagicMock()
        
        # This allows us to control the callback from the tracker
        stability_check_callback = None
        
        def capture_callback(hass_ref, action, interval):
            nonlocal stability_check_callback
            stability_check_callback = action
            return MagicMock()  # Return a mock cancel function
        
        mock_tracker.side_effect = capture_callback
        
        with freeze_time("2023-01-01 12:00:00") as freezer:
            learner = DelayLearner(hass, "climate.test", "sensor.test_temp", store)
            
            # Initial state
            hass.states.get.return_value = MagicMock(state="25.0")
            learner.start_learning_cycle()
            assert stability_check_callback is not None

            # 1st check: Temp is changing
            freezer.tick(CHECK_INTERVAL)
            hass.states.get.return_value = MagicMock(state="24.5")  # 0.5 delta
            print(f"1st check - last_temp: {learner._last_temp}, new temp: 24.5")
            print(f"Current temp from _get_current_temp(): {learner._get_current_temp()}")
            stability_check_callback(freezer.time_to_freeze)
            print(f"After 1st check - last_temp: {learner._last_temp}")
            store.async_save.assert_not_awaited()  # Not saved yet

            # 2nd check: Temp is still changing
            freezer.tick(CHECK_INTERVAL)
            hass.states.get.return_value = MagicMock(state="24.1")  # 0.4 delta
            print(f"2nd check - last_temp: {learner._last_temp}, new temp: 24.1")
            stability_check_callback(freezer.time_to_freeze)
            print(f"After 2nd check - last_temp: {learner._last_temp}")
            store.async_save.assert_not_awaited()

            # 3rd check: Temp has stabilized
            freezer.tick(CHECK_INTERVAL)
            hass.states.get.return_value = MagicMock(state="24.05")  # 0.05 delta < STABILITY_THRESHOLD
            
            # Debug: Check the last temp value before calling
            print(f"3rd check - last_temp: {learner._last_temp}, new temp: 24.05")
            
            stability_check_callback(freezer.time_to_freeze)
            print(f"After 3rd check - last_temp: {learner._last_temp}")
            
            # Assertions
            expected_delay = int(3 * CHECK_INTERVAL.total_seconds()) + 5  # 45 seconds + 5 buffer = 50
            # Check that hass.async_create_task was called (indicates save was triggered)
            hass.async_create_task.assert_called_once()
            assert learner._cancel_listener is None  # Should have stopped

    @patch("custom_components.smart_climate.delay_learner.async_track_time_interval")
    @patch("homeassistant.util.dt.now")
    async def test_learning_cycle_times_out(self, mock_now, mock_tracker, mock_hass_and_store):
        """Test that the learning cycle stops after the timeout."""
        hass, store = mock_hass_and_store
        
        # Mock async_create_task
        hass.async_create_task = MagicMock()
        
        stability_check_callback = None
        
        def capture_callback(hass_ref, action, interval):
            nonlocal stability_check_callback
            stability_check_callback = action
            return MagicMock()
        
        mock_tracker.side_effect = capture_callback
        
        with freeze_time("2023-01-01 12:00:00") as freezer:
            # Mock now to return timezone-naive datetime for consistency
            mock_now.return_value = datetime(2023, 1, 1, 12, 0, 0)
            
            learner = DelayLearner(hass, "climate.test", "sensor.test_temp", store)
            hass.states.get.return_value = MagicMock(state="25.0")
            learner.start_learning_cycle()
            
            # Simulate time passing beyond the timeout
            freezer.tick(LEARNING_TIMEOUT + timedelta(seconds=1))
            
            # Temp is still changing, but it doesn't matter because it should time out
            hass.states.get.return_value = MagicMock(state="22.0")
            stability_check_callback(freezer.time_to_freeze)
            
            # Assertions
            hass.async_create_task.assert_not_called()  # Should not save on timeout
            assert learner._cancel_listener is None  # Should have stopped

    async def test_get_adaptive_delay_with_learned_value(self, mock_hass_and_store):
        """Test getting adaptive delay when learned value exists."""
        hass, store = mock_hass_and_store
        store.async_load.return_value = {"learned_delay": 75}
        
        learner = DelayLearner(hass, "climate.test", "sensor.test_temp", store)
        await learner.async_load()
        
        assert learner.get_adaptive_delay() == 75
        assert learner.get_adaptive_delay(30) == 75  # fallback ignored

    async def test_get_adaptive_delay_with_fallback(self, mock_hass_and_store):
        """Test getting adaptive delay when no learned value exists."""
        hass, store = mock_hass_and_store
        learner = DelayLearner(hass, "climate.test", "sensor.test_temp", store)
        
        assert learner.get_adaptive_delay() == 45  # default fallback
        assert learner.get_adaptive_delay(30) == 30  # custom fallback

    async def test_sensor_unavailable_during_start(self, mock_hass_and_store):
        """Test start learning cycle fails gracefully when sensor unavailable."""
        hass, store = mock_hass_and_store
        
        # Mock unavailable sensor
        hass.states.get.return_value = None
        
        learner = DelayLearner(hass, "climate.test", "sensor.test_temp", store)
        learner.start_learning_cycle()
        
        # Should not start learning
        assert learner._cancel_listener is None
        assert learner._learning_start_time is None

    async def test_sensor_state_unknown_during_start(self, mock_hass_and_store):
        """Test start learning cycle fails gracefully when sensor state unknown."""
        hass, store = mock_hass_and_store
        
        # Mock unknown sensor state
        temp_state = MagicMock()
        temp_state.state = "unknown"
        hass.states.get.return_value = temp_state
        
        learner = DelayLearner(hass, "climate.test", "sensor.test_temp", store)
        learner.start_learning_cycle()
        
        # Should not start learning
        assert learner._cancel_listener is None
        assert learner._learning_start_time is None

    @patch("custom_components.smart_climate.delay_learner.async_track_time_interval")
    async def test_sensor_unavailable_during_check(self, mock_tracker, mock_hass_and_store):
        """Test stability check continues gracefully when sensor becomes unavailable."""
        hass, store = mock_hass_and_store
        
        stability_check_callback = None
        
        def capture_callback(hass_ref, action, interval):
            nonlocal stability_check_callback
            stability_check_callback = action
            return MagicMock()
        
        mock_tracker.side_effect = capture_callback
        
        learner = DelayLearner(hass, "climate.test", "sensor.test_temp", store)
        
        # Start with available sensor
        hass.states.get.return_value = MagicMock(state="25.0")
        learner.start_learning_cycle()
        
        # Sensor becomes unavailable during check
        hass.states.get.return_value = None
        stability_check_callback(datetime.now())
        
        # Should continue learning (not stop)
        assert learner._cancel_listener is not None
        store.async_save.assert_not_awaited()

    async def test_duplicate_start_learning_cycle(self, mock_hass_and_store):
        """Test that starting learning cycle twice is handled gracefully."""
        hass, store = mock_hass_and_store
        
        # Mock available sensor
        temp_state = MagicMock()
        temp_state.state = "22.0"
        hass.states.get.return_value = temp_state
        
        with patch("custom_components.smart_climate.delay_learner.async_track_time_interval") as mock_tracker:
            mock_tracker.return_value = MagicMock()
            
            learner = DelayLearner(hass, "climate.test", "sensor.test_temp", store)
            learner.start_learning_cycle()
            learner.start_learning_cycle()  # Second call should be ignored
            
            # Should only call tracker once
            assert mock_tracker.call_count == 1

    async def test_stop_learning_cycle_when_not_started(self, mock_hass_and_store):
        """Test stopping learning cycle when not started is handled gracefully."""
        hass, store = mock_hass_and_store
        learner = DelayLearner(hass, "climate.test", "sensor.test_temp", store)
        
        # Should not raise exception
        learner.stop_learning_cycle()
        
        assert learner._cancel_listener is None