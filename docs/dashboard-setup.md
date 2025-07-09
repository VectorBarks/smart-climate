# Smart Climate Dashboard Setup Guide

This guide will help you set up the Smart Climate visualization dashboard to monitor and analyze your climate control system's performance.

## Prerequisites

Before setting up the dashboard, ensure you have:

1. **Smart Climate Integration Installed**: The Smart Climate Control integration must be installed and configured with at least one climate entity
2. **Home Assistant 2024.1+**: Required for blueprint compatibility
3. **Lovelace Dashboard Access**: Ability to edit dashboards in your Home Assistant instance
4. **Entities Created**: Your Smart Climate entities should be available:
   - Smart Climate entity (e.g., `climate.living_room_smart_ac`)
   - Learning switch (e.g., `switch.living_room_smart_ac_learning`)

### Optional but Recommended

For the best visualization experience, consider installing these custom cards through HACS:
- **ApexCharts Card**: For advanced time-series charts showing offset history and accuracy trends
- **Mushroom Cards**: For a modern, clean climate control interface
- **Button Card**: For customized status displays

The dashboard will work without these cards using Home Assistant's built-in cards, but the experience will be enhanced with them installed.

## Installing the Dashboard Blueprint

### Method 1: Blueprint Import (Recommended)

1. **Navigate to Dashboard Settings**
   - Go to Settings → Dashboards
   - Click the three dots menu on any dashboard
   - Select "Edit Dashboard"

2. **Import the Blueprint**
   - Click the three dots menu in the top right
   - Select "Take control" if prompted
   - Choose "Import Blueprint"
   - Select "Smart Climate Dashboard" from the list

3. **Configure the Blueprint**
   - **Climate Entity**: Select your Smart Climate entity from the dropdown
   - **Learning Switch**: Select the corresponding learning switch
   - Click "Import"

![Dashboard Blueprint Import Dialog](images/dashboard-blueprint-import.png)
<!-- TODO: Add actual screenshot when available -->

4. **Customize Location**
   - Choose where to add the dashboard:
     - As a new view in an existing dashboard
     - As a standalone dashboard
   - Name your view (e.g., "Climate Control")

### Method 2: Manual YAML Import

If blueprint import isn't available:

1. Access the blueprint YAML file at:
   ```
   custom_components/smart_climate/blueprints/dashboard/smart_climate_dashboard.yaml
   ```

2. Copy the dashboard configuration section

3. In your dashboard:
   - Edit Dashboard → Raw Configuration Editor
   - Paste the configuration
   - Replace placeholder entity IDs with your actual entities

## Understanding the Dashboard Sections

The Smart Climate dashboard is organized into four main sections:

### 1. Current Status Section

![Current Status Section](images/dashboard-current-status.png)
<!-- TODO: Add actual screenshot when available -->

This section provides real-time information about your climate control:

- **Climate Control Card**: Shows current temperature, target temperature, and operating mode
- **Current Offset Gauge**: Displays the active temperature offset (-5°C to +5°C)
- **Learning Accuracy**: Shows how accurately the system is predicting needed offsets (0-100%)
- **Confidence Level**: Indicates the system's confidence in its current predictions

### 2. Learning Progress Section

![Learning Progress Charts](images/dashboard-learning-progress.png)
<!-- TODO: Add actual screenshot when available -->

Track your system's learning progress over time:

- **Accuracy Trend Chart**: Line graph showing prediction accuracy over the last 7 days
- **Offset History**: Area chart displaying how offsets have changed over time
- **Sample Collection Rate**: Bar chart showing when the system collected learning data

Key indicators to watch:
- Accuracy should increase over time as the system learns
- Offset patterns should stabilize after initial learning
- Sample collection should be regular during active use

### 3. Calibration & Hysteresis Section

![Calibration Status Display](images/dashboard-calibration.png)
<!-- TODO: Add actual screenshot when available -->

Monitor advanced learning features:

- **Calibration Status**: Shows if the system is in calibration phase
  - "Calibrating" - Currently collecting initial samples
  - "Calibration Complete" - Ready for normal operation
  - Samples collected vs. required for calibration

- **Hysteresis Detection**: (Requires power sensor)
  - Current power consumption
  - Detected start/stop thresholds
  - AC operating state visualization

- **Power vs Temperature Graph**: Historical correlation between power usage and temperature changes

### 4. Control Section

![Control Panel](images/dashboard-controls.png)
<!-- TODO: Add actual screenshot when available -->

Quick access to system controls:

- **Mode Selection**: Switch between Normal, Away, Sleep, and Boost modes
- **Learning Toggle**: Enable/disable the learning system
- **Manual Override**: Set a temporary manual offset
- **Reset Training Data**: Clear all learned data and start fresh

## Customizing the Dashboard

### Modifying Card Layouts

After importing, you can customize the dashboard:

