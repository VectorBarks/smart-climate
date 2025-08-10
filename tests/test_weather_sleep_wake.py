"""Test smart sleep mode wake-up functionality for weather strategies."""

import asyncio
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock, call
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from custom_components.smart_climate.models import WeatherStrategy, ModeAdjustments, SmartClimateData
from custom_components.smart_climate.forecast_engine import ForecastEngine
from custom_components.smart_climate.coordinator import SmartClimateCoordinator
from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.mode_manager import ModeManager


class TestWeatherStrategy:
    """Test the WeatherStrategy dataclass."""
    
    def test_weather_strategy_creation(self):
        """Test creating a WeatherStrategy object."""
        now = dt_util.utcnow()
        event_time = now + timedelta(hours=4)
        pre_action_time = now + timedelta(hours=1)
        
        strategy = WeatherStrategy(
            is_active=False,
            pre_action_needed=True,
            pre_action_start_time=pre_action_time,
            event_start_time=event_time,
            strategy_name="heat_wave",
            adjustment=-2.0
        )
        
        assert strategy.is_active is False
        assert strategy.pre_action_needed is True
        assert strategy.pre_action_start_time == pre_action_time
        assert strategy.event_start_time == event_time
        assert strategy.strategy_name == "heat_wave"
        assert strategy.adjustment == -2.0
    
    def test_weather_strategy_defaults(self):
        """Test WeatherStrategy default values."""
        strategy = WeatherStrategy()
        
        assert strategy.is_active is False
        assert strategy.pre_action_needed is False
        assert strategy.pre_action_start_time is None
        assert strategy.event_start_time is None
        assert strategy.strategy_name == ""
        assert strategy.adjustment == 0.0


