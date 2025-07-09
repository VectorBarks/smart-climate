# Smart Climate Learning System Guide

This guide will help you understand and effectively train your Smart Climate system to achieve optimal comfort and efficiency. The learning system is designed to make your air conditioning smarter over time, adapting to your specific unit and environment.

## Introduction: Why Learning Matters

Traditional thermostats and climate controls rely on their internal temperature sensors, which often don't reflect the actual room temperature you experience. This mismatch leads to discomfort - your AC might think it's 22°C while you're sweating at 25°C.

Smart Climate Control solves this by:
- Learning the unique offset patterns of your AC unit
- Adapting to your room's thermal characteristics
- Improving predictions over time based on real performance
- Automatically adjusting for different times of day and conditions

The result? Your AC maintains the temperature you actually want, not just what its internal sensor reads.

## How the Learning System Works

### The Simple Concept

Think of the learning system as a personal assistant that observes patterns:

1. **Observation**: "When we set the AC to 20°C, the room actually ends up at 22°C"
2. **Pattern Recognition**: "This happens consistently in the afternoon"
3. **Prediction**: "Next time, let's set it to 18°C to actually get 22°C"
4. **Refinement**: "That worked well, let's remember this pattern"

### Two Learning Approaches

#### 1. Basic Offset Learning (Always Active)
Learns the difference between your AC's internal sensor and actual room temperature:
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

## Getting Started: Initial Setup Best Practices

### Understanding the Calibration Phase (v1.1.1-beta2+)

When you first enable learning, the system enters a **Calibration Phase** for the first 10 samples. This prevents the overcooling issues that could occur during initial learning:

- **What Happens**: The system observes your AC behavior without applying aggressive offsets
- **Stable State Detection**: Only calculates offsets when AC is idle and temperatures have stabilized
- **Smart Caching**: Uses cached "stable" offsets during active cooling to prevent feedback loops
- **Status Messages**: You'll see messages like:
  - "Calibration (Stable): Updated offset to -2.1°C. (3/10 samples)"
  - "Calibration (Active): Using cached stable offset of -2.1°C."
- **Automatic Transition**: After 10 samples, switches to full learning mode

This calibration phase is especially important if your AC has an evaporator coil sensor that shows very low temperatures (e.g., 15°C) when cooling.

### Day 1: Foundation Setup

1. **Verify Sensor Accuracy**
   - Place your room sensor at seated/standing height
   - Keep it away from direct sunlight, drafts, or heat sources
   - Ensure it updates frequently (every 1-5 minutes is ideal)

2. **Start with Learning Disabled**
   ```
   Settings → Devices & Services → Smart Climate → Your AC → Learning Switch OFF
   ```
   - Let the system run for 2-3 hours in rule-based mode
   - Verify basic operation is working correctly
   - Check that temperature adjustments are happening

3. **Enable Learning After Verification**
   - Turn on the learning switch
   - The system will show "Never" for last sample collected
   - This is normal - samples are collected after temperature changes

### First Week: Building Patterns

**Days 1-3: Let It Learn Naturally**
- Use your AC normally throughout the day
- Make temperature adjustments as you usually would
- The system will collect samples after each change
- Check the learning switch attributes to see progress:
  ```
  samples_collected: 12
  learning_accuracy: 0.65
  confidence_level: 0.40
  last_sample_collected: "2025-07-08 14:30:00"
  ```

**Days 4-7: Encourage Variety**
- Try different temperature settings
- Use the AC at different times of day
- Let it experience various outdoor conditions
- More variety = better pattern recognition

### First Month: Optimization

**Weeks 2-3: Fine-Tuning**
- Monitor the accuracy metric (aim for >0.80)
- Adjust feedback delay if needed (see below)
- Let the system experience your daily routines
- Patterns will become more refined

**Week 4: Evaluation**
- Check if comfort has improved
- Review learning metrics
- Consider resetting if patterns seem wrong
- Most users see 85-95% accuracy by now

## Training Your System Effectively

### Understanding Learning Metrics

The learning switch provides real-time insights:

