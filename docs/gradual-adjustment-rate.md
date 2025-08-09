# Gradual Adjustment Rate Guide

## Overview

The gradual adjustment rate is a critical parameter that controls how aggressively Smart Climate Control adjusts your AC's target temperature. This guide helps you choose the optimal rate for your specific needs.

## What Is Gradual Adjustment Rate?

The gradual adjustment rate determines the **maximum temperature change** Smart Climate can apply to your AC's setpoint during each update cycle (default: every 180 seconds). This creates smooth, controlled temperature transitions rather than abrupt changes.

### Key Concepts

- **Update Interval**: How often Smart Climate recalculates (default: 180 seconds)
- **Adjustment Rate**: Maximum °C change per update (0.1 to 2.0°C)
- **Effective Speed**: Rate × Updates per hour = Maximum hourly change

Example: 0.5°C rate × 20 updates/hour = 10°C/hour maximum change

## Understanding Rate Impact

### Visual Comparison

For a scenario where room is 26°C and target is 24°C (2°C difference):

```
Rate 1.0°C:  ████████████████████ (6 min)
Rate 0.5°C:  ██████████ (12 min)
Rate 0.25°C: █████ (24 min)
Rate 0.1°C:  ██ (60 min)
```

### Detailed Rate Analysis

#### 1.0°C - Aggressive Rate
- **Speed**: Reaches target in 6-10 minutes
- **Behavior**: Large, noticeable temperature jumps
- **Energy**: Higher consumption, more overshoot
- **Comfort**: Quick relief but possible discomfort from rapid changes
- **AC Wear**: Higher stress on compressor from large swings

#### 0.5°C - Balanced Rate (Default)
- **Speed**: Reaches target in 12-20 minutes
- **Behavior**: Moderate, predictable adjustments
- **Energy**: Good efficiency with acceptable response time
- **Comfort**: Balanced between speed and stability
- **AC Wear**: Normal operating conditions

#### 0.25°C - Gentle Rate
- **Speed**: Reaches target in 25-40 minutes
- **Behavior**: Smooth, barely noticeable changes
- **Energy**: High efficiency, minimal overshoot
- **Comfort**: Very stable, no sudden changes
- **AC Wear**: Reduced cycling extends lifespan

#### 0.1°C - Ultra-Gentle Rate
- **Speed**: Reaches target in 60+ minutes
- **Behavior**: Imperceptible micro-adjustments
- **Energy**: Maximum efficiency, zero overshoot
- **Comfort**: Rock-stable temperature
- **AC Wear**: Minimal stress, maximum longevity

## Room-Specific Recommendations

### Bedrooms
**Recommended Rate**: 0.1 - 0.3°C
```yaml
gradual_adjustment_rate: 0.2
```
**Why**: Sleep quality requires stable temperatures. Slow adjustments prevent waking from temperature changes.

**Considerations**:
- Night-time body temperature naturally drops
- Covers trap heat differently throughout night
- Partner preferences may differ
- Lower rates = better sleep

### Living Rooms
**Recommended Rate**: 0.4 - 0.6°C
```yaml
gradual_adjustment_rate: 0.5  # Default
```
**Why**: Balance between comfort and responsiveness for varied activities.

**Considerations**:
- Multiple occupants with different preferences
- Variable heat from TV, lighting, cooking
- Day/night usage patterns differ
- Need reasonable response to activity changes

### Kitchens
**Recommended Rate**: 0.7 - 1.2°C
```yaml
gradual_adjustment_rate: 1.0
```
**Why**: Rapid heat generation from cooking requires quick response.

**Considerations**:
- Stove/oven create sudden heat spikes
- Steam and humidity affect perceived temperature
- Short occupancy during cooking
- Need quick recovery after cooking

### Home Offices
**Recommended Rate**: 0.2 - 0.4°C
```yaml
gradual_adjustment_rate: 0.3
```
**Why**: Stable temperature improves focus and productivity.

**Considerations**:
- Computer equipment generates steady heat
- Sedentary work makes temperature changes noticeable
- Long continuous occupancy
- Consistent comfort improves concentration

### Sunrooms/Conservatories
**Recommended Rate**: 0.8 - 1.5°C
```yaml
gradual_adjustment_rate: 1.2
```
**Why**: Extreme solar heat gain requires aggressive response.

**Considerations**:
- Rapid temperature swings with sun angle
- Poor insulation typical
- Large glass areas amplify heat changes
- May need different day/night settings

## AC Type Considerations

### Inverter/Variable Speed ACs
**Recommended Rate**: 0.1 - 0.4°C
- Designed for continuous micro-adjustments
- Most efficient with small changes
- Quieter operation with gentle rates
- Energy savings maximized

### Traditional On/Off ACs
**Recommended Rate**: 0.5 - 1.0°C
- Need larger changes to trigger cycling
- Less efficient with tiny adjustments
- Better response with decisive changes
- Avoid rates below 0.3°C

### Window Units
**Recommended Rate**: 0.6 - 1.2°C
- Simple controls need clear signals
- Limited modulation capability
- Faster rates prevent short cycling
- Consider room size vs unit capacity

### Central Systems
**Recommended Rate**: 0.3 - 0.7°C
- Multiple zones complicate response
- Ductwork adds thermal lag
- Moderate rates work best
- Account for furthest room from unit

## Environmental Factors

### Well-Insulated Rooms
- **Use Lower Rates**: 0.1 - 0.3°C
- Temperature stable naturally
- Small adjustments sufficient
- Maximum efficiency possible

### Poorly-Insulated Rooms
- **Use Higher Rates**: 0.6 - 1.2°C
- Constant heat loss/gain
- Need aggressive corrections
- Efficiency limited by structure

