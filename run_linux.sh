#!/bin/bash

# CPU Fan ARGB Controller - Linux Run Script
# This script installs necessary dependencies and starts the GUI.

echo "=========================================="
echo "   CPU Fan ARGB Controller - Quick Start  "
echo "=========================================="
echo ""

# Check if python3 is installed
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 is not installed."
    echo "Please install it using: sudo apt install python3"
    exit 1
fi

# Check for tkinter (common issue on Linux)
if ! python3 -c "import tkinter" &>/dev/null; then
    echo "ERROR: tkinter is not installed for Python 3."
    echo "Please install it using your package manager."
    echo "Example (Ubuntu/Debian): sudo apt install python3-tk"
    exit 1
fi

# Check for pip
if ! command -v pip3 &>/dev/null && ! python3 -m pip --version &>/dev/null; then
    echo "ERROR: pip for Python 3 is not installed."
    echo "Please install it using: sudo apt install python3-pip"
    exit 1
fi

# Install python dependencies
echo "1. Checking/Installing Python dependencies..."
python3 -m pip install -r requirements.txt --user

# Add user to dialout group for serial access if needed
if ! groups $USER | grep &>/dev/null "\bdialout\b"; then
    echo ""
    echo "REMARK: Your user might not have permission to access serial ports (dialout group)."
    echo "If the app cannot find your Arduino, run:"
    echo "    sudo usermod -a -G dialout $USER"
    echo "Then log out and log back in for changes to take effect."
    echo ""
fi

echo "2. Starting the GUI..."
python3 FanControl_GUI.py

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: The application exited with an error."
fi
