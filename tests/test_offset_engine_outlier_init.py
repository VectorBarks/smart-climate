"""
Test OffsetEngine initialization with outlier detection configuration.

This module tests the integration between ConfigEntry options and OffsetEngine
outlier detection initialization in the __init__.py setup flow.
"""
import pytest
from unittest.mock import Mock, patch
from homeassistant.config_entries import ConfigEntry
from custom_components.smart_climate import _build_outlier_config
from custom_components.smart_climate.const import (
    CONF_OUTLIER_DETECTION_ENABLED,
    CONF_OUTLIER_SENSITIVITY,
)
from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.outlier_detector import OutlierDetector


class TestOffsetEngineOutlierInit:
    """Test OffsetEngine initialization with outlier detection config."""
    
    def test_build_outlier_config_with_enabled_options(self):
        """Test _build_outlier_config returns config when outlier detection enabled."""
        options = {
            CONF_OUTLIER_DETECTION_ENABLED: True,
            CONF_OUTLIER_SENSITIVITY: 2.5,
        }
        
        config = _build_outlier_config(options)
        
        assert config is not None
        assert config['zscore_threshold'] == 2.5
        assert 'history_size' in config
        assert 'min_samples_for_stats' in config
        assert 'temperature_bounds' in config
        assert 'power_bounds' in config
    
    def test_build_outlier_config_with_disabled_options(self):
        """Test _build_outlier_config returns None when outlier detection disabled."""
        options = {
            CONF_OUTLIER_DETECTION_ENABLED: False,
            CONF_OUTLIER_SENSITIVITY: 2.5,
        }
        
        config = _build_outlier_config(options)
        
        assert config is None
    
    def test_build_outlier_config_with_empty_options(self):
        """Test _build_outlier_config returns None with empty options."""
        config = _build_outlier_config({})
        assert config is None
    
    @patch('custom_components.smart_climate.offset_engine.OutlierDetector')
    def test_offset_engine_creates_outlier_detector_when_config_provided(self, mock_outlier_detector):
        """Test OffsetEngine creates OutlierDetector when outlier_detection_config provided."""
        # Mock config entry data
        config_data = {
            'climate_entity': 'climate.test',
            'name': 'Test Climate'
        }
        
        # Mock outlier config (as returned by _build_outlier_config)
        outlier_config = {
            'zscore_threshold': 2.0,
            'history_size': 50,
            'min_samples_for_stats': 10,
            'temperature_bounds': (-10.0, 50.0),
            'power_bounds': (0.0, 5000.0)
        }
        
        # Create OffsetEngine with outlier config (seasonal_learner can be None)
        offset_engine = OffsetEngine(
            config=config_data,
            seasonal_learner=None,
            outlier_detection_config=outlier_config
        )
        
        # Verify OutlierDetector was created with correct config
        mock_outlier_detector.assert_called_once_with(config=outlier_config)
        
        # Verify OffsetEngine has the outlier detector
        assert offset_engine._outlier_detector is not None
    
    @patch('custom_components.smart_climate.offset_engine.OutlierDetector')
    def test_offset_engine_no_outlier_detector_when_config_none(self, mock_outlier_detector):
        """Test OffsetEngine doesn't create OutlierDetector when outlier_detection_config is None."""
        # Mock config entry data
        config_data = {
            'climate_entity': 'climate.test',
            'name': 'Test Climate'
        }
        
        # Create OffsetEngine without outlier config
        offset_engine = OffsetEngine(
            config=config_data,
            seasonal_learner=None,
            outlier_detection_config=None
        )
        
        # Verify OutlierDetector was not created
        mock_outlier_detector.assert_not_called()
        
        # Verify OffsetEngine has no outlier detector
        assert offset_engine._outlier_detector is None


