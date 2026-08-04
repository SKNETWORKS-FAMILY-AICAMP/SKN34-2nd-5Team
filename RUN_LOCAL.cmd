@echo off
setlocal

cd /d "%~dp0"
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
