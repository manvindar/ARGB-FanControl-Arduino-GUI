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
        
        # Pin configuration
        self.config_file = os.path.join(os.path.dirname(__file__), "arduino_config.json")
        self.led_pin = 6  # Default pin
        self.num_leds = 12  # Default LED count
        
        self.load_presets()
        self.load_macros()
        self.load_arduino_config()
        
        self.setup_ui()
        # Load history after UI exists so the widget can be updated
        self.load_history()
        self.detect_ports()
        
    def setup_ui(self):
        # Create notebook (tabs) for organized interface
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Quick Control
        quick_tab = ttk.Frame(notebook)
        notebook.add(quick_tab, text="Quick Control")
        self.setup_quick_tab(quick_tab)
        
        # Tab 2: Sliders & Custom Colors
        advanced_tab = ttk.Frame(notebook)
        notebook.add(advanced_tab, text="Sliders & Colors")
        self.setup_advanced_tab(advanced_tab)
        
        # Tab 3: Presets & Macros
        preset_tab = ttk.Frame(notebook)
        notebook.add(preset_tab, text="Presets & Macros")
        self.setup_preset_tab(preset_tab)
        
        # Tab 4: Status & Favorites
        status_tab = ttk.Frame(notebook)
        notebook.add(status_tab, text="Status & Favorites")
        self.setup_status_tab(status_tab)
        
        # Tab 5: PWM Graph & Monitoring
        graph_tab = ttk.Frame(notebook)
        notebook.add(graph_tab, text="PWM Graph")
        self.setup_graph_tab(graph_tab)
        
        # Tab 6: Settings & Configuration
        settings_tab = ttk.Frame(notebook)
        notebook.add(settings_tab, text="Settings")
        self.setup_settings_tab(settings_tab)
        
        # Bottom status bar
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="Status: Disconnected", foreground="red")
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        self.info_label = ttk.Label(status_frame, text="")
        self.info_label.pack(side=tk.LEFT, padx=10)

        # ===== Persistent Command History (bottom, visible across tabs) =====
        history_frame = ttk.LabelFrame(self.root, text="Command History", padding="5")
        history_frame.pack(fill=tk.BOTH, side=tk.BOTTOM, padx=10, pady=5)
        self.history_text = scrolledtext.ScrolledText(history_frame, height=10, width=120, state=tk.DISABLED)
        self.history_text.pack(fill=tk.BOTH, expand=True)
    
    def setup_quick_tab(self, parent):
        parent_frame = ttk.Frame(parent, padding="10")
        parent_frame.pack(fill=tk.BOTH, expand=True)
        
        # ===== CONNECTION SECTION =====
        conn_frame = ttk.LabelFrame(parent_frame, text="Connection", padding="10")
        conn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(conn_frame, text="COM Port:").pack(side=tk.LEFT, padx=5)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(conn_frame, textvariable=self.port_var, width=12, state="readonly")
        self.port_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(conn_frame, text="Baud:").pack(side=tk.LEFT, padx=5)
        self.baud_var = tk.StringVar(value="9600")
        ttk.Combobox(conn_frame, textvariable=self.baud_var, values=["9600", "115200"], width=8, state="readonly").pack(side=tk.LEFT, padx=5)
        
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.connect_port, width=12)
        self.connect_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(conn_frame, text="Refresh Ports", command=self.detect_ports, width=12).pack(side=tk.LEFT, padx=5)
        
        # ===== COLORS SECTION =====
        color_frame = ttk.LabelFrame(parent_frame, text="Colors", padding="10")
        color_frame.pack(fill=tk.X, pady=5)
        
        colors = [("Red", "1"), ("Green", "2"), ("Blue", "3"), ("White", "4"), 
                  ("Cyan", "5"), ("Magenta", "6"), ("Yellow", "7"), ("Orange", "8"),
                  ("Pink", "9"), ("Purple", "0")]
        
        for i, (name, cmd) in enumerate(colors):
            ttk.Button(color_frame, text=name, width=10, command=lambda c=cmd, n=name: self.send_command_track(c, n)).grid(row=i//5, column=i%5, padx=3, pady=3)
        
        # ===== MULTICOLOR QUICK OPTIONS =====
        mc_frame = ttk.Frame(color_frame)
        mc_frame.grid(row=2, column=0, columnspan=5, pady=(8,0))
        ttk.Label(mc_frame, text="Multi-Color Options:").pack(side=tk.LEFT, padx=5)
        ttk.Button(mc_frame, text="Multi Rainbow", width=14, command=lambda: (self.send_command_track('J','Multi-Color'), self.send_command('~H2\n'))).pack(side=tk.LEFT, padx=4)
        ttk.Button(mc_frame, text="Pastel Cycle", width=14, command=lambda: (self.send_command_track('J','Multi-Color'), self.send_command('~I200\n'), self.send_command('~H1\n'))).pack(side=tk.LEFT, padx=4)
        ttk.Button(mc_frame, text="RGB Cycle", width=12, command=lambda: (self.send_command_track('J','Multi-Color'), self.send_command('~I255\n'), self.send_command('~H3\n'))).pack(side=tk.LEFT, padx=4)
        
        # ===== EFFECTS SECTION (2 ROWS) =====
        effect_frame = ttk.LabelFrame(parent_frame, text="Effects (12 Available)", padding="10")
        effect_frame.pack(fill=tk.X, pady=5)
        
        effects = [("Rainbow", "R"), ("Pulse", "P"), ("Static", "S"), ("Wipe", "W"),
               ("Theater", "T"), ("Sparkle", "K"), ("Sinelon", "N"), ("BPM", "B"),
               ("Confetti", "C"), ("Fire", "F"), ("Strobe", "X"), ("Breathing", "E"),
               ("Tipsy", "Y"), ("Multi-Color", "J")]
        
        for i, (name, cmd) in enumerate(effects):
            ttk.Button(effect_frame, text=name, width=11, command=lambda c=cmd, n=name: self.send_command_track(c, n)).grid(row=i//6, column=i%6, padx=3, pady=3)
        
        # ===== BRIGHTNESS & SPEED CONTROLS =====
        control_frame = ttk.Frame(parent_frame)
        control_frame.pack(fill=tk.X, pady=5)
        
        brightness_frame = ttk.LabelFrame(control_frame, text="Brightness", padding="10")
        brightness_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Button(brightness_frame, text="Low (25%)", command=lambda: self.send_command("!")).pack(side=tk.LEFT, padx=2)
        ttk.Button(brightness_frame, text="Medium (50%)", command=lambda: self.send_command("@")).pack(side=tk.LEFT, padx=2)
        ttk.Button(brightness_frame, text="+", width=3, command=lambda: self.send_command("+")).pack(side=tk.LEFT, padx=2)
        ttk.Button(brightness_frame, text="-", width=3, command=lambda: self.send_command("-")).pack(side=tk.LEFT, padx=2)
        
        speed_frame = ttk.LabelFrame(control_frame, text="Speed Presets", padding="10")
        speed_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Original single-char presets (kept for compatibility)
        speeds = [("VFast", "Q"), ("Fast", "D"), ("Med", "V"), ("Slow", "Z"), ("VSlow", "M")]
        for name, cmd in speeds:
            ttk.Button(speed_frame, text=name, width=7, command=lambda c=cmd: self.send_command(c)).pack(side=tk.LEFT, padx=2)

        # Additional numeric presets (send ~V<value> so Arduino uses numeric speed)
        more = [("Ultra", 2), ("Super", 8), ("Very Fast", 12), ("Normal", 30), ("Slower", 80), ("Turtle", 150), ("Molasses", 250)]
        for name, val in more:
            ttk.Button(speed_frame, text=name, width=8, command=lambda v=val: self.send_command(f"~V{v}\n")).pack(side=tk.LEFT, padx=2)
        
        # ===== CUSTOMIZATION =====
        custom_frame = ttk.LabelFrame(parent_frame, text="Customization", padding="10")
        custom_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(custom_frame, text="Intensity:").pack(side=tk.LEFT, padx=5)
        ttk.Button(custom_frame, text="−", width=2, command=lambda: self.send_command("#")).pack(side=tk.LEFT, padx=2)
        ttk.Button(custom_frame, text="+", width=2, command=lambda: self.send_command("$")).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(custom_frame, text="| Saturation:").pack(side=tk.LEFT, padx=5)
        ttk.Button(custom_frame, text="−", width=2, command=lambda: self.send_command("%")).pack(side=tk.LEFT, padx=2)
        ttk.Button(custom_frame, text="+", width=2, command=lambda: self.send_command("^")).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(custom_frame, text="| Hue Speed:").pack(side=tk.LEFT, padx=5)
        ttk.Button(custom_frame, text="−", width=2, command=lambda: self.send_command("&")).pack(side=tk.LEFT, padx=2)
        ttk.Button(custom_frame, text="+", width=2, command=lambda: self.send_command("*")).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(custom_frame, text="| Reverse LEDs", command=lambda: self.send_command(";")).pack(side=tk.LEFT, padx=2)
        ttk.Button(custom_frame, text="Mirror", command=lambda: self.send_command("'")).pack(side=tk.LEFT, padx=2)
        ttk.Button(custom_frame, text="Wave Dir", command=lambda: self.send_command("[")).pack(side=tk.LEFT, padx=2)
        ttk.Button(custom_frame, text="Rainbow Modes", command=lambda: self.send_command("]")).pack(side=tk.LEFT, padx=2)

        # ===== QUICK SLIDERS (compact, visible on Quick Control tab) =====
        quick_sliders = ttk.LabelFrame(parent_frame, text="Quick Sliders", padding="8")
        quick_sliders.pack(fill=tk.X, pady=5)

        # Brightness (compact)
        ttk.Label(quick_sliders, text="Bright").pack(side=tk.LEFT, padx=4)
        self.q_bright = ttk.Scale(quick_sliders, from_=0, to=255, orient=tk.HORIZONTAL, command=self.on_q_brightness_change)
        self.q_bright.set(self.brightness_val)
        self.q_bright.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.q_bright.bind("<ButtonRelease-1>", lambda e: (self.bright_slider.set(int(float(self.q_bright.get()))), self.send_brightness()))

        # Intensity (compact)
        ttk.Label(quick_sliders, text="Intensity").pack(side=tk.LEFT, padx=4)
        self.q_intensity = ttk.Scale(quick_sliders, from_=0, to=255, orient=tk.HORIZONTAL, command=self.on_q_intensity_change)
        self.q_intensity.set(self.intensity_val)
        self.q_intensity.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.q_intensity.bind("<ButtonRelease-1>", lambda e: (self.intensity_slider.set(int(float(self.q_intensity.get()))), self.send_intensity()))

        # Saturation (compact)
        ttk.Label(quick_sliders, text="Sat").pack(side=tk.LEFT, padx=4)
        self.q_saturation = ttk.Scale(quick_sliders, from_=0, to=255, orient=tk.HORIZONTAL, command=self.on_q_saturation_change)
        self.q_saturation.set(self.saturation_val)
        self.q_saturation.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.q_saturation.bind("<ButtonRelease-1>", lambda e: (self.saturation_slider.set(int(float(self.q_saturation.get()))), self.send_saturation()))

        # Hue speed (compact)
        ttk.Label(quick_sliders, text="Hue").pack(side=tk.LEFT, padx=4)
        self.q_hue = ttk.Scale(quick_sliders, from_=1, to=5, orient=tk.HORIZONTAL, command=self.on_q_hue_change)
        self.q_hue.set(self.hue_rotation_val)
        self.q_hue.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.q_hue.bind("<ButtonRelease-1>", lambda e: (self.hue_slider.set(int(float(self.q_hue.get()))), self.send_hue()))
        
        # ===== SYSTEM COMMANDS =====
        system_frame = ttk.LabelFrame(parent_frame, text="System", padding="10")
        system_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(system_frame, text="Status", command=lambda: self.send_command("L")).pack(side=tk.LEFT, padx=3)
        ttk.Button(system_frame, text="Show Custom", command=lambda: self.send_command(")")).pack(side=tk.LEFT, padx=3)
        ttk.Button(system_frame, text="LED Settings", command=lambda: self.send_command("}")).pack(side=tk.LEFT, padx=3)
        ttk.Button(system_frame, text="Clear LEDs", command=lambda: self.send_command("{")).pack(side=tk.LEFT, padx=3)
        ttk.Button(system_frame, text="Auto-Cycle", command=lambda: self.send_command("A")).pack(side=tk.LEFT, padx=3)
        ttk.Button(system_frame, text="Reset All", command=lambda: self.send_command("(")).pack(side=tk.LEFT, padx=3)
    
    def setup_advanced_tab(self, parent):
        parent_frame = ttk.Frame(parent, padding="10")
        parent_frame.pack(fill=tk.BOTH, expand=True)
        
        # ===== BRIGHTNESS SLIDER =====
        bright_frame = ttk.LabelFrame(parent_frame, text="Brightness Control", padding="10")
        bright_frame.pack(fill=tk.X, pady=5)
        
        self.bright_label = ttk.Label(bright_frame, text="255", width=5)
        self.bright_slider = ttk.Scale(bright_frame, from_=0, to=255, orient=tk.HORIZONTAL, command=self.on_brightness_change)
        self.bright_slider.set(255)
        self.bright_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.bright_label.pack(side=tk.LEFT, padx=5)
        # Send brightness when user releases the slider
        self.bright_slider.bind("<ButtonRelease-1>", lambda e: self.send_brightness())
        
        # ===== SPEED SLIDER =====
        speed_frame = ttk.LabelFrame(parent_frame, text="Speed Control (1-200ms)", padding="10")
        speed_frame.pack(fill=tk.X, pady=5)
        
        self.speed_label = ttk.Label(speed_frame, text="10ms", width=7)
        self.speed_slider = ttk.Scale(speed_frame, from_=1, to=200, orient=tk.HORIZONTAL, command=self.on_speed_change)
        self.speed_slider.set(10)
        self.speed_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.speed_label.pack(side=tk.LEFT, padx=5)
        self.speed_slider.bind("<ButtonRelease-1>", lambda e: self.send_speed())
        
        # ===== INTENSITY SLIDER =====
        intensity_frame = ttk.LabelFrame(parent_frame, text="Effect Intensity (0-255)", padding="10")
        intensity_frame.pack(fill=tk.X, pady=5)
        
        self.intensity_label = ttk.Label(intensity_frame, text="128", width=5)
        self.intensity_slider = ttk.Scale(intensity_frame, from_=0, to=255, orient=tk.HORIZONTAL, command=self.on_intensity_change)
        self.intensity_slider.set(128)
        self.intensity_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.intensity_label.pack(side=tk.LEFT, padx=5)
        self.intensity_slider.bind("<ButtonRelease-1>", lambda e: self.send_intensity())
        
        # ===== SATURATION SLIDER =====
        saturation_frame = ttk.LabelFrame(parent_frame, text="Color Saturation (0-255)", padding="10")
        saturation_frame.pack(fill=tk.X, pady=5)
        
        self.saturation_label = ttk.Label(saturation_frame, text="255", width=5)
        self.saturation_slider = ttk.Scale(saturation_frame, from_=0, to=255, orient=tk.HORIZONTAL, command=self.on_saturation_change)
        self.saturation_slider.set(255)
        self.saturation_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.saturation_label.pack(side=tk.LEFT, padx=5)
        self.saturation_slider.bind("<ButtonRelease-1>", lambda e: self.send_saturation())
        
        # ===== HUE ROTATION SPEED SLIDER =====
        hue_frame = ttk.LabelFrame(parent_frame, text="Hue Rotation Speed (1-5)", padding="10")
        hue_frame.pack(fill=tk.X, pady=5)
        
        self.hue_label = ttk.Label(hue_frame, text="1", width=3)
        self.hue_slider = ttk.Scale(hue_frame, from_=1, to=5, orient=tk.HORIZONTAL, command=self.on_hue_change)
        self.hue_slider.set(1)
        self.hue_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.hue_label.pack(side=tk.LEFT, padx=5)
        self.hue_slider.bind("<ButtonRelease-1>", lambda e: self.send_hue())
        
        # ===== CUSTOM RGB COLOR PICKER =====
        color_frame = ttk.LabelFrame(parent_frame, text="Custom RGB Color", padding="10")
        color_frame.pack(fill=tk.X, pady=5)
        
        self.color_canvas = tk.Canvas(color_frame, bg="red", width=100, height=40, relief=tk.SUNKEN, bd=2)
        self.color_canvas.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(color_frame, text="Pick Color", command=self.pick_custom_color).pack(side=tk.LEFT, padx=5)
        
        self.rgb_label = ttk.Label(color_frame, text="RGB: (255, 0, 0)", font=("Arial", 10))
        self.rgb_label.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(color_frame, text="Send Custom RGB", command=self.send_custom_rgb).pack(side=tk.LEFT, padx=5)
    
    def setup_preset_tab(self, parent):
        parent_frame = ttk.Frame(parent, padding="10")
        parent_frame.pack(fill=tk.BOTH, expand=True)
        
        # ===== PRESETS SECTION =====
        preset_frame = ttk.LabelFrame(parent_frame, text="Save/Load Settings Presets", padding="10")
        preset_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(preset_frame, text="Preset Name:").pack(side=tk.LEFT, padx=5)
        self.preset_name_var = tk.StringVar()
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
        self.macro_name_var = tk.StringVar()
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
    
    def setup_status_tab(self, parent):
        parent_frame = ttk.Frame(parent, padding="10")
        parent_frame.pack(fill=tk.BOTH, expand=True)
        
        # ===== STATUS DISPLAY =====
        status_frame = ttk.LabelFrame(parent_frame, text="Current Status", padding="10")
        status_frame.pack(fill=tk.X, pady=5)
        
        self.status_info_text = scrolledtext.ScrolledText(status_frame, height=6, width=80, state=tk.DISABLED)
        self.status_info_text.pack(fill=tk.BOTH, expand=True)
        
        # NOTE: Command history is shown in the persistent pane at the bottom of the window.
        ttk.Button(parent_frame, text="Clear History (bottom pane)", command=self.clear_history).pack(pady=5)
        
        # ===== FAVORITES / QUICK PRESETS =====
        favorites_frame = ttk.LabelFrame(parent_frame, text="Quick Favorites", padding="10")
        favorites_frame.pack(fill=tk.X, pady=5)
        
        favorite_combos = [
            ("Chill Rainbow", "R", 100, "1"),
            ("Fast Pulse Red", "P", 5, "1"),
            ("Calm Fire", "F", 50, "1"),
            ("Disco Strobe", "X", 5, "1"),
        ]
        
        for label, effect, speed, color in favorite_combos:
            ttk.Button(favorites_frame, text=label, command=lambda e=effect, s=speed, c=color: self.play_favorite(e, s, c)).pack(side=tk.LEFT, padx=3)
    
    def setup_graph_tab(self, parent):
        """Setup the Multi-Channel Oscilloscope tab"""
        parent_frame = ttk.Frame(parent, padding="10")
        parent_frame.pack(fill=tk.BOTH, expand=True)
        
        # ===== GRAPH CONTROLS =====
        control_frame = ttk.LabelFrame(parent_frame, text="Oscilloscope Controls", padding="10")
        control_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(control_frame, text="⏵ Start Monitoring", command=self.start_monitoring).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="⏹ Stop Monitoring", command=self.stop_monitoring).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Clear Data", command=self.clear_graph).pack(side=tk.LEFT, padx=5)
        
        # ===== Tipsy Sync Tuning =====
        ttk.Label(control_frame, text="Tipsy Sync:").pack(side=tk.LEFT, padx=8)
        self.tipsy_slider = ttk.Scale(control_frame, from_=32, to=255, orient=tk.HORIZONTAL, command=self.on_tipsy_sync_change)
        self.tipsy_slider.set(self.tipsy_sync_value)
        self.tipsy_slider.pack(side=tk.LEFT, fill=tk.X, expand=False, padx=4)
        self.tipsy_slider.bind("<ButtonRelease-1>", lambda e: self.send_tipsy_sync())

        ttk.Checkbutton(control_frame, text="Bind to Measured Speed", variable=self.bind_tipsy_var, command=self.toggle_bind_tipsy).pack(side=tk.LEFT, padx=10)
        
        # Auto-update toggle
        self.auto_update_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="📊 Live Updates", variable=self.auto_update_var, 
                       command=self.toggle_auto_update).pack(side=tk.LEFT, padx=20)
        
        self.monitoring_status = ttk.Label(control_frame, text="Status: Stopped", foreground="red")
        self.monitoring_status.pack(side=tk.LEFT, padx=20)
        
        # ===== CHANNEL SELECTION =====
        channel_frame = ttk.LabelFrame(parent_frame, text="Signal Channels (enable/disable channels to display)", padding="10")
        channel_frame.pack(fill=tk.X, pady=5)
        
        self.channel_vars = {}
        for key, channel in list(self.telemetry_channels.items())[:6]:  # Show first 6 main channels
            var = tk.BooleanVar(value=channel['show'])
            self.channel_vars[key] = var
            chk = ttk.Checkbutton(channel_frame, text=f"▮ {channel['name']}", variable=var,
                                 command=lambda k=key: self.toggle_channel(k))
            chk.pack(side=tk.LEFT, padx=10)
        
        # RGB sub-channels (hidden by default)
        rgb_frame = ttk.Frame(channel_frame)
        rgb_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(rgb_frame, text="RGB Channels:").pack(side=tk.LEFT, padx=5)
        
        for key in ['R', 'G', 'BL']:
            if key in self.telemetry_channels:
                var = tk.BooleanVar(value=self.telemetry_channels[key]['show'])
                self.channel_vars[key] = var
                chk = ttk.Checkbutton(rgb_frame, text=self.telemetry_channels[key]['name'], variable=var,
                                     command=lambda k=key: self.toggle_channel(k))
                chk.pack(side=tk.LEFT, padx=10)
        
        # ===== CANVAS FOR OSCILLOSCOPE =====
        graph_frame = ttk.LabelFrame(parent_frame, text="Multi-Channel Oscilloscope", padding="5")
        graph_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.graph_canvas = tk.Canvas(graph_frame, bg="#0a0a1a", height=350, relief=tk.SUNKEN, bd=2)
        self.graph_canvas.pack(fill=tk.BOTH, expand=True)
        self.graph_canvas.bind("<Configure>", lambda e: self.draw_graph())  # Redraw on resize
        
        # ===== STATS DISPLAY =====
        stats_frame = ttk.LabelFrame(parent_frame, text="Signal Statistics", padding="10")
        stats_frame.pack(fill=tk.X, pady=5)
        
        # Create a frame for stats
        stats_info = ttk.Frame(stats_frame)
        stats_info.pack(fill=tk.X, expand=True)
        
        ttk.Label(stats_info, text="Current Brightness:").pack(side=tk.LEFT, padx=5)
        self.current_brightness_label = ttk.Label(stats_info, text="0", font=("Arial", 10, "bold"))
        self.current_brightness_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(stats_info, text="| Min:").pack(side=tk.LEFT, padx=5)
        self.min_brightness_label = ttk.Label(stats_info, text="0")
        self.min_brightness_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(stats_info, text="| Max:").pack(side=tk.LEFT, padx=5)
        self.max_brightness_label = ttk.Label(stats_info, text="0")
        self.max_brightness_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(stats_info, text="| Avg:").pack(side=tk.LEFT, padx=5)
        self.avg_brightness_label = ttk.Label(stats_info, text="0")
        self.avg_brightness_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(stats_info, text="| Samples:").pack(side=tk.LEFT, padx=5)
        self.samples_label = ttk.Label(stats_info, text="0")
        self.samples_label.pack(side=tk.LEFT, padx=5)
        
        self.monitoring_enabled = False
        self.draw_graph()
        # Start auto-update timer
        self.schedule_graph_update()
    
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
        
        ttk.Label(config_subframe, text="LED Pin (0-13):").pack(side=tk.LEFT, padx=5)
        self.pin_var = tk.StringVar(value=str(self.led_pin))
        pin_spinbox = ttk.Spinbox(config_subframe, from_=0, to=13, textvariable=self.pin_var, width=5)
        pin_spinbox.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(config_subframe, text="| Number of LEDs:").pack(side=tk.LEFT, padx=5)
        self.led_count_var = tk.StringVar(value=str(self.num_leds))
        led_spinbox = ttk.Spinbox(config_subframe, from_=1, to=60, textvariable=self.led_count_var, width=5)
        led_spinbox.pack(side=tk.LEFT, padx=5)
        
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
        for channel_key, channel_info in self.telemetry_channels.items():
            if not channel_info['show']:
                continue
                
            history = channel_info['history']
            if len(history) > 1:
                has_data = True
                points = []
                
                for idx, value in enumerate(history):
                    x = left_margin + (idx / max(1, len(history) - 1)) * plot_width
                    # Normalize value (0-255 range)
                    normalized = min(max(value / 255.0, 0), 1)
                    y = height - bottom_margin - normalized * plot_height
                    points.append((x, y))
                
                # Draw lines connecting points
                if len(points) > 1:
                    for i in range(len(points) - 1):
                        canvas.create_line(points[i][0], points[i][1], points[i+1][0], points[i+1][1],
                                         fill=channel_info['color'], width=2)
                
                # Draw data points (small circles)
                for i, (x, y) in enumerate(points):
                    radius = 2
                    canvas.create_oval(x - radius, y - radius, x + radius, y + radius, 
                                     fill=channel_info['color'], outline=channel_info['color'])
                    # Highlight the latest point with a larger circle
                    if i == len(points) - 1:
                        canvas.create_oval(x - 4, y - 4, x + 4, y + 4, 
                                         outline=channel_info['color'], width=2)
        
        # Draw legend
        legend_y = top_margin + 10
        legend_x = width - right_margin - 150
        for channel_key, channel_info in self.telemetry_channels.items():
            if channel_info['show']:
                canvas.create_rectangle(legend_x, legend_y, legend_x + 12, legend_y + 12, 
                                       fill=channel_info['color'], outline=channel_info['color'])
                canvas.create_text(legend_x + 18, legend_y + 6, text=channel_info['name'],
                                 anchor=tk.W, font=("Courier", 8), fill=channel_info['color'])
                legend_y += 15
        
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
        val = int(float(val))
        self.brightness_val = val
        if hasattr(self, 'bright_label'):
            self.bright_label.config(text=str(val))
        # keep quick slider in sync without causing recursion
        if hasattr(self, 'q_bright'):
            try:
                if int(float(self.q_bright.get())) != val:
                    self.q_bright.set(val)
            except:
                pass
        # Update PWM graph on slider change
        self.update_pwm_graph(val)
    
    def on_speed_change(self, val):
        """Handle speed slider changes"""
        val = int(float(val))
        self.speed_val = val
        if hasattr(self, 'speed_label'):
            self.speed_label.config(text=f"{val}ms")
        if hasattr(self, 'q_speed'):
            try:
                if int(float(self.q_speed.get())) != val:
                    self.q_speed.set(val)
            except:
                pass
    
    def on_intensity_change(self, val):
        """Handle intensity slider changes"""
        # existing method continues unchanged below
        val = int(float(val))
        self.intensity_val = val
        if hasattr(self, 'intensity_label'):
            self.intensity_label.config(text=str(val))
        if hasattr(self, 'q_intensity'):
            try:
                if int(float(self.q_intensity.get())) != val:
                    self.q_intensity.set(val)
            except:
                pass
        # Update intensity in Arduino when released
        # Note: actual send happens on ButtonRelease bound earlier

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
        val = int(float(val))
        self.intensity_val = val
        if hasattr(self, 'intensity_label'):
            self.intensity_label.config(text=str(val))
        if hasattr(self, 'q_intensity'):
            try:
                if int(float(self.q_intensity.get())) != val:
                    self.q_intensity.set(val)
            except:
                pass
    
    def on_saturation_change(self, val):
        """Handle saturation slider changes"""
        val = int(float(val))
        self.saturation_val = val
        if hasattr(self, 'saturation_label'):
            self.saturation_label.config(text=str(val))
        if hasattr(self, 'q_saturation'):
            try:
                if int(float(self.q_saturation.get())) != val:
                    self.q_saturation.set(val)
            except:
                pass
    
    def on_hue_change(self, val):
        """Handle hue rotation speed slider changes"""
        val = int(float(val))
        self.hue_rotation_val = val
        if hasattr(self, 'hue_label'):
            self.hue_label.config(text=str(val))
        if hasattr(self, 'q_hue'):
            try:
                if int(float(self.q_hue.get())) != val:
                    self.q_hue.set(val)
            except:
                pass

    # Lightweight handlers for quick sliders (don't send serial until release)
    def on_q_brightness_change(self, val):
        try:
            v = int(float(val))
            self.brightness_val = v
            if hasattr(self, 'bright_label'):
                self.bright_label.config(text=str(v))
            # Update graph
            self.update_pwm_graph(v)
        except:
            pass

    def on_q_intensity_change(self, val):
        try:
            v = int(float(val))
            self.intensity_val = v
            if hasattr(self, 'intensity_label'):
                self.intensity_label.config(text=str(v))
        except:
            pass

    def on_q_saturation_change(self, val):
        try:
            v = int(float(val))
            self.saturation_val = v
            if hasattr(self, 'saturation_label'):
                self.saturation_label.config(text=str(v))
        except:
            pass

    def on_q_hue_change(self, val):
        try:
            v = int(float(val))
            self.hue_rotation_val = v
            if hasattr(self, 'hue_label'):
                self.hue_label.config(text=str(v))
        except:
            pass
    
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
            
            self.bright_slider.set(preset.get("brightness", 255))
            self.speed_slider.set(preset.get("speed", 10))
            self.intensity_slider.set(preset.get("intensity", 128))
            self.saturation_slider.set(preset.get("saturation", 255))
            self.hue_slider.set(preset.get("hue_rotation", 1))
            
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
