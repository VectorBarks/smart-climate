# User Guide

This guide covers daily usage of Smart Climate Control, from basic operation to understanding the learning system and advanced features.

## Table of Contents

1. [Basic Operation](#basic-operation)
2. [Understanding the Learning System](#understanding-the-learning-system)
3. [Operating Modes](#operating-modes)
4. [Learning System Controls](#learning-system-controls)
5. [Manual Override Controls](#manual-override-controls)
6. [Training Your System Effectively](#training-your-system-effectively)
7. [Integration with Automations](#integration-with-automations)
8. [Monitoring Performance](#monitoring-performance)
9. [Best Practices](#best-practices)

## Basic Operation

Once configured, Smart Climate Control appears as a standard climate entity in Home Assistant with enhanced intelligence working behind the scenes.

### Setting Temperature

**Use Normal Climate Controls**: Set your desired temperature through:
- Home Assistant UI climate card
- Google Home/Alexa voice commands  
- Automations and scripts
- Physical thermostats (if integrated)

**What Happens Automatically**:
- System calculates required offset based on sensor differences
- Applies gradual adjustments to prevent oscillation
- Learns from results to improve future predictions

**Example**:
- You set: 22°C (your desired room temperature)
- System calculates: +2°C offset needed
- AC receives: 20°C command
- Result: Room reaches and maintains 22°C

## Understanding the Learning System

### The Simple Concept

Think of the learning system as a personal assistant that observes patterns:

1. **Observation**: "When we set the AC to 20°C, the room actually ends up at 22°C"
2. **Pattern Recognition**: "This happens consistently in the afternoon"
3. **Prediction**: "Next time, let's set it to 18°C to actually get 22°C"
4. **Refinement**: "That worked well, let's remember this pattern"

### Two Learning Approaches

#### 1. Basic Offset Learning (Always Active)
- Tracks patterns throughout the day
- Adapts to outdoor temperature influences
- Builds confidence through repetition
- Works with any AC unit

#### 2. HysteresisLearner (With Power Monitoring)
If you have a power sensor, this advanced system learns your AC's operational behavior:
- Detects when your AC starts cooling (power spike)
- Identifies when it stops (power drop)
- Learns the temperature thresholds for these transitions
- Optimizes predictions based on AC state

### Learning Timeline

- **First 24 hours**: Basic patterns emerge
- **2-3 days**: Time-of-day patterns stabilize
- **1 week**: Good accuracy for regular conditions
- **2-4 weeks**: Seasonal and weather patterns develop

## Operating Modes

Smart Climate Control provides preset modes for different scenarios.

### Normal Mode (None)
- **Description**: Default operating mode with dynamic offset compensation
- **Features**: Learning system active, optimal comfort and efficiency
- **When to Use**: Most of the time - provides optimal comfort with energy efficiency

### Away Mode
- **Description**: Fixed temperature setting (default 26°C, configurable)
- **Features**: Ignores sensor readings, maintains minimal cooling/heating
- **When to Use**: When nobody is home for extended periods
- **Automation**: Can be automated with presence detection

### Sleep Mode  
- **Description**: Additional positive offset (default +1°C) for quieter operation
- **Features**: Reduces cooling, prevents overcooling during sleep
- **When to Use**: At night for better sleep comfort and reduced AC noise

### Boost Mode
- **Description**: Additional negative offset (default -2°C) for rapid cooling
- **Features**: Extra cooling for rapid temperature reduction
- **When to Use**: When you need to cool a room quickly (returning home on hot day)
- **Note**: Should be used sparingly

### Switching Modes

Change modes through the climate entity preset dropdown or automations:

```yaml
service: climate.set_preset_mode
target:
  entity_id: climate.living_room_smart_ac
data:
  preset_mode: away
```

## Learning System Controls

### Enabling/Disabling Learning

The learning system is controlled through a dedicated switch entity:

1. **Find the Learning Switch**: `switch.{climate_name}_learning`
   - Example: `switch.living_room_smart_ac_learning`

2. **Turn On Learning**:
   - System begins collecting performance data
   - Predictions improve over time
   - Creates rich learning attributes

3. **Turn Off Learning**:
   - System continues using existing patterns
   - Rule-based calculations remain active
   - No new learning data collected

### Monitoring Learning Progress

The learning switch provides comprehensive diagnostics:

```yaml
# Example attributes
switch.living_room_ac_learning:
  learning_enabled: true
  samples_collected: 156
  learning_accuracy: 0.89
  confidence_level: 0.75
  last_update: "2024-01-15 14:30:00"
  average_error: 0.3
  prediction_quality: "good"
  patterns_learned: 18
  has_sufficient_data: true
  last_sample_collected: "2025-07-08 14:30:00"
```

**Key Metrics**:
- **samples_collected**: Total learning data points (aim for 50+ for basic patterns)
- **learning_accuracy**: How close predictions are to actual needs (0.0-1.0)
- **confidence_level**: System's confidence in its predictions
- **average_error**: Average temperature offset error in °C
- **patterns_learned**: Number of distinct patterns recognized

### Resetting Training Data

If you need to clear all learned patterns and start fresh:

**Entity**: `button.{climate_name}_reset_training_data`
- **Location**: Device configuration in Home Assistant UI
- **Icon**: Database remove (mdi:database-remove)
- **Action**: Clears all learning data (both in-memory and saved files)
- **Safety**: Creates backup before deletion

**When to Reset**:
- After major changes to AC system or room layout
- Moving integration to different room or AC unit
- Learning patterns become inaccurate due to unusual usage
- Start of new season if you prefer fresh patterns
- After significant sensor placement changes

**How to Reset**:
1. Navigate to your Smart Climate device in Home Assistant
2. Find "Reset Training Data" button in configuration
3. Press button to clear all learned patterns
4. System creates backup before deletion (check logs for location)
5. Learning starts fresh with next data collection

**Note**: After resetting, system relies on rule-based calculations until new patterns develop (allow 24-48 hours).

## Manual Override Controls

For temporary adjustments, use the manual override number entities.

### Manual Offset Control

**Entity**: `number.{climate_name}_manual_offset`
- **Range**: -5°C to +5°C
- **Use When**: The calculated offset isn't quite right
- **Example**: Set to +1°C if room feels slightly cool

### Override Duration

**Entity**: `number.{climate_name}_override_duration`  
- **Range**: 0 to 480 minutes
- **Use When**: You want temporary control
- **Example**: Set 120 minutes for a 2-hour override

### Using Manual Overrides

```yaml
# Make it 1°C cooler for 2 hours
- service: number.set_value
  target:
    entity_id: number.living_room_smart_ac_manual_offset
  data:
    value: -1
- service: number.set_value
  target:
    entity_id: number.living_room_smart_ac_override_duration
  data:
    value: 120
```

**Cancel Override**: Set duration to 0 to immediately return to automatic control.

## Training Your System Effectively

### Understanding Learning Metrics

Monitor these key indicators for training progress:

**Learning Progress Phases**:
- **0-20%**: Just starting to collect data, high uncertainty
- **20-40%**: Basic patterns emerging, daily routine identified
- **40-60%**: Solid understanding of typical usage patterns
- **60-80%**: Reliable predictions, handles most scenarios well
- **80-100%**: Full optimization, excellent accuracy across all conditions

### Best Practices for Training

#### 1. Consistent Usage Patterns
- Use similar temperatures at similar times
- Maintain consistent comfort preferences
- Let system experience your full daily routine

#### 2. Avoid Confusing the System
- Don't make rapid temperature changes (wait 10+ minutes between)
- Avoid manual overrides during learning phase
- Keep doors/windows closed during training
- Don't block vents or redirect airflow

#### 3. Optimal Feedback Timing

The `learning_feedback_delay` is crucial for accurate learning:

**Typical Values by AC Type**:
- **Modern Inverter Units**: 30-60 seconds
- **Standard Split Systems**: 45-90 seconds (default: 45)
- **Older Units**: 90-180 seconds

**How to Optimize**:
1. Enable debug logging
2. Set AC to new temperature
3. Watch logs for internal sensor stabilization
4. Set feedback delay 10-15 seconds after stabilization

#### 4. Power Sensor Best Practices

If you have power monitoring:
- Ensure power thresholds match your AC's consumption patterns
- System shows "learning_hysteresis" initially
- After 5-10 power transitions, learns your AC's behavior
- Dramatically improves prediction accuracy

## Integration with Automations

### Presence-Based Control

```yaml
automation:
  - alias: "Climate Away Mode When Nobody Home"
    trigger:
      - platform: state
        entity_id: group.family
        to: 'not_home'
        for: '00:30:00'
    action:
      - service: climate.set_preset_mode
        target:
          entity_id: climate.living_room_smart_ac
        data:
          preset_mode: away
          
  - alias: "Climate Normal Mode When Someone Returns"
    trigger:
      - platform: state
        entity_id: group.family
        to: 'home'
    action:
      - service: climate.set_preset_mode
        target:
          entity_id: climate.living_room_smart_ac
        data:
          preset_mode: none
```

### Time-Based Modes

```yaml
automation:
  - alias: "Climate Sleep Mode at Night"
    trigger:
      - platform: time
        at: "22:00:00"
    action:
      - service: climate.set_preset_mode
        target:
          entity_id: climate.bedroom_smart_ac
        data:
          preset_mode: sleep
          
  - alias: "Climate Normal Mode in Morning"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: climate.set_preset_mode
        target:
          entity_id: climate.bedroom_smart_ac
        data:
          preset_mode: none
```

### Learning Control Automation

```yaml
automation:
  - alias: "Pause Learning During Parties"
    trigger:
      - platform: state
        entity_id: input_boolean.party_mode
        to: 'on'
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.living_room_smart_ac_learning
```

## Monitoring Performance

### Climate Entity Attributes

The Smart Climate entity provides additional insights:

```yaml
current_temperature: 22.5      # Room sensor temperature
target_temperature: 22.0       # Your desired temperature
offset_applied: -1.5           # Current offset being used
offset_reason: "Learned pattern + outdoor temp"
learning_active: true
last_update: "2024-01-15 14:45:30"
```

### Dashboard Visualization

Smart Climate automatically creates 5 dashboard sensors:
- **Current Offset**: Real-time temperature compensation
- **Learning Progress**: System optimization percentage  
- **Current Accuracy**: Prediction accuracy over time
- **Calibration Status**: Current learning phase
- **Hysteresis State**: AC behavior detection

Use the one-click dashboard generation service to create comprehensive visualizations.

### History Graphs

Create useful visualizations in Lovelace:

```yaml
type: history-graph
entities:
  - entity: climate.living_room_smart_ac
    name: Set Temperature
  - entity: sensor.living_room_temperature
    name: Room Temperature
  - entity: sensor.living_room_ac_internal_temp
    name: AC Sensor
hours_to_show: 24
```

## Best Practices

### Optimal Sensor Placement
- Place room sensor at seated/standing height (1.2-1.5m)
- Avoid direct sunlight, airflow, or heat sources
- Keep away from exterior walls
- Ensure good air circulation around sensor

### Learning System Tips
- Enable learning after initial setup verification
- Allow at least 48 hours for initial pattern development
- Don't make frequent manual adjustments during learning
- Monitor learning metrics to track improvement

### Energy Efficiency
- Use Away mode when leaving for extended periods
- Set reasonable temperature targets
- Enable Sleep mode at night
- Avoid excessive use of Boost mode

### Troubleshooting Performance

If the system isn't maintaining temperature well:

1. **Check Sensor Placement**: Verify sensors are accurate and well-positioned
2. **Verify Learning Status**: Ensure learning is enabled and collecting data
3. **Review Offset Calculations**: Check debug logs for reasoning
4. **Adjust Feedback Delay**: Consider optimization for your AC type
5. **Use Manual Override**: Temporary adjustment while investigating

## Advanced Usage

### Multiple Zones

If you have multiple Smart Climate entities:
- Each learns independently
- Consider coordinating modes through automations
- Monitor for conflicting operations in adjacent spaces

### Seasonal Adjustments

The learning system adapts to seasons automatically, but you can help by:
- Monitoring learning accuracy during season changes
- Adjusting temperature limits seasonally
- Reviewing and adjusting mode offsets if needed

### Integration with Other Systems

Smart Climate Control works well with:
- **Presence Detection**: Automatic home/away modes
- **Weather Forecasts**: Predictive adjustments (with weather integration)
- **Energy Monitoring**: Track efficiency improvements
- **Voice Assistants**: Natural temperature control

## Understanding System Behavior

### What's Normal

**During Initial Learning (First 24-48 hours)**:
- System in "PRIMING" state with minimal offsets
- Learning accuracy starting low, gradually improving
- Conservative temperature adjustments
- Some manual fine-tuning may be needed

**After Learning Establishes (1-2 weeks)**:
- Accuracy typically 70-85%
- Consistent temperature maintenance
- Reduced need for manual adjustments
- Predictable response to temperature changes

**Fully Optimized (1 month+)**:
- Accuracy 85-95%
- Excellent temperature stability
- Handles unusual conditions well
- Minimal energy waste

### When to Be Concerned

**Poor Learning Progress**:
- Accuracy stuck below 50% after 2+ weeks
- Sample collection not increasing
- Frequent large temperature swings

**Possible Causes and Solutions**:
- Sensor placement issues → relocate sensors
- Inconsistent usage patterns → establish routine
- Environmental changes → check for new heat sources, drafts
- AC maintenance needed → inspect filters, refrigerant

## Next Steps

After mastering basic usage:

1. **Explore Advanced Features**: Learn about [thermal efficiency](technical-reference.md#thermal-efficiency-management) and [weather integration](technical-reference.md#weather-forecast-integration)
2. **Optimize Configuration**: Review [Configuration Guide](configuration-guide.md) for fine-tuning options
3. **Understand All Sensors**: Check [Sensor Reference](sensor-reference.md) for complete monitoring capabilities
4. **Troubleshoot Issues**: Reference solutions for common problems

---

*Your Smart Climate Control system improves daily - enjoy optimal comfort with minimal effort!*