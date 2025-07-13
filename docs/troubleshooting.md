# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with Smart Climate Control.

## Quick Diagnostics

### Integration Health Check

1. **Check Entity Status**: 
   - Go to Developer Tools → States
   - Search for your Smart Climate entity
   - Verify it's not "unavailable" or "unknown"

2. **Review Logs**:
   - Settings → System → Logs
   - Filter by "smart_climate"
   - Look for ERROR or WARNING messages

3. **Verify Dependencies**:
   - Ensure wrapped climate entity is working
   - Check room sensor is providing values
   - Confirm Home Assistant version compatibility

## Common Issues and Solutions

### Installation Issues

#### Integration Not Found After Installation

**Symptoms**: Can't find "Smart Climate Control" when adding integration

**Solutions**:
1. Verify correct file placement:
   ```
   custom_components/
   └── smart_climate/
       ├── __init__.py
       ├── climate.py
       ├── manifest.json
       └── (other files)
   ```

2. Check file permissions - Home Assistant must be able to read files

3. Clear browser cache and restart Home Assistant:
   ```yaml
   # SSH/Terminal
   ha core restart
   ```

4. Check logs for import errors:
   ```
   ERROR (MainThread) [homeassistant.loader] Error loading custom_components.smart_climate
   ```

#### Configuration Fails

**Symptoms**: Error during configuration flow

**Solutions**:
1. Verify entity IDs are correct (case-sensitive)
2. Ensure selected entities exist and are functional
3. Check that temperature sensors provide numeric values:
   ```yaml
   # Developer Tools → Template
   {{ states('sensor.room_temperature') | float }}
   ```
4. **v1.1.0+**: Default target temperature is now configurable (16-30°C range)
   - If seeing unexpected default temperatures, check configuration
   - Default is 24°C if not specified

### Operational Issues

#### Offset Seems Incorrect

**Symptoms**: Room temperature doesn't match target, offset appears wrong

