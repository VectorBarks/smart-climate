"""Tests for debug logging functionality in Smart Climate Control.

ABOUTME: Tests comprehensive debug logging across the learning system components.
Validates logging output, performance impact, and logging configuration.
"""

import logging
import pytest
import asyncio
from datetime import datetime, time
from unittest.mock import Mock, patch, call, MagicMock, AsyncMock
from io import StringIO

from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.lightweight_learner import LightweightOffsetLearner
from custom_components.smart_climate.switch import LearningSwitch
from custom_components.smart_climate.models import OffsetInput, OffsetResult


class LoggingCapture:
    """Helper class to capture and analyze logging output."""
    
    def __init__(self, logger_name: str):
        """Initialize logging capture for specified logger."""
        self.logger = logging.getLogger(logger_name)
        self.log_stream = StringIO()
        self.handler = logging.StreamHandler(self.log_stream)
        self.handler.setLevel(logging.DEBUG)
        self.formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
        self.handler.setFormatter(self.formatter)
        
    def __enter__(self):
        """Start capturing logs."""
        self.original_level = self.logger.level
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.handler)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop capturing logs."""
        self.logger.removeHandler(self.handler)
        self.logger.setLevel(self.original_level)
        
    def get_logs(self) -> str:
        """Get captured log output."""
        return self.log_stream.getvalue()
        
    def get_log_lines(self) -> list:
        """Get captured log lines as list."""
        return [line.strip() for line in self.get_logs().split('\n') if line.strip()]
        
    def assert_log_contains(self, level: str, message: str):
        """Assert that logs contain a specific level and message."""
        logs = self.get_logs()
        expected = f"{level}:custom_components.smart_climate"
        assert expected in logs, f"Expected '{expected}' in logs: {logs}"
        assert message in logs, f"Expected '{message}' in logs: {logs}"
        
    def assert_debug_logged(self, message: str):
        """Assert that a DEBUG message was logged."""
        self.assert_log_contains("DEBUG", message)
        
    def assert_info_logged(self, message: str):
        """Assert that an INFO message was logged."""
        self.assert_log_contains("INFO", message)
        
    def assert_warning_logged(self, message: str):
        """Assert that a WARNING message was logged."""
        self.assert_log_contains("WARNING", message)


class TestOffsetEngineDebugLogging:
    """Test debug logging for OffsetEngine operations."""
    
    def test_initialization_logging(self):
        """Test that OffsetEngine initialization is properly logged."""
        config = {
            "max_offset": 3.0,
            "ml_enabled": True,
            "enable_learning": True
        }
        
        with LoggingCapture("custom_components.smart_climate.offset_engine") as log_capture:
            engine = OffsetEngine(config)
            
            log_capture.assert_debug_logged("Learning enabled - LightweightOffsetLearner initialized")
            log_capture.assert_debug_logged("OffsetEngine initialized with max_offset=3.0, ml_enabled=True, learning_enabled=True")
    
    def test_learning_state_change_logging(self):
        """Test that learning state changes are properly logged."""
        config = {"enable_learning": False}
        engine = OffsetEngine(config)
        
        with LoggingCapture("custom_components.smart_climate.offset_engine") as log_capture:
            # Test enabling learning
            engine.enable_learning()
            log_capture.assert_info_logged("LightweightOffsetLearner initialized at runtime")
            log_capture.assert_info_logged("Offset learning has been enabled")
            
            # Test disabling learning
            engine.disable_learning()
            log_capture.assert_info_logged("Offset learning has been disabled")
    
    def test_offset_calculation_logging(self):
        """Test that offset calculations are properly logged."""
        config = {"enable_learning": True}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=25.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="normal",
            power_consumption=200.0,
            time_of_day=time(14, 30),
            day_of_week=1
        )
        
        with LoggingCapture("custom_components.smart_climate.offset_engine") as log_capture:
            result = engine.calculate_offset(input_data)
            
            # Should log the calculation details
            logs = log_capture.get_logs()
            assert "Calculated offset:" in logs
            assert f"{result.offset:.2f}" in logs
            assert f"clamped: {result.clamped}" in logs
            assert f"confidence: {result.confidence:.2f}" in logs
    
    def test_learning_sample_recording_logging(self):
        """Test that learning sample recording is properly logged."""
        config = {"enable_learning": True}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=25.0,
            room_temp=24.0,
            outdoor_temp=None,
            mode="normal",
            power_consumption=None,
            time_of_day=time(14, 30),
            day_of_week=1
        )
        
        with LoggingCapture("custom_components.smart_climate.offset_engine") as log_capture:
            engine.record_actual_performance(1.5, 1.2, input_data)
            
            log_capture.assert_debug_logged("Recorded learning sample: predicted=1.50, actual=1.20")
    
    def test_data_persistence_logging(self):
        """Test that data persistence operations are properly logged."""
        config = {"enable_learning": True}
        engine = OffsetEngine(config)
        
        # Mock data store
        mock_data_store = Mock()
        mock_data_store.async_save_learning_data = AsyncMock()
        mock_data_store.async_load_learning_data = AsyncMock(return_value=None)
        
        with LoggingCapture("custom_components.smart_climate.offset_engine") as log_capture:
            engine.set_data_store(mock_data_store)
            log_capture.assert_debug_logged("Data store configured for OffsetEngine")
            
            # Test save operation
            asyncio.run(engine.async_save_learning_data())
            log_capture.assert_debug_logged("Learning data and engine state saved successfully")
    
    def test_error_handling_logging(self):
        """Test that errors are properly logged with context."""
        config = {"enable_learning": True}
        engine = OffsetEngine(config)
        
        # Test error in offset calculation
        invalid_input = Mock()
        invalid_input.ac_internal_temp = "invalid"  # Invalid type
        
        with LoggingCapture("custom_components.smart_climate.offset_engine") as log_capture:
            result = engine.calculate_offset(invalid_input)
            
            # Should log error and return safe fallback
            log_capture.assert_log_contains("ERROR", "Error calculating offset:")
            assert result.offset == 0.0
            assert result.reason == "Error in calculation, using safe fallback"
    
    def test_periodic_save_logging(self):
        """Test that periodic save setup is properly logged."""
        config = {"enable_learning": True}
        engine = OffsetEngine(config)
        
        mock_hass = Mock()
        with patch('homeassistant.helpers.event.async_track_time_interval') as mock_track:
            mock_track.return_value = Mock()
            
            with LoggingCapture("custom_components.smart_climate.offset_engine") as log_capture:
                asyncio.run(engine.async_setup_periodic_save(mock_hass))
                
                log_capture.assert_debug_logged("Periodic learning data save configured (every 10 minutes)")


class TestSwitchDebugLogging:
    """Test debug logging for LearningSwitch operations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_config_entry = Mock()
        self.mock_config_entry.title = "Test Climate"
        self.mock_config_entry.unique_id = "test_unique_id"
        
        self.mock_offset_engine = Mock(spec=OffsetEngine)
        self.mock_offset_engine.is_learning_enabled = True
        self.mock_offset_engine.enable_learning = Mock()
        self.mock_offset_engine.disable_learning = Mock()
        self.mock_offset_engine.async_save_learning_data = Mock(return_value=asyncio.Future())
        self.mock_offset_engine.async_save_learning_data.return_value.set_result(None)
        self.mock_offset_engine.register_update_callback = Mock(return_value=Mock())
        self.mock_offset_engine.get_learning_info = Mock(return_value={
            "samples": 10,
            "accuracy": 0.85,
            "confidence": 0.75,
            "has_sufficient_data": True,
            "enabled": True
        })
    
    def test_switch_initialization_logging(self):
        """Test that switch initialization is properly logged."""
        with LoggingCapture("custom_components.smart_climate.switch") as log_capture:
            switch = LearningSwitch(
                self.mock_config_entry,
                self.mock_offset_engine,
                "Test Climate (climate.test)",
                "climate.test"
            )
            
            # Simulate async_added_to_hass
            asyncio.run(switch.async_added_to_hass())
            
            log_capture.assert_debug_logged("Registered update callback for learning switch")
    
    def test_switch_state_change_logging(self):
        """Test that switch state changes are properly logged."""
        switch = LearningSwitch(
            self.mock_config_entry,
            self.mock_offset_engine,
            "Test Climate (climate.test)",
            "climate.test"
        )
        
        with LoggingCapture("custom_components.smart_climate.switch") as log_capture:
            # Test enabling learning
            asyncio.run(switch.async_turn_on())
            
            log_capture.assert_debug_logged("Learning enabled via switch for climate.test")
            log_capture.assert_debug_logged("Learning data saved after switch state change for climate.test")
            
            # Test disabling learning
            asyncio.run(switch.async_turn_off())
            
            log_capture.assert_debug_logged("Learning disabled via switch for climate.test")
    
    def test_switch_error_handling_logging(self):
        """Test that switch errors are properly logged."""
        # Setup mock to raise exception
        self.mock_offset_engine.enable_learning.side_effect = Exception("Test error")
        
        switch = LearningSwitch(
            self.mock_config_entry,
            self.mock_offset_engine,
            "Test Climate (climate.test)",
            "climate.test"
        )
        
        with LoggingCapture("custom_components.smart_climate.switch") as log_capture:
            asyncio.run(switch.async_turn_on())
            
            log_capture.assert_log_contains("ERROR", "Failed to enable learning for climate.test: Test error")
    
    def test_switch_callback_update_logging(self):
        """Test that switch callback updates are properly logged."""
        switch = LearningSwitch(
            self.mock_config_entry,
            self.mock_offset_engine,
            "Test Climate (climate.test)",
            "climate.test"
        )
        
        # Mock async_write_ha_state
        switch.async_write_ha_state = Mock()
        
        with LoggingCapture("custom_components.smart_climate.switch") as log_capture:
            switch._handle_update()
            
            log_capture.assert_debug_logged("Learning switch state updated")
    
    def test_switch_attribute_error_logging(self):
        """Test that switch attribute errors are properly logged."""
        # Setup mock to raise exception when getting learning info
        self.mock_offset_engine.get_learning_info.side_effect = Exception("Attribute error")
        
        switch = LearningSwitch(
            self.mock_config_entry,
            self.mock_offset_engine,
            "Test Climate (climate.test)",
            "climate.test"
        )
        
        with LoggingCapture("custom_components.smart_climate.switch") as log_capture:
            attributes = switch.extra_state_attributes
            
            log_capture.assert_warning_logged("Failed to get learning info for switch attributes: Attribute error")
            assert attributes["error"] == "Attribute error"


