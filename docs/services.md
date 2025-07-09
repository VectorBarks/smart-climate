# Services Documentation

Smart Climate Control provides several services for advanced control and management of your climate devices.

## Available Services

### smart_climate.generate_dashboard

Generates a complete visualization dashboard customized for your Smart Climate device.

**Service**: `smart_climate.generate_dashboard`

**Description**: Creates a ready-to-use dashboard YAML configuration with all necessary cards and layouts for monitoring your Smart Climate device's learning progress, offset history, and performance metrics.

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `climate_entity_id` | entity | Yes | The Smart Climate entity to generate a dashboard for |

**Example**:
```yaml
service: smart_climate.generate_dashboard
data:
  climate_entity_id: climate.living_room_smart_ac
```

**Result**: Creates a persistent notification containing complete dashboard YAML that can be copied and pasted into a new Lovelace dashboard.

**Usage**:
1. Call the service via Developer Tools → Services
2. Select your Smart Climate entity
3. Click "Call Service"
4. Copy the YAML from the notification
5. Create a new dashboard and paste the configuration

For detailed instructions, see the [Dashboard Setup Guide](dashboard-setup.md).

### climate.set_temperature

Standard climate service that works with Smart Climate entities.

**Service**: `climate.set_temperature`

**Description**: Sets the target temperature for the Smart Climate device. The integration automatically calculates and applies the necessary offset to achieve the desired room temperature.

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `entity_id` | entity | Yes | The Smart Climate entity |
| `temperature` | number | Yes | Desired room temperature in °C |
| `hvac_mode` | string | No | HVAC mode to set (cool, heat, auto) |

**Example**:
```yaml
service: climate.set_temperature
target:
  entity_id: climate.living_room_smart_ac
data:
  temperature: 22
```

**Note**: You set the desired room temperature, not the AC temperature. Smart Climate handles the offset calculation automatically.

### climate.set_preset_mode

Changes the operating mode of the Smart Climate device.

**Service**: `climate.set_preset_mode`

**Description**: Switches between different preset modes that affect how the Smart Climate device operates.

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `entity_id` | entity | Yes | The Smart Climate entity |
| `preset_mode` | string | Yes | Mode to activate: none, away, sleep, boost |

**Available Modes**:
- `none`: Normal operation with dynamic offset calculation
- `away`: Fixed temperature mode for energy savings
- `sleep`: Adds positive offset for quieter nighttime operation
- `boost`: Adds negative offset for rapid cooling

**Example**:
```yaml
service: climate.set_preset_mode
target:
  entity_id: climate.living_room_smart_ac
data:
  preset_mode: sleep
```

### climate.set_hvac_mode

Controls the HVAC operation mode.

**Service**: `climate.set_hvac_mode`

**Description**: Changes the HVAC mode of the Smart Climate device (forwarded to the wrapped climate entity).

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `entity_id` | entity | Yes | The Smart Climate entity |
| `hvac_mode` | string | Yes | HVAC mode: off, cool, heat, auto, dry, fan_only |

**Example**:
```yaml
service: climate.set_hvac_mode
target:
  entity_id: climate.living_room_smart_ac
data:
  hvac_mode: cool
```

### switch.turn_on / switch.turn_off

Controls the learning system.

**Service**: `switch.turn_on` or `switch.turn_off`

**Description**: Enables or disables the machine learning system for the Smart Climate device.

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `entity_id` | entity | Yes | The learning switch entity |

**Example**:
```yaml
# Enable learning
service: switch.turn_on
target:
  entity_id: switch.living_room_smart_ac_learning

# Disable learning
service: switch.turn_off
target:
  entity_id: switch.living_room_smart_ac_learning
```

### button.press

Resets the learning data.

**Service**: `button.press`

**Description**: Clears all collected learning data and resets the machine learning model to start fresh.

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `entity_id` | entity | Yes | The reset button entity |

**Example**:
```yaml
service: button.press
target:
  entity_id: button.living_room_smart_ac_reset_learning_data
```

**Warning**: This action cannot be undone. All learning history will be permanently deleted.

## Using Services in Automations

### Example: Temperature Schedule

Create different temperature settings throughout the day:

