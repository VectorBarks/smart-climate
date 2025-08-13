# Release Notes - v1.5.0-beta9

## Bug Fixes

### Heat Index Calculation
Fixed incorrect heat index calculation that was showing wildly wrong values:
- Replaced broken simplified formula with proper Rothfusz regression formula
- Heat index now only calculated for temperatures above 27°C (80°F)
- Indoor conditions (24°C @ 49.5% humidity) now correctly show 24°C instead of 37°C
- Properly handles extreme heat conditions like 34.4°C @ 36.2% humidity

### Status Sensors
Fixed humidity status sensors showing as unavailable:
- Sensor Status and Comfort Level sensors now properly display their text values
- Added proper handling for text-based sensor values
- Both status sensors now show as available with correct status strings

## Changes from v1.5.0-beta8
- **Fixed**: Heat index calculation using incorrect formula
- **Fixed**: Status sensors (sensor_status, comfort_level) showing unavailable
- **Improved**: Heat index now uses industry-standard Rothfusz regression

## Humidity Monitoring Status
All 12 humidity sensors now working correctly:
1. ✅ Indoor Humidity
2. ✅ Outdoor Humidity  
3. ✅ Humidity Differential
4. ✅ Heat Index (now with correct formula)
5. ✅ Indoor Dew Point
6. ✅ Outdoor Dew Point
7. ✅ Absolute Humidity
8. ✅ ML Humidity Offset
9. ✅ ML Humidity Confidence
10. ✅ ML Humidity Weight
11. ✅ Sensor Status (now available)
12. ✅ Comfort Level (now available)

## Testing
- Heat index shows correct values for both indoor and outdoor conditions
- Status sensors properly display text values
- All humidity sensors functional and integrated with ML model

## Upgrade Notes
This release fixes critical calculation errors in the heat index sensor. Users on v1.5.0-beta8 should upgrade to get accurate heat index readings and working status sensors.

---
*Smart Climate Control - Accurate climate monitoring with proper heat index calculations.*