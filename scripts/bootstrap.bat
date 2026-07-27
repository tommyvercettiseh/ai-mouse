@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

if not exist "data\logs" mkdir "data\logs"
set "LOG=data\logs\launcher.log"
set "MODE=%~1"
if "%MODE%"=="" set "MODE=main"

echo.>>"%LOG%"
echo [%date% %time%] Launcher gestart (%MODE%).>>"%LOG%"

set "BASEPY="
where py >nul 2>&1
if not errorlevel 1 set "BASEPY=py -3"
if not defined BASEPY (
    where python >nul 2>&1
    if not errorlevel 1 set "BASEPY=python"
)

if not defined BASEPY (
    echo Python 3.11 of nieuwer is niet gevonden.>>"%LOG%"
    echo.
    echo [FOUT] Python 3.11 of nieuwer is niet gevonden.
    echo Installeer Python en vink "Add Python to PATH" aan.
    pause
    exit /b 1
)

%BASEPY% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 (
    echo Python is ouder dan 3.11.>>"%LOG%"
    echo [FOUT] Python 3.11 of nieuwer is vereist.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Virtuele omgeving wordt aangemaakt...
    %BASEPY% -m venv .venv >>"%LOG%" 2>&1
    if errorlevel 1 goto :failed
)

set "VENV_PY=.venv\Scripts\python.exe"

echo Dependencies controleren...
"%VENV_PY%" -m pip install --disable-pip-version-check -r requirements.txt >>"%LOG%" 2>&1
if errorlevel 1 goto :failed

if /I "%MODE%"=="aim" (
    "%VENV_PY%" -m ai_mouse_lab.app --aim-lab >>"%LOG%" 2>&1
) else (
    "%VENV_PY%" -m ai_mouse_lab.app >>"%LOG%" 2>&1
)

if errorlevel 1 goto :failed
exit /b 0

:failed
echo [%date% %time%] Launcherfout.>>"%LOG%"
echo.
echo [FOUT] AI Mouse Lab kon niet worden gestart.
echo Het logbestand wordt geopend: %LOG%
start "" notepad "%CD%\%LOG%"
pause
exit /b 1
