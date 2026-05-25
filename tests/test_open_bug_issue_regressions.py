"""Regression tests for open GitHub bug issues #57, #58, #59, #69."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "smart_climate"


def _source(relative_path: str) -> str:
    return (COMPONENT / relative_path).read_text(encoding="utf-8")


def test_cycle_monitor_uses_shared_timing_constants():
    """Issue #58: CycleMonitor defaults must track const.py timing constants."""
    text = _source("cycle_monitor.py")

    assert "from .const import MIN_OFF_TIME_SECONDS, MIN_ON_TIME_SECONDS" in text
    assert "min_off_time: int = MIN_OFF_TIME_SECONDS" in text
    assert "min_on_time: int = MIN_ON_TIME_SECONDS" in text
    assert "min_off_time: int = 600" not in text
    assert "min_on_time: int = 300" not in text


def test_thermal_models_uses_shared_thermal_constants():
    """Issue #59: ThermalConstants must derive defaults from const.py."""
    text = _source("thermal_models.py")

    for name in (
        "MIN_OFF_TIME_SECONDS",
        "MIN_ON_TIME_SECONDS",
        "PRIMING_DURATION_HOURS",
        "RECOVERY_DURATION_MINUTES",
    ):
        assert name in text

    assert "min_off_time: int = MIN_OFF_TIME_SECONDS" in text
    assert "min_on_time: int = MIN_ON_TIME_SECONDS" in text
    assert "priming_duration: int = PRIMING_DURATION_HOURS * 3600" in text
    assert "recovery_duration: int = RECOVERY_DURATION_MINUTES * 60" in text

    forbidden_defaults = (
        r"min_off_time:\s*int\s*=\s*600",
        r"min_on_time:\s*int\s*=\s*300",
        r"priming_duration:\s*int\s*=\s*86400",
        r"recovery_duration:\s*int\s*=\s*1800",
    )
    for pattern in forbidden_defaults:
        assert not re.search(pattern, text)


def test_mode_behaviors_uses_shared_mode_defaults():
    """Issue #57: mode_behaviors.py must not duplicate mode defaults."""
    text = _source("mode_behaviors.py")

    assert "from .const import (" in text
    for name in (
        "DEFAULT_AWAY_TEMPERATURE",
        "DEFAULT_SLEEP_OFFSET",
        "DEFAULT_BOOST_OFFSET",
    ):
        assert name in text

    assert '"away_temperature": DEFAULT_AWAY_TEMPERATURE' in text
    assert '"sleep_offset": CONST_DEFAULT_SLEEP_OFFSET' in text
    assert '"boost_offset": CONST_DEFAULT_BOOST_OFFSET' in text
    assert "DEFAULT_AWAY_TEMP = DEFAULT_AWAY_TEMPERATURE" in text
    assert "DEFAULT_SLEEP_OFFSET = CONST_DEFAULT_SLEEP_OFFSET" in text
    assert "DEFAULT_BOOST_OFFSET = CONST_DEFAULT_BOOST_OFFSET" in text

    for literal in ("19.0", "1.0", "-2.0"):
        assert literal not in text


def test_config_flow_validates_weather_strategy_windows():
    """Issue #69: impossible weather strategy windows must be rejected."""
    text = _source("config_flow.py")

    assert "def _validate_forecast_strategy_windows" in text
    assert "CONF_HEAT_WAVE_LOOKAHEAD_HOURS" in text
    assert "CONF_CLEAR_SKY_LOOKAHEAD_HOURS" in text
    assert "heat_wave_lookahead_too_short" in text
    assert "clear_sky_lookahead_too_short" in text
    assert "lookahead < min_duration + pre_action" in text
    assert "self._validate_forecast_strategy_windows(user_input)" in text
