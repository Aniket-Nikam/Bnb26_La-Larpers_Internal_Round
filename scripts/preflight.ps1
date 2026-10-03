[CmdletBinding()]
param(
    [switch]$RequireLoadTools
)

$ErrorActionPreference = 'Stop'
$missing = [System.Collections.Generic.List[string]]::new()

foreach ($path in @(
    'backend/Dockerfile',
    'backend/app/main.py',
    'backend/app/allocation/worker.py',
    'backend/alembic.ini',
    'frontend/Dockerfile',
    'frontend/package-lock.json',
    'contracts/openapi.json'
)) {
    if (-not (Test-Path -LiteralPath $path)) { $missing.Add($path) }
}

foreach ($command in @('docker', 'git')) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) { $missing.Add("command:$command") }
}
if ($RequireLoadTools -and -not (Get-Command 'k6' -ErrorAction SilentlyContinue)) {
    $missing.Add('command:k6')
}

if ($missing.Count -gt 0) {
    Write-Error ("Preflight blocked. Missing dependency checkpoint items:`n - " + ($missing -join "`n - "))
}

docker compose --env-file .env config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Docker Compose configuration validation failed.' }
Write-Host 'Preflight passed.'
