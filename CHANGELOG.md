# Changelog

All notable changes to Smart Climate Control will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/VectorBarks/smart-climate/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/VectorBarks/smart-climate/releases/tag/v1.0.0
