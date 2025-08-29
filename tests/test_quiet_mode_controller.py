"""
ABOUTME: Tests for the Quiet Mode QuietModeController that suppresses unnecessary 
temperature adjustments when AC compressor is idle to reduce beep noise.
"""

import pytest
from unittest.mock import Mock, MagicMock
import logging
from custom_components.smart_climate.quiet_mode_controller import QuietModeController
from custom_components.smart_climate.compressor_state_analyzer import CompressorStateAnalyzer
from custom_components.smart_climate.offset_engine import HysteresisLearner


class TestQuietModeController:
    """Test the QuietModeController class functionality."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create mock analyzer
        self.mock_analyzer = Mock(spec=CompressorStateAnalyzer)
        
        # Create mock logger
        self.mock_logger = Mock(spec=logging.Logger)
        
        # Create mock hysteresis learner with known thresholds
        self.mock_hysteresis_learner = Mock(spec=HysteresisLearner)
        self.mock_hysteresis_learner.learned_start_threshold = 22.0
        self.mock_hysteresis_learner.learned_stop_threshold = 24.0
        
        # Create controller instances
        self.enabled_controller = QuietModeController(
            enabled=True,
            analyzer=self.mock_analyzer,
            logger=self.mock_logger
        )
        
        self.disabled_controller = QuietModeController(
            enabled=False,
            analyzer=self.mock_analyzer,
            logger=self.mock_logger
        )

    def test_quiet_mode_enabled_by_config(self):
        """Test that quiet mode respects config setting."""
        # Test enabled controller
        assert self.enabled_controller._enabled is True
        
        # Test disabled controller  
        assert self.disabled_controller._enabled is False
        
        # Test disabled controller never suppresses
        self.mock_analyzer.is_compressor_idle.return_value = True
        self.mock_analyzer.would_adjustment_activate_compressor.return_value = False
        
        should_suppress, reason = self.disabled_controller.should_suppress_adjustment(
            current_room_temp=25.0,
            current_setpoint=24.0,
            new_setpoint=23.0,
            power=30.0,
            hvac_mode="cool",
            hysteresis_learner=self.mock_hysteresis_learner
        )
        
        assert should_suppress is False
        assert reason is None

    def test_suppresses_adjustment_when_idle_and_wont_activate(self):
        """Test main quiet mode path - suppress when idle and won't activate."""
        # Setup mocks - compressor is idle and adjustment won't activate it
        self.mock_analyzer.is_compressor_idle.return_value = True
        self.mock_analyzer.would_adjustment_activate_compressor.return_value = False
        
        should_suppress, reason = self.enabled_controller.should_suppress_adjustment(
            current_room_temp=25.0,
            current_setpoint=24.0,
            new_setpoint=23.5,  # Small adjustment that won't activate
            power=30.0,  # Below threshold (idle)
            hvac_mode="cool",
            hysteresis_learner=self.mock_hysteresis_learner
        )
        
        assert should_suppress is True
        assert "compressor idle" in reason.lower()
        assert "won't activate" in reason.lower()
        
        # Verify analyzer methods were called correctly
        self.mock_analyzer.is_compressor_idle.assert_called_once_with(30.0)
        self.mock_analyzer.would_adjustment_activate_compressor.assert_called_once_with(
            25.0, 23.5, self.mock_hysteresis_learner, "cool"
        )

    def test_allows_adjustment_when_would_activate(self):
        """Test allows adjustment when it would cross threshold and activate compressor."""
        # Setup mocks - compressor is idle but adjustment would activate it
        self.mock_analyzer.is_compressor_idle.return_value = True
        self.mock_analyzer.would_adjustment_activate_compressor.return_value = True
        
        should_suppress, reason = self.enabled_controller.should_suppress_adjustment(
            current_room_temp=25.0,
            current_setpoint=24.0,
            new_setpoint=21.0,  # Big adjustment that will activate
            power=30.0,  # Below threshold (idle)
            hvac_mode="cool",
            hysteresis_learner=self.mock_hysteresis_learner
        )
        
        assert should_suppress is False
        assert reason is None

    def test_allows_adjustment_when_compressor_active(self):
        """Test allows adjustment when compressor is already active (no suppression)."""
        # Setup mocks - compressor is active
        self.mock_analyzer.is_compressor_idle.return_value = False
        
        should_suppress, reason = self.enabled_controller.should_suppress_adjustment(
            current_room_temp=25.0,
            current_setpoint=24.0,
            new_setpoint=23.0,
            power=75.0,  # Above threshold (active)
            hvac_mode="cool",
            hysteresis_learner=self.mock_hysteresis_learner
        )
        
        assert should_suppress is False
        assert reason is None
        
        # Should only check if compressor is idle, not call would_activate
        self.mock_analyzer.is_compressor_idle.assert_called_once_with(75.0)
        self.mock_analyzer.would_adjustment_activate_compressor.assert_not_called()

    def test_disabled_in_unsupported_modes(self):
        """Test quiet mode is disabled in heat/heat_cool/off modes."""
        # Test all unsupported modes
        unsupported_modes = ["heat", "heat_cool", "off"]
        
        for mode in unsupported_modes:
            # Reset mock
            self.mock_analyzer.reset_mock()
            
            should_suppress, reason = self.enabled_controller.should_suppress_adjustment(
                current_room_temp=20.0,
                current_setpoint=22.0,
                new_setpoint=21.0,
                power=30.0,
                hvac_mode=mode,
                hysteresis_learner=self.mock_hysteresis_learner
            )
            
            assert should_suppress is False
            assert reason is None
            
            # Should not call analyzer methods for unsupported modes
            self.mock_analyzer.is_compressor_idle.assert_not_called()
            self.mock_analyzer.would_adjustment_activate_compressor.assert_not_called()

    def test_enabled_in_supported_modes(self):
        """Test quiet mode works in cool/dry/auto modes."""
        supported_modes = ["cool", "dry", "auto"]
        
        # Setup mocks for suppression case
        self.mock_analyzer.is_compressor_idle.return_value = True
        self.mock_analyzer.would_adjustment_activate_compressor.return_value = False
        
        for mode in supported_modes:
            # Reset mock call counts
            self.mock_analyzer.reset_mock()
            
            should_suppress, reason = self.enabled_controller.should_suppress_adjustment(
                current_room_temp=25.0,
                current_setpoint=24.0,
                new_setpoint=23.5,
                power=30.0,
                hvac_mode=mode,
                hysteresis_learner=self.mock_hysteresis_learner
            )
            
            assert should_suppress is True
            assert "compressor idle" in reason.lower()
            
            # Should call analyzer methods for supported modes
            self.mock_analyzer.is_compressor_idle.assert_called_once()
            self.mock_analyzer.would_adjustment_activate_compressor.assert_called_once()

    def test_progressive_learning_when_threshold_unknown(self):
        """Test progressive learning when hysteresis threshold is unknown."""
        # Create hysteresis learner without learned thresholds
        unknown_learner = Mock(spec=HysteresisLearner)
        unknown_learner.learned_start_threshold = None
        unknown_learner.learned_stop_threshold = None
        
        # Setup analyzer to return None for unknown thresholds
        self.mock_analyzer.is_compressor_idle.return_value = True
        self.mock_analyzer.would_adjustment_activate_compressor.return_value = None
        
        # Should get progressive adjustment
        progressive_adjustment = self.enabled_controller.get_progressive_adjustment(
            current_room_temp=25.0,
            current_setpoint=24.0,
            hysteresis_learner=unknown_learner,
            hvac_mode="cool"
        )
        
        # Should return a setpoint 0.5°C lower than current
        assert progressive_adjustment == 23.5
        
        # Test unsupported modes return None
        progressive_adjustment = self.enabled_controller.get_progressive_adjustment(
            current_room_temp=25.0,
            current_setpoint=24.0,
            hysteresis_learner=unknown_learner,
            hvac_mode="heat"
        )
        
        assert progressive_adjustment is None

    def test_tracks_suppression_count(self):
        """Test that suppression count is tracked and can be retrieved/reset."""
        # Initial count should be 0
        assert self.enabled_controller.get_suppression_count() == 0
        
        # Setup for suppression
        self.mock_analyzer.is_compressor_idle.return_value = True
        self.mock_analyzer.would_adjustment_activate_compressor.return_value = False
        
        # Make several suppressed adjustments
        for i in range(3):
            should_suppress, reason = self.enabled_controller.should_suppress_adjustment(
                current_room_temp=25.0,
                current_setpoint=24.0,
                new_setpoint=23.5,
                power=30.0,
                hvac_mode="cool",
                hysteresis_learner=self.mock_hysteresis_learner
            )
            assert should_suppress is True
        
        # Count should be incremented
        assert self.enabled_controller.get_suppression_count() == 3
        
        # Reset count
        self.enabled_controller.reset_suppression_count()
        assert self.enabled_controller.get_suppression_count() == 0

    def test_provides_suppression_reasons(self):
        """Test that suppression reasons are descriptive and informative."""
        # Test compressor idle + won't activate case
        self.mock_analyzer.is_compressor_idle.return_value = True
        self.mock_analyzer.would_adjustment_activate_compressor.return_value = False
        
        should_suppress, reason = self.enabled_controller.should_suppress_adjustment(
            current_room_temp=25.0,
            current_setpoint=24.0,
            new_setpoint=23.5,
            power=30.0,
            hvac_mode="cool",
            hysteresis_learner=self.mock_hysteresis_learner
        )
        
        assert should_suppress is True
        assert isinstance(reason, str)
        assert len(reason) > 10  # Should be descriptive
        assert "idle" in reason.lower() or "compressor" in reason.lower()
        
        # Test when thresholds unknown
        unknown_learner = Mock(spec=HysteresisLearner)
        unknown_learner.learned_start_threshold = None
        self.mock_analyzer.would_adjustment_activate_compressor.return_value = None
        
        should_suppress, reason = self.enabled_controller.should_suppress_adjustment(
            current_room_temp=25.0,
            current_setpoint=24.0,
            new_setpoint=23.5,
            power=30.0,
            hvac_mode="cool",
            hysteresis_learner=unknown_learner
        )
        
        assert should_suppress is True
        assert "unknown" in reason.lower() or "learning" in reason.lower()

    def test_handles_none_power_gracefully(self):
        """Test graceful handling of None power consumption."""
        # Setup analyzer to handle None power (should treat as idle)
        self.mock_analyzer.is_compressor_idle.return_value = True
        self.mock_analyzer.would_adjustment_activate_compressor.return_value = False
        
        should_suppress, reason = self.enabled_controller.should_suppress_adjustment(
            current_room_temp=25.0,
            current_setpoint=24.0,
            new_setpoint=23.5,
            power=None,  # None power
            hvac_mode="cool",
            hysteresis_learner=self.mock_hysteresis_learner
        )
        
        assert should_suppress is True
        assert reason is not None
        
        # Verify None was passed to analyzer
        self.mock_analyzer.is_compressor_idle.assert_called_once_with(None)

    def test_no_suppression_without_analyzer_calls_when_not_needed(self):
        """Test optimization - don't call analyzer when not needed."""
        # Test disabled controller
        should_suppress, reason = self.disabled_controller.should_suppress_adjustment(
            current_room_temp=25.0,
            current_setpoint=24.0,
            new_setpoint=23.5,
            power=30.0,
            hvac_mode="cool",
            hysteresis_learner=self.mock_hysteresis_learner
        )
        
        assert should_suppress is False
        assert reason is None
        
        # Should not call analyzer when disabled
        self.mock_analyzer.is_compressor_idle.assert_not_called()
        self.mock_analyzer.would_adjustment_activate_compressor.assert_not_called()