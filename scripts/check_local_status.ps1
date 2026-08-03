[CmdletBinding()]
param()

$ProjectRoot = Split-Path -Parent $PSScriptRoot

function Get-ListenerPid {
    param([int]$Port)

    $pattern = "^\s*TCP\s+\S+:$Port\s+\S+\s+LISTENING\s+(\d+)\s*$"
    $listener = (& netstat.exe -ano -p TCP | Select-String -Pattern $pattern | Select-Object -First 1)
    if ($null -eq $listener) { return $null }
    return [int]$listener.Matches[0].Groups[1].Value
}

function Test-HttpService {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec 2 -UseBasicParsing
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    }
    catch {
        return $false
    }
}

$services = @(
    [PSCustomObject]@{ Name = 'MySQL'; Port = 3306; Url = $null },
    [PSCustomObject]@{ Name = 'Analysis API'; Port = 8000; Url = 'http://127.0.0.1:8000/health' },
    [PSCustomObject]@{ Name = 'Auth API'; Port = 8100; Url = 'http://127.0.0.1:8100/auth/login' },
    [PSCustomObject]@{ Name = 'React'; Port = 5173; Url = 'http://127.0.0.1:5173/' }
)

$rows = foreach ($service in $services) {
    $listenerPid = Get-ListenerPid -Port $service.Port
    $isRunning = $null -ne $listenerPid
    $isHealthy = if ($isRunning -and $service.Url) { Test-HttpService -Url $service.Url } else { $null }

    [PSCustomObject]@{
        Service = $service.Name
        Port = $service.Port
        Status = if (-not $isRunning) { 'Stopped' } elseif ($isHealthy -eq $false) { 'Listening (health check failed)' } else { 'Running' }
        PID = if ($isRunning) { $listenerPid } else { '-' }
    }
}

Write-Host "Local service status: $ProjectRoot" -ForegroundColor Cyan
$rows | Format-Table -AutoSize