```yaml
switch.living_room_ac_learning:
  samples_collected: 245        # Total learning samples
  learning_accuracy: 0.91       # How well predictions match reality (91%)
  confidence_level: 0.82        # System confidence in predictions (82%)
  patterns_learned: 18          # Distinct patterns recognized
  has_sufficient_data: true     # Enough data for reliable predictions
  enabled: true                 # Learning is active
  last_sample_collected: "2025-07-08 14:30:00"  # Most recent learning
```

**What These Mean:**
- **Samples Collected**: More samples = better learning (aim for 100+)
- **Learning Accuracy**: Historical prediction success (0.80+ is good)
- **Confidence Level**: Current prediction confidence (0.70+ is reliable)
- **Patterns Learned**: Different conditions recognized (10+ is typical)
- **Has Sufficient Data**: True when samples ≥ 10
- **Last Sample Collected**: Shows learning is actively happening

### Best Practices for Training

#### 1. Consistent Usage Patterns
The system learns from repetition:
- Use similar temperatures at similar times
- Maintain consistent comfort preferences
- Let it experience your full daily routine

#### 2. Avoid Confusing the System
- Don't make rapid temperature changes (wait 10+ minutes between)
- Avoid manual overrides during the learning phase
- Keep doors/windows closed during training
- Don't block vents or redirect airflow

#### 3. Optimal Feedback Timing

The `learning_feedback_delay` is crucial. Here's how to optimize it:

**Quick Test Method:**
1. Enable debug logging
2. Set your AC to a new temperature
3. Watch the logs for when the AC's internal sensor stabilizes
4. Set feedback delay 10-15 seconds after stabilization

**Typical Values:**
- Modern Inverter Units: 30-45 seconds
- Standard Split Systems: 45-90 seconds
- Older Units: 90-180 seconds

#### 4. Power Sensor Best Practices

If you have power monitoring:
- Ensure thresholds are set correctly (see Configuration Guide)
- The system will show "learning_hysteresis" initially
- After 5-10 power transitions, it learns your AC's behavior
- This dramatically improves prediction accuracy

### Understanding Feedback Collection

**What Happens During Feedback:**
1. You set desired temperature (e.g., 22°C)
2. System calculates and applies offset
3. Waits for feedback delay period
4. Measures actual sensor difference
5. Updates learning patterns

**Important:** The system learns offset patterns, NOT whether the room reached your desired temperature. It's learning how to translate between what you want and what to tell the AC.

## Common Training Scenarios

### Scenario 1: "My AC Overcools"

**Symptoms**: Room gets too cold, AC overshoots target

**Training Solution**:
1. Let the system observe this pattern
2. It will learn your AC tends to overcool
3. Future predictions will use smaller offsets
4. May take 10-15 cycles to fully adapt

### Scenario 2: "Different Patterns Day vs Night"

**Symptoms**: AC works well during day, poorly at night (or vice versa)

**Training Solution**:
1. Ensure learning is enabled 24/7
2. Use the AC at different times
3. System learns hourly patterns automatically
4. Night patterns separate from day patterns

### Scenario 3: "Weather Affects Performance"

**Symptoms**: AC struggles on very hot/cold days

**Training Solution**:
1. Configure outdoor temperature sensor
2. Let system experience various weather
3. Learns correlation between outdoor/indoor
4. Adjusts predictions based on weather

### Scenario 4: "Power Sensor Shows Wrong State"

**Symptoms**: Learning shows "no_power_sensor" despite having one

**Training Solution**:
1. Check power sensor is updating regularly
2. Verify power thresholds in configuration
3. Run AC and monitor actual power consumption
4. Adjust thresholds based on observations

## Advanced Training Techniques

### Accelerated Learning

To speed up initial training:
1. **Morning Session**: Set 3-4 different temperatures over 2 hours
2. **Afternoon Session**: Repeat with similar changes
3. **Evening Session**: Use your normal evening settings
4. **Result**: 20-30 samples in one day instead of 5-10

### Seasonal Adaptation

