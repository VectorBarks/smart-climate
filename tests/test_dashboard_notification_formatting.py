"""Test dashboard notification message formatting with YAML code blocks."""
# ABOUTME: Tests for proper YAML code block formatting in dashboard notifications
# Validates markdown code blocks, copying functionality, readability, and edge cases

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
import pytest

# Define mock exception class
class ServiceValidationError(Exception):
    """Mock ServiceValidationError."""
    pass

# Mock homeassistant exceptions module
import sys
if 'homeassistant.exceptions' not in sys.modules:
    sys.modules['homeassistant.exceptions'] = Mock()
sys.modules['homeassistant.exceptions'].ServiceValidationError = ServiceValidationError

from custom_components.smart_climate import (
    DOMAIN,
    _async_register_services,
)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.services = Mock()
    hass.services.has_service = Mock(return_value=False)
    hass.services.async_register = Mock()
    hass.states = Mock()
    hass.states.get = Mock()
    hass.data = {DOMAIN: {}}
    # CRITICAL: Mock async_add_executor_job to return awaitable results
    hass.async_add_executor_job = AsyncMock()
    return hass


@pytest.fixture
def mock_service_call():
    """Create a mock service call."""
    call = Mock()
    call.data = {"climate_entity_id": "climate.test_ac"}
    return call


@pytest.fixture
def standard_entity_setup(mock_hass):
    """Standard entity setup for most tests."""
    with patch("custom_components.smart_climate.er") as mock_er:
        with patch("custom_components.smart_climate.async_create_notification") as mock_notify:
            mock_registry = Mock()
            mock_er.async_get.return_value = mock_registry
            
            # Entity exists and is from smart_climate
            mock_entity = Mock()
            mock_entity.platform = DOMAIN
            mock_entity.config_entry_id = "test_config_entry"
            mock_registry.async_get.return_value = mock_entity
            mock_registry.entities = {"climate.test_ac": mock_entity}
            
            # Mock state
            mock_state = Mock()
            mock_state.attributes = {"friendly_name": "Test AC"}
            mock_hass.states.get.return_value = mock_state
            
            yield mock_er, mock_notify, mock_registry, mock_entity, mock_state


@pytest.mark.asyncio
async def test_yaml_content_wrapped_in_markdown_code_blocks(mock_hass, mock_service_call, standard_entity_setup):
    """Test that notification message includes YAML content wrapped in markdown code blocks."""
    mock_er, mock_notify, mock_registry, mock_entity, mock_state = standard_entity_setup
    
    # Template content with YAML structure
    template_content = """title: Smart Climate - REPLACE_ME_NAME
views:
  - title: Overview
    cards:
      - type: thermostat
        entity: REPLACE_ME_CLIMATE
      - type: gauge
        entity: REPLACE_ME_SENSOR_OFFSET"""
    
    mock_hass.async_add_executor_job.return_value = template_content
    
    with patch("os.path.exists", return_value=True):
        # Register services
        await _async_register_services(mock_hass)
        
        # Get the service handler
        service_handler = mock_hass.services.async_register.call_args[0][2]
        
        # Call service
        await service_handler(mock_service_call)
    
    # Verify notification was created with code blocks
    mock_notify.assert_called_once()
    notification_args = mock_notify.call_args[1]
    message = notification_args["message"]
    
    # Check for markdown code block wrapper
    assert "```yaml" in message
    assert "```" in message
    
    # Verify YAML content is inside code blocks
    lines = message.split('\n')
    yaml_start_found = False
    yaml_end_found = False
    yaml_content_found = False
    
    for line in lines:
        if line.strip() == "```yaml":
            yaml_start_found = True
        elif yaml_start_found and not yaml_end_found and line.strip() == "```":
            yaml_end_found = True
        elif yaml_start_found and not yaml_end_found:
            if "title:" in line or "views:" in line or "cards:" in line:
                yaml_content_found = True
    
    assert yaml_start_found, "YAML code block start (```yaml) not found"
    assert yaml_end_found, "YAML code block end (```) not found"
    assert yaml_content_found, "YAML content not found inside code blocks"


