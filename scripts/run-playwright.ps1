param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $PlaywrightArgs
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

$ArtifactsRoot = if ($env:TEST_ARTIFACTS_DIR) { $env:TEST_ARTIFACTS_DIR } else { Join-Path $RepoRoot "artifacts" }
if (-not [System.IO.Path]::IsPathRooted($ArtifactsRoot)) {
    $ArtifactsRoot = Join-Path $RepoRoot $ArtifactsRoot
}

$LogsDir = Join-Path $ArtifactsRoot "playwright\logs"
New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null

$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$LogFile = Join-Path $LogsDir "playwright-$Timestamp.txt"

$Npx = if ($env:OS -eq "Windows_NT") { "npx.cmd" } else { "npx" }

Write-Host "Writing Playwright log to $LogFile"
$StdoutFile = Join-Path $LogsDir "playwright-$Timestamp.stdout.tmp"
$StderrFile = Join-Path $LogsDir "playwright-$Timestamp.stderr.tmp"
try {
    $ArgumentList = @("playwright", "test") + $PlaywrightArgs
    $Process = Start-Process `
        -FilePath $Npx `
        -ArgumentList $ArgumentList `
        -NoNewWindow `
        -Wait `
        -PassThru `
        -RedirectStandardOutput $StdoutFile `
        -RedirectStandardError $StderrFile
    $ExitCode = $Process.ExitCode

    if (Test-Path $StdoutFile) {
        Get-Content -Encoding UTF8 $StdoutFile | Tee-Object -FilePath $LogFile
    }
    if (Test-Path $StderrFile) {
        Get-Content -Encoding UTF8 $StderrFile | Tee-Object -FilePath $LogFile -Append
    }
}
finally {
    Remove-Item -LiteralPath $StdoutFile, $StderrFile -Force -ErrorAction SilentlyContinue
}
exit $ExitCode
