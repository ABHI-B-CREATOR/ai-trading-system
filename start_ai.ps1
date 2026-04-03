param(
    [switch]$NoBrowser,
    [switch]$SkipTokenRefresh,
    [switch]$UseDev,
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSCommandPath
$BackendSettingsPath = Join-Path $RepoRoot "8_BACKEND_APPLICATION_LAYER\backend_settings.yaml"
$BrokerSessionPath = Join-Path $RepoRoot "6_EXECUTION_LAYER\broker_auth_session.json"
$TokenHelperPath = Join-Path $RepoRoot "8_BACKEND_APPLICATION_LAYER\zerodha_token_helper.py"
$BackendScriptPath = Join-Path $RepoRoot "8_BACKEND_APPLICATION_LAYER\app_server.py"
$FrontendDirectory = Join-Path $RepoRoot "9_FRONTEND_DASHBOARD_LAYER"

function Convert-ToSingleQuotedPsLiteral {
    param([string]$Value)

    return "'" + $Value.Replace("'", "''") + "'"
}

function Get-BackendDemoMode {
    if (-not (Test-Path -LiteralPath $BackendSettingsPath)) {
        return $false
    }

    foreach ($line in Get-Content -LiteralPath $BackendSettingsPath) {
        if ($line -match "^\s*demo_mode\s*:\s*(.+?)\s*$") {
            return $Matches[1].Trim().ToLower() -eq "true"
        }
    }

    # Default to live mode (false) if demo_mode is not found
    return $false
}

function Set-BackendDemoMode {
    param([bool]$DemoMode)

    if (-not (Test-Path -LiteralPath $BackendSettingsPath)) {
        Write-Warning "Backend settings file not found: $BackendSettingsPath"
        return
    }

    $lines = Get-Content -LiteralPath $BackendSettingsPath
    $updated = $false
    $newLines = @()

    foreach ($line in $lines) {
        if ($line -match "^\s*demo_mode\s*:\s*") {
            $newLines += "demo_mode: $($DemoMode.ToString().ToLower())"
            $updated = $true
        }
        else {
            $newLines += $line
        }
    }

    if ($updated) {
        $newLines | Set-Content -LiteralPath $BackendSettingsPath -Encoding UTF8
        Write-Host "Set demo_mode to $($DemoMode.ToString().ToLower()) in backend_settings.yaml"
    }
}

function Get-BrokerSession {
    if (-not (Test-Path -LiteralPath $BrokerSessionPath)) {
        return $null
    }

    try {
        return Get-Content -LiteralPath $BrokerSessionPath -Raw | ConvertFrom-Json
    }
    catch {
        return $null
    }
}

function Test-TokenFresh {
    param($Session)

    if (-not $Session) {
        return $false
    }

    $accessToken = [string]$Session.access_token
    if ([string]::IsNullOrWhiteSpace($accessToken)) {
        return $false
    }

    $generatedRaw = [string]$Session.token_generated_time
    if ([string]::IsNullOrWhiteSpace($generatedRaw)) {
        return $false
    }

    $validityHours = 24.0
    if ($Session.PSObject.Properties.Name -contains "token_validity_hours" -and $Session.token_validity_hours) {
        $validityHours = [double]$Session.token_validity_hours
    }

    try {
        $generatedAt = [datetimeoffset]::Parse($generatedRaw)
    }
    catch {
        return $false
    }

    try {
        $indiaTimeZone = [System.TimeZoneInfo]::FindSystemTimeZoneById("India Standard Time")
        $generatedIndiaDate = [System.TimeZoneInfo]::ConvertTime($generatedAt, $indiaTimeZone).Date
        $todayIndiaDate = [System.TimeZoneInfo]::ConvertTime([datetimeoffset]::UtcNow, $indiaTimeZone).Date
        if ($generatedIndiaDate -ne $todayIndiaDate) {
            return $false
        }
    }
    catch {
        # Fall back to the configured validity window if India timezone lookup is unavailable.
    }

    return [datetimeoffset]::UtcNow -lt $generatedAt.ToUniversalTime().AddHours($validityHours)
}

function Test-PortListening {
    param([int]$Port)

    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    return $null -ne $listener
}

function Start-PowerShellWindow {
    param(
        [string]$WorkingDirectory,
        [string]$CommandLine
    )

    $psCommand = "Set-Location $(Convert-ToSingleQuotedPsLiteral $WorkingDirectory); $CommandLine"
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        $psCommand
    ) | Out-Null
}

Set-Location -LiteralPath $RepoRoot

# Ensure demo_mode is set to false (live mode) by default
Set-BackendDemoMode -DemoMode $false

$demoMode = Get-BackendDemoMode
if (-not $demoMode -and -not $SkipTokenRefresh) {
    $brokerSession = Get-BrokerSession

    if (-not (Test-TokenFresh $brokerSession)) {
        Write-Host "Zerodha token is missing, stale, or expired. Starting login flow..."
        & python $TokenHelperPath --auto --callback "http://127.0.0.1:5000"

        if ($LASTEXITCODE -ne 0) {
            throw "Token refresh failed. Backend launch aborted."
        }

        $brokerSession = Get-BrokerSession
        if (-not (Test-TokenFresh $brokerSession)) {
            throw "Token metadata is still invalid after refresh. Backend launch aborted."
        }
    }
    else {
        Write-Host "Zerodha token looks fresh."
    }
}
elseif ($demoMode) {
    Write-Host "backend_settings.yaml has demo_mode: true. Skipping Zerodha token preflight."
}
else {
    Write-Host "Skipping Zerodha token preflight."
}

if (Test-PortListening -Port $BackendPort) {
    Write-Host "Backend already listening on port $BackendPort."
}
else {
    Write-Host "Starting backend (LIVE MODE) on port $BackendPort..."
    Start-PowerShellWindow -WorkingDirectory (Join-Path $RepoRoot "8_BACKEND_APPLICATION_LAYER") -CommandLine ("python " + (Convert-ToSingleQuotedPsLiteral $BackendScriptPath))
    Start-Sleep -Seconds 3
}

if (Test-PortListening -Port $FrontendPort) {
    Write-Host "Frontend already listening on port $FrontendPort."
}
else {
    Write-Host "Starting frontend development server..."
    Write-Host "Frontend directory: $FrontendDirectory"
    
    # Verify directory exists
    if (-not (Test-Path -LiteralPath $FrontendDirectory)) {
        Write-Host "ERROR: Frontend directory does not exist!" -ForegroundColor Red
        exit 1
    }
    
    # Verify package.json exists
    $packageJson = Join-Path $FrontendDirectory "package.json"
    if (-not (Test-Path -LiteralPath $packageJson)) {
        Write-Host "ERROR: package.json not found!" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Launching frontend PowerShell window..."
    
    # Start PowerShell window for frontend
    $frontendCmd = "cd '$FrontendDirectory'; Write-Host 'Starting npm run dev...'; npm run dev"
    Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $frontendCmd
    
    Write-Host "Waiting for frontend to start..."
    Start-Sleep -Seconds 6
}

$frontendUrl = "http://127.0.0.1:$FrontendPort/"
$backendHealthUrl = "http://127.0.0.1:$BackendPort/health"

Write-Host ""
Write-Host "========================================="
Write-Host "  AI OPTIONS TRADING SYSTEM - LIVE MODE"
Write-Host "========================================="
Write-Host "Frontend: $frontendUrl"
Write-Host "Backend:  $backendHealthUrl"
Write-Host ""

if (-not $NoBrowser) {
    Start-Process $frontendUrl | Out-Null
}
