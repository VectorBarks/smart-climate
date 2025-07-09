# Dashboard Template Sensors Reference

This document explains each template sensor created by the Smart Climate Dashboard Blueprint. Understanding these sensors helps you customize the dashboard and create your own visualizations.

## Overview

The dashboard blueprint creates template sensors that transform raw Smart Climate data into visualization-friendly formats. These sensors:

- Extract specific attributes from the main entities
- Calculate derived metrics like trends and averages
- Format data for chart consumption
- Provide fallback values to prevent errors

## Template Sensor Naming Convention

All template sensors follow this naming pattern:
```
sensor.{climate_name}_{metric_type}
```

For example, if your climate entity is `climate.living_room_smart_ac`:
- `sensor.living_room_smart_ac_offset_history`
- `sensor.living_room_smart_ac_learning_progress`
- `sensor.living_room_smart_ac_accuracy_trend`

## Core Template Sensors

### 1. Offset History Sensor

**Entity ID**: `sensor.{name}_offset_history`

**Purpose**: Tracks the current offset and maintains recent history for visualization

**State**: Current offset value in °C

**Attributes**:
```yaml
history: List of recent offset values (last 24 hours)
timestamp: When the current offset was calculated
clamped: Whether the offset hit the maximum limit
reason: Human-readable explanation for the offset
```

**Template Expression**:
```jinja2
{% set climate = states('climate.living_room_smart_ac') %}
{% set offset = state_attr('climate.living_room_smart_ac', 'current_offset') %}
{{ offset | float(0) }}
```

**Usage in Dashboard**:
- Gauge cards showing current offset
- History graphs showing offset changes over time
- Conditional cards based on offset direction

**Customization Example**:
```yaml
# Show warning when offset is extreme
- type: conditional
  conditions:
    - entity: sensor.living_room_offset_history
      state_not: '0.0'
    - entity: sensor.living_room_offset_history
      above: 4.0
  card:
    type: markdown
    content: "⚠️ High offset detected!"
```

### 2. Learning Progress Sensor

**Entity ID**: `sensor.{name}_learning_progress`

**Purpose**: Calculates learning completion percentage based on samples collected

**State**: Percentage complete (0-100%)

**Attributes**:
```yaml
samples_collected: Total number of learning samples
target_samples: Required samples for good predictions
estimated_completion: Time estimate for full learning
learning_rate: Samples per day
```

**Template Expression**:
```jinja2
{% set switch = 'switch.living_room_smart_ac_learning' %}
{% set samples = state_attr(switch, 'sample_count') | int(0) %}
{% set calibration = state_attr(switch, 'calibration_samples') | int(0) %}
{% set total = samples + calibration %}
{% set target = 200 %}  {# Minimum for good predictions #}
{{ ((total / target) * 100) | round(1) }}
```

**State Classes**:
- `state_class: measurement` - For statistics tracking
- `unit_of_measurement: '%'`

**Usage in Dashboard**:
- Progress bars showing learning completion
- Estimated time to completion calculations
- Conditional messages based on progress

**Interpretation Guide**:
| Progress | Meaning | Recommendation |
|----------|---------|----------------|
| 0-10% | Just started | Let system run normally |
| 10-50% | Basic patterns | Initial predictions working |
| 50-90% | Good coverage | Reliable predictions |
| 90-100% | Comprehensive | Excellent accuracy |

### 3. Accuracy Trend Sensor

**Entity ID**: `sensor.{name}_accuracy_trend`

**Purpose**: Calculates rolling accuracy average to show improvement over time

**State**: 7-day average accuracy (0-100%)

**Attributes**:
```yaml
daily_accuracy: List of daily accuracy values
trend_direction: improving/stable/declining
confidence_level: Statistical confidence in trend
best_accuracy: Highest accuracy achieved
```

**Template Expression**:
```jinja2
{% set switch = 'switch.living_room_smart_ac_learning' %}
{% set accuracy = state_attr(switch, 'prediction_accuracy') | float(0) %}
{# Calculate 7-day moving average from history #}
{{ accuracy | round(1) }}
```

**Advanced Calculations**:
```jinja2
{# Trend detection logic #}
{% set history = state_attr(switch, 'accuracy_history') | default([]) %}
{% if history | length > 7 %}
  {% set recent = history[-7:] | average %}
  {% set previous = history[-14:-7] | average %}
  {% if recent > previous + 5 %}
    improving
  {% elif recent < previous - 5 %}
    declining
  {% else %}
    stable
  {% endif %}
{% else %}
  insufficient_data
{% endif %}
```