**Diagnostic Steps**:
1. Enable debug logging:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.smart_climate: debug
   ```

2. Monitor offset calculations in logs:
   ```
   DEBUG: Offset calculation: room=22.5°C, internal=20.8°C, offset=-1.7°C
   ```

3. Check sensor accuracy:
   - Compare sensors with a reference thermometer
   - Verify sensor placement (see [Sensor Guide](sensors.md))

**Solutions**:
- Calibrate sensors if readings are inaccurate
- Adjust sensor placement away from heat sources/drafts
- Use manual override temporarily while investigating
- Allow learning system time to adapt (if enabled)

#### Temperature Not Reaching Target

**Symptoms**: System runs but doesn't achieve desired temperature

**Possible Causes**:
1. **Undersized AC unit**: Can't overcome heat load
2. **Poor sensor placement**: Incorrect temperature readings
3. **Offset limits**: Max offset might be constraining
4. **AC limitations**: Unit's own limits preventing operation

**Solutions**:
- Increase max_offset in configuration (default 5°C)
- Check if AC is actually reaching its setpoint
- Verify sensor placement represents room average
- Consider using Boost mode temporarily
- Check for heat sources affecting readings

#### Learning Not Improving

**Symptoms**: Learning enabled but predictions remain poor

**Diagnostic Steps**:
1. Check learning statistics:
   ```yaml
   # Developer Tools → States
   # Find: switch.your_climate_learning
   # Check attributes for samples_collected, accuracy
   # New in v1.1.0: last_feedback_timestamp shows when last learning occurred
   ```

2. Verify feedback collection in logs:
   ```
   DEBUG: Learning feedback collected: predicted=2.0°C, actual=2.3°C
   ```

3. Ensure consistent operation patterns

**Solutions**:
- Allow more time (minimum 48-72 hours)
- Check feedback_delay matches your AC response time
- Ensure sensors remain stable and available
- Avoid frequent manual overrides during learning
- Verify offset is actually being applied (non-zero)

#### AC Overcooling During Learning Phase

**Symptoms**: AC cools room well below target temperature during initial learning period

**Real Example**: 
- Room temperature: 24.6°C
- Target temperature: 25°C
- AC internal sensor: 20.8°C
- Smart Climate sets AC to: 20.6°C (trying to compensate)
- Result: Room becomes too cold as AC runs continuously

**Why This Happens**:

The Smart Climate system detects a large difference between your room sensor (24.6°C) and the AC's internal sensor (20.8°C) - nearly 4°C difference. To compensate, it applies an aggressive negative offset, setting the AC even lower (20.6°C) thinking this will help reach the target.

However, this creates a "chicken-and-egg" problem:
- The AC can't reach such a low temperature (20.6°C is extremely cold)
- Because it can't reach the setpoint, it never turns off
- Since it never cycles off, the HysteresisLearner can't learn the AC's behavior
- Without learning data, the system can't optimize its approach

**This is Normal and Temporary**

Don't worry - this behavior is expected during the initial learning phase when there's a large sensor discrepancy. The system will gradually learn and improve once it collects enough data.

**Practical Solutions**:

1. **Temporary Manual Control** (Recommended for first 24-48 hours):
   ```yaml
   # Use manual override to set a reasonable offset
   service: smart_climate.set_manual_offset
   target:
     entity_id: climate.your_smart_ac
   data:
     offset: -2  # Start with a smaller offset
     duration: 1440  # 24 hours
   ```

2. **Adjust Learning Parameters**:
   - Increase `min_offset` to prevent extreme compensations (e.g., -3°C instead of -5°C)
   - Reduce `learning_rate` to make adjustments more gradual
   - Decrease `update_interval` to allow more frequent corrections

3. **Help the System Learn**:
   - Manually set the AC to a reachable temperature (e.g., 22-23°C)
   - Let it run until the room reaches your target
   - Turn it off manually when comfortable
   - Repeat this cycle several times to generate learning data

4. **Use Power Monitoring** (Best long-term solution):
   - Configure a power sensor for your AC
   - This enables HysteresisLearner to detect on/off cycles even without temperature cycling
   - The system will learn optimal temperatures within a few days

**What NOT to Do**:

- **Don't use Boost Mode**: This makes the problem worse by setting even lower temperatures
- **Don't use Night/Sleep Mode**: These apply positive offsets, making the room warmer
- **Don't constantly adjust the target**: Let the system stabilize with one target temperature
- **Don't disable learning**: The system needs to learn to improve

**Timeline for Improvement**:

- **Day 1-2**: May experience overcooling, use manual overrides as needed
- **Day 3-5**: System begins learning patterns, overcooling reduces
- **Week 1-2**: HysteresisLearner (if power sensor configured) optimizes thresholds
- **Week 2+**: System should maintain comfortable temperatures automatically

**Monitor Progress**:

Check the learning switch attributes to see improvement:
```yaml
# Developer Tools → States → switch.your_climate_learning
samples_collected: 156  # Should increase over time
current_accuracy: 0.72  # Should improve toward 1.0
hysteresis_state: "learning_hysteresis"  # Shows learning progress
```

**When to Be Concerned**:

If after 1 week you still experience severe overcooling:
1. Verify your sensors are accurate (compare with a thermometer)
2. Check that the AC's internal sensor isn't faulty
3. Consider if the AC unit is oversized for your room
4. Review debug logs for any error patterns
5. Reset training data and try with adjusted parameters

Remember: The learning system is designed to handle these scenarios. Give it time to adapt to your specific AC's behavior and sensor characteristics.

#### AC Heating When It Should Cool

**Symptoms**: AC set to higher temperature when room is warmer than target

**Example**: Room 25.3°C, target 24.5°C, but AC set to 28.5°C

**Root Cause**: Learning system recorded inverted offsets (fixed in v1.1.0)

**Solutions**:
- Update to latest version (v1.1.0 or later)
- Reset training data after update using reset button
- Check logs confirm negative offsets when cooling:
  ```
  DEBUG: Learning feedback: predicted=-2.0°C, actual=-2.3°C
  ```

#### Learning Samples Reset to Zero

**Symptoms**: samples_collected shows 0 after HA restart despite previous learning

**Root Cause**: Sample count synchronization issue (fixed in v1.1.0)

**Solutions**:
- Update to latest version
- Check logs for synchronization messages:
  ```
  WARNING: Sample count mismatch detected: stored=0, actual enhanced samples=150. Using actual count.
  ```
- Learning data is preserved, only display was incorrect

#### Hysteresis State Shows "no_power_sensor"

**Symptoms**: Power sensor configured but hysteresis_state shows "no_power_sensor"

**Root Cause**: State detection logic issue (fixed in v1.1.0)

**Solutions**:
- Update to latest version
- During initial learning, should show "learning_hysteresis"
- After sufficient data, shows actual states: "active_phase", "idle_stable_zone", etc.

#### HysteresisLearner Not Detecting AC Cycles

**Symptoms**: Power sensor configured but no hysteresis learning occurring

**Diagnostic Steps**:
1. Check power sensor readings:
   ```yaml
   # Developer Tools → States
   # Verify sensor shows distinct values when AC is on/off
   sensor.ac_power → should show ~0W idle, >min_power when active
   ```

2. Verify power thresholds in configuration:
   ```yaml
   # Check learning switch attributes
   switch.your_climate_learning → power_idle, power_min thresholds
   ```

3. Monitor power transitions in logs:
   ```
   DEBUG: Power transition detected: 5W → 950W (transition to active)
   ```

**Solutions**:
- Ensure power_min is set above idle consumption (default 100W)
- Adjust power_idle to match your AC's standby power (default 50W)
- Allow at least 10 power transitions for initial learning
- Check that AC actually cycles (not running continuously)

#### HysteresisLearner Predictions Seem Wrong

**Symptoms**: AC starts/stops at unexpected temperatures

**Diagnostic**:
Check learned thresholds in learning switch attributes:
```yaml
hysteresis_thresholds:
  start_temp_internal: 23.5
  stop_temp_internal: 22.8