The system automatically adapts to seasons:
- Summer patterns differ from winter
- Humidity impacts are learned implicitly
- No manual seasonal adjustments needed
- Continuous learning handles transitions

### Multi-Zone Considerations

If using multiple Smart Climate instances:
- Each zone learns independently
- Different rooms can have different patterns
- Train each zone based on its usage
- Don't expect identical behavior

## Troubleshooting Learning Issues

### "Learning Seems Stuck"

**Check These First:**
1. Is the learning switch enabled?
2. Are you making temperature changes?
3. Is `last_sample_collected` updating?
4. Are all sensors working correctly?

**Solutions:**
- Make more frequent adjustments initially
- Verify feedback delay is appropriate
- Check debug logs for errors
- Consider reset if corrupted

### "Predictions Are Wrong"

**Common Causes:**
1. Insufficient training data (<50 samples)
2. Environmental changes (new furniture, seasons)
3. AC maintenance changed behavior
4. Sensor accuracy issues

**Solutions:**
- Continue training for more samples
- Reset learning after major changes
- Verify sensor calibration
- Adjust feedback delay

### "Confidence Stays Low"

**Why This Happens:**
1. Inconsistent usage patterns
2. Rapidly changing conditions
3. Sensor reliability issues
4. Too much manual override

**Solutions:**
- Use consistent temperature preferences
- Allow system to work without intervention
- Check sensor update frequency
- Maintain stable environment during training

## Frequently Asked Questions

### Q: How long until the system is fully trained?

**A:** Most users see good results within:
- 24-48 hours: Basic patterns established
- 1 week: 75-85% accuracy typical
- 2-4 weeks: Optimal performance achieved
- Ongoing: Continuous refinement

### Q: Should I reset learning seasonally?

**A:** No! The system adapts automatically. Resetting throws away valuable long-term patterns. Only reset if:
- You've replaced your AC unit
- Major room renovations
- Sensor relocation
- Corrupted learning data

### Q: Why doesn't it learn from manual overrides?

**A:** Manual overrides bypass the offset system entirely. The system can't learn from these because it doesn't know what offset would have worked. Use normal temperature adjustments for training.

### Q: Can I speed up learning?

**A:** Yes, by:
- Making more temperature changes initially
- Using varied settings throughout the day
- Ensuring sensors update frequently
- Setting appropriate feedback delay

### Q: What's the difference between accuracy and confidence?

**A:** 
- **Accuracy**: Historical measure - "How well have predictions worked overall?"
- **Confidence**: Current measure - "How sure am I about this specific prediction?"

High accuracy with low confidence might mean conditions are unusual right now.

### Q: Do I need a power sensor?

**A:** No, but it helps significantly:
- Without: Learns offset patterns (works well)
- With: Learns offset AND AC behavior (works better)
- Power monitoring adds 10-15% accuracy typically

### Q: How do I know if it's working?

**A:** Good signs include:
- Steady increase in samples_collected
- Accuracy trending upward
- Room temperature matching your settings better
- Less manual adjustment needed
- Comfort improving over time

## Tips for Success

### DO:
- ✓ Be patient - learning takes time
- ✓ Use consistent temperature preferences
- ✓ Let the system work without constant intervention
- ✓ Monitor learning metrics periodically
- ✓ Trust the process - it will improve

### DON'T:
- ✗ Reset learning frequently
- ✗ Make rapid temperature changes
- ✗ Use manual override during training
- ✗ Expect perfection immediately
- ✗ Disable learning when patterns change

## Conclusion

The Smart Climate learning system is designed to improve your comfort automatically over time. By understanding how it works and following these training guidelines, you'll achieve optimal results:

- Better temperature accuracy
- Reduced energy consumption
- Less manual adjustment needed
- Consistent comfort levels
- Adaptation to your patterns

Remember: The system is always learning and improving. What starts as a simple offset calculator becomes an intelligent climate assistant that understands your specific needs and environment.

For technical details about the learning algorithms, see the [Learning System Documentation](learning-system.md).
For configuration options, see the [Configuration Guide](configuration.md).
For troubleshooting help, see the [Troubleshooting Guide](troubleshooting.md).