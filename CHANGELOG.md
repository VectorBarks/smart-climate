# Changelog

All notable changes to Smart Climate Control will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] - 2025-07-10

### 🚀 Major Features

#### **Startup AC Temperature Update** - New in v1.2.0
- **Immediate Application**: Smart Climate now applies learned temperature offsets immediately when Home Assistant starts
- **Learning Data Integration**: Uses cached learning data for instant temperature compensation on startup
- **Threshold Override**: Startup updates bypass the normal 0.3°C change threshold for immediate effect
- **Graceful Handling**: Robust error handling ensures startup failures don't break entity initialization
- **Enhanced Architecture**: 
  - New `is_startup_calculation` flag in `SmartClimateData` for startup detection
  - `async_force_startup_refresh()` method in coordinator for triggering startup refresh
  - Modified climate entity `async_added_to_hass()` to trigger initial temperature calculation
  - Updated `_handle_coordinator_update()` to handle startup scenario OR significant offset changes

#### **Smart Climate Dashboard** - Complete Visualization System
- Beautiful, responsive dashboard for monitoring learning progress and performance
- Automatic creation of 5 dashboard sensor entities - zero configuration needed
- One-click dashboard generation service creates customized YAML
- Real-time visualization of temperature offsets, accuracy, and AC behavior
- Works on all devices with responsive design using only core Home Assistant cards

#### **Multi-Factor Confidence Calculation** - Enhanced ML Intelligence
- **Fixed**: Confidence level no longer stuck at 50% - now provides meaningful progression
- **Enhanced Algorithm**: Uses sample count, condition diversity, time coverage, and prediction accuracy
- **Logarithmic Scaling**: Natural confidence progression from 0-100% based on actual learning
- **Better User Feedback**: Users can now see real learning progress instead of static 50%

### 🐛 Critical Bug Fixes

#### **Training Data Persistence** - Issues #8, #9
- **Periodic Save System**: Configurable save intervals (5 minutes to 24 hours, default 60 minutes)
- **Shutdown Protection**: Enhanced shutdown save with 5-second timeout protection
- **Save Diagnostics**: Real-time save statistics in entity attributes (save_count, failed_save_count, last_save_time)
- **Reliable Recovery**: No more training data loss during Home Assistant restarts

#### **Integration Startup Failures** - Issue #11
- **Retry Mechanism**: Exponential backoff retry system (30s, 60s, 120s, 240s intervals)
- **Zigbee Compatibility**: Handles sensors that take >60s to initialize
- **User Notifications**: Clear feedback on retry progress and final failure status
- **Graceful Recovery**: Automatic recovery when sensors become available

#### **Temperature Logic Corrections** - Issue #13
- **Fixed Backwards Operation**: Room temperature deviation now properly considered
- **Correct Cooling Logic**: When room > target, AC sets lower temperature for more cooling
- **Intuitive Behavior**: Eliminates confusing AC behavior that warmed when cooling was needed

#### **Dashboard Sensor Availability** - Issue #17
- **DataUpdateCoordinator Pattern**: Migrated from direct offset_engine access to proper coordinator pattern
- **Real-time Updates**: Dashboard sensors now receive data through coordinator updates every 30 seconds
- **Robust Architecture**: Each climate entity has its own dedicated coordinator instance
- **No More Red Indicators**: All 5 sensor types now show as available with real-time data

### 🛡️ **Stable State Calibration** - Prevents Overcooling
- **Intelligent Caching**: System caches offsets only during stable periods (AC idle + temps converged)
- **Feedback Loop Prevention**: Uses cached stable offset during active cooling
- **User Safety**: Prevents severe overcooling during initial learning (e.g., 24.5°C → 23°C)
- **Automatic Transition**: Seamlessly moves to full learning mode after calibration complete

