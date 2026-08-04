@echo off
setlocal

cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_local_web.ps1" -StartAuth -StartReact

if errorlevel 1 (
    echo.
    echo Failed to start LAN services. Check the error message above.
    pause
    exit /b 1
)

echo.
echo Web (LAN) service launcher finished.
pause