@pytest.mark.asyncio
async def test_code_block_format_allows_easy_copying(mock_hass, mock_service_call, standard_entity_setup):
    """Test that the code block format allows for easy copying."""
    mock_er, mock_notify, mock_registry, mock_entity, mock_state = standard_entity_setup
    
    # Template content with indented YAML
    template_content = """title: Smart Climate - REPLACE_ME_NAME
views:
  - title: Overview
    path: overview
    cards:
      - type: thermostat
        entity: REPLACE_ME_CLIMATE
      - type: horizontal-stack
        cards:
          - type: gauge
            entity: REPLACE_ME_SENSOR_OFFSET
          - type: gauge
            entity: REPLACE_ME_SENSOR_PROGRESS"""
    
    mock_hass.async_add_executor_job.return_value = template_content
    
    with patch("os.path.exists", return_value=True):
        # Register services
        await _async_register_services(mock_hass)
        
        # Get the service handler
        service_handler = mock_hass.services.async_register.call_args[0][2]
        
        # Call service
        await service_handler(mock_service_call)
    
    # Verify notification message structure
    mock_notify.assert_called_once()
    notification_args = mock_notify.call_args[1]
    message = notification_args["message"]
    
    # Check that code block preserves indentation
    lines = message.split('\n')
    yaml_lines = []
    in_yaml_block = False
    
    for line in lines:
        if line.strip() == "```yaml":
            in_yaml_block = True
            continue
        elif in_yaml_block and line.strip() == "```":
            in_yaml_block = False
            break
        elif in_yaml_block:
            yaml_lines.append(line)
    
    # Verify proper indentation is preserved
    assert any("  - title: Overview" in line for line in yaml_lines), "YAML indentation not preserved"
    assert any("    path: overview" in line for line in yaml_lines), "Nested YAML indentation not preserved"
    assert any("      - type: thermostat" in line for line in yaml_lines), "Deep YAML indentation not preserved"
    
    # Verify no extra leading/trailing whitespace that would break copying
    yaml_content = '\n'.join(yaml_lines)
    assert not yaml_content.startswith(' '), "Extra leading whitespace found"
    assert not yaml_content.endswith(' '), "Extra trailing whitespace found"


@pytest.mark.asyncio
async def test_instructions_remain_clear_and_readable(mock_hass, mock_service_call, standard_entity_setup):
    """Test that instructions remain clear and readable around the code block."""
    mock_er, mock_notify, mock_registry, mock_entity, mock_state = standard_entity_setup
    
    template_content = "title: Smart Climate - REPLACE_ME_NAME"
    mock_hass.async_add_executor_job.return_value = template_content
    
    with patch("os.path.exists", return_value=True):
        # Register services
        await _async_register_services(mock_hass)
        
        # Get the service handler
        service_handler = mock_hass.services.async_register.call_args[0][2]
        
        # Call service
        await service_handler(mock_service_call)
    
    # Verify notification includes clear instructions
    mock_notify.assert_called_once()
    notification_args = mock_notify.call_args[1]
    message = notification_args["message"]
    
    # Check for key instruction components
    assert "Copy the YAML below" in message
    assert "Settings → Dashboards" in message or "Settings" in message and "Dashboards" in message
    assert "Add Dashboard" in message
    assert "Raw Configuration Editor" in message or "Raw" in message
    
    # Verify instructions are separated from code block
    lines = message.split('\n')
    
    # Find instruction text before code block
    yaml_start_index = None
    instruction_lines = []
    
    for i, line in enumerate(lines):
        if line.strip() == "```yaml":
            yaml_start_index = i
            break
        instruction_lines.append(line)
    
    assert yaml_start_index is not None, "YAML code block start not found"
    
    # Verify instructions appear before code block
    instruction_text = '\n'.join(instruction_lines)
    assert len(instruction_text.strip()) > 0, "No instructions found before code block"
    assert "Copy" in instruction_text, "Copy instruction not found before code block"


