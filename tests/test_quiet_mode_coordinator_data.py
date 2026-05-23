"""Regression tests for quiet-mode data exposed through coordinator data."""

import sys
from pathlib import Path
from types import ModuleType


# Load models without executing the heavy integration package __init__.py.
_previous_smart_climate_package = sys.modules.get("custom_components.smart_climate")
package_module = ModuleType("custom_components.smart_climate")
package_module.__path__ = [str(Path(__file__).parents[1] / "custom_components" / "smart_climate")]
sys.modules["custom_components.smart_climate"] = package_module

from custom_components.smart_climate.models import ModeAdjustments, SmartClimateData

if _previous_smart_climate_package is None:
    sys.modules.pop("custom_components.smart_climate", None)
else:
    sys.modules["custom_components.smart_climate"] = _previous_smart_climate_package
sys.modules.pop("custom_components.smart_climate.models", None)


REPO_ROOT = Path(__file__).parents[1]
COORDINATOR_SOURCE = REPO_ROOT / "custom_components" / "smart_climate" / "coordinator.py"
INIT_SOURCE = REPO_ROOT / "custom_components" / "smart_climate" / "__init__.py"
SENSOR_SOURCE = REPO_ROOT / "custom_components" / "smart_climate" / "sensor.py"


def _mode_adjustments() -> ModeAdjustments:
    return ModeAdjustments(
        temperature_override=None,
        offset_adjustment=0.0,
        update_interval_override=None,
        boost_offset=0.0,
    )


def test_smart_climate_data_carries_quiet_mode_fields():
    """Dashboard sensors need quiet-mode fields from real SmartClimateData."""
    data = SmartClimateData(
        room_temp=23.6,
        outdoor_temp=28.4,
        power=4.0,
        calculated_offset=0.4,
        mode_adjustments=_mode_adjustments(),
        quiet_mode_status="enabled",
        quiet_mode_suppressions=14,
        compressor_state="idle",
    )

    assert data.quiet_mode_status == "enabled"
    assert data.quiet_mode_suppressions == 14
    assert data.compressor_state == "idle"


def test_coordinator_populates_quiet_mode_fields_from_power_and_config():
    """Coordinator return data must populate the fields the sensors read."""
    source = COORDINATOR_SOURCE.read_text()

    assert "quiet_mode_status=quiet_mode_status" in source
    assert "quiet_mode_suppressions=quiet_mode_suppressions" in source
    assert "compressor_state=compressor_state" in source
    assert 'compressor_state = "idle" if power < quiet_mode_power_threshold else "active"' in source


def test_dashboard_sensor_coordinator_augments_quiet_mode_fields():
    """The actual sensor coordinator path must attach quiet-mode display fields."""
    source = INIT_SOURCE.read_text()

    assert "def _augment_quiet_mode_dashboard_data" in source
    assert 'data["quiet_mode_status"] = "enabled" if quiet_mode_enabled else "disabled"' in source
    assert 'data["quiet_mode_suppressions"] = climate_attrs.get("quiet_mode_suppressions", 0)' in source
    assert 'data["compressor_state"] = compressor_state' in source
    assert "_augment_quiet_mode_dashboard_data(hass, config, entity_id, data)" in source


def test_quiet_mode_sensors_read_dict_backed_dashboard_payloads():
    """Dashboard sensors must read the dict payload returned by OffsetEngine."""
    source = SENSOR_SOURCE.read_text()

    assert "def _data_value" in source
    assert "if isinstance(data, dict):" in source
    assert 'return self._data_value("quiet_mode_status")' in source
    assert 'return self._data_value("quiet_mode_suppressions")' in source
    assert 'return self._data_value("compressor_state")' in source
