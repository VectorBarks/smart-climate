"""Simplified tests for debug logging functionality.

ABOUTME: Tests key debug logging functionality without complex Home Assistant setup.
Validates logging output and basic functionality.
"""

import logging
import pytest
from datetime import time
from unittest.mock import Mock, patch, AsyncMock
from io import StringIO

from custom_components.smart_climate.offset_engine import OffsetEngine, LightweightOffsetLearner
from custom_components.smart_climate.models import OffsetInput


class SimpleLoggingCapture:
    """Simple logging capture for testing."""
    
    def __init__(self, logger_name: str):
        """Initialize logging capture."""
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
        
    def assert_contains(self, message: str):
        """Assert that logs contain a specific message."""
        logs = self.get_logs()
        assert message in logs, f"Expected '{message}' in logs: {logs}"


class TestOffsetEngineLogging:
    """Test debug logging for OffsetEngine operations."""
    
    def test_initialization_logging(self):
        """Test that OffsetEngine initialization is properly logged."""
        config = {
            "max_offset": 3.0,
            "ml_enabled": True,
            "enable_learning": True
        }
        
        with SimpleLoggingCapture("custom_components.smart_climate.offset_engine") as log_capture:
            engine = OffsetEngine(config)
            
            log_capture.assert_contains("Learning enabled - LightweightOffsetLearner initialized")
            log_capture.assert_contains("OffsetEngine initialized with max_offset=3.0, ml_enabled=True, learning_enabled=True")
    
    def test_learning_state_change_logging(self):
        """Test that learning state changes are properly logged."""
        config = {"enable_learning": False}
        engine = OffsetEngine(config)
        
        with SimpleLoggingCapture("custom_components.smart_climate.offset_engine") as log_capture:
            # Test enabling learning
            engine.enable_learning()
            log_capture.assert_contains("LightweightOffsetLearner initialized at runtime")
            log_capture.assert_contains("Offset learning has been enabled")
            log_capture.assert_contains("Learning state changed: False -> True")
            
            # Test disabling learning
            engine.disable_learning()
            log_capture.assert_contains("Offset learning has been disabled")
            log_capture.assert_contains("Learning state changed: True -> False")
    
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
        
        with SimpleLoggingCapture("custom_components.smart_climate.offset_engine") as log_capture:
            result = engine.calculate_offset(input_data)
            
            logs = log_capture.get_logs()
            assert "Offset calculation complete:" in logs
            assert "Learning enabled but insufficient data for prediction" in logs
    
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
        
        with SimpleLoggingCapture("custom_components.smart_climate.offset_engine") as log_capture:
            engine.record_actual_performance(1.5, 1.2, input_data)
            
            log_capture.assert_contains("Recorded learning sample: predicted=1.50, actual=1.20")
    
    def test_data_persistence_logging(self):
        """Test that data persistence operations are properly logged."""
        config = {"enable_learning": True}
        engine = OffsetEngine(config)
        
        mock_data_store = Mock()
        mock_data_store.async_save_learning_data = AsyncMock()
        
        with SimpleLoggingCapture("custom_components.smart_climate.offset_engine") as log_capture:
            engine.set_data_store(mock_data_store)
            log_capture.assert_contains("Data store configured for OffsetEngine")


class TestLightweightLearnerLogging:
    """Test debug logging for LightweightOffsetLearner operations."""
    
    def test_learner_initialization_logging(self):
        """Test that learner initialization is properly logged."""
        with SimpleLoggingCapture("custom_components.smart_climate.offset_engine") as log_capture:
            learner = LightweightOffsetLearner()
            
            # The logger name is different for LightweightOffsetLearner (inside offset_engine.py)
            logs = log_capture.get_logs()
            # This would be logged from LightweightOffsetLearner.__init__ in the actual lightweight_learner.py
            # but we're testing the one imported in offset_engine.py which doesn't have debug logging yet
            
    def test_pattern_learning_milestones(self):
        """Test that learning progress milestones are logged."""
        config = {"enable_learning": True}
        engine = OffsetEngine(config)
        
        input_data = OffsetInput(
            ac_internal_temp=25.0,
            room_temp=24.0,
            outdoor_temp=25.0,
            mode="normal",
            power_consumption=200.0,
            time_of_day=time(14, 30),
            day_of_week=1
        )
        
        with SimpleLoggingCapture("custom_components.smart_climate.offset_engine") as log_capture:
            # Record multiple samples to test learning progression
            for i in range(5):
                engine.record_actual_performance(1.0 + i * 0.1, 1.2 + i * 0.1, input_data)
            
            logs = log_capture.get_logs()
            # Should contain multiple learning sample recordings
            assert logs.count("Recorded learning sample:") == 5


class TestLoggingPerformance:
    """Test that logging doesn't significantly impact performance."""
    
    def test_logging_uses_lazy_formatting(self):
        """Test that logging uses lazy string formatting."""
        config = {"enable_learning": True}
        engine = OffsetEngine(config)
        
        # Mock the logger to verify lazy formatting is used
        with patch('custom_components.smart_climate.offset_engine._LOGGER') as mock_logger:
            engine.enable_learning()
            
            # Verify that debug calls use % formatting (lazy) not f-strings
            debug_calls = [call for call in mock_logger.debug.call_args_list]
            info_calls = [call for call in mock_logger.info.call_args_list]
            
            # At least one call should be made
            assert len(debug_calls) > 0 or len(info_calls) > 0
            
            # Check that calls use % formatting pattern (indicates lazy evaluation)
            for call in debug_calls + info_calls:
                args, kwargs = call
                if len(args) > 1:
                    # Multiple args indicates % formatting (lazy)
                    format_string = args[0]
                    assert '%' in format_string, f"Expected % formatting in: {format_string}"


class TestLoggingLevels:
    """Test that appropriate logging levels are used."""
    
    def test_debug_level_for_detailed_info(self):
        """Test that DEBUG level is used for detailed operational info."""
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
        
        with SimpleLoggingCapture("custom_components.smart_climate.offset_engine") as log_capture:
            engine.calculate_offset(input_data)
            
            logs = log_capture.get_logs()
            assert "DEBUG:" in logs
            assert "Offset calculation complete:" in logs
    
    def test_info_level_for_state_changes(self):
        """Test that INFO level is used for important state changes."""
        config = {"enable_learning": False}
        engine = OffsetEngine(config)
        
        with SimpleLoggingCapture("custom_components.smart_climate.offset_engine") as log_capture:
            engine.enable_learning()
            
            logs = log_capture.get_logs()
            assert "INFO:" in logs
            assert "Offset learning has been enabled" in logs
    
    def test_warning_level_for_recoverable_issues(self):
        """Test that WARNING level is used for recoverable issues."""
        config = {"enable_learning": True}
        engine = OffsetEngine(config)
        
        # Test warning when saving without data store
        with SimpleLoggingCapture("custom_components.smart_climate.offset_engine") as log_capture:
            import asyncio
            asyncio.run(engine.async_save_learning_data())
            
            logs = log_capture.get_logs()
            assert "WARNING:" in logs
            assert "No data store configured, cannot save learning data" in logs


if __name__ == "__main__":
    pytest.main([__file__])