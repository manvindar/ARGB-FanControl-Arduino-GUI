#!/usr/bin/env python3
"""
CPU Fan ARGB Controller GUI - Enhanced Edition
A comprehensive graphical interface for controlling Arduino ARGB fan controllers
Features: Sliders, Color Picker, Presets, Macros, Real-time Status
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, colorchooser
import serial
import serial.tools.list_ports
import threading
import queue
import json
import os
from datetime import datetime
from collections import deque
from typing import Optional, List, Dict, Any, Deque, Tuple

class FanControlGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CPU Fan ARGB Controller - Enhanced")
        self.root.geometry("1400x900")
        self.root.resizable(True, True)
        
        self.serial_port = None
        self.is_connected = False
        self.read_thread = None
        
        # Tracking variables
        self.current_effect = "Rainbow"
        self.current_color = "Red"
        self.brightness_val = 255
        self.speed_val = 10
        self.intensity_val = 128
        self.saturation_val = 255
        self.hue_rotation_val = 1
        self.custom_rgb = (255, 0, 0)
        
        # Preset and macro management
        self.presets_file = os.path.join(os.path.dirname(__file__), "fan_presets.json")
        self.macros_file = os.path.join(os.path.dirname(__file__), "fan_macros.json")
        self.macros = {}
        self.macro_recording = False
        self.recorded_commands = []
        self.favorites = {}
        self.command_history = []
        
        # History file for persistent logging
        self.history_file = os.path.join(os.path.dirname(__file__), "command_history.json")
        
        # Multi-channel Oscilloscope tracking with multiple signals
        self.max_samples = 200
        self.telemetry_channels = {
            'BR': {'name': 'Brightness', 'history': deque(maxlen=self.max_samples), 'color': '#0066cc', 'show': True},
            'M': {'name': 'Mode', 'history': deque(maxlen=self.max_samples), 'color': '#ff6600', 'show': True},
            'S': {'name': 'Speed', 'history': deque(maxlen=self.max_samples), 'color': '#00cc66', 'show': True},
            'I': {'name': 'Intensity', 'history': deque(maxlen=self.max_samples), 'color': '#ff0066', 'show': True},
            'SAT': {'name': 'Saturation', 'history': deque(maxlen=self.max_samples), 'color': '#cc00ff', 'show': True},
            'H': {'name': 'Hue Speed', 'history': deque(maxlen=self.max_samples), 'color': '#ffaa00', 'show': True},
            'R': {'name': 'Red', 'history': deque(maxlen=self.max_samples), 'color': '#ff3333', 'show': False},
            'G': {'name': 'Green', 'history': deque(maxlen=self.max_samples), 'color': '#33ff33', 'show': False},
            'BL': {'name': 'Blue', 'history': deque(maxlen=self.max_samples), 'color': '#3333ff', 'show': False},
            'TS': {'name': 'Tipsy Scale', 'history': deque(maxlen=self.max_samples), 'color': '#ffd24d', 'show': False},
        }
        self.pwm_timestamps = deque(maxlen=self.max_samples)
        self.monitoring_enabled = False
        self.graph_canvas = None
        self.auto_update_graph = True  # Enable continuous graph updates
        self.graph_update_interval = 100  # Update every 100ms
        # Tipsy sync tuning (GUI-exposed)
        self.tipsy_sync_value = 128
        self.bind_tipsy_var = tk.BooleanVar(value=False)
        
        # Core Pin configuration
        self.config_file = os.path.join(os.path.dirname(__file__), "arduino_config.json")
        self.led_pin: int = 6
        self.num_leds: int = 12

        # UI State Variables
        self.port_var = tk.StringVar()
        self.baud_var = tk.StringVar(value="9600")
        self.preset_name_var = tk.StringVar()
        self.macro_name_var = tk.StringVar()
        self.pin_var = tk.StringVar()
        self.led_count_var = tk.StringVar()
        self.bind_tipsy_var = tk.BooleanVar(value=False)
        self.auto_update_var = tk.BooleanVar(value=True)

        # UI Element References (Use Any to bypass strict NoneType checking in some lint environments)
        self.status_label: Any = None
        self.info_label: Any = None
        self.history_text: Any = None
        self.port_combo: Any = None
        self.connect_btn: Any = None
        self.graph_canvas: Any = None
        self.brightness_slider: Any = None
        self.brightness_label: Any = None
        self.speed_slider: Any = None
        self.speed_label: Any = None
        self.intensity_slider: Any = None
        self.intensity_label: Any = None
        self.saturation_slider: Any = None
        self.saturation_label: Any = None
        self.hue_rotation_slider: Any = None
        self.hue_rotation_label: Any = None
        self.tipsy_slider: Any = None
        self.color_canvas: Any = None
        self.rgb_label: Any = None
        self.macro_combo: Any = None
        self.preset_combo: Any = None
        self.commands_text: Any = None
        self.record_btn: Any = None
        self.scroll_frame: Any = None
        self.current_brightness_label: Any = None
        self.min_brightness_label: Any = None
        self.max_brightness_label: Any = None
        self.avg_brightness_label: Any = None
        self.samples_label: Any = None
        self.display_pin_label: Any = None
        self.display_led_count_label: Any = None
        self.monitoring_status: Any = None
        self.code_snippet_text: Any = None
        
        self.load_presets()
        self.load_macros()
        self.load_arduino_config()
        
        self.setup_ui()
        # Load history after UI exists so the widget can be updated
        self.load_history()
        self.detect_ports()
        
    def setup_ui(self):
        # Create persistent status info first (used by various tabs/handlers)
        top_status = ttk.Frame(self.root)
        top_status.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = ttk.Label(top_status, text="Status: Disconnected", foreground="red", font=("Arial", 10, "bold"))
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        self.info_label = ttk.Label(top_status, text="Effect: Rainbow | Color: Red", font=("Arial", 10))
        self.info_label.pack(side=tk.LEFT, padx=10)

        # 1. Main Vertical Split (Notebook vs History)
        # This allows the user to dynamically resize the console area.
        main_v_pane = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        main_v_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 2. Main Tabbed Notebook
        notebook = ttk.Notebook(main_v_pane)
        main_v_pane.add(notebook, weight=4)
        
        # Tab 1: Dashboard (Everything in one)
        dashboard_tab = ttk.Frame(notebook)
        notebook.add(dashboard_tab, text="🎮 Dashboard")
        self.setup_quick_tab(dashboard_tab)
        
        # Tab 2: Presets & Macros
        preset_tab = ttk.Frame(notebook)
        notebook.add(preset_tab, text="💾 Presets & Macros")
        self.setup_preset_tab(preset_tab)
        
        # Tab 3: Configuration
        settings_tab = ttk.Frame(notebook)
        notebook.add(settings_tab, text="⚙ Settings")
        self.setup_settings_tab(settings_tab)
        
        # 3. Bottom Persistent Command History
        history_frame = ttk.LabelFrame(main_v_pane, text="📜 Command History", padding="5")
        main_v_pane.add(history_frame, weight=1)
        
        self.history_text = scrolledtext.ScrolledText(history_frame, height=8, width=120, state=tk.DISABLED, font=("Consolas", 9))
        self.history_text.pack(fill=tk.BOTH, expand=True)
    
    def setup_quick_tab(self, parent):
        # Main container with a pane for layout
        main_pane = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True)

        # ===== LEFT COLUMN: ALL CONTROLS (Scrollable) =====
        left_container = ttk.Frame(main_pane)
        main_pane.add(left_container, weight=1)

        # Add a scrollable area for the controls
        canvas = tk.Canvas(left_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        # Add dynamic binding to sync scroll_frame width with the canvas
        canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        
        def _on_canvas_configure(event):
            # Sync the inner frame width to the canvas width
            canvas.itemconfig(canvas_window, width=event.width)
            
        canvas.bind("<Configure>", _on_canvas_configure)
        
        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Compact padding for internal frames
        p = {"fill": tk.X, "pady": 3, "padx": 5}

        # 1. CONNECTION
        conn_frame = ttk.LabelFrame(scroll_frame, text="🔌 Connection", padding="8")
        conn_frame.pack(fill=tk.X, pady=3, padx=5)
        ttk.Label(conn_frame, text="Port:").pack(side=tk.LEFT)
        self.port_combo = ttk.Combobox(conn_frame, textvariable=self.port_var, width=8, state="readonly")
        self.port_combo.pack(side=tk.LEFT, padx=2)
        ttk.Combobox(conn_frame, textvariable=self.baud_var, values=["9600", "115200"], width=8, state="readonly").pack(side=tk.LEFT, padx=2)
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.connect_port, width=10)
        self.connect_btn.pack(side=tk.LEFT, padx=2)
        ttk.Button(conn_frame, text="⟳", width=3, command=self.detect_ports).pack(side=tk.LEFT)

        # 2. COLORS
        color_frame = ttk.LabelFrame(scroll_frame, text="🎨 Colors", padding="8")
        color_frame.pack(fill=tk.X, pady=3, padx=5)
        colors = [("Red", "1"), ("Green", "2"), ("Blue", "3"), ("White", "4"), ("Cyan", "5"),
                  ("Magenta", "6"), ("Yellow", "7"), ("Orange", "8"), ("Pink", "9"), ("Purple", "0"),
                  ("Multi", "J")]
        for i, (name, cmd) in enumerate(colors):
            ttk.Button(color_frame, text=name, width=8, command=lambda c=cmd, n=name: self.send_command_track(c, n)).grid(row=i//4, column=i%4, padx=2, pady=2)
        
        # 3. EFFECTS
        effect_frame = ttk.LabelFrame(scroll_frame, text="✨ Effects", padding="8")
        effect_frame.pack(fill=tk.X, pady=3, padx=5)
        # Use full names for effects
        effects = [
            ("Rainbow", "R"), ("Police", "P"), ("Strobe", "S"), ("Wipe", "W"), 
            ("Theater", "T"), ("Scanner", "K"), ("Snow", "N"), ("Beam", "B"), 
            ("Comet", "C"), ("Fire", "F"), ("Xbox", "X"), ("Breath", "E"),
            ("Typer", "Y")
        ]
        for i, (name, cmd) in enumerate(effects):
            ttk.Button(effect_frame, text=name, width=10, command=lambda c=cmd, n=name: self.send_command_track(c, n)).grid(row=i//4, column=i%4, padx=2, pady=2)

        # 4. SLIDERS (Full Control)
        slider_frame = ttk.LabelFrame(scroll_frame, text="⚙ Fine Tuning", padding="8")
        slider_frame.pack(fill=tk.X, pady=3, padx=5)

        # Helper to create compact sliders with labels
        def add_compact_slider(parent, label_text, var_name, from_val, to_val, cmd_func, change_func):
            frame = ttk.Frame(parent)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=label_text, width=7).pack(side=tk.LEFT)
            lbl = ttk.Label(frame, text=str(from_val), width=4)
            slider = ttk.Scale(frame, from_=from_val, to=to_val, orient=tk.HORIZONTAL, command=change_func)
            slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            lbl.pack(side=tk.RIGHT)
            
            setattr(self, var_name + "_slider", slider)
            setattr(self, var_name + "_label", lbl)
            slider.bind("<ButtonRelease-1>", lambda e: cmd_func())
            return slider

        self.brightness_slider = add_compact_slider(slider_frame, "Bright:", "brightness", 0, 255, self.send_brightness, self.on_brightness_change)
        self.brightness_slider.set(self.brightness_val)
        
        self.speed_slider = add_compact_slider(slider_frame, "Speed:", "speed", 1, 200, self.send_speed, self.on_speed_change)
        self.speed_slider.set(self.speed_val)
        
        self.intensity_slider = add_compact_slider(slider_frame, "Intens:", "intensity", 0, 255, self.send_intensity, self.on_intensity_change)
        self.intensity_slider.set(self.intensity_val)
        
        self.saturation_slider = add_compact_slider(slider_frame, "Satur:", "saturation", 0, 255, self.send_saturation, self.on_saturation_change)
        self.saturation_slider.set(self.saturation_val)
        
        self.hue_rotation_slider = add_compact_slider(slider_frame, "Hue Rot:", "hue_rotation", 1, 5, self.send_hue, self.on_hue_change)
        self.hue_rotation_slider.set(self.hue_rotation_val)

        # 5. CUSTOM RGB PICKER
        rgb_frame = ttk.LabelFrame(scroll_frame, text="🌈 Custom RGB", padding="8")
        rgb_frame.pack(fill=tk.X, pady=3, padx=5)
        self.color_canvas = tk.Canvas(rgb_frame, bg="red", width=60, height=25, relief=tk.SUNKEN, bd=1)
        self.color_canvas.pack(side=tk.LEFT, padx=5)
        ttk.Button(rgb_frame, text="Pick", width=6, command=self.pick_custom_color).pack(side=tk.LEFT, padx=2)
        self.rgb_label = ttk.Label(rgb_frame, text="(255,0,0)", font=("Arial", 8))
        self.rgb_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(rgb_frame, text="Apply", width=6, command=self.send_custom_rgb).pack(side=tk.LEFT, padx=2)

        # 6. SYSTEM COMMANDS
        sys_frame = ttk.LabelFrame(scroll_frame, text="💻 System", padding="8")
        sys_frame.pack(fill=tk.X, pady=3, padx=5)
        sys_btns = [
            ("Status", "L"), ("Show Custom", ")"), ("Hard Reset", "("), 
            ("Clear LEDs", "{"), ("Auto Cycle", "A"), ("Pin Config", "I")
        ]
        for i, (name, cmd) in enumerate(sys_btns):
            ttk.Button(sys_frame, text=name, width=12, command=lambda c=cmd: self.send_command(c)).grid(row=i//3, column=i%3, padx=2, pady=2)

        # ===== RIGHT COLUMN: VISUALIZATION & MONITORING =====
        right_container = ttk.Frame(main_pane, padding="10")
        main_pane.add(right_container, weight=1)

        # 1. Graph Canvas
        graph_box = ttk.LabelFrame(right_container, text="📊 Real-time Multi-Channel Oscilloscope", padding="5")
        graph_box.pack(fill=tk.BOTH, expand=True)

        self.graph_canvas = tk.Canvas(graph_box, bg="#050510", highlightthickness=0)
        self.graph_canvas.pack(fill=tk.BOTH, expand=True)
        self.graph_canvas.bind("<Configure>", lambda e: self.draw_graph())

        # 2. Channel Selectors
        chan_frame = ttk.Frame(right_container)
        chan_frame.pack(fill=tk.X, pady=5)
        self.channel_vars = {}
        # Explicit keys to satisfy type checker
        main_telemetry_keys = ['BR', 'M', 'S', 'I', 'SAT', 'H']
        for key in main_telemetry_keys:
            if key in self.telemetry_channels:
                chan_data = self.telemetry_channels[key]
                show_val = bool(chan_data.get('show', True))
                v = tk.BooleanVar(value=show_val)
                self.channel_vars[key] = v
                name_val = str(chan_data.get('name', key))
                ttk.Checkbutton(chan_frame, text=name_val, variable=v, 
                               command=lambda k=key: self.toggle_channel(k)).pack(side=tk.LEFT, padx=5)

        # 3. Statistics Dashboard
        stats_frame = ttk.LabelFrame(right_container, text="📈 Signal Statistics", padding="8")
        stats_frame.pack(fill=tk.X, pady=5)
        
        # Grid for stats to keep them centered and neat
        for i, txt in enumerate(["CURRENT", "MIN", "MAX", "AVG", "SAMPLES"]):
            ttk.Label(stats_frame, text=txt, font=("Arial", 7, "bold")).grid(row=0, column=i, padx=15)
        
        self.current_brightness_label = ttk.Label(stats_frame, text="0", font=("Courier", 12, "bold"), foreground="#00ff00")
        self.current_brightness_label.grid(row=1, column=0)
        self.min_brightness_label = ttk.Label(stats_frame, text="0", font=("Courier", 10))
        self.min_brightness_label.grid(row=1, column=1)
        self.max_brightness_label = ttk.Label(stats_frame, text="0", font=("Courier", 10))
        self.max_brightness_label.grid(row=1, column=2)
        self.avg_brightness_label = ttk.Label(stats_frame, text="0", font=("Courier", 10))
        self.avg_brightness_label.grid(row=1, column=3)
        self.samples_label = ttk.Label(stats_frame, text="0", font=("Courier", 10))
        self.samples_label.grid(row=1, column=4)

        # Auto-start monitoring
        self.monitoring_enabled = True
        self.auto_update_graph = True
        self.schedule_graph_update()
    
    def setup_preset_tab(self, parent):
        parent_frame = ttk.Frame(parent, padding="10")
        parent_frame.pack(fill=tk.BOTH, expand=True)
        
        # ===== PRESETS SECTION =====
        preset_frame = ttk.LabelFrame(parent_frame, text="Save/Load Settings Presets", padding="10")
        preset_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(preset_frame, text="Preset Name:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(preset_frame, textvariable=self.preset_name_var, width=20).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(preset_frame, text="Save Current", command=self.save_preset).pack(side=tk.LEFT, padx=3)
        
        ttk.Label(preset_frame, text="Load:").pack(side=tk.LEFT, padx=5)
        self.preset_combo = ttk.Combobox(preset_frame, width=20, state="readonly")
        self.preset_combo.pack(side=tk.LEFT, padx=5)
        ttk.Button(preset_frame, text="Load", command=self.load_preset).pack(side=tk.LEFT, padx=3)
        ttk.Button(preset_frame, text="Delete", command=self.delete_preset).pack(side=tk.LEFT, padx=3)
        
        self.refresh_presets()
        
        # ===== MACROS SECTION =====
        macro_frame = ttk.LabelFrame(parent_frame, text="Record & Playback Macros", padding="10")
        macro_frame.pack(fill=tk.X, pady=5)
        
        self.record_btn = ttk.Button(macro_frame, text="⏺ Record Macro", command=self.toggle_macro_record)
        self.record_btn.pack(side=tk.LEFT, padx=3)
        
        ttk.Label(macro_frame, text="Macro Name:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(macro_frame, textvariable=self.macro_name_var, width=20).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(macro_frame, text="Save Macro", command=self.save_macro).pack(side=tk.LEFT, padx=3)
        
        ttk.Label(macro_frame, text="Play:").pack(side=tk.LEFT, padx=5)
        self.macro_combo = ttk.Combobox(macro_frame, width=20, state="readonly")
        self.macro_combo.pack(side=tk.LEFT, padx=5)
        ttk.Button(macro_frame, text="▶ Play", command=self.play_macro).pack(side=tk.LEFT, padx=3)
        ttk.Button(macro_frame, text="Delete", command=self.delete_macro).pack(side=tk.LEFT, padx=3)
        
        self.refresh_macros()
        
        # ===== RECORDED COMMANDS DISPLAY =====
        commands_frame = ttk.LabelFrame(parent_frame, text="Recorded Commands", padding="10")
        commands_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.commands_text = scrolledtext.ScrolledText(commands_frame, height=8, width=80, state=tk.DISABLED)
        self.commands_text.pack(fill=tk.BOTH, expand=True)
        
        ttk.Button(commands_frame, text="Clear Recording", command=self.clear_recording).pack(pady=5)
    
    
    
    def setup_settings_tab(self, parent):
        """Setup the Settings & Configuration tab"""
        parent_frame = ttk.Frame(parent, padding="10")
        parent_frame.pack(fill=tk.BOTH, expand=True)
        
        # ===== ARDUINO PIN CONFIGURATION =====
        pin_frame = ttk.LabelFrame(parent_frame, text="Arduino LED Pin Configuration", padding="10")
        pin_frame.pack(fill=tk.X, pady=5)
        
        info_text = """
