# Changelog

All notable changes to Smart Climate Control will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/VectorBarks/smart-climate/compare/v1.1.1-beta1...HEAD
[1.1.1-beta1]: https://github.com/VectorBarks/smart-climate/compare/v1.1.0...v1.1.1-beta1
[1.1.0]: https://github.com/VectorBarks/smart-climate/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/VectorBarks/smart-climate/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/VectorBarks/smart-climate/releases/tag/v1.0.0
