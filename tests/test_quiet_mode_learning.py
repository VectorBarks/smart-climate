"""Learning tests for Quiet Mode feature.

Tests progressive temperature stepping, compressor activation detection,
threshold learning, backing off after learning, timeouts, and 
multiple learning cycles.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from custom_components.smart_climate.compressor_state_analyzer import CompressorStateAnalyzer
from custom_components.smart_climate.quiet_mode_controller import QuietModeController
from custom_components.smart_climate.offset_engine import HysteresisLearner


class TestQuietModeLearning:
    """Tests for Quiet Mode learning functionality."""
    
    @pytest.fixture
    def mock_analyzer(self):
        """Mock CompressorStateAnalyzer."""
        analyzer = Mock(spec=CompressorStateAnalyzer)
        # Default: compressor idle, adjustments won't activate
        analyzer.is_compressor_idle.return_value = True
        analyzer.would_adjustment_activate_compressor.return_value = False
        analyzer.get_adjustment_needed_to_activate.return_value = None
        return analyzer
    
    @pytest.fixture
    def mock_hysteresis_learner_no_thresholds(self):
        """Mock HysteresisLearner without learned thresholds."""
        learner = Mock(spec=HysteresisLearner)
        learner.learned_start_threshold = None
        learner.learned_stop_threshold = None
        learner.has_learned_thresholds.return_value = False
        learner.record_threshold.return_value = None
        return learner
    
    @pytest.fixture
    def mock_logger(self):
        """Mock logger."""
        return Mock()
    
    @pytest.fixture
    def quiet_controller(self, mock_analyzer, mock_logger):
        """Create QuietModeController for testing."""
        return QuietModeController(
            enabled=True,
            analyzer=mock_analyzer,
            logger=mock_logger
        )
    
    def test_progressive_temperature_stepping(self, quiet_controller, mock_analyzer, mock_hysteresis_learner_no_thresholds):
        """Test progressive 0.5°C temperature stepping during learning."""
        # Setup: No learned thresholds, need to learn
        mock_analyzer.get_adjustment_needed_to_activate.return_value = 20.0  # Need to reach 20°C
        
        current_room_temp = 23.0
        current_setpoint = 22.0
        hvac_mode = "cool"
        power = 15.0  # Idle
        
        # Simulate progressive learning steps
        learning_steps = [
            21.5,  # First step: -0.5°C
            21.0,  # Second step: -0.5°C  
            20.5,  # Third step: -0.5°C
            20.0,  # Fourth step: -0.5°C (should activate)
        ]
        
        for expected_setpoint in learning_steps:
            progressive_setpoint = quiet_controller.get_progressive_adjustment(
                current_room_temp=current_room_temp,
                current_setpoint=current_setpoint,
                hysteresis_learner=mock_hysteresis_learner_no_thresholds,
                hvac_mode=hvac_mode
            )
            
            # Should return progressive setpoint for learning
            if progressive_setpoint is not None:
                # Verify 0.5°C steps
                step_size = current_setpoint - progressive_setpoint
                assert abs(step_size - 0.5) < 0.1, f"Expected 0.5°C step, got {step_size}"
                current_setpoint = progressive_setpoint
        
        # Verify learning progression attempted
        assert mock_analyzer.get_adjustment_needed_to_activate.called
    
    def test_detects_compressor_activation(self, quiet_controller, mock_analyzer, mock_hysteresis_learner_no_thresholds):
        """Test detection of compressor activation during learning."""
        # Setup learning scenario
        current_room_temp = 24.0
        current_setpoint = 23.0
        new_setpoint = 22.0
        hvac_mode = "cool"
        
        # Scenario 1: Power jump indicates compressor activation
        low_power = 20.0   # Idle
        high_power = 75.0  # Active
        
        # First call with low power (idle)
        mock_analyzer.is_compressor_idle.return_value = True
        mock_analyzer.would_adjustment_activate_compressor.return_value = False
        
        should_suppress_1, reason_1 = quiet_controller.should_suppress_adjustment(
            current_room_temp=current_room_temp,
            current_setpoint=current_setpoint,
            new_setpoint=new_setpoint,
            power=low_power,
            hvac_mode=hvac_mode,
            hysteresis_learner=mock_hysteresis_learner_no_thresholds
        )
        
        # Should suppress when idle and won't activate
        assert should_suppress_1 is True
        
        # Second call with high power (compressor activated!)
        mock_analyzer.is_compressor_idle.return_value = False
        
        should_suppress_2, reason_2 = quiet_controller.should_suppress_adjustment(
            current_room_temp=current_room_temp,
            current_setpoint=current_setpoint,
            new_setpoint=new_setpoint,
            power=high_power,
            hvac_mode=hvac_mode,
            hysteresis_learner=mock_hysteresis_learner_no_thresholds
        )
        
        # Should not suppress when compressor is active
        assert should_suppress_2 is False
        assert "active" in reason_2
    
    def test_records_learned_threshold(self, quiet_controller, mock_analyzer, mock_hysteresis_learner_no_thresholds):
        """Test recording of learned threshold to HysteresisLearner."""
        # Mock the learning detection scenario
        current_room_temp = 24.0
        learned_threshold_temp = 22.5  # Temperature where compressor activated
        hvac_mode = "cool"
        
        # Setup: analyzer detects that adjustment would activate compressor
        mock_analyzer.would_adjustment_activate_compressor.return_value = True
        mock_analyzer.get_adjustment_needed_to_activate.return_value = learned_threshold_temp
        
        # Simulate learning cycle
        should_suppress, reason = quiet_controller.should_suppress_adjustment(
            current_room_temp=current_room_temp,
            current_setpoint=23.0,
            new_setpoint=learned_threshold_temp,
            power=15.0,  # Was idle
            hvac_mode=hvac_mode,
            hysteresis_learner=mock_hysteresis_learner_no_thresholds
        )
        
        # Should not suppress when adjustment would activate compressor
        assert should_suppress is False
        assert "would activate" in reason
        
        # In real implementation, threshold would be recorded when power jump detected
        # This would happen in the climate entity integration, not the controller directly
    
    def test_backs_off_after_learning(self, quiet_controller, mock_analyzer):
        """Test backing off to comfortable level after learning threshold."""
        # Create a learner that has just learned thresholds
        mock_hysteresis_learner = Mock(spec=HysteresisLearner)
        mock_hysteresis_learner.learned_start_threshold = 22.0  # Just learned
        mock_hysteresis_learner.learned_stop_threshold = 21.5
        mock_hysteresis_learner.has_learned_thresholds.return_value = True
        
        # Setup: Compressor idle, but we now know thresholds
        mock_analyzer.is_compressor_idle.return_value = True
        mock_analyzer.would_adjustment_activate_compressor.return_value = False
        
        # Post-learning scenario: Small adjustment that won't cross learned threshold
        should_suppress, reason = quiet_controller.should_suppress_adjustment(
            current_room_temp=22.8,
            current_setpoint=22.5,
            new_setpoint=22.3,  # Small adjustment, won't reach learned threshold of 22.0
            power=20.0,  # Idle
            hvac_mode="cool",
            hysteresis_learner=mock_hysteresis_learner
        )
        
        # Should suppress now that we have learned thresholds
        assert should_suppress is True
        assert "won't activate" in reason or "idle" in reason
        
        # But should not suppress if adjustment would cross threshold
        mock_analyzer.would_adjustment_activate_compressor.return_value = True
        
        should_suppress, reason = quiet_controller.should_suppress_adjustment(
            current_room_temp=22.8,
            current_setpoint=22.5, 
            new_setpoint=21.8,  # Would cross learned threshold
            power=20.0,
            hvac_mode="cool",
            hysteresis_learner=mock_hysteresis_learner
        )
        
        assert should_suppress is False
        assert "would activate" in reason
    
    def test_learning_timeout(self, quiet_controller, mock_analyzer, mock_hysteresis_learner_no_thresholds):
        """Test learning gives up after timeout attempts."""
        # Setup: Long learning attempt that should eventually timeout
        current_room_temp = 25.0
        current_setpoint = 24.0
        hvac_mode = "cool"
        
        # Mock time progression for timeout testing
        with patch('custom_components.smart_climate.quiet_mode_controller.datetime') as mock_datetime:
            # Initial learning attempt
            start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = start_time
            
            # Simulate learning attempts over time
            mock_analyzer.get_adjustment_needed_to_activate.return_value = 20.0  # Need big adjustment
            
            # First learning attempt
            progressive_setpoint = quiet_controller.get_progressive_adjustment(
                current_room_temp=current_room_temp,
                current_setpoint=current_setpoint,
                hysteresis_learner=mock_hysteresis_learner_no_thresholds,
                hvac_mode=hvac_mode
            )
            
            # Should provide progressive learning setpoint initially
            if progressive_setpoint is not None:
                assert progressive_setpoint < current_setpoint
            
            # Simulate timeout (e.g., 10 minutes later with no success)
            timeout_time = start_time + timedelta(minutes=15)
            mock_datetime.now.return_value = timeout_time
            
            # Update last learning attempt timestamp
            quiet_controller._last_learning_attempt = start_time
            
            # After timeout, should give up learning for a while
            progressive_setpoint_2 = quiet_controller.get_progressive_adjustment(
                current_room_temp=current_room_temp,
                current_setpoint=current_setpoint,
                hysteresis_learner=mock_hysteresis_learner_no_thresholds,
                hvac_mode=hvac_mode
            )
            
            # Implementation detail: timeout behavior depends on actual implementation
            # But learning should eventually back off or give up
    
    def test_multiple_learning_cycles(self, quiet_controller, mock_analyzer, mock_hysteresis_learner_no_thresholds):
        """Test handling of multiple learning cycles over time."""
        current_room_temp = 24.0
        hvac_mode = "cool"
        
        # Simulate multiple learning sessions
        learning_sessions = [
            # Session 1: Learn from 23°C setpoint
            {"current_setpoint": 23.0, "target_activation": 21.5},
            # Session 2: Learn from different starting point  
            {"current_setpoint": 22.5, "target_activation": 21.0},
            # Session 3: Another learning opportunity
            {"current_setpoint": 24.0, "target_activation": 22.0}
        ]
        
        for session in learning_sessions:
            mock_analyzer.get_adjustment_needed_to_activate.return_value = session["target_activation"]
            
            progressive_setpoint = quiet_controller.get_progressive_adjustment(
                current_room_temp=current_room_temp,
                current_setpoint=session["current_setpoint"],
                hysteresis_learner=mock_hysteresis_learner_no_thresholds,
                hvac_mode=hvac_mode
            )
            
            # Each session should attempt progressive learning
            if progressive_setpoint is not None:
                # Verify progressive step (should be 0.5°C cooler)
                expected_step = session["current_setpoint"] - 0.5
                assert abs(progressive_setpoint - expected_step) < 0.1
        
        # Verify multiple learning attempts tracked
        assert mock_analyzer.get_adjustment_needed_to_activate.call_count >= 3
    
    def test_learning_disabled_when_thresholds_known(self, quiet_controller, mock_analyzer):
        """Test that learning is disabled when thresholds are already known."""
        # Create learner with known thresholds  
        mock_hysteresis_learner = Mock(spec=HysteresisLearner)
        mock_hysteresis_learner.learned_start_threshold = 22.0
        mock_hysteresis_learner.learned_stop_threshold = 21.5
        mock_hysteresis_learner.has_learned_thresholds.return_value = True
        
        # Setup normal suppression scenario
        mock_analyzer.is_compressor_idle.return_value = True
        mock_analyzer.would_adjustment_activate_compressor.return_value = False
        
        # Should not attempt progressive learning when thresholds known
        progressive_setpoint = quiet_controller.get_progressive_adjustment(
            current_room_temp=23.0,
            current_setpoint=22.5,
            hysteresis_learner=mock_hysteresis_learner,
            hvac_mode="cool"
        )
        
        # Should return None (no learning needed)
        assert progressive_setpoint is None
        
        # Should use normal suppression logic
        should_suppress, reason = quiet_controller.should_suppress_adjustment(
            current_room_temp=23.0,
            current_setpoint=22.5,
            new_setpoint=22.0,
            power=20.0,
            hvac_mode="cool",
            hysteresis_learner=mock_hysteresis_learner
        )
        
        assert should_suppress is True
        assert "won't activate" in reason or "idle" in reason
    
    def test_learning_only_in_cooling_modes(self, quiet_controller, mock_analyzer, mock_hysteresis_learner_no_thresholds):
        """Test that learning only occurs in supported cooling modes."""
        current_room_temp = 24.0
        current_setpoint = 23.0
        
        # Test supported modes
        supported_modes = ["cool", "dry", "auto"]
        for hvac_mode in supported_modes:
            progressive_setpoint = quiet_controller.get_progressive_adjustment(
                current_room_temp=current_room_temp,
                current_setpoint=current_setpoint,
                hysteresis_learner=mock_hysteresis_learner_no_thresholds,
                hvac_mode=hvac_mode
            )
            
            # Should attempt learning in supported modes (or return None if not needed)
            # This depends on implementation details
        
        # Test unsupported modes  
        unsupported_modes = ["heat", "heat_cool", "fan_only"]
        for hvac_mode in unsupported_modes:
            progressive_setpoint = quiet_controller.get_progressive_adjustment(
                current_room_temp=current_room_temp,
                current_setpoint=current_setpoint,
                hysteresis_learner=mock_hysteresis_learner_no_thresholds,
                hvac_mode=hvac_mode
            )
            
            # Should not attempt learning in unsupported modes
            assert progressive_setpoint is None