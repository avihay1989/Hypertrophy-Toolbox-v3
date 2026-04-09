Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Python venv not found at $python"
}

$dbPath = Join-Path $env:TEMP ("summary_regression_" + [guid]::NewGuid().ToString("N") + ".db")
$env:DB_FILE = $dbPath

Write-Host "[1/4] Seeding temporary DB: $dbPath"
Push-Location $repoRoot
try {
    & $python (Join-Path $repoRoot "e2e\scripts\seed_summary_regression_db.py")
    if ($LASTEXITCODE -ne 0) {
        throw "Seeding failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}

$serverArgs = @("-m", "flask", "run", "--host", "127.0.0.1", "--port", "5001", "--no-reload")

Write-Host "[2/4] Starting isolated Flask server on http://127.0.0.1:5001"
$oldFlaskApp = $env:FLASK_APP
$oldFlaskDebug = $env:FLASK_DEBUG
$env:FLASK_APP = "app:app"
$env:FLASK_DEBUG = "0"
$serverProc = Start-Process -FilePath $python -ArgumentList $serverArgs -PassThru -WorkingDirectory $repoRoot -NoNewWindow

try {
    $ready = $false
    for ($i = 0; $i -lt 60; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri "http://127.0.0.1:5001/weekly_summary" -UseBasicParsing -TimeoutSec 2
            if ($resp.StatusCode -eq 200) {
                $ready = $true
                break
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) {
        throw "Timed out waiting for isolated Flask server startup."
    }

    Write-Host "[3/4] Running Puppeteer regression checks"
    $env:TEST_BASE_URL = "http://127.0.0.1:5001"
    & $python (Join-Path $repoRoot "e2e\puppeteer_mcp_summary_regression.py")
    $testExit = $LASTEXITCODE
    if ($testExit -ne 0) {
        throw "Puppeteer regression checks failed with exit code $testExit"
    }
}
finally {
    Write-Host "[4/4] Stopping isolated server and cleaning temporary DB"
    $env:FLASK_APP = $oldFlaskApp
    $env:FLASK_DEBUG = $oldFlaskDebug
    if ($null -ne $serverProc -and -not $serverProc.HasExited) {
        Stop-Process -Id $serverProc.Id -Force
    }
    if (Test-Path $dbPath) {
        Remove-Item $dbPath -Force
    }
}

Write-Host "Puppeteer regression checks completed."
