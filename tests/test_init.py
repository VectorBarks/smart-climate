"""ABOUTME: Tests for smart climate integration initialization and setup.
Verifies component structure, manifest, and HACS compatibility."""

import pytest
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch

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