class TestLightweightLearnerDebugLogging:
    """Test debug logging for LightweightOffsetLearner operations."""
    
    def test_learner_initialization_logging(self):
        """Test that learner initialization is properly logged."""
        with LoggingCapture("custom_components.smart_climate.lightweight_learner") as log_capture:
            learner = LightweightOffsetLearner(max_history=500, learning_rate=0.15)
            
            log_capture.assert_debug_logged("LightweightOffsetLearner initialized: max_history=500, learning_rate=0.150")
    
    def test_pattern_update_logging(self):
        """Test that pattern updates are properly logged."""
        learner = LightweightOffsetLearner()
        
        with LoggingCapture("custom_components.smart_climate.lightweight_learner") as log_capture:
            learner.update_pattern(
                offset=1.5,
                outdoor_temp=25.0,
                hour=14,
                power_state="cooling"
            )
            
            log_capture.assert_debug_logged("Pattern updated: hour=14, offset=1.50, outdoor_temp=25.0, power_state=cooling")
    
    def test_prediction_logging(self):
        """Test that predictions are properly logged."""
        learner = LightweightOffsetLearner()
        
        # Add some training data first
        learner.update_pattern(1.0, 25.0, 14, "cooling")
        learner.update_pattern(1.2, 26.0, 14, "cooling")
        
        with LoggingCapture("custom_components.smart_climate.lightweight_learner") as log_capture:
            prediction = learner.predict_offset(
                outdoor_temp=25.5,
                hour=14,
                power_state="cooling"
            )
            
            logs = log_capture.get_logs()
            assert "Offset predicted:" in logs
            assert f"{prediction.predicted_offset:.3f}" in logs
            assert f"confidence: {prediction.confidence:.2f}" in logs
            assert f"reason: {prediction.reason}" in logs
    
    def test_pattern_reset_logging(self):
        """Test that pattern reset is properly logged."""
        learner = LightweightOffsetLearner()
        
        with LoggingCapture("custom_components.smart_climate.lightweight_learner") as log_capture:
            learner.reset_learning()
            
            log_capture.assert_info_logged("All learning patterns have been reset")
    
    def test_pattern_loading_logging(self):
        """Test that pattern loading is properly logged."""
        learner = LightweightOffsetLearner()
        
        # Create valid pattern data
        patterns = {
            "version": "1.0",
            "time_patterns": {"14": 1.5},
            "time_pattern_counts": {"14": 5},
            "temp_correlation_data": [{"outdoor_temp": 25.0, "offset": 1.5}],
            "power_state_patterns": {"cooling": {"avg_offset": 1.2, "count": 3}},
            "sample_count": 5
        }
        
        with LoggingCapture("custom_components.smart_climate.lightweight_learner") as log_capture:
            learner.load_patterns(patterns)
            
            log_capture.assert_info_logged("Loaded patterns: 5 samples, 1 hours with data, 1 power states")
    
    def test_error_prediction_logging(self):
        """Test that prediction errors are properly logged."""
        learner = LightweightOffsetLearner()
        
        # Mock the _predict_from_temperature_correlation to raise an error
        with patch.object(learner, '_predict_from_temperature_correlation', side_effect=ValueError("Test error")):
            with LoggingCapture("custom_components.smart_climate.lightweight_learner") as log_capture:
                # Add some data to trigger temperature correlation
                learner.update_pattern(1.0, 25.0, 14, None)
                learner.update_pattern(1.2, 26.0, 14, None)
                
                prediction = learner.predict_offset(25.5, 14, None)
                
                log_capture.assert_warning_logged("Error in temperature correlation prediction: Test error")


