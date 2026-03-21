$ErrorActionPreference = "Stop"

param(
    [string]$Host = "127.0.0.1",
    [int]$Port = 5173
)

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not (Test-Path ".third_part_newsnow/package.json")) {
    throw "NewsNow submodule is missing. Run scripts/init-newsnow-submodule.ps1 first."
}

if (-not (Test-Path ".third_part_newsnow/node_modules")) {
    throw "NewsNow dependencies are missing. Run scripts/init-newsnow-submodule.ps1 first."
}

Push-Location ".third_part_newsnow"
try {
    Write-Host "[newsnow] starting upstream dev server at http://$Host`:$Port ..."
    cmd /c npm run dev -- --host $Host --port $Port
}
finally {
    Pop-Location
}
