# Update Interval Configuration Guide

## Overview

The update interval determines how frequently Smart Climate Control recalculates offsets and adjusts your AC's target temperature. This setting has significant impact on efficiency, comfort, and AC lifespan.

## What Is Update Interval?

The update interval (measured in seconds) controls:
- How often ML predictions are recalculated
- When temperature adjustments are applied
- Frequency of data collection for learning
- Response time to temperature changes

**Default**: 180 seconds (3 minutes)
**Range**: 30-600 seconds (0.5-10 minutes)

## Relationship with Gradual Adjustment Rate

These settings work together to determine control behavior:

```
Maximum °C/hour = (gradual_adjustment_rate × 3600) / update_interval
```

### Examples

| Update Interval | Adjustment Rate | Max Change/Hour | Behavior |
|----------------|-----------------|-----------------|----------|
| 180s | 0.5°C | 10°C/hr | Default - balanced |
| 90s | 0.2°C | 8°C/hr | Smooth - inverter optimal |
| 60s | 0.15°C | 9°C/hr | Ultra-smooth - maximum efficiency |
| 240s | 0.6°C | 9°C/hr | Sparse - traditional AC |

## AC Type Recommendations

### Inverter/Variable Speed ACs

Inverter ACs modulate compressor speed continuously and work best with frequent, small adjustments.

#### Optimal Settings
```yaml
update_interval: 90  # 1.5 minutes
gradual_adjustment_rate: 0.2  # Small steps
```

**Why this works:**
- Compressor stays at steady speed (45-55%)
- Minimal ramping up/down
- 15-25% more efficient than defaults
- Quieter operation
- Less mechanical wear

#### Alternative Configurations

**Maximum Efficiency**
```yaml
update_interval: 60
gradual_adjustment_rate: 0.15
```
- Best for: Stable environments, bedrooms
- Efficiency gain: 20-30%
- Tradeoff: Slower response

**Balanced Performance**
```yaml
update_interval: 120
gradual_adjustment_rate: 0.3
```
- Best for: Living rooms, variable occupancy
- Efficiency gain: 10-15%
- Good response with stability

### Traditional On/Off ACs

Traditional ACs cycle compressor on/off and need larger, less frequent changes.

#### Optimal Settings
```yaml
update_interval: 180  # 3 minutes (default)
gradual_adjustment_rate: 0.5  # Standard steps
```

**Why this works:**
- Prevents short cycling
- Clear on/off signals
- Reduces start/stop wear
- Acceptable efficiency

#### Alternative Configurations

**Stable Environments**
```yaml
update_interval: 240
gradual_adjustment_rate: 0.6
```
- Best for: Well-insulated rooms
- Reduces cycling frequency
- Better for older units

**Quick Response**
```yaml
update_interval: 120
gradual_adjustment_rate: 0.6
```
- Best for: Poor insulation, kitchens
- Faster reaction to changes
- More cycling (higher wear)

### Window Units

Window units typically have simple controls and limited modulation.

#### Optimal Settings
```yaml
update_interval: 180  # 3 minutes
gradual_adjustment_rate: 0.6  # Larger steps
```

**Why this works:**
- Clear control signals
- Accounts for basic thermostat
- Prevents confusion from small changes

### Central Systems

Central AC systems have additional complexity from ductwork and multiple zones.

#### Optimal Settings
```yaml
update_interval: 240  # 4 minutes
gradual_adjustment_rate: 0.4  # Moderate steps
```

**Why this works:**
- Accounts for duct lag
- Prevents zone fighting
- Balances all rooms

## Room-Specific Configurations

### Bedrooms
Priority: Stability and quiet operation

```yaml
# For Inverter AC
update_interval: 120
gradual_adjustment_rate: 0.2

# For Traditional AC
update_interval: 240
gradual_adjustment_rate: 0.4
```

Benefits:
- Minimal temperature fluctuation
- Quieter operation at night
- Better sleep quality

### Living Rooms
Priority: Balance comfort and efficiency

```yaml
# For Inverter AC
update_interval: 90
gradual_adjustment_rate: 0.25

# For Traditional AC
update_interval: 180
gradual_adjustment_rate: 0.5
```

Benefits:
- Responsive to activity changes
- Good efficiency
- Handles multiple occupants

### Kitchens
Priority: Quick response to heat sources

```yaml
# For Inverter AC
update_interval: 60
gradual_adjustment_rate: 0.3

# For Traditional AC
update_interval: 120
gradual_adjustment_rate: 0.7
```

Benefits:
- Rapid response to cooking heat
- Prevents overheating
- Accepts higher energy use

### Home Offices
Priority: Consistent temperature for productivity

```yaml
# For Inverter AC
update_interval: 90
gradual_adjustment_rate: 0.2

# For Traditional AC
update_interval: 180
gradual_adjustment_rate: 0.3
```

Benefits:
- Stable working environment
- No distracting temperature changes
- Good efficiency

## Efficiency Analysis

### Inverter AC Comparison: 90s/0.2°C vs 180s/0.5°C (Default)

#### Energy Consumption

**Default (180s/0.5°C)**
- Compressor cycles: 30% → 70% → 30%
- Power swings: 400W → 1200W → 400W
- Average consumption: ~800W
- Efficiency losses from ramping: 8-10%

