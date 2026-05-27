"""Test configuration for Smart Climate Control."""

import sys
import os
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Mock homeassistant modules before any imports
homeassistant_module = ModuleType('homeassistant')
homeassistant_module.__path__ = []
sys.modules['homeassistant'] = homeassistant_module
core_module = ModuleType('homeassistant.core')

class MockHomeAssistant:
    pass

class MockServiceCall:
    pass

class MockState:
    pass

setattr(core_module, 'HomeAssistant', MockHomeAssistant)
setattr(core_module, 'ServiceCall', MockServiceCall)
setattr(core_module, 'State', MockState)
setattr(core_module, 'callback', lambda func: func)
sys.modules['homeassistant.core'] = core_module

# Create a proper mock for exceptions that preserves actual exception classes
class MockExceptions:
    # Import actual exception classes so they work properly with pytest.raises
    try:
        from homeassistant.exceptions import (
            HomeAssistantError, 
            ConfigEntryNotReady, 
            IntegrationError,
            ServiceValidationError
        )
    except ImportError:
        # Fallback - create our own exception classes that behave correctly
        class HomeAssistantError(Exception):
            """Base exception for Home Assistant."""
            pass
        
        class IntegrationError(HomeAssistantError):
            """Error with integration."""
            pass
            
        class ConfigEntryNotReady(IntegrationError):
            """Config entry is not ready for setup."""
            pass
            
        class ServiceValidationError(HomeAssistantError):
            """Service validation error."""
            pass

sys.modules['homeassistant.exceptions'] = MockExceptions()
helpers_module = ModuleType('homeassistant.helpers')
helpers_module.__path__ = []
sys.modules['homeassistant.helpers'] = helpers_module
setattr(sys.modules['homeassistant'], 'helpers', helpers_module)
sys.modules['homeassistant.helpers.typing'] = MagicMock()
sys.modules['homeassistant.helpers.config_validation'] = MagicMock()
sys.modules['homeassistant.helpers.event'] = MagicMock()
sys.modules['homeassistant.helpers.update_coordinator'] = MagicMock()
sys.modules['homeassistant.helpers.entity'] = MagicMock()

entity_registry_module = ModuleType('homeassistant.helpers.entity_registry')
setattr(entity_registry_module, 'async_get', MagicMock())
sys.modules['homeassistant.helpers.entity_registry'] = entity_registry_module
setattr(helpers_module, 'entity_registry', entity_registry_module)

device_registry_import_module = ModuleType('homeassistant.helpers.device_registry')
setattr(device_registry_import_module, 'async_get', MagicMock())
sys.modules['homeassistant.helpers.device_registry'] = device_registry_import_module
setattr(helpers_module, 'device_registry', device_registry_import_module)

selector_module = ModuleType('homeassistant.helpers.selector')

class _SelectorConfig:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

class _Selector:
    def __init__(self, config=None):
        self.config = config

class _SelectOptionDict(dict):
    def __init__(self, *, value, label):
        super().__init__(value=value, label=label)

setattr(selector_module, 'SelectSelectorConfig', _SelectorConfig)
setattr(selector_module, 'NumberSelectorConfig', _SelectorConfig)
setattr(selector_module, 'SelectSelector', _Selector)
setattr(selector_module, 'NumberSelector', _Selector)
setattr(selector_module, 'BooleanSelector', _Selector)
setattr(selector_module, 'TextSelector', _Selector)
setattr(selector_module, 'SelectOptionDict', _SelectOptionDict)
setattr(selector_module, 'SelectSelectorMode', SimpleNamespace(DROPDOWN="dropdown"))
setattr(selector_module, 'NumberSelectorMode', SimpleNamespace(BOX="box"))
sys.modules['homeassistant.helpers.selector'] = selector_module
setattr(helpers_module, 'selector', selector_module)
sys.modules['homeassistant.const'] = MagicMock()
sys.modules['homeassistant.components'] = MagicMock()
sys.modules['homeassistant.components.climate'] = MagicMock()
sys.modules['homeassistant.components.climate.const'] = MagicMock()

persistent_notification_module = MagicMock()
persistent_notification_module.async_create = MagicMock()
sys.modules['homeassistant.components.persistent_notification'] = persistent_notification_module

# Minimal HA entity/platform stubs used by sensor unit tests.
class MockCoordinatorEntity:
    def __init__(self, coordinator=None):
        self.coordinator = coordinator

class MockSensorEntity:
    def __init__(self):
        pass
    @property
    def name(self):
        return getattr(self, "_attr_name", None)
    @property
    def icon(self):
        return getattr(self, "_attr_icon", None)
    @property
    def native_unit_of_measurement(self):
        return getattr(self, "_attr_native_unit_of_measurement", None)
    @property
    def state_class(self):
        return getattr(self, "_attr_state_class", None)

