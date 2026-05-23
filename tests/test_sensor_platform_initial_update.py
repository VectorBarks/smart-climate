"""Regression tests for initial Smart Climate sensor state updates."""

from __future__ import annotations

import ast
from pathlib import Path


SENSOR_PLATFORM = Path(__file__).parents[1] / "custom_components" / "smart_climate" / "sensor.py"


def test_sensor_platform_requests_update_before_add() -> None:
    """Sensor entities should get their first value before HA publishes them.

    Without update_before_add=True, polling sensors such as Smart Climate humidity
    entities can appear as unknown until the first scheduler poll or a manual
    homeassistant.update_entity call.
    """
    tree = ast.parse(SENSOR_PLATFORM.read_text())

    add_entity_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "async_add_entities"
    ]

    assert add_entity_calls, "sensor platform must call async_add_entities"
    assert any(
        len(call.args) >= 2 and isinstance(call.args[1], ast.Constant) and call.args[1].value is True
        for call in add_entity_calls
    ), "sensor platform must call async_add_entities(sensors, True) for initial state hydration"
