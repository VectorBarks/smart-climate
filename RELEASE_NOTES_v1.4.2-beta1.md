# Smart Climate Control v1.4.2-beta1

## 🚨 Critical Bug Fixes Release

This release addresses critical bugs that were preventing core functionality from working correctly, causing energy waste and disabled thermal learning.

## 🐛 Major Bugs Fixed

### 1. Timezone Confusion in Weather Strategies (#70) - FIXED ✅
**Problem**: Weather strategies were comparing UTC forecast times to local time, causing pre-cooling to run DURING hot periods instead of BEFORE them.
- **Impact**: Significant energy waste - AC was cooling MORE during sunny periods when it should have been allowing higher temperatures
- **Solution**: All time calculations now use UTC consistently with proper timezone conversions for display

### 2. Thermal State Transitions Never Occurring - FIXED ✅
**Problem**: Thermal manager was stuck in PRIMING state indefinitely, never transitioning to CALIBRATING or PROBING states.
- **Impact**: Thermal learning was completely disabled - system couldn't learn your home's thermal characteristics
- **Solution**: Added proper state transition checks that run periodically, including calibration_hour transitions

### 3. Smart Sleep Mode Wake-Up - NEW FEATURE ✅
**Problem**: Weather strategies didn't interact intelligently with preset modes.
- **Solution**: System now auto-wakes from sleep mode (not away) when pre-cooling is needed for approaching weather events
- **Benefits**: 
  - Automatically prepares for extreme weather while you sleep
  - Respects away mode - never wakes when you're not home
  - Suppresses pre-cooling if manually woken during active events (too late to help)

## 💡 User Impact

### Energy Savings
- Pre-cooling now correctly runs BEFORE hot periods, not during them
- Significant reduction in unnecessary cooling during peak heat
- Smart suppression prevents wasteful cooling when it won't help

### Comfort Improvements
- Thermal learning now works, optimizing your system over time
- Auto-wake ensures your home is prepared for extreme weather
- Better temperature stability through proper thermal modeling

### System Intelligence
- Calibration cycles run nightly as designed (default 2 AM)
- Probing can occur to measure thermal time constants
- Weather strategies apply at the correct times

## 📊 Technical Details

### Files Modified
- `forecast_engine.py` - UTC time handling throughout
- `thermal_manager.py` - State transition logic
- `thermal_special_states.py` - Calibration hour checks
- `coordinator.py` - Thermal updates and wake-up orchestration
- `climate.py` - Wake-up request handling
- `mode_manager.py` - Mode change tracking
- `models.py` - WeatherStrategy dataclass

### Testing
- 30+ new tests covering all bug fixes
- Comprehensive timezone scenario testing
- State transition verification
- Sleep mode wake-up scenarios

## 🔄 Upgrade Instructions

1. Update via HACS or manually download the latest release
2. Restart Home Assistant
3. Your thermal system will begin calibration at the next calibration_hour
4. Weather strategies will immediately work correctly

## ⚠️ Breaking Changes

None - all fixes maintain backward compatibility.

## 🎯 What's Next

- v1.5.0: Microclimate correction implementation (architecture complete)
- UI improvements for configuration options (#61, #62)
- Performance optimizations for ML components (#37)

## 📝 Notes

This is a critical bug fix release. All users should upgrade immediately to restore proper functionality and achieve significant energy savings.

---

**Full Changelog**: [v1.4.1-beta7...v1.4.2-beta1](https://github.com/VectorBarks/smart-climate/compare/v1.4.1-beta7...v1.4.2-beta1)