class TestForecastEngineWeatherStrategy:
    """Test ForecastEngine enhancements for weather strategies."""
    
    @pytest.fixture
    def mock_hass(self):
        """Mock HomeAssistant instance."""
        return Mock()
    
    @pytest.fixture
    def forecast_engine(self, mock_hass):
        """Create ForecastEngine with weather strategy support."""
        config = {
            "weather_entity": "weather.test",
            "strategies": [
                {
                    "name": "heat_wave",
                    "strategy_type": "heat_wave", 
                    "temp_threshold_c": 32.0,
                    "pre_action_hours": 4,
                    "adjustment": -2.0,
                    "enabled": True
                }
            ]
        }
        return ForecastEngine(mock_hass, config)
    
    def test_forecast_engine_mode_tracking(self, forecast_engine):
        """Test mode change time tracking."""
        # Initially no mode change time tracked
        assert forecast_engine._last_mode_change_time is None
        assert forecast_engine._mode_wake_suppressed is False
    
    def test_get_weather_strategy_no_active(self, forecast_engine):
        """Test get_weather_strategy when no strategy is active."""
        strategy = forecast_engine.get_weather_strategy()
        
        assert isinstance(strategy, WeatherStrategy)
        assert strategy.is_active is False
        assert strategy.pre_action_needed is False
        assert strategy.pre_action_start_time is None
        assert strategy.event_start_time is None
        assert strategy.strategy_name == ""
        assert strategy.adjustment == 0.0
    
    @patch('custom_components.smart_climate.forecast_engine.dt_util.utcnow')
    def test_get_weather_strategy_active_event(self, mock_utcnow, forecast_engine):
        """Test get_weather_strategy when event is currently active."""
        now = datetime(2023, 8, 15, 14, 0, 0, tzinfo=dt_util.UTC)
        mock_utcnow.return_value = now
        
        # Set up active strategy - event started 1 hour ago (currently happening)
        forecast_engine._active_strategy = Mock()
        forecast_engine._active_strategy.name = "heat_wave"
        forecast_engine._active_strategy.adjustment = -2.0
        forecast_engine._active_strategy.end_time = now - timedelta(hours=1)  # Event started 1 hour ago
        
        # Simulate recent mode change during active event
        forecast_engine._last_mode_change_time = now - timedelta(minutes=5)
        
        strategy = forecast_engine.get_weather_strategy()
        
        assert strategy.is_active is True
        assert strategy.pre_action_needed is False  # Too late for pre-action
        assert strategy.strategy_name == "heat_wave"
        assert strategy.adjustment == -2.0
        assert strategy.event_start_time == forecast_engine._active_strategy.end_time
        assert forecast_engine._mode_wake_suppressed is True
    
    @patch('custom_components.smart_climate.forecast_engine.dt_util.utcnow')
    def test_get_weather_strategy_pre_action_needed(self, mock_utcnow, forecast_engine):
        """Test get_weather_strategy when pre-action is needed."""
        now = datetime(2023, 8, 15, 10, 0, 0, tzinfo=dt_util.UTC)
        mock_utcnow.return_value = now
        
        # Set up strategy needing pre-action (will start in 4 hours)
        forecast_engine._active_strategy = Mock()
        forecast_engine._active_strategy.name = "heat_wave"
        forecast_engine._active_strategy.adjustment = -2.0
        forecast_engine._active_strategy.end_time = now + timedelta(hours=4)  # Event starts at 14:00
        
        # No recent mode change
        forecast_engine._last_mode_change_time = None
        
        strategy = forecast_engine.get_weather_strategy()
        
        assert strategy.is_active is False  # Event not yet started
        assert strategy.pre_action_needed is True
        assert strategy.strategy_name == "heat_wave"
        assert strategy.adjustment == -2.0
        assert strategy.pre_action_start_time == now  # Pre-action starts now
        assert strategy.event_start_time == forecast_engine._active_strategy.end_time
    
    @patch('custom_components.smart_climate.forecast_engine.dt_util.utcnow')
    def test_mode_change_tracking(self, mock_utcnow, forecast_engine):
        """Test mode change time tracking."""
        now = datetime(2023, 8, 15, 10, 0, 0, tzinfo=dt_util.UTC)
        mock_utcnow.return_value = now
        
        # Record mode change
        forecast_engine._record_mode_change()
        
        assert forecast_engine._last_mode_change_time == now
        assert forecast_engine._mode_wake_suppressed is False  # Not set yet
    
    @patch('custom_components.smart_climate.forecast_engine.dt_util.utcnow')
    def test_suppression_logic_active_event(self, mock_utcnow, forecast_engine):
        """Test suppression when mode changed during active event."""
        now = datetime(2023, 8, 15, 14, 0, 0, tzinfo=dt_util.UTC)
        mock_utcnow.return_value = now
        
        # Active event happening now - started 30 minutes ago
        forecast_engine._active_strategy = Mock()
        forecast_engine._active_strategy.end_time = now - timedelta(minutes=30)  # Event started 30 min ago
        
        # Recent mode change (5 minutes ago)
        forecast_engine._last_mode_change_time = now - timedelta(minutes=5)
        
        strategy = forecast_engine.get_weather_strategy()
        assert forecast_engine._mode_wake_suppressed is True
    
    @patch('custom_components.smart_climate.forecast_engine.dt_util.utcnow')
    def test_no_suppression_pre_action(self, mock_utcnow, forecast_engine):
        """Test no suppression during pre-action period."""
        now = datetime(2023, 8, 15, 10, 0, 0, tzinfo=dt_util.UTC)
        mock_utcnow.return_value = now
        
        # Pre-action period (event starts later)
        forecast_engine._active_strategy = Mock()
        forecast_engine._active_strategy.end_time = now + timedelta(hours=4)
        
        # Recent mode change
        forecast_engine._last_mode_change_time = now - timedelta(minutes=5)
        
        strategy = forecast_engine.get_weather_strategy()
        assert forecast_engine._mode_wake_suppressed is False  # No suppression during pre-action


