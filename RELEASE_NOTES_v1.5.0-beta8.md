# Release Notes - v1.5.0-beta8

## Critical Fix

### Humidity ML Integration
Fixed the critical issue where humidity data was not being integrated into the ML model:
- Humidity values are now properly collected from sensor_manager
- FeatureEngineering component calculates derived humidity metrics (heat index, dew points)
- All humidity data is now included in OffsetInput for ML predictions
- The ML model now properly uses humidity to influence temperature offset calculations

## Changes from v1.5.0-beta7
- **Fixed**: Humidity data not being passed to ML model for predictions
- **Added**: FeatureEngineering integration in climate.py
- **Added**: Proper humidity data collection and population in OffsetInput
- **Fixed**: ML humidity sensors now show actual values instead of 0

## Humidity Monitoring Features
The complete humidity monitoring system now includes:
- 12 humidity-related sensors all working correctly
- Indoor/outdoor humidity tracking
- Heat index and dew point calculations
- Humidity differential monitoring
- Absolute humidity in g/m³
- ML integration metrics showing humidity's impact on predictions
- Sensor status and comfort level indicators
- Event-driven monitoring with configurable thresholds
- 24-hour data persistence with daily aggregation

## Testing
- All 127 humidity tests passing
- Humidity sensors properly display values
- ML integration confirmed working
- Humidity data influences temperature offset predictions

## Debug Logging
To monitor humidity integration with ML, add to your configuration.yaml:
```yaml
logger:
  logs:
    custom_components.smart_climate: debug
    custom_components.smart_climate.climate: debug
    custom_components.smart_climate.offset_engine: debug
    smart_climate.humidity: debug
    smart_climate.humidity.ml: debug
```

## Upgrade Notes
This is a critical fix release. Users on v1.5.0-beta7 should upgrade immediately to enable proper humidity-ML integration. The humidity data will now properly influence temperature offset predictions as originally intended.

---
*Smart Climate Control - Now with fully integrated humidity-aware ML predictions for optimal comfort.*