### 🧪 **Quality Assurance**
- **100+ New Tests**: Comprehensive test coverage with unit and integration tests
- **Test-Driven Development**: All features implemented using TDD methodology
- **Backward Compatibility**: 100% compatibility maintained - no breaking changes
- **Performance Validated**: Startup updates complete within 2 seconds

### 📊 **User Experience Improvements**
- **Immediate Benefits**: Users benefit from learned temperature compensation from HA startup
- **Better Feedback**: Real confidence progression shows actual learning progress
- **Clear Monitoring**: Dashboard provides comprehensive visibility into system behavior
- **Reliable Operation**: Robust error handling and automatic recovery mechanisms

### 🔧 **Technical Architecture Enhancements**
- **Enhanced Data Models**: Added startup calculation flag support
- **Improved Coordination**: Better separation of concerns between climate and sensor platforms
- **Robust Error Handling**: Comprehensive error handling with graceful degradation
- **Enhanced Logging**: Better debugging and troubleshooting capabilities

### 🆕 **New Sensor Entities** (Created Automatically)
- `sensor.{entity}_offset_current` - Current temperature offset in real-time
- `sensor.{entity}_learning_progress` - Learning completion percentage (0-100%)
- `sensor.{entity}_accuracy_current` - Current prediction accuracy (now progresses correctly)
- `sensor.{entity}_calibration_status` - Shows calibration phase status
- `sensor.{entity}_hysteresis_state` - AC behavior state (idle/cooling/heating)

### 🛠️ **New Service**
- `smart_climate.generate_dashboard` - Generates complete dashboard configuration
  - Automatically replaces entity IDs in template
  - Sends dashboard via persistent notification
  - Includes step-by-step setup instructions
  - No manual YAML editing required

## [1.2.0-beta5] - 2025-07-10 [Pre-release]

