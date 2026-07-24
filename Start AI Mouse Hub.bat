@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv 2>nul
  if errorlevel 1 python -m venv .venv
)

if not exist ".venv\Scripts\python.exe" (
  echo Python 3 kon niet worden gestart.
  pause
  exit /b 1
)

if not exist "data\logs" mkdir "data\logs"
".venv\Scripts\python.exe" -c "import tkinter" >> "data\logs\launcher.log" 2>&1
if errorlevel 1 (
  echo Tkinter ontbreekt. Controleer je Python-installatie.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m ai_mouse_hub.main >> "data\logs\launcher.log" 2>&1
if errorlevel 1 (
  echo De hub stopte met een fout. Bekijk data\logs\launcher.log
  pause
)
endlocal
