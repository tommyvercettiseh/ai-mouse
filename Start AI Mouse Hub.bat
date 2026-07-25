@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Virtuele omgeving wordt gemaakt...
  py -3 -m venv .venv 2>nul
  if errorlevel 1 python -m venv .venv
)

if not exist ".venv\Scripts\python.exe" (
  echo Python 3 kon niet worden gestart.
  echo Installeer Python 3 en vink "Add Python to PATH" aan.
  pause
  exit /b 1
)

if not exist "data\logs" mkdir "data\logs"
echo [%date% %time%] AI Mouse launcher gestart>> "data\logs\launcher.log"

".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet --upgrade pip >> "data\logs\launcher.log" 2>&1
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet pynput >> "data\logs\launcher.log" 2>&1
if errorlevel 1 (
  echo De globale muisdependency kon niet worden geinstalleerd.
  echo Bekijk data\logs\launcher.log
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -c "import tkinter; import pynput; from ai_mouse_hub.screen_layout import enumerate_monitors" >> "data\logs\launcher.log" 2>&1
if errorlevel 1 (
  echo Een vereiste ontbreekt. Bekijk data\logs\launcher.log
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m ai_mouse_hub.modern_main >> "data\logs\launcher.log" 2>&1
if errorlevel 1 (
  echo De hub stopte met een fout. Bekijk data\logs\launcher.log
  pause
)
endlocal
