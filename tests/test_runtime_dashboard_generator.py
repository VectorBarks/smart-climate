"""Regression tests for the runtime dashboard generator."""

import re

import yaml

from custom_components.smart_climate.dashboard.generator import DashboardGenerator


RELATED_ENTITIES = [
    {
        "entity_id": "sensor.smart_climate_control_climate_klimaanlage_tu_climate_current_offset",
        "domain": "sensor",
        "friendly_name": "SCC Torsten Current Offset",
        "state": "0.125",
    },
    {
        "entity_id": "sensor.smart_climate_control_climate_klimaanlage_tu_climate_learning_progress",
        "domain": "sensor",
        "friendly_name": "SCC Torsten Learning Progress",
        "state": "0",
    },
    {
        "entity_id": "sensor.scc_torsten_model_confidence",
        "domain": "sensor",
        "friendly_name": "SCC Torsten Model Confidence",
        "state": "56.7",
    },
    {
        "entity_id": "sensor.scc_torsten_thermal_probe_confidence",
        "domain": "sensor",
        "friendly_name": "SCC Torsten Thermal Probe Confidence",
        "state": "0.0",
    },
    {
        "entity_id": "sensor.scc_torsten_passive_drift_confidence",
        "domain": "sensor",
        "friendly_name": "SCC Torsten Passive Drift Confidence",
        "state": "56.7",
    },
    {
        "entity_id": "sensor.scc_torsten_overall_control_confidence",
        "domain": "sensor",
        "friendly_name": "SCC Torsten Overall Control Confidence",
        "state": "56.7",
    },
    {
        "entity_id": "sensor.scc_torsten_probe_diagnostics",
        "domain": "sensor",
        "friendly_name": "SCC Torsten Probe Diagnostics",
        "state": "blocked_min_interval",
    },
    {
        "entity_id": "sensor.scc_torsten_compressor_state",
        "domain": "sensor",
        "friendly_name": "SCC Torsten Compressor State",
        "state": "idle",
    },
    {
        "entity_id": "sensor.scc_torsten_temperature_window",
        "domain": "sensor",
        "friendly_name": "SCC Torsten Temperature Window",
        "state": "learning",
    },
    {
        "entity_id": "sensor.scc_torsten_thermal_state",
        "domain": "sensor",
        "friendly_name": "SCC Torsten Thermal State",
        "state": "drifting",
    },
    {
        "entity_id": "switch.smart_climate_control_climate_klimaanlage_tu_climate_learning",
        "domain": "switch",
        "friendly_name": "SCC Torsten Learning",
        "state": "on",
    },
    {
        "entity_id": "button.smart_climate_control_climate_klimaanlage_tu_climate_reset_training_data",
        "domain": "button",
        "friendly_name": "SCC Torsten Reset Training Data",
        "state": "2026-05-23T13:09:45+00:00",
    },
]


def _referenced_entities(yaml_content: str) -> set[str]:
    return {
        match
        for match in re.findall(r"(?<![A-Za-z0-9_])(?:[a-z_]+\.[a-z0-9_]+)", yaml_content)
        if match.split(".", 1)[0] in {"climate", "sensor", "switch", "button", "binary_sensor"}
    }


def _card_types(node) -> set[str]:
    found = set()
    if isinstance(node, dict):
        if "type" in node:
            found.add(str(node["type"]))
        for value in node.values():
            found.update(_card_types(value))
    elif isinstance(node, list):
        for value in node:
            found.update(_card_types(value))
    return found


def test_runtime_dashboard_references_only_existing_entities():
    """Runtime dashboard must not guess missing helper entity IDs."""
    climate_entity = "climate.smart_klimaanlage_tu_climate"
    yaml_content = DashboardGenerator().generate_runtime_dashboard(
        climate_entity,
        "Smart Klimaanlage TU Climate",
        RELATED_ENTITIES,
    )

    allowed_entities = {climate_entity, *(entity["entity_id"] for entity in RELATED_ENTITIES)}

    assert _referenced_entities(yaml_content) <= allowed_entities
    assert "sensor.smart_klimaanlage_tu_climate_offset_current" not in yaml_content
    assert "custom:apexcharts-card" not in yaml_content
    assert "custom:plotly-graph-card" not in yaml_content
    assert "&id" not in yaml_content
    assert "*id" not in yaml_content


def test_runtime_dashboard_uses_core_cards_and_keeps_five_views():
    """Generated dashboard should be pasteable without HACS-only Lovelace cards."""
    yaml_content = DashboardGenerator().generate_runtime_dashboard(
        "climate.smart_klimaanlage_tu_climate",
        "Smart Klimaanlage TU Climate",
        RELATED_ENTITIES,
    )
    dashboard = yaml.safe_load(yaml_content)

    assert dashboard["title"] == "Smart Climate - Smart Klimaanlage TU Climate"
    assert [view["path"] for view in dashboard["views"]] == [
        "overview",
        "learning",
        "thermal",
        "performance",
        "diagnostics",
    ]
    assert _card_types(dashboard) <= {"thermostat", "markdown", "gauge", "entities", "history-graph"}


def test_runtime_dashboard_explains_hysteresis_learning_metrics():
    """Status card should distinguish exact offsets, probe constraints, and correlation readiness."""
    yaml_content = DashboardGenerator().generate_runtime_dashboard(
        "climate.smart_klimaanlage_tu_climate",
        "Smart Klimaanlage TU Climate",
        RELATED_ENTITIES,
    )

    assert "Exact compressor offsets" in yaml_content
    assert "Probe-derived bounds" in yaml_content
    assert "Sample progress" in yaml_content
    assert "Power correlation" in yaml_content
    assert "power_correlation_status_detail" in yaml_content
    assert "power_correlation_sample_count" in yaml_content


def test_runtime_dashboard_shows_thermal_relearn_confidence_and_probe_blockers():
    """Cold-start recovery telemetry must be visible and explained in the generated dashboard."""
    yaml_content = DashboardGenerator().generate_runtime_dashboard(
        "climate.smart_klimaanlage_tu_climate",
        "Smart Klimaanlage TU Climate",
        RELATED_ENTITIES,
    )
    dashboard = yaml.safe_load(yaml_content)

    assert "sensor.scc_torsten_thermal_probe_confidence" in yaml_content
    assert "sensor.scc_torsten_passive_drift_confidence" in yaml_content
    assert "sensor.scc_torsten_overall_control_confidence" in yaml_content
    assert "sensor.scc_torsten_probe_diagnostics" in yaml_content
    assert "Thermal relearn confidence" in yaml_content
    assert "Active thermal probes" in yaml_content
    assert "Passive drift / recorder backfill" in yaml_content
    assert "Overall control confidence" in yaml_content
    assert "Probe diagnostics" in yaml_content
    assert "fast_relearn" in yaml_content
    assert "blocked_min_interval" in yaml_content
    assert any(
        card.get("type") == "gauge"
        and card.get("entity") == "sensor.scc_torsten_thermal_probe_confidence"
        for view in dashboard["views"]
        for card in view["cards"]
    )
