"""ABOUTME: Tests for smart climate integration initialization and setup.
Verifies component structure, manifest, and HACS compatibility."""

import pytest
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# Test component structure
def test_component_directory_exists():
    """Test that the component directory exists."""
    component_dir = Path("custom_components/smart_climate")
    assert component_dir.exists(), "Component directory should exist"
    assert component_dir.is_dir(), "Component path should be a directory"

def test_required_files_exist():
    """Test that all required files exist."""
    component_dir = Path("custom_components/smart_climate")
    required_files = [
        "__init__.py",
        "manifest.json",
        "const.py"
    ]
    
    for file_name in required_files:
        file_path = component_dir / file_name
        assert file_path.exists(), f"Required file {file_name} should exist"

def test_manifest_json_structure():
    """Test that manifest.json has correct structure."""
    manifest_path = Path("custom_components/smart_climate/manifest.json")
    assert manifest_path.exists(), "manifest.json should exist"
    
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    # Required fields
    required_fields = ["domain", "name", "version", "requirements", "dependencies", "codeowners"]
    for field in required_fields:
        assert field in manifest, f"manifest.json should have {field} field"
    
    # Domain should be smart_climate
    assert manifest["domain"] == "smart_climate", "Domain should be 'smart_climate'"
    
    # Version should follow semantic versioning
    version = manifest["version"]
    version_parts = version.split('.')
    assert len(version_parts) == 3, "Version should be in format X.Y.Z"
    for part in version_parts:
        assert part.isdigit(), "Version parts should be numeric"

def test_const_py_content():
    """Test that const.py has required constants."""
    const_path = Path("custom_components/smart_climate/const.py")
    assert const_path.exists(), "const.py should exist"
    
    # Import the module to check DOMAIN constant
    import sys
    sys.path.insert(0, str(Path("custom_components/smart_climate")))
    
    try:
        import const
        assert hasattr(const, "DOMAIN"), "const.py should define DOMAIN"
        assert const.DOMAIN == "smart_climate", "DOMAIN should be 'smart_climate'"
    finally:
        sys.path.remove(str(Path("custom_components/smart_climate")))

def test_hacs_json_exists():
    """Test that hacs.json exists for HACS compatibility."""
    hacs_path = Path("hacs.json")
    assert hacs_path.exists(), "hacs.json should exist for HACS compatibility"
    
    with open(hacs_path, 'r') as f:
        hacs_config = json.load(f)
    
    # Should have required HACS fields
    required_hacs_fields = ["name", "hacs", "domains"]
    for field in required_hacs_fields:
        assert field in hacs_config, f"hacs.json should have {field} field"

def test_readme_exists():
    """Test that README.md exists."""
    readme_path = Path("README.md")
    assert readme_path.exists(), "README.md should exist"
    
    # Should not be empty
    with open(readme_path, 'r') as f:
        content = f.read().strip()
    assert len(content) > 0, "README.md should not be empty"

def test_init_py_importable():
    """Test that __init__.py is importable."""
    init_path = Path("custom_components/smart_climate/__init__.py")
    assert init_path.exists(), "__init__.py should exist"
    
    # Should be a valid Python file (not cause syntax errors)
    with open(init_path, 'r') as f:
        content = f.read()
    
    # Basic check - should not be empty and should be valid Python
    assert len(content.strip()) >= 0, "__init__.py should exist (can be empty initially)"
    
    # Try to compile to check syntax
    try:
        compile(content, str(init_path), 'exec')
    except SyntaxError:
        pytest.fail("__init__.py should have valid Python syntax")

def test_component_discoverable():
    """Test that the component can be discovered by Home Assistant."""
    # Check that manifest domain matches directory name
    manifest_path = Path("custom_components/smart_climate/manifest.json")
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    component_dir = Path("custom_components/smart_climate")
    assert component_dir.name == manifest["domain"], "Directory name should match manifest domain"
    
    # Check that required Home Assistant integration files exist
    assert (component_dir / "manifest.json").exists()
    assert (component_dir / "__init__.py").exists()
    
    # Manifest should specify required dependencies
    assert "dependencies" in manifest
    assert isinstance(manifest["dependencies"], list)
    assert "requirements" in manifest
    assert isinstance(manifest["requirements"], list)


