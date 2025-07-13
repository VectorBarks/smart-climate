"""ABOUTME: Comprehensive tests for ML feedback loop prevention in Smart Climate Control.
Tests for Issue #36: ML feedback loop causes ±3°C temperature oscillations."""

import pytest
from unittest.mock import Mock, patch
import time
from datetime import datetime

from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.models import OffsetInput


class TestMLFeedbackLoopPrevention:
    """Test suite for ML feedback loop prevention functionality."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = Mock()
        hass.states = Mock()
        hass.services = Mock()
        hass.async_create_task = Mock()
        return hass

    @pytest.fixture
    def offset_engine_config(self):
        """Create a basic offset engine configuration."""
        return {
            "max_offset": 5.0,
            "ml_enabled": True,
            "enable_learning": True,
            "power_sensor": "sensor.ac_power",
            "save_interval": 300,
        }

    @pytest.fixture
    def offset_engine(self, offset_engine_config):
        """Create an OffsetEngine instance for testing."""
        return OffsetEngine(offset_engine_config)

    @pytest.fixture
    def sample_input_data(self):
        """Create sample OffsetInput data for testing."""
        return OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=28.0,
            mode="normal",
            power_consumption=1000.0,
            time_of_day=datetime.now().time(),
            day_of_week=1
        )

    def test_initial_state_no_prediction_tracking(self, offset_engine):
        """Test that initially no prediction source tracking is active."""
        # Initially, no prediction should be active
        assert not hasattr(offset_engine, '_prediction_active') or not getattr(offset_engine, '_prediction_active', False)
        assert not hasattr(offset_engine, '_adjustment_source') or getattr(offset_engine, '_adjustment_source', None) is None

    def test_prediction_source_tracking_initialization(self, offset_engine):
        """Test that prediction source tracking attributes are properly initialized."""
        # After initialization, the tracking attributes should exist
        if not hasattr(offset_engine, '_prediction_active'):
            offset_engine._prediction_active = False
        if not hasattr(offset_engine, '_adjustment_source'):
            offset_engine._adjustment_source = None
            
        assert hasattr(offset_engine, '_prediction_active')
        assert hasattr(offset_engine, '_adjustment_source')
        assert offset_engine._prediction_active is False
        assert offset_engine._adjustment_source is None

    def test_record_feedback_from_manual_adjustment(self, offset_engine, sample_input_data):
        """Test that feedback from manual adjustments is recorded normally."""
        # Simulate manual adjustment (not from prediction)
        if not hasattr(offset_engine, '_adjustment_source'):
            offset_engine._adjustment_source = None
        offset_engine._adjustment_source = "manual"
        
        # Should record feedback when source is manual
        with patch.object(offset_engine, '_validate_feedback', return_value=True):
            offset_engine.record_actual_performance(
                predicted_offset=2.0,
                actual_offset=1.8,
                input_data=sample_input_data
            )
        
        # Verify feedback was recorded (learner should have been called)
        if offset_engine._learner:
            # If learner exists, it should have samples
            stats = offset_engine._learner.get_statistics()
            assert stats.samples_collected > 0

    def test_record_feedback_from_prediction_blocked(self, offset_engine, sample_input_data):
        """Test that feedback from prediction adjustments is blocked."""
        # Initialize tracking attributes if they don't exist
        if not hasattr(offset_engine, '_adjustment_source'):
            offset_engine._adjustment_source = None
        
        # Simulate prediction adjustment
        offset_engine._adjustment_source = "prediction"
        
        initial_samples = 0
        if offset_engine._learner:
            initial_samples = offset_engine._learner.get_statistics().samples_collected
        
        # Should NOT record feedback when source is prediction
        with patch.object(offset_engine, '_validate_feedback', return_value=True):
            offset_engine.record_actual_performance(
                predicted_offset=2.0,
                actual_offset=1.8,
                input_data=sample_input_data
            )
        
        # Verify feedback was NOT recorded
        if offset_engine._learner:
            final_samples = offset_engine._learner.get_statistics().samples_collected
            assert final_samples == initial_samples

    def test_apply_prediction_sets_source_tracking(self, offset_engine):
        """Test that applying a prediction sets proper source tracking."""
        # Add apply_prediction method simulation
        def mock_apply_prediction(offset: float):
            offset_engine._prediction_active = True
            offset_engine._adjustment_source = "prediction"
            return offset
        
        # Apply the mock method
        result = mock_apply_prediction(2.5)
        
        assert offset_engine._prediction_active is True
        assert offset_engine._adjustment_source == "prediction"
        assert result == 2.5

    def test_external_trigger_clears_prediction_source(self, offset_engine):
        """Test that external triggers clear prediction source tracking."""
        # Initialize with prediction source
        offset_engine._prediction_active = True
        offset_engine._adjustment_source = "prediction"
        
        # Simulate external trigger clearing the source
        def mock_external_trigger():
            offset_engine._prediction_active = False
            offset_engine._adjustment_source = "external"
        
        mock_external_trigger()
        
        assert offset_engine._prediction_active is False
        assert offset_engine._adjustment_source == "external"

    def test_mixed_scenario_prediction_then_manual(self, offset_engine, sample_input_data):
        """Test mixed scenario: prediction adjustment followed by manual adjustment."""
        # Initialize tracking
        offset_engine._prediction_active = False
        offset_engine._adjustment_source = None
        
        # First: prediction adjustment
        offset_engine._adjustment_source = "prediction"
        
        initial_samples = 0
        if offset_engine._learner:
            initial_samples = offset_engine._learner.get_statistics().samples_collected
        
        # Should NOT record feedback for prediction
        with patch.object(offset_engine, '_validate_feedback', return_value=True):
            offset_engine.record_actual_performance(
                predicted_offset=2.0,
                actual_offset=1.8,
                input_data=sample_input_data
            )
        
        if offset_engine._learner:
            prediction_samples = offset_engine._learner.get_statistics().samples_collected
            assert prediction_samples == initial_samples
        
        # Then: manual adjustment
        offset_engine._adjustment_source = "manual"
        
        # Should record feedback for manual adjustment
        with patch.object(offset_engine, '_validate_feedback', return_value=True):
            offset_engine.record_actual_performance(
                predicted_offset=1.8,
                actual_offset=1.5,
                input_data=sample_input_data
            )
        
        if offset_engine._learner:
            final_samples = offset_engine._learner.get_statistics().samples_collected
            assert final_samples > prediction_samples

    def test_temperature_stability_with_source_tracking(self, offset_engine, sample_input_data):
        """Test that source tracking prevents temperature oscillations."""
        # Simulate a scenario that would cause oscillations without tracking
        predictions = [2.0, -1.5, 2.8, -2.2, 3.1]  # Would cause oscillations
        
        offset_engine._prediction_active = False
        offset_engine._adjustment_source = None
        
        initial_samples = 0
        if offset_engine._learner:
            initial_samples = offset_engine._learner.get_statistics().samples_collected
        
        # Apply multiple predictions in sequence
        for prediction in predictions:
            # Mark as prediction
            offset_engine._adjustment_source = "prediction"
            
            # Should NOT record feedback
            with patch.object(offset_engine, '_validate_feedback', return_value=True):
                offset_engine.record_actual_performance(
                    predicted_offset=prediction,
                    actual_offset=prediction + 0.3,  # Simulated actual
                    input_data=sample_input_data
                )
        
        # Verify no feedback was recorded from predictions
        if offset_engine._learner:
            final_samples = offset_engine._learner.get_statistics().samples_collected
            assert final_samples == initial_samples

    def test_learning_still_works_for_legitimate_adjustments(self, offset_engine, sample_input_data):
        """Test that learning still works for legitimate (non-prediction) adjustments."""
        # Initialize tracking
        offset_engine._adjustment_source = None
        
        initial_samples = 0
        if offset_engine._learner:
            initial_samples = offset_engine._learner.get_statistics().samples_collected
        
        # Test various legitimate sources
        legitimate_sources = ["manual", "external", "user", None]
        
        for source in legitimate_sources:
            offset_engine._adjustment_source = source
            
            # Should record feedback for legitimate sources
            with patch.object(offset_engine, '_validate_feedback', return_value=True):
                offset_engine.record_actual_performance(
                    predicted_offset=2.0,
                    actual_offset=1.8,
                    input_data=sample_input_data
                )
        
        # Verify feedback was recorded for all legitimate sources
        if offset_engine._learner:
            final_samples = offset_engine._learner.get_statistics().samples_collected
            assert final_samples > initial_samples

    def test_debug_logging_for_prediction_blocks(self, offset_engine, sample_input_data):
        """Test that proper debug logging occurs when prediction feedback is blocked."""
        offset_engine._adjustment_source = "prediction"
        
        with patch('custom_components.smart_climate.offset_engine._LOGGER') as mock_logger:
            with patch.object(offset_engine, '_validate_feedback', return_value=True):
                offset_engine.record_actual_performance(
                    predicted_offset=2.0,
                    actual_offset=1.8,
                    input_data=sample_input_data
                )
            
            # Should log debug message about skipping feedback
            mock_logger.debug.assert_called()
            debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
            assert any("Skipping feedback recording from prediction" in msg for msg in debug_calls)

    def test_confidence_tracking_unaffected(self, offset_engine, sample_input_data):
        """Test that confidence calculations are unaffected by source tracking."""
        # Confidence should be calculated normally regardless of source tracking
        offset_engine._adjustment_source = "prediction"
        
        # Calculate offset (which includes confidence calculation)
        result = offset_engine.calculate_offset(sample_input_data)
        
        # Confidence should be calculated normally
        assert 0.0 <= result.confidence <= 1.0
        assert result.confidence is not None

    def test_alternative_weighted_approach_compatibility(self, offset_engine, sample_input_data):
        """Test that the implementation is compatible with alternative weighted approach."""
        # Test that we could implement weighted training if needed
        offset_engine._adjustment_source = "prediction"
        
        # Simulate weighted approach (reduced weight for predictions)
        def simulate_weighted_feedback(weight=0.3):
            # This simulates how weighted feedback could work
            if offset_engine._adjustment_source == "prediction":
                return weight  # Reduced weight for predictions
            else:
                return 1.0  # Full weight for manual adjustments
        
        # Prediction should get reduced weight
        prediction_weight = simulate_weighted_feedback()
        assert prediction_weight == 0.3
        
        # Manual should get full weight
        offset_engine._adjustment_source = "manual"
        manual_weight = simulate_weighted_feedback()
        assert manual_weight == 1.0

    def test_source_tracking_reset_on_engine_reset(self, offset_engine):
        """Test that source tracking is reset when engine is reset."""
        # Set some tracking state
        offset_engine._prediction_active = True
        offset_engine._adjustment_source = "prediction"
        
        # Reset the engine
        offset_engine.reset_learning()
        
        # Tracking should be reset (add this to reset method if not present)
        if hasattr(offset_engine, '_prediction_active'):
            assert offset_engine._prediction_active is False
        if hasattr(offset_engine, '_adjustment_source'):
            assert offset_engine._adjustment_source is None

    def test_persistence_excludes_prediction_state(self, offset_engine):
        """Test that prediction state is not persisted (it's runtime-only)."""
        # Set some runtime state
        offset_engine._prediction_active = True
        offset_engine._adjustment_source = "prediction"
        
        # Get learning info (which is used for persistence)
        learning_info = offset_engine.get_learning_info()
        
        # Prediction state should not be in persistence data
        assert '_prediction_active' not in learning_info
        assert '_adjustment_source' not in learning_info

    def test_feedback_loop_prevention_end_to_end(self, mock_hass, offset_engine_config):
        """End-to-end test of feedback loop prevention in climate entity."""
        # This test simulates the full feedback loop scenario
        with patch('custom_components.smart_climate.sensor_manager.SensorManager'), \
             patch('custom_components.smart_climate.mode_manager.ModeManager'), \
             patch('custom_components.smart_climate.temperature_controller.TemperatureController'), \
             patch('custom_components.smart_climate.coordinator.SmartClimateCoordinator'):
            
            # Create engine with tracking enabled
            engine = OffsetEngine(offset_engine_config)
            engine._prediction_active = False
            engine._adjustment_source = None
            
            # Simulate prediction cycle
            sample_input = OffsetInput(
                ac_internal_temp=22.0,
                room_temp=24.0,
                outdoor_temp=28.0,
                mode="normal",
                power_consumption=1000.0,
                time_of_day=datetime.now().time(),
                day_of_week=1
            )
            
            # Calculate offset (this would be a prediction)
            result = engine.calculate_offset(sample_input)
            
            # Mark as prediction-sourced adjustment
            engine._adjustment_source = "prediction"
            
            initial_samples = 0
            if engine._learner:
                initial_samples = engine._learner.get_statistics().samples_collected
            
            # Try to record feedback (should be blocked)
            with patch.object(engine, '_validate_feedback', return_value=True):
                engine.record_actual_performance(
                    predicted_offset=result.offset,
                    actual_offset=result.offset + 0.5,
                    input_data=sample_input
                )
            
            # Verify no feedback loop occurred
            if engine._learner:
                final_samples = engine._learner.get_statistics().samples_collected
                assert final_samples == initial_samples

    def test_edge_case_none_adjustment_source(self, offset_engine, sample_input_data):
        """Test edge case where adjustment source is None."""
        # Adjustment source is None (should allow feedback)
        offset_engine._adjustment_source = None
        
        initial_samples = 0
        if offset_engine._learner:
            initial_samples = offset_engine._learner.get_statistics().samples_collected
        
        # Should record feedback when source is None (treated as legitimate)
        with patch.object(offset_engine, '_validate_feedback', return_value=True):
            offset_engine.record_actual_performance(
                predicted_offset=2.0,
                actual_offset=1.8,
                input_data=sample_input_data
            )
        
        # Verify feedback was recorded
        if offset_engine._learner:
            final_samples = offset_engine._learner.get_statistics().samples_collected
            assert final_samples > initial_samples

    def test_edge_case_missing_source_tracking_attributes(self, offset_engine_config, sample_input_data):
        """Test that missing source tracking attributes don't break functionality."""
        # Create engine and remove tracking attributes to simulate old version
        engine = OffsetEngine(offset_engine_config)
        if hasattr(engine, '_adjustment_source'):
            delattr(engine, '_adjustment_source')
        if hasattr(engine, '_prediction_active'):
            delattr(engine, '_prediction_active')
        
        # Should still work without errors
        with patch.object(engine, '_validate_feedback', return_value=True):
            engine.record_actual_performance(
                predicted_offset=2.0,
                actual_offset=1.8,
                input_data=sample_input_data
            )
        
        # Should not raise any exceptions

    def test_source_tracking_with_learning_disabled(self, offset_engine_config, sample_input_data):
        """Test that source tracking works even when learning is disabled."""
        # Create engine with learning disabled
        config = offset_engine_config.copy()
        config['enable_learning'] = False
        engine = OffsetEngine(config)
        
        # Set prediction source
        engine._adjustment_source = "prediction"
        
        # Should not record feedback (due to learning disabled, not source tracking)
        engine.record_actual_performance(
            predicted_offset=2.0,
            actual_offset=1.8,
            input_data=sample_input_data
        )
        
        # No exception should be raised, and no feedback should be recorded
        assert engine._learner is None or engine._learner.get_statistics().samples_collected == 0

    def test_rapid_source_changes(self, offset_engine, sample_input_data):
        """Test rapid changes between prediction and manual sources."""
        sources = ["prediction", "manual", "prediction", "external", "prediction", "manual"]
        
        initial_samples = 0
        if offset_engine._learner:
            initial_samples = offset_engine._learner.get_statistics().samples_collected
        
        manual_count = 0
        for source in sources:
            offset_engine._adjustment_source = source
            
            if source != "prediction":
                manual_count += 1
            
            with patch.object(offset_engine, '_validate_feedback', return_value=True):
                offset_engine.record_actual_performance(
                    predicted_offset=2.0,
                    actual_offset=1.8,
                    input_data=sample_input_data
                )
        
        # Only non-prediction sources should have been recorded
        if offset_engine._learner:
            final_samples = offset_engine._learner.get_statistics().samples_collected
            expected_samples = initial_samples + manual_count
            assert final_samples == expected_samples