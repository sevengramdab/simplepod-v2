@echo off
setlocal

set "PROJECT_ROOT=%USERPROFILE%\simplepod-shadow"
set "PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe"
set "SIMPOD_NODE_ID=shadow_pc"
set "SIMPOD_PORT=8002"
set "PYTHONPATH=%PROJECT_ROOT%"

cd /d "%PROJECT_ROOT%"

echo ===========================================
echo   SimplePod Shadow PC (RTX 3080)
echo ===========================================
echo.
echo Setting NODE_ID=%SIMPOD_NODE_ID%
echo Setting PORT=%SIMPOD_PORT%
echo.

"%PYTHON%" shadow_node.py
