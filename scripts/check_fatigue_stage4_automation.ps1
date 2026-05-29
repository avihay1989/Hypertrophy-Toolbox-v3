<#
.SYNOPSIS
    Health check for the Fatigue Meter Stage 4 calibration-observer automation.

.DESCRIPTION
    Read-only. Reports — and classifies — the full state of the Stage 4 observer
    automation so the owner can tell at a glance whether it is broken, was
    skipped by Windows, ran fine but has no data to process, or has logged data
    waiting for felt-label annotation. It checks:

      * scripts/fatigue_stage4_observer.py exists
      * scripts/run_fatigue_stage4_observer.bat exists
      * the scheduled task HypertrophyToolbox\FatigueStage4Observer exists
      * task enabled/disabled state, next run, last run, last result code
      * a plain-English explanation of the last result code (esp. 0 and 0x800710E0)
      * logs/fatigue_stage4_latest.txt exists + its last-modified time
      * docs/fatigue_meter/stage4_calibration_log.csv exists + pending/annotated rows
      * the live workout_log row count (via scripts/fatigue_stage4_status.py)

    It then prints one VERDICT distinguishing:
      [BROKEN]  automation broken (missing files/task, or a hard task failure)
      [SKIPPED] installed but skipped/refused by Windows (e.g. 0x800710E0)
      [IDLE]    ran successfully but has no workout_log data to process yet
      [READY]   logged data exists and pending calibration rows are available

    Strictly read-only: it never edits thresholds, scenarios, boundary tests,
    the scheduled task, the calibration CSV, or the database. To create/repair
    the task, run install_fatigue_stage4_observer_task.ps1.

.PARAMETER TaskName
    Full task path to inspect. Default: HypertrophyToolbox\FatigueStage4Observer.

.EXAMPLE
    .\scripts\check_fatigue_stage4_automation.ps1
