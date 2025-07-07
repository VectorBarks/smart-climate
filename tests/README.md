# Testing Smart Climate Control

This document provides comprehensive guidance for testing the Smart Climate Control integration.

## Prerequisites

Before running tests, ensure you have the required testing dependencies installed:

```bash
# Install testing dependencies
pip install pytest pytest-homeassistant-custom-component pytest-cov pytest-asyncio

# For development environment
pip install -r requirements_dev.txt
```

### Required Components

- **pytest**: Core testing framework
- **pytest-homeassistant-custom-component**: Home Assistant-specific test utilities
- **pytest-cov**: Coverage reporting
- **pytest-asyncio**: Async test support

## Running Tests

### All Tests

Run the complete test suite:

```bash
# From the repository root
pytest tests/

# With verbose output
pytest -v tests/

# With coverage reporting
pytest --cov=custom_components.smart_climate tests/
```

### Specific Test Categories

#### Unit Tests
Test individual components in isolation:

```bash
# Core components
pytest tests/test_offset_engine.py
pytest tests/test_temperature_control.py
pytest tests/test_modes.py
pytest tests/test_override_manager.py

# Sensor integration
pytest tests/test_sensor_integration.py
```

#### Integration Tests
Test component interactions:

```bash
# Integration suite
pytest tests/test_integration.py
pytest tests/test_climate_entity.py
pytest tests/test_coordinator.py
```

#### Configuration Tests
Test setup and configuration:

```bash
# Configuration flow
pytest tests/test_config_flow.py
pytest tests/test_config_flow_functional.py
pytest tests/test_config_flow_simple.py

# YAML configuration
pytest tests/test_yaml_config.py
pytest tests/test_yaml_integration.py
```

#### Home Assistant Specific Tests
Test HA integration behavior:

```bash
# Entity behavior
pytest tests/test_climate_entity_simple.py
pytest tests/test_climate_structure.py
pytest tests/test_hvac_mode_ui.py
pytest tests/test_target_temperature.py

# Startup and timing
pytest tests/test_startup_timing.py
pytest tests/test_startup_timing_simple.py
```

### Running Individual Tests

Run specific test files or functions:

```bash
# Single test file
pytest tests/test_climate_entity.py

# Specific test class
pytest tests/test_climate_entity.py::TestSmartClimateEntity

# Specific test method
pytest tests/test_climate_entity.py::TestSmartClimateEntity::test_current_temperature
```

## Test Coverage

### Generate Coverage Report

```bash
# Basic coverage
pytest --cov=custom_components.smart_climate tests/

# HTML coverage report
pytest --cov=custom_components.smart_climate --cov-report=html tests/

# Coverage with missing lines
pytest --cov=custom_components.smart_climate --cov-report=term-missing tests/
```

### Coverage Targets

- **Overall Coverage**: Aim for >90% code coverage
- **Critical Components**: 95%+ coverage for core logic
- **Edge Cases**: Comprehensive error handling coverage

## Test Structure

### Test Organization

```
tests/
├── conftest.py                    # Test configuration and fixtures
├── fixtures/                     # Shared test fixtures
│   ├── __init__.py
│   └── mock_entities.py          # Mock Home Assistant entities
├── test_*.py                     # Individual test files
└── README.md                     # This file
```

### Test Categories

1. **Unit Tests** (`test_*_unit.py`)
   - Test individual classes and methods
   - Mock external dependencies
   - Focus on business logic

2. **Integration Tests** (`test_*_integration.py`)
   - Test component interactions
   - Use real Home Assistant test framework
   - End-to-end workflows

3. **Configuration Tests** (`test_config_*.py`)
   - Test setup and configuration flows
   - UI configuration wizard
   - YAML configuration parsing

4. **Functional Tests** (`test_*_functional.py`)
   - Test complete user scenarios
   - Real-world usage patterns
   - Performance characteristics

## Common Testing Issues and Solutions

### Issue: "ModuleNotFoundError: No module named 'custom_components'"

**Solution**: Ensure you're running tests from the repository root:
```bash
cd /path/to/smart-climate
pytest tests/
```

### Issue: "RuntimeError: There is no current event loop in thread"