class TestLoggingPerformance:
    """Test that logging doesn't significantly impact performance."""
    
    def test_logging_performance_impact(self):
        """Test that debug logging doesn't significantly slow down operations."""
        import time
        
        config = {"enable_learning": True}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=25.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="normal",
            power_consumption=200.0,
            time_of_day=time(14, 30),
            day_of_week=1
        )
        
        # Test without debug logging
        logger = logging.getLogger("custom_components.smart_climate.offset_engine")
        original_level = logger.level
        logger.setLevel(logging.WARNING)
        
        start_time = time.time()
        for _ in range(100):
            engine.calculate_offset(input_data)
        time_without_debug = time.time() - start_time
        
        # Test with debug logging
        logger.setLevel(logging.DEBUG)
        
        start_time = time.time()
        for _ in range(100):
            engine.calculate_offset(input_data)
        time_with_debug = time.time() - start_time
        
        # Restore original level
        logger.setLevel(original_level)
        
        # Debug logging shouldn't add more than 50% overhead
        overhead_ratio = time_with_debug / time_without_debug
        assert overhead_ratio < 1.5, f"Debug logging overhead too high: {overhead_ratio:.2f}x"
    
    def test_lazy_string_formatting(self):
        """Test that logging uses lazy string formatting for performance."""
        config = {"enable_learning": True}
        engine = OffsetEngine(config)
        
        # Mock the logger to verify lazy formatting is used
        with patch('custom_components.smart_climate.offset_engine._LOGGER') as mock_logger:
            engine.enable_learning()
            
            # Verify that debug calls use % formatting (lazy) not f-strings or .format()
            debug_calls = [call for call in mock_logger.debug.call_args_list]
            info_calls = [call for call in mock_logger.info.call_args_list]
            
            # At least one call should be made
            assert len(debug_calls) > 0 or len(info_calls) > 0
            
            # Check that calls use % formatting pattern
            for call in debug_calls + info_calls:
                args, kwargs = call
                if len(args) > 1:
                    # Multiple args indicates % formatting (lazy)
                    assert '%' in args[0], f"Expected % formatting in: {args[0]}"


