param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $PytestArgs
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

$ArtifactsRoot = if ($env:TEST_ARTIFACTS_DIR) { $env:TEST_ARTIFACTS_DIR } else { Join-Path $RepoRoot "artifacts" }
if (-not [System.IO.Path]::IsPathRooted($ArtifactsRoot)) {
    $ArtifactsRoot = Join-Path $RepoRoot $ArtifactsRoot
}

$PytestArtifacts = Join-Path $ArtifactsRoot "pytest"
$LogsDir = Join-Path $PytestArtifacts "logs"
$JunitDir = Join-Path $PytestArtifacts "junit"
New-Item -ItemType Directory -Force -Path $LogsDir, $JunitDir | Out-Null

$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$LogFile = Join-Path $LogsDir "pytest-$Timestamp.txt"
$JunitFile = Join-Path $JunitDir "pytest-$Timestamp.xml"

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

if (-not $PytestArgs -or $PytestArgs.Count -eq 0) {
    $PytestArgs = @("tests/", "-q")
}

$HasJunitArg = $PytestArgs | Where-Object { $_ -like "--junitxml*" }
if (-not $HasJunitArg) {
    $PytestArgs += "--junitxml=$JunitFile"
}

Write-Host "Writing pytest log to $LogFile"
$StdoutFile = Join-Path $LogsDir "pytest-$Timestamp.stdout.tmp"
$StderrFile = Join-Path $LogsDir "pytest-$Timestamp.stderr.tmp"
try {
    $ArgumentList = @("-m", "pytest") + $PytestArgs
    $Process = Start-Process `
        -FilePath $Python `
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