# TDD Phase 6: Humidity Component Wiring Tests
# These tests MUST FAIL initially to verify TDD approach

@pytest.mark.asyncio
class TestHumidityComponentWiring:
    """Test humidity component wiring in async_setup_entry."""

    @pytest.fixture
    def mock_hass(self):
        """Mock Home Assistant core."""
        hass = MagicMock()
        hass.data = {}
        return hass

    @pytest.fixture  
    def mock_config_entry(self):
        """Mock config entry with humidity sensors."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        entry.data = {
            "room_sensor": "sensor.room_temp",
            "climate_entity": "climate.test", 
            "indoor_humidity_sensor": "sensor.indoor_humidity",
            "outdoor_humidity_sensor": "sensor.outdoor_humidity"
        }
        entry.options = {}
        return entry

    @pytest.fixture
    def mock_config_entry_no_humidity(self):
        """Mock config entry without humidity sensors (backward compatibility)."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        entry.data = {
            "room_sensor": "sensor.room_temp",
            "climate_entity": "climate.test"
        }
        entry.options = {}
        return entry

    @patch('custom_components.smart_climate.FeatureEngineering')
    async def test_feature_engineering_instantiation(self, mock_feature_engineering, mock_hass, mock_config_entry):
        """Test FeatureEngineering is imported and instantiated."""
        # Import here to allow patching
        from custom_components.smart_climate import async_setup_entry
        
        # Mock all dependencies to prevent side effects
        with patch('custom_components.smart_climate.EntityWaiter') as mock_entity_waiter, \
             patch('custom_components.smart_climate.SeasonalHysteresisLearner'), \
             patch('custom_components.smart_climate._async_setup_entity_persistence', new_callable=AsyncMock), \
             patch('custom_components.smart_climate._async_register_services', new_callable=AsyncMock), \
             patch.object(mock_hass.config_entries, 'async_forward_entry_setups', new_callable=AsyncMock):
            
            # Mock EntityWaiter async method
            mock_entity_waiter_instance = mock_entity_waiter.return_value
            mock_entity_waiter_instance.wait_for_required_entities = AsyncMock()
            
            # This should fail initially - FeatureEngineering not imported
            await async_setup_entry(mock_hass, mock_config_entry)
            
            # Verify FeatureEngineering was instantiated
            mock_feature_engineering.assert_called_once_with()

    @patch('custom_components.smart_climate.FeatureEngineering')
    @patch('custom_components.smart_climate.SensorManager')
    async def test_sensor_manager_receives_humidity_ids(self, mock_sensor_manager, mock_feature_engineering, mock_hass, mock_config_entry):
        """Test SensorManager constructor receives humidity sensor IDs.""" 
        from custom_components.smart_climate import async_setup_entry
        
        with patch('custom_components.smart_climate.EntityWaiter') as mock_entity_waiter, \
             patch('custom_components.smart_climate.SeasonalHysteresisLearner'), \
             patch('custom_components.smart_climate._async_setup_entity_persistence', new_callable=AsyncMock), \
             patch('custom_components.smart_climate._async_register_services', new_callable=AsyncMock), \
             patch.object(mock_hass.config_entries, 'async_forward_entry_setups', new_callable=AsyncMock):
            
            # Mock EntityWaiter async method
            mock_entity_waiter_instance = mock_entity_waiter.return_value
            mock_entity_waiter_instance.wait_for_required_entities = AsyncMock()
            
            await async_setup_entry(mock_hass, mock_config_entry)
            
            # Verify SensorManager was called with humidity IDs
            # This should fail initially - SensorManager doesn't receive humidity IDs yet
            mock_sensor_manager.assert_called_with(
                mock_hass,
                room_sensor_id="sensor.room_temp",
                outdoor_sensor_id=None,
                power_sensor_id=None,
                indoor_humidity_sensor_id="sensor.indoor_humidity",
                outdoor_humidity_sensor_id="sensor.outdoor_humidity"
            )

    @patch('custom_components.smart_climate.FeatureEngineering')
    @patch('custom_components.smart_climate.SensorManager')
    async def test_sensor_manager_backward_compatibility(self, mock_sensor_manager, mock_feature_engineering, mock_hass, mock_config_entry_no_humidity):
        """Test SensorManager with no humidity sensors (backward compatibility)."""
        from custom_components.smart_climate import async_setup_entry
        
        with patch('custom_components.smart_climate.EntityWaiter') as mock_entity_waiter, \
             patch('custom_components.smart_climate.SeasonalHysteresisLearner'), \
             patch('custom_components.smart_climate._async_setup_entity_persistence', new_callable=AsyncMock), \
             patch('custom_components.smart_climate._async_register_services', new_callable=AsyncMock), \
             patch.object(mock_hass.config_entries, 'async_forward_entry_setups', new_callable=AsyncMock):
            
            # Mock EntityWaiter async method
            mock_entity_waiter_instance = mock_entity_waiter.return_value
            mock_entity_waiter_instance.wait_for_required_entities = AsyncMock()
            
            await async_setup_entry(mock_hass, mock_config_entry_no_humidity)
            
            # Verify SensorManager called with None for humidity IDs  
            mock_sensor_manager.assert_called_with(
                mock_hass,
                room_sensor_id="sensor.room_temp", 
                outdoor_sensor_id=None,
                power_sensor_id=None,
                indoor_humidity_sensor_id=None,
                outdoor_humidity_sensor_id=None
            )

    @patch('custom_components.smart_climate.FeatureEngineering')
    async def test_feature_engineer_stored_in_entry_data(self, mock_feature_engineering, mock_hass, mock_config_entry):
        """Test feature_engineer is stored in entry_data for OffsetEngine access."""
        from custom_components.smart_climate import async_setup_entry
        
        # Create mock instance to verify it's stored
        mock_feature_engineer_instance = MagicMock()
        mock_feature_engineering.return_value = mock_feature_engineer_instance
        
        with patch('custom_components.smart_climate.EntityWaiter') as mock_entity_waiter, \
             patch('custom_components.smart_climate.SeasonalHysteresisLearner'), \
             patch('custom_components.smart_climate._async_setup_entity_persistence', new_callable=AsyncMock), \
             patch('custom_components.smart_climate._async_register_services', new_callable=AsyncMock), \
             patch.object(mock_hass.config_entries, 'async_forward_entry_setups', new_callable=AsyncMock):
            
            # Mock EntityWaiter async method
            mock_entity_waiter_instance = mock_entity_waiter.return_value
            mock_entity_waiter_instance.wait_for_required_entities = AsyncMock()
            
            await async_setup_entry(mock_hass, mock_config_entry)
            
            # Verify feature_engineer is stored in entry_data for later access by OffsetEngine
            entry_data = mock_hass.data['smart_climate']['test_entry']
            assert 'feature_engineer' in entry_data, "feature_engineer should be stored in entry_data"
            assert entry_data['feature_engineer'] == mock_feature_engineer_instance, "Same feature_engineer instance should be stored"

    @patch('custom_components.smart_climate.FeatureEngineering')  
    @patch('custom_components.smart_climate.SensorManager')
    async def test_full_component_chain(self, mock_sensor_manager, mock_feature_engineering, mock_hass, mock_config_entry):
        """Test full component chain wiring with humidity sensors."""
        from custom_components.smart_climate import async_setup_entry
        
        # Create mock instances
        mock_feature_engineer_instance = MagicMock()
        mock_sensor_manager_instance = MagicMock()
        
        mock_feature_engineering.return_value = mock_feature_engineer_instance
        mock_sensor_manager.return_value = mock_sensor_manager_instance
        
        with patch('custom_components.smart_climate.EntityWaiter') as mock_entity_waiter, \
             patch('custom_components.smart_climate.SeasonalHysteresisLearner'), \
             patch('custom_components.smart_climate._async_setup_entity_persistence', new_callable=AsyncMock), \
             patch('custom_components.smart_climate._async_register_services', new_callable=AsyncMock), \
             patch.object(mock_hass.config_entries, 'async_forward_entry_setups', new_callable=AsyncMock):
            
            # Mock EntityWaiter async method
            mock_entity_waiter_instance = mock_entity_waiter.return_value
            mock_entity_waiter_instance.wait_for_required_entities = AsyncMock()
            
            await async_setup_entry(mock_hass, mock_config_entry)
            
            # Verify all main components created with correct parameters
            mock_feature_engineering.assert_called_once_with()
            
            mock_sensor_manager.assert_called_once_with(
                mock_hass,
                room_sensor_id="sensor.room_temp",
                outdoor_sensor_id=None,
                power_sensor_id=None,
                indoor_humidity_sensor_id="sensor.indoor_humidity",
                outdoor_humidity_sensor_id="sensor.outdoor_humidity"  
            )
            
            # Verify components are stored in entry_data
            entry_data = mock_hass.data['smart_climate']['test_entry']
            assert 'feature_engineer' in entry_data
            assert entry_data['feature_engineer'] == mock_feature_engineer_instance
            assert 'sensor_manager' in entry_data
            assert entry_data['sensor_manager'] == mock_sensor_manager_instance

    @patch('custom_components.smart_climate.FeatureEngineering')
    @patch('custom_components.smart_climate.OffsetEngine')
    async def test_offset_engine_integration_with_feature_engineer(self, mock_offset_engine, mock_feature_engineering, mock_hass, mock_config_entry):
        """Integration test verifying OffsetEngine receives feature_engineer in persistence setup."""
        from custom_components.smart_climate import async_setup_entry, _async_setup_entity_persistence
        
        # Create mock instance
        mock_feature_engineer_instance = MagicMock()
        mock_feature_engineering.return_value = mock_feature_engineer_instance
        
        # Set up basic mocks for async_setup_entry
        with patch('custom_components.smart_climate.EntityWaiter') as mock_entity_waiter, \
             patch('custom_components.smart_climate.SeasonalHysteresisLearner'), \
             patch('custom_components.smart_climate._async_register_services', new_callable=AsyncMock), \
             patch.object(mock_hass.config_entries, 'async_forward_entry_setups', new_callable=AsyncMock):
            
            # Mock EntityWaiter
            mock_entity_waiter_instance = mock_entity_waiter.return_value
            mock_entity_waiter_instance.wait_for_required_entities = AsyncMock()
            
            # Run setup to wire components
            await async_setup_entry(mock_hass, mock_config_entry)
            
            # Now test _async_setup_entity_persistence directly with detailed mocking
            with patch('custom_components.smart_climate.SmartClimateDataStore') as mock_data_store, \
                 patch('custom_components.smart_climate.DataUpdateCoordinator') as mock_coordinator, \
                 patch('custom_components.smart_climate.PassiveThermalModel'), \
                 patch('custom_components.smart_climate.ThermalManager'), \
                 patch('custom_components.smart_climate.ProbeManager'), \
                 patch('custom_components.smart_climate.SmartClimateStatusSensor'):
                
                # Set up mocks for DataStore operations
                mock_data_store_instance = MagicMock()
                mock_data_store.return_value = mock_data_store_instance
                mock_offset_engine_instance = MagicMock()
                mock_offset_engine_instance.async_load_learning_data = AsyncMock(return_value=True)
                mock_offset_engine_instance.async_setup_periodic_save = AsyncMock(return_value=lambda: None)
                mock_offset_engine.return_value = mock_offset_engine_instance
                
                # Set up coordinator mock
                mock_coordinator_instance = MagicMock()
                mock_coordinator_instance.async_config_entry_first_refresh = AsyncMock()
                mock_coordinator.return_value = mock_coordinator_instance
                
                # Call _async_setup_entity_persistence directly
                await _async_setup_entity_persistence(mock_hass, mock_config_entry, "climate.test")
                
                # Verify OffsetEngine was called with feature_engineer
                assert mock_offset_engine.called, "OffsetEngine should have been instantiated"
                call_kwargs = mock_offset_engine.call_args.kwargs
                assert 'feature_engineer' in call_kwargs, "OffsetEngine should receive feature_engineer"
                assert call_kwargs['feature_engineer'] == mock_feature_engineer_instance, "Should receive the same feature_engineer instance"
                assert call_kwargs['hass'] == mock_hass, "Should receive hass"
                assert call_kwargs['entity_id'] == "climate.test", "Should receive entity_id"