**Solution**: Use pytest-asyncio markers:
```python
@pytest.mark.asyncio
async def test_async_function():
    # Your async test code
```

### Issue: "AttributeError: 'MockEntity' object has no attribute..."

**Solution**: Update mock entities in `tests/fixtures/mock_entities.py` to include required attributes.

### Issue: Tests failing due to Home Assistant version differences

**Solution**: Check Home Assistant version compatibility:
```bash
# Check HA version in test environment
python -c "import homeassistant; print(homeassistant.__version__)"
```

### Issue: Sensor state not updating in tests

**Solution**: Use the proper async state change simulation:
```python
# In tests
hass.states.async_set("sensor.room_temp", "22.5")
await hass.async_block_till_done()
```

## Adding New Tests

### Test File Template

```python
"""Test module for [component_name]."""

import pytest
from homeassistant.core import HomeAssistant
from unittest.mock import Mock, patch

from custom_components.smart_climate.[module] import [Class]


class Test[ComponentName]:
    """Test [ComponentName] functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Initialize test objects
        pass
    
    @pytest.mark.asyncio
    async def test_[functionality](self, hass: HomeAssistant):
        """Test [specific functionality]."""
        # Arrange
        # Act
        # Assert
        pass
    
    def test_[edge_case](self):
        """Test [edge case or error condition]."""
        # Test implementation
        pass
```

### Test Guidelines

1. **Naming**: Use descriptive test names that explain what is being tested
2. **Structure**: Follow Arrange-Act-Assert pattern
3. **Isolation**: Each test should be independent
4. **Mocking**: Mock external dependencies (Home Assistant, sensors, etc.)
5. **Edge Cases**: Test error conditions and boundary cases
6. **Documentation**: Include docstrings explaining test purpose

### Mock Usage

```python
# Mock Home Assistant entities
with patch('custom_components.smart_climate.climate.hass') as mock_hass:
    mock_hass.states.get.return_value = Mock(
        state="22.5",
        attributes={"unit_of_measurement": "°C"}
    )
    
    # Test code using mocked entity
```

## Troubleshooting

### Debug Test Failures

```bash
# Run with maximum verbosity
pytest -vvv tests/test_failing_test.py

# Show local variables on failure
pytest -l tests/test_failing_test.py

# Start pdb on failure
pytest --pdb tests/test_failing_test.py

# Show print statements
pytest -s tests/test_failing_test.py
```

### Test Environment Issues

```bash
# Clear pytest cache
pytest --cache-clear tests/

# Run without coverage (faster)
pytest --no-cov tests/

# Run only failed tests from last run
pytest --lf tests/
```

### Home Assistant Test Framework

The integration uses the official Home Assistant test framework. Key considerations:

- Tests run in an isolated HA environment
- Use `async_setup_component` for component setup
- Use `async_fire_time_changed` for time-based tests
- Use `async_block_till_done` to wait for async operations

## Performance Testing

### Timing Tests

```bash
# Run with timing information
pytest --durations=10 tests/

# Profile slow tests
pytest --durations=0 tests/
```

### Load Testing

For testing with multiple entities or high-frequency updates:

```python
@pytest.mark.asyncio
async def test_high_frequency_updates(hass: HomeAssistant):
    """Test system behavior with frequent sensor updates."""
    # Simulate rapid sensor updates
    for i in range(100):
        hass.states.async_set("sensor.room_temp", f"{20 + i * 0.1}")
        await hass.async_block_till_done()
```

## Contributing Tests

When contributing new features:

1. **Write tests first** (Test-Driven Development)
2. **Ensure all tests pass** before submitting
3. **Maintain high coverage** (>90% for new code)
4. **Test edge cases** and error conditions
5. **Update this documentation** if adding new test categories

### Pre-commit Hooks

The repository uses pre-commit hooks to ensure code quality:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

## Continuous Integration

Tests are automatically run on:
- Pull requests
- Pushes to main branch
- Release tags

CI configuration includes:
- Multiple Python versions
- Multiple Home Assistant versions
- Code coverage reporting
- Linting and formatting checks

Check the `.github/workflows/` directory for CI configuration details.