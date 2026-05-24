"""Regression guard against runtime magic defaults in Smart Climate."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "smart_climate"

ALLOWED_FILES = {
    "const.py",
}

FORBIDDEN_PATTERNS = [
    (
        re.compile(r"get\([^\n]*default_target_temperature[^\n]*,\s*24\.0\)"),
        "default_target_temperature fallback must use DEFAULT_TARGET_TEMPERATURE",
    ),
    (
        re.compile(r"getattr\([^\n]*_setpoint[^\n]*,\s*24\.0\)"),
        "thermal setpoint fallback must not hardcode 24.0",
    ),
    (
        re.compile(r"return\s+24\.0\b"),
        "runtime must not return hardcoded target 24.0",
    ),
    (
        re.compile(r"\[20\.0,\s*26\.0\]"),
        "runtime must not hardcode fallback comfort window",
    ),
    (
        re.compile(r"\b22\.0\b"),
        "runtime must not hardcode outdoor/current temp fallback 22.0",
    ),
    (
        re.compile(r"weather\.home"),
        "weather.home must be centralized or optional",
    ),
    (
        re.compile(r"quiet_mode_enabled:\s*bool\s*=\s*False"),
        "quiet mode default must not contradict DEFAULT_QUIET_MODE_ENABLED",
    ),
]


def test_no_known_runtime_magic_defaults():
    violations = []
    for path in COMPONENT.rglob("*.py"):
        rel = path.relative_to(COMPONENT)
        if rel.name in ALLOWED_FILES:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern, message in FORBIDDEN_PATTERNS:
            for match in pattern.finditer(text):
                line_no = text[: match.start()].count("\n") + 1
                violations.append(f"{rel}:{line_no}: {message}: {match.group(0)}")

    assert not violations, "\n" + "\n".join(violations)