class MockBinarySensorEntity:
    def __init__(self):
        pass
    @property
    def name(self):
        return getattr(self, "_attr_name", None)
    @property
    def icon(self):
        return getattr(self, "_attr_icon", None)

class MockDeviceInfo(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class MockDataUpdateCoordinator:
    def __init__(self, *args, **kwargs):
        self.hass = args[0] if args else kwargs.get("hass")
        self.logger = args[1] if len(args) > 1 else kwargs.get("logger")
        self.name = kwargs.get("name")
        self.update_interval = kwargs.get("update_interval")
        self.data = None
        self.last_update_success = True

    @classmethod
    def __class_getitem__(cls, item):
        return cls

class MockUpdateFailed(Exception):
    pass

class _Const:
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return self.value

class MockSensorStateClass:
    MEASUREMENT = "measurement"
    TOTAL_INCREASING = "total_increasing"

class MockSensorDeviceClass:
    TEMPERATURE = "temperature"
    DURATION = "duration"
    DATA_SIZE = "data_size"
    HUMIDITY = "humidity"
    POWER = "power"

class MockBinarySensorDeviceClass:
    PROBLEM = "problem"
    SAFETY = "safety"
    RUNNING = "running"

class MockEntityCategory:
    DIAGNOSTIC = "diagnostic"

sensor_module = MagicMock()
sensor_module.SensorEntity = MockSensorEntity
sensor_module.SensorStateClass = MockSensorStateClass
sensor_module.SensorDeviceClass = MockSensorDeviceClass
sys.modules['homeassistant.components.sensor'] = sensor_module

binary_sensor_module = MagicMock()
binary_sensor_module.BinarySensorEntity = MockBinarySensorEntity
binary_sensor_module.BinarySensorDeviceClass = MockBinarySensorDeviceClass
sys.modules['homeassistant.components.binary_sensor'] = binary_sensor_module

config_entries_module = MagicMock()
config_entries_module.ConfigEntry = MagicMock

class MockConfigEntries:
    def async_entries(self, *args, **kwargs):
        return []

class MockConfigFlowBase:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()

    def async_show_form(self, *, step_id, data_schema=None, errors=None, description_placeholders=None):
        return {
            "type": "form",
            "step_id": step_id,
            "data_schema": data_schema,
            "errors": errors or {},
            "description_placeholders": description_placeholders or {},
        }

    def async_create_entry(self, *, title, data=None, options=None):
        return {
            "type": "create_entry",
            "title": title,
            "data": data or {},
            "options": options or {},
        }

    def async_abort(self, *, reason):
        return {"type": "abort", "reason": reason}

class MockOptionsFlowBase(MockConfigFlowBase):
    pass

config_entries_module.ConfigEntries = MockConfigEntries
config_entries_module.ConfigFlow = MockConfigFlowBase
config_entries_module.OptionsFlow = MockOptionsFlowBase
sys.modules['homeassistant.config_entries'] = config_entries_module
setattr(sys.modules['homeassistant'], 'config_entries', config_entries_module)

data_entry_flow_module = MagicMock()
data_entry_flow_module.FlowResult = dict
data_entry_flow_module.FlowResultType = SimpleNamespace(
    FORM="form",
    CREATE_ENTRY="create_entry",
    ABORT="abort",
)
data_entry_flow_module.RESULT_TYPE_FORM = "form"
data_entry_flow_module.RESULT_TYPE_CREATE_ENTRY = "create_entry"
data_entry_flow_module.RESULT_TYPE_ABORT = "abort"
sys.modules['homeassistant.data_entry_flow'] = data_entry_flow_module
setattr(sys.modules['homeassistant'], 'data_entry_flow', data_entry_flow_module)

update_coordinator_module = MagicMock()
update_coordinator_module.CoordinatorEntity = MockCoordinatorEntity
update_coordinator_module.DataUpdateCoordinator = MockDataUpdateCoordinator
update_coordinator_module.UpdateFailed = MockUpdateFailed
sys.modules['homeassistant.helpers.update_coordinator'] = update_coordinator_module

device_registry_module = MagicMock()
device_registry_module.DeviceInfo = MockDeviceInfo
sys.modules['homeassistant.helpers.device_registry'] = device_registry_module

entity_platform_module = MagicMock()
entity_platform_module.AddEntitiesCallback = MagicMock
sys.modules['homeassistant.helpers.entity_platform'] = entity_platform_module

storage_module = MagicMock()
storage_module.Store = MagicMock
sys.modules['homeassistant.helpers.storage'] = storage_module

util_module = MagicMock()
dt_module = MagicMock()
sys.modules['homeassistant.util'] = util_module
sys.modules['homeassistant.util.dt'] = dt_module

# Mock Platform
sys.modules['homeassistant.const'].Platform = MagicMock()
sys.modules['homeassistant.const'].Platform.CLIMATE = "climate"

# Mock constants
sys.modules['homeassistant.const'].STATE_UNAVAILABLE = "unavailable"
sys.modules['homeassistant.const'].STATE_UNKNOWN = "unknown"
sys.modules['homeassistant.const'].STATE_ON = "on"
sys.modules['homeassistant.const'].STATE_OFF = "off"
sys.modules['homeassistant.const'].PERCENTAGE = "%"
sys.modules['homeassistant.const'].UnitOfTemperature = type("UnitOfTemperature", (), {"CELSIUS": "°C"})
sys.modules['homeassistant.const'].UnitOfTime = type("UnitOfTime", (), {"SECONDS": "s", "MINUTES": "min"})
sys.modules['homeassistant.const'].UnitOfInformation = type("UnitOfInformation", (), {"KIBIBYTES": "KiB"})
sys.modules['homeassistant.const'].EntityCategory = MockEntityCategory

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
    FAN_ONLY = "fan_only"
    DRY = "dry"
    HEAT_COOL = "heat_cool"

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


# Import pytest for fixtures (used below)
import pytest

# Thermal persistence test fixtures
@pytest.fixture
def mock_thermal_callbacks():
    """Mock thermal persistence callbacks using unittest.mock.MagicMock."""
    get_thermal_data_cb = MagicMock()
    restore_thermal_data_cb = MagicMock()
    
    # Default return value for get callback
    get_thermal_data_cb.return_value = {
        "version": "1.0",
        "state": {
            "current_state": "DRIFTING",
            "last_transition": "2025-08-08T15:45:00Z"
        },
        "model": {
            "tau_cooling": 95.5,
            "tau_warming": 148.2,
            "last_modified": "2025-08-08T15:30:00Z"
        },
        "probe_history": [],
        "confidence": 0.75
    }
    
    return get_thermal_data_cb, restore_thermal_data_cb


@pytest.fixture  
def mock_failing_thermal_callbacks():
    """Mock thermal callbacks that simulate failures for testing."""
    get_thermal_data_cb = MagicMock()
    restore_thermal_data_cb = MagicMock()
    
    # Simulate callback failures
    get_thermal_data_cb.side_effect = Exception("Get callback failed")
    restore_thermal_data_cb.side_effect = Exception("Restore callback failed")
    
    return get_thermal_data_cb, restore_thermal_data_cb


@pytest.fixture
def mock_thermal_manager():
    """Mock ThermalManager for testing thermal persistence."""
    manager = MagicMock()
    manager.serialize.return_value = {
        "version": "1.0", 
        "state": {
            "current_state": "PRIMING",
            "last_transition": "2025-08-08T16:00:00Z"
        },
        "model": {
            "tau_cooling": 90.0,
            "tau_warming": 150.0,
            "last_modified": "2025-08-08T16:00:00Z"
        },
        "probe_history": [],
        "confidence": 0.0,
        "metadata": {
            "saves_count": 0,
            "corruption_recoveries": 0,
            "schema_version": "1.0"
        }
    }
    manager.reset = MagicMock()
    manager.restore = MagicMock()
    return manager


@pytest.fixture
def thermal_data_structure_helper():
    """Helper to create valid thermal_data structures for testing."""
    def create_thermal_data_dict(
        current_state: str = "PRIMING",
        tau_cooling: float = 90.0,
        tau_warming: float = 150.0,
        confidence: float = 0.0
    ):
        return {
            "version": "1.0",
            "state": {
                "current_state": current_state,
                "last_transition": "2025-08-08T16:00:00Z"
            },
            "model": {
                "tau_cooling": tau_cooling,
                "tau_warming": tau_warming,
                "last_modified": "2025-08-08T16:00:00Z"
            },
            "probe_history": [],
            "confidence": confidence,
            "metadata": {
                "saves_count": 0,
                "corruption_recoveries": 0,
                "schema_version": "1.0"
            }
        }
    return create_thermal_data_dict


@pytest.fixture
def mock_callback_failure_simulation():
    """Helper to simulate various callback failure modes."""
    def create_failing_get_callback():
        cb = MagicMock()
        cb.side_effect = Exception("Simulated get failure")
        return cb
    
    def create_failing_restore_callback():
        cb = MagicMock()
        cb.side_effect = Exception("Simulated restore failure") 
        return cb
        
    def create_timeout_callback():
        cb = MagicMock()
        cb.side_effect = TimeoutError("Callback timed out")
        return cb
        
    return {
        "failing_get": create_failing_get_callback,
        "failing_restore": create_failing_restore_callback,
        "timeout": create_timeout_callback
    }