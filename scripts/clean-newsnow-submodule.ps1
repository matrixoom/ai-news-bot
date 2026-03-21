$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not (Test-Path ".third_part_newsnow/.git")) {
    throw "NewsNow submodule is missing."
}

Push-Location ".third_part_newsnow"
try {
    Write-Host "[newsnow] restoring tracked generated files..."
    git restore --worktree --staged --source=HEAD -- server/glob.d.ts shared/pinyin.json shared/sources.json src/routeTree.gen.ts
}
finally {
    Pop-Location
}
