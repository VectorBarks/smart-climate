# Release Notes - v1.5.0-beta11

## 🚨 CRITICAL FIX - Humidity Sensors Now Actually Update!

### Root Cause Identified and Fixed
The humidity sensors were showing "unknown" because they were **never being updated by Home Assistant**. The sensors were created during setup but remained orphaned - their `async_update()` method was never called because Home Assistant didn't know it needed to poll them.

### The Fix
Added `_attr_should_poll = True` to the `HumiditySensorEntity` base class. This simple but critical change enables Home Assistant to:
- Poll each humidity sensor every 30 seconds
- Call their `async_update()` method to fetch fresh data
- Update sensor states with actual values instead of "unknown"

## What This Fixes

### Status Sensors - NOW WORKING! ✅
- **Sensor Status** will now show:
  - "Both" when both indoor and outdoor sensors are available
  - "Indoor Only" when only indoor sensor has data
  - "Outdoor Only" when only outdoor sensor has data  
  - "None" when no sensors have data

### Comfort Level - NOW WORKING! ✅
- **Comfort Level** will now show:
  - "Optimal" for 40-50% humidity
  - "Comfortable" for 30-40% or 50-60% humidity
  - "Too Dry" for humidity below 30%
  - "Too Humid" for humidity above 60%
  - "Caution - Elevated Heat Index" when heat index is elevated
  - "Uncomfortable - High Heat Index" when heat index is high

## All 12 Humidity Sensors - FULLY FUNCTIONAL! 🎉

1. ✅ Indoor Humidity - **working & updating**
2. ✅ Outdoor Humidity - **working & updating**
3. ✅ Humidity Differential - **working & updating**
4. ✅ Heat Index - **working & updating** (correct formula since beta9)
5. ✅ Indoor Dew Point - **working & updating**
6. ✅ Outdoor Dew Point - **working & updating**
7. ✅ Absolute Humidity - **working & updating**
8. ✅ ML Humidity Offset - **working & updating**
9. ✅ ML Humidity Confidence - **working & updating**
10. ✅ ML Humidity Weight - **working & updating**
11. ✅ **Sensor Status - FINALLY WORKING & UPDATING!**
12. ✅ **Comfort Level - FINALLY WORKING & UPDATING!**

## Technical Details

**Problem:** Sensors inherited from `SensorEntity` but didn't tell Home Assistant they needed polling.

**Solution:** Set `_attr_should_poll = True` to enable Home Assistant's polling mechanism.

**Update Frequency:** Every 30 seconds (Home Assistant default polling interval).

**Credit:** Issue diagnosed using sequential thinking analysis and confirmed by Gemini AI consultation.

## Upgrade Notes

**CRITICAL UPDATE** - Users on any previous beta version should upgrade immediately to v1.5.0-beta11 to get working humidity sensors. After upgrading:
1. Restart Home Assistant
2. Wait 30-60 seconds for first sensor updates
3. All humidity sensors should show actual values instead of "unknown"
4. Status sensors will display proper text descriptions

---
*Smart Climate Control - Humidity monitoring finally working as designed!*