### High Ceiling Rooms
- **Increase Rate by 0.1-0.2°C**
- Stratification requires more correction
- Larger air volume to condition
- Heat rises away from occupants

### Multiple Windows/Doors
- **Increase Rate by 0.2-0.3°C**
- More heat transfer points
- Drafts affect temperature
- Solar gain varies by time

## Seasonal Adjustments

### Summer Cooling
- **Consider Lower Rates**: Reduce by 0.1-0.2°C
- Consistent heat load from outside
- Dehumidification improves comfort
- Prevent overcooling at night

### Winter Heating
- **Consider Higher Rates**: Increase by 0.1-0.2°C
- Heat rises and escapes
- Cold drafts need quick response
- Comfort more critical than efficiency

### Spring/Fall
- **Use Moderate Rates**: Default ±0.1°C
- Variable conditions
- May switch between heating/cooling
- Balance all factors

## Energy Impact Analysis

### Energy Savings by Rate

| Rate | Relative Energy Use | Comfort Level | Response Time |
|------|-------------------|---------------|---------------|
| 0.1°C | 70-80% (Best) | Very Stable | Very Slow |
| 0.25°C | 80-85% | Stable | Slow |
| 0.5°C | 90-95% (Baseline) | Balanced | Moderate |
| 0.75°C | 95-105% | Variable | Fast |
| 1.0°C | 105-120% (Worst) | Unstable | Very Fast |

### Cost Analysis Example

For a typical 2.5kW AC running 8 hours/day at $0.15/kWh:

- **Rate 0.1°C**: ~$0.90/day (25% savings)
- **Rate 0.5°C**: ~$1.20/day (baseline)
- **Rate 1.0°C**: ~$1.44/day (20% increase)

Annual difference: **$197 savings** (0.1°C vs 1.0°C)

## Advanced Configuration

### Time-Based Rates

Different rates for different times (requires automation):

```yaml
# Day rate - balanced for activity
automation:
  - trigger:
      platform: time
      at: "08:00:00"
    action:
      service: smart_climate.set_config
      data:
        gradual_adjustment_rate: 0.5

# Night rate - gentle for sleep
  - trigger:
      platform: time
      at: "22:00:00"
    action:
      service: smart_climate.set_config
      data:
        gradual_adjustment_rate: 0.2
```

### Occupancy-Based Rates

Adjust based on presence:

```yaml
# When occupied - responsive
gradual_adjustment_rate: 0.5

# When away - efficient
gradual_adjustment_rate: 0.1
```

### Weather-Responsive Rates

Adjust for conditions:
- **Hot days (>30°C)**: Increase rate by 0.2°C
- **Mild days (20-25°C)**: Decrease rate by 0.1°C
- **Humid days**: Increase rate by 0.1°C

## Troubleshooting

### Problem: Room Never Reaches Target
**Solution**: Increase rate by 0.2-0.3°C increments

### Problem: Temperature Overshoots Target
**Solution**: Decrease rate by 0.1-0.2°C increments

### Problem: AC Cycles Too Frequently
**Solution**: Decrease rate to create smoother transitions

### Problem: Too Slow to Respond
**Solution**: Increase rate or decrease update interval

### Problem: Energy Bills Too High
**Solution**: Lower rate to 0.1-0.3°C range

## Optimization Process

1. **Start with Default** (0.5°C)
2. **Monitor for 1 Week**
   - Track comfort complaints
   - Note response times
   - Check energy usage
3. **Adjust by ±0.1°C**
4. **Test for 3-4 Days**
5. **Repeat Until Optimal**

### Signs of Correct Rate

✅ Room reaches target without overshoot
✅ Temperature remains stable once reached
✅ AC doesn't short cycle
✅ Energy usage reasonable
✅ Occupants comfortable

### Signs Rate Too High

❌ Temperature swings past target
❌ AC turns on/off frequently
❌ Noticeable temperature changes
❌ Higher energy bills
❌ Comfort complaints about changes

### Signs Rate Too Low

❌ Takes too long to cool/heat
❌ Never quite reaches target
❌ Discomfort during temperature transitions
❌ AC runs continuously
❌ Slow response to setpoint changes

## Integration with Other Features

### With Thermal Efficiency
- Lower rates work better with thermal management
- Allows thermal model to optimize better
- Prevents fighting between systems

### With Offset Learning
- Moderate rates (0.3-0.6°C) provide clear learning signals
- Too low: Learning system can't detect changes
- Too high: Creates noise in learning data

### With Weather Forecast
- Can increase rate preemptively for heat waves
- Lower rate when mild weather predicted
- Coordinates with predictive adjustments

## Quick Reference

| Use Case | Recommended Rate | Update Interval |
|----------|-----------------|-----------------|
| Bedroom (sleep) | 0.1 - 0.2°C | 180s |
| Bedroom (day) | 0.2 - 0.3°C | 180s |
| Living Room | 0.4 - 0.6°C | 180s |
| Kitchen | 0.8 - 1.2°C | 120s |
| Office | 0.2 - 0.4°C | 180s |
| Sunroom | 1.0 - 1.5°C | 120s |
| Bathroom | 0.6 - 1.0°C | 180s |
| Basement | 0.3 - 0.5°C | 240s |
| Attic | 0.8 - 1.2°C | 180s |

## Conclusion

The gradual adjustment rate is not "one size fits all". Consider:
1. Room usage patterns
2. AC type and capabilities
3. Insulation quality
4. Comfort preferences
5. Energy saving goals

Start with the default (0.5°C) and adjust based on your specific needs. Lower rates save energy and provide stability, while higher rates offer quick response at the cost of efficiency.