**Usage in Dashboard**:
- Line charts showing accuracy over time
- Color-coded badges (green for improving, yellow for stable)
- Alerts when accuracy drops

### 4. Calibration Status Sensor

**Entity ID**: `sensor.{name}_calibration_status`

**Purpose**: Provides human-readable calibration phase information

**State**: Text description of calibration status

**State Values**:
- `"Not Started"` - No calibration data collected
- `"Calibrating (X/10)"` - In progress with sample count
- `"Calibration Complete"` - Minimum samples collected
- `"Ready"` - Calibration done and learning active

**Attributes**:
```yaml
calibration_samples: Number of calibration samples
required_samples: Samples needed to exit calibration
is_calibrating: Boolean for conditional cards
stable_offset_cached: Whether stable offset is available
last_stable_reading: Timestamp of last stable state
```

**Template Expression**:
```jinja2
{% set switch = 'switch.living_room_smart_ac_learning' %}
{% set cal_samples = state_attr(switch, 'calibration_samples') | int(0) %}
{% set is_enabled = is_state(switch, 'on') %}

{% if not is_enabled %}
  Learning Disabled
{% elif cal_samples < 10 %}
  Calibrating ({{ cal_samples }}/10)
{% else %}
  Calibration Complete
{% endif %}
```

**Icon Logic**:
```jinja2
{% if cal_samples < 10 %}
  mdi:progress-clock
{% else %}
  mdi:check-circle
{% endif %}
```

**Usage in Dashboard**:
- Status cards with dynamic icons
- Progress indicators during calibration
- Conditional instructions based on phase

### 5. Hysteresis State Sensor

**Entity ID**: `sensor.{name}_hysteresis_state`

**Purpose**: Shows AC temperature window learning status (requires power sensor)

**State**: Human-readable hysteresis detection state

**State Values**:
- `"No Power Sensor"` - Power monitoring not configured
- `"Learning Windows"` - Detecting temperature thresholds
- `"Windows Detected"` - Start/stop thresholds learned
- `"Optimizing"` - Refining threshold accuracy

**Attributes**:
```yaml
start_threshold: Temperature where AC typically starts
stop_threshold: Temperature where AC typically stops
temperature_window: The maintained temperature range
current_power: Latest power reading
power_state: idle/low/moderate/high
confidence: Confidence in detected thresholds
```

**Template Expression**:
```jinja2
{% set switch = 'switch.living_room_smart_ac_learning' %}
{% set state = state_attr(switch, 'hysteresis_state') | default('unknown') %}
{% set thresholds = state_attr(switch, 'hysteresis_thresholds') | default({}) %}

{% if state == 'no_power_sensor' %}
  No Power Sensor
{% elif state == 'learning_hysteresis' %}
  Learning Windows
{% elif thresholds.start and thresholds.stop %}
  Windows Detected ({{ thresholds.start }}°C - {{ thresholds.stop }}°C)
{% else %}
  {{ state | replace('_', ' ') | title }}
{% endif %}
```

**Visual Indicators**:
```yaml
# Card showing temperature window
type: gauge
entity: sensor.room_temperature
min: 20
max: 30
needle: true
segments:
  - from: 20
    to: "{{ state_attr('sensor.hysteresis_state', 'start_threshold') }}"
    color: blue
  - from: "{{ state_attr('sensor.hysteresis_state', 'start_threshold') }}"
    to: "{{ state_attr('sensor.hysteresis_state', 'stop_threshold') }}"
    color: green
  - from: "{{ state_attr('sensor.hysteresis_state', 'stop_threshold') }}"
    to: 30
    color: red
```

## Advanced Template Sensors

### 6. Power Correlation Sensor

**Entity ID**: `sensor.{name}_power_correlation`

**Purpose**: Shows correlation between power usage and temperature changes

**State**: Correlation coefficient (-1 to 1)

**Interpretation**:
- Near 1: Strong positive correlation (more power = more cooling)
- Near 0: No correlation
- Near -1: Inverse correlation (unusual, check configuration)

### 7. Offset Stability Sensor

**Entity ID**: `sensor.{name}_offset_stability`

**Purpose**: Measures how stable offset predictions have been

**State**: Stability percentage (0-100%)

**Calculation**: Standard deviation of recent offsets, converted to percentage

### 8. Learning Rate Sensor

**Entity ID**: `sensor.{name}_learning_rate`

**Purpose**: Tracks how quickly the system is learning

**State**: Samples per day

**Attributes**:
```yaml
samples_today: Count for current day
samples_yesterday: Previous day count
weekly_average: 7-day average rate
```

