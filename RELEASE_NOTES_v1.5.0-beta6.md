# Release Notes - v1.5.0-beta6

## What's New

### Humidity Monitoring System
Added comprehensive humidity monitoring and diagnostic logging capabilities to improve ML model performance and user insight.

## Features

### New Components
- **HumidityMonitor**: Central orchestrator for all humidity monitoring operations
- **HumidityLogger**: Structured diagnostic logging with contextual information
- **HumidityBuffer**: Efficient 24-hour circular buffer for event storage
- **HumidityAggregator**: Calculates daily statistics and comfort metrics

### New Sensors (12 total)
- **Core Sensors**: Indoor/Outdoor humidity with device class and units
- **Calculated Sensors**: Heat index, dew points, absolute humidity, differential
- **ML Impact Sensors**: Humidity offset contribution, confidence impact, feature weight
- **Status Sensors**: Overall humidity sensor status and comfort level

### Configuration Options
- 8 configurable thresholds for humidity monitoring
- Customizable logging levels (INFO/DEBUG)
- Event-driven triggers for significant changes

### Integration Features
- Event-driven architecture for efficient updates
- ML model integration showing humidity's impact on offset calculations
- 24-hour data persistence with daily aggregation
- Automatic sensor creation with proper device associations

## Technical Improvements
- Separated concerns between monitoring, logging, storage, and UI
- Observer pattern for efficient event handling
- Memory-efficient circular buffer implementation
- Comprehensive test coverage (127 tests across 12 test files)

## Performance
- Event-driven updates reduce polling overhead
- Batch sensor updates for efficiency
- Lazy calculation of aggregates
- Rate limiting for rapid changes

## Testing
- 127 tests covering all humidity monitoring components
- Unit tests for each component in isolation
- Integration tests for end-to-end data flow
- Edge case handling for missing sensors

## Configuration
New options in Options Flow:
- `humidity_change_threshold`: Trigger threshold for humidity changes (default: 2%)
- `heat_index_warning`: Heat index warning level (default: 26°C)
- `heat_index_high`: Heat index high level (default: 29°C)
- `dew_point_warning`: Dew point warning threshold (default: 2°C)
- `dew_point_critical`: Dew point critical threshold (default: 1°C)
- `differential_significant`: Significant humidity differential (default: 25%)
- `differential_extreme`: Extreme humidity differential (default: 40%)
- `humidity_log_level`: Logging detail level (default: DEBUG)

## Bug Fixes
- Fixed test failures in humidity sensor integration tests

## Known Issues
None

## Upgrade Notes
This release adds new functionality without breaking existing features. The humidity monitoring system will automatically activate if humidity sensors are configured. All new sensors are optional and will only appear if humidity sensors are available.

## Next Release Preview
- Microclimate correction implementation
- Additional ML model improvements
- Enhanced dashboard visualization

---
*Smart Climate Control continues to evolve with intelligent features for optimal comfort and efficiency.*