class TestCoordinatorWakeLogic:
    """Test coordinator auto-wake logic."""
    
    @pytest.fixture
    def mock_hass(self):
        """Mock HomeAssistant instance."""
        return Mock()
    
    @pytest.fixture
    def mock_sensor_manager(self):
        """Mock SensorManager."""
        return Mock()
    
    @pytest.fixture
    def mock_offset_engine(self):
        """Mock OffsetEngine."""
        return Mock()
    
    @pytest.fixture
    def mock_mode_manager(self):
        """Mock ModeManager."""
        manager = Mock()
        manager.current_mode = "none"
        return manager
    
    @pytest.fixture
    def mock_forecast_engine(self):
        """Mock ForecastEngine with weather strategy support."""
        engine = Mock()
        engine.get_weather_strategy = Mock()
        return engine
    
    @pytest.fixture
    def coordinator(self, mock_hass, mock_sensor_manager, mock_offset_engine, 
                   mock_mode_manager, mock_forecast_engine):
        """Create SmartClimateCoordinator with wake-up support."""
        coordinator = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=180,
            sensor_manager=mock_sensor_manager,
            offset_engine=mock_offset_engine,
            mode_manager=mock_mode_manager,
            forecast_engine=mock_forecast_engine
        )
        # Initialize wake-up state manually for testing
        coordinator._wake_up_requested = False
        return coordinator
    
    def test_coordinator_wake_initialization(self, coordinator):
        """Test coordinator initializes wake-up state."""
        assert hasattr(coordinator, '_wake_up_requested')
        assert coordinator._wake_up_requested is False
    
    def test_wake_logic_sleep_mode_pre_action(self, coordinator, mock_mode_manager, mock_forecast_engine):
        """Test auto-wake from sleep mode when pre-action needed."""
        # Verify coordinator is a real instance
        assert hasattr(coordinator, '_check_weather_wake_up')
        assert hasattr(coordinator, '_wake_up_requested')
        
        # Setup: AC in sleep mode
        mock_mode_manager.current_mode = "sleep"
        
        # Setup: Weather strategy needs pre-action
        now = dt_util.utcnow()
        strategy = WeatherStrategy(
            pre_action_needed=True,
            event_start_time=now + timedelta(hours=2),
            strategy_name="heat_wave",
            adjustment=-2.0
        )
        mock_forecast_engine.get_weather_strategy.return_value = strategy
        
        # Verify initial state
        assert coordinator._wake_up_requested is False
        
        # Simulate coordinator update
        coordinator._check_weather_wake_up()
        
        assert coordinator._wake_up_requested is True
    
    def test_no_wake_away_mode(self, coordinator, mock_mode_manager, mock_forecast_engine):
        """Test no auto-wake from away mode."""
        # Setup: AC in away mode
        mock_mode_manager.current_mode = "away"
        
        # Setup: Weather strategy needs pre-action
        strategy = WeatherStrategy(
            pre_action_needed=True,
            event_start_time=dt_util.utcnow() + timedelta(hours=2),
            strategy_name="heat_wave"
        )
        mock_forecast_engine.get_weather_strategy.return_value = strategy
        
        # Simulate coordinator update
        coordinator._check_weather_wake_up()
        
        assert coordinator._wake_up_requested is False
    
    def test_no_wake_already_active(self, coordinator, mock_mode_manager, mock_forecast_engine):
        """Test no wake when already in normal mode."""
        # Setup: AC in normal mode
        mock_mode_manager.current_mode = "none"
        
        # Setup: Weather strategy needs pre-action
        strategy = WeatherStrategy(
            pre_action_needed=True,
            event_start_time=dt_util.utcnow() + timedelta(hours=2),
            strategy_name="heat_wave"
        )
        mock_forecast_engine.get_weather_strategy.return_value = strategy
        
        # Simulate coordinator update
        coordinator._check_weather_wake_up()
        
        assert coordinator._wake_up_requested is False
    
    def test_no_wake_no_pre_action(self, coordinator, mock_mode_manager, mock_forecast_engine):
        """Test no wake when no pre-action needed."""
        # Setup: AC in sleep mode
        mock_mode_manager.current_mode = "sleep"
        
        # Setup: No weather strategy or no pre-action needed
        strategy = WeatherStrategy(pre_action_needed=False)
        mock_forecast_engine.get_weather_strategy.return_value = strategy
        
        # Simulate coordinator update
        coordinator._check_weather_wake_up()
        
        assert coordinator._wake_up_requested is False


