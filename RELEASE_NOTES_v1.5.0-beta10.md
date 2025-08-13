# Release Notes - v1.5.0-beta10

## Bug Fix

### Text Sensor Display
Fixed humidity status sensors showing "unknown" instead of proper text values:
- Removed `state_class` attribute from text sensors (was causing Home Assistant to treat them as numeric)
- Set `unit_of_measurement` to `None` instead of empty string for text sensors
- Sensor Status now properly displays: "Both", "Indoor Only", "Outdoor Only", or "None"
- Comfort Level now properly displays: "Optimal", "Comfortable", "Too Dry", "Too Humid", etc.

## Changes from v1.5.0-beta9
- **Fixed**: Text sensors (status and comfort level) showing "unknown"
- **Improved**: Proper text sensor configuration for Home Assistant compatibility

## Complete Humidity System Status
All 12 humidity sensors now fully functional:
1. ✅ Indoor Humidity - working
2. ✅ Outdoor Humidity - working
3. ✅ Humidity Differential - working
4. ✅ Heat Index - working (fixed in beta9)
5. ✅ Indoor Dew Point - working
6. ✅ Outdoor Dew Point - working
7. ✅ Absolute Humidity - working
8. ✅ ML Humidity Offset - working (0.0 until ML methods implemented)
9. ✅ ML Humidity Confidence - working (0.0 until ML methods implemented)
10. ✅ ML Humidity Weight - working (0.0 until ML methods implemented)
11. ✅ Sensor Status - now working (was showing "unknown")
12. ✅ Comfort Level - now working (was showing "unknown")

## Testing
- All humidity sensors display correct values
- Text sensors show proper status strings
- Heat index calculation accurate for all temperature ranges
- ML integration ready for future feature importance methods

## Upgrade Notes
This release completes the humidity monitoring system fixes. Users on v1.5.0-beta9 should upgrade to see proper text values for status sensors.

---
*Smart Climate Control - Complete humidity monitoring with all sensors working correctly.*