@pytest.mark.asyncio
async def test_empty_yaml_content_handling(mock_hass, mock_service_call, standard_entity_setup):
    """Test handling of empty YAML content."""
    mock_er, mock_notify, mock_registry, mock_entity, mock_state = standard_entity_setup
    
    # Empty template content
    template_content = ""
    mock_hass.async_add_executor_job.return_value = template_content
    
    with patch("os.path.exists", return_value=True):
        # Register services
        await _async_register_services(mock_hass)
        
        # Get the service handler
        service_handler = mock_hass.services.async_register.call_args[0][2]
        
        # Call service
        await service_handler(mock_service_call)
    
    # Verify notification handles empty content gracefully
    mock_notify.assert_called_once()
    notification_args = mock_notify.call_args[1]
    message = notification_args["message"]
    
    # Should still have code block structure even with empty content
    assert "```yaml" in message
    assert message.count("```") >= 2, "Code block not properly closed"
    
    # Verify instructions are still present
    assert "Copy the YAML below" in message
    
    # Check that empty content doesn't break formatting
    lines = message.split('\n')
    yaml_start_found = False
    yaml_end_found = False
    
    for line in lines:
        if line.strip() == "```yaml":
            yaml_start_found = True
        elif yaml_start_found and line.strip() == "```":
            yaml_end_found = True
            break
    
    assert yaml_start_found and yaml_end_found, "Code block structure broken with empty content"


@pytest.mark.asyncio
async def test_special_characters_in_yaml_content(mock_hass, mock_service_call, standard_entity_setup):
    """Test handling of special characters in YAML content."""
    mock_er, mock_notify, mock_registry, mock_entity, mock_state = standard_entity_setup
    
    # YAML content with special characters
    template_content = """title: "Smart Climate - REPLACE_ME_NAME & More"
views:
  - title: "Overview 100% Awesome"
    cards:
      - type: markdown
        content: |
          # Header with *italics* and **bold**
          - Bullet point with émojis: 🌡️ 🏠
          - Special chars: @#$%^&*()
          - Unicode: ñáéíóú αβγδ 中文
      - type: gauge
        entity: REPLACE_ME_SENSOR_OFFSET
        name: "Temperature ±5°C"
        unit: "°C/°F" """
    
    mock_hass.async_add_executor_job.return_value = template_content
    
    with patch("os.path.exists", return_value=True):
        # Register services
        await _async_register_services(mock_hass)
        
        # Get the service handler
        service_handler = mock_hass.services.async_register.call_args[0][2]
        
        # Call service
        await service_handler(mock_service_call)
    
    # Verify notification handles special characters correctly
    mock_notify.assert_called_once()
    notification_args = mock_notify.call_args[1]
    message = notification_args["message"]
    
    # Check that special characters are preserved in code block
    assert "🌡️ 🏠" in message
    assert "@#$%^&*()" in message
    assert "ñáéíóú αβγδ 中文" in message
    assert "±5°C" in message
    assert "°C/°F" in message
    
    # Verify markdown formatting characters are preserved (not interpreted)
    assert "*italics*" in message
    assert "**bold**" in message
    assert "# Header" in message
    
    # Ensure code block structure is intact
    assert "```yaml" in message
    lines = message.split('\n')
    yaml_content_lines = []
    in_yaml_block = False
    
    for line in lines:
        if line.strip() == "```yaml":
            in_yaml_block = True
            continue
        elif in_yaml_block and line.strip() == "```":
            break
        elif in_yaml_block:
            yaml_content_lines.append(line)
    
    yaml_content = '\n'.join(yaml_content_lines)
    
    # Verify all special characters are in the YAML content section
    assert "🌡️ 🏠" in yaml_content
    assert "ñáéíóú αβγδ 中文" in yaml_content


