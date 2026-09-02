[CmdletBinding()]
param(
    [switch]$ApiOnly,
    [switch]$StartAuth,
    [switch]$StartReact,
    [string]$LanIp
)

# Same services as start_local.ps1, but bound to 0.0.0.0 so other devices on
# the LAN can reach them, with the React dev server pointed at this
# machine's LAN IP instead of localhost (see RUN_LOCAL.cmd's counterpart,
# RUN_WEB.cmd — kept as a separate script rather than a flag on
# start_local.ps1 so the plain localhost-only workflow is untouched).

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot 'venv\Scripts\python.exe'
$StatusScript = Join-Path $PSScriptRoot 'check_local_status.ps1'
$RuntimeRoot = Join-Path $ProjectRoot 'venv\.runtime'
$LogDir = Join-Path $RuntimeRoot 'logs'

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

function Repair-DuplicatePathEnvironment {
    $processEnvironment = [Environment]::GetEnvironmentVariables('Process')
    $pathKeys = @(
        $processEnvironment.Keys |
        Where-Object { $_.ToString().Equals('PATH', [System.StringComparison]::OrdinalIgnoreCase) }
    )
    if ($pathKeys.Count -le 1) { return }

    $pathValue = $processEnvironment[$pathKeys[0]]
    foreach ($pathKey in $pathKeys) {
        [Environment]::SetEnvironmentVariable($pathKey.ToString(), $null, 'Process')
    }
    [Environment]::SetEnvironmentVariable('Path', $pathValue, 'Process')
}

Repair-DuplicatePathEnvironment

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

function Stop-ListenerTree {
    param([int]$Port)

    $listenerPid = Get-ListenerPid -Port $Port
    if ($null -eq $listenerPid) { return }

    & taskkill.exe /PID $listenerPid /T /F 2>$null | Out-Null
    Start-Sleep -Milliseconds 750

    if ($null -ne (Get-ListenerPid -Port $Port)) {
        throw "Could not stop the existing process on port $Port. Close it manually and retry."
    }
}

function Get-LanIPAddress {
    param([string]$RequestedAddress)

    if ($RequestedAddress) {
        $parsed = $null
        if (-not [System.Net.IPAddress]::TryParse($RequestedAddress, [ref]$parsed)) {
            throw "Invalid LAN IPv4 address: $RequestedAddress"
        }
        return $RequestedAddress
    }

    $candidates = @(
        Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notlike '169.254.*' -and $_.PrefixOrigin -ne 'WellKnown' } |
        Select-Object -ExpandProperty IPAddress
    )

    if ($candidates.Count -eq 0) {
        $ipconfigText = (& ipconfig.exe | Out-String)
        $candidates = @(
            [regex]::Matches($ipconfigText, '(?im)IPv4[^:]*:\s*(\d{1,3}(?:\.\d{1,3}){3})') |
            ForEach-Object { $_.Groups[1].Value } |
            Where-Object { $_ -notlike '127.*' -and $_ -notlike '169.254.*' }
        )
    }

    $candidate = $candidates |
        Sort-Object { if ($_ -like '192.168.*') { 0 } elseif ($_ -like '10.*') { 1 } elseif ($_ -match '^172\.(1[6-9]|2\d|3[01])\.') { 2 } else { 3 } } |
        Select-Object -First 1

    if (-not $candidate) {
        throw 'Could not detect a LAN IPv4 address. Run start_local_web.ps1 with -LanIp <address>.'
    }
    return $candidate
}

function Start-UvicornService {
    param([string]$Application, [int]$Port, [string]$LogName)

    if (-not (Test-Path -LiteralPath $PythonExe)) {
        throw "Python virtual environment was not found: $PythonExe"
    }

    Start-Process -FilePath $PythonExe `
        -ArgumentList @('-m', 'uvicorn', $Application, '--reload', '--host', '0.0.0.0', '--port', $Port) `
        -WorkingDirectory $ProjectRoot -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $LogDir "$LogName.out.log") `
        -RedirectStandardError (Join-Path $LogDir "$LogName.err.log")
}

$lanIp = Get-LanIPAddress -RequestedAddress $LanIp
Write-Host "Detected LAN IP: $lanIp" -ForegroundColor Green

Write-Host 'Stopping any existing local-only services (8000/8100/5173)...' -ForegroundColor Yellow
Stop-ListenerTree -Port 8000
Stop-ListenerTree -Port 8100
Stop-ListenerTree -Port 5173

Write-Host 'Starting Analysis API on 0.0.0.0:8000...' -ForegroundColor Cyan
Start-UvicornService -Application 'api.main:app' -Port 8000 -LogName 'analysis-api'

$shouldStartAuth = -not $ApiOnly -or $StartAuth
$shouldStartReact = -not $ApiOnly -or $StartReact

if ($shouldStartAuth) {
    Write-Host 'Starting Auth API on 0.0.0.0:8100...' -ForegroundColor Cyan
    Start-UvicornService -Application 'auth_service.main:app' -Port 8100 -LogName 'auth-api'
}

if ($shouldStartReact) {
    Write-Host 'Starting React on 0.0.0.0:5173...' -ForegroundColor Cyan
    # Set in this process's environment so Start-Process's child (cmd.exe ->
    # npm -> vite) inherits it — avoids cmd.exe's fragile "set X=Y&&cmd" quoting.
    $env:VITE_API_BASE_URL = "http://${lanIp}:8000"
    $npmCommand = Resolve-NpmCommand
    Start-Process -FilePath $npmCommand `
        -ArgumentList @('run', 'dev', '--', '--host', '0.0.0.0') `
        -WorkingDirectory (Join-Path $ProjectRoot 'app') -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $LogDir 'react.out.log') `
        -RedirectStandardError (Join-Path $LogDir 'react.err.log')
}

& $StatusScript -Wait -TimeoutSeconds 30
if ($LASTEXITCODE -ne 0) {
    Write-Error "One or more LAN services failed to start. Check logs in: $LogDir"
    exit 1
}

Write-Host ''
Write-Host "Open from another device on the same network: http://${lanIp}:5173" -ForegroundColor Green
Write-Host 'First run may trigger a Windows Firewall prompt — allow it on Private networks.' -ForegroundColor DarkGray
