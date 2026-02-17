**ARGB CPU Fan Controller (Arduino + Desktop GUI)**

This repository contains an Arduino sketch and a Python desktop GUI for controlling addressable ARGB CPU fans. The project provides:

- A feature-rich Arduino sketch (`FanControl.ino`) using the FastLED library with many lighting effects (rainbow, pulse, tipsy, multicolor, etc.).
- A Tkinter-based GUI (`FanControl_GUI.py`) that can control the device, send presets, display a live multi-channel oscilloscope of telemetry, and tune a "Tipsy" sync effect.

**This README covers:** wiring and safety, how to upload the sketch, how to run the GUI, the serial protocol and telemetry format, Tipsy sync tuning, troubleshooting, and development notes.

**Safety & Hardware Requirements**

- Arduino Uno (or compatible board)
- ARGB fan (5V addressable LEDs / WS2812B-like)
- If you use multiple fans or run at high brightness, a separate 5V power supply capable of the total LED current is required.
- Common ground: when using an external supply, connect its GND to the Arduino GND.

Warning: Never connect 12V to a 5V LED strip. Double-check connector pinout before powering.

**Wiring (typical)**

- Fan V (5V) -> 5V (or external 5V supply)
- Fan G (GND) -> GND (Arduino and external supply common ground)
- Fan D (DATA) -> Arduino digital pin 6 (default in `FanControl.ino`)

If your fan uses a VGD-style connector, map `V`->5V, `G`->GND, `D`->Pin 6. Adjust `LED_PIN` in the sketch if you need a different pin.
## Software Requirements (Desktop)

- Python 3.8+ (Windows: use the official installer or Anaconda)
- `pyserial` (install with pip)
- `tkinter` (normally included with Python on Windows)

Install Python dependency:

```powershell
python -m pip install pyserial
```

Run the GUI:

```powershell
python FanControl_GUI.py
```

## Upload the Arduino sketch

1. Open `FanControl/FanControl.ino` in the Arduino IDE.
2. Ensure `#define LED_PIN` and `#define NUM_LEDS` are set to match your hardware.
3. Install the FastLED library (Library Manager → search "FastLED").
4. Select the correct board and COM port, then upload.

## Quick Usage (GUI)

- Connect to the Arduino's COM port at 9600 baud using the GUI's connection controls.
- Use Quick Control buttons for colors and effects, or the Sliders & Colors tab for fine-grained adjustments.
- The PWM Graph tab displays live telemetry channels; enable/disable channels in the Oscilloscope Controls.
- Tipsy Sync: use the Tipsy Sync slider to tune wobble speed, or enable "Bind to Measured Speed" to auto-map measured effect speed to Tipsy Scale.

## Serial Protocol (how GUI and Arduino communicate)

Two command forms are used:

1) Single-character commands (legacy/simple). Examples:
- `R` — Rainbow
- `P` — Pulse
- `S` — Static
- `Y` — Tipsy
- `J` — Multi-Color

The GUI appends a newline to single-character commands.

2) Numeric settings (tilde-prefixed): format `~<Type><Value>\\n`

- `~B<0-255>` — Brightness
- `~I<0-255>` — Intensity
- `~U<0-255>` — Saturation
- `~H<1-5>` — Hue rotation speed
- `~V<1-200>` — Effect speed (ms)
- `~T<32-255>` — Tipsy sync scale

Note: numeric commands must end with a newline. The GUI uses `~` commands for precise numeric control.

## Telemetry (JSON)

The Arduino emits JSON telemetry roughly every 50ms for the GUI's oscilloscope. Example:

```json
{"BR":128,"M":12,"S":30,"I":200,"SAT":255,"H":2,"R":255,"G":100,"BL":50,"TS":128}
```

Fields:

- `BR` — Brightness (0–255)
- `M`  — Mode index
- `S`  — Effect speed (1–200 ms)
- `I`  — Intensity (0–255)
- `SAT`— Saturation (0–255)
- `H`  — Hue rotation speed (1–5)
- `R`,`G`,`BL` — Current color RGB components (0–255)
- `TS` — Tipsy Scale value (32–255)

The GUI reads these keys and updates channel histories for plotting.

## Tipsy Sync Tuning

- The Tipsy effect uses `effectSpeed` as a base and a Tipsy Scale multiplier (`tipsySyncScale`) to control wobble frequency.
- Use the GUI slider (32–255) to tune the behavior; larger values speed up the wobble.
- Enabling "Bind to Measured Speed" causes the GUI to map the latest telemetry `S` value into a Tipsy Scale and send `~T<value>\\n` to the Arduino automatically.

The mapping logic lives in `FanControl_GUI.py` (`map_range`) and can be adjusted to taste.

## Troubleshooting

- If the GUI can't connect: verify COM port and that no other program (e.g., Arduino Serial Monitor) is using the port.
- If effects don't change: ensure the sketch is uploaded and the GUI is sending newline-terminated commands.
- If telemetry parsing fails: capture raw serial lines with the Arduino Serial Monitor to inspect the emitted JSON.

## Development Notes

- Important files:
	- `FanControl/FanControl.ino` — Arduino sketch
	- `FanControl_GUI.py` — Python GUI and telemetry parser
- To add telemetry channels: emit a new JSON key in the sketch and add an entry in `telemetry_channels` in the GUI.

## Contributing

Contributions welcome. Open issues for bugs or feature ideas, and submit PRs for improvements. When extending the serial protocol, prefer adding new `~` numeric commands for optional features.

## License

This project is suitable to release under the MIT license. Add a `LICENSE` file if you plan to publish the repository.

---