#>
param(
    [string] $TaskName = "HypertrophyToolbox\FatigueStage4Observer"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$RepoRoot   = Resolve-Path (Join-Path $PSScriptRoot "..")
$ObserverPy = Join-Path $RepoRoot "scripts\fatigue_stage4_observer.py"
$ObserverBat= Join-Path $RepoRoot "scripts\run_fatigue_stage4_observer.bat"
$StatusPy   = Join-Path $RepoRoot "scripts\fatigue_stage4_status.py"
$LatestLog  = Join-Path $RepoRoot "logs\fatigue_stage4_latest.txt"
$CalibCsv   = Join-Path $RepoRoot "docs\fatigue_meter\stage4_calibration_log.csv"

function Write-Check([string] $label, [bool] $ok, [string] $detail) {
    $mark = if ($ok) { "[ OK ]" } else { "[FAIL]" }
    $color = if ($ok) { "Green" } else { "Red" }
    Write-Host ("  {0} {1}" -f $mark, $label) -ForegroundColor $color -NoNewline
    if ($detail) { Write-Host (" - {0}" -f $detail) } else { Write-Host "" }
}

# Neutral row for facts whose absence is expected (not a failure on its own).
function Write-Info([string] $label, [string] $detail) {
    Write-Host ("  [INFO] {0}" -f $label) -ForegroundColor DarkGray -NoNewline
    if ($detail) { Write-Host (" - {0}" -f $detail) } else { Write-Host "" }
}

# Normalize a Windows task result code (signed Int32 or unsigned) to 0xXXXXXXXX.
function Format-ResultCode([object] $code) {
    if ($null -eq $code) { return "(none)" }
    $u = [int64]$code -band 0xFFFFFFFFL
    return ("0x{0:X8}" -f $u)
}

# Plain-English meaning for the common scheduled-task result/state codes.
function Explain-ResultCode([object] $code) {
    if ($null -eq $code) { return "No last-result recorded yet (task has never run)." }
    $u = [int64]$code -band 0xFFFFFFFFL
    switch ($u) {
        0x0        { return "Success - the last run completed without error." }
        0x1        { return "Incorrect function / generic failure - the task action returned exit code 1." }
        0x2        { return "File not found - the program or .bat the task points at could not be located." }
        0x41300    { return "Task is ready (scheduled, has not run since last reset)." }
        0x41301    { return "Task is currently running." }
        0x41302    { return "Task is disabled." }
        0x41303    { return "Task has not yet run." }
        0x41306    { return "Task was terminated by the user (last run aborted)." }
        0x8004131F { return "An instance of the task is already running." }
        0x800710E0 { return "The operator or administrator refused the request - Windows SKIPPED the scheduled run. Typical causes: the machine was asleep/off/locked at 20:00, it was on battery while 'Stop on battery' is set, or the interactive-only task had no available user session. A manual 'schtasks /Run' still succeeds." }
        0x80070420 { return "The service has not been started." }
        default    { return "Unrecognized result code. Look it up via 'certutil -error <code>' or the Win32 error list." }
    }
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " Fatigue Stage 4 automation health check" -ForegroundColor Cyan
Write-Host " repo: $RepoRoot" -ForegroundColor DarkGray
Write-Host "================================================================" -ForegroundColor Cyan

# --- Repo-native files -------------------------------------------------------
Write-Host "`nObserver tooling:" -ForegroundColor White
$observerPyOk  = Test-Path $ObserverPy
$observerBatOk = Test-Path $ObserverBat
$statusPyOk    = Test-Path $StatusPy
Write-Check "scripts\fatigue_stage4_observer.py"      $observerPyOk  $ObserverPy
Write-Check "scripts\run_fatigue_stage4_observer.bat" $observerBatOk $ObserverBat
Write-Check "scripts\fatigue_stage4_status.py"        $statusPyOk    $StatusPy

# --- Scheduled task ----------------------------------------------------------
Write-Host "`nScheduled task ($TaskName):" -ForegroundColor White
$taskFolder = Split-Path $TaskName -Parent
$taskLeaf   = Split-Path $TaskName -Leaf
$taskPath   = if ($taskFolder) { "\$taskFolder\" } else { "\" }

$task = $null
$taskInfo = $null
try {
    $task = Get-ScheduledTask -TaskName $taskLeaf -TaskPath $taskPath -ErrorAction Stop
    $taskInfo = $task | Get-ScheduledTaskInfo -ErrorAction Stop
} catch {
    $task = $null
}

$taskExists = $null -ne $task
$taskEnabled = $false
$lastResultRaw = $null
if ($taskExists) {
    $taskEnabled = ($task.State -ne "Disabled")
    $lastResultRaw = $taskInfo.LastTaskResult
    Write-Check "task registered" $true $TaskName
    Write-Check "task enabled"    $taskEnabled ("State = {0}" -f $task.State)
    Write-Host  ("       next run : {0}" -f $taskInfo.NextRunTime)
    Write-Host  ("       last run : {0}" -f $taskInfo.LastRunTime)
    Write-Host  ("       last code: {0}" -f (Format-ResultCode $lastResultRaw))
    Write-Host  ("       meaning  : {0}" -f (Explain-ResultCode $lastResultRaw)) -ForegroundColor DarkGray
} else {
    Write-Check "task registered" $false "not found - run install_fatigue_stage4_observer_task.ps1"
}

# --- Latest observer log -----------------------------------------------------
Write-Host "`nLatest observer output:" -ForegroundColor White
$logOk = Test-Path $LatestLog
if ($logOk) {
    $logItem = Get-Item $LatestLog
    Write-Check "logs\fatigue_stage4_latest.txt" $true ("modified {0}" -f $logItem.LastWriteTime)
    Write-Host ("       path: {0}" -f $LatestLog) -ForegroundColor DarkGray
} else {
    Write-Check "logs\fatigue_stage4_latest.txt" $false "not written yet (task has not produced output)"
}

# --- Calibration CSV ---------------------------------------------------------
Write-Host "`nCalibration log:" -ForegroundColor White
$csvExists = Test-Path $CalibCsv
$csvPending = 0
$csvAnnotated = 0
if ($csvExists) {
    try {
        $rows = @(Import-Csv $CalibCsv)
        $csvAnnotated = @($rows | Where-Object { $_.felt_band -and $_.felt_band.Trim() }).Count
        $csvPending   = $rows.Count - $csvAnnotated
    } catch {
        $csvExists = $false
    }
}
if ($csvExists) {
    Write-Check "docs\fatigue_meter\stage4_calibration_log.csv" $true ("{0} pending, {1} annotated row(s)" -f $csvPending, $csvAnnotated)
} else {
    Write-Info "docs\fatigue_meter\stage4_calibration_log.csv" "not created yet (expected until logged data has been observed)"
}

# --- workout_log row count (read-only via Python helper) ---------------------
Write-Host "`nLogged workout data:" -ForegroundColor White
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

$workoutLogRows = $null
$dbError = $null
if ($statusPyOk) {
    try {
        $json = & $Python $StatusPy 2>&1 | Out-String
        $status = $json | ConvertFrom-Json
        $workoutLogRows = $status.workout_log_rows
        $dbError = $status.error
        if ($dbError) {
            Write-Check "workout_log query" $false ("DB error: {0}" -f $dbError)
        } elseif (-not $status.db_exists) {
            Write-Check "workout_log query" $false ("database not found at {0}" -f $status.db_path)
        } else {
            $hasData = ($workoutLogRows -gt 0)
            Write-Check "workout_log row count" $true ("{0} row(s)" -f $workoutLogRows)
            if (-not $hasData) {
                Write-Host "       (empty - observer is correct but has nothing to calibrate against)" -ForegroundColor DarkGray
            }
        }
    } catch {
        Write-Check "workout_log query" $false ("failed to run status helper: {0}" -f $_.Exception.Message)
    }
} else {
    Write-Check "workout_log query" $false "status helper missing"
}

# --- Verdict -----------------------------------------------------------------
Write-Host "`n----------------------------------------------------------------" -ForegroundColor Cyan
$lastResultU = if ($null -ne $lastResultRaw) { [int64]$lastResultRaw -band 0xFFFFFFFFL } else { $null }
$filesOk = $observerPyOk -and $observerBatOk -and $statusPyOk

# Hard-failure codes: anything nonzero that is not the 0x800710E0 "skipped" code
# and not a benign "ready / not yet run / running" state code.
$benignStates = @(0x0, 0x41300, 0x41301, 0x41303)
$skippedCode  = 0x800710E0

if (-not $filesOk -or -not $taskExists) {
    Write-Host " VERDICT: [BROKEN] automation is not fully installed." -ForegroundColor Red
    if (-not $filesOk)    { Write-Host "   - One or more observer scripts are missing (see FAIL rows above)." }
    if (-not $taskExists) { Write-Host "   - The scheduled task is not registered. Run:" }
    if (-not $taskExists) { Write-Host "       .\scripts\install_fatigue_stage4_observer_task.ps1" -ForegroundColor Yellow }
} elseif (-not $taskEnabled) {
    Write-Host " VERDICT: [BROKEN] the task exists but is DISABLED." -ForegroundColor Red
    Write-Host "   - Re-enable it, or re-run install_fatigue_stage4_observer_task.ps1." -ForegroundColor Yellow
} elseif ($null -ne $dbError) {
    Write-Host " VERDICT: [BROKEN] the database could not be read - $dbError" -ForegroundColor Red
} elseif ($lastResultU -eq $skippedCode) {
    Write-Host " VERDICT: [SKIPPED] installed, but Windows refused/skipped the last run (0x800710E0)." -ForegroundColor Yellow
    Write-Host "   - The automation itself is healthy. Windows skipped the 20:00 slot (asleep/off/battery)."
    Write-Host "   - Trigger it manually to confirm:"
    Write-Host "       schtasks /Run /TN `"$TaskName`"" -ForegroundColor Yellow
} elseif (($null -ne $lastResultU) -and ($benignStates -notcontains $lastResultU)) {
    Write-Host (" VERDICT: [BROKEN] the last run failed with {0}." -f (Format-ResultCode $lastResultRaw)) -ForegroundColor Red
    Write-Host ("   - {0}" -f (Explain-ResultCode $lastResultRaw))
    Write-Host "   - Inspect logs\fatigue_stage4_latest.txt and re-run via schtasks /Run." -ForegroundColor Yellow
} elseif ($workoutLogRows -gt 0) {
    Write-Host " VERDICT: [READY] logged data exists - calibration rows can be collected." -ForegroundColor Green
    if ($csvPending -gt 0) {
        Write-Host ("   - {0} pending row(s) await a felt_band label in the calibration CSV." -f $csvPending)
    } else {
        Write-Host "   - Run the observer (or wait for the 20:00 task) to append pending rows, then annotate felt_band."
    }
    Write-Host "   - After annotating, analyze with:"
    Write-Host "       .venv\Scripts\python.exe scripts\fatigue_stage4_observer.py --analyze" -ForegroundColor Yellow
} else {
    Write-Host " VERDICT: [IDLE] automation ran successfully but workout_log is empty." -ForegroundColor Cyan
    Write-Host "   - Nothing to calibrate against yet. This is expected until you train and log sessions."
    Write-Host "   - Stage 4 stays blocked on real logged workouts (no synthetic data, by design)."
}
Write-Host "----------------------------------------------------------------" -ForegroundColor Cyan
Write-Host ""
