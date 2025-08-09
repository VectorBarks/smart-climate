# Weather Strategies - Pre-cooling Behavior

## Overview

Smart Climate Control includes weather-based pre-cooling strategies that automatically adjust your target temperature BEFORE weather events occur. Understanding how these strategies work is crucial for optimal configuration.

## Key Concept: Pre-cooling, Not Continuous Adjustment

**Important:** Weather strategies are designed for **pre-cooling only**. They activate BEFORE the weather event and expire when the event BEGINS, not when it ends.

### Timeline Example

```
8:00 AM  - Heat wave detected for noon
         - Pre-cooling starts: Target 24°C → 22°C
         
12:00 PM - Heat wave period begins
         - Strategy expires
         - Target returns to 24°C
         - Building has thermal mass pre-cooled
         
6:00 PM  - Heat wave continues (but no special offset)
         - Normal operation with tighter comfort bands
```

## Available Strategies

### Heat Wave Strategy

Designed for extreme temperature events (default: >30°C).

**Purpose:** Pre-cool building thermal mass before extreme heat arrives

**Configuration:**
- `heat_wave_temp_threshold`: Temperature to trigger strategy (20-40°C)
- `heat_wave_min_duration_hours`: Minimum duration of high temps (1-24h)
- `heat_wave_lookahead_hours`: How far to check forecast (1-72h)
- `heat_wave_pre_action_hours`: Hours before event to start (1-12h)
- `heat_wave_adjustment`: Temperature offset (e.g., -2.0°C)

### Clear Sky Strategy

Designed for solar heat gain from sunny periods.

**Purpose:** Pre-cool before intense sun exposure heats the building

**Configuration:**
- `clear_sky_condition`: Weather condition (usually "sunny")
- `clear_sky_min_duration_hours`: Minimum sunny period (1-24h)
- `clear_sky_lookahead_hours`: Forecast check period (1-72h)
- `clear_sky_pre_action_hours`: Pre-cooling lead time (1-12h)
- `clear_sky_adjustment`: Temperature offset (e.g., -1.5°C)

## Strategy Behavior

### Activation Rules

1. **First Match Wins:** Only ONE strategy can be active at a time
2. **Priority Order:** Strategies evaluated in configuration order (heat_wave first by default)
3. **No Stacking:** Offsets do NOT combine (-2°C OR -1.5°C, never -3.5°C)

### Expiration and Restoration

When a strategy expires:
1. `predictive_offset` returns to 0.0°C
2. Target temperature returns to user's original setpoint
3. Transition happens smoothly on next coordinator update

**Critical:** Strategies expire when the weather event STARTS, not when it ends. This is pre-cooling, not continuous adjustment.

## Configuration Validation

### Required Mathematical Relationship

For strategies to work, this MUST be true:
```
lookahead_hours >= pre_action_hours + min_duration_hours
```

### Examples

✅ **Valid Configuration:**
```yaml
lookahead_hours: 12
min_duration_hours: 4
pre_action_hours: 2
# Can see 4-hour events and pre-cool 2 hours before
```

❌ **Invalid Configuration:**
```yaml
lookahead_hours: 3
min_duration_hours: 4
pre_action_hours: 2
# Cannot detect 4-hour events in 3-hour window!
```

## During Weather Events

After pre-cooling expires, comfort is maintained by:

1. **Thermal Manager:** Automatically tightens comfort bands in extreme heat (≥30°C)
   - Normal band: ±1.0°C
   - At 35°C: ±0.7°C (30% tighter)

2. **Building Thermal Mass:** Pre-cooled mass provides cooling inertia

3. **Regular ML Offsets:** Continue learning and adapting to conditions

## Best Practices

### For Heat Waves

Best for climates with:
- Occasional extreme heat events
- Predictable heat wave patterns
- Buildings with good thermal mass

**Recommended Settings:**
```yaml
heat_wave_temp_threshold: 32    # Only for truly hot days
heat_wave_min_duration_hours: 6 # Significant events only
heat_wave_lookahead_hours: 24   # Full day advance notice
heat_wave_pre_action_hours: 4   # Substantial pre-cooling
heat_wave_adjustment: -2.0      # Meaningful cooling
```

### For Clear Sky (Solar Gain)

Best for buildings with:
- Large west/south-facing windows
- Poor insulation or shading
- Predictable afternoon overheating

**Recommended Settings:**
```yaml
clear_sky_condition: "sunny"     # Check your weather provider!
clear_sky_min_duration_hours: 4  # Half-day sun minimum
clear_sky_lookahead_hours: 12    # Morning detection for afternoon
clear_sky_pre_action_hours: 2    # Moderate pre-cooling
clear_sky_adjustment: -1.0       # Gentle adjustment
```

### Choosing Strategy Priority

Since only one strategy can be active:

**Heat Wave Priority** (default):
- Use when extreme heat is main concern
- Clear sky becomes backup for non-extreme sunny days

**Clear Sky Priority:**
- Use when solar gain is bigger problem than temperature
- Reorder strategies in configuration

**Single Strategy:**
- Consider using only one to avoid confusion
- Simpler to understand and tune

## Checking Weather Conditions

To find what conditions your weather integration reports:

```yaml
# In Developer Tools → Template
{{ states('weather.your_weather_entity') }}
{{ state_attr('weather.your_weather_entity', 'forecast')[0].condition }}

# Common values:
# - "sunny" (most common)
# - "clear-sky" (some integrations)  
# - "partlycloudy" (not ideal for clear_sky strategy)
# - "cloudy", "rainy", etc.
```

## Important Limitations

1. **No Continuous Adjustment:** Strategies only pre-cool, they don't maintain special offsets during events

2. **Single Strategy Active:** Cannot combine heat_wave and clear_sky simultaneously

3. **Configuration Validation:** Currently allows invalid mathematical combinations (Issue #69)

4. **Pre-cooling Only Design:** Some users might expect continued aggressive cooling during events

## How Weather Strategies Work With ML Learning

**Important:** Weather strategy offsets do NOT poison ML training data!

- ML learns from actual sensor readings (room, AC, outdoor temps)
- Weather adjustments applied AFTER ML offset calculation  
- Training data remains clean and reflects true thermal behavior
- Strategies are temporary overlays, not part of learned model

## Troubleshooting

### Strategy Never Activates

Check:
1. Lookahead >= pre_action + min_duration (mathematical requirement)
2. Weather entity is working and has forecast data
3. Conditions match exactly (e.g., "sunny" not "clear")
4. Thresholds are achievable in your climate

### Unexpected Deactivation

Remember:
- Strategies expire when weather event STARTS
- Only one strategy active at a time
- First matching strategy wins

### No Effect During Heat Wave

This is by design:
- Pre-cooling happens BEFORE heat wave
- Normal operation DURING heat wave (with tighter bands)
- Relies on pre-cooled thermal mass

## Future Improvements

Potential enhancements being considered:

1. **Continuous strategies:** Maintain offsets during events
2. **Strategy stacking:** Combine multiple strategies
3. **Dynamic priority:** Override active strategy if more severe detected
4. **Validation:** Prevent invalid configurations (Issue #69)

---

*For more information, see the [Smart Climate documentation](https://github.com/VectorBarks/smart-climate)*