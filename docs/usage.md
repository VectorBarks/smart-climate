# Usage Guide

This guide covers how to use Smart Climate Control for optimal comfort and efficiency.

## Basic Operation

Once configured, Smart Climate Control appears as a standard climate entity in Home Assistant with enhanced intelligence working behind the scenes.

### Setting Temperature

1. **Use Normal Climate Controls**: Set your desired temperature using:
   - Home Assistant UI climate card
   - Google Home/Alexa voice commands
   - Automations and scripts
   - Physical thermostats (if integrated)

2. **Automatic Offset Application**: The system automatically:
   - Calculates the required offset based on sensor differences
   - Applies gradual adjustments to prevent oscillation
   - Learns from results to improve future predictions

3. **What You See vs What Happens**:
   - You set: 22°C (your desired room temperature)
   - System calculates: +2°C offset needed
   - AC receives: 20°C command
   - Result: Room reaches and maintains 22°C

## Operating Modes

Smart Climate Control provides preset modes for different scenarios:

### Normal Mode (None)
- Default operating mode
- Dynamic offset compensation based on current conditions
- Learning system active (if enabled)
- Best for everyday use

**When to use**: Most of the time - this mode provides optimal comfort with energy efficiency.

### Away Mode
- Fixed temperature setting (default 26°C, configurable)
- Ignores sensor readings for energy savings
- Maintains minimal cooling/heating
- No learning data collection

**When to use**: When nobody is home for extended periods. Can be automated with presence detection.

### Sleep Mode
- Applies additional positive offset (default +1°C)
- Reduces cooling for quieter operation
- Prevents overcooling during sleep
- Continues learning with sleep-specific patterns

**When to use**: At night for better sleep comfort and reduced AC noise.

### Boost Mode
- Applies additional negative offset (default -2°C)
- Provides extra cooling for rapid temperature reduction
- Temporary intensive cooling
- Should be used sparingly

**When to use**: When you need to cool a room quickly, such as returning home on a hot day.

### Switching Modes

Change modes through:
- Climate entity preset dropdown in UI
- Service calls in automations:
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

1. **Find the Learning Switch**: Look for "{Your Climate Name} Learning" in your entities
   - Example: `switch.living_room_smart_ac_learning`

2. **Turn On Learning**: 
   - Toggle the switch to enable intelligent pattern learning
   - System begins collecting performance data
   - Predictions improve over time

3. **Turn Off Learning**:
   - Toggle the switch to disable learning
   - System continues using existing patterns
   - Rule-based calculations remain active

### Monitoring Learning Progress

The learning switch entity provides rich attributes:

```yaml
# Example attributes
learning_enabled: true
samples_collected: 156
learning_accuracy: 0.89
confidence_level: 0.75
last_update: "2024-01-15 14:30:00"
average_error: 0.3
prediction_quality: "good"
```

**Key Metrics**:
- `samples_collected`: Total learning data points (aim for 50+ for basic patterns)
- `learning_accuracy`: How close predictions are to actual needs (0.0-1.0)
- `confidence_level`: System's confidence in its predictions
- `average_error`: Average temperature offset error in °C

### Learning Timeline

- **First 24 hours**: Basic patterns emerge
- **2-3 days**: Time-of-day patterns stabilize
- **1 week**: Good accuracy for regular conditions
- **2-4 weeks**: Seasonal and weather patterns develop

### Resetting Training Data

If you need to clear all learned patterns and start fresh, use the reset training data button:

**Entity**: `button.{climate_name}_reset_training_data`
- Location: Device configuration section in Home Assistant UI
- Icon: Database remove (mdi:database-remove)
- Action: Clears all learning data (both in-memory and saved files)
- Safety: Creates a backup before deletion

**When to reset training data**:
- After major changes to your AC system or room layout
- When moving the integration to a different room or AC unit
- If learning patterns become inaccurate due to unusual usage
- At the start of a new season if you prefer fresh patterns
- After significant sensor placement changes

**How to reset**:
1. Navigate to your Smart Climate device in Home Assistant
2. Find the "Reset Training Data" button in configuration
3. Press the button to clear all learned patterns
4. The system creates a backup before deletion (check logs for location)
5. Learning starts fresh with the next data collection

**Note**: After resetting, the system will rely on rule-based calculations until new patterns develop. Allow 24-48 hours for basic patterns to re-emerge.

## Manual Override Controls

For temporary adjustments, use the manual override number entities:

### Manual Offset Control

Entity: `number.{climate_name}_manual_offset`
- Range: -5°C to +5°C
- Use when: The calculated offset isn't quite right
- Example: Set to +1°C if room feels slightly cool

### Override Duration

Entity: `number.{climate_name}_override_duration`
- Range: 0 to 480 minutes
- Use when: You want temporary control
- Example: Set 120 minutes for a 2-hour override

### Using Manual Overrides

1. **Temporary Adjustment**:
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

2. **Cancel Override**: Set duration to 0 to immediately return to automatic control

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

The Smart Climate entity provides additional attributes:

```yaml
current_temperature: 22.5      # Room sensor temperature
target_temperature: 22.0       # Your desired temperature
offset_applied: -1.5          # Current offset being used
offset_reason: "Learned pattern + outdoor temp"
learning_active: true
last_update: "2024-01-15 14:45:30"
```

### Using History Graphs

Create useful visualizations:

```yaml
# In your Lovelace UI
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
- Place room sensor at seated/standing height
- Avoid direct sunlight or airflow
- Keep away from heat sources
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
1. Check sensor placement and accuracy
2. Verify learning is enabled and collecting data
3. Review offset calculations in debug logs
4. Consider adjusting feedback delay for your AC type
5. Use manual override temporarily while investigating

## Advanced Usage

### Multiple Zones

If you have multiple Smart Climate entities:
- Each learns independently
- Consider coordinating modes through automations
- Monitor for conflicting operations in adjacent spaces

### Seasonal Adjustments

The learning system adapts to seasons automatically, but you can help by:
- Clearing old learning data at season changes (optional)
- Adjusting temperature limits seasonally
- Monitoring and adjusting mode offsets if needed

### Integration with Other Systems

Smart Climate Control works well with:
- **Presence detection**: Automatic home/away modes
- **Weather forecasts**: Predictive adjustments (future feature)
- **Energy monitoring**: Track efficiency improvements
- **Voice assistants**: Natural temperature control

## Next Steps

- [Understand the learning system in detail](learning-system.md)
- [Configure advanced features](configuration.md)
- [Troubleshoot any issues](troubleshooting.md)
- [Learn about the architecture](architecture.md)