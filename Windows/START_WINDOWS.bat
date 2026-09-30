@echo off
setlocal
cd /d "%~dp0..\Files"
if errorlevel 1 exit /b 1

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\Files\bootstrap_windows.ps1"

if errorlevel 1 (
    echo.
    echo Startup failed.
    pause
    exit /b 1
)
