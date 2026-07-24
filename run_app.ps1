$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$projectPython = Join-Path $PSScriptRoot "venv\Scripts\python.exe"

if (Test-Path $projectPython) {
    & $projectPython -m streamlit run "app\streamlit_app.py"
} else {
    Write-Host "[INFO] 프로젝트 venv를 찾지 못해 현재 Python을 사용합니다."
    python -m streamlit run "app\streamlit_app.py"
}

