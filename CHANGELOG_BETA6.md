# Smart Climate Control v1.5.5-beta6

## Critical Data Collection Fixes

### 🔧 Fixed Learning System Data Collection
**Problem:** The learning system was completely broken - after 2 weeks of operation, `learner_data` was empty with 0 samples collected.

**Root Cause:** Learning was incorrectly paused during DRIFTING state (normal operation), preventing ALL data collection. The system was stuck in a catch-22 where it needed to learn during DRIFTING but was programmatically prevented from doing so.

**Fix:** Modified learning pause logic to only pause during PRIMING state (initial 24-48 hours). Learning is now active during DRIFTING state when thermal behavior data is actually needed.

**Impact:** The ML learning system will now properly collect and learn from temperature offset data, improving accuracy over time.

### 🌡️ Fixed Outdoor Temperature Recording in Probe History
**Problem:** All probe history entries had `outdoor_temp: null`, preventing weather-correlated thermal analysis.

**Root Cause:** ProbeResult objects were created without passing the outdoor_temp parameter, even though the data was available.

**Fix:** Updated all ProbeResult creation points to properly capture and store outdoor temperature:
- `probe_manager.py`: Stores outdoor_temp when starting probe, passes it when completing
- `thermal_special_states.py`: Passes available outdoor_temp to ProbeResult  
- `probe_scheduler.py`: Added outdoor_temp parameter handling

**Impact:** Probe history will now include outdoor temperature data, enabling better thermal time constant analysis based on weather conditions.

## Files Modified
- `custom_components/smart_climate/coordinator.py` - Fixed learning pause logic
- `custom_components/smart_climate/probe_manager.py` - Added outdoor_temp capture
- `custom_components/smart_climate/thermal_special_states.py` - Fixed ProbeResult creation
- `custom_components/smart_climate/probe_scheduler.py` - Added outdoor_temp parameter
- `tests/test_thermal_coordinator_phase2.py` - Updated tests for new learning behavior
- `tests/test_thermal_efficiency_e2e.py` - Updated tests for DRIFTING state learning

## Testing
- ✅ Learning now active during DRIFTING state
- ✅ Outdoor temperature properly captured in new probe results
- ✅ All related tests updated and passing

## Upgrade Notes
- No configuration changes required
- Existing probe history entries will remain with null outdoor_temp (historical data unchanged)
- New probe results will automatically include outdoor temperature
- Learning will begin collecting data immediately after upgrade

---
*These fixes address fundamental data collection issues that were preventing the system from learning and improving over time.*