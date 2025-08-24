"""
Comprehensive integration tests for DashboardGenerator.

Tests the complete dashboard generation system end-to-end including:
- All 5 tab builders working together
- YAML generation with placeholder substitution
- File operations with backup
- Error handling and validation
"""
import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
import yaml
import tempfile
import os

from custom_components.smart_climate.dashboard.generator import DashboardGenerator
from custom_components.smart_climate.dashboard.templates import GraphTemplates
from custom_components.smart_climate.dashboard.tooltips import TooltipProvider


class TestDashboardGeneratorInit:
    """Test DashboardGenerator initialization and setup."""
    
    def test_init_creates_all_builders(self):
        """Test that initialization creates all 5 tab builders."""
        generator = DashboardGenerator()
        
        assert hasattr(generator, '_templates')
        assert hasattr(generator, '_tooltips')
        assert hasattr(generator, '_builders')
        assert len(generator._builders) == 5
        
        expected_builders = {
            'overview', 'thermal', 'ml_performance', 
            'optimization', 'system_health'
        }
        assert set(generator._builders.keys()) == expected_builders
    
    def test_builders_have_correct_types(self):
        """Test that each builder is the correct class type."""
        generator = DashboardGenerator()
        
        from custom_components.smart_climate.dashboard.builders import (
            OverviewTabBuilder, ThermalMetricsTabBuilder, MLPerformanceTabBuilder
        )
        
        assert isinstance(generator._builders['overview'], OverviewTabBuilder)
        assert isinstance(generator._builders['thermal'], ThermalMetricsTabBuilder)
        assert isinstance(generator._builders['ml_performance'], MLPerformanceTabBuilder)
        # Note: optimization and system_health builders will be tested once implemented
    
    def test_shared_dependencies(self):
        """Test that all builders share the same template and tooltip instances."""
        generator = DashboardGenerator()
        
        for builder in generator._builders.values():
            assert builder._templates is generator._templates
            assert builder._tooltips is generator._tooltips


class TestDashboardGeneration:
    """Test complete dashboard generation functionality."""
    
    @pytest.fixture
    def generator(self):
        """Provide a DashboardGenerator instance for testing."""
        return DashboardGenerator()
    
    def test_generate_dashboard_basic(self, generator):
        """Test basic dashboard generation with valid inputs."""
        entity_id = "climate.smart_thermostat"
        friendly_name = "Living Room Climate"
        
        yaml_content = generator.generate_dashboard(entity_id, friendly_name)
        
        # Verify YAML is valid
        dashboard_data = yaml.safe_load(yaml_content)
        assert isinstance(dashboard_data, dict)
        
        # Verify title replacement
        expected_title = f"Smart Climate Advanced Analytics - {friendly_name}"
        assert dashboard_data['title'] == expected_title
        
        # Verify all 5 views exist
        assert 'views' in dashboard_data
        assert len(dashboard_data['views']) == 5
        
        view_paths = {view['path'] for view in dashboard_data['views']}
        expected_paths = {'overview', 'thermal', 'ml_performance', 'optimization', 'system_health'}
        assert view_paths == expected_paths
    
    def test_placeholder_substitution(self, generator):
        """Test that all placeholders are properly replaced."""
        entity_id = "climate.test_unit"
        friendly_name = "Test Climate"
        
        yaml_content = generator.generate_dashboard(entity_id, friendly_name)
        
        # Verify no placeholders remain
        assert "REPLACE_ME_ENTITY" not in yaml_content
        assert "REPLACE_ME_NAME" not in yaml_content
        
        # Verify entity_id appears in sensor references
        entity_name = entity_id.split('.')[1]
        assert f"sensor.{entity_name}_" in yaml_content
        assert entity_id in yaml_content
    
    def test_yaml_structure_completeness(self, generator):
        """Test that generated YAML has all required elements."""
        yaml_content = generator.generate_dashboard("climate.test", "Test")
        dashboard_data = yaml.safe_load(yaml_content)
        
        # Check top-level structure
        assert 'title' in dashboard_data
        assert 'views' in dashboard_data
        
        # Check each view structure
        for view in dashboard_data['views']:
            assert 'title' in view
            assert 'path' in view  
            assert 'icon' in view
            assert 'cards' in view
            assert isinstance(view['cards'], list)
            assert len(view['cards']) > 0
    
    def test_view_metadata_correctness(self, generator):
        """Test that each view has correct metadata."""
        yaml_content = generator.generate_dashboard("climate.test", "Test")
        dashboard_data = yaml.safe_load(yaml_content)
        
        views_by_path = {view['path']: view for view in dashboard_data['views']}
        
        # Overview tab
        overview = views_by_path['overview']
        assert overview['title'] == 'Overview'
        assert overview['icon'] == 'mdi:view-dashboard'
        
        # Thermal tab
        thermal = views_by_path['thermal']
        assert thermal['title'] == 'Thermal Metrics'
        assert thermal['icon'] == 'mdi:thermometer-lines'
        
        # ML Performance tab
        ml = views_by_path['ml_performance']
        assert ml['title'] == 'ML Performance'
        assert ml['icon'] == 'mdi:brain'
        
        # Optimization tab (will be implemented)
        optimization = views_by_path['optimization']
        assert optimization['title'] == 'Optimization'
        assert optimization['icon'] == 'mdi:tune'
        
        # System Health tab (will be implemented)
        health = views_by_path['system_health']
        assert health['title'] == 'System Health'
        assert health['icon'] == 'mdi:heart-pulse'
    
    def test_entity_id_variations(self, generator):
        """Test dashboard generation with various entity ID formats."""
        test_cases = [
            "climate.simple",
            "climate.with_underscore",
            "climate.with_dash_and_number_123",
            "climate.very_long_entity_name_with_multiple_parts"
        ]
        
        for entity_id in test_cases:
            yaml_content = generator.generate_dashboard(entity_id, "Test")
            dashboard_data = yaml.safe_load(yaml_content)
            
            # Should generate valid YAML
            assert isinstance(dashboard_data, dict)
            
            # Should contain entity references
            assert f"climate.{entity_id.split('.')[1]}" in yaml_content
    
    def test_friendly_name_special_characters(self, generator):
        """Test friendly names with special characters."""
        test_names = [
            "Living Room & Kitchen",
            "Master Bedroom (2nd Floor)",
            "Mom's Climate Control",
            "Test-Name_With.Various/Characters"
        ]
        
        for name in test_names:
            yaml_content = generator.generate_dashboard("climate.test", name)
            dashboard_data = yaml.safe_load(yaml_content)
            
            expected_title = f"Smart Climate Advanced Analytics - {name}"
            assert dashboard_data['title'] == expected_title


