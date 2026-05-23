"""Regression tests for power sensor configuration in the options flow."""

import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest


# Load config_flow without executing the heavy integration package __init__.py.
_previous_smart_climate_package = sys.modules.get("custom_components.smart_climate")
package_module = ModuleType("custom_components.smart_climate")
package_module.__path__ = [str(Path(__file__).parents[1] / "custom_components" / "smart_climate")]
sys.modules["custom_components.smart_climate"] = package_module


class _FakeConfigFlow:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()


class _FakeOptionsFlow:
    pass


core_module = ModuleType("homeassistant.core")
core_module.HomeAssistant = object
core_module.callback = lambda func: func
sys.modules["homeassistant.core"] = core_module

const_module = sys.modules.get("homeassistant.const", ModuleType("homeassistant.const"))
const_module.CONF_NAME = "name"
sys.modules["homeassistant.const"] = const_module

config_entries_module = ModuleType("homeassistant.config_entries")
config_entries_module.ConfigFlow = _FakeConfigFlow
config_entries_module.OptionsFlow = _FakeOptionsFlow
config_entries_module.ConfigEntry = object
sys.modules["homeassistant.config_entries"] = config_entries_module
sys.modules["homeassistant"].config_entries = config_entries_module

flow_module = ModuleType("homeassistant.data_entry_flow")
flow_module.FlowResult = dict
sys.modules["homeassistant.data_entry_flow"] = flow_module

helpers_module = ModuleType("homeassistant.helpers")
helpers_module.__path__ = []
sys.modules["homeassistant.helpers"] = helpers_module

entity_registry_module = ModuleType("homeassistant.helpers.entity_registry")
entity_registry_module.async_get = Mock()
sys.modules["homeassistant.helpers.entity_registry"] = entity_registry_module

device_registry_module = ModuleType("homeassistant.helpers.device_registry")
device_registry_module.async_get = Mock()
sys.modules["homeassistant.helpers.device_registry"] = device_registry_module

selector_module = ModuleType("homeassistant.helpers.selector")


class _SelectorConfig:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _Selector:
    def __init__(self, config=None):
        self.config = config


class _SelectOptionDict(dict):
    def __init__(self, *, value, label):
        super().__init__(value=value, label=label)


selector_module.SelectSelectorConfig = _SelectorConfig
selector_module.NumberSelectorConfig = _SelectorConfig
selector_module.SelectSelector = _Selector
selector_module.NumberSelector = _Selector
selector_module.BooleanSelector = _Selector
selector_module.TextSelector = _Selector
selector_module.SelectOptionDict = _SelectOptionDict
selector_module.SelectSelectorMode = SimpleNamespace(DROPDOWN="dropdown")
selector_module.NumberSelectorMode = SimpleNamespace(BOX="box")
sys.modules["homeassistant.helpers.selector"] = selector_module
helpers_module.selector = selector_module

persistent_notification_module = ModuleType("homeassistant.components.persistent_notification")
persistent_notification_module.async_create = Mock()
sys.modules["homeassistant.components.persistent_notification"] = persistent_notification_module

from custom_components.smart_climate.config_flow import SmartClimateOptionsFlow
from custom_components.smart_climate.const import (
    CONF_POWER_IDLE_THRESHOLD,
    CONF_POWER_MAX_THRESHOLD,
    CONF_POWER_MIN_THRESHOLD,
    CONF_POWER_SENSOR,
)

if _previous_smart_climate_package is None:
    sys.modules.pop("custom_components.smart_climate", None)
else:
    sys.modules["custom_components.smart_climate"] = _previous_smart_climate_package
sys.modules.pop("custom_components.smart_climate.config_flow", None)
sys.modules.pop("custom_components.smart_climate.const", None)


class FakeStates:
    """Minimal Home Assistant states helper for options-flow schema tests."""

    def async_all(self):
        return [
            SimpleNamespace(
                entity_id="sensor.ac_plug_power",
                attributes={
                    "device_class": "power",
                    "friendly_name": "AC plug power",
                },
            ),
            SimpleNamespace(
                entity_id="sensor.room_humidity",
                attributes={
                    "device_class": "humidity",
                    "friendly_name": "Room humidity",
                },
            ),
        ]

    def async_entity_ids(self, domain):
        return []


def _schema_keys(schema):
    return {getattr(key, "key", key) for key in schema.schema}


@pytest.mark.asyncio
async def test_options_flow_exposes_power_sensor_when_not_configured():
    """Existing entries can add the AC power sensor from the options flow."""
    flow = SmartClimateOptionsFlow()
    flow.hass = SimpleNamespace(states=FakeStates())
    flow.config_entry = SimpleNamespace(data={}, options={})
    flow.async_show_form = Mock(side_effect=lambda **kwargs: kwargs)

    result = await flow.async_step_init()

    keys = _schema_keys(result["data_schema"])
    assert CONF_POWER_SENSOR in keys
    assert CONF_POWER_IDLE_THRESHOLD in keys
    assert CONF_POWER_MIN_THRESHOLD in keys
    assert CONF_POWER_MAX_THRESHOLD in keys


def test_empty_power_sensor_is_cleaned_to_none():
    """The optional power sensor can be removed without leaving an empty string config value."""
    flow = SmartClimateOptionsFlow()

    cleaned = flow._clean_entity_ids({CONF_POWER_SENSOR: ""})

    assert cleaned[CONF_POWER_SENSOR] is None
