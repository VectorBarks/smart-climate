# Dashboard Setup Guide

This guide explains how to set up the Smart Climate visualization dashboard to monitor your learning progress, offset history, and system performance.

## Overview

Smart Climate Control provides a comprehensive dashboard solution that requires zero manual configuration:

1. **Automatic Sensor Creation**: When you add a Smart Climate device, dashboard sensors are automatically created
2. **Dashboard Generation Service**: A single service call generates a complete, customized dashboard
3. **Ready-to-Use**: The generated dashboard works immediately with responsive layouts for desktop and mobile

## Dashboard Sensors (Automatically Created)

When you configure a Smart Climate device, the integration automatically creates five specialized sensors for dashboard visualization:

### Current Offset Sensor
- **Entity ID**: `sensor.{your_climate_name}_offset_current`
- **Purpose**: Shows the current temperature offset being applied
- **Unit**: °C
- **Updates**: Real-time as offsets change
- **Example**: `sensor.living_room_smart_ac_offset_current`

### Learning Progress Sensor
- **Entity ID**: `sensor.{your_climate_name}_learning_progress`
- **Purpose**: Displays learning completion percentage (0-100%)
- **Unit**: %
- **Updates**: When new learning samples are collected
- **Example**: `sensor.living_room_smart_ac_learning_progress`

### Accuracy Sensor
- **Entity ID**: `sensor.{your_climate_name}_accuracy_current`
- **Purpose**: Shows current prediction accuracy
- **Unit**: %
- **Updates**: After each learning feedback cycle
- **Example**: `sensor.living_room_smart_ac_accuracy_current`

### Calibration Status Sensor
- **Entity ID**: `sensor.{your_climate_name}_calibration_status`
- **Purpose**: Indicates calibration phase status
- **States**: "calibrating", "learning", "complete"
- **Icon**: Progress check icon
- **Example**: `sensor.living_room_smart_ac_calibration_status`

### Hysteresis State Sensor
- **Entity ID**: `sensor.{your_climate_name}_hysteresis_state`
- **Purpose**: Shows AC behavior learning state
- **States**: "idle", "cooling", "learning_pattern"
- **Icon**: Sine wave icon
- **Example**: `sensor.living_room_smart_ac_hysteresis_state`

## Generating Your Dashboard

### Step 1: Open Developer Tools

1. Navigate to **Developer Tools** in Home Assistant
2. Click on the **Services** tab
3. Search for "Smart Climate" in the service dropdown

### Step 2: Call the Dashboard Generation Service

1. Select the service: `smart_climate.generate_dashboard`
2. Choose your Smart Climate entity from the entity picker
3. Click **Call Service**

Example service call:
```yaml
service: smart_climate.generate_dashboard
data:
  climate_entity_id: climate.living_room_smart_ac
```

### Step 3: Copy the Generated Dashboard

1. A **persistent notification** will appear with your complete dashboard YAML
2. Click on the notification to view the full dashboard code
3. **Copy all the YAML code** from the notification

**Important**: The generated dashboard automatically replaces placeholder values with your actual entity IDs:
- `REPLACE_ME_ROOM_SENSOR` → Your configured room temperature sensor
- `REPLACE_ME_OUTDOOR_SENSOR` → Your configured outdoor temperature sensor (if available)  
- `REPLACE_ME_POWER_SENSOR` → Your configured power sensor (if available)
- All Smart Climate entity references → Your actual Smart Climate entity IDs

**Placeholder System**: The dashboard template uses placeholder values that are intelligently replaced during generation. This ensures proper entity ID replacement without manual YAML editing, providing zero-configuration dashboard setup.

### Step 4: Create Your Dashboard

1. Navigate to **Settings → Dashboards**
2. Click **+ Add Dashboard**
3. Choose **"Start with an empty dashboard"**
4. Give it a name like "Smart Climate Monitor"
5. Click **Create**

### Step 5: Paste and Save

1. Click the **three dots menu** (⋮) in the top right
2. Select **Edit Dashboard**
3. Click the **three dots menu** again
4. Select **Raw Configuration Editor**
5. **Delete all existing content**
6. **Paste** your copied dashboard YAML
7. Click **Save**

