# Release Notes - v1.4.3-beta2

## 🐛 Critical Bug Fix Release

This release fixes a critical runtime error in the thermal state system that prevented proper state transitions.

## 🔧 Bug Fixes

### Critical: Thermal State Handler Signature Mismatch
- **Issue**: `TypeError: PrimingState.execute() takes 2 positional arguments but 4 were given`
- **Cause**: State handlers expected `execute(context)` but were called with `execute(context, current_temp, operating_window)`
- **Fix**: Updated all 6 state handlers to accept the correct signature
- **Impact**: Thermal state transitions now work correctly without runtime errors

### Test Suite Updates
- Updated all test files to use the new execute() signature
- Fixed 50+ test calls across 5 test files
- Tests now properly validate thermal state behavior

## 📊 Changes from beta1

### Files Modified
- `thermal_states.py` - Base class signature updated
- `thermal_special_states.py` - All special state handlers fixed
- `thermal_state_handlers.py` - Standard state handlers fixed
- 5 test files - Updated for new signature

## 🔄 Upgrade Instructions

**IMPORTANT**: This is a critical fix. If you installed beta1, please update immediately.

1. Update via HACS or manually copy files
2. Restart Home Assistant
3. Verify thermal states are transitioning correctly in logs

## ✅ Testing

- All state handlers tested with new signature
- Thermal state transitions verified
- No regression in existing functionality

## 📝 Note

This release maintains all features from v1.4.3-beta1:
- Opportunistic calibration system
- Force Calibration button
- Realistic drift thresholds (0.3°C default)
- Removed calibration_hour option

---

**Full Changelog**: [v1.4.3-beta1...v1.4.3-beta2](https://github.com/VectorBarks/smart-climate/compare/v1.4.3-beta1...v1.4.3-beta2)

**Critical Fix**: All users on beta1 should update immediately to resolve thermal state errors.