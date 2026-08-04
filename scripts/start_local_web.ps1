[CmdletBinding()]
param(
    [switch]$ApiOnly,
    [switch]$StartAuth,
    [switch]$StartReact
)

# Same services as start_local.ps1, but bound to 0.0.0.0 so other devices on
# the LAN can reach them, with the React dev server pointed at this
# machine's LAN IP instead of localhost (see RUN_LOCAL.cmd's counterpart,
# RUN_WEB.cmd — kept as a separate script rather than a flag on
# start_local.ps1 so the plain localhost-only workflow is untouched).

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

function Stop-ListenerWithParent {
    param([int]$Port)

    $listenerPid = Get-ListenerPid -Port $Port
    if ($null -eq $listenerPid) { return }

    # uvicorn --reload runs a supervisor process that respawns the worker
    # the moment it's killed, so the parent has to go too or the port keeps
    # reopening on 127.0.0.1 from the previous run.
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$listenerPid" -ErrorAction SilentlyContinue
    if ($proc -and $proc.ParentProcessId) {
        Stop-Process -Id $proc.ParentProcessId -Force -ErrorAction SilentlyContinue
    }
    Stop-Process -Id $listenerPid -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 500
}

function Get-LanIPAddress {
    $candidate = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notlike '169.254.*' -and $_.PrefixOrigin -ne 'WellKnown' } |
        Select-Object -First 1
    if ($null -eq $candidate) {
        throw 'Could not detect a LAN IPv4 address. Check your network adapter and set VITE_API_BASE_URL manually.'
    }
    return $candidate.IPAddress
}

function Start-UvicornService {
    param([string]$Application, [int]$Port)

    if (-not (Test-Path -LiteralPath $PythonExe)) {
        throw "Python virtual environment was not found: $PythonExe"
    }

    Start-Process -FilePath $PythonExe `
        -ArgumentList @('-m', 'uvicorn', $Application, '--reload', '--host', '0.0.0.0', '--port', $Port) `
        -WorkingDirectory $ProjectRoot -WindowStyle Hidden
}

$lanIp = Get-LanIPAddress
Write-Host "Detected LAN IP: $lanIp" -ForegroundColor Green

Write-Host 'Stopping any existing local-only services (8000/8100/5173)...' -ForegroundColor Yellow
Stop-ListenerWithParent -Port 8000
Stop-ListenerWithParent -Port 8100
Stop-ListenerWithParent -Port 5173

Write-Host 'Starting Analysis API on 0.0.0.0:8000...' -ForegroundColor Cyan
Start-UvicornService -Application 'api.main:app' -Port 8000

$shouldStartAuth = -not $ApiOnly -or $StartAuth
$shouldStartReact = -not $ApiOnly -or $StartReact

if ($shouldStartAuth) {
    Write-Host 'Starting Auth API on 0.0.0.0:8100...' -ForegroundColor Cyan
    Start-UvicornService -Application 'auth_service.main:app' -Port 8100
}

if ($shouldStartReact) {
    Write-Host 'Starting React on 0.0.0.0:5173...' -ForegroundColor Cyan
    # Set in this process's environment so Start-Process's child (cmd.exe ->
    # npm -> vite) inherits it — avoids cmd.exe's fragile "set X=Y&&cmd" quoting.
    $env:VITE_API_BASE_URL = "http://${lanIp}:8000"
    $npmCommand = Resolve-NpmCommand
    Start-Process -FilePath $npmCommand `
        -ArgumentList @('run', 'dev', '--', '--host', '0.0.0.0') `
        -WorkingDirectory (Join-Path $ProjectRoot 'app') -WindowStyle Hidden
}

Start-Sleep -Seconds 2
& $StatusScript

Write-Host ''
Write-Host "Open from another device on the same network: http://${lanIp}:5173" -ForegroundColor Green
Write-Host 'First run may trigger a Windows Firewall prompt — allow it on Private networks.' -ForegroundColor DarkGray