@pytest.mark.asyncio
async def test_yaml_syntax_highlighting_specification(mock_hass, mock_service_call, standard_entity_setup):
    """Test that YAML syntax highlighting is properly specified."""
    mock_er, mock_notify, mock_registry, mock_entity, mock_state = standard_entity_setup
    
    template_content = """title: Smart Climate - REPLACE_ME_NAME
views:
  - title: Overview"""
    
    mock_hass.async_add_executor_job.return_value = template_content
    
    with patch("os.path.exists", return_value=True):
        # Register services
        await _async_register_services(mock_hass)
        
        # Get the service handler
        service_handler = mock_hass.services.async_register.call_args[0][2]
        
        # Call service
        await service_handler(mock_service_call)
    
    # Verify notification uses proper syntax highlighting
    mock_notify.assert_called_once()
    notification_args = mock_notify.call_args[1]
    message = notification_args["message"]
    
    # Must use "yaml" language specification for syntax highlighting
    assert "```yaml" in message
    
    # Should not use generic code blocks
    assert "```\n" not in message.replace("```yaml", "").replace("yaml\n", "")
    
    # Verify proper structure: ```yaml ... content ... ```
    lines = message.split('\n')
    yaml_start_line = None
    yaml_end_line = None
    
    for i, line in enumerate(lines):
        if line.strip() == "```yaml":
            yaml_start_line = i
        elif yaml_start_line is not None and line.strip() == "```":
            yaml_end_line = i
            break
    
    assert yaml_start_line is not None, "YAML code block start not found"
    assert yaml_end_line is not None, "YAML code block end not found"
    assert yaml_end_line > yaml_start_line + 1, "No content between YAML code block markers"


@pytest.mark.asyncio
async def test_multiple_code_blocks_not_created(mock_hass, mock_service_call, standard_entity_setup):
    """Test that only one YAML code block is created, not multiple."""
    mock_er, mock_notify, mock_registry, mock_entity, mock_state = standard_entity_setup
    
    template_content = """title: Smart Climate - REPLACE_ME_NAME
views:
  - title: Overview
    cards:
      - type: gauge"""
    
    mock_hass.async_add_executor_job.return_value = template_content
    
    with patch("os.path.exists", return_value=True):
        # Register services
        await _async_register_services(mock_hass)
        
        # Get the service handler
        service_handler = mock_hass.services.async_register.call_args[0][2]
        
        # Call service
        await service_handler(mock_service_call)
    
    # Verify only one code block is created
    mock_notify.assert_called_once()
    notification_args = mock_notify.call_args[1]
    message = notification_args["message"]
    
    # Count occurrences of code block markers
    yaml_start_count = message.count("```yaml")
    yaml_end_count = message.count("```") - yaml_start_count  # Total ``` minus ```yaml
    
    assert yaml_start_count == 1, f"Expected 1 '```yaml' marker, found {yaml_start_count}"
    assert yaml_end_count == 1, f"Expected 1 closing '```' marker, found {yaml_end_count}"
    
    # Verify single code block structure
    lines = message.split('\n')
    code_block_markers = [i for i, line in enumerate(lines) if line.strip().startswith("```")]
    
    assert len(code_block_markers) == 2, f"Expected exactly 2 code block markers, found {len(code_block_markers)}"
    
    # First should be ```yaml, second should be ```
    assert lines[code_block_markers[0]].strip() == "```yaml"
    assert lines[code_block_markers[1]].strip() == "```"


@pytest.mark.asyncio
async def test_code_block_preserves_line_breaks(mock_hass, mock_service_call, standard_entity_setup):
    """Test that code block preserves line breaks and formatting."""
    mock_er, mock_notify, mock_registry, mock_entity, mock_state = standard_entity_setup
    
    # Template with specific line break patterns
    template_content = """title: Smart Climate - REPLACE_ME_NAME

views:
  - title: Overview
    path: overview
    
    cards:
      - type: thermostat
        entity: REPLACE_ME_CLIMATE
        
      - type: horizontal-stack
        cards:
          - type: gauge
            entity: REPLACE_ME_SENSOR_OFFSET"""
    
    mock_hass.async_add_executor_job.return_value = template_content
    
    with patch("os.path.exists", return_value=True):
        # Register services
        await _async_register_services(mock_hass)
        
        # Get the service handler
        service_handler = mock_hass.services.async_register.call_args[0][2]
        
        # Call service
        await service_handler(mock_service_call)
    
    # Verify line breaks are preserved
    mock_notify.assert_called_once()
    notification_args = mock_notify.call_args[1]
    message = notification_args["message"]
    
    # Extract YAML content from code block
    lines = message.split('\n')
    yaml_lines = []
    in_yaml_block = False
    
    for line in lines:
        if line.strip() == "```yaml":
            in_yaml_block = True
            continue
        elif in_yaml_block and line.strip() == "```":
            break
        elif in_yaml_block:
            yaml_lines.append(line)
    
    yaml_content = '\n'.join(yaml_lines)
    
    # Verify empty lines are preserved
    assert '\n\nviews:' in yaml_content or '\n\n  - title: Overview' in yaml_content
    assert 'path: overview\n    \n    cards:' in yaml_content or 'overview\n    \n    cards:' in yaml_content
    
    # Verify indentation levels are maintained
    assert '  - title: Overview' in yaml_content
    assert '    path: overview' in yaml_content
    assert '      - type: thermostat' in yaml_content
    assert '          - type: gauge' in yaml_content