```

**Solutions**:
- Reset training data if thresholds are clearly wrong
- Ensure consistent AC operation during learning phase
- Avoid manual temperature changes during initial learning
- Allow system to observe multiple complete cooling cycles

### Sensor Issues

#### Room Sensor Unavailable

**Symptoms**: Climate shows no current temperature

**Impact**: No offset calculations possible

**Solutions**:
1. Check sensor battery (if applicable)
2. Verify network connectivity (WiFi/Zigbee/Z-Wave)
3. Check parent integration (e.g., Zigbee2MQTT)
4. Look for sensor-specific errors in logs
5. Create sensor automation to alert on failures

#### Erratic Sensor Readings

**Symptoms**: Temperature jumps wildly, unrealistic values

**Solutions**:
1. Add sensor filtering:
   ```yaml
   sensor:
     - platform: filter
       name: "Filtered Temperature"
       entity_id: sensor.raw_temperature
       filters:
         - filter: outlier
           window_size: 3
           radius: 2.0
   ```

2. Check for interference:
   - Move sensor away from electronics
   - Verify stable power supply
   - Check wireless signal strength

3. Consider sensor replacement if issues persist

### Mode and Control Issues

#### Preset Modes Not Working

**Symptoms**: Selecting modes doesn't change behavior

**Diagnostic**:
```yaml
# Check current mode in Developer Tools → States
climate.your_smart_ac → preset_mode attribute
```

**Solutions**:
1. Verify mode configuration in YAML/UI
2. Check if wrapped climate entity is responding
3. Review logs for mode change events
4. Ensure mode-specific settings are configured

#### Manual Override Not Releasing

**Symptoms**: Manual offset continues past duration

**Solutions**:
1. Set override duration to 0 to force release
2. Check if entity was restarted during override
3. Review automation conflicts
4. Verify timer functionality in logs

### Performance Issues

#### Slow Response Times

**Symptoms**: Delays in temperature adjustments

**Solutions**:
1. Reduce update_interval (default 180s):
   ```yaml
   smart_climate:
     update_interval: 120  # Faster updates
   ```

2. Check Home Assistant performance:
   - CPU usage
   - Memory availability
   - Database size

3. Verify wrapped climate entity responsiveness

#### High Resource Usage

**Symptoms**: Increased CPU/memory after installing

**Solutions**:
1. Check number of Smart Climate entities
2. Review update intervals (longer = less resource use)
3. Disable learning if not needed
4. Check for automation loops

## Advanced Troubleshooting

### Enable Comprehensive Debug Logging

```yaml
logger:
  default: info
  logs:
    custom_components.smart_climate: debug
    custom_components.smart_climate.offset_engine: debug
    custom_components.smart_climate.sensor_manager: debug
    custom_components.smart_climate.coordinator: debug
    custom_components.smart_climate.lightweight_learner: debug
    custom_components.smart_climate.hysteresis_learner: debug
