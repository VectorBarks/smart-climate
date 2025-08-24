"""Test dashboard package structure and abstract base classes."""

import pytest
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from unittest.mock import Mock, patch


class TestTabBuilderAbstractClass:
    """Test the TabBuilder abstract base class."""
    
    def test_tab_builder_is_abstract(self):
        """Test that TabBuilder cannot be instantiated directly."""
        from custom_components.smart_climate.dashboard.base import TabBuilder
        
        # Should not be able to instantiate abstract class directly
        with pytest.raises(TypeError):
            TabBuilder()
            
    def test_tab_builder_abstract_methods_exist(self):
        """Test that TabBuilder has the required abstract methods."""
        # This test will pass after implementation
        try:
            from custom_components.smart_climate.dashboard.base import TabBuilder
            
            # Check that it's an abstract base class
            assert issubclass(TabBuilder, ABC)
            
            # Check abstract methods exist
            abstract_methods = TabBuilder.__abstractmethods__
            assert 'build_cards' in abstract_methods
            assert 'get_tab_config' in abstract_methods
            assert len(abstract_methods) == 2
            
        except ImportError:
            pytest.skip("TabBuilder not implemented yet")
    
    def test_concrete_implementation_must_implement_methods(self):
        """Test that concrete implementations must implement all abstract methods."""
        try:
            from custom_components.smart_climate.dashboard.base import TabBuilder
            
            # Test that incomplete implementation fails
            class IncompleteTabBuilder(TabBuilder):
                def build_cards(self, entity_id: str) -> List[dict]:
                    return []
                # Missing get_tab_config - should fail
            
            with pytest.raises(TypeError):
                IncompleteTabBuilder()
                
            # Test that complete implementation works
            class CompleteTabBuilder(TabBuilder):
                def build_cards(self, entity_id: str) -> List[dict]:
                    return [{'type': 'test', 'entity': entity_id}]
                
                def get_tab_config(self) -> dict:
                    return {'title': 'Test', 'icon': 'mdi:test', 'path': 'test'}
            
            # This should work
            builder = CompleteTabBuilder()
            assert isinstance(builder, TabBuilder)
            
        except ImportError:
            pytest.skip("TabBuilder not implemented yet")


class TestDashboardPackageStructure:
    """Test the dashboard package structure and imports."""
    
    def test_dashboard_package_imports(self):
        """Test that dashboard package can be imported."""
        # Should be able to import dashboard package
        import custom_components.smart_climate.dashboard
        assert custom_components.smart_climate.dashboard is not None
    
    def test_dashboard_init_file_exists(self):
        """Test that dashboard __init__.py exists and has required imports."""
        try:
            import custom_components.smart_climate.dashboard
            
            # Check that TabBuilder is available from package
            from custom_components.smart_climate.dashboard import TabBuilder
            assert TabBuilder is not None
            
        except ImportError:
            pytest.skip("Dashboard package not implemented yet")
    
    def test_base_module_imports(self):
        """Test that base module can be imported independently."""
        # Should be able to import TabBuilder directly from base module
        from custom_components.smart_climate.dashboard.base import TabBuilder
        assert TabBuilder is not None


class TestTabBuilderInterface:
    """Test the TabBuilder interface specifications."""
    
    def test_build_cards_signature(self):
        """Test build_cards method signature and return type."""
        try:
            from custom_components.smart_climate.dashboard.base import TabBuilder
            
            class TestBuilder(TabBuilder):
                def build_cards(self, entity_id: str) -> List[dict]:
                    return [
                        {'type': 'gauge', 'entity': f'sensor.{entity_id}_test'},
                        {'type': 'history-graph', 'entities': [f'sensor.{entity_id}_temp']}
                    ]
                
                def get_tab_config(self) -> dict:
                    return {'title': 'Test', 'icon': 'mdi:test', 'path': 'test'}
            
            builder = TestBuilder()
            result = builder.build_cards('test_climate')
            
            # Verify return type
            assert isinstance(result, list)
            assert all(isinstance(card, dict) for card in result)
            
            # Verify content structure
            assert len(result) == 2
            assert result[0]['type'] == 'gauge'
            assert result[0]['entity'] == 'sensor.test_climate_test'
            
        except ImportError:
            pytest.skip("TabBuilder not implemented yet")
    
    def test_get_tab_config_signature(self):
        """Test get_tab_config method signature and return type."""
        try:
            from custom_components.smart_climate.dashboard.base import TabBuilder
            
            class TestBuilder(TabBuilder):
                def build_cards(self, entity_id: str) -> List[dict]:
                    return []
                
                def get_tab_config(self) -> dict:
                    return {
                        'title': 'Overview',
                        'icon': 'mdi:view-dashboard',
                        'path': 'overview'
                    }
            
            builder = TestBuilder()
            result = builder.get_tab_config()
            
            # Verify return type
            assert isinstance(result, dict)
            
            # Verify required keys
            required_keys = {'title', 'icon', 'path'}
            assert all(key in result for key in required_keys)
            
            # Verify content
            assert result['title'] == 'Overview'
            assert result['icon'] == 'mdi:view-dashboard'
            assert result['path'] == 'overview'
            
        except ImportError:
            pytest.skip("TabBuilder not implemented yet")


