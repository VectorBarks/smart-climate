# Smart Climate Control v1.0.1 Release Notes

## Enhanced User Experience

This release focuses on making Smart Climate Control more user-friendly and accessible to all Home Assistant users by providing comprehensive UI configuration options.

### What's New

#### 🎛️ Complete UI Configuration
- **All settings now available through the UI** - No more YAML editing required!
- Configure every aspect of the integration through the Home Assistant interface
- Options flow allows changing settings after initial setup

#### 🔧 New Configuration Options
- **Away Mode Temperature** (10-35°C) - Set a fixed temperature for when you're away
- **Sleep Mode Offset** (-5 to +5°C) - Adjust for quieter nighttime operation
- **Boost Mode Offset** (-10 to 0°C) - Aggressive cooling when you need it fast
- **Gradual Adjustment Rate** (0.1-2.0°C) - Control how fast temperatures change
- **Learning Feedback Delay** (10-300s) - Fine-tune learning data collection
- **Enable Learning Toggle** - Separate control from ML features

#### 🔄 Reset Training Data Button
- New button entity in device configuration section
- Clear all learning data with one click
- Automatic backup created before deletion
- Perfect for starting fresh when your AC usage patterns change

#### ⚡ Configurable Power Thresholds
- Customize power detection for your specific AC unit
- **Idle Threshold** - Define when your AC is off (default 50W)
- **Min Threshold** - AC running at minimum (default 100W)
- **Max Threshold** - AC at high capacity (default 250W)
- Settings only appear when using a power sensor
- Automatic validation ensures proper threshold order

### Improvements
- Better validation for all configuration options
- Enhanced documentation with UI-first approach
- Improved onboarding experience for new users
- More accurate AC state detection with custom thresholds

### Upgrading
Simply update through HACS or manually replace the files. Your existing configuration will continue to work, and you can now modify all settings through the UI.

### Next Steps
After updating, visit the integration's options to explore all the new configuration possibilities. Check out the updated documentation for detailed explanations of each setting.

---

For full details, see the [CHANGELOG](https://github.com/VectorBarks/smart-climate/blob/main/CHANGELOG.md).