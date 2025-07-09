# Dashboard Screenshot Placeholders

This document lists all screenshot placeholders used in the dashboard documentation. These images should be created when the dashboard is implemented and tested.

## Required Screenshots

### dashboard-setup.md Screenshots

1. **dashboard-blueprint-import.png**
   - Shows: Blueprint import dialog with Smart Climate Dashboard selected
   - Elements: Entity selectors, import button
   - Size: 800x600px recommended

2. **dashboard-current-status.png**
   - Shows: Current status section with all gauges
   - Elements: Climate card, offset gauge, accuracy gauge, confidence gauge
   - Size: 1200x400px recommended

3. **dashboard-learning-progress.png**
   - Shows: Learning progress charts section
   - Elements: Accuracy trend line chart, offset history area chart, sample collection bar chart
   - Size: 1200x600px recommended

4. **dashboard-calibration.png**
   - Shows: Calibration and hysteresis section
   - Elements: Status entities, power/temperature correlation graph
   - Size: 1200x500px recommended

5. **dashboard-controls.png**
   - Shows: Control panel section
   - Elements: Mode buttons, learning switch, manual override, reset button
   - Size: 1200x300px recommended

### Additional Screenshots Needed

6. **dashboard-mobile-view.png**
   - Shows: Mobile-optimized layout
   - Elements: Stacked cards, simplified gauges
   - Size: 375x812px (iPhone viewport)

7. **dashboard-core-cards-only.png**
   - Shows: Dashboard using only built-in HA cards
   - Elements: Standard thermostat, history-graph, entities cards
   - Size: 1200x800px recommended

8. **dashboard-custom-cards.png**
   - Shows: Enhanced view with custom cards
   - Elements: Mushroom climate, ApexCharts, button-card
   - Size: 1200x800px recommended

## Screenshot Guidelines

### General Requirements
- Use a consistent theme (default HA theme recommended)
- Include realistic data (not all zeros or errors)
- Show both day and night mode if possible
- Blur or replace any personal information
- Use English language for UI elements

### Data to Display
- Temperature values between 20-26°C
- Offset values between -2 to +2°C
- Learning progress at various stages (25%, 75%, 100%)
- Accuracy trends showing improvement
- Mix of operating modes

### Tools for Screenshots
- Browser developer tools for consistent viewport sizes
- Home Assistant's built-in screenshot service
- Image editing software for annotations if needed

## Placeholder Images

Until actual screenshots are available, the documentation references these placeholders. The images should be created in this priority order:

1. High Priority (User Setup):
   - dashboard-blueprint-import.png
   - dashboard-current-status.png
   - dashboard-controls.png

2. Medium Priority (Understanding):
   - dashboard-learning-progress.png
   - dashboard-calibration.png

3. Low Priority (Advanced):
   - dashboard-mobile-view.png
   - dashboard-core-cards-only.png
   - dashboard-custom-cards.png

## Alternative Text

Each image should have descriptive alt text for accessibility:

```markdown
![Dashboard Blueprint Import Dialog showing entity selection dropdowns and import button](images/dashboard-blueprint-import.png)
```

## Future Additions

Consider adding:
- Animated GIFs showing interactions
- Before/after comparisons
- Troubleshooting screenshots
- Video tutorials linked from the documentation