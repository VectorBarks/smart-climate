# Installation Guide

This guide covers all installation methods for Smart Climate Control.

## Prerequisites

- Home Assistant 2024.1 or newer
- Python 3.11 or newer
- A climate device integrated with Home Assistant
- At least one temperature sensor in the same room as your climate device

## Installation Methods

### Option 1: HACS (Home Assistant Community Store) - Recommended

HACS provides the easiest installation and update experience.

#### Step 1: Add Custom Repository

1. Open HACS in your Home Assistant interface
2. Navigate to "Integrations" section
3. Click the three dots menu in the top right
4. Select "Custom repositories"
5. Add the following:
   - **Repository URL**: `https://github.com/VectorBarks/smart-climate`
   - **Category**: Integration
6. Click "Add"

#### Step 2: Install the Integration

1. In HACS Integrations, click the "+ Explore & Download Repositories" button
2. Search for "Smart Climate Control"
3. Click on the integration
4. Click "Download" 
5. Select the latest version
6. Click "Download" again to confirm
7. **Restart Home Assistant** (required for custom integrations)

#### Step 3: Configure the Integration

1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "Smart Climate Control"
4. Follow the comprehensive configuration wizard which now includes:
   - Entity selection (climate device and sensors)
   - Basic settings (temperature limits, offsets, intervals)
   - Mode configuration (away, sleep, boost settings)
   - Advanced options (learning parameters, adjustment rates)
   
All settings are now available through the UI - no YAML editing required!

### Option 2: Manual Installation

For users who prefer manual installation or don't use HACS.

#### Step 1: Download the Integration

1. Download the latest release from the [GitHub releases page](https://github.com/VectorBarks/smart-climate/releases)
2. Extract the downloaded archive

#### Step 2: Copy Files

1. Navigate to your Home Assistant configuration directory
   - Default location: `/config/` in Home Assistant OS
   - Docker: Your mapped config volume
   - Core installation: `~/.homeassistant/`

2. Create the `custom_components` directory if it doesn't exist:
   ```bash
   mkdir -p custom_components
   ```

3. Copy the `smart_climate` folder from the extracted archive:
   ```bash
   cp -r /path/to/extracted/custom_components/smart_climate custom_components/
   ```

4. Your directory structure should look like:
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

#### Step 3: Restart Home Assistant

Restart Home Assistant for the integration to be recognized:
- **Home Assistant OS/Supervised**: Settings → System → Restart
- **Docker**: `docker restart homeassistant`
- **Core**: `systemctl restart home-assistant@homeassistant`

#### Step 4: Configure the Integration

Follow the same configuration steps as HACS installation (Step 3 above). The comprehensive UI configuration makes setup quick and easy without any YAML editing.

## Post-Installation Setup

### Verify Installation

1. Check that the integration appears in Settings → Devices & Services
2. Look for any error messages in the Home Assistant logs:
   - Settings → System → Logs
   - Search for "smart_climate"

### Initial Configuration

The UI configuration wizard provides access to all settings during initial setup. See the [Configuration Guide](configuration.md) for detailed explanations of each setting.

### Enable Debug Logging (Optional)

To monitor the integration's operation during initial setup:

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.smart_climate: debug
```

## Updating the Integration

### HACS Updates

1. Open HACS → Integrations
2. Look for available updates (indicated by an update badge)
3. Click on Smart Climate Control
4. Click "Update" and select the new version
5. Restart Home Assistant

### Manual Updates

1. Download the latest release
2. Remove the old version:
   ```bash
   rm -rf custom_components/smart_climate
   ```
3. Copy the new version as in initial installation
4. Restart Home Assistant

## Troubleshooting Installation

### Integration Not Found

If the integration doesn't appear after installation:

1. Verify file placement - check that all files are in `custom_components/smart_climate/`
2. Check file permissions - ensure Home Assistant can read the files
3. Clear browser cache and reload
4. Check logs for import errors

### Configuration Errors

If you encounter errors during configuration:

1. Ensure your climate entity and sensors are working properly
2. Verify entity IDs are correct (case-sensitive)
3. Check that sensors provide numeric temperature values
4. See [Troubleshooting Guide](troubleshooting.md) for more help

### Version Compatibility

- **Home Assistant**: Requires 2024.1 or newer
- **Python**: Requires 3.11 or newer
- **Breaking Changes**: Check release notes when updating

## Next Steps

- [Configure your Smart Climate device](configuration.md)
- [Learn about usage and features](usage.md)
- [Understand the learning system](learning-system.md)