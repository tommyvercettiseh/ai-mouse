@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0.."
set "FOUND=0"
for %%F in ("data\runtime\ai-mouse-lab.pid" "data\runtime\aim-lab.pid") do (
    if exist %%F (
        set /p PID=<%%F
        if defined PID (
            taskkill /PID !PID! /T /F >nul 2>&1
            set "FOUND=1"
        )
        del /q %%F >nul 2>&1
    )
)
if "%FOUND%"=="0" echo AI Mouse Lab draait niet.
endlocal