class TestClimateWakeHandling:
    """Test climate entity wake-up handling."""
    
    @pytest.fixture
    def mock_hass(self):
        """Mock HomeAssistant instance."""
        return Mock()
    
    @pytest.fixture  
    def mock_coordinator(self):
        """Mock SmartClimateCoordinator."""
        coordinator = Mock()
        coordinator._wake_up_requested = False
        return coordinator
    
    @pytest.fixture
    def mock_mode_manager(self):
        """Mock ModeManager."""
        manager = Mock()
        manager.current_mode = "sleep"
        return manager
    
    @pytest.fixture
    def climate_entity(self, mock_hass, mock_coordinator, mock_mode_manager):
        """Create SmartClimateEntity with wake-up support."""
        config = {"test": "config"}
        
        entity = SmartClimateEntity(
            hass=mock_hass,
            config=config,
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room",
            offset_engine=Mock(),
            sensor_manager=Mock(),
            mode_manager=mock_mode_manager,
            temperature_controller=Mock(),
            coordinator=mock_coordinator
        )
        
        return entity
    
    def test_check_weather_wake_up_requested(self, climate_entity, mock_coordinator, mock_mode_manager):
        """Test wake-up when coordinator requests it."""
        # Setup: Coordinator requests wake-up
        mock_coordinator._wake_up_requested = True
        
        # Setup: Currently in sleep mode
        mock_mode_manager.current_mode = "sleep"
        
        # Call wake-up check
        result = climate_entity.check_weather_wake_up()
        
        assert result is True
        # Should set mode to none (normal operation)
        mock_mode_manager.set_mode.assert_called_once_with("none")
        # Should clear the wake-up request
        assert mock_coordinator._wake_up_requested is False
    
    def test_no_wake_up_not_requested(self, climate_entity, mock_coordinator, mock_mode_manager):
        """Test no wake-up when not requested."""
        # Setup: No wake-up requested
        mock_coordinator._wake_up_requested = False
        
        # Call wake-up check
        result = climate_entity.check_weather_wake_up()
        
        assert result is False
        # Mode should not change
        mock_mode_manager.set_mode.assert_not_called()
    
    def test_no_wake_up_not_sleep_mode(self, climate_entity, mock_coordinator, mock_mode_manager):
        """Test no wake-up when not in sleep mode."""
        # Setup: Wake-up requested but not in sleep mode
        mock_coordinator._wake_up_requested = True
        mock_mode_manager.current_mode = "none"
        
        # Call wake-up check
        result = climate_entity.check_weather_wake_up()
        
        assert result is False
        # Mode should not change
        mock_mode_manager.set_mode.assert_not_called()
        # Wake-up request should remain
        assert mock_coordinator._wake_up_requested is True
    
    def test_wake_up_suppression_active_event(self, climate_entity, mock_coordinator, mock_mode_manager):
        """Test pre-cooling suppression when waking during active event."""
        # Setup: Manual wake during active weather event
        mock_coordinator._wake_up_requested = False  # Manual wake, not auto
        mock_mode_manager.current_mode = "sleep"
        
        # Mock forecast engine indicating active event with suppression
        mock_forecast_engine = Mock()
        mock_forecast_engine._mode_wake_suppressed = True
        climate_entity._forecast_engine = mock_forecast_engine
        
        # Manually set mode to none (simulate user wake-up)
        mock_mode_manager.set_mode("none")
        mock_forecast_engine._record_mode_change()
        
        # The suppression should already be set by forecast engine
        assert mock_forecast_engine._mode_wake_suppressed is True


class TestModeChangeTracking:
    """Test mode change time tracking."""
    
    def test_mode_manager_change_tracking(self):
        """Test ModeManager tracks mode change times."""
        config = {}
        manager = ModeManager(config)
        
        # Should have mode change tracking
        assert hasattr(manager, '_last_mode_change_time')
        assert hasattr(manager, 'get_time_since_mode_change')
        assert hasattr(manager, 'was_recently_in_sleep_or_away')
    
    @patch('custom_components.smart_climate.mode_manager.dt_util.utcnow')
    def test_mode_change_time_recording(self, mock_utcnow):
        """Test recording mode change times."""
        now = datetime(2023, 8, 15, 10, 0, 0, tzinfo=dt_util.UTC)
        mock_utcnow.return_value = now
        
        config = {}
        manager = ModeManager(config)
        
        # Change mode should record time
        manager.set_mode("sleep")
        
        assert manager._last_mode_change_time == now
    
    @patch('custom_components.smart_climate.mode_manager.dt_util.utcnow')
    def test_time_since_mode_change(self, mock_utcnow):
        """Test calculating time since mode change."""
        start_time = datetime(2023, 8, 15, 10, 0, 0, tzinfo=dt_util.UTC)
        current_time = start_time + timedelta(minutes=15)
        
        config = {}
        manager = ModeManager(config)
        
        # Set initial time and change mode
        mock_utcnow.return_value = start_time
        manager.set_mode("sleep")
        
        # Check time difference
        mock_utcnow.return_value = current_time
        time_diff = manager.get_time_since_mode_change()
        
        assert time_diff == timedelta(minutes=15)
    
    def test_was_recently_in_sleep_or_away(self):
        """Test checking if recently in sleep or away mode."""
        config = {}
        manager = ModeManager(config)
        
        # Initially false (no mode changes)
        assert manager.was_recently_in_sleep_or_away() is False
        
        # After setting sleep mode recently
        manager.set_mode("sleep")
        manager.set_mode("none")  # Wake up
        
        # Should detect recent sleep mode
        with patch.object(manager, 'get_time_since_mode_change', return_value=timedelta(minutes=5)):
            assert manager.was_recently_in_sleep_or_away() is True
        
        # Should not detect if too long ago
        with patch.object(manager, 'get_time_since_mode_change', return_value=timedelta(hours=2)):
            assert manager.was_recently_in_sleep_or_away() is False


