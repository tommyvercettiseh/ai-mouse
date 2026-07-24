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
  pause
  exit /b 1
)

if not exist "data\logs" mkdir "data\logs"
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet pynput >> "data\logs\launcher.log" 2>&1
".venv\Scripts\python.exe" -c "import tkinter; import ai_mouse_hub.click_test" >> "data\logs\launcher.log" 2>&1
if errorlevel 1 (
  echo De kliktest kon niet worden geladen. Bekijk data\logs\launcher.log
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m ai_mouse_hub.click_test >> "data\logs\launcher.log" 2>&1
if errorlevel 1 (
  echo De kliktest stopte met een fout. Bekijk data\logs\launcher.log
  pause
)
endlocal