Your dashboard is now ready to use!

## Dashboard Features

### Overview Section

The top section provides at-a-glance information:
- **Climate Control Card**: Direct control of your Smart Climate device
- **Current Offset Gauge**: Visual representation of active offset (-5°C to +5°C)
- **Learning Progress Gauge**: Percentage complete (0-100%)
- **Accuracy Gauge**: Current prediction accuracy

### Learning Analytics

Interactive charts showing:
- **Multi-Layered Offset Analysis**: Reactive, predictive, and total offsets with component breakdowns
- **Weather Intelligence**: Active weather strategies and predictive adjustments timeline
- **Accuracy Trend**: How prediction accuracy improves over time
- **Temperature Correlation**: Relationship between room and AC temperatures

### v1.3.0+ Enhanced Intelligence Dashboard

The enhanced dashboard showcases the comprehensive multi-layered intelligent architecture introduced in v1.3.0:

#### Multi-Layered Intelligence Display
Advanced offset visualization showing the sophisticated decision-making process:
- **Reactive Offset**: Traditional ML-based learning offset from historical patterns
- **Predictive Offset**: Weather-forecast-based preemptive temperature adjustments 
- **Total Offset**: Combined intelligent offset for optimal precision control
- **Component Breakdown**: Real-time contribution percentages from each intelligence layer

#### Weather Intelligence Analytics
Comprehensive weather-based predictive system monitoring:
- **Active Strategy Display**: Current weather strategy (Heat Wave Pre-cooling, Clear Sky Optimization, etc.)
- **Strategy Timeline**: Upcoming weather predictions and planned system responses
- **Forecast Confidence**: Weather service reliability and prediction accuracy metrics
- **Adjustment History**: Timeline of weather-based offset decisions and their effectiveness

#### Adaptive Timing Intelligence
Advanced AC response optimization with learned behavioral patterns:
- **Learned Delays**: Adaptive feedback delays optimized for your specific AC unit
- **Temperature Stability Detection**: Real-time monitoring of thermal equilibrium states
- **Response Pattern Analysis**: Historical AC behavior and optimal timing recommendations
- **Equilibrium Metrics**: Temperature deviation thresholds and stability confidence levels

#### Seasonal Learning Analytics  
Context-aware adaptation with outdoor temperature correlation:
- **Outdoor Temperature Context**: Current conditions and seasonal pattern matching
- **Pattern Bucket Status**: Active temperature range bucket and available historical data
- **Seasonal Accuracy**: Performance metrics across different outdoor temperature ranges
- **Adaptation Progress**: Learning coverage across seasonal temperature variations

#### Enhanced Performance Metrics
Technical diagnostic information for advanced users:
- **Prediction Latency**: Real-time ML inference performance (<1ms target)
- **Learning Confidence**: Multi-factor confidence calculation with sample diversity
- **Pattern Recognition**: Time-series analysis and correlation strength indicators
- **System Health**: Overall integration status and component availability

### System Status

Detailed information cards displaying:
- **Calibration Status**: Current calibration phase
- **Hysteresis State**: AC behavior learning progress
- **Last Update Times**: When sensors last changed
- **Power State**: If power sensor is configured

### Mobile Optimization

The dashboard automatically adapts for mobile devices:
- Single column layout on phones
- Larger touch targets
- Simplified visualizations
- Swipe-friendly navigation

## Customizing Your Dashboard

### Adding Custom Cards

The generated dashboard uses standard Home Assistant cards. You can enhance it with custom cards:

**Recommended Custom Cards** (install via HACS):
- `custom:apexcharts-card` - For advanced charts
- `custom:mushroom-climate-card` - Enhanced climate control
- `custom:button-card` - Custom status displays
- `custom:mini-graph-card` - Compact history graphs

### Modifying Layouts

To adjust the layout:
1. Enter **Edit Mode** (three dots → Edit Dashboard)
2. **Drag and drop** cards to rearrange
3. **Edit individual cards** to change settings
4. Use **horizontal/vertical stacks** for grouping

### Adding Multiple Devices

