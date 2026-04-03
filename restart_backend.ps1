# Quick Backend Restart Script
# Kills Python backend and restarts it

$ErrorActionPreference = "Continue"

Write-Host "🔄 Restarting Backend..." -ForegroundColor Cyan

# Kill all Python processes (be careful if you have other Python apps running!)
Write-Host "Stopping Python processes..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 2

# Start backend
$RepoRoot = Split-Path -Parent $PSCommandPath
$BackendScript = Join-Path $RepoRoot "8_BACKEND_APPLICATION_LAYER\app_server.py"

Write-Host "Starting backend..." -ForegroundColor Green
Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", "cd '$RepoRoot'; python '$BackendScript'"
)

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "✅ Backend restarted!" -ForegroundColor Green
Write-Host "Check the new PowerShell window for backend logs"
Write-Host "Dashboard: http://127.0.0.1:5173/"
Write-Host "Backend: http://127.0.0.1:8000/health"