```

### Key Log Messages to Understand

**Normal Operation**:
```
INFO: Setting up Smart Climate for climate.living_room_ac
DEBUG: Room temp: 22.5°C, Internal: 20.8°C, Offset: -1.7°C
INFO: Applying temperature 20.3°C to wrapped entity
```

**Learning System**:
```
DEBUG: Learning enabled, collecting feedback in 45 seconds
INFO: Learning feedback: predicted=2.0°C, actual=2.3°C, error=0.3°C
DEBUG: Updating patterns: samples=156, accuracy=0.89
```

**HysteresisLearner (v1.1.0+)**:
```
DEBUG: Power transition detected: 0W → 950W (transition to active)
INFO: HysteresisLearner: Learning AC start threshold at 25.3°C (internal: 23.8°C)
DEBUG: HysteresisLearner state: learning_hysteresis (7/10 transitions)
INFO: HysteresisLearner: Thresholds learned - Start: 25.2°C, Stop: 24.1°C
```

**Error Conditions**:
```
WARNING: Room sensor unavailable, cannot calculate offset
ERROR: Failed to update wrapped entity: Service call failed
WARNING: Learning data corruption detected, resetting
```

### Database Queries

Check historical data:
```sql
-- In Developer Tools → SQL
SELECT * FROM states 
WHERE entity_id = 'climate.your_smart_ac' 
ORDER BY created DESC 
LIMIT 10;
```

### Test Offset Calculations

Use Developer Tools → Services:
```yaml
service: climate.set_temperature
target:
  entity_id: climate.your_smart_ac
data:
  temperature: 22
```

Then check logs for offset application.

## Recovery Procedures

### Reset Learning Data

If learning data is corrupted:

1. Turn off learning switch
2. Delete persistence file:
   ```bash
   rm .storage/smart_climate_learning_*.json
   ```
3. Restart Home Assistant
4. Re-enable learning

### Full Integration Reset

For complete reset:

1. Remove integration from UI
2. Delete from YAML (if configured there)
3. Restart Home Assistant
4. Re-add integration
5. Reconfigure settings

### Emergency Bypass

To temporarily bypass Smart Climate:

1. Use Developer Tools to control wrapped entity directly
2. Or create automation:
   ```yaml
   automation:
     - alias: "Emergency AC Control"
       trigger:
         - platform: state
           entity_id: input_boolean.emergency_ac_bypass
           to: 'on'
       action:
         - service: climate.set_temperature
           target:
             entity_id: climate.actual_ac  # Wrapped entity
           data:
             temperature: 22
   ```

## Getting Help

### Before Requesting Help

1. **Collect Information**:
   - Home Assistant version
   - Integration version
   - Climate device model
   - Sensor types and models
   - Configuration (sanitized)
   - Relevant log entries
   - Steps to reproduce issue

2. **Try Basic Fixes**:
   - Restart Home Assistant
   - Check all entities are available
   - Verify configuration
   - Review this guide

### Where to Get Help

**GitHub Issues**: For bugs and feature requests
- Search existing issues first
- Use issue templates
- Provide all requested information

**GitHub Discussions**: For questions and community help
- Share your setup details
- Describe what you've tried
- Include relevant logs

**Home Assistant Community**: For general discussion
- Forum category: Custom Integrations
- Discord: #custom-components channel

### Diagnostic Information Template

When reporting issues, include:

```markdown
**System Information**
- Home Assistant: 2024.1.0
- Smart Climate: 1.1.0
- Installation method: HACS/Manual
- Python: 3.11

**Configuration**
```yaml
smart_climate:
  - name: "Living Room"
    climate_entity: climate.living_ac
    room_sensor: sensor.room_temp
    # ... other settings
```

**Issue Description**
[Clear description of the problem]

**Expected Behavior**
[What should happen]

**Actual Behavior**
[What actually happens]

**Steps to Reproduce**
1. [First step]
2. [Second step]
3. [etc.]