Configure which pin your addressable LED (ARGB fan) is connected to on the Arduino.
Default: Pin 6 (VDG Header compatible)
After changing pins, you must recompile and upload the .ino sketch to the Arduino.
        """
        ttk.Label(pin_frame, text=info_text, justify=tk.LEFT, wraplength=400).pack(pady=10)
        
        config_subframe = ttk.Frame(pin_frame)
        config_subframe.pack(fill=tk.X, pady=10)
        
        ttk.Button(config_subframe, text="Save Config", command=self.save_arduino_config).pack(side=tk.LEFT, padx=10)
        
        status_frame = ttk.Frame(pin_frame)
        status_frame.pack(fill=tk.X, pady=5)
        ttk.Label(status_frame, text="Current Config: Pin ").pack(side=tk.LEFT)
        self.display_pin_label = ttk.Label(status_frame, text=str(self.led_pin), font=("Arial", 10, "bold"))
        self.display_pin_label.pack(side=tk.LEFT)
        ttk.Label(status_frame, text=", LEDs ").pack(side=tk.LEFT)
        self.display_led_count_label = ttk.Label(status_frame, text=str(self.num_leds), font=("Arial", 10, "bold"))
        self.display_led_count_label.pack(side=tk.LEFT)

        # ===== CODE SNIPPET =====
        snippet_frame = ttk.LabelFrame(parent_frame, text="Generated Arduino Code Snippet", padding="10")
        snippet_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.code_snippet_text = scrolledtext.ScrolledText(snippet_frame, height=8, width=80, font=("Consolas", 9))
        self.code_snippet_text.pack(fill=tk.BOTH, expand=True)
        self.update_code_snippet()
        
        # ===== MONITORING CONTROL =====
        mon_frame = ttk.LabelFrame(parent_frame, text="Monitoring Process", padding="10")
        mon_frame.pack(fill=tk.X, pady=5)
        self.monitoring_status = ttk.Label(mon_frame, text="Status: Ready", foreground="blue")
        self.monitoring_status.pack(side=tk.LEFT, padx=10)
        ttk.Button(mon_frame, text="Start", command=self.start_monitoring).pack(side=tk.LEFT, padx=5)
        ttk.Button(mon_frame, text="Stop", command=self.stop_monitoring).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(config_subframe, text="Save Config", command=self.save_arduino_config).pack(side=tk.LEFT, padx=10)
        ttk.Button(config_subframe, text="Load Config File", command=self.load_config_file_dialog).pack(side=tk.LEFT, padx=5)
        
        # ===== ARDUINO SKETCH HELPER =====
        sketch_frame = ttk.LabelFrame(parent_frame, text="Arduino Sketch Helper", padding="10")
        sketch_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        helper_text = """