## Creating Custom Template Sensors

### Basic Template Structure

```yaml
template:
  - sensor:
      - name: "My Custom Metric"
        unique_id: smart_climate_custom_metric
        state: >
          {% set climate = 'climate.living_room_smart_ac' %}
          {% set switch = 'switch.living_room_smart_ac_learning' %}
          {# Your calculation here #}
          {{ value }}
        attributes:
          my_attribute: >
            {{ state_attr(climate, 'some_attribute') }}
        availability: >
          {{ states(climate) not in ['unknown', 'unavailable'] }}
```

### Performance Best Practices

1. **Use Availability Templates**
   ```jinja2
   availability: >
     {{ states('climate.entity') not in ['unknown', 'unavailable'] }}
   ```

2. **Provide Defaults**
   ```jinja2
   {{ state_attr('entity', 'attribute') | default(0) }}
   ```

3. **Limit Update Frequency**
   ```yaml
   sensor:
     scan_interval: 300  # 5 minutes
   ```

4. **Avoid Complex Calculations**
   - Precalculate in integration when possible
   - Use statistics platform for aggregations

### Example: Custom Comfort Score

```yaml
template:
  - sensor:
      - name: "Living Room Comfort Score"
        unique_id: living_room_comfort_score
        unit_of_measurement: "points"
        state: >
          {% set temp_diff = (state_attr('climate.living_room_smart_ac', 'current_temperature') | float(0) - 
                              state_attr('climate.living_room_smart_ac', 'temperature') | float(0)) | abs %}
          {% set offset = state_attr('climate.living_room_smart_ac', 'current_offset') | float(0) | abs %}
          {% set accuracy = state_attr('switch.living_room_smart_ac_learning', 'prediction_accuracy') | float(0) %}
          
          {# Score calculation: 100 - penalties #}
          {% set score = 100 %}
          {% set score = score - (temp_diff * 10) %}  {# -10 points per degree off #}
          {% set score = score - (offset * 5) %}       {# -5 points per degree offset #}
          {% set score = score + (accuracy / 2) %}     {# Bonus for learning accuracy #}
          
          {{ score | round(0) | max(0) | min(100) }}
        attributes:
          temperature_penalty: >
            {{ (temp_diff * 10) | round(0) }}
          offset_penalty: >
            {{ (offset * 5) | round(0) }}
          accuracy_bonus: >
            {{ (accuracy / 2) | round(0) }}
        icon: >
          {% if states('sensor.living_room_comfort_score') | int(0) > 80 %}
            mdi:emoticon-happy
          {% elif states('sensor.living_room_comfort_score') | int(0) > 60 %}
            mdi:emoticon-neutral
          {% else %}
            mdi:emoticon-sad
          {% endif %}
```

## Troubleshooting Template Sensors

### Common Issues

1. **Sensor Shows "unavailable"**
   - Check entity IDs are correct
   - Verify source entities exist
   - Add availability template

2. **Values Don't Update**
   - Check if source attributes are changing
   - Force update with different scan_interval
   - Verify template syntax in Developer Tools

3. **Performance Impact**
   - Simplify complex calculations
   - Increase scan_interval
   - Use trigger-based templates

### Debug Templates

Test in Developer Tools → Template:

```jinja2
{# Debug template #}
Climate entity state: {{ states('climate.living_room_smart_ac') }}
Current offset: {{ state_attr('climate.living_room_smart_ac', 'current_offset') }}
Switch state: {{ states('switch.living_room_smart_ac_learning') }}
Sample count: {{ state_attr('switch.living_room_smart_ac_learning', 'sample_count') }}

{# Test your calculation #}
{% set offset = state_attr('climate.living_room_smart_ac', 'current_offset') | float(0) %}
Result: {{ offset * 2 }}
```

## Integration with Automations

Template sensors can trigger automations:

```yaml
automation:
  - alias: "Notify when learning complete"
    trigger:
      - platform: numeric_state
        entity_id: sensor.living_room_learning_progress
        above: 90
    action:
      - service: notify.mobile_app
        data:
          message: "Smart Climate has completed initial learning!"
          
  - alias: "Alert on poor accuracy"
    trigger:
      - platform: numeric_state
        entity_id: sensor.living_room_accuracy_trend
        below: 70
        for: "01:00:00"
    action:
      - service: persistent_notification.create
        data:
          title: "Smart Climate Accuracy Low"
          message: "Check your temperature sensors"
```

## Next Steps

- Use these sensors to create custom dashboard cards
- Build automations based on learning progress
- Create your own template sensors for specific needs
- Share your custom sensors with the community