"""Tests for learning data collection behavior in different HVAC modes.

These tests verify that the system properly skips learning in non-active HVAC modes
to prevent ML model poisoning with invalid data.
"""

import pytest
from datetime import time
from unittest.mock import Mock, patch, MagicMock
import logging

from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.models import OffsetInput, OffsetResult
from custom_components.smart_climate.lightweight_learner import LightweightOffsetLearner as EnhancedLightweightOffsetLearner


class TestHVACModeLearning:
    """Test suite for HVAC mode-aware learning behavior."""

    @pytest.fixture
    def mock_learner(self):
        """Create a mock learner with add_sample method."""
        learner = Mock(spec=EnhancedLightweightOffsetLearner)
        learner.add_sample = Mock()
        learner._enhanced_samples = []  # Mock some existing samples
        learner.get_statistics = Mock(return_value=Mock(
            samples_collected=5,
            avg_accuracy=0.8,
            last_sample_time=None
        ))
        return learner

    @pytest.fixture
    def engine_with_learning(self, mock_learner):
        """Create an OffsetEngine with learning enabled and mock learner."""
        config = {
            "max_offset": 5.0,
            "enable_learning": True,
            "power_sensor": "sensor.power",  # Enable hysteresis
            "validation_rate_limit_seconds": 0  # Disable rate limiting for tests
        }
        engine = OffsetEngine(config)
        engine._learner = mock_learner
        return engine

    def test_learning_skipped_in_fan_only_mode(self, engine_with_learning, mock_learner, caplog):
        """Test that record_actual_performance skips learning when HVAC mode is fan_only."""
        # Set up input data with fan_only mode
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=50.0,
            time_of_day=time(14, 30),
            day_of_week=1,
            hvac_mode="fan_only"  # This field needs to be added to OffsetInput
        )
        
        # Record performance
        with caplog.at_level(logging.DEBUG):
            engine_with_learning.record_actual_performance(
                predicted_offset=2.0,
                actual_offset=1.8,
                input_data=input_data
            )
        
        # Verify learner was NOT called
        mock_learner.add_sample.assert_not_called()
        
        # Verify proper debug logging
        assert "Skipping learning sample in fan_only mode" in caplog.text

    def test_learning_skipped_in_off_mode(self, engine_with_learning, mock_learner, caplog):
        """Test that record_actual_performance skips learning when HVAC mode is off."""
        # Set up input data with off mode
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=0.0,
            time_of_day=time(14, 30),
            day_of_week=1,
            hvac_mode="off"
        )
        
        # Record performance
        with caplog.at_level(logging.DEBUG):
            engine_with_learning.record_actual_performance(
                predicted_offset=2.0,
                actual_offset=1.8,
                input_data=input_data
            )
        
        # Verify learner was NOT called
        mock_learner.add_sample.assert_not_called()
        
        # Verify proper debug logging
        assert "Skipping learning sample in off mode" in caplog.text

    def test_learning_recorded_in_cool_mode(self, engine_with_learning, mock_learner):
        """Test that record_actual_performance records samples in cool mode."""
        # Set up input data with cool mode
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=1,
            hvac_mode="cool"
        )
        
        # Record performance
        engine_with_learning.record_actual_performance(
            predicted_offset=2.0,
            actual_offset=1.8,
            input_data=input_data
        )
        
        # Verify learner was called
        mock_learner.add_sample.assert_called_once()
        
        # Verify the call arguments
        call_args = mock_learner.add_sample.call_args[1]
        assert call_args['predicted'] == 2.0
        assert call_args['actual'] == 1.8
        assert call_args['ac_temp'] == 22.0
        assert call_args['room_temp'] == 20.0
        assert call_args['mode'] == "none"

    def test_learning_recorded_in_heat_mode(self, engine_with_learning, mock_learner):
        """Test that record_actual_performance records samples in heat mode."""
        # Set up input data with heat mode
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=10.0,
            mode="none",
            power_consumption=200.0,
            time_of_day=time(14, 30),
            day_of_week=1,
            hvac_mode="heat"
        )
        
        # Record performance
        engine_with_learning.record_actual_performance(
            predicted_offset=2.0,
            actual_offset=1.8,
            input_data=input_data
        )
        
        # Verify learner was called
        mock_learner.add_sample.assert_called_once()

    def test_learning_recorded_in_auto_mode(self, engine_with_learning, mock_learner):
        """Test that record_actual_performance records samples in auto mode."""
        # Set up input data with auto mode
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=15.0,
            mode="none",
            power_consumption=180.0,
            time_of_day=time(14, 30),
            day_of_week=1,
            hvac_mode="auto"
        )
        
        # Record performance
        engine_with_learning.record_actual_performance(
            predicted_offset=2.0,
            actual_offset=1.8,
            input_data=input_data
        )
        
        # Verify learner was called
        mock_learner.add_sample.assert_called_once()

    def test_learning_skipped_logging_message(self, engine_with_learning, mock_learner, caplog):
        """Test that proper debug logging occurs when learning is skipped."""
        # Set up input data with fan_only mode
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=50.0,
            time_of_day=time(14, 30),
            day_of_week=1,
            hvac_mode="fan_only"
        )
        
        # Record performance with debug logging
        with caplog.at_level(logging.DEBUG):
            engine_with_learning.record_actual_performance(
                predicted_offset=2.0,
                actual_offset=1.8,
                input_data=input_data
            )
        
        # Verify specific debug message
        log_records = [r for r in caplog.records if "Skipping learning sample" in r.message]
        assert len(log_records) == 1
        assert "fan_only" in log_records[0].message
        assert "predicted=2.00" in log_records[0].message
        assert "actual=1.80" in log_records[0].message

    def test_full_feedback_chain_from_climate_entity(self, engine_with_learning, mock_learner):
        """Test the full feedback chain from climate entity to offset engine.
        
        This test simulates how the climate entity calls record_actual_performance
        and verifies that HVAC mode filtering works end-to-end.
        """
        # Simulate climate entity collecting feedback in fan_only mode
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,  # Room warmer than AC
            outdoor_temp=30.0,
            mode="none",
            power_consumption=30.0,  # Low power for fan
            time_of_day=time(15, 0),
            day_of_week=3,
            hvac_mode="fan_only"
        )
        
        # Calculate actual offset as climate entity would
        actual_offset = input_data.ac_internal_temp - input_data.room_temp  # 22 - 24 = -2
        
        # Record performance as climate entity would
        engine_with_learning.record_actual_performance(
            predicted_offset=-1.5,  # System predicted less cooling needed
            actual_offset=actual_offset,  # But actual shows more cooling needed
            input_data=input_data
        )
        
        # Verify learner was NOT called in fan_only mode
        mock_learner.add_sample.assert_not_called()

    def test_hvac_mode_none_still_records_learning(self, engine_with_learning, mock_learner):
        """Test that when hvac_mode is None (not set), learning still records."""
        # Set up input data without hvac_mode field (backward compatibility)
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=1
            # Note: hvac_mode not set - simulating old behavior
        )
        
        # Add hvac_mode as None to simulate missing field
        input_data.hvac_mode = None
        
        # Record performance
        engine_with_learning.record_actual_performance(
            predicted_offset=2.0,
            actual_offset=1.8,
            input_data=input_data
        )
        
        # Verify learner was called (backward compatibility)
        mock_learner.add_sample.assert_called_once()

    def test_learning_skipped_in_dry_mode(self, engine_with_learning, mock_learner, caplog):
        """Test that record_actual_performance skips learning when HVAC mode is dry."""
        # Set up input data with dry mode
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=80.0,
            time_of_day=time(14, 30),
            day_of_week=1,
            hvac_mode="dry"
        )
        
        # Record performance
        with caplog.at_level(logging.DEBUG):
            engine_with_learning.record_actual_performance(
                predicted_offset=2.0,
                actual_offset=1.8,
                input_data=input_data
            )
        
        # Verify learner was NOT called
        mock_learner.add_sample.assert_not_called()
        
        # Verify proper debug logging
        assert "Skipping learning sample in dry mode" in caplog.text

    def test_learning_recorded_in_heat_cool_mode(self, engine_with_learning, mock_learner):
        """Test that record_actual_performance records samples in heat_cool mode."""
        # Set up input data with heat_cool mode
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=20.0,
            outdoor_temp=18.0,
            mode="none",
            power_consumption=160.0,
            time_of_day=time(14, 30),
            day_of_week=1,
            hvac_mode="heat_cool"
        )
        
        # Record performance
        engine_with_learning.record_actual_performance(
            predicted_offset=2.0,
            actual_offset=1.8,
            input_data=input_data
        )
        
        # Verify learner was called
        mock_learner.add_sample.assert_called_once()

    def test_multiple_modes_sequential_filtering(self, engine_with_learning, mock_learner):
        """Test sequential calls with different HVAC modes to ensure proper filtering."""
        # Test data for different modes
        test_cases = [
            ("cool", True),      # Should record
            ("heat", True),      # Should record
            ("fan_only", False), # Should NOT record
            ("auto", True),      # Should record
            ("off", False),      # Should NOT record
            ("dry", False),      # Should NOT record
            ("heat_cool", True), # Should record
        ]
        
        for hvac_mode, should_record in test_cases:
            # Reset mock
            mock_learner.add_sample.reset_mock()
            
            # Create input data for this mode
            input_data = OffsetInput(
                ac_internal_temp=22.0,
                room_temp=20.0,
                outdoor_temp=25.0,
                mode="none",
                power_consumption=150.0,
                time_of_day=time(14, 30),
                day_of_week=1,
                hvac_mode=hvac_mode
            )
            
            # Record performance
            engine_with_learning.record_actual_performance(
                predicted_offset=2.0,
                actual_offset=1.8,
                input_data=input_data
            )
            
            # Verify based on expected behavior
            if should_record:
                mock_learner.add_sample.assert_called_once()
            else:
                mock_learner.add_sample.assert_not_called()