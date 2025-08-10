# Smart Climate Control v1.4.2-beta2

## 🔥 Hotfix Release - Critical Weather Strategy Bug

This release fixes a critical bug discovered in beta1 where weather strategies were still activating during (instead of before) weather events.

## 🐛 Critical Fix Since beta1

### Weather Strategy Detection Logic - FIXED ✅
**Problem**: System was activating pre-cooling even when ALREADY in sunny/hot conditions
- At 10:39 with sun since 08:00, system would still try to pre-cool for "future" sun at 11:00
- Caused energy waste by cooling during peak heat instead of before

**Solution**: 
- System now checks if currently in target weather conditions
- Looks back 2 hours to detect ongoing events
- Only activates pre-cooling if event is genuinely in the future
- Clear logging when skipping pre-cooling: "Already in sunny conditions - skipping pre-cooling"

## 🔧 Additional Improvements

### Thermal Constants Initialization - FIXED ✅
- Eliminated "Missing thermal constants" warnings
- ThermalManager properly initializes all timing parameters
- Supports configuration overrides for all thermal constants

### Enhanced Debug Logging - NEW ✅
**Thermal System:**
- Shows why state transitions do/don't occur
- Logs calibration hour checks and timing calculations
- Tracks elapsed time in each state

**Seasonal Learner:**
- Logs every learning attempt with parameters
- Shows pattern detection process
- New pattern summary method for debugging
- Helps diagnose why patterns aren't being learned

## 📊 All Fixes from v1.4.2 Series

### From beta1:
- ✅ Timezone confusion in weather strategies (#70)
- ✅ Thermal state transitions never occurring
- ✅ Smart sleep mode wake-up for weather events

### New in beta2:
- ✅ Weather strategies correctly detect ongoing events
- ✅ Thermal constants properly initialized
- ✅ Comprehensive debug logging for troubleshooting

## 💡 User Impact

### Immediate Benefits
- **Energy Savings**: No more wasteful cooling during hot/sunny periods
- **Proper Pre-cooling**: Only runs BEFORE events when it's beneficial
- **Better Diagnostics**: Debug logs reveal why learning isn't occurring

### Example Scenario
**Before beta2**: 
- 10:00 AM - Already sunny since 8:00 AM
- System: "I'll pre-cool for sun at 11:00!" ❌
- Result: Wastes energy cooling during peak sun

**After beta2**:
- 10:00 AM - Already sunny since 8:00 AM  
- System: "Already sunny - no pre-cooling needed" ✅
- Result: Significant energy savings

## 🔄 Upgrade Instructions

1. Update via HACS or manually download the latest release
2. Restart Home Assistant
3. Check logs for enhanced debug information
4. Weather strategies will immediately work correctly

## ⚠️ Breaking Changes

None - all fixes maintain backward compatibility.

## 📝 Technical Details

### Files Modified
- `forecast_engine.py` - Weather event detection logic
- `thermal_manager.py` - Thermal constants initialization
- `thermal_special_states.py` - Enhanced state logging
- `seasonal_learner.py` - Pattern detection logging

### Testing
- 50+ tests covering all functionality
- Verified no regression in existing features
- Confirmed energy-saving behavior works correctly

---

**Full Changelog**: [v1.4.2-beta1...v1.4.2-beta2](https://github.com/VectorBarks/smart-climate/compare/v1.4.2-beta1...v1.4.2-beta2)