class TestConfigEntryIntegration:
    """Test integration with ConfigEntry objects and options handling."""
    
    def test_config_entry_with_options_attribute(self):
        """Test handling ConfigEntry that has options attribute."""
        # Mock ConfigEntry with options
        config_entry = Mock(spec=ConfigEntry)
        config_entry.options = {
            CONF_OUTLIER_DETECTION_ENABLED: True,
            CONF_OUTLIER_SENSITIVITY: 2.0,
        }
        config_entry.data = {
            'climate_entity': 'climate.test',
            'name': 'Test Climate'
        }
        
        # Test safe options access
        options = config_entry.options if hasattr(config_entry, 'options') else {}
        assert options == config_entry.options
        
        # Test outlier config building
        outlier_config = _build_outlier_config(options)
        assert outlier_config is not None
        assert outlier_config['zscore_threshold'] == 2.0
    
    def test_config_entry_without_options_attribute(self):
        """Test backward compatibility with ConfigEntry that has no options attribute."""
        # Mock ConfigEntry without options attribute
        config_entry = Mock(spec=ConfigEntry)
        config_entry.data = {
            'climate_entity': 'climate.test',
            'name': 'Test Climate'
        }
        # Explicitly remove options to simulate old ConfigEntry
        if hasattr(config_entry, 'options'):
            delattr(config_entry, 'options')
        
        # Test safe options access
        options = config_entry.options if hasattr(config_entry, 'options') else {}
        assert options == {}
        
        # Test outlier config building returns None for empty options
        outlier_config = _build_outlier_config(options)
        assert outlier_config is None
    
    def test_init_flow_integration_outlier_enabled(self):
        """Test complete initialization flow integration when outlier detection enabled."""
        # Mock ConfigEntry with enabled outlier detection
        config_entry = Mock(spec=ConfigEntry)
        config_entry.options = {
            CONF_OUTLIER_DETECTION_ENABLED: True,
            CONF_OUTLIER_SENSITIVITY: 2.5,
        }
        config_entry.data = {
            'climate_entity': 'climate.test',
            'name': 'Test Climate'
        }
        
        # Simulate the __init__.py initialization flow
        options = config_entry.options if hasattr(config_entry, 'options') else {}
        outlier_config = _build_outlier_config(options)
        
        # Verify configuration is built correctly
        assert outlier_config is not None
        expected_config = {
            'zscore_threshold': 2.5,
            'history_size': 100,  # DEFAULT_OUTLIER_HISTORY_SIZE
            'min_samples_for_stats': 10,  # DEFAULT_OUTLIER_MIN_SAMPLES 
            'temperature_bounds': (0, 40),  # DEFAULT_OUTLIER_TEMP_BOUNDS
            'power_bounds': (0, 5000),  # DEFAULT_OUTLIER_POWER_BOUNDS
        }
        assert outlier_config == expected_config
    
    def test_init_flow_integration_outlier_disabled(self):
        """Test complete initialization flow integration when outlier detection disabled."""
        # Mock ConfigEntry with disabled outlier detection
        config_entry = Mock(spec=ConfigEntry)
        config_entry.options = {
            CONF_OUTLIER_DETECTION_ENABLED: False,
            CONF_OUTLIER_SENSITIVITY: 2.0,
        }
        config_entry.data = {
            'climate_entity': 'climate.test',
            'name': 'Test Climate'
        }
        
        # Simulate the initialization flow
        options = config_entry.options if hasattr(config_entry, 'options') else {}
        outlier_config = _build_outlier_config(options)
        
        # Verify configuration returns None when disabled
        assert outlier_config is None
    
    def test_init_flow_integration_legacy_entries(self):
        """Test complete initialization flow integration for legacy ConfigEntries."""
        # Mock legacy ConfigEntry without options attribute
        config_entry = Mock(spec=ConfigEntry)
        config_entry.data = {
            'climate_entity': 'climate.test',
            'name': 'Test Climate'
        }
        # Remove options attribute to simulate legacy entry
        if hasattr(config_entry, 'options'):
            delattr(config_entry, 'options')
        
        # Simulate the initialization flow
        options = config_entry.options if hasattr(config_entry, 'options') else {}
        outlier_config = _build_outlier_config(options)
        
        # Verify configuration returns None for legacy entries (backward compatibility)
        assert outlier_config is None


class TestInitFlowSimulation:
    """Test the complete initialization flow as it would happen in __init__.py."""
    
    @patch('custom_components.smart_climate.offset_engine.OutlierDetector')
    def test_complete_init_flow_with_outlier_detection_enabled(self, mock_outlier_detector):
        """Test complete initialization flow when outlier detection is enabled."""
        # Mock ConfigEntry with outlier detection enabled
        config_entry = Mock(spec=ConfigEntry)
        config_entry.options = {
            CONF_OUTLIER_DETECTION_ENABLED: True,
            CONF_OUTLIER_SENSITIVITY: 2.0,
        }
        config_entry.data = {
            'climate_entity': 'climate.test',
            'name': 'Test Climate'
        }
        
        # Simulate the __init__.py initialization flow
        options = config_entry.options if hasattr(config_entry, 'options') else {}
        outlier_config = _build_outlier_config(options)
        
        # Create OffsetEngine (this is the critical line being fixed)
        offset_engine = OffsetEngine(
            config=config_entry.data,
            seasonal_learner=None,  # Can be None for testing
            outlier_detection_config=outlier_config
        )
        
        # Verify the complete integration works
        expected_config = {
            'zscore_threshold': 2.0,
            'history_size': 100,
            'min_samples_for_stats': 10,
            'temperature_bounds': (0, 40),
            'power_bounds': (0, 5000),
        }
        mock_outlier_detector.assert_called_once_with(config=expected_config)
        assert offset_engine._outlier_detector is not None
    
    @patch('custom_components.smart_climate.offset_engine.OutlierDetector')
    def test_complete_init_flow_with_outlier_detection_disabled(self, mock_outlier_detector):
        """Test complete initialization flow when outlier detection is disabled."""
        # Mock ConfigEntry with outlier detection disabled
        config_entry = Mock(spec=ConfigEntry)
        config_entry.options = {
            CONF_OUTLIER_DETECTION_ENABLED: False,
            CONF_OUTLIER_SENSITIVITY: 2.0,
        }
        config_entry.data = {
            'climate_entity': 'climate.test',
            'name': 'Test Climate'
        }
        
        # Simulate the __init__.py initialization flow
        options = config_entry.options if hasattr(config_entry, 'options') else {}
        outlier_config = _build_outlier_config(options)
        
        # Create OffsetEngine
        offset_engine = OffsetEngine(
            config=config_entry.data,
            seasonal_learner=None,  # Can be None for testing
            outlier_detection_config=outlier_config
        )
        
        # Verify OutlierDetector is not created when disabled
        mock_outlier_detector.assert_not_called()
        assert offset_engine._outlier_detector is None