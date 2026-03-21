$ErrorActionPreference = "Stop"

param(
    [int]$Port = 5173
)

$connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1

if (-not $connection) {
    Write-Host "[newsnow] no listening process found on port $Port."
    exit 0
}

$processId = $connection.OwningProcess
$process = Get-Process -Id $processId -ErrorAction SilentlyContinue

if (-not $process) {
    Write-Host "[newsnow] process $processId is no longer running."
    exit 0
}

Write-Host "[newsnow] stopping process $($process.ProcessName) ($processId) on port $Port ..."
Stop-Process -Id $processId -Force
Write-Host "[newsnow] upstream dev server stopped."
