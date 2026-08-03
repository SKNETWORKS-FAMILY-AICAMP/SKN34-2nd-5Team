@echo off
setlocal

cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_local_web.ps1"

echo.
echo Web (LAN) service launcher finished.
pause
