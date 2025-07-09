# Smart Climate Control v1.1.1-beta2 Release Notes

## 🎯 Critical Fix: Overcooling During Initial Learning

This beta release addresses a critical issue where the system would severely overcool rooms during the initial learning phase, making the integration unusable for new installations.

## 🚀 What's New

### Stable State Calibration Phase
We've implemented an intelligent calibration system that prevents overcooling during the first 10 learning samples:

- **Smart Offset Caching**: The system now detects when your AC is in a "stable state" (idle with converged temperatures) and only calculates offsets during these periods
- **Prevents Feedback Loops**: During active cooling, the system uses the cached stable offset instead of recalculating, preventing the feedback loop that caused overcooling
- **Clear Status Messages**: You'll see helpful calibration messages like:
  - "Calibration (Stable): Updated offset to -7.0°C. (3/10 samples)"
  - "Calibration (Active): Using cached stable offset of -7.0°C."
- **Automatic Transition**: After 10 samples, the system seamlessly switches to full learning mode

## 🐛 Fixed Issues

### Critical Overcooling Issue (#3)
- **Problem**: With a target of 24.5°C, rooms would cool to 23°C or lower during initial learning
- **Root Cause**: System applied large dynamic offsets creating feedback loops
- **Solution**: Stable state calibration prevents offset adjustments during active cooling
- **Result**: Your AC will now maintain proper temperatures even during the learning phase

This fix is especially important for ACs with evaporator coil sensors that show very low temperatures (e.g., 15°C) when cooling.

## 📦 Installation

### For HACS Users
1. Go to HACS → Integrations
2. Click the three dots on Smart Climate Control
3. Select "Redownload"
4. **Enable "Show beta versions"** toggle
5. Select version 1.1.1-beta2
6. Restart Home Assistant

### For Manual Installation
1. Download the release from GitHub
2. Copy to your `custom_components/smart_climate/` directory
3. Restart Home Assistant

## 🧪 Testing Feedback Needed

Please test this beta release and report:
- Does the overcooling issue during initial learning still occur?
- Are the calibration status messages clear and helpful?
- Any unexpected behavior during the calibration phase?

Report issues at: https://github.com/VectorBarks/smart-climate/issues

## 📝 Technical Details

- Calibration phase lasts for the first 10 learning samples
- Stable state defined as: power < idle threshold AND |AC temp - room temp| < 2°C
- Comprehensive test suite ensures no regression in existing functionality

## 🙏 Acknowledgments

Thanks to everyone who reported the overcooling issue and helped test solutions!