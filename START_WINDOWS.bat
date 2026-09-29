@echo off
setlocal
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0bootstrap_windows.ps1"

if errorlevel 1 (
    echo.
    echo Startup failed.
    pause
    exit /b 1
)
