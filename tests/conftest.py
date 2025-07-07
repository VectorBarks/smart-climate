"""Test configuration for Smart Climate Control."""

import sys
import os
from unittest.mock import MagicMock

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Mock homeassistant modules before any imports
sys.modules['homeassistant'] = MagicMock()
sys.modules['homeassistant.core'] = MagicMock()
sys.modules['homeassistant.exceptions'] = MagicMock()
sys.modules['homeassistant.helpers'] = MagicMock()
sys.modules['homeassistant.helpers.typing'] = MagicMock()
sys.modules['homeassistant.helpers.config_validation'] = MagicMock()
sys.modules['homeassistant.helpers.event'] = MagicMock()
sys.modules['homeassistant.helpers.update_coordinator'] = MagicMock()
sys.modules['homeassistant.helpers.entity'] = MagicMock()
sys.modules['homeassistant.const'] = MagicMock()
sys.modules['homeassistant.components'] = MagicMock()
sys.modules['homeassistant.components.climate'] = MagicMock()
sys.modules['homeassistant.components.climate.const'] = MagicMock()

# Mock Platform
sys.modules['homeassistant.const'].Platform = MagicMock()
sys.modules['homeassistant.const'].Platform.CLIMATE = "climate"

# Mock constants
sys.modules['homeassistant.const'].STATE_UNAVAILABLE = "unavailable"
sys.modules['homeassistant.const'].STATE_UNKNOWN = "unknown"
sys.modules['homeassistant.const'].STATE_ON = "on"
sys.modules['homeassistant.const'].STATE_OFF = "off"

# Mock climate constants
sys.modules['homeassistant.components.climate.const'].HVAC_MODE_OFF = "off"
sys.modules['homeassistant.components.climate.const'].HVAC_MODE_COOL = "cool"
sys.modules['homeassistant.components.climate.const'].HVAC_MODE_HEAT = "heat"
sys.modules['homeassistant.components.climate.const'].HVAC_MODE_AUTO = "auto"
sys.modules['homeassistant.components.climate.const'].SUPPORT_TARGET_TEMPERATURE = 1
sys.modules['homeassistant.components.climate.const'].SUPPORT_PRESET_MODE = 16

# Mock climate enums
class MockHVACMode:
    OFF = "off"
    COOL = "cool"
    HEAT = "heat"
    AUTO = "auto"

class MockHVACAction:
    OFF = "off"
    COOLING = "cooling"
    HEATING = "heating"
    IDLE = "idle"

class MockClimateEntityFeature:
    TARGET_TEMPERATURE = 1
    PRESET_MODE = 16

sys.modules['homeassistant.components.climate.const'].HVACMode = MockHVACMode
sys.modules['homeassistant.components.climate.const'].HVACAction = MockHVACAction
sys.modules['homeassistant.components.climate.const'].ClimateEntityFeature = MockClimateEntityFeature

# Mock ClimateEntity
class MockClimateEntity:
    def __init__(self):
        pass

sys.modules['homeassistant.components.climate'].ClimateEntity = MockClimateEntity

# Mock voluptuous with proper validation
sys.modules['voluptuous'] = MagicMock()

# Set up mock voluptuous functionality
mock_vol = sys.modules['voluptuous']