**Logs**
```
[Relevant log entries]
```

**Additional Context**
[Any other relevant information]
```

## Preventive Maintenance

### Regular Checks

**Weekly**:
- Verify sensors are reporting correctly
- Check offset calculations seem reasonable
- Monitor learning progress (if enabled)

**Monthly**:
- Review system accuracy
- Check for integration updates
- Verify sensor calibration
- Clean/maintain physical sensors

**Seasonally**:
- Adjust temperature limits if needed
- Consider clearing old learning data
- Update mode-specific offsets
- Review energy usage patterns

### Monitoring Automations

Create automations to catch issues early:

```yaml
automation:
  - alias: "Monitor Smart Climate Health"
    trigger:
      - platform: state
        entity_id: climate.smart_ac
        to: 'unavailable'
        for: '00:05:00'
    action:
      - service: notify.mobile_app
        data:
          title: "Smart Climate Alert"
          message: "Smart AC is unavailable"
          
  - alias: "Sensor Accuracy Check"
    trigger:
      - platform: time
        at: "12:00:00"
    condition:
      - condition: template
        value_template: >
          {% set room = states('sensor.room_temp') | float %}
          {% set internal = state_attr('climate.wrapped_ac', 'current_temperature') | float %}
          {{ (room - internal) | abs > 10 }}
    action:
      - service: persistent_notification.create
        data:
          title: "Sensor Discrepancy"
          message: "Large difference between room and AC sensors"
