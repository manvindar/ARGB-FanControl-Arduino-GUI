# FanControl Sketch - Enhanced Customization Features

## Summary of Enhancements

This enhanced version of the FanControl sketch includes significantly expanded customization options for controlling your ARGB CPU fan.

---

## 🎨 NEW COLOR PRESETS

Added 3 new color options beyond the original 7:

| Command | Color   | RGB Value      |
|---------|---------|----------------|
| 1       | Red     | (255, 0, 0)    |
| 2       | Green   | (0, 255, 0)    |
| 3       | Blue    | (0, 0, 255)    |
| 4       | White   | (255, 255, 255)|
| 5       | Cyan    | (0, 255, 255)  |
| 6       | Magenta | (255, 0, 255)  |
| 7       | Yellow  | (255, 255, 0)  |
| **8**   | **Orange** | **(255, 165, 0)**   |
| **9**   | **Pink**   | **(255, 192, 203)**  |
| **0**   | **Purple** | **(128, 0, 128)**    |

---

## ✨ NEW LIGHTING EFFECTS

### 2 Completely New Effects Added:

**X - Strobe Flash**
- Rapid on/off flashing with the current color
- Creates a dramatic pulsing effect
- Great for RGB gaming setups or attention-grabbing displays

**E - Breathing**
- Smooth fade in and out effect
- Simulates a breathing motion
- Very calming and sophisticated
- Perfect for ambient lighting

All 12 effects now available:
- `R` - Rainbow Cycle
- `P` - Pulse Effect  
- `S` - Static Color
- `W` - Color Wipe
- `T` - Theater Chase
- `K` - Sparkle
- `N` - Sinelon (neon sweep)
- `B` - BPM (color pulse)
- `C` - Confetti (twinkles)
- `F` - Fire
- `X` - Strobe Flash ⭐ **NEW**
- `E` - Breathing ⭐ **NEW**

---

## ⚡ SPEED CONTROL ENHANCEMENTS

### Quick Speed Presets (Letter Keys):

Instead of just using `>` and `<`, you can now set speed directly:

| Command | Speed  | Wait (ms) | Use Case              |
|---------|--------|-----------|----------------------|
| `Q`     | Very Fast | 5ms   | Rapid animations     |
| `D`     | Fast   | 15ms    | Normal animations    |
| `V`     | Medium | 30ms    | Balanced feel        |
| `Z`     | Slow   | 50ms    | Smooth transitions   |
| `M`     | Very Slow | 100ms| Graceful patterns    |

**Original controls still work:**
- `>` - Increase speed (reduce wait time by 5ms)
- `<` - Decrease speed (increase wait time by 5ms)

---

## 🔄 AUTO-CYCLE MODE ⭐ NEW

Press `A` to toggle **Auto-Cycle Mode**:
- Automatically cycles through all 10 classic effects
- Changes effect every 5 seconds
- Press any control button to manually override and reset timer
- Perfect for demonstrations or ambient rotation

Status updates in Serial Monitor:
```
>> AUTO-CYCLE MODE: ENABLED
   Effects change every 5 seconds

Auto-cycle -> Mode 1
Auto-cycle -> Mode 2
...
```

---

## 📊 STATUS DISPLAY

Press `L` to view detailed system status:

```
========== CURRENT STATUS ==========
Brightness: 200
Effect Speed: 20
Current Mode: Rainbow Cycle
Current Color: RGB(255,0,0)
Auto-Cycle: OFF
====================================
```

Shows at startup with enhanced welcome message.

---

## 🌈 GLOBAL VARIABLES FOR ADVANCED CUSTOMIZATION

The sketch now includes additional global variables for fine-tuning:

```cpp
uint8_t hueShiftSpeed = 1;        // Adjust rainbow rotation speed
uint8_t minBrightness = 50;       // Minimum brightness threshold
uint8_t maxBrightness = 255;      // Maximum brightness threshold
bool autoCycleMode = false;       // Auto-cycle toggle state
```

These can be easily modified in the code for custom behavior.

---

## 🎮 COMPLETE COMMAND REFERENCE

### Colors (Sets to Static Mode)
- `1-7` = Original colors
- `8-0` = New colors (Orange, Pink, Purple)

### Effects
- `R` = Rainbow Cycle
- `P` = Pulse
- `S` = Static
- `W` = Color Wipe
- `T` = Theater Chase
- `K` = Sparkle
- `N` = Sinelon
- `B` = BPM
- `C` = Confetti
- `F` = Fire
- `X` = Strobe (NEW)
- `E` = Breathing (NEW)

### Controls
- `+` / `-` = Brightness up/down
- `>` / `<` = Speed faster/slower
- `Q`, `D`, `V`, `Z`, `M` = Speed presets
- `A` = Toggle Auto-Cycle (NEW)
- `L` = Display Status (NEW)
- `G` = Custom RGB input option
- `H` = Hue shift speed info

---

## 🔧 CUSTOMIZATION TIPS

### Make Breathing Slower
Find this line and increase the value:
```cpp
static int8_t breathDirection = 3;  // Increase to 2 or 1 for slower breathing
```

### Extend Auto-Cycle Interval
Modify the constant:
```cpp
const uint16_t MODE_CHANGE_INTERVAL = 5000;  // Change 5000 to higher value (milliseconds)
```

### Add Your Own Color
Edit the colorPresets array:
```cpp
const CRGB colorPresets[] = {
    CRGB::Red,        // 1
    // ... existing colors ...
    {255, 100, 200}   // Your custom color
};
```

### Increase Min/Max Brightness Range
```cpp
uint8_t minBrightness = 30;   // Lower = darker minimum
uint8_t maxBrightness = 255;  // 255 = full brightness
```

---

## 📝 COMPATIBILITY

- **Arduino Board**: Uno, Nano, Mega, etc.
- **Library Required**: FastLED (Install via Arduino Library Manager)
- **LED Type**: WS2812B or compatible addressable RGB LEDs
- **Voltage**: 5V
- **Data Pin**: Pin 6 (configurable via `#define LED_PIN`)

---

## 🚀 FEATURES AT A GLANCE

| Feature | Before | After |
|---------|--------|-------|
| Color Presets | 7 | **10** |
| Effects | 10 | **12** |
| Speed Control Methods | 2 | **7** |
| Status Display | ❌ | **✅** |
| Auto-Cycle Mode | ❌ | **✅** |
| Enhanced Menu | ❌ | **✅** |
| Custom Variables | Limited | **Extensive** |

---

## 💡 Example Workflows

### Gaming Setup
1. `X` - Enable Strobe for dramatic effect
2. `1` - Set to Red
3. `Q` - Very Fast speed
4. Adjust brightness with `+` as needed

### Ambient Lighting
1. `A` - Enable Auto-Cycle
2. `Z` - Set to Slow speed
3. Press `L` to monitor
4. Effects rotate automatically every 5 seconds

### Relaxation Mode
1. `E` - Enable Breathing effect
2. `4` - Set to White or `9` (Pink)
3. `-` - Reduce brightness
4. `M` - Very Slow speed for calm pacing

---

Enjoy your enhanced ARGB fan control! 🎨✨
