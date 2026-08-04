[CmdletBinding()]
param(
    [switch]$RestartApi,
    [switch]$ApiOnly,
    [switch]$StartAuth,
    [switch]$StartReact
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot 'venv\Scripts\python.exe'
$StatusScript = Join-Path $PSScriptRoot 'check_local_status.ps1'

function Resolve-NpmCommand {
    $pathCommand = Get-Command 'npm.cmd' -ErrorAction SilentlyContinue
    if ($null -ne $pathCommand) {
        $env:PATH = "$(Split-Path -Parent $pathCommand.Source);$env:PATH"
        return $pathCommand.Source
    }

    $standardCommand = Join-Path $env:ProgramFiles 'nodejs\npm.cmd'
    if (Test-Path -LiteralPath $standardCommand -PathType Leaf) {
        $env:PATH = "$(Split-Path -Parent $standardCommand);$env:PATH"
        return $standardCommand
    }

    throw 'npm.cmd was not found. Install Node.js 20.19+ or 22.12+, then reopen the terminal.'
}

function Get-ListenerPid {
    param([int]$Port)

    $pattern = "^\s*TCP\s+\S+:$Port\s+\S+\s+LISTENING\s+(\d+)\s*$"
    $listener = (& netstat.exe -ano -p TCP | Select-String -Pattern $pattern | Select-Object -First 1)
    if ($null -eq $listener) { return $null }
    return [int]$listener.Matches[0].Groups[1].Value
}

function Start-UvicornService {
    param([string]$Application, [int]$Port)

    if (-not (Test-Path -LiteralPath $PythonExe)) {
        throw "Python virtual environment was not found: $PythonExe"
    }

    Start-Process -FilePath $PythonExe `
        -ArgumentList @('-m', 'uvicorn', $Application, '--reload', '--port', $Port) `
        -WorkingDirectory $ProjectRoot -WindowStyle Hidden
}

if ($RestartApi) {
    $apiPid = Get-ListenerPid -Port 8000
    if ($null -ne $apiPid) {
        Write-Host "Stopping existing Analysis API (PID $apiPid)..." -ForegroundColor Yellow
        Stop-Process -Id $apiPid -Force
        Start-Sleep -Milliseconds 500
    }
}

if ($null -eq (Get-ListenerPid -Port 8000)) {
    Write-Host 'Starting Analysis API on 8000...' -ForegroundColor Cyan
    Start-UvicornService -Application 'api.main:app' -Port 8000
}
else {
    Write-Host 'Analysis API is already running on 8000.' -ForegroundColor DarkGray
}

$shouldStartAuth = -not $ApiOnly -or $StartAuth
$shouldStartReact = -not $ApiOnly -or $StartReact

if ($shouldStartAuth -and $null -eq (Get-ListenerPid -Port 8100)) {
    Write-Host 'Starting Auth API on 8100...' -ForegroundColor Cyan
    Start-UvicornService -Application 'auth_service.main:app' -Port 8100
}

if ($shouldStartReact -and $null -eq (Get-ListenerPid -Port 5173)) {
    Write-Host 'Starting React on 5173...' -ForegroundColor Cyan
    $npmCommand = Resolve-NpmCommand
    Start-Process -FilePath $npmCommand `
        -ArgumentList @('run', 'dev', '--', '--host', '127.0.0.1') `
        -WorkingDirectory (Join-Path $ProjectRoot 'app') -WindowStyle Hidden
}

Start-Sleep -Seconds 2
& $StatusScript
