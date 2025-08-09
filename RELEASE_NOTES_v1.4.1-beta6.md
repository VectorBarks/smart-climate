# Release Notes - v1.4.1-beta6

## 🎯 Critical Thermal Persistence Fixes

This release fixes critical bugs that prevented the thermal efficiency feature from working properly. Thermal learning data now persists across restarts and calibration respects user configuration.

## 🐛 Bug Fixes

### Thermal Data Persistence (Root Cause)
- **Fixed #67**: Thermal data section in JSON was empty - serialization callback registration was broken
- **Fixed #64**: Probe history now saves correctly (resolved by #67)
- **Fixed #66**: Thermal state now restores on startup (resolved by #67)
- Impact: Thermal learning survives Home Assistant restarts

### Calibration Hour Configuration
- **Fixed #63**: Calibration hour now uses configured value instead of hardcoded 2-3 AM
- Users can now set when daily calibration runs (0-23 hours)
- Maintains backward compatibility with default of 2 AM

### Diagnostic Accuracy
- **Fixed #65**: `tau_values_modified` now shows actual modification time instead of current time
- Only updates when tau values actually change (>0.01 difference)
- Provides accurate diagnostic information

## 🧪 Testing
- Added 22 new tests covering all fixes
- All 150+ thermal tests passing
- Integration tests verify full persistence cycle

## 📦 Installation

### HACS (Recommended)
1. Update to latest version via HACS
2. Restart Home Assistant
3. Verify thermal data persists in `.storage/smart_climate_learning_*.json`

### Manual Installation
1. Download the latest release
2. Copy to `custom_components/smart_climate/`
3. Restart Home Assistant

## ⚠️ Breaking Changes
None - all changes maintain backward compatibility

## 🔄 Upgrade Notes
- Thermal data will start persisting after first save (hourly by default)
- Check your calibration_hour setting if you want calibration at a specific time
- Existing configurations will continue to work

## 📊 Technical Details

### Files Changed
- `__init__.py`: Fixed callback registration for thermal persistence
- `thermal_model.py`: Added tau modification tracking
- `thermal_manager.py`: Enhanced serialization with timestamps
- `thermal_special_states.py`: Use configured calibration hour
- `sensor.py`: Display real tau modification time

### Test Coverage
- `test_tau_modification_tracking.py`: 11 tests
- `test_thermal_persistence_integration.py`: 2 integration tests  
- `test_calibration_hour_config.py`: 9 tests

## 🚀 Next Steps
- Monitor thermal learning persistence
- Verify calibration runs at configured time
- Report any issues with thermal efficiency feature

## 📝 Full Changelog
- fix: track actual tau modification timestamps instead of current time
- fix: repair thermal data persistence callback registration
- fix: use configured calibration_hour instead of hardcoded 2-3 AM
- chore: bump version to 1.4.1-beta6

---
*Please report any issues on [GitHub](https://github.com/VectorBarks/smart-climate/issues)*