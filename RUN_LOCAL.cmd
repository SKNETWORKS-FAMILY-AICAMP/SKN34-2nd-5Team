@echo off
setlocal

cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_local.ps1"

echo.
echo Local service launcher finished.
pause
