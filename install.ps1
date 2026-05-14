#!/usr/bin/env pwsh
$Repo = "chasew28/homelab-monitor"
$VenvDir = "$HOME\.hlm\venv"

Write-Host "=== Homelab Monitor Installer ===" -ForegroundColor Cyan

$python = if (Get-Command "py" -ErrorAction SilentlyContinue) { "py" } `
    elseif (Get-Command "python" -ErrorAction SilentlyContinue) { "python" } `
    else { $null }

if (-not $python) {
    Write-Host "Error: Python is required but not found." -ForegroundColor Yellow
    Write-Host "Download from https://python.org" -ForegroundColor Yellow
    exit 1
}

Write-Host "  -> Creating virtual environment at $VenvDir"
& $python -m venv "$VenvDir"

Write-Host "  -> Installing from github.com/$Repo"
& "$VenvDir\Scripts\pip" install "git+https://github.com/$Repo.git" --quiet 2>&1 | Select-Object -Last 1

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$VenvDir\Scripts*") {
    Write-Host "  -> Adding $VenvDir\Scripts to PATH"
    [Environment]::SetEnvironmentVariable("Path", "$UserPath;$VenvDir\Scripts", "User")
}

Write-Host ""
Write-Host "  - Ready! Open a new terminal and run:" -ForegroundColor Green
Write-Host "    hlm setup" -ForegroundColor Cyan
Write-Host "    hlm run" -ForegroundColor Cyan
Write-Host ""
Write-Host "  On remote nodes, run:" -ForegroundColor Yellow
Write-Host "    hlm agent" -ForegroundColor Cyan
