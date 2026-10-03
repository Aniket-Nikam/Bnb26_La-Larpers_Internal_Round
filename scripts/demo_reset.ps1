[CmdletBinding()]
param(
    [switch]$IUnderstandThisDeletesDemoData
)

$ErrorActionPreference = 'Stop'
if (-not $IUnderstandThisDeletesDemoData) {
    throw 'Refusing reset. Pass -IUnderstandThisDeletesDemoData explicitly.'
}
if (-not (Test-Path -LiteralPath '.env')) { throw '.env is required.' }

$profileLine = Get-Content -LiteralPath '.env' | Where-Object { $_ -match '^APP_PROFILE=' } | Select-Object -First 1
$profile = ($profileLine -split '=', 2)[1].Trim()
if ($profile -notin @('demo', 'test')) {
    throw "Refusing reset for APP_PROFILE=$profile. Only demo/test are allowed."
}

docker compose -p fairdrop-demo --env-file .env -f compose.yaml -f infra/compose.demo.yaml --profile lab down --volumes --remove-orphans
if ($LASTEXITCODE -ne 0) { throw 'Demo reset failed.' }
Write-Host 'Removed only the fairdrop-demo Compose project containers, networks, and named volumes.'
