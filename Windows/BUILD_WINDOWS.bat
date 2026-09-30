@echo off
setlocal
cd /d "%~dp0..\Files"
if errorlevel 1 exit /b 1

set "PYEXE="

py -3.12 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
if not errorlevel 1 set "PYEXE=py -3.12"

if not defined PYEXE (
    py -3.11 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
    if not errorlevel 1 set "PYEXE=py -3.11"
)

if not defined PYEXE (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
    if not errorlevel 1 set "PYEXE=python"
)

if not defined PYEXE (
    echo Python 3.11+ is required to build the app.
    echo Run START_WINDOWS.bat first - it can install Python 3.12 automatically.
    pause
    exit /b 1
)

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
    if errorlevel 1 rmdir /s /q ".venv"
)

if not exist ".venv\Scripts\python.exe" (
    %PYEXE% -m venv .venv
    if errorlevel 1 goto :error
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt
python build_app.py

echo.
echo Build is in the Files\dist folder.
pause
exit /b 0

:error
echo.
echo Build failed.
pause
exit /b 1