```

## v1.3.0 Advanced Features Troubleshooting

### Adaptive Feedback Delays Issues

#### Adaptive Delays Not Learning

**Symptoms**: Learned delay stays at default value, no learning progress

**Diagnostic Steps**:
1. Check if feature is enabled:
   ```yaml
   # In entity attributes
   adaptive_delay: true
   adaptive_delay_learned: null  # Should show learned value after cycles
   ```

2. Enable debug logging:
   ```yaml
   logger:
     logs:
       custom_components.smart_climate.delay_learner: debug
   ```

3. Monitor learning cycle triggers:
   ```
   DEBUG: DelayLearner: Starting learning cycle for climate.ac
   DEBUG: DelayLearner: Temperature stabilized after 47 seconds
   DEBUG: DelayLearner: Updated learned delay: 45s → 48s
   ```

**Common Causes & Solutions**:

- **No HVAC Mode Changes**: Learning only triggers on mode changes
  - *Solution*: Turn AC on/off or change modes to trigger learning
  
- **Temperature Sensor Updates Too Slow**: Need updates every 1-2 minutes
  - *Solution*: Check sensor update frequency, consider different sensor
  
- **Very Stable Environment**: Temperature never varies enough to detect stabilization
  - *Solution*: May need to manually trigger mode changes initially
  
- **Learning Timeout**: Cycles timing out after 10 minutes
  - *Solution*: Check for external temperature influences, sensor placement

#### Learned Delays Seem Wrong

**Symptoms**: Learned delays much shorter/longer than expected

**Diagnostic Steps**:
1. Check current learned value:
   ```yaml
   # Entity attributes
   adaptive_delay_learned: 65  # seconds
   ```

2. Compare with manual timing:
   - Change AC temperature manually
   - Time how long until temperature reading stabilizes
   - Should match learned delay ± 5-10 seconds

**Solutions**:
- **Too Short**: May indicate rapid sensor response but slow AC response
  - Check sensor placement relative to AC vents
- **Too Long**: May indicate slow sensor or external influences
  - Verify sensor isn't affected by drafts, sunlight, etc.

### Weather Forecast Integration Issues

#### Weather Predictions Not Working

**Symptoms**: No predictive offsets applied, weather strategies inactive

**Diagnostic Steps**:
1. Verify weather entity configuration:
   ```yaml
   # Developer Tools → Services
   service: weather.get_forecasts
   data:
     entity_id: weather.home
     type: hourly
   ```

2. Check forecast data format:
   ```json
   {
     "forecast": [
       {
         "datetime": "2025-07-13T14:00:00+00:00",
         "temperature": 32.5,
         "condition": "sunny"
       }
     ]
   }
   ```

3. Enable debug logging:
   ```yaml
   logger:
     logs:
       custom_components.smart_climate.forecast_engine: debug
   ```

4. Monitor strategy evaluation:
   ```
   DEBUG: ForecastEngine: Evaluating heat_wave strategy
   DEBUG: ForecastEngine: Found 4 consecutive hours above 30°C
   DEBUG: ForecastEngine: Activating heat_wave strategy with -1.0°C adjustment
   ```

**Common Causes & Solutions**:

- **Weather Entity Not Found**: Entity ID incorrect or integration not configured
  - *Solution*: Verify weather integration is working, check entity ID spelling
  
- **No Hourly Forecasts**: Some weather integrations only provide daily forecasts
  - *Solution*: Use weather integration that provides hourly data (OpenWeatherMap, etc.)
  
- **Forecast Triggers Not Met**: Strategy conditions too restrictive
  - *Solution*: Adjust trigger_temp, trigger_duration to match local climate
  
- **API Rate Limiting**: Forecast updates throttled to 30 minutes
  - *Solution*: Normal behavior, wait for next update cycle

#### Weather Strategies Not Activating

**Symptoms**: Conditions met but no strategy activated

**Diagnostic Steps**:
1. Check strategy configuration:
   ```yaml
   forecast_strategies:
     - type: "heat_wave"
       enabled: true  # Must be true
       trigger_temp: 30.0
       trigger_duration: 3
   ```

2. Verify trigger conditions:
   - Check actual forecast temperatures against trigger_temp
   - Confirm consecutive hours meet trigger_duration
   - Verify current time falls within any time_range restrictions

3. Check entity attributes:
   ```yaml
   # Should show active strategy
   forecast_active_strategy: "heat_wave"
   forecast_next_update: "2025-07-13T15:30:00"
   ```

**Solutions**:
- **Strategy Disabled**: Check `enabled: true` in configuration
- **Trigger Too High**: Lower trigger_temp for your climate
- **Duration Too Long**: Reduce trigger_duration hours required
- **Time Restrictions**: Remove or adjust time_range if strategy has one

### Seasonal Adaptation Issues

#### Seasonal Learning Not Active

**Symptoms**: No seasonal patterns learned, outdoor temperature not considered

**Diagnostic Steps**:
1. Verify outdoor sensor configuration:
   ```yaml
   outdoor_sensor: sensor.outdoor_temperature
   seasonal_learning: true  # Should be auto-enabled
   ```

2. Check outdoor sensor data:
   ```yaml
   # Developer Tools → States
   sensor.outdoor_temperature: 28.5  # Must be numeric
   ```

3. Monitor pattern collection:
   ```yaml
   # Entity attributes
   seasonal_patterns_count: 15  # Number of patterns learned
   seasonal_current_bucket: "25-30°C"  # Current temperature bucket
   ```

4. Enable debug logging:
   ```yaml
   logger:
     logs:
       custom_components.smart_climate.seasonal_learner: debug
   ```

**Common Causes & Solutions**:

- **Outdoor Sensor Invalid**: Sensor not providing numeric values
  - *Solution*: Check sensor entity, ensure it reports temperature as number
  
- **Insufficient Data**: Need 3+ samples per temperature bucket (5°C ranges)
  - *Solution*: Allow more time for data collection during AC operation
  
- **Seasonal Learning Disabled**: Explicitly disabled in configuration
  - *Solution*: Enable via UI or set `seasonal_learning: true`
  
- **Temperature Range Too Narrow**: All patterns fall in same bucket
  - *Solution*: Normal in stable climates, system will still learn general patterns

#### Seasonal Patterns Not Improving Accuracy

**Symptoms**: Seasonal adaptation enabled but no accuracy improvement

**Diagnostic Steps**:
1. Check pattern distribution:
   ```yaml
   # In debug logs
   DEBUG: SeasonalLearner: Current bucket 25-30°C has 5 patterns
   DEBUG: SeasonalLearner: Using median delta: 2.3°C
   ```

2. Verify outdoor temperature varies enough:
   - Need patterns across different outdoor temperature ranges
   - Single temperature bucket won't show seasonal differences

3. Monitor pattern usage:
   - Patterns should be retrieved based on current outdoor temperature
   - Check if fallback to general patterns is being used

**Solutions**:
- **Limited Temperature Range**: Normal in stable climates, benefits may be subtle
- **Insufficient Time**: Need data across seasonal temperature variations
- **Pattern Pruning**: Old patterns automatically pruned after 45 days, may reduce data

### Performance and Resource Issues

#### High CPU Usage

**Symptoms**: Home Assistant performance impact with v1.3.0 features

**Diagnostic Steps**:
1. Monitor update intervals:
   ```yaml
   # Reduce update frequency if needed
   update_interval: 300  # 5 minutes instead of 3
   ```

2. Check debug logging impact:
   ```yaml
   # Disable debug logs in production
   logger:
     logs:
       custom_components.smart_climate: info
   ```

**Solutions**:
- **Disable Unused Features**: Turn off adaptive_delay, weather integration if not needed
- **Increase Update Intervals**: Less frequent updates reduce CPU load
- **Disable Debug Logging**: Only enable for troubleshooting

#### Storage Space Issues

**Symptoms**: Growing storage usage from learned patterns

**Diagnostic Steps**:
1. Check pattern retention:
   ```yaml
   data_retention_days: 45  # Default for seasonal
   # Standard learning uses 30-60 days
   ```

2. Monitor storage usage in logs:
   ```
   DEBUG: SeasonalLearner: Pruned 15 old patterns, 45 remaining
   ```

**Solutions**:
- **Reduce Retention Period**: Lower data_retention_days if storage is limited
- **Pattern Pruning**: System automatically prunes old data

### Integration Compatibility Issues

#### Conflicts with Other Integrations

**Symptoms**: Weather/climate integrations not working together

**Solutions**:
- **Multiple Weather Entities**: Use different weather entity IDs
- **Climate Entity Conflicts**: Don't wrap the same climate entity multiple times
- **Sensor Conflicts**: Ensure sensor entities are unique per Smart Climate instance

## Advanced Debugging Techniques

### Complete Debug Configuration
```yaml
logger:
  default: info
  logs:
    # Core components
    custom_components.smart_climate: debug
    custom_components.smart_climate.offset_engine: debug
    custom_components.smart_climate.climate: debug
    
    # v1.3.0 features
    custom_components.smart_climate.delay_learner: debug
    custom_components.smart_climate.forecast_engine: debug
    custom_components.smart_climate.seasonal_learner: debug
    
    # Data persistence  
    custom_components.smart_climate.data_store: debug
    custom_components.smart_climate.coordinator: debug