1. **Rearrange Cards**: Drag and drop to reorder sections
2. **Resize Cards**: Adjust width for different screen sizes
3. **Add Custom Cards**: Include additional sensors or controls

### Adjusting for Mobile

The dashboard is responsive but you can optimize for mobile:

```yaml
# Example: Conditional card for mobile
type: conditional
conditions:
  - condition: screen
    media_query: "(max-width: 600px)"
card:
  type: vertical-stack
  cards:
    # Simplified mobile layout
```

### Using Core Cards Only

If you don't have custom cards installed, the dashboard automatically falls back to core cards:

- ApexCharts → History Graph
- Mushroom Climate → Thermostat Card
- Button Card → Entity Button

### Adding Additional Sensors

You can extend the dashboard with your own sensors:

```yaml
type: entities
entities:
  - entity: sensor.living_room_humidity
  - entity: sensor.outdoor_temperature
  - entity: sensor.energy_consumption
```

## Template Sensors Created

The dashboard blueprint creates several template sensors for data visualization. See the [Dashboard Sensors Reference](dashboard-sensors.md) for detailed information about each sensor.

Key template sensors:
- `sensor.[name]_offset_history` - Recent offset values
- `sensor.[name]_learning_progress` - Learning completion percentage
- `sensor.[name]_accuracy_trend` - 7-day accuracy average
- `sensor.[name]_calibration_status` - Current calibration state

## Performance Considerations

### Update Frequency

- Template sensors update when source entities change
- History data is pulled from Home Assistant's recorder
- Default recorder retention is 10 days - extend if needed:

```yaml
# configuration.yaml
recorder:
  purge_keep_days: 30
  include:
    entities:
      - climate.living_room_smart_ac
      - switch.living_room_smart_ac_learning
```

### Database Impact

The dashboard queries historical data which may impact performance on:
- Raspberry Pi or low-power devices
- Systems with SD card storage
- Databases with millions of state changes

Optimize by:
- Using MariaDB/PostgreSQL instead of SQLite
- Limiting history graph ranges
- Excluding unused entities from recorder

## Troubleshooting

### Dashboard Not Loading

1. **Check Entity Availability**
   - Ensure all referenced entities exist
   - Verify entities are not "unavailable"

2. **Validate YAML**
   - Use Developer Tools → YAML to check configuration
   - Look for indentation errors

3. **Clear Browser Cache**
   - Force refresh: Ctrl+F5 (Windows/Linux) or Cmd+Shift+R (Mac)
   - Try incognito/private browsing mode

### Missing Data in Charts

1. **Verify Recorder Configuration**
   - Ensure entities are included in recorder
   - Check retention period is sufficient

2. **Check Template Sensors**
   - Go to Developer Tools → Template
   - Test template expressions manually

3. **Wait for Data Collection**
   - New installations need time to collect history
   - Learning system requires active use to generate data

### Cards Show "Entity Not Available"

1. **Entity Name Mismatch**
   - Verify exact entity IDs in Developer Tools → States
   - Check for typos or incorrect prefixes

2. **Integration Not Loaded**
   - Ensure Smart Climate integration is running
   - Check logs for integration errors

3. **Template Sensor Issues**
   - Template sensors may take a minute to initialize
   - Check template sensor configuration in States

### Performance Issues

1. **Reduce History Range**
   ```yaml
   # Limit charts to 24 hours instead of 7 days
   hours_to_show: 24
   ```

2. **Decrease Update Frequency**
   ```yaml
   # Update less frequently
   scan_interval: 300  # 5 minutes
   ```

3. **Use Fewer Cards**
   - Remove non-essential visualizations
   - Combine multiple sensors into single cards

## Dashboard Examples

### Minimal Setup

For a simple, performance-friendly dashboard:

```yaml
views:
  - title: Climate
    cards:
      - type: thermostat
        entity: climate.living_room_smart_ac
      - type: entities
        entities:
          - switch.living_room_smart_ac_learning
          - sensor.living_room_offset_history
```

### Advanced Setup

For comprehensive monitoring with custom cards:

```yaml
views:
  - title: Climate Control
    cards:
      - type: custom:mushroom-climate-card
        entity: climate.living_room_smart_ac
        show_temperature_control: true
      - type: custom:apexcharts-card
        # ... detailed configuration
```

## Getting Help

If you encounter issues:

1. Check the [Smart Climate Documentation](../README.md)
2. Review [Home Assistant Dashboard Documentation](https://www.home-assistant.io/dashboards/)
3. Search existing [GitHub Issues](https://github.com/VectorBarks/smart-climate/issues)
4. Create a new issue with:
   - Your dashboard configuration
   - Error messages from logs
   - Screenshots of the problem
   - Home Assistant version

## Next Steps

- Review the [Dashboard Sensors Reference](dashboard-sensors.md) to understand each visualization
- Explore the [Usage Guide](usage.md) for tips on interpreting dashboard data
- Check the [Learning System Guide](learning-system.md) to understand what the visualizations mean