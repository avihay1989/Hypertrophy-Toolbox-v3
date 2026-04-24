param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
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
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

Write-Host "Writing Playwright log to $LogFile"

function Invoke-PlaywrightRun {
    param(
        [string[]] $PlaywrightRunArgs,
        [string] $Label
    )

    $SafeLabel = $Label -replace '[^A-Za-z0-9_-]', '-'
    $StdoutFile = Join-Path $LogsDir "playwright-$Timestamp.$SafeLabel.stdout.tmp"
    $StderrFile = Join-Path $LogsDir "playwright-$Timestamp.$SafeLabel.stderr.tmp"

    Write-Host "Running Playwright $Label"
    $ArgumentList = @("playwright", "test") + $PlaywrightRunArgs
    $ArgumentString = ($ArgumentList | ForEach-Object {
        if ($_ -match '\s') {
            '"' + ($_ -replace '"', '\"') + '"'
        }
        else {
            $_
        }
    }) -join ' '
    $Process = Start-Process `
        -FilePath $Npx `
        -ArgumentList $ArgumentString `
        -NoNewWindow `
        -Wait `
        -PassThru `
        -RedirectStandardOutput $StdoutFile `
        -RedirectStandardError $StderrFile
    $ExitCode = $Process.ExitCode

    if (Test-Path $StdoutFile) {
        Get-Content -Encoding UTF8 $StdoutFile |
            Tee-Object -FilePath $LogFile -Append |
            ForEach-Object { Write-Host $_ }
    }
    if (Test-Path $StderrFile) {
        Get-Content -Encoding UTF8 $StderrFile |
            Tee-Object -FilePath $LogFile -Append |
            ForEach-Object { Write-Host $_ }
    }

    Remove-Item -LiteralPath $StdoutFile, $StderrFile -Force -ErrorAction SilentlyContinue
    return $ExitCode
}

function New-VisualDatabase {
    $PrepareScript = Join-Path $RepoRoot "e2e\scripts\prepare_visual_db.py"
    if (-not (Test-Path $PrepareScript)) {
        throw "Visual DB preparation script not found: $PrepareScript"
    }

    $Output = & $Python $PrepareScript
    $VisualDb = ($Output | Select-Object -Last 1).Trim()
    if (-not (Test-Path $VisualDb)) {
        throw "Visual DB was not created: $VisualDb"
    }

    return (Resolve-Path $VisualDb).Path
}

$ExitCode = 0
$RunDefaultSuite = -not $PlaywrightArgs -or $PlaywrightArgs.Count -eq 0
$RunsVisualSpec = $PlaywrightArgs | Where-Object { $_ -match 'visual\.spec\.ts' }

if ($RunDefaultSuite) {
    $NonVisualSpecs = Get-ChildItem (Join-Path $RepoRoot "e2e") -Filter "*.spec.ts" |
        Where-Object { $_.Name -ne "visual.spec.ts" } |
        ForEach-Object { "e2e/$($_.Name)" }

    $ExitCode = Invoke-PlaywrightRun -PlaywrightRunArgs (@($NonVisualSpecs) + @("--project=chromium")) -Label "non-visual suite"
    if ($ExitCode -eq 0) {
        $PreviousDbFile = $env:DB_FILE
        $env:DB_FILE = New-VisualDatabase
        try {
            $ExitCode = Invoke-PlaywrightRun -PlaywrightRunArgs @("e2e/visual.spec.ts", "--project=chromium") -Label "visual suite"
        }
        finally {
            if ($null -ne $PreviousDbFile) {
                $env:DB_FILE = $PreviousDbFile
            }
            else {
                Remove-Item Env:DB_FILE -ErrorAction SilentlyContinue
            }
        }
    }
}
elseif ($RunsVisualSpec -and -not $env:DB_FILE) {
    $PreviousDbFile = $env:DB_FILE
    $env:DB_FILE = New-VisualDatabase
    try {
        $ExitCode = Invoke-PlaywrightRun -PlaywrightRunArgs $PlaywrightArgs -Label "requested suite"
    }
    finally {
        if ($null -ne $PreviousDbFile) {
            $env:DB_FILE = $PreviousDbFile
        }
        else {
            Remove-Item Env:DB_FILE -ErrorAction SilentlyContinue
        }
    }
}
else {
    $ExitCode = Invoke-PlaywrightRun -PlaywrightRunArgs $PlaywrightArgs -Label "requested suite"
}
exit $ExitCode