```

### Log Analysis Commands
```bash
# Filter Smart Climate logs
grep "smart_climate" home-assistant.log

# Monitor real-time Smart Climate activity
tail -f home-assistant.log | grep "smart_climate"

# Check for specific v1.3.0 feature activity
grep -E "(DelayLearner|ForecastEngine|SeasonalLearner)" home-assistant.log
```

### Performance Monitoring
```yaml
# Monitor update timing
DEBUG: SmartClimateCoordinator: Update completed in 2.3ms
DEBUG: OffsetEngine: Calculation completed in 0.8ms
DEBUG: DelayLearner: Temperature check completed in 0.1ms
```

### Entity State Inspection
Use Developer Tools → States to monitor these diagnostic attributes:
```yaml
# Core diagnostics
current_offset: -1.2
confidence_level: 0.85
sample_count: 142
calibration_status: "active_learning"

# v1.3.0 diagnostics
adaptive_delay_learned: 52
adaptive_delay_learning: false
forecast_active_strategy: "heat_wave"
forecast_next_update: "2025-07-13T15:30:00"
seasonal_patterns_count: 28
seasonal_current_bucket: "30-35°C"
```

## Conclusion

Most issues with Smart Climate Control v1.3.0 can be resolved by:
1. Verifying sensor accuracy and regular updates
2. Ensuring proper configuration of new features
3. Allowing sufficient time for learning systems to collect data
4. Checking logs for specific errors and warnings
5. Understanding feature requirements and limitations

The v1.3.0 features are designed to be optional and backward-compatible. If experiencing issues, features can be disabled individually while troubleshooting.

For persistent issues not covered here, please check the [GitHub repository](https://github.com/VectorBarks/smart-climate) for updates and community support.