class TestLoggingLevels:
    """Test that appropriate logging levels are used."""
    
    def test_debug_level_usage(self):
        """Test that DEBUG level is used for detailed operational info."""
        config = {"enable_learning": True}
        engine = OffsetEngine(config)
        
        with LoggingCapture("custom_components.smart_climate.offset_engine") as log_capture:
            input_data = OffsetInput(
                ac_internal_temp=25.0,
                room_temp=24.0,
                outdoor_temp=None,
                mode="normal",
                power_consumption=None,
                time_of_day=time(14, 30),
                day_of_week=1
            )
            
            engine.calculate_offset(input_data)
            
            # DEBUG should be used for calculation details
            logs = log_capture.get_logs()
            assert "DEBUG:" in logs
            assert "Calculated offset:" in logs
    
    def test_info_level_usage(self):
        """Test that INFO level is used for important state changes."""
        config = {"enable_learning": False}
        engine = OffsetEngine(config)
        
        with LoggingCapture("custom_components.smart_climate.offset_engine") as log_capture:
            engine.enable_learning()
            
            # INFO should be used for state changes
            log_capture.assert_info_logged("Offset learning has been enabled")
    
    def test_warning_level_usage(self):
        """Test that WARNING level is used for recoverable issues."""
        config = {"enable_learning": True}
        engine = OffsetEngine(config)
        
        with LoggingCapture("custom_components.smart_climate.offset_engine") as log_capture:
            # Trigger a warning by trying to record sample without learner data
            with patch.object(engine._learner, 'record_sample', side_effect=Exception("Test error")):
                input_data = OffsetInput(
                    ac_internal_temp=25.0,
                    room_temp=24.0,
                    outdoor_temp=None,
                    mode="normal",
                    power_consumption=None,
                    time_of_day=time(14, 30),
                    day_of_week=1
                )
                engine.record_actual_performance(1.0, 1.2, input_data)
            
            log_capture.assert_warning_logged("Failed to record learning sample: Test error")
    
    def test_error_level_usage(self):
        """Test that ERROR level is used for serious problems."""
        config = {"enable_learning": True}
        engine = OffsetEngine(config)
        
        with LoggingCapture("custom_components.smart_climate.offset_engine") as log_capture:
            # Trigger an error with invalid input
            invalid_input = Mock()
            invalid_input.ac_internal_temp = "invalid"
            
            result = engine.calculate_offset(invalid_input)
            
            # ERROR should be used for serious calculation failures
            logs = log_capture.get_logs()
            assert "ERROR:" in logs
            assert "Error calculating offset:" in logs


if __name__ == "__main__":
    pytest.main([__file__])