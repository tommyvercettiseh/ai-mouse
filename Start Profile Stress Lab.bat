@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Start eerst "Start AI Mouse Hub.bat" zodat de omgeving wordt aangemaakt.
  pause
  exit /b 1
)

if not exist "data\logs" mkdir "data\logs"
".venv\Scripts\python.exe" -m ai_mouse_hub.stress_cli --runs 100 --seed 42
if errorlevel 1 (
  echo.
  echo Stress Lab kon niet draaien. Bouw eerst een masterprofiel in de hub.
)
pause
endlocal
