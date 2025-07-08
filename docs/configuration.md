# Configuration Guide

This guide covers all configuration options for Smart Climate Control. The integration now provides a comprehensive UI configuration that includes ALL settings, eliminating the need for YAML configuration in most cases.

## Configuration Methods

Smart Climate Control supports two configuration methods:
- **UI Configuration** (recommended): Complete configuration through the Home Assistant interface with ALL settings available
- **YAML Configuration** (optional): For advanced users who prefer text-based configuration or need bulk setup

## UI Configuration (Complete Settings Available)

The UI configuration now provides access to ALL settings, making it the preferred configuration method for most users.

### Step 1: Add Integration

1. Navigate to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "Smart Climate Control"
4. Click on the integration to start configuration

### Step 2: Basic Configuration

The configuration wizard will guide you through the following settings:

#### Required Settings

**Climate Entity**
- Select your existing climate device from the dropdown
- This is the AC unit, heat pump, or other climate device you want to control
- Examples: `climate.living_room_ac`, `climate.bedroom_minisplit`

**Room Temperature Sensor**
- Choose a trusted temperature sensor in the same room
- This sensor should accurately reflect the room temperature
- Must be a sensor entity that provides numeric temperature values
- Examples: `sensor.living_room_temperature`, `sensor.bedroom_temp`

#### Optional Sensors

**Outdoor Temperature Sensor**
- Select an outdoor temperature sensor if available
- Improves offset predictions based on outdoor conditions
- Can be a weather integration sensor or physical outdoor sensor
- Example: `sensor.outdoor_temperature`, `sensor.weather_temperature`

**Power Consumption Sensor**
- Choose a power sensor monitoring your climate device
- Helps detect when the AC is actively cooling vs idle
- Enhances learning accuracy and state detection
- Example: `sensor.ac_power`, `sensor.smart_plug_power`

### Step 3: Comprehensive Settings Configuration

The UI now includes ALL configuration options:

<!-- Screenshot placeholder: UI configuration dialog showing all available settings -->
<!-- TODO: Add actual screenshots when available -->

#### Basic Settings

| Setting | Description | Default | Range |
|---------|-------------|---------|-------|
| **Maximum Offset** | Maximum temperature adjustment allowed | 5.0°C | 1.0 - 10.0°C |
| **Minimum Temperature** | Lowest allowed setpoint | 16°C | 10 - 25°C |
| **Maximum Temperature** | Highest allowed setpoint | 30°C | 20 - 35°C |
| **Update Interval** | How often to recalculate offsets | 180s | 60 - 600s |
| **ML Enabled** | Enable machine learning features | True | True/False |

#### Mode Settings

| Setting | Description | Default | Range |
|---------|-------------|---------|-------|
| **Away Temperature** | Fixed temperature for away mode | 26°C | 10 - 35°C |
| **Sleep Mode Offset** | Additional offset for quieter night operation | 1.0°C | -5.0 to +5.0°C |
| **Boost Mode Offset** | Extra cooling offset for rapid temperature reduction | -2.0°C | -10.0 to 0°C |

#### Advanced Settings

| Setting | Description | Default | Range |
|---------|-------------|---------|-------|
| **Gradual Adjustment Rate** | Temperature change per update cycle | 0.5°C | 0.1 - 2.0°C |
| **Learning Feedback Delay** | Time to wait before measuring AC response | 45s | 10 - 300s |
| **Enable Learning** | Start with learning system active | False | True/False |
| **Data Retention Days** | Days of historical data to keep | 60 | 30 - 365 |

#### Power Sensor Settings (Only visible when power sensor is configured)

| Setting | Description | Default | Range |
|---------|-------------|---------|-------|
| **Power Idle Threshold** | Power consumption below this = AC idle/off | 50W | 10 - 500W |
| **Power Min Threshold** | Power consumption below this = AC at minimum | 100W | 50 - 1000W |
| **Power Max Threshold** | Power consumption above this = AC at high/max | 250W | 100 - 5000W |

Note: These settings only appear in the UI when a power sensor is configured. The system validates that idle < min < max.

## Power Threshold Configuration Guide