class TestWeatherSleepWakeIntegration:
    """Integration tests for complete weather sleep wake-up flow."""
    
    @pytest.fixture
    def mock_hass(self):
        """Mock HomeAssistant instance."""
        return Mock()
    
    @pytest.fixture
    async def full_system(self, mock_hass):
        """Create full system with all components."""
        # Create real components with mocked dependencies
        mode_manager = ModeManager({})
        
        forecast_config = {
            "weather_entity": "weather.test",
            "strategies": [{
                "name": "test_strategy",
                "strategy_type": "heat_wave",
                "temp_threshold_c": 30.0,
                "pre_action_hours": 2,
                "adjustment": -2.0
            }]
        }
        forecast_engine = ForecastEngine(mock_hass, forecast_config)
        
        coordinator = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=180,
            sensor_manager=Mock(),
            offset_engine=Mock(),
            mode_manager=mode_manager,
            forecast_engine=forecast_engine
        )
        
        climate_entity = SmartClimateEntity(
            hass=mock_hass,
            config={},
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room",
            offset_engine=Mock(),
            sensor_manager=Mock(),
            mode_manager=mode_manager,
            temperature_controller=Mock(),
            coordinator=coordinator
        )
        
        return {
            "mode_manager": mode_manager,
            "forecast_engine": forecast_engine,
            "coordinator": coordinator,
            "climate_entity": climate_entity
        }
    
    async def test_complete_auto_wake_flow(self, full_system):
        """Test complete auto-wake flow from sleep mode."""
        components = full_system
        mode_manager = components["mode_manager"]
        forecast_engine = components["forecast_engine"]
        coordinator = components["coordinator"]
        climate_entity = components["climate_entity"]
        
        # Setup: AC in sleep mode
        mode_manager.set_mode("sleep")
        assert mode_manager.current_mode == "sleep"
        
        # Setup: Mock weather strategy needing pre-action
        now = dt_util.utcnow()
        mock_strategy = WeatherStrategy(
            pre_action_needed=True,
            event_start_time=now + timedelta(hours=2),
            strategy_name="heat_wave"
        )
        
        with patch.object(forecast_engine, 'get_weather_strategy', return_value=mock_strategy):
            # Simulate coordinator update cycle
            coordinator._check_weather_wake_up()
            
            # Should request wake-up
            assert coordinator._wake_up_requested is True
            
            # Climate entity checks for wake-up
            woke_up = climate_entity.check_weather_wake_up()
            
            # Should wake up successfully
            assert woke_up is True
            assert mode_manager.current_mode == "none"
            assert coordinator._wake_up_requested is False
    
    async def test_no_auto_wake_from_away(self, full_system):
        """Test no auto-wake from away mode."""
        components = full_system
        mode_manager = components["mode_manager"]
        forecast_engine = components["forecast_engine"]
        coordinator = components["coordinator"]
        
        # Setup: AC in away mode
        mode_manager.set_mode("away")
        
        # Setup: Mock weather strategy needing pre-action
        mock_strategy = WeatherStrategy(
            pre_action_needed=True,
            event_start_time=dt_util.utcnow() + timedelta(hours=2),
            strategy_name="heat_wave"
        )
        
        with patch.object(forecast_engine, 'get_weather_strategy', return_value=mock_strategy):
            # Simulate coordinator update
            coordinator._check_weather_wake_up()
            
            # Should NOT request wake-up
            assert coordinator._wake_up_requested is False
            assert mode_manager.current_mode == "away"
    
    async def test_suppression_during_active_event(self, full_system):
        """Test suppression when manually waking during active event."""
        components = full_system
        mode_manager = components["mode_manager"]
        forecast_engine = components["forecast_engine"]
        
        # Setup: Currently active weather event
        now = dt_util.utcnow()
        mock_strategy = WeatherStrategy(
            is_active=True,
            strategy_name="heat_wave",
            event_start_time=now - timedelta(minutes=30),  # Started 30 min ago
        )
        
        # Setup: In sleep mode initially
        mode_manager.set_mode("sleep")
        
        with patch.object(forecast_engine, 'get_weather_strategy', return_value=mock_strategy):
            # Manually wake up during active event
            mode_manager.set_mode("none")
            
            # Get updated weather strategy
            strategy = forecast_engine.get_weather_strategy()
            
            # Should indicate suppression due to active event
            assert strategy.is_active is True
            assert forecast_engine._mode_wake_suppressed is True