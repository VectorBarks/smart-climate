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

## Conclusion

Most issues with Smart Climate Control can be resolved by:
1. Verifying sensor accuracy and placement
2. Ensuring proper configuration
3. Allowing time for learning adaptation
4. Checking logs for specific errors

For persistent issues not covered here, please check the [GitHub repository](https://github.com/VectorBarks/smart-climate) for updates and community support.