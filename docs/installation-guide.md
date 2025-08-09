# Installation Guide

This guide covers all installation methods for Smart Climate Control and includes migration information for existing users.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [HACS Installation (Recommended)](#hacs-installation-recommended)
3. [Manual Installation](#manual-installation)
4. [Post-Installation Setup](#post-installation-setup)
5. [Dashboard and Visualization](#dashboard-and-visualization)
6. [Updating the Integration](#updating-the-integration)
7. [Migration from Previous Versions](#migration-from-previous-versions)
8. [Troubleshooting Installation](#troubleshooting-installation)

## Prerequisites

Before installing Smart Climate Control, ensure you have:

- **Home Assistant 2024.1 or newer**
- **Python 3.11 or newer**
- **A climate device integrated with Home Assistant** (AC unit, heat pump, etc.)
- **At least one temperature sensor** in the same room as your climate device
- **Optional**: Outdoor temperature sensor, power consumption sensor, weather integration

## HACS Installation (Recommended)

HACS provides the easiest installation and update experience with automatic notifications for new releases.

### Step 1: Add Custom Repository

1. Open HACS in your Home Assistant interface
2. Navigate to "Integrations" section
3. Click the three dots menu in the top right corner
4. Select "Custom repositories"
5. Add the following details:
   - **Repository URL**: `https://github.com/VectorBarks/smart-climate`
   - **Category**: Integration
6. Click "Add"

### Step 2: Install the Integration

1. In HACS Integrations, click the "+ Explore & Download Repositories" button
2. Search for "Smart Climate Control"
3. Click on the integration card
4. Click "Download" 
5. Select the latest version (v1.4.1-beta5 or newer)
6. Click "Download" again to confirm
7. **Restart Home Assistant** (required for custom integrations)

### Step 3: Configure the Integration

1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "Smart Climate Control"
4. Follow the comprehensive configuration wizard:

#### Required Settings
- **Climate Entity**: Your existing AC/climate device
- **Room Temperature Sensor**: Trusted sensor in the same room

#### Optional Sensors (Recommended)
- **Outdoor Temperature Sensor**: Physical sensor or weather integration
- **Power Consumption Sensor**: Monitoring your climate device's power usage

#### Advanced Settings (All Available in UI)
The configuration wizard now includes ALL settings previously requiring YAML:
- Basic settings (temperature limits, update intervals, ML features)
- Mode configuration (away, sleep, boost settings) 
- Advanced options (learning parameters, gradual adjustment rates)
- Power thresholds (when power sensor configured)
- Thermal efficiency options
- Weather integration settings

All configuration is now done through the intuitive UI - **no YAML editing required!**

## Manual Installation

For users who prefer manual installation or don't use HACS.

### Step 1: Download the Integration

1. Download the latest release from the [GitHub releases page](https://github.com/VectorBarks/smart-climate/releases)
2. Extract the downloaded archive to a temporary location

### Step 2: Copy Files

1. Navigate to your Home Assistant configuration directory:
   - **Home Assistant OS**: `/config/`
   - **Docker**: Your mapped config volume
   - **Core installation**: `~/.homeassistant/`

2. Create the `custom_components` directory if it doesn't exist:
   ```bash
   mkdir -p custom_components
   ```

3. Copy the `smart_climate` folder from the extracted archive:
   ```bash
   cp -r /path/to/extracted/custom_components/smart_climate custom_components/
   ```

4. Verify your directory structure:
   ```
   config/
   ├── configuration.yaml
   ├── custom_components/
   │   └── smart_climate/
   │       ├── __init__.py
   │       ├── climate.py
   │       ├── manifest.json
   │       └── ... (other files)
   ```

### Step 3: Restart Home Assistant

Restart Home Assistant to recognize the new integration:
- **Home Assistant OS/Supervised**: Settings → System → Restart
- **Docker**: `docker restart homeassistant`
- **Core**: `systemctl restart home-assistant@homeassistant`

### Step 4: Configure the Integration

Follow the same configuration steps as HACS installation (Step 3 above). The comprehensive UI configuration wizard provides access to all features.

## Post-Installation Setup

### Verify Installation

1. Check that the integration appears in Settings → Devices & Services
2. Look for any error messages in Home Assistant logs:
   - Settings → System → Logs
   - Search for "smart_climate"
3. Verify your new Smart Climate entity appears in your entities list

### Enable Optional Debug Logging

To monitor integration behavior during setup:

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.smart_climate: debug
```

## Dashboard and Visualization

Smart Climate Control provides comprehensive monitoring capabilities through automatic sensor creation and dashboard generation.

### Automatic Dashboard Sensors

Each configured Smart Climate device automatically creates 5 specialized sensors:
- **Current Offset**: Real-time temperature compensation being applied
- **Learning Progress**: Completion percentage of the learning system
- **Current Accuracy**: Prediction accuracy over time
- **Calibration Status**: Current system phase (calibrating/learning/complete)
- **Hysteresis State**: AC behavior state (cooling/idle/learning patterns)

### One-Click Dashboard Generation

Create a complete visualization dashboard instantly:

1. Go to Developer Tools → Services
2. Search for "Smart Climate: Generate Dashboard"
3. Select your Smart Climate entity
4. Click "Call Service"
5. Copy the YAML configuration from the notification
6. Create a new dashboard using the generated configuration

The generated dashboard includes:
- **Real-time Status Cards**: Current temperature, offset, and mode
- **Learning Progress Gauges**: Visual feedback on system optimization
- **Historical Charts**: Temperature trends and prediction accuracy
- **Performance Metrics**: Energy efficiency and system health indicators

For detailed dashboard setup instructions, see the full [Configuration Guide](configuration-guide.md).

## Updating the Integration

### HACS Updates

1. Open HACS → Integrations
2. Look for available updates (indicated by update badge)
3. Click on Smart Climate Control
4. Click "Update" and select the new version
5. Restart Home Assistant

### Manual Updates

1. Download the latest release
2. **Back up your current installation** (optional but recommended)
3. Remove the old version:
   ```bash
   rm -rf custom_components/smart_climate
   ```
4. Copy the new version following the installation steps above
5. Restart Home Assistant

**Note**: Your configuration and learning data are preserved during updates.

## Migration from Previous Versions

Smart Climate Control includes automatic migration for data and configuration.

### What's New in v1.4.1-beta5

Smart Climate Control v1.4.1-beta5 includes important updates and improvements:

#### Removed Features
- **Seasonal Migration Code**: Obsolete migration logic has been removed as all users should now be on modern schema versions
- **Legacy Warnings**: Cleaned up async_load deprecation warnings

#### Improved Features
- **Shadow Mode Behavior**: Enhanced thermal efficiency shadow mode operation
- **Configuration Validation**: Better error handling during setup
- **Learning System**: Continued refinements to ML offset calculations

### Migration Process

The integration handles migration automatically:

1. **Data Preservation**: All learning data and historical patterns are preserved
2. **Configuration Upgrade**: Settings are automatically migrated to new format
3. **Backward Compatibility**: New features are disabled by default for existing installations
4. **Schema Evolution**: Storage format upgrades happen transparently

### Post-Migration Verification

After updating to v1.4.1-beta5:

1. **Check Entity Status**: Verify your Smart Climate entity is working normally
2. **Review Learning Data**: Confirm learning progress and accuracy metrics are preserved  
3. **Validate Configuration**: Ensure all settings are still configured as expected
4. **Monitor Logs**: Watch for any migration-related messages during first startup

### New Dashboard Sensors (v1.2.0+)

If upgrading from pre-v1.2.0, you'll gain access to automatic dashboard sensors:
- These sensors appear automatically after the update
- No configuration changes required
- Use the dashboard generation service to create visualizations

### Breaking Changes

**v1.4.1-beta5**: No breaking changes - fully backward compatible

**v1.3.0**: No breaking changes - new features are optional

**v1.2.0**: No breaking changes - dashboard sensors are additions

### Rollback Procedure

If you need to revert to a previous version:

1. **HACS Users**: Select previous version in HACS download dialog
2. **Manual Users**: Download and install previous release
3. **Data Safety**: Your learning data remains compatible with older versions
4. **Feature Loss**: New features will be unavailable but basic operation continues

## Troubleshooting Installation

### Integration Not Found After Installation

1. **Verify File Placement**: Ensure files are in correct `custom_components/smart_climate/` directory
2. **Check Permissions**: Verify Home Assistant can read all files
3. **Clear Browser Cache**: Force refresh your browser
4. **Review Logs**: Check for Python import errors in system logs

### Configuration Wizard Errors

1. **Entity Validation**: Ensure climate entity and sensors exist and are working
2. **Entity ID Format**: Verify entity IDs are correct and case-sensitive
3. **Sensor Data Types**: Check that temperature sensors provide numeric values
4. **Network Connectivity**: Ensure sensors are online and updating

### Sensor Data Issues

If sensors show "unknown" or don't update:
1. **Placement Verification**: Check sensor placement per recommendations
2. **Update Frequency**: Ensure sensors update at least every 5 minutes
3. **Battery Status**: Check battery levels for wireless sensors
4. **Integration Status**: Verify sensor integrations are working properly

### Performance Issues

If the integration seems slow or unresponsive:
1. **Resource Usage**: Check system resources aren't constrained
2. **Update Intervals**: Consider increasing update intervals for slower systems
3. **Learning Data**: Large learning datasets may need cleanup
4. **Debug Logging**: Disable debug logging after troubleshooting

### Version Compatibility

- **Home Assistant**: Requires 2024.1+ (check Settings → System → General)
- **Python**: Requires 3.11+ (usually automatic with Home Assistant updates)
- **Dependencies**: All required packages are automatically installed

## Getting Help

If you encounter issues not covered here:

1. **Check Logs**: Enable debug logging and review error messages
2. **Search Issues**: Look for similar problems in [GitHub Issues](https://github.com/VectorBarks/smart-climate/issues)
3. **Community Forum**: Ask questions in the [Home Assistant Community](https://community.home-assistant.io)
4. **File Bug Reports**: Create detailed issue reports with logs and configuration

## Next Steps

After successful installation:

1. **Learn Basic Usage**: Read the [User Guide](user-guide.md) for daily operation
2. **Optimize Configuration**: Explore the [Configuration Guide](configuration-guide.md) for advanced settings
3. **Understand Sensors**: Review [Sensor Reference](sensor-reference.md) for monitoring capabilities
4. **Monitor Learning**: Watch your system learn and improve over the first few weeks

---

*Installation complete! Your Smart Climate Control system is ready to learn and optimize your comfort.*