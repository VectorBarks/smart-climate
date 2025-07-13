"""
ABOUTME: Comprehensive integration loading test validating HA integration loads successfully.
Tests verify HVACMode import fix and all modules can be imported without errors.
"""

import pytest
import sys
import importlib
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

import homeassistant.core as ha_core
from homeassistant.const import Platform


class TestIntegrationLoading:
    """Test integration loading after HVACMode import fix."""
    
    def test_core_integration_module_imports(self):
        """Test that core integration module can be imported."""
        try:
            import custom_components.smart_climate
            assert custom_components.smart_climate is not None
            
            # Verify version info is accessible
            assert hasattr(custom_components.smart_climate, '__version__')
            assert hasattr(custom_components.smart_climate, '__author__')
        except ImportError as e:
            pytest.fail(f"Failed to import smart_climate integration: {e}")

    def test_delay_learner_module_imports_correctly(self):
        """Test that delay_learner module imports without HVACMode errors."""
        try:
            from custom_components.smart_climate.delay_learner import DelayLearner
            
            # Verify class can be imported and accessed
            assert DelayLearner is not None
            assert callable(DelayLearner)
            
            # Verify basic class structure exists
            assert hasattr(DelayLearner, '__init__')
            
        except ImportError as e:
            pytest.fail(f"Failed to import DelayLearner after HVACMode fix: {e}")

    def test_hvacmode_available_from_correct_location(self):
        """Test that HVACMode is accessible from correct import location."""
        try:
            from homeassistant.components.climate.const import HVACMode
            
            # Verify enum values are accessible
            assert hasattr(HVACMode, 'OFF')
            assert hasattr(HVACMode, 'COOL')
            assert hasattr(HVACMode, 'HEAT')
            assert hasattr(HVACMode, 'AUTO')
            
            # Verify it's an actual enum
            assert HVACMode.OFF != HVACMode.COOL
            
        except ImportError as e:
            pytest.fail(f"Failed to import HVACMode from correct location: {e}")

    def test_climate_platform_module_imports(self):
        """Test that climate platform module imports correctly."""
        try:
            from custom_components.smart_climate.climate import SmartClimateEntity
            
            # Verify class can be imported
            assert SmartClimateEntity is not None
            assert callable(SmartClimateEntity)
            
            # Verify it's a proper HA climate entity
            from homeassistant.components.climate import ClimateEntity
            assert issubclass(SmartClimateEntity, ClimateEntity)
            
        except ImportError as e:
            pytest.fail(f"Failed to import climate platform: {e}")

    def test_sensor_platform_module_imports(self):
        """Test that sensor platform module imports correctly."""
        try:
            import custom_components.smart_climate.sensor
            assert custom_components.smart_climate.sensor is not None
            
        except ImportError as e:
            pytest.fail(f"Failed to import sensor platform: {e}")

    def test_switch_platform_module_imports(self):
        """Test that switch platform module imports correctly."""
        try:
            import custom_components.smart_climate.switch
            assert custom_components.smart_climate.switch is not None
            
        except ImportError as e:
            pytest.fail(f"Failed to import switch platform: {e}")

    def test_all_core_modules_import_without_errors(self):
        """Test that all core modules can be imported without errors."""
        core_modules = [
            'custom_components.smart_climate.const',
            'custom_components.smart_climate.models',
            'custom_components.smart_climate.data_store',
            'custom_components.smart_climate.offset_engine',
            'custom_components.smart_climate.lightweight_learner',
            'custom_components.smart_climate.sensor_manager',
            'custom_components.smart_climate.mode_manager',
            'custom_components.smart_climate.temperature_controller',
            'custom_components.smart_climate.delay_learner',
        ]
        
        import_errors = []
        
        for module_name in core_modules:
            try:
                module = importlib.import_module(module_name)
                assert module is not None
            except ImportError as e:
                import_errors.append(f"{module_name}: {e}")
        
        if import_errors:
            pytest.fail(f"Failed to import core modules: {import_errors}")

    @pytest.mark.asyncio
    async def test_integration_setup_function_exists(self):
        """Test that integration setup function exists and is callable."""
        try:
            from custom_components.smart_climate import async_setup_entry
            
            # Verify setup function exists
            assert async_setup_entry is not None
            assert callable(async_setup_entry)
            
        except ImportError as e:
            pytest.fail(f"Failed to import setup function: {e}")

    def test_platform_constants_accessible(self):
        """Test that platform constants are accessible."""
        try:
            from custom_components.smart_climate.const import DOMAIN, PLATFORMS
            
            # Verify domain is defined
            assert DOMAIN is not None
            assert isinstance(DOMAIN, str)
            assert len(DOMAIN) > 0
            
            # Verify platforms list exists
            assert PLATFORMS is not None
            assert isinstance(PLATFORMS, list)
            assert len(PLATFORMS) > 0
            
            # Verify expected platforms are present
            expected_platforms = [Platform.CLIMATE, Platform.SENSOR, Platform.SWITCH]
            for platform in expected_platforms:
                assert platform in PLATFORMS
                
        except ImportError as e:
            pytest.fail(f"Failed to import integration constants: {e}")


