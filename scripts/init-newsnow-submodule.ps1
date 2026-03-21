$ErrorActionPreference = "Stop"

param(
    [switch]$UpdateRemote,
    [switch]$SkipInstall
)

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git is required."
}

if (-not (Test-Path ".gitmodules")) {
    throw ".gitmodules not found."
}

Write-Host "[newsnow] syncing submodule metadata..."
git submodule sync -- .third_part_newsnow

if ($UpdateRemote) {
    Write-Host "[newsnow] updating submodule to latest upstream commit..."
    git submodule update --init --remote .third_part_newsnow
}
else {
    Write-Host "[newsnow] initializing pinned submodule commit..."
    git submodule update --init .third_part_newsnow
}

if ($SkipInstall) {
    Write-Host "[newsnow] skipping npm install."
    exit 0
}

Push-Location ".third_part_newsnow"
try {
    if (-not (Test-Path "package.json")) {
        throw "package.json not found in .third_part_newsnow."
    }
    Write-Host "[newsnow] installing npm dependencies..."
    cmd /c npm install --legacy-peer-deps
}
finally {
    Pop-Location
}

Write-Host "[newsnow] submodule is ready."
