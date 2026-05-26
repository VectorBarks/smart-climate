"""Regression tests for changing the wrapped climate entity in options flow."""

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
core_module.ServiceCall = object
core_module.State = object
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
flow_module.FlowResultType = SimpleNamespace(FORM="form", CREATE_ENTRY="create_entry", ABORT="abort")
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

from custom_components.smart_climate.config_flow import (  # noqa: E402
    SmartClimateConfigFlow,
    SmartClimateOptionsFlow,
)
from custom_components.smart_climate.const import CONF_CLIMATE_ENTITY, CONF_LEARNING_PROFILE  # noqa: E402

if _previous_smart_climate_package is None:
    sys.modules.pop("custom_components.smart_climate", None)
else:
    sys.modules["custom_components.smart_climate"] = _previous_smart_climate_package
sys.modules.pop("custom_components.smart_climate.config_flow", None)
sys.modules.pop("custom_components.smart_climate.const", None)


class FakeStates:
    """Minimal Home Assistant states helper for climate selector tests."""

    def async_all(self):
        return [
            SimpleNamespace(
                entity_id="climate.tu_klima_anlage",
                attributes={"friendly_name": "TU Klima Anlage"},
            ),
            SimpleNamespace(
                entity_id="climate.tu_klima",
                attributes={"friendly_name": "TU Klima"},
            ),
        ]

    def async_entity_ids(self, domain):
        return []


def _schema_key(schema_key):
    return getattr(schema_key, "key", schema_key)


def _schema_item(schema, key_name):
    for schema_key, validator in schema.schema.items():
        if _schema_key(schema_key) == key_name:
            return schema_key, validator
    raise AssertionError(f"{key_name} not found in schema")


@pytest.mark.asyncio
async def test_options_flow_exposes_wrapped_climate_entity_selector():
    """Existing entries can switch the wrapped climate entity without deleting the entry."""
    flow = SmartClimateOptionsFlow()
    flow.hass = SimpleNamespace(states=FakeStates())
    flow.config_entry = SimpleNamespace(
        data={CONF_CLIMATE_ENTITY: "climate.tu_klima_anlage"},
        options={},
    )
    flow.async_show_form = Mock(side_effect=lambda **kwargs: kwargs)

    result = await flow.async_step_init()

    schema_key, selector_obj = _schema_item(result["data_schema"], CONF_CLIMATE_ENTITY)
    assert getattr(schema_key, "default", None) == "climate.tu_klima_anlage"
    assert {option["value"] for option in selector_obj.config.kwargs["options"]} == {
        "climate.tu_klima_anlage",
        "climate.tu_klima",
    }


def test_config_flow_passes_config_entry_to_options_flow():
    """The options flow receives the existing entry so it can use current data as defaults."""
    config_entry = SimpleNamespace(data={CONF_CLIMATE_ENTITY: "climate.tu_klima_anlage"}, options={})

    options_flow = SmartClimateConfigFlow.async_get_options_flow(config_entry)

    assert isinstance(options_flow, SmartClimateOptionsFlow)
    assert options_flow.config_entry is config_entry


def test_options_flow_can_store_selected_climate_entity_override():
    """Selected climate entity is stored in options and overrides entry data at setup."""
    flow = SmartClimateOptionsFlow()
    flow.async_create_entry = Mock(side_effect=lambda **kwargs: kwargs)

    import asyncio

    result = asyncio.run(
        flow.async_step_init(
            {
                CONF_CLIMATE_ENTITY: "climate.tu_klima",
                CONF_LEARNING_PROFILE: "balanced",
            }
        )
    )

    assert result["data"][CONF_CLIMATE_ENTITY] == "climate.tu_klima"
