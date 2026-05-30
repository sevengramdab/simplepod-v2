@echo off
setlocal

:: Shadow PC Watcher Launcher
:: ==========================
:: Double-click this to start the watcher.
:: It will keep running in the background until you close the window.

cd /d "%~dp0.."

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else if exist "..\..\.venv\Scripts\python.exe" (
    set "PYTHON=..\..\.venv\Scripts\python.exe"
) else (
    echo [ERROR] Python venv not found. Please run from the project root.
    pause
    exit /b 1
)

echo ===========================================
echo   Shadow PC Watcher
echo ===========================================
echo.
echo Target : 100.64.0.2:8002
echo Logs   : logs/shadow_watcher.log
echo Captures: shadow_captures/
echo.
echo Press Ctrl+C to stop.
echo.

"%PYTHON%" scripts/shadow_watcher.py