To apply pin changes to your Arduino:

1. Open FanControl.ino in the Arduino IDE
2. Find the line: #define LED_PIN  6
3. Replace '6' with your desired pin (from configuration above)
4. (Optional) Find: #define NUM_LEDS  12
5. (Optional) Change to your actual LED count
6. Upload the sketch to your Arduino

Your current configuration (saved locally):
        """
        
        ttk.Label(sketch_frame, text=helper_text, justify=tk.LEFT, wraplength=550).pack(pady=5)
        
        conf_display = ttk.Frame(sketch_frame)
        conf_display.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(conf_display, text="Configured Pin:").pack(side=tk.LEFT, padx=5)
        self.display_pin_label = ttk.Label(conf_display, text=str(self.led_pin), font=("Courier", 11, "bold"))
        self.display_pin_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(conf_display, text="| Configured LEDs:").pack(side=tk.LEFT, padx=5)
        self.display_led_count_label = ttk.Label(conf_display, text=str(self.num_leds), font=("Courier", 11, "bold"))
        self.display_led_count_label.pack(side=tk.LEFT, padx=5)
        
        # ===== GENERATED CODE SNIPPET =====
        code_frame = ttk.LabelFrame(parent_frame, text="Code Snippet (for FanControl.ino)", padding="10")
        code_frame.pack(fill=tk.X, pady=5)
        
        code_text = scrolledtext.ScrolledText(code_frame, height=6, width=80, state=tk.DISABLED)
        code_text.pack(fill=tk.BOTH, expand=True)
        
        self.code_snippet_text = code_text
        self.update_code_snippet()
    
    def update_code_snippet(self):
        """Update the code snippet display"""
        snippet = f"""#define LED_PIN     {self.led_pin}          // Your configured LED pin
