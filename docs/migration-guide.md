# Migration Guide - Dashboard Feature

## Overview

Smart Climate v1.2.0 introduces a new visualization dashboard feature that provides real-time monitoring of your climate control system's performance. This guide explains how to migrate to this new version and set up the dashboard.

## What's New in v1.2.0

### Automatic Dashboard Sensors

The integration now automatically creates five new sensor entities:
- `sensor.{entity}_offset_current` - Current temperature offset being applied
- `sensor.{entity}_learning_progress` - Learning system completion percentage
- `sensor.{entity}_accuracy_current` - Current prediction accuracy
- `sensor.{entity}_calibration_status` - Calibration phase status
- `sensor.{entity}_hysteresis_state` - AC behavior state (idle/cooling/heating)

These sensors are created automatically when you install or restart with v1.2.0 - no configuration needed!

### Dashboard Generation Service

A new service `smart_climate.generate_dashboard` creates a complete dashboard configuration customized for your specific Smart Climate entity.

## Migration Steps

### For Existing Users

1. **Update to v1.2.0**
   - If using HACS: Update Smart Climate Control
   - If manual: Replace the `custom_components/smart_climate` folder
   
2. **Restart Home Assistant**
   - This will automatically create the new dashboard sensors
   
3. **Verify New Sensors**
   - Go to Developer Tools → States
   - Search for your climate entity name
   - You should see 5 new sensor entities

4. **Generate Your Dashboard**
   - Go to Developer Tools → Services
   - Search for "Smart Climate: Generate Dashboard"
   - Select your Smart Climate entity
   - Click "Call Service"
   - Copy the YAML from the notification
   - Create a new dashboard following the instructions

### For New Users

Simply install v1.2.0 and the dashboard sensors will be created automatically during setup.

## Important Notes

### No Manual Configuration Required

Unlike some integrations that require manual template sensor configuration, Smart Climate's dashboard sensors are created automatically. You don't need to:
- Edit configuration.yaml
- Create template sensors manually
- Configure sensor platforms

### Dashboard Templates vs Blueprints

Home Assistant doesn't support dashboard blueprints (only automation blueprints exist). Instead, we provide:
- A dashboard template that's customized for your entity
- A service that generates the YAML with your entity IDs already filled in
- Clear instructions for creating the dashboard

### Compatibility

- The dashboard uses only core Home Assistant cards
- Works with all themes
- Responsive design for mobile and desktop
- Optional: Enhanced visualization with custom cards (apexcharts-card, mushroom-cards)

## Troubleshooting

### Sensors Not Appearing

If the dashboard sensors don't appear after updating:
1. Check the logs for any errors
2. Ensure you've restarted Home Assistant after updating
3. Verify your Smart Climate entity is working properly
4. Try reloading the integration from Settings → Devices & Services

### Service Not Found

If the generate_dashboard service isn't available:
1. Verify you're on v1.2.0 or later
2. Check that the integration loaded successfully
3. Look for errors in the logs
4. Try restarting Home Assistant again

### Dashboard Not Working

If the generated dashboard has issues:
1. Ensure you copied the entire YAML content
2. Check that your entity IDs match
3. Verify the sensors have data (not "unknown")
4. Try the dashboard after the system has been running for a few minutes

## Rolling Back

If you need to revert to v1.1.x:
1. The new sensors will be removed automatically
2. Your existing climate entity will continue working normally
3. No data loss will occur
4. Learning data is preserved