Power thresholds are crucial for accurate AC state detection and optimal HysteresisLearner performance. This section helps you determine appropriate values for your specific AC unit.

### Understanding Power Thresholds

The Smart Climate Control uses power consumption patterns to understand your AC's behavior:

- **Idle Threshold**: Power consumption when the AC is in standby or off
- **Min Threshold**: Power consumption when the AC is running at minimum capacity
- **Max Threshold**: Power consumption when the AC is running at high or maximum capacity

These thresholds enable the system to:
1. Detect when your AC turns on/off
2. Understand cooling intensity levels
3. Learn temperature hysteresis patterns (with HysteresisLearner)
4. Improve offset predictions based on AC operating state

### How to Determine Your AC's Power Values

#### Method 1: Using Home Assistant History (Recommended)

1. Enable your power sensor and let it run for a few cooling cycles
2. Go to Developer Tools → Statistics
3. Select your power sensor
4. Observe the patterns:
   - **Lowest values** (when AC is off) = Idle power
   - **Consistent low values** (when AC just started) = Minimum power
   - **Highest sustained values** = Maximum power

#### Method 2: Real-time Observation

1. Turn off your AC completely and wait 1 minute
2. Check power sensor reading = **Idle power**
3. Set AC to cool with a high temperature difference
4. Note initial running power = **Minimum power**
5. Wait for AC to reach full cooling (hot day helps)
6. Note peak sustained power = **Maximum power**

### Configuration Examples by AC Type

#### Small Window/Portable Units (500-800W)
```yaml
power_idle_threshold: 5      # Standby: 3-5W
power_min_threshold: 80     # Minimum cooling: 80-120W
power_max_threshold: 600    # Maximum cooling: 500-800W
```

#### Medium Split Systems (1000-2000W)
```yaml
power_idle_threshold: 10     # Standby: 5-15W
power_min_threshold: 150    # Minimum cooling: 150-300W
power_max_threshold: 1500   # Maximum cooling: 1200-2000W
```

#### Large Central/Multi-zone Systems (2000-5000W)
```yaml
power_idle_threshold: 20     # Standby: 10-30W
power_min_threshold: 400    # Minimum cooling: 400-800W
power_max_threshold: 4000   # Maximum cooling: 3000-5000W
```

#### High-Power Mini-Split Example (User's AC)
Based on a real user's AC with these characteristics:
- Idle/standby: 3-4W
- Running at minimum: 230W
- Running at full power: 1200W

Recommended configuration:
```yaml
power_idle_threshold: 10     # Set slightly above idle (3-4W) for stability
power_min_threshold: 200    # Set slightly below minimum running (230W)
power_max_threshold: 1000   # Set below maximum (1200W) to catch high power states
```

### Setting Optimal Thresholds

#### General Guidelines

1. **Idle Threshold**: Set 2-3x higher than actual standby power
   - Prevents false "on" detection from power sensor noise
   - Example: If standby is 3W, set threshold to 8-10W

2. **Min Threshold**: Set 10-20% below typical minimum running power
   - Ensures reliable detection when AC starts
   - Example: If min running is 230W, set threshold to 190-210W

3. **Max Threshold**: Set at 70-80% of actual maximum power
   - Captures "high power" state without requiring absolute peak
   - Example: If max is 1200W, set threshold to 850-1000W

#### Safety Margins

Always leave margins between thresholds:
- Idle to Min: At least 50W gap
- Min to Max: At least 200W gap

This prevents threshold overlap and ensures clear state detection.

### Impact on HysteresisLearner

Accurate power thresholds are essential for the HysteresisLearner feature:

- **Too Low Idle**: May miss AC turn-on events
- **Too High Min**: May not detect low-power cooling states
- **Too Low Max**: May not distinguish between moderate and high cooling

The HysteresisLearner uses power transitions to learn:
- When your AC starts cooling (temperature threshold)
- When your AC stops cooling (temperature threshold)
- The temperature "window" your AC maintains

### Troubleshooting Power Thresholds

#### Symptoms of Incorrect Thresholds

1. **Learning not collecting data**: Idle threshold too high
2. **Constant "high power" state**: Max threshold too low
3. **Never sees "idle" state**: Idle threshold too low
4. **Erratic state changes**: Thresholds too close together

