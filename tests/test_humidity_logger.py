"""
ABOUTME: Unit tests for HumidityLogger class - contextual diagnostic logging
Tests cover log message formatting, levels, categories, and contextual information
"""

import pytest
import logging
from unittest.mock import Mock, patch
from custom_components.smart_climate.humidity_monitor import HumidityLogger


class TestHumidityLogger:
    """Test suite for HumidityLogger contextual logging functionality."""
    
    def test_init_creates_three_logger_categories(self):
        """Test that __init__ creates loggers for humidity, humidity.ml, and humidity.comfort"""
        with patch('custom_components.smart_climate.humidity_monitor.logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            logger = HumidityLogger(level="DEBUG")
            
            # Should create three different loggers
            expected_calls = [
                ('smart_climate.humidity',),
                ('smart_climate.humidity.ml',),
                ('smart_climate.humidity.comfort',)
            ]
            mock_get_logger.assert_any_call('smart_climate.humidity')
            mock_get_logger.assert_any_call('smart_climate.humidity.ml')
            mock_get_logger.assert_any_call('smart_climate.humidity.comfort')
            assert mock_get_logger.call_count == 3
    
    def test_init_default_level_is_debug(self):
        """Test that default log level is DEBUG when not specified"""
        with patch('custom_components.smart_climate.humidity_monitor.logging.getLogger'):
            logger = HumidityLogger()
            # Should not raise exception and accept default level
            assert logger is not None
    
    def test_log_humidity_change_formats_message_correctly(self):
        """Test log_humidity_change creates properly formatted contextual message"""
        with patch('custom_components.smart_climate.humidity_monitor.logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            logger = HumidityLogger()
            
            # Test data matching spec format
            context = {
                'outdoor': 72.5,
                'heat_index': 24.1,
                'ml_offset': 0.3,
                'ml_conf_old': 92,
                'ml_conf_new': 89
            }
            
            logger.log_humidity_change(45.0, 48.0, context)
            
            # Verify the exact message format from spec
            expected_msg = ("Indoor humidity changed: 45.0% → 48.0% "
                           "(outdoor: 72.5%, heat index: 24.1°C, "
                           "ML impact: +0.3°C offset, "
                           "confidence: 92%→89%)")
            
            mock_logger.debug.assert_called_once_with(expected_msg)
    
    def test_log_humidity_change_handles_negative_ml_offset(self):
        """Test negative ML offset is formatted with minus sign"""
        with patch('custom_components.smart_climate.humidity_monitor.logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            logger = HumidityLogger()
            
            context = {
                'outdoor': 65.0,
                'heat_index': 22.0,
                'ml_offset': -0.5,  # Negative offset
                'ml_conf_old': 85,
                'ml_conf_new': 88
            }
            
            logger.log_humidity_change(50.0, 52.0, context)
            
            # Should contain "-0.5°C offset" in the message
            call_args = mock_logger.debug.call_args[0][0]
            assert "-0.5°C offset" in call_args
            assert "50.0% → 52.0%" in call_args
    
    def test_log_ml_impact_uses_ml_logger(self):
        """Test log_ml_impact uses the ML-specific logger"""
        with patch('custom_components.smart_climate.humidity_monitor.logging.getLogger') as mock_get_logger:
            # Create separate mocks for each logger
            mock_main_logger = Mock()
            mock_ml_logger = Mock()
            mock_comfort_logger = Mock()
            
            def get_logger_side_effect(name):
                if name == 'smart_climate.humidity':
                    return mock_main_logger
                elif name == 'smart_climate.humidity.ml':
                    return mock_ml_logger
                elif name == 'smart_climate.humidity.comfort':
                    return mock_comfort_logger
                return Mock()
            
            mock_get_logger.side_effect = get_logger_side_effect
            
            logger = HumidityLogger()
            
            # This method should exist and use the ML logger
            test_message = "ML impact calculation completed"
            logger.log_ml_impact(test_message)
            
            # Should call the ML logger, not the main logger
            mock_ml_logger.debug.assert_called_once_with(test_message)
            mock_main_logger.debug.assert_not_called()
    
    def test_log_comfort_event_uses_comfort_logger(self):
        """Test log_comfort_event uses the comfort-specific logger"""
        with patch('custom_components.smart_climate.humidity_monitor.logging.getLogger') as mock_get_logger:
            # Create separate mocks for each logger
            mock_main_logger = Mock()
            mock_ml_logger = Mock()
            mock_comfort_logger = Mock()
            
            def get_logger_side_effect(name):
                if name == 'smart_climate.humidity':
                    return mock_main_logger
                elif name == 'smart_climate.humidity.ml':
                    return mock_ml_logger
                elif name == 'smart_climate.humidity.comfort':
                    return mock_comfort_logger
                return Mock()
            
            mock_get_logger.side_effect = get_logger_side_effect
            
            logger = HumidityLogger()
            
            # This method should exist and use the comfort logger
            test_message = "Comfort level transition detected"
            logger.log_comfort_event(test_message)
            
            # Should call the comfort logger, not the main logger
            mock_comfort_logger.info.assert_called_once_with(test_message)
            mock_main_logger.debug.assert_not_called()
    
    def test_log_humidity_change_uses_debug_level(self):
        """Test that log_humidity_change uses DEBUG level by default"""
        with patch('custom_components.smart_climate.humidity_monitor.logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            logger = HumidityLogger()
            
            context = {
                'outdoor': 70.0,
                'heat_index': 25.0,
                'ml_offset': 0.1,
                'ml_conf_old': 90,
                'ml_conf_new': 91
            }
            
            logger.log_humidity_change(40.0, 41.0, context)
            
            # Should use debug level, not info
            mock_logger.debug.assert_called_once()
            mock_logger.info.assert_not_called()
    
    def test_comfort_event_uses_info_level(self):
        """Test that comfort events use INFO level (more important than regular humidity changes)"""
        with patch('custom_components.smart_climate.humidity_monitor.logging.getLogger') as mock_get_logger:
            mock_comfort_logger = Mock()
            
            def get_logger_side_effect(name):
                if name == 'smart_climate.humidity.comfort':
                    return mock_comfort_logger
                return Mock()
            
            mock_get_logger.side_effect = get_logger_side_effect
            
            logger = HumidityLogger()
            
            logger.log_comfort_event("Comfort transition")
            
            # Comfort events should use INFO level
            mock_comfort_logger.info.assert_called_once()
            mock_comfort_logger.debug.assert_not_called()
    
    def test_directional_arrows_in_format(self):
        """Test that directional arrows (→) are used correctly in messages"""
        with patch('custom_components.smart_climate.humidity_monitor.logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            logger = HumidityLogger()
            
            context = {
                'outdoor': 75.0,
                'heat_index': 26.5,
                'ml_offset': 0.8,
                'ml_conf_old': 88,
                'ml_conf_new': 85
            }
            
            logger.log_humidity_change(42.0, 47.0, context)
            
            call_args = mock_logger.debug.call_args[0][0]
            # Should contain two arrows: one for humidity change, one for confidence
            assert "42.0% → 47.0%" in call_args
            assert "88%→85%" in call_args
            assert call_args.count("→") == 2
    
    def test_percentage_and_temperature_formatting(self):
        """Test proper formatting of percentages and temperatures"""
        with patch('custom_components.smart_climate.humidity_monitor.logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            logger = HumidityLogger()
            
            context = {
                'outdoor': 68.75,  # Decimal percentage
                'heat_index': 23.45,  # Decimal temperature
                'ml_offset': 1.23,  # Decimal offset
                'ml_conf_old': 94,
                'ml_conf_new': 92
            }
            
            logger.log_humidity_change(43.25, 44.75, context)
            
            call_args = mock_logger.debug.call_args[0][0]
            # Check proper unit formatting
            assert "%" in call_args  # Humidity percentages
            assert "°C" in call_args  # Temperature units
            assert "68.75%" in call_args  # Outdoor humidity
            assert "23.45°C" in call_args  # Heat index
            assert "+1.2°C" in call_args  # ML offset (formatted to 1 decimal place)
    
    def test_integration_basic_usage(self):
        """Test basic integration without mocks - verifies real logger functionality"""
        logger = HumidityLogger("DEBUG")
        
        # Should not raise exceptions
        context = {
            'outdoor': 75.0,
            'heat_index': 26.0,
            'ml_offset': 0.5,
            'ml_conf_old': 90,
            'ml_conf_new': 88
        }
        
        # These should execute without errors
        logger.log_humidity_change(45.0, 47.0, context)
        logger.log_ml_impact("ML recalculation completed")
        logger.log_comfort_event("Comfort zone entered")
        
        # If we get here, the basic functionality works