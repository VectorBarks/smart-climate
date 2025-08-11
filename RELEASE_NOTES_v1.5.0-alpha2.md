# Release Notes - v1.5.0-alpha2

## 🔧 Critical Fix: PrimingState Persistence

This alpha release fixes a critical bug where the PRIMING state would get stuck indefinitely after Home Assistant restarts, preventing the system from transitioning to normal operation.

## 🐛 Bug Fixes

### PrimingState Start Time Persistence
- **Fixed**: PRIMING state now correctly persists its start time across HA restarts
- **Fixed**: Warning "Missing start time in PrimingState, staying in priming" no longer appears
- **Fixed**: System now properly transitions to DRIFTING after 24-48 hours as designed
- **Added**: Automatic fallback initialization if start time is missing
- **Added**: Persistence trigger when start time is auto-initialized

## ✨ Features from v1.5.0-alpha1

### Passive Learning System (Still Included)
- **Automatic Thermal Characterization**: Learns tau values during PRIMING by analyzing natural AC cycles
- **Non-Intrusive**: No active probing required
- **Exponential Curve Fitting**: Advanced mathematical analysis
- **Configurable Thresholds**: Adjust sensitivity for your building

## 🔄 What's Changed Since alpha1

### Code Changes
- Modified `ThermalManager.serialize()` to include `priming_start_time` field
- Modified `ThermalManager.restore()` to restore priming start time to handler
- Updated `PrimingState.execute()` to auto-initialize missing start time
- Added 6 comprehensive tests for persistence cycle

### Persistence Format Update
```json
{
  "state": {
    "current_state": "priming",
    "last_transition": "2025-01-11T10:30:00",
    "priming_start_time": "2025-01-11T08:00:00"  // NEW field
  }
}
```

## 📊 Testing Status

- **60 total tests** for passive learning and persistence
- All tests passing
- Verified fix resolves stuck PRIMING state issue
- Confirmed passive learning continues working during PRIMING

## 🚀 Installation

1. Download the release package
2. Copy to `custom_components/smart_climate/`
3. Restart Home Assistant
4. PRIMING state will now properly track duration across restarts

## 📋 Full Changelog

### Added (from alpha1)
- Passive thermal learning during PRIMING state
- Exponential curve fitting for tau extraction
- HVAC state tracking in StabilityDetector
- Configuration options for passive learning thresholds

### Fixed (new in alpha2)
- PRIMING state stuck after HA restart
- Missing start time warning in logs
- Proper state transition after configured duration

### Changed
- Thermal persistence format now includes priming_start_time
- PrimingState handler more resilient to missing data

## 🏷️ Version Info

- **Version**: 1.5.0-alpha2
- **Type**: Alpha Pre-release
- **Branch**: main
- **Commit**: 2d3ed71
- **Home Assistant**: 2024.1.0+
- **Python**: 3.11+

## ⚠️ Alpha Release Notice

This is an alpha release for testing. While the critical PRIMING bug is fixed and all tests pass, please continue monitoring system behavior and report any issues.

## 🐛 Bug Reports

Please report issues at: https://github.com/VectorBarks/smart-climate/issues

Include:
- Home Assistant version
- Smart Climate version (1.5.0-alpha2)
- Debug logs with `smart_climate: debug`
- Description of observed behavior

## 💡 Key Improvements

This release ensures that:
1. **PRIMING completes properly** - No more infinite PRIMING after restarts
2. **Passive learning works** - Tau values learned during the PRIMING period
3. **State persistence improved** - All critical state data survives restarts
4. **Graceful degradation** - System self-heals if data is missing