#### Debug Mode

Enable debug logging to see power state detection:
```yaml
logger:
  default: info
  logs:
    custom_components.smart_climate.offset_engine: debug
```

Look for messages like:
```
Power state: idle (3W < 10W threshold)
Power state: moderate (450W between 200W and 1000W)
Power transition detected: idle -> moderate
```

### Advanced Configuration

#### Variable Speed Compressors

Modern inverter ACs have highly variable power consumption:
```yaml
# Inverter AC with 100-1500W range
power_idle_threshold: 15
power_min_threshold: 80     # Catches ultra-low speed operation
power_max_threshold: 1200   # Below peak but captures high demand
```

#### Multi-Stage Systems

For systems with discrete stages:
```yaml
# 2-stage system: 800W (stage 1) or 1600W (stage 2)
power_idle_threshold: 20
power_min_threshold: 700    # Below stage 1
power_max_threshold: 1400   # Between stage 1 and 2
```

### Quick Reference Table

| AC Type | Typical Range | Idle | Min | Max |
|---------|--------------|------|-----|-----|
| Small Window | 500-800W | 5-10W | 80-120W | 400-600W |
| Portable | 800-1200W | 5-15W | 100-200W | 600-1000W |
| Split System | 1000-3000W | 10-20W | 150-400W | 800-2500W |
| Central AC | 2000-5000W | 20-50W | 400-800W | 1500-4000W |
| Mini-Split | 600-2000W | 3-15W | 100-300W | 500-1800W |

Remember: These are starting points. Always verify with your actual power sensor readings!

### Step 4: Options Flow (Modify After Setup)

After initial setup, you can modify ALL settings through the Options flow:

1. Go to Settings → Devices & Services
2. Find your Smart Climate integration
3. Click "Configure"
4. Modify any setting through the comprehensive UI
5. Click "Submit" to apply changes

The options flow provides the same comprehensive settings as initial setup, allowing you to fine-tune your configuration without editing YAML files.

### Complete Setup

1. Review your configuration
2. Click "Submit" to create the Smart Climate entity
3. The new climate entity will appear in your devices list
4. A learning switch entity will also be created for control

## YAML Configuration (Advanced/Optional)

While the UI now provides access to all settings, YAML configuration remains available for advanced users who prefer text-based configuration or need to configure multiple devices at once.

### Basic Configuration

Add to your `configuration.yaml`:

```yaml
smart_climate:
  - name: "Living Room Smart AC"
    climate_entity: climate.living_room_ac
    room_sensor: sensor.living_room_temperature
```

### Full Configuration Example

```yaml
smart_climate:
  - name: "Living Room Smart AC"
    # Required entities
    climate_entity: climate.living_room_ac
    room_sensor: sensor.living_room_temperature
    
    # Optional sensors
    outdoor_sensor: sensor.outdoor_temperature
    power_sensor: sensor.ac_power_consumption
    
    # Temperature limits
    min_temperature: 16      # Minimum setpoint temperature
    max_temperature: 30      # Maximum setpoint temperature
    
    # Offset configuration
    max_offset: 5           # Maximum offset in either direction
    update_interval: 180    # Seconds between offset updates
    
    # Mode-specific settings
    away_temperature: 26    # Fixed temp for away mode
    sleep_offset: 1.0       # Extra offset for sleep mode
    boost_offset: -2.0      # Extra cooling for boost mode
    
    # Learning configuration
    enable_learning: false  # Start with learning disabled
    data_retention_days: 60 # Days to keep learning data
    learning_feedback_delay: 45  # Seconds before feedback collection
    
  # You can configure multiple climate devices
  - name: "Bedroom Smart AC"
    climate_entity: climate.bedroom_ac
    room_sensor: sensor.bedroom_temperature
    sleep_offset: 2.0  # Higher offset for bedroom comfort
```

### Configuration Parameters Reference