class TestFileOperations:
    """Test dashboard file saving and backup operations."""
    
    @pytest.fixture
    def temp_dashboard_path(self):
        """Create a temporary dashboard file path."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("# Existing dashboard content\ntitle: Old Dashboard")
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        backup_path = temp_path + '.backup'
        if os.path.exists(backup_path):
            os.unlink(backup_path)
    
    def test_save_dashboard_creates_backup(self, temp_dashboard_path):
        """Test that save_dashboard creates backup of existing file."""
        generator = DashboardGenerator()
        
        new_yaml = "title: New Dashboard\nviews: []"
        
        with patch('custom_components.smart_climate.dashboard.generator.DASHBOARD_PATH', temp_dashboard_path):
            generator.save_dashboard(new_yaml, backup=True)
        
        # Verify backup was created
        backup_path = temp_dashboard_path + '.backup'
        assert os.path.exists(backup_path)
        
        # Verify backup contains original content
        with open(backup_path, 'r') as f:
            backup_content = f.read()
        assert "Old Dashboard" in backup_content
        
        # Verify main file has new content
        with open(temp_dashboard_path, 'r') as f:
            new_content = f.read()
        assert "New Dashboard" in new_content
    
    def test_save_dashboard_no_backup(self, temp_dashboard_path):
        """Test saving without backup creation."""
        generator = DashboardGenerator()
        
        new_yaml = "title: New Dashboard\nviews: []"
        
        with patch('custom_components.smart_climate.dashboard.generator.DASHBOARD_PATH', temp_dashboard_path):
            generator.save_dashboard(new_yaml, backup=False)
        
        # Verify no backup was created
        backup_path = temp_dashboard_path + '.backup'
        assert not os.path.exists(backup_path)
        
        # Verify main file has new content
        with open(temp_dashboard_path, 'r') as f:
            new_content = f.read()
        assert "New Dashboard" in new_content
    
    def test_save_dashboard_atomic_write(self, temp_dashboard_path):
        """Test that save operation is atomic (doesn't leave partial file)."""
        generator = DashboardGenerator()
        
        # Simulate write failure
        with patch('custom_components.smart_climate.dashboard.generator.DASHBOARD_PATH', temp_dashboard_path):
            with patch('builtins.open', side_effect=IOError("Disk full")):
                with pytest.raises(IOError):
                    generator.save_dashboard("new content", backup=False)
        
        # Original file should still be intact
        with open(temp_dashboard_path, 'r') as f:
            content = f.read()
        assert "Old Dashboard" in content


class TestErrorHandling:
    """Test error handling and validation."""
    
    def test_invalid_entity_id_format(self):
        """Test handling of invalid entity ID formats."""
        generator = DashboardGenerator()
        
        invalid_ids = [
            "",  # Empty
            "invalid",  # No domain
            "climate.",  # Missing entity
            ".test",  # Missing domain
            "climate.with spaces",  # Spaces not allowed
        ]
        
        for invalid_id in invalid_ids:
            with pytest.raises(ValueError, match="Invalid entity ID"):
                generator.generate_dashboard(invalid_id, "Test")
    
    def test_empty_friendly_name(self):
        """Test handling of empty friendly name."""
        generator = DashboardGenerator()
        
        with pytest.raises(ValueError, match="Friendly name cannot be empty"):
            generator.generate_dashboard("climate.test", "")
        
        with pytest.raises(ValueError, match="Friendly name cannot be empty"):
            generator.generate_dashboard("climate.test", None)
    
    def test_yaml_validation_failure(self):
        """Test handling of invalid YAML generation."""
        generator = DashboardGenerator()
        
        # Mock a builder to return invalid YAML structure (using object() which is not serializable)
        class NonSerializable:
            pass
        with patch.object(generator._builders['overview'], 'build_cards', 
                          return_value=[{'invalid': NonSerializable()}]):
            with pytest.raises(ValueError, match="Generated YAML is invalid"):
                generator.generate_dashboard("climate.test", "Test")
    
    def test_missing_builder_handling(self):
        """Test graceful handling when a builder is missing."""
        generator = DashboardGenerator()
        
        # Remove a builder to simulate missing implementation
        del generator._builders['optimization']
        
        with pytest.raises(KeyError, match="Missing required tab builder"):
            generator.generate_dashboard("climate.test", "Test")


class TestIntegrationScenarios:
    """Test complete integration scenarios."""
    
    def test_end_to_end_generation(self):
        """Test complete end-to-end dashboard generation."""
        generator = DashboardGenerator()
        
        entity_id = "climate.living_room"
        friendly_name = "Living Room Thermostat"
        
        # Generate dashboard
        yaml_content = generator.generate_dashboard(entity_id, friendly_name)
        
        # Parse and validate structure
        dashboard_data = yaml.safe_load(yaml_content)
        
        # Verify complete structure
        assert dashboard_data['title'] == f"Smart Climate Advanced Analytics - {friendly_name}"
        assert len(dashboard_data['views']) == 5
        
        # Verify each tab has proper structure
        for view in dashboard_data['views']:
            assert 'title' in view
            assert 'path' in view
            assert 'icon' in view
            assert 'cards' in view
            assert len(view['cards']) > 0
            
            # Verify cards have proper structure
            for card in view['cards']:
                assert 'type' in card
                # Card should have entity references replaced
                card_yaml = yaml.dump(card)
                assert "REPLACE_ME" not in card_yaml
    
    def test_dashboard_yaml_home_assistant_compatibility(self):
        """Test that generated YAML is compatible with Home Assistant."""
        generator = DashboardGenerator()
        
        yaml_content = generator.generate_dashboard("climate.test", "Test")
        dashboard_data = yaml.safe_load(yaml_content)
        
        # Check Home Assistant dashboard requirements
        assert 'title' in dashboard_data
        assert 'views' in dashboard_data
        
        for view in dashboard_data['views']:
            # Each view must have these fields
            assert 'title' in view
            assert 'cards' in view
            
            # Optional but commonly used
            if 'path' in view:
                assert isinstance(view['path'], str)
            if 'icon' in view:
                assert view['icon'].startswith('mdi:')
            
            # Cards must be valid
            for card in view['cards']:
                assert 'type' in card
                # Type should be a known HA card type or custom card
                card_type = card['type']
                valid_types = [
                    'gauge', 'entities', 'thermostat', 'history-graph',
                    'statistics-graph', 'custom:apexcharts-card', 
                    'custom:plotly-graph-card', 'custom:mini-graph-card',
                    'custom:button-card'
                ]
                # Should be one of the known types (may have variations)
                assert any(card_type.startswith(t) for t in valid_types)
    
    def test_sensor_entity_references(self):
        """Test that all sensor entity references are properly formatted."""
        generator = DashboardGenerator()
        
        entity_id = "climate.bedroom"
        yaml_content = generator.generate_dashboard(entity_id, "Bedroom")
        
        # Extract entity name
        entity_name = entity_id.split('.')[1]
        
        # Should contain various sensor references
        expected_sensors = [
            f"sensor.{entity_name}_offset_current",
            f"sensor.{entity_name}_confidence",
            f"sensor.{entity_name}_thermal_state",
            f"sensor.{entity_name}_tau_cooling",
            f"sensor.{entity_name}_cycle_health"
        ]
        
        for sensor in expected_sensors:
            assert sensor in yaml_content
        
        # Should contain climate entity reference
        assert entity_id in yaml_content
    
    @patch('custom_components.smart_climate.dashboard.generator.DASHBOARD_PATH')
    def test_complete_workflow_with_file_operations(self, mock_path):
        """Test complete workflow including file operations."""
        # Setup mock file path
        mock_path.return_value = "/tmp/test_dashboard.yaml"
        
        generator = DashboardGenerator()
        
        # Generate dashboard
        yaml_content = generator.generate_dashboard("climate.test", "Test")
        
        # Mock file operations
        with patch('builtins.open', mock_open()) as mock_file:
            generator.save_dashboard(yaml_content, backup=True)
            
            # Verify file was written
            mock_file.assert_called()
            handle = mock_file()
            written_content = ''.join(call.args[0] for call in handle.write.call_args_list)
            
            # Verify content was written correctly
            assert "Smart Climate Advanced Analytics - Test" in written_content
            assert "REPLACE_ME" not in written_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])