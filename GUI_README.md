# Fan Control GUI Setup & Usage Guide - Enhanced Edition

A Python-based graphical interface for controlling the Arduino ARGB Fan Controller with advanced features.

## ✨ What's New (Enhanced Edition)

✅ **Tabbed Interface** - 4 organizing tabs for different control modes  
✅ **Interactive Sliders** - Real-time brightness, speed, intensity, saturation, hue rotation controls  
✅ **Custom RGB Color Picker** - Choose any color from the color palette  
✅ **Preset System** - Save and load entire settings configurations  
✅ **Macro Recording** - Record command sequences and play them back automatically  
✅ **Command History** - See all sent and received commands with timestamps  
✅ **Quick Favorites** - Pre-configured effect + color combinations  
✅ **Real-time Status Display** - Monitor current effect, color, and all settings  
✅ **Persistent Storage** - Presets and macros saved to JSON files  

## Prerequisites

1. **Python 3.6+** installed on your system
2. **PySerial library** (handles USB serial communication)
3. Arduino with the `FanControl.ino` sketch uploaded

## Installation

### Step 1: Install Python (if not already installed)
- Download from: https://www.python.org/downloads/
- During installation, **MAKE SURE to check "Add Python to PATH"**

### Step 2: Install PySerial Library
Open PowerShell and run:
```powershell
pip install pyserial
```

Or if that doesn't work:
```powershell
python -m pip install pyserial
```

## Running the GUI

### Option 1: Double-Click (Windows)
1. Right-click on `FanControl_GUI.py`
2. Select "Open with" → "Python"

### Option 2: PowerShell
```powershell
cd C:\Users\manvi\Documents\ardiono_uno
python FanControl_GUI.py
```

### Option 3: Create a Shortcut (Easy Access)
1. Right-click on `FanControl_GUI.py` → "Send To" → "Desktop (create shortcut)"
2. Right-click the shortcut, select "Properties"
3. Change "Start in" to: `C:\Users\manvi\Documents\ardiono_uno`
4. Now you can double-click the shortcut anytime

## How to Use - Tab Guide

### **Tab 1: Quick Control** (Main Interface)

**Connection Section**
- Select COM Port from dropdown
- Choose Baud Rate (default 9600)
- Click "Connect" to establish connection
- Click "Refresh Ports" to scan for Arduino

**Colors Section** (10 buttons)
- Click any color to instantly switch (Red, Green, Blue, White, Cyan, Magenta, Yellow, Orange, Pink, Purple)

**Effects Section** (12 buttons)
- Rainbow, Pulse, Static, Wipe, Theater, Sparkle, Sinelon, BPM, Confetti, Fire, Strobe, Breathing

**Brightness Control**
- Low (25%) - Quick dim preset
- Medium (50%) - Quick medium preset
- `+` / `-` - Fine brightness adjustment

**Speed Presets**
- VFast (5ms), Fast (15ms), Med (30ms), Slow (50ms), VSlow (100ms)

**Customization Buttons**
- **Intensity**: Decrease/Increase effect intensity (−/+)
- **Saturation**: Adjust color saturation (−/+)
- **Hue Speed**: Control rainbow rotation speed (−/+)
- **LED Options**: Reverse, Mirror, Wave Direction
- **Rainbow Modes**: Cycle through 4 rainbow visual styles

**System Commands**
- Status - Show current settings
- Show Custom - Display customization values
- LED Settings - Show LED-specific options
- Clear LEDs - Turn off all LEDs
- Auto-Cycle - Toggle automatic effect rotation
- Reset All - Return to factory defaults

---

### **Tab 2: Sliders & Colors** (Fine Control)

**Brightness Slider** (0-255)
- Drag to adjust brightness in real-time
- Value shown in label

**Speed Control Slider** (1-200ms)
- Control animation speed precisely
- Lower = faster, Higher = slower

**Effect Intensity Slider** (0-255)
- Adjust how powerful/intense the effect is
- Affects pulsing strength, flash intensity, etc.

**Color Saturation Slider** (0-255)
- 0 = Gray/desaturated
- 255 = Full vivid colors
- Great for pastel effects

**Hue Rotation Speed Slider** (1-5)
- Controls rainbow effect speed multiplier
- 1 = slow rainbow, 5 = fast rainbow

**Custom RGB Color Picker**
- Click "Pick Color" to open color selector
- Choose any RGB value
- Preview shown in color box
- Click "Send Custom RGB" to apply

---

### **Tab 3: Presets & Macros** (Automation)

#### **Save/Load Presets**
**Save Current Settings:**
1. Adjust brightness, speed, intensity, saturation, hue speed to desired values
2. Enter a preset name (e.g., "Chill Mode")
3. Click "Save Current"
4. Preset saved to `fan_presets.json`

**Load Saved Preset:**
1. Select preset from dropdown
2. Click "Load"
3. All slider values update automatically

**Delete Preset:**
1. Select preset from dropdown
2. Click "Delete"
3. Confirm deletion

#### **Macro Recording**
**Record a Macro:**
1. Click "⏺ Record Macro" (button changes to "⏹ Stop Recording")
2. Send commands from Quick Control tab - every command is recorded
3. Click "⏹ Stop Recording" when finished
4. Recorded commands shown in text box

