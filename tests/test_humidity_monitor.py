"""Tests for HumidityMonitor component."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from custom_components.smart_climate.humidity_monitor import HumidityMonitor


class TestHumidityMonitor:
    """Test suite for HumidityMonitor class."""

    def test_init_with_default_config(self):
        """Test HumidityMonitor initialization with default thresholds."""
        mock_hass = Mock()
        mock_sensor_manager = Mock()
        mock_offset_engine = Mock()
        config = {}
        
        monitor = HumidityMonitor(mock_hass, mock_sensor_manager, mock_offset_engine, config)
        
        assert monitor._hass == mock_hass
        assert monitor._sensor_manager == mock_sensor_manager
        assert monitor._offset_engine == mock_offset_engine
        assert monitor._config == config
        assert monitor._last_values == {}
        
        # Check default thresholds
        thresholds = monitor._thresholds
        assert thresholds['humidity_change'] == 2.0  # 2% humidity change
        assert thresholds['heat_index_warning'] == 26.0  # 26°C
        assert thresholds['dew_point_warning'] == 2.0  # 2°C
        assert thresholds['differential_significant'] == 25.0  # 25%

    def test_init_with_custom_config(self):
        """Test HumidityMonitor initialization with custom thresholds."""
        mock_hass = Mock()
        mock_sensor_manager = Mock()
        mock_offset_engine = Mock()
        config = {
            'humidity_change_threshold': 1.5,
            'heat_index_warning': 28.0,
            'dew_point_warning': 1.0,
            'differential_significant': 30.0
        }
        
        monitor = HumidityMonitor(mock_hass, mock_sensor_manager, mock_offset_engine, config)
        
        thresholds = monitor._thresholds
        assert thresholds['humidity_change'] == 1.5
        assert thresholds['heat_index_warning'] == 28.0
        assert thresholds['dew_point_warning'] == 1.0
        assert thresholds['differential_significant'] == 30.0

    def test_check_triggers_humidity_change(self):
        """Test threshold detection for humidity changes."""
        mock_hass = Mock()
        mock_sensor_manager = Mock()
        mock_offset_engine = Mock()
        config = {}
        
        monitor = HumidityMonitor(mock_hass, mock_sensor_manager, mock_offset_engine, config)
        monitor._last_values = {'indoor_humidity': 45.0}
        
        new_values = {'indoor_humidity': 48.0}  # 3% change, above 2% threshold
        
        triggers = monitor.check_triggers(new_values)
        
        assert len(triggers) == 1
        assert 'humidity_change' in triggers

    def test_check_triggers_no_change(self):
        """Test no triggers when changes are below thresholds."""
        mock_hass = Mock()
        mock_sensor_manager = Mock()
        mock_offset_engine = Mock()
        config = {}
        
        monitor = HumidityMonitor(mock_hass, mock_sensor_manager, mock_offset_engine, config)
        monitor._last_values = {'indoor_humidity': 45.0}
        
        new_values = {'indoor_humidity': 46.0}  # 1% change, below 2% threshold
        
        triggers = monitor.check_triggers(new_values)
        
        assert len(triggers) == 0

    def test_check_triggers_heat_index_warning(self):
        """Test threshold detection for heat index warnings."""
        mock_hass = Mock()
        mock_sensor_manager = Mock()
        mock_offset_engine = Mock()
        config = {}
        
        monitor = HumidityMonitor(mock_hass, mock_sensor_manager, mock_offset_engine, config)
        monitor._last_values = {'heat_index': 25.0}
        
        new_values = {'heat_index': 27.0}  # Above 26°C threshold
        
        triggers = monitor.check_triggers(new_values)
        
        assert len(triggers) == 1
        assert 'heat_index_warning' in triggers

    def test_check_triggers_dew_point_warning(self):
        """Test threshold detection for dew point warnings."""
        mock_hass = Mock()
        mock_sensor_manager = Mock()
        mock_offset_engine = Mock()
        config = {}
        
        monitor = HumidityMonitor(mock_hass, mock_sensor_manager, mock_offset_engine, config)
        monitor._last_values = {
            'indoor_temp': 22.0,
            'indoor_dew_point': 18.0
        }
        
        new_values = {
            'indoor_temp': 22.0,
            'indoor_dew_point': 20.5  # Dew point within 2°C of temp
        }
        
        triggers = monitor.check_triggers(new_values)
        
        assert len(triggers) == 1
        assert 'dew_point_warning' in triggers

    def test_check_triggers_differential_significant(self):
        """Test threshold detection for significant humidity differential."""
        mock_hass = Mock()
        mock_sensor_manager = Mock()
        mock_offset_engine = Mock()
        config = {}
        
        monitor = HumidityMonitor(mock_hass, mock_sensor_manager, mock_offset_engine, config)
        monitor._last_values = {'humidity_differential': 20.0}
        
        new_values = {'humidity_differential': 30.0}  # Above 25% threshold
        
        triggers = monitor.check_triggers(new_values)
        
        assert len(triggers) == 1
        assert 'differential_significant' in triggers

    def test_check_triggers_multiple_events(self):
        """Test detection of multiple threshold crossings in single update."""
        mock_hass = Mock()
        mock_sensor_manager = Mock()
        mock_offset_engine = Mock()
        config = {}
        
        monitor = HumidityMonitor(mock_hass, mock_sensor_manager, mock_offset_engine, config)
        monitor._last_values = {
            'indoor_humidity': 45.0,
            'heat_index': 25.0,
            'humidity_differential': 20.0
        }
        
        new_values = {
            'indoor_humidity': 50.0,  # 5% change > 2% threshold
            'heat_index': 27.0,  # Above 26°C threshold
            'humidity_differential': 30.0  # Above 25% threshold
        }
        
        triggers = monitor.check_triggers(new_values)
        
        assert len(triggers) == 3
        assert 'humidity_change' in triggers
        assert 'heat_index_warning' in triggers
        assert 'differential_significant' in triggers

    @pytest.mark.asyncio
    async def test_async_update(self):
        """Test async update processing and trigger detection."""
        mock_hass = Mock()
        mock_sensor_manager = Mock()
        mock_offset_engine = Mock()
        config = {}
        
        monitor = HumidityMonitor(mock_hass, mock_sensor_manager, mock_offset_engine, config)
        
        # Mock sensor data
        mock_sensor_manager.get_indoor_humidity.return_value = 48.0
        mock_sensor_manager.get_outdoor_humidity.return_value = 70.0
        
        # Set up previous values to trigger a change
        monitor._last_values = {'indoor_humidity': 45.0}
        
        result = await monitor.async_update()
        
        # Should return triggered events
        assert 'triggered_events' in result
        assert len(result['triggered_events']) >= 1

    def test_check_triggers_with_none_values(self):
        """Test threshold checking handles None values gracefully."""
        mock_hass = Mock()
        mock_sensor_manager = Mock()
        mock_offset_engine = Mock()
        config = {}
        
        monitor = HumidityMonitor(mock_hass, mock_sensor_manager, mock_offset_engine, config)
        monitor._last_values = {'indoor_humidity': 45.0}
        
        new_values = {'indoor_humidity': None}  # None value
        
        triggers = monitor.check_triggers(new_values)
        
        # Should not trigger anything with None values
        assert len(triggers) == 0

    def test_check_triggers_first_reading(self):
        """Test threshold checking with no previous values."""
        mock_hass = Mock()
        mock_sensor_manager = Mock()
        mock_offset_engine = Mock()
        config = {}
        
        monitor = HumidityMonitor(mock_hass, mock_sensor_manager, mock_offset_engine, config)
        # Empty last_values (first reading)
        monitor._last_values = {}
        
        new_values = {'indoor_humidity': 45.0}
        
        triggers = monitor.check_triggers(new_values)
        
        # Should not trigger on first reading (no comparison possible)
        assert len(triggers) == 0

    def test_thresholds_customization(self):
        """Test that all thresholds can be customized."""
        mock_hass = Mock()
        mock_sensor_manager = Mock()
        mock_offset_engine = Mock()
        config = {
            'humidity_change_threshold': 3.0,
            'heat_index_warning': 25.0,
            'dew_point_warning': 1.5,
            'differential_significant': 35.0
        }
        
        monitor = HumidityMonitor(mock_hass, mock_sensor_manager, mock_offset_engine, config)
        
        thresholds = monitor._thresholds
        assert thresholds['humidity_change'] == 3.0
        assert thresholds['heat_index_warning'] == 25.0
        assert thresholds['dew_point_warning'] == 1.5
        assert thresholds['differential_significant'] == 35.0