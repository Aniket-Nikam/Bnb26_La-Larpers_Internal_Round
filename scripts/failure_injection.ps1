[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('worker', 'redis')]
    [string]$Service,

    [Parameter(Mandatory)]
    [ValidateSet('stop', 'start', 'restart')]
    [string]$Action,

    [switch]$IsolatedDemoConfirmed
)

$ErrorActionPreference = 'Stop'
if (-not $IsolatedDemoConfirmed) {
    throw 'Failure injection is restricted to the isolated demo project. Pass -IsolatedDemoConfirmed.'
}
if (-not (Test-Path -LiteralPath '.env')) { throw '.env is required.' }
$profileLine = Get-Content -LiteralPath '.env' | Where-Object { $_ -match '^APP_PROFILE=' } | Select-Object -First 1
$profile = ($profileLine -split '=', 2)[1].Trim()
if ($profile -notin @('demo', 'test')) { throw 'Failure injection is disabled outside demo/test.' }

$composeArgs = @('compose', '-p', 'fairdrop-demo', '--env-file', '.env', '-f', 'compose.yaml', '-f', 'infra/compose.demo.yaml')
& docker @composeArgs $Action $Service
if ($LASTEXITCODE -ne 0) { throw "Failed to $Action allowlisted service $Service." }