### Fixed
- **Dashboard Sensors Availability** (#17)
  - Fixed dashboard sensors showing as unavailable (red "!" indicators)
  - Root cause: Sensors couldn't access offset_engine instance due to architectural limitations
  - Implemented DataUpdateCoordinator pattern for proper cross-platform data sharing
  - Dashboard sensors now receive data through coordinator updates every 30 seconds
  - All 5 sensor types now show as available with real-time data updates
  - Comprehensive test coverage: 45+ tests for coordinator implementation

### Changed
- **Architecture Enhancement**
  - Migrated from direct offset_engine access to DataUpdateCoordinator pattern
  - Each climate entity now has its own dedicated coordinator instance
  - Sensors use CoordinatorEntity base class for automatic availability management
  - OffsetEngine exposes dashboard data through new async_get_dashboard_data() method
  - Improved separation of concerns between climate and sensor platforms

### Technical Improvements
- Added robust error handling in coordinator data fetching
- Coordinator automatically handles entity availability state
- Initial data fetch on coordinator setup ensures immediate sensor availability
- Enhanced logging for coordinator operations and data updates
- Backward compatible with existing configurations

## [1.2.0-beta4] - 2025-07-09 [Pre-release]

### Fixed
- **Dashboard Sensor Availability** (#17)
  - Fixed dashboard sensors showing as unavailable (red "!" indicators)
  - Root cause: Complex coordinator dependency check in sensor.py line 92
  - Applied KISS solution: simplified `available` property to `return self._offset_engine is not None`
  - All 5 sensor types (Current Offset, Learning Progress, Current Accuracy, Calibration Status, Hysteresis State) now show as available
  - Comprehensive test coverage: 28 unit tests + 29 integration tests = 57 total tests
  - Maintains existing error handling in `native_value` methods
  - No regression in existing functionality - purely availability logic fix

### Note
This release was superseded by v1.2.0-beta5 which implements a more robust architectural solution using DataUpdateCoordinator pattern.

## [1.2.0-beta3] - 2025-07-09 [Pre-release]

### Added
- **Complete Training Data Persistence System** - Resolves all data loss issues
  - Configurable save intervals (5 minutes to 24 hours) with 60-minute default
  - Save diagnostics exposed in entity attributes (save_count, failed_save_count, last_save_time)
  - Enhanced shutdown save with 5-second timeout protection
  - INFO level logging for successful saves with sample count details
  - WARNING level logging for save errors (upgraded from DEBUG)
  - Save statistics tracking for troubleshooting and monitoring
- **Robust Integration Startup System** - Fixes startup failures with slow sensors
  - Retry mechanism with exponential backoff (30s, 60s, 120s, 240s intervals)
  - Configurable initial timeout (default 60 seconds)
  - User notifications for retry status and final failure
  - Graceful handling of Zigbee sensors that take >60s to initialize
  - Automatic recovery when sensors become available
- **Fixed Temperature Adjustment Logic** - Corrects backwards AC operation
  - Room temperature deviation now properly considered in calculations
  - When room > target, AC sets lower temperature for more cooling
  - When room < target, AC sets higher temperature for less cooling
  - Eliminates confusing behavior where AC would warm when cooling needed

### Fixed
- **Training Data Persistence Issues** (#8, #9)
  - Periodic save interval changed from 10 to 60 minutes (as expected by users)
  - Shutdown save now reliably saves data before Home Assistant restart
  - Save operations no longer block Home Assistant during shutdown
  - Enhanced error handling prevents data corruption during save failures
- **Integration Startup Failures** (#11)
  - No more integration failures when Zigbee sensors take >60s to initialize
  - Automatic retries with exponential backoff prevent permanent failures
  - Clear user notifications explain retry progress and final status
- **Temperature Logic Errors** (#13)
  - Fixed backwards temperature adjustment causing AC to warm instead of cool
  - Room temperature properly factored into offset calculations
  - Eliminated user confusion about AC behavior

### Enhanced
- **Save System Monitoring**
  - Real-time save statistics visible in Home Assistant UI
  - Users can track save frequency and success rates
  - Troubleshooting improved with detailed save logging
- **User Experience**
  - All save intervals configurable through UI (no more hardcoded values)
  - Clear feedback on persistence system status
  - Automatic retry system reduces setup frustration
  - Consistent temperature behavior eliminates user confusion

### Technical Improvements
- 50+ new test cases covering all persistence functionality
- Comprehensive error handling with graceful degradation
- Atomic save operations prevent data corruption
- Configurable save intervals with validation (300-86400 seconds)
- Enhanced logging throughout the system
- Backward compatibility maintained for existing configurations

## [1.2.0-beta1] - 2025-07-09 [Pre-release]

### Added
- **Smart Climate Dashboard - Complete Visualization System** (#7)
  - Beautiful, responsive dashboard for monitoring learning progress and performance
  - Automatic creation of 5 dashboard sensor entities - zero configuration needed
  - One-click dashboard generation service creates customized YAML
  - Real-time visualization of temperature offsets, accuracy, and AC behavior
  - Works on all devices with responsive design
  - Uses only core Home Assistant cards - no dependencies

### New Sensor Entities (Created Automatically)
- `sensor.{entity}_offset_current` - Current temperature offset in real-time
- `sensor.{entity}_learning_progress` - Learning completion percentage (0-100%)
- `sensor.{entity}_accuracy_current` - Current prediction accuracy
- `sensor.{entity}_calibration_status` - Shows calibration phase status
- `sensor.{entity}_hysteresis_state` - AC behavior state (idle/cooling/heating)

### New Service
- `smart_climate.generate_dashboard` - Generates complete dashboard configuration
  - Automatically replaces entity IDs in template
  - Sends dashboard via persistent notification
  - Includes step-by-step setup instructions
  - No manual YAML editing required

### Documentation
- New dashboard setup guide with visual examples
- Migration guide for existing users
- Updated README with dashboard feature highlights
- Service documentation for generate_dashboard

### Technical Improvements
- Added sensor platform with automatic entity creation
- Dashboard template with responsive grid layouts
- Comprehensive test coverage for dashboard features
- Performance optimized sensor updates (<10ms)

## [1.1.1-beta2] - 2025-07-09 [Pre-release]

### Added
- **Stable State Calibration Phase** - Prevents Overcooling During Initial Learning
  - Implements intelligent offset caching for the first 10 learning samples
  - Detects "stable states" when AC is idle and temperatures have converged
  - Caches offset only during stable periods (power < idle threshold AND temp diff < 2°C)
  - Uses cached stable offset during active cooling to prevent feedback loops
  - Provides clear calibration status messages to users
  - Automatically transitions to full learning mode after calibration

### Fixed
- **Critical Overcooling Issue** (#3)
  - System no longer applies large dynamic offsets during initial learning
  - Prevents room temperature from dropping well below target (e.g., 24.5°C → 23°C)
  - Especially important for ACs with evaporator coil sensors showing 15°C when cooling
  - Eliminates feedback loop that made the integration unusable during setup

### Technical Details
- Added `MIN_SAMPLES_FOR_ACTIVE_CONTROL` constant (10 samples)
- New `_stable_calibration_offset` attribute for caching stable offsets
- Enhanced `calculate_offset()` with calibration phase logic
- Comprehensive test suite with 8 new calibration tests
- Updated existing tests to work with calibration phase

## [1.1.1-beta1] - 2025-07-08 [Pre-release]

### Added
- **Enhanced Learning Switch Display**
  - Shows learned AC temperature thresholds directly in switch attributes
  - Displays AC start temperature and stop temperature when learned
  - Shows temperature window size and hysteresis sample count
  - Human-readable hysteresis state descriptions
- **Improved Documentation**
  - Comprehensive troubleshooting guide for overcooling during learning phase
  - New learning system guide explaining how the system adapts to AC behavior
  - Clearer explanations of power monitoring benefits

### Improved
- Learning switch now provides better visibility into hysteresis learning progress
- More intuitive attribute names for AC temperature window display
- Enhanced diagnostic information for troubleshooting learning behavior

## [1.1.0] - 2025-07-08

### Added
- **HysteresisLearner System** - Advanced AC Temperature Window Detection
  - Automatically learns AC start/stop temperature thresholds through power monitoring
  - Detects temperature patterns for AC on/off cycles
  - Sub-millisecond performance with efficient pattern matching
  - Improves learning accuracy by understanding AC behavior patterns
- **Enhanced Learning Switch Attributes**
  - Added `learning_started_at` timestamp to track when learning was enabled
  - Shows exact date/time in learning switch attributes
  - Helps users understand learning progress over time
- **Configurable Default Target Temperature**
  - New UI setting for default temperature (16-30°C range)
  - Sets initial temperature when climate entity has no target
  - Defaults to 24°C for optimal comfort
  - Prevents errors when wrapped entity returns None

### Changed
- **Learning System Architecture**
  - Integrated HysteresisLearner with LightweightOffsetLearner
  - Persistence schema upgraded to v2 with backward compatibility
  - Enhanced prediction accuracy using hysteresis context
  - Improved feedback loop with power state awareness

### Fixed
- **Critical Learning System Bugs**
  - Inverted offset calculation causing AC to heat instead of cool
  - Learning feedback now correctly applies negative offsets for cooling
  - Sample count persistence synchronization after restarts
  - Hysteresis state now shows "learning_hysteresis" when power sensor configured
- **Home Assistant Integration Issues**
  - Config flow TypeError (500 error) when accessing options
  - Added method aliases for OffsetEngine compatibility (`add_training_sample`, `get_optimal_offset`)
  - Fixed all deprecation warnings for HA 2024.1+ compatibility
  - Proper async method handling throughout integration
- **Component Compatibility**
  - Button entity category error in reset training data button
  - Periodic offset adjustments now work correctly
  - Target temperature always returns valid float
  - Enhanced error handling for wrapped entity access

## [1.0.1] - 2025-07-07

### Added
- Comprehensive UI configuration with ALL settings available through the interface
- New UI configuration options:
  - Away Mode Temperature (10-35°C) - Fixed temperature for away mode
  - Sleep Mode Offset (-5 to +5°C) - Additional offset for quieter night operation
  - Boost Mode Offset (-10 to 0°C) - Aggressive cooling offset
  - Gradual Adjustment Rate (0.1-2.0°C) - Temperature change per update
  - Learning Feedback Delay (10-300s) - Time before recording feedback
  - Enable Learning toggle - Separate from ML enabled flag
- Options flow now includes all configuration parameters
- Configuration validation ensures away temperature is within min/max range
- Enhanced user experience with no YAML editing required for any setting
- Reset Training Data button entity for clearing all learned patterns
  - Available in device configuration section
  - Creates backup before deletion for safety
  - Allows fresh start for learning system
- Configurable power thresholds for better AC state detection
  - Power Idle Threshold (10-500W) - Below this = AC idle/off
  - Power Min Threshold (50-1000W) - Below this = AC at minimum
  - Power Max Threshold (100-5000W) - Above this = AC at high/max
  - Settings only appear in UI when power sensor is configured
  - Validation ensures idle < min < max thresholds

### Changed
- UI configuration is now the recommended method for all users
- YAML configuration is now marked as optional/advanced
- Documentation updated to emphasize UI-first configuration approach

### Improved
- User onboarding experience with comprehensive UI settings
- Configuration flexibility without requiring technical knowledge
- Ability to fine-tune all parameters through the interface

## [1.0.0] - 2025-07-07

### Added
- Initial release with production-ready features
- Universal compatibility with any Home Assistant climate entity
- Intelligent learning system with lightweight ML
- Dynamic offset compensation with safety limits
- Multiple operating modes (Normal, Away, Sleep, Boost)
- UI-based configuration with entity selectors
- Learning on/off switch with status attributes
- Persistent learning data across restarts
- Comprehensive debug logging system
- HACS-compatible repository structure

### Fixed
- Learning data collection with feedback mechanism
- Corrected inverted offset calculation logic
- Home Assistant 2024.1+ API compatibility
- Entity attribute access with defensive programming
- Startup timing robustness with entity availability checking
- HVAC mode UI state update responsiveness
- Temperature setpoint control visibility

### Changed
- Documentation reorganized for better accessibility
- Removed device-specific references for universal use
- Enhanced configuration with UI setup

### Security
- Input validation for all user-configurable parameters
- Safe temperature limits to prevent extreme settings
- Atomic file operations for data persistence

[Unreleased]: https://github.com/VectorBarks/smart-climate/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/VectorBarks/smart-climate/compare/v1.1.0...v1.2.0
[1.2.0-beta5]: https://github.com/VectorBarks/smart-climate/compare/v1.2.0-beta4...v1.2.0-beta5
[1.2.0-beta4]: https://github.com/VectorBarks/smart-climate/compare/v1.2.0-beta3...v1.2.0-beta4
[1.2.0-beta3]: https://github.com/VectorBarks/smart-climate/compare/v1.2.0-beta1...v1.2.0-beta3
[1.2.0-beta1]: https://github.com/VectorBarks/smart-climate/compare/v1.1.1-beta2...v1.2.0-beta1
[1.1.1-beta2]: https://github.com/VectorBarks/smart-climate/compare/v1.1.1-beta1...v1.1.1-beta2
[1.1.1-beta1]: https://github.com/VectorBarks/smart-climate/compare/v1.1.0...v1.1.1-beta1
[1.1.0]: https://github.com/VectorBarks/smart-climate/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/VectorBarks/smart-climate/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/VectorBarks/smart-climate/releases/tag/v1.0.0
