@echo off
echo FanControl GUI - Quick Start
echo ----------------------------
echo 1) Upload `FanControl/FanControl.ino` to your Arduino (select correct board and COM).
echo 2) Install Python requirements (one-time):
echo    python -m pip install -r "%~dp0requirements.txt"
echo 3) Connect Arduino and run this script to start the GUI.
echo.
REM Try to start the GUI
python "%~dp0FanControl_GUI.py"
if %ERRORLEVEL% neq 0 (
  echo.
  echo ERROR: Could not start GUI. Ensure Python 3 is on PATH and pyserial is installed.
  pause
)