**Optimized (90s/0.2°C)**
- Compressor steady: 45-55%
- Power stable: 600-650W
- Average consumption: ~625W
- Minimal ramping losses: 2-3%

#### Cost Impact

Daily operation (8 hours, $0.15/kWh):
- Default: 6.4 kWh = $0.96/day
- Optimized: 5.0 kWh = $0.75/day
- **Savings: $0.21/day ($77/year)**

#### Efficiency Gains

| Factor | Improvement | Reason |
|--------|-------------|---------|
| Compressor efficiency | +20% | Operates in 40-60% sweet spot |
| Reduced overshoot | +10% | Catches deviations at 0.2°C vs 0.5°C |
| Less cycling loss | +5% | Steady state vs constant ramping |
| **Total** | **+15-25%** | Depending on conditions |

### Traditional AC Comparison

Traditional ACs see minimal efficiency gain from shorter intervals:
- May increase wear from frequent cycling
- Best to maintain 180-240s intervals
- Focus on appropriate adjustment rate

## Advanced Optimization

### Dynamic Interval Adjustment

Consider automations to adjust intervals based on conditions:

```yaml
# Increase frequency during high activity
automation:
  - trigger:
      platform: state
      entity_id: sensor.kitchen_motion
      to: 'on'
    action:
      service: smart_climate.set_config
      data:
        update_interval: 60

# Reduce frequency at night
  - trigger:
      platform: time
      at: "22:00:00"
    action:
      service: smart_climate.set_config
      data:
        update_interval: 240
```

### Seasonal Adjustments

**Summer (Cooling)**
- Shorter intervals during peak heat (12-6 PM)
- Longer intervals at night
- Account for solar gain patterns

**Winter (Heating)**
- Longer intervals (heat rises naturally)
- Shorter during morning warm-up
- Account for heat loss patterns

## Troubleshooting

### Problem: Temperature Overshooting
**Solution**: Decrease update interval or reduce adjustment rate

### Problem: Too Slow to Respond
**Solution**: Decrease update interval while maintaining reasonable adjustment rate

### Problem: AC Short Cycling (Traditional AC)
**Solution**: Increase update interval to 240+ seconds

### Problem: High Energy Bills (Inverter AC)
**Solution**: Decrease to 60-90s with 0.15-0.2°C rate

### Problem: Noisy Operation (Inverter AC)
**Solution**: Shorter interval with smaller rate for steady operation

## Quick Reference Table

| AC Type | Room Type | Update Interval | Adjustment Rate | Efficiency |
|---------|-----------|-----------------|-----------------|------------|
| Inverter | Bedroom | 120s | 0.2°C | ⭐⭐⭐⭐⭐ |
| Inverter | Living | 90s | 0.25°C | ⭐⭐⭐⭐ |
| Inverter | Kitchen | 60s | 0.3°C | ⭐⭐⭐ |
| Traditional | Bedroom | 240s | 0.4°C | ⭐⭐⭐⭐ |
| Traditional | Living | 180s | 0.5°C | ⭐⭐⭐ |
| Traditional | Kitchen | 120s | 0.7°C | ⭐⭐ |
| Window | Any | 180s | 0.6°C | ⭐⭐⭐ |
| Central | Any | 240s | 0.4°C | ⭐⭐⭐ |

## Best Practices

1. **Start with recommended settings** for your AC type
2. **Monitor for 1 week** before adjusting
3. **Change one parameter at a time** (interval OR rate)
4. **Document changes** and their effects
5. **Consider room usage patterns** when optimizing
6. **Account for seasonal changes** in your settings

## Mathematical Relationships

### Control Response Time

Time to reach target temperature:
```
Time (minutes) = Temperature_Difference / (Rate × 60 / Interval)
```

Example: 2°C difference, 90s interval, 0.2°C rate:
```
Time = 2 / (0.2 × 60 / 90) = 15 minutes
```

### Energy Efficiency Formula

For inverter ACs:
```
Efficiency_Loss = Base_Loss + (Ramping_Events × Ramping_Loss)
Ramping_Events = (3600 / Interval) × (Rate / 0.1)
```

Shorter intervals with smaller rates = fewer ramping events = better efficiency

### Comfort Index

Temperature stability score:
```
Stability = 1 / (Rate × sqrt(3600 / Interval))
```

Lower rate and shorter interval = higher stability score

## Integration with Other Features

### With Machine Learning
- Shorter intervals provide more training data
- But need sufficient time between samples
- Optimal: 90-180 seconds

### With Thermal Efficiency
- Thermal manager benefits from frequent updates
- Allows better state tracking
- Recommended: 60-120 seconds

### With Weather Forecast
- Longer intervals OK (weather changes slowly)
- Can extend to 240-300 seconds
- Predictive offsets compensate

## Conclusion

The optimal update interval depends on:
1. **AC type** (inverter vs traditional)
2. **Room characteristics** (insulation, heat sources)
3. **Usage patterns** (occupancy, activity)
4. **Comfort preferences** (stability vs responsiveness)
5. **Energy goals** (efficiency vs comfort)

For most users:
- **Inverter AC**: 90s/0.2°C for 15-25% efficiency gain
- **Traditional AC**: 180s/0.5°C (default) remains optimal
- **Adjust based on specific needs** using this guide

Remember: Update interval and gradual adjustment rate work together. Always consider both when optimizing your system.