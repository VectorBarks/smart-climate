"""Regression tests for runtime use of options-flow overrides."""

from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "custom_components" / "smart_climate" / "__init__.py"


def _async_setup_entry_source() -> str:
    text = SOURCE.read_text(encoding="utf-8")
    start = text.index("async def async_setup_entry")
    end = text.index("async def _async_setup_entity_persistence", start)
    return text[start:end]


def test_required_entity_wait_uses_options_merged_config() -> None:
    """Options-flow climate/room sensor overrides must drive startup waiting."""
    source = _async_setup_entry_source()

    required_start = source.index("required_entities = [")
    required_end = source.index("# Optional entities", required_start)
    required_block = source[required_start:required_end]

    assert "config[CONF_CLIMATE_ENTITY]" in required_block
    assert "config[CONF_ROOM_SENSOR]" in required_block
    assert "entry.data[CONF_CLIMATE_ENTITY]" not in required_block
    assert "entry.data[CONF_ROOM_SENSOR]" not in required_block


def test_integration_exposes_safe_device_removal_hook() -> None:
    """HA can remove orphaned old Smart Climate devices after entity churn."""
    text = SOURCE.read_text(encoding="utf-8")

    assert "async def async_remove_config_entry_device" in text
    assert "getattr(entity_entry, \"disabled_by\", None) is None" in text
    assert "return False" in text
    assert "return True" in text
