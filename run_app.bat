@echo off
setlocal
cd /d "%~dp0"

if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" -m streamlit run app\streamlit_app.py
) else (
    echo [INFO] 프로젝트 venv를 찾지 못해 현재 Python을 사용합니다.
    python -m streamlit run app\streamlit_app.py
)

if errorlevel 1 (
    echo.
    echo [ERROR] 앱 실행에 실패했습니다.
    echo 먼저 requirements-streamlit.txt를 설치했는지 확인하세요.
    pause
)

endlocal