If you have multiple Smart Climate devices:
1. Generate a dashboard for each device
2. Combine the cards into a single dashboard
3. Use **conditional cards** to show/hide based on active device
4. Create **tabs** for different rooms

Example multi-device setup:
```yaml
views:
  - title: Living Room
    cards: [living room cards]
  - title: Bedroom  
    cards: [bedroom cards]
  - title: Overview
    cards: [combined summary cards]
```

## Dashboard Examples

### Basic Setup (No Custom Cards)

The default generated dashboard works with core Home Assistant cards:
- Uses `gauge`, `entities`, and `history-graph` cards
- No additional installations required
- Full functionality out of the box

### Enhanced Setup (With Custom Cards)

For the best experience, install these HACS cards:
- **ApexCharts**: Beautiful, interactive charts
- **Mushroom**: Modern, clean UI elements
- **Button Card**: Customizable status displays

### Power Monitoring Dashboard

If you have a power sensor configured, additional cards show:
- Power consumption gauge
- State detection indicators
- Energy usage statistics
- Efficiency metrics

## Troubleshooting

### Dashboard Not Generating

**Problem**: Service call doesn't create notification
- **Solution**: Ensure you selected a valid Smart Climate entity
- **Check**: Look in the Home Assistant logs for errors

### Placeholder Values Not Replaced

**Problem**: Dashboard shows "REPLACE_ME_" values instead of actual entity IDs
- **Solution**: This indicates the dashboard generation service couldn't find your configured sensors
- **Check**: Verify your Smart Climate entity has room sensor, outdoor sensor (optional), and power sensor (optional) properly configured
- **Fix**: Reconfigure your Smart Climate entity with correct sensor entity IDs, then regenerate the dashboard

### Sensors Show "Unknown"

**Problem**: Dashboard sensors display unknown state
- **Solution**: Wait for the first update cycle (up to 3 minutes)
- **Check**: Verify the Smart Climate entity is functioning

### Cards Show Errors

**Problem**: Some cards display configuration errors
- **Solution**: The generated YAML references custom cards you haven't installed
- **Fix**: Either install the custom cards via HACS or use the fallback configuration

### Mobile Layout Issues

**Problem**: Dashboard doesn't look right on phone
- **Solution**: Ensure you're using the Home Assistant mobile app
- **Try**: Clear the app cache and reload

## Advanced Features

### Creating Automations from Dashboard Data

Use the dashboard sensors in automations:

```yaml
automation:
  - alias: "Notify when learning complete"
    trigger:
      - platform: numeric_state
        entity_id: sensor.living_room_smart_ac_learning_progress
        above: 95
    action:
      - service: notify.mobile_app
        data:
          message: "Smart Climate has completed initial learning!"
```

### Exporting Learning Data

Create sensors that track long-term statistics:

```yaml
sensor:
  - platform: statistics
    name: "AC Offset Average"
    entity_id: sensor.living_room_smart_ac_offset_current
    state_characteristic: mean
    max_age:
      days: 7
```

### Building Custom Views

Combine Smart Climate data with other sensors:
- Room occupancy
- Weather conditions  
- Energy prices
- Schedule data

## Best Practices

1. **Regular Monitoring**: Check the dashboard weekly during initial learning
2. **Screenshot Progress**: Document learning improvements
3. **Note Patterns**: Observe when offsets are highest
4. **Adjust Settings**: Use insights to optimize configuration
5. **Share Success**: Help others with similar setups

## Next Steps

- Learn about the [Learning System](learning-system.md) to understand the data
- Configure [Power Sensors](sensors.md#power-sensor-integration) for enhanced monitoring
- Set up [Automations](usage.md#automations) based on dashboard data
- Explore [Advanced Features](hysteresis-learning.md) like HysteresisLearner

## Getting Help

If you need assistance with dashboard setup:
1. Check the [Troubleshooting Guide](troubleshooting.md)
2. Review the [Home Assistant Logs](troubleshooting.md#checking-logs)
3. Ask in the [Home Assistant Community](https://community.home-assistant.io/)
4. Report issues on [GitHub](https://github.com/VectorBarks/smart-climate/issues)