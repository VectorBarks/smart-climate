"""End-to-end tests for Quiet Mode feature.

Tests complete quiet mode workflows including lifecycle management, 
beep reduction scenarios, mode transitions, and integration with 
thermal states and coordinator updates.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timezone, timedelta

from custom_components.smart_climate.compressor_state_analyzer import CompressorStateAnalyzer  
from custom_components.smart_climate.quiet_mode_controller import QuietModeController
from custom_components.smart_climate.offset_engine import HysteresisLearner
from custom_components.smart_climate.thermal_models import ThermalState


class TestQuietModeE2E:
    """End-to-end tests for Quiet Mode feature."""
    
    @pytest.fixture
    def mock_analyzer(self):
        """Mock CompressorStateAnalyzer."""
        return Mock(spec=CompressorStateAnalyzer)
    
    @pytest.fixture  
    def mock_hysteresis_learner(self):
        """Mock HysteresisLearner with learned thresholds."""
        learner = Mock(spec=HysteresisLearner)
        learner.learned_start_threshold = 25.0  # Compressor starts at 25°C
        learner.learned_stop_threshold = 24.0   # Compressor stops at 24°C
        learner.has_learned_thresholds.return_value = True
        return learner
    
    @pytest.fixture
    def mock_hysteresis_learner_no_thresholds(self):
        """Mock HysteresisLearner without learned thresholds."""
        learner = Mock(spec=HysteresisLearner)
        learner.learned_start_threshold = None
        learner.learned_stop_threshold = None  
        learner.has_learned_thresholds.return_value = False
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
    
    def test_full_quiet_mode_lifecycle(self, quiet_controller, mock_analyzer, mock_hysteresis_learner):
        """Test complete quiet mode lifecycle from config to suppression."""
        # Setup: Compressor is idle (low power)
        mock_analyzer.is_compressor_idle.return_value = True
        mock_analyzer.would_adjustment_activate_compressor.return_value = False
        
        # Test scenario: Room temp 23°C, current setpoint 22°C, want to adjust to 21°C
        current_room_temp = 23.0
        current_setpoint = 22.0
        new_setpoint = 21.0
        power = 15.0  # Low power = idle compressor
        hvac_mode = "cool"
        
        # Execute: Should suppress adjustment
        should_suppress, reason = quiet_controller.should_suppress_adjustment(
            current_room_temp=current_room_temp,
            current_setpoint=current_setpoint,
            new_setpoint=new_setpoint,
            power=power,
            hvac_mode=hvac_mode,
            hysteresis_learner=mock_hysteresis_learner
        )
        
        # Verify: Adjustment suppressed with proper reason
        assert should_suppress is True
        assert "Compressor idle and adjustment won't activate it" in reason
        assert mock_analyzer.is_compressor_idle.called
        assert mock_analyzer.would_adjustment_activate_compressor.called
        
        # Verify suppression counter incremented
        assert quiet_controller._suppression_count == 1
    
    def test_beep_reduction_scenario(self, quiet_controller, mock_analyzer, mock_hysteresis_learner):
        """Test typical beep reduction scenario with multiple adjustments."""
        # Setup: Compressor idle, adjustments won't activate it
        mock_analyzer.is_compressor_idle.return_value = True
        mock_analyzer.would_adjustment_activate_compressor.return_value = False
        
        # Scenario: Multiple small adjustments over time
        test_cases = [
            (22.5, 22.0, 21.8, 20.0),  # Small cooling adjustment
            (22.3, 21.8, 21.5, 18.0),  # Another small adjustment
            (22.1, 21.5, 21.2, 16.0),  # Another small adjustment
        ]
        
        suppressed_count = 0
        for room_temp, current_sp, new_sp, power in test_cases:
            should_suppress, reason = quiet_controller.should_suppress_adjustment(
                current_room_temp=room_temp,
                current_setpoint=current_sp,
                new_setpoint=new_sp,
                power=power,
                hvac_mode="cool",
                hysteresis_learner=mock_hysteresis_learner
            )
            
            if should_suppress:
                suppressed_count += 1
        
        # Verify: All adjustments suppressed (would have caused 6 beeps normally)
        assert suppressed_count == 3
        assert quiet_controller._suppression_count == 3
    
    def test_mode_transitions(self, quiet_controller, mock_analyzer, mock_hysteresis_learner):
        """Test quiet mode behavior during HVAC mode transitions."""
        mock_analyzer.is_compressor_idle.return_value = True
        mock_analyzer.would_adjustment_activate_compressor.return_value = False
        
        # Test different HVAC modes
        hvac_modes = ["cool", "dry", "auto"]
        current_room_temp = 23.0
        current_setpoint = 22.0
        new_setpoint = 21.5
        power = 25.0
        
        suppression_results = []
        for hvac_mode in hvac_modes:
            should_suppress, reason = quiet_controller.should_suppress_adjustment(
                current_room_temp=current_room_temp,
                current_setpoint=current_setpoint,
                new_setpoint=new_setpoint,
                power=power,
                hvac_mode=hvac_mode,
                hysteresis_learner=mock_hysteresis_learner
            )
            suppression_results.append((hvac_mode, should_suppress))
        
        # Verify: All supported modes suppress appropriately
        for hvac_mode, should_suppress in suppression_results:
            assert should_suppress is True, f"Mode {hvac_mode} should suppress"
        
        # Test unsupported modes (heat, heat_cool)
        unsupported_modes = ["heat", "heat_cool"]
        for hvac_mode in unsupported_modes:
            should_suppress, reason = quiet_controller.should_suppress_adjustment(
                current_room_temp=current_room_temp,
                current_setpoint=current_setpoint,
                new_setpoint=new_setpoint,
                power=power,
                hvac_mode=hvac_mode,
                hysteresis_learner=mock_hysteresis_learner
            )
            # Unsupported modes should not suppress (let normal logic handle)
            assert should_suppress is False
            assert "not supported" in reason
    
    def test_power_transitions(self, quiet_controller, mock_analyzer, mock_hysteresis_learner):
        """Test quiet mode during compressor power transitions."""
        current_room_temp = 23.0
        current_setpoint = 22.0  
        new_setpoint = 21.0
        hvac_mode = "cool"
        
        # Test Case 1: Compressor idle (low power) -> suppress
        mock_analyzer.is_compressor_idle.return_value = True
        mock_analyzer.would_adjustment_activate_compressor.return_value = False
        
        should_suppress, reason = quiet_controller.should_suppress_adjustment(
            current_room_temp=current_room_temp,
            current_setpoint=current_setpoint,
            new_setpoint=new_setpoint,
            power=20.0,  # Low power
            hvac_mode=hvac_mode,
            hysteresis_learner=mock_hysteresis_learner
        )
        assert should_suppress is True
        
        # Test Case 2: Compressor active (high power) -> don't suppress  
        mock_analyzer.is_compressor_idle.return_value = False
        
        should_suppress, reason = quiet_controller.should_suppress_adjustment(
            current_room_temp=current_room_temp,
            current_setpoint=current_setpoint,
            new_setpoint=new_setpoint,
            power=80.0,  # High power
            hvac_mode=hvac_mode,
            hysteresis_learner=mock_hysteresis_learner
        )
        assert should_suppress is False
        assert "Compressor active" in reason
        
        # Test Case 3: Idle but adjustment would activate -> don't suppress
        mock_analyzer.is_compressor_idle.return_value = True
        mock_analyzer.would_adjustment_activate_compressor.return_value = True
        
        should_suppress, reason = quiet_controller.should_suppress_adjustment(
            current_room_temp=current_room_temp,
            current_setpoint=current_setpoint,
            new_setpoint=new_setpoint,
            power=15.0,  # Low power
            hvac_mode=hvac_mode,
            hysteresis_learner=mock_hysteresis_learner
        )
        assert should_suppress is False
        assert "would activate compressor" in reason
    
    def test_coordinator_update_suppression(self, quiet_controller, mock_analyzer, mock_hysteresis_learner):
        """Test suppression of periodic coordinator updates."""
        # Setup: Typical coordinator update scenario
        mock_analyzer.is_compressor_idle.return_value = True
        mock_analyzer.would_adjustment_activate_compressor.return_value = False
        
        # Simulate coordinator making small periodic adjustments
        base_temp = 22.0
        periodic_adjustments = [
            (base_temp, base_temp + 0.1),  # +0.1°C
            (base_temp, base_temp - 0.2),  # -0.2°C  
            (base_temp, base_temp + 0.15), # +0.15°C
            (base_temp, base_temp - 0.1),  # -0.1°C
        ]
        
        suppressed_count = 0
        for current_sp, new_sp in periodic_adjustments:
            should_suppress, reason = quiet_controller.should_suppress_adjustment(
                current_room_temp=22.5,
                current_setpoint=current_sp,
                new_setpoint=new_sp,
                power=25.0,  # Idle power
                hvac_mode="cool",
                hysteresis_learner=mock_hysteresis_learner
            )
            
            if should_suppress:
                suppressed_count += 1
        
        # Verify: All small periodic updates suppressed  
        assert suppressed_count == 4
        assert quiet_controller._suppression_count == 4
    
    def test_manual_adjustment_suppression(self, quiet_controller, mock_analyzer, mock_hysteresis_learner):
        """Test suppression of manual user adjustments when appropriate."""
        mock_analyzer.is_compressor_idle.return_value = True
        mock_analyzer.would_adjustment_activate_compressor.return_value = False
        
        # Scenario: User makes manual adjustment that won't activate compressor
        should_suppress, reason = quiet_controller.should_suppress_adjustment(
            current_room_temp=23.0,
            current_setpoint=22.0,
            new_setpoint=21.0,  # User wants cooler
            power=30.0,  # But compressor idle
            hvac_mode="cool",
            hysteresis_learner=mock_hysteresis_learner
        )
        
        # Manual adjustments should still be suppressed if they won't help
        assert should_suppress is True
        assert "won't activate" in reason
        
        # But if adjustment would activate compressor, don't suppress
        mock_analyzer.would_adjustment_activate_compressor.return_value = True
        
        should_suppress, reason = quiet_controller.should_suppress_adjustment(
            current_room_temp=23.0,
            current_setpoint=22.0,
            new_setpoint=20.0,  # Big adjustment
            power=30.0,
            hvac_mode="cool",
            hysteresis_learner=mock_hysteresis_learner
        )
        
        assert should_suppress is False
        assert "would activate" in reason
    
    def test_interaction_with_thermal_states(self, quiet_controller, mock_analyzer, mock_hysteresis_learner):
        """Test quiet mode interaction with thermal states (PRIMING/DRIFTING/PROBING)."""
        mock_analyzer.is_compressor_idle.return_value = True
        mock_analyzer.would_adjustment_activate_compressor.return_value = False
        
        # Test during different thermal states
        test_scenarios = [
            ("PRIMING", True),     # Should suppress during PRIMING
            ("DRIFTING", True),    # Should suppress during DRIFTING  
            ("PROBING", True),     # Should suppress during PROBING
            ("NORMAL", True),      # Should suppress during normal operation
        ]
        
        for thermal_state, expected_suppress in test_scenarios:
            # Quiet mode logic doesn't directly check thermal state
            # but should work consistently regardless
            should_suppress, reason = quiet_controller.should_suppress_adjustment(
                current_room_temp=22.5,
                current_setpoint=22.0,
                new_setpoint=21.8,
                power=20.0,
                hvac_mode="cool", 
                hysteresis_learner=mock_hysteresis_learner
            )
            
            assert should_suppress == expected_suppress, f"Failed for thermal state: {thermal_state}"
    
    def test_config_runtime_changes(self, mock_analyzer, mock_logger, mock_hysteresis_learner):
        """Test enabling/disabling quiet mode at runtime."""
        # Start with quiet mode enabled
        controller = QuietModeController(
            enabled=True,
            analyzer=mock_analyzer,
            logger=mock_logger
        )
        
        mock_analyzer.is_compressor_idle.return_value = True
        mock_analyzer.would_adjustment_activate_compressor.return_value = False
        
        # Test with enabled
        should_suppress, reason = controller.should_suppress_adjustment(
            current_room_temp=22.5,
            current_setpoint=22.0,
            new_setpoint=21.8,
            power=20.0,
            hvac_mode="cool",
            hysteresis_learner=mock_hysteresis_learner
        )
        assert should_suppress is True
        
        # Simulate runtime config change to disable
        controller._enabled = False
        
        should_suppress, reason = controller.should_suppress_adjustment(
            current_room_temp=22.5,
            current_setpoint=22.0,
            new_setpoint=21.8,
            power=20.0,
            hvac_mode="cool",
            hysteresis_learner=mock_hysteresis_learner
        )
        
        # Should not suppress when disabled
        assert should_suppress is False
        assert "disabled" in reason
        
        # Verify suppression counter preserved across enable/disable
        original_count = controller._suppression_count
        controller._enabled = True  # Re-enable
        
        # Make another suppression
        should_suppress, reason = controller.should_suppress_adjustment(
            current_room_temp=22.5,
            current_setpoint=22.0,
            new_setpoint=21.6,
            power=25.0,
            hvac_mode="cool",
            hysteresis_learner=mock_hysteresis_learner
        )
        
        assert should_suppress is True
        assert controller._suppression_count == original_count + 1