# Release Notes - v1.5.0-beta7

## Bug Fixes

### Humidity Sensor Initialization
Fixed critical issues preventing humidity sensors from being created:
- Corrected HumidityMonitor lookup location in sensor platform
- Fixed indentation errors that caused ImportError on sensor platform load
- Added debug logging to track humidity sensor creation status

## Changes from v1.5.0-beta6
- **Fixed**: Humidity sensors not appearing in Home Assistant entity list
- **Fixed**: IndentationError preventing sensor platform from loading
- **Added**: Debug logging for humidity sensor initialization

## Humidity Monitoring (from v1.5.0-beta6)
The humidity monitoring system includes:
- 12 humidity-related sensors
- Event-driven monitoring with configurable thresholds
- ML integration showing humidity's impact on temperature offset calculations
- 24-hour data persistence with daily aggregation

## Testing
- All 127 humidity tests passing
- Sensor platform loads correctly
- Humidity sensors properly initialized when configured

## Debug Logging
To see humidity debug logs, add to your configuration.yaml:
```yaml
logger:
  logs:
    custom_components.smart_climate: debug
    smart_climate.humidity: debug
```

Or use Developer Tools → Services → logger.set_level:
```yaml
custom_components.smart_climate: debug
smart_climate.humidity: debug
```

## Upgrade Notes
This is a bug fix release. Users on v1.5.0-beta6 should upgrade to see humidity sensors properly.

---
*Smart Climate Control continues to evolve with intelligent features for optimal comfort and efficiency.*