@pytest.mark.asyncio
async def test_notification_title_includes_entity_name(mock_hass, mock_service_call, standard_entity_setup):
    """Test that notification title includes the entity's friendly name."""
    mock_er, mock_notify, mock_registry, mock_entity, mock_state = standard_entity_setup
    
    # Set specific friendly name
    mock_state.attributes = {"friendly_name": "Living Room AC Unit"}
    
    template_content = "title: Smart Climate - REPLACE_ME_NAME"
    mock_hass.async_add_executor_job.return_value = template_content
    
    with patch("os.path.exists", return_value=True):
        # Register services
        await _async_register_services(mock_hass)
        
        # Get the service handler
        service_handler = mock_hass.services.async_register.call_args[0][2]
        
        # Call service
        await service_handler(mock_service_call)
    
    # Verify notification title includes entity name
    mock_notify.assert_called_once()
    notification_args = mock_notify.call_args[1]
    title = notification_args["title"]
    
    assert "Living Room AC Unit" in title
    assert "Smart Climate Dashboard" in title or "Dashboard" in title


@pytest.mark.asyncio
async def test_large_yaml_content_formatting(mock_hass, mock_service_call, standard_entity_setup):
    """Test formatting of large YAML content in code blocks."""
    mock_er, mock_notify, mock_registry, mock_entity, mock_state = standard_entity_setup
    
    # Create large YAML content
    cards_section = []
    for i in range(20):
        cards_section.extend([
            f"      - type: gauge",
            f"        entity: sensor.test_{i}",
            f"        name: Test Sensor {i}",
            f"        min: 0",
            f"        max: 100",
            ""
        ])
    
    large_template = f"""title: Smart Climate - REPLACE_ME_NAME
views:
  - title: Overview
    path: overview
    cards:
{chr(10).join(cards_section)}
  - title: Details
    path: details
    cards:
      - type: history-graph
        entities:
          - REPLACE_ME_SENSOR_OFFSET
          - REPLACE_ME_SENSOR_PROGRESS"""
    
    mock_hass.async_add_executor_job.return_value = large_template
    
    with patch("os.path.exists", return_value=True):
        # Register services
        await _async_register_services(mock_hass)
        
        # Get the service handler
        service_handler = mock_hass.services.async_register.call_args[0][2]
        
        # Call service
        await service_handler(mock_service_call)
    
    # Verify large content is properly formatted
    mock_notify.assert_called_once()
    notification_args = mock_notify.call_args[1]
    message = notification_args["message"]
    
    # Check code block structure is maintained
    assert "```yaml" in message
    assert message.count("```") == 2  # One start, one end
    
    # Verify content structure is preserved
    assert "Test Sensor 19" in message  # Last sensor should be present
    assert "views:" in message
    assert "- title: Details" in message
    
    # Check that indentation is consistent throughout large content
    lines = message.split('\n')
    yaml_lines = []
    in_yaml_block = False
    
    for line in lines:
        if line.strip() == "```yaml":
            in_yaml_block = True
            continue
        elif in_yaml_block and line.strip() == "```":
            break
        elif in_yaml_block:
            yaml_lines.append(line)
    
    # Verify consistent indentation patterns
    gauge_lines = [line for line in yaml_lines if "- type: gauge" in line]
    entity_lines = [line for line in yaml_lines if "entity: sensor.test_" in line]
    
    assert len(gauge_lines) == 20, "Not all gauge entries found"
    assert len(entity_lines) == 20, "Not all entity entries found"
    
    # All gauge lines should have same indentation
    gauge_indents = [len(line) - len(line.lstrip()) for line in gauge_lines]
    assert all(indent == gauge_indents[0] for indent in gauge_indents), "Inconsistent gauge indentation"