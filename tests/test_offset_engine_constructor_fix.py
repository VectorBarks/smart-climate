"""Test OffsetEngine constructor fix - removing hass and entity_id parameters."""

import pytest
from unittest.mock import Mock, AsyncMock
from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.seasonal_learner import SeasonalHysteresisLearner
from custom_components.smart_climate.feature_engineering import FeatureEngineering


class TestOffsetEngineConstructorFix:
    """Test OffsetEngine constructor can be called with the correct parameters."""
    
    def test_offset_engine_basic_constructor(self):
        """Test OffsetEngine can be created with just config parameter."""
        config = {
            "room_sensor": "sensor.room_temp",
            "climate_entity": "climate.test",
        }
        
        # Should not raise an error
        engine = OffsetEngine(config=config)
        assert engine is not None
    
    def test_offset_engine_with_all_optional_parameters(self):
        """Test OffsetEngine can be created with all optional parameters."""
        config = {
            "room_sensor": "sensor.room_temp", 
            "climate_entity": "climate.test",
        }
        
        # Mock optional components
        seasonal_learner = Mock(spec=SeasonalHysteresisLearner)
        feature_engineer = Mock(spec=FeatureEngineering)
        outlier_config = {"zscore_threshold": 2.5}
        
        def mock_get_thermal_data():
            return {"tau_cooling": 90.0, "tau_warming": 150.0}
        
        def mock_restore_thermal_data(data):
            pass
        
        # Should not raise an error
        engine = OffsetEngine(
            config=config,
            seasonal_learner=seasonal_learner,
            feature_engineer=feature_engineer,
            outlier_detection_config=outlier_config,
            get_thermal_data_cb=mock_get_thermal_data,
            restore_thermal_data_cb=mock_restore_thermal_data
        )
        assert engine is not None
    
    def test_offset_engine_rejects_old_parameters(self):
        """Test that OffsetEngine constructor rejects old hass and entity_id parameters."""
        config = {
            "room_sensor": "sensor.room_temp",
            "climate_entity": "climate.test",
        }
        
        mock_hass = Mock()
        
        # Should raise TypeError for unexpected keyword arguments
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            OffsetEngine(
                hass=mock_hass,  # This should cause an error
                entity_id="climate.test",  # This should cause an error  
                config=config
            )
    
    def test_offset_engine_accepts_config_first(self):
        """Test that config parameter is required and must be first."""
        # Should raise TypeError when config is missing
        with pytest.raises(TypeError, match="missing 1 required positional argument: 'config'"):
            OffsetEngine()
    
    def test_offset_engine_constructor_signature(self):
        """Test that OffsetEngine constructor has the expected signature."""
        import inspect
        
        sig = inspect.signature(OffsetEngine.__init__)
        params = list(sig.parameters.keys())
        
        # Should have 'self' as first parameter
        assert params[0] == 'self'
        # Should have 'config' as second parameter (first actual parameter)
        assert params[1] == 'config'
        # Should NOT have 'hass' or 'entity_id' parameters
        assert 'hass' not in params
        assert 'entity_id' not in params
        
        # Check that config is required (no default value)
        config_param = sig.parameters['config']
        assert config_param.default == inspect.Parameter.empty