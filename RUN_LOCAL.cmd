@echo off
setlocal

cd /d "%~dp0"

set "DEV_RUNTIME=%~dp0venv\.runtime"
if not exist "%DEV_RUNTIME%\tmp" mkdir "%DEV_RUNTIME%\tmp"
if not exist "%DEV_RUNTIME%\pip-cache" mkdir "%DEV_RUNTIME%\pip-cache"
if not exist "%DEV_RUNTIME%\npm-cache" mkdir "%DEV_RUNTIME%\npm-cache"
if not exist "%DEV_RUNTIME%\logs" mkdir "%DEV_RUNTIME%\logs"

set "TEMP=%DEV_RUNTIME%\tmp"
set "TMP=%DEV_RUNTIME%\tmp"
set "PIP_CACHE_DIR=%DEV_RUNTIME%\pip-cache"
set "NPM_CONFIG_CACHE=%DEV_RUNTIME%\npm-cache"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_local.ps1" -StartAuth -StartReact

if errorlevel 1 (
    echo.
    echo Failed to start local services. Check the error message above.
    pause
    exit /b 1
)

echo.
echo Local services are ready. React: http://localhost:5173
pause