class TestHVACModeImportFix:
    """Specific tests for HVACMode import fix validation."""
    
    def test_delay_learner_uses_correct_hvacmode_import(self):
        """Test that delay_learner.py uses correct HVACMode import path."""
        import ast
        import os
        
        # Check delay_learner.py source code
        delay_learner_path = "custom_components/smart_climate/delay_learner.py"
        assert os.path.exists(delay_learner_path), "delay_learner.py not found"
        
        with open(delay_learner_path, 'r') as f:
            content = f.read()
            
        # Parse file as AST to check imports
        tree = ast.parse(content)
        
        correct_import_found = False
        deprecated_import_found = False
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if (node.module == "homeassistant.components.climate.const" and 
                    any(alias.name == "HVACMode" for alias in node.names)):
                    correct_import_found = True
                elif (node.module == "homeassistant.const" and 
                      any(alias.name == "HVACMode" for alias in node.names)):
                    deprecated_import_found = True
        
        assert correct_import_found, "delay_learner.py missing correct HVACMode import"
        assert not deprecated_import_found, "delay_learner.py still has deprecated HVACMode import"

    def test_climate_entity_uses_correct_hvacmode_import(self):
        """Test that climate.py uses correct HVACMode import path."""
        import ast
        import os
        
        # Check climate.py source code
        climate_path = "custom_components/smart_climate/climate.py"
        assert os.path.exists(climate_path), "climate.py not found"
        
        with open(climate_path, 'r') as f:
            content = f.read()
            
        # Parse file as AST to check imports
        tree = ast.parse(content)
        
        correct_import_found = False
        deprecated_import_found = False
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if (node.module == "homeassistant.components.climate.const" and 
                    any(alias.name == "HVACMode" for alias in node.names)):
                    correct_import_found = True
                elif (node.module == "homeassistant.const" and 
                      any(alias.name == "HVACMode" for alias in node.names)):
                    deprecated_import_found = True
        
        assert correct_import_found, "climate.py missing correct HVACMode import"
        assert not deprecated_import_found, "climate.py still has deprecated HVACMode import"

    def test_all_modules_hvacmode_imports_consistency(self):
        """Test that all modules using HVACMode use consistent import path."""
        import ast
        import os
        import glob
        
        # Find all Python files in the integration
        py_files = glob.glob("custom_components/smart_climate/*.py")
        py_files.extend(glob.glob("tests/test_*.py"))
        
        import_issues = []
        
        for file_path in py_files:
            if not os.path.exists(file_path):
                continue
                
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                tree = ast.parse(content)
                
                has_deprecated_import = False
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if (node.module == "homeassistant.const" and 
                            any(alias.name == "HVACMode" for alias in node.names)):
                            has_deprecated_import = True
                            break
                
                if has_deprecated_import:
                    import_issues.append(f"{file_path}: still uses deprecated HVACMode import")
                    
            except (SyntaxError, UnicodeDecodeError):
                # Skip files that can't be parsed
                continue
        
        if import_issues:
            pytest.fail(f"Found deprecated HVACMode imports: {import_issues}")