```yaml
automation:
  - alias: "Morning Comfort"
    trigger:
      - platform: time
        at: "06:00:00"
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.living_room_smart_ac
        data:
          temperature: 22
      - service: climate.set_preset_mode
        target:
          entity_id: climate.living_room_smart_ac
        data:
          preset_mode: none

  - alias: "Night Mode"
    trigger:
      - platform: time
        at: "22:00:00"
    action:
      - service: climate.set_preset_mode
        target:
          entity_id: climate.living_room_smart_ac
        data:
          preset_mode: sleep
```

### Example: Presence-Based Control

Automatically switch to away mode when leaving:

```yaml
automation:
  - alias: "Away Mode When Leaving"
    trigger:
      - platform: state
        entity_id: person.john
        from: "home"
        to: "not_home"
    action:
      - service: climate.set_preset_mode
        target:
          entity_id: climate.living_room_smart_ac
        data:
          preset_mode: away

  - alias: "Normal Mode When Home"
    trigger:
      - platform: state
        entity_id: person.john
        from: "not_home"
        to: "home"
    action:
      - service: climate.set_preset_mode
        target:
          entity_id: climate.living_room_smart_ac
        data:
          preset_mode: none
```

### Example: Learning Control

Enable learning only during active use:

```yaml
automation:
  - alias: "Enable Learning During Day"
    trigger:
      - platform: time
        at: "08:00:00"
    condition:
      - condition: state
        entity_id: climate.living_room_smart_ac
        state: "cool"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.living_room_smart_ac_learning

  - alias: "Disable Learning at Night"
    trigger:
      - platform: time
        at: "23:00:00"
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.living_room_smart_ac_learning
```

### Example: Dashboard Generation Automation

Automatically generate dashboard after setup:

```yaml
automation:
  - alias: "Generate Dashboard After Setup"
    trigger:
      - platform: event
        event_type: component_loaded
        event_data:
          component: smart_climate
    action:
      - delay: "00:00:30"  # Wait for entities to initialize
      - service: smart_climate.generate_dashboard
        data:
          climate_entity_id: climate.living_room_smart_ac
      - service: notify.persistent_notification
        data:
          title: "Smart Climate Dashboard Ready"
          message: "Your dashboard has been generated. Check notifications."
```

## Service Responses

### Dashboard Generation Response

The `generate_dashboard` service creates a persistent notification with:
- Complete dashboard YAML configuration
- All entity IDs properly configured
- Responsive layout for desktop and mobile
- Card configurations for both core and custom cards

### Error Handling

Services will log errors in these cases:
- Invalid entity ID provided
- Entity not available
- Invalid parameter values
- Communication errors with wrapped climate device

Check the Home Assistant logs for detailed error messages.

## Advanced Service Usage

### Using Templates

Services support Home Assistant templates for dynamic behavior:

```yaml
service: climate.set_temperature
target:
  entity_id: climate.living_room_smart_ac
data:
  temperature: >
    {% if is_state('binary_sensor.workday', 'on') %}
      22
    {% else %}
      24
    {% endif %}
```

### Multiple Entity Control

Control multiple Smart Climate devices simultaneously:

```yaml
service: climate.set_preset_mode
target:
  entity_id:
    - climate.living_room_smart_ac
    - climate.bedroom_smart_ac
    - climate.office_smart_ac
data:
  preset_mode: away
```

### Service Scripts

Create reusable scripts for common operations:

```yaml
script:
  boost_cooling:
    alias: "Boost All ACs"
    sequence:
      - service: climate.set_preset_mode
        target:
          entity_id: >
            {{ states.climate 
               | selectattr('attributes.integration', 'eq', 'smart_climate') 
               | map(attribute='entity_id') 
               | list }}
        data:
          preset_mode: boost
      - delay: "00:30:00"
      - service: climate.set_preset_mode
        target:
          entity_id: >
            {{ states.climate 
               | selectattr('attributes.integration', 'eq', 'smart_climate') 
               | map(attribute='entity_id') 
               | list }}
        data:
          preset_mode: none
```

## Best Practices

1. **Use Preset Modes**: Leverage preset modes instead of manually adjusting offsets
2. **Automate Learning**: Enable/disable learning based on occupancy and time
3. **Monitor via Dashboard**: Generate and use the dashboard for insights
4. **Test Services**: Use Developer Tools to test service calls before automation
5. **Check Logs**: Review logs when services don't work as expected

## Related Documentation

- [Configuration Guide](configuration.md) - Initial setup and options
- [Usage Guide](usage.md) - General operation instructions
- [Dashboard Setup](dashboard-setup.md) - Visualization dashboard
- [Automations Guide](usage.md#automations) - Automation examples