**Save Recording:**
1. Enter macro name (e.g., "Rainbow Cool Down")
2. Click "Save Macro"
3. Macro saved to `fan_macros.json`

**Play Macro:**
1. Select macro from "Play:" dropdown
2. Click "▶ Play"
3. All recorded commands execute automatically on Arduino

**Delete Macro:**
1. Select macro from dropdown
2. Click "Delete"
3. Confirm deletion

**Clear Recording:**
- Click "Clear Recording" to start fresh
- Previous recording discarded

---

### **Tab 4: Status & Favorites** (Monitoring)

#### **Current Status**
- Real-time display of Arduino status
- Shows effects, colors, speeds sent

#### **Command History**
- Timestamped log of all sent and received commands
- Format: `[HH:MM:SS] → Sent: R` or `[HH:MM:SS] ← Received: Arduino: Rainbow`
- Useful for debugging and confirming communication

**Clear History:**
- Click "Clear History" to empty the log

#### **Quick Favorites**
Pre-configured buttons for popular combinations:
- **Chill Rainbow** - Slow rainbow effect with Red
- **Fast Pulse Red** - Quick pulsing in red
- **Calm Fire** - Medium-speed fire effect
- **Disco Strobe** - Fast strobing for parties

Click any favorite button to instantly apply that combination!

---

## File Storage

### Saved Files (Created automatically)

**fan_presets.json** - Your saved settings presets
```json
{
  "Chill Mode": {
    "brightness": 128,
    "speed": 50,
    "intensity": 100,
    "saturation": 200,
    "hue_rotation": 1,
    "effect": "Rainbow",
    "color": "Red"
  }
}
```

**fan_macros.json** - Your recorded macros
```json
{
  "Rainbow Cool Down": {"R", "+", "+", ">", ">"}
}
```

Both files saved in the same directory as `FanControl_GUI.py`

---

## Troubleshooting

### "No COM ports detected"
- Plug in your Arduino with USB cable
- Wait 2-3 seconds for drivers to load
- Click "Refresh Ports"
- Check Device Manager (Settings → Device Manager) for Arduino COM port

### "Connection refused" or "Port already in use"
- Close Arduino IDE (it locks the port)
- Close other serial monitor applications
- Try a different USB port
- Restart the GUI

### Commands not working
- Verify Arduino has `FanControl.ino` uploaded correctly
- Check baud rate matches Arduino (default 9600)
- Look at Command History tab for error messages
- Try sending "L" (status) command to test connection

### Presets/Macros not saving
- Check folder permissions for your user account
- Make sure you have write access to the folder
- Verify JSON files aren't corrupted
- Delete `.json` files and restart to create fresh ones

### Slider changes don't send to Arduino
- Sliders track local values
- Use slider values to verify settings before uploading
- Send preset to Arduino after adjusting sliders

---

## Advanced Tips

1. **Use Presets for Moods**
   - Save "Movie Mode" (low brightness, calm effects)
   - Save "Gaming Mode" (fast effects, bright)
   - Save "Sleep Mode" (breathing effect, dim)

2. **Create Macros for Sequences**
   - Record transition from Rainbow → Fire → Strobe
   - Play entire sequence with one click

3. **Combine Sliders + Buttons**
   - Use sliders for fine-tuning
   - Use quick buttons for instant changes

4. **Monitor with History**
   - Keep Command History tab open
   - Verify every command reaches Arduino
   - Useful for debugging connection issues

5. **Favorites for Quick Access**
   - Click favorite buttons instead of navigating tabs
   - Great for switching effects during video/games

---

## Keyboard Shortcuts

While the app is focused:
- Most buttons can be triggered with Alt+underlined letter
- Not all controls have shortcuts (check for underlines)

---

## Performance Notes

- **Multi-tab interface** - Runs smoothly on any Windows machine
- **Real-time sliders** - No lag, instant value updates
- **Macro playback** - Commands sent sequentially with brief delays
- **Command history** - Stores up to hundreds of commands before scrolling

---

## Still Having Issues?

1. **Test Arduino directly:**
   - Open Arduino IDE → Tools → Serial Monitor
   - Set baud to 9600
   - Send manual commands to verify Arduino works

2. **Check Python & PySerial:**
   ```powershell
   python -m pip show pyserial
   ```
   Should show version info if installed correctly

3. **Verify COM Port:**
   - Windows Settings → Device Manager
   - Look for "COM#" entries
   - Arduino usually shows as "USB Serial Device"

4. **Check file permissions:**
   - Right-click `fan_presets.json` → Properties
   - Ensure your user has "Write" permission

---

## Keyboard Guide - Arduino Commands

For reference when using Serial Monitor directly (not the GUI):

**Colors:** 1-0  
**Effects:** R, P, S, W, T, K, N, B, C, F, X, E  
**Control:** +/-, ><, QDVZM  
**Custom:** #/$, %/^, &/*, ;/', [, ], {, }, (, ), A, L

---

Enjoy your enhanced RGB fan controller! 🎨✨