class TestDashboardPackageIntegration:
    """Test integration aspects of the dashboard package."""
    
    def test_dashboard_package_structure(self):
        """Test that the dashboard package has the expected structure."""
        try:
            import custom_components.smart_climate.dashboard
            import custom_components.smart_climate.dashboard.base
            
            # Verify package can be imported
            assert hasattr(custom_components.smart_climate.dashboard, '__file__')
            
            # Verify base module exists
            assert hasattr(custom_components.smart_climate.dashboard.base, 'TabBuilder')
            
        except ImportError:
            pytest.skip("Dashboard package not fully implemented yet")
    
    def test_multiple_concrete_implementations(self):
        """Test that multiple concrete TabBuilder implementations can coexist."""
        try:
            from custom_components.smart_climate.dashboard.base import TabBuilder
            
            class OverviewTabBuilder(TabBuilder):
                def build_cards(self, entity_id: str) -> List[dict]:
                    return [{'type': 'thermostat', 'entity': f'climate.{entity_id}'}]
                
                def get_tab_config(self) -> dict:
                    return {'title': 'Overview', 'icon': 'mdi:view-dashboard', 'path': 'overview'}
            
            class ThermalTabBuilder(TabBuilder):
                def build_cards(self, entity_id: str) -> List[dict]:
                    return [{'type': 'history-graph', 'entities': [f'sensor.{entity_id}_thermal_state']}]
                
                def get_tab_config(self) -> dict:
                    return {'title': 'Thermal', 'icon': 'mdi:thermometer-lines', 'path': 'thermal'}
            
            # Both should be instantiable
            overview = OverviewTabBuilder()
            thermal = ThermalTabBuilder()
            
            # Both should be TabBuilder instances
            assert isinstance(overview, TabBuilder)
            assert isinstance(thermal, TabBuilder)
            
            # Both should have different configurations
            assert overview.get_tab_config()['path'] != thermal.get_tab_config()['path']
            
        except ImportError:
            pytest.skip("TabBuilder not implemented yet")


class TestDashboardFoundationRequirements:
    """Test requirements specific to the dashboard foundation step."""
    
    def test_no_concrete_implementations_yet(self):
        """Test that we only implement the foundation, no concrete tab builders."""
        try:
            # Should only have TabBuilder, not concrete implementations
            from custom_components.smart_climate.dashboard.base import TabBuilder
            
            # Check that module doesn't have concrete implementations yet
            import custom_components.smart_climate.dashboard.base as base_module
            
            # Get all classes from module
            classes = [getattr(base_module, name) for name in dir(base_module) 
                      if isinstance(getattr(base_module, name), type)]
            
            # Filter to only our classes (not ABC, etc)
            our_classes = [cls for cls in classes 
                          if hasattr(cls, '__module__') 
                          and cls.__module__ == 'custom_components.smart_climate.dashboard.base']
            
            # Should only have TabBuilder abstract class
            assert len(our_classes) == 1
            assert our_classes[0] is TabBuilder
            assert TabBuilder.__abstractmethods__  # Confirm it's abstract
            
        except ImportError:
            pytest.skip("TabBuilder not implemented yet")
    
    def test_clean_package_interface(self):
        """Test that the package exports clean interface."""
        try:
            import custom_components.smart_climate.dashboard as dashboard_pkg
            
            # Should be able to import TabBuilder from package
            assert hasattr(dashboard_pkg, 'TabBuilder')
            
            # TabBuilder should be the abstract base class
            from custom_components.smart_climate.dashboard import TabBuilder
            from abc import ABC
            assert issubclass(TabBuilder, ABC)
            
        except ImportError:
            pytest.skip("Dashboard package not implemented yet")