All parameters below are available in both UI and YAML configuration:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | string | Yes | - | Friendly name for the entity |
| `climate_entity` | entity_id | Yes | - | The climate entity to control |
| `room_sensor` | entity_id | Yes | - | Room temperature sensor |
| `outdoor_sensor` | entity_id | No | None | Outdoor temperature sensor |
| `power_sensor` | entity_id | No | None | Power consumption sensor |
| `min_temperature` | float | No | 16 | Minimum temperature limit (°C) |
| `max_temperature` | float | No | 30 | Maximum temperature limit (°C) |
| `max_offset` | float | No | 5 | Maximum offset allowed (°C) |
| `update_interval` | integer | No | 180 | Update frequency (seconds) |
| `ml_enabled` | boolean | No | true | Enable machine learning features |
| `away_temperature` | float | No | 26 | Temperature for away mode (°C) |
| `sleep_offset` | float | No | 1.0 | Additional offset for sleep mode (°C) |
| `boost_offset` | float | No | -2.0 | Additional cooling for boost mode (°C) |
| `gradual_adjustment_rate` | float | No | 0.5 | Temperature change per update (°C) |
| `enable_learning` | boolean | No | false | Enable learning on startup |
| `data_retention_days` | integer | No | 60 | Days to retain learning data |
| `learning_feedback_delay` | integer | No | 45 | Delay before feedback collection (seconds) |
| `power_idle_threshold` | integer | No | 50 | Power threshold for idle state (W) |
| `power_min_threshold` | integer | No | 100 | Power threshold for minimum operation (W) |
| `power_max_threshold` | integer | No | 250 | Power threshold for maximum operation (W) |

## Learning Feedback Delay Configuration

The `learning_feedback_delay` parameter controls how long the system waits after a temperature adjustment before measuring the actual sensor offset. This is important for accurate learning.

### Choosing the Right Delay

Different AC units respond at different speeds:

- **Fast-responding units** (modern inverters, mini-splits): 30-60 seconds
- **Standard units**: 45-90 seconds (default: 45)
- **Slow-responding units** (older systems, large spaces): 90-180 seconds

### How to Determine Your Optimal Delay

1. Enable debug logging:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.smart_climate: debug
   ```

2. Make temperature adjustments and observe logs
3. Note how long it takes for the AC's internal temperature to stabilize
4. Set the feedback delay slightly longer than this stabilization time

### Example for Different AC Types

```yaml
smart_climate:
  # Modern mini-split (fast response)
  - name: "Living Room Mini-Split"
    climate_entity: climate.living_room_ac
    room_sensor: sensor.living_room_temp
    learning_feedback_delay: 30
    
  # Standard central AC (medium response)
  - name: "Main Floor AC"
    climate_entity: climate.central_ac
    room_sensor: sensor.hallway_temp
    learning_feedback_delay: 60
    
  # Older window unit (slow response)
  - name: "Bedroom Window AC"
    climate_entity: climate.bedroom_ac
    room_sensor: sensor.bedroom_temp
    learning_feedback_delay: 120
```

## Sensor Requirements

### Room Temperature Sensor

The room sensor must:
- Provide numeric temperature values
- Update at least every 5 minutes
- Be placed away from direct airflow
- Not be affected by heat sources

Good sensor placement:
- Wall-mounted at sitting/standing height
- Away from windows and doors
- Not in direct sunlight
- Clear of furniture and obstacles

### Outdoor Temperature Sensor (Optional)

Can be:
- Physical outdoor sensor
- Weather integration sensor
- Must update at least hourly

### Power Sensor (Optional)

Should:
- Monitor the climate device's power consumption
- Report in Watts (W) or kilowatts (kW)
- Update frequently (every 10-60 seconds)
- Have sufficient resolution to detect on/off states

## After Configuration

### Verify Setup

1. Check that your new Smart Climate entity appears in the UI
2. Verify the current temperature shows your room sensor value
3. Test setting a temperature and observe the behavior
4. Check for any errors in the logs

### Enable Learning

1. Find the learning switch entity (e.g., "Living Room Smart AC Learning")
2. Turn on the switch to enable learning
3. Monitor the switch attributes for learning progress

### Next Steps

- [Learn how to use your Smart Climate device](usage.md)
- [Understand the learning system](learning-system.md)
- [Troubleshoot any issues](troubleshooting.md)