#define NUM_LEDS    {self.num_leds}         // Your configured LED count
#define LED_TYPE    WS2812B    // ARGB fans typically use WS2812B
#define COLOR_ORDER GRB"""
        
        self.code_snippet_text.config(state=tk.NORMAL)
        self.code_snippet_text.delete(1.0, tk.END)
        self.code_snippet_text.insert(tk.END, snippet)
        self.code_snippet_text.config(state=tk.DISABLED)
    
    def draw_graph(self):
        """Draw multi-channel oscilloscope-style graph with all signal channels"""
        if not self.graph_canvas:
            return
            
        canvas = self.graph_canvas
        canvas.delete("all")
        
        # Get canvas dimensions
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        
        # Use reasonable defaults if canvas hasn't been rendered
        if width < 100:
            width = 1000
        if height < 100:
            height = 400
        
        # Margins
        left_margin = 60
        right_margin = 20
        top_margin = 30
        bottom_margin = 50
        plot_width = width - left_margin - right_margin
        plot_height = height - top_margin - bottom_margin
        
        # Draw grid background
        canvas.create_rectangle(left_margin, top_margin, width - right_margin, height - bottom_margin,
                              fill="#0a0a1a", outline="#333")  # Dark background for oscilloscope feel
        
        # Draw grid lines (more visible for scope style)
        for i in range(0, 256, 51):
            y = height - bottom_margin - (i / 255.0) * plot_height
            canvas.create_line(left_margin, y, width - right_margin, y, fill="#1a1a3a", width=1)
        
        # Vertical grid lines
        num_x_divisions = 10
        for i in range(num_x_divisions + 1):
            x = left_margin + (i / num_x_divisions) * plot_width
            canvas.create_line(x, top_margin, x, height - bottom_margin, fill="#1a1a3a", width=1)
        
        # Draw axes
        canvas.create_line(left_margin, top_margin, left_margin, height - bottom_margin, fill="#00ff00", width=2)  # Y-axis (green)
        canvas.create_line(left_margin, height - bottom_margin, width - right_margin, height - bottom_margin, fill="#00ff00", width=2)  # X-axis
        
        # Y-axis labels and ticks (0-255)
        for i in range(0, 256, 51):
            y = height - bottom_margin - (i / 255.0) * plot_height
            canvas.create_line(left_margin - 5, y, left_margin, y, fill="#00ff00", width=2)
            canvas.create_text(left_margin - 15, y, text=str(i), anchor=tk.E, font=("Courier", 7), fill="#00ff00")
        
        # X-axis labels
        canvas.create_text(width // 2, height - 10, text="Time (samples)", anchor=tk.CENTER, font=("Courier", 9, "bold"), fill="#00ff00")
        canvas.create_text(20, height // 2, text="Value", anchor=tk.CENTER, angle=90, font=("Courier", 9, "bold"), fill="#00ff00")
        
        # Draw all enabled channels
        has_data = False
        # Use keys() to avoid complex tuple unpacking lints
        for key in self.telemetry_channels.keys():
            info = self.telemetry_channels[key]
            if not bool(info.get('show', False)):
                continue
                
            history_data = list(info.get('history', []))
            h_len_actual = len(history_data)
            
            if h_len_actual > 1:
                has_data = True
                points = []
                
                h_divisor = float(max(1, h_len_actual - 1))
                for idx, value in enumerate(history_data):
                    try:
                        v_float = float(value)
                    except (ValueError, TypeError):
                        v_float = 0.0
                        
                    x_pos = float(left_margin) + (float(idx) / h_divisor) * float(plot_width)
                    # Normalize value (0-255 range)
                    norm_val = min(max(v_float / 255.0, 0.0), 1.0)
                    y_pos = float(height) - float(bottom_margin) - norm_val * float(plot_height)
                    points.append((float(x_pos), float(y_pos)))
                
                # Draw lines connecting points
                chan_color = str(info.get('color', '#00ff00'))
                if len(points) > 1:
                    for i in range(len(points) - 1):
                        canvas.create_line(points[i][0], points[i][1], points[i+1][0], points[i+1][1],
                                         fill=chan_color, width=2)
                
                # Draw data points (small circles)
                for i, pt in enumerate(points):
                    px, py = pt
                    r = 2.0
                    canvas.create_oval(px - r, py - r, px + r, py + r, 
                                     fill=chan_color, outline=chan_color)
                    # Highlight the latest point
                    if i == len(points) - 1:
                        canvas.create_oval(px - 4.0, py - 4.0, px + 4.0, py + 4.0, 
                                         outline=chan_color, width=2)
        
        # Draw legend
        leg_y = float(top_margin) + 10.0
        leg_x = float(width) - float(right_margin) - 150.0
        for key in self.telemetry_channels.keys():
            info = self.telemetry_channels[key]
            if bool(info.get('show', False)):
                c = str(info.get('color', '#00ff00'))
                canvas.create_rectangle(leg_x, leg_y, leg_x + 12.0, leg_y + 12.0, 
                                       fill=c, outline=c)
                canvas.create_text(leg_x + 18.0, leg_y + 6.0, text=str(info.get('name', key)),
                                 anchor=tk.W, font=("Courier", 8), fill=c)
                leg_y += 15.0
        
        # Empty state message
        if not has_data:
            msg = "🔌 Multi-Channel Oscilloscope\n\nConnect Arduino and adjust settings to see live signals\nDisplays: Brightness, Mode, Speed, Intensity, Saturation, Hue, RGB"
            canvas.create_text(width // 2, height // 2, text=msg,
                             anchor=tk.CENTER, font=("Arial", 11), fill="#00ff00", justify=tk.CENTER)
    
    def start_monitoring(self):
        """Start monitoring brightness changes"""
        self.monitoring_enabled = True
        self.monitoring_status.config(text="Status: Monitoring...", foreground="green")
        self.add_history("[MONITORING STARTED]")
    
    def stop_monitoring(self):
        """Stop monitoring brightness changes"""
        self.monitoring_enabled = False
        self.monitoring_status.config(text="Status: Stopped", foreground="red")
        self.add_history("[MONITORING STOPPED]")
    
    def clear_graph(self):
        """Clear all telemetry channel data"""
        for channel in self.telemetry_channels.values():
            channel['history'].clear()
        self.pwm_timestamps.clear()
        self.draw_graph()
        self.update_stats()
        self.add_history("[OSCILLOSCOPE CLEARED]")
    
    def toggle_auto_update(self):
        """Toggle automatic graph updates"""
        self.auto_update_graph = self.auto_update_var.get()
        if self.auto_update_graph:
            self.add_history("[AUTO-UPDATE ENABLED]")
            self.schedule_graph_update()
        else:
            self.add_history("[AUTO-UPDATE DISABLED]")
    
    def schedule_graph_update(self):
        """Schedule the next graph update"""
        if self.auto_update_graph and self.graph_canvas:
            self.draw_graph()
            self.root.after(self.graph_update_interval, self.schedule_graph_update)
    
    
    def update_pwm_graph(self, brightness):
        """Update brightness channel in the oscilloscope"""
        # Capture brightness data for live visualization
        self.telemetry_channels['BR']['history'].append(brightness)
        self.pwm_timestamps.append(datetime.now())
        
        # Update stats
        self.update_stats()
        
        # Redraw only if auto-update is disabled (the scheduler handles periodic updates)
        if not self.auto_update_graph and self.graph_canvas:
            self.draw_graph()
    
    def update_stats(self):
        """Update statistics display from brightness channel"""
        # Guard: only update if labels have been created
        if not hasattr(self, 'current_brightness_label'):
            return
            
        brightness_history = self.telemetry_channels['BR']['history']
        if brightness_history:
            current = brightness_history[-1]
            min_val = min(brightness_history)
            max_val = max(brightness_history)
            avg_val = sum(brightness_history) / len(brightness_history)
            
            self.current_brightness_label.config(text=str(current))
            self.min_brightness_label.config(text=str(min_val))
            self.max_brightness_label.config(text=str(max_val))
            self.avg_brightness_label.config(text=f"{avg_val:.1f}")
            self.samples_label.config(text=str(len(brightness_history)))
    
    def toggle_channel(self, channel_key):
        """Toggle a channel's visibility on the oscilloscope"""
        if channel_key in self.channel_vars and channel_key in self.telemetry_channels:
            self.telemetry_channels[channel_key]['show'] = self.channel_vars[channel_key].get()
            self.draw_graph()
            channel_name = self.telemetry_channels[channel_key]['name']
            status = "ENABLED" if self.telemetry_channels[channel_key]['show'] else "DISABLED"
            self.add_history(f"[CHANNEL {channel_name} {status}]")
    
    def save_arduino_config(self):
        """Save Arduino pin configuration"""
        try:
            pin = int(self.pin_var.get())
            led_count = int(self.led_count_var.get())
            
            if not (0 <= pin <= 13):
                messagebox.showerror("Invalid Pin", "Pin must be between 0 and 13")
                return
            
            if not (1 <= led_count <= 60):
                messagebox.showerror("Invalid LED Count", "LED count must be between 1 and 60")
                return
            
            self.led_pin = pin
            self.num_leds = led_count
            
            config = {"led_pin": pin, "num_leds": led_count}
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            self.display_pin_label.config(text=str(pin))
            self.display_led_count_label.config(text=str(led_count))
            self.update_code_snippet()
            
            self.add_history(f"[CONFIG SAVED] Pin {pin}, LEDs {led_count}")
            messagebox.showinfo("Success", f"Configuration saved!\n\nPin: {pin}\nLEDs: {led_count}\n\nRemember to update your Arduino sketch and reupload!")
        except ValueError:
            messagebox.showerror("Invalid Input", "Pin and LED count must be numbers")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {str(e)}")
    
    def load_arduino_config(self):
        """Load Arduino pin configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.led_pin = config.get("led_pin", 6)
                    self.num_leds = config.get("num_leds", 12)
                    self.pin_var.set(str(self.led_pin))
                    self.led_count_var.set(str(self.num_leds))
        except:
            pass
    
    def load_config_file_dialog(self):
        """Show information about loading config"""
        messagebox.showinfo("Arduino Config", 
            f"Current configuration:\n\n"
            f"LED Pin: {self.led_pin}\n"
            f"Number of LEDs: {self.num_leds}\n\n"
            f"This is loaded from: arduino_config.json\n"
            f"Location: {self.config_file}")

    
    def detect_ports(self):
        """Detect available COM ports"""
        ports = []
        for port, desc, hwid in serial.tools.list_ports.comports():
            ports.append(port)
        
        if ports:
            self.port_combo['values'] = ports
            self.port_combo.current(0)
        else:
            self.port_combo['values'] = []
    
    def connect_port(self):
        """Connect to the selected COM port"""
        if self.is_connected:
            self.disconnect_port()
            return
        
        port = self.port_var.get()
        baud = int(self.baud_var.get())
        
        if not port:
            messagebox.showerror("Error", "Please select a COM port")
            return
        
        try:
            self.serial_port = serial.Serial(port, baud, timeout=1)
            self.is_connected = True
            self.status_label.config(text=f"✓ Connected ({port})", foreground="green")
            self.connect_btn.config(text="Disconnect")
            self.port_combo.config(state=tk.DISABLED)
            
            self.read_thread = threading.Thread(target=self.read_serial, daemon=True)
            self.read_thread.start()
            
            self.add_history(f"[CONNECTED] {port} @ {baud} baud")
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
            self.is_connected = False
    
    def disconnect_port(self):
        """Disconnect from the COM port"""
        if self.serial_port:
            self.serial_port.close()
        
        self.is_connected = False
        self.status_label.config(text="✗ Disconnected", foreground="red")
        self.connect_btn.config(text="Connect")
        self.port_combo.config(state="readonly")
        self.add_history("[DISCONNECTED]")
    
    def send_command(self, cmd):
        """Send a command to the Arduino and capture PWM data if applicable"""
        if not self.is_connected:
            messagebox.showwarning("Not Connected", "Please connect to a COM port first")
            return
        
        # Record command if macro recording is enabled
        if self.macro_recording:
            self.recorded_commands.append(cmd)
            self.update_commands_display()
        
        # Add newline to single character commands if not already present
        if len(cmd) == 1:
            cmd = cmd + "\n"
        
        # Extract and capture PWM data from brightness commands (~B format)
        # Example: "~B128\n" sets brightness to 128
        if cmd.startswith("~B") and cmd.endswith("\n"):
            try:
                pwm_val = int(cmd[2:-1])  # Extract the numeric value
                if 0 <= pwm_val <= 255:
                    self.update_pwm_graph(pwm_val)
            except (ValueError, IndexError):
                pass
        
        try:
            self.serial_port.write(cmd.encode())
            self.add_history(f"→ Sent: {cmd.strip()}")
        except Exception as e:
            messagebox.showerror("Send Error", f"Failed to send command: {str(e)}")
            self.is_connected = False
            self.status_label.config(text="✗ Connection Lost", foreground="red")
    
    def send_command_track(self, cmd, name=""):
        """Send command and update status"""
        self.send_command(cmd)
        if name:
            if cmd in ['1','2','3','4','5','6','7','8','9','0']:
                self.current_color = name
            else:
                self.current_effect = name
            self.info_label.config(text=f"Effect: {self.current_effect} | Color: {self.current_color}")
    
    def read_serial(self):
        """Read from serial port in a background thread and parse telemetry data"""
        while self.is_connected:
            try:
                if self.serial_port.in_waiting:
                    data = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                    if data:
                        # Try to parse as JSON telemetry data
                        if data.startswith('{'):
                            try:
                                telemetry = json.loads(data)
                                # Update telemetry channels with new data
                                if 'BR' in telemetry:
                                    self.telemetry_channels['BR']['history'].append(telemetry['BR'])
                                    self.brightness_val = telemetry['BR']
                                if 'M' in telemetry:
                                    self.telemetry_channels['M']['history'].append(telemetry['M'])
                                if 'S' in telemetry:
                                    self.telemetry_channels['S']['history'].append(telemetry['S'])
                                    self.speed_val = telemetry['S']
                                    # If binding is enabled, compute tipsy scale from measured speed
                                    try:
                                        if self.bind_tipsy_var.get():
                                            s_val = int(telemetry['S'])
                                            # Map measured speed (1-200) to tipsy scale (255 fast -> 50 slow)
                                            tipsy_val = int(self.map_range(s_val, 1, 200, 255, 50))
                                            # Schedule UI update and send command from main thread
                                            self.root.after(0, lambda v=tipsy_val: self.apply_bound_tipsy(v))
                                    except Exception:
                                        pass
                                if 'I' in telemetry:
                                    self.telemetry_channels['I']['history'].append(telemetry['I'])
                                    self.intensity_val = telemetry['I']
                                if 'SAT' in telemetry:
                                    self.telemetry_channels['SAT']['history'].append(telemetry['SAT'])
                                    self.saturation_val = telemetry['SAT']
                                if 'H' in telemetry:
                                    self.telemetry_channels['H']['history'].append(telemetry['H'])
                                    self.hue_rotation_val = telemetry['H']
                                if 'R' in telemetry:
                                    self.telemetry_channels['R']['history'].append(telemetry['R'])
                                if 'G' in telemetry:
                                    self.telemetry_channels['G']['history'].append(telemetry['G'])
                                if 'BL' in telemetry:
                                    self.telemetry_channels['BL']['history'].append(telemetry['BL'])
                                if 'TS' in telemetry:
                                    self.telemetry_channels['TS']['history'].append(telemetry['TS'])
                                self.pwm_timestamps.append(datetime.now())
                            except json.JSONDecodeError:
                                # Not JSON, treat as regular message
                                self.add_history(f"← Received: {data}")
                        else:
                            # Regular text message
                            self.add_history(f"← Received: {data}")
            except:
                break
    
    def add_history(self, message):
        """Add message to command history and save to file"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        timestamped_msg = f"[{timestamp}] {message}"
        
        self.history_text.config(state=tk.NORMAL)
        self.history_text.insert(tk.END, timestamped_msg + "\n")
        self.history_text.see(tk.END)
        self.history_text.config(state=tk.DISABLED)
        self.command_history.append(timestamped_msg)
        
        # Save to file
        self.save_history()
    
    def clear_history(self):
        """Clear command history"""
        self.history_text.config(state=tk.NORMAL)
        self.history_text.delete(1.0, tk.END)
        self.history_text.config(state=tk.DISABLED)
        self.command_history.clear()
        
        # Delete history file
        try:
            if os.path.exists(self.history_file):
                os.remove(self.history_file)
        except:
            pass
    
    def on_brightness_change(self, val):
        """Handle brightness slider changes"""
        try:
            v = int(float(val))
            self.brightness_val = v
            if self.brightness_label:
                self.brightness_label.config(text=str(v))
            self.update_pwm_graph(v)
        except:
            pass
    
    def on_speed_change(self, val):
        """Handle speed slider changes"""
        try:
            v = int(float(val))
            self.speed_val = v
            if self.speed_label:
                self.speed_label.config(text=f"{v}ms")
        except:
            pass
    
    def on_intensity_change(self, val):
        """Handle intensity slider changes"""
        try:
            v = int(float(val))
            self.intensity_val = v
            if self.intensity_label:
                self.intensity_label.config(text=str(v))
        except:
            pass

    def on_saturation_change(self, val):
        """Handle saturation slider changes"""
        try:
            v = int(float(val))
            self.saturation_val = v
            if self.saturation_label:
                self.saturation_label.config(text=str(v))
        except:
            pass

    def on_hue_change(self, val):
        """Handle hue rotation speed slider changes"""
        try:
            v = int(float(val))
            self.hue_rotation_val = v
            if self.hue_rotation_label:
                self.hue_rotation_label.config(text=str(v))
        except:
            pass

    def on_tipsy_sync_change(self, val):
        """Handle tipsy sync slider changes (does not send until release)"""
        try:
            v = int(float(val))
        except:
            return
        self.tipsy_sync_value = v

    def send_tipsy_sync(self):
        """Send current tipsy sync value to Arduino (~T<value>\n)"""
        val = int(self.tipsy_sync_value)
        # Ensure proper range
        val = max(32, min(255, val))
        self.send_command(f"~T{val}\n")
        self.add_history(f"→ Sent: Tipsy Sync {val}")

    def toggle_bind_tipsy(self):
        """Enable/disable binding of tipsy sync to measured speed"""
        if self.bind_tipsy_var.get():
            self.add_history("[TIPSY BIND ENABLED]")
            # When enabling, immediately compute from last speed sample if available
            try:
                if self.telemetry_channels['S']['history']:
                    last_s = self.telemetry_channels['S']['history'][-1]
                    tipsy_val = int(self.map_range(int(last_s), 1, 200, 255, 50))
                    self.apply_bound_tipsy(tipsy_val)
            except Exception:
                pass
        else:
            self.add_history("[TIPSY BIND DISABLED]")

    def apply_bound_tipsy(self, val):
        """Apply a tipsy value computed from telemetry: update slider and send to Arduino"""
        try:
            v = int(max(32, min(255, val)))
            self.tipsy_sync_value = v
            if hasattr(self, 'tipsy_slider'):
                try:
                    self.tipsy_slider.set(v)
                except Exception:
                    pass
            # Send to Arduino
            self.send_command(f"~T{v}\n")
            self.add_history(f"→ Sent (bound): Tipsy Sync {v}")
        except Exception:
            pass

    def map_range(self, x, in_min, in_max, out_min, out_max):
        """Simple linear mapping helper"""
        if in_max == in_min:
            return out_min
        ratio = float(x - in_min) / float(in_max - in_min)
        return out_min + (ratio * (out_max - out_min))
    
    def pick_custom_color(self):
        """Open color picker dialog"""
        color = colorchooser.askcolor(color=self.custom_rgb, title="Pick Custom RGB Color")
        if color[0]:
            rgb = tuple(int(c) for c in color[0])
            self.custom_rgb = rgb
            self.rgb_label.config(text=f"RGB: {rgb}")
            self.color_canvas.config(bg=color[1])
    
    def send_custom_rgb(self):
        """Send custom RGB color to Arduino"""
        if not self.is_connected:
            messagebox.showwarning("Not Connected", "Please connect to Arduino first")
            return
        
        r, g, b = self.custom_rgb
        
        try:
            # Format: G<r>,<g>,<b> (e.g., G255,128,64)
            command = f"G{r},{g},{b}\n"
            
            # Record if macro recording enabled
            if self.macro_recording:
                self.recorded_commands.append(command)
                self.update_commands_display()
            
            self.serial_port.write(command.encode())
            self.add_history(f"→ Sent Custom RGB: ({r},{g},{b})")
            messagebox.showinfo("Success", f"Sent RGB({r},{g},{b})\n\nFormat sent: G{r},{g},{b}\nUpdate Arduino to parse custom RGB")
        except Exception as e:
            messagebox.showerror("Send Error", f"Failed to send RGB: {str(e)}")
            self.is_connected = False
            self.status_label.config(text="✗ Connection Lost", foreground="red")

    # -------- Send numeric settings to Arduino (use prefix ~ + type + value + newline)
    def send_brightness(self):
        val = int(self.brightness_val)
        cmd = f"~B{val}\n"
        self._send_numeric_cmd(cmd, f"Brightness set to {val}")
        # Update PWM graph
        self.update_pwm_graph(val)

    def send_speed(self):
        val = int(self.speed_val)
        cmd = f"~V{val}\n"
        self._send_numeric_cmd(cmd, f"Speed set to {val}ms")

    def send_intensity(self):
        val = int(self.intensity_val)
        cmd = f"~I{val}\n"
        self._send_numeric_cmd(cmd, f"Intensity set to {val}")

    def send_saturation(self):
        val = int(self.saturation_val)
        cmd = f"~U{val}\n"
        self._send_numeric_cmd(cmd, f"Saturation set to {val}")

    def send_hue(self):
        val = int(self.hue_rotation_val)
        cmd = f"~H{val}\n"
        self._send_numeric_cmd(cmd, f"Hue speed set to {val}")

    def _send_numeric_cmd(self, cmd, history_msg=None):
        if not self.is_connected:
            messagebox.showwarning("Not Connected", "Please connect to Arduino first")
            return

        try:
            if self.macro_recording:
                self.recorded_commands.append(cmd)
                self.update_commands_display()

            self.serial_port.write(cmd.encode())
            self.add_history(f"→ {history_msg if history_msg else cmd.strip()}")
        except Exception as e:
            messagebox.showerror("Send Error", f"Failed to send setting: {str(e)}")
            self.is_connected = False
            self.status_label.config(text="✗ Connection Lost", foreground="red")
    
    def toggle_macro_record(self):
        """Toggle macro recording on/off"""
        self.macro_recording = not self.macro_recording
        if self.macro_recording:
            self.recorded_commands = []
            self.record_btn.config(text="⏹ Stop Recording")
            self.add_history("[MACRO RECORD STARTED]")
            self.update_commands_display()
        else:
            self.record_btn.config(text="⏺ Record Macro")
            self.add_history("[MACRO RECORD STOPPED]")
            self.update_commands_display()
    
    def update_commands_display(self):
        """Update the commands display in macro tab"""
        self.commands_text.config(state=tk.NORMAL)
        self.commands_text.delete(1.0, tk.END)
        for i, cmd in enumerate(self.recorded_commands):
            self.commands_text.insert(tk.END, f"{i+1}. {cmd}\n")
        self.commands_text.config(state=tk.DISABLED)
    
    def clear_recording(self):
        """Clear recorded commands"""
        self.recorded_commands = []
        self.update_commands_display()
        self.add_history("[RECORDING CLEARED]")
    
    def save_macro(self):
        """Save recorded macro"""
        if not self.recorded_commands:
            messagebox.showwarning("Empty Macro", "No commands recorded yet")
            return
        
        name = self.macro_name_var.get()
        if not name:
            messagebox.showerror("Error", "Enter macro name")
            return
        
        self.macros[name] = self.recorded_commands.copy()
        self.save_macros()
        self.refresh_macros()
        self.add_history(f"[MACRO SAVED] {name} with {len(self.recorded_commands)} commands")
        messagebox.showinfo("Success", f"Macro '{name}' saved!")
    
    def play_macro(self):
        """Play selected macro"""
        name = self.macro_combo.get()
        if not name:
            messagebox.showwarning("Error", "Select a macro to play")
            return
        
        if not self.is_connected:
            messagebox.showwarning("Not Connected", "Please connect to Arduino first")
            return
        
        commands = self.macros.get(name, [])
        self.add_history(f"[MACRO PLAYING] {name}")
        for cmd in commands:
            self.send_command(cmd)
            self.root.update()
    
    def delete_macro(self):
        """Delete selected macro"""
        name = self.macro_combo.get()
        if not name:
            return
        
        if messagebox.askyesno("Confirm", f"Delete macro '{name}'?"):
            del self.macros[name]
            self.save_macros()
            self.refresh_macros()
            self.add_history(f"[MACRO DELETED] {name}")
    
    def refresh_macros(self):
        """Refresh macro list"""
        self.macro_combo['values'] = list(self.macros.keys())
    
    def save_preset(self):
        """Save current settings as preset"""
        name = self.preset_name_var.get()
        if not name:
            messagebox.showerror("Error", "Enter preset name")
            return
        
        preset = {
            "brightness": self.brightness_val,
            "speed": self.speed_val,
            "intensity": self.intensity_val,
            "saturation": self.saturation_val,
            "hue_rotation": self.hue_rotation_val,
            "effect": self.current_effect,
            "color": self.current_color,
        }
        
        try:
            presets = {}
            if os.path.exists(self.presets_file):
                with open(self.presets_file, 'r') as f:
                    presets = json.load(f)
            
            presets[name] = preset
            with open(self.presets_file, 'w') as f:
                json.dump(presets, f, indent=2)
            
            self.refresh_presets()
            self.add_history(f"[PRESET SAVED] {name}")
            messagebox.showinfo("Success", f"Preset '{name}' saved!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save preset: {str(e)}")
    
    def load_preset(self):
        """Load selected preset"""
        name = self.preset_combo.get()
        if not name:
            messagebox.showwarning("Error", "Select a preset to load")
            return
        
        try:
            with open(self.presets_file, 'r') as f:
                presets = json.load(f)
            
            preset = presets.get(name)
            if not preset:
                return
            
            self.brightness_slider.set(preset.get("brightness", 255))
            self.speed_slider.set(preset.get("speed", 10))
            self.intensity_slider.set(preset.get("intensity", 128))
            self.saturation_slider.set(preset.get("saturation", 255))
            self.hue_rotation_slider.set(preset.get("hue_rotation", 1))
            
            self.add_history(f"[PRESET LOADED] {name}")
            messagebox.showinfo("Success", f"Preset '{name}' loaded!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load preset: {str(e)}")
    
    def delete_preset(self):
        """Delete selected preset"""
        name = self.preset_combo.get()
        if not name:
            return
        
        if messagebox.askyesno("Confirm", f"Delete preset '{name}'?"):
            try:
                with open(self.presets_file, 'r') as f:
                    presets = json.load(f)
                del presets[name]
                with open(self.presets_file, 'w') as f:
                    json.dump(presets, f, indent=2)
                self.refresh_presets()
                self.add_history(f"[PRESET DELETED] {name}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete preset: {str(e)}")
    
    def refresh_presets(self):
        """Refresh preset list"""
        try:
            if os.path.exists(self.presets_file):
                with open(self.presets_file, 'r') as f:
                    presets = json.load(f)
                self.preset_combo['values'] = list(presets.keys())
        except:
            pass
    
    def load_presets(self):
        """Load presets from file"""
        self.refresh_presets()
    
    def load_macros(self):
        """Load macros from file"""
        try:
            if os.path.exists(self.macros_file):
                with open(self.macros_file, 'r') as f:
                    self.macros = json.load(f)
            self.refresh_macros()
        except:
            self.macros = {}
    
    def save_macros(self):
        """Save macros to file"""
        try:
            with open(self.macros_file, 'w') as f:
                json.dump(self.macros, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save macros: {str(e)}")
    
    def load_history(self):
        """Load command history from file"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    self.command_history = data.get("history", [])
                    # If the history widget exists, display loaded history
                    if hasattr(self, 'history_text'):
                        self.history_text.config(state=tk.NORMAL)
                        for msg in self.command_history[-100:]:  # Show last 100 entries
                            self.history_text.insert(tk.END, msg + "\n")
                        self.history_text.see(tk.END)
                        self.history_text.config(state=tk.DISABLED)
        except:
            self.command_history = []
    
    def save_history(self):
        """Save command history to file"""
        try:
            # Limit history to last 1000 entries to prevent file bloat
            max_entries = 1000
            history_to_save = self.command_history[-max_entries:] if len(self.command_history) > max_entries else self.command_history
            
            data = {"history": history_to_save}
            with open(self.history_file, 'w') as f:
                json.dump(data, f, indent=2)
        except:
            pass  # Silently fail on history save
    
    def play_favorite(self, effect, speed, color):
        """Play a favorite combination"""
        if not self.is_connected:
            messagebox.showwarning("Not Connected", "Connect to Arduino first")
            return
        
        self.send_command(color)
        self.send_command(effect)
        self.add_history(f"[FAVORITE] Effect:{effect} Speed:{speed}ms Color:{color}")

if __name__ == "__main__":
    root = tk.Tk()
    gui = FanControlGUI(root)
    root.mainloop()