class TestPlatformLoading:
    """Test loading of specific platforms after import fixes."""

    @pytest.mark.asyncio
    async def test_climate_platform_async_setup_exists(self):
        """Test that climate platform has async_setup_platform function."""
        try:
            from custom_components.smart_climate.climate import async_setup_entry as climate_setup
            
            assert climate_setup is not None
            assert callable(climate_setup)
            
        except ImportError as e:
            pytest.fail(f"Failed to import climate platform setup: {e}")

    @pytest.mark.asyncio 
    async def test_sensor_platform_async_setup_exists(self):
        """Test that sensor platform has async_setup_platform function."""
        try:
            from custom_components.smart_climate.sensor import async_setup_entry as sensor_setup
            
            assert sensor_setup is not None
            assert callable(sensor_setup)
            
        except ImportError as e:
            pytest.fail(f"Failed to import sensor platform setup: {e}")

    @pytest.mark.asyncio
    async def test_switch_platform_async_setup_exists(self):
        """Test that switch platform has async_setup_platform function."""
        try:
            from custom_components.smart_climate.switch import async_setup_entry as switch_setup
            
            assert switch_setup is not None
            assert callable(switch_setup)
            
        except ImportError as e:
            pytest.fail(f"Failed to import switch platform setup: {e}")


class TestIntegrationManifest:
    """Test integration manifest and metadata loading."""
    
    def test_manifest_file_exists_and_valid(self):
        """Test that manifest.json exists and contains required fields."""
        import json
        import os
        
        manifest_path = "custom_components/smart_climate/manifest.json"
        assert os.path.exists(manifest_path), "manifest.json not found"
        
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Verify required manifest fields
        required_fields = ["domain", "name", "version", "requirements", "dependencies"]
        for field in required_fields:
            assert field in manifest, f"Required field '{field}' missing from manifest"
        
        # Verify domain matches
        from custom_components.smart_climate.const import DOMAIN
        assert manifest["domain"] == DOMAIN, "Manifest domain doesn't match const DOMAIN"

    def test_translation_files_structure(self):
        """Test that translation files exist and are structured correctly."""
        import os
        import json
        
        # Check if translations directory exists
        translations_dir = "custom_components/smart_climate/translations"
        if os.path.exists(translations_dir):
            # Check for at least English translations
            en_file = os.path.join(translations_dir, "en.json")
            if os.path.exists(en_file):
                with open(en_file, 'r') as f:
                    translations = json.load(f)
                    
                # Verify basic structure exists
                assert "config" in translations, "Missing config translations"


class TestEdgeCaseScenarios:
    """Test edge cases and error scenarios for integration loading."""
    
    def test_import_with_missing_dependencies_graceful_handling(self):
        """Test graceful handling when optional dependencies are missing."""
        # This would test behavior when scikit-learn is not available
        # Since it's an optional dependency, integration should still load
        
        with patch.dict('sys.modules', {'sklearn': None, 'pandas': None}):
            try:
                # Core integration should still import
                import custom_components.smart_climate
                assert custom_components.smart_climate is not None
                
                # DelayLearner should still work without optional ML features
                from custom_components.smart_climate.delay_learner import DelayLearner
                assert DelayLearner is not None
                
            except ImportError as e:
                pytest.fail(f"Integration failed with missing optional dependencies: {e}")

    def test_import_with_module_reload(self):
        """Test that modules can be reloaded without import errors."""
        import importlib
        
        try:
            # Import, then reload main module
            import custom_components.smart_climate
            importlib.reload(custom_components.smart_climate)
            
            # Import, then reload delay_learner 
            from custom_components.smart_climate import delay_learner
            importlib.reload(delay_learner)
            
            # Verify DelayLearner is still accessible after reload
            from custom_components.smart_climate.delay_learner import DelayLearner
            assert DelayLearner is not None
            
        except Exception as e:
            pytest.fail(f"Module reload failed: {e}")

    def test_circular_import_prevention(self):
        """Test that there are no circular import issues."""
        # Import all modules simultaneously to detect circular imports
        modules_to_test = [
            'custom_components.smart_climate',
            'custom_components.smart_climate.climate',
            'custom_components.smart_climate.sensor', 
            'custom_components.smart_climate.switch',
            'custom_components.smart_climate.delay_learner',
            'custom_components.smart_climate.offset_engine',
            'custom_components.smart_climate.lightweight_learner',
        ]
        
        import_results = {}
        
        for module_name in modules_to_test:
            try:
                module = importlib.import_module(module_name)
                import_results[module_name] = "success"
            except ImportError as e:
                import_results[module_name] = f"failed: {e}"
        
        failed_imports = {k: v for k, v in import_results.items() if "failed" in v}
        
        if failed_imports:
            pytest.fail(f"Circular import issues detected: {failed_imports}")