# Create a mock schema class that behaves like a validation function
class MockSchema:
    def __init__(self, schema_dict, **kwargs):
        self.schema = schema_dict
        self.extra = kwargs.get('extra', None)
        self.validators = []
        
    def __call__(self, config):
        # Start with the config
        result = dict(config)
        
        # Check required fields
        required_fields = []
        optional_fields = []
        
        for key, validator in self.schema.items():
            if hasattr(key, 'key'):
                # This is a MockOptional or MockRequired
                if isinstance(key, MockRequired):
                    required_fields.append(key.key)
                elif isinstance(key, MockOptional):
                    optional_fields.append(key)
                    if key.key not in result and key.default is not None:
                        result[key.key] = key.default
            else:
                # This is a direct key (for MockRequired without wrapper)
                required_fields.append(key)
        
        # Check if required fields are present
        for field in required_fields:
            if field not in result:
                raise MockInvalid(f"required key not provided @ data['{field}']")
        
        # Apply type coercion and validation
        for key, validator in self.schema.items():
            actual_key = key.key if hasattr(key, 'key') else key
            if actual_key in result:
                value = result[actual_key]
                
                # Skip validation for None values from optional fields without defaults
                if value is None and isinstance(key, MockOptional) and key.default is None:
                    continue
                
                # Handle type coercion and validation
                if hasattr(validator, '__name__'):
                    if validator.__name__ == 'mock_coerce_float':
                        try:
                            result[actual_key] = float(value)
                        except (ValueError, TypeError):
                            raise MockInvalid(f"invalid literal for float(): {value}")
                    elif validator.__name__ == 'mock_coerce_int':
                        try:
                            result[actual_key] = int(value)
                        except (ValueError, TypeError):
                            raise MockInvalid(f"invalid literal for int(): {value}")
                    elif validator.__name__ == 'mock_entity_id':
                        if not isinstance(value, str) or '.' not in value:
                            raise MockInvalid(f"entity ID is invalid: {value}")
                    elif validator.__name__ == 'mock_boolean':
                        if isinstance(value, str):
                            if value.lower() in ('true', 'yes', '1'):
                                result[actual_key] = True
                            elif value.lower() in ('false', 'no', '0'):
                                result[actual_key] = False
                            else:
                                raise MockInvalid(f"invalid boolean value: {value}")
                        else:
                            result[actual_key] = bool(value)
                # Apply validator if it's a function (especially for mocked cv functions)
                elif callable(validator):
                    try:
                        # Special handling for mocked cv.boolean and cv.entity_id
                        if str(validator).startswith('<MagicMock') and 'boolean' in str(validator):
                            result[actual_key] = mock_boolean(value)
                        elif str(validator).startswith('<MagicMock') and 'entity_id' in str(validator):
                            result[actual_key] = mock_entity_id(value)
                        else:
                            result[actual_key] = validator(value)
                    except Exception as e:
                        raise MockInvalid(f"invalid value for {actual_key}: {e}")
        
        # Apply any validation functions that were added via vol.All
        for validator_func in self.validators:
            if callable(validator_func):
                result = validator_func(result)
        
        return result

# Custom exception for validation errors
class MockInvalid(Exception):
    """Mock voluptuous.Invalid exception."""
    pass

# Mock classes and functions
mock_vol.Schema = MockSchema
mock_vol.Invalid = MockInvalid
mock_vol.ALLOW_EXTRA = "allow_extra"

class MockRequired:
    def __init__(self, key):
        self.key = key
    
    def __str__(self):
        return str(self.key)

class MockOptional:
    def __init__(self, key, default=None):
        self.key = key
        self.default = default
    
    def __str__(self):
        return str(self.key)

def mock_coerce_float(value):
    """Mock vol.Coerce(float)"""
    return float(value)

def mock_coerce_int(value):
    """Mock vol.Coerce(int)"""
    return int(value)

def mock_entity_id(value):
    """Mock cv.entity_id validation"""
    if not isinstance(value, str) or '.' not in value:
        raise MockInvalid(f"entity ID is invalid: {value}")
    return value

def mock_boolean(value):
    """Mock cv.boolean validation"""
    if isinstance(value, str):
        if value.lower() in ('true', 'yes', '1'):
            return True
        elif value.lower() in ('false', 'no', '0'):
            return False
        else:
            raise MockInvalid(f"invalid boolean value: {value}")
    return bool(value)

# Set up mock functions
mock_vol.Required = MockRequired
mock_vol.Optional = MockOptional

def mock_coerce(type_func):
    """Mock vol.Coerce that returns appropriate validator"""
    if type_func is float:
        return mock_coerce_float
    elif type_func is int:
        return mock_coerce_int
    else:
        return type_func

mock_vol.Coerce = mock_coerce

def mock_all(*args):
    """Mock vol.All that chains validators"""
    class AllValidator:
        def __init__(self, validators):
            self.validators = validators
        
        def __call__(self, config):
            result = config
            for validator in self.validators:
                if callable(validator):
                    result = validator(result)
                elif hasattr(validator, '__call__'):
                    result = validator(result)
            return result
    
    return AllValidator(args)

mock_vol.All = mock_all

# Mock config validation helpers - Replace the entire module
class MockConfigValidation:
    entity_id = staticmethod(mock_entity_id)
    boolean = staticmethod(mock_boolean)

# Replace the module completely
sys.modules['homeassistant.helpers.config_validation'] = MockConfigValidation()
mock_cv = MockConfigValidation()